# Phase 39 — Studio Keyboard Navigation & Shortcuts Architectural Audit

## 1. Executive Summary

This document presents a comprehensive, read-only architectural audit for **Phase 39: Studio Keyboard Navigation & Shortcuts** in HeyZen Studio (`d:\HeyGen\video-ai-tools`).

### Readiness Assessment: **READY FOR IMPLEMENTATION**
The existing studio architecture is well-positioned for keyboard controls. The foundation established in Phase 34 (canvas direct manipulation and normalized coordinates), Phase 33 (timeline track synchronization), and Phase 38 (canonical layer locking and visibility unification) provides clean, centralized state interfaces. 

Specifically:
1. **Selection State is Unified**: `selectedMediaLayerId`, `selectedTextLayerId`, and `selectedElementLayerId` operate under mutual exclusion via canonical selection helpers in `VidoAIStudio.tsx`.
2. **Transform Pipeline is Normalized**: `handleUpdateLayerTransform` and `handleCommitLayerTransform` in `VidoAIStudio.tsx` already decouple transient local updates (`unsaved`) from backend OCC version commits (`createVersion`).
3. **Lock & Visibility Semantics are Canonical**: Phase 38's `locked` and `enabled` attributes, along with `src/lib/studioLockingVisibility.ts` guards, provide the exact boundary required to ensure locked layers cannot be mutated by keyboard commands.
4. **Duplication Patterns are Consistent**: All layer types (`media`, `text`, `shape`, `sticker`) have established duplication logic with unique ID generation and coordinate offsetting.

Adding keyboard shortcuts requires zero database migrations, zero schema changes, zero backend modifications, and zero alterations to production video rendering. The entire capability can be implemented through a dedicated, pure helper library (`src/lib/studioKeyboardShortcuts.ts`) and a disciplined global listener with strict input focus guards.

---

## 2. Current Keyboard Infrastructure

A repository-wide audit of keyboard handling revealed:
- **Global Studio Listeners**: **Zero (0)**. There are currently no `window.addEventListener("keydown")` or root-level key listeners in `src/components/studio/` or `VidoAIStudio.tsx`.
- **Component-Level Listeners in Studio**: **Zero (0)**. Neither `CanvasTransformGizmo.tsx`, `MediaLayerPanel.tsx`, `TextPanel.tsx`, `ElementsPanel.tsx`, nor any timeline track implements `onKeyDown` or `onKeyUp`.
- **Existing Keyboard Handling in Repository**: Confined entirely to non-Studio modal/dashboard interactions:
  - `AttachAssetModal.tsx`, `ChooseBrandSystemModal.tsx`, `ChooseAvatarModal.tsx`, `ContinueVideoModal.tsx`, `CreateAvatarModal.tsx`, `KnowledgeHubModal.tsx`, `TemplateConfigModal.tsx`, and `TranslateVideos.tsx` listen for `Escape` to dismiss modals.
  - Form inputs in `ProjectsManager.tsx`, `DevelopersManager.tsx`, and `AskRhysWidget.tsx` listen for `Enter` to submit.
- **Clipboard Access in Repository**:
  - Existing components use `navigator.clipboard?.writeText(...)` for copying text strings (project IDs, API keys, URLs) in `DevelopersManager.tsx`, `BrandSystems.tsx`, and `SceneByScene.tsx`.
  - There is currently no clipboard handling or layer serialization for Studio canvas items.

---

## 3. Selection Architecture

### 3.1 State Representation
Studio layer selection is managed in [VidoAIStudio.tsx](file:///d:/HeyGen/video-ai-tools/src/components/studio/VidoAIStudio.tsx) using three mutually-exclusive state variables:
```typescript
const [selectedTextLayerId, setSelectedTextLayerId] = useState<string | null>(null);
const [selectedMediaLayerId, setSelectedMediaLayerId] = useState<string | null>(null);
const [selectedElementLayerId, setSelectedElementLayerId] = useState<string | null>(null);
```

Mutual exclusion is enforced by three canonical selection callbacks:
- `selectMediaLayer(id: string | null)`: sets `selectedMediaLayerId`, nullifies text and element selections.
- `selectTextLayer(id: string | null)`: sets `selectedTextLayerId`, nullifies media and element selections.
- `selectElementLayer(id: string | null)`: sets `selectedElementLayerId`, nullifies media and text selections.
- `clearVisualSelection()`: sets all three IDs to `null`.

Additional secondary selections exist for non-visual track items:
- `selectedCueId: string | number | null` (subtitle cues)
- `activeAudioTrackId: string | null` (background music tracks)
- `activeSceneIndex: number` (current scene in the sequence)

### 3.2 Canonical Active Layer Resolution
Because only one visual layer ID can be active at a time, the active layer for any keyboard command resolves deterministically:
```typescript
const activeSelectedLayerId = selectedMediaLayerId || selectedTextLayerId || selectedElementLayerId;

const activeSelectedLayer = useMemo(() => {
  if (!activeScene?.layers || !activeSelectedLayerId) return null;
  return activeScene.layers.find((l: any) => l.id === activeSelectedLayerId) || null;
}, [activeScene?.layers, activeSelectedLayerId]);
```

### 3.3 Selection Flow During Deletion
When a layer is deleted via any panel (`MediaLayerPanel`, `TextPanel`, `ElementsPanel`):
1. The target layer is filtered out of the scene's layer array.
2. If the deleted layer was currently selected:
   - `MediaLayerPanel` selects `updated[0]?.id || null`.
   - `TextPanel` selects `remaining[0]?.id || null`.
   - `ElementsPanel` selects `updated[0]?.id || null`.
3. If no layers remain of that type, the selection resolves to `null`.

---

## 4. Shortcut Matrix

| Shortcut | Proposed Action | Existing Support | Conflicts | Implementation Complexity |
| :--- | :--- | :--- | :--- | :--- |
| **ArrowLeft** | Nudge layer left (`x - 0.005`) | None (canvas mouse drag only) | Caret navigation in `<input>` / `<textarea>` | Low (requires focus guard) |
| **ArrowRight** | Nudge layer right (`x + 0.005`) | None (canvas mouse drag only) | Caret navigation in `<input>` / `<textarea>` | Low (requires focus guard) |
| **ArrowUp** | Nudge layer up (`y - 0.005`) | None (canvas mouse drag only) | Caret navigation in `<input>` / `<textarea>` | Low (requires focus guard) |
| **ArrowDown** | Nudge layer down (`y + 0.005`) | None (canvas mouse drag only) | Caret navigation in `<input>` / `<textarea>` | Low (requires focus guard) |
| **Shift + ArrowLeft** | Large nudge left (`x - 0.05`) | None | Text selection in inputs | Low (requires focus guard) |
| **Shift + ArrowRight** | Large nudge right (`x + 0.05`) | None | Text selection in inputs | Low (requires focus guard) |
| **Shift + ArrowUp** | Large nudge up (`y - 0.05`) | None | Text selection in inputs | Low (requires focus guard) |
| **Shift + ArrowDown** | Large nudge down (`y + 0.05`) | None | Text selection in inputs | Low (requires focus guard) |
| **Delete** | Delete active visual layer | Panel button only | Forward character delete in inputs | Low-Medium (requires lock & focus guard) |
| **Backspace** | Delete active visual layer | Panel button only | Backspace character delete in inputs; browser Back nav | Low-Medium (requires lock & focus guard) |
| **Escape** | Deselect active layer | None (`clearVisualSelection` exists) | Modal dismissal, input blur | Low (blur input first, deselect second) |
| **Space** | Toggle playback (play/pause) | Play button only (`togglePlayback`) | Page scroll, typing spaces in script | Medium (strict input & editable guards) |
| **Ctrl/Cmd + C** | Copy active layer to in-memory clipboard | None | Native text copy inside inputs | Low-Medium (bypass if text is focused) |
| **Ctrl/Cmd + V** | Paste layer into active scene | None | Native text paste inside inputs | Medium (in-memory deserialization & OCC) |
| **Ctrl/Cmd + D** | Duplicate active layer | Panel duplicate button only | Browser "Bookmark Page" shortcut | Medium (`preventDefault` required) |

---

## 5. Input / Focus Safety Architecture

Keyboard shortcut handlers in complex web apps frequently cause critical bugs when users type in textareas or inputs (e.g. typing space in a script pauses video; pressing backspace deletes a layer; arrow keys move a layer instead of moving the text caret).

### 5.1 Elements Requiring Protection
The Studio contains more than 30 interactive input fields:
1. **Script Textarea**: `<textarea>` for scene speech script (`VidoAIStudio.tsx:2365`).
2. **Project Title Input**: `<input>` in top navigation (`VidoAIStudio.tsx:1475`).
3. **Inspector Inputs**:
   - `TextPanel`: text content textarea, font size input, hex color input, timing inputs, opacity sliders.
   - `MediaLayerPanel`: timing inputs, scale/opacity sliders, position inputs.
   - `ElementsPanel`: shape dimensions, fill color, border color, corner radius, opacity inputs.
   - `CaptionsPanel`: cue text textareas, cue start/end timestamp inputs.
4. **Search Inputs**: voice catalog search, avatar catalog search, media asset search.
5. **Modal Inputs**: upload modal, asset selector dialogs.

### 5.2 Recommended Focus Guard Strategy
A centralized pure guard function must be used on every `keydown` event:

```typescript
export function isInputOrEditableTarget(target: EventTarget | null): boolean {
  if (!target || !(target instanceof HTMLElement)) return false;
  
  const tagName = target.tagName.toLowerCase();
  if (tagName === "input" || tagName === "textarea" || tagName === "select") {
    return true;
  }
  
  if (target.isContentEditable) {
    return true;
  }
  
  // Guard against active modal dialogs that handle their own keys
  if (target.closest("[role='dialog']") || target.closest("[data-ignore-studio-shortcuts='true']")) {
    return true;
  }
  
  return false;
}
```

When `isInputOrEditableTarget(e.target)` is `true`:
- `Space` must NOT toggle playback.
- `Delete` and `Backspace` must NOT delete layers.
- Arrow keys must NOT nudge layers.
- `Ctrl/Cmd + C` and `Ctrl/Cmd + V` must NOT intercept layer clipboard operations (native OS text copy/paste must proceed uninhibited).
- **Special handling for `Escape`**: If focused inside an input, `Escape` should blur the input (`(e.target as HTMLElement).blur()`) without clearing the visual layer selection. A subsequent `Escape` press while blurred can then clear the visual selection.

---

## 6. Locked Layer Interaction

Phase 38 introduced canonical locking via `layer.locked: boolean = false`.

### 6.1 Action Matrix for Locked Layers

| Keyboard Action | Unlocked Layer (`locked !== true`) | Locked Layer (`locked === true`) | Architectural Rationale |
| :--- | :--- | :--- | :--- |
| **Arrow Nudge** | Mutates `x, y` within bounds | **STRICTLY BLOCKED** | Nudging modifies geometry; locked layers are protected from spatial change. |
| **Shift + Arrow** | Mutates `x, y` by large step | **STRICTLY BLOCKED** | Same as above. |
| **Delete / Backspace** | Removes layer from scene | **STRICTLY BLOCKED** | Professional design convention (Figma, After Effects, Canva): keyboard deletion must NEVER delete locked layers to prevent accidental destruction of protected background plates/templates. |
| **Duplicate (Ctrl+D)** | Clones layer with offset | **ALLOWED** (Clone is unlocked) | Reading a locked layer to duplicate it is harmless. The newly created copy will have `locked: false`. |
| **Copy (Ctrl+C)** | Copies layer to clipboard | **ALLOWED** | Read-only operation; does not alter state. |
| **Paste (Ctrl+V)** | N/A (Pastes clipboard) | **ALLOWED** | Operates on target scene; unaffected by source lock. |
| **Space (Playback)**| Toggles playback | **INDEPENDENT** | Playback is a global scene action unrelated to layer locking. |

---

## 7. Visibility Interaction (`enabled = false`)

In Phase 38, canonical visibility is represented by `enabled: boolean = true`.

### 7.1 Existing Behavior
- On Canvas: Layers with `enabled === false` are filtered out of `activeMediaLayers`, `activeTextLayers`, and `activeElementLayers`. They are NOT rendered on the canvas viewport, and no `CanvasTransformGizmo` is displayed for them.
- On Timeline and Panels: Hidden layers remain listed with dimmed styling, an `EyeOff` indicator, and can still be selected via timeline click or panel list click.

### 7.2 Keyboard Rules for Hidden Layers
1. **Arrow Keys (Nudge)**:
   - If a hidden layer is selected via the timeline or panel: **BLOCK NUDGE**. Nudging an invisible layer on canvas without visual feedback is error-prone and violates predictable direct manipulation principles.
2. **Delete / Backspace**:
   - If a hidden layer is selected (and not locked): **ALLOW DELETE**. Users frequently clean up unused or hidden layers via timeline/panel selection and the Delete key.
3. **Duplicate / Copy / Paste**:
   - **ALLOW DUPLICATE / COPY**. The duplicated layer inherits `enabled: false`.

---

## 8. Persistence & Concurrency (OCC) Strategy

### 8.1 The High-Frequency Keydown Problem
When a user holds down an arrow key, the OS keyboard auto-repeat fires `keydown` events at 30 to 60 times per second.
If each keydown event called:
```typescript
await api.projects.createVersion(workspaceId, projectId, { expected_revision, document })
```
The application would:
1. Dispatch 30–60 concurrent HTTP requests per second.
2. Cause immediate `CONCURRENCY_CONFLICT` (409) errors because `expected_revision` changes asynchronously upon the first completed request.
3. Flood the backend and PostgreSQL with dozens of unwanted project versions.

### 8.2 Recommended Batching & Commit Architecture
The Studio already implements the correct two-phase pattern in [VidoAIStudio.tsx](file:///d:/HeyGen/video-ai-tools/src/components/studio/VidoAIStudio.tsx#L997-L1028):
- **Phase 1: Local Transient Update (`keydown`)**:
  Call `handleUpdateLayerTransform(layerId, { x: newX, y: newY })`.
  This updates local React state (`setScenes`) and marks `setSaveStatus("unsaved")` with zero network overhead. The UI updates at a crisp 60fps.
- **Phase 2: Debounced / KeyUp OCC Commit**:
  Use a debounced commit timer (e.g. 500ms debounce) or `keyup` handler to trigger `handleCommitLayerTransform()` (`await handleSave()`).
  If another arrow key is pressed within 500ms, the timer resets.
  When key activity stops, exactly **ONE** version is committed to the backend with the final coordinates and proper `expected_revision`.
- **Delete and Duplicate**:
  Because Delete and Duplicate are single-action operations (not continuous repeat gestures), they should commit immediately via `await handleSave(nextScenes)`.

---

## 9. Duplicate & Clipboard Architecture

### 9.1 Evaluation of Clipboard Approaches

| Approach | Feasibility | Pros | Cons | Recommendation |
| :--- | :--- | :--- | :--- | :--- |
| **1. Browser System Clipboard (`navigator.clipboard`)** | Low | Cross-tab / cross-window copy | Requires browser permission, async, fails on unfocused document, pollutes user OS text clipboard with JSON | Not recommended |
| **2. In-Memory Studio Ref / State** | High | Instantaneous, 100% reliable, no permissions, preserves rich object hierarchy | Only works within current tab session | **RECOMMENDED** |
| **3. Serialized LocalStorage** | Medium | Cross-tab persistence | Subject to storage quotas, potential stale asset references | Overkill for Phase 39 |

### 9.2 In-Memory Clipboard Specification
Maintain a ref in `VidoAIStudio.tsx`:
```typescript
const studioClipboardRef = useRef<{
  type: "layer";
  layer: any;
  layerKind: "media" | "text" | "element";
} | null>(null);
```

1. **Copy (`Ctrl/Cmd + C`)**:
   - Resolve `activeSelectedLayer`.
   - Deep clone the layer object into `studioClipboardRef.current`.
   - Show notification: `"Copied layer to clipboard"`.
2. **Paste (`Ctrl/Cmd + V`)**:
   - Inspect `studioClipboardRef.current`. If null, no-op.
   - Generate fresh unique ID: `${kind}_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`.
   - Apply slight offset: `x: Math.min(0.9, (layer.transform?.x ?? 0.5) + 0.05)`, `y: Math.min(0.9, (layer.transform?.y ?? 0.5) + 0.05)`.
   - Append to `activeScene.layers`.
   - Select newly pasted layer.
   - Commit version via `handleSave`.
3. **Duplicate (`Ctrl/Cmd + D`)**:
   - Equivalent to an atomic Copy + Paste in a single user action without altering the clipboard.

---

## 10. Browser Shortcut Conflicts & Native Integrity

Certain browser shortcuts must NEVER be intercepted:
- `Ctrl/Cmd + R` (Reload)
- `Ctrl/Cmd + W` (Close Tab)
- `Ctrl/Cmd + T` (New Tab)
- `Ctrl/Cmd + Shift + I` / `F12` (DevTools)
- `Ctrl/Cmd + F` (Find in Page)
- `Ctrl/Cmd + A` (Select All) — unless specifically scoped to a timeline/text editor
- `Ctrl/Cmd + Z` / `Ctrl/Cmd + Shift + Z` — Reserved for future Undo/Redo milestone; must not be intercepted in Phase 39.

Shortcuts that SHOULD call `e.preventDefault()` when studio canvas is active:
- `Space` (prevents page down-scroll)
- `ArrowUp` / `ArrowDown` / `ArrowLeft` / `ArrowRight` (prevents container scroll)
- `Ctrl/Cmd + D` (prevents browser "Bookmark this page" dialog)
- `Delete` / `Backspace` (prevents back-navigation in older browser engines)

---

## 11. Test Plan

### 11.1 Pure Logic Unit Tests (`src/lib/studioKeyboardShortcuts.test.ts`)
1. **Focus Guard Tests**:
   - Rejects shortcut when target is `<input>`, `<textarea>`, `<select>`, or `contenteditable`.
   - Allows shortcut when target is `<div>`, `<canvas>`, or `<button>`.
2. **Nudge Calculation Tests**:
   - Normal nudge steps (`0.005` normalized, clamped between `0.0` and `1.0`).
   - Shift nudge steps (`0.05` normalized, clamped between `0.0` and `1.0`).
   - Rejects nudge if `layer.locked === true`.
   - Rejects nudge if `layer.enabled === false`.
3. **Key Matching Tests**:
   - Matches Arrow keys, Delete, Backspace, Escape, Space.
   - Matches modifier combinations (`Ctrl+C`, `Cmd+C`, `Ctrl+V`, `Cmd+V`, `Ctrl+D`, `Cmd+D`).
4. **Duplicate / Clipboard Tests**:
   - Clones layer payload with new unique ID and offset.
   - Resets `locked` to `false` on duplicate.
   - Preserves content, styling, and metadata.

### 11.2 Studio Regression Suite
Verify full 94/94 passing Studio tests in backend:
- `test_studio_canvas_manipulation.py`
- `test_studio_captions.py`
- `test_studio_elements_shapes_stickers.py`
- `test_studio_interactive_timeline.py`
- `test_studio_locking_visibility.py`
- `test_studio_media_layers.py`
- `test_studio_music_media.py`
- `test_studio_pipeline_e2e.py`
- `test_studio_text.py`
- `test_studio_text_rotation_render.py`

### 11.3 Typecheck & Build
- `npx tsc --noEmit` &rarr; 0 errors.
- `npm run build` &rarr; 0 errors, 6/6 static pages compiled.

---

## 12. Architectural Risks & Edge Cases

1. **Focus Trapping on Window vs Canvas**:
   - *Risk*: A global `window.addEventListener("keydown")` might intercept keys when another modal or sub-app is mounted.
   - *Mitigation*: Attach the listener either to the studio container via `tabIndex={0}` or at the window level with a check ensuring the Studio component is active and no modal/dialog is open.
2. **High-Frequency Arrow Key Repeat**:
   - *Risk*: Flooding the backend with save requests.
   - *Mitigation*: Strictly separate transient React state updates on `keydown` from debounced OCC commits (500ms timer or `keyup`).
3. **Accidental Deletion of Locked Layers**:
   - *Risk*: User hits Backspace expecting to delete a text character, but deletes a locked background layer.
   - *Mitigation*: Strict focus guard (`isInputOrEditableTarget`) combined with strict lock check (`if (isLayerLocked(layer)) return;`).
4. **Platform Key Discrepancies (`Ctrl` vs `Meta`)**:
   - *Risk*: Mac users press `Cmd+C` while Windows users press `Ctrl+C`.
   - *Mitigation*: Check `(e.ctrlKey || e.metaKey)` universally for all command shortcuts.

---

## 13. Recommended Implementation Scope for Phase 39

1. **Step 1 — Create Pure Helper Library (`src/lib/studioKeyboardShortcuts.ts`)**:
   - Implement `isInputOrEditableTarget(target)`.
   - Implement `calculateKeyboardNudge(position, direction, isShift)`.
   - Implement `createLayerDuplicatePayload(layer, kind)`.
   - Implement `canDeleteLayerViaKeyboard(layer)`.
   - Implement `canNudgeLayerViaKeyboard(layer)`.
2. **Step 2 — Add Exhaustive Unit Tests (`src/lib/studioKeyboardShortcuts.test.ts`)**:
   - Test all keyboard combinations, focus guards, lock guards, and step calculations.
3. **Step 3 — Wire Keyboard Controller in `VidoAIStudio.tsx`**:
   - Set up `useEffect` with `handleKeyDown` and `handleKeyUp`.
   - Wire `ArrowLeft/Right/Up/Down` to `handleUpdateLayerTransform` with debounced OCC commit.
   - Wire `Delete` / `Backspace` to unified layer deletion.
   - Wire `Escape` to `clearVisualSelection()` and blur.
   - Wire `Space` to `togglePlayback()`.
   - Wire `Ctrl/Cmd + C`, `Ctrl/Cmd + V`, `Ctrl/Cmd + D` to in-memory clipboard and duplication.
4. **Step 4 — Verification**:
   - Run unit tests, full Studio regression (94 tests), TypeScript check, and production build.

---

## 14. Explicit Non-Goals

The following features are **explicitly out of scope** for Phase 39:
- Undo / Redo history stack.
- Multi-layer selection (box select, shift-click select).
- Cross-type layer reordering or z-index grouping.
- Snapping or alignment guides.
- Timeline clip splitting, ripple editing, or clip duplication on tracks.
- Scene transitions or animation keyframing.
- Database schema migrations or backend persistence redesign.
