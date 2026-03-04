"""
添加系统配置表

Revision ID: add_system_config
Create Date: 2026-01-30
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers
revision = 'add_system_config'
down_revision = 'add_instance_config'
branch_labels = None
depends_on = None


def upgrade():
    """创建系统配置表"""
    op.create_table(
        'system_config',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True, comment='主键ID'),
        sa.Column('module', sa.String(50), nullable=False, comment='模块名称: cmdb, monitoring, analysis'),
        sa.Column('config_key', sa.String(100), nullable=False, comment='配置键'),
        sa.Column('config_value', sa.Text(), nullable=True, comment='配置值（JSON格式）'),
        sa.Column('description', sa.String(500), nullable=True, comment='配置说明'),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), nullable=False, comment='更新时间'),
        sa.Column('updated_by', sa.Integer(), nullable=True, comment='更新人ID'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('module', 'config_key', name='uq_module_config_key'),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id'], name='fk_system_config_updated_by'),
        mysql_engine='InnoDB',
        mysql_charset='utf8mb4',
        mysql_comment='系统配置表'
    )
    
    # 创建索引
    op.create_index('idx_module', 'system_config', ['module'])
    op.create_index('idx_config_key', 'system_config', ['config_key'])


def downgrade():
    """删除系统配置表"""
    op.drop_index('idx_config_key', table_name='system_config')
    op.drop_index('idx_module', table_name='system_config')
    op.drop_table('system_config')
