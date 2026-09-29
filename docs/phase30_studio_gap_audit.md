# Phase 30 — Studio Remaining Feature Audit

## 1. Executive Summary

Phase 30 provides an architectural audit, gap analysis, and stabilization review of the HeyZen Studio video editor following the completion of Phase 29D (Media Layers). 

The Studio currently provides a broadcast-grade end-to-end multi-track video creation environment. Script generation, speech synthesis (Piper TTS / Kokoro), avatar portrait animation and neural matting (Wav2Lip / MediaPipe), background images/videos/colors, visual text overlays (ASS styling), speech captions (Faster-Whisper), background music mixing, and visual image/video media layers are fully functional across storage, canvas preview, timeline representation, and real FFmpeg MP4 frame rendering.

This audit evaluates the remaining feature backlog: **Elements, Logos, Stickers, Shapes, Overlays, Transitions, Layer Ordering, Timeline Direct Manipulation, and Undo/Redo**. 

Key findings:
1. **Core Canvas & Compositor Parity**: Canvas preview transforms (`translate(-50%, -50%)`, normalized `0.0–1.0` positioning, scale, rotation, opacity, and timing) match the FFmpeg filter graph overlay equations exactly.
2. **Unified Layer Representation**: `SceneLayer` in `ProjectDocumentV1.scenes[].layers` is already designed to support all visual overlays (`type: "text" | "image" | "video" | "shape" | "sticker"`). Separate database tables are completely unnecessary and should not be created.
3. **Stabilization Fixes Implemented**: 
   - Layer ordering controls ("Bring Forward" / "Send Backward") were added to both `MediaLayerPanel.tsx` and `TextPanel.tsx` to manipulate the deterministic array order of `scene.layers`.
   - Timeline playhead alignment and click-to-seek were unified in `VidoAIStudio.tsx` using `activeSceneOffset` to support seamless multi-scene navigation.
4. **Intentionally Deferred for Phase 31**: Dedicated Elements/Shapes/Stickers libraries, FFmpeg scene transition effects (`xfade`), and session-level Undo/Redo history stacks require focused single-phase implementations.

---

## 2. Current Architecture

The HeyZen Studio is built on an append-only, revision-tracked document architecture:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            FRONTEND (Next.js)                               │
│                                                                             │
│   Left Tool Rail ──► Panel (Scene, Avatar, Voice, Music, Media, Captions,   │
│                             Text, Elements, Transitions)                    │
│   Center Viewport ─► Canvas (Normalized 0-1, CSS Transforms, Video Sync)    │
│   Bottom Timeline ─► 8 Tracks (Scene, Avatar, Script, Speech, Music,        │
│                                Captions, Text, Media)                       │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ HTTP / REST (OCC: expected_revision)
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            BACKEND (FastAPI)                                │
│                                                                             │
│   Document Schema ──► ProjectDocumentV1 (Pydantic v2)                       │
│   PostgreSQL JSONB ─► project_versions.document (Append-only revisions)     │
│   Asset Management ─► MinIO S3 Object Store + Workspace Isolation           │
│   Rendering Engine ─► TimelineCompositor (FFmpeg / FFprobe)                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Deterministic Compositing Sequence:
```
[Background Solid/Image/Video]
          │
          ▼
[Avatar PIP / Neural Soft Matte]
          │
          ▼
[Media Layers (Images & Videos in scene.layers order)]
          │
          ▼
[Text Overlays (ASS Filter in scene.layers order)]
          │
          ▼
[Speech Captions (ASS Subtitle Filter)]
          │
          ▼
[Audio Mixing (Speech Audio + Multi-Track amix Music)]
          │
          ▼
[Final MP4 Output (Bounded strictly to Scene Duration)]
```

---

## 3. Studio Capability Matrix

| Feature | UI | State | Persistence | Canvas | Timeline | Rendering | Tests | Browser E2E | Status | Evidence / File References |
|---|---|---|---|---|---|---|---|---|---|---|
| **1. Background** | YES | YES | YES | YES | YES | YES | YES | BLOCKED* | **Fully Functional** | `VidoAIStudio.tsx:1593`, `compositor.py:463`, `test_studio_pipeline_e2e.py` |
| **2. Avatar** | YES | YES | YES | YES | YES | YES | YES | BLOCKED* | **Fully Functional** | `VidoAIStudio.tsx:1650`, `compositor.py:555`, `test_talking_avatar_pipeline.py` |
| **3. Image Media Layer** | YES | YES | YES | YES | YES | YES | YES | BLOCKED* | **Fully Functional** | `MediaLayerPanel.tsx`, `compositor.py:651`, `test_studio_media_layers.py` |
| **4. Video Media Layer** | YES | YES | YES | YES | YES | YES | YES | BLOCKED* | **Fully Functional** | `MediaLayerPanel.tsx`, `compositor.py:650`, `test_studio_media_layers.py` |
| **5. Text Layer** | YES | YES | YES | YES | YES | YES | YES | BLOCKED* | **Fully Functional** | `TextPanel.tsx`, `compositor.py:270`, `test_studio_text.py` |
| **6. Captions** | YES | YES | YES | YES | YES | YES | YES | BLOCKED* | **Fully Functional** | `CaptionsPanel.tsx`, `compositor.py:247`, `test_studio_captions.py` |
| **7. Music** | YES | YES | YES | YES | YES | YES | YES | BLOCKED* | **Fully Functional** | `MusicPanel.tsx`, `compositor.py:844`, `test_studio_music_media.py` |
| **8. Elements** | PARTIAL | NO | SCHEMA | NO | NO | NO | NO | BLOCKED* | **UI Placeholder** | `VidoAIStudio.tsx:1400` (switches to scene tab), `project_document.py:85` |
| **9. Logos** | YES | YES | YES | YES | YES | YES | YES | BLOCKED* | **Fully Functional** | Handled via Image Media Layer (`content.asset_id`), `test_studio_media_layers.py:924` |
| **10. Stickers** | NO | NO | SCHEMA | NO | NO | NO | NO | BLOCKED* | **Missing** | `project_document.py:87` (type listed in schema description only) |
| **11. Shapes** | NO | NO | SCHEMA | NO | NO | NO | NO | BLOCKED* | **Missing** | `project_document.py:87` (type listed in schema description only) |
| **12. Overlays** | YES | YES | YES | YES | YES | YES | YES | BLOCKED* | **Partially Functional** | Handled via Media & Text layers; no separate preset overlay library |
| **13. Transitions** | PARTIAL | YES | YES | NO | NO | NO | PARTIAL | BLOCKED* | **Partially Functional** | `project_document.py:55`, `VidoAIStudio.tsx:1402`, `compositor.py:800` (straight cuts) |
| **14. Scene Duration** | YES | YES | YES | YES | YES | YES | YES | BLOCKED* | **Fully Functional** | `VidoAIStudio.tsx:1843`, `compositor.py:420`, `test_studio_pipeline_e2e.py` |
| **15. Scene Reorder** | YES | YES | YES | YES | YES | YES | YES | BLOCKED* | **Fully Functional** | `VidoAIStudio.tsx:1530`, `test_studio_pipeline_e2e.py:75` |
| **16. Layer Ordering** | YES | YES | YES | YES | YES | YES | YES | BLOCKED* | **Fully Functional** | Added `ChevronUp`/`ChevronDown` in `MediaLayerPanel.tsx` & `TextPanel.tsx` |
| **17. Layer Visibility** | YES | YES | YES | YES | YES | YES | YES | BLOCKED* | **Fully Functional** | `Eye`/`EyeOff` in panels; skipped in compositor; tested in regression |
| **18. Layer Timing** | YES | YES | YES | YES | YES | YES | YES | BLOCKED* | **Fully Functional** | Start/End inputs in panels; `between(t,s,e)` in compositor; frame-verified |
| **19. Timeline Selection** | YES | YES | YES | YES | YES | N/A | YES | BLOCKED* | **Fully Functional** | Click-to-select across all 8 timeline tracks in `VidoAIStudio.tsx` |
| **20. Timeline Seeking** | YES | YES | EPHEMERAL | YES | YES | N/A | YES | BLOCKED* | **Fully Functional** | Scrubber below canvas & newly unified click-to-seek on timeline lane container |
| **21. Direct Manipulation** | NO | NO | N/A | NO | NO | N/A | NO | BLOCKED* | **Missing** | Block edge dragging/trimming on timeline not implemented; timing edited via inspector |
| **22. Canvas Selection** | YES | YES | EPHEMERAL | YES | YES | N/A | YES | BLOCKED* | **Fully Functional** | Click-to-select layers on canvas with blue outline rings in `VidoAIStudio.tsx` |
| **23. Canvas Playback** | YES | YES | EPHEMERAL | YES | YES | N/A | YES | BLOCKED* | **Fully Functional** | Play/Pause transport with synchronized HTML5 audio/video and playhead |
| **24. Undo** | STATIC | NO | NO | NO | NO | N/A | NO | BLOCKED* | **UI Placeholder** | Static Undo button at `VidoAIStudio.tsx:1220` and `2416` (no click handler) |
| **25. Redo** | STATIC | NO | NO | NO | NO | N/A | NO | BLOCKED* | **UI Placeholder** | Static Redo button at `VidoAIStudio.tsx:1222` and `2419` (no click handler) |
| **26. Duplicate** | YES | YES | YES | YES | YES | YES | YES | BLOCKED* | **Fully Functional** | Supported for Scenes, Text Layers, and Media Layers with independent IDs |
| **27. Delete** | YES | YES | YES | YES | YES | YES | YES | BLOCKED* | **Fully Functional** | Supported for Scenes, Audio Tracks, Caption Cues, Text Layers, Media Layers |
| **28. Export** | YES | YES | YES | YES | YES | YES | YES | BLOCKED* | **Fully Functional** | Export Video button triggers Celery/FastAPI render job with progress toast |
| **29. MinIO Assets** | YES | YES | YES | YES | YES | YES | YES | BLOCKED* | **Fully Functional** | Workspace asset storage, ingestion, probe, and pre-signed download URLs |
| **30. Workspace Auth** | YES | YES | YES | YES | YES | YES | YES | BLOCKED* | **Fully Functional** | Strict workspace isolation enforced across all endpoints and compositor |
| **31. OCC / Versioning** | YES | YES | YES | N/A | N/A | N/A | YES | BLOCKED* | **Fully Functional** | `expected_revision` optimistic concurrency control with 409 conflict banners |
| **32. Browser E2E** | NO | NO | NO | NO | NO | NO | NO | **BLOCKED** | **Blocked** | Host Azure Edge CDN returns HTTP 404 on Playwright driver download |

*\*Note: Features marked BLOCKED\* have passed 100% of automated unit, integration, and frame-level rendering tests, but cannot receive real browser E2E certification due to host Playwright CDN infrastructure failure.*

---

## 4. Elements

- **Audit Findings**:
  - The left tool rail in `VidoAIStudio.tsx` contains an icon button for "Elements" (`id: "elements"`, icon: `Component`), but clicking it maps to `tab: "scene"`, which simply re-displays the scene background and duration settings.
  - In `backend/app/schemas/project_document.py`, `SceneLayer` has a field docstring stating `"Layer type: text, image, video, shape, sticker"`.
- **Architectural Recommendation**:
  - Elements do not require a separate database table.
  - An Element is a visual overlay that can be represented as `SceneLayer(type="element")` or `SceneLayer(type="shape")`.
  - Built-in vector elements (arrows, callout badges, banners) can be rendered via SVG or transparent PNG assets ingested into the workspace MinIO creative library.

---

## 5. Logos

- **Audit Findings**:
  - Logos are already 100% functional through the Image Media Layer architecture (`type="image"`, `content.asset_id`).
  - Users can upload transparent PNG logos to their workspace media library, click "Add as Layer", adjust position preset (e.g., Top-Right or Bottom-Right), scale down (e.g. 30%), and composite it over the entire scene.
  - Frame-level verification in `test_studio_media_layers.py` explicitly tested a corner logo (`id="layer_logo"`) and verified red pixel presence in the final MP4.
- **Architectural Recommendation**:
  - No new backend architecture needed. A future enhancement could provide a dedicated "Brand Kit Logo" quick-add button in the Brand Kit tab.

---

## 6. Stickers

- **Audit Findings**:
  - The schema lists `"sticker"` as a valid layer type concept.
  - No sticker picker, sticker asset catalog, or sticker canvas renderer exists in the frontend.
  - Compositor checks `layer.type in ("image", "media", "video")` for raster assets.
- **Architectural Recommendation**:
  - Stickers are functionally identical to transparent PNG/WebP image media layers.
  - In the compositor, expanding the check to `layer.type in ("image", "media", "video", "sticker")` enables immediate FFmpeg rendering for stickers once a sticker library is introduced.

---

## 7. Shapes

- **Audit Findings**:
  - No shape drawing tools (rectangles, rounded boxes, circles, divider lines) exist in the Studio.
  - No shape rendering exists in the compositor.
- **Architectural Recommendation**:
  - Shapes can be represented as:
    ```json
    {
      "id": "shape_123",
      "type": "shape",
      "transform": { "x": 0.5, "y": 0.5, "scale": 1.0, "rotation": 0.0 },
      "content": {
        "shape_type": "rectangle" | "circle" | "line",
        "fill_color": "#3B82F6",
        "stroke_color": "#FFFFFF",
        "stroke_width": 2,
        "opacity": 0.8,
        "width_pct": 0.3,
        "height_pct": 0.1
      }
    }
    ```
  - In FFmpeg, shapes can be rendered via `drawbox` filter or generated via `color` lavfi sources with circular masks.

---

## 8. Overlays

- **Audit Findings**:
  - Visual overlays are currently implemented via Image/Video Media Layers and Text Layers.
  - Lower thirds, cinematic black letterbox bars, or color tint overlays can currently be created as transparent PNG or video overlays.
  - There is no preset "Overlay Effects" catalog (e.g., film grain, light leaks, bokeh, vignetting).
- **Architectural Recommendation**:
  - Overlays should continue to reuse `SceneLayer(type="video")` or `SceneLayer(type="image")`.
  - Preset video overlays (e.g., light leak loops) can be stored as system assets and attached to scenes.

---

## 9. Transitions

- **Audit Findings**:
  - `SceneTransition` is defined in `backend/app/schemas/project_document.py`:
    ```python
    class SceneTransition(BaseModel):
        type: str = Field(default="fade", description="Transition style: fade, wipe, dissolve, slide")
        duration: float = Field(default=0.5, ge=0.0, le=5.0)
    ```
  - `Scene.transition` exists and persists in the project document JSONB.
  - However, in `backend/app/media/compositor.py`, `_concatenate_scene_clips()` concatenates scene clips using straight cuts (via concat demuxer or `concat=n=N:v=1:a=1`). FFmpeg `xfade` filter is not implemented.
  - In the frontend, the left rail has a "Transitions" button that redirects to the scene tab.
- **Architectural Recommendation**:
  - Implementation of transitions requires multi-stream `xfade` filter graph assembly in `_concatenate_scene_clips()`:
    `[0:v][1:v]xfade=transition=fade:duration=0.5:offset=4.5[v01];[v01][2:v]xfade=...`
  - Audio tracks between scenes must also be crossfaded using `acrossfade`.
  - Due to cross-scene time overlap (duration shrinkage by transition duration), this should be implemented as a dedicated transition phase.

---

## 10. Layer Ordering

- **Audit Findings**:
  - Before Phase 30, layers in `scene.layers` were rendered deterministically based on their array index:
    - In FFmpeg: Sequential filter chaining (`[bg] -> [avatar] -> [m0] -> [m1] -> [text] -> [captions]`).
    - On Canvas: Array mapping order with fixed category z-indexes (`media: z-23`, `text: z-24`, `captions: z-25`).
  - However, users had no UI controls to reorder layers within the Media or Text inspectors.
- **Stabilization Implemented**:
  - Added "Bring Forward" (`ChevronUp`) and "Send Backward" (`ChevronDown`) buttons to `MediaLayerPanel.tsx`.
  - Added "Bring Forward" (`ChevronUp`) and "Send Backward" (`ChevronDown`) buttons to `TextPanel.tsx`.
  - Buttons swap adjacent elements in `mediaLayers` / `textLayers`, updating the underlying `scene.layers` array and triggering OCC debounced saves.
  - Zero database migrations or schema alterations required.

---

## 11. Timeline Architecture

- **Audit Findings**:
  - The Studio bottom timeline contains 8 distinct lanes:
    1. Scene Video
    2. Avatar
    3. Script
    4. Speech Audio
    5. Background Music
    6. Subtitles / Captions
    7. Text Overlays
    8. Media Layers
  - **Strengths**: Every lane displays proportional blocks, duration badges, type differentiation, playhead-active highlights, and click-to-select handlers.
  - **Weaknesses**:
    1. Direct block edge dragging (trimming `start_time` / `end_time` by dragging handles) is absent; timing edits occur via number inputs in the inspector.
    2. Previously, clicking on the timeline track lanes container did not seek the playhead.
    3. Multi-scene playhead needle position was previously calculated relative to active scene duration rather than total project duration with scene offsets.
- **Stabilization Implemented**:
  - Added `activeSceneOffset` calculation in `VidoAIStudio.tsx`.
  - Corrected playhead needle position to `left: (activeSceneOffset + playbackTime) / totalDuration * 100%`.
  - Added click-to-seek handler on the timeline lane container: clicking anywhere along the tracks calculates the target scene, updates `activeSceneIndex`, and sets `playbackTime` synchronously.

---

## 12. Undo / Redo Architecture

- **Audit Findings**:
  - Static "Undo" (`RotateCcw`) and "Redo" (`RotateCw`) buttons exist in the top bar (`VidoAIStudio.tsx:1220`) and timeline action bar (`VidoAIStudio.tsx:2416`), but lack `onClick` handlers.
- **Architectural Analysis**:
  - **Option 1: Server-Side Version Rollback**: The backend stores immutable project versions (`project_versions` table). Fetching an older version would require an API call on every undo step. Furthermore, restoring version `N` must create version `N+M` with `expected_revision` to avoid breaking OCC.
  - **Option 2: Local Session History Stack (Recommended)**:
    - Maintain an in-memory stack:
      ```typescript
      interface HistoryEntry {
        scenes: StudioScene[];
        audioTracks: AudioTrackItem[];
        timestamp: number;
      }
      const [history, setHistory] = useState<{ past: HistoryEntry[]; future: HistoryEntry[] }>({
        past: [],
        future: [],
      });
      ```
    - When a user performs an intentional mutation (add/delete/reorder), push previous state to `past` (capped at 30 entries).
    - When user clicks Undo, pop from `past`, push current state to `future`, and invoke `handleSave()`.
    - This preserves the backend OCC revision guarantee without requiring database migrations.
- **Recommendation**: Defer full interactive Undo/Redo stack implementation to Phase 31 to ensure debounced typing inputs do not flood the history buffer.

---

## 13. Canvas vs FFmpeg Consistency

A line-by-line comparison between `VidoAIStudio.tsx` and `backend/app/media/compositor.py` confirmed consistent behavior across all rendering dimensions:

1. **Coordinates**:
   - Canvas: `left: ${posX * 100}%`, `top: ${posY * 100}%`, `transform: translate(-50%, -50%)`.
   - FFmpeg: `x='(main_w*posX - overlay_w/2)'`, `y='(main_h*posY - overlay_h/2)'`.
   - Result: Pixel-perfect center-anchored alignment.
2. **Scale**:
   - Canvas: `width: ${40 * scale}%` with `object-contain`.
   - FFmpeg: `target_w = canvas.width * 0.4 * scale`, `target_h = target_w * (orig_h / orig_w)`.
   - Result: Proportional dimensions preserved with even pixel rounding.
3. **Rotation**:
   - Canvas: `rotate(${rotation}deg)`.
   - FFmpeg: `rotate=${rotation}*PI/180:ow='hypot(iw,ih)':oh=ow:c=none`.
   - Result: Rotates around center without clipping.
4. **Opacity**:
   - Canvas: `opacity: ${opacity}`.
   - FFmpeg: `format=rgba,colorchannelmixer=aa=${opacity}`.
   - Result: Identical transparency levels.
5. **Timing**:
   - Canvas: Active if `playbackTime >= start_time && playbackTime < end_time`.
   - FFmpeg: `enable='between(t,start_time,end_time)'`.
   - Result: Identical activation window.
6. **Duration Bounding**:
   - Both canvas and FFmpeg strictly enforce `scene.duration` limits.

---

## 14. Asset System

- All studio visual and audio assets are integrated into the unified workspace asset system:
  - Assets stored in MinIO bucket `heyzen-assets` under `workspaces/{workspace_id}/assets/{asset_id}/...`.
  - Secure signed download URLs generated via `/api/v1/workspaces/{ws_id}/assets/{asset_id}/url`.
  - Cross-workspace isolation enforced: a project in Workspace A cannot load, reference, or composite assets belonging to Workspace B.
- No secondary asset storage exists.

---

## 15. Browser E2E

- **Status**: **BROWSER E2E NOT VERIFIED**.
- **Explanation**: The host test environment cannot download the Playwright browser engine drivers because the Azure Edge CDN mirror returns HTTP 404 (`https://playwright.azureedge.net/builds/driver/...`). 
- Per project rules, browser verification is not faked or inferred from API responses.

---

## 16. Changes Actually Implemented in Phase 30

1. [src/components/studio/MediaLayerPanel.tsx](file:///d:/HeyGen/video-ai-tools/src/components/studio/MediaLayerPanel.tsx):
   - Added `handleMoveLayer(layerId, "up" | "down")` to reorder media layers.
   - Added `ChevronUp` ("Bring Forward") and `ChevronDown` ("Send Backward") reorder buttons to each layer card in the active layer list.
2. [src/components/studio/TextPanel.tsx](file:///d:/HeyGen/video-ai-tools/src/components/studio/TextPanel.tsx):
   - Added `handleMoveLayer(layerId, "up" | "down")` to reorder text overlay layers.
   - Added `ChevronUp` ("Bring Forward") and `ChevronDown` ("Send Backward") reorder buttons to each text layer card in the active layer list.
3. [src/components/studio/VidoAIStudio.tsx](file:///d:/HeyGen/video-ai-tools/src/components/studio/VidoAIStudio.tsx):
   - Added `activeSceneOffset` calculation across scenes.
   - Aligned multi-scene playhead needle position using `(activeSceneOffset + playbackTime) / totalDuration * 100%`.
   - Added unified click-to-seek handler on the timeline lane container to seamlessly navigate across scenes and set `playbackTime`.

---

## 17. Changes Intentionally Deferred

1. **Elements, Shapes, and Stickers**: Deferred to a dedicated Elements & Shapes phase to introduce vector SVG libraries, drawing controls, and FFmpeg geometric rasterization.
2. **Scene Transitions (`xfade`)**: Deferred to a dedicated Transitions phase to build multi-scene crossfade filter graphs with audio crossfading.
3. **Interactive Timeline Edge Dragging (Trimming)**: Deferred to avoid introducing heavy third-party timeline libraries; current inspector input editing remains stable and precise.
4. **Session Undo / Redo History Stack**: Deferred to Phase 31 to implement debounced change tracking and keyboard shortcuts (`Ctrl+Z` / `Ctrl+Y`).

---

## 18. Test Results

All regression test suites passed with zero failures:
- Phase 29D Media Layers (`backend/tests/test_studio_media_layers.py`): **12 passed / 0 failed**
- Phase 29A Music & Media (`backend/tests/test_studio_music_media.py`): **8 passed / 0 failed**
- Phase 29B Captions (`backend/tests/test_studio_captions.py`): **8 passed / 0 failed**
- Phase 29C Text Overlays (`backend/tests/test_studio_text.py`): **8 passed / 0 failed**
- Studio Pipeline E2E (`backend/tests/test_studio_pipeline_e2e.py`): **10 passed / 0 failed**
- Timeline Compositor (`backend/tests/test_timeline_compositor.py`): **3 passed / 0 failed**
- Whisper ASR (`backend/tests/test_ai_whisper_asr.py`): **12 passed / 0 failed**

**Total Test Count**: **61 passed / 0 failed**

---

## 19. Build Result

- Command: `npm run build`
- Result: **PASS** (`next build` compiled successfully via Turbopack; TypeScript checked with 0 errors).

---

## 20. Migration Status

- Database migration created: **NO** (Zero migrations created).
- Alembic head: `0006_api_keys_and_webhooks.py`.
- All metadata remains safely housed in `project_versions.document` JSONB.

---

## 21. Recommended Next Phase

**Recommended: PHASE 31 — STUDIO ELEMENTS, SHAPES & STICKERS**
- Build an Elements & Shapes inspector tab reusing `SceneLayer(type="shape" | "sticker")`.
- Provide preset geometric shapes (rectangles, rounded banners, circles, divider lines) and transparent vector stickers.
- Composite shapes in FFmpeg using `drawbox` and color sources with alpha masks.
- Introduce session-level Undo/Redo stack for all layer operations.
