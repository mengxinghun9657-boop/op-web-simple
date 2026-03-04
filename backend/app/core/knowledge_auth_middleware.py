#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
知识库管理会话令牌验证中间件

提供依赖注入函数，用于验证知识库管理操作的会话令牌。

Requirements: 25.7, 25.8
"""

from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from typing import Optional

from app.core.deps import get_db, get_current_user
from app.models.user import User, UserRole
from app.services.ai.knowledge_auth import get_knowledge_auth_service
from app.core.logger import logger


async def verify_knowledge_session(
    x_knowledge_token: Optional[str] = Header(None, description="知识库管理会话令牌"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict:
    """
    验证知识库管理会话令牌
    
    此函数作为 FastAPI 依赖项使用，用于保护知识库管理相关的 API 接口。
    
    验证流程：
    1. 检查用户角色（必须是超级管理员）
    2. 检查请求头中是否包含会话令牌
    3. 验证令牌的有效性
    4. 返回验证结果
    
    Args:
        x_knowledge_token: 请求头中的会话令牌（X-Knowledge-Token）
        current_user: 当前登录用户
        db: 数据库会话
    
    Returns:
        dict: 包含 user_id、username、expires_at 的验证结果
    
    Raises:
        HTTPException: 验证失败时抛出异常
            - 403: 用户不是超级管理员
            - 401: 缺少会话令牌
            - 401: 令牌无效或已过期
    
    使用示例：
    ```python
    @router.post("/knowledge/entries")
    async def create_entry(
        entry_data: dict,
        session: dict = Depends(verify_knowledge_session),
        db: Session = Depends(get_db)
    ):
        # session 包含验证后的用户信息
        user_id = session["user_id"]
        username = session["username"]
        # ... 执行知识库操作
    ```
    
    Validates: Requirements 25.7, 25.8
    """
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
        
        # 2. 检查会话令牌是否存在
        if not x_knowledge_token:
            logger.warning(
                f"⚠️ 缺少知识库管理会话令牌: user_id={current_user.id}"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="缺少知识库管理会话令牌，请先进行二次验证"
            )
        
        # 3. 验证会话令牌（Requirements 25.7, 25.8）
        auth_service = get_knowledge_auth_service(db)
        verification = await auth_service.verify_session_token(x_knowledge_token)
        
        if not verification["valid"]:
            error_code = verification.get("error_code")
            message = verification.get("message")
            
            logger.warning(
                f"⚠️ 知识库管理会话令牌验证失败: "
                f"user_id={current_user.id}, error_code={error_code}"
            )
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": message,
                    "error_code": error_code
                }
            )
        
        # 4. 验证用户ID是否匹配
        if verification["user_id"] != str(current_user.id):
            logger.warning(
                f"⚠️ 会话令牌用户ID不匹配: "
                f"token_user_id={verification['user_id']}, current_user_id={current_user.id}"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="会话令牌用户ID不匹配"
            )
        
        # 5. 验证成功，返回会话信息
        logger.debug(
            f"✅ 知识库管理会话令牌验证成功: "
            f"user_id={current_user.id}, username={current_user.username}"
        )
        
        return {
            "user_id": verification["user_id"],
            "username": verification["username"],
            "expires_at": verification.get("expires_at")
        }
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"❌ 验证知识库管理会话令牌异常: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"验证会话令牌失败: {str(e)}"
        )


# 可选：提供一个更简洁的别名
require_knowledge_session = verify_knowledge_session
