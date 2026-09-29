"""Unit and integration tests for Media Pipeline Foundation, FFmpeg abstraction, and scratch lifecycle."""

import uuid
from pathlib import Path
import pytest

from app.media.errors import (
    FFmpegNotFoundError,
    InvalidMediaFileError,
    MediaProcessingError,
    MediaTimeoutError,
)
from app.media.ffmpeg import FFmpegService, MediaProbeResult, _generate_minimal_png_bytes
from app.media.temp_manager import MediaTempManager
from app.ai.adapters.mock import _generate_synthetic_wav_bytes


def test_media_temp_manager_synchronous_lifecycle():
    """Verify MediaTempManager creates isolated directory and cleans up on exit."""
    job_id = uuid.uuid4()
    captured_dir: Path

    with MediaTempManager(job_id=job_id) as temp_dir:
        captured_dir = temp_dir
        assert captured_dir.exists()
        assert str(job_id) in str(captured_dir)

        # Create temporary file
        temp_file = captured_dir / "test_frame.png"
        temp_file.write_text("dummy frame data")
        assert temp_file.exists()

    # Directory should be cleaned up
    assert not captured_dir.exists()


@pytest.mark.asyncio
async def test_media_temp_manager_async_cleanup_on_error():
    """Verify MediaTempManager removes directory even when an unhandled exception occurs."""
    job_id = uuid.uuid4()
    captured_dir = None

    with pytest.raises(RuntimeError):
        async with MediaTempManager(job_id=job_id) as temp_dir:
            captured_dir = temp_dir
            assert captured_dir.exists()
            raise RuntimeError("Simulated pipeline crash during media encoding")

    assert captured_dir is not None
    assert not captured_dir.exists()


def test_media_temp_manager_create_temp_file():
    """Verify helper generates unique paths within scratch directory."""
    with MediaTempManager() as temp_dir:
        mgr = MediaTempManager()
        f1 = mgr.create_temp_file(suffix=".mp4", prefix="video_")
        f2 = mgr.create_temp_file(suffix=".mp4", prefix="video_")
        assert f1 != f2
        assert f1.suffix == ".mp4"
        assert f1.name.startswith("video_")


def test_media_error_taxonomy_retryable_classification():
    """Verify error classes carry correct retryable semantics for Celery."""
    base_err = MediaProcessingError("Base error")
    assert base_err.retryable is False

    timeout_err = MediaTimeoutError("Timeout")
    assert timeout_err.retryable is True
    assert timeout_err.code == "MEDIA_TIMEOUT"
    assert timeout_err.status_code == 504

    ffmpeg_not_found = FFmpegNotFoundError()
    assert ffmpeg_not_found.retryable is False
    assert ffmpeg_not_found.code == "FFMPEG_NOT_FOUND"
    assert ffmpeg_not_found.status_code == 500

    invalid_media = InvalidMediaFileError()
    assert invalid_media.retryable is False
    assert invalid_media.code == "INVALID_MEDIA_FILE"
    assert invalid_media.status_code == 400


@pytest.mark.asyncio
async def test_ffmpeg_service_missing_file_handling():
    """Verify FFmpegService raises InvalidMediaFileError on missing or empty files."""
    service = FFmpegService()

    with pytest.raises(InvalidMediaFileError) as exc_info:
        await service.probe("nonexistent_video_file_xyz123.mp4")
    assert "does not exist" in str(exc_info.value)


@pytest.mark.asyncio
async def test_ffmpeg_service_empty_file_handling():
    """Verify FFmpegService rejects zero-byte files."""
    service = FFmpegService()
    with MediaTempManager() as temp_dir:
        empty_file = temp_dir / "empty.wav"
        empty_file.touch()

        with pytest.raises(InvalidMediaFileError) as exc_info:
            await service.probe(empty_file)
        assert "empty" in str(exc_info.value)


@pytest.mark.asyncio
async def test_ffmpeg_service_uninstalled_strict_behavior():
    """Verify FFmpegService raises FFmpegNotFoundError when FFmpeg is not installed and fallback is disabled."""
    service = FFmpegService(ffmpeg_path="nonexistent_ffmpeg_bin_abc", ffprobe_path="nonexistent_ffprobe_bin_abc")
    assert service.is_available() is False

    with MediaTempManager() as temp_dir:
        wav_file = temp_dir / "test.wav"
        wav_file.write_bytes(_generate_synthetic_wav_bytes(duration_seconds=1.0))

        # Real execution requested without fallback
        with pytest.raises(FFmpegNotFoundError):
            await service.probe(wav_file, allow_mock_fallback=False)

        with pytest.raises(FFmpegNotFoundError):
            await service.normalize_audio(wav_file, temp_dir / "norm.wav", allow_mock_fallback=False)

        with pytest.raises(FFmpegNotFoundError):
            await service.extract_thumbnail(wav_file, temp_dir / "thumb.png", allow_mock_fallback=False)

        with pytest.raises(FFmpegNotFoundError):
            await service.compute_waveform(wav_file, allow_mock_fallback=False)


@pytest.mark.asyncio
async def test_ffmpeg_service_mock_fallback_mode():
    """Verify deterministic mock fallback when FFmpeg is not installed but allow_mock_fallback=True."""
    service = FFmpegService(ffmpeg_path="nonexistent_ffmpeg_bin_abc", ffprobe_path="nonexistent_ffprobe_bin_abc")

    with MediaTempManager() as temp_dir:
        wav_bytes = _generate_synthetic_wav_bytes(duration_seconds=2.0, sample_rate=24000)
        wav_file = temp_dir / "synth.wav"
        wav_file.write_bytes(wav_bytes)

        # 1. Probe synthetic WAV
        probe_res = await service.probe(wav_file, allow_mock_fallback=True)
        assert isinstance(probe_res, MediaProbeResult)
        assert probe_res.format_name == "wav"
        assert probe_res.sample_rate == 24000
        assert probe_res.duration_seconds >= 1.9

        # 2. Audio normalization fallback
        norm_output = temp_dir / "synth_norm.wav"
        await service.normalize_audio(wav_file, norm_output, allow_mock_fallback=True)
        assert norm_output.exists()
        assert norm_output.stat().st_size == wav_file.stat().st_size

        # 3. Waveform computation fallback
        waveform = await service.compute_waveform(wav_file, points=50, allow_mock_fallback=True)
        assert len(waveform) == 50
        assert all(0.0 <= pt <= 1.0 for pt in waveform)

        # 4. Thumbnail extraction fallback
        thumb_output = temp_dir / "thumb.png"
        await service.extract_thumbnail(wav_file, thumb_output, allow_mock_fallback=True)
        assert thumb_output.exists()
        header = thumb_output.read_bytes()[:8]
        assert header == b"\x89PNG\r\n\x1a\n"
