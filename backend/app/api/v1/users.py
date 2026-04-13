from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from ...schemas.user import UserCreate, UserLogin, UserResponse, TokenResponse, UserUpdate, AuditLogResponse
from ...schemas.response import APIResponse, PaginatedResponse
from ...models.user import User, AuditLog, UserRole
from ...core.security import verify_password, get_password_hash, create_access_token, create_refresh_token
from ...core.deps import get_db, get_current_user

router = APIRouter()

# =============== 认证相关 ===============

@router.post("/auth/login")
def login(user_data: UserLogin, request: Request, db: Session = Depends(get_db)):
    """用户登录"""
    user = db.query(User).filter(User.username == user_data.username).first()
    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用"
        )
    
    # 更新最后登录时间
    user.last_login = datetime.utcnow()
    db.commit()
    
    # 记录审计日志
    audit = AuditLog(
        user_id=user.id,
        username=user.username,
        action="LOGIN",
        resource="System",
        ip_address=request.client.host
    )
    db.add(audit)
    db.commit()
    
    # 生成Token
    token_data = {"sub": str(user.id), "username": user.username, "role": user.role}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    return {
        "success": True,
        "data": {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": UserResponse.from_orm(user).dict()
        },
        "message": "登录成功"
    }

from pydantic import BaseModel
from jose import jwt, JWTError

class RefreshTokenRequest(BaseModel):
    refresh_token: str

@router.post("/auth/refresh")
def refresh_token(request_data: RefreshTokenRequest, db: Session = Depends(get_db)):
    """刷新Token"""
    from app.core.security import SECRET_KEY, ALGORITHM
    
    try:
        payload = jwt.decode(request_data.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="无效的刷新令牌")
        
        user_id = payload.get("sub")
        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="用户不存在或已禁用")
        
        token_data = {"sub": str(user.id), "username": user.username, "role": user.role}
        return {
            "success": True,
            "data": {
                "access_token": create_access_token(token_data),
                "refresh_token": create_refresh_token(token_data)
            },
            "message": "Token刷新成功"
        }
    except JWTError:
        raise HTTPException(status_code=401, detail="刷新令牌已过期或无效")

# =============== 用户管理 ===============

@router.get("/users/me")
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """获取当前登录用户信息"""
    return {
        "success": True,
        "data": UserResponse.from_orm(current_user).dict(),
        "message": "获取成功"
    }

@router.get("/users")
def get_users(
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取用户列表（需要admin权限）"""
    if current_user.role not in [UserRole.SUPER_ADMIN.value, UserRole.ADMIN.value]:
        raise HTTPException(status_code=403, detail="权限不足")
    
    # 计算偏移量
    skip = (page - 1) * page_size
    
    # 查询总数和数据
    total = db.query(User).count()
    users = db.query(User).offset(skip).limit(page_size).all()
    
    return {
        "success": True,
        "data": {
            "list": [UserResponse.from_orm(user).dict() for user in users],
            "total": total,
            "page": page,
            "page_size": page_size
        },
        "message": "获取成功"
    }

@router.post("/users", status_code=201)
def create_user(
    user_data: UserCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建新用户"""
    if current_user.role not in [UserRole.SUPER_ADMIN.value, UserRole.ADMIN.value]:
        raise HTTPException(status_code=403, detail="权限不足")
    
    # 检查用户名和邮箱是否已存在
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")
    # 只有当email不为None时才检查唯一性
    if user_data.email and db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(status_code=400, detail="邮箱已存在")
    
    # 创建用户
    user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        role=user_data.role
    )
    db.add(user)
    
    # 审计日志
    audit = AuditLog(
        user_id=current_user.id,
        username=current_user.username,
        action="CREATE",
        resource=f"User: {user.username}",
        ip_address=request.client.host
    )
    db.add(audit)
    
    # 一次性提交所有更改
    db.commit()
    db.refresh(user)
    
    return {
        "success": True,
        "data": UserResponse.from_orm(user).dict(),
        "message": "用户创建成功"
    }

@router.put("/users/{user_id}")
def update_user(
    user_id: int,
    user_data: UserUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新用户信息"""
    if current_user.role not in [UserRole.SUPER_ADMIN.value, UserRole.ADMIN.value]:
        raise HTTPException(status_code=403, detail="权限不足")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # admin 不能修改 super_admin 的信息
    if current_user.role == UserRole.ADMIN.value and user.role == UserRole.SUPER_ADMIN.value:
        raise HTTPException(status_code=403, detail="管理员无权修改超级管理员")

    update_data = user_data.dict(exclude_unset=True)

    # admin 不能将用户角色提升为 super_admin
    if current_user.role == UserRole.ADMIN.value and update_data.get("role") == UserRole.SUPER_ADMIN.value:
        raise HTTPException(status_code=403, detail="管理员无权将用户设置为超级管理员")

    for field, value in update_data.items():
        setattr(user, field, value)
    
    # 审计日志
    audit = AuditLog(
        user_id=current_user.id,
        username=current_user.username,
        action="UPDATE",
        resource=f"User: {user.username}",
        ip_address=request.client.host
    )
    db.add(audit)
    
    # 一次性提交所有更改
    db.commit()
    db.refresh(user)
    
    return {
        "success": True,
        "data": UserResponse.from_orm(user).dict(),
        "message": "用户更新成功"
    }

@router.delete("/users/{user_id}", status_code=204)
def delete_user(
    user_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除用户"""
    if current_user.role != UserRole.SUPER_ADMIN.value:
        raise HTTPException(status_code=403, detail="仅超级管理员可以删除用户")

    if current_user.id == user_id:
        raise HTTPException(status_code=400, detail="不能删除自己的账号")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    username = user.username
    db.delete(user)
    
    # 审计日志
    audit = AuditLog(
        user_id=current_user.id,
        username=current_user.username,
        action="DELETE",
        resource=f"User: {username}",
        ip_address=request.client.host
    )
    db.add(audit)
    
    # 一次性提交所有更改
    db.commit()

@router.post("/users/{user_id}/reset-password")
def reset_password(
    user_id: int,
    password_data: dict,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    重置用户密码

    - **new_password**: 新密码（至少6位）
    """
    if current_user.role not in [UserRole.SUPER_ADMIN.value, UserRole.ADMIN.value]:
        raise HTTPException(status_code=403, detail="权限不足")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # admin 不能重置 super_admin 的密码
    if current_user.role == UserRole.ADMIN.value and user.role == UserRole.SUPER_ADMIN.value:
        raise HTTPException(status_code=403, detail="管理员无权重置超级管理员密码")
    
    new_password = password_data.get('new_password')
    if not new_password or len(new_password) < 6:
        raise HTTPException(status_code=400, detail="密码至少6位")
    
    # 更新密码
    user.hashed_password = get_password_hash(new_password)
    
    # 审计日志
    audit = AuditLog(
        user_id=current_user.id,
        username=current_user.username,
        action="RESET_PASSWORD",
        resource=f"User: {user.username}",
        ip_address=request.client.host
    )
    db.add(audit)
    
    # 一次性提交所有更改
    db.commit()
    
    return {
        "success": True,
        "data": None,
        "message": "密码重置成功"
    }

# =============== 审计日志 ===============

@router.get("/audit-logs")
def get_audit_logs(
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取审计日志"""
    if current_user.role not in [UserRole.SUPER_ADMIN.value, UserRole.ADMIN.value]:
        raise HTTPException(status_code=403, detail="权限不足")
    
    # 计算偏移量
    skip = (page - 1) * page_size
    
    # 查询总数和数据
    total = db.query(AuditLog).count()
    logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).offset(skip).limit(page_size).all()
    
    return {
        "success": True,
        "data": {
            "list": [AuditLogResponse.from_orm(log).dict() for log in logs],
            "total": total,
            "page": page,
            "page_size": page_size
        },
        "message": "获取成功"
    }
