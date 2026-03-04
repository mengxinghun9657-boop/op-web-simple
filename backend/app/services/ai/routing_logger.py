#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
路由日志记录器（Routing Logger）

实现需求：
- Requirements 5.1: 记录每次路由的详细信息
- Requirements 5.2: 提供统计查询功能
- Requirements 5.3: 识别低置信度查询
- Requirements 5.4: 分析路由方法分布
"""

import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, and_, select

from app.core.logger import logger
from app.models.routing_log import RoutingLog


class RoutingLogger:
    """路由日志记录器"""
    
    def __init__(self, db):
        """
        初始化路由日志记录器
        
        Args:
            db: 数据库会话 (AsyncSession 或 Session)
        """
        self.db = db
        self.is_async = isinstance(db, AsyncSession)
        logger.info("✅ 路由日志记录器初始化成功")
    
    async def log_routing(
        self,
        query: str,
        intent_type: str,
        confidence: float,
        routing_method: str,
        matched_rule_id: Optional[int] = None,
        similarity_score: Optional[float] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> RoutingLog:
        """
        记录路由信息（同步写入，确保数据持久化）
        
        Args:
            query: 用户查询文本
            intent_type: 路由结果（意图类型）
            confidence: 置信度
            routing_method: 路由方法（forced_rule/routing_rule/ernie/similarity/keyword）
            matched_rule_id: 匹配的规则 ID（如果有）
            similarity_score: 相似度分数（如果有）
            user_id: 用户 ID
            session_id: 会话 ID
        
        Returns:
            创建的日志记录
        
        Validates: Requirements 5.1
        """
        try:
            # 创建日志记录
            log = RoutingLog(
                query=query,
                intent_type=intent_type,
                confidence=confidence,
                routing_method=routing_method,
                matched_rule_id=matched_rule_id,
                similarity_score=similarity_score,
                user_id=user_id,
                session_id=session_id
            )
            
            # 同步写入数据库（确保数据持久化）
            await self._save_log_async(log)
            
            logger.debug(f"📝 路由日志已记录: query={query[:50]}..., intent={intent_type}, confidence={confidence:.2f}")
            
            return log
            
        except Exception as e:
            logger.error(f"❌ 记录路由日志失败: {e}")
            # 不抛出异常，避免影响主流程
            return None
    
    async def _save_log_async(self, log: RoutingLog):
        """
        异步保存日志到数据库
        
        Args:
            log: 日志记录
        """
        try:
            self.db.add(log)
            if self.is_async:
                await self.db.commit()
                await self.db.refresh(log)
            else:
                self.db.commit()
                self.db.refresh(log)
            logger.debug(f"✅ 路由日志已保存: id={log.id}")
        except Exception as e:
            logger.error(f"❌ 保存路由日志失败: {e}")
            if self.is_async:
                await self.db.rollback()
            else:
                self.db.rollback()
    
    async def get_statistics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        intent_type: Optional[str] = None,
        routing_method: Optional[str] = None
    ) -> Dict:
        """
        获取路由统计信息
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            intent_type: 意图类型过滤
            routing_method: 路由方法过滤
        
        Returns:
            统计信息字典
        
        Validates: Requirements 5.2, 5.3, 5.4
        """
        try:
            # 构建查询条件
            filters = []
            
            if start_date:
                filters.append(RoutingLog.created_at >= start_date)
            
            if end_date:
                filters.append(RoutingLog.created_at <= end_date)
            
            if intent_type:
                filters.append(RoutingLog.intent_type == intent_type)
            
            if routing_method:
                filters.append(RoutingLog.routing_method == routing_method)
            
            # 总数统计
            stmt = select(func.count(RoutingLog.id)).filter(and_(*filters))
            result = await self.db.execute(stmt)
            total_count = result.scalar()
            
            # 按意图类型统计
            stmt = select(
                RoutingLog.intent_type,
                func.count(RoutingLog.id).label('count')
            ).filter(and_(*filters)).group_by(RoutingLog.intent_type)
            result = await self.db.execute(stmt)
            intent_stats = result.all()
            
            # 按路由方法统计
            stmt = select(
                RoutingLog.routing_method,
                func.count(RoutingLog.id).label('count')
            ).filter(and_(*filters)).group_by(RoutingLog.routing_method)
            result = await self.db.execute(stmt)
            method_stats = result.all()
            
            # 按置信度区间统计
            stmt = select(func.count(RoutingLog.id)).filter(
                and_(*filters, RoutingLog.confidence >= 0.8)
            )
            result = await self.db.execute(stmt)
            high_count = result.scalar()
            
            stmt = select(func.count(RoutingLog.id)).filter(
                and_(*filters, RoutingLog.confidence >= 0.5, RoutingLog.confidence < 0.8)
            )
            result = await self.db.execute(stmt)
            medium_count = result.scalar()
            
            stmt = select(func.count(RoutingLog.id)).filter(
                and_(*filters, RoutingLog.confidence < 0.5)
            )
            result = await self.db.execute(stmt)
            low_count = result.scalar()
            
            confidence_stats = {
                "high": high_count,
                "medium": medium_count,
                "low": low_count
            }
            
            # 平均置信度
            stmt = select(func.avg(RoutingLog.confidence)).filter(and_(*filters))
            result = await self.db.execute(stmt)
            avg_confidence = result.scalar()
            
            # 构建统计结果
            statistics = {
                "total_count": total_count,
                "avg_confidence": float(avg_confidence) if avg_confidence else 0.0,
                "intent_distribution": {
                    intent: count for intent, count in intent_stats
                },
                "method_distribution": {
                    method: count for method, count in method_stats
                },
                "confidence_distribution": confidence_stats,
                "period": {
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None
                }
            }
            
            logger.info(f"📊 路由统计查询完成: total={total_count}, avg_confidence={avg_confidence if avg_confidence else 0:.2f}")
            
            return statistics
            
        except Exception as e:
            logger.error(f"❌ 获取路由统计失败: {e}")
            raise
    
    async def get_low_confidence_logs(
        self,
        threshold: float = 0.7,
        limit: int = 100,
        offset: int = 0
    ) -> Dict:
        """
        获取低置信度的路由记录
        
        Args:
            threshold: 置信度阈值（默认 0.7）
            limit: 返回数量限制
            offset: 偏移量（分页）
        
        Returns:
            低置信度记录列表和总数
        
        Validates: Requirements 5.3
        """
        try:
            # 查询低置信度记录
            stmt = select(RoutingLog).filter(
                RoutingLog.confidence < threshold
            ).order_by(RoutingLog.created_at.desc())
            
            # 总数
            count_stmt = select(func.count(RoutingLog.id)).filter(
                RoutingLog.confidence < threshold
            )
            result = await self.db.execute(count_stmt)
            total = result.scalar()
            
            # 分页查询
            stmt = stmt.limit(limit).offset(offset)
            result = await self.db.execute(stmt)
            logs = result.scalars().all()
            
            # 转换为字典
            log_list = [
                {
                    "id": log.id,
                    "query": log.query,
                    "intent_type": log.intent_type,
                    "confidence": log.confidence,
                    "routing_method": log.routing_method,
                    "matched_rule_id": log.matched_rule_id,
                    "similarity_score": log.similarity_score,
                    "created_at": log.created_at.isoformat()
                }
                for log in logs
            ]
            
            logger.info(f"📊 低置信度查询完成: threshold={threshold}, total={total}, returned={len(log_list)}")
            
            return {
                "total": total,
                "logs": log_list,
                "threshold": threshold,
                "limit": limit,
                "offset": offset
            }
            
        except Exception as e:
            logger.error(f"❌ 获取低置信度记录失败: {e}")
            raise
    
    async def get_recent_logs(
        self,
        hours: int = 24,
        limit: int = 100
    ) -> List[Dict]:
        """
        获取最近的路由记录
        
        Args:
            hours: 最近多少小时
            limit: 返回数量限制
        
        Returns:
            路由记录列表
        """
        try:
            # 计算时间范围
            start_time = datetime.now() - timedelta(hours=hours)
            
            # 查询最近记录
            stmt = select(RoutingLog).filter(
                RoutingLog.created_at >= start_time
            ).order_by(RoutingLog.created_at.desc()).limit(limit)
            
            result = await self.db.execute(stmt)
            logs = result.scalars().all()
            
            # 转换为字典
            log_list = [
                {
                    "id": log.id,
                    "query": log.query,
                    "intent_type": log.intent_type,
                    "confidence": log.confidence,
                    "routing_method": log.routing_method,
                    "created_at": log.created_at.isoformat()
                }
                for log in logs
            ]
            
            logger.info(f"📊 最近记录查询完成: hours={hours}, returned={len(log_list)}")
            
            return log_list
            
        except Exception as e:
            logger.error(f"❌ 获取最近记录失败: {e}")
            raise


# 全局实例（可选）
_routing_logger = None


def get_routing_logger(db) -> RoutingLogger:
    """获取路由日志记录器实例"""
    return RoutingLogger(db)
