/**
 * Canvas Magnetic Snapping and Alignment Guides Tests (Phase 42A)
 *
 * Verifies:
 * 1. Canvas center snapping (x = 0.5, y = 0.5)
 * 2. Canvas edge snapping (left, right, top, bottom) with half-width/height offsets
 * 3. Neighbor layer snapping (centers, edge-to-edge alignment)
 * 4. Threshold enforcement (within threshold snaps, outside does not)
 * 5. Deterministic selection & priority tie-breaking
 * 6. Exclusions (hidden layers, invalid geometry)
 * 7. Rotation snapping (continuous vs 15 deg increments on Shift)
 * 8. Alignment guide metadata generation
 * 9. Resize boundary snapping
 * 10. Effective bounds calculation from layer models
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  calculateCanvasSnap,
  calculateResizeSnap,
  snapRotation,
  getLayerEffectiveBounds,
  DEFAULT_SNAP_THRESHOLD,
  SnapTargetLayer,
} from "./studioCanvasSnapping";
import { calculateRotationFromPointer } from "./canvasTransformUtils";

describe("Studio Canvas Magnetic Snapping (Phase 42A)", () => {
  const standardBounds = { width: 0.2, height: 0.2 }; // halfWidth = 0.1, halfHeight = 0.1

  describe("1. Canvas Center Snapping", () => {
    it("snaps x to 0.5 when within threshold", () => {
      const res = calculateCanvasSnap({ x: 0.495, y: 0.2 }, standardBounds, [], DEFAULT_SNAP_THRESHOLD);
      assert.equal(res.x, 0.5);
      assert.equal(res.snappedX, true);
      assert.equal(res.guides.some((g) => g.type === "vertical" && g.position === 0.5), true);
    });

    it("snaps y to 0.5 when within threshold", () => {
      const res = calculateCanvasSnap({ x: 0.2, y: 0.51 }, standardBounds, [], DEFAULT_SNAP_THRESHOLD);
      assert.equal(res.y, 0.5);
      assert.equal(res.snappedY, true);
      assert.equal(res.guides.some((g) => g.type === "horizontal" && g.position === 0.5), true);
    });

    it("snaps both x and y to 0.5 simultaneously when near dead center", () => {
      const res = calculateCanvasSnap({ x: 0.492, y: 0.508 }, standardBounds, [], DEFAULT_SNAP_THRESHOLD);
      assert.equal(res.x, 0.5);
      assert.equal(res.y, 0.5);
      assert.equal(res.snappedX, true);
      assert.equal(res.snappedY, true);
      assert.equal(res.guides.length, 2);
    });
  });

  describe("2. Canvas Edge Snapping", () => {
    it("snaps left edge to canvas left boundary (0.0) accounting for half-width", () => {
      // halfWidth is 0.1. If x is 0.11, left edge is 0.01 (within 0.02 threshold)
      const res = calculateCanvasSnap({ x: 0.11, y: 0.5 }, standardBounds, [], DEFAULT_SNAP_THRESHOLD);
      assert.equal(res.x, 0.1); // center becomes 0.0 + 0.1
      assert.equal(res.snappedX, true);
      assert.equal(res.guides.some((g) => g.type === "vertical" && g.position === 0.0), true);
    });

    it("snaps right edge to canvas right boundary (1.0) accounting for half-width", () => {
      // halfWidth is 0.1. If x is 0.89, right edge is 0.99 (within 0.02 threshold)
      const res = calculateCanvasSnap({ x: 0.89, y: 0.5 }, standardBounds, [], DEFAULT_SNAP_THRESHOLD);
      assert.equal(res.x, 0.9); // center becomes 1.0 - 0.1
      assert.equal(res.snappedX, true);
      assert.equal(res.guides.some((g) => g.type === "vertical" && g.position === 1.0), true);
    });

    it("snaps top edge to canvas top boundary (0.0) accounting for half-height", () => {
      // halfHeight is 0.1. If y is 0.11, top edge is 0.01 (within 0.02 threshold)
      const res = calculateCanvasSnap({ x: 0.5, y: 0.11 }, standardBounds, [], DEFAULT_SNAP_THRESHOLD);
      assert.equal(res.y, 0.1); // center becomes 0.0 + 0.1
      assert.equal(res.snappedY, true);
      assert.equal(res.guides.some((g) => g.type === "horizontal" && g.position === 0.0), true);
    });

    it("snaps bottom edge to canvas bottom boundary (1.0) accounting for half-height", () => {
      // halfHeight is 0.1. If y is 0.89, bottom edge is 0.99 (within 0.02 threshold)
      const res = calculateCanvasSnap({ x: 0.5, y: 0.89 }, standardBounds, [], DEFAULT_SNAP_THRESHOLD);
      assert.equal(res.y, 0.9); // center becomes 1.0 - 0.1
      assert.equal(res.snappedY, true);
      assert.equal(res.guides.some((g) => g.type === "horizontal" && g.position === 1.0), true);
    });
  });

  describe("3. Neighbor Layer Snapping", () => {
    const neighbor: SnapTargetLayer = {
      id: "layer_2",
      name: "Reference Box",
      enabled: true,
      bounds: {
        x: 0.2,
        y: 0.2,
        width: 0.2, // halfWidth = 0.1, left = 0.1, right = 0.3
        height: 0.2, // halfHeight = 0.1, top = 0.1, bottom = 0.3
      },
    };

    it("snaps center to neighbor center on x axis", () => {
      const res = calculateCanvasSnap({ x: 0.205, y: 0.7 }, standardBounds, [neighbor]);
      assert.equal(res.x, 0.2);
      assert.equal(res.snappedX, true);
      assert.equal(res.guides.some((g) => g.type === "vertical" && g.position === 0.2), true);
    });

    it("snaps left edge to neighbor right edge (flush right alignment)", () => {
      // neighbor right is 0.3. Active layer halfWidth is 0.1.
      // If active x is 0.405, active left is 0.305 (within 0.02 threshold)
      const res = calculateCanvasSnap({ x: 0.405, y: 0.7 }, standardBounds, [neighbor]);
      assert.equal(res.x, 0.4); // active left becomes 0.3, so center becomes 0.4
      assert.equal(res.snappedX, true);
      assert.equal(res.guides.some((g) => g.type === "vertical" && g.position === 0.3), true);
    });

    it("snaps top edge to neighbor bottom edge (stacked vertical alignment)", () => {
      // neighbor bottom is 0.3. Active layer halfHeight is 0.1.
      // If active y is 0.405, active top is 0.305 (within 0.02 threshold)
      const res = calculateCanvasSnap({ x: 0.7, y: 0.405 }, standardBounds, [neighbor]);
      assert.equal(res.y, 0.4); // active top becomes 0.3, so center becomes 0.4
      assert.equal(res.snappedY, true);
      assert.equal(res.guides.some((g) => g.type === "horizontal" && g.position === 0.3), true);
    });
  });

  describe("4. Threshold Enforcement & Free Movement", () => {
    it("does not snap when distance exceeds threshold", () => {
      const res = calculateCanvasSnap({ x: 0.47, y: 0.47 }, standardBounds, [], 0.02);
      assert.equal(res.x, 0.47);
      assert.equal(res.y, 0.47);
      assert.equal(res.snappedX, false);
      assert.equal(res.snappedY, false);
      assert.equal(res.guides.length, 0);
    });
  });

  describe("5. Deterministic Priority & Tie-Breaking", () => {
    it("prioritizes nearest candidate when multiple exist", () => {
      const neighborClose: SnapTargetLayer = {
        id: "close",
        enabled: true,
        bounds: { x: 0.508, y: 0.2, width: 0.2, height: 0.2 },
      };
      // Center is 0.5 (dist 0.015 from 0.515). Neighbor is 0.508 (dist 0.007 from 0.515).
      const res = calculateCanvasSnap({ x: 0.515, y: 0.2 }, standardBounds, [neighborClose]);
      assert.equal(res.x, 0.508); // neighbor is closer
    });

    it("breaks equal distance ties by choosing center over neighbor", () => {
      // Both center (0.5) and neighbor (0.52) are exactly 0.01 away from 0.51
      const neighborTie: SnapTargetLayer = {
        id: "tie",
        enabled: true,
        bounds: { x: 0.52, y: 0.2, width: 0.2, height: 0.2 },
      };
      const res = calculateCanvasSnap({ x: 0.51, y: 0.2 }, standardBounds, [neighborTie]);
      assert.equal(res.x, 0.5); // Center has priority 1
    });
  });

  describe("6. Exclusions & Safety", () => {
    it("ignores disabled (hidden) neighbor layers", () => {
      const hiddenNeighbor: SnapTargetLayer = {
        id: "hidden",
        enabled: false,
        bounds: { x: 0.3, y: 0.3, width: 0.2, height: 0.2 },
      };
      const res = calculateCanvasSnap({ x: 0.298, y: 0.2 }, standardBounds, [hiddenNeighbor]);
      assert.equal(res.x, 0.298);
      assert.equal(res.snappedX, false);
    });

    it("safely handles empty or invalid neighbor layers array", () => {
      const res = calculateCanvasSnap({ x: 0.2, y: 0.2 }, standardBounds, null as any);
      assert.equal(res.x, 0.2);
      assert.equal(res.y, 0.2);
    });
  });

  describe("7. Rotation Snapping", () => {
    it("allows free continuous rotation when shouldSnap is false", () => {
      assert.equal(snapRotation(14.3, false), 14.3);
      assert.equal(snapRotation(-33.7, false), -33.7);
    });

    it("snaps to nearest 15 degree increment when shouldSnap is true", () => {
      assert.equal(snapRotation(14.3, true, 15), 15);
      assert.equal(snapRotation(6.8, true, 15), 0);
      assert.equal(snapRotation(43, true, 15), 45);
      assert.equal(snapRotation(89, true, 15), 90);
      assert.equal(snapRotation(-92, true, 15), -90);
      assert.equal(snapRotation(-44, true, 15), -45);
    });

    it("works with calculateRotationFromPointer when snapIncrement is provided", () => {
      // 45 degree angle: dx = 100, dy = 100 => 45 deg
      const rot = calculateRotationFromPointer(0, 0, { x: 200, y: 200 }, { x: 100, y: 100 }, 15);
      assert.equal(rot, 45);
    });
  });

  describe("8. Resize Boundary Snapping", () => {
    it("snaps scale to align layer left edge with canvas boundary on tl drag", () => {
      // Center is at x=0.2. Base width is 0.4.
      // If scale is 0.95, half-width is 0.4*0.95/2 = 0.19. Left edge is 0.2 - 0.19 = 0.01.
      // Scale required to hit exactly 0.0 is 2*0.2/0.4 = 1.0.
      const res = calculateResizeSnap(0.95, { x: 0.2, y: 0.5 }, { width: 0.4, height: 0.4 }, "tl", 0.02);
      assert.equal(res.snapped, true);
      assert.equal(res.scale, 1.0);
      assert.equal(res.guides.some((g) => g.position === 0.0), true);
    });
  });

  describe("9. Effective Bounds Computation", () => {
    it("computes bounds for video/image layers", () => {
      const bounds = getLayerEffectiveBounds({ type: "image", transform: { scale: 1.0 } });
      assert.equal(bounds.width, 0.4);
      assert.equal(bounds.height, 0.225);
    });

    it("computes bounds for shape layers", () => {
      const bounds = getLayerEffectiveBounds({
        type: "shape",
        content: { width: 0.5, height: 0.3 },
        transform: { scale: 2.0 },
      });
      assert.equal(bounds.width, 1.0);
      assert.equal(bounds.height, 0.6);
    });

    it("computes bounds for text layers based on content length", () => {
      const bounds = getLayerEffectiveBounds({
        type: "text",
        content: { text: "Short" },
        transform: { scale: 1.0 },
      });
      assert.ok(bounds.width > 0.1);
      assert.ok(bounds.height > 0.03);
    });
  });
});
