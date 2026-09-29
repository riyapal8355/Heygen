import os
import re
import uuid
from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import ConflictException, NotFoundException
from app.models.asset import Asset
from app.repositories.asset import AssetRepository
from app.storage.base import StorageProvider
from app.storage.s3 import get_storage_provider

# Block executable and dangerous scripts from direct S3/MinIO upload
PROHIBITED_FILE_EXTENSIONS = {
    ".exe", ".bat", ".cmd", ".sh", ".bash", ".php", ".py", ".pyw",
    ".js", ".mjs", ".vbs", ".ps1", ".msi", ".dll", ".so", ".dylib",
    ".com", ".scr", ".pif", ".cpl", ".jar", ".vbe", ".wsf", ".hta",
}


class AssetService:
    """Coordinates MinIO/S3 object storage interactions with Postgres asset catalog."""

    def __init__(self, db: AsyncSession, storage: Optional[StorageProvider] = None):
        self.db = db
        self.repo = AssetRepository(db)
        self.storage = storage or get_storage_provider()
        self.settings = get_settings()

    async def create_upload_intent(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        original_filename: str,
        mime_type: str,
        size_bytes: Optional[int] = None,
        asset_type: str = "other",
        checksum_sha256: Optional[str] = None,
    ) -> Tuple[Asset, str]:
        """Generate a pre-signed direct upload URL and register pending asset metadata."""
        # 1. Path Traversal & Sanitization: Strip path segments and dots
        base_name = os.path.basename(original_filename.replace("\\", "/"))
        clean_filename = base_name.strip()
        if not clean_filename or clean_filename in (".", ".."):
            raise ConflictException(
                code="ASSET_INVALID_FILENAME",
                message="Filename cannot be empty or a relative directory path.",
            )

        # 2. Extension validation: Prohibit executables and scripts
        ext = os.path.splitext(clean_filename)[1].lower()
        if ext in PROHIBITED_FILE_EXTENSIONS:
            raise ConflictException(
                code="ASSET_DANGEROUS_EXTENSION",
                message=f"Files with extension '{ext}' are prohibited for upload security.",
            )

        # 3. File size constraints
        if size_bytes is not None:
            if size_bytes <= 0:
                raise ConflictException(
                    code="ASSET_INVALID_SIZE",
                    message="Asset size must be greater than zero bytes.",
                )
            if size_bytes > self.settings.MAX_MEDIA_INPUT_SIZE_BYTES:
                raise ConflictException(
                    code="ASSET_SIZE_EXCEEDED",
                    message=f"Asset size ({size_bytes} bytes) exceeds maximum permitted limit of {self.settings.MAX_MEDIA_INPUT_SIZE_BYTES} bytes.",
                )

        # 4. MIME type validation
        clean_mime = mime_type.strip().lower() if mime_type else ""
        if not clean_mime or "/" not in clean_mime:
            raise ConflictException(
                code="ASSET_INVALID_MIME",
                message="A valid MIME type (e.g., 'image/png', 'video/mp4') is required.",
            )

        asset_id = uuid.uuid4()
        # Sanitize filename for safe S3 path
        safe_name = re.sub(r"[^a-zA-Z0-9_.-]", "_", clean_filename)
        storage_key = f"workspaces/{workspace_id}/assets/{asset_id}/{safe_name}"


        # Generate pre-signed PUT upload URL
        signed_upload_url = self.storage.generate_upload_url(
            storage_key=storage_key,
            content_type=mime_type,
            expires_in_seconds=900,
        )

        asset = Asset(
            id=asset_id,
            workspace_id=workspace_id,
            created_by=user_id,
            original_filename=clean_filename,
            storage_bucket=self.storage.bucket_name,
            storage_key=storage_key,
            mime_type=mime_type,
            size_bytes=size_bytes,
            checksum_sha256=checksum_sha256,
            asset_type=asset_type,
            status="pending_upload",
            extra_metadata={},
        )
        saved_asset = await self.repo.create(asset)
        return saved_asset, signed_upload_url

    async def confirm_upload(
        self,
        asset_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> Asset:
        """Inspect storage object existence and size, then transition pending_upload -> ready."""
        asset = await self.repo.get_by_id(asset_id, workspace_id)
        if not asset:
            raise NotFoundException(
                code="ASSET_NOT_FOUND",
                message="Asset not found in this workspace.",
            )

        # Idempotent confirmation if already confirmed
        if asset.status in ("ready", "uploaded"):
            return asset

        # Verify object physically exists in storage
        metadata = self.storage.get_object_metadata(asset.storage_key)
        if not metadata:
            raise ConflictException(
                code="ASSET_OBJECT_NOT_FOUND",
                message="Object was not found in storage. Ensure client upload has finished before confirming.",
            )

        actual_size = metadata.get("size_bytes")
        if actual_size is not None:
            if asset.size_bytes is not None and asset.size_bytes > 0 and actual_size == 0:
                raise ConflictException(
                    code="ASSET_EMPTY_FILE",
                    message="Uploaded object is 0 bytes.",
                )
            asset.size_bytes = actual_size

        actual_content_type = metadata.get("content_type")
        if actual_content_type:
            asset.mime_type = actual_content_type

        asset.status = "ready"
        return await self.repo.update(asset)

    async def generate_download_url(
        self,
        asset_id: uuid.UUID,
        workspace_id: uuid.UUID,
        expires_in_seconds: int = 3600,
    ) -> Tuple[Asset, str]:
        """Generate secure pre-signed GET URL for asset download."""
        asset = await self.get_asset(asset_id, workspace_id)
        if asset.status not in ("ready", "uploaded"):
            raise ConflictException(
                code="ASSET_NOT_READY",
                message=f"Asset is not ready for download (current status: {asset.status}).",
            )

        download_url = self.storage.generate_download_url(
            storage_key=asset.storage_key,
            expires_in_seconds=expires_in_seconds,
        )
        return asset, download_url

    async def get_asset(self, asset_id: uuid.UUID, workspace_id: uuid.UUID) -> Asset:
        """Fetch active asset strictly within workspace."""
        asset = await self.repo.get_by_id(asset_id, workspace_id)
        if not asset:
            raise NotFoundException(
                code="ASSET_NOT_FOUND",
                message="Asset not found in this workspace.",
            )
        return asset

    async def list_assets(
        self,
        workspace_id: uuid.UUID,
        asset_type: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Asset]:
        """List active workspace assets."""
        return await self.repo.list_by_workspace(
            workspace_id=workspace_id,
            asset_type=asset_type,
            status=status,
            search=search,
            limit=limit,
            offset=offset,
        )

    async def delete_asset(self, asset_id: uuid.UUID, workspace_id: uuid.UUID) -> None:
        """Soft-delete asset record in database; object GC handled asynchronously."""
        asset = await self.get_asset(asset_id, workspace_id)
        await self.repo.soft_delete(asset)
