"""
导入故障手册数据到数据库
从 knowledge/故障维修手册.csv 解析数据并导入
"""
import sys
import os
import csv
from pathlib import Path

# 添加项目根目录到路径
# 脚本位置: /app/backend/scripts/import_fault_manual.py
# 需要添加: /app
sys.path.insert(0, '/app')

from sqlalchemy.orm import Session
from app.core.deps import SessionLocal
from app.models.alert import FaultManual
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def parse_manual_file(file_path: str) -> list:
    """解析故障维修手册CSV文件"""
    records = []
    
    logger.info("开始解析CSV文件（使用utf-8-sig编码）")
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        logger.info(f"CSV表头: {reader.fieldnames}")
        
        for row in reader:
            try:
                record = {
                    'category': row['类别'],
                    'has_level': row['HAS级别'],
                    'name_zh': row['中文'],
                    'alert_type': row['项目'],
                    'impact': row['影响'],
                    'recovery_plan': row['恢复方案'],
                    'customer_aware': row['是否客户有感/需要通知客户操作维修'] == '是',
                    'danger_level': row['危害等级(云)'] if row['危害等级(云)'] else None,
                    'manual_check': row['手动判断方法'] if row.get('手动判断方法') else None
                }
                
                # 过滤空记录
                if record['alert_type'] and record['category']:
                    records.append(record)
            except Exception as e:
                logger.warning(f"解析行失败: {row.get('项目', 'unknown')} 错误: {e}")
                continue
    
    logger.info(f"解析完成，共 {len(records)} 条有效记录")
    if records:
        logger.info(f"前3条记录样本:")
        for i, r in enumerate(records[:3], 1):
            logger.info(f"  {i}. {r['category']} - {r['alert_type']} - {r['name_zh']}")
    
    return records


def import_manual_data(db: Session, records: list):
    """导入数据到数据库（先清空旧数据，内存去重）"""
    # 先删除所有旧数据
    logger.info("清空旧数据...")
    deleted_count = db.query(FaultManual).delete()
    logger.info(f"已删除 {deleted_count} 条旧记录")
    db.commit()
    
    # 内存去重（使用 category + alert_type 作为唯一键）
    seen = set()
    unique_records = []
    duplicate_count = 0
    
    for record in records:
        key = (record['category'], record['alert_type'])
        if key not in seen:
            seen.add(key)
            unique_records.append(record)
        else:
            duplicate_count += 1
            logger.debug(f"跳过重复记录: {record['category']}-{record['alert_type']}")
    
    logger.info(f"去重完成: 保留 {len(unique_records)} 条, 跳过重复 {duplicate_count} 条")
    
    # 导入新数据
    success_count = 0
    
    for record in unique_records:
        try:
            manual = FaultManual(**record)
            db.add(manual)
            success_count += 1
        except Exception as e:
            logger.error(f"导入记录失败: {record.get('alert_type')} - {e}")
            continue
    
    db.commit()
    logger.info(f"成功导入 {success_count} 条新记录")
    return success_count


def main():
    """主函数"""
    # 故障手册文件路径（优先使用CSV）
    # 脚本位置: /app/backend/scripts/import_fault_manual.py
    # 文件位置: /knowledge/故障维修手册.csv
    csv_file = Path('/knowledge/故障维修手册.csv')
    md_file = Path('/knowledge/故障维修手册.md')
    
    # 优先使用CSV文件
    if csv_file.exists():
        manual_file = csv_file
        logger.info(f"使用CSV文件: {manual_file}")
    elif md_file.exists():
        manual_file = md_file
        logger.info(f"使用MD文件（降级）: {manual_file}")
    else:
        logger.error("故障手册文件不存在（CSV和MD都未找到）")
        logger.error(f"  检查路径: {csv_file}")
        logger.error(f"  检查路径: {md_file}")
        return
    
    logger.info(f"开始解析故障手册: {manual_file}")
    records = parse_manual_file(str(manual_file))
    logger.info(f"解析完成,共 {len(records)} 条记录")
    
    if not records:
        logger.error("没有解析到任何记录，请检查CSV文件格式")
        return
    
    # 导入数据库
    db = SessionLocal()
    try:
        logger.info("开始导入数据库...")
        success = import_manual_data(db, records)
        logger.info(f"✅ 导入完成: 成功 {success} 条")
    except Exception as e:
        logger.error(f"❌ 导入失败: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
