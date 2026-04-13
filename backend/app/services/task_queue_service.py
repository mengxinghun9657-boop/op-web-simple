"""
Redis 任务队列服务
用于将长任务从 API 进程剥离到 worker 消费
"""
from __future__ import annotations

import asyncio
import json
from typing import Any, Callable, Dict, Optional

from app.core.logger import logger
from app.core.redis_client import get_redis_client


QUEUE_KEYS = {
    "resource_analysis": "queue:resource_analysis",
    "gpu_bottom_analysis": "queue:gpu_bottom_analysis",
    "apiserver_alert_analysis": "queue:apiserver_alert_analysis",
    "pfs_export": "queue:pfs_export",
    "gpu_has_inspection_collect": "queue:gpu_has_inspection_collect",
    "prometheus_batch_collect": "queue:prometheus_batch_collect",
    "operational_excel_analysis": "queue:operational_excel_analysis",
    "operational_api_analysis": "queue:operational_api_analysis",
}


class TaskQueueService:
    def __init__(self):
        self.redis = get_redis_client()

    def enqueue(self, queue_name: str, payload: Dict[str, Any]) -> bool:
        queue_key = QUEUE_KEYS[queue_name]
        ok = self.redis.lpush(queue_key, payload)
        if ok:
            logger.info(f"任务已入队: {queue_key}")
        return ok

    def consume_one(self, handlers: Dict[str, Callable[[Dict[str, Any]], Any]], timeout: int = 5) -> bool:
        result = self.redis.brpop(list(QUEUE_KEYS.values()), timeout=timeout)
        if not result:
            return False

        queue_key, payload_raw = result
        payload = json.loads(payload_raw) if isinstance(payload_raw, str) else payload_raw
        queue_name = next((name for name, key in QUEUE_KEYS.items() if key == queue_key), None)
        if not queue_name or queue_name not in handlers:
            logger.warning(f"未知队列或未注册处理器: {queue_key}")
            return True

        handler = handlers[queue_name]
        logger.info(f"开始消费队列任务: {queue_name}")
        result = handler(payload)
        if asyncio.iscoroutine(result):
            asyncio.run(result)
        return True


task_queue_service = TaskQueueService()
