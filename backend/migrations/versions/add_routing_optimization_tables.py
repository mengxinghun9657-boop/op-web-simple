"""添加意图路由优化相关表

Revision ID: add_routing_optimization
Revises: 
Create Date: 2026-02-06

说明：
- routing_rules: 路由规则表，包含 metadata 字段用于存储推荐的表、数据库等信息
- routing_logs: 路由日志表，记录每次路由的详细信息
- routing_feedback: 路由反馈表，记录用户对路由结果的反馈
- rule_suggestions: 规则建议表，基于反馈自动生成规则建议
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'add_routing_optimization'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """创建意图路由优化相关表"""
    
    # 1. 创建 routing_rules 表
    op.create_table(
        'routing_rules',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('pattern', sa.String(500), nullable=False, comment='查询模式'),
        sa.Column('intent_type', sa.String(50), nullable=False, comment='意图类型'),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='50', comment='优先级(1-100)'),
        sa.Column('description', sa.Text(), nullable=True, comment='规则描述'),
        sa.Column('metadata', mysql.JSON(), nullable=True, comment='规则元数据（推荐的表、数据库等）'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1', comment='是否启用'),
        sa.Column('created_by', sa.String(100), nullable=True, comment='创建者'),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP'), comment='创建时间'),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), comment='更新时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_intent_type', 'intent_type'),
        sa.Index('idx_priority', 'priority'),
        sa.Index('idx_is_active', 'is_active'),
        mysql_engine='InnoDB',
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci',
        comment='路由规则表'
    )
    
    # 2. 创建 routing_logs 表
    op.create_table(
        'routing_logs',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('query', sa.Text(), nullable=False, comment='用户查询'),
        sa.Column('intent_type', sa.String(50), nullable=False, comment='路由到的意图类型'),
        sa.Column('confidence', sa.DECIMAL(5, 4), nullable=False, comment='置信度'),
        sa.Column('routing_method', sa.String(50), nullable=False, comment='路由方法'),
        sa.Column('matched_rule_id', sa.Integer(), nullable=True, comment='匹配的规则ID'),
        sa.Column('similarity_score', sa.DECIMAL(5, 4), nullable=True, comment='相似度分数'),
        sa.Column('user_id', sa.String(100), nullable=True, comment='用户ID'),
        sa.Column('session_id', sa.String(100), nullable=True, comment='会话ID'),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP'), comment='创建时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['matched_rule_id'], ['routing_rules.id'], ondelete='SET NULL'),
        sa.Index('idx_intent_type', 'intent_type'),
        sa.Index('idx_confidence', 'confidence'),
        sa.Index('idx_routing_method', 'routing_method'),
        sa.Index('idx_created_at', 'created_at'),
        sa.Index('idx_user_id', 'user_id'),
        mysql_engine='InnoDB',
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci',
        comment='路由日志表'
    )
    
    # 3. 创建 routing_feedback 表
    op.create_table(
        'routing_feedback',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('routing_log_id', sa.Integer(), nullable=False, comment='路由日志ID'),
        sa.Column('correct_intent', sa.String(50), nullable=False, comment='正确的意图类型'),
        sa.Column('user_id', sa.String(100), nullable=False, comment='反馈用户ID'),
        sa.Column('comment', sa.Text(), nullable=True, comment='反馈备注'),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP'), comment='创建时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['routing_log_id'], ['routing_logs.id'], ondelete='CASCADE'),
        sa.Index('idx_routing_log_id', 'routing_log_id'),
        sa.Index('idx_correct_intent', 'correct_intent'),
        sa.Index('idx_created_at', 'created_at'),
        mysql_engine='InnoDB',
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci',
        comment='路由反馈表'
    )
    
    # 4. 创建 rule_suggestions 表
    op.create_table(
        'rule_suggestions',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('pattern', sa.String(500), nullable=False, comment='建议的查询模式'),
        sa.Column('suggested_intent', sa.String(50), nullable=False, comment='建议的意图类型'),
        sa.Column('confidence', sa.DECIMAL(5, 4), nullable=False, comment='建议置信度'),
        sa.Column('support_count', sa.Integer(), nullable=False, comment='支持证据数量'),
        sa.Column('evidence', mysql.JSON(), nullable=True, comment='支持证据(反馈记录)'),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending', comment='状态'),
        sa.Column('adopted_by', sa.String(100), nullable=True, comment='采纳者'),
        sa.Column('adopted_at', sa.TIMESTAMP(), nullable=True, comment='采纳时间'),
        sa.Column('created_rule_id', sa.Integer(), nullable=True, comment='创建的规则ID'),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP'), comment='创建时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['created_rule_id'], ['routing_rules.id'], ondelete='SET NULL'),
        sa.Index('idx_status', 'status'),
        sa.Index('idx_suggested_intent', 'suggested_intent'),
        mysql_engine='InnoDB',
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci',
        comment='规则建议表'
    )


def downgrade():
    """删除意图路由优化相关表"""
    op.drop_table('rule_suggestions')
    op.drop_table('routing_feedback')
    op.drop_table('routing_logs')
    op.drop_table('routing_rules')
