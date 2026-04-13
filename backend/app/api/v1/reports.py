#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一的报告下载 API
提供所有类型报告（HTML、Excel）的下载接口
"""

from fastapi import APIRouter, HTTPException, Path as PathParam
from fastapi.responses import Response
from typing import Literal
from app.core.logger import logger
from app.services.report_upload_service import get_report_upload_service

router = APIRouter()

ReportType = Literal['html', 'excel']
ModuleType = Literal['bcc', 'bos', 'eip', 'resource', 'operational', 'prometheus', 'gpu_bottom']


@router.get("/proxy/{file_path:path}")
async def proxy_minio_file(file_path: str, download: bool = False):
    """
    代理访问MinIO中的文件
    
    - **file_path**: MinIO对象路径
    - **download**: 是否强制下载
    """
    try:
        upload_service = get_report_upload_service()
        
        # 去掉可能存在的 bucket 名称前缀（如 /cluster-files/）
        # MinIO 客户端已经配置了 bucket，object_name 不应包含 bucket
        clean_path = file_path
        bucket_prefixes = ['cluster-files/', '/cluster-files/']
        for prefix in bucket_prefixes:
            if clean_path.startswith(prefix):
                clean_path = clean_path[len(prefix):]
                break
        
        content = upload_service.minio_client.download_data(clean_path)
        
        # 获取文件名
        filename = clean_path.split('/')[-1]
        
        # 根据文件类型设置Content-Type
        if clean_path.endswith('.html'):
            content_type = 'text/html; charset=utf-8'
        elif clean_path.endswith('.xlsx'):
            content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        elif clean_path.endswith('.json'):
            content_type = 'application/json'
        else:
            content_type = 'application/octet-stream'
        
        headers = {}
        if download:
            headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return Response(content=content, media_type=content_type, headers=headers)
        
    except Exception as e:
        logger.error(f"代理MinIO文件失败: {file_path}, 错误: {e}")
        raise HTTPException(status_code=404, detail=f"文件不存在: {file_path}")


@router.get("/{module_type}/{task_id}/download/{report_type}")
async def download_report(
    module_type: ModuleType = PathParam(..., description="模块类型"),
    task_id: str = PathParam(..., description="任务ID"),
    report_type: ReportType = PathParam(..., description="报告类型")
):
    """
    统一的报告下载接口 - 获取预签名下载URL

    **支持的模块类型**:
    - bcc: BCC监控分析
    - bos: BOS存储分析
    - eip: EIP流量分析
    - resource: 资源综合分析
    - operational: 运营数据分析
    - prometheus: Prometheus批量采集
    - gpu_bottom: GPU bottom卡时分析

    **报告类型**:
    - html: HTML报告
    - excel: Excel报告

    **返回**: 预签名下载URL（有效期1小时）
    """
    try:
        # 构建MinIO对象名称
        if report_type == 'html':
            if module_type == 'prometheus':
                # Prometheus结果是JSON，不是HTML
                raise HTTPException(
                    status_code=400,
                    detail="Prometheus模块只有JSON结果，请使用 /api/v1/tasks/prometheus/{task_id}/download"
                )
            object_name = f"html_reports/{module_type}/{task_id}_{module_type}_report.html"
        elif report_type == 'excel':
            if module_type in ['eip', 'resource', 'operational']:
                # 这些模块没有Excel报告
                raise HTTPException(
                    status_code=404,
                    detail=f"{module_type.upper()}模块不提供Excel报告"
                )
            object_name = f"excel_reports/{task_id}_{module_type}_report.xlsx"
        else:
            raise HTTPException(status_code=400, detail="无效的报告类型")

        # 获取预签名URL
        upload_service = get_report_upload_service()
        download_url = upload_service.get_download_url(
            object_name=object_name,
            expires=3600  # 1小时
        )

        return {
            "success": True,
            "module_type": module_type,
            "task_id": task_id,
            "report_type": report_type,
            "download_url": download_url,
            "file_name": object_name.split('/')[-1],
            "expires_in": 3600,
            "expires_text": "1小时"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取报告下载URL失败: {module_type}/{task_id}/{report_type}, 错误: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"获取下载URL失败: {str(e)}"
        )


@router.get("/{module_type}/{task_id}/info")
async def get_report_info(
    module_type: ModuleType = PathParam(..., description="模块类型"),
    task_id: str = PathParam(..., description="任务ID")
):
    """
    获取指定任务的报告信息

    **返回**: 可用的报告列表及下载链接
    """
    try:
        # 定义每个模块支持的报告类型
        module_report_types = {
            'bcc': ['html', 'excel'],
            'bos': ['html', 'excel'],
            'eip': ['html'],
            'resource': ['html'],
            'operational': ['html'],
            'prometheus': ['json'],  # 特殊情况
            'gpu_bottom': ['html', 'excel']
        }

        if module_type not in module_report_types:
            raise HTTPException(status_code=400, detail="无效的模块类型")

        upload_service = get_report_upload_service()
        available_reports = []

        # 检查每种报告类型是否存在
        for report_type in module_report_types[module_type]:
            if report_type == 'json':
                # Prometheus的JSON结果
                continue

            try:
                if report_type == 'html':
                    object_name = f"html_reports/{module_type}/{task_id}_{module_type}_report.html"
                else:  # excel
                    object_name = f"excel_reports/{task_id}_{module_type}_report.xlsx"

                # 先检查文件是否真实存在，再生成下载URL
                if not upload_service.minio_client.object_exists(object_name):
                    continue

                download_url = upload_service.get_download_url(object_name, expires=3600)

                available_reports.append({
                    "type": report_type,
                    "file_name": object_name.split('/')[-1],
                    "download_url": download_url
                })

            except Exception:
                # 文件不存在，跳过
                continue

        if not available_reports:
            raise HTTPException(status_code=404, detail="未找到任何报告文件，请确认任务已完成且报告已成功上传到 MinIO")

        return {
            "success": True,
            "module_type": module_type,
            "task_id": task_id,
            "reports": available_reports,
            "total_reports": len(available_reports)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取报告信息失败: {module_type}/{task_id}, 错误: {e}")
        raise HTTPException(status_code=500, detail=str(e))
