#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
运营数据分析引擎
支持动态字段检测，适配不同格式的Excel文件
"""

import pandas as pd
import json
import os
import re
from collections import Counter
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
        '有感事件': ['有感事件', '有感', '感知事件'],
        '是否升级到研或OP': ['是否升级到研或OP', '升级到研或OP', '是否升级', '升级到RD'],
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

    # ── 终态状态集合（isFinishedStatus=True 对应的流程状态）──
    FINISHED_STATUSES = {'已完成', '关闭', '已修复', '已分析', '已解决'}

    def analyze_data_overview(self, df: pd.DataFrame) -> Dict[str, Any]:
        """数据概览统计"""
        current_thursday, next_wednesday = self._get_current_week_range()

        # 确保创建时间列存在
        create_time_col = self._get_column(df, '创建时间')
        if create_time_col is not None:
            df['_创建时间'] = pd.to_datetime(create_time_col, errors='coerce')
        else:
            df['_创建时间'] = pd.NaT

        df['_week'] = df['_创建时间'].apply(self._get_week_identifier)
        total_weeks = len([w for w in df['_week'].unique() if w and w != ""])
        if total_weeks == 0:
            total_weeks = 1

        # 产品分布（多值拆分）
        product_distribution = []
        product_col = self._get_column(df, '细分分类')
        if product_col is not None:
            product_counter: Counter = Counter()
            for raw_value in product_col:
                if pd.isna(raw_value) or str(raw_value).strip() == '':
                    continue
                for part in re.split(r'[,，;；、\|]+', str(raw_value).strip()):
                    part = part.strip()
                    if part:
                        product_counter[part] += 1
            total_product_refs = sum(product_counter.values())
            for product, count in product_counter.most_common():
                pct = f"{(count / max(total_product_refs, 1) * 100):.1f}%"
                product_distribution.append({'name': str(product), 'value': int(count), 'percentage': pct})

        # 类型列、状态列
        type_col = self._get_column(df, '类型')
        status_col = self._get_column(df, '流程状态')

        # 故障统计（Task / Bug 类，即非需求、非风险治理、非团队事务）
        exclude_types = {'需求', '风险治理', '团队事务', 'Epic'}
        if type_col is not None:
            task_mask = ~type_col.isin(exclude_types)
            task_df = df[task_mask]
        else:
            task_df = df

        total_problems = len(task_df)
        if status_col is not None and total_problems > 0:
            task_status = status_col.loc[task_df.index]
            completed_problems = int(task_status.isin(self.FINISHED_STATUSES).sum())
        else:
            completed_problems = 0
        problem_closure_rate = f"{(completed_problems / total_problems * 100):.1f}%" if total_problems > 0 else "0.0%"

        # 需求统计
        requirement_df = df[type_col == '需求'] if type_col is not None else pd.DataFrame()
        total_requirements = len(requirement_df)
        if total_requirements > 0 and status_col is not None:
            req_status = status_col.loc[requirement_df.index]
            new_requirements = int(len(requirement_df[
                (requirement_df['_创建时间'] >= current_thursday) &
                (requirement_df['_创建时间'] <= next_wednesday)
            ]))
            ongoing_requirements = int((~req_status.isin(self.FINISHED_STATUSES)).sum())
            completed_requirements = int(req_status.isin(self.FINISHED_STATUSES).sum())
        else:
            new_requirements = ongoing_requirements = completed_requirements = 0
        requirement_closure_rate = f"{(completed_requirements / total_requirements * 100):.1f}%" if total_requirements > 0 else "0.0%"

        # 风险治理统计
        risk_df = df[type_col == '风险治理'] if type_col is not None else pd.DataFrame()
        total_risks = len(risk_df)
        if total_risks > 0 and status_col is not None:
            risk_status = status_col.loc[risk_df.index]
            completed_risks = int(risk_status.isin(self.FINISHED_STATUSES).sum())
        else:
            completed_risks = 0

        total_cards = len(df)
        avg_weekly_cards = round(total_cards / total_weeks, 1) if total_weeks > 0 else 0

        # ── 新增：有感事件统计 ──
        feels_col = self._get_column(df, '有感事件') if self.field_mapper and self.field_mapper.has('有感事件') else None
        feels_col_raw = None
        for col in df.columns:
            if '有感' in col:
                feels_col_raw = df[col]
                break
        if feels_col_raw is not None:
            feels_yes = int((feels_col_raw.astype(str).str.strip() == '是').sum())
            feels_no  = int((feels_col_raw.astype(str).str.strip() == '否').sum())
            feels_empty = total_cards - feels_yes - feels_no
            feels_rate = f"{(feels_yes / total_cards * 100):.1f}%" if total_cards > 0 else "0.0%"
        else:
            feels_yes = feels_no = feels_empty = 0
            feels_rate = "N/A"

        # ── 新增：升级到研或OP 统计 ──
        escalate_col_raw = None
        for col in df.columns:
            if '升级' in col and 'OP' in col:
                escalate_col_raw = df[col]
                break
        if escalate_col_raw is not None:
            escalated = int((escalate_col_raw.astype(str).str.strip() == '是').sum())
            escalate_rate = f"{(escalated / total_cards * 100):.1f}%" if total_cards > 0 else "0.0%"
        else:
            escalated = 0
            escalate_rate = "N/A"

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
            '有感事件数': feels_yes,
            '无感事件数': feels_no,
            '有感率': feels_rate,
            '升级到研或OP数': escalated,
            '升级率': escalate_rate,
            '有感字段填写率': f"{((feels_yes + feels_no) / total_cards * 100):.1f}%" if total_cards > 0 else "0.0%",
            'product_distribution': product_distribution,
        }

    def analyze_trends(self, df: pd.DataFrame) -> Tuple[List, List, List]:
        """趋势分析（X 轴粒度根据数据跨度自适应）"""
        from datetime import timedelta
        create_time_col = self._get_column(df, '创建时间')
        if create_time_col is not None:
            df['_创建时间'] = pd.to_datetime(create_time_col, errors='coerce')
        else:
            df['_创建时间'] = pd.NaT

        status_col = self._get_column(df, '流程状态')

        valid_dates = df[df['_创建时间'].notna()].copy()

        # 计算数据跨度（天数）
        date_span_days = 0
        if not valid_dates.empty:
            date_min = valid_dates['_创建时间'].min()
            date_max = valid_dates['_创建时间'].max()
            date_span_days = (date_max - date_min).days

        # 每月/每日处理卡片数趋势（跨度 < 14 天时改用日粒度）
        monthly_trends = []
        use_daily_for_monthly = date_span_days < 14
        if not valid_dates.empty:
            if use_daily_for_monthly:
                valid_dates['_period'] = valid_dates['_创建时间'].dt.strftime('%m/%d')
                period_key = '_period'
            else:
                valid_dates['_month'] = valid_dates['_创建时间'].dt.to_period('M')
                period_key = '_month'

            for period, grp in valid_dates.groupby(period_key, sort=True):
                total = len(grp)
                if status_col is not None:
                    finished = int(status_col.loc[grp.index].isin(self.FINISHED_STATUSES).sum())
                else:
                    finished = 0
                monthly_trends.append([
                    str(period), total, finished,
                    round(finished / total * 100, 1) if total > 0 else 0
                ])
            if not use_daily_for_monthly:
                monthly_trends.sort(key=lambda x: x[0])

        # 运维事件统计（跨度 < 14 天时按日，否则按月）
        maintenance_monthly_data = []
        summary_col = self._get_column(df, '汇总分类')
        if summary_col is not None and not valid_dates.empty:
            maint_mask = summary_col.astype(str).str.contains('运维事件', na=False)
            maint_df = valid_dates[maint_mask.loc[valid_dates.index].values]
            if not maint_df.empty:
                if use_daily_for_monthly:
                    for period, grp in maint_df.groupby(maint_df['_创建时间'].dt.strftime('%m/%d'), sort=True):
                        maintenance_monthly_data.append([str(period), len(grp)])
                else:
                    for period, grp in maint_df.groupby(maint_df['_创建时间'].dt.to_period('M')):
                        maintenance_monthly_data.append([str(period), len(grp)])
                    maintenance_monthly_data.sort(key=lambda x: x[0])

        # 每周/每日处理卡片趋势（跨度 < 28 天时改用日粒度）
        weekly_trends = []
        use_daily_for_weekly = date_span_days < 28

        # 找有感事件列
        feels_col_name = None
        for col in df.columns:
            if '有感' in col:
                feels_col_name = col
                break

        if use_daily_for_weekly:
            # 按日分组
            df['_day'] = df['_创建时间'].apply(
                lambda x: x.strftime('%m/%d') if pd.notna(x) else ''
            )
            for day_label, day_data in df[df['_day'] != ''].groupby('_day', sort=True):
                total = len(day_data)
                closed_events = 0
                if status_col is not None:
                    closed_events = int(status_col.loc[day_data.index].isin(self.FINISHED_STATUSES).sum())
                feels_count = 0
                if feels_col_name:
                    feels_count = int(
                        (df.loc[day_data.index, feels_col_name].astype(str).str.strip() == '是').sum()
                    )
                resolution_rate = round(closed_events / total * 100, 1) if total > 0 else 0
                weekly_trends.append({
                    '周期': day_label,
                    '周期标签': day_label,
                    '问题跟进数': total,
                    '闭环个数': closed_events,
                    '问题解决率': f"{resolution_rate}%",
                    '有感事件数': feels_count,
                })
        else:
            df['_week'] = df['_创建时间'].apply(self._get_week_identifier)
            for week in df['_week'].unique():
                if not week or week == "":
                    continue
                week_data = df[df['_week'] == week]
                total = len(week_data)

                if status_col is not None:
                    closed_events = int(status_col.loc[week_data.index].isin(self.FINISHED_STATUSES).sum())
                else:
                    closed_events = 0

                feels_this_week = 0
                if feels_col_name:
                    feels_this_week = int(
                        (df.loc[week_data.index, feels_col_name].astype(str).str.strip() == '是').sum()
                    )

                resolution_rate = round(closed_events / total * 100, 1) if total > 0 else 0

                try:
                    year, w = week.split('-W')
                    from datetime import date
                    week_start = date.fromisocalendar(int(year), int(w), 1)
                    week_end = date.fromisocalendar(int(year), int(w), 7)
                    week_label = f"{week_start.strftime('%m/%d')}-{week_end.strftime('%m/%d')}"
                except Exception:
                    week_label = week

                weekly_trends.append({
                    '周期': week,
                    '周期标签': week_label,
                    '问题跟进数': total,
                    '闭环个数': closed_events,
                    '问题解决率': f"{resolution_rate}%",
                    '有感事件数': feels_this_week,
                })

            weekly_trends.sort(key=lambda x: x['周期'])

        return monthly_trends, weekly_trends, maintenance_monthly_data
    
    def analyze_visualizations(self, df: pd.DataFrame) -> Dict[str, List]:
        """数据可视化分析"""
        visualizations = {}

        # 产品处理量分布（细分分类，支持多值拆分）
        product_col = self._get_column(df, '细分分类')
        if product_col is not None:
            product_counter: Counter = Counter()
            for raw_value in product_col:
                if pd.isna(raw_value) or str(raw_value).strip() == '':
                    continue
                # 用逗号、顿号、分号等拆分多产品
                parts = re.split(r'[,，;；、]+', str(raw_value).strip())
                for part in parts:
                    part = part.strip()
                    if part:
                        product_counter[part] += 1

            volume_data = []
            for i, (product, count) in enumerate(product_counter.most_common()):
                volume_data.append({'name': product, 'value': count, 'is_top3': i < 3})
            visualizations['product_volume'] = volume_data

            # 问题产品分布图 Top10
            dist_data = []
            total_count = sum(product_counter.values())
            for i, (product, count) in enumerate(product_counter.most_common(10)):
                dist_data.append({
                    'name': product, 'value': count,
                    'percentage': f"{(count/total_count*100):.1f}%", 'is_top3': i < 3
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

    def analyze_product_details(self, df: pd.DataFrame) -> List[Dict]:
        """产品详细统计 Top5（支持多值细分分类拆分）"""
        product_col = self._get_column(df, '细分分类')
        if product_col is None:
            return []

        # 用与 analyze_visualizations 相同的拆分逻辑，收集每个产品对应的行索引
        product_indices: dict = {}
        for idx, raw_value in product_col.items():
            if pd.isna(raw_value) or str(raw_value).strip() == '':
                continue
            parts = re.split(r'[,，;；、]+', str(raw_value).strip())
            for part in parts:
                part = part.strip()
                if not part:
                    continue
                if part not in product_indices:
                    product_indices[part] = []
                product_indices[part].append(idx)

        # 按出现次数排序，取 Top 5
        sorted_products = sorted(product_indices.items(), key=lambda x: len(x[1]), reverse=True)[:5]
        total_cards = len(df)
        top5_products = []

        for product_name, indices in sorted_products:
            count = len(indices)
            percentage = f"{(count / total_cards * 100):.1f}%"

            # 取前 10 条相关卡片
            cards = []
            for idx in indices[:10]:
                row = df.loc[idx]
                cards.append({
                    '编号': self._get_value(row, '编号') or '',
                    '标题': self._get_value(row, '标题') or '',
                    '创建人': self._get_value(row, '创建人') or ''
                })

            top5_products.append({
                '产品名称': product_name,
                '记录数量': count,
                '占比': percentage,
                '相关卡片': cards
            })

        return top5_products

    def analyze_quality_metrics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        质量指标分析（新增维度）：
        - 有感事件率 × 产品维度
        - 升级到研或OP率 × 产品维度
        - 处理时效分布（整体 + 产品维度）
        - 字段填写完整性
        """
        result: Dict[str, Any] = {}

        # 工具函数：找含关键字的列
        def find_col(keyword):
            for col in df.columns:
                if keyword in col:
                    return col
            return None

        feels_col = find_col('有感')
        escalate_col = find_col('升级')
        product_col_name = self.field_mapper.get('细分分类') if self.field_mapper else None
        created_col_name = self.field_mapper.get('创建时间') if self.field_mapper else None
        status_col_name = self.field_mapper.get('流程状态') if self.field_mapper else None

        # ── 1. 各产品有感事件率 ──
        product_feels = []
        if product_col_name and product_col_name in df.columns and feels_col:
            prod_stats = {}
            for idx, row in df.iterrows():
                raw = str(row.get(product_col_name, '') or '').strip()
                if not raw:
                    continue
                for part in re.split(r'[,，;；、\|]+', raw):
                    part = part.strip()
                    if not part:
                        continue
                    if part not in prod_stats:
                        prod_stats[part] = {'total': 0, 'feels': 0, 'escalated': 0}
                    prod_stats[part]['total'] += 1
                    if str(row.get(feels_col, '')).strip() == '是':
                        prod_stats[part]['feels'] += 1
                    if escalate_col and str(row.get(escalate_col, '')).strip() == '是':
                        prod_stats[part]['escalated'] += 1

            for prod, v in sorted(prod_stats.items(), key=lambda x: -x[1]['total'])[:15]:
                total = v['total']
                product_feels.append({
                    '产品': prod,
                    '卡片总数': total,
                    '有感事件数': v['feels'],
                    '有感率': f"{v['feels'] / total * 100:.1f}%" if total > 0 else '0.0%',
                    '升级到研或OP数': v['escalated'],
                    '升级率': f"{v['escalated'] / total * 100:.1f}%" if total > 0 else '0.0%',
                })
        result['product_quality'] = product_feels

        # ── 2. 处理时效分析（仅适用于 API 数据，Excel 无完成时间字段时跳过）──
        ttd_stats: Dict[str, Any] = {}
        # Excel 数据可能没有完成时间列，静默跳过
        result['ttd_stats'] = ttd_stats

        # ── 3. 月度有感事件趋势（给折线图用）──
        monthly_feels = []
        if feels_col and created_col_name and created_col_name in df.columns:
            df2 = df.copy()
            df2['_ct'] = pd.to_datetime(df2[created_col_name], errors='coerce')
            df2['_month'] = df2['_ct'].dt.to_period('M')
            for period, grp in df2[df2['_ct'].notna()].groupby('_month'):
                total = len(grp)
                feels_yes = int((grp[feels_col].astype(str).str.strip() == '是').sum())
                feels_no = int((grp[feels_col].astype(str).str.strip() == '否').sum())
                feels_filled = feels_yes + feels_no
                monthly_feels.append({
                    '月份': str(period),
                    '总卡片数': total,
                    '有感事件数': feels_yes,
                    '有感率': f"{feels_yes / total * 100:.1f}%",
                    '字段填写率': f"{feels_filled / total * 100:.1f}%",
                })
        result['monthly_feels_trend'] = monthly_feels

        return result

    def analyze_person_workload(self, df: pd.DataFrame) -> List[Dict]:
        """
        负责人工作量分析（改进版）：
        - 基于 API 数据的 responsiblePeople 字段多值拆分（Excel 模式同样支持 "张三, 李四" 格式）
        - 输出：总卡片数、已完成、未完成（含状态细分）
        - 不输出"完成率"，避免被 AI 误读为效率指标
        """
        resp_col_name = self.field_mapper.get('负责人') if self.field_mapper else None
        status_col_name = self.field_mapper.get('流程状态') if self.field_mapper else None
        if resp_col_name is None or resp_col_name not in df.columns:
            return []

        person_data: Dict[str, Dict] = {}

        for idx, row in df.iterrows():
            raw_resp = str(row.get(resp_col_name, '') or '').strip()
            if not raw_resp:
                continue
            persons = [p.strip() for p in re.split(r'[,，;；]+', raw_resp) if p.strip()]
            status = str(row.get(status_col_name, '') or '').strip() if status_col_name else ''
            is_finished = status in self.FINISHED_STATUSES

            for person in persons:
                if person not in person_data:
                    person_data[person] = {'total': 0, 'finished': 0, 'in_progress': 0, 'status_dist': Counter()}
                person_data[person]['total'] += 1
                if is_finished:
                    person_data[person]['finished'] += 1
                else:
                    person_data[person]['in_progress'] += 1
                person_data[person]['status_dist'][status] += 1

        result = []
        for person, v in sorted(person_data.items(), key=lambda x: -x[1]['finished']):
            if v['total'] < 1:
                continue
            result.append({
                '创建人': person,
                '总卡片数': v['total'],
                '已完成数量': v['finished'],
                '未完成数量': v['in_progress'],
                '状态分布': dict(v['status_dist'].most_common(5)),
            })
        return result

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
        monthly_trends, weekly_trends, maintenance_monthly_data = self.analyze_trends(df)
        logger.info(f"月度趋势数据点: {len(monthly_trends)}")
        logger.info(f"运维事件月度趋势数据点: {len(maintenance_monthly_data)}")
        logger.info(f"周度趋势数据点: {len(weekly_trends)}")

        # 4. 数据可视化
        visualizations = self.analyze_visualizations(df)

        # 5. 产品详细统计
        top5_products = self.analyze_product_details(df)
        logger.info(f"Top5产品: {len(top5_products)} 个")

        # 6. 质量指标分析（有感事件、升级率、字段完整性）
        quality_metrics = self.analyze_quality_metrics(df)
        logger.info(f"产品质量指标数据: {len(quality_metrics.get('product_quality', []))} 个产品")

        # 7. 负责人工作量分析
        person_workload = self.analyze_person_workload(df)
        logger.info(f"负责人工作量数据: {len(person_workload)} 人")

        # 汇总结果
        analysis_results = {
            'anomalies': anomalies,
            'overview': overview,
            'monthly_trends': monthly_trends,
            'maintenance_monthly_trends': maintenance_monthly_data,
            'weekly_trends': weekly_trends,
            'visualizations': visualizations,
            'top5_products': top5_products,
            'quality_metrics': quality_metrics,
            'person_workload': person_workload,
        }

        logger.info("数据分析完成")
        return analysis_results

