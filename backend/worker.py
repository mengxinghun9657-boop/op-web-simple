#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
后台 Worker 入口
负责承接常驻后台任务：
1. 定时调度器（CMDB / APIServer）
2. 告警文件监控
"""
import os
import signal
import threading
import time
from datetime import datetime

from app.core.config import ensure_directories
from app.core.database import SessionLocal
from app.core.logger import setup_logging
from app.core.scheduler import init_scheduler, shutdown_scheduler
from app.services.task_queue_service import task_queue_service
from loguru import logger


shutdown_event = threading.Event()


def _wait_mysql_ready(timeout_seconds: int = 360) -> bool:
    check_interval = 5
    for _ in range(0, timeout_seconds, check_interval):
        try:
            from sqlalchemy import text
            db = SessionLocal()
            db.execute(text("SELECT 1"))
            db.close()
            return True
        except Exception:
            time.sleep(check_interval)
    return False


def _run_file_watcher():
    alerts_source_path = "/app/alerts_source"
    if not os.path.exists(alerts_source_path):
        logger.info(f"ℹ️ 告警源目录不存在({alerts_source_path})，Worker 跳过文件监控")
        return None

    logger.info("⏳ Worker 等待 MySQL 就绪后启动文件监控...")
    _wait_mysql_ready()

    from app.services.alert.file_watcher import FileWatcherService

    watcher = FileWatcherService()
    watcher.process_existing_files()
    watcher.start_monitoring()
    logger.info("✅ Worker 文件监控已启动")
    return watcher


def _handle_shutdown(signum, frame):
    logger.info(f"收到退出信号: {signum}")
    shutdown_event.set()


def main():
    setup_logging()
    ensure_directories()
    signal.signal(signal.SIGTERM, _handle_shutdown)
    signal.signal(signal.SIGINT, _handle_shutdown)

    logger.info("🚀 后台 Worker 启动中...")
    init_scheduler()
    logger.info("✅ Worker 调度器已启动")

    watcher = None
    try:
        if os.getenv("ENABLE_FILE_WATCHER", "true").lower() == "true":
            watcher = _run_file_watcher()

        handlers = {
            "resource_analysis": _handle_resource_analysis,
            "gpu_bottom_analysis": _handle_gpu_bottom_analysis,
            "apiserver_alert_analysis": _handle_apiserver_analysis,
            "pfs_export": _handle_pfs_export,
            "gpu_has_inspection_collect": _handle_gpu_has_inspection_collect,
            "prometheus_batch_collect": _handle_prometheus_batch_collect,
            "operational_excel_analysis": _handle_operational_excel_analysis,
            "operational_api_analysis": _handle_operational_api_analysis,
        }

        while not shutdown_event.is_set():
            consumed = task_queue_service.consume_one(handlers, timeout=5)
            if not consumed:
                time.sleep(1)
    finally:
        if watcher:
            try:
                watcher.stop()
            except Exception as exc:
                logger.warning(f"停止文件监控失败: {exc}")
        shutdown_scheduler()
        logger.info("✅ 后台 Worker 已退出")


def _handle_resource_analysis(payload):
    from app.api.v1.resource import run_resource_analysis
    import asyncio

    return asyncio.run(
        run_resource_analysis(
            task_id=payload["task_id"],
            cluster_ids=payload.get("cluster_ids"),
            excel_file_path=payload.get("excel_file_path"),
            multicluster_file_path=payload.get("multicluster_file_path"),
        )
    )


def _handle_gpu_bottom_analysis(payload):
    from app.services.gpu_monitoring_service import gpu_monitoring_service

    return gpu_monitoring_service.run_bottom_analysis_task(
        payload["task_id"],
        datetime.fromisoformat(payload["start_time"]),
        datetime.fromisoformat(payload["end_time"]),
        payload.get("cluster_ids"),
        payload.get("target_models"),
        payload.get("step"),
    )


def _handle_apiserver_analysis(payload):
    from app.core.deps import SessionLocal
    from app.services.apiserver_alert_service import APIServerAlertService

    db = SessionLocal()
    try:
        service = APIServerAlertService(db)
        return service.run_scan_task(payload["task_id"])
    finally:
        db.close()


def _handle_pfs_export(payload):
    from app.api.v1.pfs import process_pfs_export_task
    from app.models.pfs import PFSExportRequest

    request = PFSExportRequest(**payload["request"])
    return process_pfs_export_task(
        task_id=payload["task_id"],
        request=request,
        user_id=payload["user_id"],
        username=payload["username"],
    )


def _handle_gpu_has_inspection_collect(payload):
    from app.services.gpu_monitoring_service import gpu_monitoring_service

    return gpu_monitoring_service.collect_has_inspection_to_mysql(payload["task_id"])


def _handle_prometheus_batch_collect(payload):
    from app.api.v1.prometheus import batch_fetch_cluster_metrics

    return batch_fetch_cluster_metrics(
        task_id=payload["task_id"],
        cluster_ids=payload["cluster_ids"],
    )


def _handle_operational_excel_analysis(payload):
    from app.api.v1.operational import process_analysis
    import asyncio

    return asyncio.run(
        process_analysis(
            task_id=payload["task_id"],
            file_path=payload["file_path"],
            file_name=payload["file_name"],
        )
    )


def _handle_operational_api_analysis(payload):
    from app.api.v1.operational import process_api_analysis, AnalyzeAPIRequest
    import asyncio

    request = AnalyzeAPIRequest(
        spacecode=payload["spacecode"],
        username=payload["username"],
        password=payload["password"],
        iql=payload["iql"],
        page=payload.get("page", 1),
        pgcount=payload.get("pgcount", 100),
    )
    return asyncio.run(process_api_analysis(task_id=payload["task_id"], request=request))


if __name__ == "__main__":
    main()
