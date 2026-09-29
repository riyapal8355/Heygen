# Phase 34 — Studio Canvas Direct Manipulation Audit

**Document Version:** 1.0.0  
**Audit Timestamp:** 2026-09-21T12:45:00Z  
**Repository:** `d:\HeyGen\video-ai-tools`  
**Status:** `AUDIT COMPLETE — IMPLEMENTATION ARCHITECTURE READY`  

---

## 1. Executive Summary

This document delivers a comprehensive, read-only, evidence-driven architectural audit of the HeyZen Studio canvas manipulation subsystem prior to implementing **Phase 34 — Studio Canvas Direct Manipulation Gizmos**.

The goal of Phase 34 is to introduce intuitive, direct canvas editing capabilities (drag-to-move, bounding-box selection, corner/edge resizing, rotation handle, live Inspector synchronization, and timeline synchronization) while maintaining strict parity with the FFmpeg compositor.

### Baseline Status
* **Phase 33 Verified Baseline:** 12/12 timeline manipulation tests passed.
* **Studio Regression Baseline:** 74/74 backend Studio tests passed (`test_studio_interactive_timeline.py`, `test_studio_elements_shapes_stickers.py`, `test_studio_media_layers.py`, `test_studio_text.py`, `test_studio_captions.py`, `test_studio_music_media.py`, `test_studio_pipeline_e2e.py`, `test_timeline_compositor.py`).
* **Frontend TypeScript:** Clean (`npx tsc --noEmit` exited with code 0).
* **Production Build:** Passing (`npm run build` completed in Turbopack with 0 errors).
* **Database Schema & Migrations:** Head migration remains `0006_api_keys_and_webhooks.py`; 0 new migrations added.
* **Protected Files:** `package.json`, `package-lock.json`, and `public/` are completely unmodified.
* **Browser E2E:** Explicitly recorded as `BROWSER E2E NOT VERIFIED` due to host environment network CDN restrictions on browser downloads.

### Primary Audit Conclusion
The Studio's canonical transform model is a **normalized center-anchored coordinate system**:
$$\text{Position: } x \in [0.0, 1.0], \quad y \in [0.0, 1.0]$$
$$\text{Scale: } \text{uniform multiplier } \ge 0.05 \quad (\text{default } 1.0)$$
$$\text{Rotation: } \text{clockwise degrees } \in [-180^\circ, +180^\circ] \quad (\text{default } 0.0^\circ)$$
$$\text{Anchor Point: } \text{exact center } (50\%, 50\%)$$

Direct canvas manipulation **can safely update this model directly without introducing a secondary transform system, without altering database schemas, and without running database migrations**.

---

## 2. Current Transform Architecture

The HeyZen transform pipeline connects user interactions directly to the final FFmpeg render graph through five well-defined architectural stages:

```
+-----------------------------------------------------------------------------+
| 1. User Interaction Surface (Canvas & Inspector)                            |
|    - Direct pointer drag / resize / rotate (Planned Phase 34 Gizmo)         |
|    - Inspector panel sliders & 9-point preset buttons (Elements/Media/Text) |
+-----------------------------------------------------------------------------+
                                      |
                                      v
+-----------------------------------------------------------------------------+
| 2. SceneLayer State Model (React State in VidoAIStudio.tsx)                 |
|    - layer.transform: { x: float, y: float, scale: float, rotation: float } |
|    - layer.content: { opacity: float, width?: float, height?: float }       |
|    - Synchronized live in memory across Canvas Viewport & Inspector         |
+-----------------------------------------------------------------------------+
                                      |
                                      v
+-----------------------------------------------------------------------------+
| 3. Frontend Canvas Preview (DOM / CSS Viewport)                             |
|    - left: `${x * 100}%`, top: `${y * 100}%`                                |
|    - transform: translate(-50%, -50%) rotate(${rotation}deg)                |
|    - width: relative % or calculated px, opacity: opacity                   |
+-----------------------------------------------------------------------------+
                                      |
                                      v
+-----------------------------------------------------------------------------+
| 4. Project Persistence & OCC (FastAPI + PostgreSQL JSONB)                   |
|    - POST /api/workspaces/{w_id}/projects/{p_id}/versions                   |
|    - Optimistic Concurrency Control (OCC) revision validation               |
|    - Immutable ProjectVersion snapshots in project_versions table           |
+-----------------------------------------------------------------------------+
                                      |
                                      v
+-----------------------------------------------------------------------------+
| 5. Backend Compositor & FFmpeg Render Engine (compositor.py)                |
|    - Media scaling: scale=target_w:target_h                                 |
|    - Rotation: rotate=m_rotation*PI/180:ow='hypot(iw,ih)':oh=ow:c=none      |
|    - Overlay center placement: x='main_w*pos_x - overlay_w/2'               |
|                                y='main_h*pos_y - overlay_h/2'               |
+-----------------------------------------------------------------------------+
```

---

## 3. SceneLayer Transform Schema

The canonical schema is declared in `backend/app/schemas/project_document.py` (lines 84–94):

```python
class SceneLayer(BaseModel):
    """Visual canvas layer (text, media, shape, sticker)."""
    id: str = Field(..., description="Unique layer ID")
    type: str = Field(..., description="Layer type: text, image, video, shape, sticker")
    name: str = Field(default="Layer")
    start_time: float = Field(default=0.0, ge=0.0)
    end_time: float = Field(default=5.0, ge=0.0)
    enabled: bool = Field(default=True, description="Layer visibility toggle")
    transform: Dict[str, Any] = Field(default_factory=dict)
    content: Dict[str, Any] = Field(default_factory=dict)
```

### Definitive Transform Specification Table

| Property | SceneLayer Field | Data Type | Coordinate Range / Units | Default | Optionality | Canvas Representation | Render Representation |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **X Position** | `transform.x` | `float` | Normalized $[0.0, 1.0]$ | `0.5` | Optional (defaults to 0.5) | `left: ${x * 100}%` | `main_w * pos_x` |
| **Y Position** | `transform.y` | `float` | Normalized $[0.0, 1.0]$ | `0.5` | Optional (defaults to 0.5) | `top: ${y * 100}%` | `main_h * pos_y` |
| **Scale** | `transform.scale` | `float` | Uniform multiplier $[0.05, 10.0]$ | `1.0` | Optional (defaults to 1.0) | Multiplier on layer width / CSS size | Multiplier on base pixel dimensions |
| **Rotation** | `transform.rotation` | `float` | Degrees $[-180.0, +180.0]$ | `0.0` | Optional (defaults to 0.0) | `rotate(${rotation}deg)` | `rotate=rad:ow='hypot(iw,ih)':oh=ow:c=none` |
| **Opacity** | `content.opacity` | `float` | Normalized $[0.0, 1.0]$ | `1.0` | Optional (defaults to 1.0) | `opacity: ${opacity}` | `colorchannelmixer=aa=${opacity}` |
| **Width** | `content.width` | `float` | Normalized $[0.0, 1.0]$ or px | `0.35` (shape) | Optional (shapes only) | Shape width sizing | `base_w = canvas.width * width` |
| **Height** | `content.height` | `float` | Normalized $[0.0, 1.0]$ or px | `0.20` (shape) | Optional (shapes only) | Shape height sizing | `base_h = canvas.height * height` |
| **Anchor X** | `NOT PRESENT` | N/A | Hardcoded Center ($50\%$) | N/A | N/A | `translate(-50%, ...)` | `- overlay_w / 2` |
| **Anchor Y** | `NOT PRESENT` | N/A | Hardcoded Center ($50\%$) | N/A | N/A | `translate(..., -50%)` | `- overlay_h / 2` |
| **Bounding Box** | `NOT PRESENT` | N/A | Calculated dynamically | N/A | N/A | DOM rect / CSS width & height | Probe / Raster dimensions |

> [!NOTE]
> Top-level `width`, `height`, `anchorX`, `anchorY`, and `transformMatrix` do **NOT** exist on `SceneLayer`. They are `NOT PRESENT` and must not be added to the schema.

---

## 4. Coordinate System

1. **Origin:** Top-left of the canvas viewport is $(0.0, 0.0)$.
2. **Horizontal Axis ($X$):**
   * $X = 0.0$: Left canvas boundary.
   * $X = 0.5$: Horizontal canvas midline.
   * $X = 1.0$: Right canvas boundary.
3. **Vertical Axis ($Y$):**
   * $Y = 0.0$: Top canvas boundary.
   * $Y = 0.5$: Vertical canvas midline.
   * $Y = 1.0$: Bottom canvas boundary.
4. **Resolution Independence:** All position coordinates are normalized fractions $[0.0, 1.0]$ relative to the canvas container width and height. When moving from a 768px preview canvas to a 1080p (1920×1080) or 4K render, coordinates remain completely identical.

---

## 5. Position Semantics

Across both the frontend canvas renderer and the backend FFmpeg compositor, the $(x, y)$ coordinate specifies the **center position** of the visual layer:

* In `src/components/studio/VidoAIStudio.tsx`:
  ```tsx
  left: `${posX * 100}%`,
  top: `${posY * 100}%`,
  transform: `translate(-50%, -50%) rotate(${rotation}deg)`
  ```
* In `backend/app/media/compositor.py` (lines 770–771):
  ```python
  ox_expr = f"(main_w*{pos_x:.3f}-overlay_w/2)"
  oy_expr = f"(main_h*{pos_y:.3f}-overlay_h/2)"
  ```

Thus, when $x = 0.5, y = 0.5$, the visual center of the layer aligns with the center of the video frame.

---

## 6. Scale Semantics

1. **Uniform Multiplier:** `scale` is a scalar floating-point number (default `1.0`).
2. **Layer-Specific Application:**
   * **Media (Images & Videos):**
     * Frontend: `width: ${Math.max(10, Math.min(80, 40 * scale))}%`, `height: auto` (`object-contain`).
     * FFmpeg: `target_w = max(4, int(round(canvas.width * 0.4 * m_scale)))`, height proportional to source aspect ratio.
     * Scale 1.0 produces an overlay whose width is exactly $40\%$ of the canvas width.
   * **Shapes:**
     * Scaled by multiplying `content.width` and `content.height` by `transform.scale`.
   * **Stickers:**
     * Scaled by multiplying the base dimension ($25\%$ of canvas dimension) by `transform.scale`.
   * **Text:**
     * Sized primarily via `content.font_size` (px). `transform.scale` is currently not factored into text rendering.

---

## 7. Rotation Semantics

1. **Units:** Degrees ($^\circ$), floating-point or integer.
2. **Slider Range:** $[-180^\circ, +180^\circ]$ in the Inspector panels; mathematically valid across $[0^\circ, 360^\circ]$.
3. **Direction:** **Clockwise** for positive angle values in both CSS and FFmpeg.
4. **Implementation Parity:**
   * **Frontend:** CSS `rotate(${rotation}deg)` rotates clockwise around the element center.
   * **FFmpeg Compositor:** `rotate={m_rotation}*PI/180:ow='hypot(iw,ih)':oh=ow:c=none` rotates clockwise in radians. The `ow='hypot(iw,ih)':oh=ow` expression expands the bounding box to prevent clipping corners during rotation, while `c=none` maintains an alpha-transparent background.

---

## 8. Anchor / Transform Origin

* **Anchor Point:** Exact visual **Center** ($50\%, 50\%$).
* **CSS Alignment:** The pairing of `left: X%`, `top: Y%` with `transform: translate(-50%, -50%)` shifts the element's origin from top-left to center.
* **FFmpeg Alignment:** Subtracting `overlay_w/2` and `overlay_h/2` from the target coordinates places the layer's center at $(W \cdot x, H \cdot y)$.
* **Equivalence:** **EXACT**. Both subsystems share the identical center-point anchor semantic.

---

## 9. Bounding Box Architecture

### Current Implementation
There is currently **no unified bounding-box data structure or abstraction** in the codebase.
* Visual dimensions are computed ad-hoc within layer rendering logic.
* Text overlays have intrinsic sizing governed by text length and `font_size`, clamped to `max-w-[85%]`.
* Media layers scale proportionally based on asset aspect ratio.

### Phase 34 Requirement
Direct manipulation gizmos must render a selection border and 8 interaction handles (4 corners, 4 edges, 1 rotation stem).
* In Phase 34, bounding boxes will be measured dynamically using DOM APIs (`el.getBoundingClientRect()`) relative to the viewport container (`canvasRef.current.getBoundingClientRect()`).
* This avoids polluting the `SceneLayer` schema with redundant width/height tracking for text and media.

---

## 10. Canvas Rendering Architecture

Located in `src/components/studio/VidoAIStudio.tsx` (lines 1705–2075):

1. **Canvas Container:**
   * 16:9 Aspect Ratio: `max-w-3xl aspect-video` (typically 768px × 432px).
   * 9:16 Aspect Ratio: `max-w-xs aspect-[9/16]` (typically 320px × 568px).
   * Positioned `relative overflow-hidden`.
2. **Stacking Context (z-index hierarchy):**
   * **z-0:** Background layer (color div, image, or looped video).
   * **z-10:** Main talking avatar video / placeholder.
   * **z-23:** Visual media layers (images, videos).
   * **z-23 + layerIndex:** Visual shapes and stickers.
   * **z-24:** Visual text overlay layers.
   * **z-25:** Subtitle/caption cues.
   * **z-30 (Planned Phase 34):** Direct manipulation gizmo overlay and handles.

---

## 11. FFmpeg Rendering Architecture

Located in `backend/app/media/compositor.py` (lines 620–820):

1. **Base Layer:** Background color or video scaled to canvas resolution ($1920 \times 1080$ or $1080 \times 1920$).
2. **Avatar Overlay:** Green-screen matte alphamerge, scaled and overlaid.
3. **Visual Media & Elements:** Filter graph chain for each layer:
   ```text
   [in:v] setpts, scale=W:H, rotate=deg*PI/180:ow='hypot(iw,ih)':oh=ow:c=none, format=rgba, colorchannelmixer=aa=opacity [m_ready];
   [current_video][m_ready] overlay=x='(main_w*X - overlay_w/2)':y='(main_h*Y - overlay_h/2)':enable='between(t,start,end)' [next_video]
   ```
4. **Text Overlays:** Rendered via libass subtitle filter with `\pos(px, py)` and `\an5` (center alignment).
5. **Captions:** Rendered via secondary libass subtitle pass.

---

## 12. Canvas vs FFmpeg Parity Matrix

| Feature / Layer Type | Frontend Preview | FFmpeg Compositor | Parity Classification | Evidence & Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Media: X / Y Position** | `left: X%`, `top: Y%` | `x='(main_w*X - overlay_w/2)'` | **EXACT** | Center-anchored coordinates match perfectly. |
| **Media: Scale** | `width: (40 * scale)%` | `target_w = round(W * 0.4 * scale)` | **EXACT** | Base size is $40\%$ of canvas width in both. |
| **Media: Rotation** | `rotate(${rotation}deg)` | `rotate=rad:ow='hypot':oh=ow:c=none` | **EXACT** | Clockwise rotation with hypot padding prevents clipping. |
| **Media: Opacity** | `opacity: opacity` | `colorchannelmixer=aa=opacity` | **EXACT** | Floating point alpha transparency is identical. |
| **Media: Anchor Point** | `translate(-50%, -50%)` | `- overlay_w/2`, `- overlay_h/2` | **EXACT** | True visual center alignment in both. |
| **Media: Timing** | Filtered by `playbackTime` | `enable='between(t, start, end)'` | **EXACT** | Visual visibility obeys identical time window. |
| **Shape: Position** | `left: X%`, `top: Y%` | `x='(main_w*X - overlay_w/2)'` | **EXACT** | Center-anchored coordinates match. |
| **Shape: Dimensions** | `widthPct * 2.5px` | `round(W * width * scale)` | **PARTIAL** | Frontend uses fixed pixel heuristic `* 2.5px`; backend scales to canvas width. |
| **Shape: Rotation** | `rotate(${rotation}deg)` | `rotate=rad:ow='hypot':oh=ow:c=none` | **EXACT** | Clockwise rotation around center. |
| **Sticker: Dimensions** | `64 * scale px` | `round(0.25 * min(W,H) * scale)` | **PARTIAL** | Frontend uses fixed 64px baseline; backend uses 25% of min canvas dimension. |
| **Text: Position** | `left: X%`, `top: Y%` | `\pos(px, py)` with `\an5` | **EQUIVALENT** | ASS `\an5` aligns center of text box at target pixel. |
| **Text: Rotation** | `translate(-50%, -50%)` | Hardcoded `Angle: 0` in ASS style | **MISMATCH** | Text rotation is not yet wired to canvas CSS or ASS style line. |
| **Text: Scale** | Fixed font-size in px | `Fontsize` in ASS style | **EQUIVALENT** | Text sizing is driven by `content.font_size` rather than `transform.scale`. |

---

## 13. Selection Model

In `src/components/studio/VidoAIStudio.tsx`:
* Selection is currently tracked across three independent state variables:
  * `selectedMediaLayerId: string | null`
  * `selectedTextLayerId: string | null`
  * `selectedElementLayerId: string | null`
* Clicking a layer in the canvas sets that layer's ID and opens its corresponding Inspector panel.
* **Phase 34 Recommendation:** To prevent multiple active gizmos from appearing simultaneously on the canvas, Phase 34 will introduce a unified active selection getter:
  ```typescript
  const activeSelectedLayer = useMemo(() => {
    if (!activeScene?.layers) return null;
    return activeScene.layers.find(
      (l: any) =>
        l.id === selectedMediaLayerId ||
        l.id === selectedTextLayerId ||
        l.id === selectedElementLayerId
    ) || null;
  }, [activeScene?.layers, selectedMediaLayerId, selectedTextLayerId, selectedElementLayerId]);
  ```
  When selecting any visual layer on the canvas, the other two IDs will be cleared to `null` to guarantee single-layer selection.

---

## 14. Inspector Synchronization

* **Canvas $\rightarrow$ Inspector:**
  * Direct manipulation gestures (drag, resize, rotate) mutate `layer.transform` in the React `scenes` state.
  * Because Inspector panels (`ElementsPanel`, `MediaLayerPanel`, `TextPanel`) consume `selectedLayer.transform` directly, their sliders, inputs, and preset buttons will update live at 60fps with zero lag.
* **Inspector $\rightarrow$ Canvas:**
  * Moving an Inspector slider calls `handleTransformChange({ x, y, scale, rotation })`, which updates `scenes`.
  * The canvas gizmo reads directly from `selectedLayer.transform`, so gizmo boundaries move immediately when sliders are dragged.

---

## 15. Timeline Synchronization

* Phase 33 established interactive clip manipulation on the timeline (`start_time`, `end_time`).
* Canvas direct manipulation modifies **only** `layer.transform` (`x`, `y`, `scale`, `rotation`).
* It does **not** modify `start_time` or `end_time`.
* Timeline track bars and canvas visibility continue to adhere to the existing temporal range check (`playbackTime >= start_time && playbackTime < end_time`).

---

## 16. Persistence & Optimistic Concurrency Control (OCC)

HeyZen uses an immutable snapshot persistence pattern with OCC:
1. **Interactive Gestures (Pointer Move):**
   * While dragging or resizing, updates are made purely to local React state via `setScenes(...)` and marked `setSaveStatus("unsaved")`.
   * **Zero API calls** occur during active pointer movement, maintaining smooth 60fps rendering without network congestion.
2. **Gesture Commit (Pointer Up):**
   * On pointer release, the final state is committed via `handleSave()`.
   * `handleSave()` calls `api.projects.createVersion(...)` with `expected_revision`.
   * If another tab or user modified the document, a `CONCURRENCY_CONFLICT` error is returned and displayed non-destructively.
3. **Database Schema:**
   * No migration is needed. `SceneLayer.transform` is serialized into PostgreSQL `JSONB` under `project_versions.document`.

---

## 17. Workspace / Security Boundaries

* All project document operations are partitioned by `workspace_id` in API routes (`/api/workspaces/{workspace_id}/projects/...`).
* Assets referenced by media layers are resolved through `mws.resolve_asset` with mandatory workspace boundary verification.
* Direct manipulation operates entirely on client-side state within the loaded workspace context, introducing zero security or authorization risks.

---

## 18. Responsive & Aspect Ratio Behavior

* The Studio canvas dynamically scales between 16:9 (`max-w-3xl aspect-video`) and 9:16 (`max-w-xs aspect-[9/16]`), and resizes as sidebars are toggled.
* Because all layer positions are stored as normalized coordinates $[0.0, 1.0]$, canvas dragging is completely resolution-independent:
  $$\Delta x = \frac{\Delta \text{clientX}}{\text{canvasRect.width}}, \quad \Delta y = \frac{\Delta \text{clientY}}{\text{canvasRect.height}}$$
* Multiplying by the live `canvasRect` guarantees consistent, jitter-free dragging regardless of screen resolution or responsive scaling.

---

## 19. Test Coverage Audit

### Existing Verified Tests
* `test_studio_interactive_timeline.py`: 12 passed.
* `test_studio_elements_shapes_stickers.py`: 13 passed.
* `test_studio_media_layers.py`: 12 passed.
* `test_studio_text.py`: 8 passed.
* `test_studio_captions.py`: 8 passed.
* `test_studio_music_media.py`: 8 passed.
* `test_studio_pipeline_e2e.py`: 10 passed.
* `test_timeline_compositor.py`: 3 passed.
* **Total Studio Tests:** 74 passed.

### Tests Required for Phase 34
* Unit tests for pointer-to-normalized coordinate conversion:
  * Delta calculation across 16:9 and 9:16 canvas profiles.
  * Clamping math preventing layers from disappearing off-screen.
  * Proportional scale calculation from corner handle distance deltas.
  * Rotation angle calculation via `Math.atan2`.
* Backend validation tests verifying that `SceneLayer` persists updated `transform` dictionaries across project versioning and export.

---

## 20. Browser E2E Status

`BROWSER E2E NOT VERIFIED`

* **Reason:** Playwright browser binary downloads are blocked by the host network/CDN policy in this execution environment.
* CLI tools and node modules are present, but automated browser execution cannot proceed without downloading Chromium/WebKit binaries.
* All backend APIs, schemas, TypeScript types, and production builds have been verified with 100% test passing rates.

---

## 21. Git & Database Integrity

* `git diff -- package.json package-lock.json public/`: Clean (0 diffs).
* `git status backend/alembic/versions`: Clean.
* Current Alembic head migration: `0006_api_keys_and_webhooks.py`.
* Zero database migrations added or required.

---

## 22. Direct Manipulation Feasibility

**Verdict:** **FEASIBLE WITHOUT SCHEMA MODIFICATIONS**.

The existing `SceneLayer.transform` model (`x`, `y`, `scale`, `rotation`) completely satisfies all requirements for direct canvas interaction. The backend compositor already accepts these fields and places overlays using center-anchored mathematics identical to the frontend's CSS transforms.

---

## 23. Required Implementation Architecture

When implementing Phase 34, the direct manipulation system will be structured as follows:

### 1. Canvas Transform Formulas

#### A. Drag-to-Move
Given initial layer center $(x_0, y_0)$, pointer start $(\text{startX}, \text{startY})$, and current pointer $(\text{curX}, \text{curY})$:
$$\Delta x = \frac{\text{curX} - \text{startX}}{\text{canvasRect.width}}, \quad \Delta y = \frac{\text{curY} - \text{startY}}{\text{canvasRect.height}}$$
$$\text{newX} = \text{clamp}(x_0 + \Delta x, 0.0, 1.0)$$
$$\text{newY} = \text{clamp}(y_0 + \Delta y, 0.0, 1.0)$$

#### B. Corner Resizing (Proportional Scale)
Given initial distance from layer center $C = (C_x, C_y)$ to the grabbed corner handle $D_0 = \|P_0 - C\|$, and current distance $D = \|P - C\|$:
$$\text{scaleRatio} = \frac{D}{D_0}$$
$$\text{newScale} = \text{clamp}(\text{scale}_0 \times \text{scaleRatio}, 0.2, 3.0)$$

#### C. Rotation Handle
Given layer center $C$ in screen coordinates and current pointer position $P$:
$$\theta = \text{atan2}(P_y - C_y, P_x - C_x) \times \frac{180}{\pi}$$
$$\text{newRotation} = \text{round}(\theta - \theta_0) \pmod{360}$$
Normalize to $[-180^\circ, +180^\circ]$ to match Inspector slider conventions.

### 2. Gizmo Component Architecture
* Create `src/components/studio/CanvasTransformGizmo.tsx`:
  * Renders on top of the active selected layer (`z-30`).
  * Displays a crisp outline with selection ring: `ring-2 ring-blue-500`.
  * 4 corner resize handles (`nw`, `ne`, `se`, `sw`) styled as white squares with blue borders (`w-2.5 h-2.5 bg-white border-2 border-blue-500 rounded-xs`).
  * 1 rotation stem extending above top-center (`w-0.5 h-4 bg-blue-500`) with a circular rotation handle (`w-3 h-3 bg-white border-2 border-blue-500 rounded-full cursor-grab`).
  * Attaches global `pointermove` and `pointerup` handlers to `window` during active gestures to ensure smooth dragging even if the cursor leaves the canvas boundary.

### 3. Implementation Files Expected to Change
* `src/components/studio/CanvasTransformGizmo.tsx` (New component)
* `src/components/studio/VidoAIStudio.tsx` (Integrate gizmo overlay, wire selection state, attach pointer handlers)
* `src/lib/canvasTransformUtils.ts` (Pure math utilities for delta conversion, angle calculation, and clamping)

---

## 24. Risks & Known Gaps

1. **Text Rotation Gap:** ASS subtitle rendering currently does not apply rotation tags `{\frz<deg>}`. If a text layer is rotated in canvas, FFmpeg will still render it unrotated unless `compositor.py` is updated to include `{\frz}`.
2. **Shape Pixel Heuristic:** The frontend shape preview uses `widthPct * 2.5px`, whereas FFmpeg computes dimensions relative to `canvas.width`. This should be standardized to relative percentage widths in future iterations.
3. **Video Pointer Event Capture:** Active `<video>` tags in canvas must retain `pointer-events-none` so that pointer drag events are captured cleanly by the layer wrapper or gizmo overlay.

---

## 25. Phase 34 Implementation Acceptance Criteria

1. **Selection:** Clicking any visual layer (image, video, shape, sticker, text) in the canvas displays the transform gizmo with corner handles and a rotation stem.
2. **Drag-to-Move:** Clicking and dragging anywhere inside the layer or gizmo moves the layer smoothly across the canvas, updating `transform.x` and `transform.y`.
3. **Corner Resize:** Dragging any corner handle scales the layer proportionally, updating `transform.scale`.
4. **Rotation:** Dragging the rotation handle rotates the layer around its center, updating `transform.rotation`.
5. **Live Inspector Sync:** Moving the layer in the canvas updates the Inspector sliders and position presets in real time.
6. **Live Timeline Sync:** Canvas manipulation does not alter layer start/end times or disrupt timeline playback.
7. **OCC Persistence:** Releasing the pointer commits the final transform state via `handleSave()`.
8. **Aspect Ratio Parity:** Gizmo interactions behave identically across 16:9 and 9:16 canvases.
9. **Zero Database Migrations:** No changes to PostgreSQL schemas or Alembic scripts.

---

## 26. Conclusion

The HeyZen Studio canvas architecture is robust, mathematically consistent, and primed for direct manipulation. All necessary foundational schemas and compositor overlay filters are in place.

**Status:** `PHASE 34 AUDIT COMPLETE — IMPLEMENTATION ARCHITECTURE READY`
