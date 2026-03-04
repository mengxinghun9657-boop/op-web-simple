#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Schema 向量存储管理器（Schema Vector Store）

实现需求：
- Requirements 3.1: 向量化数据库 Schema 信息
- Requirements 3.2: 检索最相关的 Top-5 表
- Requirements 9.1: 加载数据库 Schema 信息
- Requirements 9.3: 提供手动刷新 Schema 的接口
"""

import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from app.core.logger import logger
from app.core.database import get_db
from app.services.ai.embedding_model import EmbeddingModel
from app.services.ai.vector_store import VectorStore


class SchemaVectorStore:
    """Schema 向量存储管理器"""
    
    def __init__(
        self,
        embedding_model: Optional[EmbeddingModel] = None,
        vector_store: Optional[VectorStore] = None,
        vector_store_path: str = "/app/vector_store/schema"
    ):
        """
        初始化 Schema 向量存储管理器
        
        Args:
            embedding_model: Embedding 模型
            vector_store: 向量存储
            vector_store_path: 向量存储路径
        """
        self.embedding_model = embedding_model or EmbeddingModel()
        self.vector_store = vector_store or VectorStore(
            index_path=vector_store_path
        )
        
        # Schema 缓存
        self.schema_cache: Dict[str, Dict] = {}
        self.last_refresh_time: Optional[datetime] = None
        
        logger.info("✅ Schema 向量存储管理器初始化成功")
    
    async def load_schema(self, force_refresh: bool = False, include_secondary: bool = True) -> int:
        """
        加载数据库 Schema 信息（支持多数据源）
        
        Args:
            force_refresh: 是否强制刷新
            include_secondary: 是否包含第二数据源（宿主机数据库）
        
        Returns:
            加载的表数量
        
        Validates: Requirements 9.1
        """
        # 如果已经加载且不强制刷新，直接返回
        if self.schema_cache and not force_refresh:
            logger.info(f"📦 使用缓存的 Schema 信息: {len(self.schema_cache)} 个表")
            return len(self.schema_cache)
        
        logger.info("🔄 开始加载数据库 Schema 信息...")
        
        # 🆕 预检查：Embedding API 是否可用（快速失败）
        logger.info("🔍 检查 Embedding API 可用性...")
        is_embedding_available = await self.embedding_model.quick_health_check(timeout=2.0)
        
        if not is_embedding_available:
            logger.warning("⚠️ Embedding API 不可用，跳过 Schema 向量化")
            logger.info("💡 这在外网环境是正常的，内网部署后会自动启用")
            logger.info("💡 SQL 生成将使用降级策略（常用表列表）")
            return 0  # 直接返回，不执行后续的表加载和向量化
        
        logger.info("✅ Embedding API 可用，继续加载 Schema...")
        
        total_tables = 0
        
        # 1. 加载主数据库（容器内的 cluster_management）
        db = None
        try:
            logger.info("📊 加载主数据库 Schema...")
            # 使用同步数据库连接
            from app.core.database import get_db_sync
            import time
            
            # 添加连接重试逻辑
            max_conn_retries = 3
            for conn_attempt in range(1, max_conn_retries + 1):
                try:
                    db = next(get_db_sync(use_secondary=False))
                    # 测试连接
                    from sqlalchemy import text
                    db.execute(text("SELECT 1"))
                    logger.info(f"✅ 数据库连接成功 (attempt {conn_attempt}/{max_conn_retries})")
                    break
                except Exception as conn_e:
                    logger.warning(f"⚠️ 数据库连接失败 (attempt {conn_attempt}/{max_conn_retries}): {conn_e}")
                    if conn_attempt < max_conn_retries:
                        time.sleep(5)
                    else:
                        raise
            
            tables_schema = self._fetch_tables_schema(db, source="primary")
            
            if not tables_schema:
                logger.error("❌ 主数据库没有找到任何表！")
                raise RuntimeError("主数据库没有找到任何表")
            
            # 为每个表生成描述文本并向量化
            indexed_count = 0
            for table_name, table_info in tables_schema.items():
                try:
                    await self._index_table_schema(table_name, table_info, source="primary")
                    indexed_count += 1
                except Exception as index_e:
                    logger.error(f"❌ 索引表 {table_name} 失败: {index_e}")
                    # 继续处理其他表
                    continue
            
            total_tables += indexed_count
            logger.info(f"✅ 主数据库 Schema 加载完成: {indexed_count}/{len(tables_schema)} 个表成功索引")
            
            if indexed_count == 0:
                raise RuntimeError("主数据库所有表索引失败")
            
        except Exception as e:
            logger.error(f"❌ 加载主数据库 Schema 失败: {e}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")
            raise
        finally:
            if db is not None:
                try:
                    db.close()
                except Exception as e:
                    logger.warning(f"⚠️ 关闭主数据库连接失败: {e}")
        
        # 2. 加载第二数据库（宿主机的所有数据库）
        if include_secondary:
            try:
                logger.info("📊 加载宿主机数据库 Schema...")
                from app.core.config import settings
                from sqlalchemy import create_engine, text
                from sqlalchemy.orm import sessionmaker
                
                # 宿主机数据库列表（根据 host_field_mapping.py）
                host_databases = ["mydb", "bcc_monitor", "bos_monitoring", "gpu_monitoring", "gpu_stats", "h20_l20_gpu_monitoring"]
                
                for db_name in host_databases:
                    db2 = None
                    try:
                        logger.info(f"📊 加载宿主机数据库: {db_name}...")
                        
                        # 为每个数据库创建独立连接
                        db_url = f"mysql+pymysql://{settings.MYSQL_USER_2}:{settings.MYSQL_PASSWORD_2}@{settings.MYSQL_HOST_2}:{getattr(settings, 'MYSQL_PORT_2', 3306)}/{db_name}?charset=utf8mb4"
                        engine_2 = create_engine(db_url, pool_pre_ping=True)
                        SessionLocal2 = sessionmaker(autocommit=False, autoflush=False, bind=engine_2)
                        db2 = SessionLocal2()
                        
                        # 获取表结构
                        tables_schema_2 = self._fetch_tables_schema(db2, source="secondary")
                        
                        # 为每个表生成描述文本并向量化
                        for table_name, table_info in tables_schema_2.items():
                            # 添加数据库前缀
                            prefixed_table_name = f"{db_name}.{table_name}"
                            await self._index_table_schema(prefixed_table_name, table_info, source="secondary", original_name=table_name)
                        
                        total_tables += len(tables_schema_2)
                        logger.info(f"✅ 宿主机数据库 {db_name} Schema 加载完成: {len(tables_schema_2)} 个表")
                        
                    except Exception as e:
                        logger.warning(f"⚠️ 加载宿主机数据库 {db_name} 失败: {e}")
                    finally:
                        if db2 is not None:
                            try:
                                db2.close()
                                engine_2.dispose()
                            except Exception as e:
                                logger.warning(f"⚠️ 关闭宿主机数据库 {db_name} 连接失败: {e}")
                
            except Exception as e:
                logger.warning(f"⚠️ 加载宿主机数据库 Schema 失败（非致命错误）: {e}")
                logger.info("💡 提示: 如果不需要宿主机数据源，可以忽略此警告")
        
        # 保存向量存储
        try:
            self.vector_store.save()
            logger.info(f"💾 向量存储已保存到磁盘")
            
            # 验证向量存储
            health = self.vector_store.health_check()
            logger.info(f"📊 向量存储健康检查: {health}")
            
            if health.get("total_vectors", 0) == 0:
                logger.error("❌ 警告：向量存储为空！Schema 索引可能失败")
            
        except Exception as e:
            logger.error(f"❌ 保存向量存储失败: {e}")
        
        self.last_refresh_time = datetime.now()
        
        logger.info(f"✅ Schema 加载完成: 共 {total_tables} 个表（主库 + 宿主机库）")
        return total_tables
    
    async def _index_table_schema(self, table_name: str, table_info: Dict, source: str, original_name: str = None) -> None:
        """
        索引单个表的 Schema 信息
        
        Args:
            table_name: 表名（可能带前缀，如 mydb.users）
            table_info: 表信息
            source: 数据源标识（primary/secondary）
            original_name: 原始表名（不带前缀）
        """
        try:
            description = self._generate_table_description(table_name, table_info, source)
            table_info["description"] = description
            table_info["source"] = source
            if original_name:
                table_info["original_name"] = original_name
            
            # 向量化表描述
            embedding = await self.embedding_model.encode(description)
            
            # 检查 embedding 是否有效
            if embedding is None or len(embedding) == 0:
                logger.error(f"❌ 表 {table_name} 的 embedding 为空，跳过索引")
                return
            
            # 存储到向量数据库
            vector_id = f"schema_{table_name}"
            self.vector_store.add(
                entry_id=hash(vector_id),  # 使用哈希值作为 entry_id
                embedding=embedding,
                metadata={
                    "table_name": table_name,
                    "original_name": original_name or table_name,
                    "source": source,
                    "type": "schema",
                    "columns": table_info["columns"],
                    "description": description,
                    "indexed_at": datetime.now().isoformat()
                }
            )
            
            # 缓存 Schema 信息
            self.schema_cache[table_name] = table_info
            
            logger.debug(f"✅ 表 {table_name} 索引成功")
            
        except Exception as e:
            logger.error(f"❌ 索引表 {table_name} 失败: {e}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")
    
    def _fetch_tables_schema(self, db, source: str = "primary") -> Dict[str, Dict]:
        """
        从数据库获取表结构信息
        
        Args:
            db: 数据库连接
            source: 数据源标识（primary/secondary）
        
        Returns:
            表结构字典 {table_name: {columns: [...], ...}}
        """
        from sqlalchemy import text
        
        tables_schema = {}
        
        # 获取所有表名（SQLAlchemy 2.0 要求显式声明文本 SQL）
        result = db.execute(text("SHOW TABLES"))
        tables = [row[0] for row in result.fetchall()]
        
        logger.info(f"📋 发现 {len(tables)} 个表")
        
        # 获取每个表的列信息
        for table_name in tables:
            try:
                # 验证表名（防止 SQL 注入）
                # 表名只能包含字母、数字、下划线
                import re
                if not re.match(r'^[a-zA-Z0-9_]+$', table_name):
                    logger.warning(f"⚠️ 跳过无效表名: {table_name}")
                    continue
                
                # 获取列信息（使用反引号包裹表名，SQLAlchemy 2.0 要求显式声明文本 SQL）
                result = db.execute(text(f"DESCRIBE `{table_name}`"))
                columns = []
                
                for row in result.fetchall():
                    column_info = {
                        "name": row[0],
                        "type": row[1],
                        "null": row[2],
                        "key": row[3],
                        "default": row[4],
                        "extra": row[5]
                    }
                    columns.append(column_info)
                
                tables_schema[table_name] = {
                    "columns": columns,
                    "column_count": len(columns)
                }
                
            except Exception as e:
                logger.warning(f"⚠️ 获取表 {table_name} 的结构失败: {e}")
                continue
        
        return tables_schema
    
    def _generate_table_description(self, table_name: str, table_info: Dict, source: str = "primary") -> str:
        """
        生成表的描述文本（增强版：支持字段映射）
        
        Args:
            table_name: 表名
            table_info: 表信息
            source: 数据源标识
        
        Returns:
            表描述文本
        """
        # 导入字段映射配置
        try:
            from app.config.host_field_mapping import HOST_FIELD_MAPPING
        except ImportError:
            HOST_FIELD_MAPPING = {}
        
        # 构建表描述
        source_label = "主数据库" if source == "primary" else "宿主机数据库"
        
        # 提取纯表名（去除数据库前缀）
        pure_table_name = table_name.split(".")[-1] if "." in table_name else table_name
        
        description_parts = [
            f"数据源: {source_label}",
            f"表名: {table_name}",
            f"字段数量: {table_info['column_count']}"
        ]
        
        # 获取字段映射
        field_mapping = HOST_FIELD_MAPPING.get(pure_table_name, {})
        table_purpose = field_mapping.get("table_purpose", "")
        
        # 添加表用途说明
        if table_purpose:
            description_parts.append(f"用途: {table_purpose}")
        else:
            # 如果没有映射，使用推断
            purpose = self._infer_table_purpose(table_name)
            if purpose:
                description_parts.append(f"用途: {purpose}")
        
        # 添加字段信息（增强版：使用字段映射）
        columns_desc = []
        for col in table_info["columns"]:
            col_name = col['name']
            col_type = col['type']
            
            # 获取字段的中文描述
            if col_name in field_mapping:
                # 使用字段映射
                col_desc = f"{col_name} - {field_mapping[col_name]} ({col_type})"
            elif col.get("comment"):
                # 使用数据库注释
                col_desc = f"{col_name} - {col['comment']} ({col_type})"
            else:
                # 只显示字段名和类型
                col_desc = f"{col_name} ({col_type})"
            
            # 添加主键标记
            if col["key"] == "PRI":
                col_desc += " [主键]"
            elif col["key"] == "UNI":
                col_desc += " [唯一]"
            elif col["key"] == "MUL":
                col_desc += " [索引]"
            
            # 添加非空标记
            if col["null"] == "NO":
                col_desc += " [非空]"
            
            columns_desc.append(col_desc)
        
        description_parts.append("字段列表:")
        description_parts.extend([f"  - {desc}" for desc in columns_desc])
        
        return "\n".join(description_parts)
    
    def _infer_table_purpose(self, table_name: str) -> Optional[str]:
        """
        根据表名推断表的用途
        
        Args:
            table_name: 表名
        
        Returns:
            表用途说明
        """
        # 常见表名模式
        patterns = {
            "user": "用户信息管理",
            "task": "任务管理",
            "audit": "审计日志",
            "knowledge": "知识库",
            "report": "报告索引",
            "cluster": "集群信息",
            "server": "服务器信息",
            "instance": "实例信息",
            "monitoring": "监控数据",
            "resource": "资源信息",
            "operational": "运营数据"
        }
        
        table_lower = table_name.lower()
        for keyword, purpose in patterns.items():
            if keyword in table_lower:
                return purpose
        
        return None
    
    async def search(
        self,
        query: str,
        top_k: int = 5,
        filter_tables: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        检索最相关的表结构
        
        Args:
            query: 用户查询文本
            top_k: 返回的表数量（默认 5）
            filter_tables: 用户有权访问的表列表（白名单）
        
        Returns:
            相关表结构列表
        
        Validates: Requirements 3.1, 3.2
        """
        logger.info(f"🔍 Schema RAG 检索 - query: {query[:50]}..., top_k: {top_k}")
        
        try:
            # 检查向量存储是否为空
            health = self.vector_store.health_check()
            total_vectors = health.get("total_vectors", 0)
            logger.info(f"📊 当前向量存储状态: {total_vectors} 个向量")
            
            if total_vectors == 0:
                logger.warning("⚠️ 向量存储为空，返回空结果")
                return []
            
            # 🆕 如果 schema_cache 为空但向量存储有数据，从 metadata 恢复缓存
            if not self.schema_cache and total_vectors > 0:
                logger.warning("⚠️ Schema 缓存为空但向量存储有数据，尝试从 metadata 恢复缓存")
                self._rebuild_cache_from_metadata()
                logger.info(f"✅ 从 metadata 恢复了 {len(self.schema_cache)} 个表的缓存")
            
            # 向量化查询
            query_embedding = await self.embedding_model.encode(query)
            
            if query_embedding is None or len(query_embedding) == 0:
                logger.error("❌ 查询向量化失败，返回空结果")
                return []
            
            # 向量检索
            results = self.vector_store.search(
                query_embedding,
                top_k=top_k * 2,  # 多检索一些，用于过滤
                similarity_threshold=0.3  # 相似度阈值
            )
            
            logger.info(f"🔍 向量检索返回 {len(results)} 个结果")
            
            # 过滤和排序
            filtered_results = []
            for result in results:
                table_name = result["metadata"]["table_name"]
                
                # 权限过滤
                if filter_tables and table_name not in filter_tables:
                    logger.debug(f"⚠️ 表 {table_name} 不在用户权限列表中，跳过")
                    continue
                
                # 从缓存获取完整 Schema 信息
                if table_name in self.schema_cache:
                    table_info = self.schema_cache[table_name].copy()
                    table_info["similarity"] = result["similarity"]
                    filtered_results.append(table_info)
                
                # 达到 top_k 数量后停止
                if len(filtered_results) >= top_k:
                    break
            
            logger.info(f"✅ Schema RAG 检索完成: 返回 {len(filtered_results)} 个表")
            
            return filtered_results
            
        except Exception as e:
            logger.error(f"❌ Schema RAG 检索失败: {e}")
            # 降级：返回常用表
            return self._get_common_tables(filter_tables, top_k)
    
    def _rebuild_cache_from_metadata(self) -> None:
        """
        从向量存储的 metadata 重建 schema_cache
        
        当服务启动时 Schema 加载失败，但向量存储中有历史数据时使用
        """
        try:
            logger.info("🔄 开始从 metadata 重建 Schema 缓存...")
            
            # 遍历向量存储的所有 metadata
            for entry_id, metadata in self.vector_store.metadata.items():
                if metadata.get("type") != "schema":
                    continue
                
                table_name = metadata.get("table_name")
                if not table_name:
                    continue
                
                # 重建表信息
                table_info = {
                    "columns": metadata.get("columns", []),
                    "column_count": len(metadata.get("columns", [])),
                    "description": metadata.get("description", ""),
                    "source": metadata.get("source", "unknown"),
                    "indexed_at": metadata.get("indexed_at", "")
                }
                
                # 如果有 original_name，也保存
                if "original_name" in metadata:
                    table_info["original_name"] = metadata["original_name"]
                
                self.schema_cache[table_name] = table_info
            
            logger.info(f"✅ Schema 缓存重建完成: {len(self.schema_cache)} 个表")
            
        except Exception as e:
            logger.error(f"❌ 重建 Schema 缓存失败: {e}")
    
    def _get_common_tables(
        self,
        filter_tables: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[Dict]:
        """
        获取常用表（降级策略）
        
        Args:
            filter_tables: 用户有权访问的表列表
            limit: 返回的表数量
        
        Returns:
            常用表列表
        
        Validates: Requirements 3.9
        """
        logger.warning("⚠️ Schema RAG 失败，使用常用表降级策略")
        
        # 常用表列表（按使用频率排序）
        # ⚠️ 注意：必须使用实际的数据库表名
        common_tables = [
            "users",
            "tasks",
            "iaas_servers",         # 物理机表（IaaS 服务器）
            "iaas_instances",       # 虚拟机实例表
            "iaas_clusters",        # 集群表
            "has_alerts",           # HAS 告警表
            "audit_logs",           # 审计日志
            "knowledge_entries",    # 知识条目
            "report_index",         # 报告索引
            "chat_history"          # 聊天历史
        ]
        
        # 过滤和返回
        result = []
        for table_name in common_tables:
            if filter_tables and table_name not in filter_tables:
                continue
            
            if table_name in self.schema_cache:
                result.append(self.schema_cache[table_name])
            
            if len(result) >= limit:
                break
        
        return result
    
    async def refresh_schema(self) -> int:
        """
        手动刷新 Schema
        
        Returns:
            刷新的表数量
        
        Validates: Requirements 9.3
        """
        logger.info("🔄 手动刷新 Schema...")
        return await self.load_schema(force_refresh=True)
    
    def get_table_info(self, table_name: str) -> Optional[Dict]:
        """
        获取单个表的 Schema 信息
        
        Args:
            table_name: 表名
        
        Returns:
            表 Schema 信息
        """
        return self.schema_cache.get(table_name)
    
    def get_all_tables(self) -> List[str]:
        """
        获取所有表名
        
        Returns:
            表名列表
        """
        return list(self.schema_cache.keys())
    
    def get_table_by_name(self, table_name: str) -> Optional[Dict]:
        """
        根据表名获取表的完整 Schema 信息
        
        支持以下格式：
        - 纯表名：users
        - 带数据库前缀：mydb.users
        
        Args:
            table_name: 表名（可能带数据库前缀）
        
        Returns:
            表 Schema 信息，如果找不到返回 None
        
        Validates: Requirements 11.5, 11.6
        """
        # 1. 直接查找（精确匹配）
        if table_name in self.schema_cache:
            logger.debug(f"✅ 找到表: {table_name}")
            return self.schema_cache[table_name]
        
        # 2. 如果表名不带前缀，尝试在所有数据库中查找
        if "." not in table_name:
            # 遍历所有缓存的表，查找匹配的纯表名
            for cached_table_name, table_info in self.schema_cache.items():
                # 提取纯表名（去除数据库前缀）
                pure_name = cached_table_name.split(".")[-1]
                if pure_name == table_name:
                    logger.debug(f"✅ 找到表: {cached_table_name} (匹配纯表名: {table_name})")
                    return table_info
            
            # 如果还是找不到，尝试使用 original_name 字段
            for cached_table_name, table_info in self.schema_cache.items():
                if table_info.get("original_name") == table_name:
                    logger.debug(f"✅ 找到表: {cached_table_name} (匹配 original_name: {table_name})")
                    return table_info
        
        # 3. 如果表名带前缀，尝试去除前缀查找
        else:
            pure_name = table_name.split(".")[-1]
            if pure_name in self.schema_cache:
                logger.debug(f"✅ 找到表: {pure_name} (去除前缀: {table_name})")
                return self.schema_cache[pure_name]
        
        logger.warning(f"⚠️ 未找到表: {table_name}")
        return None
    
    def get_tables_by_names(self, table_names: List[str]) -> List[Dict]:
        """
        批量获取表的 Schema 信息
        
        Args:
            table_names: 表名列表
        
        Returns:
            表 Schema 信息列表（过滤掉找不到的表）
        
        Validates: Requirements 11.5, 11.6
        """
        results = []
        for table_name in table_names:
            table_info = self.get_table_by_name(table_name)
            if table_info:
                # 添加表名到结果中（确保有 table_name 字段）
                table_info_copy = table_info.copy()
                table_info_copy["table_name"] = table_name
                results.append(table_info_copy)
        
        logger.info(f"📊 批量获取表信息: 请求 {len(table_names)} 个，找到 {len(results)} 个")
        return results


# 全局实例（可选）
_schema_vector_store = None


def get_schema_vector_store(
    embedding_model: Optional[EmbeddingModel] = None,
    vector_store: Optional[VectorStore] = None
) -> SchemaVectorStore:
    """获取 Schema 向量存储管理器实例"""
    global _schema_vector_store
    
    if _schema_vector_store is None:
        _schema_vector_store = SchemaVectorStore(embedding_model, vector_store)
    
    return _schema_vector_store
