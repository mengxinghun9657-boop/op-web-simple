#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EIP带宽监控API
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import List, Optional
from loguru import logger

from app.services.eip_service import eip_service
from app.core.deps import get_db


router = APIRouter(prefix="/eip", tags=["EIP带宽监控"])


# ==================== 请求模型 ====================

class EIPAnalysisRequest(BaseModel):
    """EIP带宽分析请求"""
    eip_ids: List[str] = Field(..., description="EIP实例ID列表")
    hours: int = Field(6, description="查询小时数（最近N小时）", ge=1, le=24)
    ak: Optional[str] = Field(None, description="百度云AK")
    sk: Optional[str] = Field(None, description="百度云SK")


class TaskResponse(BaseModel):
    """任务响应"""
    task_id: str
    status: str
    message: str


# ==================== API端点 ====================

@router.post("/analyze", response_model=TaskResponse)
async def analyze_eip(
    request: EIPAnalysisRequest,
    background_tasks: BackgroundTasks
):
    """
    启动EIP带宽分析
    
    - **eip_ids**: EIP实例ID列表
    - **hours**: 查询小时数（1-24小时）
    - **ak**: 百度云访问密钥（可选）
    - **sk**: 百度云密钥（可选）
    """
    try:
        logger.info(f"收到EIP分析请求: {len(request.eip_ids)}个EIP, {request.hours}小时数据")
        
        # 执行分析
        task_id = await eip_service.analyze_eip(
            eip_ids=request.eip_ids,
            hours=request.hours,
            ak=request.ak,
            sk=request.sk
        )
        
        # 直接获取结果
        result = eip_service.get_task_result(task_id)
        if result and result.get('status') == 'completed':
            html_file = result.get('html_file', '')
            return {
                "task_id": task_id,
                "status": "completed",
                "message": f"EIP带宽分析已完成，EIP数: {len(request.eip_ids)}",
                "html_file": f"/api/v1/reports/proxy/{html_file}" if html_file and not html_file.startswith('/api/') else html_file
            }
        
        return TaskResponse(
            task_id=task_id,
            status="completed",
            message=f"EIP带宽分析已完成，EIP数: {len(request.eip_ids)}"
        )
        
    except Exception as e:
        logger.error(f"EIP分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/result/{task_id}")
async def get_task_result(task_id: str, db: Session = Depends(get_db)):
    """
    获取EIP分析任务结果
    
    - **task_id**: 任务ID
    """
    # 先从内存获取
    result = eip_service.get_task_result(task_id)
    
    if not result:
        # 从MySQL获取
        try:
            from app.models.task import Task
            task = db.query(Task).filter(Task.id == task_id).first()
            if task:
                html_file = task.result_url or ''
                result = {
                    "status": task.status.value if task.status else "unknown",
                    "html_file": f"/api/v1/reports/proxy/{html_file}" if html_file else None,
                    "message": task.message,
                    "error": task.error_message
                }
        except Exception as e:
            logger.error(f"从MySQL获取任务失败: {e}")
    
    if not result:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")
    
    return result


@router.get("/download/{task_id}")
async def download_eip_report(task_id: str):
    """
    下载EIP分析报告（从MinIO获取）
    
    - **task_id**: 任务ID
    """
    try:
        from app.core.minio_client import get_minio_client
        from app.services.eip_service import eip_service
        
        minio_client = get_minio_client()
        
        # 获取任务结果
        task_result = eip_service.get_task_result(task_id)
        if not task_result or task_result.get('status') != 'completed':
            raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在或未完成")
        
        # 从结果中获取MinIO对象名称
        # EIP服务返回的是 /reports/{filename}，需要从MinIO获取实际文件
        html_file = task_result.get('html_file', '')
        if not html_file:
            raise HTTPException(status_code=404, detail="报告文件不存在")
        
        # 从任务存储中获取完整的MinIO路径
        full_task = eip_service.tasks.get(task_id)
        if not full_task or 'result' not in full_task:
            raise HTTPException(status_code=404, detail="无法找到完整任务信息")
        
        # 获取MinIO中的实际对象名称
        minio_object_name = full_task['result'].get('html_report')
        if not minio_object_name:
            raise HTTPException(status_code=404, detail="MinIO对象不存在")
        
        # 从MinIO下载文件内容
        file_content = minio_client.download_data(minio_object_name)
        if not file_content:
            raise HTTPException(status_code=404, detail="无法从MinIO下载文件")
        
        from fastapi.responses import Response
        import os
        
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
        logger.error(f"下载EIP报告失败: {e}")
        raise HTTPException(status_code=500, detail=f"下载报告失败: {str(e)}")
