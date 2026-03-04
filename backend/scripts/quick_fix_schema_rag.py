#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Schema RAG 快速修复脚本
实现最关键的优化：增强表描述 + 降低阈值
"""

import asyncio
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.ai.schema_vector_store import SchemaVectorStore
from app.services.ai.vector_store import VectorStore
from app.services.ai.embedding_model import EmbeddingModel
from app.core.logger import logger


async def quick_fix():
    """快速修复 Schema RAG"""
    
    print("=" * 80)
    print("Schema RAG 快速修复工具")
    print("=" * 80)
    print()
    
    print("🔧 修复内容:")
    print("  1. 清空现有向量存储")
    print("  2. 使用增强的表描述重新加载 Schema")
    print("  3. 验证修复效果")
    print()
    
    input("按 Enter 键继续...")
    print()
    
    # 1. 清空向量存储
    print("📊 步骤 1: 清空向量存储")
    print("-" * 80)
    try:
        vector_store = VectorStore()
        vector_store.clear()
        print("✅ 向量存储已清空")
        print()
    except Exception as e:
        print(f"❌ 清空失败: {e}")
        return
    
    # 2. 重新加载 Schema（使用增强的描述）
    print("📊 步骤 2: 重新加载 Schema")
    print("-" * 80)
    try:
        embedding_model = EmbeddingModel()
        schema_store = SchemaVectorStore(
            embedding_model=embedding_model,
            vector_store=vector_store
        )
        
        print("正在加载 Schema（包含主库和宿主机库）...")
        table_count = await schema_store.load_schema(
            force_refresh=True,
            include_secondary=True
        )
        print(f"✅ Schema 加载完成: {table_count} 个表")
        
        # 验证向量存储
        health = vector_store.health_check()
        total_vectors = health.get("total_vectors", 0)
        print(f"✅ 向量存储包含 {total_vectors} 个向量")
        print()
        
        if total_vectors == 0:
            print("❌ 警告：向量存储仍然为空！")
            return
        
    except Exception as e:
        print(f"❌ 加载失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 3. 验证修复效果
    print("📊 步骤 3: 验证修复效果")
    print("-" * 80)
    
    test_cases = [
        {
            "query": "10.90.0.245 属于哪个集群",
            "expected_table": "bce_cce_nodes",
            "threshold": 0.2  # 降低阈值
        },
        {
            "query": "实例ID查信息",
            "expected_table": "bce_bcc_instances",
            "threshold": 0.2
        },
        {
            "query": "GPU监控数据",
            "expected_table": "gpu_metrics",
            "threshold": 0.2
        }
    ]
    
    success_count = 0
    
    for i, test_case in enumerate(test_cases, 1):
        query = test_case["query"]
        expected_table = test_case["expected_table"]
        threshold = test_case["threshold"]
        
        print(f"\n测试 {i}: {query}")
        print(f"期望表: {expected_table}")
        print(f"阈值: {threshold}")
        print("-" * 40)
        
        try:
            # 使用降低的阈值检索
            query_embedding = await embedding_model.encode(query)
            results = vector_store.search(
                query_embedding,
                top_k=5,
                similarity_threshold=threshold
            )
            
            if results:
                print(f"✅ 返回 {len(results)} 个结果:")
                
                found = False
                for j, result in enumerate(results, 1):
                    table_name = result["metadata"].get("table_name", "unknown")
                    similarity = result.get("similarity", 0)
                    
                    # 检查是否包含期望的表
                    if expected_table in table_name:
                        print(f"  {j}. {table_name} (相似度: {similarity:.4f}) ✅")
                        found = True
                    else:
                        print(f"  {j}. {table_name} (相似度: {similarity:.4f})")
                
                if found:
                    print(f"✅ 测试通过：找到期望的表")
                    success_count += 1
                else:
                    print(f"❌ 测试失败：未找到期望的表")
            else:
                print(f"❌ 无结果返回")
                
                # 尝试无阈值检索
                print("\n尝试无阈值检索...")
                raw_results = vector_store.search(
                    query_embedding,
                    top_k=5,
                    similarity_threshold=0.0
                )
                
                if raw_results:
                    print(f"无阈值检索返回 {len(raw_results)} 个结果:")
                    for j, result in enumerate(raw_results, 1):
                        table_name = result["metadata"].get("table_name", "unknown")
                        similarity = result.get("similarity", 0)
                        print(f"  {j}. {table_name} (相似度: {similarity:.4f})")
                else:
                    print("无阈值检索也无结果")
        
        except Exception as e:
            print(f"❌ 测试错误: {e}")
            import traceback
            traceback.print_exc()
    
    print()
    print("=" * 80)
    print("修复总结")
    print("=" * 80)
    print(f"测试通过: {success_count}/{len(test_cases)}")
    
    if success_count == len(test_cases):
        print("✅ 所有测试通过，修复成功！")
    elif success_count > 0:
        print("⚠️ 部分测试通过，可能需要进一步优化")
        print("\n建议:")
        print("  1. 进一步降低相似度阈值（如 0.1）")
        print("  2. 增强表描述的语义信息")
        print("  3. 实现查询预处理（移除 IP 等噪声）")
    else:
        print("❌ 所有测试失败，需要深入排查")
        print("\n建议:")
        print("  1. 检查 Embedding API 是否正常")
        print("  2. 检查表描述是否正确生成")
        print("  3. 运行诊断脚本获取详细信息")
    
    print()
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(quick_fix())
