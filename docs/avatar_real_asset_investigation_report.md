# Avatar Real Asset Investigation & Root Cause Report

## 1. Executive Summary

This report documents the exhaustive investigation into avatar visual assets, the `/api/v1/avatars` endpoint, MinIO object storage, and the central canvas rendering path within `VidoAIStudio.tsx`.

**Conclusion:** **BLOCKED — REAL AVATAR VISUAL ASSETS ARE MISSING**

No legitimate avatar visual media (production portrait images or talking head videos) exist in the repository, Git history, MinIO object storage, database records, or provider model directories. The current MinIO objects are 3,445-byte synthetic test frames (OpenCV circle drawings) generated during backend unit test fixtures. Under project safety guidelines, synthetic test fixtures must not be fabricated as production avatar images.

---

## 2. Root Cause Analysis

### Proven Root Cause
1. **Primary Root Cause (Asset Availability):** `G — Missing legitimate avatar assets`.
   - Exhaustive repository search across all image/video formats (`.png`, `.jpg`, `.jpeg`, `.webp`, `.mp4`) revealed only 5 standard Next.js SVG icons and `favicon.ico`. No real avatar portraits or videos have ever been committed to Git.
   - Paginating through all objects in the MinIO `heyzen-assets` bucket confirmed 0 non-synthetic avatar portraits exist.
   - The 5 canonical avatar preview assets in MinIO (`workspaces/00000000-0000-0000-0000-000000000001/assets/...`) contain identical 3,445-byte synthetic test images (`SHA256: ad87b1b1f018d0d2`) created by `_create_synthetic_portrait_image_bytes()` in backend test files.
2. **Secondary Canvas Placeholder Condition:**
   - In `VidoAIStudio.tsx`, the purple gradient placeholder (`bg-gradient-to-t from-blue-900/40 to-purple-900/40` with `👤` or `🎙️`) is rendered when `avatarVisualUrl` is falsy (`null` or `undefined`).
   - `avatarVisualUrl` evaluates to `null` whenever:
     1. `avatars` array has not loaded (e.g. initial render or unauthenticated 401 response from `/api/v1/avatars`), causing `activeAvatarObj` to be `null`.
     2. An avatar has no valid `preview_url` or `provider_metadata.preview_url`.
   - When authenticated, the API successfully returns pre-signed URLs pointing to MinIO; however, because the underlying MinIO objects are synthetic test drawings rather than legitimate portrait photos/videos, the canvas renders synthetic circles instead of real human avatar presenters.

---

## 3. Avatar API Verification

- **Endpoint:** `GET http://127.0.0.1:8000/api/v1/avatars`
- **Workspace Header:** `X-Workspace-ID: 22222222-2222-2222-2222-222222222222`
- **Authentication:** Bearer JWT Token (`sub: 11111111-1111-1111-1111-111111111111`)
- **Total Avatars Returned:** 5

### Avatar Records & Preview URLs

1. **Default Presenter**
   - **ID:** `30000000-0000-0000-0000-000000000001`
   - **Provider:** `wav2lip`
   - **Provider Reference:** `default-presenter`
   - **Preview Asset ID:** `20000000-0000-0000-0000-000000000101`
   - **Preview URL:** `http://127.0.0.1:9000/heyzen-assets/workspaces/00000000-0000-0000-0000-000000000001/assets/20000000-0000-0000-0000-000000000101/portrait_default_presenter.png?...`
     - Status: `200 OK` | Type: `image/png` | Length: `3445 bytes` | Synthetic: `True`
   - **Looks (3):**
     - *Studio Half Body* (`31000000-0000-0000-0000-000000000001`): `3445 bytes` (Synthetic)
     - *Close Up* (`31000000-0000-0000-0000-000000000002`): `3445 bytes` (Synthetic)
     - *Circle Badge* (`31000000-0000-0000-0000-000000000003`): `3445 bytes` (Synthetic)

2. **Annie - Studio Presenter**
   - **ID:** `30000000-0000-0000-0000-000000000002`
   - **Provider:** `wav2lip`
   - **Provider Reference:** `annie`
   - **Preview Asset ID:** `20000000-0000-0000-0000-000000000102`
   - **Preview URL:** `http://127.0.0.1:9000/heyzen-assets/workspaces/00000000-0000-0000-0000-000000000001/assets/20000000-0000-0000-0000-000000000102/portrait_annie___studio_presenter.png?...`
     - Status: `200 OK` | Type: `image/png` | Length: `3445 bytes` | Synthetic: `True`
   - **Looks (2):**
     - *Beige Blazer* (`31000000-0000-0000-0000-000000000011`): `3445 bytes` (Synthetic)
     - *Navy Blazer* (`31000000-0000-0000-0000-000000000012`): `3445 bytes` (Synthetic)

3. **Rasmus - Executive**
   - **ID:** `30000000-0000-0000-0000-000000000003`
   - **Provider:** `wav2lip`
   - **Provider Reference:** `rasmus`
   - **Preview Asset ID:** `20000000-0000-0000-0000-000000000103`
   - **Preview URL:** `http://127.0.0.1:9000/heyzen-assets/workspaces/00000000-0000-0000-0000-000000000001/assets/20000000-0000-0000-0000-000000000103/portrait_rasmus___executive.png?...`
     - Status: `200 OK` | Type: `image/png` | Length: `3445 bytes` | Synthetic: `True`
   - **Looks (1):**
     - *Navy Jacket* (`31000000-0000-0000-0000-000000000021`): `3445 bytes` (Synthetic)

4. **Daniel - Modern Creator**
   - **ID:** `30000000-0000-0000-0000-000000000004`
   - **Provider:** `musetalk`
   - **Provider Reference:** `daniel`
   - **Preview Asset ID:** `20000000-0000-0000-0000-000000000104`
   - **Preview URL:** `http://127.0.0.1:9000/heyzen-assets/workspaces/00000000-0000-0000-0000-000000000001/assets/20000000-0000-0000-0000-000000000104/portrait_daniel___modern_creator.png?...`
     - Status: `200 OK` | Type: `image/png` | Length: `3445 bytes` | Synthetic: `True`
   - **Looks (1):**
     - *Black Shirt* (`31000000-0000-0000-0000-000000000031`): `3445 bytes` (Synthetic)

5. **Sophia - Creative Director**
   - **ID:** `30000000-0000-0000-0000-000000000005`
   - **Provider:** `wav2lip`
   - **Provider Reference:** `sophia`
   - **Preview Asset ID:** `20000000-0000-0000-0000-000000000105`
   - **Preview URL:** `http://127.0.0.1:9000/heyzen-assets/workspaces/00000000-0000-0000-0000-000000000001/assets/20000000-0000-0000-0000-000000000105/portrait_sophia___creative_director.png?...`
     - Status: `200 OK` | Type: `image/png` | Length: `3445 bytes` | Synthetic: `True`
   - **Looks (1):**
     - *White Top* (`31000000-0000-0000-0000-000000000041`): `3445 bytes` (Synthetic)

---

## 4. Current Asset Objects Audit

| Avatar | Avatar ID | Provider | Provider Ref | Preview Asset ID | Storage Key | Exists | Real / Synthetic |
|---|---|---|---|---|---|---|---|
| **Default Presenter** | `30000000-0000-0000-0000-000000000001` | wav2lip | default-presenter | `20000000-0000-0000-0000-000000000101` | `workspaces/00000000-0000-0000-0000-000000000001/assets/20000000-0000-0000-0000-000000000101/portrait_default_presenter.png` | True | **Synthetic** (3445 bytes) |
| **Annie - Studio Presenter** | `30000000-0000-0000-0000-000000000002` | wav2lip | annie | `20000000-0000-0000-0000-000000000102` | `workspaces/00000000-0000-0000-0000-000000000001/assets/20000000-0000-0000-0000-000000000102/portrait_annie___studio_presenter.png` | True | **Synthetic** (3445 bytes) |
| **Rasmus - Executive** | `30000000-0000-0000-0000-000000000003` | wav2lip | rasmus | `20000000-0000-0000-0000-000000000103` | `workspaces/00000000-0000-0000-0000-000000000001/assets/20000000-0000-0000-0000-000000000103/portrait_rasmus___executive.png` | True | **Synthetic** (3445 bytes) |
| **Daniel - Modern Creator** | `30000000-0000-0000-0000-000000000004` | musetalk | daniel | `20000000-0000-0000-0000-000000000104` | `workspaces/00000000-0000-0000-0000-000000000001/assets/20000000-0000-0000-0000-000000000104/portrait_daniel___modern_creator.png` | True | **Synthetic** (3445 bytes) |
| **Sophia - Creative Director** | `30000000-0000-0000-0000-000000000005` | wav2lip | sophia | `20000000-0000-0000-0000-000000000105` | `workspaces/00000000-0000-0000-0000-000000000001/assets/20000000-0000-0000-0000-000000000105/portrait_sophia___creative_director.png` | True | **Synthetic** (3445 bytes) |

---

## 5. Studio Canvas Verification

- **Default Presenter:** `BLOCKED` (Renders 3445B synthetic circle drawing or purple fallback; no real asset exists)
- **Annie:** `BLOCKED` (Renders 3445B synthetic circle drawing or purple fallback; no real asset exists)
- **Rasmus:** `BLOCKED` (Renders 3445B synthetic circle drawing or purple fallback; no real asset exists)
- **Daniel:** `BLOCKED` (Renders 3445B synthetic circle drawing or purple fallback; no real asset exists)
- **Sophia:** `BLOCKED` (Renders 3445B synthetic circle drawing or purple fallback; no real asset exists)

---

## 6. Seed Code Inspection & Cleanup

- Inspected `backend/app/db/seeds.py`.
- Verified that `seeds.py` only checks `storage.object_exists(storage_key)` and does NOT generate synthetic avatar portraits.
- No temporary investigation mutations exist in `seeds.py`.
- Removed scratch files (`scratch_test_api.py`).

---

## 7. Test Results

- **TypeScript:** `npx tsc --noEmit` -> **PASS** (Exit code 0, 0 type errors)
- **Frontend Unit Tests:** `npm test` -> **PASS** (263 passed, 0 failed, 74 suites)
- **Next.js Production Build:** `npm run build` -> **PASS** (Compiled in 10.6s, all static routes generated)
- **Backend Avatar Tests:** `pytest tests/test_avatars.py tests/test_avatar_looks.py tests/test_avatar_visual_endpoints.py` -> **PASS** (8 passed, 0 failed)
- **Browser E2E:** **NOT VERIFIED** — no Playwright specs configured.

---

## 8. Service Status

- **Next.js (Port 3000):** ALL RUNNING (PID: 19008)
- **FastAPI (Port 8000):** ALL RUNNING (PID: 18148)
- **PostgreSQL (Port 5432):** ALL RUNNING (PID: 6444)
- **Redis (Port 6379):** ALL RUNNING (PID: 21024)
- **MinIO (Port 9000):** ALL RUNNING (PID: 21024)
- **MinIO Console (Port 9001):** ALL RUNNING (PID: 21024)
- **Docker:** ALL RUNNING
