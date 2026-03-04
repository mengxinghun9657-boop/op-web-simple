#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
影响预测服务

实现需求：
- Requirements 16.1-16.6: 规则效果预测
"""

import logging
from typing import Dict, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.routing_log import RoutingLog

logger = logging.getLogger(__name__)


class ImpactPredictor:
    """影响预测器"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def predict_impact(
        self,
        pattern: str,
        intent_type: str
    ) -> Dict:
        """
        预测规则影响
        
        Returns:
            Dict: {
                "affected_query_count": int,
                "affected_query_percentage": float,
                "sample_queries": List[str],
                "expected_accuracy_change": float,
                "expected_usage_frequency": str,
                "warning": str
            }
        """
        try:
            # 查询过去30天的历史数据
            thirty_days_ago = datetime.now() - timedelta(days=30)
            
            # 获取总查询数
            total_count = self.db.query(RoutingLog).filter(
                RoutingLog.created_at >= thirty_days_ago
            ).count()
            
            if total_count == 0:
                return self._get_default_prediction()
            
            # 简化的匹配逻辑（实际应该用正则匹配）
            import re
            try:
                regex = re.compile(pattern)
                
                # 获取所有查询
                logs = self.db.query(RoutingLog).filter(
                    RoutingLog.created_at >= thirty_days_ago
                ).limit(1000).all()
                
                affected_queries = []
                for log in logs:
                    if regex.search(log.query):
                        affected_queries.append(log.query)
                
                affected_count = len(affected_queries)
                affected_percentage = (affected_count / total_count) * 100
                
                # 预测使用频率
                if affected_percentage > 10:
                    frequency = "高"
                    warning = "该规则影响范围较大，请谨慎设置优先级"
                elif affected_percentage > 5:
                    frequency = "中"
                    warning = None
                else:
                    frequency = "低"
                    warning = None
                
                return {
                    "affected_query_count": affected_count,
                    "affected_query_percentage": round(affected_percentage, 2),
                    "sample_queries": affected_queries[:5],
                    "expected_accuracy_change": 0.05,
                    "expected_usage_frequency": frequency,
                    "warning": warning
                }
                
            except re.error:
                return self._get_default_prediction()
                
        except Exception as e:
            logger.error(f"预测影响失败: {str(e)}")
            return self._get_default_prediction()
    
    def _get_default_prediction(self) -> Dict:
        """获取默认预测结果"""
        return {
            "affected_query_count": 0,
            "affected_query_percentage": 0.0,
            "sample_queries": [],
            "expected_accuracy_change": 0.0,
            "expected_usage_frequency": "未知",
            "warning": "历史数据不足，无法准确预测"
        }
