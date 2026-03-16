"""
告警管理 API
"""
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.core.deps import get_db
from app.models.alert import AlertRecord, DiagnosisResult
from app.schemas.response import APIResponse
from app.schemas.alert.alert import AlertRecordResponse, AlertListResponse, AlertListItem, AlertStatusUpdate
from app.schemas.alert.diagnosis import DiagnosisResultResponse
from app.services.alert.database_corrector import get_database_corrector

import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/alerts", response_model=APIResponse)
async def get_alerts(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    alert_type: Optional[str] = Query(None, description="告警类型"),
    severity: Optional[str] = Query(None, description="严重程度"),
    component: Optional[str] = Query(None, description="组件类型"),
    status: Optional[str] = Query(None, description="处理状态"),
    start_time: Optional[str] = Query(None, description="开始时间(ISO 8601格式)"),
    end_time: Optional[str] = Query(None, description="结束时间(ISO 8601格式)"),
    sort_by: Optional[str] = Query("timestamp", description="排序字段(timestamp/severity/status/alert_type)"),
    sort_order: Optional[str] = Query("desc", description="排序方向(asc/desc)"),
    db: Session = Depends(get_db)
):
    """
    获取告警列表
    
    支持分页和多条件筛选
    支持按字段排序（默认按发生时间降序）
    """
    try:
        # 构建查询
        query = db.query(AlertRecord)
        
        # 应用过滤条件（处理空字符串）
        if alert_type and alert_type.strip():
            query = query.filter(AlertRecord.alert_type == alert_type)
        if severity and severity.strip():
            query = query.filter(AlertRecord.severity == severity)
        if component and component.strip():
            query = query.filter(AlertRecord.component == component)
        if status and status.strip():
            query = query.filter(AlertRecord.status == status)
        
        # 处理时间参数（字符串转datetime）
        if start_time and start_time.strip():
            try:
                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                query = query.filter(AlertRecord.timestamp >= start_dt)
            except ValueError:
                logger.warning(f"无效的开始时间格式: {start_time}")
        
        if end_time and end_time.strip():
            try:
                end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                query = query.filter(AlertRecord.timestamp <= end_dt)
            except ValueError:
                logger.warning(f"无效的结束时间格式: {end_time}")
        
        # 获取总数
        total = query.count()
        
        # 排序逻辑
        sort_field_map = {
            'id': AlertRecord.id,
            'timestamp': AlertRecord.timestamp,
            'severity': AlertRecord.severity,
            'status': AlertRecord.status,
            'alert_type': AlertRecord.alert_type,
            'component': AlertRecord.component,
            'ip': AlertRecord.ip,
            'cluster_id': AlertRecord.cluster_id
        }
        
        # 验证排序字段
        if sort_by not in sort_field_map:
            sort_by = 'timestamp'  # 默认按时间排序
        
        # 验证排序方向
        if sort_order not in ['asc', 'desc']:
            sort_order = 'desc'  # 默认降序
        
        # 应用排序
        sort_field = sort_field_map[sort_by]
        if sort_order == 'desc':
            query = query.order_by(desc(sort_field))
        else:
            query = query.order_by(sort_field)
        
        # 分页查询
        offset = (page - 1) * page_size
        alerts = query.offset(offset).limit(page_size).all()
        
        # 构建响应
        alert_list = []
        for alert in alerts:
            has_diagnosis = db.query(DiagnosisResult).filter(
                DiagnosisResult.alert_id == alert.id
            ).order_by(DiagnosisResult.created_at.desc()).first() is not None
            
            # 映射 severity 值：ERROR→critical, FAIL/WARN→warning, GOOD→info
            severity_mapped = alert.severity
            if alert.severity == 'ERROR':
                severity_mapped = 'critical'
            elif alert.severity in ['FAIL', 'WARN']:
                severity_mapped = 'warning'
            elif alert.severity == 'GOOD':
                severity_mapped = 'info'
            
            alert_list.append(AlertListItem(
                id=alert.id,
                alert_type=alert.alert_type,
                ip=alert.ip,
                cluster_id=alert.cluster_id,
                instance_id=alert.instance_id,
                hostname=alert.hostname,
                component=alert.component,
                severity=severity_mapped,
                timestamp=alert.timestamp,
                status=alert.status,
                has_diagnosis=has_diagnosis
            ))
        
        data = AlertListResponse(
            list=alert_list,
            total=total,
            page=page,
            page_size=page_size
        )
        
        return APIResponse(
            success=True,
            data=data.dict(),
            message="获取成功"
        )
        
    except Exception as e:
        logger.error(f"获取告警列表失败: {e}")
        return APIResponse(
            success=False,
            error=str(e),
            message="获取告警列表失败"
        )
@router.get("/alerts/filter-options", response_model=APIResponse)
async def get_filter_options(
    db: Session = Depends(get_db)
):
    """
    获取筛选选项
    
    返回所有可用的筛选选项(告警类型、组件、集群等)
    用于前端动态生成筛选器
    """
    try:
        # 查询所有唯一的告警类型
        alert_types = db.query(AlertRecord.alert_type).distinct().filter(
            AlertRecord.alert_type.isnot(None)
        ).all()
        alert_types = [row[0] for row in alert_types]
        
        # 查询所有唯一的组件
        components = db.query(AlertRecord.component).distinct().filter(
            AlertRecord.component.isnot(None)
        ).all()
        components = [row[0] for row in components]
        
        # 查询所有唯一的集群
        clusters = db.query(AlertRecord.cluster_id).distinct().filter(
            AlertRecord.cluster_id.isnot(None)
        ).all()
        clusters = [row[0] for row in clusters]
        
        # 查询所有唯一的严重程度
        severity_levels = db.query(AlertRecord.severity).distinct().filter(
            AlertRecord.severity.isnot(None)
        ).all()
        severity_levels = [row[0] for row in severity_levels]
        
        # 映射 severity 值：ERROR→critical, FAIL/WARN→warning, GOOD→info
        severity_levels_mapped = set()
        for level in severity_levels:
            if level == 'ERROR':
                severity_levels_mapped.add('critical')
            elif level in ['FAIL', 'WARN']:
                severity_levels_mapped.add('warning')
            elif level == 'GOOD':
                severity_levels_mapped.add('info')
        severity_levels = sorted(list(severity_levels_mapped))
        
        # 查询所有唯一的状态
        statuses = db.query(AlertRecord.status).distinct().filter(
            AlertRecord.status.isnot(None)
        ).all()
        statuses = [row[0] for row in statuses]
        
        return APIResponse(
            success=True,
            data={
                "alert_types": sorted(alert_types),
                "components": sorted(components),
                "clusters": sorted(clusters),
                "severity_levels": sorted(severity_levels),
                "statuses": sorted(statuses)
            },
            message="获取成功"
        )
        
    except Exception as e:
        logger.error(f"获取筛选选项失败: {e}")
        return APIResponse(
            success=False,
            error=str(e),
            message="获取筛选选项失败"
        )


@router.get("/alerts/detect-incorrect", response_model=APIResponse)
async def detect_incorrect_alerts(db: Session = Depends(get_db)):
    """
    检测需要修正cluster_id的告警记录

    从宿主机数据库查询正确的cluster_id，对比容器内数据库的记录
    """
    try:
        corrector = get_database_corrector()
        incorrect_records = corrector.detect_incorrect_records(db)

        return APIResponse(
            success=True,
            data={
                'total': len(incorrect_records),
                'records': incorrect_records
            },
            message=f"检测完成，找到 {len(incorrect_records)} 条需要修正的记录"
        )

    except Exception as e:
        logger.error(f"检测不正确告警记录失败: {e}", exc_info=True)
        return APIResponse(
            success=False,
            error=str(e),
            message="检测失败"
        )


@router.get("/alerts/test-host-connection", response_model=APIResponse)
async def test_host_database_connection(
    db: Session = Depends(get_db)
):
    """
    测试宿主机数据库连接

    用于检查数据库修正功能的前置条件
    """
    try:
        corrector = get_database_corrector()
        result = corrector.test_host_connection()

        return APIResponse(
            success=result['success'],
            data=result,
            message=result['message'],
            error=result.get('error')
        )

    except Exception as e:
        logger.error(f"测试宿主机数据库连接失败: {e}", exc_info=True)
        return APIResponse(
            success=False,
            error=str(e),
            message="测试连接失败"
        )


@router.get("/alerts/{alert_id}", response_model=APIResponse)
async def get_alert_detail(
    alert_id: int,
    db: Session = Depends(get_db)
):
    """
    获取告警详情
    
    包含告警基本信息和诊断结果
    """
    try:
        # 查询告警
        alert = db.query(AlertRecord).filter(AlertRecord.id == alert_id).first()
        if not alert:
            return APIResponse(
                success=False,
                error="告警不存在",
                message=f"未找到ID为 {alert_id} 的告警"
            )
        
        # 查询诊断结果（按创建时间降序，获取最新的）
        diagnosis = db.query(DiagnosisResult).filter(
            DiagnosisResult.alert_id == alert_id
        ).order_by(DiagnosisResult.created_at.desc()).first()
        
        # 映射 severity 值：ERROR→critical, FAIL/WARN→warning, GOOD→info
        severity_mapped = alert.severity
        if alert.severity == 'ERROR':
            severity_mapped = 'critical'
        elif alert.severity in ['FAIL', 'WARN']:
            severity_mapped = 'warning'
        elif alert.severity == 'GOOD':
            severity_mapped = 'info'
        
        # 构建响应
        alert_data = AlertRecordResponse.from_orm(alert)
        # 覆盖 severity 字段为映射后的值
        alert_dict = alert_data.dict()
        alert_dict['severity'] = severity_mapped
        
        diagnosis_data = DiagnosisResultResponse.from_orm(diagnosis) if diagnosis else None
        
        return APIResponse(
            success=True,
            data={
                "alert": alert_dict,
                "diagnosis": diagnosis_data.dict() if diagnosis_data else None
            },
            message="获取成功"
        )
        
    except Exception as e:
        logger.error(f"获取告警详情失败: {e}")
        return APIResponse(
            success=False,
            error=str(e),
            message="获取告警详情失败"
        )


@router.post("/alerts/{alert_id}/diagnose", response_model=APIResponse)
async def trigger_diagnosis(
    alert_id: int,
    force: bool = Query(False, description="是否强制重新诊断"),
    db: Session = Depends(get_db)
):
    """
    手动触发诊断
    
    为指定告警创建诊断任务
    """
    try:
        # 查询告警
        alert = db.query(AlertRecord).filter(AlertRecord.id == alert_id).first()
        if not alert:
            return APIResponse(
                success=False,
                error="告警不存在",
                message=f"未找到ID为 {alert_id} 的告警"
            )
        
        # 检查是否已有诊断结果
        existing_diagnosis = db.query(DiagnosisResult).filter(
            DiagnosisResult.alert_id == alert_id
        ).first()
        
        if existing_diagnosis and not force:
            return APIResponse(
                success=False,
                error="已存在诊断结果",
                message="该告警已有诊断结果,如需重新诊断请设置 force=true"
            )
        
        # 如果force=true，删除已有诊断结果，当做新告警处理
        if existing_diagnosis and force:
            logger.info(f"强制重新诊断，删除已有诊断结果: 告警ID={alert_id}")
            logger.info(f"删除前 cluster_id={alert.cluster_id}")
            db.delete(existing_diagnosis)
            db.commit()
            # 刷新告警记录，获取最新的字段值（用户可能已手动修正）
            db.expire(alert)  # 先过期缓存
            db.refresh(alert)  # 再刷新
            logger.info(f"刷新后 cluster_id={alert.cluster_id}")
        else:
            # 即使不删除诊断结果，也要刷新告警记录获取最新数据
            logger.info(f"刷新告警记录获取最新数据: alert_id={alert_id}")
            logger.info(f"刷新前 cluster_id={alert.cluster_id}")
            db.expire(alert)  # 先过期缓存
            db.refresh(alert)  # 再刷新
            logger.info(f"刷新后 cluster_id={alert.cluster_id}")
        
        # 调用告警处理器，当做新告警处理（不使用force_recreate标记）
        from app.services.alert.alert_processor import AlertProcessor
        processor = AlertProcessor()
        
        # 准备告警数据（使用数据库中的最新数据，包含用户修正）
        alert_data = {
            'alert_type': alert.alert_type,
            'component': alert.component,
            'severity': alert.severity,
            'ip': alert.ip,
            'cluster_id': alert.cluster_id,  # 使用用户修正后的值
            'instance_id': alert.instance_id,
            'hostname': alert.hostname,
            'is_cce_cluster': alert.cluster_id and alert.cluster_id.startswith('cce-'),  # 重新判断CCE类型
            'timestamp': alert.timestamp,
            'raw_data': alert.raw_data or {}  # 保留原始数据
            # 不添加force_recreate标记，让系统当做新告警处理
        }
        
        logger.info(f"开始重新诊断（当做新告警处理): alert_id={alert_id}, force={force}")
        logger.info(f"告警数据: cluster_id={alert_data['cluster_id']}, is_cce={alert_data['is_cce_cluster']}")
        
        # 当做新告警处理（完整流程：手册匹配、AI解读、诊断API、通知）
        try:
            success = await processor.process_single_alert(alert_data)
            logger.info(f"重新诊断处理结果: success={success}, alert_id={alert_id}")
            
            if success:
                return APIResponse(
                    success=True,
                    data={
                        "task_id": f"diag_{alert_id}_{int(datetime.now().timestamp())}",
                        "status": "completed",
                        "message": "重新诊断完成，包含手册匹配、AI解读和诊断API调用"
                    },
                    message="重新诊断任务已完成"
                )
            else:
                return APIResponse(
                    success=False,
                    error="重新诊断失败",
                    message="重新诊断任务处理失败，请检查告警数据"
                )
        except Exception as e:
            logger.error(f"重新诊断处理异常: alert_id={alert_id}, error={str(e)}", exc_info=True)
            return APIResponse(
                success=False,
                error=str(e),
                message="重新诊断任务执行异常"
            )
        
    except Exception as e:
        logger.error(f"触发诊断失败: {e}")
        return APIResponse(
            success=False,
            error=str(e),
            message="触发诊断失败"
        )


@router.post("/alerts/{alert_id}/resend-notification", response_model=APIResponse)
async def resend_alert_notification(
    alert_id: int,
    db: Session = Depends(get_db)
):
    """
    重新发送告警通知
    
    用于首次部署时webhook未配置，导致告警未通知的情况
    """
    try:
        # 查询告警
        alert = db.query(AlertRecord).filter(AlertRecord.id == alert_id).first()
        if not alert:
            return APIResponse(
                success=False,
                error="告警不存在",
                message=f"未找到ID为 {alert_id} 的告警"
            )
        
        # 查询诊断结果（获取最新的）
        diagnosis = db.query(DiagnosisResult).filter(
            DiagnosisResult.alert_id == alert_id
        ).order_by(DiagnosisResult.created_at.desc()).first()
        
        if not diagnosis:
            return APIResponse(
                success=False,
                error="诊断结果不存在",
                message=f"告警 {alert_id} 没有诊断结果"
            )
        
        # 检查是否已通知
        if diagnosis.notified:
            return APIResponse(
                success=False,
                error="已发送通知",
                message=f"告警 {alert_id} 已在 {diagnosis.notified_at} 发送过通知"
            )
        
        # 发送通知
        from app.services.alert.webhook_notifier import WebhookNotifier
        from app.core.redis_client import get_redis_client
        
        # 获取Redis客户端
        redis_client = None
        try:
            redis_wrapper = get_redis_client()
            redis_client = redis_wrapper.client
        except Exception as e:
            logger.warning(f"无法获取Redis客户端: {str(e)}")
        
        notifier = WebhookNotifier(db, redis_client=redis_client)
        success = await notifier.send_alert_notification(alert, diagnosis)
        
        if success:
            return APIResponse(
                success=True,
                data={
                    "alert_id": alert_id,
                    "notified": diagnosis.notified,
                    "notified_at": diagnosis.notified_at.isoformat() if diagnosis.notified_at else None
                },
                message="通知发送成功"
            )
        else:
            return APIResponse(
                success=False,
                error="通知发送失败",
                message="请检查webhook配置是否正确"
            )
            
    except Exception as e:
        logger.error(f"重新发送通知失败: {e}", exc_info=True)
        return APIResponse(
            success=False,
            error=str(e),
            message="重新发送通知失败"
        )


@router.post("/alerts/batch-resend-notification", response_model=APIResponse)
async def batch_resend_notifications(
    alert_ids: Optional[list[int]] = Query(None, description="指定告警ID列表（为空则补发所有未通知的告警）"),
    db: Session = Depends(get_db)
):
    """
    批量重新发送未通知的告警
    
    - 如果提供alert_ids参数，则只补发指定ID的告警
    - 如果不提供alert_ids参数，则补发所有未通知的告警
    
    用于首次部署时webhook未配置，批量补发所有未通知的告警
    """
    try:
        # 构建查询
        query = db.query(DiagnosisResult).filter(
            DiagnosisResult.notified == False
        )
        
        # 如果指定了告警ID列表，则只查询这些ID
        if alert_ids:
            query = query.filter(DiagnosisResult.alert_id.in_(alert_ids))
        
        unnotified_diagnoses = query.all()
        
        if not unnotified_diagnoses:
            return APIResponse(
                success=True,
                data={
                    "total": 0,
                    "success": 0,
                    "failed": 0
                },
                message="没有需要补发的告警通知"
            )
        
        # 批量发送通知
        from app.services.alert.webhook_notifier import WebhookNotifier
        from app.core.redis_client import get_redis_client
        
        # 获取Redis客户端
        redis_client = None
        try:
            redis_wrapper = get_redis_client()
            redis_client = redis_wrapper.client
        except Exception as e:
            logger.warning(f"无法获取Redis客户端: {str(e)}")
        
        notifier = WebhookNotifier(db, redis_client=redis_client)
        success_count = 0
        failed_count = 0
        
        for diagnosis in unnotified_diagnoses:
            # 查询对应的告警记录
            alert = db.query(AlertRecord).filter(
                AlertRecord.id == diagnosis.alert_id
            ).first()
            
            if not alert:
                logger.warning(f"告警 {diagnosis.alert_id} 不存在，跳过")
                failed_count += 1
                continue
            
            # 发送通知
            try:
                success = await notifier.send_alert_notification(alert, diagnosis)
                if success:
                    success_count += 1
                    logger.info(f"✅ 告警 {alert.id} 通知补发成功")
                else:
                    failed_count += 1
                    logger.warning(f"⚠️ 告警 {alert.id} 通知补发失败")
            except Exception as e:
                failed_count += 1
                logger.error(f"❌ 告警 {alert.id} 通知补发异常: {e}")
        
        return APIResponse(
            success=True,
            data={
                "total": len(unnotified_diagnoses),
                "success": success_count,
                "failed": failed_count
            },
            message=f"批量补发完成：成功 {success_count} 个，失败 {failed_count} 个"
        )
        
    except Exception as e:
        logger.error(f"批量重新发送通知失败: {e}", exc_info=True)
        return APIResponse(
            success=False,
            error=str(e),
            message="批量重新发送通知失败"
        )



@router.put("/alerts/{alert_id}/status", response_model=APIResponse)
async def update_alert_status(
    alert_id: int,
    status_update: AlertStatusUpdate,
    db: Session = Depends(get_db)
):
    """
    更新告警状态
    
    支持将告警标记为已处理(resolved)或重新打开(pending)
    """
    try:
        # 查询告警
        alert = db.query(AlertRecord).filter(AlertRecord.id == alert_id).first()
        if not alert:
            return APIResponse(
                success=False,
                error="告警不存在",
                message=f"未找到ID为 {alert_id} 的告警"
            )
        
        # 验证请求参数
        if not status_update.status and not status_update.resolution_notes:
            return APIResponse(
                success=False,
                error="参数错误",
                message="必须提供status或resolution_notes中的至少一个"
            )
        
        # 如果只更新备注
        if not status_update.status and status_update.resolution_notes is not None:
            alert.resolution_notes = status_update.resolution_notes
            logger.info(f"告警备注更新: ID={alert.id}, 操作人=系统管理员")
            
            db.commit()
            db.refresh(alert)
            
            return APIResponse(
                success=True,
                data={
                    "id": alert.id,
                    "status": alert.status,
                    "resolution_notes": alert.resolution_notes
                },
                message="备注更新成功"
            )
        
        # 验证状态值和转换规则
        valid_statuses = ['pending', 'processing', 'diagnosed', 'notified', 'failed', 'resolved']
        if status_update.status not in valid_statuses:
            return APIResponse(
                success=False,
                error="无效的状态值",
                message=f"状态必须是以下之一: {', '.join(valid_statuses)}"
            )
        
        # 状态转换规则验证
        current_status = alert.status
        new_status = status_update.status
        
        # 定义允许的状态转换
        allowed_transitions = {
            'pending': ['processing', 'resolved'],
            'processing': ['diagnosed', 'failed', 'resolved'],
            'diagnosed': ['notified', 'resolved'],
            'notified': ['resolved'],
            'failed': ['pending', 'resolved'],
            'resolved': ['pending']  # 允许重新打开
        }
        
        if new_status not in allowed_transitions.get(current_status, []):
            return APIResponse(
                success=False,
                error="无效的状态转换",
                message=f"不能从 '{current_status}' 转换到 '{new_status}'"
            )
        
        # 更新状态（考虑与自动流程的兼容性）
        old_status = alert.status
        alert.status = status_update.status
        
        # 如果标记为已处理，记录处理信息
        if status_update.status == 'resolved':
            alert.resolved_at = datetime.now()
            if status_update.resolution_notes:
                alert.resolution_notes = status_update.resolution_notes
            # TODO: 从当前用户获取处理人信息
            alert.resolved_by = "系统管理员"  # 暂时使用默认值
        elif status_update.status == 'pending':
            # 如果重新打开，清除处理信息
            alert.resolved_at = None
            alert.resolved_by = None
            alert.resolution_notes = None
        
        # 记录状态变更日志
        logger.info(f"告警状态手动更新: ID={alert.id}, {old_status} → {status_update.status}, 操作人=系统管理员")
        
        db.commit()
        db.refresh(alert)
        
        logger.info(f"告警 {alert_id} 状态已更新: {old_status} → {status_update.status}")
        
        return APIResponse(
            success=True,
            data={
                "id": alert.id,
                "status": alert.status,
                "resolved_by": alert.resolved_by,
                "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
                "resolution_notes": alert.resolution_notes
            },
            message="状态更新成功"
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"更新告警状态失败: {e}", exc_info=True)
        return APIResponse(
            success=False,
            error=str(e),
            message="更新告警状态失败"
        )


@router.post("/alerts/correct-filenames", response_model=APIResponse)
async def correct_alert_filenames(
    dry_run: bool = Query(True, description="是否为试运行模式"),
    db: Session = Depends(get_db)
):
    """
    批量修正长安告警文件名中的cluster_id
    
    通过宿主机数据库查询正确的cluster_id并修正文件名
    """
    try:
        from app.services.alert.filename_corrector import get_filename_corrector
        
        corrector = get_filename_corrector()
        
        # 批量修正告警目录中的文件名
        alert_dir = "/app/alerts"  # 容器内的告警目录
        
        stats = corrector.batch_correct_directory(alert_dir, dry_run=dry_run)
        
        return APIResponse(
            success=True,
            data=stats,
            message=f"文件名修正完成 (试运行模式: {dry_run})"
        )
        
    except Exception as e:
        logger.error(f"批量修正文件名失败: {e}", exc_info=True)
        return APIResponse(
            success=False,
            error=str(e),
            message="批量修正文件名失败"
        )


@router.post("/alerts/{alert_id}/create-icafe-card", response_model=APIResponse)
async def create_icafe_card(
    alert_id: int,
    card_data: dict,
    db: Session = Depends(get_db)
):
    """
    为指定告警创建 iCafe 卡片
    
    Args:
        alert_id: 告警ID
        card_data: 卡片数据
            - responsible_person: 负责人
            - subcategory: 细分分类
            - work_hours: 工时
            - plan: 所属计划
    """
    try:
        # 查询告警信息
        alert = db.query(AlertRecord).filter(AlertRecord.id == alert_id).first()
        if not alert:
            return APIResponse(
                success=False,
                error="告警不存在",
                message=f"未找到ID为 {alert_id} 的告警"
            )
        
        # 查询诊断信息（获取最新的）
        diagnosis = db.query(DiagnosisResult).filter(
            DiagnosisResult.alert_id == alert_id
        ).order_by(DiagnosisResult.created_at.desc()).first()
        
        # 获取 iCafe 配置
        from app.models.system_config import SystemConfig
        icafe_config_record = db.query(SystemConfig).filter(
            SystemConfig.module == 'icafe',
            SystemConfig.config_key == 'main'
        ).first()
        
        if not icafe_config_record:
            return APIResponse(
                success=False,
                error="iCafe 配置不存在",
                message="请先在系统配置中配置 iCafe API 信息"
            )
        
        icafe_config = icafe_config_record.config_value
        
        # 如果是字符串，解析为字典
        if isinstance(icafe_config, str):
            import json
            icafe_config = json.loads(icafe_config)
        
        # 创建 iCafe 服务
        from app.services.icafe.icafe_service import get_icafe_service
        icafe_service = get_icafe_service(icafe_config)
        
        # 准备告警数据
        alert_data = {
            'id': alert.id,
            'alert_type': alert.alert_type,
            'component': alert.component,
            'severity': alert.severity,
            'ip': alert.ip,
            'cluster_id': alert.cluster_id,
            'hostname': alert.hostname,
            'timestamp': alert.timestamp.strftime('%Y-%m-%d %H:%M:%S') if alert.timestamp else ''
        }
        
        # 准备诊断数据
        diagnosis_data = None
        if diagnosis:
            diagnosis_data = {
                'manual_matched': diagnosis.manual_matched,
                'manual_solution': diagnosis.manual_solution,
                'ai_interpretation': diagnosis.ai_interpretation
            }
        
        # 生成卡片标题和详情
        title = icafe_service.generate_card_title(alert_data)
        detail = icafe_service.generate_card_detail(alert_data, diagnosis_data)
        
        # 构建卡片字段
        fields = icafe_service.build_card_fields(card_data)
        
        # 创建卡片
        create_data = {
            'title': title,
            'detail': detail,
            'type': 'Bug',  # 使用 Bug 类型（与 HMLCC 空间自定义字段匹配）
            'fields': fields,
            'creator': icafe_config.get('username', ''),
            'comment': f'由告警系统自动创建，告警ID: {alert_id}'
        }
        
        result = icafe_service.create_card(create_data)
        
        if result['success']:
            logger.info(f"告警 {alert_id} 成功创建 iCafe 卡片: {title}")
            return APIResponse(
                success=True,
                data={
                    'alert_id': alert_id,
                    'card_title': title,
                    'icafe_result': result['data']
                },
                message="iCafe 卡片创建成功"
            )
        else:
            return APIResponse(
                success=False,
                error=result['message'],
                message="iCafe 卡片创建失败"
            )
            
    except Exception as e:
        logger.error(f"创建 iCafe 卡片失败: {e}", exc_info=True)
        return APIResponse(
            success=False,
            error=str(e),
            message="创建 iCafe 卡片失败"
        )


@router.post("/alerts/correct-cluster-ids", response_model=APIResponse)
async def correct_cluster_ids(
    alert_ids: Optional[list] = None,
    db: Session = Depends(get_db)
):
    """
    批量修正告警记录的cluster_id
    
    Args:
        alert_ids: 可选的告警ID列表，如果不提供则修正所有需要修正的记录
    """
    try:
        corrector = get_database_corrector()
        
        # 如果提供了alert_ids，验证格式
        if alert_ids is not None:
            if not isinstance(alert_ids, list):
                return APIResponse(
                    success=False,
                    error="alert_ids必须是数组格式",
                    message="参数格式错误"
                )
            
            # 转换为整数列表
            try:
                alert_ids = [int(aid) for aid in alert_ids]
            except (ValueError, TypeError):
                return APIResponse(
                    success=False,
                    error="alert_ids数组中包含无效的ID",
                    message="参数格式错误"
                )
        
        # 执行批量修正
        result = corrector.correct_batch_records(alert_ids, db)
        
        if result['success']:
            return APIResponse(
                success=True,
                data=result,
                message=f"修正完成：成功 {result['corrected']} 个，跳过 {result['skipped']} 个，失败 {result['failed']} 个"
            )
        else:
            return APIResponse(
                success=False,
                error=result.get('error', '未知错误'),
                message="批量修正失败"
            )
            
    except Exception as e:
        logger.error(f"批量修正cluster_id失败: {e}", exc_info=True)
        return APIResponse(
            success=False,
            error=str(e),
            message="批量修正失败"
        )


@router.post("/alerts/{alert_id}/correct-cluster-id", response_model=APIResponse)
async def correct_single_alert_cluster_id(
    alert_id: int,
    db: Session = Depends(get_db)
):
    """
    修正单个告警记录的cluster_id
    
    Args:
        alert_id: 告警记录ID
    """
    try:
        corrector = get_database_corrector()
        result = corrector.correct_single_record(alert_id, db)
        
        if result['success']:
            if result.get('changed', False):
                return APIResponse(
                    success=True,
                    data=result,
                    message=f"修正成功：{result['old_cluster_id']} -> {result['new_cluster_id']}"
                )
            else:
                return APIResponse(
                    success=True,
                    data=result,
                    message="cluster_id已正确，无需修正"
                )
        else:
            return APIResponse(
                success=False,
                error=result.get('error', '未知错误'),
                message="修正失败"
            )
            
    except Exception as e:
        logger.error(f"修正单个告警cluster_id失败: alert_id={alert_id}, 错误={e}", exc_info=True)
        return APIResponse(
            success=False,
            error=str(e),
            message="修正失败"
        )


@router.put("/alerts/{alert_id}", response_model=APIResponse)
async def update_alert_fields(
    alert_id: int,
    alert_data: dict,
    db: Session = Depends(get_db)
):
    """
    更新告警字段
    
    支持更新告警的基本字段：组件、严重程度、IP、集群ID等
    """
    try:
        # 查询告警
        alert = db.query(AlertRecord).filter(AlertRecord.id == alert_id).first()
        if not alert:
            return APIResponse(
                success=False,
                error="告警不存在",
                message=f"未找到ID为 {alert_id} 的告警"
            )
        
        # 允许更新的字段
        allowed_fields = {
            'component', 'severity', 'ip', 'cluster_id', 
            'hostname', 'instance_id', 'alert_type'
        }
        
        updated_fields = []
        for field, value in alert_data.items():
            if field in allowed_fields and hasattr(alert, field):
                old_value = getattr(alert, field)
                if old_value != value:
                    setattr(alert, field, value)
                    updated_fields.append(f"{field}: {old_value} → {value}")
        
        if not updated_fields:
            return APIResponse(
                success=True,
                data={"id": alert_id, "updated_fields": []},
                message="没有字段需要更新"
            )
        
        # 如果更新了cluster_id，同时更新is_cce_cluster字段
        if 'cluster_id' in alert_data:
            alert.is_cce_cluster = alert_data['cluster_id'].startswith('cce-') if alert_data['cluster_id'] else False
        
        db.commit()
        db.refresh(alert)
        
        logger.info(f"告警字段更新成功: ID={alert_id}, 更新字段={updated_fields}")
        
        return APIResponse(
            success=True,
            data={
                "id": alert_id,
                "updated_fields": updated_fields
            },
            message=f"成功更新 {len(updated_fields)} 个字段"
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"更新告警字段失败: ID={alert_id}, 错误={e}", exc_info=True)
        return APIResponse(
            success=False,
            error=str(e),
            message="更新告警字段失败"
        )