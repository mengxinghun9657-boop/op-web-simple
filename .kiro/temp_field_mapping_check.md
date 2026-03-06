# PFS 模块前后端字段映射检查表

## API 1: GET /api/v1/pfs/metrics (指标目录)

### 后端返回 (pfs_service.py:get_metrics_catalog)
```python
{
  "容量": [
    {
      "name": "FsUsage",              # ✅ 正确
      "zh_name": "文件系统已用容量",
      "description": "...",
      "unit": "bytes",
      "unit_zh": "字节",
      "category": "容量",
      "level": "cluster",
      "warn_threshold": 0.80,
      "critical_threshold": 0.95,
      "promql_template": "...",
      "normal_range": "..."
    }
  ]
}
```

### 前端使用 (QueryPanel.vue)
```javascript
// ✅ 正确使用
metric.name
metric.zh_name
metric.description
```

**状态**: ✅ 字段映射正确

---

## API 2: POST /api/v1/pfs/query (查询指标数据)

### 后端返回 (PFSMetricResult)
```python
{
  "metric_name": "FsUsage",           # 注意：这里是 metric_name
  "zh_name": "文件系统已用容量",
  "desc": "...",
  "unit": "bytes",
  "unit_zh": "字节",
  "level": "cluster",
  "category": "容量",
  "data_points": [
    {
      "timestamp": 1704067200,        # Unix时间戳（秒）
      "value": 1000000000.0,
      "client_id": null,
      "client_ip": null,
      "labels": {}
    }
  ],
  "statistics": {                     # 注意：这里是 statistics
    "count": 100,
    "avg": 1000000000.0,
    "min": 900000000.0,
    "max": 1100000000.0,
    "p95": 1080000000.0,
    "status": "normal"
  },
  "query_params": {}
}
```

### 前端使用

#### PFSMonitoring.vue
```javascript
// ✅ 已修复
:key="metric.metric_name"
```

#### MetricCard.vue
```javascript
// ✅ 已修复
metric.zh_name
metric.desc
metric.unit
metric.unit_zh
metric.data_points
metric.statistics.avg
metric.statistics.max
metric.statistics.p95
```

#### DataDashboard.vue
```javascript
// ✅ 已修复
metricResult.metric_name
metricResult.zh_name
metricResult.unit
metricResult.unit_zh
metricResult.data_points
point.timestamp
point.value
point.client_id
point.client_ip
point.labels
```

**状态**: ✅ 已全部修复

---

## API 3: POST /api/v1/pfs/compare (对比查询)

### 后端返回 (pfs_service.py:compare_metrics)
```python
{
  "summary": {
    "total_metrics": 2,
    "stable_count": 1,
    "warning_count": 1,
    "critical_count": 0
  },
  "metrics": [
    {
      "metric_name": "FsUsage",
      "zh_name": "文件系统已用容量",
      "unit_zh": "字节",
      "today": {
        "avg": 1100000000.0,
        "max": 1200000000.0,
        "status": "normal"
      },
      "yesterday": {
        "avg": 1000000000.0,
        "max": 1100000000.0,
        "status": "normal"
      },
      "change": {
        "percent": 10.0,
        "status": "stable",
        "direction": "up"
      }
    }
  ]
}
```

### 前端使用
**状态**: ⚠️ 未实现对比模式前端展示（TODO）

---

## API 4: POST /api/v1/pfs/export (导出任务)

### 后端返回
```python
{
  "success": true,
  "data": {
    "task_id": "pfs_export_xxx",
    "status": "pending",
    "message": "导出任务已创建"
  },
  "message": "导出任务已创建"
}
```

### 前端使用 (PFSMonitoring.vue)
```javascript
// ✅ 正确
const { task_id } = response.data
```

**状态**: ✅ 字段映射正确

---

## API 5: GET /api/v1/pfs/task/{task_id} (任务状态)

### 后端返回
```python
{
  "success": true,
  "data": {
    "task_id": "pfs_export_xxx",
    "status": "completed",
    "message": "导出完成",
    "progress": 100,
    "result_url": "http://...",
    "created_at": "2024-01-01T00:00:00",
    "completed_at": "2024-01-01T00:05:00"
  }
}
```

### 前端使用 (taskPoller.js)
```javascript
// ✅ 正确（复用现有 taskPoller）
taskData.status
taskData.progress
taskData.message
taskData.result_file
```

**状态**: ✅ 字段映射正确

---

## API 6: GET /api/v1/pfs/clients (客户端列表)

### 后端返回
```python
{
  "success": true,
  "data": [
    {
      "client_id": "client-001",
      "client_ip": "10.0.0.1",
      "read_throughput": 1000000.0,
      "write_throughput": 500000.0,
      "has_read": true,
      "has_write": true
    }
  ]
}
```

### 前端使用 (QueryPanel.vue)
```javascript
// ✅ 正确
client.client_id
client.client_ip
```

**状态**: ✅ 字段映射正确

---

## 检查总结

| API | 后端字段 | 前端访问 | 状态 | 问题 |
|-----|---------|---------|------|------|
| /metrics | name | metric.name | ✅ | 无 |
| /query | metric_name | metric.metric_name | ✅ | 已修复 |
| /query | statistics | metric.statistics | ✅ | 已修复 |
| /query | data_points | metric.data_points | ✅ | 无 |
| /compare | - | - | ⚠️ | 未实现前端展示 |
| /export | task_id | response.data.task_id | ✅ | 无 |
| /task/{id} | status/progress | taskData.status | ✅ | 无 |
| /clients | client_id | client.client_id | ✅ | 无 |

---

## 潜在问题

### 1. 导出功能字段不匹配 ✅ 已修复
- **位置**: `PFSMonitoring.vue` 第 248 行
- **问题**: 前端访问 `taskData.result_file`，后端返回 `result_url`
- **修复**: 改为 `taskData.result_url`
- **修复时间**: 2026-03-06

### 2. 时间戳格式不一致 ✅ 已修复
- **后端**: Unix时间戳（秒）`1704067200`
- **前端**: 需要转换为毫秒 `timestamp * 1000`
- **修复**: DataDashboard.vue 已修复

### 3. 对比模式未实现 ⚠️
- **后端**: `/compare` API 已实现
- **前端**: 未实现对比模式的数据展示
- **影响**: 用户勾选对比模式后无法看到对比结果
- **优先级**: 低（后续优化）

### 4. 字段命名不一致 ⚠️
- **指标目录**: 使用 `name`
- **查询结果**: 使用 `metric_name`
- **建议**: 统一使用 `metric_name` 或在后端做字段别名
- **优先级**: 低（架构优化）

---

## 建议

1. **立即修复**: 时间戳转换问题（已修复）
2. **后续优化**: 实现对比模式前端展示
3. **架构优化**: 统一字段命名规范（name vs metric_name）
