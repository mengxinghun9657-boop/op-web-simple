#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Embedding 模型封装
支持本地模型和远程 API 两种方式进行文本向量化
"""

import asyncio
import time
import hashlib
from typing import List, Optional, Union, Dict, Any
import numpy as np
import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

from app.core.config import settings
from app.core.logger import logger


class EmbeddingModel:
    """
    Embedding 模型封装
    
    功能：
    - 文本向量化（单个和批量）
    - 支持本地模型（bge-small-zh）和远程 API
    - 向量相似度计算（余弦相似度）
    - Redis 缓存机制（可选）
    - 重试机制和错误处理
    
    使用示例：
    ```python
    model = EmbeddingModel()
    
    # 单个文本向量化
    embedding = await model.encode("这是一段测试文本")
    
    # 批量向量化
    embeddings = await model.encode_batch(["文本1", "文本2", "文本3"])
    
    # 计算相似度
    similarity = model.cosine_similarity(embedding1, embedding2)
    ```
    """
    
    def __init__(
        self,
        model_name: Optional[str] = None,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        use_cache: bool = True,
        timeout: int = 60,
        max_retries: int = 2,
        use_local: bool = False
    ):
        """
        初始化 Embedding 模型
        
        Args:
            model_name: 模型名称，默认从配置读取
            api_url: API 地址（如果使用远程 API），默认从配置读取
            api_key: API 密钥（如果使用远程 API），默认从配置读取
            use_cache: 是否使用 Redis 缓存，默认 True
            timeout: 请求超时时间（秒），默认 60 秒
            max_retries: 最大重试次数，默认 2 次
            use_local: 是否使用本地模型，默认 False（使用 API）
        """
        self.model_name = model_name or settings.EMBEDDING_MODEL
        self.api_url = api_url or settings.EMBEDDING_API_URL
        self.api_key = api_key or settings.EMBEDDING_API_KEY
        self.use_cache = use_cache
        self.timeout = timeout
        self.max_retries = max_retries
        self.dimension = settings.VECTOR_DIMENSION
        
        # 判断使用本地模型还是远程 API
        # 优先使用 use_local 参数，其次检查配置，最后检查 API URL
        if use_local or getattr(settings, 'EMBEDDING_USE_LOCAL', False):
            self.use_api = False
        else:
            self.use_api = True  # 默认使用 API 模式
        
        # 本地模型
        self.local_model = None
        
        # HTTP 客户端（用于 API 调用）
        self.client = None
        
        # Redis 客户端（用于缓存）
        self.redis_client = None
        
        # 初始化
        self._initialize()
        
        logger.info(f"EmbeddingModel initialized: model={self.model_name}, use_api={self.use_api}, use_cache={use_cache}")
    
    def _initialize(self):
        """初始化模型或 API 客户端"""
        if self.use_api:
            # 使用远程 API
            if self.api_url:
                self.client = httpx.AsyncClient(
                    timeout=httpx.Timeout(self.timeout),
                    limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
                )
                logger.info(f"Using remote Embedding API: {self.api_url}")
            else:
                logger.warning("Embedding API URL not configured. Embedding functionality will be limited.")
                logger.warning("Please set EMBEDDING_API_URL in environment variables or .env file")
                logger.warning("Example: EMBEDDING_API_URL=https://your-embedding-api.com/v1/embeddings")
                # 不抛出异常，允许应用启动
        else:
            # 使用本地模型
            try:
                from sentence_transformers import SentenceTransformer
                self.local_model = SentenceTransformer(self.model_name)
                logger.info(f"Loaded local Embedding model: {self.model_name}")
            except ImportError as e:
                logger.warning(f"sentence-transformers not installed: {e}")
                logger.warning("Local model mode requires sentence-transformers>=2.3.0")
                logger.warning("Install with: pip install sentence-transformers>=2.3.0")
                logger.warning("Or switch to API mode by setting EMBEDDING_USE_LOCAL=False")
                # 降级到 API 模式
                self.use_api = True
                self.local_model = None
                if self.api_url:
                    self.client = httpx.AsyncClient(
                        timeout=httpx.Timeout(self.timeout),
                        limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
                    )
                    logger.info(f"Fallback to remote Embedding API: {self.api_url}")
                else:
                    logger.error("No API URL configured and local model unavailable.")
                    logger.error("Embedding functionality will NOT work until properly configured.")
            except Exception as e:
                logger.error(f"Failed to load local model: {e}")
                logger.warning("Falling back to API mode")
                self.use_api = True
                self.local_model = None
                if self.api_url:
                    self.client = httpx.AsyncClient(
                        timeout=httpx.Timeout(self.timeout),
                        limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
                    )
                    logger.info(f"Fallback to remote Embedding API: {self.api_url}")
        
        # 初始化 Redis 缓存（如果启用）
        if self.use_cache:
            try:
                import redis.asyncio as aioredis
                self.redis_client = aioredis.from_url(
                    f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}",
                    password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
                    decode_responses=False  # 存储二进制数据
                )
                logger.info("Redis cache enabled for embeddings")
            except Exception as e:
                logger.warning(f"Failed to initialize Redis cache: {e}. Cache disabled.")
                self.use_cache = False
    
    async def close(self):
        """关闭客户端连接"""
        if self.client:
            await self.client.aclose()
            logger.info("Embedding API client closed")
        
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Redis cache client closed")
    
    def _get_cache_key(self, text: str) -> str:
        """
        生成缓存键
        
        Args:
            text: 文本内容
        
        Returns:
            str: 缓存键
        """
        # 使用 MD5 哈希作为缓存键
        text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
        return f"embedding:{self.model_name}:{text_hash}"
    
    async def _get_from_cache(self, text: str) -> Optional[np.ndarray]:
        """
        从缓存获取向量
        
        Args:
            text: 文本内容
        
        Returns:
            Optional[np.ndarray]: 向量，如果不存在返回 None
        """
        if not self.use_cache or not self.redis_client:
            return None
        
        try:
            cache_key = self._get_cache_key(text)
            cached_data = await self.redis_client.get(cache_key)
            
            if cached_data:
                # 反序列化向量
                embedding = np.frombuffer(cached_data, dtype=np.float32)
                logger.debug(f"Cache hit for text: {text[:50]}...")
                return embedding
            
            return None
        
        except Exception as e:
            logger.warning(f"Failed to get from cache: {e}")
            return None
    
    async def _save_to_cache(self, text: str, embedding: np.ndarray, ttl: int = 86400):
        """
        保存向量到缓存
        
        Args:
            text: 文本内容
            embedding: 向量
            ttl: 缓存过期时间（秒），默认 24 小时
        """
        if not self.use_cache or not self.redis_client:
            return
        
        try:
            cache_key = self._get_cache_key(text)
            # 序列化向量
            cached_data = embedding.astype(np.float32).tobytes()
            await self.redis_client.setex(cache_key, ttl, cached_data)
            logger.debug(f"Saved to cache: {text[:50]}...")
        
        except Exception as e:
            logger.warning(f"Failed to save to cache: {e}")
    
    @retry(
        stop=stop_after_attempt(3),  # 最多尝试 3 次（1 次原始 + 2 次重试）
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        reraise=True
    )
    async def _encode_via_api(self, text: str) -> np.ndarray:
        """
        通过 API 进行向量化（带重试机制）
        
        Args:
            text: 文本内容
        
        Returns:
            np.ndarray: 向量
        """
        if not self.client:
            raise RuntimeError("API client not initialized")
        
        # 构建请求体（适配 P4 Embedding 服务格式）
        request_body = {
            "texts": [text]  # P4 服务期望 texts 数组
        }
        
        # 构建请求头
        headers = {
            "Content-Type": "application/json"
        }
        
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        logger.debug(f"Embedding API request: text_length={len(text)}")
        
        start_time = time.time()
        
        try:
            # 发送请求
            response = await self.client.post(
                self.api_url,
                json=request_body,
                headers=headers
            )
            
            # 检查 HTTP 状态码
            response.raise_for_status()
            
            # 解析响应
            result = response.json()
            
            # 提取向量（支持新旧两种格式）
            embedding = None
            
            # 格式 1: 符合 API 规范 {"success": true, "data": {"embeddings": [[...]]}}
            if isinstance(result, dict) and "success" in result:
                if not result.get("success", False):
                    error_msg = result.get("error", "Unknown error")
                    raise RuntimeError(f"Embedding API error: {error_msg}")
                
                data = result.get("data", {})
                if "embeddings" in data and len(data["embeddings"]) > 0:
                    embedding = np.array(data["embeddings"][0], dtype=np.float32)
            
            # 格式 2: 旧格式 {"embeddings": [[...]], ...}（向后兼容）
            elif isinstance(result, dict) and "embeddings" in result:
                if len(result["embeddings"]) > 0:
                    embedding = np.array(result["embeddings"][0], dtype=np.float32)
            
            # 格式 3: OpenAI 格式 {"data": [{"embedding": [...]}]}
            elif isinstance(result, dict) and "data" in result:
                if len(result["data"]) > 0 and "embedding" in result["data"][0]:
                    embedding = np.array(result["data"][0]["embedding"], dtype=np.float32)
            
            # 格式 4: 直接返回数组 [[...]]（极少见）
            elif isinstance(result, list) and len(result) > 0:
                embedding = np.array(result[0], dtype=np.float32)
            
            if embedding is None:
                raise ValueError(f"Unexpected API response format: {type(result)}")
            
            # 计算耗时
            elapsed_time = (time.time() - start_time) * 1000
            
            logger.debug(f"Embedding API response: status=success, elapsed_time={elapsed_time:.2f}ms, dimension={len(embedding)}")
            
            return embedding
        
        except httpx.TimeoutException as e:
            elapsed_time = (time.time() - start_time) * 1000
            logger.warning(f"Embedding API timeout: elapsed_time={elapsed_time:.2f}ms, error={str(e)}")
            raise
        
        except httpx.NetworkError as e:
            elapsed_time = (time.time() - start_time) * 1000
            logger.warning(f"Embedding API network error: elapsed_time={elapsed_time:.2f}ms, error={str(e)}")
            raise
        
        except Exception as e:
            elapsed_time = (time.time() - start_time) * 1000
            logger.error(f"Embedding API error: elapsed_time={elapsed_time:.2f}ms, error={str(e)}")
            raise
    
    def _encode_via_local_model(self, text: str) -> np.ndarray:
        """
        通过本地模型进行向量化
        
        Args:
            text: 文本内容
        
        Returns:
            np.ndarray: 向量
        """
        if not self.local_model:
            raise RuntimeError("Local model not initialized")
        
        logger.debug(f"Local model encoding: text_length={len(text)}")
        
        start_time = time.time()
        
        try:
            # 编码
            embedding = self.local_model.encode(text, convert_to_numpy=True)
            
            # 计算耗时
            elapsed_time = (time.time() - start_time) * 1000
            
            logger.debug(f"Local model encoding: status=success, elapsed_time={elapsed_time:.2f}ms, dimension={len(embedding)}")
            
            return embedding.astype(np.float32)
        
        except Exception as e:
            elapsed_time = (time.time() - start_time) * 1000
            logger.error(f"Local model encoding error: elapsed_time={elapsed_time:.2f}ms, error={str(e)}")
            raise
    
    async def encode(self, text: str) -> np.ndarray:
        """
        文本向量化
        
        Args:
            text: 文本内容
        
        Returns:
            np.ndarray: 向量（768 维）
        
        Raises:
            ValueError: 文本为空
            RuntimeError: Embedding 功能不可用
            Exception: 向量化失败
        """
        # 验证参数
        if not text or not text.strip():
            raise ValueError("text cannot be empty")
        
        # 检查 Embedding 功能是否可用
        if not self.use_api and not self.local_model:
            raise RuntimeError(
                "Embedding functionality is not available. "
                "Please configure API URL or install sentence-transformers>=2.3.0"
            )
        
        # 检查缓存
        cached_embedding = await self._get_from_cache(text)
        if cached_embedding is not None:
            return cached_embedding
        
        # 向量化
        try:
            if self.use_api:
                if not self.client:
                    raise RuntimeError("API client not initialized. Please configure EMBEDDING_API_URL")
                embedding = await self._encode_via_api(text)
            else:
                if not self.local_model:
                    raise RuntimeError("Local model not loaded. Please install sentence-transformers>=2.3.0")
                # 本地模型是同步的，需要在线程池中运行
                loop = asyncio.get_event_loop()
                embedding = await loop.run_in_executor(None, self._encode_via_local_model, text)
        except RuntimeError:
            # 重新抛出 RuntimeError
            raise
        except Exception as e:
            logger.error(f"Encoding failed: {e}")
            raise RuntimeError(f"Failed to encode text: {str(e)}") from e
        
        # 保存到缓存
        await self._save_to_cache(text, embedding)
        
        return embedding
    
    async def encode_batch(
        self,
        texts: List[str],
        batch_size: int = 32
    ) -> List[np.ndarray]:
        """
        批量文本向量化
        
        Args:
            texts: 文本列表
            batch_size: 批次大小，默认 32
        
        Returns:
            List[np.ndarray]: 向量列表
        """
        if not texts:
            return []
        
        logger.info(f"Batch encoding: {len(texts)} texts")
        
        embeddings = []
        
        # 分批处理
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            
            # 并发处理每个批次
            batch_embeddings = await asyncio.gather(
                *[self.encode(text) for text in batch_texts],
                return_exceptions=True
            )
            
            # 处理结果
            for j, result in enumerate(batch_embeddings):
                if isinstance(result, Exception):
                    logger.error(f"Failed to encode text {i+j}: {result}")
                    # 使用零向量作为占位符
                    embeddings.append(np.zeros(self.dimension, dtype=np.float32))
                else:
                    embeddings.append(result)
        
        logger.info(f"Batch encoding completed: {len(embeddings)}/{len(texts)} successful")
        
        return embeddings
    
    @staticmethod
    def cosine_similarity(
        embedding1: np.ndarray,
        embedding2: np.ndarray
    ) -> float:
        """
        计算余弦相似度
        
        Args:
            embedding1: 向量1
            embedding2: 向量2
        
        Returns:
            float: 余弦相似度（-1 到 1）
        """
        # 归一化
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        # 计算余弦相似度
        similarity = np.dot(embedding1, embedding2) / (norm1 * norm2)
        
        return float(similarity)
    
    @staticmethod
    def normalize(embedding: np.ndarray) -> np.ndarray:
        """
        归一化向量
        
        Args:
            embedding: 向量
        
        Returns:
            np.ndarray: 归一化后的向量
        """
        norm = np.linalg.norm(embedding)
        if norm == 0:
            return embedding
        return embedding / norm
    
    async def health_check(self) -> Dict[str, Any]:
        """
        健康检查
        
        Returns:
            Dict: 健康状态信息
        """
        try:
            # 测试向量化
            test_text = "健康检查测试文本"
            embedding = await self.encode(test_text)
            
            status = {
                "status": "healthy",
                "model": self.model_name,
                "use_api": self.use_api,
                "use_cache": self.use_cache,
                "dimension": len(embedding),
                "test_encoding": "success"
            }
            
            # 检查缓存
            if self.use_cache and self.redis_client:
                try:
                    await self.redis_client.ping()
                    status["cache_status"] = "connected"
                except Exception as e:
                    status["cache_status"] = f"error: {str(e)}"
            
            return status
        
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    async def quick_health_check(self, timeout: float = 2.0) -> bool:
        """
        快速健康检查（用于启动时预检查）

        Args:
            timeout: 超时时间（秒），默认 2 秒

        Returns:
            bool: True 表示服务可用，False 表示不可用
        """
        if not self.use_api or not self.client:
            # 本地模型模式，直接返回可用
            return self.local_model is not None

        try:
            # 创建临时客户端，使用短超时
            async with httpx.AsyncClient(timeout=httpx.Timeout(timeout)) as temp_client:
                # 发送简单的测试请求
                response = await temp_client.post(
                    self.api_url,
                    json={"texts": ["test"]},
                    headers={"Content-Type": "application/json"}
                )

                # 只要能连接上就算成功（不检查响应内容）
                return response.status_code in [200, 201]

        except (httpx.TimeoutException, httpx.ConnectTimeout, httpx.NetworkError) as e:
            logger.debug(f"Quick health check failed (connection issue): {type(e).__name__}")
            return False
        except Exception as e:
            logger.debug(f"Quick health check failed: {str(e)[:100]}")
            return False

    async def health_check(self) -> Dict[str, Any]:
        """
        健康检查
        
        Returns:
            Dict: 健康状态信息
        """
        try:
            # 测试向量化
            test_text = "健康检查测试文本"
            embedding = await self.encode(test_text)
            
            status = {
                "status": "healthy",
                "model": self.model_name,
                "use_api": self.use_api,
                "use_cache": self.use_cache,
                "dimension": len(embedding),
                "test_encoding": "success"
            }
            
            # 检查缓存
            if self.use_cache and self.redis_client:
                try:
                    await self.redis_client.ping()
                    status["cache_status"] = "connected"
                except Exception as e:
                    status["cache_status"] = f"error: {str(e)}"
            
            return status
        
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    def __del__(self):
        """析构函数"""
        try:
            # 注意：在异步环境中，析构函数可能无法正确关闭异步客户端
            # 建议显式调用 close() 方法
            pass
        except Exception:
            pass


# 创建全局实例（单例模式）
_embedding_model_instance: Optional[EmbeddingModel] = None


def get_embedding_model() -> EmbeddingModel:
    """
    获取 Embedding 模型实例（单例模式）
    
    Returns:
        EmbeddingModel: Embedding 模型实例
    """
    global _embedding_model_instance
    
    if _embedding_model_instance is None:
        _embedding_model_instance = EmbeddingModel()
    
    return _embedding_model_instance


async def close_embedding_model():
    """关闭全局 Embedding 模型实例"""
    global _embedding_model_instance
    
    if _embedding_model_instance is not None:
        await _embedding_model_instance.close()
        _embedding_model_instance = None
