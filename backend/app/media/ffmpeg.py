"""FFmpeg and FFprobe subprocess execution abstraction.

Provides cross-platform media inspection, audio normalization, thumbnail extraction,
and waveform calculation with strict error handling, subprocess timeouts,
and deterministic fallback for test and mock environments.
"""

import asyncio
import math
import os
import shutil
import struct
import zlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from app.core.config import get_settings
from app.core.logging import get_logger
from app.media.discovery import find_media_binary
from app.media.errors import (
    FFmpegFailedError,
    FFmpegNotFoundError,
    FFprobeNotFoundError,
    InvalidMediaFileError,
    MediaProcessingError,
    MediaTimeoutError,
)
from app.media.ffprobe import FFprobeService
from app.media.models import MediaProbeResult

logger = get_logger(__name__)


def _generate_minimal_png_bytes(width: int = 64, height: int = 64) -> bytes:
    """Generate a minimal valid RGBA PNG binary in pure Python."""
    # PNG signature
    png_signature = b"\x89PNG\r\n\x1a\n"
    # IHDR chunk: width (4 bytes), height (4 bytes), bit depth 8 (1), color type 6 (RGBA, 1),
    # compression 0 (1), filter 0 (1), interlace 0 (1)
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    ihdr_crc = struct.pack(">I", zlib.crc32(b"IHDR" + ihdr_data) & 0xFFFFFFFF)
    ihdr_chunk = struct.pack(">I", len(ihdr_data)) + b"IHDR" + ihdr_data + ihdr_crc

    # IDAT chunk: raw scanlines (1 filter byte 0 + 4 bytes RGBA per pixel)
    raw_scanlines = bytearray()
    for _ in range(height):
        raw_scanlines.append(0)  # Filter type 0 (None)
        raw_scanlines.extend(b"\x20\x50\x80\xFF" * width)  # Blueish gray pixel

    compressed_idat = zlib.compress(bytes(raw_scanlines))
    idat_crc = struct.pack(">I", zlib.crc32(b"IDAT" + compressed_idat) & 0xFFFFFFFF)
    idat_chunk = struct.pack(">I", len(compressed_idat)) + b"IDAT" + compressed_idat + idat_crc

    # IEND chunk
    iend_crc = struct.pack(">I", zlib.crc32(b"IEND") & 0xFFFFFFFF)
    iend_chunk = struct.pack(">I", 0) + b"IEND" + iend_crc

    return png_signature + ihdr_chunk + idat_chunk + iend_chunk


class FFmpegService:
    """Subprocess abstraction for FFmpeg and FFprobe media operations."""

    def __init__(
        self,
        ffmpeg_path: Optional[str] = None,
        ffprobe_path: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
    ) -> None:
        settings = get_settings()
        configured_ffmpeg = ffmpeg_path or getattr(settings, "FFMPEG_PATH", "ffmpeg")
        configured_ffprobe = ffprobe_path or getattr(settings, "FFPROBE_PATH", "ffprobe")

        self._resolved_ffmpeg = find_media_binary("ffmpeg", configured_ffmpeg)
        self._resolved_ffprobe = find_media_binary("ffprobe", configured_ffprobe)

        self.ffmpeg_path = self._resolved_ffmpeg or configured_ffmpeg
        self.ffprobe_path = self._resolved_ffprobe or configured_ffprobe
        self.timeout_seconds = timeout_seconds or getattr(settings, "MEDIA_TIMEOUT_SECONDS", 300)

        # Delegate probing to dedicated FFprobeService
        self.ffprobe_service = FFprobeService(
            ffprobe_path=self.ffprobe_path,
            timeout_seconds=self.timeout_seconds,
        )

    def is_ffmpeg_available(self) -> bool:
        """Check whether the ffmpeg binary is discoverable and available."""
        if self._resolved_ffmpeg and os.path.exists(self._resolved_ffmpeg):
            return True
        found = find_media_binary("ffmpeg", self.ffmpeg_path)
        if found:
            self._resolved_ffmpeg = found
            return True
        return False

    def is_ffprobe_available(self) -> bool:
        """Check whether the ffprobe binary is discoverable and available."""
        return self.ffprobe_service.is_available()

    def is_available(self) -> bool:
        """Check whether both ffmpeg and ffprobe binaries are available."""
        return self.is_ffmpeg_available() and self.is_ffprobe_available()

    def get_ffmpeg_executable(self) -> Optional[str]:
        """Return the resolved absolute path to the ffmpeg executable."""
        if self.is_ffmpeg_available():
            return self._resolved_ffmpeg
        return None

    def get_ffprobe_executable(self) -> Optional[str]:
        """Return the resolved absolute path to the ffprobe executable."""
        return self.ffprobe_service.get_executable_path()

    async def execute_ffmpeg(
        self,
        args: List[str],
        timeout: Optional[int] = None,
        cwd: Optional[Union[str, Path]] = None,
    ) -> bytes:
        """Safely execute an FFmpeg command with timeout and error classification.

        Args:
            args: Argument list to pass to ffmpeg (excluding the binary itself).
            timeout: Optional custom timeout in seconds.
            cwd: Working directory for execution.

        Returns:
            stdout bytes on success.

        Raises:
            FFmpegNotFoundError: If ffmpeg binary is not available.
            MediaTimeoutError: If execution exceeds timeout duration.
            FFmpegFailedError: If ffmpeg returns non-zero exit status.
        """
        if not self.is_ffmpeg_available():
            raise FFmpegNotFoundError("FFmpeg executable not found. Cannot run FFmpeg command.")

        exe = self.get_ffmpeg_executable() or "ffmpeg"
        cmd = [exe] + args
        working_dir = str(cwd) if cwd else None
        exec_timeout = timeout or self.timeout_seconds

        proc = None
        stdout = b""
        stderr = b""
        returncode = -1
        try:
            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=working_dir,
                )
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=exec_timeout,
                )
                returncode = proc.returncode
            except NotImplementedError:
                import subprocess
                def _run_ffmpeg_sync():
                    return subprocess.run(
                        cmd,
                        capture_output=True,
                        cwd=working_dir,
                        timeout=exec_timeout,
                    )
                sync_res = await asyncio.to_thread(_run_ffmpeg_sync)
                stdout, stderr, returncode = sync_res.stdout, sync_res.stderr, sync_res.returncode
        except asyncio.TimeoutError:
            if proc:
                try:
                    proc.kill()
                    await proc.wait()
                except Exception:
                    pass
            raise MediaTimeoutError(f"FFmpeg command timed out after {exec_timeout}s")
        except Exception as e:
            if isinstance(e, (MediaTimeoutError, FFmpegFailedError)):
                raise
            raise MediaProcessingError(f"Failed to launch FFmpeg subprocess: {str(e)}")

        if returncode != 0:
            err_msg = stderr.decode("utf-8", errors="replace").strip()
            # Capture last 10 lines of stderr for clean diagnostics
            summary = "\n".join(err_msg.splitlines()[-10:])
            raise FFmpegFailedError(
                f"FFmpeg command failed with exit code {proc.returncode}: {summary}",
                details={"exit_code": proc.returncode, "stderr": summary},
            )

        return stdout

    async def probe(
        self,
        file_path: Union[str, Path],
        allow_mock_fallback: bool = False,
    ) -> MediaProbeResult:
        """Inspect media file structure and metadata via FFprobeService."""
        if not self.is_ffprobe_available():
            if not allow_mock_fallback:
                raise FFprobeNotFoundError(
                    "FFprobe executable is not available in system PATH. Cannot perform real media probe."
                )
        return await self.ffprobe_service.probe(file_path, allow_mock_fallback=allow_mock_fallback)

    async def normalize_audio(
        self,
        input_wav: Union[str, Path],
        output_wav: Union[str, Path],
        target_lufs: float = -16.0,
        allow_mock_fallback: bool = False,
    ) -> Path:
        """Normalize audio volume using EBU R128 loudness filter (-16 LUFS broadcast standard)."""
        in_path = Path(input_wav).resolve()
        out_path = Path(output_wav).resolve()

        if not in_path.exists():
            raise InvalidMediaFileError(f"Input audio file not found: {in_path}")

        out_path.parent.mkdir(parents=True, exist_ok=True)

        if self.is_ffmpeg_available():
            args = [
                "-y",
                "-i", str(in_path),
                "-af", f"loudnorm=I={target_lufs}:TP=-1.5:LRA=11",
                "-ar", "24000",
                str(out_path),
            ]
            await self.execute_ffmpeg(args)
            return out_path

        if not allow_mock_fallback:
            raise FFmpegNotFoundError(
                "FFmpeg executable not found in system PATH. Cannot perform real audio normalization."
            )

        # Deterministic mock copy/normalization for isolated unit tests
        shutil.copy2(in_path, out_path)
        return out_path

    async def extract_thumbnail(
        self,
        video_path: Union[str, Path],
        output_png: Union[str, Path],
        timestamp: float = 1.0,
        allow_mock_fallback: bool = False,
    ) -> Path:
        """Extract a single frame image from a video at the specified timestamp."""
        in_path = Path(video_path).resolve()
        out_path = Path(output_png).resolve()

        if not in_path.exists():
            raise InvalidMediaFileError(f"Source video file not found: {in_path}")

        out_path.parent.mkdir(parents=True, exist_ok=True)

        if self.is_ffmpeg_available():
            args = [
                "-y",
                "-ss", str(max(0.0, timestamp)),
                "-i", str(in_path),
                "-vframes", "1",
                "-f", "image2",
                str(out_path),
            ]
            await self.execute_ffmpeg(args)
            return out_path

        if not allow_mock_fallback:
            raise FFmpegNotFoundError(
                "FFmpeg executable not found in system PATH. Cannot perform real thumbnail extraction."
            )

        # Deterministic mock thumbnail generation for isolated unit tests
        png_data = _generate_minimal_png_bytes(width=64, height=64)
        out_path.write_bytes(png_data)
        return out_path

    async def compute_waveform(
        self,
        audio_path: Union[str, Path],
        points: int = 100,
        allow_mock_fallback: bool = False,
    ) -> List[float]:
        """Compute downsampled normalized peak amplitudes between 0.0 and 1.0 for UI audio wave display."""
        in_path = Path(audio_path).resolve()
        if not in_path.exists():
            raise InvalidMediaFileError(f"Audio file not found: {in_path}")

        points = max(10, min(points, 2000))

        if self.is_ffmpeg_available():
            args = [
                "-y",
                "-i", str(in_path),
                "-ac", "1",
                "-ar", "8000",
                "-f", "s16le",
                "-",
            ]
            raw_pcm = await self.execute_ffmpeg(args)
            if len(raw_pcm) >= 2:
                sample_count = len(raw_pcm) // 2
                samples = struct.unpack(f"<{sample_count}h", raw_pcm[: sample_count * 2])
                step = max(1, sample_count // points)
                peaks = []
                for i in range(0, sample_count, step):
                    chunk = samples[i : i + step]
                    max_val = max(abs(s) for s in chunk) if chunk else 0
                    peaks.append(round(min(1.0, max_val / 32767.0), 3))
                return peaks[:points]

        if not allow_mock_fallback:
            raise FFmpegNotFoundError(
                "FFmpeg executable not found in system PATH. Cannot perform real waveform calculation."
            )

        # Deterministic mock sinusoidal waveform envelope for isolated unit tests
        waveform = []
        for i in range(points):
            angle = (i / points) * 2 * math.pi * 3
            val = abs(math.sin(angle)) * 0.7 + 0.15
            waveform.append(round(val, 3))
        return waveform
