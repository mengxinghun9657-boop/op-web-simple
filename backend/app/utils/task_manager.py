#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务状态管理 - 使用Redis替代内存存储
"""
from app.core.redis_client import get_redis_client
from app.core.logger import logger
import time

def save_task_status(task_id: str, status_data: dict, expire: int = 3600):
    """
    保存任务状态到Redis

    Args:
        task_id: 任务ID
        status_data: 状态数据
        expire: 过期时间（秒），默认1小时
    """
    try:
        redis_client = get_redis_client()
        redis_client.set_task_status(task_id, status_data, expire)
    except Exception as e:
        logger.error(f"保存任务状态失败: {task_id}, 错误: {e}")
        # 降级：如果Redis失败，至少记录日志
        logger.warning(f"任务 {task_id} 状态: {status_data}")

def get_task_status(task_id: str) -> dict:
    """
    从Redis获取任务状态

    Args:
        task_id: 任务ID

    Returns:
        任务状态数据，不存在返回None
    """
    try:
        redis_client = get_redis_client()
        return redis_client.get_task_status(task_id)
    except Exception as e:
        logger.error(f"获取任务状态失败: {task_id}, 错误: {e}")
        return None

def delete_task_status(task_id: str):
    """删除任务状态"""
    try:
        redis_client = get_redis_client()
        redis_client.delete_task_status(task_id)
    except Exception as e:
        logger.error(f"删除任务状态失败: {task_id}, 错误: {e}")

def create_task_status(task_id: str, total_clusters: int) -> dict:
    """创建初始任务状态"""
    status_data = {
        'status': 'pending',
        'message': '任务已创建，等待开始...',
        'progress': 0,
        'total_clusters': total_clusters,
        'completed_clusters': 0,
        'timestamp': time.strftime("%Y-%m-%d %H:%M:%S")
    }
    save_task_status(task_id, status_data)
    return status_data

def update_task_progress(task_id: str, completed: int, total: int, message: str = None):
    """更新任务进度"""
    progress = int((completed / total) * 100) if total > 0 else 0
    status_data = {
        'status': 'processing',
        'message': message or f'正在处理 {completed}/{total} 个集群...',
        'progress': progress,
        'total_clusters': total,
        'completed_clusters': completed,
        'timestamp': time.strftime("%Y-%m-%d %H:%M:%S")
    }
    save_task_status(task_id, status_data)

def mark_task_completed(task_id: str, total_clusters: int, result_file: str = None):
    """标记任务完成"""
    status_data = {
        'status': 'completed',
        'message': f'批量采集完成，共 {total_clusters} 个集群',
        'progress': 100,
        'total_clusters': total_clusters,
        'completed_clusters': total_clusters,
        'result_file': result_file,
        'timestamp': time.strftime("%Y-%m-%d %H:%M:%S")
    }
    # 完成的任务保留24小时
    save_task_status(task_id, status_data, expire=86400)

def mark_task_failed(task_id: str, total_clusters: int, error: str):
    """标记任务失败"""
    status_data = {
        'status': 'failed',
        'message': '批量采集失败',
        'progress': 0,
        'total_clusters': total_clusters,
        'completed_clusters': 0,
        'error': error,
        'timestamp': time.strftime("%Y-%m-%d %H:%M:%S")
    }
    # 失败的任务保留24小时
    save_task_status(task_id, status_data, expire=86400)
