#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import json
import os
from datetime import datetime, timedelta
import re

def load_excel_data(file_path):
    """加载Excel数据"""
    try:
        df = pd.read_excel(file_path)
        print(f"成功加载数据，共 {len(df)} 行")
        print(f"列名: {list(df.columns)}")
        return df
    except Exception as e:
        print(f"加载Excel文件失败: {e}")
        return None

def get_week_range():
    """获取上周四至本周三的时间范围"""
    today = datetime.now()
    # 计算上周四
    days_since_thursday = (today.weekday() + 4) % 7
    last_thursday = today - timedelta(days=days_since_thursday + 7)
    this_wednesday = last_thursday + timedelta(days=6)
    return last_thursday, this_wednesday

def get_current_week_range():
    """获取本周四至下周三的时间范围"""
    today = datetime.now()
    days_since_thursday = (today.weekday() + 4) % 7
    this_thursday = today - timedelta(days=days_since_thursday)
    next_wednesday = this_thursday + timedelta(days=6)
    return this_thursday, next_wednesday

def get_week_identifier(date_str):
    """获取周期标识 (2025-W01格式) - 2025-W25从6.18开始"""
    try:
        if pd.isna(date_str):
            return ""
        
        date_obj = pd.to_datetime(date_str)
        year = date_obj.year
        
        # 2025年特殊处理：W25从6.18开始
        if year == 2025:
            # 2025-W25的开始日期是6.18（周四）
            w25_start = datetime(2025, 6, 18)  # 2025年6月18日周四
            
            if date_obj < w25_start:
                # 6.18之前的日期，按照正常ISO周计算但调整为2025年的周数
                days_since_jan1 = (date_obj - datetime(2025, 1, 1)).days
                week_num = (days_since_jan1 // 7) + 1
                return f"2025-W{week_num:02d}"
            else:
                # 6.18及之后的日期
                days_since_w25 = (date_obj - w25_start).days
                week_num = 25 + (days_since_w25 // 7)
                return f"2025-W{week_num:02d}"
        else:
            # 其他年份按照正常逻辑
            # 找到该日期所在的周四
            days_since_thursday = (date_obj.weekday() + 4) % 7  # 周四为0
            week_thursday = date_obj - timedelta(days=days_since_thursday)
            
            # 计算该年第一个周四
            jan_1 = datetime(year, 1, 1)
            days_to_first_thursday = (3 - jan_1.weekday()) % 7  # 周四是weekday=3
            if days_to_first_thursday == 0 and jan_1.weekday() != 3:
                days_to_first_thursday = 7
            first_thursday = jan_1 + timedelta(days=days_to_first_thursday)
            
            # 计算周数
            days_diff = (week_thursday - first_thursday).days
            week_num = (days_diff // 7) + 1
            
            if week_num < 1:
                prev_year = year - 1
                return f"{prev_year}-W52"  # 简化处理
            
            return f"{year}-W{week_num:02d}"
    except:
        return ""

def detect_anomalies(df):
    """异常检测 - 严格按照要求"""
    anomalies = {
        'c_anomalies': [],
        'r_anomalies': [],
        'k_anomalies': [],
        'classification_anomalies': []
    }
    
    for idx, row in df.iterrows():
        # A列编号，B列标题，C列流程状态，D列类型，E列创建人，R列方向大类，T列细分分类
        number = row.iloc[0] if pd.notna(row.iloc[0]) else ""
        title = str(row.iloc[1]) if pd.notna(row.iloc[1]) else ""
        status = str(row.iloc[2]) if pd.notna(row.iloc[2]) else ""
        card_type = str(row.iloc[3]) if pd.notna(row.iloc[3]) else ""
        creator = str(row.iloc[4]) if pd.notna(row.iloc[4]) else ""
        direction = row.iloc[18] if len(row) > 18 else None  # 方向大类列
        classification = row.iloc[20] if len(row) > 20 else None  # 细分分类列
        
        title_lower = title.lower()
        
        # C2/C3异常检测：标题包含C2/C3且类型应为除需求外的内容，若为需求即为错误
        if any(x in title_lower for x in ['c2', 'c3']):
            if '需求' in card_type:
                level = 'C2' if 'c2' in title_lower else 'C3'
                anomalies['c_anomalies'].append({
                    '编号': number,
                    '标题': title,
                    '故障等级': level,
                    '创建人': creator
                })
        
        # R2/R3异常检测：标题包含R2/R3且类型应为需求，若为其他即为错误
        if any(x in title_lower for x in ['r2', 'r3']):
            if '需求' not in card_type:
                level = 'R2' if 'r2' in title_lower else 'R3'
                anomalies['r_anomalies'].append({
                    '编号': number,
                    '标题': title,
                    '故障等级': level,
                    '创建人': creator
                })
        
        # K2/K3异常检测：标题包含K2/K3且类型应为风险治理，若为其他即为错误
        if any(x in title_lower for x in ['k2', 'k3']):
            if '风险治理' not in card_type:
                level = 'K2' if 'k2' in title_lower else 'K3'
                anomalies['k_anomalies'].append({
                    '编号': number,
                    '标题': title,
                    '故障等级': level,
                    '创建人': creator
                })
        
        # 方向大类、细分分类字段为空：R列和T列为空
        if pd.isna(direction) and pd.isna(classification):
            anomalies['classification_anomalies'].append({
                '编号': number,
                '标题': title,
                '创建人': creator
            })
    
    return anomalies

def analyze_data_overview(df):
    """数据概览统计 - 严格按照要求"""
    last_thursday, this_wednesday = get_week_range()
    current_thursday, next_wednesday = get_current_week_range()
    
    # 计算总周数和平均每周卡片处理量
    df['创建时间'] = pd.to_datetime(df.iloc[:, 5], errors='coerce')
    df['week'] = df['创建时间'].apply(get_week_identifier)
    total_weeks = len([week for week in df['week'].unique() if week and week != ""])
    
    # 涉及产品分布：细分分类列内容各占比计数
    product_distribution = []
    if len(df.columns) > 20:
        product_counts = df.iloc[:, 20].value_counts()
        for product, count in product_counts.items():
            if pd.notna(product):
                percentage = f"{(count/len(df)*100):.1f}%"
                product_distribution.append({
                    'name': str(product),
                    'value': int(count),
                    'percentage': percentage
                })
    
    # 故障统计 - 数据范围改为Excel表中的总范围
    # 总问题数：D列"类型"为除需求和风险治理以外的数量
    task_df = df[~df.iloc[:, 3].isin(['需求', '风险治理'])]
    total_problems = len(task_df)
    
    # 已完成数：D列"类型"为除需求和风险治理以外且C列"流程状态"中除新建，测试中，验证中以外都算已完成
    completed_statuses = task_df[~task_df.iloc[:, 2].isin(['新建', '测试中', '验证中'])]
    completed_problems = len(completed_statuses)
    
    # 问题闭环率：已完成数/总问题数，保留两位小数
    problem_closure_rate = f"{(completed_problems/total_problems*100):.2f}%" if total_problems > 0 else "0.00%"
    
    # 需求统计
    requirement_df = df[df.iloc[:, 3] == '需求']
    total_requirements = len(requirement_df)
    
    # 新增需求：按照时间划分，属于本周的需求即为新增需求
    new_requirements = len(requirement_df[(requirement_df['创建时间'] >= current_thursday) & 
                                        (requirement_df['创建时间'] <= next_wednesday)])
    
    # 进行中需求：C列"流程状态"中除已完成和关闭的数量
    ongoing_requirements = len(requirement_df[~requirement_df.iloc[:, 2].isin(['已完成', '关闭'])])
    
    # 已完成需求：C列"流程状态"中已完成和关闭的数量
    completed_requirements = len(requirement_df[requirement_df.iloc[:, 2].isin(['已完成', '关闭'])])
    
    # 需求闭环率：已完成需求/总需求数
    requirement_closure_rate = f"{(completed_requirements/total_requirements*100):.2f}%" if total_requirements > 0 else "0.00%"
    
    # 风险统计
    risk_df = df[df.iloc[:, 3] == '风险治理']
    total_risks = len(risk_df)
    completed_risks = len(risk_df[risk_df.iloc[:, 2].isin(['已完成', '关闭'])])
    
    # 总卡片数：应该等于总问题数+总需求数+风险治理总数
    total_cards = total_problems + total_requirements + total_risks
    avg_weekly_cards = round(total_cards / total_weeks, 1) if total_weeks > 0 else 0
    
    return {
        '总卡片数': total_cards,
        '平均每周卡片处理量': avg_weekly_cards,
        '总问题数': total_problems,
        '已完成数': completed_problems,
        '问题闭环率': problem_closure_rate,
        '总需求数': total_requirements,
        '新增需求': new_requirements,
        '进行中需求': ongoing_requirements,
        '已完成需求': completed_requirements,
        '需求闭环率': requirement_closure_rate,
        '风险治理总数': total_risks,
        '风险治理完成数量': completed_risks,
        'product_distribution': product_distribution
    }

def analyze_trends(df):
    """趋势分析"""
    df['创建时间'] = pd.to_datetime(df.iloc[:, 5], errors='coerce')
    
    # 每月处理卡片数趋势：将数据按照月份进行分类，按照升序展示
    monthly_data = df.groupby(df['创建时间'].dt.to_period('M')).size().sort_index()
    monthly_trends = [[str(period), int(count)] for period, count in monthly_data.items() if pd.notna(period)]
    
    # 每周处理卡片趋势
    weekly_trends = []
    df['week'] = df['创建时间'].apply(get_week_identifier)
    
    # 按周期分组统计
    for week in df['week'].unique():
        if week and week != "":
            week_data = df[df['week'] == week]
            
            # 问题跟进数（运维事件个数）：D列类型除需求外的数量总和
            maintenance_events = len(week_data[week_data.iloc[:, 3] != '需求'])
            
            # 闭环个数：D列中除需求外且C列流程状态为关闭、已完成、已修复、已分析的数量总和
            closed_events = len(week_data[
                (week_data.iloc[:, 3] != '需求') & 
                (week_data.iloc[:, 2].isin(['关闭', '已完成', '已修复', '已分析']))
            ])
            
            # 问题解决率：闭环个数/问题跟进数
            resolution_rate = round((closed_events/maintenance_events*100), 2) if maintenance_events > 0 else 0
            
            weekly_trends.append({
                '周期': week,
                '问题跟进数': maintenance_events,
                '闭环个数': closed_events,
                '问题解决率': resolution_rate
            })
    
    # 按周期排序
    weekly_trends.sort(key=lambda x: x['周期'])
    
    return monthly_trends, weekly_trends

def analyze_visualizations(df):
    """数据可视化分析"""
    visualizations = {}
    
    # 产品处理量分布：横轴为细分分类列内容，以柱状图进行展示，top3以不同颜色进行展示
    if len(df.columns) > 20:
        product_volume = df.iloc[:, 20].value_counts()
        volume_data = []
        for i, (product, count) in enumerate(product_volume.items()):
            if pd.notna(product):
                volume_data.append({
                    'name': str(product),
                    'value': int(count),
                    'is_top3': i < 3
                })
        visualizations['product_volume'] = volume_data
    
    # 问题产品分布图：对细分分类列进行分析，输出扇形图，top3内容在上方重点展示
    if len(df.columns) > 20:
        product_dist = df.iloc[:, 20].value_counts().head(10)
        dist_data = []
        for i, (product, count) in enumerate(product_dist.items()):
            if pd.notna(product):
                dist_data.append({
                    'name': str(product),
                    'value': int(count),
                    'percentage': f"{(count/len(df)*100):.1f}%",
                    'is_top3': i < 3
                })
        visualizations['product_distribution'] = dist_data
    
    # 完成状态分析：将C列"流程状态"进行分析以环形图进行展示
    status_counts = df.iloc[:, 2].value_counts()
    status_data = []
    for status, count in status_counts.items():
        if pd.notna(status):
            status_data.append({
                'name': str(status),
                'value': int(count)
            })
    visualizations['completion_status'] = status_data
    
    return visualizations

def analyze_hardware_failures(df):
    """硬件故障分析：基于R列方向大类包含"硬件"的内容进行深度分析"""
    hardware_analysis = []
    hardware_details = []
    hardware_summary = {}
    
    if len(df.columns) > 18:
        # 筛选方向大类列包含"硬件"的内容
        hardware_df = df[df.iloc[:, 18].astype(str).str.contains('硬件', na=False)]
        
        print(f"硬件故障分析: 找到 {len(hardware_df)} 条硬件相关记录")
        
        if not hardware_df.empty:
            # 1. 按细分分类统计硬件故障分布
            if len(df.columns) > 20:
                hardware_counts = hardware_df.iloc[:, 20].value_counts()
                for category, count in hardware_counts.items():
                    if pd.notna(category):
                        hardware_analysis.append({
                            'name': str(category),
                            'value': int(count)
                        })
            
            # 2. 硬件故障状态分析
            status_counts = hardware_df.iloc[:, 2].value_counts()  # C列流程状态
            hardware_status = []
            for status, count in status_counts.items():
                if pd.notna(status):
                    hardware_status.append({
                        'status': str(status),
                        'count': int(count),
                        'percentage': f"{(count/len(hardware_df)*100):.1f}%"
                    })
            
            # 3. 硬件故障时间趋势分析
            hardware_df_copy = hardware_df.copy()
            hardware_df_copy['创建时间'] = pd.to_datetime(hardware_df_copy.iloc[:, 5], errors='coerce')
            hardware_df_copy['week'] = hardware_df_copy['创建时间'].apply(get_week_identifier)
            
            hardware_weekly_trends = []
            for week in sorted(hardware_df_copy['week'].unique()):
                if week and week != "":
                    week_hardware = hardware_df_copy[hardware_df_copy['week'] == week]
                    if not week_hardware.empty:
                        # 该周硬件故障数量
                        week_count = len(week_hardware)
                        # 该周已解决的硬件故障
                        week_resolved = len(week_hardware[week_hardware.iloc[:, 2].isin(['已完成', '已分析', '关闭', '已修复'])])
                        # 解决率
                        resolve_rate = (week_resolved/week_count*100) if week_count > 0 else 0
                        
                        hardware_weekly_trends.append({
                            '周期': week,
                            '硬件故障数': week_count,
                            '已解决数': week_resolved,
                            '解决率': f"{resolve_rate:.1f}%"
                        })
            
            # 4. 硬件故障严重程度分析（基于标题中的C2/C3等级）
            severity_analysis = {'C2': 0, 'C3': 0, '其他': 0}
            for _, row in hardware_df.iterrows():
                title = str(row.iloc[1]).lower() if pd.notna(row.iloc[1]) else ''
                if 'c2' in title:
                    severity_analysis['C2'] += 1
                elif 'c3' in title:
                    severity_analysis['C3'] += 1
                else:
                    severity_analysis['其他'] += 1
            
            # 5. 硬件故障负责人分析
            responsible_analysis = hardware_df.iloc[:, 4].value_counts().head(5)  # E列负责人，取前5名
            hardware_responsible = []
            for person, count in responsible_analysis.items():
                if pd.notna(person):
                    hardware_responsible.append({
                        '负责人': str(person),
                        '处理数量': int(count),
                        '占比': f"{(count/len(hardware_df)*100):.1f}%"
                    })
            
            # 6. 硬件故障详细信息（增强版）
            for _, row in hardware_df.iterrows():
                # 判断故障等级
                title = str(row.iloc[1]).lower() if pd.notna(row.iloc[1]) else ''
                if 'c2' in title:
                    severity = 'C2'
                elif 'c3' in title:
                    severity = 'C3'
                else:
                    severity = '一般'
                
                # 判断是否已解决
                status = str(row.iloc[2]) if pd.notna(row.iloc[2]) else ''
                is_resolved = status in ['已完成', '已分析', '关闭', '已修复']
                
                hardware_details.append({
                    '编号': row.iloc[0] if pd.notna(row.iloc[0]) else '',
                    '标题': row.iloc[1] if pd.notna(row.iloc[1]) else '',
                    '流程状态': status,
                    '故障等级': severity,
                    '是否已解决': '是' if is_resolved else '否',
                    '细分分类': row.iloc[20] if len(row) > 20 and pd.notna(row.iloc[20]) else '',
                    '负责人': row.iloc[4] if pd.notna(row.iloc[4]) else '',
                    '创建时间': row.iloc[5] if pd.notna(row.iloc[5]) else ''
                })
            
            # 7. 硬件故障汇总统计
            total_hardware = len(hardware_df)
            resolved_hardware = len(hardware_df[hardware_df.iloc[:, 2].isin(['已完成', '已分析', '关闭', '已修复'])])
            hardware_resolve_rate = (resolved_hardware/total_hardware*100) if total_hardware > 0 else 0
            
            hardware_summary = {
                '硬件故障总数': total_hardware,
                '已解决数量': resolved_hardware,
                '未解决数量': total_hardware - resolved_hardware,
                '解决率': f"{hardware_resolve_rate:.2f}%",
                '状态分布': hardware_status,
                '严重程度分布': severity_analysis,
                '负责人分布': hardware_responsible,
                '周度趋势': hardware_weekly_trends
            }
            
            print(f"硬件故障汇总: 总数{total_hardware}, 已解决{resolved_hardware}, 解决率{hardware_resolve_rate:.1f}%")
    
    return hardware_analysis, hardware_details, hardware_summary

def analyze_product_details(df):
    """产品详细统计模块：筛选T列细分分类top5进行展示"""
    top5_products = []
    
    if len(df.columns) > 20:
        product_counts = df.iloc[:, 20].value_counts().head(5)
        
        for product, count in product_counts.items():
            if pd.notna(product):
                # 获取该产品的相关卡片
                product_df = df[df.iloc[:, 20] == product]
                cards = []
                
                # 展示编号、标题（带链接）、创建人
                for _, row in product_df.head(10).iterrows():
                    cards.append({
                        '编号': row.iloc[0] if pd.notna(row.iloc[0]) else '',
                        '标题': row.iloc[1] if pd.notna(row.iloc[1]) else '',
                        '创建人': row.iloc[4] if pd.notna(row.iloc[4]) else ''
                    })
                
                # 计算占比
                percentage = f"{(count/len(df)*100):.1f}%"
                
                top5_products.append({
                    '产品名称': str(product),
                    '记录数量': int(count),
                    '占比': percentage,
                    '相关卡片': cards
                })
    
    return top5_products

def analyze_efficiency(df):
    """人效分析模块 - 支持多负责人拆分统计"""
    # 聚合字段：E列"负责人"为张星培(v_zhangxingpei)、庹任龙(v_tuorenlong)
    target_users = ['张星培(v_zhangxingpei)', '庹任龙(v_tuorenlong)']
    efficiency_data = []
    
    print("人效分析调试信息：")
    print(f"E列负责人字段的所有唯一值: {df.iloc[:, 4].value_counts().head(10)}")
    
    # 为每个目标用户统计
    for user in target_users:
        user_name = user.split('(')[0]  # 提取用户名部分，如"张星培"
        
        # 查找包含该用户的所有记录（支持多负责人情况）
        # 多负责人可能的分隔符：逗号、分号、顿号等
        user_df = df[df.iloc[:, 4].astype(str).str.contains(user_name, na=False, regex=False)]
        
        print(f"用户 {user}:")
        print(f"  匹配数量: {len(user_df)}")
        
        if not user_df.empty:
            total_cards = len(user_df)
            
            # 判定规则：C列"流程状态"为"已完成"、"已分析"、"关闭" → 记为完成，其余为未完成
            completed_cards = len(user_df[user_df.iloc[:, 2].isin(['已完成', '已分析', '关闭'])])
            uncompleted_cards = total_cards - completed_cards
            
            # 完成率（百分比，保留两位小数）
            completion_rate = round((completed_cards/total_cards*100), 2) if total_cards > 0 else 0.00
            
            efficiency_data.append({
                '创建人': user,
                '总卡片数': total_cards,
                '已完成数量': completed_cards,
                '未完成数量': uncompleted_cards,
                '完成率': f"{completion_rate:.2f}%",
                '完成率数值': completion_rate  # 用于图表
            })
            
            print(f"  最终统计: 总数{total_cards}, 已完成{completed_cards}, 未完成{uncompleted_cards}")
    
    # 添加全员统计（所有负责人的工作量分布）
    all_responsible_stats = analyze_all_responsible_persons(df)
    
    return efficiency_data, all_responsible_stats


def analyze_all_responsible_persons(df):
    """分析所有负责人的工作量分布 - 支持多负责人拆分"""
    responsible_stats = {}
    
    # 遍历所有记录
    for idx, row in df.iterrows():
        responsible_field = str(row.iloc[4]) if pd.notna(row.iloc[4]) else ''
        status = str(row.iloc[2]) if pd.notna(row.iloc[2]) else ''
        
        if not responsible_field or responsible_field == 'nan':
            continue
        
        # 拆分多个负责人（支持多种分隔符）
        # 常见分隔符：逗号、分号、顿号、空格等
        import re
        persons = re.split(r'[,，;；、\s]+', responsible_field)
        
        # 为每个负责人单独统计
        for person in persons:
            person = person.strip()
            if not person:
                continue
            
            # 初始化该负责人的统计数据
            if person not in responsible_stats:
                responsible_stats[person] = {
                    '总卡片数': 0,
                    '已完成数量': 0,
                    '未完成数量': 0
                }
            
            # 累加总数
            responsible_stats[person]['总卡片数'] += 1
            
            # 判断是否完成
            if status in ['已完成', '已分析', '关闭']:
                responsible_stats[person]['已完成数量'] += 1
            else:
                responsible_stats[person]['未完成数量'] += 1
    
    # 计算完成率并排序
    result = []
    for person, stats in responsible_stats.items():
        total = stats['总卡片数']
        completed = stats['已完成数量']
        completion_rate = round((completed/total*100), 2) if total > 0 else 0.00
        
        result.append({
            '负责人': person,
            '总卡片数': total,
            '已完成数量': completed,
            '未完成数量': stats['未完成数量'],
            '完成率': f"{completion_rate:.2f}%",
            '完成率数值': completion_rate
        })
    
    # 按总卡片数降序排序，取前10名
    result.sort(key=lambda x: x['总卡片数'], reverse=True)
    
    print(f"全员统计: 共 {len(result)} 个负责人")
    if result:
        print(f"  Top 3: {result[0]['负责人']}({result[0]['总卡片数']}), {result[1]['负责人']}({result[1]['总卡片数']}), {result[2]['负责人']}({result[2]['总卡片数']})")
    
    return result[:10]  # 返回前10名

def analyze_historical_overview(df):
    """历史数据概览模块"""
    historical_overview = []
    
    df['创建时间'] = pd.to_datetime(df.iloc[:, 5], errors='coerce')
    df['week'] = df['创建时间'].apply(get_week_identifier)
    
    # 获取所有需求数据
    all_requirements = df[df.iloc[:, 3] == '需求'].copy()
    all_requirements['week'] = all_requirements['创建时间'].apply(get_week_identifier)
    
    # 累计已完成需求数
    cumulative_completed = 0
    
    # 按周期分组
    for week in sorted(df['week'].unique()):
        if week and week != "":
            week_data = df[df['week'] == week]
            
            # 运维事件个数：按照D列类型来进行计数，内容除需求、风险治理外，其他数量总和
            maintenance_events = len(week_data[~week_data.iloc[:, 3].isin(['需求', '风险治理'])])
            
            # 闭环个数：D列中除需求外且C列流程状态为关闭、已完成、已修复、已分析的数量总和
            closed_events = len(week_data[
                (week_data.iloc[:, 3] != '需求') & 
                (week_data.iloc[:, 2].isin(['关闭', '已完成', '已修复', '已分析']))
            ])
            
            # 解决率：闭环个数/运维事件个数
            resolution_rate = f"{(closed_events/maintenance_events*100):.2f}%" if maintenance_events > 0 else "0.00%"
            
            # 当前周完成的需求数
            week_completed_requirements = len(week_data[
                (week_data.iloc[:, 3] == '需求') & 
                (week_data.iloc[:, 2].isin(['关闭', '已完成', '已修复', '已分析']))
            ])
            
            # 累计已完成需求数
            cumulative_completed += week_completed_requirements
            
            # 总需求数（固定为19）
            total_requirements = 19
            
            # 正在进行中的需求个数 = 总需求数 - 累计已完成需求数
            ongoing_requirements = total_requirements - cumulative_completed
            
            historical_overview.append({
                '周期': week,
                '运维事件个数': maintenance_events,
                '闭环个数': closed_events,
                '解决率': resolution_rate,
                '正在进行中需求个数': ongoing_requirements,
                '本周完成需求个数': week_completed_requirements  # 改为每周完成数，而不是累计数
            })
    
    return historical_overview

def main():
    """主函数"""
    import sys
    
    # 从命令行参数获取文件路径
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        # 默认使用脚本所在目录的excel-export.xlsx
        script_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(script_dir, 'excel-export.xlsx')
    
    print(f"📁 分析文件: {file_path}")
    
    # 加载数据
    df = load_excel_data(file_path)
    if df is None:
        return
    
    print("开始数据分析...")
    
    # 1. 异常检测
    anomalies = detect_anomalies(df)
    print(f"检测到 C2/C3 异常: {len(anomalies['c_anomalies'])} 项")
    print(f"检测到 R2/R3 异常: {len(anomalies['r_anomalies'])} 项")
    print(f"检测到 K2/K3 异常: {len(anomalies['k_anomalies'])} 项")
    print(f"检测到分类字段为空: {len(anomalies['classification_anomalies'])} 项")
    
    # 2. 数据概览统计
    overview = analyze_data_overview(df)
    print(f"总卡片数: {overview['总卡片数']}")
    
    # 3. 趋势分析
    monthly_trends, weekly_trends = analyze_trends(df)
    print(f"月度趋势数据点: {len(monthly_trends)}")
    print(f"周度趋势数据点: {len(weekly_trends)}")
    
    # 4. 数据可视化
    visualizations = analyze_visualizations(df)
    
    # 5. 硬件故障分析
    hardware_analysis, hardware_details, hardware_summary = analyze_hardware_failures(df)
    print(f"硬件故障分析: {len(hardware_analysis)} 个分类")
    
    # 6. 产品详细统计
    top5_products = analyze_product_details(df)
    print(f"Top5产品: {len(top5_products)} 个")
    
    # 7. 人效分析
    efficiency_data, all_responsible_stats = analyze_efficiency(df)
    print(f"人效分析: {len(efficiency_data)} 个目标用户, {len(all_responsible_stats)} 个全员统计")
    
    # 8. 历史数据概览
    historical_overview = analyze_historical_overview(df)
    print(f"历史数据: {len(historical_overview)} 个周期")
    
    # 保存分析结果
    analysis_results = {
        'anomalies': anomalies,
        'overview': overview,
        'monthly_trends': monthly_trends,
        'weekly_trends': weekly_trends,
        'visualizations': visualizations,
        'hardware_analysis': hardware_analysis,
        'hardware_details': hardware_details,
        'hardware_summary': hardware_summary,
        'top5_products': top5_products,
        'efficiency_data': efficiency_data,
        'all_responsible_stats': all_responsible_stats,  # 新增全员统计
        'historical_overview': historical_overview
    }
    
    # 保存到JSON文件供HTML生成器使用
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, 'analysis_results.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(analysis_results, f, ensure_ascii=False, indent=2, default=str)
    
    print("✅ 数据分析完成，结果已保存到 analysis_results.json")

if __name__ == "__main__":
    main()
