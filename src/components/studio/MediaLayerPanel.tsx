"use client";

import React, { useState } from "react";
import {
  Image as ImageIcon,
  Film,
  Plus,
  Trash2,
  Copy,
  Eye,
  EyeOff,
  Lock,
  LockOpen,
  AlertCircle,
  Sliders,
  Move,
  RotateCw,
  ChevronUp,
  ChevronDown,
} from "lucide-react";
import { StudioScene } from "./VidoAIStudio";
import {
  bringLayerForward,
  sendLayerBackward,
  duplicateLayerWithZIndex,
  deleteLayerWithZIndex,
} from "../../lib/studioLayerOrdering";

export interface MediaLayerItem {
  id: string;
  type: string; // "image" | "video" | "media"
  name?: string;
  start_time: number;
  end_time: number;
  enabled?: boolean;
  locked?: boolean;
  z_index?: number;
  transform?: {
    x?: number;
    y?: number;
    scale?: number;
    rotation?: number;
  };
  content?: {
    asset_id?: string;
    media_type?: string;
    name?: string;
    opacity?: number;
    [key: string]: any;
  };
}

interface MediaLayerPanelProps {
  scenes: StudioScene[];
  activeSceneIndex: number;
  onSelectScene: (idx: number) => void;
  selectedMediaLayerId: string | null;
  onSelectMediaLayer: (id: string | null) => void;
  onUpdateMediaLayers: (sceneIndex: number, layers: any[]) => void;
  onOpenMediaLibrary: () => void;
  assetUrls?: Record<string, string>;
}

const POSITION_PRESETS = [
  { label: "Top Left", x: 0.2, y: 0.2, key: "top-left" },
  { label: "Top", x: 0.5, y: 0.2, key: "top" },
  { label: "Top Right", x: 0.8, y: 0.2, key: "top-right" },
  { label: "Center Left", x: 0.2, y: 0.5, key: "center-left" },
  { label: "Center", x: 0.5, y: 0.5, key: "center" },
  { label: "Center Right", x: 0.8, y: 0.5, key: "center-right" },
  { label: "Bottom Left", x: 0.2, y: 0.8, key: "bottom-left" },
  { label: "Bottom", x: 0.5, y: 0.8, key: "bottom" },
  { label: "Bottom Right", x: 0.8, y: 0.8, key: "bottom-right" },
];

export default function MediaLayerPanel({
  scenes,
  activeSceneIndex,
  onSelectScene,
  selectedMediaLayerId,
  onSelectMediaLayer,
  onUpdateMediaLayers,
  onOpenMediaLibrary,
  assetUrls = {},
}: MediaLayerPanelProps) {
  const [timingError, setTimingError] = useState<string | null>(null);

  const activeScene = scenes[activeSceneIndex];
  const sceneDuration = activeScene?.duration || 5.0;

  // Extract visual media layers and non-media layers
  const allLayers = (activeScene?.layers || []) as any[];
  const mediaLayers = allLayers.filter(
    (l) => l.type === "image" || l.type === "video" || l.type === "media"
  ) as MediaLayerItem[];
  const nonMediaLayers = allLayers.filter(
    (l) => l.type !== "image" && l.type !== "video" && l.type !== "media"
  );

  // Selected layer
  const selectedLayer =
    mediaLayers.find((l) => l.id === selectedMediaLayerId) || mediaLayers[0] || null;

  const saveUpdatedMediaLayers = (newMediaLayers: MediaLayerItem[]) => {
    onUpdateMediaLayers(activeSceneIndex, [...nonMediaLayers, ...newMediaLayers]);
  };

  // Toggle enable/disable
  const handleToggleEnable = (layerId: string) => {
    const updated = mediaLayers.map((l) =>
      l.id === layerId ? { ...l, enabled: l.enabled === false ? true : false } : l
    );
    saveUpdatedMediaLayers(updated);
  };

  // Toggle locked
  const handleToggleLocked = (layerId: string) => {
    const updated = mediaLayers.map((l) =>
      l.id === layerId ? { ...l, locked: !l.locked } : l
    );
    saveUpdatedMediaLayers(updated);
  };

  // Duplicate layer with cross-type z-index positioning
  const handleDuplicate = (layer: MediaLayerItem) => {
    const newId = `layer_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`;
    const cloned: MediaLayerItem = {
      ...layer,
      id: newId,
      name: `${layer.name || "Media Layer"} (Copy)`,
      transform: {
        x: Math.min(0.9, (layer.transform?.x ?? 0.5) + 0.05),
        y: Math.min(0.9, (layer.transform?.y ?? 0.5) + 0.05),
        scale: layer.transform?.scale ?? 1.0,
        rotation: layer.transform?.rotation ?? 0,
      },
      content: {
        ...(layer.content || {}),
      },
      enabled: layer.enabled !== false,
      locked: false,
    };
    const updated = duplicateLayerWithZIndex(allLayers, layer.id, cloned);
    onUpdateMediaLayers(activeSceneIndex, updated);
    onSelectMediaLayer(newId);
  };

  // Delete layer with z-index normalization
  const handleDelete = (layerId: string) => {
    const updated = deleteLayerWithZIndex(allLayers, layerId);
    onUpdateMediaLayers(activeSceneIndex, updated);
    if (selectedMediaLayerId === layerId) {
      const remainingMedia = updated.filter(
        (l) => l.type === "image" || l.type === "video" || l.type === "media"
      );
      onSelectMediaLayer(remainingMedia.length > 0 ? remainingMedia[0].id : null);
    }
  };

  // Cross-type reorder layer (up = forward / rendered on top, down = backward / rendered behind)
  const handleMoveLayer = (layerId: string, direction: "up" | "down", e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    const updated =
      direction === "up"
        ? bringLayerForward(allLayers, layerId)
        : sendLayerBackward(allLayers, layerId);
    onUpdateMediaLayers(activeSceneIndex, updated);
  };

  // Timing change with validation
  const handleTimingChange = (field: "start" | "end", valStr: string) => {
    if (!selectedLayer || selectedLayer.locked === true) return;
    const val = parseFloat(valStr);
    if (isNaN(val)) return;

    let newStart = selectedLayer.start_time;
    let newEnd = selectedLayer.end_time;

    if (field === "start") {
      newStart = Math.max(0, Math.min(val, sceneDuration));
      if (newStart >= newEnd) {
        setTimingError("Start time must be strictly before end time.");
        return;
      }
    } else {
      newEnd = Math.max(0.1, Math.min(val, sceneDuration));
      if (newEnd <= newStart) {
        setTimingError("End time must be strictly after start time.");
        return;
      }
    }

    setTimingError(null);
    const updated = mediaLayers.map((l) =>
      l.id === selectedLayer.id ? { ...l, start_time: newStart, end_time: newEnd } : l
    );
    saveUpdatedMediaLayers(updated);
  };

  // Transform change
  const handleTransformChange = (changes: Partial<{ x: number; y: number; scale: number; rotation: number }>) => {
    if (!selectedLayer || selectedLayer.locked === true) return;
    const updated = mediaLayers.map((l) =>
      l.id === selectedLayer.id
        ? {
            ...l,
            transform: {
              ...(l.transform || { x: 0.5, y: 0.5, scale: 1.0, rotation: 0 }),
              ...changes,
            },
          }
        : l
    );
    saveUpdatedMediaLayers(updated);
  };

  // Opacity change
  const handleOpacityChange = (opacityVal: number) => {
    if (!selectedLayer || selectedLayer.locked === true) return;
    const updated = mediaLayers.map((l) =>
      l.id === selectedLayer.id
        ? {
            ...l,
            content: {
              ...(l.content || {}),
              opacity: opacityVal,
            },
          }
        : l
    );
    saveUpdatedMediaLayers(updated);
  };

  // Preset Position
  const handleSetPresetPosition = (presetX: number, presetY: number) => {
    if (!selectedLayer || selectedLayer.locked === true) return;
    handleTransformChange({ x: presetX, y: presetY });
  };

  return (
    <div className="space-y-4 select-none">
      {/* 1. Header with Add Media Action */}
      <div className="flex items-center justify-between">
        <h4 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
          <ImageIcon size={14} className="text-blue-400" /> Scene Media Layers
        </h4>
        <button
          onClick={onOpenMediaLibrary}
          className="px-2.5 py-1 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white text-[11px] font-semibold rounded-lg shadow-sm flex items-center gap-1 cursor-pointer transition-all"
        >
          <Plus size={12} /> Add Media
        </button>
      </div>

      {/* 2. Scene Selector if multiple scenes */}
      {scenes.length > 1 && (
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 text-[10px]">
          <span className="text-slate-500 font-semibold uppercase tracking-wider text-[9px] mr-1">
            Scene:
          </span>
          {scenes.map((sc, idx) => (
            <button
              key={sc.id}
              onClick={() => {
                onSelectScene(idx);
                const sceneMedia = (sc.layers || []).filter(
                  (l: any) => l.type === "image" || l.type === "video" || l.type === "media"
                );
                onSelectMediaLayer(sceneMedia.length > 0 ? sceneMedia[0].id : null);
              }}
              className={`px-2 py-0.5 rounded-md font-semibold transition-all cursor-pointer whitespace-nowrap ${
                activeSceneIndex === idx
                  ? "bg-blue-600 text-white shadow-xs"
                  : "bg-[#111728] border border-[#1b2640] text-slate-400 hover:text-slate-200"
              }`}
            >
              {sc.title || `Scene ${idx + 1}`}
            </button>
          ))}
        </div>
      )}

      {/* 3. Layers List Strip */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-[11px] text-slate-400">
          <span>Active Layers ({mediaLayers.length})</span>
          {selectedLayer && (
            <span className="text-[10px] text-blue-400 font-medium truncate max-w-[140px]">
              {selectedLayer.name || selectedLayer.id}
            </span>
          )}
        </div>

        {mediaLayers.length === 0 ? (
          <div className="py-8 text-center text-slate-500 text-xs bg-[#0c101d] rounded-xl border border-dashed border-[#1c2742] p-4">
            <p className="font-semibold text-slate-400">No media layers in this scene</p>
            <p className="text-[10px] text-slate-500 mt-1">
              Add images or videos from your Media Library to overlay them on the canvas.
            </p>
            <button
              onClick={onOpenMediaLibrary}
              className="mt-3 px-3 py-1.5 bg-blue-600/80 hover:bg-blue-600 text-white text-[11px] font-semibold rounded-lg inline-flex items-center gap-1 cursor-pointer transition-colors"
            >
              <Plus size={12} /> Browse Media Library
            </button>
          </div>
        ) : (
          <div className="space-y-1 max-h-[140px] overflow-y-auto pr-1">
            {mediaLayers.map((layer) => {
              const isSelected = selectedLayer?.id === layer.id;
              const isEnabled = layer.enabled !== false;
              const assetId = layer.content?.asset_id;
              const thumbUrl = assetId ? assetUrls[assetId] : null;
              const isVideo = layer.type === "video" || layer.content?.media_type === "video";

              return (
                <div
                  key={layer.id}
                  onClick={() => onSelectMediaLayer(layer.id)}
                  className={`p-1.5 rounded-lg border transition-all cursor-pointer flex items-center justify-between gap-2 ${
                    isSelected
                      ? "bg-[#141f33] border-blue-500 shadow-xs"
                      : "bg-[#0d1222] border-[#18233a] hover:border-[#223352]"
                  }`}
                >
                  <div className="flex items-center gap-2 min-w-0 flex-1">
                    {/* Thumbnail / Icon */}
                    <div className="w-8 h-8 rounded bg-[#172036] border border-white/5 flex items-center justify-center overflow-hidden flex-shrink-0">
                      {thumbUrl ? (
                        <img src={thumbUrl} alt="" className="w-full h-full object-cover" />
                      ) : isVideo ? (
                        <Film size={14} className="text-purple-400" />
                      ) : (
                        <ImageIcon size={14} className="text-blue-400" />
                      )}
                    </div>

                    <div className="min-w-0 flex-1">
                      <span
                        className={`text-xs font-semibold truncate block ${
                          isSelected ? "text-white" : "text-slate-300"
                        }`}
                      >
                        {layer.name || "Media Layer"}
                      </span>
                      <span className="text-[9px] text-slate-500 block font-mono">
                        {layer.start_time.toFixed(1)}s - {layer.end_time.toFixed(1)}s
                      </span>
                    </div>
                  </div>

                  {/* Actions: Reorder, Visibility, Lock, Duplicate, Delete */}
                  <div className="flex items-center gap-1 flex-shrink-0">
                    {allLayers.length > 1 && (
                      <div className="flex items-center bg-[#161f36] rounded p-0.5">
                        <button
                          disabled={
                            layer.locked === true ||
                            (typeof layer.z_index === "number"
                              ? layer.z_index === allLayers.length - 1
                              : mediaLayers.indexOf(layer) === mediaLayers.length - 1)
                          }
                          onClick={(e) => handleMoveLayer(layer.id, "up", e)}
                          className="p-0.5 text-slate-400 hover:text-white disabled:opacity-20 disabled:hover:text-slate-400 cursor-pointer disabled:cursor-not-allowed"
                          title="Bring Forward (Cross-Type Stacking)"
                        >
                          <ChevronUp size={11} />
                        </button>
                        <button
                          disabled={
                            layer.locked === true ||
                            (typeof layer.z_index === "number"
                              ? layer.z_index === 0
                              : mediaLayers.indexOf(layer) === 0)
                          }
                          onClick={(e) => handleMoveLayer(layer.id, "down", e)}
                          className="p-0.5 text-slate-400 hover:text-white disabled:opacity-20 disabled:hover:text-slate-400 cursor-pointer disabled:cursor-not-allowed"
                          title="Send Backward (Cross-Type Stacking)"
                        >
                          <ChevronDown size={11} />
                        </button>
                      </div>
                    )}
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleToggleEnable(layer.id);
                      }}
                      className={`p-1 rounded cursor-pointer transition-colors ${
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
                        handleToggleLocked(layer.id);
                      }}
                      className={`p-1 rounded cursor-pointer transition-colors ${
                        layer.locked
                          ? "text-amber-400 hover:text-amber-300"
                          : "text-slate-400 hover:text-white"
                      }`}
                      title={layer.locked ? "Unlock Layer" : "Lock Layer"}
                    >
                      {layer.locked ? <Lock size={12} /> : <LockOpen size={12} />}
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDuplicate(layer);
                      }}
                      className="p-1 text-slate-400 hover:text-white rounded cursor-pointer transition-colors"
                      title="Duplicate Layer"
                    >
                      <Copy size={12} />
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDelete(layer.id);
                      }}
                      className="p-1 text-slate-400 hover:text-red-400 rounded cursor-pointer transition-colors"
                      title="Delete Layer"
                    >
                      <Trash2 size={12} />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* 4. Selected Layer Inspector Details */}
      {selectedLayer && (
        <div className="space-y-3.5 pt-2 border-t border-[#18233a]">
          {/* Inspector Header with Name & Lock Toggle */}
          <div className="flex items-center justify-between px-1">
            <span className="text-xs font-semibold text-white truncate max-w-[170px]">
              {selectedLayer.name || "Media Inspector"}
            </span>
            <button
              onClick={() => handleToggleLocked(selectedLayer.id)}
              className={`flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-medium border transition-colors cursor-pointer ${
                selectedLayer.locked
                  ? "bg-amber-950/60 border-amber-600/50 text-amber-300 hover:bg-amber-900/60"
                  : "bg-[#141d33] border-[#1f2c4c] text-slate-300 hover:text-white hover:border-slate-500"
              }`}
              title={selectedLayer.locked ? "Click to unlock layer" : "Click to lock layer"}
            >
              {selectedLayer.locked ? <Lock size={10} /> : <LockOpen size={10} />}
              <span>{selectedLayer.locked ? "Locked" : "Lock"}</span>
            </button>
          </div>

          {/* Lock Status Banner */}
          {selectedLayer.locked && (
            <div className="flex items-center gap-2 px-3 py-2 bg-amber-950/40 border border-amber-700/40 rounded-xl text-amber-300 text-[11px]">
              <Lock size={12} className="flex-shrink-0" />
              <span className="font-semibold">Layer is locked — transforms are read-only.</span>
              <button
                onClick={() => handleToggleLocked(selectedLayer.id)}
                className="ml-auto text-[10px] underline text-amber-200 hover:text-white cursor-pointer"
              >
                Unlock
              </button>
            </div>
          )}

          {/* Timing Section */}
          <div className="p-2.5 bg-[#0e1424] border border-[#1a2640] rounded-xl space-y-2">
            <span className="text-[10px] font-bold text-slate-300 uppercase tracking-wider block">
              Layer Timing (seconds)
            </span>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-[10px] text-slate-400 block mb-0.5">Start Time</label>
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  max={sceneDuration}
                  value={selectedLayer.start_time}
                  disabled={!!selectedLayer.locked}
                  onChange={(e) => handleTimingChange("start", e.target.value)}
                  className="w-full bg-[#121828] border border-[#1e2a44] rounded-lg px-2 py-1 text-xs text-white font-mono focus:outline-none focus:border-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
                />
              </div>
              <div>
                <label className="text-[10px] text-slate-400 block mb-0.5">End Time</label>
                <input
                  type="number"
                  step="0.1"
                  min="0.1"
                  max={sceneDuration}
                  value={selectedLayer.end_time}
                  disabled={!!selectedLayer.locked}
                  onChange={(e) => handleTimingChange("end", e.target.value)}
                  className="w-full bg-[#121828] border border-[#1e2a44] rounded-lg px-2 py-1 text-xs text-white font-mono focus:outline-none focus:border-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
                />
              </div>
            </div>

            {timingError && (
              <div className="flex items-center gap-1 text-[10px] text-red-400 pt-0.5">
                <AlertCircle size={11} />
                <span>{timingError}</span>
              </div>
            )}
          </div>

          {/* Position Section */}
          <div className="p-2.5 bg-[#0e1424] border border-[#1a2640] rounded-xl space-y-2.5">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1">
                <Move size={11} className="text-blue-400" /> Canvas Position
              </span>
              <span className="text-[9px] text-slate-400 font-mono">
                X: {Math.round((selectedLayer.transform?.x ?? 0.5) * 100)}% | Y:{" "}
                {Math.round((selectedLayer.transform?.y ?? 0.5) * 100)}%
              </span>
            </div>

            {/* 9-Point Presets Grid */}
            <div className="grid grid-cols-3 gap-1 bg-[#090d18] p-1.5 rounded-lg border border-[#162035]">
              {POSITION_PRESETS.map((p) => {
                const curX = selectedLayer.transform?.x ?? 0.5;
                const curY = selectedLayer.transform?.y ?? 0.5;
                const isClose = Math.abs(curX - p.x) < 0.08 && Math.abs(curY - p.y) < 0.08;

                return (
                  <button
                    key={p.key}
                    onClick={() => !selectedLayer.locked && handleSetPresetPosition(p.x, p.y)}
                    disabled={!!selectedLayer.locked}
                    className={`py-1 px-1.5 text-[9px] font-semibold rounded transition-colors truncate ${
                      selectedLayer.locked
                        ? "text-slate-600 cursor-not-allowed"
                        : isClose
                        ? "bg-blue-600 text-white shadow-xs cursor-pointer"
                        : "text-slate-400 hover:text-slate-200 hover:bg-[#141d33] cursor-pointer"
                    }`}
                  >
                    {p.label}
                  </button>
                );
              })}
            </div>

            {/* Fine Position Sliders */}
            <div className="space-y-1.5 pt-1">
              <div className="flex items-center gap-2">
                <span className="text-[10px] text-slate-400 w-6">X:</span>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={Math.round((selectedLayer.transform?.x ?? 0.5) * 100)}
                  disabled={!!selectedLayer.locked}
                  onChange={(e) =>
                    handleTransformChange({ x: parseFloat(e.target.value) / 100 })
                  }
                  className="flex-1 accent-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
                />
                <span className="text-[9px] text-slate-400 font-mono w-8 text-right">
                  {Math.round((selectedLayer.transform?.x ?? 0.5) * 100)}%
                </span>
              </div>

              <div className="flex items-center gap-2">
                <span className="text-[10px] text-slate-400 w-6">Y:</span>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={Math.round((selectedLayer.transform?.y ?? 0.5) * 100)}
                  disabled={!!selectedLayer.locked}
                  onChange={(e) =>
                    handleTransformChange({ y: parseFloat(e.target.value) / 100 })
                  }
                  className="flex-1 accent-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
                />
                <span className="text-[9px] text-slate-400 font-mono w-8 text-right">
                  {Math.round((selectedLayer.transform?.y ?? 0.5) * 100)}%
                </span>
              </div>
            </div>
          </div>

          {/* Scale, Rotation & Opacity Section */}
          <div className="p-2.5 bg-[#0e1424] border border-[#1a2640] rounded-xl space-y-2.5">
            <span className="text-[10px] font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1">
              <Sliders size={11} className="text-blue-400" /> Transform & Opacity
            </span>

            {/* Scale Slider (20% to 200%) */}
            <div className="space-y-1">
              <div className="flex items-center justify-between text-[10px] text-slate-400">
                <span>Scale Size</span>
                <span className="font-mono text-white">
                  {Math.round((selectedLayer.transform?.scale ?? 1.0) * 100)}%
                </span>
              </div>
              <input
                type="range"
                min="20"
                max="200"
                value={Math.round((selectedLayer.transform?.scale ?? 1.0) * 100)}
                disabled={!!selectedLayer.locked}
                onChange={(e) =>
                  handleTransformChange({ scale: parseFloat(e.target.value) / 100 })
                }
                className="w-full accent-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
              />
            </div>

            {/* Rotation Slider (-180° to 180°) */}
            <div className="space-y-1">
              <div className="flex items-center justify-between text-[10px] text-slate-400">
                <span className="flex items-center gap-1">
                  <RotateCw size={10} /> Rotation
                </span>
                <span className="font-mono text-white">
                  {Math.round(selectedLayer.transform?.rotation ?? 0)}°
                </span>
              </div>
              <input
                type="range"
                min="-180"
                max="180"
                value={Math.round(selectedLayer.transform?.rotation ?? 0)}
                disabled={!!selectedLayer.locked}
                onChange={(e) =>
                  handleTransformChange({ rotation: parseInt(e.target.value, 10) })
                }
                className="w-full accent-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
              />
            </div>

            {/* Opacity Slider (10% to 100%) */}
            <div className="space-y-1">
              <div className="flex items-center justify-between text-[10px] text-slate-400">
                <span>Opacity</span>
                <span className="font-mono text-white">
                  {Math.round((selectedLayer.content?.opacity ?? 1.0) * 100)}%
                </span>
              </div>
              <input
                type="range"
                min="10"
                max="100"
                value={Math.round((selectedLayer.content?.opacity ?? 1.0) * 100)}
                disabled={!!selectedLayer.locked}
                onChange={(e) => handleOpacityChange(parseFloat(e.target.value) / 100)}
                className="w-full accent-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
