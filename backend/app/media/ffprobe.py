"""Dedicated FFprobe media inspection and stream validation service.

Provides container-level metadata inspection, stream detection, duration, codec,
and deterministic validation of rendered audio/video outputs.
"""

import asyncio
import json
import os
import struct
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from app.core.config import get_settings
from app.core.logging import get_logger
from app.media.discovery import find_media_binary
from app.media.errors import (
    FFprobeNotFoundError,
    InvalidMediaFileError,
    MediaProcessingError,
    MediaTimeoutError,
    RenderOutputInvalidError,
)
from app.media.models import MediaProbeResult

logger = get_logger(__name__)


class FFprobeService:
    """Subprocess abstraction for ffprobe inspection and output stream validation."""

    def __init__(
        self,
        ffprobe_path: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
    ) -> None:
        settings = get_settings()
        configured_path = ffprobe_path or getattr(settings, "FFPROBE_PATH", "ffprobe")
        self._resolved_path = find_media_binary("ffprobe", configured_path)
        self.ffprobe_path = self._resolved_path or configured_path
        self.timeout_seconds = timeout_seconds or getattr(settings, "MEDIA_TIMEOUT_SECONDS", 300)

    def is_available(self) -> bool:
        """Check whether the ffprobe binary is available."""
        if self._resolved_path and os.path.exists(self._resolved_path):
            return True
        found = find_media_binary("ffprobe", self.ffprobe_path)
        if found:
            self._resolved_path = found
            return True
        return False

    def get_executable_path(self) -> Optional[str]:
        """Return the resolved absolute path to the ffprobe executable, if available."""
        if self.is_available():
            return self._resolved_path
        return None

    async def probe(
        self,
        file_path: Union[str, Path],
        allow_mock_fallback: bool = False,
    ) -> MediaProbeResult:
        """Inspect media file structure and metadata via ffprobe or mock fallback.

        Args:
            file_path: Path to the target audio/video/image file.
            allow_mock_fallback: Whether to allow synthetic inspection if ffprobe is absent.
                                 NOTE: Permitted ONLY in isolated mock unit tests.

        Returns:
            MediaProbeResult with verified container metrics and streams.

        Raises:
            InvalidMediaFileError: If file is missing, empty, or unparseable.
            FFprobeNotFoundError: If ffprobe binary is unavailable and mock fallback disabled.
            MediaTimeoutError: If ffprobe inspection exceeds timeout.
        """
        target_path = Path(file_path).resolve()
        if not target_path.exists():
            raise InvalidMediaFileError(f"Target media file does not exist: {target_path}")

        file_size = target_path.stat().st_size
        if file_size == 0:
            raise InvalidMediaFileError(f"Target media file is empty (0 bytes): {target_path}")

        # Real ffprobe execution
        if self.is_available():
            exe = self.get_executable_path() or "ffprobe"
            cmd = [
                exe,
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                str(target_path),
            ]
            try:
                try:
                    proc = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    stdout, stderr = await asyncio.wait_for(
                        proc.communicate(),
                        timeout=self.timeout_seconds,
                    )
                    returncode = proc.returncode
                except NotImplementedError:
                    import subprocess
                    def _probe_sync():
                        return subprocess.run(
                            cmd,
                            capture_output=True,
                            timeout=self.timeout_seconds,
                        )
                    sync_res = await asyncio.to_thread(_probe_sync)
                    stdout, stderr, returncode = sync_res.stdout, sync_res.stderr, sync_res.returncode
            except asyncio.TimeoutError:
                raise MediaTimeoutError(
                    f"ffprobe timed out after {self.timeout_seconds}s inspecting {target_path.name}"
                )
            except Exception as e:
                raise MediaProcessingError(f"Failed to execute ffprobe: {str(e)}")

            if returncode != 0:
                if allow_mock_fallback:
                    return self._mock_probe(target_path, file_size)
                err_msg = stderr.decode("utf-8", errors="replace").strip()
                raise InvalidMediaFileError(f"ffprobe failed to parse media: {err_msg}")

            try:
                data = json.loads(stdout.decode("utf-8", errors="replace"))
                format_info = data.get("format", {})
                streams = data.get("streams", [])

                video_streams = [s for s in streams if s.get("codec_type") == "video"]
                audio_streams = [s for s in streams if s.get("codec_type") == "audio"]

                width = int(video_streams[0]["width"]) if video_streams and "width" in video_streams[0] else None
                height = int(video_streams[0]["height"]) if video_streams and "height" in video_streams[0] else None
                fps = None
                if video_streams and "r_frame_rate" in video_streams[0]:
                    rate_parts = video_streams[0]["r_frame_rate"].split("/")
                    if len(rate_parts) == 2 and float(rate_parts[1]) > 0:
                        fps = round(float(rate_parts[0]) / float(rate_parts[1]), 2)

                sample_rate = int(audio_streams[0]["sample_rate"]) if audio_streams and "sample_rate" in audio_streams[0] else None
                channels = int(audio_streams[0]["channels"]) if audio_streams and "channels" in audio_streams[0] else None
                codec = (
                    video_streams[0].get("codec_name")
                    if video_streams
                    else audio_streams[0].get("codec_name")
                    if audio_streams
                    else None
                )

                duration = float(format_info.get("duration", 0.0))
                bit_rate = int(format_info.get("bit_rate")) if format_info.get("bit_rate") else None

                return MediaProbeResult(
                    duration_seconds=duration,
                    format_name=format_info.get("format_name", target_path.suffix.lstrip(".")),
                    size_bytes=int(format_info.get("size", file_size)),
                    bit_rate=bit_rate,
                    video_streams=video_streams,
                    audio_streams=audio_streams,
                    width=width,
                    height=height,
                    fps=fps,
                    sample_rate=sample_rate,
                    channels=channels,
                    codec_name=codec,
                )
            except Exception as parse_err:
                raise InvalidMediaFileError(f"Failed to parse ffprobe output: {parse_err}")

        # If not available and fallback not permitted
        if not allow_mock_fallback:
            raise FFprobeNotFoundError(
                "FFprobe executable is not available in system PATH. Cannot perform real media probe."
            )

        # Deterministic mock inspection for isolated unit tests
        return self._mock_probe(target_path, file_size)

    def _mock_probe(self, target_path: Path, file_size: int) -> MediaProbeResult:
        """Deterministic mock probe parsing basic file headers for unit tests."""
        ext = target_path.suffix.lower().lstrip(".")
        with open(target_path, "rb") as f:
            header = f.read(64)

        if header[:4] == b"RIFF" and header[8:12] == b"WAVE":
            sample_rate = 24000
            channels = 1
            if len(header) >= 32:
                try:
                    channels = struct.unpack_from("<H", header, 22)[0]
                    sample_rate = struct.unpack_from("<I", header, 24)[0]
                except Exception:
                    pass
            duration = round((file_size - 44) / max(1, sample_rate * channels * 2), 2)
            return MediaProbeResult(
                duration_seconds=max(0.1, duration),
                format_name="wav",
                size_bytes=file_size,
                sample_rate=sample_rate,
                channels=channels,
                codec_name="pcm_s16le",
                audio_streams=[{"codec_name": "pcm_s16le", "sample_rate": sample_rate, "channels": channels}],
            )

        if header[:8] == b"\x89PNG\r\n\x1a\n":
            width, height = 1920, 1080
            if len(header) >= 24:
                try:
                    width, height = struct.unpack_from(">II", header, 16)
                except Exception:
                    pass
            return MediaProbeResult(
                duration_seconds=0.0,
                format_name="png",
                size_bytes=file_size,
                width=width,
                height=height,
                codec_name="png",
                video_streams=[{"codec_name": "png", "width": width, "height": height}],
            )

        # General video/audio mock fallback probe
        return MediaProbeResult(
            duration_seconds=10.0,
            format_name=ext or "mp4",
            size_bytes=file_size,
            width=1920 if ext in ("mp4", "webm", "mov") else None,
            height=1080 if ext in ("mp4", "webm", "mov") else None,
            fps=30.0 if ext in ("mp4", "webm", "mov") else None,
            sample_rate=48000,
            channels=2,
            codec_name="h264" if ext in ("mp4", "webm") else "aac",
            video_streams=[{"width": 1920, "height": 1080, "fps": 30.0}] if ext in ("mp4", "webm") else [],
            audio_streams=[{"sample_rate": 48000, "channels": 2}],
        )

    async def validate_render_output(
        self,
        file_path: Union[str, Path],
        min_duration: float = 0.1,
        require_video: bool = True,
        require_audio: bool = False,
        allow_mock_fallback: bool = False,
    ) -> MediaProbeResult:
        """Strictly validate rendered media file to ensure it is not corrupt, empty, or truncated.

        Args:
            file_path: Path to rendered output file.
            min_duration: Minimum required duration in seconds.
            require_video: Whether a video stream with valid dimensions is required.
            require_audio: Whether an audio stream is required.
            allow_mock_fallback: Whether mock inspection is allowed (mock unit tests only).

        Returns:
            MediaProbeResult on successful verification.

        Raises:
            RenderOutputInvalidError: If file is missing, empty, shorter than min_duration,
                                      or missing required streams.
        """
        target = Path(file_path).resolve()
        if not target.exists():
            raise RenderOutputInvalidError(f"Render output file does not exist: {target}")

        file_size = target.stat().st_size
        if file_size < 100:
            raise RenderOutputInvalidError(
                f"Render output file is too small ({file_size} bytes) to be a valid media container"
            )

        try:
            probe_result = await self.probe(target, allow_mock_fallback=allow_mock_fallback)
        except Exception as e:
            raise RenderOutputInvalidError(f"Failed to probe rendered media output: {str(e)}")

        if probe_result.duration_seconds < min_duration:
            raise RenderOutputInvalidError(
                f"Render output duration {probe_result.duration_seconds}s is below minimum {min_duration}s"
            )

        if require_video:
            if not probe_result.video_streams:
                raise RenderOutputInvalidError("Render output does not contain any video streams")
            if not probe_result.width or not probe_result.height or probe_result.width <= 0 or probe_result.height <= 0:
                raise RenderOutputInvalidError(
                    f"Render output has invalid video dimensions: {probe_result.width}x{probe_result.height}"
                )

        if require_audio:
            if not probe_result.audio_streams:
                raise RenderOutputInvalidError("Render output is missing required audio streams")

        return probe_result
