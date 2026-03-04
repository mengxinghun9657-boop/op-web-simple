"""add unique constraint to knowledge_entries

Revision ID: add_unique_constraint_ke
Revises: add_ai_intelligent_query_tables
Create Date: 2026-02-04 16:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_unique_constraint_ke'
down_revision = 'add_ai_intelligent_query_tables'
branch_labels = None
depends_on = None


def upgrade():
    """
    添加唯一约束：防止同一个 source_id 创建多个知识条目
    """
    # 1. 先删除重复的记录（保留最早创建的）
    op.execute("""
        DELETE ke1 FROM knowledge_entries ke1
        INNER JOIN knowledge_entries ke2
        WHERE ke1.source = 'auto'
          AND ke2.source = 'auto'
          AND ke1.source_id = ke2.source_id
          AND ke1.id > ke2.id
          AND ke1.deleted_at IS NULL
          AND ke2.deleted_at IS NULL
    """)
    
    # 2. 添加唯一索引（只对未删除的记录生效）
    # 注意：MySQL 不支持部分索引，所以我们使用触发器或应用层控制
    # 这里创建一个普通的唯一索引，删除的记录通过 deleted_at 区分
    op.create_index(
        'idx_unique_auto_source',
        'knowledge_entries',
        ['source', 'source_id', 'deleted_at'],
        unique=True
    )


def downgrade():
    """
    移除唯一约束
    """
    op.drop_index('idx_unique_auto_source', table_name='knowledge_entries')
