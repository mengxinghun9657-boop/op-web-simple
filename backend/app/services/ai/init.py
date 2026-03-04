#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI 服务初始化模块
在应用启动时初始化向量数据库、ERNIE API 客户端和 Embedding 模型等 AI 相关服务
"""

from app.core.logger import logger
from app.core.config import settings
from app.services.ai.vector_store import get_vector_store
from app.services.ai.ernie_client import get_ernie_client
from app.services.ai.embedding_model import get_embedding_model


async def initialize_ai_services():
    """
    初始化 AI 相关服务（异步版本）
    
    包括：
    1. 向量数据库初始化
    2. ERNIE API 客户端初始化
    3. Embedding 模型初始化
    4. Schema 向量存储初始化 🆕
    5. 健康检查
    6. 目录结构验证
    """
    logger.info("Initializing AI services...")
    
    success_count = 0
    total_count = 4  # 增加到 4 个服务
    
    # 1. 初始化向量数据库
    try:
        logger.info("Initializing vector store...")
        vector_store = get_vector_store()
        
        # 健康检查
        health = vector_store.health_check()
        logger.info(f"Vector store health check: {health}")
        
        if health["status"] != "healthy":
            logger.warning(f"Vector store is not healthy: {health}")
        else:
            logger.info(f"Vector store initialized successfully: "
                       f"{health['total_vectors']} vectors, "
                       f"{health['total_entries']} entries")
            success_count += 1
    except Exception as e:
        logger.error(f"Failed to initialize vector store: {e}")
    
    # 2. 初始化 ERNIE API 客户端
    try:
        logger.info("Initializing ERNIE API client...")
        ernie_client = get_ernie_client()
        logger.info(f"ERNIE API client initialized: url={ernie_client.api_url}, model={ernie_client.current_model}")
        success_count += 1
    except Exception as e:
        logger.error(f"Failed to initialize ERNIE API client: {e}")
    
    # 3. 初始化 Embedding 模型
    embedding_model = None
    try:
        logger.info("Initializing Embedding model...")
        embedding_model = get_embedding_model()
        logger.info(f"Embedding model initialized: model={embedding_model.model_name}, "
                   f"use_api={embedding_model.use_api}, use_cache={embedding_model.use_cache}")
        success_count += 1
    except Exception as e:
        logger.error(f"Failed to initialize Embedding model: {e}")
    
    # 4. 初始化 Schema 向量存储 🆕（带重试逻辑和优雅降级）
    try:
        logger.info("Initializing Schema vector store...")
        from app.services.ai.schema_vector_store import get_schema_vector_store
        import asyncio
        
        # 检查是否配置了 Embedding API
        if not embedding_model or not embedding_model.use_api or not embedding_model.api_url:
            logger.warning("⚠️ Embedding API 未配置，跳过 Schema 向量化")
            logger.info("💡 SQL 生成将使用降级策略（常用表列表）")
        else:
            # 传递 embedding_model 实例，确保使用相同的配置
            schema_vector_store = get_schema_vector_store(embedding_model=embedding_model)
            
            # 重试加载 Schema（等待 MySQL 就绪）
            max_retries = 3  # 减少重试次数（外网环境快速失败）
            retry_delay = 5  # 减少延迟时间（秒）
            table_count = 0
            
            for attempt in range(1, max_retries + 1):
                try:
                    logger.info(f"Loading Schema (attempt {attempt}/{max_retries})...")
                    table_count = await schema_vector_store.load_schema()
                    
                    if table_count > 0:
                        logger.info(f"✅ Schema vector store initialized successfully: {table_count} tables loaded")
                        success_count += 1
                        break
                    else:
                        logger.warning(f"⚠️ Schema loaded but no tables found (attempt {attempt}/{max_retries})")
                        if attempt < max_retries:
                            logger.info(f"Retrying in {retry_delay} seconds...")
                            await asyncio.sleep(retry_delay)
                        
                except Exception as e:
                    logger.warning(f"⚠️ Schema loading failed (attempt {attempt}/{max_retries}): {str(e)[:200]}")
                    
                    # 检查是否是 Embedding API 连接错误
                    if "ConnectTimeout" in str(e) or "Connection" in str(e):
                        logger.warning("⚠️ Embedding API 不可用，跳过 Schema 向量化")
                        logger.info("💡 这在外网环境是正常的，内网部署后会自动启用")
                        break  # 不再重试，直接跳过
                    
                    if attempt < max_retries:
                        logger.info(f"Retrying in {retry_delay} seconds...")
                        await asyncio.sleep(retry_delay)
                    else:
                        # 最后一次尝试失败
                        raise
            
            if table_count == 0:
                logger.warning("⚠️ Schema 向量化未完成")
                logger.info("💡 SQL 生成将使用降级策略（常用表列表）")
            
    except Exception as e:
        logger.warning(f"⚠️ Schema vector store initialization skipped: {str(e)[:200]}")
        logger.info("💡 SQL 生成将使用降级策略（常用表列表）")
        logger.info("💡 这在外网环境是正常的，内网部署后会自动启用")
    
    # 5. 验证配置
    logger.info("Verifying AI service configurations...")
    logger.info(f"Vector DB type: {settings.VECTOR_DB_TYPE}")
    logger.info(f"Vector DB path: {settings.VECTOR_DB_PATH}")
    logger.info(f"Vector dimension: {settings.VECTOR_DIMENSION}")
    logger.info(f"ERNIE API URL: {getattr(settings, 'ERNIE_API_URL', 'Not configured')}")
    logger.info(f"ERNIE Model: {getattr(settings, 'ERNIE_MODEL', 'Not configured')}")
    logger.info(f"Embedding model: {settings.EMBEDDING_MODEL}")
    
    # 总结
    if success_count == total_count:
        logger.info(f"AI services initialized successfully ✓ ({success_count}/{total_count})")
        return True
    else:
        logger.warning(f"AI services partially initialized ({success_count}/{total_count})")
        logger.warning("Some AI features may not be available")
        return False


async def shutdown_ai_services():
    """
    关闭 AI 相关服务
    
    在应用关闭时调用，确保数据持久化和资源释放
    """
    logger.info("Shutting down AI services...")
    
    success_count = 0
    total_count = 3
    
    # 1. 保存向量数据库
    try:
        vector_store = get_vector_store()
        vector_store.save()
        logger.info("Vector store saved successfully")
        success_count += 1
    except Exception as e:
        logger.error(f"Failed to save vector store: {e}")
    
    # 2. 关闭 ERNIE API 客户端
    try:
        from app.services.ai.ernie_client import close_ernie_client
        await close_ernie_client()
        logger.info("ERNIE API client closed successfully")
        success_count += 1
    except Exception as e:
        logger.error(f"Failed to close ERNIE API client: {e}")
    
    # 3. 关闭 Embedding 模型
    try:
        from app.services.ai.embedding_model import close_embedding_model
        await close_embedding_model()
        logger.info("Embedding model closed successfully")
        success_count += 1
    except Exception as e:
        logger.error(f"Failed to close Embedding model: {e}")
    
    # 总结
    if success_count == total_count:
        logger.info(f"AI services shut down successfully ✓ ({success_count}/{total_count})")
        return True
    else:
        logger.warning(f"AI services partially shut down ({success_count}/{total_count})")
        return False
