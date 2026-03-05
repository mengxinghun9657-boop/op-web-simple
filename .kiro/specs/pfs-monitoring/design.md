# PFS 监控模块设计文档

## 1. 概述

### 1.1 背景

PFS（Parallel File System）是百度云提供的高性能并行文件存储服务。当前项目中有一个独立的 Python 脚本 `pfswatcher.py` 用于查询 PFS 监控数据，但缺乏 Web 界面和系统集成。

**重要说明**：原脚本 `pfswatcher.py` **仅作为功能参考**，其代码结构、计算逻辑和交互方式需要根据当前项目的架构规范进行重新设计和优化。

### 1.2 目标

将 PFS 监控功能集成到集群管理平台，提供：
- **系统配置集成**：PFS 配置纳入现有系统配置模块管理
- **监控分析集成**：PFS 监控作为监控分析中心的一个子模块
- Web 界面实时展示 PFS 监控数据
- 支持数据对比分析（当前 vs 历史）
- 数据大屏展示效果
- 数据导出功能

### 1.3 模块归属

| 功能模块 | 归属位置 | 说明 |
|---------|----------|------|
| **PFS 配置管理** | 系统配置模块 (`/system-config`) | 新增 `pfs` 模块类型，与 `monitoring`、`cmdb` 同级 |
| **PFS 监控界面** | 监控分析中心 (`/monitoring/pfs`) | 与 BCC、BOS、EIP 监控并列 |
| **PFS 数据查询** | 后端 API (`/api/v1/pfs/*`) | 独立路由，复用现有 Prometheus 客户端模式 |

### 1.4 参考脚本说明

原脚本 `pfswatcher.py` 功能概览：
- 通过 Prometheus API 查询 PFS 监控指标
- 支持 40+ 个指标（容量、吞吐、QPS、延迟等）
- 支持集群级别和客户端级别指标
- 支持时间范围选择（最近1小时/4小时/24小时、自定义、对比模式）
- 数据导出 CSV
- 交互式命令行界面
- 脚本已有的配置，作为默认配置沿用

**需要优化的地方**：
- ❌ 配置硬编码，需要改为系统配置管理
- ❌ 命令行交互，需要改为 Web 界面
- ❌ 文本表格展示，需要改为可视化图表
- ❌ 同步阻塞查询，需要改为异步 API
- ❌ 数据仅内存处理，需要考虑缓存策略

---

## 2. 复用设计模式总览

### 2.1 现有功能复用清单

| 功能 | 现有实现 | 复用文件 | 复用方式 |
|------|----------|----------|----------|
| **任务管理** | Task模型 + Redis缓存 + MinIO存储 | `task.py`, `prometheus_task_service.py` | 新增 `TaskType.PFS_MONITORING` |
| **配置管理** | SystemConfig模型 | `system_config.py` | 新增 `module='pfs'` |
| **Redis缓存** | Redis客户端封装 | `redis_client.py` | 直接复用 `get_redis_client()` |
| **MinIO存储** | MinIO客户端封装 | `minio_client.py` | 直接复用 `get_minio_client()` |
| **Prometheus客户端** | 现有Prometheus配置 | `prometheus_config.py` | 参考封装PFS专用客户端 |
| **后台任务** | BackgroundTasks异步处理 | `prometheus.py` | 复用异步任务模式 |
| **API响应格式** | 统一响应封装 | `response.py` | 使用 `APIResponse` 统一格式 |
| **前端任务轮询** | 任务状态轮询工具 | `taskPoller.js` | 直接复用 |
| **前端数据表格** | DataTable组件 | `DataTable.vue` | 直接复用 |
| **前端Axios封装** | HTTP请求封装 | `axios.js` | 直接复用 |

### 2.2 代码复用架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                          PFS 监控模块                                │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  后端实现（新增文件）                                          │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐  │  │
│  │  │ pfs.py (API)    │  │ pfs_service.py  │  │ pfs_task_    │  │  │
│  │  │ - /pfs/metrics  │  │ - 业务逻辑      │  │   service.py │  │  │
│  │  │ - /pfs/query    │  │ - PromQL构建    │  │ - 复用Task   │  │  │
│  │  │ - /pfs/export   │  │ - 数据解析      │  │   机制       │  │  │
│  │  │ - /pfs/task/    │  │ - 统计计算      │  │              │  │  │
│  │  └────────┬────────┘  └────────┬────────┘  └──────┬───────┘  │  │
│  │           │                    │                  │          │  │
│  │           └────────────────────┴──────────────────┘          │  │
│  │                              │                               │  │
│  │  ┌───────────────────────────▼───────────────────────────┐  │  │
│  │  │              复用现有基础设施（无需修改）              │  │  │
│  │  │  ┌────────────┐  ┌────────────┐  ┌────────────────┐  │  │  │
│  │  │  │ RedisClient│  │ MinIOClient│  │ SystemConfig   │  │  │  │
│  │  │  │ (直接复用) │  │ (直接复用) │  │ (直接复用)     │  │  │  │
│  │  │  └────────────┘  └────────────┘  └────────────────┘  │  │  │
│  │  │  ┌────────────┐  ┌────────────┐  ┌────────────────┐  │  │  │
│  │  │  │ Task模型   │  │ TaskService│  │ APIResponse    │  │  │  │
│  │  │  │ (直接复用) │  │ (继承复用) │  │ (直接复用)     │  │  │  │
│  │  │  └────────────┘  └────────────┘  └────────────────┘  │  │  │
│  │  └───────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  前端实现（新增文件）                                          │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐  │  │
│  │  │ PFSMonitoring   │  │ QueryPanel.vue  │  │ DataDashboard│  │  │
│  │  │   .vue          │  │ (查询面板)      │  │   .vue       │  │  │
│  │  │ - 配置卡片      │  │ - 指标选择      │  │ - 大屏展示   │  │  │
│  │  │ - 查询区域      │  │ - 时间范围      │  │ - ECharts    │  │  │
│  │  │ - 数据展示      │  │ - 对比模式      │  │ - 实时刷新   │  │  │
│  │  └────────┬────────┘  └─────────────────┘  └──────────────┘  │  │
│  │           │                                                  │  │
│  │  ┌────────▼───────────────────────────────────────────────┐  │  │
│  │  │              复用现有前端组件（无需修改）              │  │  │
│  │  │  ┌────────────┐  ┌────────────┐  ┌────────────────┐  │  │  │
│  │  │  │ taskPoller │  │ DataTable  │  │ axios.js       │  │  │  │
│  │  │  │ (直接复用) │  │ (直接复用) │  │ (直接复用)     │  │  │  │
│  │  │  └────────────┘  └────────────┘  └────────────────┘  │  │  │
│  │  └───────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. 系统架构

### 3.1 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        前端 (Vue3)                               │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    监控分析中心                           │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐    │  │
│  │  │ BCC监控  │ │ BOS监控  │ │ EIP监控  │ │ PFS监控  │    │  │
│  │  │(现有)   │ │(现有)   │ │(现有)   │ │(新增)   │    │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘    │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    系统配置页面                           │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐    │  │
│  │  │ CMDB配置 │ │监控配置  │ │分析配置  │ │ PFS配置  │    │  │
│  │  │(现有)   │ │(现有)   │ │(现有)   │ │(新增)   │    │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘    │  │
│  └──────────────────────────────────────────────────────────┘  │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTP API
┌──────────────────────────▼──────────────────────────────────────┐
│                      后端 (FastAPI)                              │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ 系统配置 API (现有，直接复用)                             │  │
│  │ - GET/PUT /api/v1/config?module=pfs                      │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ PFS 监控 API (新增)                                       │  │
│  │ - /api/v1/pfs/metrics                                    │  │
│  │ - /api/v1/pfs/query                                      │  │
│  │ - /api/v1/pfs/compare                                    │  │
│  │ - /api/v1/pfs/export (异步任务)                          │  │
│  │ - /api/v1/pfs/task/{task_id} (复用任务查询)              │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Prometheus 客户端 (复用现有模式)                          │  │
│  │ - 参考：app/core/prometheus_config.py                    │  │
│  │ - 封装 HTTP 请求                                          │  │
│  │ - 认证管理 (Token + InstanceId)                           │  │
│  └──────────────────────────────────────────────────────────┘  │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTPS
┌──────────────────────────▼──────────────────────────────────────┐
│                    Prometheus API                                │
│              https://cprom.cd.baidubce.com                       │
└──────────────────────────────────────────────────────────────────┘
```

### 3.2 模块划分

| 模块 | 职责 | 位置 | 集成方式 |
|------|------|------|----------|
| **PFS配置管理** | 存储和管理 Grafana 配置、Token、实例ID | 系统配置模块 (`module='pfs'`) | **复用** `SystemConfig` 模型 |
| **PFS监控服务** | 业务逻辑：指标查询、数据处理、对比分析 | `app/services/pfs_service.py` | **参考** `prometheus_service.py` |
| **PFS任务服务** | 异步任务管理（创建、进度、完成） | `app/services/pfs_task_service.py` | **继承** `PrometheusTaskService` |
| **Prometheus客户端** | 底层 HTTP 客户端，封装 API 调用 | `app/core/pfs_prometheus_client.py` | **参考** `prometheus_config.py` |
| **PFS API路由** | RESTful API 接口 | `app/api/v1/pfs.py` | **复用** `BackgroundTasks` 模式 |
| **前端PFS页面** | 可视化界面 | `frontend/src/views/PFSMonitoring.vue` | **复用** `BCCMonitoring.vue` 模式 |
| **监控分析入口** | PFS 入口卡片 | `MonitoringAnalysis.vue` | 在模块列表中新增 PFS 卡片 |

---

## 4. 数据存储设计

### 4.1 配置存储（复用 SystemConfig）

**存储位置**：MySQL `system_config` 表（**直接复用现有表**）

```python
# 复用现有 SystemConfig 模型，module='pfs'
# 文件: app/models/system_config.py

class SystemConfig(Base):
    __tablename__ = "system_config"
    
    id = Column(Integer, primary_key=True)
    module = Column(String(50))  # 使用 'pfs'
    config_key = Column(String(100))  # 'grafana_config', 'instance_config'
    config_value = Column(Text)  # JSON 格式
    # ... 其他字段复用现有
```

**配置项设计**：

| 配置键 | 配置值 (JSON) | 说明 |
|--------|---------------|------|
| `grafana_config` | `{"url": "...", "token": "..."}` | Grafana 连接配置（加密存储 token） |
| `instance_config` | `{"instance_id": "...", "pfs_instance_id": "..."}` | 实例 ID 配置 |
| `query_defaults` | `{"step": "5m", "region": "cd"}` | 查询默认参数 |

### 4.2 监控数据存储策略（复用三层存储架构）

**参考现有功能实现**：项目中的 `prometheus.py` 和 `prometheus_task_service.py` 已实现成熟的数据缓存和持久化机制，PFS 监控应**复用以下设计模式**：

#### 4.2.1 现有功能参考

| 功能 | 现有实现 | 参考文件 | 复用方式 |
|------|----------|----------|----------|
| **任务状态缓存** | Redis 实时状态管理 | `app/utils/task_manager.py` | **直接复用** `save_task_status()` |
| **任务持久化** | MySQL Task 表存储 | `app/models/task.py` | **直接复用** `Task` 模型 |
| **结果文件存储** | MinIO 对象存储 | `app/core/minio_client.py` | **直接复用** `get_minio_client()` |
| **后台任务** | BackgroundTasks + 异步处理 | `app/api/v1/prometheus.py` | **复用模式** |

#### 4.2.2 PFS 数据存储策略

**实时查询数据**：
- 不持久化到 MySQL，直接返回前端展示
- **Redis 短期缓存**：查询结果缓存 5 分钟，减少重复请求 Prometheus
- 使用 `redis_client.set_cache()` / `get_cache()` 方法

**异步导出任务**：
- **Redis**：任务状态实时缓存（**复用** `task_manager.py`）
- **MySQL**：任务记录持久化（**复用** `Task` 模型，新增 `TaskType.PFS_EXPORT`）
- **MinIO**：导出文件长期存储（**复用** `minio_client.py`）

**数据流**：
```
实时查询：
Prometheus API → 后端服务 → Redis缓存(5min) → 前端展示

导出任务：
Prometheus API → 后台任务 → MinIO存储
                    ↓
              Redis状态 + MySQL记录
```

### 4.3 数据模型（新增）

```python
# app/models/pfs.py

from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime

class PFSConfig(BaseModel):
    """PFS配置模型"""
    grafana_url: str = "https://cprom.cd.baidubce.com/select/prometheus"
    token: str
    instance_id: str
    pfs_instance_id: str
    region: str = "cd"
    instance_type: str = "plusl2"
    step: str = "5m"
    enabled: bool = True

class PFSMetric(BaseModel):
    """PFS指标定义"""
    name: str
    zh_name: str
    description: str
    unit: str
    unit_zh: str
    category: str
    level: str  # cluster/client
    warn_threshold: Optional[float]
    critical_threshold: Optional[float]
    promql_template: str

class PFSMetricData(BaseModel):
    """PFS指标数据点"""
    timestamp: datetime
    value: float
    labels: Dict[str, str]
    metric_name: str

class PFSMetricResult(BaseModel):
    """PFS指标查询结果"""
    metric: PFSMetric
    data_points: List[PFSMetricData]
    statistics: Dict[str, float]  # avg/min/max/p95

class PFSQueryRequest(BaseModel):
    """PFS查询请求"""
    metrics: List[str]
    level: str = "cluster"  # cluster/client
    time_range: str = "1h"  # 1h/4h/24h/custom
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    step: str = "5m"
    compare_mode: bool = False  # 对比模式

class PFSCompareRequest(BaseModel):
    """PFS对比查询请求"""
    metrics: List[str]
    level: str = "cluster"
    primary_range: Dict[str, Any]  # 主时间范围
    compare_range: Dict[str, Any]  # 对比时间范围
    step: str = "5m"
```

---

## 5. API 设计

### 5.1 接口列表

```
# 配置管理（复用现有系统配置API）
GET  /api/v1/config?module=pfs              # 获取PFS配置
POST /api/v1/config/save                    # 保存PFS配置（module='pfs'）

# PFS监控API（新增）
GET  /api/v1/pfs/metrics                    # 获取指标列表
POST /api/v1/pfs/query                      # 查询指标数据
POST /api/v1/pfs/compare                    # 对比查询
POST /api/v1/pfs/export                     # 导出数据（异步任务）
GET  /api/v1/pfs/task/{task_id}             # 查询任务状态（复用任务机制）
GET  /api/v1/pfs/download/{filename}        # 下载导出文件
```

### 5.2 接口详情

#### 获取指标列表
```
GET /api/v1/pfs/metrics?level=cluster

Response: {
    "categories": [
        {
            "name": "容量",
            "metrics": [
                {"name": "FsUsage", "zh_name": "文件系统已用容量", "unit": "bytes", ...}
            ]
        }
    ]
}
```

#### 查询指标数据
```
POST /api/v1/pfs/query
Request: {
    "metrics": ["FsUsage", "FsQps"],
    "level": "cluster",
    "time_range": "1h",
    "step": "5m"
}

Response: {
    "results": [
        {
            "metric": {...},
            "data_points": [{"timestamp": "...", "value": 123}], 
            "statistics": {"avg": 100, "max": 200}
        }
    ]
}
```

#### 导出数据（复用异步任务机制）
```
POST /api/v1/pfs/export
Request: {
    "metrics": ["FsUsage"],
    "level": "cluster",
    "time_range": "24h",
    "format": "csv"
}

Response: {
    "task_id": "pfs-export-1234567890",
    "status": "pending",
    "message": "导出任务已启动"
}

# 查询任务状态（复用现有任务状态查询机制）
GET /api/v1/pfs/task/{task_id}
Response: {
    "task_id": "pfs-export-1234567890",
    "status": "completed",
    "progress": 100,
    "result_file": "pfs_results/xxx.csv",
    "download_url": "/api/v1/pfs/download/xxx.csv"
}
```

---

## 6. 后端实现

### 6.1 Prometheus 客户端（参考现有模式）

```python
# app/core/pfs_prometheus_client.py

import requests
import urllib3
from typing import List, Dict, Any
from app.core.config import settings
from app.models.system_config import SystemConfig

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class PFSPrometheusClient:
    """PFS Prometheus API 客户端
    
    参考：app/core/prometheus_config.py
    """
    
    def __init__(self, db_session):
        """从系统配置初始化客户端"""
        config = self._load_config(db_session)
        self.base_url = config["grafana_url"].rstrip('/')
        self.token = config["token"]
        self.instance_id = config["instance_id"]
        self.pfs_instance_id = config["pfs_instance_id"]
        self.region = config.get("region", "cd")
        self.instance_type = config.get("instance_type", "plusl2")
        
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "InstanceId": self.instance_id,
        }
    
    def _load_config(self, db_session) -> dict:
        """从数据库加载配置（复用 SystemConfig）"""
        configs = db_session.query(SystemConfig).filter(
            SystemConfig.module == "pfs"
        ).all()
        
        result = {}
        for config in configs:
            if config.config_value:
                import json
                result.update(json.loads(config.config_value))
        
        return result
    
    def query_range(
        self,
        promql: str,
        start_ts: int,
        end_ts: int,
        step: str = "5m"
    ) -> List[Dict[str, Any]]:
        """执行范围查询"""
        url = f"{self.base_url}/api/v1/query_range"
        params = {
            "query": promql,
            "start": start_ts,
            "end": end_ts,
            "step": step,
        }
        
        resp = requests.get(
            url,
            headers=self.headers,
            params=params,
            timeout=60,
            verify=False
        )
        
        if resp.status_code == 200:
            data = resp.json()
            if data.get("status") == "success":
                return data.get("data", {}).get("result", [])
        
        return []
```

### 6.2 PFS 服务

```python
# app/services/pfs_service.py

from typing import List, Dict, Any, Optional
from datetime import datetime
from collections import defaultdict
import time

from app.core.pfs_prometheus_client import PFSPrometheusClient
from app.models.pfs import PFSMetric, PFSMetricData, PFSMetricResult
from app.core.redis_client import get_redis_client  # 复用 Redis


class PFSService:
    """PFS监控服务
    
    参考：app/services/prometheus_service.py
    """
    
    # 指标配置（从 pfswatcher.py 优化迁移）
    METRIC_CONFIG = {
        "FsUsage": {
            "zh_name": "文件系统已用容量",
            "desc": "PFS实例当前已使用的存储容量",
            "unit": "bytes",
            "unit_zh": "字节",
            "category": "容量",
            "level": "cluster",
            "warn_threshold": 0.80,
            "critical_threshold": 0.95,
            "promql_template": 'FsUsage{region="$region", InstanceType=~"$instanceType"}'
        },
        # ... 其他指标配置
    }
    
    def __init__(self, db_session):
        self.client = PFSPrometheusClient(db_session)
        self.redis = get_redis_client()  # 复用 Redis 客户端
    
    def query_metrics_with_cache(
        self,
        metrics: List[str],
        level: str,
        start_ts: int,
        end_ts: int,
        step: str = "5m"
    ) -> List[PFSMetricResult]:
        """查询指标数据（带Redis缓存）"""
        # 构建缓存key
        cache_key = f"pfs:query:{','.join(sorted(metrics))}:{level}:{start_ts}:{end_ts}:{step}"
        
        # 尝试从缓存获取
        cached = self.redis.get_cache(cache_key)
        if cached:
            return cached
        
        # 缓存未命中，查询Prometheus
        results = self._query_metrics(metrics, level, start_ts, end_ts, step)
        
        # 写入缓存（5分钟）
        self.redis.set_cache(cache_key, results, expire=300)
        
        return results
    
    def _query_metrics(self, metrics, level, start_ts, end_ts, step):
        """实际查询逻辑"""
        results = []
        
        for metric_name in metrics:
            config = self.METRIC_CONFIG.get(metric_name)
            if not config:
                continue
            
            # 构建 PromQL
            promql = self._build_promql(metric_name, config, level)
            
            # 执行查询
            raw_results = self.client.query_range(promql, start_ts, end_ts, step)
            
            # 解析数据
            data_points = self._parse_results(raw_results, metric_name)
            
            # 计算统计值
            statistics = self._calculate_stats(data_points)
            
            results.append(PFSMetricResult(
                metric=PFSMetric(name=metric_name, **config),
                data_points=data_points,
                statistics=statistics
            ))
        
        return results
```

### 6.3 PFS 任务服务（继承复用）

```python
# app/services/pfs_task_service.py

from typing import Dict, Any, Optional
from datetime import datetime

from app.services.prometheus_task_service import PrometheusTaskService  # 继承
from app.models.task import TaskType
from app.core.logger import logger


class PFSTaskService(PrometheusTaskService):
    """PFS任务服务
    
    继承 PrometheusTaskService，复用三层存储架构：
    - Redis: 实时状态缓存
    - MySQL: 任务记录持久化
    - MinIO: 结果文件存储
    """
    
    def create_pfs_export_task(
        self,
        task_id: str,
        message: str = "PFS导出任务已创建"
    ):
        """创建PFS导出任务"""
        return self.create_task(
            task_id=task_id,
            task_type=TaskType.PFS_EXPORT,  # 需要在 TaskType 枚举中新增
            total_clusters=1,  # PFS是单实例，所以是1
            message=message
        )
    
    def complete_pfs_export_task(
        self,
        task_id: str,
        result_data: Dict[str, Any],
        upload_to_minio: bool = True
    ) -> Optional[str]:
        """完成PFS导出任务"""
        # 复用父类的 complete_task 方法
        return self.complete_task(task_id, result_data, upload_to_minio)
```

### 6.4 API 路由（复用异步任务模式）

```python
# app/api/v1/pfs.py

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import time

from app.core.deps import get_db
from app.services.pfs_service import PFSService
from app.services.pfs_task_service import PFSTaskService
from app.models.pfs import PFSQueryRequest, PFSCompareRequest
from app.models.task import TaskType
from app.utils.task_manager import get_task_status as redis_get_task_status
from app.schemas.response import APIResponse  # 复用统一响应格式

router = APIRouter(prefix="/pfs", tags=["PFS监控"])


@router.get("/metrics", summary="获取PFS指标列表", response_model=APIResponse)
async def get_metrics(level: str = None, db: Session = Depends(get_db)):
    """获取PFS指标目录"""
    try:
        service = PFSService(db)
        categories = service.get_metrics_catalog(level)
        return APIResponse(success=True, data={"categories": categories})
    except Exception as e:
        return APIResponse(success=False, error=str(e), message="获取指标列表失败")


@router.post("/query", summary="查询PFS指标数据", response_model=APIResponse)
async def query_metrics(request: PFSQueryRequest, db: Session = Depends(get_db)):
    """查询PFS指标数据（带Redis缓存）"""
    try:
        service = PFSService(db)
        
        # 计算时间范围
        end_ts = int(time.time())
        if request.time_range == "1h":
            start_ts = end_ts - 3600
        elif request.time_range == "4h":
            start_ts = end_ts - 4 * 3600
        elif request.time_range == "24h":
            start_ts = end_ts - 24 * 3600
        else:
            start_ts = int(request.start_time.timestamp())
            end_ts = int(request.end_time.timestamp())
        
        results = service.query_metrics_with_cache(
            metrics=request.metrics,
            level=request.level,
            start_ts=start_ts,
            end_ts=end_ts,
            step=request.step
        )
        
        return APIResponse(success=True, data={"results": results})
    except Exception as e:
        return APIResponse(success=False, error=str(e), message="查询指标数据失败")


# ========== 后台任务函数（复用 prometheus.py 模式）==========

def process_pfs_export_task(task_id: str, request: PFSQueryRequest):
    """
    后台任务：处理PFS导出
    
    复用 prometheus.py 的后台任务模式：
    1. 创建独立数据库会话
    2. 执行任务
    3. 上传结果到MinIO
    4. 更新任务状态
    """
    from app.core.database import SessionLocal
    
    db = SessionLocal()
    service = None
    
    try:
        # 创建任务服务
        service = PFSTaskService(db, user_id=None, username="system")
        
        # 更新进度
        service.update_progress(task_id, 0, 1, "开始查询PFS数据...")
        
        # 执行查询
        pfs_service = PFSService(db)
        # ... 查询逻辑
        
        # 生成导出文件
        service.update_progress(task_id, 0, 1, "正在生成导出文件...")
        export_data = {...}  # 导出数据
        
        # 完成任务（自动上传到MinIO）
        service.complete_pfs_export_task(task_id, export_data, upload_to_minio=True)
        
    except Exception as e:
        if service:
            service.fail_task(task_id, str(e))
    finally:
        db.close()


@router.post("/export", summary="导出PFS数据（异步任务）", response_model=APIResponse)
async def export_data(
    request: PFSQueryRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    导出PFS数据到 MinIO（异步任务）
    
    复用现有任务机制：
    - 立即返回 task_id
    - 后台执行查询、生成文件、上传 MinIO
    - 通过 GET /pfs/task/{task_id} 查询进度
    """
    try:
        # 1. 生成任务ID
        task_id = f"pfs-export-{int(time.time())}"
        
        # 2. 创建任务记录（MySQL + Redis）
        # 复用 prometheus_task_service.py 的模式
        service = PFSTaskService(db)
        service.create_pfs_export_task(
            task_id=task_id,
            message="PFS导出任务已创建"
        )
        
        # 3. 添加后台任务
        background_tasks.add_task(
            process_pfs_export_task,
            task_id,
            request
        )
        
        return APIResponse(
            success=True,
            data={
                "task_id": task_id,
                "status": "pending",
                "message": "导出任务已启动，请通过task_id查询进度"
            }
        )
    except Exception as e:
        return APIResponse(success=False, error=str(e), message="创建导出任务失败")


@router.get("/task/{task_id}", summary="查询PFS任务状态", response_model=APIResponse)
async def get_task_status(task_id: str):
    """
    查询PFS导出任务状态
    
    复用 app/utils/task_manager.py 的 Redis 状态管理机制
    """
    try:
        task_data = redis_get_task_status(task_id)
        if not task_data:
            raise HTTPException(status_code=404, detail="任务不存在或已过期")
        
        return APIResponse(
            success=True,
            data={
                "task_id": task_id,
                "status": task_data["status"],
                "message": task_data["message"],
                "progress": task_data.get("progress", 0),
                "result_file": task_data.get("result_file"),
                "timestamp": task_data["timestamp"]
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        return APIResponse(success=False, error=str(e), message="查询任务状态失败")
```

---

## 7. 前端设计

### 7.1 页面结构（复用 BCCMonitoring 模式）

```
PFS监控页面 (/monitoring/pfs)
├── 配置区域（复用 BCCMonitoring 模式）
│   ├── 从系统配置加载按钮
│   ├── Token 输入框（加密显示）
│   ├── Instance ID 输入框
│   └── 测试连接按钮
├── 查询区域
│   ├── 指标选择器（按分类分组，多选）
│   ├── 级别选择（集群/客户端）
│   ├── 时间范围选择器
│   │   ├── 快捷选项（1小时/4小时/24小时）
│   │   ├── 自定义时间（日期时间选择器）
│   │   └── 对比模式（今天vs昨天）
│   └── 查询按钮
├── 数据展示区域（数据大屏）
│   ├── 概览卡片（关键指标 + 状态标识）
│   ├── 趋势图表（ECharts 折线图/面积图）
│   ├── 对比图表（双轴对比，如开启对比模式）
│   └── 数据表格（详细数据，支持排序）
└── 操作区域
    ├── 刷新按钮
    └── 导出按钮（CSV/JSON）
```

### 7.2 数据大屏设计

```
┌─────────────────────────────────────────────────────────────┐
│  PFS 监控大屏                   [集群] [客户端] [实时] [刷新] [导出]        │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │
│  │ 容量使用率   │ │ 读吞吐       │ │ 写吞吐       │        │
│  │   75.2%     │ │  1.2 GB/s   │ │  800 MB/s   │        │
│  │   🟡 警告   │ │   ✅ 正常   │ │   ✅ 正常   │        │
│  └──────────────┘ └──────────────┘ └──────────────┘        │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────┐ ┌──────────────────────────┐ │
│  │    容量趋势图            │ │    吞吐趋势图            │ │
│  │  [折线图: 24小时]        │ │  [面积图: 24小时]        │ │
│  └──────────────────────────┘ └──────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────┐ ┌──────────────────────────┐ │
│  │    QPS 监控              │ │    延迟监控              │ │
│  │  [多线图: 读写QPS]       │ │  [热力图: 延迟分布]      │ │
│  └──────────────────────────┘ └──────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  对比分析（可选）                                            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  [双轴对比图: 今天 vs 昨天]                          │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 7.3 组件设计（复用现有组件）

```vue
<!-- PFS监控主页面：参考 BCCMonitoring.vue -->
<template>
  <div class="pfs-monitoring-page">
    <!-- 配置卡片：复用 BCCMonitoring 的认证配置卡片模式 -->
    <ConfigCard 
      module="pfs"
      @load="loadConfig"
      @test="testConnection"
    />
    
    <!-- 查询面板 -->
    <QueryPanel
      :metrics="metricCategories"
      v-model:selected="selectedMetrics"
      v-model:level="queryLevel"
      v-model:timeRange="timeRange"
      @query="executeQuery"
    />
    
    <!-- 数据大屏 -->
    <DataDashboard
      :data="queryResults"
      :loading="loading"
      :compare-mode="isCompareMode"
    />
    
    <!-- 操作栏 -->
    <ActionBar
      @export="exportData"
      @refresh="refreshData"
    />
  </div>
</template>

<script setup>
import { ref, onUnmounted } from 'vue'
import { pollTaskStatus } from '@/utils/taskPoller'  // 复用任务轮询工具
import ConfigCard from '@/components/monitoring/ConfigCard.vue'
import QueryPanel from '@/components/pfs/QueryPanel.vue'
import DataDashboard from '@/components/pfs/DataDashboard.vue'
import ActionBar from '@/components/pfs/ActionBar.vue'
import { queryPFSMetrics, exportPFSData } from '@/api/pfs'

const loading = ref(false)
const queryResults = ref([])
let pollTimer = null

// 执行查询
const executeQuery = async () => {
  loading.value = true
  try {
    const response = await queryPFSMetrics({
      metrics: selectedMetrics.value,
      level: queryLevel.value,
      time_range: timeRange.value
    })
    queryResults.value = response.data.results
  } finally {
    loading.value = false
  }
}

// 导出数据（复用任务轮询模式）
const exportData = async () => {
  const response = await exportPFSData({
    metrics: selectedMetrics.value,
    level: queryLevel.value,
    time_range: timeRange.value,
    format: 'csv'
  })
  
  const { task_id } = response.data
  
  // 复用 taskPoller.js 轮询任务状态
  pollTimer = pollTaskStatus(
    task_id,
    ({ status, progress, message }) => {
      // 更新进度条
      exportProgress.value = progress
      exportMessage.value = message
    },
    (response) => {
      // 任务完成，下载文件
      ElMessage.success('导出完成')
      downloadFile(response.result_file)
    },
    (error) => {
      // 任务失败
      ElMessage.error(error)
    }
  )
}

// 组件销毁时清除轮询
onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>
```

### 7.4 监控分析中心集成

```javascript
// MonitoringAnalysis.vue 模块列表新增 PFS
const modules = [
  {
    title: 'EIP带宽分析',
    desc: '弹性IP入向/出向带宽监控与丢包统计',
    icon: 'Connection',
    path: '/monitoring/eip',
    variant: 'primary'
  },
  {
    title: 'BOS存储分析',
    desc: '对象存储空间使用量、文件数及TOP排名',
    icon: 'Coin',
    path: '/monitoring/bos',
    variant: 'success'
  },
  {
    title: 'BCC实例分析',
    desc: '云服务器CPU、内存使用率深度监控',
    icon: 'Monitor',
    path: '/monitoring/bcc',
    variant: 'info'
  },
  {
    title: 'PFS监控分析',  // 新增
    desc: '并行文件系统容量、吞吐、QPS、延迟监控',
    icon: 'Folder',  // 或自定义图标
    path: '/monitoring/pfs',
    variant: 'warning'
  }
]
```

---

## 8. 实施计划

### 8.1 实施步骤

| 阶段 | 任务 | 时间 | 产出 |
|------|------|------|------|
| **Phase 1** | 后端基础 | Week 1 | PFSPrometheusClient、PFSService、API路由 |
| **Phase 2** | 配置管理 | Week 1 | 复用SystemConfig、配置页面 |
| **Phase 3** | 前端界面 | Week 2 | PFSMonitoring页面、复用DataTable |
| **Phase 4** | 数据大屏 | Week 2 | ECharts图表、大屏布局 |
| **Phase 5** | 对比分析 | Week 3 | 对比查询、双轴图表 |
| **Phase 6** | 导出功能 | Week 3 | 复用Task机制、MinIO存储 |
| **Phase 7** | 测试优化 | Week 4 | 集成测试、性能优化 |

### 8.2 代码文件清单

**后端文件**：
```
backend/
├── app/
│   ├── api/v1/
│   │   ├── __init__.py          # 注册 pfs 路由
│   │   └── pfs.py               # PFS API路由（复用BackgroundTasks模式）
│   ├── core/
│   │   └── pfs_prometheus_client.py  # PFS Prometheus客户端
│   ├── services/
│   │   ├── pfs_service.py       # PFS业务服务
│   │   └── pfs_task_service.py  # PFS任务服务（继承PrometheusTaskService）
│   └── models/
│       ├── pfs.py               # PFS数据模型（Pydantic）
│       └── task.py              # 复用现有Task模型，新增TaskType.PFS_EXPORT
```

**前端文件**：
```
frontend/src/
├── views/
│   └── PFSMonitoring.vue        # PFS监控主页面（复用BCCMonitoring模式）
├── components/pfs/
│   ├── QueryPanel.vue           # 查询面板
│   ├── DataDashboard.vue        # 数据大屏
│   └── MetricCard.vue           # 指标卡片
├── api/
│   └── pfs.js                   # PFS API封装（复用axios.js）
└── router/
    └── index.js                 # 添加 /monitoring/pfs 路由
```

**复用文件（无需修改）**：
```
backend/
├── app/core/
│   ├── redis_client.py          # 直接复用
│   ├── minio_client.py          # 直接复用
│   └── database.py              # 直接复用
├── app/models/
│   ├── system_config.py         # 直接复用
│   └── task.py                  # 新增枚举值即可
├── app/utils/
│   └── task_manager.py          # 直接复用
└── app/schemas/
    └── response.py              # 直接复用

frontend/src/
├── utils/
│   ├── taskPoller.js            # 直接复用
│   └── axios.js                 # 直接复用
└── components/common/
    └── DataTable.vue            # 直接复用
```

---

## 9. 与原脚本的对比优化

| 功能 | 原脚本 | 新模块 | 优化点 |
|------|--------|--------|--------|
| 配置管理 | 硬编码 | **复用**系统配置模块 | 集中管理、加密存储、动态更新 |
| 界面 | 命令行交互 | Web 可视化 | 实时图表、大屏展示、友好交互 |
| 数据展示 | 文本表格 | ECharts 图表 | 趋势图、对比图、状态标识 |
| 查询方式 | 同步阻塞 | **复用**异步 API 模式 | 非阻塞、支持并发、Redis缓存 |
| 数据存储 | 仅内存 | **复用**Redis + MinIO | 短期缓存、长期归档 |
| 对比分析 | 简单文本对比 | 可视化双轴对比 | 直观展示变化趋势 |
| 导出格式 | CSV | CSV + JSON | 更多格式选择 |
| 任务管理 | 无 | **复用**现有 Task 机制 | 统一任务ID、状态追踪、进度查询 |

---

## 10. 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| Prometheus API 变更 | 高 | 封装客户端，统一处理响应格式 |
| Token 过期 | 高 | 系统配置页面支持快速更新 |
| 查询性能问题 | 中 | **复用**Redis缓存5分钟，限制查询时间范围 |
| 数据量大 | 中 | **复用**分页加载、前端虚拟滚动 |
| 配置信息泄露 | 高 | Token加密存储，脱敏显示 |

---

## 11. 总结

本设计文档描述了将 `pfswatcher.py` 脚本集成到集群管理平台的完整方案：

1. **模块归属明确**：
   - PFS 配置 → 系统配置模块 (`module='pfs'`)
   - PFS 监控 → 监控分析中心 (`/monitoring/pfs`)

2. **数据存储规范**：
   - 配置：**复用** MySQL `system_config` 表
   - 缓存：**复用** Redis（5 分钟）
   - 导出文件：**复用** MinIO

3. **参考脚本优化**：
   - 硬编码配置 → **复用**系统配置管理
   - 命令行交互 → Web 可视化
   - 同步查询 → **复用**异步 API + BackgroundTasks
   - 内存处理 → **复用**Redis 缓存

4. **复用现有模式（核心设计原则）**：
   - **前端页面**：**复用** `BCCMonitoring.vue` 设计模式（配置卡片、查询面板、进度追踪）
   - **Prometheus 客户端**：**参考** `prometheus_config.py` 封装 PFS 专用客户端
   - **配置管理**：**复用** `SystemConfig` 模型，使用 `module='pfs'` 存储配置
   - **数据缓存**：**复用** `task_manager.py` + `redis_client.py` 缓存任务状态和查询结果
   - **任务持久化**：**继承** `PrometheusTaskService` 使用 MySQL Task 表 + MinIO 存储导出文件
   - **后台任务**：**复用** `prometheus.py` 使用 `BackgroundTasks` 实现异步导出
   - **API响应**：**复用** `response.py` 统一响应格式
   - **前端组件**：**复用** `taskPoller.js` + `DataTable.vue` + `axios.js`

**设计原则**：优先复用现有成熟的设计模式，避免重复造轮子，确保与现有系统架构保持一致。
