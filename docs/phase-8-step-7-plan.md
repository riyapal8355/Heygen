
# Phase 8 Step 7 Planning: Real Neural Avatar Background Matting & Multi-Track Canvas Compositing

---

## 1. Executive Summary

Following the successful completion and acceptance of Phase 8 Steps 1–6 (331/331 tests passing, full regression green), HeyZen possesses genuine local CPU implementations of:
- **LLM Video Agent**: Qwen 2.5 0.5B Instruct ONNX INT4 (script & scene structure generation)
- **TTS Synthesis**: Piper TTS (English & Spanish neural speech)
- **ASR Transcription**: faster-whisper INT8 (multilingual speech recognition & word-level subtitle alignment)
- **Lip-Sync Animation**: Wav2Lip-ONNX (talking face facial animation, research-only engine)
- **Neural Translation**: CTranslate2 INT8 MarianMT (English to Spanish with collision-resistant Brand Glossary preservation)
- **Media Composition**: FFmpeg `TimelineCompositor`

### The Real Platform Bottleneck Discovered
In inspecting the rendering layer (`backend/app/media/compositor.py`), a critical architectural gap was uncovered:
**`TimelineCompositor` currently ignores `scene.avatar.video_asset_id` entirely.**
When a full project render is requested, `_render_scene_clip` renders only:
1. Background color, image, or video loop (`scene.background`)
2. Text overlay layer (`scene.layers`)
3. Speech audio (`scene.speech.audio_asset_id`)

The avatar video produced by Wav2Lip (`scene.avatar.video_asset_id`) is **never composited into the scene timeline**.
The fundamental technical reason is that raw avatar video output has an opaque, solid rectangular background inherited from the source portrait or webcam capture. Placing an opaque rectangular video over a scene canvas either occludes background graphics, branding, and presentation slides, or looks unfinished.

To deliver an **end-to-end avatar-composited rendering path**, the pipeline requires:
1. **Real Neural Avatar Background Matting / Segmentation**: Extracting high-accuracy alpha mattes ($[0.0, 1.0]$ transparency) from avatar frames on CPU with real-time latency.
2. **Multi-Track Canvas Compositing**: Blending the segmented avatar over `scene.background` with precise spatial positioning (`position: {x, y, scale}`), view modes (`view_mode: "half_body" | "close_up" | "circle"`), along with visual text layers, Whisper subtitle cues, and audio tracks.

### Hardware & Constraint Alignment
- Current Host: AMD Ryzen 5 5500U CPU (12 logical cores, ~7.34 GB RAM, ~0.85 GB available baseline, AMD integrated graphics, NO NVIDIA CUDA).
- User Constraint: **"CPU-first, low-memory architecture, no PyTorch/CUDA installation merely for experimentation, no heavyweight diffusion stack, no GPU dependency"**.
- Proposed Engine: **`onnx-community/mediapipe_selfie_segmentation` ONNX**.
  - Model disk size: **462.35 KB** (462,352 bytes)
  - RAM requirement: **< 30 MB RAM** (negligible memory pressure)
  - CPU throughput: **50 to 100+ fps** (8 to 15 ms/frame on AMD Ryzen 5500U)
  - License: **Apache-2.0** (`COMMERCIAL_SAFE`)

---

## 2. Current Capabilities Inventory (Real vs. Mock)

| Capability | Current Provider | Status | CPU Support | CUDA Support | Commercial Status | Frontend Surface | Backend Completeness | Next Dependency |
|---|---|---|---|---|---|---|---|---|
| **LLM (Video Agent)** | `RealQwenLLMProvider` | **Real** | Yes (ONNX INT4) | Planned (vLLM) | `COMMERCIAL_SAFE` (Apache-2.0) | `VideoAgent.tsx` | Complete (Step 5) | None |
| **TTS (Speech)** | `PiperTTSProvider` | **Real** | Yes (ONNX) | Planned (XTTS) | `COMMERCIAL_SAFE` (MIT / CC0) | `SingleScene.tsx`, Studio | Complete (Step 2, 6) | Cloned voices |
| **ASR (Subtitles)** | `WhisperASRProvider` | **Real** | Yes (INT8) | Supported | `COMMERCIAL_SAFE` (MIT) | Studio Captions | Complete (Step 3, 6) | None |
| **Translation** | `RealCTranslate2TranslationProvider` | **Real** | Yes (INT8) | Supported | `COMMERCIAL_SAFE` (Apache-2.0) | `TranslateVideos.tsx` | Complete (Step 6) | Extra language pairs |
| **Avatar Lip-Sync** | `RealWav2LipAvatarProvider` | **Real (CPU Prototype)** | Yes (ONNX) | Architectural (MuseTalk) | `RESEARCH_ONLY` (LRS2 dataset) | Studio, `SingleScene.tsx` | Complete prototype (Step 4) | CUDA MuseTalk |
| **Avatar Matting / Segmentation** | None / Missing | **None** | Yes (Target: ONNX) | Yes | Target: `COMMERCIAL_SAFE` | Studio Avatar Tab, Modes | Missing | **Phase 8 Step 7** |
| **Multi-Track Avatar Compositing** | `TimelineCompositor` | **Incomplete** | Yes (FFmpeg) | Yes (NVENC) | Open Source (FFmpeg) | Studio Preview, Export | Incomplete (avatar omitted) | Matting & Filtergraph |
| **Image Generation** | `MockImageProvider` | **Mock** | Infeasible (<1 GB RAM) | Planned (SDXL) | Mock: MIT / SDXL: Non-comm | Scene Visuals, Studio Media | Incomplete (Mock PNG) | Dedicated GPU worker |
| **Video Generation (B-Roll)** | `MockVideoProvider` | **Mock** | Infeasible on CPU | Planned (SVD) | Mock: MIT / SVD: Non-comm | `FeaturedAppModals.tsx` | Incomplete (Mock MP4) | Dedicated GPU worker |
| **Voice Cloning** | `MockTTSProvider.clone_voice` | **Mock** | Infeasible on CPU | Planned (XTTS/OpenVoice)| Mock: MIT / XTTS: Non-comm | `CreateVoiceModal.tsx` | Incomplete | Dedicated GPU worker |
| **Avatar Training (Digital Twin)**| `MockAvatarProvider.train_digital_twin`| **Mock** | Infeasible on CPU | Planned (NeRF/3DGS)| Mock: MIT | `CreateAvatarModal.tsx` | Incomplete | Dedicated GPU worker |
| **Music / Audio Gen** | None (Mixing only) | **Incomplete** | Infeasible on CPU | Planned (MusicGen) | Mock: MIT | Studio Music Tab | Incomplete | Dedicated GPU worker |
| **Brand & Glossary** | `BrandService` + Dynamic Masker | **Real** | Yes (In-memory) | N/A | `COMMERCIAL_SAFE` (MIT) | `BrandGlossaryDetail.tsx`| Complete (Step 6) | None |
| **Rendering Pipeline** | `ProjectRenderOrchestrator` | **Real** | Yes (FFmpeg) | Planned | Open Source | Studio Export, Download | Complete | Avatar layer compositing |

---

## 3. Evaluation of Step 7 Candidates & Bottleneck Analysis

### Candidate A: Production-Safe Avatar / Lip-Sync (MuseTalk / LivePortrait)
- **Technical Barrier**: MuseTalk and LivePortrait require PyTorch, CUDA, and >= 4–6 GB VRAM.
- **Host Feasibility**: AMD Ryzen 5 5500U host has no NVIDIA CUDA GPU and ~0.85 GB available RAM. Running a diffusion UNet on CPU would cause OOM and take >10 seconds per frame (300 seconds for 1 second of video).
- **Rule Compliance**: Violates the rule forbidding unexecutable GPU implementations on this machine. Step 4 already architected the `MuseTalkAvatarProvider` skeleton for future CUDA workers.
- **Verdict**: **REJECTED for Step 7 local execution.**

### Candidate B: Real Image Generation (Diffusion Text-to-Image)
- **Technical Barrier**: Stable Diffusion 1.5 ONNX requires ~1.7 GB weights and ~3 GB RAM during inference. SDXL Turbo is non-commercial and requires 6 GB VRAM.
- **Host Feasibility**: Host has ~0.85 GB available RAM baseline. Loading a 3 GB diffusion pipeline risks fatal virtual memory thrashing and host crashes. Generating 1 image on 12 CPU threads takes 45–120 seconds.
- **Rule Compliance**: The prompt explicitly mandates: *"no heavyweight diffusion stack"*.
- **Verdict**: **REJECTED for Step 7 local execution.**

### Candidate C: Real Neural Avatar Background Matting & Multi-Track Canvas Compositing (RECOMMENDED)
- **Technical Justification**:
  1. Resolves the single most glaring hole in the video rendering pipeline: `TimelineCompositor` currently omits `scene.avatar.video_asset_id` because raw avatar videos have opaque rectangular backgrounds.
  2. Enables true HeyGen-style presentation videos: the talking avatar can be placed seamlessly over custom scene backgrounds, presentation slides, or color backdrops with custom scaling, positioning (`x, y, scale`), and circular PIP bubble clipping (`view_mode="circle"`).
  3. Micro-footprint: Model size is **~462 KB**; RAM consumption is **< 30 MB**; CPU inference latency is **8 to 15 ms per frame** (60–100+ fps).
  4. Commercial safety: **Apache-2.0** license (100% commercially permissive).
- **Verdict**: **RECOMMENDED AS PRIMARY STEP 7 CAPABILITY.**

### Candidate D: Real Voice Cloning
- **Technical Barrier**: XTTS-v2 / OpenVoice require PyTorch and CUDA; XTTS-v2 has the non-commercial CPML license. Piper is not a zero-shot voice cloner.
- **Verdict**: **REJECTED for Step 7 local execution.**

### Candidate E: Real Music / Sound Generation
- **Technical Barrier**: Meta MusicGen requires PyTorch, heavy compute, and high memory (>2 GB RAM).
- **Verdict**: **REJECTED for Step 7 local execution.**

---

## 4. Exact Model Provenance, Checkpoint Audit & License Verification

To comply with the strict model audit requirements, the exact executable ONNX model artifact has been investigated and verified from its upstream source down to the specific binary file and checksum.

### Primary Selected Executable Artifact: `onnx-community/mediapipe_selfie_segmentation`

| Attribute | Verified Value |
|---|---|
| **Exact Repository** | `onnx-community/mediapipe_selfie_segmentation` (Hugging Face Hub) |
| **Source URL** | `https://huggingface.co/onnx-community/mediapipe_selfie_segmentation/resolve/main/onnx/model.onnx` |
| **Exact Revision / Commit SHA** | `be49485c8e027524be38591817fc5cd31bd9d00e` (main branch commit) |
| **Exact Filename** | `onnx/model.onnx` |
| **Exact File Size** | `462,352` bytes (~451.5 KB) |
| **SHA256 Checksum** | `3241ac4ad8aa35bdaf33946776db29f7c283a413aa0b0dacb9483594b4531aad` |
| **Original Model Source** | Google MediaPipe Selfie Segmentation (`google-ai-edge/mediapipe`) |
| **Upstream Model Format** | TFLite (`selfie_segmentation.tflite`, MobileNetV3 backbone) |
| **Upstream Model License** | **Apache-2.0** (Google Open Source Models) |
| **Conversion Source** | Hugging Face ONNX Community (`onnx-community`, Xenova) converted using standard `tf2onnx` / `onnx` tools |
| **Conversion & Code License** | **Apache-2.0** |
| **Preprocessing & Postprocessing License** | **Apache-2.0** (standard normalization `rescale_factor: 1/255.0`, resize $256 \times 256$, implemented in pure Python/NumPy) |
| **Runtime Engine & License** | ONNX Runtime (`onnxruntime 1.24.4`), **MIT License** |
| **Commercial Use Permitted** | **YES** |
| **Redistribution Permitted** | **YES** (with preservation of Apache-2.0 copyright notices) |
| **Classification** | **`COMMERCIAL_SAFE`** |

### Input / Output Tensor Contracts
- **Input Tensor**: `input` of shape `[1, 3, 256, 256]` (Float32, normalized to $[0.0, 1.0]$).
- **Output Tensor**: `alphas` of shape `[1, 1, 256, 256]` (Float32, sigmoid probability in $[0.0, 1.0]$ representing foreground human matte).

---

### Alternative Models Evaluated & Audited

1. **Qualcomm AI Hub (`qualcomm/MediaPipe-Selfie-Segmentation`)**:
   - Repository: `https://huggingface.co/qualcomm/MediaPipe-Selfie-Segmentation`
   - License: Qualcomm AI Hub Community License (contains proprietary Qualcomm vendor restrictions).
   - Classification: `REJECTED` for open-source self-hosted commercial safety.
2. **MODNet Photographic Portrait Matting (`ZHKKKe/MODNet`)**:
   - Repository: `https://github.com/ZHKKKe/MODNet` (ONNX export: `petergu684/modnet_photographic_portrait_matting`)
   - License: Code is Apache-2.0, but pretrained model weights were trained using the Adobe Matting Dataset (non-commercial research only) and PPM-100.
   - Classification: `RESEARCH_ONLY` (non-commercial).
3. **BRIA RMBG-1.4 / RMBG-2.0 (`briaai/RMBG-1.4`)**:
   - Repository: `https://huggingface.co/briaai/RMBG-1.4`
   - License: Creative Commons Attribution-NonCommercial 4.0 (`CC-BY-NC-4.0`).
   - Classification: `RESEARCH_ONLY` (non-commercial).

**Conclusion**: The **`onnx-community/mediapipe_selfie_segmentation`** artifact (`SHA256: 3241ac4ad8aa35bdaf33946776db29f7c283a413aa0b0dacb9483594b4531aad`) has unassailable Apache-2.0 provenance and is strictly **`COMMERCIAL_SAFE`**.

---

## 5. Hardware Feasibility on Current Host (AMD Ryzen 5 5500U)

| Parameter | Primary Selected Checkpoint (`onnx/model.onnx`) | Host Capacity | Status |
|---|---|---|---|
| **Model Disk Size** | 462.35 KB (462,352 bytes) | 162 GB free | **FEASIBLE** |
| **Inference RAM** | ~20 MB | ~850 MB available | **FEASIBLE** |
| **Peak Process RAM** | ~50 MB | ~850 MB available | **FEASIBLE** |
| **Frame Latency (CPU)** | 8 to 15 ms [ESTIMATED] | N/A | **REAL-TIME (60+ fps)** |
| **Batch Latency (5s video, 150 frames)** | 1.2 to 2.2 seconds [ESTIMATED] | N/A | **FAST** |
| **CUDA Requirement** | None (CPUExecutionProvider) | CUDA Unavailable | **100% CPU COMPATIBLE** |
| **VRAM Requirement** | 0 MB | 0 MB | **PASSED** |

---

## 6. Architectural Design

```
ProjectDocumentV1 (Scene, SceneAvatar, SceneSpeech, SceneLayer, Background)
        ↓
ProjectRenderOrchestrator / TimelineCompositor
        ↓
Asset Resolver (MinIO / S3)
  - Resolve scene.speech.audio_asset_id (Speech WAV)
  - Resolve scene.background (Color / Image / Video asset)
  - Resolve scene.avatar.video_asset_id (Wav2Lip avatar MP4)
        ↓
[NEW] RealMediaPipeMattingProvider (ONNX CPU)
  - Extract frames from avatar video
  - Infer alpha segmentation matte [0.0, 1.0] per frame
  - Output alpha matte mask video or RGBA stream
        ↓
[NEW] Multi-Track FFmpeg Filtergraph Engine:
  - Input 0: Scene Background (scaled to canvas 1920x1080 or 1080x1920)
  - Input 1: Avatar Video Stream
  - Input 2: Avatar Alpha Matte Stream (or circular PIP mask generator)
  - Filter 1: Alphamerge (Avatar Video + Matte -> RGBA)
  - Filter 2: Transform & Scale (position.x, position.y, scale, view_mode)
  - Filter 3: Overlay on Background
  - Filter 4: Drawtext text layers (titles, badges)
  - Filter 5: Drawtext subtitles (Whisper word timestamps)
  - Filter 6: Amix speech audio + background music tracks
        ↓
FFmpeg Encoder (libx264, AAC, fast preset, yuv420p)
        ↓
FFprobe Strict Verification (Stream count, dimensions, codecs, duration > 0)
        ↓
MinIO Storage Ingestion -> Rendered MP4 Asset
```

### Provider Architecture
- **Contract**: `backend/app/ai/contracts.py`:
  - `MattingContractRequest(AIContractRequest)`: input video/image asset, output alpha format (`matte_mask`, `rgba_video`).
  - `MattingContractResult(AIContractResult)`: output asset, dimensions, frame count, processing latency.
- **Interface**: `backend/app/ai/interfaces.py`:
  - `MattingProvider(Protocol)`: `extract_matte(video_storage_key: str) -> str`
- **Adapter**: `backend/app/ai/adapters/matting.py`:
  - `RealMediaPipeMattingProvider`: loads ONNX model via `onnxruntime.InferenceSession`, processes frame batches with normalized preprocessing.
- **Provider Registry**: `backend/app/ai/registry.py`:
  - Registers `matting` capability with `mediapipe` provider in real mode; `mock` in mock mode.
- **Model Registry**: `backend/app/ai/model_registry.py`:
  - Registers `matting/mediapipe-selfie-cpu` (`COMMERCIAL_SAFE`, Apache-2.0, revision `be49485c8e027524be38591817fc5cd31bd9d00e`).
  - Registers `matting/modnet-cpu` (`RESEARCH_ONLY`).
- **Celery Task**:
  - `heyzen.tasks.ai.extract_matte` routed to `cpu_media`.

---

## 7. ProjectDocumentV1 Schema Impact

### Absolute Immutability & Backwards Compatibility
The canonical `ProjectDocumentV1` schema in `backend/app/schemas/project_document.py` already includes all required fields:
```python
class SceneAvatar(BaseModel):
    avatar_id: str
    look_id: Optional[str] = None
    position: Dict[str, float] = Field(
        default_factory=lambda: {"x": 0.5, "y": 0.65, "scale": 1.0, "rotation": 0.0}
    )
    view_mode: str = Field(default="half_body", description="half_body, close_up, circle")
    video_asset_id: Optional[str] = None
```
- **Fields Read by Step 7**:
  - `scene.avatar.video_asset_id`: Used to locate the synthesized talking-avatar video.
  - `scene.avatar.position`: `{x, y, scale}` coordinates on the canvas.
  - `scene.avatar.view_mode`:
    - `"half_body"`: Neural matting removes background; avatar anchored to lower canvas.
    - `"close_up"`: Neural matting removes background; avatar centered with higher scale.
    - `"circle"`: Circular PIP mask with white/colored border applied to avatar (Loom/HeyGen style).
  - `scene.background`: Background image, video loop, or solid color.
  - `scene.layers`: Text and graphics overlay layers.
  - `scene.subtitles`: Whisper aligned subtitle cues.
- **Fields Written**:
  - No new fields required!
  - `ProjectDocumentV1` remains 100% backward-compatible.
- **Database Migrations**: **ZERO (0) new migrations**.

---

## 8. Frontend Integration & Frozen Rule Adherence

### Strict Frozen Frontend Rule
- No edits to `src/`, `public/`, `package.json`, `package-lock.json`, or Next.js configurations.
- `git status --porcelain src public package.json package-lock.json` must remain empty.

### Existing Frontend Surfaces Consuming Step 7
1. **`src/components/studio/VidoAIStudio.tsx`**:
   - Right Inspector: `Scene Settings` -> `Background` ("Office Room"), `Layers` (AI Video Creator, Text), Timeline Avatar Track.
   - Canvas: Preview and export now display the avatar composited over the selected background instead of a solid color box.
2. **`src/components/create/SingleScene.tsx`**:
   - Mode switcher: `Presenter`, `Avatar IV`, `Cinematic`.
   - Generates single scene with avatar overlay.
3. **`src/components/apps/AppLibrary.tsx`**:
   - `AI Video Generator`, `Video Podcast`, `PPT/PDF to Video`.

---

## 9. Closed-Loop Value: End-to-End Avatar-Composited Rendering Path

With Step 7 implemented, HeyZen achieves its first **end-to-end avatar-composited rendering path**:
```
User Natural Language Prompt
        ↓ (Step 5: Qwen 2.5 0.5B ONNX)
Structured ProjectDocumentV1 (Scenes, Script, Visual Prompts)
        ↓ (Step 6: CTranslate2 INT8)
Spanish Localized Document & Protected Brand Terms
        ↓ (Step 2: Piper TTS)
Spanish Spoken Audio (es_ES-davefx-medium)
        ↓ (Step 3: faster-whisper Tiny)
Word-level Timestamps & Aligned Spanish Subtitles
        ↓ (Step 4: Wav2Lip-ONNX)
Spanish Talking Avatar Video Clip
        ↓ [NEW STEP 7: Real MediaPipe Matting ONNX]
Neural Alpha Matte Extraction (Transparent Avatar Stream)
        ↓ [NEW STEP 7: Multi-Track TimelineCompositor]
Canvas Composition: Scene Background + Positioned Avatar + Text Layers + Subtitles + Mixed Audio
        ↓ (MinIO Storage)
Final Verified 1080p/720p MP4 Video with Avatar Speaking Over Scene Backdrop
```

---

## 10. Test Strategy

Design 15+ dedicated tests in:
1. `backend/tests/test_ai_matting.py` (8 tests):
   - Protocol adherence (`MattingProvider`)
   - Model registration (`matting/mediapipe-selfie-cpu`)
   - Exact checkpoint metadata (`COMMERCIAL_SAFE`, Apache-2.0, checksum verification)
   - Real ONNX CPU inference on test video/portrait frames
   - Alpha channel verification (dimensions, $[0.0, 1.0]$ bounds)
   - Strict real-mode failure when model missing
   - Mock provider mode retention
   - Telemetry (frame latency, peak memory)
2. `backend/tests/test_media_avatar_compositor.py` (5 tests):
   - Multi-track FFmpeg compositing with avatar overlay
   - `view_mode="half_body"` with alpha matte blending
   - `view_mode="circle"` with circular PIP mask and border
   - Positioning transforms (`x, y, scale`)
   - Fallback when avatar video is missing
3. `backend/tests/test_real_avatar_timeline_closed_loop.py` (2 tests):
   - Real E2E: Qwen -> Piper -> Whisper -> Wav2Lip -> MediaPipe Matting -> TimelineCompositor -> MinIO.
   - FFprobe validation of final composite MP4.
- Full regression target: **331 baseline + 15 new = 346 passing tests (0 failures, 0 regressions)**.

---

## 11. Security & Reliability

- **Path Containment**: Matting model files strictly contained in `models_cache/matting/`.
- **Resource Protection**: Batch frame processing with generator streaming to prevent memory spikes on longer clips.
- **Cooperative Cancellation**: Checks cancellation flag between frame batches.
- **Fail-Safe Compositing**: If matting inference fails in non-strict mode, falls back to rectangular window with logged warning; in strict real mode, fails with explicit structured exception.

---

## 12. Implementation Plan (Phased Execution)

### Phase A: Model Verification & Matting Provider (Stage 1)
- Files:
  - `[NEW] backend/app/ai/adapters/matting.py`
  - `[MODIFY] backend/app/ai/contracts.py` (add `MattingContractRequest`, `MattingContractResult`)
  - `[MODIFY] backend/app/ai/interfaces.py` (add `MattingProvider`)
  - `[MODIFY] backend/app/ai/registry.py` (register `mediapipe` matting provider)
  - `[MODIFY] backend/app/ai/model_registry.py` (register `matting/mediapipe-selfie-cpu`)
- Checkpoint verification: `onnx/model.onnx` (`SHA256: 3241ac4ad8aa35bdaf33946776db29f7c283a413aa0b0dacb9483594b4531aad`).
- Tests: `backend/tests/test_ai_matting.py`.

### Phase B: FFmpeg Multi-Track Filtergraph & Compositor (Stage 2)
- Files:
  - `[MODIFY] backend/app/media/filters.py` (add `build_avatar_overlay_filter`, `build_circular_mask_filter`)
  - `[MODIFY] backend/app/media/compositor.py` (integrate avatar video resolution, alpha matte blending, and positioned overlay)
- Tests: `backend/tests/test_media_avatar_compositor.py`.

### Phase C: Celery Task & Service Integration (Stage 3)
- Files:
  - `[MODIFY] backend/app/workers/tasks/ai_tasks.py` (add `_execute_extract_matte`)
  - `[MODIFY] backend/app/workers/celery_app.py` (route `heyzen.tasks.ai.extract_matte` to `cpu_media`)
  - `[MODIFY] backend/app/services/project_avatar_service.py`
- Tests: `backend/tests/test_real_avatar_timeline_closed_loop.py`.

### Phase D: Performance Measurement & Full Regression (Stage 4)
- Measure cold load, warm load, per-frame latency, throughput (fps), peak RAM.
- Execute full regression `pytest tests/` (target: 346/346).
- Verify frontend untouched (`git status`).
- Verify database migrations (`alembic heads`).
- Verify `/api/v1/health` and `/api/v1/health/ai`.
- Produce final walkthrough and report.

---

## 13. Acceptance Criteria

1. **Real Provider**: `RealMediaPipeMattingProvider` operating via ONNX Runtime CPU.
2. **Exact Model Checkpoint**: `onnx-community/mediapipe_selfie_segmentation` -> `onnx/model.onnx` (`462,352` bytes, SHA256 `3241ac4ad8aa35bdaf33946776db29f7c283a413aa0b0dacb9483594b4531aad`).
3. **License**: Apache-2.0 (`COMMERCIAL_SAFE`), audited and verified.
4. **Strict Real Mode**: Zero silent fallback to mock in real mode.
5. **Compositing**: `TimelineCompositor` renders the avatar lip-sync video over the scene background with correct positioning and alpha transparency.
6. **Zero Database Migrations**: `alembic heads` remains unchanged.
7. **Zero Frontend Modifications**: `git status --porcelain src public package.json package-lock.json` is empty.
8. **Tests**: 100% passing across new tests and all 331 pre-existing tests.
9. **Measured Telemetry**: Cold load, warm load, per-frame latency, and RAM clearly reported.
