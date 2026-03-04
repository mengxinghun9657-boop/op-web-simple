#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
降级策略服务

实现多层降级策略以保证服务可用性。

降级策略：
1. 意图分类降级：ERNIE API → 语义相似度 → 关键词规则
2. Schema RAG降级：向量检索 → 完整Schema（限制10表）
3. 报告缓存降级：Redis缓存 → MinIO直接读取
4. 知识库检索降级：向量检索 → 全文搜索（MySQL LIKE）

Validates: Requirements 10.4, 10.5, 2.8, 3.9, 16.5
"""

from typing import Optional, Dict, Any, List, Callable
from loguru import logger
import asyncio
from functools import wraps

from app.core.custom_exceptions import (
    DegradationError,
    ERNIEAPIError,
    VectorDatabaseError,
    ExternalServiceError
)


class DegradationService:
    """
    降级策略服务
    
    提供统一的降级处理接口，当主要服务不可用时自动切换到备用方案。
    """
    
    def __init__(self):
        self.degradation_stats = {
            "intent_classification": {"total": 0, "degraded": 0},
            "schema_rag": {"total": 0, "degraded": 0},
            "report_cache": {"total": 0, "degraded": 0},
            "knowledge_search": {"total": 0, "degraded": 0}
        }
    
    async def with_degradation(
        self,
        service_name: str,
        primary_func: Callable,
        fallback_func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        执行带降级的服务调用
        
        Args:
            service_name: 服务名称（用于日志和统计）
            primary_func: 主要服务函数
            fallback_func: 降级服务函数
            *args, **kwargs: 传递给服务函数的参数
        
        Returns:
            服务调用结果
        
        Validates: Requirements 10.4
        """
        self.degradation_stats[service_name]["total"] += 1
        
        try:
            # 尝试调用主要服务
            result = await primary_func(*args, **kwargs)
            return result
        
        except Exception as e:
            # 主要服务失败，切换到降级服务
            logger.warning(
                f"Service degradation: {service_name} primary failed, "
                f"switching to fallback. Error: {str(e)}"
            )
            
            self.degradation_stats[service_name]["degraded"] += 1
            
            try:
                result = await fallback_func(*args, **kwargs)
                logger.info(f"Service degradation: {service_name} fallback succeeded")
                return result
            
            except Exception as fallback_error:
                logger.error(
                    f"Service degradation: {service_name} fallback also failed. "
                    f"Error: {str(fallback_error)}"
                )
                raise ExternalServiceError(
                    message=f"{service_name}服务暂时不可用",
                    detail={"primary_error": str(e), "fallback_error": str(fallback_error)}
                )
    
    def get_degradation_stats(self) -> Dict[str, Any]:
        """
        获取降级统计信息
        
        Returns:
            降级统计数据
        """
        stats = {}
        for service, data in self.degradation_stats.items():
            total = data["total"]
            degraded = data["degraded"]
            stats[service] = {
                "total_calls": total,
                "degraded_calls": degraded,
                "degradation_rate": f"{(degraded / total * 100):.2f}%" if total > 0 else "0%"
            }
        return stats
    
    def reset_stats(self):
        """重置统计数据"""
        for service in self.degradation_stats:
            self.degradation_stats[service] = {"total": 0, "degraded": 0}


# ==================== 意图分类降级 ====================

class IntentClassificationDegradation:
    """
    意图分类降级策略
    
    降级链：ERNIE API → 语义相似度 → 关键词规则
    
    Validates: Requirements 2.8
    """
    
    def __init__(self):
        self.keyword_rules = {
            "sql": ["查询", "有多少", "统计", "列出", "显示", "数据库", "表", "字段"],
            "rag_report": ["报告", "分析", "最近", "上周", "昨天", "历史", "趋势"],
            "rag_knowledge": ["如何", "怎么", "处理", "解决", "故障", "问题", "经验", "最佳实践"],
            "chat": ["你好", "谢谢", "帮助", "介绍", "是什么"]
        }
    
    async def classify_by_keywords(self, query: str) -> Dict[str, Any]:
        """
        基于关键词的规则路由（最后的降级方案）
        
        Args:
            query: 用户查询文本
        
        Returns:
            意图分类结果
        
        Validates: Requirements 2.8
        """
        query_lower = query.lower()
        
        # 计算每种意图的匹配分数
        scores = {}
        for intent_type, keywords in self.keyword_rules.items():
            score = sum(1 for keyword in keywords if keyword in query_lower)
            scores[intent_type] = score
        
        # 选择得分最高的意图
        if max(scores.values()) == 0:
            # 没有匹配的关键词，默认为 chat
            intent_type = "chat"
            confidence = 0.3
        else:
            intent_type = max(scores, key=scores.get)
            # 置信度基于匹配的关键词数量
            confidence = min(0.5 + scores[intent_type] * 0.1, 0.7)
        
        logger.info(
            f"Intent classified by keywords: {intent_type} "
            f"(confidence: {confidence:.2f}, scores: {scores})"
        )
        
        return {
            "intent_type": intent_type,
            "confidence": confidence,
            "method": "keyword_rules"
        }


# ==================== Schema RAG 降级 ====================

class SchemaRAGDegradation:
    """
    Schema RAG 降级策略
    
    降级链：向量检索 → 完整Schema（限制10个常用表）
    
    Validates: Requirements 3.9
    """
    
    def __init__(self):
        # 定义最常用的10个表
        self.common_tables = [
            "users",
            "tasks",
            "iaas_servers",
            "iaas_instances",
            "audit_logs",
            "knowledge_entries",
            "report_index",
            "chat_history",
            "user_notes",
            "instance_config"
        ]
    
    async def get_common_tables_schema(
        self,
        user_permissions: List[str],
        schema_loader: Callable
    ) -> List[Dict[str, Any]]:
        """
        获取常用表的 Schema（降级方案）
        
        Args:
            user_permissions: 用户权限列表
            schema_loader: Schema 加载函数
        
        Returns:
            常用表的 Schema 列表（最多10个）
        
        Validates: Requirements 3.9
        """
        # 加载完整 Schema
        full_schema = await schema_loader()
        
        # 过滤出常用表且用户有权限的表
        filtered_schema = []
        for table in full_schema:
            if table["name"] in self.common_tables:
                # 检查用户权限
                if table["name"] in user_permissions or "admin" in user_permissions:
                    filtered_schema.append(table)
        
        # 限制为10个表
        result = filtered_schema[:10]
        
        logger.info(
            f"Schema RAG degradation: using {len(result)} common tables "
            f"(from {len(self.common_tables)} candidates)"
        )
        
        return result


# ==================== 报告缓存降级 ====================

class ReportCacheDegradation:
    """
    报告缓存降级策略
    
    降级链：Redis缓存 → MinIO直接读取
    
    Validates: Requirements 16.5
    """
    
    async def get_report_with_fallback(
        self,
        task_id: str,
        redis_client: Any,
        minio_client: Any,
        file_path: str
    ) -> str:
        """
        获取报告内容（带降级）
        
        Args:
            task_id: 任务ID
            redis_client: Redis 客户端
            minio_client: MinIO 客户端
            file_path: MinIO 文件路径
        
        Returns:
            报告内容
        
        Validates: Requirements 16.5
        """
        # 尝试从 Redis 缓存读取
        try:
            cache_key = f"report:{task_id}"
            cached_content = await redis_client.get(cache_key)
            
            if cached_content:
                logger.info(f"Report cache hit: {task_id}")
                return cached_content
        
        except Exception as e:
            logger.warning(f"Redis cache read failed: {str(e)}, falling back to MinIO")
        
        # 降级：直接从 MinIO 读取
        try:
            content = await minio_client.get_object(file_path)
            logger.info(f"Report loaded from MinIO (cache miss): {task_id}")
            
            # 尝试缓存到 Redis（失败不影响主流程）
            try:
                await redis_client.setex(cache_key, 86400, content)  # 24小时
            except Exception as cache_error:
                logger.warning(f"Failed to cache report: {str(cache_error)}")
            
            return content
        
        except Exception as e:
            logger.error(f"Failed to load report from MinIO: {str(e)}")
            raise ExternalServiceError(
                message="报告加载失败",
                detail={"task_id": task_id, "error": str(e)}
            )


# ==================== 知识库检索降级 ====================

class KnowledgeSearchDegradation:
    """
    知识库检索降级策略
    
    降级链：向量检索 → 全文搜索（MySQL LIKE）
    
    Validates: Requirements 22.7
    """
    
    async def search_by_fulltext(
        self,
        query: str,
        db_connection: Any,
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        使用全文搜索（MySQL LIKE）检索知识条目（降级方案）
        
        Args:
            query: 查询文本
            db_connection: 数据库连接
            top_k: 返回数量
        
        Returns:
            知识条目列表
        
        Validates: Requirements 22.7
        """
        cursor = db_connection.cursor()
        
        try:
            # 使用 LIKE 进行全文搜索
            search_pattern = f"%{query}%"
            
            cursor.execute("""
                SELECT id, title, content, category, tags, source, created_at
                FROM knowledge_entries
                WHERE deleted_at IS NULL
                  AND (title LIKE %s OR content LIKE %s)
                ORDER BY 
                    CASE 
                        WHEN title LIKE %s THEN 1
                        ELSE 2
                    END,
                    created_at DESC
                LIMIT %s
            """, (search_pattern, search_pattern, search_pattern, top_k))
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    "id": row[0],
                    "title": row[1],
                    "content": row[2],
                    "category": row[3],
                    "tags": row[4],
                    "source": row[5],
                    "created_at": row[6].isoformat() if row[6] else None,
                    "similarity": 0.5,  # 全文搜索没有相似度，给一个默认值
                    "method": "fulltext_search"
                })
            
            logger.info(
                f"Knowledge search degradation: fulltext search returned "
                f"{len(results)} results for query: {query}"
            )
            
            return results
        
        finally:
            cursor.close()


# ==================== 全局降级服务实例 ====================

_degradation_service = None


def get_degradation_service() -> DegradationService:
    """获取全局降级服务实例"""
    global _degradation_service
    if _degradation_service is None:
        _degradation_service = DegradationService()
    return _degradation_service


def get_intent_degradation() -> IntentClassificationDegradation:
    """获取意图分类降级实例"""
    return IntentClassificationDegradation()


def get_schema_degradation() -> SchemaRAGDegradation:
    """获取 Schema RAG 降级实例"""
    return SchemaRAGDegradation()


def get_report_cache_degradation() -> ReportCacheDegradation:
    """获取报告缓存降级实例"""
    return ReportCacheDegradation()


def get_knowledge_search_degradation() -> KnowledgeSearchDegradation:
    """获取知识库检索降级实例"""
    return KnowledgeSearchDegradation()
