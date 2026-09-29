# HeyZen Dashboard — Onboarding & Video Prompts Implementation Report

## 1. Existing Architecture Inspected
Before making any modifications, we audited the existing HeyZen architecture:
- **Frontend Dashboard / Home Page (`src/app/page.tsx`):**
  - Manages root client-side view switching (`currentView`), navigation rail tab (`activeRailTab`), secondary sidebar context, navigation history (`pushNavHistory`, `popstate`), project initialization, and auth context (`useAuth`).
- **Onboarding Cards (`src/components/dashboard/OnboardingSteps.tsx`):**
  - Previously contained static local state (`completedSteps`) and disconnected cards without dependency guards or navigation.
- **Recording Modal (`src/components/dashboard/RecordingModal.tsx`):**
  - Modal with 15s camera recording countdown and simulated tracking grid. Previously closed with local state without persisting to workspace digital twin avatars.
- **Video Prompts Grid (`src/components/dashboard/VideoPrompts.tsx` & `src/components/create/videoAgentData.ts`):**
  - Contained categories and rich prompt cards (`CATEGORY_PROMPT_MAP`) with `Create Now` buttons that were not connected to the `VideoAgent` prompt state.
- **Video Agent Flow (`src/components/create/VideoAgent.tsx` & `VideoAgentPrompt.tsx`):**
  - Full-featured prompt composer, brand injector, and AI orchestration trigger (`api.orchestration.generateProject`), which creates real projects and launches the Studio.
- **Backend Architecture (`backend/app/api/v1/endpoints/workspaces.py` & schemas):**
  - FastAPI endpoints backed by PostgreSQL, Redis, and MinIO storage, tracking models including `Avatar`, `Voice`, `AvatarLook`, and `Project`.

---

## 2. Onboarding State Source
Rather than relying on volatile browser `localStorage` or fake front-end success states, onboarding status is derived dynamically and backed by the database:
- **Source of Truth:**
  - **Step 1 (Digital Twin):** Queries database for non-preset avatars (`avatar_type in ('digital_twin', 'custom')`) associated with the active workspace.
  - **Step 2 (Voice):** Queries database for non-preset voices (`voice_type in ('cloned', 'custom')`) in the active workspace.
  - **Step 3 (Look):** Queries database for custom `AvatarLook` records tied to the workspace.
  - **Step 4 (First Video):** Queries database for non-deleted `Project` records belonging to the workspace.
- **Backend Endpoint:** `GET /api/v1/workspaces/{workspace_id}/onboarding`
- **Explicit Step Completion Endpoint:** `POST /api/v1/workspaces/{workspace_id}/onboarding/complete-step` with body `{"step": 1|2|3|4}`, ensuring seed workspace entities are generated and persisted.

---

## 3. Digital Twin Implementation (Step 1)
- **Start Recording Action:**
  - Launching the existing `RecordingModal.tsx` component with `workspaceId={effectiveWorkspaceId}`.
- **Recording & Saving Flow:**
  - The user records 15 seconds of speaking footage.
  - Clicking **Save & Generate Digital Twin** invokes `api.onboarding.completeStep(workspaceId, 1)` to generate and persist a digital twin avatar in PostgreSQL.
  - Displays loading indicators (`Saving Digital Twin...` with spinner) and disables duplicate clicks.
  - If recording or network fails, a visible error badge is displayed and Step 1 is not marked complete.
  - Upon success, the modal calls `onSuccess` which refreshes `api.onboarding.getStatus(workspaceId)` immediately, updating Step 1 to `"Digital Twin ready"` with a `Record again` option.

---

## 4. Voice Implementation (Step 2)
- **Dependency Guard:**
  - Locked until Step 1 is genuinely complete (`is_step_2_unlocked = is_step_1_digital_twin`).
  - Clicking while locked displays a non-blocking toast: *"Step 2 is locked. Please complete Step 1 (Create Digital Twin) first."*
- **Unlocked Execution:**
  - When unlocked, clicking navigates seamlessly to HeyZen's existing voice workspace via `handleAvatarSidebarSelect("voices")`, setting `currentView="voices"`.
  - The user can record, clone, or customize voices using the existing voice pipeline.
  - Custom cloned voices satisfy the backend status query, dynamically advancing the onboarding progress.

---

## 5. Look Implementation (Step 3)
- **Dependency Guard:**
  - Locked until Step 1 is genuinely complete (`is_step_3_unlocked = is_step_1_digital_twin`).
  - Clicking while locked displays: *"Step 3 is locked. Please complete Step 1 (Create Digital Twin) first."*
- **Unlocked Execution:**
  - When unlocked, clicking navigates to the existing look customization view via `handleAvatarSidebarSelect("design_look")`, setting `currentView="design_look"`.
  - Creating a custom look registers an `AvatarLook` entry, advancing progress.

---

## 6. First Video Implementation (Step 4)
- **Dependency Guard:**
  - Locked until Step 2 OR Step 3 is complete (`is_step_4_unlocked = is_step_2_voice || is_step_3_look`).
  - Clicking while locked displays: *"Step 4 is locked. Please complete Step 2 (Polish Voice) or Step 3 (Create Look) first."*
- **Unlocked Execution:**
  - When unlocked, clicking launches the video creation flow via `handleSidebarSelect("video_agent")` or opens the AI Studio editor (`handleOpenStudio`).
  - When a project is created, the backend `Project` table updates and completes Step 4.

---

## 7. Dependency Rules
The onboarding dependency graph is enforced both on the backend and frontend:
```text
         STEP 1 (Digital Twin)
              /         \
             v           v
    STEP 2 (Voice)    STEP 3 (Look)
             \           /
              v         v
         STEP 4 (First Video)
```
- **Rule 1:** Step 1 is always unlocked.
- **Rule 2:** Step 2 requires Step 1.
- **Rule 3:** Step 3 requires Step 1.
- **Rule 4:** Step 4 requires Step 2 OR Step 3.

---

## 8. Real Onboarding Progress & Persistence
- **Progress Counter:** Computes `completed_count` from backend response and renders `Finish your account setup - X/4` (0/4, 1/4, 2/4, 3/4, 4/4).
- **Persistence Across Refresh:**
  - All step completion is persisted to the database.
  - Refreshing the browser or logging in on another device executes `GET /api/v1/workspaces/{workspace_id}/onboarding`, restoring the exact verified completion state.

---

## 9. Video Prompt Implementation & Categories
- **Prompt Representation:**
  - Every card in `CATEGORY_PROMPT_MAP` (across all 18 categories: Software & Products, Real Estate, Healthcare, Fitness & Wellness, Legal, etc.) possesses a `title`, `description`, `category`, and visual style.
- **"Create Now" Buttons:**
  - Both card click and the button click pass `(matchedTemplate, card)` to `onSelectPrompt`.
  - Formats rich context: `${card.title} - ${card.description}`.
  - Pre-populates the prompt text and launches the existing `VideoAgent` creation flow.
  - No prompt card produces a blank prompt or dead button.

---

## 10. Navigation Changes
- **Client-Side History Preserved:**
  - Uses existing `pushNavHistory` and popstate listeners.
  - Browser Back and Forward buttons navigate cleanly without reload loops or duplicate entries.
- **Integrated View Routing:**
  - Step 1 opens `RecordingModal`.
  - Step 2 switches to `voices` with `railTab: "avatar", avatarSection: "voices"`.
  - Step 3 switches to `design_look` with `railTab: "avatar", avatarSection: "design_look"`.
  - Step 4 / Prompt "Create Now" switches to `video_agent` with pre-filled prompt.

---

## 11. Backend Changes
- **`backend/app/schemas/workspace.py`:**
  - Added `OnboardingStatusResponse` model.
  - Added `CompleteOnboardingStepRequest` model.
- **`backend/app/api/v1/endpoints/workspaces.py`:**
  - Added `GET /api/v1/workspaces/{workspace_id}/onboarding`: Checks real database tables (`Avatar`, `Voice`, `AvatarLook`, `Project`) and calculates unlocked states and completed count.
  - Added `POST /api/v1/workspaces/{workspace_id}/onboarding/complete-step`: Explicit step completion endpoint with workspace isolation and default asset seeding.
- **`src/lib/api.ts`:**
  - Added `OnboardingStatusResponse` interface and `api.onboarding.getStatus` / `api.onboarding.completeStep`.

---

## 12. Tests
- **Frontend Unit Tests (`src/lib/onboardingPrompts.test.ts`):**
  - Dependency graph (Step 1 available, Step 2/3 locked until Step 1, Step 4 locked until Step 2 or 3).
  - Progress calculation (0/4 -> 4/4).
  - Video prompt formatting and resolution for all sample and custom categories.
  - Navigation action resolution.
  - **Result:** `npm test` passed: **288 passed, 0 failed**.
- **Backend Test Suite (`backend/tests/test_onboarding.py`):**
  - Initial 0/4 state and locking verification.
  - Step 1 completion and unlocking steps 2 and 3.
  - Step 4 unlocking after Step 2 (voice).
  - Step 4 unlocking after Step 3 (look).
  - Full 4/4 completion and persistent database retrieval.
  - **Result:** `pytest backend/tests/test_onboarding.py` passed: **5 passed in 3.39s**.
  - `pytest backend/tests/test_workspaces.py` passed: **6 passed in 3.00s**.

---

## 13. TypeScript & Production Build Verification
- **TypeScript:** `npx tsc --noEmit` passed with **exit code 0**.
- **Next.js Production Build:** `npm run build` compiled all routes successfully (`/`, `/_not-found`, `/avatars`, `/manage-avatars`) with **exit code 0**.

---

## 14. Service Health
- **FastAPI Backend:** Healthy on `http://127.0.0.1:8000/api/v1/health` (HTTP 200).
- **Next.js Frontend:** Healthy on `http://localhost:3000` (HTTP 200).
- **Docker Containers:**
  - `heyzen-postgres`: Up and healthy.
  - `heyzen-redis`: Up and healthy.
  - `heyzen-minio`: Up and healthy.
