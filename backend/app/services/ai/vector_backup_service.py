#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
向量数据库备份与恢复服务

实现向量数据库的备份、恢复和重建功能。

功能：
- 备份向量数据库文件和 MySQL 元数据到 MinIO
- 从 MinIO 恢复向量数据库
- 从 MySQL 元数据重建向量索引

Requirements: 26.6, 26.7, 26.8, 26.9, 26.10, 26.11
"""

import os
import json
import tarfile
import tempfile
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.logger import logger
from app.core.minio_client import get_minio_client
from app.services.ai.vector_store import VectorStore, get_vector_store
from app.services.ai.embedding_model import EmbeddingModel, get_embedding_model


class VectorBackupService:
    """
    向量数据库备份与恢复服务
    
    负责：
    - 备份向量数据库文件和 MySQL 知识库元数据
    - 压缩后上传到 MinIO 的 vector-backups/ 目录
    - 从 MinIO 下载备份并恢复
    - 从 MySQL 元数据重建向量索引
    
    使用示例：
    ```python
    service = VectorBackupService(db_session)
    
    # 备份
    backup_info = await service.backup_vector_store()
    
    # 恢复
    success = await service.restore_vector_store(backup_file="backup_20260123_120000.tar.gz")
    
    # 重建
    stats = await service.rebuild_vector_store()
    ```
    """
    
    def __init__(
        self,
        db: Session,
        vector_store: Optional[VectorStore] = None,
        embedding_model: Optional[EmbeddingModel] = None
    ):
        """
        初始化备份服务
        
        Args:
            db: 数据库会话
            vector_store: 向量存储实例（可选，默认使用全局实例）
            embedding_model: 向量化模型实例（可选，默认使用全局实例）
        """
        self.db = db
        self.vector_store = vector_store or get_vector_store()
        self.embedding_model = embedding_model or get_embedding_model()
        self.minio_client = get_minio_client()
        
        # MinIO 备份目录
        self.backup_prefix = "vector-backups/"
        
        logger.info("VectorBackupService initialized")
    
    async def backup_vector_store(
        self,
        user_id: str,
        username: str,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        备份向量数据库
        
        备份内容包括：
        1. 向量数据库文件（FAISS 索引、ID 映射、元数据）
        2. MySQL 知识库元数据（knowledge_entries 表）
        3. 备份元信息（时间、用户、描述）
        
        备份文件命名格式：backup_YYYYMMDD_HHMMSS.tar.gz
        
        Args:
            user_id: 执行备份的用户ID
            username: 执行备份的用户名
            description: 备份描述（可选）
        
        Returns:
            Dict: 备份信息，包含：
                - backup_file: 备份文件名
                - backup_path: MinIO 中的完整路径
                - backup_time: 备份时间
                - file_size_bytes: 文件大小（字节）
                - vector_count: 向量数量
                - entry_count: 知识条目数量
        
        Raises:
            Exception: 备份失败
            
        Validates: Requirements 26.6, 26.7
        """
        try:
            logger.info(f"开始备份向量数据库: user={username}")
            
            # 1. 创建临时目录
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                backup_dir = temp_path / "vector_backup"
                backup_dir.mkdir()
                
                # 2. 备份向量数据库文件
                logger.info("备份向量数据库文件...")
                vector_backup_dir = backup_dir / "vector_store"
                vector_backup_dir.mkdir()
                
                # 复制 FAISS 索引文件
                vector_store_path = Path(self.vector_store.index_path)
                for file_name in ["faiss_index.bin", "id_map.json", "metadata.json"]:
                    src_file = vector_store_path / file_name
                    if src_file.exists():
                        dst_file = vector_backup_dir / file_name
                        import shutil
                        shutil.copy2(src_file, dst_file)
                        logger.info(f"  ✓ 已复制: {file_name}")
                    else:
                        logger.warning(f"  ⚠️ 文件不存在: {file_name}")
                
                # 3. 导出 MySQL 知识库元数据
                logger.info("导出 MySQL 知识库元数据...")
                metadata_file = backup_dir / "knowledge_entries.json"
                
                sql_query = text("""
                    SELECT 
                        id, title, content, metadata, category, tags, priority,
                        source, source_type, source_id,
                        author, updated_by,
                        auto_generated, manually_edited,
                        created_at, updated_at, deleted_at, deleted_by
                    FROM knowledge_entries
                """)
                
                result = self.db.execute(sql_query)
                rows = result.fetchall()
                
                entries = []
                for row in rows:
                    entry = {
                        "id": row[0],
                        "title": row[1],
                        "content": row[2],
                        "metadata": row[3],  # JSON 字符串
                        "category": row[4],
                        "tags": row[5],  # JSON 字符串
                        "priority": row[6],
                        "source": row[7],
                        "source_type": row[8],
                        "source_id": row[9],
                        "author": row[10],
                        "updated_by": row[11],
                        "auto_generated": bool(row[12]),
                        "manually_edited": bool(row[13]),
                        "created_at": row[14].isoformat() if row[14] else None,
                        "updated_at": row[15].isoformat() if row[15] else None,
                        "deleted_at": row[16].isoformat() if row[16] else None,
                        "deleted_by": row[17]
                    }
                    entries.append(entry)
                
                with open(metadata_file, 'w', encoding='utf-8') as f:
                    json.dump(entries, f, ensure_ascii=False, indent=2)
                
                logger.info(f"  ✓ 已导出 {len(entries)} 条知识条目")
                
                # 4. 创建备份元信息
                backup_info = {
                    "backup_time": datetime.now().isoformat(),
                    "backup_user_id": user_id,
                    "backup_username": username,
                    "description": description or "向量数据库备份",
                    "vector_count": self.vector_store.index.ntotal if self.vector_store.index else 0,
                    "entry_count": len(entries),
                    "vector_dimension": self.vector_store.dimension,
                    "vector_db_type": "faiss"
                }
                
                info_file = backup_dir / "backup_info.json"
                with open(info_file, 'w', encoding='utf-8') as f:
                    json.dump(backup_info, f, ensure_ascii=False, indent=2)
                
                logger.info("  ✓ 已创建备份元信息")
                
                # 5. 压缩备份文件
                logger.info("压缩备份文件...")
                backup_filename = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.tar.gz"
                backup_tar_path = temp_path / backup_filename
                
                with tarfile.open(backup_tar_path, "w:gz") as tar:
                    tar.add(backup_dir, arcname="vector_backup")
                
                file_size = backup_tar_path.stat().st_size
                logger.info(f"  ✓ 压缩完成: {backup_filename} ({file_size / 1024 / 1024:.2f} MB)")
                
                # 6. 上传到 MinIO
                logger.info("上传备份到 MinIO...")
                minio_object_name = f"{self.backup_prefix}{backup_filename}"
                
                with open(backup_tar_path, 'rb') as f:
                    backup_data = f.read()
                
                self.minio_client.upload_data(
                    data=backup_data,
                    object_name=minio_object_name,
                    content_type='application/gzip'
                )
                
                logger.info(f"  ✓ 已上传到 MinIO: {minio_object_name}")
                
                # 7. 返回备份信息
                result = {
                    "success": True,
                    "backup_file": backup_filename,
                    "backup_path": minio_object_name,
                    "backup_time": backup_info["backup_time"],
                    "file_size_bytes": file_size,
                    "file_size_mb": round(file_size / 1024 / 1024, 2),
                    "vector_count": backup_info["vector_count"],
                    "entry_count": backup_info["entry_count"],
                    "description": backup_info["description"]
                }
                
                logger.info(f"✅ 向量数据库备份成功: {backup_filename}")
                
                return result
        
        except Exception as e:
            logger.error(f"❌ 向量数据库备份失败: {e}", exc_info=True)
            raise Exception(f"备份失败: {str(e)}")
    
    async def restore_vector_store(
        self,
        backup_file: str,
        user_id: str,
        username: str,
        restore_mysql: bool = True,
        restore_vectors: bool = True
    ) -> Dict[str, Any]:
        """
        恢复向量数据库
        
        从 MinIO 下载备份文件并恢复向量数据库和 MySQL 元数据。
        
        Args:
            backup_file: 备份文件名（例如：backup_20260123_120000.tar.gz）
            user_id: 执行恢复的用户ID
            username: 执行恢复的用户名
            restore_mysql: 是否恢复 MySQL 数据（默认 True）
            restore_vectors: 是否恢复向量数据库（默认 True）
        
        Returns:
            Dict: 恢复结果，包含：
                - success: 是否成功
                - restored_entries: 恢复的条目数量
                - restored_vectors: 恢复的向量数量
                - backup_info: 备份元信息
        
        Raises:
            Exception: 恢复失败
            
        Validates: Requirements 26.8, 26.9
        """
        try:
            logger.info(f"开始恢复向量数据库: backup_file={backup_file}, user={username}")
            
            # 1. 从 MinIO 下载备份文件
            logger.info("从 MinIO 下载备份文件...")
            minio_object_name = f"{self.backup_prefix}{backup_file}"
            
            backup_data = self.minio_client.download_data(minio_object_name)
            logger.info(f"  ✓ 已下载: {len(backup_data) / 1024 / 1024:.2f} MB")
            
            # 2. 解压备份文件
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                backup_tar_path = temp_path / backup_file
                
                # 写入临时文件
                with open(backup_tar_path, 'wb') as f:
                    f.write(backup_data)
                
                # 解压
                logger.info("解压备份文件...")
                extract_dir = temp_path / "extracted"
                extract_dir.mkdir()
                
                with tarfile.open(backup_tar_path, "r:gz") as tar:
                    tar.extractall(extract_dir)
                
                backup_dir = extract_dir / "vector_backup"
                
                # 3. 读取备份元信息
                info_file = backup_dir / "backup_info.json"
                with open(info_file, 'r', encoding='utf-8') as f:
                    backup_info = json.load(f)
                
                logger.info(f"  ✓ 备份信息: {backup_info['backup_time']}, 条目数={backup_info['entry_count']}, 向量数={backup_info['vector_count']}")
                
                restored_entries = 0
                restored_vectors = 0
                
                # 4. 恢复 MySQL 数据
                if restore_mysql:
                    logger.info("恢复 MySQL 知识库元数据...")
                    metadata_file = backup_dir / "knowledge_entries.json"
                    
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        entries = json.load(f)
                    
                    # 清空现有数据（可选，根据需求决定）
                    # self.db.execute(text("TRUNCATE TABLE knowledge_entries"))
                    
                    # 插入数据
                    for entry in entries:
                        try:
                            sql_insert = text("""
                                INSERT INTO knowledge_entries (
                                    id, title, content, metadata, category, tags, priority,
                                    source, source_type, source_id,
                                    author, updated_by,
                                    auto_generated, manually_edited,
                                    created_at, updated_at, deleted_at, deleted_by
                                ) VALUES (
                                    :id, :title, :content, :metadata, :category, :tags, :priority,
                                    :source, :source_type, :source_id,
                                    :author, :updated_by,
                                    :auto_generated, :manually_edited,
                                    :created_at, :updated_at, :deleted_at, :deleted_by
                                )
                                ON DUPLICATE KEY UPDATE
                                    title = VALUES(title),
                                    content = VALUES(content),
                                    metadata = VALUES(metadata),
                                    category = VALUES(category),
                                    tags = VALUES(tags),
                                    priority = VALUES(priority),
                                    updated_at = VALUES(updated_at),
                                    updated_by = VALUES(updated_by),
                                    manually_edited = VALUES(manually_edited)
                            """)
                            
                            self.db.execute(sql_insert, entry)
                            restored_entries += 1
                        
                        except Exception as e:
                            logger.error(f"  ⚠️ 恢复条目失败: id={entry.get('id')}, error={e}")
                            continue
                    
                    self.db.commit()
                    logger.info(f"  ✓ 已恢复 {restored_entries} 条知识条目")
                
                # 5. 恢复向量数据库文件
                if restore_vectors:
                    logger.info("恢复向量数据库文件...")
                    vector_backup_dir = backup_dir / "vector_store"
                    vector_store_path = Path(self.vector_store.index_path)
                    
                    # 备份当前文件（以防恢复失败）
                    import shutil
                    backup_current_dir = temp_path / "current_backup"
                    if vector_store_path.exists():
                        shutil.copytree(vector_store_path, backup_current_dir)
                        logger.info("  ✓ 已备份当前向量数据库文件")
                    
                    # 复制备份文件
                    for file_name in ["faiss_index.bin", "id_map.json", "metadata.json"]:
                        src_file = vector_backup_dir / file_name
                        if src_file.exists():
                            dst_file = vector_store_path / file_name
                            shutil.copy2(src_file, dst_file)
                            logger.info(f"  ✓ 已恢复: {file_name}")
                        else:
                            logger.warning(f"  ⚠️ 备份中不存在: {file_name}")
                    
                    # 重新加载向量存储
                    logger.info("重新加载向量存储...")
                    self.vector_store._load_index()
                    restored_vectors = self.vector_store.index.ntotal if self.vector_store.index else 0
                    logger.info(f"  ✓ 已加载 {restored_vectors} 个向量")
                
                # 6. 返回恢复结果
                result = {
                    "success": True,
                    "restored_entries": restored_entries,
                    "restored_vectors": restored_vectors,
                    "backup_info": backup_info,
                    "restore_mysql": restore_mysql,
                    "restore_vectors": restore_vectors
                }
                
                logger.info(f"✅ 向量数据库恢复成功: entries={restored_entries}, vectors={restored_vectors}")
                
                return result
        
        except Exception as e:
            logger.error(f"❌ 向量数据库恢复失败: {e}", exc_info=True)
            raise Exception(f"恢复失败: {str(e)}")
    
    async def rebuild_vector_store(
        self,
        user_id: str,
        username: str,
        include_deleted: bool = False
    ) -> Dict[str, Any]:
        """
        从 MySQL 元数据重建向量索引
        
        当向量数据库文件损坏或需要清理已删除的向量时使用。
        
        Args:
            user_id: 执行重建的用户ID
            username: 执行重建的用户名
            include_deleted: 是否包含已删除的条目（默认 False）
        
        Returns:
            Dict: 重建结果，包含：
                - success: 是否成功
                - total_entries: 总条目数
                - rebuilt_entries: 成功重建的条目数
                - failed_entries: 失败的条目数
                - skipped_entries: 跳过的条目数（已删除）
        
        Raises:
            Exception: 重建失败
            
        Validates: Requirements 26.10, 26.11
        """
        try:
            logger.info(f"开始重建向量索引: user={username}, include_deleted={include_deleted}")
            
            # 1. 从 MySQL 查询所有知识条目
            logger.info("从 MySQL 查询知识条目...")
            
            where_clause = "" if include_deleted else "WHERE deleted_at IS NULL"
            
            sql_query = text(f"""
                SELECT 
                    id, title, content, metadata, category, tags,
                    source, source_type,
                    created_at
                FROM knowledge_entries
                {where_clause}
                ORDER BY id ASC
            """)
            
            result = self.db.execute(sql_query)
            rows = result.fetchall()
            
            total_entries = len(rows)
            logger.info(f"  ✓ 查询到 {total_entries} 条知识条目")
            
            if total_entries == 0:
                return {
                    "success": True,
                    "total_entries": 0,
                    "rebuilt_entries": 0,
                    "failed_entries": 0,
                    "skipped_entries": 0,
                    "message": "没有需要重建的条目"
                }
            
            # 2. 准备重建数据
            logger.info("准备重建数据...")
            entries_to_rebuild = []
            
            for row in rows:
                entry_id = row[0]
                title = row[1]
                content = row[2]
                metadata_json = row[3]
                category = row[4]
                tags_json = row[5]
                source = row[6]
                source_type = row[7]
                created_at = row[8]
                
                # 解析 JSON 字段
                tags = json.loads(tags_json) if tags_json else []
                
                # 向量化内容
                try:
                    content_text = f"{title} {content}"
                    embedding = await self.embedding_model.encode(content_text)
                    
                    # 准备元数据
                    vector_metadata = {
                        "title": title,
                        "category": category,
                        "tags": tags,
                        "source": source,
                        "source_type": source_type,
                        "is_deleted": False,
                        "created_at": created_at.isoformat() if created_at else None
                    }
                    
                    entries_to_rebuild.append({
                        "entry_id": entry_id,
                        "embedding": embedding,
                        "metadata": vector_metadata
                    })
                
                except Exception as e:
                    logger.error(f"  ⚠️ 向量化失败: entry_id={entry_id}, error={e}")
                    continue
            
            logger.info(f"  ✓ 准备了 {len(entries_to_rebuild)} 条数据用于重建")
            
            # 3. 重建向量索引
            logger.info("重建向量索引...")
            success = self.vector_store.rebuild_index(entries_to_rebuild)
            
            if not success:
                raise Exception("向量索引重建失败")
            
            rebuilt_entries = len(entries_to_rebuild)
            failed_entries = total_entries - rebuilt_entries
            
            logger.info(f"  ✓ 重建完成: 成功={rebuilt_entries}, 失败={failed_entries}")
            
            # 4. 返回重建结果
            result = {
                "success": True,
                "total_entries": total_entries,
                "rebuilt_entries": rebuilt_entries,
                "failed_entries": failed_entries,
                "skipped_entries": 0,
                "vector_count": self.vector_store.index.ntotal if self.vector_store.index else 0
            }
            
            logger.info(f"✅ 向量索引重建成功: {rebuilt_entries}/{total_entries}")
            
            return result
        
        except Exception as e:
            logger.error(f"❌ 向量索引重建失败: {e}", exc_info=True)
            raise Exception(f"重建失败: {str(e)}")
    
    async def list_backups(self) -> Dict[str, Any]:
        """
        列出所有可用的备份文件
        
        Returns:
            Dict: 备份列表，包含：
                - backups: 备份文件列表
                - total: 总数
        """
        try:
            logger.info("列出备份文件...")
            
            # 从 MinIO 列出备份文件
            backup_files = self.minio_client.list_objects(prefix=self.backup_prefix)
            
            backups = []
            for file_path in backup_files:
                # 提取文件名
                file_name = file_path.replace(self.backup_prefix, "")
                
                # 解析文件名获取时间
                # 格式：backup_YYYYMMDD_HHMMSS.tar.gz
                if file_name.startswith("backup_") and file_name.endswith(".tar.gz"):
                    try:
                        time_str = file_name.replace("backup_", "").replace(".tar.gz", "")
                        backup_time = datetime.strptime(time_str, "%Y%m%d_%H%M%S")
                        
                        backups.append({
                            "file_name": file_name,
                            "file_path": file_path,
                            "backup_time": backup_time.isoformat()
                        })
                    except ValueError:
                        logger.warning(f"  ⚠️ 无法解析备份文件名: {file_name}")
                        continue
            
            # 按时间倒序排序
            backups.sort(key=lambda x: x["backup_time"], reverse=True)
            
            logger.info(f"  ✓ 找到 {len(backups)} 个备份文件")
            
            return {
                "backups": backups,
                "total": len(backups)
            }
        
        except Exception as e:
            logger.error(f"❌ 列出备份文件失败: {e}", exc_info=True)
            raise Exception(f"列出备份失败: {str(e)}")


# 创建全局实例获取函数
def get_vector_backup_service(db: Session) -> VectorBackupService:
    """
    获取向量备份服务实例
    
    Args:
        db: 数据库会话
    
    Returns:
        VectorBackupService: 向量备份服务实例
    """
    return VectorBackupService(db)
