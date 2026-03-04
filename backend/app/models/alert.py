"""
硬件告警相关数据模型
"""
from datetime import datetime
from sqlalchemy import Column, BigInteger, String, DateTime, Boolean, Text, JSON, ForeignKey, Index, Integer
from sqlalchemy.orm import relationship
from app.models.base import Base


class AlertRecord(Base):
    """告警记录表
    
    设计原则：
    1. 关键字段提取到独立列，支持高效查询和统计
    2. 原始数据完整保存在 raw_data JSON 字段
    3. 字段长度留足余量，支持未来扩展
    """
    __tablename__ = "alert_records"
    
    # 基础信息
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='主键ID')
    alert_type = Column(String(200), nullable=False, index=True, comment='告警类型（预留足够长度）')
    
    # 位置信息（用于分组统计）
    ip = Column(String(100), index=True, comment='节点IP地址')
    cluster_id = Column(String(200), index=True, comment='集群ID（CCE集群专用）')
    instance_id = Column(String(200), comment='实例ID（物理机专用）')
    hostname = Column(String(200), comment='主机名/节点名')
    
    # 告警属性（用于筛选和统计）
    component = Column(String(100), index=True, comment='组件类型(GPU/Memory/CPU/Motherboard等)')
    severity = Column(String(50), nullable=False, index=True, comment='严重程度(critical/warning/info等)')
    
    # 时间信息（用于时间趋势分析）
    timestamp = Column(DateTime, nullable=False, index=True, comment='告警发生时间')
    
    # 文件信息
    file_path = Column(String(1000), comment='源文件路径（预留足够长度）')
    
    # 原始数据（完整保存，支持未来重新解析）
    raw_data = Column(JSON, comment='告警原始数据（完整JSON）')
    
    # 处理状态
    status = Column(String(50), default='pending', index=True, 
                   comment='处理状态(pending/processing/diagnosed/notified/failed/resolved)')
    
    # 处理信息
    resolved_by = Column(String(100), comment='处理人')
    resolved_at = Column(DateTime, comment='处理时间')
    resolution_notes = Column(Text, comment='处理备注')
    
    # 是否CCE集群（用于区分处理流程）
    is_cce_cluster = Column(Boolean, default=False, index=True, comment='是否CCE集群告警')
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.now, index=True, comment='记录创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='记录更新时间')
    
    # 关系
    diagnosis = relationship("DiagnosisResult", back_populates="alert", uselist=False, cascade="all, delete-orphan")
    
    # 复合索引（用于常见查询场景）
    __table_args__ = (
        Index('idx_timestamp_severity', 'timestamp', 'severity'),  # 时间+严重程度
        Index('idx_cluster_timestamp', 'cluster_id', 'timestamp'),  # 集群+时间
        Index('idx_component_timestamp', 'component', 'timestamp'),  # 组件+时间
        Index('idx_status_timestamp', 'status', 'timestamp'),  # 状态+时间
        Index('idx_unique_alert', 'alert_type', 'ip', 'timestamp', unique=True),  # 防止重复告警
    )


class DiagnosisResult(Base):
    """诊断结果表
    
    设计原则：
    1. 手册匹配结果提取关键字段
    2. API诊断完整报告保存在 JSON 字段
    3. AI解读完整内容保存在 Text 字段
    4. 统计字段独立存储，支持快速查询
    """
    __tablename__ = "diagnosis_results"
    
    # 基础信息
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='主键ID')
    alert_id = Column(BigInteger, ForeignKey('alert_records.id', ondelete='CASCADE'), 
                     nullable=False, unique=True, comment='关联告警ID（一对一）')
    
    # 诊断来源
    source = Column(String(50), nullable=False, index=True, 
                   comment='诊断来源(manual/api/manual+api)')
    
    # ========== 手册匹配结果 ==========
    manual_matched = Column(Boolean, default=False, index=True, comment='是否匹配到手册')
    manual_name_zh = Column(String(500), comment='故障中文名称（预留足够长度）')
    manual_solution = Column(Text, comment='手册解决方案（完整文本）')
    manual_impact = Column(Text, comment='影响描述')
    manual_recovery = Column(Text, comment='恢复方案')
    danger_level = Column(String(50), index=True, comment='危害等级（严重/中等/轻微）')
    customer_aware = Column(Boolean, comment='是否客户有感')
    
    # ========== API诊断结果（仅CCE集群） ==========
    api_task_id = Column(String(200), comment='API任务ID')
    api_status = Column(String(50), index=True, comment='API任务状态(normal/abnormal/failed)')
    
    # API诊断统计字段（用于快速查询）
    api_items_count = Column(Integer, default=0, comment='诊断项总数')
    api_error_count = Column(Integer, default=0, comment='错误项数量')
    api_warning_count = Column(Integer, default=0, comment='警告项数量')
    api_abnormal_count = Column(Integer, default=0, comment='异常项数量')
    
    # API诊断完整报告（JSON格式，包含所有诊断项）
    api_diagnosis = Column(JSON, comment='API诊断完整报告（包含raw_report）')
    
    # ========== AI解读结果 ==========
    # AI解读完整内容（Markdown格式）
    ai_interpretation = Column(Text, comment='AI解读完整内容（Markdown）')
    
    # AI解读提取字段（用于快速展示）
    ai_category = Column(String(100), comment='AI问题分类')
    ai_root_cause = Column(Text, comment='根本原因分析')
    ai_impact = Column(Text, comment='影响评估')
    ai_solution = Column(Text, comment='修复建议')
    
    # ========== 通知状态 ==========
    notified = Column(Boolean, default=False, comment='是否已发送通知')
    notified_at = Column(DateTime, comment='通知发送时间')
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    
    # 关系
    alert = relationship("AlertRecord", back_populates="diagnosis")
    
    # 索引
    __table_args__ = (
        Index('idx_source', 'source'),
        Index('idx_danger_level', 'danger_level'),
        Index('idx_api_status', 'api_status'),
    )


class WebhookConfig(Base):
    """Webhook配置表"""
    __tablename__ = "webhook_configs"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='主键ID')
    name = Column(String(200), nullable=False, comment='配置名称')
    type = Column(String(50), nullable=False, index=True, comment='Webhook类型(feishu/ruliu)')
    url = Column(String(1000), nullable=False, comment='Webhook URL（预留足够长度）')
    access_token = Column(String(500), comment='访问令牌')
    secret = Column(String(500), comment='签名密钥（飞书专用）')
    group_id = Column(String(200), comment='群组ID（如流专用）')
    enabled = Column(Boolean, default=True, index=True, comment='是否启用')
    
    # 触发条件（JSON格式，支持复杂过滤规则）
    severity_filter = Column(String(200), comment='严重程度过滤(critical,warning)')
    component_filter = Column(String(500), comment='组件过滤(GPU,Memory)')
    keywords = Column(String(200), comment='飞书机器人关键词(如: 告警，仅飞书需要)')
    
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    
    # 索引
    __table_args__ = (
        Index('idx_type_enabled', 'type', 'enabled'),
    )


class FaultManual(Base):
    """故障手册表"""
    __tablename__ = "fault_manual"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='主键ID')
    category = Column(String(100), nullable=False, index=True, comment='类别(GPU/CPU/Memory等)')
    alert_type = Column(String(200), nullable=False, index=True, comment='告警类型')
    has_level = Column(String(50), comment='HAS级别')
    name_zh = Column(String(500), comment='中文名称')
    impact = Column(Text, comment='影响描述')
    recovery_plan = Column(Text, comment='恢复方案')
    danger_level = Column(String(50), comment='危害等级')
    customer_aware = Column(Boolean, comment='是否客户有感')
    manual_check = Column(Text, comment='手动判断方法')
    
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    
    # 索引
    __table_args__ = (
        Index('uk_category_type', 'category', 'alert_type', unique=True),
    )


