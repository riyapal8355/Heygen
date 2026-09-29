# Phase 35 — Studio Render Parity & Remaining Canvas Gaps Audit Walkthrough

## Overview

This walkthrough provides a concise, engineering-focused explanation of the Phase 35 audit findings, detailing the mathematical root causes of preview-to-render discrepancies in HeyZen Studio and outlining the exact implementation blueprint for closing them.

---

## 1. The Core Render Parity Pipeline

When a user manipulates a layer in HeyZen Studio:
1. The **Canvas Viewport** updates local React DOM elements using CSS (`left`, `top`, `width`, `transform: translate(-50%, -50%) rotate(...)`).
2. On release, the transform is committed to PostgreSQL JSONB storage as `SceneLayer.transform`:
   ```json
   { "x": 0.5, "y": 0.5, "scale": 1.2, "rotation": 30.0 }
   ```
3. During export, `TimelineCompositor` translates these canonical transforms into FFmpeg video filter chains and ASS v4.00+ subtitle scripts.

---

## 2. Summary of Confirmed Gaps & Root Causes

### Gap 1: Text Overlays Ignore Rotation & Scale in Backend Export
- **Where**: `backend/app/media/compositor.py` -> `_generate_scene_text_ass_file` (lines 355–408).
- **Root Cause**: The ASS generator only extracts `x` and `y` from `layer.transform`. `scale` and `rotation` are completely omitted.
- **Libass Angle Sign Inversion**:
  - In CSS: `rotate(30deg)` rotates **clockwise**.
  - In ASS: `\frz30` rotates **counter-clockwise** (Cartesian convention).
  - Empirical FFmpeg verification proved that to rotate clockwise by `rotation` degrees, ASS requires:
    $$\backslash\text{frz}\{\text{round}(-\text{rotation}, 2)\}$$
- **Scale Resolution**: In ASS, `scale` must multiply the layer style's `font_size`:
  $$\text{effective\_font\_size} = \max(8, \text{int}(\text{round}(\text{font\_size} \times \text{scale})))$$

### Gap 2: Shape Sizing & Aspect Ratio Distortion
- **Where**: `src/components/studio/VidoAIStudio.tsx` (lines 2016–2105).
- **Root Cause**: The frontend multiplies normalized width/height by a fixed `2.5px` instead of using percentage of canvas width/height.
- **The Discrepancy**:
  - On a 768px canvas, a default rectangle ($w=0.35$) displays at $35 \times 2.5\text{px} = 87.5\text{px}$ (only **11.4%** of preview width).
  - In backend FFmpeg, the same rectangle renders at $35\% \times 1920\text{px} = 672\text{px}$ (**35.0%** of video width).
  - The exported shape is **3.07× larger** than previewed.
  - Furthermore, aspect ratios distort: 1.75:1 on canvas preview vs 3.11:1 in 16:9 export.
- **Fix**: Replace `widthPct * 2.5px` with standard CSS percentage:
  ```tsx
  width: `${widthPct}%`,
  height: `${heightPct}%`
  ```

### Gap 3: Sticker Sizing Discrepancy
- **Where**: `src/components/studio/VidoAIStudio.tsx` (lines 2142–2143) vs `backend/app/media/compositor.py` (lines 698–702).
- **Root Cause**: The frontend uses a static `64 * scale px`, whereas the backend computes sticker dimensions from $0.25 \times \min(\text{width}, \text{height}) \times \text{scale}$ (270px on a 1080p canvas, which corresponds to 108px on a 432p preview).
- **Fix**: Calculate frontend sticker size relative to canvas container dimensions.

### Gap 4: Media Scale Clamping Ceiling
- **Where**: `src/components/studio/VidoAIStudio.tsx` (line 1885).
- **Root Cause**: `Math.min(80, 40 * scale)%` restricts the preview to a maximum of 80% canvas width, whereas backend scales up to 120% at `scale = 3.0`.
- **Fix**: Remove the artificial 80% ceiling.

### Gap 5: 1:1 Aspect Ratio Canvas Viewport
- **Where**: `src/components/studio/VidoAIStudio.tsx` (line 1782).
- **Root Cause**: Container styling only branches on `aspectRatio === "9:16"` and falls back to `aspect-video` (16:9), showing a widescreen box for 1:1 projects.
- **Fix**: Add `aspect-square` styling when `aspectRatio === "1:1"`.

---

## 3. Implementation Plan for Next Milestone

```text
1. Backend Compositor (backend/app/media/compositor.py):
   ├── Update _generate_scene_text_ass_file()
   ├── Multiply font_size by scale
   └── Inject \frz{-rotation} into dialogue event tags

2. Backend Automated Tests (backend/tests/test_studio_text_rotation_render.py):
   ├── Verify ASS script text tags contain \frz{-rotation}
   └── Render synthetic scene and verify rotated text pixel burn-in

3. Frontend Studio (src/components/studio/VidoAIStudio.tsx):
   ├── Change shape styles from px to % of canvas container
   ├── Align sticker size to 0.25 * min(width, height)
   ├── Remove 80% media scale ceiling
   └── Add 1:1 aspect-square viewport support

4. Regression & Verification:
   ├── Run 78+ backend studio tests
   ├── Run TypeScript check (npx tsc --noEmit)
   └── Run production build (npm run build)
```

---

## 4. Verification & Testing Strategy

1. **Deterministic ASS Validation**: Verify generated `.ass` files directly:
   - `\frz-45` for `rotation = 45.0`
   - `\frz45` for `rotation = -45.0`
   - `Fontsize = 96` for `font_size = 48, scale = 2.0`
2. **Pixel-Level Video Verification**: Extract frames at $t=1.0s$ using FFmpeg and verify pixel luminance in expected quadrants for rotated text and properly proportioned shapes.
3. **Database Integrity**: Zero database migrations.
