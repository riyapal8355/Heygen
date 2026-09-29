/**
 * Canvas Transform Utilities for HeyZen Studio
 *
 * Implements pure, framework-independent mathematical operations for direct canvas
 * manipulation (drag-to-move, proportional corner resizing, and center rotation).
 *
 * Canonical Coordinate System:
 * - Normalized position: x in [0.0, 1.0], y in [0.0, 1.0] relative to canvas dimensions.
 * - Origin (0, 0): Top-left corner of canvas.
 * - Center (0.5, 0.5): Center of canvas.
 * - Scale: Uniform multiplier clamped between 0.2 and 3.0 (default 1.0).
 * - Rotation: Clockwise degrees normalized to [-180, 180] (default 0.0).
 * - Anchor: Exact visual center of the layer.
 */

export interface Point2D {
  x: number;
  y: number;
}

export interface RectDimensions {
  width: number;
  height: number;
}

export interface LayerTransformState {
  x: number;
  y: number;
  scale: number;
  rotation: number;
}

/**
 * Clamps a numerical value between min and max bounds.
 * Falls back to min if value is NaN or not finite.
 */
export function clamp(val: number, min: number, max: number): number {
  if (!Number.isFinite(val)) {
    return min;
  }
  if (min > max) {
    return min;
  }
  return Math.max(min, Math.min(max, val));
}

/**
 * Calculates Euclidean distance between two 2D points.
 */
export function distance(p1: Point2D, p2: Point2D): number {
  const dx = p2.x - p1.x;
  const dy = p2.y - p1.y;
  const dist = Math.sqrt(dx * dx + dy * dy);
  return Number.isFinite(dist) ? dist : 0;
}

/**
 * Normalizes any degree value into [-180, 180] range.
 * Preserves the existing clockwise degree convention.
 */
export function normalizeDegrees(deg: number): number {
  if (!Number.isFinite(deg)) {
    return 0;
  }
  // Wrap to (-180, 180]
  let normalized = ((deg + 180) % 360 + 360) % 360 - 180;
  if (normalized === -180 && deg > 0) {
    normalized = 180;
  }
  return Math.round(normalized * 100) / 100;
}

/**
 * Calculates the shortest angular difference (in degrees) from angle1 to angle2.
 * Output is in [-180, 180], preventing sudden jumps across the +/-180 boundary.
 */
export function shortestAngleDelta(fromAngle: number, toAngle: number): number {
  const diff = toAngle - fromAngle;
  return normalizeDegrees(diff);
}

/**
 * Converts screen/client pointer delta to normalized [0, 1] canvas coordinates.
 */
export function pointerToNormalizedDelta(
  startPointer: Point2D,
  currentPointer: Point2D,
  canvasRect: RectDimensions
): Point2D {
  const width = canvasRect.width > 0 ? canvasRect.width : 1;
  const height = canvasRect.height > 0 ? canvasRect.height : 1;

  const dx = (currentPointer.x - startPointer.x) / width;
  const dy = (currentPointer.y - startPointer.y) / height;

  return {
    x: Number.isFinite(dx) ? dx : 0,
    y: Number.isFinite(dy) ? dy : 0,
  };
}

/**
 * Calculates new layer position from drag movement, clamped to [0, 1].
 */
export function calculatePositionFromPointer(
  startPosition: Point2D,
  startPointer: Point2D,
  currentPointer: Point2D,
  canvasRect: RectDimensions,
  clampBounds: { minX?: number; maxX?: number; minY?: number; maxY?: number } = {}
): Point2D {
  const minX = clampBounds.minX ?? 0.0;
  const maxX = clampBounds.maxX ?? 1.0;
  const minY = clampBounds.minY ?? 0.0;
  const maxY = clampBounds.maxY ?? 1.0;

  const delta = pointerToNormalizedDelta(startPointer, currentPointer, canvasRect);

  const newX = clamp(startPosition.x + delta.x, minX, maxX);
  const newY = clamp(startPosition.y + delta.y, minY, maxY);

  return {
    x: Math.round(newX * 1000) / 1000,
    y: Math.round(newY * 1000) / 1000,
  };
}

/**
 * Calculates proportional scale based on pointer radial distance from layer center.
 * Clamps scale between minScale (default 0.2) and maxScale (default 3.0).
 */
export function calculateScaleFromPointer(
  startScale: number,
  startPointer: Point2D,
  currentPointer: Point2D,
  layerCenter: Point2D,
  minScale = 0.2,
  maxScale = 3.0
): number {
  const initialDist = distance(startPointer, layerCenter);
  const currentDist = distance(currentPointer, layerCenter);

  // Guard against division by zero or tiny initial distances
  if (initialDist < 1.0 || !Number.isFinite(initialDist)) {
    return clamp(startScale, minScale, maxScale);
  }

  if (!Number.isFinite(currentDist)) {
    return clamp(startScale, minScale, maxScale);
  }

  const scaleRatio = currentDist / initialDist;
  const newScale = startScale * scaleRatio;

  return Math.round(clamp(newScale, minScale, maxScale) * 100) / 100;
}

/**
 * Calculates layer rotation angle (in degrees, [-180, 180]) from pointer position around center.
 * Avoids rotation jumps when crossing +/-180 degrees.
 */
export function calculateRotationFromPointer(
  initialRotation: number,
  startPointerAngle: number,
  currentPointer: Point2D,
  layerCenter: Point2D,
  snapIncrement?: number
): number {
  const dx = currentPointer.x - layerCenter.x;
  const dy = currentPointer.y - layerCenter.y;

  // If pointer is right on center, preserve initial rotation
  if (Math.abs(dx) < 0.001 && Math.abs(dy) < 0.001) {
    return normalizeDegrees(initialRotation);
  }

  // Calculate current pointer angle in degrees (clockwise: 0 deg = +X, 90 deg = +Y in screen coords)
  const currentPointerAngle = (Math.atan2(dy, dx) * 180) / Math.PI;

  // Shortest angular change to avoid discontinuous jumps
  const angleDelta = shortestAngleDelta(startPointerAngle, currentPointerAngle);

  const rawRotation = initialRotation + angleDelta;
  if (snapIncrement && snapIncrement > 0) {
    const snapped = Math.round(rawRotation / snapIncrement) * snapIncrement;
    return normalizeDegrees(snapped);
  }

  return normalizeDegrees(rawRotation);
}

/**
 * Computes angle of a point relative to center in degrees [-180, 180].
 */
export function getPointerAngleFromCenter(pointer: Point2D, center: Point2D): number {
  const dx = pointer.x - center.x;
  const dy = pointer.y - center.y;
  if (Math.abs(dx) < 0.001 && Math.abs(dy) < 0.001) {
    return 0;
  }
  return normalizeDegrees((Math.atan2(dy, dx) * 180) / Math.PI);
}
