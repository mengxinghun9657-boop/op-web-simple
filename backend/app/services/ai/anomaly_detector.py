#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
异常检测系统（Anomaly Detector）

参考: 字节跳动RAG 8.2节 - 异常检测和自动修复

实现功能：
- 路由异常检测（置信度持续低于阈值、规则匹配率下降、响应时间异常）
- 自动修复建议生成
- 异常记录和统计
"""

import time
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, deque

from app.core.logger import logger


class AnomalyDetector:
    """异常检测系统"""
    
    # 异常类型定义
    ANOMALY_LOW_CONFIDENCE = "low_confidence"  # 置信度持续低于阈值
    ANOMALY_RULE_MATCH_DROP = "rule_match_drop"  # 规则匹配率下降
    ANOMALY_HIGH_LATENCY = "high_latency"  # 响应时间异常
    ANOMALY_ERROR_RATE_HIGH = "error_rate_high"  # 错误率过高
    
    def __init__(
        self,
        confidence_threshold: float = 0.7,
        confidence_window_size: int = 100,
        confidence_anomaly_ratio: float = 0.3,
        rule_match_window_size: int = 100,
        rule_match_drop_threshold: float = 0.2,
        latency_threshold_ms: float = 1000.0,
        latency_window_size: int = 100,
        latency_anomaly_ratio: float = 0.2,
        error_rate_threshold: float = 0.1,
        error_rate_window_size: int = 100
    ):
        """
        初始化异常检测系统
        
        Args:
            confidence_threshold: 置信度阈值（默认0.7）
            confidence_window_size: 置信度滑动窗口大小（默认100）
            confidence_anomaly_ratio: 置信度异常比例阈值（默认0.3，即30%的请求低于阈值）
            rule_match_window_size: 规则匹配滑动窗口大小（默认100）
            rule_match_drop_threshold: 规则匹配率下降阈值（默认0.2，即下降20%）
            latency_threshold_ms: 响应时间阈值（毫秒，默认1000ms）
            latency_window_size: 响应时间滑动窗口大小（默认100）
            latency_anomaly_ratio: 响应时间异常比例阈值（默认0.2，即20%的请求超时）
            error_rate_threshold: 错误率阈值（默认0.1，即10%）
            error_rate_window_size: 错误率滑动窗口大小（默认100）
        """
        # 置信度监控
        self.confidence_threshold = confidence_threshold
        self.confidence_window = deque(maxlen=confidence_window_size)
        self.confidence_anomaly_ratio = confidence_anomaly_ratio
        
        # 规则匹配率监控
        self.rule_match_window = deque(maxlen=rule_match_window_size)
        self.rule_match_drop_threshold = rule_match_drop_threshold
        self.baseline_rule_match_rate = None  # 基线规则匹配率
        
        # 响应时间监控
        self.latency_threshold_ms = latency_threshold_ms
        self.latency_window = deque(maxlen=latency_window_size)
        self.latency_anomaly_ratio = latency_anomaly_ratio
        
        # 错误率监控
        self.error_rate_threshold = error_rate_threshold
        self.error_window = deque(maxlen=error_rate_window_size)
        
        # 异常记录
        self.anomalies: List[Dict] = []
        
        # 统计数据
        self.stats = {
            'total_requests': 0,
            'low_confidence_count': 0,
            'rule_match_count': 0,
            'high_latency_count': 0,
            'error_count': 0,
            'anomaly_detected_count': 0
        }
        
        logger.info("✅ 异常检测系统初始化成功")
    
    def record_routing(
        self,
        confidence: float,
        routing_method: str,
        latency_ms: float,
        is_error: bool = False
    ):
        """
        记录路由请求数据
        
        Args:
            confidence: 置信度
            routing_method: 路由方法（forced_rule/routing_rule/ernie/similarity/keyword）
            latency_ms: 响应时间（毫秒）
            is_error: 是否发生错误
        """
        # 更新统计
        self.stats['total_requests'] += 1
        
        # 记录置信度
        self.confidence_window.append(confidence)
        if confidence < self.confidence_threshold:
            self.stats['low_confidence_count'] += 1
        
        # 记录规则匹配
        is_rule_matched = routing_method in ['forced_rule', 'routing_rule']
        self.rule_match_window.append(is_rule_matched)
        if is_rule_matched:
            self.stats['rule_match_count'] += 1
        
        # 记录响应时间
        self.latency_window.append(latency_ms)
        if latency_ms > self.latency_threshold_ms:
            self.stats['high_latency_count'] += 1
        
        # 记录错误
        self.error_window.append(is_error)
        if is_error:
            self.stats['error_count'] += 1
    
    def detect_anomalies(self) -> List[Dict]:
        """
        检测异常
        
        Returns:
            异常列表，每个异常包含：
            - type: 异常类型
            - severity: 严重程度（low/medium/high）
            - description: 异常描述
            - metrics: 相关指标
            - suggestions: 修复建议
            - detected_at: 检测时间
        
        参考: 字节跳动RAG 8.2节 - 路由异常检测
        """
        detected_anomalies = []
        
        # 1. 检测置信度持续低于阈值
        anomaly = self._detect_low_confidence()
        if anomaly:
            detected_anomalies.append(anomaly)
        
        # 2. 检测规则匹配率下降
        anomaly = self._detect_rule_match_drop()
        if anomaly:
            detected_anomalies.append(anomaly)
        
        # 3. 检测响应时间异常
        anomaly = self._detect_high_latency()
        if anomaly:
            detected_anomalies.append(anomaly)
        
        # 4. 检测错误率过高
        anomaly = self._detect_high_error_rate()
        if anomaly:
            detected_anomalies.append(anomaly)
        
        # 记录检测到的异常
        if detected_anomalies:
            self.stats['anomaly_detected_count'] += len(detected_anomalies)
            self.anomalies.extend(detected_anomalies)
            
            # 只保留最近1000条异常记录
            if len(self.anomalies) > 1000:
                self.anomalies = self.anomalies[-1000:]
            
            logger.warning(f"⚠️ 检测到 {len(detected_anomalies)} 个异常")
        
        return detected_anomalies
    
    def _detect_low_confidence(self) -> Optional[Dict]:
        """
        检测置信度持续低于阈值
        
        Returns:
            异常信息或None
        """
        if len(self.confidence_window) < 10:
            return None
        
        # 计算低置信度比例
        low_confidence_count = sum(1 for c in self.confidence_window if c < self.confidence_threshold)
        low_confidence_ratio = low_confidence_count / len(self.confidence_window)
        
        # 如果低置信度比例超过阈值，触发异常
        if low_confidence_ratio > self.confidence_anomaly_ratio:
            avg_confidence = sum(self.confidence_window) / len(self.confidence_window)
            
            # 确定严重程度
            if low_confidence_ratio > 0.5:
                severity = "high"
            elif low_confidence_ratio > 0.4:
                severity = "medium"
            else:
                severity = "low"
            
            return {
                'type': self.ANOMALY_LOW_CONFIDENCE,
                'severity': severity,
                'description': f'置信度持续低于阈值：{low_confidence_ratio:.1%} 的请求置信度 < {self.confidence_threshold}',
                'metrics': {
                    'low_confidence_ratio': low_confidence_ratio,
                    'avg_confidence': avg_confidence,
                    'threshold': self.confidence_threshold,
                    'window_size': len(self.confidence_window)
                },
                'suggestions': self._generate_low_confidence_suggestions(low_confidence_ratio, avg_confidence),
                'detected_at': datetime.now().isoformat()
            }
        
        return None
    
    def _detect_rule_match_drop(self) -> Optional[Dict]:
        """
        检测规则匹配率下降
        
        Returns:
            异常信息或None
        """
        if len(self.rule_match_window) < 10:
            return None
        
        # 计算当前规则匹配率
        current_match_rate = sum(self.rule_match_window) / len(self.rule_match_window)
        
        # 如果还没有基线，设置基线
        if self.baseline_rule_match_rate is None:
            if len(self.rule_match_window) >= 50:  # 至少50个样本才设置基线
                self.baseline_rule_match_rate = current_match_rate
            return None
        
        # 计算匹配率下降幅度
        drop_ratio = (self.baseline_rule_match_rate - current_match_rate) / max(self.baseline_rule_match_rate, 0.01)
        
        # 如果下降幅度超过阈值，触发异常
        if drop_ratio > self.rule_match_drop_threshold:
            # 确定严重程度
            if drop_ratio > 0.5:
                severity = "high"
            elif drop_ratio > 0.3:
                severity = "medium"
            else:
                severity = "low"
            
            return {
                'type': self.ANOMALY_RULE_MATCH_DROP,
                'severity': severity,
                'description': f'规则匹配率下降：从 {self.baseline_rule_match_rate:.1%} 降至 {current_match_rate:.1%}（下降 {drop_ratio:.1%}）',
                'metrics': {
                    'baseline_match_rate': self.baseline_rule_match_rate,
                    'current_match_rate': current_match_rate,
                    'drop_ratio': drop_ratio,
                    'threshold': self.rule_match_drop_threshold,
                    'window_size': len(self.rule_match_window)
                },
                'suggestions': self._generate_rule_match_drop_suggestions(drop_ratio, current_match_rate),
                'detected_at': datetime.now().isoformat()
            }
        
        return None
    
    def _detect_high_latency(self) -> Optional[Dict]:
        """
        检测响应时间异常
        
        Returns:
            异常信息或None
        """
        if len(self.latency_window) < 10:
            return None
        
        # 计算高延迟比例
        high_latency_count = sum(1 for l in self.latency_window if l > self.latency_threshold_ms)
        high_latency_ratio = high_latency_count / len(self.latency_window)
        
        # 如果高延迟比例超过阈值，触发异常
        if high_latency_ratio > self.latency_anomaly_ratio:
            avg_latency = sum(self.latency_window) / len(self.latency_window)
            p95_latency = sorted(self.latency_window)[int(len(self.latency_window) * 0.95)]
            
            # 确定严重程度
            if high_latency_ratio > 0.5:
                severity = "high"
            elif high_latency_ratio > 0.3:
                severity = "medium"
            else:
                severity = "low"
            
            return {
                'type': self.ANOMALY_HIGH_LATENCY,
                'severity': severity,
                'description': f'响应时间异常：{high_latency_ratio:.1%} 的请求响应时间 > {self.latency_threshold_ms}ms',
                'metrics': {
                    'high_latency_ratio': high_latency_ratio,
                    'avg_latency_ms': avg_latency,
                    'p95_latency_ms': p95_latency,
                    'threshold_ms': self.latency_threshold_ms,
                    'window_size': len(self.latency_window)
                },
                'suggestions': self._generate_high_latency_suggestions(high_latency_ratio, avg_latency, p95_latency),
                'detected_at': datetime.now().isoformat()
            }
        
        return None
    
    def _detect_high_error_rate(self) -> Optional[Dict]:
        """
        检测错误率过高
        
        Returns:
            异常信息或None
        """
        if len(self.error_window) < 10:
            return None
        
        # 计算错误率
        error_count = sum(self.error_window)
        error_rate = error_count / len(self.error_window)
        
        # 如果错误率超过阈值，触发异常
        if error_rate > self.error_rate_threshold:
            # 确定严重程度
            if error_rate > 0.3:
                severity = "high"
            elif error_rate > 0.2:
                severity = "medium"
            else:
                severity = "low"
            
            return {
                'type': self.ANOMALY_ERROR_RATE_HIGH,
                'severity': severity,
                'description': f'错误率过高：{error_rate:.1%} 的请求发生错误',
                'metrics': {
                    'error_rate': error_rate,
                    'error_count': error_count,
                    'threshold': self.error_rate_threshold,
                    'window_size': len(self.error_window)
                },
                'suggestions': self._generate_high_error_rate_suggestions(error_rate),
                'detected_at': datetime.now().isoformat()
            }
        
        return None
    
    def _generate_low_confidence_suggestions(
        self,
        low_confidence_ratio: float,
        avg_confidence: float
    ) -> List[str]:
        """
        生成低置信度异常的修复建议
        
        Args:
            low_confidence_ratio: 低置信度比例
            avg_confidence: 平均置信度
        
        Returns:
            修复建议列表
        
        参考: 字节跳动RAG 8.2节 - 自动修复建议生成
        """
        suggestions = []
        
        # 建议1: 检查ERNIE模型状态
        suggestions.append("检查ERNIE模型状态：确认模型是否正常运行，是否需要重启或更新")
        
        # 建议2: 优化意图分类Prompt
        if avg_confidence < 0.6:
            suggestions.append("优化意图分类Prompt：当前平均置信度过低，建议优化Prompt模板，增加更多示例和分类规则")
        
        # 建议3: 扩展路由规则库
        suggestions.append("扩展路由规则库：添加更多路由规则，覆盖常见查询模式，减少对ERNIE的依赖")
        
        # 建议4: 检查典型问题库
        suggestions.append("检查典型问题库：确认典型问题库是否完整，是否需要补充新的示例")
        
        # 建议5: 启用查询预处理
        suggestions.append("启用查询预处理：使用同义词替换、拼写纠错等预处理功能，提高查询质量")
        
        return suggestions
    
    def _generate_rule_match_drop_suggestions(
        self,
        drop_ratio: float,
        current_match_rate: float
    ) -> List[str]:
        """
        生成规则匹配率下降异常的修复建议
        
        Args:
            drop_ratio: 下降比例
            current_match_rate: 当前匹配率
        
        Returns:
            修复建议列表
        """
        suggestions = []
        
        # 建议1: 检查规则库状态
        suggestions.append("检查规则库状态：确认路由规则是否被误删除或禁用")
        
        # 建议2: 分析未匹配查询
        suggestions.append("分析未匹配查询：查看最近未匹配规则的查询，识别新的查询模式")
        
        # 建议3: 更新规则向量索引
        if drop_ratio > 0.3:
            suggestions.append("更新规则向量索引：重新构建向量索引，确保索引与规则库同步")
        
        # 建议4: 调整相似度阈值
        suggestions.append("调整相似度阈值：当前阈值可能过高，建议适当降低（如从0.7降至0.65）")
        
        # 建议5: 启用RRF融合算法
        suggestions.append("启用RRF融合算法：使用向量检索+关键词检索融合，提高规则匹配率")
        
        return suggestions
    
    def _generate_high_latency_suggestions(
        self,
        high_latency_ratio: float,
        avg_latency: float,
        p95_latency: float
    ) -> List[str]:
        """
        生成高延迟异常的修复建议
        
        Args:
            high_latency_ratio: 高延迟比例
            avg_latency: 平均延迟
            p95_latency: P95延迟
        
        Returns:
            修复建议列表
        """
        suggestions = []
        
        # 建议1: 检查向量数据库性能
        suggestions.append("检查向量数据库性能：确认向量数据库负载是否过高，是否需要扩容")
        
        # 建议2: 优化检索参数
        if p95_latency > 2000:
            suggestions.append("优化检索参数：降低HNSW索引的efSearch参数，减少检索时间")
        
        # 建议3: 启用缓存
        suggestions.append("启用缓存：对高频查询启用Redis缓存，减少重复检索")
        
        # 建议4: 检查ERNIE API
        if avg_latency > 1500:
            suggestions.append("检查ERNIE API：确认ERNIE API响应时间是否正常，是否需要切换到备用模型")
        
        # 建议5: 负载均衡优化
        suggestions.append("负载均衡优化：检查负载均衡配置，确保请求均匀分配到各节点")
        
        return suggestions
    
    def _generate_high_error_rate_suggestions(
        self,
        error_rate: float
    ) -> List[str]:
        """
        生成高错误率异常的修复建议
        
        Args:
            error_rate: 错误率
        
        Returns:
            修复建议列表
        """
        suggestions = []
        
        # 建议1: 检查系统日志
        suggestions.append("检查系统日志：查看详细错误日志，定位错误根因")
        
        # 建议2: 检查依赖服务
        suggestions.append("检查依赖服务：确认ERNIE API、向量数据库、Redis等依赖服务是否正常")
        
        # 建议3: 检查网络连接
        if error_rate > 0.2:
            suggestions.append("检查网络连接：确认网络是否稳定，是否存在超时或连接失败")
        
        # 建议4: 回滚最近更新
        suggestions.append("回滚最近更新：如果错误率突然升高，考虑回滚最近的代码或配置更新")
        
        # 建议5: 启用降级策略
        suggestions.append("启用降级策略：在依赖服务异常时，使用关键词规则等降级方案")
        
        return suggestions
    
    def get_statistics(self) -> Dict:
        """
        获取统计数据
        
        Returns:
            统计数据字典
        """
        # 计算各项指标
        total = max(self.stats['total_requests'], 1)
        
        return {
            'total_requests': self.stats['total_requests'],
            'low_confidence_rate': self.stats['low_confidence_count'] / total,
            'rule_match_rate': self.stats['rule_match_count'] / total,
            'high_latency_rate': self.stats['high_latency_count'] / total,
            'error_rate': self.stats['error_count'] / total,
            'anomaly_detected_count': self.stats['anomaly_detected_count'],
            'current_metrics': {
                'avg_confidence': sum(self.confidence_window) / len(self.confidence_window) if self.confidence_window else 0,
                'current_rule_match_rate': sum(self.rule_match_window) / len(self.rule_match_window) if self.rule_match_window else 0,
                'avg_latency_ms': sum(self.latency_window) / len(self.latency_window) if self.latency_window else 0,
                'current_error_rate': sum(self.error_window) / len(self.error_window) if self.error_window else 0
            }
        }
    
    def get_recent_anomalies(
        self,
        limit: int = 10,
        severity: Optional[str] = None,
        anomaly_type: Optional[str] = None
    ) -> List[Dict]:
        """
        获取最近的异常记录
        
        Args:
            limit: 返回数量限制
            severity: 严重程度过滤（low/medium/high）
            anomaly_type: 异常类型过滤
        
        Returns:
            异常记录列表
        """
        # 过滤异常
        filtered_anomalies = self.anomalies
        
        if severity:
            filtered_anomalies = [a for a in filtered_anomalies if a['severity'] == severity]
        
        if anomaly_type:
            filtered_anomalies = [a for a in filtered_anomalies if a['type'] == anomaly_type]
        
        # 返回最近的N条
        return filtered_anomalies[-limit:]
    
    def reset_baseline(self):
        """重置基线指标"""
        self.baseline_rule_match_rate = None
        logger.info("✅ 基线指标已重置")


# 全局实例（可选）
_anomaly_detector = None


def get_anomaly_detector() -> AnomalyDetector:
    """获取异常检测系统实例"""
    global _anomaly_detector
    
    if _anomaly_detector is None:
        _anomaly_detector = AnomalyDetector()
    
    return _anomaly_detector
