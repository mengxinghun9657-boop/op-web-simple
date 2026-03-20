#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手动导入CSV数据到数据库
用法：python import_to_db.py
"""

from database_writer import InstanceDatabaseWriter
from config import DB_CONFIG

def main():
    print("=" * 60)
    print("BCC/CCE实例数据库导入工具")
    print("=" * 60)
    
    # 创建数据库写入器
    try:
        writer = InstanceDatabaseWriter(**DB_CONFIG)
        print(f"✓ 数据库连接成功: {DB_CONFIG['database']}")
        print(f"  - BCC表: {DB_CONFIG['bcc_table']}")
        print(f"  - CCE表: {DB_CONFIG['cce_table']}")
    except Exception as e:
        print(f"✗ 数据库连接失败: {e}")
        print("\n请检查 config.py 中的 DB_CONFIG 配置：")
        print(f"  - host: {DB_CONFIG.get('host')}")
        print(f"  - port: {DB_CONFIG.get('port')}")
        print(f"  - user: {DB_CONFIG.get('user')}")
        print(f"  - database: {DB_CONFIG.get('database')}")
        print(f"  - bcc_table: {DB_CONFIG.get('bcc_table')}")
        print(f"  - cce_table: {DB_CONFIG.get('cce_table')}")
        return
    
    # 导入所有最新数据
    writer.import_all_latest()

if __name__ == "__main__":
    main()

