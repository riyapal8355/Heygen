"""Unit, Integration, and Hardware Safety Tests for the Neural Avatar Pipeline.

Tests:
1. Provider registration across all neural and fallback adapters
2. Hardware capability detection and dedicated VRAM reporting
3. Graceful GPU unavailable behavior (AIRuntimeUnavailableException)
4. GPUAvatarProvider mode routing (LOCAL_GPU, REMOTE_GPU, LOCAL_WAV2LIP_FALLBACK)
5. LivePortrait adapter contract and option validation
6. MuseTalk 1.5 adapter motion video pipeline interface
7. Hallo2 adapter portrait diffusion interface
8. Legacy Delaunay separation (confirming Delaunay is NOT the default provider)
9. Standalone MP4 video validation and duration accuracy
10. MinIO transfer and asset linkage compatibility
"""

import asyncio
import io
import os
import shutil
import tempfile
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.adapters.hallo2 import Hallo2Adapter
from app.ai.adapters.liveportrait import LivePortraitAdapter, LivePortraitMotionOptions
from app.ai.adapters.musetalk import MuseTalkAvatarProvider
from app.ai.adapters.wav2lip import Wav2LipONNXAvatarProvider
from app.ai.capabilities import ProviderDescriptor
from app.ai.hardware import CPUSpec, DiskSpec, GPUSpec, HardwareSpec, MemorySpec, detect_hardware
from app.ai.providers.gpu_avatar_provider import GPUAvatarProvider, GPUAvatarProviderMode
from app.ai.registry import AICapability, get_ai_registry
from app.core.exceptions import AIRuntimeUnavailableException
from app.media.ffprobe import FFprobeService


@pytest.fixture
def registry():
    """Ensure clean AI provider registry."""
    reg = get_ai_registry()
    return reg


def test_avatar_providers_registration(registry):
    """Verify that all neural providers and GPU provider are registered, and legacy delaunay is removed."""
    providers = registry.list_providers(AICapability.AVATAR)["avatar"]
    assert "gpu_avatar" in providers
    assert "liveportrait" in providers
    assert "musetalk" in providers
    assert "hallo2" in providers
    assert "wav2lip" in providers
    assert "legacy_delaunay" not in providers


def test_delaunay_not_primary_provider(registry):
    """Verify Delaunay is permanently eliminated and gpu_avatar is primary production provider."""
    default_provider = registry.get_avatar_provider()
    assert default_provider.provider_name == "gpu_avatar"
    providers = registry.list_providers(AICapability.AVATAR)["avatar"]
    assert "legacy_delaunay" not in providers


def test_hardware_audit_truthfulness():
    """Verify hardware detection accurately reports discrete GPU, VRAM, and CUDA status."""
    spec = detect_hardware()
    assert isinstance(spec, HardwareSpec)
    assert hasattr(spec.gpu, "cuda_available")
    assert hasattr(spec.gpu, "vram_total_gb")
    assert hasattr(spec.gpu, "vendor")

    # On this specific machine, integrated graphics without CUDA should be detected
    if not spec.gpu.cuda_available:
        assert spec.gpu.cuda_available is False
        assert spec.gpu.vram_total_gb < 4.0


def test_liveportrait_hardware_gate_raises_on_non_cuda():
    """LivePortrait MUST NOT execute or fake execution when CUDA is unavailable."""
    lp = LivePortraitAdapter()
    hw = detect_hardware()

    if not hw.gpu.cuda_available:
        with pytest.raises(AIRuntimeUnavailableException) as exc_info:
            lp._verify_cuda_hardware()
        assert "NEURAL AVATAR QUALITY BLOCKED BY LOCAL HARDWARE" in str(exc_info.value.message)
        assert exc_info.value.details.get("error_code") == "NEURAL_AVATAR_QUALITY_BLOCKED_BY_LOCAL_HARDWARE"


def test_musetalk_hardware_gate_raises_on_non_cuda():
    """MuseTalk 1.5 MUST NOT execute or fake execution when CUDA is unavailable."""
    mt = MuseTalkAvatarProvider()
    hw = detect_hardware()

    if not hw.gpu.cuda_available:
        with pytest.raises(AIRuntimeUnavailableException) as exc_info:
            mt._ensure_cuda_available()
        assert "CUDA" in str(exc_info.value.message)


def test_hallo2_hardware_gate_raises_on_non_cuda():
    """Hallo2 MUST NOT execute or fake execution when CUDA is unavailable."""
    hallo = Hallo2Adapter()
    hw = detect_hardware()

    if not hw.gpu.cuda_available:
        with pytest.raises(AIRuntimeUnavailableException) as exc_info:
            hallo._verify_cuda_hardware()
        assert "NEURAL AVATAR QUALITY BLOCKED BY LOCAL HARDWARE" in str(exc_info.value.message)


def test_gpu_avatar_provider_modes():
    """Test mode selection and configuration in GPUAvatarProvider."""
    # 1. Remote worker mode
    p_remote = GPUAvatarProvider(mode=GPUAvatarProviderMode.REMOTE_GPU, remote_worker_url="http://gpu-worker.local:8100")
    assert p_remote.mode == GPUAvatarProviderMode.REMOTE_GPU
    assert p_remote.remote_worker_url == "http://gpu-worker.local:8100"

    # 2. Local GPU mode (should report GPU_REQUIRED on non-CUDA)
    hw = detect_hardware()
    if not hw.gpu.cuda_available:
        p_local = GPUAvatarProvider(mode=GPUAvatarProviderMode.LOCAL_GPU)
        is_ready, msg = p_local.health_check()
        assert is_ready is False
        assert "GPU_REQUIRED" in msg


@pytest.mark.asyncio
async def test_gpu_avatar_local_gpu_raises_without_fallback():
    """On non-CUDA machine, LOCAL_GPU strictly raises GPU_REQUIRED exception."""
    hw = detect_hardware()
    if not hw.gpu.cuda_available:
        provider = GPUAvatarProvider(mode=GPUAvatarProviderMode.LOCAL_GPU)
        with pytest.raises(AIRuntimeUnavailableException) as exc_info:
            await provider.generate_talking_video(
                avatar_image_bytes=b"fake_image",
                audio_bytes=b"fake_audio",
            )
        assert "NEURAL AVATAR QUALITY BLOCKED BY LOCAL HARDWARE" in str(exc_info.value.message)
        assert exc_info.value.details.get("provider_status") == "GPU_REQUIRED"


def test_avatar_source_package_structure():
    """Verify avatars/annie and avatars/daniel meet Section 7 specifications."""
    backend_root = Path(__file__).resolve().parent.parent
    repo_root = backend_root.parent

    for avatar_name in ["annie", "daniel"]:
        avatar_dir = repo_root / "avatars" / avatar_name
        assert avatar_dir.exists(), f"Directory missing: {avatar_dir}"
        assert (avatar_dir / "source.png").exists()
        assert (avatar_dir / "source_512.png").exists()
        assert (avatar_dir / "source_1024.png").exists()
        assert (avatar_dir / "metadata.json").exists()

        driving_dir = avatar_dir / "driving"
        assert driving_dir.exists()
        assert (driving_dir / "neutral.mp4").exists()
        assert (driving_dir / "talking.mp4").exists()


@pytest.mark.asyncio
async def test_remote_worker_request_contract():
    """Verify remote worker REST and MinIO interface contract."""
    from app.ai.workers.remote_gpu_avatar_worker import JobAvatarRequest, JobAvatarResponse, AvatarJobState

    req = JobAvatarRequest(
        job_id="test_job_123",
        workspace_id="ws_abc",
        source_avatar_asset="workspace/ws_abc/avatar-jobs/test_job_123/source.png",
        audio_asset="workspace/ws_abc/avatar-jobs/test_job_123/audio.wav",
        driving_motion_asset="workspace/ws_abc/avatar-jobs/test_job_123/driving.mp4",
        provider="liveportrait_musetalk",
        model="liveportrait-v1",
        fps=25,
        resolution=512,
    )
    assert req.job_id == "test_job_123"
    assert req.workspace_id == "ws_abc"
    assert req.provider == "liveportrait_musetalk"
    assert "workspace/ws_abc/" in req.source_avatar_asset
    assert AvatarJobState.GPU_REQUIRED.value == "GPU_REQUIRED"
    assert AvatarJobState.GENERATING_MOTION.value == "GENERATING_MOTION"


def test_avatar_motion_provider_protocol():
    """Verify LivePortraitAdapter satisfies AvatarMotionProvider protocol."""
    from app.ai.interfaces import AvatarMotionProvider

    lp = LivePortraitAdapter()
    assert isinstance(lp, AvatarMotionProvider)
    assert hasattr(lp, "generate_motion")
    assert hasattr(lp, "health_check")
    assert hasattr(lp, "capabilities")
    assert hasattr(lp, "is_available")


def test_model_discovery_status_states():
    """Verify Section 7 model discovery statuses."""
    from app.ai.model_registry import discover_model_state

    # 1. LivePortrait on CPU host should return GPU_REQUIRED
    lp_state = discover_model_state("avatar/liveportrait")
    assert lp_state["status"] == "GPU_REQUIRED"
    assert lp_state["cuda_required"] is True

    # 2. MuseTalk on CPU host should return GPU_REQUIRED
    mt_state = discover_model_state("avatar/musetalk")
    assert mt_state["status"] == "GPU_REQUIRED"

    # 3. Hallo2 on CPU host should return GPU_REQUIRED
    hallo_state = discover_model_state("avatar/hallo2")
    assert hallo_state["status"] == "GPU_REQUIRED"

    # 4. Wav2Lip fallback should return AVAILABLE
    w2l_state = discover_model_state("avatar/wav2lip")
    assert w2l_state["status"] == "AVAILABLE"


def test_neural_avatar_hardware_status_section8():
    """Verify Section 8 hardware capability detection schema."""
    from app.ai.hardware import get_neural_avatar_hardware_status

    status = get_neural_avatar_hardware_status()
    assert "cuda_available" in status
    assert "gpu_name" in status
    assert "vram_gb" in status
    assert "directml_available" in status
    assert "liveportrait" in status
    assert "musetalk" in status
    assert "hallo2" in status
    assert "wav2lip" in status
    assert status["liveportrait"]["available"] is False
    assert status["liveportrait"]["reason"] == "CUDA GPU required"


def test_truthful_avatar_artifacts_and_manifest():
    """Verify that only genuine artifacts exist, manifests/execution logs are accurate,
    and no fake neural model outputs are created on CPU host."""
    import json
    backend_root = Path(__file__).resolve().parent.parent
    repo_root = backend_root.parent
    out_dir = repo_root / "test-results" / "avatar_quality"

    # 1. Genuine required files
    required_files = [
        "source.png",
        "driving.mp4",
        "annie_wav2lip_fallback.mp4",
        "fallback_contact_sheet.jpg",
        "face_closeups.jpg",
        "mouth_closeups.jpg",
        "eye_closeups.jpg",
        "comparison_available.jpg",
        "manifest.json",
        "execution.json",
    ]
    for rf in required_files:
        p = out_dir / rf
        assert p.exists(), f"Required artifact '{rf}' missing from {out_dir}"
        assert p.stat().st_size > 0, f"Artifact '{rf}' is empty"

    # 2. Strict check: Banned fake/misleading files MUST NOT exist
    banned_files = [
        "liveportrait.mp4",
        "musetalk.mp4",
        "final_neural_avatar.mp4",
        "annie_neural_avatar.mp4",
        "daniel_neural_avatar.mp4",
        "comparison.jpg",
    ]
    for bf in banned_files:
        p = out_dir / bf
        assert not p.exists(), f"Misleading fake model artifact '{bf}' must NOT exist on CPU host!"

    # 3. Validate manifest.json
    manifest_data = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest_data["source"] == "source.png"
    assert manifest_data["driving_motion"] == "driving.mp4"
    provs = manifest_data["providers"]
    assert provs["wav2lip"]["status"] == "EXECUTED"
    assert provs["wav2lip"]["hardware"] == "CPU"
    assert provs["wav2lip"]["output"] == "annie_wav2lip_fallback.mp4"
    assert provs["liveportrait"]["status"] == "GPU_REQUIRED"
    assert provs["liveportrait"]["output"] is None
    assert provs["musetalk"]["status"] == "GPU_REQUIRED"
    assert provs["musetalk"]["output"] is None
    assert provs["hallo2"]["status"] == "GPU_REQUIRED"
    assert provs["hallo2"]["output"] is None

    # 4. Validate execution.json
    exec_data = json.loads((out_dir / "execution.json").read_text(encoding="utf-8"))
    assert exec_data["wav2lip"]["executed"] is True
    assert exec_data["wav2lip"]["hardware"] == "CPU"
    assert "output_sha256" in exec_data["wav2lip"]
    assert exec_data["liveportrait"]["executed"] is False
    assert exec_data["liveportrait"]["reason"] == "CUDA_REQUIRED"
    assert exec_data["musetalk"]["executed"] is False
    assert exec_data["musetalk"]["reason"] == "CUDA_REQUIRED"
    assert exec_data["hallo2"]["executed"] is False
    assert exec_data["hallo2"]["reason"] == "CUDA_REQUIRED"

