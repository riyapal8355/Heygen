"""Tests for S3/MinIO StorageProvider abstraction."""

from app.storage.base import StorageProvider
from app.storage.s3 import S3StorageProvider, get_storage_provider


def test_storage_provider_initialization():
    """Verify storage provider singleton conforms to StorageProvider protocol."""
    provider = get_storage_provider()
    assert isinstance(provider, S3StorageProvider)
    assert isinstance(provider, StorageProvider)


def test_generate_presigned_upload_url():
    """Verify pre-signed upload URL contains bucket and parameters."""
    provider = get_storage_provider()
    key = "workspaces/test-ws/assets/test.mp4"
    url = provider.generate_upload_url(
        storage_key=key,
        content_type="video/mp4",
        expires_in_seconds=300,
    )
    assert url is not None
    assert "test.mp4" in url
    assert "X-Amz-Signature" in url or "Signature" in url


def test_generate_presigned_download_url():
    """Verify pre-signed download URL contains bucket and parameters."""
    provider = get_storage_provider()
    key = "workspaces/test-ws/assets/test.mp4"
    url = provider.generate_download_url(
        storage_key=key,
        expires_in_seconds=600,
    )
    assert url is not None
    assert "test.mp4" in url


def test_storage_health():
    """Verify MinIO container health check and bucket creation/existence."""
    provider = get_storage_provider()
    is_healthy = provider.check_health()
    assert is_healthy is True, "Storage health check failed against MinIO container"
