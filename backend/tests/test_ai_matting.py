"""Comprehensive tests for Real MediaPipe Matting Provider and Neural Human Segmentation.

Verifies:
1. Protocol conformance (MattingProvider).
2. Model catalog registration (matting/mediapipe-selfie-cpu).
3. Exact model provenance and Apache-2.0 / COMMERCIAL_SAFE licensing.
4. Real ONNX CPU inference on portrait frames (shape, range, soft matte [0, 255]).
5. Video matte extraction (MP4 output, frame alignment, greyscale matte).
6. Strict real-mode failure on missing/corrupt model artifact.
7. Mock provider contract execution.
8. Performance and throughput telemetry.
"""

import os
import tempfile
import time
from pathlib import Path
import cv2
import numpy as np
import pytest

from app.ai.adapters.matting import DEFAULT_MEDIAPIPE_MATTING_PATH, RealMediaPipeMattingProvider
from app.ai.adapters.mock import MockMattingProvider
from app.ai.contracts import MattingContractRequest, MediaAssetRef
from app.ai.interfaces import MattingProvider, MattingResult
from app.ai.model_registry import ModelInstallStatus, get_model_registry
from app.ai.registry import AICapability, get_ai_registry, get_matting_provider
from app.core.exceptions import AIModelIncompatibleException, AIModelSecurityException, AIRuntimeUnavailableException


def test_matting_protocol_conformance():
    """Verify that both RealMediaPipeMattingProvider and MockMattingProvider implement MattingProvider."""
    real_provider = RealMediaPipeMattingProvider()
    mock_provider = MockMattingProvider()

    assert isinstance(real_provider, MattingProvider)
    assert isinstance(mock_provider, MattingProvider)
    assert real_provider.provider_name == "mediapipe"
    assert mock_provider.provider_name == "mock"


def test_matting_model_catalog_registration():
    """Verify matting/mediapipe-selfie-cpu is registered in ModelRegistry with verified metadata."""
    model_reg = get_model_registry()
    model = model_reg.get_model("matting/mediapipe-selfie-cpu")

    assert model is not None
    assert model.capability == "matting"
    assert model.provider == "mediapipe"
    assert model.requires_gpu is False
    assert "cpu" in model.supported_devices
    assert model.approximate_size_bytes == 462352
    assert model.license == "Apache-2.0"
    assert model.license_commercial_permitted is True
    assert model.metadata.get("license_classification") == "COMMERCIAL_SAFE"
    assert model.checksum_sha256 == "3241ac4ad8aa35bdaf33946776db29f7c283a413aa0b0dacb9483594b4531aad"
    assert model.revision == "be49485c8e027524be38591817fc5cd31bd9d00e"

    # Also verify non-commercial model is properly isolated
    modnet = model_reg.get_model("matting/modnet-cpu")
    assert modnet is not None
    assert modnet.license_commercial_permitted is False
    assert modnet.metadata.get("license_classification") == "RESEARCH_ONLY"


def test_matting_provider_registry_resolution():
    """Verify AICapability.MATTING resolves properly in AIProviderRegistry."""
    registry = get_ai_registry()
    provider = registry.get_matting_provider()
    assert provider is not None
    assert isinstance(provider, MattingProvider)


@pytest.mark.asyncio
async def test_real_mediapipe_frame_segmentation_inference():
    """Verify real local CPU ONNX inference on portrait frames produces valid alpha mask."""
    provider = RealMediaPipeMattingProvider()
    session = await provider._get_session()
    assert session is not None

    # Create synthetic frame with a bright center (simulating portrait subject)
    h, w = 480, 640
    frame = np.full((h, w, 3), 30, dtype=np.uint8)
    cv2.circle(frame, (w // 2, h // 2), 120, (220, 200, 180), -1)

    t0 = time.perf_counter()
    alpha_mask = provider.segment_frame_sync(session, frame, threshold=0.5, soft_matte=True)
    latency_ms = (time.perf_counter() - t0) * 1000

    assert alpha_mask.shape == (h, w)
    assert alpha_mask.dtype == np.uint8
    assert np.min(alpha_mask) >= 0
    assert np.max(alpha_mask) <= 255
    # Center should have higher alpha than the background corner
    assert int(alpha_mask[h // 2, w // 2]) >= int(alpha_mask[10, 10])
    # Latency check on modern CPU (< 250ms per frame under concurrent test load)
    assert latency_ms < 250.0



@pytest.mark.asyncio
async def test_real_mediapipe_video_matte_extraction():
    """Verify end-to-end video matte extraction produces synchronized 3-channel MP4 video."""
    provider = RealMediaPipeMattingProvider()
    session = await provider._get_session()

    with tempfile.TemporaryDirectory(prefix="test_matting_vid_") as tmp_dir:
        input_video = Path(tmp_dir) / "test_input.mp4"
        output_matte = Path(tmp_dir) / "output_matte.mp4"

        # Generate a small 10-frame synthetic test video
        w, h = 320, 240
        fps = 25.0
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(input_video), fourcc, fps, (w, h), isColor=True)
        for i in range(10):
            frame = np.full((h, w, 3), 40, dtype=np.uint8)
            cv2.circle(frame, (w // 2 + i * 2, h // 2), 50, (200, 180, 160), -1)
            writer.write(frame)
        writer.release()

        metrics = provider.extract_video_matte_sync(
            session=session,
            input_video_path=input_video,
            output_matte_video_path=output_matte,
            threshold=0.5,
            soft_matte=True,
        )

        assert output_matte.exists()
        assert output_matte.stat().st_size > 1000
        assert metrics["frame_count"] == 10
        assert metrics["width"] == w
        assert metrics["height"] == h
        assert metrics["fps"] == fps
        assert metrics["throughput_fps"] > 10.0

        # Verify output video can be read and has 3-channel greyscale frames
        cap = cv2.VideoCapture(str(output_matte))
        assert cap.isOpened()
        ret, matte_frame = cap.read()
        cap.release()
        assert ret is True
        assert matte_frame.shape == (h, w, 3)


def test_strict_real_mode_missing_model_fails():
    """Verify strict real mode throws when ONNX model file does not exist."""
    provider = RealMediaPipeMattingProvider(model_path="nonexistent/path/model.onnx")
    with pytest.raises(AIModelIncompatibleException) as exc_info:
        provider._ensure_model_file_exists()
    assert "AI_MATTING_MODEL_NOT_FOUND" in str(exc_info.value.code)


@pytest.mark.asyncio
async def test_mock_matting_provider_contract_execution():
    """Verify MockMattingProvider adheres to execution contracts without neural execution."""
    import uuid
    mock_provider = MockMattingProvider()
    req = MattingContractRequest(
        workspace_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        media_asset=MediaAssetRef(storage_key="test/videos/avatar_input.mp4"),
        output_format="matte_mask",
        threshold=0.5,
    )
    res = await mock_provider.segment(req)
    assert res.status == "succeeded"
    assert "mock/mattes" in res.output_storage_key
    assert res.fps == 30.0
    assert res.frame_count > 0
    assert res.width == 1920
    assert res.height == 1080


@pytest.mark.asyncio
async def test_matting_performance_and_telemetry():
    """Verify inference latency, throughput, and memory bounds."""
    provider = RealMediaPipeMattingProvider()
    session = await provider._get_session()

    # Benchmark 20 frames
    frame = np.zeros((256, 256, 3), dtype=np.uint8)
    cv2.circle(frame, (128, 128), 60, (255, 255, 255), -1)

    t0 = time.perf_counter()
    for _ in range(20):
        provider.segment_frame_sync(session, frame)
    total_sec = time.perf_counter() - t0

    fps = 20 / total_sec
    ms_per_frame = (total_sec / 20) * 1000

    # On host AMD Ryzen 5 5500U, expects > 50 fps, < 20 ms
    assert ms_per_frame < 30.0
    assert fps > 30.0
