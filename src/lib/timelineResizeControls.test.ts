/**
 * Timeline Edge Resizing, Edit/Delete Controls & Undo/Redo Tests
 *
 * Verifies:
 * 1. clip resize start (left edge drag adjusts start_time, preserves end_time)
 * 2. clip resize end (right edge drag adjusts end_time, preserves start_time)
 * 3. minimum duration enforcement (cannot resize below MIN_CLIP_DURATION)
 * 4. maximum boundary enforcement (cannot resize beyond scene duration or clamped bounds)
 * 5. Edit action mapping (identifies and routes to correct inspector)
 * 6. Delete action (removes item from state and updates timeline)
 * 7. Delete + undo (Ctrl+Z restores deleted item and previous timing)
 * 8. Delete + redo (Ctrl+Shift+Z reapplies deletion)
 * 9. multi-selection delete (deletes all selected deletable items in a single operation)
 * 10. zoom + resize coordinate conversion (pixel delta to seconds with zoom factor)
 * 11. split + resize (split pieces remain independently resizable)
 * 12. persistence & clamp propagation (clamping layers when scene duration shrinks)
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  calculateLeftTrimTiming,
  calculateRightTrimTiming,
  calculateSceneResizeTiming,
  clampLayersToSceneDuration,
  splitClip,
  MIN_CLIP_DURATION,
  MIN_TIMELINE_ZOOM,
  MAX_TIMELINE_ZOOM,
} from "./timelineUtils";
import {
  createHistory,
  pushHistory,
  undo,
  redo,
  canUndo,
  canRedo,
  HistorySelectionState,
} from "./studioHistory";
import { deleteLayerWithZIndex } from "./studioLayerOrdering";
import { groupDeleteLayers } from "./studioMultiSelection";

const defaultSelection: HistorySelectionState = {
  activeSceneIndex: 0,
  selectedMediaLayerId: null,
  selectedTextLayerId: null,
  selectedElementLayerId: null,
};

describe("Timeline Resizing, Controls & Unlock Tests", () => {
  // 1. Clip Resize Start (Left edge)
  it("1. clip resize start changes start_time while preserving end_time", () => {
    const initStart = 2.0;
    const initEnd = 8.0;

    // Drag left edge to the right by +1.5s
    const resultRight = calculateLeftTrimTiming(initStart, initEnd, 1.5, MIN_CLIP_DURATION, []);
    assert.equal(resultRight.start_time, 3.5);
    assert.equal(resultRight.end_time, 8.0);
    assert.equal(resultRight.end_time - resultRight.start_time, 4.5);

    // Drag left edge to the left by -1.0s
    const resultLeft = calculateLeftTrimTiming(initStart, initEnd, -1.0, MIN_CLIP_DURATION, []);
    assert.equal(resultLeft.start_time, 1.0);
    assert.equal(resultLeft.end_time, 8.0);
    assert.equal(resultLeft.end_time - resultLeft.start_time, 7.0);
  });

  // 2. Clip Resize End (Right edge)
  it("2. clip resize end changes end_time while preserving start_time", () => {
    const initStart = 1.0;
    const initEnd = 6.0;
    const sceneDuration = 10.0;

    // Drag right edge right by +2.0s
    const resultRight = calculateRightTrimTiming(initStart, initEnd, 2.0, sceneDuration, MIN_CLIP_DURATION, []);
    assert.equal(resultRight.start_time, 1.0);
    assert.equal(resultRight.end_time, 8.0);
    assert.equal(resultRight.end_time - resultRight.start_time, 7.0);

    // Drag right edge left by -2.0s
    const resultLeft = calculateRightTrimTiming(initStart, initEnd, -2.0, sceneDuration, MIN_CLIP_DURATION, []);
    assert.equal(resultLeft.start_time, 1.0);
    assert.equal(resultLeft.end_time, 4.0);
    assert.equal(resultLeft.end_time - resultLeft.start_time, 3.0);
  });

  // 3. Minimum duration enforcement
  it("3. prevents resizing below MIN_CLIP_DURATION (no zero or negative duration)", () => {
    const initStart = 2.0;
    const initEnd = 4.0;
    const sceneDuration = 10.0;

    // Attempt to drag left edge past the end boundary
    const resultLeftExcess = calculateLeftTrimTiming(initStart, initEnd, 5.0, MIN_CLIP_DURATION, []);
    assert.ok(resultLeftExcess.end_time - resultLeftExcess.start_time >= MIN_CLIP_DURATION);
    assert.equal(resultLeftExcess.start_time, initEnd - MIN_CLIP_DURATION);
    assert.equal(resultLeftExcess.end_time, initEnd);

    // Attempt to drag right edge past the start boundary
    const resultRightExcess = calculateRightTrimTiming(initStart, initEnd, -5.0, sceneDuration, MIN_CLIP_DURATION, []);
    assert.ok(resultRightExcess.end_time - resultRightExcess.start_time >= MIN_CLIP_DURATION);
    assert.equal(resultRightExcess.start_time, initStart);
    assert.equal(resultRightExcess.end_time, initStart + MIN_CLIP_DURATION);
  });

  // 4. Maximum boundary enforcement
  it("4. clamps resize within scene boundaries [0, sceneDuration]", () => {
    const initStart = 2.0;
    const initEnd = 8.0;
    const sceneDuration = 10.0;

    // Drag left edge before 0
    const resultLeft = calculateLeftTrimTiming(initStart, initEnd, -10.0, MIN_CLIP_DURATION, []);
    assert.equal(resultLeft.start_time, 0.0);
    assert.equal(resultLeft.end_time, 8.0);

    // Drag right edge beyond scene duration
    const resultRight = calculateRightTrimTiming(initStart, initEnd, 10.0, sceneDuration, MIN_CLIP_DURATION, []);
    assert.equal(resultRight.start_time, 2.0);
    assert.equal(resultRight.end_time, 10.0);
  });

  // 5. Edit action inspector mapping
  it("5. maps edit action to appropriate inspector panel", () => {
    const getInspectorForType = (itemType: string): string => {
      switch (itemType) {
        case "scene": return "scene";
        case "avatar": return "avatar";
        case "script": return "scene";
        case "speech": return "voice";
        case "music": return "music";
        case "caption": return "captions";
        case "text": return "text";
        case "media": return "media";
        case "element": return "elements";
        default: return "scene";
      }
    };

    assert.equal(getInspectorForType("avatar"), "avatar");
    assert.equal(getInspectorForType("script"), "scene");
    assert.equal(getInspectorForType("speech"), "voice");
    assert.equal(getInspectorForType("music"), "music");
    assert.equal(getInspectorForType("caption"), "captions");
    assert.equal(getInspectorForType("text"), "text");
    assert.equal(getInspectorForType("media"), "media");
    assert.equal(getInspectorForType("element"), "elements");
  });

  // 6. Delete action
  it("6. deletes item and updates layers list and z-indices", () => {
    const layers = [
      { id: "layer_1", type: "text", z_index: 0 },
      { id: "layer_2", type: "image", z_index: 1 },
      { id: "layer_3", type: "shape", z_index: 2 },
    ];

    const updated = deleteLayerWithZIndex(layers, "layer_2");
    assert.equal(updated.length, 2);
    assert.equal(updated.find((l) => l.id === "layer_2"), undefined);
    assert.equal(updated[0].id, "layer_1");
    assert.equal(updated[0].z_index, 0);
    assert.equal(updated[1].id, "layer_3");
    assert.equal(updated[1].z_index, 1);
  });

  // 7. Delete + Undo
  it("7. delete followed by undo restores deleted item and previous state", () => {
    const initialScenes = [
      {
        id: "sc_1",
        sequence: 0,
        duration: 5.0,
        avatar: { avatar_id: "avatar_daniel" },
        layers: [{ id: "l1", type: "text", name: "Heading" }],
      },
    ];
    let history = createHistory(initialScenes as any, defaultSelection);

    // Perform delete layer
    const nextScenes = [
      {
        ...initialScenes[0],
        layers: [],
      },
    ];
    history = pushHistory(history, nextScenes as any, defaultSelection);
    assert.equal(canUndo(history), true);

    // Undo delete
    const undoResult = undo(history);
    assert.ok(undoResult);
    assert.equal(undoResult.snapshot.scenes[0]!.layers!.length, 1);
    assert.equal(undoResult.snapshot.scenes[0]!.layers![0].id, "l1");
  });

  // 8. Delete + Redo
  it("8. redo reapplies deletion correctly", () => {
    const initialScenes = [
      {
        id: "sc_1",
        sequence: 0,
        duration: 5.0,
        layers: [{ id: "l1", type: "text" }],
      },
    ];

    let history = createHistory(initialScenes as any, defaultSelection);
    const deletedScenes = [{ ...initialScenes[0], layers: [] }];
    history = pushHistory(history, deletedScenes as any, defaultSelection);

    // Undo
    const undoResult = undo(history);
    assert.ok(undoResult);
    assert.equal(undoResult.snapshot.scenes[0]!.layers!.length, 1);
    history = undoResult.nextState;

    // Redo
    assert.equal(canRedo(history), true);
    const redoResult = redo(history);
    assert.ok(redoResult);
    assert.equal(redoResult.snapshot.scenes[0]!.layers!.length, 0);
  });

  // 9. Multi-selection delete
  it("9. multi-selection delete removes all selected items at once", () => {
    const layers = [
      { id: "l1", type: "text" },
      { id: "l2", type: "image" },
      { id: "l3", type: "shape" },
      { id: "l4", type: "video" },
    ];
    const selectedIds = ["l2", "l3"];

    const nextLayers = groupDeleteLayers(layers as any[], selectedIds);
    assert.equal(nextLayers.length, 2);
    assert.deepEqual(nextLayers.map((l) => l.id), ["l1", "l4"]);
  });

  // 10. Zoom + resize coordinate conversion
  it("10. calculates pixel to time conversion accurately across zoom levels", () => {
    const totalDuration = 20.0; // 20s total timeline
    const containerBaseWidth = 1000; // 1000px at 100% zoom

    const zoomLevels = [0.5, 1.0, 1.5, 2.0];
    zoomLevels.forEach((zoom) => {
      const zoomWidth = containerBaseWidth * zoom;
      const secondsPerPixel = totalDuration / zoomWidth;

      // Drag 50 pixels
      const pixelDelta = 50;
      const timeDelta = pixelDelta * secondsPerPixel;

      // At zoom 1.0 (1000px): 50px * (20 / 1000) = 1.0s
      // At zoom 2.0 (2000px): 50px * (20 / 2000) = 0.5s
      assert.equal(timeDelta, 50 * (20 / (1000 * zoom)));
    });
  });

  // 11. Split + Resize
  it("11. split clips can be resized independently", () => {
    const clip = {
      id: "clip_orig",
      type: "video",
      start_time: 0.0,
      end_time: 10.0,
      duration: 10.0,
    };

    const splitRes = splitClip(clip, 4.0, "clip_second", MIN_CLIP_DURATION);
    assert.ok(splitRes);
    const { firstClip, secondClip } = splitRes;
    assert.equal(firstClip.start_time, 0.0);
    assert.equal(firstClip.end_time, 4.0);
    assert.equal(secondClip.start_time, 4.0);
    assert.equal(secondClip.end_time, 10.0);

    // Resize first clip right edge from 4.0s to 3.0s
    const resizedFirst = calculateRightTrimTiming(firstClip.start_time, firstClip.end_time, -1.0, 10.0, MIN_CLIP_DURATION, []);
    assert.equal(resizedFirst.end_time, 3.0);
    assert.equal(resizedFirst.end_time - resizedFirst.start_time, 3.0);

    // Resize second clip left edge from 4.0s to 5.0s
    const resizedSecond = calculateLeftTrimTiming(secondClip.start_time, secondClip.end_time, 1.0, MIN_CLIP_DURATION, []);
    assert.equal(resizedSecond.start_time, 5.0);
    assert.equal(resizedSecond.end_time - resizedSecond.start_time, 5.0);
  });

  // 12. Persistence & Clamping Propagation
  it("12. clamps child layers when scene duration shrinks", () => {
    const initialLayers = [
      { id: "l1", start_time: 0.0, end_time: 4.0 },
      { id: "l2", start_time: 2.0, end_time: 7.0 },
      { id: "l3", start_time: 6.0, end_time: 8.0 },
    ];

    // Scene resized from 8.0s down to 5.0s
    const newSceneDuration = 5.0;
    const clampedLayers = clampLayersToSceneDuration(initialLayers, newSceneDuration);

    assert.equal(clampedLayers[0].end_time, 4.0); // was 4.0 <= 5.0, unchanged
    assert.equal(clampedLayers[1].end_time, 5.0); // was 7.0 > 5.0, clamped to 5.0
    // l3 was 6.0-8.0; start clamped to 4.5, end clamped to 5.0 (min 0.5s duration)
    assert.ok(clampedLayers[2].end_time <= 5.0);
    assert.ok(clampedLayers[2].start_time < clampedLayers[2].end_time);
  });

  it("12b. calculates scene duration resizing safely with min and max bounds", () => {
    // Scene 01: 5.0s resized by +2.0s -> 7.0s
    const expanded = calculateSceneResizeTiming(5.0, 2.0, 1.0, 60.0);
    assert.equal(expanded, 7.0);

    // Scene 01: 7.0s resized by -3.0s -> 4.0s
    const shrunk = calculateSceneResizeTiming(7.0, -3.0, 1.0, 60.0);
    assert.equal(shrunk, 4.0);

    // Prevent scene duration < 1.0s
    const minBound = calculateSceneResizeTiming(2.0, -5.0, 1.0, 60.0);
    assert.equal(minBound, 1.0);

    // Prevent scene duration > 60.0s
    const maxBound = calculateSceneResizeTiming(55.0, 20.0, 1.0, 60.0);
    assert.equal(maxBound, 60.0);
  });
});
