#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
反馈管理器（Feedback Manager）

实现需求：
- Requirements 6.3, 6.4: 提交路由错误反馈
- Requirements 7.1, 7.2, 7.3: 生成规则建议
- Requirements 7.5: 采纳规则建议
"""

from typing import Dict, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, and_, select

from app.core.logger import logger
from app.models.routing_feedback import RoutingFeedback
from app.models.routing_log import RoutingLog
from app.models.rule_suggestion import RuleSuggestion
from app.services.ai.routing_rule_manager import RoutingRuleManager


class FeedbackManager:
    """反馈管理器"""
    
    def __init__(self, db):
        """
        初始化反馈管理器
        
        Args:
            db: 数据库会话 (AsyncSession 或 Session)
        """
        self.db = db
        self.is_async = isinstance(db, AsyncSession)
        logger.info("✅ 反馈管理器初始化成功")
    
    def submit_feedback(
        self,
        routing_log_id: int,
        correct_intent: str,
        user_id: str,
        comment: Optional[str] = None
    ) -> RoutingFeedback:
        """
        提交路由错误反馈
        
        Args:
            routing_log_id: 路由日志ID
            correct_intent: 正确的意图类型
            user_id: 反馈用户ID
            comment: 反馈备注
        
        Returns:
            创建的反馈记录
        
        Validates: Requirements 6.3, 6.4
        """
        try:
            # 1. 验证路由日志是否存在
            stmt = select(RoutingLog).filter(RoutingLog.id == routing_log_id)
            result = self.db.execute(stmt)
            routing_log = result.scalar_one_or_none()
            
            if not routing_log:
                raise ValueError(f"路由日志不存在: id={routing_log_id}")
            
            # 2. 创建反馈记录
            feedback = RoutingFeedback(
                routing_log_id=routing_log_id,
                correct_intent=correct_intent,
                user_id=user_id,
                comment=comment
            )
            
            self.db.add(feedback)
            self.db.commit()
            self.db.refresh(feedback)
            
            logger.info(
                f"✅ 用户 {user_id} 提交反馈: log_id={routing_log_id}, "
                f"correct_intent={correct_intent}"
            )
            
            return feedback
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ 提交反馈失败: {e}")
            raise
    
    async def get_feedback_by_log(
        self,
        routing_log_id: int
    ) -> Optional[RoutingFeedback]:
        """
        获取指定路由日志的反馈
        
        Args:
            routing_log_id: 路由日志ID
        
        Returns:
            反馈记录（如果存在）
        """
        stmt = select(RoutingFeedback).filter(
            RoutingFeedback.routing_log_id == routing_log_id
        )
        
        if self.is_async:
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
        else:
            result = self.db.execute(stmt)
            return result.scalar_one_or_none()
    
    async def list_feedback(
        self,
        page: int = 1,
        page_size: int = 20,
        correct_intent: Optional[str] = None
    ) -> Dict:
        """
        获取反馈列表
        
        Args:
            page: 页码
            page_size: 每页数量
            correct_intent: 正确意图类型过滤
        
        Returns:
            分页格式的反馈列表
        
        Validates: Requirements 6.5
        """
        try:
            # 构建查询
            stmt = select(RoutingFeedback)
            
            # 过滤条件
            if correct_intent:
                stmt = stmt.filter(RoutingFeedback.correct_intent == correct_intent)
            
            # 获取总数
            count_stmt = select(func.count(RoutingFeedback.id))
            if correct_intent:
                count_stmt = count_stmt.filter(RoutingFeedback.correct_intent == correct_intent)
            
            if self.is_async:
                result = await self.db.execute(count_stmt)
                total = result.scalar()
            else:
                result = self.db.execute(count_stmt)
                total = result.scalar()
            
            # 分页查询
            stmt = stmt.order_by(RoutingFeedback.created_at.desc())\
                       .offset((page - 1) * page_size)\
                       .limit(page_size)
            
            if self.is_async:
                result = await self.db.execute(stmt)
                feedbacks = result.scalars().all()
            else:
                result = self.db.execute(stmt)
                feedbacks = result.scalars().all()
            
            # 转换为字典
            feedback_list = []
            for feedback in feedbacks:
                # 获取关联的路由日志
                log_stmt = select(RoutingLog).filter(RoutingLog.id == feedback.routing_log_id)
                
                if self.is_async:
                    log_result = await self.db.execute(log_stmt)
                    routing_log = log_result.scalar_one_or_none()
                else:
                    log_result = self.db.execute(log_stmt)
                    routing_log = log_result.scalar_one_or_none()
                
                feedback_dict = {
                    "id": feedback.id,
                    "routing_log_id": feedback.routing_log_id,
                    "query": routing_log.query if routing_log else None,
                    "original_intent": routing_log.intent_type if routing_log else None,
                    "correct_intent": feedback.correct_intent,
                    "user_id": feedback.user_id,
                    "comment": feedback.comment,
                    "created_at": feedback.created_at.isoformat()
                }
                feedback_list.append(feedback_dict)
            
            return {
                "list": feedback_list,
                "total": total,
                "page": page,
                "page_size": page_size
            }
            
        except Exception as e:
            logger.error(f"❌ 获取反馈列表失败: {e}")
            raise
    
    async def generate_rule_suggestions(
        self,
        min_support_count: int = 3
    ) -> List[RuleSuggestion]:
        """
        生成规则建议
        
        分析反馈记录，对于错误次数 >= min_support_count 的查询模式，生成规则建议。
        
        Args:
            min_support_count: 最小支持数量（默认 3）
        
        Returns:
            生成的规则建议列表
        
        Validates: Requirements 7.1, 7.2, 7.3
        """
        try:
            logger.info(f"🔍 开始生成规则建议（最小支持数: {min_support_count}）...")
            
            # 1. 查询所有反馈记录，按 correct_intent 分组
            stmt = select(RoutingFeedback)
            
            if self.is_async:
                result = await self.db.execute(stmt)
                feedbacks = result.scalars().all()
            else:
                result = self.db.execute(stmt)
                feedbacks = result.scalars().all()
            
            # 2. 按 correct_intent 和查询模式分组统计
            intent_patterns = {}  # {correct_intent: {pattern: [feedback_ids]}}
            
            for feedback in feedbacks:
                # 获取关联的路由日志
                log_stmt = select(RoutingLog).filter(RoutingLog.id == feedback.routing_log_id)
                
                if self.is_async:
                    log_result = await self.db.execute(log_stmt)
                    routing_log = log_result.scalar_one_or_none()
                else:
                    log_result = self.db.execute(log_stmt)
                    routing_log = log_result.scalar_one_or_none()
                
                if not routing_log:
                    continue
                
                query = routing_log.query
                correct_intent = feedback.correct_intent
                
                # 提取查询模式（简化版：使用查询的前 20 个字符作为模式）
                # 实际应用中可以使用更复杂的模式提取算法
                pattern = self._extract_pattern(query)
                
                if correct_intent not in intent_patterns:
                    intent_patterns[correct_intent] = {}
                
                if pattern not in intent_patterns[correct_intent]:
                    intent_patterns[correct_intent][pattern] = []
                
                intent_patterns[correct_intent][pattern].append({
                    "feedback_id": feedback.id,
                    "query": query,
                    "routing_log_id": feedback.routing_log_id
                })
            
            # 3. 生成规则建议
            suggestions = []
            
            for correct_intent, patterns in intent_patterns.items():
                for pattern, evidence_list in patterns.items():
                    support_count = len(evidence_list)
                    
                    # 只为支持数 >= min_support_count 的模式生成建议
                    if support_count >= min_support_count:
                        # 检查是否已存在相同的建议
                        check_stmt = select(RuleSuggestion).filter(
                            and_(
                                RuleSuggestion.pattern == pattern,
                                RuleSuggestion.suggested_intent == correct_intent,
                                RuleSuggestion.status == "pending"
                            )
                        )
                        
                        if self.is_async:
                            check_result = await self.db.execute(check_stmt)
                            existing_suggestion = check_result.scalar_one_or_none()
                        else:
                            check_result = self.db.execute(check_stmt)
                            existing_suggestion = check_result.scalar_one_or_none()
                        
                        if existing_suggestion:
                            logger.info(f"⏭️ 跳过已存在的建议: pattern={pattern}")
                            continue
                        
                        # 计算置信度（基于支持数）
                        confidence = min(0.7 + (support_count - min_support_count) * 0.05, 0.95)
                        
                        # 构建证据
                        evidence = {
                            "feedback_ids": [e["feedback_id"] for e in evidence_list],
                            "common_patterns": [pattern],
                            "error_rate": 1.0,  # 简化：假设所有反馈都是错误的
                            "sample_queries": [e["query"] for e in evidence_list[:5]]  # 最多 5 个示例
                        }
                        
                        # 创建规则建议
                        suggestion = RuleSuggestion(
                            pattern=pattern,
                            suggested_intent=correct_intent,
                            confidence=confidence,
                            support_count=support_count,
                            evidence=evidence,
                            status="pending"
                        )
                        
                        self.db.add(suggestion)
                        suggestions.append(suggestion)
                        
                        logger.info(
                            f"✅ 生成规则建议: pattern={pattern}, "
                            f"intent={correct_intent}, support={support_count}"
                        )
            
            # 4. 提交到数据库
            if suggestions:
                if self.is_async:
                    await self.db.commit()
                else:
                    self.db.commit()
                logger.info(f"✅ 生成 {len(suggestions)} 个规则建议")
            else:
                logger.info("ℹ️ 没有生成新的规则建议")
            
            return suggestions
            
        except Exception as e:
            if self.is_async:
                await self.db.rollback()
            else:
                self.db.rollback()
            logger.error(f"❌ 生成规则建议失败: {e}")
            raise
    
    def _extract_pattern(self, query: str) -> str:
        """
        从查询中提取模式
        
        简化版实现：使用查询的关键部分作为模式。
        实际应用中可以使用更复杂的算法（如 NLP 分词、实体识别等）。
        
        Args:
            query: 查询文本
        
        Returns:
            提取的模式
        """
        # 移除数字和特殊字符，保留关键词
        import re
        
        # 移除 IP 地址
        pattern = re.sub(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', '', query)
        
        # 移除实例 ID
        pattern = re.sub(r'\b(i-[a-zA-Z0-9]+|instance-[a-zA-Z0-9]+|ins-[a-zA-Z0-9]+)\b', '', pattern, flags=re.IGNORECASE)
        
        # 移除多余空格
        pattern = ' '.join(pattern.split())
        
        # 如果模式太短，使用原始查询的前 20 个字符
        if len(pattern) < 5:
            pattern = query[:20]
        
        return pattern.strip()
    
    async def adopt_suggestion(
        self,
        suggestion_id: int,
        adopted_by: str,
        final_pattern: Optional[str] = None,
        final_intent: Optional[str] = None,
        final_priority: Optional[int] = None,
        final_metadata: Optional[Dict] = None
    ) -> int:
        """
        采纳规则建议（创建正式规则）
        
        Args:
            suggestion_id: 建议ID
            adopted_by: 采纳者
            final_pattern: 最终的模式（如果为None则使用建议的pattern）
            final_intent: 最终的意图类型
            final_priority: 最终的优先级
            final_metadata: 最终的元数据
        
        Returns:
            创建的规则ID
        
        Validates: Requirements 7.5
        """
        try:
            # 1. 获取建议详情
            stmt = select(RuleSuggestion).filter(RuleSuggestion.id == suggestion_id)
            
            if self.is_async:
                result = await self.db.execute(stmt)
                suggestion = result.scalar_one_or_none()
            else:
                result = self.db.execute(stmt)
                suggestion = result.scalar_one_or_none()
            
            if not suggestion:
                raise ValueError(f"规则建议不存在: id={suggestion_id}")
            
            if suggestion.status != "pending":
                raise ValueError(f"规则建议状态不是 pending: status={suggestion.status}")
            
            # 2. 创建正式规则
            rule_manager = RoutingRuleManager(db=self.db)
            
            rule_id = await rule_manager.create_rule(
                pattern=final_pattern or suggestion.pattern,
                intent_type=final_intent or suggestion.suggested_intent,
                priority=final_priority or 50,
                description=f"从规则建议 #{suggestion_id} 采纳",
                metadata=final_metadata,
                created_by=adopted_by
            )
            
            # 3. 更新建议状态
            suggestion.status = "adopted"
            suggestion.adopted_by = adopted_by
            suggestion.adopted_at = datetime.now()
            suggestion.created_rule_id = rule_id
            
            if self.is_async:
                await self.db.commit()
            else:
                self.db.commit()
            
            logger.info(
                f"✅ 采纳规则建议: suggestion_id={suggestion_id}, "
                f"created_rule_id={rule_id}, adopted_by={adopted_by}"
            )
            
            return rule_id
            
        except Exception as e:
            if self.is_async:
                await self.db.rollback()
            else:
                self.db.rollback()
            logger.error(f"❌ 采纳规则建议失败: {e}")
            raise
    
    async def reject_suggestion(
        self,
        suggestion_id: int,
        rejected_by: str,
        reason: Optional[str] = None
    ) -> bool:
        """
        拒绝规则建议
        
        Args:
            suggestion_id: 建议ID
            rejected_by: 拒绝者
            reason: 拒绝原因
        
        Returns:
            是否拒绝成功
        """
        try:
            # 获取建议
            stmt = select(RuleSuggestion).filter(RuleSuggestion.id == suggestion_id)
            
            if self.is_async:
                result = await self.db.execute(stmt)
                suggestion = result.scalar_one_or_none()
            else:
                result = self.db.execute(stmt)
                suggestion = result.scalar_one_or_none()
            
            if not suggestion:
                raise ValueError(f"规则建议不存在: id={suggestion_id}")
            
            if suggestion.status != "pending":
                raise ValueError(f"规则建议状态不是 pending: status={suggestion.status}")
            
            # 更新状态
            suggestion.status = "rejected"
            suggestion.rejected_by = rejected_by
            suggestion.rejected_at = datetime.now()
            suggestion.reject_reason = reason
            
            if self.is_async:
                await self.db.commit()
            else:
                self.db.commit()
            
            logger.info(
                f"✅ 拒绝规则建议: suggestion_id={suggestion_id}, "
                f"rejected_by={rejected_by}"
            )
            
            return True
            
        except Exception as e:
            if self.is_async:
                await self.db.rollback()
            else:
                self.db.rollback()
            logger.error(f"❌ 拒绝规则建议失败: {e}")
            raise
    
    async def get_suggestion(self, suggestion_id: int) -> Optional[Dict]:
        """
        获取规则建议详情
        
        Args:
            suggestion_id: 建议ID
        
        Returns:
            建议详情字典
        
        Validates: Requirements 14.2
        """
        stmt = select(RuleSuggestion).filter(RuleSuggestion.id == suggestion_id)
        
        if self.is_async:
            result = await self.db.execute(stmt)
            suggestion = result.scalar_one_or_none()
        else:
            result = self.db.execute(stmt)
            suggestion = result.scalar_one_or_none()
        
        if not suggestion:
            return None
        
        return {
            "id": suggestion.id,
            "pattern": suggestion.pattern,
            "suggested_intent": suggestion.suggested_intent,
            "confidence": suggestion.confidence,
            "support_count": suggestion.support_count,
            "evidence": suggestion.evidence,
            "status": suggestion.status,
            "adopted_by": suggestion.adopted_by,
            "adopted_at": suggestion.adopted_at.isoformat() if suggestion.adopted_at else None,
            "rejected_by": suggestion.rejected_by,
            "rejected_at": suggestion.rejected_at.isoformat() if suggestion.rejected_at else None,
            "reject_reason": suggestion.reject_reason,
            "created_rule_id": suggestion.created_rule_id,
            "created_at": suggestion.created_at.isoformat(),
            "updated_at": suggestion.updated_at.isoformat()
        }
    
    async def list_suggestions(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        intent_type: Optional[str] = None
    ) -> Dict:
        """
        获取规则建议列表
        
        Args:
            page: 页码
            page_size: 每页数量
            status: 状态过滤（pending/adopted/rejected）
            intent_type: 意图类型过滤
        
        Returns:
            分页格式的建议列表
        
        Validates: Requirements 7.4, 14.1
        """
        try:
            # 构建查询
            stmt = select(RuleSuggestion)
            
            # 过滤条件
            filters = []
            if status:
                filters.append(RuleSuggestion.status == status)
            if intent_type:
                filters.append(RuleSuggestion.suggested_intent == intent_type)
            
            if filters:
                stmt = stmt.filter(and_(*filters))
            
            # 获取总数
            count_stmt = select(func.count(RuleSuggestion.id))
            if filters:
                count_stmt = count_stmt.filter(and_(*filters))
            
            if self.is_async:
                result = await self.db.execute(count_stmt)
                total = result.scalar()
            else:
                result = self.db.execute(count_stmt)
                total = result.scalar()
            
            # 分页查询
            stmt = stmt.order_by(
                RuleSuggestion.confidence.desc(),
                RuleSuggestion.created_at.desc()
            ).offset((page - 1) * page_size).limit(page_size)
            
            if self.is_async:
                result = await self.db.execute(stmt)
                suggestions = result.scalars().all()
            else:
                result = self.db.execute(stmt)
                suggestions = result.scalars().all()
            
            # 转换为字典
            suggestion_list = [
                {
                    "id": s.id,
                    "pattern": s.pattern,
                    "suggested_intent": s.suggested_intent,
                    "confidence": s.confidence,
                    "support_count": s.support_count,
                    "status": s.status,
                    "created_at": s.created_at.isoformat()
                }
                for s in suggestions
            ]
            
            return {
                "list": suggestion_list,
                "total": total,
                "page": page,
                "page_size": page_size
            }
            
        except Exception as e:
            logger.error(f"❌ 获取规则建议列表失败: {e}")
            raise
    
    async def update_suggestion(
        self,
        suggestion_id: int,
        pattern: Optional[str] = None,
        intent_type: Optional[str] = None,
        priority: Optional[int] = None,
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        更新规则建议（审核时编辑）
        
        Args:
            suggestion_id: 建议ID
            pattern: 修改后的模式
            intent_type: 修改后的意图类型
            priority: 修改后的优先级
            metadata: 修改后的元数据
        
        Returns:
            是否更新成功
        
        Validates: Requirements 14.3
        """
        try:
            # 获取建议
            stmt = select(RuleSuggestion).filter(RuleSuggestion.id == suggestion_id)
            
            if self.is_async:
                result = await self.db.execute(stmt)
                suggestion = result.scalar_one_or_none()
            else:
                result = self.db.execute(stmt)
                suggestion = result.scalar_one_or_none()
            
            if not suggestion:
                raise ValueError(f"规则建议不存在: id={suggestion_id}")
            
            # 更新字段
            if pattern is not None:
                suggestion.pattern = pattern
            if intent_type is not None:
                suggestion.suggested_intent = intent_type
            # priority 和 metadata 存储在 evidence 中（简化实现）
            if priority is not None or metadata is not None:
                evidence = suggestion.evidence or {}
                if priority is not None:
                    evidence["priority"] = priority
                if metadata is not None:
                    evidence["metadata"] = metadata
                suggestion.evidence = evidence
            
            if self.is_async:
                await self.db.commit()
            else:
                self.db.commit()
            
            logger.info(f"✅ 更新规则建议: suggestion_id={suggestion_id}")
            
            return True
            
        except Exception as e:
            if self.is_async:
                await self.db.rollback()
            else:
                self.db.rollback()
            logger.error(f"❌ 更新规则建议失败: {e}")
            raise
    
    async def batch_approve(
        self,
        suggestion_ids: List[int],
        approved_by: str
    ) -> Dict:
        """
        批量采纳规则建议
        
        Args:
            suggestion_ids: 建议ID列表
            approved_by: 审核人
        
        Returns:
            批量操作结果
        
        Validates: Requirements 14.6
        """
        try:
            success_count = 0
            failed_count = 0
            created_rule_ids = []
            failed_suggestions = []
            
            for suggestion_id in suggestion_ids:
                try:
                    rule_id = await self.adopt_suggestion(
                        suggestion_id=suggestion_id,
                        adopted_by=approved_by
                    )
                    created_rule_ids.append(rule_id)
                    success_count += 1
                except Exception as e:
                    logger.error(f"❌ 采纳建议 {suggestion_id} 失败: {e}")
                    failed_count += 1
                    failed_suggestions.append({
                        "suggestion_id": suggestion_id,
                        "error": str(e)
                    })
            
            result = {
                "success_count": success_count,
                "failed_count": failed_count,
                "created_rule_ids": created_rule_ids
            }
            
            if failed_suggestions:
                result["failed_suggestions"] = failed_suggestions
            
            logger.info(
                f"✅ 批量采纳完成: 成功={success_count}, 失败={failed_count}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"❌ 批量采纳失败: {e}")
            raise


# 全局实例（可选）
_feedback_manager = None


def get_feedback_manager(db: Session) -> FeedbackManager:
    """获取反馈管理器实例"""
    return FeedbackManager(db)
