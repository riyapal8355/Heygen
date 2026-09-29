"use client";

import React, { useState } from "react";
import {
  Type,
  Plus,
  Trash2,
  Copy,
  Eye,
  EyeOff,
  Lock,
  LockOpen,
  AlertCircle,
  Sliders,
  AlignLeft,
  AlignCenter,
  AlignRight,
  Move,
  Bold,
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

export interface TextLayerItem {
  id: string;
  type: string;
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
    text?: string;
    font_family?: string;
    font_size?: number;
    font_weight?: string;
    color?: string;
    background_color?: string;
    background_opacity?: number;
    opacity?: number;
    alignment?: string;
    position?: string;
    style?: Record<string, any>;
  };
}

interface TextPanelProps {
  scenes: StudioScene[];
  activeSceneIndex: number;
  onSelectScene: (idx: number) => void;
  selectedTextLayerId: string | null;
  onSelectTextLayer: (id: string | null) => void;
  onUpdateTextLayers: (sceneIndex: number, layers: any[]) => void;
}

const TEXT_COLORS = ["#FFFFFF", "#FACC15", "#60A5FA", "#4ADE80", "#F472B6", "#F97316", "#000000"];
const BG_COLORS = ["#000000", "#0F172A", "#1E293B", "#1E1B4B", "#312E81", "#701A75", "#FFFFFF"];

const POSITION_PRESETS = [
  { label: "Top Left", x: 0.2, y: 0.15, key: "top-left" },
  { label: "Top", x: 0.5, y: 0.15, key: "top" },
  { label: "Top Right", x: 0.8, y: 0.15, key: "top-right" },
  { label: "Center Left", x: 0.2, y: 0.5, key: "center-left" },
  { label: "Center", x: 0.5, y: 0.5, key: "center" },
  { label: "Center Right", x: 0.8, y: 0.5, key: "center-right" },
  { label: "Bottom Left", x: 0.2, y: 0.85, key: "bottom-left" },
  { label: "Bottom", x: 0.5, y: 0.85, key: "bottom" },
  { label: "Bottom Right", x: 0.8, y: 0.85, key: "bottom-right" },
];

export default function TextPanel({
  scenes,
  activeSceneIndex,
  onSelectScene,
  selectedTextLayerId,
  onSelectTextLayer,
  onUpdateTextLayers,
}: TextPanelProps) {
  const [activeSubTab, setActiveSubTab] = useState<"layers" | "style">("layers");
  const [timingError, setTimingError] = useState<string | null>(null);

  const activeScene = scenes[activeSceneIndex];
  const sceneDuration = activeScene?.duration || 5.0;

  // Extract text layers and other layers
  const allLayers = (activeScene?.layers || []) as any[];
  const textLayers = allLayers.filter((l) => l.type === "text") as TextLayerItem[];
  const nonTextLayers = allLayers.filter((l) => l.type !== "text");

  // Selected layer
  const selectedLayer = textLayers.find((l) => l.id === selectedTextLayerId) || textLayers[0] || null;

  const saveUpdatedTextLayers = (newTextLayers: TextLayerItem[]) => {
    onUpdateTextLayers(activeSceneIndex, [...nonTextLayers, ...newTextLayers]);
  };

  // Add new text overlay
  const handleAddTextLayer = () => {
    const newId = `text_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`;
    const newLayer: TextLayerItem = {
      id: newId,
      type: "text",
      name: "Text Overlay",
      start_time: 0.0,
      end_time: sceneDuration,
      enabled: true,
      transform: {
        x: 0.5,
        y: 0.5,
        scale: 1.0,
        rotation: 0.0,
      },
      content: {
        text: "Add your text",
        font_family: "Arial",
        font_size: 48,
        font_weight: "bold",
        color: "#FFFFFF",
        background_color: "#000000",
        background_opacity: 0.0,
        opacity: 1.0,
        alignment: "center",
        position: "center",
      },
    };
    saveUpdatedTextLayers([...textLayers, newLayer]);
    onSelectTextLayer(newId);
    setTimingError(null);
  };

  // Duplicate layer with cross-type z-index positioning
  const handleDuplicateLayer = (layer: TextLayerItem, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    const newId = `text_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`;
    const duplicated: TextLayerItem = {
      ...JSON.parse(JSON.stringify(layer)),
      id: newId,
      name: `${layer.name || "Text Overlay"} (Copy)`,
      locked: false,
    };
    const updated = duplicateLayerWithZIndex(allLayers, layer.id, duplicated);
    onUpdateTextLayers(activeSceneIndex, updated);
    onSelectTextLayer(newId);
  };

  // Delete layer with z-index normalization
  const handleDeleteLayer = (layerId: string, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    const updated = deleteLayerWithZIndex(allLayers, layerId);
    onUpdateTextLayers(activeSceneIndex, updated);
    if (selectedTextLayerId === layerId) {
      const remainingText = updated.filter((l) => l.type === "text");
      onSelectTextLayer(remainingText[0]?.id || null);
    }
  };

  // Cross-type reorder layer (up = forward / rendered on top, down = backward / rendered behind)
  const handleMoveLayer = (layerId: string, direction: "up" | "down", e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    const updated =
      direction === "up"
        ? bringLayerForward(allLayers, layerId)
        : sendLayerBackward(allLayers, layerId);
    onUpdateTextLayers(activeSceneIndex, updated);
  };

  // Toggle layer visibility
  const handleToggleLayerEnabled = (layerId: string, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    const updated = textLayers.map((l) =>
      l.id === layerId ? { ...l, enabled: l.enabled === false ? true : false } : l
    );
    saveUpdatedTextLayers(updated);
  };

  // Toggle layer lock
  const handleToggleLayerLocked = (layerId: string, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    const updated = textLayers.map((l) =>
      l.id === layerId ? { ...l, locked: !l.locked } : l
    );
    saveUpdatedTextLayers(updated);
  };

  // Update selected layer property
  const handleUpdateSelectedLayer = (updates: Partial<TextLayerItem>) => {
    if (!selectedLayer) return;
    const updated = textLayers.map((l) => (l.id === selectedLayer.id ? { ...l, ...updates } : l));
    saveUpdatedTextLayers(updated);
  };

  // Update selected layer content property
  const handleUpdateContent = (key: string, value: any) => {
    if (!selectedLayer || selectedLayer.locked === true) return;
    const currentContent = selectedLayer.content || {};
    handleUpdateSelectedLayer({
      content: {
        ...currentContent,
        [key]: value,
      },
    });
  };

  // Update selected layer transform property
  const handleUpdateTransform = (key: string, value: any) => {
    if (!selectedLayer || selectedLayer.locked === true) return;
    const currentTransform = selectedLayer.transform || {};
    handleUpdateSelectedLayer({
      transform: {
        ...currentTransform,
        [key]: value,
      },
    });
  };

  // Handle timing adjustments with validation
  const handleTimingChange = (field: "start_time" | "end_time", value: number) => {
    if (!selectedLayer || selectedLayer.locked === true) return;
    const start = field === "start_time" ? value : selectedLayer.start_time;
    const end = field === "end_time" ? value : selectedLayer.end_time;

    if (start < 0) {
      setTimingError("Start time must be greater than or equal to 0.0s.");
      return;
    }
    if (end <= start) {
      setTimingError("End time must be strictly greater than start time.");
      return;
    }
    setTimingError(null);
    handleUpdateSelectedLayer({ [field]: value });
  };

  return (
    <div className="space-y-4">
      {/* Panel Header */}
      <div className="bg-[#0b101d] border border-[#172033] rounded-2xl p-4 shadow-sm">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400">
              <Type size={16} />
            </div>
            <div>
              <h3 className="text-xs font-semibold text-white">Text Overlays</h3>
              <p className="text-[10px] text-slate-400">Scene visual typography and titles</p>
            </div>
          </div>
          <button
            onClick={handleAddTextLayer}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-medium transition-colors shadow-sm cursor-pointer"
          >
            <Plus size={13} />
            <span>Add Text</span>
          </button>
        </div>

        {/* Scene Selector Indicator */}
        <div className="flex items-center justify-between pt-2 border-t border-[#131b2e] text-[11px]">
          <span className="text-slate-400">Target Scene:</span>
          <div className="flex items-center gap-1 overflow-x-auto max-w-[180px]">
            {scenes.map((_, idx) => (
              <button
                key={idx}
                onClick={() => onSelectScene(idx)}
                className={`px-2 py-0.5 rounded-md text-[10px] font-medium transition-all ${
                  activeSceneIndex === idx
                    ? "bg-blue-600 text-white font-semibold"
                    : "bg-[#131b2e] text-slate-400 hover:text-slate-200"
                }`}
              >
                S{idx + 1}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Sub-Tab Switcher: Layers / Styling */}
      <div className="flex bg-[#0b101d] p-1 rounded-xl border border-[#172033]">
        <button
          onClick={() => setActiveSubTab("layers")}
          className={`flex-1 py-1.5 text-xs font-medium rounded-lg transition-all cursor-pointer ${
            activeSubTab === "layers"
              ? "bg-[#18233a] text-blue-400 font-semibold shadow-xs"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          Layers ({textLayers.length})
        </button>
        <button
          onClick={() => setActiveSubTab("style")}
          disabled={!selectedLayer}
          className={`flex-1 py-1.5 text-xs font-medium rounded-lg transition-all cursor-pointer ${
            activeSubTab === "style"
              ? "bg-[#18233a] text-blue-400 font-semibold shadow-xs"
              : "text-slate-400 hover:text-slate-200 disabled:opacity-40 disabled:cursor-not-allowed"
          }`}
        >
          Style & Position
        </button>
      </div>

      {/* Timing Error Banner */}
      {timingError && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-2.5 flex items-center gap-2 text-red-400 text-xs">
          <AlertCircle size={14} className="shrink-0" />
          <span>{timingError}</span>
        </div>
      )}

      {/* SUB-TAB 1: LAYERS LIST & SELECTED LAYER EDITING */}
      {activeSubTab === "layers" && (
        <div className="space-y-3">
          {textLayers.length === 0 ? (
            <div className="bg-[#0b101d] border border-dashed border-[#1a253d] rounded-2xl p-6 text-center">
              <Type size={28} className="mx-auto text-slate-600 mb-2" />
              <p className="text-xs font-medium text-slate-300">No text layers in Scene {activeSceneIndex + 1}</p>
              <p className="text-[10px] text-slate-500 mt-1 max-w-[220px] mx-auto">
                Add titles, headlines, or callout banners to this scene.
              </p>
              <button
                onClick={handleAddTextLayer}
                className="mt-3 px-3 py-1.5 bg-blue-600/20 hover:bg-blue-600/30 text-blue-400 border border-blue-500/30 rounded-xl text-xs font-medium transition-colors cursor-pointer"
              >
                + Add Text Layer
              </button>
            </div>
          ) : (
            <div className="space-y-2">
              <div className="text-[11px] text-slate-400 font-medium px-1 flex items-center justify-between">
                <span>Text Layers in Scene</span>
                <span className="text-[10px] text-slate-500">Click to select</span>
              </div>
              {textLayers.map((layer, i) => {
                const isSelected = selectedLayer?.id === layer.id;
                const isEnabled = layer.enabled !== false;
                const textContent = layer.content?.text || "Untitled Text";

                return (
                  <div
                    key={layer.id}
                    onClick={() => onSelectTextLayer(layer.id)}
                    className={`p-3 rounded-xl border transition-all cursor-pointer ${
                      isSelected
                        ? "bg-[#111a2f] border-blue-500/60 shadow-xs"
                        : "bg-[#0b101d] border-[#151c2d] hover:border-[#1d273f]"
                    } ${!isEnabled ? "opacity-50" : ""}`}
                  >
                    <div className="flex items-center justify-between gap-2 mb-1.5">
                      <div className="flex items-center gap-1.5 min-w-0">
                        <span className="w-4 h-4 rounded-full bg-[#18233a] text-blue-400 text-[9px] font-bold flex items-center justify-center shrink-0">
                          {i + 1}
                        </span>
                        <span className="text-xs font-semibold text-white truncate max-w-[140px]">
                          {textContent}
                        </span>
                      </div>
                      <div className="flex items-center gap-1 shrink-0">
                        {allLayers.length > 1 && (
                          <div className="flex items-center bg-[#161f36] rounded p-0.5">
                            <button
                              disabled={
                                layer.locked === true ||
                                (typeof layer.z_index === "number"
                                  ? layer.z_index === allLayers.length - 1
                                  : textLayers.indexOf(layer) === textLayers.length - 1)
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
                                  : textLayers.indexOf(layer) === 0)
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
                          onClick={(e) => handleToggleLayerEnabled(layer.id, e)}
                          title={isEnabled ? "Disable Layer" : "Enable Layer"}
                          className={`p-1 rounded-md transition-colors ${
                            isEnabled ? "text-slate-400 hover:text-white" : "text-amber-400"
                          }`}
                        >
                          {isEnabled ? <Eye size={12} /> : <EyeOff size={12} />}
                        </button>
                        <button
                          onClick={(e) => handleToggleLayerLocked(layer.id, e)}
                          title={layer.locked ? "Unlock Layer" : "Lock Layer"}
                          className={`p-1 rounded-md transition-colors ${
                            layer.locked ? "text-amber-400 hover:text-amber-300" : "text-slate-400 hover:text-white"
                          }`}
                        >
                          {layer.locked ? <Lock size={12} /> : <LockOpen size={12} />}
                        </button>
                        <button
                          onClick={(e) => handleDuplicateLayer(layer, e)}
                          title="Duplicate Layer"
                          className="p-1 rounded-md text-slate-400 hover:text-white transition-colors"
                        >
                          <Copy size={12} />
                        </button>
                        <button
                          onClick={(e) => handleDeleteLayer(layer.id, e)}
                          title="Delete Layer"
                          className="p-1 rounded-md text-slate-400 hover:text-red-400 transition-colors"
                        >
                          <Trash2 size={12} />
                        </button>
                      </div>
                    </div>

                    <div className="flex items-center justify-between text-[10px] text-slate-400 pt-1 border-t border-[#141b2b]">
                      <span>
                        Time: {layer.start_time.toFixed(1)}s – {layer.end_time.toFixed(1)}s
                      </span>
                      <span className="text-slate-500">
                        Pos: {Math.round((layer.transform?.x ?? 0.5) * 100)}%,{" "}
                        {Math.round((layer.transform?.y ?? 0.5) * 100)}%
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* Selected Layer Quick Content Editor */}
          {selectedLayer && (
            <div className="bg-[#0b101d] border border-[#172033] rounded-2xl p-4 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-white">Edit Selected Text</span>
                <div className="flex items-center gap-2">
                  <button
                    onClick={(e) => handleToggleLayerLocked(selectedLayer.id, e)}
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
                  <button
                    onClick={() => setActiveSubTab("style")}
                    className="text-[11px] text-blue-400 hover:text-blue-300 flex items-center gap-1 font-medium cursor-pointer"
                  >
                    <Sliders size={11} />
                    <span>Full Styling</span>
                  </button>
                </div>
              </div>

              {/* Lock Banner */}
              {selectedLayer.locked && (
                <div className="flex items-center gap-2 px-3 py-2 bg-amber-950/40 border border-amber-700/40 rounded-xl text-amber-300 text-[11px]">
                  <Lock size={12} className="flex-shrink-0" />
                  <span className="font-semibold">Layer is locked — content is read-only.</span>
                  <button
                    onClick={() => handleToggleLayerLocked(selectedLayer.id)}
                    className="ml-auto text-[10px] underline text-amber-200 hover:text-white cursor-pointer"
                  >
                    Unlock
                  </button>
                </div>
              )}

              {/* Content editing (disabled when locked) */}
              <div style={{ pointerEvents: selectedLayer.locked ? "none" : undefined }} className={selectedLayer.locked ? "opacity-50" : ""}>
                {/* Text Area */}
                <div>
                  <label className="text-[10px] font-medium text-slate-400 block mb-1">Text Content</label>
                  <textarea
                    value={selectedLayer.content?.text || ""}
                    onChange={(e) => handleUpdateContent("text", e.target.value)}
                    rows={2}
                    placeholder="Enter text..."
                    className="w-full bg-[#111728] border border-[#192238] rounded-xl p-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 transition-colors resize-none"
                  />
                </div>

                {/* Timing Controls */}
                <div className="grid grid-cols-2 gap-2 mt-2">
                  <div>
                    <label className="text-[10px] font-medium text-slate-400 block mb-1">Start Time (s)</label>
                    <input
                      type="number"
                      step={0.1}
                      min={0}
                      max={selectedLayer.end_time - 0.1}
                      value={selectedLayer.start_time}
                      onChange={(e) => handleTimingChange("start_time", parseFloat(e.target.value) || 0)}
                      className="w-full bg-[#111728] border border-[#192238] rounded-xl px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-blue-500 transition-colors"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] font-medium text-slate-400 block mb-1">End Time (s)</label>
                    <input
                      type="number"
                      step={0.1}
                      min={selectedLayer.start_time + 0.1}
                      max={sceneDuration}
                      value={selectedLayer.end_time}
                      onChange={(e) =>
                        handleTimingChange("end_time", parseFloat(e.target.value) || sceneDuration)
                      }
                      className="w-full bg-[#111728] border border-[#192238] rounded-xl px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-blue-500 transition-colors"
                    />
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* SUB-TAB 2: STYLE & POSITION CONTROLS */}
      {activeSubTab === "style" && selectedLayer && (
        <div className="space-y-4">
          {/* Header with Name & Lock Toggle */}
          <div className="flex items-center justify-between px-1">
            <span className="text-xs font-semibold text-white truncate max-w-[170px]">
              {selectedLayer.content?.text || selectedLayer.name || "Text Styling"}
            </span>
            <button
              onClick={(e) => handleToggleLayerLocked(selectedLayer.id, e)}
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

          {/* Lock Banner */}
          {selectedLayer.locked && (
            <div className="flex items-center gap-2 px-3 py-2 bg-amber-950/40 border border-amber-700/40 rounded-xl text-amber-300 text-[11px]">
              <Lock size={12} className="flex-shrink-0" />
              <span className="font-semibold">Layer is locked — style controls are read-only.</span>
              <button
                onClick={() => handleToggleLayerLocked(selectedLayer.id)}
                className="ml-auto text-[10px] underline text-amber-200 hover:text-white cursor-pointer"
              >
                Unlock
              </button>
            </div>
          )}

          {/* Style controls (disabled when locked) */}
          <div style={{ pointerEvents: selectedLayer.locked ? "none" : undefined }} className={selectedLayer.locked ? "opacity-50" : ""}>
          {/* 1. Position Presets */}
          <div className="bg-[#0b101d] border border-[#172033] rounded-2xl p-3.5 space-y-2">
            <div className="flex items-center justify-between text-xs font-semibold text-white">
              <span className="flex items-center gap-1.5">
                <Move size={13} className="text-blue-400" />
                <span>Screen Position</span>
              </span>
              <span className="text-[10px] text-slate-400">
                X: {Math.round((selectedLayer.transform?.x ?? 0.5) * 100)}% | Y:{" "}
                {Math.round((selectedLayer.transform?.y ?? 0.5) * 100)}%
              </span>
            </div>

            {/* 3x3 Position Grid */}
            <div className="grid grid-cols-3 gap-1.5 pt-1">
              {POSITION_PRESETS.map((preset) => {
                const currentX = selectedLayer.transform?.x ?? 0.5;
                const currentY = selectedLayer.transform?.y ?? 0.5;
                const isSelected =
                  Math.abs(currentX - preset.x) < 0.08 && Math.abs(currentY - preset.y) < 0.08;

                return (
                  <button
                    key={preset.key}
                    onClick={() => {
                      handleUpdateTransform("x", preset.x);
                      handleUpdateTransform("y", preset.y);
                      handleUpdateContent("position", preset.key);
                    }}
                    className={`py-1.5 px-2 rounded-lg text-[10px] font-medium transition-all text-center cursor-pointer ${
                      isSelected
                        ? "bg-blue-600 text-white font-semibold shadow-xs"
                        : "bg-[#111728] border border-[#192238] text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    {preset.label}
                  </button>
                );
              })}
            </div>

            {/* Fine-Tuning Sliders */}
            <div className="space-y-2 pt-2 border-t border-[#141b2b]">
              <div>
                <div className="flex justify-between text-[10px] text-slate-400 mb-0.5">
                  <span>Horizontal Position (X)</span>
                  <span>{Math.round((selectedLayer.transform?.x ?? 0.5) * 100)}%</span>
                </div>
                <input
                  type="range"
                  min={0}
                  max={100}
                  value={Math.round((selectedLayer.transform?.x ?? 0.5) * 100)}
                  onChange={(e) => handleUpdateTransform("x", parseFloat(e.target.value) / 100)}
                  className="w-full accent-blue-500 h-1.5 bg-[#172033] rounded-lg cursor-pointer"
                />
              </div>

              <div>
                <div className="flex justify-between text-[10px] text-slate-400 mb-0.5">
                  <span>Vertical Position (Y)</span>
                  <span>{Math.round((selectedLayer.transform?.y ?? 0.5) * 100)}%</span>
                </div>
                <input
                  type="range"
                  min={0}
                  max={100}
                  value={Math.round((selectedLayer.transform?.y ?? 0.5) * 100)}
                  onChange={(e) => handleUpdateTransform("y", parseFloat(e.target.value) / 100)}
                  className="w-full accent-blue-500 h-1.5 bg-[#172033] rounded-lg cursor-pointer"
                />
              </div>
            </div>
          </div>

          {/* 2. Typography & Text Alignment */}
          <div className="bg-[#0b101d] border border-[#172033] rounded-2xl p-3.5 space-y-3">
            <span className="text-xs font-semibold text-white block">Typography</span>

            {/* Font Size Slider */}
            <div>
              <div className="flex justify-between text-[10px] text-slate-400 mb-1">
                <span>Font Size</span>
                <span className="font-semibold text-white">
                  {selectedLayer.content?.font_size || 48}px
                </span>
              </div>
              <input
                type="range"
                min={16}
                max={96}
                step={2}
                value={selectedLayer.content?.font_size || 48}
                onChange={(e) => handleUpdateContent("font_size", parseInt(e.target.value, 10))}
                className="w-full accent-blue-500 h-1.5 bg-[#172033] rounded-lg cursor-pointer"
              />
            </div>

            {/* Font Weight & Alignment */}
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-[10px] font-medium text-slate-400 block mb-1">Weight</label>
                <div className="flex bg-[#111728] p-0.5 rounded-xl border border-[#192238]">
                  <button
                    onClick={() => handleUpdateContent("font_weight", "normal")}
                    className={`flex-1 py-1 text-[10px] font-medium rounded-lg transition-all cursor-pointer ${
                      selectedLayer.content?.font_weight !== "bold"
                        ? "bg-[#1d2945] text-white font-semibold"
                        : "text-slate-400"
                    }`}
                  >
                    Normal
                  </button>
                  <button
                    onClick={() => handleUpdateContent("font_weight", "bold")}
                    className={`flex-1 py-1 text-[10px] font-bold rounded-lg transition-all cursor-pointer flex items-center justify-center gap-1 ${
                      selectedLayer.content?.font_weight === "bold"
                        ? "bg-[#1d2945] text-white font-semibold"
                        : "text-slate-400"
                    }`}
                  >
                    <Bold size={11} />
                    <span>Bold</span>
                  </button>
                </div>
              </div>

              <div>
                <label className="text-[10px] font-medium text-slate-400 block mb-1">Alignment</label>
                <div className="flex bg-[#111728] p-0.5 rounded-xl border border-[#192238]">
                  {(["left", "center", "right"] as const).map((al) => {
                    const isSelected = (selectedLayer.content?.alignment || "center") === al;
                    return (
                      <button
                        key={al}
                        onClick={() => handleUpdateContent("alignment", al)}
                        className={`flex-1 py-1 text-[10px] rounded-lg transition-all flex items-center justify-center cursor-pointer ${
                          isSelected ? "bg-[#1d2945] text-white" : "text-slate-400 hover:text-slate-200"
                        }`}
                      >
                        {al === "left" ? (
                          <AlignLeft size={12} />
                        ) : al === "center" ? (
                          <AlignCenter size={12} />
                        ) : (
                          <AlignRight size={12} />
                        )}
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>

            {/* Text Color */}
            <div>
              <label className="text-[10px] font-medium text-slate-400 block mb-1">Text Color</label>
              <div className="flex items-center gap-1.5">
                {TEXT_COLORS.map((c) => (
                  <button
                    key={c}
                    onClick={() => handleUpdateContent("color", c)}
                    style={{ backgroundColor: c }}
                    className={`w-6 h-6 rounded-full border transition-all cursor-pointer ${
                      (selectedLayer.content?.color || "#FFFFFF").toUpperCase() === c.toUpperCase()
                        ? "border-blue-400 scale-110 shadow-sm"
                        : "border-white/20 hover:scale-105"
                    }`}
                  />
                ))}
                <input
                  type="text"
                  value={selectedLayer.content?.color || "#FFFFFF"}
                  onChange={(e) => handleUpdateContent("color", e.target.value)}
                  className="w-16 bg-[#111728] border border-[#192238] rounded-lg px-1.5 py-1 text-[10px] text-white text-center font-mono ml-auto"
                />
              </div>
            </div>
          </div>

          {/* 3. Background Box & Opacity */}
          <div className="bg-[#0b101d] border border-[#172033] rounded-2xl p-3.5 space-y-3">
            <span className="text-xs font-semibold text-white block">Background Bounding Box</span>

            {/* Background Color Palette */}
            <div>
              <label className="text-[10px] font-medium text-slate-400 block mb-1">Box Color</label>
              <div className="flex items-center gap-1.5">
                {BG_COLORS.map((c) => (
                  <button
                    key={c}
                    onClick={() => handleUpdateContent("background_color", c)}
                    style={{ backgroundColor: c }}
                    className={`w-6 h-6 rounded-full border transition-all cursor-pointer ${
                      (selectedLayer.content?.background_color || "#000000").toUpperCase() ===
                      c.toUpperCase()
                        ? "border-blue-400 scale-110 shadow-sm"
                        : "border-white/20 hover:scale-105"
                    }`}
                  />
                ))}
                <input
                  type="text"
                  value={selectedLayer.content?.background_color || "#000000"}
                  onChange={(e) => handleUpdateContent("background_color", e.target.value)}
                  className="w-16 bg-[#111728] border border-[#192238] rounded-lg px-1.5 py-1 text-[10px] text-white text-center font-mono ml-auto"
                />
              </div>
            </div>

            {/* Background Opacity */}
            <div>
              <div className="flex justify-between text-[10px] text-slate-400 mb-1">
                <span>Box Background Opacity</span>
                <span className="font-semibold text-white">
                  {Math.round((selectedLayer.content?.background_opacity ?? 0.0) * 100)}%
                </span>
              </div>
              <input
                type="range"
                min={0}
                max={100}
                step={5}
                value={Math.round((selectedLayer.content?.background_opacity ?? 0.0) * 100)}
                onChange={(e) =>
                  handleUpdateContent("background_opacity", parseFloat(e.target.value) / 100)
                }
                className="w-full accent-blue-500 h-1.5 bg-[#172033] rounded-lg cursor-pointer"
              />
            </div>

            {/* Overall Text Opacity */}
            <div>
              <div className="flex justify-between text-[10px] text-slate-400 mb-1">
                <span>Text Layer Opacity</span>
                <span className="font-semibold text-white">
                  {Math.round((selectedLayer.content?.opacity ?? 1.0) * 100)}%
                </span>
              </div>
              <input
                type="range"
                min={10}
                max={100}
                step={5}
                value={Math.round((selectedLayer.content?.opacity ?? 1.0) * 100)}
                onChange={(e) => handleUpdateContent("opacity", parseFloat(e.target.value) / 100)}
                className="w-full accent-blue-500 h-1.5 bg-[#172033] rounded-lg cursor-pointer"
              />
            </div>
          </div>
          </div>
        </div>
      )}
    </div>
  );
}
