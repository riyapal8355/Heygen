/**
 * Unit Tests for Canvas Transform Utilities (Phase 34)
 *
 * Verifies mathematical correctness, coordinate resolution invariance (16:9, 9:16, 1:1),
 * clamping bounds, proportional scaling, rotation normalization, and numerical safety.
 */

import test, { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  clamp,
  distance,
  normalizeDegrees,
  shortestAngleDelta,
  pointerToNormalizedDelta,
  calculatePositionFromPointer,
  calculateScaleFromPointer,
  calculateRotationFromPointer,
  getPointerAngleFromCenter,
} from "./canvasTransformUtils";

describe("Canvas Transform Utilities", () => {
  describe("clamp()", () => {
    it("clamps values strictly within min and max", () => {
      assert.strictEqual(clamp(0.5, 0.0, 1.0), 0.5);
      assert.strictEqual(clamp(-0.2, 0.0, 1.0), 0.0);
      assert.strictEqual(clamp(1.5, 0.0, 1.0), 1.0);
    });

    it("handles NaN and Infinity defensively", () => {
      assert.strictEqual(clamp(NaN, 0.0, 1.0), 0.0);
      assert.strictEqual(clamp(Infinity, 0.0, 1.0), 0.0);
      assert.strictEqual(clamp(-Infinity, 0.0, 1.0), 0.0);
    });

    it("handles inverted bounds safely", () => {
      assert.strictEqual(clamp(0.5, 1.0, 0.0), 1.0);
    });
  });

  describe("distance()", () => {
    it("computes Euclidean distance accurately", () => {
      assert.strictEqual(distance({ x: 0, y: 0 }, { x: 3, y: 4 }), 5);
      assert.strictEqual(distance({ x: 10, y: 10 }, { x: 10, y: 10 }), 0);
    });

    it("handles NaN safely", () => {
      assert.strictEqual(distance({ x: NaN, y: 0 }, { x: 0, y: 0 }), 0);
    });
  });

  describe("normalizeDegrees()", () => {
    it("keeps degrees within [-180, 180]", () => {
      assert.strictEqual(normalizeDegrees(0), 0);
      assert.strictEqual(normalizeDegrees(90), 90);
      assert.strictEqual(normalizeDegrees(180), 180);
      assert.strictEqual(normalizeDegrees(-90), -90);
      assert.strictEqual(normalizeDegrees(-180), -180);
    });

    it("wraps angles outside [-180, 180]", () => {
      assert.strictEqual(normalizeDegrees(270), -90);
      assert.strictEqual(normalizeDegrees(360), 0);
      assert.strictEqual(normalizeDegrees(450), 90);
      assert.strictEqual(normalizeDegrees(-270), 90);
      assert.strictEqual(normalizeDegrees(-360), 0);
    });

    it("handles NaN safely", () => {
      assert.strictEqual(normalizeDegrees(NaN), 0);
      assert.strictEqual(normalizeDegrees(Infinity), 0);
    });
  });

  describe("shortestAngleDelta()", () => {
    it("computes shortest angular difference", () => {
      assert.strictEqual(shortestAngleDelta(10, 30), 20);
      assert.strictEqual(shortestAngleDelta(30, 10), -20);
    });

    it("handles crossing +/-180 boundary smoothly", () => {
      // From 170 to -170 is +20 degrees, not -340
      assert.strictEqual(shortestAngleDelta(170, -170), 20);
      // From -170 to 170 is -20 degrees, not +340
      assert.strictEqual(shortestAngleDelta(-170, 170), -20);
    });
  });

  describe("pointerToNormalizedDelta()", () => {
    it("converts delta for 16:9 canvas (e.g. 768x432)", () => {
      const rect = { width: 768, height: 432 };
      const start = { x: 100, y: 100 };
      const current = { x: 176.8, y: 143.2 };
      const delta = pointerToNormalizedDelta(start, current, rect);

      assert.strictEqual(Math.round(delta.x * 10), 1); // 76.8 / 768 = 0.1
      assert.strictEqual(Math.round(delta.y * 10), 1); // 43.2 / 432 = 0.1
    });

    it("converts delta for 9:16 canvas (e.g. 320x568)", () => {
      const rect = { width: 320, height: 568 };
      const start = { x: 50, y: 50 };
      const current = { x: 82, y: 106.8 };
      const delta = pointerToNormalizedDelta(start, current, rect);

      assert.strictEqual(Math.round(delta.x * 10), 1); // 32 / 320 = 0.1
      assert.strictEqual(Math.round(delta.y * 10), 1); // 56.8 / 568 = 0.1
    });

    it("converts delta for 1:1 canvas (e.g. 500x500)", () => {
      const rect = { width: 500, height: 500 };
      const start = { x: 100, y: 100 };
      const current = { x: 200, y: 50 };
      const delta = pointerToNormalizedDelta(start, current, rect);

      assert.strictEqual(delta.x, 0.2); // 100 / 500 = 0.2
      assert.strictEqual(delta.y, -0.1); // -50 / 500 = -0.1
    });

    it("protects against zero canvas dimensions and NaN", () => {
      const deltaZero = pointerToNormalizedDelta({ x: 0, y: 0 }, { x: 10, y: 10 }, { width: 0, height: 0 });
      assert.strictEqual(deltaZero.x, 10);
      assert.strictEqual(deltaZero.y, 10);

      const deltaNaN = pointerToNormalizedDelta({ x: NaN, y: 0 }, { x: 10, y: 10 }, { width: 100, height: 100 });
      assert.strictEqual(deltaNaN.x, 0);
    });
  });

  describe("calculatePositionFromPointer()", () => {
    const canvasRect = { width: 800, height: 600 };

    it("calculates new center position accurately", () => {
      const pos = calculatePositionFromPointer(
        { x: 0.5, y: 0.5 },
        { x: 400, y: 300 },
        { x: 480, y: 360 },
        canvasRect
      );
      assert.strictEqual(pos.x, 0.6); // 0.5 + 80/800 = 0.6
      assert.strictEqual(pos.y, 0.6); // 0.5 + 60/600 = 0.6
    });

    it("clamps position at boundaries [0, 1]", () => {
      // Drag way off top-left
      const posTL = calculatePositionFromPointer(
        { x: 0.5, y: 0.5 },
        { x: 400, y: 300 },
        { x: -500, y: -500 },
        canvasRect
      );
      assert.strictEqual(posTL.x, 0.0);
      assert.strictEqual(posTL.y, 0.0);

      // Drag way off bottom-right
      const posBR = calculatePositionFromPointer(
        { x: 0.5, y: 0.5 },
        { x: 400, y: 300 },
        { x: 1500, y: 1500 },
        canvasRect
      );
      assert.strictEqual(posBR.x, 1.0);
      assert.strictEqual(posBR.y, 1.0);
    });
  });

  describe("calculateScaleFromPointer()", () => {
    const center = { x: 400, y: 300 };

    it("increases scale proportionally when pointer distance expands", () => {
      const startPointer = { x: 450, y: 300 }; // dist = 50
      const currentPointer = { x: 500, y: 300 }; // dist = 100 (2x)
      const scale = calculateScaleFromPointer(1.0, startPointer, currentPointer, center);
      assert.strictEqual(scale, 2.0);
    });

    it("decreases scale proportionally when pointer distance contracts", () => {
      const startPointer = { x: 500, y: 300 }; // dist = 100
      const currentPointer = { x: 450, y: 300 }; // dist = 50 (0.5x)
      const scale = calculateScaleFromPointer(1.0, startPointer, currentPointer, center);
      assert.strictEqual(scale, 0.5);
    });

    it("enforces minimum scale clamp (0.2)", () => {
      const startPointer = { x: 500, y: 300 }; // dist = 100
      const currentPointer = { x: 405, y: 300 }; // dist = 5 (0.05x -> clamps to 0.2)
      const scale = calculateScaleFromPointer(1.0, startPointer, currentPointer, center);
      assert.strictEqual(scale, 0.2);
    });

    it("enforces maximum scale clamp (3.0)", () => {
      const startPointer = { x: 450, y: 300 }; // dist = 50
      const currentPointer = { x: 650, y: 300 }; // dist = 250 (5x -> clamps to 3.0)
      const scale = calculateScaleFromPointer(1.0, startPointer, currentPointer, center);
      assert.strictEqual(scale, 3.0);
    });

    it("safely handles zero or tiny initial distances without NaN", () => {
      const scaleZero = calculateScaleFromPointer(1.0, center, { x: 450, y: 300 }, center);
      assert.strictEqual(scaleZero, 1.0);
      assert.strictEqual(Number.isFinite(scaleZero), true);
    });
  });

  describe("calculateRotationFromPointer()", () => {
    const center = { x: 400, y: 300 };

    it("calculates 0 degree starting orientation", () => {
      const startPointer = { x: 400, y: 200 }; // directly above center (dy = -100, dx = 0 => -90 deg)
      const startAngle = getPointerAngleFromCenter(startPointer, center);
      assert.strictEqual(startAngle, -90);

      const rot = calculateRotationFromPointer(0.0, startAngle, startPointer, center);
      assert.strictEqual(rot, 0.0);
    });

    it("computes 90 degree clockwise rotation", () => {
      const startPointer = { x: 400, y: 200 }; // -90 deg
      const startAngle = getPointerAngleFromCenter(startPointer, center);

      // Rotate 90 deg clockwise to directly right (dx = 100, dy = 0 => 0 deg)
      const currentPointer = { x: 500, y: 300 };
      const rot = calculateRotationFromPointer(0.0, startAngle, currentPointer, center);
      assert.strictEqual(rot, 90);
    });

    it("computes 180 degree rotation", () => {
      const startPointer = { x: 400, y: 200 }; // -90 deg
      const startAngle = getPointerAngleFromCenter(startPointer, center);

      // Rotate 180 deg to directly below (dx = 0, dy = 100 => 90 deg)
      const currentPointer = { x: 400, y: 400 };
      const rot = calculateRotationFromPointer(0.0, startAngle, currentPointer, center);
      assert.strictEqual(rot, 180);
    });

    it("computes -90 degree counter-clockwise rotation", () => {
      const startPointer = { x: 400, y: 200 }; // -90 deg
      const startAngle = getPointerAngleFromCenter(startPointer, center);

      // Rotate -90 deg to directly left (dx = -100, dy = 0 => 180 or -180 deg)
      const currentPointer = { x: 300, y: 300 };
      const rot = calculateRotationFromPointer(0.0, startAngle, currentPointer, center);
      assert.strictEqual(rot, -90);
    });

    it("crosses the +/-180 boundary smoothly without sudden flips", () => {
      // Initial rotation is 170 deg, pointer at 80 deg relative to center
      const initialRotation = 170;
      const startAngle = 80;

      // Pointer moves slightly clockwise past boundary (+20 deg change)
      // Angle goes from 80 deg to 100 deg
      const currentPointer = {
        x: center.x + 100 * Math.cos((100 * Math.PI) / 180),
        y: center.y + 100 * Math.sin((100 * Math.PI) / 180),
      };

      const rot = calculateRotationFromPointer(initialRotation, startAngle, currentPointer, center);
      // 170 + 20 = 190 -> normalized to -170
      assert.strictEqual(rot, -170);
    });

    it("safely handles pointer exactly on center", () => {
      const rot = calculateRotationFromPointer(45, 0, center, center);
      assert.strictEqual(rot, 45);
    });
  });
});
