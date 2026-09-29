"use client";

import React, { useState } from "react";
import {
  Square,
  Circle,
  Minus,
  ArrowRight,
  Star,
  Heart,
  Flame,
  Sparkles,
  Rocket,
  ThumbsUp,
  CheckCircle,
  AlertTriangle,
  Trophy,
  Tag,
  Plus,
  Trash2,
  Copy,
  Eye,
  EyeOff,
  Lock,
  LockOpen,
  Sliders,
  ChevronUp,
  ChevronDown,
  Move,
  RotateCw,
  Palette,
  Component,
} from "lucide-react";
import { StudioScene } from "./VidoAIStudio";
import {
  bringLayerForward,
  sendLayerBackward,
  duplicateLayerWithZIndex,
  deleteLayerWithZIndex,
} from "../../lib/studioLayerOrdering";

export interface ElementLayerItem {
  id: string;
  type: "shape" | "sticker" | "element";
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
    shape_type?: string;
    width?: number;
    height?: number;
    fill?: string;
    border_color?: string;
    border_width?: number;
    border_radius?: number;
    opacity?: number;
    sticker_id?: string;
    asset_id?: string;
    [key: string]: any;
  };
}

interface ElementsPanelProps {
  scenes: StudioScene[];
  activeSceneIndex: number;
  onSelectScene: (idx: number) => void;
  selectedElementLayerId: string | null;
  onSelectElementLayer: (id: string | null) => void;
  onUpdateElementLayers: (sceneIndex: number, layers: any[]) => void;
}

const SHAPE_TEMPLATES = [
  {
    id: "rectangle",
    name: "Rectangle",
    icon: Square,
    shape_type: "rectangle",
    width: 0.35,
    height: 0.2,
    fill: "#3B82F6",
    border_color: "#FFFFFF",
    border_width: 0,
    border_radius: 0,
  },
  {
    id: "rounded_rectangle",
    name: "Rounded Box",
    icon: Square,
    shape_type: "rounded_rectangle",
    width: 0.35,
    height: 0.2,
    fill: "#8B5CF6",
    border_color: "#FFFFFF",
    border_width: 2,
    border_radius: 16,
  },
  {
    id: "circle",
    name: "Circle",
    icon: Circle,
    shape_type: "circle",
    width: 0.25,
    height: 0.25,
    fill: "#10B981",
    border_color: "#FFFFFF",
    border_width: 0,
    border_radius: 0,
  },
  {
    id: "ellipse",
    name: "Ellipse",
    icon: Circle,
    shape_type: "ellipse",
    width: 0.35,
    height: 0.2,
    fill: "#F59E0B",
    border_color: "#FFFFFF",
    border_width: 0,
    border_radius: 0,
  },
  {
    id: "line",
    name: "Line",
    icon: Minus,
    shape_type: "line",
    width: 0.4,
    height: 0.04,
    fill: "#FFFFFF",
    border_color: "#FFFFFF",
    border_width: 4,
    border_radius: 0,
  },
  {
    id: "arrow",
    name: "Arrow",
    icon: ArrowRight,
    shape_type: "arrow",
    width: 0.35,
    height: 0.12,
    fill: "#EC4899",
    border_color: "#FFFFFF",
    border_width: 0,
    border_radius: 0,
  },
];

const STICKER_TEMPLATES = [
  { id: "star", name: "Star", icon: Star, color: "#FBBF24" },
  { id: "heart", name: "Heart", icon: Heart, color: "#EF4444" },
  { id: "fire", name: "Fire", icon: Flame, color: "#F97316" },
  { id: "sparkles", name: "Sparkles", icon: Sparkles, color: "#A855F7" },
  { id: "rocket", name: "Rocket", icon: Rocket, color: "#EC4899" },
  { id: "thumbs_up", name: "Thumbs Up", icon: ThumbsUp, color: "#3B82F6" },
  { id: "checkmark", name: "Checkmark", icon: CheckCircle, color: "#10B981" },
  { id: "warning", name: "Warning", icon: AlertTriangle, color: "#EAB308" },
  { id: "trophy", name: "Trophy", icon: Trophy, color: "#F59E0B" },
  { id: "discount", name: "Sale Tag", icon: Tag, color: "#EF4444" },
];

const COLOR_SWATCHES = [
  "#FFFFFF",
  "#3B82F6",
  "#8B5CF6",
  "#EC4899",
  "#EF4444",
  "#F97316",
  "#FBBF24",
  "#10B981",
  "#06B6D4",
  "#000000",
];

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

export default function ElementsPanel({
  scenes,
  activeSceneIndex,
  onSelectScene,
  selectedElementLayerId,
  onSelectElementLayer,
  onUpdateElementLayers,
}: ElementsPanelProps) {
  const [activeSubTab, setActiveSubTab] = useState<"shapes" | "stickers" | "inspector">("shapes");
  const [timingError, setTimingError] = useState<string | null>(null);

  const activeScene = scenes[activeSceneIndex];
  const sceneDuration = activeScene?.duration || 5.0;

  // Extract element layers (shapes, stickers, elements)
  const allLayers = (activeScene?.layers || []) as any[];
  const elementLayers = allLayers.filter(
    (l) => l.type === "shape" || l.type === "sticker" || l.type === "element"
  ) as ElementLayerItem[];

  // Selected layer
  const selectedLayer =
    elementLayers.find((l) => l.id === selectedElementLayerId) || elementLayers[0] || null;

  // Save changes directly into allLayers preserving exact sequence
  const saveUpdatedLayers = (updatedElementLayers: ElementLayerItem[]) => {
    // Replace element layers in-place or append
    const nonElementLayers = allLayers.filter(
      (l) => l.type !== "shape" && l.type !== "sticker" && l.type !== "element"
    );
    onUpdateElementLayers(activeSceneIndex, [...nonElementLayers, ...updatedElementLayers]);
  };

  // 1. Add Shape Layer
  const handleAddShape = (tmpl: (typeof SHAPE_TEMPLATES)[0]) => {
    const newId = `shape_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`;
    const newLayer: ElementLayerItem = {
      id: newId,
      type: "shape",
      name: tmpl.name,
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
        shape_type: tmpl.shape_type,
        width: tmpl.width,
        height: tmpl.height,
        fill: tmpl.fill,
        border_color: tmpl.border_color,
        border_width: tmpl.border_width,
        border_radius: tmpl.border_radius,
        opacity: 1.0,
      },
    };

    const next = [...elementLayers, newLayer];
    saveUpdatedLayers(next);
    onSelectElementLayer(newId);
    setActiveSubTab("inspector");
  };

  // 2. Add Sticker Layer
  const handleAddSticker = (tmpl: (typeof STICKER_TEMPLATES)[0]) => {
    const newId = `sticker_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`;
    const newLayer: ElementLayerItem = {
      id: newId,
      type: "sticker",
      name: tmpl.name,
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
        sticker_id: tmpl.id,
        fill: tmpl.color,
        opacity: 1.0,
      },
    };

    const next = [...elementLayers, newLayer];
    saveUpdatedLayers(next);
    onSelectElementLayer(newId);
    setActiveSubTab("inspector");
  };

  // 3. Toggle Enable/Disable
  const handleToggleEnable = (layerId: string) => {
    const updated = elementLayers.map((l) =>
      l.id === layerId ? { ...l, enabled: l.enabled === false ? true : false } : l
    );
    saveUpdatedLayers(updated);
  };

  // 3b. Toggle Locked
  const handleToggleLocked = (layerId: string) => {
    const updated = elementLayers.map((l) =>
      l.id === layerId ? { ...l, locked: !l.locked } : l
    );
    saveUpdatedLayers(updated);
  };

  // 4. Duplicate Layer with cross-type z-index positioning
  const handleDuplicate = (layerId: string) => {
    const target = elementLayers.find((l) => l.id === layerId);
    if (!target) return;
    const newId = `element_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`;
    const dup: ElementLayerItem = {
      ...JSON.parse(JSON.stringify(target)),
      id: newId,
      name: `${target.name || "Element"} (Copy)`,
      transform: {
        ...(target.transform || {}),
        x: Math.min(0.9, (target.transform?.x ?? 0.5) + 0.05),
        y: Math.min(0.9, (target.transform?.y ?? 0.5) + 0.05),
      },
      locked: false,
    };
    const updated = duplicateLayerWithZIndex(allLayers, target.id, dup);
    onUpdateElementLayers(activeSceneIndex, updated);
    onSelectElementLayer(newId);
  };

  // 5. Delete Layer with z-index normalization
  const handleDelete = (layerId: string) => {
    const updated = deleteLayerWithZIndex(allLayers, layerId);
    onUpdateElementLayers(activeSceneIndex, updated);
    if (selectedElementLayerId === layerId) {
      const remainingElements = updated.filter(
        (l) => l.type === "shape" || l.type === "sticker" || l.type === "element"
      );
      onSelectElementLayer(remainingElements[0]?.id || null);
    }
  };

  // 6. Layer Reordering (Bring Forward / Send Backward cross-type)
  const handleReorder = (layerId: string, direction: "up" | "down", e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    const updated =
      direction === "up"
        ? bringLayerForward(allLayers, layerId)
        : sendLayerBackward(allLayers, layerId);
    onUpdateElementLayers(activeSceneIndex, updated);
  };

  // 7. Timing Change
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
    const updated = elementLayers.map((l) =>
      l.id === selectedLayer.id ? { ...l, start_time: newStart, end_time: newEnd } : l
    );
    saveUpdatedLayers(updated);
  };

  // 8. Transform Change
  const handleTransformChange = (
    changes: Partial<{ x: number; y: number; scale: number; rotation: number }>
  ) => {
    if (!selectedLayer || selectedLayer.locked === true) return;
    const updated = elementLayers.map((l) =>
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
    saveUpdatedLayers(updated);
  };

  // 9. Content Change
  const handleContentChange = (changes: Partial<Record<string, any>>) => {
    if (!selectedLayer || selectedLayer.locked === true) return;
    const updated = elementLayers.map((l) =>
      l.id === selectedLayer.id
        ? {
            ...l,
            content: {
              ...(l.content || {}),
              ...changes,
            },
          }
        : l
    );
    saveUpdatedLayers(updated);
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h4 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
          <Component size={14} className="text-blue-400" /> Elements & Shapes
        </h4>
        <span className="text-[10px] text-slate-400 font-mono">
          {elementLayers.length} active
        </span>
      </div>

      {/* Sub-Tabs: Shapes | Stickers | Active Inspector */}
      <div className="flex bg-[#121828] p-0.5 rounded-lg border border-[#1e2a44] text-[11px]">
        <button
          onClick={() => setActiveSubTab("shapes")}
          className={`flex-1 py-1.5 rounded-md font-semibold transition-all cursor-pointer ${
            activeSubTab === "shapes"
              ? "bg-blue-600 text-white shadow-xs"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          Shapes
        </button>
        <button
          onClick={() => setActiveSubTab("stickers")}
          className={`flex-1 py-1.5 rounded-md font-semibold transition-all cursor-pointer ${
            activeSubTab === "stickers"
              ? "bg-blue-600 text-white shadow-xs"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          Stickers
        </button>
        <button
          onClick={() => setActiveSubTab("inspector")}
          className={`flex-1 py-1.5 rounded-md font-semibold transition-all cursor-pointer flex items-center justify-center gap-1 ${
            activeSubTab === "inspector"
              ? "bg-blue-600 text-white shadow-xs"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          <Sliders size={11} />
          <span>Edit</span>
          {elementLayers.length > 0 && (
            <span className="w-4 h-4 rounded-full bg-blue-900/60 text-[9px] flex items-center justify-center">
              {elementLayers.length}
            </span>
          )}
        </button>
      </div>

      {/* TAB 1: SHAPES CATALOG */}
      {activeSubTab === "shapes" && (
        <div className="space-y-3">
          <div className="text-[11px] text-slate-400">
            Click any shape to insert it into the current scene canvas:
          </div>

          <div className="grid grid-cols-2 gap-2.5">
            {SHAPE_TEMPLATES.map((tmpl) => {
              const Icon = tmpl.icon;
              return (
                <button
                  key={tmpl.id}
                  onClick={() => handleAddShape(tmpl)}
                  className="bg-[#101626] hover:bg-[#18233c] border border-[#1b2640] hover:border-blue-500/60 rounded-xl p-3 flex flex-col items-center justify-center gap-2 transition-all cursor-pointer group shadow-xs"
                >
                  <div
                    className="w-10 h-10 rounded-lg flex items-center justify-center shadow-inner"
                    style={{ backgroundColor: `${tmpl.fill}22`, border: `1.5px solid ${tmpl.fill}` }}
                  >
                    <Icon size={20} style={{ color: tmpl.fill }} />
                  </div>
                  <span className="text-xs font-semibold text-slate-200 group-hover:text-white">
                    {tmpl.name}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* TAB 2: STICKERS CATALOG */}
      {activeSubTab === "stickers" && (
        <div className="space-y-3">
          <div className="text-[11px] text-slate-400">
            Click a graphic sticker to place it onto the active scene:
          </div>

          <div className="grid grid-cols-2 gap-2.5">
            {STICKER_TEMPLATES.map((tmpl) => {
              const Icon = tmpl.icon;
              return (
                <button
                  key={tmpl.id}
                  onClick={() => handleAddSticker(tmpl)}
                  className="bg-[#101626] hover:bg-[#18233c] border border-[#1b2640] hover:border-blue-500/60 rounded-xl p-3 flex flex-col items-center justify-center gap-2 transition-all cursor-pointer group shadow-xs"
                >
                  <div
                    className="w-10 h-10 rounded-xl flex items-center justify-center shadow-inner"
                    style={{ backgroundColor: `${tmpl.color}20`, border: `1.5px solid ${tmpl.color}` }}
                  >
                    <Icon size={20} style={{ color: tmpl.color }} />
                  </div>
                  <span className="text-xs font-semibold text-slate-200 group-hover:text-white">
                    {tmpl.name}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* TAB 3: INSPECTOR & ACTIVE ELEMENTS LIST */}
      {activeSubTab === "inspector" && (
        <div className="space-y-4">
          {/* Active Layer Pill Selector */}
          {elementLayers.length === 0 ? (
            <div className="p-6 bg-[#0e1322] border border-dashed border-[#1a233a] rounded-xl text-center space-y-2">
              <Component size={24} className="mx-auto text-slate-500" />
              <p className="text-xs text-slate-400 font-medium">No elements in this scene</p>
              <div className="flex justify-center gap-2 pt-1">
                <button
                  onClick={() => setActiveSubTab("shapes")}
                  className="px-3 py-1 bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold rounded-lg transition-all cursor-pointer"
                >
                  + Add Shape
                </button>
                <button
                  onClick={() => setActiveSubTab("stickers")}
                  className="px-3 py-1 bg-[#1a243a] hover:bg-[#253350] text-slate-200 text-xs font-semibold rounded-lg transition-all cursor-pointer"
                >
                  + Add Sticker
                </button>
              </div>
            </div>
          ) : (
            <>
              {/* Elements Stack List with Reordering */}
              <div className="space-y-1.5">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                  Layer Stack (Top to Bottom)
                </span>
                <div className="space-y-1 max-h-36 overflow-y-auto pr-0.5">
                  {/* Render in reverse order so top visual layer appears at top of list */}
                  {[...elementLayers].reverse().map((layer, revIdx) => {
                    const originalIdx = elementLayers.length - 1 - revIdx;
                    const isSelected = layer.id === selectedLayer?.id;
                    const isShape = layer.type === "shape";
                    return (
                      <div
                        key={layer.id}
                        onClick={() => onSelectElementLayer(layer.id)}
                        className={`p-2 rounded-lg border transition-all flex items-center justify-between cursor-pointer ${
                          isSelected
                            ? "bg-[#18233a] border-blue-500 text-white shadow-xs"
                            : "bg-[#0f1424] border-[#1a243a] text-slate-300 hover:border-slate-600"
                        }`}
                      >
                        <div className="flex items-center gap-2 min-w-0">
                          <span className="text-xs">
                            {isShape ? "📐" : "⭐"}
                          </span>
                          <span className="text-xs font-medium truncate">
                            {layer.name || (isShape ? "Shape" : "Sticker")}
                          </span>
                        </div>

                        <div className="flex items-center gap-1">
                          {/* Reorder Up (Bring Forward) */}
                          <button
                            disabled={
                              layer.locked === true ||
                              (typeof layer.z_index === "number"
                                ? layer.z_index === allLayers.length - 1
                                : originalIdx >= elementLayers.length - 1)
                            }
                            onClick={(e) => handleReorder(layer.id, "up", e)}
                            className="p-1 text-slate-400 hover:text-white disabled:opacity-20 cursor-pointer disabled:cursor-not-allowed"
                            title="Bring Forward (Cross-Type Stacking)"
                          >
                            <ChevronUp size={12} />
                          </button>
                          {/* Reorder Down (Send Backward) */}
                          <button
                            disabled={
                              layer.locked === true ||
                              (typeof layer.z_index === "number"
                                ? layer.z_index === 0
                                : originalIdx <= 0)
                            }
                            onClick={(e) => handleReorder(layer.id, "down", e)}
                            className="p-1 text-slate-400 hover:text-white disabled:opacity-20 cursor-pointer disabled:cursor-not-allowed"
                            title="Send Backward (Cross-Type Stacking)"
                          >
                            <ChevronDown size={12} />
                          </button>
                          {/* Visibility Toggle */}
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleToggleEnable(layer.id);
                            }}
                            className="p-1 text-slate-400 hover:text-white cursor-pointer"
                            title={layer.enabled === false ? "Enable" : "Disable"}
                          >
                            {layer.enabled === false ? <EyeOff size={12} className="text-slate-500" /> : <Eye size={12} className="text-emerald-400" />}
                          </button>
                          {/* Lock Toggle */}
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleToggleLocked(layer.id);
                            }}
                            className={`p-1 cursor-pointer transition-colors ${
                              layer.locked ? "text-amber-400 hover:text-amber-300" : "text-slate-400 hover:text-white"
                            }`}
                            title={layer.locked ? "Unlock Layer" : "Lock Layer"}
                          >
                            {layer.locked ? <Lock size={12} /> : <LockOpen size={12} />}
                          </button>
                          {/* Duplicate */}
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDuplicate(layer.id);
                            }}
                            className="p-1 text-slate-400 hover:text-white cursor-pointer"
                            title="Duplicate"
                          >
                            <Copy size={12} />
                          </button>
                          {/* Delete */}
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDelete(layer.id);
                            }}
                            className="p-1 text-slate-400 hover:text-red-400 cursor-pointer"
                            title="Delete"
                          >
                            <Trash2 size={12} />
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {selectedLayer && (
                <div className="space-y-4 pt-2 border-t border-[#171f33]">
                  {/* Layer Name, Lock Toggle & Type */}
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-white uppercase tracking-wider truncate max-w-[150px]">
                      {selectedLayer.name || "Element Inspector"}
                    </span>
                    <div className="flex items-center gap-1.5">
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
                      <span className="text-[10px] bg-blue-900/50 text-blue-300 px-1.5 py-0.5 rounded font-mono uppercase">
                        {selectedLayer.type}
                      </span>
                    </div>
                  </div>

                  {/* Lock Banner */}
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

                  {/* Inspector controls (disabled when locked) */}
                  <div style={{ pointerEvents: selectedLayer.locked ? "none" : undefined }} className={selectedLayer.locked ? "opacity-50 space-y-4" : "space-y-4"}>

                  {/* TIMING */}
                  <div className="space-y-2 p-3 bg-[#101626] border border-[#1a2640] rounded-xl">
                    <div className="flex items-center justify-between">
                      <label className="text-[10px] font-bold text-slate-300 uppercase tracking-wider">
                        Timing (Seconds)
                      </label>
                      <span className="text-[10px] text-slate-500 font-mono">
                        Max: {Math.round(sceneDuration)}s
                      </span>
                    </div>

                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <span className="text-[9px] text-slate-400 block mb-0.5">Start</span>
                        <input
                          type="number"
                          step="0.1"
                          min="0"
                          max={sceneDuration}
                          value={selectedLayer.start_time ?? 0}
                          onChange={(e) => handleTimingChange("start", e.target.value)}
                          className="w-full bg-[#121828] border border-[#1e2a44] rounded-lg px-2.5 py-1 text-xs text-white font-mono focus:outline-none focus:border-blue-500"
                        />
                      </div>
                      <div>
                        <span className="text-[9px] text-slate-400 block mb-0.5">End</span>
                        <input
                          type="number"
                          step="0.1"
                          min="0.1"
                          max={sceneDuration}
                          value={selectedLayer.end_time ?? sceneDuration}
                          onChange={(e) => handleTimingChange("end", e.target.value)}
                          className="w-full bg-[#121828] border border-[#1e2a44] rounded-lg px-2.5 py-1 text-xs text-white font-mono focus:outline-none focus:border-blue-500"
                        />
                      </div>
                    </div>

                    {timingError && (
                      <p className="text-[10px] text-red-400">{timingError}</p>
                    )}
                  </div>

                  {/* POSITION PRESETS */}
                  <div className="space-y-1.5">
                    <span className="text-[10px] font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1">
                      <Move size={11} className="text-blue-400" /> Position Presets
                    </span>
                    <div className="grid grid-cols-3 gap-1.5">
                      {POSITION_PRESETS.map((p) => (
                        <button
                          key={p.key}
                          onClick={() => handleTransformChange({ x: p.x, y: p.y })}
                          className="bg-[#101626] hover:bg-[#1a253e] border border-[#1a243a] text-slate-300 hover:text-white rounded-lg py-1 text-[10px] font-medium transition-all cursor-pointer"
                        >
                          {p.label}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* FINE TRANSFORM SLIDERS */}
                  <div className="space-y-3 p-3 bg-[#101626] border border-[#1a2640] rounded-xl">
                    <span className="text-[10px] font-bold text-slate-300 uppercase tracking-wider block">
                      Transform & Scale
                    </span>

                    {/* Scale */}
                    <div>
                      <div className="flex items-center justify-between text-[10px] text-slate-400 mb-1">
                        <span>Scale</span>
                        <span className="font-mono text-white">
                          {(selectedLayer.transform?.scale ?? 1.0).toFixed(2)}x
                        </span>
                      </div>
                      <input
                        type="range"
                        min="0.2"
                        max="3.0"
                        step="0.05"
                        value={selectedLayer.transform?.scale ?? 1.0}
                        onChange={(e) =>
                          handleTransformChange({ scale: parseFloat(e.target.value) })
                        }
                        className="w-full accent-blue-500 cursor-pointer"
                      />
                    </div>

                    {/* Rotation */}
                    <div>
                      <div className="flex items-center justify-between text-[10px] text-slate-400 mb-1">
                        <span>Rotation</span>
                        <span className="font-mono text-white">
                          {Math.round(selectedLayer.transform?.rotation ?? 0)}°
                        </span>
                      </div>
                      <input
                        type="range"
                        min="-180"
                        max="180"
                        step="5"
                        value={selectedLayer.transform?.rotation ?? 0}
                        onChange={(e) =>
                          handleTransformChange({ rotation: parseFloat(e.target.value) })
                        }
                        className="w-full accent-blue-500 cursor-pointer"
                      />
                    </div>

                    {/* Opacity */}
                    <div>
                      <div className="flex items-center justify-between text-[10px] text-slate-400 mb-1">
                        <span>Opacity</span>
                        <span className="font-mono text-white">
                          {Math.round((selectedLayer.content?.opacity ?? 1.0) * 100)}%
                        </span>
                      </div>
                      <input
                        type="range"
                        min="0.05"
                        max="1.0"
                        step="0.05"
                        value={selectedLayer.content?.opacity ?? 1.0}
                        onChange={(e) =>
                          handleContentChange({ opacity: parseFloat(e.target.value) })
                        }
                        className="w-full accent-blue-500 cursor-pointer"
                      />
                    </div>
                  </div>

                  {/* SHAPE SPECIFIC STYLING */}
                  {selectedLayer.type === "shape" && (
                    <div className="space-y-3 p-3 bg-[#101626] border border-[#1a2640] rounded-xl">
                      <span className="text-[10px] font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1">
                        <Palette size={11} className="text-blue-400" /> Shape Appearance
                      </span>

                      {/* Fill Color */}
                      <div>
                        <span className="text-[9px] text-slate-400 block mb-1">Fill Color</span>
                        <div className="flex items-center gap-2">
                          <input
                            type="color"
                            value={selectedLayer.content?.fill || "#3B82F6"}
                            onChange={(e) => handleContentChange({ fill: e.target.value })}
                            className="w-7 h-7 rounded border border-white/20 bg-transparent cursor-pointer"
                          />
                          <div className="flex gap-1 overflow-x-auto py-1">
                            {COLOR_SWATCHES.map((col) => (
                              <button
                                key={col}
                                onClick={() => handleContentChange({ fill: col })}
                                className="w-5 h-5 rounded-full border border-white/20 flex-shrink-0 cursor-pointer hover:scale-110 transition-transform"
                                style={{ backgroundColor: col }}
                              />
                            ))}
                          </div>
                        </div>
                      </div>

                      {/* Border / Stroke Color & Width */}
                      <div>
                        <div className="flex items-center justify-between text-[9px] text-slate-400 mb-1">
                          <span>Border / Stroke</span>
                          <span className="font-mono text-white">
                            {selectedLayer.content?.border_width ?? 0}px
                          </span>
                        </div>
                        <div className="flex items-center gap-2 mb-2">
                          <input
                            type="color"
                            value={selectedLayer.content?.border_color || "#FFFFFF"}
                            onChange={(e) => handleContentChange({ border_color: e.target.value })}
                            className="w-7 h-7 rounded border border-white/20 bg-transparent cursor-pointer"
                          />
                          <input
                            type="range"
                            min="0"
                            max="16"
                            step="1"
                            value={selectedLayer.content?.border_width ?? 0}
                            onChange={(e) =>
                              handleContentChange({ border_width: parseInt(e.target.value, 10) })
                            }
                            className="flex-1 accent-blue-500 cursor-pointer"
                          />
                        </div>
                      </div>

                      {/* Border Radius (For box shapes) */}
                      {selectedLayer.content?.shape_type !== "circle" && (
                        <div>
                          <div className="flex items-center justify-between text-[9px] text-slate-400 mb-1">
                            <span>Corner Radius</span>
                            <span className="font-mono text-white">
                              {selectedLayer.content?.border_radius ?? 0}px
                            </span>
                          </div>
                          <input
                            type="range"
                            min="0"
                            max="40"
                            step="2"
                            value={selectedLayer.content?.border_radius ?? 0}
                            onChange={(e) =>
                              handleContentChange({ border_radius: parseInt(e.target.value, 10) })
                            }
                            className="w-full accent-blue-500 cursor-pointer"
                          />
                        </div>
                      )}
                    </div>
                  )}

                  </div>{/* end locked wrapper */}

                  {/* QUICK ACTIONS */}
                  <div className="flex gap-2 pt-1">
                    <button
                      onClick={() => handleDuplicate(selectedLayer.id)}
                      className="flex-1 py-1.5 bg-[#141b2e] hover:bg-[#1f2b48] text-slate-200 rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 transition-all cursor-pointer"
                    >
                      <Copy size={12} /> Duplicate
                    </button>
                    <button
                      onClick={() => handleDelete(selectedLayer.id)}
                      className="py-1.5 px-3 bg-red-950/40 hover:bg-red-900/60 border border-red-500/30 text-red-200 rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 transition-all cursor-pointer"
                    >
                      <Trash2 size={12} /> Delete
                    </button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
