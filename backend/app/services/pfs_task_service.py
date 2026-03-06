#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PFS 任务管理服务
继承 PrometheusTaskService，提供 PFS 导出任务的创建和管理
"""
import json
import csv
import io
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from app.services.prometheus_task_service import PrometheusTaskService
from app.models.task import TaskType
from app.core.minio_client import get_minio_client
from app.core.logger import logger


class PFSTaskService(PrometheusTaskService):
    """PFS 任务服务类 - 继承三层存储架构"""
    
    def __init__(self, db: Session, user_id: int = None, username: str = None):
        """
        初始化 PFS 任务服务
        
        Args:
            db: 数据库会话
            user_id: 用户 ID
            username: 用户名
        """
        super().__init__(db, user_id, username)
        logger.info("✅ PFS 任务服务初始化完成")
    
    def create_pfs_export_task(
        self,
        task_id: str,
        total_metrics: int,
        message: str = "PFS 数据导出任务已创建"
    ):
        """
        创建 PFS 导出任务
        
        Args:
            task_id: 任务 ID
            total_metrics: 指标总数
            message: 任务消息
        
        Returns:
            Task 对象
        """
        return self.create_task(
            task_id=task_id,
            task_type=TaskType.PFS_EXPORT,
            total_clusters=total_metrics,  # 复用 total_clusters 字段存储指标数量
            message=message
        )
    
    def complete_pfs_export_task(
        self,
        task_id: str,
        export_data: List[Dict[str, Any]],
        format: str = "csv"
    ) -> Optional[str]:
        """
        完成 PFS 导出任务并上传到 MinIO
        
        Args:
            task_id: 任务 ID
            export_data: 导出数据列表
            format: 导出格式 ("csv" / "json")
        
        Returns:
            MinIO 文件 URL
        """
        try:
            # 1. 生成导出文件
            if format == "csv":
                file_content = self._generate_csv(export_data)
                file_name = f"pfs_results/{task_id}.csv"
                content_type = "text/csv"
            else:
                file_content = json.dumps(export_data, indent=2, ensure_ascii=False).encode('utf-8')
                file_name = f"pfs_results/{task_id}.json"
                content_type = "application/json"
            
            logger.info(f"✅ 生成导出文件：{file_name}，大小：{len(file_content)} 字节")
            
            # 2. 上传到 MinIO
            minio_client = get_minio_client()
            result_url = minio_client.upload_data(
                data=file_content,
                object_name=file_name,
                content_type=content_type
            )
            logger.info(f"✅ 文件已上传到 MinIO：{file_name}")
            
            # 3. 构建结果数据
            result_data = {
                "task_id": task_id,
                "format": format,
                "file_name": file_name,
                "file_url": result_url,
                "total_records": len(export_data),
                "file_size": len(file_content),
                "created_at": datetime.now().isoformat()
            }
            
            # 4. 更新任务状态（调用父类方法）
            # 注意：父类的 complete_task 会再次上传 result_data 到 MinIO
            # 这里我们直接更新数据库和 Redis，不使用父类的上传逻辑
            task = self.db.query(self.db.query(Task).filter(Task.id == task_id).first().__class__).filter_by(id=task_id).first()
            if task:
                from app.models.task import TaskStatus
                task.status = TaskStatus.COMPLETED
                task.progress = 100
                task.completed_items = task.total_items
                task.message = f'PFS 数据导出完成，共 {len(export_data)} 条记录'
                task.result_path = file_name
                task.result_url = result_url
                task.completed_at = datetime.now()
                self.db.commit()
                logger.info(f"✅ 任务已标记完成（MySQL）：{task_id}")
            
            # 5. 更新 Redis
            from app.utils.task_manager import save_task_status
            import time
            redis_status = {
                'status': 'completed',
                'message': f'PFS 数据导出完成，共 {len(export_data)} 条记录',
                'progress': 100,
                'total_clusters': len(export_data),
                'completed_clusters': len(export_data),
                'result_file': f"{task_id}.{format}",
                'result_url': result_url,
                'format': format,
                'file_size': len(file_content),
                'timestamp': time.strftime("%Y-%m-%d %H:%M:%S")
            }
            save_task_status(task_id, redis_status, expire=86400)
            logger.info(f"✅ 任务状态已更新（Redis）：{task_id}")
            
            return result_url
            
        except Exception as e:
            logger.error(f"❌ 完成 PFS 导出任务失败：{e}")
            self.fail_task(task_id, str(e))
            raise
    
    def _generate_csv(self, export_data: List[Dict[str, Any]]) -> bytes:
        """
        生成 CSV 文件内容
        
        Args:
            export_data: 导出数据列表
        
        Returns:
            CSV 文件内容（字节）
        """
        if not export_data:
            return b""
        
        # 使用 StringIO 生成 CSV
        output = io.StringIO()
        
        # 定义 CSV 列（中文列名）
        fieldnames = [
            "时间",
            "指标英文名",
            "指标中文名",
            "指标说明",
            "数值",
            "单位",
            "正常范围",
            "客户端 ID",
            "客户端 IP",
            "标签"
        ]
        
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        # 写入数据行
        for row in export_data:
            writer.writerow({
                "时间": row.get("timestamp", ""),
                "指标英文名": row.get("metric_name", ""),
                "指标中文名": row.get("zh_name", ""),
                "指标说明": row.get("desc", ""),
                "数值": row.get("value", ""),
                "单位": row.get("unit_zh", ""),
                "正常范围": row.get("normal_range", ""),
                "客户端 ID": row.get("client_id", ""),
                "客户端 IP": row.get("client_ip", ""),
                "标签": row.get("labels", "")
            })
        
        # 转换为字节（UTF-8 with BOM，支持 Excel 打开）
        csv_content = output.getvalue()
        return b'\xef\xbb\xbf' + csv_content.encode('utf-8')
    
    def update_export_progress(
        self,
        task_id: str,
        completed_metrics: int,
        total_metrics: int,
        current_metric: str = None
    ):
        """
        更新导出任务进度
        
        Args:
            task_id: 任务 ID
            completed_metrics: 已完成指标数
            total_metrics: 总指标数
            current_metric: 当前处理的指标名称
        """
        message = f"正在导出 {completed_metrics}/{total_metrics} 个指标"
        if current_metric:
            message += f"（当前：{current_metric}）"
        
        self.update_progress(
            task_id=task_id,
            completed=completed_metrics,
            total=total_metrics,
            message=message
        )
    
    def get_pfs_export_history(
        self,
        skip: int = 0,
        limit: int = 20,
        user_id: int = None
    ):
        """
        查询 PFS 导出任务历史
        
        Args:
            skip: 跳过数量
            limit: 返回数量
            user_id: 用户 ID 筛选
        
        Returns:
            任务列表
        """
        return self.get_task_history(
            skip=skip,
            limit=limit,
            task_type=TaskType.PFS_EXPORT,
            user_id=user_id
        )
