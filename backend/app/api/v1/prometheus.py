#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prometheus配置和集群监控API
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
import json
import time

from app.core.prometheus_config import get_prometheus_config
from app.core.deps import get_db, SessionLocal
from app.services.prometheus_service import PrometheusService
from app.services.prometheus_task_service import PrometheusTaskService
from app.models.task import TaskType, TaskStatus
from app.utils.task_manager import get_task_status as redis_get_task_status
from app.core.logger import logger
from app.core.config import settings
from app.services.task_queue_service import task_queue_service

router = APIRouter()


# ========== 请求/响应模型 ==========

class CookieUpdateRequest(BaseModel):
    """Cookie更新请求"""
    cookie_string: str = Field(..., description="从浏览器复制的Cookie字符串")


class CookieUpdateResponse(BaseModel):
    """Cookie更新响应"""
    success: bool
    message: str
    cookies_count: Optional[int] = None


class ConnectionTestResponse(BaseModel):
    """连接测试响应"""
    success: bool
    message: str


class ClusterMetricsRequest(BaseModel):
    """集群指标查询请求"""
    cluster_id: str = Field(..., description="集群ID")


class BatchClusterMetricsRequest(BaseModel):
    """批量集群指标查询请求"""
    cluster_ids: List[str] = Field(..., description="集群ID列表")


class ClusterMetricsResponse(BaseModel):
    """集群指标响应"""
    cluster_id: str
    metrics: Dict[str, Any]
    timestamp: str


class TaskStatusResponse(BaseModel):
    """任务状态响应"""
    task_id: str
    status: str  # 'pending' | 'processing' | 'completed' | 'failed'
    message: str
    progress: Optional[int] = None  # 0-100
    total_clusters: Optional[int] = None
    completed_clusters: Optional[int] = None
    error: Optional[str] = None
    result_file: Optional[str] = None
    timestamp: str


class BatchClusterMetricsResponse(BaseModel):
    """批量集群指标响应（初始响应）"""
    task_id: str
    status: str
    message: str
    total_clusters: int
    timestamp: str


# ========== 配置管理API ==========

@router.get("/config", summary="获取Prometheus配置")
async def get_config():
    """
    获取当前Prometheus配置（敏感信息已隐藏）
    """
    try:
        config = get_prometheus_config()
        return {
            "success": True,
            "config": config.get_all_config()
        }
    except Exception as e:
        logger.error(f"获取配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取配置失败: {str(e)}")


@router.post("/config/cookie", response_model=CookieUpdateResponse, summary="更新Cookie配置")
async def update_cookie(request: CookieUpdateRequest):
    """
    更新Cookie配置
    
    - **cookie_string**: 从浏览器开发者工具复制的完整Cookie字符串
    
    获取步骤：
    1. 登录百度云CCE控制台
    2. 打开任意集群监控页面
    3. F12打开开发者工具 → Network标签
    4. 刷新页面，找到包含 'query_range' 的请求
    5. 复制请求头中的Cookie内容
    """
    try:
        config = get_prometheus_config()
        
        # 解析Cookie字符串
        cookies = config.parse_cookie_string(request.cookie_string)
        
        if not cookies:
            raise HTTPException(status_code=400, detail="Cookie字符串解析失败，请检查格式")
        
        # 更新配置
        success = config.update_cookies(cookies)
        
        if success:
            return CookieUpdateResponse(
                success=True,
                message=f"Cookie更新成功！包含 {len(cookies)} 个有效cookie",
                cookies_count=len(cookies)
            )
        else:
            raise HTTPException(status_code=400, detail="Cookie更新失败，缺少必要字段")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新Cookie失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"更新Cookie失败: {str(e)}")


@router.post("/config/test", response_model=ConnectionTestResponse, summary="测试连接")
async def test_connection():
    """
    测试Prometheus连接是否正常
    
    返回连接测试结果
    """
    try:
        config = get_prometheus_config()
        success, message = config.test_connection()
        
        return ConnectionTestResponse(
            success=success,
            message=message
        )
    except Exception as e:
        logger.error(f"测试连接失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"测试连接失败: {str(e)}")


# ========== 后台任务函数 ==========

def batch_fetch_cluster_metrics(task_id: str, cluster_ids: List[str]):
    """
    后台任务：批量获取集群指标（使用Redis + MySQL + MinIO）
    注意：后台任务需要创建自己的数据库会话
    """
    # 创建独立的数据库会话
    db = SessionLocal()
    service = None

    try:
        # 创建任务服务实例
        service = PrometheusTaskService(db, user_id=None, username="system")

        logger.info(f"开始后台任务: {task_id}, 集群数量: {len(cluster_ids)}")

        # 更新任务进度到10%
        service.update_progress(task_id, 0, len(cluster_ids), "开始采集集群数据...")

        # 定义进度回调函数
        def update_progress_callback(completed, total, message):
            """进度回调函数"""
            try:
                service.update_progress(task_id, completed, total, message)
            except Exception as e:
                logger.error(f"更新进度失败: {e}")

        # 执行批量采集（带进度回调）
        prometheus_service = PrometheusService()
        all_metrics = prometheus_service.get_multiple_clusters_metrics(
            cluster_ids,
            progress_callback=update_progress_callback
        )

        # 更新进度到95%
        service.update_progress(
            task_id,
            len(cluster_ids),
            len(cluster_ids),
            f"采集完成，正在保存数据..."
        )

        # 准备结果数据（包含实际采集的集群列表）
        export_data = {
            "task_id": task_id,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_clusters": len(all_metrics),
            "requested_clusters": len(cluster_ids),
            "actual_clusters": list(all_metrics.keys()),  # 实际采集的集群列表
            "clusters": all_metrics
        }

        # 完成任务（自动上传到MinIO）
        result_url = service.complete_task(task_id, export_data, upload_to_minio=True)

        logger.info(f"✅ 任务完成: {task_id}, 已采集 {len(all_metrics)} 个集群，结果已上传到MinIO")

    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ 任务失败: {task_id}, 错误: {error_msg}")

        # 标记任务失败
        try:
            if service is None:
                service = PrometheusTaskService(db, user_id=None, username="system")
            service.fail_task(task_id, error_msg)
        except Exception as fail_error:
            logger.error(f"标记任务失败时出错: {fail_error}")

    finally:
        # 关闭数据库会话
        db.close()


# ========== 集群监控API ==========

@router.post("/cluster/metrics", response_model=ClusterMetricsResponse, summary="获取单个集群指标")
async def get_cluster_metrics(request: ClusterMetricsRequest):
    """
    获取单个集群的完整监控指标
    
    - **cluster_id**: 集群ID，例如 'cce-3nusu9su'
    
    返回40+个关键指标，包括：
    - 基础资源（节点、Pod、CPU、内存）
    - 资源使用率
    - Pod状态
    - 节点健康状态
    - 存储/网络监控
    - 资源效率指标
    """
    try:
        service = PrometheusService()
        metrics = service.get_cluster_metrics(request.cluster_id)
        
        return ClusterMetricsResponse(
            cluster_id=request.cluster_id,
            metrics=metrics,
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S")
        )
    except Exception as e:
        logger.error(f"获取集群指标失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取集群指标失败: {str(e)}")


@router.post("/cluster/metrics/batch", response_model=BatchClusterMetricsResponse, summary="批量获取集群指标（异步）")
async def get_batch_cluster_metrics(
    request: BatchClusterMetricsRequest,
    db: Session = Depends(get_db)
):
    """
    批量获取多个集群的监控指标（异步后台任务）

    - **cluster_ids**: 集群ID列表

    立即返回task_id，后台执行采集。使用 GET /cluster/task/{task_id} 查询进度
    任务完成后，结果自动保存到MinIO对象存储，可通过历史查询接口下载
    """
    try:
        # 生成唯一任务ID
        task_id = f"batch-{int(time.time())}"

        # 创建任务服务实例
        service = PrometheusTaskService(db, user_id=None, username="system")

        # 创建任务（同时写入MySQL和Redis）
        task = service.create_task(
            task_id=task_id,
            task_type=TaskType.PROMETHEUS_BATCH,
            total_clusters=len(request.cluster_ids),
            message="任务已创建，等待开始..."
        )

        # 提交到 worker 队列（worker 进程会创建自己的数据库会话）
        task_queue_service.enqueue("prometheus_batch_collect", {
            "task_id": task_id,
            "cluster_ids": request.cluster_ids,
        })

        logger.info(f"✅ 批量采集任务已创建: {task_id}, 集群数: {len(request.cluster_ids)}")

        return BatchClusterMetricsResponse(
            task_id=task_id,
            status='pending',
            message=f'批量采集任务已启动，共 {len(request.cluster_ids)} 个集群',
            total_clusters=len(request.cluster_ids),
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S")
        )

    except Exception as e:
        logger.error(f"创建批量采集任务失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"创建任务失败: {str(e)}")


@router.get("/cluster/task/{task_id}", response_model=TaskStatusResponse, summary="查询任务状态")
async def get_task_status(task_id: str):
    """
    查询批量采集任务的状态（从Redis读取实时状态）

    - **task_id**: 任务ID

    返回任务状态：pending | processing | completed | failed
    任务完成后，状态在Redis中保留24小时
    """
    try:
        # 从Redis获取实时任务状态
        task_data = redis_get_task_status(task_id)

        if not task_data:
            raise HTTPException(status_code=404, detail=f"任务不存在或已过期: {task_id}")

        return TaskStatusResponse(
            task_id=task_id,
            status=task_data['status'],
            message=task_data['message'],
            progress=task_data.get('progress', 0),
            total_clusters=task_data.get('total_clusters'),
            completed_clusters=task_data.get('completed_clusters'),
            error=task_data.get('error'),
            result_file=task_data.get('result_file'),
            timestamp=task_data['timestamp']
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询任务状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"查询任务状态失败: {str(e)}")


@router.post("/cluster/export", summary="导出集群数据")
async def export_cluster_data(request: dict):
    """
    导出集群监控数据为JSON文件
    
    - **task_id**: 任务ID（优先使用）
    - **cluster_ids**: 集群ID列表（如果task_id不存在则重新生成）
    
    返回可下载的JSON文件路径
    """
    try:
        import os
        task_id = request.get('task_id')
        
        # 如果提供了task_id，尝试查找对应的文件
        if task_id:
            existing_file = os.path.join(
                settings.RESULT_DIR,
                f"cluster_metrics_{task_id}.json"
            )
            
            if os.path.exists(existing_file):
                logger.info(f"使用已存在的文件: {existing_file}")
                return {
                    "success": True,
                    "message": "数据导出成功",
                    "file": os.path.basename(existing_file),
                    "task_id": task_id
                }
        
        # 如果本地文件不存在，从MinIO下载
        if not task_id:
            raise HTTPException(status_code=400, detail="必须提供task_id")
            
        # 尝试从MinIO获取数据
        from app.services.prometheus_task_service import PrometheusTaskService
        from app.core.database import SessionLocal
        
        db = SessionLocal()
        try:
            service = PrometheusTaskService(db)
            task = service.get_task_from_db(task_id)
            
            if not task or not task.result_path:
                raise HTTPException(status_code=404, detail="任务数据不存在，请重新获取集群数据")
            
            # 从MinIO下载数据到本地
            from app.core.minio_client import get_minio_client
            minio_client = get_minio_client()
            
            file_content = minio_client.download_data(task.result_path)
            if not file_content:
                raise HTTPException(status_code=404, detail="MinIO中的数据文件不存在")
            
            # 保存到本地文件
            local_file = os.path.join(
                settings.RESULT_DIR,
                f"cluster_metrics_{task_id}.json"
            )
            with open(local_file, 'wb') as f:
                f.write(file_content)
            
            logger.info(f"从MinIO下载数据成功: {local_file}")
            
            return {
                "success": True,
                "message": "数据导出成功",
                "file": os.path.basename(local_file),
                "task_id": task_id
            }
                
        finally:
            db.close()
        
    except Exception as e:
        logger.error(f"导出数据失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"导出数据失败: {str(e)}")


@router.get("/cluster/download/{filename}", summary="下载集群数据文件")
async def download_cluster_file(filename: str):
    """
    下载集群数据JSON文件，设置正确的响应头强制下载
    
    - **filename**: 文件名
    """
    try:
        import os
        from fastapi.responses import FileResponse
        
        # 验证文件名格式，防止路径遍历攻击
        if not filename.startswith('cluster_metrics_') or not filename.endswith('.json'):
            raise HTTPException(status_code=400, detail="无效的文件名")
        
        file_path = os.path.join(settings.RESULT_DIR, filename)
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail=f"文件不存在: {filename}")
        
        logger.info(f"下载文件: {file_path}")
        
        # 返回文件，设置Content-Disposition头强制下载
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type='application/json',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"'
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"下载文件失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"下载文件失败: {str(e)}")
