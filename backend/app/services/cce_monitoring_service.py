#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CCE 集群实时监控服务
从 Prometheus 实时查询集群健康指标，纯展示，不写告警记录
复用 APIServer 的 prometheus_runtime 配置（grafana_url / token / instance_id / cluster_ids）
"""
import json
import time
import requests
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.core.logger import logger
from app.models.system_config import SystemConfig


# ---------------------------------------------------------------------------
# 指标定义
# cluster_id 占位使用 {cluster_id}，匹配时使用精确等值 = 避免跨集群混叠
# ---------------------------------------------------------------------------

METRICS: List[Dict[str, Any]] = [
    # ── 基础资源 ────────────────────────────────────────────────────────────
    {
        "key": "node_count",
        "label": "节点总数",
        "category": "basic",
        "promql": 'count(kube_node_info{{clusterID="{cluster_id}"}})',
        "unit": "个",
    },
    {
        "key": "node_ready",
        "label": "Ready 节点数",
        "category": "basic",
        "promql": 'count(kube_node_status_condition{{clusterID="{cluster_id}",condition="Ready",status="true"}} == 1)',
        "unit": "个",
    },
    {
        "key": "pod_count",
        "label": "Pod 总数",
        "category": "basic",
        "promql": 'count(kube_pod_info{{clusterID="{cluster_id}"}})',
        "unit": "个",
    },
    {
        "key": "pod_running",
        "label": "Running Pod 数",
        "category": "basic",
        "promql": 'sum(kube_pod_status_phase{{clusterID="{cluster_id}",phase="Running"}})',
        "unit": "个",
    },
    {
        "key": "pod_pending",
        "label": "Pending Pod 数",
        "category": "basic",
        "promql": 'sum(kube_pod_status_phase{{clusterID="{cluster_id}",phase="Pending"}}) or vector(0)',
        "unit": "个",
    },
    {
        "key": "pod_failed",
        "label": "Failed Pod 数",
        "category": "basic",
        "promql": 'sum(kube_pod_status_phase{{clusterID="{cluster_id}",phase="Failed"}}) or vector(0)',
        "unit": "个",
    },
    # ── 资源使用率 ──────────────────────────────────────────────────────────
    {
        "key": "cpu_usage_pct",
        "label": "CPU 实际使用率",
        "category": "usage",
        "promql": 'avg(1 - rate(node_cpu_seconds_total{{clusterID="{cluster_id}",mode="idle"}}[5m])) * 100',
        "unit": "%",
    },
    {
        "key": "memory_usage_pct",
        "label": "内存实际使用率",
        "category": "usage",
        "promql": 'avg((1 - node_memory_MemAvailable_bytes{{clusterID="{cluster_id}"}} / node_memory_MemTotal_bytes{{clusterID="{cluster_id}"}}) * 100)',
        "unit": "%",
    },
    {
        "key": "cpu_request_pct",
        "label": "CPU Request 占分配比",
        "category": "usage",
        "promql": 'sum(kube_pod_container_resource_requests{{clusterID="{cluster_id}",resource="cpu",unit="core"}}) / sum(kube_node_status_allocatable{{clusterID="{cluster_id}",resource="cpu"}}) * 100',
        "unit": "%",
    },
    {
        "key": "memory_request_pct",
        "label": "内存 Request 占分配比",
        "category": "usage",
        "promql": 'sum(kube_pod_container_resource_requests{{clusterID="{cluster_id}",resource="memory",unit="byte"}}) / sum(kube_node_status_allocatable{{clusterID="{cluster_id}",resource="memory"}}) * 100',
        "unit": "%",
    },
    {
        "key": "disk_usage_pct",
        "label": "节点磁盘平均使用率",
        "category": "usage",
        "promql": 'avg((1 - node_filesystem_avail_bytes{{clusterID="{cluster_id}",fstype!="tmpfs"}} / node_filesystem_size_bytes{{clusterID="{cluster_id}",fstype!="tmpfs"}}) * 100)',
        "unit": "%",
    },
    # ── 节点状态 ────────────────────────────────────────────────────────────
    {
        "key": "node_disk_pressure",
        "label": "DiskPressure 节点数",
        "category": "node_condition",
        "promql": 'count(kube_node_status_condition{{clusterID="{cluster_id}",condition="DiskPressure",status="true"}} == 1) or vector(0)',
        "unit": "个",
    },
    {
        "key": "node_memory_pressure",
        "label": "MemoryPressure 节点数",
        "category": "node_condition",
        "promql": 'count(kube_node_status_condition{{clusterID="{cluster_id}",condition="MemoryPressure",status="true"}} == 1) or vector(0)',
        "unit": "个",
    },
    {
        "key": "node_pid_pressure",
        "label": "PIDPressure 节点数",
        "category": "node_condition",
        "promql": 'count(kube_node_status_condition{{clusterID="{cluster_id}",condition="PIDPressure",status="true"}} == 1) or vector(0)',
        "unit": "个",
    },
    {
        "key": "node_network_unavailable",
        "label": "NetworkUnavailable 节点数",
        "category": "node_condition",
        "promql": 'count(kube_node_status_condition{{clusterID="{cluster_id}",condition="NetworkUnavailable",status="true"}} == 1) or vector(0)',
        "unit": "个",
    },
    # ── 集群容量 ────────────────────────────────────────────────────────────
    {
        "key": "total_cpu_cores",
        "label": "集群可分配 CPU 总核数",
        "category": "capacity",
        "promql": 'sum(kube_node_status_allocatable{{clusterID="{cluster_id}",resource="cpu"}})',
        "unit": "核",
    },
    {
        "key": "total_memory_gb",
        "label": "集群可分配内存总量",
        "category": "capacity",
        "promql": 'sum(kube_node_status_allocatable{{clusterID="{cluster_id}",resource="memory"}}) / 1024 / 1024 / 1024',
        "unit": "GB",
    },
    # ── 网络带宽 ────────────────────────────────────────────────────────────
    {
        "key": "net_receive_mbps",
        "label": "集群网络入流量",
        "category": "network",
        "promql": 'sum(rate(node_network_receive_bytes_total{{clusterID="{cluster_id}",device!~"lo|veth.*|docker.*|flannel.*|cni.*"}}[5m])) / 1024 / 1024',
        "unit": "MB/s",
    },
    {
        "key": "net_transmit_mbps",
        "label": "集群网络出流量",
        "category": "network",
        "promql": 'sum(rate(node_network_transmit_bytes_total{{clusterID="{cluster_id}",device!~"lo|veth.*|docker.*|flannel.*|cni.*"}}[5m])) / 1024 / 1024',
        "unit": "MB/s",
    },
    # ── 磁盘 I/O ────────────────────────────────────────────────────────────
    {
        "key": "disk_read_mbps",
        "label": "集群磁盘读速率",
        "category": "disk_io",
        "promql": 'sum(rate(node_disk_read_bytes_total{{clusterID="{cluster_id}"}}[5m])) / 1024 / 1024',
        "unit": "MB/s",
    },
    {
        "key": "disk_write_mbps",
        "label": "集群磁盘写速率",
        "category": "disk_io",
        "promql": 'sum(rate(node_disk_written_bytes_total{{clusterID="{cluster_id}"}}[5m])) / 1024 / 1024',
        "unit": "MB/s",
    },
    # ── 系统负载 ────────────────────────────────────────────────────────────
    {
        "key": "load1",
        "label": "节点平均负载 (1m)",
        "category": "load",
        "promql": 'avg(node_load1{{clusterID="{cluster_id}"}})',
        "unit": "",
    },
    {
        "key": "load5",
        "label": "节点平均负载 (5m)",
        "category": "load",
        "promql": 'avg(node_load5{{clusterID="{cluster_id}"}})',
        "unit": "",
    },
    # ── 集群组件健康 ────────────────────────────────────────────────────────
    {
        "key": "etcd_has_leader",
        "label": "etcd 有 Leader",
        "category": "components",
        "promql": 'min(etcd_server_has_leader{{clusterID="{cluster_id}"}})',
        "unit": "",
    },
    {
        "key": "etcd_leader_changes",
        "label": "etcd Leader 变更次数 (1h)",
        "category": "components",
        "promql": 'sum(increase(etcd_server_leader_changes_seen_total{{clusterID="{cluster_id}"}}[1h]))',
        "unit": "次",
    },
    {
        "key": "etcd_db_size_mb",
        "label": "etcd 数据库大小",
        "category": "components",
        "promql": 'max(etcd_mvcc_db_total_size_in_bytes{{clusterID="{cluster_id}"}}) / 1024 / 1024',
        "unit": "MB",
    },
    {
        "key": "coredns_qps",
        "label": "CoreDNS QPS",
        "category": "components",
        "promql": 'sum(rate(coredns_dns_requests_total{{clusterID="{cluster_id}"}}[5m]))',
        "unit": "qps",
    },
    {
        "key": "pod_restarts_1h",
        "label": "容器重启次数 (1h)",
        "category": "components",
        "promql": 'sum(increase(kube_pod_container_status_restarts_total{{clusterID="{cluster_id}"}}[1h]))',
        "unit": "次",
    },
    {
        "key": "pending_pods_unschedulable",
        "label": "不可调度 Pending Pod",
        "category": "components",
        "promql": 'sum(scheduler_pending_pods{{clusterID="{cluster_id}",queue="unschedulable"}}) or vector(0)',
        "unit": "个",
    },
    {
        "key": "tcp_connections",
        "label": "TCP 连接数",
        "category": "components",
        "promql": 'sum(node_sockstat_TCP_inuse{{clusterID="{cluster_id}"}})',
        "unit": "条",
    },
    # ── APIServer 健康 ──────────────────────────────────────────────────────
    {
        "key": "api_qps",
        "label": "APIServer QPS",
        "category": "apiserver",
        "promql": 'sum(rate(apiserver_request_total{{clusterID="{cluster_id}",verb!~"WATCH|CONNECT"}}[5m]))',
        "unit": "qps",
    },
    {
        "key": "read_success_rate",
        "label": "读请求成功率",
        "category": "apiserver",
        "promql": 'sum(rate(apiserver_request_total{{clusterID="{cluster_id}",verb=~"GET|LIST",code=~"2..|3.."}}[5m])) / sum(rate(apiserver_request_total{{clusterID="{cluster_id}",verb=~"GET|LIST"}}[5m])) * 100',
        "unit": "%",
    },
    {
        "key": "write_success_rate",
        "label": "写请求成功率",
        "category": "apiserver",
        "promql": 'sum(rate(apiserver_request_total{{clusterID="{cluster_id}",verb=~"POST|PUT|PATCH|DELETE",code=~"2..|3.."}}[5m])) / sum(rate(apiserver_request_total{{clusterID="{cluster_id}",verb=~"POST|PUT|PATCH|DELETE"}}[5m])) * 100',
        "unit": "%",
    },
    {
        "key": "get_p50_latency",
        "label": "GET 请求 P50 延迟",
        "category": "apiserver",
        "promql": 'histogram_quantile(0.5, sum(rate(apiserver_request_duration_seconds_bucket{{clusterID="{cluster_id}",verb="GET"}}[5m])) by (le))',
        "unit": "s",
    },
    {
        "key": "write_p50_latency",
        "label": "写请求 P50 延迟",
        "category": "apiserver",
        "promql": 'histogram_quantile(0.5, sum(rate(apiserver_request_duration_seconds_bucket{{clusterID="{cluster_id}",verb=~"POST|PUT|PATCH|DELETE"}}[5m])) by (le))',
        "unit": "s",
    },
]

CATEGORY_LABELS = {
    "basic": "基础资源",
    "capacity": "集群容量",
    "usage": "资源使用率",
    "node_condition": "节点状态",
    "network": "网络带宽",
    "disk_io": "磁盘 I/O",
    "load": "系统负载",
    "components": "组件健康",
    "apiserver": "APIServer 告警统计",
}

# 用于趋势图的 range query 指标（key → promql_template）
CHART_METRICS: Dict[str, Dict[str, str]] = {
    "cpu_usage_pct": {
        "label": "CPU 使用率",
        "promql": 'avg(1 - rate(node_cpu_seconds_total{{clusterID="{cluster_id}",mode="idle"}}[5m])) * 100',
        "unit": "%",
    },
    "memory_usage_pct": {
        "label": "内存使用率",
        "promql": 'avg((1 - node_memory_MemAvailable_bytes{{clusterID="{cluster_id}"}} / node_memory_MemTotal_bytes{{clusterID="{cluster_id}"}}) * 100)',
        "unit": "%",
    },
    "api_qps": {
        "label": "APIServer QPS",
        "promql": 'sum(rate(apiserver_request_total{{clusterID="{cluster_id}",verb!~"WATCH|CONNECT"}}[5m]))',
        "unit": "qps",
    },
    "read_success_rate": {
        "label": "读请求成功率",
        "promql": 'sum(rate(apiserver_request_total{{clusterID="{cluster_id}",verb=~"GET|LIST",code=~"2..|3.."}}[5m])) / sum(rate(apiserver_request_total{{clusterID="{cluster_id}",verb=~"GET|LIST"}}[5m])) * 100',
        "unit": "%",
    },
    "write_success_rate": {
        "label": "写请求成功率",
        "promql": 'sum(rate(apiserver_request_total{{clusterID="{cluster_id}",verb=~"POST|PUT|PATCH|DELETE",code=~"2..|3.."}}[5m])) / sum(rate(apiserver_request_total{{clusterID="{cluster_id}",verb=~"POST|PUT|PATCH|DELETE"}}[5m])) * 100',
        "unit": "%",
    },
    "pod_running": {
        "label": "Running Pod 数",
        "promql": 'sum(kube_pod_status_phase{{clusterID="{cluster_id}",phase="Running"}})',
        "unit": "个",
    },
    "net_receive_mbps": {
        "label": "网络入流量",
        "promql": 'sum(rate(node_network_receive_bytes_total{{clusterID="{cluster_id}",device!~"lo|veth.*|docker.*|flannel.*|cni.*"}}[5m])) / 1024 / 1024',
        "unit": "MB/s",
    },
    "net_transmit_mbps": {
        "label": "网络出流量",
        "promql": 'sum(rate(node_network_transmit_bytes_total{{clusterID="{cluster_id}",device!~"lo|veth.*|docker.*|flannel.*|cni.*"}}[5m])) / 1024 / 1024',
        "unit": "MB/s",
    },
    "disk_read_mbps": {
        "label": "磁盘读速率",
        "promql": 'sum(rate(node_disk_read_bytes_total{{clusterID="{cluster_id}"}}[5m])) / 1024 / 1024',
        "unit": "MB/s",
    },
    "disk_write_mbps": {
        "label": "磁盘写速率",
        "promql": 'sum(rate(node_disk_written_bytes_total{{clusterID="{cluster_id}"}}[5m])) / 1024 / 1024',
        "unit": "MB/s",
    },
    "load1": {
        "label": "系统负载 (1m)",
        "promql": 'avg(node_load1{{clusterID="{cluster_id}"}})',
        "unit": "",
    },
    "disk_usage_pct": {
        "label": "磁盘使用率",
        "promql": 'avg((1 - node_filesystem_avail_bytes{{clusterID="{cluster_id}",fstype!="tmpfs"}} / node_filesystem_size_bytes{{clusterID="{cluster_id}",fstype!="tmpfs"}}) * 100)',
        "unit": "%",
    },
}


# ---------------------------------------------------------------------------
# 服务类
# ---------------------------------------------------------------------------

class CCEMonitoringService:
    def __init__(self, db: Session):
        self.db = db

    def _load_config(self) -> Dict[str, Any]:
        """从 prometheus_runtime SystemConfig 读取连接参数（与 APIServer 共用）"""
        runtime_record = self.db.query(SystemConfig).filter(
            SystemConfig.module == "prometheus_runtime",
            SystemConfig.config_key == "main",
        ).first()
        runtime_config = {}
        if runtime_record and runtime_record.config_value:
            runtime_config = json.loads(runtime_record.config_value)

        cluster_ids = runtime_config.get("cluster_ids") or ""
        if isinstance(cluster_ids, str):
            cluster_ids = [item.strip() for item in cluster_ids.split(",") if item.strip()]

        return {
            "grafana_url": runtime_config.get("grafana_url", ""),
            "token": runtime_config.get("token", ""),
            "instance_id": runtime_config.get("instance_id", ""),
            "cluster_ids": cluster_ids,
        }

    def get_config(self) -> Dict[str, Any]:
        config = self._load_config()
        return {
            "grafana_url": config["grafana_url"],
            "instance_id": config["instance_id"],
            "cluster_ids": config["cluster_ids"],
            "has_token": bool(config["token"]),
        }

    def _headers(self, config: Dict[str, Any]) -> Dict[str, str]:
        token = config["token"]
        return {
            "Authorization": token if str(token).startswith("Bearer ") else f"Bearer {token}",
            "InstanceId": config["instance_id"],
        }

    def _query_instant(self, promql: str, config: Dict[str, Any]) -> Optional[float]:
        url = f"{config['grafana_url'].rstrip('/')}/api/v1/query"
        try:
            resp = requests.get(
                url, headers=self._headers(config),
                params={"query": promql}, timeout=30, verify=False
            )
            resp.raise_for_status()
            data = resp.json()
            results = data.get("data", {}).get("result", [])
            if not results:
                return None
            value = results[0].get("value", [None, None])[1]
            return float(value) if value is not None else None
        except Exception as exc:
            logger.warning(f"CCE 即时查询失败: {exc}")
            return None

    def _query_range(self, promql: str, config: Dict[str, Any], start: int, end: int, step: str) -> List[Dict]:
        """返回 [{timestamp, value}, ...] 列表"""
        url = f"{config['grafana_url'].rstrip('/')}/api/v1/query_range"
        try:
            resp = requests.get(
                url, headers=self._headers(config),
                params={"query": promql, "start": start, "end": end, "step": step},
                timeout=60, verify=False
            )
            resp.raise_for_status()
            data = resp.json()
            results = data.get("data", {}).get("result", [])
            if not results:
                return []
            # 取第一条 series 的 values
            values = results[0].get("values", [])
            return [{"timestamp": int(v[0]) * 1000, "value": round(float(v[1]), 4)} for v in values if v[1] is not None]
        except Exception as exc:
            logger.warning(f"CCE range 查询失败: {exc}")
            return []

    def query_cluster(self, cluster_id: str) -> Dict[str, Any]:
        """查询单个集群的全部即时指标，返回按 category 分组的结果"""
        config = self._load_config()
        if not config["grafana_url"]:
            return {"error": "Prometheus 未配置，请在系统配置 → Prometheus 配置中填写"}

        results: Dict[str, Any] = {"cluster_id": cluster_id, "categories": {}}

        for metric in METRICS:
            promql = metric["promql"].format(cluster_id=cluster_id)
            value = self._query_instant(promql, config)

            category = metric["category"]
            if category not in results["categories"]:
                results["categories"][category] = {
                    "label": CATEGORY_LABELS.get(category, category),
                    "metrics": [],
                }
            results["categories"][category]["metrics"].append({
                "key": metric["key"],
                "label": metric["label"],
                "value": round(value, 3) if value is not None else None,
                "unit": metric["unit"],
            })

        return results

    def query_cluster_charts(self, cluster_id: str, period_hours: int = 3, step: str = "5m") -> Dict[str, Any]:
        """查询集群趋势图数据（range query），返回各指标时间序列"""
        config = self._load_config()
        if not config["grafana_url"]:
            return {"error": "Prometheus 未配置"}

        end_ts = int(time.time())
        start_ts = end_ts - period_hours * 3600

        charts = {}
        for key, meta in CHART_METRICS.items():
            promql = meta["promql"].format(cluster_id=cluster_id)
            series = self._query_range(promql, config, start_ts, end_ts, step)
            charts[key] = {
                "label": meta["label"],
                "unit": meta["unit"],
                "data": series,
            }

        return {"cluster_id": cluster_id, "period_hours": period_hours, "step": step, "charts": charts}

    def query_all_clusters(self) -> List[Dict[str, Any]]:
        config = self._load_config()
        cluster_ids = config.get("cluster_ids", [])
        if not cluster_ids:
            return []
        return [self.query_cluster(cid) for cid in cluster_ids]

    def list_clusters(self) -> List[str]:
        """
        优先从 CCE 官方 API 动态获取集群 ID 列表；
        若 AK/SK 未配置或请求失败，则 fallback 到 prometheus_runtime 配置中的 cluster_ids。
        """
        try:
            from app.services.cce_api_service import CCEApiService
            ids = CCEApiService(self.db).get_cluster_ids()
            if ids:
                return ids
        except Exception as e:
            logger.warning(f"CCE API 获取集群列表失败，使用配置兜底: {e}")
        return self._load_config().get("cluster_ids", [])
