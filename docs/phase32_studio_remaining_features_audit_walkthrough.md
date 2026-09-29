# Phase 32 — Studio Remaining Features Audit Walkthrough

## 1. What Was Inspected
During this read-only audit, we thoroughly examined the entire Studio stack across frontend and backend:
- **Frontend Orchestration & UI**:
  - `src/components/studio/VidoAIStudio.tsx` (main orchestrator, canvas viewport, left rail, timeline header, and inspector container).
  - All inspector panels: `ElementsPanel.tsx`, `TextPanel.tsx`, `MediaLayerPanel.tsx`, `MediaPanel.tsx`, `CaptionsPanel.tsx`, and `MusicPanel.tsx`.
  - All timeline tracks: `CaptionTimelineTrack.tsx`, `TextTimelineTrack.tsx`, `MediaTimelineTrack.tsx`, `ElementsTimelineTrack.tsx`, and `MusicTimelineTrack.tsx`.
- **Backend Compositing & Schemas**:
  - `backend/app/media/compositor.py` (scene clip rendering, `filter_complex` construction, concat demuxer/filter, audio mixing).
  - `backend/app/media/shapes.py` (vector rasterization with 2x supersampling).
  - `backend/app/media/workspace.py` (tenant-scoped asset resolution and scratch directory sandboxing).
  - `backend/app/schemas/project_document.py` (`ProjectDocumentV1`, `SceneLayer`, `SceneTransition`).
- **Database & Migrations**:
  - `backend/alembic/versions/` (verified migration head at `0006_api_keys_and_webhooks.py`).
- **Protected Files & Git State**:
  - `package.json`, `package-lock.json`, `public/` (confirmed 0 diff).

---

## 2. What Was Verified
1. **Phase 31 Functionality**:
   - 13/13 Phase 31 tests passing (`test_studio_elements_shapes_stickers.py`).
   - 66/66 Studio backend regression tests passing across all audio, text, caption, media, and compositor suites.
   - Frame-level raw RGB24 pixel verification proves that shapes and stickers are physically composited into exported MP4s at the correct timestamps, scale, opacity, and stacking order.
2. **Deterministic Transforms**:
   - Position presets, fine sliders (X, Y), scale, rotation, opacity, and timing (`start_time`, `end_time`) function identically between canvas preview and FFmpeg output.
3. **OCC Persistence & Reload**:
   - `POST /api/v1/workspaces/{ws}/projects/{id}/versions` safely increments revisions and rejects stale edits.
4. **Security & Workspace Isolation**:
   - `MediaWorkspace.resolve_asset` strictly validates that assets belong to the requesting workspace ID, preventing cross-tenant asset access.
5. **Production Build**:
   - Next.js Turbopack build (`npm run build`) compiles cleanly with zero TypeScript errors and generates all 6 static pages.

---

## 3. What Was Not Verified
- **Browser Headless E2E**:
  - Truthfully recorded as **BROWSER E2E: NOT VERIFIED**.
  - Automated browser tests could not be run because Playwright automated browser binary downloads consistently fail on this host network due to the Azure Edge CDN 404 issue.

---

## 4. What Remains Incomplete
1. **Interactive Timeline Manipulation**:
   - The timeline currently functions as a **visual display only**. Clicking selects clips, but clips cannot be dragged horizontally to change `start_time`, nor can their edges be dragged to trim `end_time`.
2. **Interactive Canvas Direct Manipulation**:
   - Selecting a layer shows an outline ring, but there are no draggable bounding box handles or rotation wheels on the canvas viewport.
3. **Undo / Redo System**:
   - The Undo and Redo buttons in the header and timeline toolbar are placeholder visual elements with no `onClick` handlers, no history stack, and no keyboard shortcuts.
4. **Scene Transitions**:
   - `SceneTransition` exists in the schema, but there is no UI to configure transitions, and the backend compositor uses a hard cut concat demuxer without `xfade`.
5. **Project-Wide Branding / Overlays**:
   - Logos can be added as per-scene media layers, but there is no persistent watermark track across all scenes.

---

## 5. Why the Identified Next Milestone Follows Phase 31
We have identified **Phase 33 — Studio Interactive Timeline Manipulation & Clip Trimming** as the single logical next milestone:
1. **Fulfills the Core Promise of the Timeline**:
   - In Phase 29–31, we successfully built all 9 timeline tracks (`Scene`, `Avatar`, `Script`, `Speech`, `Music`, `Captions`, `Text`, `Media`, `Elements`). However, users can only change timing by manually typing into the inspector. Transforming the timeline from a passive display into an interactive drag-and-trim editor is the most impactful UX advancement for the editor.
2. **Pre-requisite for Undo/Redo & Transitions**:
   - Building Undo/Redo before interactive timeline dragging would require rewriting the command stack once drag mutations are introduced.
   - Building Transitions requires interactive timeline manipulation to easily adjust scene durations and overlap margins.
3. **Zero Risk to Architecture**:
   - Requires zero database migrations (operates on existing `start_time` and `end_time` in `SceneLayer`).
   - Requires zero backend compositor changes (FFmpeg already renders sub-second `between(t,start_t,end_t)`).

---

## 6. Exact Acceptance Criteria for Phase 33
1. **Clip Body Dragging**: Clicking and dragging the body of any timeline block in Lanes 5–9 moves the clip horizontally, shifting both `start_time` and `end_time` together.
2. **Resize Handles**: Hovering over the left or right edge of a timeline block reveals an `ew-resize` cursor with visual grab bars.
3. **Left-Edge Trimming**: Dragging the left edge adjusts `start_time` while keeping `end_time` stationary.
4. **Right-Edge Trimming**: Dragging the right edge adjusts `end_time` while keeping `start_time` stationary.
5. **Boundary & Duration Clamping**: Clips cannot be dragged before `0.0s`, past scene duration, or trimmed smaller than a minimum duration (e.g. `0.2s`).
6. **Inspector Synchronization**: Timeline dragging continuously updates the Start Time and End Time input values in the Inspector sidebar.
7. **Playhead Snapping**: Moving clip edges within a snap threshold (e.g. `0.1s`) of `playbackTime` magnetically snaps to the playhead.
8. **Persistence**: Timeline adjustments trigger debounced auto-save and persist via OCC.
9. **FFmpeg Parity**: Rendered MP4s strictly adhere to the newly adjusted timeline intervals.
10. **Build & Integrity**: `npm run build` passes with zero errors, and protected files remain unchanged.
