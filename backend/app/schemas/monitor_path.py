"""
监控路径配置相关的Pydantic模型
"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, validator


class MonitorPathBase(BaseModel):
    """监控路径基础模型"""
    path: str = Field(..., description="监控路径（绝对路径）", max_length=1000)
    description: Optional[str] = Field(None, description="路径描述", max_length=500)
    enabled: bool = Field(True, description="是否启用")
    priority: int = Field(50, description="优先级（1-100，数值越大优先级越高）", ge=1, le=100)
    file_pattern: str = Field("*.txt", description="文件匹配模式", max_length=200)
    
    @validator('path')
    def validate_path(cls, v):
        """验证路径格式"""
        if not v:
            raise ValueError('路径不能为空')
        if not v.startswith('/'):
            raise ValueError('必须是绝对路径（以/开头）')
        if not v.endswith('/'):
            v = v + '/'  # 自动添加结尾斜杠
        return v
    
    @validator('file_pattern')
    def validate_file_pattern(cls, v):
        """验证文件模式"""
        if not v:
            raise ValueError('文件模式不能为空')
        # 基本验证：确保包含通配符或具体文件名
        if not any(char in v for char in ['*', '?', '.']):
            raise ValueError('文件模式格式不正确，应包含通配符（如 *.txt）')
        return v


class MonitorPathCreate(MonitorPathBase):
    """创建监控路径请求模型"""
    pass


class MonitorPathUpdate(BaseModel):
    """更新监控路径请求模型（所有字段可选）"""
    description: Optional[str] = Field(None, description="路径描述", max_length=500)
    enabled: Optional[bool] = Field(None, description="是否启用")
    priority: Optional[int] = Field(None, description="优先级（1-100）", ge=1, le=100)
    file_pattern: Optional[str] = Field(None, description="文件匹配模式", max_length=200)
    
    @validator('file_pattern')
    def validate_file_pattern(cls, v):
        """验证文件模式"""
        if v is not None and not any(char in v for char in ['*', '?', '.']):
            raise ValueError('文件模式格式不正确，应包含通配符（如 *.txt）')
        return v


class MonitorPathResponse(MonitorPathBase):
    """监控路径响应模型"""
    id: int = Field(..., description="主键ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    class Config:
        from_attributes = True  # Pydantic v2
        # orm_mode = True  # Pydantic v1


class MonitorPathTestResult(BaseModel):
    """路径测试结果模型"""
    path_exists: bool = Field(..., description="路径是否存在")
    readable: bool = Field(..., description="是否可读")
    writable: bool = Field(..., description="是否可写")
    file_count: int = Field(..., description="文件数量")
    sample_files: list[str] = Field(default_factory=list, description="示例文件列表（最多3个）")


class MonitorPathBatchUpdate(BaseModel):
    """批量更新请求模型"""
    path_ids: list[int] = Field(..., description="路径ID列表")
    enabled: bool = Field(..., description="启用状态")
