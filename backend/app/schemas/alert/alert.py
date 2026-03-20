"""
告警记录 Schema
"""
from datetime import datetime
from typing import Optional, Any, List
from pydantic import BaseModel, Field


class AlertRecordBase(BaseModel):
    """告警记录基础模型"""
    alert_type: str = Field(..., description="告警类型")
    ip: Optional[str] = Field(None, description="实例IP")
    cluster_id: Optional[str] = Field(None, description="集群ID")
    instance_id: Optional[str] = Field(None, description="实例ID")
    hostname: Optional[str] = Field(None, description="主机名")
    component: Optional[str] = Field(None, description="组件类型")
    severity: str = Field(..., description="严重程度")
    timestamp: datetime = Field(..., description="告警时间")
    file_path: Optional[str] = Field(None, description="源文件路径")
    source: Optional[str] = Field('file', description="告警来源(file/manual)")
    raw_data: Optional[Any] = Field(None, description="原始数据")
    is_cce_cluster: bool = Field(False, description="是否CCE集群")


class AlertRecordCreate(AlertRecordBase):
    """创建告警记录"""
    pass


class AlertRecordResponse(AlertRecordBase):
    """告警记录响应"""
    id: int = Field(..., description="告警ID")
    status: str = Field(..., description="处理状态")
    resolved_by: Optional[str] = Field(None, description="处理人")
    resolved_at: Optional[datetime] = Field(None, description="处理时间")
    resolution_notes: Optional[str] = Field(None, description="处理备注")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    has_diagnosis: bool = Field(False, description="是否有诊断结果")
    
    class Config:
        from_attributes = True


class AlertListItem(BaseModel):
    """告警列表项"""
    id: int
    alert_type: str
    ip: Optional[str]
    cluster_id: Optional[str] = None
    instance_id: Optional[str] = None
    hostname: Optional[str] = None
    component: Optional[str]
    severity: str
    timestamp: datetime
    status: str
    source: Optional[str] = 'file'
    has_diagnosis: bool

    class Config:
        from_attributes = True


class AlertListResponse(BaseModel):
    """告警列表响应"""
    list: List[AlertListItem] = Field(..., description="告警列表")
    total: int = Field(..., description="总数")
    page: int = Field(..., description="当前页")
    page_size: int = Field(..., description="每页数量")


class AlertStatusUpdate(BaseModel):
    """更新告警状态或备注"""
    status: Optional[str] = Field(None, description="新状态(pending/processing/diagnosed/notified/failed/resolved)")
    resolution_notes: Optional[str] = Field(None, description="处理备注")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "resolved",
                "resolution_notes": "已联系运维团队更换硬件"
            }
        }
