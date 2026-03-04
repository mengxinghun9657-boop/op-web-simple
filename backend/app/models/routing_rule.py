#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
路由规则数据模型

实现需求：
- Requirements 2.1: 创建 routing_rules 数据库表存储路由规则
- Requirements 2.7: 支持 metadata 字段存储推荐的表、数据库等信息
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, TIMESTAMP, JSON, Index
from sqlalchemy.sql import func
from app.models.base import Base


class RoutingRule(Base):
    """路由规则模型"""
    
    __tablename__ = "routing_rules"
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment="规则ID")
    pattern = Column(String(500), nullable=False, comment="查询模式")
    intent_type = Column(String(50), nullable=False, comment="意图类型")
    priority = Column(Integer, nullable=False, default=50, comment="优先级(1-100)")
    description = Column(Text, nullable=True, comment="规则描述")
    rule_metadata = Column("metadata", JSON, nullable=True, comment="规则元数据（推荐的表、数据库等）")
    is_active = Column(Boolean, nullable=False, default=True, comment="是否启用")
    created_by = Column(String(100), nullable=True, comment="创建者")
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now(), comment="创建时间")
    updated_at = Column(
        TIMESTAMP,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="更新时间"
    )
    
    # 索引
    __table_args__ = (
        Index('idx_routing_rule_intent_type', 'intent_type'),
        Index('idx_routing_rule_priority', 'priority'),
        Index('idx_routing_rule_is_active', 'is_active'),
        {'comment': '路由规则表'}
    )
    
    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "pattern": self.pattern,
            "intent_type": self.intent_type,
            "priority": self.priority,
            "description": self.description,
            "metadata": self.rule_metadata,  # 对外仍使用 metadata 字段名
            "is_active": self.is_active,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
