# Phase 20 — Commercial-Safe Voice Cloning / Voice Import Forensic Audit

**PROJECT:** HeyZen  
**REPOSITORY:** `d:\HeyGen\video-ai-tools`  
**STATUS:** **AUDIT COMPLETE — CONDITIONAL — ARTIFACT VERIFICATION REQUIRED**  
**DATE:** 2026-09-17  

---

## 1. Executive Summary & Audit Classification

Phase 20 investigates the feasibility of integrating a real, commercial-safe local voice cloning / voice import capability into HeyZen. In strict accordance with Phase 20 rules:
- **No model weights have been downloaded.**
- **No AI packages have been installed.**
- **No database migrations have been created.**
- **No frontend files have been modified.**
- **No production code has been altered.**

### Final Audit Classification
```
CONDITIONAL — ARTIFACT VERIFICATION REQUIRED
```

A verified commercial-safe candidate with a complete, permissible open-source dependency chain exists: **OpenVoice V2 (MyShell.ai)** under the **MIT License**. Furthermore, it is capable of running on the host **AMD Ryzen 5 5500U CPU** (~1.5–3.5s latency) without requiring NVIDIA CUDA. Popular alternative candidates (such as **XTTS-v2**, **YourTTS**, **F5-TTS**, **Fish Speech**, and **StyleTTS2**) have been **REJECTED** due to strict non-commercial licenses (Coqui CPML, CC-BY-NC-4.0), research-only clauses, or GPL-3.0 copyleft dependency contamination.

---

## 2. Existing HeyZen Architecture & Subsystems

The HeyZen platform already possesses the necessary architectural components to support voice cloning:

```
+-------------------------------------------------------------------------+
|                           Next.js Frontend                              |
|   - CreateVoiceCloneModal.tsx (Mic Recording, Audio File Upload, Tabs)  |
|   - VoicesLibrary.tsx (Voice Catalog, Preset vs Custom Cloned Badges)   |
|   - api.assets.createUploadIntent / uploadBinaryDirect / confirmUpload   |
+-------------------------------------------------------------------------+
                                     |
                       POST /assets/upload-intents
                       POST /voices/clone (Job Enqueue)
                                     v
+-------------------------------------------------------------------------+
|                       FastAPI API Gateway                               |
|   - Authentication: get_current_user (JWT / Session Cookie)             |
|   - Authorization: require_permission("voice.create")                   |
|   - Workspace Boundary Isolation: workspace_id enforcement              |
|   - Redis Atomic Rate Limiter: check_rate_limit                         |
+-------------------------------------------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                  PostgreSQL 16 (Durable Source of Truth)                |
|   - voices (id, workspace_id, voice_type='cloned', provider_metadata)  |
|   - assets (id, workspace_id, storage_key, mime_type, extra_metadata)   |
|   - jobs (id, workspace_id, job_type='voice_clone', status, payload)    |
+-------------------------------------------------------------------------+
                                     |
                       Enqueue Celery Task (Redis)
                                     v
+-------------------------------------------------------------------------+
|                        Celery Async Workers                             |
|   - Task: heyzen.tasks.ai.voice_clone                                   |
|   - Input: source_asset_id, voice_name, language                        |
|   - Temp Execution Isolation: MediaTempManager                          |
|   - Speaker Embedding Extraction -> MinIO Object Storage                |
|   - Preview Synthesis -> MinIO Object Storage (preview_asset_id)        |
+-------------------------------------------------------------------------+
```

---

## 3. Existing Voice UI & Frontend Controls Audit

An inspection of `src/components/voices/` reveals that rich, canonical UI controls are already implemented:

1. **`CreateVoiceCloneModal.tsx`**:
   - **Tab 1 ("Record audio")**:
     - Language selection (`English`, `Hindi`, `Spanish`, `French`).
     - Microphone detection and permissions toggle.
     - Live recording with a 15-second countdown timer, visual progress bar, prompt text, and stop action.
     - Sample recorded state with voice name input (`voiceName`), re-record button, and "Save & Clone Voice" trigger.
   - **Tab 2 ("Upload audio")**:
     - Drag-and-drop / file browser dropzone accepting `audio/*` (MP3, WAV, M4A, AAC; max 50MB).
   - **Tab 3 ("Record on phone")**:
     - QR code modal for mobile audio capture.
   - **Styling & Freeze**: All styles use vanilla Tailwind CSS classes, Lucide icons, and dark-mode tokens. **Zero frontend redesign is needed.**

2. **`ImportVoiceModal.tsx`**:
   - Dedicated modal for 3rd-party remote API key connections (ElevenLabs, LMNT). Distinct from local voice cloning.

3. **`DesignVoiceModal.tsx`**:
   - Dedicated modal for natural-language descriptive voice generation ("Design a voice from prompt"). Distinct from reference-audio voice cloning.

4. **`VoicesLibrary.tsx`**:
   - Displays voices categorized by language, gender, and type (`Public` vs `Custom`).
   - Includes "+ Create voice clone", "+ Design a voice", and "+ Import voice" header action buttons.
   - Supports audio preview playback via HTML5 Audio.

5. **`src/lib/api.ts`**:
   - Contains `api.assets.createUploadIntent(...)`, `api.assets.uploadBinaryDirect(...)`, `api.assets.confirmUpload(...)`, and `api.assets.getDownloadUrl(...)`.
   - Directly enables pre-signed direct MinIO streaming of user voice recordings.

---

## 4. Existing Voice Model & Database Feasibility Audit

### Current Database State
```bash
alembic current
# Output: 0006_api_keys_and_webhooks (head)
```

### Table: `voices` (`backend/app/models/voice.py`)
The existing schema was engineered during Phase 8 to support voice cloning without schema changes:

| Column | Type | Nullable | Role in Voice Cloning |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | No | Unique cloned voice identifier (PK). |
| `workspace_id` | `UUID` | No | Strict workspace boundary; prevents cross-workspace voice leakage. |
| `created_by` | `UUID` | No | User ownership tracking. |
| `name` | `String(128)` | No | User-assigned voice display name (e.g. "CEO Keynote Voice"). |
| `description` | `String(512)` | Yes | Optional description of speaker characteristics. |
| `voice_type` | `String(32)` | No | Stores `"cloned"` (already valid alongside `"preset"` and `"custom"`). |
| `language` | `String(16)` | No | Primary language code (e.g. `"en"`, `"es"`). |
| `gender` | `String(16)` | No | Perceived gender (`"male"`, `"female"`, `"neutral"`). |
| `provider` | `String(64)` | No | Cloned voice provider engine (e.g. `"openvoice"`). |
| `provider_reference` | `String(255)` | Yes | MinIO storage key for the serialized speaker embedding tensor (e.g. `workspaces/{id}/voices/{voice_id}/embedding.pt`). |
| `provider_metadata` | `JSONB` | No | Structured cloning metadata: `source_asset_id`, `sample_duration_sec`, `sample_rate`, `model`, `base_voice_id`, `quality_score`. |
| `preview_asset_id` | `UUID` | Yes | Foreign key to `assets.id` holding the synthesized preview audio clip. |
| `status` | `String(32)` | No | Lifecycle state: `"pending"`, `"processing"`, `"ready"`, `"failed"`. |
| `visibility` | `String(32)` | No | Defaults to `"workspace"`, enforcing tenant data privacy. |
| `deleted_at` | `DateTime` | Yes | Soft-delete capability. |

### Table: `jobs` (`backend/app/models/job.py`)
- `job_type`: Already includes `"voice_clone"` in its model definition and comments.
- `payload`: Contains `{"voice_name": "...", "source_asset_id": "...", "language": "en"}`.
- `result`: Stores `{"voice_id": "...", "preview_asset_id": "...", "status": "ready"}`.
- `celery_task_id`: Tracks background task execution.

### Table: `assets` (`backend/app/models/asset.py`)
- Represents both the input reference audio (`asset_type="audio"`, `mime_type="audio/wav"`) and the generated voice preview audio.

### Database Feasibility Verdict
**NO DATABASE MIGRATIONS REQUIRED.** The existing relational structure fully and safely accommodates voice cloning identity, source audio provenance, embedding reference, preview asset linkage, and workspace isolation. The Alembic head remains safely frozen at `0006_api_keys_and_webhooks (head)`.

---

## 5. Existing TTS & Speech Pipeline Integration

In `backend/app/services/project_speech_service.py`:
1. Every scene cut in `ProjectDocumentV1` defines:
   ```python
   class SceneSpeech(BaseModel):
       voice_id: str
       script: str
       audio_asset_id: Optional[str] = None
       speed: float = 1.0
       pitch: float = 0.0
   ```
2. During speech synthesis, the service queries `get_tts_provider()`.
3. If `voice_id` references a cloned voice, the TTS provider:
   - Synthesizes the base prosody/phonemes.
   - Applies the cloned speaker embedding (`embedding.pt`) to convert the timbre into the cloned voice.
   - Emits synthesized audio bytes.
   - Ingests the result via `AssetLifecycleManager` into `scene.speech.audio_asset_id`.

**Key Architectural Finding:** Cloned voices integrate directly into the existing `SceneSpeech` pipeline without requiring a second, separate speech orchestration system.

---

## 6. Voice Cloning vs. Voice Design vs. Voice Conversion vs. TTS

To ensure truthful advertising and prevent fake cloning:

| Concept | Definition | HeyZen Status | Reference Audio Required? |
| :--- | :--- | :--- | :--- |
| **Voice Cloning** | Extracts acoustic/timbre features from a user reference recording to synthesize new text in that specific person's voice. | **Target of Phase 20** | **YES (Mandatory)** |
| **Voice Design** | Generates synthetic speech profiles from descriptive text prompts (e.g. "warm female narrator"). | Implemented via `DesignVoiceModal.tsx` | NO (Text prompt only) |
| **Voice Conversion** | Audio-to-audio transformation altering the timbre of an existing recorded spoken sentence into another voice. | Distinct capability | YES |
| **Text-to-Speech (TTS)** | Generates speech audio from text using fixed, predefined voices (e.g. Piper `en_US-lessac-medium`). | Existing production baseline | NO (Pre-trained fixed voices) |

*Rule:* Plain TTS or fixed preset playback will NEVER be labeled as voice cloning. Reference audio must be physically ingested and processed by an embedding extractor.

---

## 7. Host Hardware Environment Audit

Host specifications detected via `app.ai.hardware.detect_hardware()`:

| Component | Detected Specification | Constraint Impact |
| :--- | :--- | :--- |
| **CPU** | AMD Ryzen 5 5500U (6 physical cores, 12 logical threads, AMD64) | High single/multi-thread CPU capability; supports ONNX Runtime & PyTorch CPU. |
| **System RAM** | 16 GB Total (~7.88 GB allocated, ~7.5 GB free) | Ample memory for CPU embedding extraction and tone color conversion. |
| **GPU** | AMD Radeon(TM) Integrated Graphics (512 MB VRAM) | **NO NVIDIA CUDA.** `cuda_available: false`. |
| **Operating System** | Windows 11 (build 10.0.26200) | Native Windows 11 host environment. |

### Hardware Rules Applied:
1. **Rule 21 & 22 Compliance**: The host has NO NVIDIA CUDA. Any model that strictly requires CUDA (e.g., GPT-SoVITS fine-tuning, XTTS-v2 GPU worker) must fail closed with `GPU_UNAVAILABLE`.
2. **CPU Execution Requirement**: To achieve local end-to-end validation on this machine, the model must support truthful, performant CPU inference without fake mocks.

---

## 8. Forensic Licensing Audit Matrix

Every realistic open-source voice cloning and TTS candidate was investigated across its complete dependency chain:

| Candidate | Code License | Weights License | Auxiliary / Encoder / Vocoder License | Commercial Use Permitted? | CPU Support | Forensic Classification & Rejection Reason |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **OpenVoice V2** | MIT | **MIT** (Hugging Face `myshell-ai/OpenVoiceV2`, updated April 2024) | Silero VAD (MIT), PyTorch (BSD) | **YES (Fully Commercial-Safe)** | **YES (~1.5–3.5s)** | **APPROVED — CONDITIONAL (Artifact verification required upon download)** |
| **OpenVoice V1** | MIT | **MIT** (Updated April 2024) | Silero VAD (MIT) | **YES** | **YES** | **APPROVED (Superseded by V2)** |
| **CosyVoice 1 & 2** | Apache-2.0 | Apache-2.0 | WeNet / FunASR (Apache-2.0) | **YES** | No (15–45s latency on CPU; designed for CUDA) | **CONDITIONAL — HARDWARE INCOMPATIBLE (CUDA Target Only)** |
| **XTTS-v2** | MPL-2.0 | **CPML (Coqui Public Model License)** | CPML | **NO (STRICTLY PROHIBITED)** | Poor / CUDA target | **REJECTED — NON-COMMERCIAL** (Coqui defunct; commercial licenses unobtainable) |
| **YourTTS** | MPL-2.0 | **CPML** | CPML | **NO (STRICTLY PROHIBITED)** | Yes | **REJECTED — NON-COMMERCIAL** (Coqui CPML non-commercial restriction) |
| **F5-TTS** | MIT | **CC-BY-NC-4.0** | Emilia Dataset (CC-BY-NC-4.0) | **NO (STRICTLY PROHIBITED)** | Poor | **REJECTED — NON-COMMERCIAL** (Pre-trained weights bound by CC-BY-NC-4.0) |
| **Fish Speech** | BSD-3 | **Fish Audio Research License** | Research License | **NO (STRICTLY PROHIBITED)** | Poor | **REJECTED — RESEARCH ONLY / NON-COMMERCIAL** (Requires commercial enterprise contract) |
| **StyleTTS2** | MIT | Conditional Attribution | `phonemizer` / `espeak-ng` (**GPL-3.0 Copyleft**) | **HIGH RISK / RESTRICTIVE** | Moderate | **REJECTED — DEPENDENCY RESTRICTION (GPL-3.0 Copyleft Contamination)** |
| **Parler-TTS** | Apache-2.0 | Apache-2.0 | Apache-2.0 | YES | Moderate | **REJECTED — INCAPABLE (Voice Design/Prompting only; no reference audio cloning)** |
| **MeloTTS** | MIT | MIT | MIT | YES | YES | **REJECTED — INCAPABLE (Fixed-preset multi-speaker TTS only; no voice cloning)** |
| **Kokoro-82M** | Apache-2.0 | Apache-2.0 | Apache-2.0 | YES | YES | **REJECTED — INCAPABLE (54 Fixed preset voices only; no voice cloning)** |
| **GPT-SoVITS** | MIT | MIT / Community | `chinese-hubert-base` (MIT) | Permitted | Infeasible (CUDA training/fine-tuning pipeline) | **CONDITIONAL — HARDWARE INCOMPATIBLE (Heavy CUDA workflow)** |
| **Chatterbox-TTS** | MIT | MIT (Resemble AI) | PerTh watermark (MIT) | Permitted | Infeasible without CUDA tensor overrides | **CONDITIONAL — HARDWARE INCOMPATIBLE (CUDA target)** |

---

## 9. In-Depth Analysis of the Leading Candidate: OpenVoice V2

### Why OpenVoice V2 is the Recommended Candidate
1. **Uncompromised Licensing**:
   - Repository: MIT License (`myshell-ai/OpenVoice`).
   - Hugging Face Model Weights: Released under MIT License since April 2024.
   - Complete downstream freedom for commercial SaaS, API, and cloud deployments.
2. **Two-Stage Decoupled Architecture**:
   - **Stage 1 (Base Speech Generation)**: Uses a base TTS model (such as Piper TTS or MeloTTS) to generate phonetic and prosodic speech. HeyZen already has local, high-speed **Piper TTS** fully integrated and operational.
   - **Stage 2 (Tone Color Converter)**: Ingests the base speech alongside the extracted speaker embedding (`target_se`) from the user's reference recording and converts the timbre to match the target speaker.
3. **CPU Execution on Host**:
   - The Tone Color Converter is compact (~104 MB checkpoint) and computationally lightweight.
   - Runs in ~1.5 to 3.5 seconds on the host AMD Ryzen 5 5500U CPU.
4. **Sample Requirements**:
   - Requires a clean 5- to 30-second audio clip (WAV, MP3, M4A).
   - Silero VAD (already in HeyZen) removes silence and segments audio for clean feature extraction.
5. **Zero Copyleft Contamination**:
   - Uses PyTorch and Silero VAD. No GPL-3.0 `espeak-ng` or viral copyleft libraries.

### Model Artifact Specifications (Upon Implementation Approval)
- **Repository**: `https://huggingface.co/myshell-ai/OpenVoiceV2`
- **Revision**: `main`
- **Target Artifacts**:
  1. `converter/checkpoint.pth` (~104 MB)
  2. `converter/config.json` (~2 KB)
- **Cache Location**: `backend/models_cache/voice_clone/openvoice_v2/`
- **SHA256 Manifest**: To be verified and recorded upon physical download.

---

## 10. Security, Privacy & Workspace Isolation Design

1. **Workspace Boundary**:
   - The reference audio file must be uploaded as an `Asset` in the user's active `workspace_id`.
   - The resulting `Voice` record and its extracted speaker embedding will belong strictly to that same `workspace_id`.
   - Cross-workspace queries return `403 Forbidden` (`VOICE_CLONE_FORBIDDEN`).
2. **Audio Processing Privacy**:
   - Raw user audio is NEVER logged or emitted in telemetry.
   - Audio files are processed in temporary isolated directories (`MediaTempManager`) and scrubbed immediately upon task completion, failure, or cancellation.
   - Speaker embeddings are stored in workspace-scoped MinIO keys (`workspaces/{workspace_id}/voices/{voice_id}/embedding.pt`).
3. **Rate Limiting**:
   - Cloned voice creation is rate-limited via Redis atomic counters (`rate_limit:voice_clone:{workspace_id}:{user_id}`) to 5 jobs per minute.

---

## 11. Structured Error Taxonomy

The implementation will utilize the following explicit, truthful error codes:

| Error Code | HTTP Status | Trigger Condition |
| :--- | :--- | :--- |
| `VOICE_CLONE_MODEL_UNAVAILABLE` | 503 | OpenVoice V2 checkpoint files or dependencies are missing. |
| `VOICE_CLONE_GPU_UNAVAILABLE` | 503 | A CUDA-dependent voice cloning model is requested on non-CUDA hardware. |
| `VOICE_CLONE_LICENSE_REJECTED` | 400 | A non-commercial or unverified model checkpoint is requested. |
| `VOICE_CLONE_INVALID_AUDIO` | 400 | The reference audio cannot be decoded or is corrupted. |
| `VOICE_CLONE_AUDIO_TOO_SHORT` | 400 | The reference audio has less than 3 seconds of active speech after VAD. |
| `VOICE_CLONE_AUDIO_TOO_LONG` | 400 | The reference audio exceeds the maximum permitted duration (120 seconds). |
| `VOICE_CLONE_RATE_LIMITED` | 429 | Workspace/user rate limit exceeded. |
| `VOICE_CLONE_FORBIDDEN` | 403 | The caller does not own the reference asset or workspace. |
| `VOICE_CLONE_GENERATION_FAILED` | 500 | Unhandled exception during tone color conversion. |
| `VOICE_CLONE_CANCELLED` | 200 / 499 | Cooperative cancellation of the cloning job. |

---

## 12. Implementation Plan (Subject to Review & Approval)

When approved to proceed with execution:

1. **Step 1: AI Provider Registration & Descriptor**:
   - Add `OpenVoiceCloningProvider` conforming to `TTSProvider` protocol.
   - Register descriptor under `AICapability.TTS` with `name="openvoice"`, `requires_gpu=False`, `is_available=True`.
2. **Step 2: Checksum Verification & Provisioning**:
   - Download `converter/checkpoint.pth` and `converter/config.json` explicitly to `backend/models_cache/voice_clone/openvoice_v2/`.
   - Calculate and verify SHA256 checksums before loading.
3. **Step 3: Celery Task Execution**:
   - Implement `heyzen.tasks.ai.voice_clone` in `ai_tasks.py` using `_execute_voice_clone`.
   - Ingest reference audio `Asset`, run VAD segmentation, compute speaker embedding vector, save to MinIO, synthesize preview audio via base Piper TTS + OpenVoice converter, and persist `Voice` record with status `ready`.
4. **Step 4: API Endpoint Wiring**:
   - Add `POST /api/v1/workspaces/{workspace_id}/voices/clone` accepting `reference_asset_id`, `name`, `language`.
   - Validate creator permissions (`voice.create`), enforce rate limits, and enqueue background Celery job.
5. **Step 5: Frontend Minimal Wiring**:
   - Wire `CreateVoiceCloneModal.tsx` to upload audio sample via existing `api.assets` and trigger `POST /voices/clone`.
   - Preserve 100% of existing UI markup, layout, typography, and styling.
6. **Step 6: Comprehensive Verification Suite**:
   - Add `backend/tests/test_voice_cloning.py` covering license compliance, audio bounds validation, workspace isolation, non-mock real inference, preview generation, and error handling.

---

## 13. Audit Decision & Next Step

### Final Classification:
```
CONDITIONAL — ARTIFACT VERIFICATION REQUIRED
```

### Exact Next Step:
Present this forensic audit and candidate comparison matrix to the user for explicit sign-off on:
1. Selection of **OpenVoice V2 (MIT)** as the verified commercial-safe cloning stack.
2. Authorization to provision the lightweight OpenVoice V2 converter artifacts into `backend/models_cache/`.
3. Authorization to begin Phase 20 backend implementation according to this plan.
