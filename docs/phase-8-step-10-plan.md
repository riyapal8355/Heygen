# Phase 8 Step 10 — Real Local AI Image Generation for Scene Visuals Plan

**Implementation Status**: PLANNING & AUDIT COMPLETED — PENDING EXECUTION  
**Target Milestone**: Phase 8 Step 10  
**System**: HeyZen Autonomous AI Video Studio  
**Date**: September 2026  

---

## 1. Executive Summary

In HeyZen, each scene in a video project timeline (`ProjectDocumentV1`) can feature a generative background visual layer (still image or motion b-roll). Currently, scene visual generation relies on `MockImageProvider` and `create_valid_mock_png_fixture` in `backend/app/services/scene_visuals_service.py`.

The objective of **Phase 8 Step 10** is to implement a **real, commercially safe, local AI image generation provider** for HeyZen scene visuals, integrating smoothly with `SceneVisualsOrchestrator`, MinIO asset storage, Celery job routing, and immutable `ProjectVersion` OCC history.

### Core Audit & Architectural Findings:
1. **Model Selection & Licensing Minefield**:
   - **SDXL-Turbo / SD-Turbo (`stabilityai/sdxl-turbo`, `stabilityai/sd-turbo`)**: Restricted by the *Stability AI Non-Commercial Research Community License*. Commercial use is strictly forbidden without a proprietary license from Stability AI. **BANNED from production.**
   - **Stable Diffusion v1.5 (`runwayml/stable-diffusion-v1-5`)**: Licensed under **CreativeML OpenRAIL-M**. Section 5 explicitly permits royalty-free commercial SaaS, hosting, and self-hosted applications subject to standard behavioral safety use restrictions. Classified as **`COMMERCIAL_SAFE`**.
   - **Stable Diffusion v2.1-base (`stabilityai/stable-diffusion-2-1-base`)**: Licensed under **CreativeML OpenRAIL++-M** (commercial use permitted). Checkpoint size ~5.2 GB.
2. **Hardware Constraints (AMD Ryzen 5 5500U, CPU-only, 16GB RAM, No CUDA)**:
   - Latent diffusion models (Stable Diffusion 1.5, 2.1, etc.) require 6–8 GB VRAM for interactive generation.
   - On CPU, running a 4.27 GB diffusion model in FP32 takes 2–5 minutes per step (40–100+ minutes per image) and consumes 10–12+ GB RAM, which would cause severe server unresponsiveness and worker timeouts.
   - The virtual environment (`backend/.venv`) does not contain `torch` or `diffusers` (and installing CUDA PyTorch is not applicable on an AMD CPU-only machine).
3. **Architectural Resolution**:
   - Establish `StableDiffusionImageProvider(ImageProvider)` targeting **NVIDIA CUDA** worker nodes on the `gpu_ai` Celery queue.
   - Implement a strict hardware guard: On CPU-only hosts, invoking `generate_image` or `generate` raises `AIRuntimeUnavailableException(code="GPU_UNAVAILABLE")`.
   - In `AI_PROVIDER_MODE="real"`, enforce **zero silent fallback** to mock or synthetic fixtures.
   - Implement strict image validation with Pillow (`PIL.Image`): decodable container, non-zero dimensions, valid aspect ratio, RGB mode, non-empty buffer.
   - Maintain zero frontend modifications and zero database migrations.

---

## 2. Audit of Existing Image Generation Infrastructure

### 1. Request Contract
`GenerateSceneVisualRequest` in `backend/app/schemas/orchestration.py`:
- `visual_type: Literal["image", "video"] = Field("image")`
- `prompt: str = Field(..., min_length=3, max_length=1000)`
- `aspect_ratio: Literal["16:9", "9:16", "1:1"] = Field("16:9")`
- `expected_revision: int = Field(..., ge=1)`
- `run_async: bool = Field(True)`
- `idempotency_key: Optional[str] = Field(None)`

`ImageGenContractRequest` in `backend/app/ai/contracts.py`:
- `prompt: str = Field(..., min_length=1, max_length=2000)`
- `aspect_ratio: Literal["16:9", "9:16", "1:1", "4:3", "21:9"] = Field("16:9")`
- `negative_prompt: Optional[str] = Field(None, max_length=1000)`
- `output_format: Literal["png", "jpg", "webp"] = Field("png")`

### 2. Provider Protocol Contract
`ImageProvider` in `backend/app/ai/interfaces.py`:
```python
@runtime_checkable
class ImageProvider(Protocol):
    async def generate_image(
        self,
        prompt: str,
        aspect_ratio: str = "16:9",
        negative_prompt: Optional[str] = None,
    ) -> str: ...

    async def generate(
        self,
        request: ImageGenContractRequest,
    ) -> ImageGenContractResult: ...
```

### 3. Current Mock Behavior
`MockImageProvider` in `backend/app/ai/adapters/mock.py`:
- Generates a synthetic key `mock/generated_images/img_{hash}.png`.
- Maps aspect ratio to nominal resolution: `16:9` -> (1920, 1080), `9:16` -> (1080, 1920), `1:1` -> (1024, 1024).
- In `scene_visuals_service.py`, generates a fixture using `create_valid_mock_png_fixture()`.

### 4. Asset Lifecycle Flow
- Binary is written to temporary location managed by `MediaTempManager`.
- Ingested via `AssetLifecycleManager.ingest_generated_asset()`:
  - Stored in MinIO at `workspaces/{workspace_id}/assets/{asset_id}/...`
  - Created in PostgreSQL `assets` table with MIME type, byte size, SHA-256 checksum, and metadata (`project_id`, `scene_id`, `prompt`, `generated=True`).

### 5. Scene Update & OCC Flow
- Target scene background updated: `target_scene.background = {"type": "image", "asset_id": str(asset.id), "storage_key": asset.storage_key}`.
- Asset appended to `doc.assets`.
- `ProjectService.create_version(..., expected_revision=request.expected_revision)` commits immutable `ProjectVersion`.
- If `expected_revision` does not match active version, raises `ConflictException` (`REVISION_CONFLICT`).

### 6. Job Execution Flow
- Endpoint: `POST /api/v1/workspaces/{ws}/projects/{id}/scenes/{scene_id}/generate-visual`.
- `run_async=True`: Submits Job `generate_scene_visual`, returns `HTTP 202 Accepted` with `JobResponse`.
- Celery Task: `heyzen.tasks.ai.generate_scene_visual` executes `SceneVisualsOrchestrator.generate_scene_visual(...)`.
- Updates job state: `generating_visual` -> `succeeded` or `failed`.

### 7. Model Lifecycle Hooks
- `ModelLifecycleManager` (`backend/app/ai/lifecycle.py`): Enforces `AI_ALLOW_AUTO_DOWNLOAD=False`, SHA-256 integrity verification, and active rejection of banned non-commercial models.

---

## 3. Candidate Model Evaluation & License Audit

| Model Candidate | Checkpoint / Repo | Parameters / Size | Base License | Commercial Use | Feasibility on CPU | Audit Decision |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **SDXL-Turbo** | `stabilityai/sdxl-turbo` | 3.5 GB | Stability Non-Commercial | **FORBIDDEN** | Infeasible | **REJECTED (BANNED)** |
| **SD-Turbo** | `stabilityai/sd-turbo` | 2.5 GB | Stability Non-Commercial | **FORBIDDEN** | Infeasible | **REJECTED (BANNED)** |
| **Stable Diffusion v1.5** | `runwayml/stable-diffusion-v1-5` | 4.27 GB | CreativeML OpenRAIL-M | **PERMITTED** | CUDA required | **SELECTED (PRODUCTION TARGET)** |
| **Stable Diffusion v2.1** | `stabilityai/stable-diffusion-2-1-base` | 5.2 GB | CreativeML OpenRAIL++-M | **PERMITTED** | CUDA required | Viable alternative |

### Production Artifact Details: Stable Diffusion v1.5
- **Repository**: `runwayml/stable-diffusion-v1-5`
- **Revision / Commit**: `1dce59b` (v1.5)
- **Primary Weights**: `v1-5-pruned-emaonly.safetensors`
- **File Size**: 4,265,380,512 bytes (~4.27 GB)
- **SHA-256 Checksum**: `6ce016e7d0fe7376494aaeae77f3e3e1c500ec6c76db432e23702d2b57347774`
- **License**: CreativeML OpenRAIL-M
- **Auxiliary Weights**:
  - Text Encoder: `openai/clip-vit-large-patch14` (MIT)
  - VAE: `stabilityai/sd-vae-ft-mse` (MIT / OpenRAIL-M)
  - UNet: SD1.5 UNet (CreativeML OpenRAIL-M)
  - Tokenizer: CLIP Tokenizer (Apache-2.0 / MIT)

---

## 4. Proposed Architecture & Media Pipeline

```
Client / Worker Request (Job: generate_scene_visual)
       │
       ▼
[ Queue Resolution: `resolve_job_queue` ] ──► Routes to `gpu_ai` (provider="stable_diffusion" or preferred_device="cuda")
       │
       ▼
[ Hardware Guard: `_ensure_cuda_available()` ]
  ├── CPU host ─────────────────────────────► Raises AIRuntimeUnavailableException(code="GPU_UNAVAILABLE")
  └── CUDA host ────────────────────────────► Proceeds to worker execution
       │
       ▼
[ Prompt Preprocessing & Aspect Ratio Mapping ]
  ├── 16:9 ──► 1024x576 (or 512x288 scaled / 768x432)
  ├── 9:16 ──► 576x1024
  └── 1:1  ──► 512x512
       │
       ▼
[ Stable Diffusion CUDA Diffusion Loop ] ──► Generates raw image buffer
       │
       ▼
[ Image Output Validation (Pillow) ]
  ├── Verify decodable container (PNG/JPEG)
  ├── Verify dimensions and aspect ratio match
  ├── Verify color mode in (RGB, RGBA)
  └── Verify non-empty byte buffer
       │
       ▼
[ MinIO Ingestion & Asset Lifecycle ] ──────► AssetLifecycleManager.ingest_generated_asset()
       │
       ▼
[ Scene Layer Binding & Document Manifest ] ─► target_scene.background = {"type": "image", "asset_id": ...}
       │
       ▼
[ Optimistic Concurrency Control (OCC) ] ───► ProjectService.create_version() with expected_revision
```

---

## 5. Implementation Steps

1. **Implement `StableDiffusionImageProvider`** in `backend/app/ai/adapters/stable_diffusion.py`:
   - Conforms to `ImageProvider` protocol (`generate_image`, `generate`).
   - Descriptor: `capability="image"`, `provider="stable_diffusion"`, `runtime="diffusers-cuda"`, `requires_gpu=True`, `supported_devices=["cuda"]`, `license_classification="CONDITIONAL — ARTIFACT VERIFICATION REQUIRED"`.
   - Banned component validation: strictly rejects `sdxl-turbo`, `sd-turbo`, etc.
   - Hardware guard: `_ensure_cuda_available()` raising `GPU_UNAVAILABLE` on CPU.
   - Image validation using Pillow (`PIL.Image`).
2. **Register in `AIProviderRegistry`** in `backend/app/ai/registry.py`:
   - Register under `AICapability.IMAGE` (`provider="stable_diffusion"`).
   - In `AI_PROVIDER_MODE="real"`, resolve `stable_diffusion` as default image provider.
3. **Register in `ModelRegistry`** in `backend/app/ai/model_registry.py`:
   - Register `image/stable-diffusion-v1-5-gpu` (CreativeML OpenRAIL-M, 6 GB VRAM, 8 GB RAM).
4. **Update Celery Routing** in `backend/app/services/job_service.py`:
   - Route `generate_scene_visual` to `gpu_ai` when `provider="stable_diffusion"` or `preferred_device="cuda"`.
5. **Update `SceneVisualsOrchestrator`** in `backend/app/services/scene_visuals_service.py`:
   - Wire `image_provider = self.ai_registry.get_image_provider()` with typed execution.
   - Validate image before persistence.
6. **Tests**:
   - Descriptor, metadata, banned components rejection, CPU guard, registry resolution, image validation, Celery routing, OCC conflict handling, zero regression across test suite.
