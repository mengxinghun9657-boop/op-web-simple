"""
APIServer 监控告警模型
"""
from datetime import datetime

from sqlalchemy import Column, BigInteger, DateTime, Float, Index, JSON, String, Text

from app.models.base import Base


class APIServerAlertRecord(Base):
    __tablename__ = "apiserver_alert_records"

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    fingerprint = Column(String(255), nullable=False, unique=True, index=True, comment="告警指纹")
    cluster_id = Column(String(200), nullable=False, index=True, comment="集群ID")
    metric_key = Column(String(100), nullable=False, index=True, comment="指标键")
    metric_label = Column(String(200), nullable=False, comment="指标名称")
    severity = Column(String(50), nullable=False, index=True, comment="严重程度")
    status = Column(String(50), nullable=False, default="active", index=True, comment="状态 active/resolved/ignored")
    current_value = Column(Float, nullable=False, default=0, comment="当前值")
    warning_threshold = Column(Float, nullable=True, comment="警告阈值")
    critical_threshold = Column(Float, nullable=True, comment="严重阈值")
    unit = Column(String(50), nullable=True, comment="单位")
    window_minutes = Column(String(50), nullable=True, comment="统计窗口")
    promql = Column(Text, nullable=True, comment="PromQL")
    description = Column(Text, nullable=True, comment="影响描述")
    suggestion = Column(Text, nullable=True, comment="建议动作")
    labels = Column(JSON, nullable=True, comment="附加标签/元数据")
    source = Column(String(50), nullable=False, default="prometheus", comment="来源")
    notified = Column(String(10), nullable=False, default="false", comment="是否已通知")
    notified_at = Column(DateTime, nullable=True, comment="通知时间")
    last_seen_at = Column(DateTime, nullable=True, comment="最近检测时间")
    created_at = Column(DateTime, default=datetime.now, nullable=False, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False, comment="更新时间")
    resolved_at = Column(DateTime, nullable=True, comment="恢复时间")
    resolved_by = Column(String(100), nullable=True, comment="处理人")
    resolution_notes = Column(Text, nullable=True, comment="处理备注")
    resolution_result = Column(String(50), nullable=True, comment="处理结果")
    icafe_card_id = Column(String(100), nullable=True, comment="关联 iCafe 卡片ID")

    __table_args__ = (
        Index("idx_apiserver_cluster_status", "cluster_id", "status"),
        Index("idx_apiserver_metric_status", "metric_key", "status"),
    )
