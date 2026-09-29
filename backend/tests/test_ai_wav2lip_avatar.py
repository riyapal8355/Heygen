"""Unit tests for Wav2Lip-ONNX CPU Avatar Provider adapter.

Validates:
- Research-Only / Non-Commercial license classification and declarative descriptor.
- Mel filterbank and 80-channel log-mel spectrogram extraction.
- YuNet face detection and portrait center-crop fallback.
- Real end-to-end neural lip-sync frame synthesis and MP4 container encoding on CPU.
- Input validation safeguards and error handling.
- Resource cleanup and session unload lifecycle.
"""

import cv2
import numpy as np
import pytest

from app.ai.adapters.wav2lip import (
    DEFAULT_WAV2LIP_MODEL_ID,
    ValidationException,
    Wav2LipONNXAvatarProvider,
    _mel_filterbank,
    compute_mel_spectrogram,
)
from app.ai.contracts import LipSyncContractRequest, MediaAssetRef
from app.core.exceptions import NotFoundException
from app.media.ffmpeg import FFmpegService
from app.media.ffprobe import FFprobeService


def _create_synthetic_wav_bytes(duration_seconds: float = 1.0, sample_rate: int = 16000) -> bytes:
    """Generate minimal valid PCM WAV bytes with a sine wave tone."""
    import io
    import wave

    t = np.linspace(0, duration_seconds, int(sample_rate * duration_seconds), endpoint=False)
    waveform = (np.sin(2 * np.pi * 440.0 * t) * 16000).astype(np.int16)

    bio = io.BytesIO()
    with wave.open(bio, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(waveform.tobytes())
    return bio.getvalue()


def _create_synthetic_portrait_image_bytes(width: int = 320, height: int = 320) -> bytes:
    """Generate synthetic portrait image bytes with face-like geometry."""
    img = np.ones((height, width, 3), dtype=np.uint8) * 230
    # Head
    cv2.circle(img, (width // 2, height // 2), int(min(width, height) * 0.35), (180, 210, 240), -1)
    # Eyes
    cv2.circle(img, (int(width * 0.4), int(height * 0.4)), 8, (50, 50, 50), -1)
    cv2.circle(img, (int(width * 0.6), int(height * 0.4)), 8, (50, 50, 50), -1)
    # Mouth
    cv2.ellipse(img, (width // 2, int(height * 0.65)), (25, 12), 0, 0, 180, (50, 50, 180), -1)
    _, buf = cv2.imencode(".png", img)
    return buf.tobytes()


def test_wav2lip_descriptor_research_only_classification():
    """Verify Wav2Lip-ONNX descriptor explicitly records research-only non-commercial status."""
    provider = Wav2LipONNXAvatarProvider()
    desc = provider.descriptor

    assert desc.name == "wav2lip"
    assert desc.capability == "avatar"
    assert desc.is_local is True
    assert desc.requires_gpu is False
    assert desc.supported_output_formats == ["mp4", "webm"]
    assert desc.is_available is True

    meta = desc.metadata
    assert meta["engine"] == "Wav2Lip-ONNX"
    assert meta["runtime"] == "onnxruntime-cpu"
    assert meta["commercial_permitted"] is False
    assert meta["research_only"] is True
    assert meta["license_classification"] == "RESEARCH_ONLY"
    assert meta["notes"] == "Real CPU lip-sync verified using research-only Wav2Lip-ONNX."


def test_mel_filterbank_and_spectrogram_computation():
    """Verify triangular Mel filterbank matrix and normalized 80-channel log-mel spectrogram."""
    sr = 16000
    filterbank = _mel_filterbank(sr=sr, n_fft=800, n_mels=80)
    assert filterbank.shape == (80, 401)
    assert np.all(filterbank >= 0.0)

    # Generate 1-second audio
    t = np.linspace(0, 1.0, sr, endpoint=False)
    wav = (np.sin(2 * np.pi * 440.0 * t)).astype(np.float32)

    mel = compute_mel_spectrogram(wav, sr=sr)
    assert mel.shape[0] == 80  # 80 mel bins
    assert mel.shape[1] > 0
    # Values should be normalized to [-4.0, 4.0]
    assert np.min(mel) >= -4.01
    assert np.max(mel) <= 4.01


def test_face_detection_center_portrait_fallback():
    """Verify face detection falls back gracefully to a centered bounding box."""
    provider = Wav2LipONNXAvatarProvider(face_detector_path="non_existent_detector.onnx")
    frame = np.zeros((480, 640, 3), dtype=np.uint8)

    y1, y2, x1, x2 = provider._detect_face(frame)
    assert 0 <= y1 < y2 <= 480
    assert 0 <= x1 < x2 <= 640
    # Box should span significant portion of the frame
    assert (y2 - y1) > 100
    assert (x2 - x1) > 100


def test_wav2lip_invalid_input_validation():
    """Verify ValidationException raised for empty/corrupt avatar image or audio inputs."""
    provider = Wav2LipONNXAvatarProvider()

    valid_image = _create_synthetic_portrait_image_bytes()
    valid_audio = _create_synthetic_wav_bytes(0.5)

    # Empty image
    with pytest.raises(ValidationException) as exc1:
        import asyncio
        asyncio.run(provider.synthesize_avatar_video(b"", valid_audio))
    assert exc1.value.code == "INVALID_AVATAR_IMAGE"

    # Empty audio
    with pytest.raises(ValidationException) as exc2:
        import asyncio
        asyncio.run(provider.synthesize_avatar_video(valid_image, b""))
    assert exc2.value.code == "INVALID_AUDIO_DATA"

    # Corrupted audio bytes
    with pytest.raises(ValidationException) as exc3:
        import asyncio
        asyncio.run(provider.synthesize_avatar_video(valid_image, b"NOT_A_WAV_FILE_DATA_CORRUPTED_HERE_1234567890"))
    assert exc3.value.code == "AUDIO_DECODE_ERROR"


@pytest.mark.asyncio
async def test_wav2lip_real_cpu_inference_e2e():
    """Verify real Wav2Lip-ONNX CPU inference produces valid MP4 video matching audio duration."""
    provider = Wav2LipONNXAvatarProvider()

    image_bytes = _create_synthetic_portrait_image_bytes(320, 320)
    audio_bytes = _create_synthetic_wav_bytes(duration_seconds=1.2, sample_rate=16000)

    progress_stages = []

    async def on_progress(pct: int, stage: str):
        progress_stages.append((pct, stage))

    mp4_bytes, duration, total_frames = await provider.synthesize_avatar_video(
        avatar_image_bytes=image_bytes,
        audio_bytes=audio_bytes,
        fps=25,
        progress_callback=on_progress,
    )

    # Assert valid output video
    assert len(mp4_bytes) > 2000
    assert mp4_bytes[:8].endswith(b"ftyp") or b"moov" in mp4_bytes[:2048]
    assert duration >= 1.0
    assert total_frames == int(duration * 25) or abs(total_frames - int(1.2 * 25)) <= 2

    # Verify progress callback was invoked across stages
    assert len(progress_stages) >= 3
    assert any(s[1] == "extracting_audio_features" for s in progress_stages)
    assert any(s[1] == "running_neural_inference" for s in progress_stages)
    assert progress_stages[-1] == (100, "completed")

    # Resource cleanup test
    provider.unload_model()
    assert provider._session is None
    assert provider._face_detector is None
