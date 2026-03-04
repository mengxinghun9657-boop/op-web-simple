#!/usr/bin/env python3
"""
诊断告警处理流程

检查：
1. 数据库中的记录状态
2. 解析逻辑是否正确
3. 诊断判断逻辑是否正确

注意：此脚本使用测试路径，实际生产环境使用双卷架构：
- 源目录：/app/alerts_source（只读）
- 处理目录：/app/alerts（读写）
"""
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.deps import SessionLocal
from app.models.alert import AlertRecord, DiagnosisResult
from app.services.alert.parser import AlertParserService

def diagnose():
    """诊断告警处理流程"""
    db = SessionLocal()
    
    try:
        print("=" * 80)
        print("硬件告警诊断流程诊断")
        print("=" * 80)
        
        # 1. 检查数据库记录
        print("\n1. 数据库记录检查")
        print("-" * 80)
        
        total_count = db.query(AlertRecord).count()
        cce_count = db.query(AlertRecord).filter(AlertRecord.is_cce_cluster == True).count()
        cce_false_count = db.query(AlertRecord).filter(
            AlertRecord.cluster_id.like('cce-%'),
            AlertRecord.is_cce_cluster == False
        ).count()
        cce_no_ip = db.query(AlertRecord).filter(
            AlertRecord.is_cce_cluster == True,
            AlertRecord.ip.is_(None)
        ).count()
        
        print(f"总告警记录: {total_count}")
        print(f"CCE集群记录 (is_cce_cluster=True): {cce_count}")
        print(f"❌ 错误记录 (有cluster_id但is_cce_cluster=False): {cce_false_count}")
        print(f"⚠️ 缺少IP的CCE记录: {cce_no_ip}")
        
        # 2. 显示最近的记录
        print("\n2. 最近5条记录")
        print("-" * 80)
        
        recent = db.query(AlertRecord).order_by(AlertRecord.id.desc()).limit(5).all()
        for r in recent:
            status = "✅" if r.is_cce_cluster else "❌"
            has_ip = "✅" if r.ip else "❌"
            print(f"{status} ID={r.id}")
            print(f"   类型: {r.alert_type}")
            print(f"   集群: {r.cluster_id}")
            print(f"   IP: {r.ip} {has_ip}")
            print(f"   CCE: {r.is_cce_cluster}")
            print()
        
        # 3. 检查诊断结果
        print("3. 诊断结果检查")
        print("-" * 80)
        
        diagnosis_count = db.query(DiagnosisResult).count()
        with_api_task = db.query(DiagnosisResult).filter(
            DiagnosisResult.api_task_id.isnot(None)
        ).count()
        
        print(f"诊断结果记录: {diagnosis_count}")
        print(f"有API任务ID的记录: {with_api_task}")
        
        if with_api_task > 0:
            print("\n最近的诊断任务:")
            recent_diagnosis = db.query(DiagnosisResult).filter(
                DiagnosisResult.api_task_id.isnot(None)
            ).order_by(DiagnosisResult.id.desc()).limit(3).all()
            
            for d in recent_diagnosis:
                alert = db.query(AlertRecord).filter(AlertRecord.id == d.alert_id).first()
                print(f"  任务ID: {d.api_task_id}")
                print(f"  状态: {d.api_status}")
                print(f"  告警: {alert.alert_type if alert else 'N/A'}")
                print()
        
        # 4. 测试解析逻辑
        print("4. 测试解析逻辑")
        print("-" * 80)
        
        test_data = {
            'reason': 'TestError_Xid[99]',
            'case_dev': 'GPU',
            'case_dev_name': 'cce-test123-node01',
            'case_type': 'ERROR',
        }
        # 注意：测试使用旧路径，实际生产使用 /app/alerts_source 和 /app/alerts
        test_file = '/app/alerts/长安-cce-test123-node01-10.90.1.100.txt'
        
        records = AlertParserService._parse_alert(test_data, test_file)
        
        if records:
            r = records[0]
            print(f"测试解析结果:")
            print(f"  集群ID: {r['cluster_id']} {'✅' if r['cluster_id'] == 'cce-test123' else '❌'}")
            print(f"  IP地址: {r['ip']} {'✅' if r['ip'] == '10.90.1.100' else '❌'}")
            print(f"  是否CCE: {r['is_cce_cluster']} {'✅' if r['is_cce_cluster'] is True else '❌'}")
        else:
            print("❌ 解析失败")
        
        # 5. 诊断判断逻辑
        print("\n5. 诊断判断逻辑")
        print("-" * 80)
        
        if records:
            r = records[0]
            is_cce = r['is_cce_cluster']
            cluster_id = r['cluster_id']
            ip = r['ip']
            
            print(f"is_cce_cluster: {is_cce}")
            print(f"cluster_id: {cluster_id}")
            print(f"ip: {ip}")
            
            if is_cce:
                if cluster_id and ip:
                    print("✅ 应该加入诊断队列")
                else:
                    missing = []
                    if not cluster_id:
                        missing.append('cluster_id')
                    if not ip:
                        missing.append('ip')
                    print(f"⚠️ CCE集群但缺少必需字段: {missing}")
            else:
                print("📋 物理机节点，跳过诊断")
        
        print("\n" + "=" * 80)
        print("诊断完成")
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ 诊断失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    diagnose()
