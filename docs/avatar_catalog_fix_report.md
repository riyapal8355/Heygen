# HeyZen Studio — Avatar Catalog Troubleshooting & Fix Report

## 1. Problem
In the HeyZen Studio editor (`src/components/studio/VidoAIStudio.tsx`), the **Avatar** tab opened correctly, but displayed:
```text
SELECT AVATAR
0 available

Search avatars...
```
Furthermore, the Studio canvas and timeline showed:
```text
👤 default-presenter
```
as the active actor layer, but the Avatar selector contained 0 selectable avatars. Selecting or changing avatars was blocked.

---

## 2. Root Cause
The root cause was traced across the end-to-end flow:
1. **Frontend Request**: Studio executes `api.creative.listAvatars({}, workspaceId)` on mount (`GET /api/v1/avatars` with header `X-Workspace-ID: <workspace_id>`).
2. **Backend Query**: `AvatarRepository.list_by_workspace(db, workspace_id)` filters:
   ```python
   or_(Avatar.workspace_id == workspace_id, Avatar.visibility == "public")
   ```
3. **Missing Canonical Preset Avatars**: In `backend/app/db/seeds.py`, `seed_canonical_presets()` previously seeded 19 canonical preset voices (`CANONICAL_PRESET_VOICES`), but completely lacked avatar presets (`CANONICAL_PRESET_AVATARS`).
4. **Database State**: The database contained 0 avatars with `visibility = "public"`. When opening Studio in any user workspace, `GET /api/v1/avatars` returned HTTP 200 with an empty list `[]`.
5. **Identifier Mapping**: New scenes in Studio initialize with `avatar_id: "default-presenter"`. Studio's UI matched selected avatars strictly by UUID `id` or exact `name`, but lacked matching against `provider_reference` or slugified name, preventing `default-presenter` from immediately linking to its canonical presenter record.

---

## 3. End-to-End Flow Investigation

```text
Studio Avatar UI (VidoAIStudio.tsx)
  │
  ▼
API Client (api.ts: api.creative.listAvatars)
  │  HTTP GET /api/v1/avatars
  │  Headers: Authorization: Bearer <jwt>, X-Workspace-ID: <workspace_id>
  │
  ▼
FastAPI Router (backend/app/api/v1/endpoints/avatars.py)
  │  Endpoint: list_avatars()
  │  Depends: get_current_user, get_workspace_context
  │
  ▼
Avatar Service & Repository (backend/app/repositories/avatar_repo.py)
  │  SQL: SELECT * FROM avatars WHERE workspace_id = :ws_id OR visibility = 'public'
  │
  ▼
PostgreSQL Database (heyzen-postgres: 5432)
  │  State before: 0 public avatars, 0 workspace avatars -> returned []
  │  State after:  5 canonical public preset avatars -> returned 5 items
  │
  ▼
FastAPI Response: HTTP 200 JSON list of AvatarRead schemas
  │
  ▼
Frontend State & UI (VidoAIStudio.tsx)
  │  setAvatars(aList) -> 5 available
  │  filteredAvatars -> matched and rendered with portrait thumbnails & badges
  │  Default Presenter matched via provider_reference="default-presenter"
```

---

## 4. Fix Summary & Files Changed

### A. Backend Seed Architecture (`backend/app/db/seeds.py`)
- Added `Avatar` and `AvatarLook` model imports to `seeds.py`.
- Implemented synthetic portrait reference asset generator `_create_synthetic_portrait_image_bytes()` and MinIO upload utility to provide reference portrait assets and preview URLs for standard public avatars.
- Seeded 5 canonical public preset avatars (`CANONICAL_PRESET_AVATARS`) into PostgreSQL:
  1. **Default Presenter** (`30000000-0000-0000-0000-000000000001`, `provider_reference="default-presenter"`, `provider="wav2lip"`, 3 looks: Default / Business / Casual)
  2. **Annie - Studio Presenter** (`30000000-0000-0000-0000-000000000002`, `provider_reference="annie"`, `provider="wav2lip"`, 2 looks: Studio / Casual)
  3. **Rasmus - Executive** (`30000000-0000-0000-0000-000000000003`, `provider_reference="rasmus"`, `provider="wav2lip"`, 1 look)
  4. **Daniel - Modern Creator** (`30000000-0000-0000-0000-000000000004`, `provider_reference="daniel"`, `provider="musetalk"`, 1 look)
  5. **Sophia - Creative Director** (`30000000-0000-0000-0000-000000000005`, `provider_reference="sophia"`, `provider="wav2lip"`, 1 look)
- Executed seed script idempotently via `run_seeds()`.

### B. Backend Unit & Isolation Tests (`backend/tests/test_avatars.py`)
- Updated `test_avatar_crud_flow` and `test_workspace_isolation_avatars` to account for coexistence with public preset avatars (mirroring how voices are tested in `test_voices.py`).
- Verified workspace-created avatars remain isolated between workspaces, while public presets remain globally discoverable.

### C. Frontend Studio UI (`src/components/studio/VidoAIStudio.tsx`)
- Enhanced `activeAvatarObj` lookup to resolve by `id`, `name`, `provider_reference`, or slugified name.
- Enhanced avatar selection matching (`isSelected`) in the Avatar panel so `default-presenter` matches `Default Presenter` immediately on load.
- Enhanced avatar item display to render portrait thumbnails (`provider_metadata.preview_url || provider_metadata.image_url`) with fallback to avatar emoji.
- Enhanced timeline track to display the resolved avatar name `👤 Default Presenter` instead of raw ID.
- Enhanced central canvas avatar placeholder to display the active avatar portrait image.
- Updated availability badge to display accurate count (e.g. `5 available` or `X of 5 available` during search).

---

## 5. Verification Results

| Check | Result | Details |
|---|---|---|
| **Avatar API (`GET /api/v1/avatars`)** | **PASS** | Returns HTTP 200 with 5 public preset avatars. |
| **Avatar UI (`Select Avatar`)** | **PASS** | Displays `5 available`, rendered with portrait thumbnails & provider badges. |
| **Search Functionality** | **PASS** | Case-insensitive search filters by name, provider (`musetalk`, `wav2lip`), or reference. Empty search displays full catalog. |
| **Framing Mode** | **PASS** | `half_body`, `close_up`, `circle` update scene document model without filtering catalog. |
| **Selection Functionality** | **PASS** | Clicking avatar card updates scene `avatar.avatar_id`, invalidates cached video, records undo history, and saves to backend. |
| **Persistence** | **PASS** | Avatar selection persists through OCC project version snapshot saving. |
| **Swagger / OpenAPI Documentation** | **PASS** | `GET /api/v1/avatars` testable in Swagger UI with `Authorization` and optional `X-Workspace-ID`. |

---

## 6. Regression Testing

- **Frontend Unit Tests**: 256/256 passed (`npm test`).
- **TypeScript Typecheck**: 0 errors (`npx tsc --noEmit`).
- **Production Build**: 0 errors (`npm run build`).
- **Backend Test Suite**: 9/9 passed (`pytest backend/tests/test_avatars.py backend/tests/test_swagger_path_params.py`).
- **API Smoke Test Suite**: 8/8 test phases passed (`backend/scripts/smoke_test_api.py`).
- **Browser E2E**: BROWSER E2E NOT VERIFIED — no Playwright `.spec.ts` tests are configured.

---

## 7. Development Services Status

| Service | Port | Status |
|---|---|---|
| **Next.js** | 3000 | RUNNING |
| **FastAPI** | 8000 | RUNNING |
| **PostgreSQL** | 5432 | RUNNING |
| **Redis** | 6379 | RUNNING |
| **MinIO** | 9000 / 9001 | RUNNING |
| **Docker** | — | RUNNING |

---

## 8. Known Limitations
- Local generation engines (Wav2Lip / MuseTalk) require local GPU/weights for offline inference; when running on CPU or without weights, mock or fallback video generation operates as expected.
- External avatar providers (e.g., LiveKit, HeyGen API) require valid third-party API credentials if external provider sync is enabled.
