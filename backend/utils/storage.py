# -*- coding: utf-8 -*-
"""
文件存储抽象层

支持多种存储后端：
- local: 本地文件系统（默认）
- minio: MinIO/S3 兼容对象存储

配置方式（环境变量）：
  STORAGE_TYPE=local|minio
  STORAGE_LOCAL_DIR=uploads
  MINIO_ENDPOINT=localhost:9000
  MINIO_ACCESS_KEY=minioadmin
  MINIO_SECRET_KEY=minioadmin
  MINIO_BUCKET=shangzhou
  MINIO_SECURE=false
"""

import os
import abc
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class StorageBackend(abc.ABC):
    """存储后端抽象基类"""

    @abc.abstractmethod
    def save(self, file_data, original_name, file_type=''):
        """
        保存文件

        Args:
            file_data: 文件二进制数据
            original_name: 原始文件名
            file_type: 文件类型/扩展名

        Returns:
            dict: {file_path, file_size, storage_key}
        """
        pass

    @abc.abstractmethod
    def read(self, storage_key):
        """
        读取文件

        Args:
            storage_key: 存储键（由 save 返回）

        Returns:
            bytes: 文件二进制数据
        """
        pass

    @abc.abstractmethod
    def delete(self, storage_key):
        """
        删除文件

        Args:
            storage_key: 存储键

        Returns:
            bool: 是否成功
        """
        pass

    @abc.abstractmethod
    def exists(self, storage_key):
        """
        检查文件是否存在

        Args:
            storage_key: 存储键

        Returns:
            bool
        """
        pass

    @abc.abstractmethod
    def get_url(self, storage_key, expires=3600):
        """
        获取文件访问 URL

        Args:
            storage_key: 存储键
            expires: URL 过期时间（秒）

        Returns:
            str: 访问 URL
        """
        pass


class LocalStorageBackend(StorageBackend):
    """本地文件系统存储"""

    def __init__(self, base_dir=None):
        self.base_dir = base_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'uploads'
        )
        os.makedirs(self.base_dir, exist_ok=True)
        logger.info(f'本地存储初始化: {self.base_dir}')

    def _generate_key(self, original_name):
        """生成存储键"""
        import uuid
        ext = ''
        if '.' in original_name:
            ext = '.' + original_name.rsplit('.', 1)[1].lower()
        date_dir = datetime.now().strftime('%Y%m%d')
        return os.path.join(date_dir, str(uuid.uuid4()) + ext)

    def save(self, file_data, original_name, file_type=''):
        storage_key = self._generate_key(original_name)
        full_path = os.path.join(self.base_dir, storage_key)

        # 创建目录
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        # 写入文件
        with open(full_path, 'wb') as f:
            f.write(file_data)

        file_size = len(file_data)
        logger.debug(f'文件已保存: {storage_key} ({file_size} bytes)')

        return {
            'file_path': storage_key,
            'file_size': file_size,
            'storage_key': storage_key,
        }

    def read(self, storage_key):
        full_path = os.path.join(self.base_dir, storage_key)
        if not os.path.exists(full_path):
            raise FileNotFoundError(f'文件不存在: {storage_key}')
        with open(full_path, 'rb') as f:
            return f.read()

    def delete(self, storage_key):
        full_path = os.path.join(self.base_dir, storage_key)
        if os.path.exists(full_path):
            os.remove(full_path)
            logger.debug(f'文件已删除: {storage_key}')
            return True
        return False

    def exists(self, storage_key):
        full_path = os.path.join(self.base_dir, storage_key)
        return os.path.exists(full_path)

    def get_url(self, storage_key, expires=3600):
        # 本地存储返回相对路径
        return f'/api/files/local/{storage_key}'


class MinioStorageBackend(StorageBackend):
    """MinIO/S3 兼容对象存储"""

    def __init__(self, endpoint=None, access_key=None, secret_key=None,
                 bucket=None, secure=False, region=None):
        try:
            from minio import Minio
        except ImportError:
            raise ImportError('使用 MinIO 存储需要安装 minio 包: pip install minio')

        self.endpoint = endpoint or os.getenv('MINIO_ENDPOINT', 'localhost:9000')
        self.access_key = access_key or os.getenv('MINIO_ACCESS_KEY', 'minioadmin')
        self.secret_key = secret_key or os.getenv('MINIO_SECRET_KEY', 'minioadmin')
        self.bucket = bucket or os.getenv('MINIO_BUCKET', 'shangzhou')
        self.secure = secure or os.getenv('MINIO_SECURE', 'false').lower() == 'true'
        self.region = region or os.getenv('MINIO_REGION', 'us-east-1')

        self.client = Minio(
            self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure,
            region=self.region,
        )

        # 确保 bucket 存在
        self._ensure_bucket()
        logger.info(f'MinIO 存储初始化: {self.endpoint}/{self.bucket}')

    def _ensure_bucket(self):
        """确保 bucket 存在"""
        if not self.client.bucket_exists(self.bucket):
            self.client.make_bucket(self.bucket)
            logger.info(f'创建 bucket: {self.bucket}')

    def _generate_key(self, original_name):
        """生成存储键"""
        import uuid
        ext = ''
        if '.' in original_name:
            ext = '.' + original_name.rsplit('.', 1)[1].lower()
        date_dir = datetime.now().strftime('%Y%m%d')
        return f'{date_dir}/{uuid.uuid4()}{ext}'

    def save(self, file_data, original_name, file_type=''):
        storage_key = self._generate_key(original_name)
        file_size = len(file_data)

        from io import BytesIO
        from minio.commonconfig import ENABLED

        self.client.put_object(
            self.bucket,
            storage_key,
            BytesIO(file_data),
            length=file_size,
            content_type=file_type or 'application/octet-stream',
        )

        logger.debug(f'文件已上传到 MinIO: {storage_key} ({file_size} bytes)')

        return {
            'file_path': storage_key,
            'file_size': file_size,
            'storage_key': storage_key,
        }

    def read(self, storage_key):
        try:
            resp = self.client.get_object(self.bucket, storage_key)
            return resp.read()
        except Exception as e:
            raise FileNotFoundError(f'文件不存在: {storage_key} ({e})')

    def delete(self, storage_key):
        try:
            self.client.remove_object(self.bucket, storage_key)
            logger.debug(f'文件已从 MinIO 删除: {storage_key}')
            return True
        except Exception:
            return False

    def exists(self, storage_key):
        try:
            self.client.stat_object(self.bucket, storage_key)
            return True
        except Exception:
            return False

    def get_url(self, storage_key, expires=3600):
        try:
            return self.client.presigned_get_object(self.bucket, storage_key, expires=expires)
        except Exception:
            return f'minio://{self.bucket}/{storage_key}'


# ============================================================
# 存储管理器（单例）
# ============================================================

_storage_instance = None


def get_storage() -> StorageBackend:
    """
    获取存储后端实例（单例）

    通过环境变量 STORAGE_TYPE 控制使用哪种后端：
    - local: 本地文件系统（默认）
    - minio: MinIO/S3 兼容对象存储
    """
    global _storage_instance
    if _storage_instance is None:
        storage_type = os.getenv('STORAGE_TYPE', 'local').lower()

        if storage_type == 'minio':
            try:
                _storage_instance = MinioStorageBackend()
            except ImportError as e:
                logger.warning(f'MinIO 不可用，回退到本地存储: {e}')
                _storage_instance = LocalStorageBackend()
        else:
            _storage_instance = LocalStorageBackend()

    return _storage_instance


def reset_storage():
    """重置存储实例（用于测试）"""
    global _storage_instance
    _storage_instance = None
