"""Asset lifecycle management service for worker-generated media outputs.

Bridges storage uploads with PostgreSQL Asset catalog persistence, ensuring
atomic operations with cleanup rollback on failure.
"""

import hashlib
import uuid
from pathlib import Path
from typing import Any, Dict, Optional, Union
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.asset import Asset
from app.repositories.asset import AssetRepository
from app.storage.base import StorageProvider
from app.storage.s3 import get_storage_provider

logger = get_logger(__name__)


class AssetLifecycleManager:
    """Manages worker-generated binary output ingestion into MinIO/S3 and PostgreSQL."""

    def __init__(self, db: AsyncSession, storage: Optional[StorageProvider] = None):
        self.db = db
        self.storage = storage or get_storage_provider()
        self.asset_repo = AssetRepository(db)

    async def ingest_generated_asset(
        self,
        workspace_id: uuid.UUID,
        created_by: uuid.UUID,
        content: Union[bytes, str, Path],
        original_filename: str,
        asset_type: str,
        mime_type: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Asset:
        """Upload worker-generated media output and persist Asset record in database.

        If storage upload succeeds but Asset DB persistence fails, cleans up the uploaded
        storage object to prevent orphaned storage objects.
        """
        asset_id = uuid.uuid4()
        storage_key = f"workspaces/{workspace_id}/assets/{asset_id}/{original_filename}"
        storage_bucket = getattr(self.storage, "bucket_name", "heyzen-media")

        # Determine bytes and checksum
        if isinstance(content, (str, Path)):
            local_path = Path(content).resolve()
            if not local_path.exists():
                raise FileNotFoundError(f"Content file not found: {local_path}")
            size_bytes = local_path.stat().st_size
            hasher = hashlib.sha256()
            with open(local_path, "rb") as f:
                while chunk := f.read(65536):
                    hasher.update(chunk)
            checksum = hasher.hexdigest()
            is_file = True
        elif isinstance(content, bytes):
            size_bytes = len(content)
            checksum = hashlib.sha256(content).hexdigest()
            is_file = False
            local_path = None
        else:
            raise ValueError(f"Unsupported content type: {type(content)}")

        uploaded = False
        try:
            # 1. Upload to storage
            if is_file and local_path is not None:
                self.storage.upload_file(str(local_path), storage_key, content_type=mime_type)
            else:
                self.storage.upload_bytes(content, storage_key, content_type=mime_type)
            uploaded = True

            # 2. Persist in database
            extra_meta = dict(metadata or {})
            extra_meta.setdefault("sha256", checksum)
            extra_meta.setdefault("generated", True)

            asset = Asset(
                id=asset_id,
                workspace_id=workspace_id,
                created_by=created_by,
                original_filename=original_filename,
                storage_bucket=storage_bucket,
                storage_key=storage_key,
                mime_type=mime_type,
                size_bytes=size_bytes,
                checksum_sha256=checksum,
                asset_type=asset_type,
                status="ready",
                extra_metadata=extra_meta,
            )

            created_asset = await self.asset_repo.create(asset)
            await self.db.commit()
            logger.info("Ingested generated asset %s (%s) for workspace %s", asset_id, storage_key, workspace_id)
            return created_asset

        except Exception as exc:
            logger.error("Failed to ingest generated asset for workspace %s: %s", workspace_id, exc)
            if uploaded:
                try:
                    logger.warning("Rolling back uploaded storage object: %s", storage_key)
                    self.storage.delete_object(storage_key)
                except Exception as del_err:
                    logger.error("Storage cleanup failed for %s: %s", storage_key, del_err)
            raise
