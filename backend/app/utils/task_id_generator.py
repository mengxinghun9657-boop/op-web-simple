#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一任务ID生成器
"""
import uuid
import time
from typing import Optional

def generate_task_id(prefix: str = "", length: int = 8) -> str:
    """
    生成统一格式的任务ID
    
    Args:
        prefix: 前缀（如 'batch', 'analysis'）
        length: UUID长度（默认8位）
    
    Returns:
        格式化的任务ID
    """
    if length == 36:
        task_uuid = str(uuid.uuid4())
    else:
        task_uuid = str(uuid.uuid4())[:length]
    
    if prefix:
        return f"{prefix}-{task_uuid}"
    return task_uuid

def generate_batch_task_id() -> str:
    """生成批量任务ID"""
    return generate_task_id("batch", 8)

def generate_analysis_task_id() -> str:
    """生成分析任务ID"""
    return generate_task_id("analysis", 8)

def generate_monitoring_task_id() -> str:
    """生成监控任务ID"""
    return generate_task_id("monitor", 8)

def is_valid_task_id(task_id: str) -> bool:
    """验证任务ID格式"""
    if not task_id:
        return False
    
    # 检查基本格式
    parts = task_id.split('-')
    if len(parts) < 2:
        return len(task_id) in [8, 36]  # 纯UUID
    
    # 检查前缀-UUID格式
    prefix, uuid_part = parts[0], '-'.join(parts[1:])
    return len(uuid_part) in [8, 36] and prefix.isalpha()
