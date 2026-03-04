"""create alert tables

Revision ID: 001_alert_tables
Revises: 
Create Date: 2026-02-10

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers
revision = '001_alert_tables'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # 创建告警记录表
    op.create_table(
        'alert_records',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, comment='主键ID'),
        sa.Column('alert_type', sa.String(100), nullable=False, comment='告警类型'),
        sa.Column('ip', sa.String(50), nullable=True, comment='实例IP'),
        sa.Column('instance_id', sa.String(100), nullable=True, comment='实例ID'),
        sa.Column('component', sa.String(50), nullable=True, comment='组件类型'),
        sa.Column('severity', sa.String(20), nullable=False, comment='严重程度'),
        sa.Column('timestamp', sa.DateTime(), nullable=False, comment='告警时间'),
        sa.Column('file_path', sa.String(500), nullable=True, comment='源文件路径'),
        sa.Column('raw_data', mysql.JSON(), nullable=True, comment='原始数据'),
        sa.Column('status', sa.String(20), server_default='pending', comment='处理状态'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_alert_type', 'alert_records', ['alert_type'])
    op.create_index('idx_ip', 'alert_records', ['ip'])
    op.create_index('idx_timestamp', 'alert_records', ['timestamp'])
    op.create_index('idx_status', 'alert_records', ['status'])
    op.create_index('idx_severity', 'alert_records', ['severity'])
    
    # 创建诊断结果表
    op.create_table(
        'diagnosis_results',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, comment='主键ID'),
        sa.Column('alert_id', sa.BigInteger(), nullable=False, comment='关联告警ID'),
        sa.Column('source', sa.String(20), nullable=False, comment='诊断来源'),
        sa.Column('manual_matched', sa.Boolean(), server_default='0', comment='是否匹配到手册'),
        sa.Column('manual_name_zh', sa.String(200), nullable=True, comment='故障中文名称'),
        sa.Column('manual_solution', sa.Text(), nullable=True, comment='手册解决方案'),
        sa.Column('manual_impact', sa.Text(), nullable=True, comment='影响描述'),
        sa.Column('manual_recovery', sa.Text(), nullable=True, comment='恢复方案'),
        sa.Column('danger_level', sa.String(20), nullable=True, comment='危害等级'),
        sa.Column('customer_aware', sa.Boolean(), nullable=True, comment='是否客户有感'),
        sa.Column('api_task_id', sa.String(100), nullable=True, comment='API任务ID'),
        sa.Column('api_status', sa.String(20), nullable=True, comment='API任务状态'),
        sa.Column('api_diagnosis', mysql.JSON(), nullable=True, comment='API诊断详情'),
        sa.Column('ai_interpretation', sa.Text(), nullable=True, comment='AI解读内容'),
        sa.Column('ai_category', sa.String(50), nullable=True, comment='AI分类'),
        sa.Column('ai_root_cause', sa.Text(), nullable=True, comment='根本原因'),
        sa.Column('ai_impact', sa.Text(), nullable=True, comment='影响评估'),
        sa.Column('ai_solution', sa.Text(), nullable=True, comment='修复建议'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['alert_id'], ['alert_records.id'], ondelete='CASCADE')
    )
    op.create_index('idx_alert_id', 'diagnosis_results', ['alert_id'])
    op.create_index('idx_source', 'diagnosis_results', ['source'])

    # 创建Webhook配置表
    op.create_table(
        'webhook_configs',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, comment='主键ID'),
        sa.Column('name', sa.String(100), nullable=False, comment='配置名称'),
        sa.Column('type', sa.String(20), nullable=False, comment='Webhook类型'),
        sa.Column('url', sa.String(500), nullable=False, comment='Webhook URL'),
        sa.Column('access_token', sa.String(200), nullable=True, comment='访问令牌'),
        sa.Column('secret', sa.String(200), nullable=True, comment='签名密钥'),
        sa.Column('enabled', sa.Boolean(), server_default='1', comment='是否启用'),
        sa.Column('severity_filter', sa.String(100), nullable=True, comment='严重程度过滤'),
        sa.Column('component_filter', sa.String(200), nullable=True, comment='组件过滤'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_enabled', 'webhook_configs', ['enabled'])
    
    # 创建故障手册表
    op.create_table(
        'fault_manual',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, comment='主键ID'),
        sa.Column('category', sa.String(50), nullable=False, comment='类别'),
        sa.Column('alert_type', sa.String(100), nullable=False, comment='告警类型'),
        sa.Column('has_level', sa.String(20), nullable=True, comment='HAS级别'),
        sa.Column('name_zh', sa.String(200), nullable=True, comment='中文名称'),
        sa.Column('impact', sa.Text(), nullable=True, comment='影响描述'),
        sa.Column('recovery_plan', sa.Text(), nullable=True, comment='恢复方案'),
        sa.Column('danger_level', sa.String(20), nullable=True, comment='危害等级'),
        sa.Column('customer_aware', sa.Boolean(), nullable=True, comment='是否客户有感'),
        sa.Column('manual_check', sa.Text(), nullable=True, comment='手动判断方法'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('uk_category_type', 'fault_manual', ['category', 'alert_type'], unique=True)
    op.create_index('idx_alert_type', 'fault_manual', ['alert_type'])


def downgrade():
    op.drop_table('fault_manual')
    op.drop_table('webhook_configs')
    op.drop_table('diagnosis_results')
    op.drop_table('alert_records')
