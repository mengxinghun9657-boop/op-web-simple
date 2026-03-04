#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
规则冲突检测服务

实现需求：
- Requirements 3.4: 检测与现有规则的潜在冲突
- Requirements 3.5: 显示冲突的规则列表
- Requirements 10.1-10.6: 完整的冲突检测逻辑
"""

import re
import logging
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from app.models.routing_rule import RoutingRule
from app.services.ai.embedding_model import get_embedding_model

logger = logging.getLogger(__name__)


class ConflictDetector:
    """规则冲突检测器"""
    
    def __init__(self, db: Session):
        self.db = db
        self.embedding_model = get_embedding_model()
        self.similarity_threshold = 0.8  # 语义相似度阈值
    
    async def detect_conflicts(
        self,
        pattern: str,
        intent_type: str,
        exclude_rule_id: Optional[int] = None
    ) -> List[Dict]:
        """
        检测规则冲突
        
        Args:
            pattern: 匹配模式
            intent_type: 意图类型
            exclude_rule_id: 排除的规则ID（编辑时使用）
            
        Returns:
            List[Dict]: 冲突列表，每个冲突包含：
                - rule_id: 冲突规则ID
                - pattern: 冲突规则模式
                - conflict_type: 冲突类型
                - severity: 严重程度
                - description: 详细描述
        """
        conflicts = []
        
        # 获取所有启用的规则
        query = self.db.query(RoutingRule).filter(
            RoutingRule.is_active == True
        )
        
        if exclude_rule_id:
            query = query.filter(RoutingRule.id != exclude_rule_id)
        
        existing_rules = query.all()
        
        for rule in existing_rules:
            # 1. 检测完全相同
            if self._is_exact_match(pattern, rule.pattern):
                conflicts.append({
                    "rule_id": rule.id,
                    "pattern": rule.pattern,
                    "conflict_type": "完全相同",
                    "severity": "高",
                    "description": f"与规则#{rule.id}的模式完全相同"
                })
                continue
            
            # 2. 检测语义相似
            similarity = await self._calculate_similarity(pattern, rule.pattern)
            if similarity > self.similarity_threshold:
                conflicts.append({
                    "rule_id": rule.id,
                    "pattern": rule.pattern,
                    "conflict_type": "语义相似",
                    "severity": "中",
                    "description": f"与规则#{rule.id}语义相似度{similarity:.2f}，可能匹配相同查询",
                    "similarity": similarity
                })
                continue
            
            # 3. 检测包含关系（仅对正则表达式）
            if self._is_regex_pattern(pattern) and self._is_regex_pattern(rule.pattern):
                containment = self._check_containment(pattern, rule.pattern)
                if containment:
                    conflicts.append({
                        "rule_id": rule.id,
                        "pattern": rule.pattern,
                        "conflict_type": containment["type"],
                        "severity": containment["severity"],
                        "description": containment["description"]
                    })
        
        # 按严重程度排序
        severity_order = {"高": 0, "中": 1, "低": 2}
        conflicts.sort(key=lambda x: severity_order.get(x["severity"], 3))
        
        return conflicts
    
    def _is_exact_match(self, pattern1: str, pattern2: str) -> bool:
        """检测完全相同"""
        return pattern1.strip() == pattern2.strip()
    
    async def _calculate_similarity(self, pattern1: str, pattern2: str) -> float:
        """计算语义相似度"""
        try:
            # 获取向量
            vec1 = await self.embedding_model.embed_text(pattern1)
            vec2 = await self.embedding_model.embed_text(pattern2)
            
            # 计算余弦相似度
            import numpy as np
            similarity = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
            
            return float(similarity)
            
        except Exception as e:
            logger.error(f"计算相似度失败: {str(e)}")
            return 0.0
    
    def _is_regex_pattern(self, pattern: str) -> bool:
        """判断是否为正则表达式"""
        # 简单判断：包含正则特殊字符
        regex_chars = r'[\.\*\+\?\[\]\(\)\{\}\|\^$\\]'
        return bool(re.search(regex_chars, pattern))
    
    def _check_containment(self, pattern1: str, pattern2: str) -> Optional[Dict]:
        """检测正则表达式包含关系"""
        try:
            # 编译正则表达式
            regex1 = re.compile(pattern1)
            regex2 = re.compile(pattern2)
            
            # 生成测试用例
            test_cases = self._generate_test_cases(pattern1, pattern2)
            
            # 测试匹配情况
            matches1 = [bool(regex1.search(case)) for case in test_cases]
            matches2 = [bool(regex2.search(case)) for case in test_cases]
            
            # 判断包含关系
            if all(m1 == m2 for m1, m2 in zip(matches1, matches2)):
                return None  # 完全相同，已在前面检测
            
            # pattern1 包含 pattern2（pattern1 更宽泛）
            if all(m2 <= m1 for m1, m2 in zip(matches1, matches2)) and any(m1 and not m2 for m1, m2 in zip(matches1, matches2)):
                return {
                    "type": "包含关系",
                    "severity": "中",
                    "description": f"当前规则的匹配范围包含规则#{pattern2}，可能导致优先级问题"
                }
            
            # pattern2 包含 pattern1（pattern2 更宽泛）
            if all(m1 <= m2 for m1, m2 in zip(matches1, matches2)) and any(m2 and not m1 for m1, m2 in zip(matches1, matches2)):
                return {
                    "type": "被包含",
                    "severity": "低",
                    "description": f"规则#{pattern2}的匹配范围包含当前规则"
                }
            
            return None
            
        except Exception as e:
            logger.error(f"检测包含关系失败: {str(e)}")
            return None
    
    def _generate_test_cases(self, pattern1: str, pattern2: str) -> List[str]:
        """生成测试用例"""
        # 简单的测试用例生成
        test_cases = [
            "查询192.168.1.1的信息",
            "10.0.0.1的状态如何",
            "实例i-abc123的配置",
            "主机名是什么",
            "统计服务器数量",
            "如何配置网络",
            "分析报告",
            "普通查询"
        ]
        
        return test_cases
