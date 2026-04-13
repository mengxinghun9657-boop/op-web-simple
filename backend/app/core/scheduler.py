#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
定时任务调度器
使用APScheduler实现CMDB自动同步等定时任务
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger
from typing import List
import os


class TaskScheduler:
    """定时任务调度器"""
    
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.is_running = False
    
    def start(self):
        """启动调度器"""
        if not self.is_running:
            self.scheduler.start()
            self.is_running = True
            logger.info("定时任务调度器已启动")
    
    def stop(self):
        """停止调度器"""
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("定时任务调度器已停止")
    
    def add_cmdb_sync_job(self, interval_hours: int, azones: List[str]):
        """
        添加CMDB同步定时任务
        
        Args:
            interval_hours: 同步间隔（小时）
            azones: 要同步的可用区列表
        """
        try:
            # 移除旧任务（如果存在）
            try:
                self.scheduler.remove_job("cmdb_sync")
            except Exception as e:
                logger.debug(f"移除旧的CMDB同步任务失败（可能不存在）: {e}")
            
            # 添加新任务
            self.scheduler.add_job(
                func=self._sync_cmdb_data,
                trigger=IntervalTrigger(hours=interval_hours),
                args=[azones],
                id="cmdb_sync",
                name="CMDB自动同步",
                replace_existing=True
            )
            
            logger.info(f"CMDB同步任务已添加: 间隔{interval_hours}小时, 可用区{azones}")
            
        except Exception as e:
            logger.error(f"添加CMDB同步任务失败: {e}")

    def add_apiserver_alert_job(self, interval_minutes: int):
        """添加 APIServer 告警自动检测任务"""
        try:
            try:
                self.scheduler.remove_job("apiserver_alert_scan")
            except Exception:
                pass

            self.scheduler.add_job(
                func=self._scan_apiserver_alerts,
                trigger=IntervalTrigger(minutes=interval_minutes),
                id="apiserver_alert_scan",
                name="APIServer告警自动检测",
                replace_existing=True,
            )
            logger.info(f"APIServer 告警自动检测任务已添加: 间隔 {interval_minutes} 分钟")
        except Exception as e:
            logger.error(f"添加 APIServer 告警自动检测任务失败: {e}")

    def remove_apiserver_alert_job(self):
        try:
            self.scheduler.remove_job("apiserver_alert_scan")
            logger.info("APIServer 告警自动检测任务已移除")
        except Exception as e:
            logger.warning(f"移除 APIServer 告警自动检测任务失败: {e}")

    def add_bce_sync_job(self, interval_hours: int, auto_sync_bcc: bool = True, auto_sync_cce: bool = True):
        """添加 BCE 数据自动同步任务"""
        try:
            try:
                self.scheduler.remove_job("bce_sync")
            except Exception:
                pass

            self.scheduler.add_job(
                func=self._sync_bce_data,
                trigger=IntervalTrigger(hours=interval_hours),
                args=[auto_sync_bcc, auto_sync_cce],
                id="bce_sync",
                name="BCE数据自动同步",
                replace_existing=True,
            )
            logger.info(f"BCE 自动同步任务已添加: 间隔 {interval_hours} 小时, BCC={auto_sync_bcc}, CCE={auto_sync_cce}")
        except Exception as e:
            logger.error(f"添加 BCE 自动同步任务失败: {e}")

    def remove_bce_sync_job(self):
        """移除 BCE 数据自动同步任务"""
        try:
            self.scheduler.remove_job("bce_sync")
            logger.info("BCE 自动同步任务已移除")
        except Exception as e:
            logger.warning(f"移除 BCE 自动同步任务失败: {e}")
    
    def remove_cmdb_sync_job(self):
        """移除CMDB同步定时任务"""
        try:
            self.scheduler.remove_job("cmdb_sync")
            logger.info("CMDB同步任务已移除")
        except Exception as e:
            logger.warning(f"移除CMDB同步任务失败: {e}")
    
    def _sync_cmdb_data(self, azones: List[str]):
        """
        执行CMDB数据同步
        
        Args:
            azones: 要同步的可用区列表
        """
        from app.core.database import SessionLocal
        from app.services.cmdb_sync_service import CMDBSyncService
        
        # 为每个azone创建独立的数据库会话，避免会话状态污染
        for azone in azones:
            db = None
            try:
                db = SessionLocal()
                sync_service = CMDBSyncService(db)
                
                logger.info(f"开始自动同步CMDB数据: {azone}")
                result = sync_service.sync_from_api(
                    azone=azone,
                    page=1,
                    per_page=2000,
                    triggered_by="scheduler"
                )
                logger.info(f"CMDB数据同步完成: {azone}, 结果: {result}")
                
            except Exception as e:
                logger.error(f"CMDB数据同步失败: {azone}, 错误: {e}")
                
            finally:
                if db:
                    db.close()

    def _scan_apiserver_alerts(self):
        """执行 APIServer 告警自动检测"""
        from app.core.deps import SessionLocal
        from app.services.apiserver_alert_service import APIServerAlertService

        db = None
        try:
            db = SessionLocal()
            service = APIServerAlertService(db)
            task_id = service.create_scan_task(username="scheduler")
            logger.info(f"开始自动执行 APIServer 告警检测: {task_id}")
            service.run_scan_task(task_id)
        except Exception as e:
            logger.error(f"APIServer 告警自动检测失败: {e}")
        finally:
            if db:
                db.close()

    def _sync_bce_data(self, auto_sync_bcc: bool = True, auto_sync_cce: bool = True):
        """执行 BCE 数据自动同步"""
        from app.core.database import SessionLocal
        from app.services.bce_sync_service import BCESyncService

        db = None
        try:
            db = SessionLocal()
            svc = BCESyncService(db)
            logger.info(f"开始自动同步 BCE 数据: BCC={auto_sync_bcc}, CCE={auto_sync_cce}")
            if auto_sync_bcc and auto_sync_cce:
                result = svc.sync_all()
            elif auto_sync_bcc:
                result = svc.sync_bcc()
            elif auto_sync_cce:
                result = svc.sync_cce()
            else:
                logger.info("BCE 自动同步：BCC 和 CCE 均未启用，跳过")
                return
            logger.info(f"BCE 自动同步完成: {result}")
        except Exception as e:
            logger.error(f"BCE 自动同步失败: {e}")
        finally:
            if db:
                db.close()
    
    def get_job_info(self, job_id: str):
        """获取任务信息"""
        try:
            job = self.scheduler.get_job(job_id)
            if job:
                return {
                    "id": job.id,
                    "name": job.name,
                    "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                    "trigger": str(job.trigger)
                }
            return None
        except Exception as e:
            logger.error(f"获取任务信息失败: {e}")
            return None
    
    def list_jobs(self):
        """列出所有任务"""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger)
            })
        return jobs


# 全局调度器实例
scheduler = TaskScheduler()


def init_scheduler():
    """初始化调度器并加载配置"""
    from app.core.database import SessionLocal
    from app.services.cmdb_sync_service import CMDBSyncService
    
    try:
        # 启动调度器
        scheduler.start()
        
        # 从数据库加载CMDB同步配置
        db = SessionLocal()
        try:
            sync_service = CMDBSyncService(db)
            
            enabled = sync_service.get_config("sync_schedule_enabled", False)
            interval_hours = sync_service.get_config("sync_schedule_interval_hours", 24)
            azones = sync_service.get_config("sync_schedule_azones", ["AZONE-cdhmlcc001"])
            
            if enabled:
                scheduler.add_cmdb_sync_job(interval_hours, azones)
                logger.info(f"CMDB定时同步已启用: 间隔{interval_hours}小时")
            else:
                logger.info("CMDB定时同步未启用")

            from app.models.system_config import SystemConfig
            import json
            apiserver_config_record = db.query(SystemConfig).filter(
                SystemConfig.module == 'apiserver',
                SystemConfig.config_key == 'main'
            ).first()
            if apiserver_config_record and apiserver_config_record.config_value:
                apiserver_config = json.loads(apiserver_config_record.config_value)
                if apiserver_config.get('auto_check_enabled'):
                    scheduler.add_apiserver_alert_job(int(apiserver_config.get('check_interval_minutes', 10)))
                    logger.info("APIServer定时检测已启用")
                else:
                    logger.info("APIServer定时检测未启用")

            # 加载 BCE 自动同步配置
            bce_sync_config_record = db.query(SystemConfig).filter(
                SystemConfig.module == 'bce_sync',
                SystemConfig.config_key == 'sync_config'
            ).first()
            if bce_sync_config_record and bce_sync_config_record.config_value:
                bce_sync_config = json.loads(bce_sync_config_record.config_value)
                if bce_sync_config.get('enabled'):
                    interval_hours = max(1, bce_sync_config.get('sync_interval', 3600) // 3600)
                    auto_sync_bcc = bce_sync_config.get('auto_sync_bcc', True)
                    auto_sync_cce = bce_sync_config.get('auto_sync_cce', True)
                    scheduler.add_bce_sync_job(interval_hours, auto_sync_bcc, auto_sync_cce)
                    logger.info(f"BCE 定时同步已启用: 间隔 {interval_hours} 小时")
                else:
                    logger.info("BCE 定时同步未启用")
                
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"初始化调度器失败: {e}")


def shutdown_scheduler():
    """关闭调度器"""
    scheduler.stop()
