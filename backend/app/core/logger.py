#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
日志配置
"""

from loguru import logger
from app.core.config import settings
import sys
import os


def setup_logging():
    """配置日志系统"""
    
    # 移除默认的logger
    logger.remove()
    
    # 控制台输出
    logger.add(
        sys.stdout,
        level=settings.LOG_LEVEL,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True,
    )
    
    # 文件输出
    log_file = os.path.join(settings.LOG_DIR, "app.log")
    logger.add(
        log_file,
        level=settings.LOG_LEVEL,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        rotation="00:00",  # 每天午夜轮换
        retention="30 days",  # 保留30天
        compression="zip",  # 压缩旧日志
        encoding="utf-8",
    )
    
    # 错误日志单独记录
    error_log_file = os.path.join(settings.LOG_DIR, "error.log")
    logger.add(
        error_log_file,
        level="ERROR",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        rotation="00:00",
        retention="30 days",
        compression="zip",
        encoding="utf-8",
    )
    
    return logger


def get_logger(name=None):
    """获取logger实例"""
    return logger
