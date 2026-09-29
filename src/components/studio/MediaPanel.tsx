"use client";

import React, { useState, useEffect } from "react";
import {
  Image as ImageIcon,
  Film,
  Music,
  Upload,
  Search,
  Check,
  Loader2,
  Layers,
  Wallpaper,
} from "lucide-react";
import { api } from "@/lib/api";

import MediaLayerPanel from "./MediaLayerPanel";
import { StudioScene } from "./VidoAIStudio";

export interface MediaAssetItem {
  id: string;
  name: string;
  type: "image" | "video" | "audio" | "doc";
  size_bytes?: number;
  mime_type?: string;
  created_at?: string;
}

interface MediaPanelProps {
  workspaceId?: string;
  onSetSceneBackground: (asset: { id: string; type: string; name: string }) => void;
  onAddMediaLayer: (asset: { id: string; type: string; name: string }) => void;
  onAddMusicTrack?: (asset: { id: string; name: string }) => void;
  onOpenUploadModal: () => void;
  currentBackgroundAssetId?: string | null;
  scenes?: StudioScene[];
  activeSceneIndex?: number;
  onSelectScene?: (idx: number) => void;
  selectedMediaLayerId?: string | null;
  onSelectMediaLayer?: (id: string | null) => void;
  onUpdateMediaLayers?: (sceneIndex: number, layers: any[]) => void;
  assetUrls?: Record<string, string>;
}

export default function MediaPanel({
  workspaceId,
  onSetSceneBackground,
  onAddMediaLayer,
  onAddMusicTrack,
  onOpenUploadModal,
  currentBackgroundAssetId,
  scenes = [],
  activeSceneIndex = 0,
  onSelectScene,
  selectedMediaLayerId = null,
  onSelectMediaLayer,
  onUpdateMediaLayers,
  assetUrls = {},
}: MediaPanelProps) {
  const [subTab, setSubTab] = useState<"library" | "layers">("library");
  const [filterType, setFilterType] = useState<"all" | "image" | "video" | "audio">("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [assets, setAssets] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [mediaUrls, setMediaUrls] = useState<Record<string, string>>({});

  const loadAssets = async () => {
    if (!workspaceId) return;
    setIsLoading(true);
    try {
      const params: any = {};
      if (filterType !== "all") {
        params.asset_type = filterType;
      }
      const res = await api.assets.list(workspaceId, params);
      if (Array.isArray(res)) {
        setAssets(res);
      }
    } catch {
      // Non-fatal
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadAssets();
  }, [workspaceId, filterType]);

  // Pre-load download URLs for image thumbnails
  useEffect(() => {
    if (!workspaceId || assets.length === 0) return;
    const imageAssets = assets.filter((a) => a.asset_type === "image" && !mediaUrls[a.id]);
    if (imageAssets.length === 0) return;

    imageAssets.slice(0, 8).forEach((a) => {
      api.assets
        .getDownloadUrl(workspaceId, a.id)
        .then((res) => {
          if (res?.download_url) {
            setMediaUrls((prev) => ({ ...prev, [a.id]: res.download_url }));
          }
        })
        .catch(() => {});
    });
  }, [workspaceId, assets, mediaUrls]);

  // Synchronize subTab with selectedMediaLayerId if a layer was clicked
  useEffect(() => {
    if (selectedMediaLayerId) {
      setSubTab("layers");
    }
  }, [selectedMediaLayerId]);

  const activeScene = scenes[activeSceneIndex];
  const activeMediaLayers = (activeScene?.layers || []).filter(
    (l: any) => l.type === "image" || l.type === "video" || l.type === "media"
  );

  const filteredAssets = assets.filter((a) => {
    const filename = a.original_filename || a.name || "";
    return !searchQuery || filename.toLowerCase().includes(searchQuery.toLowerCase());
  });

  return (
    <div className="space-y-4 select-none">
      {/* 0. Top Sub-tab Switcher (Library vs Layers) if scenes are provided */}
      {scenes.length > 0 && onUpdateMediaLayers && (
        <div className="flex bg-[#0c111e] p-1 rounded-xl border border-[#1a253d] text-[11px] gap-1">
          <button
            onClick={() => setSubTab("library")}
            className={`flex-1 py-1.5 rounded-lg font-semibold transition-all cursor-pointer flex items-center justify-center gap-1.5 ${
              subTab === "library"
                ? "bg-blue-600 text-white shadow-xs"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <ImageIcon size={13} />
            <span>Library</span>
          </button>
          <button
            onClick={() => setSubTab("layers")}
            className={`flex-1 py-1.5 rounded-lg font-semibold transition-all cursor-pointer flex items-center justify-center gap-1.5 ${
              subTab === "layers"
                ? "bg-blue-600 text-white shadow-xs"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <Layers size={13} />
            <span>Active Layers ({activeMediaLayers.length})</span>
          </button>
        </div>
      )}

      {/* RENDER LAYERS INSPECTOR */}
      {subTab === "layers" && scenes.length > 0 && onUpdateMediaLayers ? (
        <MediaLayerPanel
          scenes={scenes}
          activeSceneIndex={activeSceneIndex}
          onSelectScene={onSelectScene || (() => {})}
          selectedMediaLayerId={selectedMediaLayerId}
          onSelectMediaLayer={onSelectMediaLayer || (() => {})}
          onUpdateMediaLayers={onUpdateMediaLayers}
          onOpenMediaLibrary={() => setSubTab("library")}
          assetUrls={assetUrls}
        />
      ) : (
        <div className="space-y-4 select-none">
          {/* 1. Header with Upload */}
          <div className="flex items-center justify-between">
            <h4 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
              <ImageIcon size={14} className="text-blue-400" /> Media Library
            </h4>
            <button
              onClick={onOpenUploadModal}
              className="px-2.5 py-1 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white text-[11px] font-semibold rounded-lg shadow-sm flex items-center gap-1 cursor-pointer transition-all"
            >
              <Upload size={12} /> Upload Media
            </button>
          </div>

          {/* 2. Category Filter Tabs */}
          <div className="flex gap-1 bg-[#101625] p-1 rounded-xl border border-[#1e2940] text-[10px]">
        {(["all", "image", "video", "audio"] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setFilterType(tab)}
            className={`flex-1 py-1 rounded-lg capitalize font-semibold transition-all cursor-pointer ${
              filterType === tab
                ? "bg-blue-600 text-white shadow-xs"
                : "text-slate-400 hover:text-white"
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* 3. Search Bar */}
      <div className="relative">
        <Search size={13} className="absolute left-2.5 top-2.5 text-slate-500" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search workspace media..."
          className="w-full bg-[#121828] border border-[#1e2a44] rounded-xl pl-8 pr-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
        />
      </div>

      {/* 4. Assets Grid / List */}
      <div className="space-y-2.5 max-h-[440px] overflow-y-auto pr-1">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-10 text-slate-500 gap-2">
            <Loader2 size={18} className="animate-spin" />
            <span className="text-xs">Loading workspace assets...</span>
          </div>
        ) : filteredAssets.length === 0 ? (
          <div className="py-8 text-center text-slate-500 text-xs bg-[#0c101d] rounded-xl border border-dashed border-[#1c2742] p-4">
            <p className="font-semibold text-slate-400">No media assets found</p>
            <p className="text-[10px] text-slate-500 mt-1">
              Click "Upload Media" above to upload images, videos, or audio.
            </p>
          </div>
        ) : (
          filteredAssets.map((asset) => {
            const assetName = asset.original_filename || asset.name || "Media File";
            const aType = asset.asset_type || "image";
            const isCurrentBg = currentBackgroundAssetId === asset.id;
            const sizeMb = asset.size_bytes
              ? `${(asset.size_bytes / (1024 * 1024)).toFixed(1)} MB`
              : "";
            const thumbUrl = mediaUrls[asset.id];

            return (
              <div
                key={asset.id}
                className={`p-2.5 rounded-xl border transition-all ${
                  isCurrentBg
                    ? "bg-[#141f33] border-blue-500/60 shadow-xs"
                    : "bg-[#0e1322] border-[#1a233a] hover:border-[#283758]"
                }`}
              >
                <div className="flex items-center gap-2.5">
                  {/* Thumbnail / Icon */}
                  <div className="w-12 h-12 rounded-lg bg-[#151c2e] border border-white/5 flex items-center justify-center overflow-hidden flex-shrink-0">
                    {thumbUrl ? (
                      <img
                        src={thumbUrl}
                        alt={assetName}
                        className="w-full h-full object-cover"
                      />
                    ) : aType === "video" ? (
                      <Film size={20} className="text-purple-400" />
                    ) : aType === "audio" ? (
                      <Music size={20} className="text-blue-400" />
                    ) : (
                      <ImageIcon size={20} className="text-emerald-400" />
                    )}
                  </div>

                  {/* Asset Info */}
                  <div className="min-w-0 flex-1">
                    <span className="text-xs font-bold text-white truncate block">
                      {assetName}
                    </span>
                    <div className="flex items-center gap-1.5 text-[9px] text-slate-400 mt-0.5">
                      <span
                        className={`uppercase font-semibold px-1 py-0.2 rounded text-[8px] ${
                          aType === "video"
                            ? "bg-purple-900/60 text-purple-300"
                            : aType === "audio"
                            ? "bg-blue-900/60 text-blue-300"
                            : "bg-emerald-900/60 text-emerald-300"
                        }`}
                      >
                        {aType}
                      </span>
                      {sizeMb && <span>• {sizeMb}</span>}
                    </div>
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="mt-2 pt-2 border-t border-white/5 flex items-center justify-end gap-1.5">
                  {aType === "audio" ? (
                    onAddMusicTrack && (
                      <button
                        onClick={() =>
                          onAddMusicTrack({ id: asset.id, name: assetName })
                        }
                        className="px-2.5 py-1 bg-blue-600 hover:bg-blue-500 text-white text-[10px] font-semibold rounded-lg cursor-pointer transition-colors flex items-center gap-1"
                      >
                        <Music size={11} /> Use as Music
                      </button>
                    )
                  ) : (
                    <>
                      {/* Add as Canvas Layer */}
                      <button
                        onClick={() => {
                          onAddMediaLayer({
                            id: asset.id,
                            type: aType,
                            name: assetName,
                          });
                          setSubTab("layers");
                        }}
                        className="px-2 py-1 bg-[#162035] hover:bg-[#1f2d4a] text-slate-300 hover:text-white text-[10px] font-semibold rounded-lg border border-[#1e2c47] cursor-pointer transition-colors flex items-center gap-1"
                        title="Add as overlay layer to this scene"
                      >
                        <Layers size={11} /> Add Layer
                      </button>

                      {/* Set as Scene Background */}
                      <button
                        onClick={() =>
                          onSetSceneBackground({
                            id: asset.id,
                            type: aType,
                            name: assetName,
                          })
                        }
                        className={`px-2 py-1 text-[10px] font-semibold rounded-lg cursor-pointer transition-colors flex items-center gap-1 ${
                          isCurrentBg
                            ? "bg-emerald-600/80 text-white"
                            : "bg-blue-600 hover:bg-blue-500 text-white"
                        }`}
                        title="Set as background for this scene"
                      >
                        {isCurrentBg ? (
                          <>
                            <Check size={11} /> Current BG
                          </>
                        ) : (
                          <>
                            <Wallpaper size={11} /> Set Background
                          </>
                        )}
                      </button>
                    </>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
      )}
    </div>
  );
}
