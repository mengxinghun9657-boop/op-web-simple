#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SQL 生成器（SQL Generator）

实现需求：
- Requirements 3.3: 调用 ERNIE API 生成 SQL
- Requirements 3.4: 提取 SQL 文本
- Requirements 3.6: 明细查询自动添加 LIMIT
- Requirements 3.7: 聚合查询不添加 LIMIT
- Requirements 3.9: Schema RAG 失败降级
"""

import re
from typing import Dict, List, Optional, Tuple

from app.core.logger import logger
from app.services.ai.ernie_client import ERNIEClient
from app.services.ai.schema_vector_store import SchemaVectorStore


class SQLGenerator:
    """SQL 生成器"""
    
    def __init__(
        self,
        ernie_client: Optional[ERNIEClient] = None,
        schema_vector_store: Optional[SchemaVectorStore] = None
    ):
        """
        初始化 SQL 生成器
        
        Args:
            ernie_client: ERNIE API 客户端
            schema_vector_store: Schema 向量存储
        """
        self.ernie_client = ernie_client or ERNIEClient()
        self.schema_vector_store = schema_vector_store or SchemaVectorStore()
        
        logger.info("✅ SQL 生成器初始化成功")
    
    async def generate_sql(
        self,
        query: str,
        user_permissions: Optional[List[str]] = None,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        生成 SQL 查询
        
        Args:
            query: 用户自然语言查询
            user_permissions: 用户有权访问的表列表
            metadata: 路由规则元数据（推荐的表、数据库等）
        
        Returns:
            SQL 生成结果字典
            {
                "sql": str,              # 生成的 SQL
                "tables": List[Dict],    # 使用的表结构
                "is_detail_query": bool, # 是否为明细查询
                "has_limit": bool        # 是否包含 LIMIT
            }
        
        Validates:
            - Requirements 3.3: 调用 ERNIE API 生成 SQL
            - Requirements 3.4: 提取 SQL 文本
            - Requirements 3.6: 明细查询自动添加 LIMIT
            - Requirements 3.7: 聚合查询不添加 LIMIT
            - Requirements 2.9, 11.5: 使用规则元数据优化表选择
        """
        logger.info(f"🔧 SQL 生成 - query: {query[:50]}...")
        
        try:
            # 1. Schema RAG: 检索相关表结构
            relevant_tables = await self._retrieve_schema(query, user_permissions, metadata)
            
            # 2. 构建 SQL 生成 Prompt
            prompt = self._build_sql_generation_prompt(query, relevant_tables)
            
            # 3. 调用 ERNIE API 生成 SQL
            response = await self.ernie_client.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1  # 低温度，更确定的结果
            )
            
            # 4. 提取 SQL 文本
            sql = self._extract_sql_from_response(response)
            
            # 5. 检查是否为明细查询
            is_detail_query = self._is_detail_query(sql)
            
            # 6. 自动添加 LIMIT（明细查询）
            has_limit = self._has_limit(sql)
            if is_detail_query and not has_limit:
                sql = self._add_limit_clause(sql, limit=100)
                has_limit = True
                logger.info("✅ 明细查询自动添加 LIMIT 100")
            
            result = {
                "sql": sql,
                "tables": relevant_tables,
                "is_detail_query": is_detail_query,
                "has_limit": has_limit
            }
            
            logger.info(f"✅ SQL 生成完成: {sql[:100]}...")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ SQL 生成失败: {e}")
            raise
    
    async def _retrieve_schema(
        self,
        query: str,
        user_permissions: Optional[List[str]] = None,
        metadata: Optional[Dict] = None
    ) -> List[Dict]:
        """
        检索相关表结构
        
        Args:
            query: 用户查询
            user_permissions: 用户权限
            metadata: 路由规则元数据（推荐的表、数据库等）
        
        Returns:
            相关表结构列表
        
        Validates: Requirements 3.9, 11.5, 11.6, 11.8
        """
        try:
            # 1. 提取查询中提到的字段名
            mentioned_fields = self._extract_field_names(query)
            logger.info(f"🔍 查询中提到的字段: {mentioned_fields}")
            
            # 2. 如果 metadata 包含推荐的表，优先使用
            if metadata and "recommended_tables" in metadata:
                recommended_tables = metadata["recommended_tables"]
                logger.info(f"📋 使用规则推荐的表: {recommended_tables}")
                
                # 从 Schema RAG 获取这些表的详细信息
                tables = []
                for table_name in recommended_tables:
                    table_info = self.schema_vector_store.get_table_by_name(table_name)
                    if table_info:
                        # 确保表信息包含 table_name 字段
                        table_info_copy = table_info.copy()
                        table_info_copy["table_name"] = table_name
                        tables.append(table_info_copy)
                
                # 如果推荐的表都找到了，进行字段验证
                if tables:
                    # 字段验证：检查表是否包含查询中的字段
                    validated_tables = self._validate_table_fields(tables, mentioned_fields)
                    
                    if validated_tables:
                        # 按 table_priority 排序（如果有）
                        if metadata and "table_priority" in metadata:
                            table_priority = metadata["table_priority"]
                            validated_tables.sort(key=lambda t: table_priority.get(t["table_name"], 0), reverse=True)
                            logger.info(f"✅ 按优先级排序表: {[t['table_name'] for t in validated_tables]}")
                        
                        return validated_tables
                    else:
                        logger.warning(f"⚠️ 推荐的表都不包含查询字段 {mentioned_fields}，使用 Schema RAG 检索")
            
            # 3. 使用 Schema RAG 检索
            tables = await self.schema_vector_store.search(
                query=query,
                top_k=10,  # 多检索一些，用于字段验证
                filter_tables=user_permissions
            )
            
            # 4. 字段验证：过滤不包含查询字段的表
            if mentioned_fields:
                validated_tables = self._validate_table_fields(tables, mentioned_fields)
                if validated_tables:
                    tables = validated_tables
                    logger.info(f"✅ 字段验证后保留 {len(tables)} 个表")
                else:
                    logger.warning(f"⚠️ 没有表包含所有查询字段 {mentioned_fields}，保留原始结果")
            
            # 5. 如果 metadata 包含 table_priority，合并并排序
            if metadata and "table_priority" in metadata and tables:
                table_priority = metadata["table_priority"]
                
                # 为每个表添加优先级分数
                for table in tables:
                    table_name = table.get("table_name", "")
                    table["priority_score"] = table_priority.get(table_name, 0)
                
                # 按优先级排序
                tables.sort(key=lambda t: t.get("priority_score", 0), reverse=True)
                logger.info(f"✅ 合并 Schema RAG 和规则优先级: {[t['table_name'] for t in tables]}")
            
            # 6. 限制返回数量
            # 但要确保 CMDB 表（iaas_servers, iaas_instances, iaas_clusters）排在前面
            cmdb_tables = []
            other_tables = []
            
            for table in tables[:10]:  # 只处理前10个
                table_name = table.get("table_name", "")
                # 提取纯表名（去除数据库前缀）
                pure_name = table_name.split(".")[-1] if "." in table_name else table_name
                
                # CMDB 表优先
                if pure_name in ['iaas_servers', 'iaas_instances', 'iaas_clusters']:
                    cmdb_tables.append(table)
                else:
                    other_tables.append(table)
            
            # CMDB 表排在前面
            final_tables = cmdb_tables + other_tables
            
            # 限制返回数量为 5
            final_tables = final_tables[:5]
            
            if cmdb_tables:
                logger.info(f"✅ CMDB 表优先: {[t['table_name'] for t in cmdb_tables]}")
            
            return final_tables
            tables = tables[:5]
            
            if not tables:
                logger.warning("⚠️ Schema RAG 未返回结果，使用降级策略")
                # 降级：返回常用表
                tables = self.schema_vector_store._get_common_tables(
                    filter_tables=user_permissions,
                    limit=10
                )
            
            return tables
            
        except Exception as e:
            logger.error(f"❌ Schema RAG 失败: {e}")
            # 降级：返回常用表
            return self.schema_vector_store._get_common_tables(
                filter_tables=user_permissions,
                limit=10
            )
    
    def _build_sql_generation_prompt(
        self,
        query: str,
        relevant_tables: List[Dict]
    ) -> str:
        """
        构建 SQL 生成 Prompt（支持多数据源）
        
        Args:
            query: 用户查询
            relevant_tables: 相关表结构
        
        Returns:
            Prompt 文本
        """
        # 构建 Schema 上下文
        schema_context = self._format_schema_context(relevant_tables)
        
        # 检查是否包含第二数据源的表
        has_secondary = any(t.get("source") == "secondary" for t in relevant_tables)
        
        datasource_note = ""
        if has_secondary:
            datasource_note = """
注意：数据源说明
- 主数据库表：直接使用表名（如 `iaas_servers`）
- 宿主机数据库表：使用 mydb.表名 格式（如 `mydb.users`）
"""
        
        prompt = f"""你是一个 SQL 专家。请根据用户的自然语言查询生成 MySQL SELECT 语句。

数据库 Schema（仅相关表）：
{schema_context}
{datasource_note}
用户查询：{query}

⚠️ 表选择优先级规则（重要）：
1. **CMDB 表优先**：涉及物理机、虚机、宿主机、集群、IP地址、SN、加黑等基础设施信息时，优先使用 CMDB 表
   - iaas_servers（物理机/宿主机信息）
   - iaas_instances（虚拟机实例信息）
   - iaas_clusters（集群信息）
2. **监控数据表**：仅在查询监控指标、性能数据时使用 mydb.bce_* 表
3. **业务数据表**：查询任务、用户、审计日志等业务数据时使用对应的业务表

要求：
1. 仅生成 SELECT 语句
2. 仅使用提供的表和字段
3. 明细查询不需要添加 LIMIT（系统会自动添加）
4. 聚合查询（COUNT/SUM/AVG/MAX/MIN/GROUP BY）不添加 LIMIT
5. 返回纯 SQL，不要包含解释文本
6. 使用标准 MySQL 语法
7. 字段名和表名使用反引号包裹（如 `table_name`.`column_name`）
8. 如果表名包含数据库前缀（如 mydb.users），保留完整格式（如 `mydb`.`users`）

SQL:
"""
        
        return prompt
    
    def _format_schema_context(self, tables: List[Dict]) -> str:
        """
        格式化 Schema 上下文（支持多数据源）
        
        Args:
            tables: 表结构列表
        
        Returns:
            格式化的 Schema 文本
        """
        if not tables:
            return "（无可用表结构）"
        
        schema_parts = []
        
        for table in tables:
            table_name = table.get("table_name", "unknown")
            columns = table.get("columns", [])
            description = table.get("description", "")
            source = table.get("source", "primary")
            
            # 数据源标识
            source_label = "【主数据库】" if source == "primary" else "【宿主机数据库】"
            
            # 表信息
            table_part = [f"{source_label} 表名: {table_name}"]
            
            # 字段信息
            if columns:
                columns_info = []
                for col in columns:
                    col_info = f"  - {col['name']} ({col['type']})"
                    
                    # 添加约束信息
                    constraints = []
                    if col.get("key") == "PRI":
                        constraints.append("主键")
                    if col.get("null") == "NO":
                        constraints.append("非空")
                    
                    if constraints:
                        col_info += f" [{', '.join(constraints)}]"
                    
                    columns_info.append(col_info)
                
                table_part.append("字段:")
                table_part.extend(columns_info)
            
            # 添加描述（如果有）
            if description:
                table_part.append(f"说明: {description}")
            
            schema_parts.append("\n".join(table_part))
        
        return "\n\n".join(schema_parts)
    
    def _extract_field_names(self, query: str) -> List[str]:
        """
        从查询中提取可能的字段名
        
        Args:
            query: 用户查询
        
        Returns:
            提取的字段名列表
        
        Validates: Requirements 11.8
        """
        # 常见字段关键词映射
        field_keywords = {
            "IP": ["ip", "ip_address", "ipv4", "host_ip"],
            "IP地址": ["ip", "ip_address", "ipv4", "host_ip"],
            "状态": ["status", "state"],
            "加黑": ["is_blacklisted", "blacklist", "blacklisted"],
            "SN": ["sn", "serial_number"],
            "序列号": ["sn", "serial_number"],
            "集群": ["cluster", "cluster_name", "cluster_id"],
            "实例": ["instance", "instance_id", "instance_name"],
            "宿主机": ["host", "host_name", "host_id", "server_name"],
            "物理机": ["server", "server_name", "server_id", "host_name"],
            "虚拟机": ["instance", "instance_id", "vm_id"],
            "名称": ["name"],
            "ID": ["id"],
            "创建时间": ["created_at", "create_time"],
            "更新时间": ["updated_at", "update_time"],
        }
        
        mentioned_fields = []
        query_lower = query.lower()
        
        # 遍历关键词映射
        for keyword, fields in field_keywords.items():
            if keyword.lower() in query_lower or keyword in query:
                mentioned_fields.extend(fields)
        
        # 去重
        mentioned_fields = list(set(mentioned_fields))
        
        return mentioned_fields
    
    def _validate_table_fields(
        self,
        tables: List[Dict],
        mentioned_fields: List[str]
    ) -> List[Dict]:
        """
        验证表是否包含查询中提到的字段
        
        Args:
            tables: 候选表列表
            mentioned_fields: 查询中提到的字段名
        
        Returns:
            包含查询字段的表列表（按匹配度排序）
        
        Validates: Requirements 11.8
        """
        if not mentioned_fields:
            return tables
        
        validated_tables = []
        
        for table in tables:
            table_name = table.get("table_name", "")
            columns = table.get("columns", [])
            
            # 提取表的所有字段名（小写）
            table_fields = [col["name"].lower() for col in columns]
            
            # 计算匹配的字段数量
            matched_count = 0
            matched_fields = []
            
            for field in mentioned_fields:
                if field.lower() in table_fields:
                    matched_count += 1
                    matched_fields.append(field)
            
            # 如果至少匹配一个字段，保留该表
            if matched_count > 0:
                table_copy = table.copy()
                table_copy["field_match_count"] = matched_count
                table_copy["matched_fields"] = matched_fields
                validated_tables.append(table_copy)
                logger.info(f"✅ 表 {table_name} 匹配 {matched_count} 个字段: {matched_fields}")
            else:
                logger.debug(f"⚠️ 表 {table_name} 不包含查询字段 {mentioned_fields}")
        
        # 按匹配字段数量排序（降序）
        validated_tables.sort(key=lambda t: t.get("field_match_count", 0), reverse=True)
        
        return validated_tables
    
    def _extract_sql_from_response(self, response: str) -> str:
        """
        从 ERNIE 响应中提取 SQL
        
        Args:
            response: ERNIE API 响应
        
        Returns:
            提取的 SQL 文本
        
        Validates: Requirements 3.4
        """
        # 尝试提取 SQL 代码块
        sql_pattern = r"```sql\s*(.*?)\s*```"
        match = re.search(sql_pattern, response, re.DOTALL | re.IGNORECASE)
        
        if match:
            sql = match.group(1).strip()
            logger.debug(f"✅ 从代码块提取 SQL: {sql[:50]}...")
            return sql
        
        # 尝试提取 SELECT 语句
        select_pattern = r"(SELECT\s+.*?;?)\s*$"
        match = re.search(select_pattern, response, re.DOTALL | re.IGNORECASE)
        
        if match:
            sql = match.group(1).strip()
            # 移除末尾的分号（如果有）
            if sql.endswith(";"):
                sql = sql[:-1]
            logger.debug(f"✅ 从文本提取 SQL: {sql[:50]}...")
            return sql
        
        # 如果都失败，返回整个响应（去除多余空白）
        sql = response.strip()
        logger.warning(f"⚠️ 无法识别 SQL 格式，返回原始响应: {sql[:50]}...")
        return sql
    
    def _is_detail_query(self, sql: str) -> bool:
        """
        检查是否为明细查询（非聚合查询）
        
        Args:
            sql: SQL 语句
        
        Returns:
            是否为明细查询
        
        Validates: Requirements 3.6, 3.7
        """
        sql_upper = sql.upper()
        
        # 聚合函数关键词
        aggregation_keywords = [
            "COUNT(",
            "SUM(",
            "AVG(",
            "MAX(",
            "MIN(",
            "GROUP BY"
        ]
        
        # 检查是否包含聚合关键词
        has_aggregation = any(kw in sql_upper for kw in aggregation_keywords)
        
        # 明细查询 = 不包含聚合关键词
        is_detail = not has_aggregation
        
        logger.debug(f"📊 查询类型: {'明细查询' if is_detail else '聚合查询'}")
        
        return is_detail
    
    def _has_limit(self, sql: str) -> bool:
        """
        检查 SQL 是否包含 LIMIT 子句
        
        Args:
            sql: SQL 语句
        
        Returns:
            是否包含 LIMIT
        """
        sql_upper = sql.upper()
        return "LIMIT" in sql_upper
    
    def _add_limit_clause(self, sql: str, limit: int = 100) -> str:
        """
        为 SQL 添加 LIMIT 子句
        
        Args:
            sql: SQL 语句
            limit: LIMIT 值
        
        Returns:
            添加 LIMIT 后的 SQL
        
        Validates: Requirements 3.6
        """
        # 移除末尾的分号（如果有）
        sql = sql.rstrip(";").strip()
        
        # 添加 LIMIT
        sql_with_limit = f"{sql} LIMIT {limit}"
        
        logger.debug(f"✅ 添加 LIMIT {limit}")
        
        return sql_with_limit
    
    def format_sql(self, sql: str) -> str:
        """
        格式化 SQL（美化）
        
        Args:
            sql: SQL 语句
        
        Returns:
            格式化后的 SQL
        """
        # 简单的格式化：添加换行和缩进
        sql = sql.strip()
        
        # 在关键词前添加换行
        keywords = ["SELECT", "FROM", "WHERE", "GROUP BY", "ORDER BY", "LIMIT"]
        for keyword in keywords:
            sql = re.sub(
                rf"\s+{keyword}\s+",
                f"\n{keyword} ",
                sql,
                flags=re.IGNORECASE
            )
        
        return sql.strip()


# 全局实例（可选）
_sql_generator = None


def get_sql_generator(
    ernie_client: Optional[ERNIEClient] = None,
    schema_vector_store: Optional[SchemaVectorStore] = None
) -> SQLGenerator:
    """获取 SQL 生成器实例"""
    global _sql_generator
    
    if _sql_generator is None:
        _sql_generator = SQLGenerator(ernie_client, schema_vector_store)
    
    return _sql_generator
