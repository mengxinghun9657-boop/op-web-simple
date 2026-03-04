#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
监控分析报告下载API - 从MinIO获取报告文件
"""

from fastapi import APIRouter, HTTPException
from loguru import logger
from fastapi.responses import Response
import os

router = APIRouter(prefix="/monitoring", tags=["监控分析"])

@router.get("/download/{task_id}")
async def download_monitoring_report(task_id: str):
    """
    下载监控分析报告（从MinIO获取）
    
    - **task_id**: 任务ID
    
    优先从内存获取，如果不存在则从数据库获取
    """
    try:
        from app.core.minio_client import get_minio_client
        from app.services.monitoring_service import monitoring_service
        
        minio_client = get_minio_client()
        minio_object_name = None
        
        # 1. 先尝试从内存中的任务状态获取
        try:
            task_result = monitoring_service.get_task_result(task_id)
            if task_result and task_result.get('status') == 'completed':
                full_task = monitoring_service.tasks.get(task_id)
                if full_task and 'result' in full_task:
                    minio_object_name = full_task['result'].get('html_report')
        except:
            pass
        
        # 2. 如果内存中没有，从数据库获取
        if not minio_object_name:
            from app.core.database import SessionLocal
            from app.models.task import Task
            
            db = SessionLocal()
            try:
                task_record = db.query(Task).filter(Task.id == task_id).first()
                if not task_record:
                    raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")
                
                if task_record.result_url:
                    minio_object_name = task_record.result_url
            finally:
                db.close()
        
        if not minio_object_name:
            raise HTTPException(status_code=404, detail="报告文件不存在")
        
        # 3. 从MinIO下载文件内容
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
        logger.error(f"下载监控报告失败: {e}")
        raise HTTPException(status_code=500, detail=f"下载报告失败: {str(e)}")
 