# Phase 34 — Studio Canvas Direct Manipulation Implementation Walkthrough

## Overview

This walkthrough details the direct manipulation gizmo implementation in HeyZen Studio and outlines the exact steps to manually test the feature on the live development servers.

---

## Architecture Walkthrough

### 1. Canvas Mathematical Core (`src/lib/canvasTransformUtils.ts`)
- Implements purely functional coordinate transforms:
  - `pointerToNormalizedDelta`: Converts mouse/pointer pixel movements to $[0, 1]$ normalized canvas coordinates based on the live `canvasRect` bounds.
  - `calculatePositionFromPointer`: Computes new layer $(x, y)$ clamped strictly within $[0, 1]$.
  - `calculateScaleFromPointer`: Computes proportional radial-distance scaling from the layer center, clamped within $[0.2, 3.0]$.
  - `calculateRotationFromPointer`: Computes clockwise angular changes relative to layer center, wrapping neatly into $[-180^\circ, +180^\circ]$ without boundary jumps.

### 2. The Gizmo Component (`src/components/studio/CanvasTransformGizmo.tsx`)
- High-contrast visual overlay placed at `z-30`:
  - **Bounding box**: Dashed active border tracing layer bounds.
  - **Corner Handles**: 4 circular handles (`cursor-nwse-resize`, `cursor-nesw-resize`) for proportional scaling.
  - **Rotation Knob & Stem**: Vertical dashed stem leading to an accent-colored rotation knob with `cursor-grab` styling.
  - **Pointer Capture**: Uses `e.currentTarget.setPointerCapture(e.pointerId)` to ensure mouse tracking continues smoothly even if the cursor leaves the canvas or browser window.
  - **Threshold Detection**: A 2px movement threshold guarantees single clicks select the layer without accidentally displacing it.

### 3. Studio Integration (`src/components/studio/VidoAIStudio.tsx`)
- **Single Active Selection**:
  - Clicking on a media layer deselects text/shapes/stickers.
  - Clicking on an element layer deselects media/text.
  - Clicking empty canvas space invokes `clearVisualSelection()`.
- **Bidirectional Inspector Sync**:
  - Live local state updates during pointer drag (`handleUpdateLayerTransform`) update the Inspector's X, Y, Scale, and Rotation controls in real time.
  - Modifying Inspector controls updates the layer and the canvas gizmo immediately.
- **OCC Persistence**:
  - Changes during gesture execution are local-only (0 network calls).
  - Releasing the pointer commits the final transform through `handleSave()` and `api.projects.createVersion(..., { expected_revision })`.
  - Timeline properties (`start_time`, `end_time`, `duration`) are completely isolated.

---

## Live Servers

Both servers are running live in the background:
- **Frontend Server**: [http://localhost:3000](http://localhost:3000)
- **Backend Server**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Backend Health Check**: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

---

## Step-by-Step Manual Verification Guide

### Step 1: Open HeyZen Studio
1. Open your browser and navigate to:
   ```text
   http://localhost:3000
   ```
2. Navigate to an existing project or create a new Studio project.

---

### Step 2: Layer Selection & Gizmo Visibility
1. Add or locate a **Media Layer** (image or video), a **Text Layer**, and an **Element Layer** (shape or sticker) on the canvas.
2. Click on the **Media Layer**:
   - Verify that the blue/indigo transform bounding box appears directly over the media layer with 4 corner handles and 1 top rotation handle.
   - Verify the Inspector on the right opens and displays the layer's Transform properties ($X, Y, \text{Scale}, \text{Rotation}$).
3. Click on the **Text Layer**:
   - Verify the gizmo transfers to the Text Layer.
   - Verify the Media Layer gizmo disappears (only one gizmo is active at any time).
4. Click on the **Element (Shape/Sticker) Layer**:
   - Verify the gizmo transfers to the Element Layer.
5. Click on the **empty canvas background**:
   - Verify all gizmos disappear and selections are cleared.

---

### Step 3: Drag-to-Move
1. Select any visual layer on the canvas.
2. Click and hold the center area of the layer or gizmo bounding box and drag across the canvas.
3. Observe:
   - The layer moves smoothly across the canvas following the cursor.
   - The Inspector's $X$ and $Y$ position fields update in real time (~60 FPS).
   - The top header displays `Unsaved changes`.
4. Release the mouse button:
   - The layer remains at its new position.
   - The header saves and displays `Saved`.
5. Refresh the browser:
   - Confirm the new $(X, Y)$ position persists after reload.

---

### Step 4: Proportional Corner Resize
1. Select a layer.
2. Move the cursor over any of the 4 corner handles (cursor changes to diagonal resize arrow).
3. Drag away from the layer center to enlarge, or towards the center to shrink.
4. Observe:
   - The layer scales smoothly and proportionally while retaining its aspect ratio and center position.
   - The Inspector's `Scale` slider reflects the updated scale in real time.
   - The scale clamps safely between `0.20x` and `3.00x`.
5. Release the mouse button:
   - Transform persists and saves via OCC versioning.

---

### Step 5: Rotation
1. Hover over the circular knob above the top edge of the bounding box (cursor changes to grab icon).
2. Click and drag in a circular motion around the layer center.
3. Observe:
   - The layer and gizmo rotate smoothly in degrees clockwise/counter-clockwise.
   - No jumping or erratic flipping occurs when crossing $\pm 180^\circ$.
   - The Inspector's `Rotation` slider displays the exact degree angle in real time.
4. Release the mouse button:
   - Transform persists cleanly.

---

### Step 6: Inspector ↔ Canvas Bidirectional Sync
1. With a layer selected, locate the **Inspector** on the right side of the screen.
2. Adjust the **Position X** slider:
   - The canvas layer and gizmo move horizontally.
3. Adjust the **Scale** slider:
   - The canvas layer and gizmo scale proportionally.
4. Adjust the **Rotation** slider:
   - The canvas layer and gizmo rotate to match.

---

### Step 7: Timeline Integrity Check
1. Inspect the timeline at the bottom of the screen.
2. Note the clip's `start_time`, `end_time`, and `duration`.
3. Manipulate the canvas gizmo (drag, scale, rotate).
4. Verify:
   - The timeline clip does not shift, shrink, or expand.
   - Clip temporal parameters remain completely unchanged.
   - Phase 33 timeline trimming and dragging remain fully functional.

---

## Automated Test Execution Commands

To re-run the automated verification suites at any time:

```bash
# Frontend Canvas Unit Tests (27 tests)
npx tsx src/lib/canvasTransformUtils.test.ts

# TypeScript Typecheck
npx tsc --noEmit

# Frontend Production Build
npm run build

# Backend Studio Regression Suite (78 tests)
backend\.venv\Scripts\pytest backend/tests/test_studio_interactive_timeline.py backend/tests/test_studio_elements_shapes_stickers.py backend/tests/test_studio_media_layers.py backend/tests/test_studio_text.py backend/tests/test_studio_captions.py backend/tests/test_studio_music_media.py backend/tests/test_studio_pipeline_e2e.py backend/tests/test_timeline_compositor.py backend/tests/test_studio_canvas_manipulation.py
```
