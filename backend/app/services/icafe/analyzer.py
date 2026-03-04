#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
运营数据分析引擎
支持动态字段检测，适配不同格式的Excel文件
"""

import pandas as pd
import json
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple, Any
from loguru import logger

from .config import get_icafe_config


class FieldMapper:
    """动态字段映射器"""
    
    # 字段名称的可能变体（按优先级排序）
    FIELD_VARIANTS = {
        '编号': ['编号', '卡片编号', 'ID', 'id', '序号'],
        '标题': ['标题', '名称', 'title', 'Title', '卡片标题'],
        '流程状态': ['流程状态', '状态', 'status', 'Status', '当前状态'],
        '类型': ['类型', '卡片类型', 'type', 'Type'],
        '负责人': ['负责人', '处理人', '责任人', 'owner', 'Owner', '当前负责人'],
        '创建时间': ['创建时间', '创建日期', 'created', 'Created', '创建于'],
        '创建人': ['创建人', '创建者', 'creator', 'Creator'],
        '方向大类': ['方向大类', '大类', '一级分类', '主分类'],
        '汇总分类': ['汇总分类', '二级分类', '分类汇总'],
        '细分分类': ['细分分类', '三级分类', '详细分类', '产品分类', '产品'],
    }
    
    def __init__(self, columns: List[str]):
        self.columns = list(columns)
        self.field_map: Dict[str, Optional[str]] = {}
        self._build_field_map()
    
    def _build_field_map(self):
        """构建字段映射"""
        columns_lower = {col.lower().strip(): col for col in self.columns}
        
        for field_name, variants in self.FIELD_VARIANTS.items():
            self.field_map[field_name] = None
            for variant in variants:
                # 精确匹配
                if variant in self.columns:
                    self.field_map[field_name] = variant
                    break
                # 忽略大小写匹配
                if variant.lower() in columns_lower:
                    self.field_map[field_name] = columns_lower[variant.lower()]
                    break
                # 包含匹配
                for col in self.columns:
                    if variant in col or variant.lower() in col.lower():
                        self.field_map[field_name] = col
                        break
                if self.field_map[field_name]:
                    break
        
        logger.info(f"字段映射结果: {self.field_map}")
    
    def get(self, field_name: str) -> Optional[str]:
        """获取映射后的实际列名"""
        return self.field_map.get(field_name)
    
    def has(self, field_name: str) -> bool:
        """检查字段是否存在"""
        return self.field_map.get(field_name) is not None


class OperationalAnalyzer:
    """运营数据分析引擎 - 支持动态字段检测"""
    
    def __init__(self):
        self.config = get_icafe_config()
        self.df: Optional[pd.DataFrame] = None
        self.field_mapper: Optional[FieldMapper] = None
    
    def load_excel_data(self, file_path: str) -> Optional[pd.DataFrame]:
        """加载 Excel 数据"""
        try:
            df = pd.read_excel(file_path)
            logger.info(f"成功加载数据，共 {len(df)} 行, {len(df.columns)} 列")
            logger.info(f"列名: {list(df.columns)}")
            
            # 初始化字段映射器
            self.field_mapper = FieldMapper(df.columns)
            self.df = df
            return df
        except Exception as e:
            logger.error(f"加载 Excel 文件失败: {e}")
            return None
    
    def _get_column(self, df: pd.DataFrame, field_name: str) -> Optional[pd.Series]:
        """安全获取列数据"""
        if self.field_mapper is None:
            self.field_mapper = FieldMapper(df.columns)
        
        col_name = self.field_mapper.get(field_name)
        if col_name and col_name in df.columns:
            return df[col_name]
        return None
    
    def _get_value(self, row: pd.Series, field_name: str) -> Any:
        """安全获取行中的字段值"""
        if self.field_mapper is None:
            return None
        col_name = self.field_mapper.get(field_name)
        if col_name and col_name in row.index:
            val = row[col_name]
            return val if pd.notna(val) else None
        return None
    
    def _get_week_range(self) -> Tuple[datetime, datetime]:
        """获取上周四至本周三的时间范围"""
        today = datetime.now()
        days_since_thursday = (today.weekday() + 4) % 7
        last_thursday = today - timedelta(days=days_since_thursday + 7)
        this_wednesday = last_thursday + timedelta(days=6)
        return last_thursday, this_wednesday

    def _get_current_week_range(self) -> Tuple[datetime, datetime]:
        """获取本周四至下周三的时间范围"""
        today = datetime.now()
        days_since_thursday = (today.weekday() + 4) % 7
        this_thursday = today - timedelta(days=days_since_thursday)
        next_wednesday = this_thursday + timedelta(days=6)
        return this_thursday, next_wednesday
    
    def _get_week_identifier(self, date_str) -> str:
        """获取周期标识 (2025-W01格式)"""
        try:
            if pd.isna(date_str):
                return ""
            date_obj = pd.to_datetime(date_str)
            year = date_obj.year
            
            # 简化的周期计算
            week_num = date_obj.isocalendar()[1]
            return f"{year}-W{week_num:02d}"
        except:
            return ""

    def detect_anomalies(self, df: pd.DataFrame) -> Dict[str, List]:
        """异常检测"""
        anomalies = {
            'c_anomalies': [],
            'r_anomalies': [],
            'k_anomalies': [],
            'classification_anomalies': []
        }
        
        for idx, row in df.iterrows():
            number = self._get_value(row, '编号') or ""
            title = str(self._get_value(row, '标题') or "")
            status = str(self._get_value(row, '流程状态') or "")
            card_type = str(self._get_value(row, '类型') or "")
            creator = str(self._get_value(row, '负责人') or "")
            direction = self._get_value(row, '方向大类')
            classification = self._get_value(row, '细分分类')
            
            title_lower = title.lower()
            
            # C2/C3异常检测：标题含C2/C3但类型是需求
            if any(x in title_lower for x in ['c2', 'c3']):
                if '需求' in card_type:
                    level = 'C2' if 'c2' in title_lower else 'C3'
                    anomalies['c_anomalies'].append({
                        '编号': number, '标题': title, '故障等级': level, '创建人': creator
                    })
            
            # R2/R3异常检测
            if any(x in title_lower for x in ['r2', 'r3']):
                if '需求' not in card_type:
                    level = 'R2' if 'r2' in title_lower else 'R3'
                    anomalies['r_anomalies'].append({
                        '编号': number, '标题': title, '故障等级': level, '创建人': creator
                    })
            
            # K2/K3异常检测
            if any(x in title_lower for x in ['k2', 'k3']):
                if '风险治理' not in card_type:
                    level = 'K2' if 'k2' in title_lower else 'K3'
                    anomalies['k_anomalies'].append({
                        '编号': number, '标题': title, '故障等级': level, '创建人': creator
                    })
            
            # 分类字段为空
            if direction is None and classification is None:
                anomalies['classification_anomalies'].append({
                    '编号': number, '标题': title, '创建人': creator
                })
        
        return anomalies

    def analyze_data_overview(self, df: pd.DataFrame) -> Dict[str, Any]:
        """数据概览统计"""
        current_thursday, next_wednesday = self._get_current_week_range()
        
        # 获取创建时间列
        create_time_col = self._get_column(df, '创建时间')
        if create_time_col is not None:
            df['_创建时间'] = pd.to_datetime(create_time_col, errors='coerce')
        else:
            df['_创建时间'] = pd.NaT
        
        df['_week'] = df['_创建时间'].apply(self._get_week_identifier)
        total_weeks = len([week for week in df['_week'].unique() if week and week != ""])
        if total_weeks == 0:
            total_weeks = 1
        
        # 涉及产品分布
        product_distribution = []
        product_col = self._get_column(df, '细分分类')
        if product_col is not None:
            product_counts = product_col.value_counts()
            for product, count in product_counts.items():
                if pd.notna(product):
                    percentage = f"{(count/len(df)*100):.1f}%"
                    product_distribution.append({
                        'name': str(product), 'value': int(count), 'percentage': percentage
                    })
        
        # 获取类型和状态列
        type_col = self._get_column(df, '类型')
        status_col = self._get_column(df, '流程状态')
        
        # 故障统计（非需求、非风险治理的卡片）
        if type_col is not None:
            task_df = df[~type_col.isin(['需求', '风险治理'])]
        else:
            task_df = df
        
        total_problems = len(task_df)
        if status_col is not None and total_problems > 0:
            task_status = status_col.loc[task_df.index]
            completed_statuses = task_df[~task_status.isin(['新建', '测试中', '验证中'])]
            completed_problems = len(completed_statuses)
        else:
            completed_problems = 0
        problem_closure_rate = f"{(completed_problems/total_problems*100):.2f}%" if total_problems > 0 else "0.00%"

        # 需求统计
        if type_col is not None:
            requirement_df = df[type_col == '需求']
        else:
            requirement_df = pd.DataFrame()
        
        total_requirements = len(requirement_df)
        if total_requirements > 0 and status_col is not None:
            req_status = status_col.loc[requirement_df.index]
            new_requirements = len(requirement_df[
                (requirement_df['_创建时间'] >= current_thursday) & 
                (requirement_df['_创建时间'] <= next_wednesday)
            ])
            ongoing_requirements = len(requirement_df[~req_status.isin(['已完成', '关闭'])])
            completed_requirements = len(requirement_df[req_status.isin(['已完成', '关闭'])])
        else:
            new_requirements = 0
            ongoing_requirements = 0
            completed_requirements = 0
        requirement_closure_rate = f"{(completed_requirements/total_requirements*100):.2f}%" if total_requirements > 0 else "0.00%"
        
        # 风险统计
        if type_col is not None:
            risk_df = df[type_col == '风险治理']
        else:
            risk_df = pd.DataFrame()
        
        total_risks = len(risk_df)
        if total_risks > 0 and status_col is not None:
            risk_status = status_col.loc[risk_df.index]
            completed_risks = len(risk_df[risk_status.isin(['已完成', '关闭'])])
        else:
            completed_risks = 0
        
        total_cards = len(df)
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

    def analyze_trends(self, df: pd.DataFrame) -> Tuple[List, List, List, List]:
        """趋势分析"""
        # 确保创建时间列存在
        create_time_col = self._get_column(df, '创建时间')
        if create_time_col is not None:
            df['_创建时间'] = pd.to_datetime(create_time_col, errors='coerce')
        else:
            df['_创建时间'] = pd.NaT
        
        # 每月处理卡片数趋势
        valid_dates = df[df['_创建时间'].notna()]
        if not valid_dates.empty:
            monthly_data = valid_dates.groupby(valid_dates['_创建时间'].dt.to_period('M')).size().sort_index()
            monthly_trends = [[str(period), int(count)] for period, count in monthly_data.items() if pd.notna(period)]
        else:
            monthly_trends = []
        
        # 运维事件每月统计
        maintenance_monthly_data = []
        summary_col = self._get_column(df, '汇总分类')
        if summary_col is not None:
            maintenance_df = df[summary_col.astype(str).str.contains('运维事件', na=False)]
            if not maintenance_df.empty and '_创建时间' in maintenance_df.columns:
                valid_maintenance = maintenance_df[maintenance_df['_创建时间'].notna()]
                if not valid_maintenance.empty:
                    maintenance_monthly = valid_maintenance.groupby(valid_maintenance['_创建时间'].dt.to_period('M')).size().sort_index()
                    maintenance_monthly_data = [[str(period), int(count)] for period, count in maintenance_monthly.items() if pd.notna(period)]

        # 每天卡片数量统计
        if not valid_dates.empty:
            daily_data = valid_dates.groupby(valid_dates['_创建时间'].dt.date).size().sort_index()
            daily_trends = [[str(date), int(count)] for date, count in daily_data.items() if pd.notna(date)]
        else:
            daily_trends = []
        
        # 每周处理卡片趋势
        weekly_trends = []
        df['_week'] = df['_创建时间'].apply(self._get_week_identifier)
        type_col = self._get_column(df, '类型')
        status_col = self._get_column(df, '流程状态')
        
        for week in df['_week'].unique():
            if week and week != "":
                week_data = df[df['_week'] == week]
                if type_col is not None:
                    week_type = type_col.loc[week_data.index]
                    maintenance_events = len(week_data[week_type != '需求'])
                    if status_col is not None:
                        week_status = status_col.loc[week_data.index]
                        closed_events = len(week_data[
                            (week_type != '需求') & 
                            (week_status.isin(['关闭', '已完成', '已修复', '已分析']))
                        ])
                    else:
                        closed_events = 0
                else:
                    maintenance_events = len(week_data)
                    closed_events = 0
                
                resolution_rate = round((closed_events/maintenance_events*100), 2) if maintenance_events > 0 else 0
                weekly_trends.append({
                    '周期': week,
                    '问题跟进数': maintenance_events,
                    '闭环个数': closed_events,
                    '问题解决率': resolution_rate
                })
        
        weekly_trends.sort(key=lambda x: x['周期'])
        return monthly_trends, daily_trends, weekly_trends, maintenance_monthly_data
    
    def analyze_visualizations(self, df: pd.DataFrame) -> Dict[str, List]:
        """数据可视化分析"""
        visualizations = {}
        
        # 产品处理量分布（细分分类）
        product_col = self._get_column(df, '细分分类')
        if product_col is not None:
            product_volume = product_col.value_counts()
            volume_data = []
            for i, (product, count) in enumerate(product_volume.items()):
                if pd.notna(product):
                    volume_data.append({'name': str(product), 'value': int(count), 'is_top3': i < 3})
            visualizations['product_volume'] = volume_data
            
            # 问题产品分布图 Top 10
            product_dist = product_col.value_counts().head(10)
            dist_data = []
            for i, (product, count) in enumerate(product_dist.items()):
                if pd.notna(product):
                    dist_data.append({
                        'name': str(product), 'value': int(count),
                        'percentage': f"{(count/len(df)*100):.1f}%", 'is_top3': i < 3
                    })
            visualizations['product_distribution'] = dist_data
        else:
            visualizations['product_volume'] = []
            visualizations['product_distribution'] = []
        
        # 汇总分类分布
        summary_col = self._get_column(df, '汇总分类')
        summary_classification_data = []
        if summary_col is not None:
            summary_counts = summary_col.value_counts()
            for category, count in summary_counts.items():
                if pd.notna(category):
                    summary_classification_data.append({
                        'name': str(category), 'value': int(count),
                        'percentage': f"{(count/len(df)*100):.1f}%"
                    })
        visualizations['summary_classification'] = summary_classification_data
        
        # 完成状态分析
        status_col = self._get_column(df, '流程状态')
        status_data = []
        if status_col is not None:
            status_counts = status_col.value_counts()
            for status, count in status_counts.items():
                if pd.notna(status):
                    status_data.append({'name': str(status), 'value': int(count)})
        visualizations['completion_status'] = status_data
        
        return visualizations


    def analyze_hardware_failures(self, df: pd.DataFrame) -> Tuple[List, List, Dict]:
        """硬件故障分析"""
        hardware_analysis = []
        hardware_details = []
        hardware_summary = {}
        
        # 使用方向大类字段检测硬件相关记录
        direction_col = self._get_column(df, '方向大类')
        if direction_col is None:
            logger.info("未找到方向大类字段，跳过硬件故障分析")
            return hardware_analysis, hardware_details, hardware_summary
        
        hardware_df = df[direction_col.astype(str).str.contains('硬件', na=False)]
        logger.info(f"硬件故障分析: 找到 {len(hardware_df)} 条硬件相关记录")
        
        if hardware_df.empty:
            return hardware_analysis, hardware_details, hardware_summary
        
        # 按细分分类统计
        product_col = self._get_column(df, '细分分类')
        if product_col is not None:
            hardware_product = product_col.loc[hardware_df.index]
            hardware_counts = hardware_product.value_counts()
            for category, count in hardware_counts.items():
                if pd.notna(category):
                    hardware_analysis.append({'name': str(category), 'value': int(count)})
        
        # 状态分析
        status_col = self._get_column(df, '流程状态')
        hardware_status = []
        if status_col is not None:
            hw_status = status_col.loc[hardware_df.index]
            status_counts = hw_status.value_counts()
            for status, count in status_counts.items():
                if pd.notna(status):
                    hardware_status.append({
                        'status': str(status), 'count': int(count),
                        'percentage': f"{(count/len(hardware_df)*100):.1f}%"
                    })
        
        # 周度趋势
        create_time_col = self._get_column(df, '创建时间')
        hardware_weekly_trends = []
        if create_time_col is not None:
            hardware_df_copy = hardware_df.copy()
            hardware_df_copy['_创建时间'] = pd.to_datetime(create_time_col.loc[hardware_df.index], errors='coerce')
            hardware_df_copy['_week'] = hardware_df_copy['_创建时间'].apply(self._get_week_identifier)
            
            for week in sorted(hardware_df_copy['_week'].unique()):
                if week and week != "":
                    week_hardware = hardware_df_copy[hardware_df_copy['_week'] == week]
                    if not week_hardware.empty:
                        week_count = len(week_hardware)
                        if status_col is not None:
                            week_hw_status = status_col.loc[week_hardware.index]
                            week_resolved = len(week_hardware[week_hw_status.isin(['已完成', '已分析', '关闭', '已修复'])])
                        else:
                            week_resolved = 0
                        resolve_rate = (week_resolved/week_count*100) if week_count > 0 else 0
                        hardware_weekly_trends.append({
                            '周期': week, '硬件故障数': week_count,
                            '已解决数': week_resolved, '解决率': f"{resolve_rate:.1f}%"
                        })
        
        # 严重程度分析
        severity_analysis = {'C2': 0, 'C3': 0, '其他': 0}
        for idx, row in hardware_df.iterrows():
            title = str(self._get_value(row, '标题') or '').lower()
            if 'c2' in title:
                severity_analysis['C2'] += 1
            elif 'c3' in title:
                severity_analysis['C3'] += 1
            else:
                severity_analysis['其他'] += 1

        # 负责人分析
        owner_col = self._get_column(df, '负责人')
        hardware_responsible = []
        if owner_col is not None:
            hw_owner = owner_col.loc[hardware_df.index]
            responsible_analysis = hw_owner.value_counts().head(5)
            for person, count in responsible_analysis.items():
                if pd.notna(person):
                    hardware_responsible.append({
                        '负责人': str(person), '处理数量': int(count),
                        '占比': f"{(count/len(hardware_df)*100):.1f}%"
                    })
        
        # 详细信息
        for idx, row in hardware_df.iterrows():
            title = str(self._get_value(row, '标题') or '').lower()
            severity = 'C2' if 'c2' in title else ('C3' if 'c3' in title else '一般')
            status = str(self._get_value(row, '流程状态') or '')
            is_resolved = status in ['已完成', '已分析', '关闭', '已修复']
            
            hardware_details.append({
                '编号': self._get_value(row, '编号') or '',
                '标题': self._get_value(row, '标题') or '',
                '流程状态': status, '故障等级': severity,
                '是否已解决': '是' if is_resolved else '否',
                '细分分类': self._get_value(row, '细分分类') or '',
                '负责人': self._get_value(row, '负责人') or '',
                '创建时间': self._get_value(row, '创建时间') or ''
            })
        
        # 汇总统计
        total_hardware = len(hardware_df)
        if status_col is not None:
            hw_status_all = status_col.loc[hardware_df.index]
            resolved_hardware = len(hardware_df[hw_status_all.isin(['已完成', '已分析', '关闭', '已修复'])])
        else:
            resolved_hardware = 0
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
        
        return hardware_analysis, hardware_details, hardware_summary

    def analyze_product_details(self, df: pd.DataFrame) -> List[Dict]:
        """产品详细统计 Top 5"""
        top5_products = []
        
        product_col = self._get_column(df, '细分分类')
        if product_col is None:
            return top5_products
        
        product_counts = product_col.value_counts().head(5)
        
        for product, count in product_counts.items():
            if pd.notna(product):
                product_df = df[product_col == product]
                cards = []
                for idx, row in product_df.head(10).iterrows():
                    cards.append({
                        '编号': self._get_value(row, '编号') or '',
                        '标题': self._get_value(row, '标题') or '',
                        '创建人': self._get_value(row, '负责人') or ''
                    })
                
                percentage = f"{(count/len(df)*100):.1f}%"
                top5_products.append({
                    '产品名称': str(product),
                    '记录数量': int(count),
                    '占比': percentage,
                    '相关卡片': cards
                })
        
        return top5_products

    
    def analyze_efficiency(self, df: pd.DataFrame) -> List[Dict]:
        """人效分析 - 分析所有负责人"""
        efficiency_data = []
        
        owner_col = self._get_column(df, '负责人')
        status_col = self._get_column(df, '流程状态')
        
        if owner_col is None:
            return efficiency_data
        
        # 获取所有唯一的负责人（按出现频率排序）
        all_users = owner_col.value_counts()
        
        for user, _ in all_users.items():
            if pd.isna(user) or user == '':
                continue
            
            # 精确匹配
            user_df_exact = df[owner_col == user]
            # 模糊匹配（用户名前缀）
            user_prefix = str(user).split('(')[0]
            user_df_contains = df[owner_col.astype(str).str.contains(user_prefix, na=False)]
            user_df = user_df_contains if len(user_df_contains) > len(user_df_exact) else user_df_exact
            
            if not user_df.empty:
                total_cards = len(user_df)
                if status_col is not None:
                    user_status = status_col.loc[user_df.index]
                    completed_cards = len(user_df[user_status.isin(['已完成', '已分析', '关闭'])])
                else:
                    completed_cards = 0
                uncompleted_cards = total_cards - completed_cards
                completion_rate = round((completed_cards/total_cards*100), 2) if total_cards > 0 else 0.00
                
                efficiency_data.append({
                    '创建人': str(user),
                    '总卡片数': total_cards,
                    '已完成数量': completed_cards,
                    '未完成数量': uncompleted_cards,
                    '完成率': f"{completion_rate:.2f}%",
                    '完成率数值': completion_rate
                })
        
        # 按完成数量降序排序
        efficiency_data.sort(key=lambda x: x['已完成数量'], reverse=True)
        
        return efficiency_data
    
    def analyze_historical_overview(self, df: pd.DataFrame) -> List[Dict]:
        """历史数据概览"""
        historical_overview = []
        
        create_time_col = self._get_column(df, '创建时间')
        type_col = self._get_column(df, '类型')
        status_col = self._get_column(df, '流程状态')
        
        if create_time_col is None:
            return historical_overview
        
        df['_创建时间'] = pd.to_datetime(create_time_col, errors='coerce')
        df['_week'] = df['_创建时间'].apply(self._get_week_identifier)
        
        cumulative_completed = 0
        
        for week in sorted(df['_week'].unique()):
            if week and week != "":
                week_data = df[df['_week'] == week]
                
                if type_col is not None:
                    week_type = type_col.loc[week_data.index]
                    maintenance_events = len(week_data[~week_type.isin(['需求', '风险治理'])])
                    
                    if status_col is not None:
                        week_status = status_col.loc[week_data.index]
                        closed_events = len(week_data[
                            (~week_type.isin(['需求', '风险治理'])) & 
                            (week_status.isin(['关闭', '已完成', '已修复', '已分析']))
                        ])
                        week_completed_requirements = len(week_data[
                            (week_type == '需求') & 
                            (week_status.isin(['关闭', '已完成', '已修复', '已分析']))
                        ])
                    else:
                        closed_events = 0
                        week_completed_requirements = 0
                else:
                    maintenance_events = len(week_data)
                    closed_events = 0
                    week_completed_requirements = 0
                
                resolution_rate = f"{(closed_events/maintenance_events*100):.2f}%" if maintenance_events > 0 else "0.00%"
                
                cumulative_completed += week_completed_requirements
                total_requirements = 19  # 可配置
                ongoing_requirements = max(0, total_requirements - cumulative_completed)
                
                historical_overview.append({
                    '周期': week,
                    '运维事件个数': maintenance_events,
                    '闭环个数': closed_events,
                    '解决率': resolution_rate,
                    '正在进行中需求个数': ongoing_requirements,
                    '本周完成需求个数': week_completed_requirements
                })
        
        return historical_overview


    def analyze(self, file_path: str) -> Dict[str, Any]:
        """执行完整分析流程"""
        logger.info(f"开始分析文件: {file_path}")
        
        # 加载数据
        df = self.load_excel_data(file_path)
        if df is None:
            raise ValueError(f"无法加载文件: {file_path}")
        
        logger.info("开始数据分析...")
        
        # 1. 异常检测
        anomalies = self.detect_anomalies(df)
        logger.info(f"检测到 C2/C3 异常: {len(anomalies['c_anomalies'])} 项")
        logger.info(f"检测到 R2/R3 异常: {len(anomalies['r_anomalies'])} 项")
        logger.info(f"检测到 K2/K3 异常: {len(anomalies['k_anomalies'])} 项")
        logger.info(f"检测到分类字段为空: {len(anomalies['classification_anomalies'])} 项")
        
        # 2. 数据概览统计
        overview = self.analyze_data_overview(df)
        logger.info(f"总卡片数: {overview['总卡片数']}")
        
        # 3. 趋势分析
        monthly_trends, daily_trends, weekly_trends, maintenance_monthly_data = self.analyze_trends(df)
        logger.info(f"月度趋势数据点: {len(monthly_trends)}")
        logger.info(f"运维事件月度趋势数据点: {len(maintenance_monthly_data)}")
        logger.info(f"每日趋势数据点: {len(daily_trends)}")
        logger.info(f"周度趋势数据点: {len(weekly_trends)}")
        
        # 4. 数据可视化
        visualizations = self.analyze_visualizations(df)
        
        # 5. 硬件故障分析
        hardware_analysis, hardware_details, hardware_summary = self.analyze_hardware_failures(df)
        logger.info(f"硬件故障分析: {len(hardware_analysis)} 个分类")
        
        # 6. 产品详细统计
        top5_products = self.analyze_product_details(df)
        logger.info(f"Top5产品: {len(top5_products)} 个")
        
        # 7. 人效分析
        efficiency_data = self.analyze_efficiency(df)
        logger.info(f"人效分析: {len(efficiency_data)} 个用户")
        
        # 8. 历史数据概览
        historical_overview = self.analyze_historical_overview(df)
        logger.info(f"历史数据: {len(historical_overview)} 个周期")
        
        # 汇总结果
        analysis_results = {
            'anomalies': anomalies,
            'overview': overview,
            'monthly_trends': monthly_trends,
            'maintenance_monthly_trends': maintenance_monthly_data,
            'daily_trends': daily_trends,
            'weekly_trends': weekly_trends,
            'visualizations': visualizations,
            'hardware_analysis': hardware_analysis,
            'hardware_details': hardware_details,
            'hardware_summary': hardware_summary,
            'top5_products': top5_products,
            'efficiency_data': efficiency_data,
            'historical_overview': historical_overview
        }
        
        logger.info("数据分析完成")
        return analysis_results
