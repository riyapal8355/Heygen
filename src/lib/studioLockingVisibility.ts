/**
 * Studio Layer Locking & Visibility Unification Helper
 *
 * Implements pure, framework-independent state helpers and guards for:
 * 1. Canonical visibility via `enabled` boolean property (default: true).
 * 2. Layer locking via `locked` boolean property (default: false).
 * 3. Canvas direct manipulation guards (move, resize, rotate).
 * 4. Timeline clip drag & trim guards.
 * 5. Inspector property mutation guards.
 */

export interface LockableLayer {
  id?: string;
  name?: string;
  enabled?: boolean;
  locked?: boolean;
  [key: string]: any;
}

/**
 * Returns whether a layer is currently locked.
 * Canonical default is false if missing or undefined.
 */
export function isLayerLocked(layer: LockableLayer | null | undefined): boolean {
  if (!layer) return false;
  return layer.locked === true;
}

/**
 * Returns whether a layer is currently visible / enabled.
 * Canonical default is true if missing or undefined.
 */
export function isLayerEnabled(layer: LockableLayer | null | undefined): boolean {
  if (!layer) return true;
  return layer.enabled !== false;
}

/**
 * Toggles a layer's canonical enabled state:
 * true -> false, false -> true, undefined -> false.
 */
export function toggleLayerEnabledState(layer: LockableLayer | null | undefined): boolean {
  return !isLayerEnabled(layer);
}

/**
 * Toggles a layer's locked state:
 * false -> true, true -> false, undefined -> true.
 */
export function toggleLayerLockedState(layer: LockableLayer | null | undefined): boolean {
  return !isLayerLocked(layer);
}

/**
 * Canvas Direct Manipulation Guard.
 * Blocks beginning any gesture (move, resize, rotate) if locked.
 *
 * @param locked Whether the layer is locked
 * @param onExecute Callback to execute if unlocked
 * @returns true if gesture started, false if blocked by lock
 */
export function guardCanvasGesture(
  locked: boolean | undefined,
  onExecute: () => void
): boolean {
  if (locked === true) {
    return false;
  }
  onExecute();
  return true;
}

/**
 * Inspector Transform & Timing Mutation Guard.
 * Blocks mutating any transform, timing, opacity, or content property if locked.
 *
 * @param layer The target layer object
 * @param mutation Callback performing the state change
 * @returns true if mutation executed, false if blocked by lock
 */
export function guardLayerMutation<T extends LockableLayer>(
  layer: T | null | undefined,
  mutation: () => void
): boolean {
  if (isLayerLocked(layer)) {
    return false;
  }
  mutation();
  return true;
}

/**
 * Timeline Clip Drag Guard.
 * When locked: preserves selection, blocks drag/trim initiation, blocks timing mutation.
 *
 * @param locked Whether the layer is locked
 * @param onSelect Callback to select the clip
 * @param startDrag Callback to initiate the drag session
 * @returns Object describing what action took place
 */
export function guardTimelineDrag(
  locked: boolean | undefined,
  onSelect: () => void,
  startDrag: () => void
): { dragAllowed: boolean; selected: boolean } {
  if (locked === true) {
    onSelect();
    return { dragAllowed: false, selected: true };
  }
  startDrag();
  return { dragAllowed: true, selected: false };
}
