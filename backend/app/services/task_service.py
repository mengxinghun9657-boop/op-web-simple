#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""通用任务服务 - 统一任务持久化到MySQL"""

from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from loguru import logger

from app.models.task import Task, TaskStatus, TaskType
from app.core.deps import SessionLocal


def save_task_to_db(
    task_id: str,
    task_type: TaskType,
    status: TaskStatus = TaskStatus.PENDING,
    message: str = "",
    file_name: str = None,
    result_url: str = None,
    username: str = "system"
) -> bool:
    """保存任务到MySQL"""
    db = None
    try:
        db = SessionLocal()
        task = Task(
            id=task_id,
            task_type=task_type,
            status=status,
            message=message,
            file_name=file_name,
            result_url=result_url,
            username=username,
            progress=0 if status == TaskStatus.PENDING else 100 if status == TaskStatus.COMPLETED else 50
        )
        db.add(task)
        db.commit()
        logger.info(f"任务已保存到MySQL: {task_id}")
        return True
    except Exception as e:
        logger.error(f"保存任务到MySQL失败: {e}")
        if db:
            db.rollback()
        return False
    finally:
        if db:
            db.close()


def update_task_status(
    task_id: str,
    status: TaskStatus,
    message: str = None,
    result_url: str = None,
    error_message: str = None,
    progress: int = None
) -> bool:
    """更新任务状态"""
    db = None
    try:
        db = SessionLocal()
        task = db.query(Task).filter(Task.id == task_id).first()
        if task:
            task.status = status
            if message:
                task.message = message
            if result_url:
                task.result_url = result_url
            if error_message:
                task.error_message = error_message
            if progress is not None:
                task.progress = progress
            if status == TaskStatus.COMPLETED:
                task.completed_at = datetime.now()
                task.progress = 100
            db.commit()
            logger.info(f"任务状态已更新: {task_id} -> {status.value}")
            return True
        return False
    except Exception as e:
        logger.error(f"更新任务状态失败: {e}")
        if db:
            db.rollback()
        return False
    finally:
        if db:
            db.close()
