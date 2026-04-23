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
            logger.debug(f"移除 APIServer 告警自动检测任务失败（任务可能不存在）: {e}")

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
            logger.debug(f"移除 BCE 自动同步任务失败（任务可能不存在）: {e}")
    
    def remove_cmdb_sync_job(self):
        """移除CMDB同步定时任务"""
        try:
            self.scheduler.remove_job("cmdb_sync")
            logger.info("CMDB同步任务已移除")
        except Exception as e:
            logger.debug(f"移除CMDB同步任务失败（任务可能不存在）: {e}")
    
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
    
    def reload_config_from_db(self):
        """从数据库重新读取三个定时任务的配置并更新调度器（worker 轮询 + 启动时调用）"""
        from app.core.database import SessionLocal
        from app.services.cmdb_sync_service import CMDBSyncService
        from app.models.system_config import SystemConfig
        import json

        db = None
        try:
            db = SessionLocal()

            # --- CMDB ---
            sync_service = CMDBSyncService(db)
            enabled = sync_service.get_config("sync_schedule_enabled", False)
            interval_hours = sync_service.get_config("sync_schedule_interval_hours", 24)
            azones = sync_service.get_config("sync_schedule_azones", ["AZONE-cdhmlcc001"])
            if enabled:
                if not self.scheduler.get_job("cmdb_sync"):
                    self.add_cmdb_sync_job(interval_hours, azones)
            else:
                self.remove_cmdb_sync_job()

            # --- APIServer ---
            apiserver_row = db.query(SystemConfig).filter_by(
                module='apiserver', config_key='main'
            ).first()
            if apiserver_row and apiserver_row.config_value:
                apiserver_cfg = json.loads(apiserver_row.config_value)
                if apiserver_cfg.get('auto_check_enabled'):
                    if not self.scheduler.get_job("apiserver_alert_scan"):
                        self.add_apiserver_alert_job(int(apiserver_cfg.get('check_interval_minutes', 10)))
                else:
                    self.remove_apiserver_alert_job()
            else:
                self.remove_apiserver_alert_job()

            # --- BCE ---
            bce_row = db.query(SystemConfig).filter_by(
                module='bce_sync', config_key='sync_config'
            ).first()
            if bce_row and bce_row.config_value:
                bce_cfg = json.loads(bce_row.config_value)
                if bce_cfg.get('enabled'):
                    if not self.scheduler.get_job("bce_sync"):
                        hours = max(0.01, bce_cfg.get('sync_interval', 3600) / 3600)
                        self.add_bce_sync_job(hours, bce_cfg.get('auto_sync_bcc', True), bce_cfg.get('auto_sync_cce', True))
                else:
                    self.remove_bce_sync_job()
            else:
                self.remove_bce_sync_job()

        except Exception as e:
            logger.error(f"reload_config_from_db 失败: {e}")
        finally:
            if db:
                db.close()

    def _config_watcher(self):
        """每60秒轮询一次DB，检测配置变化后自动重新注册定时任务"""
        try:
            self.reload_config_from_db()
            logger.debug("config_watcher: 配置同步完成")
        except Exception as e:
            logger.error(f"config_watcher 执行失败: {e}")

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
    """初始化调度器并加载配置（含 MySQL 就绪等待）"""
    import time
    from app.core.database import SessionLocal

    # 等待 MySQL 就绪（最多 60 秒）
    db = None
    for attempt in range(1, 13):
        try:
            db = SessionLocal()
            db.execute(__import__('sqlalchemy').text('SELECT 1'))
            db.close()
            db = None
            logger.info("✅ MySQL 已就绪，开始初始化调度器")
            break
        except Exception as e:
            if db:
                try:
                    db.close()
                except Exception:
                    pass
                db = None
            logger.warning(f"MySQL 未就绪，等待重试 ({attempt}/12): {e}")
            time.sleep(5)
    else:
        logger.error("MySQL 等待超时（60s），调度器初始化跳过，定时任务不会运行")
        return

    try:
        # 启动调度器
        scheduler.start()

        # 从数据库加载所有定时任务配置
        scheduler.reload_config_from_db()
        logger.info("✅ 所有定时任务配置已加载")

        # 注册配置轮询任务（每60秒检查一次DB，感知页面配置变更）
        scheduler.scheduler.add_job(
            func=scheduler._config_watcher,
            trigger=IntervalTrigger(seconds=60),
            id="config_watcher",
            name="配置变更轮询",
            replace_existing=True,
        )
        logger.info("✅ 配置变更轮询任务已注册（间隔60秒）")

    except Exception as e:
        logger.error(f"初始化调度器失败: {e}")


def shutdown_scheduler():
    """关闭调度器"""
    scheduler.stop()
