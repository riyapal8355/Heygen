"""Unit and integration tests for FFprobeService and render output validation."""

import tempfile
from pathlib import Path
import pytest

from app.ai.adapters.mock import _generate_synthetic_wav_bytes
from app.media.errors import (
    FFprobeNotFoundError,
    InvalidMediaFileError,
    RenderOutputInvalidError,
)
from app.media.ffmpeg import FFmpegService
from app.media.ffprobe import FFprobeService
from app.media.fixtures import create_valid_mock_mp4_fixture


def test_ffprobe_service_discovery():
    """Verify FFprobeService discovers installed ffprobe executable."""
    svc = FFprobeService()
    assert svc.is_available() is True
    assert svc.get_executable_path() is not None
    assert "ffprobe" in svc.get_executable_path().lower()


@pytest.mark.asyncio
async def test_ffprobe_service_probe_wav():
    """Verify real ffprobe accurately inspects WAV container."""
    svc = FFprobeService()
    with tempfile.TemporaryDirectory() as td:
        wav_path = Path(td) / "audio.wav"
        wav_path.write_bytes(_generate_synthetic_wav_bytes(duration_seconds=2.0, sample_rate=48000))

        probe = await svc.probe(wav_path)
        assert probe.duration_seconds >= 1.9
        assert probe.sample_rate == 48000
        assert len(probe.audio_streams) >= 1
        assert probe.format_name in ("wav", "riff")


@pytest.mark.asyncio
async def test_ffprobe_validate_render_output_success():
    """Verify validate_render_output accepts a valid generated video."""
    svc = FFprobeService()
    with tempfile.TemporaryDirectory() as td:
        mp4_path = Path(td) / "render.mp4"
        # Render a minimal valid video with real FFmpeg
        ffmpeg_svc = FFmpegService()
        await ffmpeg_svc.execute_ffmpeg([
            "-y",
            "-f", "lavfi", "-i", "color=c=black:s=640x360:r=30:d=1.5",
            "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-t", "1.5",
            str(mp4_path),
        ])

        result = await svc.validate_render_output(
            mp4_path,
            min_duration=1.0,
            require_video=True,
            require_audio=True,
        )
        assert result.duration_seconds >= 1.4
        assert result.width == 640
        assert result.height == 360
        assert len(result.video_streams) == 1
        assert len(result.audio_streams) == 1


@pytest.mark.asyncio
async def test_ffprobe_validate_render_output_rejections():
    """Verify validate_render_output rejects missing, empty, or stream-deficient files."""
    svc = FFprobeService()
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)

        # 1. Nonexistent file
        with pytest.raises(RenderOutputInvalidError) as exc_1:
            await svc.validate_render_output(td_path / "nonexistent.mp4")
        assert "does not exist" in str(exc_1.value)

        # 2. Empty file
        empty = td_path / "empty.mp4"
        empty.touch()
        with pytest.raises(RenderOutputInvalidError) as exc_2:
            await svc.validate_render_output(empty)
        assert "too small" in str(exc_2.value)

        # 3. Audio only when video is required
        wav_path = td_path / "sound.wav"
        wav_path.write_bytes(_generate_synthetic_wav_bytes(duration_seconds=2.0))
        with pytest.raises(RenderOutputInvalidError) as exc_3:
            await svc.validate_render_output(wav_path, require_video=True)
        assert "video streams" in str(exc_3.value)
