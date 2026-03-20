from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from jose import jwt, JWTError
import os
from typing import TYPE_CHECKING

# 使用 TYPE_CHECKING 避免循环导入
if TYPE_CHECKING:
    from ..models.user import User

from .security import SECRET_KEY, ALGORITHM
from .config import settings

# 创建同步数据库引擎（用于用户认证）- 使用连接池
DATABASE_URL = settings.DATABASE_URL.replace("mysql+aiomysql", "mysql+pymysql")
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

security = HTTPBearer()

def get_db():
    """获取数据库会话（同步版本）"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
    token: str = None
):
    """从Token获取当前用户
    
    支持从 HTTP Header Authorization 或 URL 参数 token 获取
    """
    # 延迟导入 User 模型，避免循环导入
    from ..models.user import User
    
    # 优先从 HTTP Header 获取，如果没有则从函数参数获取（用于SSE）
    if credentials:
        token = credentials.credentials
    
    if not token:
        from app.core.logger import logger
        logger.warning("缺少认证令牌")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少认证令牌"
        )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            from app.core.logger import logger
            logger.warning("Token 中缺少 user_id (sub)")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的认证凭证"
            )
    except JWTError as e:
        from app.core.logger import logger
        # 区分不同的JWT错误类型
        error_msg = str(e)
        if "expired" in error_msg.lower():
            logger.info(f"JWT 令牌已过期，用户需要重新登录")
        elif "signature" in error_msg.lower():
            logger.warning(f"JWT 签名验证失败: {e}")
        else:
            logger.warning(f"JWT 解码失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="认证令牌已过期或无效，请重新登录"
        )
    
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        from app.core.logger import logger
        logger.warning(f"用户不存在: user_id={user_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在"
        )
    
    # 检查用户是否被禁用
    if not user.is_active:
        from app.core.logger import logger
        logger.warning(f"用户已被禁用: {user.username} (ID: {user.id})")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户账户已被禁用，请联系管理员"
        )
    
    from app.core.logger import logger
    logger.debug(f"认证成功: {user.username} (ID: {user.id}, Role: {user.role})")
    return user


def require_admin(
    current_user = Depends(get_current_user)
):
    """要求管理员权限"""
    if current_user.role not in ['super_admin', 'admin']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    return current_user
