# Phase 7: Real Media Rendering Engine Architecture & Verification

## 1. Overview

Phase 7 introduces the **Real Media Rendering Engine** for HeyZen. It elevates the platform from synthetic/mock fixtures to broadcast-quality, deterministic multi-scene MP4 video composition using real **FFmpeg** and **FFprobe** subprocesses.

The engine coordinates the end-to-end rendering workflow:
1. Validating frozen `ProjectDocumentV1` revisions.
2. Resolving project media assets securely from MinIO object storage into isolated tenant workspaces.
3. Synthesizing visual canvases (aspect ratios 16:9, 9:16 vertical shorts, 1:1 square) using solid colors, images, or video clips.
4. Aligning and padding narration speech audio tracks with EBU R128 loudness normalization and stereo parity.
5. Overlaying typography captions with safe parameter escaping.
6. Assembling multi-scene cuts losslessly using the FFmpeg concat demuxer (with filtergraph concat fallback).
7. Blending background music tracks with volume ducking and mixing.
8. Validating rendered media containers and streams with real `ffprobe`.
9. Ingesting master MP4 and extracted PNG poster thumbnails into MinIO via `AssetLifecycleManager`.
10. Updating database Job states to `succeeded` and target Project status to `ready`.

---

## 2. Architecture & Component Structure

```
+-----------------------------------------------------------------------------------+
|                              HeyZen Fast/Async Core                               |
|                                                                                   |
|  +---------------------+      +------------------------+      +----------------+  |
|  | ProjectDocumentV1   | ---> | TimelineCompositor     | ---> | MediaWorkspace |  |
|  | (Settings & Scenes) |      | (app/media/compositor) |      | (inputs/scenes)|  |
|  +---------------------+      +------------------------+      +----------------+  |
|                                           |                           |           |
|                               +-----------+-----------+               v           |
|                               |                       |       +----------------+  |
|                               v                       v       | MinIO Storage  |  |
|                     +-------------------+   +-----------------+ (Asset Resolv) |  |
|                     | FFmpegService     |   | FFprobeService  | +----------------+  |
|                     | (Execution Engine)|   | (Stream Probe)  |                   |
|                     +-------------------+   +-----------------+                   |
|                               |                       |                           |
|                               +-----------+-----------+                           |
|                                           |                                       |
|                                           v                                       |
|                               +------------------------+                          |
|                               | Real Render Worker     |                          |
|                               | (media_tasks.py)       |                          |
|                               +------------------------+                          |
|                                           |                                       |
|                  +------------------------+------------------------+              |
|                  v                                                 v              |
|       +-----------------------+                         +----------------------+  |
|       | AssetLifecycleManager |                         | Project Repository   |  |
|       | (Ingest MP4 + PNG)    |                         | (status = "ready")   |  |
|       +-----------------------+                         +----------------------+  |
+-----------------------------------------------------------------------------------+
```

### Key Modules

- **`app.media.discovery` (`find_media_binary`)**:
  Discovers external media binaries across system PATH and known OS installation paths (including Windows WinGet packages/links and program files) while respecting explicit test overrides.

- **`app.media.ffprobe` (`FFprobeService`)**:
  Dedicated media inspection service. Parses format metadata, video/audio stream arrays, duration, frame rates, sample rates, and channel layouts. Provides `validate_render_output()` to strictly reject 0-byte, corrupt, missing-stream, or truncated files.

- **`app.media.ffmpeg` (`FFmpegService`)**:
  Safe subprocess executor with async execution, configurable timeouts, cancellation cleanup, audio normalization (`loudnorm=I=-16:TP=-1.5:LRA=11`), frame extraction, and waveform peak generation.

- **`app.media.filters`**:
  Safe filter string generators for `color` canvases, aspect ratio scale & pad (`contain`, `cover`, `stretch`), external file-referenced `drawtext` (preventing shell injection and Windows path escaping bugs), `volume` gain, and `amix` multi-track audio blending.

- **`app.media.workspace` (`MediaWorkspace`)**:
  Context manager isolating temp scratch space into `inputs/`, `scenes/`, `audio/`, and `output/` subdirectories. Safely resolves and downloads tenant-isolated assets from MinIO with path traversal guards and automated rmtree cleanup.

- **`app.media.compositor` (`TimelineCompositor`)**:
  Modular timeline compositor orchestrating per-scene clip generation, multi-scene concatenation, audio mixing, output validation, and poster extraction with cooperative cancellation hooks.

- **`app.workers.tasks.media_tasks` (`_execute_render_video`)**:
  Celery task worker executing real media rendering when `AI_PROVIDER_MODE != "mock"`, reporting progressive stages (`analyzing_timeline` -> `preparing_assets` -> `rendering_scenes` -> `assembling` -> `validating_output` -> `uploading_output`), ingesting outputs, and updating database state.

---

## 3. Real Acceptance Path

In compliance with Phase 7 requirements:
1. Mocked FFmpeg subprocesses are permitted **only** in isolated mock unit tests.
2. The authoritative acceptance path verifies real FFmpeg execution:
   - **Input**: A valid `ProjectDocumentV1` with multiple scenes, canvas dimensions, background colors, and speech scripts.
   - **Render**: Real FFmpeg renders each scene clip with `libx264` (yuv420p) and `aac` (48000 Hz, stereo).
   - **Assembly**: Lossless stream concat demuxer concatenates scene clips into master MP4.
   - **Validation**: Real `ffprobe` validates container duration, video stream dimensions, and audio stream channel layout.
   - **Ingestion**: `AssetLifecycleManager` uploads MP4 and PNG thumbnail to MinIO storage under `workspaces/{workspace_id}/assets/{asset_id}/{filename}` and creates catalog `Asset` records.
   - **Job Completion**: Render `Job` status updates to `succeeded` with full output metadata.
   - **Project Promotion**: Target `Project.status` updates from `processing` to `ready`, with `project.thumbnail_asset_id` pointing to the newly generated thumbnail asset.

---

## 4. Verification Results

### Test Suite Execution
- **Phase 7 Media Tests**: 39 / 39 passed (100%).
- **Full Backend Regression Suite**: 199 / 199 passed (100%).
- **Total Test Execution Duration**: ~69 seconds.

### Service Integrity
- **Frontend**: Running on `http://localhost:3000` (HTTP 200, untouched).
- **Backend API**: Running on `http://127.0.0.1:8000` (HTTP 200 `/health`, HTTP 200 `/ready`).
- **Database Schema**: Alembic head locked at `0005_jobs_task_pipeline` (0 new migrations).
- **Python Dependencies**: Pyproject.toml clean (0 new external dependencies added).
