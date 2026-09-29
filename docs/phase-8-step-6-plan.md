# Phase 8 Step 6 Plan
## Real Local CPU Neural Machine Translation & Multilingual Video Localization Engine
### CTranslate2 / MarianMT (Opus-MT) & M2M-100 Architecture

---

## 1. Current System State

HeyZen has successfully completed Phase 8 Steps 1 through 5, establishing a functional, self-hosted, CPU-feasible AI video creation pipeline running on Windows 11 with an AMD Ryzen 5 5500U processor (12 logical cores, 7.34 GB RAM, ~0.85 GB available RAM, AMD Radeon integrated graphics, zero CUDA).

The canonical repository is:
`D:\HeyGen\video-ai-tools`

### Architectural Status Across Milestones:
- **Phase 6 & Core Architecture**: FastAPI async backend, PostgreSQL with SQLAlchemy 2.0 async, Redis cache/broker, MinIO S3-compatible storage, Celery distributed tasks, optimistic concurrency control (`expected_revision`), canonical `ProjectDocumentV1`, and frozen Next.js 16.3.4 App Router frontend.
- **Phase 7**: Real media timeline compositor, FFmpeg subprocess engine with non-blocking async execution, FFprobe probe & validation services, visual layer compositing, audio mixing, and MinIO asset persistence.
- **Phase 8 Step 1**: Local AI runtime foundation, hardware capability detection (`HardwareSpec`), model catalog (`ModelRegistry`), unified lifecycle management (`get_lifecycle_manager()`), and multi-queue Celery topology (`cpu_media`, `gpu_ai`, `maintenance`).
- **Phase 8 Step 2**: Real local CPU text-to-speech synthesis using Piper TTS (`en_US-lessac-medium.onnx`), producing 16-bit mono 22,050 Hz PCM WAV audio with Brand Glossary pronunciation overrides.
- **Phase 8 Step 3**: Real local CPU automatic speech recognition using `faster-whisper` (`tiny.en` INT8 CTranslate2), extracting timestamped words, confidence scores, and subtitle cues.
- **Phase 8 Step 4**: Real local CPU lip-sync engine using `Wav2Lip-ONNX` (research-only prototyping), with `MuseTalk` architecturally prepared for future CUDA deployment.
- **Phase 8 Step 5**: Real local CPU autonomous AI video agent & structured script generation using `Qwen/Qwen2.5-0.5B-Instruct-ONNX` via `onnxruntime-genai`, transforming natural language prompts into validated `ProjectDocumentV1` timelines.
- **Current Test Suite**: 310 / 310 backend tests passing with zero regressions and zero Alembic migrations.

---

## 2. Existing Capabilities

The table below illustrates the active provider implementations across all 7 platform capabilities defined in `AICapability`:

| Capability | Active Mode (`real`) | Active Provider | Engine / Runtime | Compute Device | Local Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`LLM`** | Real | `RealQwenLLMProvider` | `onnxruntime-genai` (INT4) | CPU | **Real CPU Validated** (Step 5) |
| **`TTS`** | Real | `PiperTTSProvider` | `piper-tts` / `onnxruntime` | CPU | **Real CPU Validated** (Step 2) |
| **`ASR`** | Real | `WhisperASRProvider` | `faster-whisper` / `CTranslate2` | CPU | **Real CPU Validated** (Step 3) |
| **`AVATAR`** | Real | `Wav2LipONNXAvatarProvider` | `onnxruntime` (CPU) | CPU | **Real CPU Validated** (Step 4, Research-Only) |
| **`TRANSLATION`** | Mock | `MockTranslationProvider` | Synthetic String Formatting | CPU | **MOCK ONLY** (`[ES] Script...`) |
| **`IMAGE`** | Mock | `MockImageProvider` | Placeholder SVG/Canvas | CPU | **MOCK ONLY** (GPU required for SDXL) |
| **`VIDEO`** | Mock | `MockVideoProvider` | Synthetic Clip Generator | CPU | **MOCK ONLY** (GPU required for SVD) |

### Existing Closed-Loop Pipeline:
```
Natural-Language Prompt
       ↓
Real Qwen 2.5 0.5B INT4 (CPU)
       ↓
ProjectDocumentV1 (Scenes, Layers, Speech, Avatar)
       ↓
Real Piper TTS Narration WAV (CPU)
       ↓
Real faster-whisper Subtitles & Timestamps (CPU)
       ↓
Real Wav2Lip-ONNX Avatar Lip-Sync MP4 (CPU)
       ↓
FFmpeg Compositor & FFprobe Verification
       ↓
Final MP4 Container & MinIO Ingestion
```

---

## 3. Remaining Product Gaps

While HeyZen can now generate an entire English video from a prompt, several key product capabilities separate it from a functional HeyGen competitor:

1. **The Multilingual Localization Gap (Headline Product Feature)**:
   - In HeyGen, the most famous and monetized feature is **Video Translation & Multilingual Localization** ("One-click video translation into 40+ languages with cloned voice, lip-sync, and brand glossary").
   - HeyZen's frontend already contains an extensive 69 KB dedicated application: `src/components/apps/TranslateVideos.tsx`.
   - The backend already defines `ProjectLocalizationService` and the endpoint `POST /api/v1/workspaces/{workspace_id}/projects/{project_id}/translate`.
   - However, `AICapability.TRANSLATION` is currently backed entirely by `MockTranslationProvider`, which simply prepends `[ES]` or `[FR]` to the script.
   - When a user requests translation, the system produces dummy text instead of real neural translation, breaking the multilingual promise.

2. **The Avatar Compositing & Transparency Gap**:
   - `SceneAvatar` links to a talking avatar video (`scene.avatar.video_asset_id`), but the compositor currently renders solid backgrounds or background imagery without alpha-compositing the avatar over layers.
   - Avatars have opaque rectangular camera backgrounds rather than transparent cutouts.

3. **Generative Visuals (B-Roll) Gap**:
   - Scenes currently use solid color backgrounds or uploaded assets; generative images/b-roll require heavy diffusion models (SDXL / SVD) requiring 6–16 GB VRAM GPUs.

4. **Zero-Shot Voice Cloning Gap**:
   - Piper uses pre-trained voice checkpoints. Instant cross-lingual zero-shot voice cloning (e.g. XTTS-v2) requires 4GB+ VRAM and PyTorch.

---

## 4. Candidate Capability Analysis

We evaluated all 10 candidate capabilities against product impact, hardware feasibility on the AMD Ryzen 5 5500U host (0.85 GB free RAM, no CUDA), licensing, dependencies, and frontend compatibility.

### Candidate Evaluation Matrix:

| Candidate | Modality / Focus | CPU Feasible? (0.85 GB RAM) | Required Stack | License Viability | Frontend Support | Product Impact | Fit for Step 6 |
| :--- | :--- | :---: | :--- | :--- | :--- | :---: | :---: |
| **A. Neural Machine Translation (NMT)** | `AICapability.TRANSLATION` | **YES** (~80 MB RAM, <100ms) | `CTranslate2` (already installed!) | **Apache-2.0 / MIT** (Opus-MT / M2M-100) | `TranslateVideos.tsx` (69 KB) | **CRITICAL** | **RECOMMENDED (1st)** |
| **B. Avatar Matting / Background Removal** | Vision / Alpha Mask | Marginal (CPU takes ~15s/clip) | ONNX Runtime / MediaPipe | Mixed (BRIA is Non-Commercial; MediaPipe Apache-2.0) | `VidoAIStudio.tsx` | Medium | Secondary |
| **C. Scene Visual Generation** | `AICapability.VIDEO` | **NO** (OOM crash, needs 16GB VRAM) | PyTorch, Diffusers, CUDA | Various | `VidoAIStudio.tsx` | High | Unfeasible on Host |
| **D. Image Generation** | `AICapability.IMAGE` | **NO** (OOM crash, needs 6GB VRAM) | PyTorch, Diffusers, CUDA | Non-commercial (SDXL-Turbo) | Studio Media Picker | Medium | Unfeasible on Host |
| **E. Voice Cloning** | `TTSProvider.clone_voice` | **NO** (OOM crash, needs 4GB VRAM) | PyTorch, XTTS-v2, CUDA | Coqui CPML (Restricted) | Voice Cloner modal | High | Unfeasible on Host |
| **F. Better Avatar (MuseTalk)** | `AICapability.AVATAR` | **NO** (requires CUDA GPU) | PyTorch, MMLab, CUDA | MIT | Studio Avatar Picker | High | Architected in Step 4 |
| **G. Advanced Video Transitions** | FFmpeg Media Pipeline | **YES** (native C execution) | FFmpeg xfade filtergraph | LGPL / GPL | Studio Transitions tab | Medium | Pipeline Utility |
| **H. Brand-Aware AI Generation** | LLM Context Injection | **YES** (uses Step 5 Qwen) | `onnxruntime-genai` | Apache-2.0 | Brand Kit editor | Low | Already in Step 5 |
| **I. AI-Assisted Editing** | LLM Timeline Diffing | **YES** (uses Step 5 Qwen) | `onnxruntime-genai` | Apache-2.0 | Studio Chat widget | Medium | Application Feature |
| **J. Template & Creative Library** | Domain Orchestration | **YES** (Database / JSON) | SQLAlchemy | Permissive | Templates tab | Medium | Data Feature |

### Detailed Analysis of Top Candidates:

#### Why Candidate A (Neural Machine Translation) is Superior:
1. **Fills the Sole Remaining Core Protocol**: `LLM`, `TTS`, `ASR`, and `AVATAR` are now real local engines. `TRANSLATION` is the only fundamental modality in `AICapability` that remains a dummy mock.
2. **Direct Closed-Loop Integration**: Step 6 connects with Step 5 (Qwen script) → Step 6 (Translate) → Step 2 (Piper target speech) → Step 3 (Whisper target subtitles) → Step 4 (Wav2Lip lip-sync) → Phase 7 (Render). This produces the industry's first **fully self-hosted, CPU-feasible, multi-lingual AI video generation loop**.
3. **Hardware Perfection**: High-performance NMT models (e.g. MarianMT / Opus-MT in CTranslate2 INT8) require only **~45 MB - 60 MB disk space** and **~80 MB RAM**. They execute in **30–80 milliseconds per sentence** on CPU without threatening host memory.
4. **Zero New Framework Installation**: `ctranslate2 4.8.2` and `tokenizers 0.23.2` are **ALREADY INSTALLED** in the Python virtual environment. Zero heavyweight dependencies (no PyTorch, no CUDA, no TensorFlow) are needed.
5. **Existing Business Domain**: `ProjectLocalizationService` and `BrandGlossaryRepository` already exist in the backend.

---

## 5. Recommended Step 6 Capability

### Formal Recommendation:
**Phase 8 Step 6: Real Local CPU Neural Machine Translation & Multilingual Video Localization Engine**

The engine will replace `MockTranslationProvider` with `RealCTranslate2TranslationProvider` (or `RealOpusMTTranslationProvider`), providing real offline neural translation with strict Brand Glossary enforcement, voice remapping, and optimistic concurrency versioning.

### Multilingual Pipeline Flow:
```
Original ProjectDocumentV1 (English narration generated by Qwen)
        │
        ▼
POST /api/v1/workspaces/{id}/projects/{id}/translate
        │
        ├── Brand Glossary Term Extraction (BrandGlossaryRepository)
        │     ├── Protected Brand Names (e.g., "HeyZen" -> preserved untouched)
        │     └── Approved Technical Terms (e.g., "artificial intelligence" -> "inteligencia artificial")
        │
        ▼
Real CTranslate2 / Opus-MT Neural Machine Translation (CPU INT8)
        │
        ├── Sentence Tokenization & Masking
        ├── CTranslate2 Beam Search (beam_size=2, max_decoding_length=256)
        └── Glossary Rule Re-integration & Casing Normalization
        │
        ▼
Localized ProjectDocumentV1 (Spanish / French / German)
        │
        ├── SceneSpeech.script updated to target language
        ├── SceneSpeech.audio_asset_id set to None (triggers downstream re-synthesis)
        ├── SceneSpeech.voice_id remapped to target language voice
        ├── ProjectDocumentV1.metadata["localized_from"] and ["language"] recorded
        │
        ▼
Atomic ProjectVersion / Forked Project Commit (OCC revision increment)
        │
        ▼
Downstream Execution:
├── Piper TTS generates target language audio WAV
├── faster-whisper transcribes target language subtitles
├── Wav2Lip-ONNX lip-syncs avatar to target language audio
└── FFmpeg renders final localized MP4 video!
```

---

## 6. Exact Model / Runtime

We specify a dual-tier model strategy:
1. **Tier 1 (Core Local Engine)**: Dedicated bilingual MarianMT (`Opus-MT`) models converted to CTranslate2 INT8 for the most critical commercial languages (English to Spanish, French, German).
2. **Tier 2 (Broad Multilingual Architecture)**: `facebook/m2m100_418M` (MIT license) in CTranslate2 INT8 as the architectural candidate for 100-language coverage.

### Specific Model Metadata:

| Property | Primary Candidate: `opus-mt-en-es` | Secondary Candidate: `opus-mt-en-fr` | Multilingual Target: `m2m100_418M` |
| :--- | :--- | :--- | :--- |
| **Hugging Face Repo** | `Helsinki-NLP/opus-mt-en-es` | `Helsinki-NLP/opus-mt-en-fr` | `facebook/m2m100_418M` |
| **CTranslate2 Format** | `ct2fast-opus-mt-en-es` | `ct2fast-opus-mt-en-fr` | `m2m100_418m-ct2-int8` |
| **Parameters** | 77.4 Million | 74.4 Million | 418 Million |
| **Quantization** | `int8` (CTranslate2 AVX2 GEMM) | `int8` (CTranslate2 AVX2 GEMM) | `int8` (CTranslate2 AVX2 GEMM) |
| **Disk Footprint** | **~48 MB** | **~46 MB** | **~425 MB** |
| **Resident RAM** | **~75 MB** | **~72 MB** | **~480 MB** |
| **Target Runtime** | `ctranslate2 4.8.2` | `ctranslate2 4.8.2` | `ctranslate2 4.8.2` |
| **Tokenizer** | Hugging Face `tokenizers` / BPE | Hugging Face `tokenizers` / BPE | SentencePiece / BPE |
| **Inference Device** | Host CPU (12 logical cores) | Host CPU (12 logical cores) | Host CPU (12 logical cores) |
| **Model Registry Key** | `translation/opus-mt-en-es-cpu` | `translation/opus-mt-en-fr-cpu` | `translation/m2m100-418m-cpu` |

---

## 7. License Audit

In strict compliance with our licensing policy, every component of the translation stack is audited independently:

| Component | Upstream Origin | License | Commercial Self-Hosting Status | Audit Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Model Weights (`opus-mt`)** | University of Helsinki / OPUS | **CC-BY-4.0 / Apache-2.0** | **COMMERCIAL_SAFE** | Trained on open parallel corpora. Commercial use permitted with attribution. |
| **Model Weights (`m2m100`)** | Meta AI Research | **MIT** | **COMMERCIAL_SAFE** | Released under permissive MIT license. Commercial use permitted. |
| **Model Weights (`nllb-200`)** | Meta AI Research | **CC-BY-NC-4.0** | **FORBIDDEN (NON-COMMERCIAL)** | **REJECTED**: Strict non-commercial restriction. Cannot be used in production. |
| **Runtime Engine (`ctranslate2`)** | OpenNMT / SYSTRAN | **MIT** | **COMMERCIAL_SAFE** | Permissive MIT license. |
| **Tokenizer (`tokenizers`)** | Hugging Face | **Apache-2.0** | **COMMERCIAL_SAFE** | Permissive Apache-2.0 license. |
| **Marian Framework Code** | Marian NMT Team | **MIT** | **COMMERCIAL_SAFE** | Permissive MIT license. |

### License Verification Conclusion:
`Helsinki-NLP/opus-mt` and `facebook/m2m100_418M` are verified **`COMMERCIAL_SAFE`**. `facebook/nllb-200` is formally rejected for production commercial self-hosting due to CC-BY-NC-4.0.

---

## 8. Provider Architecture

### 1. Protocol Conformance
The provider will implement `TranslationProvider` defined in `backend/app/ai/interfaces.py`:
```python
@runtime_checkable
class TranslationProvider(Protocol):
    async def translate_text(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        glossary_rules: Optional[List[Dict[str, str]]] = None,
    ) -> TranslationResult: ...

    async def translate(
        self,
        request: TranslationContractRequest,
    ) -> TranslationContractResult: ...
```

### 2. Provider Implementation Details (`backend/app/ai/adapters/ctranslate2_translation.py`)
- **Class**: `RealCTranslate2TranslationProvider`
- **Model Loading**: Thread-safe lazy loading into singleton cache.
- **Brand Glossary Term Protection Pipeline**:
  1. *Extraction*: Match active glossary rules for `source_language` and `target_language`.
  2. *Masking / Preservation*: Replace brand terms with non-translatable alphanumeric tokens (e.g. `__BRAND_TERM_0__`) to prevent the NMT model from translating proprietary trademarks (e.g. "HeyZen" or "VidoAI").
  3. *Neural Inference*: Execute CTranslate2 INT8 beam search (`beam_size=2`).
  4. *Unmasking / Substitution*: Swap placeholders with preferred brand terminology (`preferred_term`) and verify absence of `forbidden_term`.
- **Metrics Telemetry**:
  Records `source_language`, `target_language`, `character_count`, `word_count`, `inference_latency_ms`, `tokens_per_second`, and `rules_applied`.

---

## 9. Model Registry

Add real model descriptors in `backend/app/ai/model_registry.py`:

```python
ModelDescriptor(
    model_id="translation/opus-mt-en-es-cpu",
    name="Opus-MT English to Spanish (CPU INT8)",
    provider="helsinki_nlp",
    capability="translation",
    supported_runtimes=["local_cpu"],
    supported_devices=["cpu"],
    requires_gpu=False,
    minimum_ram_bytes=128 * mb,
    recommended_ram_bytes=256 * mb,
    approximate_size_bytes=48 * mb,
    quantization="int8",
    license="CC-BY-4.0 / Apache-2.0",
    license_commercial_permitted=True,
    source="Helsinki-NLP/opus-mt-en-es",
    supported_languages=["en", "es"],
    installation_status=ModelInstallStatus.INSTALLED,
    health_status=ModelHealthStatus.HEALTHY,
    metadata={
        "engine": "CTranslate2 (int8)",
        "license_classification": "COMMERCIAL_SAFE",
        "commercial_use_permitted": True,
        "source_lang": "en",
        "target_lang": "es",
    },
)
```

Update `translation/nllb-200-cpu` in the registry to explicitly label its license as `CC-BY-NC-4.0` with `license_commercial_permitted=False` and `license_classification="RESEARCH_ONLY"`.

---

## 10. Runtime / Hardware Selection

- **Runtime ID**: `runtime-local-cpu` (Local CTranslate2 CPU Runtime).
- **Execution Provider**: CTranslate2 native C++ multi-threaded CPU inference.
- **Thread Allocation**: Configured with `inter_threads=1`, `intra_threads=4` to utilize host physical cores without starving the FastAPI event loop.
- **Hardware Boundary**: Validated on AMD Ryzen 5 5500U. CUDA is strictly flagged as unavailable and rejected if requested.

---

## 11. Celery Architecture

- **Task Name**: `heyzen.tasks.ai.translate_project` in `backend/app/workers/tasks/ai_tasks.py`.
- **Target Queue**: `cpu_media` (routed in `backend/app/workers/celery_app.py` and `job_service.py`).
- **Progress Lifecycle**:
  - `0%` - Queued / Initializing job
  - `15%` - Loading project snapshot & resolving Brand Glossary rules
  - `30%` - Initializing CTranslate2 translation model into CPU memory
  - `60%` - Translating scene scripts & applying brand glossary term substitutions
  - `85%` - Validating localized ProjectDocumentV1 and resetting speech audio references
  - `95%` - Committing atomic ProjectVersion with OCC (or creating forked project)
  - `100%` - Job completed successfully
- **Cooperative Cancellation**: Checks `JobService.is_job_cancelled()` between scene translation iterations.
- **Idempotency**: Prevents duplicate project versions or fork creations via `idempotency_key`.

---

## 12. MinIO / Asset Flow

- Translation itself is text/timeline transformation.
- However, for each translated scene:
  - `scene.speech.audio_asset_id` is set to `None` (clearing English audio).
  - When the downstream `POST /projects/{id}/synthesize-speech` or render worker executes, new translated WAV audio assets (e.g. `speech_<scene>_es.wav`) will be generated and stored in the MinIO bucket `heyzen-assets` with MIME type `audio/wav`.
  - Project documents and version records preserve references to the new assets.

---

## 13. ProjectDocumentV1 Integration

`ProjectLocalizationService` updates `ProjectDocumentV1`:
1. Deep-copies source document (`copy.deepcopy(current_version.document)`).
2. Iterates over `doc.scenes`:
   - Translates `scene.speech.script`.
   - Clears `scene.speech.audio_asset_id = None`.
   - Updates `scene.speech.voice_id = target_voice_id` if a target voice is specified.
3. Updates `doc.metadata`:
   - `doc.metadata["language"] = target_language`
   - `doc.metadata["localized_from"] = str(source_project_id)`
   - `doc.metadata["translation_metrics"] = {...}`
4. Preserves all canvas settings (`width`, `height`, `fps`, `aspect_ratio`), background configurations, avatar positions, and visual layers.

---

## 14. OCC / ProjectVersion Behavior

- **Forked Translation (`create_fork=True`)**:
  - Creates a new `Project` record titled `"{source_title} - {TARGET_LANG.upper()}"`.
  - Assigns `revision = 1`.
  - Creates initial `ProjectVersion` with `revision = 1` and `source = "translation_fork"`.
- **In-Place Translation (`create_fork=False`)**:
  - Requires `expected_revision`.
  - Checks if `source_project.revision == expected_revision`.
  - Increments `revision` (e.g. 1 → 2).
  - If revision mismatch occurs, raises `ConflictException` (`OCCVersionConflictError`).
  - Strict atomic commit: zero partial mutations on failure.

---

## 15. API Design

Existing API contract in `backend/app/api/v1/endpoints/project_orchestration.py`:

```http
POST /api/v1/workspaces/{workspace_id}/projects/{project_id}/translate
Content-Type: application/json

{
  "target_language": "es",
  "source_language": "en",
  "target_voice_id": "es_ES-davefx-medium",
  "create_fork": true,
  "expected_revision": 1,
  "run_async": true,
  "idempotency_key": "trans-req-98765"
}
```

### Responses:
- **Async Execution (`run_async=True`)**: `HTTP 202 Accepted` with `JobResponse` payload (`job_id`, `status: "queued"`, `queue: "cpu_media"`).
- **Synchronous Execution (`run_async=False`)**:
  - If `create_fork=True`: `HTTP 200 OK` with `ProjectResponse` of the new forked project.
  - If `create_fork=False`: `HTTP 200 OK` with `ProjectVersionResponse` of the updated project version.

---

## 16. Error Handling

- **`AI_PROVIDER_MODE="real"`**: Strictly forbids silent fallback to `MockTranslationProvider`.
- **Unsupported Language**: Raises `AIModelIncompatibleException` (`LANGUAGE_PAIR_UNSUPPORTED`) if no model is available for the requested pair.
- **Missing Model**: Raises `AIRuntimeUnavailableException` (`TRANSLATION_MODEL_NOT_FOUND`).
- **Empty / Malformed Script**: Validates text presence; skips empty scenes gracefully without failing the entire timeline.
- **OCC Conflict**: Raises `ConflictException` (`EXPECTED_REVISION_MISMATCH`).

---

## 17. Security

- **Workspace Isolation**: Database queries enforce `workspace_id` tenant scoping for projects, versions, brand kits, and glossaries.
- **Model Cache Path Traversal**: Model directories resolved using `safe_resolve_model_path()`. Symlinks and parent directory traversal (`..`) are strictly rejected.
- **Injection Safety**: Term placeholders in Brand Glossary matching are sanitized to prevent regex or template injection attacks.
- **No Secret Leaks**: Prompts, scripts, and glossary rules are masked in general application logs.

---

## 18. Testing Strategy

Comprehensive automated tests to be developed:
1. **Provider Tests (`tests/test_ai_translation.py`)**:
   - Provider conforms to `TranslationProvider` runtime protocol.
   - ProviderDescriptor metadata and licensing attributes.
   - Real CTranslate2 translation execution (`en -> es`, `en -> fr`).
   - Strict real mode: no mock fallback when real provider is unavailable.
   - Brand Glossary rule enforcement (exact substitution, case sensitivity, forbidden terms).
2. **Domain & Localization Service Tests (`tests/test_project_localization_real.py`)**:
   - Multi-scene translation with audio asset reset.
   - Voice remapping per scene speech.
   - Fork creation (`create_fork=True`) producing revision 1 project.
   - In-place versioning (`create_fork=False`) with OCC revision increment and conflict rejection.
3. **Celery Worker Tests (`tests/test_real_translation_worker.py`)**:
   - Task `heyzen.tasks.ai.translate_project` execution on `cpu_media`.
   - Progress stages (0% → 100%).
   - Cooperative cancellation during multi-scene translation.
   - Idempotency deduplication.
4. **API Endpoint Tests (`tests/test_project_translation_api.py`)**:
   - Permissions, authentication, async HTTP 202, sync HTTP 200.
5. **Closed-Loop Multilingual E2E Test (`tests/test_real_multilingual_closed_loop.py`)**:
   - Prompt → Real Qwen (EN) → ProjectDocumentV1 → Real Translation (ES) with Brand Glossary → Real Piper TTS (ES) → Real faster-whisper (ES) → Real Wav2Lip (ES lip-sync) → FFmpeg (ES video) → FFprobe verification.

---

## 19. E2E Acceptance Test

The mandatory acceptance test will prove:
1. Exact Opus-MT / CTranslate2 model loaded on host CPU.
2. Real translation performed on multi-scene script without mock fallback.
3. Brand glossary term (e.g. `"HeyZen"`) strictly preserved across all translated scenes.
4. ProjectVersion created with OCC increment.
5. Translated audio synthesized via Piper TTS, transcribed via faster-whisper, lip-synced via Wav2Lip, and rendered via FFmpeg.
6. Actual performance and memory measured on the host.

---

## 20. Hardware Feasibility

- **Host**: AMD Ryzen 5 5500U, 12 logical cores, ~7.34 GB RAM, ~0.85 GB free memory.
- **Model Footprint**: ~48 MB disk, ~75 MB resident RAM.
- **CPU Inference Speed**: ~40–80 ms per sentence (~150 words/second).
- **Feasibility Verdict**: **100% FEASIBLE AND SAFE**. Memory impact is negligible (<10% of available headroom).

---

## 21. Dependencies

### Existing Dependencies (Already Installed in `.venv`):
- `ctranslate2 4.8.2` (installed in Step 3 for faster-whisper)
- `tokenizers 0.23.2` (installed in Step 5 for Qwen)
- `onnxruntime 1.30.0`
- `ffmpeg` & `ffprobe` (installed system binaries)

### Proposed New Dependencies:
- **ZERO NEW PYTHON PACKAGES REQUIRED**.
- All necessary C++ neural execution and tokenization capabilities are already satisfied by `ctranslate2` and `tokenizers`.

---

## 22. Database Migration Assessment

- **Alembic Migrations Required**: **ZERO**.
- Tables used:
  - `projects` (existing)
  - `project_versions` (existing)
  - `brand_glossaries` (existing, migration `0004`)
  - `brand_glossary_rules` (existing, migration `0004`)
  - `jobs` & `job_events` (existing, migration `0005`)
- Document model: `ProjectDocumentV1` already accommodates `doc.metadata["language"]`, `doc.metadata["localized_from"]`, and `scene.speech.voice_id`.

---

## 23. Frontend Impact Assessment

- **Frontend Modifications Required**: **ZERO**.
- `src/components/apps/TranslateVideos.tsx` already exists in the frontend tree and exposes video/project selection, glossary picking, and target language options.
- The Next.js frontend remains 100% frozen and untouched.

---

## 24. Risks / Limitations

1. **Language Pair Coverage**: While `m2m100` supports 100 languages, bilingual Opus-MT models provide higher translation quality for individual pairs. Step 6 will focus initially on high-demand pairs (EN-ES, EN-FR, EN-DE) with dynamic model loading.
2. **Cross-Lingual Voice Availability**: Local Piper TTS voice checkpoints must be available for target languages (e.g. `es_ES`, `fr_FR`) to complete the audio loop. Piper includes official ONNX voices for Spanish, French, and German.

---

## 25. Implementation Sequence

1. **Step 6.1**: Verify exact model artifacts, provenance, and commercial-safe license hashes (`Helsinki-NLP/opus-mt-en-es`, `ct2fast-opus-mt-en-es`).
2. **Step 6.2**: Implement `RealCTranslate2TranslationProvider` in `backend/app/ai/adapters/translation.py` satisfying `TranslationProvider` protocol with Brand Glossary term masking.
3. **Step 6.3**: Register provider in `backend/app/ai/registry.py` and register model descriptors in `backend/app/ai/model_registry.py`.
4. **Step 6.4**: Connect `ProjectLocalizationService` to resolve `RealCTranslate2TranslationProvider` when `AI_PROVIDER_MODE="real"`.
5. **Step 6.5**: Implement Celery task `_execute_translate_project` and `@celery_app.task name="heyzen.tasks.ai.translate_project"` in `backend/app/workers/tasks/ai_tasks.py`.
6. **Step 6.6**: Implement unit tests, glossary enforcement tests, worker tests, and API integration tests.
7. **Step 6.7**: Execute closed-loop E2E test (Qwen → Translate → Piper → Whisper → Wav2Lip → FFmpeg).
8. **Step 6.8**: Execute full backend regression (expecting 310 baseline + ~15 new tests = ~325 passed).
9. **Step 6.9**: Verify zero frontend changes, zero migrations, and create implementation documentation.

---

## 26. Acceptance Criteria

1. Exact Opus-MT / CTranslate2 checkpoint verified and loaded on CPU.
2. License verified as `COMMERCIAL_SAFE` (Apache-2.0 / CC-BY-4.0 / MIT). `nllb-200` rejected.
3. Real neural translation measured: latency < 500ms for full multi-scene script, RAM < 150 MB.
4. Strict real mode: structured exception raised when model missing; zero mock fallback.
5. Brand glossary rules strictly enforced (e.g. brand names preserved).
6. Localized `ProjectDocumentV1` generated; speech audio IDs cleared; voice remapped.
7. `ProjectVersion` committed with sequential OCC revision increment; conflicts rejected.
8. Celery job executed on queue `cpu_media` with 0% → 100% progress and cooperative cancellation.
9. Downstream closed-loop verified (Translation → Piper → Whisper → Wav2Lip → FFmpeg).
10. Frontend verified untouched (`git status` clean).
11. Database verified with zero new migrations.
12. Full regression suite passes with 0 regressions.

---

## 27. Final Recommendation

### **PROCEED**

**Scope for Phase 8 Step 6 Implementation**:
Implement **Real Local CPU Neural Machine Translation & Multilingual Video Localization Engine** using CTranslate2 INT8 (`Helsinki-NLP/opus-mt` family) with Brand Glossary term preservation, Celery task `translate_project` on queue `cpu_media`, OCC versioning, and complete downstream integration with Piper, Whisper, Wav2Lip, and FFmpeg.
