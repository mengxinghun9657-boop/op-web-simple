"""
GPU 集群监控服务
"""
from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime
import os
from urllib.parse import urlparse, urlunparse, urlencode
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
from loguru import logger
from sqlalchemy.orm import Session
import json

from app.core.config import settings
from app.core.deps import SessionLocal
from app.models.gpu_monitoring import GPUInspectionRecord
from app.models.system_config import SystemConfig
from app.models.task import Task, TaskStatus, TaskType
from app.services.report_upload_service import get_report_upload_service
from app.services.task_service import save_task_to_db, update_task_status


DEFAULT_PROM_TOKEN = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJuYW1lc3BhY2UiOiJjcHJvbS1qNWkxMm94dXFqMXo3Iiwic2VjcmV0TmFtZSI6ImYwMDhkYjQ3NTE4OTRhZmU5Yjg1MWUzMmEyMDY4MzM1IiwiZXhwIjo0ODk3MjczNTI2LCJpc3MiOiJjcHJvbSJ9."
    "wbsW3Cs3PkTfgx_lsBHONGFqY7CFENSU-2NXChlT304"
)


class GPUMonitoringService:
    """GPU 集群监控相关服务"""

    STEP_TO_HOURS = {
        "1h": 1.0,
        "30m": 0.5,
        "15m": 0.25,
        "10m": 1 / 6,
        "5m": 1 / 12,
        "1m": 1 / 60,
    }

    def __init__(self):
        self.grafana_url = settings.GPU_GRAFANA_URL
        self.grafana_username = settings.GPU_GRAFANA_USERNAME
        self.grafana_password = settings.GPU_GRAFANA_PASSWORD
        self.prom_url = settings.GPU_PROM_URL
        self.prom_token = settings.GPU_PROM_TOKEN or os.getenv("PROM_TOKEN") or DEFAULT_PROM_TOKEN
        self.prom_instance_id = settings.GPU_PROM_INSTANCE_ID
        self.prom_cluster_id = settings.GPU_PROM_CLUSTER_ID
        self.prom_step = settings.GPU_PROM_STEP
        self.gpu_target_types = {
            item.strip() for item in settings.GPU_HAS_TARGET_GPU_TYPES.split(",") if item.strip()
        }

    def _load_runtime_prometheus_config(self) -> Dict[str, Any]:
        db = SessionLocal()
        try:
            runtime_record = db.query(SystemConfig).filter(
                SystemConfig.module == "prometheus_runtime",
                SystemConfig.config_key == "main",
            ).first()
            config = {}
            if runtime_record and runtime_record.config_value:
                config = json.loads(runtime_record.config_value)
            cluster_ids = config.get("cluster_ids") or ""
            if isinstance(cluster_ids, str):
                cluster_ids = [item.strip() for item in cluster_ids.split(",") if item.strip()]
            return {
                "grafana_url": config.get("grafana_url") or self.prom_url.rsplit("/api/v1/query_range", 1)[0],
                "token": config.get("token") or self.prom_token,
                "instance_id": config.get("instance_id") or self.prom_instance_id,
                "step": config.get("step") or self.prom_step,
                "cluster_ids": cluster_ids,
            }
        finally:
            db.close()

    def get_has_inspection_data(self, db: Session) -> Dict[str, Any]:
        """从主 MySQL 获取 HAS 自动化巡检实例数据"""
        rows = (
            db.query(GPUInspectionRecord)
            .order_by(
                GPUInspectionRecord.gpu_card.asc(),
                GPUInspectionRecord.has_alive.asc(),
                GPUInspectionRecord.instance_name.asc(),
            )
            .all()
        )

        collect_time = db.query(GPUInspectionRecord.source_updated_at).order_by(
            GPUInspectionRecord.source_updated_at.desc()
        ).first()
        collect_time = collect_time[0].isoformat(sep=" ") if collect_time and collect_time[0] else None

        instances = []
        summary = {
            "total": 0,
            "online": 0,
            "offline": 0,
            "gpu_cards": defaultdict(int),
            "regions": defaultdict(int),
        }

        for index, row in enumerate(rows, start=1):
            instance = {
                "index": index,
                "id": row.instance_id,
                "name": row.instance_name,
                "gpu_card": row.gpu_card or "Unknown",
                "internal_ip": row.internal_ip,
                "has_alive": row.has_alive or "unknown",
                "region": row.region or "-",
                "last_update": row.source_updated_at.isoformat(sep=" ") if row.source_updated_at else None,
            }
            instances.append(instance)

            summary["total"] += 1
            if instance["has_alive"] == "online":
                summary["online"] += 1
            else:
                summary["offline"] += 1
            summary["gpu_cards"][instance["gpu_card"]] += 1
            summary["regions"][instance["region"]] += 1

        summary["gpu_cards"] = dict(sorted(summary["gpu_cards"].items(), key=lambda item: item[0]))
        summary["regions"] = dict(sorted(summary["regions"].items(), key=lambda item: item[0]))

        return {
            "instances": instances,
            "collect_time": collect_time,
            "summary": summary,
            "grafana_url": self.grafana_url,
            "grafana_proxy_url": self.get_grafana_proxy_url(),
        }

    def create_has_sync_task(self, username: str = "system") -> str:
        """创建巡检数据同步任务"""
        task_id = f"gpu-has-sync-{uuid.uuid4().hex[:12]}"
        save_task_to_db(
            task_id=task_id,
            task_type=TaskType.GPU_HAS_SYNC,
            status=TaskStatus.PENDING,
            message="GPU HAS 巡检数据同步任务已创建",
            username=username,
        )
        return task_id

    def create_has_collect_task(self, username: str = "system") -> str:
        task_id = f"gpu-has-collect-{uuid.uuid4().hex[:12]}"
        save_task_to_db(
            task_id=task_id,
            task_type=TaskType.GPU_HAS_COLLECT,
            status=TaskStatus.PENDING,
            message="GPU HAS 巡检采集任务已创建",
            username=username,
        )
        return task_id

    def create_bottom_analysis_task(self, username: str = "system") -> str:
        task_id = f"gpu-bottom-{uuid.uuid4().hex[:12]}"
        save_task_to_db(
            task_id=task_id,
            task_type=TaskType.GPU_BOTTOM_ANALYSIS,
            status=TaskStatus.PENDING,
            message="GPU bottom卡时分析任务已创建",
            username=username,
        )
        return task_id

    def collect_has_inspection_to_mysql(self, task_id: str) -> None:
        """直接从 BCE 采集 HAS 巡检数据并写入主 MySQL"""
        db = SessionLocal()
        try:
            update_task_status(task_id, TaskStatus.PROCESSING, message="开始采集 GPU HAS 巡检数据", progress=10)

            client = self._get_bcc_client()
            response = client.list_instances(max_keys=1000)
            all_instances = getattr(response, "instances", []) or []
            instances = []
            for inst in all_instances:
                gpu = getattr(inst, "gpu_card", None)
                if gpu not in self.gpu_target_types:
                    continue
                instances.append(inst)

            total = len(instances)
            if total == 0:
                update_task_status(task_id, TaskStatus.COMPLETED, message="未采集到符合条件的 GPU HAS 数据", progress=100)
                return

            task = db.query(Task).filter(Task.id == task_id).first()
            if task:
                task.total_items = total
                task.completed_items = 0
                db.commit()

            imported = 0
            for inst in instances:
                service_components = getattr(inst, "service_components", None)
                has_alive = getattr(service_components, "has_alive", None) if service_components else None

                record = db.query(GPUInspectionRecord).filter(
                    GPUInspectionRecord.instance_id == inst.id
                ).first()

                if record is None:
                    record = GPUInspectionRecord(instance_id=inst.id)
                    db.add(record)

                record.instance_name = getattr(inst, "name", None) or inst.id
                record.gpu_card = getattr(inst, "gpu_card", None) or "Unknown"
                record.internal_ip = getattr(inst, "internal_ip", None)
                record.has_alive = has_alive or "unknown"
                record.region = settings.BCE_REGION or "cd"
                record.source_updated_at = datetime.now()

                imported += 1

                if imported % 50 == 0 or imported == total:
                    db.flush()
                    if task:
                        task.completed_items = imported
                        task.progress = min(95, int(imported / total * 100))
                        task.message = f"正在采集 GPU HAS 巡检数据 {imported}/{total}"
                        db.commit()

            if task:
                task.completed_items = total
                db.commit()

            update_task_status(
                task_id,
                TaskStatus.COMPLETED,
                message=f"GPU HAS 巡检数据采集完成，共 {total} 条",
                progress=100,
            )
        except Exception as exc:
            logger.error(f"采集 GPU HAS 巡检数据失败: {exc}")
            update_task_status(task_id, TaskStatus.FAILED, error_message=str(exc), message="GPU HAS 巡检数据采集失败")
            if db:
                db.rollback()
        finally:
            db.close()

    def run_bottom_analysis_task(
        self,
        task_id: str,
        start_time: datetime,
        end_time: datetime,
        cluster_ids: Optional[List[str]] = None,
        target_models: Optional[List[str]] = None,
        step: Optional[str] = None,
    ) -> None:
        """执行 bottom 卡时分析并上传报告到 MinIO"""
        try:
            update_task_status(task_id, TaskStatus.PROCESSING, message="开始分析 GPU bottom 卡时数据", progress=10)
            result = self.query_bottom_card_time(
                start_time=start_time,
                end_time=end_time,
                cluster_ids=cluster_ids,
                target_models=target_models,
                step=step,
            )
            update_task_status(task_id, TaskStatus.PROCESSING, message="GPU 卡时分析完成，正在生成报告", progress=65)

            html_content = self._build_bottom_analysis_html(result)

            def generate_excel(output_path: str) -> None:
                self._build_bottom_analysis_excel(result, output_path)

            upload_service = get_report_upload_service()
            uploaded = upload_service.upload_html_and_excel(
                task_id=task_id,
                html_content=html_content,
                excel_generator_func=generate_excel,
                report_type="gpu_bottom",
            )

            html_report = uploaded.get("html_report")
            result_url = f"/api/v1/reports/proxy/{html_report}" if html_report else None
            update_task_status(
                task_id,
                TaskStatus.COMPLETED,
                message="GPU bottom 卡时分析完成",
                result_url=result_url,
                progress=100,
            )
        except Exception as exc:
            logger.error(f"GPU bottom 卡时分析失败: {exc}")
            update_task_status(
                task_id,
                TaskStatus.FAILED,
                message="GPU bottom 卡时分析失败",
                error_message=str(exc),
            )

    def get_grafana_proxy_url(self) -> str:
        parsed = urlparse(self.grafana_url)
        path = parsed.path.lstrip("/")
        query = f"?{parsed.query}" if parsed.query else ""
        return f"/api/v1/gpu-monitoring/grafana-proxy/{path}{query}"

    def proxy_grafana(self, path: str, query_params: Dict[str, Any]) -> requests.Response:
        parsed = urlparse(self.grafana_url)
        normalized_path = "/" + path.lstrip("/")
        query_string = urlencode(query_params, doseq=True)
        upstream_url = urlunparse((
            parsed.scheme,
            parsed.netloc,
            normalized_path,
            "",
            query_string,
            "",
        ))

        response = requests.get(
            upstream_url,
            auth=(self.grafana_username, self.grafana_password),
            timeout=60,
            allow_redirects=True,
        )
        response.raise_for_status()
        return response

    def query_bottom_card_time(
        self,
        start_time: datetime,
        end_time: datetime,
        cluster_ids: Optional[List[str]] = None,
        target_models: Optional[List[str]] = None,
        step: Optional[str] = None,
    ) -> Dict[str, Any]:
        """按时间区间查询 GPU 卡时数据"""
        runtime_config = self._load_runtime_prometheus_config()
        actual_step = step or runtime_config["step"] or self.prom_step
        if actual_step not in self.STEP_TO_HOURS:
            raise ValueError(f"不支持的 step: {actual_step}")
        if end_time <= start_time:
            raise ValueError("结束时间必须大于开始时间")

        actual_cluster_ids = [cluster_id for cluster_id in (cluster_ids or runtime_config.get("cluster_ids") or [self.prom_cluster_id]) if cluster_id]
        if not actual_cluster_ids:
            raise ValueError("至少需要提供一个集群ID")

        results = []
        for cluster_id in actual_cluster_ids:
            results.extend(
                self._query_prometheus_range(
                    start=int(start_time.timestamp()),
                    end=int(end_time.timestamp()),
                    step=actual_step,
                    cluster_id=cluster_id,
                    runtime_config=runtime_config,
                )
            )

        start_ts = int(start_time.timestamp())
        end_ts   = int(end_time.timestamp())

        # 拉取 pod 元数据（start/completion/phase/gpu_requests）
        pod_meta: Dict[str, Any] = {"pod_start": {}, "pod_completion": {}, "pod_phase": {}, "pod_gpu_req": {}}
        for cluster_id in actual_cluster_ids:
            meta = self._fetch_pod_meta(start_ts, end_ts, cluster_id, runtime_config)
            for key in pod_meta:
                pod_meta[key].update(meta[key])

        pod_stats = self._calculate_pod_stats(results, actual_step, start_ts, end_ts, pod_meta)
        pods = self._format_pod_output(pod_stats)
        raw_pod_count = len(pods)
        bottom_pods = self._filter_bottom_pods(pods)
        namespaces = self._format_namespace_output(bottom_pods)
        model_summary = self._format_model_summary(bottom_pods, target_models or ["H800", "L20", "H20"])

        total_gpu_hours = round(sum(item["gpu_hours"] for item in pods), 2)
        total_bottom = round(sum(item["bottom"] for item in bottom_pods), 2)
        total_gpu_cards = sum(item["gpu_count"] for item in bottom_pods)
        avg_util = round(
            sum(item["avg_util_percent"] for item in bottom_pods) / len(bottom_pods),
            2,
        ) if bottom_pods else 0

        return {
            "summary": {
                "pod_count": len(bottom_pods),
                "raw_pod_count": raw_pod_count,
                "namespace_count": len(namespaces),
                "total_gpu_hours": total_gpu_hours,
                "total_bottom": total_bottom,
                "total_gpu_cards": total_gpu_cards,
                "avg_util_percent": avg_util,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "step": actual_step,
                "cluster_ids": actual_cluster_ids,
            },
            "model_summary": model_summary,
            "namespaces": namespaces,
            "pods": bottom_pods,
        }

    def _query_prometheus_range(self, start: int, end: int, step: str, cluster_id: str, runtime_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        query = f'DCGM_FI_DEV_GPU_UTIL{{clusterID="{cluster_id}", job_pod_namespace!=""}}'
        headers = {
            "Authorization": runtime_config["token"] if str(runtime_config["token"]).startswith("Bearer ") else f"Bearer {runtime_config['token']}",
            "InstanceId": runtime_config["instance_id"],
            "Content-Type": "application/json",
        }

        try:
            response = requests.get(
                f"{runtime_config['grafana_url'].rstrip('/')}/api/v1/query_range",
                headers=headers,
                params={
                    "query": query,
                    "start": start,
                    "end": end,
                    "step": step,
                },
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()
            if data.get("status") != "success":
                raise RuntimeError(data.get("error", "Prometheus 查询失败"))
            return data.get("data", {}).get("result", [])
        except requests.RequestException as exc:
            logger.error(f"GPU 卡时查询失败: {exc}")
            raise RuntimeError(f"Prometheus 请求失败: {exc}") from exc

    def _query_prometheus_range_chunked(self, query: str, start: int, end: int, step: str, runtime_config: Dict[str, Any], chunk_hours: int = 2) -> List[Dict[str, Any]]:
        """分段查询 Prometheus range，防止大时间范围 422 错误"""
        headers = {
            "Authorization": runtime_config["token"] if str(runtime_config["token"]).startswith("Bearer ") else f"Bearer {runtime_config['token']}",
            "InstanceId": runtime_config["instance_id"],
        }
        results = []
        cur = start
        while cur < end:
            nxt = min(cur + chunk_hours * 3600, end)
            try:
                r = requests.get(
                    f"{runtime_config['grafana_url'].rstrip('/')}/api/v1/query_range",
                    headers=headers,
                    params={"query": query, "start": cur, "end": nxt, "step": step},
                    timeout=60,
                )
                if r.status_code == 200:
                    results.extend(r.json().get("data", {}).get("result", []))
            except Exception as exc:
                logger.warning(f"分段查询失败 [{cur},{nxt}]: {exc}")
            cur = nxt
        return results

    def _fetch_pod_meta(self, start: int, end: int, cluster_id: str, runtime_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        拉取 pod 元数据：start_time / completion_time / status_phase / gpu_requests
        返回四个 dict，key 均为 pod 名称
        """
        step = "5m"

        def q(query):
            return self._query_prometheus_range_chunked(query, start, end, step, runtime_config)

        start_data      = q(f'kube_pod_start_time{{clusterID="{cluster_id}"}}')
        completion_data = q(f'kube_pod_completion_time{{clusterID="{cluster_id}"}}')
        status_data     = q(f'kube_pod_status_phase{{clusterID="{cluster_id}"}}')
        gpu_req_data    = q(f'kube_pod_container_resource_requests{{clusterID="{cluster_id}",resource="nvidia_com_gpu"}}')

        pod_start: Dict[str, float] = {}
        pod_completion: Dict[str, float] = {}
        pod_phase: Dict[str, str] = {}
        pod_gpu_req: Dict[str, float] = {}

        for r in start_data:
            pod = r['metric'].get('pod')
            if pod and r.get('values'):
                pod_start[pod] = float(r['values'][0][1])

        for r in completion_data:
            pod = r['metric'].get('pod')
            if pod and r.get('values'):
                pod_completion[pod] = float(r['values'][0][1])

        for r in status_data:
            pod = r['metric'].get('pod')
            phase = r['metric'].get('phase')
            vals = [v for v in r.get('values', []) if v[1] == "1"]
            if vals and pod:
                pod_phase[pod] = phase

        for r in gpu_req_data:
            pod = r['metric'].get('pod')
            if pod and r.get('values'):
                val = float(r['values'][-1][1])
                # 取最大值而非累加，避免多容器重复计算
                pod_gpu_req[pod] = max(pod_gpu_req.get(pod, 0), val)

        return {
            "pod_start": pod_start,
            "pod_completion": pod_completion,
            "pod_phase": pod_phase,
            "pod_gpu_req": pod_gpu_req,
        }

    @staticmethod
    def _is_valid_util(value: Any) -> bool:
        try:
            val = float(value)
            return 0 <= val <= 100
        except (TypeError, ValueError):
            return False

    def _calculate_pod_stats(
        self,
        results: List[Dict[str, Any]],
        step: str,
        start_ts: int,
        end_ts: int,
        pod_meta: Dict[str, Any],
    ) -> Dict[Any, Dict[str, Any]]:
        """
        聚合每个 pod 的利用率时间点，卡时改为：申请卡数 × 实际运行时长
        运行时长规则：
          - Succeeded/Failed → completion_time - start_time
          - Running/Pending/未知 → now(end_ts) - start_time
        """
        pod_start      = pod_meta["pod_start"]
        pod_completion = pod_meta["pod_completion"]
        pod_phase      = pod_meta["pod_phase"]
        pod_gpu_req    = pod_meta["pod_gpu_req"]

        pod_stats: Dict[Any, Dict[str, Any]] = defaultdict(
            lambda: {
                "time_point_utils": defaultdict(list),
                "models": set(),
                "gpu_indices": set(),
            }
        )

        for series in results:
            metric = series.get("metric", {})
            namespace = metric.get("job_pod_namespace") or metric.get("namespace")
            pod       = metric.get("job_pod_name")      or metric.get("pod")
            model     = metric.get("modelName", "Unknown")
            gpu_index = metric.get("gpu", "0")
            if not namespace or not pod:
                continue

            key = (namespace, pod)
            stats = pod_stats[key]
            stats["models"].add(model)
            stats["gpu_indices"].add(gpu_index)

            for timestamp, value in series.get("values", []):
                if self._is_valid_util(value):
                    stats["time_point_utils"][timestamp].append(float(value))

        # 计算卡时：申请卡数 × 运行时长（小时）
        for (namespace, pod), stats in pod_stats.items():
            s = pod_start.get(pod, start_ts)
            phase = pod_phase.get(pod)
            if phase in ("Succeeded", "Failed"):
                e = pod_completion.get(pod, end_ts)
            else:
                e = end_ts
            duration_hrs = max(0.0, min(e, end_ts) - max(s, start_ts)) / 3600.0

            gpu_cnt = pod_gpu_req.get(pod, 0)
            # 若 kube 指标未覆盖此 pod，退回到 DCGM 上报的卡数
            if gpu_cnt == 0:
                gpu_cnt = len(stats["gpu_indices"])

            stats["gpu_hours"] = round(duration_hrs * gpu_cnt, 2)
            stats["gpu_count"] = gpu_cnt

        return pod_stats

    def _format_pod_output(self, pod_stats: Dict[Any, Dict[str, Any]]) -> List[Dict[str, Any]]:
        pods = []
        for (namespace, pod), stats in pod_stats.items():
            avg_points = []
            for utils in stats["time_point_utils"].values():
                if utils:
                    avg_points.append(sum(utils) / len(utils))

            models = stats["models"]
            model_name = "Mixed" if len(models) > 1 else (next(iter(models)) if models else "Unknown")
            avg_util = round(sum(avg_points) / len(avg_points), 2) if avg_points else 0
            gpu_hours = stats.get("gpu_hours", 0.0)

            pods.append(
                {
                    "namespace": namespace,
                    "pod": pod,
                    "gpu_count": stats.get("gpu_count", len(stats["gpu_indices"])),
                    "model": model_name,
                    "avg_util_percent": avg_util,
                    "gpu_hours": gpu_hours,
                    "bottom": 0,
                }
            )

        # bottom 对所有 pod 先算出来，过滤在 _filter_bottom_pods 里做
        for item in pods:
            item["bottom"] = round(item["gpu_hours"] * (1 - item["avg_util_percent"] * 0.01), 2)

        pods.sort(key=lambda item: item["gpu_hours"], reverse=True)
        return pods

    @staticmethod
    def _filter_bottom_pods(pods: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        过滤规则（客户原需求）：
        1. 排除同时满足 avg_util > 70% AND gpu_hours < 100 的 pod（高效小任务）
        2. 去除剩余中利用率最高的前 10 个 pod（避免极端值影响）
        3. 按 bottom 降序排列
        """
        # Step1：排除同时满足"利用率>70% AND 卡时<100"的 pod（短时高效小任务）
        # 注意：两个条件必须同时成立才排除，任一条件不满足则保留
        filtered = [
            item for item in pods
            if not (item["avg_util_percent"] > 70 and item["gpu_hours"] < 100)
        ]

        # Step2：去除利用率前 10 个 pod
        if len(filtered) > 10:
            sorted_by_util = sorted(filtered, key=lambda x: x["avg_util_percent"], reverse=True)
            top10_pods = {item["pod"] for item in sorted_by_util[:10]}
            filtered = [item for item in filtered if item["pod"] not in top10_pods]

        # Step3：按 bottom 降序
        filtered.sort(key=lambda item: item["bottom"], reverse=True)
        return filtered

    @staticmethod
    def _format_namespace_output(pods: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        namespace_stats = defaultdict(lambda: {"total_gpus": 0, "pod_count": 0, "total_gpu_hours": 0.0, "total_bottom": 0.0, "total_util": 0.0})

        for item in pods:
            stats = namespace_stats[item["namespace"]]
            stats["total_gpus"] += item["gpu_count"]
            stats["pod_count"] += 1
            stats["total_gpu_hours"] += item["gpu_hours"]
            stats["total_bottom"] += item["bottom"]
            stats["total_util"] += item["avg_util_percent"]

        rows = [
            {
                "namespace": namespace,
                "total_gpus": stats["total_gpus"],
                "pod_count": stats["pod_count"],
                "total_gpu_hours": round(stats["total_gpu_hours"], 2),
                "total_bottom": round(stats["total_bottom"], 2),
                "avg_util_percent": round(stats["total_util"] / stats["pod_count"], 2) if stats["pod_count"] else 0,
            }
            for namespace, stats in namespace_stats.items()
        ]
        rows.sort(key=lambda item: item["total_bottom"], reverse=True)
        return rows

    @staticmethod
    def _format_model_summary(pods: List[Dict[str, Any]], target_models: List[str]) -> List[Dict[str, Any]]:
        target_lookup = [item.upper() for item in target_models]
        summary = defaultdict(lambda: {"total_gpus": 0, "pod_count": 0, "gpu_hours": 0.0, "bottom": 0.0, "total_util": 0.0})

        for item in pods:
            matched_model = item["model"]
            for target in target_lookup:
                if target in item["model"].upper():
                    matched_model = target
                    break
            summary[matched_model]["total_gpus"] += item["gpu_count"]
            summary[matched_model]["pod_count"] += 1
            summary[matched_model]["gpu_hours"] += item["gpu_hours"]
            summary[matched_model]["bottom"] += item["bottom"]
            summary[matched_model]["total_util"] += item["avg_util_percent"]

        rows = [
            {
                "model": model,
                "total_gpus": values["total_gpus"],
                "pod_count": values["pod_count"],
                "avg_util_percent": round(values["total_util"] / values["pod_count"], 2) if values["pod_count"] else 0,
                "gpu_hours": round(values["gpu_hours"], 2),
                "bottom": round(values["bottom"], 2),
            }
            for model, values in summary.items()
        ]
        rows.sort(key=lambda item: item["bottom"], reverse=True)
        return rows

    @staticmethod
    def _build_bottom_analysis_excel(result: Dict[str, Any], output_path: str) -> None:
        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            pd.DataFrame(result.get("model_summary", [])).to_excel(writer, sheet_name="型号汇总", index=False)
            pd.DataFrame(result.get("namespaces", [])).to_excel(writer, sheet_name="队列汇总", index=False)
            pd.DataFrame(result.get("pods", [])).to_excel(writer, sheet_name="Pod明细", index=False)

    @staticmethod
    def _build_bottom_analysis_html(result: Dict[str, Any]) -> str:
        summary = result.get("summary", {})
        model_df = pd.DataFrame(result.get("model_summary", []))
        namespace_df = pd.DataFrame(result.get("namespaces", []))
        pod_df = pd.DataFrame(result.get("pods", []))

        def render_table(df: pd.DataFrame) -> str:
            if df.empty:
                return '<div class="empty">暂无数据</div>'
            return df.to_html(index=False, classes="report-table", border=0)

        return f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>GPU bottom 卡时分析报告</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 0; padding: 32px; background: #f5f7fb; color: #1f2937; }}
    .page {{ max-width: 1400px; margin: 0 auto; }}
    .hero {{ background: #fff; border-radius: 16px; padding: 28px 32px; box-shadow: 0 10px 30px rgba(15, 23, 42, 0.08); margin-bottom: 24px; }}
    .title {{ font-size: 28px; font-weight: 700; margin-bottom: 8px; }}
    .subtitle {{ color: #6b7280; margin-bottom: 0; }}
    .stats {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 16px; margin: 24px 0; }}
    .stat {{ background: #fff; border-radius: 16px; padding: 20px; box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06); }}
    .stat-label {{ color: #6b7280; font-size: 13px; margin-bottom: 10px; }}
    .stat-value {{ font-size: 28px; font-weight: 700; }}
    .section {{ background: #fff; border-radius: 16px; padding: 24px; box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06); margin-bottom: 24px; }}
    .section h2 {{ margin: 0 0 16px; font-size: 20px; }}
    .report-table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
    .report-table th, .report-table td {{ padding: 12px 14px; border-bottom: 1px solid #e5e7eb; text-align: left; }}
    .report-table th {{ background: #f8fafc; color: #475569; font-weight: 600; }}
    .empty {{ color: #94a3b8; padding: 12px 0; }}
    @media (max-width: 960px) {{ .stats {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }} body {{ padding: 18px; }} }}
  </style>
</head>
<body>
  <div class="page">
    <div class="hero">
      <div class="title">GPU bottom 卡时分析报告</div>
      <p class="subtitle">统计区间：{summary.get("start_time", "-")} 至 {summary.get("end_time", "-")} | 步长：{summary.get("step", "-")} | 集群：{", ".join(summary.get("cluster_ids", []) or ["-"])} | 已过滤利用率&gt;70% 且 卡时&lt;100 的记录，并去除利用率前10的Pod</p>
    </div>

    <div class="stats">
      <div class="stat"><div class="stat-label">Bottom Pod 数量</div><div class="stat-value">{summary.get("pod_count", 0)}</div></div>
      <div class="stat"><div class="stat-label">队列数量</div><div class="stat-value">{summary.get("namespace_count", 0)}</div></div>
      <div class="stat"><div class="stat-label">总卡时</div><div class="stat-value">{summary.get("total_gpu_hours", 0)}</div></div>
      <div class="stat"><div class="stat-label">总 Bottom</div><div class="stat-value">{summary.get("total_bottom", 0)}</div></div>
    </div>

    <div class="section">
      <h2>GPU 型号卡时汇总</h2>
      {render_table(model_df)}
    </div>

    <div class="section">
      <h2>队列汇总</h2>
      {render_table(namespace_df)}
    </div>

    <div class="section">
      <h2>Pod 卡时明细</h2>
      {render_table(pod_df)}
    </div>
  </div>
</body>
</html>
"""

    @staticmethod
    def _get_bcc_client():
        from baidubce.services.bcc.bcc_client import BccClient
        from baidubce.bce_client_configuration import BceClientConfiguration
        from baidubce.auth.bce_credentials import BceCredentials

        access_key = settings.BCE_ACCESS_KEY
        secret_key = settings.BCE_SECRET_KEY

        if not access_key or not secret_key:
            db = SessionLocal()
            try:
                config_record = db.query(SystemConfig).filter(
                    SystemConfig.module == "monitoring",
                    SystemConfig.config_key == "main"
                ).first()
                if config_record and config_record.config_value:
                    config = json.loads(config_record.config_value)
                    access_key = config.get("bce_access_key") or config.get("ak") or access_key
                    secret_key = config.get("bce_secret_key") or config.get("sk") or secret_key
            finally:
                db.close()

        if not access_key or not secret_key:
            raise RuntimeError("未配置可复用的 BCE_ACCESS_KEY / BCE_SECRET_KEY，无法执行 HAS 巡检采集")

        endpoint = f"https://bcc.{settings.BCE_REGION}.baidubce.com"
        config = BceClientConfiguration(
            credentials=BceCredentials(access_key, secret_key),
            endpoint=endpoint,
        )
        return BccClient(config)


gpu_monitoring_service = GPUMonitoringService()
