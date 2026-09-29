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
