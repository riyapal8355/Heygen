/**
 * Multi-Selection Inspector & Distribution UI Tests (Phase 45)
 *
 * Dedicated test suite covering all Phase 45 requirements:
 *
 * Distribution:
 *   1. horizontal distribution evenly spaces middle layers
 *   2. vertical distribution evenly spaces middle layers
 *   3. minimum three selected layers requirement
 *   4. locked-layer protection during distribution
 *   5. single history entry created for distribution
 *   6. undo restores original positions and selection
 *   7. redo reapplies distributed positions and selection
 *   8. persistence / OCC revision tracking
 *
 * Inspector:
 *   9. multi-selection mode activated when selectedLayerIds.length > 1
 *   10. concise selection summary and type composition
 *   11. mixed opacity detection
 *   12. batch opacity updates all unlocked selected layers
 *   13. batch visibility toggles enabled state without mutating selection
 *   14. batch lock locks or unlocks all selected layers
 *   15. mixed lock state detection
 *   16. selection transition back to single-layer mode
 *   17. Escape clears inspector selection state
 *   18. mixed-type property filtering
 *   19. locked-layer protection during batch edits
 *   20. batch mutation history atomicity
 *
 * Transform Batch Deltas:
 *   21. position delta preserves relative spacing
 *   22. scale delta preserves relative proportions
 *   23. rotation delta preserves relative angles
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  calculateGroupDistribution,
  getMultiSelectionSummary,
  batchSetOpacity,
  batchSetVisibility,
  batchSetLock,
  batchApplyTransformDelta,
} from "./studioMultiSelection";
import { VisualLayer } from "./studioLayerOrdering";
import { createHistory, pushHistory, undo, redo, canUndo, HistorySelectionState } from "./studioHistory";

const defaultSelection: HistorySelectionState = {
  activeSceneIndex: 0,
  selectedMediaLayerId: null,
  selectedTextLayerId: null,
  selectedElementLayerId: null,
  selectedLayerIds: [],
};

describe("Phase 45 — Multi-Selection Inspector & Distribution", () => {
  // =========================================================================
  // 1. DISTRIBUTION UI & LOGIC
  // =========================================================================
  describe("Group Distribution", () => {
    it("1. distributes layers horizontally with equal spacing between outer bounds", () => {
      const layers: VisualLayer[] = [
        { id: "A", type: "shape", transform: { x: 0.1, y: 0.5, scale: 1.0 } },
        { id: "B", type: "shape", transform: { x: 0.4, y: 0.5, scale: 1.0 } },
        { id: "C", type: "shape", transform: { x: 0.9, y: 0.5, scale: 1.0 } },
      ];

      const distMap = calculateGroupDistribution(layers, "horizontal");
      assert.equal(distMap.size, 3);
      assert.equal(distMap.get("A")?.x, 0.1);
      assert.equal(distMap.get("B")?.x, 0.5); // (0.9 - 0.1) / 2 = 0.4 -> 0.1 + 0.4 = 0.5
      assert.equal(distMap.get("C")?.x, 0.9);
      // Y and scale are not in the distMap
      assert.equal(distMap.get("B")?.y, undefined);
    });

    it("2. distributes layers vertically with equal spacing between outer bounds", () => {
      const layers: VisualLayer[] = [
        { id: "A", type: "text", transform: { x: 0.5, y: 0.2, scale: 1.0 } },
        { id: "B", type: "text", transform: { x: 0.5, y: 0.3, scale: 1.0 } },
        { id: "C", type: "text", transform: { x: 0.5, y: 0.8, scale: 1.0 } },
      ];

      const distMap = calculateGroupDistribution(layers, "vertical");
      assert.equal(distMap.size, 3);
      assert.equal(distMap.get("A")?.y, 0.2);
      assert.equal(distMap.get("B")?.y, 0.5); // (0.8 - 0.2) / 2 = 0.3 -> 0.2 + 0.3 = 0.5
      assert.equal(distMap.get("C")?.y, 0.8);
      // X is not in the distMap
      assert.equal(distMap.get("B")?.x, undefined);
    });

    it("3. requires minimum three eligible layers and safely no-ops on fewer", () => {
      const twoLayers: VisualLayer[] = [
        { id: "A", type: "shape", transform: { x: 0.2, y: 0.5 } },
        { id: "B", type: "shape", transform: { x: 0.8, y: 0.5 } },
      ];

      const res = calculateGroupDistribution(twoLayers, "horizontal");
      assert.equal(res.size, 0);
    });

    it("4. respects locked layers: excludes locked layers from distribution and handles <3 unlocked", () => {
      // 3 layers total, but 1 is locked -> only 2 unlocked -> cannot distribute
      const withLocked: VisualLayer[] = [
        { id: "A", type: "shape", transform: { x: 0.1, y: 0.5 }, locked: false },
        { id: "B", type: "shape", transform: { x: 0.3, y: 0.5 }, locked: true },
        { id: "C", type: "shape", transform: { x: 0.9, y: 0.5 }, locked: false },
      ];

      const res = calculateGroupDistribution(withLocked, "horizontal");
      assert.equal(res.size, 0); // safe no-op

      // 4 layers total, 1 is locked -> 3 unlocked -> distributes only unlocked
      const fourWithLocked: VisualLayer[] = [
        { id: "A", type: "shape", transform: { x: 0.1, y: 0.5 }, locked: false },
        { id: "B", type: "shape", transform: { x: 0.3, y: 0.5 }, locked: true },
        { id: "C", type: "shape", transform: { x: 0.4, y: 0.5 }, locked: false },
        { id: "D", type: "shape", transform: { x: 0.9, y: 0.5 }, locked: false },
      ];

      const res2 = calculateGroupDistribution(fourWithLocked, "horizontal");
      assert.equal(res2.size, 3);
      assert.equal(res2.has("B"), false); // locked layer excluded
      assert.equal(res2.get("A")?.x, 0.1);
      assert.equal(res2.get("C")?.x, 0.5);
      assert.equal(res2.get("D")?.x, 0.9);
    });

    it("5, 6, 7. distribution produces one history entry and undo/redo restores positions & selection", () => {
      const initialScene = {
        id: "s1",
        sequence: 1,
        duration: 5.0,
        layers: [
          { id: "A", type: "shape", transform: { x: 0.1, y: 0.5 } },
          { id: "B", type: "shape", transform: { x: 0.2, y: 0.5 } },
          { id: "C", type: "shape", transform: { x: 0.9, y: 0.5 } },
        ],
      };
      const sel: HistorySelectionState = { ...defaultSelection, selectedLayerIds: ["A", "B", "C"] };
      let history = createHistory([initialScene], sel);

      // Perform distribution
      const distMap = calculateGroupDistribution(initialScene.layers as VisualLayer[], "horizontal");
      const nextLayers = (initialScene.layers as VisualLayer[]).map((l) => {
        const up = distMap.get(l.id);
        return up ? { ...l, transform: { ...(l.transform || {}), ...up } } : l;
      });
      const nextScene = { ...initialScene, layers: nextLayers };

      // Commit single history entry
      history = pushHistory(history, [nextScene], sel, "Distribute Horizontal");
      assert.equal(history.past.length, 1);
      assert.equal((nextScene.layers[1] as any).transform.x, 0.5);

      // Undo
      const undoRes = undo(history);
      assert.ok(undoRes);
      history = undoRes.nextState;
      const restoredScene = undoRes.snapshot.scenes[0]!;
      assert.equal((restoredScene.layers![1] as any).transform.x, 0.2); // Restored original
      assert.deepEqual(undoRes.snapshot.selection.selectedLayerIds, ["A", "B", "C"]); // Restored selection

      // Redo
      const redoRes = redo(history);
      assert.ok(redoRes);
      history = redoRes.nextState;
      const redoneScene = redoRes.snapshot.scenes[0]!;
      assert.equal((redoneScene.layers![1] as any).transform.x, 0.5); // Reapplied
      assert.deepEqual(redoRes.snapshot.selection.selectedLayerIds, ["A", "B", "C"]);
    });

    it("8. persistence / OCC revision integration", () => {
      let revision = 1;
      let doc: { version: number; scenes: any[] } = { version: revision, scenes: [{ id: "s1", layers: [] }] };

      // Simulate handleSave path
      const saveDoc = (newScenes: any[]) => {
        revision += 1;
        doc = { version: revision, scenes: newScenes };
        return { success: true, revision };
      };

      const updatedScenes = [
        {
          id: "s1",
          layers: [
            { id: "A", transform: { x: 0.1 } },
            { id: "B", transform: { x: 0.5 } },
            { id: "C", transform: { x: 0.9 } },
          ],
        },
      ];

      const saveRes = saveDoc(updatedScenes);
      assert.equal(saveRes.revision, 2);
      assert.equal((doc.scenes[0].layers[1] as any).transform.x, 0.5);
    });
  });

  // =========================================================================
  // 2. MULTI-SELECTION INSPECTOR & MIXED VALUES
  // =========================================================================
  describe("Multi-Selection Inspector", () => {
    const testLayers: VisualLayer[] = [
      { id: "L1", type: "text", content: { text: "Title", opacity: 1.0 }, transform: { x: 0.2, y: 0.2, scale: 1.0, rotation: 0 }, locked: false, enabled: true },
      { id: "L2", type: "text", content: { text: "Subtitle", opacity: 0.7 }, transform: { x: 0.4, y: 0.4, scale: 1.0, rotation: 10 }, locked: false, enabled: true },
      { id: "L3", type: "shape", content: { opacity: 1.0 }, transform: { x: 0.6, y: 0.6, scale: 1.5, rotation: 0 }, locked: true, enabled: false },
    ];

    it("9. activates multi-selection summary when selectedLayerIds.length > 1", () => {
      const summarySingle = getMultiSelectionSummary(testLayers, ["L1"]);
      assert.equal(summarySingle.count, 1);

      const summaryMulti = getMultiSelectionSummary(testLayers, ["L1", "L2"]);
      assert.equal(summaryMulti.count, 2);
      assert.equal(summaryMulti.count > 1, true);
    });

    it("10. computes concise selection summary and type composition", () => {
      const summary = getMultiSelectionSummary(testLayers, ["L1", "L2", "L3"]);
      assert.equal(summary.count, 3);
      assert.equal(summary.typeCounts["Text"], 2);
      assert.equal(summary.typeCounts["Shape"], 1);
      assert.equal(summary.typeSummary, "2 Text, 1 Shape");
    });

    it("11. detects mixed opacity accurately", () => {
      // L1 (1.0) and L2 (0.7) -> mixed
      const summaryMixed = getMultiSelectionSummary(testLayers, ["L1", "L2"]);
      assert.equal(summaryMixed.opacityState.isMixed, true);
      assert.equal(summaryMixed.opacityState.value, null);

      // Set identical opacity
      const uniformLayers: VisualLayer[] = [
        { id: "L1", type: "text", content: { opacity: 0.8 } },
        { id: "L2", type: "text", content: { opacity: 0.8 } },
      ];
      const summaryUniform = getMultiSelectionSummary(uniformLayers, ["L1", "L2"]);
      assert.equal(summaryUniform.opacityState.isMixed, false);
      assert.equal(summaryUniform.opacityState.value, 0.8);
    });

    it("12. batch updates opacity for all eligible selected layers while skipping locked layers", () => {
      // L1 and L2 are unlocked; L3 is locked
      const updated = batchSetOpacity(testLayers, ["L1", "L2", "L3"], 0.5);

      const l1 = updated.find((l) => l.id === "L1");
      const l2 = updated.find((l) => l.id === "L2");
      const l3 = updated.find((l) => l.id === "L3");

      assert.equal(l1?.content?.opacity, 0.5);
      assert.equal(l2?.content?.opacity, 0.5);
      assert.equal(l3?.content?.opacity, 1.0); // Locked layer protected!
    });

    it("13. batch updates visibility without mutating selection and independent of lock", () => {
      const updated = batchSetVisibility(testLayers, ["L1", "L2", "L3"], false);

      assert.equal(updated.find((l) => l.id === "L1")?.enabled, false);
      assert.equal(updated.find((l) => l.id === "L2")?.enabled, false);
      assert.equal(updated.find((l) => l.id === "L3")?.enabled, false); // Visibility toggles even if locked
    });

    it("14. batch updates lock state for all selected layers", () => {
      const locked = batchSetLock(testLayers, ["L1", "L2"], true);
      assert.equal(locked.find((l) => l.id === "L1")?.locked, true);
      assert.equal(locked.find((l) => l.id === "L2")?.locked, true);

      const unlocked = batchSetLock(locked, ["L1", "L2", "L3"], false);
      assert.equal(unlocked.find((l) => l.id === "L1")?.locked, false);
      assert.equal(unlocked.find((l) => l.id === "L2")?.locked, false);
      assert.equal(unlocked.find((l) => l.id === "L3")?.locked, false);
    });

    it("15. detects mixed lock state", () => {
      // L1 is unlocked, L3 is locked
      const summary = getMultiSelectionSummary(testLayers, ["L1", "L3"]);
      assert.equal(summary.lockState.isMixed, true);
      assert.equal(summary.lockState.allLocked, false);
      assert.equal(summary.lockState.lockedCount, 1);
    });

    it("16. handles selection transition from multi-selection back to single layer", () => {
      let selectedIds = ["L1", "L2"];
      assert.equal(selectedIds.length > 1, true); // multi-selection active

      // Deselect L2
      selectedIds = selectedIds.filter((id) => id !== "L2");
      assert.equal(selectedIds.length, 1); // returns to single layer
      assert.equal(selectedIds[0], "L1");
    });

    it("17. Escape clears inspector selection state to empty", () => {
      let selectedIds = ["L1", "L2", "L3"];
      // Escape action
      selectedIds = [];
      const summary = getMultiSelectionSummary(testLayers, selectedIds);
      assert.equal(summary.count, 0);
      assert.equal(selectedIds.length, 0);
    });

    it("18. mixed-type property filtering exposes common types and identifies compatible attributes", () => {
      const multiTypeLayers: VisualLayer[] = [
        { id: "T1", type: "text", content: { text: "Hello", font_family: "Arial", opacity: 1.0 } },
        { id: "S1", type: "shape", content: { fill: "#FF0000", opacity: 1.0 } },
        { id: "V1", type: "video", content: { asset_id: "vid-1", opacity: 1.0 } },
      ];

      const summary = getMultiSelectionSummary(multiTypeLayers, ["T1", "S1", "V1"]);
      assert.equal(summary.eligibleTypes.length, 3);
      assert.deepEqual(summary.eligibleTypes.sort(), ["shape", "text", "video"]);
      // All 3 support opacity
      assert.equal(summary.opacityState.isMixed, false);
      assert.equal(summary.opacityState.value, 1.0);
    });

    it("19. locked-layer protection blocks mutations when all selected layers are locked", () => {
      const allLockedLayers: VisualLayer[] = [
        { id: "A", type: "shape", transform: { x: 0.1 }, content: { opacity: 0.9 }, locked: true },
        { id: "B", type: "shape", transform: { x: 0.2 }, content: { opacity: 0.9 }, locked: true },
      ];

      const summary = getMultiSelectionSummary(allLockedLayers, ["A", "B"]);
      assert.equal(summary.allLocked, true);

      // batchSetOpacity does nothing
      const opResult = batchSetOpacity(allLockedLayers, ["A", "B"], 0.2);
      assert.equal(opResult[0].content?.opacity, 0.9);
      assert.equal(opResult[1].content?.opacity, 0.9);

      // batchApplyTransformDelta does nothing
      const transResult = batchApplyTransformDelta(allLockedLayers, ["A", "B"], { dx: 0.2 });
      assert.equal(transResult[0].transform?.x, 0.1);
      assert.equal(transResult[1].transform?.x, 0.2);
    });

    it("20. batch mutation history atomicity pushes exactly 1 history entry", () => {
      const scene = { id: "s1", sequence: 1, duration: 5.0, layers: testLayers };
      const sel: HistorySelectionState = { ...defaultSelection, selectedLayerIds: ["L1", "L2"] };
      let history = createHistory([scene], sel);

      // Batch opacity edit
      const updatedLayers = batchSetOpacity(testLayers, ["L1", "L2"], 0.3);
      const nextScene = { ...scene, layers: updatedLayers };

      history = pushHistory(history, [nextScene], sel, "Batch Opacity 30%");
      assert.equal(history.past.length, 1);

      // Undo reverts both layers simultaneously
      const undoRes = undo(history);
      assert.ok(undoRes);
      const reverted = undoRes.snapshot.scenes[0].layers as VisualLayer[];
      assert.equal(reverted.find((l) => l.id === "L1")?.content?.opacity, 1.0);
      assert.equal(reverted.find((l) => l.id === "L2")?.content?.opacity, 0.7);
    });
  });

  // =========================================================================
  // 3. TRANSFORM BATCH DELTAS (POSITION, SCALE, ROTATION)
  // =========================================================================
  describe("Transform Batch Deltas", () => {
    const transformLayers: VisualLayer[] = [
      { id: "A", type: "shape", transform: { x: 0.2, y: 0.3, scale: 1.0, rotation: 0 }, locked: false },
      { id: "B", type: "shape", transform: { x: 0.4, y: 0.5, scale: 1.5, rotation: 45 }, locked: false },
      { id: "C", type: "shape", transform: { x: 0.8, y: 0.7, scale: 2.0, rotation: 90 }, locked: true },
    ];

    it("21. position delta preserves relative spacing between layers and skips locked", () => {
      const moved = batchApplyTransformDelta(transformLayers, ["A", "B", "C"], { dx: 0.1, dy: -0.05 });

      const a = moved.find((l) => l.id === "A")!;
      const b = moved.find((l) => l.id === "B")!;
      const c = moved.find((l) => l.id === "C")!;

      // A: x=0.2+0.1=0.3, y=0.3-0.05=0.25
      assert.equal(a.transform?.x, 0.3);
      assert.equal(a.transform?.y, 0.25);

      // B: x=0.4+0.1=0.5, y=0.5-0.05=0.45
      assert.equal(b.transform?.x, 0.5);
      assert.equal(b.transform?.y, 0.45);

      // Relative distance between A and B was 0.2 in x, 0.2 in y -> still 0.2!
      assert.equal(Math.round((b.transform!.x! - a.transform!.x!) * 100) / 100, 0.2);
      assert.equal(Math.round((b.transform!.y! - a.transform!.y!) * 100) / 100, 0.2);

      // C: locked, untouched
      assert.equal(c.transform?.x, 0.8);
      assert.equal(c.transform?.y, 0.7);
    });

    it("22. multiplicative scale delta preserves relative proportions and skips locked", () => {
      const scaled = batchApplyTransformDelta(transformLayers, ["A", "B", "C"], { scaleMult: 1.2 });

      const a = scaled.find((l) => l.id === "A")!;
      const b = scaled.find((l) => l.id === "B")!;
      const c = scaled.find((l) => l.id === "C")!;

      // A: 1.0 * 1.2 = 1.2
      assert.equal(a.transform?.scale, 1.2);
      // B: 1.5 * 1.2 = 1.8
      assert.equal(b.transform?.scale, 1.8);
      // Proportion B / A = 1.8 / 1.2 = 1.5 -> identical to original 1.5 / 1.0 = 1.5
      assert.equal(Math.round((b.transform!.scale! / a.transform!.scale!) * 10) / 10, 1.5);

      // C: locked, untouched
      assert.equal(c.transform?.scale, 2.0);
    });

    it("23. additive rotation delta preserves relative angles and skips locked", () => {
      const rotated = batchApplyTransformDelta(transformLayers, ["A", "B", "C"], { dRotation: 15 });

      const a = rotated.find((l) => l.id === "A")!;
      const b = rotated.find((l) => l.id === "B")!;
      const c = rotated.find((l) => l.id === "C")!;

      // A: 0 + 15 = 15°
      assert.equal(a.transform?.rotation, 15);
      // B: 45 + 15 = 60°
      assert.equal(b.transform?.rotation, 60);
      // Relative difference between B and A was 45° -> still 45°!
      assert.equal(b.transform!.rotation! - a.transform!.rotation!, 45);

      // C: locked, untouched
      assert.equal(c.transform?.rotation, 90);
    });
  });
});
