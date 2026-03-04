"""初始化告警相关表

Revision ID: 001
Revises: 
Create Date: 2026-02-10

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """创建告警相关表"""
    
    # 1. 创建告警记录表
    op.create_table(
        'alert_records',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, comment='主键ID'),
        sa.Column('alert_type', sa.String(200), nullable=False, comment='告警类型'),
        sa.Column('ip', sa.String(100), nullable=True, comment='节点IP地址'),
        sa.Column('cluster_id', sa.String(200), nullable=True, comment='集群ID'),
        sa.Column('instance_id', sa.String(200), nullable=True, comment='实例ID'),
        sa.Column('hostname', sa.String(200), nullable=True, comment='主机名/节点名'),
        sa.Column('component', sa.String(100), nullable=True, comment='组件类型'),
        sa.Column('severity', sa.String(50), nullable=False, comment='严重程度'),
        sa.Column('timestamp', sa.DateTime(), nullable=False, comment='告警发生时间'),
        sa.Column('file_path', sa.String(1000), nullable=True, comment='源文件路径'),
        sa.Column('raw_data', sa.JSON(), nullable=True, comment='告警原始数据'),
        sa.Column('status', sa.String(50), nullable=True, comment='处理状态'),
        sa.Column('is_cce_cluster', sa.Boolean(), nullable=True, comment='是否CCE集群告警'),
        sa.Column('created_at', sa.DateTime(), nullable=True, comment='记录创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=True, comment='记录更新时间'),
        sa.PrimaryKeyConstraint('id'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci'
    )
    
    # 创建索引
    op.create_index('idx_alert_type', 'alert_records', ['alert_type'])
    op.create_index('idx_ip', 'alert_records', ['ip'])
    op.create_index('idx_cluster_id', 'alert_records', ['cluster_id'])
    op.create_index('idx_component', 'alert_records', ['component'])
    op.create_index('idx_severity', 'alert_records', ['severity'])
    op.create_index('idx_timestamp', 'alert_records', ['timestamp'])
    op.create_index('idx_status', 'alert_records', ['status'])
    op.create_index('idx_is_cce_cluster', 'alert_records', ['is_cce_cluster'])
    op.create_index('idx_created_at', 'alert_records', ['created_at'])
    op.create_index('idx_timestamp_severity', 'alert_records', ['timestamp', 'severity'])
    op.create_index('idx_cluster_timestamp', 'alert_records', ['cluster_id', 'timestamp'])
    op.create_index('idx_component_timestamp', 'alert_records', ['component', 'timestamp'])
    op.create_index('idx_status_timestamp', 'alert_records', ['status', 'timestamp'])
    
    # 2. 创建诊断结果表
    op.create_table(
        'diagnosis_results',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, comment='主键ID'),
        sa.Column('alert_id', sa.BigInteger(), nullable=False, comment='关联告警ID'),
        sa.Column('source', sa.String(50), nullable=False, comment='诊断来源'),
        sa.Column('manual_matched', sa.Boolean(), nullable=True, comment='是否匹配到手册'),
        sa.Column('manual_name_zh', sa.String(500), nullable=True, comment='故障中文名称'),
        sa.Column('manual_solution', sa.Text(), nullable=True, comment='手册解决方案'),
        sa.Column('manual_impact', sa.Text(), nullable=True, comment='影响描述'),
        sa.Column('manual_recovery', sa.Text(), nullable=True, comment='恢复方案'),
        sa.Column('danger_level', sa.String(50), nullable=True, comment='危害等级'),
        sa.Column('customer_aware', sa.Boolean(), nullable=True, comment='是否客户有感'),
        sa.Column('api_task_id', sa.String(200), nullable=True, comment='API任务ID'),
        sa.Column('api_status', sa.String(50), nullable=True, comment='API任务状态'),
        sa.Column('api_items_count', sa.Integer(), nullable=True, comment='诊断项总数'),
        sa.Column('api_error_count', sa.Integer(), nullable=True, comment='错误项数量'),
        sa.Column('api_warning_count', sa.Integer(), nullable=True, comment='警告项数量'),
        sa.Column('api_abnormal_count', sa.Integer(), nullable=True, comment='异常项数量'),
        sa.Column('api_diagnosis', sa.JSON(), nullable=True, comment='API诊断完整报告'),
        sa.Column('ai_interpretation', sa.Text(), nullable=True, comment='AI解读完整内容'),
        sa.Column('ai_category', sa.String(100), nullable=True, comment='AI问题分类'),
        sa.Column('ai_root_cause', sa.Text(), nullable=True, comment='根本原因分析'),
        sa.Column('ai_impact', sa.Text(), nullable=True, comment='影响评估'),
        sa.Column('ai_solution', sa.Text(), nullable=True, comment='修复建议'),
        sa.Column('notified', sa.Boolean(), nullable=True, comment='是否已发送通知'),
        sa.Column('notified_at', sa.DateTime(), nullable=True, comment='通知发送时间'),
        sa.Column('created_at', sa.DateTime(), nullable=True, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=True, comment='更新时间'),
        sa.ForeignKeyConstraint(['alert_id'], ['alert_records.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci'
    )
    
    # 创建索引
    op.create_index('idx_alert_id', 'diagnosis_results', ['alert_id'], unique=True)
    op.create_index('idx_source', 'diagnosis_results', ['source'])
    op.create_index('idx_danger_level', 'diagnosis_results', ['danger_level'])
    op.create_index('idx_api_status', 'diagnosis_results', ['api_status'])
    op.create_index('idx_manual_matched', 'diagnosis_results', ['manual_matched'])
    
    # 3. 创建Webhook配置表
    op.create_table(
        'webhook_configs',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, comment='主键ID'),
        sa.Column('name', sa.String(200), nullable=False, comment='配置名称'),
        sa.Column('type', sa.String(50), nullable=False, comment='Webhook类型'),
        sa.Column('url', sa.String(1000), nullable=False, comment='Webhook URL'),
        sa.Column('access_token', sa.String(500), nullable=True, comment='访问令牌'),
        sa.Column('secret', sa.String(500), nullable=True, comment='签名密钥'),
        sa.Column('enabled', sa.Boolean(), nullable=True, comment='是否启用'),
        sa.Column('severity_filter', sa.String(200), nullable=True, comment='严重程度过滤'),
        sa.Column('component_filter', sa.String(500), nullable=True, comment='组件过滤'),
        sa.Column('created_at', sa.DateTime(), nullable=True, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=True, comment='更新时间'),
        sa.PrimaryKeyConstraint('id'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci'
    )
    
    # 创建索引
    op.create_index('idx_type_enabled', 'webhook_configs', ['type', 'enabled'])
    
    # 4. 创建故障手册表
    op.create_table(
        'fault_manual',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, comment='主键ID'),
        sa.Column('category', sa.String(100), nullable=False, comment='类别'),
        sa.Column('alert_type', sa.String(200), nullable=False, comment='告警类型'),
        sa.Column('has_level', sa.String(50), nullable=True, comment='HAS级别'),
        sa.Column('name_zh', sa.String(500), nullable=True, comment='中文名称'),
        sa.Column('impact', sa.Text(), nullable=True, comment='影响描述'),
        sa.Column('recovery_plan', sa.Text(), nullable=True, comment='恢复方案'),
        sa.Column('danger_level', sa.String(50), nullable=True, comment='危害等级'),
        sa.Column('customer_aware', sa.Boolean(), nullable=True, comment='是否客户有感'),
        sa.Column('manual_check', sa.Text(), nullable=True, comment='手动判断方法'),
        sa.Column('created_at', sa.DateTime(), nullable=True, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=True, comment='更新时间'),
        sa.PrimaryKeyConstraint('id'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci'
    )
    
    # 创建索引
    op.create_index('idx_category', 'fault_manual', ['category'])
    op.create_index('uk_category_type', 'fault_manual', ['category', 'alert_type'], unique=True)


def downgrade():
    """删除告警相关表"""
    op.drop_table('fault_manual')
    op.drop_table('webhook_configs')
    op.drop_table('diagnosis_results')
    op.drop_table('alert_records')
