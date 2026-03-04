#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SQL 安全验证器

实现需求：
- Requirements 4.1: 验证 SQL 仅为 SELECT 类型
- Requirements 4.2: 拒绝 INSERT、UPDATE、DELETE、DROP、ALTER、CREATE、TRUNCATE 等修改操作
- Requirements 4.3: 验证所有表都在白名单中
- Requirements 4.4: 检查明细查询是否包含 LIMIT
- Requirements 4.5: 验证 LIMIT 值不超过 100
- Requirements 4.6: 检测分号分隔的多条 SQL
- Requirements 4.7: 检测笛卡尔积
- Requirements 4.10: 检测子查询嵌套深度
"""

import re
from typing import List, Dict, Any, Optional
from app.core.logger import logger


class ValidationResult:
    """验证结果"""
    
    def __init__(self, is_valid: bool, errors: List[str] = None):
        self.is_valid = is_valid
        self.errors = errors or []
    
    def __bool__(self):
        return self.is_valid
    
    def __repr__(self):
        if self.is_valid:
            return "ValidationResult(valid=True)"
        return f"ValidationResult(valid=False, errors={self.errors})"


class SecurityValidator:
    """SQL 安全验证器"""
    
    def __init__(self, table_whitelist: Optional[List[str]] = None):
        """
        初始化安全验证器
        
        Args:
            table_whitelist: 允许查询的表白名单
        """
        self.table_whitelist = table_whitelist or []
        
        # 危险关键词列表
        self.dangerous_keywords = [
            "INSERT", "UPDATE", "DELETE", "DROP", "ALTER",
            "CREATE", "TRUNCATE", "GRANT", "REVOKE", "EXEC",
            "EXECUTE", "CALL", "LOAD", "OUTFILE", "INFILE"
        ]
        
        # 聚合函数关键词
        self.aggregation_keywords = [
            "COUNT", "SUM", "AVG", "MAX", "MIN", "GROUP BY"
        ]
    
    def validate_sql(
        self, 
        sql: str, 
        user_permissions: Optional[List[str]] = None
    ) -> ValidationResult:
        """
        验证 SQL 语句的安全性
        
        Args:
            sql: SQL 语句
            user_permissions: 用户可访问的表列表
        
        Returns:
            ValidationResult: 验证结果
        """
        errors = []
        
        # 1. 检查是否为 SELECT 语句
        if not self._is_select_only(sql):
            errors.append("仅允许 SELECT 查询")
        
        # 2. 检查危险关键词
        if self._contains_dangerous_keywords(sql):
            errors.append("SQL 包含不允许的操作")
        
        # 3. 检查表白名单
        tables = self._extract_tables(sql)
        for table in tables:
            if self.table_whitelist and table not in self.table_whitelist:
                errors.append(f"表 {table} 不在白名单中")
            if user_permissions and table not in user_permissions:
                errors.append(f"用户无权访问表 {table}")
        
        # 4. 检查 LIMIT 子句（明细查询）
        if self._is_detail_query(sql):
            if not self._has_limit(sql):
                errors.append("明细查询必须包含 LIMIT 子句")
            else:
                limit_value = self._extract_limit_value(sql)
                if limit_value and limit_value > 100:
                    errors.append("LIMIT 值不能超过 100")
        
        # 5. 检查多条语句
        if self._has_multiple_statements(sql):
            errors.append("不允许执行多条 SQL 语句")
        
        # 6. 检查笛卡尔积
        if self._has_cartesian_product(sql):
            errors.append("检测到笛卡尔积，请添加 JOIN 条件")
        
        # 7. 检查子查询嵌套深度
        nesting_level = self._get_subquery_nesting_level(sql)
        if nesting_level > 3:
            errors.append(f"子查询嵌套层数 ({nesting_level}) 超过限制 (3)")
        
        return ValidationResult(is_valid=len(errors) == 0, errors=errors)
    
    def _is_select_only(self, sql: str) -> bool:
        """
        检查是否仅为 SELECT 语句
        
        Requirements 4.1: 验证 SQL 仅为 SELECT 类型
        """
        sql_upper = sql.strip().upper()
        return sql_upper.startswith("SELECT")
    
    def _contains_dangerous_keywords(self, sql: str) -> bool:
        """
        检查是否包含危险关键词
        
        Requirements 4.2: 拒绝 INSERT、UPDATE、DELETE、DROP 等操作
        """
        sql_upper = sql.upper()
        
        for keyword in self.dangerous_keywords:
            # 使用单词边界匹配，避免误判（如 "INSERTED_AT" 字段名）
            pattern = r'\b' + keyword + r'\b'
            if re.search(pattern, sql_upper):
                logger.warning(f"Dangerous keyword detected: {keyword}")
                return True
        
        return False
    
    def _extract_tables(self, sql: str) -> List[str]:
        """
        提取 SQL 中的表名
        
        简化实现：提取 FROM 和 JOIN 后的表名
        """
        tables = []
        sql_upper = sql.upper()
        
        # 提取 FROM 后的表名
        from_pattern = r'FROM\s+([a-zA-Z0-9_]+)'
        from_matches = re.findall(from_pattern, sql_upper)
        tables.extend(from_matches)
        
        # 提取 JOIN 后的表名
        join_pattern = r'JOIN\s+([a-zA-Z0-9_]+)'
        join_matches = re.findall(join_pattern, sql_upper)
        tables.extend(join_matches)
        
        # 去重并转换为小写
        tables = list(set([t.lower() for t in tables]))
        
        return tables
    
    def _is_detail_query(self, sql: str) -> bool:
        """
        检查是否为明细查询（非聚合查询）
        
        明细查询：不包含聚合函数的 SELECT 语句
        """
        sql_upper = sql.upper()
        
        for keyword in self.aggregation_keywords:
            if keyword in sql_upper:
                return False
        
        return True
    
    def _has_limit(self, sql: str) -> bool:
        """检查是否包含 LIMIT 子句"""
        sql_upper = sql.upper()
        return "LIMIT" in sql_upper
    
    def _extract_limit_value(self, sql: str) -> Optional[int]:
        """提取 LIMIT 值"""
        sql_upper = sql.upper()
        
        # 匹配 LIMIT 数字
        pattern = r'LIMIT\s+(\d+)'
        match = re.search(pattern, sql_upper)
        
        if match:
            return int(match.group(1))
        
        return None
    
    def _has_multiple_statements(self, sql: str) -> bool:
        """
        检查是否包含多条语句
        
        Requirements 4.6: 检测分号分隔的多条 SQL
        """
        # 简单检查：是否包含分号（排除字符串中的分号）
        # 移除字符串字面量
        sql_no_strings = re.sub(r"'[^']*'", "", sql)
        sql_no_strings = re.sub(r'"[^"]*"', "", sql_no_strings)
        
        # 检查是否有分号
        return ";" in sql_no_strings.strip().rstrip(";")
    
    def _has_cartesian_product(self, sql: str) -> bool:
        """
        检测笛卡尔积
        
        Requirements 4.7: 检测多表 JOIN 缺少 ON 条件
        """
        sql_upper = sql.upper()
        
        # 检查逗号分隔的多表（FROM table1, table2）
        from_clause = self._extract_from_clause(sql)
        if "," in from_clause and "WHERE" not in sql_upper:
            return True
        
        # 检查 JOIN 但缺少 ON 条件
        # 统计 JOIN 和 ON 的数量
        join_count = sql_upper.count("JOIN")
        on_count = sql_upper.count(" ON ")
        
        # 如果有 JOIN 但 ON 的数量少于 JOIN 的数量，说明有笛卡尔积
        if join_count > 0 and on_count < join_count:
            return True
        
        return False
    
    def _extract_from_clause(self, sql: str) -> str:
        """提取 FROM 子句"""
        sql_upper = sql.upper()
        
        # 移除子查询（括号内的内容）
        sql_no_subqueries = re.sub(r'\([^)]*\)', '', sql_upper)
        
        # 查找 FROM 到 WHERE/GROUP/ORDER/LIMIT 之间的内容
        pattern = r'FROM\s+(.*?)(?:WHERE|GROUP|ORDER|LIMIT|$)'
        match = re.search(pattern, sql_no_subqueries, re.DOTALL)
        
        if match:
            return match.group(1).strip()
        
        return ""
    
    def _get_subquery_nesting_level(self, sql: str) -> int:
        """
        计算子查询嵌套深度
        
        Requirements 4.10: 检测子查询嵌套超过 3 层
        """
        # 简化实现：统计 SELECT 关键词的嵌套层数
        max_depth = 0
        current_depth = 0
        
        # 移除字符串字面量
        sql_no_strings = re.sub(r"'[^']*'", "", sql)
        sql_no_strings = re.sub(r'"[^"]*"', "", sql_no_strings)
        
        i = 0
        while i < len(sql_no_strings):
            if sql_no_strings[i] == '(':
                current_depth += 1
                max_depth = max(max_depth, current_depth)
            elif sql_no_strings[i] == ')':
                current_depth -= 1
            i += 1
        
        # 如果有嵌套的 SELECT，深度至少为 1
        select_count = sql.upper().count("SELECT")
        if select_count > 1:
            return max(max_depth, select_count - 1)
        
        return 0


# 全局实例（可选）
_security_validator = None


def get_security_validator(table_whitelist: Optional[List[str]] = None) -> SecurityValidator:
    """获取安全验证器实例"""
    global _security_validator
    
    if _security_validator is None:
        _security_validator = SecurityValidator(table_whitelist)
    
    return _security_validator
