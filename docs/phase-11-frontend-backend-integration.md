# HeyZen Phase 11 — Frontend ↔ Backend Integration Contract

## 1. Overview & System Invariants

This document specifies the concrete end-to-end integration contracts between the existing canonical HeyZen Next.js frontend (`src/`) and the production FastAPI + PostgreSQL + Redis + MinIO + Celery backend (`backend/`).

### Canonical System Constraints
1. **Frontend UI is FROZEN**: No modifications to colors, typography, sizing, spacing, layouts, animations, navigation, sidebars, buttons, or component hierarchy.
2. **File Freeze**: No new npm dependencies. Native `fetch` with `credentials: "include"` is used throughout.
3. **Database Schema Freeze**: Alembic migration head remains strictly `0005_jobs_task_pipeline`. No new migrations.
4. **Authoritative Source of Truth**: PostgreSQL + MinIO + Redis are authoritative. Frontend is a client presentation and interaction layer.
5. **No Fake AI Success / No Fake GPU**: Hardware on development machine is CPU-only (AMD Ryzen). Workloads requiring CUDA (MuseTalk, etc.) return genuine `GPU_UNAVAILABLE` errors to the UI. No fake success states or mock fallbacks are introduced.
6. **Optimistic Concurrency Control (OCC)**: ProjectDocument updates require matching `expected_revision`. Stale revision errors (409 Conflict) are handled with user notifications and reload offers without silently overwriting.

---

## 2. API Client Architecture (`src/lib/api.ts`)

A unified, typed API client is established in `src/lib/api.ts` adhering to the following rules:
- **Base URL**: Configured via `process.env.NEXT_PUBLIC_API_URL` (default fallback `http://127.0.0.1:8000`).
- **Authentication**: Stores the access token in memory. Includes `Authorization: Bearer <access_token>` on authenticated endpoints.
- **Cookies**: Sets `credentials: "include"` on all requests so that the backend HttpOnly refresh cookie (`heyzen_refresh_token` scoped to `/api/v1/auth`) is automatically sent and received by the browser.
- **Automatic Token Refresh**: Intercepts `401 Unauthorized` responses and attempts a single token rotation via `POST /api/v1/auth/refresh`. If refresh succeeds, the pending request is retried with the new token. If refresh fails, session is cleared and the user is redirected to login.
- **Request Tracking**: Attaches unique `X-Request-ID` header to all outgoing requests.
- **Error Normalization**: Maps backend `APIErrorResponse` (`{ error: { code, message, request_id, details } }`) to structured TypeScript errors.
- **Real-Time Job Streaming**: Provides an `api.jobs.stream(jobId, onEvent, onError)` helper utilizing Server-Sent Events (SSE) via `EventSource` with connection lifecycle management and automatic cleanup.

---

## 3. End-to-End Integration Matrix

### 3.1 Authentication

#### 1. User Registration (Signup)
- **Frontend Operation**: User fills in name, email, and password on `AuthPage.tsx` and submits.
- **Frontend File & Component**: `src/components/auth/AuthPage.tsx` (`handleSubmit`), calling `signup()` from `src/context/AuthContext.tsx`.
- **Backend Endpoint**: `POST /api/v1/auth/signup`
- **HTTP Method**: `POST`
- **Request Schema**:
  ```json
  {
    "email": "user@example.com",
    "password": "SecurePassword123!",
    "display_name": "Full Name"
  }
  ```
- **Response Schema**:
  ```json
  {
    "user": {
      "id": "uuid",
      "email": "user@example.com",
      "display_name": "Full Name",
      "is_active": true,
      "created_at": "timestamp"
    },
    "workspace": {
      "id": "uuid",
      "name": "Personal Workspace",
      "slug": "personal-workspace",
      "role": "owner"
    },
    "tokens": {
      "access_token": "jwt_string",
      "token_type": "bearer",
      "expires_in_seconds": 900
    }
  }
  ```
- **Authentication Requirement**: Public (No auth header required).
- **Workspace Requirement**: None (Creates initial default personal workspace atomically).
- **Cookie Side-Effect**: Backend sets HttpOnly `heyzen_refresh_token` cookie (path: `/api/v1/auth`).
- **State Update**:
  - `access_token` stored in memory.
  - `user` set to `{ id, name: display_name, email, avatarInitial, role: "owner", plan: "Pro Creator", credits: 1000, maxCredits: 1000 }`.
  - `currentWorkspace` set to returned workspace.
  - `isAuthenticated = true`, `isLoading = false`.
- **Error Behavior**:
  - `409 Conflict` (`USER_ALREADY_EXISTS`): Displays "Email already registered" in UI form.
  - `422 Validation Error`: Highlights field validation error (e.g. password length).

#### 2. User Login
- **Frontend Operation**: User enters email & password or clicks 1-Click Demo Login.
- **Frontend File & Component**: `src/components/auth/AuthPage.tsx` (`handleSubmit` / `handleDemoLogin`), calling `login()` from `src/context/AuthContext.tsx`.
- **Backend Endpoint**: `POST /api/v1/auth/login`
- **HTTP Method**: `POST`
- **Request Schema**:
  ```json
  {
    "email": "user@example.com",
    "password": "UserPassword123!"
  }
  ```
- **Response Schema**: Same as `AuthResponse` above.
- **Authentication Requirement**: Public.
- **Workspace Requirement**: None (Loads active workspace membership).
- **Cookie Side-Effect**: Backend sets HttpOnly `heyzen_refresh_token` cookie.
- **State Update**: Updates `access_token`, `user`, `currentWorkspace`, and sets `isAuthenticated = true`.
- **Error Behavior**:
  - `401 Unauthorized` (`INVALID_CREDENTIALS`): Displays "Invalid email or password" error banner on `AuthPage`.

#### 3. Session Initialization & Current User Hydration
- **Frontend Operation**: Page loads or browser refreshes (`src/context/AuthContext.tsx` `useEffect`).
- **Frontend File & Component**: `src/context/AuthContext.tsx`.
- **Backend Endpoint**:
  1. `POST /api/v1/auth/refresh` (sends HttpOnly cookie via `credentials: "include"`).
  2. `GET /api/v1/auth/me` with `Authorization: Bearer <access_token>`.
- **HTTP Methods**: `POST`, then `GET`.
- **Request Schemas**: Empty body (relies on HttpOnly cookie).
- **Response Schema (`/me`)**:
  ```json
  {
    "user": {
      "id": "uuid",
      "email": "user@example.com",
      "display_name": "Full Name",
      "is_active": true
    },
    "workspaces": [
      {
        "id": "uuid",
        "name": "My Workspace",
        "slug": "my-workspace",
        "role": "owner"
      }
    ]
  }
  ```
- **Authentication Requirement**: Refresh uses HttpOnly cookie; `/me` requires `access_token`.
- **State Update**:
  - If valid: Hydrates `user`, `workspaces`, selects first workspace as `currentWorkspace`, sets `isAuthenticated = true`, `isLoading = false`.
  - If invalid/expired: Clears state, sets `user = null`, `isAuthenticated = false`, `isLoading = false` (presents `AuthPage`).

#### 4. Session Rotation (Refresh)
- **Frontend Operation**: Triggered when `api.ts` intercepts a `401 Unauthorized` response or during session restore.
- **Backend Endpoint**: `POST /api/v1/auth/refresh`
- **HTTP Method**: `POST`
- **Request Schema**: Optional `{ "refresh_token": string }` (primary transport is HttpOnly cookie).
- **Response Schema**: `AuthResponse`.
- **State Update**: Rotates memory `access_token`, updates cookie.

#### 5. User Logout
- **Frontend Operation**: User clicks "Sign Out / Log Out" in `UserMenuDropdown.tsx`.
- **Frontend File & Component**: `src/components/dashboard/UserMenuDropdown.tsx` calling `logout()` in `AuthContext.tsx`.
- **Backend Endpoint**: `POST /api/v1/auth/logout`
- **HTTP Method**: `POST`
- **Authentication Requirement**: Sends HttpOnly cookie (`credentials: "include"`).
- **Response Schema**: `{ "status": "ok", "message": "Logged out successfully." }`.
- **Cookie Side-Effect**: Backend clears `heyzen_refresh_token` cookie.
- **State Update**: Clears memory tokens, resets `user = null`, `isAuthenticated = false`.

---

### 3.2 Workspace Integration

#### 1. List Workspaces
- **Frontend Operation**: Loading available workspaces for account menu or switching.
- **Frontend File & Component**: `src/context/AuthContext.tsx` and `src/components/dashboard/UserMenuDropdown.tsx`.
- **Backend Endpoint**: `GET /api/v1/workspaces`
- **HTTP Method**: `GET`
- **Response Schema**:
  ```json
  [
    {
      "id": "uuid",
      "name": "Workspace Name",
      "slug": "workspace-name",
      "owner_id": "uuid",
      "status": "active",
      "role": "owner",
      "created_at": "timestamp"
    }
  ]
  ```
- **Authentication Requirement**: Required (`Authorization: Bearer <access_token>`).

#### 2. Create Workspace
- **Frontend Operation**: Creating an additional workspace.
- **Backend Endpoint**: `POST /api/v1/workspaces`
- **HTTP Method**: `POST`
- **Request Schema**: `{ "name": "New Team Workspace" }`
- **Response Schema**: `WorkspaceResponse`.
- **State Update**: Appends new workspace to `workspaces` list in state and sets as `currentWorkspace`.

---

### 3.3 Projects & Studio Integration

#### 1. List Workspace Projects
- **Frontend Operation**: Opening Projects tab in navigation rail or sidebar.
- **Frontend File & Component**: `src/components/projects/ProjectsManager.tsx` and `src/components/apps/TranslateVideos.tsx`.
- **Backend Endpoint**: `GET /api/v1/workspaces/{workspace_id}/projects`
- **Query Parameters**: `folder_id`, `filter_folder`, `status`, `search`, `limit`, `offset`.
- **HTTP Method**: `GET`
- **Response Schema**:
  ```json
  [
    {
      "id": "uuid",
      "workspace_id": "uuid",
      "folder_id": "uuid | null",
      "created_by": "uuid",
      "title": "Project Title",
      "project_type": "standard",
      "status": "draft",
      "aspect_ratio": "16:9",
      "width": 1920,
      "height": 1080,
      "fps": 30,
      "duration_ms": 46000,
      "current_version_id": "uuid",
      "revision": 1,
      "created_at": "timestamp",
      "updated_at": "timestamp"
    }
  ]
  ```
- **Authentication Requirement**: Required.
- **Workspace Requirement**: Active workspace UUID in URL path.
- **State Update**: Maps items into `ProjectItem[]` displayed in List, Grid, and Date views.

#### 2. Create Project
- **Frontend Operation**: "Create Project", "Create Sample Video", or template click.
- **Frontend File & Component**: `ProjectsManager.tsx` or `page.tsx`.
- **Backend Endpoint**: `POST /api/v1/workspaces/{workspace_id}/projects`
- **HTTP Method**: `POST`
- **Request Schema**:
  ```json
  {
    "title": "Untitled Video",
    "folder_id": null,
    "project_type": "standard",
    "aspect_ratio": "16:9",
    "width": 1920,
    "height": 1080,
    "fps": 30
  }
  ```
- **Response Schema**: `ProjectResponse`.
- **State Update**: Opens newly created project directly in Studio editor (`onOpenStudio(project.id)`).

#### 3. Open Project & Load Document in Studio
- **Frontend Operation**: Clicking on project row, card, or edit button.
- **Frontend File & Component**: `src/app/page.tsx` renders `<VidoAIStudio projectId={activeProjectId} />`.
- **Backend Endpoints**:
  1. `GET /api/v1/workspaces/{workspace_id}/projects/{project_id}`
  2. `GET /api/v1/workspaces/{workspace_id}/projects/{project_id}/versions/{current_version_id}`
- **HTTP Method**: `GET`
- **Response Schema**:
  ```json
  {
    "id": "uuid",
    "project_id": "uuid",
    "revision": 1,
    "document": {
      "schema_version": "1.0",
      "settings": {
        "title": "Project Title",
        "aspect_ratio": "16:9",
        "width": 1920,
        "height": 1080,
        "fps": 30,
        "total_duration": 46.0
      },
      "scenes": [...],
      "tracks": [...]
    },
    "source": "initial",
    "created_at": "timestamp"
  }
  ```
- **State Update**: Studio state hydrated with `ProjectDocumentV1`: title, aspect ratio, duration, scenes, active revision.

#### 4. Save Project Document (Optimistic Concurrency Control)
- **Frontend Operation**: Clicking "Save" or auto-save debounce in Studio.
- **Frontend File & Component**: `src/components/studio/VidoAIStudio.tsx`.
- **Backend Endpoint**: `POST /api/v1/workspaces/{workspace_id}/projects/{project_id}/versions`
- **HTTP Method**: `POST`
- **Request Schema**:
  ```json
  {
    "expected_revision": 1,
    "document": { ...validated ProjectDocumentV1... },
    "source": "manual"
  }
  ```
- **Response Schema**: `ProjectVersionResponse` (with `revision: 2`).
- **State Update**: Updates Studio `revision = response.revision`, shows "Saved" indicator with green check.
- **Error Behavior**:
  - `409 Conflict` (`CONCURRENCY_CONFLICT`): Current revision is newer than `expected_revision`.
  - Action: Displays non-destructive warning dialog: "Project was modified in another session. Would you like to reload the latest version?"

#### 5. Rename / Update Project Metadata
- **Frontend Operation**: Editing title in Studio header or inline rename in ProjectsManager.
- **Backend Endpoint**: `PATCH /api/v1/workspaces/{workspace_id}/projects/{project_id}`
- **HTTP Method**: `PATCH`
- **Request Schema**: `{ "title": "Updated Title" }`
- **Response Schema**: `ProjectResponse`.

#### 6. Delete Project
- **Frontend Operation**: Clicking Trash icon on project card/row.
- **Backend Endpoint**: `DELETE /api/v1/workspaces/{workspace_id}/projects/{project_id}`
- **HTTP Method**: `DELETE`
- **Response**: `204 No Content`.
- **State Update**: Removes project from active project list in UI.

---

### 3.4 Folders Integration

#### 1. List Folders
- **Frontend File & Component**: `src/components/projects/CreateFolderModal.tsx` and `ProjectsManager.tsx`.
- **Backend Endpoint**: `GET /api/v1/workspaces/{workspace_id}/folders`
- **HTTP Method**: `GET`
- **Response Schema**: `List[FolderResponse]`.

#### 2. Create Folder
- **Frontend Operation**: Submitting folder name in `CreateFolderModal.tsx`.
- **Backend Endpoint**: `POST /api/v1/workspaces/{workspace_id}/folders`
- **HTTP Method**: `POST`
- **Request Schema**: `{ "name": "Marketing 2026", "parent_id": null }`
- **Response Schema**: `FolderResponse`.

---

### 3.5 Asset Management & MinIO Direct Upload

#### 1. Asset Upload Flow
- **Frontend Files & Components**:
  - `src/components/create/AttachAssetModal.tsx`
  - `src/components/apps/TranslateVideos.tsx` (drag-and-drop / file picker)
  - `src/components/avatars/DesignLookStudio.tsx`
- **Step 1: Create Upload Intent**:
  - Backend Endpoint: `POST /api/v1/workspaces/{workspace_id}/assets/upload-intents`
  - HTTP Method: `POST`
  - Request Schema:
    ```json
    {
      "original_filename": "clip.mp4",
      "mime_type": "video/mp4",
      "size_bytes": 10485760,
      "asset_type": "video"
    }
    ```
  - Response Schema:
    ```json
    {
      "asset_id": "uuid",
      "storage_bucket": "heyzen-assets",
      "storage_key": "workspaces/.../assets/uuid.mp4",
      "signed_upload_url": "http://127.0.0.1:9000/heyzen-assets/...",
      "expires_in_seconds": 900,
      "required_headers": { "Content-Type": "video/mp4" }
    }
    ```
- **Step 2: Direct Binary PUT to MinIO**:
  - Browser performs `fetch(signed_upload_url, { method: "PUT", headers: { "Content-Type": mime_type }, body: file })`.
  - Upload progress tracked via XHR or native fetch reader where supported.
- **Step 3: Confirm Upload**:
  - Backend Endpoint: `POST /api/v1/workspaces/{workspace_id}/assets/{asset_id}/confirm`
  - HTTP Method: `POST`
  - Response Schema:
    ```json
    {
      "asset_id": "uuid",
      "status": "ready",
      "size_bytes": 10485760,
      "mime_type": "video/mp4"
    }
    ```
- **Step 4: Get Download / Preview URL**:
  - Backend Endpoint: `GET /api/v1/workspaces/{workspace_id}/assets/{asset_id}/download`
  - HTTP Method: `GET`
  - Response Schema: `{ "asset_id": "uuid", "download_url": "...", "expires_in_seconds": 3600 }`.

---

### 3.6 AI Generation & Video Agent

#### 1. Generate Project from Natural Language Prompt
- **Frontend Operation**: User types prompt and clicks generate in `VideoAgent.tsx`.
- **Frontend File & Component**: `src/components/create/VideoAgent.tsx` (`handleFinalContinue`).
- **Backend Endpoint**: `POST /api/v1/workspaces/{workspace_id}/projects/generate`
- **HTTP Method**: `POST`
- **Request Schema**:
  ```json
  {
    "prompt": "Create a 30-second SaaS product launch video",
    "run_async": true,
    "target_duration_seconds": 30,
    "aspect_ratio": "16:9",
    "avatar_id": "annie",
    "voice_id": "en_us_female_1",
    "video_tone": "Professional",
    "auto_synthesize_speech": true
  }
  ```
- **Response Schema**: HTTP 202 `JobResponse` (`{ "id": "job_uuid", "status": "queued", "job_type": "generate_project" }`).
- **Real-Time Progress & SSE Flow**:
  - Frontend establishes SSE connection: `GET /api/v1/jobs/{job_id}/stream`.
  - Progress updates (`queued` -> `running` -> `progress_pct` -> `succeeded`) displayed in existing UI status toast/banner.
  - On `succeeded`: `job.result_payload["project_id"]` is retrieved, and Studio is opened for the new project.
  - On `failed`: Shows actual backend error message (`job.error_message`).

---

### 3.7 Speech Synthesis (TTS) & Subtitles (ASR)

#### 1. Synthesize Speech for Timeline Scenes
- **Frontend File & Component**: `src/components/studio/VidoAIStudio.tsx` (Voice tool).
- **Backend Endpoint**: `POST /api/v1/workspaces/{workspace_id}/projects/{project_id}/synthesize-speech`
- **HTTP Method**: `POST` (HTTP 202)
- **Request Schema**:
  ```json
  {
    "expected_revision": 1,
    "run_async": true,
    "scene_ids": ["scene_1"],
    "voice_id_override": "en_us_female_1"
  }
  ```
- **Response Schema**: `JobResponse`.
- **Progress Tracking**: Via SSE. On success, reloads latest version to update audio duration and waveforms.

#### 2. Transcribe Audio (ASR)
- **Frontend File & Component**: `src/components/studio/VidoAIStudio.tsx` (Captions tool).
- **Backend Endpoint**: `POST /api/v1/workspaces/{workspace_id}/projects/{project_id}/transcribe`
- **HTTP Method**: `POST` (HTTP 202)
- **Request Schema**: `{ "expected_revision": 1, "scene_id": "scene_1", "run_async": true }`
- **Response Schema**: `JobResponse`.

---

### 3.8 Video Translation

#### 1. Translate Project Scripts & Speech
- **Frontend File & Component**: `src/components/apps/TranslateVideos.tsx`.
- **Backend Endpoint**: `POST /api/v1/workspaces/{workspace_id}/projects/{project_id}/translate`
- **HTTP Method**: `POST` (HTTP 202)
- **Request Schema**:
  ```json
  {
    "target_language": "es",
    "source_language": "en",
    "target_voice_id": "es_es_female_1",
    "create_fork": true,
    "expected_revision": 1,
    "run_async": true
  }
  ```
- **Response Schema**: `JobResponse`.
- **Progress Tracking**: Via SSE `/api/v1/jobs/{job_id}/stream`. Progress bar displays percentage and stage.

---

### 3.9 Talking Avatar Video (MuseTalk / Wav2Lip)

#### 1. Synthesize Neural Talking Avatar
- **Frontend File & Component**: Studio Avatar tab or Avatar Generator.
- **Backend Endpoint**: `POST /api/v1/workspaces/{workspace_id}/projects/{project_id}/generate-avatar-video`
- **HTTP Method**: `POST` (HTTP 202)
- **Request Schema**:
  ```json
  {
    "expected_revision": 1,
    "scene_id": "scene_1",
    "avatar_id_override": "annie",
    "run_async": true
  }
  ```
- **CUDA Invariant Handling**:
  - When running on development machine (CPU-only), worker or API returns structured error `GPU_UNAVAILABLE`.
  - Frontend surfaces: "GPU Unavailable: Neural talking avatar generation requires dedicated NVIDIA CUDA hardware. Status: CUDA VALIDATION PENDING."
  - Does NOT fake success or silently fallback.

---

### 3.10 Video Rendering & Export

#### 1. Export Video Render
- **Frontend File & Component**: "Export" button in `src/components/studio/VidoAIStudio.tsx`.
- **Backend Endpoint**: `POST /api/v1/workspaces/{workspace_id}/projects/{project_id}/render`
- **HTTP Method**: `POST` (HTTP 202)
- **Request Schema**:
  ```json
  {
    "expected_revision": 1,
    "resolution": "1080p",
    "format": "mp4"
  }
  ```
- **Response Schema**: `JobResponse`.
- **Progress Tracking**:
  - SSE stream `/api/v1/jobs/{job_id}/stream` connected.
  - Studio Export button transitions to progress indicator showing exact stage: `queued` -> `rendering` -> `encoding` -> `uploading` -> `completed`.
  - On completion: `job.result_payload` provides output `video_asset_id` and download URL. User is provided direct preview and download link.

---

### 3.11 Creative Library Catalogs

#### 1. Avatars & Looks
- **Backend Endpoints**:
  - `GET /api/v1/avatars`
  - `GET /api/v1/avatars/{avatar_id}/looks`
- **Response**: `List[AvatarResponse]`, `List[AvatarLookResponse]`.
- **Used by**: `AvatarsManager.tsx`, `VideoAgent.tsx`, `DesignLookStudio.tsx`.

#### 2. Voices Catalog
- **Backend Endpoint**: `GET /api/v1/voices`
- **Query Parameters**: `language`, `gender`, `voice_type`, `search`.
- **Response**: `List[VoiceResponse]`.
- **Used by**: `VoicesLibrary.tsx`, Studio Voice panel.

#### 3. Video Templates
- **Backend Endpoint**: `GET /api/v1/templates`
- **Response**: `List[TemplateResponse]`.
- **Used by**: `TemplatesLibrary.tsx`, Home Page template cards.

---

## 4. Structured Error Handling Matrix

| HTTP Status | Error Code | Backend Condition | Frontend Handling |
| :--- | :--- | :--- | :--- |
| **401** | `UNAUTHORIZED` / `INVALID_CREDENTIALS` | Token expired or invalid credentials | Attempt refresh via cookie; if fails, clear session & present `AuthPage`. |
| **403** | `FORBIDDEN` / `WORKSPACE_ACCESS_DENIED` | User lacks role/permission in workspace | Surface permission notification; prevent forbidden action. |
| **404** | `NOT_FOUND` / `PROJECT_NOT_FOUND` | Resource does not exist | Show resource not found notification; return to dashboard. |
| **409** | `CONCURRENCY_CONFLICT` | Stale `expected_revision` on project save | Show conflict dialog; preserve unsaved edits in memory; offer to reload. |
| **422** | `VALIDATION_ERROR` | Request payload failed Pydantic validation | Display localized form field error messages without crashing. |
| **429** | `RATE_LIMIT_EXCEEDED` | Request rate exceeded tier limit | Read `Retry-After` header; disable button and show retry countdown. |
| **500** | `INTERNAL_SERVER_ERROR` | Unhandled server exception | Show standard toast: "Server error. Please try again." |
| **503 / 422** | `GPU_UNAVAILABLE` | Workload requires NVIDIA CUDA device | Display real status: "GPU Unavailable — CUDA Validation Pending". |

---

## 5. Security & Persistence Summary

1. **Storage of Tokens**:
   - `access_token`: Stored in application memory (`AuthContext` / `api.ts`), never in `localStorage`.
   - `refresh_token`: Maintained strictly in HttpOnly cookie `heyzen_refresh_token` set by FastAPI.
2. **Persistence in `localStorage`**:
   - Only non-sensitive presentation preferences remain in `localStorage` (e.g., `theme` dark/light, recent tab selection).
   - Mock user `vidoai_user` is removed from `localStorage`.
3. **Workspace Scoping**:
   - All tenant-scoped operations pass `{workspace_id}` in the path; backend enforces DB-level tenant isolation.
