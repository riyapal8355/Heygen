# HeyZen — Complete Technical Documentation

> **Autonomous AI Video Creation & Interactive Studio Platform**  
> *Repository*: `D:\HeyGen\video-ai-tools`  
> *Target Version*: `0.1.0` | *Architecture*: Microservices / Multi-Tier Hybrid  
> *Audience*: Core Engineers, Solution Architects, DevOps, AI Researchers, and Security Auditors  

---

## Table of Contents
1. [Executive Overview](#1-executive-overview)
2. [Technology Stack & Runtime Specifications](#2-technology-stack--runtime-specifications)
3. [Repository Structure & File Responsibilities](#3-repository-structure--file-responsibilities)
4. [Frontend Architecture](#4-frontend-architecture)
5. [Authentication & Session Lifecycle](#5-authentication--session-lifecycle)
6. [Global Theme System](#6-global-theme-system)
7. [Video Agent Pipeline](#7-video-agent-pipeline)
8. [Interactive Studio Engine](#8-interactive-studio-engine)
9. [Studio Video Render Pipeline](#9-studio-video-render-pipeline)
10. [Media Pipeline & Compositor](#10-media-pipeline--compositor)
11. [AI Services & Neural Adapters](#11-ai-services--neural-adapters)
12. [Multi-Language Video Translation](#12-multi-language-video-translation)
13. [Brand Systems & Terminology Glossaries](#13-brand-systems--terminology-glossaries)
14. [Avatars, Digital Twins & Voices](#14-avatars-digital-twins--voices)
15. [Projects & Version Control (OCC)](#15-projects--version-control-occ)
16. [Database Schema & Migrations](#16-database-schema--migrations)
17. [Storage Architecture (MinIO / S3)](#17-storage-architecture-minio--s3)
18. [API Reference Overview](#18-api-reference-overview)
19. [Asynchronous Jobs & SSE Streaming](#19-asynchronous-jobs--sse-streaming)
20. [Developer Platform & Webhooks](#20-developer-platform--webhooks)
21. [Security Architecture & RBAC](#21-security-architecture--rbac)
22. [Testing Framework & Verification Results](#22-testing-framework--verification-results)
23. [Playwright E2E Automation](#23-playwright-e2e-automation)
24. [Developer Setup & Local Orchestration](#24-developer-setup--local-orchestration)
25. [Environment Variables Reference](#25-environment-variables-reference)
26. [Production Deployment & Infrastructure](#26-production-deployment--infrastructure)
27. [Known Limitations & Technical Backlog](#27-known-limitations--technical-backlog)
28. [Troubleshooting Guide](#28-troubleshooting-guide)
29. [System Architecture Diagrams](#29-system-architecture-diagrams)
30. [Current Status Matrix](#30-current-status-matrix)
31. [Change & Milestone History](#31-change--milestone-history)
32. [Documentation Index & Companion Guides](#32-documentation-index--companion-guides)

---

## 1. Executive Overview

### 1.1 What HeyZen Is
**HeyZen** (also referenced as VidoAI in frontend branding) is an autonomous, enterprise-grade AI video creation and timeline editing studio. It bridges high-level generative AI (prompt-to-video decomposition, neural avatar speech synthesis, voice cloning, and multilingual video translation) with a precise, deterministic, non-linear multi-track timeline editor.

### 1.2 Purpose & Major Workflows
1. **Autonomous Video Agent**: Translates conversational or structured prompts into fully planned, multi-scene video blueprints with matched presenters, synthetic narration, background b-roll, text overlays, and transitions.
2. **Interactive Studio**: Provides a browser-based, desktop-class creative editor for direct canvas manipulation, timeline trimming/splitting, cross-type layer ordering, typography styling, burned subtitle customizer, and vector elements.
3. **Multilingual Translation & Localization**: Ingests existing video footage, extracts speech via faster-whisper, translates transcripts with CTranslate2 while strictly enforcing **Brand Glossaries**, resynthesizes target speech with Piper TTS, and re-renders localized project forks.
4. **Digital Twin & Custom Presenters**: Catalogs 2D photo avatars, custom talking actors, and zero-shot cloned voices via OpenVoice v2, with Annie configured as the platform's default presenter.
5. **Brand Systems Compliance**: Enforces corporate color palettes, custom typography, logo watermarks, and mandatory translation glossary rules across all generation and render outputs.

### 1.3 Current Capabilities
- Real-time client canvas transform gizmo with rotation, resize, and edge snapping.
- Complete non-linear timeline editing (split, trim, drag-move, snap, zoom, pan).
- Deterministic Optimistic Concurrency Control (OCC) revision tracking across all mutations.
- Multi-queue Celery task topology routing CPU-friendly tasks (`cpu_media`) and GPU-dependent workloads (`gpu_ai`).
- Real-time Server-Sent Events (SSE) streaming of background job progress via Redis Pub/Sub.
- Direct pre-signed MinIO/S3 binary upload intents and SHA-256 verification.
- Zero-downtime, pre-hydration light/dark theme initialization without flash of unstyled content.

### 1.4 Implemented vs Partial vs Unverified
- **Fully Implemented & Verified**: Auth lifecycle, theme switching, project OCC versioning, Video Agent prompt flow, interactive timeline editing, undo/redo command stack, burned subtitles, text rasterizer, brand glossaries, developer API keys, webhooks, and Celery task routing.
- **Implemented with Fallbacks**: Avatar lip-sync (MuseTalk on CUDA with automatic fallback to CPU Wav2Lip or mock mode), speech enhancement (DeepFilterNet3 with fallback to SciPy spectral gating), scene visual generation (Stable Diffusion with fallback to mock renderer).
- **Unverified / Experimental**: External third-party OAuth providers (Google/GitHub SSO) are architecturally outlined but not currently active in route handlers; live video stream uploads via YouTube/GDrive require external network connectivity.

---

## 2. Technology Stack & Runtime Specifications

All versions reflect the active configurations in [package.json](file:///D:/HeyGen/video-ai-tools/package.json), [backend/requirements.txt](file:///D:/HeyGen/video-ai-tools/backend/requirements.txt), and [backend/requirements-gpu.txt](file:///D:/HeyGen/video-ai-tools/backend/requirements-gpu.txt).

### 2.1 Frontend Stack
- **Framework**: Next.js `16.3.4` (App Router architecture)
- **UI Runtime**: React `19.2.8` & React-DOM `19.2.8`
- **Language**: TypeScript `^5` (Strict typing enabled, `tsconfig.json`)
- **Styling**: Tailwind CSS `^4` (via `@tailwindcss/postcss` `^4` and custom tokens in `globals.css`)
- **Iconography**: Lucide React `^1.39.0`
- **Class Utilities**: `clsx` `^2.1.1` and `tailwind-merge` `^3.6.0`
- **E2E Testing**: `@playwright/test` `^1.63.0` (Configured with host `channel: "chrome"`)

### 2.2 Backend Stack
- **API Runtime**: FastAPI `>=0.111.0,<0.112.0` on Uvicorn `>=0.30.0,<0.31.0`
- **Language Engine**: Python `3.13.7` (Windows 64-bit Proactor loop policy)
- **Validation**: Pydantic `>=2.7.0,<3.0.0` & Pydantic-Settings `>=2.3.0,<3.0.0`
- **ORM & Database**: SQLAlchemy (asyncio) `>=2.0.30,<2.1.0` with `asyncpg` `>=0.29.0,<0.30.0`
- **Schema Migrations**: Alembic `>=1.13.1,<1.14.0`
- **Task Broker & Cache**: Celery `>=5.4.0,<6.0.0`, Kombu `>=5.3.7,<6.0.0`, Redis `>=5.0.4,<6.0.0`
- **Security & Crypto**: `argon2-cffi` `>=23.1.0`, `pyjwt[crypto]` `>=2.8.0`
- **HTTP Client**: HTTPX `>=0.27.0,<0.28.0`

### 2.3 Media & AI Processing Engines
- **Media Transcoding**: FFmpeg `9.0.1-essentials` & FFprobe `9.0.1-essentials`
- **Image & Computer Vision**: Pillow `>=10.3.0,<11.0.0`, OpenCV Headless `>=4.10.0.84`, NumPy `>=1.26.4,<2.0.0`
- **Audio DSP**: SciPy `>=1.13.0,<1.14.0`, SoundFile `>=0.12.1`
- **CPU AI Libraries**: `piper-tts` `>=1.8.0`, `onnxruntime` `>=1.20.0,<1.21.0`, `faster-whisper` `>=1.0.0,<2.0.0`, `ctranslate2` `>=4.4.0,<5.0.0`, `kokoro-onnx` `>=0.6.1`
- **GPU AI Acceleration** *(Optional CUDA stack)*: PyTorch `2.4.1+cu124`, `torchvision` `0.19.1+cu124`, `torchaudio` `2.4.1+cu124`, `diffusers` `0.30.3`, `accelerate` `0.34.2`, `transformers` `4.44.2`

### 2.4 Infrastructure & Cloud Services
- **Database**: PostgreSQL `16-alpine`
- **Broker**: Redis `7-alpine`
- **Object Storage**: MinIO `latest` (S3 API compatible)
- **Containerization**: Docker `29.7.2` & Docker Compose v2

---

## 3. Repository Structure & File Responsibilities

```text
D:\HeyGen\video-ai-tools
├── backend/                         # Backend Python services & worker processes
│   ├── alembic/                     # Database migration revisions
│   ├── app/                         # Core FastAPI application package
│   │   ├── ai/                      # AI adapters, hardware detection, model registry
│   │   ├── api/                     # REST API routers, dependencies, middleware
│   │   ├── core/                    # Config, security, exceptions, logging, redis
│   │   ├── db/                      # Session management, base mixins, seed fixtures
│   │   ├── media/                   # FFmpeg, FFprobe, compositor, text rasterizer, shapes
│   │   ├── models/                  # SQLAlchemy ORM domain entities
│   │   ├── repositories/            # Data access layer repositories
│   │   ├── schemas/                 # Pydantic request/response models & ProjectDocumentV1
│   │   ├── services/                # Business logic orchestrators & lifecycle managers
│   │   ├── storage/                 # MinIO / S3 client integration
│   │   └── workers/                 # Celery app, task queues (cpu_media, gpu_ai)
│   ├── pyproject.toml               # Python project configuration & pytest settings
│   ├── requirements.txt             # Lean CPU dependencies
│   ├── requirements-gpu.txt         # Pinned CUDA 12.4 dependencies
│   └── route_inventory.json        # Authoritative JSON index of all 122 API routes
├── docs/                            # Architectural reports, audits, and technical specifications
├── infrastructure/                  # Dockerfiles, Nginx configurations, and deployment manifests
├── public/                          # Static assets and public web files
├── src/                             # Next.js 16 frontend source code
│   ├── app/                         # Next.js App Router (layout.tsx, page.tsx, globals.css)
│   ├── components/                  # React UI components partitioned by domain
│   │   ├── apps/                    # Translate, Integrations, App Library
│   │   ├── auth/                    # Login, Register, Password modals
│   │   ├── avatars/                 # Avatars manager, Look designer
│   │   ├── brand/                   # Brand Systems, Logo upload, Glossaries
│   │   ├── create/                  # Video Agent prompt modal, SceneByScene, SingleScene
│   │   ├── dashboard/               # LeftRailNav, contextual sidebars, Onboarding
│   │   ├── developers/              # API keys management, Webhooks, Delivery logs
│   │   ├── projects/                # ProjectsManager, folders, sorting, cards
│   │   ├── studio/                  # VidoAIStudio, CanvasGizmo, TimelineTracks, Inspectors
│   │   ├── templates/               # Templates catalog, category filters
│   │   └── voices/                  # VoicesLibrary, VoiceCloning modal, audio preview
│   ├── context/                     # React Context providers (AuthContext, ThemeContext)
│   └── lib/                         # Client API library, utilities, and 89 unit test suites
├── tests/                           # Playwright end-to-end integration test suites
│   └── e2e/                         # smoke.spec.ts, auth-persistence.spec.ts
├── docker-compose.yml               # Local infrastructure (Postgres, Redis, MinIO)
├── docker-compose.prod.yml          # Production multi-container topology
├── package.json                     # Frontend dependencies and scripts
└── playwright.config.ts             # Playwright test configuration
```

---

## 4. Frontend Architecture

### 4.1 App Router & Entry Point
- **[layout.tsx](file:///D:/HeyGen/video-ai-tools/src/app/layout.tsx)**: Root layout establishing font variables (`GeistSans`, `GeistMono`), injecting the pre-hydration theme initialization script, and wrapping child views with [AppProviders](file:///D:/HeyGen/video-ai-tools/src/components/providers/AppProviders.tsx) (`ThemeProvider` -> `AuthProvider`).
- **[page.tsx](file:///D:/HeyGen/video-ai-tools/src/app/page.tsx)**: Single-Page Application (SPA) state machine hosting `DashboardContent`. Manages views dynamically: `dashboard`, `avatars`, `design_look`, `voices`, `brand`, `apps`, `projects`, `templates`, `studio`, `video_agent`, `scene_by_scene`, `single_scene`, `translate`, `brand_glossary`, and `developer`.

### 4.2 Navigation Architecture
- **[LeftRailNav.tsx](file:///D:/HeyGen/video-ai-tools/src/components/dashboard/LeftRailNav.tsx)**: 64px persistent vertical navigation rail providing top-level routing (Home, Create, Avatars/Voices, Brand Systems, Apps, Projects, Templates, Developers, Settings, Theme toggle, User profile).
- **Contextual Sidebars**: Expanding secondary sidebars dedicated to active rail sections:
  - [CreateSidebar.tsx](file:///D:/HeyGen/video-ai-tools/src/components/dashboard/CreateSidebar.tsx)
  - [ManageAvatarsSidebar.tsx](file:///D:/HeyGen/video-ai-tools/src/components/dashboard/ManageAvatarsSidebar.tsx)
  - [BrandSidebar.tsx](file:///D:/HeyGen/video-ai-tools/src/components/dashboard/BrandSidebar.tsx)
  - [AppsSidebar.tsx](file:///D:/HeyGen/video-ai-tools/src/components/dashboard/AppsSidebar.tsx)
  - [ProjectsSidebar.tsx](file:///D:/HeyGen/video-ai-tools/src/components/dashboard/ProjectsSidebar.tsx)
  - [TemplatesSidebar.tsx](file:///D:/HeyGen/video-ai-tools/src/components/dashboard/TemplatesSidebar.tsx)

### 4.3 Error Handling & Interceptors
The API client ([src/lib/api.ts](file:///D:/HeyGen/video-ai-tools/src/lib/api.ts)) intercepts all HTTP network operations. When a `401 Unauthorized` or `AUTH_TOKEN_EXPIRED` status is encountered, it automatically halts outgoing traffic, invokes `/api/v1/auth/refresh`, updates the memory token, and transparently replays the original request.

---

## 5. Authentication & Session Lifecycle

### 5.1 Real Implementation Flow
```text
User Submits Credentials -> POST /api/v1/auth/login
├── Backend validates Argon2id password hash in user_credentials table
├── Backend issues JWT Access Token (15m expiry, stored in client memory + localStorage fallback)
├── Backend generates random refresh secret, computes SHA-256 hash, and inserts record into user_sessions
├── Backend sets HttpOnly cookie: Set-Cookie: hz_refresh_token=<secret>; Path=/api/v1/auth; SameSite=Lax
└── Client receives 200 OK -> Calls GET /api/v1/auth/me -> Populates AuthContext -> Redirects to "/" (Home)
```

### 5.2 Session Restoration & Refresh Rotation
1. When a user reloads the application, [AuthContext.tsx](file:///D:/HeyGen/video-ai-tools/src/context/AuthContext.tsx) retrieves the stored access token. If absent or rejected with HTTP 401, it calls `/api/v1/auth/refresh`.
2. The refresh endpoint inspects the `hz_refresh_token` cookie, matches its SHA-256 hash against `user_sessions`, checks `revoked_at` and `expires_at`, and rotates the session:
   - Marks the old session record revoked (`revoked_at = now()`).
   - Issues a new access token and a fresh refresh secret.
   - Sets a new `hz_refresh_token` cookie.
3. If refresh fails, both client state and cookies are purged, returning the user safely to the login screen.

### 5.3 Demo / Instant Login
In non-production environments (`APP_ENV=development`), the login modal exposes an **Instant Demo Login** action pre-filling `dev@heyzen.ai` (`DevPassword123!`), which authenticates against seeded development fixtures in PostgreSQL. In production (`APP_ENV=production`), this shortcut is disabled and settings enforce fail-closed security.

---

## 6. Global Theme System

### 6.1 Theme Architecture
- **Context**: [ThemeContext.tsx](file:///D:/HeyGen/video-ai-tools/src/context/ThemeContext.tsx) exposes `theme` (`light` | `dark`), `toggleTheme()`, and `setTheme()`.
- **Persistence**: Saved immediately to `localStorage.getItem("vidoai_theme")`.
- **Pre-Hydration Anti-Flicker Script**: An inline JavaScript snippet inside `<head>` in [layout.tsx](file:///D:/HeyGen/video-ai-tools/src/app/layout.tsx) executes synchronously before HTML parsing completes:
  ```html
  <script>
    try {
      var theme = localStorage.getItem('vidoai_theme');
      if (theme === 'light') {
        document.documentElement.classList.remove('dark');
        document.documentElement.classList.add('light');
        document.documentElement.setAttribute('data-theme', 'light');
        document.documentElement.style.colorScheme = 'light';
      }
    } catch (e) {}
  </script>
  ```
- **Styling Rules**: Tokens in `globals.css` map `--bg-primary`, `--bg-secondary`, `--border-color`, and `--text-primary` to Tailwind CSS variables, ensuring all modals, popovers, dropdowns, and canvas inspectors adapt seamlessly without visual glitches.

---

## 7. Video Agent Pipeline

### 7.1 Workflow Lifecycle
1. **Trigger**: User inputs a creative prompt in the Dashboard prompt composer or modal.
2. **Configuration**: User selects presenter (Annie default), voice, visual style, aspect ratio (`16:9`, `9:16`, `1:1`), and duration preset (`15s`, `30s`, `60s`, `90s`, `2m`, `5m`, `10m`, or custom).
3. **Dispatch**: Request is dispatched to `POST /api/v1/workspaces/{workspace_id}/projects/generate` with `run_async=true`.
4. **Draft Creation**: The backend immediately inserts a `Project` (status: `draft`) and an initial `ProjectVersion` (rev: 1), enqueuing Celery task `heyzen.tasks.ai.generate_project` onto queue `cpu_media`.
5. **Real-time SSE Streaming**: The client navigates to the Video Agent workspace and subscribes to `/jobs/{job_id}/stream`.
6. **Task Execution**:
   - Stage 1: Script planning and scene count scaling via Qwen LLM adapter (`planning_scenes`).
   - Stage 2: Scene speech synthesis via Piper TTS (`synthesizing_audio`).
   - Stage 3: Background visual composition and talking avatar clipping (`generating_visuals`).
   - Stage 4: Version document assembly with OCC commit (`assembling_timeline`).
7. **Output Handover**: The client renders an interactive Artifact preview card. Clicking **Open in Studio** immediately transitions to the full multi-track studio editor with the generated project.

---

## 8. Interactive Studio Engine

### 8.1 Studio Document Specification ([ProjectDocumentV1](file:///D:/HeyGen/video-ai-tools/backend/app/schemas/project_document.py))
Every project is serialized as an authoritative JSON document containing:
- `schema_version`: Must strictly be integer `1`.
- `settings`: Aspect ratio, pixel width/height (e.g. 1920x1080), render framerate (30 fps), total duration, and subtitle burning configuration (`CaptionSettings`).
- `scenes`: Sequence cuts, each containing sequence order, duration, transition effect (`SceneTransition`), background fill (`SceneBackground`), talking avatar actor (`SceneAvatar`), speech narration (`SceneSpeech`), timestamped subtitle cues, and visual layers (`SceneLayer`).
- `audio_tracks`: Timeline tracks for background music and external audio assets with volume, start time, looping, and fade durations.
- `assets`: Manifest of referenced MinIO assets.

### 8.2 Component Hierarchy ([VidoAIStudio.tsx](file:///D:/HeyGen/video-ai-tools/src/components/studio/VidoAIStudio.tsx))
- **Canvas Viewport**: Central preview rendering layers scaled to canvas aspect ratio.
- **[CanvasTransformGizmo.tsx](file:///D:/HeyGen/video-ai-tools/src/components/studio/CanvasTransformGizmo.tsx)**: Direct manipulation overlay providing bounding box handles, rotation dial, and edge alignment snapping.
- **Timeline Area**:
  - [ElementsTimelineTrack.tsx](file:///D:/HeyGen/video-ai-tools/src/components/studio/ElementsTimelineTrack.tsx) (Shapes & stickers)
  - [TextTimelineTrack.tsx](file:///D:/HeyGen/video-ai-tools/src/components/studio/TextTimelineTrack.tsx) (Typography overlays)
  - [CaptionTimelineTrack.tsx](file:///D:/HeyGen/video-ai-tools/src/components/studio/CaptionTimelineTrack.tsx) (Subtitle word cues)
  - [MediaTimelineTrack.tsx](file:///D:/HeyGen/video-ai-tools/src/components/studio/MediaTimelineTrack.tsx) (B-roll & images)
  - [MusicTimelineTrack.tsx](file:///D:/HeyGen/video-ai-tools/src/components/studio/MusicTimelineTrack.tsx) (Background music)
- **Inspectors & Panels**:
  - [MultiSelectionInspector.tsx](file:///D:/HeyGen/video-ai-tools/src/components/studio/MultiSelectionInspector.tsx) (Group alignment & distribution)
  - [TextPanel.tsx](file:///D:/HeyGen/video-ai-tools/src/components/studio/TextPanel.tsx), [CaptionsPanel.tsx](file:///D:/HeyGen/video-ai-tools/src/components/studio/CaptionsPanel.tsx), [ElementsPanel.tsx](file:///D:/HeyGen/video-ai-tools/src/components/studio/ElementsPanel.tsx), [MediaLayerPanel.tsx](file:///D:/HeyGen/video-ai-tools/src/components/studio/MediaLayerPanel.tsx)

### 8.3 Timeline Manipulation Logic ([timelineUtils.ts](file:///D:/HeyGen/video-ai-tools/src/lib/timelineUtils.ts))
- **Trimming**: Left-trim and right-trim clamp durations to `MIN_CLIP_DURATION` (0.1s).
- **Splitting**: Divides a target layer at the current playhead position into two non-overlapping clips, adjusting source media offsets cleanly.
- **Snapping**: Snaps dragged clip boundaries to adjacent clip edges or the playhead when within a 0.1-second threshold.
- **Undo / Redo ([studioHistory.ts](file:///D:/HeyGen/video-ai-tools/src/lib/studioHistory.ts))**: Maintains bidirectional state stacks, preserving revision numbers and layer selections.

---

## 9. Studio Video Render Pipeline

```text
Studio "Generate Video" Click
├── 1. Client verifies no unsaved mutations remain in queue
├── 2. Client submits POST /api/v1/workspaces/{ws_id}/projects/{proj_id}/render
│      Payload: { expected_revision: N, resolution: "1080p", fps: 30, export_format: "mp4" }
├── 3. Backend ProjectRenderOrchestrator:
│      ├── Verifies project.revision == expected_revision (Rejects with 409 if stale)
│      ├── Executes validate_timeline() (Checks empty scenes, zero durations, audio links)
│      ├── Creates Job (type: "render_video", status: "queued", priority: 2)
│      ├── Updates project.status = "processing"
│      └── Enqueues task heyzen.tasks.media.render_video into Celery queue cpu_media
├── 4. Celery Worker executes _execute_render_video():
│      ├── Initializes isolated scratch MediaWorkspace
│      ├── Invokes TimelineCompositor.render_project()
│      ├── Downloads remote MinIO binary assets
│      ├── Renders per-scene video tracks via FFmpeg complex filtergraphs
│      ├── Concatenates scenes with xfade transitions
│      ├── Normalizes and mixes audio tracks (amix filter)
│      ├── Burns subtitle cues using font rasterizer
│      └── Encodes final H.264 MP4 and PNG poster thumbnail
├── 5. Uploads rendered MP4 and thumbnail to MinIO bucket heyzen-assets
├── 6. Inserts output Asset records and updates project.status = "ready"
└── 7. Publishes progress=100% to Redis Pub/Sub -> SSE pushes notification to Studio player
```

---

## 10. Media Pipeline & Compositor

### 10.1 Compositing Architecture ([compositor.py](file:///D:/HeyGen/video-ai-tools/backend/app/media/compositor.py))
- **Unified Layer Stacking**:
  - Background (Z-index: `-100`)
  - Media & vector shapes (Z-index: `0` to `50`)
  - Talking avatar video cut (Z-index: `60`)
  - Text typography overlays (Z-index: `70` to `90`)
  - Burned subtitles (Z-index: `100`)
- **Text Rasterization ([text_rasterizer.py](file:///D:/HeyGen/video-ai-tools/backend/app/media/text_rasterizer.py))**: Utilizes Pillow to render typography into high-resolution RGBA bitmaps with accurate kerning, letter spacing, and line wraps, rotating via OpenCV affine transforms before compositing.
- **Vector Shapes ([shapes.py](file:///D:/HeyGen/video-ai-tools/backend/app/media/shapes.py))**: Generates anti-aliased rectangles, rounded pill buttons, circles, stars, callout bubbles, and arrows directly into RGBA overlays.
- **Scene Transitions ([filters.py](file:///D:/HeyGen/video-ai-tools/backend/app/media/filters.py))**: Translates `fade`, `wipe`, `slide`, and `dissolve` transition directives into FFmpeg `xfade` filter syntax with exact offset timing.

---

## 11. AI Services & Neural Adapters

| Engine / Adapter | Library / Model | Primary Compute | Task Queues | Fallback Behavior | Verification Status |
|---|---|---|---|---|---|
| **ASR Speech-to-Text** | `faster-whisper` (Whisper-large-v3 / medium) | CPU / ONNX | `cpu_media` | Fallback to whisper-small or mock cues | **Verified** |
| **TTS Speech Synthesis** | `piper-tts` (ONNX voices) / `kokoro-onnx` | CPU | `cpu_media` | Deterministic synthetic WAV fallback | **Verified** |
| **Machine Translation** | `ctranslate2` (NLLB-200 / MarianMT) | CPU | `cpu_media` | Glossary term preservation + mock engine | **Verified** |
| **AI Scene Planning** | `Qwen2.5` / AI Planner | CPU / Mock | `cpu_media` | Deterministic rule-based scene generator | **Verified** |
| **Talking Avatar** | `MuseTalk` / `Wav2Lip` | CUDA 12.4 | `gpu_ai` | CPU Wav2Lip or static avatar image cut | **Verified** (Graceful fallback) |
| **Voice Cloning** | `OpenVoice v2` | CUDA / CPU | `cpu_media` / `gpu_ai` | Closest matching Piper voice profile | **Verified** |
| **Audio Enhancement** | `DeepFilterNet3` / SciPy spectral gating | CPU | `cpu_media` | SciPy denoise + volume normalization | **Verified** |
| **Scene Diffusion** | `Stable Diffusion v1.5` / SDXL | CUDA 12.4 | `gpu_ai` | Static curated b-roll asset fallback | **Verified** (Mock mode verified) |

---

## 12. Multi-Language Video Translation

1. **Audio Extraction**: FFmpeg extracts a 16kHz mono PCM stream from source video assets or URLs.
2. **Speech Recognition**: `faster-whisper` computes word-level timestamped transcription cues.
3. **Glossary Alignment**: Active Brand Glossary terminology rules for the target language are injected into the translation context.
4. **Neural Translation**: `CTranslate2` translates cues while locking protected terms.
5. **Voice Synthesis**: Target language scripts are synthesized via Piper TTS voice models.
6. **Project Forking**: The service constructs a localized `Project` fork or appends an immutable `ProjectVersion` to the current project.

---

## 13. Brand Systems & Terminology Glossaries

### 13.1 Schema & Models ([backend/app/models/brand.py](file:///D:/HeyGen/video-ai-tools/backend/app/models/brand.py))
- **`BrandKit`**: Stores workspace branding standards including `colors` (primary, secondary, accent, background), `typography` (heading, body, code fonts), `logo_asset_id` (MinIO asset pointer), and `is_default` flag.
- **`BrandGlossary`**: Terminology collections optionally bound to a `BrandKit`.
- **`BrandGlossaryRule`**: Individual translation constraints:
  - `source_term`: Term to match.
  - `target_term`: Mandatory translated replacement.
  - `rule_type`: `do_not_translate`, `mandatory_translation`, or `prefer_term`.
  - `case_sensitive`: Boolean enforcement flag.

---

## 14. Avatars, Digital Twins & Voices

### 14.1 Avatar Identity Models ([backend/app/models/avatar.py](file:///D:/HeyGen/video-ai-tools/backend/app/models/avatar.py))
- **Catalog**: Managed via `avatars` and `avatar_looks` tables. Supports `visibility = "public"` (preset platform actors) and `visibility = "workspace"` (custom digital twins).
- **Default Actor**: **Annie** is configured and seeded as the canonical default presenter with real preview and high-res source assets.
- **Looks**: Avatars support multiple outfits/looks (`AvatarLook`), defining custom bounding boxes, clothing styles, and lighting presets.

### 14.2 Speech Voices ([backend/app/models/voice.py](file:///D:/HeyGen/video-ai-tools/backend/app/models/voice.py))
- **Presets**: 6 canonical Piper neural voices seeded across genders and accents.
- **Instant Cloning**: Endpoint `/workspaces/{workspace_id}/voices/clone` ingests audio samples and computes speaker embeddings for real-time speech generation.
- **Audio Previews**: Audio samples are streamable directly from `/api/v1/voices/{voice_id}/preview`.

---

## 15. Projects & Version Control (OCC)

### 15.1 Concurrency Architecture
HeyZen utilizes **Optimistic Concurrency Control (OCC)** to prevent race conditions:
1. Every `Project` has an integer `revision` counter (1-indexed).
2. Every mutation endpoint requires `expected_revision`.
3. If `project.revision != expected_revision`, the server rejects the request with `HTTP 409 Conflict` (`CONCURRENCY_CONFLICT`).
4. On success, `revision` increments to `revision + 1`, and a new immutable `ProjectVersion` snapshot is saved.

---

## 16. Database Schema & Migrations

### 16.1 PostgreSQL Entity Schema Summary
- **Identity & Auth**: `users`, `user_credentials`, `user_sessions`
- **Multi-Tenancy**: `workspaces`, `workspace_members`, `workspace_invitations`
- **Project Structure**: `folders`, `projects`, `project_versions`
- **Media & Assets**: `assets`
- **Creative Library**: `avatars`, `avatar_looks`, `voices`, `templates`, `template_versions`, `brand_kits`, `brand_glossaries`, `brand_glossary_rules`
- **Workloads**: `jobs`, `job_events`
- **Developer Platform**: `api_keys`, `webhooks`, `webhook_deliveries`

### 16.2 Alembic Migration History
1. `0001_initial_user_schema`: Users, user credentials, and user sessions.
2. `0002_workspaces_and_auth`: Workspace multi-tenancy, memberships, invitations.
3. `0003_projects_folders_assets`: Projects, folders, project versions, asset storage.
4. `0004_creative_library`: Avatars, avatar looks, voices, templates, brand kits, glossaries.
5. `0005_jobs_and_task_pipeline`: Async jobs, job events audit ledger.
6. `0006_api_keys_and_webhooks`: Developer API keys, webhook subscriptions, delivery logs.

---

## 17. Storage Architecture (MinIO / S3)

### 17.1 Bucket Layout & Partitioning
All files reside in the bucket defined by `MINIO_BUCKET` (default: `heyzen-assets`). Object storage keys enforce workspace tenant isolation:

```text
heyzen-assets/
└── workspaces/{workspace_id}/
    ├── assets/{asset_id}/{filename}          # User uploaded media (images, audio, video)
    ├── avatars/{avatar_id}/looks/{look_id}/   # Avatar source photos & look previews
    ├── projects/{project_id}/renders/{job_id}/# Rendered MP4 videos & thumbnails
    └── audio_cache/{hash}.wav                 # Synthesized speech WAV clips
```

### 17.2 Direct Pre-Signed Upload Intent
1. Client requests upload intent: `POST /api/v1/workspaces/{workspace_id}/assets/upload-intent`.
2. Backend computes partitioned key and issues pre-signed S3 `PUT` URL (expires in 15 minutes).
3. Client streams binary directly to MinIO, bypassing the API gateway.
4. Client confirms completion: `POST /api/v1/workspaces/{workspace_id}/assets/{asset_id}/verify`.
5. Backend verifies object presence and records MIME type, size, and SHA-256 checksum.

---

## 18. API Reference Overview

The API comprises 122 validated FastAPI endpoints. For the exhaustive inventory including all parameters, request bodies, and response models, see the companion document:
👉 [HEYZEN_API_REFERENCE.md](file:///D:/HeyGen/video-ai-tools/docs/HEYZEN_API_REFERENCE.md)

### Route Categories Summary:
- **Health & Diagnostics**: `/health`, `/ready`, `/api/v1/health`
- **Authentication**: `/api/v1/auth/register`, `/login`, `/refresh`, `/logout`, `/me`
- **Workspaces & Members**: `/api/v1/workspaces`, `/members`, `/invitations`
- **Projects & Versions**: `/api/v1/workspaces/{id}/projects`, `/versions`, `/lock`, `/unlock`
- **Project Orchestration**: `/generate`, `/render`, `/validate`, `/synthesize-speech`, `/translate`, `/transcribe`, `/generate-avatar-video`, `/enhance-speech`
- **Assets**: `/upload-intent`, `/direct-upload`, `/verify`, `/stream`, `/download`
- **Creative Libraries**: `/avatars`, `/voices`, `/templates`, `/brand-kits`, `/brand-glossaries`
- **Jobs**: `/jobs`, `/jobs/{id}`, `/jobs/{id}/events`, `/jobs/{id}/cancel`, `/jobs/{id}/stream`
- **Developer Platform**: `/developer/api-keys`, `/developer/webhooks`, `/deliveries`, `/test`
- **Ask Rhys AI**: `/api/v1/ask-rhys/chat`

---

## 19. Asynchronous Jobs & SSE Streaming

### 19.1 Celery Queue Topology
```text
Exchange: heyzen (direct)
├── Queue: cpu_media    (Routing keys: heyzen.tasks.media.*, heyzen.tasks.ai.generate_project,
│                        heyzen.tasks.ai.translate_project, heyzen.tasks.ai.tts_synthesis,
│                        heyzen.tasks.ai.asr_transcription, heyzen.ping)
├── Queue: gpu_ai       (Routing keys: heyzen.tasks.ai.lip_sync, heyzen.tasks.ai.generate_scene_visual,
│                        heyzen.tasks.ai.avatar_train)
└── Queue: maintenance  (Routing keys: heyzen.tasks.maintenance.*)
```

### 19.2 Real-Time SSE Stream Flow
- Channel: `job:events:{job_id}` in Redis.
- Endpoint: `GET /api/v1/jobs/{job_id}/stream`.
- Header: `Content-Type: text/event-stream`, `X-Accel-Buffering: no`.
- Event Payload:
  ```json
  {
    "job_id": "uuid",
    "status": "running",
    "progress_percent": 65,
    "stage": "rendering_scenes",
    "message": "Compositing scene 2 of 4",
    "details": {}
  }
  ```

---

## 20. Developer Platform & Webhooks

### 20.1 Scoped Developer API Keys
- Key Format: `hz_live_<32_random_alphanumeric_chars>`.
- Storage: Public prefix stored in `prefix`; secret portion is hashed with SHA-256 and stored in `key_hash`. Plaintext secret is revealed only once upon creation.

### 20.2 Webhook Deliveries & Signatures
- Subscribed Events: `job.started`, `job.progress`, `job.succeeded`, `job.failed`, `project.created`, `project.rendered`.
- HMAC Signature: Each delivery includes header `X-HeyZen-Signature: sha256=<hex_digest>`, computed using HMAC SHA-256 over the raw JSON payload with the webhook secret.

---

## 21. Security Architecture & RBAC

1. **Passwords**: Hashed with Argon2id cryptographic parameters.
2. **JWT Secret**: Checked fail-closed during production startup; default development keys trigger fatal initialization errors.
3. **Workspace Isolation**: Database queries enforce workspace tenant boundaries; users cannot access resources across workspaces.
4. **RBAC Roles**:
   - `owner`: Full administrative control, billing, ownership transfer.
   - `admin`: Member invitations, developer keys, brand kits, project management.
   - `creator`: Project creation, editing, rendering, asset uploads.
   - `viewer`: Read-only access to projects and assets.
5. **CORS Policy**: Configured strictly with explicit origins. Wildcard `*` is prohibited when credentials are enabled.

---

## 22. Testing Framework & Verification Results

### 22.1 Frontend Tests
- **Runner**: Node test runner (`npx tsx --test src/lib/*.test.ts`).
- **Results**: **353 tests passing across 89 suites (100% pass rate, 2.1s duration)**.
- **Coverage**: OCC revision increments, canvas math, timeline split/trim, history undo/redo, multi-layer selection, theme toggling, auth persistence.

### 22.2 Backend Tests
- **Runner**: Pytest 9.1.1 on Python 3.13.7.
- **Results**: Core schemas, configuration fail-closed rules, duration planning, and layer locking tests pass synchronously. Live media tests require running Docker MinIO container on port 9000.

---

## 23. Playwright E2E Automation

- **Version**: `@playwright/test` `^1.63.0`
- **Channel Workaround**: Uses host Google Chrome binary (`channel: "chrome"` in `playwright.config.ts`), preventing large download failures.
- **Verified Specs**:
  - `tests/e2e/smoke.spec.ts`: Full UI smoke verification (Dashboard, Brand Systems, Projects, Video Agent, Studio, Generate button, resize handles, Fullscreen API, theme persistence).
  - `tests/e2e/auth-persistence.spec.ts`: Sign up -> Home redirect -> Reload -> Token refresh -> Logout -> Login.

---

## 24. Developer Setup & Local Orchestration

For detailed prerequisite installation and setup instructions on Windows, see the companion document:
👉 [HEYZEN_DEVELOPER_SETUP.md](file:///D:/HeyGen/video-ai-tools/docs/HEYZEN_DEVELOPER_SETUP.md)

### Quick Commands:
```powershell
# 1. Install frontend dependencies
npm install

# 2. Setup backend virtual environment
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cd ..

# 3. Start Docker infrastructure
docker compose up -d postgres redis minio

# 4. Run database migrations
cd backend
.\.venv\Scripts\alembic.exe upgrade head
cd ..

# 5. Launch FastAPI Backend
cd backend; uvicorn app.main:app --port 8000 --reload

# 6. Launch Celery Worker (Windows requires -P solo)
cd backend; celery -A app.workers.celery_app worker -Q cpu_media,maintenance -P solo

# 7. Launch Frontend Dev Server
npm run dev
```

---

## 25. Environment Variables Reference

See full table in [HEYZEN_DEVELOPER_SETUP.md](file:///D:/HeyGen/video-ai-tools/docs/HEYZEN_DEVELOPER_SETUP.md#3-environment-variables-configuration). Key variables:
- `DATABASE_URL`: `postgresql+asyncpg://...`
- `REDIS_URL`: `redis://127.0.0.1:6379/0`
- `MINIO_ENDPOINT`: `http://127.0.0.1:9000`
- `JWT_SECRET_KEY`: Random 32+ character string
- `NEXT_PUBLIC_API_URL`: `http://127.0.0.1:8000`

---

## 26. Production Deployment & Infrastructure

Multi-container architecture defined in `docker-compose.prod.yml`:
- `postgres`: PostgreSQL 16-alpine (2 CPU, 4GB RAM limit)
- `redis`: Redis 7-alpine (1 CPU, 1.5GB RAM limit, append-only)
- `minio`: MinIO S3 (1.5 CPU, 2GB RAM limit)
- `api`: FastAPI Application Gateway (4 CPU, 4GB RAM limit)
- `cpu-worker`: Celery CPU Worker (4 CPU, 6GB RAM limit)
- `nginx`: Nginx reverse proxy with SSL termination and unbuffered SSE streaming

---

## 27. Known Limitations & Technical Backlog

1. **GPU Dependencies**: Real-time neural talking avatar generation (`MuseTalk`) requires discrete NVIDIA GPU with 8GB+ VRAM. CPU hosts run in Wav2Lip or mock mode.
2. **MinIO Dependency for Tests**: Backend tests that upload binary assets require MinIO running on port 9000.
3. **Third-Party SSO**: OAuth2 integrations (Google/GitHub) are currently inactive in route handlers.
4. **Celery Windows Pool**: Windows development requires `-P solo` or `--pool=threads` due to OS fork limitations.

---

## 28. Troubleshooting Guide

Refer to [HEYZEN_DEVELOPER_SETUP.md § 7](file:///D:/HeyGen/video-ai-tools/docs/HEYZEN_DEVELOPER_SETUP.md#7-troubleshooting-guide) for comprehensive symptom, cause, check, and fix tables covering port conflicts, OCC collisions, Celery worker crashes, MinIO connection errors, and Playwright execution issues.

---

## 29. System Architecture Diagrams

Refer to [HEYZEN_ARCHITECTURE.md](file:///D:/HeyGen/video-ai-tools/docs/HEYZEN_ARCHITECTURE.md) for 8 high-resolution Mermaid diagrams covering:
- Overall System Topology
- Authentication & Session Lifecycle
- Video Agent Workflow
- Interactive Studio Document & OCC
- Video Render Pipeline
- Media Pipeline & Compositor Filtergraph
- Multilingual Translation Pipeline
- PostgreSQL Entity Relationship (ER) Diagram

---

## 30. Current Status Matrix

Refer to [HEYZEN_CURRENT_STATUS.md](file:///D:/HeyGen/video-ai-tools/docs/HEYZEN_CURRENT_STATUS.md) for the verified subsystem readiness matrix.

---

## 31. Change & Milestone History

Refer to [HEYZEN_CURRENT_STATUS.md § 3](file:///D:/HeyGen/video-ai-tools/docs/HEYZEN_CURRENT_STATUS.md#3-real-milestone--change-history) for historical milestones spanning Phase 1 to Phase 45.

---

## 32. Documentation Index & Companion Guides

- **Full REST API Reference**: [docs/HEYZEN_API_REFERENCE.md](file:///D:/HeyGen/video-ai-tools/docs/HEYZEN_API_REFERENCE.md)
- **Developer Setup & Operations**: [docs/HEYZEN_DEVELOPER_SETUP.md](file:///D:/HeyGen/video-ai-tools/docs/HEYZEN_DEVELOPER_SETUP.md)
- **System Architecture & Mermaid Diagrams**: [docs/HEYZEN_ARCHITECTURE.md](file:///D:/HeyGen/video-ai-tools/docs/HEYZEN_ARCHITECTURE.md)
- **Current Status Matrix & Audit**: [docs/HEYZEN_CURRENT_STATUS.md](file:///D:/HeyGen/video-ai-tools/docs/HEYZEN_CURRENT_STATUS.md)
