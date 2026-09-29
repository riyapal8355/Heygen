/**
 * Studio Unified Cross-Type Layer Ordering Utilities (Phase 42B)
 *
 * Implements pure, framework-independent functions for:
 * 1. Sorting visual layers by canonical `z_index` (lower = behind, higher = in front).
 * 2. Normalizing `z_index` to consecutive 0..N-1 integers with legacy project compatibility.
 * 3. Bring Forward, Send Backward, Bring To Front, Send To Back.
 * 4. Arbitrary index movement (cross-type drag-and-drop).
 * 5. Deterministic placement for duplication and deletion.
 * 6. Phase 38 locking and visibility guards.
 */

export interface VisualLayer {
  id: string;
  type: string; // "image" | "video" | "media" | "text" | "shape" | "sticker" | "element"
  name?: string;
  z_index?: number;
  start_time?: number;
  end_time?: number;
  enabled?: boolean;
  locked?: boolean;
  transform?: {
    x?: number;
    y?: number;
    scale?: number;
    rotation?: number;
    [key: string]: any;
  };
  content?: Record<string, any>;
  [key: string]: any;
}

/**
 * Normalizes an array of visual layers so that every layer has a unique,
 * consecutive integer `z_index` from `0` to `layers.length - 1`.
 *
 * Ordering logic:
 * - If layers have defined `z_index` values, sort primarily by `z_index`.
 * - Ties or missing `z_index` fall back to the layer's original index in the array,
 *   preserving legacy document stability.
 */
export function normalizeLayerZIndices<T extends VisualLayer>(layers: T[]): T[] {
  if (!Array.isArray(layers) || layers.length === 0) return [];

  // Create indexed tuples to ensure stable sorting
  const indexed = layers.map((layer, originalIdx) => ({
    layer,
    originalIdx,
    currentZ: typeof layer.z_index === "number" && !isNaN(layer.z_index) ? layer.z_index : null,
  }));

  indexed.sort((a, b) => {
    if (a.currentZ !== null && b.currentZ !== null) {
      if (a.currentZ !== b.currentZ) {
        return a.currentZ - b.currentZ;
      }
      return a.originalIdx - b.originalIdx;
    }
    if (a.currentZ !== null) return -1;
    if (b.currentZ !== null) return 1;
    return a.originalIdx - b.originalIdx;
  });

  return indexed.map((item, newZ) => ({
    ...item.layer,
    z_index: newZ,
  }));
}

/**
 * Returns visual layers sorted in ascending order of `z_index`
 * (index 0 = backmost/rendered first, index N-1 = frontmost/rendered on top).
 */
export function getOrderedVisualLayers<T extends VisualLayer>(layers: T[]): T[] {
  if (!Array.isArray(layers) || layers.length === 0) return [];
  return normalizeLayerZIndices(layers);
}

/**
 * Bring Forward: Moves the target layer exactly 1 position toward the front.
 * Swaps with the layer at index + 1 in the ordered stack.
 * If target layer is locked or already frontmost, returns layers normalized without movement.
 */
export function bringLayerForward<T extends VisualLayer>(layers: T[], targetLayerId: string): T[] {
  const ordered = getOrderedVisualLayers(layers);
  const idx = ordered.findIndex((l) => l.id === targetLayerId);
  if (idx === -1) return ordered;

  const target = ordered[idx];
  if (target.locked === true) return ordered; // Phase 38 locking protection
  if (idx === ordered.length - 1) return ordered; // Already frontmost

  // Swap with next layer
  const next = [...ordered];
  const temp = next[idx];
  next[idx] = next[idx + 1];
  next[idx + 1] = temp;

  return next.map((l, i) => ({ ...l, z_index: i }));
}

/**
 * Send Backward: Moves the target layer exactly 1 position toward the back.
 * Swaps with the layer at index - 1 in the ordered stack.
 * If target layer is locked or already backmost, returns layers normalized without movement.
 */
export function sendLayerBackward<T extends VisualLayer>(layers: T[], targetLayerId: string): T[] {
  const ordered = getOrderedVisualLayers(layers);
  const idx = ordered.findIndex((l) => l.id === targetLayerId);
  if (idx === -1) return ordered;

  const target = ordered[idx];
  if (target.locked === true) return ordered; // Phase 38 locking protection
  if (idx === 0) return ordered; // Already backmost

  // Swap with previous layer
  const next = [...ordered];
  const temp = next[idx];
  next[idx] = next[idx - 1];
  next[idx - 1] = temp;

  return next.map((l, i) => ({ ...l, z_index: i }));
}

/**
 * Bring To Front: Moves the target layer to the topmost position (index N - 1).
 * If target layer is locked or already frontmost, returns layers normalized without movement.
 */
export function bringLayerToFront<T extends VisualLayer>(layers: T[], targetLayerId: string): T[] {
  const ordered = getOrderedVisualLayers(layers);
  const idx = ordered.findIndex((l) => l.id === targetLayerId);
  if (idx === -1) return ordered;

  const target = ordered[idx];
  if (target.locked === true) return ordered;
  if (idx === ordered.length - 1) return ordered;

  const next = [...ordered];
  const [removed] = next.splice(idx, 1);
  next.push(removed);

  return next.map((l, i) => ({ ...l, z_index: i }));
}

/**
 * Send To Back: Moves the target layer to the bottommost position (index 0).
 * If target layer is locked or already backmost, returns layers normalized without movement.
 */
export function sendLayerToBack<T extends VisualLayer>(layers: T[], targetLayerId: string): T[] {
  const ordered = getOrderedVisualLayers(layers);
  const idx = ordered.findIndex((l) => l.id === targetLayerId);
  if (idx === -1) return ordered;

  const target = ordered[idx];
  if (target.locked === true) return ordered;
  if (idx === 0) return ordered;

  const next = [...ordered];
  const [removed] = next.splice(idx, 1);
  next.unshift(removed);

  return next.map((l, i) => ({ ...l, z_index: i }));
}

/**
 * Arbitrary Drag-and-Drop Reorder: Moves the target layer to `toIndex`.
 * Clamps `toIndex` within `[0, ordered.length - 1]`.
 */
export function moveLayerToIndex<T extends VisualLayer>(
  layers: T[],
  targetLayerId: string,
  toIndex: number
): T[] {
  const ordered = getOrderedVisualLayers(layers);
  const fromIdx = ordered.findIndex((l) => l.id === targetLayerId);
  if (fromIdx === -1) return ordered;

  const target = ordered[fromIdx];
  if (target.locked === true) return ordered;

  const clampedTargetIdx = Math.max(0, Math.min(toIndex, ordered.length - 1));
  if (fromIdx === clampedTargetIdx) return ordered;

  const next = [...ordered];
  const [removed] = next.splice(fromIdx, 1);
  next.splice(clampedTargetIdx, 0, removed);

  return next.map((l, i) => ({ ...l, z_index: i }));
}

/**
 * Duplication Placement:
 * Places a cloned layer immediately above its source layer in the stack (`sourceIdx + 1`).
 */
export function duplicateLayerWithZIndex<T extends VisualLayer>(
  layers: T[],
  sourceLayerId: string,
  clonedLayer: T
): T[] {
  const ordered = getOrderedVisualLayers(layers);
  const sourceIdx = ordered.findIndex((l) => l.id === sourceLayerId);

  const next = [...ordered];
  if (sourceIdx === -1) {
    next.push(clonedLayer);
  } else {
    next.splice(sourceIdx + 1, 0, clonedLayer);
  }

  return next.map((l, i) => ({ ...l, z_index: i }));
}

/**
 * Deletion Placement:
 * Removes target layer and re-normalizes remaining layers to consecutive 0..N-1.
 */
export function deleteLayerWithZIndex<T extends VisualLayer>(
  layers: T[],
  targetLayerId: string
): T[] {
  const filtered = layers.filter((l) => l.id !== targetLayerId);
  return normalizeLayerZIndices(filtered);
}

/**
 * Derives a unified, ordered visual layer collection from typed layer arrays.
 * Handles legacy projects where `z_index` might not yet be set by applying
 * a deterministic legacy tier baseline (media: 0..M-1, text: M..M+T-1, elements: M+T..M+T+E-1)
 * only if none of the layers have explicit `z_index`.
 */
export function deriveUnifiedVisualLayers<T extends VisualLayer>(
  mediaLayers: T[],
  textLayers: T[],
  elementLayers: T[]
): T[] {
  const m = Array.isArray(mediaLayers) ? mediaLayers : [];
  const t = Array.isArray(textLayers) ? textLayers : [];
  const e = Array.isArray(elementLayers) ? elementLayers : [];

  const combined = [...m, ...t, ...e];
  const hasAnyZIndex = combined.some(
    (l) => typeof l.z_index === "number" && !isNaN(l.z_index)
  );

  if (hasAnyZIndex) {
    return normalizeLayerZIndices(combined);
  }

  // Legacy tier normalization: media -> text -> elements
  let counter = 0;
  const legacyOrdered: T[] = [];
  m.forEach((l) => legacyOrdered.push({ ...l, z_index: counter++ }));
  t.forEach((l) => legacyOrdered.push({ ...l, z_index: counter++ }));
  e.forEach((l) => legacyOrdered.push({ ...l, z_index: counter++ }));

  return legacyOrdered;
}

/**
 * Splits a unified visual collection back into typed arrays while preserving each layer's z_index.
 */
export function distributeUnifiedVisualLayers<T extends VisualLayer>(unifiedLayers: T[]): {
  mediaLayers: T[];
  textLayers: T[];
  elementLayers: T[];
} {
  const mediaLayers: T[] = [];
  const textLayers: T[] = [];
  const elementLayers: T[] = [];

  (unifiedLayers || []).forEach((l) => {
    if (l.type === "image" || l.type === "video" || l.type === "media") {
      mediaLayers.push(l);
    } else if (l.type === "text") {
      textLayers.push(l);
    } else {
      elementLayers.push(l);
    }
  });

  return { mediaLayers, textLayers, elementLayers };
}
