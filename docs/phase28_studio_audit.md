# Phase 28 Studio Audit: Studio Editing Completion & Production Video Integration

**Date:** 2026-09-19  
**Document Target:** `docs/phase28_studio_audit.md`  
**Focus:** Complete audit of HeyZen Studio frontend components, static/mock data paths, missing controls, and mapping to existing backend services.

---

## 1. Studio Architecture & Entry Point Audit

- **Studio Entry Point:**  
  `src/app/page.tsx` (Lines 378–386):  
  When `currentView === "studio"`, renders:
  ```tsx
  <VidoAIStudio
    projectId={activeProjectId || undefined}
    workspaceId={currentWorkspace?.id}
    onBackToDashboard={() => setCurrentView("dashboard")}
  />
  ```
  `activeProjectId` is set when a project card is clicked in `ProjectsManager.tsx` or via creation templates.

- **Primary Component Structure:**  
  `src/components/studio/VidoAIStudio.tsx` (767 lines, single monolith component).
  - **Top Navigation Bar:** Title input, Undo/Redo (no-op), Save status & OCC conflict reload button, Aspect ratio dropdown (local state), Preview button (toggles boolean), Export button (triggers render job + SSE stream), User menu.
  - **Left Tool Icon Rail:** 11 tool icons (`scenes`, `avatar`, `voice`, `script`, `media`, `text`, `elements`, `music`, `transitions`, `captions`, `brand_kit`). Clicking icons only updates `activeLeftTool` state without opening respective tool panels (except `scenes`).
  - **Scenes Thumbnail Strip:** Lists scenes in vertical strip. The `+` button has no `onClick` handler. Thumbnails display static emoji `👩‍💼`. No duplicate/delete/reorder controls.
  - **Center Canvas & Player:** Renders static emoji `👩‍💼` on gradient with static text. Scrubber slider and time display (`00:02.15 / 00:46.00`) are static. Play/Pause flips boolean without controlling media.
  - **Right Inspector Panel:** Tab switcher (`scene`, `avatar`, `voice`). All 3 tabs currently render the exact same hardcoded "Scene Settings" panel. No avatar picker, no voice picker, no script editor, no speech generation controls.
  - **Bottom Timeline:** 4 tracks (`Video`, `Avatar`, `Text`, `Audio`). Clips are completely hardcoded strings (`Clip 1 (0:08)`, `Emma - Professional`, `AI VIDEO CREATOR`, `Voice Over (Emma AI - Neutral)`). Action buttons (`Scissors`, `Trash2`, `Copy`) have no handlers.

---

## 2. Comprehensive Audit Matrix

| UI Area | Existing Implementation | Missing / Static Behavior | Backend Endpoint / Service | Required Change |
|:---|:---|:---|:---|:---|
| **Project Loading & Header** | `loadProject` fetches project via `api.projects.get` and version via `api.projects.getVersion`. Sets project title, aspect ratio, duration. | If no project ID is provided or project is empty, defaults to 5 mock scenes. Errors caught silently (`catch {}`). No loading spinner or error alert. | `GET /api/v1/workspaces/{ws}/projects/{id}`<br>`GET /api/v1/workspaces/{ws}/projects/{id}/versions/{vid}` (`ProjectService`) | Add loading indicator; handle empty project gracefully; display error alert if project fails to load; auto-sync settings. |
| **Scene List & Strip** | Vertical list displaying scene label and duration. Clicking selects `activeSceneIndex`. | `+` Add Scene button has NO `onClick` handler.<br>Thumbnails show static emoji `👩‍💼`.<br>No Duplicate, Delete, or Reorder (Move Up/Down) controls. | `POST /api/v1/workspaces/{ws}/projects/{id}/versions` (`ProjectService.create_version`) | Connect `+` button to create new scene in `currentDocument.scenes`; add duplicate, delete, and reorder controls; recalculate sequence indices; persist to backend with OCC. |
| **Script Editor** | Left rail has `script` tool icon (`activeLeftTool === "script"`), but no script editor exists. | Completely missing from inspector and canvas. Users cannot view or edit `scene.speech.script`. No character or word counter. | `ProjectDocumentV1.scenes[i].speech.script`<br>`POST /api/v1/workspaces/{ws}/projects/{id}/versions` | Implement Script Editor in inspector when `script` tool or `scene` tab is active. Allow editing script, display word count, and persist script edits. |
| **Voice Selector** | Inspector has "Voice" tab; left rail has "Voice" tool. | Clicking "Voice" tab renders static "Scene Settings". No voice catalog list, no language/gender filter, no preview audio playback. `scene.speech.voice_id` is not selectable. | `GET /api/v1/voices`<br>`GET /api/v1/voices/{id}/preview` (`VoiceService`) | In "Voice" tab, fetch real voices from `api.creative.listVoices`. Display Piper (13) + Kokoro (4) voices with badges and audio preview player. Selecting voice updates `scene.speech.voice_id` and persists. |
| **Avatar Selector** | Inspector has "Avatar" tab; left rail has "Avatar" tool. | Clicking "Avatar" tab renders static "Scene Settings". No avatar list, no portrait preview, no view mode toggle (`half_body`, `circle`, `close_up`). `scene.avatar.avatar_id` is not selectable. | `GET /api/v1/avatars`<br>`GET /api/v1/workspaces/{ws}/assets/{id}/download` (`AvatarService`) | In "Avatar" tab, fetch real avatars from `api.creative.listAvatars`. Show portrait cards, provider badge, view mode toggle. Selecting avatar updates `scene.avatar.avatar_id` and persists. |
| **Scene Speech Generation** | Missing from Studio UI. | No button to generate speech audio for the active scene. No status badge showing `scene.speech.audio_asset_id`. | `POST /api/v1/workspaces/{ws}/projects/{id}/synthesize-speech`<br>`GET /api/v1/jobs/{id}`<br>SSE `/api/v1/jobs/{id}/stream` (`ProjectSpeechOrchestrator`) | Add "Generate Speech Audio" button. Triggers `synthesizeSpeech(run_async=true)`. Streams real job progress % via SSE. Refreshes document upon completion to bind `audio_asset_id`. |
| **Talking Avatar Generation** | Missing from Studio UI. | No button to generate neural lip-sync video. No status badge showing `scene.avatar.video_asset_id`. | `POST /api/v1/workspaces/{ws}/projects/{id}/generate-avatar-video`<br>`GET /api/v1/jobs/{id}`<br>SSE `/api/v1/jobs/{id}/stream` (`ProjectAvatarOrchestrator`) | Add "Generate Talking Avatar" button. Requires speech audio. Triggers `generateAvatarVideo`. Surfaces truthful `GPU_UNAVAILABLE` on AMD host if MuseTalk requested. Binds `video_asset_id` on success. |
| **Center Canvas & Media Player** | Canvas displays static emoji `👩‍💼` and static text. Play/Pause flips boolean `isPlaying`. Scrubber is a static div at 18%. | No real HTML5 `<video>` or `<audio>` playback. Does not resolve or play `video_asset_id` or `audio_asset_id`. Duration is hardcoded `00:46.00`. | `GET /api/v1/workspaces/{ws}/assets/{id}/download` (`AssetLifecycleManager` MinIO download URL) | When `video_asset_id` exists, fetch download URL and render real video player. When only `audio_asset_id` exists, play audio with avatar image. Real scrubber and playback time tracking. |
| **Bottom Timeline** | 4 lanes (`Video`, `Avatar`, `Text`, `Audio`) with fixed mock clip blocks. Action bar has inactive buttons (`Scissors`, `Trash2`, `Copy`). | Clips are hardcoded strings. They do not reflect `currentDocument.scenes`. Clicking a clip does not switch the active scene. Action bar buttons do nothing. Fixed playhead needle. | `ProjectDocumentV1.scenes`<br>`ProjectDocumentV1.settings.total_duration` | Dynamically render timeline blocks proportional to scene durations. Display real scene titles, avatar names, voice names. Clicking selects scene. Action bar duplicates/deletes scenes. |
| **Project Persistence & Concurrency** | `handleSave` creates version with `api.projects.createVersion`. Shows "Saving...", "Saved (rX)", and "Conflict (Reload)". | Scene mapping only retains dummy duration or loses speech/avatar details if not structured carefully. No auto-save on change. | `POST /api/v1/workspaces/{ws}/projects/{id}/versions` (`ProjectService.create_version`) | Ensure complete fidelity of `ProjectDocumentV1` (scenes, speech, avatar, settings, metadata). Preserve OCC revision tracking. Add debounce auto-save or clear save prompts. |
| **Render & Export** | `handleExport` calls `api.orchestration.renderProject`, streams SSE with `api.jobs.stream`, shows Download button when completed. | No pre-flight validation warning if scenes lack media. No cancellation button. Generic error display if render fails. | `POST /api/v1/workspaces/{ws}/projects/{id}/render`<br>`POST /api/v1/jobs/{id}/cancel` (`ProjectRenderOrchestrator`) | Keep existing export flow; add Cancel button (`api.jobs.cancel`); display detailed render error banner if job fails; ensure downloaded MP4 is playable. |
| **Error Handling & Feedback** | Concurrency conflict shows amber badge. | 401, 403, 404, 422, network drops, and `GPU_UNAVAILABLE` are not surfaced with clear user banners. | `ApiError` class in `src/lib/api.ts` | Add toast / banner notification system for API errors, job failures, and validation warnings. |

---

## 3. Backend Capability Mapping

All required capabilities exist in the backend without requiring any new routes or database migrations:

1. **Project & Version Management:**
   - `GET /api/v1/workspaces/{ws}/projects/{id}`
   - `GET /api/v1/workspaces/{ws}/projects/{id}/versions/{vid}`
   - `POST /api/v1/workspaces/{ws}/projects/{id}/versions` (OCC `expected_revision`)
2. **Voice Catalog & Previews:**
   - `GET /api/v1/voices` (Supports real Piper 13 voices + Kokoro 4 voices)
   - `GET /api/v1/voices/{id}/preview` (Returns pre-signed URL to MinIO preview WAV/MP3)
3. **Avatar Catalog & Looks:**
   - `GET /api/v1/avatars` (Returns avatars with provider, status, preview_asset_id)
   - `GET /api/v1/avatars/{id}/looks`
4. **Speech Synthesis Orchestration:**
   - `POST /api/v1/workspaces/{ws}/projects/{id}/synthesize-speech` (`run_async=true`, `scene_ids=[...]`)
5. **Talking-Avatar Video Orchestration:**
   - `POST /api/v1/workspaces/{ws}/projects/{id}/generate-avatar-video` (`run_async=true`, `scene_id=...`)
6. **Timeline Rendering Orchestration:**
   - `POST /api/v1/workspaces/{ws}/projects/{id}/render` (`resolution="1080p"`, `format="mp4"`)
   - `POST /api/v1/workspaces/{ws}/projects/{id}/validate`
7. **Asset Download & Streaming:**
   - `GET /api/v1/workspaces/{ws}/assets/{id}/download` (Returns pre-signed MinIO URL)
8. **Asynchronous Job Management & SSE Streaming:**
   - `GET /api/v1/jobs/{id}`
   - `GET /api/v1/jobs/{id}/stream` (SSE event streaming with durable poll recovery)
   - `POST /api/v1/jobs/{id}/cancel`

---

## 4. Execution Plan for Phase 28

1. **Step 2:** Complete backend capability mapping (Done above).
2. **Step 3 & 4:** Update `src/components/studio/VidoAIStudio.tsx`:
   - Replace static mock scenes with real `ProjectDocumentV1` scenes.
   - Implement Add Scene, Duplicate Scene, Delete Scene, Reorder Scene.
   - Implement Script Editor for the active scene.
   - Implement real Voice Selector with audio preview playback.
   - Implement real Avatar Selector with portrait display and view mode selection.
   - Add real "Generate Speech" action connected to `api.orchestration.synthesizeSpeech` + SSE progress.
   - Add real "Generate Talking Avatar" action connected to `api.orchestration.generateAvatarVideo` + SSE progress + truthful `GPU_UNAVAILABLE` handling.
   - Update Canvas to render real `<video>` or `<audio>` player from MinIO pre-signed download URLs.
   - Connect bottom timeline lanes dynamically to scenes, displaying real durations and titles.
   - Wire timeline action buttons (`Trash2`, `Copy`).
   - Connect Cancel Render action.
3. **Step 5–12:** Verify project persistence, OCC concurrency handling, and multi-scene project rendering.
4. **Step 13–15:** Perform persistence test, multi-scene test, and error handling verification.
5. **Step 16–17:** Verify frontend build (`npm run build`), full backend tests (`pytest -q`), and browser E2E verification.
6. **Step 18:** Generate `docs/phase28_final_report.md`.
