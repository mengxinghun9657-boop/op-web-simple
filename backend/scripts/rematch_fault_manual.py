#!/usr/bin/env python3
"""
重新匹配已有告警的故障手册
用于在导入新手册后，为历史告警重新匹配故障手册
"""

import sys
import time
import logging
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """主函数：重新匹配已有告警"""

    # 带重试的数据库连接
    db = None
    for attempt in range(5):
        try:
            from sqlalchemy import text
            from app.core.deps import SessionLocal
            db = SessionLocal()
            db.execute(text("SELECT 1"))
            logger.info("✓ 数据库连接成功")
            break
        except Exception as e:
            if attempt < 4:
                logger.warning(f"数据库连接失败（尝试 {attempt+1}/5）: {e}，3秒后重试...")
                time.sleep(3)
            else:
                logger.error(f"数据库连接失败（已重试5次）: {e}")
                return 1

    try:
        from app.models.alert import AlertRecord, DiagnosisResult
        from app.services.alert.manual_matcher import ManualMatchService

        # 查询所有未匹配手册的告警
        unmatched = db.query(DiagnosisResult).filter(
            DiagnosisResult.manual_matched == False
        ).all()

        logger.info(f"发现 {len(unmatched)} 条未匹配手册的告警")

        if len(unmatched) > 0:
            matcher = ManualMatchService(db)
            success_count = 0

            for diagnosis in unmatched:
                alert = db.query(AlertRecord).filter(AlertRecord.id == diagnosis.alert_id).first()
                if not alert:
                    continue

                # 重新匹配手册
                manual = matcher.match(alert.alert_type, alert.component)
                if manual:
                    diagnosis.manual_matched = True
                    diagnosis.manual_name_zh = manual.get("name_zh")
                    diagnosis.manual_impact = manual.get("impact")
                    diagnosis.manual_recovery = manual.get("recovery")
                    diagnosis.manual_solution = manual.get("solution")
                    diagnosis.customer_aware = manual.get("customer_aware")
                    diagnosis.danger_level = manual.get("danger_level")
                    success_count += 1

            db.commit()
            logger.info(f"✅ 重新匹配完成: {success_count}/{len(unmatched)} 条成功")
        else:
            logger.info("✅ 所有告警已匹配手册")

        return 0

    except Exception as e:
        logger.error(f"重新匹配失败: {e}")
        if db:
            db.rollback()
        return 1
    finally:
        if db:
            db.close()

if __name__ == "__main__":
    sys.exit(main())
