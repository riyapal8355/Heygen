"""Standalone Replaceable Remote GPU Avatar Worker Service.

Runs on dedicated NVIDIA CUDA GPU instances (e.g. AWS g5.xlarge, RunPod, Lambda Labs, on-prem GPU).
Communicates with HeyZen backend via MinIO S3 object storage using workspace-scoped paths
and standardized REST contracts.

Endpoints (as specified by Section 11):
- GET /health: Worker health, CUDA availability, GPU model, VRAM
- GET /capabilities: Model & pipeline capability descriptors
- POST /jobs/avatar: Submit neural avatar generation job
- GET /jobs/{job_id}: Query job status and state machine progress

Job State Machine:
QUEUED -> PREPARING -> DOWNLOADING -> GENERATING_MOTION -> GENERATING_LIPSYNC -> COMPOSITING -> UPLOADING -> COMPLETED
(or FAILED / GPU_REQUIRED)
"""

from enum import Enum
import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.ai.adapters.hallo2 import Hallo2Adapter
from app.ai.adapters.liveportrait import LivePortraitAdapter, LivePortraitMotionOptions
from app.ai.adapters.musetalk import MuseTalkAvatarProvider
from app.ai.hardware import detect_hardware
from app.core.logging import get_logger
from app.media.ffmpeg import FFmpegService
from app.media.ffprobe import FFprobeService
from app.storage.s3 import get_storage_provider

logger = get_logger(__name__)

worker_app = FastAPI(
    title="HeyZen Remote GPU Avatar Worker",
    version="1.5.0",
    description="Dedicated CUDA GPU worker executing LivePortrait, MuseTalk 1.5, and Hallo2.",
)


class AvatarJobState(str, Enum):
    QUEUED = "QUEUED"
    PREPARING = "PREPARING"
    DOWNLOADING = "DOWNLOADING"
    GENERATING_MOTION = "GENERATING_MOTION"
    GENERATING_LIPSYNC = "GENERATING_LIPSYNC"
    COMPOSITING = "COMPOSITING"
    UPLOADING = "UPLOADING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    GPU_REQUIRED = "GPU_REQUIRED"


class JobAvatarRequest(BaseModel):
    job_id: str = Field(..., description="Unique avatar job identifier")
    workspace_id: str = Field(..., description="Workspace ID for MinIO isolation")
    source_avatar_asset: str = Field(..., description="MinIO storage key or asset key for source avatar image")
    driving_motion_asset: Optional[str] = Field(None, description="MinIO storage key or asset key for driving video")
    audio_asset: str = Field(..., description="MinIO storage key or asset key for audio WAV")
    provider: str = Field("liveportrait_musetalk", description="Neural provider: liveportrait, musetalk, hallo2, liveportrait_musetalk")
    model: str = Field("liveportrait-v1", description="Model identifier")
    resolution: int = Field(512, ge=256, le=1080)
    fps: int = Field(25, ge=15, le=60)


class JobAvatarResponse(BaseModel):
    job_id: str
    asset_id: str
    output_storage_key: str
    duration: float
    fps: int
    width: int
    height: int
    frame_count: int
    provider: str
    model: str
    model_version: str
    gpu_name: str
    generation_time: float
    state: AvatarJobState
    error_message: Optional[str] = None


# In-memory job state store
_JOB_STORE: Dict[str, Dict[str, Any]] = {}


@worker_app.get("/health")
def health() -> Dict[str, Any]:
    """Check GPU availability and VRAM on the worker node."""
    hw = detect_hardware()
    cuda_ready = hw.gpu.cuda_available
    return {
        "status": "healthy" if cuda_ready else "gpu_required",
        "cuda_available": cuda_ready,
        "gpu_name": f"{hw.gpu.vendor} {hw.gpu.model}",
        "vram_gb": hw.gpu.vram_total_gb,
        "vram_free_gb": hw.gpu.vram_free_gb,
        "supported_pipelines": ["liveportrait", "musetalk", "hallo2", "liveportrait_musetalk"],
    }


@worker_app.get("/capabilities")
def capabilities() -> Dict[str, Any]:
    """Expose worker capabilities and supported neural portrait models."""
    hw = detect_hardware()
    return {
        "worker_version": "1.5.0",
        "cuda_available": hw.gpu.cuda_available,
        "gpu_name": f"{hw.gpu.vendor} {hw.gpu.model}",
        "vram_gb": hw.gpu.vram_total_gb,
        "models": {
            "liveportrait": {
                "version": "1.0.0",
                "vendor": "KwaiVGI",
                "features": ["head_rotation", "gaze", "natural_blinking", "expression_retargeting", "stitching"],
                "cuda_required": True,
            },
            "musetalk": {
                "version": "1.5.0",
                "vendor": "TMElyralab",
                "features": ["neural_latent_lipsync", "whisper_audio_conditioning", "vae_decoding"],
                "cuda_required": True,
            },
            "hallo2": {
                "version": "2.0.0",
                "vendor": "Fudan",
                "features": ["hierarchical_audio_diffusion", "long_duration"],
                "cuda_required": True,
            },
        },
    }


@worker_app.get("/jobs/{job_id}", response_model=JobAvatarResponse)
def get_job(job_id: str) -> JobAvatarResponse:
    """Retrieve avatar job progress and status."""
    if job_id not in _JOB_STORE:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    data = _JOB_STORE[job_id]
    return JobAvatarResponse(**data)


@worker_app.post("/jobs/avatar", response_model=JobAvatarResponse)
async def create_avatar_job(req: JobAvatarRequest) -> JobAvatarResponse:
    """Execute neural portrait generation job synchronously or return state."""
    hw = detect_hardware()
    if not hw.gpu.cuda_available:
        err_msg = "LivePortrait requires a CUDA GPU. Configure a local or remote GPU worker."
        res = JobAvatarResponse(
            job_id=req.job_id,
            asset_id=f"avatar_gen_{req.job_id}",
            output_storage_key="",
            duration=0.0,
            fps=req.fps,
            width=req.resolution,
            height=req.resolution,
            frame_count=0,
            provider=req.provider,
            model=req.model,
            model_version="1.0.0",
            gpu_name="None",
            generation_time=0.0,
            state=AvatarJobState.GPU_REQUIRED,
            error_message=err_msg,
        )
        _JOB_STORE[req.job_id] = res.dict()
        return res

    storage = get_storage_provider()
    t0 = time.perf_counter()

    # MinIO workspace-scoped path convention as mandated by Section 12
    # workspace/{workspace_id}/avatar-jobs/{job_id}/output.mp4
    scoped_output_key = f"workspace/{req.workspace_id}/avatar-jobs/{req.job_id}/output.mp4"

    _JOB_STORE[req.job_id] = {
        "job_id": req.job_id,
        "asset_id": f"avatar_gen_{req.job_id}",
        "output_storage_key": scoped_output_key,
        "duration": 0.0,
        "fps": req.fps,
        "width": req.resolution,
        "height": req.resolution,
        "frame_count": 0,
        "provider": req.provider,
        "model": req.model,
        "model_version": "1.0.0",
        "gpu_name": f"{hw.gpu.vendor} {hw.gpu.model}",
        "generation_time": 0.0,
        "state": AvatarJobState.DOWNLOADING,
        "error_message": None,
    }

    with tempfile.TemporaryDirectory(prefix=f"worker_{req.job_id}_") as tmpdir:
        tmp_path = Path(tmpdir)
        source_path = tmp_path / "source.png"
        audio_path = tmp_path / "audio.wav"
        driving_path = tmp_path / "driving.mp4"
        output_path = tmp_path / "output.mp4"

        try:
            # Download source avatar & audio
            src_bytes = await storage.get_object(req.source_avatar_asset)
            source_path.write_bytes(src_bytes)

            aud_bytes = await storage.get_object(req.audio_asset)
            audio_path.write_bytes(aud_bytes)

            if req.driving_motion_asset:
                drv_bytes = await storage.get_object(req.driving_motion_asset)
                driving_path.write_bytes(drv_bytes)
        except Exception as exc:
            _JOB_STORE[req.job_id]["state"] = AvatarJobState.FAILED
            _JOB_STORE[req.job_id]["error_message"] = f"MinIO download failed: {exc}"
            raise HTTPException(status_code=400, detail=_JOB_STORE[req.job_id]["error_message"])

        # Execute neural motion
        prov = req.provider.lower()
        if prov in ("liveportrait", "liveportrait_musetalk"):
            if not driving_path.exists():
                _JOB_STORE[req.job_id]["state"] = AvatarJobState.FAILED
                _JOB_STORE[req.job_id]["error_message"] = "LivePortrait requires driving_motion_asset."
                raise HTTPException(status_code=400, detail="LivePortrait requires driving_motion_asset.")

            _JOB_STORE[req.job_id]["state"] = AvatarJobState.GENERATING_MOTION
            lp = LivePortraitAdapter()
            motion_video_path = tmp_path / "motion.mp4"
            await lp.generate_motion(
                source_avatar=source_path,
                driving_motion=driving_path,
                output_path=motion_video_path,
                options=LivePortraitMotionOptions(fps=req.fps, output_resolution=req.resolution),
            )

            if prov == "liveportrait":
                shutil.copy2(str(motion_video_path), str(output_path))
            else:
                _JOB_STORE[req.job_id]["state"] = AvatarJobState.GENERATING_LIPSYNC
                mt = MuseTalkAvatarProvider()
                await mt.synthesize_lipsync_from_motion_video(
                    motion_video=motion_video_path,
                    audio=audio_path,
                    output_path=output_path,
                    fps=req.fps,
                )

        elif prov == "hallo2":
            _JOB_STORE[req.job_id]["state"] = AvatarJobState.GENERATING_MOTION
            hallo = Hallo2Adapter()
            await hallo.synthesize_portrait(
                source_avatar=source_path,
                audio=audio_path,
                output_path=output_path,
                fps=req.fps,
                resolution=req.resolution,
            )
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported neural provider '{req.provider}'")

        # Validate render output
        _JOB_STORE[req.job_id]["state"] = AvatarJobState.COMPOSITING
        probe = await FFprobeService().validate_render_output(output_path)

        # Upload to scoped MinIO location
        _JOB_STORE[req.job_id]["state"] = AvatarJobState.UPLOADING
        await storage.put_object(scoped_output_key, output_path.read_bytes(), content_type="video/mp4")

        latency = time.perf_counter() - t0
        res_data = {
            "job_id": req.job_id,
            "asset_id": f"avatar_gen_{req.job_id}",
            "output_storage_key": scoped_output_key,
            "duration": probe.duration_seconds,
            "fps": probe.fps,
            "width": probe.width,
            "height": probe.height,
            "frame_count": probe.frame_count,
            "provider": req.provider,
            "model": req.model,
            "model_version": "1.0.0",
            "gpu_name": f"{hw.gpu.vendor} {hw.gpu.model}",
            "generation_time": round(latency, 2),
            "state": AvatarJobState.COMPLETED,
            "error_message": None,
        }
        _JOB_STORE[req.job_id] = res_data
        return JobAvatarResponse(**res_data)


# Backward-compatible alias for existing tests and scripts
@worker_app.post("/generate")
async def generate_legacy(req: JobAvatarRequest) -> JobAvatarResponse:
    return await create_avatar_job(req)


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("REMOTE_GPU_WORKER_PORT", 8100))
    uvicorn.run("app.ai.workers.remote_gpu_avatar_worker:worker_app", host="0.0.0.0", port=port, reload=False)
