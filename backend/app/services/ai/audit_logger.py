# -*- coding: utf-8 -*-
"""
AI 智能查询审计日志记录器

负责记录所有 AI 查询操作的审计日志，包括：
- 查询提交、成功、失败、超时
- SQL 安全拒绝事件
- 知识库操作（创建、更新、删除）
- 认证验证事件

Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6
"""

import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.logger import logger


class AuditLogger:
    """审计日志记录器"""
    
    def __init__(self, db: Session):
        """
        初始化审计日志记录器
        
        Args:
            db: 数据库会话
        """
        self.db = db
    
    async def log_query_submit(
        self,
        user_id: str,
        username: str,
        nl_query: str,
        intent_type: Optional[str] = None,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> int:
        """
        记录查询提交事件
        
        Args:
            user_id: 用户ID
            username: 用户名
            nl_query: 自然语言查询文本
            intent_type: 意图类型（sql/rag_report/rag_knowledge/chat/mixed）
            session_id: 会话ID
            ip_address: IP地址
            user_agent: User Agent
            
        Returns:
            日志记录ID
            
        Validates: Requirements 8.1
        """
        try:
            sql_stmt = text("""
                INSERT INTO ai_audit_logs (
                    user_id, username, action_type, nl_query, intent_type,
                    session_id, ip_address, user_agent, created_at
                ) VALUES (
                    :user_id, :username, 'query_submit', :nl_query, :intent_type,
                    :session_id, :ip_address, :user_agent, :created_at
                )
            """)
            
            result = self.db.execute(sql_stmt, {
                "user_id": user_id,
                "username": username,
                "nl_query": nl_query,
                "intent_type": intent_type,
                "session_id": session_id,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "created_at": datetime.now()
            })
            self.db.commit()
            
            log_id = result.lastrowid
            logger.info(f"✅ 审计日志: 查询提交 - user={username}, query={nl_query[:50]}..., log_id={log_id}")
            return log_id
            
        except Exception as e:
            logger.error(f"❌ 记录查询提交日志失败: {e}")
            self.db.rollback()
            raise
    
    async def log_query_success(
        self,
        user_id: str,
        username: str,
        nl_query: str,
        generated_sql: Optional[str] = None,
        intent_type: Optional[str] = None,
        execution_time_ms: Optional[int] = None,
        row_count: Optional[int] = None,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> int:
        """
        记录查询成功事件
        
        Args:
            user_id: 用户ID
            username: 用户名
            nl_query: 自然语言查询文本
            generated_sql: 生成的SQL语句
            intent_type: 意图类型
            execution_time_ms: 执行时间（毫秒）
            row_count: 返回行数
            session_id: 会话ID
            ip_address: IP地址
            user_agent: User Agent
            
        Returns:
            日志记录ID
            
        Validates: Requirements 8.2, 8.3
        """
        try:
            sql_stmt = text("""
                INSERT INTO ai_audit_logs (
                    user_id, username, action_type, nl_query, generated_sql, intent_type,
                    execution_status, execution_time_ms, row_count,
                    session_id, ip_address, user_agent, created_at
                ) VALUES (
                    :user_id, :username, 'query_success', :nl_query, :generated_sql, :intent_type,
                    'success', :execution_time_ms, :row_count,
                    :session_id, :ip_address, :user_agent, :created_at
                )
            """)
            
            result = self.db.execute(sql_stmt, {
                "user_id": user_id,
                "username": username,
                "nl_query": nl_query,
                "generated_sql": generated_sql,
                "intent_type": intent_type,
                "execution_time_ms": execution_time_ms,
                "row_count": row_count,
                "session_id": session_id,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "created_at": datetime.now()
            })
            self.db.commit()
            
            log_id = result.lastrowid
            logger.info(
                f"✅ 审计日志: 查询成功 - user={username}, "
                f"time={execution_time_ms}ms, rows={row_count}, log_id={log_id}"
            )
            return log_id
            
        except Exception as e:
            logger.error(f"❌ 记录查询成功日志失败: {e}")
            self.db.rollback()
            raise
    
    async def log_query_error(
        self,
        user_id: str,
        username: str,
        nl_query: str,
        error_message: str,
        generated_sql: Optional[str] = None,
        intent_type: Optional[str] = None,
        execution_time_ms: Optional[int] = None,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> int:
        """
        记录查询失败事件
        
        Args:
            user_id: 用户ID
            username: 用户名
            nl_query: 自然语言查询文本
            error_message: 错误消息
            generated_sql: 生成的SQL语句
            intent_type: 意图类型
            execution_time_ms: 执行时间（毫秒）
            session_id: 会话ID
            ip_address: IP地址
            user_agent: User Agent
            
        Returns:
            日志记录ID
            
        Validates: Requirements 8.5
        """
        try:
            sql_stmt = text("""
                INSERT INTO ai_audit_logs (
                    user_id, username, action_type, nl_query, generated_sql, intent_type,
                    execution_status, execution_time_ms, error_message,
                    session_id, ip_address, user_agent, created_at
                ) VALUES (
                    :user_id, :username, 'query_error', :nl_query, :generated_sql, :intent_type,
                    'error', :execution_time_ms, :error_message,
                    :session_id, :ip_address, :user_agent, :created_at
                )
            """)
            
            result = self.db.execute(sql_stmt, {
                "user_id": user_id,
                "username": username,
                "nl_query": nl_query,
                "generated_sql": generated_sql,
                "intent_type": intent_type,
                "execution_time_ms": execution_time_ms,
                "error_message": error_message,
                "session_id": session_id,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "created_at": datetime.now()
            })
            self.db.commit()
            
            log_id = result.lastrowid
            logger.warning(
                f"⚠️ 审计日志: 查询失败 - user={username}, "
                f"error={error_message[:100]}, log_id={log_id}"
            )
            return log_id
            
        except Exception as e:
            logger.error(f"❌ 记录查询失败日志失败: {e}")
            self.db.rollback()
            raise
    
    async def log_query_timeout(
        self,
        user_id: str,
        username: str,
        nl_query: str,
        generated_sql: Optional[str] = None,
        intent_type: Optional[str] = None,
        execution_time_ms: Optional[int] = None,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> int:
        """
        记录查询超时事件
        
        Args:
            user_id: 用户ID
            username: 用户名
            nl_query: 自然语言查询文本
            generated_sql: 生成的SQL语句
            intent_type: 意图类型
            execution_time_ms: 执行时间（毫秒）
            session_id: 会话ID
            ip_address: IP地址
            user_agent: User Agent
            
        Returns:
            日志记录ID
            
        Validates: Requirements 8.3
        """
        try:
            sql_stmt = text("""
                INSERT INTO ai_audit_logs (
                    user_id, username, action_type, nl_query, generated_sql, intent_type,
                    execution_status, execution_time_ms, error_message,
                    session_id, ip_address, user_agent, created_at
                ) VALUES (
                    :user_id, :username, 'query_timeout', :nl_query, :generated_sql, :intent_type,
                    'timeout', :execution_time_ms, '查询执行超时',
                    :session_id, :ip_address, :user_agent, :created_at
                )
            """)
            
            result = self.db.execute(sql_stmt, {
                "user_id": user_id,
                "username": username,
                "nl_query": nl_query,
                "generated_sql": generated_sql,
                "intent_type": intent_type,
                "execution_time_ms": execution_time_ms,
                "session_id": session_id,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "created_at": datetime.now()
            })
            self.db.commit()
            
            log_id = result.lastrowid
            logger.warning(
                f"⚠️ 审计日志: 查询超时 - user={username}, "
                f"time={execution_time_ms}ms, log_id={log_id}"
            )
            return log_id
            
        except Exception as e:
            logger.error(f"❌ 记录查询超时日志失败: {e}")
            self.db.rollback()
            raise
    
    async def log_sql_rejected(
        self,
        user_id: str,
        username: str,
        nl_query: str,
        generated_sql: str,
        rejection_reason: str,
        security_event_details: Optional[Dict[str, Any]] = None,
        intent_type: Optional[str] = None,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> int:
        """
        记录SQL安全拒绝事件
        
        Args:
            user_id: 用户ID
            username: 用户名
            nl_query: 自然语言查询文本
            generated_sql: 生成的SQL语句
            rejection_reason: 拒绝原因
            security_event_details: 安全事件详情
            intent_type: 意图类型
            session_id: 会话ID
            ip_address: IP地址
            user_agent: User Agent
            
        Returns:
            日志记录ID
            
        Validates: Requirements 8.4
        """
        try:
            # 构建安全事件详情
            event_details = security_event_details or {}
            event_details["rejection_reason"] = rejection_reason
            event_details["sql"] = generated_sql
            
            sql_stmt = text("""
                INSERT INTO ai_audit_logs (
                    user_id, username, action_type, nl_query, generated_sql, intent_type,
                    execution_status, error_message,
                    security_event_type, security_event_details,
                    session_id, ip_address, user_agent, created_at
                ) VALUES (
                    :user_id, :username, 'sql_rejected', :nl_query, :generated_sql, :intent_type,
                    'rejected', :error_message,
                    'sql_security_violation', :security_event_details,
                    :session_id, :ip_address, :user_agent, :created_at
                )
            """)
            
            result = self.db.execute(sql_stmt, {
                "user_id": user_id,
                "username": username,
                "nl_query": nl_query,
                "generated_sql": generated_sql,
                "intent_type": intent_type,
                "error_message": rejection_reason,
                "security_event_details": json.dumps(event_details, ensure_ascii=False),
                "session_id": session_id,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "created_at": datetime.now()
            })
            self.db.commit()
            
            log_id = result.lastrowid
            logger.warning(
                f"🚨 审计日志: SQL拒绝 - user={username}, "
                f"reason={rejection_reason}, log_id={log_id}"
            )
            return log_id
            
        except Exception as e:
            logger.error(f"❌ 记录SQL拒绝日志失败: {e}")
            self.db.rollback()
            raise
    
    async def log_knowledge_create(
        self,
        user_id: str,
        username: str,
        entry_id: int,
        entry_data: Dict[str, Any],
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> int:
        """
        记录知识库创建事件
        
        Args:
            user_id: 用户ID
            username: 用户名
            entry_id: 知识条目ID
            entry_data: 知识条目数据
            session_id: 会话ID
            ip_address: IP地址
            user_agent: User Agent
            
        Returns:
            日志记录ID
            
        Validates: Requirements 8.4
        """
        try:
            operation_details = {
                "operation": "create",
                "entry_id": entry_id,
                "title": entry_data.get("title"),
                "category": entry_data.get("category"),
                "source": entry_data.get("source", "manual")
            }
            
            sql_stmt = text("""
                INSERT INTO ai_audit_logs (
                    user_id, username, action_type,
                    knowledge_entry_id, knowledge_operation,
                    session_id, ip_address, user_agent, created_at
                ) VALUES (
                    :user_id, :username, 'knowledge_create',
                    :knowledge_entry_id, :knowledge_operation,
                    :session_id, :ip_address, :user_agent, :created_at
                )
            """)
            
            result = self.db.execute(sql_stmt, {
                "user_id": user_id,
                "username": username,
                "knowledge_entry_id": entry_id,
                "knowledge_operation": json.dumps(operation_details, ensure_ascii=False),
                "session_id": session_id,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "created_at": datetime.now()
            })
            self.db.commit()
            
            log_id = result.lastrowid
            logger.info(
                f"✅ 审计日志: 知识库创建 - user={username}, "
                f"entry_id={entry_id}, title={entry_data.get('title')}, log_id={log_id}"
            )
            return log_id
            
        except Exception as e:
            logger.error(f"❌ 记录知识库创建日志失败: {e}")
            self.db.rollback()
            raise
    
    async def log_knowledge_update(
        self,
        user_id: str,
        username: str,
        entry_id: int,
        updates: Dict[str, Any],
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> int:
        """
        记录知识库更新事件
        
        Args:
            user_id: 用户ID
            username: 用户名
            entry_id: 知识条目ID
            updates: 更新的字段
            session_id: 会话ID
            ip_address: IP地址
            user_agent: User Agent
            
        Returns:
            日志记录ID
            
        Validates: Requirements 8.4
        """
        try:
            operation_details = {
                "operation": "update",
                "entry_id": entry_id,
                "updated_fields": list(updates.keys()),
                "updates": updates
            }
            
            sql_stmt = text("""
                INSERT INTO ai_audit_logs (
                    user_id, username, action_type,
                    knowledge_entry_id, knowledge_operation,
                    session_id, ip_address, user_agent, created_at
                ) VALUES (
                    :user_id, :username, 'knowledge_update',
                    :knowledge_entry_id, :knowledge_operation,
                    :session_id, :ip_address, :user_agent, :created_at
                )
            """)
            
            result = self.db.execute(sql_stmt, {
                "user_id": user_id,
                "username": username,
                "knowledge_entry_id": entry_id,
                "knowledge_operation": json.dumps(operation_details, ensure_ascii=False),
                "session_id": session_id,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "created_at": datetime.now()
            })
            self.db.commit()
            
            log_id = result.lastrowid
            logger.info(
                f"✅ 审计日志: 知识库更新 - user={username}, "
                f"entry_id={entry_id}, fields={list(updates.keys())}, log_id={log_id}"
            )
            return log_id
            
        except Exception as e:
            logger.error(f"❌ 记录知识库更新日志失败: {e}")
            self.db.rollback()
            raise
    
    async def log_knowledge_delete(
        self,
        user_id: str,
        username: str,
        entry_id: int,
        entry_title: Optional[str] = None,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> int:
        """
        记录知识库删除事件
        
        Args:
            user_id: 用户ID
            username: 用户名
            entry_id: 知识条目ID
            entry_title: 知识条目标题
            session_id: 会话ID
            ip_address: IP地址
            user_agent: User Agent
            
        Returns:
            日志记录ID
            
        Validates: Requirements 8.4
        """
        try:
            operation_details = {
                "operation": "delete",
                "entry_id": entry_id,
                "title": entry_title
            }
            
            sql_stmt = text("""
                INSERT INTO ai_audit_logs (
                    user_id, username, action_type,
                    knowledge_entry_id, knowledge_operation,
                    session_id, ip_address, user_agent, created_at
                ) VALUES (
                    :user_id, :username, 'knowledge_delete',
                    :knowledge_entry_id, :knowledge_operation,
                    :session_id, :ip_address, :user_agent, :created_at
                )
            """)
            
            result = self.db.execute(sql_stmt, {
                "user_id": user_id,
                "username": username,
                "knowledge_entry_id": entry_id,
                "knowledge_operation": json.dumps(operation_details, ensure_ascii=False),
                "session_id": session_id,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "created_at": datetime.now()
            })
            self.db.commit()
            
            log_id = result.lastrowid
            logger.warning(
                f"⚠️ 审计日志: 知识库删除 - user={username}, "
                f"entry_id={entry_id}, title={entry_title}, log_id={log_id}"
            )
            return log_id
            
        except Exception as e:
            logger.error(f"❌ 记录知识库删除日志失败: {e}")
            self.db.rollback()
            raise
    
    async def log_auth_verify_success(
        self,
        user_id: str,
        username: str,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> int:
        """
        记录认证验证成功事件
        
        Args:
            user_id: 用户ID
            username: 用户名
            session_id: 会话ID
            ip_address: IP地址
            user_agent: User Agent
            
        Returns:
            日志记录ID
        """
        try:
            sql_stmt = text("""
                INSERT INTO ai_audit_logs (
                    user_id, username, action_type,
                    session_id, ip_address, user_agent, created_at
                ) VALUES (
                    :user_id, :username, 'auth_verify_success',
                    :session_id, :ip_address, :user_agent, :created_at
                )
            """)
            
            result = self.db.execute(sql_stmt, {
                "user_id": user_id,
                "username": username,
                "session_id": session_id,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "created_at": datetime.now()
            })
            self.db.commit()
            
            log_id = result.lastrowid
            logger.info(f"✅ 审计日志: 认证成功 - user={username}, log_id={log_id}")
            return log_id
            
        except Exception as e:
            logger.error(f"❌ 记录认证成功日志失败: {e}")
            self.db.rollback()
            raise
    
    async def log_auth_verify_failed(
        self,
        user_id: str,
        username: str,
        failure_reason: str = "密码错误",
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> int:
        """
        记录认证验证失败事件
        
        Args:
            user_id: 用户ID
            username: 用户名
            failure_reason: 失败原因
            session_id: 会话ID
            ip_address: IP地址
            user_agent: User Agent
            
        Returns:
            日志记录ID
        """
        try:
            sql_stmt = text("""
                INSERT INTO ai_audit_logs (
                    user_id, username, action_type, error_message,
                    session_id, ip_address, user_agent, created_at
                ) VALUES (
                    :user_id, :username, 'auth_verify_failed', :error_message,
                    :session_id, :ip_address, :user_agent, :created_at
                )
            """)
            
            result = self.db.execute(sql_stmt, {
                "user_id": user_id,
                "username": username,
                "error_message": failure_reason,
                "session_id": session_id,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "created_at": datetime.now()
            })
            self.db.commit()
            
            log_id = result.lastrowid
            logger.warning(
                f"⚠️ 审计日志: 认证失败 - user={username}, "
                f"reason={failure_reason}, log_id={log_id}"
            )
            return log_id
            
        except Exception as e:
            logger.error(f"❌ 记录认证失败日志失败: {e}")
            self.db.rollback()
            raise
    
    async def get_user_query_history(
        self,
        user_id: str,
        limit: int = 10,
        action_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        获取用户查询历史
        
        Args:
            user_id: 用户ID
            limit: 返回记录数量限制
            action_types: 操作类型过滤（可选）
            
        Returns:
            查询历史记录列表
        """
        try:
            if action_types:
                placeholders = ','.join([f"'{t}'" for t in action_types])
                sql_stmt = text(f"""
                    SELECT 
                        id, user_id, username, action_type, nl_query, generated_sql,
                        intent_type, execution_status, execution_time_ms, row_count,
                        error_message, created_at
                    FROM ai_audit_logs
                    WHERE user_id = :user_id
                        AND action_type IN ({placeholders})
                    ORDER BY created_at DESC
                    LIMIT :limit
                """)
            else:
                sql_stmt = text("""
                    SELECT 
                        id, user_id, username, action_type, nl_query, generated_sql,
                        intent_type, execution_status, execution_time_ms, row_count,
                        error_message, created_at
                    FROM ai_audit_logs
                    WHERE user_id = :user_id
                    ORDER BY created_at DESC
                    LIMIT :limit
                """)
            
            result = self.db.execute(sql_stmt, {
                "user_id": user_id,
                "limit": limit
            })
            
            rows = result.fetchall()
            history = []
            for row in rows:
                # Handle created_at - could be datetime or string depending on database
                created_at = row[11]
                if created_at:
                    if hasattr(created_at, 'isoformat'):
                        created_at = created_at.isoformat()
                    elif isinstance(created_at, str):
                        created_at = created_at
                    else:
                        created_at = str(created_at)
                
                history.append({
                    "id": row[0],
                    "user_id": row[1],
                    "username": row[2],
                    "action_type": row[3],
                    "nl_query": row[4],
                    "generated_sql": row[5],
                    "intent_type": row[6],
                    "execution_status": row[7],
                    "execution_time_ms": row[8],
                    "row_count": row[9],
                    "error_message": row[10],
                    "created_at": created_at
                })
            
            return history
            
        except Exception as e:
            logger.error(f"❌ 获取用户查询历史失败: {e}")
            return []
    
    async def get_security_events(
        self,
        limit: int = 50,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取安全事件列表
        
        Args:
            limit: 返回记录数量限制
            user_id: 用户ID过滤（可选）
            
        Returns:
            安全事件记录列表
        """
        try:
            if user_id:
                sql_stmt = text("""
                    SELECT 
                        id, user_id, username, action_type, nl_query, generated_sql,
                        security_event_type, security_event_details, error_message,
                        ip_address, created_at
                    FROM ai_audit_logs
                    WHERE action_type = 'sql_rejected'
                        AND user_id = :user_id
                    ORDER BY created_at DESC
                    LIMIT :limit
                """)
                result = self.db.execute(sql_stmt, {
                    "user_id": user_id,
                    "limit": limit
                })
            else:
                sql_stmt = text("""
                    SELECT 
                        id, user_id, username, action_type, nl_query, generated_sql,
                        security_event_type, security_event_details, error_message,
                        ip_address, created_at
                    FROM ai_audit_logs
                    WHERE action_type = 'sql_rejected'
                    ORDER BY created_at DESC
                    LIMIT :limit
                """)
                result = self.db.execute(sql_stmt, {
                    "limit": limit
                })
            
            rows = result.fetchall()
            events = []
            for row in rows:
                event_details = None
                if row[7]:  # security_event_details
                    try:
                        event_details = json.loads(row[7])
                    except:
                        event_details = row[7]
                
                # Handle created_at - could be datetime or string depending on database
                created_at = row[10]
                if created_at:
                    if hasattr(created_at, 'isoformat'):
                        created_at = created_at.isoformat()
                    elif isinstance(created_at, str):
                        created_at = created_at
                    else:
                        created_at = str(created_at)
                
                events.append({
                    "id": row[0],
                    "user_id": row[1],
                    "username": row[2],
                    "action_type": row[3],
                    "nl_query": row[4],
                    "generated_sql": row[5],
                    "security_event_type": row[6],
                    "security_event_details": event_details,
                    "error_message": row[8],
                    "ip_address": row[9],
                    "created_at": created_at
                })
            
            return events
            
        except Exception as e:
            logger.error(f"❌ 获取安全事件失败: {e}")
            return []
