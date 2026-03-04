#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Schema RAG 诊断脚本
用于快速诊断 Schema RAG 返回 0 结果的问题
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


async def diagnose():
    """诊断 Schema RAG"""
    
    print("=" * 80)
    print("Schema RAG 诊断工具")
    print("=" * 80)
    print()
    
    # 1. 检查 Embedding 模型
    print("📊 步骤 1: 检查 Embedding 模型")
    print("-" * 80)
    try:
        embedding_model = EmbeddingModel()
        health = await embedding_model.health_check()
        print(f"✅ Embedding 模型状态: {health}")
        
        # 测试向量化
        test_text = "测试文本：10.90.0.245 属于哪个集群"
        embedding = await embedding_model.encode(test_text)
        print(f"✅ 测试向量化成功，维度: {len(embedding)}")
        print()
    except Exception as e:
        print(f"❌ Embedding 模型错误: {e}")
        print()
        return
    
    # 2. 检查向量存储
    print("📊 步骤 2: 检查向量存储")
    print("-" * 80)
    try:
        vector_store = VectorStore()
        health = vector_store.health_check()
        print(f"向量存储状态:")
        for key, value in health.items():
            print(f"  - {key}: {value}")
        
        total_vectors = health.get("total_vectors", 0)
        if total_vectors == 0:
            print("❌ 警告：向量存储为空！")
            print("   可能原因：")
            print("   1. Schema 尚未加载")
            print("   2. 索引文件丢失")
            print("   3. Docker 卷未正确挂载")
        else:
            print(f"✅ 向量存储包含 {total_vectors} 个向量")
        print()
    except Exception as e:
        print(f"❌ 向量存储错误: {e}")
        print()
        return
    
    # 3. 检查 Schema 缓存
    print("📊 步骤 3: 检查 Schema 缓存")
    print("-" * 80)
    try:
        schema_store = SchemaVectorStore(
            embedding_model=embedding_model,
            vector_store=vector_store
        )
        
        # 尝试加载 Schema
        print("正在加载 Schema...")
        table_count = await schema_store.load_schema(force_refresh=False)
        print(f"✅ Schema 加载完成: {table_count} 个表")
        
        # 显示表列表
        all_tables = schema_store.get_all_tables()
        print(f"\n表列表（前 10 个）:")
        for i, table_name in enumerate(all_tables[:10], 1):
            print(f"  {i}. {table_name}")
        
        if len(all_tables) > 10:
            print(f"  ... 还有 {len(all_tables) - 10} 个表")
        print()
        
        # 检查关键表是否存在
        key_tables = [
            "mydb.bce_cce_nodes",
            "mydb.bce_bcc_instances",
            "mydb.cluster_stats"
        ]
        print("关键表检查:")
        for table in key_tables:
            if table in all_tables:
                print(f"  ✅ {table}")
            else:
                print(f"  ❌ {table} (缺失)")
        print()
        
    except Exception as e:
        print(f"❌ Schema 加载错误: {e}")
        import traceback
        traceback.print_exc()
        print()
        return
    
    # 4. 测试检索功能
    print("📊 步骤 4: 测试检索功能")
    print("-" * 80)
    
    test_queries = [
        "10.90.0.245 属于哪个集群",
        "实例ID查信息",
        "GPU监控数据",
        "BCC实例信息"
    ]
    
    for query in test_queries:
        print(f"\n查询: {query}")
        print("-" * 40)
        try:
            results = await schema_store.search(query, top_k=5)
            
            if results:
                print(f"✅ 返回 {len(results)} 个结果:")
                for i, result in enumerate(results, 1):
                    table_name = result.get("table_name", "unknown")
                    similarity = result.get("similarity", 0)
                    print(f"  {i}. {table_name} (相似度: {similarity:.4f})")
            else:
                print(f"❌ 无结果返回")
                print("   可能原因：")
                print("   1. 相似度阈值过高（当前: 0.3）")
                print("   2. 表描述语义不足")
                print("   3. 查询包含噪声（如 IP 地址）")
        except Exception as e:
            print(f"❌ 检索错误: {e}")
            import traceback
            traceback.print_exc()
    
    print()
    
    # 5. 测试原始向量检索（无阈值）
    print("📊 步骤 5: 测试原始向量检索（无阈值）")
    print("-" * 80)
    
    query = "10.90.0.245 属于哪个集群"
    print(f"查询: {query}")
    print()
    
    try:
        # 向量化查询
        query_embedding = await embedding_model.encode(query)
        
        # 原始检索（无阈值）
        raw_results = vector_store.search(
            query_embedding,
            top_k=10,
            similarity_threshold=0.0  # 无阈值
        )
        
        if raw_results:
            print(f"✅ 原始检索返回 {len(raw_results)} 个结果:")
            print("\nTop-10 相似度分数:")
            for i, result in enumerate(raw_results, 1):
                table_name = result["metadata"].get("table_name", "unknown")
                similarity = result.get("similarity", 0)
                print(f"  {i}. {table_name}: {similarity:.4f}")
            
            # 分析相似度分布
            similarities = [r.get("similarity", 0) for r in raw_results]
            max_sim = max(similarities)
            min_sim = min(similarities)
            avg_sim = sum(similarities) / len(similarities)
            
            print(f"\n相似度统计:")
            print(f"  - 最高: {max_sim:.4f}")
            print(f"  - 最低: {min_sim:.4f}")
            print(f"  - 平均: {avg_sim:.4f}")
            
            # 判断阈值是否合理
            if max_sim < 0.3:
                print(f"\n⚠️ 警告：最高相似度 {max_sim:.4f} 低于阈值 0.3")
                print("   建议：")
                print("   1. 降低相似度阈值到 0.2 或 0.1")
                print("   2. 增强表描述的语义信息")
                print("   3. 实现查询预处理（移除 IP 等噪声）")
            else:
                print(f"\n✅ 最高相似度 {max_sim:.4f} 高于阈值 0.3，检索应该成功")
        else:
            print(f"❌ 原始检索也无结果，向量存储可能为空")
    except Exception as e:
        print(f"❌ 原始检索错误: {e}")
        import traceback
        traceback.print_exc()
    
    print()
    
    # 6. 检查表描述质量
    print("📊 步骤 6: 检查表描述质量")
    print("-" * 80)
    
    key_table = "mydb.bce_cce_nodes"
    if key_table in schema_store.schema_cache:
        table_info = schema_store.schema_cache[key_table]
        description = table_info.get("description", "")
        
        print(f"表: {key_table}")
        print(f"描述:")
        print(description)
        print()
        
        # 检查描述是否包含关键信息
        checks = {
            "包含表用途": "用途:" in description or "table_purpose" in description,
            "包含查询场景": "场景" in description or "实例IP查集群" in description,
            "包含字段描述": "集群ID" in description or "cluster_id" in description,
        }
        
        print("描述质量检查:")
        for check_name, passed in checks.items():
            status = "✅" if passed else "❌"
            print(f"  {status} {check_name}")
        
        if not all(checks.values()):
            print("\n⚠️ 表描述质量不足，建议增强")
    else:
        print(f"❌ 表 {key_table} 不在缓存中")
    
    print()
    
    # 7. 总结和建议
    print("=" * 80)
    print("诊断总结")
    print("=" * 80)
    
    issues = []
    recommendations = []
    
    # 检查向量存储
    if total_vectors == 0:
        issues.append("向量存储为空")
        recommendations.append("运行 Schema 加载脚本")
    
    # 检查检索结果
    if not results:
        issues.append("检索无结果")
        recommendations.append("降低相似度阈值或增强表描述")
    
    # 检查相似度
    if raw_results and max_sim < 0.3:
        issues.append(f"最高相似度 {max_sim:.4f} 低于阈值")
        recommendations.append("实现查询预处理或降低阈值")
    
    # 检查表描述
    if not all(checks.values()):
        issues.append("表描述质量不足")
        recommendations.append("增强表描述的语义信息")
    
    if issues:
        print("\n发现的问题:")
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue}")
        
        print("\n建议的解决方案:")
        for i, rec in enumerate(recommendations, 1):
            print(f"  {i}. {rec}")
    else:
        print("\n✅ 未发现明显问题，Schema RAG 应该正常工作")
    
    print()
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(diagnose())
