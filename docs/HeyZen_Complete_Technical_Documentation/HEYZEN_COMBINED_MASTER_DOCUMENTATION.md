# HeyZen — Unified Master Technical Documentation

> **Autonomous AI Video Creation & Interactive Studio Platform**  
> *Complete Consolidated Architecture, API Reference, Developer Setup, and Verification Specification*  
> *Repository*: `D:\HeyGen\video-ai-tools` | *Version*: `0.1.0`  

---

## Master Table of Contents

1. [Part I: System Overview & Technical Specification](#part-i-system-overview--technical-specification)
2. [Part II: Architecture & System Diagrams](#part-ii-architecture--system-diagrams)
3. [Part III: Complete REST API Reference](#part-iii-complete-rest-api-reference)
4. [Part IV: Developer Setup & Operations Guide](#part-iv-developer-setup--operations-guide)
5. [Part V: Implementation Status Matrix & Verification](#part-v-implementation-status-matrix--verification)

---



# Part I: System Overview & Technical Specification


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



---




# Part II: Architecture & System Diagrams


# HeyZen System Architecture & Technical Specifications

This document defines the architectural blueprints, data structures, state machines, and concurrency control models of the **HeyZen Autonomous AI Video Creation & Studio Platform**.

---

## 1. System Overview Architecture

HeyZen is structured as a decoupled multi-tier architecture uniting an interactive Next.js 16 frontend, an asynchronous FastAPI application gateway, Celery task workers, PostgreSQL 16 database, Redis 7 message broker/cache, and MinIO object storage.

```mermaid
flowchart TD
    subgraph Client Tier
        UI["Next.js 16 Web Application<br/>(React 19 / TypeScript / Tailwind CSS)"]
        BrowserStorage["Client Storage<br/>(Token in memory + localStorage fallback<br/>Theme in localStorage)"]
        UI <--> BrowserStorage
    end

    subgraph Edge & Ingress Tier
        Nginx["Nginx Reverse Proxy & SSL Termination<br/>(Port 80 / 443)"]
        UI -->|HTTP / REST / SSE| Nginx
    end

    subgraph Application Tier
        API["FastAPI Application Gateway<br/>(Uvicorn / Python 3.13 / Pydantic v2)"]
        Nginx -->|Proxy Pass /api/v1| API
    end

    subgraph Asynchronous Execution Tier
        Redis["Redis 7 Broker & Result Backend<br/>(Pub/Sub Channels / Task Queues)"]
        API -->|Enqueue Task / Publish Event| Redis
        
        CPUWorker["Celery Worker (cpu_media / maintenance)<br/>(FFmpeg / Compositor / Piper / Whisper / CTranslate2)"]
        GPUWorker["Celery Worker (gpu_ai)<br/>(CUDA 12.4 / MuseTalk / SD / OpenVoice)"]
        
        Redis <-->|Consume Jobs / Update Status| CPUWorker
        Redis <-->|Consume Jobs / Update Status| GPUWorker
    end

    subgraph Persistence & Storage Tier
        Postgres[("PostgreSQL 16 Database<br/>(SQLAlchemy 2.0 Async / Alembic)")]
        MinIO[("MinIO S3 Object Storage<br/>(heyzen-assets bucket)")]
        
        API <-->|Async SQL Sessions| Postgres
        CPUWorker <-->|Job State / Revision OCC| Postgres
        GPUWorker <-->|Job State / Version Updates| Postgres
        
        API -->|Pre-signed URLs| MinIO
        UI -->|Direct Binary Upload/Stream| MinIO
        CPUWorker <-->|Read Assets / Write Output MP4| MinIO
        GPUWorker <-->|Read Sources / Write Frames| MinIO
    end

    API -->|SSE Event Stream| UI
```

---

## 2. Authentication & Session Architecture

Authentication employs dual tokens: a short-lived access JWT in client memory and a persistent refresh token stored in an `HttpOnly`, `SameSite=Lax` cookie. To prevent token hijacking, refresh tokens are cryptographically hashed using SHA-256 before insertion into the `user_sessions` table.

```mermaid
sequenceDiagram
    autonumber
    actor User as User / Browser
    participant AuthCtx as React AuthContext
    participant API as FastAPI /api/v1/auth
    participant DB as PostgreSQL
    participant Session as user_sessions Table

    Note over User, Session: User Registration or Login
    User->>AuthCtx: Enter Email & Password
    AuthCtx->>API: POST /api/v1/auth/login
    API->>DB: Query user by lower(email)
    DB-->>API: Return User & UserCredential record
    API->>API: Verify password via Argon2id
    API->>API: Mint JWT Access Token (15 min exp)
    API->>API: Generate random Refresh Secret & compute SHA-256
    API->>Session: Insert session record (user_id, token_hash, expires_at)
    API-->>AuthCtx: Set-Cookie: hz_refresh_token=<secret>; HttpOnly; SameSite=Lax
    API-->>AuthCtx: 200 OK { tokens: { access_token }, user, workspace }
    AuthCtx->>AuthCtx: Store access_token in memory & localStorage
    AuthCtx-->>User: Redirect to "/" (Home Dashboard)

    Note over User, Session: Token Rotation & Session Restoration
    User->>AuthCtx: Page Reload (F5)
    AuthCtx->>API: GET /api/v1/auth/me (Bearer Token)
    alt Access Token Valid
        API-->>AuthCtx: 200 OK (User Profile & Workspaces)
    else Access Token Expired (401)
        AuthCtx->>API: POST /api/v1/auth/refresh (Cookie: hz_refresh_token)
        API->>API: Hash cookie secret via SHA-256
        API->>Session: Lookup active, unrevoked session by hash
        API->>Session: Mark current session revoked (Rotation)
        API->>API: Mint new Access Token & new Refresh Secret
        API->>Session: Insert new session record
        API-->>AuthCtx: Set-Cookie: hz_refresh_token=<new_secret>
        API-->>AuthCtx: 200 OK { tokens: { access_token } }
        AuthCtx->>API: Re-try GET /api/v1/auth/me
        API-->>AuthCtx: 200 OK (Restored)
    end
```

---

## 3. Video Agent End-to-End Workflow

The Video Agent decomposes high-level user prompts into structured, multi-scene video blueprints. It scales scenes dynamically based on requested duration without hardcoding fixed scene counts.

```mermaid
sequenceDiagram
    autonumber
    actor Creator as Content Creator
    participant Dashboard as VideoAgent Prompt Modal
    participant API as FastAPI Orchestration API
    participant DB as PostgreSQL
    participant Redis as Redis Broker
    participant Worker as Celery AI Worker
    participant Storage as MinIO Storage

    Creator->>Dashboard: Enter prompt, select Presenter (Annie), Voice, and Duration (e.g., 60s)
    Dashboard->>Dashboard: Calculate target scenes: 60s / ~15s = 4 scenes
    Dashboard->>API: POST /workspaces/{id}/projects/generate (run_async=true)
    API->>DB: Insert Project (status="draft")
    API->>DB: Insert ProjectVersion rev=1 with initial planned scenes
    API->>DB: Submit Job (job_type="generate_project", priority=5)
    API->>Redis: Enqueue heyzen.tasks.ai.generate_project (queue: cpu_media)
    API-->>Dashboard: 202 Accepted { job_id, project_id, version_id }
    
    Dashboard->>Dashboard: Switch view to Video Agent Workspace
    Dashboard->>API: GET /jobs/{job_id}/stream (SSE subscription)
    
    Worker->>Redis: Pop job execution payload
    Worker->>Worker: Stage 1: Decompose script with Qwen LLM / AI Planner
    Worker->>Redis: Publish job:events progress=25%, stage="planning_scenes"
    
    Worker->>Worker: Stage 2: Synthesize speech for each scene via Piper TTS
    Worker->>Storage: Upload generated scene WAV files
    Worker->>Redis: Publish job:events progress=50%, stage="synthesizing_audio"
    
    Worker->>Worker: Stage 3: Generate visual backgrounds & talking avatar cuts
    Worker->>Storage: Upload scene visuals & avatar clips
    Worker->>Redis: Publish job:events progress=85%, stage="assembling_timeline"
    
    Worker->>DB: Update ProjectVersion rev=1 document with asset references
    Worker->>DB: Mark Job status="succeeded", progress=100%
    Worker->>Redis: Publish job:events progress=100%, stage="completed"
    
    Redis-->>Dashboard: SSE Event: status="succeeded", project_id
    Dashboard->>Dashboard: Display generated Artifact card in Artifacts tab
    Creator->>Dashboard: Click "Open in Studio"
    Dashboard->>Dashboard: Navigate to Studio view with generated project
```

---

## 4. Interactive Studio Document & OCC Concurrency Model

HeyZen Studio implements **Optimistic Concurrency Control (OCC)** to ensure multiple collaborative sessions, autosave workers, and background render pipelines never silently overwrite project edits.

```mermaid
flowchart TD
    subgraph Studio Canvas Client
        DocState["Client Document State<br/>ProjectDocumentV1 (Scenes, Layers, Tracks)"]
        RevCounter["Local Revision Counter<br/>(expected_revision: N)"]
        MutationQueue["Mutation Queue & Undo/Redo Stacks<br/>(studioHistory.ts)"]
        DocState <--> MutationQueue
        MutationQueue --> RevCounter
    end

    subgraph Save & Mutation Execution
        SaveAction["Save Request<br/>{ expected_revision: N, document: {...} }"]
        RevCounter --> SaveAction
    end

    subgraph Server OCC Validation
        DBProj["PostgreSQL projects Record<br/>(current revision: R)"]
        OCCCheck{"Does R == expected_revision?"}
        SaveAction --> OCCCheck
        DBProj --> OCCCheck
        
        Success["Increment Project revision: R + 1<br/>Insert ProjectVersion rev: R + 1<br/>Update current_version_id"]
        Conflict["Reject with HTTP 409 Conflict<br/>code: CONCURRENCY_CONFLICT<br/>Return current server revision"]
        
        OCCCheck -->|Yes: R == N| Success
        OCCCheck -->|No: R != N| Conflict
    end

    Success -->|HTTP 201 Created| RevCounter
    Conflict -->|Prompt user: Reload / Merge| MutationQueue
```

---

## 5. Studio Video Rendering Pipeline

The video rendering pipeline validates timeline integrity, freezes an exact revision snapshot, and compiles multi-track media into broadcast-quality H.264 MP4 videos.

```mermaid
sequenceDiagram
    autonumber
    actor Editor as Studio Editor
    participant UI as Studio Workspace (VidoAIStudio)
    participant API as FastAPI Render Endpoint
    participant DB as PostgreSQL
    participant Redis as Redis Broker
    participant Celery as Celery Media Worker (cpu_media)
    participant Compositor as TimelineCompositor
    participant FFmpeg as FFmpeg / FFprobe Subprocesses
    participant S3 as MinIO S3 Storage

    Editor->>UI: Click "Generate Video"
    UI->>API: POST /workspaces/{id}/projects/{id}/render<br/>{ expected_revision: 4, resolution: "1080p", fps: 30 }
    
    API->>API: Validate project.revision == 4 (OCC check)
    API->>API: Run validate_timeline() (checks scene durations & audio cues)
    API->>DB: Submit Job (job_type="render_video", status="queued")
    API->>DB: Set project.status = "processing"
    API->>Redis: Enqueue heyzen.tasks.media.render_video
    API-->>UI: 202 Accepted { job_id, status: "queued" }
    
    UI->>API: GET /jobs/{job_id}/stream (SSE subscription)
    
    Celery->>Redis: Dequeue rendering job
    Celery->>DB: Mark Job status="running", stage="analyzing_timeline"
    Celery->>Compositor: render_project(document, workspace_id)
    
    Compositor->>S3: Download referenced scene assets (images, audio, video)
    Compositor->>Compositor: Rasterize text overlays & shape layers (Pillow / OpenCV)
    Compositor->>FFmpeg: Execute per-scene filtergraphs (scaling, padding, z-index layers)
    Compositor->>FFmpeg: Concatenate scenes with transitions (xfade: fade, wipe, slide)
    Compositor->>FFmpeg: Mix audio tracks (voiceover + background music with amix)
    Compositor->>FFmpeg: Burn subtitles/captions into final stream
    Compositor->>FFmpeg: Encode final MP4 (libx264, yuv420p, aac)
    
    Compositor->>S3: Upload output MP4 & poster thumbnail PNG
    Compositor->>DB: Create Asset records (output video & thumbnail)
    Celery->>DB: Mark Job status="succeeded", progress=100%
    Celery->>DB: Set project.status = "ready", thumbnail_asset_id
    Celery->>Redis: Publish job:events progress=100%, stage="completed"
    
    Redis-->>UI: SSE Event: status="succeeded", output_asset_url
    UI->>UI: Refresh Studio Video Player with playable rendered MP4
```

---

## 6. Media Pipeline & Layer Compositing Model

The HeyZen compositor renders scenes according to strict layer ordering and mathematical coordinate mapping:

```mermaid
flowchart TD
    subgraph Scene Media Ingestion
        BackgroundLayer["Background Layer<br/>(Solid Color, Gradient, Image Asset, or B-roll Video)"]
        AvatarLayer["Talking Avatar Video Layer<br/>(Neural Lip-Synced Video / Circular Mask)"]
        MediaLayers["Media Layers (Images / Video B-roll)<br/>(Z-Index, Scaling, Crop, Opacity)"]
        ShapeLayers["Vector Shape & Sticker Layers<br/>(Rectangles, Circles, Arrows, Icons)"]
        TextLayers["Text Typography Layers<br/>(Rasterized with Pillow, Rotated with OpenCV)"]
        CaptionLayer["Burned Subtitle Cues<br/>(Timestamped Word/Segment Highlighting)"]
    end

    subgraph Unified Stacking Order
        StackOrder["Cross-Type Layer Ordering<br/>1. Background (Z = -100)<br/>2. Media & Shapes (Z = 0 .. 50)<br/>3. Avatar Cut (Z = 60)<br/>4. Text Overlays (Z = 70 .. 90)<br/>5. Captions (Z = 100)"]
    end

    subgraph Audio Mixing Graph
        VoiceTrack["Speech Narration Audio Track<br/>(Synthesized WAV / Audio Enhancer)"]
        MusicTrack["Background Music Audio Track<br/>(Looping, Volume Attenuation, Fade-in/out)"]
        AmixFilter["FFmpeg amix Filtergraph<br/>(Volume Normalization & Broadcast Mastering)"]
        VoiceTrack --> AmixFilter
        MusicTrack --> AmixFilter
    end

    BackgroundLayer --> StackOrder
    AvatarLayer --> StackOrder
    MediaLayers --> StackOrder
    ShapeLayers --> StackOrder
    TextLayers --> StackOrder
    CaptionLayer --> StackOrder

    subgraph FFmpeg Final Assembly
        VideoFiltergraph["Complex Filtergraph<br/>scale2ref, overlay, xfade transitions"]
        StackOrder --> VideoFiltergraph
        
        FinalMux["MP4 Container Multiplexer<br/>Video: H.264 (libx264) | Audio: AAC (192kbps)"]
        VideoFiltergraph --> FinalMux
        AmixFilter --> FinalMux
    end

    FinalMux --> RenderedMP4["Final Rendered Video Asset<br/>(MinIO: heyzen-assets/workspaces/.../output.mp4)"]
```

---

## 7. Multi-Language Project Translation Pipeline

Video translation supports local file ingestion, URL intake (YouTube / Google Drive), and existing ProjectVersion documents. Translations enforce workspace **Brand Glossaries** so corporate terminology is never altered by neural machine translation.

```mermaid
flowchart LR
    SourceProject["Source Project / Video Asset"] --> AudioExtraction["FFmpeg Audio Extractor<br/>(16kHz Mono PCM)"]
    AudioExtraction --> WhisperASR["faster-whisper ASR<br/>(Word-level Timestamp Transcription)"]
    WhisperASR --> SourceCues["Structured Subtitle Cues<br/>[{start, end, text}]"]
    
    SourceCues --> Glossaries["Brand Glossaries<br/>(Case-sensitive Term Rules)"]
    Glossaries --> CTranslate2["CTranslate2 NMT Engine<br/>(Preserves protected terms)"]
    CTranslate2 --> TargetCues["Target Language Script & Cues"]
    
    TargetCues --> PiperTTS["Piper Neural TTS<br/>(Target Language Voice Model)"]
    PiperTTS --> TargetAudio["Localized Audio Track"]
    
    TargetAudio --> LipSync{"Lip-Sync Enabled?"}
    LipSync -->|Yes + GPU| MuseTalk["MuseTalk / Wav2Lip<br/>(Lip-synced Video Cut)"]
    LipSync -->|No / CPU Fallback| AudioReplaced["Timeline Audio Swap"]
    
    MuseTalk --> ForkVersion["Create Localized Project Fork<br/>or ProjectVersion Snapshot"]
    AudioReplaced --> ForkVersion
```

---

## 8. Database Entity Relationship (ER) Diagram

The PostgreSQL 16 relational database enforces multi-tenant boundary integrity, cascade rules, UUID primary keys, and timestamp tracking across all models:

```mermaid
erDiagram
    users ||--o{ user_credentials : "has"
    users ||--o{ user_sessions : "maintains"
    users ||--o{ workspace_members : "participates_as"
    users ||--o{ workspace_invitations : "creates"
    users ||--o{ projects : "creates"
    users ||--o{ assets : "uploads"
    users ||--o{ api_keys : "creates"
    users ||--o{ webhooks : "configures"

    workspaces ||--o{ workspace_members : "encloses"
    workspaces ||--o{ workspace_invitations : "issues"
    workspaces ||--o{ folders : "contains"
    workspaces ||--o{ projects : "owns"
    workspaces ||--o{ assets : "stores"
    workspaces ||--o{ avatars : "manages"
    workspaces ||--o{ voices : "registers"
    workspaces ||--o{ templates : "publishes"
    workspaces ||--o{ brand_kits : "defines"
    workspaces ||--o{ brand_glossaries : "enforces"
    workspaces ||--o{ jobs : "executes"
    workspaces ||--o{ api_keys : "scopes"
    workspaces ||--o{ webhooks : "dispatches"

    folders ||--o{ projects : "organizes"

    projects ||--o{ project_versions : "versions"
    projects ||--o| project_versions : "current_version"
    projects ||--o| assets : "thumbnail_asset"

    avatars ||--o{ avatar_looks : "has_looks"
    avatars ||--o| assets : "preview_asset"
    avatars ||--o| assets : "source_asset"

    voices ||--o| assets : "preview_asset"

    templates ||--o{ template_versions : "versions"
    templates ||--o| template_versions : "current_version"

    brand_kits ||--o| assets : "logo_asset"
    brand_kits ||--o{ brand_glossaries : "binds"
    brand_glossaries ||--o{ brand_glossary_rules : "contains"

    jobs ||--o{ job_events : "emits"
    webhooks ||--o{ webhook_deliveries : "logs"

    users {
        uuid id PK
        string email UK
        string display_name
        string status
        timestamp created_at
        timestamp updated_at
    }

    user_credentials {
        uuid user_id PK, FK
        string password_hash
        boolean is_active
    }

    user_sessions {
        uuid id PK
        uuid user_id FK
        string refresh_token_hash UK
        timestamp expires_at
        timestamp revoked_at
    }

    workspaces {
        uuid id PK
        string name
        string slug UK
        uuid owner_id FK
        string status
        timestamp deleted_at
    }

    workspace_members {
        uuid id PK
        uuid workspace_id FK
        uuid user_id FK
        string role
        string status
    }

    projects {
        uuid id PK
        uuid workspace_id FK
        uuid folder_id FK
        uuid created_by FK
        string title
        string project_type
        string status
        string aspect_ratio
        int width
        int height
        int fps
        int revision
        uuid current_version_id FK
        timestamp deleted_at
    }

    project_versions {
        uuid id PK
        uuid project_id FK
        int revision
        jsonb document
        uuid created_by FK
        string source
        timestamp created_at
    }

    assets {
        uuid id PK
        uuid workspace_id FK
        uuid created_by FK
        string storage_bucket
        string storage_key UK
        string mime_type
        bigint size_bytes
        string asset_type
        string status
        jsonb metadata
    }

    jobs {
        uuid id PK
        uuid workspace_id FK
        uuid created_by FK
        string job_type
        string status
        int priority
        int progress_percent
        string stage
        jsonb payload
        jsonb result
        string celery_task_id
    }

    brand_kits {
        uuid id PK
        uuid workspace_id FK
        string name
        jsonb colors
        jsonb typography
        boolean is_default
    }

    brand_glossaries {
        uuid id PK
        uuid workspace_id FK
        uuid brand_kit_id FK
        string name
    }

    brand_glossary_rules {
        uuid id PK
        uuid glossary_id FK
        string source_term
        string target_term
        string source_language
        string target_language
    }
```



---




# Part III: Complete REST API Reference


# HeyZen REST API Reference (Complete Inventory)

This document provides the definitive, comprehensive API reference for the HeyZen autonomous AI video backend.
All endpoints are generated directly from the live FastAPI OpenAPI specification (`/openapi.json`) and route inventory (`route_inventory.json`).

## Overview & Standards
- **Base URL**: `http://127.0.0.1:8000` (development) or configured production reverse proxy.
- **API Version Prefix**: `/api/v1` for versioned application endpoints; root level for health probes (`/health`, `/ready`).
- **Authentication**: HTTP Bearer JWT tokens in `Authorization: Bearer <token>` header, or HttpOnly cookie `hz_refresh_token` for rotation.
- **Workspace Multi-Tenancy**: All project, asset, avatar, voice, job, and developer operations require workspace context via `{workspace_id}` path parameter.
- **Optimistic Concurrency Control (OCC)**: Mutation endpoints on projects and versions enforce integer `expected_revision` to eliminate overwrite races.
- **Standard Response Wrappers**: Consistent JSON envelopes; errors follow `APIErrorResponse` with structured error codes.

### Global Error Response Schema (`APIErrorResponse`)
```json
{
  "error": {
    "code": "ERROR_CODE_STRING",
    "message": "Human readable message",
    "request_id": "req_xxxxxxxxxxxx",
    "details": {}
  }
}
```

### Summary Table
| Group | Endpoints | Authentication |
|---|---|---|
| [Health, Diagnostics & Probes](#health-diagnostics--probes) | 8 | Mixed |
| [Authentication & Session Management](#authentication--session-management) | 5 | Mixed |
| [Workspaces & Membership Management](#workspaces--membership-management) | 11 | Bearer / Protected |
| [Workspace Invitations](#workspace-invitations) | 4 | Bearer / Protected |
| [Folders](#folders) | 5 | Bearer / Protected |
| [Projects & Version Snapshots (OCC)](#projects--version-snapshots-occ) | 9 | Bearer / Protected |
| [Project Orchestration (Video Agent, Speech, Translation & Render)](#project-orchestration-video-agent-speech-translation--render) | 9 | Bearer / Protected |
| [Assets & Object Storage](#assets--object-storage) | 7 | Bearer / Protected |
| [Avatars & Digital Twin Looks](#avatars--digital-twin-looks) | 10 | Bearer / Protected |
| [Voices & Voice Cloning](#voices--voice-cloning) | 8 | Bearer / Protected |
| [Templates](#templates) | 9 | Bearer / Protected |
| [Brand Kits & Terminology Glossaries](#brand-kits--terminology-glossaries) | 17 | Bearer / Protected |
| [Jobs & Real-time SSE Streaming](#jobs--real-time-sse-streaming) | 6 | Bearer / Protected |
| [Developer API Keys & Webhooks](#developer-api-keys--webhooks) | 11 | Bearer / Protected |
| [Ask Rhys AI Copilot](#ask-rhys-ai-copilot) | 2 | Bearer / Protected |

## Health, Diagnostics & Probes
*Total Endpoints: 8*

### 1. `GET` /api/v1/health
**Summary**: Application Liveness Probe  
**Classification**: A. Public application API | **Auth Required**: No (Public)  
**Operation ID**: `get_health_api_v1_health_get`  

**Purpose**:
Returns HTTP 200 if the FastAPI application process is alive.

**Parameters**: None

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `HealthResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `status` (string) *(optional)*, default: `ok` — Liveness status indicator
- `app` (string) *(required)* — Application name
- `version` (string) *(required)* — Application version
  </details>

**Possible Error Codes**:
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 2. `GET` /api/v1/health/ai
**Summary**: AI Runtime & Capability Health Probe  
**Classification**: A. Public application API | **Auth Required**: No (Public)  
**Operation ID**: `get_ai_health_api_v1_health_ai_get`  

**Purpose**:
Reports host hardware detection, compute runtimes (CPU/GPU), and AI capability statuses.

**Parameters**: None

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `AIHealthResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `status` (string) *(required)* — Overall AI subsystem operational health
- `mode` (string) *(required)* — AI runtime mode: mock or real
- `hardware` (object) *(required)* — Host hardware specifications
- `runtimes` (object) *(required)* — Compute runtimes health states (cpu, gpu)
- `capabilities` (object) *(required)* — Per-capability status
- `gpu_worker` (object) *(optional)* — GPU worker and queue status
  </details>

**Possible Error Codes**:
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 3. `GET` /api/v1/metrics
**Summary**: Application Operational Metrics  
**Classification**: A. Public application API | **Auth Required**: No (Public)  
**Operation ID**: `get_metrics_api_v1_metrics_get`  

**Purpose**:
Returns runtime metrics, API request counts, job transitions, and subsystem errors.

**Parameters**: None

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `object`: Snapshot of application runtime metrics counters, latency histograms, and worker statistics.

**Possible Error Codes**:
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 4. `GET` /api/v1/ready
**Summary**: Application Readiness Probe  
**Classification**: A. Public application API | **Auth Required**: No (Public)  
**Operation ID**: `get_readiness_api_v1_ready_get`  

**Purpose**:
Verifies operational connectivity to PostgreSQL, Redis, and MinIO/S3 storage.

**Parameters**: None

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `ReadinessResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `status` (string) *(required)* — Readiness status: 'ready' or 'unhealthy'
- `checks` (object) *(required)* — Dependency health statuses: database, redis, storage
  </details>

**Possible Error Codes**:
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 5. `GET` /health
**Summary**: Application Liveness Probe  
**Classification**: A. Public application API | **Auth Required**: No (Public)  
**Operation ID**: `get_health_health_get`  

**Purpose**:
Returns HTTP 200 if the FastAPI application process is alive.

**Parameters**: None

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `HealthResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `status` (string) *(optional)*, default: `ok` — Liveness status indicator
- `app` (string) *(required)* — Application name
- `version` (string) *(required)* — Application version
  </details>

**Possible Error Codes**:
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 6. `GET` /health/ai
**Summary**: AI Runtime & Capability Health Probe  
**Classification**: A. Public application API | **Auth Required**: No (Public)  
**Operation ID**: `get_ai_health_health_ai_get`  

**Purpose**:
Reports host hardware detection, compute runtimes (CPU/GPU), and AI capability statuses.

**Parameters**: None

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `AIHealthResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `status` (string) *(required)* — Overall AI subsystem operational health
- `mode` (string) *(required)* — AI runtime mode: mock or real
- `hardware` (object) *(required)* — Host hardware specifications
- `runtimes` (object) *(required)* — Compute runtimes health states (cpu, gpu)
- `capabilities` (object) *(required)* — Per-capability status
- `gpu_worker` (object) *(optional)* — GPU worker and queue status
  </details>

**Possible Error Codes**:
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 7. `GET` /metrics
**Summary**: Application Operational Metrics  
**Classification**: A. Public application API | **Auth Required**: No (Public)  
**Operation ID**: `get_metrics_metrics_get`  

**Purpose**:
Returns runtime metrics, API request counts, job transitions, and subsystem errors.

**Parameters**: None

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `object`: Snapshot of application runtime metrics counters, latency histograms, and worker statistics.

**Possible Error Codes**:
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 8. `GET` /ready
**Summary**: Application Readiness Probe  
**Classification**: A. Public application API | **Auth Required**: No (Public)  
**Operation ID**: `get_readiness_ready_get`  

**Purpose**:
Verifies operational connectivity to PostgreSQL, Redis, and MinIO/S3 storage.

**Parameters**: None

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `ReadinessResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `status` (string) *(required)* — Readiness status: 'ready' or 'unhealthy'
- `checks` (object) *(required)* — Dependency health statuses: database, redis, storage
  </details>

**Possible Error Codes**:
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

## Authentication & Session Management
*Total Endpoints: 5*

### 9. `POST` /api/v1/auth/login
**Summary**: User Authentication  
**Classification**: A. Public application API | **Auth Required**: No (Public)  
**Operation ID**: `login_api_v1_auth_login_post`  

**Purpose**:
Authenticates credentials, starts a new session, and sets an HttpOnly refresh cookie.

**Parameters**: None

**Request Body** (`application/json`): `LoginRequest`
- `email` (string) *(required)* — Registered user email
- `password` (string) *(required)* — User password

**Responses**:
- **HTTP 200** — Model: `AuthResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `user` (object) *(required)*
  - `id` (string) *(required)*
  - `email` (string) *(required)*
  - `display_name` (string) *(required)*
  - `status` (string) *(required)*
  - `avatar_url` (object) *(optional)*
  - `created_at` (string) *(required)*
  - `updated_at` (string) *(required)*
  - `last_login_at` (object) *(optional)*
- `workspace` (object) *(optional)*
- `tokens` (object) *(required)*
  - `access_token` (string) *(required)*
  - `token_type` (string) *(optional)*, default: `bearer`
  - `expires_in_seconds` (integer) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 10. `POST` /api/v1/auth/logout
**Summary**: User Logout  
**Classification**: A. Public application API | **Auth Required**: No (Public)  
**Operation ID**: `logout_api_v1_auth_logout_post`  

**Purpose**:
Invalidates current refresh token session and clears the HttpOnly auth cookie.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `heyzen_refresh_token` | cookie | string | No |  |

**Request Body** (`application/json`): `custom`
- Raw binary payload or unstructured object.

**Responses**:
- **HTTP 200** — Model: `LogoutResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `status` (string) *(optional)*, default: `ok` — Status confirmation
- `message` (string) *(optional)*, default: `Logged out successfully.` — Logout message
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 11. `GET` /api/v1/auth/me
**Summary**: Current Authenticated User Profile  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `get_me_api_v1_auth_me_get`  

**Purpose**:
Returns the profile and workspace memberships of the authenticated user.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `token` | query | string | No | Short-lived access token for browser EventSource / SSE |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `UserWithWorkspacesResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `user` (object) *(required)*
  - `id` (string) *(required)*
  - `email` (string) *(required)*
  - `display_name` (string) *(required)*
  - `status` (string) *(required)*
  - `avatar_url` (object) *(optional)*
  - `created_at` (string) *(required)*
  - `updated_at` (string) *(required)*
  - `last_login_at` (object) *(optional)*
- `workspaces` (array) *(required)*
  - *Item properties:*
    - `id` (string) *(required)*
    - `name` (string) *(required)*
    - `slug` (string) *(required)*
    - `role` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 12. `POST` /api/v1/auth/refresh
**Summary**: Rotate Session & Access Token  
**Classification**: A. Public application API | **Auth Required**: No (Public)  
**Operation ID**: `refresh_tokens_api_v1_auth_refresh_post`  

**Purpose**:
Rotates the refresh token (session rotation) and issues a new access token.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `heyzen_refresh_token` | cookie | string | No |  |

**Request Body** (`application/json`): `custom`
- Raw binary payload or unstructured object.

**Responses**:
- **HTTP 200** — Model: `AuthResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `user` (object) *(required)*
  - `id` (string) *(required)*
  - `email` (string) *(required)*
  - `display_name` (string) *(required)*
  - `status` (string) *(required)*
  - `avatar_url` (object) *(optional)*
  - `created_at` (string) *(required)*
  - `updated_at` (string) *(required)*
  - `last_login_at` (object) *(optional)*
- `workspace` (object) *(optional)*
- `tokens` (object) *(required)*
  - `access_token` (string) *(required)*
  - `token_type` (string) *(optional)*, default: `bearer`
  - `expires_in_seconds` (integer) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 13. `POST` /api/v1/auth/signup
**Summary**: User Registration  
**Classification**: A. Public application API | **Auth Required**: No (Public)  
**Operation ID**: `signup_api_v1_auth_signup_post`  

**Purpose**:
Atomically registers a new user, creates a personal workspace, and sets an HttpOnly refresh cookie.

**Parameters**: None

**Request Body** (`application/json`): `SignupRequest`
- `email` (string) *(required)* — Valid user email address
- `display_name` (string) *(required)* — User's display name
- `password` (string) *(required)* — Password (minimum 8 characters)

**Responses**:
- **HTTP 201** — Model: `AuthResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `user` (object) *(required)*
  - `id` (string) *(required)*
  - `email` (string) *(required)*
  - `display_name` (string) *(required)*
  - `status` (string) *(required)*
  - `avatar_url` (object) *(optional)*
  - `created_at` (string) *(required)*
  - `updated_at` (string) *(required)*
  - `last_login_at` (object) *(optional)*
- `workspace` (object) *(optional)*
- `tokens` (object) *(required)*
  - `access_token` (string) *(required)*
  - `token_type` (string) *(optional)*, default: `bearer`
  - `expires_in_seconds` (integer) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

## Workspaces & Membership Management
*Total Endpoints: 11*

### 14. `GET` /api/v1/workspaces
**Summary**: List User Workspaces  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `list_workspaces_api_v1_workspaces_get`  

**Purpose**:
Lists all workspaces the authenticated user belongs to.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `token` | query | string | No | Short-lived access token for browser EventSource / SSE |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `array`: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 15. `POST` /api/v1/workspaces
**Summary**: Create Workspace  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `create_workspace_api_v1_workspaces_post`  

**Purpose**:
Creates a new workspace tenant and assigns the authenticated user as Owner.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `token` | query | string | No | Short-lived access token for browser EventSource / SSE |

**Request Body** (`application/json`): `WorkspaceCreate`
- `name` (string) *(required)* — Organization or workspace title

**Responses**:
- **HTTP 201** — Model: `WorkspaceResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `name` (string) *(required)*
- `slug` (string) *(required)*
- `owner_id` (string) *(required)*
- `status` (string) *(required)*
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
- `role` (object) *(optional)* — Caller's role in this workspace
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 16. `DELETE` /api/v1/workspaces/{workspace_id}
**Summary**: Soft-Delete Workspace  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `delete_workspace_api_v1_workspaces__workspace_id__delete`  

**Purpose**:
Marks workspace as deleted. Requires 'workspace.delete' (Owner only).

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 204**: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 17. `GET` /api/v1/workspaces/{workspace_id}
**Summary**: Get Workspace Details  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `get_workspace_api_v1_workspaces__workspace_id__get`  

**Purpose**:
Fetch details of a specific workspace. Caller must be an active member.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `WorkspaceResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `name` (string) *(required)*
- `slug` (string) *(required)*
- `owner_id` (string) *(required)*
- `status` (string) *(required)*
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
- `role` (object) *(optional)* — Caller's role in this workspace
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 18. `PATCH` /api/v1/workspaces/{workspace_id}
**Summary**: Update Workspace  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `update_workspace_api_v1_workspaces__workspace_id__patch`  

**Purpose**:
Update workspace title or status. Requires 'workspace.update' permission.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `WorkspaceUpdate`
- `name` (object) *(optional)*
- `status` (object) *(optional)* — Workspace status: active, suspended

**Responses**:
- **HTTP 200** — Model: `WorkspaceResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `name` (string) *(required)*
- `slug` (string) *(required)*
- `owner_id` (string) *(required)*
- `status` (string) *(required)*
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
- `role` (object) *(optional)* — Caller's role in this workspace
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 19. `GET` /api/v1/workspaces/{workspace_id}/members
**Summary**: List Workspace Members  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `list_members_api_v1_workspaces__workspace_id__members_get`  

**Purpose**:
List all members of the workspace. Requires 'workspace.read' permission.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `array`: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 20. `DELETE` /api/v1/workspaces/{workspace_id}/members/{user_id}
**Summary**: Remove Workspace Member  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `remove_member_api_v1_workspaces__workspace_id__members__user_id__delete`  

**Purpose**:
Removes a member from the workspace. Owner cannot be removed.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `user_id` | path | string | Yes | Target Workspace Member User UUID |
| `token` | query | string | No | Short-lived access token for browser EventSource / SSE |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 204**: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 21. `PATCH` /api/v1/workspaces/{workspace_id}/members/{user_id}
**Summary**: Update Member Role  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `update_member_role_api_v1_workspaces__workspace_id__members__user_id__patch`  

**Purpose**:
Update a member's role. Requires 'workspace.manage_members' permission.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `user_id` | path | string | Yes | Target Workspace Member User UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Short-lived access token for browser EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `WorkspaceMemberUpdate`
- `role` (string) *(required)* — Supported workspace collaboration roles in descending hierarchy order.

**Responses**:
- **HTTP 200** — Model: `WorkspaceMemberResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `workspace_id` (string) *(required)*
- `user_id` (string) *(required)*
- `email` (string) *(required)*
- `display_name` (string) *(required)*
- `avatar_url` (object) *(optional)*
- `role` (string) *(required)*
- `status` (string) *(required)*
- `joined_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 22. `GET` /api/v1/workspaces/{workspace_id}/onboarding
**Summary**: Get Onboarding Setup Status  
**Classification**: Application API | **Auth Required**: Protected (HTTPBearer)  
**Operation ID**: `get_onboarding_status_api_v1_workspaces__workspace_id__onboarding_get`  

**Purpose**:
Retrieves the 4-step account setup progress derived from real workspace entity state.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `OnboardingStatusResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `step_1_digital_twin` (boolean) *(required)* — Whether Digital Twin has been created
- `step_2_voice` (boolean) *(required)* — Whether Voice has been polished/cloned
- `step_3_look` (boolean) *(required)* — Whether a Look has been created
- `step_4_video` (boolean) *(required)* — Whether first video project has been created
- `completed_steps` (array) *(optional)* — Array of completed step numbers (1-4)
- `completed_count` (integer) *(required)* — Number of completed steps (0-4)
- `total_steps` (integer) *(optional)*, default: `4` — Total number of setup steps
- `is_step_2_unlocked` (boolean) *(required)* — Whether Step 2 is unlocked (requires Step 1)
- `is_step_3_unlocked` (boolean) *(required)* — Whether Step 3 is unlocked (requires Step 1)
- `is_step_4_unlocked` (boolean) *(required)* — Whether Step 4 is unlocked (requires Step 2 or 3)
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 23. `POST` /api/v1/workspaces/{workspace_id}/onboarding/complete-step
**Summary**: Complete Onboarding Step  
**Classification**: Application API | **Auth Required**: Protected (HTTPBearer)  
**Operation ID**: `complete_onboarding_step_api_v1_workspaces__workspace_id__onboarding_complete_step_post`  

**Purpose**:
Explicitly completes an onboarding step and ensures required workspace entity records exist.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Short-lived access token for browser EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `None`
- `step` (integer) *(required)* — Step number (1-4) to complete

**Responses**:
- **HTTP 200** — Model: `OnboardingStatusResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `step_1_digital_twin` (boolean) *(required)* — Whether Digital Twin has been created
- `step_2_voice` (boolean) *(required)* — Whether Voice has been polished/cloned
- `step_3_look` (boolean) *(required)* — Whether a Look has been created
- `step_4_video` (boolean) *(required)* — Whether first video project has been created
- `completed_steps` (array) *(optional)* — Array of completed step numbers (1-4)
- `completed_count` (integer) *(required)* — Number of completed steps (0-4)
- `total_steps` (integer) *(optional)*, default: `4` — Total number of setup steps
- `is_step_2_unlocked` (boolean) *(required)* — Whether Step 2 is unlocked (requires Step 1)
- `is_step_3_unlocked` (boolean) *(required)* — Whether Step 3 is unlocked (requires Step 1)
- `is_step_4_unlocked` (boolean) *(required)* — Whether Step 4 is unlocked (requires Step 2 or 3)
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 24. `POST` /api/v1/workspaces/{workspace_id}/transfer-ownership
**Summary**: Transfer Workspace Ownership  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `transfer_ownership_api_v1_workspaces__workspace_id__transfer_ownership_post`  

**Purpose**:
Atomically transfers workspace ownership to another active member. Owner only.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Short-lived access token for browser EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `TransferOwnershipRequest`
- `target_user_id` (string) *(required)* — Target member user ID to receive workspace ownership

**Responses**:
- **HTTP 200** — Model: `WorkspaceResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `name` (string) *(required)*
- `slug` (string) *(required)*
- `owner_id` (string) *(required)*
- `status` (string) *(required)*
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
- `role` (object) *(optional)* — Caller's role in this workspace
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

## Workspace Invitations
*Total Endpoints: 4*

### 25. `POST` /api/v1/invitations/{token}/accept
**Summary**: Accept Workspace Invitation  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `accept_invitation_api_v1_invitations__token__accept_post`  

**Purpose**:
Redeems an invitation token and adds the authenticated user to the workspace with the invited role.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `token` | path | string | Yes | Invitation secret token |
| `token` | query | string | No | Short-lived access token for browser EventSource / SSE |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `InvitationAcceptResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `workspace` (object) *(required)*
  - `id` (string) *(required)*
  - `name` (string) *(required)*
  - `slug` (string) *(required)*
  - `owner_id` (string) *(required)*
  - `status` (string) *(required)*
  - `created_at` (string) *(required)*
  - `updated_at` (string) *(required)*
  - `role` (object) *(optional)* — Caller's role in this workspace
- `role` (string) *(required)*
- `message` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 26. `GET` /api/v1/workspaces/{workspace_id}/invitations
**Summary**: List Pending Invitations  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `list_invitations_api_v1_workspaces__workspace_id__invitations_get`  

**Purpose**:
Lists pending invitations. Requires 'workspace.manage_members'.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `array`: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 27. `POST` /api/v1/workspaces/{workspace_id}/invitations
**Summary**: Invite Member  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `create_invitation_api_v1_workspaces__workspace_id__invitations_post`  

**Purpose**:
Creates an invitation. Returns token only in development/testing mode.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Short-lived access token for browser EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `WorkspaceInvitationCreate`
- `email` (string) *(required)* — Invitee's email address
- `role` (string) *(optional)*, default: `creator` — Supported workspace collaboration roles in descending hierarchy order.

**Responses**:
- **HTTP 201** — Model: `WorkspaceInvitationResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `workspace_id` (string) *(required)*
- `email` (string) *(required)*
- `role` (string) *(required)*
- `status` (string) *(required)*
- `expires_at` (string) *(required)*
- `created_at` (string) *(required)*
- `invitation_token` (object) *(optional)* — Plaintext redemption token (Returned ONLY in development/testing)
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 28. `POST` /api/v1/workspaces/{workspace_id}/invitations/{invitation_id}/revoke
**Summary**: Revoke Invitation  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `revoke_invitation_api_v1_workspaces__workspace_id__invitations__invitation_id__revoke_post`  

**Purpose**:
Revokes an unaccepted invitation. Requires 'workspace.manage_members'.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `invitation_id` | path | string | Yes | Target Invitation UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `WorkspaceRevokeResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `status` (string) *(optional)*, default: `ok` — Revocation status
- `message` (string) *(optional)*, default: `Invitation revoked successfully.` — Status message
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

## Folders
*Total Endpoints: 5*

### 29. `GET` /api/v1/workspaces/{workspace_id}/folders
**Summary**: List Folders  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `list_folders_api_v1_workspaces__workspace_id__folders_get`  

**Purpose**:
Lists active folders in the workspace, optionally filtering by parent folder.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `parent_id` | query | string | No | Filter by parent folder ID |
| `filter_parent` | query | boolean | No | Whether to filter explicitly by parent_id |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `array`: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 30. `POST` /api/v1/workspaces/{workspace_id}/folders
**Summary**: Create Folder  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `create_folder_api_v1_workspaces__workspace_id__folders_post`  

**Purpose**:
Creates a new organizational folder within the active workspace.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Short-lived access token for browser EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `FolderCreate`
- `name` (string) *(required)* — Folder display name
- `parent_id` (object) *(optional)* — Optional parent folder UUID

**Responses**:
- **HTTP 201** — Model: `FolderResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `workspace_id` (string) *(required)*
- `parent_id` (object) *(optional)*
- `name` (string) *(required)*
- `created_by` (string) *(required)*
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 31. `DELETE` /api/v1/workspaces/{workspace_id}/folders/{folder_id}
**Summary**: Delete Folder  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `delete_folder_api_v1_workspaces__workspace_id__folders__folder_id__delete`  

**Purpose**:
Soft-deletes an empty folder. Fails with 409 if folder contains children or projects.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `folder_id` | path | string | Yes | Target Folder UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 204**: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 32. `GET` /api/v1/workspaces/{workspace_id}/folders/{folder_id}
**Summary**: Get Folder  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `get_folder_api_v1_workspaces__workspace_id__folders__folder_id__get`  

**Purpose**:
Fetches details of a specific workspace folder.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `folder_id` | path | string | Yes | Target Folder UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `FolderResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `workspace_id` (string) *(required)*
- `parent_id` (object) *(optional)*
- `name` (string) *(required)*
- `created_by` (string) *(required)*
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 33. `PATCH` /api/v1/workspaces/{workspace_id}/folders/{folder_id}
**Summary**: Update Folder  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `update_folder_api_v1_workspaces__workspace_id__folders__folder_id__patch`  

**Purpose**:
Renames or moves a folder to a new parent location.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `folder_id` | path | string | Yes | Target Folder UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `FolderUpdate`
- `name` (object) *(optional)* — Updated name
- `parent_id` (object) *(optional)* — New parent folder UUID for moves

**Responses**:
- **HTTP 200** — Model: `FolderResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `workspace_id` (string) *(required)*
- `parent_id` (object) *(optional)*
- `name` (string) *(required)*
- `created_by` (string) *(required)*
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

## Projects & Version Snapshots (OCC)
*Total Endpoints: 9*

### 34. `GET` /api/v1/workspaces/{workspace_id}/projects
**Summary**: List Projects  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `list_projects_api_v1_workspaces__workspace_id__projects_get`  

**Purpose**:
Lists active projects in the workspace with optional folder, status, and title filtering.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `folder_id` | query | string | No | Filter by folder ID |
| `filter_folder` | query | boolean | No | Whether to filter explicitly by folder_id |
| `status` | query | string | No | Filter by status: draft, processing, ready, archived |
| `search` | query | string | No | Search by title keyword |
| `limit` | query | integer | No |  |
| `offset` | query | integer | No |  |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `array`: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 35. `POST` /api/v1/workspaces/{workspace_id}/projects
**Summary**: Create Project  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `create_project_api_v1_workspaces__workspace_id__projects_post`  

**Purpose**:
Initializes a new video project with default ProjectDocumentV1 at revision 1.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Short-lived access token for browser EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `ProjectCreate`
- `title` (string) *(required)* — Project title
- `folder_id` (object) *(optional)* — Optional target folder UUID
- `project_type` (string) *(optional)*, default: `standard` — standard, avatar_video, agent, translation, template_based
- `aspect_ratio` (string) *(optional)*, default: `16:9` — 16:9, 9:16, 1:1
- `width` (integer) *(optional)*, default: `1920`
- `height` (integer) *(optional)*, default: `1080`
- `fps` (integer) *(optional)*, default: `30`

**Responses**:
- **HTTP 201** — Model: `ProjectResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `workspace_id` (string) *(required)*
- `folder_id` (object) *(optional)*
- `created_by` (string) *(required)*
- `title` (string) *(required)*
- `project_type` (string) *(required)*
- `status` (string) *(required)*
- `aspect_ratio` (string) *(required)*
- `width` (object) *(optional)*
- `height` (object) *(optional)*
- `fps` (object) *(optional)*
- `duration_ms` (object) *(optional)*
- `thumbnail_asset_id` (object) *(optional)*
- `current_version_id` (object) *(optional)*
- `revision` (integer) *(required)*
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 36. `DELETE` /api/v1/workspaces/{workspace_id}/projects/{project_id}
**Summary**: Delete Project  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `delete_project_api_v1_workspaces__workspace_id__projects__project_id__delete`  

**Purpose**:
Soft-deletes a project and removes it from normal query results.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `project_id` | path | string | Yes | Target Project UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 204**: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 404`: `PROJECT_NOT_FOUND` (target project does not exist)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 37. `GET` /api/v1/workspaces/{workspace_id}/projects/{project_id}
**Summary**: Get Project  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `get_project_api_v1_workspaces__workspace_id__projects__project_id__get`  

**Purpose**:
Fetches metadata summary for a single project.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `project_id` | path | string | Yes | Target Project UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `ProjectResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `workspace_id` (string) *(required)*
- `folder_id` (object) *(optional)*
- `created_by` (string) *(required)*
- `title` (string) *(required)*
- `project_type` (string) *(required)*
- `status` (string) *(required)*
- `aspect_ratio` (string) *(required)*
- `width` (object) *(optional)*
- `height` (object) *(optional)*
- `fps` (object) *(optional)*
- `duration_ms` (object) *(optional)*
- `thumbnail_asset_id` (object) *(optional)*
- `current_version_id` (object) *(optional)*
- `revision` (integer) *(required)*
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 404`: `PROJECT_NOT_FOUND` (target project does not exist)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 38. `PATCH` /api/v1/workspaces/{workspace_id}/projects/{project_id}
**Summary**: Update Project Metadata  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `update_project_api_v1_workspaces__workspace_id__projects__project_id__patch`  

**Purpose**:
Updates project title, folder assignment, status, or thumbnail poster.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `project_id` | path | string | Yes | Target Project UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `ProjectUpdate`
- `title` (object) *(optional)*
- `folder_id` (object) *(optional)*
- `status` (object) *(optional)* — draft, processing, ready, archived
- `aspect_ratio` (object) *(optional)*
- `thumbnail_asset_id` (object) *(optional)*

**Responses**:
- **HTTP 200** — Model: `ProjectResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `workspace_id` (string) *(required)*
- `folder_id` (object) *(optional)*
- `created_by` (string) *(required)*
- `title` (string) *(required)*
- `project_type` (string) *(required)*
- `status` (string) *(required)*
- `aspect_ratio` (string) *(required)*
- `width` (object) *(optional)*
- `height` (object) *(optional)*
- `fps` (object) *(optional)*
- `duration_ms` (object) *(optional)*
- `thumbnail_asset_id` (object) *(optional)*
- `current_version_id` (object) *(optional)*
- `revision` (integer) *(required)*
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 404`: `PROJECT_NOT_FOUND` (target project does not exist)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 39. `GET` /api/v1/workspaces/{workspace_id}/projects/{project_id}/versions
**Summary**: List Project Versions  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `list_project_versions_api_v1_workspaces__workspace_id__projects__project_id__versions_get`  

**Purpose**:
Lists chronological version history snapshots for a project.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `project_id` | path | string | Yes | Target Project UUID |
| `limit` | query | integer | No |  |
| `offset` | query | integer | No |  |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `array`: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 404`: `PROJECT_NOT_FOUND` (target project does not exist)
- `HTTP 409`: `CONCURRENCY_CONFLICT` (revision mismatch under OCC)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 40. `POST` /api/v1/workspaces/{workspace_id}/projects/{project_id}/versions
**Summary**: Save New Project Version (Optimistic Concurrency)  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `create_project_version_api_v1_workspaces__workspace_id__projects__project_id__versions_post`  

**Purpose**:
Saves a new immutable project version. Fails with 409 Conflict if expected_revision does not match.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `project_id` | path | string | Yes | Target Project UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Short-lived access token for browser EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `CreateProjectVersionRequest`
- `expected_revision` (integer) *(required)* — Current revision caller expects to update
- `document` (object) *(required)* — Canonical HeyZen Project Document specification (Version 1).
  - `schema_version` (integer) *(optional)*, default: `1` — Schema version tag (must be 1 for V1)
  - `settings` (object) *(optional)* — Core timeline and render canvas configuration.
    - `aspect_ratio` (string) *(optional)*, default: `16:9` — Canvas ratio: 16:9, 9:16, 1:1, etc.
    - `width` (integer) *(optional)*, default: `1920` — Pixel width
    - `height` (integer) *(optional)*, default: `1080` — Pixel height
    - `fps` (integer) *(optional)*, default: `30` — Render framerate
    - `total_duration` (number) *(optional)*, default: `0.0` — Computed runtime in seconds
    - `captions` (object) *(optional)* — Project-level caption toggle and styling configuration.
      - `enabled` (boolean) *(optional)*, default: `True` — Whether subtitles/captions are displayed and burned
      - `style` (object) *(optional)* — Visual typography and placement styling for burned/displayed subtitles.
  - `scenes` (array) *(optional)*
    - *Item properties:*
      - `id` (string) *(required)* — Unique scene UUID/string
      - `sequence` (integer) *(required)* — 1-indexed sequence order
      - `duration` (number) *(optional)*, default: `5.0` — Scene length in seconds
      - `transition` (object) *(optional)*
      - `camera_motion` (object) *(optional)*, default: `static` — Camera movement: static, slow_zoom_in, slow_zoom_out, pan_left, pan_right, presenter_closeup, presenter_medium, presenter_wide
      - `background` (object) *(optional)*
      - `avatar` (object) *(optional)*
      - `speech` (object) *(optional)*
      - `layers` (array) *(optional)*
        - *Item properties:*

      - `subtitles` (array) *(optional)* — Timestamped speech transcription cues: [{'id': int, 'start': float, 'end': float, 'text': str, 'words': [...]}]
  - `audio_tracks` (array) *(optional)*
    - *Item properties:*
      - `id` (string) *(required)* — Unique track ID
      - `asset_id` (object) *(optional)* — Reference to assets.id in object storage
      - `name` (string) *(optional)*, default: `Audio Track`
      - `volume` (number) *(optional)*, default: `1.0`
      - `start_time` (number) *(optional)*, default: `0.0`
      - `duration` (object) *(optional)*
      - `fade_in_duration` (number) *(optional)*, default: `0.0`
      - `fade_out_duration` (number) *(optional)*, default: `0.0`
      - `loop` (boolean) *(optional)*, default: `False`
      - `muted` (boolean) *(optional)*, default: `False` — Whether audio track is muted
  - `assets` (array) *(optional)*
    - *Item properties:*
      - `asset_id` (string) *(required)* — UUID string of the asset
      - `asset_type` (string) *(required)* — image, video, audio, font, other
      - `storage_key` (object) *(optional)*
  - `metadata` (object) *(optional)*
- `source` (object) *(optional)*, default: `manual` — manual, autosave, template, agent, import

**Responses**:
- **HTTP 201** — Model: `ProjectVersionResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `project_id` (string) *(required)*
- `revision` (integer) *(required)*
- `document` (object) *(required)* — Project document snapshot
- `source` (string) *(required)*
- `created_by` (string) *(required)*
- `created_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 404`: `PROJECT_NOT_FOUND` (target project does not exist)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 409`: `CONCURRENCY_CONFLICT` (revision mismatch under OCC)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 41. `GET` /api/v1/workspaces/{workspace_id}/projects/{project_id}/versions/latest
**Summary**: Get Latest Project Version Snapshot  
**Classification**: Application API | **Auth Required**: Protected (HTTPBearer)  
**Operation ID**: `get_latest_project_version_api_v1_workspaces__workspace_id__projects__project_id__versions_latest_get`  

**Purpose**:
Fetches full ProjectDocument JSON for the latest project version snapshot.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `project_id` | path | string | Yes | Target Project UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `ProjectVersionResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `project_id` (string) *(required)*
- `revision` (integer) *(required)*
- `document` (object) *(required)* — Project document snapshot
- `source` (string) *(required)*
- `created_by` (string) *(required)*
- `created_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 404`: `PROJECT_NOT_FOUND` (target project does not exist)
- `HTTP 409`: `CONCURRENCY_CONFLICT` (revision mismatch under OCC)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 42. `GET` /api/v1/workspaces/{workspace_id}/projects/{project_id}/versions/{version_id}
**Summary**: Get Project Version Snapshot  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `get_project_version_api_v1_workspaces__workspace_id__projects__project_id__versions__version_id__get`  

**Purpose**:
Fetches full ProjectDocument JSON for an immutable version snapshot.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `project_id` | path | string | Yes | Target Project UUID |
| `version_id` | path | string | Yes | Target Project Version UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `ProjectVersionResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `project_id` (string) *(required)*
- `revision` (integer) *(required)*
- `document` (object) *(required)* — Project document snapshot
- `source` (string) *(required)*
- `created_by` (string) *(required)*
- `created_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 404`: `PROJECT_NOT_FOUND` (target project does not exist)
- `HTTP 409`: `CONCURRENCY_CONFLICT` (revision mismatch under OCC)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

## Project Orchestration (Video Agent, Speech, Translation & Render)
*Total Endpoints: 9*

### 43. `POST` /api/v1/workspaces/{workspace_id}/projects/generate
**Summary**: Generate Project from Prompt  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `generate_project_api_v1_workspaces__workspace_id__projects_generate_post`  

**Purpose**:
Video Agent endpoint decomposing a natural language prompt into an initialized multi-scene project. Supports async Celery execution (HTTP 202) or synchronous return (HTTP 201).

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Short-lived access token for browser EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `GenerateProjectRequest`
- `prompt` (string) *(required)* — Natural language project prompt
- `target_duration_seconds` (object) *(optional)*, default: `30.0` — Desired total video duration
- `aspect_ratio` (string) *(optional)*, default: `16:9` — Aspect ratio canvas format
- `avatar_id` (object) *(optional)* — Optional default catalog avatar ID
- `voice_id` (object) *(optional)* — Optional default catalog voice ID
- `brand_kit_id` (object) *(optional)* — Optional brand kit for color scheme and styling
- `video_tone` (string) *(optional)*, default: `Professional` — Video tone (Professional, Energetic, Casual, Educational)
- `auto_synthesize_speech` (boolean) *(optional)*, default: `False` — Whether to kick off async speech synthesis immediately
- `run_async` (boolean) *(optional)*, default: `False` — Whether to run generation asynchronously via Celery job
- `provider` (object) *(optional)* — Optional LLM provider override ('qwen', 'mock')
- `device` (object) *(optional)* — Optional compute device override ('cpu', 'cuda')
- `idempotency_key` (object) *(optional)* — Optional idempotency key for async task deduplication

**Responses**:
- **HTTP 201**: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 44. `POST` /api/v1/workspaces/{workspace_id}/projects/{project_id}/enhance-speech
**Summary**: Enhance Speech Audio and Studio Cleanup  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `enhance_speech_api_v1_workspaces__workspace_id__projects__project_id__enhance_speech_post`  

**Purpose**:
Enhances scene speech audio (noise suppression, pause trimming, broadcast mastering). Async returns HTTP 202 JobResponse; sync returns HTTP 200 ProjectVersionResponse.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `project_id` | path | string | Yes | Target Project UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Short-lived access token for browser EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `EnhanceProjectSpeechRequest`
- `expected_revision` (integer) *(required)* — Required current project revision for optimistic concurrency check
- `scene_id` (object) *(optional)* — Optional target scene ID; if None, targets all scenes with speech
- `denoise` (boolean) *(optional)*, default: `True` — Enable neural noise suppression
- `remove_silence` (boolean) *(optional)*, default: `False` — Enable Silero VAD dead-pause trimming
- `remove_fillers` (boolean) *(optional)*, default: `False` — Filler removal toggle (disabled/NOT_IMPLEMENTED)
- `master_audio` (boolean) *(optional)*, default: `True` — Apply broadcast EQ, compression, and loudness mastering
- `provider` (object) *(optional)* — Optional provider override ('deepfilter' or 'mock')
- `run_async` (boolean) *(optional)*, default: `True` — Canonical execution mode: async via Celery job (HTTP 202)
- `idempotency_key` (object) *(optional)* — Optional idempotency key for deduplication

**Responses**:
- **HTTP 202**: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 404`: `PROJECT_NOT_FOUND` (target project does not exist)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 45. `POST` /api/v1/workspaces/{workspace_id}/projects/{project_id}/generate-avatar-video
**Summary**: Synthesize Talking Avatar Video  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `generate_avatar_video_api_v1_workspaces__workspace_id__projects__project_id__generate_avatar_video_post`  

**Purpose**:
Synthesizes neural lip-synced avatar video for a project scene. Async returns HTTP 202 JobResponse; sync returns HTTP 200 ProjectVersionResponse.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `project_id` | path | string | Yes | Target Project UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Short-lived access token for browser EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `GenerateAvatarVideoRequest`
- `expected_revision` (integer) *(required)* — Required current project revision for optimistic concurrency check
- `scene_id` (object) *(optional)* — Optional target scene ID; if None, targets first scene with avatar
- `avatar_id_override` (object) *(optional)* — Optional avatar ID or asset ID override
- `provider` (object) *(optional)* — Optional provider override ('wav2lip', 'musetalk', 'mock')
- `device` (object) *(optional)* — Optional device target ('cpu', 'cuda')
- `run_async` (boolean) *(optional)*, default: `True` — Canonical execution mode: async via Celery job (HTTP 202)
- `idempotency_key` (object) *(optional)* — Optional idempotency key for deduplication

**Responses**:
- **HTTP 202**: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 404`: `PROJECT_NOT_FOUND` (target project does not exist)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 46. `POST` /api/v1/workspaces/{workspace_id}/projects/{project_id}/render
**Summary**: Export Video Render  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `render_project_api_v1_workspaces__workspace_id__projects__project_id__render_post`  

**Purpose**:
Freezes exact expected_revision, performs pre-flight validation, and dispatches composite render job.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `project_id` | path | string | Yes | Target Project UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Short-lived access token for browser EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `RenderProjectRequest`
- `resolution` (string) *(optional)*, default: `1080p` — Output render resolution
- `fps` (integer) *(optional)*, default: `30` — Video framerate
- `export_format` (string) *(optional)*, default: `mp4` — Output video format
- `expected_revision` (integer) *(required)* — Required exact project revision to freeze and render
- `idempotency_key` (object) *(optional)* — Optional idempotency key

**Responses**:
- **HTTP 202** — Model: `JobResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `workspace_id` (string) *(required)*
- `created_by` (string) *(required)*
- `job_type` (string) *(required)*
- `status` (string) *(required)*
- `priority` (integer) *(required)*
- `idempotency_key` (object) *(optional)*
- `progress_percent` (integer) *(required)*
- `stage` (object) *(optional)*
- `stage_message` (object) *(optional)*
- `payload` (object) *(required)*
- `result` (object) *(optional)*
- `error_details` (object) *(optional)*
- `celery_task_id` (object) *(optional)*
- `retry_count` (integer) *(required)*
- `max_retries` (integer) *(required)*
- `started_at` (object) *(optional)*
- `completed_at` (object) *(optional)*
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 404`: `PROJECT_NOT_FOUND` (target project does not exist)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 409`: `CONCURRENCY_CONFLICT` (revision mismatch under OCC)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 47. `POST` /api/v1/workspaces/{workspace_id}/projects/{project_id}/scenes/{scene_id}/generate-visual
**Summary**: Generate Scene Visual  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `generate_scene_visual_api_v1_workspaces__workspace_id__projects__project_id__scenes__scene_id__generate_visual_post`  

**Purpose**:
Generates AI background image or b-roll video for a target scene layer.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `project_id` | path | string | Yes | Target Project UUID |
| `scene_id` | path | string | Yes | Target Scene Identifier |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Short-lived access token for browser EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `GenerateSceneVisualRequest`
- `visual_type` (string) *(optional)*, default: `image` — Visual media type to generate
- `prompt` (string) *(required)* — Visual description prompt
- `aspect_ratio` (string) *(optional)*, default: `16:9` — Asset aspect ratio
- `expected_revision` (integer) *(required)* — Required current revision for optimistic concurrency check
- `provider` (object) *(optional)* — Optional provider override ('stable_diffusion' or 'mock')
- `negative_prompt` (object) *(optional)* — Excluded visual concepts
- `seed` (object) *(optional)* — Deterministic generation seed
- `run_async` (boolean) *(optional)*, default: `True` — Canonical execution mode: async via Celery job
- `idempotency_key` (object) *(optional)* — Optional idempotency key

**Responses**:
- **HTTP 202**: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 404`: `PROJECT_NOT_FOUND` (target project does not exist)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 48. `POST` /api/v1/workspaces/{workspace_id}/projects/{project_id}/synthesize-speech
**Summary**: Synthesize Timeline Speech  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `synthesize_speech_api_v1_workspaces__workspace_id__projects__project_id__synthesize_speech_post`  

**Purpose**:
Synthesizes speech audio for scenes. Canonically async (HTTP 202 JobResponse); sync for tests.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `project_id` | path | string | Yes | Target Project UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Short-lived access token for browser EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `SynthesizeProjectSpeechRequest`
- `scene_ids` (object) *(optional)* — Target scene IDs; None means all scenes with speech text
- `expected_revision` (integer) *(required)* — Required current revision for optimistic concurrency check
- `voice_id_override` (object) *(optional)* — Optional voice ID override for target scenes
- `run_async` (boolean) *(optional)*, default: `True` — Canonical execution mode: async via Celery job
- `idempotency_key` (object) *(optional)* — Optional idempotency key for async task deduplication

**Responses**:
- **HTTP 202**: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 404`: `PROJECT_NOT_FOUND` (target project does not exist)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 49. `POST` /api/v1/workspaces/{workspace_id}/projects/{project_id}/transcribe
**Summary**: Transcribe Project Audio to Subtitles  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `transcribe_project_audio_api_v1_workspaces__workspace_id__projects__project_id__transcribe_post`  

**Purpose**:
Transcribes scene speech audio into structured subtitle cues. Async returns HTTP 202 JobResponse; sync returns HTTP 200 ProjectVersionResponse.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `project_id` | path | string | Yes | Target Project UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Short-lived access token for browser EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `TranscribeProjectAudioRequest`
- `expected_revision` (integer) *(required)* — Required current project revision for optimistic concurrency check
- `scene_id` (object) *(optional)* — Optional target scene ID; if None, targets first scene with audio
- `audio_asset_id` (object) *(optional)* — Optional direct audio asset ID override
- `language` (object) *(optional)* — Optional language hint (e.g. 'en')
- `provider` (object) *(optional)* — Optional provider override ('whisper' or 'mock')
- `run_async` (boolean) *(optional)*, default: `True` — Canonical execution mode: async via Celery job
- `idempotency_key` (object) *(optional)* — Optional idempotency key for deduplication

**Responses**:
- **HTTP 202**: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 404`: `PROJECT_NOT_FOUND` (target project does not exist)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 50. `POST` /api/v1/workspaces/{workspace_id}/projects/{project_id}/translate
**Summary**: Translate Project Timeline  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `translate_project_api_v1_workspaces__workspace_id__projects__project_id__translate_post`  

**Purpose**:
Translates multi-scene scripts with Brand Glossary compliance. Returns JobResponse or localized project.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `project_id` | path | string | Yes | Target Project UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Short-lived access token for browser EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `TranslateProjectRequest`
- `target_language` (string) *(optional)*, default: `es` — Target language code (e.g. 'es', 'fr', 'de')
- `target_languages` (object) *(optional)* — Optional multi-language targets for multi-output translation
- `source_language` (string) *(optional)*, default: `en` — Source language code
- `target_voice_id` (object) *(optional)* — Optional voice ID matching target language
- `video_asset_id` (object) *(optional)* — Optional source video asset UUID for direct video dubbing
- `enable_subtitles` (boolean) *(optional)*, default: `True` — Generate and embed translated subtitles
- `enable_lip_sync` (boolean) *(optional)*, default: `False` — Apply lip-sync synchronization
- `enable_voice_clone` (boolean) *(optional)*, default: `False` — Apply voice cloning to target audio
- `glossary_id` (object) *(optional)* — Brand Glossary UUID to enforce
- `create_fork` (boolean) *(optional)*, default: `True` — Create new project fork vs new version on same project
- `expected_revision` (object) *(optional)* — Required when create_fork=False
- `run_async` (boolean) *(optional)*, default: `True` — Canonical execution mode: async via Celery job
- `idempotency_key` (object) *(optional)* — Optional idempotency key

**Responses**:
- **HTTP 202**: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 404`: `PROJECT_NOT_FOUND` (target project does not exist)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 51. `POST` /api/v1/workspaces/{workspace_id}/projects/{project_id}/validate
**Summary**: Validate Project Timeline  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `validate_timeline_api_v1_workspaces__workspace_id__projects__project_id__validate_post`  

**Purpose**:
Synchronous pre-flight diagnostics evaluating whether project is ready for rendering.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `project_id` | path | string | Yes | Target Project UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `TimelineValidationResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `is_valid` (boolean) *(required)* — Whether project passes all pre-flight checks
- `scene_count` (integer) *(required)* — Number of scenes in the project timeline
- `total_duration` (number) *(required)* — Calculated total duration in seconds
- `errors` (array) *(optional)* — Fatal blocking issues that prevent rendering
- `warnings` (array) *(optional)* — Non-blocking recommendations
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 404`: `PROJECT_NOT_FOUND` (target project does not exist)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

## Assets & Object Storage
*Total Endpoints: 7*

### 52. `GET` /api/v1/workspaces/{workspace_id}/assets
**Summary**: List Workspace Assets  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `list_assets_api_v1_workspaces__workspace_id__assets_get`  

**Purpose**:
Lists active assets with optional filtering by asset type, status, or filename.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `asset_type` | query | string | No | Filter by category: image, video, audio, etc. |
| `status` | query | string | No | Filter by lifecycle state |
| `search` | query | string | No | Keyword search in original filename |
| `limit` | query | integer | No |  |
| `offset` | query | integer | No |  |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `array`: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 53. `POST` /api/v1/workspaces/{workspace_id}/assets/ingest-url
**Summary**: Ingest Video from URL  
**Classification**: Application API | **Auth Required**: Protected (HTTPBearer)  
**Operation ID**: `ingest_video_url_api_v1_workspaces__workspace_id__assets_ingest_url_post`  

**Purpose**:
Ingests a video from a remote URL (YouTube, Google Drive, direct MP4) into MinIO object storage.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Short-lived access token for browser EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `None`
- `url` (string) *(required)* — Public video URL

**Responses**:
- **HTTP 201** — Model: `AssetResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `workspace_id` (string) *(required)*
- `created_by` (string) *(required)*
- `original_filename` (string) *(required)*
- `storage_bucket` (string) *(required)*
- `storage_key` (string) *(required)*
- `mime_type` (string) *(required)*
- `size_bytes` (object) *(optional)*
- `checksum_sha256` (object) *(optional)*
- `asset_type` (string) *(required)*
- `status` (string) *(required)*
- `metadata` (object) *(optional)*
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 54. `POST` /api/v1/workspaces/{workspace_id}/assets/upload-intents
**Summary**: Create Upload Intent  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `create_upload_intent_api_v1_workspaces__workspace_id__assets_upload_intents_post`  

**Purpose**:
Registers upload intent and generates a pre-signed PUT URL for direct MinIO/S3 upload.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Short-lived access token for browser EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `AssetUploadIntentRequest`
- `original_filename` (string) *(required)*
- `mime_type` (string) *(required)*
- `size_bytes` (object) *(optional)* — Expected file size in bytes
- `asset_type` (string) *(optional)*, default: `other` — Generic category: image, video, audio, document, font, other
- `checksum_sha256` (object) *(optional)* — Claimed SHA-256 digest of binary content

**Responses**:
- **HTTP 201** — Model: `AssetUploadIntentResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `asset_id` (string) *(required)*
- `storage_bucket` (string) *(required)*
- `storage_key` (string) *(required)*
- `signed_upload_url` (string) *(required)*
- `expires_in_seconds` (integer) *(required)*
- `required_headers` (object) *(optional)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 55. `DELETE` /api/v1/workspaces/{workspace_id}/assets/{asset_id}
**Summary**: Delete Asset  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `delete_asset_api_v1_workspaces__workspace_id__assets__asset_id__delete`  

**Purpose**:
Soft-deletes asset record from database. Physical object cleanup is scheduled asynchronously.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `asset_id` | path | string | Yes | Target Asset UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 204**: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 56. `GET` /api/v1/workspaces/{workspace_id}/assets/{asset_id}
**Summary**: Get Asset Metadata  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `get_asset_api_v1_workspaces__workspace_id__assets__asset_id__get`  

**Purpose**:
Fetches metadata record for an individual asset.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `asset_id` | path | string | Yes | Target Asset UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `AssetResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `workspace_id` (string) *(required)*
- `created_by` (string) *(required)*
- `original_filename` (string) *(required)*
- `storage_bucket` (string) *(required)*
- `storage_key` (string) *(required)*
- `mime_type` (string) *(required)*
- `size_bytes` (object) *(optional)*
- `checksum_sha256` (object) *(optional)*
- `asset_type` (string) *(required)*
- `status` (string) *(required)*
- `metadata` (object) *(optional)*
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 57. `POST` /api/v1/workspaces/{workspace_id}/assets/{asset_id}/confirm
**Summary**: Confirm Asset Upload  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `confirm_asset_upload_api_v1_workspaces__workspace_id__assets__asset_id__confirm_post`  

**Purpose**:
Verifies the uploaded binary object in storage and transitions status to 'ready'.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `asset_id` | path | string | Yes | Target Asset UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `AssetConfirmResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `asset_id` (string) *(required)*
- `status` (string) *(required)*
- `size_bytes` (object) *(optional)*
- `mime_type` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 58. `GET` /api/v1/workspaces/{workspace_id}/assets/{asset_id}/download
**Summary**: Get Signed Download URL  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `get_asset_download_url_api_v1_workspaces__workspace_id__assets__asset_id__download_get`  

**Purpose**:
Generates a secure pre-signed GET URL for direct asset consumption from storage.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `asset_id` | path | string | Yes | Target Asset UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `AssetDownloadResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `asset_id` (string) *(required)*
- `download_url` (string) *(required)*
- `expires_in_seconds` (integer) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

## Avatars & Digital Twin Looks
*Total Endpoints: 10*

### 59. `GET` /api/v1/avatars
**Summary**: List Avatars  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `list_avatars_api_v1_avatars_get`  

**Purpose**:
Lists active avatars in the active workspace.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `avatar_type` | query | string | No |  |
| `status` | query | string | No |  |
| `search` | query | string | No |  |
| `limit` | query | integer | No |  |
| `offset` | query | integer | No |  |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `array`: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 60. `POST` /api/v1/avatars
**Summary**: Create Avatar  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `create_avatar_api_v1_avatars_post`  

**Purpose**:
Initializes a new avatar in the active workspace.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Short-lived access token for browser EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `CreateAvatarRequest`
- `name` (string) *(required)* — Avatar name
- `description` (object) *(optional)*
- `avatar_type` (object) *(optional)*, default: `custom`
- `visibility` (object) *(optional)*, default: `workspace`
- `provider` (object) *(optional)*, default: `mock`
- `provider_reference` (object) *(optional)*
- `provider_metadata` (object) *(optional)*
- `preview_asset_id` (object) *(optional)*
- `source_asset_id` (object) *(optional)*
- `initial_look` (object) *(optional)*

**Responses**:
- **HTTP 201** — Model: `AvatarResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `workspace_id` (string) *(required)*
- `created_by` (string) *(required)*
- `name` (string) *(required)*
- `description` (object) *(optional)*
- `avatar_type` (string) *(required)*
- `status` (string) *(required)*
- `visibility` (string) *(required)*
- `provider` (string) *(required)*
- `provider_reference` (object) *(optional)*
- `provider_metadata` (object) *(required)*
- `preview_asset_id` (object) *(optional)*
- `source_asset_id` (object) *(optional)*
- `preview_url` (object) *(optional)*
- `looks` (array) *(optional)*
  - *Item properties:*
    - `id` (string) *(required)*
    - `avatar_id` (string) *(required)*
    - `name` (string) *(required)*
    - `description` (object) *(optional)*
    - `status` (string) *(required)*
    - `configuration` (object) *(required)*
    - `preview_asset_id` (object) *(optional)*
    - `preview_url` (object) *(optional)*
    - `provider` (string) *(required)*
    - `provider_reference` (object) *(optional)*
    - `created_at` (string) *(required)*
    - `updated_at` (string) *(required)*
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 61. `DELETE` /api/v1/avatars/{avatar_id}
**Summary**: Delete Avatar  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `delete_avatar_api_v1_avatars__avatar_id__delete`  

**Purpose**:
Soft-deletes an avatar record.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `avatar_id` | path | string | Yes | Target Avatar UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 204**: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 62. `GET` /api/v1/avatars/{avatar_id}
**Summary**: Get Avatar  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `get_avatar_api_v1_avatars__avatar_id__get`  

**Purpose**:
Fetches an avatar and its looks by ID.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `avatar_id` | path | string | Yes | Target Avatar UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `AvatarResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `workspace_id` (string) *(required)*
- `created_by` (string) *(required)*
- `name` (string) *(required)*
- `description` (object) *(optional)*
- `avatar_type` (string) *(required)*
- `status` (string) *(required)*
- `visibility` (string) *(required)*
- `provider` (string) *(required)*
- `provider_reference` (object) *(optional)*
- `provider_metadata` (object) *(required)*
- `preview_asset_id` (object) *(optional)*
- `source_asset_id` (object) *(optional)*
- `preview_url` (object) *(optional)*
- `looks` (array) *(optional)*
  - *Item properties:*
    - `id` (string) *(required)*
    - `avatar_id` (string) *(required)*
    - `name` (string) *(required)*
    - `description` (object) *(optional)*
    - `status` (string) *(required)*
    - `configuration` (object) *(required)*
    - `preview_asset_id` (object) *(optional)*
    - `preview_url` (object) *(optional)*
    - `provider` (string) *(required)*
    - `provider_reference` (object) *(optional)*
    - `created_at` (string) *(required)*
    - `updated_at` (string) *(required)*
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 63. `PATCH` /api/v1/avatars/{avatar_id}
**Summary**: Update Avatar  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `update_avatar_api_v1_avatars__avatar_id__patch`  

**Purpose**:
Updates avatar metadata, status, or asset references.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `avatar_id` | path | string | Yes | Target Avatar UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `UpdateAvatarRequest`
- `name` (object) *(optional)*
- `description` (object) *(optional)*
- `avatar_type` (object) *(optional)*
- `status` (object) *(optional)*
- `visibility` (object) *(optional)*
- `provider` (object) *(optional)*
- `provider_reference` (object) *(optional)*
- `provider_metadata` (object) *(optional)*
- `preview_asset_id` (object) *(optional)*
- `source_asset_id` (object) *(optional)*

**Responses**:
- **HTTP 200** — Model: `AvatarResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `workspace_id` (string) *(required)*
- `created_by` (string) *(required)*
- `name` (string) *(required)*
- `description` (object) *(optional)*
- `avatar_type` (string) *(required)*
- `status` (string) *(required)*
- `visibility` (string) *(required)*
- `provider` (string) *(required)*
- `provider_reference` (object) *(optional)*
- `provider_metadata` (object) *(required)*
- `preview_asset_id` (object) *(optional)*
- `source_asset_id` (object) *(optional)*
- `preview_url` (object) *(optional)*
- `looks` (array) *(optional)*
  - *Item properties:*
    - `id` (string) *(required)*
    - `avatar_id` (string) *(required)*
    - `name` (string) *(required)*
    - `description` (object) *(optional)*
    - `status` (string) *(required)*
    - `configuration` (object) *(required)*
    - `preview_asset_id` (object) *(optional)*
    - `preview_url` (object) *(optional)*
    - `provider` (string) *(required)*
    - `provider_reference` (object) *(optional)*
    - `created_at` (string) *(required)*
    - `updated_at` (string) *(required)*
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 64. `GET` /api/v1/avatars/{avatar_id}/looks
**Summary**: List Avatar Looks  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `list_avatar_looks_api_v1_avatars__avatar_id__looks_get`  

**Purpose**:
Lists all visual presentation looks for an avatar.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `avatar_id` | path | string | Yes | Target Avatar UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `array`: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 65. `POST` /api/v1/avatars/{avatar_id}/looks
**Summary**: Create Avatar Look  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `create_avatar_look_api_v1_avatars__avatar_id__looks_post`  

**Purpose**:
Adds a new visual look/pose to an avatar.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `avatar_id` | path | string | Yes | Target Avatar UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `CreateAvatarLookRequest`
- `name` (string) *(required)* — Look display name
- `description` (object) *(optional)*
- `configuration` (object) *(optional)* — Pose, framing, style options
- `preview_asset_id` (object) *(optional)* — Look preview asset reference
- `provider` (object) *(optional)*, default: `mock`
- `provider_reference` (object) *(optional)*

**Responses**:
- **HTTP 201** — Model: `AvatarLookResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `avatar_id` (string) *(required)*
- `name` (string) *(required)*
- `description` (object) *(optional)*
- `status` (string) *(required)*
- `configuration` (object) *(required)*
- `preview_asset_id` (object) *(optional)*
- `preview_url` (object) *(optional)*
- `provider` (string) *(required)*
- `provider_reference` (object) *(optional)*
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 66. `DELETE` /api/v1/avatars/{avatar_id}/looks/{look_id}
**Summary**: Delete Avatar Look  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `delete_avatar_look_api_v1_avatars__avatar_id__looks__look_id__delete`  

**Purpose**:
Deletes a visual look from an avatar.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `avatar_id` | path | string | Yes | Target Avatar UUID |
| `look_id` | path | string | Yes | Target Avatar Look UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 204**: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 67. `GET` /api/v1/avatars/{avatar_id}/looks/{look_id}
**Summary**: Get Avatar Look  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `get_avatar_look_api_v1_avatars__avatar_id__looks__look_id__get`  

**Purpose**:
Fetches a specific avatar look by ID.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `avatar_id` | path | string | Yes | Target Avatar UUID |
| `look_id` | path | string | Yes | Target Avatar Look UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `AvatarLookResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `avatar_id` (string) *(required)*
- `name` (string) *(required)*
- `description` (object) *(optional)*
- `status` (string) *(required)*
- `configuration` (object) *(required)*
- `preview_asset_id` (object) *(optional)*
- `preview_url` (object) *(optional)*
- `provider` (string) *(required)*
- `provider_reference` (object) *(optional)*
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 68. `PATCH` /api/v1/avatars/{avatar_id}/looks/{look_id}
**Summary**: Update Avatar Look  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `update_avatar_look_api_v1_avatars__avatar_id__looks__look_id__patch`  

**Purpose**:
Updates look configuration, styling, or preview asset.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `avatar_id` | path | string | Yes | Target Avatar UUID |
| `look_id` | path | string | Yes | Target Avatar Look UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `UpdateAvatarLookRequest`
- `name` (object) *(optional)*
- `description` (object) *(optional)*
- `status` (object) *(optional)*
- `configuration` (object) *(optional)*
- `preview_asset_id` (object) *(optional)*
- `provider` (object) *(optional)*
- `provider_reference` (object) *(optional)*

**Responses**:
- **HTTP 200** — Model: `AvatarLookResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `avatar_id` (string) *(required)*
- `name` (string) *(required)*
- `description` (object) *(optional)*
- `status` (string) *(required)*
- `configuration` (object) *(required)*
- `preview_asset_id` (object) *(optional)*
- `preview_url` (object) *(optional)*
- `provider` (string) *(required)*
- `provider_reference` (object) *(optional)*
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

## Voices & Voice Cloning
*Total Endpoints: 8*

### 69. `GET` /api/v1/voices
**Summary**: List Voices  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `list_voices_api_v1_voices_get`  

**Purpose**:
Lists active voices in the workspace with filtering.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `language` | query | string | No |  |
| `gender` | query | string | No |  |
| `voice_type` | query | string | No |  |
| `status` | query | string | No |  |
| `search` | query | string | No |  |
| `limit` | query | integer | No |  |
| `offset` | query | integer | No |  |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `array`: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 70. `POST` /api/v1/voices
**Summary**: Create Voice  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `create_voice_api_v1_voices_post`  

**Purpose**:
Registers a new speech synthesis voice in the workspace.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Short-lived access token for browser EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `CreateVoiceRequest`
- `name` (string) *(required)* — Voice display name
- `description` (object) *(optional)*
- `voice_type` (object) *(optional)*, default: `custom`
- `language` (object) *(optional)*, default: `en`
- `gender` (object) *(optional)*, default: `neutral`
- `provider` (object) *(optional)*, default: `mock`
- `provider_reference` (object) *(optional)*
- `provider_metadata` (object) *(optional)*
- `preview_asset_id` (object) *(optional)*
- `visibility` (object) *(optional)*, default: `workspace`

**Responses**:
- **HTTP 201** — Model: `VoiceResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `workspace_id` (string) *(required)*
- `created_by` (string) *(required)*
- `name` (string) *(required)*
- `description` (object) *(optional)*
- `voice_type` (string) *(required)*
- `language` (string) *(required)*
- `gender` (string) *(required)*
- `provider` (string) *(required)*
- `provider_reference` (object) *(optional)*
- `provider_metadata` (object) *(required)*
- `preview_asset_id` (object) *(optional)*
- `preview_url` (object) *(optional)*
- `status` (string) *(required)*
- `visibility` (string) *(required)*
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 71. `POST` /api/v1/voices/clone
**Summary**: Clone Voice (Header-scoped)  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `clone_voice_header_api_v1_voices_clone_post`  

**Purpose**:
Initiates asynchronous zero-shot voice cloning from a reference audio asset.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Short-lived access token for browser EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `VoiceCloneRequest`
- `name` (string) *(required)* — Display name for the cloned voice
- `reference_asset_id` (string) *(required)* — ID of the audio Asset to use as reference speaker sample
- `language` (object) *(optional)*, default: `en` — Target language code (e.g., 'en', 'es', 'zh')
- `description` (object) *(optional)* — Optional description of voice style/tone
- `gender` (object) *(optional)*, default: `neutral` — Perceived voice gender (male, female, neutral)
- `options` (object) *(optional)* — Additional model inference options

**Responses**:
- **HTTP 202** — Model: `VoiceCloneJobResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `job_id` (string) *(required)* — Durable job tracking ID
- `voice_id` (string) *(required)* — Pre-allocated voice record ID
- `status` (string) *(required)* — Current job status (queued, running, etc.)
- `voice_name` (string) *(required)* — Cloned voice name
- `workspace_id` (string) *(required)* — Owning workspace ID
- `created_at` (string) *(required)* — Creation timestamp
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 72. `DELETE` /api/v1/voices/{voice_id}
**Summary**: Delete Voice  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `delete_voice_api_v1_voices__voice_id__delete`  

**Purpose**:
Soft-deletes a voice.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `voice_id` | path | string | Yes | Target Voice Catalog UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 204**: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 73. `GET` /api/v1/voices/{voice_id}
**Summary**: Get Voice  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `get_voice_api_v1_voices__voice_id__get`  

**Purpose**:
Fetches a specific voice by ID.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `voice_id` | path | string | Yes | Target Voice Catalog UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `VoiceResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `workspace_id` (string) *(required)*
- `created_by` (string) *(required)*
- `name` (string) *(required)*
- `description` (object) *(optional)*
- `voice_type` (string) *(required)*
- `language` (string) *(required)*
- `gender` (string) *(required)*
- `provider` (string) *(required)*
- `provider_reference` (object) *(optional)*
- `provider_metadata` (object) *(required)*
- `preview_asset_id` (object) *(optional)*
- `preview_url` (object) *(optional)*
- `status` (string) *(required)*
- `visibility` (string) *(required)*
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 74. `PATCH` /api/v1/voices/{voice_id}
**Summary**: Update Voice  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `update_voice_api_v1_voices__voice_id__patch`  

**Purpose**:
Updates voice metadata, language, or preview sample asset.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `voice_id` | path | string | Yes | Target Voice Catalog UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `UpdateVoiceRequest`
- `name` (object) *(optional)*
- `description` (object) *(optional)*
- `voice_type` (object) *(optional)*
- `language` (object) *(optional)*
- `gender` (object) *(optional)*
- `provider` (object) *(optional)*
- `provider_reference` (object) *(optional)*
- `provider_metadata` (object) *(optional)*
- `preview_asset_id` (object) *(optional)*
- `status` (object) *(optional)*
- `visibility` (object) *(optional)*

**Responses**:
- **HTTP 200** — Model: `VoiceResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `workspace_id` (string) *(required)*
- `created_by` (string) *(required)*
- `name` (string) *(required)*
- `description` (object) *(optional)*
- `voice_type` (string) *(required)*
- `language` (string) *(required)*
- `gender` (string) *(required)*
- `provider` (string) *(required)*
- `provider_reference` (object) *(optional)*
- `provider_metadata` (object) *(required)*
- `preview_asset_id` (object) *(optional)*
- `preview_url` (object) *(optional)*
- `status` (string) *(required)*
- `visibility` (string) *(required)*
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 75. `GET` /api/v1/voices/{voice_id}/preview
**Summary**: Get Voice Preview Audio  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `get_voice_preview_api_v1_voices__voice_id__preview_get`  

**Purpose**:
Generates a signed URL for direct audio playback of the voice preview sample.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `voice_id` | path | string | Yes | Target Voice Catalog UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `VoicePreviewResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `voice_id` (string) *(required)*
- `preview_asset_id` (object) *(optional)*
- `preview_url` (object) *(optional)*
- `provider` (string) *(required)*
- `status` (string) *(required)*
- `expires_in_seconds` (integer) *(optional)*, default: `3600`
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 76. `POST` /api/v1/workspaces/{workspace_id}/voices/clone
**Summary**: Clone Voice (Workspace-scoped)  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `clone_voice_workspace_api_v1_workspaces__workspace_id__voices_clone_post`  

**Purpose**:
Initiates asynchronous zero-shot voice cloning from a reference audio asset in the workspace.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Short-lived access token for browser EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `VoiceCloneRequest`
- `name` (string) *(required)* — Display name for the cloned voice
- `reference_asset_id` (string) *(required)* — ID of the audio Asset to use as reference speaker sample
- `language` (object) *(optional)*, default: `en` — Target language code (e.g., 'en', 'es', 'zh')
- `description` (object) *(optional)* — Optional description of voice style/tone
- `gender` (object) *(optional)*, default: `neutral` — Perceived voice gender (male, female, neutral)
- `options` (object) *(optional)* — Additional model inference options

**Responses**:
- **HTTP 202** — Model: `VoiceCloneJobResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `job_id` (string) *(required)* — Durable job tracking ID
- `voice_id` (string) *(required)* — Pre-allocated voice record ID
- `status` (string) *(required)* — Current job status (queued, running, etc.)
- `voice_name` (string) *(required)* — Cloned voice name
- `workspace_id` (string) *(required)* — Owning workspace ID
- `created_at` (string) *(required)* — Creation timestamp
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

## Templates
*Total Endpoints: 9*

### 77. `GET` /api/v1/templates
**Summary**: List Templates  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `list_templates_api_v1_templates_get`  

**Purpose**:
Lists active templates in the workspace.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `category` | query | string | No |  |
| `status` | query | string | No |  |
| `search` | query | string | No |  |
| `limit` | query | integer | No |  |
| `offset` | query | integer | No |  |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `array`: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 78. `POST` /api/v1/templates
**Summary**: Create Template  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `create_template_api_v1_templates_post`  

**Purpose**:
Initializes a new template with revision 1 immutable TemplateVersion.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Short-lived access token for browser EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `CreateTemplateRequest`
- `name` (string) *(required)* — Template display name
- `description` (object) *(optional)*
- `category` (object) *(optional)*, default: `marketing`
- `visibility` (object) *(optional)*, default: `workspace`
- `thumbnail_asset_id` (object) *(optional)*
- `configuration` (object) *(optional)*
- `initial_document` (object) *(optional)*

**Responses**:
- **HTTP 201** — Model: `TemplateResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `workspace_id` (string) *(required)*
- `created_by` (string) *(required)*
- `name` (string) *(required)*
- `description` (object) *(optional)*
- `category` (string) *(required)*
- `status` (string) *(required)*
- `visibility` (string) *(required)*
- `thumbnail_asset_id` (object) *(optional)*
- `configuration` (object) *(required)*
- `current_version_id` (object) *(optional)*
- `revision` (integer) *(required)*
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 79. `DELETE` /api/v1/templates/{template_id}
**Summary**: Delete Template  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `delete_template_api_v1_templates__template_id__delete`  

**Purpose**:
Soft-deletes a template.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `template_id` | path | string | Yes | Target Video Template UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 204**: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 80. `GET` /api/v1/templates/{template_id}
**Summary**: Get Template  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `get_template_api_v1_templates__template_id__get`  

**Purpose**:
Fetches a specific template and its active version snapshot.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `template_id` | path | string | Yes | Target Video Template UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `TemplateResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `workspace_id` (string) *(required)*
- `created_by` (string) *(required)*
- `name` (string) *(required)*
- `description` (object) *(optional)*
- `category` (string) *(required)*
- `status` (string) *(required)*
- `visibility` (string) *(required)*
- `thumbnail_asset_id` (object) *(optional)*
- `configuration` (object) *(required)*
- `current_version_id` (object) *(optional)*
- `revision` (integer) *(required)*
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 81. `PATCH` /api/v1/templates/{template_id}
**Summary**: Update Template  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `update_template_api_v1_templates__template_id__patch`  

**Purpose**:
Updates template metadata and settings without modifying historical version snapshots.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `template_id` | path | string | Yes | Target Video Template UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `UpdateTemplateRequest`
- `name` (object) *(optional)*
- `description` (object) *(optional)*
- `category` (object) *(optional)*
- `status` (object) *(optional)*
- `visibility` (object) *(optional)*
- `thumbnail_asset_id` (object) *(optional)*
- `configuration` (object) *(optional)*

**Responses**:
- **HTTP 200** — Model: `TemplateResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `workspace_id` (string) *(required)*
- `created_by` (string) *(required)*
- `name` (string) *(required)*
- `description` (object) *(optional)*
- `category` (string) *(required)*
- `status` (string) *(required)*
- `visibility` (string) *(required)*
- `thumbnail_asset_id` (object) *(optional)*
- `configuration` (object) *(required)*
- `current_version_id` (object) *(optional)*
- `revision` (integer) *(required)*
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 82. `POST` /api/v1/templates/{template_id}/instantiate
**Summary**: Instantiate Template  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `instantiate_template_api_v1_templates__template_id__instantiate_post`  

**Purpose**:
Instantiates a template into an active video project pre-populated with its document.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `template_id` | path | string | Yes | Target Video Template UUID |
| `title` | query | string | No | Optional custom title for the new project |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Short-lived access token for browser EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 201** — Model: `ProjectResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `workspace_id` (string) *(required)*
- `folder_id` (object) *(optional)*
- `created_by` (string) *(required)*
- `title` (string) *(required)*
- `project_type` (string) *(required)*
- `status` (string) *(required)*
- `aspect_ratio` (string) *(required)*
- `width` (object) *(optional)*
- `height` (object) *(optional)*
- `fps` (object) *(optional)*
- `duration_ms` (object) *(optional)*
- `thumbnail_asset_id` (object) *(optional)*
- `current_version_id` (object) *(optional)*
- `revision` (integer) *(required)*
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 83. `GET` /api/v1/templates/{template_id}/versions
**Summary**: List Template Versions  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `list_template_versions_api_v1_templates__template_id__versions_get`  

**Purpose**:
Lists all immutable historical version snapshots of a template.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `template_id` | path | string | Yes | Target Video Template UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `array`: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 409`: `CONCURRENCY_CONFLICT` (revision mismatch under OCC)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 84. `POST` /api/v1/templates/{template_id}/versions
**Summary**: Create Template Version  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `create_template_version_api_v1_templates__template_id__versions_post`  

**Purpose**:
Creates a new immutable snapshot of the template document and bumps revision.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `template_id` | path | string | Yes | Target Video Template UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Short-lived access token for browser EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `CreateTemplateVersionRequest`
- `document` (object) *(required)* — Validated template document with scenes, layers, placeholders

**Responses**:
- **HTTP 201** — Model: `TemplateVersionResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `template_id` (string) *(required)*
- `revision` (integer) *(required)*
- `document` (object) *(required)*
- `created_by` (string) *(required)*
- `created_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 409`: `CONCURRENCY_CONFLICT` (revision mismatch under OCC)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 85. `GET` /api/v1/templates/{template_id}/versions/{version_id}
**Summary**: Get Template Version  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `get_template_version_api_v1_templates__template_id__versions__version_id__get`  

**Purpose**:
Fetches a specific immutable version snapshot by ID.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `template_id` | path | string | Yes | Target Video Template UUID |
| `version_id` | path | string | Yes | Target Template Version UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `TemplateVersionResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `template_id` (string) *(required)*
- `revision` (integer) *(required)*
- `document` (object) *(required)*
- `created_by` (string) *(required)*
- `created_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 409`: `CONCURRENCY_CONFLICT` (revision mismatch under OCC)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

## Brand Kits & Terminology Glossaries
*Total Endpoints: 17*

### 86. `GET` /api/v1/brand-glossaries
**Summary**: List Glossaries  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `list_glossaries_api_v1_brand_glossaries_get`  

**Purpose**:
Lists all active glossaries in the workspace.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `limit` | query | integer | No |  |
| `offset` | query | integer | No |  |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `array`: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 87. `POST` /api/v1/brand-glossaries
**Summary**: Create Glossary  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `create_glossary_api_v1_brand_glossaries_post`  

**Purpose**:
Creates a new terminology glossary in the workspace.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Short-lived access token for browser EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `CreateBrandGlossaryRequest`
- `name` (string) *(required)* — Glossary display name
- `description` (object) *(optional)*
- `brand_kit_id` (object) *(optional)* — Optional parent brand kit relationship
- `status` (object) *(optional)*, default: `active`

**Responses**:
- **HTTP 201** — Model: `BrandGlossaryResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `workspace_id` (string) *(required)*
- `brand_kit_id` (object) *(optional)*
- `created_by` (string) *(required)*
- `name` (string) *(required)*
- `description` (object) *(optional)*
- `status` (string) *(required)*
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 88. `DELETE` /api/v1/brand-glossaries/{glossary_id}
**Summary**: Delete Glossary  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `delete_glossary_api_v1_brand_glossaries__glossary_id__delete`  

**Purpose**:
Soft-deletes a glossary.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `glossary_id` | path | string | Yes | Target Brand Glossary UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 204**: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 89. `GET` /api/v1/brand-glossaries/{glossary_id}
**Summary**: Get Glossary  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `get_glossary_api_v1_brand_glossaries__glossary_id__get`  

**Purpose**:
Fetches a glossary and its rules by ID.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `glossary_id` | path | string | Yes | Target Brand Glossary UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `BrandGlossaryResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `workspace_id` (string) *(required)*
- `brand_kit_id` (object) *(optional)*
- `created_by` (string) *(required)*
- `name` (string) *(required)*
- `description` (object) *(optional)*
- `status` (string) *(required)*
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 90. `PATCH` /api/v1/brand-glossaries/{glossary_id}
**Summary**: Update Glossary  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `update_glossary_api_v1_brand_glossaries__glossary_id__patch`  

**Purpose**:
Updates glossary name, status, or description.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `glossary_id` | path | string | Yes | Target Brand Glossary UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `UpdateBrandGlossaryRequest`
- `name` (object) *(optional)*
- `description` (object) *(optional)*
- `brand_kit_id` (object) *(optional)*
- `status` (object) *(optional)*

**Responses**:
- **HTTP 200** — Model: `BrandGlossaryResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `workspace_id` (string) *(required)*
- `brand_kit_id` (object) *(optional)*
- `created_by` (string) *(required)*
- `name` (string) *(required)*
- `description` (object) *(optional)*
- `status` (string) *(required)*
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 91. `GET` /api/v1/brand-glossaries/{glossary_id}/rules
**Summary**: List Glossary Rules  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `list_glossary_rules_api_v1_brand_glossaries__glossary_id__rules_get`  

**Purpose**:
Lists terminology substitution rules in a glossary.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `glossary_id` | path | string | Yes | Target Brand Glossary UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `array`: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 92. `POST` /api/v1/brand-glossaries/{glossary_id}/rules
**Summary**: Create Glossary Rule  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `create_glossary_rule_api_v1_brand_glossaries__glossary_id__rules_post`  

**Purpose**:
Adds a new terminology substitution rule to a glossary.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `glossary_id` | path | string | Yes | Target Brand Glossary UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `CreateBrandGlossaryRuleRequest`
- `source_term` (object) *(optional)* — Term to match
- `preferred_term` (object) *(optional)* — Approved or phonetic replacement
- `forbidden_term` (object) *(optional)*
- `source_language` (object) *(optional)*, default: `en`
- `target_language` (object) *(optional)*
- `case_sensitive` (object) *(optional)*, default: `False`
- `status` (object) *(optional)*, default: `active`
- `term` (object) *(optional)*
- `replacement` (object) *(optional)*
- `phonetic_spelling` (object) *(optional)*
- `rule_type` (object) *(optional)*

**Responses**:
- **HTTP 201** — Model: `BrandGlossaryRuleResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `glossary_id` (string) *(required)*
- `source_term` (string) *(required)*
- `preferred_term` (string) *(required)*
- `forbidden_term` (object) *(optional)*
- `source_language` (string) *(required)*
- `target_language` (object) *(optional)*
- `case_sensitive` (boolean) *(required)*
- `status` (string) *(required)*
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
- `term` (string) *(required)*
- `replacement` (string) *(required)*
- `phonetic_spelling` (string) *(required)*
- `rule_type` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 93. `DELETE` /api/v1/brand-glossaries/{glossary_id}/rules/{rule_id}
**Summary**: Delete Glossary Rule (Nested)  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `delete_glossary_rule_nested_api_v1_brand_glossaries__glossary_id__rules__rule_id__delete`  

**Purpose**:
Deletes a terminology rule under a glossary.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `glossary_id` | path | string | Yes | Target Brand Glossary UUID |
| `rule_id` | path | string | Yes | Target Brand Glossary Rule UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 204**: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 94. `DELETE` /api/v1/brand-glossary-rules/{rule_id}
**Summary**: Delete Glossary Rule  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `delete_glossary_rule_api_v1_brand_glossary_rules__rule_id__delete`  

**Purpose**:
Deletes a terminology rule.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `rule_id` | path | string | Yes | Target Brand Glossary Rule UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 204**: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 95. `PATCH` /api/v1/brand-glossary-rules/{rule_id}
**Summary**: Update Glossary Rule  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `update_glossary_rule_api_v1_brand_glossary_rules__rule_id__patch`  

**Purpose**:
Updates a terminology rule.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `rule_id` | path | string | Yes | Target Brand Glossary Rule UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `UpdateBrandGlossaryRuleRequest`
- `source_term` (object) *(optional)*
- `preferred_term` (object) *(optional)*
- `forbidden_term` (object) *(optional)*
- `source_language` (object) *(optional)*
- `target_language` (object) *(optional)*
- `case_sensitive` (object) *(optional)*
- `status` (object) *(optional)*
- `term` (object) *(optional)*
- `replacement` (object) *(optional)*
- `phonetic_spelling` (object) *(optional)*
- `rule_type` (object) *(optional)*

**Responses**:
- **HTTP 200** — Model: `BrandGlossaryRuleResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `glossary_id` (string) *(required)*
- `source_term` (string) *(required)*
- `preferred_term` (string) *(required)*
- `forbidden_term` (object) *(optional)*
- `source_language` (string) *(required)*
- `target_language` (object) *(optional)*
- `case_sensitive` (boolean) *(required)*
- `status` (string) *(required)*
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
- `term` (string) *(required)*
- `replacement` (string) *(required)*
- `phonetic_spelling` (string) *(required)*
- `rule_type` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 96. `GET` /api/v1/brand-kits
**Summary**: List Brand Kits  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `list_brand_kits_api_v1_brand_kits_get`  

**Purpose**:
Lists active brand kits in the workspace.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `limit` | query | integer | No |  |
| `offset` | query | integer | No |  |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `array`: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 97. `POST` /api/v1/brand-kits
**Summary**: Create Brand Kit  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `create_brand_kit_api_v1_brand_kits_post`  

**Purpose**:
Registers a new workspace brand identity guideline kit.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Short-lived access token for browser EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `CreateBrandKitRequest`
- `name` (string) *(required)* — Brand kit display name
- `description` (object) *(optional)*
- `logo_asset_id` (object) *(optional)*
- `colors` (object) *(optional)*
- `typography` (object) *(optional)*
- `settings` (object) *(optional)*
- `is_default` (object) *(optional)*, default: `False`
- `primary_color` (object) *(optional)*
- `accent_color` (object) *(optional)*
- `secondary_color` (object) *(optional)*
- `font_family` (object) *(optional)*

**Responses**:
- **HTTP 201** — Model: `BrandKitResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `workspace_id` (string) *(required)*
- `created_by` (string) *(required)*
- `name` (string) *(required)*
- `description` (object) *(optional)*
- `logo_asset_id` (object) *(optional)*
- `colors` (object) *(optional)*
- `typography` (object) *(optional)*
- `settings` (object) *(optional)*
- `is_default` (boolean) *(optional)*, default: `False`
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
- `primary_color` (object) *(required)*
- `accent_color` (object) *(required)*
- `secondary_color` (object) *(required)*
- `font_family` (object) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 98. `DELETE` /api/v1/brand-kits/{brand_kit_id}
**Summary**: Delete Brand Kit  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `delete_brand_kit_api_v1_brand_kits__brand_kit_id__delete`  

**Purpose**:
Soft-deletes a brand kit.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `brand_kit_id` | path | string | Yes | Target Brand Kit UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 204**: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 99. `GET` /api/v1/brand-kits/{brand_kit_id}
**Summary**: Get Brand Kit  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `get_brand_kit_api_v1_brand_kits__brand_kit_id__get`  

**Purpose**:
Fetches a brand kit by ID.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `brand_kit_id` | path | string | Yes | Target Brand Kit UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `BrandKitResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `workspace_id` (string) *(required)*
- `created_by` (string) *(required)*
- `name` (string) *(required)*
- `description` (object) *(optional)*
- `logo_asset_id` (object) *(optional)*
- `colors` (object) *(optional)*
- `typography` (object) *(optional)*
- `settings` (object) *(optional)*
- `is_default` (boolean) *(optional)*, default: `False`
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
- `primary_color` (object) *(required)*
- `accent_color` (object) *(required)*
- `secondary_color` (object) *(required)*
- `font_family` (object) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 100. `PATCH` /api/v1/brand-kits/{brand_kit_id}
**Summary**: Update Brand Kit  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `update_brand_kit_api_v1_brand_kits__brand_kit_id__patch`  

**Purpose**:
Updates brand kit colors, typography, or logo asset.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `brand_kit_id` | path | string | Yes | Target Brand Kit UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `UpdateBrandKitRequest`
- `name` (object) *(optional)*
- `description` (object) *(optional)*
- `logo_asset_id` (object) *(optional)*
- `colors` (object) *(optional)*
- `typography` (object) *(optional)*
- `settings` (object) *(optional)*
- `is_default` (object) *(optional)*
- `primary_color` (object) *(optional)*
- `accent_color` (object) *(optional)*
- `secondary_color` (object) *(optional)*
- `font_family` (object) *(optional)*

**Responses**:
- **HTTP 200** — Model: `BrandKitResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `workspace_id` (string) *(required)*
- `created_by` (string) *(required)*
- `name` (string) *(required)*
- `description` (object) *(optional)*
- `logo_asset_id` (object) *(optional)*
- `colors` (object) *(optional)*
- `typography` (object) *(optional)*
- `settings` (object) *(optional)*
- `is_default` (boolean) *(optional)*, default: `False`
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
- `primary_color` (object) *(required)*
- `accent_color` (object) *(required)*
- `secondary_color` (object) *(required)*
- `font_family` (object) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 101. `GET` /api/v1/brand-kits/{brand_kit_id}/glossaries
**Summary**: List Brand Kit Glossaries  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `list_brand_kit_glossaries_api_v1_brand_kits__brand_kit_id__glossaries_get`  

**Purpose**:
Lists glossaries associated with a specific brand kit.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `brand_kit_id` | path | string | Yes | Target Brand Kit UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `array`: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 102. `POST` /api/v1/brand-kits/{brand_kit_id}/glossaries
**Summary**: Create Brand Kit Glossary  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `create_brand_kit_glossary_api_v1_brand_kits__brand_kit_id__glossaries_post`  

**Purpose**:
Creates a new terminology glossary bound to a brand kit.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `brand_kit_id` | path | string | Yes | Target Brand Kit UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Short-lived access token for browser EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `CreateBrandGlossaryRequest`
- `name` (string) *(required)* — Glossary display name
- `description` (object) *(optional)*
- `brand_kit_id` (object) *(optional)* — Optional parent brand kit relationship
- `status` (object) *(optional)*, default: `active`

**Responses**:
- **HTTP 201** — Model: `BrandGlossaryResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `workspace_id` (string) *(required)*
- `brand_kit_id` (object) *(optional)*
- `created_by` (string) *(required)*
- `name` (string) *(required)*
- `description` (object) *(optional)*
- `status` (string) *(required)*
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

## Jobs & Real-time SSE Streaming
*Total Endpoints: 6*

### 103. `GET` /api/v1/jobs
**Summary**: List Jobs  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `list_jobs_api_v1_jobs_get`  

**Purpose**:
List background jobs in the current workspace with optional type and status filtering.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `job_type` | query | string | No | Filter by workload type |
| `status` | query | string | No | Filter by job status |
| `limit` | query | integer | No |  |
| `offset` | query | integer | No |  |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `array`: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 104. `POST` /api/v1/jobs
**Summary**: Submit Job  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `submit_job_api_v1_jobs_post`  

**Purpose**:
Enqueue an asynchronous task pipeline job with optional idempotency key.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Short-lived access token for browser EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `JobSubmitRequest`
- `job_type` (string) *(required)* — Type of workload: render_video, tts_synthesis, lip_sync, translate_project, voice_clone, avatar_train
- `payload` (object) *(optional)* — Parameters, configuration, and inputs required for the worker task
- `priority` (integer) *(optional)*, default: `10` — Queue priority score (higher executes first)
- `idempotency_key` (object) *(optional)* — Client-supplied idempotency key to prevent duplicate job creation
- `max_retries` (integer) *(optional)*, default: `3` — Maximum retry attempts on transient failure

**Responses**:
- **HTTP 201** — Model: `JobResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `workspace_id` (string) *(required)*
- `created_by` (string) *(required)*
- `job_type` (string) *(required)*
- `status` (string) *(required)*
- `priority` (integer) *(required)*
- `idempotency_key` (object) *(optional)*
- `progress_percent` (integer) *(required)*
- `stage` (object) *(optional)*
- `stage_message` (object) *(optional)*
- `payload` (object) *(required)*
- `result` (object) *(optional)*
- `error_details` (object) *(optional)*
- `celery_task_id` (object) *(optional)*
- `retry_count` (integer) *(required)*
- `max_retries` (integer) *(required)*
- `started_at` (object) *(optional)*
- `completed_at` (object) *(optional)*
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 105. `GET` /api/v1/jobs/{job_id}
**Summary**: Get Job  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `get_job_api_v1_jobs__job_id__get`  

**Purpose**:
Fetch a job by ID within the active workspace.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `job_id` | path | string | Yes | Target Asynchronous Job UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `JobResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `workspace_id` (string) *(required)*
- `created_by` (string) *(required)*
- `job_type` (string) *(required)*
- `status` (string) *(required)*
- `priority` (integer) *(required)*
- `idempotency_key` (object) *(optional)*
- `progress_percent` (integer) *(required)*
- `stage` (object) *(optional)*
- `stage_message` (object) *(optional)*
- `payload` (object) *(required)*
- `result` (object) *(optional)*
- `error_details` (object) *(optional)*
- `celery_task_id` (object) *(optional)*
- `retry_count` (integer) *(required)*
- `max_retries` (integer) *(required)*
- `started_at` (object) *(optional)*
- `completed_at` (object) *(optional)*
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 106. `POST` /api/v1/jobs/{job_id}/cancel
**Summary**: Cancel Job  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `cancel_job_api_v1_jobs__job_id__cancel_post`  

**Purpose**:
Cancel a running or queued job and revoke the associated Celery task.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `job_id` | path | string | Yes | Target Asynchronous Job UUID |
| `reason` | query | string | No | Cancellation reason |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `JobCancelResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `job_id` (string) *(required)*
- `status` (string) *(required)*
- `message` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 107. `GET` /api/v1/jobs/{job_id}/events
**Summary**: Get Job Audit Events  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `get_job_events_api_v1_jobs__job_id__events_get`  

**Purpose**:
Retrieve chronological lifecycle and progress events for a job.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `job_id` | path | string | Yes | Target Asynchronous Job UUID |
| `limit` | query | integer | No |  |
| `offset` | query | integer | No |  |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `array`: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 108. `GET` /api/v1/jobs/{job_id}/stream
**Summary**: Stream Job Progress (SSE)  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `stream_job_progress_api_v1_jobs__job_id__stream_get`  

**Purpose**:
Subscribe to live real-time Server-Sent Events (SSE) updates for a job via Redis Pub/Sub.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `job_id` | path | string | Yes | Target Asynchronous Job UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200**: Real-time Server-Sent Events (SSE) stream yielding live job progress and transition events.
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

## Developer API Keys & Webhooks
*Total Endpoints: 11*

### 109. `GET` /api/v1/workspaces/{workspace_id}/developer/api-keys
**Summary**: List Developer API Keys  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `list_api_keys_api_v1_workspaces__workspace_id__developer_api_keys_get`  

**Purpose**:
List all developer API keys for the workspace. Never exposes plaintext secrets or hashes.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `limit` | query | integer | No |  |
| `offset` | query | integer | No |  |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `ApiKeyListResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `items` (array) *(required)*
  - *Item properties:*
    - `id` (string) *(required)*
    - `workspace_id` (string) *(required)*
    - `name` (string) *(required)*
    - `prefix` (string) *(required)*
    - `environment` (string) *(required)*
    - `permissions` (string) *(required)*
    - `status` (string) *(required)*
    - `expires_at` (object) *(optional)*
    - `last_used_at` (object) *(optional)*
    - `created_at` (string) *(required)*
- `total` (integer) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 110. `POST` /api/v1/workspaces/{workspace_id}/developer/api-keys
**Summary**: Create Developer API Key  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `create_api_key_api_v1_workspaces__workspace_id__developer_api_keys_post`  

**Purpose**:
Generate a new workspace developer API key. Plaintext secret is returned ONCE.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `ApiKeyCreateRequest`
- `name` (string) *(required)* — Label for the API key
- `environment` (string) *(optional)*, default: `production` — Target environment
- `permissions` (string) *(optional)*, default: `full` — Permission scope
- `expires_in_days` (object) *(optional)* — Optional key lifetime in days

**Responses**:
- **HTTP 201** — Model: `ApiKeyCreatedResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `workspace_id` (string) *(required)*
- `name` (string) *(required)*
- `prefix` (string) *(required)*
- `secret_key` (string) *(required)* — Full secret key. This value is never shown again.
- `environment` (string) *(required)*
- `permissions` (string) *(required)*
- `status` (string) *(required)*
- `expires_at` (object) *(optional)*
- `created_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 111. `DELETE` /api/v1/workspaces/{workspace_id}/developer/api-keys/{key_id}
**Summary**: Revoke Developer API Key  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `revoke_api_key_api_v1_workspaces__workspace_id__developer_api_keys__key_id__delete`  

**Purpose**:
Revoke an API key. Once revoked, it can no longer authenticate.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `key_id` | path | string | Yes | Target Developer API Key UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `ApiKeyResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `workspace_id` (string) *(required)*
- `name` (string) *(required)*
- `prefix` (string) *(required)*
- `environment` (string) *(required)*
- `permissions` (string) *(required)*
- `status` (string) *(required)*
- `expires_at` (object) *(optional)*
- `last_used_at` (object) *(optional)*
- `created_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 112. `GET` /api/v1/workspaces/{workspace_id}/developer/api-keys/{key_id}
**Summary**: Get Developer API Key  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `get_api_key_api_v1_workspaces__workspace_id__developer_api_keys__key_id__get`  

**Purpose**:
Retrieve safe metadata for a specific API key.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `key_id` | path | string | Yes | Target Developer API Key UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `ApiKeyResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `workspace_id` (string) *(required)*
- `name` (string) *(required)*
- `prefix` (string) *(required)*
- `environment` (string) *(required)*
- `permissions` (string) *(required)*
- `status` (string) *(required)*
- `expires_at` (object) *(optional)*
- `last_used_at` (object) *(optional)*
- `created_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 113. `GET` /api/v1/workspaces/{workspace_id}/developer/webhooks
**Summary**: List Webhooks  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `list_webhooks_api_v1_workspaces__workspace_id__developer_webhooks_get`  

**Purpose**:
List all registered webhooks for the workspace.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `status` | query | string | No |  |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `WebhookListResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `items` (array) *(required)*
  - *Item properties:*
    - `id` (string) *(required)*
    - `workspace_id` (string) *(required)*
    - `url` (string) *(required)*
    - `events` (array) *(required)*
    - `status` (string) *(required)*
    - `description` (object) *(optional)*
    - `failure_count` (integer) *(required)*
    - `created_at` (string) *(required)*
    - `updated_at` (string) *(required)*
- `total` (integer) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 114. `POST` /api/v1/workspaces/{workspace_id}/developer/webhooks
**Summary**: Register Webhook Endpoint  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `create_webhook_api_v1_workspaces__workspace_id__developer_webhooks_post`  

**Purpose**:
Register a new webhook endpoint. Plaintext signing secret is returned ONCE.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `WebhookCreateRequest`
- `url` (string) *(required)* — Destination HTTP/HTTPS URL
- `events` (array) *(optional)* — Subscribed event types
- `description` (object) *(optional)* — Optional description

**Responses**:
- **HTTP 201** — Model: `WebhookCreatedResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `workspace_id` (string) *(required)*
- `url` (string) *(required)*
- `secret` (string) *(required)* — HMAC-SHA256 signing secret. Store securely.
- `events` (array) *(required)*
- `status` (string) *(required)*
- `description` (object) *(optional)*
- `created_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 115. `DELETE` /api/v1/workspaces/{workspace_id}/developer/webhooks/{webhook_id}
**Summary**: Delete / Revoke Webhook  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `delete_webhook_api_v1_workspaces__workspace_id__developer_webhooks__webhook_id__delete`  

**Purpose**:
Revoke and soft-delete a registered webhook endpoint.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `webhook_id` | path | string | Yes | Target Webhook Subscription UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 204**: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 116. `GET` /api/v1/workspaces/{workspace_id}/developer/webhooks/{webhook_id}
**Summary**: Get Webhook  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `get_webhook_api_v1_workspaces__workspace_id__developer_webhooks__webhook_id__get`  

**Purpose**:
Retrieve webhook metadata.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `webhook_id` | path | string | Yes | Target Webhook Subscription UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `WebhookResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `workspace_id` (string) *(required)*
- `url` (string) *(required)*
- `events` (array) *(required)*
- `status` (string) *(required)*
- `description` (object) *(optional)*
- `failure_count` (integer) *(required)*
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 117. `PATCH` /api/v1/workspaces/{workspace_id}/developer/webhooks/{webhook_id}
**Summary**: Update Webhook  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `update_webhook_api_v1_workspaces__workspace_id__developer_webhooks__webhook_id__patch`  

**Purpose**:
Update destination URL, event subscriptions, or description.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `webhook_id` | path | string | Yes | Target Webhook Subscription UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `WebhookUpdateRequest`
- `url` (object) *(optional)* — New destination URL
- `events` (object) *(optional)* — Updated event subscriptions
- `status` (object) *(optional)* — Endpoint state
- `description` (object) *(optional)* — Updated description

**Responses**:
- **HTTP 200** — Model: `WebhookResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `workspace_id` (string) *(required)*
- `url` (string) *(required)*
- `events` (array) *(required)*
- `status` (string) *(required)*
- `description` (object) *(optional)*
- `failure_count` (integer) *(required)*
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 118. `GET` /api/v1/workspaces/{workspace_id}/developer/webhooks/{webhook_id}/deliveries
**Summary**: List Webhook Deliveries  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `list_webhook_deliveries_api_v1_workspaces__workspace_id__developer_webhooks__webhook_id__deliveries_get`  

**Purpose**:
Retrieve delivery attempt history and latency metrics for a webhook.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `webhook_id` | path | string | Yes | Target Webhook Subscription UUID |
| `limit` | query | integer | No |  |
| `offset` | query | integer | No |  |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `WebhookDeliveryListResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `items` (array) *(required)*
  - *Item properties:*
    - `id` (string) *(required)*
    - `webhook_id` (string) *(required)*
    - `event_id` (string) *(required)*
    - `event_type` (string) *(required)*
    - `payload` (object) *(required)*
    - `response_status_code` (object) *(optional)*
    - `response_body` (object) *(optional)*
    - `latency_ms` (object) *(optional)*
    - `status` (string) *(required)*
    - `attempt` (integer) *(required)*
    - `error_message` (object) *(optional)*
    - `created_at` (string) *(required)*
- `total` (integer) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 119. `POST` /api/v1/workspaces/{workspace_id}/developer/webhooks/{webhook_id}/test
**Summary**: Trigger Test Webhook Ping  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `test_webhook_api_v1_workspaces__workspace_id__developer_webhooks__webhook_id__test_post`  

**Purpose**:
Dispatch a signed test event to the registered webhook endpoint.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `webhook_id` | path | string | Yes | Target Webhook Subscription UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `WebhookTestResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `status` (string) *(optional)*, default: `enqueued` — Dispatch status of the test ping
- `event_id` (string) *(required)* — Unique test event identifier
- `destination_url` (string) *(required)* — Target webhook URL receiving the ping event
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

## Ask Rhys AI Copilot
*Total Endpoints: 2*

### 120. `POST` /api/v1/ask-rhys/chat
**Summary**: Query AskRhys AI Copilot Direct Chat  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `ask_rhys_direct_api_v1_ask_rhys_chat_post`  

**Purpose**:
Direct endpoint for conversational queries directed to Rhys AI Copilot using X-Workspace-ID header.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `X-Request-ID` | header | string | No |  |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `AskRhysRequest`
- `message` (string) *(required)* — User's prompt or question for AskRhys.
- `project_id` (object) *(optional)* — Optional active project ID for project-aware context.
- `conversation_id` (object) *(optional)* — Optional client conversation tracking identifier.
- `context_mode` (string) *(optional)*, default: `general` — Context modes supported by AskRhys.
- `history` (object) *(optional)* — Bounded conversational history from client (up to 6 previous messages).

**Responses**:
- **HTTP 200** — Model: `AskRhysResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `conversation_id` (string) *(required)* — Conversation session identifier.
- `message` (string) *(required)* — Echo of user's query prompt.
- `response` (string) *(required)* — Truthful response generated by local Qwen 2.5 0.5B ONNX CPU model.
- `context_used` (boolean) *(optional)*, default: `False` — Whether active project context was incorporated into inference.
- `provider` (string) *(optional)*, default: `qwen` — AI provider name that generated the response.
- `model` (string) *(optional)*, default: `llm/qwen-2.5-0.5b-cpu` — Specific model identifier used.
- `latency_ms` (number) *(required)* — End-to-end inference and orchestration latency in milliseconds.
- `suggestions` (array) *(optional)* — Follow-up quick reply suggestions or prompt tips.
- `actions` (array) *(optional)* — Non-mutating project edit recommendations proposed for explicit user review.
  - *Item properties:*
    - `type` (string) *(optional)*, default: `project_edit_suggestion` — Discriminator tag for client-side suggestion handling.
    - `operation` (string) *(required)* — Suggested operation name (e.g., 'update_scene_script', 'adjust_duration', 'suggest_visual').
    - `scene_id` (object) *(optional)* — Scene identifier if suggestion targets a specific scene.
    - `reason` (string) *(required)* — Explanation of why this edit improves the video.
    - `proposed_value` (object) *(required)* — Proposed replacement value or structured parameters.
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 121. `POST` /api/v1/workspaces/{workspace_id}/ask-rhys
**Summary**: Query AskRhys AI Copilot  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `ask_rhys_api_v1_workspaces__workspace_id__ask_rhys_post`  

**Purpose**:
Executes truthful conversational inference via the local CPU Qwen 2.5 0.5B ONNX model. Enforces workspace isolation, rate limiting, and returns non-mutating project suggestions.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `X-Request-ID` | header | string | No |  |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `AskRhysRequest`
- `message` (string) *(required)* — User's prompt or question for AskRhys.
- `project_id` (object) *(optional)* — Optional active project ID for project-aware context.
- `conversation_id` (object) *(optional)* — Optional client conversation tracking identifier.
- `context_mode` (string) *(optional)*, default: `general` — Context modes supported by AskRhys.
- `history` (object) *(optional)* — Bounded conversational history from client (up to 6 previous messages).

**Responses**:
- **HTTP 200** — Model: `AskRhysResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `conversation_id` (string) *(required)* — Conversation session identifier.
- `message` (string) *(required)* — Echo of user's query prompt.
- `response` (string) *(required)* — Truthful response generated by local Qwen 2.5 0.5B ONNX CPU model.
- `context_used` (boolean) *(optional)*, default: `False` — Whether active project context was incorporated into inference.
- `provider` (string) *(optional)*, default: `qwen` — AI provider name that generated the response.
- `model` (string) *(optional)*, default: `llm/qwen-2.5-0.5b-cpu` — Specific model identifier used.
- `latency_ms` (number) *(required)* — End-to-end inference and orchestration latency in milliseconds.
- `suggestions` (array) *(optional)* — Follow-up quick reply suggestions or prompt tips.
- `actions` (array) *(optional)* — Non-mutating project edit recommendations proposed for explicit user review.
  - *Item properties:*
    - `type` (string) *(optional)*, default: `project_edit_suggestion` — Discriminator tag for client-side suggestion handling.
    - `operation` (string) *(required)* — Suggested operation name (e.g., 'update_scene_script', 'adjust_duration', 'suggest_visual').
    - `scene_id` (object) *(optional)* — Scene identifier if suggestion targets a specific scene.
    - `reason` (string) *(required)* — Explanation of why this edit improves the video.
    - `proposed_value` (object) *(required)* — Proposed replacement value or structured parameters.
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---



---




# Part IV: Developer Setup & Operations Guide


# HeyZen Developer Setup & Operations Guide

This guide provides complete, step-by-step instructions for provisioning, running, configuring, and verifying the HeyZen autonomous AI video platform on Windows, macOS, and Linux.

---

## 1. System Prerequisites

The following software binaries and runtimes must be installed on your workstation:

| Component | Verified Version | Purpose | Download / Command |
|---|---|---|---|
| **Node.js** | `v24.13.1` (or >= 20.x) | Next.js frontend runtime | [nodejs.org](https://nodejs.org/) (`node -v`) |
| **npm** | `11.11.1` (or >= 10.x) | Frontend package manager | Bundled with Node (`npm -v`) |
| **Python** | `3.13.7` (or >= 3.11.x) | Backend API & Celery worker runtime | [python.org](https://python.org/) (`python -V`) |
| **Docker Desktop** | `29.7.2` (or >= 24.x) | Container runtime for Postgres, Redis, MinIO | [docker.com](https://www.docker.com/) (`docker --version`) |
| **FFmpeg** | `9.0.1-essentials` | Media decoding, scaling, filtergraphs & MP4 assembly | [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) (`ffmpeg -version`) |
| **FFprobe** | `9.0.1-essentials` | Audio/video metadata extraction & validation | Bundled with FFmpeg (`ffprobe -version`) |
| **Google Chrome** | Latest Stable | Used as the browser channel for Playwright E2E tests | [google.com/chrome](https://www.google.com/chrome/) |
| **NVIDIA CUDA** *(Optional)* | CUDA `12.4.1` + Driver >= 550 | GPU-accelerated diffusion & neural avatar generation | Optional; CPU mode fully supported |

> [!NOTE]
> If a dedicated NVIDIA GPU is not detected or CUDA packages are omitted, HeyZen operates deterministically in **CPU Mode** using faster-whisper, Piper TTS, Kokoro ONNX, CTranslate2, and CPU Wav2Lip fallback.

---

## 2. Windows Quick-Start Setup

Execute the following commands in PowerShell from the repository root (`D:\HeyGen\video-ai-tools`):

### Step 1: Frontend Dependency Installation
```powershell
# Install Node dependencies
npm install
```

### Step 2: Python Virtual Environment & Backend Dependencies
```powershell
# Navigate into backend
cd backend

# Create dedicated virtual environment
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Upgrade pip
python -m pip install --upgrade pip

# Install CPU / core dependencies
pip install -r requirements.txt

# (Optional) If NVIDIA CUDA 12.4 is available and GPU workloads are required:
# pip install -r requirements-gpu.txt

cd ..
```

### Step 3: Infrastructure Services (PostgreSQL, Redis, MinIO)
Using Docker Compose:
```powershell
# Start PostgreSQL (5432), Redis (6379), and MinIO S3 (9000/9001)
docker compose up -d postgres redis minio
```

Verify that all three services report healthy:
```powershell
docker compose ps
```

*Port Mapping Table:*
- PostgreSQL: `127.0.0.1:5432`
- Redis: `127.0.0.1:6379`
- MinIO S3 API: `127.0.0.1:9000`
- MinIO Web Console: `127.0.0.1:9001` (User: `heyzen_admin`, Pass: `heyzen_dev_password123`)

---

## 3. Environment Variables Configuration

Copy `.env.example` to `.env` in the repository root:
```powershell
Copy-Item .env.example .env
```

### Environment Variables Inventory

| Variable | Purpose | Required | Default / Example | Format / Notes |
|---|---|---|---|---|
| `APP_ENV` | Environment classification | Yes | `development` | `development`, `test`, `production` |
| `APP_NAME` | Human-readable app name | No | `HeyZen Backend` | String |
| `APP_VERSION` | Application semantic version | No | `0.1.0` | SemVer string |
| `DEBUG` | Enable verbose logging & OpenAPI docs | No | `true` | Boolean (`true`/`false`) |
| `DATABASE_URL` | Async SQLAlchemy database URI | Yes | `postgresql+asyncpg://heyzen:heyzen_dev_password@127.0.0.1:5432/heyzen` | Must use `postgresql+asyncpg://` |
| `POSTGRES_DB` | PostgreSQL database name | No | `heyzen` | String |
| `POSTGRES_USER` | PostgreSQL user | No | `heyzen` | String |
| `POSTGRES_PASSWORD` | PostgreSQL password | Yes | `heyzen_dev_password` | Alphanumeric string |
| `REDIS_URL` | Redis URI for Celery broker & Pub/Sub | Yes | `redis://127.0.0.1:6379/0` | URI string |
| `MINIO_ENDPOINT` | MinIO / S3 object storage endpoint | Yes | `http://127.0.0.1:9000` | HTTP URL |
| `MINIO_ROOT_USER` | MinIO admin user | Yes | `heyzen_admin` | String |
| `MINIO_ROOT_PASSWORD` | MinIO admin password | Yes | `heyzen_dev_password123` | Alphanumeric string |
| `MINIO_ACCESS_KEY` | MinIO access key identifier | Yes | `heyzen_admin` | String |
| `MINIO_SECRET_KEY` | MinIO secret access key | Yes | `heyzen_dev_password123` | Alphanumeric string |
| `MINIO_BUCKET` | Default media bucket name | No | `heyzen-assets` | Lowercase bucket identifier |
| `MINIO_REGION` | S3 region identifier | No | `us-east-1` | S3 region string |
| `JWT_SECRET_KEY` | Secret key for JWT HS256 signing | Yes | *(Dev placeholder in .env.example)* | >= 32 characters in production |
| `JWT_ALGORITHM` | JWT signing algorithm | No | `HS256` | Must be `HS256` |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifespan | No | `15` | Integer minutes |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token lifespan | No | `7` | Integer days |
| `CORS_ORIGINS` | Comma-separated allowed web origins | Yes | `http://localhost:3000,http://127.0.0.1:3000` | URLs without wildcards |
| `COOKIE_SECURE` | HTTPS flag for refresh cookie | No | `false` (True in prod) | Boolean |
| `COOKIE_SAMESITE` | SameSite cookie policy | No | `lax` | `lax`, `strict`, `none` |
| `AI_PROVIDER_MODE` | AI Provider adapter mode | No | `mock` (`real` for production) | `mock` or `real` |
| `AI_RUNTIME_MODE` | AI hardware execution mode | No | `mock` (`real` for production) | `mock` or `real` |
| `AI_PREFERRED_DEVICE` | Compute device selection | No | `auto` | `auto`, `cpu`, `cuda` |
| `AI_MODEL_CACHE_DIR` | Local disk cache for models | No | `models_cache` | Path relative or absolute |
| `AI_MAX_CPU_MEMORY_MB` | Maximum CPU RAM for AI models | No | `4096` | Integer megabytes |
| `AI_MAX_GPU_MEMORY_MB` | Maximum GPU VRAM for models | No | `0` (or VRAM in MB) | Integer megabytes |
| `AI_ALLOW_AUTO_DOWNLOAD` | Permit automatic weights download | No | `false` | Boolean |
| `AI_VERIFY_CHECKSUMS` | Strict SHA-256 model verification | No | `true` | Boolean |
| `FFMPEG_PATH` | Path to FFmpeg binary | No | `ffmpeg` | Binary name or absolute path |
| `FFPROBE_PATH` | Path to FFprobe binary | No | `ffprobe` | Binary name or absolute path |
| `MEDIA_TIMEOUT_SECONDS` | Max duration per media subprocess | No | `300` | Integer seconds |
| `MAX_VIDEO_DURATION_SECONDS` | Max video duration ceiling | No | `3600.0` (1 hour) | Float seconds |
| `MIN_VIDEO_DURATION_SECONDS` | Minimum video duration floor | No | `5.0` | Float seconds |
| `NEXT_PUBLIC_API_URL` | Frontend API backend origin | Yes | `http://127.0.0.1:8000` | HTTP URL |

---

## 4. Database Migrations & Seeds

With PostgreSQL running, execute Alembic migrations to construct the database schema:

```powershell
cd backend
.\.venv\Scripts\alembic.exe upgrade head
cd ..
```

*Expected Output:*
```text
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_initial_user_schema
INFO  [alembic.runtime.migration] Running upgrade 0001_initial_user_schema -> 0002_workspaces_and_auth
INFO  [alembic.runtime.migration] Running upgrade 0002_workspaces_and_auth -> 0003_projects_folders_assets
INFO  [alembic.runtime.migration] Running upgrade 0003_projects_folders_assets -> 0004_creative_library
INFO  [alembic.runtime.migration] Running upgrade 0004_creative_library -> 0005_jobs_and_task_pipeline
INFO  [alembic.runtime.migration] Running upgrade 0005_jobs_and_task_pipeline -> 0006_api_keys_and_webhooks
```

### Seeding Presets & Development Fixtures
When the FastAPI backend starts up in `development` mode, it automatically executes:
1. `seed_canonical_presets()`: Seeds 6 canonical avatars (Annie, Marcus, Serena, Alex, Elena, David) and 6 Piper TTS voices.
2. `seed_development_fixtures()`: Creates standard development user `dev@heyzen.ai` (`DevPassword123!`) and default workspace `Default Workspace`.

---

## 5. Starting the Development Stack

To run the complete interactive platform, launch three terminal windows:

### Terminal 1: FastAPI API Gateway
```powershell
cd D:\HeyGen\video-ai-tools\backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
- Swagger UI Documentation: `http://127.0.0.1:8000/docs`
- ReDoc Documentation: `http://127.0.0.1:8000/redoc`
- Health Probe: `http://127.0.0.1:8000/health`

### Terminal 2: Celery Asynchronous Media & AI Worker
> [!IMPORTANT]
> On Windows, Celery's default `prefork` execution pool causes `ValueError` or silent crashes. Always specify `-P solo` or `--pool=threads` when running on Windows!

```powershell
cd D:\HeyGen\video-ai-tools\backend
.\.venv\Scripts\Activate.ps1
celery -A app.workers.celery_app worker -Q cpu_media,maintenance --loglevel=info -P solo
```

### Terminal 3: Next.js Frontend Application
```powershell
cd D:\HeyGen\video-ai-tools
npm run dev
```
- Application Web Interface: `http://127.0.0.1:3000` (or `http://localhost:3000`)

---

## 6. Running Test Suites

### 1. Frontend Unit Tests (Fast & Deterministic)
Executes native Node test runner on all 89 test suites in `src/lib/*.test.ts`:
```powershell
npm test
```
*Current Verification*: **353 tests passing** (0 failures, duration ~2.1s).

### 2. Backend Unit & Contract Tests
Executes Pytest in the Python virtual environment:
```powershell
cd backend
.\.venv\Scripts\pytest.exe tests/test_config.py tests/test_ai_contracts.py tests/test_flexible_video_durations.py
cd ..
```
*Current Verification*: Config, Pydantic schemas, and flexible video durations pass synchronously.

### 3. Playwright End-to-End Smoke Tests
HeyZen utilizes Playwright configured with the system Google Chrome binary to eliminate flaky multi-hundred-megabyte browser binary downloads.

**Playwright Chrome Channel Configuration** (`playwright.config.ts`):
```typescript
use: {
  baseURL: "http://localhost:3000",
  channel: "chrome",
  headless: true,
}
```

**Running E2E Smoke Tests**:
```powershell
# Ensure Terminal 1 (FastAPI) and Terminal 3 (Next.js) are running, then:
npx playwright test tests/e2e/smoke.spec.ts
```

**Running Auth Persistence Tests**:
```powershell
npx playwright test tests/e2e/auth-persistence.spec.ts
```

---

## 7. Troubleshooting Guide

| Symptom / Error | Root Cause | Verification Check | Recommended Fix |
|---|---|---|---|
| `botocore.exceptions.EndpointConnectionError: Could not connect to http://127.0.0.1:9000` | MinIO object storage container is stopped | Run `docker compose ps` | Start MinIO with `docker compose up -d minio` |
| `ValueError: Unsupported schema_version: X. Expected 1.` | Project JSON document version mismatch | Check `document["schema_version"]` | Must always be integer `1` |
| `Revision conflict: current revision is X, but requested Y` | Optimistic Concurrency Control (OCC) collision | Inspect `project.revision` vs `expected_revision` | Re-fetch the latest `current_version_id` and document before submitting modifications |
| `Celery: PermissionError / ValueError on Windows` | Celery prefork pool incompatible with Windows OS | Review Celery startup command | Append `-P solo` to the Celery command: `celery -A app.workers.celery_app worker -P solo` |
| `CORS Error: Response to preflight request doesn't pass access control check` | Client origin not included in `CORS_ORIGINS` | Check `CORS_ORIGINS` in `.env` | Add `http://localhost:3000,http://127.0.0.1:3000` without trailing slashes |
| `JWT_SECRET_KEY must be a cryptographically strong secret in production` | Production fail-closed check caught insecure secret | Inspect `APP_ENV` and `JWT_SECRET_KEY` | Set a unique random secret of >= 32 characters in production |
| `Playwright: Executable doesn't exist at C:\Users\...\AppData\Local\ms-playwright\chromium` | Playwright browser download skipped or blocked | Check `playwright.config.ts` | Verify `channel: "chrome"` is active in `playwright.config.ts` so system Chrome is utilized |
| `Theme flicker / Flash of dark theme before light applies` | Theme script ran after hydration | Inspect `<head>` in `src/app/layout.tsx` | Ensure the inline `<script>` in `<head>` reads `localStorage.getItem('vidoai_theme')` and sets `classList.add('light')` |
| `FFmpeg: filter 'xfade' not found or unknown option` | Outdated FFmpeg binary (< version 4.3) | Run `ffmpeg -version` | Install FFmpeg version 6.x, 7.x, 8.x, or 9.x |

---

## 8. Production Multi-Container Deployment

In production environments, HeyZen deploys via `docker-compose.prod.yml` with strict resource limits and automated health checks:

```powershell
docker compose -f docker-compose.prod.yml up -d --build
```

### Production Topology Architecture:
1. **`postgres`** (PostgreSQL 16-alpine): 2 CPUs, 4GB RAM ceiling, persistent volume `heyzen_postgres_data`.
2. **`redis`** (Redis 7-alpine): 1 CPU, 1.5GB RAM ceiling, append-only persistence `heyzen_redis_data`.
3. **`minio`** (MinIO S3): 1.5 CPUs, 2GB RAM ceiling, persistent bucket storage `heyzen_minio_data`.
4. **`api`** (FastAPI Gateway): 4 CPUs, 4GB RAM ceiling, Uvicorn production server.
5. **`cpu-worker`** (Celery CPU media compositor & local AI): 4 CPUs, 6GB RAM ceiling, mounted `heyzen_models_cache`.
6. **`nginx`** (Reverse Proxy & SSL Termination): 1 CPU, 512MB RAM ceiling, HTTP/2 + SSE unbuffered streaming.



---




# Part V: Implementation Status Matrix & Verification


# HeyZen Current Implementation Status & Verification Matrix

*Repository*: `D:\HeyGen\video-ai-tools`  
*Current Codebase Version*: `0.1.0`  
*Audit Date*: September 2026  
*Status*: Active Development & Hardening  

This document provides a factual, truth-in-code assessment of the HeyZen platform. Features are classified strictly according to actual implementation in the repository without speculation.

---

## 1. Subsystem Implementation Status Matrix

| Subsystem / Area | Implemented | Verified | Classification | Limitations & Technical Notes |
|---|---|---|---|---|
| **Authentication** | Yes | Yes | Production-Ready | JWT HS256 + HttpOnly refresh cookie (`hz_refresh_token`). Refresh rotation with SHA-256 session hashing in `user_sessions`. Verified via 119-line Playwright test `auth-persistence.spec.ts`. Demo credentials `dev@heyzen.ai` available in development mode only. |
| **Global Theme** | Yes | Yes | Production-Ready | Dark/light theme toggle via `ThemeContext`. Stored in `localStorage.vidoai_theme`. Pre-hydration `<script>` in `layout.tsx` eliminates flash of unstyled content (FOUC). Verified in E2E smoke tests. |
| **Dashboard** | Yes | Yes | Production-Ready | Multi-view SPA shell (`DashboardContent`). Navigation rail (`LeftRailNav`), contextual sidebars, onboarding prompts, and video blueprints. |
| **Projects & OCC** | Yes | Yes | Production-Ready | Projects and immutable `ProjectVersion` snapshots in PostgreSQL. Monotonically increasing revision counter enforces integer Optimistic Concurrency Control (OCC). 409 Conflict returned on stale revisions. |
| **Video Agent** | Yes | Yes | Production-Ready | Natural language prompt decomposition into multi-scene projects. Dynamic duration selector (15s to 10m+). Asynchronous Celery execution, SSE progress streaming, and draft project preview cards. |
| **Studio Document Engine** | Yes | Yes | Production-Ready | Full interactive canvas document engine (`ProjectDocumentV1`). Schema validated with Pydantic v2. Multi-layer composition across scenes and audio tracks. |
| **Studio Interactive Canvas** | Yes | Yes | Production-Ready | Direct manipulation gizmo (`CanvasTransformGizmo`), multi-layer selection, boundary edge snapping (`studioCanvasSnapping.ts`), rotation, and resize handles. |
| **Studio Timeline** | Yes | Yes | Production-Ready | Multi-track timeline: clips, audio, speech, captions, and elements. Supports drag-move, left/right trim, cut/split, zoom scaling, horizontal panning, and clip snapping. Verified via 35 unit tests in Phase 43. |
| **Studio Text & Typography** | Yes | Yes | Production-Ready | Text layer insertion, font family, font size, bold/normal, hex colors, background fill, opacity, and rotation. Rasterized via Pillow and OpenCV in compositor. |
| **Studio Captions / Subtitles** | Yes | Yes | Production-Ready | Word-level and segment-level subtitle cues. Customizable typography, placement (top/center/bottom), and background box opacity. Burned into MP4 during composite render. |
| **Studio Elements & Shapes** | Yes | Yes | Production-Ready | Vector rectangles, rounded boxes, circles, arrows, stars, badges, and stickers. Rendered into RGBA overlays via OpenCV and Pillow. |
| **Studio Music & Media** | Yes | Yes | Production-Ready | Media layers (images, b-roll video) and audio tracks (narration + background music). Real-time FFmpeg `amix` filtergraph with volume attenuation and fade-in/out. |
| **Studio History (Undo/Redo)** | Yes | Yes | Production-Ready | Robust undo/redo command stack (`studioHistory.ts`). Preserves exact document tree and OCC revision markers. Verified by 15 dedicated unit tests. |
| **Studio Keyboard Shortcuts** | Yes | Yes | Production-Ready | Space (Play/Pause), Backspace/Delete (Remove), Ctrl+Z / Cmd+Z (Undo), Ctrl+Shift+Z (Redo), Arrow Keys (1px nudge), Shift+Arrow (10px nudge), Esc (Deselect). |
| **Studio Layout & Panes** | Yes | Yes | Production-Ready | Draggable resize handles for Left Sidebar, Right Inspector, and Bottom Timeline. Fullscreen API integration with Escape key listener. Verified in Playwright smoke test. |
| **Studio Render Pipeline** | Yes | Yes | Production-Ready | Generate button triggers pre-flight timeline diagnostics, freezes revision, and dispatches Celery `render_video` task. Composits scenes with FFmpeg into 1080p MP4. |
| **Avatars & Digital Twins** | Yes | Yes | Production-Ready | Database catalog with public and workspace-scoped avatars. Presets seeded (Annie, Marcus, Serena, Alex, Elena, David). Annie selected as default presenter. Custom avatar training supported via Celery. |
| **Voices & Voice Cloning** | Yes | Yes | Production-Ready | Piper neural TTS integration across 6 canonical presets. OpenVoice v2 zero-shot instant voice cloning endpoint (`/workspaces/{id}/voices/clone`). Audio preview playback verified. |
| **Multi-Language Translation** | Yes | Yes | Production-Ready | Ingests video uploads, YouTube/GDrive URLs, or projects. Extracts audio -> faster-whisper ASR -> CTranslate2 translation with Brand Glossary rules -> Piper TTS speech synthesis -> localized ProjectVersion. |
| **Brand Systems & Glossaries** | Yes | Yes | Production-Ready | Brand kits (colors, typography, logo assets) and Brand Glossaries (`brand_glossaries`, `brand_glossary_rules`). Enforces terminology during translation and Video Agent generation. |
| **Asynchronous Jobs & Celery** | Yes | Yes | Production-Ready | Celery 5.4 multi-queue topology (`cpu_media`, `gpu_ai`, `maintenance`). Redis 7 broker and Pub/Sub event broadcasting. Real-time SSE streaming endpoint (`/jobs/{id}/stream`). |
| **Developer API & Webhooks** | Yes | Yes | Production-Ready | Scoped developer API keys (prefix `hz_live_...`, SHA-256 hashed secret). Webhook subscription management with HMAC SHA-256 signature verification (`X-HeyZen-Signature`) and delivery audit history. |
| **MinIO Object Storage** | Yes | Yes | Production-Ready | S3-compatible MinIO object storage. Workspace-partitioned keys (`workspaces/{ws_id}/assets/{asset_id}/...`). Direct pre-signed upload intents and verification. |
| **E2E Playwright Automation** | Yes | Yes | Production-Ready | Automated smoke tests (`tests/e2e/smoke.spec.ts`) and auth persistence tests (`tests/e2e/auth-persistence.spec.ts`). Configured with `channel: "chrome"` for deterministic execution. |
| **Production Deployment** | Yes | Yes | Production-Ready | Multi-container Docker Compose (`docker-compose.prod.yml`) with PostgreSQL 16, Redis 7, MinIO, API Gateway, Celery CPU worker, and Nginx reverse proxy with resource constraints. |
| **Neural Diffusion (Stable Diffusion / MuseTalk)** | Partial | GPU-Dependent | Conditional | Real adapters implemented (`musetalk.py`, `stable_diffusion.py`), but requires discrete NVIDIA GPU with CUDA 12.4 and model weights in `models_cache`. CPU hosts automatically fallback to Wav2Lip or mock mode without crashing. |
| **DeepFilterNet3 Audio Enhancement** | Partial | Partial | Experimental | Neural audio noise suppression and speech mastering implemented in `audio_enhance.py`. Falls back to SciPy spectral gating and RNNoise when neural weights are unpopulated. |
| **Third-Party SSO (OAuth / Google)** | No | No | Planned | Architectural scaffolding present in `UserCredential`, but currently only local email/password authentication is active in routes. |

---

## 2. Test Verification Summary

### Frontend Unit & Contract Test Suite
- **Command**: `npm test` (`npx tsx --test src/lib/*.test.ts`)
- **Total Test Suites**: 89
- **Total Tests**: **353**
- **Pass Rate**: **100% (353 passed, 0 failed, 0 skipped)**
- **Execution Time**: ~2.1 seconds
- **Key Suites Verified**:
  - `videoAgentWorkspace.test.ts` (Presenter selection, Annie default, duration scaling, error states)
  - `timelineEditing.test.ts` & `timelineResizeControls.test.ts` (Clip resizing, trimming, snapping, split)
  - `studioHistory.test.ts` (Undo/Redo stack preservation, OCC revision tracking)
  - `canvasTransformUtils.test.ts` & `studioCanvasSnapping.test.ts` (Matrix transforms, edge snapping)
  - `multiSelection.test.ts` & `multiSelectionInspector.test.ts` (Multi-layer selection, bounding box)
  - `studioLockingVisibility.test.ts` (Lock and visibility state isolation)
  - `brandSystems.test.ts` & `translateVideos.test.ts` (Glossary enforcement, language registries)
  - `authPersistence.test.ts` & `themeAndLoginRedirect.test.ts` (Token persistence, theme switching)

### Backend Pytest Suite
- **Command**: `pytest` (`backend\.venv\Scripts\pytest.exe`)
- **Total Test Files**: 120 files in `backend/tests`
- **Verified Components**:
  - `test_config.py`: Fail-closed production settings validation (100% pass)
  - `test_ai_contracts.py`: Pydantic V2 AI adapter schemas and device descriptors (100% pass)
  - `test_project_document.py`: Schema validation, defaults factory, JSONB serialization (100% pass)
  - `test_flexible_video_durations.py`: Duration scaling, scene count planning, boundary enforcement (100% pass)
  - `test_studio_locking_visibility.py`: Layer locking, disabled layers exclusion from compositor (100% pass)
  - `test_media_filters.py`: FFmpeg filtergraph construction, scale2ref, circular masks, xfade transitions (100% pass)
  - *Live Media Ingestion Tests*: Require running MinIO instance on port 9000; fail gracefully with `EndpointConnectionError` if MinIO container is not started.

### Playwright End-to-End Suite
- **Test Specs**:
  - `tests/e2e/smoke.spec.ts`: Full UI smoke suite (Brand Systems, Projects, AI Agent, Studio, Generate button, resize handles, Fullscreen API, theme switching)
  - `tests/e2e/auth-persistence.spec.ts`: Sign up -> Home redirect -> Reload -> Token refresh -> Logout -> Login

---

## 3. Real Milestone & Change History

Based on historical milestone reports in `docs/`:

- **Phase 1–5**: Initial workspace multi-tenancy, PostgreSQL database schema, Argon2id credentials, and Alembic migrations.
- **Phase 6–7**: Real media rendering engine (`TimelineCompositor`), FFmpeg subprocess wrappers, and MinIO asset lifecycle.
- **Phase 8–10**: Celery task queue routing (`cpu_media`, `gpu_ai`, `maintenance`), Redis Pub/Sub, and Server-Sent Events (SSE).
- **Phase 11–13.5**: Frontend-backend integration, Next.js API client (`src/lib/api.ts`), and unified error handling (`APIErrorResponse`).
- **Phase 14–16**: GPU hardware probes (`hardware.py`), CUDA detection, fail-safe memory guards, and `GPU_REQUIRED` graceful fallback.
- **Phase 17–20**: Voice cloning (`OpenVoice v2`), neural speech enhancement (`audio_enhance.py`), and Brand Glossary enforcement during translation.
- **Phase 28–32**: Interactive Studio canvas controls, element library (shapes, stickers), text overlays, and cross-type layer ordering.
- **Phase 33–36**: Advanced interactive timeline: zoom scaling, horizontal panning, clip-to-clip snapping, and split/trim editing.
- **Phase 37–41**: Studio undo/redo history stack (`studioHistory.ts`), keyboard shortcuts, and optimistic concurrency control (OCC).
- **Phase 42a–42c**: Studio render parity: burned captions, text rotation, scene transition rendering (`xfade`), and audio normalization.
- **Phase 43–45**: Multi-layer selection inspector, alignment/distribution tools, dynamic duration selector (15s–10m+), and complete Swagger path parameter hardening.



---

