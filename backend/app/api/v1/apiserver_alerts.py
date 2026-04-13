"""
APIServer 监控告警 API
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user
from app.schemas.response import APIResponse, PaginatedResponse, PaginatedData
from app.services.apiserver_alert_service import APIServerAlertService, serialize_record
from app.services.task_queue_service import task_queue_service

router = APIRouter(prefix="/apiserver-alerts", tags=["APIServer 监控告警"])


@router.post("/analyze", response_model=APIResponse)
async def analyze_apiserver_alerts(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = APIServerAlertService(db)
    task_id = service.create_scan_task(username=getattr(current_user, "username", "system"))
    task_queue_service.enqueue("apiserver_alert_analysis", {"task_id": task_id})
    return APIResponse(success=True, data={"task_id": task_id}, message="APIServer 告警分析任务已创建")


@router.get("/config", response_model=APIResponse)
async def get_apiserver_config(db: Session = Depends(get_db)):
    service = APIServerAlertService(db)
    return APIResponse(success=True, data=service.get_config(), message="获取成功")


@router.post("/config", response_model=APIResponse)
async def save_apiserver_config(payload: dict, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    service = APIServerAlertService(db)
    saved = service.save_config(payload, user_id=getattr(current_user, "id", None))
    try:
        from app.core.scheduler import scheduler
        if saved.get("auto_check_enabled"):
            scheduler.add_apiserver_alert_job(int(saved.get("check_interval_minutes", 10)))
        else:
            scheduler.remove_apiserver_alert_job()
    except Exception:
        pass
    return APIResponse(success=True, data=saved, message="保存成功")


@router.get("", response_model=PaginatedResponse)
async def list_apiserver_alerts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    cluster_id: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    service = APIServerAlertService(db)
    result = service.list_alerts(page, page_size, cluster_id, severity, status)
    return PaginatedResponse(
        success=True,
        data=PaginatedData(
            list=[serialize_record(row) for row in result["list"]],
            total=result["total"],
            page=result["page"],
            page_size=result["page_size"],
        ),
        message="获取成功",
    )


@router.get("/stats", response_model=APIResponse)
async def get_apiserver_alert_stats(db: Session = Depends(get_db)):
    service = APIServerAlertService(db)
    return APIResponse(success=True, data=service.get_stats(), message="获取成功")


@router.get("/monitoring/overview", response_model=APIResponse)
async def get_apiserver_monitoring_overview(
    period_hours: int = Query(24, ge=1, le=168),
    db: Session = Depends(get_db),
):
    service = APIServerAlertService(db)
    return APIResponse(success=True, data=service.get_monitoring_overview(period_hours=period_hours), message="获取成功")


@router.get("/{alert_id}", response_model=APIResponse)
async def get_apiserver_alert_detail(alert_id: int, db: Session = Depends(get_db)):
    from app.models.apiserver_alert import APIServerAlertRecord

    record = db.query(APIServerAlertRecord).filter(APIServerAlertRecord.id == alert_id).first()
    if not record:
        return APIResponse(success=False, error="记录不存在", message="未找到对应告警")
    return APIResponse(success=True, data=serialize_record(record), message="获取成功")


@router.put("/{alert_id}/status", response_model=APIResponse)
async def update_apiserver_alert_status(
    alert_id: int,
    payload: dict,
    db: Session = Depends(get_db),
):
    from datetime import datetime
    from app.models.apiserver_alert import APIServerAlertRecord

    record = db.query(APIServerAlertRecord).filter(APIServerAlertRecord.id == alert_id).first()
    if not record:
        return APIResponse(success=False, error="记录不存在", message="未找到对应告警")

    new_status = payload.get("status")
    valid_statuses = ["processing", "resolved", "closed"]
    if new_status:
        if new_status not in valid_statuses:
            return APIResponse(success=False, error="无效的状态值", message=f"状态必须是: {', '.join(valid_statuses)}")
        record.status = new_status
        if new_status == "resolved":
            record.resolved_at = datetime.now()
            record.resolved_by = payload.get("resolved_by", "系统管理员")
        elif new_status in ("processing", "closed"):
            # 重新打开时清除恢复时间，关闭时保留
            if new_status == "processing":
                record.resolved_at = None
                record.resolved_by = None

    if payload.get("resolution_notes") is not None:
        record.resolution_notes = payload.get("resolution_notes")
    if payload.get("resolution_result") is not None:
        record.resolution_result = payload.get("resolution_result")

    db.commit()
    db.refresh(record)
    return APIResponse(success=True, data=serialize_record(record), message="更新成功")


@router.put("/batch/status", response_model=APIResponse)
async def batch_update_apiserver_alert_status(
    payload: dict,
    db: Session = Depends(get_db),
):
    """批量修改 APIServer 告警状态"""
    from datetime import datetime
    from app.models.apiserver_alert import APIServerAlertRecord

    alert_ids = payload.get("alert_ids", [])
    new_status = payload.get("status")
    if not alert_ids or not new_status:
        return APIResponse(success=False, error="参数错误", message="alert_ids 和 status 不能为空")

    valid_statuses = ["processing", "resolved", "closed"]
    if new_status not in valid_statuses:
        return APIResponse(success=False, error="无效的状态值", message=f"状态必须是: {', '.join(valid_statuses)}")

    records = db.query(APIServerAlertRecord).filter(APIServerAlertRecord.id.in_(alert_ids)).all()
    now = datetime.now()
    for record in records:
        record.status = new_status
        if new_status == "resolved":
            record.resolved_at = now
            record.resolved_by = payload.get("resolved_by", "系统管理员")
        elif new_status == "processing":
            record.resolved_at = None
            record.resolved_by = None
    db.commit()
    return APIResponse(success=True, data={"updated": len(records)}, message=f"已批量更新 {len(records)} 条记录")


@router.post("/{alert_id}/create-icafe-card", response_model=APIResponse)
async def create_apiserver_icafe_card(
    alert_id: int,
    card_data: dict,
    db: Session = Depends(get_db),
):
    """为 APIServer 告警创建 iCafe 卡片"""
    import json
    from app.models.apiserver_alert import APIServerAlertRecord
    from app.models.system_config import SystemConfig

    record = db.query(APIServerAlertRecord).filter(APIServerAlertRecord.id == alert_id).first()
    if not record:
        return APIResponse(success=False, error="记录不存在", message="未找到对应告警")

    icafe_config_record = db.query(SystemConfig).filter(
        SystemConfig.module == "icafe",
        SystemConfig.config_key == "main"
    ).first()
    if not icafe_config_record:
        return APIResponse(success=False, error="iCafe 配置不存在", message="请先在系统配置中配置 iCafe API 信息")

    icafe_config = icafe_config_record.config_value
    if isinstance(icafe_config, str):
        icafe_config = json.loads(icafe_config)

    from app.services.icafe.icafe_service import get_icafe_service
    icafe_service = get_icafe_service(icafe_config)

    # 构造告警数据（适配 icafe_service 接口）
    alert_data = {
        "id": record.id,
        "alert_type": record.metric_label,
        "component": "APIServer",
        "severity": record.severity,
        "ip": "",
        "cluster_id": record.cluster_id,
        "hostname": record.cluster_id,
        "timestamp": record.created_at.strftime("%Y-%m-%d %H:%M:%S") if record.created_at else "",
    }
    diagnosis_data = {
        "manual_matched": False,
        "manual_solution": record.suggestion or "",
        "ai_interpretation": record.description or "",
    }

    card_type = card_data.get("card_type", "Bug")
    if card_type not in ["Bug", "Task"]:
        card_type = "Bug"

    title = icafe_service.generate_card_title(alert_data)
    detail = icafe_service.generate_card_detail(alert_data, diagnosis_data)
    fields = icafe_service.build_card_fields(card_data, card_type)

    result = icafe_service.create_card({
        "title": title,
        "detail": detail,
        "type": card_type,
        "fields": fields,
        "creator": icafe_config.get("username", ""),
        "comment": f"由告警系统自动创建，APIServer 告警ID: {alert_id}",
    })

    if result["success"]:
        card_id = str(result.get("data", {}).get("id", ""))
        if card_id:
            record.icafe_card_id = card_id
            db.commit()
        return APIResponse(
            success=True,
            data={"alert_id": alert_id, "card_title": title, "icafe_card_id": card_id, "icafe_result": result["data"]},
            message="iCafe 卡片创建成功",
        )
    else:
        return APIResponse(success=False, error=result["message"], message="iCafe 卡片创建失败")
