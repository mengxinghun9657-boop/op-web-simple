#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PFS 监控数据交互式查询工具
功能：查询/对比/导出 PFS 性能指标
支持：当前数据 | 历史数据 | 同比对比 | CSV导出
基于 Dashboard: PFS-ONLINE (uid: Yr0GA4PHz2)
"""

import requests
import csv
import json
import os
import time
import urllib3
from datetime import datetime, timedelta
from collections import defaultdict
import sys

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ================= 配置区 =================
PROM_BASE_URL = "https://cprom.cd.baidubce.com/select/prometheus"
PROM_QUERY_URL = f"{PROM_BASE_URL}/api/v1/query_range"
PROM_LABELS_URL = f"{PROM_BASE_URL}/api/v1/label"

# 🔑 PFS 实例配置（已验证可用）
PROM_INSTANCE_ID = "cprom-pmdfwwqqln0w7"
TOKEN = os.getenv("PROM_TOKEN", 
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJuYW1lc3BhY2UiOiJjcHJvbS1wbWRmd3dxcWxuMHc3Iiwic2VjcmV0TmFtZSI6ImYwMDhkYjQ3NTE4OTRhZmU5Yjg1MWUzMmEyMDY4MzM1IiwiZXhwIjo0OTAxMzI4NzY4LCJpc3MiOiJjcHJvbSJ9."
    "xMrMQgaV1Hb0WwF04sTFFTaMWyfqoutB4670dTpIIHA"
)

# 默认查询参数
DEFAULT_REGION = "cd"
DEFAULT_INSTANCE_TYPE = "plusl2"
DEFAULT_INSTANCE_ID = "pfs-mTYGr6"
DEFAULT_STEP = "5m"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "InstanceId": PROM_INSTANCE_ID,
}
# ========================================================

# 📊 指标中文映射字典（含说明和正常范围）
# 基于 Dashboard JSON 中所有面板的指标整理
METRIC_CONFIG = {
    # ===== Usage Summary (容量) =====
    "FsUsage": {
        "zh_name": "文件系统已用容量",
        "desc": "PFS 实例当前已使用的存储容量",
        "unit": "bytes",
        "unit_zh": "字节",
        "normal_range": "0 ~ 80% 总容量",
        "warn_threshold": 0.80,
        "critical_threshold": 0.95,
        "category": "容量",
        "level": "cluster",
        "promql_template": 'FsUsage{region="$region", InstanceType=~"$instanceType"}'
    },
    "FsCapacity": {
        "zh_name": "文件系统总容量",
        "desc": "PFS 实例配置的总存储容量",
        "unit": "bytes",
        "unit_zh": "字节",
        "normal_range": "固定值",
        "warn_threshold": None,
        "critical_threshold": None,
        "category": "容量",
        "level": "cluster",
        "promql_template": 'FsCapacity{region="$region", InstanceType=~"$instanceType"}'
    },
    "FsCapacityPercentage": {
        "zh_name": "容量使用率",
        "desc": "已用容量 / 总容量 的百分比",
        "unit": "percentunit",
        "unit_zh": "%",
        "normal_range": "0% ~ 80%",
        "warn_threshold": 0.80,
        "critical_threshold": 0.95,
        "category": "容量",
        "level": "cluster",
        "promql_template": 'FsUsage{region="$region", InstanceType=~"$instanceType"} / FsCapacity{region="$region", InstanceType=~"$instanceType"}'
    },
    
    # ===== Cluster Throughput (集群吞吐) =====
    "FisReadThroughput": {
        "zh_name": "集群读吞吐",
        "desc": "PFS 集群整体读取数据速率",
        "unit": "binBps",
        "unit_zh": "二进制字节/秒",
        "normal_range": "取决于业务负载",
        "warn_threshold": -0.50,  # 下降 50% 告警
        "critical_threshold": -0.90,
        "category": "吞吐",
        "level": "cluster",
        "promql_template": 'FisReadThroughput{region="$region", InstanceId="$instanceId"}'
    },
    "FisWriteThroughput": {
        "zh_name": "集群写吞吐",
        "desc": "PFS 集群整体写入数据速率",
        "unit": "binBps",
        "unit_zh": "二进制字节/秒",
        "normal_range": "取决于业务负载",
        "warn_threshold": -0.50,
        "critical_threshold": -0.90,
        "category": "吞吐",
        "level": "cluster",
        "promql_template": 'FisWriteThroughput{region="$region", InstanceId="$instanceId"}'
    },
    
    # ===== Cluster QPS (集群 QPS) =====
    "FisReadQps": {
        "zh_name": "读操作 QPS",
        "desc": "每秒读取请求次数",
        "unit": "iops",
        "unit_zh": "次/秒",
        "normal_range": "取决于业务负载",
        "warn_threshold": -0.50,
        "critical_threshold": -0.90,
        "category": "QPS",
        "level": "cluster",
        "promql_template": 'FisReadQps{region="$region", InstanceId="$instanceId"}'
    },
    "FisWriteQps": {
        "zh_name": "写操作 QPS",
        "desc": "每秒写入请求次数",
        "unit": "iops",
        "unit_zh": "次/秒",
        "normal_range": "取决于业务负载",
        "warn_threshold": -0.50,
        "critical_threshold": -0.90,
        "category": "QPS",
        "level": "cluster",
        "promql_template": 'FisWriteQps{region="$region", InstanceId="$instanceId"}'
    },
    
    # ===== Cluster Latency (集群延迟) =====
    "VfsxReadAvgLatency": {
        "zh_name": "读操作平均延迟",
        "desc": "读取请求的平均响应时间",
        "unit": "µs",
        "unit_zh": "微秒",
        "normal_range": "< 500 µs",
        "warn_threshold": 1000,
        "critical_threshold": 5000,
        "category": "延迟",
        "level": "cluster",
        "promql_template": 'VfsxReadAvgLatency{region="$region", InstanceType=~"$instanceType", InstanceId="$instanceId"}'
    },
    "VfsxWriteAvgLatency": {
        "zh_name": "写操作平均延迟",
        "desc": "写入请求的平均响应时间",
        "unit": "µs",
        "unit_zh": "微秒",
        "normal_range": "< 1000 µs",
        "warn_threshold": 2000,
        "critical_threshold": 10000,
        "category": "延迟",
        "level": "cluster",
        "promql_template": 'VfsxWriteAvgLatency{region="$region", InstanceType=~"$instanceType", InstanceId="$instanceId"}'
    },
    
    # ===== Meta QPS (元数据 QPS - 集群) =====
    "VfsxLookupQps": {"zh_name": "Lookup QPS", "desc": "路径查找请求频率", "unit": "ops", "unit_zh": "次/秒", "normal_range": "取决于业务", "warn_threshold": None, "critical_threshold": None, "category": "元数据 QPS", "level": "cluster", "promql_template": 'VfsxLookupQps{region="$region", InstanceId="$instanceId"}'},
    "VfsxGetattrQps": {"zh_name": "Getattr QPS", "desc": "获取文件属性请求频率", "unit": "ops", "unit_zh": "次/秒", "normal_range": "取决于业务", "warn_threshold": None, "critical_threshold": None, "category": "元数据 QPS", "level": "cluster", "promql_template": 'VfsxGetattrQps{region="$region", InstanceId="$instanceId"}'},
    "VfsxSetattrQps": {"zh_name": "Setattr QPS", "desc": "设置文件属性请求频率", "unit": "ops", "unit_zh": "次/秒", "normal_range": "取决于业务", "warn_threshold": None, "critical_threshold": None, "category": "元数据 QPS", "level": "cluster", "promql_template": 'VfsxSetattrQps{region="$region", InstanceId="$instanceId"}'},
    "VfsxLinkQps": {"zh_name": "Link QPS", "desc": "创建硬链接请求频率", "unit": "ops", "unit_zh": "次/秒", "normal_range": "取决于业务", "warn_threshold": None, "critical_threshold": None, "category": "元数据 QPS", "level": "cluster", "promql_template": 'VfsxLinkQps{region="$region", InstanceId="$instanceId"}'},
    "VfsxRemoveQps": {"zh_name": "Remove QPS", "desc": "删除文件请求频率", "unit": "ops", "unit_zh": "次/秒", "normal_range": "取决于业务", "warn_threshold": None, "critical_threshold": None, "category": "元数据 QPS", "level": "cluster", "promql_template": 'VfsxRemoveQps{region="$region", InstanceId="$instanceId"}'},
    "VfsxMkdirQps": {"zh_name": "Mkdir QPS", "desc": "创建目录请求频率", "unit": "ops", "unit_zh": "次/秒", "normal_range": "取决于业务", "warn_threshold": None, "critical_threshold": None, "category": "元数据 QPS", "level": "cluster", "promql_template": 'VfsxMkdirQps{region="$region", InstanceId="$instanceId"}'},
    "VfsxRmdirQps": {"zh_name": "Rmdir QPS", "desc": "删除目录请求频率", "unit": "ops", "unit_zh": "次/秒", "normal_range": "取决于业务", "warn_threshold": None, "critical_threshold": None, "category": "元数据 QPS", "level": "cluster", "promql_template": 'VfsxRmdirQps{region="$region", InstanceId="$instanceId"}'},
    "VfsxSymlinkQps": {"zh_name": "Symlink QPS", "desc": "创建软链接请求频率", "unit": "ops", "unit_zh": "次/秒", "normal_range": "取决于业务", "warn_threshold": None, "critical_threshold": None, "category": "元数据 QPS", "level": "cluster", "promql_template": 'VfsxSymlinkQps{region="$region", InstanceId="$instanceId"}'},
    "VfsxReadlinkQps": {"zh_name": "Readlink QPS", "desc": "读取软链接请求频率", "unit": "ops", "unit_zh": "次/秒", "normal_range": "取决于业务", "warn_threshold": None, "critical_threshold": None, "category": "元数据 QPS", "level": "cluster", "promql_template": 'VfsxReadlinkQps{region="$region", InstanceId="$instanceId"}'},
    "VfsxReaddirQps": {"zh_name": "Readdir QPS", "desc": "读取目录内容请求频率", "unit": "ops", "unit_zh": "次/秒", "normal_range": "取决于业务", "warn_threshold": None, "critical_threshold": None, "category": "元数据 QPS", "level": "cluster", "promql_template": 'VfsxReaddirQps{region="$region", InstanceId="$instanceId"}'},
    "VfsxRenameQps": {"zh_name": "Rename QPS", "desc": "重命名请求频率", "unit": "ops", "unit_zh": "次/秒", "normal_range": "取决于业务", "warn_threshold": None, "critical_threshold": None, "category": "元数据 QPS", "level": "cluster", "promql_template": 'VfsxRenameQps{region="$region", InstanceId="$instanceId"}'},
    "VfsxStatfsQps": {"zh_name": "Statfs QPS", "desc": "文件系统状态查询频率", "unit": "ops", "unit_zh": "次/秒", "normal_range": "取决于业务", "warn_threshold": None, "critical_threshold": None, "category": "元数据 QPS", "level": "cluster", "promql_template": 'VfsxStatfsQps{region="$region", InstanceId="$instanceId"}'},
    
    # ===== Meta Latency (元数据延迟 - 集群) =====
    "VfsxLookupAvgLatency": {"zh_name": "Lookup 平均延迟", "desc": "路径查找请求平均响应时间", "unit": "µs", "unit_zh": "微秒", "normal_range": "< 200 µs", "warn_threshold": 500, "critical_threshold": 2000, "category": "元数据延迟", "level": "cluster", "promql_template": 'VfsxLookupAvgLatency{region="$region", InstanceType=~"$instanceType", InstanceId="$instanceId"}'},
    "VfsxGetattrAvgLatency": {"zh_name": "Getattr 平均延迟", "desc": "获取属性请求平均响应时间", "unit": "µs", "unit_zh": "微秒", "normal_range": "< 200 µs", "warn_threshold": 500, "critical_threshold": 2000, "category": "元数据延迟", "level": "cluster", "promql_template": 'VfsxGetattrAvgLatency{region="$region", InstanceType=~"$instanceType", InstanceId="$instanceId"}'},
    "VfsxSetattrAvgLatency": {"zh_name": "Setattr 平均延迟", "desc": "设置属性请求平均响应时间", "unit": "µs", "unit_zh": "微秒", "normal_range": "< 300 µs", "warn_threshold": 800, "critical_threshold": 3000, "category": "元数据延迟", "level": "cluster", "promql_template": 'VfsxSetattrAvgLatency{region="$region", InstanceType=~"$instanceType", InstanceId="$instanceId"}'},
    "VfsxLinkAvgLatency": {"zh_name": "Link 平均延迟", "desc": "创建硬链接请求平均响应时间", "unit": "µs", "unit_zh": "微秒", "normal_range": "< 300 µs", "warn_threshold": 800, "critical_threshold": 3000, "category": "元数据延迟", "level": "cluster", "promql_template": 'VfsxLinkAvgLatency{region="$region", InstanceType=~"$instanceType", InstanceId="$instanceId"}'},
    "VfsxRemoveAvgLatency": {"zh_name": "Remove 平均延迟", "desc": "删除文件请求平均响应时间", "unit": "µs", "unit_zh": "微秒", "normal_range": "< 300 µs", "warn_threshold": 800, "critical_threshold": 3000, "category": "元数据延迟", "level": "cluster", "promql_template": 'VfsxRemoveAvgLatency{region="$region", InstanceType=~"$instanceType", InstanceId="$instanceId"}'},
    "VfsxMkdirAvgLatency": {"zh_name": "Mkdir 平均延迟", "desc": "创建目录请求平均响应时间", "unit": "µs", "unit_zh": "微秒", "normal_range": "< 300 µs", "warn_threshold": 800, "critical_threshold": 3000, "category": "元数据延迟", "level": "cluster", "promql_template": 'VfsxMkdirAvgLatency{region="$region", InstanceType=~"$instanceType", InstanceId="$instanceId"}'},
    "VfsxRmdirAvgLatency": {"zh_name": "Rmdir 平均延迟", "desc": "删除目录请求平均响应时间", "unit": "µs", "unit_zh": "微秒", "normal_range": "< 300 µs", "warn_threshold": 800, "critical_threshold": 3000, "category": "元数据延迟", "level": "cluster", "promql_template": 'VfsxRmdirAvgLatency{region="$region", InstanceType=~"$instanceType", InstanceId="$instanceId"}'},
    "VfsxSymlinkAvgLatency": {"zh_name": "Symlink 平均延迟", "desc": "创建软链接请求平均响应时间", "unit": "µs", "unit_zh": "微秒", "normal_range": "< 300 µs", "warn_threshold": 800, "critical_threshold": 3000, "category": "元数据延迟", "level": "cluster", "promql_template": 'VfsxSymlinkAvgLatency{region="$region", InstanceType=~"$instanceType", InstanceId="$instanceId"}'},
    "VfsxReadlinkAvgLatency": {"zh_name": "Readlink 平均延迟", "desc": "读取软链接请求平均响应时间", "unit": "µs", "unit_zh": "微秒", "normal_range": "< 200 µs", "warn_threshold": 500, "critical_threshold": 2000, "category": "元数据延迟", "level": "cluster", "promql_template": 'VfsxReadlinkAvgLatency{region="$region", InstanceType=~"$instanceType", InstanceId="$instanceId"}'},
    "VfsxReaddirAvgLatency": {"zh_name": "Readdir 平均延迟", "desc": "读取目录内容请求平均响应时间", "unit": "µs", "unit_zh": "微秒", "normal_range": "< 500 µs", "warn_threshold": 1000, "critical_threshold": 5000, "category": "元数据延迟", "level": "cluster", "promql_template": 'VfsxReaddirAvgLatency{region="$region", InstanceType=~"$instanceType", InstanceId="$instanceId"}'},
    "VfsxRenameAvgLatency": {"zh_name": "Rename 平均延迟", "desc": "重命名请求平均响应时间", "unit": "µs", "unit_zh": "微秒", "normal_range": "< 500 µs", "warn_threshold": 1000, "critical_threshold": 5000, "category": "元数据延迟", "level": "cluster", "promql_template": 'VfsxRenameAvgLatency{region="$region", InstanceType=~"$instanceType", InstanceId="$instanceId"}'},
    "VfsxStatfsAvgLatency": {"zh_name": "Statfs 平均延迟", "desc": "文件系统状态查询平均响应时间", "unit": "µs", "unit_zh": "微秒", "normal_range": "< 200 µs", "warn_threshold": 500, "critical_threshold": 2000, "category": "元数据延迟", "level": "cluster", "promql_template": 'VfsxStatfsAvgLatency{region="$region", InstanceType=~"$instanceType", InstanceId="$instanceId"}'},
}

# Client 级别指标前缀（自动生成配置）
CLIENT_METRIC_PREFIXES = [
    "FisReadThroughput", "FisWriteThroughput",
    "FisReadQps", "FisWriteQps",
    "VfsxReadAvgLatency", "VfsxWriteAvgLatency",
    "VfsxLookupQps", "VfsxGetattrQps", "VfsxSetattrQps", "VfsxLinkQps",
    "VfsxRemoveQps", "VfsxMkdirQps", "VfsxRmdirQps", "VfsxSymlinkQps",
    "VfsxReadlinkQps", "VfsxReaddirQps", "VfsxRenameQps", "VfsxStatfsQps",
    "VfsxLookupAvgLatency", "VfsxGetattrAvgLatency", "VfsxSetattrAvgLatency",
    "VfsxLinkAvgLatency", "VfsxRemoveAvgLatency", "VfsxMkdirAvgLatency",
    "VfsxRmdirAvgLatency", "VfsxSymlinkAvgLatency", "VfsxReadlinkAvgLatency",
    "VfsxReaddirAvgLatency", "VfsxRenameAvgLatency", "VfsxStatfsAvgLatency",
]

# 为 Client 指标自动生成配置
for prefix in CLIENT_METRIC_PREFIXES:
    cluster_config = METRIC_CONFIG.get(prefix, {})
    client_key = f"Client{prefix}"
    
    # Client 级别 PromQL 模板（从 Dashboard 提取）
    if "AvgLatency" in prefix:
        promql_template = f'Client{prefix}{{region="$region", InstanceType=~"$instanceType", InstanceId="$instanceId", ClientId=~"$client"}}'
    else:
        promql_template = f'Client{prefix}{{region="$region", InstanceId="$instanceId", ClientId=~"$client"}}'
    
    METRIC_CONFIG[client_key] = {
        **cluster_config,
        "zh_name": f"客户端-{cluster_config.get('zh_name', prefix)}",
        "desc": f"客户端维度的{cluster_config.get('desc', '')}",
        "level": "client",
        "promql_template": promql_template
    }


# ================= 工具函数 =================

def format_bytes(value):
    """格式化字节值为人类可读格式"""
    if value is None:
        return "N/A"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB']:
        if abs(value) < 1024.0:
            return f"{value:,.2f} {unit}"
        value /= 1024.0
    return f"{value:,.2f} EB"

def format_latency(value):
    """格式化延迟值"""
    if value is None:
        return "N/A"
    if value < 1000:
        return f"{value:.2f} µs"
    elif value < 1000000:
        return f"{value/1000:.2f} ms"
    else:
        return f"{value/1000000:.2f} s"

def format_qps(value):
    """格式化 QPS 值"""
    if value is None:
        return "N/A"
    if value >= 1000000:
        return f"{value/1000000:.2f} M"
    elif value >= 1000:
        return f"{value/1000:.2f} K"
    return f"{value:.0f}"

def format_value(metric_name, value):
    """根据指标类型格式化值"""
    config = METRIC_CONFIG.get(metric_name, {})
    unit = config.get("unit", "")
    
    if unit == "bytes":
        return format_bytes(value)
    elif unit == "percentunit":
        return f"{value*100:.2f}%"
    elif unit in ["binBps"]:
        return format_bytes(value) + "/s"
    elif unit in ["iops", "ops"]:
        return format_qps(value) + "/s"
    elif unit == "µs":
        return format_latency(value)
    return f"{value:.2f}"

def get_timestamp(time_str):
    """时间字符串转时间戳"""
    if isinstance(time_str, (int, float)):
        return int(time_str)
    dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
    return int(dt.timestamp())

def query_prometheus(promql, start_ts, end_ts, step="5m"):
    """执行 PromQL 查询"""
    try:
        resp = requests.get(
            PROM_QUERY_URL,
            headers=HEADERS,
            params={
                "query": promql,
                "start": start_ts,
                "end": end_ts,
                "step": step,
                "match[]": promql
            },
            timeout=60,
            verify=False
        )
        
        if resp.status_code == 200:
            data = resp.json()
            if data.get("status") == "success":
                return data.get("data", {}).get("result", [])
        return []
    except Exception as e:
        print(f"❌ 查询异常：{e}")
        return []

def get_label_values(label_name, match_query):
    """获取标签值列表"""
    try:
        resp = requests.get(
            f"{PROM_LABELS_URL}/{label_name}/values",
            headers=HEADERS,
            params={"match[]": match_query},
            timeout=30,
            verify=False
        )
        if resp.status_code == 200:
            return resp.json().get("data", [])
        return []
    except:
        return []

def flatten_results(results, metric_name, period_label=""):
    """展平查询结果为列表"""
    rows = []
    for series in results:
        labels = series.get("metric", {})
        label_str = ";".join([f"{k}={v}" for k, v in labels.items()])
        for ts, val in series.get("values", []):
            if val and val != "NaN":
                try:
                    rows.append({
                        "period": period_label,
                        "metric": metric_name,
                        "timestamp": datetime.fromtimestamp(int(float(ts))).strftime("%Y-%m-%d %H:%M:%S"),
                        "timestamp_ts": int(float(ts)),
                        "value": float(val),
                        "labels": label_str,
                        "config": METRIC_CONFIG.get(metric_name, {})
                    })
                except (ValueError, TypeError):
                    continue
    return rows

def calculate_stats(rows):
    """计算统计指标"""
    if not rows:
        return {}
    values = [r["value"] for r in rows]
    sorted_values = sorted(values)
    p95_idx = int(len(sorted_values) * 0.95)
    return {
        "count": len(values),
        "avg": sum(values) / len(values),
        "min": min(values),
        "max": max(values),
        "p95": sorted_values[p95_idx] if len(values) >= 20 else max(values)
    }


# ================= 交互界面 =================

def print_header(title):
    """打印分区标题"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print('='*70)

def show_metric_info(metric_key):
    """显示指标详细信息"""
    config = METRIC_CONFIG.get(metric_key, {})
    print(f"\n📊 {config.get('zh_name', metric_key)}")
    print(f"   说明：{config.get('desc', '无')}")
    print(f"   单位：{config.get('unit_zh', config.get('unit', 'N/A'))}")
    print(f"   正常范围：{config.get('normal_range', 'N/A')}")
    if config.get('warn_threshold'):
        print(f"   ⚠️  警告阈值：{config.get('warn_threshold')}")
    if config.get('critical_threshold'):
        print(f"   🔴 严重阈值：{config.get('critical_threshold')}")
    print(f"   级别：{'🌐 集群' if config.get('level')=='cluster' else '👤 客户端'}")

def select_time_range():
    """
    交互式选择时间范围
    ✅ 已修复：对比模式昨天时间计算错误
    """
    print("\n🕐 选择查询时间范围:")
    print("  1) 最近 1 小时")
    print("  2) 最近 4 小时")
    print("  3) 最近 24 小时")
    print("  4) 自定义历史时间")
    print("  5) 对比模式 (今天 vs 昨天同期)")
    print("  0) 返回主菜单")
    
    choice = input("\n请输入选项 (0-5): ").strip()
    
    end_ts = int(time.time())
    
    if choice == "1":
        start_ts = end_ts - 3600
        return [("当前", start_ts, end_ts)]
    elif choice == "2":
        start_ts = end_ts - 4 * 3600
        return [("当前", start_ts, end_ts)]
    elif choice == "3":
        start_ts = end_ts - 24 * 3600
        return [("当前", start_ts, end_ts)]
    elif choice == "4":
        print("\n📅 输入要查询的历史时间段:")
        days = input("   多少天前开始 (默认 7): ").strip() or "7"
        hours = input("   查询时长 (小时，默认 4): ").strip() or "4"
        try:
            start_ts = end_ts - int(days) * 24 * 3600
            end_ts_custom = start_ts + int(hours) * 3600
            return [("历史", start_ts, end_ts_custom)]
        except:
            print("❌ 输入格式错误")
            return []
    elif choice == "5":
        # ✅ 对比模式：今天 vs 昨天同期（已修复）
        end_today = int(time.time())
        start_today = end_today - 4 * 3600  # 最近 4 小时
        
        # 🔑 关键修复：昨天 = 今天时间 - 24 小时（不是减去当前时间）
        end_yesterday = end_today - 24 * 3600      # 昨天同一结束时间
        start_yesterday = start_today - 24 * 3600  # 昨天同一开始时间
        
        print(f"\n📅 对比时间范围:")
        print(f"   今天：{datetime.fromtimestamp(start_today)} ~ {datetime.fromtimestamp(end_today)}")
        print(f"   昨天：{datetime.fromtimestamp(start_yesterday)} ~ {datetime.fromtimestamp(end_yesterday)}")
        
        return [
            ("today", start_today, end_today), 
            ("yesterday", start_yesterday, end_yesterday)
        ]
    else:
        return []

def select_metrics(level_filter=None):
    """交互式选择指标"""
    categories = defaultdict(list)
    for key, config in METRIC_CONFIG.items():
        if level_filter and config.get("level") != level_filter:
            continue
        categories[config.get("category", "其他")].append((key, config))
    
    print(f"\n📋 可选指标 ({'集群' if level_filter=='cluster' else '客户端' if level_filter=='client' else '全部'}):")
    
    selected = []
    for i, (category, metrics) in enumerate(sorted(categories.items()), 1):
        print(f"\n  [{i}] {category}")
        for key, config in metrics[:8]:  # 每类最多显示 8 个
            print(f"      • {config.get('zh_name', key)}")
    
    print(f"\n  [0] 全选当前类别  [99] 返回")
    choice = input("\n输入类别编号选择，或输入指标中文名搜索：").strip()
    
    if choice == "99":
        return []
    elif choice == "0":
        # 全选
        for metrics in categories.values():
            selected.extend([k for k, _ in metrics])
        return selected
    elif choice.isdigit() and int(choice) in range(1, len(categories)+1):
        # 选择某个类别
        cat_name = list(categories.keys())[int(choice)-1]
        return [k for k, _ in categories[cat_name]]
    else:
        # 搜索指标
        matched = [(k, c) for k, c in METRIC_CONFIG.items() 
                  if choice.lower() in k.lower() or choice in c.get('zh_name', '')]
        if matched:
            print(f"\n✅ 找到 {len(matched)} 个匹配指标:")
            for i, (k, c) in enumerate(matched[:10], 1):
                print(f"  {i}. {c.get('zh_name')} ({k})")
            sub_choice = input("输入序号选择 (回车全选): ").strip()
            if sub_choice and sub_choice.isdigit() and int(sub_choice) <= len(matched):
                return [matched[int(sub_choice)-1][0]]
            return [k for k, _ in matched]
    
    return selected

def display_results(rows, show_detail=False, compare_mode=False):
    """
    展示查询结果
    ✅ 已添加：对比模式显示 today vs yesterday
    """
    if not rows:
        print("⚠️  无数据返回")
        return
    
    # 按指标分组统计
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["metric"]].append(row)
    
    print(f"\n📊 查询结果 ({len(rows)} 条数据点):")
    print(f"{'指标名称':<25} | {'数据点':>8} | {'平均值':>15} | {'峰值':>15} | {'状态'}")
    print("-"*85)
    
    for metric, metric_rows in grouped.items():
        config = METRIC_CONFIG.get(metric, {})
        stats = calculate_stats(metric_rows)
        
        # 格式化显示
        avg_val = format_value(metric, stats["avg"])
        max_val = format_value(metric, stats["max"])
        
        # 状态判断
        status = "✅ 正常"
        if config.get("critical_threshold"):
            threshold = config["critical_threshold"]
            if "µs" in config.get("unit", "") and stats["max"] > threshold:
                status = "🔴 严重"
            elif "%" in config.get("unit", "") and stats["avg"] > threshold:
                status = "🔴 严重"
        elif config.get("warn_threshold"):
            threshold = config["warn_threshold"]
            if "µs" in config.get("unit", "") and stats["max"] > threshold:
                status = "⚠️  警告"
        
        zh_name = config.get("zh_name", metric)
        print(f"{zh_name:<25} | {stats['count']:>8} | {avg_val:>15} | {max_val:>15} | {status}")
    
    # ✅ 对比模式：显示同比变化
    if compare_mode:
        print(f"\n📈 同比对比分析 (today vs yesterday):")
        print(f"{'指标名称':<25} | {'今天平均':>15} | {'昨天平均':>15} | {'变化':>10} | {'状态'}")
        print("-"*90)
        
        for metric, metric_rows in grouped.items():
            config = METRIC_CONFIG.get(metric, {})
            
            # 分离 today/yesterday 数据
            today_vals = [r["value"] for r in metric_rows if r.get("period") == "today"]
            yesterday_vals = [r["value"] for r in metric_rows if r.get("period") == "yesterday"]
            
            if today_vals and yesterday_vals:
                today_avg = sum(today_vals) / len(today_vals)
                yesterday_avg = sum(yesterday_vals) / len(yesterday_vals)
                
                # 避免除零
                if yesterday_avg != 0:
                    change_pct = (today_avg - yesterday_avg) / abs(yesterday_avg) * 100
                else:
                    change_pct = 0
                
                # 状态判断
                if abs(change_pct) > 50:
                    status = "🔴 剧变" if change_pct < 0 else "🟡 上升"
                elif abs(change_pct) > 20:
                    status = "⚠️  波动"
                else:
                    status = "✅ 稳定"
                
                zh_name = config.get("zh_name", metric)
                print(f"{zh_name:<25} | {format_value(metric, today_avg):>15} | {format_value(metric, yesterday_avg):>15} | {change_pct:+.1f}% | {status}")
    
    if show_detail and len(grouped) == 1:
        # 显示单个指标的详细时间序列
        metric = list(grouped.keys())[0]
        print(f"\n📈 {METRIC_CONFIG.get(metric, {}).get('zh_name', metric)} 详细数据 (前 20 点):")
        print(f"{'时间':<20} | {'数值':>20} | {'标签'}")
        print("-"*70)
        for row in sorted(grouped[metric], key=lambda x: x["timestamp_ts"])[:20]:
            print(f"{row['timestamp']:<20} | {format_value(metric, row['value']):>20} | {row['labels'][:30]}")

def export_csv(rows, filename=None):
    """导出 CSV 文件"""
    if not rows:
        print("⚠️  无数据可导出")
        return None
    
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        filename = f"pfs_export_{timestamp}.csv"
    
    # 准备导出字段
    export_rows = []
    for row in rows:
        config = row.get("config", {})
        export_rows.append({
            "时间": row["timestamp"],
            "指标英文名": row["metric"],
            "指标中文名": config.get("zh_name", row["metric"]),
            "指标说明": config.get("desc", ""),
            "数值": row["value"],
            "单位": config.get("unit_zh", config.get("unit", "")),
            "正常范围": config.get("normal_range", ""),
            "标签": row["labels"],
            "时间段": row.get("period", "")
        })
    
    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=export_rows[0].keys())
        writer.writeheader()
        writer.writerows(export_rows)
    
    print(f"💾 已导出：{filename} ({len(export_rows)} 行)")
    return filename

def main_menu():
    """主菜单"""
    while True:
        print_header("🗄️  PFS 监控数据交互式查询工具")
        print(f"📍 Prometheus: {PROM_INSTANCE_ID}")
        print(f"📍 PFS 实例：{DEFAULT_INSTANCE_ID}")
        print(f"📍 区域：{DEFAULT_REGION}")
        
        print("\n📋 主菜单:")
        print("  1) 🔍 查询指标数据")
        print("  2) 📊 查看指标说明")
        print("  3) 📥 导出历史数据")
        print("  4) ⚙️  修改查询配置")
        print("  5) ℹ️  查看帮助")
        print("  0) 🚪 退出")
        
        choice = input("\n请输入选项 (0-5): ").strip()
        
        if choice == "0":
            print("👋 再见!")
            break
        elif choice == "1":
            query_flow()
        elif choice == "2":
            show_metric_catalog()
        elif choice == "3":
            export_flow()
        elif choice == "4":
            config_flow()
        elif choice == "5":
            show_help()
        else:
            print("❌ 无效选项")
            time.sleep(1)

def query_flow():
    """查询流程"""
    print_header("🔍 指标查询")
    
    # 1. 选择指标级别
    print("\n📐 选择指标级别:")
    print("  1) 🌐 集群级别 (整体性能)")
    print("  2) 👤 客户端级别 (单客户端性能)")
    print("  3) ✨ 全部指标")
    level_choice = input("请输入 (1-3, 默认 3): ").strip() or "3"
    
    level_filter = None
    if level_choice == "1":
        level_filter = "cluster"
    elif level_choice == "2":
        level_filter = "client"
    
    # 2. 选择指标
    metrics = select_metrics(level_filter)
    if not metrics:
        print("⚠️  未选择指标")
        return
    
    # 3. 选择时间范围
    time_ranges = select_time_range()
    if not time_ranges:
        return
    
    # 4. 执行查询
    all_rows = []
    for period_label, start_ts, end_ts in time_ranges:
        print(f"\n🔄 查询 [{period_label}]: {datetime.fromtimestamp(start_ts)} ~ {datetime.fromtimestamp(end_ts)}")
        for metric in metrics:
            config = METRIC_CONFIG.get(metric, {})
            
            # 构建 PromQL
            if config.get("level") == "client":
                # 客户端指标需要 ClientId
                client_ids = get_label_values(
                    "ClientId",
                    f'ClientFisReadThroughput{{region="{DEFAULT_REGION}", InstanceId="{DEFAULT_INSTANCE_ID}"}}'
                )
                if not client_ids:
                    print(f"   ⚠️  {metric}: 无可用客户端")
                    continue
                # 查询前 3 个客户端
                for cid in client_ids[:3]:
                    promql = config.get("promql_template", f'{metric}{{region="{DEFAULT_REGION}", InstanceId="{DEFAULT_INSTANCE_ID}", ClientId="{cid}"}}')
                    promql = promql.replace("$region", DEFAULT_REGION).replace("$instanceId", DEFAULT_INSTANCE_ID).replace("$client", cid).replace("$instanceType", DEFAULT_INSTANCE_TYPE)
                    results = query_prometheus(promql, start_ts, end_ts, DEFAULT_STEP)
                    all_rows.extend(flatten_results(results, metric, period_label))
            else:
                # 集群指标
                promql = config.get("promql_template", f'{metric}{{region="{DEFAULT_REGION}", InstanceId="{DEFAULT_INSTANCE_ID}"}}')
                promql = promql.replace("$region", DEFAULT_REGION).replace("$instanceId", DEFAULT_INSTANCE_ID).replace("$instanceType", DEFAULT_INSTANCE_TYPE)
                results = query_prometheus(promql, start_ts, end_ts, DEFAULT_STEP)
                all_rows.extend(flatten_results(results, metric, period_label))
    
    # 5. 展示结果
    is_compare = len(time_ranges) == 2  # 对比模式有 2 个时间段
    display_results(all_rows, show_detail=True, compare_mode=is_compare)
    
    # 6. 导出选项
    if all_rows:
        export = input("\n📥 是否导出 CSV? (y/n, 默认 n): ").strip().lower()
        if export == "y":
            export_csv(all_rows)

def show_metric_catalog():
    """显示指标目录"""
    print_header("📚 指标说明目录")
    
    categories = defaultdict(list)
    for key, config in METRIC_CONFIG.items():
        categories[config.get("category", "其他")].append((key, config))
    
    for category, metrics in sorted(categories.items()):
        print(f"\n📁 {category}")
        print("-"*60)
        for key, config in metrics:
            show_metric_info(key)
    
    input("\n按回车返回...")

def export_flow():
    """导出流程"""
    print_header("📥 数据导出")
    
    # 简化：导出最近 24 小时所有集群指标
    print("🔄 正在导出最近 24 小时集群级别指标...")
    
    end_ts = int(time.time())
    start_ts = end_ts - 24 * 3600
    
    all_rows = []
    cluster_metrics = [k for k, v in METRIC_CONFIG.items() if v.get("level") == "cluster"]
    
    for metric in cluster_metrics[:10]:  # 限制数量避免超时
        config = METRIC_CONFIG.get(metric, {})
        promql = config.get("promql_template", f'{metric}{{region="{DEFAULT_REGION}", InstanceId="{DEFAULT_INSTANCE_ID}"}}')
        promql = promql.replace("$region", DEFAULT_REGION).replace("$instanceId", DEFAULT_INSTANCE_ID).replace("$instanceType", DEFAULT_INSTANCE_TYPE)
        
        results = query_prometheus(promql, start_ts, end_ts, "15m")
        all_rows.extend(flatten_results(results, metric, "export"))
        print(f"   ✓ {config.get('zh_name', metric)}")
    
    if all_rows:
        filename = export_csv(all_rows)
        print(f"\n✅ 导出完成：{filename}")
    else:
        print("⚠️  无数据可导出")
    
    input("\n按回车返回...")

def config_flow():
    """配置修改流程"""
    print_header("⚙️  查询配置")
    
    global DEFAULT_REGION, DEFAULT_INSTANCE_TYPE, DEFAULT_INSTANCE_ID, DEFAULT_STEP
    
    print(f"\n当前配置:")
    print(f"  Region: {DEFAULT_REGION}")
    print(f"  InstanceType: {DEFAULT_INSTANCE_TYPE}")
    print(f"  InstanceId: {DEFAULT_INSTANCE_ID}")
    print(f"  Step: {DEFAULT_STEP}")
    
    print("\n🔄 修改配置 (回车跳过):")
    
    new_region = input("  Region: ").strip()
    if new_region:
        DEFAULT_REGION = new_region
    
    new_type = input("  InstanceType: ").strip()
    if new_type:
        DEFAULT_INSTANCE_TYPE = new_type
    
    new_id = input("  InstanceId: ").strip()
    if new_id:
        DEFAULT_INSTANCE_ID = new_id
    
    new_step = input("  Step (5m/15m/1h): ").strip()
    if new_step:
        DEFAULT_STEP = new_step
    
    print("\n✅ 配置已更新")
    input("按回车返回...")

def show_help():
    """显示帮助"""
    print_header("❓ 使用帮助")
    print("""
🔍 查询功能:
  • 支持集群/客户端级别指标
  • 支持当前/历史/对比时间范围
  • 结果自动格式化显示 + 状态判断
  • ✅ 对比模式自动计算同比变化百分比

📊 指标说明:
  • 每个指标含中文名、说明、单位、正常范围
  • 自动标记 ⚠️警告 / 🔴严重 状态
  • 基于 Dashboard PFS-ONLINE 所有面板指标

📥 导出功能:
  • 支持 CSV 导出，含完整中文映射
  • 文件可直接用 Excel 打开分析
  • 包含时间段标识 (today/yesterday)

💡 使用技巧:
  1. 先查看"指标说明"了解各指标含义
  2. 对比模式可快速发现性能变化
  3. 导出后建议用 Excel 透视表分析趋势
  4. 客户端指标需要实例有活跃连接

🔧 常见问题:
  Q: 查询返回空数据？
  A: 检查 InstanceId 是否正确，或扩大时间范围
  
  Q: 客户端指标查不到？
  A: 该实例当前可能无客户端活跃连接
  
  Q: 对比模式昨天时间不对？
  A: 已修复，昨天=今天时间-24 小时
  
  Q: 导出文件乱码？
  A: 用 Excel 打开时选择"UTF-8"编码
    """)
    input("\n按回车返回...")


# ================= 入口 =================

if __name__ == "__main__":
    print("🚀 PFS 监控查询工具 启动中...")
    
    # 依赖检查
    try:
        import pandas
        print("✅ pandas 已安装 (支持高级分析)")
    except ImportError:
        print("⚠️  提示：安装 pandas 可启用高级分析：pip install pandas")
    
    # 验证连接
    test_promql = f'FsUsage{{region="{DEFAULT_REGION}", InstanceId="{DEFAULT_INSTANCE_ID}"}}'
    results = query_prometheus(test_promql, int(time.time())-300, int(time.time()))
    if results:
        print("✅ 连接 Prometheus 成功")
    else:
        print("⚠️  连接测试无返回，请检查配置后继续")
        time.sleep(2)
    
    # 启动主菜单
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\n\n👋 用户中断，再见!")
    except Exception as e:
        print(f"\n❌ 程序异常：{e}")
        import traceback
        traceback.print_exc()
