"""
告警统计分析 API
"""
from typing import Optional
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, case, desc

from app.core.deps import get_db
from app.models.alert import AlertRecord
from app.schemas.response import APIResponse

import logging

logger = logging.getLogger(__name__)

router = APIRouter()


def convert_utc_to_local(dt: datetime) -> datetime:
    """
    将UTC时间转换为本地时间（UTC+8）
    
    Args:
        dt: UTC时间（可能带时区信息）
        
    Returns:
        本地时间（naive datetime，用于数据库查询）
    """
    if dt.tzinfo is not None:
        # 如果有时区信息，转换为UTC+8
        local_dt = dt.astimezone(timezone(timedelta(hours=8)))
        # 去除时区信息，返回naive datetime
        return local_dt.replace(tzinfo=None)
    else:
        # 如果没有时区信息，假设是UTC时间，直接加8小时
        return dt + timedelta(hours=8)


@router.get("/alerts/statistics/trend", response_model=APIResponse)
async def get_alert_trend(
    start_time: datetime = Query(..., description="开始时间"),
    end_time: datetime = Query(..., description="结束时间"),
    group_by: str = Query("day", description="分组方式(day/hour/week/month)"),
    cluster_id: Optional[str] = Query(None, description="按集群筛选"),
    component: Optional[str] = Query(None, description="按组件筛选"),
    db: Session = Depends(get_db)
):
    """
    获取告警趋势统计
    
    支持按时间分组(day/hour/week/month)
    支持按集群、组件筛选
    返回趋势数据和汇总统计
    """
    try:
        # 时区转换：前端传递UTC时间，数据库存储本地时间（UTC+8）
        start_time_local = convert_utc_to_local(start_time)
        end_time_local = convert_utc_to_local(end_time)
        
        logger.info(f"查询时间范围: UTC {start_time} ~ {end_time}")
        logger.info(f"转换为本地时间: {start_time_local} ~ {end_time_local}")
        
        # 根据group_by确定时间分组函数
        if group_by == "hour":
            time_group = func.date_format(AlertRecord.timestamp, '%Y-%m-%d %H:00:00')
        elif group_by == "week":
            time_group = func.date_format(AlertRecord.timestamp, '%Y-%u')
        elif group_by == "month":
            time_group = func.date_format(AlertRecord.timestamp, '%Y-%m')
        else:  # day
            time_group = func.date(AlertRecord.timestamp)
        
        # 构建查询
        # 兼容两种severity格式：
        # 1. 旧格式：ERROR/FAIL/WARN/GOOD
        # 2. 新格式：critical/warning/info
        query = db.query(
            time_group.label('date'),
            func.count().label('total'),
            func.sum(case(
                (AlertRecord.severity.in_(['ERROR', 'critical']), 1), 
                else_=0
            )).label('critical'),
            func.sum(case(
                (AlertRecord.severity.in_(['FAIL', 'WARN', 'warning']), 1), 
                else_=0
            )).label('warning'),
            func.sum(case(
                (AlertRecord.severity.in_(['GOOD', 'info']), 1), 
                else_=0
            )).label('info')
        ).filter(
            AlertRecord.timestamp.between(start_time_local, end_time_local)
        )
        
        # 应用筛选条件
        if cluster_id:
            query = query.filter(AlertRecord.cluster_id == cluster_id)
        if component:
            query = query.filter(AlertRecord.component == component)
        
        # 分组和排序
        query = query.group_by(time_group).order_by(time_group)
        
        # 执行查询
        results = query.all()
        
        # 构建趋势数据
        trend = []
        for row in results:
            trend.append({
                "date": str(row.date),
                "total": row.total or 0,
                "critical": row.critical or 0,
                "warning": row.warning or 0,
                "info": row.info or 0
            })
        
        # 计算汇总统计
        total_alerts = sum(item['total'] for item in trend)
        avg_per_period = total_alerts / len(trend) if trend else 0
        peak_item = max(trend, key=lambda x: x['total']) if trend else None
        
        summary = {
            "total_alerts": total_alerts,
            "avg_per_period": round(avg_per_period, 2),
            "peak_date": peak_item['date'] if peak_item else None,
            "peak_count": peak_item['total'] if peak_item else 0
        }
        
        return APIResponse(
            success=True,
            data={
                "trend": trend,
                "summary": summary
            },
            message="获取成功"
        )
        
    except Exception as e:
        logger.error(f"获取告警趋势统计失败: {e}")
        return APIResponse(
            success=False,
            error=str(e),
            message="获取告警趋势统计失败"
        )


@router.get("/alerts/statistics/distribution", response_model=APIResponse)
async def get_alert_distribution(
    start_time: datetime = Query(..., description="开始时间"),
    end_time: datetime = Query(..., description="结束时间"),
    dimension: str = Query("alert_type", description="维度(alert_type/component/severity/cluster)"),
    db: Session = Depends(get_db)
):
    """
    获取告警类型分布
    
    支持按不同维度统计(alert_type/component/severity/cluster)
    返回分布数据和百分比
    """
    try:
        # 时区转换：前端传递UTC时间，数据库存储本地时间（UTC+8）
        start_time_local = convert_utc_to_local(start_time)
        end_time_local = convert_utc_to_local(end_time)
        
        # 根据dimension确定分组字段
        dimension_map = {
            "alert_type": AlertRecord.alert_type,
            "component": AlertRecord.component,
            "severity": AlertRecord.severity,
            "cluster": AlertRecord.cluster_id
        }
        
        if dimension not in dimension_map:
            return APIResponse(
                success=False,
                error=f"不支持的维度: {dimension}",
                message="参数错误"
            )
        
        group_field = dimension_map[dimension]
        
        # 获取总数
        total_count = db.query(func.count(AlertRecord.id)).filter(
            AlertRecord.timestamp.between(start_time_local, end_time_local)
        ).scalar()
        
        if total_count == 0:
            return APIResponse(
                success=True,
                data={
                    "distribution": [],
                    "total": 0
                },
                message="获取成功"
            )
        
        # 构建查询
        query = db.query(
            group_field.label('name'),
            func.count().label('count')
        ).filter(
            AlertRecord.timestamp.between(start_time_local, end_time_local)
        ).group_by(group_field).order_by(desc('count'))
        
        # 执行查询
        results = query.all()
        
        # 构建分布数据
        distribution = []
        for row in results:
            if row.name:  # 过滤NULL值
                distribution.append({
                    "name": row.name,
                    "count": row.count,
                    "percentage": round(row.count * 100.0 / total_count, 2)
                })
        
        return APIResponse(
            success=True,
            data={
                "distribution": distribution,
                "total": total_count
            },
            message="获取成功"
        )
        
    except Exception as e:
        logger.error(f"获取告警分布统计失败: {e}")
        return APIResponse(
            success=False,
            error=str(e),
            message="获取告警分布统计失败"
        )


@router.get("/alerts/statistics/top-nodes", response_model=APIResponse)
async def get_top_nodes(
    start_time: datetime = Query(..., description="开始时间"),
    end_time: datetime = Query(..., description="结束时间"),
    limit: int = Query(10, ge=1, le=100, description="返回数量"),
    order_by: str = Query("total", description="排序字段(total/critical)"),
    db: Session = Depends(get_db)
):
    """
    获取集群/节点告警排行
    
    支持按总数或严重程度排序
    返回Top N节点的告警统计
    """
    try:
        # 时区转换：前端传递UTC时间，数据库存储本地时间（UTC+8）
        start_time_local = convert_utc_to_local(start_time)
        end_time_local = convert_utc_to_local(end_time)
        
        # 构建查询
        query = db.query(
            AlertRecord.cluster_id,
            AlertRecord.ip,
            AlertRecord.hostname,
            func.count().label('total_alerts'),
            func.sum(case(
                (AlertRecord.severity.in_(['ERROR', 'critical']), 1), 
                else_=0
            )).label('critical_count'),
            func.sum(case(
                (AlertRecord.severity.in_(['FAIL', 'WARN', 'warning']), 1), 
                else_=0
            )).label('warning_count'),
            func.sum(case(
                (AlertRecord.severity.in_(['GOOD', 'info']), 1), 
                else_=0
            )).label('info_count'),
            func.max(AlertRecord.timestamp).label('last_alert_time')
        ).filter(
            AlertRecord.timestamp.between(start_time_local, end_time_local)
        ).group_by(
            AlertRecord.cluster_id,
            AlertRecord.ip,
            AlertRecord.hostname
        )
        
        # 排序
        if order_by == "critical":
            query = query.order_by(desc('critical_count'))
        else:  # total
            query = query.order_by(desc('total_alerts'))
        
        # 限制数量
        query = query.limit(limit)
        
        # 执行查询
        results = query.all()
        
        # 构建响应数据
        top_nodes = []
        for row in results:
            top_nodes.append({
                "cluster_id": row.cluster_id,
                "ip": row.ip,
                "hostname": row.hostname,
                "total_alerts": row.total_alerts or 0,
                "critical_count": row.critical_count or 0,
                "warning_count": row.warning_count or 0,
                "info_count": row.info_count or 0,
                "last_alert_time": row.last_alert_time.isoformat() if row.last_alert_time else None
            })
        
        return APIResponse(
            success=True,
            data={
                "top_nodes": top_nodes
            },
            message="获取成功"
        )
        
    except Exception as e:
        logger.error(f"获取节点告警排行失败: {e}")
        return APIResponse(
            success=False,
            error=str(e),
            message="获取节点告警排行失败"
        )



