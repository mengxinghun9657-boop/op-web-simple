#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
运营数据分析器 - API封装层
将原有的分析逻辑封装为可调用的函数
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path
import pandas as pd
import numpy as np

# 添加当前目录到Python路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))


class DateTimeEncoder(json.JSONEncoder):
    """自定义JSON编码器，处理datetime和pandas类型"""
    def default(self, obj):
        if isinstance(obj, (pd.Timestamp, datetime)):
            return obj.isoformat()
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if pd.isna(obj):
            return None
        return super().default(obj)

def analyze_operational_data(excel_file_path: str, output_dir: str = None) -> dict:
    """
    分析运营数据Excel文件
    
    Args:
        excel_file_path: Excel文件路径
        output_dir: 输出目录，默认为当前目录
    
    Returns:
        分析结果字典，包含状态、结果路径等
    """
    try:
        # 导入分析模块
        from . import complete_excel_analyzer as analyzer
        
        # 设置输出目录
        if output_dir is None:
            output_dir = str(current_dir)
        
        # 检查文件是否存在
        if not os.path.exists(excel_file_path):
            return {
                "success": False,
                "error": f"文件不存在: {excel_file_path}"
            }
        
        # 加载数据
        df = analyzer.load_excel_data(excel_file_path)
        if df is None:
            return {
                "success": False,
                "error": "加载Excel文件失败"
            }
        
        # 执行分析
        results = {}
        
        # 1. 数据概览
        print("📊 开始数据概览分析...")
        results['overview'] = analyzer.analyze_data_overview(df)
        
        # 2. 异常检测
        print("🔍 开始异常检测...")
        results['anomalies'] = analyzer.detect_anomalies(df)
        
        # 3. 趋势分析
        print("📈 开始趋势分析...")
        monthly_trends, weekly_trends = analyzer.analyze_trends(df)
        results['trends'] = {
            'monthly_trends': monthly_trends,
            'weekly_trends': weekly_trends
        }
        # 同时保留原始格式兼容性
        results['monthly_trends'] = monthly_trends
        results['weekly_trends'] = weekly_trends
        
        # 4. 可视化数据
        print("🎨 开始可视化数据分析...")
        results['visualizations'] = analyzer.analyze_visualizations(df)
        
        # 5. 效率分析
        print("👥 开始效率分析...")
        results['efficiency'] = analyzer.analyze_efficiency(df)
        
        # 6. 硬件故障分析
        print("🔧 开始硬件故障分析...")
        hardware_analysis, hardware_details, hardware_summary = analyzer.analyze_hardware_failures(df)
        results['hardware_failures'] = {
            'analysis': hardware_analysis,
            'details': hardware_details,
            'summary': hardware_summary
        }
        
        # 7. 产品详情分析
        print("📦 开始产品详情分析...")
        results['product_details'] = analyzer.analyze_product_details(df)
        
        # 保存分析结果
        result_file = os.path.join(output_dir, 'analysis_results.json')
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2, cls=DateTimeEncoder)
        
        print(f"✅ 分析完成，结果已保存到: {result_file}")
        
        return {
            "success": True,
            "result_file": result_file,
            "results": results,
            "message": "分析完成"
        }
        
    except Exception as e:
        import traceback
        error_msg = f"分析失败: {str(e)}\n{traceback.format_exc()}"
        print(f"❌ {error_msg}")
        return {
            "success": False,
            "error": error_msg
        }


def generate_html_report(analysis_results_path: str, output_dir: str = None) -> dict:
    """
    生成HTML报告
    
    Args:
        analysis_results_path: 分析结果JSON文件路径
        output_dir: 输出目录
    
    Returns:
        生成结果字典
    """
    try:
        # 导入HTML生成模块
        from . import html_report_generator_fixed as html_gen
        
        if output_dir is None:
            output_dir = str(current_dir)
        
        # 检查分析结果文件是否存在
        if not os.path.exists(analysis_results_path):
            return {
                "success": False,
                "error": f"分析结果文件不存在: {analysis_results_path}"
            }
        
        # 读取分析结果
        with open(analysis_results_path, 'r', encoding='utf-8') as f:
            analysis_data = json.load(f)
        
        # 生成HTML
        print("📄 开始生成HTML报告...")
        current_date = datetime.now().strftime('%Y%m%d')
        html_filename = f'长安LCC运营数据分析报告_{current_date}.html'
        html_filepath = os.path.join(output_dir, html_filename)
        
        # 调用HTML生成函数（需要从原模块中提取）
        html_content = html_gen.generate_html_report(analysis_data)
        
        with open(html_filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"✅ HTML报告已生成: {html_filepath}")
        
        return {
            "success": True,
            "html_file": html_filepath,
            "message": "HTML报告生成成功"
        }
        
    except Exception as e:
        import traceback
        error_msg = f"生成HTML失败: {str(e)}\n{traceback.format_exc()}"
        print(f"❌ {error_msg}")
        return {
            "success": False,
            "error": error_msg
        }


def analyze_and_generate_report(excel_file_path: str, output_dir: str = None) -> dict:
    """
    完整流程：分析数据并生成HTML报告
    
    Args:
        excel_file_path: Excel文件路径
        output_dir: 输出目录
    
    Returns:
        完整结果字典
    """
    print("=" * 60)
    print("🚀 运营数据分析流程开始")
    print("=" * 60)
    
    if output_dir is None:
        output_dir = str(current_dir)
    
    # 步骤1: 分析数据
    analysis_result = analyze_operational_data(excel_file_path, output_dir)
    if not analysis_result['success']:
        return analysis_result
    
    # 步骤2: 生成HTML报告（可选，失败也不影响整体结果）
    try:
        html_result = generate_html_report(analysis_result['result_file'], output_dir)
        if html_result['success']:
            return {
                "success": True,
                "analysis_file": analysis_result['result_file'],
                "html_file": html_result['html_file'],
                "results": analysis_result.get('results', {}),
                "message": "分析和报告生成完成"
            }
        else:
            # HTML生成失败，但分析成功
            print(f"⚠️ HTML报告生成失败，但数据分析已完成")
            return {
                "success": True,
                "analysis_file": analysis_result['result_file'],
                "results": analysis_result.get('results', {}),
                "message": "数据分析完成，HTML报告生成失败",
                "warning": html_result.get('error')
            }
    except Exception as e:
        # HTML生成异常，但分析成功
        print(f"⚠️ HTML报告生成异常: {e}")
        return {
            "success": True,
            "analysis_file": analysis_result['result_file'],
            "results": analysis_result.get('results', {}),
            "message": "数据分析完成，HTML报告生成异常",
            "warning": str(e)
        }
