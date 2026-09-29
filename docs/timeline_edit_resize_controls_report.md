# HeyZen Studio — Timeline Editing, Resizing & Unlock Controls Report

## 1. Root Cause of Locked Values
Prior to this enhancement, the bottom timeline in `VidoAIStudio.tsx` rendered the first four tracks as static, non-interactive visual `<div>`s:
- **Track 1 (Scene Video Track):** Only supported clicking to switch `activeSceneIndex`. Lacked left and right edge resize handles to adjust scene duration.
- **Track 2 (Avatar Track):** Displayed a static avatar label in a fixed width block based on scene duration. Lacked drag handles, an Edit button to switch to the Avatar catalog/inspector, and a Delete action to remove or clear the avatar from the scene.
- **Track 3 (Script / Text Track):** Rendered a static speech script preview block. Had no timing handles, no direct button to open the script editor, and no clear/delete capability.
- **Track 4 (Speech Audio Track):** Rendered static voice name and WAV tag. Had no edge handles to trim speech audio duration, no button to configure voice settings, and no delete action.
- **Left Track Rail Labels:** The left rail labels for Scene, Avatar, Script, and Speech lacked `onClick` event handlers, whereas Music, Captions, Text, Media, and Elements had click handlers to open their respective inspector tools.

## 2. Files Changed
1. **`src/lib/timelineUtils.ts`**:
   - Added `calculateSceneResizeTiming`: computes clamped, snapped duration for scene resizing (min 1.0s, max 60.0s).
   - Added `clampLayersToSceneDuration`: clamps child layers (visual layers, cues, etc.) when a scene's duration is shrunk, ensuring no orphaned timestamps exist beyond the new scene duration.
2. **`src/components/studio/VidoAIStudio.tsx`**:
   - Added `timelineTracksContainerRef` for coordinate and zoom scale resolution.
   - Added deletion handlers: `handleDeleteAvatar`, `handleDeleteScript`, `handleDeleteSpeechAudio`, `handleDeleteLayer` (with multi-selection group deletion support), and `handleDeleteCue`.
   - Added interactive edge resize handlers: `startResizeScene`, `startResizeAvatar`, and `startResizeSpeech`.
   - Enhanced Left Track Labels (Scene, Avatar, Script, Speech) with click handlers to immediately activate inspector panels.
   - Updated tracks 1–4 with subtle left/right resize handles, `cursor-ew-resize`, and hover/selection `[Edit]` (✎) and `[Delete]` (🗑) action buttons.
   - Connected `onDeleteTrack`, `onDeleteCue`, and `onDeleteLayer` handlers to tracks 5–9 (`MusicTimelineTrack`, `CaptionTimelineTrack`, `TextTimelineTrack`, `MediaTimelineTrack`, `ElementsTimelineTrack`).
   - Added `start_time` and `end_time` optional fields to `StudioScene['avatar']` and `StudioScene['speech']`.
3. **`src/components/studio/TextTimelineTrack.tsx`**:
   - Added hover/selection Edit (✎) and Delete (🗑) buttons to text overlay clips.
   - Integrated `onDeleteLayer` prop.
4. **`src/components/studio/MediaTimelineTrack.tsx`**:
   - Added hover/selection Edit (✎) and Delete (🗑) buttons to media overlay clips.
   - Integrated `onDeleteLayer` prop.
5. **`src/components/studio/ElementsTimelineTrack.tsx`**:
   - Added hover/selection Edit (✎) and Delete (🗑) buttons to element overlay clips.
   - Integrated `onDeleteLayer` prop.
6. **`src/components/studio/CaptionTimelineTrack.tsx`**:
   - Added hover/selection Edit (✎) and Delete (🗑) buttons to subtitle/caption cues.
   - Integrated `onDeleteCue` prop.
7. **`src/components/studio/MusicTimelineTrack.tsx`**:
   - Added hover/selection Edit (✎) and Delete (🗑) buttons to background music clips.
   - Integrated `onDeleteTrack` prop.
8. **`src/lib/timelineResizeControls.test.ts`**:
   - Added 13 comprehensive automated unit tests covering all 12 timeline editing scenarios.

## 3. Resize Implementation
- **Left Edge Handle (`startResizeScene`, `startResizeAvatar`, `startResizeSpeech`, `calculateLeftTrimTiming`):**
  - Dragging the left edge shifts `start_time` while strictly pinning `end_time`.
  - Drag deltas are computed using pixel-to-second conversion: `deltaSeconds = (clientX - startX) * (totalDuration / containerWidth)`.
  - When resizing Scene 01's right edge or Scene 02's left boundary, adjoining scene durations adapt smoothly without creating timing gaps or overlap.
- **Right Edge Handle (`startResizeScene`, `startResizeAvatar`, `startResizeSpeech`, `calculateRightTrimTiming`):**
  - Dragging the right edge shifts `end_time` / `duration` while strictly preserving `start_time`.
- **Duration Safety Constraints:**
  - Enforces safe minimum durations (`MIN_CLIP_DURATION = 0.5s` for clips, `1.0s` for scenes).
  - Clamps upper boundaries to scene duration (`maxDuration = 60.0s` for scenes).
  - Automatically invokes `clampLayersToSceneDuration` when scene duration decreases, keeping all child layers and cues valid.

## 4. Four Unlocked Values/Controls
1. **Scene Duration (Track 1):** Unlocked from fixed 5s blocks; draggable left and right handles allow resizing from 1.0s up to 60.0s per scene.
2. **Avatar Timing & Placement (Track 2):** Unlocked from static scene span; supports left/right edge trimming, direct Edit button to open the Avatar catalog/inspector, and Delete button to remove avatar with undo/redo.
3. **Script Editor & Timing (Track 3):** Unlocked from read-only text view; supports edge trimming, direct Edit button to switch to the Scene/Script inspector, and Clear/Delete button.
4. **Speech Audio Controls & Trimming (Track 4):** Unlocked from read-only audio badge; supports edge trimming, direct Edit button to configure voice attributes, and Delete button to remove generated audio assets.

## 5. Edit Implementation
- Clicking the compact Pencil icon (✎) on hover or selection directs the studio to the item's corresponding inspector panel:
  - **Scene:** Opens Scene settings inspector (`activeLeftTool: "scenes"`, `activeTab: "scene"`).
  - **Avatar:** Opens Avatar catalog inspector (`activeLeftTool: "avatar"`, `activeTab: "avatar"`).
  - **Script:** Opens Scene/Script inspector (`activeLeftTool: "scenes"`, `activeTab: "scene"`).
  - **Speech:** Opens Voice & Audio inspector (`activeLeftTool: "voice"`, `activeTab: "voice"`).
  - **Music:** Opens Background Music panel (`activeLeftTool: "music"`, `activeTab: "music"`).
  - **Captions:** Opens Subtitles/Captions inspector (`activeLeftTool: "captions"`, `activeTab: "captions"`).
  - **Text:** Opens Text inspector (`activeLeftTool: "text"`, `activeTab: "text"`).
  - **Media:** Opens Media library inspector (`activeLeftTool: "media"`, `activeTab: "media"`).
  - **Elements:** Opens Elements & Shapes inspector (`activeLeftTool: "elements"`, `activeTab: "elements"`).
- Uses `e.stopPropagation()` to prevent conflicting drag or playback seek events.

## 6. Delete Implementation
- Compact Trash icon (🗑) appears on clip hover or selection.
- Deleting updates Studio scene state, re-normalizes z-indices with `deleteLayerWithZIndex`, updates the central canvas, and synchronizes the timeline.
- If multiple items are selected (`selectedLayerIds.length > 1`), deleting triggers `groupDeleteLayers` to delete all selected items at once.
- Triggers notifications (e.g., `"Deleted layer"`, `"Avatar removed from scene."`).

## 7. Undo/Redo Behavior
- Leverages the existing `commitStudioHistory` system in `studioHistory.ts`.
- Every deletion and resize operation commits a discrete snapshot:
  - Action names: `"Delete Layer"`, `"Delete Avatar"`, `"Delete Script"`, `"Delete Speech Audio"`, `"Delete Scene"`, `"Delete Group"`, `"Resize Scene Duration"`, `"Resize Avatar Timing"`.
- Pressing `Ctrl+Z` (or clicking top bar Undo button) fully restores the previous document snapshot, including timing, layers, avatars, and selection state.
- Pressing `Ctrl+Shift+Z` / `Ctrl+Y` (or clicking Redo button) reapplies the change.

## 8. Multi-Selection Behavior
- Fully compatible with `studioMultiSelection.ts` and `selectedLayerIds`.
- When multiple layers are selected:
  - Resizing operates on the specific handle targeted by the pointer gesture.
  - Deleting deletes all compatible selected layers in a single batch with single-step undo restoration.
  - Selection highlights remain synchronized across the timeline lanes and central canvas.

## 9. Split Compatibility
- Split (S shortcut) functionality remains 100% intact:
  - Each split clip half retains independent `start_time` and `end_time`.
  - Both pieces can be independently resized from their left and right handles.
  - Both pieces can be independently selected, edited, or deleted.

## 10. Zoom Compatibility
- Timeline horizontal zoom (50% to 200%+, `MIN_TIMELINE_ZOOM = 0.5`, `MAX_TIMELINE_ZOOM = 3.0`) dynamically adjusts container lane width (`minWidth: Math.round(timelineZoom * 100)%`).
- The resize handlers reference `timelineTracksContainerRef.current.getBoundingClientRect().width` to calculate `secondsPerPixel = totalDuration / containerWidth`.
- Resize handles remain pixel-aligned at clip edges regardless of zoom level.

## 11. Persistence Result
- Mutations invoke the existing `handleSave(nextScenes)` persistence mechanism.
- Concurrency and optimistic locking via OCC document revision numbers are preserved.
- Resized durations, updated start/end timestamps, and deletions persist across page reloads.

## 12. TypeScript Result
- Command: `npx tsc --noEmit`
- Result: **PASS** (0 errors).

## 13. Frontend Test Result
- Command: `npm test` (`npx tsx --test src/lib/*.test.ts`)
- Result: **PASS** — 279 tests across 75 test suites passed (0 failures, 0 skipped).

## 14. Build Result
- Command: `npm run build` (`next build` with Turbopack)
- Result: **PASS** — Compiled successfully; static pages generated (6/6).

## 15. Browser E2E Status
- **BROWSER E2E NOT VERIFIED — no Playwright specs configured.**

## 16. Services Status
All core development services verified active and responsive:
- **FastAPI Backend (port 8000):** Running (HTTP 200 on `/docs`).
- **Next.js Dev Server (port 3000):** Running (HTTP 200 on `/`).
- **Docker Containers:**
  - `heyzen-postgres`: Healthy (Up, port 5432)
  - `heyzen-redis`: Healthy (Up, port 6379)
  - `heyzen-minio`: Healthy (Up, ports 9000 & 9001)
