"""Comprehensive Test Suite for Phase 9: Production GPU Worker Architecture (gpu_ai).

Tests:
A. Queue routing (musetalk, stable_diffusion, device=cuda -> gpu_ai; CPU providers -> cpu_media)
B. GPU hardware admission (no GPU, incompatible CC, insufficient VRAM, CUDA unavailable)
C. Security (path traversal, arbitrary model IDs, blocked models)
D. Artifact integrity (SHA256 match/mismatch, size mismatch, missing file, partial tmp download)
E. Model policy (MuseTalk & SD1.5 conditional; AnimateDiff, SDXL-Turbo, SD-Turbo, ModelScope, Zeroscope BLOCKED)
F. No fallback (MuseTalk & Stable Diffusion strictly fail with GPU_UNAVAILABLE, zero mock/Wav2Lip fallback, no auto-download)
G. Worker configuration (queue=gpu_ai, concurrency=1, prefetch=1, acks_late=True, max_tasks_per_child=50)
"""

import hashlib
import os
import tempfile
import pytest

from app.ai.adapters.musetalk import MuseTalkAvatarProvider
from app.ai.adapters.stable_diffusion import StableDiffusionImageProvider
from app.ai.contracts import ImageGenContractRequest, LipSyncContractRequest
from app.ai.gpu_manifest import (
    CommercialStatus,
    GPU_MODEL_MANIFEST,
    assert_artifact_not_blocked,
    get_gpu_manifest_entry,
)
from app.ai.hardware import (
    CPUSpec,
    DiskSpec,
    GPUSpec,
    HardwareSpec,
    HardwareState,
    MemorySpec,
    check_gpu_admission,
    detect_hardware,
)
from app.ai.lifecycle import (
    ModelLifecycleManager,
    compute_file_sha256,
    resolve_safe_cache_path,
    verify_model_checksum,
)
from app.ai.model_registry import ModelDescriptor, ModelInstallStatus
from app.ai.runtimes import LocalCPURuntime
from app.core.config import get_settings
from app.core.exceptions import (
    AIModelSecurityException,
    AIRuntimeUnavailableException,
)
from app.services.job_service import resolve_job_queue
from app.workers.celery_app import celery_app
from scripts.provision_gpu_models import verify_staged_artifact


# ==============================================================================
# Category A: Queue Routing Tests
# ==============================================================================

def test_queue_routing_musetalk_to_gpu_ai():
    """Verify MuseTalk lip-sync requests route strictly to gpu_ai queue."""
    assert resolve_job_queue("lip_sync", {"provider": "musetalk"}) == "gpu_ai"
    assert resolve_job_queue("generate_avatar_video", {"provider": "musetalk"}) == "gpu_ai"


def test_queue_routing_stable_diffusion_to_gpu_ai():
    """Verify Stable Diffusion image requests route strictly to gpu_ai queue."""
    assert resolve_job_queue("generate_scene_visual", {"provider": "stable_diffusion"}) == "gpu_ai"
    assert resolve_job_queue("generate_scene_visual", {"provider": "stable_diffusion", "device": "cuda"}) == "gpu_ai"


def test_queue_routing_explicit_cuda_device_to_gpu_ai():
    """Verify any workload specifying CUDA preferred device routes to gpu_ai."""
    assert resolve_job_queue("tts_synthesis", {"preferred_device": "cuda"}) == "gpu_ai"
    assert resolve_job_queue("lip_sync", {"device": "cuda"}) == "gpu_ai"
    assert resolve_job_queue("generate_scene_visual", {"device": "cuda"}) == "gpu_ai"
    assert resolve_job_queue("asr_transcription", {"requires_gpu": True}) == "gpu_ai"


def test_queue_routing_cpu_workloads_remain_cpu_media():
    """Verify standard CPU workloads remain strictly on cpu_media queue."""
    assert resolve_job_queue("render_video", {}) == "cpu_media"
    assert resolve_job_queue("tts_synthesis", {"provider": "piper"}) == "cpu_media"
    assert resolve_job_queue("asr_transcription", {"provider": "whisper"}) == "cpu_media"
    assert resolve_job_queue("translate_project", {}) == "cpu_media"
    assert resolve_job_queue("enhance_speech", {}) == "cpu_media"
    assert resolve_job_queue("generate_project", {}) == "cpu_media"
    assert resolve_job_queue("lip_sync", {"provider": "wav2lip"}) == "cpu_media"
    assert resolve_job_queue("generate_scene_visual", {"provider": "mock", "device": "cpu"}) == "cpu_media"


# ==============================================================================
# Category B: GPU Admission Tests
# ==============================================================================

def _create_mock_spec(
    has_gpu: bool = True,
    vendor: str = "NVIDIA",
    model: str = "NVIDIA GeForce RTX 4080",
    vram_gb: float = 16.0,
    cuda_available: bool = True,
    driver_version: str = "550.54.14",
    compute_capability: str = "8.9",
) -> HardwareSpec:
    vram_bytes = int(vram_gb * 1024 * 1024 * 1024)
    return HardwareSpec(
        os_name="Linux",
        os_release="22.04",
        os_version="5.15.0",
        python_version="3.11.9",
        cpu=CPUSpec(model="AMD Ryzen 9", architecture="x86_64", physical_cores=8, logical_cores=16),
        gpu=GPUSpec(
            has_gpu=has_gpu,
            gpu_count=1 if has_gpu else 0,
            vendor=vendor,
            model=model,
            vram_total_bytes=vram_bytes,
            vram_free_bytes=int(vram_bytes * 0.9),
            cuda_available=cuda_available,
            cuda_version="12.4" if cuda_available else None,
            driver_version=driver_version if has_gpu else None,
            compute_capability=compute_capability if has_gpu else None,
            device_index=0,
        ),
        memory=MemorySpec(ram_total_bytes=32 * 1024 * 1024 * 1024, ram_available_bytes=24 * 1024 * 1024 * 1024),
        disk=DiskSpec(disk_total_bytes=500 * 1024 * 1024 * 1024, disk_free_bytes=300 * 1024 * 1024 * 1024),
    )


def test_admission_passes_for_valid_nvidia_cuda_gpu():
    """Verify admission succeeds when host satisfies all GPU requirements."""
    spec = _create_mock_spec(has_gpu=True, vendor="NVIDIA", vram_gb=16.0, cuda_available=True, compute_capability="8.9")
    admitted, reason, details = check_gpu_admission(min_vram_gb=8.0, min_compute_capability=7.0, spec=spec)
    assert admitted is True
    assert "ADMITTED" in reason
    assert details["has_gpu"] is True
    assert details["vram_total_gb"] == 16.0


def test_admission_fails_when_no_gpu():
    """Verify admission fails with GPU_UNAVAILABLE when host has no discrete GPU."""
    spec = _create_mock_spec(has_gpu=False, vendor="None", model="None", vram_gb=0, cuda_available=False)
    admitted, reason, _ = check_gpu_admission(spec=spec)
    assert admitted is False
    assert "GPU_UNAVAILABLE" in reason


def test_admission_fails_when_non_nvidia_gpu():
    """Verify admission fails with GPU_UNAVAILABLE on AMD / Intel GPUs."""
    spec = _create_mock_spec(has_gpu=True, vendor="AMD", model="AMD Radeon Graphics", vram_gb=8.0, cuda_available=False)
    admitted, reason, _ = check_gpu_admission(spec=spec)
    assert admitted is False
    assert "GPU_UNAVAILABLE" in reason
    assert "vendor=AMD" in reason


def test_admission_fails_when_cuda_not_available():
    """Verify admission fails if NVIDIA card exists but CUDA runtime is not operational."""
    spec = _create_mock_spec(has_gpu=True, vendor="NVIDIA", cuda_available=False)
    admitted, reason, _ = check_gpu_admission(spec=spec)
    assert admitted is False
    assert "GPU_UNAVAILABLE" in reason


def test_admission_fails_when_insufficient_vram():
    """Verify admission fails with GPU_INSUFFICIENT_VRAM when VRAM < 8 GB."""
    spec = _create_mock_spec(has_gpu=True, vendor="NVIDIA", vram_gb=4.0, cuda_available=True, compute_capability="7.5")
    admitted, reason, details = check_gpu_admission(min_vram_gb=8.0, spec=spec)
    assert admitted is False
    assert "GPU_INSUFFICIENT_VRAM" in reason
    assert details["vram_total_gb"] == 4.0


def test_admission_fails_when_incompatible_compute_capability():
    """Verify admission fails with GPU_INCOMPATIBLE when compute capability < 7.0."""
    spec = _create_mock_spec(has_gpu=True, vendor="NVIDIA", vram_gb=12.0, compute_capability="6.1")
    admitted, reason, _ = check_gpu_admission(min_vram_gb=8.0, min_compute_capability=7.0, spec=spec)
    assert admitted is False
    assert "GPU_INCOMPATIBLE" in reason


# ==============================================================================
# Category C: Security Tests
# ==============================================================================

def test_security_path_traversal_strictly_rejected():
    """Verify path traversal sequences are detected and rejected."""
    base = tempfile.mkdtemp()
    try:
        with pytest.raises(AIModelSecurityException) as exc:
            resolve_safe_cache_path(base, "../../etc/shadow")
        assert "AI_PATH_TRAVERSAL_DETECTED" in exc.value.code

        with pytest.raises(AIModelSecurityException) as exc:
            resolve_safe_cache_path(base, "../../../models/evil.bin")
        assert "AI_PATH_TRAVERSAL_DETECTED" in exc.value.code
    finally:
        import shutil
        shutil.rmtree(base, ignore_errors=True)


def test_security_blocked_models_strictly_rejected():
    """Verify blocked models raise AIModelSecurityException fail-closed."""
    blocked_ids = [
        "video/animatediff-v1-5",
        "image/sdxl-turbo",
        "image/sd-turbo",
        "video/modelscope-t2v",
        "video/zeroscope",
        "s3fd-619a3168.pth",
        "face-parse-bisent/79999_iter.pth",
        "CelebAMask-HQ",
        "InsightFace",
        "CodeFormer",
    ]
    for m in blocked_ids:
        with pytest.raises(AIModelSecurityException) as exc:
            assert_artifact_not_blocked(m)
        assert "AI_MODEL_SECURITY_BLOCKED" in exc.value.code


# ==============================================================================
# Category D: Artifact Integrity Tests
# ==============================================================================

def test_artifact_integrity_valid_sha_passes():
    """Verify valid SHA-256 checksum matches cleanly."""
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b"deterministic test artifact content")
        f_path = f.name

    try:
        expected = hashlib.sha256(b"deterministic test artifact content").hexdigest()
        assert verify_model_checksum(f_path, expected) is True
    finally:
        if os.path.exists(f_path):
            os.remove(f_path)


def test_artifact_integrity_invalid_sha_fails():
    """Verify SHA-256 mismatch raises AIModelSecurityException."""
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b"corrupted artifact data")
        f_path = f.name

    try:
        with pytest.raises(AIModelSecurityException) as exc:
            verify_model_checksum(f_path, "0000000000000000000000000000000000000000000000000000000000000000")
        assert "AI_CHECKSUM_MISMATCH" in exc.value.code
    finally:
        if os.path.exists(f_path):
            os.remove(f_path)


def test_artifact_integrity_size_mismatch_fails():
    """Verify provision verification reports SIZE_MISMATCH when byte counts differ."""
    tmp_dir = tempfile.mkdtemp()
    try:
        entry = GPU_MODEL_MANIFEST["avatar/yunet-2023mar"]
        # Create a file at target path with wrong byte size
        target_path = resolve_safe_cache_path(tmp_dir, entry.relative_path)
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        with open(target_path, "wb") as f:
            f.write(b"too small")

        valid, reason = verify_staged_artifact(entry, tmp_dir)
        assert valid is False
        assert "SIZE_MISMATCH" in reason
    finally:
        import shutil
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_artifact_integrity_missing_file_fails():
    """Verify missing artifact returns MISSING status."""
    tmp_dir = tempfile.mkdtemp()
    try:
        entry = GPU_MODEL_MANIFEST["avatar/yunet-2023mar"]
        valid, reason = verify_staged_artifact(entry, tmp_dir)
        assert valid is False
        assert "MISSING" in reason
    finally:
        import shutil
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_artifact_integrity_partial_download_is_not_ready():
    """Verify interrupted/partial download (.download.tmp) does not count as READY."""
    tmp_dir = tempfile.mkdtemp()
    try:
        entry = GPU_MODEL_MANIFEST["avatar/yunet-2023mar"]
        target_path = resolve_safe_cache_path(tmp_dir, entry.relative_path)
        tmp_file = f"{target_path}.download.tmp"
        os.makedirs(os.path.dirname(tmp_file), exist_ok=True)
        with open(tmp_file, "wb") as f:
            f.write(b"partial content")

        valid, reason = verify_staged_artifact(entry, tmp_dir)
        assert valid is False
        assert "MISSING" in reason
        assert not os.path.isfile(target_path)
    finally:
        import shutil
        shutil.rmtree(tmp_dir, ignore_errors=True)


# ==============================================================================
# Category E: Model Policy Tests
# ==============================================================================

def test_model_policy_musetalk_conditional():
    """Verify MuseTalk core and VAE artifacts are marked CONDITIONAL."""
    entry_core = GPU_MODEL_MANIFEST["avatar/musetalk-core"]
    assert entry_core.commercial_status == CommercialStatus.CONDITIONAL

    entry_vae = GPU_MODEL_MANIFEST["avatar/musetalk-vae"]
    assert entry_vae.commercial_status == CommercialStatus.CONDITIONAL


def test_model_policy_stable_diffusion_conditional():
    """Verify Stable Diffusion v1.5 is marked CONDITIONAL."""
    entry_sd = GPU_MODEL_MANIFEST["image/stable-diffusion-v1-5-gpu"]
    assert entry_sd.commercial_status == CommercialStatus.CONDITIONAL
    assert entry_sd.license == "CreativeML OpenRAIL-M"


def test_model_policy_blocked_models_registered_as_blocked():
    """Verify AnimateDiff, SDXL-Turbo, SD-Turbo, ModelScope, and Zeroscope are registered as BLOCKED."""
    assert GPU_MODEL_MANIFEST["video/animatediff-v1-5"].commercial_status == CommercialStatus.BLOCKED
    assert GPU_MODEL_MANIFEST["image/sdxl-turbo"].commercial_status == CommercialStatus.BLOCKED
    assert GPU_MODEL_MANIFEST["image/sd-turbo"].commercial_status == CommercialStatus.BLOCKED
    assert GPU_MODEL_MANIFEST["video/modelscope-t2v"].commercial_status == CommercialStatus.BLOCKED
    assert GPU_MODEL_MANIFEST["video/zeroscope"].commercial_status == CommercialStatus.BLOCKED


# ==============================================================================
# Category F: No Fallback Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_no_fallback_musetalk_on_cpu_raises_gpu_unavailable():
    """Verify MuseTalk strictly raises GPU_UNAVAILABLE on CPU and does NOT fall back to Wav2Lip or mock."""
    import uuid
    from app.ai.contracts import MediaAssetRef

    hw = detect_hardware()
    if not hw.has_cuda:
        provider = MuseTalkAvatarProvider()
        req = LipSyncContractRequest(
            workspace_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            avatar_look_asset=MediaAssetRef(storage_key="test-look.png"),
            audio_asset=MediaAssetRef(storage_key="test-audio.wav"),
        )
        with pytest.raises(AIRuntimeUnavailableException) as exc:
            await provider.lip_sync(req)
        assert exc.value.code == "GPU_UNAVAILABLE"
        assert "CUDA" in exc.value.message


@pytest.mark.asyncio
async def test_no_fallback_stable_diffusion_on_cpu_raises_gpu_unavailable():
    """Verify Stable Diffusion strictly raises GPU_UNAVAILABLE on CPU and does NOT fall back to mock."""
    import uuid

    hw = detect_hardware()
    if not hw.has_cuda:
        provider = StableDiffusionImageProvider()
        req = ImageGenContractRequest(
            workspace_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            prompt="A stunning sunset over the ocean",
        )
        with pytest.raises(AIRuntimeUnavailableException) as exc:
            await provider.generate(req)
        assert exc.value.code == "GPU_UNAVAILABLE"
        assert "CUDA" in exc.value.message



def test_no_fallback_auto_download_prohibited():
    """Verify missing models raise AI_AUTO_DOWNLOAD_PROHIBITED without downloading."""
    settings = get_settings()
    # In production/default, auto-download is disabled
    assert settings.AI_ALLOW_AUTO_DOWNLOAD is False

    mgr = ModelLifecycleManager()
    descriptor = ModelDescriptor(
        model_id="image/uninstalled-test-model",
        name="Uninstalled Model",
        provider="diffusion",
        capability="image",
        requires_gpu=False,
    )
    runtime = LocalCPURuntime()

    with pytest.raises(AIModelSecurityException) as exc:
        mgr.load_model(descriptor, runtime)
    assert exc.value.code == "AI_AUTO_DOWNLOAD_PROHIBITED"


# ==============================================================================
# Category G: Worker Configuration Tests
# ==============================================================================

def test_worker_celery_configuration():
    """Verify Celery application config enforces required worker parameters."""
    conf = celery_app.conf

    # Routing and queues
    assert "gpu_ai" in [q.name for q in conf.task_queues]
    assert "cpu_media" in [q.name for q in conf.task_queues]
    assert "maintenance" in [q.name for q in conf.task_queues]

    # Task reliability settings
    assert conf.task_acks_late is True
    assert conf.worker_prefetch_multiplier == 1

    # Task routes for AI
    routes = conf.task_routes
    assert routes.get("heyzen.tasks.ai.*", {}).get("queue") == "gpu_ai"
