#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
规则模板数据模型

实现需求：
- Requirements 8.1: 提供至少 10 个常见场景的规则模板
- Requirements 8.2: 包含 IP 查询、实例 ID 查询、统计查询、报告查询、知识查询等模板类型
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, TIMESTAMP, JSON, Index
from sqlalchemy.sql import func
from app.models.base import Base


class RuleTemplate(Base):
    """规则模板模型"""
    
    __tablename__ = "rule_templates"
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment="模板ID")
    name = Column(String(100), nullable=False, comment="模板名称")
    category = Column(String(50), nullable=False, comment="模板分类")
    description = Column(Text, nullable=True, comment="模板描述")
    pattern = Column(String(500), nullable=False, comment="匹配模式")
    intent_type = Column(String(50), nullable=False, comment="意图类型")
    priority = Column(Integer, nullable=False, default=50, comment="优先级")
    rule_metadata = Column("metadata", JSON, nullable=True, comment="元数据")
    is_system = Column(Boolean, nullable=False, default=True, comment="是否系统模板")
    created_by = Column(String(50), nullable=True, comment="创建者")
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
        Index('idx_category', 'category'),
        Index('idx_intent_type', 'intent_type'),
        {'comment': '路由规则模板表'}
    )
    
    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "pattern": self.pattern,
            "intent_type": self.intent_type,
            "priority": self.priority,
            "metadata": self.rule_metadata,
            "is_system": self.is_system,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
