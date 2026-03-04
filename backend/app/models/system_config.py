#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统配置模型
用于集中管理CMDB、监控、分析等模块的配置
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, UniqueConstraint
from datetime import datetime
from app.models.base import Base


class SystemConfig(Base):
    """系统配置表"""
    __tablename__ = "system_config"
    
    id = Column(Integer, primary_key=True, index=True, comment="主键ID")
    module = Column(String(50), nullable=False, index=True, comment="模块名称: cmdb, monitoring, analysis")
    config_key = Column(String(100), nullable=False, index=True, comment="配置键")
    config_value = Column(Text, nullable=True, comment="配置值（JSON格式）")
    description = Column(String(500), comment="配置说明")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, comment="更新时间")
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True, comment="更新人ID")
    
    # 唯一约束：同一模块下的同一配置键只能有一条记录
    __table_args__ = (
        UniqueConstraint('module', 'config_key', name='uq_module_config_key'),
    )
    
    def __repr__(self):
        return f"<SystemConfig(module={self.module}, config_key={self.config_key})>"
