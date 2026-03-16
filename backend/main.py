#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
FastAPI 主应用入口
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
import os

from app.core.config import settings, ensure_directories
from app.core.database import init_db, close_db
from app.core.logger import setup_logging
from app.core.exceptions import ExceptionMiddleware, http_exception_handler, validation_exception_handler
from app.core.rate_limit import setup_rate_limit
from app.api.v1 import tasks, files, health, prometheus, resource, monitoring, monitoring_download, eip, operational, dashboard, users, reports, cmdb

from loguru import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    import asyncio
    import random

    logger.info("应用启动中...")
    app.state.debug = settings.DEBUG
    ensure_directories()

    # 初始化用户数据库（带重试机制）
    # 使用 asyncio.sleep 替代 time.sleep，避免阻塞事件循环导致 gunicorn worker 心跳超时
    max_db_retries = 10  # 增加到10次，适应内网MySQL启动较慢的情况
    db_retry_delay = 5  # 增加到5秒，给MySQL更多初始化时间

    for db_attempt in range(max_db_retries):
        try:
            from app.models.base import Base
            from app.core.deps import engine, SessionLocal
            from app.models.chat import ChatHistory  # 先导入 ChatHistory
            from app.models.user import User, AuditLog, UserRole, UserNote
            from app.models.task import Task
            from app.models.iaas import IaasServer, IaasInstance
            from app.models.cmdb_config import CMDBConfig, CMDBSyncLog  # CMDB配置和日志
            from app.models.instance_config import InstanceConfig  # 实例配置模型
            from app.models.system_config import SystemConfig  # 系统配置模型
            from app.models.alert import AlertRecord, DiagnosisResult, WebhookConfig, FaultManual  # 硬件告警模型
            from app.core.security import get_password_hash
            from sqlalchemy import text, inspect

            # 获取数据库中已存在的表
            inspector = inspect(engine)
            existing_tables = set(inspector.get_table_names())
            logger.info(f"数据库已有表: {existing_tables}")

            # 创建所有不存在的表
            tables_to_create = [t for t in Base.metadata.sorted_tables if t.name not in existing_tables]
            if tables_to_create:
                logger.info(f"需要创建的表: {[t.name for t in tables_to_create]}")
                for table in tables_to_create:
                    try:
                        table.create(bind=engine)
                        logger.info(f"✅ 创建表: {table.name}")
                    except Exception as e:
                        # 如果是表已存在错误，只记录info级别日志
                        if "already exists" in str(e).lower() or "1050" in str(e):
                            logger.info(f"ℹ️ 表 {table.name} 已存在，跳过创建")
                        else:
                            logger.warning(f"⚠️ 创建表 {table.name} 失败: {e}")
            else:
                logger.info("✅ 所有表已存在")

            # 初始化默认用户（带重试机制）
            await asyncio.sleep(random.uniform(0.1, 0.5))  # 随机延迟避免并发冲突
            max_retries = 3
            for attempt in range(max_retries):
                db = SessionLocal()
                try:
                    existing_admin = db.query(User).filter(User.username == "admin").first()
                    if not existing_admin:
                        admin = User(
                            username="admin",
                            hashed_password=get_password_hash("admin123"),
                            full_name="系统管理员",
                            role=UserRole.SUPER_ADMIN,
                            is_active=True
                        )
                        db.add(admin)
                        db.commit()
                        logger.info("✅ 默认管理员已创建: admin/admin123")
                    else:
                        logger.info("✅ 管理员账户已存在")
                    break

                except Exception as e:
                    db.rollback()
                    if attempt < max_retries - 1:
                        await asyncio.sleep(0.5 * (attempt + 1))
                    else:
                        logger.warning(f"⚠️ 管理员初始化跳过: {e}")
                finally:
                    db.close()

            # 数据库初始化成功，跳出重试循环
            logger.info("✅ 数据库初始化成功")
            break

        except Exception as e:
            if db_attempt < max_db_retries - 1:
                logger.warning(f"⚠️ 数据库初始化失败（尝试 {db_attempt + 1}/{max_db_retries}）: {e}")
                logger.info(f"⏳ {db_retry_delay} 秒后重试...")
                await asyncio.sleep(db_retry_delay)
            else:
                logger.error(f"❌ 数据库初始化失败（已重试 {max_db_retries} 次）: {e}")
                logger.error("⚠️ 应用将继续启动，但数据库功能可能不可用")
    
    # 启动CMDB定时同步调度器
    try:
        from app.core.scheduler import init_scheduler
        init_scheduler()
        logger.info("✅ CMDB定时同步调度器已启动")
    except Exception as e:
        logger.warning(f"⚠️ CMDB定时同步调度器启动失败: {e}")
    
    # 启动文件监控服务
    # 仅当监控源目录存在时才初始化（外网环境未挂载该目录，跳过以避免无意义的等待）
    file_watcher = None
    alerts_source_path = "/app/alerts_source"
    if os.path.exists(alerts_source_path):
        try:
            from app.services.alert.file_watcher import FileWatcherService

            file_watcher = FileWatcherService()

            # 使用后台线程等待MySQL就绪后处理已存在文件，然后启动实时监控
            import threading
            def delayed_init_file_watcher():
                import time as _time
                logger.info("等待MySQL完全就绪后初始化文件监控...")

                # MySQL初始化需要约6分钟，最多等待360秒
                wait_time = 360
                check_interval = 30  # 每30秒检查一次

                for i in range(0, wait_time, check_interval):
                    _time.sleep(check_interval)
                    elapsed = i + check_interval
                    logger.info(f"已等待 {elapsed}/{wait_time} 秒...")

                    # 尝试连接MySQL检查是否就绪
                    try:
                        from app.core.deps import SessionLocal
                        db = SessionLocal()
                        # 执行简单查询测试连接
                        db.execute("SELECT 1")
                        db.close()
                        logger.info("✅ MySQL连接成功")
                        break
                    except Exception as e:
                        logger.debug(f"MySQL尚未就绪: {str(e)}")
                        if elapsed >= wait_time:
                            logger.warning("⚠️ 等待超时，强制开始处理")

                # 步骤1: 先处理已存在的文件（此时Observer未启动，不会重复标记）
                logger.info("步骤1: 处理已存在的告警文件...")
                try:
                    file_watcher.process_existing_files()
                    logger.info("✅ 已存在文件处理完成")
                except Exception as e:
                    logger.error(f"❌ 处理已存在文件失败: {e}", exc_info=True)

                # 步骤2: 启动实时监控（监控新增文件）
                logger.info("步骤2: 启动实时文件监控...")
                try:
                    file_watcher.start_monitoring()
                    logger.info("✅ 实时文件监控已启动")
                except Exception as e:
                    logger.error(f"❌ 启动文件监控失败: {e}", exc_info=True)

            threading.Thread(target=delayed_init_file_watcher, daemon=True).start()

            # 保存到app.state以便后续访问
            app.state.file_watcher = file_watcher
            logger.info("✅ 文件监控服务已启动（已存在文件将在MySQL就绪后处理，最多等待6分钟）")
        except Exception as e:
            logger.error(f"❌ 文件监控服务启动失败: {e}", exc_info=True)
    else:
        logger.info(f"ℹ️ 告警源目录不存在({alerts_source_path})，跳过文件监控服务初始化")
    
    logger.info(f"{settings.APP_NAME} v{settings.APP_VERSION} 应用启动成功")
    yield
    logger.info("应用关闭中...")

    # 停止文件监控服务
    if file_watcher:
        try:
            file_watcher.stop()
            logger.info("✅ 文件监控服务已停止")
        except Exception as e:
            logger.warning(f"⚠️ 停止文件监控服务失败: {e}")

    # 停止CMDB定时同步调度器
    try:
        from app.core.scheduler import shutdown_scheduler
        shutdown_scheduler()
        logger.info("✅ CMDB定时同步调度器已停止")
    except Exception as e:
        logger.warning(f"⚠️ 停止CMDB定时同步调度器失败: {e}")
    
    await close_db()


# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="集群管理平台API",
    lifespan=lifespan,
)

# 限流（先添加）
setup_rate_limit(app)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins if not settings.DEBUG else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 异常处理（最后添加，最先执行）
app.add_middleware(ExceptionMiddleware)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

# 注册路由
app.include_router(health.router, prefix=settings.API_V1_PREFIX, tags=["健康检查"])
app.include_router(users.router, prefix=settings.API_V1_PREFIX, tags=["用户认证与权限"])
app.include_router(dashboard.router, prefix=f"{settings.API_V1_PREFIX}/dashboard", tags=["仪表盘"])
app.include_router(files.router, prefix=settings.API_V1_PREFIX, tags=["文件管理"])
app.include_router(tasks.router, prefix=settings.API_V1_PREFIX, tags=["任务管理"])
app.include_router(reports.router, prefix=f"{settings.API_V1_PREFIX}/reports", tags=["报告下载"])
app.include_router(operational.router, prefix=settings.API_V1_PREFIX, tags=["运营数据分析"])
app.include_router(prometheus.router, prefix=f"{settings.API_V1_PREFIX}/prometheus", tags=["Prometheus监控"])
app.include_router(resource.router, prefix=f"{settings.API_V1_PREFIX}/resource", tags=["资源分析"])
app.include_router(monitoring.router, prefix=settings.API_V1_PREFIX, tags=["监控分析"])
app.include_router(monitoring_download.router, prefix=settings.API_V1_PREFIX, tags=["监控分析"])
app.include_router(eip.router, prefix=settings.API_V1_PREFIX, tags=["EIP带宽监控"])
app.include_router(cmdb.router, prefix=f"{settings.API_V1_PREFIX}/cmdb", tags=["CMDB资源管理"])

# AI 对话路由
from app.api.v1 import ai_chat
app.include_router(ai_chat.router, prefix=f"{settings.API_V1_PREFIX}/ai", tags=["AI 对话助手"])

# HAS 硬件告警 Webhook 路由
from app.api.v1 import has_webhook
app.include_router(has_webhook.router, prefix=settings.API_V1_PREFIX, tags=["HAS 硬件告警"])

# 实例配置管理路由
from app.api.v1 import instance_config
app.include_router(instance_config.router, prefix=settings.API_V1_PREFIX, tags=["实例配置管理"])

# 系统配置管理路由
from app.api.v1 import config
app.include_router(config.router, prefix=settings.API_V1_PREFIX, tags=["系统配置管理"])

# PFS 监控路由
from app.api.v1 import pfs
app.include_router(pfs.router, prefix=f"{settings.API_V1_PREFIX}/pfs", tags=["PFS 监控"])

# 硬件告警管理路由（统一注册）
from app.api.v1.api import api_router
app.include_router(api_router, prefix=settings.API_V1_PREFIX, tags=["硬件告警管理"])

# 静态文件
results_dir = settings.RESULT_DIR
if os.path.exists(results_dir):
    app.mount("/results", StaticFiles(directory=results_dir), name="results")

reports_dir = os.path.join(os.path.dirname(__file__), "data", "reports")
os.makedirs(reports_dir, exist_ok=True)
app.mount("/reports", StaticFiles(directory=reports_dir), name="reports")


@app.get("/")
async def root():
    return {"app": settings.APP_NAME, "version": settings.APP_VERSION, "docs": "/docs", "status": "running"}


setup_logging()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
