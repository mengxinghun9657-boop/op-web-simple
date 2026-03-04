#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
定时清理任务调度器 (Cleanup Scheduler)

负责定期清理软删除超过 30 天的知识库条目。

功能：
- 每周执行一次清理任务
- 物理删除 MySQL 中的记录
- 物理删除向量数据库中的向量
- 记录清理日志

Requirements: 20.7
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional

from app.core.logger import logger
from app.core.deps import SessionLocal
from app.services.ai.knowledge_manager import KnowledgeManager


class CleanupScheduler:
    """
    定时清理任务调度器
    
    每周执行一次，清理软删除超过 30 天的知识库条目。
    
    使用示例：
    ```python
    scheduler = CleanupScheduler()
    await scheduler.start()
    ```
    """
    
    def __init__(
        self,
        interval_days: int = 7,
        days_threshold: int = 30
    ):
        """
        初始化清理调度器
        
        Args:
            interval_days: 清理任务执行间隔（天），默认 7 天（每周）
            days_threshold: 软删除后保留的天数，默认 30 天
        """
        self.interval_days = interval_days
        self.days_threshold = days_threshold
        self.is_running = False
        self.task: Optional[asyncio.Task] = None
        
        logger.info(
            f"CleanupScheduler initialized: "
            f"interval={interval_days} days, threshold={days_threshold} days"
        )
    
    async def _run_cleanup(self) -> None:
        """
        执行一次清理任务
        """
        db = SessionLocal()
        try:
            logger.info("=" * 60)
            logger.info("开始执行定时清理任务...")
            logger.info(f"清理条件: 软删除超过 {self.days_threshold} 天的条目")
            
            # 创建知识库管理器
            knowledge_manager = KnowledgeManager(db)
            
            # 执行清理
            result = await knowledge_manager.cleanup_deleted_entries(
                days_threshold=self.days_threshold
            )
            
            # 记录结果
            logger.info(f"✅ 清理任务完成: {result['message']}")
            logger.info(f"   删除数量: {result['deleted_count']}")
            if result['deleted_count'] > 0:
                logger.info(f"   删除的条目ID: {result['deleted_ids']}")
                logger.info(f"   删除的条目标题: {result['deleted_titles']}")
            logger.info("=" * 60)
        
        except Exception as e:
            logger.error(f"❌ 定时清理任务执行失败: {e}")
        
        finally:
            db.close()
    
    async def _schedule_loop(self) -> None:
        """
        调度循环，定期执行清理任务
        """
        logger.info(f"清理调度器已启动，每 {self.interval_days} 天执行一次")
        
        while self.is_running:
            try:
                # 执行清理
                await self._run_cleanup()
                
                # 等待下一次执行
                next_run = datetime.now() + timedelta(days=self.interval_days)
                logger.info(f"下次清理时间: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
                
                # 转换为秒
                interval_seconds = self.interval_days * 24 * 60 * 60
                await asyncio.sleep(interval_seconds)
            
            except asyncio.CancelledError:
                logger.info("清理调度器收到取消信号")
                break
            
            except Exception as e:
                logger.error(f"❌ 清理调度循环异常: {e}")
                # 发生异常后等待 1 小时再重试
                await asyncio.sleep(3600)
    
    async def start(self) -> None:
        """
        启动清理调度器
        """
        if self.is_running:
            logger.warning("清理调度器已在运行中")
            return
        
        self.is_running = True
        self.task = asyncio.create_task(self._schedule_loop())
        logger.info("✅ 清理调度器已启动")
    
    async def stop(self) -> None:
        """
        停止清理调度器
        """
        if not self.is_running:
            logger.warning("清理调度器未在运行")
            return
        
        self.is_running = False
        
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                logger.info("✅ 清理调度器已停止")
        
        self.task = None
    
    async def run_now(self) -> None:
        """
        立即执行一次清理任务（用于手动触发）
        """
        logger.info("手动触发清理任务...")
        await self._run_cleanup()


# 全局调度器实例
_cleanup_scheduler: Optional[CleanupScheduler] = None


def get_cleanup_scheduler() -> CleanupScheduler:
    """
    获取全局清理调度器实例
    
    Returns:
        CleanupScheduler: 清理调度器实例
    """
    global _cleanup_scheduler
    
    if _cleanup_scheduler is None:
        _cleanup_scheduler = CleanupScheduler(
            interval_days=7,  # 每周执行一次
            days_threshold=30  # 清理软删除超过 30 天的条目
        )
    
    return _cleanup_scheduler


async def start_cleanup_scheduler() -> None:
    """
    启动全局清理调度器
    """
    scheduler = get_cleanup_scheduler()
    await scheduler.start()


async def stop_cleanup_scheduler() -> None:
    """
    停止全局清理调度器
    """
    global _cleanup_scheduler
    
    if _cleanup_scheduler:
        await _cleanup_scheduler.stop()
        _cleanup_scheduler = None
