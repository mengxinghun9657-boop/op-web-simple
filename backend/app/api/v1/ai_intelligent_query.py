"""
AI 智能查询接口

实现主查询接口，整合所有已完成的组件：
- Intent Router（意图路由）
- SQL Generator（SQL 生成）
- Report Retriever（报告检索）
- Security Validator（安全验证）
- Query Executor（查询执行）
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Literal
from sqlalchemy.orm import Session
import asyncio
import json
import time
from datetime import datetime

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.services.ai.intent_router import IntentRouter
from app.services.ai.sql_generator import SQLGenerator
from app.services.ai.security_validator import SecurityValidator
from app.services.ai.query_executor import QueryExecutor
from app.services.ai.report_retriever import ReportRetriever
from app.services.ai.audit_logger import AuditLogger
from app.services.ai.routing_logger import RoutingLogger
from app.services.ai.ernie_client import ERNIEClient
from app.services.ai.embedding_model import EmbeddingModel
from app.services.ai.knowledge_manager import KnowledgeManager
from app.core.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


# ==================== Request/Response Models ====================

class IntelligentQueryRequest(BaseModel):
    """智能查询请求"""
    query: str = Field(..., description="用户查询文本")
    session_id: Optional[str] = Field(None, description="会话ID（多轮对话）")
    include_details: bool = Field(False, description="是否包含详细数据")
    
    @validator('query')
    def validate_query(cls, v):
        """验证查询文本"""
        if not v or not v.strip():
            raise ValueError("查询文本不能为空")
        if len(v) > 1000:
            raise ValueError("查询文本过长（最多1000字符）")
        return v.strip()


class QueryData(BaseModel):
    """查询结果数据"""
    answer: str
    source_type: Literal["database", "report", "knowledge", "mixed", "chat"]  # 添加 "chat"
    sql: Optional[str] = None
    query_results: Optional[List[Dict[str, Any]]] = None
    referenced_reports: Optional[List[Dict[str, Any]]] = None
    referenced_knowledge: Optional[List[Dict[str, Any]]] = None
    execution_time_ms: int


class QueryResponse(BaseModel):
    """查询响应"""
    status: Literal["analyzing_intent", "querying_data", "generating_answer", "completed", "error"]
    message: str
    data: Optional[QueryData] = None
    error: Optional[Dict[str, Any]] = None


# ==================== Service Initialization ====================

# 注意：routing_rule_manager 需要 db 会话，在路由函数中动态创建
intent_router = None  # 延迟初始化
sql_generator = SQLGenerator()
security_validator = SecurityValidator()
query_executor = QueryExecutor()
report_retriever = ReportRetriever()
ernie_client = ERNIEClient()
# audit_logger 需要 db 会话，在路由函数中通过依赖注入获取


def get_intent_router(db: Session) -> IntentRouter:
    """
    获取 IntentRouter 实例（带路由规则管理器）
    
    Args:
        db: 数据库会话
    
    Returns:
        IntentRouter 实例
    """
    from app.services.ai.routing_rule_manager import RoutingRuleManager
    
    # 创建 RoutingRuleManager
    routing_rule_manager = RoutingRuleManager(db=db)
    
    # 创建 IntentRouter（传入 routing_rule_manager）
    return IntentRouter(routing_rule_manager=routing_rule_manager)


# ==================== Main Query Endpoint ====================

@router.get("/intelligent-query")
@router.post("/intelligent-query")
async def intelligent_query(
    query: str = None,  # GET 参数
    session_id: Optional[str] = None,  # GET 参数
    include_details: bool = False,  # GET 参数
    request: IntelligentQueryRequest = None,  # POST body
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    AI 智能查询主接口
    
    支持的查询类型：
    - SQL 查询：查询实时数据库数据
    - 报告检索：检索历史分析报告
    - 知识库检索：检索知识库内容
    - 混合查询：同时查询多个数据源
    
    支持 GET（SSE）和 POST 两种方式
    
    返回 SSE 流式响应
    """
    # 兼容 GET 和 POST 两种方式
    if request is None:
        # GET 方式：从查询参数获取
        if not query:
            raise HTTPException(status_code=400, detail="query 参数不能为空")
        request = IntelligentQueryRequest(
            query=query,
            session_id=session_id,
            include_details=include_details
        )
    
    user_id = str(current_user.id)
    username = current_user.username
    user_role = current_user.role
    # 注意：User 对象没有 permissions 字段，这里暂时设为空列表
    user_permissions = []
    
    # 创建审计日志记录器实例
    audit_logger = AuditLogger(db)
    
    # 记录查询提交
    await audit_logger.log_query_submit(
        user_id=user_id,
        username=username,
        nl_query=request.query,
        session_id=request.session_id
    )
    
    async def generate_sse_stream():
        """生成 SSE 流式响应"""
        start_time = time.time()
        
        try:
            # 获取 IntentRouter 实例（带路由规则管理器）
            intent_router = get_intent_router(db)
            
            # ==================== 阶段 1：意图分析 ====================
            yield _format_sse_event(QueryResponse(
                status="analyzing_intent",
                message="正在分析查询意图..."
            ))
            
            intent_type, confidence, handlers, metadata, matched_rule_id, similarity_score, routing_method = await intent_router.route(
                query=request.query,
                user_id=user_id,
                session_id=request.session_id
            )
            
            logger.info(f"Intent classified: {intent_type} (confidence: {confidence}, method: {routing_method})")
            
            # 记录路由日志
            routing_logger = RoutingLogger(db)
            await routing_logger.log_routing(
                query=request.query,
                intent_type=intent_type,
                confidence=confidence,
                routing_method=routing_method,
                # handlers 参数已移除，不再传递
                matched_rule_id=matched_rule_id,
                similarity_score=similarity_score,
                user_id=user_id,
                session_id=request.session_id
            )
            
            # ==================== 阶段 2：查询数据 ====================
            yield _format_sse_event(QueryResponse(
                status="querying_data",
                message="正在查询数据..."
            ))
            
            # 根据意图类型路由到不同的处理器
            query_data = None
            
            if intent_type == "sql":
                query_data = await _handle_sql_query(
                    query=request.query,
                    user_id=user_id,
                    username=username,
                    user_permissions=user_permissions,
                    include_details=request.include_details,
                    audit_logger=audit_logger
                )
            
            elif intent_type == "rag_report":
                query_data = await _handle_report_query(
                    query=request.query,
                    user_id=user_id,
                    include_details=request.include_details
                )
            
            elif intent_type == "rag_knowledge":
                query_data = await _handle_knowledge_query(
                    query=request.query,
                    user_id=user_id,
                    db=db
                )
            
            elif intent_type == "chat":
                query_data = await _handle_chat_query(
                    query=request.query,
                    user_id=user_id
                )
            
            elif intent_type == "mixed":
                query_data = await _handle_mixed_query(
                    query=request.query,
                    user_id=user_id,
                    username=username,
                    user_permissions=user_permissions,
                    processors=handlers,
                    include_details=request.include_details,
                    audit_logger=audit_logger,
                    db=db
                )
            
            else:
                raise ValueError(f"Unknown intent type: {intent_type}")
            
            # ==================== 阶段 3：生成回答 ====================
            yield _format_sse_event(QueryResponse(
                status="generating_answer",
                message="正在生成自然语言回答..."
            ))
            
            # 如果还没有自然语言回答，调用 ERNIE 生成
            if not query_data.get("answer"):
                answer = await _generate_natural_language_answer(
                    query=request.query,
                    query_data=query_data
                )
                query_data["answer"] = answer
            
            # ==================== 阶段 4：完成 ====================
            execution_time_ms = int((time.time() - start_time) * 1000)
            query_data["execution_time_ms"] = execution_time_ms
            
            yield _format_sse_event(QueryResponse(
                status="completed",
                message="查询完成",
                data=QueryData(**query_data)
            ))
            
            # 记录查询成功
            await audit_logger.log_query_success(
                user_id=user_id,
                username=username,
                nl_query=request.query,
                intent_type=intent_type,
                execution_time_ms=execution_time_ms
            )
        
        except asyncio.TimeoutError:
            # 超时处理
            yield _format_sse_event(QueryResponse(
                status="error",
                message="查询超时",
                error={
                    "code": "TIMEOUT_ERROR",
                    "message": "查询处理时间过长，请简化查询或稍后重试"
                }
            ))
            
            await audit_logger.log_query_timeout(
                user_id=user_id,
                username=username,
                nl_query=request.query
            )
        
        except Exception as e:
            # 错误处理
            logger.error(f"Query error: {str(e)}", exc_info=True)
            
            yield _format_sse_event(QueryResponse(
                status="error",
                message="查询失败",
                error={
                    "code": "QUERY_ERROR",
                    "message": _get_user_friendly_error_message(e)
                }
            ))
            
            await audit_logger.log_query_error(
                user_id=user_id,
                username=username,
                nl_query=request.query,
                error_message=str(e)
            )
    
    return StreamingResponse(
        generate_sse_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# ==================== Query Handlers ====================

async def _handle_sql_query(
    query: str,
    user_id: str,
    username: str,
    user_permissions: List[str],
    include_details: bool,
    audit_logger: AuditLogger
) -> Dict[str, Any]:
    """处理 SQL 查询"""
    # 1. 生成 SQL
    sql_result = await sql_generator.generate_sql(
        query=query,
        user_permissions=user_permissions
    )
    
    # 修复：sql_result 是 dict，直接访问
    generated_sql = sql_result.get("sql")
    
    logger.info(f"Generated SQL: {generated_sql}")
    
    # 2. 安全验证
    validation_result = security_validator.validate_sql(
        sql=generated_sql,
        user_permissions=user_permissions
    )
    
    if not validation_result.is_valid:
        # 记录安全事件
        await audit_logger.log_sql_rejected(
            user_id=user_id,
            username=username,
            nl_query=query,
            generated_sql=generated_sql,
            rejection_reason="; ".join(validation_result.errors)
        )
        
        raise HTTPException(
            status_code=400,
            detail={
                "code": "SQL_SECURITY_ERROR",
                "message": "SQL 安全验证失败",
                "errors": validation_result.errors
            }
        )
    
    # 3. 执行查询
    # 修复：execute_query 返回元组 (success, results, error_message, execution_time_ms)
    success, results, error_message, execution_time_ms = await query_executor.execute_query(
        sql=generated_sql,
        user_id=user_id,
        username=username,
        nl_query=query
    )
    
    # 检查执行结果
    if not success:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "QUERY_EXECUTION_ERROR",
                "message": error_message or "查询执行失败"
            }
        )
    
    # 4. 格式化结果
    formatted_results = results or []
    
    return {
        "source_type": "database",
        "sql": generated_sql,
        "query_results": formatted_results if include_details else formatted_results[:10],
        "answer": None  # 将在后续生成
    }


async def _handle_report_query(
    query: str,
    user_id: str,
    include_details: bool
) -> Dict[str, Any]:
    """处理报告检索查询"""
    report_result = await report_retriever.retrieve_reports(
        query=query,
        include_details=include_details
    )
    
    # 修复：report_result 可能是 list 或对象，统一处理
    if isinstance(report_result, list):
        reports = report_result
    elif isinstance(report_result, dict):
        reports = report_result.get("reports", [])
    else:
        reports = report_result.reports if hasattr(report_result, "reports") else []
    
    return {
        "source_type": "report",
        "referenced_reports": reports,
        "answer": None  # 将在后续生成
    }


async def _handle_knowledge_query(
    query: str,
    user_id: str,
    db: Session
) -> Dict[str, Any]:
    """处理知识库检索查询"""
    try:
        # 初始化知识库管理器
        knowledge_manager = KnowledgeManager(db)
        
        # 向量检索知识条目
        knowledge_results = await knowledge_manager.search_entries(
            query=query,
            top_k=3,
            similarity_threshold=0.6
        )
        
        logger.info(f"✅ 知识库检索完成: found={len(knowledge_results)} entries")
        
        # 如果没有找到相关知识，返回提示
        if not knowledge_results:
            return {
                "source_type": "knowledge",
                "referenced_knowledge": [],
                "answer": "未找到相关知识条目。您可以尝试：\n1. 使用不同的关键词重新搜索\n2. 在知识库管理页面添加相关知识\n3. 切换到其他查询方式（如数据库查询或报告检索）"
            }
        
        # 构建知识引用列表
        referenced_knowledge = []
        for entry in knowledge_results:
            referenced_knowledge.append({
                "id": entry["id"],
                "title": entry["title"],
                "content": entry["content"][:200] + "..." if len(entry["content"]) > 200 else entry["content"],
                "category": entry.get("category"),
                "tags": entry.get("tags", []),
                "similarity": entry.get("similarity", 0.0),
                "source": entry.get("source", "manual")
            })
        
        # 使用 ERNIE 生成综合回答
        ernie_client = ERNIEClient()
        
        # 构建上下文
        context = "\n\n".join([
            f"【{entry['title']}】\n{entry['content']}"
            for entry in knowledge_results
        ])
        
        prompt = f"""基于以下知识库内容，回答用户的问题。

知识库内容：
{context}

用户问题：{query}

请提供准确、专业的回答，并在回答中引用相关知识条目的标题。"""
        
        answer = await ernie_client.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        
        return {
            "source_type": "knowledge",
            "referenced_knowledge": referenced_knowledge,
            "answer": answer
        }
        
    except Exception as e:
        logger.error(f"❌ 知识库检索失败: {e}")
        return {
            "source_type": "knowledge",
            "referenced_knowledge": [],
            "answer": f"知识库检索失败：{str(e)}"
        }


async def _handle_chat_query(
    query: str,
    user_id: str
) -> Dict[str, Any]:
    """处理普通对话查询"""
    # 直接调用 ERNIE API 生成回答
    answer = await ernie_client.chat(
        messages=[{"role": "user", "content": query}]
    )
    
    return {
        "source_type": "chat",
        "answer": answer
    }


async def _handle_mixed_query(
    query: str,
    user_id: str,
    username: str,
    user_permissions: List[str],
    processors: List[str],
    include_details: bool,
    audit_logger: AuditLogger,
    db: Session
) -> Dict[str, Any]:
    """处理混合查询（并行执行多个处理器）"""
    tasks = []
    
    if "sql" in processors:
        tasks.append(_handle_sql_query(
            query=query,
            user_id=user_id,
            username=username,
            user_permissions=user_permissions,
            include_details=include_details,
            audit_logger=audit_logger
        ))
    
    if "rag_report" in processors:
        tasks.append(_handle_report_query(
            query=query,
            user_id=user_id,
            include_details=include_details
        ))
    
    if "rag_knowledge" in processors:
        tasks.append(_handle_knowledge_query(
            query=query,
            user_id=user_id,
            db=db
        ))
    
    # 并行执行
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # 合并结果
    merged_result = {
        "source_type": "mixed",
        "sql": None,
        "query_results": None,
        "referenced_reports": [],
        "referenced_knowledge": [],
        "answer": None
    }
    
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"Mixed query sub-task failed: {str(result)}")
            continue
        
        if result.get("sql"):
            merged_result["sql"] = result["sql"]
            merged_result["query_results"] = result.get("query_results")
        
        if result.get("referenced_reports"):
            merged_result["referenced_reports"].extend(result["referenced_reports"])
        
        if result.get("referenced_knowledge"):
            merged_result["referenced_knowledge"].extend(result["referenced_knowledge"])
    
    return merged_result


async def _generate_natural_language_answer(
    query: str,
    query_data: Dict[str, Any]
) -> str:
    """生成自然语言回答"""
    source_type = query_data.get("source_type")
    
    # 构建 Prompt
    prompt_parts = [f"用户问题：{query}\n"]
    
    if source_type == "database":
        sql = query_data.get("sql")
        results = query_data.get("query_results", [])
        prompt_parts.append(f"执行的 SQL：{sql}\n")
        prompt_parts.append(f"查询结果（共 {len(results)} 条）：\n")
        if results:
            prompt_parts.append(json.dumps(results[:5], ensure_ascii=False, indent=2))
        else:
            prompt_parts.append("（无结果）")
        prompt_parts.append("\n请用自然语言总结查询结果，突出关键信息。")
    
    elif source_type == "report":
        reports = query_data.get("referenced_reports", [])
        prompt_parts.append(f"找到 {len(reports)} 份相关报告：\n")
        for report in reports:
            # 修复：安全访问字段，使用 get 方法
            report_type = report.get('report_type', '未知类型')
            generated_at = report.get('generated_at', '未知时间')
            summary = report.get('summary', report.get('conclusion', '无摘要'))
            prompt_parts.append(f"- {report_type} ({generated_at}): {summary}\n")
        prompt_parts.append("\n请基于这些报告回答用户问题。")
    
    elif source_type == "mixed":
        prompt_parts.append("综合查询结果：\n")
        if query_data.get("query_results"):
            prompt_parts.append(f"实时数据：{len(query_data['query_results'])} 条记录\n")
        if query_data.get("referenced_reports"):
            prompt_parts.append(f"历史报告：{len(query_data['referenced_reports'])} 份\n")
        prompt_parts.append("\n请综合实时数据和历史报告回答用户问题。")
    
    elif source_type == "chat":
        # chat 类型已经有 answer，不需要再生成
        return query_data.get("answer", "")
    
    prompt = "".join(prompt_parts)
    
    # 调用 ERNIE API
    answer = await ernie_client.chat(
        messages=[{"role": "user", "content": prompt}]
    )
    
    return answer


# ==================== Helper Functions ====================

def _format_sse_event(response: QueryResponse) -> str:
    """格式化 SSE 事件"""
    data = response.dict(exclude_none=True)
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def _get_user_friendly_error_message(error: Exception) -> str:
    """获取用户友好的错误消息"""
    error_type = type(error).__name__
    
    error_messages = {
        "ValidationError": "输入验证失败，请检查查询内容",
        "SQLSecurityError": "SQL 安全验证失败，请简化查询",
        "TimeoutError": "查询超时，请简化查询或稍后重试",
        "DatabaseError": "数据库查询失败，请稍后重试",
        "ExternalServiceError": "外部服务调用失败，请稍后重试"
    }
    
    return error_messages.get(error_type, "查询处理失败，请稍后重试")


# ==================== Auxiliary Endpoints ====================

@router.get("/query-tables")
async def get_query_tables(
    current_user: User = Depends(get_current_user)
):
    """
    获取可查询的表列表
    
    根据用户权限过滤
    
    Returns:
        tables: 用户有权访问的表列表，包含表名、描述和字段信息
    """
    user_permissions = []  # User 对象没有 permissions 字段
    user_role = current_user.role
    
    # 定义所有可用的表
    all_tables = [
        {
            "name": "users",
            "description": "用户信息表",
            "columns": ["id", "username", "email", "role", "created_at"],
            "required_permission": "users"
        },
        {
            "name": "tasks",
            "description": "任务信息表",
            "columns": ["id", "task_id", "task_type", "status", "created_at", "updated_at"],
            "required_permission": "tasks"
        },
        {
            "name": "iaas_servers",
            "description": "物理机信息表",
            "columns": ["id", "hostname", "ip_address", "status", "cpu_cores", "memory_gb", "region"],
            "required_permission": "iaas"
        },
        {
            "name": "iaas_instances",
            "description": "虚拟机实例表",
            "columns": ["id", "instance_id", "instance_name", "status", "cpu", "memory", "host"],
            "required_permission": "iaas"
        },
        {
            "name": "audit_logs",
            "description": "审计日志表",
            "columns": ["id", "user_id", "action_type", "created_at"],
            "required_permission": "admin"
        }
    ]
    
    # 根据用户权限过滤表
    accessible_tables = []
    for table in all_tables:
        # 超级管理员可以访问所有表
        if user_role == "SUPER_ADMIN":
            accessible_tables.append({
                "name": table["name"],
                "description": table["description"],
                "columns": table["columns"]
            })
        # 普通用户根据权限过滤
        elif table["required_permission"] in user_permissions or table["required_permission"] == "public":
            accessible_tables.append({
                "name": table["name"],
                "description": table["description"],
                "columns": table["columns"]
            })
    
    return {
        "tables": accessible_tables,
        "total": len(accessible_tables)
    }


@router.get("/report-index")
async def get_report_index(
    report_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    sort_by: str = "generated_at",
    sort_order: str = "desc",
    current_user: User = Depends(get_current_user)
):
    """
    获取报告索引（从数据库查询真实数据）
    
    支持按类型和时间范围过滤、分页、排序
    
    Args:
        report_type: 报告类型（resource_analysis, bcc_monitoring, bos_monitoring, operational_analysis）
        start_date: 开始日期（ISO 8601 格式）
        end_date: 结束日期（ISO 8601 格式）
        limit: 返回数量限制（默认 50，最大 100）
        offset: 跳过数量（默认 0）
        sort_by: 排序字段（默认 generated_at）
        sort_order: 排序顺序（asc/desc，默认 desc）
        current_user: 当前用户
    
    Returns:
        reports: 报告索引列表及统计信息
    """
    import traceback
    from app.core.database import get_db_connection
    
    try:
        # 参数验证
        # 限制 limit 最大值
        if limit > 100:
            limit = 100
        
        # 验证排序字段（防止 SQL 注入）
        allowed_sort_fields = ['generated_at', 'indexed_at', 'report_type', 'task_id']
        if sort_by not in allowed_sort_fields:
            sort_by = 'generated_at'
        
        # 验证排序顺序
        sort_order_sql = 'DESC' if sort_order.lower() == 'desc' else 'ASC'
        
        # 获取数据库连接
        import pymysql.cursors
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # 构建 WHERE 子句
        where_clauses = []
        params = []
        
        if report_type:
            where_clauses.append("report_type = %s")
            params.append(report_type)
        
        if start_date:
            where_clauses.append("generated_at >= %s")
            params.append(start_date.replace('Z', ''))
        
        if end_date:
            where_clauses.append("generated_at <= %s")
            params.append(end_date.replace('Z', ''))
        
        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
        
        # 查询总数
        count_sql = f"SELECT COUNT(*) as total FROM report_index WHERE {where_sql}"
        cursor.execute(count_sql, params)
        total = cursor.fetchone()['total']
        
        # 查询已向量化数量
        vectorized_sql = f"SELECT COUNT(*) as count FROM report_index WHERE {where_sql} AND vectorized = TRUE"
        cursor.execute(vectorized_sql, params)
        vectorized_count = cursor.fetchone()['count']
        
        # 查询报告列表
        list_sql = f"""
            SELECT 
                task_id,
                report_type,
                file_path,
                file_format,
                summary,
                conclusion,
                generated_at,
                indexed_at,
                vectorized,
                vector_id
            FROM report_index
            WHERE {where_sql}
            ORDER BY {sort_by} {sort_order_sql}
            LIMIT %s OFFSET %s
        """
        cursor.execute(list_sql, params + [limit, offset])
        reports = cursor.fetchall()
        
        # 格式化响应数据
        for report in reports:
            # 转换日期时间为 ISO 8601 格式
            if report['generated_at']:
                report['generated_at'] = report['generated_at'].isoformat() + 'Z'
            if report['indexed_at']:
                report['indexed_at'] = report['indexed_at'].isoformat() + 'Z'
            
            # 转换布尔值
            report['vectorized'] = bool(report['vectorized'])
            
            # 处理空值
            if not report['summary']:
                report['summary'] = None
            if not report['conclusion']:
                report['conclusion'] = None
            if not report['vector_id']:
                report['vector_id'] = None
        
        # 关闭连接
        cursor.close()
        conn.close()
        
        # 返回响应
        return {
            "success": True,
            "data": {
                "reports": reports,
                "total": total,
                "vectorized_count": vectorized_count,
                "pending_count": total - vectorized_count,
                "filters": {
                    "report_type": report_type,
                    "start_date": start_date,
                    "end_date": end_date
                },
                "pagination": {
                    "limit": limit,
                    "offset": offset,
                    "has_more": offset + len(reports) < total
                }
            },
            "message": "查询成功"
        }
    
    except Exception as e:
        logger.error(f"❌ 查询报告索引失败: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"查询报告索引失败: {str(e)}"
        )


# ==================== Report Vectorization Endpoints ====================

from app.services.ai.report_vectorization_service import get_vectorization_service


class VectorizeReportRequest(BaseModel):
    """向量化报告请求"""
    task_id: str = Field(..., description="任务ID")
    report_type: Literal["resource_analysis", "bcc_monitoring", "bos_monitoring", "operational_analysis"] = Field(..., description="报告类型")
    file_path: str = Field(..., description="MinIO 文件路径")
    generated_at: Optional[str] = Field(None, description="报告生成时间（ISO 8601 格式）")


class VectorizeReportResponse(BaseModel):
    """向量化报告响应"""
    success: bool
    message: str
    task_id: str
    knowledge_entry_id: Optional[int] = None


@router.post("/vectorize-report")
async def vectorize_report(
    request: VectorizeReportRequest,
    current_user: User = Depends(get_current_user)
):
    """
    手动触发报告向量化
    
    仅超级管理员可以调用此接口
    
    Args:
        request: 向量化请求，包含 task_id, report_type, file_path, generated_at
    
    Returns:
        VectorizeReportResponse: 向量化结果
    
    Validates:
        - Requirements 14.1: 触发报告向量化流程
        - Requirements 14.8: 记录向量化失败日志
        - Requirements 14.9, 14.10, 14.11: 自动创建知识条目
    """
    # 权限检查：仅超级管理员
    user_role = current_user.role
    if user_role != "SUPER_ADMIN":
        raise HTTPException(
            status_code=403,
            detail="仅超级管理员可以手动触发报告向量化"
        )
    
    try:
        # 解析生成时间
        if request.generated_at:
            generated_at = datetime.fromisoformat(request.generated_at.replace('Z', '+00:00'))
        else:
            generated_at = datetime.now()
        
        # 获取向量化服务
        vectorization_service = get_vectorization_service()
        
        # 执行向量化
        success = await vectorization_service.vectorize_report(
            task_id=request.task_id,
            report_type=request.report_type,
            file_path=request.file_path,
            generated_at=generated_at
        )
        
        if success:
            return VectorizeReportResponse(
                success=True,
                message="报告向量化成功",
                task_id=request.task_id
            )
        else:
            return VectorizeReportResponse(
                success=False,
                message="报告向量化失败，请查看日志",
                task_id=request.task_id
            )
    
    except Exception as e:
        logger.error(f"手动向量化报告失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"向量化失败: {str(e)}"
        )


@router.post("/scan-and-vectorize-reports")
async def scan_and_vectorize_reports(
    current_user: User = Depends(get_current_user)
):
    """
    扫描 MinIO 并向量化所有新报告
    
    仅超级管理员可以调用此接口
    
    Returns:
        Dict: 扫描和向量化统计信息
    
    Validates: Requirements 14.1
    """
    # 权限检查：仅超级管理员
    user_role = current_user.role
    if user_role != "SUPER_ADMIN":
        raise HTTPException(
            status_code=403,
            detail="仅超级管理员可以触发批量向量化"
        )
    
    try:
        # 获取向量化服务
        vectorization_service = get_vectorization_service()
        
        # 扫描并向量化
        stats = await vectorization_service.scan_and_vectorize_new_reports()
        
        return {
            "success": True,
            "message": "扫描和向量化完成",
            "stats": stats
        }
    
    except Exception as e:
        logger.error(f"批量向量化失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"批量向量化失败: {str(e)}"
        )


@router.get("/vectorization-status")
async def get_vectorization_status(
    current_user: User = Depends(get_current_user)
):
    """
    获取报告向量化状态统计
    
    Returns:
        Dict: 向量化状态统计
    """
    try:
        from app.core.database import get_db_connection
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 统计总报告数
        cursor.execute("SELECT COUNT(*) FROM report_index")
        total_reports = cursor.fetchone()[0]
        
        # 统计已向量化报告数
        cursor.execute("SELECT COUNT(*) FROM report_index WHERE vectorized = TRUE")
        vectorized_reports = cursor.fetchone()[0]
        
        # 统计未向量化报告数
        cursor.execute("SELECT COUNT(*) FROM report_index WHERE vectorized = FALSE")
        pending_reports = cursor.fetchone()[0]
        
        # 按类型统计
        cursor.execute("""
            SELECT report_type, 
                   COUNT(*) as total,
                   SUM(CASE WHEN vectorized = TRUE THEN 1 ELSE 0 END) as vectorized
            FROM report_index
            GROUP BY report_type
        """)
        by_type = []
        for row in cursor.fetchall():
            by_type.append({
                "report_type": row[0],
                "total": row[1],
                "vectorized": row[2],
                "pending": row[1] - row[2]
            })
        
        cursor.close()
        conn.close()
        
        return {
            "total_reports": total_reports,
            "vectorized_reports": vectorized_reports,
            "pending_reports": pending_reports,
            "vectorization_rate": f"{(vectorized_reports / total_reports * 100):.1f}%" if total_reports > 0 else "0%",
            "by_type": by_type
        }
    
    except Exception as e:
        logger.error(f"获取向量化状态失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取向量化状态失败: {str(e)}"
        )


# ==================== Category and Tag Management Endpoints ====================

class CreateCategoryRequest(BaseModel):
    """创建分类请求"""
    name: str = Field(..., min_length=1, max_length=100, description="分类名称")
    description: Optional[str] = Field(None, max_length=500, description="分类描述")
    display_order: int = Field(0, description="显示顺序")


class CategoryResponse(BaseModel):
    """分类响应"""
    id: int
    name: str
    description: Optional[str]
    display_order: int
    created_at: str
    created_by: Optional[str]


@router.get("/knowledge/categories")
async def get_categories(
    current_user: User = Depends(get_current_user)
):
    """
    获取所有知识分类列表
    
    所有用户都可以访问此接口
    
    Returns:
        List[CategoryResponse]: 分类列表，按 display_order 排序
    
    Validates: Requirements 21.1
    """
    try:
        from app.core.database import get_db_connection
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 查询所有分类，按显示顺序排序
        cursor.execute("""
            SELECT id, name, description, display_order, created_at, created_by
            FROM knowledge_categories
            ORDER BY display_order ASC, name ASC
        """)
        
        categories = []
        for row in cursor.fetchall():
            categories.append({
                "id": row[0],
                "name": row[1],
                "description": row[2],
                "display_order": row[3],
                "created_at": row[4].isoformat() if row[4] else None,
                "created_by": row[5]
            })
        
        cursor.close()
        conn.close()
        
        logger.info(f"✅ 获取分类列表成功: total={len(categories)}")
        
        return {
            "categories": categories,
            "total": len(categories)
        }
    
    except Exception as e:
        logger.error(f"❌ 获取分类列表失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取分类列表失败: {str(e)}"
        )


@router.post("/knowledge/categories")
async def create_category(
    request: CreateCategoryRequest,
    current_user: User = Depends(get_current_user)
):
    """
    创建新的知识分类
    
    仅超级管理员可以调用此接口
    
    Args:
        request: 创建分类请求，包含 name, description, display_order
    
    Returns:
        CategoryResponse: 创建的分类信息
    
    Validates: Requirements 21.2, 21.8
    """
    # 权限检查：仅超级管理员（Requirements 21.8）
    user_role = current_user.role
    if user_role != "SUPER_ADMIN":
        logger.warning(f"⚠️ 非超级管理员尝试创建分类: user_id={current_user.id}, role={user_role}")
        raise HTTPException(
            status_code=403,
            detail="仅超级管理员可以创建知识分类"
        )
    
    try:
        from app.core.database import get_db_connection
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 检查分类名称是否已存在
        cursor.execute("""
            SELECT id FROM knowledge_categories WHERE name = %s
        """, (request.name,))
        
        if cursor.fetchone():
            cursor.close()
            conn.close()
            raise HTTPException(
                status_code=400,
                detail=f"分类名称已存在: {request.name}"
            )
        
        # 插入新分类
        cursor.execute("""
            INSERT INTO knowledge_categories (name, description, display_order, created_by)
            VALUES (%s, %s, %s, %s)
        """, (
            request.name,
            request.description,
            request.display_order,
            current_user.username
        ))
        
        conn.commit()
        category_id = cursor.lastrowid
        
        # 获取创建的分类信息
        cursor.execute("""
            SELECT id, name, description, display_order, created_at, created_by
            FROM knowledge_categories
            WHERE id = %s
        """, (category_id,))
        
        row = cursor.fetchone()
        category = {
            "id": row[0],
            "name": row[1],
            "description": row[2],
            "display_order": row[3],
            "created_at": row[4].isoformat() if row[4] else None,
            "created_by": row[5]
        }
        
        cursor.close()
        conn.close()
        
        logger.info(f"✅ 创建分类成功: id={category_id}, name={request.name}, created_by={current_user.username}")
        
        return category
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"❌ 创建分类失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"创建分类失败: {str(e)}"
        )


class TagResponse(BaseModel):
    """标签响应"""
    id: int
    name: str
    usage_count: int
    created_at: str


@router.get("/knowledge/tags")
async def get_tags(
    min_usage: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user)
):
    """
    获取所有知识标签列表
    
    所有用户都可以访问此接口
    
    Args:
        min_usage: 最小使用次数过滤（默认0，返回所有标签）
        limit: 返回数量限制（默认100）
    
    Returns:
        List[TagResponse]: 标签列表，按使用次数降序排序
    
    Validates: Requirements 21.3
    """
    try:
        from app.core.database import get_db_connection
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 查询标签，按使用次数降序排序
        cursor.execute("""
            SELECT id, name, usage_count, created_at
            FROM knowledge_tags
            WHERE usage_count >= %s
            ORDER BY usage_count DESC, name ASC
            LIMIT %s
        """, (min_usage, limit))
        
        tags = []
        for row in cursor.fetchall():
            tags.append({
                "id": row[0],
                "name": row[1],
                "usage_count": row[2],
                "created_at": row[3].isoformat() if row[3] else None
            })
        
        cursor.close()
        conn.close()
        
        logger.info(f"✅ 获取标签列表成功: total={len(tags)}, min_usage={min_usage}")
        
        return {
            "tags": tags,
            "total": len(tags)
        }
    
    except Exception as e:
        logger.error(f"❌ 获取标签列表失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取标签列表失败: {str(e)}"
        )


# ==================== Vector Database Backup & Restore Endpoints ====================

from app.services.ai.vector_backup_service import get_vector_backup_service


class BackupVectorStoreRequest(BaseModel):
    """备份向量数据库请求"""
    description: Optional[str] = Field(None, max_length=500, description="备份描述")


class BackupVectorStoreResponse(BaseModel):
    """备份向量数据库响应"""
    success: bool
    message: str
    backup_file: str
    backup_path: str
    backup_time: str
    file_size_mb: float
    vector_count: int
    entry_count: int


@router.post("/knowledge/vector-store/backup")
async def backup_vector_store(
    request: BackupVectorStoreRequest,
    current_user: User = Depends(get_current_user)
):
    """
    备份向量数据库
    
    仅超级管理员可以调用此接口
    
    备份内容包括：
    - 向量数据库文件（FAISS 索引、ID 映射、元数据）
    - MySQL 知识库元数据
    - 备份元信息
    
    备份文件压缩后上传到 MinIO 的 vector-backups/ 目录
    
    Args:
        request: 备份请求，包含可选的描述信息
    
    Returns:
        BackupVectorStoreResponse: 备份结果
    
    Validates: Requirements 26.6, 26.7
    """
    # 权限检查：仅超级管理员
    user_role = current_user.role
    if user_role != "SUPER_ADMIN":
        logger.warning(f"⚠️ 非超级管理员尝试备份向量数据库: user_id={current_user.id}, role={user_role}")
        raise HTTPException(
            status_code=403,
            detail="仅超级管理员可以备份向量数据库"
        )
    
    try:
        from app.core.database import get_db_connection
        
        # 获取数据库连接
        db = get_db_connection()
        
        # 获取备份服务
        backup_service = get_vector_backup_service(db)
        
        # 执行备份
        result = await backup_service.backup_vector_store(
            user_id=str(current_user.id),
            username=current_user.username,
            description=request.description
        )
        
        return {
            "success": result["success"],
            "message": "向量数据库备份成功",
            "backup_file": result["backup_file"],
            "backup_path": result["backup_path"],
            "backup_time": result["backup_time"],
            "file_size_mb": result["file_size_mb"],
            "vector_count": result["vector_count"],
            "entry_count": result["entry_count"]
        }
    
    except Exception as e:
        logger.error(f"❌ 备份向量数据库失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"备份失败: {str(e)}"
        )


class RestoreVectorStoreRequest(BaseModel):
    """恢复向量数据库请求"""
    backup_file: str = Field(..., description="备份文件名（例如：backup_20260123_120000.tar.gz）")
    restore_mysql: bool = Field(True, description="是否恢复 MySQL 数据")
    restore_vectors: bool = Field(True, description="是否恢复向量数据库")


class RestoreVectorStoreResponse(BaseModel):
    """恢复向量数据库响应"""
    success: bool
    message: str
    restored_entries: int
    restored_vectors: int
    backup_info: Dict[str, Any]


@router.post("/knowledge/vector-store/restore")
async def restore_vector_store(
    request: RestoreVectorStoreRequest,
    current_user: User = Depends(get_current_user)
):
    """
    恢复向量数据库
    
    仅超级管理员可以调用此接口
    
    从 MinIO 下载备份文件并恢复向量数据库和 MySQL 元数据。
    
    Args:
        request: 恢复请求，包含：
            - backup_file: 备份文件名
            - restore_mysql: 是否恢复 MySQL 数据
            - restore_vectors: 是否恢复向量数据库
    
    Returns:
        RestoreVectorStoreResponse: 恢复结果
    
    Validates: Requirements 26.8, 26.9
    """
    # 权限检查：仅超级管理员
    user_role = current_user.role
    if user_role != "SUPER_ADMIN":
        logger.warning(f"⚠️ 非超级管理员尝试恢复向量数据库: user_id={current_user.id}, role={user_role}")
        raise HTTPException(
            status_code=403,
            detail="仅超级管理员可以恢复向量数据库"
        )
    
    try:
        from app.core.database import get_db_connection
        
        # 获取数据库连接
        db = get_db_connection()
        
        # 获取备份服务
        backup_service = get_vector_backup_service(db)
        
        # 执行恢复
        result = await backup_service.restore_vector_store(
            backup_file=request.backup_file,
            user_id=str(current_user.id),
            username=current_user.username,
            restore_mysql=request.restore_mysql,
            restore_vectors=request.restore_vectors
        )
        
        return {
            "success": result["success"],
            "message": "向量数据库恢复成功",
            "restored_entries": result["restored_entries"],
            "restored_vectors": result["restored_vectors"],
            "backup_info": result["backup_info"]
        }
    
    except Exception as e:
        logger.error(f"❌ 恢复向量数据库失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"恢复失败: {str(e)}"
        )


class RebuildVectorStoreRequest(BaseModel):
    """重建向量索引请求"""
    include_deleted: bool = Field(False, description="是否包含已删除的条目")


class RebuildVectorStoreResponse(BaseModel):
    """重建向量索引响应"""
    success: bool
    message: str
    total_entries: int
    rebuilt_entries: int
    failed_entries: int
    vector_count: int


@router.post("/knowledge/vector-store/rebuild")
async def rebuild_vector_store(
    request: RebuildVectorStoreRequest,
    current_user: User = Depends(get_current_user)
):
    """
    从 MySQL 元数据重建向量索引
    
    仅超级管理员可以调用此接口
    
    当向量数据库文件损坏或需要清理已删除的向量时使用。
    
    Args:
        request: 重建请求，包含：
            - include_deleted: 是否包含已删除的条目
    
    Returns:
        RebuildVectorStoreResponse: 重建结果
    
    Validates: Requirements 26.10, 26.11
    """
    # 权限检查：仅超级管理员
    user_role = current_user.role
    if user_role != "SUPER_ADMIN":
        logger.warning(f"⚠️ 非超级管理员尝试重建向量索引: user_id={current_user.id}, role={user_role}")
        raise HTTPException(
            status_code=403,
            detail="仅超级管理员可以重建向量索引"
        )
    
    try:
        from app.core.database import get_db_connection
        
        # 获取数据库连接
        db = get_db_connection()
        
        # 获取备份服务
        backup_service = get_vector_backup_service(db)
        
        # 执行重建
        result = await backup_service.rebuild_vector_store(
            user_id=str(current_user.id),
            username=current_user.username,
            include_deleted=request.include_deleted
        )
        
        return {
            "success": result["success"],
            "message": "向量索引重建成功",
            "total_entries": result["total_entries"],
            "rebuilt_entries": result["rebuilt_entries"],
            "failed_entries": result["failed_entries"],
            "vector_count": result["vector_count"]
        }
    
    except Exception as e:
        logger.error(f"❌ 重建向量索引失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"重建失败: {str(e)}"
        )


class BackupListResponse(BaseModel):
    """备份列表响应"""
    backups: List[Dict[str, Any]]
    total: int


@router.get("/knowledge/vector-store/backups")
async def list_vector_backups(
    current_user: User = Depends(get_current_user)
):
    """
    列出所有可用的备份文件
    
    仅超级管理员可以调用此接口
    
    Returns:
        BackupListResponse: 备份文件列表
    """
    # 权限检查：仅超级管理员
    user_role = current_user.role
    if user_role != "SUPER_ADMIN":
        raise HTTPException(
            status_code=403,
            detail="仅超级管理员可以查看备份列表"
        )
    
    try:
        from app.core.database import get_db_connection
        
        # 获取数据库连接
        db = get_db_connection()
        
        # 获取备份服务
        backup_service = get_vector_backup_service(db)
        
        # 列出备份
        result = await backup_service.list_backups()
        
        return {
            "backups": result["backups"],
            "total": result["total"]
        }
    
    except Exception as e:
        logger.error(f"❌ 列出备份文件失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"列出备份失败: {str(e)}"
        )


# ==================== Vectorized Content Viewing Endpoints ====================

class VectorizedReportResponse(BaseModel):
    """向量化报告响应"""
    task_id: str
    report_type: str
    file_path: str
    file_format: Optional[str] = None
    summary: str
    conclusion: str
    generated_at: str
    indexed_at: str
    vector_id: str
    knowledge_entries: Optional[List[Dict[str, Any]]] = None


@router.get("/vectorized-reports")
async def get_vectorized_reports(
    report_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user)
):
    """
    获取所有向量化的报告列表
    
    Args:
        report_type: 报告类型（可选）
        limit: 返回数量限制（默认50，最大100）
        offset: 跳过数量（默认0）
    
    Returns:
        Dict: 向量化报告列表
    """
    try:
        from app.core.database import get_db_connection
        
        # 限制 limit 最大值
        if limit > 100:
            limit = 100
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 构建查询
        where_clause = "WHERE vectorized = TRUE"
        params = []
        
        if report_type:
            where_clause += " AND report_type = %s"
            params.append(report_type)
        
        # 查询总数
        count_sql = f"SELECT COUNT(*) FROM report_index {where_clause}"
        cursor.execute(count_sql, params)
        total = cursor.fetchone()[0]
        
        # 查询报告列表
        list_sql = f"""
            SELECT 
                task_id,
                report_type,
                file_path,
                file_format,
                summary,
                conclusion,
                generated_at,
                indexed_at,
                vector_id
            FROM report_index
            {where_clause}
            ORDER BY indexed_at DESC
            LIMIT %s OFFSET %s
        """
        cursor.execute(list_sql, params + [limit, offset])
        
        reports = []
        for row in cursor.fetchall():
            reports.append({
                'task_id': row[0],
                'report_type': row[1],
                'file_path': row[2],
                'file_format': row[3],
                'summary': row[4][:200] + '...' if row[4] and len(row[4]) > 200 else row[4],  # 摘要截断
                'conclusion': row[5][:200] + '...' if row[5] and len(row[5]) > 200 else row[5],  # 结论截断
                'generated_at': row[6].isoformat() + 'Z' if row[6] else None,
                'indexed_at': row[7].isoformat() + 'Z' if row[7] else None,
                'vector_id': row[8]
            })
        
        cursor.close()
        conn.close()
        
        return {
            "success": True,
            "data": {
                "reports": reports,
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_more": offset + len(reports) < total
            },
            "message": "查询成功"
        }
    
    except Exception as e:
        logger.error(f"❌ 查询向量化报告失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"查询失败: {str(e)}"
        )


@router.get("/vectorized-reports/{task_id}")
async def get_vectorized_report_detail(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    获取特定报告的向量化内容详情
    
    Args:
        task_id: 任务ID
    
    Returns:
        VectorizedReportResponse: 报告详情（包含完整的摘要和结论）
    """
    try:
        from app.core.database import get_db_connection
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 查询报告
        cursor.execute("""
            SELECT 
                task_id,
                report_type,
                file_path,
                file_format,
                summary,
                conclusion,
                generated_at,
                indexed_at,
                vector_id
            FROM report_index
            WHERE task_id = %s AND vectorized = TRUE
        """, (task_id,))
        
        row = cursor.fetchone()
        
        if not row:
            cursor.close()
            conn.close()
            raise HTTPException(
                status_code=404,
                detail=f"未找到向量化的报告: {task_id}"
            )
        
        report = {
            'task_id': row[0],
            'report_type': row[1],
            'file_path': row[2],
            'file_format': row[3],
            'summary': row[4],  # 完整摘要
            'conclusion': row[5],  # 完整结论
            'generated_at': row[6].isoformat() + 'Z' if row[6] else None,
            'indexed_at': row[7].isoformat() + 'Z' if row[7] else None,
            'vector_id': row[8]
        }
        
        # 查询关联的知识条目
        cursor.execute("""
            SELECT 
                id,
                title,
                content,
                category,
                tags,
                created_at
            FROM knowledge_entries
            WHERE source = 'auto' AND source_id = %s
        """, (task_id,))
        
        knowledge_entries = []
        for ke_row in cursor.fetchall():
            knowledge_entries.append({
                'id': ke_row[0],
                'title': ke_row[1],
                'content': ke_row[2][:200] + '...' if ke_row[2] and len(ke_row[2]) > 200 else ke_row[2],
                'category': ke_row[3],
                'tags': ke_row[4],
                'created_at': ke_row[5].isoformat() + 'Z' if ke_row[5] else None
            })
        
        report['knowledge_entries'] = knowledge_entries
        
        cursor.close()
        conn.close()
        
        return {
            "success": True,
            "data": report,
            "message": "查询成功"
        }
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"❌ 查询报告详情失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"查询失败: {str(e)}"
        )


@router.get("/tables")
async def get_tables(
    current_user: User = Depends(get_current_user)
):
    """
    获取所有可查询的数据库表列表
    
    返回表名、注释等信息，用于前端表选择器
    
    Returns:
        Dict: 包含表列表的响应
    """
    try:
        from app.services.ai.schema_vector_store import get_schema_vector_store
        
        # 获取Schema向量存储实例
        schema_store = get_schema_vector_store()
        
        # 获取所有表的schema信息
        tables = []
        
        # 优先从 schema_cache 获取（这是正确的数据源）
        if schema_store.schema_cache:
            logger.info(f"📦 从 schema_cache 获取表列表: {len(schema_store.schema_cache)} 个表")
            for table_name, schema_info in schema_store.schema_cache.items():
                # 提取表的描述信息
                description = schema_info.get("description", "")
                
                # 尝试从描述中提取用途说明
                comment = ""
                if description:
                    # 描述格式: "数据源: xxx\n表名: xxx\n用途: xxx\n字段数量: xxx\n字段列表:\n..."
                    lines = description.split("\n")
                    for line in lines:
                        if line.startswith("用途:"):
                            comment = line.replace("用途:", "").strip()
                            break
                
                # 如果没有用途说明，尝试从表名推断
                if not comment:
                    # 提取纯表名（去除数据库前缀）
                    pure_table_name = table_name.split(".")[-1] if "." in table_name else table_name
                    
                    # 使用 _infer_table_purpose 推断用途
                    inferred_purpose = schema_store._infer_table_purpose(pure_table_name)
                    if inferred_purpose:
                        comment = inferred_purpose
                    else:
                        comment = f"{pure_table_name} 表"
                
                tables.append({
                    "table_name": table_name,
                    "comment": comment,
                    "table_comment": comment
                })
        else:
            # 如果Schema缓存为空，从数据库直接查询
            logger.warning("⚠️ schema_cache 为空，从数据库直接查询")
            from app.core.database import get_db_connection
            import pymysql.cursors
            
            conn = get_db_connection()
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            # 查询所有表
            cursor.execute("""
                SELECT 
                    TABLE_NAME as table_name,
                    TABLE_COMMENT as comment
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_TYPE = 'BASE TABLE'
                ORDER BY TABLE_NAME
            """)
            
            for row in cursor.fetchall():
                comment = row["comment"] or f"{row['table_name']} 表"
                tables.append({
                    "table_name": row["table_name"],
                    "comment": comment,
                    "table_comment": comment
                })
            
            cursor.close()
            conn.close()
        
        logger.info(f"✅ 返回 {len(tables)} 个表，示例: {tables[:3] if tables else '无'}")
        
        return {
            "success": True,
            "data": tables,
            "message": "查询成功"
        }
    
    except Exception as e:
        logger.error(f"❌ 获取表列表失败: {e}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"获取表列表失败: {str(e)}"
        )
