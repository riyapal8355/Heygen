/**
 * Studio Multi-Layer Selection & Group Editing Engine (Phase 44)
 *
 * Implements pure, framework-independent utilities for:
 * 1. Centralized Multi-Layer Selection Model ({ sceneId, layerType, layerId }).
 * 2. Additive, Range, and Toggle Selection operations.
 * 3. Canvas Group Bounding Box & Marquee Intersection calculations.
 * 4. Group Movement with relative offset preservation & Phase 42A magnetic group snapping.
 * 5. Group Alignment (left, center, right, top, middle, bottom) & Distribution.
 * 6. Group Operations: Duplication (unique IDs & z-order), Deletion, Lock, Visibility.
 * 7. Group Z-Ordering maintaining relative order through the unified stacking sequence.
 * 8. Timeline Multi-Clip Movement preserving relative timing gaps & leading-edge snapping.
 */

import { VisualLayer, normalizeLayerZIndices, getOrderedVisualLayers } from "./studioLayerOrdering";
import {
  BoundingBox2D,
  Point2D,
  SnapTargetLayer,
  AlignmentGuide,
  calculateCanvasSnap,
  DEFAULT_SNAP_THRESHOLD,
} from "./studioCanvasSnapping";
import { calculateMoveTiming, SNAP_THRESHOLD_SECONDS, MIN_CLIP_DURATION } from "./timelineUtils";

export interface SelectedLayerIdentity {
  sceneId: string;
  layerType: string; // "media" | "text" | "element" | "shape" | "sticker" | "audio"
  layerId: string;
}

export interface GroupBoundingBox {
  minX: number;
  maxX: number;
  minY: number;
  maxY: number;
  centerX: number;
  centerY: number;
  width: number;
  height: number;
}

export type AlignmentType =
  | "left"
  | "center"
  | "right"
  | "top"
  | "middle"
  | "bottom";

export type DistributionAxis = "horizontal" | "vertical";

// ============================================================================
// 1. SELECTION STATE MANAGEMENT
// ============================================================================

export function createSelectionKey(sceneId: string, layerId: string): string {
  return `${sceneId}::${layerId}`;
}

export function isLayerSelected(
  selection: SelectedLayerIdentity[],
  sceneId: string,
  layerId: string
): boolean {
  return selection.some((item) => item.sceneId === sceneId && item.layerId === layerId);
}

export function selectSingleLayer(
  item: SelectedLayerIdentity
): SelectedLayerIdentity[] {
  return [item];
}

export function toggleLayerSelection(
  selection: SelectedLayerIdentity[],
  item: SelectedLayerIdentity
): SelectedLayerIdentity[] {
  const index = selection.findIndex(
    (s) => s.sceneId === item.sceneId && s.layerId === item.layerId
  );
  if (index >= 0) {
    return selection.filter((_, i) => i !== index);
  }
  return [...selection, item];
}

export function addLayersToSelection(
  selection: SelectedLayerIdentity[],
  items: SelectedLayerIdentity[]
): SelectedLayerIdentity[] {
  const existingKeys = new Set(selection.map((s) => createSelectionKey(s.sceneId, s.layerId)));
  const next = [...selection];
  for (const item of items) {
    const key = createSelectionKey(item.sceneId, item.layerId);
    if (!existingKeys.has(key)) {
      existingKeys.add(key);
      next.push(item);
    }
  }
  return next;
}

export function removeLayersFromSelection(
  selection: SelectedLayerIdentity[],
  layerIds: string[]
): SelectedLayerIdentity[] {
  const toRemove = new Set(layerIds);
  return selection.filter((s) => !toRemove.has(s.layerId));
}

export function getSelectedLayerIdsForScene(
  selection: SelectedLayerIdentity[],
  sceneId: string
): string[] {
  return selection.filter((s) => s.sceneId === sceneId).map((s) => s.layerId);
}

// ============================================================================
// 2. CANVAS MULTI-SELECTION BOUNDS & GEOMETRY
// ============================================================================

/**
 * Calculates normalized bounding box for an individual visual layer.
 */
export function getLayerBounds(layer: VisualLayer): BoundingBox2D {
  const t = layer.transform || {};
  const c = layer.content || {};
  const cx = t.x ?? 0.5;
  const cy = t.y ?? 0.5;
  const scale = t.scale ?? 1.0;

  let width = 0.25;
  let height = 0.15;

  if (layer.type === "image" || layer.type === "video" || layer.type === "media") {
    width = 0.40 * scale;
    height = 0.225 * scale;
  } else if (layer.type === "text") {
    const textLen = (c.text || layer.name || "Text").length;
    width = Math.max(0.12, Math.min(0.85, (textLen * 0.025 + 0.05) * scale));
    height = 0.08 * scale;
  } else if (layer.type === "shape" || layer.type === "element" || layer.type === "sticker") {
    width = (c.width ?? 0.35) * scale;
    height = (c.height ?? 0.2) * scale;
  }

  return {
    x: cx,
    y: cy,
    width: Math.max(0.02, width),
    height: Math.max(0.02, height),
  };
}

/**
 * Computes the composite bounding box enclosing all selected layers.
 */
export function calculateGroupBounds(layers: VisualLayer[]): GroupBoundingBox | null {
  if (!Array.isArray(layers) || layers.length === 0) return null;

  let minX = Infinity;
  let maxX = -Infinity;
  let minY = Infinity;
  let maxY = -Infinity;

  for (const layer of layers) {
    const b = getLayerBounds(layer);
    const halfW = b.width / 2;
    const halfH = b.height / 2;
    const l = b.x - halfW;
    const r = b.x + halfW;
    const t = b.y - halfH;
    const bt = b.y + halfH;

    if (l < minX) minX = l;
    if (r > maxX) maxX = r;
    if (t < minY) minY = t;
    if (bt > maxY) maxY = bt;
  }

  if (!Number.isFinite(minX) || !Number.isFinite(maxX)) return null;

  const width = Math.max(0.01, maxX - minX);
  const height = Math.max(0.01, maxY - minY);
  const centerX = minX + width / 2;
  const centerY = minY + height / 2;

  return {
    minX: Math.round(minX * 1000) / 1000,
    maxX: Math.round(maxX * 1000) / 1000,
    minY: Math.round(minY * 1000) / 1000,
    maxY: Math.round(maxY * 1000) / 1000,
    centerX: Math.round(centerX * 1000) / 1000,
    centerY: Math.round(centerY * 1000) / 1000,
    width: Math.round(width * 1000) / 1000,
    height: Math.round(height * 1000) / 1000,
  };
}

/**
 * Detects which layers intersect with a rectangular marquee drag area.
 */
export function getLayersIntersectingMarquee(
  layers: VisualLayer[],
  marquee: { minX: number; maxX: number; minY: number; maxY: number }
): string[] {
  const normMinX = Math.min(marquee.minX, marquee.maxX);
  const normMaxX = Math.max(marquee.minX, marquee.maxX);
  const normMinY = Math.min(marquee.minY, marquee.maxY);
  const normMaxY = Math.max(marquee.minY, marquee.maxY);

  const intersectingIds: string[] = [];

  for (const layer of layers) {
    if (layer.enabled === false) continue; // Exclude hidden layers from marquee
    const b = getLayerBounds(layer);
    const halfW = b.width / 2;
    const halfH = b.height / 2;
    const layerLeft = b.x - halfW;
    const layerRight = b.x + halfW;
    const layerTop = b.y - halfH;
    const layerBottom = b.y + halfH;

    // Check AABB intersection
    const overlaps =
      layerLeft <= normMaxX &&
      layerRight >= normMinX &&
      layerTop <= normMaxY &&
      layerBottom >= normMinY;

    if (overlaps) {
      intersectingIds.push(layer.id);
    }
  }

  return intersectingIds;
}

// ============================================================================
// 3. GROUP MOVEMENT & SNAPPING
// ============================================================================

export interface GroupMoveResult {
  transformMap: Map<string, { x: number; y: number }>;
  activeGuides: AlignmentGuide[];
}

/**
 * Calculates coordinated movement for multiple layers preserving relative offsets.
 * Enforces locking protection (locked layers do not move).
 * Magnetically snaps the group as a single unified bounding box using Phase 42A snapping.
 */
export function calculateGroupMove(
  selectedLayers: VisualLayer[],
  deltaX: number,
  deltaY: number,
  allSceneLayers: VisualLayer[] = [],
  snapEnabled: boolean = true,
  snapThreshold: number = DEFAULT_SNAP_THRESHOLD
): GroupMoveResult {
  const transformMap = new Map<string, { x: number; y: number }>();
  let activeGuides: AlignmentGuide[] = [];

  const unlockedLayers = selectedLayers.filter((l) => l.locked !== true);
  if (unlockedLayers.length === 0) {
    return { transformMap, activeGuides };
  }

  let finalDeltaX = deltaX;
  let finalDeltaY = deltaY;

  if (snapEnabled) {
    const groupBounds = calculateGroupBounds(unlockedLayers);
    if (groupBounds) {
      const selectedIdSet = new Set(selectedLayers.map((l) => l.id));
      const neighborSnapTargets: SnapTargetLayer[] = allSceneLayers
        .filter((l) => !selectedIdSet.has(l.id) && l.enabled !== false)
        .map((l) => ({
          id: l.id,
          name: l.name,
          enabled: l.enabled,
          locked: l.locked,
          bounds: getLayerBounds(l),
        }));

      const proposedCenter: Point2D = {
        x: groupBounds.centerX + deltaX,
        y: groupBounds.centerY + deltaY,
      };

      const snapRes = calculateCanvasSnap(
        proposedCenter,
        { width: groupBounds.width, height: groupBounds.height },
        neighborSnapTargets,
        snapThreshold
      );

      finalDeltaX = snapRes.x - groupBounds.centerX;
      finalDeltaY = snapRes.y - groupBounds.centerY;
      activeGuides = snapRes.guides;
    }
  }

  for (const layer of selectedLayers) {
    const curX = layer.transform?.x ?? 0.5;
    const curY = layer.transform?.y ?? 0.5;

    if (layer.locked === true) {
      // Locked layer stays anchored
      transformMap.set(layer.id, { x: curX, y: curY });
    } else {
      transformMap.set(layer.id, {
        x: Math.round((curX + finalDeltaX) * 1000) / 1000,
        y: Math.round((curY + finalDeltaY) * 1000) / 1000,
      });
    }
  }

  return { transformMap, activeGuides };
}

// ============================================================================
// 4. GROUP ALIGNMENT & DISTRIBUTION
// ============================================================================

/**
 * Aligns selected unlocked layers along group bounding box edges or centers.
 * Requires at least 2 layers.
 */
export function calculateGroupAlignment(
  layers: VisualLayer[],
  alignment: AlignmentType
): Map<string, { x?: number; y?: number }> {
  const result = new Map<string, { x?: number; y?: number }>();
  const unlocked = layers.filter((l) => l.locked !== true);
  if (unlocked.length < 2) return result;

  const group = calculateGroupBounds(unlocked);
  if (!group) return result;

  for (const layer of unlocked) {
    const b = getLayerBounds(layer);
    const halfW = b.width / 2;
    const halfH = b.height / 2;

    switch (alignment) {
      case "left":
        result.set(layer.id, { x: Math.round((group.minX + halfW) * 1000) / 1000 });
        break;
      case "center":
        result.set(layer.id, { x: Math.round(group.centerX * 1000) / 1000 });
        break;
      case "right":
        result.set(layer.id, { x: Math.round((group.maxX - halfW) * 1000) / 1000 });
        break;
      case "top":
        result.set(layer.id, { y: Math.round((group.minY + halfH) * 1000) / 1000 });
        break;
      case "middle":
        result.set(layer.id, { y: Math.round(group.centerY * 1000) / 1000 });
        break;
      case "bottom":
        result.set(layer.id, { y: Math.round((group.maxY - halfH) * 1000) / 1000 });
        break;
    }
  }

  return result;
}

/**
 * Distributes selected unlocked layers evenly along an axis.
 * Requires at least 3 layers.
 */
export function calculateGroupDistribution(
  layers: VisualLayer[],
  axis: DistributionAxis
): Map<string, { x?: number; y?: number }> {
  const result = new Map<string, { x?: number; y?: number }>();
  const unlocked = layers.filter((l) => l.locked !== true);
  if (unlocked.length < 3) return result;

  if (axis === "horizontal") {
    const sorted = [...unlocked].sort(
      (a, b) => (a.transform?.x ?? 0.5) - (b.transform?.x ?? 0.5)
    );
    const minCenter = sorted[0].transform?.x ?? 0.5;
    const maxCenter = sorted[sorted.length - 1].transform?.x ?? 0.5;
    const totalSpan = maxCenter - minCenter;
    const step = totalSpan / (sorted.length - 1);

    sorted.forEach((l, idx) => {
      result.set(l.id, { x: Math.round((minCenter + idx * step) * 1000) / 1000 });
    });
  } else {
    const sorted = [...unlocked].sort(
      (a, b) => (a.transform?.y ?? 0.5) - (b.transform?.y ?? 0.5)
    );
    const minCenter = sorted[0].transform?.y ?? 0.5;
    const maxCenter = sorted[sorted.length - 1].transform?.y ?? 0.5;
    const totalSpan = maxCenter - minCenter;
    const step = totalSpan / (sorted.length - 1);

    sorted.forEach((l, idx) => {
      result.set(l.id, { y: Math.round((minCenter + idx * step) * 1000) / 1000 });
    });
  }

  return result;
}

// ============================================================================
// 5. GROUP OPERATIONS (DUPLICATE, DELETE, LOCK, VISIBILITY, Z-ORDER)
// ============================================================================

/**
 * Duplicates all selected unlocked layers as a single atomic operation.
 * Assigns unique IDs, offsets positions slightly (+0.03, +0.03), and assigns
 * consecutive z-index values directly above the source layers.
 */
export function groupDuplicateLayers(
  layers: VisualLayer[],
  selectedIds: string[]
): { nextLayers: VisualLayer[]; newIds: string[] } {
  const selectedSet = new Set(selectedIds);
  const eligible = layers.filter((l) => selectedSet.has(l.id) && l.locked !== true);
  if (eligible.length === 0) {
    return { nextLayers: layers, newIds: [] };
  }

  const newIds: string[] = [];
  const clonedMap = new Map<string, VisualLayer>();

  for (const source of eligible) {
    const newId = `${source.type || "layer"}_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`;
    newIds.push(newId);

    const cloned: VisualLayer = JSON.parse(JSON.stringify(source));
    cloned.id = newId;
    if (cloned.name) cloned.name = `${cloned.name} (Copy)`;
    if (cloned.transform) {
      cloned.transform.x = Math.round(Math.min(0.95, (cloned.transform.x ?? 0.5) + 0.03) * 1000) / 1000;
      cloned.transform.y = Math.round(Math.min(0.95, (cloned.transform.y ?? 0.5) + 0.03) * 1000) / 1000;
    }
    clonedMap.set(source.id, cloned);
  }

  // Interleave cloned layers immediately above their sources
  const next: VisualLayer[] = [];
  for (const l of layers) {
    next.push(l);
    if (clonedMap.has(l.id)) {
      next.push(clonedMap.get(l.id)!);
    }
  }

  return {
    nextLayers: normalizeLayerZIndices(next),
    newIds,
  };
}

/**
 * Deletes all selected unlocked layers in a single atomic mutation.
 * Normalizes remaining z-indices using Phase 42B rules.
 */
export function groupDeleteLayers(
  layers: VisualLayer[],
  selectedIds: string[]
): VisualLayer[] {
  const toDelete = new Set(selectedIds);
  const remaining = layers.filter((l) => !toDelete.has(l.id) || l.locked === true);
  return normalizeLayerZIndices(remaining);
}

/**
 * Sets locked state for all selected layers.
 */
export function groupSetLock(
  layers: VisualLayer[],
  selectedIds: string[],
  locked: boolean
): VisualLayer[] {
  const targetSet = new Set(selectedIds);
  return layers.map((l) => (targetSet.has(l.id) ? { ...l, locked } : l));
}

/**
 * Sets visibility (enabled) state for all selected layers.
 */
export function groupSetVisibility(
  layers: VisualLayer[],
  selectedIds: string[],
  enabled: boolean
): VisualLayer[] {
  const targetSet = new Set(selectedIds);
  return layers.map((l) => (targetSet.has(l.id) ? { ...l, enabled } : l));
}

/**
 * Coordinated Z-ordering for multiple selected layers.
 * Preserves their relative internal order while shifting the block.
 */
export function groupMoveZOrder(
  layers: VisualLayer[],
  selectedIds: string[],
  direction: "forward" | "backward" | "front" | "back"
): VisualLayer[] {
  const ordered = getOrderedVisualLayers(layers);
  const selectedSet = new Set(selectedIds);
  const hasLocked = ordered.some((l) => selectedSet.has(l.id) && l.locked === true);
  if (hasLocked) return ordered; // Do not move if selection contains locked layers

  const selectedItems = ordered.filter((l) => selectedSet.has(l.id));
  const unselectedItems = ordered.filter((l) => !selectedSet.has(l.id));
  if (selectedItems.length === 0 || unselectedItems.length === 0) return ordered;

  let next: VisualLayer[] = [];

  if (direction === "front") {
    next = [...unselectedItems, ...selectedItems];
  } else if (direction === "back") {
    next = [...selectedItems, ...unselectedItems];
  } else if (direction === "forward") {
    // Shift each selected layer 1 position forward past unselected layers if possible
    next = [...ordered];
    for (let i = next.length - 2; i >= 0; i--) {
      if (selectedSet.has(next[i].id) && !selectedSet.has(next[i + 1].id)) {
        const temp = next[i];
        next[i] = next[i + 1];
        next[i + 1] = temp;
      }
    }
  } else if (direction === "backward") {
    // Shift each selected layer 1 position backward past unselected layers if possible
    next = [...ordered];
    for (let i = 1; i < next.length; i++) {
      if (selectedSet.has(next[i].id) && !selectedSet.has(next[i - 1].id)) {
        const temp = next[i];
        next[i] = next[i - 1];
        next[i - 1] = temp;
      }
    }
  }

  return next.map((l, i) => ({ ...l, z_index: i }));
}

// ============================================================================
// 6. TIMELINE MULTI-CLIP MOVEMENT & SNAPPING
// ============================================================================

export interface TimelineClipItem {
  id: string | number;
  start_time: number;
  end_time: number;
  locked?: boolean;
  enabled?: boolean;
}

export interface GroupTimelineMoveResult {
  timingMap: Map<string | number, { start_time: number; end_time: number }>;
  snappedTarget: number | null;
}

/**
 * Calculates group movement for multiple timeline clips.
 * Preserves relative timing gaps between clips.
 * Snaps using the leading edge or boundaries as a unit.
 */
export function calculateGroupTimelineMove(
  allClips: TimelineClipItem[],
  selectedClipIds: Array<string | number>,
  deltaSeconds: number,
  maxDuration: number,
  snapTargets: number[] = [],
  snapThreshold: number = SNAP_THRESHOLD_SECONDS
): GroupTimelineMoveResult {
  const timingMap = new Map<string | number, { start_time: number; end_time: number }>();
  const selectedSet = new Set(selectedClipIds.map(String));

  const targetClips = allClips.filter(
    (c) => selectedSet.has(String(c.id)) && c.locked !== true
  );

  if (targetClips.length === 0) {
    return { timingMap, snappedTarget: null };
  }

  // Find min start and max end of selected group
  let groupMinStart = Infinity;
  let groupMaxEnd = -Infinity;
  for (const c of targetClips) {
    if (c.start_time < groupMinStart) groupMinStart = c.start_time;
    if (c.end_time > groupMaxEnd) groupMaxEnd = c.end_time;
  }

  // Calculate move and snapping using group bounding boundaries
  const groupDuration = groupMaxEnd - groupMinStart;
  const moveRes = calculateMoveTiming(
    groupMinStart,
    groupMaxEnd,
    deltaSeconds,
    maxDuration,
    snapTargets,
    snapThreshold
  );

  const effectiveDelta = moveRes.start_time - groupMinStart;

  for (const clip of targetClips) {
    const newStart = Math.max(0, Math.min(maxDuration - MIN_CLIP_DURATION, clip.start_time + effectiveDelta));
    const duration = clip.end_time - clip.start_time;
    const newEnd = Math.min(maxDuration, newStart + duration);

    timingMap.set(clip.id, {
      start_time: Math.round(newStart * 1000) / 1000,
      end_time: Math.round(newEnd * 1000) / 1000,
    });
  }

  return {
    timingMap,
    snappedTarget: moveRes.snappedTarget ?? null,
  };
}

// ============================================================================
// 7. MULTI-SELECTION INSPECTOR & BATCH MUTATIONS (PHASE 45)
// ============================================================================

export interface MultiSelectionSummary {
  count: number;
  typeCounts: Record<string, number>;
  typeSummary: string; // e.g. "2 Text, 1 Shape"
  allLocked: boolean;
  anyLocked: boolean;
  unlockedCount: number;
  opacityState: {
    isMixed: boolean;
    value: number | null; // null if mixed or empty
  };
  visibilityState: {
    isMixed: boolean;
    allVisible: boolean;
    visibleCount: number;
  };
  lockState: {
    isMixed: boolean;
    allLocked: boolean;
    lockedCount: number;
  };
  transformState: {
    isScaleMixed: boolean;
    isRotationMixed: boolean;
  };
  eligibleTypes: string[];
}

export interface TransformBatchDelta {
  dx?: number;
  dy?: number;
  scaleMult?: number;
  dRotation?: number;
}

/**
 * Computes multi-selection summary and mixed-value states across selected layers.
 */
export function getMultiSelectionSummary(
  layers: VisualLayer[],
  selectedIds: string[]
): MultiSelectionSummary {
  const selectedSet = new Set(selectedIds);
  const selected = layers.filter((l) => selectedSet.has(l.id));
  const count = selected.length;

  const typeCounts: Record<string, number> = {};
  const eligibleTypes: string[] = [];
  let lockedCount = 0;
  let visibleCount = 0;

  for (const l of selected) {
    const rawType = l.type || "layer";
    const typeLabel =
      rawType === "image" || rawType === "media"
        ? "Image"
        : rawType === "video"
        ? "Video"
        : rawType === "text"
        ? "Text"
        : rawType === "shape"
        ? "Shape"
        : rawType === "sticker"
        ? "Sticker"
        : "Layer";

    typeCounts[typeLabel] = (typeCounts[typeLabel] || 0) + 1;
    if (!eligibleTypes.includes(rawType)) {
      eligibleTypes.push(rawType);
    }
    if (l.locked === true) lockedCount++;
    if (l.enabled !== false) visibleCount++;
  }

  const typeSummary = Object.entries(typeCounts)
    .map(([type, c]) => `${c} ${type}`)
    .join(", ") || `${count} Layers`;

  const allLocked = count > 0 && lockedCount === count;
  const anyLocked = lockedCount > 0;
  const unlockedCount = count - lockedCount;

  // Opacity mixed detection
  const opacities = selected.map((l) =>
    typeof l.content?.opacity === "number" ? Math.round(l.content.opacity * 100) / 100 : 1.0
  );
  let isOpacityMixed = false;
  let uniformOpacity: number | null = null;
  if (opacities.length > 0) {
    const firstOp = opacities[0];
    const allSame = opacities.every((op) => Math.abs(op - firstOp) < 0.005);
    if (allSame) {
      uniformOpacity = firstOp;
      isOpacityMixed = false;
    } else {
      isOpacityMixed = true;
      uniformOpacity = null;
    }
  }

  // Scale mixed detection
  const scales = selected.map((l) =>
    typeof l.transform?.scale === "number" ? Math.round(l.transform.scale * 100) / 100 : 1.0
  );
  const isScaleMixed = scales.length > 1 && !scales.every((s) => Math.abs(s - scales[0]) < 0.01);

  // Rotation mixed detection
  const rotations = selected.map((l) =>
    typeof l.transform?.rotation === "number" ? Math.round(l.transform.rotation) : 0
  );
  const isRotationMixed = rotations.length > 1 && !rotations.every((r) => r === rotations[0]);

  return {
    count,
    typeCounts,
    typeSummary,
    allLocked,
    anyLocked,
    unlockedCount,
    opacityState: {
      isMixed: isOpacityMixed,
      value: uniformOpacity,
    },
    visibilityState: {
      isMixed: count > 0 && visibleCount > 0 && visibleCount < count,
      allVisible: count > 0 && visibleCount === count,
      visibleCount,
    },
    lockState: {
      isMixed: count > 0 && lockedCount > 0 && lockedCount < count,
      allLocked,
      lockedCount,
    },
    transformState: {
      isScaleMixed,
      isRotationMixed,
    },
    eligibleTypes,
  };
}

/**
 * Safely updates opacity on all selected unlocked layers in a single batch mutation.
 * Clamps opacity between 0 and 1. Skips locked layers.
 */
export function batchSetOpacity(
  layers: VisualLayer[],
  selectedIds: string[],
  opacity: number
): VisualLayer[] {
  const targetSet = new Set(selectedIds);
  const clamped = Math.max(0, Math.min(1, Math.round(opacity * 100) / 100));

  return layers.map((l) => {
    if (!targetSet.has(l.id)) return l;
    if (l.locked === true) return l; // Locked layers cannot have opacity changed

    return {
      ...l,
      content: {
        ...(l.content || {}),
        opacity: clamped,
      },
    };
  });
}

/**
 * Batch updates visibility on selected layers.
 * Visibility remains independent of locking.
 */
export function batchSetVisibility(
  layers: VisualLayer[],
  selectedIds: string[],
  enabled: boolean
): VisualLayer[] {
  return groupSetVisibility(layers, selectedIds, enabled);
}

/**
 * Batch updates locked state on selected layers.
 */
export function batchSetLock(
  layers: VisualLayer[],
  selectedIds: string[],
  locked: boolean
): VisualLayer[] {
  return groupSetLock(layers, selectedIds, locked);
}

/**
 * Applies relative transform deltas (dx, dy, scaleMult, dRotation) to selected unlocked layers.
 * Preserves relative spacing and proportions. Skips locked layers.
 */
export function batchApplyTransformDelta(
  layers: VisualLayer[],
  selectedIds: string[],
  delta: TransformBatchDelta
): VisualLayer[] {
  const targetSet = new Set(selectedIds);

  return layers.map((l) => {
    if (!targetSet.has(l.id)) return l;
    if (l.locked === true) return l; // Locked layers cannot be transformed

    const currentX = l.transform?.x ?? 0.5;
    const currentY = l.transform?.y ?? 0.5;
    const currentScale = l.transform?.scale ?? 1.0;
    const currentRotation = l.transform?.rotation ?? 0;

    const nextTransform: Record<string, any> = {
      ...(l.transform || {}),
    };

    if (typeof delta.dx === "number") {
      nextTransform.x = Math.max(0, Math.min(1, Math.round((currentX + delta.dx) * 1000) / 1000));
    }
    if (typeof delta.dy === "number") {
      nextTransform.y = Math.max(0, Math.min(1, Math.round((currentY + delta.dy) * 1000) / 1000));
    }
    if (typeof delta.scaleMult === "number") {
      nextTransform.scale = Math.max(0.1, Math.min(5.0, Math.round(currentScale * delta.scaleMult * 100) / 100));
    }
    if (typeof delta.dRotation === "number") {
      nextTransform.rotation = Math.round(((currentRotation + delta.dRotation) % 360));
    }

    return {
      ...l,
      transform: nextTransform,
    };
  });
}

