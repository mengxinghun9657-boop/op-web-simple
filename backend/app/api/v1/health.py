#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
健康检查API
"""

from fastapi import APIRouter
from datetime import datetime
from app.core.config import settings
from app.services.ai.vector_store import get_vector_store

router = APIRouter()


@router.get("/health")
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/ping")
async def ping():
    """简单的Ping接口"""
    return {"message": "pong"}


@router.get("/health/vector-store")
async def vector_store_health():
    """
    向量数据库健康检查接口
    
    返回向量数据库的状态信息，包括：
    - 索引类型
    - 向量维度
    - 向量总数
    - 条目总数
    - 文件存在性
    """
    try:
        vector_store = get_vector_store()
        health_status = vector_store.health_check()
        return health_status
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
