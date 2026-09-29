"""URL video ingestion service for YouTube, Google Drive, and public video URLs."""

import asyncio
import os
import re
import tempfile
import uuid
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urlparse

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, ValidationException
from app.core.logging import get_logger
from app.media.ffprobe import FFprobeService
from app.models.asset import Asset
from app.repositories.asset import AssetRepository
from app.storage.s3 import get_storage_provider

logger = get_logger(__name__)

ALLOWED_SCHEMES = {"http", "https"}


class UrlIngestionService:
    """Safely downloads and ingests remote video URLs (YouTube, Google Drive, direct links) into MinIO."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = AssetRepository(db)
        self.storage = get_storage_provider()
        self.ffprobe = FFprobeService()

    def validate_url(self, url: str) -> str:
        """Validate URL syntax and scheme."""
        clean_url = (url or "").strip()
        if not clean_url:
            raise ValidationException(
                code="INVALID_URL",
                message="Video URL cannot be empty.",
            )

        parsed = urlparse(clean_url)
        if parsed.scheme.lower() not in ALLOWED_SCHEMES or not parsed.netloc:
            raise ValidationException(
                code="INVALID_URL_SCHEME",
                message="Video URL must use http or https protocol.",
            )

        # Basic block for private/loopback addresses (SSRF mitigation)
        hostname = parsed.hostname or ""
        if hostname in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
            raise ValidationException(
                code="DISALLOWED_HOST",
                message="Localhost and internal network URLs are disallowed for security.",
            )

        return clean_url

    async def ingest_video_url(
        self,
        url: str,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Asset:
        """Download remote video via yt-dlp, inspect via FFprobe, and persist to MinIO as workspace Asset."""
        clean_url = self.validate_url(url)
        logger.info("Starting ingestion of video URL '%s' for workspace %s", clean_url, workspace_id)

        loop = asyncio.get_running_loop()

        def _download_sync(temp_dir: str) -> Tuple[str, str]:
            import yt_dlp

            out_template = os.path.join(temp_dir, "ingested_video.%(ext)s")
            ydl_opts = {
                "outtmpl": out_template,
                "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
                "merge_output_format": "mp4",
                "quiet": True,
                "no_warnings": True,
                "max_filesize": 500 * 1024 * 1024,  # 500 MB limit
                "socket_timeout": 30,
            }

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(clean_url, download=True)
                    title = info.get("title") or "Ingested Video"
                    # Determine actual output filename
                    downloaded_files = [
                        os.path.join(temp_dir, f)
                        for f in os.listdir(temp_dir)
                        if os.path.isfile(os.path.join(temp_dir, f)) and not f.endswith(".part")
                    ]
                    if not downloaded_files:
                        raise ValueError("No video file was produced by downloader.")

                    # Sort by size or modification
                    downloaded_files.sort(key=lambda p: os.path.getsize(p), reverse=True)
                    return downloaded_files[0], title
            except yt_dlp.utils.DownloadError as dl_err:
                clean_msg = str(dl_err).split(":")[-1].strip()
                raise ValidationException(
                    code="URL_DOWNLOAD_FAILED",
                    message=f"Unable to retrieve this video URL: {clean_msg or 'Video is unavailable or private.'}",
                )
            except Exception as exc:
                logger.error("Failed to download video from URL '%s': %s", clean_url, exc)
                raise ValidationException(
                    code="URL_DOWNLOAD_FAILED",
                    message=f"Unable to retrieve this video URL: {str(exc)}",
                )

        temp_dir = tempfile.mkdtemp(prefix="heyzen_url_ingest_")
        try:
            local_path, video_title = await loop.run_in_executor(None, _download_sync, temp_dir)

            if not os.path.isfile(local_path) or os.path.getsize(local_path) == 0:
                raise ValidationException(
                    code="EMPTY_MEDIA_FILE",
                    message="Downloaded media file is empty (0 bytes).",
                )

            # Probe media with FFprobe
            try:
                probe_res = await self.ffprobe.probe(local_path)
            except Exception as probe_err:
                raise ValidationException(
                    code="INVALID_SOURCE",
                    message=f"Unable to process this video: Media analysis failed ({probe_err}).",
                )

            if not probe_res.has_video:
                raise ValidationException(
                    code="NO_VIDEO_STREAM",
                    message="Unable to process this video: File does not contain a valid video stream.",
                )

            file_size = os.path.getsize(local_path)
            asset_id = uuid.uuid4()
            safe_title = re.sub(r"[^a-zA-Z0-9_.-]", "_", video_title).strip("_") or "ingested_video"
            filename = f"{safe_title}.mp4"
            storage_key = f"workspaces/{workspace_id}/assets/{asset_id}/{filename}"
            mime_type = "video/mp4"

            # Upload to MinIO/S3
            await loop.run_in_executor(
                None,
                self.storage.upload_file,
                local_path,
                storage_key,
                mime_type,
            )

            # Register Asset in database
            asset = Asset(
                id=asset_id,
                workspace_id=workspace_id,
                created_by=user_id,
                original_filename=filename,
                storage_bucket=self.storage.bucket_name,
                storage_key=storage_key,
                mime_type=mime_type,
                size_bytes=file_size,
                asset_type="video",
                status="ready",
                extra_metadata={
                    "source_url": clean_url,
                    "duration": probe_res.duration_seconds,
                    "width": probe_res.width,
                    "height": probe_res.height,
                    "fps": probe_res.fps,
                    "has_audio": probe_res.has_audio,
                },
            )
            await self.repo.create(asset)
            await self.db.commit()
            await self.db.refresh(asset)

            logger.info("Successfully ingested video from URL '%s' as asset %s", clean_url, asset.id)
            return asset

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
