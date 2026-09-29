/**
 * Studio Keyboard Navigation & Shortcuts Test Suite
 *
 * Exhaustively tests:
 * 1. Focus guard (input, textarea, select, contenteditable, normal elements).
 * 2. Active visual layer resolution.
 * 3. Arrow-key nudging (normal 0.005, shift 0.05, bounds clamping [0, 1]).
 * 4. Locked layer mutation & deletion guards.
 * 5. Layer duplication and in-memory clipboard cloning.
 * 6. Phase 38 locking & visibility integrity preservation.
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  isInputOrEditableTarget,
  getSelectedVisualLayer,
  calculateKeyboardNudge,
  canMutateLayerViaKeyboard,
  canDeleteLayerViaKeyboard,
  createLayerDuplicatePayload,
} from "./studioKeyboardUtils";

describe("Studio Keyboard Navigation & Shortcuts", () => {
  describe("1. Focus & Input Safety Guard (isInputOrEditableTarget)", () => {
    it("detects standard INPUT element", () => {
      const mockInput = { tagName: "INPUT" };
      assert.equal(isInputOrEditableTarget(mockInput), true);
    });

    it("detects TEXTAREA element", () => {
      const mockTextarea = { tagName: "TEXTAREA" };
      assert.equal(isInputOrEditableTarget(mockTextarea), true);
    });

    it("detects SELECT element", () => {
      const mockSelect = { tagName: "SELECT" };
      assert.equal(isInputOrEditableTarget(mockSelect), true);
    });

    it("detects element with isContentEditable true", () => {
      const mockEditable = { tagName: "DIV", isContentEditable: true };
      assert.equal(isInputOrEditableTarget(mockEditable), true);
    });

    it("detects descendant inside contenteditable ancestor", () => {
      const mockSpan = {
        tagName: "SPAN",
        closest: (selector: string) =>
          selector.includes("contenteditable") ? { tagName: "DIV" } : null,
      };
      assert.equal(isInputOrEditableTarget(mockSpan), true);
    });

    it("detects descendant inside input/textarea/select ancestor", () => {
      const mockChild = {
        tagName: "SPAN",
        closest: (selector: string) =>
          selector.includes("input") ? { tagName: "INPUT" } : null,
      };
      assert.equal(isInputOrEditableTarget(mockChild), true);
    });

    it("detects element inside modal or ignore dialog", () => {
      const mockModalChild = {
        tagName: "BUTTON",
        closest: (selector: string) =>
          selector.includes("dialog") ? { tagName: "DIV", role: "dialog" } : null,
      };
      assert.equal(isInputOrEditableTarget(mockModalChild), true);
    });

    it("allows standard studio canvas / container DIV", () => {
      const mockDiv = {
        tagName: "DIV",
        isContentEditable: false,
        closest: () => null,
      };
      assert.equal(isInputOrEditableTarget(mockDiv), false);
    });

    it("allows canvas or button elements outside input contexts", () => {
      const mockCanvas = {
        tagName: "CANVAS",
        isContentEditable: false,
        closest: () => null,
      };
      assert.equal(isInputOrEditableTarget(mockCanvas), false);
    });

    it("safely handles null and undefined targets", () => {
      assert.equal(isInputOrEditableTarget(null), false);
      assert.equal(isInputOrEditableTarget(undefined), false);
    });
  });

  describe("2. Active Visual Layer Resolution (getSelectedVisualLayer)", () => {
    const mockScenes = [
      {
        id: "scene_1",
        layers: [
          { id: "media_1", type: "image", name: "Photo 1", transform: { x: 0.3, y: 0.4 } },
          { id: "text_1", type: "text", name: "Title 1", transform: { x: 0.5, y: 0.2 } },
          { id: "shape_1", type: "shape", name: "Box 1", transform: { x: 0.7, y: 0.8 } },
        ],
      },
      {
        id: "scene_2",
        layers: [
          { id: "media_2", type: "video", name: "Video 2", transform: { x: 0.5, y: 0.5 } },
        ],
      },
    ];

    it("resolves active media layer when selectedMediaLayerId is set", () => {
      const res = getSelectedVisualLayer(mockScenes, 0, "media_1", null, null);
      assert.ok(res);
      assert.equal(res.kind, "media");
      assert.equal(res.layer.id, "media_1");
      assert.equal(res.sceneIndex, 0);
    });

    it("resolves active text layer when selectedTextLayerId is set", () => {
      const res = getSelectedVisualLayer(mockScenes, 0, null, "text_1", null);
      assert.ok(res);
      assert.equal(res.kind, "text");
      assert.equal(res.layer.id, "text_1");
    });

    it("resolves active element layer when selectedElementLayerId is set", () => {
      const res = getSelectedVisualLayer(mockScenes, 0, null, null, "shape_1");
      assert.ok(res);
      assert.equal(res.kind, "element");
      assert.equal(res.layer.id, "shape_1");
    });

    it("resolves correctly on non-zero scene index", () => {
      const res = getSelectedVisualLayer(mockScenes, 1, "media_2", null, null);
      assert.ok(res);
      assert.equal(res.layer.id, "media_2");
      assert.equal(res.sceneIndex, 1);
    });

    it("returns null when no visual layer ID is selected", () => {
      const res = getSelectedVisualLayer(mockScenes, 0, null, null, null);
      assert.equal(res, null);
    });

    it("returns null when selected layer ID is not in active scene", () => {
      const res = getSelectedVisualLayer(mockScenes, 0, "media_2", null, null);
      assert.equal(res, null);
    });

    it("handles empty or invalid scene array gracefully", () => {
      assert.equal(getSelectedVisualLayer([], 0, "media_1", null, null), null);
      assert.equal(getSelectedVisualLayer(null as any, 0, "media_1", null, null), null);
    });
  });

  describe("3. Arrow-Key Nudging (calculateKeyboardNudge)", () => {
    it("nudges left by 0.005 on ArrowLeft", () => {
      const res = calculateKeyboardNudge({ x: 0.5, y: 0.5 }, "ArrowLeft", false);
      assert.equal(res.x, 0.495);
      assert.equal(res.y, 0.5);
    });

    it("nudges right by 0.005 on ArrowRight", () => {
      const res = calculateKeyboardNudge({ x: 0.5, y: 0.5 }, "ArrowRight", false);
      assert.equal(res.x, 0.505);
      assert.equal(res.y, 0.5);
    });

    it("nudges up by 0.005 on ArrowUp", () => {
      const res = calculateKeyboardNudge({ x: 0.5, y: 0.5 }, "ArrowUp", false);
      assert.equal(res.x, 0.5);
      assert.equal(res.y, 0.495);
    });

    it("nudges down by 0.005 on ArrowDown", () => {
      const res = calculateKeyboardNudge({ x: 0.5, y: 0.5 }, "ArrowDown", false);
      assert.equal(res.x, 0.5);
      assert.equal(res.y, 0.505);
    });

    it("nudges by large step 0.05 when Shift is pressed", () => {
      const left = calculateKeyboardNudge({ x: 0.5, y: 0.5 }, "ArrowLeft", true);
      assert.equal(left.x, 0.45);

      const right = calculateKeyboardNudge({ x: 0.5, y: 0.5 }, "ArrowRight", true);
      assert.equal(right.x, 0.55);

      const up = calculateKeyboardNudge({ x: 0.5, y: 0.5 }, "ArrowUp", true);
      assert.equal(up.y, 0.45);

      const down = calculateKeyboardNudge({ x: 0.5, y: 0.5 }, "ArrowDown", true);
      assert.equal(down.y, 0.55);
    });

    it("clamps position at boundaries [0.0, 1.0]", () => {
      // Left boundary
      const atLeft = calculateKeyboardNudge({ x: 0.002, y: 0.5 }, "ArrowLeft", false);
      assert.equal(atLeft.x, 0.0);

      // Right boundary
      const atRight = calculateKeyboardNudge({ x: 0.998, y: 0.5 }, "ArrowRight", false);
      assert.equal(atRight.x, 1.0);

      // Top boundary
      const atTop = calculateKeyboardNudge({ x: 0.5, y: 0.01 }, "ArrowUp", true);
      assert.equal(atTop.y, 0.0);

      // Bottom boundary
      const atBottom = calculateKeyboardNudge({ x: 0.5, y: 0.98 }, "ArrowDown", true);
      assert.equal(atBottom.y, 1.0);
    });

    it("handles missing initial position with canonical center fallback (0.5, 0.5)", () => {
      const res = calculateKeyboardNudge(undefined, "ArrowRight", false);
      assert.equal(res.x, 0.505);
      assert.equal(res.y, 0.5);
    });
  });

  describe("4. Locked Layer Protection", () => {
    it("blocks keyboard mutation when layer is locked", () => {
      const lockedLayer = { id: "l1", locked: true };
      assert.equal(canMutateLayerViaKeyboard(lockedLayer), false);
    });

    it("allows keyboard mutation when layer is unlocked", () => {
      const unlockedLayer = { id: "l2", locked: false };
      assert.equal(canMutateLayerViaKeyboard(unlockedLayer), true);

      const defaultUnlockedLayer = { id: "l3" };
      assert.equal(canMutateLayerViaKeyboard(defaultUnlockedLayer), true);
    });

    it("blocks keyboard deletion when layer is locked", () => {
      const lockedLayer = { id: "l1", locked: true };
      assert.equal(canDeleteLayerViaKeyboard(lockedLayer), false);
    });

    it("allows keyboard deletion when layer is unlocked", () => {
      const unlockedLayer = { id: "l2", locked: false };
      assert.equal(canDeleteLayerViaKeyboard(unlockedLayer), true);
    });

    it("handles null and undefined layers defensively", () => {
      assert.equal(canMutateLayerViaKeyboard(null), false);
      assert.equal(canDeleteLayerViaKeyboard(null), false);
    });
  });

  describe("5. Layer Duplication & In-Memory Clipboard Cloning (createLayerDuplicatePayload)", () => {
    it("generates a new unique ID with correct type prefix", () => {
      const srcMedia = { id: "layer_orig", type: "image", name: "Banner" };
      const { clonedLayer, newId } = createLayerDuplicatePayload(srcMedia, "media");
      assert.ok(newId.startsWith("layer_"));
      assert.notEqual(newId, "layer_orig");
      assert.equal(clonedLayer.id, newId);
    });

    it("appends '(Copy)' to the duplicated layer name", () => {
      const srcText = { id: "text_1", type: "text", name: "Heading" };
      const { clonedLayer } = createLayerDuplicatePayload(srcText, "text");
      assert.equal(clonedLayer.name, "Heading (Copy)");

      // Does not double append if already named (Copy)
      const { clonedLayer: doubleClone } = createLayerDuplicatePayload(clonedLayer, "text");
      assert.equal(doubleClone.name, "Heading (Copy)");
    });

    it("offsets transform coordinates by +0.05, clamped to 0.9 max", () => {
      const src = {
        id: "el_1",
        transform: { x: 0.4, y: 0.5, scale: 1.2, rotation: 15 },
      };
      const { clonedLayer } = createLayerDuplicatePayload(src, "element");
      assert.equal(clonedLayer.transform.x, 0.45);
      assert.equal(clonedLayer.transform.y, 0.55);
      assert.equal(clonedLayer.transform.scale, 1.2);
      assert.equal(clonedLayer.transform.rotation, 15);

      // Near edge clamps to 0.9
      const nearEdge = { id: "el_2", transform: { x: 0.88, y: 0.92 } };
      const { clonedLayer: clampedClone } = createLayerDuplicatePayload(nearEdge, "element");
      assert.equal(clampedClone.transform.x, 0.9);
      assert.equal(clampedClone.transform.y, 0.9);
    });

    it("ensures duplicated layer is unlocked even if source was locked", () => {
      const lockedSource = {
        id: "src_locked",
        locked: true,
        type: "image",
      };
      const { clonedLayer } = createLayerDuplicatePayload(lockedSource, "media");
      assert.equal(clonedLayer.locked, false);
      assert.equal(lockedSource.locked, true); // Source unchanged
    });

    it("preserves layer content, styling, and timing intact", () => {
      const complexLayer = {
        id: "shape_10",
        type: "shape",
        start_time: 1.5,
        end_time: 4.5,
        enabled: true,
        content: {
          shape_type: "rectangle",
          fill: "#ff0000",
          border_width: 2,
        },
      };
      const { clonedLayer } = createLayerDuplicatePayload(complexLayer, "element");
      assert.equal(clonedLayer.start_time, 1.5);
      assert.equal(clonedLayer.end_time, 4.5);
      assert.equal(clonedLayer.enabled, true);
      assert.deepEqual(clonedLayer.content, complexLayer.content);
    });
  });
});
