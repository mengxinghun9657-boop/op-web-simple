#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prometheus配置管理模块
用于管理百度云CCE Grafana/Prometheus的访问配置
"""
import os
import json
from typing import Dict, Optional
from pathlib import Path
from app.core.deps import SessionLocal
from app.models.system_config import SystemConfig


class PrometheusConfig:
    """Prometheus配置管理类"""
    
    # 默认配置
    DEFAULT_CONFIG = {
        "base_url": "https://console.bce.baidu.com/api/cce/service/v2/grafana/proxy",
        "datasource_id": 166,
        "headers": {
            "Accept": "application/json, text/plain, */*",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "X-Grafana-Org-Id": "1",
            "Referer": "https://console.bce.baidu.com/api/cce/service/v2/grafana/proxy/d/SecZmPmSz/ji-qun-gai-lan"
        },
        "cookies": {},
        "query_config": {
            "default_time_range": 900,  # 15分钟
            "query_step": 15
        }
    }
    
    def __init__(self, config_file: Optional[str] = None):
        """
        初始化配置管理
        
        Args:
            config_file: 配置文件路径，如果为None则使用默认路径
        """
        if config_file is None:
            config_dir = Path(__file__).parent.parent.parent / "config"
            config_dir.mkdir(exist_ok=True)
            config_file = config_dir / "prometheus_config.json"
        
        self.config_file = Path(config_file)
        self.config = self._load_config()
    
    def _load_config(self) -> Dict:
        """加载配置文件"""
        # 优先读取统一 Prometheus 配置
        try:
            db = SessionLocal()
            runtime_record = db.query(SystemConfig).filter(
                SystemConfig.module == 'prometheus_runtime',
                SystemConfig.config_key == 'main'
            ).first()
            if runtime_record and runtime_record.config_value:
                runtime_config = json.loads(runtime_record.config_value)
                return {
                    "base_url": runtime_config.get("grafana_url", "https://cprom.cd.baidubce.com/select/prometheus"),
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

        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                # 合并默认配置和加载的配置
                config = self.DEFAULT_CONFIG.copy()
                config.update(loaded_config)
                return config
            except Exception as e:
                print(f"⚠️ 加载配置文件失败: {e}，使用默认配置")
                return self.DEFAULT_CONFIG.copy()
        else:
            # 首次运行，创建默认配置文件
            self._save_config(self.DEFAULT_CONFIG)
            return self.DEFAULT_CONFIG.copy()
    
    def _save_config(self, config: Dict) -> bool:
        """保存配置到文件"""
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"❌ 保存配置文件失败: {e}")
            return False
    
    def get_base_url(self) -> str:
        """获取基础URL"""
        return self.config.get("base_url", self.DEFAULT_CONFIG["base_url"])
    
    def get_datasource_id(self) -> int:
        """获取数据源ID"""
        return self.config.get("datasource_id", self.DEFAULT_CONFIG["datasource_id"])
    
    def get_headers(self) -> Dict:
        """获取HTTP请求头"""
        if self.config.get("token") and self.config.get("instance_id"):
            token = self.config.get("token")
            return {
                "Authorization": token if str(token).startswith("Bearer ") else f"Bearer {token}",
                "InstanceId": self.config.get("instance_id"),
                "Accept": "application/json, text/plain, */*"
            }
        return self.config.get("headers", self.DEFAULT_CONFIG["headers"]).copy()
    
    def get_cookies(self) -> Dict:
        """获取Cookies"""
        return self.config.get("cookies", {}).copy()

    def use_direct_api(self) -> bool:
        return bool(self.config.get("token") and self.config.get("instance_id"))
    
    def get_query_config(self) -> Dict:
        """获取查询配置"""
        return self.config.get("query_config", self.DEFAULT_CONFIG["query_config"]).copy()
    
    def update_cookies(self, cookies: Dict) -> bool:
        """
        更新Cookies配置
        
        Args:
            cookies: Cookie字典
            
        Returns:
            是否更新成功
        """
        # 验证必要的cookie字段
        required_keys = ['bce-session', 'bce-login-accountid', 'bce-org-id']
        missing_keys = [key for key in required_keys if key not in cookies]
        
        if missing_keys:
            print(f"❌ Cookie缺少必要字段: {', '.join(missing_keys)}")
            return False
        
        self.config["cookies"] = cookies
        return self._save_config(self.config)
    
    def parse_cookie_string(self, cookie_string: str) -> Dict:
        """
        解析Cookie字符串
        
        Args:
            cookie_string: 浏览器复制的Cookie字符串
            
        Returns:
            解析后的Cookie字典
        """
        cookies = {}
        for item in cookie_string.split(';'):
            item = item.strip()
            if '=' in item:
                name, value = item.split('=', 1)
                cookies[name.strip()] = value.strip()
        
        # 筛选有效的cookie
        valid_keys = ['bce-session', 'jwt', 'bce-login-accountid', 'bce-org-id', 
                      'bce-sessionid', 'JSESSIONID']
        filtered_cookies = {k: v for k, v in cookies.items() if k in valid_keys}
        
        return filtered_cookies
    
    def test_connection(self) -> tuple[bool, str]:
        """
        测试连接是否有效

        Returns:
            (是否成功, 消息)
        """
        try:
            import requests
            import time

            if self.use_direct_api():
                url = f"{self.get_base_url().rstrip('/')}/api/v1/query"
            else:
                url = f"{self.get_base_url()}/api/datasources/proxy/{self.get_datasource_id()}/api/v1/query"
            params = {
                'query': 'up',
                'time': int(time.time())
            }

            cookies = self.get_cookies()
            if not self.use_direct_api() and not cookies:
                return False, "⚠️  Cookie 未配置，请先配置 Cookie"

            response = requests.get(
                url,
                headers=self.get_headers(),
                cookies=cookies if not self.use_direct_api() else None,
                params=params,
                timeout=10,
                verify=False  # 内网环境跳过SSL证书验证
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    return True, "✅ 连接成功！"
                else:
                    return False, f"❌ 连接失败，Prometheus 返回错误: {data.get('error', 'Unknown')}"
            elif response.status_code == 401:
                return False, "❌ 认证失败（状态码: 401）"
            elif response.status_code == 403:
                return False, "❌ 权限不足（状态码: 403），请检查账号权限"
            else:
                return False, f"❌ 连接失败，状态码: {response.status_code}"

        except requests.exceptions.SSLError as e:
            return False, f"❌ SSL 连接错误: {str(e)[:200]}\n提示: 这通常是 Cookie 认证失败或网络配置问题"
        except requests.exceptions.ConnectionError as e:
            return False, f"❌ 网络连接错误: {str(e)[:200]}\n提示: 请检查网络连接和代理配置"
        except requests.exceptions.Timeout:
            return False, "❌ 请求超时（10秒），请检查网络连接"
        except Exception as e:
            return False, f"❌ 连接错误: {str(e)[:200]}"
    
    def get_all_config(self) -> Dict:
        """获取完整配置（用于API返回）"""
        config = self.config.copy()
        # 隐藏敏感信息
        if "cookies" in config:
            config["cookies_configured"] = bool(config["cookies"])
            config["cookies"] = {k: "***" for k in config["cookies"].keys()}
        return config


# 全局配置实例
_prometheus_config = None


def get_prometheus_config() -> PrometheusConfig:
    """获取全局Prometheus配置实例"""
    global _prometheus_config
    if _prometheus_config is None:
        _prometheus_config = PrometheusConfig()
    return _prometheus_config
