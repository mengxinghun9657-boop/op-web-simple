"""
添加实例配置表

Revision ID: add_instance_config
Create Date: 2026-01-26
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers
revision = 'add_instance_config'
down_revision = 'add_ai_intelligent_query'
branch_labels = None
depends_on = None


def upgrade():
    """创建实例配置表"""
    op.create_table(
        'instance_config',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True, comment='主键ID'),
        sa.Column('config_type', sa.String(50), nullable=False, comment='配置类型'),
        sa.Column('instance_ids', sa.Text(), nullable=False, comment='实例ID列表（JSON数组格式）'),
        sa.Column('description', sa.String(500), nullable=True, comment='配置说明'),
        sa.Column('created_by', sa.String(100), nullable=True, comment='创建者'),
        sa.Column('updated_by', sa.String(100), nullable=True, comment='更新者'),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), nullable=False, comment='更新时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('config_type', name='uk_config_type'),
        mysql_engine='InnoDB',
        mysql_charset='utf8mb4',
        mysql_comment='实例ID配置表'
    )
    
    # 创建索引
    op.create_index('idx_config_type', 'instance_config', ['config_type'])


def downgrade():
    """删除实例配置表"""
    op.drop_index('idx_config_type', table_name='instance_config')
    op.drop_table('instance_config')
