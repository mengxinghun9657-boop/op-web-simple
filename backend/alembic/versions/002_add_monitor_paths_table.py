"""add monitor paths table

Revision ID: 002_monitor_paths
Revises: 001_alert_tables
Create Date: 2026-02-10

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '002_monitor_paths'
down_revision = '001_alert_tables'
branch_labels = None
depends_on = None


def upgrade():
    """创建监控路径配置表"""
    op.create_table(
        'monitor_paths',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, comment='主键ID'),
        sa.Column('path', sa.String(1000), nullable=False, comment='监控路径（绝对路径）'),
        sa.Column('description', sa.String(500), nullable=True, comment='路径描述'),
        sa.Column('enabled', sa.Boolean(), server_default='1', nullable=False, comment='是否启用'),
        sa.Column('priority', sa.Integer(), server_default='50', nullable=False, comment='优先级（1-100，数值越大优先级越高）'),
        sa.Column('file_pattern', sa.String(200), server_default='*.txt', nullable=False, comment='文件匹配模式'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), comment='更新时间'),
        sa.PrimaryKeyConstraint('id'),
        comment='监控路径配置表'
    )
    
    # 创建唯一约束：防止重复配置相同路径
    op.create_index('uk_path', 'monitor_paths', ['path'], unique=True)
    
    # 创建复合索引：优化查询启用的路径并按优先级排序
    op.create_index('idx_enabled_priority', 'monitor_paths', ['enabled', 'priority'])


def downgrade():
    """删除监控路径配置表"""
    op.drop_table('monitor_paths')
