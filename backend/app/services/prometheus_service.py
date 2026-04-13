#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prometheus查询服务
用于从百度云CCE Grafana获取集群监控指标
"""
import time
import requests
import urllib3
from typing import Dict, List, Optional, Any
from app.core.prometheus_config import get_prometheus_config
from app.core.logger import logger

# 禁用 SSL 警告（仅限内网环境）
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class PrometheusService:
    """Prometheus查询服务类"""
    
    def __init__(self):
        """初始化服务"""
        self.config = get_prometheus_config()
    
    def query_metric(self, query: str, query_time: Optional[int] = None) -> Optional[str]:
        """
        查询单个Prometheus指标

        Args:
            query: Prometheus查询语句
            query_time: 查询时间戳，None则使用当前时间

        Returns:
            查询结果值，失败返回None
        """
        try:
            if self.config.use_direct_api():
                url = f"{self.config.get_base_url().rstrip('/')}/api/v1/query"
            else:
                url = f"{self.config.get_base_url()}/api/datasources/proxy/{self.config.get_datasource_id()}/api/v1/query"

            params = {
                'query': query,
                'time': query_time or int(time.time())
            }

            cookies = self.config.get_cookies()
            if not self.config.use_direct_api() and not cookies:
                logger.warning("⚠️  Prometheus Cookie 未配置，请在资源分析页面配置 Cookie")
                return None

            response = requests.get(
                url,
                headers=self.config.get_headers(),
                cookies=cookies if not self.config.use_direct_api() else None,
                params=params,
                timeout=30,
                verify=False  # 内网环境跳过SSL证书验证
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success' and data['data']['result']:
                    return data['data']['result'][0]['value'][1]
                else:
                    logger.warning(f"查询无结果: {query[:100]}...")
            elif response.status_code == 401:
                logger.error(f"❌ Cookie 已过期或无效，状态码: 401，请在资源分析页面重新配置 Cookie")
            elif response.status_code == 403:
                logger.error(f"❌ 权限不足，状态码: 403，请检查 Cookie 对应账号的权限")
            else:
                logger.warning(f"查询失败，状态码: {response.status_code}, 查询: {query[:100]}...")

            return None

        except requests.exceptions.SSLError as e:
            logger.error(f"❌ SSL 连接错误: {str(e)[:200]}")
            logger.error(f"   提示: 如果在内网环境，这通常是 Cookie 认证失败导致")
            return None
        except requests.exceptions.ConnectionError as e:
            logger.error(f"❌ 网络连接错误: {str(e)[:200]}")
            logger.error(f"   提示: 请检查网络连接和代理配置")
            return None
        except requests.exceptions.Timeout as e:
            logger.error(f"❌ 请求超时: {str(e)[:200]}")
            return None
        except Exception as e:
            logger.error(f"查询指标失败: {query[:100]}..., 错误: {str(e)[:200]}")
            return None
    
    def get_cluster_metrics(self, cluster_id: str) -> Dict[str, Any]:
        """
        获取单个集群的完整指标数据
        
        Args:
            cluster_id: 集群ID
            
        Returns:
            指标数据字典
        """
        logger.info(f"开始获取集群 {cluster_id} 的指标数据")
        
        # 定义所有查询
        queries = self._get_cluster_queries(cluster_id)
        
        # 执行查询
        results = {}
        for name, query_str in queries.items():
            value = self.query_metric(query_str)
            results[name] = value if value else "N/A"
        
        logger.info(f"集群 {cluster_id} 指标获取完成，共 {len(results)} 个指标")
        return results
    
    def get_multiple_clusters_metrics(self, cluster_ids: List[str], progress_callback=None) -> Dict[str, Dict[str, Any]]:
        """
        批量获取多个集群的指标数据
        
        Args:
            cluster_ids: 集群ID列表
            progress_callback: 进度回调函数，签名为 callback(completed, total, message)
            
        Returns:
            {cluster_id: metrics} 格式的数据
        """
        logger.info(f"开始批量获取 {len(cluster_ids)} 个集群的指标数据")
        
        all_data = {}
        for i, cluster_id in enumerate(cluster_ids, 1):
            logger.info(f"正在获取集群 {cluster_id} ({i}/{len(cluster_ids)})")
            try:
                metrics = self.get_cluster_metrics(cluster_id)
                all_data[cluster_id] = metrics
                
                # 调用进度回调
                if progress_callback:
                    progress_callback(i, len(cluster_ids), f"已采集 {i}/{len(cluster_ids)} 个集群")
                    
            except Exception as e:
                logger.error(f"获取集群 {cluster_id} 失败: {str(e)}")
                all_data[cluster_id] = {"error": str(e)}
                
                # 即使失败也更新进度
                if progress_callback:
                    progress_callback(i, len(cluster_ids), f"已采集 {i}/{len(cluster_ids)} 个集群（包含失败）")
        
        logger.info(f"批量获取完成，成功 {len(all_data)} 个集群")
        return all_data
    
    def _get_cluster_queries(self, cluster_id: str) -> Dict[str, str]:
        """
        获取集群的所有Prometheus查询语句
        
        Args:
            cluster_id: 集群ID
            
        Returns:
            {指标名称: Prometheus查询语句} 字典
        """
        return {
            # ========== 基础资源指标 ==========
            'Node Count': f'sum(kube_node_info{{clusterID=~"{cluster_id}"}})',
            'Pod Count': f'sum(kube_pod_info{{clusterID=~"{cluster_id}"}})',
            'Memory Request %': f'sum(kube_pod_container_resource_requests{{resource="memory", clusterID=~"{cluster_id}"}}) / sum(kube_node_status_allocatable{{resource="memory", clusterID=~"{cluster_id}"}}) * 100',
            'Memory Capacity': f'sum(kube_node_status_capacity{{resource="memory", clusterID=~"{cluster_id}"}})',
            'Memory Allocatable': f'sum(kube_node_status_allocatable{{resource="memory", clusterID=~"{cluster_id}"}})',
            'Memory Request': f'sum(kube_pod_container_resource_requests{{resource="memory", clusterID=~"{cluster_id}"}})',
            'CPU Request %': f'sum(kube_pod_container_resource_requests{{resource="cpu", clusterID=~"{cluster_id}"}}) / sum(kube_node_status_allocatable{{resource="cpu", clusterID=~"{cluster_id}"}}) * 100',
            'CPU Capacity': f'sum(kube_node_status_capacity{{resource="cpu", clusterID=~"{cluster_id}"}})',
            'CPU Allocatable': f'sum(kube_node_status_allocatable{{resource="cpu", clusterID=~"{cluster_id}"}})',
            'CPU Request': f'sum(kube_pod_container_resource_requests{{resource="cpu", clusterID=~"{cluster_id}"}})',
            
            # ========== 实际资源使用率 ==========
            'Memory Usage': f'sum(node_memory_MemTotal_bytes{{clusterID=~"{cluster_id}"}} - node_memory_MemAvailable_bytes{{clusterID=~"{cluster_id}"}})',
            'Memory Usage %': f'(sum(node_memory_MemTotal_bytes{{clusterID=~"{cluster_id}"}} - node_memory_MemAvailable_bytes{{clusterID=~"{cluster_id}"}}) / sum(node_memory_MemTotal_bytes{{clusterID=~"{cluster_id}"}})) * 100',
            'CPU Usage': f'sum(rate(node_cpu_seconds_total{{mode!="idle",clusterID=~"{cluster_id}"}}[5m]))',
            'CPU Usage %': f'sum(rate(node_cpu_seconds_total{{mode!="idle",clusterID=~"{cluster_id}"}}[5m])) / sum(kube_node_status_allocatable{{resource="cpu", clusterID=~"{cluster_id}"}}) * 100',
            
            # ========== 资源限制 ==========
            'Memory Limit': f'sum(kube_pod_container_resource_limits{{resource="memory", clusterID=~"{cluster_id}"}})',
            'CPU Limit': f'sum(kube_pod_container_resource_limits{{resource="cpu", clusterID=~"{cluster_id}"}})',
            
            # ========== Pod状态监控 ==========
            'Running Pod Count': f'sum(kube_pod_status_phase{{phase="Running", clusterID=~"{cluster_id}"}})',
            'Pending Pod Count': f'sum(kube_pod_status_phase{{phase="Pending", clusterID=~"{cluster_id}"}})',
            'Failed Pod Count': f'sum(kube_pod_status_phase{{phase="Failed", clusterID=~"{cluster_id}"}})',
            'Succeeded Pod Count': f'sum(kube_pod_status_phase{{phase="Succeeded", clusterID=~"{cluster_id}"}})',
            'Evicted Pod Count': f'sum(kube_pod_status_reason{{reason="Evicted", clusterID=~"{cluster_id}"}})',
            'Pod Restarts (1h)': f'sum(max by (pod, namespace) (changes(kube_pod_container_status_restarts_total{{clusterID=~"{cluster_id}"}}[1h])))',
            'Pod Restarts (24h)': f'sum(max by (pod, namespace) (changes(kube_pod_container_status_restarts_total{{clusterID=~"{cluster_id}"}}[24h])))',
            
            # ========== 节点健康状态 ==========
            'Ready Node Count': f'sum(kube_node_status_condition{{condition="Ready", status="true", clusterID=~"{cluster_id}"}})',
            'NotReady Node Count': f'sum(kube_node_status_condition{{condition="Ready", status=~"false|unknown", clusterID=~"{cluster_id}"}} == 1) or vector(0)',
            'DiskPressure Node Count': f'sum(kube_node_status_condition{{condition="DiskPressure", status="true", clusterID=~"{cluster_id}"}} == 1) or vector(0)',
            'MemoryPressure Node Count': f'sum(kube_node_status_condition{{condition="MemoryPressure", status="true", clusterID=~"{cluster_id}"}} == 1) or vector(0)',
            'PIDPressure Node Count': f'sum(kube_node_status_condition{{condition="PIDPressure", status="true", clusterID=~"{cluster_id}"}} == 1) or vector(0)',
            'NetworkUnavailable Node Count': f'sum(kube_node_status_condition{{condition="NetworkUnavailable", status="true", clusterID=~"{cluster_id}"}} == 1) or vector(0)',
            
            # ========== 存储监控 ==========
            'Node Filesystem Usage %': f'avg((node_filesystem_size_bytes{{clusterID=~"{cluster_id}", fstype!="tmpfs"}} - node_filesystem_avail_bytes{{clusterID=~"{cluster_id}", fstype!="tmpfs"}}) / node_filesystem_size_bytes{{clusterID=~"{cluster_id}", fstype!="tmpfs"}} * 100)',
            
            # ========== 网络监控 ==========
            'Network Receive Bytes/s': f'sum(rate(node_network_receive_bytes_total{{clusterID=~"{cluster_id}", device!="lo"}}[5m]))',
            'Network Transmit Bytes/s': f'sum(rate(node_network_transmit_bytes_total{{clusterID=~"{cluster_id}", device!="lo"}}[5m]))',
            
            # ========== 服务监控 ==========
            'Service Count': f'sum(kube_service_info{{clusterID=~"{cluster_id}"}})',
            'Ingress Count': f'sum(kube_ingress_info{{clusterID=~"{cluster_id}"}})',
            
            # ========== 容器监控 ==========
            'Container Count': f'sum(kube_pod_container_info{{clusterID=~"{cluster_id}"}})',
            'Container Restarts (1h)': f'sum(changes(kube_pod_container_status_restarts_total{{clusterID=~"{cluster_id}"}}[1h]))',
            
            # ========== 资源效率指标 ==========
            'CPU Request vs Usage Ratio': f'(sum(rate(node_cpu_seconds_total{{mode!="idle",clusterID=~"{cluster_id}"}}[5m])) / sum(kube_pod_container_resource_requests{{resource="cpu", clusterID=~"{cluster_id}"}})) * 100',
            'Memory Request vs Usage Ratio': f'(sum(node_memory_MemTotal_bytes{{clusterID=~"{cluster_id}"}} - node_memory_MemAvailable_bytes{{clusterID=~"{cluster_id}"}}) / sum(kube_pod_container_resource_requests{{resource="memory", clusterID=~"{cluster_id}"}})) * 100',
            'Allocatable Memory per Node (avg)': f'avg(kube_node_status_allocatable{{resource="memory", clusterID=~"{cluster_id}"}})',
            'Allocatable CPU per Node (avg)': f'avg(kube_node_status_allocatable{{resource="cpu", clusterID=~"{cluster_id}"}})',
            
            # ========== 集群健康度评分 ==========
            'Node Ready Ratio': f'(sum(kube_node_status_condition{{condition="Ready", status="true", clusterID=~"{cluster_id}"}}) /sum(kube_node_status_condition{{condition="Ready", clusterID=~"{cluster_id}"}})* 100)',
            'Pod Success Rate': f'(sum(kube_pod_status_phase{{phase="Running", clusterID=~"{cluster_id}"}}) / sum(kube_pod_info{{clusterID=~"{cluster_id}"}}) * 100)',
        }
