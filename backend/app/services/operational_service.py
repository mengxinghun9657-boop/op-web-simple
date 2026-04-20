#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
运营数据分析服务
集成 icafe 分析引擎和报告生成器
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
from loguru import logger

from app.core.config import settings


async def analyze_operational_file(file_path: str, task_id: str) -> dict:
    """
    分析运营数据文件（使用新的 icafe 分析引擎）
    
    Args:
        file_path: 上传的Excel文件路径
        task_id: 任务ID
    
    Returns:
        分析结果字典
    """
    db = None
    try:
        logger.info(f"开始分析运营数据文件: {file_path}")

        # 使用新的 icafe 分析引擎
        from app.services.icafe import OperationalAnalyzer, ReportGenerator

        # 获取 db session 以读取数据库中的 AI 配置
        try:
            from app.core.deps import SessionLocal
            db = SessionLocal()
        except Exception as e:
            logger.warning(f"无法创建 DB session，将使用环境变量 AI 配置: {e}")

        # 创建分析器和报告生成器
        analyzer = OperationalAnalyzer()
        report_generator = ReportGenerator(enable_ai_interpretation=True, db=db)
        
        # 执行分析
        analysis_results = analyzer.analyze(file_path)
        
        # 生成 HTML 报告（包含 AI 解读）
        try:
            html_content = await report_generator.generate_html_report_full_with_ai(
                analysis_results,
                report_type='operational_analysis'
            )
            logger.info("✅ 已生成包含 AI 解读的报告")
        except Exception as e:
            logger.warning(f"⚠️ 生成 AI 解读失败，使用基础报告: {e}")
            html_content = report_generator.generate_html_report_full(analysis_results)
        
        # 保存报告到临时文件
        output_dir = settings.RESULT_DIR
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        html_filename = f"长安LCC运营数据分析报告_{timestamp}.html"
        html_file_path = os.path.join(output_dir, html_filename)
        
        report_generator.save_report(html_content, html_file_path)
        logger.info(f"运营数据分析完成: {html_file_path}")

        # 上传 HTML 报告到 MinIO
        if os.path.exists(html_file_path):
            try:
                from app.services.report_upload_service import get_report_upload_service
                upload_service = get_report_upload_service()
                
                # 上传文件到 MinIO 并删除本地文件
                html_object_name, html_url = upload_service.upload_html_file(
                    task_id=task_id,
                    file_path=html_file_path,
                    report_type='operational',
                    delete_after_upload=True
                )
                
                logger.info(f"运营数据 HTML 报告已上传到 MinIO: {html_object_name}")
                
                return {
                    'success': True,
                    'html_file': html_object_name,
                    'html_report': html_object_name,
                    'html_report_url': html_url
                }
                
            except Exception as e:
                logger.error(f"上传运营报告到 MinIO 失败: {e}")
                # 如果上传失败，返回本地路径
                return {
                    'success': True,
                    'html_file': html_file_path,
                    'html_report': html_file_path
                }
        
        return {
            'success': True,
            'html_file': html_file_path,
            'html_report': html_file_path
        }
        
    except Exception as e:
        logger.error(f"运营数据分析异常: {e}")
        import traceback
        return {
            "success": False,
            "error": f"分析异常: {str(e)}\n{traceback.format_exc()}"
        }
    finally:
        if db is not None:
            try:
                db.close()
            except Exception:
                pass


async def analyze_api_data(
    spacecode: str,
    username: str,
    password: str,
    iql: str,
    page: int,
    pgcount: int,
    task_id: str
) -> dict:
    """
    通过 API 查询分析运营数据
    
    Args:
        spacecode: 空间代码
        username: 用户名
        password: 密码
        iql: IQL 查询语句
        page: 起始页码
        pgcount: 每页记录数
        task_id: 任务ID
    
    Returns:
        分析结果字典
    """
    excel_path = None
    try:
        logger.info(f"开始 API 查询分析: spacecode={spacecode}, task_id={task_id}")
        
        from app.services.icafe import IcafeAPIClient, OperationalAnalyzer, ReportGenerator
        
        # 创建 API 客户端
        api_client = IcafeAPIClient()
        
        # 获取 API 数据
        api_data = api_client.fetch_data(
            spacecode=spacecode,
            username=username,
            password=password,
            iql=iql,
            page=page,
            pgcount=pgcount
        )
        
        if not api_data:
            return {
                'success': False,
                'error': '获取 icafe API 数据失败'
            }
        
        logger.info(f"成功获取 {api_data.get('total', 0)} 条记录")
        
        # 转换为 Excel 格式
        output_dir = settings.UPLOAD_DIR
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        excel_filename = f"api_data_{task_id}_{timestamp}.xlsx"
        excel_path = os.path.join(output_dir, excel_filename)
        
        success = api_client.convert_to_excel(api_data, excel_path)
        if not success:
            return {
                'success': False,
                'error': 'API 数据转换为 Excel 失败'
            }
        
        logger.info(f"API 数据已转换为 Excel: {excel_path}")
        
        # 使用分析引擎分析
        result = await analyze_operational_file(excel_path, task_id)
        
        # 添加记录数信息
        if result.get('success'):
            result['total_records'] = api_data.get('total', 0)
        
        return result
        
    except Exception as e:
        logger.error(f"API 查询分析异常: {e}")
        import traceback
        return {
            "success": False,
            "error": f"分析异常: {str(e)}\n{traceback.format_exc()}"
        }
    finally:
        # 确保清理临时 Excel 文件
        if excel_path and os.path.exists(excel_path):
            try:
                os.remove(excel_path)
                logger.info(f"已清理临时文件: {excel_path}")
            except Exception as e:
                logger.warning(f"清理临时文件失败: {e}")
