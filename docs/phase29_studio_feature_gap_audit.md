# Phase 29: Studio Editor Feature Gap Audit

**Date**: 2026-09-19  
**Alembic Head**: `0006_orchestration_jobs`  
**Scope**: Exhaustive audit of all visible Studio features, document model capabilities, backend services, assets, timeline tracks, and compositor rendering.  
**Constraint**: **AUDIT ONLY — ZERO CODE MODIFICATIONS, ZERO DATABASE MIGRATIONS, ZERO DEPENDENCY CHANGES**.

---

## 1. Executive Summary & Current Studio State

Phase 28 established the foundational end-to-end pipeline connecting:
- Scene script authoring
- Voice selection (Piper & Kokoro local TTS)
- Avatar selection (Wav2Lip CPU prototype & MuseTalk GPU)
- Asynchronous AI speech synthesis (MinIO WAV assets)
- Asynchronous talking-avatar video generation (MinIO MP4 assets)
- Basic 4-track timeline visualization (Scene, Avatar, Script, Speech)
- Timeline composition and final video rendering (`TimelineCompositor` generating 1080p MP4)
- Version control under Optimistic Concurrency Control (OCC `expected_revision`).

However, **the Studio editor UI is currently an incomplete shell for non-avatar editing workflows**.
Multiple visible tool icons on the primary navigation rail (Music, Captions, Text, Elements, Media, Brand Kit, Transitions) do not open dedicated panels or handlers. Instead, they silently fall back to the generic Script & Scene inspector tab. Furthermore, while the backend architecture and `ProjectDocumentV1` schema already possess robust representations for background music mixing, Whisper ASR transcription, and canvas layers, these capabilities have not been wired into the user-facing Studio editing canvas or timeline.

---

## 2. Comprehensive Studio Feature Matrix

The following table audits every visible and underlying Studio editing feature against all 12 evaluation criteria:

| Feature | UI Exists | UI Functional | Project State | Backend | Asset | Timeline | Compositor | Render | Status |
|---|---|---|---|---|---|---|---|---|---|
| **Script** | Yes | Yes | Yes | Yes | N/A | Yes | Yes | Yes | **Complete (100%)** |
| **Voice** | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | **Complete (100%)** |
| **Avatar** | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | **Complete (100%)** |
| **Speech** | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | **Complete (100%)** |
| **Music** | Partial | No | Yes | Yes | Yes | No | Yes | Yes | **Gap (25%)** |
| **Captions** | Partial | No | Yes | Yes | N/A | No | Partial | Partial | **Gap (30%)** |
| **Text** | Partial | No | Yes | Yes | N/A | No | Partial | Partial | **Gap (20%)** |
| **Elements** | Partial | No | Yes | Yes | N/A | No | No | No | **Gap (10%)** |
| **Images** | No | No | Yes | Yes | Yes | No | No | No | **Gap (10%)** |
| **Media** | Partial | No | Yes | Yes | Yes | No | Partial | Partial | **Gap (30%)** |
| **Background** | Partial | Partial | Yes | Yes | Yes | No | Yes | Yes | **Partial (50%)** |
| **Stickers** | No | No | Yes | Yes | Yes | No | No | No | **Gap (5%)** |
| **Logos** | Partial | No | Yes | Yes | Yes | No | No | No | **Gap (15%)** |
| **Shapes** | No | No | Yes | Yes | N/A | No | No | No | **Gap (5%)** |
| **Overlays** | No | No | Yes | Yes | Yes | No | No | No | **Gap (10%)** |
| **Scene duration** | Yes | Yes | Yes | Yes | N/A | Yes | Yes | Yes | **Complete (100%)** |
| **Scene transitions** | Yes | Yes | Yes | Yes | N/A | No | Partial | Partial | **Partial (60%)** |
| **Timeline** | Yes | Yes | Yes | Yes | N/A | Yes | Yes | Yes | **Partial (60%)** |
| **Preview** | Yes | Yes | Yes | Yes | Yes | Yes | N/A | N/A | **Partial (80%)** |
| **Upload** | Modal | Modal | Yes | Yes | Yes | N/A | N/A | N/A | **Gap (40%)** |
| **Media library** | Modal | Modal | Yes | Yes | Yes | N/A | N/A | N/A | **Gap (40%)** |
| **Export** | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | **Complete (100%)** |
| **Render** | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | **Complete (100%)** |
| **Undo / Redo** | Yes (Icon) | No | No | Partial | N/A | N/A | N/A | N/A | **Static (15%)** |
| **Duplicate** | Yes | Yes | Yes | Yes | N/A | Yes | Yes | Yes | **Complete (100%)** |
| **Delete** | Yes | Yes | Yes | Yes | N/A | Yes | Yes | Yes | **Complete (100%)** |
| **Reorder** | Yes | Yes | Yes | Yes | N/A | Yes | Yes | Yes | **Complete (100%)** |

---

## 3. ProjectDocumentV1 Capability Analysis

Authoritative Schema Reference: [`backend/app/schemas/project_document.py`](file:///d:/HeyGen/video-ai-tools/backend/app/schemas/project_document.py)

`ProjectDocumentV1` is stored as structured JSONB in PostgreSQL (`project_versions.document`). It enforces `schema_version = 1`.

### Supported Document Elements
- **Music**: Fully supported by `ProjectDocumentV1.audio_tracks: List[AudioTrack]`.  
  Fields: `id: str`, `asset_id: Optional[str]`, `name: str`, `volume: float` (0.0-2.0), `start_time: float`, `duration: Optional[float]`, `fade_in_duration: float`, `fade_out_duration: float`, `loop: bool`.
- **Captions / Subtitles**: Fully supported by `Scene.subtitles: List[Dict[str, Any]]`.  
  Structured payload: `[{ "id": int, "start": float, "end": float, "text": str, "words": [...] }]`.
- **Text Elements**: Supported by `Scene.layers: List[SceneLayer]`.  
  Fields: `id: str`, `type: "text"`, `name: str`, `start_time: float`, `end_time: float`, `transform: Dict[str, Any]`, `content: Dict[str, Any]`.
- **Image Elements**: Supported by `Scene.layers: List[SceneLayer]`.  
  Fields: `type: "image"`, `content: { "asset_id": "...", "url": "..." }`.
- **Overlays**: Supported by `Scene.layers: List[SceneLayer]` with `type: "image" | "video" | "sticker"`.
- **Background**: Supported by `Scene.background: Dict[str, Any]`.  
  Supports `{"type": "color", "value": "#0F172A"}`, `{"type": "image", "asset_id": "..."}`, and `{"type": "video", "asset_id": "..."}`.
- **Shapes**: Supported by `Scene.layers: List[SceneLayer]` with `type: "shape"`, `content: { "shape_type": "rect" | "circle", "fill": "..." }`.
- **Media Clips**: Supported by `Scene.layers: List[SceneLayer]` with `type: "video"`.
- **Element Timing**: Supported by `SceneLayer.start_time: float` and `SceneLayer.end_time: float`.

### Unsupported / Schemaless Gaps in ProjectDocumentV1
- **Element Position, Dimensions, Opacity, Rotation**:
  Currently, `SceneLayer.transform` is defined as a generic unconstrained dictionary:  
  `transform: Dict[str, Any] = Field(default_factory=dict)`  
  Unlike `SceneAvatar.position` which specifies explicit `{ x, y, scale, rotation }`, `SceneLayer` has no typed Pydantic submodel for transforms.
- **Minimum Model Correction (No Migration Needed)**:
  Because `project_versions.document` is a JSONB column, typed Pydantic models for `LayerTransform` (specifying `x: float = 0.5`, `y: float = 0.5`, `width: Optional[float] = None`, `height: Optional[float] = None`, `scale: float = 1.0`, `rotation: float = 0.0`, `opacity: float = 1.0`, `z_index: int = 0`) can be introduced into `SceneLayer` without requiring any Alembic database migration.

---

## 4. Backend Service & Pipeline Audit

Inspection of existing backend infrastructure reveals extensive reusable code that eliminates the need for duplicate pipelines:

### 1. `ProjectService` ([`backend/app/services/project_service.py`](file:///d:/HeyGen/video-ai-tools/backend/app/services/project_service.py))
- Handles optimistic concurrency control (OCC) version creation: `create_version(project_id, expected_revision, document, source)`.
- Rejects stale revisions with HTTP 409 `CONCURRENCY_CONFLICT`.
- Fully capable of storing updated `audio_tracks`, `layers`, and `subtitles`.

### 2. `AssetLifecycleManager` & `AssetService` ([`backend/app/services/asset_service.py`](file:///d:/HeyGen/video-ai-tools/backend/app/services/asset_service.py))
- Provides `/workspaces/{id}/assets/upload-intents` for pre-signed MinIO PUT uploads.
- Direct binary browser uploads to MinIO with SHA256 verification and automatic MIME categorization.
- Confirmation via `/workspaces/{id}/assets/{asset_id}/confirm`.
- Pre-signed download URLs via `/workspaces/{id}/assets/{asset_id}/download`.
- Listing and filtering via `/workspaces/{id}/assets?asset_type=audio|image|video`.

### 3. `TimelineCompositor` ([`backend/app/media/compositor.py`](file:///d:/HeyGen/video-ai-tools/backend/app/media/compositor.py))
- Already implements `_mix_background_audio()`:
  - Resolves `audio_tracks[0].asset_id` via `MediaWorkspace.resolve_asset()`.
  - Loops background audio seamlessly via `-stream_loop -1`.
  - Applies volume attenuation via `build_audio_volume(track.volume)`.
  - Mixes speech voiceover with background music using `amix=inputs=2:duration=first:dropout_transition=2.0`.
- Already implements solid color, image (`-loop 1`), and video (`-stream_loop -1`) background rendering.
- Already implements alpha-matting neural video overlay and circular PIP avatar compositing.
- Text overlay filter: uses `build_drawtext_filter()` with external UTF-8 file to prevent injection.

### 4. ASR & Transcription Infrastructure ([`backend/app/services/project_transcription_service.py`](file:///d:/HeyGen/video-ai-tools/backend/app/services/project_transcription_service.py))
- `ProjectTranscriptionOrchestrator` is fully implemented.
- Uses `WhisperASRProvider` (Faster-Whisper) with word-level timestamps (`include_word_timestamps=True`).
- Endpoint exists: `POST /workspaces/{id}/projects/{id}/transcribe`.
- Automatically populates `scene.subtitles = transcription.segments` and updates `ProjectDocumentV1` under OCC.
- Celery task `asr_transcription` already registered in task router.

---

## 5. Music Feature Audit

| Requirement | Current Backend State | Current Frontend State | Gap / Missing Implementation |
|---|---|---|---|
| Upload audio file | Supported via `/assets/upload-intents` (`asset_type="audio"`) | Supported in `AttachAssetModal.tsx` | Missing audio tab/modal trigger in Studio |
| Store audio asset | Supported in PostgreSQL `assets` & MinIO | Handled by API client | None |
| Attach audio to project | Supported in `ProjectDocumentV1.audio_tracks` | Serialized on save, but no setter | Missing Studio UI state & audio picker |
| Define volume | Supported in `AudioTrack.volume` (0.0-2.0) | None | Missing volume slider in Studio |
| Define start / end | Supported in `AudioTrack.start_time` & `duration` | None | Missing timeline trimmer for audio |
| Define offset | Supported in `AudioTrack.start_time` | None | `_mix_background_audio` needs `adelay` filter |
| Mix audio | Implemented via `build_audio_amix(inputs=2)` | None | None (already works in compositor) |
| Render music | Mixed into final `render.mp4` | None | UI must allow user to select audio track |

---

## 6. Captions / Subtitles Feature Audit

| Requirement | Current Backend State | Current Frontend State | Gap / Missing Implementation |
|---|---|---|---|
| Transcription | Implemented via `WhisperASRProvider` (Faster-Whisper) | None | Studio lacks "Generate Subtitles" button |
| Timestamps | Returns word & segment start/end timestamps | None | None (data exists in `TranscriptionResult`) |
| Subtitle model | Stored in `Scene.subtitles: List[Dict[str, Any]]` | Preserved in state, no editor | Missing cue list and text editor |
| Subtitle editing | Supported via `create_version` OCC document update | None | Missing cue time-adjustment and text editor |
| Subtitle persistence | Fully persisted in JSONB `scene.subtitles` | None | None |
| Subtitle rendering | `TimelineCompositor` only reads fallback plain text | None | Missing timed burn-in (`enable='between(t,...)'` or ASS/SRT filter) |

---

## 7. Elements & Visual Overlays Audit

| Element Type | Data Model | Project State | Asset Dependency | Dimensions / Position | Compositor Support | Render Support |
|---|---|---|---|---|---|---|
| **Text Overlay** | `SceneLayer(type="text")` | `scene.layers` | None | `transform: {x, y, scale}` | Partial (single static bottom box) | Partial |
| **Shape** | `SceneLayer(type="shape")` | `scene.layers` | None | `transform: {x, y, width, height}` | Not implemented | None |
| **Sticker / Icon** | `SceneLayer(type="sticker")` | `scene.layers` | MinIO PNG asset | `transform: {x, y, scale}` | Not implemented | None |
| **Image Overlay** | `SceneLayer(type="image")` | `scene.layers` | MinIO image asset | `transform: {x, y, scale}` | Not implemented | None |
| **B-Roll Video** | `SceneLayer(type="video")` | `scene.layers` | MinIO video asset | `transform: {x, y, scale}` | Not implemented | None |
| **Logo** | `SceneLayer(type="image")` | `scene.layers` | MinIO PNG asset | `transform: {x, y, scale}` | Not implemented | None |

### Architectural Support for Elements
- The data model (`SceneLayer`) exists and is persisted inside `ProjectDocumentV1`.
- The frontend canvas does not render layer overlays, bounding boxes, or transform handles.
- `TimelineCompositor` only reads the first text layer for script text; it does not loop over `scene.layers` to construct overlay filter chains.

---

## 8. Timeline Architecture Audit

### Current Timeline Tracks (Phase 28)
Located in [`src/components/studio/VidoAIStudio.tsx`](file:///d:/HeyGen/video-ai-tools/src/components/studio/VidoAIStudio.tsx#L1822-L1949):
1. `🎬 Scene`: Displays scene sequence block with duration width.
2. `👤 Avatar`: Displays selected avatar name and framing badge.
3. `🔤 Script`: Displays scene speech text snippet.
4. `🎵 Speech`: Displays TTS audio status and WAV badge.

### Missing Timeline Tracks Required by Studio Features
1. **Music Track Lane**:
   - Must represent `doc.audio_tracks`.
   - Displays audio track title, waveform placeholder, volume badge, and duration.
2. **Subtitles / Captions Track Lane**:
   - Must represent `scene.subtitles`.
   - Displays timestamped subtitle cue chips (`start` to `end`) synchronized with speech audio.
3. **Canvas Layers Track Lane**:
   - Must represent `scene.layers` (text, image, shape, sticker).
   - Displays layer type icon, name, and `[start_time, end_time]` span within the scene.

---

## 9. TimelineCompositor & FFmpeg Audit

Inspection of [`backend/app/media/compositor.py`](file:///d:/HeyGen/video-ai-tools/backend/app/media/compositor.py) and [`backend/app/media/filters.py`](file:///d:/HeyGen/video-ai-tools/backend/app/media/filters.py):

| Capability | Current Compositor Status | Code Reference |
|---|---|---|
| **Multi-scene video concat** | Supported | `_concatenate_scene_clips()` (lines 488-540) |
| **Avatar video overlay** | Supported | Neural alpha-matting or circular PIP (lines 335-408) |
| **Speech audio** | Supported | Mapped to scene audio output (lines 416-439) |
| **Background music** | Supported | `_mix_background_audio()` loops track & mixes via `amix` (lines 541-607) |
| **Color background** | Supported | `build_color_source()` lavfi color (lines 292-303) |
| **Image background** | Supported | `-loop 1` with `build_scale_and_pad(contain)` (lines 273-281) |
| **Video background** | Supported | `-stream_loop -1` with `build_scale_and_pad(cover)` (lines 282-290) |
| **Static scene text** | Supported | `build_drawtext_filter()` with external UTF-8 file (lines 319-333) |
| **Timed subtitle burn-in** | **Not implemented** | Subtitles only used as fallback text for whole scene |
| **Multi-layer overlays** | **Not implemented** | Only background + 1 avatar + 1 text layer supported |
| **Layer positioning / scale** | **Not implemented** | Only avatar `pos_x`, `pos_y`, and `scale` supported |
| **Layer opacity / rotation** | **Not implemented** | Not present in filtergraph |
| **Scene transitions** | **Partial** | Concat demuxer copies stream; `xfade` filter not yet active |

---

## 10. Frontend Static Data & Mock Audit

Search of [`src/components/studio/VidoAIStudio.tsx`](file:///d:/HeyGen/video-ai-tools/src/components/studio/VidoAIStudio.tsx):

1. **Left Tool Rail Fallback Placeholders** (Lines 1056–1067):
   - `media`, `text`, `elements`, `music`, `transitions`, `captions`, `brand_kit` all have `tab: "scene"`.
   - Clicking any of these icons simply switches the inspector back to the Script & Scene tab.
2. **Non-Functional Undo / Redo Controls**:
   - Header Undo/Redo (Lines 882–887): buttons have no `onClick` handlers.
   - Timeline Action Bar Undo/Redo (Lines 1789–1794): buttons have no `onClick` handlers.
3. **Non-Functional Canvas Player Controls**:
   - Volume and Maximize icons (Lines 1350–1353): static icons with no event handlers.
4. **Non-Functional Timeline Track Controls**:
   - Track visibility eye icons (Lines 1825, 1829, 1833, 1837): static icons `<Eye size={11} />` with no mute/hide state.
5. **Hardcoded Fallback Identifiers**:
   - Voice ID fallback: `"10000000-0000-0000-0000-000000000004"` (Piper Bryce) hardcoded at lines 238, 367, 466.
   - Avatar ID fallback: `"default-presenter"` hardcoded at lines 232, 368, 1600.
6. **Hardcoded Background Colors** (Line 1540):
   - Only 5 hardcoded hex values: `["#0F172A", "#1E1B4B", "#064E3B", "#831843", "#000000"]`.
   - No color picker, no custom hex input, and no image or video background selection UI.
7. **Static AI Credits Box** (Lines 1091–1098):
   - Displays static "Active" label and `w-[100%]` progress bar.
8. **Toast Auto-Dismiss Timer** (Lines 159–161):
   - `setTimeout` used for notification dismissal (acceptable UI utility).

---

## 11. Missing UI & Disconnected Control Audit

| Component / File Reference | Control / Element | Current Behavior | Required Functional Behavior |
|---|---|---|---|
| `VidoAIStudio.tsx:1063` | Left Rail: "Music" | Switches to `activeTab="scene"` | Open Music Inspector panel (catalog, upload, volume, loop) |
| `VidoAIStudio.tsx:1065` | Left Rail: "Captions" | Switches to `activeTab="scene"` | Open Captions panel (transcribe button, cue list, style) |
| `VidoAIStudio.tsx:1061` | Left Rail: "Text" | Switches to `activeTab="scene"` | Open Text panel (heading, body, callout, font, color) |
| `VidoAIStudio.tsx:1062` | Left Rail: "Elements" | Switches to `activeTab="scene"` | Open Elements panel (shapes, badges, stickers) |
| `VidoAIStudio.tsx:1060` | Left Rail: "Media" | Switches to `activeTab="scene"` | Open Media Library modal / asset selector (`AttachAssetModal`) |
| `VidoAIStudio.tsx:1066` | Left Rail: "Brand Kit" | Switches to `activeTab="scene"` | Open Brand Kit panel (colors, logos, fonts) |
| `VidoAIStudio.tsx:1538` | Inspector: Background | Only 5 color buttons | Add image/video background selector from workspace assets |
| `VidoAIStudio.tsx:882, 1789` | Top & Bottom: Undo/Redo | No `onClick` | Undo/redo stack for local document changes |
| `VidoAIStudio.tsx:1820` | Bottom: Timeline Tracks | Only 4 tracks | Add Music, Subtitle, and Layer tracks |
| `VidoAIStudio.tsx:1238` | Center: Canvas Viewport | Static video/avatar | Display layer overlays (text, image, shape) on canvas |

---

## 12. Implementation Plan

To safely complete the Studio editor without breaking existing verified speech, avatar, or render pipelines, implementation must proceed in modular phases:

```
┌─────────────────────────────────────────────────────────────┐
│ Phase 30A: Music Track & Audio Assets                       │
│ - Studio Music panel (list workspace audio, MinIO upload)   │
│ - Update doc.audio_tracks (asset_id, volume, loop)          │
│ - Timeline Music track lane                                 │
│ - Compositor: adelay audio offset verification              │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│ Phase 30B: Captions & Subtitles Engine                      │
│ - Studio Captions panel & "Generate Captions" (Whisper ASR) │
│ - Subtitle cue editor (timestamp & text editing)            │
│ - Timeline Subtitles track lane with cue chips              │
│ - Compositor: timed subtitle burn-in filtergraph            │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│ Phase 30C: Media Library & Asset Integration                │
│ - Wire AttachAssetModal into Studio "Media" rail tool       │
│ - Background image/video picker                             │
│ - Canvas background rendering for image & video             │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│ Phase 30D: Canvas Layers, Text & Elements                   │
│ - Text layer inspector (add title/body, color, font size)   │
│ - Elements inspector (shapes, stickers)                     │
│ - Canvas overlay positioning & visual preview               │
│ - Timeline Layers track lane                                │
│ - Compositor: multi-layer overlay filtergraph chaining      │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│ Phase 30E: Timeline Expansion & History Controls            │
│ - Undo/Redo stack for scene & layer mutations               │
│ - Timeline track mute/visibility toggles                    │
│ - Interactive scrubber zoom and time ruler markers          │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│ Phase 30F: End-to-End Verification                          │
│ - Automated multi-track test suite                          │
│ - Live Browser E2E validation in Chrome                     │
└─────────────────────────────────────────────────────────────┘
```

---

## 13. Database Migration Requirement

- **Current Alembic Head**: `0006_orchestration_jobs`.
- **Database Migration Required**: **NO (0 migrations needed)**.
- **Rationale**:
  `ProjectDocumentV1` is persisted entirely inside the `project_versions.document` JSONB column. All missing features (`audio_tracks`, `subtitles`, `layers`, `background`, `settings`) are native JSON fields within this document. Modifying the Pydantic schema in Python requires no database schema changes, no table alterations, and no Alembic migrations.

---

## 14. Dependency Requirement

- **Frontend (`package.json`)**: **0 new dependencies required**.
  Existing packages (`react`, `next`, `lucide-react`, `tailwindcss`) provide all necessary icons, state primitives, and styling tokens.
- **Backend (`pyproject.toml`)**: **0 new dependencies required**.
  Existing local libraries (`faster-whisper`, `ffmpeg-python`, `piper-tts`, `kokoro-onnx`, `celery`, `redis`, `minio`, `sqlalchemy`) provide all required ASR, audio processing, video compositing, and async job execution capabilities.

---

## 15. Risk Analysis & Mitigation Strategy

1. **Risk: FFmpeg Filtergraph Complexity in Multi-Layer Compositing**
   - *Issue*: Chaining multiple overlay layers (background + video + matting avatar + text layers + shape layers) in FFmpeg can lead to syntax errors or long render times.
   - *Mitigation*: Construct modular filtergraph parts with named intermediate stream labels (`[bg]`, `[layer_0]`, `[layer_1]`, `[comp]`). Test each layer builder in isolated unit tests before integrating.
2. **Risk: OCC Concurrency Conflicts during Asynchronous AI Jobs**
   - *Issue*: Generating speech or captions updates the document revision in the database. If the user simultaneously edits text in the UI, an OCC revision mismatch occurs.
   - *Mitigation*: Ensure frontend auto-saves pending local modifications before dispatching async jobs, and updates its local `revision` state upon receiving job completion events.
3. **Risk: Audio Desynchronization with Background Music**
   - *Issue*: Background music looping must not extend the scene beyond the total narration duration.
   - *Mitigation*: Use `-shortest` and `amix=duration=first` in FFmpeg, which guarantees the output video cuts off exactly when the visual scenes terminate.

---

## 16. Verification & Testing Strategy

1. **Backend Integration Tests**:
   - `test_music_composition`: Verify that `_mix_background_audio` properly loops and blends background audio with speech.
   - `test_caption_burn_in`: Verify that `scene.subtitles` are rendered as timed text on the video.
   - `test_layer_compositing`: Verify that `scene.layers` produce correct overlay filter chains.
2. **Frontend Build & Lint**:
   - `npm run build` to verify clean Next.js bundle without type errors.
3. **Browser E2E Verification**:
   - Navigate to Studio editor.
   - Add background music track and verify volume adjustment.
   - Click "Transcribe Audio" and verify subtitle cues appear on the timeline.
   - Add text overlay and position it on the canvas.
   - Export full video and verify resulting MP4 has speech, music, avatar, and subtitles in Chrome.

---

## Current Studio Completion Summary

```
CURRENT STUDIO COMPLETION:

Script:        100% (Functional editor, real OCC persistence, auto-invalidation)
Voice:         100% (17 local TTS voices, language filters, audio preview playback)
Avatar:        100% (Wav2Lip CPU prototype & MuseTalk GPU admission, framing modes)
Speech:        100% (Async Celery synthesis, MinIO WAV assets, SSE streaming)
Music:          25% (Compositor mixes audio; UI panel, track lane & picker missing)
Captions:       30% (Faster-Whisper ASR works; UI editor, cue lane & burn-in missing)
Elements:       10% (JSONB schema ready; UI panel, canvas handles & compositor missing)
Text:           20% (Single static box rendered; multi-layer UI & timeline lane missing)
Images/Media:   30% (MinIO upload ready; Studio modal wiring & overlay missing)
Background:     50% (Solid color fully functional; image/video asset picker missing)
Timeline:       60% (4 tracks functional; music, subtitle, and layer lanes missing)
Render:        100% (Async Celery worker, SSE progress, 1080p MP4 export verified)
```
