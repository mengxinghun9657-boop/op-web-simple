#!/usr/bin/env python3
"""
检查告警记录的手册匹配情况
"""
import sys
from pathlib import Path

# 添加backend路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.deps import SessionLocal
from app.models.alert import AlertRecord, DiagnosisResult, FaultManual
import json

def check_manual_match():
    """检查手册匹配情况"""
    db = SessionLocal()
    
    try:
        # 查询最新的告警记录
        alert = db.query(AlertRecord).order_by(AlertRecord.id.desc()).first()
        
        if not alert:
            print("❌ 数据库中没有告警记录")
            return
        
        print(f"📋 告警ID: {alert.id}")
        print(f"📋 告警类型: {alert.alert_type}")
        print()
        
        # 查询诊断结果
        diagnosis = db.query(DiagnosisResult).filter(
            DiagnosisResult.alert_id == alert.id
        ).first()
        
        if not diagnosis:
            print("❌ 没有诊断结果")
            return
        
        print("🔍 诊断结果:")
        print(f"  manual_matched: {diagnosis.manual_matched}")
        print(f"  manual_name_zh: {diagnosis.manual_name_zh}")
        print(f"  manual_solution: {diagnosis.manual_solution}")
        print(f"  manual_impact: {diagnosis.manual_impact}")
        print(f"  manual_recovery: {diagnosis.manual_recovery}")
        print(f"  danger_level: {diagnosis.danger_level}")
        print(f"  customer_aware: {diagnosis.customer_aware}")
        print()
        
        # 检查故障手册表
        print("📚 检查故障手册表:")
        manual_count = db.query(FaultManual).count()
        print(f"  手册总数: {manual_count}")
        
        # 查询XID相关手册
        xid_manuals = db.query(FaultManual).filter(
            FaultManual.alert_type.like('%xid%')
        ).all()
        print(f"  XID手册数量: {len(xid_manuals)}")
        
        if xid_manuals:
            print("\n  XID手册列表:")
            for manual in xid_manuals[:5]:  # 只显示前5个
                print(f"    - {manual.alert_type}: {manual.name_zh}")
        
        # 尝试匹配当前告警
        print(f"\n🔍 尝试匹配告警类型: {alert.alert_type}")
        
        # 精确匹配
        exact_match = db.query(FaultManual).filter(
            FaultManual.alert_type == alert.alert_type
        ).first()
        
        if exact_match:
            print(f"  ✅ 精确匹配成功: {exact_match.name_zh}")
        else:
            print(f"  ❌ 精确匹配失败")
            
            # 尝试模糊匹配
            alert_type_lower = alert.alert_type.lower()
            fuzzy_matches = db.query(FaultManual).filter(
                FaultManual.alert_type.like(f'%{alert_type_lower}%')
            ).all()
            
            if fuzzy_matches:
                print(f"  ⚠️  找到 {len(fuzzy_matches)} 个模糊匹配:")
                for match in fuzzy_matches[:3]:
                    print(f"    - {match.alert_type}: {match.name_zh}")
            else:
                print(f"  ❌ 模糊匹配也失败")
        
    finally:
        db.close()

if __name__ == "__main__":
    check_manual_match()
