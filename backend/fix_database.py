#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库修复脚本 - 用于内网部署后创建缺失的表
"""

import sys
from sqlalchemy import inspect, text

# 导入所有模型
from app.models.base import Base
from app.core.deps import engine, SessionLocal
from app.models.chat import ChatHistory
from app.models.user import User, AuditLog, UserNote
from app.models.task import Task
from app.models.iaas import IaasServer, IaasInstance

def check_and_create_tables():
    """检查并创建缺失的表"""
    print("=" * 60)
    print("数据库修复脚本")
    print("=" * 60)
    print()
    
    try:
        # 获取数据库中已存在的表
        inspector = inspect(engine)
        existing_tables = set(inspector.get_table_names())
        
        print(f"✓ 数据库已有表 ({len(existing_tables)} 个):")
        for table in sorted(existing_tables):
            print(f"  - {table}")
        print()
        
        # 获取所有应该存在的表
        all_tables = {table.name for table in Base.metadata.sorted_tables}
        
        print(f"✓ 应该存在的表 ({len(all_tables)} 个):")
        for table in sorted(all_tables):
            print(f"  - {table}")
        print()
        
        # 找出缺失的表
        missing_tables = all_tables - existing_tables
        
        if not missing_tables:
            print("✅ 所有表都已存在，无需修复！")
            return True
        
        print(f"⚠️  发现缺失的表 ({len(missing_tables)} 个):")
        for table in sorted(missing_tables):
            print(f"  - {table}")
        print()
        
        # 确认是否创建
        response = input("是否创建缺失的表? (y/n): ")
        if response.lower() != 'y':
            print("已取消")
            return False
        
        print()
        print("开始创建缺失的表...")
        print()
        
        # 创建缺失的表
        success_count = 0
        fail_count = 0
        
        for table in Base.metadata.sorted_tables:
            if table.name in missing_tables:
                try:
                    table.create(bind=engine, checkfirst=True)
                    print(f"✅ 成功创建表: {table.name}")
                    success_count += 1
                except Exception as e:
                    print(f"❌ 创建表 {table.name} 失败: {e}")
                    fail_count += 1
        
        print()
        print("=" * 60)
        print(f"修复完成！成功: {success_count}, 失败: {fail_count}")
        print("=" * 60)
        
        # 再次检查
        inspector = inspect(engine)
        existing_tables_after = set(inspector.get_table_names())
        still_missing = all_tables - existing_tables_after
        
        if still_missing:
            print()
            print("⚠️  以下表仍然缺失:")
            for table in sorted(still_missing):
                print(f"  - {table}")
            return False
        else:
            print()
            print("✅ 所有表已成功创建！")
            return True
            
    except Exception as e:
        print(f"❌ 修复失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_chat_history_table():
    """验证 chat_history 表是否存在并可用"""
    print()
    print("=" * 60)
    print("验证 chat_history 表")
    print("=" * 60)
    print()
    
    try:
        db = SessionLocal()
        
        # 尝试查询表
        result = db.execute(text("SELECT COUNT(*) FROM chat_history"))
        count = result.scalar()
        
        print(f"✅ chat_history 表存在，当前记录数: {count}")
        
        # 显示表结构
        result = db.execute(text("DESCRIBE chat_history"))
        columns = result.fetchall()
        
        print()
        print("表结构:")
        for col in columns:
            print(f"  - {col[0]}: {col[1]}")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ chat_history 表验证失败: {e}")
        return False


if __name__ == "__main__":
    print()
    
    # 检查并创建表
    if check_and_create_tables():
        # 验证 chat_history 表
        verify_chat_history_table()
        print()
        print("🎉 数据库修复成功！请重启 backend 服务：")
        print("   docker compose -f docker-compose.prod.yml restart backend")
        print()
        sys.exit(0)
    else:
        print()
        print("❌ 数据库修复失败，请检查错误信息")
        print()
        sys.exit(1)
