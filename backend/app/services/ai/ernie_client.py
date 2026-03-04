#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ERNIE API 客户端
封装百度文心一言 API 调用，支持重试机制、超时控制和错误处理
"""

import asyncio
import time
from typing import Dict, List, Optional, Any
import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

from app.core.config import settings
from app.core.logger import logger


class ERNIEClient:
    """
    ERNIE API 客户端
    
    功能：
    - 调用百度文心一言 API 进行自然语言理解和生成
    - 支持重试机制（最多 2 次）
    - 超时控制和错误处理
    - API 调用日志记录
    - 智能模型切换（额度用尽时自动切换到备用模型）
    
    使用示例：
    ```python
    client = ERNIEClient()
    response = await client.chat(
        messages=[
            {"role": "user", "content": "你好"}
        ]
    )
    print(response)
    ```
    """
    
    # 可用模型列表（按优先级排序）
    AVAILABLE_MODELS = [
        'ernie-4.5-turbo-32k',      # 优先使用：额度最大（1000万）
        'ernie-4.5-turbo-128k',     # 备用1：额度100万
        'ernie-4.5-turbo-128k-preview',  # 备用2：额度100万
        'ernie-x1-turbo-32k',       # 备用3：额度100万
        'ernie-x1-turbo-32k-preview',  # 备用4：额度100万
        'ernie-x1-32k-preview',     # 备用5：额度100万
        'ernie-4.5-21b-a3b',        # 备用6：额度100万
        'ernie-4.5-0.3b',           # 备用7：额度100万（轻量级）
        'deepseek-v3.2',            # 备用8：额度100万
        'deepseek-v3.2-think',      # 备用9：额度100万（思考模式）
        'qwen3-235b-a22b-thinking-2507',  # 备用10：额度100万（已使用部分）
        'ernie-4.5-8k-preview',     # 最后备用：额度50万（已使用大部分）
    ]
    
    def __init__(
        self,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: int = 60,
        max_retries: int = 2
    ):
        """
        初始化 ERNIE 客户端
        
        Args:
            api_url: API 地址，默认从配置读取
            api_key: API 密钥，默认从配置读取
            model: 模型名称，默认从配置读取
            timeout: 请求超时时间（秒），默认 60 秒
            max_retries: 最大重试次数，默认 2 次
        """
        self.api_url = api_url or getattr(settings, 'ERNIE_API_URL', 'http://llms-se.baidu-int.com:8200/chat/completions')
        self.api_key = api_key or getattr(settings, 'ERNIE_API_KEY', '')
        self.primary_model = model or getattr(settings, 'ERNIE_MODEL', 'ernie-4.5-turbo-32k')
        self.current_model = self.primary_model
        self.timeout = timeout
        self.max_retries = max_retries
        
        # 模型切换状态
        self.failed_models = set()  # 记录失败的模型
        self.model_switch_count = 0  # 模型切换次数
        
        # 请求频率限制（避免429错误）
        self.min_request_interval = 3.0  # 最小请求间隔（秒）
        self.last_request_time = 0.0  # 上次请求时间戳
        self._rate_limit_lock = asyncio.Lock()  # 频率限制锁
        
        # 创建 HTTP 客户端（禁用连接池复用，避免连接关闭错误）
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            limits=httpx.Limits(
                max_keepalive_connections=0,  # 禁用 keep-alive，每次请求使用新连接
                max_connections=10
            ),
            http2=False  # 禁用 HTTP/2，使用更稳定的 HTTP/1.1
        )
        
        logger.info(f"ERNIEClient initialized: url={self.api_url}, primary_model={self.primary_model}, timeout={timeout}s, max_retries={max_retries}")
        logger.info(f"Available fallback models: {len(self.AVAILABLE_MODELS)} models configured")
        logger.info(f"Rate limit: minimum {self.min_request_interval}s between requests")
    
    async def close(self):
        """关闭 HTTP 客户端"""
        await self.client.aclose()
        logger.info(f"ERNIEClient closed - switched models {self.model_switch_count} times")
    
    def _get_next_available_model(self) -> Optional[str]:
        """
        获取下一个可用模型
        
        Returns:
            Optional[str]: 下一个可用模型名称，如果没有可用模型则返回 None
        """
        for model in self.AVAILABLE_MODELS:
            if model not in self.failed_models:
                return model
        return None
    
    def _switch_model(self) -> bool:
        """
        切换到下一个可用模型
        
        Returns:
            bool: 是否成功切换
        """
        # 标记当前模型为失败
        self.failed_models.add(self.current_model)
        
        # 获取下一个可用模型
        next_model = self._get_next_available_model()
        
        if next_model:
            old_model = self.current_model
            self.current_model = next_model
            self.model_switch_count += 1
            logger.warning(f"🔄 Model switched: {old_model} -> {next_model} (switch count: {self.model_switch_count})")
            return True
        else:
            logger.error(f"❌ No available models left! All {len(self.AVAILABLE_MODELS)} models have failed.")
            return False
    
    def _is_quota_exceeded_error(self, error: Exception) -> bool:
        """
        判断是否是额度用尽错误
        
        Args:
            error: 异常对象
        
        Returns:
            bool: 是否是额度用尽错误
        """
        error_str = str(error).lower()
        quota_keywords = [
            'quota',
            'limit',
            'exceeded',
            'insufficient',
            '额度',
            '超限',
            '不足',
            'rate limit',
            'too many requests'
        ]
        return any(keyword in error_str for keyword in quota_keywords)
    
    @retry(
        stop=stop_after_attempt(3),  # 最多尝试 3 次（1 次原始 + 2 次重试）
        wait=wait_exponential(multiplier=1, min=1, max=10),  # 指数退避：1s, 2s, 4s
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError, RuntimeError)),  # 增加 RuntimeError 重试
        reraise=True
    )
    async def _make_request(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        top_p: float = 0.9,
        max_tokens: Optional[int] = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        发送 API 请求（带重试机制和模型切换）
        
        Args:
            messages: 对话消息列表
            temperature: 温度参数（0-1），控制随机性
            top_p: Top-p 采样参数
            max_tokens: 最大生成 token 数
            stream: 是否使用流式响应
        
        Returns:
            Dict: API 响应
        
        Raises:
            httpx.TimeoutException: 请求超时
            httpx.NetworkError: 网络错误
            httpx.HTTPStatusError: HTTP 错误
        """
        # 频率限制：确保请求间隔至少为 min_request_interval 秒
        async with self._rate_limit_lock:
            current_time = time.time()
            time_since_last_request = current_time - self.last_request_time
            
            if time_since_last_request < self.min_request_interval:
                wait_time = self.min_request_interval - time_since_last_request
                logger.info(f"⏱️ Rate limit: waiting {wait_time:.2f}s before next request")
                await asyncio.sleep(wait_time)
            
            self.last_request_time = time.time()
        
        # 构建请求体
        request_body = {
            "model": self.current_model,
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
            "stream": stream
        }
        
        if max_tokens:
            request_body["max_tokens"] = max_tokens
        
        # 构建请求头
        headers = {
            "Content-Type": "application/json"
        }
        
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        # 记录请求日志
        logger.info(f"ERNIE API request: model={self.current_model}, messages_count={len(messages)}, temperature={temperature}")
        
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
            
            # 计算耗时
            elapsed_time = (time.time() - start_time) * 1000
            
            # 记录成功日志
            logger.info(f"ERNIE API response: status=success, model={self.current_model}, elapsed_time={elapsed_time:.2f}ms")
            
            return result
        
        except httpx.TimeoutException as e:
            elapsed_time = (time.time() - start_time) * 1000
            logger.warning(f"ERNIE API timeout: model={self.current_model}, elapsed_time={elapsed_time:.2f}ms, error={str(e)}")
            raise
        
        except httpx.NetworkError as e:
            elapsed_time = (time.time() - start_time) * 1000
            logger.warning(f"ERNIE API network error: model={self.current_model}, elapsed_time={elapsed_time:.2f}ms, error={str(e)}")
            raise
        
        except httpx.HTTPStatusError as e:
            elapsed_time = (time.time() - start_time) * 1000
            error_detail = ""
            try:
                error_detail = e.response.json()
            except:
                error_detail = e.response.text
            
            logger.error(f"ERNIE API HTTP error: model={self.current_model}, status={e.response.status_code}, elapsed_time={elapsed_time:.2f}ms, error={error_detail}")
            
            # 检查是否是额度用尽错误
            if self._is_quota_exceeded_error(e) or e.response.status_code == 429:
                logger.warning(f"⚠️ Model {self.current_model} quota exceeded or rate limited, attempting to switch model...")
                
                # 尝试切换模型
                if self._switch_model():
                    logger.info(f"🔄 Retrying with new model: {self.current_model}")
                    # 递归调用，使用新模型重试
                    return await self._make_request(messages, temperature, top_p, max_tokens, stream)
                else:
                    logger.error("❌ All models exhausted, cannot continue")
                    raise Exception("All available models have exceeded their quota or failed")
            
            raise
        
        except Exception as e:
            elapsed_time = (time.time() - start_time) * 1000
            
            # 特殊处理 RuntimeError（TCP 连接关闭错误）
            if isinstance(e, RuntimeError) and "TCPTransport closed" in str(e):
                logger.warning(f"ERNIE API connection closed: model={self.current_model}, elapsed_time={elapsed_time:.2f}ms, will retry with new connection")
                # 关闭并重新创建客户端
                await self.client.aclose()
                self.client = httpx.AsyncClient(
                    timeout=httpx.Timeout(self.timeout),
                    limits=httpx.Limits(
                        max_keepalive_connections=0,
                        max_connections=10
                    ),
                    http2=False
                )
                raise  # 让 tenacity 重试
            
            logger.error(f"ERNIE API unexpected error: model={self.current_model}, elapsed_time={elapsed_time:.2f}ms, error={str(e)}")
            
            # 检查是否是额度相关错误
            if self._is_quota_exceeded_error(e):
                logger.warning(f"⚠️ Model {self.current_model} quota exceeded, attempting to switch model...")
                
                # 尝试切换模型
                if self._switch_model():
                    logger.info(f"🔄 Retrying with new model: {self.current_model}")
                    # 递归调用，使用新模型重试
                    return await self._make_request(messages, temperature, top_p, max_tokens, stream)
                else:
                    logger.error("❌ All models exhausted, cannot continue")
                    raise Exception("All available models have exceeded their quota or failed")
            
            raise
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        top_p: float = 0.9,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        调用 ERNIE API 进行对话
        
        Args:
            messages: 对话消息列表，格式：[{"role": "user", "content": "..."}]
            temperature: 温度参数（0-1），控制随机性，默认 0.7
            top_p: Top-p 采样参数，默认 0.9
            max_tokens: 最大生成 token 数，默认 None（使用模型默认值）
        
        Returns:
            str: 生成的回答文本
        
        Raises:
            ValueError: 参数验证失败
            Exception: API 调用失败
        """
        # 验证参数
        if not messages:
            raise ValueError("messages cannot be empty")
        
        if not all(isinstance(m, dict) and "role" in m and "content" in m for m in messages):
            raise ValueError("messages must be a list of dicts with 'role' and 'content' keys")
        
        if not 0 <= temperature <= 1:
            raise ValueError("temperature must be between 0 and 1")
        
        if not 0 <= top_p <= 1:
            raise ValueError("top_p must be between 0 and 1")
        
        try:
            # 发送请求
            response = await self._make_request(
                messages=messages,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                stream=False
            )
            
            # 提取回答文本
            if "choices" in response and len(response["choices"]) > 0:
                content = response["choices"][0].get("message", {}).get("content", "")
                return content
            else:
                logger.error(f"Unexpected ERNIE API response format: {response}")
                raise ValueError("Unexpected API response format")
        
        except Exception as e:
            logger.error(f"ERNIE chat failed: {str(e)}")
            raise
    
    async def chat_with_system_prompt(
        self,
        user_message: str,
        system_prompt: str,
        temperature: float = 0.7,
        top_p: float = 0.9,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        使用系统提示词进行对话
        
        Args:
            user_message: 用户消息
            system_prompt: 系统提示词
            temperature: 温度参数
            top_p: Top-p 采样参数
            max_tokens: 最大生成 token 数
        
        Returns:
            str: 生成的回答文本
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        return await self.chat(
            messages=messages,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens
        )
    
    async def generate_sql(
        self,
        query: str,
        schema_context: str
    ) -> str:
        """
        生成 SQL 语句
        
        Args:
            query: 用户的自然语言查询
            schema_context: 数据库 Schema 上下文
        
        Returns:
            str: 生成的 SQL 语句
        """
        system_prompt = """你是一个 SQL 专家。请根据用户的自然语言查询生成 MySQL SELECT 语句。

要求：
1. 仅生成 SELECT 语句
2. 仅使用提供的表和字段
3. 明细查询不需要添加 LIMIT（系统会自动添加）
4. 聚合查询（COUNT/SUM/AVG/MAX/MIN/GROUP BY）不添加 LIMIT
5. 返回纯 SQL，不要包含解释文本

数据库 Schema（仅相关表）：
{schema_context}

用户查询：{query}

SQL:"""
        
        prompt = system_prompt.format(
            schema_context=schema_context,
            query=query
        )
        
        response = await self.chat_with_system_prompt(
            user_message=query,
            system_prompt=prompt,
            temperature=0.3,  # 降低温度以提高准确性
            max_tokens=500
        )
        
        # 提取 SQL（去除可能的 markdown 代码块标记）
        sql = response.strip()
        if sql.startswith("```sql"):
            sql = sql[6:]
        if sql.startswith("```"):
            sql = sql[3:]
        if sql.endswith("```"):
            sql = sql[:-3]
        
        return sql.strip()
    
    async def classify_intent(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        分类查询意图
        
        Args:
            query: 用户查询
            context: 对话上下文（可选）
        
        Returns:
            Dict: 意图分类结果，包含 intent_type, confidence, reasoning
        """
        system_prompt = """你是一个意图分类专家。请分析用户的查询意图，返回 JSON 格式结果。

可能的意图类型：
- sql: 查询实时数据库数据（如"查询物理机信息"、"有多少台虚机"）
- rag_report: 检索历史分析报告（如"最近的资源分析"、"上周的监控报告"）
- rag_knowledge: 检索知识库内容（如"如何处理MySQL延迟"、"故障处理流程"）
- chat: 普通对话（如"你好"、"谢谢"）
- mixed: 混合查询（如"物理机cdhmlcc001的当前状态和历史报告"）

请返回 JSON 格式：
{
  "intent_type": "sql" | "rag_report" | "rag_knowledge" | "chat" | "mixed",
  "confidence": 0.0-1.0,
  "processors": ["sql", "rag_report"],  // 仅 mixed 类型需要
  "reasoning": "分类理由"
}"""
        
        user_message = f"用户查询：{query}"
        if context:
            user_message += f"\n\n对话上下文：{context}"
        
        response = await self.chat_with_system_prompt(
            user_message=user_message,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=300
        )
        
        # 解析 JSON 响应
        import json
        try:
            result = json.loads(response)
            return result
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse intent classification response: {response}, error: {e}")
            # 返回默认值
            return {
                "intent_type": "chat",
                "confidence": 0.0,
                "reasoning": "Failed to parse response"
            }
    
    async def generate_answer(
        self,
        query: str,
        context: str,
        source_type: str
    ) -> str:
        """
        生成自然语言回答
        
        Args:
            query: 用户查询
            context: 上下文信息（查询结果、报告内容等）
            source_type: 数据来源类型（database/report/knowledge/mixed）
        
        Returns:
            str: 自然语言回答
        """
        system_prompt = f"""你是一个智能助手。请根据提供的信息回答用户的问题。

数据来源：{source_type}

上下文信息：
{context}

要求：
1. 使用自然、友好的语言
2. 准确传达信息，不要编造内容
3. 如果信息不足，明确说明
4. 对于报告内容，标注生成时间以提醒用户数据时效性
5. 对于混合查询，明确区分实时数据和历史报告来源

用户问题：{query}

回答："""
        
        response = await self.chat_with_system_prompt(
            user_message=query,
            system_prompt=system_prompt,
            temperature=0.7,
            max_tokens=1000
        )
        
        return response
    
    def __del__(self):
        """析构函数，确保客户端关闭"""
        try:
            # 注意：在异步环境中，析构函数可能无法正确关闭异步客户端
            # 建议显式调用 close() 方法
            pass
        except Exception:
            pass


# 创建全局实例（单例模式）
_ernie_client_instance: Optional[ERNIEClient] = None


def get_ernie_client() -> ERNIEClient:
    """
    获取 ERNIE 客户端实例（单例模式）
    
    Returns:
        ERNIEClient: ERNIE 客户端实例
    """
    global _ernie_client_instance
    
    if _ernie_client_instance is None:
        # 从配置读取超时时间
        timeout = getattr(settings, 'ERNIE_TIMEOUT', 60)
        _ernie_client_instance = ERNIEClient(timeout=timeout)
    
    return _ernie_client_instance


async def close_ernie_client():
    """关闭全局 ERNIE 客户端实例"""
    global _ernie_client_instance
    
    if _ernie_client_instance is not None:
        await _ernie_client_instance.close()
        _ernie_client_instance = None
