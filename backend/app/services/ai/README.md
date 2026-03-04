# AI 智能查询服务模块

## 概述

本模块实现了 AI 智能查询功能的核心组件，包括向量数据库管理、知识库检索等功能。

## 组件

### VectorStore - 向量数据库管理器

向量数据库管理器基于 FAISS 实现，提供向量的存储、检索、更新和删除功能。

#### 特性

- **向量存储**: 支持单个和批量添加向量
- **语义检索**: 基于余弦相似度的向量检索
- **元数据管理**: 为每个向量关联元数据（标题、分类、标签等）
- **软删除**: 支持软删除机制，不物理删除向量
- **持久化**: 自动保存到文件，支持容器重启后恢复
- **健康检查**: 提供健康状态查询接口

#### 文件结构

```
/app/vector_store/
├── faiss_index.bin          # FAISS 索引文件
├── id_map.json              # ID 映射（vector_id -> entry_id）
└── metadata.json            # 元数据
```

#### 使用示例

```python
from app.services.ai.vector_store import get_vector_store
import numpy as np

# 获取向量存储实例（单例模式）
vector_store = get_vector_store()

# 添加向量
embedding = np.random.randn(768).astype('float32')
vector_store.add(
    entry_id=1,
    embedding=embedding,
    metadata={
        "title": "MySQL 主从同步延迟处理方案",
        "category": "故障处理",
        "tags": ["MySQL", "主从同步"],
        "source": "manual",
        "is_deleted": False
    }
)

# 检索向量
query_embedding = np.random.randn(768).astype('float32')
results = vector_store.search(
    query_embedding=query_embedding,
    top_k=5,
    filter_func=lambda m: not m.get("is_deleted", False)
)

for result in results:
    print(f"Entry ID: {result['entry_id']}")
    print(f"Similarity: {result['similarity']:.4f}")
    print(f"Title: {result['metadata']['title']}")

# 更新元数据
vector_store.update_metadata(1, {"priority": "high"})

# 软删除
vector_store.mark_deleted(1)

# 健康检查
health = vector_store.health_check()
print(health)
```

#### API 参考

##### `add(entry_id, embedding, metadata) -> bool`

添加向量到索引。

**参数**:
- `entry_id` (int): 条目ID
- `embedding` (np.ndarray): 向量表示（768维）
- `metadata` (dict): 元数据

**返回**: bool - 是否添加成功

##### `add_batch(entries) -> int`

批量添加向量。

**参数**:
- `entries` (List[Dict]): 条目列表，每个条目包含 entry_id, embedding, metadata

**返回**: int - 成功添加的数量

##### `search(query_embedding, top_k=5, filter_func=None) -> List[Dict]`

向量检索。

**参数**:
- `query_embedding` (np.ndarray): 查询向量
- `top_k` (int): 返回结果数量
- `filter_func` (callable): 过滤函数，接收 metadata 返回 bool

**返回**: List[Dict] - 检索结果列表

##### `update_metadata(entry_id, metadata) -> bool`

更新条目的元数据。

**参数**:
- `entry_id` (int): 条目ID
- `metadata` (dict): 新的元数据

**返回**: bool - 是否更新成功

##### `mark_deleted(entry_id) -> bool`

标记条目为已删除（软删除）。

**参数**:
- `entry_id` (int): 条目ID

**返回**: bool - 是否标记成功

##### `health_check() -> Dict`

健康检查。

**返回**: Dict - 健康状态信息

#### 配置

在 `.env` 文件中配置：

```bash
# 向量数据库配置
VECTOR_DB_TYPE=faiss  # 或 chroma
VECTOR_DB_PATH=/app/vector_store
VECTOR_DIMENSION=768  # bge-small-zh 的向量维度

# Embedding 模型配置
EMBEDDING_MODEL=bge-small-zh
EMBEDDING_API_URL=  # 如果使用 API
EMBEDDING_API_KEY=  # 如果使用 API
```

#### Docker 部署

在 `docker-compose.yml` 中已配置持久化卷：

```yaml
services:
  backend:
    volumes:
      - backend_vector_store:/app/vector_store
    environment:
      VECTOR_DB_TYPE: faiss
      VECTOR_DB_PATH: /app/vector_store

volumes:
  backend_vector_store:
```

#### 健康检查端点

```bash
# 检查向量数据库健康状态
curl http://localhost:8000/api/v1/health/vector-store
```

响应示例：

```json
{
  "status": "healthy",
  "index_type": "IndexFlatIP",
  "dimension": 768,
  "total_vectors": 150,
  "total_entries": 150,
  "id_mappings": 150,
  "index_file_exists": true,
  "id_map_file_exists": true,
  "metadata_file_exists": true
}
```

## 测试

### 单元测试

```bash
# 在 Docker 容器中运行测试
docker exec -it cluster-backend python test_vector_store.py
```

### 集成测试

测试将在后续任务中实现，包括：
- 向量添加和检索的端到端测试
- 软删除一致性测试
- 批量操作性能测试

## 注意事项

1. **向量维度**: 确保所有向量的维度一致（默认 768）
2. **归一化**: 向量会自动归一化以支持余弦相似度计算
3. **软删除**: FAISS 不支持直接删除向量，使用软删除机制
4. **定期重建**: 建议定期重建索引以清理已删除的向量
5. **备份**: 定期备份 `/app/vector_store` 目录

## 未来扩展

- [ ] 支持 Chroma 向量数据库
- [ ] 实现向量索引的定期重建任务
- [ ] 支持分布式向量数据库（Milvus/Weaviate）
- [ ] 实现向量数据库的备份和恢复接口
- [ ] 添加向量检索的性能监控
