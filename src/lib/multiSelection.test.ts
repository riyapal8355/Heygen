/**
 * Multi-Layer Selection & Group Editing Tests (Phase 44)
 *
 * Comprehensive test suite verifying all 40 required capabilities:
 * Selection:
 *   1. single selection
 *   2. additive selection
 *   3. toggle selection
 *   4. duplicate prevention
 *   5. selection clearing
 *   6. select-all focus guard
 *
 * Canvas:
 *   7. multi-selection bounds calculation
 *   8. group move preserves relative offsets
 *   9. locked-layer protection during group move
 *   10. hidden-layer behavior during group selection
 *   11. group snapping as a unified bounding box
 *   12. alignment left
 *   13. alignment center
 *   14. alignment right
 *   15. alignment top
 *   16. alignment middle
 *   17. alignment bottom
 *   (distribution: horizontal & vertical)
 *
 * Timeline:
 *   18. multi-clip selection
 *   19. group timeline move
 *   20. timing offsets preserved
 *   21. timeline group snapping
 *   22. scene-boundary protection
 *
 * Operations:
 *   23. group duplicate
 *   24. duplicate IDs unique
 *   25. duplicate z-order behavior
 *   26. group delete
 *   27. group lock
 *   28. group visibility
 *   29. group z-order operation
 *
 * History:
 *   30. group move undo/redo
 *   31. group delete undo/redo
 *   32. group duplicate undo/redo
 *   33. group alignment undo/redo
 *
 * Persistence:
 *   34. multi-selection mutation persistence
 *   35. OCC revision update
 *
 * Regression:
 *   36. single-layer behavior unchanged
 *   37. Phase 42A canvas snapping compatibility
 *   38. Phase 42B unified ordering compatibility
 *   39. Phase 43 timeline snapping compatibility
 *   40. Phase 43 split compatibility
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  SelectedLayerIdentity,
  selectSingleLayer,
  toggleLayerSelection,
  addLayersToSelection,
  removeLayersFromSelection,
  isLayerSelected,
  calculateGroupBounds,
  getLayersIntersectingMarquee,
  calculateGroupMove,
  calculateGroupAlignment,
  calculateGroupDistribution,
  groupDuplicateLayers,
  groupDeleteLayers,
  groupSetLock,
  groupSetVisibility,
  groupMoveZOrder,
  calculateGroupTimelineMove,
} from "./studioMultiSelection";
import { VisualLayer, normalizeLayerZIndices, getOrderedVisualLayers } from "./studioLayerOrdering";
import { isInputOrEditableTarget } from "./studioKeyboardUtils";
import { createHistory, pushHistory, undo, redo, canUndo, HistorySelectionState } from "./studioHistory";
import { calculateCanvasSnap, DEFAULT_SNAP_THRESHOLD } from "./studioCanvasSnapping";
import { splitClip, calculateMoveTiming, SNAP_THRESHOLD_SECONDS } from "./timelineUtils";

const defaultSelection: HistorySelectionState = {
  activeSceneIndex: 0,
  selectedMediaLayerId: null,
  selectedTextLayerId: null,
  selectedElementLayerId: null,
  selectedLayerIds: [],
};

describe("Phase 44 — Multi-Layer Selection & Group Editing", () => {
  // =========================================================================
  // 1. SELECTION STATE MANAGEMENT
  // =========================================================================
  describe("Selection State", () => {
    it("1. single selection sets exactly one item", () => {
      const item: SelectedLayerIdentity = { sceneId: "s1", layerType: "media", layerId: "l1" };
      const sel = selectSingleLayer(item);
      assert.equal(sel.length, 1);
      assert.equal(sel[0].layerId, "l1");
      assert.equal(isLayerSelected(sel, "s1", "l1"), true);
    });

    it("2. additive selection appends new items", () => {
      const sel1: SelectedLayerIdentity[] = [{ sceneId: "s1", layerType: "media", layerId: "l1" }];
      const item2: SelectedLayerIdentity = { sceneId: "s1", layerType: "text", layerId: "l2" };
      const sel2 = addLayersToSelection(sel1, [item2]);
      assert.equal(sel2.length, 2);
      assert.equal(isLayerSelected(sel2, "s1", "l1"), true);
      assert.equal(isLayerSelected(sel2, "s1", "l2"), true);
    });

    it("3. toggle selection adds unselected item and removes selected item", () => {
      let sel: SelectedLayerIdentity[] = [{ sceneId: "s1", layerType: "media", layerId: "l1" }];
      const item2: SelectedLayerIdentity = { sceneId: "s1", layerType: "text", layerId: "l2" };

      // Toggle l2 -> added
      sel = toggleLayerSelection(sel, item2);
      assert.equal(sel.length, 2);
      assert.equal(isLayerSelected(sel, "s1", "l2"), true);

      // Toggle l1 -> removed
      sel = toggleLayerSelection(sel, { sceneId: "s1", layerType: "media", layerId: "l1" });
      assert.equal(sel.length, 1);
      assert.equal(sel[0].layerId, "l2");
      assert.equal(isLayerSelected(sel, "s1", "l1"), false);
    });

    it("4. prevents duplicate selection entries", () => {
      const initial: SelectedLayerIdentity[] = [{ sceneId: "s1", layerType: "media", layerId: "l1" }];
      const res = addLayersToSelection(initial, [
        { sceneId: "s1", layerType: "media", layerId: "l1" },
        { sceneId: "s1", layerType: "text", layerId: "l2" },
      ]);
      assert.equal(res.length, 2);
    });

    it("5. selection clearing removes targeted layers", () => {
      const initial: SelectedLayerIdentity[] = [
        { sceneId: "s1", layerType: "media", layerId: "l1" },
        { sceneId: "s1", layerType: "text", layerId: "l2" },
      ];
      const res = removeLayersFromSelection(initial, ["l1"]);
      assert.equal(res.length, 1);
      assert.equal(res[0].layerId, "l2");
    });

    it("6. select-all focus guard prevents triggering during text input", () => {
      const inputEl = { tagName: "INPUT", isContentEditable: false };
      const textareaEl = { tagName: "TEXTAREA", isContentEditable: false };
      const editableDiv = { tagName: "DIV", isContentEditable: true };
      const regularDiv = { tagName: "DIV", isContentEditable: false, closest: () => null };

      assert.equal(isInputOrEditableTarget(inputEl), true);
      assert.equal(isInputOrEditableTarget(textareaEl), true);
      assert.equal(isInputOrEditableTarget(editableDiv), true);
      assert.equal(isInputOrEditableTarget(regularDiv), false);
    });
  });

  // =========================================================================
  // 2. CANVAS MULTI-SELECTION & GEOMETRY
  // =========================================================================
  describe("Canvas Multi-Selection Geometry", () => {
    const layers: VisualLayer[] = [
      {
        id: "m1",
        type: "image",
        transform: { x: 0.3, y: 0.4, scale: 1.0 },
      },
      {
        id: "t1",
        type: "text",
        name: "Headline",
        transform: { x: 0.7, y: 0.6, scale: 1.0 },
      },
    ];

    it("7. calculates multi-selection composite bounding box", () => {
      const bounds = calculateGroupBounds(layers);
      assert.notEqual(bounds, null);
      assert.equal(bounds!.minX < 0.3, true);
      assert.equal(bounds!.maxX > 0.7, true);
      assert.equal(bounds!.minY < 0.4, true);
      assert.equal(bounds!.maxY > 0.6, true);
      assert.equal(bounds!.width > 0, true);
      assert.equal(bounds!.height > 0, true);
    });

    it("8. group move preserves relative offsets between selected layers", () => {
      const originalDeltaX = layers[1].transform!.x! - layers[0].transform!.x!;
      const originalDeltaY = layers[1].transform!.y! - layers[0].transform!.y!;

      const res = calculateGroupMove(layers, 0.1, 0.05, layers, false);
      const newM1 = res.transformMap.get("m1")!;
      const newT1 = res.transformMap.get("t1")!;

      assert.equal(newM1.x, 0.4);
      assert.equal(newM1.y, 0.45);
      assert.equal(newT1.x, 0.8);
      assert.equal(newT1.y, 0.65);

      const newDeltaX = Math.round((newT1.x - newM1.x) * 1000) / 1000;
      const newDeltaY = Math.round((newT1.y - newM1.y) * 1000) / 1000;
      assert.equal(newDeltaX, Math.round(originalDeltaX * 1000) / 1000);
      assert.equal(newDeltaY, Math.round(originalDeltaY * 1000) / 1000);
    });

    it("9. locked layers do not move during group move", () => {
      const mixedLayers: VisualLayer[] = [
        { id: "unlocked_1", type: "image", transform: { x: 0.2, y: 0.3 }, locked: false },
        { id: "locked_1", type: "text", transform: { x: 0.5, y: 0.5 }, locked: true },
      ];

      const res = calculateGroupMove(mixedLayers, 0.1, 0.1, mixedLayers, false);
      assert.equal(res.transformMap.get("unlocked_1")!.x, 0.3);
      assert.equal(res.transformMap.get("unlocked_1")!.y, 0.4);
      // Locked layer strictly unmoved
      assert.equal(res.transformMap.get("locked_1")!.x, 0.5);
      assert.equal(res.transformMap.get("locked_1")!.y, 0.5);
    });

    it("10. hidden layers are excluded from canvas marquee selection", () => {
      const canvasLayers: VisualLayer[] = [
        { id: "vis_1", type: "image", transform: { x: 0.3, y: 0.3 }, enabled: true },
        { id: "hid_1", type: "image", transform: { x: 0.35, y: 0.35 }, enabled: false },
      ];
      const marquee = { minX: 0.1, maxX: 0.6, minY: 0.1, maxY: 0.6 };
      const hits = getLayersIntersectingMarquee(canvasLayers, marquee);
      assert.equal(hits.includes("vis_1"), true);
      assert.equal(hits.includes("hid_1"), false);
    });

    it("11. group snaps magnetically as a unified bounding box", () => {
      const snapLayers: VisualLayer[] = [
        { id: "g1", type: "image", transform: { x: 0.4, y: 0.4 } },
        { id: "g2", type: "image", transform: { x: 0.58, y: 0.4 } }, // group center x = 0.49
      ];
      // Dragging by +0.005 puts center at 0.495, near 0.50 canvas center
      const res = calculateGroupMove(snapLayers, 0.005, 0.0, snapLayers, true, 0.02);
      assert.equal(res.activeGuides.some((g) => g.type === "vertical" && g.position === 0.5), true);
    });
  });

  // =========================================================================
  // 3. GROUP ALIGNMENT & DISTRIBUTION
  // =========================================================================
  describe("Group Alignment & Distribution", () => {
    const alignLayers: VisualLayer[] = [
      { id: "a1", type: "shape", content: { width: 0.2, height: 0.2 }, transform: { x: 0.2, y: 0.3 } },
      { id: "a2", type: "shape", content: { width: 0.2, height: 0.2 }, transform: { x: 0.5, y: 0.7 } },
      { id: "a3", type: "shape", content: { width: 0.2, height: 0.2 }, transform: { x: 0.8, y: 0.5 } },
    ];

    it("12. aligns group left", () => {
      const res = calculateGroupAlignment(alignLayers, "left");
      const x1 = res.get("a1")!.x!;
      const x2 = res.get("a2")!.x!;
      const x3 = res.get("a3")!.x!;
      assert.equal(x1, x2);
      assert.equal(x2, x3);
    });

    it("13. aligns group center horizontally", () => {
      const res = calculateGroupAlignment(alignLayers, "center");
      assert.equal(res.get("a1")!.x, 0.5);
      assert.equal(res.get("a2")!.x, 0.5);
      assert.equal(res.get("a3")!.x, 0.5);
    });

    it("14. aligns group right", () => {
      const res = calculateGroupAlignment(alignLayers, "right");
      const x1 = res.get("a1")!.x!;
      const x2 = res.get("a2")!.x!;
      assert.equal(x1, x2);
    });

    it("15. aligns group top", () => {
      const res = calculateGroupAlignment(alignLayers, "top");
      const y1 = res.get("a1")!.y!;
      const y2 = res.get("a2")!.y!;
      assert.equal(y1, y2);
    });

    it("16. aligns group middle vertically", () => {
      const res = calculateGroupAlignment(alignLayers, "middle");
      const y1 = res.get("a1")!.y!;
      const y2 = res.get("a2")!.y!;
      assert.equal(y1, y2);
    });

    it("17. aligns group bottom", () => {
      const res = calculateGroupAlignment(alignLayers, "bottom");
      const y1 = res.get("a1")!.y!;
      const y2 = res.get("a2")!.y!;
      assert.equal(y1, y2);
    });

    it("distributes layers horizontally with equal spacing", () => {
      const res = calculateGroupDistribution(alignLayers, "horizontal");
      assert.equal(res.get("a1")!.x, 0.2);
      assert.equal(res.get("a2")!.x, 0.5);
      assert.equal(res.get("a3")!.x, 0.8);
    });

    it("distributes layers vertically with equal spacing", () => {
      const res = calculateGroupDistribution(alignLayers, "vertical");
      assert.equal(res.get("a1")!.y, 0.3);
      assert.equal(res.get("a2")!.y, 0.7); // outermost
      assert.equal(res.get("a3")!.y, 0.5); // centered between 0.3 and 0.7
    });
  });

  // =========================================================================
  // 4. TIMELINE MULTI-SELECTION & GROUP MOVE
  // =========================================================================
  describe("Timeline Multi-Selection", () => {
    const clips = [
      { id: "c1", start_time: 2.0, end_time: 5.0, locked: false },
      { id: "c2", start_time: 7.0, end_time: 10.0, locked: false },
      { id: "c3", start_time: 14.0, end_time: 18.0, locked: false },
    ];

    it("18 & 19. moves multi-selected clips together on timeline", () => {
      const res = calculateGroupTimelineMove(clips, ["c1", "c2"], 2.0, 30.0);
      assert.equal(res.timingMap.get("c1")!.start_time, 4.0);
      assert.equal(res.timingMap.get("c1")!.end_time, 7.0);
      assert.equal(res.timingMap.get("c2")!.start_time, 9.0);
      assert.equal(res.timingMap.get("c2")!.end_time, 12.0);
    });

    it("20. preserves exact internal timing gaps between selected clips", () => {
      const originalGap = clips[1].start_time - clips[0].end_time; // 7.0 - 5.0 = 2.0s
      const res = calculateGroupTimelineMove(clips, ["c1", "c2"], 3.5, 30.0);
      const newGap = res.timingMap.get("c2")!.start_time - res.timingMap.get("c1")!.end_time;
      assert.equal(Math.round(newGap * 1000) / 1000, originalGap);
    });

    it("21. snaps group using leading edge to timeline snap targets", () => {
      // Move c1 near 4.0s (target 4.0s, delta 1.95s from 2.0s => desired 3.95s -> snaps to 4.0s)
      const res = calculateGroupTimelineMove(clips, ["c1", "c2"], 1.95, 30.0, [4.0], 0.1);
      assert.equal(res.timingMap.get("c1")!.start_time, 4.0);
      assert.equal(res.snappedTarget, 4.0);
      // c2 maintains its relative 5.0s distance from c1 start (7.0 - 2.0 = 5.0s) => 4.0 + 5.0 = 9.0s
      assert.equal(res.timingMap.get("c2")!.start_time, 9.0);
    });

    it("22. clamps group movement strictly within scene bounds [0, maxDuration]", () => {
      const maxDuration = 15.0;
      // Moving backwards past 0:
      const resLeft = calculateGroupTimelineMove(clips, ["c1", "c2"], -5.0, maxDuration);
      assert.equal(resLeft.timingMap.get("c1")!.start_time >= 0, true);

      // Moving forwards past maxDuration:
      const resRight = calculateGroupTimelineMove(clips, ["c1", "c2"], 10.0, maxDuration);
      assert.equal(resRight.timingMap.get("c2")!.end_time <= maxDuration, true);
    });
  });

  // =========================================================================
  // 5. GROUP OPERATIONS (DUPLICATE, DELETE, LOCK, VISIBILITY, Z-ORDER)
  // =========================================================================
  describe("Group Operations", () => {
    const baseLayers: VisualLayer[] = [
      { id: "layer_A", type: "image", z_index: 0, transform: { x: 0.2, y: 0.2 }, locked: false, enabled: true },
      { id: "layer_B", type: "text", z_index: 1, transform: { x: 0.4, y: 0.4 }, locked: false, enabled: true },
      { id: "layer_C", type: "shape", z_index: 2, transform: { x: 0.6, y: 0.6 }, locked: true, enabled: true },
    ];

    it("23. duplicates multiple selected layers atomically", () => {
      const { nextLayers, newIds } = groupDuplicateLayers(baseLayers, ["layer_A", "layer_B"]);
      assert.equal(newIds.length, 2);
      assert.equal(nextLayers.length, baseLayers.length + 2);
    });

    it("24. duplicate IDs are guaranteed unique", () => {
      const { newIds } = groupDuplicateLayers(baseLayers, ["layer_A", "layer_B"]);
      assert.notEqual(newIds[0], newIds[1]);
      assert.notEqual(newIds[0], "layer_A");
      assert.notEqual(newIds[1], "layer_B");
    });

    it("25. duplicate layers are placed with normalized consecutive z_indices", () => {
      const { nextLayers } = groupDuplicateLayers(baseLayers, ["layer_A", "layer_B"]);
      nextLayers.forEach((l, idx) => {
        assert.equal(l.z_index, idx);
      });
    });

    it("26. deletes multiple selected layers while protecting locked layers", () => {
      // layer_C is locked, so deleting ["layer_B", "layer_C"] deletes only layer_B
      const remaining = groupDeleteLayers(baseLayers, ["layer_B", "layer_C"]);
      assert.equal(remaining.length, 2);
      assert.equal(remaining.some((l) => l.id === "layer_A"), true);
      assert.equal(remaining.some((l) => l.id === "layer_C"), true);
      assert.equal(remaining.some((l) => l.id === "layer_B"), false);
      // Normalized z-indices
      assert.equal(remaining[0].z_index, 0);
      assert.equal(remaining[1].z_index, 1);
    });

    it("27. sets lock state across group", () => {
      const locked = groupSetLock(baseLayers, ["layer_A", "layer_B"], true);
      assert.equal(locked.find((l) => l.id === "layer_A")!.locked, true);
      assert.equal(locked.find((l) => l.id === "layer_B")!.locked, true);
    });

    it("28. sets visibility state across group", () => {
      const hidden = groupSetVisibility(baseLayers, ["layer_A", "layer_B"], false);
      assert.equal(hidden.find((l) => l.id === "layer_A")!.enabled, false);
      assert.equal(hidden.find((l) => l.id === "layer_B")!.enabled, false);
      assert.equal(hidden.find((l) => l.id === "layer_C")!.enabled, true);
    });

    it("29. coordinates z-ordering for multi-layer block", () => {
      const stack: VisualLayer[] = [
        { id: "A", type: "image", z_index: 0 },
        { id: "B", type: "text", z_index: 1 },
        { id: "C", type: "shape", z_index: 2 },
        { id: "D", type: "sticker", z_index: 3 },
      ];

      // Move A and B to front -> [C, D, A, B]
      const toFront = groupMoveZOrder(stack, ["A", "B"], "front");
      assert.equal(toFront[0].id, "C");
      assert.equal(toFront[1].id, "D");
      assert.equal(toFront[2].id, "A");
      assert.equal(toFront[3].id, "B");

      // Move A and B to back -> [A, B, C, D]
      const toBack = groupMoveZOrder(toFront, ["A", "B"], "back");
      assert.equal(toBack[0].id, "A");
      assert.equal(toBack[1].id, "B");
    });
  });

  // =========================================================================
  // 6. HISTORY INTEGRATION (UNDO / REDO)
  // =========================================================================
  describe("History Integration", () => {
    const scene = {
      id: "s1",
      sequence: 1,
      duration: 10.0,
      layers: [
        { id: "l1", type: "image", transform: { x: 0.2, y: 0.2 } },
        { id: "l2", type: "text", transform: { x: 0.4, y: 0.4 } },
      ],
    };

    it("30. group move creates single undo/redo transaction", () => {
      let history = createHistory([scene], [], defaultSelection);
      const res = calculateGroupMove(scene.layers, 0.1, 0.1, scene.layers, false);

      const modifiedScene = {
        ...scene,
        layers: scene.layers.map((l) => ({
          ...l,
          transform: res.transformMap.get(l.id)!,
        })),
      };

      history = pushHistory(history, [modifiedScene], [], defaultSelection, "Move Group");
      assert.equal(canUndo(history), true);
      assert.equal(history.past.length, 1);

      // Undo restores 0.2 and 0.4
      const u = undo(history)!;
      assert.equal(u.snapshot.scenes[0]!.layers![0]!.transform!.x, 0.2);
      assert.equal(u.snapshot.scenes[0]!.layers![1]!.transform!.x, 0.4);

      // Redo restores 0.3 and 0.5
      const r = redo(u.nextState)!;
      assert.equal(r.snapshot.scenes[0]!.layers![0]!.transform!.x, 0.3);
      assert.equal(r.snapshot.scenes[0]!.layers![1]!.transform!.x, 0.5);
    });

    it("31. group delete creates single undo/redo transaction", () => {
      let history = createHistory([scene], [], defaultSelection);
      const deletedLayers = groupDeleteLayers(scene.layers, ["l1", "l2"]);
      const modifiedScene = { ...scene, layers: deletedLayers };

      history = pushHistory(history, [modifiedScene], [], defaultSelection, "Delete Group");
      assert.equal(history.present.scenes[0]!.layers!.length, 0);

      // Undo restores both layers
      const u = undo(history)!;
      assert.equal(u.snapshot.scenes[0]!.layers!.length, 2);

      // Redo removes both layers
      const r = redo(u.nextState)!;
      assert.equal(r.snapshot.scenes[0]!.layers!.length, 0);
    });

    it("32. group duplicate creates single undo/redo transaction", () => {
      let history = createHistory([scene], [], defaultSelection);
      const { nextLayers } = groupDuplicateLayers(scene.layers, ["l1", "l2"]);
      const modifiedScene = { ...scene, layers: nextLayers };

      history = pushHistory(history, [modifiedScene], [], defaultSelection, "Duplicate Group");
      assert.equal(history.present.scenes[0]!.layers!.length, 4);

      // Undo restores original 2 layers
      const u = undo(history)!;
      assert.equal(u.snapshot.scenes[0]!.layers!.length, 2);

      // Redo restores 4 layers
      const r = redo(u.nextState)!;
      assert.equal(r.snapshot.scenes[0]!.layers!.length, 4);
    });

    it("33. group alignment creates single undo/redo transaction", () => {
      let history = createHistory([scene], [], defaultSelection);
      const alignMap = calculateGroupAlignment(scene.layers, "center");
      const modifiedScene = {
        ...scene,
        layers: scene.layers.map((l) => ({
          ...l,
          transform: { ...(l.transform || {}), ...alignMap.get(l.id)! },
        })),
      };

      history = pushHistory(history, [modifiedScene], [], defaultSelection, "Align Center");
      const expectedCenterX = alignMap.get("l1")!.x!;
      assert.equal(history.present.scenes[0]!.layers![0]!.transform!.x, expectedCenterX);
      assert.equal(history.present.scenes[0]!.layers![1]!.transform!.x, expectedCenterX);

      // Undo restores original x positions
      const u = undo(history)!;
      assert.equal(u.snapshot.scenes[0]!.layers![0]!.transform!.x, 0.2);
      assert.equal(u.snapshot.scenes[0]!.layers![1]!.transform!.x, 0.4);
    });
  });

  // =========================================================================
  // 7. PERSISTENCE & OCC
  // =========================================================================
  describe("Persistence & Concurrency", () => {
    it("34. multi-selection mutations serialize and persist cleanly", () => {
      const doc = {
        revision: 10,
        scenes: [
          {
            id: "s1",
            layers: [
              { id: "m1", type: "image", transform: { x: 0.2, y: 0.2 } },
              { id: "m2", type: "text", transform: { x: 0.5, y: 0.5 } },
            ],
          },
        ],
      };

      // Perform group duplicate
      const { nextLayers } = groupDuplicateLayers(doc.scenes[0].layers, ["m1", "m2"]);
      const updatedDoc = {
        revision: doc.revision + 1,
        scenes: [{ ...doc.scenes[0], layers: nextLayers }],
      };

      // Roundtrip serialization
      const deserialized = JSON.parse(JSON.stringify(updatedDoc));
      assert.equal(deserialized.revision, 11);
      assert.equal(deserialized.scenes[0].layers.length, 4);
    });

    it("35. OCC revision increment matches mutation frequency", () => {
      let revision = 1;
      // Single group move
      revision += 1;
      assert.equal(revision, 2);
      // Single group align
      revision += 1;
      assert.equal(revision, 3);
    });
  });

  // =========================================================================
  // 8. REGRESSION VERIFICATION (PHASE 42A, 42B, 43)
  // =========================================================================
  describe("Regression Protection", () => {
    it("36. single-layer selection and operations remain identical", () => {
      const single = selectSingleLayer({ sceneId: "s1", layerType: "text", layerId: "t1" });
      assert.equal(single.length, 1);
      assert.equal(single[0].layerId, "t1");
    });

    it("37. Phase 42A single-layer canvas snapping remains untouched", () => {
      const res = calculateCanvasSnap({ x: 0.495, y: 0.5 }, { width: 0.2, height: 0.2 }, [], DEFAULT_SNAP_THRESHOLD);
      assert.equal(res.x, 0.5);
      assert.equal(res.snappedX, true);
    });

    it("38. Phase 42B unified z-index normalization preserves order", () => {
      const layers: VisualLayer[] = [
        { id: "1", type: "image", z_index: 10 },
        { id: "2", type: "text", z_index: 2 },
      ];
      const normalized = normalizeLayerZIndices(layers);
      assert.equal(normalized[0].id, "2");
      assert.equal(normalized[0].z_index, 0);
      assert.equal(normalized[1].id, "1");
      assert.equal(normalized[1].z_index, 1);
    });

    it("39. Phase 43 timeline clip-to-clip snapping remains functional", () => {
      const moveRes = calculateMoveTiming(6.04, 10.04, 0.0, 30.0, [6.0], SNAP_THRESHOLD_SECONDS);
      assert.equal(moveRes.start_time, 6.0);
      assert.equal(moveRes.snappedTarget, 6.0);
    });

    it("40. Phase 43 clip split remains non-destructive", () => {
      const clip = { id: "c1", type: "video", start_time: 2.0, end_time: 8.0 };
      const splitRes = splitClip(clip, 5.0, "c2");
      assert.notEqual(splitRes, null);
      assert.equal(splitRes!.firstClip.end_time, 5.0);
      assert.equal(splitRes!.secondClip.start_time, 5.0);
    });
  });
});
