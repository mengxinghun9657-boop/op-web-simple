"""
API v1 路由汇总
"""
from fastapi import APIRouter
from app.api.v1.endpoints import alerts, webhooks, alert_statistics

api_router = APIRouter()

# 注册告警管理路由
api_router.include_router(
    alerts.router,
    tags=["alerts"]
)

# 注册告警统计路由
api_router.include_router(
    alert_statistics.router,
    tags=["alert-statistics"]
)

# 注册Webhook管理路由
api_router.include_router(
    webhooks.router,
    tags=["webhooks"]
)
