"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  Music,
  Plus,
  Trash2,
  Volume2,
  VolumeX,
  Play,
  Pause,
  Repeat,
  Upload,
  Search,
  Check,
  Clock,
  Loader2,
  Sliders,
} from "lucide-react";
import { api } from "@/lib/api";

export interface AudioTrackItem {
  id: string;
  asset_id?: string | null;
  name: string;
  volume: number;
  start_time: number;
  duration?: number | null;
  loop: boolean;
  muted: boolean;
}

interface MusicPanelProps {
  workspaceId?: string;
  audioTracks: AudioTrackItem[];
  activeTrackId?: string | null;
  onSelectTrack: (trackId: string) => void;
  onAddTrack: (asset: { id: string; name: string }) => void;
  onUpdateTrack: (
    trackId: string,
    updates: Partial<{
      volume: number;
      muted: boolean;
      loop: boolean;
      start_time: number;
      name: string;
    }>
  ) => void;
  onRemoveTrack: (trackId: string) => void;
  onOpenUploadModal: () => void;
  onCommitTrack?: (actionName?: string) => void;
}

export default function MusicPanel({
  workspaceId,
  audioTracks,
  activeTrackId,
  onSelectTrack,
  onAddTrack,
  onUpdateTrack,
  onRemoveTrack,
  onOpenUploadModal,
  onCommitTrack,
}: MusicPanelProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [audioAssets, setAudioAssets] = useState<any[]>([]);
  const [isLoadingAssets, setIsLoadingAssets] = useState(false);
  const [previewingAssetId, setPreviewingAssetId] = useState<string | null>(null);

  const previewAudioRef = useRef<HTMLAudioElement | null>(null);

  // Determine active track safely
  const activeTrack =
    audioTracks.find((t) => t.id === activeTrackId) || audioTracks[0] || null;

  // Load workspace audio assets
  const loadAudioAssets = async () => {
    if (!workspaceId) return;
    setIsLoadingAssets(true);
    try {
      const res = await api.assets.list(workspaceId, { asset_type: "audio" });
      if (Array.isArray(res)) {
        setAudioAssets(res);
      }
    } catch {
      // Non-fatal loading failure
    } finally {
      setIsLoadingAssets(false);
    }
  };

  useEffect(() => {
    loadAudioAssets();
  }, [workspaceId]);

  // Clean up preview audio on unmount
  useEffect(() => {
    return () => {
      if (previewAudioRef.current) {
        previewAudioRef.current.pause();
        previewAudioRef.current = null;
      }
    };
  }, []);

  const handleTogglePreview = async (assetId: string) => {
    if (!workspaceId) return;

    if (previewingAssetId === assetId) {
      if (previewAudioRef.current) {
        previewAudioRef.current.pause();
        previewAudioRef.current.currentTime = 0;
      }
      setPreviewingAssetId(null);
      return;
    }

    try {
      setPreviewingAssetId(assetId);
      const res = await api.assets.getDownloadUrl(workspaceId, assetId);
      if (res?.download_url) {
        if (!previewAudioRef.current) {
          previewAudioRef.current = new Audio();
        }
        previewAudioRef.current.src = res.download_url;
        previewAudioRef.current.onended = () => setPreviewingAssetId(null);
        previewAudioRef.current.onerror = () => setPreviewingAssetId(null);
        await previewAudioRef.current.play();
      } else {
        setPreviewingAssetId(null);
      }
    } catch {
      setPreviewingAssetId(null);
    }
  };

  const filteredAssets = audioAssets.filter((a) => {
    const filename = a.original_filename || a.name || "";
    return !searchQuery || filename.toLowerCase().includes(searchQuery.toLowerCase());
  });

  return (
    <div className="space-y-4 select-none">
      {/* 1. Header */}
      <div className="flex items-center justify-between">
        <h4 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
          <Music size={14} className="text-blue-400" /> Background Music
        </h4>
        <button
          onClick={onOpenUploadModal}
          className="px-2.5 py-1 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white text-[11px] font-semibold rounded-lg shadow-sm flex items-center gap-1 cursor-pointer transition-all"
        >
          <Upload size={12} /> Upload Audio
        </button>
      </div>

      {/* 2. Currently Attached Track Controls */}
      <div className="p-3 bg-[#101626] border border-[#1a2640] rounded-xl space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-bold text-slate-300 uppercase tracking-wider">
            Timeline Audio ({audioTracks.length})
          </span>
          {activeTrack && (
            <button
              onClick={() => onRemoveTrack(activeTrack.id)}
              className="text-[10px] text-red-400 hover:text-red-300 flex items-center gap-0.5 cursor-pointer"
              title="Remove this track from project"
            >
              <Trash2 size={11} /> Remove
            </button>
          )}
        </div>

        {audioTracks.length === 0 ? (
          <div className="py-4 px-3 text-center rounded-lg bg-[#0c101d] border border-dashed border-[#1c2742]">
            <Music size={20} className="mx-auto text-slate-500 mb-1.5" />
            <p className="text-xs text-slate-300 font-medium">No background music added</p>
            <p className="text-[10px] text-slate-500 mt-0.5">
              Select an audio file from the library below or upload your own.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {/* Track selector chips if multiple tracks */}
            {audioTracks.length > 1 && (
              <div className="flex gap-1.5 overflow-x-auto pb-1">
                {audioTracks.map((t, idx) => (
                  <button
                    key={t.id}
                    onClick={() => onSelectTrack(t.id)}
                    className={`px-2.5 py-1 rounded-lg text-[10px] font-semibold border transition-all truncate max-w-[140px] cursor-pointer ${
                      t.id === activeTrack?.id
                        ? "bg-blue-600 border-blue-400 text-white"
                        : "bg-[#0d1322] border-[#1c2742] text-slate-400 hover:text-white"
                    }`}
                  >
                    Track {idx + 1}: {t.name}
                  </button>
                ))}
              </div>
            )}

            {activeTrack && (
              <div className="space-y-2.5 pt-1">
                {/* Track Name */}
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-white truncate max-w-[180px]">
                    {activeTrack.name}
                  </span>
                  <div className="flex items-center gap-1.5">
                    {/* Mute Toggle */}
                    <button
                      onClick={() => {
                        const nextMuted = !activeTrack.muted;
                        onUpdateTrack(activeTrack.id, { muted: nextMuted });
                        onCommitTrack?.(nextMuted ? "Mute Audio Track" : "Unmute Audio Track");
                      }}
                      className={`p-1.5 rounded-lg border transition-all cursor-pointer ${
                        activeTrack.muted
                          ? "bg-red-950/60 border-red-500/40 text-red-400"
                          : "bg-[#141b2c] border-[#1e2942] text-slate-300 hover:text-white"
                      }`}
                      title={activeTrack.muted ? "Unmute track" : "Mute track"}
                    >
                      {activeTrack.muted ? <VolumeX size={13} /> : <Volume2 size={13} />}
                    </button>

                    {/* Loop Toggle */}
                    <button
                      onClick={() => {
                        const nextLoop = !activeTrack.loop;
                        onUpdateTrack(activeTrack.id, { loop: nextLoop });
                        onCommitTrack?.(nextLoop ? "Enable Audio Loop" : "Disable Audio Loop");
                      }}
                      className={`px-2 py-1 rounded-lg border text-[10px] font-semibold flex items-center gap-1 transition-all cursor-pointer ${
                        activeTrack.loop
                          ? "bg-blue-900/60 border-blue-500/40 text-blue-300"
                          : "bg-[#141b2c] border-[#1e2942] text-slate-400 hover:text-white"
                      }`}
                      title="Loop music for full video duration"
                    >
                      <Repeat size={11} />
                      <span>{activeTrack.loop ? "Loop On" : "Loop Off"}</span>
                    </button>
                  </div>
                </div>

                {/* Volume Slider */}
                <div>
                  <div className="flex items-center justify-between text-[11px] text-slate-400 mb-1">
                    <span className="flex items-center gap-1">
                      <Sliders size={11} /> Volume
                    </span>
                    <span className="text-white font-mono font-semibold">
                      {activeTrack.muted ? "0% (Muted)" : `${Math.round(activeTrack.volume * 100)}%`}
                    </span>
                  </div>
                  <input
                    type="range"
                    min={0}
                    max={2.0}
                    step={0.05}
                    value={activeTrack.muted ? 0 : activeTrack.volume}
                    onChange={(e) => {
                      const val = Number(e.target.value);
                      onUpdateTrack(activeTrack.id, {
                        volume: val,
                        muted: val === 0,
                      });
                    }}
                    onPointerUp={() => onCommitTrack?.("Change Audio Volume")}
                    onKeyUp={() => onCommitTrack?.("Change Audio Volume")}
                    className="w-full accent-blue-500 cursor-pointer"
                  />
                </div>

                {/* Start Offset */}
                <div className="flex items-center justify-between text-[11px]">
                  <span className="text-slate-400 flex items-center gap-1">
                    <Clock size={11} /> Start Delay (s)
                  </span>
                  <div className="flex items-center gap-1.5">
                    <input
                      type="number"
                      min={0}
                      max={300}
                      step={0.5}
                      value={activeTrack.start_time || 0}
                      onChange={(e) => {
                        const val = Math.max(0, Number(e.target.value));
                        onUpdateTrack(activeTrack.id, { start_time: val });
                      }}
                      onBlur={() => onCommitTrack?.("Change Audio Delay")}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") {
                          onCommitTrack?.("Change Audio Delay");
                        }
                      }}
                      className="w-16 bg-[#121828] border border-[#1e2a44] rounded-lg px-2 py-0.5 text-xs text-white text-right focus:outline-none focus:border-blue-500"
                    />
                    <span className="text-slate-500 text-[10px]">sec</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* 3. Audio Asset Library Catalog */}
      <div className="space-y-2.5">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold text-white uppercase tracking-wider">
            Workspace Audio Library
          </span>
          <span className="text-[10px] text-slate-400">{filteredAssets.length} tracks</span>
        </div>

        {/* Search Input */}
        <div className="relative">
          <Search size={13} className="absolute left-2.5 top-2.5 text-slate-500" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search audio assets..."
            className="w-full bg-[#121828] border border-[#1e2a44] rounded-xl pl-8 pr-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
          />
        </div>

        {/* Audio Assets List */}
        <div className="space-y-2 max-h-[320px] overflow-y-auto pr-1">
          {isLoadingAssets ? (
            <div className="flex flex-col items-center justify-center py-8 text-slate-500 gap-2">
              <Loader2 size={16} className="animate-spin" />
              <span className="text-xs">Loading audio assets...</span>
            </div>
          ) : filteredAssets.length === 0 ? (
            <div className="py-6 text-center text-slate-500 text-xs">
              No audio assets found. Click "Upload Audio" to import MP3/WAV files.
            </div>
          ) : (
            filteredAssets.map((asset) => {
              const isAttached = audioTracks.some((t) => t.asset_id === asset.id);
              const isPreviewing = previewingAssetId === asset.id;
              const assetName = asset.original_filename || asset.name || "Audio File";
              const sizeMb = asset.size_bytes
                ? `${(asset.size_bytes / (1024 * 1024)).toFixed(1)} MB`
                : "";

              return (
                <div
                  key={asset.id}
                  className={`p-2.5 rounded-xl border transition-all flex items-center justify-between ${
                    isAttached
                      ? "bg-[#141e33] border-blue-500/50 shadow-xs"
                      : "bg-[#0e1322] border-[#1a233a] hover:border-[#283758]"
                  }`}
                >
                  <div className="flex items-center gap-2.5 flex-1 min-w-0 pr-2">
                    <button
                      onClick={() => handleTogglePreview(asset.id)}
                      className="w-8 h-8 rounded-lg bg-[#162035] hover:bg-[#1e2b47] flex items-center justify-center text-blue-400 hover:text-white transition-colors flex-shrink-0 cursor-pointer"
                      title={isPreviewing ? "Stop Preview" : "Preview Audio"}
                    >
                      {isPreviewing ? (
                        <Pause size={13} className="fill-blue-400" />
                      ) : (
                        <Play size={13} className="fill-blue-400 ml-0.5" />
                      )}
                    </button>

                    <div className="min-w-0 flex-1">
                      <span className="text-xs font-bold text-white truncate block">
                        {assetName}
                      </span>
                      <div className="flex items-center gap-1.5 text-[9px] text-slate-400 mt-0.5">
                        <span className="uppercase font-semibold text-blue-400">Audio</span>
                        {sizeMb && <span>• {sizeMb}</span>}
                      </div>
                    </div>
                  </div>

                  <div>
                    {isAttached ? (
                      <div className="flex items-center gap-1 text-emerald-400 text-[10px] font-semibold bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-500/30">
                        <Check size={11} /> Attached
                      </div>
                    ) : (
                      <button
                        onClick={() => onAddTrack({ id: asset.id, name: assetName })}
                        className="px-2.5 py-1 bg-blue-600 hover:bg-blue-500 text-white text-[10px] font-bold rounded-lg shadow-sm cursor-pointer transition-colors flex items-center gap-1"
                      >
                        <Plus size={11} /> Use Track
                      </button>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
