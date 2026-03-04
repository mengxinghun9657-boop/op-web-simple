#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
实例配置数据模型
"""

from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, text
from app.models.base import Base


class InstanceConfig(Base):
    """实例配置表"""
    __tablename__ = "instance_config"
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    config_type = Column(String(50), nullable=False, unique=True, comment="配置类型")
    instance_ids = Column(Text, nullable=False, comment="实例ID列表（JSON数组格式）")
    description = Column(String(500), comment="配置说明")
    created_by = Column(String(100), comment="创建者")
    updated_by = Column(String(100), comment="更新者")
    created_at = Column(
        TIMESTAMP,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        comment="创建时间"
    )
    updated_at = Column(
        TIMESTAMP,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
        comment="更新时间"
    )
    
    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "config_type": self.config_type,
            "instance_ids": self.instance_ids,
            "description": self.description,
            "created_by": self.created_by,
            "updated_by": self.updated_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
