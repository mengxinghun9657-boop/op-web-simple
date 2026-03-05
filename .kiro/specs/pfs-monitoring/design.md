# PFS 监控模块设计文档

## 1. 概述

### 1.1 背景

PFS（Parallel File System）是百度云提供的高性能并行文件存储服务。当前项目中有一个独立的 Python 脚本 `pfswatcher.py` 用于查询 PFS 监控数据，但缺乏 Web 界面和系统集成。

### 1.2 目标

将 PFS 监控功能集成到集群管理平台，提供：
- 可视化配置管理（Grafana 地址、Token、实例 ID）
- Web 界面实时展示 PFS 监控数据
- 支持数据对比分析（当前 vs 历史）
- 数据大屏展示效果
- 数据导出功能

### 1.3 参考脚本

原脚本 `pfswatcher.py` 功能：
- 通过 Prometheus API 查询 PFS 监控指标
- 支持 40+ 个指标（容量、吞吐、QPS、延迟等）
- 支持集群级别和客户端级别指标
- 支持时间范围选择（最近1小时/4小时/24小时、自定义、对比模式）
- 数据导出 CSV
- 交互式命令行界面

## 2. 系统架构

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        前端 (Vue3)                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ PFS监控配置   │  │ 数据查询界面  │  │ 数据大屏展示         │  │
│  │ - Grafana配置 │  │ - 指标选择   │  │ - 实时图表           │  │
│  │ - Token管理   │  │ - 时间范围   │  │ - 对比分析           │  │
│  │ - 实例ID配置  │  │ - 数据对比   │  │ - 导出功能           │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTP API
┌──────────────────────────▼──────────────────────────────────────┐
│                      后端 (FastAPI)                              │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ PFS监控服务 (PFSService)                                   │  │
│  │ - 指标查询                                                 │  │
│  │ - 数据聚合                                                 │  │
│  │ - 对比分析                                                 │  │
│  │ - 数据导出                                                 │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Prometheus 客户端                                          │  │
│  │ - 封装 HTTP 请求                                           │  │
│  │ - 认证管理 (Token + InstanceId)                            │  │
│  │ - 数据解析                                                 │  │
│  └──────────────────────────────────────────────────────────┘  │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTPS
┌──────────────────────────▼──────────────────────────────────────┐
│                    Prometheus API                                │
│              https://cprom.cd.baidubce.com                       │
└──────────────────────────────────────────────────────────────────┘
```

### 2.2 模块划分

| 模块 | 职责 | 位置 |
|------|------|------|
| **PFS配置管理** | 存储和管理 Grafana 配置、Token、实例ID | 系统配置模块扩展 |
| **PFS监控服务** | 业务逻辑：指标查询、数据处理、对比分析 | `app/services/pfs_service.py` |
| **Prometheus客户端** | 底层 HTTP 客户端，封装 API 调用 | `app/core/prometheus_client.py` |
| **PFS API路由** | RESTful API 接口 | `app/api/v1/pfs.py` |
| **前端PFS页面** | 可视化界面 | `frontend/src/views/PFSMonitoring.vue` |

## 3. 数据模型

### 3.1 配置模型

```python
# 系统配置扩展 - PFS监控配置
class PFSConfig(BaseModel):
    """PFS监控配置"""
    grafana_url: str = "https://cprom.cd.baidubce.com/select/prometheus"
    token: str  # JWT Token
    instance_id: str  # Prometheus 实例ID
    pfs_instance_id: str  # PFS 实例ID
    region: str = "cd"
    instance_type: str = "plusl2"
    step: str = "5m"  # 查询步长
    enabled: bool = True
```

### 3.2 指标数据模型

```python
class PFSMetric(BaseModel):
    """PFS指标定义"""
    name: str  # 指标英文名
    zh_name: str  # 指标中文名
    description: str  # 指标说明
    unit: str  # 单位
    unit_zh: str  # 中文单位
    category: str  # 分类（容量/吞吐/QPS/延迟等）
    level: str  # 级别（cluster/client）
    warn_threshold: Optional[float]  # 警告阈值
    critical_threshold: Optional[float]  # 严重阈值
    promql_template: str  # PromQL 模板

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
```

### 3.3 查询请求模型

```python
class PFSQueryRequest(BaseModel):
    """PFS查询请求"""
    metrics: List[str]  # 指标名称列表
    level: str = "cluster"  # cluster/client
    time_range: str  # 1h/4h/24h/custom/compare
    start_time: Optional[datetime]  # 自定义开始时间
    end_time: Optional[datetime]  # 自定义结束时间
    step: str = "5m"  # 查询步长

class PFSCompareRequest(BaseModel):
    """PFS对比查询请求"""
    metrics: List[str]
    level: str = "cluster"
    compare_type: str  # today_vs_yesterday/this_week_vs_last_week
    duration_hours: int = 4  # 对比时长
```

## 4. API 设计

### 4.1 配置管理 API

```python
# 获取PFS配置
GET /api/v1/pfs/config
Response: {
    "grafana_url": "https://cprom.cd.baidubce.com/select/prometheus",
    "instance_id": "cprom-pmdfwwqqln0w7",
    "pfs_instance_id": "pfs-mTYGr6",
    "region": "cd",
    "instance_type": "plusl2",
    "step": "5m",
    "enabled": true
}

# 更新PFS配置
PUT /api/v1/pfs/config
Body: {
    "token": "eyJhbGciOiJIUzI1NiIs...",
    "instance_id": "cprom-pmdfwwqqln0w7",
    "pfs_instance_id": "pfs-mTYGr6"
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
GET /api/v1/pfs/metrics
Query: level=cluster|client
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
    "format": "csv"  # csv/json
}
Response: {
    "download_url": "/api/v1/pfs/download/export_20240101_120000.csv"
}

# 下载文件
GET /api/v1/pfs/download/{filename}
```

## 5. 前端设计

### 5.1 页面结构

```
PFS监控页面 (/pfs-monitoring)
├── 配置区域
│   ├── Grafana URL 输入框
│   ├── Token 输入框（加密显示）
│   ├── Instance ID 输入框
│   ├── PFS 实例 ID 输入框
│   └── 测试连接按钮
├── 查询区域
│   ├── 指标选择器（按分类分组）
│   ├── 级别选择（集群/客户端）
│   ├── 时间范围选择器
│   │   ├── 快捷选项（1小时/4小时/24小时）
│   │   ├── 自定义时间
│   │   └── 对比模式
│   └── 查询按钮
├── 数据展示区域
│   ├── 概览卡片（关键指标）
│   ├── 趋势图表（ECharts）
│   ├── 对比图表（双轴对比）
│   └── 数据表格
└── 操作区域
    ├── 刷新按钮
    ├── 导出CSV按钮
    └── 导出JSON按钮
```

### 5.2 数据大屏设计

```
┌─────────────────────────────────────────────────────────────┐
│  PFS 监控大屏                    [实时] [刷新] [导出]        │
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
│  对比分析                                                    │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  [双轴对比图: 今天 vs 昨天]                          │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 5.3 关键组件

```vue
<!-- PFS监控主页面 -->
<template>
  <div class="pfs-monitoring-page">
    <!-- 配置卡片 -->
    <PFSConfigCard 
      v-model:config="pfsConfig"
      @test="testConnection"
    />
    
    <!-- 查询条件 -->
    <PFSQueryPanel
      v-model:metrics="selectedMetrics"
      v-model:level="queryLevel"
      v-model:timeRange="timeRange"
      @query="executeQuery"
    />
    
    <!-- 数据大屏 -->
    <PFSDataDashboard
      :data="queryResults"
      :loading="loading"
      :compare-mode="isCompareMode"
    />
    
    <!-- 操作栏 -->
    <PFSActionBar
      @export="exportData"
      @refresh="refreshData"
    />
  </div>
</template>
```

## 6. 后端实现

### 6.1 Prometheus 客户端

```python
# app/core/prometheus_client.py

import requests
import urllib3
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.core.config import settings

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class PrometheusClient:
    """Prometheus API 客户端"""
    
    def __init__(self, base_url: str, token: str, instance_id: str):
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.instance_id = instance_id
        self.headers = {
            "Authorization": f"Bearer {token}",
            "InstanceId": instance_id,
        }
    
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
    
    def get_label_values(self, label_name: str, match_query: str) -> List[str]:
        """获取标签值列表"""
        url = f"{self.base_url}/api/v1/label/{label_name}/values"
        params = {"match[]": match_query}
        
        resp = requests.get(
            url,
            headers=self.headers,
            params=params,
            timeout=30,
            verify=False
        )
        
        if resp.status_code == 200:
            return resp.json().get("data", [])
        return []
```

### 6.2 PFS 服务

```python
# app/services/pfs_service.py

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import time
from collections import defaultdict

from app.core.prometheus_client import PrometheusClient
from app.core.config import settings
from app.models.pfs import PFSMetric, PFSMetricData, PFSMetricResult


class PFSService:
    """PFS监控服务"""
    
    # 指标配置（从 pfswatcher.py 迁移）
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
        "FisReadThroughput": {
            "zh_name": "集群读吞吐",
            "desc": "PFS集群整体读取数据速率",
            "unit": "binBps",
            "unit_zh": "二进制字节/秒",
            "category": "吞吐",
            "level": "cluster",
            "promql_template": 'FisReadThroughput{region="$region", InstanceId="$instanceId"}'
        },
        # ... 更多指标配置
    }
    
    def __init__(self, client: PrometheusClient):
        self.client = client
    
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
        promql = template.replace("$region", settings.PFS_REGION)
        promql = promql.replace("$instanceId", settings.PFS_INSTANCE_ID)
        promql = promql.replace("$instanceType", settings.PFS_INSTANCE_TYPE)
        
        return promql
    
    def _parse_results(
        self,
        raw_results: List[Dict],
        metric_name: str
    ) -> List[PFSMetricData]:
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
from app.core.prometheus_client import PrometheusClient
from app.services.pfs_service import PFSService
from app.models.pfs import PFSQueryRequest, PFSCompareRequest

router = APIRouter(prefix="/pfs", tags=["PFS监控"])


def get_pfs_service() -> PFSService:
    """获取PFS服务实例"""
    from app.core.config import settings
    client = PrometheusClient(
        base_url=settings.PFS_GRAFANA_URL,
        token=settings.PFS_TOKEN,
        instance_id=settings.PFS_INSTANCE_ID
    )
    return PFSService(client)


@router.get("/metrics", summary="获取PFS指标列表")
async def get_metrics(level: str = None):
    """获取PFS指标目录"""
    service = get_pfs_service()
    return {"categories": service.get_metrics_catalog(level)}


@router.post("/query", summary="查询PFS指标数据")
async def query_metrics(request: PFSQueryRequest):
    """查询PFS指标数据"""
    service = get_pfs_service()
    
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


@router.post("/compare", summary="对比查询")
async def compare_metrics(request: PFSCompareRequest):
    """对比查询（今天vs昨天等）"""
    service = get_pfs_service()
    
    # 计算对比时间范围
    end_today = int(time.time())
    start_today = end_today - request.duration_hours * 3600
    
    end_yesterday = end_today - 24 * 3600
    start_yesterday = start_today - 24 * 3600
    
    # 查询今天数据
    today_results = service.query_metrics(
        metrics=request.metrics,
        level=request.level,
        start_ts=start_today,
        end_ts=end_today
    )
    
    # 查询昨天数据
    yesterday_results = service.query_metrics(
        metrics=request.metrics,
        level=request.level,
        start_ts=start_yesterday,
        end_ts=end_yesterday
    )
    
    # 合并对比结果
    compare_results = []
    for today, yesterday in zip(today_results, yesterday_results):
        today_avg = today.statistics.get("avg", 0)
        yesterday_avg = yesterday.statistics.get("avg", 0)
        
        change_pct = 0
        if yesterday_avg != 0:
            change_pct = (today_avg - yesterday_avg) / abs(yesterday_avg) * 100
        
        compare_results.append({
            "metric": today.metric,
            "today_data": today,
            "yesterday_data": yesterday,
            "change_percent": change_pct
        })
    
    return {"results": compare_results}
```

## 7. 实施计划

### 7.1 实施步骤

| 阶段 | 任务 | 时间 | 产出 |
|------|------|------|------|
| **Phase 1** | 后端基础 | Week 1 | PrometheusClient、PFSService、API路由 |
| **Phase 2** | 配置管理 | Week 1 | 系统配置扩展、配置页面 |
| **Phase 3** | 前端界面 | Week 2 | PFS监控页面、数据展示组件 |
| **Phase 4** | 数据大屏 | Week 2 | ECharts图表、大屏布局 |
| **Phase 5** | 对比分析 | Week 3 | 对比查询、双轴图表 |
| **Phase 6** | 导出功能 | Week 3 | CSV/JSON导出、下载接口 |
| **Phase 7** | 测试优化 | Week 4 | 集成测试、性能优化 |

### 7.2 代码文件清单

**后端文件**：
```
backend/
├── app/
│   ├── api/v1/
│   │   └── pfs.py              # PFS API路由
│   ├── core/
│   │   └── prometheus_client.py # Prometheus客户端
│   ├── services/
│   │   └── pfs_service.py      # PFS业务服务
│   └── models/
│       └── pfs.py              # PFS数据模型
```

**前端文件**：
```
frontend/src/
├── views/
│   └── PFSMonitoring.vue       # PFS监控主页面
├── components/pfs/
│   ├── PFSConfigCard.vue       # 配置卡片
│   ├── PFSQueryPanel.vue       # 查询面板
│   ├── PFSDataDashboard.vue    # 数据大屏
│   └── PFSActionBar.vue        # 操作栏
└── api/
    └── pfs.js                  # PFS API封装
```

## 8. 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| Prometheus API 变更 | 高 | 封装客户端，统一处理响应格式 |
| Token 过期 | 高 | 配置页面支持快速更新 Token |
| 查询性能问题 | 中 | 限制查询时间范围，添加缓存 |
| 数据量大 | 中 | 分页加载，前端虚拟滚动 |

## 9. 总结

本设计文档描述了将 `pfswatcher.py` 脚本集成到集群管理平台的完整方案：

1. **配置管理**：通过系统配置模块管理 Grafana 连接信息
2. **后端服务**：封装 Prometheus 客户端，提供 RESTful API
3. **前端界面**：可视化查询界面，支持数据大屏展示
4. **数据对比**：支持今天 vs 昨天等对比分析
5. **数据导出**：支持 CSV/JSON 格式导出

实施周期约 4 周，可直接复用现有项目的组件和样式体系。
