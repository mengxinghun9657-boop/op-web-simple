"""
统一 API 响应格式模型

遵循 API 响应格式规范：
- 所有 API 必须返回 {success, data, message, error} 格式
- 分页接口必须返回 {list, total, page, page_size} 格式
"""

from typing import Any, Optional, List
from pydantic import BaseModel, Field


class APIResponse(BaseModel):
    """统一 API 响应格式"""
    success: bool = Field(True, description="操作是否成功")
    data: Optional[Any] = Field(None, description="返回的数据")
    message: Optional[str] = Field(None, description="提示信息")
    error: Optional[str] = Field(None, description="错误信息")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {"id": 1, "name": "示例"},
                "message": "操作成功"
            }
        }


class PaginatedData(BaseModel):
    """分页数据格式"""
    list: List[Any] = Field(default_factory=list, description="数据列表")
    total: int = Field(0, description="总数")
    page: int = Field(1, description="当前页")
    page_size: int = Field(20, description="每页数量")


class PaginatedResponse(APIResponse):
    """分页响应格式"""
    data: Optional[PaginatedData] = Field(None, description="分页数据")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {
                    "list": [],
                    "total": 100,
                    "page": 1,
                    "page_size": 20
                },
                "message": "获取成功"
            }
        }


class TaskResponse(APIResponse):
    """任务响应格式"""
    data: Optional[dict] = Field(None, description="任务数据")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {
                    "task_id": "task_123",
                    "status": "processing",  # pending/processing/completed/failed
                    "progress": 50,
                    "message": "正在处理中..."
                },
                "message": "任务创建成功"
            }
        }
