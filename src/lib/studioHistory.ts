/**
 * Studio Client-side Undo/Redo History Engine (Phase 40)
 *
 * Implements pure, framework-independent snapshot history for Studio scenes and selections:
 * 1. Immutable state snapshots: captures full `scenes: StudioScene[]` and visual selection state.
 * 2. Linear history semantics: past / present / future stacks with branch truncation on new mutations.
 * 3. Configurable capacity: default 50 entries with FIFO eviction of oldest snapshots.
 * 4. Selection restoration & normalization: restores activeSceneIndex and visual layer selection IDs,
 *    safely falling back to null if a selected layer ID no longer exists in the restored scene.
 * 5. Deterministic deep cloning: utilizes native `structuredClone` (with JSON fallback) to isolate snapshots.
 */

import { StudioScene } from "@/components/studio/VidoAIStudio";

export interface HistorySelectionState {
  activeSceneIndex: number;
  selectedMediaLayerId: string | null;
  selectedTextLayerId: string | null;
  selectedElementLayerId: string | null;
  selectedLayerIds?: string[];
}

export interface AudioTrackItem {
  id: string;
  asset_id?: string | null;
  name: string;
  volume: number;
  start_time: number;
  duration?: number | null;
  loop: boolean;
  muted: boolean;
}

export interface StudioHistorySnapshot {
  scenes: StudioScene[];
  audio_tracks: AudioTrackItem[];
  activeSceneIndex: number;
  selection: HistorySelectionState;
  actionName?: string;
  timestamp: number;
}

export interface HistoryState {
  past: StudioHistorySnapshot[];
  present: StudioHistorySnapshot;
  future: StudioHistorySnapshot[];
  maxEntries: number;
}

export const DEFAULT_MAX_HISTORY_ENTRIES = 50;

/**
 * Safely deep-clones a value using structuredClone when available, falling back to JSON serialization.
 */
export function deepClone<T>(value: T): T {
  if (value === undefined || value === null) {
    return value;
  }
  if (typeof structuredClone === "function") {
    try {
      return structuredClone(value);
    } catch {
      // Fallback below if structuredClone fails on DOM nodes or unexpected non-cloneables
    }
  }
  return JSON.parse(JSON.stringify(value));
}

/**
 * Normalizes selection state against the target scenes array.
 * If a selected layer ID does not exist in the active scene's layers, it is cleared to null.
 * If activeSceneIndex is out of range, it is clamped to [0, scenes.length - 1].
 */
export function normalizeSelectionState(
  scenes: StudioScene[],
  selection: HistorySelectionState
): HistorySelectionState {
  if (!Array.isArray(scenes) || scenes.length === 0) {
    return {
      activeSceneIndex: 0,
      selectedMediaLayerId: null,
      selectedTextLayerId: null,
      selectedElementLayerId: null,
    };
  }

  const clampedIndex = Math.max(0, Math.min(selection.activeSceneIndex, scenes.length - 1));
  const activeScene = scenes[clampedIndex];
  const layerIds = new Set(
    Array.isArray(activeScene?.layers) ? activeScene.layers.map((l: any) => l.id) : []
  );

  const selectedLayerIds = Array.isArray(selection.selectedLayerIds)
    ? selection.selectedLayerIds.filter((id) => layerIds.has(id))
    : [];

  return {
    activeSceneIndex: clampedIndex,
    selectedMediaLayerId:
      selection.selectedMediaLayerId && layerIds.has(selection.selectedMediaLayerId)
        ? selection.selectedMediaLayerId
        : null,
    selectedTextLayerId:
      selection.selectedTextLayerId && layerIds.has(selection.selectedTextLayerId)
        ? selection.selectedTextLayerId
        : null,
    selectedElementLayerId:
      selection.selectedElementLayerId && layerIds.has(selection.selectedElementLayerId)
        ? selection.selectedElementLayerId
        : null,
    selectedLayerIds,
  };
}

/**
 * Creates a standalone snapshot object with cloned scenes, cloned audio tracks, and normalized selection.
 */
export function createSnapshot(
  scenes: StudioScene[],
  audioTracksOrSelection: AudioTrackItem[] | HistorySelectionState,
  selectionOrActionName?: HistorySelectionState | string,
  actionName = "Initial State"
): StudioHistorySnapshot {
  let audioTracks: AudioTrackItem[] = [];
  let selection: HistorySelectionState;
  let finalActionName = actionName;

  if (Array.isArray(audioTracksOrSelection)) {
    audioTracks = audioTracksOrSelection;
    selection = (selectionOrActionName as HistorySelectionState) || {
      activeSceneIndex: 0,
      selectedMediaLayerId: null,
      selectedTextLayerId: null,
      selectedElementLayerId: null,
    };
  } else {
    selection = audioTracksOrSelection;
    if (typeof selectionOrActionName === "string") {
      finalActionName = selectionOrActionName;
    }
  }

  const clonedScenes = deepClone(scenes);
  const clonedAudioTracks = deepClone(audioTracks);
  const normalizedSelection = normalizeSelectionState(clonedScenes, selection);

  return {
    scenes: clonedScenes,
    audio_tracks: clonedAudioTracks,
    activeSceneIndex: normalizedSelection.activeSceneIndex,
    selection: normalizedSelection,
    actionName: finalActionName,
    timestamp: Date.now(),
  };
}

/**
 * Initializes a new HistoryState using the initial loaded scenes, audio tracks, and selection as the baseline `present`.
 * Notice: Opening the Studio does NOT create an artificial undoable entry. Past starts empty.
 */
export function createHistory(
  initialScenes: StudioScene[],
  initialAudioOrSelection: AudioTrackItem[] | HistorySelectionState,
  initialSelectionOrMax?: HistorySelectionState | number,
  maxEntries: number = DEFAULT_MAX_HISTORY_ENTRIES
): HistoryState {
  let initialAudio: AudioTrackItem[] = [];
  let initialSelection: HistorySelectionState;
  let finalMax = maxEntries;

  if (Array.isArray(initialAudioOrSelection)) {
    initialAudio = initialAudioOrSelection;
    initialSelection = (initialSelectionOrMax as HistorySelectionState) || {
      activeSceneIndex: 0,
      selectedMediaLayerId: null,
      selectedTextLayerId: null,
      selectedElementLayerId: null,
    };
  } else {
    initialSelection = initialAudioOrSelection;
    if (typeof initialSelectionOrMax === "number") {
      finalMax = initialSelectionOrMax;
    }
  }

  const present = createSnapshot(initialScenes, initialAudio, initialSelection, "Initial Document");
  return {
    past: [],
    present,
    future: [],
    maxEntries: Math.max(1, finalMax),
  };
}

/**
 * Checks if an Undo operation is currently available.
 */
export function canUndo(state: HistoryState): boolean {
  return Array.isArray(state?.past) && state.past.length > 0;
}

/**
 * Checks if a Redo operation is currently available.
 */
export function canRedo(state: HistoryState): boolean {
  return Array.isArray(state?.future) && state.future.length > 0;
}

/**
 * Pushes a new mutation snapshot into the history stack:
 * - Current `present` moves into `past`.
 * - If `past` exceeds `maxEntries`, oldest entries are evicted (FIFO).
 * - New state becomes the new `present`.
 * - `future` is truncated (linear history branch truncation).
 */
export function pushHistory(
  state: HistoryState,
  newScenes: StudioScene[],
  newAudioOrSelection: AudioTrackItem[] | HistorySelectionState,
  newSelectionOrActionName?: HistorySelectionState | string,
  actionName = "Mutation"
): HistoryState {
  let newAudioTracks: AudioTrackItem[];
  let newSelection: HistorySelectionState;
  let finalActionName = actionName;

  if (Array.isArray(newAudioOrSelection)) {
    newAudioTracks = newAudioOrSelection;
    newSelection = (newSelectionOrActionName as HistorySelectionState) || {
      activeSceneIndex: 0,
      selectedMediaLayerId: null,
      selectedTextLayerId: null,
      selectedElementLayerId: null,
    };
  } else {
    newAudioTracks = state.present?.audio_tracks || [];
    newSelection = newAudioOrSelection;
    if (typeof newSelectionOrActionName === "string") {
      finalActionName = newSelectionOrActionName;
    }
  }

  const newSnapshot = createSnapshot(newScenes, newAudioTracks, newSelection, finalActionName);

  // Archive previous present into past
  const nextPast = [...state.past, state.present];

  // Enforce max capacity (FIFO eviction)
  if (nextPast.length > state.maxEntries) {
    nextPast.splice(0, nextPast.length - state.maxEntries);
  }

  return {
    past: nextPast,
    present: newSnapshot,
    future: [], // Branch truncation
    maxEntries: state.maxEntries,
  };
}

export interface HistoryRestoreResult {
  nextState: HistoryState;
  snapshot: StudioHistorySnapshot;
}

/**
 * Performs an Undo operation:
 * - Pops the most recent snapshot from `past`.
 * - Current `present` moves onto the top of `future`.
 * - The popped snapshot becomes the new `present` and is returned for restoration.
 * - Returns null if past is empty.
 */
export function undo(state: HistoryState): HistoryRestoreResult | null {
  if (!canUndo(state)) {
    return null;
  }

  const nextPast = [...state.past];
  const previousSnapshot = nextPast.pop()!;

  const nextFuture = [state.present, ...state.future];

  const nextState: HistoryState = {
    past: nextPast,
    present: previousSnapshot,
    future: nextFuture,
    maxEntries: state.maxEntries,
  };

  return {
    nextState,
    snapshot: deepClone(previousSnapshot),
  };
}

/**
 * Performs a Redo operation:
 * - Pops the next snapshot from the top of `future`.
 * - Current `present` moves to the top of `past`.
 * - The popped snapshot becomes the new `present` and is returned for restoration.
 * - Returns null if future is empty.
 */
export function redo(state: HistoryState): HistoryRestoreResult | null {
  if (!canRedo(state)) {
    return null;
  }

  const nextFuture = [...state.future];
  const nextSnapshot = nextFuture.shift()!;

  const nextPast = [...state.past, state.present];
  if (nextPast.length > state.maxEntries) {
    nextPast.splice(0, nextPast.length - state.maxEntries);
  }

  const nextState: HistoryState = {
    past: nextPast,
    present: nextSnapshot,
    future: nextFuture,
    maxEntries: state.maxEntries,
  };

  return {
    nextState,
    snapshot: deepClone(nextSnapshot),
  };
}

/**
 * Clears past and future history stacks while retaining current present state.
 */
export function clearHistory(state: HistoryState): HistoryState {
  return {
    past: [],
    present: deepClone(state.present),
    future: [],
    maxEntries: state.maxEntries,
  };
}
