"""
GPU 集群监控相关数据模型
"""
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Index

from app.models.base import Base


class GPUInspectionRecord(Base):
    """HAS 自动化巡检实例记录"""

    __tablename__ = "gpu_inspection_records"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    instance_id = Column(String(100), nullable=False, unique=True, index=True, comment="实例ID")
    instance_name = Column(String(255), nullable=False, index=True, comment="实例名称")
    gpu_card = Column(String(50), nullable=False, index=True, comment="GPU 型号")
    internal_ip = Column(String(64), nullable=True, index=True, comment="内网IP")
    has_alive = Column(String(32), nullable=False, index=True, comment="HAS 状态")
    region = Column(String(50), nullable=True, index=True, comment="区域")
    source_updated_at = Column(DateTime, nullable=True, comment="源数据更新时间")
    created_at = Column(DateTime, default=datetime.now, nullable=False, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False, comment="更新时间")

    __table_args__ = (
        Index("idx_gpu_inspection_status_card", "has_alive", "gpu_card"),
    )
