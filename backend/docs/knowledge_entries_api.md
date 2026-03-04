# 知识库管理 API 接口文档

## 概述

知识库管理 API 提供了完整的知识条目 CRUD 操作接口，支持创建、查询、更新、删除、搜索和批量导入功能。所有接口都需要超级管理员权限和知识库管理会话令牌验证。

**基础路径**: `/api/v1/knowledge`

**认证要求**:
1. 用户必须是超级管理员（SUPER_ADMIN）
2. 必须通过知识库管理密码验证（获取会话令牌）
3. 请求头必须包含：
   - `Authorization: Bearer <access_token>` - 用户访问令牌
   - `X-Knowledge-Token: <knowledge_token>` - 知识库管理会话令牌

## API 接口列表

### 1. 创建知识条目

**接口**: `POST /api/v1/knowledge/entries`

**描述**: 创建新的知识条目，自动向量化并存储到向量数据库。

**请求体**:
```json
{
  "title": "MySQL 主从同步延迟处理方案",
  "content": "当发现 MySQL 主从同步延迟超过 10 秒时，按以下步骤排查：\n1. 检查网络连接\n2. 查看 binlog 大小\n3. 优化慢查询",
  "category": "故障处理",
  "tags": ["MySQL", "主从同步", "性能优化"],
  "priority": "high",
  "metadata": {
    "detail_level": "summary_and_conclusion",
    "additional_info": "..."
  }
}
```

**字段说明**:
- `title` (必填): 标题，1-500 字符
- `content` (必填): 内容，1-10000 字符
- `category` (可选): 分类，最多 100 字符
- `tags` (可选): 标签列表
- `priority` (可选): 优先级，可选值：low/medium/high，默认 medium
- `metadata` (可选): 元数据（详情层数据），JSON 对象

**响应**:
```json
{
  "id": 1,
  "title": "MySQL 主从同步延迟处理方案",
  "content": "当发现 MySQL 主从同步延迟超过 10 秒时...",
  "metadata": {...},
  "category": "故障处理",
  "tags": ["MySQL", "主从同步", "性能优化"],
  "priority": "high",
  "source": "manual",
  "source_type": null,
  "source_id": null,
  "author": "admin",
  "updated_by": null,
  "auto_generated": false,
  "manually_edited": false,
  "created_at": "2026-01-23T10:00:00Z",
  "updated_at": "2026-01-23T10:00:00Z",
  "similarity": null
}
```

**Requirements**: 17.1, 17.7, 17.8, 17.9, 17.10, 17.11

---

### 2. 列出知识条目

**接口**: `GET /api/v1/knowledge/entries`

**描述**: 列出知识条目（分页），支持过滤和排序。

**查询参数**:
- `page` (可选): 页码，默认 1
- `page_size` (可选): 每页数量，默认 20
- `category` (可选): 分类过滤
- `tags` (可选): 标签过滤，逗号分隔，如 "MySQL,主从同步"
- `author` (可选): 作者过滤
- `source` (可选): 来源过滤，可选值：manual/auto
- `order_by` (可选): 排序字段，可选值：created_at/updated_at/priority，默认 created_at
- `order_direction` (可选): 排序方向，可选值：ASC/DESC，默认 DESC

**示例请求**:
```
GET /api/v1/knowledge/entries?page=1&page_size=10&category=故障处理&order_by=created_at&order_direction=DESC
```

**响应**:
```json
{
  "entries": [
    {
      "id": 1,
      "title": "MySQL 主从同步延迟处理方案",
      "content": "当发现 MySQL 主从同步延迟超过 10 秒时...",
      "category": "故障处理",
      "tags": ["MySQL", "主从同步"],
      "priority": "high",
      "source": "manual",
      "author": "admin",
      "created_at": "2026-01-23T10:00:00Z",
      "updated_at": "2026-01-23T10:00:00Z"
    }
  ],
  "total": 100,
  "page": 1,
  "page_size": 10,
  "total_pages": 10
}
```

**Requirements**: 18.1, 18.2, 18.3, 18.4

---

### 3. 获取知识条目详情

**接口**: `GET /api/v1/knowledge/entries/{id}`

**描述**: 根据 ID 获取知识条目的完整信息。

**路径参数**:
- `id`: 知识条目 ID

**示例请求**:
```
GET /api/v1/knowledge/entries/1
```

**响应**: 同创建接口的响应格式

**错误响应**:
- `404 Not Found`: 条目不存在或已删除

**Requirements**: 18.5

---

### 4. 更新知识条目

**接口**: `PUT /api/v1/knowledge/entries/{id}`

**描述**: 更新知识条目，支持部分更新（PATCH）。如果内容被更新，会自动重新生成向量。

**路径参数**:
- `id`: 知识条目 ID

**请求体** (所有字段都是可选的):
```json
{
  "title": "【已更新】MySQL 主从同步延迟处理方案",
  "content": "【已更新】当发现 MySQL 主从同步延迟超过 10 秒时...",
  "category": "故障处理",
  "tags": ["MySQL", "主从同步", "性能优化", "故障排查"],
  "priority": "medium",
  "metadata": {...}
}
```

**响应**: 同创建接口的响应格式

**自动处理**:
- 如果内容被更新，自动重新生成向量
- 如果是自动生成的条目，标记 `manually_edited` 为 true
- 自动更新标签使用次数
- 记录审计日志

**Requirements**: 19.1, 19.2, 19.3, 19.4, 19.5, 19.6, 19.8, 19.9, 19.10

---

### 5. 删除知识条目

**接口**: `DELETE /api/v1/knowledge/entries/{id}`

**描述**: 软删除知识条目。条目不会立即物理删除，而是标记为已删除，定时任务会清理软删除超过 30 天的条目。

**路径参数**:
- `id`: 知识条目 ID

**示例请求**:
```
DELETE /api/v1/knowledge/entries/1
```

**响应**:
```json
{
  "success": true,
  "message": "知识条目已删除: entry_id=1",
  "entry_id": 1
}
```

**软删除机制**:
- MySQL 中标记 `deleted_at` 字段
- 向量存储中标记 `is_deleted=true`
- 后续的向量检索不会返回该条目
- 定时任务会物理清理软删除超过 30 天的条目

**Requirements**: 20.1, 20.2, 20.3, 20.4, 20.5, 20.8

---

### 6. 搜索知识条目

**接口**: `GET /api/v1/knowledge/search`

**描述**: 使用向量检索搜索知识条目，按相似度降序排序。

**查询参数**:
- `query` (必填): 查询文本
- `top_k` (可选): 返回结果数量，默认 3，最大 10
- `similarity_threshold` (可选): 相似度阈值，默认 0.6，范围 0-1
- `category` (可选): 分类过滤

**示例请求**:
```
GET /api/v1/knowledge/search?query=MySQL主从同步&top_k=3&similarity_threshold=0.6
```

**响应**:
```json
{
  "results": [
    {
      "id": 1,
      "title": "MySQL 主从同步延迟处理方案",
      "content": "当发现 MySQL 主从同步延迟超过 10 秒时...",
      "category": "故障处理",
      "tags": ["MySQL", "主从同步"],
      "similarity": 0.8523,
      "...": "..."
    }
  ],
  "query": "MySQL主从同步",
  "total": 1
}
```

**搜索方式**:
- 使用向量化模型将查询文本转换为向量
- 在向量数据库中检索最相关的条目
- 按相似度降序排序
- 自动过滤已删除的条目

**Requirements**: 18.7, 22.1, 22.2, 22.3, 22.4

---

### 7. 批量导入知识条目

**接口**: `POST /api/v1/knowledge/import`

**描述**: 批量导入知识条目，支持 JSON 和 CSV 格式。

**请求**:
- Content-Type: `multipart/form-data`
- 文件字段名: `file`
- 支持的文件格式: `.json`, `.csv`

**JSON 格式示例**:
```json
[
  {
    "title": "MySQL 主从同步延迟处理方案",
    "content": "当发现 MySQL 主从同步延迟超过 10 秒时...",
    "category": "故障处理",
    "tags": ["MySQL", "主从同步"],
    "priority": "high"
  },
  {
    "title": "Redis 内存溢出处理方案",
    "content": "当 Redis 内存使用超过 80% 时...",
    "category": "故障处理",
    "tags": ["Redis", "内存管理"],
    "priority": "high"
  }
]
```

**CSV 格式示例**:
```csv
title,content,category,tags,priority
"MySQL 主从同步延迟处理方案","当发现 MySQL 主从同步延迟超过 10 秒时...","故障处理","MySQL,主从同步","high"
"Redis 内存溢出处理方案","当 Redis 内存使用超过 80% 时...","故障处理","Redis,内存管理","high"
```

**响应**:
```json
{
  "success": true,
  "message": "导入完成: 成功 2 条，失败 0 条",
  "imported_count": 2,
  "failed_count": 0,
  "errors": []
}
```

**限制**:
- 单次导入最多 1000 条
- 单个条目导入失败不影响其他条目
- 失败的条目会在 `errors` 数组中返回详情

**Requirements**: 23.1, 23.2, 23.3, 23.4, 23.5, 23.6, 23.7, 23.8, 23.9

---

## 错误响应格式

所有接口的错误响应遵循统一格式：

```json
{
  "detail": "错误消息"
}
```

**常见错误代码**:
- `400 Bad Request`: 请求参数验证失败
- `401 Unauthorized`: 未认证或令牌无效
- `403 Forbidden`: 权限不足（非超级管理员或会话令牌无效）
- `404 Not Found`: 资源不存在
- `500 Internal Server Error`: 服务器内部错误

---

## 认证流程

### 1. 登录获取访问令牌

```bash
curl -X POST http://localhost:8000/api/v1/login \
  -d "username=admin&password=admin123"
```

响应:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### 2. 验证知识库管理密码

```bash
curl -X POST http://localhost:8000/api/v1/knowledge/auth/verify \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"password": "admin123"}'
```

响应:
```json
{
  "success": true,
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "message": "密码验证成功",
  "expires_in": 1800
}
```

### 3. 使用知识库管理接口

```bash
curl -X POST http://localhost:8000/api/v1/knowledge/entries \
  -H "Authorization: Bearer <access_token>" \
  -H "X-Knowledge-Token: <knowledge_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "测试知识条目",
    "content": "这是测试内容",
    "category": "测试分类",
    "tags": ["测试"],
    "priority": "medium"
  }'
```

---

## 使用示例

### Python 示例

```python
import requests

BASE_URL = "http://localhost:8000/api/v1"

# 1. 登录
response = requests.post(f"{BASE_URL}/login", data={
    "username": "admin",
    "password": "admin123"
})
access_token = response.json()["access_token"]

# 2. 验证知识库管理密码
response = requests.post(
    f"{BASE_URL}/knowledge/auth/verify",
    headers={"Authorization": f"Bearer {access_token}"},
    json={"password": "admin123"}
)
knowledge_token = response.json()["token"]

# 3. 创建知识条目
response = requests.post(
    f"{BASE_URL}/knowledge/entries",
    headers={
        "Authorization": f"Bearer {access_token}",
        "X-Knowledge-Token": knowledge_token
    },
    json={
        "title": "MySQL 主从同步延迟处理方案",
        "content": "当发现 MySQL 主从同步延迟超过 10 秒时...",
        "category": "故障处理",
        "tags": ["MySQL", "主从同步"],
        "priority": "high"
    }
)
entry = response.json()
print(f"创建成功: entry_id={entry['id']}")

# 4. 搜索知识条目
response = requests.get(
    f"{BASE_URL}/knowledge/search",
    headers={
        "Authorization": f"Bearer {access_token}",
        "X-Knowledge-Token": knowledge_token
    },
    params={
        "query": "MySQL主从同步",
        "top_k": 3
    }
)
results = response.json()
print(f"搜索结果: {len(results['results'])} 条")
```

---

## 注意事项

1. **会话令牌有效期**: 知识库管理会话令牌有效期为 30 分钟，过期后需要重新验证密码。

2. **并发限制**: 系统支持低并发场景（2 个并发请求），高并发场景需要扩展。

3. **内容长度限制**: 知识条目内容最多 10000 字符，超过限制会返回 400 错误。

4. **批量导入限制**: 单次导入最多 1000 条，建议分批导入大量数据。

5. **软删除机制**: 删除的条目不会立即物理删除，定时任务会清理软删除超过 30 天的条目。

6. **向量化**: 创建和更新条目时会自动向量化内容，可能需要几秒钟时间。

7. **审计日志**: 所有操作都会记录到审计日志，包含用户ID、操作类型、时间戳等信息。

---

## 相关文档

- [知识库管理认证文档](./knowledge_auth.md)
- [知识库管理器服务文档](../app/services/ai/knowledge_manager.py)
- [向量存储管理文档](./vector_backup_restore.md)
- [分类与标签管理文档](./category_tag_management.md)

---

## 更新日志

- **2026-01-23**: 初始版本，实现所有 CRUD 接口和批量导入功能
