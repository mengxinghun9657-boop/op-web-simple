# 报告自动向量化功能

## 概述

报告自动向量化功能实现了对 MinIO 中存储的分析报告的自动向量化和知识库索引，使得用户可以通过自然语言查询历史报告内容。

## 功能特性

### 1. 自动向量化流程

当新的分析报告上传到 MinIO 时，系统会自动：

1. **检测新报告**：后台任务定期扫描 MinIO 中的报告文件
2. **下载报告内容**：从 MinIO 下载报告文件（HTML/JSON 格式）
3. **提取内容层级**：
   - **摘要层**（≤200字）：集群数量、健康状态统计等核心信息
   - **结论层**（≤800字）：关键发现、问题列表、优化建议
   - **详情层**（完整数据）：所有详细指标和数据
4. **向量化**：使用 Embedding 模型将摘要层和结论层转换为向量
5. **存储向量**：将向量存储到 FAISS 向量数据库
6. **更新索引**：更新 MySQL `report_index` 表
7. **创建知识条目**：自动创建知识库条目（`source=auto`）

### 2. 知识库自动生成

向量化成功后，系统会自动创建知识库条目：

- **标题**：`{报告类型} - {生成日期}`
- **内容**：结论层内容（关键发现和建议）
- **元数据**：详情层数据（JSON 格式）
- **来源标记**：
  - `source = "auto"`：自动生成
  - `source_type`：报告类型（resource_analysis, bcc_monitoring 等）
  - `source_id`：任务 ID
  - `auto_generated = true`：标记为自动生成

### 3. 错误处理

- **向量化失败**：记录错误日志到 `ai_audit_logs` 表，但不影响报告的正常存储和访问
- **重试机制**：后台任务会在下次扫描时重试失败的报告
- **降级策略**：即使向量化失败，报告仍然可以通过其他方式访问

## 使用方式

### 1. 自动模式（推荐）

系统启动时会自动启动后台向量化任务，默认每 5 分钟扫描一次 MinIO：

```python
# 在 main.py 中自动启动
vectorization_task = asyncio.create_task(
    background_vectorization_task(interval_seconds=300)
)
```

### 2. 手动触发

超级管理员可以通过 API 手动触发向量化：

#### 向量化单个报告

```bash
POST /api/v1/ai/vectorize-report
Authorization: Bearer <token>

{
  "task_id": "task_12345",
  "report_type": "resource_analysis",
  "file_path": "html_reports/resource/task_12345_resource_report.html",
  "generated_at": "2026-01-23T10:00:00Z"
}
```

#### 批量扫描和向量化

```bash
POST /api/v1/ai/scan-and-vectorize-reports
Authorization: Bearer <token>
```

#### 查看向量化状态

```bash
GET /api/v1/ai/vectorization-status
Authorization: Bearer <token>
```

响应示例：

```json
{
  "total_reports": 150,
  "vectorized_reports": 120,
  "pending_reports": 30,
  "vectorization_rate": "80.0%",
  "by_type": [
    {
      "report_type": "resource_analysis",
      "total": 50,
      "vectorized": 45,
      "pending": 5
    },
    {
      "report_type": "bcc_monitoring",
      "total": 40,
      "vectorized": 35,
      "pending": 5
    }
  ]
}
```

## 支持的报告类型

| 报告类型 | MinIO 路径 | 摘要层内容 | 结论层内容 |
|---------|-----------|-----------|-----------|
| 资源分析 | `html_reports/resource/` | 集群数量、健康状态统计 | 严重/警告集群列表、关键建议 |
| BCC 监控 | `html_reports/bcc/` | 实例数量、监控周期 | 异常实例列表、关键指标异常 |
| BOS 监控 | `html_reports/bos/` | Bucket 数量、存储统计 | 异常 Bucket 列表、容量告警 |
| 运营分析 | `html_reports/operational/` | 数据时间范围、总问题数 | Top 10 问题列表、趋势分析 |

## 数据库表结构

### report_index 表

存储报告索引和向量化状态：

```sql
CREATE TABLE report_index (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    task_id VARCHAR(100) NOT NULL UNIQUE,
    report_type ENUM('resource_analysis', 'bcc_monitoring', 'bos_monitoring', 'operational_analysis'),
    file_path VARCHAR(500) NOT NULL,
    file_format ENUM('html', 'json', 'excel'),
    summary TEXT,
    conclusion TEXT,
    generated_at TIMESTAMP NOT NULL,
    indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    vectorized BOOLEAN DEFAULT FALSE,
    vector_id VARCHAR(100)
);
```

### knowledge_entries 表

存储自动生成的知识条目：

```sql
CREATE TABLE knowledge_entries (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    metadata JSON,
    category VARCHAR(100),
    tags JSON,
    source ENUM('manual', 'auto') DEFAULT 'manual',
    source_type VARCHAR(50),
    source_id VARCHAR(100),
    author VARCHAR(100) NOT NULL,
    auto_generated BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

## 配置选项

在 `.env` 文件中配置：

```bash
# 向量数据库配置
VECTOR_DB_TYPE=faiss
VECTOR_DB_PATH=/app/vector_store
VECTOR_DIMENSION=768

# Embedding 模型配置
EMBEDDING_MODEL=bge-small-zh
EMBEDDING_API_URL=https://your-embedding-api.com/v1/embeddings
EMBEDDING_API_KEY=your-api-key

# MinIO 配置
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=cluster-files
```

## 监控和日志

### 日志记录

所有向量化操作都会记录日志：

- **成功**：`✅ 报告向量化完成: task_12345, 知识条目ID: 123`
- **失败**：`❌ 报告向量化失败: task_12345, 错误: {error_message}`
- **扫描**：`📊 向量化统计: {'scanned': 10, 'success': 8, 'failed': 2, 'skipped': 0}`

### 审计日志

向量化失败会记录到 `ai_audit_logs` 表：

```sql
INSERT INTO ai_audit_logs (
    user_id, username, action_type, execution_status, error_message, knowledge_operation
) VALUES (
    'system', 'system', 'knowledge_create', 'error', 
    'Failed to download report from MinIO',
    '{"operation": "auto_vectorization", "task_id": "task_12345", "report_type": "resource_analysis"}'
);
```

## 性能优化

### 1. 批量处理

后台任务会批量处理多个报告，减少数据库连接开销。

### 2. 缓存机制

- **向量缓存**：Embedding 模型使用 Redis 缓存向量结果
- **报告缓存**：从 MinIO 下载的报告内容缓存 24 小时

### 3. 增量更新

只向量化新报告，已向量化的报告会被跳过。

## 故障排查

### 问题 1：向量化任务未启动

**症状**：后台任务日志中没有扫描记录

**解决方案**：
1. 检查 `main.py` 中是否启动了后台任务
2. 查看应用启动日志是否有错误
3. 确认 AI 服务初始化成功

### 问题 2：MinIO 下载失败

**症状**：日志显示 "无法从 MinIO 下载报告"

**解决方案**：
1. 检查 MinIO 连接配置
2. 确认报告文件路径正确
3. 验证 MinIO 访问权限

### 问题 3：向量存储失败

**症状**：日志显示 "向量存储失败"

**解决方案**：
1. 检查向量数据库目录权限
2. 确认 FAISS 索引文件未损坏
3. 查看磁盘空间是否充足

### 问题 4：知识条目创建失败

**症状**：向量化成功但知识条目创建失败

**解决方案**：
1. 检查 MySQL 连接
2. 确认 `knowledge_entries` 表存在
3. 查看数据库错误日志

## 最佳实践

### 1. 定期备份

定期备份向量数据库和知识库：

```bash
# 备份向量数据库
tar -czf vector_store_backup_$(date +%Y%m%d).tar.gz /app/vector_store

# 备份知识库
mysqldump -u root -p cmdb knowledge_entries > knowledge_entries_backup_$(date +%Y%m%d).sql
```

### 2. 监控向量化率

定期检查向量化状态，确保大部分报告已向量化：

```bash
curl -X GET "http://localhost:8000/api/v1/ai/vectorization-status" \
  -H "Authorization: Bearer <token>"
```

### 3. 清理失败记录

定期清理向量化失败的审计日志：

```sql
DELETE FROM ai_audit_logs
WHERE action_type = 'knowledge_create'
  AND execution_status = 'error'
  AND created_at < DATE_SUB(NOW(), INTERVAL 30 DAY);
```

## 未来改进

1. **实时事件监听**：使用 MinIO 事件通知替代定时扫描
2. **增量向量化**：支持报告内容更新时重新向量化
3. **多语言支持**：支持英文报告的向量化
4. **智能摘要**：使用 LLM 自动生成更准确的摘要和结论
5. **向量索引优化**：使用 FAISS IVF 索引提升检索性能

## 相关文档

- [AI 智能查询功能设计文档](../../.kiro/specs/ai-intelligent-query/design.md)
- [向量数据库管理](./vector_store.md)
- [知识库管理](./knowledge_management.md)
