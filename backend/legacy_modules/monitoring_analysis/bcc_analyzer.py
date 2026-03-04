#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BCC监控分析器
从bcc_monitor_dashboard.py迁移，保留完整逻辑
"""
import pandas as pd
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from pathlib import Path


class BCCAnalyzer:
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
    
    def load_instances_from_file(self, file_path: str) -> List[str]:
        """
        从文件加载BCC实例列表
        
        Args:
            file_path: 实例ID列表文件路径
            
        Returns:
            实例ID列表
        """
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
        """
        从列表加载BCC实例
        
        Args:
            instances: 实例ID列表
        """
        self.bcc_instances = instances
        print(f"加载了{len(instances)}个BCC实例")
    
    def get_monitoring_data(self, days: int = 7) -> List[Any]:
        """
        获取监控数据
        
        Args:
            days: 查询天数
            
        Returns:
            API响应列表
        """
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
                import traceback
                traceback.print_exc()
        
        print(f"批量查询完成，成功获取 {len(all_responses)}/{total_batches} 批次的数据")
        return all_responses
    
    def process_data(self, responses: List[Any]) -> pd.DataFrame:
        """
        处理监控数据
        
        Args:
            responses: API响应列表
            
        Returns:
            处理后的DataFrame
        """
        data = []
        for response in responses:
            if response and hasattr(response, 'metrics'):
                for metric in response.metrics:
                    for point in metric.data_points:
                        if hasattr(point, 'average') and point.average is not None:
                            metric_type = 'cpu_usage' if metric.metric_name == 'CPUUsagePercent' else 'mem_usage'
                            # 解析时间戳并移除时区信息，避免Excel序列化错误
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
        # 确保timestamp列无时区信息
        if not df.empty and 'timestamp' in df.columns:
            if hasattr(df['timestamp'].dtype, 'tz') and df['timestamp'].dtype.tz is not None:
                df['timestamp'] = df['timestamp'].dt.tz_localize(None)
        return df
    
    def get_summary_stats(self, df: pd.DataFrame) -> Dict[str, float]:
        """
        获取汇总统计数据
        
        Args:
            df: 监控数据DataFrame
            
        Returns:
            统计数据字典
        """
        cpu_df = df[df['metric_type'] == 'cpu_usage']
        mem_df = df[df['metric_type'] == 'mem_usage']
        
        return {
            'total_avg_cpu': float(cpu_df['value'].mean()) if not cpu_df.empty else 0.0,
            'total_max_cpu': float(cpu_df['value'].max()) if not cpu_df.empty else 0.0,
            'total_avg_mem': float(mem_df['value'].mean()) if not mem_df.empty else 0.0,
            'total_max_mem': float(mem_df['value'].max()) if not mem_df.empty else 0.0
        }
    
    def get_top30_stats(self, df: pd.DataFrame) -> tuple:
        """
        获取TOP30统计数据
        
        Args:
            df: 监控数据DataFrame
            
        Returns:
            (cpu_top30, mem_top30) 元组
        """
        # 按实例统计平均值
        instance_stats = []
        for instance in self.bcc_instances:
            instance_data = df[df['instance_id'] == instance]
            if not instance_data.empty:
                cpu_data = instance_data[instance_data['metric_type'] == 'cpu_usage']['value']
                mem_data = instance_data[instance_data['metric_type'] == 'mem_usage']['value']
                instance_stats.append({
                    'instance_id': instance,
                    'avg_cpu': float(cpu_data.mean()) if not cpu_data.empty else 0.0,
                    'max_cpu': float(cpu_data.max()) if not cpu_data.empty else 0.0,
                    'avg_mem': float(mem_data.mean()) if not mem_data.empty else 0.0,
                    'max_mem': float(mem_data.max()) if not mem_data.empty else 0.0
                })
        
        # 排序获取TOP30
        cpu_top30 = sorted(instance_stats, key=lambda x: x['avg_cpu'], reverse=True)[:30]
        mem_top30 = sorted(instance_stats, key=lambda x: x['avg_mem'], reverse=True)[:30]
        
        return cpu_top30, mem_top30
    
    def get_instance_stats(self, df: pd.DataFrame) -> List[Dict]:
        """
        获取所有实例的统计数据
        
        Args:
            df: 监控数据DataFrame
            
        Returns:
            实例统计列表
        """
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
    
    def export_to_excel(self, df: pd.DataFrame, filename: str = 'bcc_monitor_report.xlsx') -> str:
        """
        导出Excel报告
        
        Args:
            df: 监控数据DataFrame
            filename: 输出文件名
            
        Returns:
            生成的文件路径
        """
        summary_stats = self.get_summary_stats(df)
        cpu_top30, mem_top30 = self.get_top30_stats(df)
        
        # 处理时间列，移除时区信息
        df_export = df.copy()
        if 'timestamp' in df_export.columns:
            # 完全移除时区信息
            if hasattr(df_export['timestamp'].dtype, 'tz') and df_export['timestamp'].dtype.tz is not None:
                df_export['timestamp'] = df_export['timestamp'].dt.tz_localize(None)
            elif df_export['timestamp'].dtype == 'object':
                df_export['timestamp'] = pd.to_datetime(df_export['timestamp'], utc=False)
        
        # 如果有beijing_time列，也要移除时区
        if 'beijing_time' in df_export.columns:
            if hasattr(df_export['beijing_time'].dtype, 'tz') and df_export['beijing_time'].dtype.tz is not None:
                df_export['beijing_time'] = df_export['beijing_time'].dt.tz_localize(None)
            df_export = df_export.drop('beijing_time', axis=1)  # 删除辅助列
        
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            # 汇总统计
            summary_df = pd.DataFrame([summary_stats])
            summary_df.to_excel(writer, sheet_name='汇总统计', index=False)
            
            # CPU TOP30
            cpu_df = pd.DataFrame(cpu_top30)
            cpu_df.to_excel(writer, sheet_name='CPU_TOP30', index=False)
            
            # 内存 TOP30
            mem_df = pd.DataFrame(mem_top30)
            mem_df.to_excel(writer, sheet_name='内存_TOP30', index=False)
            
            # 原始数据
            df_export.to_excel(writer, sheet_name='原始数据', index=False)
        
        return filename
    
    def generate_html_report(self, df: pd.DataFrame) -> str:
        """
        生成BCC监控HTML报告（完整保留原版格式）
        
        Args:
            df: 监控数据DataFrame
            
        Returns:
            HTML内容
        """
        import json
        from datetime import timezone, timedelta
        
        beijing_tz = timezone(timedelta(hours=8))
        current_time = datetime.now(beijing_tz).strftime('%Y-%m-%d %H:%M:%S')
        
        # 获取统计数据
        summary_stats = self.get_summary_stats(df)
        cpu_top30, mem_top30 = self.get_top30_stats(df)
        instance_stats = self.get_instance_stats(df)
        
        # 图表数据
        chart_data = {'timestamps': [], 'cpu_series': {}, 'mem_series': {}}
        if not df.empty:
            # 确保timestamp列有时区信息才能转换
            if not hasattr(df['timestamp'].dtype, 'tz') or df['timestamp'].dtype.tz is None:
                # 如果没有时区，先添加UTC时区，然后转换到北京时间
                df['beijing_time'] = pd.to_datetime(df['timestamp']).dt.tz_localize('UTC').dt.tz_convert('Asia/Shanghai')
            else:
                df['beijing_time'] = df['timestamp'].dt.tz_convert('Asia/Shanghai')
            df_sorted = df.sort_values('beijing_time')
            timestamps = df_sorted['beijing_time'].dt.strftime('%m-%d %H:%M').unique()
            chart_data['timestamps'] = timestamps.tolist()
            
            for instance in self.bcc_instances:
                chart_data['cpu_series'][instance] = []
                chart_data['mem_series'][instance] = []
            
            for timestamp in timestamps:
                ts_data = df_sorted[df_sorted['beijing_time'].dt.strftime('%m-%d %H:%M') == timestamp]
                for instance in self.bcc_instances:
                    cpu_data = ts_data[(ts_data['instance_id'] == instance) & (ts_data['metric_type'] == 'cpu_usage')]
                    mem_data = ts_data[(ts_data['instance_id'] == instance) & (ts_data['metric_type'] == 'mem_usage')]
                    cpu_val = cpu_data['value'].iloc[0] if not cpu_data.empty else 0
                    mem_val = mem_data['value'].iloc[0] if not mem_data.empty else 0
                    chart_data['cpu_series'][instance].append(float(cpu_val))
                    chart_data['mem_series'][instance].append(float(mem_val))
        
        # 构建CPU TOP30列表
        cpu_top10_html = ''
        for i, item in enumerate(cpu_top30[:10], 1):
            cpu_top10_html += f"""
            <div class="top-item">
                <span class="rank">#{i}</span>
                <span class="instance">{item['instance_id']}</span>
                <span class="value">{item['avg_cpu']:.1f}%</span>
            </div>"""
        
        # 构建内存TOP30列表
        mem_top10_html = ''
        for i, item in enumerate(mem_top30[:10], 1):
            mem_top10_html += f"""
            <div class="top-item">
                <span class="rank">#{i}</span>
                <span class="instance">{item['instance_id']}</span>
                <span class="value">{item['avg_mem']:.1f}%</span>
            </div>"""
        
        # 构建实例卡片
        instance_cards_html = ''
        for stat in instance_stats:
            card_style = "high-cpu" if stat['max_cpu'] > 80 or stat['max_mem'] > 80 else ""
            warning_icon = "🔥" if stat['max_cpu'] > 80 or stat['max_mem'] > 80 else ""
            instance_cards_html += f"""
        <div class="stat-card {card_style}">
            <h4>🔧 {stat['id']} {warning_icon}</h4>
            <p class="cpu-value">CPU - 平均: {stat['avg_cpu']:.1f}% | 最高: {stat['max_cpu']:.1f}%</p>
            <p class="cpu-value">内存 - 平均: {stat['avg_mem']:.1f}% | 最高: {stat['max_mem']:.1f}%</p>
        </div>"""
        
        chart_data_json = json.dumps(chart_data)
        
        html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>BCC CPU监控报表</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; margin-bottom: 30px; }}
        .stat-card {{ background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        .chart-container {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-bottom: 20px; }}
        .summary-card {{ background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); color: white; }}
        .high-cpu {{ background: #ffebee; border-left: 4px solid #f44336; }}
        .cpu-value {{ color: #4CAF50; font-weight: bold; }}
        .top-list {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 10px; }}
        .top-item {{ display: flex; justify-content: space-between; align-items: center; padding: 10px; background: #f8f9fa; border-radius: 5px; }}
        .rank {{ font-weight: bold; color: #007bff; min-width: 30px; }}
        .instance {{ flex: 1; margin: 0 10px; }}
        .value {{ font-weight: bold; color: #28a745; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🖥️ BCC监控报表</h1>
        <p>近一周CPU和内存使用率统计 - 监控{len(self.bcc_instances)}台服务器</p>
    </div>
    
    <div class="stat-card summary-card" style="margin-bottom: 20px;">
        <h3>📊 汇总统计</h3>
        <p>平均CPU使用率: {summary_stats['total_avg_cpu']:.1f}% | 平均内存使用率: {summary_stats['total_avg_mem']:.1f}%</p>
        <p>最高CPU使用率: {summary_stats['total_max_cpu']:.1f}% | 最高内存使用率: {summary_stats['total_max_mem']:.1f}%</p>
        <p>监控实例数: {len(self.bcc_instances)}台</p>
    </div>
    
    <div class="chart-container">
        <h3>🔥 CPU使用率 TOP30</h3>
        <div class="top-list">{cpu_top10_html}
        </div>
    </div>
    
    <div class="chart-container">
        <h3>💾 内存使用率 TOP30</h3>
        <div class="top-list">{mem_top10_html}
        </div>
    </div>
    
    <div class="stats-grid">{instance_cards_html}
    </div>
    
    <div class="chart-container">
        <h3>📈 CPU使用率趋势</h3>
        <canvas id="cpuChart"></canvas>
    </div>
    
    <div class="chart-container">
        <h3>📊 内存使用率趋势</h3>
        <canvas id="memChart"></canvas>
    </div>
    
    <p style="text-align: center; color: #666;">📅 更新时间: {current_time} (北京时间)</p>
    
    <script>
        const chartData = {chart_data_json};
        const colors = ['#4CAF50', '#FF5722', '#2196F3', '#FF9800', '#9C27B0', '#00BCD4'];
        
        new Chart(document.getElementById('cpuChart'), {{
            type: 'line',
            data: {{
                labels: chartData.timestamps,
                datasets: Object.keys(chartData.cpu_series).map((key, i) => ({{
                    label: key,
                    data: chartData.cpu_series[key],
                    borderColor: colors[i % colors.length],
                    tension: 0.4
                }}))
            }},
            options: {{
                responsive: true,
                scales: {{
                    y: {{
                        beginAtZero: true,
                        max: 100,
                        title: {{ display: true, text: 'CPU使用率 (%)' }}
                    }},
                    x: {{
                        title: {{ display: true, text: '时间 (北京时间)' }}
                    }}
                }}
            }}
        }});
        
        new Chart(document.getElementById('memChart'), {{
            type: 'line',
            data: {{
                labels: chartData.timestamps,
                datasets: Object.keys(chartData.mem_series).map((key, i) => ({{
                    label: key,
                    data: chartData.mem_series[key],
                    borderColor: colors[i % colors.length],
                    tension: 0.4
                }}))
            }},
            options: {{
                responsive: true,
                scales: {{
                    y: {{
                        beginAtZero: true,
                        max: 100,
                        title: {{ display: true, text: '内存使用率 (%)' }}
                    }},
                    x: {{
                        title: {{ display: true, text: '时间 (北京时间)' }}
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>"""
        return html_content
    
    def analyze(self, instance_ids: Optional[List[str]] = None, days: int = 7) -> Dict[str, Any]:
        """
        执行完整的BCC监控分析
        
        Args:
            instance_ids: 实例ID列表（可选）
            days: 查询天数
            
        Returns:
            分析结果字典
        """
        if instance_ids:
            self.load_instances_from_list(instance_ids)
        
        if not self.bcc_instances:
            raise Exception("未加载任何BCC实例")
        
        # 获取监控数据
        print("开始获取监控数据...")
        responses = self.get_monitoring_data(days)
        
        # 处理数据
        print("处理监控数据...")
        df = self.process_data(responses)
        
        if df.empty:
            return {
                'success': False,
                'message': '未获取到任何监控数据',
                'instance_count': len(self.bcc_instances)
            }
        
        # 生成统计数据
        summary_stats = self.get_summary_stats(df)
        cpu_top30, mem_top30 = self.get_top30_stats(df)
        instance_stats = self.get_instance_stats(df)
        
        return {
            'success': True,
            'instance_count': len(self.bcc_instances),
            'data_points': len(df),
            'summary': summary_stats,
            'cpu_top30': cpu_top30,
            'mem_top30': mem_top30,
            'instance_stats': instance_stats,
            'raw_data': df.to_dict('records'),
            'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
