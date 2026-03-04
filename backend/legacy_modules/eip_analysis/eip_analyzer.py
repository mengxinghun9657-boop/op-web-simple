#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EIP带宽监控分析器
从eip_monitor_dashboard.py和eip_web_dashboard.py迁移，保留完整逻辑
"""
import pandas as pd
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
import json


class EIPAnalyzer:
    """EIP带宽监控分析器"""
    
    def __init__(self, bcm_client=None, user_id: str = "f008db4751894afe9b851e32a2068335"):
        """
        初始化EIP分析器
        
        Args:
            bcm_client: BCM客户端实例
            user_id: 百度云用户ID
        """
        self.client = bcm_client
        self.user_id = user_id
        self.scope = "BCE_EIP"
        self.region = "cd"
        self.eip_ids = []
    
    def load_eips_from_file(self, file_path: str) -> List[str]:
        """
        从文件加载EIP列表
        
        Args:
            file_path: EIP ID列表文件路径
            
        Returns:
            EIP ID列表
        """
        try:
            with open(file_path, 'r') as f:
                eips = [line.strip() for line in f if line.strip()]
            print(f"从{file_path}加载了{len(eips)}个EIP实例")
            self.eip_ids = eips
            return eips
        except FileNotFoundError:
            print(f"文件{file_path}未找到")
            return []
    
    def load_eips_from_list(self, eips: List[str]):
        """
        从列表加载EIP
        
        Args:
            eips: EIP ID列表
        """
        self.eip_ids = eips
        print(f"加载了{len(eips)}个EIP实例")
    
    def get_eip_data(self, eip_ids: List[str], hours: int = 6) -> Any:
        """
        获取EIP监控数据
        
        Args:
            eip_ids: EIP ID列表
            hours: 查询小时数（最近N小时）
            
        Returns:
            BCM API响应
        """
        if not self.client:
            raise Exception("BCM客户端未初始化")
        
        # 北京时间最近N小时
        beijing_tz = timezone(timedelta(hours=8))
        end_time = datetime.now(beijing_tz)
        start_time = end_time - timedelta(hours=hours)
        
        # 转换为UTC时间
        start_utc = start_time.astimezone(timezone.utc)
        end_utc = end_time.astimezone(timezone.utc)
        
        print(f"查询时间范围: {start_time.strftime('%Y-%m-%d %H:%M:%S')} 至 {end_time.strftime('%Y-%m-%d %H:%M:%S')} (北京时间)")
        
        dimensions = [[{"name": "InstanceId", "value": eip_id}] for eip_id in eip_ids]
        
        response = self.client.get_all_data_metrics_v2(
            self.user_id, self.scope, self.region, dimensions,
            ["WebInBitsPerSecond", "WebOutBitsPerSecond", "DropsInPkgCounts", "DropsOutPkgCounts"],
            ["average"],
            start_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
            end_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
            type="Instance", cycle=30  # 30秒间隔，与原项目保持一致
        )
        
        return response
    
    def process_data(self, response: Any, eip_ids: List[str]) -> pd.DataFrame:
        """
        处理EIP监控数据
        
        Args:
            response: BCM API响应
            eip_ids: EIP ID列表
            
        Returns:
            处理后的DataFrame
        """
        data = []
        
        if response and hasattr(response, 'metrics') and response.metrics:
            for metric_data in response.metrics:
                eip_id = metric_data.resource_id
                metric_name = metric_data.metric_name
                
                for point in metric_data.data_points:
                    if hasattr(point, 'average') and point.average is not None:
                        # 带宽数据转换为Mbps，丢包数保持原值
                        value = point.average / 1024 / 1024 if 'BitsPerSecond' in metric_name else point.average
                        
                        # 解析时间戳并移除时区信息
                        timestamp = pd.to_datetime(point.timestamp)
                        if hasattr(timestamp, 'tz_localize'):
                            timestamp = timestamp.tz_localize(None)
                        
                        data.append({
                            'eip_id': eip_id,
                            'metric': metric_name,
                            'timestamp': timestamp,
                            'value': value
                        })
        
        df = pd.DataFrame(data)
        
        # 确保timestamp列无时区信息
        if not df.empty and 'timestamp' in df.columns:
            if hasattr(df['timestamp'].dtype, 'tz') and df['timestamp'].dtype.tz is not None:
                df['timestamp'] = df['timestamp'].dt.tz_localize(None)
        
        print(f"处理得到 {len(data)} 条数据点")
        return df
    
    def aggregate_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        按时间戳汇聚所有EIP的流量
        
        Args:
            df: 监控数据DataFrame
            
        Returns:
            汇聚后的DataFrame
        """
        agg_data = df.groupby(['timestamp', 'metric'])['value'].sum().reset_index()
        return agg_data
    
    def get_eip_stats(self, df: pd.DataFrame) -> List[Dict]:
        """
        获取各EIP统计数据
        
        Args:
            df: 监控数据DataFrame
            
        Returns:
            EIP统计列表
        """
        eip_stats = []
        for eip_id in self.eip_ids:
            eip_data = df[df['eip_id'] == eip_id]
            if not eip_data.empty:
                in_data = eip_data[eip_data['metric'] == 'WebInBitsPerSecond']['value']
                out_data = eip_data[eip_data['metric'] == 'WebOutBitsPerSecond']['value']
                in_drops = eip_data[eip_data['metric'] == 'DropsInPkgCounts']['value']
                out_drops = eip_data[eip_data['metric'] == 'DropsOutPkgCounts']['value']
                
                eip_stats.append({
                    'id': eip_id,
                    'in_total': float(in_data.sum()) if not in_data.empty else 0.0,
                    'out_total': float(out_data.sum()) if not out_data.empty else 0.0,
                    'in_avg': float(in_data.mean()) if not in_data.empty else 0.0,
                    'out_avg': float(out_data.mean()) if not out_data.empty else 0.0,
                    'in_max': float(in_data.max()) if not in_data.empty else 0.0,
                    'out_max': float(out_data.max()) if not out_data.empty else 0.0,
                    'in_drops_total': float(in_drops.sum()) if not in_drops.empty else 0.0,
                    'out_drops_total': float(out_drops.sum()) if not out_drops.empty else 0.0
                })
        
        return eip_stats
    
    def generate_html_report(self, df: pd.DataFrame, agg_df: pd.DataFrame, eip_ids: List[str]) -> str:
        """
        生成EIP带宽监控HTML报告（完整保留原版格式）
        
        Args:
            df: 监控数据DataFrame
            agg_df: 汇聚数据DataFrame
            eip_ids: EIP ID列表
            
        Returns:
            HTML内容
        """
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 单个EIP统计
        eip_stats = self.get_eip_stats(df)
        
        # 汇聚统计
        agg_in_avg = agg_df[agg_df['metric'] == 'WebInBitsPerSecond']['value'].mean() if not agg_df[agg_df['metric'] == 'WebInBitsPerSecond'].empty else 0
        agg_out_avg = agg_df[agg_df['metric'] == 'WebOutBitsPerSecond']['value'].mean() if not agg_df[agg_df['metric'] == 'WebOutBitsPerSecond'].empty else 0
        
        # 时间序列数据
        chart_data = {
            'timestamps': [],
            'series': {}
        }
        
        for eip_id in eip_ids:
            chart_data['series'][f'{eip_id}_in'] = []
            chart_data['series'][f'{eip_id}_out'] = []
            chart_data['series'][f'{eip_id}_drops_in'] = []
            chart_data['series'][f'{eip_id}_drops_out'] = []
        
        # 按时间排序并准备图表数据
        df_sorted = df.sort_values('timestamp')
        timestamps = df_sorted['timestamp'].dt.strftime('%H:%M').unique()
        chart_data['timestamps'] = timestamps.tolist()
        
        for timestamp in timestamps:
            ts_data = df_sorted[df_sorted['timestamp'].dt.strftime('%H:%M') == timestamp]
            for eip_id in eip_ids:
                eip_ts_data = ts_data[ts_data['eip_id'] == eip_id]
                in_val = eip_ts_data[eip_ts_data['metric'] == 'WebInBitsPerSecond']['value'].iloc[0] if not eip_ts_data[eip_ts_data['metric'] == 'WebInBitsPerSecond'].empty else 0
                out_val = eip_ts_data[eip_ts_data['metric'] == 'WebOutBitsPerSecond']['value'].iloc[0] if not eip_ts_data[eip_ts_data['metric'] == 'WebOutBitsPerSecond'].empty else 0
                drops_in_val = eip_ts_data[eip_ts_data['metric'] == 'DropsInPkgCounts']['value'].iloc[0] if not eip_ts_data[eip_ts_data['metric'] == 'DropsInPkgCounts'].empty else 0
                drops_out_val = eip_ts_data[eip_ts_data['metric'] == 'DropsOutPkgCounts']['value'].iloc[0] if not eip_ts_data[eip_ts_data['metric'] == 'DropsOutPkgCounts'].empty else 0
                chart_data['series'][f'{eip_id}_in'].append(float(in_val))
                chart_data['series'][f'{eip_id}_out'].append(float(out_val))
                chart_data['series'][f'{eip_id}_drops_in'].append(float(drops_in_val))
                chart_data['series'][f'{eip_id}_drops_out'].append(float(drops_out_val))
        
        # 构建EIP统计卡片HTML
        eip_cards_html = ''
        for stat in eip_stats:
            eip_cards_html += f"""
        <div class="stat-card">
            <div class="stat-title">🖥️ {stat['id']}</div>
            <table>
                <tr><th>指标</th><th>入向</th><th>出向</th></tr>
                <tr><td>平均带宽</td><td class="in-traffic">{stat['in_avg']:.2f} Mbps</td><td class="out-traffic">{stat['out_avg']:.2f} Mbps</td></tr>
                <tr><td>峰值带宽</td><td class="in-traffic">{stat['in_max']:.2f} Mbps</td><td class="out-traffic">{stat['out_max']:.2f} Mbps</td></tr>
                <tr><td>丢包数</td><td style="color: #FF9800;">{stat['in_drops_total']:.0f} 个</td><td style="color: #FF9800;">{stat['out_drops_total']:.0f} 个</td></tr>
            </table>
        </div>"""
        
        chart_data_json = json.dumps(chart_data)
        
        html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EIP流量监控报表</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 30px; }}
        .stat-card {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .stat-title {{ font-size: 18px; font-weight: bold; color: #333; margin-bottom: 15px; }}
        .stat-value {{ font-size: 24px; font-weight: bold; margin: 5px 0; }}
        .in-traffic {{ color: #4CAF50; }}
        .out-traffic {{ color: #FF5722; }}
        .chart-container {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-bottom: 20px; }}
        .summary-card {{ background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); color: white; padding: 20px; border-radius: 10px; }}
        .update-time {{ text-align: center; color: #666; margin-top: 20px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
        th, td {{ padding: 10px; text-align: right; border-bottom: 1px solid #eee; }}
        th {{ background-color: #f8f9fa; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🌐 EIP流量监控报表</h1>
        <p>实时监控多个EIP实例的网络流量数据</p>
    </div>

    <div class="stats-grid">
        <div class="stat-card summary-card">
            <div class="stat-title">📊 汇聚带宽统计</div>
            <div class="stat-value in-traffic">入向平均: {agg_in_avg:.2f} Mbps</div>
            <div class="stat-value out-traffic">出向平均: {agg_out_avg:.2f} Mbps</div>
            <div class="stat-value">总平均: {agg_in_avg + agg_out_avg:.2f} Mbps</div>
        </div>
{eip_cards_html}
    </div>

    <div class="chart-container">
        <h3>📈 带宽趋势图</h3>
        <canvas id="trafficChart" width="400" height="200"></canvas>
    </div>

    <div class="chart-container">
        <h3>📉 丢包数趋势图</h3>
        <canvas id="dropsChart" width="400" height="200"></canvas>
    </div>

    <div class="update-time">
        📅 更新时间: {current_time} | 监控周期: 最近6小时
    </div>

    <script>
        const trafficCtx = document.getElementById('trafficChart').getContext('2d');
        const dropsCtx = document.getElementById('dropsChart').getContext('2d');
        const chartData = {chart_data_json};
        
        // 流量图表
        const trafficDatasets = [];
        const dropsDatasets = [];
        const colors = ['#4CAF50', '#FF5722', '#2196F3', '#FF9800', '#9C27B0', '#00BCD4'];
        let colorIndex = 0;
        
        for (const [key, values] of Object.entries(chartData.series)) {{
            if (key.includes('drops')) {{
                const isInbound = key.includes('_drops_in');
                const eipId = key.replace('_drops_in', '').replace('_drops_out', '');
                const label = `${{eipId}} ${{isInbound ? '入向丢包' : '出向丢包'}}`;
                
                dropsDatasets.push({{
                    label: label,
                    data: values,
                    borderColor: colors[colorIndex % colors.length],
                    backgroundColor: colors[colorIndex % colors.length] + '20',
                    tension: 0.4,
                    fill: false
                }});
            }} else {{
                const isInbound = key.includes('_in');
                const eipId = key.replace('_in', '').replace('_out', '');
                const label = `${{eipId}} ${{isInbound ? '入向流量' : '出向流量'}}`;
                
                trafficDatasets.push({{
                    label: label,
                    data: values,
                    borderColor: colors[colorIndex % colors.length],
                    backgroundColor: colors[colorIndex % colors.length] + '20',
                    tension: 0.4,
                    fill: false
                }});
            }}
            colorIndex++;
        }}
        
        // 创建流量图表
        new Chart(trafficCtx, {{
            type: 'line',
            data: {{
                labels: chartData.timestamps,
                datasets: trafficDatasets
            }},
            options: {{
                responsive: true,
                plugins: {{
                    title: {{
                        display: true,
                        text: 'EIP流量时间序列'
                    }},
                    legend: {{
                        position: 'top'
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        title: {{
                            display: true,
                            text: '流量 (Mbps)'
                        }}
                    }},
                    x: {{
                        title: {{
                            display: true,
                            text: '时间'
                        }}
                    }}
                }}
            }}
        }});
        
        // 创建丢包图表
        new Chart(dropsCtx, {{
            type: 'line',
            data: {{
                labels: chartData.timestamps,
                datasets: dropsDatasets
            }},
            options: {{
                responsive: true,
                plugins: {{
                    title: {{
                        display: true,
                        text: 'EIP丢包数时间序列'
                    }},
                    legend: {{
                        position: 'top'
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        title: {{
                            display: true,
                            text: '丢包数 (个)'
                        }}
                    }},
                    x: {{
                        title: {{
                            display: true,
                            text: '时间'
                        }}
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>"""
        return html_content
    
    def analyze(self, eip_ids: Optional[List[str]] = None, hours: int = 6) -> Dict[str, Any]:
        """
        执行完整的EIP带宽分析
        
        Args:
            eip_ids: EIP ID列表（可选）
            hours: 查询小时数
            
        Returns:
            分析结果字典
        """
        if eip_ids:
            self.load_eips_from_list(eip_ids)
        
        if not self.eip_ids:
            raise Exception("未加载任何EIP实例")
        
        # 获取监控数据
        print("开始获取EIP监控数据...")
        response = self.get_eip_data(self.eip_ids, hours)
        
        # 处理数据
        print("处理监控数据...")
        df = self.process_data(response, self.eip_ids)
        
        if df.empty:
            return {
                'success': False,
                'message': '未获取到任何监控数据',
                'eip_count': len(self.eip_ids)
            }
        
        # 汇聚数据
        agg_df = self.aggregate_data(df)
        
        # 生成统计数据
        eip_stats = self.get_eip_stats(df)
        
        agg_in_avg = float(agg_df[agg_df['metric'] == 'WebInBitsPerSecond']['value'].mean()) if not agg_df[agg_df['metric'] == 'WebInBitsPerSecond'].empty else 0.0
        agg_out_avg = float(agg_df[agg_df['metric'] == 'WebOutBitsPerSecond']['value'].mean()) if not agg_df[agg_df['metric'] == 'WebOutBitsPerSecond'].empty else 0.0
        
        return {
            'success': True,
            'eip_count': len(self.eip_ids),
            'data_points': len(df),
            'eip_stats': eip_stats,
            'aggregate': {
                'in_avg': agg_in_avg,
                'out_avg': agg_out_avg,
                'total_avg': agg_in_avg + agg_out_avg
            },
            'raw_data': {
                'df': df.to_dict('records'),
                'agg_df': agg_df.to_dict('records')
            },
            'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
