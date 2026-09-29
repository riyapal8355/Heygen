/**
 * Studio Canvas Magnetic Snapping and Alignment Guides (Phase 42A)
 *
 * Implements pure, framework-independent geometric snapping calculations for direct
 * canvas manipulation:
 * 1. Center Snapping: Snaps layer visual center to canvas horizontal center (y=0.5) and vertical center (x=0.5).
 * 2. Edge Snapping: Snaps layer bounding box edges (left, right, top, bottom) to canvas scene boundaries (0.0, 1.0).
 * 3. Neighbor-Layer Snapping: Snaps to centers and bounding box edges of other visible, unlocked layers in the active scene.
 * 4. Deterministic Priority: Nearest candidate wins; ties broken by center > canvas edge > neighbor layer.
 * 5. Alignment Guide Generation: Emits lightweight, non-persistent guide line metadata when snapping is active.
 * 6. Rotation Snapping: Snaps continuous degrees to 15° increments when Shift is held.
 *
 * All coordinates are normalized in [0.0, 1.0] center-anchored coordinate space.
 */

import { normalizeDegrees } from "./canvasTransformUtils";

export interface Point2D {
  x: number;
  y: number;
}

export interface BoundingBox2D {
  x: number; // center x in [0.0, 1.0]
  y: number; // center y in [0.0, 1.0]
  width: number; // normalized width in [0.0, 1.0]
  height: number; // normalized height in [0.0, 1.0]
}

export interface SnapTargetLayer {
  id: string;
  name?: string;
  enabled?: boolean;
  locked?: boolean;
  bounds: BoundingBox2D;
}

export interface AlignmentGuide {
  type: "vertical" | "horizontal";
  position: number; // normalized [0, 1] position across canvas
  targetType: "center" | "edge" | "neighbor";
  label?: string;
}

export interface SnapResult {
  x: number;
  y: number;
  snappedX: boolean;
  snappedY: boolean;
  guides: AlignmentGuide[];
}

export const DEFAULT_SNAP_THRESHOLD = 0.02; // 2% of canvas dimension (~16-20px on standard screen)
export const DEFAULT_ROTATION_SNAP_INCREMENT = 15;

/**
 * Snaps rotation angle in degrees [-180, 180] to the nearest multiple of increment (e.g. 15 deg)
 * when shouldSnap is true. Otherwise preserves smooth continuous angle.
 */
export function snapRotation(
  degrees: number,
  shouldSnap: boolean,
  increment: number = DEFAULT_ROTATION_SNAP_INCREMENT
): number {
  const norm = normalizeDegrees(degrees);
  if (!shouldSnap || increment <= 0) {
    return norm;
  }
  const snapped = Math.round(norm / increment) * increment;
  return normalizeDegrees(snapped);
}

interface SnapCandidate {
  snappedPos: number;
  distance: number;
  guide: AlignmentGuide;
  priority: number; // 1: center, 2: canvas edge, 3: neighbor
}

/**
 * Calculates magnetic snapping for a moving layer against canvas center, canvas edges,
 * and neighboring visible layers.
 */
export function calculateCanvasSnap(
  currentPos: Point2D,
  layerBounds: { width: number; height: number },
  neighborLayers: SnapTargetLayer[] = [],
  threshold: number = DEFAULT_SNAP_THRESHOLD,
  options: {
    snapCenter?: boolean;
    snapEdges?: boolean;
    snapNeighbors?: boolean;
  } = {}
): SnapResult {
  const {
    snapCenter = true,
    snapEdges = true,
    snapNeighbors = true,
  } = options;

  const halfWidth = Math.max(0.01, (layerBounds.width || 0.2) / 2);
  const halfHeight = Math.max(0.01, (layerBounds.height || 0.2) / 2);

  const candidatesX: SnapCandidate[] = [];
  const candidatesY: SnapCandidate[] = [];

  // --------------------------------------------------------------------------
  // 1. CANVAS CENTER SNAPPING (x = 0.5, y = 0.5)
  // --------------------------------------------------------------------------
  if (snapCenter) {
    // Vertical Center Guide (x = 0.5)
    const distCenterX = Math.abs(currentPos.x - 0.5);
    if (distCenterX <= threshold) {
      candidatesX.push({
        snappedPos: 0.5,
        distance: distCenterX,
        guide: { type: "vertical", position: 0.5, targetType: "center", label: "Center (X)" },
        priority: 1,
      });
    }

    // Horizontal Center Guide (y = 0.5)
    const distCenterY = Math.abs(currentPos.y - 0.5);
    if (distCenterY <= threshold) {
      candidatesY.push({
        snappedPos: 0.5,
        distance: distCenterY,
        guide: { type: "horizontal", position: 0.5, targetType: "center", label: "Center (Y)" },
        priority: 1,
      });
    }
  }

  // --------------------------------------------------------------------------
  // 2. CANVAS EDGE SNAPPING (left=0.0, right=1.0, top=0.0, bottom=1.0)
  // --------------------------------------------------------------------------
  if (snapEdges) {
    // Left edge of layer to canvas left boundary (0.0)
    const layerLeft = currentPos.x - halfWidth;
    const distLeft = Math.abs(layerLeft - 0.0);
    if (distLeft <= threshold) {
      candidatesX.push({
        snappedPos: 0.0 + halfWidth,
        distance: distLeft,
        guide: { type: "vertical", position: 0.0, targetType: "edge", label: "Canvas Left" },
        priority: 2,
      });
    }

    // Right edge of layer to canvas right boundary (1.0)
    const layerRight = currentPos.x + halfWidth;
    const distRight = Math.abs(layerRight - 1.0);
    if (distRight <= threshold) {
      candidatesX.push({
        snappedPos: 1.0 - halfWidth,
        distance: distRight,
        guide: { type: "vertical", position: 1.0, targetType: "edge", label: "Canvas Right" },
        priority: 2,
      });
    }

    // Top edge of layer to canvas top boundary (0.0)
    const layerTop = currentPos.y - halfHeight;
    const distTop = Math.abs(layerTop - 0.0);
    if (distTop <= threshold) {
      candidatesY.push({
        snappedPos: 0.0 + halfHeight,
        distance: distTop,
        guide: { type: "horizontal", position: 0.0, targetType: "edge", label: "Canvas Top" },
        priority: 2,
      });
    }

    // Bottom edge of layer to canvas bottom boundary (1.0)
    const layerBottom = currentPos.y + halfHeight;
    const distBottom = Math.abs(layerBottom - 1.0);
    if (distBottom <= threshold) {
      candidatesY.push({
        snappedPos: 1.0 - halfHeight,
        distance: distBottom,
        guide: { type: "horizontal", position: 1.0, targetType: "edge", label: "Canvas Bottom" },
        priority: 2,
      });
    }
  }

  // --------------------------------------------------------------------------
  // 3. NEIGHBOR-LAYER SNAPPING
  // --------------------------------------------------------------------------
  if (snapNeighbors && Array.isArray(neighborLayers)) {
    for (const neighbor of neighborLayers) {
      if (!neighbor || neighbor.enabled === false) continue;
      const nb = neighbor.bounds;
      if (!nb || typeof nb.x !== "number" || typeof nb.y !== "number") continue;

      const nHalfW = Math.max(0.01, (nb.width || 0.2) / 2);
      const nHalfH = Math.max(0.01, (nb.height || 0.2) / 2);

      const nLeft = Math.round((nb.x - nHalfW) * 1000) / 1000;
      const nRight = Math.round((nb.x + nHalfW) * 1000) / 1000;
      const nTop = Math.round((nb.y - nHalfH) * 1000) / 1000;
      const nBottom = Math.round((nb.y + nHalfH) * 1000) / 1000;
      const nCenterX = Math.round(nb.x * 1000) / 1000;
      const nCenterY = Math.round(nb.y * 1000) / 1000;

      // X: Center alignment
      const distNCenterX = Math.abs(currentPos.x - nb.x);
      if (distNCenterX <= threshold) {
        candidatesX.push({
          snappedPos: nb.x,
          distance: distNCenterX,
          guide: { type: "vertical", position: nb.x, targetType: "neighbor", label: neighbor.name ? `Align ${neighbor.name}` : "Align Layer" },
          priority: 3,
        });
      }

      // X: Left to neighbor Left
      const distNLeftToLeft = Math.abs((currentPos.x - halfWidth) - nLeft);
      if (distNLeftToLeft <= threshold) {
        candidatesX.push({
          snappedPos: nLeft + halfWidth,
          distance: distNLeftToLeft,
          guide: { type: "vertical", position: nLeft, targetType: "neighbor", label: "Edge Align" },
          priority: 3,
        });
      }

      // X: Right to neighbor Right
      const distNRightToRight = Math.abs((currentPos.x + halfWidth) - nRight);
      if (distNRightToRight <= threshold) {
        candidatesX.push({
          snappedPos: nRight - halfWidth,
          distance: distNRightToRight,
          guide: { type: "vertical", position: nRight, targetType: "neighbor", label: "Edge Align" },
          priority: 3,
        });
      }

      // X: Left to neighbor Right
      const distNLeftToRight = Math.abs((currentPos.x - halfWidth) - nRight);
      if (distNLeftToRight <= threshold) {
        candidatesX.push({
          snappedPos: nRight + halfWidth,
          distance: distNLeftToRight,
          guide: { type: "vertical", position: nRight, targetType: "neighbor", label: "Edge Align" },
          priority: 3,
        });
      }

      // X: Right to neighbor Left
      const distNRightToLeft = Math.abs((currentPos.x + halfWidth) - nLeft);
      if (distNRightToLeft <= threshold) {
        candidatesX.push({
          snappedPos: nLeft - halfWidth,
          distance: distNRightToLeft,
          guide: { type: "vertical", position: nLeft, targetType: "neighbor", label: "Edge Align" },
          priority: 3,
        });
      }

      // Y: Center alignment
      const distNCenterY = Math.abs(currentPos.y - nb.y);
      if (distNCenterY <= threshold) {
        candidatesY.push({
          snappedPos: nb.y,
          distance: distNCenterY,
          guide: { type: "horizontal", position: nb.y, targetType: "neighbor", label: neighbor.name ? `Align ${neighbor.name}` : "Align Layer" },
          priority: 3,
        });
      }

      // Y: Top to neighbor Top
      const distNTopToTop = Math.abs((currentPos.y - halfHeight) - nTop);
      if (distNTopToTop <= threshold) {
        candidatesY.push({
          snappedPos: nTop + halfHeight,
          distance: distNTopToTop,
          guide: { type: "horizontal", position: nTop, targetType: "neighbor", label: "Edge Align" },
          priority: 3,
        });
      }

      // Y: Bottom to neighbor Bottom
      const distNBottomToBottom = Math.abs((currentPos.y + halfHeight) - nBottom);
      if (distNBottomToBottom <= threshold) {
        candidatesY.push({
          snappedPos: nBottom - halfHeight,
          distance: distNBottomToBottom,
          guide: { type: "horizontal", position: nBottom, targetType: "neighbor", label: "Edge Align" },
          priority: 3,
        });
      }

      // Y: Top to neighbor Bottom
      const distNTopToBottom = Math.abs((currentPos.y - halfHeight) - nBottom);
      if (distNTopToBottom <= threshold) {
        candidatesY.push({
          snappedPos: nBottom + halfHeight,
          distance: distNTopToBottom,
          guide: { type: "horizontal", position: nBottom, targetType: "neighbor", label: "Edge Align" },
          priority: 3,
        });
      }

      // Y: Bottom to neighbor Top
      const distNBottomToTop = Math.abs((currentPos.y + halfHeight) - nTop);
      if (distNBottomToTop <= threshold) {
        candidatesY.push({
          snappedPos: nTop - halfHeight,
          distance: distNBottomToTop,
          guide: { type: "horizontal", position: nTop, targetType: "neighbor", label: "Edge Align" },
          priority: 3,
        });
      }
    }
  }

  // --------------------------------------------------------------------------
  // 4. CANDIDATE SELECTION & DETERMINISTIC TIE-BREAKING
  // --------------------------------------------------------------------------
  const guides: AlignmentGuide[] = [];

  let finalX = currentPos.x;
  let snappedX = false;
  if (candidatesX.length > 0) {
    // Sort by shortest distance, then priority (center > edge > neighbor)
    candidatesX.sort((a, b) => {
      if (Math.abs(a.distance - b.distance) < 0.0001) {
        return a.priority - b.priority;
      }
      return a.distance - b.distance;
    });
    const bestX = candidatesX[0];
    finalX = Math.round(bestX.snappedPos * 1000) / 1000;
    snappedX = true;
    guides.push(bestX.guide);
  }

  let finalY = currentPos.y;
  let snappedY = false;
  if (candidatesY.length > 0) {
    candidatesY.sort((a, b) => {
      if (Math.abs(a.distance - b.distance) < 0.0001) {
        return a.priority - b.priority;
      }
      return a.distance - b.distance;
    });
    const bestY = candidatesY[0];
    finalY = Math.round(bestY.snappedPos * 1000) / 1000;
    snappedY = true;
    guides.push(bestY.guide);
  }

  return {
    x: finalX,
    y: finalY,
    snappedX,
    snappedY,
    guides,
  };
}

/**
 * Calculates resize boundary snapping when dragging corner handles near canvas boundaries.
 */
export function calculateResizeSnap(
  proposedScale: number,
  layerCenter: Point2D,
  baseDimensions: { width: number; height: number },
  corner: "tl" | "tr" | "br" | "bl",
  threshold: number = DEFAULT_SNAP_THRESHOLD
): { scale: number; snapped: boolean; guides: AlignmentGuide[] } {
  const baseW = Math.max(0.02, baseDimensions.width);
  const baseH = Math.max(0.02, baseDimensions.height);

  const guides: AlignmentGuide[] = [];
  let snappedScale = proposedScale;
  let snapped = false;

  const currentHalfW = (baseW * proposedScale) / 2;
  const currentHalfH = (baseH * proposedScale) / 2;

  // Left edge boundary (0.0)
  if (corner === "tl" || corner === "bl") {
    const leftDist = Math.abs((layerCenter.x - currentHalfW) - 0.0);
    if (leftDist <= threshold) {
      // center.x - (baseW * scale)/2 = 0 => scale = 2 * center.x / baseW
      if (layerCenter.x > 0) {
        snappedScale = (2 * layerCenter.x) / baseW;
        snapped = true;
        guides.push({ type: "vertical", position: 0.0, targetType: "edge", label: "Canvas Left" });
      }
    }
  }

  // Right edge boundary (1.0)
  if (corner === "tr" || corner === "br") {
    const rightDist = Math.abs((layerCenter.x + currentHalfW) - 1.0);
    if (rightDist <= threshold) {
      // center.x + (baseW * scale)/2 = 1 => scale = 2 * (1 - center.x) / baseW
      if (layerCenter.x < 1.0) {
        snappedScale = (2 * (1.0 - layerCenter.x)) / baseW;
        snapped = true;
        guides.push({ type: "vertical", position: 1.0, targetType: "edge", label: "Canvas Right" });
      }
    }
  }

  // Top edge boundary (0.0)
  if (corner === "tl" || corner === "tr") {
    const topDist = Math.abs((layerCenter.y - currentHalfH) - 0.0);
    if (topDist <= threshold) {
      if (layerCenter.y > 0) {
        snappedScale = (2 * layerCenter.y) / baseH;
        snapped = true;
        guides.push({ type: "horizontal", position: 0.0, targetType: "edge", label: "Canvas Top" });
      }
    }
  }

  // Bottom edge boundary (1.0)
  if (corner === "bl" || corner === "br") {
    const bottomDist = Math.abs((layerCenter.y + currentHalfH) - 1.0);
    if (bottomDist <= threshold) {
      if (layerCenter.y < 1.0) {
        snappedScale = (2 * (1.0 - layerCenter.y)) / baseH;
        snapped = true;
        guides.push({ type: "horizontal", position: 1.0, targetType: "edge", label: "Canvas Bottom" });
      }
    }
  }

  return {
    scale: Math.round(Math.max(0.2, Math.min(3.0, snappedScale)) * 100) / 100,
    snapped,
    guides,
  };
}

/**
 * Extracts normalized effective dimensions [width, height] in [0, 1] from layer object.
 */
export function getLayerEffectiveBounds(layer: any): { width: number; height: number } {
  if (!layer) {
    return { width: 0.2, height: 0.2 };
  }
  const scale = layer?.transform?.scale ?? 1.0;

  if (layer.type === "video" || layer.type === "image") {
    return {
      width: Math.max(0.04, 0.40 * scale),
      height: Math.max(0.04, 0.225 * scale),
    };
  }

  if (layer.type === "shape") {
    const c = layer.content || {};
    return {
      width: Math.max(0.02, (c.width ?? 0.35) * scale),
      height: Math.max(0.02, (c.height ?? 0.20) * scale),
    };
  }

  if (layer.type === "sticker") {
    const c = layer.content || {};
    const size = (c.size || 80) / 1000;
    return {
      width: Math.max(0.04, size * scale),
      height: Math.max(0.04, size * scale),
    };
  }

  if (layer.type === "text") {
    const c = layer.content || {};
    const textLen = (c.text || layer.name || "Text").length;
    const estWidth = Math.min(0.85, Math.max(0.1, (textLen * 0.025 + 0.05) * scale));
    return {
      width: estWidth,
      height: Math.max(0.04, 0.08 * scale),
    };
  }

  return { width: 0.2 * scale, height: 0.2 * scale };
}
