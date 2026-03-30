"""
GPU 集群监控 API
"""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field
from loguru import logger
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user
from app.schemas.response import APIResponse
from app.services.gpu_monitoring_service import gpu_monitoring_service


router = APIRouter(prefix="/gpu-monitoring", tags=["GPU 集群监控"])


class BottomCardTimeRequest(BaseModel):
    start_time: datetime = Field(..., description="开始时间")
    end_time: datetime = Field(..., description="结束时间")
    cluster_ids: List[str] = Field(default_factory=list, description="集群ID列表")
    target_models: List[str] = Field(default_factory=lambda: ["H800", "L20", "H20"], description="目标 GPU 型号")
    step: Optional[str] = Field(None, description="Prometheus 采样步长，例如 5m")


@router.get("/has-inspection", response_model=APIResponse)
async def get_has_inspection(db: Session = Depends(get_db)):
    """获取 HAS 自动化巡检数据"""
    try:
        data = gpu_monitoring_service.get_has_inspection_data(db)
        return APIResponse(success=True, data=data, message="获取成功")
    except Exception as exc:
        logger.error(f"获取 HAS 自动化巡检数据失败: {exc}")
        return APIResponse(success=False, error=str(exc), message="获取 HAS 自动化巡检数据失败")


@router.post("/has-inspection/collect", response_model=APIResponse)
async def collect_has_inspection(
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user),
):
    """直接采集 GPU HAS 巡检数据并写入主 MySQL"""
    try:
        task_id = gpu_monitoring_service.create_has_collect_task(username=getattr(current_user, "username", "system"))
        background_tasks.add_task(gpu_monitoring_service.collect_has_inspection_to_mysql, task_id)
        return APIResponse(
            success=True,
            data={"task_id": task_id},
            message="GPU HAS 巡检采集任务已创建",
        )
    except Exception as exc:
        logger.error(f"创建 GPU HAS 巡检采集任务失败: {exc}")
        return APIResponse(success=False, error=str(exc), message="创建采集任务失败")


@router.get("/grafana", response_model=APIResponse)
async def get_grafana_info():
    """获取 Grafana 仪表盘信息"""
    return APIResponse(
        success=True,
        data={
            "url": gpu_monitoring_service.grafana_url,
            "proxy_url": gpu_monitoring_service.get_grafana_proxy_url(),
        },
        message="获取成功",
    )


@router.get("/grafana-proxy/{path:path}")
async def proxy_grafana(request: Request, path: str):
    """代理 Grafana 页面与静态资源，便于在系统内嵌显示"""
    try:
        upstream_response = gpu_monitoring_service.proxy_grafana(path=path, query_params=dict(request.query_params))
        content_type = upstream_response.headers.get("content-type", "text/html; charset=utf-8")

        content = upstream_response.content
        if "text/html" in content_type:
            html = upstream_response.text
            base_prefix = "/api/v1/gpu-monitoring/grafana-proxy"
            html = html.replace('href="/', f'href="{base_prefix}/')
            html = html.replace('src="/', f'src="{base_prefix}/')
            html = html.replace('action="/', f'action="{base_prefix}/')
            html = html.replace('appSubUrl:""', f'appSubUrl:"{base_prefix}"')
            content = html.encode("utf-8")

        headers = {}
        cache_control = upstream_response.headers.get("cache-control")
        if cache_control:
            headers["Cache-Control"] = cache_control

        return Response(content=content, media_type=content_type, headers=headers)
    except Exception as exc:
        logger.error(f"代理 Grafana 失败: {path}, error={exc}")
        return APIResponse(success=False, error=str(exc), message="代理 Grafana 失败")


@router.post("/bottom-card-time/query", response_model=APIResponse)
async def query_bottom_card_time(request: BottomCardTimeRequest):
    """查询指定时间范围的 GPU 卡时数据"""
    try:
        data = gpu_monitoring_service.query_bottom_card_time(
            start_time=request.start_time,
            end_time=request.end_time,
            cluster_ids=request.cluster_ids,
            target_models=request.target_models,
            step=request.step,
        )
        return APIResponse(success=True, data=data, message="查询成功")
    except Exception as exc:
        logger.error(f"查询 GPU 卡时数据失败: {exc}")
        return APIResponse(success=False, error=str(exc), message="查询 GPU 卡时数据失败")


@router.post("/bottom-card-time/analyze", response_model=APIResponse)
async def analyze_bottom_card_time(
    request: BottomCardTimeRequest,
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user),
):
    """创建 GPU bottom 卡时分析任务"""
    try:
        task_id = gpu_monitoring_service.create_bottom_analysis_task(
            username=getattr(current_user, "username", "system")
        )
        background_tasks.add_task(
            gpu_monitoring_service.run_bottom_analysis_task,
            task_id,
            request.start_time,
            request.end_time,
            request.cluster_ids,
            request.target_models,
            request.step,
        )
        return APIResponse(
            success=True,
            data={"task_id": task_id},
            message="GPU bottom 卡时分析任务已创建",
        )
    except Exception as exc:
        logger.error(f"创建 GPU bottom 卡时分析任务失败: {exc}")
        return APIResponse(success=False, error=str(exc), message="创建分析任务失败")
