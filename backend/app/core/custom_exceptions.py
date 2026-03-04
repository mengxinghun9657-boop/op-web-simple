#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自定义异常类

定义统一的异常类型，用于错误处理和用户反馈。
每个异常类包含错误代码、HTTP 状态码和用户友好的错误消息。

Validates: Requirements 10.1, 10.2, 10.3, 10.4, 10.5
"""

from typing import Optional, Dict, Any, List


class AIQueryException(Exception):
    """AI 查询基础异常类"""
    error_code = "AI_QUERY_ERROR"
    http_status = 500
    user_message = "查询处理失败"
    
    def __init__(
        self, 
        message: str = None, 
        detail: Optional[Dict[str, Any]] = None,
        suggestion: Optional[str] = None
    ):
        self.message = message or self.user_message
        self.detail = detail or {}
        self.suggestion = suggestion
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {
            "code": self.error_code,
            "message": self.message
        }
        if self.detail:
            result["details"] = self.detail
        if self.suggestion:
            result["suggestion"] = self.suggestion
        return result


# ==================== 输入验证错误 ====================

class ValidationError(AIQueryException):
    """输入验证失败"""
    error_code = "VALIDATION_ERROR"
    http_status = 400
    user_message = "输入验证失败"


class EmptyQueryError(ValidationError):
    """查询文本为空"""
    error_code = "EMPTY_QUERY"
    user_message = "查询文本不能为空"
    
    def __init__(self):
        super().__init__(
            message=self.user_message,
            suggestion="请输入您的问题"
        )


class QueryTooLongError(ValidationError):
    """查询文本过长"""
    error_code = "QUERY_TOO_LONG"
    user_message = "查询文本过长"
    
    def __init__(self, length: int, max_length: int = 1000):
        super().__init__(
            message=f"查询文本过长（{length} 字符，最多 {max_length} 字符）",
            detail={"length": length, "max_length": max_length},
            suggestion="请简化您的问题"
        )


class ContentTooLongError(ValidationError):
    """内容过长"""
    error_code = "CONTENT_TOO_LONG"
    user_message = "内容过长"
    
    def __init__(self, field: str, length: int, max_length: int):
        super().__init__(
            message=f"{field}过长（{length} 字符，最多 {max_length} 字符）",
            detail={"field": field, "length": length, "max_length": max_length},
            suggestion=f"请缩短{field}内容"
        )


class MissingFieldError(ValidationError):
    """缺少必填字段"""
    error_code = "MISSING_FIELD"
    user_message = "缺少必填字段"
    
    def __init__(self, fields: List[str]):
        super().__init__(
            message=f"缺少必填字段: {', '.join(fields)}",
            detail={"missing_fields": fields},
            suggestion="请提供所有必填字段"
        )


# ==================== 认证和权限错误 ====================

class AuthenticationError(AIQueryException):
    """认证失败"""
    error_code = "AUTHENTICATION_ERROR"
    http_status = 401
    user_message = "认证失败"


class UnauthenticatedError(AuthenticationError):
    """用户未登录"""
    error_code = "UNAUTHENTICATED"
    user_message = "用户未登录"
    
    def __init__(self):
        super().__init__(
            message=self.user_message,
            suggestion="请先登录"
        )


class PasswordVerificationError(AuthenticationError):
    """密码验证失败"""
    error_code = "PASSWORD_VERIFICATION_FAILED"
    user_message = "密码验证失败"
    
    def __init__(self, remaining_attempts: Optional[int] = None):
        message = self.user_message
        suggestion = "请检查密码是否正确"
        
        if remaining_attempts is not None:
            message = f"密码验证失败，剩余尝试次数: {remaining_attempts}"
            if remaining_attempts == 0:
                suggestion = "账户已被锁定，请 30 分钟后重试"
        
        super().__init__(
            message=message,
            detail={"remaining_attempts": remaining_attempts} if remaining_attempts is not None else {},
            suggestion=suggestion
        )


class AccountLockedError(AuthenticationError):
    """账户被锁定"""
    error_code = "ACCOUNT_LOCKED"
    http_status = 403
    user_message = "账户已被锁定"
    
    def __init__(self, locked_until: Optional[str] = None):
        super().__init__(
            message="账户因多次密码验证失败已被锁定",
            detail={"locked_until": locked_until} if locked_until else {},
            suggestion="请 30 分钟后重试"
        )


class AuthorizationError(AIQueryException):
    """权限不足"""
    error_code = "AUTHORIZATION_ERROR"
    http_status = 403
    user_message = "权限不足"


class InsufficientPermissionError(AuthorizationError):
    """用户无权访问"""
    error_code = "INSUFFICIENT_PERMISSION"
    user_message = "您无权访问此资源"
    
    def __init__(self, resource: Optional[str] = None):
        message = self.user_message
        if resource:
            message = f"您无权访问: {resource}"
        
        super().__init__(
            message=message,
            detail={"resource": resource} if resource else {},
            suggestion="请联系管理员申请权限"
        )


class SuperAdminOnlyError(AuthorizationError):
    """仅超级管理员可访问"""
    error_code = "SUPER_ADMIN_ONLY"
    user_message = "仅超级管理员可以执行此操作"
    
    def __init__(self, operation: Optional[str] = None):
        message = self.user_message
        if operation:
            message = f"仅超级管理员可以{operation}"
        
        super().__init__(
            message=message,
            detail={"operation": operation} if operation else {},
            suggestion="请联系超级管理员"
        )


# ==================== SQL 安全错误 ====================

class SQLSecurityError(AIQueryException):
    """SQL 安全验证失败"""
    error_code = "SQL_SECURITY_ERROR"
    http_status = 400
    user_message = "SQL 安全验证失败"


class UnsafeSQLOperationError(SQLSecurityError):
    """不安全的 SQL 操作"""
    error_code = "UNSAFE_SQL_OPERATION"
    user_message = "检测到不安全的 SQL 操作"
    
    def __init__(self, operation: str):
        super().__init__(
            message=f"不允许的 SQL 操作: {operation}",
            detail={"operation": operation},
            suggestion="仅支持查询操作（SELECT）"
        )


class TableNotInWhitelistError(SQLSecurityError):
    """表不在白名单中"""
    error_code = "TABLE_NOT_IN_WHITELIST"
    user_message = "查询的表不在允许范围内"
    
    def __init__(self, tables: List[str]):
        super().__init__(
            message=f"以下表不在允许范围内: {', '.join(tables)}",
            detail={"tables": tables},
            suggestion="请查看可查询的表列表"
        )


class MissingLimitClauseError(SQLSecurityError):
    """缺少 LIMIT 子句"""
    error_code = "MISSING_LIMIT_CLAUSE"
    user_message = "查询缺少 LIMIT 子句"
    
    def __init__(self):
        super().__init__(
            message="明细查询必须包含 LIMIT 子句",
            suggestion="系统会自动添加 LIMIT 限制"
        )


class LimitExceededError(SQLSecurityError):
    """LIMIT 值超过限制"""
    error_code = "LIMIT_EXCEEDED"
    user_message = "LIMIT 值超过限制"
    
    def __init__(self, limit: int, max_limit: int = 100):
        super().__init__(
            message=f"LIMIT 值 ({limit}) 超过最大限制 ({max_limit})",
            detail={"limit": limit, "max_limit": max_limit},
            suggestion=f"请将 LIMIT 值设置为不超过 {max_limit}"
        )


class CartesianProductError(SQLSecurityError):
    """检测到笛卡尔积"""
    error_code = "CARTESIAN_PRODUCT"
    user_message = "检测到笛卡尔积查询"
    
    def __init__(self):
        super().__init__(
            message="查询可能产生笛卡尔积，请添加 JOIN 条件或 WHERE 条件",
            suggestion="请优化查询，添加表之间的关联条件"
        )


class SubqueryNestingTooDeepError(SQLSecurityError):
    """子查询嵌套过深"""
    error_code = "SUBQUERY_NESTING_TOO_DEEP"
    user_message = "子查询嵌套过深"
    
    def __init__(self, level: int, max_level: int = 3):
        super().__init__(
            message=f"子查询嵌套层数 ({level}) 超过限制 ({max_level})",
            detail={"level": level, "max_level": max_level},
            suggestion="请简化查询，减少子查询嵌套"
        )


class MultipleStatementsError(SQLSecurityError):
    """多条 SQL 语句"""
    error_code = "MULTIPLE_STATEMENTS"
    user_message = "不允许执行多条 SQL 语句"
    
    def __init__(self):
        super().__init__(
            message="检测到多条 SQL 语句（使用分号分隔）",
            suggestion="请一次只执行一条查询"
        )


# ==================== 执行超时错误 ====================

class TimeoutError(AIQueryException):
    """操作超时"""
    error_code = "TIMEOUT_ERROR"
    http_status = 408
    user_message = "操作超时"


class QueryTimeoutError(TimeoutError):
    """查询超时"""
    error_code = "QUERY_TIMEOUT"
    user_message = "查询执行超时"
    
    def __init__(self, timeout_seconds: int = 5):
        super().__init__(
            message=f"查询执行超过 {timeout_seconds} 秒",
            detail={"timeout_seconds": timeout_seconds},
            suggestion="请简化查询或稍后重试"
        )


class APICallTimeoutError(TimeoutError):
    """API 调用超时"""
    error_code = "API_CALL_TIMEOUT"
    user_message = "外部服务调用超时"
    
    def __init__(self, service: str, timeout_seconds: int):
        super().__init__(
            message=f"{service} 调用超过 {timeout_seconds} 秒",
            detail={"service": service, "timeout_seconds": timeout_seconds},
            suggestion="请稍后重试"
        )


class ProcessingTimeoutError(TimeoutError):
    """处理超时"""
    error_code = "PROCESSING_TIMEOUT"
    user_message = "查询处理超时"
    
    def __init__(self, timeout_seconds: int = 30):
        super().__init__(
            message=f"查询处理超过 {timeout_seconds} 秒",
            detail={"timeout_seconds": timeout_seconds},
            suggestion="请简化查询或稍后重试"
        )


# ==================== 外部服务错误 ====================

class ExternalServiceError(AIQueryException):
    """外部服务调用失败"""
    error_code = "EXTERNAL_SERVICE_ERROR"
    http_status = 502
    user_message = "外部服务调用失败"


class ERNIEAPIError(ExternalServiceError):
    """ERNIE API 调用失败"""
    error_code = "ERNIE_API_ERROR"
    user_message = "AI 服务调用失败"
    
    def __init__(self, detail: Optional[str] = None):
        super().__init__(
            message="AI 服务暂时不可用",
            detail={"error_detail": detail} if detail else {},
            suggestion="请稍后重试"
        )


class MinIOError(ExternalServiceError):
    """MinIO 访问失败"""
    error_code = "MINIO_ERROR"
    user_message = "文件存储服务访问失败"
    
    def __init__(self, detail: Optional[str] = None):
        super().__init__(
            message="文件存储服务暂时不可用",
            detail={"error_detail": detail} if detail else {},
            suggestion="请稍后重试"
        )


class VectorDatabaseError(ExternalServiceError):
    """向量数据库操作失败"""
    error_code = "VECTOR_DATABASE_ERROR"
    user_message = "向量数据库操作失败"
    
    def __init__(self, operation: str, detail: Optional[str] = None):
        super().__init__(
            message=f"向量数据库{operation}失败",
            detail={"operation": operation, "error_detail": detail} if detail else {"operation": operation},
            suggestion="请稍后重试"
        )


class EmbeddingError(ExternalServiceError):
    """向量化失败"""
    error_code = "EMBEDDING_ERROR"
    user_message = "文本向量化失败"
    
    def __init__(self, detail: Optional[str] = None):
        super().__init__(
            message="文本向量化服务暂时不可用",
            detail={"error_detail": detail} if detail else {},
            suggestion="请稍后重试"
        )


# ==================== 数据错误 ====================

class DataError(AIQueryException):
    """数据处理错误"""
    error_code = "DATA_ERROR"
    http_status = 500
    user_message = "数据处理失败"


class DatabaseError(DataError):
    """数据库错误"""
    error_code = "DATABASE_ERROR"
    user_message = "数据库操作失败"
    
    def __init__(self, operation: str, detail: Optional[str] = None):
        super().__init__(
            message=f"数据库{operation}失败",
            detail={"operation": operation, "error_detail": detail} if detail else {"operation": operation},
            suggestion="请稍后重试"
        )


class ReportParsingError(DataError):
    """报告解析失败"""
    error_code = "REPORT_PARSING_ERROR"
    user_message = "报告内容解析失败"
    
    def __init__(self, report_type: str, detail: Optional[str] = None):
        super().__init__(
            message=f"{report_type} 报告解析失败",
            detail={"report_type": report_type, "error_detail": detail} if detail else {"report_type": report_type},
            suggestion="报告格式可能不正确"
        )


class JSONParsingError(DataError):
    """JSON 解析失败"""
    error_code = "JSON_PARSING_ERROR"
    user_message = "JSON 格式错误"
    
    def __init__(self, detail: Optional[str] = None):
        super().__init__(
            message="JSON 数据解析失败",
            detail={"error_detail": detail} if detail else {},
            suggestion="请检查数据格式"
        )


class VectorStoreCorruptedError(DataError):
    """向量数据库文件损坏"""
    error_code = "VECTOR_STORE_CORRUPTED"
    user_message = "向量数据库文件损坏"
    
    def __init__(self):
        super().__init__(
            message="向量数据库文件损坏，需要重建",
            suggestion="请联系管理员重建向量索引"
        )


# ==================== 资源错误 ====================

class ResourceError(AIQueryException):
    """资源错误"""
    error_code = "RESOURCE_ERROR"
    http_status = 404
    user_message = "资源不存在"


class NotFoundError(ResourceError):
    """资源不存在"""
    error_code = "NOT_FOUND"
    user_message = "资源不存在"
    
    def __init__(self, resource_type: str, resource_id: Any):
        super().__init__(
            message=f"{resource_type}不存在: {resource_id}",
            detail={"resource_type": resource_type, "resource_id": str(resource_id)}
        )


class NoResultsError(ResourceError):
    """未找到结果"""
    error_code = "NO_RESULTS"
    http_status = 200  # 这不是错误，只是没有结果
    user_message = "未找到相关结果"
    
    def __init__(self, query_type: str):
        super().__init__(
            message=f"未找到相关{query_type}",
            suggestion="请尝试其他关键词或调整查询条件"
        )


# ==================== 意图识别错误 ====================

class IntentError(AIQueryException):
    """意图识别错误"""
    error_code = "INTENT_ERROR"
    http_status = 400
    user_message = "无法理解查询意图"


class LowConfidenceError(IntentError):
    """意图置信度过低"""
    error_code = "LOW_CONFIDENCE"
    user_message = "无法确定查询意图"
    
    def __init__(self, confidence: float):
        super().__init__(
            message=f"查询意图不明确（置信度: {confidence:.2f}）",
            detail={"confidence": confidence},
            suggestion="请更明确地描述您的问题"
        )


class AmbiguousQueryError(IntentError):
    """查询意图模糊"""
    error_code = "AMBIGUOUS_QUERY"
    user_message = "查询意图不明确"
    
    def __init__(self, possible_intents: List[str]):
        super().__init__(
            message="查询可能有多种理解方式",
            detail={"possible_intents": possible_intents},
            suggestion="请更具体地描述您的需求"
        )


# ==================== 降级错误（用于内部处理，不直接返回给用户）====================

class DegradationError(AIQueryException):
    """降级错误（内部使用）"""
    error_code = "DEGRADATION_ERROR"
    http_status = 200  # 降级不是错误，只是功能受限
    user_message = "服务降级运行"
    
    def __init__(self, service: str, fallback: str):
        super().__init__(
            message=f"{service}不可用，已切换到{fallback}",
            detail={"service": service, "fallback": fallback}
        )
