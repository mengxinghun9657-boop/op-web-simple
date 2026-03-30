"""
诊断结果 Schema
"""
from datetime import datetime
from typing import Optional, Any, List
from pydantic import BaseModel, Field


class FaultItem(BaseModel):
    """故障项（用于前端表格展示）"""
    device: str = Field("", description="设备名，如 gpu1")
    device_slot: str = Field("", description="设备槽位，如 gpu1_1")
    part_model: str = Field("", description="设备型号，如 NVIDIA H20")
    part_sn: str = Field("", description="设备序列号")
    
    fault_name: str = Field("", description="故障中文名称")
    alert_type: str = Field("", description="告警类型，如 xid48")
    severity: str = Field("ERROR", description="严重程度：FAIL/ERROR/WARN")
    
    danger_level: str = Field("P2", description="危害等级：P0/P1/P2")
    customer_aware: bool = Field(False, description="是否客户有感")
    impact_description: str = Field("", description="影响描述")
    solution: str = Field("", description="建议解决方案")
    manual_check: str = Field("", description="手动判断方法")
    
    timestamp: str = Field("", description="故障发生时间")
    source: str = Field("", description="告警来源")


class DiagnosisResultResponse(BaseModel):
    """诊断结果响应"""
    id: int = Field(..., description="诊断ID")
    alert_id: int = Field(..., description="关联告警ID")
    source: str = Field(..., description="诊断来源")
    
    # 手册匹配结果
    manual_matched: bool = Field(False, description="是否匹配到手册")
    manual_name_zh: Optional[str] = Field(None, description="故障中文名称")
    suggested_solution: Optional[str] = Field(None, description="建议解决方案（合并原解决方案和恢复方案）")
    manual_impact: Optional[str] = Field(None, description="影响描述")
    danger_level: Optional[str] = Field(None, description="危害等级")
    customer_aware: Optional[bool] = Field(None, description="是否客户有感")
    
    # 多故障类型详情（用于前端表格展示）
    fault_items: Optional[List[FaultItem]] = Field(None, description="故障类型列表")
    
    # API诊断结果
    api_task_id: Optional[str] = Field(None, description="API任务ID")
    api_status: Optional[str] = Field(None, description="API任务状态")
    api_items_count: int = Field(0, description="诊断项总数")
    api_error_count: int = Field(0, description="错误项数量")
    api_warning_count: int = Field(0, description="警告项数量")
    api_abnormal_count: int = Field(0, description="异常项数量")
    api_diagnosis: Optional[Any] = Field(None, description="API诊断详情")
    
    # AI解读结果
    ai_interpretation: Optional[str] = Field(None, description="AI解读内容")
    ai_category: Optional[str] = Field(None, description="AI分类")
    ai_root_cause: Optional[str] = Field(None, description="根本原因")
    ai_impact: Optional[str] = Field(None, description="影响评估")
    ai_solution: Optional[str] = Field(None, description="修复建议")
    
    # 通知状态
    notified: bool = Field(False, description="是否已通知")
    notified_at: Optional[datetime] = Field(None, description="通知时间")
    
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    class Config:
        from_attributes = True
