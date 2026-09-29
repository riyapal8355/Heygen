# Phase 8 — Step 5 Implementation Plan & Architectural Recommendation
## Autonomous AI Video Agent & Structured Script Generation Engine

**Document Status:** DRAFT FOR USER REVIEW (PLANNING ONLY)  
**Target Repository:** `D:\HeyGen\video-ai-tools`  
**Target File:** `docs/phase-8-step-5-plan.md`  
**Host Target:** Windows 11 | AMD Ryzen 5 5500U (12 vCPUs) | 7.34 GB RAM (~0.85 GB Available) | AMD Radeon Integrated Graphics | No CUDA  
**Production Target:** Linux / Windows Server | NVIDIA CUDA Worker (>= 16 GB VRAM)  
**Current Phase:** Phase 8 (Self-Hosted AI/Media Capabilities), Step 5 Planning  

---

## 1. Existing HeyZen State

HeyZen is a self-hosted, vendor-independent AI video creation platform providing a complete HeyGen-like workflow. The repository consists of two strictly decoupled components:

1. **Canonical Frontend (`src/`, `public/`)**:
   - **Framework**: Next.js 16.3.4 (App Router), React 19.2.8, Tailwind CSS 4, TypeScript.
   - **Status**: Canonical, fully operational, and **100% UNTOUCHED**.
   - **Contract**: The backend adapts strictly around the frontend’s REST, SSE, and asset contracts without requiring any frontend code changes.

2. **Backend Engine (`backend/app/`)**:
   - **Framework**: FastAPI (async Python 3.13), SQLAlchemy 2.0 (asyncpg), PostgreSQL 16 (Docker).
   - **Job / Worker Pipeline**: Redis 7, Celery 5.6.3 with dedicated Multi-Queue Topology (`cpu_media`, `gpu_ai`, `maintenance`).
   - **Object Storage**: MinIO / S3 tenant-isolated asset storage (`app.storage.s3`).
   - **Domain & Document Model**: Canonical `ProjectDocumentV1` (JSONB), immutable `ProjectVersion` history, and strict Optimistic Concurrency Control (OCC) using sequential `revision` numbers.
   - **Media Engine**: Subprocess-isolated FFmpeg and FFprobe pipeline (`app.media`) capable of broadcast-grade timeline composition, loudness normalization, audio mixing, and format validation.
   - **AI Architecture**: Strict vendor-independent abstraction layer (`app.ai`) decoupling contracts, registries, lifecycle, runtime selection, and hardware detection from specific neural inference engines.

---

## 2. Completed Phase 8 Steps

The repository has successfully implemented, tested, and accepted Steps 1 through 4 of Phase 8:

- **Step 1 — AI Runtime Foundation**:
  - Hardware detection engine (`app.ai.hardware`) with safe, non-crashing CPU/CUDA/VRAM/RAM detection across Windows, Linux, and Docker.
  - Model and provider registries (`app.ai.model_registry`, `app.ai.registry`) managing declarative capability metadata, hardware requirements, and licensing constraints.
  - Deterministic runtime selection (`app.ai.selection`) enforcing strict compatibility matching.
  - Strict real-mode enforcement: `AI_PROVIDER_MODE="real"` raises structured exceptions (`AIRuntimeUnavailableException`, `AIModelIncompatibleException`, `GPU_UNAVAILABLE`) and **never** falls back silently to mock.

- **Step 2 — Real Self-Hosted TTS (Text-to-Speech)**:
  - Neural engine: **Piper ONNX** (`en_US-lessac-medium`).
  - License: MIT / Public Domain (`COMMERCIAL_SAFE`).
  - Validation: 100% real CPU neural inference generating 24 kHz WAV audio, ingested into MinIO, integrated into multi-scene project speech orchestration, with OCC versioning and Celery async execution.

- **Step 3 — Real Self-Hosted ASR (Automatic Speech Recognition)**:
  - Neural engine: **faster-whisper** (`Systran/faster-whisper-tiny` via CTranslate2 int8).
  - License: MIT (`COMMERCIAL_SAFE`).
  - Validation: Real CPU neural transcription producing timestamped sentence and word subtitle cues. Closed-loop verification (Piper WAV -> Whisper ASR). Subtitles stored strictly on `Scene.subtitles` without overloading visual `SceneLayer` semantics.

- **Step 4 — Real Local CPU Lip-Sync & CUDA Architecture**:
  - Local CPU Prototyping Engine: **Wav2Lip-ONNX** (`instant-high/wav2lip-onnx`).
  - License: **`RESEARCH_ONLY` (Non-Commercial)** due to LRS2 training dataset licensing constraints. Explicitly isolated and classified as research-only.
  - Local CPU Validation: Real CPU neural lip-sync inference on AMD Ryzen 5 5500U producing 52-frame (2.08s) 25 fps MP4 avatar video in 6.18s (~8.4 fps), validated by FFprobe, stored in MinIO, bound to `SceneAvatar.video_asset_id`, committed under OCC revision control, with Celery worker routing (`gpu_ai` / `cpu_media`).
  - Production CUDA Target: **MuseTalk** (`TMElyralab/MuseTalk`, MIT). Architecturally prepared as `production_target_cuda_unvalidated`, raising structured `GPU_UNAVAILABLE` on CPU with zero mock fallback. No PyTorch or CUDA dependencies were installed on the host.

---

## 3. Non-Negotiable Architectural Rules

Any Step 5 implementation must adhere strictly to these non-negotiable principles:

1. **Frontend Untouched**: Absolutely zero edits to `src/`, `public/`, `package.json`, Tailwind styles, or React components.
2. **Zero Database Migrations**: All state must fit within the existing PostgreSQL tables (`projects`, `project_versions`, `assets`, `jobs`, `workspaces`, `users`) and the JSONB `ProjectDocumentV1` schema.
3. **ProjectDocumentV1 Canonical Representation**: Projects remain structured timelines, never flattened prematurely to MP4 files.
4. **SceneLayer Semantics Preserved**: `SceneLayer` represents visual timeline layers (text, image, video, shape). Non-visual metadata or actor definitions must use dedicated top-level fields on `Scene`.
5. **Strict Real Mode (No Silent Mock Fallback)**: Under `AI_PROVIDER_MODE="real"`, any missing dependency, missing weights file, or incompatible hardware must immediately raise a structured error (e.g., `AIRuntimeUnavailableException`, `AIModelIncompatibleException`). Mock output is forbidden in real mode.
6. **Asynchronous Celery Architecture**: Heavy operations must be asynchronous via FastAPI -> Celery (`cpu_media` or `gpu_ai` queue) -> MinIO -> OCC `ProjectVersion`. Synchronous execution is reserved exclusively for lightweight tests.
7. **Storage in MinIO/S3**: All generated artifacts belong in MinIO and must be tracked via the workspace-scoped `Asset` model.
8. **Rigorous License Audit**: Every proposed model, codebase, training dataset, and bundled detector must be independently audited and classified as `COMMERCIAL_SAFE`, `RESEARCH_ONLY`, or `LICENSE_REQUIRES_REVIEW`.

---

## 4. Current Codebase Inspection Report

A comprehensive inspection of the actual codebase was performed:

| Path / Module | Current Implementation Status | Key Observations & Constraints |
| :--- | :--- | :--- |
| `backend/app/ai/interfaces.py` | Defines `LLMProvider`, `TTSProvider`, `ASRProvider`, `TranslationProvider`, `AvatarProvider`, `ImageProvider`, `VideoProvider`. | `LLMProvider` defines `generate_script(prompt, system_prompt, context) -> ScriptGenerationResult` and `stream_script(...)`. |
| `backend/app/ai/contracts.py` | Strongly typed Pydantic V2 execution contracts for all modalities. | Currently includes `TTSContractRequest`, `ASRContractRequest`, `TranslationContractRequest`, `LipSyncContractRequest`, `ImageGenContractRequest`, `VideoGenContractRequest`, `VideoRenderContractRequest`. |
| `backend/app/ai/registry.py` | Central `AIProviderRegistry` managing providers and `ProviderDescriptor`. | `AICapability` enum defines `LLM`, `TTS`, `ASR`, `TRANSLATION`, `AVATAR`, `IMAGE`, `VIDEO`. Auto-registers real `PiperTTSProvider`, `WhisperASRProvider`, `Wav2LipONNXAvatarProvider`, `MuseTalkAvatarProvider`. `LLM`, `TRANSLATION`, `IMAGE`, `VIDEO` currently default to `mock`. |
| `backend/app/ai/model_registry.py` | Central `ModelRegistry` tracking model requirements, licensing, and installation. | Already catalogs `tts/piper-en-lessac`, `asr/whisper-tiny-cpu`, `avatar/wav2lip-cpu`, `avatar/musetalk-gpu`, `llm/llama-3.2-3b-cpu`, `translation/nllb-200-cpu`, `image/sdxl-turbo-gpu`. |
| `backend/app/ai/hardware.py` | Detects CPU, RAM, GPU, VRAM, and CUDA status without failing. | Live host reading: AMD Ryzen 5 5500U (12 vCPUs), Total RAM 7.34 GB, **Available RAM: ~0.85 GB**, GPU AMD Radeon Graphics, `cuda_available: False`. |
| `backend/app/ai/selection.py` | Resolves `Capability -> Provider -> Model -> Runtime -> Device`. | Strict real mode rejects mock models when real mode is configured and raises explicit `AIRuntimeUnavailableException` if hardware is insufficient. |
| `backend/app/services/video_agent_service.py` | Implements prompt-to-project decomposition into `ProjectDocumentV1`. | Currently calls `self.ai_registry.get_llm_provider()`, which returns `MockLLMProvider`. Generates mock multi-scene documents. |
| `backend/app/services/project_localization_service.py` | Implements multi-scene script translation with brand glossaries. | Calls `MockTranslationProvider`. Replaces script text with mock prefixes. |
| `backend/app/services/scene_visuals_service.py` | Generates scene visuals (background images or b-roll videos). | Calls `MockImageProvider` / `MockVideoProvider` and writes synthetic PNG/MP4 fixtures (`create_valid_mock_png_fixture`). |
| `backend/app/media/compositor.py` | Real FFmpeg timeline compositor rendering multi-scene MP4 videos. | Assembles scenes, handles solid color/image/video backgrounds, drawtext captions, audio padding, and background music mixing. Currently lacks transparent avatar overlay compositing. |
| `backend/app/api/v1/endpoints/project_orchestration.py` | Exposes REST orchestration endpoints. | `POST /generate` (Video Agent), `POST /{id}/synthesize-speech` (TTS), `POST /{id}/transcribe` (ASR), `POST /{id}/generate-avatar-video` (Lip-sync), `POST /{id}/translate` (Translation), `POST /{id}/scenes/{id}/generate-visual` (Visuals), `POST /{id}/render` (Export). |
| `backend/app/workers/tasks/ai_tasks.py` | Celery AI tasks on `gpu_ai` / `cpu_media` queues. | Tasks implemented: `tts_synthesis`, `lip_sync`, `project_batch_speech`, `generate_scene_visual`, `asr_transcription`, `translate_project`, `voice_clone`, `avatar_train`. |
| `backend/.venv` Installed Packages | Inspected active virtual environment dependencies. | **Critical Discovery**: `onnxruntime-genai==0.16.0`, `onnxruntime==1.30.0`, `ctranslate2==4.8.2`, `tokenizers==0.23.2`, `opencv-python-headless==5.0.0.93`, and `piper-tts==1.8.0` are **ALREADY INSTALLED**. |

---

## 5. Determine What Step 5 Should Be

### The Architectural Mission of Step 5
In Phase 8 Steps 2, 3, and 4, HeyZen solved the downstream media generation pipeline:
- Spoken audio can be synthesized from text using neural TTS (Piper).
- Narration audio can be transcribed into timestamped subtitle cues (Whisper).
- Avatar video portraits can be animated to speak with neural lip-sync (Wav2Lip-ONNX).
- The timeline compositor can assemble these elements into a final video (FFmpeg).

**However, the platform currently suffers from a glaring upstream bottleneck:**
When a user visits the HeyZen frontend and clicks **"Generate Video with AI"** (`POST /workspaces/{id}/projects/generate`), the backend invokes `MockLLMProvider`. The user receives a hardcoded, static mock script with dummy scene breakdowns!

In a true HeyGen-like platform, the **AI Video Agent** is the primary creation engine. It converts high-level natural language prompts into:
1. Multi-scene dramatic narrative structure.
2. Character/Avatar selection and positioning.
3. Voice actor selection, speech pacing, and spoken script per scene.
4. Scene visual descriptions and background styling.
5. Calculated scene durations and timeline sequencing.

Once the Video Agent generates real scenes, Steps 2, 3, and 4 immediately process those scenes into real speech, real subtitles, and real avatar video. **Implementing a real, self-hosted AI Video Agent completes the entire end-to-end autonomous video creation loop.**

---

## 6. Comprehensive Candidate Evaluation

We systematically evaluated five candidate capabilities against the existing architecture and hardware boundary:

```
+-------------------------------------------------------------------------------------------------------+
|                                    Phase 8 Step 5 Candidate Matrix                                   |
+-------------------+--------------------+------------------------+-------------------+-----------------+
| Candidate         | Modality           | Host RAM Requirement   | Licensing Status  | Primary Status  |
+-------------------+--------------------+------------------------+-------------------+-----------------+
| 1. Video Agent    | SLM / LLM          | ~500 MB (0.5B ONNX)    | COMMERCIAL_SAFE   | RECOMMENDED     |
| 2. Translation    | Seq2Seq Neural MT  | ~220 MB (CTranslate2)  | COMMERCIAL_SAFE   | Secondary       |
| 3. Avatar Matting | Alpha Segmentation | ~180 MB (ONNX MODNet)  | COMMERCIAL_SAFE   | Media Extension |
| 4. Scene Visuals  | Diffusion (SD/SDXL)| 4.5 GB - 8.0 GB        | COMMERCIAL_SAFE   | CUDA-Only (OOM) |
| 5. Voice Cloning  | Zero-Shot TTS      | 3.5 GB - 5.0 GB        | RESEARCH_ONLY     | CUDA-Only (OOM) |
+-------------------+--------------------+------------------------+-------------------+-----------------+
```

---

### Candidate 1: Real AI Video Agent & Script Generation (RECOMMENDED)

- **Capability**: Decomposes natural language prompts (e.g. *"Create a 3-scene product launch video for an AI developer assistant"*) into structured `ProjectDocumentV1` scenes with genuine spoken narration scripts, background styles, avatar framing, and timing.
- **Existing Architecture Fit**: Direct drop-in for `VideoAgentService` (`backend/app/services/video_agent_service.py`), replacing `MockLLMProvider`. Integrates with `POST /workspaces/{id}/projects/generate`.
- **Open-Source Implementation**:
  - **Host CPU Engine**: `Qwen/Qwen2.5-0.5B-Instruct-ONNX` (or int4 quantized GGUF) executed via `onnxruntime-genai` (which is **already installed** in `.venv`!).
  - **Future CUDA Target**: `Qwen/Qwen2.5-7B-Instruct` or `meta-llama/Llama-3.3-70B-Instruct` deployed via vLLM or Ollama on a GPU worker.
- **License Audit**:
  - Code: Apache 2.0.
  - Model Weights: Apache 2.0.
  - Training Data: Permissive web crawl + synthesized datasets without non-commercial restrictions.
  - Commercial Classification: **`COMMERCIAL_SAFE`**.
- **Hardware Feasibility**:
  - Model Disk Footprint: ~380 MB.
  - Peak Runtime RAM: **~520 MB** (including KV cache for 1024 context window).
  - Current Host Free RAM: **~0.85 GB available**. Fits safely with ~330 MB safety headroom.
  - CPU Inference Speed: ~25-35 tokens/sec on AMD Ryzen 5 5500U (12 threads). A full 3-scene script (250 tokens) generates in **7 to 10 seconds**.
- **Integration Complexity**: Low/Medium. Reuses existing `LLMProvider` protocol, `GenerateProjectRequest`, and `VideoAgentService`.
- **Storage**: Generates structured JSON document; does not generate binary blobs directly into MinIO (downstream TTS/lip-sync generates binary assets).
- **ProjectDocumentV1 Fit**: 100% native. Populates `doc.scenes`, `scene.speech.script`, `scene.avatar`, and `doc.settings`.
- **Job System**: Executed via Celery task `heyzen.tasks.ai.generate_project` on `cpu_media` queue (or `gpu_ai` for 7B CUDA target).
- **API**: `POST /workspaces/{workspace_id}/projects/generate` (already exists, currently mock).
- **Failure Modes**: Prompt rejection, JSON formatting error, token budget overflow, model download failure, memory pressure. Handled via structured JSON schema parsing with fallback recovery.
- **Testing**: Deterministic seed unit tests, prompt-to-schema validation, OCC verification, and regression tests.

---

### Candidate 2: Real Neural Project Localization & Script Translation

- **Capability**: Translates existing multi-scene project scripts into foreign languages (Spanish, French, German, Japanese, etc.) with brand glossary enforcement.
- **Existing Architecture Fit**: Replaces `MockTranslationProvider` in `ProjectLocalizationService` (`POST /workspaces/{id}/projects/{id}/translate`).
- **Open-Source Implementation**:
  - **Host CPU Engine**: `Helsinki-NLP/Opus-MT` models converted to CTranslate2 int8, executed via `ctranslate2` (which is **already installed** in `.venv`!).
  - **Future CUDA Target**: `facebook/nllb-200-3.3B` or `SeamlessM4T-v2` on GPU worker.
- **License Audit**:
  - Opus-MT: CC-BY-4.0 (Model) / MIT (Code). **`COMMERCIAL_SAFE`**.
  - Meta NLLB-200: CC-BY-NC-4.0. **`RESEARCH_ONLY` (Non-Commercial)**.
- **Hardware Feasibility**:
  - Model Disk Footprint: ~85 MB - 130 MB per language pair.
  - Peak Runtime RAM: **~220 MB**.
  - Latency: ~80 ms per scene script on CPU.
- **Why Secondary**: While technically trivial and lightweight, translation is a downstream post-processing capability. It does not solve the core creation gap where new projects are generated from prompts with dummy text.

---

### Candidate 3: Avatar Background Removal & Alpha Matting (MODNet / BiRefNet)

- **Capability**: Removes background from avatar portrait plates to produce transparent alpha PNGs or green-screen backgrounds, enabling avatars to overlay cleanly on top of custom scene images/videos.
- **Existing Architecture Fit**: Fits inside `AvatarService` and `TimelineCompositor`.
- **Open-Source Implementation**:
  - **Host CPU Engine**: `MODNet-ONNX` (~25 MB) executed via `onnxruntime` (already installed).
  - **Future CUDA Target**: `ZhengPeng7/BiRefNet` or `briaai/RMBG-1.4`.
- **License Audit**:
  - MODNet: Apache 2.0 (**`COMMERCIAL_SAFE`**).
  - RMBG-1.4: BRIA Non-Commercial (**`RESEARCH_ONLY`**).
- **Hardware Feasibility**: Model disk ~25 MB, RAM ~180 MB, inference latency ~40 ms on CPU.
- **Why Secondary**: Background removal is a visual pre-processing utility rather than a standalone platform capability in `AICapability` enum (`LLM`, `TTS`, `ASR`, `AVATAR`, `IMAGE`, `VIDEO`). It is best implemented as an enhancement to the media pipeline or alongside avatar digital twin authoring.

---

### Candidate 4: Real Generative Scene Visuals & Background Plates (Stable Diffusion)

- **Capability**: Generates AI background plates or b-roll imagery from text prompts (`POST /workspaces/{id}/projects/{id}/scenes/{id}/generate-visual`).
- **Existing Architecture Fit**: Fits `SceneVisualsOrchestrator` and `ImageProvider` protocol.
- **Open-Source Implementation**:
  - **Host CPU Engine**: SD-1.5 ONNX / OpenVINO.
  - **Future CUDA Target**: `stabilityai/sdxl-turbo` or `black-forest-labs/FLUX.1-schnell`.
- **License Audit**:
  - SD-1.5: CreativeML Open RAIL-M (**`COMMERCIAL_SAFE`** with standard RAIL restrictions).
  - SDXL-Turbo: Stability AI Non-Commercial License (**`RESEARCH_ONLY`**).
  - FLUX.1-schnell: Apache 2.0 (**`COMMERCIAL_SAFE`**).
- **Hardware Feasibility**:
  - **CRITICAL FAILURE ON CURRENT HOST**: SD-1.5 on CPU requires 4.5 GB to 6.0 GB of RAM during unet diffusion step execution.
  - Current host has **only ~0.85 GB available RAM**.
  - Attempting to run Stable Diffusion on this CPU host will trigger immediate OS thrashing, memory exhaustion (OOM), or crash the development server.
  - CPU latency is 45 to 120 seconds per 512x512 image.
- **Verdict**: **NOT FEASIBLE ON CURRENT CPU HOST**. Must be architecturally designed as a CUDA-only capability.

---

### Candidate 5: Real Zero-Shot Voice Cloning

- **Capability**: Clones user voices from 5-15 seconds of reference audio for personalized TTS.
- **Existing Architecture Fit**: Fits `TTSProvider.clone_voice` and `VoiceService`.
- **Open-Source Implementation**: Coqui XTTS-v2 or OpenVoice v2.
- **License Audit**:
  - Coqui XTTS-v2: Coqui Public Model License (CPML) — strictly non-commercial (**`RESEARCH_ONLY`**).
  - OpenVoice v2: Creative Commons Attribution-NonCommercial 4.0 (**`RESEARCH_ONLY`**).
- **Hardware Feasibility**: Requires PyTorch, torchaudio, and ~3.5 GB RAM. Exceeds available RAM (0.85 GB).
- **Verdict**: **NOT FEASIBLE ON CURRENT CPU HOST**.

---

## 7. Hardware Constraint & Memory Budget Analysis

### Host Hardware Snapshot
```
Processor: AMD Ryzen 5 5500U with Radeon Graphics (6 Cores, 12 Logical Threads)
Host Total Physical RAM: 7.34 GB (7,881,588,736 bytes)
Current Available RAM:   ~0.85 GB (892,342,272 bytes)
Dedicated VRAM:          0 MB (Shared System RAM only)
GPU Vendor:              AMD (Radeon Integrated Graphics)
CUDA Operational:        False (NVIDIA CUDA Unavailable)
```

### Strict Memory Budget for Candidate 1 (Qwen 2.5 0.5B ONNX)
```
+-----------------------------------------------------------------------------------+
|                        Host Memory Allocation Breakdown                           |
+-----------------------------------+-----------------------------------------------+
| System / Docker / Postgres / Redis| 6.49 GB (Active OS & Container Baseline)      |
| Available Physical Headroom       | 0.85 GB (850 MB)                              |
+-----------------------------------+-----------------------------------------------+
| Planned Step 5 Model Budget       |                                               |
| - Qwen 2.5 0.5B Weights (int4)    | ~350 MB                                       |
| - Runtime Context & KV Cache      | ~120 MB (1024 tokens)                         |
| - Tokenizer & Buffer Workspace    | ~50 MB                                        |
| Total Step 5 Peak RAM Footprint   | ~520 MB                                       |
+-----------------------------------+-----------------------------------------------+
| Remaining Safety Headroom         | ~330 MB (Buffer to prevent OOM/swapping)      |
+-----------------------------------+-----------------------------------------------+
```

### CUDA Worker Requirements (Future Production Architecture)
- **Target GPU**: NVIDIA RTX 3090, 4090, or A10G / L4 (>= 16 GB VRAM).
- **GPU Software Stack**: CUDA 12.4+, cuDNN 9+, vLLM 0.6+ or Ollama.
- **Target Model**: `Qwen/Qwen2.5-7B-Instruct` or `meta-llama/Llama-3.3-70B-Instruct-AWQ`.
- **Target Latency**: 80-120 tokens/sec.
- **Queue**: Celery direct routing to `gpu_ai`.

---

## 8. License Safety Audit & Matrix

Every component proposed for Step 5 has been audited against commercial and redistribution criteria:

| Component / Model | Code License | Checkpoint License | Training Data Status | Bundled Sub-models | Permitted Use | Classification |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Qwen 2.5 0.5B Instruct** | Apache 2.0 | Apache 2.0 | Synthesized + Permissive Public Web | Tokenizer (BPE, Apache 2.0) | Full Commercial Self-Hosting | **`COMMERCIAL_SAFE`** |
| **Qwen 2.5 7B Instruct (CUDA Target)** | Apache 2.0 | Apache 2.0 | Permissive Web + Synthetic Multi-lingual | Tokenizer (BPE, Apache 2.0) | Full Commercial Self-Hosting | **`COMMERCIAL_SAFE`** |
| **onnxruntime-genai 0.16.0** | MIT | N/A (Engine) | N/A | DirectML / CPU Providers | Commercial Redistribution | **`COMMERCIAL_SAFE`** |
| **Helsinki-NLP Opus-MT** | Apache 2.0 | CC-BY-4.0 | OPUS Multi-lingual Corpus | SentencePiece (Apache 2.0) | Commercial with Attribution | **`COMMERCIAL_SAFE`** |
| **Meta NLLB-200** | MIT | CC-BY-NC-4.0 | CCMatrix / Paracrawl (Filtered) | SentencePiece | Non-Commercial Research Only | **`RESEARCH_ONLY`** |
| **Wav2Lip-ONNX (Step 4)** | MIT | Academic | LRS2 Dataset Non-Commercial | Face Detection (S3FD) | Non-Commercial Research Only | **`RESEARCH_ONLY`** |
| **MuseTalk (Step 4 CUDA Target)** | MIT | MIT | Open Human Datasets | DWPose / Whisper / VAE | Commercial Self-Hosting | **`COMMERCIAL_SAFE`** |
| **SDXL-Turbo** | Apache 2.0 | Non-Commercial | Stability Internal + LAION | Autoencoder / CLIP | Research Only | **`RESEARCH_ONLY`** |

**Conclusion**: The recommended capability (Qwen 2.5 0.5B Instruct via ONNX) is **100% `COMMERCIAL_SAFE`** with zero non-commercial or research-only viral clauses.

---

## 9. Provider Architecture

Step 5 integrates directly into the existing provider architecture without creating duplicate abstractions:

```
+-----------------------------------------------------------------------------------+
|                        HeyZen AI Provider Architecture (Step 5)                   |
|                                                                                   |
|   +---------------------------------------------------------------------------+   |
|   | AICapability.LLM                                                          |   |
|   +---------------------------------------------------------------------------+   |
|         |                                                           |             |
|         v                                                           v             |
|   +--------------------------+                                +---------------+   |
|   | RealQwenLLMProvider      |                                | MockLLMProvider|  |
|   | (CPU Local SLM)          |                                | (Test Default)|  |
|   +--------------------------+                                +---------------+   |
|         |                                                                         |
|         v                                                                         |
|   +---------------------------------------------------------------------------+   |
|   | ModelDescriptor: "llm/qwen-2.5-0.5b-cpu"                                  |   |
|   | - Provider: "qwen"                                                        |   |
|   | - Runtime: "local_cpu" (onnxruntime-genai)                                |   |
|   | - License: "Apache-2.0" (COMMERCIAL_SAFE)                                 |   |
|   | - Memory: 520 MB peak RAM                                                 |   |
|   +---------------------------------------------------------------------------+   |
|         |                                                                         |
|         v                                                                         |
|   +---------------------------------------------------------------------------+   |
|   | ModelDescriptor: "llm/qwen-2.5-7b-gpu" (Production CUDA Target)           |   |
|   | - Provider: "qwen"                                                        |   |
|   | - Runtime: "local_gpu" (vLLM / PyTorch CUDA)                              |   |
|   | - Status: "production_target_cuda_unvalidated"                            |   |
|   +---------------------------------------------------------------------------+   |
+-----------------------------------------------------------------------------------+
```

### 1. Provider Class: `RealQwenLLMProvider`
- File: `backend/app/ai/adapters/qwen.py` [NEW]
- Satisfies Protocol: `LLMProvider` (`app.ai.interfaces.LLMProvider`).
- Implements:
  ```python
  async def generate_script(
      self,
      prompt: str,
      system_prompt: Optional[str] = None,
      context: Optional[Dict[str, Any]] = None,
  ) -> ScriptGenerationResult: ...
  
  async def stream_script(
      self,
      prompt: str,
      system_prompt: Optional[str] = None,
      context: Optional[Dict[str, Any]] = None,
  ) -> AsyncGenerator[str, None]: ...
  ```

### 2. Execution Contract: `LLMContractRequest` & `LLMContractResult`
- File: `backend/app/ai/contracts.py` [MODIFY]
- Strongly typed execution models:
  ```python
  class LLMContractRequest(AIContractRequest):
      prompt: str = Field(..., min_length=1, max_length=5000)
      system_prompt: Optional[str] = Field(None, max_length=2000)
      target_scenes: int = Field(3, ge=1, le=10)
      target_duration_seconds: float = Field(30.0, ge=5.0, le=300.0)
      video_tone: str = Field("professional", description="professional, casual, dramatic, energetic")
      aspect_ratio: str = Field("16:9")
      temperature: float = Field(0.7, ge=0.0, le=2.0)
      max_new_tokens: int = Field(512, ge=64, le=2048)

  class LLMContractResult(AIContractResult):
      title: str
      script: str
      suggested_scenes: List[Dict[str, Any]] = Field(default_factory=list)
      prompt_tokens: int = 0
      completion_tokens: int = 0
      generation_latency: float = 0.0
  ```

### 3. Registry Registration: `app.ai.registry`
- In `_bootstrap_default_mock_providers(registry)`:
  ```python
  try:
      from app.ai.adapters.qwen import RealQwenLLMProvider
      settings = get_settings()
      qwen_default = (settings.AI_PROVIDER_MODE == "real" or getattr(settings, "DEFAULT_LLM_PROVIDER", "qwen") == "qwen")
      registry.register(AICapability.LLM, "qwen", RealQwenLLMProvider(), is_default=qwen_default)
  except Exception as exc:
      logger.warning("Could not auto-register RealQwenLLMProvider: %s", exc)
  ```

### 4. Model Catalog Registration: `app.ai.model_registry`
- Register `llm/qwen-2.5-0.5b-cpu`:
  - `capability`: `"llm"`
  - `provider`: `"qwen"`
  - `supported_runtimes`: `["local_cpu"]`
  - `supported_devices`: `["cpu"]`
  - `requires_gpu`: `False`
  - `minimum_ram_bytes`: `512 * 1024 * 1024` (512 MB)
  - `approximate_size_bytes`: `398 * 1024 * 1024` (398 MB)
  - `license`: `"Apache-2.0"`
  - `license_commercial_permitted`: `True`
  - `metadata`: `{"license_classification": "COMMERCIAL_SAFE", "engine": "onnxruntime-genai"}`
- Register `llm/qwen-2.5-7b-gpu`:
  - `capability`: `"llm"`
  - `provider`: `"qwen"`
  - `supported_runtimes`: `["local_gpu"]`
  - `supported_devices`: `["cuda"]`
  - `requires_gpu`: `True`
  - `minimum_vram_bytes`: `8 * 1024 * 1024 * 1024` (8 GB)
  - `license`: `"Apache-2.0"`
  - `metadata`: `{"status": "production_target_cuda_unvalidated", "license_classification": "COMMERCIAL_SAFE"}`

---

## 10. Celery Asynchronous Job Design

Large language model inference can take 5 to 15 seconds on CPU. To maintain responsiveness, the Video Agent pipeline is designed as an asynchronous background job with cooperative cancellation and observable progress tracking.

### 1. Job Type & Routing
- **Job Type**: `generate_project`
- **Celery Task**: `heyzen.tasks.ai.generate_project`
- **Queue**: `cpu_media` for CPU SLM; `gpu_ai` for 7B CUDA target.
- **Routing Key**: Matches queue name directly.

### 2. Task Payload
```json
{
  "prompt": "Create an introductory 3-scene video welcoming new users to HeyZen.",
  "target_duration_seconds": 30.0,
  "video_tone": "professional",
  "aspect_ratio": "16:9",
  "avatar_id": "00000000-0000-0000-0000-000000000001",
  "voice_id": "en_US-lessac-medium",
  "auto_synthesize_speech": true,
  "provider": "qwen",
  "device": "cpu"
}
```

### 3. Observable Progress Stages
```
+-------------------------------------------------------------------------------+
| Progress Percent | Stage                      | Message                       |
+------------------+----------------------------+-------------------------------+
| 0%               | queued                     | Job submitted to queue        |
| 10%              | loading_model              | Initializing SLM engine       |
| 25%              | decomposing_prompt         | Generating structured script  |
| 70%              | structuring_scenes         | Parsing timeline scenes       |
| 85%              | creating_project_version   | Committing initial ProjectDoc |
| 100%             | completed                  | Video project ready           |
+-------------------------------------------------------------------------------+
```

### 4. Cooperative Cancellation Points
The worker checks `job.status == "cancelled"` at three checkpoints:
1. Immediately upon task execution before model invocation.
2. After SLM token generation completes, before creating database records.
3. Before committing the initial `ProjectVersion`.

### 5. Idempotency & Retries
- Supports optional `idempotency_key` via `JobService.submit_job`.
- Max retries: 2, default retry delay: 10 seconds.
- Transient errors (model loading timeout) retry; deterministic validation errors fail immediately.

---

## 11. Project Integration: ProjectDocumentV1

Step 5 strictly preserves `ProjectDocumentV1` schema semantics. Zero database migrations are needed.

### Structured Prompt Decomposition
The LLM decomposes user prompts into a structured JSON payload:
```json
{
  "title": "Welcome to HeyZen",
  "suggested_scenes": [
    {
      "sequence": 1,
      "duration": 7.0,
      "heading": "Welcome to HeyZen",
      "text": "Welcome to HeyZen. Create stunning studio-grade AI videos from simple text in seconds.",
      "visual_description": "Clean modern gradient backdrop with avatar centered."
    },
    {
      "sequence": 2,
      "duration": 8.0,
      "heading": "Powerful AI Avatars",
      "text": "Choose from dozens of neural avatars and voices, with instant lip-sync and automatic subtitles.",
      "visual_description": "Subtle feature highlight graphics."
    },
    {
      "sequence": 3,
      "duration": 5.0,
      "heading": "Get Started Today",
      "text": "Ready to bring your ideas to life? Start creating your first project right now.",
      "visual_description": "Call to action card."
    }
  ]
}
```

### ProjectDocumentV1 JSON Structure (Before and After)

#### BEFORE (Static Mock Generation)
```json
{
  "schema_version": 1,
  "settings": {
    "aspect_ratio": "16:9",
    "width": 1920,
    "height": 1080,
    "fps": 30,
    "total_duration": 18.0
  },
  "scenes": [
    {
      "id": "c1f7a28e-8a62-4f3b-b2b9-e1f486d5e120",
      "sequence": 1,
      "duration": 6.0,
      "background": {"type": "color", "value": "#0F172A"},
      "avatar": {
        "avatar_id": "00000000-0000-0000-0000-000000000001",
        "view_mode": "half_body",
        "position": {"x": 0.5, "y": 0.65, "scale": 1.0, "rotation": 0.0}
      },
      "speech": {
        "voice_id": "voice_mock_en_marcus",
        "script": "Mock intro text for testing.",
        "speed": 1.0,
        "pitch": 0.0
      },
      "layers": [],
      "subtitles": []
    }
  ],
  "audio_tracks": [],
  "assets": [],
  "metadata": {
    "generated_by": "video_agent",
    "prompt": "Create an introductory video"
  }
}
```

#### AFTER (Real Neural SLM Generation)
```json
{
  "schema_version": 1,
  "settings": {
    "aspect_ratio": "16:9",
    "width": 1920,
    "height": 1080,
    "fps": 30,
    "total_duration": 20.0
  },
  "scenes": [
    {
      "id": "d8e3b1c2-7a41-41e9-9184-f3a2c5e8b001",
      "sequence": 1,
      "duration": 7.0,
      "background": {"type": "color", "value": "#0F172A"},
      "avatar": {
        "avatar_id": "00000000-0000-0000-0000-000000000001",
        "view_mode": "half_body",
        "position": {"x": 0.5, "y": 0.65, "scale": 1.0, "rotation": 0.0},
        "video_asset_id": null
      },
      "speech": {
        "voice_id": "en_US-lessac-medium",
        "script": "Welcome to HeyZen. Create stunning studio-grade AI videos from simple text in seconds.",
        "audio_asset_id": null,
        "speed": 1.0,
        "pitch": 0.0
      },
      "layers": [
        {
          "id": "layer_001_heading",
          "type": "text",
          "name": "Title Heading",
          "start_time": 0.0,
          "end_time": 7.0,
          "transform": {"x": 0.5, "y": 0.2, "scale": 1.0},
          "content": {"text": "Welcome to HeyZen", "font_size": 48, "color": "#FFFFFF"}
        }
      ],
      "subtitles": []
    },
    {
      "id": "d8e3b1c2-7a41-41e9-9184-f3a2c5e8b002",
      "sequence": 2,
      "duration": 8.0,
      "background": {"type": "color", "value": "#0F172A"},
      "avatar": {
        "avatar_id": "00000000-0000-0000-0000-000000000001",
        "view_mode": "half_body",
        "position": {"x": 0.5, "y": 0.65, "scale": 1.0, "rotation": 0.0},
        "video_asset_id": null
      },
      "speech": {
        "voice_id": "en_US-lessac-medium",
        "script": "Choose from dozens of neural avatars and voices, with instant lip-sync and automatic subtitles.",
        "audio_asset_id": null,
        "speed": 1.0,
        "pitch": 0.0
      },
      "layers": [],
      "subtitles": []
    },
    {
      "id": "d8e3b1c2-7a41-41e9-9184-f3a2c5e8b003",
      "sequence": 3,
      "duration": 5.0,
      "background": {"type": "color", "value": "#0F172A"},
      "avatar": {
        "avatar_id": "00000000-0000-0000-0000-000000000001",
        "view_mode": "half_body",
        "position": {"x": 0.5, "y": 0.65, "scale": 1.0, "rotation": 0.0},
        "video_asset_id": null
      },
      "speech": {
        "voice_id": "en_US-lessac-medium",
        "script": "Ready to bring your ideas to life? Start creating your first project right now.",
        "audio_asset_id": null,
        "speed": 1.0,
        "pitch": 0.0
      },
      "layers": [],
      "subtitles": []
    }
  ],
  "audio_tracks": [],
  "assets": [],
  "metadata": {
    "generated_by": "video_agent",
    "prompt": "Create an introductory 3-scene video welcoming new users to HeyZen.",
    "model_id": "llm/qwen-2.5-0.5b-cpu",
    "provider": "qwen"
  }
}
```

---

## 12. API Design

The API design reuses and strengthens the canonical endpoint without modifying frontend contracts.

### Endpoint Definition
- **Method & Path**: `POST /workspaces/{workspace_id}/projects/generate`
- **Summary**: Generate Video Project from Prompt
- **Status Code**: `HTTP_201_CREATED` (synchronous execution) or `HTTP_202_ACCEPTED` (when `run_async=True`).
- **Authorization**: Header `Authorization: Bearer <jwt>`, permission check `project.create`.
- **Workspace Isolation**: Enforced via path parameter `workspace_id`. Cross-workspace project creation is forbidden.

### Request Schema (`GenerateProjectRequest`)
```json
{
  "prompt": "Create a 3-scene product overview video for an AI dev tool",
  "target_duration_seconds": 30.0,
  "video_tone": "professional",
  "aspect_ratio": "16:9",
  "avatar_id": "00000000-0000-0000-0000-000000000001",
  "voice_id": "en_US-lessac-medium",
  "brand_kit_id": null,
  "auto_synthesize_speech": false,
  "run_async": false,
  "provider": "qwen",
  "device": "cpu",
  "idempotency_key": null
}
```

### Response Schema
- **Sync (`run_async=false`)**: `ProjectResponse` (`HTTP_201_CREATED`) returning the initialized Project and active `ProjectVersionResponse`.
- **Async (`run_async=true`)**: `JobResponse` (`HTTP_202_ACCEPTED`) returning the durable tracking `job_id`.

### Error Responses
- `400 Bad Request`: `PROMPT_TOO_SHORT`, `INVALID_ASPECT_RATIO`, `INVALID_DURATION`.
- `404 Not Found`: `BRAND_KIT_NOT_FOUND`, `AVATAR_NOT_FOUND`, `VOICE_NOT_FOUND`.
- `503 Service Unavailable`: `AI_RUNTIME_UNAVAILABLE` (when `AI_PROVIDER_MODE="real"` and local model weights are missing).
- `409 Conflict`: `CONCURRENCY_CONFLICT` (if revising existing project).

---

## 13. Comprehensive Test Strategy

The planned test matrix covers all layers of the platform:

```
+-----------------------------------------------------------------------------------+
|                            Step 5 Test Matrix                                     |
+-------------------+---------------------------------------------------------------+
| Test Category     | Key Validation Points                                         |
+-------------------+---------------------------------------------------------------+
| 1. Unit Tests     | - Qwen Provider protocol adherence (LLMProvider)              |
|                   | - ProviderDescriptor and ModelDescriptor metadata validity    |
|                   | - Prompt template formatting and JSON parser robustness       |
|                   | - License metadata classification (COMMERCIAL_SAFE)           |
| 2. Runtime Tests  | - Strict real mode: raises AIRuntimeUnavailableException      |
|                   |   if ONNX weights missing (NO mock fallback)                  |
|                   | - Device preference: rejects 'cuda' on CPU with AI_GPU_UNAVAIL|
|                   | - Memory bounds check: rejects loading if RAM < 512 MB        |
| 3. Domain Tests   | - VideoAgentService prompt decomposition                      |
|                   | - Multi-scene timeline assembly with valid durations          |
|                   | - Avatar and Voice ID propagation to scenes                   |
|                   | - BrandKit color inheritance to scene backgrounds             |
| 4. Worker Tests   | - Celery task heyzen.tasks.ai.generate_project on cpu_media   |
|                   | - Observable progress reporting (10%, 25%, 70%, 100%)         |
|                   | - Cooperative cancellation check points                       |
|                   | - Failure handling and error message propagation              |
| 5. Concurrency    | - Initial ProjectVersion creation with revision = 1           |
|                   | - Atomic database transaction (Project + ProjectVersion)      |
|                   | - Workspace isolation and multi-tenant security               |
| 6. E2E Acceptance | - Real local neural inference generating 3-scene project      |
|                   | - Closed-loop downstream test: Prompt -> Project -> Speech    |
|                   |   Synthesis (Piper) -> Subtitles (Whisper) -> OK!             |
+-------------------+---------------------------------------------------------------+
```

---

## 14. Planned Acceptance Criteria

Before Step 5 can be considered complete, all of the following objective criteria must pass:

1. **Exact Provider Selected**: `RealQwenLLMProvider` is resolved when `AI_PROVIDER_MODE="real"`.
2. **Exact Model Cataloged**: `llm/qwen-2.5-0.5b-cpu` registered with `Apache-2.0` license and `COMMERCIAL_SAFE` metadata.
3. **Real Neural Inference Performed**: Local CPU inference generates genuine, context-relevant scene script narration without calling `MockLLMProvider`.
4. **Valid ProjectDocumentV1 Created**: Emits a valid schema version 1 document containing >= 1 scenes with valid durations, backgrounds, speech scripts, and avatar assignments.
5. **Database Transaction Atomic**: Project and initial `ProjectVersion` (revision 1) committed atomically under workspace boundary.
6. **Strict No-Mock Policy**: In `AI_PROVIDER_MODE="real"`, if model weights are deleted, the endpoint strictly returns `503 Service Unavailable` (`AIRuntimeUnavailableException`) and does **not** fall back to mock.
7. **Correct Celery Queue**: When dispatched asynchronously, routes strictly to the `cpu_media` queue.
8. **Cooperative Cancellation Verified**: Cancelled jobs terminate gracefully without committing orphaned records.
9. **Zero Migrations**: All existing Alembic migrations pass without introducing new database schema changes.
10. **Frontend Untouched**: Zero lines changed in `src/` or `public/`.
11. **Full Regression Clean**: All 286 existing backend tests continue to pass with zero regressions.

---

## 15. Ordered Implementation Plan

Once approved, Step 5 implementation will proceed in eight orderly phases:

### Phase 5.1: Provider Contract & Protocol Conformance
- Add `LLMContractRequest` and `LLMContractResult` to `backend/app/ai/contracts.py`.
- Define prompt templates, system instructions, and JSON extraction helpers.

### Phase 5.2: Model Catalog & Runtime Registration
- Add `llm/qwen-2.5-0.5b-cpu` (local CPU) and `llm/qwen-2.5-7b-gpu` (CUDA production target) to `backend/app/ai/model_registry.py`.
- Configure strict hardware requirements, memory limits (512 MB), and license metadata (`COMMERCIAL_SAFE`).

### Phase 5.3: Real Qwen LLM Adapter Implementation
- Implement `RealQwenLLMProvider` in `backend/app/ai/adapters/qwen.py` using `onnxruntime-genai` (CPUExecutionProvider).
- Implement robust JSON markdown parsing with deterministic fallback structuring for non-conformant completions.
- Wire auto-registration into `backend/app/ai/registry.py`.

### Phase 5.4: Domain Service Orchestration
- Update `backend/app/services/video_agent_service.py` to use typed execution contracts and pass prompt context (tone, target duration, scene count).
- Ensure BrandKit colors and default avatar/voice IDs propagate to structured scenes.

### Phase 5.5: Celery Asynchronous Task & Queue Routing
- Implement `generate_project` Celery task in `backend/app/workers/tasks/ai_tasks.py`.
- Route to `cpu_media` queue with progress callbacks and cancellation checks.

### Phase 5.6: API Endpoint Enhancement
- Update `POST /workspaces/{workspace_id}/projects/generate` in `backend/app/api/v1/endpoints/project_orchestration.py` to support `run_async` parameter and return `JobResponse` (`HTTP 202`) when requested.

### Phase 5.7: Unit, Runtime, and Integration Tests
- Write test suite `backend/tests/unit/test_ai_qwen_provider.py`.
- Write contract tests in `backend/tests/unit/test_ai_contracts.py`.
- Write domain service tests in `backend/tests/unit/test_video_agent_service.py`.
- Test strict real-mode failure behavior without mock fallback.

### Phase 5.8: Real Local Inference & End-to-End Acceptance
- Download local ONNX model weights to `models_cache/llm/qwen2.5-0.5b/`.
- Run real end-to-end prompt-to-project synthesis on host CPU.
- Verify downstream closed loop: prompt generated project -> TTS speech synthesis -> ASR transcription.
- Execute full test regression across all 286+ backend tests.

---

## 16. File-Level Plan

```
[NEW]
backend/app/ai/adapters/qwen.py
  - RealQwenLLMProvider implementing LLMProvider protocol via onnxruntime-genai.
  - JSON schema prompt formatting and robust response parsing.

[NEW]
backend/tests/unit/test_ai_qwen_provider.py
  - Unit tests for Qwen provider, prompt formatting, and fallback JSON extraction.

[MODIFY]
backend/app/ai/contracts.py
  - Add LLMContractRequest and LLMContractResult models.

[MODIFY]
backend/app/ai/adapters/__init__.py
  - Export RealQwenLLMProvider.

[MODIFY]
backend/app/ai/registry.py
  - Auto-register RealQwenLLMProvider under AICapability.LLM in _bootstrap_default_mock_providers().

[MODIFY]
backend/app/ai/model_registry.py
  - Register llm/qwen-2.5-0.5b-cpu (CPU) and llm/qwen-2.5-7b-gpu (CUDA target).

[MODIFY]
backend/app/services/video_agent_service.py
  - Connect VideoAgentService to typed LLM contracts with structured prompt decomposition.

[MODIFY]
backend/app/workers/tasks/ai_tasks.py
  - Add _execute_generate_project() and Celery task generate_project on queue 'cpu_media'.

[MODIFY]
backend/app/schemas/orchestration.py
  - Add optional run_async, provider, and device fields to GenerateProjectRequest.

[MODIFY]
backend/app/api/v1/endpoints/project_orchestration.py
  - Support run_async in generate_project endpoint returning Union[ProjectResponse, JobResponse].

[DO NOT MODIFY]
src/*
public/*
package.json
package-lock.json
backend/app/schemas/project_document.py
backend/alembic/*
backend/app/models/*
```

---

## 17. Dependency Plan

### Existing Dependencies Reused
- **`onnxruntime-genai==0.16.0`**: Already installed in `.venv`. High-performance CPU generative runtime for SLM inference.
- **`tokenizers==0.23.2`**: Already installed in `.venv`. Fast HuggingFace BPE tokenization.
- **`onnxruntime==1.30.0`**: Already installed in `.venv`. Core ONNX inference engine.
- **`pydantic==2.13.5`**: Already installed. Contract validation.
- **`celery==5.6.3` & `redis==8.1.0`**: Already installed. Task queue and pub/sub.
- **`sqlalchemy==2.0.52` & `asyncpg==0.31.0`**: Already installed. Async DB access.

### New Packages Required
- **NONE**. Zero new pip dependencies required! The necessary generative ONNX runtime packages are already present in the active virtual environment.

### Approximate Footprint
- Model Download: ~380 MB on disk (`models_cache/llm/qwen2.5-0.5b/`).
- Runtime Memory: ~520 MB peak RAM during inference.
- VRAM Impact: 0 MB (runs purely on host CPU).

---

## 18. Security Evaluation

1. **Prompt Injection & System Jailbreaks**:
   - System prompts are strictly separated from user input.
   - Prompts are clamped to a maximum length (5000 chars) to prevent context flooding.
2. **Model Download Integrity**:
   - Model weights downloaded with explicit SHA-256 integrity verification.
   - Cache path locked to workspace scratch / dedicated `models_cache` directory.
3. **Workspace Isolation**:
   - Project creation strictly requires verified `workspace_id` matching user membership.
   - Cross-workspace prompt generation is rejected with `403 Forbidden`.
4. **Resource Exhaustion Defense**:
   - `max_new_tokens` hard-capped at 512 tokens to bound generation latency and memory consumption.
   - Timeouts enforced at 30 seconds for CPU execution.
5. **Temporary File & Memory Cleanup**:
   - Explicit memory garbage collection after generation to release KV cache buffers.

---

## 19. Technical Risks & Mitigations

| Risk | Severity | Technical Mitigation |
| :--- | :--- | :--- |
| **Low Free RAM (~0.85 GB on Host)** | HIGH | Use Qwen 2.5 0.5B (350 MB weights, 520 MB peak RAM). Do NOT use 3B or 7B models on host. Explicitly monitor available memory before loading. |
| **Non-Conformant JSON Output** | MEDIUM | Prompt includes few-shot JSON schema; provider implements regex-based JSON block extractor and fallback schema recovery to ensure valid `ProjectDocumentV1`. |
| **CPU Generation Latency (Windows)** | MEDIUM | `onnxruntime-genai` utilizes multithreaded OpenMP execution across 12 vCPUs, yielding 25-35 tokens/sec (~8 seconds total). Asynchronous Celery dispatch prevents API timeouts. |
| **Licensing Contamination** | LOW | Qwen 2.5 is licensed under Apache 2.0 (`COMMERCIAL_SAFE`), unlike LRS2 (Wav2Lip) or CPML (XTTS). Fully cleared for commercial self-hosting. |
| **Concurrency / OCC Conflicts** | LOW | Generation creates a new `Project` with revision = 1; OCC conflicts only apply if updating existing projects. |

---

## 20. Final Recommendation

### Status: PROCEED

1. **Recommended Step 5 Capability**: **Autonomous AI Video Agent & Structured Script Generation (`AICapability.LLM`)**.
2. **Recommended Local Provider**: `RealQwenLLMProvider` (`app.ai.adapters.qwen`).
3. **Exact Model / Checkpoint**: `Qwen/Qwen2.5-0.5B-Instruct-ONNX` (CPU) | `Qwen/Qwen2.5-7B-Instruct` (Future CUDA Target).
4. **License Classification**: **`COMMERCIAL_SAFE`** (Apache 2.0 across code, weights, and tokenizer).
5. **Current Host Feasibility**: **100% FEASIBLE** on AMD Ryzen 5 5500U (~350 MB disk, ~520 MB RAM, fits inside 0.85 GB available headroom, 25-35 tokens/sec).
6. **Future CUDA Strategy**: Architected for `Qwen/Qwen2.5-7B-Instruct` or `Llama-3.3-70B` via vLLM on `gpu_ai` worker.
7. **Required Dependencies**: **Zero new packages**. Reuses already-installed `onnxruntime-genai 0.16.0` and `tokenizers 0.23.2`.
8. **Database Migration Requirement**: **Zero database migrations**.
9. **Frontend Modification Requirement**: **Zero frontend changes**.
10. **Estimated Implementation Complexity**: **Medium** (clean provider abstraction, JSON parsing robustness, Celery task, unit tests).
11. **Acceptance-Test Strategy**: Unit contract tests + strict real-mode failure tests + real CPU neural prompt decomposition + downstream Piper/Whisper closed loop + full 286-test regression.
12. **Main Blocker / Risk**: Low host memory (~0.85 GB available) requiring strict adherence to the 0.5B parameter budget.

---

## 21. Absolute Stop Condition

**NO IMPLEMENTATION CODE HAS BEEN WRITTEN.**  
**NO SOURCE FILES HAVE BEEN MODIFIED.**  
**NO PACKAGES HAVE BEEN INSTALLED.**  
**NO DATABASE MIGRATIONS HAVE BEEN CREATED.**  
**NO FRONTEND FILES HAVE BEEN ALTERED.**  

This document (`docs/phase-8-step-5-plan.md`) represents the exclusive deliverable for Step 5 planning.  
**AWAITING EXPLICIT USER APPROVAL BEFORE PROCEEDING TO IMPLEMENTATION.**
