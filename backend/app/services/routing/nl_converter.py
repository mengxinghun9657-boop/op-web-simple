#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
自然语言到正则表达式转换服务

实现需求：
- Requirements 2.1: 调用 ERNIE API 生成对应的正则表达式
- Requirements 2.2: 显示生成的正则表达式和匹配说明
- Requirements 2.3: 提供至少 3 个匹配示例
- Requirements 2.7: ERNIE API 在 5 秒内返回转换结果
"""

import re
import asyncio
import logging
from typing import Dict, List, Optional
from app.services.ai.ernie_client import get_ernie_client

logger = logging.getLogger(__name__)


class NLConverter:
    """自然语言到正则表达式转换器"""
    
    def __init__(self):
        self.ernie_client = get_ernie_client()
        self.max_retries = 3
        self.retry_delay = 1  # 秒
    
    async def convert(
        self,
        natural_language: str,
        intent_type: str
    ) -> Dict:
        """
        将自然语言描述转换为正则表达式
        
        Args:
            natural_language: 自然语言描述
            intent_type: 意图类型
            
        Returns:
            Dict: {
                "regex": str,
                "explanation": str,
                "examples": List[str],
                "confidence": float
            }
        """
        if not natural_language or not natural_language.strip():
            raise ValueError("自然语言描述不能为空")
        
        # 构建提示词
        prompt = self._build_prompt(natural_language, intent_type)
        
        # 调用 ERNIE API（带重试）
        for attempt in range(self.max_retries):
            try:
                response = await asyncio.wait_for(
                    self._call_ernie(prompt),
                    timeout=5.0  # 5秒超时
                )
                
                # 解析响应
                result = self._parse_response(response)
                
                # 验证结果
                if self._validate_result(result):
                    return result
                else:
                    logger.warning(f"转换结果验证失败，尝试 {attempt + 1}/{self.max_retries}")
                    
            except asyncio.TimeoutError:
                logger.error(f"ERNIE API 超时，尝试 {attempt + 1}/{self.max_retries}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))  # 指数退避
                    
            except Exception as e:
                logger.error(f"ERNIE API 调用失败: {str(e)}，尝试 {attempt + 1}/{self.max_retries}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))
        
        # 所有重试失败，返回降级结果
        return self._get_fallback_result(natural_language)
    
    def _build_prompt(self, natural_language: str, intent_type: str) -> str:
        """构建 ERNIE API 提示词"""
        return f"""你是一个正则表达式专家。请将以下自然语言描述转换为正则表达式。

自然语言描述：{natural_language}
意图类型：{intent_type}

请按照以下JSON格式返回结果：
{{
    "regex": "正则表达式",
    "explanation": "正则表达式的解释说明",
    "examples": ["匹配示例1", "匹配示例2", "匹配示例3"],
    "confidence": 0.95
}}

要求：
1. 正则表达式必须是有效的Python正则表达式
2. 提供至少3个匹配示例
3. 解释说明要清晰易懂
4. 置信度范围0-1
5. 只返回JSON，不要其他文字

示例：
输入："匹配包含IP地址的查询"
输出：
{{
    "regex": "\\\\b(?:\\\\d{{1,3}}\\\\.){3}\\\\d{{1,3}}\\\\b",
    "explanation": "匹配标准的IPv4地址格式",
    "examples": ["查询192.168.1.1的信息", "10.0.0.1的状态如何", "172.16.0.100有什么问题"],
    "confidence": 0.95
}}
"""
    
    async def _call_ernie(self, prompt: str) -> str:
        """调用 ERNIE API"""
        messages = [
            {"role": "user", "content": prompt}
        ]
        
        response = await self.ernie_client.chat(
            messages=messages,
            temperature=0.3,  # 降低随机性
            top_p=0.8
        )
        
        return response
    
    def _parse_response(self, response: str) -> Dict:
        """解析 ERNIE API 响应"""
        import json
        
        try:
            # 尝试提取JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return result
            else:
                raise ValueError("响应中未找到JSON格式")
                
        except Exception as e:
            logger.error(f"解析响应失败: {str(e)}")
            raise
    
    def _validate_result(self, result: Dict) -> bool:
        """验证转换结果"""
        # 检查必需字段
        required_fields = ["regex", "explanation", "examples", "confidence"]
        if not all(field in result for field in required_fields):
            return False
        
        # 验证正则表达式
        try:
            re.compile(result["regex"])
        except re.error:
            return False
        
        # 验证示例数量
        if not isinstance(result["examples"], list) or len(result["examples"]) < 3:
            return False
        
        # 验证置信度
        if not isinstance(result["confidence"], (int, float)) or not 0 <= result["confidence"] <= 1:
            return False
        
        return True
    
    def _get_fallback_result(self, natural_language: str) -> Dict:
        """获取降级结果（基本模式识别）"""
        # 简单的关键词匹配
        patterns = {
            "IP": {
                "regex": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
                "explanation": "匹配IPv4地址格式",
                "examples": ["查询192.168.1.1", "10.0.0.1的状态", "172.16.0.100信息"]
            },
            "实例": {
                "regex": r"\bi-[a-zA-Z0-9]+\b",
                "explanation": "匹配实例ID格式（i-xxx）",
                "examples": ["查询i-abc123", "实例i-xyz789状态", "i-test001信息"]
            },
            "主机": {
                "regex": r"主机名|hostname",
                "explanation": "匹配主机名相关查询",
                "examples": ["查询主机名", "hostname是什么", "主机名列表"]
            }
        }
        
        # 查找匹配的模式
        for keyword, pattern_info in patterns.items():
            if keyword in natural_language:
                return {
                    **pattern_info,
                    "confidence": 0.6  # 降级结果置信度较低
                }
        
        # 默认通用模式
        return {
            "regex": natural_language,
            "explanation": "使用原始文本作为匹配模式（关键词匹配）",
            "examples": [natural_language, f"包含{natural_language}", f"{natural_language}相关"],
            "confidence": 0.5
        }
