#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
报告上传服务 - 统一处理 HTML 和 Excel 报告的 MinIO 上传
"""

from typing import Optional, Dict, Tuple, Callable
from app.core.minio_client import get_minio_client
from app.core.logger import logger
import tempfile
import os


class ReportUploadService:
    """报告上传服务 - 统一管理所有报告的 MinIO 上传"""

    def __init__(self):
        self.minio_client = get_minio_client()

    def upload_html_content(
        self,
        task_id: str,
        html_content: str,
        report_type: str
    ) -> Tuple[str, str]:
        """
        上传 HTML 报告内容（字符串）

        Args:
            task_id: 任务ID
            html_content: HTML 内容字符串
            report_type: 报告类型 (bcc/bos/eip/resource/operational)

        Returns:
            (object_name, url) - MinIO 对象名称和相对URL
        """
        try:
            object_name = f"html_reports/{report_type}/{task_id}_{report_type}_report.html"

            url = self.minio_client.upload_data(
                data=html_content.encode('utf-8'),
                object_name=object_name,
                content_type='text/html; charset=utf-8'
            )

            logger.info(f"✅ HTML报告已上传到MinIO: {object_name}")
            return object_name, url

        except Exception as e:
            logger.error(f"❌ HTML报告上传失败: {e}")
            raise

    def upload_html_file(
        self,
        task_id: str,
        file_path: str,
        report_type: str,
        delete_after_upload: bool = True
    ) -> Tuple[str, str]:
        """
        上传 HTML 报告文件

        Args:
            task_id: 任务ID
            file_path: 本地文件路径
            report_type: 报告类型
            delete_after_upload: 上传后是否删除本地文件

        Returns:
            (object_name, url) - MinIO 对象名称和相对URL
        """
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"文件不存在: {file_path}")

            object_name = f"html_reports/{report_type}/{task_id}_{report_type}_report.html"

            url = self.minio_client.upload_file(
                file_path=file_path,
                object_name=object_name,
                content_type='text/html; charset=utf-8'
            )

            logger.info(f"✅ HTML报告文件已上传到MinIO: {object_name}")

            # 上传成功后删除本地文件
            if delete_after_upload and os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"🗑️  本地文件已删除: {file_path}")

            return object_name, url

        except Exception as e:
            logger.error(f"❌ HTML报告文件上传失败: {e}")
            raise

    def upload_excel_file(
        self,
        task_id: str,
        file_path: str,
        report_type: str,
        delete_after_upload: bool = True
    ) -> Tuple[str, str]:
        """
        上传 Excel 报告文件

        Args:
            task_id: 任务ID
            file_path: 本地文件路径
            report_type: 报告类型
            delete_after_upload: 上传后是否删除本地文件

        Returns:
            (object_name, url) - MinIO 对象名称和相对URL
        """
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"文件不存在: {file_path}")

            object_name = f"excel_reports/{task_id}_{report_type}_report.xlsx"

            url = self.minio_client.upload_file(
                file_path=file_path,
                object_name=object_name,
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )

            logger.info(f"✅ Excel报告已上传到MinIO: {object_name}")

            # 上传成功后删除本地文件
            if delete_after_upload and os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"🗑️  本地文件已删除: {file_path}")

            return object_name, url

        except Exception as e:
            logger.error(f"❌ Excel报告上传失败: {e}")
            raise

    def upload_html_and_excel(
        self,
        task_id: str,
        html_content: str,
        excel_generator_func: Callable[[str], None],
        report_type: str
    ) -> Dict[str, str]:
        """
        同时上传 HTML 和 Excel 报告

        Args:
            task_id: 任务ID
            html_content: HTML 内容字符串
            excel_generator_func: Excel 生成函数（接收文件路径参数，生成Excel到该路径）
            report_type: 报告类型

        Returns:
            包含所有路径和 URL 的字典:
            {
                'html_report': 'html_reports/bcc/xxx.html',
                'html_report_url': '/cluster-files/html_reports/...',
                'excel_report': 'excel_reports/xxx.xlsx',
                'excel_report_url': '/cluster-files/excel_reports/...'
            }
        """
        result = {}

        # 1. 上传 HTML
        html_object_name, html_url = self.upload_html_content(
            task_id, html_content, report_type
        )
        result['html_report'] = html_object_name
        result['html_report_url'] = html_url

        # 2. 生成并上传 Excel
        tmp_excel = None
        try:
            # 创建临时文件
            with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
                tmp_excel = tmp.name

            # 调用 Excel 生成函数
            excel_generator_func(tmp_excel)

            # 上传到 MinIO
            excel_object_name, excel_url = self.upload_excel_file(
                task_id, tmp_excel, report_type, delete_after_upload=False
            )
            result['excel_report'] = excel_object_name
            result['excel_report_url'] = excel_url

        except Exception as e:
            logger.error(f"❌ Excel报告生成或上传失败: {e}")
            # Excel 失败不影响 HTML，继续执行
            result['excel_error'] = str(e)

        finally:
            # 清理临时文件
            if tmp_excel and os.path.exists(tmp_excel):
                try:
                    os.remove(tmp_excel)
                    logger.info(f"🗑️  临时Excel文件已删除: {tmp_excel}")
                except Exception as e:
                    logger.warning(f"⚠️  删除临时文件失败: {e}")

        return result

    def get_download_url(
        self,
        object_name: str,
        expires: int = 3600
    ) -> str:
        """
        获取报告的预签名下载 URL

        Args:
            object_name: MinIO 对象名称
            expires: 过期时间（秒），默认1小时

        Returns:
            预签名下载 URL
        """
        try:
            download_url = self.minio_client.get_object_url(
                object_name=object_name,
                expires=expires
            )
            return download_url
        except Exception as e:
            logger.error(f"❌ 获取下载URL失败: {e}")
            raise


# 全局实例
_report_upload_service: Optional[ReportUploadService] = None


def get_report_upload_service() -> ReportUploadService:
    """获取报告上传服务单例"""
    global _report_upload_service
    if _report_upload_service is None:
        _report_upload_service = ReportUploadService()
    return _report_upload_service
