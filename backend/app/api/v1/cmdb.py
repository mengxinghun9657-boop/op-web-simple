"""
CMDB API - 服务器资源管理
支持API自动同步、Cookie管理、定时同步等功能
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct, or_
from typing import Optional, List, Dict, Any
from loguru import logger
from datetime import datetime
import pandas as pd
import io

from app.core.deps import get_db, get_current_user
from app.models.iaas import IaasServer, IaasInstance
from app.models.user import UserRole
from app.services.cmdb_sync_service import CMDBSyncService
from app.schemas.response import APIResponse

router = APIRouter()


def require_admin(current_user = Depends(get_current_user)):
    """要求管理员权限"""
    if current_user.role not in [UserRole.SUPER_ADMIN.value, UserRole.ADMIN.value, 'super_admin', 'admin']:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return current_user


def safe_int(val, default=0):
    """安全转换为整数"""
    if pd.isna(val) or val == '-' or val == '':
        return default
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return default

def safe_str(val):
    """安全转换为字符串"""
    if pd.isna(val) or val == '-':
        return None
    return str(val) if val else None


@router.post("/import")
async def import_iaas_data(
    file: UploadFile = File(...),
    mode: str = Query("update", description="导入模式: update=更新, replace=覆盖"),
    db: Session = Depends(get_db),
    current_user = Depends(require_admin)
):
    """导入IaaS数据Excel文件（仅管理员）"""
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="仅支持Excel文件")
    
    try:
        content = await file.read()
        df = pd.read_excel(io.BytesIO(content), sheet_name='iaas数据源')
        
        # 覆盖模式：先清空旧数据
        if mode == "replace":
            db.query(IaasInstance).delete()
            db.query(IaasServer).delete()
        
        # 处理服务器数据（去重）
        server_cols = [
            'bns_hostname', 'rms_sn', 'rms_suit', 'rms_type', 'rms_model',
            'rms_manufacturer', 'rms_product', 'rms_cpu', 'rms_memory', 'rms_ssd',
            'nova_host_node_type', 'nova_host_model', 'nova_host_physical_memory_mb_total',
            'nova_host_physical_memory_mb_free', 'nova_host_physical_disk_gb_free',
            'nova_host_vcpus_total', 'nova_host_vcpus_used', 'nova_host_vcpus_free',
            'nova_host_running_vms', 'nova_host_physical_cpus',
            'nova_host_blacklisted_description', 'nova_host_blacklisted_reason'
        ]
        df_servers = df[server_cols].drop_duplicates(subset=['bns_hostname'])
        
        servers_added = 0
        servers_updated = 0
        for _, row in df_servers.iterrows():
            hostname = safe_str(row['bns_hostname'])
            if not hostname:
                continue
                
            # 查找是否存在
            existing = db.query(IaasServer).filter(IaasServer.bns_hostname == hostname).first()
            
            server_data = {
                'rms_sn': safe_str(row['rms_sn']),
                'rms_suit': safe_str(row['rms_suit']),
                'rms_type': safe_str(row['rms_type']),
                'rms_model': safe_str(row['rms_model']),
                'rms_manufacturer': safe_str(row['rms_manufacturer']),
                'rms_product': safe_str(row['rms_product']),
                'rms_cpu': safe_str(row['rms_cpu']),
                'rms_memory': safe_str(row['rms_memory']),
                'rms_ssd': safe_str(row['rms_ssd']),
                'nova_host_node_type': safe_str(row['nova_host_node_type']),
                'nova_host_model': safe_str(row['nova_host_model']),
                'nova_host_physical_memory_mb_total': safe_int(row['nova_host_physical_memory_mb_total']),
                'nova_host_physical_memory_mb_free': safe_int(row['nova_host_physical_memory_mb_free']),
                'nova_host_physical_disk_gb_free': safe_int(row['nova_host_physical_disk_gb_free']),
                'nova_host_vcpus_total': safe_int(row['nova_host_vcpus_total']),
                'nova_host_vcpus_used': safe_int(row['nova_host_vcpus_used']),
                'nova_host_vcpus_free': safe_int(row['nova_host_vcpus_free']),
                'nova_host_running_vms': safe_int(row['nova_host_running_vms']),
                'nova_host_physical_cpus': safe_int(row['nova_host_physical_cpus']),
                'nova_host_blacklisted_description': safe_str(row['nova_host_blacklisted_description']),
                'nova_host_blacklisted_reason': safe_str(row['nova_host_blacklisted_reason']),
            }
            
            if existing:
                for key, value in server_data.items():
                    setattr(existing, key, value)
                servers_updated += 1
            else:
                server = IaasServer(bns_hostname=hostname, **server_data)
                db.add(server)
                servers_added += 1
        
        # 处理实例数据
        instances_added = 0
        instances_updated = 0
        for _, row in df.iterrows():
            uuid_val = safe_str(row.get('nova_vm_instance_uuid'))
            if not uuid_val:
                continue
            
            existing = db.query(IaasInstance).filter(IaasInstance.nova_vm_instance_uuid == uuid_val).first()
            
            instance_data = {
                'bns_hostname': safe_str(row['bns_hostname']),
                'nova_vm_vm_state': safe_str(row['nova_vm_vm_state']),
                'nova_vm_fixed_ips': safe_str(row['nova_vm_fixed_ips']),
                'nova_vm_metadata_source': safe_str(row['nova_vm_metadata_source']),
                'nova_vm_vcpus': safe_int(row['nova_vm_vcpus']),
                'nova_vm_memory_mb': safe_int(row['nova_vm_memory_mb']),
                'nova_vm_root_gb': safe_int(row['nova_vm_root_gb']),
            }
            
            if existing:
                for key, value in instance_data.items():
                    setattr(existing, key, value)
                instances_updated += 1
            else:
                instance = IaasInstance(nova_vm_instance_uuid=uuid_val, **instance_data)
                db.add(instance)
                instances_added += 1
        
        db.commit()
        logger.info(f"CMDB数据导入完成: 服务器(新增{servers_added}/更新{servers_updated}), 实例(新增{instances_added}/更新{instances_updated})")
        
        return {
            "success": True,
            "message": "数据导入成功",
            "mode": mode,
            "servers": {"added": servers_added, "updated": servers_updated},
            "instances": {"added": instances_added, "updated": instances_updated}
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"CMDB数据导入失败: {e}")
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e)}")


@router.get("/stats")
async def get_cmdb_stats(db: Session = Depends(get_db)):
    """获取CMDB统计概览"""
    total_servers = db.query(func.count(IaasServer.id)).scalar()
    total_instances = db.query(func.count(IaasInstance.id)).scalar()
    
    # 实例状态统计
    instance_states = db.query(
        IaasInstance.nova_vm_vm_state,
        func.count(IaasInstance.id)
    ).group_by(IaasInstance.nova_vm_vm_state).all()
    
    # 资源汇总
    resource_stats = db.query(
        func.sum(IaasServer.nova_host_vcpus_total),
        func.sum(IaasServer.nova_host_vcpus_used),
        func.sum(IaasServer.nova_host_physical_memory_mb_total),
        func.sum(IaasServer.nova_host_physical_memory_mb_free),
    ).first()
    
    # 服务器品牌分布
    manufacturer_dist = db.query(
        IaasServer.rms_manufacturer,
        func.count(IaasServer.id)
    ).group_by(IaasServer.rms_manufacturer).all()
    
    # 节点类型分布
    node_type_dist = db.query(
        IaasServer.nova_host_node_type,
        func.count(IaasServer.id)
    ).group_by(IaasServer.nova_host_node_type).all()
    
    return {
        "total_servers": total_servers or 0,
        "total_instances": total_instances or 0,
        "instance_states": {state: count for state, count in instance_states if state},
        "resource_summary": {
            "vcpus_total": resource_stats[0] or 0,
            "vcpus_used": resource_stats[1] or 0,
            "vcpus_free": (resource_stats[0] or 0) - (resource_stats[1] or 0),
            "memory_total_gb": round((resource_stats[2] or 0) / 1024, 2),
            "memory_free_gb": round((resource_stats[3] or 0) / 1024, 2),
        },
        "manufacturer_distribution": {m: c for m, c in manufacturer_dist if m},
        "node_type_distribution": {n: c for n, c in node_type_dist if n},
    }


@router.get("/servers")
async def list_servers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    manufacturer: Optional[str] = None,
    node_type: Optional[str] = None,
    sort_by: Optional[str] = Query(None, description="排序字段: vcpus_used, memory_used, running_vms, disk_free"),
    sort_order: Optional[str] = Query("desc", description="排序方向: asc, desc"),
    db: Session = Depends(get_db)
):
    """获取服务器列表（支持排序和跨表搜索）"""
    query = db.query(IaasServer)

    if search:
        # 支持批量搜索：按换行符或英文逗号分割，过滤空值
        keywords = [k.strip() for k in search.replace('\n', ',').split(',') if k.strip()]

        all_conditions = []
        for kw in keywords:
            # 每个关键词：先找匹配IP或UUID的实例对应的主机名
            matching_hostnames = db.query(distinct(IaasInstance.bns_hostname)).filter(
                (IaasInstance.nova_vm_fixed_ips.contains(kw)) |
                (IaasInstance.nova_vm_instance_uuid.contains(kw))
            ).all()
            matching_hostnames = [h[0] for h in matching_hostnames if h[0]]

            # BCE 反向关联：从 bce_bcc_instances / bce_cce_nodes 中匹配 IP，再反查 CMDB
            try:
                from app.core.database import get_db_connection
                _conn = get_db_connection()
                _cur = _conn.cursor()
                bce_ips = set()
                # 匹配 BCC 实例名、实例ID、IP
                _cur.execute(
                    "SELECT `主ipv4私网地址` FROM `bce_bcc_instances`"
                    " WHERE `主ipv4私网地址` LIKE %s OR `名称` LIKE %s OR `bcc_id` LIKE %s"
                    " LIMIT 200",
                    (f'%{kw}%', f'%{kw}%', f'%{kw}%')
                )
                bce_ips.update(r[0] for r in _cur.fetchall() if r[0])
                # 匹配 CCE 节点名、IP
                _cur.execute(
                    "SELECT `ip地址` FROM `bce_cce_nodes`"
                    " WHERE `ip地址` LIKE %s OR `节点名称` LIKE %s"
                    " LIMIT 200",
                    (f'%{kw}%', f'%{kw}%')
                )
                bce_ips.update(r[0] for r in _cur.fetchall() if r[0])
                _cur.close()
                _conn.close()
                if bce_ips:
                    bce_hostnames = db.query(distinct(IaasInstance.bns_hostname)).filter(
                        or_(*[IaasInstance.nova_vm_fixed_ips.contains(ip) for ip in bce_ips])
                    ).all()
                    matching_hostnames += [h[0] for h in bce_hostnames if h[0] and h[0] not in matching_hostnames]
            except Exception as _e:
                logger.debug(f"BCE 反向关联查询跳过: {_e}")

            kw_conditions = [
                IaasServer.bns_hostname.contains(kw),
                IaasServer.rms_sn.contains(kw)
            ]
            if matching_hostnames:
                kw_conditions.append(IaasServer.bns_hostname.in_(matching_hostnames))

            all_conditions.append(or_(*kw_conditions))

        query = query.filter(or_(*all_conditions))
    if manufacturer:
        query = query.filter(IaasServer.rms_manufacturer == manufacturer)
    if node_type:
        query = query.filter(IaasServer.nova_host_node_type == node_type)
    
    # 排序处理
    sort_field_mapping = {
        'vcpus_used': IaasServer.nova_host_vcpus_used,
        'running_vms': IaasServer.nova_host_running_vms,
        'disk_free': IaasServer.nova_host_physical_disk_gb_free,
    }
    
    if sort_by:
        if sort_by == 'memory_used':
            # 内存使用量 = 总量 - 空闲量
            sort_expr = IaasServer.nova_host_physical_memory_mb_total - IaasServer.nova_host_physical_memory_mb_free
        elif sort_by in sort_field_mapping:
            sort_expr = sort_field_mapping[sort_by]
        else:
            sort_expr = None
        
        if sort_expr is not None:
            if sort_order == 'asc':
                query = query.order_by(sort_expr.asc())
            else:
                query = query.order_by(sort_expr.desc())
    
    total = query.count()
    servers = query.offset((page - 1) * page_size).limit(page_size).all()
    
    # 使用 SQLAlchemy 的 __dict__ 获取所有字段，并过滤掉内部属性
    def server_to_dict(server):
        """将服务器对象转换为字典，包含所有字段"""
        data = {}
        for column in server.__table__.columns:
            value = getattr(server, column.name)
            # 处理日期时间字段
            if value is not None and hasattr(value, 'isoformat'):
                data[column.name] = value.isoformat()
            else:
                data[column.name] = value
        
        # 添加计算字段
        data['vcpu_usage_percent'] = round(server.nova_host_vcpus_used / server.nova_host_vcpus_total * 100, 1) if server.nova_host_vcpus_total else 0
        data['memory_usage_percent'] = round((server.nova_host_physical_memory_mb_total - server.nova_host_physical_memory_mb_free) / server.nova_host_physical_memory_mb_total * 100, 1) if server.nova_host_physical_memory_mb_total else 0
        data['memory_used'] = server.nova_host_physical_memory_mb_total - server.nova_host_physical_memory_mb_free if server.nova_host_physical_memory_mb_total and server.nova_host_physical_memory_mb_free else 0
        
        # 添加 status 字段（根据加黑状态判断）
        if server.nova_host_blacklisted_reason:
            data['status'] = 'blacklisted'
        elif server.nova_host_node_state:
            data['status'] = server.nova_host_node_state
        else:
            data['status'] = 'normal'
        
        return data
    
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "data": [server_to_dict(s) for s in servers]
    }


@router.get("/servers/{hostname}")
async def get_server_detail(hostname: str, db: Session = Depends(get_db)):
    """获取服务器详情及其实例列表"""
    server = db.query(IaasServer).filter(IaasServer.bns_hostname == hostname).first()
    if not server:
        raise HTTPException(status_code=404, detail="服务器不存在")
    
    instances = db.query(IaasInstance).filter(IaasInstance.bns_hostname == hostname).all()
    
    # 使用相同的转换函数
    def server_to_dict(s):
        """将服务器对象转换为字典，包含所有字段"""
        data = {}
        for column in s.__table__.columns:
            value = getattr(s, column.name)
            if value is not None and hasattr(value, 'isoformat'):
                data[column.name] = value.isoformat()
            else:
                data[column.name] = value
        return data
    
    def instance_to_dict(i):
        """将实例对象转换为字典，包含所有字段"""
        data = {}
        for column in i.__table__.columns:
            value = getattr(i, column.name)
            if value is not None and hasattr(value, 'isoformat'):
                data[column.name] = value.isoformat()
            else:
                data[column.name] = value
        return data
    
    return {
        "server": server_to_dict(server),
        "instances": [instance_to_dict(i) for i in instances],
        "instance_count": len(instances)
    }


@router.get("/instances")
async def list_instances(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    state: Optional[str] = None,
    source: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取实例列表（支持跨表搜索）"""
    query = db.query(IaasInstance)

    if search:
        # 支持批量搜索：按换行符或英文逗号分割，过滤空值
        keywords = [k.strip() for k in search.replace('\n', ',').split(',') if k.strip()]

        all_conditions = []
        for kw in keywords:
            # 先查找匹配主机名或SN的服务器对应的主机名
            matching_servers = db.query(distinct(IaasServer.bns_hostname)).filter(
                (IaasServer.bns_hostname.contains(kw)) |
                (IaasServer.rms_sn.contains(kw))
            ).all()
            matching_hostnames = [h[0] for h in matching_servers if h[0]]

            # BCE 反向关联：从 BCE 表中查到 IP，再匹配实例
            bce_ips = set()
            try:
                from app.core.database import get_db_connection
                _conn = get_db_connection()
                _cur = _conn.cursor()
                _cur.execute(
                    "SELECT `主ipv4私网地址` FROM `bce_bcc_instances`"
                    " WHERE `主ipv4私网地址` LIKE %s OR `名称` LIKE %s OR `bcc_id` LIKE %s"
                    " LIMIT 200",
                    (f'%{kw}%', f'%{kw}%', f'%{kw}%')
                )
                bce_ips.update(r[0] for r in _cur.fetchall() if r[0])
                _cur.execute(
                    "SELECT `ip地址` FROM `bce_cce_nodes`"
                    " WHERE `ip地址` LIKE %s OR `节点名称` LIKE %s"
                    " LIMIT 200",
                    (f'%{kw}%', f'%{kw}%')
                )
                bce_ips.update(r[0] for r in _cur.fetchall() if r[0])
                _cur.close()
                _conn.close()
            except Exception as _e:
                logger.debug(f"BCE 反向关联查询跳过: {_e}")

            kw_conditions = [
                IaasInstance.nova_vm_instance_uuid.contains(kw),
                IaasInstance.nova_vm_fixed_ips.contains(kw),
                IaasInstance.bns_hostname.contains(kw)
            ]
            if matching_hostnames:
                kw_conditions.append(IaasInstance.bns_hostname.in_(matching_hostnames))
            if bce_ips:
                kw_conditions.append(or_(*[IaasInstance.nova_vm_fixed_ips.contains(ip) for ip in bce_ips]))

            all_conditions.append(or_(*kw_conditions))

        query = query.filter(or_(*all_conditions))
    if state:
        query = query.filter(IaasInstance.nova_vm_vm_state == state)
    if source:
        query = query.filter(IaasInstance.nova_vm_metadata_source == source)
    
    total = query.count()
    instances = query.offset((page - 1) * page_size).limit(page_size).all()
    
    # 使用 SQLAlchemy 的 __dict__ 获取所有字段，并过滤掉内部属性
    def instance_to_dict(instance):
        """将实例对象转换为字典，包含所有字段"""
        data = {}
        for column in instance.__table__.columns:
            value = getattr(instance, column.name)
            # 处理日期时间字段
            if value is not None and hasattr(value, 'isoformat'):
                data[column.name] = value.isoformat()
            else:
                data[column.name] = value
        return data
    
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "data": [instance_to_dict(i) for i in instances]
    }


@router.get("/filters")
async def get_filter_options(db: Session = Depends(get_db)):
    """获取筛选选项"""
    manufacturers = db.query(distinct(IaasServer.rms_manufacturer)).filter(IaasServer.rms_manufacturer.isnot(None)).all()
    node_types = db.query(distinct(IaasServer.nova_host_node_type)).filter(IaasServer.nova_host_node_type.isnot(None)).all()
    instance_states = db.query(distinct(IaasInstance.nova_vm_vm_state)).filter(IaasInstance.nova_vm_vm_state.isnot(None)).all()
    instance_sources = db.query(distinct(IaasInstance.nova_vm_metadata_source)).filter(IaasInstance.nova_vm_metadata_source.isnot(None)).all()
    
    return {
        "manufacturers": [m[0] for m in manufacturers if m[0] and m[0] != '-'],
        "node_types": [n[0] for n in node_types if n[0] and n[0] != '-'],
        "instance_states": [s[0] for s in instance_states if s[0]],
        "instance_sources": [s[0] for s in instance_sources if s[0]],
    }


# ========== API同步相关接口 ==========

@router.post("/sync")
async def sync_from_api(
    azone: str = Query("AZONE-cdhmlcc001", description="可用区"),
    page: int = Query(1, ge=1),
    per_page: int = Query(2000, ge=1, le=5000),
    db: Session = Depends(get_db),
    current_user = Depends(require_admin)
):
    """从AMIS API同步CMDB数据（仅管理员）"""
    try:
        sync_service = CMDBSyncService(db)
        result = sync_service.sync_from_api(
            azone=azone,
            page=page,
            per_page=per_page,
            triggered_by=current_user.username
        )
        
        return {
            "success": True,
            "message": "同步成功",
            **result
        }
        
    except Exception as e:
        logger.error(f"CMDB同步失败: {e}")
        raise HTTPException(status_code=500, detail=f"同步失败: {str(e)}")


@router.get("/sync/logs")
async def get_sync_logs(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取同步日志"""
    sync_service = CMDBSyncService(db)
    logs = sync_service.get_sync_logs(limit=limit)
    
    return {
        "total": len(logs),
        "logs": [{
            "id": log.id,
            "sync_type": log.sync_type,
            "azone": log.azone,
            "status": log.status,
            "total_rows": log.total_rows,
            "servers_added": log.servers_added,
            "servers_updated": log.servers_updated,
            "instances_added": log.instances_added,
            "instances_updated": log.instances_updated,
            "duration_seconds": log.duration_seconds,
            "error_message": log.error_message,
            "triggered_by": log.triggered_by,
            "started_at": log.started_at.isoformat() if log.started_at else None,
            "completed_at": log.completed_at.isoformat() if log.completed_at else None,
        } for log in logs]
    }


# ========== Cookie管理接口 ==========

@router.get("/config/cookie")
async def get_cookie_config(
    db: Session = Depends(get_db),
    current_user = Depends(require_admin)
):
    """获取AMIS Cookie配置（仅管理员）"""
    sync_service = CMDBSyncService(db)
    cookie = sync_service.get_cookie()
    
    # 脱敏显示
    masked_cookie = None
    if cookie:
        if len(cookie) > 20:
            masked_cookie = cookie[:10] + "..." + cookie[-10:]
        else:
            masked_cookie = "***"
    
    return {
        "configured": cookie is not None,
        "cookie_preview": masked_cookie,
        "last_updated": None  # TODO: 从配置表获取
    }


@router.post("/config/cookie")
async def update_cookie_config(
    cookie: str,
    db: Session = Depends(get_db),
    current_user = Depends(require_admin)
):
    """更新AMIS Cookie配置（仅管理员）"""
    if not cookie or len(cookie) < 10:
        raise HTTPException(status_code=400, detail="Cookie格式不正确")
    
    try:
        sync_service = CMDBSyncService(db)
        
        # 测试Cookie是否有效
        is_valid = sync_service.test_cookie(cookie)
        if not is_valid:
            raise HTTPException(status_code=400, detail="Cookie无效或已过期，请检查后重试")
        
        # 保存Cookie
        sync_service.set_config(
            key="amis_cookie",
            value=cookie,
            config_type="string",
            description="AMIS API认证Cookie",
            updated_by=current_user.username
        )
        
        logger.info(f"用户 {current_user.username} 更新了AMIS Cookie配置")
        
        return {
            "success": True,
            "message": "Cookie配置已更新并验证通过"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新Cookie配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")


@router.post("/config/cookie/test")
async def test_cookie(
    request: dict,
    db: Session = Depends(get_db),
    current_user = Depends(require_admin)
):
    """测试Cookie是否有效（仅管理员）"""
    try:
        cookie = request.get("cookie")
        if not cookie:
            raise HTTPException(status_code=422, detail="Cookie参数缺失")
        
        sync_service = CMDBSyncService(db)
        is_valid = sync_service.test_cookie(cookie)
        
        return {
            "valid": is_valid,
            "message": "Cookie有效" if is_valid else "Cookie无效或已过期"
        }
        
    except Exception as e:
        logger.error(f"测试Cookie失败: {e}")
        return {
            "valid": False,
            "message": f"测试失败: {str(e)}"
        }


# ========== 定时同步配置接口 ==========

@router.get("/sync/schedule")
async def get_sync_schedule(
    db: Session = Depends(get_db),
    current_user = Depends(require_admin)
):
    """获取定时同步配置（仅管理员）"""
    sync_service = CMDBSyncService(db)
    
    enabled = sync_service.get_config("sync_schedule_enabled", False)
    interval_hours = sync_service.get_config("sync_schedule_interval_hours", 6)
    azones = sync_service.get_config("sync_schedule_azones", ["AZONE-cdhmlcc001"])
    
    return {
        "enabled": enabled,
        "interval_hours": interval_hours,
        "azones": azones
    }


@router.post("/sync/schedule")
async def update_sync_schedule(
    enabled: bool,
    interval_hours: int = Query(6, ge=1, le=24, description="同步间隔（小时）"),
    azones: List[str] = Query(["AZONE-cdhmlcc001"], description="要同步的可用区列表"),
    db: Session = Depends(get_db),
    current_user = Depends(require_admin)
):
    """配置定时同步任务（仅管理员）"""
    try:
        sync_service = CMDBSyncService(db)
        
        # 保存配置
        sync_service.set_config(
            key="sync_schedule_enabled",
            value=enabled,
            config_type="bool",
            description="是否启用定时同步",
            updated_by=current_user.username
        )
        
        sync_service.set_config(
            key="sync_schedule_interval_hours",
            value=interval_hours,
            config_type="int",
            description="定时同步间隔（小时）",
            updated_by=current_user.username
        )
        
        sync_service.set_config(
            key="sync_schedule_azones",
            value=azones,
            config_type="json",
            description="要同步的可用区列表",
            updated_by=current_user.username
        )
        
        # 实时更新调度器
        try:
            from app.core.scheduler import scheduler
            
            if enabled:
                # 启用定时任务
                scheduler.add_cmdb_sync_job(interval_hours, azones)
                logger.info(f"定时同步任务已更新: 间隔{interval_hours}小时, 可用区{azones}")
            else:
                # 禁用定时任务
                scheduler.remove_cmdb_sync_job()
                logger.info("定时同步任务已禁用")
                
        except Exception as e:
            logger.error(f"更新调度器失败: {e}")
            # 配置已保存，但调度器更新失败
            raise HTTPException(
                status_code=500, 
                detail=f"配置已保存，但调度器更新失败: {str(e)}"
            )
        
        message = f"定时同步已{'启用' if enabled else '禁用'}，间隔{interval_hours}小时"
        logger.info(f"用户 {current_user.username} 更新了定时同步配置: {message}")
        
        return {
            "success": True,
            "message": message,
            "enabled": enabled,
            "interval_hours": interval_hours,
            "azones": azones
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新定时同步配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")


# ========== BCE 数据同步接口 ==========

@router.get("/bce/config")
async def get_bce_config(
    db: Session = Depends(get_db),
    current_user = Depends(require_admin)
):
    """获取 BCE 同步配置（SK 脱敏、区域、集群ID列表）"""
    from app.services.bce_sync_service import BCESyncService
    return BCESyncService(db).get_full_config()


@router.post("/bce/config")
async def update_bce_config(
    request: dict,
    db: Session = Depends(get_db),
    current_user = Depends(require_admin)
):
    """更新 BCE 同步配置（patch 式，只更新传入字段）"""
    from app.services.bce_sync_service import BCESyncService
    svc = BCESyncService(db)
    ids = request.get('cluster_ids')
    if isinstance(ids, str):
        ids = [x.strip() for x in ids.replace('\n', ',').split(',') if x.strip()]
    svc.update_config(
        access_key=request.get('access_key', ''),
        secret_key=request.get('secret_key', ''),
        region=request.get('region', ''),
        cluster_ids=ids,
        updated_by_id=current_user.id
    )
    return {"success": True, "message": "BCE 配置已更新"}


@router.post("/bce/sync")
async def bce_sync(
    target: str = Query("all", description="同步目标: all / bcc / cce"),
    db: Session = Depends(get_db),
    current_user = Depends(require_admin)
):
    """一键同步 BCE 数据到本地容器数据库（BCC实例 + CCE节点）"""
    from app.services.bce_sync_service import BCESyncService
    svc = BCESyncService(db)
    try:
        if target == 'bcc':
            result = svc.sync_bcc()
        elif target == 'cce':
            result = svc.sync_cce()
        else:
            result = svc.sync_all()
        return {"success": True, "result": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"BCE 同步失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bce/stats")
async def get_bce_stats(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """查询本地库中 BCE 数据的统计信息（记录数、最新采集日期）"""
    from app.services.bce_sync_service import BCESyncService
    stats = BCESyncService(db).get_table_stats()

    # 转换为前端期望的格式
    return {
        'bcc_count': stats.get('bcc', {}).get('count', 0),
        'bcc_latest_date': stats.get('bcc', {}).get('latest_date'),
        'cce_count': stats.get('cce', {}).get('count', 0),
        'cce_latest_date': stats.get('cce', {}).get('latest_date')
    }


@router.post("/bce/test-connection", response_model=APIResponse, summary="测试 BCE 连接")
async def test_bce_connection(
    config: Optional[Dict[str, Any]] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    测试 BCE 连接（使用 AK/SK 调用官方 API）

    支持两种模式：
    1. 传入配置数据：使用传入的 AK/SK 测试（保存前测试）
    2. 不传配置：使用数据库中的配置测试（保存后测试）
    """
    try:
        if current_user.role not in ['admin', 'super_admin']:
            raise HTTPException(status_code=403, detail="仅管理员可以测试连接")

        from app.services.bce_sync_service import BCESyncService, _BCCApiClient

        if config and (config.get('access_key') or config.get('secret_key')):
            ak = config.get('access_key', '')
            sk = config.get('secret_key', '')
            region = config.get('region', 'cd')
        else:
            svc = BCESyncService(db)
            ak, sk = svc.get_credentials()
            region = svc.get_region()

        if not ak or not sk:
            return APIResponse(
                success=False,
                error="未配置 BCE Access Key / Secret Key",
                message="请先填写 AK 和 SK"
            )

        logger.info(f"测试 BCE 连接（region={region}）")
        # 只获取第一页（max_keys=1）验证凭证有效性，避免拉全量数据
        from baidubce.bce_client_configuration import BceClientConfiguration
        from baidubce.auth.bce_credentials import BceCredentials
        from baidubce.services.bcc.bcc_client import BccClient
        _BCC_EP = {'cd': 'bcc.cd.baidubce.com', 'bj': 'bcc.bj.baidubce.com',
                   'gz': 'bcc.gz.baidubce.com', 'su': 'bcc.su.baidubce.com'}
        endpoint = _BCC_EP.get(region, f'bcc.{region}.baidubce.com')
        cfg = BceClientConfiguration(
            credentials=BceCredentials(ak, sk),
            endpoint=endpoint,
        )
        client = BccClient(cfg)
        resp = client.list_instances(max_keys=1)
        count = len(resp.instances) if hasattr(resp, 'instances') else 0
        return APIResponse(
            success=True,
            data={"connected": True, "region": region, "sample_count": count},
            message=f"BCE 连接测试成功（region={region}）"
        )

    except Exception as e:
        err = str(e)
        logger.error(f"测试 BCE 连接失败: {err}")
        return APIResponse(
            success=False,
            error=err,
            message="连接测试失败：请检查 AK/SK 是否正确，以及账号是否有 BCC 只读权限"
        )


@router.get("/bce/sync-config", response_model=APIResponse, summary="获取 BCE 自动同步配置")
async def get_bce_sync_config(
    db: Session = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    获取 BCE 自动同步配置

    需要管理员权限
    """
    try:
        from app.services.bce_sync_service import BCESyncService
        from app.models.system_config import SystemConfig

        # 读取同步配置
        row = db.query(SystemConfig).filter_by(
            module='bce_sync', config_key='sync_config').first()

        default_config = {
            'enabled': False,
            'sync_interval': 3600,  # 默认1小时
            'auto_sync_bcc': True,
            'auto_sync_cce': True,
            'last_sync_time': None,
            'next_sync_time': None
        }

        if row and row.config_value:
            try:
                import json
                stored = json.loads(row.config_value)
                default_config.update(stored)
            except Exception:
                pass

        return APIResponse(
            success=True,
            data=default_config,
            message="获取同步配置成功"
        )

    except Exception as e:
        logger.error(f"❌ 获取 BCE 同步配置失败: {e}")
        return APIResponse(
            success=False,
            error=str(e),
            message="获取同步配置失败"
        )


@router.post("/bce/sync-config", response_model=APIResponse, summary="更新 BCE 自动同步配置")
async def update_bce_sync_config(
    config: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    更新 BCE 自动同步配置

    需要管理员权限
    """
    try:
        from app.models.system_config import SystemConfig
        import json

        # 验证配置
        if 'sync_interval' in config:
            interval = config['sync_interval']
            if not isinstance(interval, int) or interval < 300:
                return APIResponse(
                    success=False,
                    error="同步间隔不能小于300秒（5分钟）",
                    message="配置验证失败"
                )

        # 读取现有配置
        row = db.query(SystemConfig).filter_by(
            module='bce_sync', config_key='sync_config').first()

        if row and row.config_value:
            try:
                current = json.loads(row.config_value)
            except Exception:
                current = {}
        else:
            current = {}

        # 合并配置
        current.update(config)

        # 保存配置
        config_value = json.dumps(current, ensure_ascii=False)
        if row:
            row.config_value = config_value
            row.updated_at = datetime.utcnow()
            row.updated_by = current_user.id
        else:
            row = SystemConfig(
                module='bce_sync',
                config_key='sync_config',
                config_value=config_value,
                description='BCE 自动同步配置',
                updated_by=current_user.id
            )
            db.add(row)

        db.commit()

        # 实时更新调度器（复用 CMDB 同步逻辑）
        try:
            from app.core.scheduler import scheduler
            if current.get('enabled'):
                interval_hours = max(1, current.get('sync_interval', 3600) // 3600)
                auto_sync_bcc = current.get('auto_sync_bcc', True)
                auto_sync_cce = current.get('auto_sync_cce', True)
                scheduler.add_bce_sync_job(interval_hours, auto_sync_bcc, auto_sync_cce)
                logger.info(f"BCE 定时同步任务已更新: 间隔 {interval_hours} 小时")
            else:
                scheduler.remove_bce_sync_job()
                logger.info("BCE 定时同步任务已禁用")
        except Exception as e:
            logger.error(f"更新 BCE 调度器失败: {e}")

        return APIResponse(
            success=True,
            data=current,
            message="同步配置已更新"
        )

    except Exception as e:
        logger.error(f"❌ 更新 BCE 同步配置失败: {e}")
        db.rollback()
        return APIResponse(
            success=False,
            error=str(e),
            message="更新同步配置失败"
        )


@router.get("/servers/{hostname}/bce-context")
async def get_server_bce_context(
    hostname: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    以 IP 为中心，查询某台服务器及其实例在 BCE（BCC/CCE）中的关联信息。

    关联逻辑：
    - 收集该服务器下所有实例的私网 IP（nova_vm_fixed_ips）
    - 用这批 IP 在 bce_bcc_instances 中匹配 `主ipv4私网地址`
    - 同时在 bce_cce_nodes 中匹配 `ip地址`，获取所属集群 ID
    """
    from app.core.database import get_db_connection

    # 1. 从 ORM 取该服务器下所有实例的 IP 列表
    # nova_vm_fixed_ips 可能是 JSON 数组字符串如 '["10.90.0.211"]'，也可能是普通 IP 字符串
    import json as _json
    instances = db.query(IaasInstance).filter(IaasInstance.bns_hostname == hostname).all()
    ip_set = set()
    for inst in instances:
        raw = inst.nova_vm_fixed_ips
        if not raw:
            continue
        raw_str = str(raw).strip()
        # 尝试 JSON 解析
        if raw_str.startswith('[') or raw_str.startswith('"'):
            try:
                parsed = _json.loads(raw_str)
                if isinstance(parsed, list):
                    for ip in parsed:
                        ip = str(ip).strip()
                        if ip:
                            ip_set.add(ip)
                    continue
                elif isinstance(parsed, str):
                    if parsed.strip():
                        ip_set.add(parsed.strip())
                    continue
            except Exception:
                pass
        # 普通逗号/分号分隔
        for part in raw_str.replace(';', ',').split(','):
            part = part.strip()
            if part:
                ip_set.add(part)

    ip_list = [ip for ip in ip_set if ip]

    if not ip_list:
        return {"bcc_instances": [], "cce_nodes": [], "ip_list": []}

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        bcc_rows = []
        cce_rows = []

        # 2. 查 bce_bcc_instances（先检查表是否存在）
        cursor.execute("SHOW TABLES LIKE 'bce_bcc_instances'")
        if cursor.fetchone():
            placeholders = ','.join(['%s'] * len(ip_list))
            cursor.execute(
                f"SELECT * FROM `bce_bcc_instances`"
                f" WHERE `主ipv4私网地址` IN ({placeholders})"
                f" ORDER BY `collect_date` DESC",
                ip_list
            )
            cols = [d[0] for d in cursor.description]
            for row in cursor.fetchall():
                bcc_rows.append(dict(zip(cols, [str(v) if v is not None else None for v in row])))

        # 3. 查 bce_cce_nodes（先检查表是否存在）
        cursor.execute("SHOW TABLES LIKE 'bce_cce_nodes'")
        if cursor.fetchone():
            placeholders = ','.join(['%s'] * len(ip_list))
            cursor.execute(
                f"SELECT * FROM `bce_cce_nodes`"
                f" WHERE `ip地址` IN ({placeholders})"
                f" ORDER BY `collect_date` DESC",
                ip_list
            )
            cols = [d[0] for d in cursor.description]
            for row in cursor.fetchall():
                cce_rows.append(dict(zip(cols, [str(v) if v is not None else None for v in row])))

        cursor.close()
    finally:
        conn.close()

    return {
        "bcc_instances": bcc_rows,
        "cce_nodes": cce_rows,
        "ip_list": ip_list
    }


# ========== 增强搜索接口 ==========

@router.get("/search")
async def advanced_search(
    keyword: str = Query(..., min_length=1, description="搜索关键词"),
    search_type: str = Query("all", description="搜索类型: all, server, instance, customer"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    增强的关联性搜索
    支持跨服务器、实例、客户信息搜索
    """
    results = {
        "keyword": keyword,
        "search_type": search_type,
        "servers": [],
        "instances": [],
        "total_servers": 0,
        "total_instances": 0
    }
    
    # 搜索服务器
    if search_type in ["all", "server"]:
        server_query = db.query(IaasServer).filter(
            or_(
                IaasServer.bns_hostname.contains(keyword),
                IaasServer.rms_sn.contains(keyword),
                IaasServer.rms_ip_in1.contains(keyword),
                IaasServer.rms_rack_info.contains(keyword),
                IaasServer.nova_host_hypervisor_hostname.contains(keyword),
                IaasServer.nova_host_host_ip.contains(keyword)
            )
        )
        
        results["total_servers"] = server_query.count()
        servers = server_query.offset((page - 1) * page_size).limit(page_size).all()
        
        results["servers"] = [{
            "id": s.id,
            "bns_hostname": s.bns_hostname,
            "rms_sn": s.rms_sn,
            "rms_manufacturer": s.rms_manufacturer,
            "nova_host_vcpus_total": s.nova_host_vcpus_total,
            "nova_host_vcpus_used": s.nova_host_vcpus_used,
            "nova_host_running_vms": s.nova_host_running_vms,
        } for s in servers]
    
    # 搜索实例
    if search_type in ["all", "instance"]:
        instance_query = db.query(IaasInstance).filter(
            or_(
                IaasInstance.nova_vm_instance_uuid.contains(keyword),
                IaasInstance.nova_vm_display_name.contains(keyword),
                IaasInstance.nova_vm_fixed_ips.contains(keyword),
                IaasInstance.nova_vm_floating_ips.contains(keyword),
                IaasInstance.bns_hostname.contains(keyword)
            )
        )
        
        results["total_instances"] = instance_query.count()
        instances = instance_query.offset((page - 1) * page_size).limit(page_size).all()
        
        results["instances"] = [{
            "id": i.id,
            "nova_vm_instance_uuid": i.nova_vm_instance_uuid,
            "nova_vm_display_name": i.nova_vm_display_name,
            "nova_vm_vm_state": i.nova_vm_vm_state,
            "nova_vm_fixed_ips": i.nova_vm_fixed_ips,
            "bns_hostname": i.bns_hostname,
            "crm_loginName": i.crm_loginName,
            "crm_company": i.crm_company,
        } for i in instances]
    
    # 搜索客户
    if search_type in ["all", "customer"]:
        customer_query = db.query(IaasInstance).filter(
            or_(
                IaasInstance.crm_loginName.contains(keyword),
                IaasInstance.crm_company.contains(keyword),
                IaasInstance.crm_accountId.contains(keyword)
            )
        )
        
        # 如果是客户搜索，覆盖实例结果
        if search_type == "customer":
            results["total_instances"] = customer_query.count()
            instances = customer_query.offset((page - 1) * page_size).limit(page_size).all()
            
            results["instances"] = [{
                "id": i.id,
                "nova_vm_instance_uuid": i.nova_vm_instance_uuid,
                "nova_vm_display_name": i.nova_vm_display_name,
                "crm_loginName": i.crm_loginName,
                "crm_company": i.crm_company,
                "crm_vip_type": i.crm_vip_type,
            } for i in instances]

    return results


# ========== CCE 官方 API 路由（只读） ==========

@router.get("/cce/clusters", summary="CCE 集群列表")
async def cce_list_clusters(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """从 BCE 官方 API 实时获取全部 CCE 集群列表"""
    from app.services.cce_api_service import CCEApiService
    result = CCEApiService(db).list_clusters()
    if not result["success"]:
        raise HTTPException(status_code=502, detail=result["error"])
    return result


@router.get("/cce/cluster-ids", summary="CCE 集群 ID 列表（轻量）")
async def cce_get_cluster_ids(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """仅返回集群 ID 数组，供下拉框使用"""
    from app.services.cce_api_service import CCEApiService
    ids = CCEApiService(db).get_cluster_ids()
    return {"success": True, "cluster_ids": ids}


@router.get("/cce/cluster/{cluster_id}", summary="CCE 集群详情")
async def cce_get_cluster_detail(
    cluster_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取单个集群的详细信息（K8S版本、网络模式、Master类型等）"""
    from app.services.cce_api_service import CCEApiService
    result = CCEApiService(db).get_cluster_detail(cluster_id)
    if not result["success"]:
        raise HTTPException(status_code=502, detail=result["error"])
    return result


@router.get("/cce/cluster/{cluster_id}/instances", summary="CCE 集群节点列表")
async def cce_list_instances(
    cluster_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取集群所有节点（节点ID、IP、状态、规格等）"""
    from app.services.cce_api_service import CCEApiService
    result = CCEApiService(db).list_cluster_instances(cluster_id)
    if not result["success"]:
        raise HTTPException(status_code=502, detail=result["error"])
    return result


@router.get("/cce/cluster/{cluster_id}/kubeconfig", summary="下载集群 KubeConfig")
async def cce_get_kubeconfig(
    cluster_id: str,
    type: str = Query("vpc", description="连接类型：vpc（内网）或 public（外网）"),
    db: Session = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    下载集群 KubeConfig（管理员权限）
    - type=vpc：使用内网 BLB VPC IP 连接
    - type=public：使用外网 EIP 连接（集群需开放公网访问）
    """
    from app.services.cce_api_service import CCEApiService
    from fastapi.responses import Response
    result = CCEApiService(db).get_kubeconfig(cluster_id, kube_type=type)
    if not result["success"]:
        raise HTTPException(status_code=502, detail=result["error"])
    kube_yaml = result["kubeConfig"]
    # 返回可直接下载的 YAML 文件
    filename = f"kubeconfig-{cluster_id}-{type}.yaml"
    return Response(
        content=kube_yaml,
        media_type="application/x-yaml",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
