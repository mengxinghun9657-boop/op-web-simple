#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
匹配测试服务

实现需求：
- Requirements 4.2-4.6: 测试匹配功能
- Requirements 11.2-11.7: 批量测试功能
"""

import re
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class MatchTester:
    """匹配测试器"""
    
    def test_match(self, regex: str, test_queries: List[str]) -> Dict:
        """
        测试正则表达式匹配
        
        Args:
            regex: 正则表达式
            test_queries: 测试查询列表
            
        Returns:
            Dict: {
                "results": List[Dict],
                "match_rate": float,
                "total_count": int,
                "matched_count": int
            }
        """
        if not regex or not test_queries:
            return {
                "results": [],
                "match_rate": 0.0,
                "total_count": 0,
                "matched_count": 0
            }
        
        try:
            pattern = re.compile(regex)
        except re.error as e:
            raise ValueError(f"无效的正则表达式: {str(e)}")
        
        results = []
        matched_count = 0
        
        for query in test_queries:
            match = pattern.search(query)
            
            if match:
                matched_count += 1
                results.append({
                    "query": query,
                    "matched": True,
                    "confidence": 0.95,
                    "matched_text": match.group(),
                    "match_position": [match.start(), match.end()]
                })
            else:
                results.append({
                    "query": query,
                    "matched": False,
                    "confidence": 0.0
                })
        
        total_count = len(test_queries)
        match_rate = matched_count / total_count if total_count > 0 else 0.0
        
        return {
            "results": results,
            "match_rate": round(match_rate, 2),
            "total_count": total_count,
            "matched_count": matched_count
        }
