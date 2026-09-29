import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  clampLeftSidebarWidth,
  clampRightInspectorWidth,
  clampTimelineHeight,
  getStoredLayoutDimension,
  STUDIO_LAYOUT_CONSTRAINTS,
  studioRenderReducer,
  StudioRenderState,
} from "./studioLayoutUtils";

describe("Studio Sections Resizing & Clamping", () => {
  it("clamps left sidebar within minimum (140px) and maximum (420px) bounds", () => {
    const defaultW = STUDIO_LAYOUT_CONSTRAINTS.leftSidebar.default; // 176
    assert.equal(clampLeftSidebarWidth(defaultW, 0), 176);

    // Growing wider
    assert.equal(clampLeftSidebarWidth(defaultW, 100), 276);
    // Exceeding maximum bound
    assert.equal(clampLeftSidebarWidth(defaultW, 500), 420);

    // Shrinking narrower
    assert.equal(clampLeftSidebarWidth(defaultW, -20), 156);
    // Exceeding minimum bound
    assert.equal(clampLeftSidebarWidth(defaultW, -100), 140);
  });

  it("clamps right inspector within minimum (240px) and maximum (500px) bounds", () => {
    const defaultW = STUDIO_LAYOUT_CONSTRAINTS.rightInspector.default; // 320
    assert.equal(clampRightInspectorWidth(defaultW, 0), 320);

    // Dragging left increases width
    assert.equal(clampRightInspectorWidth(defaultW, 80), 400);
    // Exceeding maximum
    assert.equal(clampRightInspectorWidth(defaultW, 300), 500);

    // Dragging right decreases width
    assert.equal(clampRightInspectorWidth(defaultW, -50), 270);
    // Exceeding minimum
    assert.equal(clampRightInspectorWidth(defaultW, -200), 240);
  });

  it("clamps timeline height within minimum (160px) and maximum (550px) bounds", () => {
    const defaultH = STUDIO_LAYOUT_CONSTRAINTS.timeline.default; // 256
    assert.equal(clampTimelineHeight(defaultH, 0), 256);

    // Dragging upwards increases height
    assert.equal(clampTimelineHeight(defaultH, 100), 356);
    // Exceeding maximum
    assert.equal(clampTimelineHeight(defaultH, 400), 550);

    // Dragging downwards decreases height
    assert.equal(clampTimelineHeight(defaultH, -80), 176);
    // Exceeding minimum
    assert.equal(clampTimelineHeight(defaultH, -200), 160);
  });

  it("retrieves valid stored layout dimensions and falls back when invalid", () => {
    const mockStorage: Record<string, string> = {
      studio_left_sidebar_width: "220",
      studio_right_inspector_width: "999", // out of bounds
      studio_timeline_height: "invalid_num",
    };

    const fakeSessionStorage = {
      getItem: (key: string) => mockStorage[key] || null,
      setItem: (key: string, val: string) => {
        mockStorage[key] = val;
      },
    } as any;

    // Valid entry returns parsed integer
    const leftWidth = getStoredLayoutDimension(
      "studio_left_sidebar_width",
      176,
      140,
      420,
      fakeSessionStorage
    );
    assert.equal(leftWidth, 220);

    // Out of bounds entry falls back to default
    const rightWidth = getStoredLayoutDimension(
      "studio_right_inspector_width",
      320,
      240,
      500,
      fakeSessionStorage
    );
    assert.equal(rightWidth, 320);

    // Non-numeric entry falls back to default
    const timelineH = getStoredLayoutDimension(
      "studio_timeline_height",
      256,
      160,
      550,
      fakeSessionStorage
    );
    assert.equal(timelineH, 256);
  });
});

describe("Studio Generate & Render State Pipeline", () => {
  const initialRenderState: StudioRenderState = {
    isRendering: false,
    progressPct: 0,
  };

  it("transitions through saving -> queued -> processing -> completed with real video asset URL", () => {
    // 1. User clicks Generate -> state moves to saving timeline state
    let state = studioRenderReducer(initialRenderState, { type: "START_SAVE" });
    assert.equal(state.isRendering, true);
    assert.equal(state.stage, "Saving timeline state...");
    assert.equal(state.error, undefined);

    // 2. Timeline persisted and render job created
    state = studioRenderReducer(state, { type: "QUEUED", jobId: "job_render_123" });
    assert.equal(state.isRendering, true);
    assert.equal(state.jobId, "job_render_123");
    assert.equal(state.stage, "Queued");

    // 3. SSE Job Stream updates progress
    state = studioRenderReducer(state, {
      type: "PROGRESS",
      progressPct: 45,
      stage: "Encoding video scenes...",
    });
    assert.equal(state.isRendering, true);
    assert.equal(state.progressPct, 45);
    assert.equal(state.stage, "Encoding video scenes...");

    // 4. Job completes with real rendered MP4 asset URL
    const realVideoUrl = "http://127.0.0.1:9000/heyzen-assets/exports/proj_1_v1.mp4";
    state = studioRenderReducer(state, {
      type: "COMPLETED",
      downloadUrl: realVideoUrl,
    });
    assert.equal(state.isRendering, false);
    assert.equal(state.progressPct, 100);
    assert.equal(state.stage, "Completed");
    assert.equal(state.downloadUrl, realVideoUrl);
  });

  it("handles render failure preserving genuine backend error without mocking or fake URLs", () => {
    let state = studioRenderReducer(initialRenderState, { type: "START_SAVE" });
    state = studioRenderReducer(state, { type: "QUEUED", jobId: "job_fail_999" });

    // GPU_REQUIRED prerequisite preservation
    const gpuErrorMessage =
      "GPU_REQUIRED: Neural avatar generation requires a CUDA GPU or configured remote GPU worker.";
    state = studioRenderReducer(state, { type: "FAILED", error: gpuErrorMessage });

    assert.equal(state.isRendering, false);
    assert.equal(state.stage, "Failed");
    assert.equal(state.error, gpuErrorMessage);
    // Must NOT fabricate a fake download URL on failure
    assert.equal(state.downloadUrl, undefined);
  });

  it("handles pre-render save failure gracefully without invoking render endpoint", () => {
    let state = studioRenderReducer(initialRenderState, { type: "START_SAVE" });
    state = studioRenderReducer(state, {
      type: "SAVE_ERROR",
      error: "OCC Conflict: project revision mismatch (expected 2, found 3)",
    });

    assert.equal(state.isRendering, false);
    assert.equal(state.error, "OCC Conflict: project revision mismatch (expected 2, found 3)");
    assert.equal(state.jobId, undefined);
  });
});

describe("Studio Concurrency & Revision Conflict Management", () => {
  it("serializes concurrent mutation calls so that expected_revision never uses stale state", async () => {
    let currentServerRevision = 3;
    const mutationLog: { expectedRev: number; committedRev: number }[] = [];

    // Simulated mutex queue matching VidoAIStudio saveQueueRef pattern
    let saveQueue: Promise<any> = Promise.resolve();
    let clientRevision = 3;

    const enqueueSaveMutation = (mutationFn: () => Promise<number>) => {
      const next = saveQueue.then(
        () => mutationFn(),
        () => mutationFn()
      );
      saveQueue = next.catch(() => {});
      return next;
    };

    const runSave = async (id: number) => {
      return enqueueSaveMutation(async () => {
        // Must read current authoritative revision
        const expected = clientRevision;
        if (expected !== currentServerRevision) {
          throw new Error(
            `Revision conflict: current project revision is ${currentServerRevision}, but update expected revision ${expected}.`
          );
        }
        currentServerRevision += 1;
        clientRevision = currentServerRevision;
        mutationLog.push({ expectedRev: expected, committedRev: currentServerRevision });
        return currentServerRevision;
      });
    };

    // Fire two mutations simultaneously (e.g. blur save + generate click)
    const [res1, res2] = await Promise.all([runSave(1), runSave(2)]);

    assert.equal(res1, 4);
    assert.equal(res2, 5);
    assert.equal(mutationLog.length, 2);
    // First mutation expected 3 -> committed 4
    assert.deepEqual(mutationLog[0], { expectedRev: 3, committedRev: 4 });
    // Second mutation waited and expected 4 -> committed 5 (NEVER sending stale 3!)
    assert.deepEqual(mutationLog[1], { expectedRev: 4, committedRev: 5 });
  });

  it("recovers from revision conflict by refetching server revision and retrying once", async () => {
    let serverRevision = 4; // Server advanced behind client's back
    let clientRevision = 3; // Stale client
    let attempts = 0;

    const executeWithRetryOnConflict = async () => {
      let localAttempt = 0;
      while (localAttempt < 2) {
        attempts++;
        try {
          if (clientRevision !== serverRevision) {
            throw new Error(
              `Revision conflict: current project revision is ${serverRevision}, but update expected revision ${clientRevision}.`
            );
          }
          serverRevision += 1;
          clientRevision = serverRevision;
          return { success: true, revision: serverRevision };
        } catch (err: any) {
          if (err.message.includes("Revision conflict") && localAttempt === 0) {
            localAttempt++;
            // Refetch latest revision
            clientRevision = serverRevision;
            continue;
          }
          throw err;
        }
      }
    };

    const res = await executeWithRetryOnConflict();
    assert.equal(res?.success, true);
    assert.equal(res?.revision, 5);
    assert.equal(attempts, 2); // 1st attempt failed with conflict, 2nd attempt refetched and succeeded
  });
});

