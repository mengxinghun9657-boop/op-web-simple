#!/usr/bin/env python3
"""
检查告警记录的component字段和raw_data
"""
import sys
from pathlib import Path

# 添加backend路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.deps import SessionLocal
from app.models.alert import AlertRecord
import json

def check_component():
    """检查component字段"""
    db = SessionLocal()
    
    try:
        # 查询最新的告警记录
        alert = db.query(AlertRecord).order_by(AlertRecord.id.desc()).first()
        
        if not alert:
            print("❌ 数据库中没有告警记录")
            return
        
        print(f"📋 告警ID: {alert.id}")
        print(f"📋 告警类型: {alert.alert_type}")
        print(f"📋 组件类型: {alert.component}")
        print(f"📋 严重程度: {alert.severity}")
        print(f"📋 节点IP: {alert.ip}")
        print(f"📋 集群ID: {alert.cluster_id}")
        print()
        
        # 显示raw_data
        print("📦 原始数据 (raw_data):")
        if alert.raw_data:
            print(json.dumps(alert.raw_data, indent=2, ensure_ascii=False))
        else:
            print("  (空)")
        print()
        
        # 检查raw_data中是否有component相关字段
        if alert.raw_data:
            print("🔍 检查raw_data中的component相关字段:")
            component_keys = ['device_type', 'case_dev', '类别', 'component', 'category', 'type', 'device']
            found_keys = []
            for key in component_keys:
                if key in alert.raw_data:
                    found_keys.append(f"{key}={alert.raw_data[key]}")
            
            if found_keys:
                print(f"  找到: {', '.join(found_keys)}")
            else:
                print("  ❌ 未找到任何component相关字段")
        
    finally:
        db.close()

if __name__ == "__main__":
    check_component()
