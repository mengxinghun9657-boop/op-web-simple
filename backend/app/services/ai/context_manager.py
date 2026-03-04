#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对话上下文管理器（Context Manager）

功能：
- 维护多轮对话历史（最近 5 轮）
- 代词引用检测和解析
- 实体提取和追踪
- 会话超时管理（30 分钟）

Requirements: 27.1, 27.2, 27.3, 27.4, 27.5, 27.6, 27.8
"""
import json
import time
import re
from typing import List, Dict, Optional, Any
from app.core.redis_client import get_redis_client
from app.core.logger import logger


class ConversationContext:
    """对话上下文数据模型"""
    
    def __init__(self, session_id: str, user_id: str, history: List[Dict] = None):
        self.session_id = session_id
        self.user_id = user_id
        self.history = history or []
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "history": self.history
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ConversationContext':
        """从字典创建"""
        return cls(
            session_id=data.get("session_id", ""),
            user_id=data.get("user_id", ""),
            history=data.get("history", [])
        )


class ContextManager:
    """
    对话上下文管理器
    
    职责：
    - 维护对话历史（最近 5 轮）
    - 代词引用解析
    - 实体追踪
    - 会话超时管理
    """
    
    def __init__(self):
        """初始化上下文管理器"""
        self.redis_client = get_redis_client()
        self.session_ttl = 1800  # 30 分钟（秒）
        self.max_history_turns = 5  # 最多保留 5 轮对话
        
        # 代词列表
        self.pronouns = ["它们", "这些", "上面的", "那些", "它", "这个", "那个"]
        
        logger.info("✅ ContextManager 初始化成功")
    
    def get_context(self, session_id: str) -> ConversationContext:
        """
        获取对话上下文
        
        Args:
            session_id: 会话ID
            
        Returns:
            ConversationContext: 对话上下文对象
            
        Requirements: 27.1
        """
        try:
            # 从 Redis 获取对话历史
            key = f"context:{session_id}"
            context_data = self.redis_client.get_cache(key)
            
            if not context_data:
                logger.debug(f"会话 {session_id} 无历史记录，创建新上下文")
                return ConversationContext(session_id=session_id, user_id="")
            
            context = ConversationContext.from_dict(context_data)
            logger.debug(f"获取会话上下文: {session_id}, 历史轮数: {len(context.history)}")
            return context
            
        except Exception as e:
            logger.error(f"获取对话上下文失败: {e}")
            return ConversationContext(session_id=session_id, user_id="")
    
    def update_context(
        self,
        session_id: str,
        user_id: str,
        query: str,
        response: Dict[str, Any]
    ) -> None:
        """
        更新对话上下文
        
        Args:
            session_id: 会话ID
            user_id: 用户ID
            query: 用户查询
            response: 系统响应
            
        Requirements: 27.1, 27.4, 27.6
        """
        try:
            # 获取当前上下文
            context = self.get_context(session_id)
            context.user_id = user_id
            
            # 提取实体（如果是 SQL 查询）
            entities = []
            if response.get("source_type") == "database":
                entities = self._extract_entities_from_results(
                    response.get("query_results", [])
                )
            
            # 添加新的对话轮次
            turn = {
                "query": query,
                "response": response,
                "entities": entities,
                "timestamp": time.time()
            }
            context.history.append(turn)
            
            # 保留最近 5 轮
            if len(context.history) > self.max_history_turns:
                context.history = context.history[-self.max_history_turns:]
                logger.debug(f"对话历史超过 {self.max_history_turns} 轮，保留最近的")
            
            # 保存到 Redis
            key = f"context:{session_id}"
            self.redis_client.set_cache(key, context.to_dict(), expire=self.session_ttl)
            
            logger.info(f"✅ 更新会话上下文: {session_id}, 当前轮数: {len(context.history)}")
            
        except Exception as e:
            logger.error(f"更新对话上下文失败: {e}")
    
    def resolve_pronouns(self, query: str, context: ConversationContext) -> str:
        """
        解析代词引用
        
        Args:
            query: 用户查询
            context: 对话上下文
            
        Returns:
            str: 解析后的查询（代词替换为实体）
            
        Requirements: 27.2, 27.3, 27.5
        """
        try:
            # 检测代词引用
            has_pronoun = any(pronoun in query for pronoun in self.pronouns)
            
            if not has_pronoun:
                logger.debug("查询中未检测到代词引用")
                return query
            
            if not context.history:
                logger.warning("检测到代词但无对话历史，无法解析")
                return query
            
            # 获取上一轮的实体
            last_turn = context.history[-1]
            entities = last_turn.get("entities", [])
            
            if not entities:
                logger.warning("上一轮查询无实体，无法解析代词")
                return query
            
            # 替换代词为实体列表
            entity_str = "、".join(entities)
            resolved_query = query
            
            for pronoun in self.pronouns:
                if pronoun in resolved_query:
                    resolved_query = resolved_query.replace(pronoun, entity_str)
                    logger.info(f"✅ 代词 '{pronoun}' 替换为实体: {entity_str}")
            
            return resolved_query
            
        except Exception as e:
            logger.error(f"解析代词引用失败: {e}")
            return query
    
    def clear_context(self, session_id: str) -> None:
        """
        清空对话上下文
        
        Args:
            session_id: 会话ID
            
        Requirements: 27.7
        """
        try:
            key = f"context:{session_id}"
            self.redis_client.delete_cache(key)
            logger.info(f"✅ 清空会话上下文: {session_id}")
        except Exception as e:
            logger.error(f"清空对话上下文失败: {e}")
    
    def detect_new_topic(self, query: str) -> bool:
        """
        检测是否开始新话题
        
        Args:
            query: 用户查询
            
        Returns:
            bool: 是否为新话题
            
        Requirements: 27.7
        """
        # 检测新话题关键词
        new_topic_keywords = [
            "换个问题", "新问题", "另一个问题", "问别的",
            "不问这个了", "换个话题", "重新开始"
        ]
        
        for keyword in new_topic_keywords:
            if keyword in query:
                logger.info(f"检测到新话题关键词: {keyword}")
                return True
        
        return False
    
    def _extract_entities_from_results(self, results: List[Dict]) -> List[str]:
        """
        从查询结果中提取实体
        
        Args:
            results: 查询结果列表
            
        Returns:
            List[str]: 实体列表（最多 10 个）
            
        Requirements: 27.4
        """
        entities = []
        
        try:
            for row in results:
                if not row:
                    continue
                
                # 提取第一列作为主要实体
                # 假设第一列通常是主键或名称字段
                first_value = None
                
                if isinstance(row, dict):
                    # 如果是字典，取第一个值
                    first_value = next(iter(row.values()), None)
                elif isinstance(row, (list, tuple)):
                    # 如果是列表或元组，取第一个元素
                    first_value = row[0] if len(row) > 0 else None
                
                if first_value is not None:
                    entity_str = str(first_value)
                    # 过滤掉空字符串和None
                    if entity_str and entity_str.lower() != 'none':
                        entities.append(entity_str)
            
            # 最多保留 10 个实体
            entities = entities[:10]
            
            if entities:
                logger.debug(f"提取到 {len(entities)} 个实体: {entities[:3]}...")
            
            return entities
            
        except Exception as e:
            logger.error(f"提取实体失败: {e}")
            return []
    
    def get_context_summary(self, session_id: str) -> Dict[str, Any]:
        """
        获取对话上下文摘要（用于调试和监控）
        
        Args:
            session_id: 会话ID
            
        Returns:
            Dict: 上下文摘要信息
        """
        try:
            context = self.get_context(session_id)
            
            return {
                "session_id": session_id,
                "user_id": context.user_id,
                "history_turns": len(context.history),
                "last_query": context.history[-1]["query"] if context.history else None,
                "last_entities": context.history[-1].get("entities", []) if context.history else [],
                "last_timestamp": context.history[-1].get("timestamp") if context.history else None
            }
            
        except Exception as e:
            logger.error(f"获取上下文摘要失败: {e}")
            return {
                "session_id": session_id,
                "error": str(e)
            }


# 全局单例
_context_manager: Optional[ContextManager] = None


def get_context_manager() -> ContextManager:
    """获取 ContextManager 单例"""
    global _context_manager
    if _context_manager is None:
        _context_manager = ContextManager()
    return _context_manager
