#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PFS 监控 API
提供 PFS 指标查询、对比分析、数据导出等功能
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
import uuid
import time
from datetime import datetime

from app.core.deps import get_db, get_current_user, SessionLocal
from app.services.pfs_service import PFSService
from app.services.pfs_task_service import PFSTaskService
from app.services.task_queue_service import task_queue_service
from app.models.pfs import (
    PFSQueryRequest,
    PFSCompareRequest,
    PFSExportRequest,
    PFSMetricResult,
    PFSClientInfo,
    MetricLevel
)
from app.models.user import User
from app.utils.task_manager import get_task_status as redis_get_task_status
from app.core.logger import logger

router = APIRouter()


# ========== 响应模型 ==========

class APIResponse(BaseModel):
    """统一 API 响应格式"""
    success: bool = Field(True, description="操作是否成功")
    data: Optional[Any] = Field(None, description="返回的数据")
    message: Optional[str] = Field(None, description="提示信息")
    error: Optional[str] = Field(None, description="错误信息")


class MetricsCatalogResponse(BaseModel):
    """指标目录响应"""
    success: bool
    data: Dict[str, List[Dict]]
    message: str


class QueryMetricsResponse(BaseModel):
    """查询指标响应"""
    success: bool
    data: List[Dict]
    message: str


class CompareMetricsResponse(BaseModel):
    """对比分析响应"""
    success: bool
    data: Dict[str, Any]
    message: str


class ExportTaskResponse(BaseModel):
    """导出任务响应"""
    success: bool
    data: Dict[str, str]
    message: str


class TaskStatusResponse(BaseModel):
    """任务状态响应"""
    success: bool
    data: Dict[str, Any]
    message: str


class ClientListResponse(BaseModel):
    """客户端列表响应"""
    success: bool
    data: List[Dict]
    message: str


# ========== API 端点 ==========

@router.get("/metrics", response_model=MetricsCatalogResponse, summary="获取指标列表")
async def get_metrics(
    level: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    获取 PFS 指标目录（按分类分组）
    
    - **level**: 指标级别过滤 ("cluster" / "client" / None=全部)
    
    返回按分类分组的指标列表，包含中文名、描述、单位、阈值等信息
    """
    try:
        pfs_service = PFSService(db)
        catalog = pfs_service.get_metrics_catalog(level=level)
        
        # catalog 已经是字典格式，直接返回
        return MetricsCatalogResponse(
            success=True,
            data=catalog,
            message=f"获取成功，共 {len(catalog)} 个分类"
        )
        
    except Exception as e:
        logger.error(f"❌ 获取指标列表失败：{e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query", response_model=QueryMetricsResponse, summary="查询指标数据")
async def query_metrics(
    request: PFSQueryRequest,
    db: Session = Depends(get_db)
):
    """
    查询 PFS 指标数据（带 Redis 缓存）
    
    请求参数：
    - **metrics**: 指标名称列表
    - **level**: 指标级别 ("cluster" / "client")
    - **region**: 区域（默认 "cd"）
    - **instance_type**: 实例类型（默认 "plusl2"）
    - **instance_id**: PFS 实例 ID
    - **client_id**: 客户端 ID（客户端级别必需）
    - **start_time**: 开始时间戳
    - **end_time**: 结束时间戳
    - **step**: 查询步长（默认 "5m"）
    
    返回指标数据点和统计值
    """
    try:
        pfs_service = PFSService(db)
        results = pfs_service.query_metrics_with_cache(request, use_cache=True)

        # 转换为可序列化的格式
        serializable_results = [result.dict() for result in results]

        # 统计客户端数量（用于调试）
        all_client_ids = set()
        total_points = 0
        for r in results:
            for pt in r.data_points:
                total_points += 1
                cid = pt.client_id or (pt.labels.get("ClientId") if pt.labels else None)
                if cid:
                    all_client_ids.add(cid)

        msg = f"查询成功，共 {len(results)} 个指标，{total_points} 个数据点"
        if all_client_ids:
            msg += f"，{len(all_client_ids)} 个客户端: {sorted(all_client_ids)}"
        logger.info(f"📋 {msg}")

        return QueryMetricsResponse(
            success=True,
            data=serializable_results,
            message=msg
        )
        
    except Exception as e:
        logger.error(f"❌ 查询指标数据失败：{e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compare", response_model=CompareMetricsResponse, summary="对比查询")
async def compare_metrics(
    request: PFSCompareRequest,
    db: Session = Depends(get_db)
):
    """
    对比分析（今天 vs 昨天同期）
    
    请求参数：
    - **metrics**: 指标名称列表
    - **level**: 指标级别 ("cluster" / "client")
    - **region**: 区域
    - **instance_type**: 实例类型
    - **instance_id**: PFS 实例 ID
    - **client_id**: 客户端 ID（可选）
    - **time_range_hours**: 时间范围（小时，默认 4）
    - **step**: 查询步长（默认 "5m"）
    
    返回对比结果，包含变化率和趋势判断
    """
    try:
        pfs_service = PFSService(db)
        comparison = pfs_service.compare_metrics(request)
        
        return CompareMetricsResponse(
            success=True,
            data=comparison,
            message="对比分析完成"
        )
        
    except Exception as e:
        logger.error(f"❌ 对比分析失败：{e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/export", response_model=ExportTaskResponse, summary="导出数据（异步任务）")
async def export_data(
    request: PFSExportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    导出 PFS 数据（异步任务）
    
    请求参数：
    - **metrics**: 指标名称列表
    - **level**: 指标级别
    - **region**: 区域
    - **instance_type**: 实例类型
    - **instance_id**: PFS 实例 ID
    - **client_id**: 客户端 ID（可选）
    - **start_time**: 开始时间戳
    - **end_time**: 结束时间戳
    - **step**: 查询步长
    - **format**: 导出格式 ("csv" / "json"，默认 "csv")
    
    返回任务 ID，可通过 /pfs/task/{task_id} 查询进度
    """
    try:
        # 生成任务 ID
        task_id = f"pfs_export_{uuid.uuid4().hex[:12]}"
        
        # 创建任务服务
        task_service = PFSTaskService(
            db=db,
            user_id=current_user.id,
            username=current_user.username
        )
        
        # 创建任务记录
        task_service.create_pfs_export_task(
            task_id=task_id,
            total_metrics=len(request.metrics),
            message=f"PFS 数据导出任务已创建（{len(request.metrics)} 个指标）"
        )
        
        # 添加后台任务
        task_queue_service.enqueue("pfs_export", {
            "task_id": task_id,
            "request": request.dict(),
            "user_id": current_user.id,
            "username": current_user.username,
        })
        
        logger.info(f"✅ PFS 导出任务已创建：{task_id}")
        
        return ExportTaskResponse(
            success=True,
            data={
                "task_id": task_id,
                "status": "pending",
                "message": "导出任务已创建，正在后台处理"
            },
            message="导出任务已创建"
        )
        
    except Exception as e:
        logger.error(f"❌ 创建导出任务失败：{e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/task/{task_id}", response_model=TaskStatusResponse, summary="查询任务状态")
async def get_task_status(
    task_id: str,
    db: Session = Depends(get_db)
):
    """
    查询任务状态和进度
    
    - **task_id**: 任务 ID
    
    返回任务状态、进度、结果文件等信息
    """
    try:
        # 优先从 Redis 获取实时状态
        redis_status = redis_get_task_status(task_id)
        
        if redis_status:
            return TaskStatusResponse(
                success=True,
                data=redis_status,
                message="任务状态获取成功"
            )
        
        # Redis 中没有，从数据库获取
        task_service = PFSTaskService(db=db)
        task = task_service.get_task_from_db(task_id)
        
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        return TaskStatusResponse(
            success=True,
            data={
                "task_id": task.id,
                "status": task.status.value,
                "message": task.message,
                "progress": task.progress,
                "result_url": task.result_url,
                "created_at": task.created_at.isoformat() if task.created_at else None,
                "completed_at": task.completed_at.isoformat() if task.completed_at else None
            },
            message="任务状态获取成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 查询任务状态失败：{e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download/{filename}", summary="下载导出文件")
async def download_file(
    filename: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    下载导出文件
    
    - **filename**: 文件名（如：task_id.csv）
    
    返回预签名下载 URL（有效期 1 小时）
    """
    try:
        # 从文件名提取任务 ID
        task_id = filename.rsplit('.', 1)[0]
        
        # 获取任务记录
        task_service = PFSTaskService(db=db)
        download_url = task_service.download_result(task_id)
        
        if not download_url:
            raise HTTPException(status_code=404, detail="文件不存在或任务未完成")
        
        return APIResponse(
            success=True,
            data={"download_url": download_url},
            message="下载链接生成成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 生成下载链接失败：{e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/clients", response_model=ClientListResponse, summary="获取客户端列表")
async def get_clients(
    region: str = "cd",
    instance_id: str = "pfs-mTYGr6",
    db: Session = Depends(get_db)
):
    """
    获取活跃客户端列表
    
    - **region**: 区域（默认 "cd"）
    - **instance_id**: PFS 实例 ID（默认 "pfs-mTYGr6"）
    
    返回客户端列表，包含 ClientId、ClientIp、最新吞吐数据
    """
    try:
        from app.core.pfs_prometheus_client import PFSPrometheusClient
        
        pfs_client = PFSPrometheusClient(db)
        
        # 查询最近 5 分钟的客户端读吞吐
        end_ts = int(time.time())
        start_ts = end_ts - 300
        
        promql = f'ClientFisReadThroughput{{region="{region}", InstanceId="{instance_id}"}}'
        results = pfs_client.query_range(
            promql=promql,
            start_ts=start_ts,
            end_ts=end_ts,
            step="1m"
        )
        
        client_map = {}
        
        if results:
            for series in results:
                metric = series.get("metric", {})
                client_id = metric.get("ClientId", "unknown")
                client_ip = metric.get("ClientIp", "unknown")
                values = series.get("values", [])
                
                latest_val = 0
                if values:
                    latest_val = float(values[-1][1]) if values[-1][1] else 0
                
                client_map[client_id] = {
                    "client_id": client_id,
                    "client_ip": client_ip,
                    "read_throughput": latest_val,
                    "has_read": latest_val > 0
                }
        
        # 如果没有读数据，尝试查询写吞吐
        if not client_map:
            promql = f'ClientFisWriteThroughput{{region="{region}", InstanceId="{instance_id}"}}'
            results = pfs_client.query_range(
                promql=promql,
                start_ts=start_ts,
                end_ts=end_ts,
                step="1m"
            )
            
            if results:
                for series in results:
                    metric = series.get("metric", {})
                    client_id = metric.get("ClientId", "unknown")
                    client_ip = metric.get("ClientIp", "unknown")
                    values = series.get("values", [])
                    
                    latest_val = 0
                    if values:
                        latest_val = float(values[-1][1]) if values[-1][1] else 0
                    
                    client_map[client_id] = {
                        "client_id": client_id,
                        "client_ip": client_ip,
                        "write_throughput": latest_val,
                        "has_write": latest_val > 0
                    }
        
        # 转换为列表并按吞吐排序
        client_list = list(client_map.values())
        client_list.sort(
            key=lambda x: x.get("read_throughput", 0) + x.get("write_throughput", 0),
            reverse=True
        )
        
        return ClientListResponse(
            success=True,
            data=client_list,
            message=f"获取成功，共 {len(client_list)} 个客户端"
        )
        
    except Exception as e:
        logger.error(f"❌ 获取客户端列表失败：{e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test-connection", response_model=APIResponse, summary="测试 Prometheus 连接")
async def test_connection(
    db: Session = Depends(get_db)
):
    """
    测试 PFS Prometheus 连接
    
    测试当前配置的 Prometheus 连接是否正常
    
    Returns:
        APIResponse: 包含连接测试结果
    """
    try:
        from app.core.pfs_prometheus_client import PFSPrometheusClient
        
        # 创建客户端并测试连接
        client = PFSPrometheusClient(db)
        success, message = client.test_connection()
        
        if success:
            return APIResponse(
                success=True,
                data={
                    "connected": True,
                    "grafana_url": client.base_url,
                    "pfs_instance_id": client.pfs_instance_id,
                    "region": client.region
                },
                message=message
            )
        else:
            return APIResponse(
                success=False,
                error=message,
                message="连接测试失败"
            )
    except Exception as e:
        logger.error(f"❌ 测试 PFS Prometheus 连接失败：{e}")
        return APIResponse(
            success=False,
            error=str(e),
            message="连接测试异常"
        )


# ========== 后台任务函数 ==========

def process_pfs_export_task(
    task_id: str,
    request: PFSExportRequest,
    user_id: int,
    username: str
):
    """
    后台处理 PFS 导出任务
    
    Args:
        task_id: 任务 ID
        request: 导出请求
        user_id: 用户 ID
        username: 用户名
    """
    # 创建独立的数据库会话
    db = SessionLocal()
    
    try:
        logger.info(f"🔄 开始处理 PFS 导出任务：{task_id}")
        
        # 创建服务实例
        pfs_service = PFSService(db)
        task_service = PFSTaskService(db=db, user_id=user_id, username=username)
        
        # 构建查询请求
        query_request = PFSQueryRequest(
            metrics=request.metrics,
            level=request.level,
            region=request.region,
            instance_type=request.instance_type,
            instance_id=request.instance_id,
            client_id=request.client_id,
            start_time=request.start_time,
            end_time=request.end_time,
            step=request.step
        )
        
        # 查询数据
        results = pfs_service.query_metrics_with_cache(query_request, use_cache=False)
        
        # 构建导出数据
        export_data = []
        for result in results:
            for data_point in result.data_points:
                export_data.append({
                    "timestamp": datetime.fromtimestamp(data_point.timestamp).strftime("%Y-%m-%d %H:%M:%S"),
                    "metric_name": result.metric_name,
                    "zh_name": result.zh_name,
                    "desc": result.desc,
                    "value": data_point.value,
                    "unit_zh": result.unit_zh,
                    "normal_range": "",  # 可以从 METRIC_CONFIG 获取
                    "client_id": data_point.client_id or "",
                    "client_ip": data_point.client_ip or "",
                    "labels": ";".join([f"{k}={v}" for k, v in data_point.labels.items()])
                })
        
        # 完成任务并上传到 MinIO
        result_url = task_service.complete_pfs_export_task(
            task_id=task_id,
            export_data=export_data,
            format=request.format
        )
        
        logger.info(f"✅ PFS 导出任务完成：{task_id}，文件 URL：{result_url}")
        
    except Exception as e:
        logger.error(f"❌ PFS 导出任务失败：{task_id}，错误：{e}")
        task_service = PFSTaskService(db=db, user_id=user_id, username=username)
        task_service.fail_task(task_id, str(e))
        
    finally:
        db.close()
