import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  isLayerLocked,
  isLayerEnabled,
  toggleLayerEnabledState,
  toggleLayerLockedState,
  guardCanvasGesture,
  guardLayerMutation,
  guardTimelineDrag,
} from "./studioLockingVisibility";

describe("Studio Layer Locking & Visibility Unification", () => {
  describe("Visibility Canonical State (enabled)", () => {
    it("treats missing or undefined enabled as true (backward compatibility)", () => {
      assert.equal(isLayerEnabled({}), true);
      assert.equal(isLayerEnabled({ id: "layer_1" }), true);
      assert.equal(isLayerEnabled(null), true);
      assert.equal(isLayerEnabled(undefined), true);
    });

    it("correctly identifies enabled layers", () => {
      assert.equal(isLayerEnabled({ enabled: true }), true);
      assert.equal(isLayerEnabled({ enabled: false }), false);
    });

    it("toggles enabled state accurately (true -> false, false -> true)", () => {
      assert.equal(toggleLayerEnabledState({ enabled: true }), false);
      assert.equal(toggleLayerEnabledState({ enabled: false }), true);
      assert.equal(toggleLayerEnabledState({}), false); // default true -> toggles to false
    });
  });

  describe("Locking Canonical State (locked)", () => {
    it("treats missing or undefined locked as false (backward compatibility)", () => {
      assert.equal(isLayerLocked({}), false);
      assert.equal(isLayerLocked({ id: "layer_1" }), false);
      assert.equal(isLayerLocked(null), false);
      assert.equal(isLayerLocked(undefined), false);
    });

    it("correctly identifies locked layers", () => {
      assert.equal(isLayerLocked({ locked: true }), true);
      assert.equal(isLayerLocked({ locked: false }), false);
    });

    it("toggles locked state accurately (false -> true, true -> false)", () => {
      assert.equal(toggleLayerLockedState({ locked: false }), true);
      assert.equal(toggleLayerLockedState({ locked: true }), false);
      assert.equal(toggleLayerLockedState({}), true); // default false -> toggles to true
    });

    it("guarantees lock state and visibility state are completely orthogonal", () => {
      const combinations = [
        { locked: false, enabled: true, expectedVisible: true, expectedLocked: false },
        { locked: false, enabled: false, expectedVisible: false, expectedLocked: false },
        { locked: true, enabled: true, expectedVisible: true, expectedLocked: true },
        { locked: true, enabled: false, expectedVisible: false, expectedLocked: true },
      ];

      for (const item of combinations) {
        assert.equal(isLayerEnabled(item), item.expectedVisible);
        assert.equal(isLayerLocked(item), item.expectedLocked);
      }
    });
  });

  describe("Canvas Direct Manipulation Locking Guards", () => {
    it("allows move gesture when layer is unlocked", () => {
      let moved = false;
      const allowed = guardCanvasGesture(false, () => {
        moved = true;
      });
      assert.equal(allowed, true);
      assert.equal(moved, true);
    });

    it("rejects move gesture when layer is locked", () => {
      let moved = false;
      const allowed = guardCanvasGesture(true, () => {
        moved = true;
      });
      assert.equal(allowed, false);
      assert.equal(moved, false);
    });

    it("rejects corner resize gesture when layer is locked", () => {
      let resized = false;
      const allowed = guardCanvasGesture(true, () => {
        resized = true;
      });
      assert.equal(allowed, false);
      assert.equal(resized, false);
    });

    it("rejects rotation gesture when layer is locked", () => {
      let rotated = false;
      const allowed = guardCanvasGesture(true, () => {
        rotated = true;
      });
      assert.equal(allowed, false);
      assert.equal(rotated, false);
    });

    it("ensures no transform mutation occurs when locked", () => {
      const layer = {
        id: "layer_locked_1",
        locked: true,
        transform: { x: 0.5, y: 0.5, scale: 1.0, rotation: 0.0 },
      };

      let mutated = false;
      const executed = guardLayerMutation(layer, () => {
        mutated = true;
        layer.transform.x = 0.8;
      });

      assert.equal(executed, false);
      assert.equal(mutated, false);
      assert.equal(layer.transform.x, 0.5);
    });
  });

  describe("Timeline Clip Manipulation Locking Guards", () => {
    it("allows drag session initiation when clip is unlocked", () => {
      let selected = false;
      let dragStarted = false;

      const result = guardTimelineDrag(
        false,
        () => {
          selected = true;
        },
        () => {
          dragStarted = true;
        }
      );

      assert.equal(result.dragAllowed, true);
      assert.equal(result.selected, false);
      assert.equal(dragStarted, true);
      assert.equal(selected, false);
    });

    it("rejects timeline move drag when clip is locked but preserves selection", () => {
      let selected = false;
      let dragStarted = false;

      const result = guardTimelineDrag(
        true,
        () => {
          selected = true;
        },
        () => {
          dragStarted = true;
        }
      );

      assert.equal(result.dragAllowed, false);
      assert.equal(result.selected, true);
      assert.equal(dragStarted, false);
      assert.equal(selected, true);
    });

    it("rejects timeline edge trim when clip is locked and prevents timing mutation", () => {
      const clip = {
        id: "clip_1",
        locked: true,
        start_time: 1.0,
        end_time: 4.0,
      };

      let selected = false;
      let trimStarted = false;

      const result = guardTimelineDrag(
        clip.locked,
        () => {
          selected = true;
        },
        () => {
          trimStarted = true;
          clip.start_time = 2.0;
        }
      );

      assert.equal(result.dragAllowed, false);
      assert.equal(result.selected, true);
      assert.equal(trimStarted, false);
      assert.equal(clip.start_time, 1.0);
    });
  });

  describe("Inspector Mutation Guards", () => {
    it("blocks position mutations when layer is locked", () => {
      const layer = { id: "l1", locked: true, transform: { x: 0.2, y: 0.3 } };
      let called = false;
      const res = guardLayerMutation(layer, () => {
        called = true;
        layer.transform.x = 0.5;
      });
      assert.equal(res, false);
      assert.equal(called, false);
      assert.equal(layer.transform.x, 0.2);
    });

    it("blocks scale mutations when layer is locked", () => {
      const layer = { id: "l1", locked: true, transform: { scale: 1.0 } };
      let called = false;
      const res = guardLayerMutation(layer, () => {
        called = true;
        layer.transform.scale = 1.8;
      });
      assert.equal(res, false);
      assert.equal(called, false);
      assert.equal(layer.transform.scale, 1.0);
    });

    it("blocks rotation mutations when layer is locked", () => {
      const layer = { id: "l1", locked: true, transform: { rotation: 0 } };
      let called = false;
      const res = guardLayerMutation(layer, () => {
        called = true;
        layer.transform.rotation = 45;
      });
      assert.equal(res, false);
      assert.equal(called, false);
      assert.equal(layer.transform.rotation, 0);
    });

    it("blocks opacity and content mutations when layer is locked", () => {
      const layer = { id: "l1", locked: true, content: { opacity: 1.0, text: "Original" } };
      let called = false;
      const res = guardLayerMutation(layer, () => {
        called = true;
        layer.content.opacity = 0.5;
        layer.content.text = "Mutated";
      });
      assert.equal(res, false);
      assert.equal(called, false);
      assert.equal(layer.content.opacity, 1.0);
      assert.equal(layer.content.text, "Original");
    });

    it("blocks timing mutations when layer is locked", () => {
      const layer = { id: "l1", locked: true, start_time: 0.0, end_time: 5.0 };
      let called = false;
      const res = guardLayerMutation(layer, () => {
        called = true;
        layer.start_time = 1.0;
        layer.end_time = 3.0;
      });
      assert.equal(res, false);
      assert.equal(called, false);
      assert.equal(layer.start_time, 0.0);
      assert.equal(layer.end_time, 5.0);
    });

    it("allows mutations when layer is unlocked", () => {
      const layer = { id: "l1", locked: false, transform: { x: 0.5 } };
      let called = false;
      const res = guardLayerMutation(layer, () => {
        called = true;
        layer.transform.x = 0.75;
      });
      assert.equal(res, true);
      assert.equal(called, true);
      assert.equal(layer.transform.x, 0.75);
    });
  });
});
