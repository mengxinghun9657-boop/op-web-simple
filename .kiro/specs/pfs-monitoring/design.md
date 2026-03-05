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

**需要优化的地方**：
- ❌ 配置硬编码，需要改为系统配置管理
- ❌ 命令行交互，需要改为 Web 界面
- ❌ 文本表格展示，需要改为可视化图表
- ❌ 同步阻塞查询，需要改为异步 API
- ❌ 数据仅内存处理，需要考虑缓存策略

## 2. 系统架构

### 2.1 整体架构

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
│  │ 系统配置 API (现有)                                       │  │
│  │ - GET/PUT /api/v1/config?module=pfs                      │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ PFS 监控 API (新增)                                       │  │
│  │ - /api/v1/pfs/metrics                                    │  │
│  │ - /api/v1/pfs/query                                      │  │
│  │ - /api/v1/pfs/compare                                    │  │
│  │ - /api/v1/pfs/export                                     │  │
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

### 2.2 模块划分

| 模块 | 职责 | 位置 | 集成方式 |
|------|------|------|----------|
| **PFS配置管理** | 存储和管理 Grafana 配置、Token、实例ID | 系统配置模块 (`module='pfs'`) | 复用现有 `SystemConfig` 模型 |
| **PFS监控服务** | 业务逻辑：指标查询、数据处理、对比分析 | `app/services/pfs_service.py` | 新增服务，参考 `prometheus_service.py` |
| **Prometheus客户端** | 底层 HTTP 客户端，封装 API 调用 | `app/core/prometheus_client.py` | 参考现有 `prometheus_config.py` 封装 |
| **PFS API路由** | RESTful API 接口 | `app/api/v1/pfs.py` | 新增路由，注册到主应用 |
| **前端PFS页面** | 可视化界面 | `frontend/src/views/PFSMonitoring.vue` | 复用 `BCCMonitoring.vue` 模式 |
| **监控分析入口** | PFS 入口卡片 | `MonitoringAnalysis.vue` | 在模块列表中新增 PFS 卡片 |

## 3. 数据存储设计

### 3.1 配置存储

**存储位置**：MySQL `system_config` 表

```python
# 使用现有 SystemConfig 模型，module='pfs'
class SystemConfig(Base):
    __tablename__ = "system_config"
    
    id = Column(Integer, primary_key=True)
    module = Column(String(50))  # 'pfs'
    config_key = Column(String(100))  # 'grafana_config', 'instance_config'
    config_value = Column(Text)  # JSON 格式
    # ... 其他字段
```

**配置项设计**：

| 配置键 | 配置值 (JSON) | 说明 |
|--------|---------------|------|
| `grafana_config` | `{"url": "...", "token": "..."}` | Grafana 连接配置（加密存储 token） |
| `instance_config` | `{"instance_id": "...", "pfs_instance_id": "..."}` | 实例 ID 配置 |
| `query_defaults` | `{"step": "5m", "region": "cd"}` | 查询默认参数 |

### 3.2 监控数据存储策略

**参考现有功能实现**：项目中的 `prometheus.py` 和 `prometheus_task_service.py` 已实现成熟的数据缓存和持久化机制，PFS 监控应**复用以下设计模式**：

#### 3.2.1 现有功能参考

| 功能 | 现有实现 | 参考文件 |
|------|----------|----------|
| **任务状态缓存** | Redis 实时状态管理 | `app/utils/task_manager.py` |
| **任务持久化** | MySQL Task 表存储 | `app/models/task.py` |
| **结果文件存储** | MinIO 对象存储 | `app/core/minio_client.py` |
| **后台任务** | BackgroundTasks + 异步处理 | `app/api/v1/prometheus.py` |

#### 3.2.2 PFS 数据存储策略

**实时查询数据**：
- 不持久化到 MySQL，直接返回前端展示
- **Redis 短期缓存**：查询结果缓存 5 分钟，减少重复请求 Prometheus
- 原因：监控数据实时性强，存储意义不大

**异步导出任务**：
- **Redis**：任务状态实时缓存（参考 `save_task_status()`）
- **MySQL**：任务记录持久化（参考 `Task` 模型）
- **MinIO**：导出文件长期存储（参考 `prometheus_task_service.py`）

**数据流**：
```
实时查询：
Prometheus API → 后端服务 → Redis缓存(5min) → 前端展示

导出任务：
Prometheus API → 后台任务 → MinIO存储
                    ↓
              Redis状态 + MySQL记录
```

### 3.3 数据模型

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
    level: str = "cluster"
    time_range: str  # 1h/4h/24h/custom/compare
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    step: str = "5m"

class PFSCompareRequest(BaseModel):
    """PFS对比查询请求"""
    metrics: List[str]
    level: str = "cluster"
    compare_type: str
    duration_hours: int = 4
```

## 4. API 设计

### 4.1 配置管理 API（复用现有）

```python
# 复用现有系统配置 API，module='pfs'

# 获取PFS配置
GET /api/v1/config?module=pfs
Response: {
    "grafana_config": {
        "url": "https://cprom.cd.baidubce.com/select/prometheus",
        "token": "***"  # 脱敏显示
    },
    "instance_config": {
        "instance_id": "cprom-pmdfwwqqln0w7",
        "pfs_instance_id": "pfs-mTYGr6"
    },
    "query_defaults": {
        "step": "5m",
        "region": "cd"
    }
}

# 更新PFS配置
PUT /api/v1/config
Body: {
    "module": "pfs",
    "configs": {
        "grafana_config": {"url": "...", "token": "..."},
        "instance_config": {"instance_id": "...", "pfs_instance_id": "..."}
    }
}

# 测试连接
POST /api/v1/pfs/config/test
Response: {
    "success": true,
    "message": "连接成功"
}
```

### 4.2 指标查询 API

```python
# 获取指标列表
GET /api/v1/pfs/metrics?level=cluster
Response: {
    "categories": [
        {
            "name": "容量",
            "metrics": [
                {
                    "name": "FsUsage",
                    "zh_name": "文件系统已用容量",
                    "unit": "bytes",
                    "description": "PFS实例当前已使用的存储容量"
                }
            ]
        }
    ]
}

# 查询指标数据
POST /api/v1/pfs/query
Body: {
    "metrics": ["FsUsage", "FisReadThroughput"],
    "level": "cluster",
    "time_range": "4h"
}
Response: {
    "results": [
        {
            "metric": {
                "name": "FsUsage",
                "zh_name": "文件系统已用容量",
                "unit": "bytes"
            },
            "data_points": [
                {"timestamp": "2024-01-01 12:00:00", "value": 107374182400}
            ],
            "statistics": {
                "avg": 107374182400,
                "min": 107374182400,
                "max": 107374182400,
                "p95": 107374182400
            }
        }
    ]
}

# 对比查询
POST /api/v1/pfs/compare
Body: {
    "metrics": ["FsUsage"],
    "compare_type": "today_vs_yesterday",
    "duration_hours": 4
}
Response: {
    "results": [
        {
            "metric": {...},
            "today_data": {...},
            "yesterday_data": {...},
            "change_percent": 5.2
        }
    ]
}
```

### 4.3 数据导出 API

```python
# 导出数据
POST /api/v1/pfs/export
Body: {
    "metrics": ["FsUsage", "FisReadThroughput"],
    "time_range": "24h",
    "format": "csv"
}
Response: {
    "download_url": "/api/v1/pfs/download/export_20240101_120000.csv",
    "expires_at": "2024-01-01T13:00:00Z"
}

# 下载文件（文件存储在 MinIO）
GET /api/v1/pfs/download/{filename}
```

## 5. 前端设计

### 5.1 页面结构

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

### 5.2 数据大屏设计

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

### 5.3 组件设计

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
```

### 5.4 监控分析中心集成

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

## 6. 后端实现

### 6.1 Prometheus 客户端

参考现有 `prometheus_config.py`，封装 PFS 专用客户端：

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
        """从数据库加载配置"""
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
    
    def get_metrics_catalog(self, level: str = None) -> List[Dict[str, Any]]:
        """获取指标目录"""
        categories = defaultdict(list)
        
        for name, config in self.METRIC_CONFIG.items():
            if level and config.get("level") != level:
                continue
            categories[config["category"]].append({
                "name": name,
                **config
            })
        
        return [
            {"name": cat, "metrics": metrics}
            for cat, metrics in sorted(categories.items())
        ]
    
    def query_metrics(
        self,
        metrics: List[str],
        level: str,
        start_ts: int,
        end_ts: int,
        step: str = "5m"
    ) -> List[PFSMetricResult]:
        """查询指标数据"""
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
    
    def _build_promql(self, metric_name: str, config: dict, level: str) -> str:
        """构建 PromQL"""
        template = config.get("promql_template", f'{metric_name}{{region="$region"}}')
        
        # 替换变量
        promql = template.replace("$region", self.client.region)
        promql = promql.replace("$instanceId", self.client.pfs_instance_id)
        promql = promql.replace("$instanceType", self.client.instance_type)
        
        return promql
    
    def _parse_results(self, raw_results: List[Dict], metric_name: str) -> List[PFSMetricData]:
        """解析查询结果"""
        data_points = []
        
        for series in raw_results:
            labels = series.get("metric", {})
            for ts, val in series.get("values", []):
                if val and val != "NaN":
                    try:
                        data_points.append(PFSMetricData(
                            timestamp=datetime.fromtimestamp(int(float(ts))),
                            value=float(val),
                            labels=labels,
                            metric_name=metric_name
                        ))
                    except (ValueError, TypeError):
                        continue
        
        return data_points
    
    def _calculate_stats(self, data_points: List[PFSMetricData]) -> Dict[str, float]:
        """计算统计值"""
        if not data_points:
            return {}
        
        values = [dp.value for dp in data_points]
        sorted_values = sorted(values)
        p95_idx = int(len(sorted_values) * 0.95)
        
        return {
            "count": len(values),
            "avg": sum(values) / len(values),
            "min": min(values),
            "max": max(values),
            "p95": sorted_values[p95_idx] if len(values) >= 20 else max(values)
        }
```

### 6.3 API 路由

```python
# app/api/v1/pfs.py

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from app.core.deps import get_db
from app.services.pfs_service import PFSService
from app.models.pfs import PFSQueryRequest, PFSCompareRequest

router = APIRouter(prefix="/pfs", tags=["PFS监控"])


@router.get("/metrics", summary="获取PFS指标列表")
async def get_metrics(level: str = None, db: Session = Depends(get_db)):
    """获取PFS指标目录"""
    service = PFSService(db)
    return {"categories": service.get_metrics_catalog(level)}


@router.post("/query", summary="查询PFS指标数据")
async def query_metrics(request: PFSQueryRequest, db: Session = Depends(get_db)):
    """查询PFS指标数据"""
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
    
    results = service.query_metrics(
        metrics=request.metrics,
        level=request.level,
        start_ts=start_ts,
        end_ts=end_ts,
        step=request.step
    )
    
    return {"results": results}


@router.post("/export", summary="导出PFS数据（异步任务）")
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
    # 1. 生成任务ID
    task_id = f"pfs-export-{int(time.time())}"
    
    # 2. 创建任务记录（MySQL + Redis）
    # 复用 prometheus_task_service.py 的模式
    service = PFSTaskService(db)
    service.create_task(
        task_id=task_id,
        task_type=TaskType.PFS_EXPORT,
        message="PFS导出任务已创建"
    )
    
    # 3. 添加后台任务
    background_tasks.add_task(
        process_pfs_export_task,
        task_id=task_id,
        request=request
    )
    
    return {
        "task_id": task_id,
        "status": "pending",
        "message": "导出任务已启动，请通过task_id查询进度"
    }


@router.get("/task/{task_id}", summary="查询PFS任务状态")
async def get_task_status(task_id: str):
    """
    查询PFS导出任务状态
    
    复用 app/utils/task_manager.py 的 Redis 状态管理机制
    """
    from app.utils.task_manager import get_task_status as redis_get_task_status
    
    task_data = redis_get_task_status(task_id)
    if not task_data:
        raise HTTPException(status_code=404, detail="任务不存在或已过期")
    
    return {
        "task_id": task_id,
        "status": task_data["status"],
        "message": task_data["message"],
        "progress": task_data.get("progress", 0),
        "result_file": task_data.get("result_file"),
        "timestamp": task_data["timestamp"]
    }
```

## 7. 实施计划

### 7.1 实施步骤

| 阶段 | 任务 | 时间 | 产出 |
|------|------|------|------|
| **Phase 1** | 后端基础 | Week 1 | PFSPrometheusClient、PFSService、API路由 |
| **Phase 2** | 配置管理 | Week 1 | 系统配置集成、配置页面 |
| **Phase 3** | 前端界面 | Week 2 | PFSMonitoring页面、查询面板 |
| **Phase 4** | 数据大屏 | Week 2 | ECharts图表、大屏布局 |
| **Phase 5** | 对比分析 | Week 3 | 对比查询、双轴图表 |
| **Phase 6** | 导出功能 | Week 3 | CSV/JSON导出、复用Task机制、MinIO存储 |
| **Phase 7** | 测试优化 | Week 4 | 集成测试、性能优化 |

### 7.2 代码文件清单

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
│   │   └── pfs_task_service.py  # PFS任务服务（复用prometheus_task_service.py模式）
│   └── models/
│       ├── pfs.py               # PFS数据模型
│       └── task.py              # 复用现有Task模型，新增TaskType.PFS_EXPORT
```

**前端文件**：
```
frontend/src/
├── views/
│   └── PFSMonitoring.vue        # PFS监控主页面
├── components/pfs/
│   ├── QueryPanel.vue           # 查询面板
│   ├── DataDashboard.vue        # 数据大屏
│   └── MetricCard.vue           # 指标卡片
├── api/
│   └── pfs.js                   # PFS API封装
└── router/
    └── index.js                 # 添加 /monitoring/pfs 路由
```

## 8. 与原脚本的对比优化

| 功能 | 原脚本 | 新模块 | 优化点 |
|------|--------|--------|--------|
| 配置管理 | 硬编码 | 系统配置模块 | 集中管理、加密存储、动态更新 |
| 界面 | 命令行交互 | Web 可视化 | 实时图表、大屏展示、友好交互 |
| 数据展示 | 文本表格 | ECharts 图表 | 趋势图、对比图、状态标识 |
| 查询方式 | 同步阻塞 | 异步 API | 非阻塞、支持并发、缓存优化 |
| 数据存储 | 仅内存 | Redis + MinIO | 短期缓存、长期归档 |
| 对比分析 | 简单文本对比 | 可视化双轴对比 | 直观展示变化趋势 |
| 导出格式 | CSV | CSV + JSON | 更多格式选择 |
| 任务管理 | 无 | 复用现有 Task 机制 | 统一任务ID、状态追踪、进度查询 |

## 9. 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| Prometheus API 变更 | 高 | 封装客户端，统一处理响应格式 |
| Token 过期 | 高 | 系统配置页面支持快速更新 |
| 查询性能问题 | 中 | Redis 缓存 5 分钟，限制查询时间范围 |
| 数据量大 | 中 | 分页加载，前端虚拟滚动 |
| 配置信息泄露 | 高 | Token 加密存储，脱敏显示 |

## 10. 总结

本设计文档描述了将 `pfswatcher.py` 脚本集成到集群管理平台的完整方案：

1. **模块归属明确**：
   - PFS 配置 → 系统配置模块 (`module='pfs'`)
   - PFS 监控 → 监控分析中心 (`/monitoring/pfs`)

2. **数据存储规范**：
   - 配置：MySQL `system_config` 表
   - 缓存：Redis（5 分钟）
   - 导出文件：MinIO

3. **参考脚本优化**：
   - 硬编码配置 → 系统配置管理
   - 命令行交互 → Web 可视化
   - 同步查询 → 异步 API
   - 内存处理 → Redis 缓存

4. **复用现有模式**：
   - **前端页面**：参考 `BCCMonitoring.vue` 设计配置卡片、查询面板、进度追踪
   - **Prometheus 客户端**：参考 `prometheus_config.py` 封装 PFS 专用客户端
   - **配置管理**：参考 `SystemConfig` 模型，使用 `module='pfs'` 存储配置
   - **数据缓存**：参考 `task_manager.py` 使用 Redis 缓存任务状态和查询结果
   - **任务持久化**：参考 `prometheus_task_service.py` 使用 MySQL Task 表 + MinIO 存储导出文件
   - **后台任务**：参考 `prometheus.py` 使用 `BackgroundTasks` 实现异步导出


