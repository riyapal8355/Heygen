/**
 * Studio History Engine Tests (Phase 40)
 *
 * Verifies all pure history operations, boundaries, and invariants:
 * 1. Initial history creation & baseline present
 * 2. Push & linear stack progression
 * 3. Undo & Redo restoration
 * 4. Empty stack protections
 * 5. Branch truncation (new mutation after undo drops redo future)
 * 6. Maximum capacity enforcement (50-entry FIFO eviction)
 * 7. Selection restoration & normalization
 * 8. Deep cloning isolation (no mutable state leaks)
 * 9. Layer locking (Phase 38) preservation across undo/redo
 * 10. Layer visibility (Phase 38) preservation across undo/redo
 * 11. Lifecycle CRUD simulation (Add, Delete, Duplicate, Reorder)
 * 12. History clear
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  createHistory,
  pushHistory,
  undo,
  redo,
  canUndo,
  canRedo,
  clearHistory,
  normalizeSelectionState,
  deepClone,
  HistorySelectionState,
  DEFAULT_MAX_HISTORY_ENTRIES,
  AudioTrackItem,
} from "./studioHistory";
import { StudioScene } from "@/components/studio/VidoAIStudio";

function createMockScenes(): StudioScene[] {
  return [
    {
      id: "scene_1",
      sequence: 1,
      duration: 5.0,
      title: "Scene 1",
      layers: [
        {
          id: "layer_media_1",
          type: "image",
          name: "Background Image",
          start_time: 0,
          end_time: 5,
          enabled: true,
          locked: false,
          transform: { x: 0.5, y: 0.5, scale: 1.0, rotation: 0 },
          content: { asset_id: "asset_1", opacity: 1.0 },
        },
        {
          id: "layer_text_1",
          type: "text",
          name: "Main Title",
          start_time: 0,
          end_time: 5,
          enabled: true,
          locked: false,
          transform: { x: 0.5, y: 0.2, scale: 1.0, rotation: 0 },
          content: { text: "Hello World", font_size: 48, color: "#FFFFFF" },
        },
      ],
    },
    {
      id: "scene_2",
      sequence: 2,
      duration: 4.0,
      title: "Scene 2",
      layers: [
        {
          id: "layer_shape_1",
          type: "shape",
          name: "Banner Box",
          start_time: 0,
          end_time: 4,
          enabled: true,
          locked: true,
          transform: { x: 0.5, y: 0.8, scale: 1.0, rotation: 0 },
          content: { shape_type: "rectangle", fill: "#3B82F6" },
        },
      ],
    },
  ];
}

const defaultSelection: HistorySelectionState = {
  activeSceneIndex: 0,
  selectedMediaLayerId: "layer_media_1",
  selectedTextLayerId: null,
  selectedElementLayerId: null,
};

describe("Studio History Engine (Phase 40)", () => {
  describe("1. Initial History State", () => {
    it("creates history with empty past and future, and correct baseline present", () => {
      const initialScenes = createMockScenes();
      const history = createHistory(initialScenes, defaultSelection);

      assert.equal(history.past.length, 0);
      assert.equal(history.future.length, 0);
      assert.equal(canUndo(history), false);
      assert.equal(canRedo(history), false);
      assert.equal(history.present.scenes.length, 2);
      assert.equal(history.present.activeSceneIndex, 0);
      assert.equal(history.present.selection.selectedMediaLayerId, "layer_media_1");
      assert.equal(history.maxEntries, DEFAULT_MAX_HISTORY_ENTRIES);
    });

    it("does not create an artificial undoable entry on initial load", () => {
      const history = createHistory(createMockScenes(), defaultSelection);
      assert.equal(canUndo(history), false);
      const res = undo(history);
      assert.equal(res, null);
    });
  });

  describe("2. Push Operations", () => {
    it("moves current present into past and updates present with new state", () => {
      const initialScenes = createMockScenes();
      let history = createHistory(initialScenes, defaultSelection);

      // Mutate scenes: change position of layer_media_1
      const updatedScenes = createMockScenes();
      updatedScenes[0].layers![0].transform.x = 0.75;
      const updatedSelection: HistorySelectionState = {
        ...defaultSelection,
        selectedMediaLayerId: "layer_media_1",
      };

      history = pushHistory(history, updatedScenes, updatedSelection, "Move Media Layer");

      assert.equal(history.past.length, 1);
      assert.equal(history.future.length, 0);
      assert.equal(canUndo(history), true);
      assert.equal(canRedo(history), false);

      // Past contains original position (0.5)
      assert.equal(history.past[0].scenes[0].layers![0].transform.x, 0.5);
      // Present contains updated position (0.75)
      assert.equal(history.present.scenes[0].layers![0].transform.x, 0.75);
    });
  });

  describe("3. Undo & Redo Restoration", () => {
    it("undo restores past state and moves current present to future", () => {
      const scenesA = createMockScenes();
      let history = createHistory(scenesA, defaultSelection);

      const scenesB = createMockScenes();
      scenesB[0].layers![0].transform.x = 0.8;
      history = pushHistory(history, scenesB, defaultSelection, "Move Layer");

      const undoResult = undo(history);
      assert.ok(undoResult);
      assert.equal(undoResult.snapshot.scenes[0].layers![0].transform.x, 0.5);

      history = undoResult.nextState;
      assert.equal(history.past.length, 0);
      assert.equal(history.future.length, 1);
      assert.equal(canUndo(history), false);
      assert.equal(canRedo(history), true);
      assert.equal(history.present.scenes[0].layers![0].transform.x, 0.5);
      assert.equal(history.future[0].scenes[0].layers![0].transform.x, 0.8);
    });

    it("redo restores future state and moves present to past", () => {
      const scenesA = createMockScenes();
      let history = createHistory(scenesA, defaultSelection);

      const scenesB = createMockScenes();
      scenesB[0].layers![0].transform.x = 0.8;
      history = pushHistory(history, scenesB, defaultSelection, "Move Layer");

      // Undo back to A
      history = undo(history)!.nextState;

      // Redo back to B
      const redoResult = redo(history);
      assert.ok(redoResult);
      assert.equal(redoResult.snapshot.scenes[0].layers![0].transform.x, 0.8);

      history = redoResult.nextState;
      assert.equal(history.past.length, 1);
      assert.equal(history.future.length, 0);
      assert.equal(canUndo(history), true);
      assert.equal(canRedo(history), false);
      assert.equal(history.present.scenes[0].layers![0].transform.x, 0.8);
    });
  });

  describe("4. Empty Stack Protections", () => {
    it("returns null safely when undoing with empty past", () => {
      const history = createHistory(createMockScenes(), defaultSelection);
      assert.equal(undo(history), null);
    });

    it("returns null safely when redoing with empty future", () => {
      const history = createHistory(createMockScenes(), defaultSelection);
      assert.equal(redo(history), null);
    });
  });

  describe("5. Branch Truncation", () => {
    it("truncates future stack when new mutation is pushed after undo", () => {
      // Flow: A -> B -> C -> Undo(B) -> New Mutation D -> Redo(C) must be unavailable
      const scenesA = createMockScenes();
      let history = createHistory(scenesA, defaultSelection);

      const scenesB = createMockScenes();
      scenesB[0].layers![0].transform.x = 0.6;
      history = pushHistory(history, scenesB, defaultSelection, "Action B");

      const scenesC = createMockScenes();
      scenesC[0].layers![0].transform.x = 0.7;
      history = pushHistory(history, scenesC, defaultSelection, "Action C");

      assert.equal(history.past.length, 2);

      // Undo to B
      history = undo(history)!.nextState;
      assert.equal(history.present.scenes[0].layers![0].transform.x, 0.6);
      assert.equal(history.future.length, 1);
      assert.equal(canRedo(history), true);

      // Now perform new mutation D
      const scenesD = createMockScenes();
      scenesD[0].layers![0].transform.x = 0.95;
      history = pushHistory(history, scenesD, defaultSelection, "Action D");

      // Future must be empty (truncated)
      assert.equal(history.future.length, 0);
      assert.equal(canRedo(history), false);
      assert.equal(history.past.length, 2); // A and B
      assert.equal(history.present.scenes[0].layers![0].transform.x, 0.95);
    });
  });

  describe("6. Maximum History Limit (50 entries)", () => {
    it("enforces maximum entries limit and evicts oldest entries (FIFO)", () => {
      const maxEntries = 5;
      const initialScenes = createMockScenes();
      let history = createHistory(initialScenes, defaultSelection, maxEntries);

      // Push 10 mutations
      for (let i = 1; i <= 10; i++) {
        const s = createMockScenes();
        s[0].layers![0].transform.x = i * 0.05;
        history = pushHistory(history, s, defaultSelection, `Mutation ${i}`);
      }

      // Past stack must not exceed maxEntries
      assert.equal(history.past.length, maxEntries);

      // Oldest entry retained in past should be Mutation 5 (since present is Mutation 10, past has 5, 6, 7, 8, 9)
      assert.equal(history.past[0].actionName, "Mutation 5");
      assert.equal(history.past[4].actionName, "Mutation 9");
      assert.equal(history.present.actionName, "Mutation 10");
    });
  });

  describe("7. Selection Restoration & Normalization", () => {
    it("restores exact activeSceneIndex and visual layer selection", () => {
      const scenesA = createMockScenes();
      const selectionA: HistorySelectionState = {
        activeSceneIndex: 0,
        selectedMediaLayerId: "layer_media_1",
        selectedTextLayerId: null,
        selectedElementLayerId: null,
      };
      let history = createHistory(scenesA, selectionA);

      // Switch to Scene 2 and select element layer
      const scenesB = createMockScenes();
      const selectionB: HistorySelectionState = {
        activeSceneIndex: 1,
        selectedMediaLayerId: null,
        selectedTextLayerId: null,
        selectedElementLayerId: "layer_shape_1",
      };
      history = pushHistory(history, scenesB, selectionB, "Switch & Select Shape");

      // Undo should restore selectionA
      const undoRes = undo(history);
      assert.ok(undoRes);
      assert.equal(undoRes.snapshot.activeSceneIndex, 0);
      assert.equal(undoRes.snapshot.selection.selectedMediaLayerId, "layer_media_1");
      assert.equal(undoRes.snapshot.selection.selectedElementLayerId, null);
    });

    it("normalizes deleted layer ID to null if layer was removed", () => {
      const scenes = createMockScenes();
      // Suppose layer_deleted_xyz was selected previously
      const staleSelection: HistorySelectionState = {
        activeSceneIndex: 0,
        selectedMediaLayerId: "layer_deleted_xyz",
        selectedTextLayerId: null,
        selectedElementLayerId: null,
      };

      const normalized = normalizeSelectionState(scenes, staleSelection);
      assert.equal(normalized.selectedMediaLayerId, null);
      assert.equal(normalized.activeSceneIndex, 0);
    });

    it("clamps activeSceneIndex if scenes array is truncated", () => {
      const singleScene = [createMockScenes()[0]];
      const outOfBoundsSelection: HistorySelectionState = {
        activeSceneIndex: 5,
        selectedMediaLayerId: null,
        selectedTextLayerId: null,
        selectedElementLayerId: null,
      };

      const normalized = normalizeSelectionState(singleScene, outOfBoundsSelection);
      assert.equal(normalized.activeSceneIndex, 0);
    });
  });

  describe("8. Deep Cloning Isolation", () => {
    it("ensures mutating current state does not corrupt past snapshots", () => {
      const scenesA = createMockScenes();
      let history = createHistory(scenesA, defaultSelection);

      const scenesB = createMockScenes();
      scenesB[0].layers![0].transform.x = 0.9;
      history = pushHistory(history, scenesB, defaultSelection, "Mutation B");

      // Mutate scenesB in place outside history
      scenesB[0].layers![0].transform.x = 0.001;

      // History present must remain untouched (0.9)
      assert.equal(history.present.scenes[0].layers![0].transform.x, 0.9);
      // History past must remain untouched (0.5)
      assert.equal(history.past[0].scenes[0].layers![0].transform.x, 0.5);
    });
  });

  describe("9. Locking Compatibility (Phase 38)", () => {
    it("preserves layer locked status accurately across undo and redo", () => {
      const scenesA = createMockScenes();
      scenesA[0].layers![0].locked = false;
      let history = createHistory(scenesA, defaultSelection);

      // Lock layer
      const scenesB = createMockScenes();
      scenesB[0].layers![0].locked = true;
      history = pushHistory(history, scenesB, defaultSelection, "Lock Layer");

      assert.equal(history.present.scenes[0].layers![0].locked, true);

      // Undo: should restore unlocked
      const undoRes = undo(history);
      assert.ok(undoRes);
      assert.equal(undoRes.snapshot.scenes[0].layers![0].locked, false);

      // Redo: should restore locked
      const redoRes = redo(undoRes.nextState);
      assert.ok(redoRes);
      assert.equal(redoRes.snapshot.scenes[0].layers![0].locked, true);
    });
  });

  describe("10. Visibility Compatibility (Phase 38)", () => {
    it("preserves layer enabled status accurately across undo and redo", () => {
      const scenesA = createMockScenes();
      scenesA[0].layers![0].enabled = true;
      let history = createHistory(scenesA, defaultSelection);

      // Hide layer
      const scenesB = createMockScenes();
      scenesB[0].layers![0].enabled = false;
      history = pushHistory(history, scenesB, defaultSelection, "Hide Layer");

      assert.equal(history.present.scenes[0].layers![0].enabled, false);

      // Undo: should restore visible
      const undoRes = undo(history);
      assert.ok(undoRes);
      assert.equal(undoRes.snapshot.scenes[0].layers![0].enabled, true);

      // Redo: should restore hidden
      const redoRes = redo(undoRes.nextState);
      assert.ok(redoRes);
      assert.equal(redoRes.snapshot.scenes[0].layers![0].enabled, false);
    });
  });

  describe("11. Lifecycle CRUD Simulation", () => {
    it("Add Layer & Undo removes layer; Redo restores it", () => {
      const scenesA = createMockScenes();
      let history = createHistory(scenesA, defaultSelection);

      // Add text layer
      const scenesB = createMockScenes();
      scenesB[0].layers!.push({
        id: "new_text_layer",
        type: "text",
        name: "New Text",
        start_time: 0,
        end_time: 5,
        enabled: true,
        locked: false,
        transform: { x: 0.5, y: 0.5, scale: 1, rotation: 0 },
        content: { text: "Added Text" },
      });
      const selectionB: HistorySelectionState = {
        ...defaultSelection,
        selectedMediaLayerId: null,
        selectedTextLayerId: "new_text_layer",
      };

      history = pushHistory(history, scenesB, selectionB, "Add Text Layer");
      assert.equal(history.present.scenes[0].layers!.length, 3);

      // Undo: layer is removed
      const undoRes = undo(history)!;
      assert.equal(undoRes.snapshot.scenes[0].layers!.length, 2);
      assert.equal(
        undoRes.snapshot.scenes[0].layers!.some((l: any) => l.id === "new_text_layer"),
        false
      );

      // Redo: layer is restored
      const redoRes = redo(undoRes.nextState)!;
      assert.equal(redoRes.snapshot.scenes[0].layers!.length, 3);
      assert.equal(
        redoRes.snapshot.scenes[0].layers!.some((l: any) => l.id === "new_text_layer"),
        true
      );
    });

    it("Delete Layer & Undo restores all original properties and styling intact", () => {
      const scenesA = createMockScenes();
      const originalTextLayer = deepClone(scenesA[0].layers![1]);
      let history = createHistory(scenesA, defaultSelection);

      // Delete text layer
      const scenesB = createMockScenes();
      scenesB[0].layers = scenesB[0].layers!.filter((l: any) => l.id !== "layer_text_1");
      history = pushHistory(history, scenesB, defaultSelection, "Delete Layer");

      assert.equal(history.present.scenes[0].layers!.length, 1);

      // Undo: text layer restored with exact content
      const undoRes = undo(history)!;
      const restoredTextLayer = undoRes.snapshot.scenes[0].layers!.find(
        (l: any) => l.id === "layer_text_1"
      );
      assert.ok(restoredTextLayer);
      assert.deepEqual(restoredTextLayer, originalTextLayer);
    });

    it("Duplicate Layer & Undo removes cloned layer while leaving source layer intact", () => {
      const scenesA = createMockScenes();
      let history = createHistory(scenesA, defaultSelection);

      // Duplicate layer_media_1
      const scenesB = createMockScenes();
      const clone = deepClone(scenesB[0].layers![0]);
      clone.id = "layer_media_1_copy";
      clone.name = "Background Image (Copy)";
      scenesB[0].layers!.push(clone);
      const selectionB: HistorySelectionState = {
        ...defaultSelection,
        selectedMediaLayerId: "layer_media_1_copy",
      };

      history = pushHistory(history, scenesB, selectionB, "Duplicate Layer");
      assert.equal(history.present.scenes[0].layers!.length, 3);

      // Undo
      const undoRes = undo(history)!;
      assert.equal(undoRes.snapshot.scenes[0].layers!.length, 2);
      assert.equal(undoRes.snapshot.selection.selectedMediaLayerId, "layer_media_1");
    });

    it("Reorder Layers & Undo restores original z-index order", () => {
      const scenesA = createMockScenes();
      assert.equal(scenesA[0].layers![0].id, "layer_media_1");
      assert.equal(scenesA[0].layers![1].id, "layer_text_1");
      let history = createHistory(scenesA, defaultSelection);

      // Swap layers
      const scenesB = createMockScenes();
      const temp = scenesB[0].layers![0];
      scenesB[0].layers![0] = scenesB[0].layers![1];
      scenesB[0].layers![1] = temp;

      history = pushHistory(history, scenesB, defaultSelection, "Bring Forward");
      assert.equal(history.present.scenes[0].layers![0].id, "layer_text_1");
      assert.equal(history.present.scenes[0].layers![1].id, "layer_media_1");

      // Undo
      const undoRes = undo(history)!;
      assert.equal(undoRes.snapshot.scenes[0].layers![0].id, "layer_media_1");
      assert.equal(undoRes.snapshot.scenes[0].layers![1].id, "layer_text_1");
    });
  });

  describe("12. History Clear", () => {
    it("clears past and future while preserving present", () => {
      const scenesA = createMockScenes();
      let history = createHistory(scenesA, defaultSelection);

      const scenesB = createMockScenes();
      scenesB[0].layers![0].transform.x = 0.9;
      history = pushHistory(history, scenesB, defaultSelection, "Mutation B");

      history = clearHistory(history);
      assert.equal(history.past.length, 0);
      assert.equal(history.future.length, 0);
      assert.equal(canUndo(history), false);
      assert.equal(canRedo(history), false);
      assert.equal(history.present.scenes[0].layers![0].transform.x, 0.9);
    });
  });

  describe("13. Audio History (Phase 42A)", () => {
    function createMockAudioTracks(): AudioTrackItem[] {
      return [
        {
          id: "track_1",
          asset_id: "audio_asset_1",
          name: "Upbeat Corporate",
          volume: 0.8,
          start_time: 0.0,
          duration: 10.0,
          loop: true,
          muted: false,
        },
      ];
    }

    it("initializes history with audio_tracks in present snapshot", () => {
      const scenes = createMockScenes();
      const audioTracks = createMockAudioTracks();
      const history = createHistory(scenes, audioTracks, defaultSelection);

      assert.equal(history.present.audio_tracks.length, 1);
      assert.equal(history.present.audio_tracks[0].id, "track_1");
      assert.equal(history.present.audio_tracks[0].volume, 0.8);
      assert.equal(history.present.audio_tracks[0].muted, false);
    });

    it("deep-clones audio_tracks so future mutations do not mutate past snapshots", () => {
      const scenes = createMockScenes();
      const audioTracks = createMockAudioTracks();
      const history = createHistory(scenes, audioTracks, defaultSelection);

      // Mutate audioTracks array in place
      audioTracks[0].volume = 0.1;
      audioTracks[0].muted = true;

      // History present must remain isolated
      assert.equal(history.present.audio_tracks[0].volume, 0.8);
      assert.equal(history.present.audio_tracks[0].muted, false);
    });

    it("Volume mutation creates one history entry and coalesces slider drag", () => {
      const scenes = createMockScenes();
      const audioTracks = createMockAudioTracks();
      let history = createHistory(scenes, audioTracks, defaultSelection);

      // Simulate slider drag (1.0 -> 0.9 -> 0.8 -> 0.5) - only commit on pointer up
      const committedTracks = [
        {
          ...audioTracks[0],
          volume: 0.5,
        },
      ];
      history = pushHistory(history, scenes, committedTracks, defaultSelection, "Change Audio Volume");

      assert.equal(history.past.length, 1);
      assert.equal(history.present.audio_tracks[0].volume, 0.5);

      // Undo restores original volume 0.8
      const undoRes = undo(history)!;
      assert.equal(undoRes.snapshot.audio_tracks[0].volume, 0.8);

      // Redo restores 0.5
      const redoRes = redo(undoRes.nextState)!;
      assert.equal(redoRes.snapshot.audio_tracks[0].volume, 0.5);
    });

    it("Mute toggle: mute, undo mute, redo mute", () => {
      const scenes = createMockScenes();
      const audioTracks = createMockAudioTracks();
      let history = createHistory(scenes, audioTracks, defaultSelection);

      const mutedTracks = [
        {
          ...audioTracks[0],
          muted: true,
        },
      ];
      history = pushHistory(history, scenes, mutedTracks, defaultSelection, "Mute Audio Track");
      assert.equal(history.present.audio_tracks[0].muted, true);

      // Undo mute -> restores unmuted
      const undoRes = undo(history)!;
      assert.equal(undoRes.snapshot.audio_tracks[0].muted, false);

      // Redo mute -> restores muted
      const redoRes = redo(undoRes.nextState)!;
      assert.equal(redoRes.snapshot.audio_tracks[0].muted, true);
    });

    it("Add track: add track, undo removes it, redo restores it", () => {
      const scenes = createMockScenes();
      const initialAudio: AudioTrackItem[] = [];
      let history = createHistory(scenes, initialAudio, defaultSelection);

      const newTrack: AudioTrackItem = {
        id: "track_new",
        asset_id: "asset_music_2",
        name: "Lofi Chill",
        volume: 0.4,
        start_time: 1.0,
        duration: null,
        loop: true,
        muted: false,
      };
      history = pushHistory(history, scenes, [newTrack], defaultSelection, "Add Audio Track");
      assert.equal(history.present.audio_tracks.length, 1);
      assert.equal(history.present.audio_tracks[0].id, "track_new");

      // Undo removes track
      const undoRes = undo(history)!;
      assert.equal(undoRes.snapshot.audio_tracks.length, 0);

      // Redo restores track
      const redoRes = redo(undoRes.nextState)!;
      assert.equal(redoRes.snapshot.audio_tracks.length, 1);
      assert.equal(redoRes.snapshot.audio_tracks[0].id, "track_new");
    });

    it("Delete track: delete track, undo restores exact track with all fields intact, redo removes it", () => {
      const scenes = createMockScenes();
      const audioTracks = createMockAudioTracks();
      let history = createHistory(scenes, audioTracks, defaultSelection);

      // Delete track
      history = pushHistory(history, scenes, [], defaultSelection, "Remove Audio Track");
      assert.equal(history.present.audio_tracks.length, 0);

      // Undo restores track with exact properties intact
      const undoRes = undo(history)!;
      assert.equal(undoRes.snapshot.audio_tracks.length, 1);
      assert.equal(undoRes.snapshot.audio_tracks[0].id, "track_1");
      assert.equal(undoRes.snapshot.audio_tracks[0].asset_id, "audio_asset_1");
      assert.equal(undoRes.snapshot.audio_tracks[0].name, "Upbeat Corporate");
      assert.equal(undoRes.snapshot.audio_tracks[0].volume, 0.8);
      assert.equal(undoRes.snapshot.audio_tracks[0].start_time, 0.0);
      assert.equal(undoRes.snapshot.audio_tracks[0].duration, 10.0);
      assert.equal(undoRes.snapshot.audio_tracks[0].loop, true);
      assert.equal(undoRes.snapshot.audio_tracks[0].muted, false);

      // Redo removes it again
      const redoRes = redo(undoRes.nextState)!;
      assert.equal(redoRes.snapshot.audio_tracks.length, 0);
    });

    it("Timing: delay, start_time, duration mutations participate in history", () => {
      const scenes = createMockScenes();
      const audioTracks = createMockAudioTracks();
      let history = createHistory(scenes, audioTracks, defaultSelection);

      const retimedTracks: AudioTrackItem[] = [
        {
          ...audioTracks[0],
          start_time: 2.5,
          duration: 7.5,
        },
      ];
      history = pushHistory(history, scenes, retimedTracks, defaultSelection, "Audio Start Delay");
      assert.equal(history.present.audio_tracks[0].start_time, 2.5);
      assert.equal(history.present.audio_tracks[0].duration, 7.5);

      const undoRes = undo(history)!;
      assert.equal(undoRes.snapshot.audio_tracks[0].start_time, 0.0);
      assert.equal(undoRes.snapshot.audio_tracks[0].duration, 10.0);
    });

    it("Atomic snapshot: scene changes and audio changes in combined history timeline", () => {
      const scenesA = createMockScenes();
      const audioA = createMockAudioTracks();
      let history = createHistory(scenesA, audioA, defaultSelection);

      // 1. Move layer in Scene 1
      const scenesB = createMockScenes();
      scenesB[0].layers![0].transform.x = 0.88;
      history = pushHistory(history, scenesB, audioA, defaultSelection, "Move Layer");

      // 2. Adjust audio volume
      const audioB = [{ ...audioA[0], volume: 0.2 }];
      history = pushHistory(history, scenesB, audioB, defaultSelection, "Change Audio Volume");

      assert.equal(history.past.length, 2);
      assert.equal(history.present.scenes[0].layers![0].transform.x, 0.88);
      assert.equal(history.present.audio_tracks[0].volume, 0.2);

      // Undo Step 1: restores audio volume 0.8, keeps layer x at 0.88
      const undo1 = undo(history)!;
      assert.equal(undo1.snapshot.audio_tracks[0].volume, 0.8);
      assert.equal(undo1.snapshot.scenes[0].layers![0].transform.x, 0.88);

      // Undo Step 2: restores layer x to 0.5
      const undo2 = undo(undo1.nextState)!;
      assert.equal(undo2.snapshot.scenes[0].layers![0].transform.x, 0.5);
    });

    it("Branch truncation: undo audio mutation, make scene mutation, future stack is dropped", () => {
      const scenesA = createMockScenes();
      const audioA = createMockAudioTracks();
      let history = createHistory(scenesA, audioA, defaultSelection);

      // Mutate audio
      const audioB = [{ ...audioA[0], volume: 0.1 }];
      history = pushHistory(history, scenesA, audioB, defaultSelection, "Mute Track");
      assert.equal(canUndo(history), true);

      // Undo
      const undoRes = undo(history)!;
      history = undoRes.nextState;
      assert.equal(canRedo(history), true);

      // Make new scene mutation
      const scenesC = createMockScenes();
      scenesC[0].layers![0].transform.y = 0.99;
      history = pushHistory(history, scenesC, defaultSelection, "New Branch Mutation");

      // Redo must now be unavailable
      assert.equal(canRedo(history), false);
      assert.equal(history.future.length, 0);
    });
  });
});
