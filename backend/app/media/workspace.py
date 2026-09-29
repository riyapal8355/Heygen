"""Isolated scratch workspace for media assembly, clip rendering, and asset resolution."""

import os
import re
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Any, Optional, Union

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.media.errors import RenderInputMissingError
from app.repositories.asset import AssetRepository
from app.storage.s3 import get_storage_provider

logger = get_logger(__name__)


def _sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent directory traversal and invalid characters."""
    base = os.path.basename(filename).strip()
    clean = re.sub(r'[^a-zA-Z0-9_.-]', '_', base)
    return clean or "asset_file"


class MediaWorkspace:
    """Manages an isolated scratch filesystem directory for media operations.

    Provides dedicated subdirectories for input assets, intermediate scene clips,
    audio tracks, and final render outputs, with automatic cleanup.
    """

    def __init__(
        self,
        prefix: str = "heyzen_render_",
        base_dir: Optional[Union[str, Path]] = None,
    ) -> None:
        settings = get_settings()
        parent = base_dir or getattr(settings, "MEDIA_TEMP_DIR", None)
        if parent:
            Path(parent).mkdir(parents=True, exist_ok=True)
            self.root_path = Path(tempfile.mkdtemp(prefix=prefix, dir=str(parent))).resolve()
        else:
            self.root_path = Path(tempfile.mkdtemp(prefix=prefix)).resolve()

        self.inputs_dir = self.root_path / "inputs"
        self.scenes_dir = self.root_path / "scenes"
        self.audio_dir = self.root_path / "audio"
        self.output_dir = self.root_path / "output"

        self.inputs_dir.mkdir(parents=True, exist_ok=True)
        self.scenes_dir.mkdir(parents=True, exist_ok=True)
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self._cleaned = False

    def __enter__(self) -> "MediaWorkspace":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.cleanup()

    async def __aenter__(self) -> "MediaWorkspace":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.cleanup()

    def cleanup(self) -> None:
        """Safely remove the scratch workspace directory and all intermediate files."""
        if self._cleaned:
            return
        try:
            if self.root_path.exists():
                shutil.rmtree(self.root_path, ignore_errors=True)
            self._cleaned = True
        except Exception as e:
            logger.warning("Failed to clean up MediaWorkspace at %s: %s", self.root_path, e)

    async def resolve_asset(
        self,
        asset_id: Union[str, uuid.UUID],
        workspace_id: Union[str, uuid.UUID],
        db: AsyncSession,
        storage_provider: Optional[Any] = None,
    ) -> Path:
        """Resolve and download a workspace-scoped asset to the local inputs directory.

        Args:
            asset_id: UUID of the asset to resolve.
            workspace_id: UUID of the workspace (enforcing isolation).
            db: Async database session.
            storage_provider: Optional S3StorageProvider override.

        Returns:
            Path to downloaded local asset file in `inputs/`.

        Raises:
            RenderInputMissingError: If asset is missing, inaccessible, or failed download.
        """
        parsed_asset_id = uuid.UUID(str(asset_id)) if isinstance(asset_id, str) else asset_id
        parsed_ws_id = uuid.UUID(str(workspace_id)) if isinstance(workspace_id, str) else workspace_id

        asset_repo = AssetRepository(db)
        asset = await asset_repo.get_by_id(parsed_asset_id, parsed_ws_id)

        if not asset:
            raise RenderInputMissingError(
                f"Asset {parsed_asset_id} not found in workspace {parsed_ws_id}",
                details={"asset_id": str(parsed_asset_id), "workspace_id": str(parsed_ws_id)},
            )

        if asset.status != "ready":
            raise RenderInputMissingError(
                f"Asset {parsed_asset_id} is in status '{asset.status}', must be 'ready'",
                details={"asset_id": str(parsed_asset_id), "status": asset.status},
            )

        if not asset.storage_key:
            raise RenderInputMissingError(
                f"Asset {parsed_asset_id} has no storage key",
                details={"asset_id": str(parsed_asset_id)},
            )

        # Build secure, collision-free local filename
        safe_name = _sanitize_filename(asset.original_filename or f"asset_{parsed_asset_id}")
        local_filename = f"{parsed_asset_id}_{safe_name}"
        local_path = (self.inputs_dir / local_filename).resolve()

        # Prevent directory traversal
        if not str(local_path).startswith(str(self.inputs_dir.resolve())):
            raise RenderInputMissingError("Invalid asset filename traversal detected")

        # Download if not already cached
        if not local_path.exists() or local_path.stat().st_size == 0:
            provider = storage_provider or get_storage_provider()
            try:
                provider.download_file(asset.storage_key, str(local_path))
            except Exception as e:
                raise RenderInputMissingError(
                    f"Failed to download asset {parsed_asset_id} from storage key '{asset.storage_key}': {str(e)}",
                    details={"asset_id": str(parsed_asset_id), "storage_key": asset.storage_key, "error": str(e)},
                )

        if not local_path.exists() or local_path.stat().st_size == 0:
            raise RenderInputMissingError(
                f"Asset {parsed_asset_id} downloaded 0 bytes from '{asset.storage_key}'",
                details={"asset_id": str(parsed_asset_id), "storage_key": asset.storage_key},
            )

        return local_path
