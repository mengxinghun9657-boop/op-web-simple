#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
实例配置管理API
仅管理员可修改配置
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
import json
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.models.instance_config import InstanceConfig
from app.core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/instance-config", tags=["实例配置管理"])


# ========== 请求/响应模型 ==========

class InstanceConfigRequest(BaseModel):
    """实例配置请求"""
    instance_ids: List[str] = Field(..., description="实例ID列表")
    description: Optional[str] = Field(None, description="配置说明")


class InstanceConfigResponse(BaseModel):
    """实例配置响应"""
    config_type: str
    instance_ids: List[str]
    description: Optional[str]
    created_by: Optional[str]
    updated_by: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]


# ========== 辅助函数 ==========

def check_admin_permission(current_user: User):
    """检查管理员权限"""
    if current_user.role not in ['super_admin', 'admin']:
        raise HTTPException(
            status_code=403,
            detail="仅管理员可以修改配置"
        )


def validate_config_type(config_type: str):
    """验证配置类型"""
    valid_types = ['resource_analysis', 'eip_monitoring', 'bos_monitoring', 'bcc_monitoring']
    if config_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"无效的配置类型。有效类型: {', '.join(valid_types)}"
        )


# ========== API 端点 ==========

@router.get("/{config_type}", response_model=InstanceConfigResponse)
async def get_config(
    config_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取指定类型的实例配置
    
    **config_type 可选值**:
    - resource_analysis: 资源分析配置
    - eip_monitoring: EIP监控配置
    - bos_monitoring: BOS监控配置
    - bcc_monitoring: BCC监控配置
    """
    validate_config_type(config_type)
    
    config = db.query(InstanceConfig).filter(
        InstanceConfig.config_type == config_type
    ).first()
    
    if not config:
        # 如果配置不存在，返回空配置
        return InstanceConfigResponse(
            config_type=config_type,
            instance_ids=[],
            description=None,
            created_by=None,
            updated_by=None,
            created_at=None,
            updated_at=None
        )
    
    # 解析JSON数组
    try:
        instance_ids = json.loads(config.instance_ids)
    except:
        instance_ids = []
    
    return InstanceConfigResponse(
        config_type=config.config_type,
        instance_ids=instance_ids,
        description=config.description,
        created_by=config.created_by,
        updated_by=config.updated_by,
        created_at=config.created_at.isoformat() if config.created_at else None,
        updated_at=config.updated_at.isoformat() if config.updated_at else None
    )


@router.post("/{config_type}", response_model=InstanceConfigResponse)
async def save_config(
    config_type: str,
    request: InstanceConfigRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    保存或更新实例配置（仅管理员）
    
    **权限要求**: 管理员或超级管理员
    """
    # 检查管理员权限
    check_admin_permission(current_user)
    
    validate_config_type(config_type)
    
    # 转换为JSON字符串
    instance_ids_json = json.dumps(request.instance_ids, ensure_ascii=False)
    
    # 查找现有配置
    config = db.query(InstanceConfig).filter(
        InstanceConfig.config_type == config_type
    ).first()
    
    if config:
        # 更新现有配置
        config.instance_ids = instance_ids_json
        config.description = request.description
        config.updated_by = current_user.username
        logger.info(f"用户 {current_user.username} 更新了配置: {config_type}")
    else:
        # 创建新配置
        config = InstanceConfig(
            config_type=config_type,
            instance_ids=instance_ids_json,
            description=request.description,
            created_by=current_user.username,
            updated_by=current_user.username
        )
        db.add(config)
        logger.info(f"用户 {current_user.username} 创建了配置: {config_type}")
    
    db.commit()
    db.refresh(config)
    
    return InstanceConfigResponse(
        config_type=config.config_type,
        instance_ids=request.instance_ids,
        description=config.description,
        created_by=config.created_by,
        updated_by=config.updated_by,
        created_at=config.created_at.isoformat() if config.created_at else None,
        updated_at=config.updated_at.isoformat() if config.updated_at else None
    )


@router.get("/", response_model=List[InstanceConfigResponse])
async def get_all_configs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取所有实例配置
    """
    configs = db.query(InstanceConfig).all()
    
    result = []
    for config in configs:
        try:
            instance_ids = json.loads(config.instance_ids)
        except:
            instance_ids = []
        
        result.append(InstanceConfigResponse(
            config_type=config.config_type,
            instance_ids=instance_ids,
            description=config.description,
            created_by=config.created_by,
            updated_by=config.updated_by,
            created_at=config.created_at.isoformat() if config.created_at else None,
            updated_at=config.updated_at.isoformat() if config.updated_at else None
        ))
    
    return result
