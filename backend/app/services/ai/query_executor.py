#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SQL 查询执行器

实现需求：
- Requirements 5.1: 创建只读数据库连接池
- Requirements 5.2: 实现 SQL 执行方法
- Requirements 5.3: 设置 MySQL 执行超时（5 秒）
- Requirements 5.4: 实现超时控制和错误处理
- Requirements 5.5: 记录执行结果到审计日志
"""

import time
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import OperationalError, DatabaseError

from app.core.config import settings
from app.core.logger import logger
from app.services.ai.audit_logger import AuditLogger


class QueryExecutor:
    """SQL 查询执行器"""
    
    def __init__(self, audit_logger: Optional[AuditLogger] = None):
        """
        初始化查询执行器
        
        Args:
            audit_logger: 审计日志记录器（可选）
        """
        self.audit_logger = audit_logger
        
        # 创建只读数据库连接（使用同步引擎）
        # Requirements 5.1: 创建只读数据库连接池
        READONLY_DATABASE_URL = settings.DATABASE_URL.replace(
            "mysql+aiomysql", "mysql+pymysql"
        )
        
        self.readonly_engine = create_engine(
            READONLY_DATABASE_URL,
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            pool_recycle=3600,
            # 设置连接超时
            connect_args={
                "connect_timeout": 5,
                "read_timeout": 5,
                "write_timeout": 5
            }
        )
        
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.readonly_engine
        )
        
        logger.info("✅ 查询执行器初始化成功（只读连接池）")
    
    async def execute_query(
        self,
        sql: str,
        user_id: str,
        username: str,
        nl_query: Optional[str] = None,
        timeout_seconds: int = 5,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Tuple[bool, Optional[List[Dict[str, Any]]], Optional[str], int]:
        """
        执行 SQL 查询（支持多数据源）
        
        Args:
            sql: SQL 语句
            user_id: 用户ID
            username: 用户名
            nl_query: 自然语言查询（用于审计日志）
            timeout_seconds: 超时时间（秒），默认 5 秒
            session_id: 会话ID
            ip_address: IP地址
            user_agent: User Agent
        
        Returns:
            (success, results, error_message, execution_time_ms)
            - success: 是否成功
            - results: 查询结果列表（字典列表）
            - error_message: 错误消息（如果失败）
            - execution_time_ms: 执行时间（毫秒）
        
        Validates:
            - Requirements 5.2: 实现 SQL 执行方法
            - Requirements 5.3: 设置 MySQL 执行超时（5 秒）
            - Requirements 5.4: 实现超时控制和错误处理
            - Requirements 5.5: 记录执行结果到审计日志
        """
        start_time = time.time()
        db = None
        
        # 检测 SQL 是否使用第二数据源（宿主机数据库）
        use_secondary = self._detect_secondary_datasource(sql)
        
        try:
            # 创建数据库会话（根据数据源选择）
            if use_secondary:
                logger.info(f"🔍 使用第二数据源（宿主机数据库）执行查询")
                db = self._get_secondary_session()
            else:
                db = self.SessionLocal()
            
            # 设置会话超时（MySQL 特定）
            # Requirements 5.3: 设置 MySQL 执行超时（5 秒）
            db.execute(text(f"SET SESSION max_execution_time = {timeout_seconds * 1000}"))
            
            logger.info(f"🔍 执行查询 - user={username}, timeout={timeout_seconds}s, secondary={use_secondary}")
            logger.debug(f"SQL: {sql}")
            
            # 执行查询
            result = db.execute(text(sql))
            
            # 获取结果
            rows = result.fetchall()
            columns = result.keys()
            
            # 转换为字典列表
            results = []
            for row in rows:
                row_dict = {}
                for i, col in enumerate(columns):
                    value = row[i]
                    # 处理特殊类型
                    if hasattr(value, 'isoformat'):
                        # datetime 对象转换为 ISO 格式字符串
                        value = value.isoformat()
                    row_dict[col] = value
                results.append(row_dict)
            
            # 计算执行时间
            execution_time_ms = int((time.time() - start_time) * 1000)
            row_count = len(results)
            
            logger.info(
                f"✅ 查询成功 - user={username}, "
                f"rows={row_count}, time={execution_time_ms}ms"
            )
            
            # 记录审计日志
            # Requirements 5.5: 记录执行结果到审计日志
            if self.audit_logger:
                try:
                    await self.audit_logger.log_query_success(
                        user_id=user_id,
                        username=username,
                        nl_query=nl_query or sql,
                        generated_sql=sql,
                        intent_type="sql",
                        execution_time_ms=execution_time_ms,
                        row_count=row_count,
                        session_id=session_id,
                        ip_address=ip_address,
                        user_agent=user_agent
                    )
                except Exception as log_error:
                    logger.error(f"❌ 记录审计日志失败: {log_error}")
            
            return True, results, None, execution_time_ms
            
        except OperationalError as e:
            # 数据库操作错误（包括超时）
            execution_time_ms = int((time.time() - start_time) * 1000)
            error_message = str(e)
            
            # 检查是否为超时错误
            # Requirements 5.4: 实现超时控制和错误处理
            if "max_execution_time" in error_message.lower() or "timeout" in error_message.lower():
                logger.warning(
                    f"⏱️ 查询超时 - user={username}, "
                    f"time={execution_time_ms}ms, timeout={timeout_seconds}s"
                )
                
                # 记录超时审计日志
                if self.audit_logger:
                    try:
                        await self.audit_logger.log_query_timeout(
                            user_id=user_id,
                            username=username,
                            nl_query=nl_query or sql,
                            generated_sql=sql,
                            intent_type="sql",
                            execution_time_ms=execution_time_ms,
                            session_id=session_id,
                            ip_address=ip_address,
                            user_agent=user_agent
                        )
                    except Exception as log_error:
                        logger.error(f"❌ 记录审计日志失败: {log_error}")
                
                return False, None, f"查询执行超时（{timeout_seconds}秒）", execution_time_ms
            else:
                logger.error(f"❌ 数据库操作错误 - user={username}: {error_message}")
                
                # 记录错误审计日志
                if self.audit_logger:
                    try:
                        await self.audit_logger.log_query_error(
                            user_id=user_id,
                            username=username,
                            nl_query=nl_query or sql,
                            error_message=error_message,
                            generated_sql=sql,
                            intent_type="sql",
                            execution_time_ms=execution_time_ms,
                            session_id=session_id,
                            ip_address=ip_address,
                            user_agent=user_agent
                        )
                    except Exception as log_error:
                        logger.error(f"❌ 记录审计日志失败: {log_error}")
                
                return False, None, f"数据库操作错误: {error_message}", execution_time_ms
        
        except DatabaseError as e:
            # 数据库错误
            execution_time_ms = int((time.time() - start_time) * 1000)
            error_message = str(e)
            
            logger.error(f"❌ 数据库错误 - user={username}: {error_message}")
            
            # 记录错误审计日志
            if self.audit_logger:
                try:
                    await self.audit_logger.log_query_error(
                        user_id=user_id,
                        username=username,
                        nl_query=nl_query or sql,
                        error_message=error_message,
                        generated_sql=sql,
                        intent_type="sql",
                        execution_time_ms=execution_time_ms,
                        session_id=session_id,
                        ip_address=ip_address,
                        user_agent=user_agent
                    )
                except Exception as log_error:
                    logger.error(f"❌ 记录审计日志失败: {log_error}")
            
            return False, None, f"数据库错误: {error_message}", execution_time_ms
        
        except Exception as e:
            # 其他错误
            execution_time_ms = int((time.time() - start_time) * 1000)
            error_message = str(e)
            
            logger.error(f"❌ 查询执行失败 - user={username}: {error_message}")
            
            # 记录错误审计日志
            if self.audit_logger:
                try:
                    await self.audit_logger.log_query_error(
                        user_id=user_id,
                        username=username,
                        nl_query=nl_query or sql,
                        error_message=error_message,
                        generated_sql=sql,
                        intent_type="sql",
                        execution_time_ms=execution_time_ms,
                        session_id=session_id,
                        ip_address=ip_address,
                        user_agent=user_agent
                    )
                except Exception as log_error:
                    logger.error(f"❌ 记录审计日志失败: {log_error}")
            
            return False, None, f"查询执行失败: {error_message}", execution_time_ms
        
        finally:
            # 关闭数据库会话
            if db:
                db.close()
    
    def _detect_secondary_datasource(self, sql: str) -> bool:
        """
        检测 SQL 是否使用第二数据源（宿主机数据库）
        
        规则：
        - 容器内数据库（主数据源）：CMDB表（iaas_servers, iaas_instances, iaas_clusters等）
        - 宿主机数据库（第二数据源）：监控数据表（mydb.bce_*等）
        
        Args:
            sql: SQL 语句
        
        Returns:
            是否使用第二数据源
        """
        import re
        
        # 容器内数据库的表（CMDB表）
        # 这些表保存物理机信息、虚机信息等底层数据
        primary_tables = [
            'iaas_servers',      # 物理服务器表
            'iaas_instances',    # 虚拟机实例表
            'iaas_clusters',     # 集群表
            'users',             # 用户表
            'tasks',             # 任务表
            'audit_logs',        # 审计日志
            'knowledge_entries', # 知识库
            'report_index',      # 报告索引
            'chat_history',      # 聊天历史
            'has_alerts',        # 告警表
            'routing_rules',     # 路由规则
            'routing_logs',      # 路由日志
        ]
        
        # 检查SQL中是否包含容器内数据库的表
        for table in primary_tables:
            # 匹配模式：`table` 或 table（带或不带反引号）
            pattern = rf'`?{table}`?'
            if re.search(pattern, sql, re.IGNORECASE):
                # 找到容器内表，使用主数据源
                return False
        
        # 检测 SQL 中是否包含 mydb. 或其他宿主机数据库前缀
        # 匹配模式：`mydb`.`table` 或 mydb.table
        secondary_db_pattern = r'`?(mydb|bcc_monitor|bos_monitoring|gpu_monitoring|gpu_stats|h20_l20_gpu_monitoring)`?\.'
        if re.search(secondary_db_pattern, sql, re.IGNORECASE):
            # 找到宿主机数据库前缀，使用第二数据源
            return True
        
        # 默认使用主数据源（容器内数据库）
        return False
    
    def _get_secondary_session(self):
        """
        获取第二数据源的数据库会话
        
        Returns:
            数据库会话对象
        """
        if not hasattr(self, 'secondary_engine'):
            # 创建第二数据源的引擎（延迟初始化）
            from app.core.config import settings
            
            if not hasattr(settings, 'MYSQL_HOST_2'):
                raise RuntimeError("第二数据源未配置，请在 .env 中添加 MYSQL_HOST_2 等配置")
            
            # 构建第二数据源 URL
            db_url_2 = f"mysql+pymysql://{settings.MYSQL_USER_2}:{settings.MYSQL_PASSWORD_2}@{settings.MYSQL_HOST_2}:{getattr(settings, 'MYSQL_PORT_2', 3306)}/{settings.MYSQL_DATABASE_2}?charset=utf8mb4"
            
            self.secondary_engine = create_engine(
                db_url_2,
                poolclass=QueuePool,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,
                pool_recycle=3600,
                connect_args={
                    "connect_timeout": 5,
                    "read_timeout": 5,
                    "write_timeout": 5
                }
            )
            
            self.SecondarySessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.secondary_engine
            )
            
            logger.info("✅ 第二数据源连接池初始化成功")
        
        return self.SecondarySessionLocal()
    
    def close(self):
        """关闭数据库连接池"""
        if self.readonly_engine:
            self.readonly_engine.dispose()
            logger.info("✅ 查询执行器连接池已关闭")
        
        if hasattr(self, 'secondary_engine') and self.secondary_engine:
            self.secondary_engine.dispose()
            logger.info("✅ 第二数据源连接池已关闭")


# 全局实例（可选）
_query_executor = None


def get_query_executor(audit_logger: Optional[AuditLogger] = None) -> QueryExecutor:
    """获取查询执行器实例"""
    global _query_executor
    
    if _query_executor is None:
        _query_executor = QueryExecutor(audit_logger)
    
    return _query_executor
