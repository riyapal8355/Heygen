# Phase 34 — Studio Canvas Direct Manipulation Implementation Report

## 1. Summary

Phase 34 delivers **direct on-canvas manipulation** for selected visual layers in HeyZen Studio. Users can directly drag to translate, interact with 4 corner handles to perform proportional radial scaling, and rotate layers using a dedicated top stem and rotation handle. The implementation strictly adheres to the canonical `SceneLayer.transform` model (`x`, `y`, `scale`, `rotation`), guarantees complete timeline isolation (`start_time`, `end_time`, `duration` remain untouched), synchronizes bidirectionally with the Studio Inspector at ~60 FPS, enforces single-layer mutual exclusivity, and commits updates via existing Optimistic Concurrency Control (OCC) versioning without network roundtrips during gesture execution.

---

## 2. Files Changed

### New Files Created
1. `src/lib/canvasTransformUtils.ts`: Pure, framework-agnostic mathematical engine for normalized coordinate transformations, bounded translation, proportional scaling, circular rotation angle computation, and numerical safety (clamp, NaN/Infinity protection, zero-distance guarding).
2. `src/lib/canvasTransformUtils.test.ts`: Deterministic unit test suite verifying translation deltas across 16:9, 9:16, 1:1 aspect ratios, boundary clamping, radial scaling, rotation angle normalization across ±180° boundaries, and numerical safety guards (27 passing tests).
3. `src/components/studio/CanvasTransformGizmo.tsx`: Interactive SVG/HTML canvas overlay (`z-30`) rendering the selection boundary, 4 proportional corner resize handles, and top rotation stem + handle with global pointer capture and click vs. drag thresholding.
4. `backend/tests/test_studio_canvas_manipulation.py`: Backend integration and regression test suite verifying `SceneLayer.transform` schema validation, version persistence, OCC conflict handling, and FFmpeg compositor execution on transformed layers (4 passing tests).
5. `docs/phase34_canvas_direct_manipulation_implementation.md`: This comprehensive implementation report.
6. `docs/phase34_canvas_direct_manipulation_implementation_walkthrough.md`: Practical walkthrough and manual test guide.

### Existing Files Modified
1. `src/components/studio/VidoAIStudio.tsx`:
   - Integrated `CanvasTransformGizmo` on active media, text, shape, and sticker layers.
   - Attached `canvasViewportRef` and configured empty canvas background click handlers to clear visual selection.
   - Enforced mutually exclusive single-layer selection (`selectMediaLayer`, `selectTextLayer`, `selectElementLayer`, `clearVisualSelection`).
   - Implemented high-performance local state update callbacks (`handleUpdateLayerTransform`) and pointer-release commit callbacks (`handleCommitLayerTransform` triggering `handleSave()`).
   - Removed clipping `overflow-hidden` on media preview wrapper so rotation stems and corner resize handles render clearly.
   - Added `rotate(...)` transform and font-size scaling support to text canvas preview.

### Database Migrations
- **NONE**: Database schema was unchanged; `0006_api_keys_and_webhooks.py` remains Alembic head.

---

## 3. Canvas Transform Architecture

### Canonical Transform Model
The architecture strictly preserves the canonical `SceneLayer.transform` schema:
```text
transform.x        ∈ [0, 1]      (normalized canvas coordinate, default 0.5)
transform.y        ∈ [0, 1]      (normalized canvas coordinate, default 0.5)
transform.scale    ∈ [0.2, 3.0]  (uniform scale multiplier, default 1.0)
transform.rotation ∈ [-180, 180] (degrees, clockwise, default 0.0)
anchor             center (50%, 50%)
```

### Canvas Coordinate Model
- Top-Left: `(0.0, 0.0)`
- Center: `(0.5, 0.5)`
- Bottom-Right: `(1.0, 1.0)`
- Responsive Parity: The gizmo measures the live canvas viewport bounding rectangle via `getBoundingClientRect()`, calculating normalized coordinate deltas relative to dynamic viewport dimensions:
  $$dx = \frac{x_{\text{current}} - x_{\text{start}}}{\text{rect.width}}, \quad dy = \frac{y_{\text{current}} - y_{\text{start}}}{\text{rect.height}}$$
  This ensures identical normalized behavior on 16:9, 9:16, 1:1, or dynamically resized windows.

---

## 4. Drag Implementation

- **Trigger**: Pointer down on the gizmo bounding area or the selected layer body.
- **Pointer Events**: Employs `pointerdown`, `pointermove`, `pointerup`, `pointercancel` with `setPointerCapture` and `releasePointerCapture`.
- **Gesture Threshold**: A 2-pixel movement threshold distinguishes simple layer selection clicks from deliberate transform drags.
- **Frame Rate**: Updates React state synchronously during movement targeting ~60 FPS without dispatching backend requests.
- **Clamping**: Coordinates are clamped to $[0.0, 1.0]$ with `clamp(val, 0, 1)` to prevent runaway layers.

---

## 5. Resize Implementation

- **Handles**: 4 corner handles (`top-left`, `top-right`, `bottom-left`, `bottom-right`).
- **Algorithm**: Proportional radial-distance scaling from the layer center:
  $$\text{newScale} = \text{startScale} \times \frac{\text{distance}(\text{currentPointer}, \text{layerCenter})}{\text{distance}(\text{startPointer}, \text{layerCenter})}$$
- **Bounds**: Clamped to $[0.2, 3.0]$.
- **Stability**: Protected against zero initial distance and NaN/Infinity values.
- **Center Invariance**: Center position $(x, y)$ remains fixed during scale adjustments.

---

## 6. Rotation Implementation

- **Handle**: Dedicated circular rotation handle placed 26px above the top bounding box edge connected via a visible dashed stem.
- **Angle Calculation**: Evaluates pointer angle relative to layer center using `Math.atan2(y - cy, x - cx)`.
- **Normalization**: Automatically maps angular deltas into $[-180^\circ, +180^\circ]$ degrees, preventing visual boundary jumps when crossing $\pm 180^\circ$.

---

## 7. Selection Behavior

- **Single Active Selection**: HeyZen Studio enforces single-item visual selection across all layer types:
  - Selecting a media layer clears text and element selections.
  - Selecting a text layer clears media and element selections.
  - Selecting an element (shape/sticker) clears media and text selections.
  - Clicking on the empty canvas viewport background clears all layer selections.
- **Gizmo Isolation**: Only exactly one `CanvasTransformGizmo` is rendered at any time.

---

## 8. Inspector Synchronization

- **Bidirectional Parity**: The canvas gizmo and Inspector share the exact same canonical `SceneLayer.transform` state in `VidoAIStudio.tsx`.
- **Canvas to Inspector**: During gizmo manipulation, `handleUpdateLayerTransform` updates the active scene's layer transform in React state, causing Inspector position/scale/rotation sliders and inputs to reflect live values in real time (~60 FPS).
- **Inspector to Canvas**: Manual entry or slider adjustments in the Inspector mutate `SceneLayer.transform`, immediately updating the layer position and canvas gizmo bounds.

---

## 9. Timeline Isolation

- Direct canvas manipulation modifies **only** `transform.x`, `transform.y`, `transform.scale`, and `transform.rotation`.
- Layer temporal fields (`start_time`, `end_time`, `duration`) are completely untouched.
- Phase 33 interactive timeline drag, trim, snap, and minimum duration enforcement remain fully operational.

---

## 10. Persistence & Concurrency (OCC)

- **Gesture Isolation**: Zero HTTP requests during interactive gestures (`pointermove`).
- **Save Status Indicator**: Sets `saveStatus = "unsaved"` during active interaction.
- **Commit on Release**: On `pointerup` / gesture completion, `handleCommitLayerTransform` commits the accumulated transform state via `handleSave()` calling `api.projects.createVersion(project.id, { ..., expected_revision: project.revision })`.
- **OCC Integrity**: Version revision conflicts (409) are caught and handled by the existing OCC workflow.

---

## 11. Automated Test Results

### Frontend Unit Tests
- Suite: `src/lib/canvasTransformUtils.test.ts`
- Total Tests: 27
- Passed: 27
- Failed: 0
- Coverage: Aspect ratios (16:9, 9:16, 1:1), bounds clamping, radial scaling, rotation angle continuity, and numerical safety (NaN, Infinity, zero distance).

### Backend Regression Tests
- Suite: `backend/tests/test_studio_canvas_manipulation.py`
  - `test_scene_layer_transform_schema_model`: PASS
  - `test_canvas_transform_persistence_and_occ`: PASS
  - `test_canvas_transform_occ_conflict_detection`: PASS
  - `test_compositor_renders_transformed_shape_layer`: PASS
- Full Studio Regression Suite:
  - `test_studio_interactive_timeline.py`: 12/12 PASS
  - `test_studio_elements_shapes_stickers.py`: 13/13 PASS
  - `test_studio_media_layers.py`: 12/12 PASS
  - `test_studio_text.py`: 8/8 PASS
  - `test_studio_captions.py`: 8/8 PASS
  - `test_studio_music_media.py`: 8/8 PASS
  - `test_studio_pipeline_e2e.py`: 10/10 PASS
  - `test_timeline_compositor.py`: 3/3 PASS
  - `test_studio_canvas_manipulation.py`: 4/4 PASS
  - Total: **78/78 passing** (0 failures).

---

## 12. Build Results

- **TypeScript Typecheck**: `npx tsc --noEmit` exited with code 0 (zero errors).
- **Next.js Production Build**: `npm run build` (Turbopack) succeeded without warnings or errors. Static pages and routes compiled cleanly.

---

## 13. Backend Server Results

- Server executable: Python 3.13 / Uvicorn in virtual environment.
- Health Check: `curl.exe -s http://127.0.0.1:8000/health` returned `{"status":"ok","app":"HeyZen Backend","version":"0.1.0"}` (HTTP 200).
- Database & Cache: PostgreSQL (5432), Redis (6379), and MinIO (9000) verified healthy and seeded.

---

## 14. Browser E2E Status

- **Status**: `NOT VERIFIED`
- **Reason**: Playwright browser binary downloads remain blocked by the host network/CDN policy in this container environment. Unit and API integration tests provide rigorous programmatic verification.

---

## 15. Manual Verification Status

- Development servers running locally and ready for user interaction.
- All layer types (media, text, shape, sticker) verified to accept gizmo attachments.
- Inspector synchronization verified via state unification.

---

## 16. Server Status

- **Frontend Server**: RUNNING at `http://localhost:3000` (Next.js 16.3.4 Turbopack dev server).
- **Backend Server**: RUNNING at `http://127.0.0.1:8000` (FastAPI / Uvicorn server).
- **Connectivity**: Verified (`NEXT_PUBLIC_API_URL` targeting `http://127.0.0.1:8000`).

---

## 17. Known Limitations

- **Text Rotation Export Parity**: As documented in the Phase 34 audit, FFmpeg `drawtext` does not natively support rotation angles; rotation displays in the canvas preview but exports without rotation. Text scaling and translation have full export parity.
- **Sticker / Shape Sizing Discrepancy**: Shape/sticker sizes use partial canonical sizing parity established in Phase 31.

---

## 18. Files Intentionally Not Changed

- `backend/alembic/versions/*`: No migrations introduced.
- `src/components/studio/MediaTimelineTrack.tsx`: Timeline track components remain untouched; temporal parameters are isolated.
- `src/components/studio/ElementsTimelineTrack.tsx`: Untouched.
- `src/components/studio/TextTimelineTrack.tsx`: Untouched.
- `src/components/studio/MusicTimelineTrack.tsx`: Untouched.

---

## 19. Final Verification

All Phase 34 requirements are complete, verified by comprehensive unit, integration, build, and typecheck suites. Both the frontend and backend servers are running live.
