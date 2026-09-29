/**
 * Studio Keyboard Navigation & Shortcuts Utilities
 *
 * Implements pure, framework-independent helpers for:
 * 1. Focus & input element detection (guarding against shortcuts during text input).
 * 2. Active visual layer resolution across mutually exclusive selection states.
 * 3. Arrow-key nudging (normalized [0, 1] step calculations with clamping).
 * 4. Locked layer guards for keyboard mutations.
 * 5. Layer duplication and in-memory clipboard cloning.
 */

import { clamp } from "./canvasTransformUtils";
import { isLayerLocked, LockableLayer } from "./studioLockingVisibility";

export type VisualLayerKind = "media" | "text" | "element";

export interface SelectedVisualLayerResult {
  layer: LockableLayer;
  kind: VisualLayerKind;
  sceneIndex: number;
}

export interface SerializedStudioLayer {
  layer: any;
  kind: VisualLayerKind;
  timestamp: number;
}

/**
 * Focus Guard:
 * Detects whether the event target or its ancestors is an interactive text input,
 * textarea, select, contenteditable, or modal dialog that must consume keyboard input natively.
 */
export function isInputOrEditableTarget(target: any): boolean {
  if (!target || typeof target !== "object") return false;

  // Check tagName if element
  const tagName = typeof target.tagName === "string" ? target.tagName.toUpperCase() : "";
  if (tagName === "INPUT" || tagName === "TEXTAREA" || tagName === "SELECT") {
    return true;
  }

  // Check contenteditable directly
  if (target.isContentEditable === true) {
    return true;
  }

  // Check element attributes and ancestry
  if (typeof target.closest === "function") {
    try {
      if (target.closest("[contenteditable='true'], [contenteditable='']")) {
        return true;
      }
      if (target.closest("input, textarea, select")) {
        return true;
      }
      if (target.closest("[data-ignore-studio-shortcuts='true']")) {
        return true;
      }
      if (target.closest("[role='dialog']")) {
        return true;
      }
    } catch {
      // Ignore DOM selector errors defensively
    }
  }

  return false;
}

/**
 * Resolves the currently active visual layer across mutually exclusive selection states.
 */
export function getSelectedVisualLayer(
  scenes: any[],
  activeSceneIndex: number,
  selectedMediaLayerId: string | null,
  selectedTextLayerId: string | null,
  selectedElementLayerId: string | null
): SelectedVisualLayerResult | null {
  if (!Array.isArray(scenes) || scenes.length === 0) return null;
  const currentScene = scenes[activeSceneIndex];
  if (!currentScene || !Array.isArray(currentScene.layers)) return null;

  if (selectedMediaLayerId) {
    const layer = currentScene.layers.find((l: any) => l.id === selectedMediaLayerId);
    if (layer) {
      return { layer, kind: "media", sceneIndex: activeSceneIndex };
    }
  }

  if (selectedTextLayerId) {
    const layer = currentScene.layers.find((l: any) => l.id === selectedTextLayerId);
    if (layer) {
      return { layer, kind: "text", sceneIndex: activeSceneIndex };
    }
  }

  if (selectedElementLayerId) {
    const layer = currentScene.layers.find((l: any) => l.id === selectedElementLayerId);
    if (layer) {
      return { layer, kind: "element", sceneIndex: activeSceneIndex };
    }
  }

  return null;
}

/**
 * Computes new normalized coordinates for arrow-key nudging.
 *
 * Normal step: 0.005
 * Shift step:  0.05
 * Coordinates clamped to [0.0, 1.0].
 */
export function calculateKeyboardNudge(
  currentPos: { x?: number; y?: number } | undefined,
  direction: "ArrowLeft" | "ArrowRight" | "ArrowUp" | "ArrowDown",
  isShift = false
): { x: number; y: number } {
  const step = isShift ? 0.05 : 0.005;
  const currX = typeof currentPos?.x === "number" && Number.isFinite(currentPos.x) ? currentPos.x : 0.5;
  const currY = typeof currentPos?.y === "number" && Number.isFinite(currentPos.y) ? currentPos.y : 0.5;

  let newX = currX;
  let newY = currY;

  switch (direction) {
    case "ArrowLeft":
      newX = clamp(currX - step, 0.0, 1.0);
      break;
    case "ArrowRight":
      newX = clamp(currX + step, 0.0, 1.0);
      break;
    case "ArrowUp":
      newY = clamp(currY - step, 0.0, 1.0);
      break;
    case "ArrowDown":
      newY = clamp(currY + step, 0.0, 1.0);
      break;
  }

  return {
    x: Math.round(newX * 1000) / 1000,
    y: Math.round(newY * 1000) / 1000,
  };
}

/**
 * Guard checking if a layer can be mutated (nudged, resized, edited) via keyboard.
 * Locked layers MUST NOT be mutated.
 */
export function canMutateLayerViaKeyboard(layer: LockableLayer | null | undefined): boolean {
  if (!layer) return false;
  return !isLayerLocked(layer);
}

/**
 * Guard checking if a layer can be deleted via keyboard.
 * Locked layers MUST NOT be deleted via keyboard.
 */
export function canDeleteLayerViaKeyboard(layer: LockableLayer | null | undefined): boolean {
  if (!layer) return false;
  return !isLayerLocked(layer);
}

/**
 * Creates an exact duplicated layer item for Paste or Duplicate actions.
 * Generates a fresh unique ID, applies coordinate offset (+0.05, max 0.9),
 * unlocks the clone, and preserves timing and content.
 */
export function createLayerDuplicatePayload(
  layer: any,
  kind: VisualLayerKind
): { clonedLayer: any; newId: string } {
  const timestamp = Date.now();
  const randomSuffix = Math.random().toString(36).substring(2, 6);
  const prefix = kind === "media" ? "layer" : kind === "text" ? "text" : "element";
  const newId = `${prefix}_${timestamp}_${randomSuffix}`;

  // Deep clone layer
  const cloned = JSON.parse(JSON.stringify(layer));

  // Update id and name
  cloned.id = newId;
  const baseName = layer.name || (kind === "media" ? "Media Layer" : kind === "text" ? "Text Overlay" : "Element");
  cloned.name = baseName.endsWith(" (Copy)") ? baseName : `${baseName} (Copy)`;

  // Apply canonical offset convention
  const currX = typeof layer.transform?.x === "number" ? layer.transform.x : 0.5;
  const currY = typeof layer.transform?.y === "number" ? layer.transform.y : 0.5;
  cloned.transform = {
    ...(cloned.transform || {}),
    x: Math.min(0.9, Math.round((currX + 0.05) * 1000) / 1000),
    y: Math.min(0.9, Math.round((currY + 0.05) * 1000) / 1000),
    scale: layer.transform?.scale ?? 1.0,
    rotation: layer.transform?.rotation ?? 0,
  };

  // Cloned layer is unlocked by default so user can edit it
  cloned.locked = false;

  return { clonedLayer: cloned, newId };
}
