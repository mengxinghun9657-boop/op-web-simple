#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
报告自动向量化服务（后台任务）

实现需求：
- Requirements 14.1: 新的分析报告上传到 MinIO 时自动触发报告向量化流程
- Requirements 14.8: 向量化失败时记录错误日志但不影响报告的正常存储和访问
- Requirements 14.9: 报告向量化成功时自动创建对应的知识条目并标记 source 为 "auto"
- Requirements 14.10: 自动创建的知识条目设置 auto_generated 字段为 true 并记录 source_id 为任务 ID
- Requirements 14.11: 创建知识条目时将内容按层级存储：title（摘要）、content（关键结论）、metadata（详细数据的引用路径）
"""

import asyncio
import json
from typing import Dict, Optional, List
from datetime import datetime
from pathlib import Path

from app.core.logger import logger
from app.core.minio_client import get_minio_client
from app.services.ai.report_retriever import ReportRetriever
from app.services.ai.embedding_model import EmbeddingModel
from app.services.ai.vector_store import VectorStore
from app.core.database import get_db_connection


class ReportVectorizationService:
    """
    报告自动向量化服务
    
    功能：
    1. 监听 MinIO 新报告上传事件（通过定时扫描或事件触发）
    2. 自动触发报告向量化流程
    3. 自动创建知识库条目（source=auto）
    4. 记录向量化失败日志
    """
    
    def __init__(
        self,
        embedding_model: Optional[EmbeddingModel] = None,
        vector_store: Optional[VectorStore] = None,
        report_retriever: Optional[ReportRetriever] = None
    ):
        """
        初始化报告向量化服务
        
        Args:
            embedding_model: Embedding 模型
            vector_store: 向量存储
            report_retriever: 报告检索器
        """
        self.minio_client = get_minio_client()
        self.embedding_model = embedding_model or EmbeddingModel()
        self.vector_store = vector_store or VectorStore(
            index_path="/app/vector_store/reports"
        )
        self.report_retriever = report_retriever or ReportRetriever(
            embedding_model=self.embedding_model,
            vector_store=self.vector_store
        )
        
        logger.info("✅ 报告向量化服务初始化成功")
    
    async def vectorize_report(
        self,
        task_id: str,
        report_type: str,
        file_path: str,
        generated_at: datetime
    ) -> bool:
        """
        向量化单个报告（带分布式锁防止并发）
        
        Args:
            task_id: 任务ID
            report_type: 报告类型
            file_path: MinIO 文件路径
            generated_at: 报告生成时间
        
        Returns:
            bool: 是否成功
        
        Validates:
            - Requirements 14.1: 自动触发报告向量化流程
            - Requirements 14.8: 向量化失败时记录错误日志
            - Requirements 14.9, 14.10, 14.11: 自动创建知识条目
        """
        # 使用 Redis 分布式锁防止并发
        lock_key = f"vectorize_lock:{task_id}"
        lock_timeout = 60  # 60 秒超时
        
        try:
            # 尝试获取锁
            from app.core.redis_client import get_redis_client
            redis_client = get_redis_client()
            
            # SET NX EX：如果 key 不存在则设置，并设置过期时间
            lock_acquired = redis_client.set(lock_key, "1", nx=True, ex=lock_timeout)
            
            if not lock_acquired:
                logger.info(f"⏭️ 其他进程正在处理该报告，跳过: {task_id}")
                return True  # 返回 True 表示不需要重试
            
            logger.info(f"📝 开始向量化报告 - task_id: {task_id}, type: {report_type}")
            
            # 1. 从 MinIO 下载报告内容
            report_content = await self._download_report_from_minio(file_path)
            if not report_content:
                logger.error(f"❌ 无法从 MinIO 下载报告: {file_path}")
                await self._log_vectorization_failure(
                    task_id, report_type, "Failed to download report from MinIO"
                )
                return False
            
            # 2. 提取报告内容层级（摘要层、结论层、详情层）
            content_layers = self._extract_content_layers(
                content=report_content,
                report_type=report_type
            )
            
            # 3. 向量化摘要层和结论层
            content_text = f"{content_layers['summary']}\n\n{content_layers['conclusion']}"
            embedding = await self.embedding_model.encode(content_text)
            
            # 4. 存储到向量数据库
            vector_id = f"report_{task_id}"
            success = self.vector_store.add(
                entry_id=hash(task_id),  # 使用 task_id 的哈希作为 entry_id
                embedding=embedding,
                metadata={
                    "task_id": task_id,
                    "report_type": report_type,
                    "file_path": file_path,
                    "generated_at": generated_at.isoformat(),
                    "indexed_at": datetime.now().isoformat(),
                    "type": "report",
                    "is_deleted": False
                }
            )
            
            if not success:
                logger.error(f"❌ 向量存储失败: {task_id}")
                await self._log_vectorization_failure(
                    task_id, report_type, "Failed to store vector"
                )
                return False
            
            # 5. 更新 MySQL report_index 表
            await self._update_report_index(
                task_id=task_id,
                report_type=report_type,
                file_path=file_path,
                generated_at=generated_at,
                summary=content_layers['summary'],
                conclusion=content_layers['conclusion'],
                vector_id=vector_id
            )
            
            # 6. 自动创建知识库条目（Requirements 14.9, 14.10, 14.11）
            knowledge_entry_id = await self._create_knowledge_entry(
                task_id=task_id,
                report_type=report_type,
                content_layers=content_layers,
                generated_at=generated_at
            )
            
            if knowledge_entry_id:
                logger.info(f"✅ 报告向量化完成: {task_id}, 知识条目ID: {knowledge_entry_id}")
            else:
                logger.warning(f"⚠️ 报告向量化完成但知识条目创建失败: {task_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 报告向量化失败: {task_id}, 错误: {e}")
            await self._log_vectorization_failure(
                task_id, report_type, str(e)
            )
            return False
        
        finally:
            # 释放锁
            try:
                redis_client.delete(lock_key)
                logger.debug(f"🔓 释放锁: {lock_key}")
            except Exception as e:
                logger.warning(f"⚠️ 释放锁失败: {lock_key}, 错误: {e}")
    
    async def _download_report_from_minio(self, file_path: str) -> Optional[str]:
        """
        从 MinIO 下载报告内容
        
        Args:
            file_path: MinIO 文件路径
        
        Returns:
            Optional[str]: 报告内容（文本）
        """
        try:
            # 下载文件内容
            file_data = self.minio_client.download_data(file_path)
            
            # 根据文件类型解析内容
            if file_path.endswith('.html'):
                # HTML 文件：提取文本内容
                html_content = file_data.decode('utf-8')
                text_content = self._extract_text_from_html(html_content)
                return text_content
            elif file_path.endswith('.json'):
                # JSON 文件：解析 JSON
                content = file_data.decode('utf-8')
                return content
            else:
                logger.warning(f"⚠️ 不支持的文件格式: {file_path}")
                return None
        
        except Exception as e:
            logger.error(f"❌ 下载报告失败: {file_path}, 错误: {e}")
            return None
    
    def _extract_text_from_html(self, html_content: str) -> str:
        """
        从 HTML 内容中提取纯文本
        
        Args:
            html_content: HTML 内容
        
        Returns:
            str: 提取的纯文本
        """
        try:
            from bs4 import BeautifulSoup
            import re
            
            # 使用 BeautifulSoup 解析 HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 移除 script 和 style 标签
            for script in soup(['script', 'style']):
                script.decompose()
            
            # 获取文本
            text = soup.get_text()
            
            # 清理多余的空白和换行
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            return text
            
        except ImportError:
            logger.warning("⚠️ BeautifulSoup 未安装，使用正则表达式提取 HTML 文本")
            # 备选方案：使用正则表达式
            import re
            # 移除 HTML 标签
            text = re.sub(r'<[^>]+>', '', html_content)
            # 移除多余空白
            text = re.sub(r'\s+', ' ', text).strip()
            return text
        
        except Exception as e:
            logger.error(f"❌ 提取 HTML 文本失败: {e}")
            return html_content  # 返回原始内容作为备选
    
    def _extract_content_layers(
        self,
        content: str,
        report_type: str
    ) -> Dict[str, str]:
        """
        提取报告内容层级
        
        Args:
            content: 报告内容
            report_type: 报告类型
        
        Returns:
            Dict: 分层内容（summary, conclusion, details）
        
        Validates: Requirements 14.2, 14.3
        """
        # 使用 ReportRetriever 的内容提取方法
        return self.report_retriever.extract_content_layers(
            content=content,
            report_type=report_type
        )
    
    async def _update_report_index(
        self,
        task_id: str,
        report_type: str,
        file_path: str,
        generated_at: datetime,
        summary: str,
        conclusion: str,
        vector_id: str
    ) -> bool:
        """
        更新 MySQL report_index 表
        
        Args:
            task_id: 任务ID
            report_type: 报告类型
            file_path: 文件路径
            generated_at: 生成时间
            summary: 摘要
            conclusion: 结论
            vector_id: 向量ID
        
        Returns:
            bool: 是否成功
        
        Validates: Requirements 14.4
        """
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # 确定文件格式
            file_format = 'html' if file_path.endswith('.html') else 'json'
            
            # 使用 INSERT ... ON DUPLICATE KEY UPDATE 避免并发冲突
            cursor.execute("""
                INSERT INTO report_index
                (task_id, report_type, file_path, file_format, summary, conclusion,
                 generated_at, vectorized, vector_id, indexed_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE, %s, NOW())
                ON DUPLICATE KEY UPDATE
                    summary = VALUES(summary),
                    conclusion = VALUES(conclusion),
                    vectorized = TRUE,
                    vector_id = VALUES(vector_id),
                    indexed_at = NOW()
            """, (
                task_id, report_type, file_path, file_format,
                summary, conclusion, generated_at, vector_id
            ))
            
            conn.commit()
            
            logger.info(f"✅ 更新 report_index 成功: {task_id}")
            return True
            
        except Exception as e:
            # 捕获 Duplicate entry 错误，视为成功（数据已存在）
            error_msg = str(e)
            if 'Duplicate entry' in error_msg and 'task_id' in error_msg:
                logger.warning(f"⚠️ 报告索引已存在（并发插入），跳过: {task_id}")
                return True
            
            # 其他错误记录日志并返回失败
            logger.error(f"❌ 更新 report_index 失败: {task_id}, 错误: {e}")
            return False
        finally:
            if cursor is not None:
                try:
                    cursor.close()
                except Exception as e:
                    logger.warning(f"⚠️ 关闭游标失败: {e}")
            if conn is not None:
                try:
                    conn.close()
                except Exception as e:
                    logger.warning(f"⚠️ 关闭数据库连接失败: {e}")
    
    async def _create_knowledge_entry(
        self,
        task_id: str,
        report_type: str,
        content_layers: Dict[str, str],
        generated_at: datetime
    ) -> Optional[int]:
        """
        自动创建知识库条目（防止重复创建）
        
        Args:
            task_id: 任务ID
            report_type: 报告类型
            content_layers: 内容层级
            generated_at: 生成时间
        
        Returns:
            Optional[int]: 知识条目ID，失败返回 None
        
        Validates:
            - Requirements 14.9: 自动创建知识条目并标记 source 为 "auto"
            - Requirements 14.10: 设置 auto_generated=true 并记录 source_id 为任务 ID
            - Requirements 14.11: 按层级存储：title（摘要）、content（关键结论）、metadata（详细数据）
        """
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # 1. 检查是否已存在相同 source_id 的知识条目（防止重复创建）
            cursor.execute("""
                SELECT id FROM knowledge_entries
                WHERE source = 'auto' AND source_id = %s AND deleted_at IS NULL
                LIMIT 1
            """, (task_id,))
            
            existing = cursor.fetchone()
            if existing:
                knowledge_entry_id = existing[0]
                logger.info(f"⏭️ 知识条目已存在，跳过创建: ID={knowledge_entry_id}, task_id={task_id}")
                return knowledge_entry_id
            
            # 2. 生成标题
            report_type_names = {
                'resource_analysis': '资源分析',
                'bcc_monitoring': 'BCC 监控',
                'bos_monitoring': 'BOS 监控',
                'operational_analysis': '运营分析'
            }
            report_type_name = report_type_names.get(report_type, report_type)
            title = f"{report_type_name} - {generated_at.strftime('%Y-%m-%d')}"
            
            # 3. 准备元数据（详情层）
            metadata = {
                "detail_level": "summary_and_conclusion",
                "full_report_url": f"/cluster-files/{content_layers.get('file_path', '')}",
                "detailed_data": content_layers.get('details', {})
            }
            
            # 4. 插入知识条目
            cursor.execute("""
                INSERT INTO knowledge_entries
                (title, content, metadata, category, tags, priority,
                 source, source_type, source_id, author, auto_generated)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                title,
                content_layers['conclusion'],  # content 字段存储结论层
                json.dumps(metadata, ensure_ascii=False),  # metadata 字段存储详情层
                '分析报告',  # category
                json.dumps([report_type_name, task_id], ensure_ascii=False),  # tags
                'medium',  # priority
                'auto',  # source
                report_type,  # source_type
                task_id,  # source_id
                'system',  # author
                True  # auto_generated
            ))
            
            knowledge_entry_id = cursor.lastrowid
            
            conn.commit()
            
            logger.info(f"✅ 创建知识条目成功: ID={knowledge_entry_id}, task_id={task_id}")
            return knowledge_entry_id
            
        except Exception as e:
            logger.error(f"❌ 创建知识条目失败: {task_id}, 错误: {e}")
            return None
        finally:
            if cursor is not None:
                try:
                    cursor.close()
                except Exception as close_err:
                    logger.warning(f"⚠️ 关闭游标失败: {close_err}")
            if conn is not None:
                try:
                    conn.close()
                except Exception as close_err:
                    logger.warning(f"⚠️ 关闭数据库连接失败: {close_err}")
    
    async def _log_vectorization_failure(
        self,
        task_id: str,
        report_type: str,
        error_message: str
    ):
        """
        记录向量化失败日志
        
        Args:
            task_id: 任务ID
            report_type: 报告类型
            error_message: 错误信息
        
        Validates: Requirements 14.8
        """
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # 记录到审计日志
            cursor.execute("""
                INSERT INTO ai_audit_logs
                (user_id, username, action_type, execution_status, error_message,
                 knowledge_operation)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                'system',
                'system',
                'knowledge_create',
                'error',
                error_message,
                json.dumps({
                    'operation': 'auto_vectorization',
                    'task_id': task_id,
                    'report_type': report_type
                }, ensure_ascii=False)
            ))
            
            conn.commit()
            
            logger.info(f"✅ 记录向量化失败日志: {task_id}")
            
        except Exception as e:
            logger.error(f"❌ 记录失败日志失败: {e}")
        finally:
            if cursor is not None:
                try:
                    cursor.close()
                except Exception as e:
                    logger.warning(f"⚠️ 关闭游标失败: {e}")
            if conn is not None:
                try:
                    conn.close()
                except Exception as e:
                    logger.warning(f"⚠️ 关闭数据库连接失败: {e}")
    
    async def scan_and_vectorize_new_reports(self) -> Dict[str, int]:
        """
        扫描 MinIO 中的新报告并向量化
        
        Returns:
            Dict: 统计信息（成功数、失败数）
        
        Validates: Requirements 14.1
        """
        stats = {
            'scanned': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0
        }
        
        try:
            logger.info("🔍 开始扫描 MinIO 中的新报告...")
            
            # 获取已向量化的报告列表
            vectorized_task_ids = await self._get_vectorized_task_ids()
            
            # 扫描 MinIO 中的报告文件
            report_prefixes = [
                'html_reports/resource/',
                'html_reports/bcc/',
                'html_reports/bos/',
                'html_reports/operational/'
            ]
            
            for prefix in report_prefixes:
                # 列出该目录下的所有文件
                objects = self.minio_client.list_objects(prefix=prefix)
                
                for object_name in objects:
                    stats['scanned'] += 1
                    
                    # 解析文件名获取 task_id 和 report_type
                    task_id, report_type = self._parse_report_filename(object_name)
                    
                    if not task_id or not report_type:
                        logger.warning(f"⚠️ 无法解析文件名: {object_name}")
                        stats['skipped'] += 1
                        continue
                    
                    # 检查是否已向量化
                    if task_id in vectorized_task_ids:
                        logger.debug(f"⏭️ 报告已向量化，跳过: {task_id}")
                        stats['skipped'] += 1
                        continue
                    
                    # 向量化报告
                    success = await self.vectorize_report(
                        task_id=task_id,
                        report_type=report_type,
                        file_path=object_name,
                        generated_at=datetime.now()  # TODO: 从文件元数据获取实际生成时间
                    )
                    
                    if success:
                        stats['success'] += 1
                    else:
                        stats['failed'] += 1
            
            logger.info(f"✅ 扫描完成: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"❌ 扫描失败: {e}")
            return stats
    
    async def _get_vectorized_task_ids(self) -> set:
        """
        获取已向量化的报告 task_id 列表
        
        Returns:
            set: task_id 集合
        """
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT task_id
                FROM report_index
                WHERE vectorized = TRUE
            """)
            
            task_ids = {row[0] for row in cursor.fetchall()}
            
            return task_ids
            
        except Exception as e:
            logger.error(f"❌ 获取已向量化报告列表失败: {e}")
            return set()
        finally:
            if cursor is not None:
                try:
                    cursor.close()
                except Exception as e:
                    logger.warning(f"⚠️ 关闭游标失败: {e}")
            if conn is not None:
                try:
                    conn.close()
                except Exception as e:
                    logger.warning(f"⚠️ 关闭数据库连接失败: {e}")
    
    def _parse_report_filename(self, filename: str) -> tuple:
        """
        解析报告文件名获取 task_id 和 report_type
        
        支持多种文件名格式：
        1. task_12345_resource_report.html (旧格式)
        2. analysis-72741ae5_resource_report.html (新格式)
        3. 602df520-81b0-41f1-b8e0-40edd6a5c759_operational_report.html (UUID格式)
        
        Args:
            filename: 文件名，例如 "html_reports/resource/analysis-72741ae5_resource_report.html"
        
        Returns:
            tuple: (task_id, report_type)
        """
        try:
            # 提取文件名部分
            basename = Path(filename).stem  # 例如 "analysis-72741ae5_resource_report"
            
            # 解析 task_id 和 report_type
            parts = basename.split('_')
            
            if len(parts) < 2:
                logger.warning(f"⚠️ 文件名格式不正确（分段不足）: {filename}")
                return None, None
            
            # 提取 task_id（第一部分，可能包含连字符）
            task_id = parts[0]
            
            # 提取 report_type（倒数第二部分，因为最后一部分是 "report"）
            if len(parts) >= 3 and parts[-1] == 'report':
                report_type = parts[-2]
            elif len(parts) >= 2:
                # 如果没有 "report" 后缀，取最后一部分
                report_type = parts[-1]
            else:
                logger.warning(f"⚠️ 无法提取报告类型: {filename}")
                return None, None
            
            # 映射报告类型
            report_type_map = {
                'resource': 'resource_analysis',
                'bcc': 'bcc_monitoring',
                'bos': 'bos_monitoring',
                'operational': 'operational_analysis'
            }
            
            report_type = report_type_map.get(report_type, report_type)
            
            # 如果 task_id 不是以 task_ 开头，添加前缀
            if not task_id.startswith('task_'):
                task_id = f"task_{task_id}"
            
            logger.debug(f"✅ 解析文件名成功: {filename} -> task_id={task_id}, report_type={report_type}")
            
            return task_id, report_type
            
        except Exception as e:
            logger.error(f"❌ 解析文件名失败: {filename}, 错误: {e}")
            return None, None


# 全局实例（可选）
_vectorization_service = None


def get_vectorization_service() -> ReportVectorizationService:
    """获取报告向量化服务实例"""
    global _vectorization_service
    
    if _vectorization_service is None:
        _vectorization_service = ReportVectorizationService()
    
    return _vectorization_service


# 后台任务：定期扫描和向量化新报告
async def background_vectorization_task(interval_seconds: int = 300):
    """
    后台任务：定期扫描和向量化新报告
    
    Args:
        interval_seconds: 扫描间隔（秒），默认 5 分钟
    
    Validates: Requirements 14.1
    """
    service = get_vectorization_service()
    
    logger.info(f"🚀 启动后台向量化任务，扫描间隔: {interval_seconds} 秒")
    
    while True:
        try:
            # 扫描并向量化新报告
            stats = await service.scan_and_vectorize_new_reports()
            
            logger.info(f"📊 向量化统计: {stats}")
            
            # 等待下一次扫描
            await asyncio.sleep(interval_seconds)
            
        except Exception as e:
            logger.error(f"❌ 后台向量化任务异常: {e}")
            # 发生异常后等待一段时间再继续
            await asyncio.sleep(60)
