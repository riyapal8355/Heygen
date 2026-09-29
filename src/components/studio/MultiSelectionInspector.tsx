"use client";

import React, { useState } from "react";
import {
  Layers,
  Eye,
  EyeOff,
  Lock,
  LockOpen,
  Sliders,
  Move,
  RotateCw,
  Maximize2,
  Copy,
  Trash2,
  ChevronsUp,
  ChevronsDown,
  ChevronUp,
  ChevronDown,
  AlignLeft,
  AlignCenter,
  AlignRight,
  ArrowUp,
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  X,
  AlertTriangle,
} from "lucide-react";
import { VisualLayer } from "../../lib/studioLayerOrdering";
import {
  getMultiSelectionSummary,
  TransformBatchDelta,
} from "../../lib/studioMultiSelection";

interface MultiSelectionInspectorProps {
  layers: VisualLayer[];
  selectedLayerIds: string[];
  onBatchUpdateOpacity: (opacity: number) => void;
  onBatchUpdateVisibility: (enabled: boolean) => void;
  onBatchUpdateLock: (locked: boolean) => void;
  onBatchApplyTransformDelta: (delta: TransformBatchDelta) => void;
  onGroupAlign?: (alignment: "left" | "center" | "right" | "top" | "middle" | "bottom") => void;
  onGroupDistribute?: (axis: "horizontal" | "vertical") => void;
  onGroupDuplicate?: () => void;
  onGroupDelete?: () => void;
  onGroupZOrder?: (direction: "forward" | "backward" | "front" | "back") => void;
  onClearSelection?: () => void;
}

export default function MultiSelectionInspector({
  layers,
  selectedLayerIds,
  onBatchUpdateOpacity,
  onBatchUpdateVisibility,
  onBatchUpdateLock,
  onBatchApplyTransformDelta,
  onGroupAlign,
  onGroupDistribute,
  onGroupDuplicate,
  onGroupDelete,
  onGroupZOrder,
  onClearSelection,
}: MultiSelectionInspectorProps) {
  const summary = getMultiSelectionSummary(layers, selectedLayerIds);
  const [localOpacity, setLocalOpacity] = useState<number | null>(null);

  // If local preview is active, show it; otherwise summary value
  const displayOpacity =
    localOpacity !== null
      ? localOpacity
      : summary.opacityState.value !== null
      ? Math.round(summary.opacityState.value * 100)
      : null;

  return (
    <div className="space-y-4 text-slate-200 select-none pb-8">
      {/* 1. SELECTION SUMMARY HEADER */}
      <div className="p-3 bg-gradient-to-r from-blue-950/80 to-[#10192e] border border-blue-500/30 rounded-xl space-y-1.5 shadow-md">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5 text-blue-300">
            <Layers size={14} className="text-blue-400" />
            <span className="text-xs font-bold uppercase tracking-wider text-white">
              {summary.count} layers selected
            </span>
          </div>
          {onClearSelection && (
            <button
              onClick={onClearSelection}
              className="text-[10px] text-slate-400 hover:text-white px-2 py-0.5 rounded bg-slate-800/80 hover:bg-slate-700 transition-colors flex items-center gap-1"
              title="Clear selection (Escape)"
            >
              <X size={10} /> Deselect
            </button>
          )}
        </div>

        {/* Type composition tags */}
        <div className="flex flex-wrap gap-1 pt-1">
          {Object.entries(summary.typeCounts).map(([type, count]) => (
            <span
              key={type}
              className="text-[10px] bg-blue-900/40 text-blue-200 font-medium px-2 py-0.5 rounded-full border border-blue-500/20"
            >
              {count} {type}
            </span>
          ))}
        </div>
      </div>

      {/* 2. LOCKED STATE BANNER */}
      {summary.allLocked ? (
        <div className="flex items-center gap-2 p-2.5 bg-amber-950/50 border border-amber-600/40 rounded-xl text-amber-300 text-[11px]">
          <AlertTriangle size={14} className="flex-shrink-0 text-amber-400" />
          <span className="font-semibold">
            All selected layers are locked. Transform and opacity edits are disabled.
          </span>
        </div>
      ) : summary.anyLocked ? (
        <div className="flex items-center gap-2 p-2 bg-amber-950/30 border border-amber-700/30 rounded-lg text-amber-300 text-[10px]">
          <Lock size={11} className="flex-shrink-0" />
          <span>
            {summary.lockState.lockedCount} locked layer(s) will be protected from edits.
          </span>
        </div>
      ) : null}

      {/* 3. BATCH LOCK & VISIBILITY CONTROLS */}
      <div className="p-3 bg-[#101626] border border-[#1a2640] rounded-xl space-y-2">
        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
          State & Visibility
        </span>
        <div className="grid grid-cols-2 gap-2 text-xs">
          {/* Lock / Unlock */}
          <button
            onClick={() => onBatchUpdateLock(!summary.allLocked)}
            className={`flex items-center justify-center gap-1.5 py-1.5 px-2 rounded-lg border text-xs font-medium transition-all ${
              summary.allLocked
                ? "bg-amber-950/60 border-amber-600/50 text-amber-300 hover:bg-amber-900/60"
                : summary.lockState.isMixed
                ? "bg-amber-950/30 border-amber-800/40 text-amber-200 hover:bg-amber-900/40"
                : "bg-[#141d33] border-[#1f2c4c] text-slate-300 hover:text-white hover:border-slate-500"
            }`}
            title="Batch toggle lock status for selected layers"
          >
            {summary.allLocked ? <Lock size={12} /> : <LockOpen size={12} />}
            <span>
              {summary.allLocked
                ? "Unlock All"
                : summary.lockState.isMixed
                ? `Mixed (${summary.lockState.lockedCount} Locked)`
                : "Lock All"}
            </span>
          </button>

          {/* Visibility Show / Hide */}
          <button
            onClick={() => onBatchUpdateVisibility(summary.visibilityState.allVisible ? false : true)}
            className={`flex items-center justify-center gap-1.5 py-1.5 px-2 rounded-lg border text-xs font-medium transition-all ${
              !summary.visibilityState.allVisible && !summary.visibilityState.isMixed
                ? "bg-slate-800/80 border-slate-600/50 text-slate-400 hover:text-white"
                : summary.visibilityState.isMixed
                ? "bg-blue-950/40 border-blue-700/40 text-blue-200 hover:bg-blue-900/40"
                : "bg-[#141d33] border-[#1f2c4c] text-slate-300 hover:text-white hover:border-slate-500"
            }`}
            title="Batch toggle visibility for selected layers"
          >
            {summary.visibilityState.allVisible ? <Eye size={12} /> : <EyeOff size={12} />}
            <span>
              {summary.visibilityState.allVisible
                ? "Hide All"
                : summary.visibilityState.isMixed
                ? "Mixed Visible"
                : "Show All"}
            </span>
          </button>
        </div>
      </div>

      {/* 4. OPACITY BATCH EDITING */}
      <div className="p-3 bg-[#101626] border border-[#1a2640] rounded-xl space-y-2.5">
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1">
            <Sliders size={11} className="text-blue-400" /> Batch Opacity
          </span>
          <span className="text-[10px] font-mono text-white">
            {displayOpacity !== null ? `${displayOpacity}%` : "Mixed"}
          </span>
        </div>

        {/* Range Slider */}
        <input
          type="range"
          min="0"
          max="100"
          step="5"
          disabled={summary.allLocked}
          value={displayOpacity ?? 100}
          onPointerDown={() => {
            if (displayOpacity !== null) setLocalOpacity(displayOpacity);
          }}
          onChange={(e) => {
            const val = parseInt(e.target.value, 10);
            setLocalOpacity(val);
          }}
          onPointerUp={(e) => {
            const val = parseInt((e.target as HTMLInputElement).value, 10);
            setLocalOpacity(null);
            onBatchUpdateOpacity(val / 100);
          }}
          className="w-full accent-blue-500 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
        />

        {/* Quick Presets */}
        <div className="grid grid-cols-4 gap-1 pt-1">
          {[25, 50, 75, 100].map((pct) => (
            <button
              key={pct}
              disabled={summary.allLocked}
              onClick={() => onBatchUpdateOpacity(pct / 100)}
              className="py-1 text-[10px] font-semibold bg-[#141d33] hover:bg-blue-600 disabled:opacity-30 disabled:hover:bg-[#141d33] text-slate-300 hover:text-white rounded border border-[#1f2c4c] transition-colors"
            >
              {pct}%
            </button>
          ))}
        </div>
      </div>

      {/* 5. TRANSFORM BATCH DELTAS (POSITION, SCALE, ROTATION) */}
      <div className="p-3 bg-[#101626] border border-[#1a2640] rounded-xl space-y-3">
        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1">
          <Move size={11} className="text-blue-400" /> Transform Deltas
        </span>

        {/* Relative Position Nudges */}
        <div>
          <div className="flex items-center justify-between text-[10px] text-slate-400 mb-1.5">
            <span>Position Nudge</span>
            <span className="text-[9px] text-slate-500">Preserves relative spacing</span>
          </div>
          <div className="grid grid-cols-4 gap-1.5">
            <button
              disabled={summary.allLocked}
              onClick={() => onBatchApplyTransformDelta({ dx: -0.05 })}
              className="flex items-center justify-center gap-1 py-1.5 bg-[#141d33] hover:bg-blue-600 disabled:opacity-30 text-slate-200 hover:text-white rounded text-[10px] font-medium border border-[#1f2c4c]"
              title="Nudge Left 5%"
            >
              <ArrowLeft size={11} /> -5% X
            </button>
            <button
              disabled={summary.allLocked}
              onClick={() => onBatchApplyTransformDelta({ dx: 0.05 })}
              className="flex items-center justify-center gap-1 py-1.5 bg-[#141d33] hover:bg-blue-600 disabled:opacity-30 text-slate-200 hover:text-white rounded text-[10px] font-medium border border-[#1f2c4c]"
              title="Nudge Right 5%"
            >
              <ArrowRight size={11} /> +5% X
            </button>
            <button
              disabled={summary.allLocked}
              onClick={() => onBatchApplyTransformDelta({ dy: -0.05 })}
              className="flex items-center justify-center gap-1 py-1.5 bg-[#141d33] hover:bg-blue-600 disabled:opacity-30 text-slate-200 hover:text-white rounded text-[10px] font-medium border border-[#1f2c4c]"
              title="Nudge Up 5%"
            >
              <ArrowUp size={11} /> -5% Y
            </button>
            <button
              disabled={summary.allLocked}
              onClick={() => onBatchApplyTransformDelta({ dy: 0.05 })}
              className="flex items-center justify-center gap-1 py-1.5 bg-[#141d33] hover:bg-blue-600 disabled:opacity-30 text-slate-200 hover:text-white rounded text-[10px] font-medium border border-[#1f2c4c]"
              title="Nudge Down 5%"
            >
              <ArrowDown size={11} /> +5% Y
            </button>
          </div>
        </div>

        {/* Multiplicative Scale Factors */}
        <div>
          <div className="flex items-center justify-between text-[10px] text-slate-400 mb-1.5">
            <span className="flex items-center gap-1">
              <Maximize2 size={10} /> Multiplicative Scale
            </span>
            <span className="text-[9px] text-slate-500">
              {summary.transformState.isScaleMixed ? "Mixed Scales" : "Scales proportional"}
            </span>
          </div>
          <div className="grid grid-cols-4 gap-1.5">
            <button
              disabled={summary.allLocked}
              onClick={() => onBatchApplyTransformDelta({ scaleMult: 0.8 })}
              className="py-1 bg-[#141d33] hover:bg-blue-600 disabled:opacity-30 text-slate-200 hover:text-white rounded text-[10px] font-medium border border-[#1f2c4c]"
              title="Scale down to 80%"
            >
              ×0.80
            </button>
            <button
              disabled={summary.allLocked}
              onClick={() => onBatchApplyTransformDelta({ scaleMult: 0.9 })}
              className="py-1 bg-[#141d33] hover:bg-blue-600 disabled:opacity-30 text-slate-200 hover:text-white rounded text-[10px] font-medium border border-[#1f2c4c]"
              title="Scale down to 90%"
            >
              ×0.90
            </button>
            <button
              disabled={summary.allLocked}
              onClick={() => onBatchApplyTransformDelta({ scaleMult: 1.1 })}
              className="py-1 bg-[#141d33] hover:bg-blue-600 disabled:opacity-30 text-slate-200 hover:text-white rounded text-[10px] font-medium border border-[#1f2c4c]"
              title="Scale up to 110%"
            >
              ×1.10
            </button>
            <button
              disabled={summary.allLocked}
              onClick={() => onBatchApplyTransformDelta({ scaleMult: 1.25 })}
              className="py-1 bg-[#141d33] hover:bg-blue-600 disabled:opacity-30 text-slate-200 hover:text-white rounded text-[10px] font-medium border border-[#1f2c4c]"
              title="Scale up to 125%"
            >
              ×1.25
            </button>
          </div>
        </div>

        {/* Additive Rotation Deltas */}
        <div>
          <div className="flex items-center justify-between text-[10px] text-slate-400 mb-1.5">
            <span className="flex items-center gap-1">
              <RotateCw size={10} /> Additive Rotation
            </span>
            <span className="text-[9px] text-slate-500">
              {summary.transformState.isRotationMixed ? "Mixed Angles" : "Relative Angles"}
            </span>
          </div>
          <div className="grid grid-cols-4 gap-1.5">
            <button
              disabled={summary.allLocked}
              onClick={() => onBatchApplyTransformDelta({ dRotation: -90 })}
              className="py-1 bg-[#141d33] hover:bg-blue-600 disabled:opacity-30 text-slate-200 hover:text-white rounded text-[10px] font-medium border border-[#1f2c4c]"
              title="Rotate counter-clockwise 90°"
            >
              -90°
            </button>
            <button
              disabled={summary.allLocked}
              onClick={() => onBatchApplyTransformDelta({ dRotation: -15 })}
              className="py-1 bg-[#141d33] hover:bg-blue-600 disabled:opacity-30 text-slate-200 hover:text-white rounded text-[10px] font-medium border border-[#1f2c4c]"
              title="Rotate counter-clockwise 15°"
            >
              -15°
            </button>
            <button
              disabled={summary.allLocked}
              onClick={() => onBatchApplyTransformDelta({ dRotation: 15 })}
              className="py-1 bg-[#141d33] hover:bg-blue-600 disabled:opacity-30 text-slate-200 hover:text-white rounded text-[10px] font-medium border border-[#1f2c4c]"
              title="Rotate clockwise 15°"
            >
              +15°
            </button>
            <button
              disabled={summary.allLocked}
              onClick={() => onBatchApplyTransformDelta({ dRotation: 90 })}
              className="py-1 bg-[#141d33] hover:bg-blue-600 disabled:opacity-30 text-slate-200 hover:text-white rounded text-[10px] font-medium border border-[#1f2c4c]"
              title="Rotate clockwise 90°"
            >
              +90°
            </button>
          </div>
        </div>
      </div>

      {/* 6. ALIGNMENT CONTROLS */}
      {onGroupAlign && (
        <div className="p-3 bg-[#101626] border border-[#1a2640] rounded-xl space-y-2">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
            Group Alignment
          </span>
          <div className="grid grid-cols-3 gap-1.5">
            <button
              disabled={summary.unlockedCount < 2}
              onClick={() => onGroupAlign("left")}
              className="py-1.5 px-2 bg-[#141d33] hover:bg-blue-600 disabled:opacity-30 disabled:hover:bg-[#141d33] text-slate-200 hover:text-white rounded text-[10px] font-medium border border-[#1f2c4c] transition-colors"
              title="Align Left"
            >
              Left
            </button>
            <button
              disabled={summary.unlockedCount < 2}
              onClick={() => onGroupAlign("center")}
              className="py-1.5 px-2 bg-[#141d33] hover:bg-blue-600 disabled:opacity-30 disabled:hover:bg-[#141d33] text-slate-200 hover:text-white rounded text-[10px] font-medium border border-[#1f2c4c] transition-colors"
              title="Align Center"
            >
              Center
            </button>
            <button
              disabled={summary.unlockedCount < 2}
              onClick={() => onGroupAlign("right")}
              className="py-1.5 px-2 bg-[#141d33] hover:bg-blue-600 disabled:opacity-30 disabled:hover:bg-[#141d33] text-slate-200 hover:text-white rounded text-[10px] font-medium border border-[#1f2c4c] transition-colors"
              title="Align Right"
            >
              Right
            </button>
            <button
              disabled={summary.unlockedCount < 2}
              onClick={() => onGroupAlign("top")}
              className="py-1.5 px-2 bg-[#141d33] hover:bg-blue-600 disabled:opacity-30 disabled:hover:bg-[#141d33] text-slate-200 hover:text-white rounded text-[10px] font-medium border border-[#1f2c4c] transition-colors"
              title="Align Top"
            >
              Top
            </button>
            <button
              disabled={summary.unlockedCount < 2}
              onClick={() => onGroupAlign("middle")}
              className="py-1.5 px-2 bg-[#141d33] hover:bg-blue-600 disabled:opacity-30 disabled:hover:bg-[#141d33] text-slate-200 hover:text-white rounded text-[10px] font-medium border border-[#1f2c4c] transition-colors"
              title="Align Middle"
            >
              Middle
            </button>
            <button
              disabled={summary.unlockedCount < 2}
              onClick={() => onGroupAlign("bottom")}
              className="py-1.5 px-2 bg-[#141d33] hover:bg-blue-600 disabled:opacity-30 disabled:hover:bg-[#141d33] text-slate-200 hover:text-white rounded text-[10px] font-medium border border-[#1f2c4c] transition-colors"
              title="Align Bottom"
            >
              Bottom
            </button>
          </div>
        </div>
      )}

      {/* 7. DISTRIBUTION CONTROLS (PHASE 45) */}
      {onGroupDistribute && (
        <div className="p-3 bg-[#101626] border border-[#1a2640] rounded-xl space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
              Group Distribution
            </span>
            <span className="text-[9px] text-slate-500">
              {summary.unlockedCount < 3 ? "Requires 3+ unlocked layers" : "Equal spacing"}
            </span>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <button
              disabled={summary.unlockedCount < 3}
              onClick={() => onGroupDistribute("horizontal")}
              className="py-2 px-2.5 bg-[#141d33] hover:bg-blue-600 disabled:opacity-30 disabled:hover:bg-[#141d33] text-slate-200 hover:text-white rounded-lg text-xs font-semibold border border-[#1f2c4c] transition-all flex items-center justify-center gap-1.5"
              title="Distribute Horizontally (evenly spaces 3+ layers between outer bounds)"
            >
              <span>Distribute Horizontally</span>
            </button>
            <button
              disabled={summary.unlockedCount < 3}
              onClick={() => onGroupDistribute("vertical")}
              className="py-2 px-2.5 bg-[#141d33] hover:bg-blue-600 disabled:opacity-30 disabled:hover:bg-[#141d33] text-slate-200 hover:text-white rounded-lg text-xs font-semibold border border-[#1f2c4c] transition-all flex items-center justify-center gap-1.5"
              title="Distribute Vertically (evenly spaces 3+ layers between outer bounds)"
            >
              <span>Distribute Vertically</span>
            </button>
          </div>
        </div>
      )}

      {/* 8. Z-ORDER & STACKING */}
      {onGroupZOrder && (
        <div className="p-3 bg-[#101626] border border-[#1a2640] rounded-xl space-y-2">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
            Layer Stacking (Z-Order)
          </span>
          <div className="grid grid-cols-4 gap-1.5">
            <button
              disabled={summary.anyLocked}
              onClick={() => onGroupZOrder("front")}
              className="py-1.5 px-1 bg-[#141d33] hover:bg-blue-600 disabled:opacity-30 disabled:hover:bg-[#141d33] text-slate-300 hover:text-white rounded text-[10px] font-medium border border-[#1f2c4c] flex flex-col items-center gap-0.5"
              title="Bring To Front"
            >
              <ChevronsUp size={12} />
              <span>To Front</span>
            </button>
            <button
              disabled={summary.anyLocked}
              onClick={() => onGroupZOrder("forward")}
              className="py-1.5 px-1 bg-[#141d33] hover:bg-blue-600 disabled:opacity-30 disabled:hover:bg-[#141d33] text-slate-300 hover:text-white rounded text-[10px] font-medium border border-[#1f2c4c] flex flex-col items-center gap-0.5"
              title="Bring Forward"
            >
              <ChevronUp size={12} />
              <span>Forward</span>
            </button>
            <button
              disabled={summary.anyLocked}
              onClick={() => onGroupZOrder("backward")}
              className="py-1.5 px-1 bg-[#141d33] hover:bg-blue-600 disabled:opacity-30 disabled:hover:bg-[#141d33] text-slate-300 hover:text-white rounded text-[10px] font-medium border border-[#1f2c4c] flex flex-col items-center gap-0.5"
              title="Send Backward"
            >
              <ChevronDown size={12} />
              <span>Backward</span>
            </button>
            <button
              disabled={summary.anyLocked}
              onClick={() => onGroupZOrder("back")}
              className="py-1.5 px-1 bg-[#141d33] hover:bg-blue-600 disabled:opacity-30 disabled:hover:bg-[#141d33] text-slate-300 hover:text-white rounded text-[10px] font-medium border border-[#1f2c4c] flex flex-col items-center gap-0.5"
              title="Send To Back"
            >
              <ChevronsDown size={12} />
              <span>To Back</span>
            </button>
          </div>
        </div>
      )}

      {/* 9. GROUP DUPLICATE & DELETE */}
      <div className="pt-2 flex items-center gap-2">
        {onGroupDuplicate && (
          <button
            disabled={summary.allLocked}
            onClick={onGroupDuplicate}
            className="flex-1 py-2 px-3 bg-[#152138] hover:bg-blue-600 disabled:opacity-30 text-blue-200 hover:text-white rounded-xl text-xs font-semibold border border-blue-500/30 transition-all flex items-center justify-center gap-1.5 shadow-sm"
            title="Duplicate Group (Ctrl+D)"
          >
            <Copy size={13} /> Duplicate ({summary.unlockedCount})
          </button>
        )}
        {onGroupDelete && (
          <button
            disabled={summary.allLocked}
            onClick={onGroupDelete}
            className="flex-1 py-2 px-3 bg-rose-950/60 hover:bg-rose-900/80 disabled:opacity-30 text-rose-300 hover:text-white rounded-xl text-xs font-semibold border border-rose-800/40 transition-all flex items-center justify-center gap-1.5 shadow-sm"
            title="Delete Group (Delete)"
          >
            <Trash2 size={13} /> Delete ({summary.unlockedCount})
          </button>
        )}
      </div>
    </div>
  );
}
