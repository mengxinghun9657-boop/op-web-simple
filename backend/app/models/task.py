#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据模型 - 任务表（当前使用内存存储，数据库可选）
"""

import enum
import uuid


class TaskStatus(str, enum.Enum):
    """任务状态枚举"""
    PENDING = "pending"           # 等待中
    PROCESSING = "processing"     # 处理中
    COMPLETED = "completed"       # 已完成
    FAILED = "failed"            # 失败
    # 保留旧状态以兼容
    CREATED = "created"
    UPLOADED = "uploaded"
    ANALYZING = "analyzing"


class TaskType(str, enum.Enum):
    """任务类型枚举"""
    # Prometheus集群监控
    PROMETHEUS_BATCH = "prometheus_batch"     # 批量集群监控
    PROMETHEUS_SINGLE = "prometheus_single"   # 单集群监控
    # 数据分析
    OPERATIONAL = "operational_analysis"      # 运营数据分析
    RESOURCE = "resource_analysis"           # 资源负载分析
    # 监控分析
    MONITORING_EIP = "monitoring_eip"        # EIP监控分析
    MONITORING_BCC = "monitoring_bcc"        # BCC监控分析
    MONITORING_BOS = "monitoring_bos"        # BOS监控分析
    GPU_HAS_SYNC = "gpu_has_sync"            # GPU HAS巡检数据同步
    GPU_HAS_COLLECT = "gpu_has_collect"      # GPU HAS巡检采集
    GPU_BOTTOM_ANALYSIS = "gpu_bottom_analysis"  # GPU bottom卡时分析
    # PFS监控
    PFS_EXPORT = "pfs_export"                # PFS数据导出


# 保留旧的ModuleType以兼容
ModuleType = TaskType


try:
    from sqlalchemy import Column, String, Integer, DateTime, Text, Enum
    from sqlalchemy.sql import func
    from app.models.base import Base
    
    SQLALCHEMY_AVAILABLE = True
    
    class Task(Base):
        """任务数据模型"""
        __tablename__ = "tasks"

        id = Column(String(50), primary_key=True, comment="任务ID")
        task_type = Column(Enum(TaskType), nullable=False, comment="任务类型")
        status = Column(Enum(TaskStatus), default=TaskStatus.PENDING, comment="任务状态")
        progress = Column(Integer, default=0, comment="进度百分比(0-100)")

        # 任务详情
        total_items = Column(Integer, default=0, comment="总项目数（如集群数）")
        completed_items = Column(Integer, default=0, comment="已完成项目数")
        message = Column(String(500), comment="任务消息")

        # 文件路径（MinIO）
        file_name = Column(String(255), comment="原始文件名")
        file_path = Column(String(500), comment="上传文件路径（MinIO）")
        result_path = Column(String(500), comment="结果文件路径（MinIO）")
        result_url = Column(String(500), comment="结果文件URL")

        # 用户信息
        user_id = Column(Integer, comment="创建用户ID")
        username = Column(String(100), comment="创建用户名")

        # 错误信息
        error_message = Column(Text, comment="错误信息")

        # 时间戳
        created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
        updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")
        completed_at = Column(DateTime, comment="完成时间")

        def __repr__(self):
            return f"<Task(id={self.id}, type={self.task_type}, status={self.status})>"
            
except Exception as e:
    SQLALCHEMY_AVAILABLE = False
    print(f"⚠️ Task模型未使用数据库，将使用内存存储: {e}")
    
    # 占位Task类（不使用数据库）
    class Task:
        """任务数据模型（内存版本）"""
        def __init__(self):
            pass
