#!/usr/bin/env python3
"""
检查告警记录的时间戳问题
"""
import sys
import os
from datetime import datetime, timezone

# 添加backend到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.core.deps import SessionLocal
from app.models.alert import AlertRecord

def check_timestamps():
    """检查告警记录的时间戳"""
    db = SessionLocal()
    
    try:
        print("=" * 60)
        print("检查告警记录的时间戳")
        print("=" * 60)
        
        # 查询所有告警记录
        alerts = db.query(AlertRecord).all()
        
        if not alerts:
            print("❌ 数据库中没有告警记录")
            return
        
        print(f"\n找到 {len(alerts)} 条告警记录:\n")
        
        for alert in alerts:
            print(f"ID: {alert.id}")
            print(f"alert_type: {alert.alert_type}")
            print(f"severity: {alert.severity}")
            print(f"timestamp: {alert.timestamp}")
            print(f"timestamp类型: {type(alert.timestamp)}")
            
            # 检查是否有时区信息
            if alert.timestamp.tzinfo is None:
                print(f"⚠️  时区信息: None (naive datetime)")
            else:
                print(f"✅ 时区信息: {alert.timestamp.tzinfo}")
            
            print(f"created_at: {alert.created_at}")
            print("-" * 60)
        
        # 模拟前端查询
        print("\n" + "=" * 60)
        print("模拟前端查询")
        print("=" * 60)
        
        # 前端传递的UTC时间
        start_time_utc = datetime(2026, 2, 18, 5, 21, 22, tzinfo=timezone.utc)
        end_time_utc = datetime(2026, 2, 25, 5, 21, 22, tzinfo=timezone.utc)
        
        print(f"\n前端传递的时间范围（UTC）:")
        print(f"start_time: {start_time_utc}")
        print(f"end_time: {end_time_utc}")
        
        # 转换为本地时间（UTC+8）
        from datetime import timedelta
        start_time_local = start_time_utc.replace(tzinfo=None)
        end_time_local = end_time_utc.replace(tzinfo=None)
        
        print(f"\n数据库查询条件（去除时区信息）:")
        print(f"start_time: {start_time_local}")
        print(f"end_time: {end_time_local}")
        
        # 执行查询
        results = db.query(AlertRecord).filter(
            AlertRecord.timestamp.between(start_time_local, end_time_local)
        ).all()
        
        print(f"\n查询结果: {len(results)} 条记录")
        
        if len(results) == 0:
            print("\n❌ 问题确认：时间范围不匹配！")
            print("\n原因分析：")
            print("1. 数据库存储的是本地时间（UTC+8）：2026-02-25 13:30:00")
            print("2. 前端传递的是UTC时间：2026-02-25T05:21:22Z")
            print("3. 查询条件：timestamp BETWEEN '2026-02-18 05:21:22' AND '2026-02-25 05:21:22'")
            print("4. 数据库中的时间 13:30:00 > 查询结束时间 05:21:22 ❌")
            
            print("\n解决方案：")
            print("1. 前端传递UTC时间时，后端需要转换为本地时间")
            print("2. 或者数据库统一存储UTC时间")
            print("3. 或者在查询时进行时区转换")
        else:
            print("\n✅ 查询成功！")
            for result in results:
                print(f"  - ID: {result.id}, timestamp: {result.timestamp}")
        
    finally:
        db.close()

if __name__ == "__main__":
    check_timestamps()
