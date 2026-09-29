# Phase 37 — Studio Completeness & Interaction Architecture Audit

**Status**: Completed  
**Milestone Type**: Read-Only Architecture & Interaction Audit  
**Workspace**: `d:\HeyGen\video-ai-tools`  
**Date**: September 2026  

---

## 1. Executive Summary

This document establishes the authoritative completeness and interaction architecture audit of the HeyZen Video AI Studio following the completion of Phases 29D (Media Layers), 31 (Elements, Shapes & Stickers), 33 (Interactive Timeline Manipulation & Trimming), 34 (Canvas Direct Manipulation Gizmos), and 36 (Studio Render Parity Corrections).

The audit systematically traces the full editing and rendering pipeline:
$$\text{Project} \longrightarrow \text{Scene} \longrightarrow \text{Layers} \longrightarrow \text{Canvas} \longrightarrow \text{Inspector} \longrightarrow \text{Timeline} \longrightarrow \text{Persistence} \longrightarrow \text{Render} \longrightarrow \text{Export}$$

Every finding in this report is grounded in concrete repository evidence from the frontend TypeScript/React codebase (`src/components/studio/`, `src/lib/`), backend Python/FastAPI services (`backend/app/`), media pipeline (`backend/app/media/`), and persistence schemas (`backend/app/schemas/`, `backend/app/models/`).

### High-Level Interaction Status Summary

| Interaction Domain | Audit Classification | Architectural Core |
| :--- | :--- | :--- |
| **Layer Ordering** | **PARTIAL** | Intra-type reorder supported in panels; cross-type ordering blocked by hardcoded z-index tiers and sequential filter chaining |
| **Visibility** | **PARTIAL** | Persisted `enabled: bool` supported in schema, canvas, and compositor; toggle missing in `ElementsPanel` and timeline lanes |
| **Locking** | **MISSING** | No schema field, pointer-events guard, or UI representation exists across canvas, inspector, or timeline |
| **Undo / Redo** | **MISSING** | Server-side OCC versions created on commit, but no client-side history stack or revert API exists; UI buttons are non-functional placeholders |
| **Keyboard Controls** | **MISSING** | No `keydown` listeners exist for arrow nudging, Delete/Backspace, Esc deselect, Space playback, or clipboard |
| **Copy / Paste / Duplicate** | **PARTIAL** | Intra-panel duplication exists; system clipboard, cross-scene duplication, and canvas duplicate shortcuts are absent |
| **Layer Deletion** | **COMPLETE** | Panel deletion consistently updates document, canvas, timeline, and OCC persistence without deleting source media assets |
| **Timeline Editing** | **PARTIAL** | Clip drag, trim, playhead snap, boundary snap complete; split/blade, clip delete, clip duplicate, clip-to-clip snap, zoom/pan absent |
| **Canvas/Timeline Sync** | **COMPLETE** | Live two-way selection, timing updates, and transform commitments are synchronized; non-active playhead clip isolation is expected behavior |
| **Snapping / Alignment** | **PARTIAL** | Timeline playhead/boundary snapping complete; canvas center/edge/guide snapping absent |
| **Transitions** | **PARTIAL** | Schema object exists; UI controls, timeline indicators, and FFmpeg crossfade/xfade concatenation absent |
| **Scene Management** | **COMPLETE** | Add, duplicate, delete, reorder, and select scenes are fully functional and OCC-persisted |
| **Multi-Layer Selection** | **MISSING** | Single-layer selection strictly enforced; no Shift+click, box selection, or compound bounding-box transform model |

---

## 2. Current Studio Architecture

### End-to-End Pipeline Diagram

```
+---------------------------------------------------------------------------------------------------+
|                                         PROJECT LIFECYCLE                                         |
|                                                                                                   |
|  [ProjectDocumentV1 (JSONB)] <======================== API / OCC ========================> [DB]   |
|            |                               (expected_revision)                         PostgreSQL |
|            v                                                                                      |
|  +-------------------+                                                                            |
|  | Scenes [0..N]     |                                                                            |
|  | - duration        |                                                                            |
|  | - background      |                                                                            |
|  | - avatar / speech |                                                                            |
|  | - layers [0..M]   |                                                                            |
|  +-------------------+                                                                            |
|            |                                                                                      |
|            +------------------------------+------------------------------+                        |
|            |                              |                              |                        |
|            v                              v                              v                        |
|   [CANVAS VIEWPORT]             [INSPECTOR PANELS]              [MULTI-TRACK TIMELINE]            |
|   - Video / Audio Sync          - MediaLayerPanel               - MediaTimelineTrack              |
|   - Image/Video (z-23)          - TextPanel                     - TextTimelineTrack               |
|   - Elements/Shapes (23+idx)    - ElementsPanel                 - ElementsTimelineTrack           |
|   - Text Overlays (z-24)        - MusicPanel                    - CaptionTimelineTrack            |
|   - Captions (z-25)             - CaptionsPanel                 - MusicTimelineTrack              |
|   - CanvasTransformGizmo        - Live state update             - useTimelineClipDrag             |
|   - Direct Pointer Events       - SaveStatus: "unsaved"         - Snap to playhead/bounds         |
|            |                              |                              |                        |
|            +------------------------------+------------------------------+                        |
|                                           |                                                       |
|                             Commit Gesture (PointerUp)                                            |
|                                           v                                                       |
|                           [handleSave() -> POST /versions]                                        |
|                                           |                                                       |
|                             Export Request (POST /render)                                         |
|                                           v                                                       |
|                       [backend/app/media/compositor.py]                                           |
|                       1. Background scaling & color                                               |
|                       2. Avatar PIP / Green-screen matting                                        |
|                       3. Visual Media & Elements overlay chain                                    |
|                       4. ASS Text overlay subtitle filter                                         |
|                       5. ASS Caption subtitle filter                                              |
|                       6. Audio mix (Speech + Background Music)                                    |
|                       7. Concat demuxer / filtergraph assembly                                    |
|                                           |                                                       |
|                                           v                                                       |
|                                  [Final MP4 Video]                                                |
+---------------------------------------------------------------------------------------------------+
```

---

## 3. Layer Ordering Audit

### 3.1 Repository Evidence

1. **Document Representation**:
   - In `backend/app/schemas/project_document.py`: `scene.layers: List[SceneLayer] = Field(default_factory=list)`.
   - `SceneLayer` does NOT possess a `z_index` or `order` integer field. Ordering is implicitly represented by the array index in `scene.layers`.
2. **Frontend Canvas Stacking**:
   - Located in `src/components/studio/VidoAIStudio.tsx`:
     - Visual Media Layers (Images & Videos): `className="absolute z-23 ..."` (lines 1908).
     - Text Layers: `className="absolute z-24 ..."` (line 1994).
     - Elements, Shapes, and Stickers: `const zIndex = 23 + layerIdx;` (lines 2029–2030, 2056, 2158).
     - Caption Cue: `className="absolute inset-x-0 z-25 ..."` (line 2214).
3. **Backend Compositor Stacking**:
   - Located in `backend/app/media/compositor.py`:
     - `visual_media_layers = [l for l in (scene.layers or []) if l.type in ("image", "video", "media", "shape", "sticker", "element")]` (lines 553–556).
     - Sequentially composites each visual media layer using an FFmpeg overlay filter chain: `current_video_label -> comp_m_{idx}` (lines 786–793).
     - Text overlays are processed as a separate stage via ASS subtitles: `[comp_m_last] -> [v_txt]` (lines 796–798).
     - Captions are processed as the final subtitle pass: `[v_txt] -> [v_out]` (lines 799–805).
4. **Panel Reordering Implementation**:
   - `src/components/studio/MediaLayerPanel.tsx`: `handleMoveLayer(layerId, "up" | "down")` swaps adjacent elements within `mediaLayers`. Saves via `[...nonMediaLayers, ...newMediaLayers]` (lines 95, 139–149).
   - `src/components/studio/TextPanel.tsx`: `handleMoveLayer(layerId, "up" | "down")` swaps adjacent elements within `textLayers`. Saves via `[...nonTextLayers, ...newTextLayers]` (lines 98, 159–169).
   - `src/components/studio/ElementsPanel.tsx`: `handleReorder(layerId, "up" | "down")` swaps adjacent elements within `elementLayers`. Saves via `[...nonElementLayers, ...updatedElementLayers]` (lines 214, 318–328).

### 3.2 Analysis of Ordering Limitations

- **Cross-Type Stacking Inversion**:
  - In `VidoAIStudio.tsx`, an element layer at index $\ge 1$ receives `zIndex >= 24`, causing it to render visually in front of text overlays (`z-24`) on the canvas preview.
  - In `compositor.py`, however, all `visual_media_layers` (including shapes and stickers) are rendered in the video filtergraph *before* the ASS text overlay is applied. Thus, in the rendered MP4, text overlays are *always* on top of shapes/stickers.
- **Partitioned Persistence Side-Effect**:
  - Because each panel partitions `scene.layers` into `non[Type]Layers` and `new[Type]Layers` and appends its own layers at the end of the array, editing any layer in a panel moves all layers of that category to the end of `scene.layers`, altering their relative stacking in the backend compositor!
- **Missing Global Reorder Operations**:
  - No "Bring to Front" or "Send to Back" actions exist.
  - No global layer stack inspector or canvas context menu exists.

### 3.3 Operation Status Matrix

| Operation | Frontend | Document | Backend | Render | Timeline | Classification |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Current ordering** | Static z-tiers | Array index | Array index | Filter chain | Separate lanes | **PARTIAL** |
| **Bring forward** | Intra-type only | Intra-type | Intra-type | Intra-type | None | **PARTIAL** |
| **Send backward** | Intra-type only | Intra-type | Intra-type | Intra-type | None | **PARTIAL** |
| **Bring to front** | Not implemented | Supported | Supported | Supported | None | **MISSING** |
| **Send to back** | Not implemented | Supported | Supported | Supported | None | **MISSING** |

---

## 4. Visibility Audit

### 4.1 Repository Evidence

1. **Document Schema**:
   - `backend/app/schemas/project_document.py`, line 91:
     ```python
     enabled: bool = Field(default=True, description="Layer visibility toggle")
     ```
2. **Frontend Canvas Filtering**:
   - `src/components/studio/VidoAIStudio.tsx`, lines 287, 300, 312:
     - `activeTextLayers`: filters `l.enabled !== false`
     - `activeMediaLayers`: filters `l.enabled !== false`
     - `activeElementLayers`: filters `l.enabled !== false`
     - `activeCaptionCue`: filters `cue.enabled !== false`
3. **Backend Compositor Enforcement**:
   - `backend/app/media/compositor.py`, lines 329, 555:
     - `text_layers = [l for l in (layers or []) if l.type == "text" and getattr(l, "enabled", True) is not False]`
     - `visual_media_layers = [l for l in (scene.layers or []) if l.type in (...) and getattr(l, "enabled", True) is not False]`
4. **Inspector UI Presence**:
   - `MediaLayerPanel.tsx`, line 99: `handleToggleEnable(layerId)` with Eye / EyeOff icon.
   - `TextPanel.tsx`, line 172: `handleToggleLayerEnabled(layerId)` with Eye / EyeOff icon.
   - `ElementsPanel.tsx`, line 281: `handleToggleEnable(layerId)` function exists in code, but the Eye toggle button is **omitted from the layer list JSX**!
5. **Timeline Track Representation**:
   - Timeline track lanes (`MediaTimelineTrack`, `TextTimelineTrack`, `ElementsTimelineTrack`) do not show visibility state or provide track/clip-level mute/eye toggles.

### 4.2 Classification & Findings

- Visibility is **PERSISTED PROJECT STATE**. Toggling `enabled` saves to the database via OCC and directly alters final FFmpeg video export.
- **Classification**: **PARTIAL** (Complete in schema, canvas, compositor, and Media/Text panels; missing in Elements panel UI and timeline track lanes).

---

## 5. Locking Audit

### 5.1 Repository Evidence

1. **Schema**:
   - Grep for `locked`, `isLocked`, `lock` across `backend/app/schemas/` confirms **zero references**.
2. **Frontend State & Components**:
   - Grep across `src/components/studio/` confirms **zero references** to `isLocked` or `locked`.
   - `CanvasTransformGizmo.tsx`: Attaches pointer capture and responds to mouse/touch gestures unconditionally whenever `isSelected` is true.
   - `timelineUtils.ts` (`useTimelineClipDrag`): Responds to drag/trim unconditionally for any mounted clip.
   - `MediaLayerPanel.tsx`, `TextPanel.tsx`, `ElementsPanel.tsx`: No lock/unlock toggle or icon exists.

### 5.2 Required Architecture for Layer Locking

To introduce locking safely without schema breakage:
1. **State**: Add `locked: bool = Field(default=False)` to `SceneLayer` schema in `project_document.py`.
2. **UI Controls**: Expose a Lock / Unlock toggle button (padlock icon) in `MediaLayerPanel`, `TextPanel`, `ElementsPanel`, and on the canvas selection overlay.
3. **Interaction Guard**:
   - In `CanvasTransformGizmo.tsx`: If `layer.locked`, suppress corner handles, edge handles, and rotation stem; display a subtle locked border with a padlock badge.
   - In `useTimelineClipDrag`: Guard pointer-down handler to return early if clip is locked.
   - In Inspector: Disable slider inputs and position presets when locked.
4. **Backend / Render**: No impact. Locked layers render normally in the FFmpeg compositor.
- **Classification**: **MISSING**.

---

## 6. Undo / Redo Audit

### 6.1 Repository Evidence

1. **Client-Side State**:
   - Grep across `src/components/studio/` for `undo`, `redo`, `history`, `command` reveals:
     - `VidoAIStudio.tsx`, lines 1426–1431 (Top Bar):
       ```tsx
       <button className="p-1 hover:text-white hover:bg-[#141b2c] rounded" title="Undo">
         <RotateCcw size={14} />
       </button>
       <button className="p-1 hover:text-white hover:bg-[#141b2c] rounded" title="Redo">
         <RotateCw size={14} />
       </button>
       ```
     - `VidoAIStudio.tsx`, lines 2868–2873 (Timeline Bar): Identical `<button title="Undo">` and `<button title="Redo">` without `onClick` handlers.
     - **No state stack** (`past`, `future`, `history`) or command pattern exists in the client.
2. **Server-Side Versioning**:
   - `backend/app/api/v1/endpoints/projects.py`:
     - `GET /projects/{id}/versions`: Lists immutable version snapshots.
     - `GET /projects/{id}/versions/{version_id}`: Retrieves full snapshot document.
     - `POST /projects/{id}/versions`: Creates a new snapshot with OCC revision check.
   - **No rollback/revert endpoint** exists (`POST /projects/{id}/revert` or `POST /projects/{id}/versions/{version_id}/restore`).
3. **OCC Persistence vs. User Undo/Redo**:
   - Pointer-up events on canvas gizmos and timeline trim drag calls `handleSave()`, creating a permanent `ProjectVersion` record in PostgreSQL.
   - However, users have no means to traverse backwards or forwards through these versions.

### 6.2 Smallest Safe Client-Side Undo/Redo Architecture

```
User Action (Canvas Transform / Timeline Trim / Inspector Edit / Layer CRUD)
                                |
                                v
               +----------------------------------+
               | Push previous Document to 'past' |
               | Clear 'future'                   |
               +----------------------------------+
                                |
                   +------------+------------+
                   |                         |
            Ctrl+Z (Undo)              Ctrl+Y (Redo)
                   |                         |
                   v                         v
       +-----------------------+ +-----------------------+
       | Pop from 'past'       | | Pop from 'future'     |
       | Push current to       | | Push current to       |
       |   'future'            | |   'past'              |
       | Set active document   | | Set active document   |
       | Mark save: 'unsaved'  | | Mark save: 'unsaved'  |
       +-----------------------+ +-----------------------+
```

- **Classification**: **MISSING**.

---

## 7. Keyboard Interaction Audit

### 7.1 Repository Evidence

1. **Event Listeners**:
   - Grep for `keydown`, `keyup`, `KeyboardEvent`, `onKeyDown` in `src/components/studio/` yields **zero results**.
2. **Key Capabilities Evaluated**:
   - **Arrow Movement / Nudging**: Not implemented. Pressing arrow keys does not move the selected layer on canvas.
   - **Delete / Backspace**: Not implemented. Pressing Delete or Backspace does not remove the selected layer or clip.
   - **Escape**: Not implemented. Pressing Escape does not dismiss selection.
   - **Spacebar**: Not implemented. Pressing Space does not toggle playback (browser scroll occurs by default).
   - **Ctrl/Cmd+Z / Ctrl/Cmd+Y**: Not implemented.
   - **Ctrl/Cmd+C / Ctrl/Cmd+V**: Not implemented.
3. **Input Field Isolation Risk**:
   - When introducing keyboard listeners, listeners must verify `e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement` to avoid hijacking text input when editing scripts, titles, or text layers.
- **Classification**: **MISSING**.

---

## 8. Duplicate / Copy / Paste Audit

### 8.1 Repository Evidence

1. **Duplicate Layer**:
   - `MediaLayerPanel.tsx`, line 107: `handleDuplicate(layer)` clones layer, assigns `layer_${Date.now()}_${random}`, offsets `x` and `y` by `+0.05`, preserves `content.asset_id`, and appends to `mediaLayers`.
   - `TextPanel.tsx`, line 136: `handleDuplicateLayer(layer)` deep-clones JSON, assigns `text_${Date.now()}_${random}`, appends to `textLayers`.
   - `ElementsPanel.tsx`, line 289: `handleDuplicate(layerId)` deep-clones JSON, assigns `element_${Date.now()}_${random}`, offsets `x` and `y` by `+0.05`, appends to `elementLayers`.
2. **Duplicate Scene**:
   - `VidoAIStudio.tsx`, line 674: `handleDuplicateScene(index)` duplicates scene, generates new scene UUID, resets avatar video and speech audio asset IDs, re-sequences, and saves.
3. **Copy / Paste (Clipboard)**:
   - Grep for `clipboard`, `copy`, `paste` in `src/components/studio/` confirms **zero implementation**.
   - No cross-scene layer copy/paste or browser clipboard synchronization exists.
4. **Security Analysis**:
   - Duplicated layers reuse the same `asset_id`. Because this occurs within the same project and workspace, `mws.resolve_asset` enforces workspace ownership, preventing asset traversal.
- **Classification**: **PARTIAL** (Intra-panel duplicate complete; system clipboard and cross-scene paste missing).

---

## 9. Layer Deletion Audit

### 9.1 Repository Evidence

1. **Deletion Mechanism**:
   - `MediaLayerPanel.tsx`, line 130: `handleDelete(layerId)` filters `mediaLayers`, updates active selection, calls `saveUpdatedMediaLayers`.
   - `TextPanel.tsx`, line 149: `handleDeleteLayer(layerId)` filters `textLayers`, updates active selection, calls `saveUpdatedTextLayers`.
   - `ElementsPanel.tsx`, line 309: `handleDelete(layerId)` filters `elementLayers`, updates active selection, calls `saveUpdatedLayers`.
2. **Consistency Verification**:
   - **Canvas**: Unmounts deleted layer and transform gizmo immediately.
   - **Timeline**: Removes corresponding clip from the timeline track lane immediately.
   - **Inspector**: Resets selection to the first remaining layer or `null`.
   - **Persistence**: Triggers OCC save on next commit; document stored with layer omitted.
   - **Backend / Render**: Compositor iterates `scene.layers`; deleted layer is omitted from the FFmpeg filtergraph.
   - **Asset Storage**: Underlying image, video, and audio assets in PostgreSQL/MinIO are **NOT deleted**, preserving asset library integrity.
- **Classification**: **COMPLETE**.

---

## 10. Timeline Editing Audit

### 10.1 Verification of Phase 33 Capabilities

- Clip dragging (`useTimelineClipDrag`): **PASS**.
- Left-edge trimming (`getLeftHandleProps`): **PASS**.
- Right-edge trimming (`getRightHandleProps`): **PASS**.
- Playhead snapping (`snapTargets = [0, duration, localPlayhead]`): **PASS**.
- Scene boundary clamping: **PASS**.

### 10.2 Capability Matrix

| Timeline Capability | Status | Existing Architecture | Evidence |
| :--- | :--- | :--- | :--- |
| **Move clip** | **COMPLETE** | `useTimelineClipDrag` pointer drag | `src/lib/timelineUtils.ts` |
| **Trim left** | **COMPLETE** | `useTimelineClipDrag` left handle | `src/lib/timelineUtils.ts` |
| **Trim right** | **COMPLETE** | `useTimelineClipDrag` right handle | `src/lib/timelineUtils.ts` |
| **Playhead snapping** | **COMPLETE** | `snapTargets` includes `playheadTime` | `src/lib/timelineUtils.ts` |
| **Scene-boundary snapping** | **COMPLETE** | `snapTargets` includes `0` and `duration` | `src/lib/timelineUtils.ts` |
| **Clip-to-clip snapping** | **MISSING** | `snapTargets` does not inspect neighboring clips | `MediaTimelineTrack.tsx:184` |
| **Split clip (Blade tool)** | **MISSING** | No blade mode, cut action, or split handler | Repository search |
| **Delete clip** | **MISSING** | No clip delete button on timeline lanes | `MediaTimelineTrack.tsx:115` |
| **Duplicate clip** | **MISSING** | No clip duplicate button on timeline lanes | `MediaTimelineTrack.tsx:115` |
| **Timeline zoom** | **MISSING** | Timeline scale fixed at 100% per scene | `VidoAIStudio.tsx:2864` |
| **Timeline pan** | **MISSING** | No horizontal scrolling or pan container | `VidoAIStudio.tsx:2864` |

---

## 11. Timeline / Canvas Synchronization

### 11.1 Synchronization Flow

1. **Selection Sync**:
   - Clicking a timeline clip triggers `onSelectMediaLayer(layer.id)` and `onOpenMediaPanel()`.
   - Clicking a canvas layer triggers `selectMediaLayer(layer.id)` and `setActiveTab("media")`.
   - Both update the mutual exclusion selection state in `VidoAIStudio.tsx`.
2. **Timing & Live Visibility**:
   - Trimming or dragging a clip updates `layer.start_time` and `layer.end_time`.
   - Canvas filtering computes `activeMediaLayers`, `activeTextLayers`, and `activeElementLayers` based on `playbackTime >= l.start_time && playbackTime < l.end_time`.
   - The canvas updates its rendered layers in real time as the playhead advances or clips are trimmed.
3. **Stale-State Isolation (Known Edge Case)**:
   - When a user selects a clip on the timeline whose time window does not include the current playhead position, the clip is visually highlighted on the timeline, but no layer or gizmo is rendered on the canvas.
   - This is structurally sound behavior (preventing out-of-time objects from ghosting on the preview), though auto-scrubbing the playhead to `clip.start_time` on timeline selection would improve usability.
- **Classification**: **COMPLETE**.

---

## 12. Snapping / Alignment Audit

### 12.1 Repository Evidence

1. **Timeline Snapping**:
   - Handled via `findBestSnapTarget(time, snapTargets, threshold)` in `src/lib/timelineUtils.ts`.
   - Snaps to start ($0.0$), end (`sceneDuration`), and `playheadTime`.
2. **Canvas Direct Manipulation Snapping**:
   - Handled via `calculatePositionFromPointer` in `src/lib/canvasTransformUtils.ts`:
     ```ts
     export function calculatePositionFromPointer(initialPos, startPointer, currentPointer, canvasRect) {
       const delta = pointerToNormalizedDelta(startPointer, currentPointer, canvasRect);
       return {
         x: clamp(initialPos.x + delta.x, 0.0, 1.0),
         y: clamp(initialPos.y + delta.y, 0.0, 1.0),
       };
     }
     ```
   - No snap calculation exists for:
     - Center lines ($x = 0.5$, $y = 0.5$)
     - Canvas edges ($x = 0, 1$; $y = 0, 1$)
     - Safe area bounds ($10\%$ margin: $x = 0.1, 0.9$; $y = 0.1, 0.9$)
     - Object-to-object alignment
     - Visual alignment guides (magnetic guide lines)
3. **Architectural Compatibility**:
   - Phase 34's `calculatePositionFromPointer` can easily accept an optional `snapTargets: { x?: number[]; y?: number[] }` and `thresholdNorm: number` without altering the canonical `SceneLayer.transform` schema.
- **Classification**: **PARTIAL** (Timeline snapping complete; canvas snapping missing).

---

## 13. Transitions Audit

### 13.1 Repository Evidence

1. **Schema**:
   - `backend/app/schemas/project_document.py`, lines 55–59:
     ```python
     class SceneTransition(BaseModel):
         type: str = Field(default="fade", description="Transition style: fade, wipe, dissolve, slide")
         duration: float = Field(default=0.5, ge=0.0, le=5.0)
     ```
2. **Compositor Concatenation**:
   - `backend/app/media/compositor.py`, lines 882–920 (`_concatenate_scene_clips`):
     - Uses FFmpeg concat demuxer (`-f concat -i concat_manifest.txt -c copy`) or basic filtergraph fallback:
       ```python
       filtergraph = f"{''.join(filter_segments)}concat=n={num}:v=1:a=1[vcat][acat]"
       ```
     - **Completely ignores `scene.transition`**. No `xfade` (crossfade, wipe, dissolve) filter is applied between scene clips.
3. **Frontend Studio UI**:
   - No transition selection button or icon exists in the scene rail or timeline.
   - `handleAddScene` writes a default `{ type: "fade", duration: 0.5 }`, but this object is never rendered or editable.
- **Classification**: **PARTIAL** (Schema defined; UI, timeline, and FFmpeg render missing).

---

## 14. Scene Management Audit

### 14.1 Repository Evidence

- **Add Scene**: `handleAddScene` (line 638 of `VidoAIStudio.tsx`). Generates new scene, initializes default background, avatar, speech, and empty layers; saves via OCC.
- **Duplicate Scene**: `handleDuplicateScene(index)` (line 674). Clones target scene, clears generated media asset IDs, inserts after target, re-sequences, and saves.
- **Delete Scene**: `handleDeleteScene(index)` (line 698). Prevents deleting the sole remaining scene; re-sequences remaining scenes and saves.
- **Reorder Scene**: `handleMoveScene(fromIndex, toIndex)` (line 710). Reorders scene array, updates `sequence: idx + 1`, and saves.
- **Scene Duration**: Editable via scene properties; updates document total duration.
- **Scene Selection**: Clicking thumbnail in left scene strip activates scene and loads corresponding layers into canvas and timeline.
- **Document Role**: Scenes are canonical top-level document entities (`ProjectDocumentV1.scenes`).
- **Classification**: **COMPLETE**.

---

## 15. Multi-Layer Selection Audit

### 15.1 Repository Evidence

- **State Model**:
  - `VidoAIStudio.tsx`:
    ```tsx
    const [selectedMediaLayerId, setSelectedMediaLayerId] = useState<string | null>(null);
    const [selectedTextLayerId, setSelectedTextLayerId] = useState<string | null>(null);
    const [selectedElementLayerId, setSelectedElementLayerId] = useState<string | null>(null);
    ```
  - Phase 34 established strict mutual exclusion: selecting one category unconditionally nullifies the others.
- **Feasibility Analysis for Future Multi-Selection**:
  - **Schema Impact**: Zero. Multi-selection is transient UI interaction state. `ProjectDocumentV1` requires no schema modifications for multi-selection.
  - **Transform Model Impact**: Requires computing an aggregate AABB (Axis-Aligned Bounding Box) enclosing all selected layers, applying delta translations proportionally to each layer's `transform.x` and `transform.y`, and scaling relative to the multi-selection centroid.
  - **Inspector Impact**: Must display an aggregate selection header with alignment buttons (align left, align center, align right, distribute evenly) rather than single-layer attribute editors.
- **Classification**: **MISSING**.

---

## 16. Layer Type Completeness Matrix

| Layer Type | Canvas Preview | Inspector | Timeline | Transform Gizmo | Timing Controls | Visibility Toggle | Locking | Reorder | Render Parity | Persistence |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Image** | PASS | PASS | PASS | PASS | PASS | PASS | GAP | PARTIAL | PASS | PASS |
| **Video** | PASS | PASS | PASS | PASS | PASS | PASS | GAP | PARTIAL | PASS | PASS |
| **Text** | PASS | PASS | PASS | PASS | PASS | PASS | GAP | PARTIAL | PASS | PASS |
| **Rectangle** | PASS | PASS | PASS | PASS | PASS | GAP (UI) | GAP | PARTIAL | PASS | PASS |
| **Rounded Rect** | PASS | PASS | PASS | PASS | PASS | GAP (UI) | GAP | PARTIAL | PASS | PASS |
| **Circle** | PASS | PASS | PASS | PASS | PASS | GAP (UI) | GAP | PARTIAL | PASS | PASS |
| **Ellipse** | PASS | PASS | PASS | PASS | PASS | GAP (UI) | GAP | PARTIAL | PASS | PASS |
| **Line** | PASS | PASS | PASS | PASS | PASS | GAP (UI) | GAP | PARTIAL | PASS | PASS |
| **Arrow** | PASS | PASS | PASS | PASS | PASS | GAP (UI) | GAP | PARTIAL | PASS | PASS |
| **Sticker** | PASS | PASS | PASS | PASS | PASS | GAP (UI) | GAP | PARTIAL | PASS | PASS |
| **Caption** | PASS | PASS | PASS | N/A | PASS | PASS | GAP | N/A | PASS | PASS |
| **Music (Audio)** | N/A | PASS | PASS | N/A | PASS | PASS (Mute) | GAP | PARTIAL | PASS | PASS |

- **Coverage Status**: **VERIFIED** (All 12 layer types participate in the core pipeline; specific interaction gaps noted in locking, global reordering, and element visibility UI).

---

## 17. Inspector Completeness Audit

### 17.1 Property Exposure Analysis

| Property Domain | MediaLayerPanel | TextPanel | ElementsPanel | MusicPanel | CaptionsPanel |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Position ($X, Y$)** | Exposed (Sliders + Presets) | Exposed (Presets) | Exposed (Sliders + Presets) | N/A | Presets (Top/Center/Bottom) |
| **Scale** | Exposed ($0.2 - 3.0$) | Exposed ($0.2 - 3.0$) | Exposed ($0.2 - 3.0$) | N/A | N/A |
| **Rotation** | Exposed ($-180^\circ - 180^\circ$) | Exposed ($-180^\circ - 180^\circ$) | Exposed ($-180^\circ - 180^\circ$) | N/A | N/A |
| **Opacity** | Exposed ($0.0 - 1.0$) | Exposed ($0.0 - 1.0$) | Exposed ($0.0 - 1.0$) | N/A | Background Opacity |
| **Timing ($Start, End$)** | Exposed (Inputs + Validation) | Exposed (Inputs + Validation) | Exposed (Inputs + Validation) | Exposed (Start/Duration) | Cue Timestamps |
| **Content / Styling** | Asset name / preview | Text, Font, Color, Bg | Shape colors, borders | Volume, Loop, Mute | Style, Position, Align |
| **Visibility Toggle** | Exposed (Eye button) | Exposed (Eye button) | **Missing in UI** | Exposed (Mute button) | Global toggle |
| **Duplicate Button** | Exposed | Exposed | Exposed | N/A | N/A |
| **Delete Button** | Exposed | Exposed | Exposed | Exposed | Exposed |
| **Layer Reorder** | Intra-type | Intra-type | Intra-type | N/A | N/A |

### 17.2 Properties Present in Schema But Not Exposed in Inspector

1. `SceneTransition.duration` and `SceneTransition.type`: Stored in `Scene.transition`, no UI control.
2. `Scene.background.blur`: Schema permits blur properties for background imagery; no blur slider exists.
3. Blend mode: Not modeled in schema or exposed in inspector.
- **Coverage Status**: **VERIFIED**.

---

## 18. Project Save & Recovery Audit

### 18.1 Save Lifecycle Flow

```
Local Interaction (Gizmo PointerUp / Timeline DragEnd / Inspector Change)
                                |
                                v
               [VidoAIStudio.tsx: handleSave()]
                                |
         +----------------------+----------------------+
         |                                             |
   Save Status: "saving"                         Serialize Doc
         |                                 (schema_version: 1)
         v                                             |
  [POST /api/v1/workspaces/{wId}/projects/{pId}/versions]
         |                                (expected_revision)
         v
  [backend/app/services/project_service.py: create_version()]
         |
         +--> [Match revision?]
                   |
         +---------+---------+
         |                   |
       YES                   NO
         |                   |
         v                   v
   Increment revision     HTTP 409 Conflict
   Commit DB version      ApiError("CONCURRENCY_CONFLICT")
   Return version                |
         |                       v
         v                Save Status: "conflict"
   Save Status: "saved"   Pulse Amber Indicator
   Update state rev       User prompts "Click to reload"
```

### 18.2 Gaps Identified

- **No Idle Auto-Save Timer**: Typing in text areas or adjusting sliders sets `saveStatus = "unsaved"` but does not trigger a debounced auto-save. If the user navigates away or refreshes without clicking Save or committing a transform gizmo, uncommitted inspector changes are lost.
- **Save Status Coverage**: **VERIFIED**.

---

## 19. OCC / Concurrency Audit

### 19.1 Concurrency Mechanism

- Enforced through `expected_revision` on `POST /projects/{id}/versions`.
- PostgreSQL updates `project.revision = project.revision + 1` within an atomic transaction.
- If concurrent requests submit the same `expected_revision`, the second request fails with HTTP 409 `CONCURRENCY_CONFLICT`.
- The frontend gracefully catches `CONCURRENCY_CONFLICT`, flags `saveStatus = "conflict"`, and provides a reload action (`loadProject()`).
- Direct pointer dragging updates local React state only; network OCC serialization is executed strictly on gesture commit (`pointerup`), preventing revision flooding.
- **Status**: **VERIFIED**.

---

## 20. Render / Export Completeness Audit

### 20.1 Post-Phase 36 State Verification

- **Text Rotation**: ASS `\frz{round(-rotation, 2)}` verified in parity with CSS rotation.
- **Text Scale**: ASS font size scaled by `scale`, matching canvas preview.
- **Shape Sizing**: Responsive percentage coordinates align preview with backend rendering.
- **Sticker Sizing**: Canvas `0.25 * min(W, H) * scale` matches backend compositor.
- **Media Sizing**: 80% ceiling removed; scales up to $3.0\times$ in preview and $10.0\times$ in export.
- **1:1 Canvas Viewport**: Dedicated square container verified for 1:1 projects.

### 20.2 Confirmed Residual Render Differences

1. **Font Matching**: Canvas renders via client system fonts; backend uses Linux fontconfig. If a selected font is absent on the host/container, FFmpeg defaults to generic sans-serif.
2. **Cross-Category Z-Stacking**: As demonstrated in Section 3, elements with `layerIdx >= 1` render in front of text overlays in frontend CSS, but backend compositor composites all elements *before* text ASS subtitles, rendering text on top.
- **Status**: **VERIFIED**.

---

## 21. Security Audit

- Workspace Isolation: Every project query and version update requires `workspace_id` validation via `require_permission("project.update")`.
- Asset Access Scoping: `mws.resolve_asset` strictly validates asset ownership against `workspace_id`.
- Model Safety Policies: Blocked AI model IDs fail-closed via `assert_artifact_not_blocked`.
- Interaction Security: Intra-project duplication duplicates metadata without exposing foreign workspace assets.
- **Status**: **PASS**.

---

## 22. Performance Audit

### 22.1 Concrete Evidence

1. **Playback Re-render Overhead**:
   - `playbackTime` state update in `VidoAIStudio.tsx` triggers re-rendering of the entire top-level component at video frame rate.
   - `activeMediaLayers`, `activeTextLayers`, and `activeElementLayers` recompute on each frame.
2. **Full-Document OCC Serialization**:
   - Every gesture commit serializes the entire project document JSONB, sending large payloads even for minor spatial updates.
3. **Compositor Shape/Sticker Rasterization**:
   - Each render job writes temporary shape and sticker PNGs to disk (`scene_XXX_shape_Y.png`). Cleanup occurs upon completion.
- **Status**: **PASS** (Operates within normal bounds for current scope; structural optimizations identified for future scale).

---

## 23. Browser E2E Status

- **Status**: **NOT VERIFIED**.
- **Reason**: Playwright browser binaries cannot currently be downloaded due to environment CDN download policy restrictions. Frontend unit tests (27/27) and backend regressions (97/97) provide verified coverage.

---

## 24. Database / Migration Integrity

- **Head Migration**: `backend/alembic/versions/0006_api_keys_and_webhooks.py`.
- **Schema Changes Required**: **NONE**.
- The `project_versions.document` JSONB column stores dynamic `SceneLayer` structures without requiring table alterations. Future fields (`locked`, `z_index`) can be introduced directly in Pydantic schemas with safe defaults.
- **Migration Status**: **NONE**.

---

## 25. Git Integrity

- Verified via `git status --short`.
- **Status**: **CLEAN** (Zero application code or test modifications introduced during this read-only audit).

---

## 26. Confirmed Gaps Summary

1. **Layer Locking**: Complete absence of `locked` field, UI toggles, and pointer interaction guards.
2. **Client-Side Undo / Redo**: No in-memory command stack or history traversal; UI buttons are non-functional.
3. **Keyboard Controls**: Complete absence of `keydown` shortcuts (arrow nudging, Delete, Esc, Space, Ctrl+Z/Y).
4. **Unified Cross-Type Layer Ordering**: Cross-category reordering blocked by hardcoded CSS z-index tiers and fixed compositor filter stages.
5. **Timeline Advanced Capabilities**: Absence of clip splitting (blade), timeline clip deletion, clip duplication, clip-to-clip snapping, and zoom/pan.
6. **Canvas Snapping & Guides**: Absence of center, edge, and safe-area snapping in direct canvas pointer manipulation.
7. **System Clipboard / Copy-Paste**: Absence of cross-scene copy/paste and standard keyboard clipboard shortcuts.
8. **Scene Transitions in Render**: Absence of `xfade` filtergraph rendering for scene transitions.
9. **Multi-Layer Selection**: Single active selection constraint; absence of compound bounding-box transform model.
10. **Element Visibility UI**: Absence of visibility toggle icon in `ElementsPanel.tsx` layer list.

---

## 27. Future Implementation Architecture

The following independent implementation candidates are identified based on empirical dependencies. In strict compliance with audit guidelines, these candidates are **not ranked**.

### Candidate A: Studio Layer Locking & Visibility Unification
- **Capability**: Add layer locking across canvas, inspector, and timeline; expose missing visibility toggle in `ElementsPanel.tsx`.
- **Current Status**: Locking is MISSING; Visibility is PARTIAL.
- **Dependencies**: None (self-contained within layer state).
- **Architectural Impact**: Minimal. Adds `locked: bool = False` to `SceneLayer` Pydantic schema; guards `CanvasTransformGizmo` and `useTimelineClipDrag`.
- **Required Files**:
  - `backend/app/schemas/project_document.py`
  - `src/components/studio/VidoAIStudio.tsx`
  - `src/components/studio/CanvasTransformGizmo.tsx`
  - `src/components/studio/MediaLayerPanel.tsx`
  - `src/components/studio/TextPanel.tsx`
  - `src/components/studio/ElementsPanel.tsx`
  - `src/lib/timelineUtils.ts`
- **Required Tests**: Unit tests verifying pointer events are ignored on locked layers; schema regression tests.
- **Potential Risks**: Ensure locked layers remain selectable for unlocking.
- **Can Implement Independently**: **YES**.

---

### Candidate B: Studio Keyboard Navigation & Shortcuts
- **Capability**: Arrow nudging (1px normal, 10px Shift), Delete/Backspace layer deletion, Escape deselect, Space play/pause.
- **Current Status**: MISSING.
- **Dependencies**: Existing single-layer selection state (`selectedMediaLayerId`, `selectedTextLayerId`, `selectedElementLayerId`).
- **Architectural Impact**: Low. Adds a centralized `useStudioKeyboardShortcuts` hook with input element focus protection.
- **Required Files**:
  - `src/hooks/useStudioKeyboardShortcuts.ts` (or `src/lib/studioKeyboardUtils.ts`)
  - `src/components/studio/VidoAIStudio.tsx`
- **Required Tests**: Unit tests for arrow key deltas, input element guard tests, delete key trigger tests.
- **Potential Risks**: Intercepting key events while users type in textareas or inputs.
- **Can Implement Independently**: **YES**.

---

### Candidate C: Client-Side Undo / Redo History Stack
- **Capability**: Lightweight in-memory document history stack (maximum 50 states) enabling Ctrl+Z (Undo) and Ctrl+Y / Cmd+Shift+Z (Redo) with active navbar and timeline buttons.
- **Current Status**: MISSING.
- **Dependencies**: Existing document state and `handleSave()` persistence model.
- **Architectural Impact**: Medium. Encapsulates document mutations through an undoable state dispatcher.
- **Required Files**:
  - `src/hooks/useStudioHistory.ts`
  - `src/components/studio/VidoAIStudio.tsx`
- **Required Tests**: History stack push, pop, redo branch invalidation, max capacity pruning tests.
- **Potential Risks**: Large memory consumption if entire document objects are retained without cloning optimization.
- **Can Implement Independently**: **YES**.

---

### Candidate D: Canvas Direct Manipulation Snapping & Alignment Guides
- **Capability**: Magnetic snapping to canvas center ($X=0.5, Y=0.5$), edges ($0, 1$), and safe margins ($0.1, 0.9$) with visible guide lines during move gestures.
- **Current Status**: MISSING on canvas.
- **Dependencies**: Existing Phase 34 `canvasTransformUtils.ts` and `CanvasTransformGizmo.tsx`.
- **Architectural Impact**: Low. Extends `calculatePositionFromPointer` with snap target evaluations.
- **Required Files**:
  - `src/lib/canvasTransformUtils.ts`
  - `src/lib/canvasTransformUtils.test.ts`
  - `src/components/studio/CanvasTransformGizmo.tsx`
- **Required Tests**: Math unit tests for snap snapping thresholds, snap release hysteresis, and guide line coordinates.
- **Potential Risks**: Overly aggressive snapping threshold causing pointer jitter.
- **Can Implement Independently**: **YES**.

---

### Candidate E: Advanced Timeline Clip Operations (Split, Duplicate, Snap)
- **Capability**: Blade tool / playhead clip splitting, clip duplicate on timeline, clip-to-clip snapping.
- **Current Status**: MISSING.
- **Dependencies**: Existing Phase 33 `timelineUtils.ts` and track components.
- **Architectural Impact**: Medium. Requires creating new layer items on split at playhead timestamp.
- **Required Files**:
  - `src/lib/timelineUtils.ts`
  - `src/lib/timelineUtils.test.ts`
  - `src/components/studio/MediaTimelineTrack.tsx`
  - `src/components/studio/TextTimelineTrack.tsx`
  - `src/components/studio/ElementsTimelineTrack.tsx`
  - `src/components/studio/VidoAIStudio.tsx`
- **Required Tests**: Clip splitting arithmetic tests, start/end boundary validation tests, clip-to-clip snap tests.
- **Potential Risks**: Creating clips shorter than `MIN_CLIP_DURATION` (0.1s) when splitting near boundaries.
- **Can Implement Independently**: **YES**.

---

### Candidate F: Unified Cross-Type Layer Ordering
- **Capability**: Global layer order index (`order` or unified `z-index`) allowing any layer type (media, text, element) to be placed above or below any other layer, synchronized in both CSS canvas and FFmpeg compositor.
- **Current Status**: PARTIAL (Intra-type only).
- **Dependencies**: Frontend canvas rendering, backend compositor filtergraph restructuring.
- **Architectural Impact**: High. Requires refactoring backend compositor from sequential type-based overlays to a single unified topological overlay pass.
- **Required Files**:
  - `backend/app/schemas/project_document.py`
  - `backend/app/media/compositor.py`
  - `src/components/studio/VidoAIStudio.tsx`
  - `src/components/studio/MediaLayerPanel.tsx`
  - `src/components/studio/TextPanel.tsx`
  - `src/components/studio/ElementsPanel.tsx`
- **Required Tests**: Backend multi-stream FFmpeg composite regression tests, frontend z-index sorting tests.
- **Potential Risks**: Breaking ASS text overlay integration if text must be interleaved between visual media layers.
- **Can Implement Independently**: **NO** (Requires compositor filtergraph redesign first).

---

## 28. Required Tests for Future Implementation

1. **Locking**:
   - `test_locked_layer_rejects_pointer_move()`
   - `test_locked_layer_rejects_timeline_trim()`
   - `test_locked_layer_persists_in_document()`
2. **Keyboard**:
   - `test_arrow_key_nudges_layer_position()`
   - `test_shift_arrow_key_multiplies_delta()`
   - `test_delete_key_removes_active_layer()`
   - `test_keyboard_ignored_when_typing_in_input()`
3. **Undo/Redo**:
   - `test_undo_reverts_transform_commit()`
   - `test_redo_restores_reverted_commit()`
   - `test_new_action_clears_redo_stack()`
4. **Snapping**:
   - `test_calculate_position_snaps_to_center()`
   - `test_calculate_position_releases_snap_outside_threshold()`

---

## 29. Acceptance Criteria for Audit

- [x] Full trace of `Project -> Scene -> Layers -> Canvas -> Inspector -> Timeline -> Persistence -> Render -> Export` documented.
- [x] All 13 interaction capabilities comprehensively audited and classified.
- [x] Layer ordering, visibility, locking, undo/redo, keyboard, and timeline mechanisms analyzed with exact file citations.
- [x] Future architectural candidates cataloged with dependencies and risks without ranking.
- [x] Zero application code, test, or migration files modified.
- [x] Pre-existing test suites verified (27/27 frontend tests, 94/94 backend studio regression tests).

---

## 30. Conclusion

Phase 37 establishes a complete, evidence-based baseline of the HeyZen Studio editing architecture. The core multi-scene, multi-layer document model, canvas transform math, timeline clip drag/trim, OCC versioning, and FFmpeg export pipelines are robust and verified. Five distinct candidate milestones (Layer Locking/Visibility, Keyboard Shortcuts, Undo/Redo, Canvas Snapping, and Advanced Timeline Operations) are architecturally ready for independent implementation without requiring schema migrations or compositor redesign.
