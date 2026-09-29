import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  bringLayerForward,
  bringLayerToFront,
  deleteLayerWithZIndex,
  deriveUnifiedVisualLayers,
  distributeUnifiedVisualLayers,
  duplicateLayerWithZIndex,
  getOrderedVisualLayers,
  moveLayerToIndex,
  normalizeLayerZIndices,
  sendLayerBackward,
  sendLayerToBack,
  VisualLayer,
} from "./studioLayerOrdering";

describe("Studio Unified Cross-Type Layer Ordering (Phase 42B)", () => {
  describe("1. Normalization & Sorting", () => {
    it("normalizes sparse z-indices into consecutive integers [0..N-1]", () => {
      const layers: VisualLayer[] = [
        { id: "l1", type: "media", z_index: 10 },
        { id: "l2", type: "text", z_index: 500 },
        { id: "l3", type: "shape", z_index: 9999 },
      ];
      const normalized = normalizeLayerZIndices(layers);
      assert.deepEqual(
        normalized.map((l) => ({ id: l.id, z: l.z_index })),
        [
          { id: "l1", z: 0 },
          { id: "l2", z: 1 },
          { id: "l3", z: 2 },
        ]
      );
    });

    it("normalizes negative and mixed z-indices accurately", () => {
      const layers: VisualLayer[] = [
        { id: "l1", type: "shape", z_index: 15 },
        { id: "l2", type: "media", z_index: -20 },
        { id: "l3", type: "text", z_index: 0 },
      ];
      const normalized = normalizeLayerZIndices(layers);
      assert.deepEqual(
        normalized.map((l) => ({ id: l.id, z: l.z_index })),
        [
          { id: "l2", z: 0 },
          { id: "l3", z: 1 },
          { id: "l1", z: 2 },
        ]
      );
    });

    it("handles legacy layers with missing z_index deterministically", () => {
      const layers: VisualLayer[] = [
        { id: "m1", type: "media" },
        { id: "t1", type: "text" },
        { id: "s1", type: "shape" },
      ];
      const normalized = normalizeLayerZIndices(layers);
      assert.deepEqual(
        normalized.map((l) => ({ id: l.id, z: l.z_index })),
        [
          { id: "m1", z: 0 },
          { id: "t1", z: 1 },
          { id: "s1", z: 2 },
        ]
      );
    });

    it("breaks ties between duplicate z-indices using stable array index", () => {
      const layers: VisualLayer[] = [
        { id: "a", type: "media", z_index: 5 },
        { id: "b", type: "text", z_index: 5 },
        { id: "c", type: "shape", z_index: 5 },
      ];
      const normalized = normalizeLayerZIndices(layers);
      assert.deepEqual(
        normalized.map((l) => ({ id: l.id, z: l.z_index })),
        [
          { id: "a", z: 0 },
          { id: "b", z: 1 },
          { id: "c", z: 2 },
        ]
      );
    });

    it("sorts mixed layer types ascending by z_index", () => {
      const layers: VisualLayer[] = [
        { id: "txt1", type: "text", z_index: 3 },
        { id: "med1", type: "media", z_index: 0 },
        { id: "stk1", type: "sticker", z_index: 2 },
        { id: "shp1", type: "shape", z_index: 1 },
      ];
      const ordered = getOrderedVisualLayers(layers);
      assert.deepEqual(
        ordered.map((l) => l.id),
        ["med1", "shp1", "stk1", "txt1"]
      );
    });
  });

  describe("2. Bring Forward & Send Backward", () => {
    const baseLayers: VisualLayer[] = [
      { id: "A", type: "media", z_index: 0 },
      { id: "B", type: "text", z_index: 1 },
      { id: "C", type: "shape", z_index: 2 },
      { id: "D", type: "sticker", z_index: 3 },
    ];

    it("bringLayerForward swaps target with layer at index + 1", () => {
      const result = bringLayerForward(baseLayers, "B");
      assert.deepEqual(
        result.map((l) => ({ id: l.id, z: l.z_index })),
        [
          { id: "A", z: 0 },
          { id: "C", z: 1 },
          { id: "B", z: 2 },
          { id: "D", z: 3 },
        ]
      );
    });

    it("bringLayerForward leaves frontmost layer unchanged", () => {
      const result = bringLayerForward(baseLayers, "D");
      assert.deepEqual(
        result.map((l) => ({ id: l.id, z: l.z_index })),
        [
          { id: "A", z: 0 },
          { id: "B", z: 1 },
          { id: "C", z: 2 },
          { id: "D", z: 3 },
        ]
      );
    });

    it("sendLayerBackward swaps target with layer at index - 1", () => {
      const result = sendLayerBackward(baseLayers, "C");
      assert.deepEqual(
        result.map((l) => ({ id: l.id, z: l.z_index })),
        [
          { id: "A", z: 0 },
          { id: "C", z: 1 },
          { id: "B", z: 2 },
          { id: "D", z: 3 },
        ]
      );
    });

    it("sendLayerBackward leaves backmost layer unchanged", () => {
      const result = sendLayerBackward(baseLayers, "A");
      assert.deepEqual(
        result.map((l) => ({ id: l.id, z: l.z_index })),
        [
          { id: "A", z: 0 },
          { id: "B", z: 1 },
          { id: "C", z: 2 },
          { id: "D", z: 3 },
        ]
      );
    });
  });

  describe("3. Bring To Front & Send To Back", () => {
    const baseLayers: VisualLayer[] = [
      { id: "A", type: "media", z_index: 0 },
      { id: "B", type: "text", z_index: 1 },
      { id: "C", type: "shape", z_index: 2 },
      { id: "D", type: "sticker", z_index: 3 },
    ];

    it("bringLayerToFront moves middle layer to the very top (index N-1)", () => {
      const result = bringLayerToFront(baseLayers, "B");
      assert.deepEqual(
        result.map((l) => ({ id: l.id, z: l.z_index })),
        [
          { id: "A", z: 0 },
          { id: "C", z: 1 },
          { id: "D", z: 2 },
          { id: "B", z: 3 },
        ]
      );
    });

    it("bringLayerToFront leaves already-front layer unchanged", () => {
      const result = bringLayerToFront(baseLayers, "D");
      assert.deepEqual(
        result.map((l) => ({ id: l.id, z: l.z_index })),
        [
          { id: "A", z: 0 },
          { id: "B", z: 1 },
          { id: "C", z: 2 },
          { id: "D", z: 3 },
        ]
      );
    });

    it("sendLayerToBack moves top or middle layer to the very bottom (index 0)", () => {
      const result = sendLayerToBack(baseLayers, "C");
      assert.deepEqual(
        result.map((l) => ({ id: l.id, z: l.z_index })),
        [
          { id: "C", z: 0 },
          { id: "A", z: 1 },
          { id: "B", z: 2 },
          { id: "D", z: 3 },
        ]
      );
    });

    it("sendLayerToBack leaves already-back layer unchanged", () => {
      const result = sendLayerToBack(baseLayers, "A");
      assert.deepEqual(
        result.map((l) => ({ id: l.id, z: l.z_index })),
        [
          { id: "A", z: 0 },
          { id: "B", z: 1 },
          { id: "C", z: 2 },
          { id: "D", z: 3 },
        ]
      );
    });
  });

  describe("4. Cross-Type Drag Reordering (moveLayerToIndex)", () => {
    const baseLayers: VisualLayer[] = [
      { id: "media1", type: "image", z_index: 0 },
      { id: "text1", type: "text", z_index: 1 },
      { id: "shape1", type: "shape", z_index: 2 },
      { id: "media2", type: "video", z_index: 3 },
    ];

    it("moves text layer between media1 and shape1 or to bottom", () => {
      const result = moveLayerToIndex(baseLayers, "text1", 0);
      assert.deepEqual(
        result.map((l) => ({ id: l.id, z: l.z_index })),
        [
          { id: "text1", z: 0 },
          { id: "media1", z: 1 },
          { id: "shape1", z: 2 },
          { id: "media2", z: 3 },
        ]
      );
    });

    it("moves media1 across types to top position", () => {
      const result = moveLayerToIndex(baseLayers, "media1", 3);
      assert.deepEqual(
        result.map((l) => ({ id: l.id, z: l.z_index })),
        [
          { id: "text1", z: 0 },
          { id: "shape1", z: 1 },
          { id: "media2", z: 2 },
          { id: "media1", z: 3 },
        ]
      );
    });

    it("clamps out-of-bounds destination index safely", () => {
      const result = moveLayerToIndex(baseLayers, "media1", 999);
      assert.equal(result[result.length - 1].id, "media1");
      assert.equal(result[result.length - 1].z_index, 3);
    });
  });

  describe("5. Duplication & Deletion", () => {
    it("duplicateLayerWithZIndex inserts cloned layer immediately above source", () => {
      const layers: VisualLayer[] = [
        { id: "m1", type: "media", z_index: 0 },
        { id: "t1", type: "text", z_index: 1 },
        { id: "s1", type: "shape", z_index: 2 },
      ];
      const clone: VisualLayer = { id: "t1_copy", type: "text" };
      const result = duplicateLayerWithZIndex(layers, "t1", clone);

      assert.deepEqual(
        result.map((l) => ({ id: l.id, z: l.z_index })),
        [
          { id: "m1", z: 0 },
          { id: "t1", z: 1 },
          { id: "t1_copy", z: 2 },
          { id: "s1", z: 3 },
        ]
      );
    });

    it("deleteLayerWithZIndex removes layer and normalizes remaining z_indices", () => {
      const layers: VisualLayer[] = [
        { id: "m1", type: "media", z_index: 0 },
        { id: "t1", type: "text", z_index: 1 },
        { id: "s1", type: "shape", z_index: 2 },
        { id: "m2", type: "media", z_index: 3 },
      ];
      const result = deleteLayerWithZIndex(layers, "t1");
      assert.deepEqual(
        result.map((l) => ({ id: l.id, z: l.z_index })),
        [
          { id: "m1", z: 0 },
          { id: "s1", z: 1 },
          { id: "m2", z: 2 },
        ]
      );
    });
  });

  describe("6. Phase 38 Locking Protection", () => {
    const layers: VisualLayer[] = [
      { id: "m1", type: "media", z_index: 0 },
      { id: "locked_layer", type: "text", z_index: 1, locked: true },
      { id: "s1", type: "shape", z_index: 2 },
    ];

    it("prevents bringLayerForward on locked layer", () => {
      const res = bringLayerForward(layers, "locked_layer");
      assert.equal(res.find((l) => l.id === "locked_layer")?.z_index, 1);
    });

    it("prevents sendLayerBackward on locked layer", () => {
      const res = sendLayerBackward(layers, "locked_layer");
      assert.equal(res.find((l) => l.id === "locked_layer")?.z_index, 1);
    });

    it("prevents bringLayerToFront on locked layer", () => {
      const res = bringLayerToFront(layers, "locked_layer");
      assert.equal(res.find((l) => l.id === "locked_layer")?.z_index, 1);
    });

    it("prevents sendLayerToBack on locked layer", () => {
      const res = sendLayerToBack(layers, "locked_layer");
      assert.equal(res.find((l) => l.id === "locked_layer")?.z_index, 1);
    });

    it("prevents moveLayerToIndex on locked layer", () => {
      const res = moveLayerToIndex(layers, "locked_layer", 0);
      assert.equal(res.find((l) => l.id === "locked_layer")?.z_index, 1);
    });
  });

  describe("7. Phase 38 Visibility Orthogonality", () => {
    it("preserves z_index when layer is hidden (enabled: false)", () => {
      const layers: VisualLayer[] = [
        { id: "m1", type: "media", z_index: 0, enabled: true },
        { id: "t1", type: "text", z_index: 1, enabled: false },
        { id: "s1", type: "shape", z_index: 2, enabled: true },
      ];
      const ordered = getOrderedVisualLayers(layers);
      assert.equal(ordered.find((l) => l.id === "t1")?.z_index, 1);
      assert.equal(ordered.find((l) => l.id === "t1")?.enabled, false);
    });
  });

  describe("8. Typed Arrays Derive & Distribute", () => {
    it("derives unified collection from legacy typed arrays using media -> text -> elements baseline", () => {
      const media: VisualLayer[] = [{ id: "m1", type: "image" }, { id: "m2", type: "video" }];
      const text: VisualLayer[] = [{ id: "t1", type: "text" }];
      const elements: VisualLayer[] = [{ id: "e1", type: "shape" }];

      const unified = deriveUnifiedVisualLayers(media, text, elements);
      assert.deepEqual(
        unified.map((l) => ({ id: l.id, z: l.z_index })),
        [
          { id: "m1", z: 0 },
          { id: "m2", z: 1 },
          { id: "t1", z: 2 },
          { id: "e1", z: 3 },
        ]
      );
    });

    it("derives unified collection preserving cross-type interleaving when z_indices are present", () => {
      const media: VisualLayer[] = [{ id: "m1", type: "image", z_index: 2 }];
      const text: VisualLayer[] = [{ id: "t1", type: "text", z_index: 0 }];
      const elements: VisualLayer[] = [{ id: "e1", type: "shape", z_index: 1 }];

      const unified = deriveUnifiedVisualLayers(media, text, elements);
      assert.deepEqual(
        unified.map((l) => ({ id: l.id, z: l.z_index })),
        [
          { id: "t1", z: 0 },
          { id: "e1", z: 1 },
          { id: "m1", z: 2 },
        ]
      );
    });

    it("distributes unified collection back into typed arrays accurately", () => {
      const unified: VisualLayer[] = [
        { id: "t1", type: "text", z_index: 0 },
        { id: "e1", type: "shape", z_index: 1 },
        { id: "m1", type: "image", z_index: 2 },
      ];
      const { mediaLayers, textLayers, elementLayers } = distributeUnifiedVisualLayers(unified);
      assert.equal(mediaLayers.length, 1);
      assert.equal(mediaLayers[0].id, "m1");
      assert.equal(mediaLayers[0].z_index, 2);

      assert.equal(textLayers.length, 1);
      assert.equal(textLayers[0].id, "t1");
      assert.equal(textLayers[0].z_index, 0);

      assert.equal(elementLayers.length, 1);
      assert.equal(elementLayers[0].id, "e1");
      assert.equal(elementLayers[0].z_index, 1);
    });
  });
});
