#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
集群管理平台 - 核心配置
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import os
from pathlib import Path


class Settings(BaseSettings):
    """应用配置类"""
    
    # Pydantic v2 配置 - 允许额外字段
    # 查找项目根目录的 .env 文件
    _project_root = Path(__file__).parent.parent.parent.parent
    _env_file = _project_root / ".env"
    
    model_config = SettingsConfigDict(
        env_file=str(_env_file) if _env_file.exists() else ".env",
        case_sensitive=True,
        extra="ignore"  # 忽略额外的环境变量
    )
    
    # 应用基础配置
    APP_NAME: str = "集群管理平台"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False
    
    # API配置
    API_V1_PREFIX: str = "/api/v1"
    
    # CORS配置 - 从环境变量读取，默认为 localhost（开发环境）
    CORS_ORIGINS: str = os.getenv('CORS_ORIGINS', "http://localhost:8089,http://127.0.0.1:8089")
    
    @property
    def get_cors_origins(self) -> list:
        if isinstance(self.CORS_ORIGINS, str):
            return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
        return self.CORS_ORIGINS
    
    # 数据库配置（MySQL）- 从环境变量读取
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "cluster_user"
    MYSQL_PASSWORD: str = "ClusterPass2024!"
    MYSQL_DATABASE: str = "cluster_management"
    MYSQL_ROOT_PASSWORD: str = ""  # Docker 使用
    
    # 第二数据源配置（宿主机数据库）- 可选
    MYSQL_HOST_2: Optional[str] = None
    MYSQL_PORT_2: Optional[int] = None
    MYSQL_USER_2: Optional[str] = None
    MYSQL_PASSWORD_2: Optional[str] = None
    MYSQL_DATABASE_2: Optional[str] = None
    
    @property
    def DATABASE_URL(self) -> str:
        return f"mysql+aiomysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}?charset=utf8mb4"
    
    # Redis配置
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0
    
    # MinIO配置
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "cluster-files"
    MINIO_SECURE: bool = False
    MINIO_ROOT_USER: str = ""  # Docker 使用
    MINIO_ROOT_PASSWORD: str = ""  # Docker 使用
    MINIO_DOMAIN: str = ""  # Docker 使用
    
    # 文件上传配置
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE: int = 100 * 1024 * 1024  # 100MB
    ALLOWED_EXTENSIONS: set = {".xlsx", ".xls", ".csv"}
    
    # 结果文件存储
    RESULT_DIR: str = "./results"
    
    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "./logs"
    
    # 应用密钥
    SECRET_KEY: str = "your-secret-key-change-me"
    
    # 百度云配置（从环境变量读取）
    BCE_ACCESS_KEY: str = ""
    BCE_SECRET_KEY: str = ""
    BCE_REGION: str = "cd"
    BCM_HOST: str = "bcm.cd.baidubce.com"
    
    # Worker配置
    WORKERS: int = 4

    # ERNIE API 配置（百度文心一言）
    ERNIE_API_URL: str = "http://llms-se.baidu-int.com:8200/chat/completions"
    ERNIE_API_KEY: str = ""  # API 密钥
    ERNIE_MODEL: str = "ernie-4.5-8k-preview"  # 模型名称
    ERNIE_TIMEOUT: int = 60  # API 超时时间（秒），默认 60 秒


# 创建全局配置实例
settings = Settings()


# 确保必要的目录存在
def ensure_directories():
    """确保必要的目录存在"""
    directories = [
        settings.UPLOAD_DIR,
        settings.RESULT_DIR,
        settings.LOG_DIR,
    ]
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
