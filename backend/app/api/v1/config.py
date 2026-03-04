#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
系统配置管理API
集中管理CMDB、监控、分析等模块的配置
仅管理员可修改配置
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, validator
from typing import Dict, Any, Optional
import json
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, OperationalError

from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.models.system_config import SystemConfig
from app.core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/config", tags=["系统配置管理"])


# ========== 请求/响应模型 ==========

class ConfigSaveRequest(BaseModel):
    """配置保存请求"""
    module: str = Field(..., description="模块名称: cmdb, monitoring, analysis")
    config: Dict[str, Any] = Field(..., description="配置内容（JSON对象）")
    
    @validator('module')
    def validate_module(cls, v):
        """验证模块名称"""
        allowed_modules = ['cmdb', 'monitoring', 'analysis']
        if v not in allowed_modules:
            raise ValueError(f'无效的模块名称：{v}，允许的值：{", ".join(allowed_modules)}')
        return v
    
    @validator('config')
    def validate_config(cls, v, values):
        """验证配置格式"""
        module = values.get('module')
        
        if module == 'monitoring':
            # 验证监控配置的实例ID格式
            for key in ['eip_instance_ids', 'bcc_instance_ids', 'bos_bucket_names']:
                if key in v:
                    ids = v[key]
                    if not isinstance(ids, str):
                        raise ValueError(f'{key}必须是字符串')
                    # 验证逗号分隔格式
                    if ids.strip():
                        id_list = [id.strip() for id in ids.split(',')]
                        if not all(id for id in id_list):
                            raise ValueError(f'{key}格式错误，应为逗号分隔的非空字符串')
        
        return v


class ConfigLoadResponse(BaseModel):
    """配置加载响应"""
    module: str
    config: Dict[str, Any]
    updated_at: Optional[str]
    updated_by: Optional[int]


class ConfigSaveResponse(BaseModel):
    """配置保存响应"""
    success: bool
    message: str
    module: str


# ========== 辅助函数 ==========

def check_admin_permission(current_user: User):
    """检查管理员权限"""
    if current_user.role not in ['super_admin', 'admin']:
        raise HTTPException(
            status_code=403,
            detail="权限不足，只有管理员可以修改系统配置"
        )


# ========== API 端点 ==========

@router.post("/save", response_model=ConfigSaveResponse)
async def save_config(
    request: ConfigSaveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    保存系统配置（仅管理员）
    
    **权限要求**: 管理员或超级管理员
    
    **支持的模块**:
    - cmdb: CMDB配置（Cookie、同步设置等）
    - monitoring: 监控配置（EIP、BCC、BOS实例ID）
    - analysis: 分析配置（资源分析集群ID）
    """
    # 检查管理员权限
    check_admin_permission(current_user)
    
    try:
        # 将配置转换为JSON字符串
        config_value = json.dumps(request.config, ensure_ascii=False)
        
        # 查找或创建配置记录
        config_record = db.query(SystemConfig).filter(
            SystemConfig.module == request.module,
            SystemConfig.config_key == 'main'
        ).first()
        
        if config_record:
            # 更新现有配置
            config_record.config_value = config_value
            config_record.updated_by = current_user.id
            logger.info(f"用户 {current_user.username} (ID: {current_user.id}) 更新了 {request.module} 模块配置")
        else:
            # 创建新配置
            config_record = SystemConfig(
                module=request.module,
                config_key='main',
                config_value=config_value,
                updated_by=current_user.id
            )
            db.add(config_record)
            logger.info(f"用户 {current_user.username} (ID: {current_user.id}) 创建了 {request.module} 模块配置")
        
        db.commit()
        
        return ConfigSaveResponse(
            success=True,
            message="配置保存成功",
            module=request.module
        )
        
    except IntegrityError as e:
        db.rollback()
        logger.error(f"配置保存失败（唯一约束冲突）: {e}")
        raise HTTPException(status_code=400, detail="配置已存在")
        
    except OperationalError as e:
        db.rollback()
        logger.error(f"配置保存失败（数据库错误）: {e}")
        raise HTTPException(status_code=500, detail="数据库错误，请稍后重试")
        
    except Exception as e:
        db.rollback()
        logger.error(f"配置保存失败: {e}")
        raise HTTPException(status_code=500, detail=f"保存配置失败: {str(e)}")


@router.get("/load", response_model=ConfigLoadResponse)
async def load_config(
    module: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    加载系统配置
    
    **支持的模块**:
    - cmdb: CMDB配置
    - monitoring: 监控配置
    - analysis: 分析配置
    """
    # 验证模块名称
    allowed_modules = ['cmdb', 'monitoring', 'analysis']
    if module not in allowed_modules:
        raise HTTPException(
            status_code=400,
            detail=f"无效的模块名称：{module}，允许的值：{', '.join(allowed_modules)}"
        )
    
    try:
        # 查找配置记录
        config_record = db.query(SystemConfig).filter(
            SystemConfig.module == module,
            SystemConfig.config_key == 'main'
        ).first()
        
        if not config_record:
            # 如果配置不存在，返回空配置
            return ConfigLoadResponse(
                module=module,
                config={},
                updated_at=None,
                updated_by=None
            )
        
        # 解析JSON配置
        try:
            config = json.loads(config_record.config_value) if config_record.config_value else {}
        except json.JSONDecodeError:
            logger.error(f"配置解析失败: {module}")
            config = {}
        
        return ConfigLoadResponse(
            module=module,
            config=config,
            updated_at=config_record.updated_at.isoformat() if config_record.updated_at else None,
            updated_by=config_record.updated_by
        )
        
    except Exception as e:
        logger.error(f"加载配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"加载配置失败: {str(e)}")
