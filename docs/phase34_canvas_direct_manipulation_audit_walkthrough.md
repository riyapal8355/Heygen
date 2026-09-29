# Phase 34 — Studio Canvas Direct Manipulation Audit Walkthrough

**Audit Status:** `PHASE 34 AUDIT COMPLETE — IMPLEMENTATION ARCHITECTURE READY`  
**Date:** September 2026  
**Repository:** `d:\HeyGen\video-ai-tools`  

---

## 1. What Was Inspected

During this read-only audit, we analyzed:
* **Frontend Viewport & Canvas:** `src/components/studio/VidoAIStudio.tsx` (canvas rendering, z-index hierarchy, aspect ratios).
* **Inspector Panels:** `ElementsPanel.tsx`, `MediaLayerPanel.tsx`, `TextPanel.tsx` (transform sliders, 9-point position presets, update callbacks).
* **Shared Schema:** `backend/app/schemas/project_document.py` (`SceneLayer`, `ProjectDocumentV1`).
* **Backend Compositor:** `backend/app/media/compositor.py` (ASS subtitle generation, visual media scaling, rotation filters, overlay positioning).
* **Media Utilities:** `backend/app/media/filters.py`, `backend/app/media/shapes.py`.
* **Database & Concurrency:** `backend/app/models/project.py` (JSONB document storage, OCC revision validation).
* **Existing Test Suite:** All 74 Studio regression tests and full frontend production build.

---

## 2. Canonical Transform Model

The verified transform model across both frontend and backend is:
* **Position:** Normalized center coordinates $(x \in [0.0, 1.0], y \in [0.0, 1.0])$, default $(0.5, 0.5)$.
* **Scale:** Uniform multiplier $\ge 0.05$, default $1.0$.
* **Rotation:** Clockwise degrees $\in [-180^\circ, +180^\circ]$, default $0.0^\circ$.
* **Anchor / Origin:** Visual **Center** ($50\%, 50\%$).
* **Opacity:** Normalized $[0.0, 1.0]$ in `content.opacity`, default $1.0$.

---

## 3. Coordinate System & Anchor

* **Origin $(0, 0)$:** Top-left corner of the canvas.
* **Anchor Point:** Visual center.
  * In CSS: `left: ${x * 100}%`, `top: ${y * 100}%`, `transform: translate(-50%, -50%) rotate(${rotation}deg)`.
  * In FFmpeg: `x='(main_w*x - overlay_w/2)'`, `y='(main_h*y - overlay_h/2)'`.
  * **Result:** 100% mathematical center-to-center parity.

---

## 4. Canvas vs Compositor Parity & Identified Mismatches

| Layer Type | Transform Properties | Canvas vs FFmpeg Parity | Notes |
| :--- | :--- | :--- | :--- |
| **Media Layers (Images / Videos)** | Position, Scale, Rotation, Opacity, Timing | **EXACT** | Base width is 40% of canvas width in both CSS and FFmpeg. |
| **Shapes** | Position, Rotation, Opacity | **EXACT** | Position and rotation match. |
| **Shapes** | Sizing / Scale | **PARTIAL** | Frontend uses `widthPct * 2.5px`; backend scales relative to canvas dimensions. |
| **Stickers** | Position, Rotation, Opacity | **EXACT** | Center-anchored overlay is identical. |
| **Stickers** | Sizing / Scale | **PARTIAL** | Frontend uses `64 * scale px`; backend uses `0.25 * min(W,H) * scale`. |
| **Text Overlays** | Position, Font Size, Opacity | **EQUIVALENT** | `\pos(px, py)` with `\an5` matches CSS center placement. |
| **Text Overlays** | Rotation | **MISMATCH** | Text rotation is not yet wired to canvas CSS or ASS style `Angle`. |

---

## 5. Direct Manipulation Feasibility

**Verdict:** **FEASIBLE WITHOUT SCHEMA CHANGES OR MIGRATIONS**.

* The existing `SceneLayer.transform: Dict[str, Any]` schema already stores `x, y, scale, rotation`.
* PostgreSQL stores the complete document in `project_versions.document` as JSONB.
* Zero database migrations are required.
* The frontend can calculate normalized deltas resolution-independently.

---

## 6. Exact Implementation Architecture for Phase 34

1. **Math Utilities (`src/lib/canvasTransformUtils.ts`):**
   * Drag conversion: $\Delta x = \frac{\Delta \text{clientX}}{\text{canvasWidth}}$, $\Delta y = \frac{\Delta \text{clientY}}{\text{canvasHeight}}$, clamped to $[0.0, 1.0]$.
   * Proportional corner resize: $\text{newScale} = \text{scale}_0 \times \frac{\text{currentDist}}{\text{initialDist}}$, clamped to $[0.2, 3.0]$.
   * Rotation angle: $\theta = \text{round}(\text{atan2}(P_y - C_y, P_x - C_x) \times \frac{180}{\pi} - \theta_0)$.
2. **Gizmo Component (`src/components/studio/CanvasTransformGizmo.tsx`):**
   * Renders at `z-30` around the selected layer.
   * Provides 4 corner handles and 1 top rotation handle stem.
   * Window-level pointer capture during gestures for smooth tracking beyond canvas edges.
3. **OCC Persistence Integration:**
   * Live React updates during drag (`onPointerMove`) with `saveStatus = "unsaved"`.
   * Final commit on release (`onPointerUp`) calling `handleSave()`.

---

## 7. Acceptance Criteria for Phase 34

* [ ] Single active selected visual layer with bounding box gizmo.
* [ ] Smooth direct drag-to-move with live Inspector slider sync.
* [ ] Corner handle dragging scales layer proportionally.
* [ ] Top rotation handle rotates layer smoothly around center.
* [ ] No timeline timing corruption (`start_time` and `end_time` preserved).
* [ ] Releasing pointer commits update via OCC.
* [ ] Responsive across 16:9 and 9:16 canvases.
* [ ] Zero database migrations.

---

## 8. Remaining Blockers

* **None for Phase 34 implementation.**
* Browser E2E remains unverified due to external network restrictions on Playwright browser binaries, but all backend tests (74/74) and TypeScript production build pass cleanly.
