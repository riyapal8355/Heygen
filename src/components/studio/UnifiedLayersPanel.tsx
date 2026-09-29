import React, { useState } from "react";
import {
  Layers,
  ChevronUp,
  ChevronDown,
  ChevronsUp,
  ChevronsDown,
  Eye,
  EyeOff,
  Lock,
  Unlock,
  Trash2,
  Copy,
  GripVertical,
  Film,
  ImageIcon,
  Type,
  Component,
  Sparkles,
} from "lucide-react";
import { VisualLayer } from "../../lib/studioLayerOrdering";

interface UnifiedLayersPanelProps {
  layers: VisualLayer[];
  activeSceneIndex: number;
  selectedMediaLayerId: string | null;
  selectedTextLayerId: string | null;
  selectedElementLayerId: string | null;
  selectedLayerIds?: string[];
  onSelectLayer: (layerId: string, type: string, isAdditive?: boolean) => void;
  onSelectAll?: () => void;
  onClearSelection?: () => void;
  onGroupAlign?: (alignment: "left" | "center" | "right" | "top" | "middle" | "bottom") => void;
  onGroupDistribute?: (axis: "horizontal" | "vertical") => void;
  onGroupDuplicate?: () => void;
  onGroupDelete?: () => void;
  onGroupToggleLock?: () => void;
  onGroupToggleVisibility?: () => void;
  onGroupZOrder?: (direction: "forward" | "backward" | "front" | "back") => void;
  onBringForward: (layerId: string) => void;
  onSendBackward: (layerId: string) => void;
  onBringToFront: (layerId: string) => void;
  onSendToBack: (layerId: string) => void;
  onMoveLayerToIndex: (layerId: string, toIndex: number) => void;
  onToggleEnable: (layerId: string) => void;
  onToggleLock: (layerId: string) => void;
  onDeleteLayer: (layerId: string) => void;
  onDuplicateLayer: (layerId: string) => void;
  assetUrls?: Record<string, string>;
}

export default function UnifiedLayersPanel({
  layers = [],
  activeSceneIndex,
  selectedMediaLayerId,
  selectedTextLayerId,
  selectedElementLayerId,
  selectedLayerIds = [],
  onSelectLayer,
  onSelectAll,
  onClearSelection,
  onGroupAlign,
  onGroupDistribute,
  onGroupDuplicate,
  onGroupDelete,
  onGroupToggleLock,
  onGroupToggleVisibility,
  onGroupZOrder,
  onBringForward,
  onSendBackward,
  onBringToFront,
  onSendToBack,
  onMoveLayerToIndex,
  onToggleEnable,
  onToggleLock,
  onDeleteLayer,
  onDuplicateLayer,
  assetUrls = {},
}: UnifiedLayersPanelProps) {
  const [draggedLayerId, setDraggedLayerId] = useState<string | null>(null);
  const [dragOverLayerId, setDragOverLayerId] = useState<string | null>(null);

  // Filter to visual layers
  const visualLayers = layers.filter((l) =>
    ["image", "video", "media", "text", "shape", "sticker", "element"].includes(l.type)
  );

  // In stacking order: display from TOP (highest z_index) to BOTTOM (lowest z_index = 0)
  const sortedDesc = [...visualLayers].sort((a, b) => {
    const zA = typeof a.z_index === "number" ? a.z_index : 0;
    const zB = typeof b.z_index === "number" ? b.z_index : 0;
    return zB - zA;
  });

  const getLayerIcon = (layer: VisualLayer) => {
    switch (layer.type) {
      case "video":
        return <Film size={13} className="text-purple-400" />;
      case "image":
      case "media":
        return <ImageIcon size={13} className="text-blue-400" />;
      case "text":
        return <Type size={13} className="text-emerald-400" />;
      case "shape":
        return <Component size={13} className="text-amber-400" />;
      case "sticker":
        return <Sparkles size={13} className="text-pink-400" />;
      default:
        return <Layers size={13} className="text-slate-400" />;
    }
  };

  const getLayerTypeLabel = (layer: VisualLayer) => {
    if (layer.type === "video") return "Video";
    if (layer.type === "image" || layer.type === "media") return "Image";
    if (layer.type === "text") return "Text";
    if (layer.type === "shape") return "Shape";
    if (layer.type === "sticker") return "Sticker";
    return "Layer";
  };

  const isLayerSelected = (layer: VisualLayer) => {
    if (selectedLayerIds && selectedLayerIds.length > 0) {
      return selectedLayerIds.includes(layer.id);
    }
    if (layer.type === "image" || layer.type === "video" || layer.type === "media") {
      return selectedMediaLayerId === layer.id;
    }
    if (layer.type === "text") {
      return selectedTextLayerId === layer.id;
    }
    return selectedElementLayerId === layer.id;
  };

  // Drag-and-drop reordering handlers
  const handleDragStart = (e: React.DragEvent, layerId: string) => {
    setDraggedLayerId(layerId);
    e.dataTransfer.setData("text/plain", layerId);
    e.dataTransfer.effectAllowed = "move";
  };

  const handleDragOver = (e: React.DragEvent, targetId: string) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
    if (dragOverLayerId !== targetId) {
      setDragOverLayerId(targetId);
    }
  };

  const handleDrop = (e: React.DragEvent, targetId: string) => {
    e.preventDefault();
    const sourceId = draggedLayerId || e.dataTransfer.getData("text/plain");
    setDraggedLayerId(null);
    setDragOverLayerId(null);
    if (!sourceId || sourceId === targetId) return;

    // Find target layer's z_index in ascending order
    const targetLayer = visualLayers.find((l) => l.id === targetId);
    if (!targetLayer) return;
    const targetZ = typeof targetLayer.z_index === "number" ? targetLayer.z_index : 0;

    onMoveLayerToIndex(sourceId, targetZ);
  };

  const handleDragEnd = () => {
    setDraggedLayerId(null);
    setDragOverLayerId(null);
  };

  return (
    <div className="flex flex-col h-full bg-[#0d121f] text-slate-200 select-none">
      {/* Header */}
      <div className="p-4 border-b border-[#18233a] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-blue-600/20 border border-blue-500/30 flex items-center justify-center text-blue-400">
            <Layers size={15} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-xs font-bold text-white tracking-wide uppercase">Scene Layers</h2>
              <span className="text-[10px] bg-[#1a2640] text-blue-400 font-mono px-1.5 py-0.5 rounded-full border border-blue-500/20">
                {visualLayers.length}
              </span>
            </div>
            <p className="text-[10px] text-slate-400 mt-0.5">
              Stacking Order (Top = Front, Bottom = Back)
            </p>
          </div>
        </div>

        {visualLayers.length > 0 && onSelectAll && (
          <button
            onClick={onSelectAll}
            className="text-[10px] px-2 py-1 rounded bg-[#162238] hover:bg-[#1f3152] text-blue-300 border border-blue-500/30 font-medium"
            title="Select all visual layers (Ctrl+A)"
          >
            Select All
          </button>
        )}
      </div>

      {/* Multi-Selection Group Editing Toolbar */}
      {selectedLayerIds && selectedLayerIds.length > 1 && (
        <div className="p-2.5 mx-3 mt-2 bg-blue-950/60 border border-blue-500/40 rounded-xl space-y-2">
          <div className="flex items-center justify-between text-xs">
            <span className="font-semibold text-blue-300">
              {selectedLayerIds.length} layers selected
            </span>
            {onClearSelection && (
              <button
                onClick={onClearSelection}
                className="text-[10px] text-slate-400 hover:text-white px-1.5 py-0.5 rounded bg-slate-800/60"
              >
                Deselect
              </button>
            )}
          </div>
          {/* Alignment controls */}
          {onGroupAlign && (
            <div className="flex items-center justify-between gap-1 pt-1 border-t border-blue-500/20 text-[10px]">
              <span className="text-slate-400 text-[9px] uppercase font-bold">Align:</span>
              <button onClick={() => onGroupAlign("left")} title="Align Left" className="p-1 hover:bg-blue-900/40 rounded text-slate-300 hover:text-white">Left</button>
              <button onClick={() => onGroupAlign("center")} title="Align Center" className="p-1 hover:bg-blue-900/40 rounded text-slate-300 hover:text-white">Center</button>
              <button onClick={() => onGroupAlign("right")} title="Align Right" className="p-1 hover:bg-blue-900/40 rounded text-slate-300 hover:text-white">Right</button>
              <button onClick={() => onGroupAlign("top")} title="Align Top" className="p-1 hover:bg-blue-900/40 rounded text-slate-300 hover:text-white">Top</button>
              <button onClick={() => onGroupAlign("middle")} title="Align Middle" className="p-1 hover:bg-blue-900/40 rounded text-slate-300 hover:text-white">Mid</button>
              <button onClick={() => onGroupAlign("bottom")} title="Align Bottom" className="p-1 hover:bg-blue-900/40 rounded text-slate-300 hover:text-white">Bottom</button>
            </div>
          )}
          {/* Distribution controls (Phase 45) */}
          {onGroupDistribute && (
            <div className="flex items-center justify-between gap-1 pt-1 border-t border-blue-500/20 text-[10px]">
              <span className="text-slate-400 text-[9px] uppercase font-bold">Distribute:</span>
              <div className="flex items-center gap-1">
                <button
                  disabled={selectedLayerIds.length < 3}
                  onClick={() => onGroupDistribute("horizontal")}
                  title="Distribute Horizontally (requires 3+ selected layers)"
                  className="px-2 py-0.5 hover:bg-blue-900/40 disabled:opacity-30 disabled:hover:bg-transparent rounded text-slate-300 hover:text-white"
                >
                  Horizontal
                </button>
                <button
                  disabled={selectedLayerIds.length < 3}
                  onClick={() => onGroupDistribute("vertical")}
                  title="Distribute Vertically (requires 3+ selected layers)"
                  className="px-2 py-0.5 hover:bg-blue-900/40 disabled:opacity-30 disabled:hover:bg-transparent rounded text-slate-300 hover:text-white"
                >
                  Vertical
                </button>
              </div>
            </div>
          )}
          {/* Quick group actions */}
          <div className="flex items-center justify-between gap-1 pt-1 border-t border-blue-500/20 text-[10px]">
            {onGroupToggleLock && (
              <button onClick={onGroupToggleLock} className="flex items-center gap-1 px-1.5 py-1 bg-slate-800/80 hover:bg-slate-700 rounded text-slate-300 hover:text-white" title="Toggle Lock">
                <Lock size={10} /> Lock
              </button>
            )}
            {onGroupToggleVisibility && (
              <button onClick={onGroupToggleVisibility} className="flex items-center gap-1 px-1.5 py-1 bg-slate-800/80 hover:bg-slate-700 rounded text-slate-300 hover:text-white" title="Toggle Visibility">
                <Eye size={10} /> Hide
              </button>
            )}
            {onGroupDuplicate && (
              <button onClick={onGroupDuplicate} className="flex items-center gap-1 px-1.5 py-1 bg-slate-800/80 hover:bg-slate-700 rounded text-slate-300 hover:text-white" title="Duplicate Group (Ctrl+D)">
                <Copy size={10} /> Copy
              </button>
            )}
            {onGroupDelete && (
              <button onClick={onGroupDelete} className="flex items-center gap-1 px-1.5 py-1 bg-rose-950/60 hover:bg-rose-900/80 text-rose-300 rounded" title="Delete Group (Delete)">
                <Trash2 size={10} /> Delete
              </button>
            )}
          </div>
        </div>
      )}

      {/* Layer List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-1.5">
        {sortedDesc.length === 0 ? (
          <div className="h-48 flex flex-col items-center justify-center text-center p-4 text-slate-500 border border-dashed border-[#1e2c48] rounded-xl">
            <Layers size={28} className="mb-2 opacity-40 text-slate-400" />
            <span className="text-xs font-medium text-slate-400">No Visual Layers</span>
            <span className="text-[10px] text-slate-500 mt-1 max-w-[200px]">
              Add media, text, shapes, or stickers to begin layering scene elements.
            </span>
          </div>
        ) : (
          sortedDesc.map((layer, displayIdx) => {
            const isSelected = isLayerSelected(layer);
            const isEnabled = layer.enabled !== false;
            const isLocked = layer.locked === true;
            const zIdx = typeof layer.z_index === "number" ? layer.z_index : 0;
            const isTop = zIdx === visualLayers.length - 1;
            const isBottom = zIdx === 0;
            const isDragging = draggedLayerId === layer.id;
            const isDragOver = dragOverLayerId === layer.id;

            return (
              <div
                key={layer.id}
                draggable={!isLocked}
                onDragStart={(e) => handleDragStart(e, layer.id)}
                onDragOver={(e) => handleDragOver(e, layer.id)}
                onDrop={(e) => handleDrop(e, layer.id)}
                onDragEnd={handleDragEnd}
                onClick={(e) => onSelectLayer(layer.id, layer.type, e.ctrlKey || e.metaKey || e.shiftKey)}
                className={`group relative flex items-center gap-2 p-2 rounded-xl border transition-all cursor-pointer ${
                  isSelected
                    ? "bg-[#18233d] border-blue-500/50 shadow-md shadow-blue-900/20"
                    : isDragOver
                    ? "bg-[#1e2c48] border-blue-400"
                    : "bg-[#121929] border-[#1c2842] hover:bg-[#152035] hover:border-slate-700"
                } ${isDragging ? "opacity-40" : "opacity-100"} ${
                  !isEnabled ? "opacity-60 bg-[#0e1422]" : ""
                }`}
              >
                {/* Drag Handle */}
                <div
                  className={`text-slate-600 hover:text-slate-400 p-0.5 cursor-grab active:cursor-grabbing ${
                    isLocked ? "invisible" : ""
                  }`}
                  title="Drag to reorder layer in stack"
                >
                  <GripVertical size={13} />
                </div>

                {/* Layer Icon / Type */}
                <div className="w-6 h-6 rounded-md bg-[#18243b] border border-white/5 flex items-center justify-center flex-shrink-0">
                  {getLayerIcon(layer)}
                </div>

                {/* Layer Name & Stacking Metadata */}
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-1.5">
                    <span
                      className={`text-xs font-medium truncate block ${
                        isSelected ? "text-white" : "text-slate-300"
                      }`}
                    >
                      {layer.name || getLayerTypeLabel(layer)}
                    </span>
                    <span className="text-[9px] bg-[#1a2642] text-slate-400 font-mono px-1 rounded border border-white/5 flex-shrink-0">
                      z:{zIdx}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-[9px] text-slate-500 font-mono mt-0.5">
                    <span>
                      {(layer.start_time ?? 0).toFixed(1)}s -{" "}
                      {(layer.end_time ?? 5.0).toFixed(1)}s
                    </span>
                    <span>•</span>
                    <span className="uppercase">{layer.type}</span>
                  </div>
                </div>

                {/* Quick Reorder Controls */}
                <div className="flex items-center gap-0.5 bg-[#0e1424] rounded-lg p-0.5 border border-white/5">
                  {/* Bring to Front */}
                  <button
                    disabled={isTop || isLocked}
                    onClick={(e) => {
                      e.stopPropagation();
                      onBringToFront(layer.id);
                    }}
                    className="p-1 rounded text-slate-400 hover:text-white disabled:opacity-20 disabled:hover:text-slate-400 cursor-pointer disabled:cursor-not-allowed transition-colors"
                    title="Bring to Front (Topmost)"
                  >
                    <ChevronsUp size={11} />
                  </button>

                  {/* Bring Forward */}
                  <button
                    disabled={isTop || isLocked}
                    onClick={(e) => {
                      e.stopPropagation();
                      onBringForward(layer.id);
                    }}
                    className="p-1 rounded text-slate-400 hover:text-white disabled:opacity-20 disabled:hover:text-slate-400 cursor-pointer disabled:cursor-not-allowed transition-colors"
                    title="Bring Forward (Up 1 Step)"
                  >
                    <ChevronUp size={11} />
                  </button>

                  {/* Send Backward */}
                  <button
                    disabled={isBottom || isLocked}
                    onClick={(e) => {
                      e.stopPropagation();
                      onSendBackward(layer.id);
                    }}
                    className="p-1 rounded text-slate-400 hover:text-white disabled:opacity-20 disabled:hover:text-slate-400 cursor-pointer disabled:cursor-not-allowed transition-colors"
                    title="Send Backward (Down 1 Step)"
                  >
                    <ChevronDown size={11} />
                  </button>

                  {/* Send to Back */}
                  <button
                    disabled={isBottom || isLocked}
                    onClick={(e) => {
                      e.stopPropagation();
                      onSendToBack(layer.id);
                    }}
                    className="p-1 rounded text-slate-400 hover:text-white disabled:opacity-20 disabled:hover:text-slate-400 cursor-pointer disabled:cursor-not-allowed transition-colors"
                    title="Send to Back (Bottommost)"
                  >
                    <ChevronsDown size={11} />
                  </button>
                </div>

                {/* State Toggles: Eye, Lock, Duplicate, Delete */}
                <div className="flex items-center gap-0.5">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onToggleEnable(layer.id);
                    }}
                    className={`p-1 rounded transition-colors cursor-pointer ${
                      isEnabled
                        ? "text-slate-400 hover:text-white"
                        : "text-slate-600 hover:text-slate-400"
                    }`}
                    title={isEnabled ? "Hide Layer" : "Show Layer"}
                  >
                    {isEnabled ? <Eye size={12} /> : <EyeOff size={12} />}
                  </button>

                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onToggleLock(layer.id);
                    }}
                    className={`p-1 rounded transition-colors cursor-pointer ${
                      isLocked
                        ? "text-amber-400 hover:text-amber-300"
                        : "text-slate-500 hover:text-slate-300"
                    }`}
                    title={isLocked ? "Unlock Layer" : "Lock Layer"}
                  >
                    {isLocked ? <Lock size={12} /> : <Unlock size={12} />}
                  </button>

                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onDuplicateLayer(layer.id);
                    }}
                    className="p-1 rounded text-slate-400 hover:text-white transition-colors cursor-pointer"
                    title="Duplicate Layer"
                  >
                    <Copy size={12} />
                  </button>

                  <button
                    disabled={isLocked}
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeleteLayer(layer.id);
                    }}
                    className="p-1 rounded text-slate-500 hover:text-red-400 disabled:opacity-20 disabled:hover:text-slate-500 transition-colors cursor-pointer disabled:cursor-not-allowed"
                    title={isLocked ? "Cannot delete locked layer" : "Delete Layer"}
                  >
                    <Trash2 size={12} />
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Footer shortcut hints */}
      <div className="p-3 bg-[#0a0e19] border-t border-[#18233a] text-[10px] text-slate-500 space-y-1">
        <div className="flex items-center justify-between">
          <span>Bring Forward / Backward</span>
          <span className="font-mono text-slate-400">Ctrl/Cmd + [ / ]</span>
        </div>
        <div className="flex items-center justify-between">
          <span>Bring to Front / Back</span>
          <span className="font-mono text-slate-400">Ctrl/Cmd + Shift + [ / ]</span>
        </div>
      </div>
    </div>
  );
}
