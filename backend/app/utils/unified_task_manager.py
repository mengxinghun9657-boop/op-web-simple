#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一任务状态管理器 - 解决Redis和MySQL双重存储同步问题
"""
from typing import Optional, Dict, Any
from datetime import datetime
from loguru import logger

from app.core.redis_client import get_redis_client
from app.services.task_service import save_task_to_db, update_task_status as update_db_status
from app.models.task import TaskStatus, TaskType


class TaskStateManager:
    """统一任务状态管理器"""
    
    def __init__(self):
        self.redis_client = None
        try:
            self.redis_client = get_redis_client()
        except Exception as e:
            logger.warning(f"Redis连接失败，将仅使用MySQL: {e}")
    
    def create_task(
        self,
        task_id: str,
        task_type: TaskType,
        username: str = "system",
        file_name: str = None,
        total_items: int = 0
    ) -> bool:
        """创建新任务"""
        try:
            # 1. 保存到MySQL（主要存储）
            success = save_task_to_db(
                task_id=task_id,
                task_type=task_type,
                status=TaskStatus.PENDING,
                message="任务已创建",
                file_name=file_name,
                username=username
            )
            
            if not success:
                return False
            
            # 2. 保存到Redis（临时状态）
            if self.redis_client:
                redis_data = {
                    'status': 'pending',
                    'message': '任务已创建，等待开始...',
                    'progress': 0,
                    'total_items': total_items,
                    'completed_items': 0,
                    'created_at': datetime.now().isoformat()
                }
                self.redis_client.set_task_status(task_id, redis_data, expire=3600)
            
            return True
            
        except Exception as e:
            logger.error(f"创建任务失败: {task_id}, 错误: {e}")
            return False
    
    def update_task(
        self,
        task_id: str,
        status: TaskStatus = None,
        message: str = None,
        progress: int = None,
        completed_items: int = None,
        total_items: int = None,
        result_url: str = None,
        error_message: str = None
    ) -> bool:
        """更新任务状态（同时更新Redis和MySQL）"""
        try:
            # 1. 更新MySQL（持久化）
            if status:
                update_db_status(
                    task_id=task_id,
                    status=status,
                    message=message,
                    result_url=result_url,
                    error_message=error_message,
                    progress=progress
                )
            
            # 2. 更新Redis（实时状态）
            if self.redis_client:
                current_data = self.redis_client.get_task_status(task_id) or {}
                
                # 合并更新数据
                if status:
                    current_data['status'] = status.value
                if message:
                    current_data['message'] = message
                if progress is not None:
                    current_data['progress'] = progress
                if completed_items is not None:
                    current_data['completed_items'] = completed_items
                if total_items is not None:
                    current_data['total_items'] = total_items
                if result_url:
                    current_data['result_url'] = result_url
                if error_message:
                    current_data['error'] = error_message
                
                current_data['updated_at'] = datetime.now().isoformat()
                
                # 根据状态设置过期时间
                expire = 86400 if status in [TaskStatus.COMPLETED, TaskStatus.FAILED] else 3600
                self.redis_client.set_task_status(task_id, current_data, expire)
            
            return True
            
        except Exception as e:
            logger.error(f"更新任务状态失败: {task_id}, 错误: {e}")
            return False
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态（优先从Redis获取）"""
        try:
            # 1. 先尝试从Redis获取（实时状态）
            if self.redis_client:
                redis_data = self.redis_client.get_task_status(task_id)
                if redis_data:
                    return redis_data
            
            # 2. Redis没有则从MySQL获取（降级）
            logger.warning(f"Redis中未找到任务 {task_id}，从MySQL获取")
            # 这里需要实现从MySQL获取任务状态的方法
            return None
            
        except Exception as e:
            logger.error(f"获取任务状态失败: {task_id}, 错误: {e}")
            return None
    
    def delete_task(self, task_id: str) -> bool:
        """删除任务（仅删除Redis缓存，MySQL保留历史记录）"""
        try:
            if self.redis_client:
                self.redis_client.delete_task_status(task_id)
            return True
        except Exception as e:
            logger.error(f"删除任务缓存失败: {task_id}, 错误: {e}")
            return False


# 全局实例
task_manager = TaskStateManager()
