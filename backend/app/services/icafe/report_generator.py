#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
HTML 报告生成器
从 icafe/html_report_generator_fixed.py 迁移
支持 AI 解读功能
"""

import json
import os
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
from loguru import logger


class ReportGenerator:
    """HTML 报告生成器"""
    
    def __init__(self, enable_ai_interpretation: bool = True, db=None):
        """
        初始化报告生成器

        Args:
            enable_ai_interpretation: 是否启用 AI 解读功能
            db: SQLAlchemy Session，用于读取数据库中的 AI 配置
        """
        self.enable_ai_interpretation = enable_ai_interpretation
        self.ai_interpreter = None

        if enable_ai_interpretation:
            try:
                from app.services.ai.report_ai_interpreter import get_report_ai_interpreter
                self.ai_interpreter = get_report_ai_interpreter(db=db)
                logger.info("✅ 报告生成器已启用 AI 解读功能")
            except Exception as e:
                logger.warning(f"⚠️ 无法加载 AI 解读服务: {e}，将跳过 AI 解读")
                self.enable_ai_interpretation = False
    
    def _safe_get(self, data: Dict, key: str, default=None):
        """安全获取字典值"""
        if not data:
            return default
        result = data.get(key, default)
        return result if result is not None else default
    
    def _safe_get_nested(self, data: Dict, key1: str, key2: str, default="0"):
        """安全获取嵌套字典值"""
        if not data:
            return default
        level1 = data.get(key1, {})
        if not level1:
            return default
        result = level1.get(key2, default)
        return result if result is not None else default
    
    def _generate_table_html(self, data: List[Dict], columns: List[str], has_links: bool = True) -> str:
        """生成表格 HTML"""
        if not data:
            return '<div class="no-data">无异常项</div>'
        
        html = '<div class="table-wrapper"><table><thead><tr>'
        for col in columns:
            html += f'<th>{col}</th>'
        html += '</tr></thead><tbody>'
        
        for item in data:
            html += '<tr>'
            for col in columns:
                value = item.get(col, '')
                if col == '标题' and has_links and '编号' in item:
                    number = item.get('编号', '')
                    html += f'<td><a href="https://console.cloud.baidu-int.com/devops/icafe/issue/{number}/show?source=copy-shortcut" target="_blank">{value}</a></td>'
                else:
                    html += f'<td>{value}</td>'
            html += '</tr>'
        
        html += '</tbody></table></div>'
        return html

    def _generate_product_detail_html(self, products: List[Dict]) -> str:
        """生成产品详细统计 HTML"""
        html = '<div class="product-details">'
        
        for i, product in enumerate(products):
            product_id = f"product_{i}"
            html += f'''
            <div class="product-item">
                <div class="product-header" onclick="toggleProductDetail('{product_id}')">
                    <h4>{product['产品名称']}</h4>
                    <div class="product-stats">
                        <span>记录数量: <strong>{product['记录数量']}</strong></span>
                        <span>占比: <strong>{product['占比']}</strong></span>
                    </div>
                </div>
                <div class="product-cards" id="{product_id}" style="display: none;">
                    <table>
                        <thead><tr><th>编号</th><th>标题</th><th>创建人</th></tr></thead>
                        <tbody>
            '''
            
            for card in product.get('相关卡片', []):
                html += f'''
                <tr>
                    <td>{card['编号']}</td>
                    <td><a href="https://console.cloud.baidu-int.com/devops/icafe/issue/{card['编号']}/show?source=copy-shortcut" target="_blank">{card['标题']}</a></td>
                    <td>{card['创建人']}</td>
                </tr>
                '''
            
            html += '</tbody></table></div></div>'
        
        html += '</div>'
        return html
    
    def _generate_chart_scripts(self, results: Dict) -> List[str]:
        """生成图表脚本（月/日自适应趋势）"""
        chart_scripts = []

        # 卡片处理量趋势（月粒度或日粒度，由 analyzer 根据数据跨度决定）
        if results.get('monthly_trends'):
            monthly_data = self._safe_get(results, 'monthly_trends', [])
            months = [item[0] for item in monthly_data]
            totals = [item[1] for item in monthly_data]
            finished_counts = [item[2] if len(item) > 2 else 0 for item in monthly_data]
            closure_rates = [item[3] if len(item) > 3 else 0 for item in monthly_data]

            # 推断粒度标题：日粒度的标签格式为 "MM/DD"
            is_daily = months and '/' in str(months[0])
            chart_title = '每日卡片处理量与闭环率趋势' if is_daily else '每月卡片处理量与闭环率趋势'

            chart_scripts.append(f"""
            const monthlyCtx = document.getElementById('monthlyChart').getContext('2d');
            new Chart(monthlyCtx, {{
                type: 'bar',
                data: {{
                    labels: {json.dumps(months)},
                    datasets: [
                        {{
                            label: '总卡片数',
                            data: {json.dumps(totals)},
                            backgroundColor: 'rgba(25, 118, 210, 0.6)',
                            yAxisID: 'y'
                        }},
                        {{
                            label: '已完成数',
                            data: {json.dumps(finished_counts)},
                            backgroundColor: 'rgba(56, 142, 60, 0.6)',
                            yAxisID: 'y'
                        }},
                        {{
                            type: 'line',
                            label: '闭环率(%)',
                            data: {json.dumps(closure_rates)},
                            borderColor: '#F57C00',
                            backgroundColor: 'transparent',
                            tension: 0.4,
                            pointRadius: 5,
                            yAxisID: 'y1'
                        }}
                    ]
                }},
                options: {{
                    responsive: true,
                    interaction: {{ mode: 'index', intersect: false }},
                    plugins: {{ title: {{ display: true, text: '{chart_title}' }} }},
                    scales: {{
                        y: {{ type: 'linear', position: 'left', title: {{ display: true, text: '卡片数' }} }},
                        y1: {{ type: 'linear', position: 'right', min: 0, max: 100, title: {{ display: true, text: '闭环率(%)' }}, grid: {{ drawOnChartArea: false }} }}
                    }}
                }}
            }});
            """)

        return chart_scripts

    def _generate_more_chart_scripts(self, results: Dict) -> List[str]:
        """生成更多图表脚本"""
        chart_scripts = []

        # 处理卡片趋势（周粒度或日粒度，由 analyzer 根据数据跨度决定）
        if results.get('weekly_trends'):
            weekly_data = self._safe_get(results, 'weekly_trends', [])
            weeks = [item.get('周期标签') or item['周期'] for item in weekly_data]
            follow_counts = [item['问题跟进数'] for item in weekly_data]
            close_counts = [item['闭环个数'] for item in weekly_data]
            resolution_rates = [item['问题解决率'] for item in weekly_data]

            import statistics
            follow_median = statistics.median(follow_counts) if follow_counts else 0
            close_median = statistics.median(close_counts) if close_counts else 0

            # 推断粒度标题：日粒度标签格式为 "MM/DD"（无 "-" 分隔符的区间）
            is_daily = weeks and '-' not in str(weeks[0])
            weekly_chart_title = '每日处理卡片趋势（含中位数参考线）' if is_daily else '每周处理卡片趋势（含中位数参考线）'

            chart_scripts.append(f"""
            const weeklyCtx = document.getElementById('weeklyChart').getContext('2d');
            new Chart(weeklyCtx, {{
                type: 'line',
                data: {{
                    labels: {json.dumps(weeks)},
                    datasets: [{{
                        label: '问题跟进数',
                        data: {json.dumps(follow_counts)},
                        borderColor: '#1976D2',
                        backgroundColor: 'rgba(25, 118, 210, 0.1)',
                        yAxisID: 'y',
                        tension: 0.4,
                        pointRadius: 6
                    }}, {{
                        label: '闭环个数',
                        data: {json.dumps(close_counts)},
                        borderColor: '#42A5F5',
                        backgroundColor: 'rgba(66, 165, 245, 0.1)',
                        yAxisID: 'y',
                        tension: 0.4,
                        pointRadius: 6
                    }}, {{
                        label: '问题解决率(%)',
                        data: {json.dumps(resolution_rates)},
                        borderColor: '#FF9800',
                        backgroundColor: 'rgba(255, 152, 0, 0.1)',
                        yAxisID: 'y1',
                        tension: 0.4,
                        pointRadius: 6
                    }}, {{
                        label: '跟进数中位数',
                        data: Array({len(weeks)}).fill({follow_median}),
                        borderColor: '#E91E63',
                        backgroundColor: 'transparent',
                        borderDash: [5, 5],
                        yAxisID: 'y',
                        pointRadius: 0,
                        tension: 0
                    }}, {{
                        label: '闭环数中位数',
                        data: Array({len(weeks)}).fill({close_median}),
                        borderColor: '#9C27B0',
                        backgroundColor: 'transparent',
                        borderDash: [10, 5],
                        yAxisID: 'y',
                        pointRadius: 0,
                        tension: 0
                    }}]
                }},
                options: {{
                    responsive: true,
                    plugins: {{
                        title: {{ display: true, text: '{weekly_chart_title}' }},
                        legend: {{ position: 'top' }}
                    }},
                    scales: {{
                        y: {{ type: 'linear', display: true, position: 'left' }},
                        y1: {{ type: 'linear', display: true, position: 'right', grid: {{ drawOnChartArea: false }} }}
                    }}
                }}
            }});
            """)
        
        # 产品处理量分布
        visualizations = self._safe_get(results, 'visualizations', {})
        if visualizations.get('product_volume'):
            volume_data = visualizations.get('product_volume', [])
            volume_labels = [item['name'] for item in volume_data]
            volume_counts = [item['value'] for item in volume_data]
            volume_colors = ['#FF9800' if item.get('is_top3') else '#1976D2' for item in volume_data]
            
            chart_scripts.append(f"""
            const volumeCtx = document.getElementById('volumeChart').getContext('2d');
            new Chart(volumeCtx, {{
                type: 'bar',
                data: {{
                    labels: {json.dumps(volume_labels)},
                    datasets: [{{
                        label: '处理量',
                        data: {json.dumps(volume_counts)},
                        backgroundColor: {json.dumps(volume_colors)}
                    }}]
                }},
                options: {{
                    responsive: true,
                    plugins: {{ title: {{ display: true, text: '产品处理量分布（橙色为Top 3）' }} }}
                }}
            }});
            """)
        
        return chart_scripts

    def _generate_pie_chart_scripts(self, results: Dict) -> List[str]:
        """生成饼图脚本"""
        chart_scripts = []
        visualizations = self._safe_get(results, 'visualizations', {})
        
        # 问题产品分布图
        if visualizations.get('product_distribution'):
            products = visualizations.get('product_distribution', [])
            labels = [item['name'] for item in products]
            data = [item['value'] for item in products]
            colors = ['#FF5722', '#FF9800', '#FFC107', '#2196F3', '#4CAF50', '#9C27B0', '#E91E63', '#00BCD4', '#795548', '#607D8B']
            
            chart_scripts.append(f"""
            const productCtx = document.getElementById('productChart').getContext('2d');
            new Chart(productCtx, {{
                type: 'pie',
                data: {{
                    labels: {json.dumps(labels)},
                    datasets: [{{ data: {json.dumps(data)}, backgroundColor: {json.dumps(colors[:len(labels)])} }}]
                }},
                options: {{
                    responsive: true,
                    plugins: {{ title: {{ display: true, text: '问题产品分布' }}, legend: {{ position: 'bottom' }} }}
                }}
            }});
            """)
        
        # 汇总分类分布
        summary_data = visualizations.get('summary_classification', [])
        if summary_data:
            summary_labels = [item['name'] for item in summary_data]
            summary_counts = [item['value'] for item in summary_data]
            summary_colors = []
            for label in summary_labels:
                if '运维事件' in label:
                    summary_colors.append('#2196F3')
                elif '运营对接' in label:
                    summary_colors.append('#9C27B0')
                else:
                    color_palette = ['#FF5722', '#FF9800', '#FFC107', '#4CAF50', '#E91E63', '#00BCD4', '#795548', '#607D8B']
                    summary_colors.append(color_palette[len(summary_colors) % len(color_palette)])
            
            chart_scripts.append(f"""
            const summaryCtx = document.getElementById('summaryChart').getContext('2d');
            new Chart(summaryCtx, {{
                type: 'pie',
                data: {{
                    labels: {json.dumps(summary_labels)},
                    datasets: [{{ data: {json.dumps(summary_counts)}, backgroundColor: {json.dumps(summary_colors[:len(summary_labels)])} }}]
                }},
                options: {{
                    responsive: true,
                    plugins: {{ title: {{ display: true, text: '事务分类分布' }}, legend: {{ position: 'bottom' }} }}
                }}
            }});
            """)
        
        # 运维事件每月统计
        if results.get('maintenance_monthly_trends'):
            maintenance_months = [item[0] for item in self._safe_get(results, 'maintenance_monthly_trends', [])]
            maintenance_counts = [item[1] for item in self._safe_get(results, 'maintenance_monthly_trends', [])]
            
            chart_scripts.append(f"""
            const maintenanceMonthlyCtx = document.getElementById('maintenanceMonthlyChart').getContext('2d');
            new Chart(maintenanceMonthlyCtx, {{
                type: 'line',
                data: {{
                    labels: {json.dumps(maintenance_months)},
                    datasets: [{{
                        label: '运维事件数量',
                        data: {json.dumps(maintenance_counts)},
                        borderColor: '#2196F3',
                        backgroundColor: 'rgba(33, 150, 243, 0.1)',
                        tension: 0.4,
                        fill: true,
                        pointRadius: 6
                    }}]
                }},
                options: {{
                    responsive: true,
                    plugins: {{ title: {{ display: true, text: '运维事件每月统计折线图' }}, legend: {{ display: false }} }},
                    scales: {{ y: {{ beginAtZero: true }} }}
                }}
            }});
            """)
        
        # 完成状态分析
        if visualizations.get('completion_status'):
            status_data = visualizations.get('completion_status', [])
            status_labels = [item['name'] for item in status_data]
            status_counts = [item['value'] for item in status_data]
            status_colors = []
            for label in status_labels:
                if '已完成' in label:
                    status_colors.append('#4CAF50')
                else:
                    color_palette = ['#FF5722', '#FF9800', '#FFC107', '#2196F3', '#9C27B0', '#E91E63', '#00BCD4', '#795548', '#607D8B', '#3F51B5', '#009688']
                    status_colors.append(color_palette[len(status_colors) % len(color_palette)])
            
            chart_scripts.append(f"""
            const statusCtx = document.getElementById('statusChart').getContext('2d');
            new Chart(statusCtx, {{
                type: 'doughnut',
                data: {{
                    labels: {json.dumps(status_labels)},
                    datasets: [{{ data: {json.dumps(status_counts)}, backgroundColor: {json.dumps(status_colors)} }}]
                }},
                options: {{
                    responsive: true,
                    plugins: {{ title: {{ display: true, text: '完成状态分析' }} }}
                }}
            }});
            """)
        
        return chart_scripts

    def _generate_quality_chart_scripts(self, results: Dict) -> List[str]:
        """生成质量指标图表脚本（有感事件、升级率、月度趋势）"""
        chart_scripts = []
        quality = self._safe_get(results, 'quality_metrics', {})

        # 各产品有感率横向对比
        product_quality = quality.get('product_quality', [])
        if product_quality:
            prod_labels = [item['产品'] for item in product_quality]
            prod_totals = [item['卡片总数'] for item in product_quality]
            prod_feels = [item['有感事件数'] for item in product_quality]
            prod_esc = [item['升级到研或OP数'] for item in product_quality]

            chart_scripts.append(f"""
            const prodQualityCtx = document.getElementById('productQualityChart').getContext('2d');
            new Chart(prodQualityCtx, {{
                type: 'bar',
                data: {{
                    labels: {json.dumps(prod_labels)},
                    datasets: [{{
                        label: '卡片总数',
                        data: {json.dumps(prod_totals)},
                        backgroundColor: 'rgba(25, 118, 210, 0.5)',
                        yAxisID: 'y'
                    }}, {{
                        label: '有感事件数',
                        data: {json.dumps(prod_feels)},
                        backgroundColor: '#FF5722',
                        yAxisID: 'y'
                    }}, {{
                        label: '升级到研或OP数',
                        data: {json.dumps(prod_esc)},
                        backgroundColor: '#FF9800',
                        yAxisID: 'y'
                    }}]
                }},
                options: {{
                    responsive: true,
                    plugins: {{
                        title: {{ display: true, text: '各产品有感事件 & 升级数量（Top 15）' }},
                        legend: {{ position: 'top' }}
                    }},
                    scales: {{ y: {{ beginAtZero: true }} }}
                }}
            }});
            """)

        # 月度有感事件趋势折线图
        monthly_feels = quality.get('monthly_feels_trend', [])
        if monthly_feels:
            mf_months = [item['月份'] for item in monthly_feels]
            mf_totals = [item['总卡片数'] for item in monthly_feels]
            mf_feels = [item['有感事件数'] for item in monthly_feels]

            chart_scripts.append(f"""
            const monthlyFeelsCtx = document.getElementById('monthlyFeelsChart').getContext('2d');
            new Chart(monthlyFeelsCtx, {{
                type: 'line',
                data: {{
                    labels: {json.dumps(mf_months)},
                    datasets: [{{
                        label: '卡片总数',
                        data: {json.dumps(mf_totals)},
                        borderColor: '#1976D2',
                        backgroundColor: 'rgba(25, 118, 210, 0.1)',
                        tension: 0.4,
                        yAxisID: 'y',
                        pointRadius: 4
                    }}, {{
                        label: '有感事件数',
                        data: {json.dumps(mf_feels)},
                        borderColor: '#FF5722',
                        backgroundColor: 'rgba(255, 87, 34, 0.1)',
                        tension: 0.4,
                        yAxisID: 'y',
                        pointRadius: 5
                    }}]
                }},
                options: {{
                    responsive: true,
                    plugins: {{
                        title: {{ display: true, text: '月度有感事件趋势' }},
                        legend: {{ position: 'top' }}
                    }},
                    scales: {{ y: {{ beginAtZero: true }} }}
                }}
            }});
            """)

        return chart_scripts

    def _generate_quality_html(self, results: Dict) -> str:
        """生成质量指标 HTML 表格"""
        quality = self._safe_get(results, 'quality_metrics', {})

        # 产品质量指标表格
        product_quality = quality.get('product_quality', [])
        pq_html = ''
        if product_quality:
            rows = ''.join(
                f"<tr><td>{item['产品']}</td><td>{item['卡片总数']}</td>"
                f"<td>{item['有感事件数']} ({item['有感率']})</td>"
                f"<td>{item['升级到研或OP数']} ({item['升级率']})</td></tr>"
                for item in product_quality
            )
            pq_html = f"""
            <h3>各产品质量指标明细（Top 15）</h3>
            <table class="data-table">
                <thead><tr><th>产品</th><th>卡片总数</th><th>有感事件</th><th>升级到研或OP</th></tr></thead>
                <tbody>{rows}</tbody>
            </table>"""

        return pq_html

    def _generate_workload_html(self, results: Dict) -> str:
        """生成负责人工作量分析 HTML 表格"""
        workload = self._safe_get(results, 'person_workload', [])
        if not workload:
            return ''
        rows = ''.join(
            f"<tr><td>{item['创建人']}</td><td>{item['总卡片数']}</td>"
            f"<td>{item['已完成数量']}</td><td>{item['未完成数量']}</td></tr>"
            for item in workload
        )
        return f"""
        <table class="data-table">
            <thead><tr><th>负责人</th><th>总卡片数</th><th>已完成</th><th>进行中/待处理</th></tr></thead>
            <tbody>{rows}</tbody>
        </table>"""

    def _get_html_styles(self) -> str:
        """获取 HTML 样式"""
        return '''
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Microsoft YaHei', Arial, sans-serif; 
            background: linear-gradient(135deg, #E3F2FD 0%, #BBDEFB 100%);
            color: #333; line-height: 1.6; min-height: 100vh;
        }
        .container { 
            max-width: 1200px; margin: 0 auto; padding: 20px; 
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px; margin-top: 20px; margin-bottom: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
        }
        h1 { 
            text-align: center; 
            background: linear-gradient(45deg, #1976D2, #42A5F5);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            background-clip: text; margin-bottom: 40px; padding: 30px 0; 
            font-size: 2.5em; font-weight: 300;
        }
        section { 
            margin-bottom: 40px; background: white;
            border-radius: 15px; padding: 25px; 
            box-shadow: 0 8px 25px rgba(0,0,0,0.08);
            border: 1px solid rgba(25, 118, 210, 0.1);
        }
        section h2 { 
            color: #1976D2; margin-bottom: 25px; padding-bottom: 15px; 
            border-bottom: 2px solid #E3F2FD; font-weight: 500; font-size: 1.5em;
        }
        .anomaly-section { background: #F3E5F5; border-left: 4px solid #1976D2; }
        .anomaly-toggle {
            background: linear-gradient(45deg, #1976D2, #42A5F5);
            color: white; border: none; padding: 12px 24px;
            border-radius: 25px; cursor: pointer; font-size: 16px;
            margin-bottom: 20px; transition: all 0.3s ease;
        }
        .anomaly-content { display: none; }
        .anomaly-content.show { display: block; }
        .table-wrapper { overflow-x: auto; margin: 20px 0; }
        table { width: 100%; border-collapse: collapse; background: white; border-radius: 10px; overflow: hidden; }
        th, td { padding: 15px; text-align: center; border-bottom: 1px solid #E3F2FD; }
        th { background: linear-gradient(45deg, #1976D2, #42A5F5); color: white; font-weight: 500; position: sticky; top: 0; }
        tr:nth-child(even) { background-color: #F8FAFC; }
        tr:hover { background-color: #E3F2FD; }
        .no-data { color: #64748B; font-style: italic; text-align: center; padding: 40px; background: #F3E5F5; border-radius: 10px; }
        .chart-container { margin: 30px 0; text-align: center; }
        .chart-wrapper { display: inline-block; width: 500px; height: 500px; margin: 20px; background: white; border-radius: 15px; padding: 20px; box-shadow: 0 8px 25px rgba(0,0,0,0.08); }
        .chart-row { display: flex; justify-content: space-around; align-items: center; flex-wrap: wrap; margin: 30px 0; }
        .section-title { font-size: 1.2em; font-weight: 600; color: #1976D2; margin: 30px 0 15px 0; padding-left: 15px; border-left: 4px solid #1976D2; }
        .overview-cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }
        .card { background: white; padding: 25px; border-radius: 15px; text-align: center; box-shadow: 0 8px 25px rgba(0,0,0,0.08); transition: all 0.3s ease; border-left: 4px solid #1976D2; }
        .card:hover { transform: translateY(-5px); box-shadow: 0 15px 35px rgba(0,0,0,0.15); }
        .card.fault { border-left-color: #1976D2; }
        .card.requirement { border-left-color: #42A5F5; }
        .card.risk { border-left-color: #FF9800; }
        .card-number { color: #1976D2; font-size: 2.5em; font-weight: 300; margin-bottom: 10px; }
        .card-label { color: #666; font-size: 0.9em; font-weight: 500; }
        .product-details { margin: 20px 0; }
        .product-item { background: white; margin: 15px 0; border-radius: 15px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }
        .product-header { background: linear-gradient(45deg, #F3E5F5, #E3F2FD); padding: 20px; cursor: pointer; display: flex; justify-content: space-between; align-items: center; transition: all 0.3s ease; }
        .product-header:hover { background: linear-gradient(45deg, #E3F2FD, #BBDEFB); }
        .product-stats { display: flex; gap: 30px; }
        .product-cards { padding: 20px; }
        .footer { margin-top: 50px; padding: 30px; background: linear-gradient(45deg, #F3E5F5, #E3F2FD); border-radius: 15px; text-align: center; color: #666; }
        a { color: #1976D2; text-decoration: none; }
        a:hover { color: #42A5F5; text-decoration: underline; }
        @media (max-width: 768px) {
            .chart-wrapper { width: 100%; height: 400px; margin: 10px 0; }
            .chart-row { flex-direction: column; }
            .overview-cards { grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); }
        }
        
        /* AI 解读样式 */
        .ai-interpretation {
            background: linear-gradient(135deg, #F3E5F5 0%, #E3F2FD 100%);
            border: 2px solid #1976D2;
            border-left: 6px solid #1976D2;
        }
        .ai-interpretation h2 {
            color: #1976D2;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .ai-content {
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin-top: 15px;
            line-height: 1.8;
        }
        .ai-content h4 {
            color: #1976D2;
            margin-top: 15px;
            margin-bottom: 10px;
            font-weight: 600;
        }
        .ai-content p {
            color: #555;
            margin-bottom: 10px;
            text-align: justify;
        }
        .ai-content ul {
            margin-left: 20px;
            margin-bottom: 15px;
        }
        .ai-content li {
            color: #555;
            margin-bottom: 8px;
        }
        '''

    def generate_html_report(self, results: Dict[str, Any]) -> str:
        """生成完整的 HTML 报告"""
        # 获取数据
        total_cards = self._safe_get_nested(results, 'overview', '总卡片数', '0')
        avg_weekly = self._safe_get_nested(results, 'overview', '平均每周卡片处理量', '0')
        total_issues = self._safe_get_nested(results, 'overview', '总问题数', '0')
        completed_issues = self._safe_get_nested(results, 'overview', '已完成数', '0')
        issue_rate = self._safe_get_nested(results, 'overview', '问题闭环率', '0')
        total_reqs = self._safe_get_nested(results, 'overview', '总需求数', '0')
        new_reqs = self._safe_get_nested(results, 'overview', '新增需求', '0')
        ongoing_reqs = self._safe_get_nested(results, 'overview', '进行中需求', '0')
        completed_reqs = self._safe_get_nested(results, 'overview', '已完成需求', '0')
        req_rate = self._safe_get_nested(results, 'overview', '需求闭环率', '0')
        risk_total = self._safe_get_nested(results, 'overview', '风险治理总数', '0')
        risk_completed = self._safe_get_nested(results, 'overview', '风险治理完成数量', '0')

        # 生成异常检测表格
        anomalies = self._safe_get(results, 'anomalies', {})
        c_anomalies_html = self._generate_table_html(anomalies.get('c_anomalies', []), ['编号', '标题', '故障等级', '创建人'])
        r_anomalies_html = self._generate_table_html(anomalies.get('r_anomalies', []), ['编号', '标题', '故障等级', '创建人'])
        k_anomalies_html = self._generate_table_html(anomalies.get('k_anomalies', []), ['编号', '标题', '故障等级', '创建人'])
        classification_anomalies_html = self._generate_table_html(anomalies.get('classification_anomalies', []), ['编号', '标题', '创建人'])

        html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>长安LCC运营数据分析</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>{self._get_html_styles()}</style>
</head>
<body>
    <div class="container">
        <h1>长安LCC运营数据分析</h1>
        
        <!-- 异常检测模块 -->
        <section class="anomaly-section">
            <h2>异常检测</h2>
            <button class="anomaly-toggle" onclick="toggleAnomalySection()">展开/收起异常检测详情</button>
            <div class="anomaly-content" id="anomalyContent">
                <h3>1. 卡片类型异常</h3>
                <h4>C2/C3类型异常</h4>{c_anomalies_html}
                <h4>R2/R3类型异常</h4>{r_anomalies_html}
                <h4>K2/K3类型异常</h4>{k_anomalies_html}
                <h3>2. 方向大类、细分分类字段为空</h3>{classification_anomalies_html}
            </div>
        </section>
        
        <!-- 数据概览统计 -->
        <section>
            <h2>数据概览统计</h2>
            <div class="overview-cards">
                <div class="card"><div class="card-number">{total_cards}</div><div class="card-label">总卡片数</div></div>
                <div class="card"><div class="card-number">{avg_weekly}</div><div class="card-label">平均每周卡片处理量</div></div>
            </div>
            <div class="section-title">故障</div>
            <div class="overview-cards">
                <div class="card fault"><div class="card-number">{total_issues}</div><div class="card-label">总问题数</div></div>
                <div class="card fault"><div class="card-number">{completed_issues}</div><div class="card-label">已完成数</div></div>
                <div class="card fault"><div class="card-number">{issue_rate}</div><div class="card-label">问题闭环率</div></div>
            </div>
            <div class="section-title">需求</div>
            <div class="overview-cards">
                <div class="card requirement"><div class="card-number">{total_reqs}</div><div class="card-label">总需求数</div></div>
                <div class="card requirement"><div class="card-number">{new_reqs}</div><div class="card-label">新增需求</div></div>
                <div class="card requirement"><div class="card-number">{ongoing_reqs}</div><div class="card-label">进行中需求</div></div>
                <div class="card requirement"><div class="card-number">{completed_reqs}</div><div class="card-label">已完成需求</div></div>
                <div class="card requirement"><div class="card-number">{req_rate}</div><div class="card-label">需求闭环率</div></div>
            </div>
            <div class="section-title">风险</div>
            <div class="overview-cards">
                <div class="card risk"><div class="card-number">{risk_total}</div><div class="card-label">风险治理总数</div></div>
                <div class="card risk"><div class="card-number">{risk_completed}</div><div class="card-label">风险治理完成数量</div></div>
            </div>
        </section>
'''
        
        return html

    async def generate_html_report_full_with_ai(self, results: Dict[str, Any], report_type: str = 'operational_analysis') -> str:
        """
        生成完整的 HTML 报告（包含 AI 解读）
        
        Args:
            results: 分析结果
            report_type: 报告类型
        
        Returns:
            str: 完整的 HTML 报告
        """
        # 获取基础报告
        html = self.generate_html_report_full(results)
        
        # 生成 AI 解读
        ai_interpretation_html = ""
        if self.enable_ai_interpretation and self.ai_interpreter:
            try:
                logger.info(f"📝 正在生成 {report_type} 的 AI 解读...")
                ai_interpretation_html = await self.ai_interpreter.generate_interpretation(
                    report_type=report_type,
                    analysis_data=results
                )
                
                if ai_interpretation_html:
                    logger.info(f"✅ AI 解读生成成功")
                else:
                    logger.warning(f"⚠️ AI 解读生成失败，返回空内容")
                    
            except Exception as e:
                logger.error(f"❌ 生成 AI 解读异常: {e}")
        
        # 如果有 AI 解读，插入到报告中
        if ai_interpretation_html:
            # 在历史数据概览之后、页脚之前插入 AI 解读
            ai_section = f'''
        <!-- AI 智能解读 -->
        <section class="ai-interpretation">
            <h2>🤖 AI 智能解读</h2>
            <div class="ai-content">
                {ai_interpretation_html}
            </div>
        </section>
'''
            # 找到页脚位置并插入
            footer_marker = '<div class="footer">'
            if footer_marker in html:
                html = html.replace(footer_marker, ai_section + footer_marker)
        
        return html
    
    def generate_html_report_full(self, results: Dict[str, Any]) -> str:
        """生成完整的 HTML 报告（包含所有部分）"""
        # 获取基础部分
        html = self.generate_html_report(results)

        # 收集所有图表脚本
        chart_scripts = []
        chart_scripts.extend(self._generate_chart_scripts(results))
        chart_scripts.extend(self._generate_more_chart_scripts(results))
        chart_scripts.extend(self._generate_pie_chart_scripts(results))
        chart_scripts.extend(self._generate_quality_chart_scripts(results))

        # 生成各 section 的 HTML 内容
        product_detail_html = self._generate_product_detail_html(self._safe_get(results, 'top5_products', []))
        quality_html = self._generate_quality_html(results)
        workload_html = self._generate_workload_html(results)

        report_time = datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")

        # 从 overview 中读取有感/升级汇总数据（N/A 表示数据中无对应列）
        overview = self._safe_get(results, 'overview', {})
        feels_yes = overview.get('有感事件数', 'N/A')
        feels_rate = overview.get('有感率', 'N/A')
        escalated = overview.get('升级到研或OP数', 'N/A')
        escalate_rate = overview.get('升级率', 'N/A')

        # 只有数据中存在有感/升级列时才展示对应 card
        has_feels_data = str(feels_rate) != 'N/A'
        has_escalate_data = str(escalate_rate) != 'N/A'
        quality_metrics = self._safe_get(results, 'quality_metrics', {})
        has_product_quality = bool(quality_metrics.get('product_quality'))
        has_monthly_feels = bool(quality_metrics.get('monthly_feels_trend'))

        # 质量指标卡片 HTML（仅在有数据时生成）
        feels_cards_html = ''
        if has_feels_data:
            feels_cards_html += f'<div class="card fault"><div class="card-number">{feels_yes}</div><div class="card-label">有感事件数</div></div>'
            feels_cards_html += f'<div class="card fault"><div class="card-number">{feels_rate}</div><div class="card-label">有感率</div></div>'
        if has_escalate_data:
            feels_cards_html += f'<div class="card risk"><div class="card-number">{escalated}</div><div class="card-label">升级到研或OP数</div></div>'
            feels_cards_html += f'<div class="card risk"><div class="card-number">{escalate_rate}</div><div class="card-label">升级率</div></div>'

        product_quality_chart_html = ''
        if has_product_quality:
            product_quality_chart_html = '<h3>各产品有感事件与升级数量</h3><div class="chart-container"><canvas id="productQualityChart" style="max-height: 450px;"></canvas></div>'

        monthly_feels_chart_html = ''
        if has_monthly_feels:
            monthly_feels_chart_html = '<h3>月度有感事件趋势</h3><div class="chart-container"><canvas id="monthlyFeelsChart" style="max-height: 350px;"></canvas></div>'

        quality_section_content = feels_cards_html or product_quality_chart_html or monthly_feels_chart_html or quality_html
        quality_section_html = ''
        if quality_section_content:
            quality_section_html = f'''
        <!-- 质量指标分析 -->
        <section>
            <h2>质量指标分析</h2>
            {'<div class="overview-cards">' + feels_cards_html + '</div>' if feels_cards_html else ''}
            {product_quality_chart_html}
            {monthly_feels_chart_html}
            {quality_html}
        </section>'''

        # 推断月度图和周度图的粒度标题
        monthly_data_check = self._safe_get(results, 'monthly_trends', [])
        weekly_data_check = self._safe_get(results, 'weekly_trends', [])
        monthly_section_title = '每日处理卡片数趋势' if (
            monthly_data_check and '/' in str(monthly_data_check[0][0])
        ) else '每月处理卡片数趋势'
        weekly_section_title = '每日处理卡片趋势' if (
            weekly_data_check and '-' not in str(
                weekly_data_check[0].get('周期标签') or weekly_data_check[0].get('周期', '')
            )
        ) else '每周处理卡片趋势'

        # 添加数据可视化部分
        html += f'''
        <!-- 数据可视化 -->
        <section>
            <h2>数据可视化</h2>
            <h3>{monthly_section_title}</h3>
            <div class="chart-container"><canvas id="monthlyChart" style="max-height: 400px;"></canvas></div>
            <h3>{weekly_section_title}</h3>
            <div class="chart-container"><canvas id="weeklyChart" style="max-height: 400px;"></canvas></div>
            <h3>产品处理量分布</h3>
            <div class="chart-container"><canvas id="volumeChart" style="max-height: 400px;"></canvas></div>
            <div class="chart-row">
                <div class="chart-wrapper"><h4>问题产品分布图</h4><canvas id="productChart"></canvas></div>
                <div class="chart-wrapper"><h4>事务分类分布</h4><canvas id="summaryChart"></canvas></div>
            </div>
            <div class="chart-row">
                <div class="chart-wrapper"><h4>运维事件统计折线图</h4><canvas id="maintenanceMonthlyChart"></canvas></div>
                <div class="chart-wrapper"><h4>完成状态分析</h4><canvas id="statusChart"></canvas></div>
            </div>
        </section>

        <!-- 产品详细统计 -->
        <section>
            <h2>产品详细统计（Top 5）</h2>
            {product_detail_html}
        </section>

        {quality_section_html}

        <!-- 负责人卡片承接情况 -->
        <section>
            <h2>负责人卡片承接情况</h2>
            <p style="color:#666;font-size:13px;margin-bottom:12px;">
                说明：未完成包含进行中、待处理、验证中、长期跟踪等正常状态，不代表工作滞后。
            </p>
            {workload_html}
        </section>

        <div class="footer">
            <p>📊 报告生成时间: {report_time}</p>
            <p>🔧 分析工具: 长安LCC运营数据分析系统</p>
        </div>
    </div>

    <script>
        {chr(10).join(chart_scripts)}

        function toggleAnomalySection() {{
            const content = document.getElementById('anomalyContent');
            content.classList.toggle('show');
        }}

        function toggleProductDetail(productId) {{
            const detail = document.getElementById(productId);
            if (detail.style.display === 'none') {{
                detail.style.display = 'block';
            }} else {{
                detail.style.display = 'none';
            }}
        }}
    </script>
</body>
</html>'''

        return html
    
    def save_report(self, html_content: str, output_path: str) -> str:
        """保存报告到文件"""
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            logger.info(f"报告已保存到: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"保存报告失败: {e}")
            raise
