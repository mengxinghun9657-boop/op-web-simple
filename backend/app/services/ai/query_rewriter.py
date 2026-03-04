#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
查询改写器（Query Rewriter）

基于字节跳动RAG最佳实践 5.1.2节 - 查询理解增强

功能：
1. 查询分解 - 将复杂查询拆分为多个子查询
2. 查询补全 - 补充缺失的查询条件
3. 查询简化 - 去除冗余信息,提取核心意图
"""

import re
from typing import List, Dict, Optional, Tuple, Any
from app.core.logger import logger


class QueryRewriter:
    """查询改写器"""
    
    def __init__(self):
        """初始化查询改写器"""
        
        # 查询分解规则
        self.decomposition_rules = self._build_decomposition_rules()
        
        # 查询补全模板
        self.completion_templates = self._build_completion_templates()
        
        # 冗余词列表
        self.redundant_words = self._build_redundant_words()
        
        logger.info("✅ 查询改写器初始化成功")
    
    def _build_decomposition_rules(self) -> Dict[str, list]:
        """
        构建查询分解规则
        
        Returns:
            分解规则字典
        """
        return {
            # 标点符号分隔
            'punctuation': [
                r'[,，]',  # 逗号
                r'[;；]',  # 分号
                r'[、]',   # 顿号
            ],
            
            # 连接词分隔
            'conjunctions': [
                '以及',
                '还有',
                '另外',
                '同时',
                '并且',
                '而且',
            ],
            
            # 疑问词分隔
            'questions': [
                '需要哪些',
                '如何',
                '怎么',
                '什么',
                '多少',
                '多久',
            ],
        }
    
    def _build_completion_templates(self) -> Dict[str, list]:
        """
        构建查询补全模板
        
        Returns:
            补全模板字典
        """
        return {
            # 集群相关查询
            'cluster': [
                '{query}的详细信息',
                '{query}的配置',
                '{query}的状态',
            ],
            
            # 实例相关查询
            'instance': [
                '{query}的详细信息',
                '{query}属于哪个集群',
                '{query}的配置参数',
            ],
            
            # 统计相关查询
            'statistics': [
                '统计{query}',
                '{query}的数量',
                '{query}的总数',
            ],
        }
    
    def _build_redundant_words(self) -> List[str]:
        """
        构建冗余词列表
        
        Returns:
            冗余词列表
        """
        return [
            '请问',
            '我想问',
            '我想知道',
            '能否告诉我',
            '可以告诉我',
            '帮我查一下',
            '帮我看一下',
            '麻烦',
            '谢谢',
        ]
    
    def decompose_query(self, query: str) -> List[str]:
        """
        查询分解 - 将复杂查询拆分为多个子查询
        
        Args:
            query: 原始查询
        
        Returns:
            子查询列表
        """
        # 如果查询很短,不需要分解
        if len(query) < 10:
            return [query]
        
        sub_queries = []
        
        # 1. 尝试使用标点符号分解
        for pattern in self.decomposition_rules['punctuation']:
            parts = re.split(pattern, query)
            if len(parts) > 1:
                # 过滤空字符串和过短的片段
                sub_queries = [p.strip() for p in parts if p.strip() and len(p.strip()) > 3]
                if len(sub_queries) > 1:
                    logger.info(f"✅ 标点符号分解: {query} -> {sub_queries}")
                    return sub_queries
        
        # 2. 尝试使用连接词分解
        for conjunction in self.decomposition_rules['conjunctions']:
            if conjunction in query:
                parts = query.split(conjunction)
                sub_queries = [p.strip() for p in parts if p.strip() and len(p.strip()) > 3]
                if len(sub_queries) > 1:
                    logger.info(f"✅ 连接词分解: {query} -> {sub_queries}")
                    return sub_queries
        
        # 3. 尝试使用疑问词分解
        question_positions = []
        for question in self.decomposition_rules['questions']:
            pos = query.find(question)
            if pos > 0:  # 不在开头
                question_positions.append((pos, question))
        
        if question_positions:
            # 按位置排序
            question_positions.sort(key=lambda x: x[0])
            
            # 在疑问词位置分割
            sub_queries = []
            start = 0
            for pos, question in question_positions:
                if start < pos:
                    sub_queries.append(query[start:pos].strip())
                start = pos
            
            # 添加最后一部分
            if start < len(query):
                sub_queries.append(query[start:].strip())
            
            # 过滤空字符串和过短的片段
            sub_queries = [q for q in sub_queries if q and len(q) > 3]
            
            if len(sub_queries) > 1:
                logger.info(f"✅ 疑问词分解: {query} -> {sub_queries}")
                return sub_queries
        
        # 如果无法分解,返回原查询
        return [query]
    
    def complete_query(self, query: str) -> List[str]:
        """
        查询补全 - 补充缺失的查询条件
        
        Args:
            query: 原始查询
        
        Returns:
            补全后的查询列表(包含原查询)
        """
        # 如果查询已经很长,不需要补全
        if len(query) > 15:
            return [query]
        
        completed_queries = [query]  # 始终包含原查询
        
        # 判断查询类型并补全
        if '集群' in query:
            for template in self.completion_templates['cluster']:
                completed_queries.append(template.format(query=query))
        
        elif '实例' in query or 'i-' in query or 'instance-' in query:
            for template in self.completion_templates['instance']:
                completed_queries.append(template.format(query=query))
        
        elif '统计' in query or '数量' in query or '总数' in query:
            for template in self.completion_templates['statistics']:
                completed_queries.append(template.format(query=query))
        
        if len(completed_queries) > 1:
            logger.info(f"✅ 查询补全: {query} -> {completed_queries}")
        
        return completed_queries
    
    def simplify_query(self, query: str) -> str:
        """
        查询简化 - 去除冗余信息,提取核心意图
        
        Args:
            query: 原始查询
        
        Returns:
            简化后的查询
        """
        simplified = query
        
        # 1. 去除冗余词
        for word in self.redundant_words:
            simplified = simplified.replace(word, '')
        
        # 2. 去除多余空格
        simplified = re.sub(r'\s+', ' ', simplified).strip()
        
        # 3. 去除开头和结尾的标点符号
        simplified = simplified.strip(',.，。?？!！')
        
        if simplified != query:
            logger.info(f"✅ 查询简化: {query} -> {simplified}")
        
        return simplified if simplified else query
    
    def rewrite(
        self,
        query: str,
        enable_decomposition: bool = True,
        enable_completion: bool = True,
        enable_simplification: bool = True
    ) -> Dict[str, any]:
        """
        综合查询改写
        
        Args:
            query: 原始查询
            enable_decomposition: 是否启用查询分解
            enable_completion: 是否启用查询补全
            enable_simplification: 是否启用查询简化
        
        Returns:
            改写结果字典
        """
        result = {
            'original_query': query,
            'simplified_query': query,
            'sub_queries': [],
            'completed_queries': [],
            'is_complex': False,
            'rewrite_applied': False,
        }
        
        # 1. 查询简化
        if enable_simplification:
            simplified = self.simplify_query(query)
            result['simplified_query'] = simplified
            if simplified != query:
                result['rewrite_applied'] = True
        else:
            simplified = query
        
        # 2. 查询分解
        if enable_decomposition:
            sub_queries = self.decompose_query(simplified)
            result['sub_queries'] = sub_queries
            if len(sub_queries) > 1:
                result['is_complex'] = True
                result['rewrite_applied'] = True
        else:
            sub_queries = [simplified]
        
        # 3. 查询补全(仅对简化后的查询或子查询)
        if enable_completion:
            if result['is_complex']:
                # 对每个子查询进行补全
                for sub_query in sub_queries:
                    completed = self.complete_query(sub_query)
                    result['completed_queries'].extend(completed)
            else:
                # 对简化后的查询进行补全
                completed = self.complete_query(simplified)
                result['completed_queries'] = completed
                if len(completed) > 1:
                    result['rewrite_applied'] = True
        
        return result


    def get_statistics(self) -> Dict[str, Any]:
        """
        获取查询改写统计数据

        Returns:
            统计数据字典

        参考: 字节跳动RAG 8.1节和13.3节 - 性能监控
        """
        return {
            'decomposition_rules': {
                'punctuation': len(self.decomposition_rules['punctuation']),
                'conjunctions': len(self.decomposition_rules['conjunctions']),
                'questions': len(self.decomposition_rules['questions'])
            },
            'completion_templates': {
                'cluster': len(self.completion_templates['cluster']),
                'instance': len(self.completion_templates['instance']),
                'statistics': len(self.completion_templates['statistics'])
            },
            'redundant_words_count': len(self.redundant_words)
        }



# 全局实例
_query_rewriter = None


def get_query_rewriter() -> QueryRewriter:
    """获取查询改写器实例"""
    global _query_rewriter
    
    if _query_rewriter is None:
        _query_rewriter = QueryRewriter()
    
    return _query_rewriter
