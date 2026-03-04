#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Redis客户端配置
用于任务状态存储和缓存
"""
import redis
import json
from typing import Optional, Dict, Any
from app.core.logger import logger
import os

class RedisClient:
    """Redis客户端封装"""

    def __init__(self):
        self.host = os.getenv('REDIS_HOST', 'localhost')
        self.port = int(os.getenv('REDIS_PORT', 6379))
        self.password = os.getenv('REDIS_PASSWORD', None)
        self.db = int(os.getenv('REDIS_DB', 0))

        self.client = redis.Redis(
            host=self.host,
            port=self.port,
            password=self.password,
            db=self.db,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True
        )

        # 测试连接
        try:
            self.client.ping()
            logger.info(f"✅ Redis连接成功: {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"❌ Redis连接失败: {e}")
            self.client = None  # 标记连接失败

    def set_task_status(self, task_id: str, status_data: Dict[str, Any], expire: int = 3600):
        """设置任务状态"""
        if not self.client:
            logger.warning("Redis未连接，跳过状态保存")
            return
        try:
            key = f"task:{task_id}"
            value = json.dumps(status_data, ensure_ascii=False)
            self.client.setex(key, expire, value)
            logger.debug(f"任务状态已保存: {task_id}")
        except Exception as e:
            logger.error(f"保存任务状态失败: {task_id}, 错误: {e}")

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务状态

        Args:
            task_id: 任务ID

        Returns:
            任务状态数据，不存在返回None
        """
        try:
            key = f"task:{task_id}"
            value = self.client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"获取任务状态失败: {task_id}, 错误: {e}")
            return None

    def delete_task_status(self, task_id: str):
        """删除任务状态"""
        try:
            key = f"task:{task_id}"
            self.client.delete(key)
            logger.debug(f"任务状态已删除: {task_id}")
        except Exception as e:
            logger.error(f"删除任务状态失败: {task_id}, 错误: {e}")

    def set_cache(self, key: str, value: Any, expire: int = 300):
        """设置缓存"""
        try:
            val = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
            self.client.setex(key, expire, val)
        except Exception as e:
            logger.error(f"设置缓存失败: {key}, 错误: {e}")

    def get_cache(self, key: str) -> Optional[Any]:
        """获取缓存"""
        try:
            value = self.client.get(key)
            if value:
                try:
                    return json.loads(value)
                except:
                    return value
            return None
        except Exception as e:
            logger.error(f"获取缓存失败: {key}, 错误: {e}")
            return None

    def delete_cache(self, key: str):
        """删除缓存"""
        try:
            self.client.delete(key)
        except Exception as e:
            logger.error(f"删除缓存失败: {key}, 错误: {e}")


    def set(self, key: str, value: Any, ex: Optional[int] = None, nx: bool = False):
        """
        设置键值对（通用方法）
        
        Args:
            key: 键名
            value: 值（自动序列化为 JSON）
            ex: 过期时间（秒），None 表示永不过期
            nx: 如果为 True，仅当 key 不存在时才设置（SET NX）
        
        Returns:
            bool: 设置是否成功（nx=True 时，如果 key 已存在则返回 False）
        """
        if not self.client:
            logger.warning("Redis未连接，跳过设置")
            return False
        try:
            val = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
            # 使用 redis-py 的 set() 方法，支持 nx 和 ex 参数
            result = self.client.set(key, val, ex=ex, nx=nx)
            if result:
                logger.debug(f"Redis set: {key}")
            return bool(result)
        except Exception as e:
            logger.error(f"Redis set 失败: {key}, 错误: {e}")
            return False
    
    def get(self, key: str) -> Optional[Any]:
        """
        获取键值（通用方法）
        
        Args:
            key: 键名
        
        Returns:
            值（自动反序列化 JSON），不存在返回 None
        """
        if not self.client:
            logger.warning("Redis未连接，跳过获取")
            return None
        try:
            value = self.client.get(key)
            if value:
                try:
                    return json.loads(value)
                except:
                    return value
            return None
        except Exception as e:
            logger.error(f"Redis get 失败: {key}, 错误: {e}")
            return None
    
    def delete(self, key: str):
        """
        删除键（通用方法）
        
        Args:
            key: 键名
        """
        if not self.client:
            logger.warning("Redis未连接，跳过删除")
            return False
        try:
            self.client.delete(key)
            logger.debug(f"Redis delete: {key}")
            return True
        except Exception as e:
            logger.error(f"Redis delete 失败: {key}, 错误: {e}")
            return False


# 全局Redis客户端实例
_redis_client: Optional[RedisClient] = None

def get_redis_client() -> RedisClient:
    """获取Redis客户端单例"""
    global _redis_client
    if _redis_client is None:
        _redis_client = RedisClient()
    return _redis_client
