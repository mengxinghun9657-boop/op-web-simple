#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
清理重复的知识条目

问题：同一个报告可能被创建了多个知识条目
解决：保留最早创建的，删除其他重复的
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.database import get_db_connection
from app.core.logger import logger


def cleanup_duplicate_entries():
    """清理重复的知识条目"""
    
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. 查找重复的记录
        logger.info("🔍 查找重复的知识条目...")
        cursor.execute("""
            SELECT source_id, COUNT(*) as count
            FROM knowledge_entries
            WHERE source = 'auto' AND deleted_at IS NULL
            GROUP BY source_id
            HAVING count > 1
        """)
        
        duplicates = cursor.fetchall()
        
        if not duplicates:
            logger.info("✅ 没有发现重复的知识条目")
            return
        
        logger.info(f"⚠️ 发现 {len(duplicates)} 个重复的 source_id")
        
        total_deleted = 0
        
        # 2. 对每个重复的 source_id，保留最早创建的，删除其他的
        for source_id, count in duplicates:
            logger.info(f"  处理 source_id={source_id}, 重复数量={count}")
            
            # 查找该 source_id 的所有记录（按创建时间排序）
            cursor.execute("""
                SELECT id, title, created_at
                FROM knowledge_entries
                WHERE source = 'auto' AND source_id = %s AND deleted_at IS NULL
                ORDER BY created_at ASC
            """, (source_id,))
            
            entries = cursor.fetchall()
            
            # 保留第一个（最早创建的）
            keep_id = entries[0][0]
            keep_title = entries[0][1]
            keep_created_at = entries[0][2]
            
            logger.info(f"    ✓ 保留: ID={keep_id}, 标题={keep_title}, 创建时间={keep_created_at}")
            
            # 删除其他的（软删除）
            for entry in entries[1:]:
                entry_id = entry[0]
                entry_title = entry[1]
                entry_created_at = entry[2]
                
                cursor.execute("""
                    UPDATE knowledge_entries
                    SET deleted_at = NOW()
                    WHERE id = %s
                """, (entry_id,))
                
                logger.info(f"    ✗ 删除: ID={entry_id}, 标题={entry_title}, 创建时间={entry_created_at}")
                total_deleted += 1
        
        # 3. 提交更改
        conn.commit()
        
        logger.info(f"✅ 清理完成: 删除了 {total_deleted} 个重复的知识条目")
        
        # 4. 显示清理后的统计
        cursor.execute("""
            SELECT COUNT(*) as total
            FROM knowledge_entries
            WHERE source = 'auto' AND deleted_at IS NULL
        """)
        
        total = cursor.fetchone()[0]
        logger.info(f"📊 当前有效的自动知识条目数量: {total}")
        
        cursor.close()
        
    except Exception as e:
        logger.error(f"❌ 清理失败: {e}")
        if conn:
            conn.rollback()
        raise
    
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("清理重复的知识条目")
    logger.info("=" * 60)
    
    cleanup_duplicate_entries()
    
    logger.info("=" * 60)
    logger.info("清理完成")
    logger.info("=" * 60)
