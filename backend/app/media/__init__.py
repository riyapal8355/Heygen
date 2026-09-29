"""HeyZen Media Processing and Subprocess Foundation."""

from app.media.compositor import TimelineCompositor
from app.media.discovery import find_media_binary
from app.media.errors import (
    FFmpegFailedError,
    FFmpegNotFoundError,
    FFprobeNotFoundError,
    InvalidMediaFileError,
    MediaProcessingError,
    MediaTimeoutError,
    RenderInputMissingError,
    RenderOutputInvalidError,
    UnsupportedMediaError,
)
from app.media.ffmpeg import FFmpegService
from app.media.ffprobe import FFprobeService
from app.media.models import CanvasProfile, MediaProbeResult, MediaStreamInfo, RenderResult
from app.media.temp_manager import MediaTempManager
from app.media.workspace import MediaWorkspace

__all__ = [
    "FFmpegService",
    "FFprobeService",
    "TimelineCompositor",
    "MediaWorkspace",
    "CanvasProfile",
    "MediaProbeResult",
    "MediaStreamInfo",
    "RenderResult",
    "MediaTempManager",
    "find_media_binary",
    "MediaProcessingError",
    "FFmpegNotFoundError",
    "FFprobeNotFoundError",
    "FFmpegFailedError",
    "MediaTimeoutError",
    "InvalidMediaFileError",
    "UnsupportedMediaError",
    "RenderInputMissingError",
    "RenderOutputInvalidError",
]
