from pydantic import BaseModel, constr
from typing import Optional
from datetime import datetime
from ..models.user import UserRole

# Request Schemas
class UserCreate(BaseModel):
    username: constr(min_length=3, max_length=50)
    email: Optional[str] = None  # 不需要注册功能，email改为可选
    password: constr(min_length=6)
    full_name: Optional[str] = None
    role: UserRole = UserRole.VIEWER

class UserLogin(BaseModel):
    username: str
    password: str

class UserUpdate(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None

# Response Schemas
class UserResponse(BaseModel):
    id: int
    username: str
    email: Optional[str]
    full_name: Optional[str]
    role: UserRole
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime]

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse

class AuditLogResponse(BaseModel):
    id: int
    user_id: int
    username: str
    action: str
    resource: str
    ip_address: str
    created_at: datetime

    class Config:
        from_attributes = True
