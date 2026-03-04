#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复任务状态获取逻辑 - 统一首次获取和历史获取
"""

from fastapi import HTTPException
from typing import Optional, Dict, Any
from loguru import logger

from app.core.redis_client import get_redis_client
from app.core.deps import SessionLocal
from app.models.task import Task


async def get_unified_task_status(task_id: str) -> Dict[str, Any]:
    """
    统一的任务状态获取逻辑
    优先级：Redis(实时) -> MySQL(历史) -> 内存(降级)
    """
    try:
        # 1. 首先尝试从Redis获取（实时状态）
        redis_client = get_redis_client()
        if redis_client and redis_client.client:
            redis_data = redis_client.get_task_status(task_id)
            if redis_data:
                logger.debug(f"从Redis获取任务状态: {task_id}")
                return redis_data
        
        # 2. Redis没有，从MySQL获取（历史任务）
        db = SessionLocal()
        try:
            task = db.query(Task).filter(Task.id == task_id).first()
            if task:
                logger.debug(f"从MySQL获取任务状态: {task_id}")
                return {
                    "task_id": task.id,
                    "status": task.status.value if task.status else "unknown",
                    "progress": task.progress or 0,
                    "message": task.message or "",
                    "total_items": task.total_items or 0,
                    "completed_items": task.completed_items or 0,
                    "result_url": task.result_url,
                    "error_message": task.error_message,
                    "created_at": task.created_at.isoformat() if task.created_at else None,
                    "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                    "source": "mysql"  # 标记数据来源
                }
        finally:
            db.close()
        
        # 3. 都没有找到
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务状态失败: {task_id}, 错误: {e}")
        raise HTTPException(status_code=500, detail="获取任务状态失败")


def validate_task_report_association(task_id: str, module_type: str) -> bool:
    """
    验证任务ID和报告类型的关联性
    """
    try:
        db = SessionLocal()
        try:
            task = db.query(Task).filter(Task.id == task_id).first()
            if not task:
                return False
            
            # 检查任务类型和模块类型的匹配
            task_module_mapping = {
                "prometheus_batch": "prometheus",
                "operational_analysis": "operational", 
                "resource_analysis": "resource",
                "monitoring_bcc": "bcc",
                "monitoring_bos": "bos",
                "monitoring_eip": "eip"
            }
            
            expected_module = task_module_mapping.get(task.task_type.value if task.task_type else "")
            return expected_module == module_type
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"验证任务报告关联失败: {task_id}, {module_type}, 错误: {e}")
        return False
