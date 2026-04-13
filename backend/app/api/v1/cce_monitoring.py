#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CCE 集群实时监控 API
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.schemas.response import APIResponse
from app.services.cce_monitoring_service import CCEMonitoringService

router = APIRouter(prefix="/cce-monitoring", tags=["CCE集群监控"])


@router.get("/config", response_model=APIResponse)
async def get_cce_monitoring_config(db: Session = Depends(get_db)):
    svc = CCEMonitoringService(db)
    return APIResponse(success=True, data=svc.get_config(), message="获取成功")


@router.get("/clusters", response_model=APIResponse)
async def list_clusters(db: Session = Depends(get_db)):
    svc = CCEMonitoringService(db)
    return APIResponse(success=True, data={"cluster_ids": svc.list_clusters()}, message="获取成功")


@router.get("/query", response_model=APIResponse)
async def query_cluster(
    cluster_id: str = Query(..., description="集群ID"),
    db: Session = Depends(get_db),
):
    """查询单个集群全部即时指标"""
    svc = CCEMonitoringService(db)
    data = svc.query_cluster(cluster_id)
    return APIResponse(success=True, data=data, message="查询成功")


@router.get("/query-charts", response_model=APIResponse)
async def query_cluster_charts(
    cluster_id: str = Query(..., description="集群ID"),
    period_hours: int = Query(3, ge=1, le=168, description="时间范围（小时）"),
    step: str = Query("5m", description="步长，如 1m/5m/15m/1h"),
    db: Session = Depends(get_db),
):
    """查询集群趋势图数据（range query）"""
    svc = CCEMonitoringService(db)
    data = svc.query_cluster_charts(cluster_id, period_hours=period_hours, step=step)
    return APIResponse(success=True, data=data, message="查询成功")


@router.get("/query-all", response_model=APIResponse)
async def query_all_clusters(db: Session = Depends(get_db)):
    svc = CCEMonitoringService(db)
    data = svc.query_all_clusters()
    return APIResponse(success=True, data={"clusters": data}, message="查询成功")
