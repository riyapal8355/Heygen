"""Storage abstraction package for S3/MinIO binary asset management."""

from app.storage.base import StorageProvider
from app.storage.s3 import S3StorageProvider, get_storage_provider

__all__ = ["StorageProvider", "S3StorageProvider", "get_storage_provider"]
