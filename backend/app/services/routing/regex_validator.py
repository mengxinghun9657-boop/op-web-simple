#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
正则表达式验证服务

实现需求：
- Requirements 3.1: 实时验证语法正确性
- Requirements 3.2: 显示具体的错误信息和位置
- Requirements 3.3: 显示复杂度评分
- Requirements 12.6: 复杂度评分算法
"""

import re
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class RegexValidator:
    """正则表达式验证器"""
    
    def validate(self, regex: str) -> Dict:
        """
        验证正则表达式
        
        Args:
            regex: 正则表达式
            
        Returns:
            Dict: {
                "is_valid": bool,
                "syntax_errors": List[Dict],
                "complexity_score": float
            }
        """
        if not regex or not regex.strip():
            return {
                "is_valid": False,
                "syntax_errors": [{
                    "message": "正则表达式不能为空",
                    "position": 0,
                    "suggestion": "请输入有效的正则表达式"
                }],
                "complexity_score": 0
            }
        
        # 验证语法
        syntax_errors = self._validate_syntax(regex)
        
        # 计算复杂度
        complexity_score = self._calculate_complexity(regex) if not syntax_errors else 0
        
        return {
            "is_valid": len(syntax_errors) == 0,
            "syntax_errors": syntax_errors,
            "complexity_score": complexity_score
        }
    
    def _validate_syntax(self, regex: str) -> List[Dict]:
        """验证正则表达式语法"""
        errors = []
        
        try:
            # 尝试编译正则表达式
            re.compile(regex)
            
        except re.error as e:
            # 解析错误信息
            error_msg = str(e)
            position = self._extract_position(error_msg)
            
            errors.append({
                "message": self._format_error_message(error_msg),
                "position": position,
                "suggestion": self._get_suggestion(error_msg, regex, position)
            })
        
        except Exception as e:
            errors.append({
                "message": f"未知错误: {str(e)}",
                "position": 0,
                "suggestion": "请检查正则表达式格式"
            })
        
        return errors
    
    def _extract_position(self, error_msg: str) -> int:
        """从错误信息中提取位置"""
        # 尝试提取 "at position X" 格式
        match = re.search(r'at position (\d+)', error_msg)
        if match:
            return int(match.group(1))
        return 0
    
    def _format_error_message(self, error_msg: str) -> str:
        """格式化错误信息"""
        # 常见错误的中文翻译
        translations = {
            "unbalanced parenthesis": "括号不匹配",
            "missing )": "缺少右括号",
            "missing ]": "缺少右方括号",
            "bad escape": "无效的转义字符",
            "nothing to repeat": "量词前没有可重复的内容",
            "multiple repeat": "重复的量词",
            "bad character range": "无效的字符范围",
            "unterminated character set": "字符集未闭合"
        }
        
        for eng, chn in translations.items():
            if eng in error_msg.lower():
                return chn
        
        return error_msg
    
    def _get_suggestion(self, error_msg: str, regex: str, position: int) -> str:
        """根据错误类型提供修复建议"""
        suggestions = {
            "括号不匹配": "请检查括号是否成对出现",
            "缺少右括号": "请在适当位置添加右括号 )",
            "缺少右方括号": "请在适当位置添加右方括号 ]",
            "无效的转义字符": "请使用有效的转义字符，如 \\d \\w \\s 等",
            "量词前没有可重复的内容": "量词（*、+、?、{n}）前必须有字符或分组",
            "重复的量词": "不能连续使用多个量词",
            "无效的字符范围": "字符范围格式应为 [a-z]，起始字符应小于结束字符",
            "字符集未闭合": "请使用 ] 闭合字符集"
        }
        
        formatted_msg = self._format_error_message(error_msg)
        return suggestions.get(formatted_msg, "请检查正则表达式语法")
    
    def _calculate_complexity(self, regex: str) -> float:
        """
        计算正则表达式复杂度评分（0-10）
        
        基于以下因素：
        1. 正则元素数量（字符类、量词、分组等）
        2. 嵌套深度
        3. 回溯风险
        """
        score = 0.0
        
        # 1. 基础长度（最多2分）
        length_score = min(len(regex) / 50, 2.0)
        score += length_score
        
        # 2. 特殊元素数量（最多3分）
        special_elements = [
            r'\d', r'\w', r'\s', r'\D', r'\W', r'\S',  # 字符类
            r'*', r'+', r'?', r'{', r'}',  # 量词
            r'|',  # 或
            r'(?:', r'(?=', r'(?!', r'(?<=', r'(?<!'  # 特殊分组
        ]
        element_count = sum(regex.count(elem) for elem in special_elements)
        element_score = min(element_count / 10, 3.0)
        score += element_score
        
        # 3. 嵌套深度（最多3分）
        nesting_depth = self._calculate_nesting_depth(regex)
        nesting_score = min(nesting_depth / 3, 3.0)
        score += nesting_score
        
        # 4. 回溯风险（最多2分）
        backtrack_risk = self._assess_backtrack_risk(regex)
        score += backtrack_risk
        
        return round(min(score, 10.0), 1)
    
    def _calculate_nesting_depth(self, regex: str) -> int:
        """计算嵌套深度"""
        max_depth = 0
        current_depth = 0
        
        i = 0
        while i < len(regex):
            if regex[i] == '(':
                current_depth += 1
                max_depth = max(max_depth, current_depth)
            elif regex[i] == ')':
                current_depth = max(0, current_depth - 1)
            elif regex[i] == '\\' and i + 1 < len(regex):
                i += 1  # 跳过转义字符
            i += 1
        
        return max_depth
    
    def _assess_backtrack_risk(self, regex: str) -> float:
        """评估回溯风险（0-2分）"""
        risk = 0.0
        
        # 嵌套量词（高风险）
        if re.search(r'(\*|\+|\?|\{\d+,\}).*(\*|\+|\?|\{\d+,\})', regex):
            risk += 1.0
        
        # 贪婪量词 + 复杂模式
        if re.search(r'\.(\*|\+)', regex):
            risk += 0.5
        
        # 多个或操作
        or_count = regex.count('|')
        if or_count > 2:
            risk += min(or_count / 10, 0.5)
        
        return min(risk, 2.0)
