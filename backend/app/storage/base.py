
"""Abstract StorageProvider interface for cloud and local object storage."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class StorageProvider(Protocol):
    """Abstract interface for multi-cloud and on-premise object storage (MinIO, S3, R2)."""

    def generate_upload_url(
        self,
        storage_key: str,
        content_type: str,
        expires_in_seconds: int = 900,
    ) -> str:
        """Generate a pre-signed PUT URL enabling direct client-to-storage upload."""
        ...

    def generate_download_url(
        self,
        storage_key: str,
        expires_in_seconds: int = 3600,
    ) -> str:
        """Generate a pre-signed GET URL for secure media access."""
        ...

    def object_exists(self, storage_key: str) -> bool:
        """Check if an object exists at the specified storage key."""
        ...

    def delete_object(self, storage_key: str) -> bool:
        """Delete an object from storage."""
        ...

    def get_object_metadata(self, storage_key: str) -> dict | None:
        """Inspect and return object metadata (size, content type, etag)."""
        ...

    def check_health(self) -> bool:
        """Verify storage backend accessibility and bucket existence."""
        ...

    def upload_file(
        self,
        local_path: str,
        storage_key: str,
        content_type: str = "application/octet-stream",
    ) -> None:
        """Upload a local file directly to object storage."""
        ...

    def upload_bytes(
        self,
        data: bytes,
        storage_key: str,
        content_type: str = "application/octet-stream",
    ) -> None:
        """Upload raw binary bytes directly to object storage."""
        ...

    def download_file(
        self,
        storage_key: str,
        local_path: str,
    ) -> None:
        """Download an object from storage to a local file path."""
        ...

    def get_object_bytes(
        self,
        storage_key: str,
    ) -> bytes:
        """Read and return complete binary bytes of an object."""
        ...
