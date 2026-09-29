/**
 * Timeline Timing & Drag Utilities for HeyZen Studio
 *
 * Provides deterministic coordinate conversions, boundary clamping,
 * playhead snapping, minimum duration enforcement, and pointer drag handling.
 */

import React, { useRef, useState, useEffect, useCallback } from "react";

export const MIN_CLIP_DURATION = 0.2; // seconds
export const SNAP_THRESHOLD_SECONDS = 0.1; // seconds
export const MIN_TIMELINE_ZOOM = 0.5; // 50%
export const MAX_TIMELINE_ZOOM = 3.0; // 300%
export const DEFAULT_TIMELINE_ZOOM = 1.0; // 100%

export interface SnapTarget {
  time: number;
  label?: string;
}

export interface SplitResult<T> {
  firstClip: T;
  secondClip: T;
}

/**
 * Validates whether a clip can be cleanly split at the specified splitTime.
 * Requires:
 * 1. startTime + minDuration <= splitTime <= endTime - minDuration.
 * 2. clip must not be locked.
 */
export function canSplitClip(
  startTime: number,
  endTime: number,
  splitTime: number,
  minDuration: number = MIN_CLIP_DURATION,
  locked: boolean = false
): boolean {
  if (locked) return false;
  if (!Number.isFinite(startTime) || !Number.isFinite(endTime) || !Number.isFinite(splitTime)) {
    return false;
  }
  const safeStart = Math.max(0, startTime);
  const safeEnd = Math.max(safeStart + minDuration, endTime);
  return splitTime >= safeStart + minDuration && splitTime <= safeEnd - minDuration;
}

/**
 * Splits a visual layer or audio track into two non-destructive continuous clips.
 * Preserves styling, transform, content, z_index, locked/visible state, and updates
 * source media offsets where applicable (e.g. video/audio source start offset).
 */
export function splitClip<T extends Record<string, any>>(
  clip: T,
  splitTime: number,
  newId: string,
  minDuration: number = MIN_CLIP_DURATION
): SplitResult<T> | null {
  const startTime = Number(clip.start_time ?? 0);
  const endTime = Number(clip.end_time ?? clip.duration ?? 0);
  const isLocked = Boolean(clip.locked);

  if (!canSplitClip(startTime, endTime, splitTime, minDuration, isLocked)) {
    return null;
  }

  const roundedSplit = Math.round(splitTime * 1000) / 1000;

  // First half: [startTime, roundedSplit]
  const firstClip = JSON.parse(JSON.stringify(clip));
  firstClip.end_time = roundedSplit;
  if (typeof firstClip.duration === "number") {
    firstClip.duration = Math.round((roundedSplit - startTime) * 1000) / 1000;
  }

  // Second half: [roundedSplit, endTime]
  const secondClip = JSON.parse(JSON.stringify(clip));
  secondClip.id = newId;
  secondClip.start_time = roundedSplit;
  secondClip.end_time = endTime;
  if (typeof secondClip.duration === "number") {
    secondClip.duration = Math.round((endTime - roundedSplit) * 1000) / 1000;
  }

  // Preserve base name with (Part 2) or maintain cleanly
  if (secondClip.name) {
    secondClip.name = `${secondClip.name} (Part 2)`;
  }

  // If layer has content with source_start_time / media offset, advance it by elapsed time
  if (secondClip.content && typeof secondClip.content === "object") {
    const elapsed = roundedSplit - startTime;
    if (typeof secondClip.content.source_start_time === "number") {
      secondClip.content.source_start_time =
        Math.round((secondClip.content.source_start_time + elapsed) * 1000) / 1000;
    }
  }

  return { firstClip, secondClip };
}

/**
 * Collects clip-to-clip snap boundary targets from neighbor clips in the same scene/timeline.
 * Extracts start_time and end_time from all other active clips, excluding self.
 */
export function getClipToClipSnapTargets(
  allClips: Array<{ id: string | number; start_time?: number; end_time?: number; enabled?: boolean; locked?: boolean }>,
  currentClipId: string | number,
  additionalTargets: number[] = []
): number[] {
  const targets = new Set<number>(additionalTargets);

  for (const c of allClips) {
    if (String(c.id) === String(currentClipId)) continue;
    if (c.enabled === false) continue; // Do not snap to disabled/hidden clips

    const st = typeof c.start_time === "number" ? Math.round(c.start_time * 1000) / 1000 : null;
    const et = typeof c.end_time === "number" ? Math.round(c.end_time * 1000) / 1000 : null;

    if (st !== null && Number.isFinite(st) && st >= 0) {
      targets.add(st);
    }
    if (et !== null && Number.isFinite(et) && et >= 0) {
      targets.add(et);
    }
  }

  return Array.from(targets).sort((a, b) => a - b);
}

/**
 * Returns the global start timestamp (in seconds) of a scene given the scenes array.
 */
export function getSceneGlobalStart(
  scenes: { duration?: number }[],
  sceneIndex: number
): number {
  let start = 0;
  for (let i = 0; i < sceneIndex && i < scenes.length; i++) {
    start += scenes[i]?.duration || 5.0;
  }
  return Math.round(start * 1000) / 1000;
}

/**
 * Returns the local playhead time within a scene, or -1 if playhead is outside this scene.
 */
export function getScenePlayheadTime(
  scenes: { duration?: number }[],
  sceneIndex: number,
  playbackTime: number
): number {
  if (sceneIndex < 0 || sceneIndex >= scenes.length) return -1;
  const sceneDuration = scenes[sceneIndex]?.duration || 5.0;
  const globalStart = getSceneGlobalStart(scenes, sceneIndex);
  const globalEnd = globalStart + sceneDuration;

  if (playbackTime >= globalStart && playbackTime <= globalEnd) {
    return Math.round((playbackTime - globalStart) * 1000) / 1000;
  }
  return -1;
}

/**
 * Calculate horizontal drag-to-move for a clip.
 * Preserves exact duration (newEnd - newStart === originalEnd - originalStart).
 * Clamps strictly within [0, maxDuration].
 * Snaps to nearby targets (like playhead or scene boundaries) if within threshold.
 */
export interface MoveTimingResult {
  start_time: number;
  end_time: number;
  snappedTarget?: number | null;
}

export function calculateMoveTiming(
  originalStart: number,
  originalEnd: number,
  deltaSeconds: number,
  maxDuration: number,
  snapTargets: number[] = [],
  snapThreshold: number = SNAP_THRESHOLD_SECONDS
): MoveTimingResult {
  const safeStart = Number.isFinite(originalStart) ? Math.max(0, originalStart) : 0;
  const safeEnd = Number.isFinite(originalEnd)
    ? Math.max(safeStart + MIN_CLIP_DURATION, originalEnd)
    : safeStart + MIN_CLIP_DURATION;
  const clipDuration = Math.round((safeEnd - safeStart) * 1000) / 1000;

  let newStart = safeStart + deltaSeconds;
  let newEnd = newStart + clipDuration;

  // Snapping check (first start edge, then end edge)
  let snappedTarget: number | null = null;
  for (const target of snapTargets) {
    if (Number.isFinite(target) && target >= 0 && target <= maxDuration) {
      if (Math.abs(newStart - target) <= snapThreshold) {
        newStart = target;
        newEnd = newStart + clipDuration;
        snappedTarget = target;
        break;
      }
    }
  }

  if (snappedTarget === null) {
    for (const target of snapTargets) {
      if (Number.isFinite(target) && target >= 0 && target <= maxDuration) {
        if (Math.abs(newEnd - target) <= snapThreshold) {
          newEnd = target;
          newStart = newEnd - clipDuration;
          snappedTarget = target;
          break;
        }
      }
    }
  }

  // Boundary clamping
  if (newStart < 0) {
    newStart = 0;
    newEnd = Math.min(maxDuration, newStart + clipDuration);
  }
  if (newEnd > maxDuration) {
    newEnd = maxDuration;
    newStart = Math.max(0, newEnd - clipDuration);
  }

  return {
    start_time: Math.round(newStart * 1000) / 1000,
    end_time: Math.round(newEnd * 1000) / 1000,
    snappedTarget,
  };
}

/**
 * Calculate left-edge trimming for a clip.
 * Keeps end_time anchored.
 * Enforces start_time >= 0 and start_time <= end_time - minDuration.
 * Snaps to nearby targets if valid.
 */
export interface TrimTimingResult {
  start_time: number;
  end_time: number;
  snappedTarget?: number | null;
}

export function calculateLeftTrimTiming(
  originalStart: number,
  originalEnd: number,
  deltaSeconds: number,
  minDuration: number = MIN_CLIP_DURATION,
  snapTargets: number[] = [],
  snapThreshold: number = SNAP_THRESHOLD_SECONDS
): TrimTimingResult {
  const safeStart = Number.isFinite(originalStart) ? Math.max(0, originalStart) : 0;
  const safeEnd = Number.isFinite(originalEnd)
    ? Math.max(safeStart + minDuration, originalEnd)
    : safeStart + minDuration;

  let newStart = safeStart + deltaSeconds;
  let snappedTarget: number | null = null;

  // Playhead/target snapping
  for (const target of snapTargets) {
    if (Number.isFinite(target) && target >= 0) {
      if (Math.abs(newStart - target) <= snapThreshold) {
        if (target <= safeEnd - minDuration) {
          newStart = target;
          snappedTarget = target;
          break;
        }
      }
    }
  }

  // Boundary and min duration clamp
  newStart = Math.max(0, Math.min(safeEnd - minDuration, newStart));

  return {
    start_time: Math.round(newStart * 1000) / 1000,
    end_time: Math.round(safeEnd * 1000) / 1000,
    snappedTarget,
  };
}

export function calculateRightTrimTiming(
  originalStart: number,
  originalEnd: number,
  deltaSeconds: number,
  maxDuration: number,
  minDuration: number = MIN_CLIP_DURATION,
  snapTargets: number[] = [],
  snapThreshold: number = SNAP_THRESHOLD_SECONDS
): TrimTimingResult {
  const safeStart = Number.isFinite(originalStart) ? Math.max(0, originalStart) : 0;
  const safeEnd = Number.isFinite(originalEnd)
    ? Math.max(safeStart + minDuration, originalEnd)
    : safeStart + minDuration;

  let newEnd = safeEnd + deltaSeconds;
  let snappedTarget: number | null = null;

  // Playhead/target snapping
  for (const target of snapTargets) {
    if (Number.isFinite(target) && target <= maxDuration) {
      if (Math.abs(newEnd - target) <= snapThreshold) {
        if (target >= safeStart + minDuration) {
          newEnd = target;
          snappedTarget = target;
          break;
        }
      }
    }
  }

  // Boundary and min duration clamp
  newEnd = Math.min(maxDuration, Math.max(safeStart + minDuration, newEnd));

  return {
    start_time: Math.round(safeStart * 1000) / 1000,
    end_time: Math.round(newEnd * 1000) / 1000,
    snappedTarget,
  };
}

/**
 * Calculates new duration when resizing a scene block from its right edge (or left edge).
 * Enforces [minDuration, maxDuration], clamps to non-negative numbers, and applies snapping.
 */
export function calculateSceneResizeTiming(
  originalDuration: number,
  deltaSeconds: number,
  minDuration: number = 1.0,
  maxDuration: number = 60.0,
  snapTargets: number[] = [],
  snapThreshold: number = SNAP_THRESHOLD_SECONDS
): number {
  const safeOriginal = Number.isFinite(originalDuration) ? Math.max(minDuration, originalDuration) : minDuration;
  let newDuration = safeOriginal + deltaSeconds;

  for (const target of snapTargets) {
    if (Number.isFinite(target) && target >= minDuration && target <= maxDuration) {
      if (Math.abs(newDuration - target) <= snapThreshold) {
        newDuration = target;
        break;
      }
    }
  }

  return Math.max(minDuration, Math.min(maxDuration, Math.round(newDuration * 10) / 10));
}

/**
 * Safely clamps child layers or subtitle cues when scene duration shrinks,
 * preventing child layers from having timing that exceeds the new scene duration.
 */
export function clampLayersToSceneDuration<T extends { start_time?: number; end_time?: number; [key: string]: any }>(
  layers: T[],
  newDuration: number,
  minDuration: number = MIN_CLIP_DURATION
): T[] {
  return layers.map((layer) => {
    let start = typeof layer.start_time === "number" ? layer.start_time : 0;
    let end = typeof layer.end_time === "number" ? layer.end_time : newDuration;

    if (end > newDuration) {
      end = newDuration;
    }
    if (start >= end) {
      start = Math.max(0, end - minDuration);
    }
    return {
      ...layer,
      start_time: Math.round(start * 1000) / 1000,
      end_time: Math.round(end * 1000) / 1000,
    };
  });
}

export type TimelineDragMode = "move" | "trim_left" | "trim_right";

export interface UseTimelineClipDragOptions {
  id: string | number;
  startTime: number;
  endTime: number;
  maxDuration: number;
  snapTargets?: number[];
  snapThreshold?: number;
  containerRef: React.RefObject<HTMLElement | null>;
  onSelect: () => void;
  onUpdateTiming: (id: any, start: number, end: number) => void;
  onCommitTiming: () => void;
  onSnapChange?: (targetTime: number | null) => void;
  /** When true, drag and trim interactions are suppressed. */
  locked?: boolean;
}

/**
 * React hook managing mouse / pointer dragging and trimming for timeline clips.
 * Provides window-level tracking, click vs drag differentiation, and handle props.
 */
export function useTimelineClipDrag({
  id,
  startTime,
  endTime,
  maxDuration,
  snapTargets = [],
  snapThreshold = SNAP_THRESHOLD_SECONDS,
  containerRef,
  onSelect,
  onUpdateTiming,
  onCommitTiming,
  onSnapChange,
  locked = false,
}: UseTimelineClipDragOptions) {
  const [isDragging, setIsDragging] = useState(false);
  const [dragMode, setDragMode] = useState<TimelineDragMode | null>(null);
  const [activeSnapTime, setActiveSnapTime] = useState<number | null>(null);

  // References to keep callbacks and mutable drag session data stable
  const sessionRef = useRef<{
    active: boolean;
    mode: TimelineDragMode;
    startX: number;
    startY: number;
    initStart: number;
    initEnd: number;
    dragInitiated: boolean;
    containerWidth: number;
  } | null>(null);

  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;

  const onUpdateTimingRef = useRef(onUpdateTiming);
  onUpdateTimingRef.current = onUpdateTiming;

  const onCommitTimingRef = useRef(onCommitTiming);
  onCommitTimingRef.current = onCommitTiming;

  const onSnapChangeRef = useRef(onSnapChange);
  onSnapChangeRef.current = onSnapChange;

  const snapTargetsRef = useRef(snapTargets);
  snapTargetsRef.current = snapTargets;

  const startDragSession = useCallback(
    (e: React.PointerEvent, mode: TimelineDragMode) => {
      e.stopPropagation();

      // Locked layers are selectable but not movable/trimmable
      if (locked) {
        onSelectRef.current();
        return;
      }

      // Only respond to main/left mouse clicks
      if (e.button !== 0) return;

      const container = containerRef.current;
      const containerWidth = container ? container.getBoundingClientRect().width : 0;
      if (containerWidth <= 0) return;

      sessionRef.current = {
        active: true,
        mode,
        startX: e.clientX,
        startY: e.clientY,
        initStart: startTime,
        initEnd: endTime,
        dragInitiated: mode !== "move", // Trimming initiates immediately
        containerWidth,
      };

      if (mode !== "move") {
        setIsDragging(true);
        setDragMode(mode);
      }
    },
    [containerRef, startTime, endTime]
  );

  useEffect(() => {
    const handlePointerMove = (e: PointerEvent) => {
      const session = sessionRef.current;
      if (!session || !session.active) return;

      const dx = e.clientX - session.startX;
      const dy = e.clientY - session.startY;

      // Threshold check for move mode to avoid accidental drags on click
      if (session.mode === "move" && !session.dragInitiated) {
        if (Math.hypot(dx, dy) < 4) {
          return;
        }
        session.dragInitiated = true;
        setIsDragging(true);
        setDragMode("move");
      }

      const secondsPerPixel = maxDuration / Math.max(1, session.containerWidth);
      const deltaSeconds = dx * secondsPerPixel;

      let result: { start_time: number; end_time: number; snappedTarget?: number | null };
      if (session.mode === "move") {
        result = calculateMoveTiming(
          session.initStart,
          session.initEnd,
          deltaSeconds,
          maxDuration,
          snapTargetsRef.current,
          snapThreshold
        );
      } else if (session.mode === "trim_left") {
        result = calculateLeftTrimTiming(
          session.initStart,
          session.initEnd,
          deltaSeconds,
          MIN_CLIP_DURATION,
          snapTargetsRef.current,
          snapThreshold
        );
      } else {
        result = calculateRightTrimTiming(
          session.initStart,
          session.initEnd,
          deltaSeconds,
          maxDuration,
          MIN_CLIP_DURATION,
          snapTargetsRef.current,
          snapThreshold
        );
      }

      const snapVal = result.snappedTarget ?? null;
      setActiveSnapTime(snapVal);
      if (onSnapChangeRef.current) {
        onSnapChangeRef.current(snapVal);
      }

      onUpdateTimingRef.current(id, result.start_time, result.end_time);
    };

    const handlePointerUp = () => {
      const session = sessionRef.current;
      if (!session || !session.active) return;

      const wasDrag = session.dragInitiated;
      sessionRef.current = null;
      setIsDragging(false);
      setDragMode(null);
      setActiveSnapTime(null);
      if (onSnapChangeRef.current) {
        onSnapChangeRef.current(null);
      }

      if (wasDrag) {
        onCommitTimingRef.current();
      } else {
        // Pure click without significant drag
        onSelectRef.current();
      }
    };

    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointerup", handlePointerUp);
    window.addEventListener("pointercancel", handlePointerUp);

    return () => {
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("pointerup", handlePointerUp);
      window.removeEventListener("pointercancel", handlePointerUp);
    };
  }, [id, maxDuration, snapThreshold]);

  return {
    isDragging,
    dragMode,
    activeSnapTime,
    getClipProps: () => ({
      onPointerDown: (e: React.PointerEvent) => startDragSession(e, "move"),
    }),
    getLeftHandleProps: () => ({
      onPointerDown: (e: React.PointerEvent) => startDragSession(e, "trim_left"),
    }),
    getRightHandleProps: () => ({
      onPointerDown: (e: React.PointerEvent) => startDragSession(e, "trim_right"),
    }),
  };
}
