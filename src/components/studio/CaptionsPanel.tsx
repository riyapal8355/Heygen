"use client";

import React, { useState } from "react";
import {
  Subtitles,
  Sparkles,
  Plus,
  Trash2,
  RefreshCw,
  Loader2,
  Eye,
  EyeOff,
  AlertCircle,
  Sliders,
  Check,
} from "lucide-react";
import { StudioScene } from "./VidoAIStudio";

export interface CaptionStyleState {
  font_family: string;
  font_size: number;
  font_weight: string;
  color: string;
  background_color: string;
  background_opacity: number;
  position: string;
  alignment: string;
}

export interface CaptionSettingsState {
  enabled: boolean;
  style: CaptionStyleState;
}

export interface SubtitleCue {
  id: string | number;
  start: number;
  end: number;
  text: string;
  enabled?: boolean;
  words?: any[];
}

interface CaptionsPanelProps {
  scenes: StudioScene[];
  activeSceneIndex: number;
  onSelectScene: (idx: number) => void;
  captionSettings: CaptionSettingsState;
  onUpdateCaptionSettings: (settings: CaptionSettingsState) => void;
  onUpdateSubtitles: (sceneIndex: number, subtitles: SubtitleCue[]) => void;
  onGenerateCaptions: (sceneIndex: number) => Promise<void>;
  isGenerating: boolean;
  selectedCueId: string | number | null;
  onSelectCue: (id: string | number | null) => void;
}

const TEXT_COLORS = ["#FFFFFF", "#FACC15", "#60A5FA", "#4ADE80", "#F472B6", "#F97316"];
const BG_COLORS = ["#000000", "#0F172A", "#1E293B", "#1E1B4B", "#312E81", "#701A75"];

export default function CaptionsPanel({
  scenes,
  activeSceneIndex,
  onSelectScene,
  captionSettings,
  onUpdateCaptionSettings,
  onUpdateSubtitles,
  onGenerateCaptions,
  isGenerating,
  selectedCueId,
  onSelectCue,
}: CaptionsPanelProps) {
  const [activeSubTab, setActiveSubTab] = useState<"cues" | "style">("cues");
  const [timingError, setTimingError] = useState<string | null>(null);

  const activeScene = scenes[activeSceneIndex];
  const subtitles: SubtitleCue[] = (activeScene?.subtitles || []).map((c: any, i: number) => ({
    id: c.id ?? `cue_${i + 1}`,
    start: Number(c.start ?? 0),
    end: Number(c.end ?? 1),
    text: String(c.text ?? ""),
    enabled: c.enabled !== false,
    words: c.words,
  }));

  const hasSpeechAudio = Boolean(activeScene?.speech?.audio_asset_id);

  // Toggle master captions enable/disable
  const handleToggleMasterEnabled = () => {
    onUpdateCaptionSettings({
      ...captionSettings,
      enabled: !captionSettings.enabled,
    });
  };

  // Update styling property
  const handleUpdateStyle = (key: keyof CaptionStyleState, value: any) => {
    onUpdateCaptionSettings({
      ...captionSettings,
      style: {
        ...captionSettings.style,
        [key]: value,
      },
    });
  };

  // Add new manual cue
  const handleAddCue = () => {
    const lastCue = subtitles[subtitles.length - 1];
    const newStart = lastCue ? Number((lastCue.end + 0.1).toFixed(2)) : 0.0;
    const newEnd = Number((newStart + 2.0).toFixed(2));
    const newCue: SubtitleCue = {
      id: `cue_${Date.now()}`,
      start: newStart,
      end: newEnd,
      text: "New caption cue",
      enabled: true,
    };
    const updated = [...subtitles, newCue];
    onUpdateSubtitles(activeSceneIndex, updated);
    onSelectCue(newCue.id);
  };

  // Edit cue field
  const handleEditCue = (index: number, field: keyof SubtitleCue, value: any) => {
    const updated = [...subtitles];
    const target = { ...updated[index] };

    if (field === "start") {
      const num = Math.max(0, Number(value) || 0);
      target.start = Number(num.toFixed(2));
      if (target.end <= target.start) {
        target.end = Number((target.start + 0.5).toFixed(2));
      }
    } else if (field === "end") {
      const num = Number(value) || 0;
      if (num <= target.start) {
        setTimingError(`Cue #${index + 1}: End time must be greater than start time.`);
      } else {
        setTimingError(null);
      }
      target.end = Number(num.toFixed(2));
    } else if (field === "text") {
      target.text = String(value);
    } else if (field === "enabled") {
      target.enabled = Boolean(value);
    }

    updated[index] = target;
    onUpdateSubtitles(activeSceneIndex, updated);
  };

  // Delete cue
  const handleDeleteCue = (index: number) => {
    const updated = subtitles.filter((_, i) => i !== index);
    onUpdateSubtitles(activeSceneIndex, updated);
  };

  // Clear all cues
  const handleClearAllCues = () => {
    if (confirm("Remove all caption cues for this scene?")) {
      onUpdateSubtitles(activeSceneIndex, []);
    }
  };

  return (
    <div className="w-80 border-l border-[#131929] bg-[#090d16] flex flex-col h-full overflow-hidden text-slate-200">
      {/* Panel Header */}
      <div className="p-4 border-b border-[#131929] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Subtitles size={16} className="text-blue-400" />
          <h2 className="text-sm font-semibold text-white">Captions</h2>
        </div>

        {/* Master Enabled Toggle */}
        <label className="flex items-center gap-2 cursor-pointer text-xs text-slate-400 hover:text-white">
          <span className="text-[11px]">{captionSettings.enabled ? "On" : "Off"}</span>
          <input
            type="checkbox"
            checked={captionSettings.enabled}
            onChange={handleToggleMasterEnabled}
            className="w-4 h-4 rounded bg-[#101626] border-slate-700 text-blue-500 focus:ring-0 cursor-pointer"
          />
        </label>
      </div>

      {/* Scene Switcher (if multiple scenes exist) */}
      {scenes.length > 1 && (
        <div className="px-4 py-2 bg-[#0c1220] border-b border-[#131929] flex items-center justify-between">
          <span className="text-[11px] text-slate-400">Target Scene:</span>
          <select
            value={activeSceneIndex}
            onChange={(e) => onSelectScene(Number(e.target.value))}
            className="bg-[#141d30] border border-[#1f2d48] text-xs text-white rounded px-2 py-1 outline-hidden"
          >
            {scenes.map((sc, i) => (
              <option key={sc.id} value={i}>
                Scene {i + 1} ({Math.round(sc.duration || 5)}s)
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Sub-tab Navigation (Cues vs Style) */}
      <div className="grid grid-cols-2 border-b border-[#131929] bg-[#0b101c]">
        <button
          onClick={() => setActiveSubTab("cues")}
          className={`py-2 text-xs font-medium border-b-2 transition-colors ${
            activeSubTab === "cues"
              ? "border-blue-500 text-blue-400 bg-[#101628]"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          Cues ({subtitles.length})
        </button>
        <button
          onClick={() => setActiveSubTab("style")}
          className={`py-2 text-xs font-medium border-b-2 transition-colors flex items-center justify-center gap-1 ${
            activeSubTab === "style"
              ? "border-blue-500 text-blue-400 bg-[#101628]"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <Sliders size={12} />
          Style
        </button>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* ASR Transcription Generator Box */}
        <div className="bg-[#0f1627] border border-[#1b2742] rounded-xl p-3 space-y-2.5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-300">Auto-Generate</span>
            {hasSpeechAudio ? (
              <span className="text-[9px] bg-emerald-950/80 text-emerald-300 border border-emerald-800/60 px-1.5 py-0.5 rounded font-mono">
                Speech Audio Ready
              </span>
            ) : (
              <span className="text-[9px] bg-amber-950/80 text-amber-300 border border-amber-800/60 px-1.5 py-0.5 rounded font-mono">
                No Audio Yet
              </span>
            )}
          </div>

          <p className="text-[11px] text-slate-400 leading-relaxed">
            Transcribes speech audio into timestamped word-accurate subtitle cues using local Faster-Whisper.
          </p>

          {hasSpeechAudio ? (
            <button
              onClick={() => onGenerateCaptions(activeSceneIndex)}
              disabled={isGenerating}
              className="w-full py-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 disabled:opacity-50 text-white rounded-lg text-xs font-medium flex items-center justify-center gap-1.5 transition-all shadow-md cursor-pointer"
            >
              {isGenerating ? (
                <>
                  <Loader2 size={13} className="animate-spin" />
                  <span>Transcribing with Whisper...</span>
                </>
              ) : subtitles.length > 0 ? (
                <>
                  <RefreshCw size={13} />
                  <span>Regenerate Captions</span>
                </>
              ) : (
                <>
                  <Sparkles size={13} />
                  <span>Generate Captions</span>
                </>
              )}
            </button>
          ) : (
            <div className="bg-amber-950/30 border border-amber-800/40 rounded-lg p-2.5 flex items-start gap-2">
              <AlertCircle size={14} className="text-amber-400 shrink-0 mt-0.5" />
              <p className="text-[10px] text-amber-200/90 leading-tight">
                Please generate speech for this scene in the Voice tab before transcribing.
              </p>
            </div>
          )}
        </div>

        {/* SUB-TAB: STYLE SETTINGS */}
        {activeSubTab === "style" && (
          <div className="space-y-4">
            {/* Font Size */}
            <div className="space-y-1.5">
              <div className="flex justify-between text-xs">
                <span className="text-slate-400">Font Size</span>
                <span className="text-white font-mono">{captionSettings.style.font_size}px</span>
              </div>
              <input
                type="range"
                min="16"
                max="64"
                step="2"
                value={captionSettings.style.font_size}
                onChange={(e) => handleUpdateStyle("font_size", Number(e.target.value))}
                className="w-full accent-blue-500 cursor-pointer"
              />
            </div>

            {/* Text Color */}
            <div className="space-y-1.5">
              <span className="text-xs text-slate-400 block">Text Color</span>
              <div className="flex items-center gap-2">
                {TEXT_COLORS.map((c) => (
                  <button
                    key={c}
                    onClick={() => handleUpdateStyle("color", c)}
                    style={{ backgroundColor: c }}
                    className={`w-6 h-6 rounded-full border transition-transform ${
                      captionSettings.style.color.toUpperCase() === c.toUpperCase()
                        ? "border-blue-400 scale-110 shadow-sm"
                        : "border-slate-700 hover:scale-105"
                    }`}
                  />
                ))}
                <input
                  type="color"
                  value={captionSettings.style.color}
                  onChange={(e) => handleUpdateStyle("color", e.target.value)}
                  className="w-7 h-7 rounded border border-slate-700 bg-transparent cursor-pointer ml-auto"
                />
              </div>
            </div>

            {/* Background Color */}
            <div className="space-y-1.5">
              <span className="text-xs text-slate-400 block">Background Box Color</span>
              <div className="flex items-center gap-2">
                {BG_COLORS.map((c) => (
                  <button
                    key={c}
                    onClick={() => handleUpdateStyle("background_color", c)}
                    style={{ backgroundColor: c }}
                    className={`w-6 h-6 rounded border transition-transform ${
                      captionSettings.style.background_color.toUpperCase() === c.toUpperCase()
                        ? "border-blue-400 scale-110 shadow-sm"
                        : "border-slate-700 hover:scale-105"
                    }`}
                  />
                ))}
                <input
                  type="color"
                  value={captionSettings.style.background_color}
                  onChange={(e) => handleUpdateStyle("background_color", e.target.value)}
                  className="w-7 h-7 rounded border border-slate-700 bg-transparent cursor-pointer ml-auto"
                />
              </div>
            </div>

            {/* Background Opacity */}
            <div className="space-y-1.5">
              <div className="flex justify-between text-xs">
                <span className="text-slate-400">Background Opacity</span>
                <span className="text-white font-mono">
                  {Math.round(captionSettings.style.background_opacity * 100)}%
                </span>
              </div>
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={captionSettings.style.background_opacity}
                onChange={(e) => handleUpdateStyle("background_opacity", Number(e.target.value))}
                className="w-full accent-blue-500 cursor-pointer"
              />
            </div>

            {/* Vertical Position */}
            <div className="space-y-1.5">
              <span className="text-xs text-slate-400 block">Vertical Position</span>
              <div className="grid grid-cols-3 gap-1.5 bg-[#0f1626] p-1 rounded-lg border border-[#19243b]">
                {["top", "center", "bottom"].map((pos) => (
                  <button
                    key={pos}
                    onClick={() => handleUpdateStyle("position", pos)}
                    className={`py-1 text-xs rounded capitalize transition-colors ${
                      captionSettings.style.position === pos
                        ? "bg-blue-600 text-white font-medium shadow-xs"
                        : "text-slate-400 hover:text-white"
                    }`}
                  >
                    {pos}
                  </button>
                ))}
              </div>
            </div>

            {/* Horizontal Alignment */}
            <div className="space-y-1.5">
              <span className="text-xs text-slate-400 block">Alignment</span>
              <div className="grid grid-cols-3 gap-1.5 bg-[#0f1626] p-1 rounded-lg border border-[#19243b]">
                {["left", "center", "right"].map((align) => (
                  <button
                    key={align}
                    onClick={() => handleUpdateStyle("alignment", align)}
                    className={`py-1 text-xs rounded capitalize transition-colors ${
                      captionSettings.style.alignment === align
                        ? "bg-blue-600 text-white font-medium shadow-xs"
                        : "text-slate-400 hover:text-white"
                    }`}
                  >
                    {align}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* SUB-TAB: CUES LIST */}
        {activeSubTab === "cues" && (
          <div className="space-y-3">
            {/* Actions Bar */}
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-white">Subtitle Cues</span>
              <div className="flex items-center gap-1.5">
                {subtitles.length > 0 && (
                  <button
                    onClick={handleClearAllCues}
                    className="text-[10px] text-slate-400 hover:text-red-400 px-2 py-1 rounded transition-colors"
                  >
                    Clear All
                  </button>
                )}
                <button
                  onClick={handleAddCue}
                  className="px-2 py-1 bg-blue-600 hover:bg-blue-500 text-white rounded text-xs font-medium flex items-center gap-1 transition-colors"
                >
                  <Plus size={12} />
                  <span>Add Cue</span>
                </button>
              </div>
            </div>

            {timingError && (
              <div className="p-2 bg-red-950/60 border border-red-800 text-red-200 text-xs rounded-lg flex items-center gap-1.5">
                <AlertCircle size={13} className="shrink-0" />
                <span>{timingError}</span>
              </div>
            )}

            {/* Cue Cards */}
            {subtitles.length === 0 ? (
              <div className="text-center py-8 px-4 border border-dashed border-[#1d2944] rounded-xl bg-[#0b101c]">
                <Subtitles size={24} className="mx-auto text-slate-500 mb-2 opacity-60" />
                <p className="text-xs text-slate-400 font-medium">No caption cues for this scene</p>
                <p className="text-[11px] text-slate-500 mt-1">
                  Click Generate Captions above or Add Cue manually.
                </p>
              </div>
            ) : (
              <div className="space-y-2.5">
                {subtitles.map((cue, idx) => {
                  const isSelected = cue.id === selectedCueId;
                  const isEnabled = cue.enabled !== false;

                  return (
                    <div
                      key={cue.id}
                      onClick={() => onSelectCue(cue.id)}
                      className={`p-3 rounded-xl border transition-all text-xs ${
                        isSelected
                          ? "bg-[#141e33] border-blue-500 shadow-md"
                          : isEnabled
                          ? "bg-[#0d1424] border-[#1a253c] hover:border-slate-600"
                          : "bg-[#090d17] border-[#141c2c] opacity-60"
                      }`}
                    >
                      {/* Cue Header: Timing & Controls */}
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-[10px] font-bold text-slate-400">
                          #{idx + 1}
                        </span>

                        <div className="flex items-center gap-1">
                          {/* Start time */}
                          <div className="flex items-center gap-0.5 bg-[#090d16] px-1.5 py-0.5 rounded border border-[#1b253b]">
                            <span className="text-[9px] text-slate-500">In</span>
                            <input
                              type="number"
                              step="0.1"
                              min="0"
                              value={cue.start}
                              onChange={(e) => handleEditCue(idx, "start", e.target.value)}
                              className="w-11 bg-transparent text-[10px] text-white font-mono text-right outline-hidden"
                            />
                            <span className="text-[9px] text-slate-500">s</span>
                          </div>

                          {/* End time */}
                          <div className="flex items-center gap-0.5 bg-[#090d16] px-1.5 py-0.5 rounded border border-[#1b253b]">
                            <span className="text-[9px] text-slate-500">Out</span>
                            <input
                              type="number"
                              step="0.1"
                              min="0"
                              value={cue.end}
                              onChange={(e) => handleEditCue(idx, "end", e.target.value)}
                              className="w-11 bg-transparent text-[10px] text-white font-mono text-right outline-hidden"
                            />
                            <span className="text-[9px] text-slate-500">s</span>
                          </div>

                          {/* Enable / Disable toggle */}
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleEditCue(idx, "enabled", !isEnabled);
                            }}
                            title={isEnabled ? "Disable Cue" : "Enable Cue"}
                            className="p-1 hover:text-white text-slate-400"
                          >
                            {isEnabled ? <Eye size={12} /> : <EyeOff size={12} />}
                          </button>

                          {/* Delete cue */}
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDeleteCue(idx);
                            }}
                            title="Delete Cue"
                            className="p-1 hover:text-red-400 text-slate-400"
                          >
                            <Trash2 size={12} />
                          </button>
                        </div>
                      </div>

                      {/* Editable Text Area */}
                      <textarea
                        rows={2}
                        value={cue.text}
                        onChange={(e) => handleEditCue(idx, "text", e.target.value)}
                        placeholder="Caption text..."
                        className="w-full bg-[#080c16] border border-[#1b253c] rounded p-1.5 text-xs text-white placeholder-slate-600 outline-hidden focus:border-blue-500 resize-none"
                      />
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
