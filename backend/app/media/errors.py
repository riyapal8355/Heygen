"""Media processing and external binary exception definitions."""

from typing import Any, Optional
from fastapi import status
from app.core.exceptions import AppException


class MediaProcessingError(AppException):
    """Base exception for audio/video media operations."""

    def __init__(
        self,
        message: str = "A media processing error occurred.",
        code: str = "MEDIA_PROCESSING_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Any] = None,
        retryable: bool = False,
    ):
        super().__init__(
            status_code=status_code,
            code=code,
            message=message,
            details=details,
            retryable=retryable,
        )


class FFmpegNotFoundError(MediaProcessingError):
    """Raised when external ffmpeg or ffprobe executable is not available in system PATH."""

    def __init__(
        self,
        message: str = "FFmpeg or FFprobe executable not found in system PATH. Cannot perform requested real media processing.",
        code: str = "FFMPEG_NOT_FOUND",
        details: Optional[Any] = None,
    ):
        super().__init__(
            message=message,
            code=code,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
            retryable=False,
        )


class MediaTimeoutError(MediaProcessingError):
    """Raised when an external media subprocess exceeds maximum allowed execution duration."""

    def __init__(
        self,
        message: str = "Media processing subprocess timed out.",
        code: str = "MEDIA_TIMEOUT",
        details: Optional[Any] = None,
    ):
        super().__init__(
            message=message,
            code=code,
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            details=details,
            retryable=True,
        )


class InvalidMediaFileError(MediaProcessingError):
    """Raised when an input media file is corrupted, empty, or an unsupported container."""

    def __init__(
        self,
        message: str = "The specified media file is invalid or corrupted.",
        code: str = "INVALID_MEDIA_FILE",
        details: Optional[Any] = None,
    ):
        super().__init__(
            message=message,
            code=code,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
            retryable=False,
        )


class FFprobeNotFoundError(FFmpegNotFoundError):
    """Raised when ffprobe executable is not available in system PATH."""

    def __init__(
        self,
        message: str = "FFprobe executable not found in system PATH. Cannot perform requested real media probe.",
        code: str = "FFPROBE_NOT_FOUND",
        details: Optional[Any] = None,
    ):
        super().__init__(
            message=message,
            code=code,
            details=details,
        )


class FFmpegFailedError(MediaProcessingError):
    """Raised when an external ffmpeg process fails with non-zero exit code."""

    def __init__(
        self,
        message: str = "FFmpeg process execution failed.",
        code: str = "FFMPEG_FAILED",
        details: Optional[Any] = None,
    ):
        super().__init__(
            message=message,
            code=code,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
            retryable=False,
        )


class UnsupportedMediaError(MediaProcessingError):
    """Raised when input media has an unsupported codec, pixel format, or layout."""

    def __init__(
        self,
        message: str = "The media format or codec is not supported for rendering.",
        code: str = "UNSUPPORTED_MEDIA",
        details: Optional[Any] = None,
    ):
        super().__init__(
            message=message,
            code=code,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
            retryable=False,
        )


class RenderInputMissingError(MediaProcessingError):
    """Raised when a required media asset (speech audio, image, video) is missing."""

    def __init__(
        self,
        message: str = "A required input asset for rendering could not be found or resolved.",
        code: str = "RENDER_INPUT_MISSING",
        details: Optional[Any] = None,
    ):
        super().__init__(
            message=message,
            code=code,
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
            retryable=False,
        )


class RenderOutputInvalidError(MediaProcessingError):
    """Raised when render completes but output validation fails (0-byte, corrupt, missing streams)."""

    def __init__(
        self,
        message: str = "Rendered media output failed validation checks.",
        code: str = "RENDER_OUTPUT_INVALID",
        details: Optional[Any] = None,
    ):
        super().__init__(
            message=message,
            code=code,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
            retryable=False,
        )
