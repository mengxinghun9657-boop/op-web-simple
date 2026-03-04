# 定时清理任务文档

## 概述

定时清理任务用于物理删除软删除超过 30 天的知识库条目，包括：
- 从 MySQL 数据库中物理删除记录
- 从向量数据库中物理删除对应的向量

## 功能特性

### 1. 自动清理
- **执行频率**: 每周执行一次
- **清理阈值**: 软删除超过 30 天的条目
- **清理范围**: 
  - MySQL `knowledge_entries` 表中的记录
  - 向量数据库中的对应向量

### 2. 日志记录
- 记录每次清理的开始和结束时间
- 记录删除的条目数量和ID列表
- 记录删除的条目标题（前50个字符）
- 记录任何清理过程中的错误

### 3. 安全性
- 仅删除 `deleted_at` 字段不为 NULL 的记录
- 仅删除 `deleted_at` 时间超过指定天数的记录
- 事务性操作，确保数据一致性

## 实现细节

### 1. KnowledgeManager.cleanup_deleted_entries()

位置: `backend/app/services/ai/knowledge_manager.py`

```python
async def cleanup_deleted_entries(self, days_threshold: int = 30) -> Dict[str, Any]:
    """
    物理删除软删除超过指定天数的条目
    
    Args:
        days_threshold: 软删除后保留的天数（默认30天）
    
    Returns:
        Dict: 清理结果，包含 deleted_count、deleted_ids、deleted_titles
    """
```

**工作流程**:
1. 查询 `deleted_at < DATE_SUB(NOW(), INTERVAL :days DAY)` 的记录
2. 对每个条目：
   - 从向量数据库中删除向量
   - 从 MySQL 中物理删除记录
3. 提交事务
4. 返回清理结果

### 2. CleanupScheduler

位置: `backend/app/services/ai/cleanup_scheduler.py`

```python
class CleanupScheduler:
    """
    定时清理任务调度器
    
    每周执行一次，清理软删除超过 30 天的知识库条目。
    """
    
    def __init__(
        self,
        interval_days: int = 7,      # 执行间隔（天）
        days_threshold: int = 30     # 清理阈值（天）
    ):
        ...
```

**主要方法**:
- `start()`: 启动调度器
- `stop()`: 停止调度器
- `run_now()`: 立即执行一次清理（用于手动触发）

### 3. 集成到 main.py

位置: `backend/main.py`

```python
# 启动定时清理任务
cleanup_scheduler = None
try:
    from app.services.ai.cleanup_scheduler import start_cleanup_scheduler, get_cleanup_scheduler
    
    # 启动清理调度器（每周执行一次，清理软删除超过 30 天的条目）
    await start_cleanup_scheduler()
    cleanup_scheduler = get_cleanup_scheduler()
    logger.info("✅ 定时清理任务已启动（执行间隔: 7 天，清理阈值: 30 天）")
except Exception as e:
    logger.warning(f"⚠️ 定时清理任务启动失败: {e}")
```

**生命周期管理**:
- 应用启动时自动启动清理调度器
- 应用关闭时自动停止清理调度器

## 使用示例

### 1. 手动触发清理

```python
from app.services.ai.cleanup_scheduler import get_cleanup_scheduler

# 获取调度器实例
scheduler = get_cleanup_scheduler()

# 立即执行一次清理
await scheduler.run_now()
```

### 2. 自定义清理阈值

```python
from app.core.deps import SessionLocal
from app.services.ai.knowledge_manager import KnowledgeManager

db = SessionLocal()
knowledge_manager = KnowledgeManager(db)

# 清理软删除超过 60 天的条目
result = await knowledge_manager.cleanup_deleted_entries(days_threshold=60)

print(f"删除数量: {result['deleted_count']}")
print(f"删除的条目ID: {result['deleted_ids']}")
```

### 3. 查看清理日志

清理任务的日志会记录在应用日志中，格式如下：

```
2026-01-26 14:00:00 | INFO | 开始执行定时清理任务...
2026-01-26 14:00:00 | INFO | 清理条件: 软删除超过 30 天的条目
2026-01-26 14:00:01 | INFO | ✅ 从向量数据库删除: entry_id=123
2026-01-26 14:00:01 | INFO | ✅ 从 MySQL 删除: entry_id=123, title=测试条目...
2026-01-26 14:00:02 | INFO | ✅ 清理任务完成: 成功清理 5 个软删除超过 30 天的条目
2026-01-26 14:00:02 | INFO |    删除数量: 5
2026-01-26 14:00:02 | INFO |    删除的条目ID: [123, 124, 125, 126, 127]
2026-01-26 14:00:02 | INFO |    删除的条目标题: ['测试条目1', '测试条目2', ...]
2026-01-26 14:00:02 | INFO | 下次清理时间: 2026-02-02 14:00:00
```

## 配置选项

### 环境变量

可以通过环境变量配置清理任务的参数：

```bash
# .env 文件
CLEANUP_INTERVAL_DAYS=7      # 清理任务执行间隔（天）
CLEANUP_THRESHOLD_DAYS=30    # 软删除后保留的天数
```

### 代码配置

在 `main.py` 中修改调度器参数：

```python
from app.services.ai.cleanup_scheduler import CleanupScheduler

# 自定义配置
scheduler = CleanupScheduler(
    interval_days=14,    # 每两周执行一次
    days_threshold=60    # 清理软删除超过 60 天的条目
)
await scheduler.start()
```

## 监控和告警

### 1. 监控指标

建议监控以下指标：
- 清理任务执行频率
- 每次清理删除的条目数量
- 清理任务执行时间
- 清理任务失败次数

### 2. 告警规则

建议设置以下告警：
- 清理任务连续失败 3 次
- 单次清理删除条目数量超过 1000
- 清理任务执行时间超过 5 分钟

## 故障排查

### 1. 清理任务未启动

**症状**: 应用启动日志中没有 "定时清理任务已启动" 的消息

**可能原因**:
- AI 服务初始化失败
- 向量数据库初始化失败

**解决方法**:
1. 检查应用启动日志，查找错误信息
2. 确保向量数据库目录存在且可写
3. 确保数据库连接正常

### 2. 清理任务执行失败

**症状**: 日志中出现 "定时清理任务执行失败" 的错误

**可能原因**:
- 数据库连接失败
- 向量数据库操作失败
- 权限不足

**解决方法**:
1. 检查数据库连接状态
2. 检查向量数据库文件权限
3. 查看详细错误日志

### 3. 条目未被清理

**症状**: 软删除超过 30 天的条目仍然存在

**可能原因**:
- 清理任务未执行
- `deleted_at` 字段为 NULL
- 清理阈值配置错误

**解决方法**:
1. 检查清理任务是否正常运行
2. 查询数据库确认 `deleted_at` 字段值
3. 检查清理阈值配置

## 测试

### 1. 单元测试

```python
# 测试清理方法
async def test_cleanup_deleted_entries():
    db = SessionLocal()
    knowledge_manager = KnowledgeManager(db)
    
    # 创建测试条目并软删除
    entry = await knowledge_manager.create_entry(...)
    await knowledge_manager.soft_delete_entry(entry["id"], ...)
    
    # 修改 deleted_at 时间（模拟超过 30 天）
    # ...
    
    # 执行清理
    result = await knowledge_manager.cleanup_deleted_entries(days_threshold=30)
    
    # 验证条目已被删除
    assert result["deleted_count"] == 1
    assert entry["id"] in result["deleted_ids"]
```

### 2. 集成测试

参考 `backend/test_cleanup_simple.py` 文件，该文件包含完整的集成测试流程。

## 性能考虑

### 1. 批量删除

当前实现逐个删除条目，对于大量条目可能较慢。未来可以优化为批量删除：

```python
# 批量删除 MySQL 记录
DELETE FROM knowledge_entries
WHERE id IN (...)

# 批量删除向量
vector_store.delete_batch(entry_ids)
```

### 2. 执行时间

建议在业务低峰期执行清理任务，避免影响正常业务。可以通过配置执行时间来实现：

```python
# 每周日凌晨 2 点执行
scheduler = CleanupScheduler(
    interval_days=7,
    days_threshold=30,
    execution_time="02:00"  # 未来功能
)
```

## 安全性

### 1. 数据备份

在执行清理任务前，建议先备份数据库：

```bash
# 备份 MySQL
mysqldump -u user -p database > backup.sql

# 备份向量数据库
tar -czf vector_store_backup.tar.gz /app/vector_store
```

### 2. 恢复机制

如果误删除了重要数据，可以从备份中恢复：

```bash
# 恢复 MySQL
mysql -u user -p database < backup.sql

# 恢复向量数据库
tar -xzf vector_store_backup.tar.gz -C /app
```

## 未来改进

1. **可配置的执行时间**: 支持指定具体的执行时间（如每周日凌晨 2 点）
2. **批量删除优化**: 支持批量删除以提高性能
3. **删除前确认**: 添加删除前的确认机制
4. **删除历史记录**: 记录每次删除的详细信息到单独的表
5. **恢复功能**: 支持从删除历史中恢复误删除的数据
6. **监控面板**: 提供 Web 界面查看清理任务的执行历史和统计信息

## 相关文件

- `backend/app/services/ai/knowledge_manager.py` - 知识库管理器（包含清理方法）
- `backend/app/services/ai/cleanup_scheduler.py` - 清理调度器
- `backend/main.py` - 应用入口（启动清理任务）
- `backend/test_cleanup_simple.py` - 清理任务测试脚本
- `backend/docs/cleanup_task.md` - 本文档

## 参考

- Requirements 20.7: 定时清理任务需求
- Design Document: AI 智能查询功能设计文档
- Tasks.md: 任务 21.10 - 实现定时清理任务
