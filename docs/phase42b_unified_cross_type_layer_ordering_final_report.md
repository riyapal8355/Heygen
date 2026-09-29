# Phase 42B — Studio Unified Cross-Type Layer Ordering Final Report

## Executive Summary
Phase 42B implements canonical, cross-type visual layer stacking and reordering in HeyZen Studio. Visual layers of differing types (images, videos, text, shapes, stickers) can now be freely interleaved, reordered, duplicated, and deleted in a unified stacking sequence while strictly preserving:
- Existing typed scene storage (`media_layers`, `text_layers`, `element_layers`, and captions) without requiring breaking schema migrations or a new physical `scene.layers[]` column.
- Phase 38 layer locking and `enabled` visibility models.
- Phase 39 keyboard navigation and shortcuts.
- Phase 40 undo/redo history engine.
- Phase 42A canvas magnetic snapping and audio history.

---

## 1. Architectural Design & Implementation

### 1.1 Canonical `z_index` Ordering Model
Every visual layer now specifies an optional integer `z_index` (defaulting to `0`).
- **Convention**: Lower values are rendered behind; higher values are rendered in front.
- **Normalization Engine**: `normalizeLayerZIndices` guarantees that any set of visual layers is deterministically mapped to consecutive integer indices `[0, 1, ..., N-1]`.
- **Legacy Compatibility**: Legacy documents or layers missing `z_index` are deterministically assigned baseline tiers (`media` -> `text` -> `elements`) without modifying the database schema or breaking existing project documents.

### 1.2 Preservation of Existing Architecture
- **Typed Scene Storage Preserved**: `media_layers`, `text_layers`, `element_layers` and subtitles remain untouched as the underlying persistence model.
- **Zero Database Migration**: `z_index` is stored directly inside the existing JSONB document structure in PostgreSQL.
- **Derivation & Distribution**: When displaying in the unified layer list or canvas, `deriveUnifiedVisualLayers` dynamically sorts layers across all visual collections by `z_index`. Reordering operations re-assign `z_index` values and cleanly distribute them back into the scene.

### 1.3 Controls & User Experience
- **Unified Layers Panel (`UnifiedLayersPanel.tsx`)**:
  - Displays all visual layers in top-to-bottom visual order (index `N-1` at the top, index `0` at the bottom).
  - Drag-and-drop reordering with live index calculation.
  - Quick action buttons: **Bring to Front**, **Bring Forward**, **Send Backward**, **Send to Back**.
  - Direct integration with Phase 38 visibility toggling and layer locking guards.
  - Quick duplicate and delete actions maintaining consecutive `z_index` values.
- **Canvas Stacking**:
  - Replaced hardcoded CSS layer classes (`z-23`, `z-24`) with dynamic styles: `zIndex: 20 + layer.z_index`.
  - Guarantees 100% canvas visual fidelity matching the ordering in the inspector.
- **Keyboard Shortcuts**:
  - `Ctrl/Cmd + ]` : Bring Layer Forward (swaps with layer directly in front).
  - `Ctrl/Cmd + [` : Send Layer Backward (swaps with layer directly behind).
  - `Ctrl/Cmd + Shift + ]` : Bring Layer to Front (moves to index `N-1`).
  - `Ctrl/Cmd + Shift + [` : Send Layer to Back (moves to index `0`).
  - Fully integrated with Phase 38 locking guards (locked layers cannot be reordered) and Phase 40 undo/redo (all reordering is committed to history).

---

## 2. Render Parity & Limitations Analysis

### 2.1 Canvas Preview vs. Backend FFmpeg Compositor
| Layer Types | Canvas Preview | Backend Compositor (FFmpeg Export) | Status |
|:---|:---|:---|:---|
| **Media ↔ Media** (Image/Video) | Exact `z_index` stacking (`zIndex: 20 + z`) | Exact overlay sorting by `z_index` | **PASS (Full Parity)** |
| **Media ↔ Element** (Shape/Sticker) | Exact `z_index` stacking | Exact overlay sorting by `z_index` | **PASS (Full Parity)** |
| **Element ↔ Element** | Exact `z_index` stacking | Exact overlay sorting by `z_index` | **PASS (Full Parity)** |
| **Text/Captions ↔ Media/Element** | Exact `z_index` stacking | Filtergraph separation (Pillow/FFmpeg overlay vs. ASS subtitle burn-in) | **PARTIAL (Documented Limitation)** |

### 2.2 Exact Technical Limitation (ASS Subtitle Burn-In)
- In `backend/app/media/compositor.py`, `visual_media_layers` (images, videos, shapes, stickers) are composited onto the video canvas via FFmpeg `overlay` filter chains sorted by `z_index`.
- Text layers and speech subtitles are rendered via FFmpeg's `ass` subtitle filter, which burns text onto the frame *after* the overlay filter chain completes.
- **Impact**: In exported MP4 video, text layers will always appear in front of media and element overlays, even if their `z_index` is configured lower than a media layer. Full cross-type interleaving for text under media would require rasterizing text layers into transparent RGBA image streams prior to FFmpeg overlay compositing.

---

## 3. Verification Matrix

| Area | Requirement | Test Result |
|:---|:---|:---|
| **Z-Index Normalization** | Normalize sparse, negative, or duplicated indices to consecutive `0..N-1` | **PASS** (`studioLayerOrdering.test.ts`) |
| **Legacy Document Baseline** | Deterministic `media -> text -> elements` tiering when `z_index` is omitted | **PASS** (`studioLayerOrdering.test.ts`) |
| **Bring Forward / Backward** | Single-step swap with adjacent layer; boundary clamping at ends | **PASS** (`studioLayerOrdering.test.ts`) |
| **Bring to Front / To Back** | Jump to indices `N-1` and `0` respectively | **PASS** (`studioLayerOrdering.test.ts`) |
| **Arbitrary Reorder** | Safe cross-type insertion at index `toIndex` | **PASS** (`studioLayerOrdering.test.ts`) |
| **Duplication Placement** | Insert duplicate immediately above source layer (`z_index = source.z_index + 1`) | **PASS** (`studioLayerOrdering.test.ts`) |
| **Deletion Re-normalization** | Remove target layer and compact remaining indices to `0..N-1` | **PASS** (`studioLayerOrdering.test.ts`) |
| **Phase 38 Locking Guards** | Block reordering, nudging, duplication, deletion when `locked: true` | **PASS** (5 dedicated test cases) |
| **Phase 38 Visibility Guard** | Layer visibility (`enabled: false`) is orthogonal to stacking order | **PASS** (`studioLayerOrdering.test.ts`) |
| **Phase 39 Shortcuts** | `Ctrl+]`, `Ctrl+[`, `Ctrl+Shift+]`, `Ctrl+Shift+[` reorder active layer | **PASS** |
| **Phase 40 History** | Reordering and duplicate/delete operations push undoable steps | **PASS** |
| **TypeScript Compilation** | `npx tsc --noEmit` | **PASS** (0 errors) |
| **Frontend Test Suite** | `npx tsx --test src/lib/*.test.ts` | **PASS** (160/160 passing) |
| **Backend Regression Suite**| `pytest -k studio -q` | **PASS** (98/98 passing) |
| **Production Build** | `npm run build` | **PASS** (Static optimization & bundle verified) |

---

## 4. Service Health Status

All required development and test services remained active throughout implementation and are currently healthy:

| Service | Port | Process / Status |
|:---|:---|:---|
| **Next.js Dev Server** | `3000` | PID 9036 (Listening) |
| **FastAPI Backend** | `8000` | PID 15688 (Listening) |
| **PostgreSQL Database** | `5432` | PID 6508 (Docker container `heyzen-postgres`) |
| **MinIO Object Storage** | `9000` / `9001` | PID 7764 (Docker container `heyzen-minio`) |
| **Redis Cache / PubSub** | `6379` | PID 7764 (Docker container `heyzen-redis`) |
| **Docker Engine** | — | Healthy |
