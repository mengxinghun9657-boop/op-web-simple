#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
任务相关的Pydantic Schema
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.models.task import TaskStatus, TaskType


class TaskBase(BaseModel):
    """任务基础Schema"""
    id: str
    task_type: TaskType
    status: TaskStatus
    progress: int
    total_items: int
    completed_items: int
    message: Optional[str] = None


class TaskHistoryResponse(BaseModel):
    """任务历史记录响应"""
    id: str
    task_type: TaskType
    status: TaskStatus
    progress: int
    total_items: int
    completed_items: int
    message: Optional[str] = None
    result_path: Optional[str] = None
    result_url: Optional[str] = None
    user_id: Optional[int] = None
    username: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TaskListResponse(BaseModel):
    """任务列表响应"""
    total: int
    tasks: List[TaskHistoryResponse]


class TaskDownloadResponse(BaseModel):
    """任务下载响应"""
    task_id: str
    download_url: Optional[str] = None
    expires_in: int = Field(default=3600, description="URL有效期（秒）")
    message: str
