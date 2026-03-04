#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
BCC监控分析器
完全重构，解决100+实例时的可读性问题
采用"倒金字塔"信息架构
"""

import pandas as pd
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from pathlib import Path
import json


class BCCAnalyzerAI:
    """BCC实例CPU/内存监控分析器"""
    
    def __init__(self, bcm_client=None, user_id: str = "f008db4751894afe9b851e32a2068335"):
        """
        初始化BCC分析器
        
        Args:
            bcm_client: BCM客户端实例
            user_id: 百度云用户ID
        """
        self.client = bcm_client
        self.user_id = user_id
        self.scope = "BCE_BCC"
        self.region = "cd"
        self.bcc_instances = []
        
        # 初始化ERNIE客户端用于AI解读
        self.ernie_client = None
        try:
            from app.services.ai.ernie_client import get_ernie_client
            self.ernie_client = get_ernie_client()
            print("ERNIE客户端初始化成功")
        except Exception as e:
            print(f"ERNIE客户端初始化失败: {e}，将使用本地算法")
    
    def load_instances_from_file(self, file_path: str) -> List[str]:
        """从文件加载BCC实例列表"""
        try:
            with open(file_path, 'r') as f:
                instances = [line.strip() for line in f if line.strip()]
            print(f"从{file_path}加载了{len(instances)}个BCC实例")
            self.bcc_instances = instances
            return instances
        except FileNotFoundError:
            print(f"文件{file_path}未找到")
            return []
    
    def load_instances_from_list(self, instances: List[str]):
        """从列表加载BCC实例"""
        self.bcc_instances = instances
        print(f"加载了{len(instances)}个BCC实例")

    
    def get_monitoring_data(self, days: int = 7) -> List[Any]:
        """获取监控数据（复用原有逻辑）"""
        if not self.client:
            raise Exception("BCM客户端未初始化")
        
        beijing_tz = timezone(timedelta(hours=8))
        end_time = datetime.now(beijing_tz)
        start_time = end_time - timedelta(days=days)
        
        start_utc = start_time.astimezone(timezone.utc)
        end_utc = end_time.astimezone(timezone.utc)
        
        print(f"查询时间范围: {start_time.strftime('%Y-%m-%d %H:%M:%S')} 至 {end_time.strftime('%Y-%m-%d %H:%M:%S')} (北京时间)")
        
        # 分批处理实例，每批最多20个
        batch_size = 20
        all_responses = []
        total_batches = (len(self.bcc_instances) - 1) // batch_size + 1
        
        print(f"总实例数: {len(self.bcc_instances)}, 分为 {total_batches} 批处理")
        
        for i in range(0, len(self.bcc_instances), batch_size):
            batch_instances = self.bcc_instances[i:i+batch_size]
            dimensions = [[{"name": "InstanceId", "value": instance_id}] for instance_id in batch_instances]
            metric_names = ["CPUUsagePercent", "MemUsedPercent"]
            
            batch_num = i//batch_size + 1
            print(f"正在处理批次 {batch_num}/{total_batches}")
            
            try:
                response = self.client.get_all_data_metrics_v2(
                    self.user_id, self.scope, self.region, dimensions, metric_names, ["average"],
                    start_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    end_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    type="Instance", cycle=3600
                )
                all_responses.append(response)
                print(f"✓ 批次 {batch_num} 处理成功")
            except Exception as e:
                print(f"✗ 批次 {batch_num} 处理失败: {e}")
        
        print(f"批量查询完成，成功获取 {len(all_responses)}/{total_batches} 批次的数据")
        return all_responses

    
    def process_data(self, responses: List[Any]) -> pd.DataFrame:
        """处理监控数据"""
        data = []
        for response in responses:
            if response and hasattr(response, 'metrics'):
                for metric in response.metrics:
                    for point in metric.data_points:
                        if hasattr(point, 'average') and point.average is not None:
                            metric_type = 'cpu_usage' if metric.metric_name == 'CPUUsagePercent' else 'mem_usage'
                            timestamp = pd.to_datetime(point.timestamp)
                            if hasattr(timestamp, 'tz_localize'):
                                timestamp = timestamp.tz_localize(None)
                            data.append({
                                'instance_id': metric.resource_id,
                                'timestamp': timestamp,
                                'metric_type': metric_type,
                                'value': point.average
                            })
        df = pd.DataFrame(data)
        if not df.empty and 'timestamp' in df.columns:
            if hasattr(df['timestamp'].dtype, 'tz') and df['timestamp'].dtype.tz is not None:
                df['timestamp'] = df['timestamp'].dt.tz_localize(None)
        return df
    
    def get_instance_stats(self, df: pd.DataFrame) -> List[Dict]:
        """获取所有实例的统计数据"""
        instance_stats = []
        for instance in self.bcc_instances:
            instance_data = df[df['instance_id'] == instance]
            if not instance_data.empty:
                cpu_data = instance_data[instance_data['metric_type'] == 'cpu_usage']['value']
                mem_data = instance_data[instance_data['metric_type'] == 'mem_usage']['value']
                instance_stats.append({
                    'id': instance,
                    'avg_cpu': float(cpu_data.mean()) if not cpu_data.empty else 0.0,
                    'max_cpu': float(cpu_data.max()) if not cpu_data.empty else 0.0,
                    'min_cpu': float(cpu_data.min()) if not cpu_data.empty else 0.0,
                    'avg_mem': float(mem_data.mean()) if not mem_data.empty else 0.0,
                    'max_mem': float(mem_data.max()) if not mem_data.empty else 0.0,
                    'min_mem': float(mem_data.min()) if not mem_data.empty else 0.0
                })
        return instance_stats
    
    def detect_anomalies(self, instance_stats: List[Dict], cpu_threshold: float = 80.0, mem_threshold: float = 80.0) -> List[Dict]:
        """检测异常实例（CPU或内存使用率过高）"""
        anomalies = []
        for stat in instance_stats:
            issues = []
            if stat['max_cpu'] >= cpu_threshold:
                issues.append(f"CPU {stat['max_cpu']:.1f}%")
            if stat['max_mem'] >= mem_threshold:
                issues.append(f"内存 {stat['max_mem']:.1f}%")
            
            if issues:
                anomalies.append({
                    'id': stat['id'],
                    'issues': ', '.join(issues),
                    'avg_cpu': stat['avg_cpu'],
                    'max_cpu': stat['max_cpu'],
                    'avg_mem': stat['avg_mem'],
                    'max_mem': stat['max_mem'],
                    'severity': 'critical' if (stat['max_cpu'] >= 95 or stat['max_mem'] >= 95) else 'warning'
                })
        
        # 按严重程度和最大使用率排序
        anomalies.sort(key=lambda x: (0 if x['severity'] == 'critical' else 1, -max(x['max_cpu'], x['max_mem'])))
        return anomalies
    
    def group_by_usage(self, instance_stats: List[Dict]) -> Dict[str, List[Dict]]:
        """按使用率智能分组"""
        groups = {
            '0-20%': [],
            '20-40%': [],
            '40-60%': [],
            '60-80%': [],
            '80-100%': []
        }
        
        for stat in instance_stats:
            # 使用CPU和内存的最大值作为分组依据
            max_usage = max(stat['avg_cpu'], stat['avg_mem'])
            
            if max_usage < 20:
                groups['0-20%'].append(stat)
            elif max_usage < 40:
                groups['20-40%'].append(stat)
            elif max_usage < 60:
                groups['40-60%'].append(stat)
            elif max_usage < 80:
                groups['60-80%'].append(stat)
            else:
                groups['80-100%'].append(stat)
        
        return groups
    
    def generate_recommendations(self, instance_stats: List[Dict], anomalies: List[Dict]) -> List[Dict]:
        """生成优化建议"""
        recommendations = []
        
        # 建议扩容（高使用率实例）
        high_usage = [s for s in instance_stats if s['max_cpu'] > 80 or s['max_mem'] > 80]
        if high_usage:
            recommendations.append({
                'type': 'scale_up',
                'title': f'建议扩容：{len(high_usage)}个实例',
                'description': f'这些实例的CPU或内存使用率超过80%，建议扩容',
                'instances': [s['id'] for s in high_usage[:10]],  # 只显示前10个
                'priority': 'high'
            })
        
        # 建议降配（低使用率实例）
        low_usage = [s for s in instance_stats if s['avg_cpu'] < 20 and s['avg_mem'] < 20]
        if low_usage:
            # 估算节省成本（假设每个实例平均成本1000元/月）
            estimated_savings = len(low_usage) * 500  # 假设降配可节省50%
            recommendations.append({
                'type': 'scale_down',
                'title': f'建议降配：{len(low_usage)}个实例',
                'description': f'这些实例的平均CPU和内存使用率都低于20%，建议降低配置',
                'instances': [s['id'] for s in low_usage[:10]],
                'estimated_savings': f'¥{estimated_savings:,}/月',
                'priority': 'medium'
            })
        
        return recommendations
    
    async def generate_ai_summary(self, instance_stats: List[Dict], anomalies: List[Dict]) -> str:
        """生成执行摘要（优先使用远程API）"""
        
        # 优先使用远程ERNIE API
        if self.ernie_client:
            try:
                ai_summary = await self._generate_ai_summary_remote(instance_stats, anomalies)
                if ai_summary:
                    print("使用远程API生成摘要成功")
                    return ai_summary
            except Exception as e:
                print(f"远程API生成失败，使用本地算法: {e}")
        
        # 降级方案：本地算法
        total = len(instance_stats)
        anomaly_count = len(anomalies)
        
        avg_cpu = sum(s['avg_cpu'] for s in instance_stats) / total if total > 0 else 0
        avg_mem = sum(s['avg_mem'] for s in instance_stats) / total if total > 0 else 0
        
        if anomaly_count == 0:
            health_status = "整体健康"
        elif anomaly_count <= total * 0.1:
            health_status = "基本健康"
        else:
            health_status = "需要关注"
        
        summary = f"监控{total}个实例，{anomaly_count}个需要立即关注，平均CPU使用率{avg_cpu:.1f}%，平均内存使用率{avg_mem:.1f}%，{health_status}"
        
        return summary
    
    async def _generate_ai_summary_remote(self, instance_stats: List[Dict], anomalies: List[Dict]) -> Optional[str]:
        """使用远程ERNIE API生成摘要"""
        total = len(instance_stats)
        anomaly_count = len(anomalies)
        avg_cpu = sum(s['avg_cpu'] for s in instance_stats) / total if total > 0 else 0
        avg_mem = sum(s['avg_mem'] for s in instance_stats) / total if total > 0 else 0
        
        # 构建提示词
        prompt = f"""
请对以下BCC实例监控数据进行专业的分析和总结：

【监控概览】
- 监控实例总数: {total}个
- 异常实例数: {anomaly_count}个
- 平均CPU使用率: {avg_cpu:.1f}%
- 平均内存使用率: {avg_mem:.1f}%

【异常实例详情】
{self._format_anomalies(anomalies[:5])}

请生成一段简洁的执行摘要（100字以内），包括：
1. 整体健康状况评估
2. 主要风险点
3. 关键建议

要求：语言简洁专业，突出重点。
"""
        
        # 调用ERNIE API
        response = await self.ernie_client.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=200
        )
        
        return response
    
    def _format_anomalies(self, anomalies: List[Dict]) -> str:
        """格式化异常信息"""
        if not anomalies:
            return "无异常"
        
        lines = []
        for i, anomaly in enumerate(anomalies, 1):
            lines.append(f"{i}. 实例{anomaly['id']}: CPU {anomaly['avg_cpu']:.1f}%, 内存 {anomaly['avg_mem']:.1f}%")
        
        return "\n".join(lines)
    
    def generate_html_report_ai(self, df: pd.DataFrame) -> str:
        """生成HTML报告（倒金字塔结构）"""
        from datetime import timezone, timedelta
        import json
        
        beijing_tz = timezone(timedelta(hours=8))
        current_time = datetime.now(beijing_tz).strftime('%Y-%m-%d %H:%M:%S')
        
        # 获取统计数据
        instance_stats = self.get_instance_stats(df)
        anomalies = self.detect_anomalies(instance_stats)
        groups = self.group_by_usage(instance_stats)
        recommendations = self.generate_recommendations(instance_stats, anomalies)
        ai_summary = self.generate_ai_summary(instance_stats, anomalies)
        
        # 获取TOP10
        top10_cpu = sorted(instance_stats, key=lambda x: x['avg_cpu'], reverse=True)[:10]
        top10_mem = sorted(instance_stats, key=lambda x: x['avg_mem'], reverse=True)[:10]
        
        # 准备图表数据
        chart_data = {'timestamps': [], 'cpu_series': {}, 'mem_series': {}}
        if not df.empty:
            if not hasattr(df['timestamp'].dtype, 'tz') or df['timestamp'].dtype.tz is None:
                df['beijing_time'] = pd.to_datetime(df['timestamp']).dt.tz_localize('UTC').dt.tz_convert('Asia/Shanghai')
            else:
                df['beijing_time'] = df['timestamp'].dt.tz_convert('Asia/Shanghai')
            df_sorted = df.sort_values('beijing_time')
            timestamps = df_sorted['beijing_time'].dt.strftime('%m-%d %H:%M').unique()
            chart_data['timestamps'] = timestamps.tolist()
            
            # 只显示异常实例和TOP5的趋势
            display_instances = list(set([a['id'] for a in anomalies[:5]] + [s['id'] for s in top10_cpu[:5]]))
            
            for instance in display_instances:
                chart_data['cpu_series'][instance] = []
                chart_data['mem_series'][instance] = []
            
            for timestamp in timestamps:
                ts_data = df_sorted[df_sorted['beijing_time'].dt.strftime('%m-%d %H:%M') == timestamp]
                for instance in display_instances:
                    cpu_data = ts_data[(ts_data['instance_id'] == instance) & (ts_data['metric_type'] == 'cpu_usage')]
                    mem_data = ts_data[(ts_data['instance_id'] == instance) & (ts_data['metric_type'] == 'mem_usage')]
                    cpu_val = cpu_data['value'].iloc[0] if not cpu_data.empty else 0
                    mem_val = mem_data['value'].iloc[0] if not mem_data.empty else 0
                    chart_data['cpu_series'][instance].append(float(cpu_val))
                    chart_data['mem_series'][instance].append(float(mem_val))
        
        chart_data_json = json.dumps(chart_data)
        
        # 构建异常实例HTML
        anomaly_html = ''
        if anomalies:
            for anomaly in anomalies[:10]:  # 只显示前10个
                severity_class = 'critical' if anomaly['severity'] == 'critical' else 'warning'
                severity_icon = '!' if anomaly['severity'] == 'critical' else '!'
                anomaly_html += f'''
                <div class="anomaly-card {severity_class}">
                    <h4>{severity_icon} {anomaly['id']}</h4>
                    <p class="anomaly-issue">{anomaly['issues']}</p>
                    <p class="anomaly-detail">平均: CPU {anomaly['avg_cpu']:.1f}% | 内存 {anomaly['avg_mem']:.1f}%</p>
                </div>'''
        else:
            anomaly_html = '<div class="no-anomaly">未检测到异常实例</div>'
        
        # 构建TOP10 HTML
        top10_cpu_html = ''
        for i, stat in enumerate(top10_cpu, 1):
            top10_cpu_html += f'''
            <div class="top-item">
                <span class="rank">#{i}</span>
                <span class="instance">{stat['id']}</span>
                <span class="value">平均: {stat['avg_cpu']:.1f}% | 最高: {stat['max_cpu']:.1f}%</span>
            </div>'''
        
        top10_mem_html = ''
        for i, stat in enumerate(top10_mem, 1):
            top10_mem_html += f'''
            <div class="top-item">
                <span class="rank">#{i}</span>
                <span class="instance">{stat['id']}</span>
                <span class="value">平均: {stat['avg_mem']:.1f}% | 最高: {stat['max_mem']:.1f}%</span>
            </div>'''
        
        # 构建分组统计HTML
        group_html = ''
        for group_name, group_instances in groups.items():
            count = len(group_instances)
            group_html += f'''
            <div class="group-card">
                <h4>{group_name}</h4>
                <p class="group-count">{count}个实例</p>
                <button class="group-btn" onclick="showGroupDetail('{group_name}')">查看列表</button>
            </div>'''
        
        # 构建优化建议HTML
        rec_html = ''
        for rec in recommendations:
            priority_class = rec['priority']
            priority_icon = '*' if rec['priority'] == 'high' else '*'
            rec_html += f'''
            <div class="rec-card {priority_class}">
                <h4>{priority_icon} {rec['title']}</h4>
                <p>{rec['description']}</p>
                <p class="rec-instances">实例: {', '.join(rec['instances'][:5])}{'...' if len(rec['instances']) > 5 else ''}</p>
                {f'<p class="rec-savings">预计节省: {rec["estimated_savings"]}</p>' if 'estimated_savings' in rec else ''}
            </div>'''
        
        # 构建完整实例列表HTML
        full_list_html = '<table id="instancesTable"><thead><tr><th>实例ID</th><th>平均CPU</th><th>最高CPU</th><th>平均内存</th><th>最高内存</th></tr></thead><tbody>'
        for stat in instance_stats:
            full_list_html += f'''
            <tr>
                <td>{stat['id']}</td>
                <td>{stat['avg_cpu']:.1f}%</td>
                <td>{stat['max_cpu']:.1f}%</td>
                <td>{stat['avg_mem']:.1f}%</td>
                <td>{stat['max_mem']:.1f}%</td>
            </tr>'''
        full_list_html += '</tbody></table>'
        
        html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>BCC监控报表</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; }}
        .section {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-bottom: 20px; }}
        .ai-summary {{ background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; }}
        .ai-summary h2 {{ margin: 0 0 10px 0; }}
        .ai-summary p {{ font-size: 1.1em; margin: 0; }}
        .anomaly-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 15px; }}
        .anomaly-card {{ padding: 15px; border-radius: 8px; border-left: 4px solid; }}
        .anomaly-card.critical {{ background: #ffebee; border-left-color: #f44336; }}
        .anomaly-card.warning {{ background: #fff3e0; border-left-color: #ff9800; }}
        .anomaly-issue {{ font-weight: bold; color: #d32f2f; margin: 5px 0; }}
        .anomaly-detail {{ color: #666; font-size: 0.9em; }}
        .no-anomaly {{ text-align: center; padding: 40px; color: #4caf50; font-size: 1.2em; }}
        .top-list {{ display: grid; gap: 10px; }}
        .top-item {{ display: flex; justify-space-between; align-items: center; padding: 10px; background: #f8f9fa; border-radius: 5px; }}
        .rank {{ font-weight: bold; color: #007bff; min-width: 30px; }}
        .instance {{ flex: 1; margin: 0 10px; }}
        .value {{ font-weight: bold; color: #28a745; }}
        .group-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; }}
        .group-card {{ background: #e3f2fd; padding: 20px; border-radius: 8px; text-align: center; }}
        .group-count {{ font-size: 1.5em; font-weight: bold; color: #1976d2; margin: 10px 0; }}
        .group-btn {{ background: #1976d2; color: white; border: none; padding: 8px 16px; border-radius: 5px; cursor: pointer; }}
        .rec-grid {{ display: grid; gap: 15px; }}
        .rec-card {{ padding: 15px; border-radius: 8px; border-left: 4px solid; }}
        .rec-card.high {{ background: #ffebee; border-left-color: #f44336; }}
        .rec-card.medium {{ background: #fff3e0; border-left-color: #ff9800; }}
        .rec-instances {{ color: #666; font-size: 0.9em; margin: 5px 0; }}
        .rec-savings {{ color: #4caf50; font-weight: bold; margin: 5px 0; }}
        .chart-container {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-bottom: 20px; }}
        .collapsed {{ display: none; }}
        .toggle-btn {{ background: #1976d2; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; margin-bottom: 15px; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #1976d2; color: white; }}
        tr:hover {{ background: #f5f5f5; }}
        .search-box {{ width: 100%; padding: 10px; margin-bottom: 15px; border: 1px solid #ddd; border-radius: 5px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>BCC监控报表</h1>
        <p>智能分析 · 异常检测 · 优化建议</p>
    </div>
    
    <!-- 1. 执行摘要 -->
    <div class="ai-summary">
        <h2>执行摘要</h2>
        <p>{ai_summary}</p>
    </div>
    
    <!-- 2. 异常实例 -->
    <div class="section">
        <h2>异常实例（需要立即关注）</h2>
        <div class="anomaly-grid">
            {anomaly_html}
        </div>
    </div>
    
    <!-- 3. TOP 10 -->
    <div class="section">
        <h2>TOP 10 高使用率实例</h2>
        <h3>CPU使用率 TOP 10</h3>
        <div class="top-list">{top10_cpu_html}</div>
        <h3 style="margin-top: 20px;">内存使用率 TOP 10</h3>
        <div class="top-list">{top10_mem_html}</div>
    </div>
    
    <!-- 4. 使用率分组统计 -->
    <div class="section">
        <h2>使用率分组统计</h2>
        <div class="group-grid">
            {group_html}
        </div>
    </div>
    
    <!-- 5. 优化建议 -->
    <div class="section">
        <h2>优化建议</h2>
        <div class="rec-grid">
            {rec_html}
        </div>
    </div>
    
    <!-- 6. 整体趋势图表 -->
    <div class="chart-container">
        <h2>整体趋势（异常实例和TOP5）</h2>
        <h3>CPU使用率趋势</h3>
        <canvas id="cpuChart"></canvas>
        <h3 style="margin-top: 30px;">内存使用率趋势</h3>
        <canvas id="memChart"></canvas>
    </div>
    
    <!-- 7. 完整实例列表 -->
    <div class="section">
        <h2>完整实例列表</h2>
        <button class="toggle-btn" onclick="toggleFullList()">展开/收起完整列表</button>
        <div id="fullList" class="collapsed">
            <input type="text" class="search-box" placeholder="搜索实例ID..." onkeyup="filterInstances(this.value)">
            {full_list_html}
        </div>
    </div>
    
    <p style="text-align: center; color: #666;">更新时间: {current_time} (北京时间)</p>
    
    <script>
        const chartData = {chart_data_json};
        const colors = ['#4CAF50', '#FF5722', '#2196F3', '#FF9800', '#9C27B0', '#00BCD4', '#E91E63', '#795548'];
        
        // CPU趋势图
        new Chart(document.getElementById('cpuChart'), {{
            type: 'line',
            data: {{
                labels: chartData.timestamps,
                datasets: Object.keys(chartData.cpu_series).map((key, i) => ({{
                    label: key,
                    data: chartData.cpu_series[key],
                    borderColor: colors[i % colors.length],
                    tension: 0.4,
                    pointRadius: 3
                }}))
            }},
            options: {{
                responsive: true,
                scales: {{
                    y: {{ beginAtZero: true, max: 100, title: {{ display: true, text: 'CPU使用率 (%)' }} }},
                    x: {{ title: {{ display: true, text: '时间 (北京时间)' }} }}
                }}
            }}
        }});
        
        // 内存趋势图
        new Chart(document.getElementById('memChart'), {{
            type: 'line',
            data: {{
                labels: chartData.timestamps,
                datasets: Object.keys(chartData.mem_series).map((key, i) => ({{
                    label: key,
                    data: chartData.mem_series[key],
                    borderColor: colors[i % colors.length],
                    tension: 0.4,
                    pointRadius: 3
                }}))
            }},
            options: {{
                responsive: true,
                scales: {{
                    y: {{ beginAtZero: true, max: 100, title: {{ display: true, text: '内存使用率 (%)' }} }},
                    x: {{ title: {{ display: true, text: '时间 (北京时间)' }} }}
                }}
            }}
        }});
        
        function toggleFullList() {{
            const list = document.getElementById('fullList');
            list.classList.toggle('collapsed');
        }}
        
        function filterInstances(query) {{
            const table = document.getElementById('instancesTable');
            const rows = table.getElementsByTagName('tr');
            
            for (let i = 1; i < rows.length; i++) {{
                const instanceId = rows[i].getElementsByTagName('td')[0].textContent;
                if (instanceId.toLowerCase().includes(query.toLowerCase())) {{
                    rows[i].style.display = '';
                }} else {{
                    rows[i].style.display = 'none';
                }}
            }}
        }}
        
        function showGroupDetail(groupName) {{
            const groups = {json.dumps({name: [s['id'] for s in group_instances] for name, group_instances in groups.items()})};
            const instances = groups[groupName] || [];
            
            if (instances.length === 0) {{
                alert('该分组暂无实例');
                return;
            }}
            
            // 构建详情HTML
            let detailHtml = '<div style="max-height: 400px; overflow-y: auto;">';
            detailHtml += '<h3>' + groupName + ' 实例列表</h3>';
            detailHtml += '<ul style="list-style: none; padding: 0;">';
            instances.forEach(id => {{
                detailHtml += '<li style="padding: 5px; border-bottom: 1px solid #eee;">' + id + '</li>';
            }});
            detailHtml += '</ul></div>';
            
            // 创建模态框
            const modal = document.createElement('div');
            modal.style.cssText = 'position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 1000;';
            modal.innerHTML = '<div style="background: white; padding: 20px; border-radius: 10px; max-width: 600px; width: 90%;">' + detailHtml + '<button onclick="this.parentElement.parentElement.remove()" style="margin-top: 15px; background: #1976d2; color: white; border: none; padding: 8px 16px; border-radius: 5px; cursor: pointer;">关闭</button></div>';
            document.body.appendChild(modal);
            
            // 点击背景关闭
            modal.addEventListener('click', function(e) {{
                if (e.target === modal) {{
                    modal.remove();
                }}
            }});
        }}
    </script>
</body>
</html>"""
        
        return html_content
