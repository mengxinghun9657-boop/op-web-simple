"""add chat history table

Revision ID: add_chat_history
Revises: 
Create Date: 2025-01-22

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers, used by Alembic.
revision = 'add_chat_history'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # 创建 chat_history 表
    op.create_table(
        'chat_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('context_data', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.now),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 创建索引
    op.create_index('idx_chat_history_user_id', 'chat_history', ['user_id'])
    op.create_index('idx_chat_history_created_at', 'chat_history', ['created_at'])


def downgrade():
    op.drop_index('idx_chat_history_created_at', table_name='chat_history')
    op.drop_index('idx_chat_history_user_id', table_name='chat_history')
    op.drop_table('chat_history')
