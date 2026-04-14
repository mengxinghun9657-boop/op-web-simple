"""
APIServer 监控告警服务
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.core.config import settings
from app.core.logger import logger
from app.models.alert import WebhookConfig
from app.models.apiserver_alert import APIServerAlertRecord
from app.models.system_config import SystemConfig
from app.models.task import TaskType, TaskStatus
from app.services.task_service import save_task_to_db, update_task_status
from app.core.deps import SessionLocal
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


@dataclass
class Rule:
    key: str
    label: str
    promql_template: str
    comparator: str
    warning_threshold: float
    critical_threshold: float
    unit: str
    description: str
    suggestion: str


DEFAULT_RULES: List[Rule] = [
    Rule(
        key="api_qps",
        label="API QPS",
        promql_template='sum(rate(apiserver_request_total{{clusterID=~"{cluster_id}",verb!~"WATCH|CONNECT"}}[{window}m]))',
        comparator="gt",
        warning_threshold=500,
        critical_threshold=1000,
        unit="qps",
        description="APIServer 请求量持续过高，可能影响控制面稳定性。",
        suggestion="检查高频调用来源、控制器行为以及是否存在异常重试。",
    ),
    Rule(
        key="read_success_rate",
        label="读请求成功率(GET+LIST)",
        promql_template='sum(rate(apiserver_request_total{{clusterID=~"{cluster_id}",verb=~"GET|LIST",code=~"2..|3.."}}[{window}m])) / clamp_min(sum(rate(apiserver_request_total{{clusterID=~"{cluster_id}",verb=~"GET|LIST"}}[{window}m])), 0.0001) * 100',
        comparator="lt",
        warning_threshold=99,
        critical_threshold=95,
        unit="%",
        description="读请求成功率下降，可能存在控制面异常或后端依赖问题。",
        suggestion="检查 apiserver 错误日志、etcd 状态和网络连通性。",
    ),
    Rule(
        key="write_success_rate",
        label="写请求成功率",
        promql_template='sum(rate(apiserver_request_total{{clusterID=~"{cluster_id}",verb=~"POST|PUT|PATCH|DELETE",code=~"2..|3.."}}[{window}m])) / clamp_min(sum(rate(apiserver_request_total{{clusterID=~"{cluster_id}",verb=~"POST|PUT|PATCH|DELETE"}}[{window}m])), 0.0001) * 100',
        comparator="lt",
        warning_threshold=99,
        critical_threshold=95,
        unit="%",
        description="写请求成功率下降，可能影响资源变更与控制器调谐。",
        suggestion="检查 admission webhook、etcd 延迟以及 apiserver 异常返回。",
    ),
    Rule(
        key="read_inflight",
        label="在处理的读请求数量",
        promql_template='sum(apiserver_current_inflight_requests{{clusterID=~"{cluster_id}",request_kind="readOnly"}})',
        comparator="gt",
        warning_threshold=200,
        critical_threshold=400,
        unit="count",
        description="读请求并发过高，可能导致 apiserver 排队与响应抖动。",
        suggestion="检查热点资源查询、监控抓取频率和异常 watch/list 行为。",
    ),
    Rule(
        key="write_inflight",
        label="在处理的写请求数量",
        promql_template='sum(apiserver_current_inflight_requests{{clusterID=~"{cluster_id}",request_kind="mutating"}})',
        comparator="gt",
        warning_threshold=50,
        critical_threshold=100,
        unit="count",
        description="写请求并发过高，可能影响资源创建、更新和删除。",
        suggestion="检查批量写入来源、控制器抖动和 webhook 响应时间。",
    ),
    Rule(
        key="get_p50_latency",
        label="GET 读请求时延 P50",
        promql_template='histogram_quantile(0.5, sum by (le) (rate(apiserver_request_duration_seconds_bucket{{clusterID=~"{cluster_id}",verb="GET"}}[{window}m])))',
        comparator="gt",
        warning_threshold=0.3,
        critical_threshold=0.8,
        unit="s",
        description="GET 请求中位时延升高，说明读路径已受到明显影响。",
        suggestion="检查 etcd 延迟、apiserver 负载和网络抖动。",
    ),
    Rule(
        key="list_p50_latency",
        label="LIST 读请求时延 P50",
        promql_template='histogram_quantile(0.5, sum by (le) (rate(apiserver_request_duration_seconds_bucket{{clusterID=~"{cluster_id}",verb="LIST"}}[{window}m])))',
        comparator="gt",
        warning_threshold=0.8,
        critical_threshold=1.5,
        unit="s",
        description="LIST 请求中位时延升高，可能由大对象列表或 watch cache 压力导致。",
        suggestion="检查大规模列表请求、watch cache 命中率及资源对象数量。",
    ),
    Rule(
        key="write_p50_latency",
        label="写请求时延 P50",
        promql_template='histogram_quantile(0.5, sum by (le) (rate(apiserver_request_duration_seconds_bucket{{clusterID=~"{cluster_id}",verb=~"POST|PUT|PATCH|DELETE"}}[{window}m])))',
        comparator="gt",
        warning_threshold=0.5,
        critical_threshold=1.2,
        unit="s",
        description="写请求中位时延升高，可能影响变更生效与控制面稳定。",
        suggestion="检查 mutating webhook、etcd 写路径和 apiserver 资源使用。",
    ),
    Rule(
        key="watch_pressure",
        label="WATCH 压力",
        promql_template='sum(rate(apiserver_request_total{{clusterID=~"{cluster_id}",verb="WATCH"}}[{window}m]))',
        comparator="gt",
        warning_threshold=200,
        critical_threshold=500,
        unit="qps",
        description="WATCH 压力过高，容易引发 watch cache、连接数与控制面负担上升。",
        suggestion="检查异常 watch 客户端、控制器重连与热点资源。",
    ),
]


class APIServerAlertService:
    def __init__(self, db: Session):
        self.db = db

    def _load_config(self) -> Dict[str, Any]:
        config_record = self.db.query(SystemConfig).filter(
            SystemConfig.module == "apiserver",
            SystemConfig.config_key == "main",
        ).first()
        config = {}
        if config_record and config_record.config_value:
            config = json.loads(config_record.config_value)

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

        merged = {
            "grafana_url": runtime_config.get("grafana_url") or settings.APISERVER_PROM_URL,
            "token": runtime_config.get("token") or settings.APISERVER_PROM_TOKEN,
            "instance_id": runtime_config.get("instance_id") or settings.APISERVER_PROM_INSTANCE_ID,
            "step": runtime_config.get("step") or "5m",
            "auto_check_enabled": bool(config.get("auto_check_enabled", False)),
            "check_interval_minutes": int(config.get("check_interval_minutes") or 10),
            "window_minutes": int(config.get("window_minutes") or settings.APISERVER_DEFAULT_WINDOW_MINUTES),
            "cluster_ids": cluster_ids,
            "rules": config.get("rules") or {},
        }
        return merged

    def _query_instant(self, promql: str, config: Dict[str, Any]) -> Optional[float]:
        url = f"{config['grafana_url'].rstrip('/')}/api/v1/query"
        headers = {
            "Authorization": config['token'] if str(config['token']).startswith("Bearer ") else f"Bearer {config['token']}",
            "InstanceId": config["instance_id"],
        }
        try:
            resp = requests.get(url, headers=headers, params={"query": promql}, timeout=30, verify=False)
            resp.raise_for_status()
            data = resp.json()
            results = data.get("data", {}).get("result", [])
            if not results:
                return None
            value = results[0].get("value", [None, None])[1]
            return float(value) if value is not None else None
        except Exception as exc:
            logger.error(f"APIServer Prometheus 查询失败: {promql}, error={exc}")
            return None

    def _get_rules(self) -> List[Rule]:
        config = self._load_config()
        raw_rules = config.get("rules") or {}
        # 兼容前端传入的 list 格式，转为 {key: override} 的 dict
        if isinstance(raw_rules, list):
            rule_overrides = {r["key"]: r for r in raw_rules if isinstance(r, dict) and "key" in r}
        else:
            rule_overrides = raw_rules
        rules = []
        for rule in DEFAULT_RULES:
            override = rule_overrides.get(rule.key, {})
            if override.get("enabled", True) is False:
                continue
            rules.append(
                Rule(
                    key=rule.key,
                    label=override.get("label", rule.label),
                    promql_template=rule.promql_template,
                    comparator=rule.comparator,
                    warning_threshold=float(override.get("warning_threshold", rule.warning_threshold)),
                    critical_threshold=float(override.get("critical_threshold", rule.critical_threshold)),
                    unit=rule.unit,
                    description=override.get("description", rule.description),
                    suggestion=override.get("suggestion", rule.suggestion),
                )
            )
        return rules

    def create_scan_task(self, username: str = "system") -> str:
        task_id = f"apiserver-alert-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        save_task_to_db(
            task_id=task_id,
            task_type=TaskType.APISERVER_ALERT_ANALYSIS,
            status=TaskStatus.PENDING,
            message="APIServer 告警分析任务已创建",
            username=username,
        )
        return task_id

    def run_scan_task(self, task_id: str) -> None:
        db = SessionLocal()
        service = APIServerAlertService(db)
        try:
            config = service._load_config()
            cluster_ids = config.get("cluster_ids") or []
            if not cluster_ids:
                raise RuntimeError("未配置 APIServer 监控集群ID")

            rules = service._get_rules()
            total = len(cluster_ids) * len(rules)
            processed = 0
            active_fingerprints = []
            update_task_status(task_id, TaskStatus.PROCESSING, message="开始扫描 APIServer 指标", progress=5)

            for cluster_id in cluster_ids:
                for rule in rules:
                    promql = rule.promql_template.format(cluster_id=cluster_id, window=config["window_minutes"])
                    value = service._query_instant(promql, config)
                    processed += 1
                    update_task_status(
                        task_id,
                        TaskStatus.PROCESSING,
                        message=f"正在检测 {cluster_id} - {rule.label}",
                        progress=min(90, int(processed / max(total, 1) * 100)),
                    )
                    if value is None:
                        continue

                    severity = service._evaluate(rule, value)
                    if not severity:
                        continue

                    fingerprint = hashlib.md5(f"{cluster_id}:{rule.key}".encode("utf-8")).hexdigest()
                    active_fingerprints.append(fingerprint)
                    record = db.query(APIServerAlertRecord).filter(APIServerAlertRecord.fingerprint == fingerprint).first()
                    if not record:
                        record = APIServerAlertRecord(fingerprint=fingerprint)
                        db.add(record)

                    record.cluster_id = cluster_id
                    record.metric_key = rule.key
                    record.metric_label = rule.label
                    record.severity = severity
                    record.status = "active"
                    record.current_value = value
                    record.warning_threshold = rule.warning_threshold
                    record.critical_threshold = rule.critical_threshold
                    record.unit = rule.unit
                    record.window_minutes = f"{config['window_minutes']}m"
                    record.promql = promql
                    record.description = rule.description
                    record.suggestion = rule.suggestion
                    record.labels = {"cluster_id": cluster_id}
                    record.last_seen_at = datetime.now()
                    record.resolved_at = None
                    if not record.notified:
                        record.notified = "false"

            if cluster_ids:
                unresolved = db.query(APIServerAlertRecord).filter(
                    APIServerAlertRecord.cluster_id.in_(cluster_ids),
                    APIServerAlertRecord.status == "active",
                ).all()
                for record in unresolved:
                    if record.fingerprint not in active_fingerprints:
                        record.status = "resolved"
                        record.resolved_at = datetime.now()

            db.commit()
            service._send_webhooks()

            active_count = db.query(APIServerAlertRecord).filter(
                APIServerAlertRecord.cluster_id.in_(cluster_ids),
                APIServerAlertRecord.status == "active",
            ).count()
            update_task_status(task_id, TaskStatus.COMPLETED, message=f"扫描完成，当前活跃告警 {active_count} 条", progress=100)
        except Exception as exc:
            logger.error(f"APIServer 告警扫描失败: {exc}")
            update_task_status(task_id, TaskStatus.FAILED, message="APIServer 告警扫描失败", error_message=str(exc))
            db.rollback()
        finally:
            db.close()

    def _evaluate(self, rule: Rule, value: float) -> Optional[str]:
        if rule.comparator == "gt":
            if value >= rule.critical_threshold:
                return "critical"
            if value >= rule.warning_threshold:
                return "warning"
        else:
            if value <= rule.critical_threshold:
                return "critical"
            if value <= rule.warning_threshold:
                return "warning"
        return None

    def _send_webhooks(self) -> None:
        active_records = self.db.query(APIServerAlertRecord).filter(
            APIServerAlertRecord.status == "active",
            or_(APIServerAlertRecord.notified == "false", APIServerAlertRecord.notified.is_(None))
        ).all()
        if not active_records:
            return
        webhooks = self.db.query(WebhookConfig).filter(WebhookConfig.enabled == True).all()
        if not webhooks:
            return

        for webhook in webhooks:
            for record in active_records:
                if webhook.severity_filter:
                    allowed = [item.strip().lower() for item in webhook.severity_filter.split(",")]
                    if record.severity not in allowed and not ((record.severity == "critical" and "critical" in allowed) or (record.severity == "warning" and "warning" in allowed)):
                        continue
                if webhook.component_filter:
                    allowed_components = [item.strip() for item in webhook.component_filter.split(",")]
                    if "APIServer" not in allowed_components and "apiserver" not in [x.lower() for x in allowed_components]:
                        continue
                try:
                    self._send_webhook(webhook, {
                        "cluster_id": record.cluster_id,
                        "metric_label": record.metric_label,
                        "severity": record.severity,
                        "current_value": record.current_value,
                        "warning_threshold": record.warning_threshold,
                        "critical_threshold": record.critical_threshold,
                        "unit": record.unit,
                        "description": record.description,
                        "suggestion": record.suggestion,
                        "promql": record.promql,
                    })
                    record.notified = "true"
                    record.notified_at = datetime.now()
                except Exception as exc:
                    logger.error(f"发送 APIServer 告警 Webhook 失败: {exc}")
        self.db.commit()

    def _send_webhook(self, webhook: WebhookConfig, row: Dict[str, Any]) -> None:
        title = f"APIServer 告警 - {row['metric_label']}"
        content = (
            f"集群: {row['cluster_id']}\n"
            f"级别: {row['severity']}\n"
            f"当前值: {row['current_value']} {row['unit']}\n"
            f"阈值: W={row['warning_threshold']}, C={row['critical_threshold']}\n"
            f"说明: {row['description']}\n"
            f"建议: {row['suggestion']}\n"
            f"PromQL: {row['promql']}"
        )
        if webhook.type == "feishu":
            payload = {
                "msg_type": "interactive",
                "card": {
                    "header": {"title": {"tag": "plain_text", "content": title}, "template": "red" if row["severity"] == "critical" else "orange"},
                    "elements": [{"tag": "div", "text": {"tag": "lark_md", "content": content.replace("\n", "\n\n")}}],
                },
            }
        else:
            payload = {"group_id": webhook.group_id, "msg": f"{title}\n{content}"}
        requests.post(webhook.url, json=payload, timeout=20)

    def list_alerts(self, page: int, page_size: int, cluster_id: Optional[str], severity: Optional[str], status: Optional[str]) -> Dict[str, Any]:
        query = self.db.query(APIServerAlertRecord).order_by(APIServerAlertRecord.updated_at.desc())
        if cluster_id:
            query = query.filter(APIServerAlertRecord.cluster_id == cluster_id)
        if severity:
            query = query.filter(APIServerAlertRecord.severity == severity)
        if status:
            query = query.filter(APIServerAlertRecord.status == status)
        total = query.count()
        rows = query.offset((page - 1) * page_size).limit(page_size).all()
        return {"list": rows, "total": total, "page": page, "page_size": page_size}

    def get_stats(self) -> Dict[str, Any]:
        records = self.db.query(APIServerAlertRecord).all()
        active = [r for r in records if r.status == "active"]
        return {
            "total": len(records),
            "active": len(active),
            "critical": len([r for r in active if r.severity == "critical"]),
            "warning": len([r for r in active if r.severity == "warning"]),
            "clusters": len({r.cluster_id for r in active}),
        }

    def get_config(self) -> Dict[str, Any]:
        config = self._load_config()
        raw_rules = config.get("rules") or {}
        # 兼容前端传入的 list 格式，转为 {key: override} 的 dict
        if isinstance(raw_rules, list):
            rule_overrides = {r["key"]: r for r in raw_rules if isinstance(r, dict) and "key" in r}
        else:
            rule_overrides = raw_rules
        rules = []
        for rule in DEFAULT_RULES:
            override = rule_overrides.get(rule.key, {})
            rules.append({
                "key": rule.key,
                "label": override.get("label", rule.label),
                "enabled": override.get("enabled", True),
                "warning_threshold": override.get("warning_threshold", rule.warning_threshold),
                "critical_threshold": override.get("critical_threshold", rule.critical_threshold),
                "unit": rule.unit,
                "description": override.get("description", rule.description),
                "suggestion": override.get("suggestion", rule.suggestion),
            })
        return {
            "auto_check_enabled": config.get("auto_check_enabled", False),
            "check_interval_minutes": config.get("check_interval_minutes", 10),
            "window_minutes": config.get("window_minutes", settings.APISERVER_DEFAULT_WINDOW_MINUTES),
            "rules": rules,
        }

    def save_config(self, payload: Dict[str, Any], user_id: Optional[int] = None) -> Dict[str, Any]:
        record = self.db.query(SystemConfig).filter(
            SystemConfig.module == "apiserver",
            SystemConfig.config_key == "main",
        ).first()
        config_value = json.dumps(payload, ensure_ascii=False)
        if record:
            record.config_value = config_value
            record.updated_by = user_id
        else:
            record = SystemConfig(
                module="apiserver",
                config_key="main",
                config_value=config_value,
                updated_by=user_id,
            )
            self.db.add(record)
        self.db.commit()
        return payload

    def get_monitoring_overview(self, period_hours: int = 24) -> Dict[str, Any]:
        since = datetime.now() - timedelta(hours=period_hours)
        query = self.db.query(APIServerAlertRecord).filter(APIServerAlertRecord.created_at >= since)
        records = query.all()
        active = [r for r in records if r.status == "active"]

        bucket = "hour" if period_hours <= 48 else "day"
        timeline_map: Dict[str, Dict[str, int]] = {}
        for record in records:
            key = record.created_at.strftime("%Y-%m-%d %H:00") if bucket == "hour" else record.created_at.strftime("%Y-%m-%d")
            slot = timeline_map.setdefault(key, {"critical": 0, "warning": 0})
            if record.severity in slot:
                slot[record.severity] += 1

        timeline = [
            {"time": key, "critical": value["critical"], "warning": value["warning"]}
            for key, value in sorted(timeline_map.items())
        ]

        metric_distribution: Dict[str, int] = {}
        cluster_distribution: Dict[str, int] = {}
        for record in active:
            metric_distribution[record.metric_label] = metric_distribution.get(record.metric_label, 0) + 1
            cluster_distribution[record.cluster_id] = cluster_distribution.get(record.cluster_id, 0) + 1

        return {
            "summary": {
                "total": len(records),
                "active": len(active),
                "critical": len([r for r in active if r.severity == "critical"]),
                "warning": len([r for r in active if r.severity == "warning"]),
            },
            "timeline": timeline,
            "metric_distribution": [{"name": k, "value": v} for k, v in sorted(metric_distribution.items(), key=lambda item: item[1], reverse=True)],
            "cluster_distribution": [{"name": k, "value": v} for k, v in sorted(cluster_distribution.items(), key=lambda item: item[1], reverse=True)],
        }


def serialize_record(record: APIServerAlertRecord) -> Dict[str, Any]:
    return {
        "id": record.id,
        "cluster_id": record.cluster_id,
        "metric_key": record.metric_key,
        "metric_label": record.metric_label,
        "severity": record.severity,
        "status": record.status,
        "current_value": record.current_value,
        "warning_threshold": record.warning_threshold,
        "critical_threshold": record.critical_threshold,
        "unit": record.unit,
        "window_minutes": record.window_minutes,
        "promql": record.promql,
        "description": record.description,
        "suggestion": record.suggestion,
        "labels": record.labels,
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "updated_at": record.updated_at.isoformat() if record.updated_at else None,
        "resolved_at": record.resolved_at.isoformat() if record.resolved_at else None,
        "resolved_by": record.resolved_by,
        "resolution_notes": record.resolution_notes,
        "resolution_result": record.resolution_result,
        "icafe_card_id": record.icafe_card_id,
    }
