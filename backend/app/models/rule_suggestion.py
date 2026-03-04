#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
规则建议数据模型

实现需求：
- Requirements 7.1: 基于反馈数据自动生成规则建议
"""

from sqlalchemy import Column, Integer, String, DECIMAL, TIMESTAMP, ForeignKey, JSON, Index
from sqlalchemy.sql import func
from app.models.base import Base


class RuleSuggestion(Base):
    """规则建议模型"""
    
    __tablename__ = "rule_suggestions"
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment="建议ID")
    pattern = Column(String(500), nullable=False, comment="建议的查询模式")
    suggested_intent = Column(String(50), nullable=False, comment="建议的意图类型")
    confidence = Column(DECIMAL(5, 4), nullable=False, comment="建议置信度")
    support_count = Column(Integer, nullable=False, comment="支持证据数量")
    evidence = Column(JSON, nullable=True, comment="支持证据(反馈记录)")
    status = Column(String(20), nullable=False, default='pending', comment="状态")
    adopted_by = Column(String(100), nullable=True, comment="采纳者")
    adopted_at = Column(TIMESTAMP, nullable=True, comment="采纳时间")
    created_rule_id = Column(
        Integer,
        ForeignKey('routing_rules.id', ondelete='SET NULL'),
        nullable=True,
        comment="创建的规则ID"
    )
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now(), comment="创建时间")
    
    # 索引
    __table_args__ = (
        Index('idx_rule_suggestion_status', 'status'),
        Index('idx_rule_suggestion_suggested_intent', 'suggested_intent'),
        {'comment': '规则建议表'}
    )
    
    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "pattern": self.pattern,
            "suggested_intent": self.suggested_intent,
            "confidence": float(self.confidence),
            "support_count": self.support_count,
            "evidence": self.evidence,
            "status": self.status,
            "adopted_by": self.adopted_by,
            "adopted_at": self.adopted_at.isoformat() if self.adopted_at else None,
            "created_rule_id": self.created_rule_id,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
