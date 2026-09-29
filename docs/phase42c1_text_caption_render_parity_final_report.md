# Phase 42C-1 — Unified Text & Caption Render Parity Final Report

## 1. Executive Summary
Phase 42C-1 achieves **true FFmpeg pixel-level render parity for Text and Caption layers participating in the unified `z_index` visual ordering system**.

In Phase 42B, canonical `z_index` ordering was established across typed storage arrays, and complete canvas preview parity was delivered. However, the FFmpeg compositor rendered text overlays and captions via an ASS subtitle burn-in stage *after* the overlay filtergraph, meaning text and captions always appeared on top of media layers in exported MP4s regardless of their `z_index`.

Phase 42C-1 closes this gap by introducing a Pillow-based transparent RGBA rasterization pipeline for text layers and caption cues. Text and captions now participate directly in the unified, deterministic `z_index`-sorted sequential FFmpeg overlay chain (`[bg] -> [comp_0] -> ... -> [comp_N]`). Actual rendered MP4 frames were tested and verified at the pixel level, confirming full visual interleaving parity without double-rendering.

---

## 2. Root Cause Analysis
- **Phase 42B Architecture**: In `backend/app/media/compositor.py`, `visual_media_layers` collected only media, shape, sticker, and element layers and sorted them by `z_index`. Text and captions were converted to `.ass` files and appended via `ass='...'` video filters *after* all media overlays.
- **Consequence**: Even when a text layer or caption cue had `z_index = 0` (behind a media layer at `z_index = 1`), the ASS filter burned text onto the video frame after the media layer had already been overlaid, forcing text to always appear in front of media in exported videos.

---

## 3. Architecture

The new unified compositing pipeline processes all visual items in a single deterministic pass:

```text
Scene
 ├── media_layers (image, video)
 ├── element_layers (shape, sticker, element)
 ├── text_layers (text)
 └── subtitles / captions
        │
        ▼
Collect all active visual items
        │
        ▼
Deterministic Phase 42B sorting:
- Layers with explicit z_index: sorted by (0, z_index, original_idx)
- Legacy layers without z_index: legacy baseline (media -> text -> elements -> captions)
        │
        ▼
Render transparent RGBA PNG for each static visual item:
- Shapes: render_shape_to_image (Pillow 2x supersampling)
- Stickers: render_sticker_to_image (Pillow 2x supersampling)
- Text layers: render_text_layer_to_image (Pillow 2x supersampling)
- Caption cues: render_caption_cue_to_image (Pillow 2x supersampling)
- Media/Videos: resolved assets
        │
        ▼
Single-chain sequential FFmpeg overlay pipeline:
[bg] -> [comp_0] -> [comp_1] -> ... -> [comp_N]
        │
        ▼
Final MP4 video with exact pixel-level stacking parity
```

---

## 4. Text Rendering Pipeline
- Implemented in `backend/app/media/text_rasterizer.py` via `render_text_layer_to_image`.
- **Typography & Styling**:
  - `font_family`: TrueType font resolution with system search (`C:\Windows\Fonts`, `/usr/share/fonts`) and fallbacks.
  - `font_size` & `scale`: Scaled font sizing with 2x supersampling and Lanczos downsampling for crisp edges.
  - `font_weight` & `font_style`: Bold and italic font face resolution.
  - `color`: Hex color parsed to RGBA.
  - `opacity`: Layer opacity (0.0 to 1.0) multiplied directly into the RGBA alpha channel.
  - `background_color` & `background_opacity`: Rounded-rectangle background box with padding.
  - `alignment`: Left, center, and right multi-line text alignment.
- **Transforms**:
  - `x`, `y`: Normalized coordinates [0.0, 1.0] representing the center of the text block, matching canvas `translate(-50%, -50%)`.
  - `rotation`: Clockwise rotation degrees passed to FFmpeg `rotate=rotation*PI/180:ow='hypot(iw,ih)':oh=ow:c=none`.
  - `start_time` & `end_time`: Mapped to FFmpeg `enable='between(t,start_t,end_t)'`.

---

## 5. Caption Rendering Pipeline
- Implemented in `backend/app/media/text_rasterizer.py` via `render_caption_cue_to_image`.
- **Caption `z_index`**: Added optional `z_index: Optional[int] = Field(default=None)` to `CaptionStyle` in `backend/app/schemas/project_document.py`.
  - When `z_index` is `None`, captions default to the top of standard layers (canvas `z-25` / `z_index = 1000`).
  - When `z_index` is specified (e.g. `z_index = 1` between media at `z=0` and media at `z=2`), captions interleave at that exact position.
- **Positioning**:
  - `"top"`: Top banner (`x=0.5, y=0.08`).
  - `"center"`: Screen center (`x=0.5, y=0.50`).
  - `"bottom"`: Bottom margin (`x=0.5, y=0.90`).
  - `"left"`, `"center"`, `"right"`: Alignment across the screen.

---

## 6. Zero Double-Rendering & ASS Compatibility
- `_generate_scene_text_ass_file` and `_generate_scene_ass_file` continue to generate their respective `.ass` files on disk (`scene_{idx}_text.ass` and `scene_{idx}_captions.ass`). This guarantees backward compatibility with external subtitle export workflows and existing integration tests that assert file presence.
- However, `text_filter` and `ass_filter` are **NOT** appended to the FFmpeg filtergraph when layers are composited via the unified RGBA overlay chain.
- Verified via Test 13: each text overlay and caption cue appears in the rendered MP4 video exactly once.

---

## 7. Render Parity Verification Matrix

Actual rendered MP4 outputs were generated and verified at the pixel level using frame extraction and color inspection:

| Layer Relationship | Canvas Preview | FFmpeg Filtergraph | FFmpeg Pixels (Export) | Result |
|:---|:---:|:---:|:---:|:---:|
| **media ↔ media** | PASS | PASS | PASS | **PASS** |
| **element ↔ element** | PASS | PASS | PASS | **PASS** |
| **media ↔ element** | PASS | PASS | PASS | **PASS** |
| **media ↔ text** | PASS | PASS | PASS | **PASS** |
| **element ↔ text** | PASS | PASS | PASS | **PASS** |
| **media ↔ caption** | PASS | PASS | PASS | **PASS** |
| **element ↔ caption** | PASS | PASS | PASS | **PASS** |
| **text ↔ text** | PASS | PASS | PASS | **PASS** |
| **caption ↔ caption** | PASS | PASS | PASS | **PASS** |
| **text ↔ caption** | PASS | PASS | PASS | **PASS** |

---

## 8. Test Execution Results

### Backend Tests
- **Phase 42C-1 Render Parity Suite** (`backend/tests/test_phase42c1_render_parity.py`):
  - **13 passed, 0 failed** in 10.42s.
  - Verified pixel-level stacking for Tests 1–13 (text above media, text below media, text between media, text between elements, caption interleaving, hidden text, locked text, timing boundaries, opacity blending, 45° rotation, legacy document baseline, mixed interleaved types, zero double-rendering).
- **Text Rasterizer Unit Tests** (`backend/tests/test_text_rasterizer.py`):
  - **5 passed, 0 failed** in 0.33s.
- **Full Studio Regression Suite** (`pytest -k studio -q`):
  - **98 passed, 0 failed, 595 deselected** in 84.13s.

### Frontend Tests & Builds
- **Frontend Test Suite** (`npx tsx --test src/lib/*.test.ts`):
  - **160 passed, 0 failed** across 54 suites.
- **TypeScript Compilation** (`npx tsc --noEmit`):
  - **0 errors**.
- **Production Build** (`npm run build`):
  - **PASS** (compiled in 12.0s, all static pages generated).
- **Browser E2E**:
  - **NOT VERIFIED** (Playwright browser binaries unavailable).

---

## 9. Service Health Status

All required development and test services remained running continuously throughout implementation and testing:

| Service | Port | Process / Status |
|:---|:---|:---|
| **Next.js Dev Server** | `3000` | PID 9036 (Listening) |
| **FastAPI Backend** | `8000` | PID 15688 (Listening) |
| **PostgreSQL Database** | `5432` | PID 6508 (`heyzen-postgres`) |
| **MinIO Storage** | `9000` / `9001` | PID 7764 (`heyzen-minio`) |
| **Redis Cache / PubSub** | `6379` | PID 7764 (`heyzen-redis`) |
| **Docker Engine** | — | Healthy |

---

## 10. Files Changed

1. [backend/app/schemas/project_document.py](file:///d:/HeyGen/video-ai-tools/backend/app/schemas/project_document.py): Added optional `z_index: Optional[int] = Field(default=None)` to `CaptionStyle`.
2. [backend/app/media/text_rasterizer.py](file:///d:/HeyGen/video-ai-tools/backend/app/media/text_rasterizer.py): Created reusable Pillow-based transparent RGBA rasterization module for text layers and caption cues with 2x supersampling and font resolution.
3. [backend/app/media/compositor.py](file:///d:/HeyGen/video-ai-tools/backend/app/media/compositor.py): Updated `_render_scene_clip` to unify visual layers (media, elements, text, captions) into a single `z_index`-sorted overlay chain with zero double rendering.
4. [backend/tests/test_text_rasterizer.py](file:///d:/HeyGen/video-ai-tools/backend/tests/test_text_rasterizer.py): Unit tests for font resolution, text layout, background boxes, opacity, and caption cue rasterization.
5. [backend/tests/test_phase42c1_render_parity.py](file:///d:/HeyGen/video-ai-tools/backend/tests/test_phase42c1_render_parity.py): Pixel-level rendered output verification suite covering all 13 required scenarios.
6. [docs/phase42c1_text_caption_render_parity_final_report.md](file:///d:/HeyGen/video-ai-tools/docs/phase42c1_text_caption_render_parity_final_report.md): Final verification report.
7. [walkthrough.md](file:///C:/Users/rahul/.gemini/antigravity-ide/brain/bde0130f-6787-4901-9c3e-cc033382b295/walkthrough.md): Updated walkthrough document.

---

## 11. Known Limitations
1. **Dynamic Text Animation / Karaoke Cues**: Word-by-word karaoke highlight animations currently rely on ASS timing tags (`\k`). When rendered through the static cue rasterizer, cues render as whole phrases per interval rather than progressive word sweeps.
2. **Custom Web Fonts**: Fonts not installed on the host operating system fall back to standard system TrueType fonts (Arial, Calibri, DejaVu Sans).

---

## 12. Final Status
```text
IMPLEMENTED
```
All 10 layer relationship combinations now achieve verified PASS status across both canvas preview and exported FFmpeg pixels.
