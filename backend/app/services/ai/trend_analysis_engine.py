#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
趋势分析引擎
用于集群资源使用趋势分析和预测
"""
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timedelta
from scipy import stats


class TrendAnalysisEngine:
    """趋势分析引擎"""
    
    def __init__(self):
        """初始化趋势分析引擎"""
        pass
    
    def moving_average(self, data: List[float], window_size: int = 3) -> List[float]:
        """
        计算移动平均
        
        Args:
            data: 时间序列数据
            window_size: 窗口大小
            
        Returns:
            平滑后的数据
        """
        if len(data) < window_size:
            return data
        
        smoothed = []
        for i in range(len(data)):
            if i < window_size - 1:
                # 前面不足窗口大小的点，使用可用的数据
                smoothed.append(np.mean(data[:i+1]))
            else:
                # 使用完整窗口
                smoothed.append(np.mean(data[i-window_size+1:i+1]))
        
        return smoothed
    
    def linear_regression_forecast(
        self, 
        data: List[float], 
        forecast_periods: int = 7
    ) -> Tuple[List[float], Dict[str, float]]:
        """
        使用线性回归进行趋势预测
        
        Args:
            data: 历史数据
            forecast_periods: 预测周期数
            
        Returns:
            (预测值列表, 统计信息字典)
        """
        if len(data) < 2:
            return [], {}
        
        # 准备数据
        x = np.arange(len(data))
        y = np.array(data)
        
        # 线性回归
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
        
        # 预测未来值
        future_x = np.arange(len(data), len(data) + forecast_periods)
        forecast = slope * future_x + intercept
        
        # 统计信息
        stats_info = {
            'slope': float(slope),
            'intercept': float(intercept),
            'r_squared': float(r_value ** 2),
            'p_value': float(p_value),
            'std_err': float(std_err),
            'trend': 'increasing' if slope > 0 else 'decreasing' if slope < 0 else 'stable'
        }
        
        return forecast.tolist(), stats_info
    
    def analyze_cpu_trend(
        self, 
        cpu_usage_history: List[Dict[str, Any]],
        forecast_days: int = 7
    ) -> Dict[str, Any]:
        """
        分析CPU使用率趋势
        
        Args:
            cpu_usage_history: CPU使用率历史数据
                格式: [{'timestamp': '2024-01-01', 'usage_percent': 6.15}, ...]
            forecast_days: 预测天数
            
        Returns:
            趋势分析结果
        """
        if not cpu_usage_history:
            return {'error': '没有历史数据'}
        
        # 提取使用率数据
        usage_data = [item['usage_percent'] for item in cpu_usage_history]
        timestamps = [item['timestamp'] for item in cpu_usage_history]
        
        # 移动平均平滑
        smoothed_data = self.moving_average(usage_data, window_size=3)
        
        # 线性回归预测
        forecast, stats_info = self.linear_regression_forecast(
            smoothed_data, 
            forecast_periods=forecast_days
        )
        
        # 生成预测时间戳
        if timestamps:
            last_timestamp = datetime.fromisoformat(timestamps[-1])
            forecast_timestamps = [
                (last_timestamp + timedelta(days=i+1)).isoformat()
                for i in range(forecast_days)
            ]
        else:
            forecast_timestamps = []
        
        return {
            'metric': 'cpu_usage_percent',
            'historical_data': {
                'timestamps': timestamps,
                'raw_values': usage_data,
                'smoothed_values': smoothed_data
            },
            'forecast': {
                'timestamps': forecast_timestamps,
                'values': forecast,
                'confidence': stats_info.get('r_squared', 0)
            },
            'statistics': stats_info,
            'insights': self._generate_cpu_insights(usage_data, forecast, stats_info)
        }
    
    def analyze_memory_trend(
        self, 
        memory_usage_history: List[Dict[str, Any]],
        forecast_days: int = 7
    ) -> Dict[str, Any]:
        """
        分析内存使用率趋势
        
        Args:
            memory_usage_history: 内存使用率历史数据
                格式: [{'timestamp': '2024-01-01', 'usage_percent': 19.83}, ...]
            forecast_days: 预测天数
            
        Returns:
            趋势分析结果
        """
        if not memory_usage_history:
            return {'error': '没有历史数据'}
        
        # 提取使用率数据
        usage_data = [item['usage_percent'] for item in memory_usage_history]
        timestamps = [item['timestamp'] for item in memory_usage_history]
        
        # 移动平均平滑
        smoothed_data = self.moving_average(usage_data, window_size=3)
        
        # 线性回归预测
        forecast, stats_info = self.linear_regression_forecast(
            smoothed_data, 
            forecast_periods=forecast_days
        )
        
        # 生成预测时间戳
        if timestamps:
            last_timestamp = datetime.fromisoformat(timestamps[-1])
            forecast_timestamps = [
                (last_timestamp + timedelta(days=i+1)).isoformat()
                for i in range(forecast_days)
            ]
        else:
            forecast_timestamps = []
        
        return {
            'metric': 'memory_usage_percent',
            'historical_data': {
                'timestamps': timestamps,
                'raw_values': usage_data,
                'smoothed_values': smoothed_data
            },
            'forecast': {
                'timestamps': forecast_timestamps,
                'values': forecast,
                'confidence': stats_info.get('r_squared', 0)
            },
            'statistics': stats_info,
            'insights': self._generate_memory_insights(usage_data, forecast, stats_info)
        }
    
    def _generate_cpu_insights(
        self, 
        historical: List[float], 
        forecast: List[float],
        stats: Dict[str, float]
    ) -> List[str]:
        """生成CPU趋势洞察"""
        insights = []
        
        if not historical or not forecast:
            return insights
        
        current_usage = historical[-1]
        avg_usage = np.mean(historical)
        predicted_usage = forecast[-1] if forecast else current_usage
        
        # 趋势判断
        if stats.get('trend') == 'increasing':
            insights.append(f"CPU使用率呈上升趋势，预计7天后将达到 {predicted_usage:.2f}%")
            if predicted_usage > 80:
                insights.append("⚠️ 警告：预测使用率将超过80%，建议考虑扩容")
        elif stats.get('trend') == 'decreasing':
            insights.append(f"CPU使用率呈下降趋势，预计7天后将降至 {predicted_usage:.2f}%")
        else:
            insights.append(f"CPU使用率保持稳定，当前约 {current_usage:.2f}%")
        
        # 使用率水平判断
        if current_usage < 20:
            insights.append("💡 当前CPU使用率较低，存在资源优化空间")
        elif current_usage > 70:
            insights.append("⚠️ 当前CPU使用率较高，建议关注性能")
        
        return insights
    
    def _generate_memory_insights(
        self, 
        historical: List[float], 
        forecast: List[float],
        stats: Dict[str, float]
    ) -> List[str]:
        """生成内存趋势洞察"""
        insights = []
        
        if not historical or not forecast:
            return insights
        
        current_usage = historical[-1]
        avg_usage = np.mean(historical)
        predicted_usage = forecast[-1] if forecast else current_usage
        
        # 趋势判断
        if stats.get('trend') == 'increasing':
            insights.append(f"内存使用率呈上升趋势，预计7天后将达到 {predicted_usage:.2f}%")
            if predicted_usage > 80:
                insights.append("⚠️ 警告：预测使用率将超过80%，建议考虑扩容")
        elif stats.get('trend') == 'decreasing':
            insights.append(f"内存使用率呈下降趋势，预计7天后将降至 {predicted_usage:.2f}%")
        else:
            insights.append(f"内存使用率保持稳定，当前约 {current_usage:.2f}%")
        
        # 使用率水平判断
        if current_usage < 30:
            insights.append("💡 当前内存使用率较低，存在资源优化空间")
        elif current_usage > 70:
            insights.append("⚠️ 当前内存使用率较高，建议关注性能")
        
        return insights
