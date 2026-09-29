"""Unit and integration tests for real FFmpegService subprocess execution."""

import tempfile
from pathlib import Path
import pytest

from app.ai.adapters.mock import _generate_synthetic_wav_bytes
from app.media.errors import FFmpegFailedError, FFmpegNotFoundError, InvalidMediaFileError
from app.media.ffmpeg import FFmpegService


def test_ffmpeg_service_real_discovery():
    """Verify FFmpegService discovers real installed ffmpeg binary."""
    svc = FFmpegService()
    assert svc.is_available() is True
    assert svc.is_ffmpeg_available() is True
    assert svc.get_ffmpeg_executable() is not None
    assert "ffmpeg" in svc.get_ffmpeg_executable().lower()


@pytest.mark.asyncio
async def test_ffmpeg_service_execute_ffmpeg_success_and_failure():
    """Verify execute_ffmpeg runs real ffmpeg and raises FFmpegFailedError on error exit."""
    svc = FFmpegService()

    # Success: version output
    out = await svc.execute_ffmpeg(["-version"])
    assert b"ffmpeg version" in out

    # Failure: invalid syntax
    with pytest.raises(FFmpegFailedError) as exc_info:
        await svc.execute_ffmpeg(["-invalid_unrecognized_argument_xyz"])
    assert exc_info.value.code == "FFMPEG_FAILED"


@pytest.mark.asyncio
async def test_ffmpeg_service_audio_normalization():
    """Verify real FFmpeg audio normalization with EBU R128 filter."""
    svc = FFmpegService()
    with tempfile.TemporaryDirectory() as td:
        in_wav = Path(td) / "input.wav"
        in_wav.write_bytes(_generate_synthetic_wav_bytes(duration_seconds=1.5, sample_rate=24000))

        out_wav = Path(td) / "normalized.wav"
        res_path = await svc.normalize_audio(in_wav, out_wav, target_lufs=-16.0)

        assert res_path.exists()
        assert res_path.stat().st_size > 1000


@pytest.mark.asyncio
async def test_ffmpeg_service_extract_thumbnail():
    """Verify real FFmpeg frame extraction to PNG."""
    svc = FFmpegService()
    with tempfile.TemporaryDirectory() as td:
        # Create 1s MP4 video first
        vid_path = Path(td) / "input.mp4"
        await svc.execute_ffmpeg([
            "-y",
            "-f", "lavfi", "-i", "color=c=blue:s=320x240:r=30:d=1.0",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            str(vid_path),
        ])

        out_thumb = Path(td) / "thumb.png"
        res = await svc.extract_thumbnail(vid_path, out_thumb, timestamp=0.5)

        assert res.exists()
        assert res.stat().st_size > 100
        # Check PNG header signature
        with open(res, "rb") as f:
            header = f.read(8)
            assert header == b"\x89PNG\r\n\x1a\n"


@pytest.mark.asyncio
async def test_ffmpeg_service_compute_waveform():
    """Verify real FFmpeg PCM downsampled waveform peaks extraction."""
    svc = FFmpegService()
    with tempfile.TemporaryDirectory() as td:
        wav_path = Path(td) / "audio.wav"
        wav_path.write_bytes(_generate_synthetic_wav_bytes(duration_seconds=2.0))

        peaks = await svc.compute_waveform(wav_path, points=50)
        assert len(peaks) == 50
        assert all(0.0 <= p <= 1.0 for p in peaks)
