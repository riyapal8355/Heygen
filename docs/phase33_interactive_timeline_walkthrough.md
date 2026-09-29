# Phase 33 — Studio Interactive Timeline Manipulation & Clip Trimming Walkthrough

## Overview

In Phase 33, we implemented interactive timeline manipulation and clip trimming across the HeyZen Studio multi-track timeline.

The timeline now supports:
1. **Horizontal Drag-to-Move**: Click and drag any timeline clip to reposition it in time while strictly preserving its duration.
2. **Left-Edge Trimming**: Grab the left handle of a clip to adjust its start time, anchored at its end time.
3. **Right-Edge Trimming**: Grab the right handle of a clip to adjust its end time, anchored at its start time.
4. **Boundary Clamping**: Clips cannot be moved or resized outside the active scene boundaries ($0.0\text{s} \le \text{start} < \text{end} \le \text{sceneDuration}$).
5. **Minimum Duration Enforcement**: Clips cannot be trimmed shorter than $0.2\text{s}$.
6. **Playhead & Boundary Snapping**: Clips magnetically snap to the playhead and scene edges when dragged within $0.1\text{s}$.
7. **Inspector $\leftrightarrow$ Timeline Synchronization**: Single canonical state ensures immediate two-way updates between timeline clips and the Inspector property panels.
8. **Multi-Track Support**: Fully functional across Captions, Text, Visual Media, Elements & Shapes, and Background Music.

---

## Key Changes Made

### 1. Shared Timeline Mathematics & Hook (`src/lib/timelineUtils.ts`)
* Implemented `MIN_CLIP_DURATION = 0.2` and `SNAP_THRESHOLD_SECONDS = 0.1`.
* Implemented `calculateMoveTiming`, `calculateLeftTrimTiming`, and `calculateRightTrimTiming`.
* Implemented `useTimelineClipDrag` React hook:
  * Manages pointer capture with `window.addEventListener("pointermove")` and `window.addEventListener("pointerup")` to avoid lost pointer events when moving outside the element.
  * Distinguishes clicks from drags using a 4px distance threshold, preventing accidental timing mutations when selecting layers.
  * Provides `getClipProps()`, `getLeftHandleProps()`, and `getRightHandleProps()`.

### 2. Five Enhanced Timeline Track Components
* `MediaTimelineTrack.tsx`: Wrapped image/video clips in `MediaTimelineClipItem` with left and right resize handles and playhead snapping.
* `ElementsTimelineTrack.tsx`: Wrapped shape/sticker clips in `ElementsTimelineClipItem` with drag-to-move and edge trim handles.
* `TextTimelineTrack.tsx`: Wrapped text overlay clips in `TextTimelineClipItem` with drag-to-move and trim handles.
* `CaptionTimelineTrack.tsx`: Wrapped subtitle cues in `CaptionTimelineClipItem` with drag-to-move and cue trim handles.
* `MusicTimelineTrack.tsx`: Full interactive music track component supporting audio offset drag, duration trimming, loop indicators, and mute badges.

### 3. Central Studio Integration (`src/components/studio/VidoAIStudio.tsx`)
* Mounted `MusicTimelineTrack` at lane 5, replacing the previous static inline music lane.
* Added unified timing handlers:
  * `handleUpdateLayerTiming(sceneIdx, layerId, start, end)`
  * `handleUpdateCueTiming(sceneIdx, cueId, start, end)`
  * `handleUpdateMusicTiming(trackId, start, duration)`
  * `handleCommitTiming()` (persists to backend via OCC `createVersion` on pointer up)
* Connected callbacks across all 5 timeline tracks.

---

## Verification Results

### 1. Dedicated Phase 33 Test Suite (`test_studio_interactive_timeline.py`)
```bash
backend/.venv/Scripts/pytest.exe backend/tests/test_studio_interactive_timeline.py -v
```
**Results**:
* `test_1_drag_to_move` — **PASSED**
* `test_2_negative_boundary` — **PASSED**
* `test_3_scene_end_boundary` — **PASSED**
* `test_4_left_trim` — **PASSED**
* `test_5_right_trim` — **PASSED**
* `test_6_minimum_duration` — **PASSED**
* `test_7_playhead_snap` — **PASSED**
* `test_8_inspector_timeline_sync_and_persistence` — **PASSED**
* `test_9_inspector_to_timeline_sync` — **PASSED**
* `test_11_all_five_tracks` — **PASSED**
* `test_12_ffmpeg_render_parity` — **PASSED** (Real FFmpeg render with frame pixel sampling)
* `test_13_scene_isolation` — **PASSED**

**Summary**: 12 passed / 0 failed.

### 2. Full Studio Regression Suite
* `test_studio_elements_shapes_stickers.py`: 13 passed
* `test_studio_media_layers.py`: 10 passed
* `test_studio_text.py`: 10 passed
* `test_studio_captions.py`: 8 passed
* `test_studio_music_media.py`: 7 passed
* `test_studio_pipeline_e2e.py`: 11 passed
* `test_timeline_compositor.py`: 3 passed
* `test_ai_whisper_asr.py`: 12 passed

**Summary**: 74 passed / 0 failed (100% green).

### 3. Production Build
```bash
npm run build
```
* Compilation: Passed in 8.8s
* TypeScript checking: Passed in 8.9s with 0 errors
* Static page generation: Passed (6/6 routes)

### 4. Integrity Checks
* `git status backend/alembic/versions`: No new migrations created.
* `git diff -- package.json package-lock.json public/`: Clean.
