#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
智能辅助服务

实现需求：
- Requirements 5.1-5.5: 智能描述生成
- Requirements 6.1-6.6: 关键词提取
- Requirements 7.1-7.6: 表推荐
- Requirements 13.1-13.7: 优先级建议
"""

import re
import logging
from typing import Dict, List
from sqlalchemy.orm import Session
from app.services.ai.ernie_client import get_ernie_client

logger = logging.getLogger(__name__)


class IntelligentAssistant:
    """智能辅助服务"""
    
    def __init__(self, db: Session):
        self.db = db
        self.ernie_client = get_ernie_client()
    
    async def generate_description(
        self,
        pattern: str,
        intent_type: str,
        keywords: List[str] = None
    ) -> Dict:
        """生成规则描述"""
        prompt = f"""根据以下信息生成路由规则描述：

匹配模式：{pattern}
意图类型：{intent_type}
关键词：{', '.join(keywords) if keywords else '无'}

请生成：
1. 简短描述（一句话）
2. 规则目的
3. 适用场景（列表）

返回JSON格式：
{{
    "description": "简短描述",
    "purpose": "规则目的",
    "applicable_scenarios": ["场景1", "场景2", "场景3"]
}}
"""
        
        try:
            response = await self.ernie_client.chat([{"role": "user", "content": prompt}])
            import json
            result = json.loads(re.search(r'\{.*\}', response, re.DOTALL).group())
            return result
        except Exception as e:
            logger.error(f"生成描述失败: {str(e)}")
            return {
                "description": f"匹配{pattern}的{intent_type}查询",
                "purpose": f"识别并路由到{intent_type}处理器",
                "applicable_scenarios": ["相关查询场景"]
            }
    
    def extract_keywords(self, pattern: str, pattern_type: str) -> List[Dict]:
        """提取关键词"""
        keywords = []
        
        if pattern_type == "natural_language":
            # 从自然语言提取
            words = re.findall(r'[\u4e00-\u9fa5a-zA-Z]+', pattern)
            for word in words:
                if len(word) > 1:
                    keywords.append({
                        "word": word,
                        "weight": 0.8,
                        "type": "noun"
                    })
        else:
            # 从正则表达式提取字面量
            literals = re.findall(r'[a-zA-Z\u4e00-\u9fa5]{2,}', pattern)
            for literal in literals:
                keywords.append({
                    "word": literal,
                    "weight": 0.9,
                    "type": "literal"
                })
        
        return keywords[:10]  # 最多返回10个
    
    def recommend_tables(
        self,
        keywords: List[str],
        intent_type: str
    ) -> List[Dict]:
        """推荐数据库表"""
        if intent_type != "sql":
            return []
        
        # 简化的表推荐逻辑
        table_mapping = {
            "IP": ["iaas_servers", "mydb.bce_bcc_instances"],
            "实例": ["iaas_instances", "mydb.bce_bcc_instances"],
            "主机": ["iaas_servers"],
            "集群": ["mydb.bce_cce_clusters", "mydb.bce_cce_nodes"],
            "监控": ["mydb.bce_bcc_instances", "mydb.bce_cce_nodes"]
        }
        
        recommended = []
        for keyword in keywords:
            for key, tables in table_mapping.items():
                if key in keyword:
                    for table in tables:
                        if table not in [r["name"] for r in recommended]:
                            recommended.append({
                                "name": table,
                                "category": "CMDB" if "iaas_" in table else "监控数据",
                                "description": f"{table}表",
                                "field_count": 100,
                                "relevance_score": 0.9,
                                "reason": f"包含关键词：{keyword}"
                            })
        
        return recommended[:5]  # 最多返回5个
    
    def suggest_priority(
        self,
        pattern: str,
        intent_type: str,
        keywords: List[str] = None
    ) -> Dict:
        """建议优先级"""
        # 强制规则：90-100
        if any(k in pattern for k in ["IP", "实例ID", "i-"]):
            return {
                "suggested_priority": 95,
                "priority_range": [90, 100],
                "category": "强制规则",
                "reason": "包含明确标识符，应具有最高优先级",
                "conflicts": []
            }
        
        # 业务规则：50-89
        if any(k in pattern for k in ["状态", "配置", "监控", "集群"]):
            return {
                "suggested_priority": 75,
                "priority_range": [50, 89],
                "category": "业务规则",
                "reason": "业务相关查询，中高优先级",
                "conflicts": []
            }
        
        # 通用规则：1-49
        return {
            "suggested_priority": 50,
            "priority_range": [1, 49],
            "category": "通用规则",
            "reason": "通用查询，标准优先级",
            "conflicts": []
        }
