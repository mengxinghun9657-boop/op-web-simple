#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CMDB配置模型
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from datetime import datetime
from app.models.base import Base


class CMDBConfig(Base):
    """CMDB配置表"""
    __tablename__ = "cmdb_config"
    
    id = Column(Integer, primary_key=True, index=True)
    config_key = Column(String(100), unique=True, index=True, comment="配置键")
    config_value = Column(Text, comment="配置值")
    config_type = Column(String(50), default="string", comment="配置类型: string, json, encrypted")
    description = Column(String(500), comment="配置说明")
    is_active = Column(Boolean, default=True, comment="是否启用")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")
    updated_by = Column(String(100), comment="更新人")


class CMDBSyncLog(Base):
    """CMDB同步日志表"""
    __tablename__ = "cmdb_sync_log"
    
    id = Column(Integer, primary_key=True, index=True)
    sync_type = Column(String(50), comment="同步类型: api, excel")
    azone = Column(String(100), comment="可用区")
    status = Column(String(50), comment="状态: success, failed, running")
    total_rows = Column(Integer, default=0, comment="总记录数")
    servers_added = Column(Integer, default=0, comment="新增服务器数")
    servers_updated = Column(Integer, default=0, comment="更新服务器数")
    instances_added = Column(Integer, default=0, comment="新增实例数")
    instances_updated = Column(Integer, default=0, comment="更新实例数")
    error_message = Column(Text, comment="错误信息")
    started_at = Column(DateTime, default=datetime.utcnow, comment="开始时间")
    completed_at = Column(DateTime, comment="完成时间")
    duration_seconds = Column(Integer, comment="耗时（秒）")
    triggered_by = Column(String(100), comment="触发人")
