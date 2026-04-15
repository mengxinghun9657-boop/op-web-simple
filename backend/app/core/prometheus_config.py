#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prometheus配置管理模块
用于管理 cProm 的访问配置（Token 模式）
"""
import json
from typing import Dict, Optional
from app.core.deps import SessionLocal
from app.models.system_config import SystemConfig


class PrometheusConfig:
    """Prometheus配置管理类（统一走 Token 认证）"""

    DEFAULT_CONFIG = {
        "base_url": "https://cprom.cd.baidubce.com/select/prometheus",
        "token": "",
        "instance_id": "",
        "cluster_ids": "",
        "query_config": {
            "default_time_range": 900,
            "query_step": "5m"
        }
    }

    def __init__(self):
        self.config = self._load_config()

    def _load_config(self) -> Dict:
        """从数据库加载 prometheus_runtime 配置"""
        try:
            db = SessionLocal()
            runtime_record = db.query(SystemConfig).filter(
                SystemConfig.module == 'prometheus_runtime',
                SystemConfig.config_key == 'main'
            ).first()
            if runtime_record and runtime_record.config_value:
                runtime_config = json.loads(runtime_record.config_value)
                return {
                    "base_url": runtime_config.get("grafana_url", self.DEFAULT_CONFIG["base_url"]),
                    "token": runtime_config.get("token", ""),
                    "instance_id": runtime_config.get("instance_id", ""),
                    "cluster_ids": runtime_config.get("cluster_ids", ""),
                    "query_config": {
                        "default_time_range": 900,
                        "query_step": runtime_config.get("step", "5m")
                    }
                }
        except Exception:
            pass
        finally:
            try:
                db.close()
            except Exception:
                pass
        return dict(self.DEFAULT_CONFIG)

    def get_base_url(self) -> str:
        return self.config.get("base_url", self.DEFAULT_CONFIG["base_url"])

    def get_headers(self) -> Dict:
        token = self.config.get("token", "")
        headers = {
            "Accept": "application/json, text/plain, */*"
        }
        if token:
            headers["Authorization"] = token if str(token).startswith("Bearer ") else f"Bearer {token}"
        if self.config.get("instance_id"):
            headers["InstanceId"] = self.config["instance_id"]
        return headers

    def get_query_config(self) -> Dict:
        return self.config.get("query_config", self.DEFAULT_CONFIG["query_config"]).copy()

    def test_connection(self) -> tuple[bool, str]:
        """测试 Prometheus 连接"""
        try:
            import requests
            import time

            if not self.config.get("token"):
                return False, "❌ 未配置 Token，请在系统配置 → Prometheus 配置中填写 Token"

            url = f"{self.get_base_url().rstrip('/')}/api/v1/query"
            params = {'query': 'up', 'time': int(time.time())}
            response = requests.get(
                url,
                headers=self.get_headers(),
                params=params,
                timeout=10,
                verify=False
            )
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    return True, "✅ 连接成功！"
                else:
                    return False, f"❌ Prometheus 返回错误: {data.get('error', 'Unknown')}"
            elif response.status_code == 401:
                return False, "❌ 认证失败（401），请检查 Token 是否正确"
            else:
                return False, f"❌ 连接失败，状态码: {response.status_code}"
        except requests.exceptions.ConnectionError as e:
            return False, f"❌ 网络连接错误: {str(e)[:200]}"
        except requests.exceptions.Timeout:
            return False, "❌ 请求超时（10秒），请检查网络连接"
        except Exception as e:
            return False, f"❌ 连接错误: {str(e)[:200]}"

    def get_all_config(self) -> Dict:
        """获取完整配置（脱敏）"""
        config = self.config.copy()
        token = config.get("token", "")
        config["token_configured"] = bool(token)
        config["token_preview"] = (token[:10] + "...") if len(token) > 10 else ("***" if token else "")
        config.pop("token", None)
        return config


# 全局配置实例
_prometheus_config = None


def get_prometheus_config() -> PrometheusConfig:
    global _prometheus_config
    if _prometheus_config is None:
        _prometheus_config = PrometheusConfig()
    return _prometheus_config
