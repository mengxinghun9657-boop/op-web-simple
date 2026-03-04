#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
资源分析报告下载API - 从MinIO获取报告文件
"""

from fastapi import APIRouter, HTTPException
from loguru import logger
from fastapi.responses import Response
import os

router = APIRouter(prefix="/resource", tags=["资源分析"])

@router.get("/download/{task_id}")
async def download_resource_report(task_id: str):
    """
    下载资源分析HTML报告（从MinIO获取）
    
    - **task_id**: 分析任务ID
    """
    try:
        from app.core.minio_client import get_minio_client
        from app.core.config import settings
        
        minio_client = get_minio_client()
        
        # 查找结果文件
        result_file = os.path.join(settings.RESULT_DIR, f"{task_id}_resource_analysis.json")
        
        if not os.path.exists(result_file):
            raise HTTPException(status_code=404, detail="分析结果不存在")
        
        # 读取结果文件获取MinIO对象信息
        import json
        with open(result_file, 'r', encoding='utf-8') as f:
            result = json.load(f)
        
        # 获取MinIO中的实际对象名称
        minio_object_name = None
        if isinstance(result, dict):
            # 首先检查是否有直接的html_report路径
            if 'html_report' in result and result['html_report']:
                minio_object_name = result['html_report']
            # 然后检查result内部
            elif 'result' in result and isinstance(result['result'], dict):
                if 'html_report' in result['result']:
                    minio_object_name = result['result']['html_report']
                elif 'result_path' in result['result']:
                    minio_object_name = result['result']['result_path']
        
        if not minio_object_name:
            # 如果结果中没有MinIO对象信息，可能是旧版格式，尝试推断
            logger.warning(f"结果文件中未找到MinIO对象信息，尝试推断路径: {result_file}")
            minio_object_name = f"html_reports/resource/{task_id}_resource_report.html"
        
        # 从MinIO下载文件内容
        file_content = minio_client.download_data(minio_object_name)
        if not file_content:
            # 如果MinIO下载失败，尝试使用原有本地文件作为fallback
            logger.warning(f"MinIO下载失败，尝试本地文件: {minio_object_name}")
            
            # 检查是否有本地HTML文件
            html_file = None
            if isinstance(result, dict):
                if 'html_file' in result and result['html_file']:
                    html_file = result['html_file']
                    if html_file.startswith('/reports/'):
                        # 转换为绝对路径
                        filename = os.path.basename(html_file)
                        reports_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data", "reports")
                        html_file = os.path.join(reports_dir, filename)
            
            if html_file and os.path.exists(html_file):
                from fastapi.responses import FileResponse
                return FileResponse(
                    path=html_file,
                    filename=os.path.basename(html_file),
                    media_type="text/html"
                )
            else:
                raise HTTPException(status_code=404, detail="无法获取报告文件")
        
        # 返回文件内容
        filename = os.path.basename(minio_object_name)
        return Response(
            content=file_content,
            media_type="text/html",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"下载资源分析报告失败: {e}")
        raise HTTPException(status_code=500, detail=f"下载报告失败: {str(e)}")