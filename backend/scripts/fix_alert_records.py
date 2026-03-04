#!/usr/bin/env python3
"""
修复告警记录中的is_cce_cluster字段错误

问题：
- 有cluster_id但is_cce_cluster=False的记录
- 需要根据cluster_id重新设置is_cce_cluster字段
"""
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.deps import SessionLocal
from app.models.alert import AlertRecord
from sqlalchemy import and_

def fix_alert_records():
    """修复告警记录中的is_cce_cluster字段"""
    db = SessionLocal()
    
    try:
        # 查找所有有cluster_id但is_cce_cluster=False的记录
        wrong_records = db.query(AlertRecord).filter(
            and_(
                AlertRecord.cluster_id.isnot(None),
                AlertRecord.cluster_id.like('cce-%'),
                AlertRecord.is_cce_cluster == False
            )
        ).all()
        
        print(f"找到 {len(wrong_records)} 条需要修复的记录")
        
        # 修复每条记录
        fixed_count = 0
        for record in wrong_records:
            print(f"修复记录 ID={record.id}, 集群={record.cluster_id}, IP={record.ip}")
            record.is_cce_cluster = True
            fixed_count += 1
        
        # 提交更改
        db.commit()
        print(f"✅ 成功修复 {fixed_count} 条记录")
        
        # 验证修复结果
        print("\n验证修复结果（最近5条CCE记录）：")
        cce_records = db.query(AlertRecord).filter(
            AlertRecord.cluster_id.like('cce-%')
        ).order_by(AlertRecord.id.desc()).limit(5).all()
        
        for record in cce_records:
            status = "✅" if record.is_cce_cluster else "❌"
            print(f"{status} ID={record.id}, 集群={record.cluster_id}, IP={record.ip}, CCE={record.is_cce_cluster}")
        
    except Exception as e:
        print(f"❌ 修复失败: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_alert_records()
