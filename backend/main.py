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
    import time
    import random
    
    logger.info("应用启动中...")
    app.state.debug = settings.DEBUG
    ensure_directories()
    
    # 初始化用户数据库（带重试机制）
    max_db_retries = 5
    db_retry_delay = 2  # 秒
    
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
            time.sleep(random.uniform(0.1, 0.5))  # 随机延迟避免并发冲突
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
                        time.sleep(0.5 * (attempt + 1))
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
                time.sleep(db_retry_delay)
            else:
                logger.error(f"❌ 数据库初始化失败（已重试 {max_db_retries} 次）: {e}")
                logger.error("⚠️ 应用将继续启动，但数据库功能可能不可用")
    
    # 初始化 AI 服务（向量数据库等）
    try:
        from app.services.ai.init import initialize_ai_services, shutdown_ai_services
        await initialize_ai_services()
    except Exception as e:
        logger.warning(f"⚠️ AI 服务初始化失败: {e}")
        logger.warning("AI 智能查询功能将不可用")
    
    # 启动后台报告向量化任务
    vectorization_task = None
    try:
        from app.services.ai.report_vectorization_service import background_vectorization_task
        import asyncio
        
        # 创建后台任务（每 5 分钟扫描一次）
        vectorization_task = asyncio.create_task(background_vectorization_task(interval_seconds=300))
        logger.info("✅ 后台报告向量化任务已启动（扫描间隔: 5 分钟）")
    except Exception as e:
        logger.warning(f"⚠️ 后台向量化任务启动失败: {e}")
    
    # 启动定时清理任务
    cleanup_scheduler = None
    try:
        from app.services.ai.cleanup_scheduler import start_cleanup_scheduler, get_cleanup_scheduler
        
        # 启动清理调度器（每周执行一次，清理软删除超过 30 天的条目）
        await start_cleanup_scheduler()
        cleanup_scheduler = get_cleanup_scheduler()
        logger.info("✅ 定时清理任务已启动（执行间隔: 7 天，清理阈值: 30 天）")
    except Exception as e:
        logger.warning(f"⚠️ 定时清理任务启动失败: {e}")
    
    # 启动CMDB定时同步调度器
    try:
        from app.core.scheduler import init_scheduler
        init_scheduler()
        logger.info("✅ CMDB定时同步调度器已启动")
    except Exception as e:
        logger.warning(f"⚠️ CMDB定时同步调度器启动失败: {e}")
    
    # 启动文件监控服务
    file_watcher = None
    try:
        from app.services.alert.file_watcher import FileWatcherService
        
        file_watcher = FileWatcherService()
        file_watcher.start_monitoring()
        
        # 延迟处理已存在的文件（给MySQL更多时间准备）
        # 使用后台线程延迟并检查MySQL就绪后处理，避免阻塞启动
        import threading
        def delayed_process_existing_files():
            import time
            logger.info("等待MySQL完全就绪后处理已存在的告警文件...")
            
            # MySQL初始化需要约6分钟，最多等待360秒
            wait_time = 360
            check_interval = 30  # 每30秒检查一次
            
            for i in range(0, wait_time, check_interval):
                time.sleep(check_interval)
                elapsed = i + check_interval
                logger.info(f"已等待 {elapsed}/{wait_time} 秒...")
                
                # 尝试连接MySQL检查是否就绪
                try:
                    from app.core.deps import SessionLocal
                    db = SessionLocal()
                    # 执行简单查询测试连接
                    db.execute("SELECT 1")
                    db.close()
                    logger.info("✅ MySQL连接成功，开始处理告警文件")
                    break
                except Exception as e:
                    logger.debug(f"MySQL尚未就绪: {str(e)}")
                    if elapsed >= wait_time:
                        logger.warning("⚠️ 等待超时，强制开始处理")
            
            logger.info("开始处理已存在的告警文件...")
            try:
                logger.info(f"file_watcher对象: {file_watcher}")
                logger.info(f"process_existing_files方法: {file_watcher.process_existing_files}")
                file_watcher.process_existing_files()
                logger.info("✅ process_existing_files()调用完成")
            except Exception as e:
                logger.error(f"❌ 处理已存在文件失败: {e}", exc_info=True)
        
        threading.Thread(target=delayed_process_existing_files, daemon=True).start()
        
        # 保存到app.state以便后续访问
        app.state.file_watcher = file_watcher
        logger.info("✅ 文件监控服务已启动（已存在文件将在MySQL就绪后处理，最多等待6分钟）")
    except Exception as e:
        logger.error(f"❌ 文件监控服务启动失败: {e}", exc_info=True)
    
    logger.info(f"{settings.APP_NAME} v{settings.APP_VERSION} 启动成功")
    yield
    logger.info("应用关闭中...")
    
    # 停止文件监控服务
    if file_watcher:
        try:
            file_watcher.stop()
            logger.info("✅ 文件监控服务已停止")
        except Exception as e:
            logger.warning(f"⚠️ 停止文件监控服务失败: {e}")
    
    # 停止定时清理任务
    if cleanup_scheduler:
        try:
            await cleanup_scheduler.stop()
            logger.info("✅ 定时清理任务已停止")
        except Exception as e:
            logger.warning(f"⚠️ 停止定时清理任务失败: {e}")
    
    # 停止CMDB定时同步调度器
    try:
        from app.core.scheduler import shutdown_scheduler
        shutdown_scheduler()
        logger.info("✅ CMDB定时同步调度器已停止")
    except Exception as e:
        logger.warning(f"⚠️ 停止CMDB定时同步调度器失败: {e}")
    
    # 停止后台向量化任务
    if vectorization_task:
        try:
            vectorization_task.cancel()
            try:
                await vectorization_task
            except asyncio.CancelledError:
                logger.info("✅ 后台向量化任务已停止")
        except Exception as e:
            logger.warning(f"⚠️ 停止后台向量化任务失败: {e}")
    
    # 关闭 AI 服务
    try:
        from app.services.ai.init import shutdown_ai_services
        shutdown_ai_services()
    except Exception as e:
        logger.warning(f"⚠️ AI 服务关闭失败: {e}")
    
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

# AI 智能查询路由
from app.api.v1 import ai_intelligent_query
app.include_router(ai_intelligent_query.router, prefix=f"{settings.API_V1_PREFIX}/ai", tags=["AI 智能查询"])

# 知识库管理认证路由
from app.api.v1 import knowledge_auth
app.include_router(knowledge_auth.router, prefix=f"{settings.API_V1_PREFIX}/knowledge/auth", tags=["知识库管理认证"])

# 知识库管理接口路由
from app.api.v1 import knowledge_entries
app.include_router(knowledge_entries.router, prefix=f"{settings.API_V1_PREFIX}/knowledge", tags=["知识库管理"])

# HAS 硬件告警 Webhook 路由
from app.api.v1 import has_webhook
app.include_router(has_webhook.router, prefix=settings.API_V1_PREFIX, tags=["HAS 硬件告警"])

# 实例配置管理路由
from app.api.v1 import instance_config
app.include_router(instance_config.router, prefix=settings.API_V1_PREFIX, tags=["实例配置管理"])

# 系统配置管理路由
from app.api.v1 import config
app.include_router(config.router, prefix=settings.API_V1_PREFIX, tags=["系统配置管理"])

# 路由规则管理路由
from app.api.v1 import routing
app.include_router(routing.router, prefix=f"{settings.API_V1_PREFIX}/routing", tags=["路由规则管理"])

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
