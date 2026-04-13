#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
监控分析API
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import List, Optional
from loguru import logger

from app.services.monitoring_service import monitoring_service
from app.core.deps import get_db


router = APIRouter(prefix="/monitoring", tags=["监控分析"])


# ==================== 请求模型 ====================

class BCCAnalysisRequest(BaseModel):
    """BCC监控分析请求"""
    instance_ids: List[str] = Field(default_factory=list, description="BCC实例ID列表，空则使用默认列表")
    days: int = Field(7, description="查询天数", ge=1, le=30)
    ak: Optional[str] = Field(None, description="百度云AK")
    sk: Optional[str] = Field(None, description="百度云SK")


class BOSAnalysisRequest(BaseModel):
    """BOS存储分析请求"""
    buckets: List[str] = Field(default_factory=list, description="Bucket名称列表，空则使用默认列表")
    ak: Optional[str] = Field(None, description="百度云AK")
    sk: Optional[str] = Field(None, description="百度云SK")


class TaskResponse(BaseModel):
    """任务响应"""
    task_id: str
    status: str
    message: str


# ==================== API端点 ====================

@router.post("/bcc/analyze", response_model=TaskResponse)
async def analyze_bcc(
    request: BCCAnalysisRequest,
):
    """
    启动BCC监控分析
    
    - **instance_ids**: BCC实例ID列表（空则使用默认测试数据）
    - **days**: 查询天数（1-30天）
    - **ak**: 百度云访问密钥（可选，如已配置则无需提供）
    - **sk**: 百度云密钥（可选）
    """
    try:
        # 如果没有传入实例ID，使用默认测试数据
        instance_ids = request.instance_ids
        if not instance_ids:
            instance_ids = [f"i-test-{i:03d}" for i in range(1, 11)]
            logger.info(f"使用默认测试实例列表: {len(instance_ids)}个")
        
        logger.info(f"收到BCC分析请求: {len(instance_ids)}个实例, {request.days}天数据")
        
        # 执行分析
        task_id = await monitoring_service.analyze_bcc(
            instance_ids=instance_ids,
            days=request.days,
            ak=request.ak,
            sk=request.sk
        )
        
        # 直接获取结果
        result = monitoring_service.get_task_result(task_id)
        if result and result.get('status') == 'completed':
            html_file = result.get('html_file', '')
            return {
                "task_id": task_id,
                "status": "completed",
                "message": f"BCC监控分析已完成，实例数: {len(instance_ids)}",
                "html_file": f"/api/v1/reports/proxy/{html_file}" if html_file else None
            }
        
        return TaskResponse(
            task_id=task_id,
            status="completed",
            message=f"BCC监控分析已完成，实例数: {len(instance_ids)}"
        )
        
    except Exception as e:
        logger.error(f"BCC分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bos/analyze", response_model=TaskResponse)
async def analyze_bos(
    request: BOSAnalysisRequest,
):
    """
    启动BOS存储分析
    
    - **buckets**: Bucket名称列表（空则使用默认测试数据）
    - **ak**: 百度云访问密钥（可选）
    - **sk**: 百度云密钥（可选）
    """
    try:
        # 如果没有传入bucket，使用默认测试数据
        buckets = request.buckets
        if not buckets:
            buckets = [f"test-bucket-{i:03d}" for i in range(1, 51)]
            logger.info(f"使用默认测试Bucket列表: {len(buckets)}个")
        
        logger.info(f"收到BOS分析请求: {len(buckets)}个Bucket")
        
        # 执行分析
        task_id = await monitoring_service.analyze_bos(
            buckets=buckets,
            ak=request.ak,
            sk=request.sk
        )
        
        # 直接获取结果
        result = monitoring_service.get_task_result(task_id)
        if result and result.get('status') == 'completed':
            html_file = result.get('html_file', '')
            return {
                "task_id": task_id,
                "status": "completed",
                "message": f"BOS存储分析已完成，Bucket数: {len(buckets)}",
                "html_file": f"/api/v1/reports/proxy/{html_file}" if html_file else None
            }
        
        return TaskResponse(
            task_id=task_id,
            status="completed",
            message=f"BOS存储分析已完成，Bucket数: {len(buckets)}"
        )
        
    except Exception as e:
        logger.error(f"BOS分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/result/{task_id}")
async def get_task_result(task_id: str, db: Session = Depends(get_db)):
    """
    获取监控分析任务结果
    
    - **task_id**: 任务ID
    """
    result = monitoring_service.get_task_result(task_id)
    
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


@router.get("/progress/{task_id}")
async def get_task_progress(task_id: str):
    """
    获取监控分析任务进度
    
    - **task_id**: 任务ID
    """
    progress = monitoring_service.get_task_progress(task_id)
    
    if not progress:
        # 检查任务是否已完成
        result = monitoring_service.get_task_result(task_id)
        if result:
            if result.get('status') == 'completed':
                return {
                    "task_id": task_id,
                    "progress": 100,
                    "message": "分析完成",
                    "status": "completed"
                }
            elif result.get('status') == 'failed':
                return {
                    "task_id": task_id,
                    "progress": 0,
                    "message": result.get('error', '分析失败'),
                    "status": "failed"
                }
        
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在或无进度信息")
    
    return {
        "task_id": task_id,
        "progress": progress.get('progress', 0),
        "current": progress.get('current', 0),
        "total": progress.get('total', 0),
        "message": progress.get('message', ''),
        "status": "in_progress"
    }
