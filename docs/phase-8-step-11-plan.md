# HeyZen — Phase 8 Step 11 Architectural Plan & Licensing Hardening Audit
# Real Local AI Generative Video / B-Roll Provider (`AICapability.VIDEO`)

**Document Version:** 1.1.0  
**Phase:** Phase 8 — Step 11 (Audit & Planning Only)  
**Status:** **IMPLEMENTATION BLOCKED — LICENSE/ARTIFACT VERIFICATION REQUIRED**  
**Classification:** Technical Specification & Deep Provenance/Licensing Audit  
**Date:** September 16, 2026  

---

## 1. Executive Summary

Phase 8 Steps 1 through 10 have implemented, hardened, and verified 8 of the 9 core AI capabilities defined in the HeyZen system:
1. `LLM` (Step 5 — Qwen 0.5B ONNX)
2. `TTS` (Step 2 — Piper ONNX)
3. `ASR` (Step 3 — Faster-Whisper CTranslate2)
4. `TRANSLATION` (Step 6 — CTranslate2 NMT)
5. `AVATAR` (Step 9 — MuseTalk CUDA / Wav2Lip CPU)
6. `IMAGE` (Step 10 — Stable Diffusion v1.5 CUDA)
7. `MATTING` (Step 7 — MediaPipe Selfie Segmentation)
8. `AUDIO_ENHANCE` (Step 8 — DeepFilterNet3 / Silero VAD / broadcast mastering)

The 9th and sole remaining core capability in [`AICapability`](file:///d:/HeyGen/video-ai-tools/backend/app/ai/registry.py#L40-L51) that currently lacks a real local AI provider is **`AICapability.VIDEO`**.

At present, resolving `get_video_provider()` returns only [`MockVideoProvider`](file:///d:/HeyGen/video-ai-tools/backend/app/ai/adapters/mock.py#L464-L507). When a client or orchestrator requests generative b-roll video for a scene (`POST .../scenes/{scene_id}/generate-visual` with `visual_type="video"`), [`SceneVisualsOrchestrator`](file:///d:/HeyGen/video-ai-tools/backend/app/services/scene_visuals_service.py#L122-L155) falls back to synthesizing synthetic MP4 solid color fixtures via `create_valid_mock_mp4_fixture`.

### Step 11 Candidate Evaluation & Licensing Blocker
The candidate architecture evaluated for Phase 8 Step 11 was **AnimateDiff v1.5 v2** ([`guoyww/animatediff-motion-adapter-v1-5-2`](https://huggingface.co/guoyww/animatediff-motion-adapter-v1-5-2)) built upon the **Stable Diffusion v1.5** foundation ([`runwayml/stable-diffusion-v1-5`](https://huggingface.co/runwayml/stable-diffusion-v1-5)).

However, a forensic artifact-level licensing and provenance audit conducted directly against the upstream Hugging Face repository and training data revealed that:
1. **The model weight repository (`guoyww/animatediff-motion-adapter-v1-5-2`) contains NO `LICENSE` file** (returns HTTP 404).
2. **The model card YAML metadata contains NO `license:` declaration** (only `library_name: diffusers` and `pipeline_tag: text-to-video`).
3. **The motion adapter weights were trained on WebVid-10M**, a dataset scraped from stock video providers (Shutterstock) with explicit non-commercial academic research restrictions, which was subsequently taken down following copyright infringement claims.
4. While the original Python source code of the AnimateDiff inference script on GitHub is licensed under Apache-2.0, **the trained neural weight artifact (`diffusion_pytorch_model.safetensors`) does NOT carry an explicit commercial license grant**.

In accordance with HeyZen Project Rules (Rules 17, 18, 19, 20):
> **BLOCKER:**  
> **"AnimateDiff motion-adapter artifact license cannot currently be established with sufficient confidence for HeyZen's production/commercial-use policy."**

Therefore, the production implementation of `AnimateDiffVideoProvider` is **STOPPED AND BLOCKED** pending resolution of weight licensing or authorization of an alternative commercially unencumbered model.

**Current Step 11 Status:** **`IMPLEMENTATION BLOCKED — LICENSE/ARTIFACT VERIFICATION REQUIRED`**

---

## 2. Current-State Audit

### 2.1 Provider Registry & Interfaces
- [`backend/app/ai/registry.py`](file:///d:/HeyGen/video-ai-tools/backend/app/ai/registry.py):
  - `AICapability.VIDEO = "video"` is defined in `AICapability` enum.
  - `CAPABILITY_PROTOCOLS[AICapability.VIDEO] = VideoProvider`.
  - In `AI_PROVIDER_MODE == "real"`, `VIDEO` is the **only capability without a default real provider mapping** (lines 174–191).
  - Registry only has `MockVideoProvider` registered under `"mock"`.
- [`backend/app/ai/interfaces.py`](file:///d:/HeyGen/video-ai-tools/backend/app/ai/interfaces.py#L251-L270):
  - Defines `@runtime_checkable class VideoProvider(Protocol)` with methods:
    - `generate_video(prompt: str, duration_seconds: float = 4.0, aspect_ratio: str = "16:9") -> str`
    - `generate(request: VideoGenContractRequest) -> VideoGenContractResult`
- [`backend/app/ai/contracts.py`](file:///d:/HeyGen/video-ai-tools/backend/app/ai/contracts.py#L125-L149):
  - `VideoGenContractRequest` defines typed schema: `workspace_id`, `user_id`, `prompt`, `duration_seconds`, `aspect_ratio`, `negative_prompt`, `fps`, `resolution`.
  - `VideoGenContractResult` defines output: `status`, `output_storage_key`, `resolution`, `fps`, `duration_seconds`, `metrics`.

### 2.2 Scene Visuals Orchestration
- [`backend/app/services/scene_visuals_service.py`](file:///d:/HeyGen/video-ai-tools/backend/app/services/scene_visuals_service.py):
  - Accepts [`GenerateSceneVisualRequest`](file:///d:/HeyGen/video-ai-tools/backend/app/schemas/orchestration.py#L62-L73) (`visual_type: Literal["image", "video"]`).
  - `request.visual_type == "image"` was upgraded in Step 10 to real `StableDiffusionImageProvider`.
  - `request.visual_type == "video"` currently executes (lines 122–155):
    ```python
    video_provider = self.ai_registry.get_video_provider()
    contract_res = await video_provider.generate(contract_req)
    create_valid_mock_mp4_fixture(tmp_file, duration_seconds=contract_res.duration_seconds or 5.0)
    ```
    This leaves video generation mock-only.

### 2.3 Document Model & Timeline Compositor
- [`backend/app/schemas/project_document.py`](file:///d:/HeyGen/video-ai-tools/backend/app/schemas/project_document.py):
  - `Scene.background` supports `{"type": "video", "asset_id": "...", "storage_key": "..."}`.
- [`backend/app/media/compositor.py`](file:///d:/HeyGen/video-ai-tools/backend/app/media/compositor.py):
  - `TimelineCompositor` natively loops, scales, and layers video backgrounds behind avatars and subtitles during real video render export.

---

## 3. Detailed Forensic Licensing Audit of Candidate Model

### 3.1 Target Artifact Under Audit
- **Hugging Face Model ID:** `guoyww/animatediff-motion-adapter-v1-5-2`
- **Primary Git Commit:** `6167b88ffe39b4441fdf2113e77b99a6f56b7906`
- **Target Filename:** `diffusion_pytorch_model.safetensors`
- **Exact Artifact Size:** 1,791,374,336 bytes (~1.67 GiB)
- **SHA-256 Checksum:** `d95c417ddd4ffe1f7d4df43b51ef1c2c3c4fd7c3fd5ae53c75ef5d798a2213a3`
- **FP16 Variant:** `diffusion_pytorch_model.fp16.safetensors` (895,687,168 bytes, SHA-256: `d866a4f9a0c1054a32c3f858a70c0c7e2c94bb2e`)

### 3.2 Artifact-Level Repository Inspection
A direct inspection of the Hugging Face model repository files via HTTP API (`https://huggingface.co/api/models/guoyww/animatediff-motion-adapter-v1-5-2`) established:
1. **Sibling Files Present in Repository:**
   - `.gitattributes`
   - `README.md`
   - `config.json`
   - `diffusion_pytorch_model.fp16.safetensors`
   - `diffusion_pytorch_model.safetensors`
2. **Missing License File:**
   - Request to `https://huggingface.co/guoyww/animatediff-motion-adapter-v1-5-2/raw/main/LICENSE` returned **HTTP 404 Not Found**.
   - Request to `https://huggingface.co/guoyww/animatediff-motion-adapter-v1-5-2/raw/main/LICENSE.txt` returned **HTTP 404 Not Found**.
   - There is NO license document anywhere within the repository tree.
3. **Missing Model Card Metadata:**
   - The raw YAML frontmatter of `README.md` contains only:
     ```yaml
     ---
     library_name: diffusers
     pipeline_tag: text-to-video
     ---
     ```
   - The `tags` array in the model metadata contains: `["diffusers", "safetensors", "text-to-video", "region:us"]`.
   - **There is NO `license:` tag** in the metadata or model card.
4. **README Body:**
   - The README describes the technical architecture of inserting motion module layers into Stable Diffusion UNet and provides a diffusers code snippet.
   - It contains zero statements regarding commercial use, licensing terms, or redistribution rights.

### 3.3 Provenance & Training Data Audit
- **Authors & Research:** Yuwei Guo et al. (*AnimateDiff: Animate Your Personalized Text-to-Image Diffusion Models without Specific Tuning*, ICLR 2024).
- **Training Dataset:** The motion adapter weights were trained on the **WebVid-10M** dataset.
- **WebVid-10M Licensing & Legal Status:**
  - WebVid-10M consists of 10.7 million video-text pairs scraped from Shutterstock without commercial licensing.
  - The dataset terms of use issued by the creators (University of Oxford VGG) explicitly restricted use to **non-commercial academic research and benchmarking**.
  - In late 2023, the dataset was completely withdrawn by the authors following copyright infringement cease-and-desist actions from content owners.
- **Legal Implication for Weights:**
  - Because the motion module weights are a direct mathematical derivation of training on WebVid-10M, releasing them under a commercial open-source license without an explicit copyright grant is legally ambiguous.
  - While the authors released their Python training/inference code under Apache-2.0 on GitHub (`guoyww/AnimateDiff`), they **did not attach an Apache-2.0 or OpenRAIL-M license to the pre-trained weight checkpoints**.
  - Inferring an Apache-2.0 license for the weights from the Python code repository is legally invalid and violates HeyZen's compliance policy.

### 3.4 Audit Conclusion on Motion Adapter
- **Exact License:** **UNSPECIFIED / UNLICENSED** on the weight artifact itself.
- **Commercial Permissibility:** **UNPROVEN & RESTRICTED BY TRAINING DATA PROVENANCE**.
- **Commercial SaaS / Self-Hosting:** Cannot be declared safe for commercial hosting.
- **Classification:** **`CONDITIONAL — ARTIFACT VERIFICATION REQUIRED` (BLOCKED)**.

---

## 4. Complete Production Runtime Dependency Graph

A full trace of every model weight, configuration, and auxiliary dependency that would be loaded during execution of an AnimateDiff text-to-video pipeline:

```
AnimateDiff Pipeline Invocations
  │
  ├── 1. Motion Adapter Weights
  │     ├── Repository: `guoyww/animatediff-motion-adapter-v1-5-2`
  │     ├── File: `diffusion_pytorch_model.safetensors` (~1.79 GB)
  │     ├── SHA-256: `d95c417ddd4ffe1f7d4df43b51ef1c2c3c4fd7c3fd5ae53c75ef5d798a2213a3`
  │     ├── Training Data: WebVid-10M (Non-commercial research only)
  │     └── License: UNSPECIFIED / UNLICENSED (BLOCKED)
  │
  ├── 2. Stable Diffusion v1.5 Base UNet & Checkpoint
  │     ├── Repository: `runwayml/stable-diffusion-v1-5`
  │     ├── File: `v1-5-pruned-emaonly.safetensors` (~4.27 GB)
  │     ├── SHA-256: `6ce016e7d0fe7376494aaeae77f3e3e1c500ec6c76db432e23702d2b57347774`
  │     ├── Training Data: LAION-5B
  │     └── License: CreativeML OpenRAIL-M (Commercial SaaS permitted under Section 5)
  │
  ├── 3. VAE (Variational Autoencoder)
  │     ├── Integrated inside `v1-5-pruned-emaonly.safetensors` or `stabilityai/sd-vae-ft-mse`
  │     ├── File: `diffusion_pytorch_model.safetensors` (~335 MB)
  │     └── License: CreativeML OpenRAIL-M / MIT (Commercial permitted)
  │
  ├── 4. Text Encoder (CLIP ViT-L/14)
  │     ├── Integrated inside `v1-5-pruned-emaonly.safetensors` (OpenAI CLIP)
  │     ├── Weight Size: ~492 MB
  │     └── License: MIT License (Commercial permitted)
  │
  ├── 5. Tokenizer (CLIPTokenizer)
  │     ├── Files: `vocab.json`, `merges.txt` (~1 MB)
  │     └── License: MIT License (Commercial permitted)
  │
  ├── 6. Scheduler (DDIMScheduler / DPMSolverMultistep)
  │     ├── Algorithmic code in Hugging Face Diffusers
  │     └── License: Apache-2.0
  │
  ├── 7. Hidden / Automatic Auxiliary Downloads Investigation:
  │     ├── Safety Checker (`CompVis/stable-diffusion-safety-checker`):
  │     │     ├── If `safety_checker` parameter is omitted in `AnimateDiffPipeline.from_pretrained`,
  │     │     │   Diffusers AUTOMATICALLY downloads `CompVis/stable-diffusion-safety-checker` (~1.22 GB weights)!
  │     │     └── Hardening Requirement: Provider MUST explicitly instantiate with `safety_checker=None`
  │     │         to prevent hidden background downloads.
  │     ├── Feature Extractor (`CLIPImageProcessor`):
  │     │     └── Omitted when `safety_checker=None`.
  │     └── Motion LoRA Weights:
  │           └── None loaded unless explicitly requested in pipeline config.
  │
  └── 8. Media Processing & Output Validation:
        ├── Video Encoder: FFmpeg (H.264 / yuv420p, invoked via external subprocess)
        └── Validator: FFprobe (Stream validation, codec inspection)
```

---

## 5. Candidate Comparison & Banned Models Audit

| Candidate Model | Upstream Source & Model | VRAM Footprint | License Status | Commercial Classification | Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **AnimateDiff v1.5 v2** | `guoyww/animatediff-motion-adapter-v1-5-2` | ~8–10 GB | Motion adapter: Unlicensed / WebVid-10M. Base: OpenRAIL-M. | `CONDITIONAL — ARTIFACT VERIFICATION REQUIRED` | **BLOCKED** (Adapter artifact license unproven) |
| **ModelScope Text-to-Video** | `damo-vilab/modelscope-damo-text-to-video-synthesis` | ~10 GB | **CC-BY-NC 4.0** | **NON_COMMERCIAL (BANNED)** | **STRICTLY PROHIBITED** |
| **Zeroscope v2** | `cerspense/zeroscope_v2_576w` | ~9 GB | **CC-BY-NC 4.0** | **NON_COMMERCIAL (BANNED)** | **STRICTLY PROHIBITED** |
| **CogVideoX-2B** | `THUDM/CogVideoX-2b` | $\ge 18$ GB | Apache-2.0 | COMMERCIAL_SAFE | **REJECTED** (Excessive VRAM; OOM on consumer/cloud GPU workers) |
| **Stable Video Diffusion (SVD-XT)** | `stabilityai/stable-video-diffusion-img2vid-xt` | $\ge 14$ GB | Stability AI Community License | RESTRICTED | **REJECTED** (Proprietary commercial limits / revenue thresholds) |
| **Open-Sora** | `hpcaitech/Open-Sora` | $\ge 16$ GB | Apache-2.0 | COMMERCIAL_SAFE | **REJECTED** (Multi-minute latency, high VRAM) |

### Non-Commercial Ban Enforcement:
Both `damo-vilab/modelscope-damo-text-to-video-synthesis` and `cerspense/zeroscope_v2_576w` are governed by **CC-BY-NC 4.0**. Section 2(a)(1) explicitly forbids commercial deployment. They are permanently banned and actively blocked from entering any HeyZen runtime path.

---

## 6. Hardware Boundary & CPU Refusal

- **Development Host:** AMD Ryzen 5 5500U, 6 cores / 12 threads, 16 GB RAM, integrated graphics (no NVIDIA CUDA GPU).
- **Hard Hardware Boundary:**
  - Video diffusion models require calculating 4D temporal latent representations. On CPU, inference takes $\ge 60$ minutes per 2-second clip and causes system memory thrashing.
  - In accordance with HeyZen Project Rules, **zero fake neural inference will be executed, zero synthetic benchmarks will be manufactured, and CPU video diffusion is strictly forbidden**.
  - If invoked, the adapter must raise `AIRuntimeUnavailableException(code="GPU_UNAVAILABLE")` immediately.
  - In `AI_PROVIDER_MODE="real"`, **zero silent fallback to mock is permitted**.

---

## 7. Architecture Integration (When Unblocked)

Should an artifact-verified or author-clarified license be obtained in the future, the integration architecture is defined as follows:

```
Client API Request: POST /api/v1/projects/{id}/scenes/{scene_id}/generate-visual
Payload: { visual_type: "video", prompt: "...", provider: "animatediff", expected_revision: N }
       │
       ▼
[ Queue Resolution: JobService.resolve_job_queue ]
  ├── Routes provider="animatediff" ──► `gpu_ai` queue
       │
       ▼
[ Worker Task: ai_tasks.py: _execute_generate_scene_visual ]
  └── Calls SceneVisualsOrchestrator.generate_scene_visual
       │
       ▼
[ Provider Resolution: AIRegistry.get_video_provider("animatediff") ]
  ├── CPU host ──► Raises AIRuntimeUnavailableException(code="GPU_UNAVAILABLE")
  └── CUDA host ──► Returns AnimateDiffVideoProvider instance
       │
       ▼
[ Banned Artifact Guard: validate_artifact_not_banned ]
  └── Blocks modelscope, zeroscope (raises AI_BANNED_NON_COMMERCIAL_ARTIFACT)
       │
       ▼
[ Neural Synthesis: AnimateDiffPipeline (CUDA, fp16) ]
  ├── Loads weights from pre-staged `models_cache`
  ├── Disables safety checker (`safety_checker=None`) to prevent hidden downloads
  └── Synthesizes 16 frames @ 8 fps, encoded to H.264 MP4 via FFmpeg
       │
       ▼
[ Video Container Validation: FFprobeService.probe ]
  └── Verifies valid MP4 container, non-zero duration, valid dimensions
       │
       ▼
[ Asset Persistence: AssetLifecycleManager.ingest_generated_asset ]
  ├── Ingests MP4 into MinIO bucket `heyzen-assets`
  └── Inserts `Asset` record (asset_type="video", mime_type="video/mp4")
       │
       ▼
[ Scene Document Update & OCC Version Commit ]
  ├── target_scene.background = { "type": "video", "asset_id": asset.id, ... }
  └── ProjectService.create_version(..., expected_revision=N)
        └── Raises ConflictException(code="CONCURRENCY_CONFLICT") if concurrent edit
```

---

## 8. Database & Frontend Invariants

- **Database Migrations:** **ZERO migrations**. Alembic migration head remains `0005_jobs_task_pipeline`.
- **Frontend Changes:** **ZERO changes**. Frontend UI is completely frozen (`src/**`, `public/**` untouched).

---

## 9. Test Plan (Automated Suite Specification)

When implemented, the test suite [`backend/tests/test_ai_video_gen.py`](file:///d:/HeyGen/video-ai-tools/backend/tests/test_ai_video_gen.py) and [`backend/tests/test_scene_visuals.py`](file:///d:/HeyGen/video-ai-tools/backend/tests/test_scene_visuals.py) will cover:

1. `test_animatediff_descriptor`: Validates metadata (`capability="video"`, `runtime="diffusers-cuda"`, `requires_gpu=True`, `supported_devices=["cuda"]`).
2. `test_animatediff_banned_components`: Proves active rejection of `modelscope` and `zeroscope` (`AIModelSecurityException`).
3. `test_animatediff_cpu_refusal`: Asserts strict `GPU_UNAVAILABLE` exception on CPU hosts with no mock fallback.
4. `test_animatediff_registry_resolution`: Validates real-mode vs mock-mode resolution in `AIRegistry`.
5. `test_animatediff_catalog_entry`: Confirms `model_registry` contains `video/animatediff-v1-5-gpu` with `CONDITIONAL — ARTIFACT VERIFICATION REQUIRED`.
6. `test_ffprobe_video_validation`: Tests valid MP4 container vs corrupt payload verification.
7. `test_job_service_routes_video_gen_to_proper_queue`: Asserts `animatediff` routes to `gpu_ai`.
8. `test_generate_scene_visual_video_occ_conflict`: Verifies `CONCURRENCY_CONFLICT` handling on stale versions.
9. `test_generate_scene_visual_video_real_mode_cpu_guard`: Asserts real-mode API halts with `GPU_UNAVAILABLE` on CPU.
10. Full backend regression pass (382+ tests maintained).

---

## 10. Audit Summary & Formal Conclusion

### Audit Findings Matrix:
- **Motion Adapter License Evidence:** **ABSENT**. Upstream repository `guoyww/animatediff-motion-adapter-v1-5-2` contains no `LICENSE` file and no `license:` metadata tag.
- **Base Model License Evidence:** **PRESENT & VERIFIED**. Stable Diffusion v1.5 is licensed under CreativeML OpenRAIL-M (commercial use authorized under Section 5).
- **Training Data Provenance:** **PROBLEMATIC**. AnimateDiff motion modules were trained on WebVid-10M (Shutterstock scrapes), restricted to non-commercial academic research and withdrawn following copyright claims.
- **Hidden Downloads:** **IDENTIFIED & MITIGATED**. `AnimateDiffPipeline` automatically downloads 1.22 GB `CompVis/stable-diffusion-safety-checker` unless explicitly disabled with `safety_checker=None`.
- **Commercial Classification:** **`CONDITIONAL — ARTIFACT VERIFICATION REQUIRED` (BLOCKED)**.

### Remaining Blocker:
> **BLOCKER:**  
> **"AnimateDiff motion-adapter artifact license cannot currently be established with sufficient confidence for HeyZen's production/commercial-use policy."**

### Final Determination:

**IMPLEMENTATION BLOCKED — LICENSE/ARTIFACT VERIFICATION REQUIRED**
