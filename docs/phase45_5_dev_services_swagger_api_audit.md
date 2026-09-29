# Phase 45.5 — Development Environment & Swagger API Audit Report

## Executive Summary

This document records the full development services initialization, Swagger UI / OpenAPI verification, backend route inventory audit, Studio API surface mapping, and regression test results for Phase 45.5.

All infrastructure services (PostgreSQL, Redis, MinIO), FastAPI backend (:8000), Next.js frontend (:3000), and Swagger UI (`http://127.0.0.1:8000/docs`) are fully operational and kept running continuously.

## 1. Development Services & Infrastructure Status

| Service | Host / Port | Container / Process | Health Status | Verification Method |
| :--- | :--- | :--- | :--- | :--- |
| **Next.js Frontend** | `http://localhost:3000` | Node.js (v16.3.4 Turbopack) | **RUNNING (HTTP 200)** | HTTP GET probe (`http://localhost:3000`) |
| **FastAPI Backend** | `http://127.0.0.1:8000` | Uvicorn (`app.main:app`) | **RUNNING (HTTP 200)** | HTTP GET probe (`/health`, `/docs`) |
| **PostgreSQL** | `127.0.0.1:5432` | `heyzen-postgres` / Native | **RUNNING (TCP 5432)** | Socket TCP probe & DB connection |
| **Redis** | `127.0.0.1:6379` | `heyzen-redis` | **RUNNING (TCP 6379)** | Socket TCP probe & async connection |
| **MinIO S3 API** | `127.0.0.1:9000` | `heyzen-minio` | **RUNNING (TCP 9000)** | Socket TCP probe & S3 API probe |
| **MinIO Console** | `127.0.0.1:9001` | `heyzen-minio` | **RUNNING (TCP 9001)** | Socket TCP probe & Web console |


## 2. Swagger UI & OpenAPI Verification

- **Swagger UI URL:** `http://127.0.0.1:8000/docs` (HTTP 200)
- **OpenAPI JSON URL:** `http://127.0.0.1:8000/openapi.json` (HTTP 200)
- **ReDoc URL:** `http://127.0.0.1:8000/redoc` (HTTP 200)
- **Security Scheme:** `HTTPBearer` (Bearer JWT auth scheme enabled for all 105 protected endpoints, testable interactively via green 'Authorize' button)
- **Validation Results:**
  - Total OpenAPI Paths: 76
  - Total Documented Operations: 117
  - Duplicate Operation IDs: 0 (None)
  - Broken `$ref` References: 0 (None)
  - Missing Response Models (200/201/202/204): 0 (None)
  - Hidden Routes: 4 internal (`/docs`, `/docs/oauth2-redirect`, `/redoc`, and 1 intentionally hidden alias `POST /{project_id}/generate-avatar` for `generate-avatar-video`)


## 3. Studio API Architecture & Coverage Mapping

HeyZen Studio persists and executes all visual canvas operations through the canonical `ProjectDocumentV1` document versioning engine and domain orchestration endpoints:

| Studio Domain | Supported Operations | Backend Contract / Endpoint | Persistence / Execution |
| :--- | :--- | :--- | :--- |
| **Projects** | Create, Get, Update, Delete, List | `POST/GET/PATCH/DELETE /api/v1/workspaces/{id}/projects` | `ProjectResponse`, `ProjectCreate`, `ProjectUpdate` |
| **Versions & OCC** | List, Get, Save Snapshot | `POST/GET /api/v1/workspaces/{id}/projects/{id}/versions` | `CreateProjectVersionRequest` with `expected_revision` |
| **Scenes** | Create, Update, Delete, Reorder, Transitions | `ProjectDocumentV1.scenes` (`sequence`, `duration`, `transition: {type, duration}`) | Persisted via project version document snapshots |
| **Media Layers** | Add, Update, Delete, Transform, Reorder | `ProjectDocumentV1.scenes[].layers` (`type: 'image'/'video'`, `transform`, `content`) | Persisted via project version document snapshots |
| **Text Layers** | Add, Update, Delete, Style, Transform | `ProjectDocumentV1.scenes[].layers` (`type: 'text'`, `content: {text, fontSize, color, ...}`) | Persisted via project version document snapshots |
| **Element Layers** | Add, Update, Delete, Duplicate, Shapes/Stickers | `ProjectDocumentV1.scenes[].layers` (`type: 'shape'/'sticker'`, `content`) | Persisted via project version document snapshots |
| **Unified Ordering** | Visual Z-ordering across all types | `ProjectDocumentV1.scenes[].layers[].z_index` (Phase 42B unified stacking) | Persisted via project version document snapshots |
| **Locking & Visibility** | Lock, Unlock, Enable, Disable | `ProjectDocumentV1.scenes[].layers[].locked` & `enabled` (Phase 38/44) | Persisted via project version document snapshots |
| **Captions** | Subtitles, styling, positioning, burning | `ProjectDocumentV1.settings.captions` & `scenes[].subtitles` | `CaptionSettings`, `CaptionStyle`, `scenes[].subtitles` cues |
| **Audio Tracks** | Add, Update, Delete, Volume, Fade, Mute | `ProjectDocumentV1.audio_tracks` (`AudioTrack` schema) | Project-level audio timeline tracks |
| **Rendering & Export** | Composite render, preflight validation, status | `POST /projects/{id}/render`, `POST /projects/{id}/validate` | `JobResponse`, `TimelineValidationResponse` |
| **AI Speech & Voices** | TTS timeline synthesis, cloning | `POST /projects/{id}/synthesize-speech`, `POST /voices/clone` | `JobResponse`, `VoiceResponse` |
| **AI Avatars** | Talking avatar generation | `POST /projects/{id}/generate-avatar-video` | `JobResponse`, `ProjectVersionResponse` |
| **AI Localization** | Project translation & dubbing | `POST /projects/{id}/translate` | `JobResponse`, `ProjectResponse` |
| **AI Copilot** | Conversational assistance | `POST /workspaces/{id}/ask-rhys`, `POST /ask-rhys/chat` | `AskRhysResponse` |


## 4. Complete OpenAPI Route Inventory

Below is the complete inventory of all 117 operations registered in FastAPI and exposed in Swagger UI:

### API Keys (4 Operations)

| Method | Path | Auth Required | Request Model | Response Model | Implementation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/workspaces/{workspace_id}/developer/api-keys` | Yes (`HTTPBearer`) | — | `ApiKeyListResponse` | `unknown` |
| `POST` | `/api/v1/workspaces/{workspace_id}/developer/api-keys` | Yes (`HTTPBearer`) | `ApiKeyCreateRequest` | `ApiKeyCreatedResponse` | `unknown` |
| `DELETE` | `/api/v1/workspaces/{workspace_id}/developer/api-keys/{key_id}` | Yes (`HTTPBearer`) | — | `ApiKeyResponse` | `unknown` |
| `GET` | `/api/v1/workspaces/{workspace_id}/developer/api-keys/{key_id}` | Yes (`HTTPBearer`) | — | `ApiKeyResponse` | `unknown` |


### Ask Rhys AI (2 Operations)

| Method | Path | Auth Required | Request Model | Response Model | Implementation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/ask-rhys/chat` | Yes (`HTTPBearer`) | `AskRhysRequest` | `AskRhysResponse` | `unknown` |
| `POST` | `/api/v1/workspaces/{workspace_id}/ask-rhys` | Yes (`HTTPBearer`) | `AskRhysRequest` | `AskRhysResponse` | `unknown` |


### Assets (6 Operations)

| Method | Path | Auth Required | Request Model | Response Model | Implementation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/workspaces/{workspace_id}/assets` | Yes (`HTTPBearer`) | — | `array` | `unknown` |
| `POST` | `/api/v1/workspaces/{workspace_id}/assets/upload-intents` | Yes (`HTTPBearer`) | `AssetUploadIntentRequest` | `AssetUploadIntentResponse` | `unknown` |
| `DELETE` | `/api/v1/workspaces/{workspace_id}/assets/{asset_id}` | Yes (`HTTPBearer`) | — | `204 No Content` | `unknown` |
| `GET` | `/api/v1/workspaces/{workspace_id}/assets/{asset_id}` | Yes (`HTTPBearer`) | — | `AssetResponse` | `unknown` |
| `POST` | `/api/v1/workspaces/{workspace_id}/assets/{asset_id}/confirm` | Yes (`HTTPBearer`) | — | `AssetConfirmResponse` | `unknown` |
| `GET` | `/api/v1/workspaces/{workspace_id}/assets/{asset_id}/download` | Yes (`HTTPBearer`) | — | `AssetDownloadResponse` | `unknown` |


### Authentication (5 Operations)

| Method | Path | Auth Required | Request Model | Response Model | Implementation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/auth/login` | No (Public) | `LoginRequest` | `AuthResponse` | `unknown` |
| `POST` | `/api/v1/auth/logout` | No (Public) | `custom` | `object` | `unknown` |
| `GET` | `/api/v1/auth/me` | Yes (`HTTPBearer`) | — | `UserWithWorkspacesResponse` | `unknown` |
| `POST` | `/api/v1/auth/refresh` | No (Public) | `custom` | `AuthResponse` | `unknown` |
| `POST` | `/api/v1/auth/signup` | No (Public) | `SignupRequest` | `AuthResponse` | `unknown` |


### Avatars (10 Operations)

| Method | Path | Auth Required | Request Model | Response Model | Implementation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/avatars` | Yes (`HTTPBearer`) | — | `array` | `unknown` |
| `POST` | `/api/v1/avatars` | Yes (`HTTPBearer`) | `CreateAvatarRequest` | `AvatarResponse` | `unknown` |
| `DELETE` | `/api/v1/avatars/{avatar_id}` | Yes (`HTTPBearer`) | — | `204 No Content` | `unknown` |
| `GET` | `/api/v1/avatars/{avatar_id}` | Yes (`HTTPBearer`) | — | `AvatarResponse` | `unknown` |
| `PATCH` | `/api/v1/avatars/{avatar_id}` | Yes (`HTTPBearer`) | `UpdateAvatarRequest` | `AvatarResponse` | `unknown` |
| `GET` | `/api/v1/avatars/{avatar_id}/looks` | Yes (`HTTPBearer`) | — | `array` | `unknown` |
| `POST` | `/api/v1/avatars/{avatar_id}/looks` | Yes (`HTTPBearer`) | `CreateAvatarLookRequest` | `AvatarLookResponse` | `unknown` |
| `DELETE` | `/api/v1/avatars/{avatar_id}/looks/{look_id}` | Yes (`HTTPBearer`) | — | `204 No Content` | `unknown` |
| `GET` | `/api/v1/avatars/{avatar_id}/looks/{look_id}` | Yes (`HTTPBearer`) | — | `AvatarLookResponse` | `unknown` |
| `PATCH` | `/api/v1/avatars/{avatar_id}/looks/{look_id}` | Yes (`HTTPBearer`) | `UpdateAvatarLookRequest` | `AvatarLookResponse` | `unknown` |


### Brand Kits (17 Operations)

| Method | Path | Auth Required | Request Model | Response Model | Implementation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/brand-glossaries` | Yes (`HTTPBearer`) | — | `array` | `unknown` |
| `POST` | `/api/v1/brand-glossaries` | Yes (`HTTPBearer`) | `CreateBrandGlossaryRequest` | `BrandGlossaryResponse` | `unknown` |
| `DELETE` | `/api/v1/brand-glossaries/{glossary_id}` | Yes (`HTTPBearer`) | — | `204 No Content` | `unknown` |
| `GET` | `/api/v1/brand-glossaries/{glossary_id}` | Yes (`HTTPBearer`) | — | `BrandGlossaryResponse` | `unknown` |
| `PATCH` | `/api/v1/brand-glossaries/{glossary_id}` | Yes (`HTTPBearer`) | `UpdateBrandGlossaryRequest` | `BrandGlossaryResponse` | `unknown` |
| `GET` | `/api/v1/brand-glossaries/{glossary_id}/rules` | Yes (`HTTPBearer`) | — | `array` | `unknown` |
| `POST` | `/api/v1/brand-glossaries/{glossary_id}/rules` | Yes (`HTTPBearer`) | `CreateBrandGlossaryRuleRequest` | `BrandGlossaryRuleResponse` | `unknown` |
| `DELETE` | `/api/v1/brand-glossaries/{glossary_id}/rules/{rule_id}` | Yes (`HTTPBearer`) | — | `204 No Content` | `unknown` |
| `DELETE` | `/api/v1/brand-glossary-rules/{rule_id}` | Yes (`HTTPBearer`) | — | `204 No Content` | `unknown` |
| `PATCH` | `/api/v1/brand-glossary-rules/{rule_id}` | Yes (`HTTPBearer`) | `UpdateBrandGlossaryRuleRequest` | `BrandGlossaryRuleResponse` | `unknown` |
| `GET` | `/api/v1/brand-kits` | Yes (`HTTPBearer`) | — | `array` | `unknown` |
| `POST` | `/api/v1/brand-kits` | Yes (`HTTPBearer`) | `CreateBrandKitRequest` | `BrandKitResponse` | `unknown` |
| `DELETE` | `/api/v1/brand-kits/{brand_kit_id}` | Yes (`HTTPBearer`) | — | `204 No Content` | `unknown` |
| `GET` | `/api/v1/brand-kits/{brand_kit_id}` | Yes (`HTTPBearer`) | — | `BrandKitResponse` | `unknown` |
| `PATCH` | `/api/v1/brand-kits/{brand_kit_id}` | Yes (`HTTPBearer`) | `UpdateBrandKitRequest` | `BrandKitResponse` | `unknown` |
| `GET` | `/api/v1/brand-kits/{brand_kit_id}/glossaries` | Yes (`HTTPBearer`) | — | `array` | `unknown` |
| `POST` | `/api/v1/brand-kits/{brand_kit_id}/glossaries` | Yes (`HTTPBearer`) | `CreateBrandGlossaryRequest` | `BrandGlossaryResponse` | `unknown` |


### Folders (5 Operations)

| Method | Path | Auth Required | Request Model | Response Model | Implementation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/workspaces/{workspace_id}/folders` | Yes (`HTTPBearer`) | — | `array` | `unknown` |
| `POST` | `/api/v1/workspaces/{workspace_id}/folders` | Yes (`HTTPBearer`) | `FolderCreate` | `FolderResponse` | `unknown` |
| `DELETE` | `/api/v1/workspaces/{workspace_id}/folders/{folder_id}` | Yes (`HTTPBearer`) | — | `204 No Content` | `unknown` |
| `GET` | `/api/v1/workspaces/{workspace_id}/folders/{folder_id}` | Yes (`HTTPBearer`) | — | `FolderResponse` | `unknown` |
| `PATCH` | `/api/v1/workspaces/{workspace_id}/folders/{folder_id}` | Yes (`HTTPBearer`) | `FolderUpdate` | `FolderResponse` | `unknown` |


### Health (8 Operations)

| Method | Path | Auth Required | Request Model | Response Model | Implementation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/health` | No (Public) | — | `HealthResponse` | `unknown` |
| `GET` | `/api/v1/health/ai` | No (Public) | — | `AIHealthResponse` | `unknown` |
| `GET` | `/api/v1/metrics` | No (Public) | — | `object` | `unknown` |
| `GET` | `/api/v1/ready` | No (Public) | — | `ReadinessResponse` | `unknown` |
| `GET` | `/health` | No (Public) | — | `HealthResponse` | `unknown` |
| `GET` | `/health/ai` | No (Public) | — | `AIHealthResponse` | `unknown` |
| `GET` | `/metrics` | No (Public) | — | `object` | `unknown` |
| `GET` | `/ready` | No (Public) | — | `ReadinessResponse` | `unknown` |


### Invitations (1 Operations)

| Method | Path | Auth Required | Request Model | Response Model | Implementation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/invitations/{token}/accept` | Yes (`HTTPBearer`) | — | `InvitationAcceptResponse` | `unknown` |


### Jobs (6 Operations)

| Method | Path | Auth Required | Request Model | Response Model | Implementation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/jobs` | Yes (`HTTPBearer`) | — | `array` | `unknown` |
| `POST` | `/api/v1/jobs` | Yes (`HTTPBearer`) | `JobSubmitRequest` | `JobResponse` | `unknown` |
| `GET` | `/api/v1/jobs/{job_id}` | Yes (`HTTPBearer`) | — | `JobResponse` | `unknown` |
| `POST` | `/api/v1/jobs/{job_id}/cancel` | Yes (`HTTPBearer`) | — | `JobCancelResponse` | `unknown` |
| `GET` | `/api/v1/jobs/{job_id}/events` | Yes (`HTTPBearer`) | — | `array` | `unknown` |
| `GET` | `/api/v1/jobs/{job_id}/stream` | Yes (`HTTPBearer`) | — | `custom` | `unknown` |


### Project Orchestration (9 Operations)

| Method | Path | Auth Required | Request Model | Response Model | Implementation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/workspaces/{workspace_id}/projects/generate` | Yes (`HTTPBearer`) | `GenerateProjectRequest` | `Union[JobResponse, ProjectResponse]` | `unknown` |
| `POST` | `/api/v1/workspaces/{workspace_id}/projects/{project_id}/enhance-speech` | Yes (`HTTPBearer`) | `EnhanceProjectSpeechRequest` | `Union[JobResponse, ProjectVersionResponse]` | `unknown` |
| `POST` | `/api/v1/workspaces/{workspace_id}/projects/{project_id}/generate-avatar-video` | Yes (`HTTPBearer`) | `GenerateAvatarVideoRequest` | `Union[JobResponse, ProjectVersionResponse]` | `unknown` |
| `POST` | `/api/v1/workspaces/{workspace_id}/projects/{project_id}/render` | Yes (`HTTPBearer`) | `RenderProjectRequest` | `JobResponse` | `unknown` |
| `POST` | `/api/v1/workspaces/{workspace_id}/projects/{project_id}/scenes/{scene_id}/generate-visual` | Yes (`HTTPBearer`) | `GenerateSceneVisualRequest` | `Union[JobResponse, ProjectVersionResponse]` | `unknown` |
| `POST` | `/api/v1/workspaces/{workspace_id}/projects/{project_id}/synthesize-speech` | Yes (`HTTPBearer`) | `SynthesizeProjectSpeechRequest` | `Union[JobResponse, ProjectVersionResponse]` | `unknown` |
| `POST` | `/api/v1/workspaces/{workspace_id}/projects/{project_id}/transcribe` | Yes (`HTTPBearer`) | `TranscribeProjectAudioRequest` | `Union[JobResponse, ProjectVersionResponse]` | `unknown` |
| `POST` | `/api/v1/workspaces/{workspace_id}/projects/{project_id}/translate` | Yes (`HTTPBearer`) | `TranslateProjectRequest` | `Union[JobResponse, ProjectResponse, ProjectVersionResponse]` | `unknown` |
| `POST` | `/api/v1/workspaces/{workspace_id}/projects/{project_id}/validate` | Yes (`HTTPBearer`) | — | `TimelineValidationResponse` | `unknown` |


### Projects (8 Operations)

| Method | Path | Auth Required | Request Model | Response Model | Implementation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/workspaces/{workspace_id}/projects` | Yes (`HTTPBearer`) | — | `array` | `unknown` |
| `POST` | `/api/v1/workspaces/{workspace_id}/projects` | Yes (`HTTPBearer`) | `ProjectCreate` | `ProjectResponse` | `unknown` |
| `DELETE` | `/api/v1/workspaces/{workspace_id}/projects/{project_id}` | Yes (`HTTPBearer`) | — | `204 No Content` | `unknown` |
| `GET` | `/api/v1/workspaces/{workspace_id}/projects/{project_id}` | Yes (`HTTPBearer`) | — | `ProjectResponse` | `unknown` |
| `PATCH` | `/api/v1/workspaces/{workspace_id}/projects/{project_id}` | Yes (`HTTPBearer`) | `ProjectUpdate` | `ProjectResponse` | `unknown` |
| `GET` | `/api/v1/workspaces/{workspace_id}/projects/{project_id}/versions` | Yes (`HTTPBearer`) | — | `array` | `unknown` |
| `POST` | `/api/v1/workspaces/{workspace_id}/projects/{project_id}/versions` | Yes (`HTTPBearer`) | `CreateProjectVersionRequest` | `ProjectVersionResponse` | `unknown` |
| `GET` | `/api/v1/workspaces/{workspace_id}/projects/{project_id}/versions/{version_id}` | Yes (`HTTPBearer`) | — | `ProjectVersionResponse` | `unknown` |


### Templates (9 Operations)

| Method | Path | Auth Required | Request Model | Response Model | Implementation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/templates` | Yes (`HTTPBearer`) | — | `array` | `unknown` |
| `POST` | `/api/v1/templates` | Yes (`HTTPBearer`) | `CreateTemplateRequest` | `TemplateResponse` | `unknown` |
| `DELETE` | `/api/v1/templates/{template_id}` | Yes (`HTTPBearer`) | — | `204 No Content` | `unknown` |
| `GET` | `/api/v1/templates/{template_id}` | Yes (`HTTPBearer`) | — | `TemplateResponse` | `unknown` |
| `PATCH` | `/api/v1/templates/{template_id}` | Yes (`HTTPBearer`) | `UpdateTemplateRequest` | `TemplateResponse` | `unknown` |
| `POST` | `/api/v1/templates/{template_id}/instantiate` | Yes (`HTTPBearer`) | — | `ProjectResponse` | `unknown` |
| `GET` | `/api/v1/templates/{template_id}/versions` | Yes (`HTTPBearer`) | — | `array` | `unknown` |
| `POST` | `/api/v1/templates/{template_id}/versions` | Yes (`HTTPBearer`) | `CreateTemplateVersionRequest` | `TemplateVersionResponse` | `unknown` |
| `GET` | `/api/v1/templates/{template_id}/versions/{version_id}` | Yes (`HTTPBearer`) | — | `TemplateVersionResponse` | `unknown` |


### Voices (8 Operations)

| Method | Path | Auth Required | Request Model | Response Model | Implementation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/voices` | Yes (`HTTPBearer`) | — | `array` | `unknown` |
| `POST` | `/api/v1/voices` | Yes (`HTTPBearer`) | `CreateVoiceRequest` | `VoiceResponse` | `unknown` |
| `POST` | `/api/v1/voices/clone` | Yes (`HTTPBearer`) | `VoiceCloneRequest` | `VoiceCloneJobResponse` | `unknown` |
| `DELETE` | `/api/v1/voices/{voice_id}` | Yes (`HTTPBearer`) | — | `204 No Content` | `unknown` |
| `GET` | `/api/v1/voices/{voice_id}` | Yes (`HTTPBearer`) | — | `VoiceResponse` | `unknown` |
| `PATCH` | `/api/v1/voices/{voice_id}` | Yes (`HTTPBearer`) | `UpdateVoiceRequest` | `VoiceResponse` | `unknown` |
| `GET` | `/api/v1/voices/{voice_id}/preview` | Yes (`HTTPBearer`) | — | `VoicePreviewResponse` | `unknown` |
| `POST` | `/api/v1/workspaces/{workspace_id}/voices/clone` | Yes (`HTTPBearer`) | `VoiceCloneRequest` | `VoiceCloneJobResponse` | `unknown` |


### Webhooks (7 Operations)

| Method | Path | Auth Required | Request Model | Response Model | Implementation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/workspaces/{workspace_id}/developer/webhooks` | Yes (`HTTPBearer`) | — | `WebhookListResponse` | `unknown` |
| `POST` | `/api/v1/workspaces/{workspace_id}/developer/webhooks` | Yes (`HTTPBearer`) | `WebhookCreateRequest` | `WebhookCreatedResponse` | `unknown` |
| `DELETE` | `/api/v1/workspaces/{workspace_id}/developer/webhooks/{webhook_id}` | Yes (`HTTPBearer`) | — | `204 No Content` | `unknown` |
| `GET` | `/api/v1/workspaces/{workspace_id}/developer/webhooks/{webhook_id}` | Yes (`HTTPBearer`) | — | `WebhookResponse` | `unknown` |
| `PATCH` | `/api/v1/workspaces/{workspace_id}/developer/webhooks/{webhook_id}` | Yes (`HTTPBearer`) | `WebhookUpdateRequest` | `WebhookResponse` | `unknown` |
| `GET` | `/api/v1/workspaces/{workspace_id}/developer/webhooks/{webhook_id}/deliveries` | Yes (`HTTPBearer`) | — | `WebhookDeliveryListResponse` | `unknown` |
| `POST` | `/api/v1/workspaces/{workspace_id}/developer/webhooks/{webhook_id}/test` | Yes (`HTTPBearer`) | — | `object` | `unknown` |


### Workspaces (12 Operations)

| Method | Path | Auth Required | Request Model | Response Model | Implementation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/workspaces` | Yes (`HTTPBearer`) | — | `array` | `unknown` |
| `POST` | `/api/v1/workspaces` | Yes (`HTTPBearer`) | `WorkspaceCreate` | `WorkspaceResponse` | `unknown` |
| `DELETE` | `/api/v1/workspaces/{workspace_id}` | Yes (`HTTPBearer`) | — | `204 No Content` | `unknown` |
| `GET` | `/api/v1/workspaces/{workspace_id}` | Yes (`HTTPBearer`) | — | `WorkspaceResponse` | `unknown` |
| `PATCH` | `/api/v1/workspaces/{workspace_id}` | Yes (`HTTPBearer`) | `WorkspaceUpdate` | `WorkspaceResponse` | `unknown` |
| `GET` | `/api/v1/workspaces/{workspace_id}/invitations` | Yes (`HTTPBearer`) | — | `array` | `unknown` |
| `POST` | `/api/v1/workspaces/{workspace_id}/invitations` | Yes (`HTTPBearer`) | `WorkspaceInvitationCreate` | `WorkspaceInvitationResponse` | `unknown` |
| `POST` | `/api/v1/workspaces/{workspace_id}/invitations/{invitation_id}/revoke` | Yes (`HTTPBearer`) | — | `object` | `unknown` |
| `GET` | `/api/v1/workspaces/{workspace_id}/members` | Yes (`HTTPBearer`) | — | `array` | `unknown` |
| `DELETE` | `/api/v1/workspaces/{workspace_id}/members/{user_id}` | Yes (`HTTPBearer`) | — | `204 No Content` | `unknown` |
| `PATCH` | `/api/v1/workspaces/{workspace_id}/members/{user_id}` | Yes (`HTTPBearer`) | `WorkspaceMemberUpdate` | `WorkspaceMemberResponse` | `unknown` |
| `POST` | `/api/v1/workspaces/{workspace_id}/transfer-ownership` | Yes (`HTTPBearer`) | `TransferOwnershipRequest` | `WorkspaceResponse` | `unknown` |

