#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
文件上传API
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import FileResponse
from typing import Optional
import os
import uuid
import shutil
from datetime import datetime
from loguru import logger

from app.core.config import settings
from app.models.task import ModuleType

router = APIRouter()


@router.post("/files/upload")
async def upload_file(
    file: UploadFile = File(...),
    module_type: str = Form(...)
):
    """
    文件上传接口
    
    - **file**: 上传的文件（Excel/CSV）
    - **module_type**: 模块类型 (operational_analysis, resource_analysis, monitoring_eip等)
    """
    try:
        # 验证模块类型
        try:
            ModuleType(module_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效的模块类型: {module_type}")
        
        # 检查文件扩展名
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件类型: {file_ext}，支持的类型: {settings.ALLOWED_EXTENSIONS}"
            )
        
        # 生成唯一文件名
        task_id = str(uuid.uuid4())
        unique_filename = f"{task_id}_{file.filename}"
        file_path = os.path.join(settings.UPLOAD_DIR, unique_filename)
        
        # 保存文件
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        file_size = os.path.getsize(file_path)
        
        logger.info(f"文件上传成功: {file.filename} -> {file_path} ({file_size} bytes)")
        
        return {
            "success": True,
            "task_id": task_id,
            "file_name": file.filename,
            "file_path": file_path,
            "file_size": file_size,
            "module_type": module_type,
            "uploaded_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"文件上传失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")


@router.get("/files/download/{task_id}")
async def download_result(task_id: str):
    """
    下载分析结果文件
    
    - **task_id**: 任务ID
    """
    # 查找结果文件
    result_files = [
        f for f in os.listdir(settings.RESULT_DIR) 
        if f.startswith(task_id)
    ]
    
    if not result_files:
        raise HTTPException(status_code=404, detail="结果文件不存在")
    
    result_file = result_files[0]
    file_path = os.path.join(settings.RESULT_DIR, result_file)
    
    return FileResponse(
        path=file_path,
        filename=result_file,
        media_type="application/octet-stream"
    )


@router.delete("/files/{task_id}")
async def delete_files(task_id: str):
    """
    删除任务相关文件
    
    - **task_id**: 任务ID
    """
    deleted_files = []
    
    # 删除上传文件
    for filename in os.listdir(settings.UPLOAD_DIR):
        if filename.startswith(task_id):
            file_path = os.path.join(settings.UPLOAD_DIR, filename)
            os.remove(file_path)
            deleted_files.append(filename)
    
    # 删除结果文件
    for filename in os.listdir(settings.RESULT_DIR):
        if filename.startswith(task_id):
            file_path = os.path.join(settings.RESULT_DIR, filename)
            os.remove(file_path)
            deleted_files.append(filename)
    
    logger.info(f"删除任务 {task_id} 相关文件: {deleted_files}")
    
    return {
        "success": True,
        "task_id": task_id,
        "deleted_files": deleted_files
    }
