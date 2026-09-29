"""MinIO and AWS S3 compatible implementation of StorageProvider."""

from functools import lru_cache
from typing import Optional
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.core.config import get_settings
from app.core.logging import get_logger
from app.storage.base import StorageProvider

logger = get_logger(__name__)


class S3StorageProvider(StorageProvider):
    """Boto3-based storage client compatible with MinIO, AWS S3, and Cloudflare R2."""

    def __init__(
        self,
        endpoint_url: str,
        access_key: str,
        secret_key: str,
        bucket_name: str,
        region_name: str = "us-east-1",
    ):
        self.endpoint_url = endpoint_url
        self.bucket_name = bucket_name
        self.region_name = region_name

        # Configure boto3 client with path-style addressing for MinIO compatibility
        self.s3_client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region_name,
            config=Config(
                signature_version="s3v4",
                s3={"addressing_style": "path"},
                retries={"max_attempts": 3, "mode": "standard"},
            ),
        )

    def ensure_bucket_exists(self) -> bool:
        """Create the target storage bucket if it does not already exist."""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            return True
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            if error_code in ("404", "NoSuchBucket"):
                try:
                    logger.info("Bucket '%s' not found. Creating bucket...", self.bucket_name)
                    self.s3_client.create_bucket(Bucket=self.bucket_name)
                    return True
                except Exception as create_err:
                    logger.error("Failed to create bucket '%s': %s", self.bucket_name, create_err)
                    return False
            logger.error("HeadBucket failed for '%s': %s", self.bucket_name, e)
            return False

    def generate_upload_url(
        self,
        storage_key: str,
        content_type: str,
        expires_in_seconds: int = 900,
    ) -> str:
        """Generate pre-signed PUT URL for client-side direct upload."""
        return self.s3_client.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": self.bucket_name,
                "Key": storage_key,
                "ContentType": content_type,
            },
            ExpiresIn=expires_in_seconds,
        )

    def generate_download_url(
        self,
        storage_key: str,
        expires_in_seconds: int = 3600,
    ) -> str:
        """Generate pre-signed GET URL for secure resource downloading."""
        return self.s3_client.generate_presigned_url(
            ClientMethod="get_object",
            Params={
                "Bucket": self.bucket_name,
                "Key": storage_key,
            },
            ExpiresIn=expires_in_seconds,
        )

    def object_exists(self, storage_key: str) -> bool:
        """Verify presence of an object without downloading body."""
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=storage_key)
            return True
        except ClientError:
            return False

    def delete_object(self, storage_key: str) -> bool:
        """Remove an object from storage."""
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=storage_key)
            return True
        except ClientError as e:
            logger.error("Failed to delete object '%s': %s", storage_key, e)
            return False

    def get_object_metadata(self, storage_key: str) -> Optional[dict]:
        """Inspect and return object metadata (size_bytes, content_type, etag)."""
        try:
            resp = self.s3_client.head_object(Bucket=self.bucket_name, Key=storage_key)
            return {
                "size_bytes": resp.get("ContentLength"),
                "content_type": resp.get("ContentType"),
                "etag": resp.get("ETag", "").strip('"'),
            }
        except ClientError as e:
            logger.debug("HeadObject failed for key '%s': %s", storage_key, e)
            return None

    def check_health(self) -> bool:
        """Readiness check verifying bucket accessibility."""
        try:
            return self.ensure_bucket_exists()
        except Exception as e:
            logger.error("Storage health check failed: %s", e)
            return False

    def upload_file(
        self,
        local_path: str,
        storage_key: str,
        content_type: str = "application/octet-stream",
    ) -> None:
        """Upload a local file directly to object storage."""
        try:
            self.s3_client.upload_file(
                Filename=str(local_path),
                Bucket=self.bucket_name,
                Key=storage_key,
                ExtraArgs={"ContentType": content_type},
            )
        except ClientError as e:
            logger.error("Failed to upload file '%s' to '%s': %s", local_path, storage_key, e)
            raise

    def upload_bytes(
        self,
        data: bytes,
        storage_key: str,
        content_type: str = "application/octet-stream",
    ) -> None:
        """Upload raw binary bytes directly to object storage."""
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=storage_key,
                Body=data,
                ContentType=content_type,
            )
        except ClientError as e:
            logger.error("Failed to upload bytes to '%s': %s", storage_key, e)
            raise

    def download_file(
        self,
        storage_key: str,
        local_path: str,
    ) -> None:
        """Download an object from storage to a local file path."""
        try:
            self.s3_client.download_file(
                Bucket=self.bucket_name,
                Key=storage_key,
                Filename=str(local_path),
            )
        except ClientError as e:
            logger.error("Failed to download object '%s' to '%s': %s", storage_key, local_path, e)
            raise

    def get_object_bytes(
        self,
        storage_key: str,
    ) -> bytes:
        """Read and return complete binary bytes of an object."""
        try:
            resp = self.s3_client.get_object(Bucket=self.bucket_name, Key=storage_key)
            return resp["Body"].read()
        except ClientError as e:
            logger.error("Failed to read object bytes for '%s': %s", storage_key, e)
            raise

    async def get_object(self, storage_key: str) -> bytes:
        """Async compatibility alias for get_object_bytes."""
        return self.get_object_bytes(storage_key)

    async def put_object(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        metadata: Optional[dict] = None,
    ) -> None:
        """Async compatibility alias for upload_bytes."""
        self.upload_bytes(data=data, storage_key=key, content_type=content_type)



@lru_cache
def get_storage_provider() -> S3StorageProvider:
    """Cached singleton instance of the configured storage provider."""
    settings = get_settings()
    provider = S3StorageProvider(
        endpoint_url=settings.s3_endpoint_resolved,
        access_key=settings.s3_access_key_resolved,
        secret_key=settings.s3_secret_key_resolved,
        bucket_name=settings.s3_bucket_resolved,
        region_name=settings.MINIO_REGION,
    )
    return provider
