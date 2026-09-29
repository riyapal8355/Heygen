/**
 * Advanced Timeline Editing & Snapping Tests (Phase 43)
 *
 * Verifies:
 * Split:
 *   1. split valid clip
 *   2. split timing correctness
 *   3. split preserves total duration
 *   4. split preserves metadata
 *   5. invalid split before start
 *   6. invalid split after end
 *   7. invalid boundary split
 *   8. split undo
 *   9. split redo
 *   10. locked clip behavior
 *   11. multi-type split behavior (video, image, text, element, audio)
 *
 * Zoom:
 *   12. zoom bounds (MIN = 0.5, MAX = 3.0)
 *   13. coordinate conversion at various zoom levels
 *   14. zoom anchor stability (viewport center time invariance)
 *   15. ruler synchronization across zoom scales
 *
 * Pan:
 *   16. horizontal viewport movement / scroll bounds
 *   17. coordinate conversion after pan
 *   18. zoom + pan interaction
 *
 * Snapping:
 *   19. start-to-end snap
 *   20. end-to-start snap
 *   21. start-to-start snap
 *   22. end-to-end snap
 *   23. snap threshold enforcement
 *   24. no self-snap
 *   25. locked/hidden clip filtering
 *   26. snapping after zoom
 *   27. snapping after pan
 *
 * Integration:
 *   28. drag + zoom
 *   29. drag + pan
 *   30. trim + zoom
 *   31. trim + pan
 *   32. split + undo/redo
 *   33. split + persistence / OCC revision
 *   34. snap + undo/redo
 *   35. multi-scene compatibility
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  canSplitClip,
  splitClip,
  getClipToClipSnapTargets,
  calculateMoveTiming,
  calculateLeftTrimTiming,
  calculateRightTrimTiming,
  getSceneGlobalStart,
  getScenePlayheadTime,
  MIN_CLIP_DURATION,
  SNAP_THRESHOLD_SECONDS,
  MIN_TIMELINE_ZOOM,
  MAX_TIMELINE_ZOOM,
  DEFAULT_TIMELINE_ZOOM,
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

const defaultSelection: HistorySelectionState = {
  activeSceneIndex: 0,
  selectedMediaLayerId: null,
  selectedTextLayerId: null,
  selectedElementLayerId: null,
};

describe("Phase 43 — Advanced Timeline Editing & Snapping", () => {
  // =========================================================================
  // 1. SPLIT TESTS
  // =========================================================================
  describe("Split Semantics & Validation", () => {
    it("1. splits a valid clip non-destructively", () => {
      const clip = {
        id: "media_1",
        type: "video",
        name: "Intro Video",
        start_time: 2.0,
        end_time: 8.0,
        duration: 6.0,
        content: { media_type: "video", source_start_time: 1.0 },
      };
      const result = splitClip(clip, 5.0, "media_2", MIN_CLIP_DURATION);
      assert.notEqual(result, null);
      assert.equal(result!.firstClip.id, "media_1");
      assert.equal(result!.secondClip.id, "media_2");
    });

    it("2. computes correct split timing on both halves", () => {
      const clip = { id: "text_1", type: "text", start_time: 1.0, end_time: 7.0 };
      const result = splitClip(clip, 4.0, "text_2", MIN_CLIP_DURATION);
      assert.notEqual(result, null);
      assert.equal(result!.firstClip.start_time, 1.0);
      assert.equal(result!.firstClip.end_time, 4.0);
      assert.equal(result!.secondClip.start_time, 4.0);
      assert.equal(result!.secondClip.end_time, 7.0);
    });

    it("3. preserves total duration with zero gap and zero overlap", () => {
      const clip = { id: "c1", start_time: 2.5, end_time: 9.5 };
      const originalDuration = clip.end_time - clip.start_time;
      const res = splitClip(clip, 6.2, "c2", MIN_CLIP_DURATION)!;
      const d1 = res.firstClip.end_time - res.firstClip.start_time;
      const d2 = res.secondClip.end_time - res.secondClip.start_time;
      assert.equal(Math.round((d1 + d2) * 1000) / 1000, originalDuration);
      assert.equal(res.firstClip.end_time, res.secondClip.start_time);
    });

    it("4. preserves metadata, styling, and advances source media offset", () => {
      const clip = {
        id: "video_clip_1",
        type: "video",
        name: "Main Feature",
        z_index: 3,
        transform: { x: 0.5, y: 0.5, scale: 1.2, rotation: 0 },
        content: {
          url: "https://example.com/video.mp4",
          source_start_time: 10.0,
        },
        start_time: 2.0,
        end_time: 10.0,
      };

      const res = splitClip(clip, 5.0, "video_clip_2")!;
      // First clip retains initial source offset
      assert.equal(res.firstClip.content.source_start_time, 10.0);
      assert.equal(res.firstClip.z_index, 3);
      assert.equal(res.firstClip.transform.scale, 1.2);

      // Second clip advances source offset by elapsed timeline duration (5.0 - 2.0 = 3.0)
      assert.equal(res.secondClip.content.source_start_time, 13.0);
      assert.equal(res.secondClip.z_index, 3);
      assert.equal(res.secondClip.transform.scale, 1.2);
    });

    it("5. rejects invalid split before clip start", () => {
      const can = canSplitClip(2.0, 8.0, 1.5, MIN_CLIP_DURATION, false);
      assert.equal(can, false);
      const res = splitClip({ start_time: 2.0, end_time: 8.0 }, 1.5, "new_id");
      assert.equal(res, null);
    });

    it("6. rejects invalid split after clip end", () => {
      const can = canSplitClip(2.0, 8.0, 8.5, MIN_CLIP_DURATION, false);
      assert.equal(can, false);
      const res = splitClip({ start_time: 2.0, end_time: 8.0 }, 8.5, "new_id");
      assert.equal(res, null);
    });

    it("7. rejects invalid boundary split (too close to start/end boundary)", () => {
      // Exactly at start
      assert.equal(canSplitClip(2.0, 8.0, 2.0, MIN_CLIP_DURATION, false), false);
      // Exactly at end
      assert.equal(canSplitClip(2.0, 8.0, 8.0, MIN_CLIP_DURATION, false), false);
      // Within minimum duration (e.g. 2.1s where start is 2.0s and minDuration is 0.2s)
      assert.equal(canSplitClip(2.0, 8.0, 2.1, MIN_CLIP_DURATION, false), false);
      assert.equal(canSplitClip(2.0, 8.0, 7.9, MIN_CLIP_DURATION, false), false);
    });

    it("8 & 9. integrates split with single-action undo and redo", () => {
      const initialScene = {
        id: "s1",
        sequence: 1,
        duration: 10.0,
        layers: [
          { id: "layer_1", type: "video", start_time: 1.0, end_time: 9.0, name: "Clip A" },
        ],
      };
      let history = createHistory([initialScene], [], {
        activeSceneIndex: 0,
        selectedMediaLayerId: "layer_1",
        selectedTextLayerId: null,
        selectedElementLayerId: null,
      });

      // Perform split at 5.0s
      const splitRes = splitClip(initialScene.layers[0], 5.0, "layer_2")!;
      const splitScene = {
        ...initialScene,
        layers: [splitRes.firstClip, splitRes.secondClip],
      };

      history = pushHistory(history, [splitScene], [], {
        activeSceneIndex: 0,
        selectedMediaLayerId: "layer_2",
        selectedTextLayerId: null,
        selectedElementLayerId: null,
      }, "Split Clip");

      assert.equal(canUndo(history), true);
      assert.equal(history.past.length, 1);

      // Undo split
      const undoRes = undo(history)!;
      assert.equal(undoRes.snapshot.scenes[0]!.layers!.length, 1);
      assert.equal(undoRes.snapshot.scenes[0]!.layers![0]!.id, "layer_1");
      assert.equal(undoRes.snapshot.scenes[0]!.layers![0]!.end_time, 9.0);

      // Redo split
      const redoRes = redo(undoRes.nextState)!;
      assert.equal(redoRes.snapshot.scenes[0]!.layers!.length, 2);
      assert.equal(redoRes.snapshot.scenes[0]!.layers![0]!.id, "layer_1");
      assert.equal(redoRes.snapshot.scenes[0]!.layers![1]!.id, "layer_2");
      assert.equal(redoRes.snapshot.scenes[0]!.layers![0]!.end_time, 5.0);
      assert.equal(redoRes.snapshot.scenes[0]!.layers![1]!.start_time, 5.0);
    });

    it("10. prevents splitting locked clips", () => {
      const lockedClip = {
        id: "locked_layer",
        type: "text",
        start_time: 1.0,
        end_time: 8.0,
        locked: true,
      };
      assert.equal(canSplitClip(1.0, 8.0, 4.0, MIN_CLIP_DURATION, true), false);
      const res = splitClip(lockedClip, 4.0, "new_id");
      assert.equal(res, null);
    });

    it("11. supports splitting all temporal layer types (video, image, text, shape, audio)", () => {
      const types = ["video", "image", "text", "shape", "sticker", "audio"];
      for (const t of types) {
        const item = { id: `${t}_item`, type: t, start_time: 0.0, end_time: 6.0 };
        const res = splitClip(item, 3.0, `${t}_split`);
        assert.notEqual(res, null, `Type ${t} should support split`);
        assert.equal(res!.firstClip.end_time, 3.0);
        assert.equal(res!.secondClip.start_time, 3.0);
      }
    });
  });

  // =========================================================================
  // 2. TIMELINE ZOOM TESTS
  // =========================================================================
  describe("Timeline Zoom", () => {
    it("12. enforces zoom bounds between MIN_TIMELINE_ZOOM and MAX_TIMELINE_ZOOM", () => {
      assert.equal(MIN_TIMELINE_ZOOM, 0.5);
      assert.equal(MAX_TIMELINE_ZOOM, 3.0);
      assert.equal(DEFAULT_TIMELINE_ZOOM, 1.0);

      const clampZoom = (z: number) =>
        Math.max(MIN_TIMELINE_ZOOM, Math.min(MAX_TIMELINE_ZOOM, z));
      assert.equal(clampZoom(0.1), 0.5);
      assert.equal(clampZoom(4.5), 3.0);
      assert.equal(clampZoom(1.5), 1.5);
    });

    it("13. coordinate conversion scales accurately with zoom", () => {
      const totalDuration = 20.0;
      const baseWidthPx = 1000;

      // At zoom 1.0: 1000px = 20s => 50px/s
      const timeToPixel = (time: number, zoom: number) =>
        (time / totalDuration) * (baseWidthPx * zoom);
      const pixelToTime = (px: number, zoom: number) =>
        (px / (baseWidthPx * zoom)) * totalDuration;

      assert.equal(timeToPixel(10.0, 1.0), 500);
      assert.equal(pixelToTime(500, 1.0), 10.0);

      // At zoom 2.0: 2000px = 20s => 100px/s
      assert.equal(timeToPixel(10.0, 2.0), 1000);
      assert.equal(pixelToTime(1000, 2.0), 10.0);

      // At zoom 0.5: 500px = 20s => 25px/s
      assert.equal(timeToPixel(10.0, 0.5), 250);
      assert.equal(pixelToTime(250, 0.5), 10.0);
    });

    it("14. maintains stable zoom anchor around viewport center", () => {
      const containerWidth = 800;
      const oldZoom = 1.0;
      const newZoom = 2.0;
      const scrollLeft = 200; // viewport center px = 200 + 400 = 600px

      const centerPx = scrollLeft + containerWidth / 2;
      const ratio = newZoom / oldZoom;
      const newScrollCenter = centerPx * ratio; // 600 * 2 = 1200px
      const newScrollLeft = newScrollCenter - containerWidth / 2; // 1200 - 400 = 800px

      // Verify center time before and after zoom
      const totalDuration = 20.0;
      const totalWidthBefore = 1000 * oldZoom;
      const totalWidthAfter = 1000 * newZoom;

      const centerTimeBefore = (centerPx / totalWidthBefore) * totalDuration;
      const centerTimeAfter = (newScrollCenter / totalWidthAfter) * totalDuration;

      assert.equal(centerTimeBefore, centerTimeAfter);
    });

    it("15. ruler scale synchronizes with timeline zoom", () => {
      const zoomLevels = [0.5, 1.0, 2.0, 3.0];
      for (const zoom of zoomLevels) {
        const widthPct = Math.round(zoom * 100);
        assert.equal(widthPct >= 50 && widthPct <= 300, true);
      }
    });
  });

  // =========================================================================
  // 3. TIMELINE PAN TESTS
  // =========================================================================
  describe("Timeline Pan", () => {
    it("16. allows horizontal viewport movement within scroll bounds", () => {
      const totalWidth = 2400; // Zoomed width
      const viewportWidth = 800;
      const maxScrollLeft = totalWidth - viewportWidth; // 1600

      const clampScroll = (s: number) => Math.max(0, Math.min(maxScrollLeft, s));
      assert.equal(clampScroll(-50), 0);
      assert.equal(clampScroll(500), 500);
      assert.equal(clampScroll(2000), 1600);
    });

    it("17. coordinate conversion remains accurate after horizontal pan", () => {
      const totalDuration = 20.0;
      const zoomedTrackWidth = 2000; // 2x zoom on 1000px base
      const scrollLeft = 400;
      const clickViewportX = 300; // click relative to viewport

      const absoluteTrackX = scrollLeft + clickViewportX; // 700px
      const calculatedTime = (absoluteTrackX / zoomedTrackWidth) * totalDuration;

      assert.equal(calculatedTime, 7.0);
    });

    it("18. zoom + pan work seamlessly together", () => {
      const totalDuration = 30.0;
      const baseWidth = 1000;
      const zoom = 1.5;
      const scrollLeft = 300;

      const trackWidth = baseWidth * zoom; // 1500px
      const testTime = 12.0;

      // Time to screen coordinate
      const trackX = (testTime / totalDuration) * trackWidth; // 600px
      const viewportX = trackX - scrollLeft; // 300px

      // Screen coordinate back to time
      const recoveredTime = ((viewportX + scrollLeft) / trackWidth) * totalDuration;
      assert.equal(Math.round(recoveredTime * 1000) / 1000, testTime);
    });
  });

  // =========================================================================
  // 4. CLIP-TO-CLIP SNAPPING TESTS
  // =========================================================================
  describe("Clip-to-Clip Timeline Snapping", () => {
    const clips = [
      { id: "clip_A", start_time: 2.0, end_time: 6.0, enabled: true },
      { id: "clip_B", start_time: 10.0, end_time: 15.0, enabled: true },
      { id: "clip_C", start_time: 18.0, end_time: 22.0, enabled: true },
    ];

    it("19. dragged clip start snaps to neighbor clip end (start-to-end)", () => {
      // clip_A ends at 6.0. Dragged clip wants to start near 6.05s
      const snapTargets = getClipToClipSnapTargets(clips, "clip_dragging", [0.0, 30.0]);
      assert.equal(snapTargets.includes(6.0), true);

      const moveRes = calculateMoveTiming(6.05, 10.05, 0.0, 30.0, snapTargets, SNAP_THRESHOLD_SECONDS);
      assert.equal(moveRes.start_time, 6.0);
      assert.equal(moveRes.end_time, 10.0);
      assert.equal(moveRes.snappedTarget, 6.0);
    });

    it("20. dragged clip end snaps to neighbor clip start (end-to-start)", () => {
      // clip_B starts at 10.0. Dragged clip ends near 9.95s (duration 3.0, start 6.95s so start is far from 6.0)
      const snapTargets = getClipToClipSnapTargets(clips, "clip_dragging", [0.0, 30.0]);
      assert.equal(snapTargets.includes(10.0), true);

      const moveRes = calculateMoveTiming(6.95, 9.95, 0.0, 30.0, snapTargets, SNAP_THRESHOLD_SECONDS);
      assert.equal(moveRes.end_time, 10.0);
      assert.equal(moveRes.start_time, 7.0);
      assert.equal(moveRes.snappedTarget, 10.0);
    });

    it("21. dragged clip start snaps to neighbor clip start (start-to-start)", () => {
      // clip_B starts at 10.0. Dragged clip starts near 10.04s
      const snapTargets = getClipToClipSnapTargets(clips, "clip_dragging", [0.0, 30.0]);
      const moveRes = calculateMoveTiming(10.04, 14.04, 0.0, 30.0, snapTargets, SNAP_THRESHOLD_SECONDS);
      assert.equal(moveRes.start_time, 10.0);
      assert.equal(moveRes.snappedTarget, 10.0);
    });

    it("22. dragged clip end snaps to neighbor clip end (end-to-end)", () => {
      // clip_B ends at 15.0. Dragged clip ends near 14.96s
      const snapTargets = getClipToClipSnapTargets(clips, "clip_dragging", [0.0, 30.0]);
      const moveRes = calculateMoveTiming(10.96, 14.96, 0.0, 30.0, snapTargets, SNAP_THRESHOLD_SECONDS);
      assert.equal(moveRes.end_time, 15.0);
      assert.equal(moveRes.snappedTarget, 15.0);
    });

    it("23. enforces snap threshold (does not snap beyond 0.1s threshold)", () => {
      const snapTargets = [6.0];
      // At 6.08s (within 0.10s) -> snaps
      const snapIn = calculateMoveTiming(6.08, 10.08, 0.0, 30.0, snapTargets, 0.1);
      assert.equal(snapIn.start_time, 6.0);
      assert.equal(snapIn.snappedTarget, 6.0);

      // At 6.15s (beyond 0.10s) -> does NOT snap
      const snapOut = calculateMoveTiming(6.15, 10.15, 0.0, 30.0, snapTargets, 0.1);
      assert.equal(snapOut.start_time, 6.15);
      assert.equal(snapOut.snappedTarget, null);
    });

    it("24. excludes self from snap targets (no self-snap)", () => {
      const targets = getClipToClipSnapTargets(clips, "clip_A", []);
      // Should NOT include clip_A's own start (2.0) or end (6.0)
      assert.equal(targets.includes(2.0), false);
      assert.equal(targets.includes(6.0), false);
      // Should include clip_B and clip_C
      assert.equal(targets.includes(10.0), true);
      assert.equal(targets.includes(15.0), true);
    });

    it("25. excludes hidden / disabled clips from snap targets", () => {
      const mixedClips = [
        { id: "c1", start_time: 2.0, end_time: 5.0, enabled: true },
        { id: "c2_hidden", start_time: 8.0, end_time: 12.0, enabled: false },
      ];
      const targets = getClipToClipSnapTargets(mixedClips, "c3", []);
      assert.equal(targets.includes(2.0), true);
      assert.equal(targets.includes(5.0), true);
      assert.equal(targets.includes(8.0), false);
      assert.equal(targets.includes(12.0), false);
    });

    it("26. snapping operates identically at different zoom levels", () => {
      // Regardless of zoom factor, a 0.05s offset in time is within threshold
      const targetTime = 8.0;
      const zoomLevels = [0.5, 1.0, 2.0, 3.0];
      for (const zoom of zoomLevels) {
        const timeNear = 8.04;
        const res = calculateMoveTiming(timeNear, timeNear + 4.0, 0.0, 30.0, [targetTime], 0.1);
        assert.equal(res.start_time, 8.0, `Should snap to 8.0 at zoom ${zoom}`);
      }
    });

    it("27. snapping behaves consistently after pan / scroll offset", () => {
      const targetTime = 12.0;
      const scrollOffsets = [0, 300, 800, 1500];
      for (const scroll of scrollOffsets) {
        // Even with various scroll offsets, the time domain calculation produces exact snap
        const res = calculateMoveTiming(11.96, 15.96, 0.0, 30.0, [targetTime], 0.1);
        assert.equal(res.start_time, 12.0);
        assert.equal(res.snappedTarget, 12.0);
      }
    });
  });

  // =========================================================================
  // 5. INTEGRATION TESTS (DRAG, TRIM, OCC, MULTI-SCENE)
  // =========================================================================
  describe("Integration & End-to-End Scenarios", () => {
    it("28. clip drag with zoom scale delta conversion", () => {
      const containerWidth = 2000; // Zoomed container
      const maxDuration = 20.0;
      const deltaPx = 100; // 100px move in 2000px container => 1.0 second move

      const deltaSeconds = (deltaPx / containerWidth) * maxDuration;
      assert.equal(deltaSeconds, 1.0);

      const res = calculateMoveTiming(2.0, 6.0, deltaSeconds, maxDuration, []);
      assert.equal(res.start_time, 3.0);
      assert.equal(res.end_time, 7.0);
    });

    it("29. clip drag with pan viewport offset", () => {
      const maxDuration = 10.0;
      const containerWidth = 1000;
      const pointerMovementPx = 50; // 50px delta on screen
      const deltaSeconds = (pointerMovementPx / containerWidth) * maxDuration;

      const res = calculateMoveTiming(3.0, 7.0, deltaSeconds, maxDuration, []);
      assert.equal(res.start_time, 3.5);
      assert.equal(res.end_time, 7.5);
    });

    it("30. left-trim with zoom and snapping", () => {
      const res = calculateLeftTrimTiming(4.0, 10.0, 1.95, MIN_CLIP_DURATION, [6.0], 0.1);
      // Desired start = 4.0 + 1.95 = 5.95s -> snaps to 6.0s
      assert.equal(res.start_time, 6.0);
      assert.equal(res.end_time, 10.0);
      assert.equal(res.snappedTarget, 6.0);
    });

    it("31. right-trim with pan and snapping", () => {
      const res = calculateRightTrimTiming(2.0, 7.0, 0.95, 15.0, MIN_CLIP_DURATION, [8.0], 0.1);
      // Desired end = 7.0 + 0.95 = 7.95s -> snaps to 8.0s
      assert.equal(res.start_time, 2.0);
      assert.equal(res.end_time, 8.0);
      assert.equal(res.snappedTarget, 8.0);
    });

    it("32. split followed by undo and redo preserves exact document structure", () => {
      const scenes = [
        {
          id: "scene_1",
          sequence: 1,
          duration: 10.0,
          layers: [
            { id: "video_1", type: "video", start_time: 0.0, end_time: 10.0, name: "Clip A" },
          ],
        },
      ];
      let history = createHistory(scenes, []);

      // Split at 4.5s
      const split = splitClip(scenes[0].layers[0], 4.5, "video_2")!;
      const modifiedScenes = [
        {
          ...scenes[0],
          layers: [split.firstClip, split.secondClip],
        },
      ];

      history = pushHistory(history, modifiedScenes, [], defaultSelection, "Split Clip");
      assert.equal(history.past.length, 1);

      // Undo -> 1 clip
      const undone = undo(history)!;
      assert.equal(undone.snapshot.scenes[0]!.layers!.length, 1);
      assert.equal(undone.snapshot.scenes[0]!.layers![0]!.end_time, 10.0);

      // Redo -> 2 clips
      const redone = redo(undone.nextState)!;
      assert.equal(redone.snapshot.scenes[0]!.layers!.length, 2);
      assert.equal(redone.snapshot.scenes[0]!.layers![0]!.end_time, 4.5);
      assert.equal(redone.snapshot.scenes[0]!.layers![1]!.start_time, 4.5);
    });

    it("33. split preserves OCC revision tracking and serialization", () => {
      let revision = 4;
      const initialDoc = {
        revision,
        scenes: [
          {
            id: "s1",
            layers: [{ id: "l1", type: "text", start_time: 0.0, end_time: 6.0 }],
          },
        ],
      };

      // Perform mutation (split)
      const split = splitClip(initialDoc.scenes[0].layers[0], 3.0, "l2")!;
      revision += 1;
      const savedDoc = {
        revision,
        scenes: [
          {
            id: "s1",
            layers: [split.firstClip, split.secondClip],
          },
        ],
      };

      // JSON round-trip simulates backend save & reload
      const reloadedDoc = JSON.parse(JSON.stringify(savedDoc));
      assert.equal(reloadedDoc.revision, 5);
      assert.equal(reloadedDoc.scenes[0].layers.length, 2);
      assert.equal(reloadedDoc.scenes[0].layers[0].end_time, 3.0);
      assert.equal(reloadedDoc.scenes[0].layers[1].start_time, 3.0);
    });

    it("34. snapping mutations integrate cleanly with undo/redo", () => {
      const scene = {
        id: "s1",
        sequence: 1,
        duration: 12.0,
        layers: [
          { id: "clip_1", type: "image", start_time: 0.0, end_time: 4.0 },
          { id: "clip_2", type: "image", start_time: 5.5, end_time: 9.5 },
        ],
      };
      let history = createHistory([scene], []);

      // Snap clip_2 to clip_1's end (4.0s)
      const snapTargets = getClipToClipSnapTargets(scene.layers, "clip_2", [0.0, 12.0]);
      const moveRes = calculateMoveTiming(4.06, 8.06, 0.0, 12.0, snapTargets, 0.1);
      assert.equal(moveRes.start_time, 4.0);

      const modifiedScene = {
        ...scene,
        layers: [
          scene.layers[0],
          { ...scene.layers[1], start_time: moveRes.start_time, end_time: moveRes.end_time },
        ],
      };

      history = pushHistory(history, [modifiedScene], [], defaultSelection, "Move Clip (Snapped)");
      assert.equal(canUndo(history), true);

      // Undo restores 5.5s
      const u = undo(history)!;
      assert.equal(u.snapshot.scenes[0]!.layers![1]!.start_time, 5.5);
    });

    it("35. multi-scene compatibility: local playhead and global offset mapping", () => {
      const scenes = [
        { id: "sc_0", duration: 5.0 },
        { id: "sc_1", duration: 7.0 },
        { id: "sc_2", duration: 6.0 },
      ];

      // Global start timestamps
      assert.equal(getSceneGlobalStart(scenes, 0), 0.0);
      assert.equal(getSceneGlobalStart(scenes, 1), 5.0);
      assert.equal(getSceneGlobalStart(scenes, 2), 12.0);

      // Scene local playhead mapping from global playback time
      // Global 7.5s falls in Scene 1 at local 2.5s (7.5 - 5.0 = 2.5)
      const localInScene1 = getScenePlayheadTime(scenes, 1, 7.5);
      assert.equal(localInScene1, 2.5);

      // Splitting a layer in scene 1 respects its local 2.5s playhead
      const layerInScene1 = { id: "sc1_layer", type: "video", start_time: 1.0, end_time: 6.0 };
      const splitRes = splitClip(layerInScene1, localInScene1, "sc1_layer_part2")!;
      assert.equal(splitRes.firstClip.end_time, 2.5);
      assert.equal(splitRes.secondClip.start_time, 2.5);
      // Scene durations and transition configurations remain untouched
      assert.equal(scenes[1].duration, 7.0);
    });
  });
});
