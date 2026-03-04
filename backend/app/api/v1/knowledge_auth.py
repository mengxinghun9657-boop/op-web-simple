#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
知识库管理认证 API 接口

提供知识库管理的二次验证接口：
- POST /api/v1/knowledge/auth/verify - 验证用户密码
- POST /api/v1/knowledge/auth/logout - 注销会话
- GET /api/v1/knowledge/auth/session - 获取会话信息

Requirements: 25.1-25.10
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional

from app.core.deps import get_db, get_current_user
from app.models.user import User, UserRole
from app.services.ai.knowledge_auth import get_knowledge_auth_service, KnowledgeAuthService
from app.core.logger import logger


router = APIRouter()


# Request/Response Models
class PasswordVerifyRequest(BaseModel):
    """密码验证请求"""
    password: str = Field(..., description="用户密码", min_length=1)


class PasswordVerifyResponse(BaseModel):
    """密码验证响应"""
    success: bool = Field(..., description="是否验证成功")
    token: Optional[str] = Field(None, description="会话令牌（JWT）")
    message: str = Field(..., description="响应消息")
    expires_in: Optional[int] = Field(None, description="令牌有效期（秒）")
    failure_count: Optional[int] = Field(None, description="失败次数")
    locked_until: Optional[float] = Field(None, description="锁定到期时间（Unix时间戳）")
    error_code: Optional[str] = Field(None, description="错误代码")


class LogoutResponse(BaseModel):
    """注销响应"""
    success: bool = Field(..., description="是否注销成功")
    message: str = Field(..., description="响应消息")


class SessionInfoResponse(BaseModel):
    """会话信息响应"""
    user_id: str = Field(..., description="用户ID")
    username: str = Field(..., description="用户名")
    verified_at: float = Field(..., description="验证时间（Unix时间戳）")
    expires_at: float = Field(..., description="过期时间（Unix时间戳）")
    remaining_seconds: int = Field(..., description="剩余有效时间（秒）")


@router.post(
    "/verify",
    summary="验证知识库管理密码",
    description="""
    验证用户密码并生成知识库管理会话令牌。
    
    **要求**：
    - 用户必须是超级管理员（SUPER_ADMIN）
    - 密码必须与 MySQL 中存储的密码哈希匹配
    - 连续 5 次失败后锁定 30 分钟
    
    **返回**：
    - 成功：返回 JWT 令牌，有效期 30 分钟
    - 失败：返回错误消息和剩余尝试次数
    - 锁定：返回锁定消息和剩余锁定时间
    
    **Requirements**: 25.1, 25.2, 25.3, 25.4, 25.5, 25.6
    """
)
async def verify_password(
    request: Request,
    verify_request: PasswordVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    验证知识库管理密码
    
    验证流程：
    1. 检查用户角色（必须是超级管理员）
    2. 检查是否被锁定
    3. 验证密码
    4. 生成会话令牌
    5. 记录审计日志
    """
    # 添加入口日志
    logger.info(f"🔐 知识库密码验证请求: user_id={current_user.id}, username={current_user.username}, role={current_user.role}")
    
    try:
        # 1. 验证用户角色（Requirements 25.1）
        if current_user.role != UserRole.SUPER_ADMIN:
            logger.warning(
                f"⚠️ 非超级管理员尝试访问知识库管理: "
                f"user_id={current_user.id}, role={current_user.role}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="仅超级管理员可以访问知识库管理功能"
            )
        
        # 2. 获取认证服务
        auth_service = get_knowledge_auth_service(db)
        
        # 3. 获取请求元数据
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        
        # 4. 验证密码（Requirements 25.2, 25.3, 25.4, 25.5, 25.6）
        result = await auth_service.verify_password(
            user_id=str(current_user.id),
            username=current_user.username,
            password=verify_request.password,
            session_id=None,  # 可以从请求中获取
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # 5. 返回结果
        if result["success"]:
            logger.info(
                f"✅ 知识库管理密码验证成功: "
                f"user_id={current_user.id}, username={current_user.username}"
            )
            return {
                "success": True,
                "data": {
                    "token": result["token"],
                    "expires_in": result.get("expires_in")
                },
                "message": result["message"]
            }
        else:
            # 验证失败
            status_code = status.HTTP_401_UNAUTHORIZED
            if result.get("error_code") == "ACCOUNT_LOCKED":
                status_code = status.HTTP_403_FORBIDDEN
            
            logger.warning(
                f"⚠️ 知识库管理密码验证失败: "
                f"user_id={current_user.id}, error_code={result.get('error_code')}"
            )
            
            raise HTTPException(
                status_code=status_code,
                detail={
                    "message": result["message"],
                    "failure_count": result.get("failure_count"),
                    "locked_until": result.get("locked_until"),
                    "error_code": result.get("error_code")
                }
            )
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"❌ 密码验证接口异常: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"密码验证失败: {str(e)}"
        )


@router.post(
    "/logout",
    summary="注销知识库管理会话",
    description="""
    注销当前用户的知识库管理会话，立即失效会话令牌。
    
    **要求**：
    - 用户必须已登录
    
    **返回**：
    - 成功：返回注销成功消息
    - 失败：返回错误消息
    
    **Requirements**: 25.9, 25.10
    """
)
async def logout(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    注销知识库管理会话
    
    注销流程：
    1. 删除 Redis 中的会话令牌
    2. 返回成功消息
    """
    try:
        # 1. 获取认证服务
        auth_service = get_knowledge_auth_service(db)
        
        # 2. 注销会话
        result = await auth_service.logout(
            user_id=str(current_user.id)
        )
        
        # 3. 返回结果
        if result["success"]:
            logger.info(
                f"✅ 知识库管理会话注销成功: "
                f"user_id={current_user.id}, username={current_user.username}"
            )
            return {
                "success": True,
                "message": result["message"]
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["message"]
            )
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"❌ 注销接口异常: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"注销失败: {str(e)}"
        )


@router.get(
    "/session",
    summary="获取知识库管理会话信息",
    description="""
    获取当前用户的知识库管理会话信息。
    
    **要求**：
    - 用户必须已登录
    - 用户必须是超级管理员
    
    **返回**：
    - 成功：返回会话信息（验证时间、过期时间、剩余时间）
    - 失败：返回 404 错误（会话不存在）
    """
)
async def get_session_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取知识库管理会话信息
    """
    try:
        # 1. 验证用户角色
        if current_user.role != UserRole.SUPER_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="仅超级管理员可以访问知识库管理功能"
            )
        
        # 2. 获取认证服务
        auth_service = get_knowledge_auth_service(db)
        
        # 3. 获取会话信息
        session_info = await auth_service.get_session_info(
            user_id=str(current_user.id)
        )
        
        # 4. 返回结果
        if session_info:
            return {
                "success": True,
                "data": session_info,
                "message": "查询成功"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="会话不存在或已过期"
            )
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"❌ 获取会话信息接口异常: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取会话信息失败: {str(e)}"
        )
