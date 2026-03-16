#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
健康检查API
"""

from fastapi import APIRouter
from datetime import datetime
from app.core.config import settings

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
