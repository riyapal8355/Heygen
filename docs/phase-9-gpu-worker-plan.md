# HeyZen — Phase 9 Implementation Specification & Architecture Report
# Production GPU Worker Architecture (`gpu_ai`)

**Document Version:** 2.0.0  
**Phase:** Phase 9 — Production GPU Worker Architecture (`gpu_ai`)  
**Status:** **IMPLEMENTED — CUDA VALIDATION PENDING**  
**Classification:** Production Infrastructure Specification & GPU Deployment Manual  
**Date:** September 16, 2026  

---

## 1. Executive Summary

Phase 9 completes the production GPU worker architecture for the HeyZen autonomous AI video studio platform. Dedicated containerized workers running against NVIDIA CUDA hardware consume workloads exclusively from the Celery `gpu_ai` queue.

Approved production generative capabilities:
1. **`MuseTalkAvatarProvider`** ([`musetalk.py`](file:///d:/HeyGen/video-ai-tools/backend/app/ai/adapters/musetalk.py)): Neural avatar lip-sync inference (`pytorch-cuda`, commercial OpenCV YuNet face detector, geometric polygon masking).
2. **`StableDiffusionImageProvider`** ([`stable_diffusion.py`](file:///d:/HeyGen/video-ai-tools/backend/app/ai/adapters/stable_diffusion.py)): Scene visual image generation (`diffusers-cuda`, Stable Diffusion v1.5 CreativeML OpenRAIL-M).

Strict Platform Constraints Preserved:
- **Frontend Frozen:** Zero changes to `src/**`, `public/**`, `package.json`, `package-lock.json`, Next.js configs.
- **Database Schema Frozen:** Zero migrations; Alembic head remains `0005_jobs_task_pipeline`.
- **Prohibited Workloads Strictly Blocked:** AnimateDiff, SDXL-Turbo, SD-Turbo, ModelScope T2V, and Zeroscope remain strictly blocked and fail closed.
- **No Silent Fallback:** GPU workloads never silently fall back to CPU or mock execution.

---

## 2. Hardware Validation State & Distinction

In strict adherence to truth-in-engineering standards:

| Component | Architecture & Code State | Artifact Integrity | Real CUDA Execution | Status Classification |
| :--- | :--- | :--- | :--- | :--- |
| **YuNet Face Detector** | **IMPLEMENTED** | **ARTIFACT VERIFIED** (SHA-256: `8f2383e...`) | CPU verified / CUDA prepared | **APPROVED** |
| **MuseTalk Core UNet** | **IMPLEMENTED** | Pending provisioning | Pending NVIDIA GPU | **CONDITIONAL** |
| **MuseTalk VAE** | **IMPLEMENTED** | Pending provisioning | Pending NVIDIA GPU | **CONDITIONAL** |
| **Stable Diffusion v1.5** | **IMPLEMENTED** | Pending provisioning | Pending NVIDIA GPU | **CONDITIONAL** |
| **AnimateDiff v1.5** | **BLOCKED** | N/A | N/A | **STRICTLY BLOCKED** |
| **SDXL-Turbo / SD-Turbo**| **BLOCKED** | N/A | N/A | **STRICTLY BLOCKED** |
| **ModelScope / Zeroscope**| **BLOCKED** | N/A | N/A | **STRICTLY BLOCKED** |

Current Development Host:
- Processor: AMD Ryzen 5 5500U with Radeon Graphics (12 logical cores)
- RAM: 16 GB DDR4
- GPU: AMD Radeon Graphics (no NVIDIA CUDA GPU)
- Acceptance Status: **`IMPLEMENTED — CUDA VALIDATION PENDING`**

---

## 3. Architecture & Target Topology

```
                              ┌─────────────────────────────┐
                              │    FastAPI API Gateway      │
                              │  (Stateless • Port 8000)    │
                              └──────────────┬──────────────┘
                                             │
                                             │ 1. Dispatches Tasks
                                             ▼
                              ┌─────────────────────────────┐
                              │         Redis 7             │
                              │  (Broker, Queue & Pub/Sub)  │
                              └──────┬───────────────┬──────┘
                                     │               │
            ┌────────────────────────┘               └────────────────────────┐
            │ Queue: `cpu_media`                              │ Queue: `gpu_ai`
            ▼                                                 ▼
┌───────────────────────────────┐                 ┌───────────────────────────────┐
│       CPU Media Worker        │                 │        GPU AI Worker          │
│   (Celery • Concurrency: 4)   │                 │   `heyzen-gpu-worker`         │
├───────────────────────────────┤                 │   (Celery • Concurrency: 1)   │
│ • FFmpeg video render/stitch  │                 ├───────────────────────────────┤
│ • Piper TTS (CPU ONNX)        │                 │ • MuseTalk neural lip-sync    │
│ • Faster-Whisper ASR (CPU)    │                 │ • Stable Diffusion v1.5       │
│ • CTranslate2 NMT (CPU)       │                 │ • OpenCV YuNet (GPU)          │
│ • DeepFilterNet3 audio clean  │                 │ • Concurrency: 1              │
│ • MediaPipe matting (CPU)     │                 │ • Max Tasks Per Child: 50     │
└───────────────┬───────────────┘                 └───────────────┬───────────────┘
                │                                                 │
                │ 2. Read/Write Audio, Video, Images              │ 2. Read/Write Assets
                ▼                                                 ▼
┌───────────────────────────────┐                 ┌───────────────────────────────┐
│     MinIO Object Storage      │                 │     PostgreSQL 16 Database    │
│    (Bucket: heyzen-assets)    │                 │    (Jobs, Assets, Versions)   │
└───────────────────────────────┘                 └───────────────────────────────┘
```

The CPU media worker and FastAPI container run completely independent of CUDA and do not require PyTorch or NVIDIA packages.

---

## 4. Docker Container Design

### 4.1 Base Image & System Dependencies
- **Base Image:** `nvidia/cuda:12.4.1-runtime-ubuntu22.04`
- **Python Version:** Deterministic Python 3.11 installed via `ppa:deadsnakes/ppa` with `python3.11-venv` and `python3.11-dev`.
- **Media Stack:** Native FFmpeg 4.4+, `libsm6`, `libxext6`, `libgl1`, `libglib2.0-0`.
- **Security:** Non-root execution as unprivileged user `heyzen` (UID 10001, GID 10001).
- **Network:** Joins internal Docker network `heyzen-network`; exposes zero public ingress ports.
- **Model Cache:** Maps `/app/models_cache` to named persistent volume `heyzen_models_cache`.

### 4.2 Dockerfile Specification
Location: [`infrastructure/docker/Dockerfile.gpu-worker`](file:///d:/HeyGen/video-ai-tools/infrastructure/docker/Dockerfile.gpu-worker)
Key features:
1. Multi-stage clean dependency installation.
2. Separate requirements handling via `requirements-gpu.txt`.
3. Entrypoint supervisor checking CUDA admission before Celery startup.

---

## 5. Dependency Separation

Two cleanly separated requirements specifications eliminate multi-gigabyte bloat from CPU development environments:

1. **`backend/requirements.txt` (CPU / Gateway):**
   - Contains: `fastapi`, `uvicorn`, `sqlalchemy`, `asyncpg`, `alembic`, `pydantic`, `redis`, `celery`, `boto3`, `piper-tts`, `onnxruntime`, `faster-whisper`, `ctranslate2`, `pillow`, `scipy`.
   - **Zero PyTorch CUDA packages.**

2. **`backend/requirements-gpu.txt` (GPU Worker Image Only):**
   - References `-r requirements.txt`.
   - Pins exact NVIDIA CUDA 12.4 wheels:
     ```text
     --extra-index-url https://download.pytorch.org/whl/cu124
     torch==2.4.1+cu124
     torchvision==0.19.1+cu124
     torchaudio==2.4.1+cu124
     diffusers==0.30.3
     accelerate==0.34.2
     safetensors==0.4.5
     transformers==4.44.2
     huggingface-hub==0.24.7
     ```

---

## 6. Docker Compose GPU Overlay

Location: [`infrastructure/docker/docker-compose.gpu.yml`](file:///d:/HeyGen/video-ai-tools/infrastructure/docker/docker-compose.gpu.yml)

```yaml
services:
  heyzen-gpu-worker:
    build:
      context: ./backend
      dockerfile: ../infrastructure/docker/Dockerfile.gpu-worker
    container_name: heyzen-gpu-worker
    restart: unless-stopped
    command: celery -A app.workers.celery_app.celery_app worker -Q gpu_ai -c 1 --max-tasks-per-child=50 --loglevel=INFO -n gpu_worker@%h
    environment:
      - APP_ENV=${APP_ENV:-production}
      - AI_PROVIDER_MODE=real
      - AI_RUNTIME_MODE=real
      - AI_PREFERRED_DEVICE=cuda
      - DATABASE_URL=postgresql+asyncpg://${POSTGRES_USER:-heyzen}:${POSTGRES_PASSWORD:-heyzen_dev_password}@postgres:5432/${POSTGRES_DB:-heyzen}
      - REDIS_URL=redis://redis:6379/0
      - S3_ENDPOINT_URL=http://minio:9000
      - S3_ACCESS_KEY_ID=${MINIO_ROOT_USER:-heyzen_admin}
      - S3_SECRET_ACCESS_KEY=${MINIO_ROOT_PASSWORD:-heyzen_dev_password123}
      - AI_MODEL_CACHE_DIR=/app/models_cache
      - AI_ALLOW_AUTO_DOWNLOAD=false
      - AI_VERIFY_CHECKSUMS=true
      - GPU_MIN_VRAM_GB=8.0
      - GPU_MIN_COMPUTE_CAPABILITY=7.0
      - GPU_WORKER_REQUIRE_MODELS=true
    volumes:
      - heyzen_models_cache:/app/models_cache
    networks:
      - heyzen-network
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
    depends_on:
      redis:
        condition: service_healthy
      postgres:
        condition: service_healthy
      minio:
        condition: service_healthy

volumes:
  heyzen_models_cache:
    name: heyzen_models_cache

networks:
  heyzen-network:
    name: heyzen-network
```

Validated using:
```bash
docker compose -f docker-compose.yml -f infrastructure/docker/docker-compose.gpu.yml config
```

---

## 7. GPU Startup Supervisor & Hardware Admission Gate

Location: [`backend/scripts/gpu_worker_entrypoint.py`](file:///d:/HeyGen/video-ai-tools/backend/scripts/gpu_worker_entrypoint.py)

Before starting the Celery worker to consume `gpu_ai`, the supervisor strictly enforces 10 criteria:
1. NVIDIA GPU physically exists.
2. NVIDIA driver is visible and accessible.
3. CUDA acceleration is operational.
4. PyTorch CUDA capability is confirmed (`torch.cuda.is_available() == True`).
5. GPU device compute capability satisfies requirement ($\ge 7.0$).
6. GPU total VRAM satisfies requirement ($\ge 8.0\text{ GB}$).
7. Model manifest catalog is present and valid.
8. Required model artifacts exist in persistent model cache.
9. Artifact checksums match expected SHA-256 hashes.
10. No blocked or non-commercial model artifact is present or active.

**Fail-Closed Behavior:** If ANY criterion fails, the supervisor emits a structured JSON diagnostic report, terminates with exit code 1, and **strictly refuses** to spawn the Celery worker process.

---

## 8. Deterministic Model Manifest Catalog

Location: [`backend/app/ai/gpu_manifest.py`](file:///d:/HeyGen/video-ai-tools/backend/app/ai/gpu_manifest.py)

| Model ID | Provider | Capability | Artifact | Size | Expected SHA-256 | License | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `avatar/yunet-2023mar` | `musetalk` | `avatar` | `face_detection_yunet_2023mar.onnx` | 232,589 B | `8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4` | Apache-2.0 | **APPROVED** |
| `avatar/musetalk-core` | `musetalk` | `avatar` | `pytorch_model.bin` | ~3.4 GB | Verified upon provision | MIT | **CONDITIONAL** |
| `avatar/musetalk-vae` | `musetalk` | `avatar` | `diffusion_pytorch_model.bin` | ~335 MB | Verified upon provision | MIT / OpenRAIL-M | **CONDITIONAL** |
| `image/stable-diffusion-v1-5-gpu` | `stable_diffusion` | `image` | `v1-5-pruned-emaonly.safetensors` | 4,265,380,512 B | `6ce016e7d0fe7376494aaeae77f3e3e1c500ec6c76db432e23702d2b57347774` | CreativeML OpenRAIL-M | **CONDITIONAL** |
| `video/animatediff-v1-5` | `animatediff` | `video` | N/A | N/A | N/A | Unverified Licensing | **BLOCKED** |
| `image/sdxl-turbo` | `stability` | `image` | N/A | N/A | N/A | Non-Commercial Research | **BLOCKED** |
| `image/sd-turbo` | `stability` | `image` | N/A | N/A | N/A | Non-Commercial Research | **BLOCKED** |
| `video/modelscope-t2v` | `modelscope` | `video` | N/A | N/A | N/A | Research Only | **BLOCKED** |
| `video/zeroscope` | `zeroscope` | `video` | N/A | N/A | N/A | CC-BY-NC-4.0 | **BLOCKED** |

---

## 9. Model Provisioning CLI

Location: [`backend/scripts/provision_gpu_models.py`](file:///d:/HeyGen/video-ai-tools/backend/scripts/provision_gpu_models.py)

Deterministic Provisioning Pipeline:
```
Download Stream
      ↓
Unique Temporary File (`.download.<pid>.tmp`)
      ↓
Verify Exact Byte Size
      ↓
Compute & Verify SHA-256
      ↓
Verify Catalog & Commercial Policy
      ↓
Atomic Rename (`os.replace`)
      ↓
READY
```
- **Prohibited Auto-Download:** Production inference never triggers background network downloads (`AI_ALLOW_AUTO_DOWNLOAD=False`). Missing models immediately raise `AI_AUTO_DOWNLOAD_PROHIBITED`.
- **Fail-Closed Security:** Corrupted or interrupted downloads are deleted immediately. Blocked models exit with code 1.

Usage Examples:
```bash
# Verify local artifact integrity
python scripts/provision_gpu_models.py --verify-only --all

# Download and verify Stable Diffusion v1.5
python scripts/provision_gpu_models.py --model-id image/stable-diffusion-v1-5-gpu
```

---

## 10. VRAM & CUDA Memory Management

1. **Concurrency Enforced at 1:** Worker runs with `-c 1` (`--concurrency=1`), serializing GPU inference tasks to prevent Out-of-Memory collisions.
2. **Post-Task Reclamation Hook:** Subclassed `HeyZenBaseTask.after_return` in [`app/workers/base.py`](file:///d:/HeyGen/video-ai-tools/backend/app/workers/base.py) executes:
   ```python
   gc.collect()
   if torch.cuda.is_available():
       torch.cuda.empty_cache()
       torch.cuda.ipc_collect()
   ```
3. **Child Process Recycling:** Configured with `--max-tasks-per-child=50` to automatically recycle worker child processes periodically, eliminating memory fragmentation.
4. **OOM Failure Interception:** `CUDA_OUT_OF_MEMORY` transitions job state directly to `failed` without infinite retry loops.

---

## 11. Celery Routing & Queue Resolution

[`JobService.resolve_job_queue`](file:///d:/HeyGen/video-ai-tools/backend/app/services/job_service.py) governs all task routing:
- `musetalk` $\rightarrow$ `gpu_ai`
- `stable_diffusion` $\rightarrow$ `gpu_ai`
- `device=cuda` or `requires_gpu=True` $\rightarrow$ `gpu_ai`
- CPU AI tasks (Piper TTS, Faster-Whisper ASR, CTranslate2 NMT, Qwen LLM, DeepFilterNet3) $\rightarrow$ `cpu_media`
- Video rendering / stitching $\rightarrow$ `cpu_media`

---

## 12. Health & Readiness Telemetry

The `/health/ai` endpoint ([`health.py`](file:///d:/HeyGen/video-ai-tools/backend/app/api/v1/endpoints/health.py)) exposes GPU worker telemetry safely:
- `cuda_available`
- `gpu_name`
- `driver_version`
- `cuda_version`
- `compute_capability`
- `total_vram_gb`
- `free_vram_gb`
- `gpu_worker.ready`
- `gpu_worker.approved_workloads`

On CPU development hosts lacking an NVIDIA GPU, `/health/ai` reports status `healthy` (with GPU degraded/unavailable) and does NOT fail the application.

---

## 13. Test Results & Verification

### Phase 9 Test Suite
Location: [`backend/tests/test_gpu_worker_routing.py`](file:///d:/HeyGen/video-ai-tools/backend/tests/test_gpu_worker_routing.py)
- Category A: Queue routing (4 tests) — PASSED
- Category B: GPU hardware admission (6 tests) — PASSED
- Category C: Security & path traversal (2 tests) — PASSED
- Category D: Artifact integrity & size validation (5 tests) — PASSED
- Category E: Model policy & blocked enforcement (3 tests) — PASSED
- Category F: No fallback & auto-download guard (3 tests) — PASSED
- Category G: Worker configuration (1 test) — PASSED
- **Total Phase 9 Tests: 24 passed in 3.91s.**

### Full Regression Suite
- Total Tests: **406 passed in 382.44s (6m 22s)**
- Failures: **0**
- Alembic Head: **`0005_jobs_task_pipeline`**

---

## 14. Deployment Instructions

### On NVIDIA GPU Production Host:
```bash
# 1. Clone repository and install NVIDIA Container Toolkit
# 2. Provision model weights to persistent volume
python backend/scripts/provision_gpu_models.py --all

# 3. Start services with GPU worker overlay
docker compose -f docker-compose.yml -f infrastructure/docker/docker-compose.gpu.yml up -d

# 4. Monitor GPU worker logs
docker compose logs -f heyzen-gpu-worker
```

### On CPU Development Machine:
```bash
# Standard CPU local development remains completely unaffected:
docker compose up -d postgres redis minio
cd backend && .venv\Scripts\uvicorn.exe app.main:app --reload
```
