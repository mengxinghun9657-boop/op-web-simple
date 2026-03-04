#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
from datetime import datetime

def safe_get(data, key, default=None):
    """安全获取字典值"""
    if not data:
        return default
    result = data.get(key, default)
    return result if result is not None else default

def safe_get_nested(data, key1, key2, default="0"):
    """安全获取嵌套字典值"""
    if not data:
        return default
    level1 = data.get(key1, {})
    if not level1:
        return default
    result = level1.get(key2, default)
    return result if result is not None else default

def load_analysis_results():
    """加载分析结果"""
    try:
        # 使用脚本所在目录
        script_dir = os.path.dirname(os.path.abspath(__file__))
        results_path = os.path.join(script_dir, 'analysis_results.json')
        
        with open(results_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"加载分析结果失败: {e}")
        return None

def generate_table_html(data, columns, has_links=True):
    """生成表格HTML"""
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

def generate_product_detail_html(products):
    """生成产品详细统计HTML"""
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
                    <thead>
                        <tr><th>编号</th><th>标题</th><th>创建人</th></tr>
                    </thead>
                    <tbody>
        '''
        
        for card in product['相关卡片']:
            html += f'''
            <tr>
                <td>{card['编号']}</td>
                <td><a href="https://console.cloud.baidu-int.com/devops/icafe/issue/{card['编号']}/show?source=copy-shortcut" target="_blank">{card['标题']}</a></td>
                <td>{card['创建人']}</td>
            </tr>
            '''
        
        html += '''
                    </tbody>
                </table>
            </div>
        </div>
        '''
    
    html += '</div>'
    return html

def generate_hardware_responsible_html(responsible_data):
    """生成硬件故障负责人分布HTML"""
    if not responsible_data:
        return '<div class="no-data">无数据</div>'
    
    html = ''
    for item in responsible_data:
        html += f'''
        <div class="product-dist-item">
            <div class="product-name">{item['负责人']}</div>
            <div>
                <span class="product-count">{item['处理数量']}</span>
                <span class="product-percentage">({item['占比']})</span>
            </div>
        </div>
        '''
    return html

def generate_product_distribution_html(product_distribution):
    """生成产品分布HTML"""
    if not product_distribution:
        return ""
    
    html = '''
    <div class="section-title">涉及产品分布</div>
    <div class="product-distribution">
    '''
    
    for item in product_distribution[:8]:
        html += f'''
        <div class="product-dist-item">
            <div class="product-name">{item['name']}</div>
            <div>
                <span class="product-count">{item['value']}</span>
                <span class="product-percentage">({item['percentage']})</span>
            </div>
        </div>
        '''
    
    html += '</div>'
    return html

def generate_html_report(results):
    """生成完整的HTML报告"""
    
    # 定义换行符和特殊字符
    newline = '\n'
    closing_script_tag = '</script>'
    
    # 生成图表脚本
    chart_scripts = []
    
    # 每月处理卡片数趋势
    if results.get('monthly_trends'):
        monthly_data = safe_get(results, 'monthly_trends', [])
        if isinstance(monthly_data, list) and len(monthly_data) > 0:
            months = [item[0] if isinstance(item, (list, tuple)) and len(item) > 0 else str(item) for item in monthly_data]
            counts = [item[1] if isinstance(item, (list, tuple)) and len(item) > 1 else 0 for item in monthly_data]
        else:
            months = []
            counts = []
        
        chart_scripts.append(f"""
        const monthlyCtx = document.getElementById('monthlyChart').getContext('2d');
        new Chart(monthlyCtx, {{
            type: 'line',
            data: {{
                labels: {json.dumps(months)},
                datasets: [{{
                    label: '处理卡片数',
                    data: {json.dumps(counts)},
                    borderColor: '#1976D2',
                    backgroundColor: 'rgba(25, 118, 210, 0.1)',
                    tension: 0.4,
                    fill: true,
                    pointRadius: 6
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{ title: {{ display: true, text: '每月处理卡片数趋势' }} }}
            }}
        }});
        """)
    
    # 每周处理卡片趋势
    if results.get('weekly_trends'):
        weekly_data = safe_get(results, 'weekly_trends', [])
        if isinstance(weekly_data, list) and len(weekly_data) > 0:
            weeks = [item.get('周期', '') if isinstance(item, dict) else '' for item in weekly_data]
            follow_counts = [item.get('问题跟进数', 0) if isinstance(item, dict) else 0 for item in weekly_data]
            close_counts = [item.get('闭环个数', 0) if isinstance(item, dict) else 0 for item in weekly_data]
            resolution_rates = [item.get('问题解决率', 0) if isinstance(item, dict) else 0 for item in weekly_data]
            
            # 计算中位数
            import statistics
            follow_median = statistics.median(follow_counts) if follow_counts else 0
            close_median = statistics.median(close_counts) if close_counts else 0
        
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
                        title: {{ display: true, text: '每周处理卡片趋势（含中位数参考线）' }},
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
    if safe_get(results, 'visualizations', {}).get('product_volume'):
        volume_data = safe_get(safe_get(results, 'visualizations', {}), 'product_volume', {})
        volume_labels = [item['name'] for item in volume_data]
        volume_counts = [item['value'] for item in volume_data]
        volume_colors = ['#FF9800' if item['is_top3'] else '#1976D2' for item in volume_data]
        
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
    
    # 问题产品分布图
    if safe_get(results, 'visualizations', {}).get('product_distribution'):
        products = safe_get(safe_get(results, 'visualizations', {}), 'product_distribution', {})
        top3 = [item for item in products if item.get('is_top3', False)][:3]
        labels = [item['name'] for item in products]
        data = [item['value'] for item in products]
        # 浅蓝色为主的配色方案
        colors = ['#1976D2', '#42A5F5', '#64B5F6', '#90CAF9', '#BBDEFB', '#E3F2FD', '#1565C0', '#0D47A1']
        top3_text = " | ".join([f"{item['name']}: {item['percentage']}" for item in top3])
        
        chart_scripts.append(f"""
        const productCtx = document.getElementById('productChart').getContext('2d');
        new Chart(productCtx, {{
            type: 'pie',
            data: {{
                labels: {json.dumps(labels)},
                datasets: [{{
                    data: {json.dumps(data)},
                    backgroundColor: {json.dumps(colors)}
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    title: {{ display: true, text: 'Top 3: {top3_text}' }},
                    legend: {{ position: 'bottom' }}
                }}
            }}
        }});
        """)
    
    # 完成状态分析
    if safe_get(results, 'visualizations', {}).get('completion_status'):
        status_data = safe_get(safe_get(results, 'visualizations', {}), 'completion_status', {})
        status_labels = [item['name'] for item in status_data]
        status_counts = [item['value'] for item in status_data]
        # 浅蓝色系的状态颜色
        status_colors = ['#1976D2', '#42A5F5', '#64B5F6', '#90CAF9', '#BBDEFB', '#E3F2FD', '#1565C0']
        
        chart_scripts.append(f"""
        const statusCtx = document.getElementById('statusChart').getContext('2d');
        new Chart(statusCtx, {{
            type: 'doughnut',
            data: {{
                labels: {json.dumps(status_labels)},
                datasets: [{{
                    data: {json.dumps(status_counts)},
                    backgroundColor: {json.dumps(status_colors)}
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{ title: {{ display: true, text: '完成状态分析' }} }}
            }}
        }});
        """)
    
    # 硬件故障分析 - 分类分布
    hardware_failures = safe_get(results, 'hardware_failures', {})
    if hardware_failures and hardware_failures.get('analysis'):
        hardware_labels = [item['name'] for item in hardware_failures['analysis']]
        hardware_counts = [item['value'] for item in hardware_failures['analysis']]
        
        chart_scripts.append(f"""
        const hardwareCtx = document.getElementById('hardwareChart').getContext('2d');
        new Chart(hardwareCtx, {{
            type: 'bar',
            data: {{
                labels: {json.dumps(hardware_labels)},
                datasets: [{{
                    label: '故障数量',
                    data: {json.dumps(hardware_counts)},
                    backgroundColor: '#1976D2',
                    borderColor: '#0D47A1',
                    borderWidth: 1
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{ 
                    title: {{ display: true, text: '硬件故障分类分布' }},
                    legend: {{ display: false }}
                }},
                scales: {{
                    y: {{ beginAtZero: true }}
                }}
            }}
        }});
        """)
    

    
    # 硬件故障周度趋势
    hardware_failures = safe_get(results, 'hardware_failures', {})
    hardware_summary = hardware_failures.get('summary', {}) if hardware_failures else {}
    if hardware_summary and hardware_summary.get('周度趋势'):
        trend_data = hardware_summary['周度趋势']
        trend_weeks = [item['周期'] for item in trend_data]
        trend_counts = [item['硬件故障数'] for item in trend_data]
        trend_resolved = [item['已解决数'] for item in trend_data]
        
        chart_scripts.append(f"""
        const hardwareTrendCtx = document.getElementById('hardwareTrendChart').getContext('2d');
        new Chart(hardwareTrendCtx, {{
            type: 'line',
            data: {{
                labels: {json.dumps(trend_weeks)},
                datasets: [{{
                    label: '硬件故障数',
                    data: {json.dumps(trend_counts)},
                    borderColor: '#F44336',
                    backgroundColor: 'rgba(244, 67, 54, 0.1)',
                    tension: 0.4,
                    pointRadius: 6
                }}, {{
                    label: '已解决数',
                    data: {json.dumps(trend_resolved)},
                    borderColor: '#4CAF50',
                    backgroundColor: 'rgba(76, 175, 80, 0.1)',
                    tension: 0.4,
                    pointRadius: 6
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    title: {{ display: true, text: '硬件故障周度趋势' }},
                    legend: {{ position: 'top' }}
                }},
                scales: {{
                    y: {{ beginAtZero: true }}
                }}
            }}
        }});
        """)
    
    # 人效分析柱状图
    efficiency_data = safe_get(results, 'efficiency', {})
    if efficiency_data and isinstance(efficiency_data, list) and len(efficiency_data) > 0:
        efficiency_users = [item['创建人'] for item in efficiency_data if isinstance(item, dict)]
        total_cards = [item['总卡片数'] for item in efficiency_data if isinstance(item, dict)]
        completed_cards = [item['已完成数量'] for item in efficiency_data if isinstance(item, dict)]
        uncompleted_cards = [item['未完成数量'] for item in efficiency_data if isinstance(item, dict)]
        completion_rates = [item['完成率数值'] for item in efficiency_data if isinstance(item, dict)]
        
        chart_scripts.append(f"""
        const efficiencyCtx = document.getElementById('efficiencyChart').getContext('2d');
        new Chart(efficiencyCtx, {{
            type: 'bar',
            data: {{
                labels: {json.dumps(efficiency_users)},
                datasets: [{{
                    label: '总卡片数',
                    data: {json.dumps(total_cards)},
                    backgroundColor: '#1976D2'
                }}, {{
                    label: '已完成数量',
                    data: {json.dumps(completed_cards)},
                    backgroundColor: '#42A5F5'
                }}, {{
                    label: '未完成数量',
                    data: {json.dumps(uncompleted_cards)},
                    backgroundColor: '#FF9800'
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{ title: {{ display: true, text: '重点关注人员工作量' }} }}
            }}
        }});
        """)
    
    # 全员工作量统计图表
    all_responsible_stats = safe_get(results, 'all_responsible_stats', {})
    if all_responsible_stats and isinstance(all_responsible_stats, list) and len(all_responsible_stats) > 0:
        all_users = [item['负责人'] for item in all_responsible_stats if isinstance(item, dict)]
        all_total_cards = [item['总卡片数'] for item in all_responsible_stats if isinstance(item, dict)]
        all_completed_cards = [item['已完成数量'] for item in all_responsible_stats if isinstance(item, dict)]
        all_uncompleted_cards = [item['未完成数量'] for item in all_responsible_stats if isinstance(item, dict)]
        
        chart_scripts.append(f"""
        const allResponsibleCtx = document.getElementById('allResponsibleChart').getContext('2d');
        new Chart(allResponsibleCtx, {{
            type: 'bar',
            data: {{
                labels: {json.dumps(all_users)},
                datasets: [{{
                    label: '总卡片数',
                    data: {json.dumps(all_total_cards)},
                    backgroundColor: '#1976D2'
                }}, {{
                    label: '已完成数量',
                    data: {json.dumps(all_completed_cards)},
                    backgroundColor: '#42A5F5'
                }}, {{
                    label: '未完成数量',
                    data: {json.dumps(all_uncompleted_cards)},
                    backgroundColor: '#FF9800'
                }}]
            }},
            options: {{
                responsive: true,
                indexAxis: 'y',  // 横向柱状图，便于显示更多人员
                plugins: {{ 
                    title: {{ display: true, text: '全员工作量统计（Top 10）' }},
                    legend: {{ position: 'top' }}
                }},
                scales: {{
                    x: {{ beginAtZero: true }}
                }}
            }}
        }});
        """)
    
    # 删除涉及产品分布
    product_dist_html = ""
    
    # 预先获取所有需要的数据
    total_cards = safe_get_nested(results, 'overview', '总卡片数', '0')
    avg_weekly = safe_get_nested(results, 'overview', '平均每周卡片处理量', '0')
    total_issues = safe_get_nested(results, 'overview', '总问题数', '0')
    completed_issues = safe_get_nested(results, 'overview', '已完成数', '0')
    issue_rate = safe_get_nested(results, 'overview', '问题闭环率', '0')
    total_reqs = safe_get_nested(results, 'overview', '总需求数', '0')
    new_reqs = safe_get_nested(results, 'overview', '新增需求', '0')
    ongoing_reqs = safe_get_nested(results, 'overview', '进行中需求', '0')
    completed_reqs = safe_get_nested(results, 'overview', '已完成需求', '0')
    req_rate = safe_get_nested(results, 'overview', '需求闭环率', '0')
    risk_total = safe_get_nested(results, 'overview', '风险治理总数', '0')
    risk_completed = safe_get_nested(results, 'overview', '风险治理完成数量', '0')
    
    report_time = datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")
    
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>长安LCC运营数据分析</title>
    <!-- 使用多个CDN源，提高加载成功率 -->
    <script src="https://cdn.bootcdn.net/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>
    <script>
        // 如果国内CDN加载失败，尝试jsdelivr
        if (typeof Chart === 'undefined') {{
            var script = document.createElement('script');
            script.src = 'https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js';
            document.head.appendChild(script);
        }}
        
        // 页面加载完成后检查Chart.js是否可用
        window.addEventListener('load', function() {{
            if (typeof Chart === 'undefined') {{
                console.error('Chart.js加载失败，图表将无法显示');
                // 显示错误提示
                const chartContainers = document.querySelectorAll('.chart-container');
                chartContainers.forEach(container => {{
                    container.innerHTML = '<div style="text-align: center; padding: 50px; color: #666; background: #f5f5f5; border-radius: 10px;">📊 图表加载失败，请检查网络连接</div>';
                }});
            }}
        }});
    </script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: 'Microsoft YaHei', Arial, sans-serif; 
            background: linear-gradient(135deg, #E3F2FD 0%, #BBDEFB 100%);
            color: #333; 
            line-height: 1.6; 
            min-height: 100vh;
        }}
        .container {{ 
            max-width: 1200px; 
            margin: 0 auto; 
            padding: 20px; 
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            margin-top: 20px;
            margin-bottom: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
        }}
        h1 {{ 
            text-align: center; 
            background: linear-gradient(45deg, #1976D2, #42A5F5);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 40px; 
            padding: 30px 0; 
            font-size: 2.5em;
            font-weight: 300;
        }}
        section {{ 
            margin-bottom: 40px; 
            background: white;
            border-radius: 15px; 
            padding: 25px; 
            box-shadow: 0 8px 25px rgba(0,0,0,0.08);
            border: 1px solid rgba(25, 118, 210, 0.1);
        }}
        section h2 {{ 
            color: #1976D2; 
            margin-bottom: 25px; 
            padding-bottom: 15px; 
            border-bottom: 2px solid #E3F2FD; 
            font-weight: 500;
            font-size: 1.5em;
        }}
        .anomaly-section {{
            background: #F3E5F5;
            border-left: 4px solid #1976D2;
        }}
        .anomaly-toggle {{
            background: linear-gradient(45deg, #1976D2, #42A5F5);
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 25px;
            cursor: pointer;
            font-size: 16px;
            margin-bottom: 20px;
            transition: all 0.3s ease;
        }}
        .anomaly-content {{
            display: none;
        }}
        .anomaly-content.show {{
            display: block;
        }}
        .table-wrapper {{
            overflow-x: auto;
            margin: 20px 0;
        }}
        table {{ 
            width: 100%; 
            border-collapse: collapse; 
            background: white; 
            border-radius: 10px; 
            overflow: hidden;
        }}
        th, td {{ 
            padding: 15px; 
            text-align: center; 
            border-bottom: 1px solid #E3F2FD; 
        }}
        th {{ 
            background: linear-gradient(45deg, #1976D2, #42A5F5);
            color: white; 
            font-weight: 500;
            position: sticky;
            top: 0;
        }}
        tr:nth-child(even) {{ background-color: #F8FAFC; }}
        tr:hover {{ background-color: #E3F2FD; }}
        .no-data {{ 
            color: #64748B; 
            font-style: italic; 
            text-align: center; 
            padding: 40px;
            background: #F3E5F5;
            border-radius: 10px;
        }}
        .chart-container {{ 
            margin: 30px 0; 
            text-align: center; 
        }}
        .chart-wrapper {{ 
            display: inline-block; 
            width: 500px; 
            height: 500px; 
            margin: 20px;
            background: white;
            border-radius: 15px;
            padding: 20px;
            box-shadow: 0 8px 25px rgba(0,0,0,0.08);
        }}
        .chart-row {{
            display: flex;
            justify-content: space-around;
            align-items: center;
            flex-wrap: wrap;
            margin: 30px 0;
        }}
        .section-title {{
            font-size: 1.2em;
            font-weight: 600;
            color: #1976D2;
            margin: 30px 0 15px 0;
            padding-left: 15px;
            border-left: 4px solid #1976D2;
        }}
        .overview-cards {{ 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); 
            gap: 20px; 
            margin: 20px 0; 
        }}
        .card {{ 
            background: white;
            padding: 25px; 
            border-radius: 15px; 
            text-align: center; 
            box-shadow: 0 8px 25px rgba(0,0,0,0.08);
            transition: all 0.3s ease;
            border-left: 4px solid #1976D2;
        }}
        .card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 15px 35px rgba(0,0,0,0.15);
        }}
        .card.fault {{ border-left-color: #1976D2; }}
        .card.requirement {{ border-left-color: #42A5F5; }}
        .card.risk {{ border-left-color: #FF9800; }}
        .card-number {{ 
            color: #1976D2; 
            font-size: 2.5em; 
            font-weight: 300;
            margin-bottom: 10px; 
        }}
        .card-label {{
            color: #666;
            font-size: 0.9em;
            font-weight: 500;
        }}
        .product-distribution {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}
        .product-dist-item {{
            background: white;
            padding: 15px 20px;
            border-radius: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 4px 15px rgba(0,0,0,0.05);
            border-left: 4px solid #64B5F6;
        }}
        .product-name {{ font-weight: 500; color: #333; }}
        .product-count {{ color: #1976D2; font-weight: 600; }}
        .product-percentage {{ color: #666; font-size: 0.9em; }}
        .product-details {{ margin: 20px 0; }}
        .product-item {{ 
            background: white; 
            margin: 15px 0; 
            border-radius: 15px; 
            overflow: hidden;
            box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        }}
        .product-header {{ 
            background: linear-gradient(45deg, #F3E5F5, #E3F2FD);
            padding: 20px; 
            cursor: pointer; 
            display: flex; 
            justify-content: space-between; 
            align-items: center;
            transition: all 0.3s ease;
        }}
        .product-header:hover {{ background: linear-gradient(45deg, #E3F2FD, #BBDEFB); }}
        .product-stats {{ display: flex; gap: 30px; }}
        .product-cards {{ padding: 20px; }}
        .footer {{ 
            margin-top: 50px; 
            padding: 30px; 
            background: linear-gradient(45deg, #F3E5F5, #E3F2FD);
            border-radius: 15px; 
            text-align: center; 
            color: #666;
        }}
        a {{ color: #1976D2; text-decoration: none; }}
        a:hover {{ color: #42A5F5; text-decoration: underline; }}
        @media (max-width: 768px) {{
            .chart-wrapper {{ width: 100%; height: 400px; margin: 10px 0; }}
            .chart-row {{ flex-direction: column; }}
            .overview-cards {{ grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); }}
        }}
    </style>
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
                <h4>C2/C3类型异常</h4>
                {generate_table_html(safe_get(safe_get(results, 'anomalies', {}), 'c_anomalies', []), ['编号', '标题', '故障等级', '创建人'])}
                
                <h4>R2/R3类型异常</h4>
                {generate_table_html(safe_get(safe_get(results, 'anomalies', {}), 'r_anomalies', []), ['编号', '标题', '故障等级', '创建人'])}
                
                <h4>K2/K3类型异常</h4>
                {generate_table_html(safe_get(safe_get(results, 'anomalies', {}), 'k_anomalies', []), ['编号', '标题', '故障等级', '创建人'])}
                
                <h3>2. 方向大类、细分分类字段为空</h3>
                {generate_table_html(safe_get(safe_get(results, 'anomalies', {}), 'classification_anomalies', []), ['编号', '标题', '创建人'])}
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
                <div class="card risk"><div class="card-number"><a href="https://ku.baidu-int.com/knowledge/HFVrC7hq1Q/-ikorFqd5i/-Zoz27NBjC/Ds7-21zQUTySrn" target="_blank">{risk_total}</a></div><div class="card-label">风险治理总数</div></div>
                <div class="card risk"><div class="card-number">{risk_completed}</div><div class="card-label">风险治理完成数量</div></div>
            </div>
            
            {product_dist_html}
        </section>
        
        <!-- 数据可视化 -->
        <section>
            <h2>数据可视化</h2>
            
            <h3>每月处理卡片数趋势</h3>
            <div class="chart-container">
                <canvas id="monthlyChart" style="max-height: 400px;"></canvas>
            </div>
            
            <h3>每周处理卡片趋势</h3>
            <div class="chart-container">
                <canvas id="weeklyChart" style="max-height: 400px;"></canvas>
            </div>
            
            <h3>产品处理量分布</h3>
            <div class="chart-container">
                <canvas id="volumeChart" style="max-height: 400px;"></canvas>
            </div>
            
            <div class="chart-row">
                <div class="chart-wrapper">
                    <h4>问题产品分布图</h4>
                    <canvas id="productChart"></canvas>
                </div>
                <div class="chart-wrapper">
                    <h4>完成状态分析</h4>
                    <canvas id="statusChart"></canvas>
                </div>
            </div>
        </section>
        
        <!-- 产品详细统计 -->
        <section>
            <h2>产品详细统计（Top 5）</h2>
            {generate_product_detail_html(safe_get(results, 'top5_products', {}))}
        </section>
        
        <!-- 硬件故障分析 -->
        <section>
            <h2>硬件故障分析</h2>
            
            <!-- 硬件故障汇总统计 -->
            <div class="overview-cards">
                <div class="card fault"><div class="card-number">{safe_get_nested(results, 'hardware_summary', '硬件故障总数', '0')}</div><div class="card-label">硬件故障总数</div></div>
                <div class="card fault"><div class="card-number">{safe_get_nested(results, 'hardware_summary', '已解决数量', '0')}</div><div class="card-label">已解决数量</div></div>
                <div class="card fault"><div class="card-number">{safe_get_nested(results, 'hardware_summary', '未解决数量', '0')}</div><div class="card-label">未解决数量</div></div>
                <div class="card fault"><div class="card-number">{safe_get_nested(results, 'hardware_summary', '解决率', '0%')}</div><div class="card-label">解决率</div></div>
            </div>
            
            <!-- 硬件故障分类分布 -->
            <h3>硬件故障分类分布</h3>
            <div class="chart-container">
                <canvas id="hardwareChart" style="max-height: 400px;"></canvas>
            </div>
            
            <!-- 硬件故障周度趋势 -->
            <h3>硬件故障周度趋势</h3>
            <div class="chart-container">
                <canvas id="hardwareTrendChart" style="max-height: 400px;"></canvas>
            </div>
            
            <button class="anomaly-toggle" onclick="toggleHardwareDetails()">展开/收起硬件故障详细信息</button>
            <div class="anomaly-content" id="hardwareDetails">
                {generate_table_html(safe_get(results, 'hardware_details', {}), ['编号', '标题', '流程状态', '故障等级', '是否已解决', '细分分类', '负责人'], has_links=True)}
            </div>
        </section>
        
        <!-- 人效分析 -->
        <section>
            <h2>人效分析</h2>
            
            <h3>重点关注人员</h3>
            <div class="chart-container">
                <canvas id="efficiencyChart" style="max-height: 400px;"></canvas>
            </div>
            {generate_table_html(safe_get(results, 'efficiency_data', {}), ['创建人', '总卡片数', '已完成数量', '未完成数量', '完成率'], has_links=False)}
            
            <h3>全员工作量统计（Top 10）</h3>
            <div class="chart-container">
                <canvas id="allResponsibleChart" style="max-height: 500px;"></canvas>
            </div>
            {generate_table_html(safe_get(results, 'all_responsible_stats', {}), ['负责人', '总卡片数', '已完成数量', '未完成数量', '完成率'], has_links=False)}
            
            <div class="section-title" style="margin-top: 20px; padding: 15px; background: #E3F2FD; border-radius: 10px;">
                <p style="color: #1976D2; font-size: 0.9em; margin: 0;">
                    💡 说明：多人负责的任务会分别计入每个负责人的工作量，确保统计的准确性和公平性。
                </p>
            </div>
        </section>
        
        <!-- 历史数据概览 -->
        <section>
            <h2>历史数据概览</h2>
            {generate_table_html(safe_get(results, 'historical_overview', {}), ['周期', '运维事件个数', '闭环个数', '解决率', '正在进行中需求个数', '本周完成需求个数'], has_links=False)}
        </section>
        
        <div class="footer">
            <p>📊 报告生成时间: {report_time}</p>
            <p>🔧 分析工具: 长安LCC运营数据分析系统</p>
        </div>
    </div>
    
    <script>
        {newline.join(chart_scripts)}
        
        function toggleAnomalySection() {{
            const content = document.getElementById('anomalyContent');
            content.classList.toggle('show');
        }}
        
        function toggleHardwareDetails() {{
            const content = document.getElementById('hardwareDetails');
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
</html>"""

def main():
    """主函数"""
    # 加载分析结果
    results = load_analysis_results()
    if results is None:
        return
    
    # 生成HTML报告
    html_content = generate_html_report(results)
    
    # 保存报告
    current_date = datetime.now().strftime('%Y%m%d')
    output_file = f'长安LCC运营数据分析报告_{current_date}.html'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ HTML报告已生成: {output_file}")

if __name__ == "__main__":
    main()
