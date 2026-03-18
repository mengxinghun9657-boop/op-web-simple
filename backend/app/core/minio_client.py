#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MinIO对象存储客户端
用于存储Excel文件和HTML报告
"""
from minio import Minio
from minio.error import S3Error
from typing import Optional
from app.core.logger import logger
import os
from io import BytesIO

class MinIOClient:
    """MinIO客户端封装"""

    def __init__(self):
        self.endpoint = os.getenv('MINIO_ENDPOINT', 'localhost:9000')
        self.access_key = os.getenv('MINIO_ACCESS_KEY', 'minioadmin')
        self.secret_key = os.getenv('MINIO_SECRET_KEY', 'minioadmin')
        self.bucket = os.getenv('MINIO_BUCKET', 'cluster-files')
        self.secure = os.getenv('MINIO_SECURE', 'false').lower() == 'true'

        self.client = Minio(
            self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure
        )

        # 确保bucket存在
        self._ensure_bucket()
        logger.info(f"✅ MinIO连接成功: {self.endpoint}, bucket: {self.bucket}")

    def _ensure_bucket(self):
        """确保bucket存在，不存在则创建"""
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
                logger.info(f"✅ 创建MinIO bucket: {self.bucket}")
            else:
                logger.debug(f"MinIO bucket已存在: {self.bucket}")
        except S3Error as e:
            # 忽略 BucketAlreadyOwnedByYou 错误（并发创建时可能发生）
            if 'BucketAlreadyOwnedByYou' in str(e.code) or 'BucketAlreadyExists' in str(e.code):
                logger.debug(f"MinIO bucket已存在（并发创建）: {self.bucket}")
            else:
                logger.error(f"❌ MinIO bucket检查失败: {e}")
                raise

    def upload_file(self, file_path: str, object_name: str, content_type: str = 'application/octet-stream') -> str:
        """
        上传文件

        Args:
            file_path: 本地文件路径
            object_name: 对象名称（存储路径）
            content_type: 内容类型

        Returns:
            对象URL
        """
        try:
            self.client.fput_object(
                self.bucket,
                object_name,
                file_path,
                content_type=content_type
            )
            logger.info(f"✅ 文件上传成功: {object_name}")
            return f"/{self.bucket}/{object_name}"
        except S3Error as e:
            logger.error(f"❌ 文件上传失败: {object_name}, 错误: {e}")
            raise

    def upload_data(self, data: bytes, object_name: str, content_type: str = 'application/octet-stream') -> str:
        """
        上传字节数据

        Args:
            data: 字节数据
            object_name: 对象名称
            content_type: 内容类型

        Returns:
            对象URL
        """
        try:
            data_stream = BytesIO(data)
            self.client.put_object(
                self.bucket,
                object_name,
                data_stream,
                length=len(data),
                content_type=content_type
            )
            logger.info(f"✅ 数据上传成功: {object_name}")
            return f"/{self.bucket}/{object_name}"
        except S3Error as e:
            logger.error(f"❌ 数据上传失败: {object_name}, 错误: {e}")
            raise

    def download_file(self, object_name: str, file_path: str):
        """
        下载文件

        Args:
            object_name: 对象名称
            file_path: 本地保存路径
        """
        try:
            self.client.fget_object(self.bucket, object_name, file_path)
            logger.info(f"✅ 文件下载成功: {object_name}")
            return True
        except S3Error as e:
            logger.error(f"❌ 文件下载失败: {object_name}, 错误: {e}")
            raise

    def download_data(self, object_name: str) -> bytes:
        """
        下载对象数据到内存

        Args:
            object_name: 对象名称

        Returns:
            文件内容字节
        """
        try:
            response = self.client.get_object(self.bucket, object_name)
            data = response.read()
            response.close()
            response.release_conn()
            return data
        except S3Error as e:
            logger.error(f"❌ 数据下载失败: {object_name}, 错误: {e}")
            raise

    def get_object_url(self, object_name: str, expires: int = 3600) -> str:
        """
        获取对象预签名URL

        Args:
            object_name: 对象名称
            expires: 过期时间（秒），默认1小时

        Returns:
            预签名URL
        """
        try:
            url = self.client.presigned_get_object(self.bucket, object_name, expires=expires)
            return url
        except S3Error as e:
            logger.error(f"❌ 获取对象URL失败: {object_name}, 错误: {e}")
            raise

    def delete_object(self, object_name: str):
        """删除对象"""
        try:
            self.client.remove_object(self.bucket, object_name)
            logger.info(f"✅ 对象删除成功: {object_name}")
        except S3Error as e:
            logger.error(f"❌ 对象删除失败: {object_name}, 错误: {e}")
            raise

    def list_objects(self, prefix: str = '') -> list:
        """列出对象"""
        try:
            objects = self.client.list_objects(self.bucket, prefix=prefix, recursive=True)
            return [obj.object_name for obj in objects]
        except S3Error as e:
            logger.error(f"❌ 列出对象失败, 错误: {e}")
            return []


# 全局MinIO客户端实例
_minio_client: Optional[MinIOClient] = None

def get_minio_client() -> MinIOClient:
    """获取MinIO客户端单例"""
    global _minio_client
    if _minio_client is None:
        _minio_client = MinIOClient()
    return _minio_client


# 延迟初始化 - 不在模块导入时创建实例
# 使用 get_minio_client() 获取实例
class _LazyMinIOClient:
    """延迟初始化的MinIO客户端代理"""
    def __getattr__(self, name):
        return getattr(get_minio_client(), name)

minio_client = _LazyMinIOClient()
