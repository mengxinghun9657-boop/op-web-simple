#!/usr/bin/env python3
"""重置管理员密码"""

from app.core.deps import engine, SessionLocal
from app.models.user import User, UserRole
from app.core.security import get_password_hash
from app.models.base import Base

def reset_admin():
    # 确保表存在
    Base.metadata.create_all(bind=engine, checkfirst=True)
    
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.username == "admin").first()
        # 新密码
        new_password = "DF210354ws!"
        
        if admin:
            admin.hashed_password = get_password_hash(new_password)
            print(f"✅ 管理员密码已重置为: {new_password}")
        else:
            admin = User(
                username="admin",
                hashed_password=get_password_hash(new_password),
                full_name="系统管理员",
                role=UserRole.SUPER_ADMIN,
                is_active=True
            )
            db.add(admin)
            print(f"✅ 管理员用户已创建: admin / {new_password}")
        db.commit()
    finally:
        db.close()

if __name__ == "__main__":
    reset_admin()
