"""Unit tests for MuseTalk Production-Target CUDA Avatar Provider adapter.

Validates:
1. Provider registration & descriptor metadata.
2. Commercial license metadata & explicit banning of non-commercial components.
3. OpenCV YuNet face detection & commercial landmark-based face masking.
4. Whisper log-mel audio feature extraction.
5. SHA-256 integrity verification and security checks.
6. Refusal to execute on CPU-only host with strict GPU_UNAVAILABLE error.
7. Strict no-fallback to mock behavior in real mode.
8. Hardware compatibility filtering in ModelRegistry.
9. Celery gpu_ai routing for MuseTalk jobs.
10. Contract compliance with LipSyncContractRequest/Result.
"""

import hashlib
import tempfile
from pathlib import Path
import cv2
import numpy as np
import pytest

from app.ai.adapters.musetalk import (
    BANNED_NON_COMMERCIAL_ARTIFACTS,
    DEFAULT_MUSETALK_MODEL_ID,
    DEFAULT_YUNET_PATH,
    YUNET_EXPECTED_SHA256,
    MuseTalkAvatarProvider,
)
from app.ai.contracts import LipSyncContractRequest, MediaAssetRef
from app.ai.hardware import detect_hardware
from app.ai.model_registry import get_model_registry
from app.ai.registry import get_ai_registry, get_avatar_provider
from app.core.exceptions import AIModelSecurityException, AIRuntimeUnavailableException
from app.services.job_service import resolve_job_queue


def test_musetalk_descriptor_and_metadata():
    """Verify MuseTalk descriptor records production-target CUDA status and licensing."""
    provider = MuseTalkAvatarProvider()
    desc = provider.descriptor

    assert desc.name == "musetalk"
    assert desc.capability == "avatar"
    assert desc.is_local is True
    assert desc.requires_gpu is True
    assert desc.supported_devices == ["cuda"]
    assert desc.supported_output_formats == ["mp4", "webm"]
    assert desc.is_available is False

    meta = desc.metadata
    assert meta["status"] == "production_target_cuda_unvalidated"
    assert meta["runtime"] == "pytorch-cuda"
    assert meta["commercial_permitted"] is True
    assert meta["research_only"] is False
    assert meta["license"] == "MIT"
    assert meta["license_classification"] == "CONDITIONAL — ARTIFACT VERIFICATION REQUIRED"
    assert "face_detector" in meta["auxiliary_models"]
    assert "opencv/yunet" in meta["auxiliary_models"]["face_detector"]


def test_musetalk_banned_non_commercial_components():
    """Verify that all non-commercial components are explicitly banned and actively rejected."""
    provider = MuseTalkAvatarProvider()
    banned = provider.descriptor.metadata["banned_components"]

    assert "s3fd-619a3168.pth" in banned
    assert "79999_iter.pth" in banned
    assert "CelebAMask-HQ" in banned
    assert "InsightFace" in banned
    assert "BFM_2009" in banned
    assert "CodeFormer" in banned

    # Verify that attempting to load or reference any banned artifact raises AIModelSecurityException
    for item in banned:
        with pytest.raises(AIModelSecurityException) as exc:
            MuseTalkAvatarProvider(face_detector_path=f"/path/to/{item}")
        assert exc.value.code == "AI_BANNED_NON_COMMERCIAL_ARTIFACT"

        with pytest.raises(AIModelSecurityException) as exc2:
            MuseTalkAvatarProvider(model_path=f"/models/{item}")
        assert exc2.value.code == "AI_BANNED_NON_COMMERCIAL_ARTIFACT"

        with pytest.raises(AIModelSecurityException) as exc3:
            MuseTalkAvatarProvider._verify_artifact_integrity(Path(f"/tmp/{item}"), "fake_hash")
        assert exc3.value.code == "AI_BANNED_NON_COMMERCIAL_ARTIFACT"


@pytest.mark.asyncio
async def test_musetalk_cpu_refusal_raises_gpu_unavailable():
    """Verify that calling MuseTalk inference methods on CPU-only host raises AIRuntimeUnavailableException."""
    provider = MuseTalkAvatarProvider()
    hw = detect_hardware()

    if not hw.has_cuda:
        # 1. Direct synthesize_avatar_video
        with pytest.raises(AIRuntimeUnavailableException) as exc1:
            await provider.synthesize_avatar_video(b"fake_image", b"fake_audio")
        assert exc1.value.code == "GPU_UNAVAILABLE"
        assert "Production-target CUDA provider — architecturally prepared, not locally validated" in str(exc1.value)

        # 2. Direct generate_lip_sync
        with pytest.raises(AIRuntimeUnavailableException) as exc2:
            await provider.generate_lip_sync("avatar_key", "audio_key")
        assert exc2.value.code == "GPU_UNAVAILABLE"

        # 3. Direct lip_sync contract
        import uuid
        req = LipSyncContractRequest(
            workspace_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            avatar_look_asset=MediaAssetRef(storage_key="test_avatar"),
            audio_asset=MediaAssetRef(storage_key="test_audio"),
        )
        with pytest.raises(AIRuntimeUnavailableException) as exc3:
            await provider.lip_sync(req)
        assert exc3.value.code == "GPU_UNAVAILABLE"


def test_musetalk_registry_resolution_on_cpu():
    """Verify registry get_avatar_provider('musetalk') strictly raises GPU_UNAVAILABLE on CPU host."""
    hw = detect_hardware()
    if not hw.has_cuda:
        registry = get_ai_registry()
        with pytest.raises(AIRuntimeUnavailableException) as exc:
            registry.get_avatar_provider("musetalk")
        assert exc.value.code == "GPU_UNAVAILABLE"

        # Also verify device='cuda' refusal
        with pytest.raises(AIRuntimeUnavailableException) as exc2:
            registry.get_avatar_provider("wav2lip", device="cuda")
        assert exc2.value.code == "GPU_UNAVAILABLE"


def test_musetalk_model_registry_catalog_entry():
    """Verify model catalog entry for avatar/musetalk-gpu has correct metadata and requirements."""
    registry = get_model_registry()
    model = registry.get_model(DEFAULT_MUSETALK_MODEL_ID)

    assert model is not None
    assert model.model_id == "avatar/musetalk-gpu"
    assert model.provider == "musetalk"
    assert model.capability == "avatar"
    assert model.requires_gpu is True
    assert model.supported_devices == ["cuda"]
    assert model.license == "MIT"
    assert model.license_commercial_permitted is True
    assert model.metadata["status"] == "production_target_cuda_unvalidated"
    assert model.metadata["license_classification"] == "CONDITIONAL — ARTIFACT VERIFICATION REQUIRED"
    assert "opencv/yunet" in model.metadata["face_detector"]

    hw = detect_hardware()
    is_compat, state, reason = model.is_compatible_with(hw)
    if not hw.has_cuda:
        assert is_compat is False
        assert "CUDA GPU" in reason or "requires_gpu" in reason or "not operational" in reason


def test_musetalk_face_detection_and_commercial_masking():
    """Verify OpenCV YuNet face detection and commercial lower-face masking."""
    provider = MuseTalkAvatarProvider()

    # Create synthetic test portrait image (320x320 with simulated face)
    img = np.zeros((320, 320, 3), dtype=np.uint8)
    cv2.circle(img, (160, 160), 60, (200, 200, 200), -1)

    y1, y2, x1, x2, landmarks = provider.detect_face(img)
    assert y2 > y1
    assert x2 > x1

    # Generate commercial lower-face inpainting & blending mask
    mask = provider.generate_commercial_lower_face_mask(img, (y1, y2, x1, x2), landmarks)
    assert mask.shape == (320, 320)
    assert mask.dtype == np.uint8
    assert mask.max() > 0
    # Upper face should be zero (unmasked)
    assert mask[0:int(y1 * 0.5), :].max() == 0


def test_musetalk_whisper_audio_feature_extraction():
    """Verify extraction of 80-channel log-mel features for MuseTalk."""
    provider = MuseTalkAvatarProvider()

    # Generate 1.0s synthetic sine wave audio
    import wave
    import io
    sr = 16000
    samples = (np.sin(2 * np.pi * 440 * np.arange(sr) / sr) * 32767).astype(np.int16)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(samples.tobytes())

    features = provider.extract_whisper_features(buf.getvalue())
    assert features.shape[0] == 80  # 80 mel channels
    assert features.shape[1] > 50   # Over 50 time steps
    assert features.dtype == np.float32


def test_musetalk_artifact_checksum_verification():
    """Verify artifact integrity validation logic."""
    with tempfile.NamedTemporaryFile(suffix=".onnx", delete=False) as f:
        f.write(b"valid_model_data_bytes")
        f_path = Path(f.name)

    try:
        correct_hash = hashlib.sha256(b"valid_model_data_bytes").hexdigest()
        # Should pass
        MuseTalkAvatarProvider._verify_artifact_integrity(f_path, correct_hash)

        # Mismatch should raise AIModelSecurityException
        with pytest.raises(AIModelSecurityException):
            MuseTalkAvatarProvider._verify_artifact_integrity(f_path, "wrong_hash_123456789")
    finally:
        if f_path.exists():
            f_path.unlink()


def test_musetalk_celery_gpu_ai_routing():
    """Verify Celery task queue resolution for MuseTalk jobs."""
    # 1. MuseTalk provider routes to gpu_ai
    q1 = resolve_job_queue("generate_avatar_video", {"provider": "musetalk"})
    assert q1 == "gpu_ai"

    q2 = resolve_job_queue("lip_sync", {"provider": "musetalk"})
    assert q2 == "gpu_ai"

    # 2. CUDA device routes to gpu_ai
    q3 = resolve_job_queue("generate_avatar_video", {"preferred_device": "cuda"})
    assert q3 == "gpu_ai"

    # 3. Wav2Lip routes to cpu_media
    q4 = resolve_job_queue("generate_avatar_video", {"provider": "wav2lip"})
    assert q4 == "cpu_media"


def test_musetalk_physical_yunet_artifact():
    """Verify that OpenCV YuNet artifact exists on disk with verified SHA-256."""
    yunet_path = Path("models_cache") / "avatar" / "face_detector" / "face_detection_yunet_2023mar.onnx"
    assert yunet_path.is_file(), f"Expected YuNet artifact at {yunet_path}"
    assert yunet_path.stat().st_size == 232589

    hasher = hashlib.sha256()
    with open(yunet_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    actual_hash = hasher.hexdigest().lower()
    assert actual_hash == YUNET_EXPECTED_SHA256


def test_musetalk_missing_weights_on_cuda_guard(monkeypatch):
    """Verify that if CUDA were available, missing weights directory raises AI_MODEL_NOT_FOUND."""
    from unittest.mock import MagicMock
    mock_hw = MagicMock()
    mock_hw.has_cuda = True
    monkeypatch.setattr("app.ai.adapters.musetalk.detect_hardware", lambda: mock_hw)

    provider = MuseTalkAvatarProvider(model_path="models_cache/nonexistent_musetalk_weights")
    with pytest.raises(AIRuntimeUnavailableException) as exc:
        provider._synthesize_avatar_video_cuda(
            avatar_image_bytes=b"fake_img",
            audio_bytes=b"fake_audio",
            fps=25,
            progress_callback=None,
            cancellation_checker=None,
        )
    assert exc.value.code == "AI_MODEL_NOT_FOUND"

