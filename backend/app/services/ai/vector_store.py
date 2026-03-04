#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
向量数据库管理器 - FAISS 实现
支持向量的存储、检索、更新和删除操作
"""

import os
import json
import pickle
from typing import List, Dict, Optional, Any
from pathlib import Path
import numpy as np

try:
    import faiss
except ImportError:
    faiss = None

from app.core.config import settings
from app.core.logger import logger


class VectorStore:
    """
    向量数据库管理器（FAISS 实现）
    
    功能：
    - 向量的添加、检索、更新、删除
    - 元数据管理
    - 持久化存储和加载
    - 健康检查
    
    文件结构：
    /app/vector_store/
    ├── faiss_index.bin          # FAISS 索引文件
    ├── id_map.json              # ID 映射（vector_id -> entry_id）
    └── metadata.json            # 元数据
    """
    
    def __init__(self, dimension: int = None, index_path: str = None):
        """
        初始化向量存储
        
        Args:
            dimension: 向量维度，默认从配置读取
            index_path: 索引文件路径，默认从配置读取
        """
        if faiss is None:
            raise ImportError("faiss-cpu is not installed. Please install it with: pip install faiss-cpu")
        
        self.dimension = dimension or settings.VECTOR_DIMENSION
        self.index_path = index_path or settings.VECTOR_DB_PATH
        
        # 确保目录存在
        os.makedirs(self.index_path, exist_ok=True)
        
        # 文件路径
        self.index_file = os.path.join(self.index_path, "faiss_index.bin")
        self.id_map_file = os.path.join(self.index_path, "id_map.json")
        self.metadata_file = os.path.join(self.index_path, "metadata.json")
        
        # 初始化索引和映射
        self.index: Optional[faiss.Index] = None
        self.id_map: Dict[int, int] = {}  # vector_id -> entry_id
        self.metadata: Dict[int, Dict[str, Any]] = {}  # entry_id -> metadata
        self.next_vector_id: int = 0
        
        # 加载或创建索引
        self._load_or_create_index()
        
        logger.info(f"VectorStore initialized with dimension={self.dimension}, path={self.index_path}")
    
    def _load_or_create_index(self):
        """加载现有索引或创建新索引"""
        if os.path.exists(self.index_file):
            try:
                self._load_index()
                logger.info(f"Loaded existing FAISS index from {self.index_file}")
            except Exception as e:
                logger.error(f"Failed to load FAISS index: {e}")
                logger.info("Creating new FAISS index")
                self._create_new_index()
        else:
            logger.info("No existing index found, creating new FAISS index")
            self._create_new_index()
    
    def _create_new_index(self):
        """创建新的 FAISS 索引"""
        # 使用 IndexFlatIP（内积索引）用于余弦相似度
        # 注意：向量需要归一化后才能使用内积计算余弦相似度
        self.index = faiss.IndexFlatIP(self.dimension)
        self.id_map = {}
        self.metadata = {}
        self.next_vector_id = 0
        logger.info(f"Created new FAISS IndexFlatIP with dimension={self.dimension}")
    
    def _load_index(self):
        """从文件加载索引"""
        # 加载 FAISS 索引
        self.index = faiss.read_index(self.index_file)
        
        # 加载 ID 映射
        if os.path.exists(self.id_map_file):
            with open(self.id_map_file, 'r', encoding='utf-8') as f:
                # JSON 的 key 是字符串，需要转换为整数
                id_map_str = json.load(f)
                self.id_map = {int(k): v for k, v in id_map_str.items()}
        else:
            self.id_map = {}
        
        # 加载元数据
        if os.path.exists(self.metadata_file):
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                # JSON 的 key 是字符串，需要转换为整数
                metadata_str = json.load(f)
                self.metadata = {int(k): v for k, v in metadata_str.items()}
        else:
            self.metadata = {}
        
        # 计算下一个 vector_id
        self.next_vector_id = max(self.id_map.keys()) + 1 if self.id_map else 0
        
        logger.info(f"Loaded index with {self.index.ntotal} vectors, {len(self.id_map)} ID mappings")
    
    def save(self):
        """保存索引到文件"""
        try:
            # 保存 FAISS 索引
            faiss.write_index(self.index, self.index_file)
            
            # 保存 ID 映射
            with open(self.id_map_file, 'w', encoding='utf-8') as f:
                json.dump(self.id_map, f, ensure_ascii=False, indent=2)
            
            # 保存元数据
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Saved FAISS index with {self.index.ntotal} vectors to {self.index_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to save FAISS index: {e}")
            return False
    
    def add(
        self, 
        entry_id: int, 
        embedding: np.ndarray, 
        metadata: Dict[str, Any]
    ) -> bool:
        """
        添加向量到索引
        
        Args:
            entry_id: 条目ID（知识库条目或报告的ID）
            embedding: 向量表示（numpy array）
            metadata: 元数据（包含 title, category, tags, source, is_deleted 等）
        
        Returns:
            bool: 是否添加成功
        """
        try:
            # 确保向量是正确的形状
            if embedding.ndim == 1:
                embedding = embedding.reshape(1, -1)
            
            # 检查维度
            if embedding.shape[1] != self.dimension:
                logger.error(f"Embedding dimension mismatch: expected {self.dimension}, got {embedding.shape[1]}")
                return False
            
            # 归一化向量（用于余弦相似度）
            faiss.normalize_L2(embedding)
            
            # 添加到索引
            self.index.add(embedding.astype('float32'))
            
            # 记录映射
            vector_id = self.next_vector_id
            self.id_map[vector_id] = entry_id
            self.metadata[entry_id] = metadata
            self.next_vector_id += 1
            
            # 保存到文件
            self.save()
            
            logger.info(f"Added vector for entry_id={entry_id}, vector_id={vector_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to add vector for entry_id={entry_id}: {e}")
            return False
    
    def add_batch(
        self, 
        entries: List[Dict[str, Any]]
    ) -> int:
        """
        批量添加向量
        
        Args:
            entries: 条目列表，每个条目包含 entry_id, embedding, metadata
        
        Returns:
            int: 成功添加的数量
        """
        success_count = 0
        
        for entry in entries:
            entry_id = entry.get("entry_id")
            embedding = entry.get("embedding")
            metadata = entry.get("metadata", {})
            
            if entry_id is None or embedding is None:
                logger.warning(f"Skipping entry with missing entry_id or embedding")
                continue
            
            if self.add(entry_id, embedding, metadata):
                success_count += 1
        
        logger.info(f"Batch add completed: {success_count}/{len(entries)} successful")
        return success_count
    
    def search(
        self, 
        query_embedding: np.ndarray, 
        top_k: int = 5,
        filter_func: Optional[callable] = None,
        similarity_threshold: float = 0.0,
        filter_deleted: bool = True
    ) -> List[Dict[str, Any]]:
        """
        向量检索
        
        实现需求：
        - Requirements 13.6: 返回最相关的 Top-K 报告片段（K ≤ 5）并按相似度排序
        - Requirements 22.2: 在 Vector_Store 中检索最相关的 Top-K 知识条目（K ≤ 3）
        - Requirements 22.4: 知识条目相似度分数低于阈值（< 0.6）不返回该条目
        - Requirements 20.6: 向量检索时自动过滤 is_deleted=true 的条目
        
        Args:
            query_embedding: 查询向量（numpy array）
            top_k: 返回结果数量，默认5（报告检索）或3（知识库检索）
            filter_func: 自定义过滤函数，接收 metadata 返回 bool
            similarity_threshold: 相似度阈值，低于此值的结果将被过滤，默认0.0（不过滤）
                                 知识库检索建议设置为0.6（Requirements 22.4）
            filter_deleted: 是否自动过滤已删除的条目（is_deleted=true），默认True
        
        Returns:
            List[Dict]: 检索结果列表，按相似度降序排序，每个结果包含：
                - entry_id: 条目ID
                - similarity: 相似度分数（余弦相似度，范围0-1）
                - metadata: 元数据字典
        
        Examples:
            # 报告检索（Top-5，无相似度阈值）
            results = vector_store.search(query_embedding, top_k=5)
            
            # 知识库检索（Top-3，相似度阈值0.6）
            results = vector_store.search(
                query_embedding, 
                top_k=3, 
                similarity_threshold=0.6
            )
            
            # 自定义过滤（例如仅检索特定分类）
            results = vector_store.search(
                query_embedding,
                top_k=5,
                filter_func=lambda m: m.get("category") == "故障处理"
            )
        """
        try:
            # 检查索引是否为空
            if self.index is None or self.index.ntotal == 0:
                logger.warning("Vector store is empty, returning empty results")
                return []
            
            # 确保向量是正确的形状
            if query_embedding.ndim == 1:
                query_embedding = query_embedding.reshape(1, -1)
            
            # 检查维度
            if query_embedding.shape[1] != self.dimension:
                logger.error(f"Query embedding dimension mismatch: expected {self.dimension}, got {query_embedding.shape[1]}")
                return []
            
            # 归一化查询向量（用于余弦相似度计算）
            faiss.normalize_L2(query_embedding)
            
            # 搜索（返回更多结果以便过滤）
            # 如果有过滤条件，搜索更多结果以确保过滤后仍有足够的结果
            has_filters = filter_func is not None or filter_deleted or similarity_threshold > 0
            search_k = min(top_k * 3, self.index.ntotal) if has_filters else top_k
            search_k = max(1, search_k)  # 确保至少搜索 1 个结果
            distances, indices = self.index.search(query_embedding.astype('float32'), search_k)
            
            # 构建结果
            results = []
            for i, (distance, vector_id) in enumerate(zip(distances[0], indices[0])):
                # 跳过无效的索引
                if vector_id == -1:
                    continue
                
                # 获取 entry_id
                entry_id = self.id_map.get(int(vector_id))
                if entry_id is None:
                    logger.warning(f"No entry_id found for vector_id={vector_id}")
                    continue
                
                # 获取元数据
                metadata = self.metadata.get(entry_id, {})
                
                # 相似度分数（FAISS IndexFlatIP 返回的是内积，归一化后等于余弦相似度）
                similarity = float(distance)
                
                # 应用相似度阈值过滤（Requirements 22.4）
                if similarity < similarity_threshold:
                    continue
                
                # 自动过滤已删除的条目（Requirements 20.6, 22.2）
                if filter_deleted and metadata.get("is_deleted", False):
                    continue
                
                # 应用自定义过滤器
                if filter_func and not filter_func(metadata):
                    continue
                
                # 添加到结果
                results.append({
                    "entry_id": entry_id,
                    "similarity": similarity,
                    "metadata": metadata
                })
                
                # 达到 top_k 后停止
                if len(results) >= top_k:
                    break
            
            logger.info(f"Search completed: found {len(results)} results (threshold={similarity_threshold}, filter_deleted={filter_deleted})")
            return results
        
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def update_metadata(self, entry_id: int, metadata: Dict[str, Any]) -> bool:
        """
        更新条目的元数据
        
        Args:
            entry_id: 条目ID
            metadata: 新的元数据
        
        Returns:
            bool: 是否更新成功
        """
        try:
            if entry_id not in self.metadata:
                logger.warning(f"Entry {entry_id} not found in metadata")
                return False
            
            # 更新元数据
            self.metadata[entry_id].update(metadata)
            
            # 保存到文件
            self.save()
            
            logger.info(f"Updated metadata for entry_id={entry_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to update metadata for entry_id={entry_id}: {e}")
            return False
    
    def mark_deleted(self, entry_id: int) -> bool:
        """
        标记条目为已删除（软删除）
        
        Args:
            entry_id: 条目ID
        
        Returns:
            bool: 是否标记成功
        """
        return self.update_metadata(entry_id, {"is_deleted": True})
    
    def get_metadata(self, entry_id: int) -> Optional[Dict[str, Any]]:
        """
        获取条目的元数据
        
        Args:
            entry_id: 条目ID
        
        Returns:
            Optional[Dict]: 元数据，如果不存在返回 None
        """
        return self.metadata.get(entry_id)
    
    def delete(self, entry_id: int) -> bool:
        """
        物理删除条目（注意：FAISS 不支持直接删除，这里只删除映射和元数据）
        
        Args:
            entry_id: 条目ID
        
        Returns:
            bool: 是否删除成功
        """
        try:
            # 找到对应的 vector_id
            vector_id = None
            for vid, eid in self.id_map.items():
                if eid == entry_id:
                    vector_id = vid
                    break
            
            if vector_id is None:
                logger.warning(f"Entry {entry_id} not found in id_map")
                return False
            
            # 删除映射和元数据
            del self.id_map[vector_id]
            if entry_id in self.metadata:
                del self.metadata[entry_id]
            
            # 保存到文件
            self.save()
            
            logger.info(f"Deleted entry_id={entry_id}, vector_id={vector_id}")
            logger.warning("Note: FAISS index still contains the vector. Consider rebuilding index periodically.")
            return True
        
        except Exception as e:
            logger.error(f"Failed to delete entry_id={entry_id}: {e}")
            return False
    
    def rebuild_index(self, entries: List[Dict[str, Any]]) -> bool:
        """
        从条目列表重建索引（用于清理已删除的向量）
        
        Args:
            entries: 条目列表，每个条目包含 entry_id, embedding, metadata
        
        Returns:
            bool: 是否重建成功
        """
        try:
            logger.info(f"Rebuilding index with {len(entries)} entries")
            
            # 创建新索引
            self._create_new_index()
            
            # 批量添加
            success_count = self.add_batch(entries)
            
            logger.info(f"Index rebuilt: {success_count}/{len(entries)} entries added")
            return success_count == len(entries)
        
        except Exception as e:
            logger.error(f"Failed to rebuild index: {e}")
            return False
    
    def health_check(self) -> Dict[str, Any]:
        """
        健康检查
        
        Returns:
            Dict: 健康状态信息
        """
        try:
            status = {
                "status": "healthy",
                "index_type": type(self.index).__name__,
                "dimension": self.dimension,
                "total_vectors": self.index.ntotal if self.index else 0,
                "total_entries": len(self.metadata),
                "id_mappings": len(self.id_map),
                "index_file_exists": os.path.exists(self.index_file),
                "id_map_file_exists": os.path.exists(self.id_map_file),
                "metadata_file_exists": os.path.exists(self.metadata_file),
            }
            
            # 检查一致性
            if status["total_vectors"] != status["id_mappings"]:
                status["warning"] = "Vector count and ID mapping count mismatch"
            
            return status
        
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    def clear(self) -> bool:
        """
        清空索引（谨慎使用）
        
        Returns:
            bool: 是否清空成功
        """
        try:
            self._create_new_index()
            self.save()
            logger.warning("Vector store cleared")
            return True
        except Exception as e:
            logger.error(f"Failed to clear vector store: {e}")
            return False


# 创建全局实例（单例模式）
_vector_store_instance: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """
    获取向量存储实例（单例模式）
    
    Returns:
        VectorStore: 向量存储实例
    """
    global _vector_store_instance
    
    if _vector_store_instance is None:
        _vector_store_instance = VectorStore()
    
    return _vector_store_instance
