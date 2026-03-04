#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prometheus任务管理服务 - Redis + MySQL + MinIO集成
"""
import time
import json
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.models.task import Task, TaskType, TaskStatus
from app.utils.task_manager import (
    save_task_status,
    get_task_status as redis_get_task_status,
    delete_task_status
)
from app.core.minio_client import get_minio_client
from app.core.logger import logger


class PrometheusTaskService:
    """Prometheus任务服务 - 统一管理Redis + MySQL + MinIO"""

    def __init__(self, db: Session, user_id: int = None, username: str = None):
        self.db = db
        self.user_id = user_id
        self.username = username

    def create_task(
        self,
        task_id: str,
        task_type: TaskType,
        total_clusters: int,
        message: str = "任务已创建"
    ) -> Task:
        """
        创建任务（同时写入MySQL和Redis）

        Args:
            task_id: 任务ID
            task_type: 任务类型
            total_clusters: 集群总数
            message: 任务消息

        Returns:
            Task对象
        """
        # 1. 写入MySQL
        task = Task(
            id=task_id,
            task_type=task_type,
            status=TaskStatus.PENDING,
            progress=0,
            total_items=total_clusters,
            completed_items=0,
            message=message,
            user_id=self.user_id,
            username=self.username
        )
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        logger.info(f"✅ 任务已写入MySQL: {task_id}")

        # 2. 写入Redis（实时状态）
        redis_status = {
            'status': 'pending',
            'message': message,
            'progress': 0,
            'total_clusters': total_clusters,
            'completed_clusters': 0,
            'timestamp': time.strftime("%Y-%m-%d %H:%M:%S")
        }
        save_task_status(task_id, redis_status, expire=86400)  # 24小时
        logger.info(f"✅ 任务状态已写入Redis: {task_id}")

        return task

    def update_progress(
        self,
        task_id: str,
        completed: int,
        total: int,
        message: str = None
    ):
        """
        更新任务进度（同时更新MySQL和Redis）

        Args:
            task_id: 任务ID
            completed: 已完成数量
            total: 总数量
            message: 消息
        """
        progress = int((completed / total) * 100) if total > 0 else 0

        # 1. 更新MySQL
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if task:
            task.status = TaskStatus.PROCESSING
            task.progress = progress
            task.completed_items = completed
            if message:
                task.message = message
            self.db.commit()

        # 2. 更新Redis
        redis_status = {
            'status': 'processing',
            'message': message or f'正在处理 {completed}/{total} 个集群...',
            'progress': progress,
            'total_clusters': total,
            'completed_clusters': completed,
            'timestamp': time.strftime("%Y-%m-%d %H:%M:%S")
        }
        save_task_status(task_id, redis_status, expire=86400)

    def complete_task(
        self,
        task_id: str,
        result_data: Dict[str, Any],
        upload_to_minio: bool = True
    ) -> Optional[str]:
        """
        完成任务（更新MySQL，上传结果到MinIO，更新Redis）

        Args:
            task_id: 任务ID
            result_data: 结果数据
            upload_to_minio: 是否上传到MinIO

        Returns:
            MinIO文件URL
        """
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            logger.error(f"❌ 任务不存在: {task_id}")
            return None

        result_url = None

        # 1. 上传结果到MinIO
        if upload_to_minio:
            try:
                minio_client = get_minio_client()
                file_name = f"prometheus_results/{task_id}.json"
                result_json = json.dumps(result_data, indent=2, ensure_ascii=False)

                result_url = minio_client.upload_data(
                    data=result_json.encode('utf-8'),
                    object_name=file_name,
                    content_type='application/json'
                )
                logger.info(f"✅ 结果已上传到MinIO: {file_name}")
            except Exception as e:
                logger.error(f"❌ 上传MinIO失败: {e}")

        # 2. 更新MySQL
        task.status = TaskStatus.COMPLETED
        task.progress = 100
        task.completed_items = task.total_items
        task.message = f'批量采集完成，共 {task.total_items} 个集群'
        task.result_path = f"prometheus_results/{task_id}.json" if result_url else None
        task.result_url = result_url
        task.completed_at = datetime.now()
        self.db.commit()
        logger.info(f"✅ 任务已标记完成（MySQL）: {task_id}")

        # 3. 更新Redis（保留24小时供前端查询）
        redis_status = {
            'status': 'completed',
            'message': task.message,
            'progress': 100,
            'total_clusters': task.total_items,
            'completed_clusters': task.total_items,
            'result_file': f"{task_id}.json",
            'result_url': result_url,
            'timestamp': time.strftime("%Y-%m-%d %H:%M:%S")
        }
        save_task_status(task_id, redis_status, expire=86400)

        return result_url

    def fail_task(
        self,
        task_id: str,
        error_message: str
    ):
        """
        标记任务失败（同时更新MySQL和Redis）

        Args:
            task_id: 任务ID
            error_message: 错误消息
        """
        # 1. 更新MySQL
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if task:
            task.status = TaskStatus.FAILED
            task.message = '任务执行失败'
            task.error_message = error_message
            task.completed_at = datetime.now()
            self.db.commit()

        # 2. 更新Redis
        redis_status = {
            'status': 'failed',
            'message': '批量采集失败',
            'progress': 0,
            'total_clusters': task.total_items if task else 0,
            'completed_clusters': 0,
            'error': error_message,
            'timestamp': time.strftime("%Y-%m-%d %H:%M:%S")
        }
        save_task_status(task_id, redis_status, expire=86400)

    def get_task_status_from_redis(self, task_id: str) -> Optional[Dict]:
        """从Redis获取任务实时状态"""
        return redis_get_task_status(task_id)

    def get_task_from_db(self, task_id: str) -> Optional[Task]:
        """从MySQL获取任务记录"""
        return self.db.query(Task).filter(Task.id == task_id).first()

    def get_task_history(
        self,
        skip: int = 0,
        limit: int = 20,
        task_type: TaskType = None,
        user_id: int = None
    ):
        """
        查询历史任务列表（从MySQL）

        Args:
            skip: 跳过数量
            limit: 返回数量
            task_type: 任务类型筛选
            user_id: 用户ID筛选

        Returns:
            任务列表
        """
        query = self.db.query(Task).order_by(Task.created_at.desc())

        if task_type:
            query = query.filter(Task.task_type == task_type)

        if user_id:
            query = query.filter(Task.user_id == user_id)

        return query.offset(skip).limit(limit).all()

    def download_result(self, task_id: str) -> Optional[str]:
        """
        获取任务结果下载URL（从MinIO生成预签名URL）

        Args:
            task_id: 任务ID

        Returns:
            预签名下载URL（有效期1小时）
        """
        task = self.get_task_from_db(task_id)
        if not task or not task.result_path:
            return None

        try:
            minio_client = get_minio_client()
            # 生成1小时有效的预签名URL
            url = minio_client.get_object_url(task.result_path, expires=3600)
            logger.info(f"✅ 生成下载URL: {task_id}")
            return url
        except Exception as e:
            logger.error(f"❌ 生成下载URL失败: {e}")
            return None
