"""
告警系统配置
"""
from typing import Optional
from pydantic_settings import BaseSettings


class AlertSettings(BaseSettings):
    """告警系统配置"""
    
    # 文件监控配置
    ALERT_WATCH_PATH: str = "~/Downloads/changan"  # 监控目录（支持 ~ 扩展）
    ALERT_FILE_PATH: str = "/data/HAS_file/changan"
    ALERT_FILE_PATTERN: str = "*.py"
    
    # 百度云配置
    BCE_ACCESS_KEY: str = ""
    BCE_SECRET_KEY: str = ""
    
    # 诊断API配置（支持多个集群）
    CCE_CLUSTER_IDS: str = ""  # 多个集群ID，用逗号分隔
    DIAGNOSIS_API_BASE_URL: str = "https://cce.cd.baidubce.com"
    DIAGNOSIS_API_TIMEOUT: int = 300  # 5分钟
    
    # AI接口配置
    AI_API_URL: Optional[str] = None
    AI_API_KEY: Optional[str] = None
    AI_API_TIMEOUT: int = 30
    
    # Webhook配置
    WEBHOOK_TIMEOUT: int = 10
    WEBHOOK_RETRY_TIMES: int = 3
    
    # 如流 Webhook 配置
    RULIU_WEBHOOK_URL: Optional[str] = None
    RULIU_ACCESS_TOKEN: Optional[str] = None
    RULIU_CALLBACK_TOKEN: Optional[str] = None
    RULIU_GROUP_ID: Optional[str] = None
    
    # 飞书 Webhook 配置
    FEISHU_WEBHOOK_URL: Optional[str] = None
    
    # Celery配置
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"
    
    # 数据保留配置
    ALERT_RETENTION_DAYS: int = 90
    
    def get_cluster_ids(self) -> list:
        """获取集群ID列表"""
        if not self.CCE_CLUSTER_IDS:
            return []
        return [cid.strip() for cid in self.CCE_CLUSTER_IDS.split(',') if cid.strip()]
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # 忽略额外字段


alert_settings = AlertSettings()
settings = alert_settings  # 别名，方便导入
