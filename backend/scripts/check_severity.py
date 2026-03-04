#!/usr/bin/env python3
"""
检查数据库中告警记录的severity字段值
"""
import sys
import os

# 添加backend目录到Python路径
backend_path = os.path.join(os.path.dirname(__file__), 'backend')
sys.path.insert(0, backend_path)

from app.core.deps import SessionLocal
from app.models.alert import AlertRecord
from sqlalchemy import func

db = SessionLocal()

try:
    # 统计不同severity值的数量
    severity_stats = db.query(
        AlertRecord.severity,
        func.count(AlertRecord.id).label('count')
    ).group_by(AlertRecord.severity).all()
    
    print("=" * 60)
    print("数据库中告警记录的severity字段统计:")
    print("=" * 60)
    
    if not severity_stats:
        print("❌ 数据库中没有告警记录！")
    else:
        for severity, count in severity_stats:
            print(f"{severity}: {count} 条")
    
    print("\n" + "=" * 60)
    print("统计API期望的severity值:")
    print("=" * 60)
    print("ERROR → critical")
    print("FAIL/WARN → warning")
    print("GOOD → info")
    
    print("\n" + "=" * 60)
    print("示例告警记录:")
    print("=" * 60)
    sample = db.query(AlertRecord).first()
    if sample:
        print(f"ID: {sample.id}")
        print(f"alert_type: {sample.alert_type}")
        print(f"severity: {sample.severity}")
        print(f"component: {sample.component}")
        print(f"timestamp: {sample.timestamp}")
    else:
        print("❌ 没有告警记录")
    
finally:
    db.close()
