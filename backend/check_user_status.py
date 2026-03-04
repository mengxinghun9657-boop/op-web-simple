#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
检查和修复用户状态脚本

用于排查 403 错误，检查用户的 is_active 状态
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.user import User
from app.core.config import settings

def main():
    """主函数"""
    # 创建数据库连接
    DATABASE_URL = settings.DATABASE_URL.replace("mysql+aiomysql", "mysql+pymysql")
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        print("=" * 60)
        print("用户状态检查")
        print("=" * 60)
        
        # 查询所有用户
        users = db.query(User).all()
        
        if not users:
            print("\n❌ 数据库中没有用户！")
            print("\n建议：运行 init_db.py 创建默认管理员账户")
            return
        
        print(f"\n找到 {len(users)} 个用户：\n")
        
        # 显示用户状态
        inactive_users = []
        for user in users:
            status = "✅ 活跃" if user.is_active else "❌ 禁用"
            print(f"  ID: {user.id}")
            print(f"  用户名: {user.username}")
            print(f"  角色: {user.role}")
            print(f"  状态: {status}")
            print(f"  创建时间: {user.created_at}")
            if user.last_login:
                print(f"  最后登录: {user.last_login}")
            print()
            
            if not user.is_active:
                inactive_users.append(user)
        
        # 如果有禁用的用户，询问是否启用
        if inactive_users:
            print("=" * 60)
            print(f"⚠️  发现 {len(inactive_users)} 个被禁用的用户")
            print("=" * 60)
            
            for user in inactive_users:
                print(f"\n用户: {user.username} (ID: {user.id})")
                answer = input("是否启用此用户？(y/n): ").strip().lower()
                
                if answer == 'y':
                    user.is_active = True
                    db.commit()
                    print(f"✅ 用户 {user.username} 已启用")
                else:
                    print(f"⏭️  跳过用户 {user.username}")
        else:
            print("✅ 所有用户都处于活跃状态")
        
        print("\n" + "=" * 60)
        print("检查完成")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    main()
