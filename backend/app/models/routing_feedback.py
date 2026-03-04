#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
路由反馈数据模型

实现需求：
- Requirements 6.3: 记录用户对路由结果的反馈
"""

from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, ForeignKey, Index
from sqlalchemy.sql import func
from app.models.base import Base


class RoutingFeedback(Base):
    """路由反馈模型"""
    
    __tablename__ = "routing_feedback"
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment="反馈ID")
    routing_log_id = Column(
        Integer,
        ForeignKey('routing_logs.id', ondelete='CASCADE'),
        nullable=False,
        comment="路由日志ID"
    )
    correct_intent = Column(String(50), nullable=False, comment="正确的意图类型")
    user_id = Column(String(100), nullable=False, comment="反馈用户ID")
    comment = Column(Text, nullable=True, comment="反馈备注")
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now(), comment="创建时间")
    
    # 索引
    __table_args__ = (
        Index('idx_routing_feedback_routing_log_id', 'routing_log_id'),
        Index('idx_routing_feedback_correct_intent', 'correct_intent'),
        Index('idx_routing_feedback_created_at', 'created_at'),
        {'comment': '路由反馈表'}
    )
    
    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "routing_log_id": self.routing_log_id,
            "correct_intent": self.correct_intent,
            "user_id": self.user_id,
            "comment": self.comment,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
