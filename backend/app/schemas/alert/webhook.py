"""
Webhook配置 Schema
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, HttpUrl


class WebhookConfigBase(BaseModel):
    """Webhook配置基础模型"""
    name: str = Field(..., description="配置名称", max_length=100)
    type: str = Field(..., description="Webhook类型(feishu/ruliu)")
    url: str = Field(..., description="Webhook URL")
    access_token: Optional[str] = Field(None, description="访问令牌")
    secret: Optional[str] = Field(None, description="签名密钥（飞书专用）")
    group_id: Optional[str] = Field(None, description="群组ID（如流专用）")
    enabled: bool = Field(True, description="是否启用")
    severity_filter: Optional[str] = Field(None, description="严重程度过滤")
    component_filter: Optional[str] = Field(None, description="组件过滤")
    keywords: Optional[str] = Field(None, description="飞书机器人关键词(仅飞书需要)")


class WebhookConfigCreate(WebhookConfigBase):
    """创建Webhook配置"""
    pass


class WebhookConfigUpdate(BaseModel):
    """更新Webhook配置"""
    name: Optional[str] = Field(None, max_length=100)
    type: Optional[str] = Field(None, description="Webhook类型(feishu/ruliu)")
    url: Optional[str] = None
    access_token: Optional[str] = None
    secret: Optional[str] = None
    group_id: Optional[str] = None
    enabled: Optional[bool] = None
    severity_filter: Optional[str] = None
    component_filter: Optional[str] = None
    keywords: Optional[str] = None


class WebhookConfigResponse(WebhookConfigBase):
    """Webhook配置响应"""
    id: int = Field(..., description="配置ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    class Config:
        from_attributes = True
