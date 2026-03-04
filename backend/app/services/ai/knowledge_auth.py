#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
知识库管理二次验证服务 (Knowledge Base Authentication Service)

负责知识库管理的二次密码验证和会话管理，包括：
- 密码验证（验证用户密码与 MySQL 中的哈希匹配）
- 会话令牌生成和验证（JWT，30 分钟有效期）
- 密码失败锁定机制（5次失败后锁定30分钟）
- 会话注销

Requirements: 25.1-25.10
"""

import time
from jose import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.logger import logger
from app.core.security import verify_password
from app.core.redis_client import get_redis_client
from app.services.ai.audit_logger import AuditLogger
from app.core.config import settings
import os


class KnowledgeAuthService:
    """
    知识库管理二次验证服务
    
    提供知识库管理的安全验证机制：
    - 二次密码验证
    - JWT 会话令牌管理
    - 失败锁定机制
    - 审计日志记录
    
    使用示例：
    ```python
    auth_service = KnowledgeAuthService(db_session)
    
    # 验证密码
    result = await auth_service.verify_password(
        user_id="user123",
        username="admin",
        password="admin123"
    )
    
    if result["success"]:
        token = result["token"]
        # 使用 token 访问知识库管理功能
    ```
    """
    
    # 常量配置
    SESSION_TTL = int(os.getenv('SESSION_TTL', '86400'))  # 会话有效期：从环境变量读取，默认 24 小时（秒）
    MAX_FAILURES = 5  # 最大失败次数
    LOCKOUT_DURATION = 1800  # 锁定时长：30 分钟（秒）
    JWT_SECRET = settings.SECRET_KEY  # JWT 密钥
    JWT_ALGORITHM = "HS256"  # JWT 算法
    
    def __init__(
        self,
        db: Session,
        redis_client=None,
        audit_logger: Optional[AuditLogger] = None
    ):
        """
        初始化知识库认证服务
        
        Args:
            db: 数据库会话
            redis_client: Redis 客户端（可选，默认使用全局实例）
            audit_logger: 审计日志记录器（可选，默认创建新实例）
        """
        self.db = db
        self.redis_client = redis_client or get_redis_client()
        self.audit_logger = audit_logger or AuditLogger(db)
        
        logger.info("KnowledgeAuthService initialized")
    
    def _get_failure_key(self, user_id: str) -> str:
        """获取失败计数的 Redis key"""
        return f"auth_failures:{user_id}"
    
    def _get_session_key(self, user_id: str) -> str:
        """获取会话令牌的 Redis key"""
        return f"knowledge_session:{user_id}"
    
    async def _get_user_password_hash(self, user_id: str) -> Optional[str]:
        """
        从 MySQL 获取用户的密码哈希
        
        Args:
            user_id: 用户ID
        
        Returns:
            Optional[str]: 密码哈希，如果用户不存在返回 None
        """
        try:
            from app.core.database import SessionLocal
            
            # 使用同步会话
            with SessionLocal() as sync_db:
                sql_stmt = text("""
                    SELECT hashed_password
                    FROM users
                    WHERE id = :user_id
                """)
                
                result = sync_db.execute(sql_stmt, {"user_id": user_id})
                row = result.fetchone()
                
                if row:
                    return row[0]
                return None
        
        except Exception as e:
            logger.error(f"❌ 获取用户密码哈希失败: user_id={user_id}, error={e}")
            return None
    
    async def _check_lockout(self, user_id: str) -> Dict[str, Any]:
        """
        检查用户是否被锁定
        
        Args:
            user_id: 用户ID
        
        Returns:
            Dict: 包含 is_locked（是否锁定）、locked_until（锁定到期时间）、failure_count（失败次数）
        """
        try:
            failure_key = self._get_failure_key(user_id)
            failure_data = self.redis_client.get_cache(failure_key)
            
            if not failure_data:
                return {
                    "is_locked": False,
                    "locked_until": None,
                    "failure_count": 0
                }
            
            failure_count = failure_data.get("failure_count", 0)
            locked_until = failure_data.get("locked_until")
            
            # 检查是否仍在锁定期内
            if locked_until and locked_until > time.time():
                return {
                    "is_locked": True,
                    "locked_until": locked_until,
                    "failure_count": failure_count
                }
            
            # 锁定已过期，重置计数
            if locked_until and locked_until <= time.time():
                self.redis_client.delete_cache(failure_key)
                return {
                    "is_locked": False,
                    "locked_until": None,
                    "failure_count": 0
                }
            
            return {
                "is_locked": False,
                "locked_until": None,
                "failure_count": failure_count
            }
        
        except Exception as e:
            logger.error(f"❌ 检查锁定状态失败: user_id={user_id}, error={e}")
            return {
                "is_locked": False,
                "locked_until": None,
                "failure_count": 0
            }
    
    async def _record_failure(self, user_id: str) -> Dict[str, Any]:
        """
        记录密码验证失败
        
        Args:
            user_id: 用户ID
        
        Returns:
            Dict: 包含 failure_count（失败次数）、is_locked（是否锁定）、locked_until（锁定到期时间）
        """
        try:
            failure_key = self._get_failure_key(user_id)
            failure_data = self.redis_client.get_cache(failure_key) or {}
            
            failure_count = failure_data.get("failure_count", 0) + 1
            
            # 检查是否达到锁定阈值
            if failure_count >= self.MAX_FAILURES:
                locked_until = time.time() + self.LOCKOUT_DURATION
                failure_data = {
                    "failure_count": failure_count,
                    "locked_until": locked_until
                }
                
                # 保存到 Redis（锁定时长）
                self.redis_client.set_cache(
                    failure_key,
                    failure_data,
                    expire=self.LOCKOUT_DURATION
                )
                
                logger.warning(
                    f"🔒 用户已被锁定: user_id={user_id}, "
                    f"failure_count={failure_count}, locked_until={datetime.fromtimestamp(locked_until)}"
                )
                
                return {
                    "failure_count": failure_count,
                    "is_locked": True,
                    "locked_until": locked_until
                }
            else:
                failure_data = {
                    "failure_count": failure_count
                }
                
                # 保存到 Redis（锁定时长，以防连续失败）
                self.redis_client.set_cache(
                    failure_key,
                    failure_data,
                    expire=self.LOCKOUT_DURATION
                )
                
                logger.warning(
                    f"⚠️ 密码验证失败: user_id={user_id}, "
                    f"failure_count={failure_count}/{self.MAX_FAILURES}"
                )
                
                return {
                    "failure_count": failure_count,
                    "is_locked": False,
                    "locked_until": None
                }
        
        except Exception as e:
            logger.error(f"❌ 记录失败次数失败: user_id={user_id}, error={e}")
            return {
                "failure_count": 0,
                "is_locked": False,
                "locked_until": None
            }
    
    async def _reset_failures(self, user_id: str) -> None:
        """
        重置失败计数
        
        Args:
            user_id: 用户ID
        """
        try:
            failure_key = self._get_failure_key(user_id)
            self.redis_client.delete_cache(failure_key)
            logger.info(f"✅ 重置失败计数: user_id={user_id}")
        
        except Exception as e:
            logger.error(f"❌ 重置失败计数失败: user_id={user_id}, error={e}")
    
    def _generate_session_token(self, user_id: str, username: str) -> str:
        """
        生成知识库管理会话令牌（JWT）
        
        Args:
            user_id: 用户ID
            username: 用户名
        
        Returns:
            str: JWT 令牌
            
        Validates: Requirements 25.4
        """
        try:
            now = datetime.utcnow()
            expires_at = now + timedelta(seconds=self.SESSION_TTL)
            
            payload = {
                "user_id": user_id,
                "username": username,
                "type": "knowledge_management",
                "iat": now.timestamp(),
                "exp": expires_at.timestamp()
            }
            
            token = jwt.encode(payload, self.JWT_SECRET, algorithm=self.JWT_ALGORITHM)
            
            logger.info(
                f"✅ 生成会话令牌: user_id={user_id}, "
                f"expires_at={expires_at.isoformat()}"
            )
            
            return token
        
        except Exception as e:
            logger.error(f"❌ 生成会话令牌失败: user_id={user_id}, error={e}")
            raise Exception(f"生成会话令牌失败: {str(e)}")
    
    async def verify_password(
        self,
        user_id: str,
        username: str,
        password: str,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        验证用户密码并生成会话令牌
        
        Args:
            user_id: 用户ID
            username: 用户名
            password: 用户密码（明文）
            session_id: 会话ID（可选）
            ip_address: IP地址（可选）
            user_agent: User Agent（可选）
        
        Returns:
            Dict: 包含 success（是否成功）、token（会话令牌）、message（消息）、
                  failure_count（失败次数）、locked_until（锁定到期时间）
        
        Validates: Requirements 25.1, 25.2, 25.3, 25.4, 25.5, 25.6
        """
        try:
            # 1. 检查是否被锁定（Requirements 25.6）
            lockout_status = await self._check_lockout(user_id)
            
            if lockout_status["is_locked"]:
                locked_until_dt = datetime.fromtimestamp(lockout_status["locked_until"])
                remaining_seconds = int(lockout_status["locked_until"] - time.time())
                
                # 记录审计日志
                await self.audit_logger.log_auth_verify_failed(
                    user_id=user_id,
                    username=username,
                    failure_reason=f"账户已锁定，剩余时间: {remaining_seconds}秒",
                    session_id=session_id,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                
                logger.warning(
                    f"🔒 账户已锁定: user_id={user_id}, "
                    f"locked_until={locked_until_dt.isoformat()}"
                )
                
                return {
                    "success": False,
                    "token": None,
                    "message": f"账户已锁定，请在 {remaining_seconds} 秒后重试",
                    "failure_count": lockout_status["failure_count"],
                    "locked_until": lockout_status["locked_until"],
                    "error_code": "ACCOUNT_LOCKED"
                }
            
            # 2. 获取用户密码哈希（Requirements 25.3）
            password_hash = await self._get_user_password_hash(user_id)
            
            if not password_hash:
                # 用户不存在
                await self.audit_logger.log_auth_verify_failed(
                    user_id=user_id,
                    username=username,
                    failure_reason="用户不存在",
                    session_id=session_id,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                
                logger.warning(f"⚠️ 用户不存在: user_id={user_id}")
                
                return {
                    "success": False,
                    "token": None,
                    "message": "用户不存在或密码错误",
                    "failure_count": 0,
                    "locked_until": None,
                    "error_code": "INVALID_CREDENTIALS"
                }
            
            # 3. 验证密码（Requirements 25.3）
            is_valid = verify_password(password, password_hash)
            
            if not is_valid:
                # 密码错误，记录失败（Requirements 25.5, 25.6）
                failure_result = await self._record_failure(user_id)
                
                # 记录审计日志
                await self.audit_logger.log_auth_verify_failed(
                    user_id=user_id,
                    username=username,
                    failure_reason="密码错误",
                    session_id=session_id,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                
                if failure_result["is_locked"]:
                    locked_until_dt = datetime.fromtimestamp(failure_result["locked_until"])
                    logger.warning(
                        f"🔒 密码验证失败，账户已锁定: user_id={user_id}, "
                        f"locked_until={locked_until_dt.isoformat()}"
                    )
                    
                    return {
                        "success": False,
                        "token": None,
                        "message": f"密码错误次数过多，账户已锁定 {self.LOCKOUT_DURATION // 60} 分钟",
                        "failure_count": failure_result["failure_count"],
                        "locked_until": failure_result["locked_until"],
                        "error_code": "ACCOUNT_LOCKED"
                    }
                else:
                    remaining_attempts = self.MAX_FAILURES - failure_result["failure_count"]
                    logger.warning(
                        f"⚠️ 密码验证失败: user_id={user_id}, "
                        f"failure_count={failure_result['failure_count']}/{self.MAX_FAILURES}"
                    )
                    
                    return {
                        "success": False,
                        "token": None,
                        "message": f"密码错误，剩余尝试次数: {remaining_attempts}",
                        "failure_count": failure_result["failure_count"],
                        "locked_until": None,
                        "error_code": "INVALID_PASSWORD"
                    }
            
            # 4. 密码正确，生成会话令牌（Requirements 25.4）
            token = self._generate_session_token(user_id, username)
            
            # 5. 保存会话令牌到 Redis
            session_key = self._get_session_key(user_id)
            session_data = {
                "user_id": user_id,
                "username": username,
                "token": token,
                "verified_at": time.time(),
                "expires_at": time.time() + self.SESSION_TTL
            }
            
            logger.info(
                f"💾 保存会话到 Redis: user_id={user_id}, session_key={session_key}, "
                f"SESSION_TTL={self.SESSION_TTL}, expires_at={session_data['expires_at']}"
            )
            
            self.redis_client.set_cache(
                session_key,
                session_data,
                expire=self.SESSION_TTL
            )
            
            logger.info(f"✅ 会话已保存到 Redis: user_id={user_id}, session_key={session_key}")
            
            # 6. 重置失败计数
            await self._reset_failures(user_id)
            
            # 7. 记录审计日志
            await self.audit_logger.log_auth_verify_success(
                user_id=user_id,
                username=username,
                session_id=session_id,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            logger.info(
                f"✅ 密码验证成功: user_id={user_id}, username={username}"
            )
            
            return {
                "success": True,
                "token": token,
                "message": "验证成功",
                "expires_in": self.SESSION_TTL,
                "failure_count": 0,
                "locked_until": None
            }
        
        except Exception as e:
            logger.error(f"❌ 密码验证失败: user_id={user_id}, error={e}")
            raise Exception(f"密码验证失败: {str(e)}")
    
    async def verify_session_token(
        self,
        token: str
    ) -> Dict[str, Any]:
        """
        验证会话令牌
        
        Args:
            token: JWT 令牌
        
        Returns:
            Dict: 包含 valid（是否有效）、user_id（用户ID）、username（用户名）、
                  message（消息）、error_code（错误代码）
        
        Validates: Requirements 25.7, 25.8
        """
        try:
            # 1. 解码 JWT 令牌
            try:
                payload = jwt.decode(
                    token,
                    self.JWT_SECRET,
                    algorithms=[self.JWT_ALGORITHM]
                )
            except jwt.ExpiredSignatureError:
                logger.debug("⚠️ 会话令牌已过期")  # 降级为 debug
                return {
                    "valid": False,
                    "user_id": None,
                    "username": None,
                    "message": "会话已过期，请重新验证",
                    "error_code": "TOKEN_EXPIRED"
                }
            except jwt.InvalidTokenError as e:
                logger.debug(f"⚠️ 无效的会话令牌: {e}")  # 降级为 debug
                return {
                    "valid": False,
                    "user_id": None,
                    "username": None,
                    "message": "无效的会话令牌",
                    "error_code": "INVALID_TOKEN"
                }
            
            # 2. 验证令牌类型
            if payload.get("type") != "knowledge_management":
                logger.warning("⚠️ 令牌类型不匹配")
                return {
                    "valid": False,
                    "user_id": None,
                    "username": None,
                    "message": "无效的令牌类型",
                    "error_code": "INVALID_TOKEN_TYPE"
                }
            
            # 3. 检查 Redis 中的会话是否存在
            user_id = payload.get("user_id")
            session_key = self._get_session_key(user_id)
            session_data = self.redis_client.get_cache(session_key)
            
            logger.debug(f"🔍 检查会话: user_id={user_id}, session_key={session_key}, session_data={session_data}")
            
            if not session_data:
                logger.warning(f"⚠️ 会话不存在: user_id={user_id}, session_key={session_key}")
                return {
                    "valid": False,
                    "user_id": None,
                    "username": None,
                    "message": "会话不存在或已过期",
                    "error_code": "SESSION_NOT_FOUND"
                }
            
            # 4. 验证令牌是否匹配
            stored_token = session_data.get("token")
            logger.debug(f"🔍 令牌对比: stored_token={stored_token[:50] if stored_token else None}..., token={token[:50] if token else None}...")
            
            if stored_token != token:
                logger.warning(f"⚠️ 令牌不匹配: user_id={user_id}")
                return {
                    "valid": False,
                    "user_id": None,
                    "username": None,
                    "message": "令牌不匹配",
                    "error_code": "TOKEN_MISMATCH"
                }
            
            # 5. 验证成功
            logger.info(f"✅ 会话令牌验证成功: user_id={user_id}")
            
            return {
                "valid": True,
                "user_id": payload.get("user_id"),
                "username": payload.get("username"),
                "message": "验证成功",
                "expires_at": payload.get("exp")
            }
        
        except Exception as e:
            logger.error(f"❌ 验证会话令牌失败: error={e}")
            return {
                "valid": False,
                "user_id": None,
                "username": None,
                "message": f"验证失败: {str(e)}",
                "error_code": "VERIFICATION_ERROR"
            }
    
    async def logout(
        self,
        user_id: str,
        token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        注销知识库管理会话
        
        Args:
            user_id: 用户ID
            token: JWT 令牌（可选，用于验证）
        
        Returns:
            Dict: 包含 success（是否成功）、message（消息）
        
        Validates: Requirements 25.9, 25.10
        """
        try:
            # 1. 如果提供了 token，先验证
            if token:
                verification = await self.verify_session_token(token)
                if not verification["valid"]:
                    return {
                        "success": False,
                        "message": "无效的会话令牌"
                    }
                
                # 验证 user_id 是否匹配
                if verification["user_id"] != user_id:
                    return {
                        "success": False,
                        "message": "用户ID不匹配"
                    }
            
            # 2. 删除 Redis 中的会话
            session_key = self._get_session_key(user_id)
            self.redis_client.delete_cache(session_key)
            
            logger.info(f"✅ 注销知识库管理会话: user_id={user_id}")
            
            return {
                "success": True,
                "message": "注销成功"
            }
        
        except Exception as e:
            logger.error(f"❌ 注销会话失败: user_id={user_id}, error={e}")
            return {
                "success": False,
                "message": f"注销失败: {str(e)}"
            }
    
    async def get_session_info(
        self,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        获取会话信息
        
        Args:
            user_id: 用户ID
        
        Returns:
            Optional[Dict]: 会话信息，如果不存在返回 None
        """
        try:
            session_key = self._get_session_key(user_id)
            session_data = self.redis_client.get_cache(session_key)
            
            if not session_data:
                return None
            
            return {
                "user_id": session_data.get("user_id"),
                "username": session_data.get("username"),
                "verified_at": session_data.get("verified_at"),
                "expires_at": session_data.get("expires_at"),
                "remaining_seconds": int(session_data.get("expires_at", 0) - time.time())
            }
        
        except Exception as e:
            logger.error(f"❌ 获取会话信息失败: user_id={user_id}, error={e}")
            return None


# 全局实例（可选）
_knowledge_auth_service: Optional[KnowledgeAuthService] = None


def get_knowledge_auth_service(db: Session) -> KnowledgeAuthService:
    """
    获取知识库认证服务实例
    
    Args:
        db: 数据库会话
    
    Returns:
        KnowledgeAuthService: 认证服务实例
    """
    return KnowledgeAuthService(db)
