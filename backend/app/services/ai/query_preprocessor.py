#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
查询预处理器（Query Preprocessor）

基于字节跳动RAG最佳实践 5.1.2节 - 查询理解增强

功能：
1. 同义词替换和查询扩展
2. 拼写纠错
3. 实体识别（IP、实例ID、集群名、时间范围）
4. 查询扩展（短查询自动生成扩展）
"""

import re
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta

from app.core.logger import logger


class QueryPreprocessor:
    """查询预处理器"""
    
    def __init__(self):
        """初始化查询预处理器"""
        # 同义词词典（业务术语映射）
        self.synonyms = self._build_synonym_dict()
        
        # 拼写纠错词典（常见错误映射）
        self.spelling_corrections = self._build_spelling_dict()
        
        # 实体识别正则表达式
        self._compile_entity_patterns()
        
        logger.info("✅ 查询预处理器初始化成功")
    
    def _build_synonym_dict(self) -> Dict[str, List[str]]:
        """
        构建同义词词典
        
        Returns:
            同义词映射表 {标准词: [同义词列表]}
        """
        return {
            # 物理机相关
            "物理机": ["服务器", "主机", "机器", "节点", "宿主机", "host"],
            "服务器": ["物理机", "主机", "机器", "节点"],
            
            # 虚拟机相关
            "虚拟机": ["实例", "虚机", "VM", "instance"],
            "实例": ["虚拟机", "虚机", "VM", "instance"],
            
            # 集群相关
            "集群": ["cluster", "集群环境", "环境"],
            
            # 资源相关
            "CPU": ["处理器", "核心", "cpu"],
            "内存": ["memory", "mem", "RAM"],
            "磁盘": ["disk", "存储", "硬盘"],
            "网络": ["network", "带宽", "流量"],
            
            # 状态相关
            "运行中": ["running", "正常", "在线", "活跃"],
            "停止": ["stopped", "关闭", "下线"],
            "异常": ["error", "错误", "故障", "问题"],
            
            # 操作相关
            "查询": ["查看", "获取", "显示", "列出", "检索"],
            "统计": ["汇总", "合计", "计算", "分析"],
            
            # 时间相关
            "今天": ["今日", "当天"],
            "昨天": ["昨日", "前一天"],
            "最近": ["近期", "最新"],
        }
    
    def _build_spelling_dict(self) -> Dict[str, str]:
        """
        构建拼写纠错词典
        
        Returns:
            拼写纠错映射表 {错误拼写: 正确拼写}
        """
        return {
            # 常见拼写错误
            "物理鸡": "物理机",
            "服务气": "服务器",
            "集群": "集群",  # 保持不变
            "实利": "实例",
            "查寻": "查询",
            "统记": "统计",
            
            # 英文拼写错误
            "sever": "server",
            "instanse": "instance",
            "cluser": "cluster",
            "memery": "memory",
            
            # 拼音输入错误
            "wuliji": "物理机",
            "fuwuqi": "服务器",
            "jiqun": "集群",
        }
    
    def _compile_entity_patterns(self):
        """编译实体识别正则表达式"""
        # IP地址模式
        self.ip_pattern = re.compile(
            r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
        )
        
        # 实例ID模式
        self.instance_id_pattern = re.compile(
            r'\b(i-[a-zA-Z0-9]+|instance-[a-zA-Z0-9]+|ins-[a-zA-Z0-9]+)\b',
            re.IGNORECASE
        )
        
        # 集群名称模式（假设格式：cluster-xxx 或 xxx-cluster）
        self.cluster_name_pattern = re.compile(
            r'\b(cluster-[a-zA-Z0-9-]+|[a-zA-Z0-9-]+-cluster)\b',
            re.IGNORECASE
        )
        
        # 时间范围模式
        self.time_range_patterns = {
            'today': re.compile(r'今天|今日|当天', re.IGNORECASE),
            'yesterday': re.compile(r'昨天|昨日|前一天', re.IGNORECASE),
            'last_week': re.compile(r'上周|上星期|最近一周|最近7天', re.IGNORECASE),
            'last_month': re.compile(r'上月|上个月|最近一个月|最近30天', re.IGNORECASE),
            'recent': re.compile(r'最近|近期|最新', re.IGNORECASE),
        }
    
    async def preprocess(
        self,
        query: str,
        enable_synonym: bool = True,
        enable_spelling: bool = True,
        enable_entity: bool = True,
        enable_expansion: bool = True
    ) -> Dict:
        """
        预处理查询
        
        Args:
            query: 原始查询文本
            enable_synonym: 是否启用同义词替换
            enable_spelling: 是否启用拼写纠错
            enable_entity: 是否启用实体识别
            enable_expansion: 是否启用查询扩展
        
        Returns:
            预处理结果字典：
            {
                'original_query': str,  # 原始查询
                'processed_query': str,  # 处理后的查询
                'corrections': List[Tuple[str, str]],  # 纠错列表 [(错误, 正确)]
                'entities': Dict,  # 识别的实体
                'expansions': List[str],  # 扩展查询
                'changes': List[str]  # 变更说明
            }
        """
        result = {
            'original_query': query,
            'processed_query': query,
            'corrections': [],
            'entities': {},
            'expansions': [],
            'changes': []
        }
        
        # 1. 拼写纠错
        if enable_spelling:
            query, corrections = self._correct_spelling(query)
            if corrections:
                result['corrections'] = corrections
                result['processed_query'] = query
                result['changes'].append(f"拼写纠错: {len(corrections)}处")
        
        # 2. 同义词替换
        if enable_synonym:
            query, synonyms_used = self._replace_synonyms(query)
            if synonyms_used:
                result['processed_query'] = query
                result['changes'].append(f"同义词替换: {len(synonyms_used)}处")
        
        # 3. 实体识别
        if enable_entity:
            entities = self._extract_entities(query)
            if entities:
                result['entities'] = entities
                result['changes'].append(f"实体识别: {sum(len(v) for v in entities.values())}个")
        
        # 4. 查询扩展
        if enable_expansion:
            expansions = self._expand_query(query, result['entities'])
            if expansions:
                result['expansions'] = expansions
                result['changes'].append(f"查询扩展: {len(expansions)}个变体")
        
        # 记录日志
        if result['changes']:
            logger.info(f"🔧 查询预处理: {', '.join(result['changes'])}")
            logger.debug(f"   原始: {result['original_query']}")
            logger.debug(f"   处理后: {result['processed_query']}")
        
        return result
    
    def _correct_spelling(self, query: str) -> Tuple[str, List[Tuple[str, str]]]:
        """
        拼写纠错
        
        Args:
            query: 查询文本
        
        Returns:
            (纠正后的查询, 纠错列表)
        """
        corrections = []
        corrected_query = query
        
        for wrong, correct in self.spelling_corrections.items():
            if wrong in corrected_query:
                corrected_query = corrected_query.replace(wrong, correct)
                corrections.append((wrong, correct))
        
        return corrected_query, corrections
    
    def _replace_synonyms(self, query: str) -> Tuple[str, List[str]]:
        """
        同义词替换（保持原查询，但记录同义词用于扩展）
        
        Args:
            query: 查询文本
        
        Returns:
            (查询文本, 使用的同义词列表)
        """
        # 注意：这里不直接替换，而是记录同义词用于后续扩展
        # 直接替换可能改变用户意图
        synonyms_used = []
        
        for standard_word, synonym_list in self.synonyms.items():
            if standard_word in query:
                synonyms_used.append(standard_word)
        
        return query, synonyms_used
    
    def _extract_entities(self, query: str) -> Dict[str, List[str]]:
        """
        实体识别
        
        Args:
            query: 查询文本
        
        Returns:
            实体字典 {实体类型: [实体值列表]}
        """
        entities = {}
        
        # 识别IP地址
        ip_matches = self.ip_pattern.findall(query)
        if ip_matches:
            entities['ip_addresses'] = list(set(ip_matches))
        
        # 识别实例ID
        instance_matches = self.instance_id_pattern.findall(query)
        if instance_matches:
            entities['instance_ids'] = list(set(instance_matches))
        
        # 识别集群名称
        cluster_matches = self.cluster_name_pattern.findall(query)
        if cluster_matches:
            entities['cluster_names'] = list(set(cluster_matches))
        
        # 识别时间范围
        time_ranges = []
        for time_type, pattern in self.time_range_patterns.items():
            if pattern.search(query):
                time_ranges.append(time_type)
        if time_ranges:
            entities['time_ranges'] = time_ranges
        
        return entities
    
    def _expand_query(self, query: str, entities: Dict) -> List[str]:
        """
        查询扩展（生成查询变体）
        
        Args:
            query: 查询文本
            entities: 识别的实体
        
        Returns:
            扩展查询列表
        """
        expansions = []
        
        # 1. 基于同义词的扩展
        for standard_word, synonym_list in self.synonyms.items():
            if standard_word in query:
                # 生成同义词变体（最多3个）
                for synonym in synonym_list[:3]:
                    expanded = query.replace(standard_word, synonym)
                    if expanded != query:
                        expansions.append(expanded)
        
        # 2. 基于实体的扩展
        if entities.get('ip_addresses'):
            # 如果有IP地址，添加"所属集群"查询
            for ip in entities['ip_addresses'][:2]:  # 最多2个IP
                expansions.append(f"{ip} 所属的集群")
                expansions.append(f"查询 {ip} 的详细信息")
        
        if entities.get('instance_ids'):
            # 如果有实例ID，添加"配置信息"查询
            for instance_id in entities['instance_ids'][:2]:
                expansions.append(f"{instance_id} 的配置信息")
                expansions.append(f"查询 {instance_id} 的状态")
        
        # 3. 短查询扩展（查询长度 < 10 个字符）
        if len(query) < 10:
            # 添加常见的查询模板
            if "查询" not in query and "统计" not in query:
                expansions.append(f"查询{query}")
                expansions.append(f"统计{query}")
        
        # 去重并限制数量（最多5个扩展）
        expansions = list(dict.fromkeys(expansions))[:5]
        
        return expansions
    
    def get_synonym_suggestions(self, word: str) -> List[str]:
        """
        获取同义词建议
        
        Args:
            word: 单词
        
        Returns:
            同义词列表
        """
        # 查找标准词
        if word in self.synonyms:
            return self.synonyms[word]
        
        # 查找是否是某个标准词的同义词
        for standard_word, synonym_list in self.synonyms.items():
            if word in synonym_list:
                return [standard_word] + [s for s in synonym_list if s != word]
        
        return []
    
    def add_synonym(self, standard_word: str, synonyms: List[str]):
        """
        添加同义词
        
        Args:
            standard_word: 标准词
            synonyms: 同义词列表
        """
        if standard_word in self.synonyms:
            # 合并同义词
            self.synonyms[standard_word] = list(set(
                self.synonyms[standard_word] + synonyms
            ))
        else:
            self.synonyms[standard_word] = synonyms
        
        logger.info(f"✅ 添加同义词: {standard_word} -> {synonyms}")
    
    def add_spelling_correction(self, wrong: str, correct: str):
        """
        添加拼写纠错规则
        
        Args:
            wrong: 错误拼写
            correct: 正确拼写
        """
        self.spelling_corrections[wrong] = correct
        logger.info(f"✅ 添加拼写纠错: {wrong} -> {correct}")


    def get_statistics(self) -> Dict[str, Any]:
        """
        获取查询预处理统计数据

        Returns:
            统计数据字典

        参考: 字节跳动RAG 8.1节和13.3节 - 性能监控
        """
        # 注意: 这里返回的是累计统计,实际使用中可能需要添加计数器
        # 为了简化实现,我们返回基础统计信息
        return {
            'synonym_dict_size': len(self.synonyms),
            'spelling_corrections_size': len(self.spelling_corrections),
            'total_synonyms': sum(len(v) for v in self.synonyms.values()),
            'entity_patterns': {
                'ip_address': 1,
                'instance_id': 1,
                'cluster_name': 1,
                'time_ranges': len(self.time_range_patterns)
            }
        }



# 全局实例
_query_preprocessor = None


def get_query_preprocessor() -> QueryPreprocessor:
    """获取查询预处理器实例"""
    global _query_preprocessor
    
    if _query_preprocessor is None:
        _query_preprocessor = QueryPreprocessor()
    
    return _query_preprocessor
