"use client";

import React, { useRef, useState, useCallback, useEffect } from "react";
import { RotateCw, Lock } from "lucide-react";
import {
  Point2D,
  RectDimensions,
  LayerTransformState,
  calculatePositionFromPointer,
  calculateScaleFromPointer,
  calculateRotationFromPointer,
  getPointerAngleFromCenter,
  distance,
} from "@/lib/canvasTransformUtils";
import {
  calculateCanvasSnap,
  calculateResizeSnap,
  SnapTargetLayer,
  AlignmentGuide,
  DEFAULT_SNAP_THRESHOLD,
  DEFAULT_ROTATION_SNAP_INCREMENT,
} from "@/lib/studioCanvasSnapping";

export interface CanvasTransformGizmoProps {
  layerId: string;
  transform: {
    x?: number;
    y?: number;
    scale?: number;
    rotation?: number;
  };
  canvasRef: React.RefObject<HTMLDivElement | null>;
  onTransformChange: (changes: Partial<LayerTransformState>) => void;
  onTransformCommit: () => void;
  isActive?: boolean;
  /** When true, all pointer interaction is suppressed; the gizmo renders in locked state. */
  locked?: boolean;
  /** Effective layer bounds (width, height in [0, 1]) for magnetic edge snapping */
  layerBounds?: { width: number; height: number };
  /** Neighbor layers in active scene to snap against */
  neighborLayers?: SnapTargetLayer[];
  /** Emits active alignment guides during move/resize gestures */
  onSnapGuidesChange?: (guides: AlignmentGuide[]) => void;
  /** Enable or disable magnetic snapping (default true) */
  snapEnabled?: boolean;
  /** Snap threshold in normalized canvas units (default 0.02) */
  snapThreshold?: number;
}

type DragMode = "none" | "move" | "resize" | "rotate";
type CornerHandle = "tl" | "tr" | "br" | "bl";

export default function CanvasTransformGizmo({
  layerId,
  transform,
  canvasRef,
  onTransformChange,
  onTransformCommit,
  isActive = true,
  locked = false,
  layerBounds,
  neighborLayers,
  onSnapGuidesChange,
  snapEnabled = true,
  snapThreshold = DEFAULT_SNAP_THRESHOLD,
}: CanvasTransformGizmoProps) {
  const [dragMode, setDragMode] = useState<DragMode>("none");
  const [activeCorner, setActiveCorner] = useState<CornerHandle | null>(null);

  const snapPropsRef = useRef({
    layerBounds,
    neighborLayers,
    onSnapGuidesChange,
    snapEnabled,
    snapThreshold,
    curX: transform.x ?? 0.5,
    curY: transform.y ?? 0.5,
  });
  useEffect(() => {
    snapPropsRef.current = {
      layerBounds,
      neighborLayers,
      onSnapGuidesChange,
      snapEnabled,
      snapThreshold,
      curX: transform.x ?? 0.5,
      curY: transform.y ?? 0.5,
    };
  });

  // Gesture tracking refs
  const gestureStateRef = useRef<{
    dragMode: DragMode;
    corner: CornerHandle | null;
    startPointer: Point2D;
    startTransform: LayerTransformState;
    canvasRect: RectDimensions;
    layerCenter: Point2D;
    startAngle: number;
    hasMoved: boolean;
    pointerId: number | null;
  }>({
    dragMode: "none",
    corner: null,
    startPointer: { x: 0, y: 0 },
    startTransform: { x: 0.5, y: 0.5, scale: 1.0, rotation: 0.0 },
    canvasRect: { width: 1, height: 1 },
    layerCenter: { x: 0, y: 0 },
    startAngle: 0,
    hasMoved: false,
    pointerId: null,
  });

  const curX = transform.x ?? 0.5;
  const curY = transform.y ?? 0.5;
  const curScale = transform.scale ?? 1.0;
  const curRotation = transform.rotation ?? 0.0;

  // Helper to measure canvas container rect
  const getCanvasDimensions = useCallback((): { rect: RectDimensions; center: Point2D } => {
    if (!canvasRef.current) {
      return {
        rect: { width: 800, height: 450 },
        center: { x: 400, y: 225 },
      };
    }
    const domRect = canvasRef.current.getBoundingClientRect();
    const width = domRect.width > 0 ? domRect.width : 800;
    const height = domRect.height > 0 ? domRect.height : 450;

    const centerX = domRect.left + width * curX;
    const centerY = domRect.top + height * curY;

    return {
      rect: { width, height },
      center: { x: centerX, y: centerY },
    };
  }, [canvasRef, curX, curY]);

  // --------------------------------------------------------------------------
  // POINTER DOWN HANDLERS
  // --------------------------------------------------------------------------

  // 1. Move pointer down (dragging layer body)
  const handleMovePointerDown = (e: React.PointerEvent) => {
    // Left mouse button or primary touch only
    if (e.button !== 0) return;
    if (locked) return;
    e.stopPropagation();

    const { rect, center } = getCanvasDimensions();
    const target = e.currentTarget as HTMLElement;
    target.setPointerCapture(e.pointerId);

    gestureStateRef.current = {
      dragMode: "move",
      corner: null,
      startPointer: { x: e.clientX, y: e.clientY },
      startTransform: {
        x: curX,
        y: curY,
        scale: curScale,
        rotation: curRotation,
      },
      canvasRect: rect,
      layerCenter: center,
      startAngle: 0,
      hasMoved: false,
      pointerId: e.pointerId,
    };

    setDragMode("move");
  };

  // 2. Corner resize pointer down
  const handleResizePointerDown = (corner: CornerHandle, e: React.PointerEvent) => {
    if (e.button !== 0) return;
    if (locked) return;
    e.stopPropagation();

    const { rect, center } = getCanvasDimensions();
    const target = e.currentTarget as HTMLElement;
    target.setPointerCapture(e.pointerId);

    gestureStateRef.current = {
      dragMode: "resize",
      corner,
      startPointer: { x: e.clientX, y: e.clientY },
      startTransform: {
        x: curX,
        y: curY,
        scale: curScale,
        rotation: curRotation,
      },
      canvasRect: rect,
      layerCenter: center,
      startAngle: 0,
      hasMoved: false,
      pointerId: e.pointerId,
    };

    setDragMode("resize");
    setActiveCorner(corner);
  };

  // 3. Rotation pointer down
  const handleRotatePointerDown = (e: React.PointerEvent) => {
    if (e.button !== 0) return;
    if (locked) return;
    e.stopPropagation();

    const { rect, center } = getCanvasDimensions();
    const target = e.currentTarget as HTMLElement;
    target.setPointerCapture(e.pointerId);

    const startPointer = { x: e.clientX, y: e.clientY };
    const startAngle = getPointerAngleFromCenter(startPointer, center);

    gestureStateRef.current = {
      dragMode: "rotate",
      corner: null,
      startPointer,
      startTransform: {
        x: curX,
        y: curY,
        scale: curScale,
        rotation: curRotation,
      },
      canvasRect: rect,
      layerCenter: center,
      startAngle,
      hasMoved: false,
      pointerId: e.pointerId,
    };

    setDragMode("rotate");
  };

  // --------------------------------------------------------------------------
  // POINTER MOVE & UP (WINDOW-LEVEL FOR RESILIENCE)
  // --------------------------------------------------------------------------
  useEffect(() => {
    const handleWindowPointerMove = (e: PointerEvent) => {
      const state = gestureStateRef.current;
      if (state.dragMode === "none") return;

      const currentPointer = { x: e.clientX, y: e.clientY };

      // Movement threshold (2px) to prevent tiny accidental jitter
      if (!state.hasMoved) {
        if (distance(state.startPointer, currentPointer) > 2) {
          state.hasMoved = true;
        } else {
          return;
        }
      }

      e.preventDefault();

      if (state.dragMode === "move") {
        const rawPos = calculatePositionFromPointer(
          { x: state.startTransform.x, y: state.startTransform.y },
          state.startPointer,
          currentPointer,
          state.canvasRect
        );
        const { snapEnabled, layerBounds, neighborLayers, snapThreshold, onSnapGuidesChange } = snapPropsRef.current;
        if (snapEnabled) {
          const snapRes = calculateCanvasSnap(
            rawPos,
            layerBounds || { width: 0.2, height: 0.2 },
            neighborLayers,
            snapThreshold
          );
          onTransformChange({ x: snapRes.x, y: snapRes.y });
          onSnapGuidesChange?.(snapRes.guides);
        } else {
          onTransformChange({ x: rawPos.x, y: rawPos.y });
          onSnapGuidesChange?.([]);
        }
      } else if (state.dragMode === "resize") {
        const rawScale = calculateScaleFromPointer(
          state.startTransform.scale,
          state.startPointer,
          currentPointer,
          state.layerCenter,
          0.2,
          3.0
        );
        const { snapEnabled, layerBounds, snapThreshold, onSnapGuidesChange, curX, curY } = snapPropsRef.current;
        if (snapEnabled && state.corner) {
          const resizeRes = calculateResizeSnap(
            rawScale,
            { x: curX, y: curY },
            layerBounds || { width: 0.2, height: 0.2 },
            state.corner,
            snapThreshold
          );
          onTransformChange({ scale: resizeRes.scale });
          onSnapGuidesChange?.(resizeRes.guides);
        } else {
          onTransformChange({ scale: rawScale });
          onSnapGuidesChange?.([]);
        }
      } else if (state.dragMode === "rotate") {
        const snapIncrement = e.shiftKey ? DEFAULT_ROTATION_SNAP_INCREMENT : undefined;
        const newRotation = calculateRotationFromPointer(
          state.startTransform.rotation,
          state.startAngle,
          currentPointer,
          state.layerCenter,
          snapIncrement
        );
        onTransformChange({ rotation: newRotation });
      }
    };

    const handleWindowPointerUp = (e: PointerEvent) => {
      const state = gestureStateRef.current;
      if (state.dragMode === "none") return;

      snapPropsRef.current.onSnapGuidesChange?.([]);

      if (state.hasMoved) {
        onTransformCommit();
      }

      gestureStateRef.current = {
        dragMode: "none",
        corner: null,
        startPointer: { x: 0, y: 0 },
        startTransform: { x: 0.5, y: 0.5, scale: 1.0, rotation: 0.0 },
        canvasRect: { width: 1, height: 1 },
        layerCenter: { x: 0, y: 0 },
        startAngle: 0,
        hasMoved: false,
        pointerId: null,
      };

      setDragMode("none");
      setActiveCorner(null);
    };

    window.addEventListener("pointermove", handleWindowPointerMove, { passive: false });
    window.addEventListener("pointerup", handleWindowPointerUp);
    window.addEventListener("pointercancel", handleWindowPointerUp);

    return () => {
      window.removeEventListener("pointermove", handleWindowPointerMove);
      window.removeEventListener("pointerup", handleWindowPointerUp);
      window.removeEventListener("pointercancel", handleWindowPointerUp);
    };
  }, [onTransformChange, onTransformCommit]);

  if (!isActive) return null;

  return (
    <div
      className="absolute -inset-1.5 pointer-events-none z-30 select-none"
      style={{
        boxSizing: "border-box",
      }}
    >
      {/* 1. SELECTION BOUNDING BOX BORDER */}
      <div
        onPointerDown={handleMovePointerDown}
        className={`absolute inset-0 border-2 rounded-lg pointer-events-auto transition-colors ${
          locked
            ? "border-amber-400 cursor-not-allowed"
            : dragMode === "move"
            ? "border-blue-400 bg-blue-500/10 cursor-grabbing shadow-lg shadow-blue-500/20"
            : "border-blue-500 hover:border-blue-400 cursor-move"
        }`}
        title={locked ? "Layer is locked — unlock it to move" : "Click and drag to move layer"}
      />

      {/* 2. LOCK INDICATOR BADGE (WHEN LOCKED) */}
      {locked && (
        <div
          className="absolute -top-3 -right-3 bg-amber-500 text-slate-950 p-1 rounded-full shadow-md z-50 pointer-events-none flex items-center justify-center border border-amber-300 ring-2 ring-amber-400/40"
          title="Layer is locked — direct manipulation disabled"
        >
          <Lock size={11} strokeWidth={2.5} />
        </div>
      )}

      {/* 3. MANIPULATION HANDLES (HIDDEN/DISABLED WHEN LOCKED) */}
      {!locked && (
        <>
          {/* TOP ROTATION STEM & HANDLE */}
          <div className="absolute -top-7 left-1/2 -translate-x-1/2 flex flex-col items-center pointer-events-auto z-40">
            {/* Rotation Knob */}
            <div
              onPointerDown={handleRotatePointerDown}
              className={`w-5 h-5 rounded-full bg-white border-2 shadow-md flex items-center justify-center transition-transform border-blue-600 hover:scale-125 cursor-grab active:cursor-grabbing ${
                dragMode === "rotate" ? "scale-125 bg-blue-50 ring-2 ring-blue-400" : ""
              }`}
              title="Drag to rotate layer"
            >
              <RotateCw size={10} className="text-blue-600" />
            </div>
            {/* Vertical Stem Line */}
            <div className="w-0.5 h-2 bg-blue-500" />
          </div>

          {/* FOUR CORNER RESIZE HANDLES */}
          {/* Top-Left */}
          <div
            onPointerDown={(e) => handleResizePointerDown("tl", e)}
            className={`absolute -top-1.5 -left-1.5 w-3 h-3 bg-white border-2 rounded-xs shadow-sm pointer-events-auto transition-transform border-blue-600 cursor-nwse-resize hover:scale-125 ${
              dragMode === "resize" && activeCorner === "tl" ? "scale-125 bg-blue-100" : ""
            }`}
            title="Drag corner to resize layer proportionally"
          />

          {/* Top-Right */}
          <div
            onPointerDown={(e) => handleResizePointerDown("tr", e)}
            className={`absolute -top-1.5 -right-1.5 w-3 h-3 bg-white border-2 rounded-xs shadow-sm pointer-events-auto transition-transform border-blue-600 cursor-nesw-resize hover:scale-125 ${
              dragMode === "resize" && activeCorner === "tr" ? "scale-125 bg-blue-100" : ""
            }`}
            title="Drag corner to resize layer proportionally"
          />

          {/* Bottom-Right */}
          <div
            onPointerDown={(e) => handleResizePointerDown("br", e)}
            className={`absolute -bottom-1.5 -right-1.5 w-3 h-3 bg-white border-2 rounded-xs shadow-sm pointer-events-auto transition-transform border-blue-600 cursor-nwse-resize hover:scale-125 ${
              dragMode === "resize" && activeCorner === "br" ? "scale-125 bg-blue-100" : ""
            }`}
            title="Drag corner to resize layer proportionally"
          />

          {/* Bottom-Left */}
          <div
            onPointerDown={(e) => handleResizePointerDown("bl", e)}
            className={`absolute -bottom-1.5 -left-1.5 w-3 h-3 bg-white border-2 rounded-xs shadow-sm pointer-events-auto transition-transform border-blue-600 cursor-nesw-resize hover:scale-125 ${
              dragMode === "resize" && activeCorner === "bl" ? "scale-125 bg-blue-100" : ""
            }`}
            title="Drag corner to resize layer proportionally"
          />
        </>
      )}
    </div>
  );
}
