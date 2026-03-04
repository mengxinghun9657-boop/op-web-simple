#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
资源分析API
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File
from pydantic import BaseModel, Field
from typing import List, Optional
import os
import uuid
import time

from app.core.config import settings
from app.core.logger import logger
from app.services.resource_service import analyze_resource_data

router = APIRouter()


# ========== 请求/响应模型 ==========

class ResourceAnalysisRequest(BaseModel):
    """资源分析请求"""
    task_id: Optional[str] = Field(None, description="集群数据任务ID（引用已获取的Prometheus数据）")
    cluster_ids: Optional[List[str]] = Field(None, description="集群ID列表（用于获取Prometheus数据）")
    excel_file_name: Optional[str] = Field(None, description="已上传的Excel文件名")
    multicluster_file_name: Optional[str] = Field(None, description="已上传的Multi-Cluster JSON文件名")


class ResourceAnalysisResponse(BaseModel):
    """资源分析响应"""
    task_id: str
    status: str
    message: str


# ========== API接口 ==========

@router.post("/analyze", response_model=ResourceAnalysisResponse, summary="执行资源分析")
async def start_resource_analysis(
    request: ResourceAnalysisRequest,
    background_tasks: BackgroundTasks
):
    """
    启动资源分析任务
    
    支持四种数据源（至少提供一种）：
    1. **task_id**: 引用已获取的集群数据（来自/cluster/metrics/batch接口）
    2. **cluster_ids**: 集群ID列表，自动从Prometheus获取实时指标
    3. **excel_file_name**: 已上传的Excel文件（包含存储/网络/实例工作表）
    4. **multicluster_file_name**: 已上传的Multi-Cluster JSON文件
    
    示例1（使用已获取的数据）：
    ```json
    {
        "task_id": "batch-1765956890",
        "excel_file_name": "resource_data.xlsx"
    }
    ```
    
    示例2（实时获取）：
    ```json
    {
        "cluster_ids": ["cce-3nusu9su", "cce-9m1ht29q"],
        "excel_file_name": "resource_data.xlsx"
    }
    ```
    """
    try:
        # 验证至少提供一种数据源
        if not request.task_id and not request.cluster_ids and not request.excel_file_name and not request.multicluster_file_name:
            raise HTTPException(
                status_code=400,
                detail="至少需要提供一种数据源：task_id、cluster_ids、excel_file_name 或 multicluster_file_name"
            )
        
        from app.utils.task_id_generator import generate_analysis_task_id
        
        # 生成任务ID
        analysis_task_id = generate_analysis_task_id()
        
        # 处理task_id：查找对应的集群数据文件
        multicluster_file_path = None
        if request.task_id:
            # 先尝试本地文件
            cluster_data_file = os.path.join(settings.RESULT_DIR, f"prometheus_results/{request.task_id}.json")
            if os.path.exists(cluster_data_file):
                logger.info(f"使用本地集群数据: {cluster_data_file}")
                multicluster_file_path = cluster_data_file
            else:
                # 尝试从MinIO下载
                try:
                    from app.core.minio_client import minio_client
                    # 尝试多种可能的文件名
                    possible_names = [
                        f"prometheus_results/{request.task_id}.json",
                        f"{request.task_id}.json"
                    ]
                    for minio_filename in possible_names:
                        temp_file = os.path.join(settings.UPLOAD_DIR, f"temp_{request.task_id}.json")
                        if minio_client.download_file(minio_filename, temp_file):
                            logger.info(f"从MinIO下载集群数据: {minio_filename}")
                            multicluster_file_path = temp_file
                            break
                    
                    if not multicluster_file_path:
                        raise HTTPException(
                            status_code=404, 
                            detail=f"未找到task_id对应的集群数据文件: {request.task_id}"
                        )
                except Exception as e:
                    logger.error(f"从MinIO获取文件失败: {e}")
                    raise HTTPException(
                        status_code=404, 
                        detail=f"未找到task_id对应的集群数据文件: {request.task_id}"
                    )
        
        # 处理multicluster_file_name（优先级低于task_id）
        if request.multicluster_file_name and not multicluster_file_path:
            multicluster_file_path = os.path.join(settings.UPLOAD_DIR, request.multicluster_file_name)
            if not os.path.exists(multicluster_file_path):
                raise HTTPException(status_code=404, detail=f"Multi-Cluster文件不存在: {request.multicluster_file_name}")
        
        # 准备Excel文件路径
        excel_file_path = None
        if request.excel_file_name:
            excel_file_path = os.path.join(settings.UPLOAD_DIR, request.excel_file_name)
            if not os.path.exists(excel_file_path):
                raise HTTPException(status_code=404, detail=f"Excel文件不存在: {request.excel_file_name}")
        
        # 启动后台分析任务
        background_tasks.add_task(
            run_resource_analysis,
            task_id=analysis_task_id,
            cluster_ids=request.cluster_ids,
            excel_file_path=excel_file_path,
            multicluster_file_path=multicluster_file_path
        )
        
        # 保存任务到MySQL
        try:
            from app.services.task_service import save_task_to_db
            from app.models.task import TaskType, TaskStatus
            save_task_to_db(analysis_task_id, TaskType.RESOURCE, TaskStatus.PROCESSING, "资源分析任务已启动")
        except Exception as e:
            logger.warning(f"保存任务到MySQL失败: {e}")
        
        logger.info(f"资源分析任务已启动: {analysis_task_id}")
        
        return ResourceAnalysisResponse(
            task_id=analysis_task_id,
            status="analyzing",
            message="资源分析任务已启动"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"启动资源分析失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"启动资源分析失败: {str(e)}")


async def run_resource_analysis(
    task_id: str,
    cluster_ids: Optional[List[str]],
    excel_file_path: Optional[str],
    multicluster_file_path: Optional[str]
):
    """后台执行资源分析"""
    # 创建初始结果文件，避免前端轮询时404
    result_file = os.path.join(settings.RESULT_DIR, f"{task_id}_resource_analysis.json")
    
    def update_progress(progress: int, message: str):
        """更新进度到结果文件"""
        try:
            import json
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'task_id': task_id,
                    'status': 'processing',
                    'message': message,
                    'progress': progress
                }, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"更新进度失败: {e}")
    
    try:
        logger.info(f"开始执行资源分析: {task_id}")
        
        # 阶段1: 初始化 (10%)
        update_progress(10, '正在准备数据...')
        
        # 阶段2: 数据分析 (30%)
        update_progress(30, '正在分析集群数据...')
        
        # 执行分析
        result = await analyze_resource_data(
            task_id=task_id,
            cluster_ids=cluster_ids,
            excel_file_path=excel_file_path,
            multicluster_file_path=multicluster_file_path
        )
        
        # 阶段3: 生成AI解读 (70%)
        update_progress(70, '正在生成AI解读，请稍候...')
        
        # 阶段4: 完成 (100%)
        # 保存最终结果
        import json
        with open(result_file, 'w', encoding='utf-8') as f:
            final_result = result.copy()
            final_result['progress'] = 100
            final_result['status'] = 'completed' if result.get('success') else 'failed'
            json.dump(final_result, f, indent=2, ensure_ascii=False)
        
        # 更新任务状态到MySQL
        try:
            from app.services.task_service import update_task_status
            from app.models.task import TaskStatus
            html_report = result.get('result', {}).get('html_report') or result.get('html_report')
            update_task_status(task_id, TaskStatus.COMPLETED, "分析完成", result_url=html_report)
        except Exception as e:
            logger.warning(f"更新任务状态失败: {e}")
        
        logger.info(f"资源分析完成并保存: {result_file}")
        
    except Exception as e:
        logger.error(f"资源分析执行失败: {task_id}, 错误: {str(e)}")
        # 更新任务状态为失败
        try:
            from app.services.task_service import update_task_status
            from app.models.task import TaskStatus
            update_task_status(task_id, TaskStatus.FAILED, error_message=str(e))
        except Exception as db_error:
            logger.warning(f"[{task_id}] 更新资源分析任务失败状态到数据库失败: {db_error}")
        # 保存错误信息
        import json
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump({
                'success': False,
                'task_id': task_id,
                'status': 'failed',
                'error': str(e),
                'progress': 0
            }, f, indent=2, ensure_ascii=False)


@router.post("/cluster/metrics", summary="获取集群监控指标")
async def get_cluster_metrics(request: dict):
    """
    从Prometheus获取集群实时监控指标
    
    请求示例:
    ```json
    {
        "prometheus_url": "http://prometheus:9090",
        "time_range": "24h"
    }
    ```
    """
    try:
        prometheus_url = request.get("prometheus_url")
        time_range = request.get("time_range", "24h")
        
        if not prometheus_url:
            raise HTTPException(status_code=400, detail="缺少prometheus_url参数")
        
        # 实现Prometheus指标获取
        import aiohttp
        from datetime import datetime, timedelta
        
        # 解析时间范围
        range_mapping = {
            '1h': timedelta(hours=1),
            '6h': timedelta(hours=6),
            '24h': timedelta(hours=24),
            '7d': timedelta(days=7)
        }
        time_delta = range_mapping.get(time_range, timedelta(hours=24))
        
        # 生成时间序列
        now = datetime.now()
        time_points = []
        cpu_data = []
        memory_data = []
        network_in_data = []
        network_out_data = []
        
        # 生成模拟的时间序列数据（实际应该查询Prometheus）
        import random
        points = 20
        for i in range(points):
            t = now - time_delta + (time_delta / points * i)
            time_points.append(t.strftime('%H:%M'))
            
            # 模拟数据（实际应该从Prometheus查询）
            cpu_data.append(round(30 + random.random() * 40, 2))
            memory_data.append(round(40 + random.random() * 30, 2))
            network_in_data.append(round(500 + random.random() * 1000, 2))
            network_out_data.append(round(300 + random.random() * 800, 2))
        
        # TODO: 真实的Prometheus查询
        # async with aiohttp.ClientSession() as session:
        #     # 查询CPU使用率
        #     cpu_query = 'rate(process_cpu_seconds_total[5m]) * 100'
        #     # 查询内存使用率
        #     mem_query = '(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100'
        #     # 查询网络流量
        #     ...
        
        return {
            "success": True,
            "metrics": {
                "time": time_points,
                "cpu": cpu_data,
                "memory": memory_data,
                "network_in": network_in_data,
                "network_out": network_out_data,
                "storage": [
                    {"value": 335, "name": "已使用"},
                    {"value": 234, "name": "可用"}
                ]
            },
            "message": "指标获取成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取集群指标失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取集群指标失败: {str(e)}")


@router.get("/result/{task_id}", summary="获取分析结果")
async def get_analysis_result(task_id: str):
    """
    获取资源分析结果
    
    - **task_id**: 分析任务ID
    """
    try:
        result_file = os.path.join(settings.RESULT_DIR, f"{task_id}_resource_analysis.json")
        
        if not os.path.exists(result_file):
            raise HTTPException(status_code=404, detail="分析结果不存在")
        
        with open(result_file, 'r', encoding='utf-8') as f:
            import json
            result = json.load(f)
        
        # 获取html_report路径
        html_report_path = None
        if isinstance(result, dict):
            if 'html_report' in result and result['html_report']:
                html_report_path = result['html_report']
            elif 'result' in result and isinstance(result['result'], dict) and 'html_report' in result['result']:
                html_report_path = result['result']['html_report']
        
        # 转换为可访问的URL
        if html_report_path:
            # 如果是MinIO路径
            if html_report_path.startswith('html_reports/'):
                result['html_file'] = f"/api/v1/reports/proxy/{html_report_path}"
            # 如果是本地路径且存在
            elif os.path.exists(html_report_path):
                filename = os.path.basename(html_report_path)
                result['html_file'] = f"/reports/{filename}"
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取分析结果失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取分析结果失败: {str(e)}")


@router.post("/upload", summary="上传文件")
async def upload_file(
    file: UploadFile = File(..., description="资源数据文件（Excel或JSON）")
):
    """
    上传文件（支持Excel或JSON/YAML）
    
    - **file**: Excel文件（.xlsx/.xls）或JSON/YAML文件（.json/.yaml/.yml）
    
    返回保存的文件名，用于后续调用/analyze接口
    """
    try:
        # 验证文件类型
        allowed_extensions = ('.xlsx', '.xls', '.json', '.yaml', '.yml')
        if not file.filename.endswith(allowed_extensions):
            raise HTTPException(
                status_code=400, 
                detail=f"不支持的文件类型。支持: {', '.join(allowed_extensions)}"
            )
        
        # 生成唯一文件名
        timestamp = int(time.time())
        file_ext = os.path.splitext(file.filename)[1]
        saved_filename = f"{timestamp}_{file.filename}"
        
        # 保存文件
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        file_path = os.path.join(settings.UPLOAD_DIR, saved_filename)
        
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        logger.info(f"文件已上传: {file_path}")
        
        return {
            "success": True,
            "filename": saved_filename,
            "original_name": file.filename,
            "message": f"文件已上传: {file.filename}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"上传文件失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")


@router.get("/download/{task_id}", summary="下载分析报告")
async def download_report(task_id: str):
    """下载资源分析HTML报告"""
    from fastapi.responses import Response
    
    try:
        html_report = None
        
        # 1. 先尝试从本地结果文件获取
        result_file = os.path.join(settings.RESULT_DIR, f"{task_id}_resource_analysis.json")
        if os.path.exists(result_file):
            with open(result_file, 'r', encoding='utf-8') as f:
                import json
                result = json.load(f)
            html_report = result.get('result', {}).get('html_report') or result.get('html_report')
        
        # 2. 如果本地没有，从数据库获取
        if not html_report:
            from app.core.database import SessionLocal
            from app.models.task import Task
            
            db = SessionLocal()
            try:
                task_record = db.query(Task).filter(Task.id == task_id).first()
                if task_record and task_record.result_url:
                    html_report = task_record.result_url
            finally:
                db.close()
        
        if not html_report:
            raise HTTPException(status_code=404, detail="HTML报告路径不存在")
        
        # 3. 从MinIO下载
        from app.core.minio_client import get_minio_client
        minio_client = get_minio_client()
        content = minio_client.download_data(html_report)
        
        if not content:
            raise HTTPException(status_code=404, detail="无法从MinIO下载文件")
        
        return Response(content=content, media_type="text/html", headers={
            "Content-Disposition": f"attachment; filename={task_id}_report.html"
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"下载报告失败: {e}")
        raise HTTPException(status_code=500, detail=f"下载失败: {e}")
