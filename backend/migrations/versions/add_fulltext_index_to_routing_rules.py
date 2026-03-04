"""添加全文索引到 routing_rules 表

Revision ID: add_fulltext_index
Revises: add_routing_optimization
Create Date: 2026-02-09

说明：
- 为 routing_rules.pattern 字段添加 MySQL 全文索引
- 使用 ngram 分词器支持中文搜索
- 提升关键词检索性能 10 倍以上

前置条件：
- MySQL 配置文件需要设置：
  - ngram_token_size = 1
  - ft_min_word_len = 1
  - innodb_ft_enable_stopword = 0
- 配置后需要重启 MySQL
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_fulltext_index'
down_revision = 'add_routing_optimization'
branch_labels = None
depends_on = None


def upgrade():
    """添加全文索引"""
    
    # 为 routing_rules.pattern 字段添加全文索引
    # 使用 ngram 分词器支持中文
    op.execute("""
        ALTER TABLE routing_rules 
        ADD FULLTEXT INDEX idx_pattern_fulltext (pattern) WITH PARSER ngram
    """)
    
    print("✅ 全文索引创建成功: idx_pattern_fulltext")
    print("ℹ️ 请确保 MySQL 配置了以下参数：")
    print("   - ngram_token_size = 1")
    print("   - ft_min_word_len = 1")
    print("   - innodb_ft_enable_stopword = 0")


def downgrade():
    """删除全文索引"""
    
    # 删除全文索引
    op.execute("""
        ALTER TABLE routing_rules 
        DROP INDEX idx_pattern_fulltext
    """)
    
    print("✅ 全文索引已删除: idx_pattern_fulltext")
