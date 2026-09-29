/**
 * Studio Layout, Section Resizing & Render Pipeline Utilities
 */

export const STUDIO_LAYOUT_CONSTRAINTS = {
  leftSidebar: {
    min: 140,
    max: 420,
    default: 176,
    storageKey: "studio_left_sidebar_width",
  },
  rightInspector: {
    min: 240,
    max: 500,
    default: 320,
    storageKey: "studio_right_inspector_width",
  },
  timeline: {
    min: 160,
    max: 550,
    default: 256,
    storageKey: "studio_timeline_height",
  },
} as const;

export function clampLeftSidebarWidth(startWidth: number, deltaX: number): number {
  const { min, max } = STUDIO_LAYOUT_CONSTRAINTS.leftSidebar;
  return Math.min(max, Math.max(min, Math.round(startWidth + deltaX)));
}

export function clampRightInspectorWidth(startWidth: number, deltaX: number): number {
  const { min, max } = STUDIO_LAYOUT_CONSTRAINTS.rightInspector;
  // Dragging left increases width (delta is startX - currentX)
  return Math.min(max, Math.max(min, Math.round(startWidth + deltaX)));
}

export function clampTimelineHeight(startHeight: number, deltaY: number): number {
  const { min, max } = STUDIO_LAYOUT_CONSTRAINTS.timeline;
  // Dragging up increases height (delta is startY - currentY)
  return Math.min(max, Math.max(min, Math.round(startHeight + deltaY)));
}

export function getStoredLayoutDimension(
  key: string,
  fallback: number,
  min: number,
  max: number,
  storage?: Storage | null
): number {
  if (!storage) return fallback;
  try {
    const raw = storage.getItem(key);
    if (!raw) return fallback;
    const parsed = parseInt(raw, 10);
    if (isNaN(parsed) || parsed < min || parsed > max) {
      return fallback;
    }
    return parsed;
  } catch {
    return fallback;
  }
}

export interface StudioRenderState {
  isRendering: boolean;
  progressPct: number;
  stage?: string;
  downloadUrl?: string;
  jobId?: string;
  error?: string;
}

export type RenderAction =
  | { type: "START_SAVE" }
  | { type: "SAVE_ERROR"; error: string }
  | { type: "QUEUED"; jobId: string }
  | { type: "PROGRESS"; progressPct: number; stage?: string; downloadUrl?: string }
  | { type: "COMPLETED"; downloadUrl?: string }
  | { type: "FAILED"; error: string }
  | { type: "CANCELLED" };

export function studioRenderReducer(
  state: StudioRenderState,
  action: RenderAction
): StudioRenderState {
  switch (action.type) {
    case "START_SAVE":
      return {
        ...state,
        isRendering: true,
        progressPct: 0,
        stage: "Saving timeline state...",
        error: undefined,
      };
    case "SAVE_ERROR":
      return {
        ...state,
        isRendering: false,
        progressPct: 0,
        stage: undefined,
        error: action.error,
      };
    case "QUEUED":
      return {
        ...state,
        isRendering: true,
        progressPct: 0,
        stage: "Queued",
        jobId: action.jobId,
        error: undefined,
      };
    case "PROGRESS":
      return {
        ...state,
        progressPct: action.progressPct,
        stage: action.stage || state.stage,
        downloadUrl: action.downloadUrl || state.downloadUrl,
      };
    case "COMPLETED":
      return {
        ...state,
        isRendering: false,
        progressPct: 100,
        stage: "Completed",
        downloadUrl: action.downloadUrl || state.downloadUrl,
        error: undefined,
      };
    case "FAILED":
      return {
        ...state,
        isRendering: false,
        stage: "Failed",
        error: action.error,
      };
    case "CANCELLED":
      return {
        ...state,
        isRendering: false,
        stage: "Cancelled",
        error: "Render job was cancelled",
      };
    default:
      return state;
  }
}
