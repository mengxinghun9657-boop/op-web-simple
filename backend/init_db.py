#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
初始化数据库并创建默认管理员用户
"""

from app.models.base import Base  # 修改：使用正确的 Base
from app.core.deps import engine, SessionLocal
from app.models.user import User, UserRole
from app.models.task import Task  # 确保Task模型被导入
from app.core.security import get_password_hash

def init_database():
    """初始化数据库表"""
    print("🔄 创建数据库表...")
    Base.metadata.create_all(bind=engine, checkfirst=True)
    print("✅ 数据库表创建完成")

def create_default_users():
    """创建默认用户"""
    db = SessionLocal()
    
    try:
        # 检查是否已存在admin用户
        existing_admin = db.query(User).filter(User.username == "admin").first()
        if existing_admin:
            print("⚠️  管理员用户已存在，跳过创建")
            return
        
        # 创建超级管理员
        admin = User(
            username="admin",
            email="admin@example.com",
            hashed_password=get_password_hash("admin"),
            full_name="系统管理员",
            role=UserRole.SUPER_ADMIN,
            is_active=True
        )
        db.add(admin)
        
        # 创建测试用户
        test_analyst = User(
            username="analyst",
            email="analyst@example.com",
            hashed_password=get_password_hash("analyst123"),
            full_name="数据分析师",
            role=UserRole.ANALYST,
            is_active=True
        )
        db.add(test_analyst)
        
        test_viewer = User(
            username="viewer",
            email="viewer@example.com",
            hashed_password=get_password_hash("viewer123"),
            full_name="只读用户",
            role=UserRole.VIEWER,
            is_active=True
        )
        db.add(test_viewer)
        
        db.commit()
        
        print("✅ 默认用户创建成功：")
        print("   - 超级管理员: admin / admin")
        print("   - 分析师: analyst / analyst123")
        print("   - 只读用户: viewer / viewer123")
        
    except Exception as e:
        print(f"❌ 创建用户失败: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("=" * 50)
    print("🚀 初始化集群管理平台数据库")
    print("=" * 50)
    
    init_database()
    create_default_users()
    
    print("\n✅ 初始化完成！")
    print("=" * 50)
