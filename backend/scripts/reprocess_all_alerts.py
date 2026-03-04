#!/usr/bin/env python3
"""
清理数据库并重新处理所有告警文件

用途：
- 删除所有现有告警记录和诊断结果
- 重新处理/app/alerts目录下的所有文件
- 验证处理结果
"""
import sys
import os
import asyncio

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.deps import SessionLocal
from app.models.alert import AlertRecord, DiagnosisResult
from app.services.alert.file_watcher import FileWatcherService

async def reprocess_all_alerts():
    """清理并重新处理所有告警"""
    db = SessionLocal()
    
    try:
        # 1. 统计现有记录
        alert_count = db.query(AlertRecord).count()
        diagnosis_count = db.query(DiagnosisResult).count()
        print(f"现有记录: {alert_count} 条告警, {diagnosis_count} 条诊断结果")
        
        # 2. 删除所有记录
        print("\n删除所有现有记录...")
        db.query(DiagnosisResult).delete()
        db.query(AlertRecord).delete()
        db.commit()
        print("✅ 删除完成")
        
        # 3. 重新处理所有文件
        print("\n开始重新处理所有告警文件...")
        service = FileWatcherService(db)
        service.process_existing_files()
        
        # 4. 等待处理完成（给异步任务足够时间）
        print("\n等待处理完成（最多60秒）...")
        await asyncio.sleep(60)
        
        # 5. 验证处理结果
        print("\n验证处理结果:")
        new_alert_count = db.query(AlertRecord).count()
        new_diagnosis_count = db.query(DiagnosisResult).count()
        print(f"新记录: {new_alert_count} 条告警, {new_diagnosis_count} 条诊断结果")
        
        # 6. 显示CCE集群记录
        print("\nCCE集群记录（前10条）:")
        cce_records = db.query(AlertRecord).filter(
            AlertRecord.is_cce_cluster == True
        ).limit(10).all()
        
        for record in cce_records:
            has_ip = "✅" if record.ip else "❌"
            print(f"{has_ip} ID={record.id}, 类型={record.alert_type}, 集群={record.cluster_id}, IP={record.ip}")
        
        # 7. 显示缺少IP的CCE记录
        print("\n缺少IP的CCE记录:")
        no_ip_records = db.query(AlertRecord).filter(
            AlertRecord.is_cce_cluster == True,
            AlertRecord.ip.is_(None)
        ).all()
        
        if no_ip_records:
            print(f"⚠️ 发现 {len(no_ip_records)} 条缺少IP的CCE记录")
            for record in no_ip_records[:5]:
                print(f"  ID={record.id}, 类型={record.alert_type}, 集群={record.cluster_id}")
        else:
            print("✅ 所有CCE记录都有IP地址")
        
    except Exception as e:
        print(f"❌ 处理失败: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(reprocess_all_alerts())
