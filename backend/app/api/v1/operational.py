#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
运营数据分析API路由
支持 Excel 上传分析和 API 查询分析
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Literal
import uuid
import os
from pathlib import Path
from datetime import datetime, timedelta

from app.core.config import settings
from app.services.operational_service import analyze_operational_file, analyze_api_data
from app.services.task_queue_service import task_queue_service
from loguru import logger

router = APIRouter(prefix="/operational", tags=["运营数据分析"])

# 任务状态存储
tasks_status = {}

# 文件大小限制 (16MB)
MAX_FILE_SIZE = 16 * 1024 * 1024


class TaskResponse(BaseModel):
    """任务响应模型"""
    task_id: str
    status: str
    message: str


class AnalysisResult(BaseModel):
    """分析结果模型"""
    task_id: str
    status: str
    html_file: Optional[str] = None
    error: Optional[str] = None
    total_records: Optional[int] = None


class AnalyzeAPIRequest(BaseModel):
    """API 查询分析请求"""
    spacecode: str = "HMLCC"
    username: Optional[str] = None
    password: Optional[str] = None
    iql: str
    page: int = 1
    pgcount: int = 100


class ReportItem(BaseModel):
    """报告项"""
    filename: str
    size: int
    modified: str


class ReportListResponse(BaseModel):
    """报告列表响应"""
    total: int
    reports: List[ReportItem]


class ReportStatsResponse(BaseModel):
    """报告统计响应"""
    total_count: int
    total_size: int
    oldest_date: Optional[str] = None
    newest_date: Optional[str] = None


class CleanReportsRequest(BaseModel):
    """批量清理请求"""
    strategy: Literal["7", "30", "keep10"]


def _validate_filename(filename: str) -> bool:
    """验证文件名安全性（防止路径遍历）"""
    if not filename:
        return False
    if '..' in filename or '/' in filename or '\\' in filename:
        return False
    return True


async def process_analysis(task_id: str, file_path: str, file_name: str):
    """后台处理分析任务"""
    # 创建结果文件路径
    result_file = os.path.join(settings.RESULT_DIR, f"{task_id}_operational_analysis.json")
    
    try:
        # 阶段1: 初始化（10%）
        import json
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump({
                'task_id': task_id,
                'status': 'processing',
                'message': '正在分析数据，生成报告中...',
                'progress': 10
            }, f, indent=2, ensure_ascii=False)
        
        # 阶段2: 数据分析（30%）
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump({
                'task_id': task_id,
                'status': 'processing',
                'message': '正在分析运营数据...',
                'progress': 30
            }, f, indent=2, ensure_ascii=False)
        
        result = await analyze_operational_file(file_path, task_id)
        
        # 阶段3: 生成AI解读（70%）
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump({
                'task_id': task_id,
                'status': 'processing',
                'message': '正在生成AI解读，请稍候...',
                'progress': 70
            }, f, indent=2, ensure_ascii=False)
        
        if result['success']:
            # 保存最终结果到文件
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'success': True,
                    'task_id': task_id,
                    'status': 'completed',
                    'html_file': result.get('html_file'),
                    'message': '分析完成',
                    'progress': 100
                }, f, indent=2, ensure_ascii=False)
            
            try:
                from app.services.task_service import update_task_status
                from app.models.task import TaskStatus
                update_task_status(task_id, TaskStatus.COMPLETED, "分析完成", result_url=result.get('html_file'))
            except Exception as db_error:
                logger.warning(f"[{task_id}] 更新运营分析任务完成状态到数据库失败: {db_error}")
        else:
            # 保存失败结果到文件
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'success': False,
                    'task_id': task_id,
                    'status': 'failed',
                    'error': result.get('error'),
                    'message': '分析失败'
                }, f, indent=2, ensure_ascii=False)

            try:
                from app.services.task_service import update_task_status
                from app.models.task import TaskStatus
                update_task_status(task_id, TaskStatus.FAILED, error_message=result.get('error'))
            except Exception as db_error:
                logger.warning(f"[{task_id}] 更新运营分析任务失败状态到数据库失败: {db_error}")
    except Exception as e:
        logger.error(f"分析任务异常: {e}")
        
        # 保存异常到文件
        import json
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump({
                'success': False,
                'task_id': task_id,
                'status': 'failed',
                'error': str(e),
                'message': '分析异常'
            }, f, indent=2, ensure_ascii=False)
        
        try:
            from app.services.task_service import update_task_status
            from app.models.task import TaskStatus
            update_task_status(task_id, TaskStatus.FAILED, error_message=str(e))
        except Exception as db_error:
            logger.warning(f"[{task_id}] 更新运营分析任务失败状态到数据库失败: {db_error}")
    finally:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as file_error:
            logger.warning(f"[{task_id}] 删除临时文件失败: {file_path}, 错误: {file_error}")


async def process_api_analysis(task_id: str, request: AnalyzeAPIRequest):
    """后台处理 API 查询分析任务"""
    # 创建结果文件路径
    result_file = os.path.join(settings.RESULT_DIR, f"{task_id}_operational_analysis.json")
    
    try:
        # 阶段1: 初始化（10%）
        import json
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump({
                'task_id': task_id,
                'status': 'processing',
                'message': '正在获取数据并分析...',
                'progress': 10
            }, f, indent=2, ensure_ascii=False)
        
        # 阶段2: 数据获取和分析（30%）
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump({
                'task_id': task_id,
                'status': 'processing',
                'message': '正在分析运营数据...',
                'progress': 30
            }, f, indent=2, ensure_ascii=False)
        
        result = await analyze_api_data(
            spacecode=request.spacecode,
            username=request.username,
            password=request.password,
            iql=request.iql,
            page=request.page,
            pgcount=request.pgcount,
            task_id=task_id
        )
        
        # 阶段3: 生成AI解读（70%）
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump({
                'task_id': task_id,
                'status': 'processing',
                'message': '正在生成AI解读，请稍候...',
                'progress': 70
            }, f, indent=2, ensure_ascii=False)
        
        if result['success']:
            # 保存最终结果到文件
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'success': True,
                    'task_id': task_id,
                    'status': 'completed',
                    'html_file': result.get('html_file'),
                    'total_records': result.get('total_records'),
                    'message': '分析完成',
                    'progress': 100
                }, f, indent=2, ensure_ascii=False)
            
            try:
                from app.services.task_service import update_task_status
                from app.models.task import TaskStatus
                update_task_status(task_id, TaskStatus.COMPLETED, "分析完成", result_url=result.get('html_file'))
            except Exception as db_error:
                logger.warning(f"[{task_id}] 更新API分析任务完成状态到数据库失败: {db_error}")
        else:
            # 保存失败结果到文件
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'success': False,
                    'task_id': task_id,
                    'status': 'failed',
                    'error': result.get('error'),
                    'message': '分析失败'
                }, f, indent=2, ensure_ascii=False)

            try:
                from app.services.task_service import update_task_status
                from app.models.task import TaskStatus
                update_task_status(task_id, TaskStatus.FAILED, error_message=result.get('error'))
            except Exception as db_error:
                logger.warning(f"[{task_id}] 更新API分析任务失败状态到数据库失败: {db_error}")
    except Exception as e:
        logger.error(f"API 分析任务异常: {e}")

        # 保存异常到文件
        import json
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump({
                'success': False,
                'task_id': task_id,
                'status': 'failed',
                'error': str(e),
                'message': '分析异常'
            }, f, indent=2, ensure_ascii=False)

        try:
            from app.services.task_service import update_task_status
            from app.models.task import TaskStatus
            update_task_status(task_id, TaskStatus.FAILED, error_message=str(e))
        except Exception as db_error:
            logger.warning(f"[{task_id}] 更新API分析任务失败状态到数据库失败: {db_error}")


@router.post("/analyze", response_model=TaskResponse)
async def analyze_operational_data(
    file: UploadFile = File(..., description="运营数据Excel文件")
):
    """
    上传并分析运营数据Excel文件
    
    - **file**: 运营数据Excel文件（.xlsx, .xls）
    """
    try:
        # 验证文件类型
        if not file.filename.endswith(('.xlsx', '.xls')):
            raise HTTPException(status_code=400, detail="仅支持Excel文件(.xlsx, .xls)")
        
        # 验证文件名安全性
        if not _validate_filename(file.filename):
            raise HTTPException(status_code=400, detail="文件名包含非法字符")
        
        # 生成任务ID
        task_id = str(uuid.uuid4())
        
        # 保存上传的文件
        upload_dir = settings.UPLOAD_DIR
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, f"{task_id}_{file.filename}")
        
        # 读取并验证文件大小
        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail=f"文件大小超过限制(最大 {MAX_FILE_SIZE // 1024 // 1024}MB)")
        
        with open(file_path, "wb") as buffer:
            buffer.write(content)
        
        logger.info(f"文件已上传: {file_path}")
        
        # 初始化任务状态
        tasks_status[task_id] = {
            "status": "pending",
            "message": "任务已提交",
            "file_name": file.filename,
            "created_at": datetime.now(),
            "source": "excel"
        }
        
        # 保存任务到MySQL
        try:
            from app.services.task_service import save_task_to_db
            from app.models.task import TaskType, TaskStatus
            save_task_to_db(task_id, TaskType.OPERATIONAL, TaskStatus.PENDING, "任务已提交", file_name=file.filename)
        except Exception as e:
            logger.warning(f"保存任务到MySQL失败: {e}")
        
        # 提交到 worker 队列
        task_queue_service.enqueue("operational_excel_analysis", {
            "task_id": task_id,
            "file_path": file_path,
            "file_name": file.filename,
        })
        
        return TaskResponse(
            task_id=task_id,
            status="pending",
            message=f"文件已上传，开始分析: {file.filename}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"上传文件失败: {e}")
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")


@router.post("/analyze-api", response_model=TaskResponse)
async def analyze_api_query(
    request: AnalyzeAPIRequest
):
    """
    通过 API 查询分析运营数据
    
    - **spacecode**: 空间代码（默认: HMLCC）
    - **username**: icafe 用户名（留空使用默认配置）
    - **password**: icafe 密码（留空使用默认配置）
    - **iql**: IQL 查询语句
    - **page**: 起始页码（默认: 1）
    - **pgcount**: 每页记录数（默认: 100）
    """
    try:
        # IQL 必填
        if not request.iql:
            raise HTTPException(status_code=400, detail="IQL 查询语句不能为空")
        
        # 如果没有提供用户名密码，使用默认配置
        username = request.username
        password = request.password
        if not username or not password:
            try:
                from app.services.icafe import IcafeAPIClient
                client = IcafeAPIClient()
                defaults = client.get_default_params()
                username = username or defaults.get('username')
                password = password or defaults.get('password')
                logger.info(f"使用默认配置: username={username}")
            except Exception as e:
                logger.warning(f"获取默认配置失败: {e}")
                raise HTTPException(status_code=400, detail="用户名和密码不能为空，且无法获取默认配置")
        
        # 生成任务ID
        task_id = str(uuid.uuid4())
        
        # 创建带有实际用户名密码的请求对象
        actual_request = AnalyzeAPIRequest(
            spacecode=request.spacecode,
            username=username,
            password=password,
            iql=request.iql,
            page=request.page,
            pgcount=request.pgcount
        )
        
        # 初始化任务状态
        tasks_status[task_id] = {
            "status": "pending",
            "message": "任务已提交",
            "spacecode": request.spacecode,
            "created_at": datetime.now(),
            "source": "api"
        }
        
        # 保存任务到MySQL
        try:
            from app.services.task_service import save_task_to_db
            from app.models.task import TaskType, TaskStatus
            save_task_to_db(task_id, TaskType.OPERATIONAL, TaskStatus.PENDING, "API查询任务已提交")
        except Exception as e:
            logger.warning(f"保存任务到MySQL失败: {e}")
        
        # 提交到 worker 队列（序列化请求对象）
        task_queue_service.enqueue("operational_api_analysis", {
            "task_id": task_id,
            "spacecode": actual_request.spacecode,
            "username": actual_request.username,
            "password": actual_request.password,
            "iql": actual_request.iql,
            "page": actual_request.page,
            "pgcount": actual_request.pgcount,
        })
        
        return TaskResponse(
            task_id=task_id,
            status="pending",
            message=f"API 查询任务已提交: spacecode={request.spacecode}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API 查询失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/result/{task_id}", response_model=AnalysisResult)
async def get_analysis_result(task_id: str):
    """获取分析结果"""
    # 优先从结果文件读取（持久化存储）
    result_file = os.path.join(settings.RESULT_DIR, f"{task_id}_operational_analysis.json")
    
    if os.path.exists(result_file):
        try:
            import json
            with open(result_file, 'r', encoding='utf-8') as f:
                result = json.load(f)
            
            html_file = result.get("html_file") or result.get("html_report")
            html_url = None
            
            if html_file:
                if html_file.startswith('html_reports/'):
                    html_url = f"/api/v1/reports/proxy/{html_file}"
                elif os.path.exists(html_file):
                    filename = os.path.basename(html_file)
                    html_url = f"/results/{filename}"
            
            return AnalysisResult(
                task_id=task_id,
                status=result.get("status", "unknown"),
                html_file=html_url,
                error=result.get("error"),
                total_records=result.get("total_records")
            )
        except Exception as e:
            logger.error(f"读取结果文件失败: {e}")
    
    # 文件不存在，尝试从内存中查找（兼容性）
    if task_id in tasks_status:
        task = tasks_status[task_id]
        html_file = task.get("html_file") or task.get("html_report")
        html_url = None
        
        if html_file:
            if html_file.startswith('html_reports/'):
                html_url = f"/api/v1/reports/proxy/{html_file}"
            elif os.path.exists(html_file):
                filename = os.path.basename(html_file)
                html_url = f"/results/{filename}"
        
        return AnalysisResult(
            task_id=task_id,
            status=task.get("status", "unknown"),
            html_file=html_url,
            error=task.get("error"),
            total_records=task.get("total_records")
        )
    
    # 内存中也没有，从数据库查询
    try:
        from app.core.database import SessionLocal
        from app.models.task import Task
        
        db = SessionLocal()
        try:
            task_record = db.query(Task).filter(Task.id == task_id).first()
            if not task_record:
                raise HTTPException(status_code=404, detail="任务不存在")
            
            html_url = None
            if task_record.result_url:
                if task_record.result_url.startswith('html_reports/'):
                    html_url = f"/api/v1/reports/proxy/{task_record.result_url}"
                else:
                    html_url = task_record.result_url
            
            return AnalysisResult(
                task_id=task_id,
                status=task_record.status.value if hasattr(task_record.status, 'value') else str(task_record.status),
                html_file=html_url,
                error=task_record.error_message
            )
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询任务状态失败: {e}")
        raise HTTPException(status_code=404, detail="任务不存在")


@router.get("/download/{task_id}")
async def download_report(task_id: str):
    """下载分析报告"""
    from fastapi.responses import FileResponse, Response
    
    if task_id in tasks_status:
        task = tasks_status[task_id]
        html_file = task.get("html_file")
        if html_file and os.path.exists(html_file):
            return FileResponse(path=html_file, filename=os.path.basename(html_file), media_type="text/html")
    
    try:
        from app.core.database import SessionLocal
        from app.models.task import Task
        
        db = SessionLocal()
        try:
            task_record = db.query(Task).filter(Task.id == task_id).first()
            if not task_record:
                raise HTTPException(status_code=404, detail="任务不存在")
            
            result_url = task_record.result_url
            if not result_url:
                raise HTTPException(status_code=404, detail="报告文件不存在")
            
            if result_url.startswith('html_reports/'):
                from app.core.minio_client import get_minio_client
                minio_client = get_minio_client()
                file_content = minio_client.download_data(result_url)
                if not file_content:
                    raise HTTPException(status_code=404, detail="无法从MinIO下载文件")
                filename = os.path.basename(result_url)
                return Response(content=file_content, media_type="text/html",
                    headers={"Content-Disposition": f"attachment; filename={filename}"})
            
            if os.path.exists(result_url):
                return FileResponse(path=result_url, filename=os.path.basename(result_url), media_type="text/html")
            
            raise HTTPException(status_code=404, detail="报告文件不存在")
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"下载报告失败: {e}")
        raise HTTPException(status_code=500, detail=f"下载报告失败: {str(e)}")


@router.get("/tasks")
async def list_tasks():
    """列出所有分析任务"""
    return {
        "total": len(tasks_status),
        "tasks": [{"task_id": tid, **{k: str(v) if isinstance(v, datetime) else v for k, v in status.items()}}
                  for tid, status in tasks_status.items()]
    }


@router.get("/config/defaults")
async def get_default_config():
    """获取默认配置"""
    try:
        from app.services.icafe import IcafeAPIClient
        client = IcafeAPIClient()
        defaults = client.get_default_params()
        # 不返回密码
        defaults.pop('password', None)
        return defaults
    except Exception as e:
        logger.error(f"获取默认配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取配置失败: {str(e)}")


@router.get("/reports", response_model=ReportListResponse)
async def list_reports():
    """获取报告列表"""
    try:
        from app.core.minio_client import get_minio_client
        minio_client = get_minio_client()
        
        reports = []
        objects = minio_client.list_objects('html_reports/operational/')
        
        for obj in objects:
            if obj.object_name.endswith('.html'):
                reports.append(ReportItem(
                    filename=os.path.basename(obj.object_name),
                    size=obj.size,
                    modified=obj.last_modified.strftime('%Y-%m-%d %H:%M:%S') if obj.last_modified else ''
                ))
        
        reports.sort(key=lambda x: x.modified, reverse=True)
        return ReportListResponse(total=len(reports), reports=reports)
    except Exception as e:
        logger.error(f"获取报告列表失败: {e}")
        return ReportListResponse(total=0, reports=[])


@router.delete("/reports/{filename}")
async def delete_report(filename: str):
    """删除单个报告"""
    try:
        if not filename.endswith('.html'):
            raise HTTPException(status_code=400, detail="只能删除HTML报告文件")
        if not _validate_filename(filename):
            raise HTTPException(status_code=400, detail="文件名包含非法字符")
        
        from app.core.minio_client import get_minio_client
        minio_client = get_minio_client()
        
        object_name = f"html_reports/operational/{filename}"
        minio_client.delete_object(object_name)
        
        logger.info(f"已删除报告: {object_name}")
        return {"success": True, "message": f"报告 {filename} 已删除"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除报告失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


@router.post("/reports/clean")
async def clean_reports(request: CleanReportsRequest):
    """批量清理报告"""
    try:
        from app.core.minio_client import get_minio_client
        minio_client = get_minio_client()
        
        objects = list(minio_client.list_objects('html_reports/operational/'))
        reports = []
        for obj in objects:
            if obj.object_name.endswith('.html'):
                reports.append({
                    'object_name': obj.object_name,
                    'filename': os.path.basename(obj.object_name),
                    'size': obj.size,
                    'mtime': obj.last_modified
                })
        
        reports.sort(key=lambda x: x['mtime'], reverse=True)
        
        deleted_files = []
        total_size = 0
        
        if request.strategy in ['7', '30']:
            days = int(request.strategy)
            cutoff_time = datetime.now(reports[0]['mtime'].tzinfo if reports else None) - timedelta(days=days)
            for report in reports:
                if report['mtime'] < cutoff_time:
                    try:
                        minio_client.delete_object(report['object_name'])
                        deleted_files.append(report['filename'])
                        total_size += report['size']
                    except Exception as e:
                        logger.error(f"删除文件失败: {report['filename']}, 错误: {e}")
        elif request.strategy == 'keep10':
            if len(reports) > 10:
                for report in reports[10:]:
                    try:
                        minio_client.delete_object(report['object_name'])
                        deleted_files.append(report['filename'])
                        total_size += report['size']
                    except Exception as e:
                        logger.error(f"删除文件失败: {report['filename']}, 错误: {e}")
        
        return {
            "success": True,
            "message": f"清理完成：删除了 {len(deleted_files)} 个报告文件",
            "deleted_count": len(deleted_files),
            "freed_size": f"{total_size/1024:.1f} KB"
        }
    except Exception as e:
        logger.error(f"批量清理报告失败: {e}")
        raise HTTPException(status_code=500, detail=f"清理失败: {str(e)}")


@router.get("/iql-templates")
async def get_iql_templates():
    """获取 IQL 查询模板列表和语法帮助"""
    return {
        "templates": [
            {
                "id": "time_range",
                "name": "按时间范围查询",
                "template": "最后修改时间 > \"2025-01-01\" AND 最后修改时间 < \"2025-12-31\"",
                "params": ["start_date", "end_date"],
                "description": "查询指定时间范围内修改的卡片，请修改日期"
            },
            {
                "id": "by_owner",
                "name": "按负责人查询",
                "template": "负责人 = v_username",
                "params": ["username"],
                "description": "查询指定负责人的卡片，请替换用户名"
            },
            {
                "id": "by_type",
                "name": "按类型查询",
                "template": "类型 in (Bug, Task, 需求)",
                "params": ["types"],
                "description": "查询指定类型的卡片（Bug, Epic, Story, Task, 需求 等）"
            },
            {
                "id": "by_status",
                "name": "按流程状态查询",
                "template": "流程状态 in (新建, 开发中, 已完成)",
                "params": ["statuses"],
                "description": "查询指定状态的卡片"
            },
            {
                "id": "by_category",
                "name": "按方向大类查询",
                "template": "方向大类 = \"K8S\"",
                "params": ["category"],
                "description": "查询指定方向大类的卡片"
            },
            {
                "id": "custom",
                "name": "自定义查询",
                "template": "",
                "params": [],
                "description": "完全自定义 IQL 查询语句"
            }
        ],
        "syntax_help": {
            "operators": ["AND", "OR", ">", "<", "=", ">=", "<=", "!=", "in ()", "not in ()", "is empty", "is not empty", "~", "!~"],
            "field_examples": {
                "日期类型": "创建时间 > \"2023-12-01\" AND 创建时间 < \"2023-12-31\"",
                "人员字段": "负责人 = v_username 或 负责人 in (user1, user2)",
                "类型字段": "类型 in (Bug, Epic, Story)",
                "流程状态": "流程状态 in (新建, 开发中, 待开发)",
                "文本字段": "标题 ~ 关键词 或 标题 !~ 排除词"
            },
            "common_fields": ["标题", "负责人", "创建时间", "最后修改时间", "类型", "流程状态", "方向大类", "优先级"]
        }
    }


@router.get("/reports/stats", response_model=ReportStatsResponse)
async def get_report_stats():
    """获取报告统计"""
    try:
        from app.core.minio_client import get_minio_client
        minio_client = get_minio_client()
        
        stats = ReportStatsResponse(total_count=0, total_size=0)
        mtimes = []
        
        objects = minio_client.list_objects('html_reports/operational/')
        for obj in objects:
            if obj.object_name.endswith('.html'):
                stats.total_count += 1
                stats.total_size += obj.size
                if obj.last_modified:
                    mtimes.append(obj.last_modified)
        
        if mtimes:
            stats.oldest_date = min(mtimes).strftime('%Y-%m-%d %H:%M:%S')
            stats.newest_date = max(mtimes).strftime('%Y-%m-%d %H:%M:%S')
        
        return stats
    except Exception as e:
        logger.error(f"获取报告统计失败: {e}")
        return ReportStatsResponse(total_count=0, total_size=0)
