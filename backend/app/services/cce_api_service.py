"""
CCE 官方 API 服务
使用 AK/SK 签名调用百度云 CCE REST API，提供只读查询功能：
  - 集群列表
  - 集群详情
  - 节点列表
  - KubeConfig 下载
AK/SK 复用 bce_sync 模块中已保存的凭证。
"""
import hashlib
import hmac
import json
import requests
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import quote, urlparse
from loguru import logger
from sqlalchemy.orm import Session

from app.models.system_config import SystemConfig


# region → CCE endpoint
_CCE_ENDPOINT = {
    "cd": "cce.cd.baidubce.com",
    "bj": "cce.bj.baidubce.com",
    "gz": "cce.gz.baidubce.com",
    "su": "cce.su.baidubce.com",
}


def _bce_sign(access_key: str, secret_key: str, method: str,
              path: str, query_string: str = "") -> str:
    """生成 bce-auth-v1 Authorization 头"""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    expiration = 1800
    sign_key_info = f"bce-auth-v1/{access_key}/{now}/{expiration}"
    sign_key = hmac.new(
        secret_key.encode("utf-8"),
        sign_key_info.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    # 只签 host，host 值从 path 中无法得到，调用方传入 host
    # 这里的 canonical_headers 只含 host，在调用方设置
    canonical_uri = quote(path or "/", safe="/-_.~")
    if query_string:
        parts = sorted(query_string.split("&"))
        qs = "&".join(
            f"{quote(p.split('=')[0], safe='')}={quote(p.split('=')[1] if '=' in p else '', safe='')}"
            for p in parts
        )
    else:
        qs = ""
    signed_headers = "host"
    # canonical_headers 的 host 值由调用方注入，这里留占位符
    canonical_headers = "__HOST__"
    canonical_request = f"{method}\n{canonical_uri}\n{qs}\n{canonical_headers}"
    signature = hmac.new(
        sign_key.encode("utf-8"),
        canonical_request.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{sign_key_info}/{signed_headers}/{signature}", sign_key, canonical_request


class _BCEAuth(requests.auth.AuthBase):
    """requests 认证插件：为每个请求动态生成 bce-auth-v1 签名"""

    def __init__(self, access_key: str, secret_key: str):
        self.access_key = access_key
        self.secret_key = secret_key

    def __call__(self, r: requests.PreparedRequest) -> requests.PreparedRequest:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        expiration = 1800
        ak = self.access_key
        sk = self.secret_key

        sign_key_info = f"bce-auth-v1/{ak}/{now}/{expiration}"
        sign_key = hmac.new(
            sk.encode("utf-8"), sign_key_info.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        parsed = urlparse(r.url)
        host = parsed.hostname or ""
        canonical_uri = quote(parsed.path or "/", safe="/-_.~")

        qs = parsed.query or ""
        if qs:
            parts = sorted(qs.split("&"))
            qs = "&".join(
                f"{quote(p.split('=')[0], safe='')}={quote(p.split('=')[1] if '=' in p else '', safe='')}"
                for p in parts
            )

        signed_headers = "host"
        canonical_headers = f"host:{host}"
        canonical_request = f"{r.method}\n{canonical_uri}\n{qs}\n{canonical_headers}"
        signature = hmac.new(
            sign_key.encode("utf-8"), canonical_request.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        r.headers["Authorization"] = f"{sign_key_info}/{signed_headers}/{signature}"
        return r


class CCEApiService:
    """CCE 官方 API 只读服务，AK/SK 从 bce_sync 配置中读取"""

    def __init__(self, db: Session):
        self.db = db
        self._credentials_cache: Optional[tuple] = None

    # ---- 凭证与 session ----

    def _get_credentials(self) -> tuple[str, str, str]:
        """返回 (access_key, secret_key, region)，从 bce_sync 配置读取"""
        if self._credentials_cache:
            return self._credentials_cache
        row = self.db.query(SystemConfig).filter_by(
            module="bce_sync", config_key="main"
        ).first()
        cfg: Dict[str, Any] = {}
        if row and row.config_value:
            try:
                cfg = json.loads(row.config_value)
            except Exception:
                pass
        ak = cfg.get("access_key", "")
        sk = cfg.get("secret_key", "")
        region = cfg.get("region", "cd")
        self._credentials_cache = (ak, sk, region)
        return ak, sk, region

    def _session(self) -> tuple[requests.Session, str]:
        """返回 (session, base_url)"""
        ak, sk, region = self._get_credentials()
        endpoint = _CCE_ENDPOINT.get(region, f"cce.{region}.baidubce.com")
        session = requests.Session()
        session.auth = _BCEAuth(ak, sk)
        return session, f"https://{endpoint}", ak, sk

    def _check_credentials(self) -> Optional[str]:
        ak, sk, _ = self._get_credentials()
        if not ak or not sk:
            return "未配置 BCE Access Key / Secret Key，请在系统设置 → BCE同步 中配置"
        return None

    # ---- 集群列表 ----

    def list_clusters(self, page_size: int = 100) -> Dict[str, Any]:
        """
        GET /v2/clusters  分页获取全部集群，返回标准化列表
        """
        err = self._check_credentials()
        if err:
            return {"success": False, "error": err}
        try:
            session, base_url, _, _ = self._session()
            all_clusters = []
            page_no = 1
            while True:
                resp = session.get(
                    f"{base_url}/v2/clusters",
                    params={"pageNo": page_no, "pageSize": page_size,
                            "orderBy": "clusterID", "order": "ASC"},
                    timeout=30,
                )
                resp.raise_for_status()
                data = resp.json()
                cluster_page = data.get("clusterPage") or data.get("result") or data
                items = cluster_page.get("clusterList") or []
                for item in items:
                    all_clusters.append(self._normalize_cluster(item))
                total = cluster_page.get("totalCount") or cluster_page.get("total", 0)
                if len(all_clusters) >= total or len(items) < page_size:
                    break
                page_no += 1
            logger.info(f"CCE API 获取到 {len(all_clusters)} 个集群")
            return {"success": True, "clusters": all_clusters}
        except Exception as e:
            logger.error(f"CCE list_clusters 失败: {e}")
            return {"success": False, "error": str(e)}

    def get_cluster_ids(self) -> List[str]:
        """仅返回集群 ID 列表，供下拉框使用"""
        result = self.list_clusters()
        if not result["success"]:
            return []
        return [c["clusterID"] for c in result["clusters"]]

    # ---- 集群详情 ----

    def get_cluster_detail(self, cluster_id: str) -> Dict[str, Any]:
        """
        GET /v2/cluster/{clusterID}  获取单个集群详情
        """
        err = self._check_credentials()
        if err:
            return {"success": False, "error": err}
        try:
            session, base_url, _, _ = self._session()
            resp = session.get(
                f"{base_url}/v2/cluster/{cluster_id}", timeout=30
            )
            resp.raise_for_status()
            data = resp.json()
            cluster = data.get("cluster") or data
            return {"success": True, "cluster": self._normalize_cluster(cluster)}
        except Exception as e:
            logger.error(f"CCE get_cluster_detail {cluster_id} 失败: {e}")
            return {"success": False, "error": str(e)}

    # ---- 节点列表 ----

    def list_cluster_instances(self, cluster_id: str, page_size: int = 100) -> Dict[str, Any]:
        """
        GET /v2/cluster/{clusterID}/instances  获取集群全部节点
        """
        err = self._check_credentials()
        if err:
            return {"success": False, "error": err}
        try:
            session, base_url, _, _ = self._session()
            all_nodes = []
            page_no = 1
            while True:
                resp = session.get(
                    f"{base_url}/v2/cluster/{cluster_id}/instances",
                    params={"pageNo": page_no, "pageSize": page_size,
                            "orderBy": "createdAt", "order": "asc"},
                    timeout=30,
                )
                resp.raise_for_status()
                data = resp.json()
                instance_page = data.get("instancePage") or data.get("result") or data
                items = instance_page.get("instanceList") or []
                for item in items:
                    all_nodes.append(self._normalize_instance(item, cluster_id))
                total = instance_page.get("totalCount") or instance_page.get("total", 0)
                if len(all_nodes) >= total or len(items) < page_size:
                    break
                page_no += 1
            return {"success": True, "instances": all_nodes, "total": len(all_nodes)}
        except Exception as e:
            logger.error(f"CCE list_instances {cluster_id} 失败: {e}")
            return {"success": False, "error": str(e)}

    # ---- KubeConfig ----

    def get_kubeconfig(self, cluster_id: str, kube_type: str = "vpc") -> Dict[str, Any]:
        """
        GET /v2/kubeconfig/{clusterID}/{type}
        type: vpc (内网) | public (外网 EIP)
        """
        if kube_type not in ("vpc", "public"):
            return {"success": False, "error": "type 只能是 vpc 或 public"}
        err = self._check_credentials()
        if err:
            return {"success": False, "error": err}
        try:
            session, base_url, _, _ = self._session()
            resp = session.get(
                f"{base_url}/v2/kubeconfig/{cluster_id}/{kube_type}", timeout=30
            )
            resp.raise_for_status()
            data = resp.json()
            kube_config = data.get("kubeConfig", "")
            if not kube_config:
                return {"success": False, "error": "响应中无 kubeConfig 字段"}
            return {
                "success": True,
                "kubeConfig": kube_config,
                "kubeConfigType": data.get("kubeConfigType", kube_type),
                "cluster_id": cluster_id,
            }
        except Exception as e:
            logger.error(f"CCE get_kubeconfig {cluster_id} 失败: {e}")
            return {"success": False, "error": str(e)}

    # ---- 标准化 ----

    @staticmethod
    def _normalize_cluster(c: Dict[str, Any]) -> Dict[str, Any]:
        # 实测响应：clusterID 在 spec 里，不在顶层
        spec = c.get("spec") or c
        master_cfg = spec.get("masterConfig") or {}
        net_cfg = spec.get("containerNetworkConfig") or {}
        status = c.get("status") or {}
        return {
            "clusterID": spec.get("clusterID") or c.get("clusterID", ""),
            "clusterName": spec.get("clusterName", ""),
            "clusterType": spec.get("clusterType", ""),
            "k8sVersion": spec.get("k8sVersion", ""),
            "description": spec.get("description", ""),
            "vpcID": spec.get("vpcID", ""),
            "masterType": master_cfg.get("masterType", ""),
            "clusterHA": master_cfg.get("clusterHA", 1),
            "networkMode": net_cfg.get("mode", ""),
            "kubeProxyMode": net_cfg.get("kubeProxyMode", ""),
            "clusterPodCIDR": net_cfg.get("clusterPodCIDR", ""),
            "clusterIPServiceCIDR": net_cfg.get("clusterIPServiceCIDR", ""),
            "plugins": spec.get("plugins") or [],
            "clusterPhase": status.get("clusterPhase", ""),
            "nodeNum": status.get("nodeNum", 0),
            "createdAt": c.get("createdAt", ""),
            "updatedAt": c.get("updatedAt", ""),
        }

    @staticmethod
    def _normalize_instance(n: Dict[str, Any], cluster_id: str) -> Dict[str, Any]:
        # 实测响应结构：
        #   instanceID  → status.machine.instanceID
        #   IP          → status.machine.vpcIP
        #   k8sNodeName → status.machine.k8sNodeName
        #   CPU/内存    → spec.instanceResource.cpu/mem
        #   OS          → spec.instanceOS.osName
        #   instanceID  → spec.cceInstanceID（CCE内部ID）
        spec = n.get("spec") or n
        status = n.get("status") or {}
        machine_status = status.get("machine") or {}
        inst_resource = spec.get("instanceResource") or {}
        inst_os = spec.get("instanceOS") or {}
        vpc_cfg = spec.get("vpcConfig") or {}
        return {
            "instanceID": machine_status.get("instanceID") or spec.get("cceInstanceID", ""),
            "instanceName": spec.get("instanceName", ""),
            "clusterID": cluster_id,
            "clusterRole": spec.get("clusterRole", ""),
            "instanceState": status.get("instancePhase") or "",
            "instanceIp": machine_status.get("vpcIP") or "",
            "k8sNodeName": machine_status.get("k8sNodeName") or "",
            "cpu": inst_resource.get("cpu", ""),
            "mem": inst_resource.get("mem", ""),
            "os": inst_os.get("osName", "") or inst_os.get("imageName", ""),
            "osVersion": inst_os.get("osVersion", ""),
            "machineType": spec.get("machineType", ""),
            "instanceType": spec.get("instanceType", ""),
            "availableZone": vpc_cfg.get("availableZone", ""),
            "createdAt": n.get("createdAt", ""),
        }
