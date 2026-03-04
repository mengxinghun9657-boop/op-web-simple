#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
规则草稿数据模型

实现需求：
- Requirements 18.1: 自动保存用户的输入到本地存储
- Requirements 18.2: 每 30 秒自动保存一次
- Requirements 18.5: 支持多个草稿的管理
"""

from sqlalchemy import Column, Integer, String, JSON, TIMESTAMP, Index
from sqlalchemy.sql import func
from app.models.base import Base


class RuleDraft(Base):
    """规则草稿模型"""
    
    __tablename__ = "rule_drafts"
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment="草稿ID")
    user_id = Column(String(50), nullable=False, comment="用户ID")
    draft_data = Column(JSON, nullable=False, comment="草稿数据")
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
        Index('idx_user_id', 'user_id'),
        Index('idx_updated_at', 'updated_at'),
        {'comment': '路由规则草稿表'}
    )
    
    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "draft_data": self.draft_data,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
