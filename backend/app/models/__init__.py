# Models Package
# 导入顺序很重要：ChatHistory 必须在 User 之前导入
from app.models.chat import ChatHistory
from app.models.user import User, UserNote, AuditLog, UserRole
from app.models.task import Task, TaskStatus, ModuleType
from app.models.iaas import IaasServer, IaasInstance
from app.models.system_config import SystemConfig
from app.models.routing_rule import RoutingRule
from app.models.routing_log import RoutingLog
from app.models.routing_feedback import RoutingFeedback
from app.models.rule_suggestion import RuleSuggestion
from app.models.rule_template import RuleTemplate
from app.models.rule_draft import RuleDraft

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
    "RoutingRule",
    "RoutingLog",
    "RoutingFeedback",
    "RuleSuggestion",
    "RuleTemplate",
    "RuleDraft"
]
