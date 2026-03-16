# Models Package
# 导入顺序很重要：ChatHistory 必须在 User 之前导入
from app.models.chat import ChatHistory
from app.models.user import User, UserNote, AuditLog, UserRole
from app.models.task import Task, TaskStatus, ModuleType
from app.models.iaas import IaasServer, IaasInstance
from app.models.system_config import SystemConfig

__all__ = [
    "ChatHistory",
    "User",
    "UserNote",
    "AuditLog",
    "UserRole",
    "Task",
    "TaskStatus",
    "ModuleType",
    "IaasServer",
    "IaasInstance",
    "SystemConfig",
]
