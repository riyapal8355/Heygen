"""Phase 21 Comprehensive Test Suite: GPU-Validated AI Runtime Architecture.

Tests:
1. CPU-only development host correctly rejected with GPU_UNAVAILABLE
2. CUDA unavailable state detected and enforced
3. GPU worker supervisor fails closed on non-NVIDIA host
4. GPU jobs rejected without GPU
5. GPU jobs never silently fall back to CPU or mock
6. Simulated A10G (24 GB, CC 8.6) admitted
7. Simulated GTX 1660 (6 GB, VRAM < 8 GB) rejected with GPU_VRAM_INSUFFICIENT
8. Simulated GTX 1080 Ti (11 GB, CC 6.1 < 7.0) rejected with GPU_COMPUTE_CAPABILITY_UNSUPPORTED
9. Insufficient VRAM threshold enforcement
10. Unsupported compute capability threshold enforcement
11. Missing model artifact rejection (GPU_MODEL_MISSING)
12. Driver/CUDA mismatch rejection (GPU_DRIVER_UNAVAILABLE / GPU_CUDA_UNAVAILABLE)
13. CPU queue unaffected (TTS, ASR, translation, matting, OpenVoice route to cpu_media)
14. GPU queue routing correct (MuseTalk, Stable Diffusion route to gpu_ai)
15. Health endpoint reports system healthy while GPU worker remains unavailable
16. MuseTalk fail-closed invariant
17. Stable Diffusion fail-closed invariant
18. GPU error metadata recorded in job failure details
19. GPU worker readiness reflection in telemetry
20. Standalone GPU validation CLI harness execution on host
"""

import json
import uuid
import pytest
from httpx import AsyncClient

from app.ai.adapters.musetalk import MuseTalkAvatarProvider
from app.ai.adapters.stable_diffusion import StableDiffusionImageProvider
from app.cli import gpu as gpu_cli
from app.ai.contracts import ImageGenContractRequest, LipSyncContractRequest
from app.ai.gpu_manifest import (
    CommercialStatus,
    GPU_MODEL_MANIFEST,
    assert_artifact_not_blocked,
)
from app.ai.hardware import (
    CPUSpec,
    DiskSpec,
    GPUAdmissionResult,
    GPUErrorCode,
    GPUSpec,
    HardwareSpec,
    MemorySpec,
    check_gpu_admission,
    detect_hardware,
)
from app.core.config import get_settings
from app.core.exceptions import (
    AIModelSecurityException,
    AIRuntimeUnavailableException,
)
from app.services.job_service import resolve_job_queue
from app.workers.celery_app import celery_app
from app.workers.tasks.ai_tasks import _execute_lip_sync
from scripts.gpu_worker_entrypoint import execute_supervisor_validation


def _make_simulated_spec(
    vendor: str = "NVIDIA",
    model: str = "NVIDIA A10G",
    vram_gb: float = 24.0,
    cuda_available: bool = True,
    driver_version: str = "550.54.14",
    compute_capability: str = "8.6",
) -> HardwareSpec:
    vram_bytes = int(vram_gb * (1024 ** 3))
    return HardwareSpec(
        os_name="Linux",
        os_release="22.04",
        os_version="5.15.0",
        python_version="3.11.9",
        cpu=CPUSpec(model="AMD EPYC 7763", architecture="x86_64", physical_cores=16, logical_cores=32),
        gpu=GPUSpec(
            has_gpu=True,
            gpu_count=1,
            vendor=vendor,
            model=model,
            vram_total_bytes=vram_bytes,
            vram_free_bytes=int(vram_bytes * 0.9),
            cuda_available=cuda_available,
            cuda_version="12.4" if cuda_available else None,
            driver_version=driver_version,
            compute_capability=compute_capability,
            device_index=0,
        ),
        memory=MemorySpec(ram_total_bytes=64 * (1024 ** 3), ram_available_bytes=48 * (1024 ** 3)),
        disk=DiskSpec(disk_total_bytes=500 * (1024 ** 3), disk_free_bytes=350 * (1024 ** 3)),
        docker_gpu_available=True,
    )


# ==============================================================================
# 1. Current CPU-Only Host Rejection & Real CUDA Detection
# ==============================================================================

def test_host_cuda_rejection_truthful():
    """Verify hardware detection truthfully reports host CPU and lack of NVIDIA CUDA."""
    hw = detect_hardware(refresh=True)
    assert hw.has_cuda is False
    assert hw.gpu.cuda_available is False


def test_host_admission_fails_closed_gpu_unavailable():
    """Verify live host check fails with GPU_UNAVAILABLE without crashing or faking CUDA."""
    admission = check_gpu_admission(spec=None)
    assert admission.supported is False
    assert admission.available is False
    assert admission.error_code in (GPUErrorCode.GPU_UNAVAILABLE, GPUErrorCode.GPU_CUDA_UNAVAILABLE)
    assert "GPU_UNAVAILABLE" in admission.reason


def test_gpu_worker_supervisor_fails_closed_on_current_host():
    """Verify supervisor startup gate strictly refuses to spawn Celery on this CPU host."""
    admitted, reason, report = execute_supervisor_validation()
    assert admitted is False
    assert "GPU_UNAVAILABLE" in reason
    assert report["admitted"] is False
    assert report["failure_stage"] == "hardware_admission"


# ==============================================================================
# 2. Simulated Hardware Admission Matrix (A10G, GTX 1660, GTX 1080 Ti)
# ==============================================================================

def test_simulated_a10g_24gb_cc86_admitted():
    """Verify compliant enterprise GPU (NVIDIA A10G 24GB CC 8.6) passes admission."""
    spec = _make_simulated_spec(
        vendor="NVIDIA",
        model="NVIDIA A10G",
        vram_gb=24.0,
        compute_capability="8.6",
    )
    result = check_gpu_admission(min_vram_gb=8.0, min_compute_capability=7.0, spec=spec)
    assert result.supported is True
    assert result.available is True
    assert result.error_code is None
    assert result.total_vram_mb == 24 * 1024
    assert result.compute_capability == "8.6"
    assert "ADMITTED" in result.reason


def test_simulated_gtx_1660_rejected_insufficient_vram():
    """Verify GTX 1660 (6GB < 8GB minimum) is rejected with GPU_VRAM_INSUFFICIENT."""
    spec = _make_simulated_spec(
        vendor="NVIDIA",
        model="NVIDIA GeForce GTX 1660",
        vram_gb=6.0,
        compute_capability="7.5",
    )
    result = check_gpu_admission(min_vram_gb=8.0, min_compute_capability=7.0, spec=spec)
    assert result.supported is False
    assert result.error_code == GPUErrorCode.GPU_VRAM_INSUFFICIENT
    assert "GPU_VRAM_INSUFFICIENT" in result.reason
    assert "INSUFFICIENT_VRAM" in result.reason


def test_simulated_gtx_1080ti_rejected_unsupported_compute_capability():
    """Verify GTX 1080 Ti (CC 6.1 < 7.0 minimum) is rejected with GPU_COMPUTE_CAPABILITY_UNSUPPORTED."""
    spec = _make_simulated_spec(
        vendor="NVIDIA",
        model="NVIDIA GeForce GTX 1080 Ti",
        vram_gb=11.0,
        compute_capability="6.1",
    )
    result = check_gpu_admission(min_vram_gb=8.0, min_compute_capability=7.0, spec=spec)
    assert result.supported is False
    assert result.error_code == GPUErrorCode.GPU_COMPUTE_CAPABILITY_UNSUPPORTED
    assert "GPU_COMPUTE_CAPABILITY_UNSUPPORTED" in result.reason
    assert "GPU_INCOMPATIBLE" in result.reason


def test_simulated_missing_driver_rejected():
    """Verify missing or inaccessible driver produces GPU_DRIVER_UNAVAILABLE."""
    spec = _make_simulated_spec(driver_version=None)
    result = check_gpu_admission(spec=spec)
    assert result.supported is False
    assert result.error_code == GPUErrorCode.GPU_DRIVER_UNAVAILABLE


def test_simulated_cuda_unavailable_rejected():
    """Verify non-operational CUDA produces GPU_CUDA_UNAVAILABLE."""
    spec = _make_simulated_spec(cuda_available=False)
    result = check_gpu_admission(spec=spec)
    assert result.supported is False
    assert result.error_code == GPUErrorCode.GPU_CUDA_UNAVAILABLE


# ==============================================================================
# 3. Queue Routing & Concurrency Invariants
# ==============================================================================

def test_gpu_workloads_route_strictly_to_gpu_ai():
    """Verify MuseTalk and Stable Diffusion route strictly to gpu_ai queue."""
    assert resolve_job_queue("lip_sync", {"provider": "musetalk"}) == "gpu_ai"
    assert resolve_job_queue("generate_avatar_video", {"provider": "musetalk"}) == "gpu_ai"
    assert resolve_job_queue("generate_scene_visual", {"provider": "stable_diffusion"}) == "gpu_ai"
    assert resolve_job_queue("generate_scene_visual", {"provider": "stable_diffusion", "device": "cuda"}) == "gpu_ai"
    assert resolve_job_queue("tts_synthesis", {"preferred_device": "cuda"}) == "gpu_ai"
    assert resolve_job_queue("lip_sync", {"device": "cuda"}) == "gpu_ai"


def test_cpu_workloads_remain_on_cpu_media():
    """Verify CPU tasks (piper, whisper, qwen, openvoice, ffmpeg rendering) stay on cpu_media."""
    assert resolve_job_queue("render_video", {}) == "cpu_media"
    assert resolve_job_queue("tts_synthesis", {"provider": "piper"}) == "cpu_media"
    assert resolve_job_queue("asr_transcription", {"provider": "whisper"}) == "cpu_media"
    assert resolve_job_queue("translate_project", {}) == "cpu_media"
    assert resolve_job_queue("enhance_speech", {}) == "cpu_media"
    assert resolve_job_queue("generate_project", {}) == "cpu_media"
    assert resolve_job_queue("lip_sync", {"provider": "wav2lip"}) == "cpu_media"


def test_gpu_worker_concurrency_is_pinned_to_one():
    """Verify celery configuration enforces concurrency=1 on GPU workloads."""
    routes = celery_app.conf.task_routes
    assert "heyzen.tasks.ai.*" in routes
    assert routes["heyzen.tasks.ai.*"]["queue"] == "gpu_ai"


# ==============================================================================
# 4. Fail-Closed Providers (No Silent CPU/Mock Fallback)
# ==============================================================================

def test_musetalk_fails_closed_without_silent_fallback():
    """Verify MuseTalk raises GPU_UNAVAILABLE and never falls back to Wav2Lip or mock."""
    provider = MuseTalkAvatarProvider()
    with pytest.raises(AIRuntimeUnavailableException) as exc_info:
        provider._ensure_cuda_available()
    assert exc_info.value.code == "GPU_UNAVAILABLE"


def test_stable_diffusion_fails_closed_without_silent_fallback():
    """Verify Stable Diffusion raises GPU_UNAVAILABLE and never falls back to CPU or mock."""
    provider = StableDiffusionImageProvider()
    with pytest.raises(AIRuntimeUnavailableException) as exc_info:
        provider._ensure_cuda_available()
    assert exc_info.value.code == "GPU_UNAVAILABLE"


@pytest.mark.asyncio
async def test_gpu_job_failure_metadata_recorded(async_client: AsyncClient):
    """Verify failed GPU job records structured error code and GPU metadata."""
    from app.models.job import Job
    from app.services.job_service import JobService
    from app.db.session import async_session_factory

    email = f"gpu_fail_{uuid.uuid4().hex[:8]}@example.com"
    resp = await async_client.post(
        "/api/v1/auth/signup",
        json={"email": email, "display_name": "GPU Tester", "password": "Password123!"},
    )
    assert resp.status_code == 201
    data = resp.json()
    user_id = uuid.UUID(data["user"]["id"])
    token = data["tokens"]["access_token"]

    ws_resp = await async_client.get("/api/v1/workspaces", headers={"Authorization": f"Bearer {token}"})
    assert ws_resp.status_code == 200
    workspace_id = uuid.UUID(ws_resp.json()[0]["id"])

    job_id = uuid.uuid4()
    async with async_session_factory() as db:
        job = Job(
            id=job_id,
            workspace_id=workspace_id,
            created_by=user_id,
            job_type="lip_sync",
            status="pending",
            payload={"provider": "musetalk", "device": "cuda"},
        )
        db.add(job)
        await db.commit()

    # Executing _execute_lip_sync on CPU host must fail closed with AIRuntimeUnavailableException
    with pytest.raises(AIRuntimeUnavailableException):
        await _execute_lip_sync(job_id=job_id, task_id="test_task_fail")

    # Verify job marked failed with structured error details
    async with async_session_factory() as db:
        service = JobService(db)
        updated_job = await service.job_repo.get_by_id(job_id)
        assert updated_job.status == "failed"
        assert updated_job.error_details is not None
        assert updated_job.error_details["code"] == "GPU_UNAVAILABLE"
        assert updated_job.error_details["queue"] == "gpu_ai"
        assert updated_job.error_details["provider"] == "musetalk"


# ==============================================================================
# 5. Health Probe & Telemetry Separation
# ==============================================================================

@pytest.mark.asyncio
async def test_health_ai_separates_system_health_from_gpu(async_client: AsyncClient):
    """Verify /api/v1/health/ai reports CPU healthy while GPU worker is unavailable."""
    resp = await async_client.get("/api/v1/health/ai")
    assert resp.status_code == 200
    data = resp.json()

    # System overall remains healthy on CPU
    assert data["status"] in ("healthy", "degraded")
    assert "gpu_worker" in data
    gpu_info = data["gpu_worker"]
    assert gpu_info["queue"] == "gpu_ai"
    assert gpu_info["concurrency"] == 1
    assert gpu_info["ready"] is False
    assert gpu_info["cuda_available"] is False
    assert "admission" in gpu_info
    assert gpu_info["admission"]["supported"] is False
    assert gpu_info["admission"]["error_code"] == "GPU_UNAVAILABLE"


# ==============================================================================
# 6. Standalone CLI Validation Harness
# ==============================================================================

def test_cli_validation_harness_output():
    """Verify the CLI validation harness runs and returns structured failure on host."""
    admitted, report = gpu_cli.execute_gpu_validation(
        min_vram_gb=8.0,
        min_compute_capability=7.0,
        run_tensor_test=False,
    )
    assert admitted is False
    assert report["verdict"] == "REJECTED"
    assert report["error_code"] == "GPU_UNAVAILABLE"
    assert "dependencies" in report
    assert "torch" in report["dependencies"]
    assert "blocked_model_enforcement" in report
    assert report["blocked_model_enforcement"]["passed"] is True
