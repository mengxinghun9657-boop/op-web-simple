#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PFS Prometheus API 客户端

功能：
- 从系统配置加载 PFS 配置
- 封装 Prometheus API 调用
- 认证管理（Token + InstanceId）
- 错误处理和重试机制

参考：app/core/prometheus_config.py
"""

import requests
import urllib3
import json
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models.system_config import SystemConfig
from app.core.logger import logger

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# ================= 默认配置（从 pfswatcher.py 复制）=================
DEFAULT_CONFIG = {
    "grafana_url": "https://cprom.cd.baidubce.com/select/prometheus",
    "token": (
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
        "eyJuYW1lc3BhY2UiOiJjcHJvbS1wbWRmd3dxcWxuMHc3Iiwic2VjcmV0TmFtZSI6ImYwMDhkYjQ3NTE4OTRhZmU5Yjg1MWUzMmEyMDY4MzM1IiwiZXhwIjo0OTAxMzI4NzY4LCJpc3MiOiJjcHJvbSJ9."
        "xMrMQgaV1Hb0WwF04sTFFTaMWyfqoutB4670dTpIIHA"
    ),
    "instance_id": "cprom-pmdfwwqqln0w7",
    "pfs_instance_ids": ["pfs-mTYGr6"],  # 支持多个集群ID
    "region": "cd",
    "instance_type": "plusl2",
    "step": "5m",
    "default_client": ".*"
}


# ================= 指标配置（从 pfswatcher.py 完整复制）=================
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
        "warn_threshold": -0.50,
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

# Client 级别指标前缀（从 pfswatcher.py 复制）
CLIENT_METRIC_PREFIXES = [
    "FisReadThroughput", "FisWriteThroughput",
    "FisReadQps", "FisWriteQps",
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
    
    # Client 级别 PromQL 模板（从 pfswatcher.py 精确提取）
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


class PFSPrometheusClient:
    """PFS Prometheus API 客户端
    
    配置加载优先级：
    1. 优先从数据库 system_config 表读取（module='pfs'）
    2. 如果数据库没有配置，使用 DEFAULT_CONFIG
    3. 用户可以在前端系统配置页面修改并保存到数据库
    """
    
    def __init__(self, db_session: Session):
        """从系统配置初始化客户端
        
        Args:
            db_session: 数据库会话
        """
        config = self._load_config(db_session)
        
        self.base_url = config["grafana_url"].rstrip('/')
        self.token = config["token"]
        self.instance_id = config["instance_id"]
        
        # 支持多个集群ID（向后兼容单个ID）
        pfs_ids = config.get("pfs_instance_ids", [])
        if not pfs_ids and config.get("pfs_instance_id"):
            # 向后兼容：如果只有单个ID，转换为数组
            pfs_ids = [config["pfs_instance_id"]]
        self.pfs_instance_ids = pfs_ids
        self.pfs_instance_id = pfs_ids[0] if pfs_ids else "pfs-mTYGr6"  # 默认使用第一个
        
        self.region = config.get("region", "cd")
        self.instance_type = config.get("instance_type", "plusl2")
        self.step = config.get("step", "5m")
        self.default_client = config.get("default_client", ".*")
        
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "InstanceId": self.instance_id,
        }
        
        logger.info(f"PFS Prometheus 客户端初始化成功: {self.base_url}, PFS实例: {self.pfs_instance_ids}")
    
    def _load_config(self, db_session: Session) -> dict:
        """从数据库加载配置（复用 SystemConfig）
        
        配置加载逻辑：
        1. 查询 system_config 表中 module='pfs' 的所有配置
        2. 如果数据库有配置，合并到结果中
        3. 如果数据库没有配置，使用 DEFAULT_CONFIG
        
        Args:
            db_session: 数据库会话
            
        Returns:
            配置字典
        """
        try:
            # 查询数据库配置
            configs = db_session.query(SystemConfig).filter(
                SystemConfig.module == "pfs"
            ).all()
            
            # 从默认配置开始
            result = DEFAULT_CONFIG.copy()
            
            # 如果数据库有配置，覆盖默认配置
            if configs:
                logger.info(f"从数据库加载 PFS 配置，共 {len(configs)} 条记录")
                for config in configs:
                    if config.config_value:
                        try:
                            # 解析 JSON 配置值
                            config_data = json.loads(config.config_value)
                            result.update(config_data)
                        except json.JSONDecodeError as e:
                            logger.error(f"解析配置失败: {config.config_key}, 错误: {e}")
            else:
                logger.info("数据库中没有 PFS 配置，使用默认配置")
            
            return result
            
        except Exception as e:
            logger.error(f"加载 PFS 配置失败: {e}，使用默认配置")
            return DEFAULT_CONFIG.copy()
    
    def query_range(
        self,
        promql: str,
        start_ts: int,
        end_ts: int,
        step: str = "5m"
    ) -> List[Dict[str, Any]]:
        """执行范围查询
        
        Args:
            promql: Prometheus 查询语句
            start_ts: 开始时间戳（Unix 时间戳，秒）
            end_ts: 结束时间戳（Unix 时间戳，秒）
            step: 查询步长（如 "5m", "1h"）
            
        Returns:
            查询结果列表
        """
        url = f"{self.base_url}/api/v1/query_range"
        params = {
            "query": promql,
            "start": start_ts,
            "end": end_ts,
            "step": step,
        }
        
        try:
            logger.debug(f"执行 Prometheus 查询: {promql}")
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
                    results = data.get("data", {}).get("result", [])
                    logger.debug(f"查询成功，返回 {len(results)} 条结果")
                    return results
                else:
                    logger.error(f"Prometheus 查询失败: {data.get('error')}")
                    return []
            else:
                logger.error(f"Prometheus API 请求失败: HTTP {resp.status_code}")
                return []
                
        except requests.exceptions.Timeout:
            logger.error(f"Prometheus 查询超时: {promql}")
            return []
        except Exception as e:
            logger.error(f"Prometheus 查询异常: {e}")
            return []
    
    def get_label_values(self, label_name: str) -> List[str]:
        """获取标签值列表
        
        Args:
            label_name: 标签名称（如 "ClientId", "ClientIp"）
            
        Returns:
            标签值列表
        """
        url = f"{self.base_url}/api/v1/label/{label_name}/values"
        
        try:
            resp = requests.get(
                url,
                headers=self.headers,
                timeout=30,
                verify=False
            )
            
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == "success":
                    values = data.get("data", [])
                    logger.debug(f"获取标签 {label_name} 的值，共 {len(values)} 个")
                    return values
                else:
                    logger.error(f"获取标签值失败: {data.get('error')}")
                    return []
            else:
                logger.error(f"获取标签值请求失败: HTTP {resp.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"获取标签值异常: {e}")
            return []
    
    def test_connection(self) -> tuple[bool, str]:
        """测试连接
        
        Returns:
            (是否成功, 消息)
        """
        try:
            # 执行一个简单的查询测试连接
            url = f"{self.base_url}/api/v1/query"
            params = {"query": "up"}
            
            resp = requests.get(
                url,
                headers=self.headers,
                params=params,
                timeout=10,
                verify=False
            )
            
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == "success":
                    logger.info("PFS Prometheus 连接测试成功")
                    return True, "连接成功"
                else:
                    error_msg = data.get("error", "未知错误")
                    logger.error(f"PFS Prometheus 连接测试失败: {error_msg}")
                    return False, f"连接失败: {error_msg}"
            else:
                logger.error(f"PFS Prometheus 连接测试失败: HTTP {resp.status_code}")
                return False, f"连接失败: HTTP {resp.status_code}"
                
        except requests.exceptions.Timeout:
            logger.error("PFS Prometheus 连接超时")
            return False, "连接超时"
        except Exception as e:
            logger.error(f"PFS Prometheus 连接异常: {e}")
            return False, f"连接异常: {str(e)}"
    
    @staticmethod
    def get_metric_config(metric_name: str = None) -> Dict[str, Any]:
        """获取指标配置
        
        Args:
            metric_name: 指标名称，如果为 None 则返回所有指标配置
            
        Returns:
            指标配置字典
        """
        if metric_name:
            return METRIC_CONFIG.get(metric_name, {})
        return METRIC_CONFIG
    
    @staticmethod
    def get_metrics_by_category(category: str = None, level: str = None) -> Dict[str, List[Dict[str, Any]]]:
        """按分类获取指标列表
        
        Args:
            category: 指标分类（容量、吞吐、QPS、延迟、元数据 QPS、元数据延迟）
            level: 指标级别（cluster、client）
            
        Returns:
            按分类分组的指标列表
        """
        from collections import defaultdict
        
        result = defaultdict(list)
        
        for metric_name, config in METRIC_CONFIG.items():
            # 过滤级别
            if level and config.get("level") != level:
                continue
            
            # 过滤分类
            if category and config.get("category") != category:
                continue
            
            metric_category = config.get("category", "其他")
            result[metric_category].append({
                "name": metric_name,
                **config
            })
        
        return dict(result)
