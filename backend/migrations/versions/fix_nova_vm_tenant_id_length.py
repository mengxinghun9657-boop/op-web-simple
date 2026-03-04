"""
修复 nova_vm_tenant_id 字段长度不足问题

问题描述:
- 数据库中 nova_vm_tenant_id 字段定义为 VARCHAR(100)
- 实际数据可能包含多个租户ID（逗号分隔），长度超过100字符
- 导致同步失败: Data too long for column 'nova_vm_tenant_id'

修复方案:
- 将 nova_vm_tenant_id 字段扩展为 VARCHAR(255)

使用方法:
    python3 migrations/versions/fix_nova_vm_tenant_id_length.py

创建时间: 2026-02-02
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from sqlalchemy import create_engine, text
from app.core.config import settings


def fix_tenant_id_length():
    """修复 nova_vm_tenant_id 字段长度"""
    
    print("=" * 80)
    print("修复 nova_vm_tenant_id 字段长度")
    print("=" * 80)
    
    # 创建数据库连接
    engine = create_engine(settings.DATABASE_URL)
    
    try:
        with engine.connect() as conn:
            # 检查表是否存在
            result = conn.execute(text("""
                SELECT COUNT(*) as count 
                FROM information_schema.tables 
                WHERE table_schema = DATABASE() 
                AND table_name = 'iaas_instances'
            """))
            
            if result.fetchone()[0] == 0:
                print("❌ 表 iaas_instances 不存在，无需修复")
                return
            
            # 检查字段当前长度
            result = conn.execute(text("""
                SELECT CHARACTER_MAXIMUM_LENGTH 
                FROM information_schema.columns 
                WHERE table_schema = DATABASE() 
                AND table_name = 'iaas_instances' 
                AND column_name = 'nova_vm_tenant_id'
            """))
            
            row = result.fetchone()
            if row is None:
                print("❌ 字段 nova_vm_tenant_id 不存在")
                return
            
            current_length = row[0]
            print(f"\n当前字段长度: VARCHAR({current_length})")
            
            if current_length >= 255:
                print("✅ 字段长度已经足够，无需修复")
                return
            
            # 执行字段扩容
            print(f"\n开始修复: VARCHAR({current_length}) → VARCHAR(255)")
            
            conn.execute(text("""
                ALTER TABLE iaas_instances 
                MODIFY COLUMN nova_vm_tenant_id VARCHAR(255) 
                COMMENT '租户ID（支持多租户ID逗号分隔）'
            """))
            
            conn.commit()
            
            # 验证修复结果
            result = conn.execute(text("""
                SELECT CHARACTER_MAXIMUM_LENGTH 
                FROM information_schema.columns 
                WHERE table_schema = DATABASE() 
                AND table_name = 'iaas_instances' 
                AND column_name = 'nova_vm_tenant_id'
            """))
            
            new_length = result.fetchone()[0]
            print(f"✅ 修复完成: VARCHAR({new_length})")
            
            print("\n" + "=" * 80)
            print("修复成功！现在可以同步包含多个租户ID的实例数据了")
            print("=" * 80)
            
    except Exception as e:
        print(f"\n❌ 修复失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        engine.dispose()


if __name__ == "__main__":
    fix_tenant_id_length()
