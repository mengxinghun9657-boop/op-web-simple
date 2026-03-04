#!/bin/bash
# CMDB Schema 快速检查脚本

echo "╔══════════════════════════════════════════╗"
echo "║     CMDB Schema 检查工具                 ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# 检查是否在Docker环境中
if [ -f "/.dockerenv" ]; then
    # 在容器内部
    python3 -c "
from app.core.database import engine
from sqlalchemy import inspect

print('检查 CMDB 数据库表结构...\n')

inspector = inspect(engine)

# 检查 iaas_servers 表
if 'iaas_servers' in inspector.get_table_names():
    columns = inspector.get_columns('iaas_servers')
    print(f'✓ iaas_servers 表存在')
    print(f'  字段数量: {len(columns)}')
    
    # 检查关键字段
    column_names = [c['name'] for c in columns]
    required_fields = ['bns_id', 'bns_hostname', 'rms_sn', 'nova_host_azone']
    missing = [f for f in required_fields if f not in column_names]
    
    if missing:
        print(f'  ❌ 缺少关键字段: {', '.join(missing)}')
        print(f'\n需要修复！运行: python3 fix_cmdb_schema.py')
        exit(1)
    else:
        print(f'  ✓ 关键字段完整')
else:
    print('❌ iaas_servers 表不存在')
    print(f'\n需要修复！运行: python3 fix_cmdb_schema.py')
    exit(1)

# 检查 iaas_instances 表
if 'iaas_instances' in inspector.get_table_names():
    columns = inspector.get_columns('iaas_instances')
    print(f'\n✓ iaas_instances 表存在')
    print(f'  字段数量: {len(columns)}')
    
    # 检查关键字段
    column_names = [c['name'] for c in columns]
    required_fields = ['bns_hostname', 'nova_vm_instance_uuid', 'nova_vm_vm_state']
    missing = [f for f in required_fields if f not in column_names]
    
    if missing:
        print(f'  ❌ 缺少关键字段: {', '.join(missing)}')
        print(f'\n需要修复！运行: python3 fix_cmdb_schema.py')
        exit(1)
    else:
        print(f'  ✓ 关键字段完整')
else:
    print('❌ iaas_instances 表不存在')
    print(f'\n需要修复！运行: python3 fix_cmdb_schema.py')
    exit(1)

print('\n' + '='*50)
print('✅ CMDB Schema 检查通过！')
print('='*50)
"
else
    # 在宿主机上
    echo "在宿主机上运行，将通过Docker容器检查..."
    docker exec -it cluster-backend bash -c "bash /app/check_cmdb_schema.sh"
fi
