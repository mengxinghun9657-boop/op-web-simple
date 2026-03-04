# 分类与标签管理功能实现文档

## 概述

本文档描述了任务 23 的实现：知识库分类与标签管理功能。

## 功能列表

### 1. 分类管理

#### 1.1 获取分类列表

**接口**: `GET /api/v1/ai/knowledge/categories`

**权限**: 所有认证用户

**功能**:
- 返回所有知识分类列表
- 按 `display_order` 和 `name` 排序
- 包含分类的完整信息（ID、名称、描述、显示顺序、创建时间、创建者）

**响应示例**:
```json
{
  "categories": [
    {
      "id": 1,
      "name": "故障处理",
      "description": "系统故障排查和处理方案",
      "display_order": 1,
      "created_at": "2026-01-23T10:00:00",
      "created_by": "system"
    },
    {
      "id": 2,
      "name": "操作规范",
      "description": "日常运维操作规范和流程",
      "display_order": 2,
      "created_by": "system"
    }
  ],
  "total": 6
}
```

**验证需求**: Requirements 21.1

#### 1.2 创建新分类

**接口**: `POST /api/v1/ai/knowledge/categories`

**权限**: 仅超级管理员（SUPER_ADMIN）

**请求体**:
```json
{
  "name": "新分类名称",
  "description": "分类描述（可选）",
  "display_order": 10
}
```

**功能**:
- 创建新的知识分类
- 验证分类名称唯一性
- 记录创建者信息
- 非超级管理员访问返回 403 错误

**响应示例**:
```json
{
  "id": 7,
  "name": "新分类名称",
  "description": "分类描述",
  "display_order": 10,
  "created_at": "2026-01-23T15:30:00",
  "created_by": "admin"
}
```

**验证需求**: Requirements 21.2, 21.8

### 2. 标签管理

#### 2.1 获取标签列表

**接口**: `GET /api/v1/ai/knowledge/tags`

**权限**: 所有认证用户

**查询参数**:
- `min_usage`: 最小使用次数过滤（默认 0）
- `limit`: 返回数量限制（默认 100）

**功能**:
- 返回所有知识标签列表
- 按使用次数降序排序
- 支持按最小使用次数过滤
- 包含标签的完整信息（ID、名称、使用次数、创建时间）

**响应示例**:
```json
{
  "tags": [
    {
      "id": 1,
      "name": "MySQL",
      "usage_count": 15,
      "created_at": "2026-01-20T10:00:00"
    },
    {
      "id": 2,
      "name": "性能优化",
      "usage_count": 12,
      "created_at": "2026-01-20T10:05:00"
    },
    {
      "id": 3,
      "name": "故障排查",
      "usage_count": 8,
      "created_at": "2026-01-20T10:10:00"
    }
  ],
  "total": 3
}
```

**验证需求**: Requirements 21.3

#### 2.2 自动创建标签

**功能**: 当用户创建知识条目时使用新标签，系统自动创建该标签

**实现位置**: `KnowledgeManager.create_entry()` 方法

**流程**:
1. 用户创建知识条目，指定标签列表
2. 系统调用 `_ensure_tags_exist()` 方法
3. 检查每个标签是否存在于 `knowledge_tags` 表
4. 如果标签不存在，自动插入新记录（初始 `usage_count` 为 0）
5. 继续创建知识条目

**代码示例**:
```python
async def _ensure_tags_exist(self, tags: List[str]) -> None:
    """确保标签存在，如果不存在则自动创建"""
    for tag_name in tags:
        # 检查标签是否存在
        result = self.db.execute(
            "SELECT id FROM knowledge_tags WHERE name = :tag_name",
            {"tag_name": tag_name}
        )
        
        if not result.fetchone():
            # 自动创建标签
            self.db.execute(
                "INSERT INTO knowledge_tags (name, usage_count) VALUES (:tag_name, 0)",
                {"tag_name": tag_name}
            )
            logger.info(f"✅ 自动创建标签: {tag_name}")
```

**验证需求**: Requirements 21.4

#### 2.3 标签使用次数更新

**功能**: 自动维护标签的使用次数统计

**触发场景**:

1. **创建知识条目**: 增加标签使用次数
   - 调用 `_increment_tag_usage(tags)`
   - 每个标签的 `usage_count` +1

2. **更新知识条目**: 根据标签变更更新使用次数
   - 计算移除的标签：`removed_tags = old_tags - new_tags`
   - 计算新增的标签：`added_tags = new_tags - old_tags`
   - 对移除的标签调用 `_decrement_tag_usage(removed_tags)`
   - 对新增的标签调用 `_increment_tag_usage(added_tags)`

3. **软删除知识条目**: 减少标签使用次数
   - 调用 `_decrement_tag_usage(tags)`
   - 每个标签的 `usage_count` -1（最小为 0）

4. **物理删除知识条目**: 减少标签使用次数
   - 在 `cleanup_deleted_entries()` 中调用 `_decrement_tag_usage(tags)`

**代码示例**:
```python
async def _increment_tag_usage(self, tags: List[str]) -> None:
    """增加标签使用次数"""
    for tag_name in tags:
        self.db.execute(
            "UPDATE knowledge_tags SET usage_count = usage_count + 1 WHERE name = :tag_name",
            {"tag_name": tag_name}
        )

async def _decrement_tag_usage(self, tags: List[str]) -> None:
    """减少标签使用次数（最小为 0）"""
    for tag_name in tags:
        self.db.execute(
            "UPDATE knowledge_tags SET usage_count = GREATEST(usage_count - 1, 0) WHERE name = :tag_name",
            {"tag_name": tag_name}
        )
```

**验证需求**: Requirements 21.5

## 数据库表结构

### knowledge_categories 表

```sql
CREATE TABLE IF NOT EXISTS `knowledge_categories` (
    `id` INT PRIMARY KEY AUTO_INCREMENT COMMENT '分类ID',
    `name` VARCHAR(100) NOT NULL UNIQUE COMMENT '分类名称',
    `description` VARCHAR(500) COMMENT '分类描述',
    `display_order` INT DEFAULT 0 COMMENT '显示顺序',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `created_by` VARCHAR(100) COMMENT '创建者',
    
    INDEX `idx_display_order` (`display_order`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

**预定义分类**:
1. 故障处理
2. 操作规范
3. 优化建议
4. 常见问题
5. 最佳实践
6. 分析报告

### knowledge_tags 表

```sql
CREATE TABLE IF NOT EXISTS `knowledge_tags` (
    `id` INT PRIMARY KEY AUTO_INCREMENT COMMENT '标签ID',
    `name` VARCHAR(50) NOT NULL UNIQUE COMMENT '标签名称',
    `usage_count` INT DEFAULT 0 COMMENT '使用次数',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    
    INDEX `idx_usage_count` (`usage_count`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

## 权限控制

### 分类管理权限

| 操作 | 权限要求 | 说明 |
|------|---------|------|
| 获取分类列表 | 所有认证用户 | 任何登录用户都可以查看分类 |
| 创建新分类 | 超级管理员（SUPER_ADMIN） | 仅超级管理员可以创建分类 |

### 标签管理权限

| 操作 | 权限要求 | 说明 |
|------|---------|------|
| 获取标签列表 | 所有认证用户 | 任何登录用户都可以查看标签 |
| 自动创建标签 | 系统自动 | 创建知识条目时自动创建 |
| 更新使用次数 | 系统自动 | 创建/更新/删除条目时自动更新 |

## 实现文件

### 1. API 接口

**文件**: `backend/app/api/v1/ai_intelligent_query.py`

**新增接口**:
- `GET /api/v1/ai/knowledge/categories` - 获取分类列表
- `POST /api/v1/ai/knowledge/categories` - 创建新分类
- `GET /api/v1/ai/knowledge/tags` - 获取标签列表

### 2. 知识库管理器

**文件**: `backend/app/services/ai/knowledge_manager.py`

**新增方法**:
- `_ensure_tags_exist(tags)` - 确保标签存在，自动创建不存在的标签
- `_increment_tag_usage(tags)` - 增加标签使用次数
- `_decrement_tag_usage(tags)` - 减少标签使用次数

**修改方法**:
- `create_entry()` - 添加自动创建标签和更新使用次数
- `update_entry()` - 添加标签变更处理和使用次数更新
- `soft_delete_entry()` - 添加减少标签使用次数
- `cleanup_deleted_entries()` - 添加减少标签使用次数

### 3. 数据库初始化

**文件**: `backend/config/mysql-init-ai-query.sql`

**已包含**:
- `knowledge_categories` 表定义
- `knowledge_tags` 表定义
- 预定义分类数据插入

## 测试

### 测试文件

**文件**: `backend/test_category_tag_management.py`

**测试内容**:
1. 获取分类列表
2. 创建新分类（超级管理员）
3. 获取标签列表
4. 获取标签列表（带过滤）
5. 自动创建标签（概念演示）

### 运行测试

```bash
# 确保后端服务正在运行
cd backend
python test_category_tag_management.py
```

**注意事项**:
- 需要有效的超级管理员认证令牌
- 需要数据库已初始化
- 某些测试需要知识库管理接口已实现

## 使用示例

### 示例 1: 获取所有分类

```bash
curl -X GET "http://localhost:8000/api/v1/ai/knowledge/categories" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 示例 2: 创建新分类（超级管理员）

```bash
curl -X POST "http://localhost:8000/api/v1/ai/knowledge/categories" \
  -H "Authorization: Bearer SUPER_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "安全加固",
    "description": "系统安全加固方案和最佳实践",
    "display_order": 7
  }'
```

### 示例 3: 获取活跃标签（使用次数 >= 1）

```bash
curl -X GET "http://localhost:8000/api/v1/ai/knowledge/tags?min_usage=1&limit=20" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 示例 4: 创建知识条目（自动创建标签）

```bash
curl -X POST "http://localhost:8000/api/v1/knowledge/entries" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "MySQL 主从同步延迟处理",
    "content": "当发现 MySQL 主从同步延迟超过 10 秒时...",
    "category": "故障处理",
    "tags": ["MySQL", "主从同步", "性能优化"]
  }'
```

**说明**: 如果 "MySQL"、"主从同步"、"性能优化" 这些标签不存在，系统会自动创建它们。

## 错误处理

### 常见错误

1. **403 Forbidden** - 非超级管理员尝试创建分类
   ```json
   {
     "detail": "仅超级管理员可以创建知识分类"
   }
   ```

2. **400 Bad Request** - 分类名称已存在
   ```json
   {
     "detail": "分类名称已存在: 故障处理"
   }
   ```

3. **500 Internal Server Error** - 数据库操作失败
   ```json
   {
     "detail": "创建分类失败: [错误详情]"
   }
   ```

## 性能考虑

### 标签使用次数更新

- 使用数据库原子操作（`usage_count = usage_count + 1`）
- 避免并发问题
- 使用索引优化查询（`idx_usage_count`）

### 分类列表查询

- 使用索引优化排序（`idx_display_order`）
- 预定义分类数量有限，查询性能良好

### 标签列表查询

- 支持分页（`limit` 参数）
- 支持过滤（`min_usage` 参数）
- 按使用次数降序排序，常用标签优先显示

## 未来扩展

### 可选功能（Requirements 21.6, 21.7）

1. **自动清理未使用的标签**
   - 定时任务检查 `usage_count = 0` 的标签
   - 可选地删除长期未使用的标签
   - 保留最近创建的标签（如 30 天内）

2. **标签合并功能**
   - 超级管理员可以合并相似标签
   - 自动更新所有使用该标签的知识条目
   - 更新使用次数统计

3. **分类层级结构**
   - 支持父子分类关系
   - 树形结构展示
   - 继承权限控制

## 总结

本实现完成了任务 23 的所有核心功能：

✅ 实现分类列表接口 `GET /api/v1/knowledge/categories`
✅ 实现创建分类接口 `POST /api/v1/knowledge/categories`（仅超级管理员）
✅ 实现标签列表接口 `GET /api/v1/knowledge/tags`
✅ 实现自动创建标签逻辑
✅ 实现标签使用次数更新

**验证需求**: Requirements 21.1, 21.2, 21.3, 21.4, 21.5, 21.7, 21.8

