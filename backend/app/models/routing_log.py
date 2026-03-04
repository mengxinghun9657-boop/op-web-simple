#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
路由日志数据模型

实现需求：
- Requirements 5.1: 记录每次路由的查询文本、意图类型、置信度和路由方法
"""

from sqlalchemy import Column, Integer, String, Text, DECIMAL, TIMESTAMP, ForeignKey, Index
from sqlalchemy.sql import func
from app.models.base import Base


class RoutingLog(Base):
    """路由日志模型"""
    
    __tablename__ = "routing_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment="日志ID")
    query = Column(Text, nullable=False, comment="用户查询")
    intent_type = Column(String(50), nullable=False, comment="路由到的意图类型")
    confidence = Column(DECIMAL(5, 4), nullable=False, comment="置信度")
    routing_method = Column(String(50), nullable=False, comment="路由方法")
    matched_rule_id = Column(
        Integer,
        ForeignKey('routing_rules.id', ondelete='SET NULL'),
        nullable=True,
        comment="匹配的规则ID"
    )
    similarity_score = Column(DECIMAL(5, 4), nullable=True, comment="相似度分数")
    user_id = Column(String(100), nullable=True, comment="用户ID")
    session_id = Column(String(100), nullable=True, comment="会话ID")
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now(), comment="创建时间")
    
    # 索引
    __table_args__ = (
        Index('idx_routing_log_intent_type', 'intent_type'),
        Index('idx_routing_log_confidence', 'confidence'),
        Index('idx_routing_log_routing_method', 'routing_method'),
        Index('idx_routing_log_created_at', 'created_at'),
        Index('idx_routing_log_user_id', 'user_id'),
        {'comment': '路由日志表'}
    )
    
    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "query": self.query,
            "intent_type": self.intent_type,
            "confidence": float(self.confidence),
            "routing_method": self.routing_method,
            "matched_rule_id": self.matched_rule_id,
            "similarity_score": float(self.similarity_score) if self.similarity_score else None,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
