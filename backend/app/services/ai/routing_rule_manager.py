#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
路由规则管理器（Routing Rule Manager）

实现需求：
- Requirements 2.2: 创建路由规则并向量化存储到 FAISS 索引
- Requirements 2.5: 支持路由规则的增删改查操作
- Requirements 2.6: 在路由规则变更时自动更新向量索引
- Requirements 2.3: 检索路由规则知识库
- Requirements 8.1, 8.2: 规则优先级管理
"""

from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, or_, select, func

from app.core.logger import logger
from app.models.routing_rule import RoutingRule
from app.services.ai.embedding_model import EmbeddingModel
from app.services.ai.vector_store import VectorStore


class RoutingRuleManager:
    """路由规则管理器"""
    
    def __init__(
        self,
        db,
        embedding_model: Optional[EmbeddingModel] = None,
        vector_store_path: str = "/app/vector_store/routing_rules"
    ):
        """
        初始化路由规则管理器
        
        Args:
            db: 数据库会话 (AsyncSession 或 Session)
            embedding_model: Embedding 模型
            vector_store_path: 向量存储路径
        """
        self.db = db
        self.is_async = isinstance(db, AsyncSession)
        self.embedding_model = embedding_model or EmbeddingModel()
        self.vector_store = VectorStore(index_path=vector_store_path)
        
        logger.info("✅ 路由规则管理器初始化成功")
    
    async def create_rule(
        self,
        pattern: str,
        intent_type: str,
        priority: int = 50,
        description: Optional[str] = None,
        metadata: Optional[Dict] = None,
        created_by: Optional[str] = None
    ) -> RoutingRule:
        """
        创建路由规则
        
        Args:
            pattern: 查询模式
            intent_type: 意图类型
            priority: 优先级(1-100)
            description: 规则描述
            metadata: 规则元数据（推荐的表、数据库等）
            created_by: 创建者
        
        Returns:
            创建的规则对象
        
        Validates: Requirements 2.2
        """
        try:
            # 1. 创建数据库记录
            rule = RoutingRule(
                pattern=pattern,
                intent_type=intent_type,
                priority=priority,
                description=description,
                rule_metadata=metadata,  # 使用 rule_metadata 字段
                created_by=created_by
            )
            
            self.db.add(rule)
            
            if self.is_async:
                await self.db.commit()
                await self.db.refresh(rule)
            else:
                self.db.commit()
                self.db.refresh(rule)
            
            logger.info(f"✅ 创建路由规则: id={rule.id}, pattern={pattern}")
            
            # 2. 向量化并存储到 FAISS 索引
            await self._add_to_vector_store(rule)
            
            return rule
            
        except Exception as e:
            if self.is_async:
                await self.db.rollback()
            else:
                self.db.rollback()
            logger.error(f"❌ 创建路由规则失败: {e}")
            raise
    
    async def update_rule(
        self,
        rule_id: int,
        pattern: Optional[str] = None,
        intent_type: Optional[str] = None,
        priority: Optional[int] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict] = None,
        is_active: Optional[bool] = None
    ) -> Optional[RoutingRule]:
        """
        更新路由规则
        
        Args:
            rule_id: 规则ID
            pattern: 查询模式
            intent_type: 意图类型
            priority: 优先级
            description: 规则描述
            metadata: 规则元数据
            is_active: 是否启用
        
        Returns:
            更新后的规则对象，如果不存在返回 None
        
        Validates: Requirements 2.5, 2.6
        """
        try:
            # 1. 查询规则
            stmt = select(RoutingRule).filter(RoutingRule.id == rule_id)
            
            if self.is_async:
                result = await self.db.execute(stmt)
                rule = result.scalar_one_or_none()
            else:
                result = self.db.execute(stmt)
                rule = result.scalar_one_or_none()
            
            if not rule:
                logger.warning(f"⚠️ 规则不存在: id={rule_id}")
                return None
            
            # 2. 更新字段
            if pattern is not None:
                rule.pattern = pattern
            if intent_type is not None:
                rule.intent_type = intent_type
            if priority is not None:
                rule.priority = priority
            if description is not None:
                rule.description = description
            if metadata is not None:
                rule.rule_metadata = metadata  # 使用 rule_metadata 字段
            if is_active is not None:
                rule.is_active = is_active
            
            if self.is_async:
                await self.db.commit()
                await self.db.refresh(rule)
            else:
                self.db.commit()
                self.db.refresh(rule)
            
            logger.info(f"✅ 更新路由规则: id={rule_id}")
            
            # 3. 重新向量化并更新索引
            if pattern is not None:
                await self._update_vector_store(rule)
            
            return rule
            
        except Exception as e:
            if self.is_async:
                await self.db.rollback()
            else:
                self.db.rollback()
            logger.error(f"❌ 更新路由规则失败: {e}")
            raise
    
    async def delete_rule(self, rule_id: int) -> bool:
        """
        删除路由规则
        
        Args:
            rule_id: 规则ID
        
        Returns:
            是否删除成功
        
        Validates: Requirements 2.5, 2.6
        """
        try:
            # 1. 查询规则
            stmt = select(RoutingRule).filter(RoutingRule.id == rule_id)
            
            if self.is_async:
                result = await self.db.execute(stmt)
                rule = result.scalar_one_or_none()
            else:
                result = self.db.execute(stmt)
                rule = result.scalar_one_or_none()
            
            if not rule:
                logger.warning(f"⚠️ 规则不存在: id={rule_id}")
                return False
            
            # 2. 从向量索引中移除
            self._remove_from_vector_store(rule_id)
            
            # 3. 删除数据库记录
            if self.is_async:
                await self.db.delete(rule)
                await self.db.commit()
            else:
                self.db.delete(rule)
                self.db.commit()
            
            logger.info(f"✅ 删除路由规则: id={rule_id}")
            
            return True
            
        except Exception as e:
            if self.is_async:
                await self.db.rollback()
            else:
                self.db.rollback()
            logger.error(f"❌ 删除路由规则失败: {e}")
            raise
    
    async def get_rule(self, rule_id: int) -> Optional[Dict]:
        """
        获取单个路由规则
        
        Args:
            rule_id: 规则ID
        
        Returns:
            规则字典
        
        Validates: Requirements 2.5
        """
        stmt = select(RoutingRule).filter(RoutingRule.id == rule_id)
        
        if self.is_async:
            result = await self.db.execute(stmt)
            rule = result.scalar_one_or_none()
        else:
            result = self.db.execute(stmt)
            rule = result.scalar_one_or_none()
        
        if not rule:
            return None
        
        return rule.to_dict()
    
    async def list_rules(
        self,
        intent_type: Optional[str] = None,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 20,
        page: Optional[int] = None,
        page_size: Optional[int] = None
    ) -> Dict:
        """
        获取路由规则列表
        
        Args:
            intent_type: 意图类型过滤
            is_active: 是否启用过滤
            skip: 跳过的记录数（与page互斥）
            limit: 返回的记录数（与page_size互斥）
            page: 页码（从1开始，与skip互斥）
            page_size: 每页数量（与limit互斥）
        
        Returns:
            分页格式的规则列表字典
        
        Validates: Requirements 2.5
        """
        # 支持 page/page_size 参数
        if page is not None and page_size is not None:
            skip = (page - 1) * page_size
            limit = page_size
        
        # 构建查询
        stmt = select(RoutingRule)
        
        # 过滤条件
        filters = []
        if intent_type:
            filters.append(RoutingRule.intent_type == intent_type)
        if is_active is not None:
            filters.append(RoutingRule.is_active == is_active)
        
        if filters:
            stmt = stmt.filter(and_(*filters))
        
        # 获取总数
        count_stmt = select(func.count(RoutingRule.id))
        if filters:
            count_stmt = count_stmt.filter(and_(*filters))
        
        if self.is_async:
            result = await self.db.execute(count_stmt)
            total = result.scalar()
        else:
            result = self.db.execute(count_stmt)
            total = result.scalar()
        
        # 排序和分页
        stmt = stmt.order_by(RoutingRule.priority.desc(), RoutingRule.created_at.desc())\
                   .offset(skip)\
                   .limit(limit)
        
        if self.is_async:
            result = await self.db.execute(stmt)
            rules = result.scalars().all()
        else:
            result = self.db.execute(stmt)
            rules = result.scalars().all()
        
        # 返回分页格式
        return {
            "list": [rule.to_dict() for rule in rules],
            "total": total,
            "page": page if page is not None else (skip // limit + 1 if limit > 0 else 1),
            "page_size": page_size if page_size is not None else limit
        }
    
    async def search_rules(
        self,
        query: str,
        similarity_threshold: float = 0.7,
        top_k: int = 3
    ) -> List[Dict]:
        """
        检索匹配的路由规则
        
        Args:
            query: 查询文本
            similarity_threshold: 相似度阈值
            top_k: 返回前 K 个结果
        
        Returns:
            匹配的规则列表（按优先级排序）
        
        Validates: Requirements 2.3, 2.4, 8.1, 8.2
        """
        try:
            # 1. 向量化查询
            query_embedding = await self.embedding_model.encode(query)
            
            # 2. 在向量索引中检索（修复：移除 await，修正参数名）
            results = self.vector_store.search(
                query_embedding=query_embedding,
                top_k=top_k * 2,  # 多检索一些，后面按优先级过滤
                similarity_threshold=similarity_threshold  # 修复：使用正确的参数名
            )
            
            if not results:
                return []
            
            # 3. 获取规则详情（修复：使用正确的字段名 entry_id）
            rule_ids = [r["entry_id"] for r in results]
            stmt = select(RoutingRule).filter(and_(
                RoutingRule.id.in_(rule_ids),
                RoutingRule.is_active == True
            ))
            
            if self.is_async:
                result = await self.db.execute(stmt)
                rules = result.scalars().all()
            else:
                result = self.db.execute(stmt)
                rules = result.scalars().all()
            
            # 4. 合并相似度和规则信息（修复：使用正确的字段名 similarity）
            rule_dict = {rule.id: rule for rule in rules}
            matched_rules = []
            
            for result in results:
                rule_id = result["entry_id"]  # 修复：使用 entry_id
                if rule_id in rule_dict:
                    rule = rule_dict[rule_id]
                    matched_rules.append({
                        **rule.to_dict(),
                        "similarity": result["similarity"]  # 修复：使用 similarity
                    })
            
            # 5. 按优先级排序（优先级高的在前）
            matched_rules.sort(key=lambda x: (x["priority"], x["similarity"]), reverse=True)
            
            # 6. 返回前 top_k 个
            return matched_rules[:top_k]
            
        except Exception as e:
            logger.error(f"❌ 检索路由规则失败: {e}")
            return []
    
    async def _add_to_vector_store(self, rule: RoutingRule):
        """
        将规则添加到向量存储
        
        Args:
            rule: 路由规则
        """
        try:
            # 向量化规则模式
            embedding = await self.embedding_model.encode(rule.pattern)
            
            # 添加到向量存储（修复：移除 await，VectorStore.add 是同步函数）
            self.vector_store.add(
                entry_id=rule.id,
                embedding=embedding,
                metadata={
                    "pattern": rule.pattern,
                    "intent_type": rule.intent_type,
                    "priority": rule.priority
                }
            )
            
            logger.info(f"✅ 规则添加到向量存储: id={rule.id}")
            
        except Exception as e:
            logger.error(f"❌ 添加规则到向量存储失败: {e}")
            # 不抛出异常，允许规则创建成功但向量化失败
    
    async def _update_vector_store(self, rule: RoutingRule):
        """
        更新向量存储中的规则
        
        Args:
            rule: 路由规则
        """
        try:
            # 先删除旧的
            self._remove_from_vector_store(rule.id)
            
            # 再添加新的
            await self._add_to_vector_store(rule)
            
            logger.info(f"✅ 规则向量更新: id={rule.id}")
            
        except Exception as e:
            logger.error(f"❌ 更新规则向量失败: {e}")
    
    def _remove_from_vector_store(self, rule_id: int):
        """
        从向量存储中移除规则
        
        Args:
            rule_id: 规则ID
        """
        try:
            self.vector_store.delete(rule_id)
            logger.info(f"✅ 规则从向量存储移除: id={rule_id}")
            
        except Exception as e:
            logger.error(f"❌ 从向量存储移除规则失败: {e}")
    
    async def rebuild_vector_store(self):
        """
        重建向量存储（从数据库重新加载所有规则）
        
        Validates: Requirements 2.6
        """
        try:
            logger.info("🔄 开始重建路由规则向量存储...")
            
            # 1. 清空向量存储
            self.vector_store.clear()
            
            # 2. 获取所有启用的规则
            stmt = select(RoutingRule).filter(RoutingRule.is_active == True)
            
            if self.is_async:
                result = await self.db.execute(stmt)
                rules = result.scalars().all()
            else:
                result = self.db.execute(stmt)
                rules = result.scalars().all()
            
            # 3. 逐个添加到向量存储
            for rule in rules:
                await self._add_to_vector_store(rule)
            
            logger.info(f"✅ 向量存储重建完成: {len(rules)} 个规则")
            
        except Exception as e:
            logger.error(f"❌ 重建向量存储失败: {e}")
            raise

    async def _keyword_search(
        self,
        query: str,
        top_k: int = 50,
        mode: str = "natural"
    ) -> List[Dict]:
        """
        使用 MySQL 全文索引进行关键词检索
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            mode: 检索模式
                - "natural": 自然语言模式（默认）
                - "boolean": 布尔模式（精确匹配）
        
        Returns:
            关键词检索结果列表
        
        Validates: Requirements 13.2, 13.3, 13.4, 13.5
        """
        try:
            from sqlalchemy import text
            
            # 根据模式选择 SQL 语句
            if mode == "natural":
                # 自然语言模式
                sql = text("""
                    SELECT id, pattern, intent_type, priority, rule_metadata,
                           MATCH(pattern) AGAINST(:query IN NATURAL LANGUAGE MODE) AS relevance_score
                    FROM routing_rules
                    WHERE MATCH(pattern) AGAINST(:query IN NATURAL LANGUAGE MODE)
                      AND is_active = 1
                    ORDER BY relevance_score DESC, priority DESC
                    LIMIT :top_k
                """)
            else:
                # 布尔模式（精确匹配）
                sql = text("""
                    SELECT id, pattern, intent_type, priority, rule_metadata,
                           MATCH(pattern) AGAINST(:query IN BOOLEAN MODE) AS relevance_score
                    FROM routing_rules
                    WHERE MATCH(pattern) AGAINST(:query IN BOOLEAN MODE)
                      AND is_active = 1
                    ORDER BY relevance_score DESC, priority DESC
                    LIMIT :top_k
                """)
            
            # 执行查询
            if self.is_async:
                result = await self.db.execute(sql, {"query": query, "top_k": top_k})
            else:
                result = self.db.execute(sql, {"query": query, "top_k": top_k})
            
            rows = result.fetchall()
            
            # 转换为字典列表
            keyword_results = []
            for row in rows:
                keyword_results.append({
                    "id": row.id,
                    "pattern": row.pattern,
                    "intent_type": row.intent_type,
                    "priority": row.priority,
                    "metadata": row.rule_metadata,  # 数据库字段名是rule_metadata
                    "relevance_score": float(row.relevance_score)
                })
            
            logger.info(
                f"🔍 关键词检索完成: query={query}, mode={mode}, "
                f"results={len(keyword_results)}"
            )
            
            return keyword_results
            
        except Exception as e:
            logger.error(f"❌ 关键词检索失败: {e}")
            # 如果全文索引不可用，返回空列表
            return []
    
    def _rrf_fusion(
        self,
        vec_results: List[Dict],
        kw_results: List[Dict],
        k: int = 60
    ) -> List[Dict]:
        """
        RRF（Reciprocal Rank Fusion）融合向量检索和关键词检索结果
        
        RRF 算法：score = Σ(1/(k + rank_i))
        
        Args:
            vec_results: 向量检索结果列表（包含 entry_id 或 id 字段）
            kw_results: 关键词检索结果列表（包含 id 字段）
            k: RRF 常数，默认 60（经验最优值）
        
        Returns:
            融合后的规则列表，按 RRF 得分降序排序
        
        Validates: Requirements 12.1, 12.3, 12.4
        """
        try:
            rrf_scores = {}  # {rule_id: rrf_score}
            rule_map = {}    # {rule_id: rule_dict}
            
            # 1. 向量检索贡献（修复：兼容 entry_id 和 id 两种字段）
            for rank, rule in enumerate(vec_results, 1):
                rule_id = rule.get("entry_id") or rule.get("id")  # 修复：兼容两种格式
                if rule_id is None:
                    continue
                score = 1.0 / (k + rank)
                rrf_scores[rule_id] = rrf_scores.get(rule_id, 0) + score
                # 统一使用 id 字段存储
                rule_normalized = rule.copy()
                rule_normalized["id"] = rule_id
                rule_map[rule_id] = rule_normalized
            
            # 2. 关键词检索贡献
            for rank, rule in enumerate(kw_results, 1):
                rule_id = rule.get("id")
                if rule_id is None:
                    continue
                score = 1.0 / (k + rank)
                rrf_scores[rule_id] = rrf_scores.get(rule_id, 0) + score
                
                # 如果规则不在 rule_map 中，添加进去
                if rule_id not in rule_map:
                    rule_map[rule_id] = rule
            
            # 3. 按 RRF 得分排序
            sorted_ids = sorted(
                rrf_scores.items(),
                key=lambda x: x[1],
                reverse=True
            )
            
            # 4. 构建融合后的结果列表
            fused_results = []
            for rule_id, rrf_score in sorted_ids:
                rule = rule_map[rule_id].copy()
                rule["rrf_score"] = rrf_score
                fused_results.append(rule)
            
            logger.info(
                f"🔀 RRF 融合完成: vec={len(vec_results)}, kw={len(kw_results)}, "
                f"fused={len(fused_results)}, k={k}"
            )
            
            return fused_results
            
        except Exception as e:
            logger.error(f"❌ RRF 融合失败: {e}")
            # 降级：返回向量检索结果
            return vec_results
    
    async def search_rules_with_rrf(
        self,
        query: str,
        similarity_threshold: float = 0.7,
        top_k: int = 10,
        rrf_k: int = 60,
        vector_top_k: int = 50,
        keyword_top_k: int = 50
    ) -> List[Dict]:
        """
        使用 RRF 融合算法检索路由规则
        
        同时执行向量检索和关键词检索，使用 RRF 算法融合结果。
        
        Args:
            query: 查询文本
            similarity_threshold: 相似度阈值（用于过滤低相似度结果）
            top_k: 返回结果数量
            rrf_k: RRF 常数，默认 60
            vector_top_k: 向量检索 top-k
            keyword_top_k: 关键词检索 top-k
        
        Returns:
            融合后的规则列表
        
        Validates: Requirements 12.2, 12.5
        """
        try:
            logger.info(f"🔍 开始 RRF 融合检索: query={query}")
            
            # 1. 向量检索
            vec_results = await self.search_rules(
                query=query,
                similarity_threshold=0.0,  # 不在这里过滤，融合后再过滤
                top_k=vector_top_k
            )
            
            # 2. 关键词检索（使用 MySQL 全文索引）
            kw_results = await self._keyword_search(
                query=query,
                top_k=keyword_top_k,
                mode="natural"
            )
            
            # 3. RRF 融合
            fused_results = self._rrf_fusion(
                vec_results=vec_results,
                kw_results=kw_results,
                k=rrf_k
            )
            
            # 4. 过滤低相似度结果（如果有 similarity 字段）
            filtered_results = []
            for rule in fused_results[:top_k]:
                # 如果有相似度分数，检查是否超过阈值
                if "similarity" in rule:
                    if rule["similarity"] >= similarity_threshold:
                        filtered_results.append(rule)
                else:
                    # 没有相似度分数（来自关键词检索），直接添加
                    filtered_results.append(rule)
            
            logger.info(
                f"✅ RRF 融合检索完成: vec={len(vec_results)}, kw={len(kw_results)}, "
                f"fused={len(fused_results)}, filtered={len(filtered_results)}"
            )
            
            return filtered_results
            
        except Exception as e:
            logger.error(f"❌ RRF 融合检索失败: {e}")
            # 降级：使用普通向量检索
            return await self.search_rules(
                query=query,
                similarity_threshold=similarity_threshold,
                top_k=top_k
            )
