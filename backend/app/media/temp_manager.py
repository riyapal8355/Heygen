"""Isolated media temporary file and directory lifecycle manager.

Provides safe per-job scratch directories with automatic cleanup on normal exit,
errors, or cancellations to prevent disk leaks on media worker nodes.
"""

import os
import shutil
import tempfile
import uuid
from pathlib import Path
from types import TracebackType
from typing import Optional, Type, Union

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class MediaTempManager:
    """Context manager for temporary media processing scratch directories."""

    def __init__(
        self,
        job_id: Optional[Union[uuid.UUID, str]] = None,
        base_dir: Optional[Union[str, Path]] = None,
        auto_cleanup: bool = True,
        prefix: Optional[str] = None,
    ) -> None:
        raw_id = str(job_id or uuid.uuid4())
        self.job_id_str = f"{prefix}{raw_id}" if prefix else raw_id
        self.auto_cleanup = auto_cleanup
        settings = get_settings()

        resolved_base = (
            Path(base_dir)
            if base_dir
            else Path(settings.MEDIA_TEMP_DIR)
            if settings.MEDIA_TEMP_DIR
            else Path(tempfile.gettempdir()) / "heyzen_media"
        )
        self.temp_dir: Path = resolved_base / self.job_id_str

    def __enter__(self) -> Path:
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        return self.temp_dir

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        if self.auto_cleanup:
            self.cleanup()

    async def __aenter__(self) -> Path:
        return self.__enter__()

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        self.__exit__(exc_type, exc_val, exc_tb)

    def create_temp_file(self, suffix: str = ".tmp", prefix: str = "media_") -> Path:
        """Create a unique filepath inside the scratch directory without creating the file yet."""
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        unique_name = f"{prefix}{uuid.uuid4().hex[:8]}{suffix}"
        return self.temp_dir / unique_name

    def cleanup(self) -> None:
        """Safely remove the temporary directory and all contents."""
        if self.temp_dir.exists():
            try:
                shutil.rmtree(self.temp_dir, ignore_errors=True)
                logger.debug("Cleaned up media scratch directory: %s", self.temp_dir)
            except Exception as e:
                logger.warning("Failed to clean up scratch dir %s: %s", self.temp_dir, e)
