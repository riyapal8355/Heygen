"""Health and readiness check endpoints."""

from fastapi import APIRouter, Response, status
from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.redis import ping_redis
from app.db.session import ping_db
from app.schemas.common import (
    AIHealthCapabilityStatus,
    AIHealthResponse,
    HealthResponse,
    ReadinessResponse,
)
from app.storage.s3 import get_storage_provider

logger = get_logger(__name__)
router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Application Liveness Probe",
    description="Returns HTTP 200 if the FastAPI application process is alive.",
)
async def get_health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        app=settings.APP_NAME,
        version=settings.APP_VERSION,
    )


@router.get(
    "/health/ai",
    response_model=AIHealthResponse,
    summary="AI Runtime & Capability Health Probe",
    description="Reports host hardware detection, compute runtimes (CPU/GPU), and AI capability statuses.",
)
async def get_ai_health() -> AIHealthResponse:
    from app.ai.hardware import detect_hardware
    from app.ai.runtimes import DeviceType, get_runtime_registry
    from app.ai.selection import select_model_and_runtime

    settings = get_settings()
    hw = detect_hardware()
    runtime_reg = get_runtime_registry()

    cpu_rt = runtime_reg.get_runtime_for_device(DeviceType.CPU)
    gpu_rt = runtime_reg.get_runtime_for_device(DeviceType.CUDA)

    runtimes_status = {
        "cpu": cpu_rt.check_health().value if cpu_rt else "unavailable",
        "gpu": gpu_rt.check_health().value if gpu_rt else "unavailable",
    }

    hardware_info = {
        "os": f"{hw.os_name} {hw.os_release} ({hw.cpu.architecture})",
        "cpu_model": hw.cpu.model,
        "cpu_cores": hw.cpu.logical_cores,
        "ram_total_gb": hw.memory.ram_total_gb,
        "ram_available_gb": hw.memory.ram_available_gb,
        "gpu_model": hw.gpu.model,
        "gpu_vendor": hw.gpu.vendor,
        "cuda_available": hw.gpu.cuda_available,
        "cuda_version": hw.gpu.cuda_version,
        "driver_version": hw.gpu.driver_version,
        "compute_capability": hw.gpu.compute_capability,
        "total_vram_gb": hw.gpu.vram_total_gb,
        "free_vram_gb": hw.gpu.vram_free_gb,
        "docker_gpu_available": hw.docker_gpu_available,
        "disk_free_gb": hw.disk.disk_free_gb,
    }

    # GPU Worker and gpu_ai queue telemetry (Failure-safe and informational)
    from app.ai.gpu_manifest import GPU_MODEL_MANIFEST
    from app.ai.hardware import check_gpu_admission
    admission = check_gpu_admission(spec=None)

    gpu_worker_info = {
        "queue": "gpu_ai",
        "concurrency": 1,
        "max_tasks_per_child": 50,
        "cuda_available": hw.gpu.cuda_available,
        "gpu_name": hw.gpu.model,
        "driver_version": hw.gpu.driver_version,
        "cuda_version": hw.gpu.cuda_version,
        "compute_capability": hw.gpu.compute_capability,
        "total_vram_gb": hw.gpu.vram_total_gb,
        "free_vram_gb": hw.gpu.vram_free_gb,
        "ready": bool(admission.supported),
        "admission": {
            "supported": admission.supported,
            "error_code": admission.error_code.value if admission.error_code else None,
            "reason": admission.reason,
        },
        "approved_workloads": [
            {"model_id": k, "status": v.commercial_status.value, "license": v.license}
            for k, v in GPU_MODEL_MANIFEST.items()
            if v.requires_gpu and v.commercial_status.value != "BLOCKED"
        ],
    }

    capabilities: dict[str, AIHealthCapabilityStatus] = {}
    cap_keys = ["tts", "asr", "translation", "image", "avatar", "video", "llm"]

    for cap in cap_keys:
        try:
            model, runtime = select_model_and_runtime(cap)
            is_healthy = runtime.check_health().value == "healthy"
            status_str = "healthy" if is_healthy else "degraded"
            capabilities[cap] = AIHealthCapabilityStatus(
                capability=cap,
                active_provider=model.provider,
                active_model=model.model_id,
                runtime_id=runtime.runtime_id,
                device=runtime.device_type.value,
                status=status_str,
                requires_gpu=model.requires_gpu,
            )
        except Exception:
            capabilities[cap] = AIHealthCapabilityStatus(
                capability=cap,
                active_provider="none",
                active_model="none",
                runtime_id="none",
                device="none",
                status="unavailable",
                requires_gpu=True,
            )

    overall_status = "healthy" if runtimes_status.get("cpu") == "healthy" else "degraded"

    return AIHealthResponse(
        status=overall_status,
        mode=settings.AI_RUNTIME_MODE,
        hardware=hardware_info,
        runtimes=runtimes_status,
        capabilities=capabilities,
        gpu_worker=gpu_worker_info,
    )



@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Application Readiness Probe",
    description="Verifies operational connectivity to PostgreSQL, Redis, and MinIO/S3 storage.",
)
async def get_readiness(response: Response) -> ReadinessResponse:
    # 1. Check PostgreSQL database
    db_ok = await ping_db()

    # 2. Check Redis
    redis_ok = await ping_redis()

    # 3. Check Storage (MinIO / S3)
    storage_provider = get_storage_provider()
    storage_ok = storage_provider.check_health()

    checks = {
        "database": "ok" if db_ok else "failed",
        "redis": "ok" if redis_ok else "failed",
        "storage": "ok" if storage_ok else "failed",
    }

    all_ready = db_ok and redis_ok and storage_ok

    if not all_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        logger.warning("Readiness probe check failed: %s", checks)
        return ReadinessResponse(status="unhealthy", checks=checks)

    return ReadinessResponse(status="ready", checks=checks)


@router.get(
    "/metrics",
    summary="Application Operational Metrics",
    description="Returns runtime metrics, API request counts, job transitions, and subsystem errors.",
    responses={
        200: {
            "description": "Snapshot of application runtime metrics counters, latency histograms, and worker statistics.",
        }
    },
)
async def get_metrics() -> dict:
    from app.core.metrics import get_metrics_registry
    registry = get_metrics_registry()
    return registry.get_snapshot()


