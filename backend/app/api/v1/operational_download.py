#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
运营数据分析报告下载API - 从MinIO获取报告文件
"""

from fastapi import APIRouter, HTTPException
from loguru import logger
from fastapi.responses import Response
import os

router = APIRouter(prefix="/operational", tags=["运营数据分析"])

@router.get("/download/{task_id}")
async def download_operational_report(task_id: str):
    """
    下载运营数据分析HTML报告（从MinIO获取）
    
    - **task_id**: 分析任务ID
    """
    try:
        from app.core.minio_client import get_minio_client
        from app.services.operational_service import OperationalService
        
        minio_client = get_minio_client()
        operational_service = OperationalService()
        
        # 获取任务结果 - 这里需要根据实际的任务存储结构进行调整
        # 暂时使用原有逻辑获取任务状态
        tasks_status = {}  # 需要从operational模块导入实际的任务状态字典
        
        if task_id not in tasks_status:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        task = tasks_status[task_id]
        
        # 获取MinIO对象名称
        minio_object_name = task.get('minio_object') or task.get('html_report')
        if not minio_object_name:
            # 如果没有直接存储MinIO对象名，尝试从html_file路径推断
            html_file = task.get('html_file')
            if html_file:
                filename = os.path.basename(html_file)
                minio_object_name = f"html_reports/operational/{filename}"
        
        if not minio_object_name:
            raise HTTPException(status_code=404, detail="报告中未找到MinIO对象信息")
        
        # 从MinIO下载文件内容
        file_content = minio_client.download_data(minio_object_name)
        if not file_content:
            raise HTTPException(status_code=404, detail="无法从MinIO下载文件")
        
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
        logger.error(f"下载运营数据分析报告失败: {e}")
        raise HTTPException(status_code=500, detail=f"下载报告失败: {str(e)}")

# 原有operational.py中的下载接口仍然保留作为fallback