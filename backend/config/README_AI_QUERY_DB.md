# AI 智能查询功能 - 数据库初始化说明

## 概述

本目录包含 AI 智能查询功能所需的数据库表结构初始化脚本。

## 文件说明

### 1. mysql-init-ai-query.sql
独立的 SQL 初始化脚本，包含以下内容：
- 5 个核心表的创建
- 预定义的知识分类数据
- 2 个视图（活跃知识条目、最近查询统计）
- 2 个存储过程（清理软删除条目、更新标签使用次数）
- 1 个触发器（自动更新标签表）

### 2. Alembic 迁移文件
位于 `backend/migrations/versions/add_ai_intelligent_query_tables.py`
- 使用 Alembic 进行数据库版本管理
- 支持升级和回滚操作

## 数据库表结构

### 核心表

#### 1. knowledge_entries（知识库条目表）
存储手动添加和自动生成的知识条目。

**关键字段**：
- `title`: 标题
- `content`: 内容（摘要层 + 结论层）
- `metadata`: 详情层数据（JSON 格式）
- `source`: 来源类型（manual/auto）
- `deleted_at`: 软删除时间戳

**索引**：
- `idx_category`: 分类索引
- `idx_source`: 来源类型索引
- `idx_deleted_at`: 软删除索引
- `idx_fulltext_title_content`: 全文搜索索引

#### 2. ai_audit_logs（AI 查询审计日志表）
记录所有 AI 查询操作和安全事件。

**关键字段**：
- `action_type`: 操作类型（query_submit/query_success/sql_rejected 等）
- `nl_query`: 自然语言查询
- `generated_sql`: 生成的 SQL
- `execution_status`: 执行状态
- `execution_time_ms`: 执行时间

**索引**：
- `idx_user_id`: 用户 ID 索引
- `idx_action_type`: 操作类型索引
- `idx_created_at`: 创建时间索引

#### 3. report_index（报告索引表）
存储 MinIO 中所有分析报告的元数据。

**关键字段**：
- `task_id`: 任务 ID（唯一）
- `report_type`: 报告类型（resource_analysis/bcc_monitoring 等）
- `file_path`: MinIO 文件路径
- `summary`: 报告摘要（≤200字）
- `conclusion`: 关键结论（≤800字）
- `vectorized`: 是否已向量化

**索引**：
- `idx_task_id`: 任务 ID 索引
- `idx_report_type`: 报告类型索引
- `idx_generated_at`: 生成时间索引

#### 4. knowledge_categories（知识库分类表）
管理知识条目的分类。

**预定义分类**：
1. 故障处理
2. 操作规范
3. 优化建议
4. 常见问题
5. 最佳实践
6. 分析报告

#### 5. knowledge_tags（知识库标签表）
管理知识条目的标签及使用次数。

**自动维护**：
- 通过触发器自动创建新标签
- 通过存储过程定期更新使用次数

## 初始化方法

### 方法 1：使用 Alembic 迁移（推荐）

```bash
# 进入后端目录
cd backend

# 运行迁移
alembic upgrade head
```

**优点**：
- 支持版本管理
- 支持回滚操作
- 与现有迁移系统集成

### 方法 2：直接执行 SQL 脚本

```bash
# 连接到 MySQL
mysql -h localhost -u root -p

# 选择数据库
USE cluster_management;

# 执行初始化脚本
source backend/config/mysql-init-ai-query.sql;
```

**优点**：
- 简单直接
- 适合首次部署

### 方法 3：Docker 容器内执行

```bash
# 复制 SQL 文件到容器
docker cp backend/config/mysql-init-ai-query.sql cluster-mysql:/tmp/

# 进入容器
docker exec -it cluster-mysql bash

# 执行脚本
mysql -u root -p${MYSQL_ROOT_PASSWORD} cluster_management < /tmp/mysql-init-ai-query.sql
```

## 验证安装

执行以下 SQL 验证表是否创建成功：

```sql
-- 查看所有 AI 查询相关的表
SHOW TABLES LIKE '%knowledge%';
SHOW TABLES LIKE '%ai_%';
SHOW TABLES LIKE '%report%';

-- 验证知识分类是否插入
SELECT * FROM knowledge_categories;

-- 验证视图是否创建
SHOW FULL TABLES WHERE Table_type = 'VIEW';

-- 验证存储过程是否创建
SHOW PROCEDURE STATUS WHERE Db = 'cluster_management';

-- 验证触发器是否创建
SHOW TRIGGERS LIKE 'knowledge_entries';
```

预期结果：
- 5 个表：knowledge_entries, ai_audit_logs, report_index, knowledge_categories, knowledge_tags
- 2 个视图：v_active_knowledge_entries, v_recent_query_stats
- 2 个存储过程：sp_cleanup_deleted_knowledge_entries, sp_update_tag_usage_counts
- 1 个触发器：trg_knowledge_entry_insert_update_tags
- 6 条预定义分类数据

## 维护操作

### 定期清理软删除的条目

```sql
-- 手动执行清理（删除 30 天前软删除的条目）
CALL sp_cleanup_deleted_knowledge_entries();
```

**建议**：设置定时任务每周执行一次。

### 更新标签使用次数

```sql
-- 手动更新标签使用次数
CALL sp_update_tag_usage_counts();
```

**建议**：在批量导入知识条目后执行。

### 优化表性能

```sql
-- 分析表统计信息
ANALYZE TABLE knowledge_entries;
ANALYZE TABLE ai_audit_logs;
ANALYZE TABLE report_index;

-- 优化表碎片
OPTIMIZE TABLE knowledge_entries;
OPTIMIZE TABLE ai_audit_logs;
```

**建议**：每月执行一次。

## 索引优化建议

### 1. 全文搜索索引

如果知识库条目数量较大（> 10000），考虑使用专门的全文搜索引擎（如 Elasticsearch）。

### 2. 审计日志分区

如果审计日志增长迅速，考虑按月分区：

```sql
ALTER TABLE ai_audit_logs
PARTITION BY RANGE (YEAR(created_at) * 100 + MONTH(created_at)) (
    PARTITION p202601 VALUES LESS THAN (202602),
    PARTITION p202602 VALUES LESS THAN (202603),
    -- 添加更多分区...
    PARTITION pmax VALUES LESS THAN MAXVALUE
);
```

### 3. 报告索引优化

如果报告数量较大，考虑添加复合索引：

```sql
CREATE INDEX idx_report_type_generated_at 
ON report_index (report_type, generated_at DESC);
```

## 备份建议

### 1. 定期备份

```bash
# 备份所有 AI 查询相关的表
mysqldump -u root -p cluster_management \
  knowledge_entries \
  ai_audit_logs \
  report_index \
  knowledge_categories \
  knowledge_tags \
  > ai_query_backup_$(date +%Y%m%d).sql
```

### 2. 备份向量数据库

```bash
# 备份向量数据库文件
tar -czf vector_store_backup_$(date +%Y%m%d).tar.gz \
  /var/lib/docker/volumes/backend_vector_store
```

### 3. 同步备份

确保 MySQL 数据和向量数据库文件同步备份，以保持数据一致性。

## 故障排查

### 问题 1：表创建失败

**可能原因**：
- MySQL 版本过低（需要 8.0+）
- 字符集不支持 utf8mb4
- 权限不足

**解决方法**：
```sql
-- 检查 MySQL 版本
SELECT VERSION();

-- 检查字符集
SHOW VARIABLES LIKE 'character_set%';

-- 检查权限
SHOW GRANTS FOR CURRENT_USER();
```

### 问题 2：触发器创建失败

**可能原因**：
- MySQL 不支持 JSON_TABLE 函数（需要 8.0+）

**解决方法**：
- 升级 MySQL 到 8.0+
- 或手动管理标签表（不使用触发器）

### 问题 3：全文索引不工作

**可能原因**：
- 表引擎不是 InnoDB
- 字段类型不支持全文索引

**解决方法**：
```sql
-- 检查表引擎
SHOW TABLE STATUS WHERE Name = 'knowledge_entries';

-- 重建全文索引
ALTER TABLE knowledge_entries DROP INDEX idx_fulltext_title_content;
ALTER TABLE knowledge_entries ADD FULLTEXT INDEX idx_fulltext_title_content (title, content);
```

## 性能监控

### 慢查询监控

```sql
-- 查看慢查询日志配置
SHOW VARIABLES LIKE 'slow_query%';

-- 启用慢查询日志
SET GLOBAL slow_query_log = 'ON';
SET GLOBAL long_query_time = 2;
```

### 索引使用情况

```sql
-- 查看索引使用统计
SELECT 
    TABLE_NAME,
    INDEX_NAME,
    SEQ_IN_INDEX,
    COLUMN_NAME,
    CARDINALITY
FROM information_schema.STATISTICS
WHERE TABLE_SCHEMA = 'cluster_management'
    AND TABLE_NAME IN ('knowledge_entries', 'ai_audit_logs', 'report_index')
ORDER BY TABLE_NAME, INDEX_NAME, SEQ_IN_INDEX;
```

## 相关文档

- [AI 智能查询功能需求文档](../../.kiro/specs/ai-intelligent-query/requirements.md)
- [AI 智能查询功能设计文档](../../.kiro/specs/ai-intelligent-query/design.md)
- [AI 智能查询功能任务列表](../../.kiro/specs/ai-intelligent-query/tasks.md)

## 联系方式

如有问题，请联系开发团队或查看项目文档。
