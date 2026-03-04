"""add AI intelligent query tables

Revision ID: add_ai_intelligent_query
Revises: add_chat_history
Create Date: 2026-01-23

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql
from datetime import datetime


# revision identifiers, used by Alembic.
revision = 'add_ai_intelligent_query'
down_revision = 'add_chat_history'
branch_labels = None
depends_on = None


def upgrade():
    # ============================================
    # 创建知识库条目表
    # ============================================
    op.create_table(
        'knowledge_entries',
        sa.Column('id', sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column('title', sa.String(500), nullable=False, comment='标题'),
        sa.Column('content', sa.Text(), nullable=False, comment='内容（摘要层 + 结论层）'),
        sa.Column('metadata', mysql.JSON(), nullable=True, comment='详情层数据（JSON 格式）'),
        sa.Column('category', sa.String(100), nullable=True, comment='分类'),
        sa.Column('tags', mysql.JSON(), nullable=True, comment='标签数组'),
        sa.Column('priority', sa.Enum('low', 'medium', 'high', name='priority_enum'), 
                  nullable=False, server_default='medium', comment='优先级'),
        
        # 来源信息
        sa.Column('source', sa.Enum('manual', 'auto', name='source_enum'), 
                  nullable=False, server_default='manual', comment='来源类型'),
        sa.Column('source_type', sa.String(50), nullable=True, comment='报告类型（auto 时有效）'),
        sa.Column('source_id', sa.String(100), nullable=True, comment='任务ID（auto 时有效）'),
        
        # 作者信息
        sa.Column('author', sa.String(100), nullable=False, comment='创建者'),
        sa.Column('updated_by', sa.String(100), nullable=True, comment='最后更新者'),
        
        # 标记字段
        sa.Column('auto_generated', sa.Boolean(), nullable=False, server_default='0', comment='是否自动生成'),
        sa.Column('manually_edited', sa.Boolean(), nullable=False, server_default='0', comment='是否被手动编辑'),
        
        # 时间戳
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP'), comment='创建时间'),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False, 
                  server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), comment='更新时间'),
        sa.Column('deleted_at', sa.TIMESTAMP(), nullable=True, comment='软删除时间'),
        sa.Column('deleted_by', sa.String(100), nullable=True, comment='删除者'),
        
        sa.PrimaryKeyConstraint('id'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci',
        mysql_engine='InnoDB',
        comment='知识库条目表'
    )
    
    # 创建索引
    op.create_index('idx_category', 'knowledge_entries', ['category'])
    op.create_index('idx_source', 'knowledge_entries', ['source', 'source_type'])
    op.create_index('idx_created_at', 'knowledge_entries', ['created_at'])
    op.create_index('idx_deleted_at', 'knowledge_entries', ['deleted_at'])
    op.create_index('idx_author', 'knowledge_entries', ['author'])
    
    # ============================================
    # 创建 AI 查询审计日志表
    # ============================================
    op.create_table(
        'ai_audit_logs',
        sa.Column('id', sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column('user_id', sa.String(100), nullable=False, comment='用户ID'),
        sa.Column('username', sa.String(100), nullable=False, comment='用户名'),
        sa.Column('action_type', sa.Enum(
            'query_submit', 'query_success', 'query_error', 'query_timeout',
            'sql_rejected', 'knowledge_create', 'knowledge_update', 
            'knowledge_delete', 'auth_verify_success', 'auth_verify_failed',
            name='action_type_enum'
        ), nullable=False, comment='操作类型'),
        
        # 查询相关
        sa.Column('nl_query', sa.Text(), nullable=True, comment='自然语言查询'),
        sa.Column('generated_sql', sa.Text(), nullable=True, comment='生成的SQL'),
        sa.Column('intent_type', sa.String(50), nullable=True, comment='意图类型'),
        
        # 执行结果
        sa.Column('execution_status', sa.Enum('success', 'error', 'timeout', 'rejected', name='execution_status_enum'), 
                  nullable=True, comment='执行状态'),
        sa.Column('execution_time_ms', sa.Integer(), nullable=True, comment='执行时间（毫秒）'),
        sa.Column('row_count', sa.Integer(), nullable=True, comment='返回行数'),
        sa.Column('error_message', sa.Text(), nullable=True, comment='错误信息'),
        
        # 安全事件
        sa.Column('security_event_type', sa.String(100), nullable=True, comment='安全事件类型'),
        sa.Column('security_event_details', mysql.JSON(), nullable=True, comment='安全事件详情'),
        
        # 知识库操作
        sa.Column('knowledge_entry_id', sa.BigInteger(), nullable=True, comment='知识条目ID'),
        sa.Column('knowledge_operation', mysql.JSON(), nullable=True, comment='知识库操作详情'),
        
        # 元数据
        sa.Column('ip_address', sa.String(50), nullable=True, comment='IP地址'),
        sa.Column('user_agent', sa.Text(), nullable=True, comment='User Agent'),
        sa.Column('session_id', sa.String(100), nullable=True, comment='会话ID'),
        
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP'), comment='创建时间'),
        
        sa.PrimaryKeyConstraint('id'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci',
        mysql_engine='InnoDB',
        comment='AI查询审计日志表'
    )
    
    # 创建索引
    op.create_index('idx_user_id', 'ai_audit_logs', ['user_id'])
    op.create_index('idx_username', 'ai_audit_logs', ['username'])
    op.create_index('idx_action_type', 'ai_audit_logs', ['action_type'])
    op.create_index('idx_created_at', 'ai_audit_logs', ['created_at'])
    op.create_index('idx_execution_status', 'ai_audit_logs', ['execution_status'])
    op.create_index('idx_session_id', 'ai_audit_logs', ['session_id'])
    
    # ============================================
    # 创建报告索引表
    # ============================================
    op.create_table(
        'report_index',
        sa.Column('id', sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column('task_id', sa.String(100), nullable=False, unique=True, comment='任务ID'),
        sa.Column('report_type', sa.Enum(
            'resource_analysis', 'bcc_monitoring', 
            'bos_monitoring', 'operational_analysis',
            name='report_type_enum'
        ), nullable=False, comment='报告类型'),
        
        # 文件信息
        sa.Column('file_path', sa.String(500), nullable=False, comment='MinIO 文件路径'),
        sa.Column('file_format', sa.Enum('html', 'json', 'excel', name='file_format_enum'), 
                  nullable=False, comment='文件格式'),
        sa.Column('file_size_bytes', sa.BigInteger(), nullable=True, comment='文件大小'),
        
        # 内容摘要
        sa.Column('summary', sa.Text(), nullable=True, comment='报告摘要（≤200字）'),
        sa.Column('conclusion', sa.Text(), nullable=True, comment='关键结论（≤800字）'),
        
        # 时间信息
        sa.Column('generated_at', sa.TIMESTAMP(), nullable=False, comment='报告生成时间'),
        sa.Column('indexed_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP'), comment='索引创建时间'),
        
        # 向量化状态
        sa.Column('vectorized', sa.Boolean(), nullable=False, server_default='0', comment='是否已向量化'),
        sa.Column('vector_id', sa.String(100), nullable=True, comment='向量数据库中的ID'),
        
        sa.PrimaryKeyConstraint('id'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci',
        mysql_engine='InnoDB',
        comment='报告索引表'
    )
    
    # 创建索引
    op.create_index('idx_task_id', 'report_index', ['task_id'])
    op.create_index('idx_report_type', 'report_index', ['report_type'])
    op.create_index('idx_generated_at', 'report_index', ['generated_at'])
    op.create_index('idx_vectorized', 'report_index', ['vectorized'])
    
    # ============================================
    # 创建知识库分类表
    # ============================================
    op.create_table(
        'knowledge_categories',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('name', sa.String(100), nullable=False, unique=True, comment='分类名称'),
        sa.Column('description', sa.String(500), nullable=True, comment='分类描述'),
        sa.Column('display_order', sa.Integer(), nullable=False, server_default='0', comment='显示顺序'),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP'), comment='创建时间'),
        sa.Column('created_by', sa.String(100), nullable=True, comment='创建者'),
        
        sa.PrimaryKeyConstraint('id'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci',
        mysql_engine='InnoDB',
        comment='知识库分类表'
    )
    
    # 创建索引
    op.create_index('idx_display_order', 'knowledge_categories', ['display_order'])
    
    # ============================================
    # 创建知识库标签表
    # ============================================
    op.create_table(
        'knowledge_tags',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('name', sa.String(50), nullable=False, unique=True, comment='标签名称'),
        sa.Column('usage_count', sa.Integer(), nullable=False, server_default='0', comment='使用次数'),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP'), comment='创建时间'),
        
        sa.PrimaryKeyConstraint('id'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci',
        mysql_engine='InnoDB',
        comment='知识库标签表'
    )
    
    # 创建索引
    op.create_index('idx_usage_count', 'knowledge_tags', ['usage_count'])
    
    # ============================================
    # 插入预定义的知识分类
    # ============================================
    op.execute("""
        INSERT INTO knowledge_categories (name, description, display_order, created_by)
        VALUES
            ('故障处理', '系统故障排查和处理方案', 1, 'system'),
            ('操作规范', '日常运维操作规范和流程', 2, 'system'),
            ('优化建议', '系统性能优化和改进建议', 3, 'system'),
            ('常见问题', '常见问题解答（FAQ）', 4, 'system'),
            ('最佳实践', '行业最佳实践和经验总结', 5, 'system'),
            ('分析报告', '自动生成的分析报告摘要', 6, 'system')
    """)


def downgrade():
    # 删除表（按依赖关系逆序）
    op.drop_table('knowledge_tags')
    op.drop_table('knowledge_categories')
    op.drop_table('report_index')
    op.drop_table('ai_audit_logs')
    op.drop_table('knowledge_entries')
    
    # 删除枚举类型
    op.execute('DROP TYPE IF EXISTS priority_enum')
    op.execute('DROP TYPE IF EXISTS source_enum')
    op.execute('DROP TYPE IF EXISTS action_type_enum')
    op.execute('DROP TYPE IF EXISTS execution_status_enum')
    op.execute('DROP TYPE IF EXISTS report_type_enum')
    op.execute('DROP TYPE IF EXISTS file_format_enum')
