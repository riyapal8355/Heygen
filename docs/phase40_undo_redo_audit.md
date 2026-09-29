# Phase 40 — Client-side Undo/Redo History
## Read-only Architecture Audit

---

## 1. Executive Summary

This document presents a comprehensive, read-only architectural audit for **Phase 40: Client-side Undo/Redo History** in the HeyZen Studio codebase (`d:\HeyGen\video-ai-tools`).

### Readiness Assessment: **READY FOR PHASE 40 ARCHITECTURE**
The Studio codebase is in an ideal architectural state for introducing client-side undo/redo:
1. **Canonical State is Centralized**: All visual layers (`image`, `video`, `text`, `shape`, `sticker`) and scenes reside in a single top-level React state array `scenes: StudioScene[]` in [VidoAIStudio.tsx](file:///d:/HeyGen/video-ai-tools/src/components/studio/VidoAIStudio.tsx).
2. **Selection State is Well-Defined and Unified**: The three visual selection variables (`selectedMediaLayerId`, `selectedTextLayerId`, `selectedElementLayerId`) are managed under strict mutual exclusion, allowing snapshotting and restoration of exact user focus alongside scene state.
3. **Transient Updates are Decoupled from Backend Commits**: Gestures (canvas drag/resize/rotate, timeline drag/trim, keyboard arrow nudge bursts) already separate high-frequency local React state updates (`setScenes`, `setSaveStatus("unsaved")`) from interaction-end commits (`handleCommitLayerTransform`, `handleCommitTiming`, `handleSave`).
4. **Optimistic Concurrency Control (OCC) is Authoritative**: Backend versioning strictly uses `expected_revision` with auto-incrementing revisions. History is strictly **client-side state management**; undo/redo operations simply restore past scene snapshots and submit them as standard forward OCC revisions.
5. **Zero Backend Changes Required**: No database migrations, no backend table modifications, no new API endpoints, and no changes to rendering pipelines are needed.

---

## 2. Current Mutation Architecture

A systematic audit across all Studio components identified every operation that mutates scene and layer state:

### A. Transform Mutations
- **Canvas Direct Manipulation**:
  - *Source*: [CanvasTransformGizmo.tsx](file:///d:/HeyGen/video-ai-tools/src/components/studio/CanvasTransformGizmo.tsx#L216-L251)
  - *Handlers*: `onTransformChange` calls `handleUpdateLayerTransform(layerId, changes)` updating `scenes` locally; on `pointerup`, `onTransformCommit()` calls `handleCommitLayerTransform()` &rarr; `handleSave()`.
  - *State Mutated*: `layer.transform.{x, y, scale, rotation}`.
  - *OCC Interaction*: Single version created at gesture end.
- **Keyboard Arrow Nudging (Phase 39)**:
  - *Source*: [VidoAIStudio.tsx](file:///d:/HeyGen/video-ai-tools/src/components/studio/VidoAIStudio.tsx#L1476-L1503)
  - *Handlers*: `calculateKeyboardNudge()` &rarr; `handleUpdateLayerTransform()` with 500ms debounced commit `handleCommitLayerTransform()`.
  - *State Mutated*: `layer.transform.{x, y}` (step `0.005`, Shift step `0.05`).
- **Inspector Position Presets & Manual Inputs**:
  - *Source*: [MediaLayerPanel.tsx](file:///d:/HeyGen/video-ai-tools/src/components/studio/MediaLayerPanel.tsx#L193-L230), [TextPanel.tsx](file:///d:/HeyGen/video-ai-tools/src/components/studio/TextPanel.tsx#L212), [ElementsPanel.tsx](file:///d:/HeyGen/video-ai-tools/src/components/studio/ElementsPanel.tsx#L327)
  - *Handlers*: `handleTransformChange`, `handleSetPresetPosition` &rarr; `onUpdate[Media|Text|Element]Layers` &rarr; `handleSave(updated)`.
- **Inspector Opacity Sliders**:
  - *Source*: [MediaLayerPanel.tsx](file:///d:/HeyGen/video-ai-tools/src/components/studio/MediaLayerPanel.tsx#L210), [TextPanel.tsx](file:///d:/HeyGen/video-ai-tools/src/components/studio/TextPanel.tsx#L555), [ElementsPanel.tsx](file:///d:/HeyGen/video-ai-tools/src/components/studio/ElementsPanel.tsx#L313)
  - *Handlers*: Updates `layer.content.opacity` &rarr; `handleSave(updated)`.

### B. Timing Mutations
- **Timeline Clip Dragging (Move)**:
  - *Source*: [timelineUtils.ts](file:///d:/HeyGen/video-ai-tools/src/lib/timelineUtils.ts#L319-L362), tracks in [MediaTimelineTrack.tsx](file:///d:/HeyGen/video-ai-tools/src/components/studio/MediaTimelineTrack.tsx), [TextTimelineTrack.tsx](file:///d:/HeyGen/video-ai-tools/src/components/studio/TextTimelineTrack.tsx), [ElementsTimelineTrack.tsx](file:///d:/HeyGen/video-ai-tools/src/components/studio/ElementsTimelineTrack.tsx)
  - *Handlers*: `useTimelineClipDrag` pointermove calls `onUpdateTiming` (`handleUpdateLayerTiming`); pointerup calls `onCommitTiming` (`handleCommitTiming` &rarr; `handleSave()`).
  - *State Mutated*: `layer.start_time`, `layer.end_time`.
- **Timeline Clip Trimming (Left/Right Handles)**:
  - *Source*: Same `useTimelineClipDrag` with mode `"trim_left"` or `"trim_right"`.
- **Inspector Timing Inputs**:
  - *Source*: [MediaLayerPanel.tsx](file:///d:/HeyGen/video-ai-tools/src/components/studio/MediaLayerPanel.tsx#L163), [TextPanel.tsx](file:///d:/HeyGen/video-ai-tools/src/components/studio/TextPanel.tsx#L224), [ElementsPanel.tsx](file:///d:/HeyGen/video-ai-tools/src/components/studio/ElementsPanel.tsx#L342)
  - *Handlers*: Validates `start < end` and bounds, calls `handleSave(updated)`.
- **Scene Duration Adjustments**:
  - *Source*: [VidoAIStudio.tsx](file:///d:/HeyGen/video-ai-tools/src/components/studio/VidoAIStudio.tsx#L2654-L2678)
  - *Handlers*: Step buttons (-1s, +1s) call `updateActiveScene` & `handleSave()`; slider calls `handleSave()` on `mouseUp`.

### C. Layer Lifecycle Mutations
- **Add Layer**:
  - *Media*: [VidoAIStudio.tsx:886](file:///d:/HeyGen/video-ai-tools/src/components/studio/VidoAIStudio.tsx#L886) (`handleAddMediaLayer`) &rarr; appends layer, selects ID, `handleSave()`.
  - *Text*: [TextPanel.tsx:105](file:///d:/HeyGen/video-ai-tools/src/components/studio/TextPanel.tsx#L105) (`handleAddTextLayer`) &rarr; appends layer, selects ID, `handleSave()`.
  - *Shape / Sticker*: [ElementsPanel.tsx:221, 254](file:///d:/HeyGen/video-ai-tools/src/components/studio/ElementsPanel.tsx#L221) (`handleAddShape`, `handleAddSticker`) &rarr; appends, selects ID, `handleSave()`.
- **Duplicate Layer**:
  - *Buttons*: [MediaLayerPanel.tsx:118](file:///d:/HeyGen/video-ai-tools/src/components/studio/MediaLayerPanel.tsx#L118), [TextPanel.tsx:139](file:///d:/HeyGen/video-ai-tools/src/components/studio/TextPanel.tsx#L139), [ElementsPanel.tsx:273](file:///d:/HeyGen/video-ai-tools/src/components/studio/ElementsPanel.tsx#L273)
  - *Keyboard Shortcut (`Ctrl/Cmd + D`)*: [VidoAIStudio.tsx:1455](file:///d:/HeyGen/video-ai-tools/src/components/studio/VidoAIStudio.tsx#L1455) using `createLayerDuplicatePayload`.
- **Delete Layer**:
  - *Buttons*: [MediaLayerPanel.tsx:141](file:///d:/HeyGen/video-ai-tools/src/components/studio/MediaLayerPanel.tsx#L141), [TextPanel.tsx:152](file:///d:/HeyGen/video-ai-tools/src/components/studio/TextPanel.tsx#L152), [ElementsPanel.tsx:288](file:///d:/HeyGen/video-ai-tools/src/components/studio/ElementsPanel.tsx#L288).
  - *Keyboard Shortcut (`Delete` / `Backspace`)*: [VidoAIStudio.tsx:1506](file:///d:/HeyGen/video-ai-tools/src/components/studio/VidoAIStudio.tsx#L1506).
- **Copy & Paste Layer**:
  - *Copy (`Ctrl/Cmd + C`)*: [VidoAIStudio.tsx:1417](file:///d:/HeyGen/video-ai-tools/src/components/studio/VidoAIStudio.tsx#L1417) &rarr; writes to in-memory `studioClipboardRef.current`.
  - *Paste (`Ctrl/Cmd + V`)*: [VidoAIStudio.tsx:1430](file:///d:/HeyGen/video-ai-tools/src/components/studio/VidoAIStudio.tsx#L1430) &rarr; clones from clipboard ref, appends to `activeScene.layers`, selects, `handleSave()`.
- **Reorder Layer (Bring Forward / Send Backward)**:
  - *Panels*: `handleMoveLayer` in all 3 panels swaps layer indices within the array &rarr; `handleSave(updated)`.

### D. Visibility Mutations
- **Toggle Visibility (`enabled`)**:
  - *Panels*: [MediaLayerPanel.tsx:102](file:///d:/HeyGen/video-ai-tools/src/components/studio/MediaLayerPanel.tsx#L102), [TextPanel.tsx:175](file:///d:/HeyGen/video-ai-tools/src/components/studio/TextPanel.tsx#L175), [ElementsPanel.tsx:308](file:///d:/HeyGen/video-ai-tools/src/components/studio/ElementsPanel.tsx#L308) inverts `layer.enabled !== false` &rarr; `handleSave(updated)`.

### E. Locking Mutations
- **Toggle Locking (`locked`)**:
  - *Panels*: [MediaLayerPanel.tsx:110](file:///d:/HeyGen/video-ai-tools/src/components/studio/MediaLayerPanel.tsx#L110), [TextPanel.tsx:184](file:///d:/HeyGen/video-ai-tools/src/components/studio/TextPanel.tsx#L184), [ElementsPanel.tsx:303](file:///d:/HeyGen/video-ai-tools/src/components/studio/ElementsPanel.tsx#L303) inverts `layer.locked` &rarr; `handleSave(updated)`.

### F. Content Mutations
- **Text Content**: [TextPanel.tsx:485](file:///d:/HeyGen/video-ai-tools/src/components/studio/TextPanel.tsx#L485) `onChange` &rarr; `handleUpdateContent("text", value)`.
- **Typography & Style**: [TextPanel.tsx:199](file:///d:/HeyGen/video-ai-tools/src/components/studio/TextPanel.tsx#L199) font family, font size, weight, colors, alignment.
- **Shape & Sticker Properties**: [ElementsPanel.tsx:313](file:///d:/HeyGen/video-ai-tools/src/components/studio/ElementsPanel.tsx#L313) fill, border width/color, corner radius.
- **Captions & Subtitles**: [CaptionsPanel.tsx](file:///d:/HeyGen/video-ai-tools/src/components/studio/CaptionsPanel.tsx) cue text, font settings.

### G. Timeline & Audio Mutations
- **Audio Track Management**: [VidoAIStudio.tsx:847, 866](file:///d:/HeyGen/video-ai-tools/src/components/studio/VidoAIStudio.tsx#L847) Add / delete / trim audio tracks &rarr; `handleSave(undefined, nextTracks)`.

### H. Scene Mutations
- **Scene CRUD**:
  - Add Scene: [VidoAIStudio.tsx:646](file:///d:/HeyGen/video-ai-tools/src/components/studio/VidoAIStudio.tsx#L646) (`handleAddScene`).
  - Duplicate Scene: [VidoAIStudio.tsx:688](file:///d:/HeyGen/video-ai-tools/src/components/studio/VidoAIStudio.tsx#L688) (`handleDuplicateScene`).
  - Delete Scene: [VidoAIStudio.tsx:705](file:///d:/HeyGen/video-ai-tools/src/components/studio/VidoAIStudio.tsx#L705) (`handleDeleteScene`).
  - Reorder Scene: [VidoAIStudio.tsx:718](file:///d:/HeyGen/video-ai-tools/src/components/studio/VidoAIStudio.tsx#L718) (`handleReorderScene`).
  - Scene Voice / Avatar / Background / Script: `handleVoiceSelect`, `handleAvatarSelect`, `handleSetSceneBackground`, `handleScriptChange`.

---

## 3. Canonical Studio State

The canonical state models are:

### Frontend TypeScript Models (`VidoAIStudio.tsx`, `studioLockingVisibility.ts`, `studioKeyboardUtils.ts`)
```typescript
interface StudioScene {
  id: string;
  sequence: number;
  duration: number;
  title?: string;
  background?: { type: string; value?: string; asset_id?: string | null };
  transition?: { type: string; duration: number } | null;
  avatar?: { avatar_id: string; look_id?: string | null; view_mode?: string; video_asset_id?: string | null; position?: { x: number; y: number; scale: number; rotation: number } } | null;
  speech?: { voice_id: string; script: string; audio_asset_id?: string | null; speed?: number; pitch?: number } | null;
  layers?: any[];
  subtitles?: any[];
}
```

### Layer Storage Architecture
- All visual layers (`image`, `video`, `text`, `shape`, `sticker`) are stored in a **single unified array**: `activeScene.layers: any[]`.
- Panels slice this array dynamically:
  - `mediaLayers = allLayers.filter(l => l.type === "image" || l.type === "video" || l.type === "media")`
  - `textLayers = allLayers.filter(l => l.type === "text")`
  - `elementLayers = allLayers.filter(l => l.type === "shape" || l.type === "sticker" || l.type === "element")`
- Ordering: Render order is strictly array index order (higher index renders in front).
- Phase 38 Flags: `enabled: boolean` (default `true`) and `locked: boolean` (default `false`) reside on each layer object.
- Transforms: `transform: { x: number, y: number, scale: number, rotation: number }` normalized in `[0.0, 1.0]`.

### Backend Pydantic Models (`backend/app/schemas/project_document.py`)
- `ProjectDocumentV1`: Authoritative schema version `1`.
- `SceneLayer`: `id: str`, `type: str`, `name: str`, `start_time: float`, `end_time: float`, `enabled: bool = True`, `locked: bool = False`, `transform: Dict[str, Any]`, `content: Dict[str, Any]`.
- `Scene`: `id: str`, `sequence: int`, `duration: float`, `layers: List[SceneLayer]`, etc.

---

## 4. Persistence/OCC Architecture

### How Mutations Persist
1. **Commit Function**: All mutations eventually invoke:
   ```typescript
   handleSave(updatedScenesList?: StudioScene[], updatedAudioTracksList?: AudioTrackItem[])
   ```
2. **OCC Call**:
   ```typescript
   const updatedVer = await api.projects.createVersion(workspaceId, projectId, {
     expected_revision: revision,
     document: doc,
     source: "studio_manual",
   });
   setCurrentDocument(doc);
   setRevision(updatedVer.revision);
   setSaveStatus("saved");
   ```
3. **Optimistic Concurrency Guarantees**:
   - The backend compares `expected_revision == project.revision`.
   - On match: increments `revision`, commits `project_versions` row, updates `current_version_id`, returns 201.
   - On mismatch: raises `ConcurrencyConflictException` (409). Frontend catches this and sets `saveStatus = "conflict"`.
4. **Transient vs. Persisted Boundaries**:
   - Canvas gestures (`CanvasTransformGizmo`) update local React state on pointermove and only call `handleSave()` on pointerup.
   - Keyboard nudges update React state on keydown and debounce `handleSave()` by 500ms.
   - Timeline drags update React state on pointermove and only call `handleSave()` on pointerup.
   - Lifecycle operations (Add, Delete, Duplicate, Paste) call `handleSave()` immediately.

### Critical Architecture Insight: Client-Side History + Standard OCC Persistence
Undo and redo are **purely client-side state restorations**. When the user presses Undo:
1. The client restores the previous scene state snapshot to React state (`setScenes`).
2. The client commits this restored state to the backend using the **normal** `handleSave()` flow with `expected_revision: revision`.
3. The backend treats this as a regular new forward revision (e.g. revision 5 &rarr; 6).
4. No backend history table manipulation, no rollbacks, no database schema changes, and no revisions rewinding are involved.

---

## 5. Existing Keyboard Architecture (Phase 39)

Phase 39 established the centralized keyboard infrastructure:
- **Location**: [VidoAIStudio.tsx:1370-1562](file:///d:/HeyGen/video-ai-tools/src/components/studio/VidoAIStudio.tsx#L1370)
- **Utilities**: [src/lib/studioKeyboardUtils.ts](file:///d:/HeyGen/video-ai-tools/src/lib/studioKeyboardUtils.ts)
- **Focus Guard**: `isInputOrEditableTarget(e.target)` checks:
  - `tagName === "INPUT" || tagName === "TEXTAREA" || tagName === "SELECT"`
  - `target.isContentEditable === true`
  - `target.closest("[contenteditable='true']")`
  - `target.closest("input, textarea, select")`
  - `target.closest("[data-ignore-studio-shortcuts='true']")`
  - `target.closest("[role='dialog']")`
- **Shortcuts Active**:
  - `Escape`: `clearVisualSelection()`
  - `Space`: `togglePlayback()`
  - `Ctrl/Cmd + C`: Copy active visual layer to `studioClipboardRef`
  - `Ctrl/Cmd + V`: Paste layer from clipboard ref
  - `Ctrl/Cmd + D`: Duplicate active layer
  - `ArrowLeft / Right / Up / Down`: Nudge unlocked layer position
  - `Delete / Backspace`: Delete unlocked layer
- **Reserved for Phase 40**:
  - `Ctrl/Cmd + Z`: Undo
  - `Ctrl/Cmd + Shift + Z` (and `Ctrl/Cmd + Y` on Windows): Redo

---

## 6. History Architecture Options

### Option A: Snapshot History (State-based)
Maintain stacks of immutable scene snapshots:
```typescript
interface StudioHistoryEntry {
  scenes: StudioScene[];
  activeSceneIndex: number;
  selectedLayerId: string | null;
  selectedLayerKind: "media" | "text" | "element" | null;
  description: string;
  timestamp: number;
}
```

### Option B: Command/Operation History (Action-based)
Define reversible action objects:
```typescript
interface UndoCommand {
  type: "move" | "resize" | "delete" | "add" | "timing" | "content" | ...;
  do: () => void;
  undo: () => void;
}
```

### Comparative Evaluation

| Evaluation Criteria | Option A: Snapshot History | Option B: Command History | Codebase Architecture Fit |
| :--- | :--- | :--- | :--- |
| **Implementation Complexity** | **Low**: A single pure history manager managing `undoStack` and `redoStack`. | **Very High**: Requires writing 25+ paired inverse operations (`delete` &harr; `restore`, `move` &harr; `moveBack`, `timing` &harr; `timingBack`, etc.). | **Snapshot wins decisively**. |
| **Correctness & Drift Risk** | **Zero Risk**: Restoring a snapshot guarantees 100% complete state fidelity across all layer fields. | **High Risk**: Any bug in any inverse command leads to cumulative state corruption or desynchronization. | **Snapshot wins**. |
| **Multi-Layer / Array State** | **Seamless**: Scene layer arrays, ordering, and cross-type layers are captured atomically. | **Complex**: Array splices, index shifts, and multi-track interactions must be inverted manually. | **Snapshot wins**. |
| **Selection Restoration** | **Trivial**: Stored directly in snapshot entry; restored atomically with scene data. | **Complex**: Must track which layer ID was targeted by each action. | **Snapshot wins**. |
| **Delete / Restore** | **Trivial**: Deleted layer is completely preserved in previous snapshot. | **Complex**: Must store entire tombstoned layer object + index inside command. | **Snapshot wins**. |
| **Locking & Visibility** | **Trivial**: Preserved exactly as was when snapshot was captured. | **Moderate**: Must ensure undoing a change to a currently-locked layer doesn't violate lock invariants. | **Snapshot wins**. |
| **OCC Persistence Fit** | **Exact Fit**: `handleSave(entry.scenes)` expects full scenes array. | **Poor Fit**: Commands still produce full scenes array for `handleSave`. | **Snapshot wins**. |
| **Memory Consumption** | ~30 KB per snapshot &times; 50 entries = **~1.5 MB RAM**. Negligible in modern browsers. | ~1 KB per command &times; 50 entries = ~50 KB RAM. | Both well within safe limits. |
| **Performance (Cloning)** | `structuredClone` of 30 KB JSON takes **<0.4 ms** on modern V8. | Instantaneous. | Both imperceptible. |

---

## 7. Recommended History Model

**Recommendation: Option A — Pure Snapshot History with Dedicated In-Memory Controller.**

### Architecture Specification
Create a dedicated, pure helper library:
`src/lib/studioHistory.ts`

```typescript
export interface HistorySelectionState {
  activeSceneIndex: number;
  selectedMediaLayerId: string | null;
  selectedTextLayerId: string | null;
  selectedElementLayerId: string | null;
}

export interface HistoryEntry {
  scenes: StudioScene[];
  selection: HistorySelectionState;
  actionName: string;
  timestamp: number;
}

export interface HistoryState {
  past: HistoryEntry[];
  present: {
    scenes: StudioScene[];
    selection: HistorySelectionState;
  };
  future: HistoryEntry[];
  maxEntries: number; // default: 50
}
```

### Core Pure Functions
1. `createHistory(initialScenes: StudioScene[], initialSelection: HistorySelectionState, maxEntries?: number): HistoryState`
2. `pushHistory(state: HistoryState, newScenes: StudioScene[], newSelection: HistorySelectionState, actionName: string): HistoryState`
3. `canUndo(state: HistoryState): boolean` (`state.past.length > 0`)
4. `canRedo(state: HistoryState): boolean` (`state.future.length > 0`)
5. `undo(state: HistoryState): { nextState: HistoryState; entryToRestore: HistoryEntry } | null`
6. `redo(state: HistoryState): { nextState: HistoryState; entryToRestore: HistoryEntry } | null`
7. `clearHistory(state: HistoryState): HistoryState`

---

## 8. History Granularity / Coalescing

Capturing every intermediate mouse move or keystroke in history would ruin the undo experience. History boundaries must strictly correspond to **completed user intents**:

| User Gesture / Action | Raw React Updates | History Strategy | History Boundary Point |
| :--- | :--- | :--- | :--- |
| **Canvas Move Drag** | 30–200 per drag | **Single History Entry** | Capture baseline on `pointerdown`; commit to history on `pointerup` (`onTransformCommit`). |
| **Canvas Corner Resize** | 30–200 per drag | **Single History Entry** | Baseline on `pointerdown`; commit on `pointerup`. |
| **Canvas Rotation** | 30–200 per drag | **Single History Entry** | Baseline on `pointerdown`; commit on `pointerup`. |
| **Timeline Clip Move** | 20–100 per drag | **Single History Entry** | Baseline on `pointerdown`; commit on `pointerup` (`onCommitTiming`). |
| **Timeline Clip Trim** | 20–100 per drag | **Single History Entry** | Baseline on `pointerdown`; commit on `pointerup` (`onCommitTiming`). |
| **Keyboard Nudge Burst** | 5–50 keydowns in burst | **Coalesced History Entry** | Capture snapshot before burst; commit snapshot when 500ms debounce timer fires (`handleCommitLayerTransform`). |
| **Inspector Text Input** | 1 entry per character typed | **Coalesced Edit** | Local state updates on `onChange`; push to history on `onBlur` or debounced commit (similar to scene script). |
| **Inspector Color / Slider** | Dragging color picker / opacity | **Single History Entry** | Push on picker close or slider `mouseUp`. |
| **Add / Delete Layer** | Single click | **Immediate History Entry** | Push immediately before mutating. |
| **Duplicate / Paste** | Single click / shortcut | **Immediate History Entry** | Push immediately before mutating. |
| **Reorder / Lock / Hide** | Single click | **Immediate History Entry** | Push immediately before mutating. |
| **Scene Add / Delete / Reorder** | Single click | **Immediate History Entry** | Push immediately before mutating. |

---

## 9. Undo/Redo Shortcut Safety

### Shortcut Matrix
- **Undo**: `Ctrl + Z` (Windows/Linux) / `Cmd + Z` (macOS)
- **Redo**: `Ctrl + Shift + Z` (macOS/cross-platform) / `Ctrl + Y` (Windows convention)

### Focus & Input Safety Boundary
The future implementation **must not** intercept `Ctrl+Z` / `Ctrl+Shift+Z` / `Ctrl+Y` when the user is typing inside an `<input>`, `<textarea>`, `<select>`, or `contenteditable` element.

The existing focus guard `isInputOrEditableTarget` in [src/lib/studioKeyboardUtils.ts](file:///d:/HeyGen/video-ai-tools/src/lib/studioKeyboardUtils.ts#L34-L69) already handles this cleanly:
```typescript
if (isInputOrEditableTarget(e.target)) {
  // Return immediately — native browser text undo/redo takes over!
  return;
}
```
This guarantees:
- Inside the speech script textarea: `Ctrl+Z` undos text typing inside the textarea natively.
- Inside inspector text inputs: `Ctrl+Z` undos character edits natively.
- Outside inputs (canvas, timeline, empty studio areas): `Ctrl+Z` undos Studio scene mutations.

---

## 10. History Scope

### Evaluation: Per-Scene vs. Whole-Project History
- **Per-Scene History**: History resets or is partitioned by scene.
  - *Problem*: Cannot undo scene addition, scene deletion, scene reordering, or cross-scene operations.
- **Whole-Project History**: Single unified history stack representing the timeline and all scenes.
  - *User Expectation*: Professional video editors (Premiere, Final Cut, After Effects, Canva, CapCut) maintain a **project-wide linear timeline history**. If a user edits Scene 1, moves to Scene 2, and hits Undo, the editor smoothly navigates back to Scene 1 and undos the edit.

### Recommendation
**Whole-Project History Stack with Active Scene & Selection Tracking.**
Each snapshot stores `scenes: StudioScene[]`, `activeSceneIndex: number`, and the layer selection IDs.
When Undo is triggered:
- If the undone mutation occurred in a different scene, `setActiveSceneIndex(entry.selection.activeSceneIndex)` automatically navigates the user back to the affected scene.
- The user sees exactly what changed in context.

---

## 11. Branching Behavior

### Standard Linear Truncation Model
Studio editing follows the standard industry convention:
```text
State A  &rarr;  State B  &rarr;  State C
                   &darr; (Undo)
                 State B
                   &darr; (New Mutation D)
                 State D  (Redo stack containing State C is TRUNCATED)
```
When a new mutation occurs after an undo, any remaining items on the `future` (redo) stack are cleared (`state.future = []`).

---

## 12. Selection Restoration

Undo/redo should restore visual selection so the user immediately knows which layer was affected:

### Specification
1. **Move / Resize / Rotate Undo**: Restores layer coordinates and keeps the layer selected.
2. **Delete Undo**: Restores the deleted layer to the scene and **re-selects it**.
3. **Duplicate / Paste Undo**: Removes the cloned layer and re-selects the **original source layer** (or null if none).
4. **Add Layer Undo**: Removes the newly added layer and resets selection to `null`.
5. **Reorder Undo**: Restores layer array order and maintains selection on the moved layer.

Selection restoration is implemented by recording `HistorySelectionState`:
```typescript
{
  activeSceneIndex: number,
  selectedMediaLayerId: string | null,
  selectedTextLayerId: string | null,
  selectedElementLayerId: string | null,
}
```
When undoing, the studio calls `selectMediaLayer`, `selectTextLayer`, or `selectElementLayer` using the restored IDs.

---

## 13. Locking & Visibility Compatibility (Phase 38)

Phase 38 introduced canonical layer locking (`locked`) and visibility (`enabled`).

### How Undo/Redo Respects Phase 38
1. **Lock State Restoration**:
   - If Layer A was locked, unlocked, moved, and the user undos:
     - Step 1 (undo move): Layer moves back to previous position.
     - Step 2 (undo unlock): Layer returns to `locked === true`.
2. **Restoration Bypass vs UI Mutation Guards**:
   - In UI handlers (`handleUpdateLayerTransform`, `handleDeleteLayer`), mutations are blocked if `layer.locked === true`.
   - Undo/Redo is an internal state restoration mechanism (`setScenes(snapshot)`). It does **not** route through the individual UI mutation handlers. Therefore, it accurately restores earlier snapshots without being blocked by current lock status.
   - Once restored, if the restored layer is locked, the Phase 38 guards (`CanvasTransformGizmo`, `useTimelineClipDrag`, `canDeleteLayerViaKeyboard`) immediately resume protecting it from further manual direct manipulation.
3. **Visibility (`enabled`)**:
   - Fully captured in snapshots and restored accurately.

---

## 14. Clipboard / Duplicate Interaction

### Interaction Rules
1. **Copy (`Ctrl/Cmd + C`)**:
   - Writes to `studioClipboardRef.current`.
   - Does **not** mutate the scene.
   - Produces **zero** history entries.
2. **Paste (`Ctrl/Cmd + V`)**:
   - Mutates `scenes` by appending cloned layer.
   - Pushes previous state to history with description `"Paste Layer"`.
   - Undoing removes the pasted layer and clears/restores selection.
3. **Duplicate (`Ctrl/Cmd + D`)**:
   - Mutates `scenes` by appending cloned layer.
   - Pushes previous state to history with description `"Duplicate Layer"`.
   - Undoing removes the duplicated layer and re-selects the source layer.
4. **Delete after Duplicate**:
   - Step 1 (Duplicate): History has [Base &rarr; Duplicated].
   - Step 2 (Delete): History has [Base &rarr; Duplicated &rarr; Deleted].
   - Undo #1: Restores duplicate layer and selects it.
   - Undo #2: Removes duplicate layer and selects source layer.

---

## 15. Timeline Interaction

### Boundaries for Multi-Track Timeline
1. **Clip Drag / Slip**:
   - `useTimelineClipDrag` tracks gesture state.
   - At drag start (`pointerdown`), baseline snapshot is captured.
   - During dragging, intermediate updates (`onUpdateTiming`) update React state without pushing history.
   - At drag release (`pointerup`), `onCommitTiming` commits the final snapshot to history and calls `handleSave()`.
2. **Clip Trim**:
   - Same boundary: one history entry per completed trim gesture.
3. **Min Clip Duration & Snapping**:
   - Snapping and duration clamping (`MIN_CLIP_DURATION = 0.5s`) happen during drag calculation.
   - The snapshot stored in history represents the final snapped, validated timing.

---

## 16. Scene Switching

### Rules for Scene Switching
1. **Switching Active Scene**:
   - Switching scenes is a **viewport navigation** action, not a content mutation.
   - Navigating between scenes does **not** create a new history entry.
2. **Flushing Pending Debounced Operations**:
   - If a keyboard nudge debounce timer is running when the user switches scenes or navigates away, the pending save must flush before switching.
3. **Scene Change & History Preservation**:
   - History stack is preserved across scene switches within the same project session.
   - Undoing while on Scene 2 an edit made on Scene 1 automatically switches the viewport back to Scene 1.

---

## 17. Performance / Memory

### Metrics & Budgets
- **Typical Scene JSON Size**: 10–50 KB (scenes, layers, text, transforms).
- **History Stack Size**: 50 entries.
- **Total Memory Footprint**: `50 × 30 KB ≈ 1.5 MB`.
- **Cloning Performance**:
  - `structuredClone(scenes)` benchmark: `< 0.4 ms` for 10 scenes with 50 layers.
  - 60 fps frame budget is `16.6 ms`. Cloning takes `< 2.5%` of a single frame budget.
- **Garbage Collection**:
  - Truncated branches and popped entries are standard unreferenced JS objects collected efficiently by V8.

---

## 18. Persistence Semantics

### OCC & Revision Flow During Undo/Redo

```text
[Initial State A]   (revision: 1)
       |
User creates Layer B &rarr; [State B] (revision: 2, saved)
       |
User moves Layer B   &rarr; [State C] (revision: 3, saved)
       |
User hits Ctrl+Z (Undo)
       |
Client restores [State B] to React state
       |
Client calls handleSave(State B) with expected_revision: 3
       |
Backend verifies revision 3 == 3 &rarr; creates revision 4 with document content of State B
       |
Client updates revision to 4, saveStatus = "saved"
```

### Key Semantics Verified:
1. **Does undo create a new persisted version?**
   - **YES**. Undo restores state and commits a new version with the next revision number.
2. **Does undo alter backend version history?**
   - **NO**. Backend version history remains strictly immutable and append-only.
3. **What happens on browser reload?**
   - The browser fetches the latest version from the backend (which reflects the last saved state, including any undo). The client-side undo stack resets for the new session.
4. **What happens if OCC conflict occurs during undo?**
   - Standard conflict handling triggers: `saveStatus = "conflict"`, alerting the user that another session modified the document.

---

## 19. Render / Export Compatibility

- Video rendering (`backend/app/renderers/video_renderer.py`) consumes the canonical `ProjectDocumentV1` JSON.
- Because client-side undo/redo produces valid `StudioScene[]` structures that serialize into `ProjectDocumentV1`, the renderer receives identical, valid layer schemas.
- Visibility (`enabled: false`) is excluded from rendering as established in Phase 38.
- Zero changes to rendering or export pipelines are required.

---

## 20. Backend / Database Impact

- **Backend code changes required**: **NONE**.
- **Database migrations required**: **NONE**.
- **API contract changes required**: **NONE**.
- **Schema changes required**: **NONE**.

The existing `POST /workspaces/{id}/projects/{id}/versions` endpoint already handles arbitrary document payloads with OCC validation.

---

## 21. Proposed Test Strategy

When Phase 40 is implemented, test coverage should be partitioned as follows:

### 1. Pure History Logic Tests (`src/lib/studioHistory.test.ts`)
- `createHistory`: Initializes empty past/future stacks with initial present state.
- `pushHistory`: Adds entry to past, updates present, clears future stack (branch truncation).
- `pushHistory maxEntries`: Enforces capacity limit (e.g. 50), dropping oldest entries FIFO.
- `undo`: Moves present to future, pops past into present, returns restored entry.
- `undo when empty`: Safely returns null, leaves state unchanged.
- `redo`: Moves present to past, pops future into present, returns restored entry.
- `redo when empty`: Safely returns null, leaves state unchanged.
- `selection restoration`: Verifies `HistorySelectionState` is preserved and restored.
- `deep cloning isolation`: Verifies that mutating the current state does not corrupt past history entries.

### 2. Studio Integration Tests
- Keyboard listener shortcuts: `Ctrl+Z` triggers undo; `Ctrl+Shift+Z` and `Ctrl+Y` trigger redo.
- Focus guard: Verifies shortcuts are ignored when typing in input/textarea/contenteditable.
- Canvas drag gesture coalescing: Verifies a drag gesture produces exactly one history push.
- Keyboard nudge debouncing: Verifies repeated arrow presses produce one coalesced history push.

### 3. Studio Regression Baseline
- All existing 82 frontend unit tests continue to pass.
- All existing 98 backend Studio regression tests continue to pass.

---

## 22. Current Regression Baseline

The current baseline was verified during this audit without altering code:

| Test Suite / Check | Result | Details |
| :--- | :--- | :--- |
| **Frontend Unit Tests** (`npx tsx --test src/lib/*.test.ts`) | **PASS** | 82 passed, 0 failed across 21 suites (847 ms). |
| **Backend Studio Regression** (`pytest tests/test_studio_*.py`) | **PASS** | 98 passed, 0 failed across 10 test files (83.47 s). |
| **TypeScript Validation** (`npx tsc --noEmit`) | **PASS** | 0 errors. |
| **Production Build** (`npm run build`) | **PASS** | Compiled in 12.7s; 6/6 static routes generated. |

---

## 23. Browser E2E Status

- **Browser E2E**: **NOT VERIFIED — Playwright browser test suite / binaries unavailable**.
- Exactly matches the baseline status recorded in Phase 38 and Phase 39.

---

## 24. Implementation Plan for Phase 40

When approved to implement Phase 40, execute the following phased plan:

1. **Step 1: Pure History Engine (`src/lib/studioHistory.ts`)**:
   - Implement `HistoryState`, `HistoryEntry`, `HistorySelectionState`.
   - Implement `createHistory`, `pushHistory`, `undo`, `redo`, `canUndo`, `canRedo`.
2. **Step 2: Comprehensive Unit Tests (`src/lib/studioHistory.test.ts`)**:
   - Write 25+ unit tests covering all stack behaviors, limits, coalescing, and edge cases.
3. **Step 3: Wire History Controller in `VidoAIStudio.tsx`**:
   - Maintain `historyRef = useRef<HistoryState>(...)`.
   - Add Undo/Redo toolbar buttons in the top navigation bar with disabled states (`canUndo`, `canRedo`).
   - Wire `Ctrl/Cmd + Z` and `Ctrl/Cmd + Shift + Z` / `Ctrl/Cmd + Y` into the centralized keyboard listener.
   - Record history entries at gesture/action boundaries (canvas commit, timeline commit, nudge debounce, lifecycle actions).
4. **Step 4: Verification**:
   - Run unit tests, backend regression, TypeScript, and production build.

---

## 25. Risks / Open Questions

1. **Risk: Double-saving during Undo**:
   - *Mitigation*: When restoring a snapshot during Undo, call `handleSave(restoredScenes)` and update `historyRef.current` without re-pushing the restored state as a new past entry.
2. **Risk: High-Frequency Typing in Inspector Inputs**:
   - *Mitigation*: Inspector inputs should commit to history on `onBlur` or debounced commit, preventing history bloat during text typing.
3. **Risk: Concurrency Conflict on Undo**:
   - *Mitigation*: Undo uses the standard `expected_revision`. If another user/tab edited the project, the standard 409 conflict dialog protects against silent overwrites.

---

## 26. Final Recommendation

**Proceed with Phase 40 implementation using pure client-side snapshot history.**
- Implement pure engine in `src/lib/studioHistory.ts`.
- Integrate with `VidoAIStudio.tsx` keyboard shortcuts and toolbar.
- Zero backend or database changes.
- All existing Phase 38 (locking/visibility) and Phase 39 (keyboard navigation) guarantees remain strictly preserved.
