#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PFS 监控数据模型

定义 PFS 监控相关的 Pydantic 模型
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class PFSConfig(BaseModel):
    """PFS 配置模型"""
    grafana_url: str = Field(..., description="Grafana Prometheus URL")
    token: str = Field(..., description="认证 Token")
    instance_id: str = Field(..., description="Prometheus 实例 ID")
    pfs_instance_id: str = Field(..., description="PFS 实例 ID")
    region: str = Field(default="cd", description="区域")
    instance_type: str = Field(default="plusl2", description="实例类型")
    step: str = Field(default="5m", description="查询步长")
    default_client: str = Field(default=".*", description="默认客户端过滤")
    enabled: bool = Field(default=True, description="是否启用")
    
    class Config:
        json_schema_extra = {
            "example": {
                "grafana_url": "https://cprom.cd.baidubce.com/select/prometheus",
                "token": "eyJhbGci...",
                "instance_id": "cprom-pmdfwwqqln0w7",
                "pfs_instance_id": "pfs-mTYGr6",
                "region": "cd",
                "instance_type": "plusl2",
                "step": "5m",
                "default_client": ".*",
                "enabled": True
            }
        }


class MetricLevel(str, Enum):
    """指标级别枚举"""
    CLUSTER = "cluster"
    CLIENT = "client"


class MetricCategory(str, Enum):
    """指标分类枚举"""
    CAPACITY = "容量"
    THROUGHPUT = "吞吐"
    QPS = "QPS"
    LATENCY = "延迟"
    META_QPS = "元数据 QPS"
    META_LATENCY = "元数据延迟"


class PFSMetric(BaseModel):
    """PFS 指标定义"""
    name: str = Field(..., description="指标英文名")
    zh_name: str = Field(..., description="指标中文名")
    description: str = Field(..., description="指标描述")
    unit: str = Field(..., description="单位（英文）")
    unit_zh: str = Field(..., description="单位（中文）")
    category: str = Field(..., description="指标分类")
    level: str = Field(..., description="指标级别: cluster/client")
    warn_threshold: Optional[float] = Field(None, description="警告阈值")
    critical_threshold: Optional[float] = Field(None, description="严重阈值")
    promql_template: str = Field(..., description="PromQL 模板")
    normal_range: Optional[str] = Field(None, description="正常范围描述")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "FsUsage",
                "zh_name": "文件系统已用容量",
                "description": "PFS 实例当前已使用的存储容量",
                "unit": "bytes",
                "unit_zh": "字节",
                "category": "容量",
                "level": "cluster",
                "warn_threshold": 0.80,
                "critical_threshold": 0.95,
                "promql_template": 'FsUsage{region="$region", InstanceType=~"$instanceType"}',
                "normal_range": "0 ~ 80% 总容量"
            }
        }


class PFSMetricData(BaseModel):
    """PFS 指标数据点"""
    timestamp: int = Field(..., description="时间戳（Unix时间戳，秒）")
    value: float = Field(..., description="数值")
    client_id: Optional[str] = Field(None, description="客户端 ID（客户端级别指标）")
    client_ip: Optional[str] = Field(None, description="客户端 IP（客户端级别指标）")
    labels: Dict[str, str] = Field(default_factory=dict, description="标签")
    
    class Config:
        json_schema_extra = {
            "example": {
                "timestamp": 1704067200,
                "value": 1234567890.0,
                "client_id": "client-001",
                "client_ip": "10.0.0.1",
                "labels": {"region": "cd", "InstanceId": "pfs-mTYGr6"}
            }
        }


class PFSMetricStatistics(BaseModel):
    """PFS 指标统计值"""
    count: int = Field(default=0, description="数据点数量")
    avg: float = Field(default=0.0, description="平均值")
    min: float = Field(default=0.0, description="最小值")
    max: float = Field(default=0.0, description="最大值")
    p95: float = Field(default=0.0, description="P95 值")
    status: str = Field(default="unknown", description="状态: normal/warning/critical/unknown")
    
    class Config:
        json_schema_extra = {
            "example": {
                "count": 100,
                "avg": 1000000000.0,
                "min": 900000000.0,
                "max": 1100000000.0,
                "p95": 1080000000.0,
                "status": "normal"
            }
        }


class PFSMetricResult(BaseModel):
    """PFS 指标查询结果"""
    metric_name: str = Field(..., description="指标名称")
    zh_name: str = Field(..., description="指标中文名")
    desc: str = Field(default="", description="指标描述")
    unit: str = Field(default="", description="单位（英文）")
    unit_zh: str = Field(default="", description="单位（中文）")
    level: str = Field(default="cluster", description="指标级别")
    category: str = Field(default="其他", description="指标分类")
    data_points: List[PFSMetricData] = Field(default_factory=list, description="数据点列表")
    statistics: PFSMetricStatistics = Field(..., description="统计值")
    query_params: Dict[str, Any] = Field(default_factory=dict, description="查询参数")
    
    class Config:
        json_schema_extra = {
            "example": {
                "metric_name": "FsUsage",
                "zh_name": "文件系统已用容量",
                "desc": "PFS 实例当前已使用的存储容量",
                "unit": "bytes",
                "unit_zh": "字节",
                "level": "cluster",
                "category": "容量",
                "data_points": [
                    {
                        "timestamp": 1704067200,
                        "value": 1000000000.0,
                        "labels": {}
                    }
                ],
                "statistics": {
                    "count": 100,
                    "avg": 1000000000.0,
                    "min": 900000000.0,
                    "max": 1100000000.0,
                    "p95": 1080000000.0,
                    "status": "normal"
                },
                "query_params": {
                    "region": "cd",
                    "instance_id": "pfs-mTYGr6"
                }
            }
        }


class TimeRange(str, Enum):
    """时间范围枚举"""
    ONE_HOUR = "1h"
    FOUR_HOURS = "4h"
    TWENTY_FOUR_HOURS = "24h"
    CUSTOM = "custom"


class PFSQueryRequest(BaseModel):
    """PFS 查询请求"""
    metrics: List[str] = Field(..., description="指标名称列表", min_length=1)
    level: MetricLevel = Field(default=MetricLevel.CLUSTER, description="指标级别")
    region: str = Field(default="cd", description="区域")
    instance_type: str = Field(default="plusl2", description="实例类型")
    instance_id: str = Field(..., description="PFS 实例 ID")
    client_id: Optional[str] = Field(None, description="客户端 ID（客户端级别必需）")
    start_time: int = Field(..., description="开始时间戳（Unix时间戳，秒）")
    end_time: int = Field(..., description="结束时间戳（Unix时间戳，秒）")
    step: str = Field(default="5m", description="查询步长")
    
    class Config:
        json_schema_extra = {
            "example": {
                "metrics": ["FsUsage", "FsCapacity"],
                "level": "cluster",
                "region": "cd",
                "instance_type": "plusl2",
                "instance_id": "pfs-mTYGr6",
                "start_time": 1704067200,
                "end_time": 1704070800,
                "step": "5m"
            }
        }


class PFSCompareRequest(BaseModel):
    """PFS 对比查询请求"""
    metrics: List[str] = Field(..., description="指标名称列表", min_length=1)
    level: MetricLevel = Field(default=MetricLevel.CLUSTER, description="指标级别")
    region: str = Field(default="cd", description="区域")
    instance_type: str = Field(default="plusl2", description="实例类型")
    instance_id: str = Field(..., description="PFS 实例 ID")
    client_id: Optional[str] = Field(None, description="客户端 ID")
    time_range_hours: int = Field(default=4, description="时间范围（小时）")
    step: str = Field(default="5m", description="查询步长")
    
    class Config:
        json_schema_extra = {
            "example": {
                "metrics": ["FsUsage"],
                "level": "cluster",
                "region": "cd",
                "instance_type": "plusl2",
                "instance_id": "pfs-mTYGr6",
                "time_range_hours": 4,
                "step": "5m"
            }
        }


class PFSCompareResult(BaseModel):
    """PFS 对比查询结果"""
    metric_name: str = Field(..., description="指标名称")
    primary_avg: float = Field(..., description="主时间段平均值")
    compare_avg: float = Field(..., description="对比时间段平均值")
    change_percent: float = Field(..., description="变化百分比")
    trend: str = Field(..., description="趋势: up/down/stable")
    status: str = Field(..., description="状态: stable/fluctuate/dramatic")
    
    class Config:
        json_schema_extra = {
            "example": {
                "metric_name": "FsUsage",
                "primary_avg": 1100000000.0,
                "compare_avg": 1000000000.0,
                "change_percent": 10.0,
                "trend": "up",
                "status": "stable"
            }
        }


class PFSExportRequest(BaseModel):
    """PFS 导出请求"""
    metrics: List[str] = Field(..., description="指标名称列表", min_length=1)
    level: MetricLevel = Field(default=MetricLevel.CLUSTER, description="指标级别")
    region: str = Field(default="cd", description="区域")
    instance_type: str = Field(default="plusl2", description="实例类型")
    instance_id: str = Field(..., description="PFS 实例 ID")
    client_id: Optional[str] = Field(None, description="客户端 ID")
    start_time: int = Field(..., description="开始时间戳（Unix时间戳，秒）")
    end_time: int = Field(..., description="结束时间戳（Unix时间戳，秒）")
    step: str = Field(default="5m", description="查询步长")
    format: str = Field(default="csv", description="导出格式: csv/json")
    
    class Config:
        json_schema_extra = {
            "example": {
                "metrics": ["FsUsage", "FsCapacity"],
                "level": "cluster",
                "region": "cd",
                "instance_type": "plusl2",
                "instance_id": "pfs-mTYGr6",
                "start_time": 1704067200,
                "end_time": 1704153600,
                "step": "5m",
                "format": "csv"
            }
        }


class PFSClientInfo(BaseModel):
    """PFS 客户端信息"""
    client_id: str = Field(..., description="客户端 ID")
    client_ip: str = Field(..., description="客户端 IP")
    read_throughput: Optional[float] = Field(None, description="读吞吐（最新值）")
    write_throughput: Optional[float] = Field(None, description="写吞吐（最新值）")
    total_throughput: Optional[float] = Field(None, description="总吞吐")
    is_active: bool = Field(default=True, description="是否活跃")
    last_seen: Optional[datetime] = Field(None, description="最后活跃时间")
    
    class Config:
        json_schema_extra = {
            "example": {
                "client_id": "client-001",
                "client_ip": "10.0.0.1",
                "read_throughput": 1000000.0,
                "write_throughput": 500000.0,
                "total_throughput": 1500000.0,
                "is_active": True,
                "last_seen": "2024-01-01T00:00:00Z"
            }
        }


class PFSMetricCategory(BaseModel):
    """PFS 指标分类"""
    name: str = Field(..., description="分类名称")
    metrics: List[PFSMetric] = Field(default_factory=list, description="指标列表")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "容量",
                "metrics": [
                    {
                        "name": "FsUsage",
                        "zh_name": "文件系统已用容量",
                        "description": "PFS 实例当前已使用的存储容量",
                        "unit": "bytes",
                        "unit_zh": "字节",
                        "category": "容量",
                        "level": "cluster",
                        "promql_template": 'FsUsage{region="$region"}'
                    }
                ]
            }
        }
