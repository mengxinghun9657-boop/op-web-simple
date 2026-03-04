#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
知识库管理器 (Knowledge Manager)

负责知识库条目的 CRUD 操作、向量化和索引管理。

功能：
- 知识条目的创建、查询、更新、删除（软删除）
- 自动向量化和索引管理
- 权限验证和审计日志记录
- 向量检索和相似度匹配

Requirements: 17.7, 17.8, 17.9, 17.10, 17.11, 18.1-18.11, 19.1-19.10, 20.1-20.11, 22.1-22.4
"""

import json
from datetime import datetime
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import text
import numpy as np

from app.core.logger import logger
from app.services.ai.vector_store import VectorStore, get_vector_store
from app.services.ai.embedding_model import EmbeddingModel, get_embedding_model
from app.services.ai.audit_logger import AuditLogger


class KnowledgeManager:
    """
    知识库管理器
    
    负责知识条目的完整生命周期管理，包括：
    - 创建、查询、更新、删除操作
    - 自动向量化和索引
    - 权限验证
    - 审计日志记录
    
    使用示例：
    ```python
    manager = KnowledgeManager(db_session)
    
    # 创建知识条目
    entry = await manager.create_entry({
        "title": "MySQL 主从同步延迟处理方案",
        "content": "当发现 MySQL 主从同步延迟超过 10 秒时...",
        "category": "故障处理",
        "tags": ["MySQL", "主从同步"]
    }, user_id="admin", username="管理员")
    ```
    """

    
    def __init__(
        self,
        db: Session,
        vector_store: Optional[VectorStore] = None,
        embedding_model: Optional[EmbeddingModel] = None,
        audit_logger: Optional[AuditLogger] = None
    ):
        """
        初始化知识库管理器
        
        Args:
            db: 数据库会话
            vector_store: 向量存储实例（可选，默认使用全局实例）
            embedding_model: 向量化模型实例（可选，默认使用全局实例）
            audit_logger: 审计日志记录器（可选，默认创建新实例）
        """
        self.db = db
        self.vector_store = vector_store or get_vector_store()
        self.embedding_model = embedding_model or get_embedding_model()
        self.audit_logger = audit_logger or AuditLogger(db)
        
        logger.info("KnowledgeManager initialized")
    
    def _validate_required_fields(self, entry_data: Dict[str, Any]) -> None:
        """
        验证必填字段
        
        Args:
            entry_data: 知识条目数据
        
        Raises:
            ValueError: 缺少必填字段
            
        Validates: Requirements 17.7
        """
        required_fields = ["title", "content"]
        
        for field in required_fields:
            if field not in entry_data or not entry_data[field]:
                raise ValueError(f"缺少必填字段: {field}")
            
            # 检查是否为空字符串或仅包含空白字符
            if isinstance(entry_data[field], str) and not entry_data[field].strip():
                raise ValueError(f"字段 {field} 不能为空或仅包含空白字符")
        
        # 验证内容长度限制（Requirements 17.12）
        if len(entry_data["content"]) > 10000:
            raise ValueError(f"内容长度超过限制（10000字符），当前长度: {len(entry_data['content'])}")
        
        logger.debug(f"✅ 必填字段验证通过: title={entry_data['title'][:50]}...")

    
    async def create_entry(
        self,
        entry_data: Dict[str, Any],
        user_id: str,
        username: str,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        创建知识条目
        
        Args:
            entry_data: 知识条目数据，必须包含 title 和 content
                可选字段：category, tags, priority, metadata, source, source_type, source_id
            user_id: 用户ID
            username: 用户名
            session_id: 会话ID（可选）
            ip_address: IP地址（可选）
            user_agent: User Agent（可选）
        
        Returns:
            Dict: 创建的知识条目信息，包含 id 和 created_at
        
        Raises:
            ValueError: 验证失败
            Exception: 创建失败
            
        Validates: Requirements 17.7, 17.8, 17.9, 17.10, 17.11, 21.4
        """
        try:
            # 1. 验证必填字段（Requirements 17.7）
            self._validate_required_fields(entry_data)
            
            # 2. 自动创建标签（Requirements 21.4）
            if entry_data.get("tags"):
                await self._ensure_tags_exist(entry_data["tags"])
            
            # 3. 尝试向量化内容（可选，失败不中断）
            logger.info(f"尝试向量化知识条目: title={entry_data['title'][:50]}...")
            embedding = None
            try:
                content_text = f"{entry_data['title']} {entry_data['content']}"
                embedding = await self.embedding_model.encode(content_text)
                if embedding is not None and len(embedding) > 0:
                    logger.info(f"✅ 向量化成功: dimension={len(embedding)}")
                else:
                    logger.warning(f"⚠️ 向量化返回空结果，将跳过向量存储")
                    embedding = None
            except Exception as e:
                logger.warning(f"⚠️ 向量化失败，将继续保存到 MySQL（不存储向量）: {e}")
            
            # 4. 准备数据
            tags_json = json.dumps(entry_data.get("tags", []), ensure_ascii=False) if entry_data.get("tags") else None
            metadata_json = json.dumps(entry_data.get("metadata", {}), ensure_ascii=False) if entry_data.get("metadata") else None
            
            # 5. 存储到 MySQL（Requirements 17.10）
            sql_stmt = text("""
                INSERT INTO knowledge_entries (
                    title, content, metadata, category, tags, priority,
                    source, source_type, source_id,
                    author, auto_generated,
                    created_at, updated_at
                ) VALUES (
                    :title, :content, :metadata, :category, :tags, :priority,
                    :source, :source_type, :source_id,
                    :author, :auto_generated,
                    :created_at, :updated_at
                )
            """)
            
            now = datetime.now()
            result = self.db.execute(sql_stmt, {
                "title": entry_data["title"],
                "content": entry_data["content"],
                "metadata": metadata_json,
                "category": entry_data.get("category"),
                "tags": tags_json,
                "priority": entry_data.get("priority", "medium"),
                "source": entry_data.get("source", "manual"),
                "source_type": entry_data.get("source_type"),
                "source_id": entry_data.get("source_id"),
                "author": username,
                "auto_generated": entry_data.get("auto_generated", False),
                "created_at": now,
                "updated_at": now
            })
            self.db.commit()
            
            entry_id = result.lastrowid
            logger.info(f"✅ 知识条目已存储到 MySQL: entry_id={entry_id}")
            
            # 6. 更新标签使用次数（Requirements 21.5）
            if entry_data.get("tags"):
                await self._increment_tag_usage(entry_data["tags"])
            
            # 7. 存储到向量数据库（Requirements 17.10，可选）
            if embedding is not None:
                vector_metadata = {
                    "title": entry_data["title"],
                    "category": entry_data.get("category"),
                    "tags": entry_data.get("tags", []),
                    "source": entry_data.get("source", "manual"),
                    "source_type": entry_data.get("source_type"),
                    "is_deleted": False,
                    "created_at": now.isoformat()
                }
                
                success = self.vector_store.add(
                    entry_id=entry_id,
                    embedding=embedding,
                    metadata=vector_metadata
                )
                
                if success:
                    logger.info(f"✅ 知识条目已存储到向量数据库: entry_id={entry_id}")
                else:
                    logger.warning(f"⚠️ 向量存储失败: entry_id={entry_id}")
            else:
                logger.warning(f"⚠️ 跳过向量存储（未进行向量化）: entry_id={entry_id}")
            
            # 8. 记录审计日志（Requirements 17.11）
            await self.audit_logger.log_knowledge_create(
                user_id=user_id,
                username=username,
                entry_id=entry_id,
                entry_data=entry_data,
                session_id=session_id,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            logger.info(f"✅ 知识条目创建成功: entry_id={entry_id}, title={entry_data['title'][:50]}...")
            
            return {
                "id": entry_id,
                "title": entry_data["title"],
                "created_at": now.isoformat()
            }
        
        except ValueError as e:
            logger.error(f"❌ 知识条目验证失败: {e}")
            raise
        
        except Exception as e:
            logger.error(f"❌ 知识条目创建失败: {e}")
            self.db.rollback()
            raise Exception(f"创建知识条目失败: {str(e)}")

    
    async def get_entry_by_id(self, entry_id: int) -> Optional[Dict[str, Any]]:
        """
        根据ID获取知识条目
        
        Args:
            entry_id: 知识条目ID
        
        Returns:
            Optional[Dict]: 知识条目信息，如果不存在或已删除返回 None
            
        Validates: Requirements 18.5
        """
        try:
            sql_stmt = text("""
                SELECT 
                    id, title, content, metadata, category, tags, priority,
                    source, source_type, source_id,
                    author, updated_by,
                    auto_generated, manually_edited,
                    created_at, updated_at, deleted_at, deleted_by
                FROM knowledge_entries
                WHERE id = :entry_id AND deleted_at IS NULL
            """)
            
            result = self.db.execute(sql_stmt, {"entry_id": entry_id})
            row = result.fetchone()
            
            if not row:
                return None
            
            # 解析 JSON 字段
            tags = json.loads(row[5]) if row[5] else []
            metadata = json.loads(row[3]) if row[3] else {}
            
            # 处理时间戳
            created_at = row[14].isoformat() if row[14] else None
            updated_at = row[15].isoformat() if row[15] else None
            
            return {
                "id": row[0],
                "title": row[1],
                "content": row[2],
                "metadata": metadata,
                "category": row[4],
                "tags": tags,
                "priority": row[6],
                "source": row[7],
                "source_type": row[8],
                "source_id": row[9],
                "author": row[10],
                "updated_by": row[11],
                "auto_generated": bool(row[12]),
                "manually_edited": bool(row[13]),
                "created_at": created_at,
                "updated_at": updated_at
            }
        
        except Exception as e:
            logger.error(f"❌ 获取知识条目失败: entry_id={entry_id}, error={e}")
            return None

    
    async def list_entries(
        self,
        page: int = 1,
        page_size: int = 20,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        author: Optional[str] = None,
        source: Optional[str] = None,
        order_by: str = "created_at",
        order_direction: str = "DESC"
    ) -> Dict[str, Any]:
        """
        列出知识条目（分页）
        
        Args:
            page: 页码（从1开始）
            page_size: 每页数量（默认20）
            category: 分类过滤（可选）
            tags: 标签过滤（可选）
            author: 作者过滤（可选）
            source: 来源过滤（manual/auto）（可选）
            order_by: 排序字段（created_at/updated_at/priority）
            order_direction: 排序方向（ASC/DESC）
        
        Returns:
            Dict: 包含 entries（条目列表）、total（总数）、page、page_size
            
        Validates: Requirements 18.1, 18.2, 18.3, 18.4
        """
        try:
            # 构建查询条件
            where_clauses = ["deleted_at IS NULL"]
            params = {}
            
            if category:
                where_clauses.append("category = :category")
                params["category"] = category
            
            if author:
                where_clauses.append("author = :author")
                params["author"] = author
            
            if source:
                where_clauses.append("source = :source")
                params["source"] = source
            
            # 标签过滤（JSON 数组查询）
            if tags:
                for i, tag in enumerate(tags):
                    where_clauses.append(f"JSON_CONTAINS(tags, :tag_{i})")
                    params[f"tag_{i}"] = json.dumps(tag)
            
            where_clause = " AND ".join(where_clauses)
            
            # 验证排序字段
            valid_order_fields = ["created_at", "updated_at", "priority"]
            if order_by not in valid_order_fields:
                order_by = "created_at"
            
            # 验证排序方向
            if order_direction.upper() not in ["ASC", "DESC"]:
                order_direction = "DESC"
            
            # 计算偏移量
            offset = (page - 1) * page_size
            params["limit"] = page_size
            params["offset"] = offset
            
            # 查询总数
            count_sql = text(f"""
                SELECT COUNT(*) as total
                FROM knowledge_entries
                WHERE {where_clause}
            """)
            
            count_result = self.db.execute(count_sql, params)
            total = count_result.fetchone()[0]
            
            # 查询数据
            data_sql = text(f"""
                SELECT 
                    id, title, content, metadata, category, tags, priority,
                    source, source_type, source_id,
                    author, updated_by,
                    auto_generated, manually_edited,
                    created_at, updated_at
                FROM knowledge_entries
                WHERE {where_clause}
                ORDER BY {order_by} {order_direction}
                LIMIT :limit OFFSET :offset
            """)
            
            data_result = self.db.execute(data_sql, params)
            rows = data_result.fetchall()
            
            # 构建结果
            entries = []
            for row in rows:
                # 解析 JSON 字段
                tags_list = json.loads(row[5]) if row[5] else []
                metadata_dict = json.loads(row[3]) if row[3] else {}
                
                # 处理时间戳
                created_at = row[14].isoformat() if row[14] else None
                updated_at = row[15].isoformat() if row[15] else None
                
                entries.append({
                    "id": row[0],
                    "title": row[1],
                    "content": row[2][:200] + "..." if len(row[2]) > 200 else row[2],  # 摘要
                    "category": row[4],
                    "tags": tags_list,
                    "priority": row[6],
                    "source": row[7],
                    "source_type": row[8],
                    "source_id": row[9],
                    "author": row[10],
                    "updated_by": row[11],
                    "auto_generated": bool(row[12]),
                    "manually_edited": bool(row[13]),
                    "created_at": created_at,
                    "updated_at": updated_at
                })
            
            logger.info(f"✅ 列出知识条目: total={total}, page={page}, page_size={page_size}")
            
            return {
                "entries": entries,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size
            }
        
        except Exception as e:
            logger.error(f"❌ 列出知识条目失败: {e}")
            raise Exception(f"列出知识条目失败: {str(e)}")

    
    async def search_entries(
        self,
        query: str,
        top_k: int = 3,
        similarity_threshold: float = 0.6,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        向量检索知识条目
        
        Args:
            query: 查询文本
            top_k: 返回结果数量（默认3）
            similarity_threshold: 相似度阈值（默认0.6）
            category: 分类过滤（可选）
        
        Returns:
            List[Dict]: 检索结果列表，按相似度降序排序
            
        Validates: Requirements 22.1, 22.2, 22.3, 22.4
        """
        try:
            # 1. 向量化查询（Requirements 22.1）
            logger.info(f"开始向量检索: query={query[:50]}..., top_k={top_k}, threshold={similarity_threshold}")
            try:
                query_embedding = await self.embedding_model.encode(query)
                if query_embedding is None or len(query_embedding) == 0:
                    logger.warning(f"⚠️ 向量化查询返回空结果，无法进行向量检索")
                    return []
            except Exception as e:
                logger.warning(f"⚠️ 向量化查询失败，无法进行向量检索: {e}")
                return []
            
            # 2. 向量检索（Requirements 22.2, 22.4）
            # 自动过滤已删除的条目（filter_deleted=True）
            # 应用相似度阈值（similarity_threshold）
            filter_func = None
            if category:
                filter_func = lambda m: m.get("category") == category
            
            search_results = self.vector_store.search(
                query_embedding=query_embedding,
                top_k=top_k,
                similarity_threshold=similarity_threshold,
                filter_func=filter_func,
                filter_deleted=True  # Requirements 22.2: 自动过滤已删除条目
            )
            
            logger.info(f"✅ 向量检索完成: found={len(search_results)} results")
            
            # 3. 从 MySQL 获取完整信息（Requirements 22.3）
            if not search_results:
                return []
            
            entry_ids = [r["entry_id"] for r in search_results]
            placeholders = ",".join([f":id_{i}" for i in range(len(entry_ids))])
            params = {f"id_{i}": entry_id for i, entry_id in enumerate(entry_ids)}
            
            sql_stmt = text(f"""
                SELECT 
                    id, title, content, metadata, category, tags, priority,
                    source, source_type, source_id,
                    author, updated_by,
                    auto_generated, manually_edited,
                    created_at, updated_at
                FROM knowledge_entries
                WHERE id IN ({placeholders}) AND deleted_at IS NULL
            """)
            
            result = self.db.execute(sql_stmt, params)
            rows = result.fetchall()
            
            # 构建结果映射
            entries_map = {}
            for row in rows:
                # 解析 JSON 字段
                tags_list = json.loads(row[5]) if row[5] else []
                metadata_dict = json.loads(row[3]) if row[3] else {}
                
                # 处理时间戳
                created_at = row[14].isoformat() if row[14] else None
                updated_at = row[15].isoformat() if row[15] else None
                
                entries_map[row[0]] = {
                    "id": row[0],
                    "title": row[1],
                    "content": row[2],
                    "metadata": metadata_dict,
                    "category": row[4],
                    "tags": tags_list,
                    "priority": row[6],
                    "source": row[7],
                    "source_type": row[8],
                    "source_id": row[9],
                    "author": row[10],
                    "updated_by": row[11],
                    "auto_generated": bool(row[12]),
                    "manually_edited": bool(row[13]),
                    "created_at": created_at,
                    "updated_at": updated_at
                }
            
            # 4. 合并向量检索结果和数据库信息
            final_results = []
            for search_result in search_results:
                entry_id = search_result["entry_id"]
                if entry_id in entries_map:
                    entry = entries_map[entry_id]
                    entry["similarity"] = search_result["similarity"]
                    final_results.append(entry)
            
            logger.info(f"✅ 知识条目检索完成: returned={len(final_results)} entries")
            
            return final_results
        
        except Exception as e:
            logger.error(f"❌ 知识条目检索失败: {e}")
            return []

    
    async def update_entry(
        self,
        entry_id: int,
        updates: Dict[str, Any],
        user_id: str,
        username: str,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """
        更新知识条目
        
        Args:
            entry_id: 知识条目ID
            updates: 更新的字段（可包含 title, content, category, tags, priority, metadata）
            user_id: 用户ID
            username: 用户名
            session_id: 会话ID（可选）
            ip_address: IP地址（可选）
            user_agent: User Agent（可选）
        
        Returns:
            bool: 是否更新成功
            
        Validates: Requirements 19.1, 19.2, 19.3, 19.4, 19.5, 19.6, 19.8, 19.9, 19.10, 21.4, 21.5
        """
        try:
            # 1. 检查条目是否存在
            existing_entry = await self.get_entry_by_id(entry_id)
            if not existing_entry:
                raise ValueError(f"知识条目不存在: entry_id={entry_id}")
            
            # 2. 验证更新字段
            if "content" in updates and len(updates["content"]) > 10000:
                raise ValueError(f"内容长度超过限制（10000字符），当前长度: {len(updates['content'])}")
            
            # 3. 处理标签变更（Requirements 21.4, 21.5）
            old_tags = existing_entry.get("tags", [])
            new_tags = updates.get("tags", old_tags)
            
            if "tags" in updates:
                # 确保新标签存在
                await self._ensure_tags_exist(new_tags)
                
                # 计算标签变更
                removed_tags = [tag for tag in old_tags if tag not in new_tags]
                added_tags = [tag for tag in new_tags if tag not in old_tags]
                
                # 更新标签使用次数
                if removed_tags:
                    await self._decrement_tag_usage(removed_tags)
                if added_tags:
                    await self._increment_tag_usage(added_tags)
            
            # 4. 准备更新语句
            update_fields = []
            params = {"entry_id": entry_id, "updated_by": username, "updated_at": datetime.now()}
            
            # 可更新的字段
            updatable_fields = ["title", "content", "category", "priority"]
            for field in updatable_fields:
                if field in updates:
                    update_fields.append(f"{field} = :{field}")
                    params[field] = updates[field]
            
            # JSON 字段
            if "tags" in updates:
                update_fields.append("tags = :tags")
                params["tags"] = json.dumps(updates["tags"], ensure_ascii=False)
            
            if "metadata" in updates:
                update_fields.append("metadata = :metadata")
                params["metadata"] = json.dumps(updates["metadata"], ensure_ascii=False)
            
            # 标记手动编辑（Requirements 19.10）
            if existing_entry.get("auto_generated"):
                update_fields.append("manually_edited = TRUE")
            
            # 更新时间和更新者
            update_fields.append("updated_by = :updated_by")
            update_fields.append("updated_at = :updated_at")
            
            if not update_fields:
                logger.warning(f"没有需要更新的字段: entry_id={entry_id}")
                return False
            
            # 5. 执行更新（Requirements 19.5, 19.6）
            sql_stmt = text(f"""
                UPDATE knowledge_entries
                SET {", ".join(update_fields)}
                WHERE id = :entry_id AND deleted_at IS NULL
            """)
            
            result = self.db.execute(sql_stmt, params)
            
            if result.rowcount == 0:
                self.db.rollback()
                raise ValueError(f"更新失败，条目可能已被删除: entry_id={entry_id}")
            
            self.db.commit()
            logger.info(f"✅ 知识条目已更新到 MySQL: entry_id={entry_id}")
            
            # 6. 如果内容被更新，重新生成向量（Requirements 19.4）
            if "title" in updates or "content" in updates:
                logger.info(f"内容已更新，重新生成向量: entry_id={entry_id}")
                
                # 获取最新的 title 和 content
                updated_entry = await self.get_entry_by_id(entry_id)
                if updated_entry:
                    try:
                        content_text = f"{updated_entry['title']} {updated_entry['content']}"
                        new_embedding = await self.embedding_model.encode(content_text)
                        if new_embedding is None or len(new_embedding) == 0:
                            raise ValueError("向量化模型返回空结果")
                    except Exception as e:
                        logger.warning(f"⚠️ 向量化失败，跳过向量更新: {e}")
                        new_embedding = None
                    
                    if new_embedding is not None:
                        # 更新向量存储的元数据
                        vector_metadata = {
                            "title": updated_entry["title"],
                            "category": updated_entry.get("category"),
                            "tags": updated_entry.get("tags", []),
                            "source": updated_entry.get("source"),
                            "source_type": updated_entry.get("source_type"),
                            "is_deleted": False,
                            "created_at": updated_entry["created_at"]
                        }
                        
                        # 删除旧向量并添加新向量
                        self.vector_store.delete(entry_id)
                        success = self.vector_store.add(
                            entry_id=entry_id,
                            embedding=new_embedding,
                            metadata=vector_metadata
                        )
                        
                        if not success:
                            logger.error(f"❌ 向量更新失败: entry_id={entry_id}")
                            # 不回滚 MySQL 更新，因为数据已经更新成功
                        else:
                            logger.info(f"✅ 向量已更新: entry_id={entry_id}")
            
            # 7. 记录审计日志
            await self.audit_logger.log_knowledge_update(
                user_id=user_id,
                username=username,
                entry_id=entry_id,
                updates=updates,
                session_id=session_id,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            logger.info(f"✅ 知识条目更新成功: entry_id={entry_id}")
            return True
        
        except ValueError as e:
            logger.error(f"❌ 知识条目更新验证失败: {e}")
            raise
        
        except Exception as e:
            logger.error(f"❌ 知识条目更新失败: entry_id={entry_id}, error={e}")
            self.db.rollback()
            raise Exception(f"更新知识条目失败: {str(e)}")

    
    async def soft_delete_entry(
        self,
        entry_id: int,
        user_id: str,
        username: str,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """
        软删除知识条目
        
        Args:
            entry_id: 知识条目ID
            user_id: 用户ID
            username: 用户名
            session_id: 会话ID（可选）
            ip_address: IP地址（可选）
            user_agent: User Agent（可选）
        
        Returns:
            bool: 是否删除成功
            
        Validates: Requirements 20.1, 20.2, 20.3, 20.4, 20.5, 20.8, 21.5
        """
        try:
            # 1. 检查条目是否存在并获取标签信息
            existing_entry = await self.get_entry_by_id(entry_id)
            if not existing_entry:
                raise ValueError(f"知识条目不存在: entry_id={entry_id}")
            
            # 2. MySQL 软删除（Requirements 20.4）
            sql_stmt = text("""
                UPDATE knowledge_entries
                SET deleted_at = :deleted_at, deleted_by = :deleted_by
                WHERE id = :entry_id AND deleted_at IS NULL
            """)
            
            result = self.db.execute(sql_stmt, {
                "entry_id": entry_id,
                "deleted_at": datetime.now(),
                "deleted_by": username
            })
            
            if result.rowcount == 0:
                self.db.rollback()
                raise ValueError(f"删除失败，条目可能已被删除: entry_id={entry_id}")
            
            self.db.commit()
            logger.info(f"✅ 知识条目已软删除（MySQL）: entry_id={entry_id}")
            
            # 3. 更新标签使用次数（Requirements 21.5）
            if existing_entry.get("tags"):
                await self._decrement_tag_usage(existing_entry["tags"])
            
            # 4. 向量存储标记删除（Requirements 20.5）
            success = self.vector_store.mark_deleted(entry_id)
            if not success:
                logger.warning(f"⚠️ 向量存储标记删除失败: entry_id={entry_id}")
                # 不回滚 MySQL 删除，因为软删除已经成功
            else:
                logger.info(f"✅ 知识条目已标记删除（向量存储）: entry_id={entry_id}")
            
            # 5. 记录审计日志（Requirements 20.8）
            await self.audit_logger.log_knowledge_delete(
                user_id=user_id,
                username=username,
                entry_id=entry_id,
                entry_title=existing_entry.get("title"),
                session_id=session_id,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            logger.info(f"✅ 知识条目软删除成功: entry_id={entry_id}, title={existing_entry.get('title')[:50]}...")
            return True
        
        except ValueError as e:
            logger.error(f"❌ 知识条目删除验证失败: {e}")
            raise
        
        except Exception as e:
            logger.error(f"❌ 知识条目删除失败: entry_id={entry_id}, error={e}")
            self.db.rollback()
            raise Exception(f"删除知识条目失败: {str(e)}")

    
    async def cleanup_deleted_entries(self, days_threshold: int = 30) -> Dict[str, Any]:
        """
        物理删除软删除超过指定天数的条目
        
        此方法会：
        1. 从 MySQL 中物理删除 deleted_at 超过指定天数的记录
        2. 从向量数据库中物理删除对应的向量
        
        Args:
            days_threshold: 软删除后保留的天数（默认30天）
        
        Returns:
            Dict: 清理结果，包含 deleted_count（删除数量）和 deleted_ids（删除的条目ID列表）
            
        Validates: Requirements 20.7
        """
        try:
            logger.info(f"开始清理软删除超过 {days_threshold} 天的知识条目...")
            
            # 1. 查询需要物理删除的条目
            sql_query = text("""
                SELECT id, title, tags
                FROM knowledge_entries
                WHERE deleted_at IS NOT NULL 
                  AND deleted_at < DATE_SUB(NOW(), INTERVAL :days DAY)
            """)
            
            result = self.db.execute(sql_query, {"days": days_threshold})
            entries_to_delete = result.fetchall()
            
            if not entries_to_delete:
                logger.info("✅ 没有需要清理的条目")
                return {
                    "deleted_count": 0,
                    "deleted_ids": [],
                    "message": f"没有软删除超过 {days_threshold} 天的条目"
                }
            
            deleted_ids = []
            deleted_titles = []
            
            # 2. 逐个删除条目
            for entry in entries_to_delete:
                entry_id = entry[0]
                entry_title = entry[1]
                entry_tags = json.loads(entry[2]) if entry[2] else []
                
                try:
                    # 2.1 从向量数据库中物理删除
                    vector_deleted = self.vector_store.delete(entry_id)
                    if vector_deleted:
                        logger.info(f"✅ 从向量数据库删除: entry_id={entry_id}")
                    else:
                        logger.warning(f"⚠️ 向量数据库删除失败或条目不存在: entry_id={entry_id}")
                    
                    # 2.2 更新标签使用次数（Requirements 21.5）
                    if entry_tags:
                        await self._decrement_tag_usage(entry_tags)
                    
                    # 2.3 从 MySQL 中物理删除
                    sql_delete = text("""
                        DELETE FROM knowledge_entries
                        WHERE id = :entry_id
                    """)
                    
                    delete_result = self.db.execute(sql_delete, {"entry_id": entry_id})
                    
                    if delete_result.rowcount > 0:
                        deleted_ids.append(entry_id)
                        deleted_titles.append(entry_title[:50] if entry_title else "无标题")
                        logger.info(f"✅ 从 MySQL 删除: entry_id={entry_id}, title={entry_title[:50] if entry_title else '无标题'}...")
                    else:
                        logger.warning(f"⚠️ MySQL 删除失败: entry_id={entry_id}")
                
                except Exception as e:
                    logger.error(f"❌ 删除条目失败: entry_id={entry_id}, error={e}")
                    # 继续处理其他条目
                    continue
            
            # 3. 提交事务
            self.db.commit()
            
            logger.info(f"✅ 清理完成: 共删除 {len(deleted_ids)} 个条目")
            
            return {
                "deleted_count": len(deleted_ids),
                "deleted_ids": deleted_ids,
                "deleted_titles": deleted_titles,
                "message": f"成功清理 {len(deleted_ids)} 个软删除超过 {days_threshold} 天的条目"
            }
        
        except Exception as e:
            logger.error(f"❌ 清理删除条目失败: {e}")
            self.db.rollback()
            raise Exception(f"清理删除条目失败: {str(e)}")
    
    async def _ensure_tags_exist(self, tags: List[str]) -> None:
        """
        确保标签存在，如果不存在则自动创建
        
        Args:
            tags: 标签名称列表
            
        Validates: Requirements 21.4
        """
        if not tags:
            return
        
        try:
            for tag_name in tags:
                # 检查标签是否存在
                sql_check = text("""
                    SELECT id FROM knowledge_tags WHERE name = :tag_name
                """)
                
                result = self.db.execute(sql_check, {"tag_name": tag_name})
                existing_tag = result.fetchone()
                
                if not existing_tag:
                    # 自动创建标签
                    sql_insert = text("""
                        INSERT INTO knowledge_tags (name, usage_count, created_at)
                        VALUES (:tag_name, 0, :created_at)
                    """)
                    
                    self.db.execute(sql_insert, {
                        "tag_name": tag_name,
                        "created_at": datetime.now()
                    })
                    
                    logger.info(f"✅ 自动创建标签: {tag_name}")
            
            self.db.commit()
        
        except Exception as e:
            logger.error(f"❌ 确保标签存在失败: {e}")
            self.db.rollback()
            raise
    
    async def _increment_tag_usage(self, tags: List[str]) -> None:
        """
        增加标签使用次数
        
        Args:
            tags: 标签名称列表
            
        Validates: Requirements 21.5
        """
        if not tags:
            return
        
        try:
            for tag_name in tags:
                sql_update = text("""
                    UPDATE knowledge_tags
                    SET usage_count = usage_count + 1
                    WHERE name = :tag_name
                """)
                
                self.db.execute(sql_update, {"tag_name": tag_name})
            
            self.db.commit()
            logger.debug(f"✅ 更新标签使用次数: {tags}")
        
        except Exception as e:
            logger.error(f"❌ 更新标签使用次数失败: {e}")
            self.db.rollback()
            raise
    
    async def _decrement_tag_usage(self, tags: List[str]) -> None:
        """
        减少标签使用次数
        
        Args:
            tags: 标签名称列表
            
        Validates: Requirements 21.5
        """
        if not tags:
            return
        
        try:
            for tag_name in tags:
                sql_update = text("""
                    UPDATE knowledge_tags
                    SET usage_count = GREATEST(usage_count - 1, 0)
                    WHERE name = :tag_name
                """)
                
                self.db.execute(sql_update, {"tag_name": tag_name})
            
            self.db.commit()
            logger.debug(f"✅ 减少标签使用次数: {tags}")
        
        except Exception as e:
            logger.error(f"❌ 减少标签使用次数失败: {e}")
            self.db.rollback()
            raise


# 创建全局实例获取函数（单例模式）
def get_knowledge_manager(db: Session) -> KnowledgeManager:
    """
    获取知识库管理器实例
    
    Args:
        db: 数据库会话
    
    Returns:
        KnowledgeManager: 知识库管理器实例
    """
    return KnowledgeManager(db)
