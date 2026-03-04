#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
快速检查向量化状态

用途：一键检查向量化是否成功，包括：
1. 向量数据库状态
2. MySQL 数据库中的原始文本
3. 向量数组的有效性
"""

import sys
import os
import numpy as np

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.ai.vector_store import VectorStore
from app.core.database import get_db_connection
from app.core.logger import logger


def check_vectorization_status():
    """检查向量化状态"""
    print("=" * 80)
    print("向量化状态检查")
    print("=" * 80)
    
    all_passed = True
    
    # 1. 检查向量数据库
    print("\n【1. 向量数据库检查】")
    try:
        vector_store = VectorStore()
        health = vector_store.health_check()
        
        print(f"状态: {health.get('status')}")
        print(f"向量总数: {health.get('total_vectors')}")
        print(f"向量维度: {health.get('dimension')}")
        
        if health.get('status') != 'healthy':
            print("❌ 向量数据库不健康")
            all_passed = False
        elif health.get('total_vectors') == 0:
            print("⚠️  向量数据库为空")
            all_passed = False
        else:
            print("✅ 向量数据库正常")
            
            # 检查第一个向量
            try:
                first_vector_id = min(vector_store.id_map.keys())
                vector = vector_store.index.reconstruct(int(first_vector_id))
                
                # 检查向量是否全0
                if np.all(vector == 0):
                    print("❌ 向量全是0，向量化失败")
                    all_passed = False
                else:
                    # 检查是否归一化
                    norm = np.linalg.norm(vector)
                    is_normalized = abs(norm - 1.0) < 0.01
                    
                    if is_normalized:
                        print(f"✅ 向量已正确归一化 (L2范数={norm:.6f})")
                    else:
                        print(f"⚠️  向量未归一化 (L2范数={norm:.6f})")
                        all_passed = False
                    
                    # 显示向量样本
                    print(f"向量样本（前5个数值）: {vector[:5]}")
                    
            except Exception as e:
                print(f"❌ 无法读取向量: {e}")
                all_passed = False
                
    except Exception as e:
        print(f"❌ 向量数据库检查失败: {e}")
        all_passed = False
    
    # 2. 检查 MySQL 数据库
    print("\n【2. MySQL 数据库检查】")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 检查 report_index 表
        cursor.execute("""
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN vectorized = TRUE THEN 1 ELSE 0 END) as vectorized_count
            FROM report_index
        """)
        result = cursor.fetchone()
        total_reports = result[0]
        vectorized_reports = result[1]
        
        print(f"报告总数: {total_reports}")
        print(f"已向量化: {vectorized_reports}")
        
        if total_reports == 0:
            print("⚠️  没有报告数据")
            all_passed = False
        elif vectorized_reports == 0:
            print("❌ 没有向量化的报告")
            all_passed = False
        else:
            print("✅ 有向量化的报告")
            
            # 检查原始文本内容
            cursor.execute("""
                SELECT task_id, report_type, 
                       LEFT(summary, 50) as summary_preview,
                       LEFT(conclusion, 50) as conclusion_preview
                FROM report_index
                WHERE vectorized = TRUE
                LIMIT 3
            """)
            
            print("\n原始文本样本:")
            for row in cursor.fetchall():
                task_id, report_type, summary, conclusion = row
                print(f"\n  Task ID: {task_id}")
                print(f"  Type: {report_type}")
                print(f"  Summary: {summary}...")
                print(f"  Conclusion: {conclusion}...")
                
                # 检查是否是默认文本
                default_texts = [
                    'BOS 存储分析报告', 'BOS 存储分析完成',
                    '资源分析报告', '集群资源分析完成',
                    'BCC 监控报告', 'BCC 实例监控分析完成',
                    '运营数据分析报告', '运营数据分析完成'
                ]
                
                if summary in default_texts or conclusion in default_texts:
                    print(f"  ⚠️  检测到默认文本，内容提取可能失败")
                    all_passed = False
                else:
                    print(f"  ✅ 内容提取正常")
        
        # 检查 knowledge_entries 表
        cursor.execute("""
            SELECT COUNT(*) as total
            FROM knowledge_entries
            WHERE source = 'auto'
        """)
        result = cursor.fetchone()
        auto_entries = result[0]
        
        print(f"\n自动创建的知识条目: {auto_entries}")
        
        if auto_entries == 0:
            print("⚠️  没有自动创建的知识条目")
            all_passed = False
        else:
            print("✅ 有自动创建的知识条目")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ MySQL 数据库检查失败: {e}")
        all_passed = False
    
    # 3. 总结
    print("\n" + "=" * 80)
    if all_passed:
        print("✅ 向量化状态检查通过")
        print("\n所有检查项都正常，向量化成功！")
    else:
        print("❌ 向量化状态检查失败")
        print("\n发现问题，请检查上述错误信息")
        print("\n可能的原因:")
        print("1. 向量化过程失败（Embedding API 调用失败）")
        print("2. 内容提取失败（HTML 解析错误）")
        print("3. 向量存储失败（FAISS 索引写入失败）")
        print("4. 数据库更新失败（MySQL 写入失败）")
        print("\n建议:")
        print("1. 查看后端日志: docker logs cluster-backend --tail 200")
        print("2. 重新向量化: 参考 ALL_REPORTS_FIX_SUMMARY.md")
        print("3. 检查 Embedding API 是否可用")
    print("=" * 80)


if __name__ == '__main__':
    check_vectorization_status()
