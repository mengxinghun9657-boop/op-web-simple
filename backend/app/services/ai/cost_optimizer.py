#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
成本优化器（Cost Optimizer）

基于字节跳动RAG最佳实践 13.2节 - 成本优化

功能：
1. 简单查询判断（IP地址、实例ID、单表查询）
2. Redis缓存高频查询结果
3. 缓存命中率监控
4. 成本节省统计
"""

import json
import hashlib
from typing import Dict, Optional, Tuple, Any
from datetime import datetime, timedelta

from app.core.logger import logger


class CostOptimizer:
    """成本优化器"""
    
    def __init__(self, redis_client: Optional[Any] = None):
        """
        初始化成本优化器
        
        Args:
            redis_client: Redis客户端（可选）
        """
        self.redis_client = redis_client
        
        # 简单查询规则库
        self.simple_query_patterns = self._build_simple_query_patterns()
        
        # 缓存配置
        self.cache_ttl = 3600  # 缓存过期时间（秒），默认1小时
        self.cache_prefix = "intent_route:"  # 缓存键前缀
        
        # 统计数据
        self.stats = {
            'cache_hits': 0,
            'cache_misses': 0,
            'simple_query_count': 0,
            'ernie_api_calls': 0,
            'cost_saved': 0.0  # 节省的成本（假设每次ERNIE调用成本0.01元）
        }
        
        logger.info("✅ 成本优化器初始化成功")
    
    def _build_simple_query_patterns(self) -> Dict[str, list]:
        """
        构建简单查询规则库
        
        Returns:
            简单查询模式字典
        """
        return {
            # IP地址查询（强制规则）
            'ip_address': [
                r'\b(?:\d{1,3}\.){3}\d{1,3}\b',  # IP地址正则
            ],
            
            # 实例ID查询（强制规则）
            'instance_id': [
                r'\b(i-[a-zA-Z0-9]+|instance-[a-zA-Z0-9]+|ins-[a-zA-Z0-9]+)\b',
            ],
            
            # 单表查询关键词
            'single_table': [
                '查询所有',
                '列出所有',
                '显示所有',
                '统计数量',
                '有多少',
            ],
            
            # 简单状态查询
            'simple_status': [
                '的状态',
                '是否在线',
                '是否运行',
                '是否正常',
            ],
        }
    
    def is_simple_query(self, query: str) -> Tuple[bool, str]:
        """
        判断是否为简单查询
        
        Args:
            query: 查询文本
        
        Returns:
            (是否简单查询, 匹配的规则类型)
        """
        import re
        
        # 检查IP地址
        for pattern in self.simple_query_patterns['ip_address']:
            if re.search(pattern, query):
                return True, 'ip_address'
        
        # 检查实例ID
        for pattern in self.simple_query_patterns['instance_id']:
            if re.search(pattern, query, re.IGNORECASE):
                return True, 'instance_id'
        
        # 检查单表查询
        for keyword in self.simple_query_patterns['single_table']:
            if keyword in query:
                return True, 'single_table'
        
        # 检查简单状态查询
        for keyword in self.simple_query_patterns['simple_status']:
            if keyword in query:
                return True, 'simple_status'
        
        return False, ''
    
    def generate_cache_key(self, query: str, user_id: Optional[str] = None) -> str:
        """
        生成缓存键
        
        Args:
            query: 查询文本
            user_id: 用户ID（可选）
        
        Returns:
            缓存键
        """
        # 使用查询文本的MD5作为缓存键
        query_hash = hashlib.md5(query.encode('utf-8')).hexdigest()
        
        # 如果有用户ID，加入缓存键（支持用户级缓存）
        if user_id:
            cache_key = f"{self.cache_prefix}{user_id}:{query_hash}"
        else:
            cache_key = f"{self.cache_prefix}global:{query_hash}"
        
        return cache_key
    
    async def get_cached_result(
        self,
        query: str,
        user_id: Optional[str] = None
    ) -> Optional[Dict]:
        """
        从缓存获取路由结果
        
        Args:
            query: 查询文本
            user_id: 用户ID
        
        Returns:
            缓存的路由结果，如果不存在返回None
        """
        if not self.redis_client:
            return None
        
        try:
            cache_key = self.generate_cache_key(query, user_id)
            
            # 从Redis获取缓存
            cached_data = await self.redis_client.get(cache_key)
            
            if cached_data:
                # 缓存命中
                self.stats['cache_hits'] += 1
                result = json.loads(cached_data)
                
                logger.info(f"✅ 缓存命中: {cache_key[:50]}...")
                
                return result
            else:
                # 缓存未命中
                self.stats['cache_misses'] += 1
                return None
                
        except Exception as e:
            logger.error(f"❌ 获取缓存失败: {e}")
            return None
    
    async def set_cached_result(
        self,
        query: str,
        result: Dict,
        user_id: Optional[str] = None,
        ttl: Optional[int] = None
    ):
        """
        设置缓存结果
        
        Args:
            query: 查询文本
            result: 路由结果
            user_id: 用户ID
            ttl: 缓存过期时间（秒），默认使用self.cache_ttl
        """
        if not self.redis_client:
            return
        
        try:
            cache_key = self.generate_cache_key(query, user_id)
            ttl = ttl or self.cache_ttl
            
            # 序列化结果
            cached_data = json.dumps(result, ensure_ascii=False)
            
            # 设置缓存
            await self.redis_client.setex(cache_key, ttl, cached_data)
            
            logger.debug(f"✅ 设置缓存: {cache_key[:50]}... (TTL: {ttl}s)")
            
        except Exception as e:
            logger.error(f"❌ 设置缓存失败: {e}")
    
    def record_simple_query(self):
        """记录简单查询（不调用ERNIE）"""
        self.stats['simple_query_count'] += 1
        # 假设每次ERNIE调用成本0.01元
        self.stats['cost_saved'] += 0.01
    
    def record_ernie_call(self):
        """记录ERNIE API调用"""
        self.stats['ernie_api_calls'] += 1
    
    def get_cache_hit_rate(self) -> float:
        """
        计算缓存命中率
        
        Returns:
            缓存命中率（0-1）
        """
        total_requests = self.stats['cache_hits'] + self.stats['cache_misses']
        
        if total_requests == 0:
            return 0.0
        
        return self.stats['cache_hits'] / total_requests
    
    def get_cost_savings(self) -> Dict[str, Any]:
        """
        获取成本节省统计
        
        Returns:
            成本节省统计字典
        """
        cache_hit_rate = self.get_cache_hit_rate()
        
        # 计算总节省成本
        # 缓存命中节省的成本 + 简单查询降级节省的成本
        cache_saved = self.stats['cache_hits'] * 0.01
        simple_query_saved = self.stats['simple_query_count'] * 0.01
        total_saved = cache_saved + simple_query_saved
        
        # 计算总请求数
        total_requests = (
            self.stats['cache_hits'] + 
            self.stats['cache_misses'] + 
            self.stats['simple_query_count']
        )
        
        # 计算节省比例（简单查询数 / 总请求数）
        # 简单查询不需要调用ERNIE，所以是节省的
        if total_requests > 0:
            savings_rate = self.stats['simple_query_count'] / total_requests
        else:
            savings_rate = 0.0
        
        return {
            'cache_hit_rate': cache_hit_rate,
            'cache_hits': self.stats['cache_hits'],
            'cache_misses': self.stats['cache_misses'],
            'simple_query_count': self.stats['simple_query_count'],
            'ernie_api_calls': self.stats['ernie_api_calls'],
            'total_requests': total_requests,
            'cache_saved_cost': cache_saved,
            'simple_query_saved_cost': simple_query_saved,
            'total_saved_cost': total_saved,
            'savings_rate': savings_rate,
            'estimated_cost': self.stats['ernie_api_calls'] * 0.01,
        }
    
    def reset_stats(self):
        """重置统计数据"""
        self.stats = {
            'cache_hits': 0,
            'cache_misses': 0,
            'simple_query_count': 0,
            'ernie_api_calls': 0,
            'cost_saved': 0.0
        }
        logger.info("✅ 成本统计数据已重置")
    
    async def clear_cache(self, pattern: Optional[str] = None):
        """
        清除缓存
        
        Args:
            pattern: 缓存键模式（可选），如果不指定则清除所有路由缓存
        """
        if not self.redis_client:
            return
        
        try:
            if pattern:
                # 清除匹配模式的缓存
                cache_pattern = f"{self.cache_prefix}{pattern}*"
            else:
                # 清除所有路由缓存
                cache_pattern = f"{self.cache_prefix}*"
            
            # 获取所有匹配的键
            keys = await self.redis_client.keys(cache_pattern)
            
            if keys:
                # 删除所有匹配的键
                await self.redis_client.delete(*keys)
                logger.info(f"✅ 清除缓存: {len(keys)} 个键")
            else:
                logger.info("ℹ️ 没有找到匹配的缓存键")
                
        except Exception as e:
            logger.error(f"❌ 清除缓存失败: {e}")
    
    def add_simple_query_pattern(self, pattern_type: str, pattern: str):
        """
        添加简单查询模式
        
        Args:
            pattern_type: 模式类型（ip_address/instance_id/single_table/simple_status）
            pattern: 模式内容（正则表达式或关键词）
        """
        if pattern_type not in self.simple_query_patterns:
            self.simple_query_patterns[pattern_type] = []
        
        self.simple_query_patterns[pattern_type].append(pattern)
        logger.info(f"✅ 添加简单查询模式: {pattern_type} -> {pattern}")


# 全局实例
_cost_optimizer = None


def get_cost_optimizer(redis_client: Optional[Any] = None) -> CostOptimizer:
    """获取成本优化器实例"""
    global _cost_optimizer
    
    if _cost_optimizer is None:
        _cost_optimizer = CostOptimizer(redis_client)
    
    return _cost_optimizer
