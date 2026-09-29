# Phase 36 — Studio Render Parity Implementation Walkthrough

## Overview

This walkthrough explains the engineering solutions implemented in Phase 36 to achieve parity between the HeyZen Studio Canvas Preview and the FFmpeg export pipeline, along with step-by-step instructions for manual testing on the live development servers.

---

## 1. What Changed and Why

### A. Text Rotation & Scale Export
- **Problem**: When a user rotated or scaled a text layer on the canvas, the exported MP4 video ignored both properties and rendered flat, unrotated, unscaled text.
- **Solution**:
  1. Updated `_generate_scene_text_ass_file` in `backend/app/media/compositor.py` to multiply `font_size` by `transform.scale` when generating the dedicated ASS style for each text layer.
  2. Evaluated `norm_rot` in $[-180, 180]$ and injected `\frz{round(-norm_rot, 2)}` into the dialogue event override tag:
     ```text
     {\pos(px, py)\an5\frz(-30)}TEXT
     ```
  3. Sign Inversion: CSS rotates clockwise for positive degrees; ASS rotates counter-clockwise for positive degrees. Inverting the sign ensures the exported video rotates in the exact same clockwise direction as the canvas preview.

### B. Shape Sizing Parity
- **Problem**: Canvas shapes were sized using `widthPct * 2.5px`, which made default shapes only ~11.4% of canvas preview width while backend rendered them at 35% of video width (>3× larger).
- **Solution**:
  1. Switched shape styles in `src/components/studio/VidoAIStudio.tsx` to percentage-based layout matching the canvas container:
     ```tsx
     width: `${widthPct}%`,
     height: `${heightPct}%`,
     ```
  2. Updated inner elements to `w-full h-full`.
  3. For `circle`, used `aspect-square h-full max-w-full rounded-full` so it remains a true circle bounded by $\min(W, H)$ identically to Pillow's rasterizer.
  4. For `arrow`, implemented an SVG vector polygon `<svg viewBox="0 0 100 100" preserveAspectRatio="none">` matching Pillow's rasterized arrow coordinates.

### C. Sticker Sizing Parity
- **Problem**: Canvas preview used fixed `64 * scale px` while backend rendered stickers at $0.25 \times \min(W, H) \times \text{scale}$.
- **Solution**:
  1. Added a `ResizeObserver` tracking `canvasDimensions` on `canvasViewportRef`.
  2. Dynamically computed sticker pixel dimensions matching the backend:
     ```tsx
     const minCanvasDim = Math.min(canvasDimensions.width, canvasDimensions.height);
     const stickerSizePx = Math.max(16, Math.round(minCanvasDim * 0.25 * scale));
     ```
  3. Scaled sticker container and inner icons proportionally.

### D. Media Scale Ceiling Removal
- **Problem**: Canvas preview applied `Math.min(80, 40 * scale)%`, artificially capping preview width at 80% when `scale > 2.0`.
- **Solution**: Changed to `Math.max(4, 40 * scale)%`, allowing previewing up to 120% at `scale = 3.0` matching backend overlay rendering.

### E. 1:1 Canvas Viewport
- **Problem**: 1:1 projects displayed in a 16:9 widescreen box.
- **Solution**: Added `aspectRatio === "1:1" ? "max-w-md aspect-square" : ...` to render a true 1:1 square canvas.

---

## 2. Live Server Details

Both servers are actively running in the background:
- **Frontend Server**: [http://localhost:3000](http://localhost:3000)
- **Backend Server**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Backend Health Endpoint**: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health) (Status: `ok`)

---

## 3. Manual Verification Steps

### Step 1: Open Studio
1. Open your browser and navigate to:
   ```text
   http://localhost:3000
   ```
2. Open or create a video project.

---

### Step 2: Test Text Rotation & Scale Parity
1. Add a **Text Layer** to the active scene.
2. In the Inspector or via the canvas gizmo:
   - Set **Scale** to `1.5x` (or drag a corner resize handle).
   - Set **Rotation** to `30°` (or drag the top rotation knob).
3. Observe:
   - Text is visibly enlarged and rotated clockwise at 30° on the canvas.
4. Save the project and trigger an export / render.
5. Verify in the exported video:
   - The burned-in text appears with the same enlarged font size and 30° clockwise rotation as seen on canvas.

---

### Step 3: Test Shape Sizing Parity
1. Add a **Rectangle** shape layer.
2. Observe its size on the canvas preview:
   - It now occupies approximately 35% of the canvas width and 20% of the canvas height.
3. Resize the browser window:
   - Notice that the shape smoothly scales with the canvas container, preserving its 35% width and 20% height proportions.
4. Export the scene:
   - Verify the exported video displays the rectangle with identical proportional dimensions to the canvas preview.

---

### Step 4: Test Sticker Sizing Parity
1. Add a **Star** or **Heart** sticker layer.
2. Observe its size on the canvas preview:
   - It now occupies 25% of the smaller canvas dimension.
3. Test scaling the sticker (e.g. `scale = 1.5`):
   - The sticker and inner icon scale smoothly.
4. Export and compare:
   - The sticker's size relative to the frame in the exported video matches the preview.

---

### Step 5: Test Media High Scale
1. Select an image or video layer.
2. Use the Inspector or corner gizmo handle to increase scale to `2.5x` or `3.0x`.
3. Verify:
   - The preview no longer caps at 80%; it expands up to 120% of the canvas width.

---

### Step 6: Test 1:1 Aspect Ratio Canvas
1. In the Studio header or settings, switch the project aspect ratio to **1:1**.
2. Verify:
   - The central canvas viewport immediately adapts into a true square box (`aspect-square`), perfectly representing a 1:1 Instagram/square video project.

---

## 4. Automated Verification Commands

To re-run the verification suites:

```bash
# Frontend Unit Tests (27 tests)
npx tsx src/lib/canvasTransformUtils.test.ts

# TypeScript Typecheck
npx tsc --noEmit

# Frontend Production Build
npm run build

# New Phase 36 Render Parity Test Suite (19 tests)
backend\.venv\Scripts\pytest backend/tests/test_studio_text_rotation_render.py

# Full Studio Backend Regression Suite (97 tests)
backend\.venv\Scripts\pytest backend/tests/test_studio_interactive_timeline.py backend/tests/test_studio_elements_shapes_stickers.py backend/tests/test_studio_media_layers.py backend/tests/test_studio_text.py backend/tests/test_studio_captions.py backend/tests/test_studio_music_media.py backend/tests/test_studio_pipeline_e2e.py backend/tests/test_timeline_compositor.py backend/tests/test_studio_canvas_manipulation.py backend/tests/test_studio_text_rotation_render.py
```
