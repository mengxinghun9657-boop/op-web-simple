#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
任务管理API
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from typing import Optional, Dict, Any, List
from datetime import datetime
from loguru import logger
from sqlalchemy.orm import Session
import os
import json

from app.core.config import settings
from app.core.deps import get_db
from app.models.task import ModuleType, Task, TaskType, TaskStatus
from app.services.prometheus_task_service import PrometheusTaskService
from app.schemas.task import TaskHistoryResponse, TaskListResponse, TaskDownloadResponse

router = APIRouter()

# 移除内存存储，统一使用Redis+MySQL
# tasks_store: Dict[str, Dict[str, Any]] = {}


@router.post("/tasks/{task_id}/analyze")
async def analyze_task(
    task_id: str,
    background_tasks: BackgroundTasks,
    module_type: str = "operational_analysis"
):
    """
    开始分析任务（异步）
    
    - **task_id**: 任务ID
    - **module_type**: 模块类型 (operational_analysis, resource_analysis等)
    """
    # 检查上传文件是否存在
    upload_files = [f for f in os.listdir(settings.UPLOAD_DIR) if f.startswith(task_id)]
    
    if not upload_files:
        raise HTTPException(status_code=404, detail="任务文件不存在")
    
    file_path = os.path.join(settings.UPLOAD_DIR, upload_files[0])
    
    # 创建任务记录
    task_info = {
        "task_id": task_id,
        "module_type": module_type,
        "status": "analyzing",
        "progress": 0,
        "file_path": file_path,
        "created_at": datetime.now().isoformat(),
        "message": "分析任务已启动"
    }
    
    tasks_store[task_id] = task_info
    
    # 添加后台任务（实际分析逻辑）
    background_tasks.add_task(run_analysis, task_id, file_path, module_type)
    
    logger.info(f"任务 {task_id} 已加入分析队列")
    
    return task_info


async def run_analysis(task_id: str, file_path: str, module_type: str):
    """后台执行分析任务"""
    try:
        logger.info(f"开始分析任务: {task_id}, 模块: {module_type}")
        
        # 更新进度
        tasks_store[task_id]["progress"] = 10
        tasks_store[task_id]["message"] = "分析中..."
        
        # 根据模块类型调用不同的分析逻辑
        if module_type == "operational_analysis":
            from app.services.operational_service import analyze_operational_file
            result = await analyze_operational_file(file_path, task_id)
        elif module_type == "resource_analysis":
            from app.services.resource_service import analyze_resource_file
            result = await analyze_resource_file(file_path, task_id)
        elif module_type == "monitoring_bcc":
            from app.services.monitoring_service import analyze_bcc_monitoring
            result = await analyze_bcc_monitoring(file_path, task_id)
        elif module_type == "monitoring_eip":
            from app.services.eip_service import analyze_eip_monitoring
            result = await analyze_eip_monitoring(file_path, task_id)
        elif module_type == "monitoring_bos":
            from app.services.monitoring_service import analyze_bos_monitoring
            result = await analyze_bos_monitoring(file_path, task_id)
        else:
            result = {"success": False, "error": f"不支持的模块类型: {module_type}"}
        
        # 更新任务状态
        if result.get("success"):
            tasks_store[task_id]["status"] = "completed"
            tasks_store[task_id]["progress"] = 100
            tasks_store[task_id]["completed_at"] = datetime.now().isoformat()
            tasks_store[task_id]["message"] = "分析完成"
            tasks_store[task_id]["result"] = result
            
            # 如果有HTML文件，保存路径
            if "html_file" in result:
                tasks_store[task_id]["html_file"] = result["html_file"]
            
            logger.info(f"任务 {task_id} 分析完成")
        else:
            tasks_store[task_id]["status"] = "failed"
            tasks_store[task_id]["error_message"] = result.get("error", "未知错误")
            logger.error(f"任务 {task_id} 分析失败: {result.get('error')}")
        
    except Exception as e:
        logger.error(f"任务 {task_id} 分析异常: {str(e)}")
        tasks_store[task_id]["status"] = "failed"
        tasks_store[task_id]["error_message"] = str(e)


@router.get("/tasks/{task_id}/status")
async def get_task_status(task_id: str):
    """获取任务状态 - 统一逻辑"""
    from app.utils.task_status_unified import get_unified_task_status
    return await get_unified_task_status(task_id)


@router.get("/tasks")
async def list_all_tasks(
    status: Optional[str] = None,
    task_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    获取所有模块的任务列表（从MySQL读取）
    """
    try:
        query = db.query(Task).order_by(Task.created_at.desc())
        
        if status:
            query = query.filter(Task.status == status)
        if task_type:
            query = query.filter(Task.task_type == task_type)
        
        total = query.count()
        tasks = query.offset(skip).limit(limit).all()
        
        def format_result_url(url):
            if not url:
                return None
            if url.startswith('/api/') or url.startswith('http'):
                return url
            return f"/api/v1/reports/proxy/{url}"
        
        return {
            "total": total,
            "tasks": [{
                "id": t.id,
                "task_type": t.task_type.value if t.task_type else "unknown",
                "status": t.status.value if t.status else "unknown",
                "progress": t.progress or 0,
                "message": t.message or "",
                "total_items": t.total_items or 1,
                "completed_items": t.completed_items or 0,
                "username": t.username or "system",
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "completed_at": t.completed_at.isoformat() if t.completed_at else None,
                "result_url": format_result_url(t.result_url),
                "error_message": t.error_message
            } for t in tasks]
        }
    except Exception as e:
        logger.error(f"从MySQL获取任务列表失败: {e}")
        # 降级到内存获取
        return await list_all_tasks_from_memory(status, task_type, skip, limit)


async def list_all_tasks_from_memory(
    status: Optional[str] = None,
    task_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 50
):
    """从内存获取任务列表（降级方案）"""
    from datetime import datetime
    
    all_tasks = []
    
    def parse_time(t):
        if isinstance(t, datetime):
            return t
        if isinstance(t, str):
            try:
                return datetime.fromisoformat(t.replace('Z', '+00:00'))
            except:
                pass
        return datetime.min
    
    # 1. 运营分析任务
    try:
        from app.api.v1.operational import tasks_status as operational_tasks
        for tid, task in operational_tasks.items():
            all_tasks.append({
                "id": tid,
                "task_type": "operational",
                "status": task.get("status", "unknown"),
                "progress": 100 if task.get("status") == "completed" else 50 if task.get("status") == "processing" else 0,
                "message": task.get("message", ""),
                "total_items": 1,
                "completed_items": 1 if task.get("status") == "completed" else 0,
                "username": task.get("username", "system"),
                "created_at": task.get("created_at"),
                "completed_at": task.get("completed_at"),
                "result_url": task.get("html_file"),
                "error_message": task.get("error")
            })
    except Exception as e:
        logger.debug(f"获取运营任务失败: {e}")
    
    # 2. 监控分析任务
    try:
        from app.services.monitoring_service import monitoring_service
        for tid, task in monitoring_service.tasks.items():
            all_tasks.append({
                "id": tid,
                "task_type": "monitoring",
                "status": task.get("status", "unknown"),
                "progress": 100 if task.get("status") == "completed" else 50,
                "message": task.get("message", ""),
                "total_items": 1,
                "completed_items": 1 if task.get("status") == "completed" else 0,
                "username": "system",
                "created_at": task.get("created_at"),
                "completed_at": task.get("completed_at"),
                "result_url": task.get("result", {}).get("html_report") if isinstance(task.get("result"), dict) else None,
                "error_message": task.get("error")
            })
    except Exception as e:
        logger.debug(f"获取监控任务失败: {e}")
    
    # 3. EIP分析任务
    try:
        from app.services.eip_service import eip_service
        for tid, task in eip_service.tasks.items():
            all_tasks.append({
                "id": tid,
                "task_type": "eip",
                "status": task.get("status", "unknown"),
                "progress": 100 if task.get("status") == "completed" else 50,
                "message": task.get("message", ""),
                "total_items": 1,
                "completed_items": 1 if task.get("status") == "completed" else 0,
                "username": "system",
                "created_at": task.get("created_at"),
                "completed_at": task.get("completed_at"),
                "result_url": task.get("result", {}).get("html_report") if isinstance(task.get("result"), dict) else None,
                "error_message": task.get("error")
            })
    except Exception as e:
        logger.debug(f"获取EIP任务失败: {e}")
    
    # 4. Prometheus批量任务
    try:
        from app.services.prometheus_service import prometheus_service
        for tid, task in prometheus_service.batch_tasks.items():
            total = task.get("total", 0)
            completed = task.get("completed", 0)
            all_tasks.append({
                "id": tid,
                "task_type": "prometheus",
                "status": task.get("status", "unknown"),
                "progress": task.get("progress", 0),
                "message": task.get("message", ""),
                "total_items": total,
                "completed_items": completed,
                "username": "system",
                "created_at": task.get("created_at"),
                "completed_at": task.get("completed_at"),
                "result_url": task.get("result_url"),
                "error_message": task.get("error")
            })
    except Exception as e:
        logger.debug(f"获取Prometheus任务失败: {e}")
    
    # 5. 资源分析任务
    try:
        from app.services.resource_service import resource_tasks
        for tid, task in resource_tasks.items():
            all_tasks.append({
                "id": tid,
                "task_type": "resource",
                "status": task.get("status", "unknown"),
                "progress": 100 if task.get("status") == "completed" else 50,
                "message": task.get("message", ""),
                "total_items": 1,
                "completed_items": 1 if task.get("status") == "completed" else 0,
                "username": "system",
                "created_at": task.get("created_at"),
                "completed_at": task.get("completed_at"),
                "result_url": task.get("html_file"),
                "error_message": task.get("error")
            })
    except Exception as e:
        logger.debug(f"获取资源任务失败: {e}")
    
    # 过滤
    if status:
        all_tasks = [t for t in all_tasks if t["status"] == status]
    if task_type:
        all_tasks = [t for t in all_tasks if t["task_type"] == task_type]
    
    # 排序（按创建时间倒序）
    all_tasks.sort(key=lambda x: parse_time(x.get("created_at")), reverse=True)
    
    total = len(all_tasks)
    tasks_page = all_tasks[skip:skip + limit]
    
    return {
        "total": total,
        "tasks": tasks_page
    }


@router.delete("/tasks/{task_id}")
async def delete_task(task_id: str):
    """
    删除任务记录

    - **task_id**: 任务ID
    """
    if task_id in tasks_store:
        del tasks_store[task_id]
        logger.info(f"任务 {task_id} 已删除")
        return {"success": True, "task_id": task_id}
    else:
        raise HTTPException(status_code=404, detail="任务不存在")


# ==================== Prometheus任务历史管理 ====================

@router.get("/prometheus/history", response_model=TaskListResponse)
async def get_prometheus_task_history(
    skip: int = 0,
    limit: int = 20,
    task_type: Optional[TaskType] = None,
    status: Optional[TaskStatus] = None,
    db: Session = Depends(get_db)
):
    """
    获取Prometheus任务历史列表

    - **skip**: 跳过数量（分页）
    - **limit**: 返回数量限制
    - **task_type**: 任务类型筛选 (prometheus_batch, prometheus_single等)
    - **status**: 任务状态筛选 (pending, processing, completed, failed)
    """
    try:
        service = PrometheusTaskService(db)

        # 查询任务历史
        query = db.query(Task).order_by(Task.created_at.desc())

        # 筛选Prometheus相关任务
        prometheus_types = [TaskType.PROMETHEUS_BATCH, TaskType.PROMETHEUS_SINGLE]
        query = query.filter(Task.task_type.in_(prometheus_types))

        # 可选筛选条件
        if task_type:
            query = query.filter(Task.task_type == task_type)

        if status:
            query = query.filter(Task.status == status)

        # 统计总数
        total = query.count()

        # 分页查询
        tasks = query.offset(skip).limit(limit).all()

        logger.info(f"查询Prometheus任务历史: total={total}, skip={skip}, limit={limit}")

        return TaskListResponse(
            total=total,
            tasks=[TaskHistoryResponse.from_orm(task) for task in tasks]
        )

    except Exception as e:
        logger.error(f"查询任务历史失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"查询任务历史失败: {str(e)}")


@router.get("/prometheus/{task_id}/detail", response_model=TaskHistoryResponse)
async def get_prometheus_task_detail(
    task_id: str,
    db: Session = Depends(get_db)
):
    """
    获取单个Prometheus任务详情

    - **task_id**: 任务ID
    """
    try:
        service = PrometheusTaskService(db)
        task = service.get_task_from_db(task_id)

        if not task:
            raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")

        return TaskHistoryResponse.from_orm(task)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询任务详情失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"查询任务详情失败: {str(e)}")


@router.get("/prometheus/{task_id}/download", response_model=TaskDownloadResponse)
async def download_prometheus_task_result(
    task_id: str,
    db: Session = Depends(get_db)
):
    """
    获取Prometheus任务结果下载URL（MinIO预签名URL，有效期1小时）

    - **task_id**: 任务ID
    """
    try:
        service = PrometheusTaskService(db)

        # 从数据库查询任务
        task = service.get_task_from_db(task_id)

        if not task:
            raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")

        # 检查任务状态
        if task.status != TaskStatus.COMPLETED:
            return TaskDownloadResponse(
                task_id=task_id,
                download_url=None,
                message=f"任务尚未完成，当前状态: {task.status.value}"
            )

        # 检查是否有结果文件
        if not task.result_path:
            return TaskDownloadResponse(
                task_id=task_id,
                download_url=None,
                message="任务结果文件不存在"
            )

        # 生成MinIO预签名下载URL（1小时有效期）
        download_url = service.download_result(task_id)

        if not download_url:
            raise HTTPException(status_code=500, detail="生成下载URL失败")

        logger.info(f"生成任务下载URL: {task_id}")

        return TaskDownloadResponse(
            task_id=task_id,
            download_url=download_url,
            expires_in=3600,
            message="下载URL已生成（有效期1小时）"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成下载URL失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"生成下载URL失败: {str(e)}")
