"use client";

import React, { useState, useEffect, useCallback, useMemo } from "react";
import {
  Search,
  Sparkles,
  Play,
  User,
  X,
  RefreshCw,
  Clock,
  Layers,
  AlertCircle,
  Check,
} from "lucide-react";
import AskRhysWidget from "../dashboard/AskRhysWidget";
import { useAuth } from "@/context/AuthContext";
import { useTheme } from "@/context/ThemeContext";
import { api } from "@/lib/api";

export interface LookCardItem {
  id: string;
  avatarId: string;
  avatarName: string;
  name: string;
  badge: string;
  imageUrl: string;
  previewAssetId?: string;
  prompt: string;
  isTemplate: boolean;
  category?: string;
}

export interface DesignLookStudioProps {
  onOpenStudio?: () => void;
  initialSelectedLookId?: string;
}

export default function DesignLookStudio({
  onOpenStudio,
  initialSelectedLookId,
}: DesignLookStudioProps) {
  const { theme } = useTheme();
  const isLight = theme === "light";
  const { currentWorkspace } = useAuth();

  const [looks, setLooks] = useState<LookCardItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [activeSubTab, setActiveSubTab] = useState<"recently_used" | "all_looks" | "templates">("all_looks");
  const [searchQuery, setSearchQuery] = useState("");
  const [isPromptModalOpen, setIsPromptModalOpen] = useState(false);
  const [customPrompt, setCustomPrompt] = useState("");
  const [selectedLookId, setSelectedLookId] = useState<string | null>(initialSelectedLookId || null);
  const [failedImageIds, setFailedImageIds] = useState<Set<string>>(new Set());
  const [recentLookIds, setRecentLookIds] = useState<string[]>([]);
  const [actionSuccessNotice, setActionSuccessNotice] = useState<string | null>(null);

  // Load recently used look IDs from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem("heyzen_recent_looks");
      if (stored) {
        const parsed = JSON.parse(stored);
        if (Array.isArray(parsed)) {
          setRecentLookIds(parsed);
        }
      }
    } catch {
      // LocalStorage errors ignored gracefully
    }
  }, []);

  // Fetch real workspace avatars and looks from backend API
  const fetchLooks = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const resp = await api.creative.listAvatars({}, currentWorkspace?.id);
      const items: LookCardItem[] = [];

      for (const avatar of resp || []) {
        const avatarLooks = avatar.looks || [];
        const defaultBadge =
          avatar.provider_metadata?.engine_version ||
          (avatar.avatar_type === "preset" ? "Avatar IV" : "Avatar V");

        if (avatarLooks.length > 0) {
          for (const l of avatarLooks) {
            items.push({
              id: l.id,
              avatarId: avatar.id,
              avatarName: avatar.name,
              name: l.name,
              badge: l.configuration?.engine_version || defaultBadge,
              imageUrl: l.preview_url || l.configuration?.preview_url || avatar.preview_url || "",
              previewAssetId: l.preview_asset_id || avatar.preview_asset_id,
              prompt: l.description || avatar.description || `${l.name} framing for ${avatar.name}`,
              isTemplate: avatar.avatar_type === "preset",
              category: avatar.provider_metadata?.category || "Professional",
            });
          }
        } else {
          // If avatar has no child looks, treat the avatar preview itself as a primary look
          items.push({
            id: avatar.id,
            avatarId: avatar.id,
            avatarName: avatar.name,
            name: avatar.name,
            badge: defaultBadge,
            imageUrl: avatar.preview_url || "",
            previewAssetId: avatar.preview_asset_id,
            prompt: avatar.description || `${avatar.name} default portrait look`,
            isTemplate: avatar.avatar_type === "preset",
            category: avatar.provider_metadata?.category || "Professional",
          });
        }
      }

      setLooks(items);
    } catch (err: any) {
      setError(err?.message || "Failed to load looks from backend");
    } finally {
      setIsLoading(false);
    }
  }, [currentWorkspace?.id]);

  useEffect(() => {
    fetchLooks();
  }, [fetchLooks]);

  // Handle Look selection and opening Studio
  const handleSelectLook = (look: LookCardItem) => {
    setSelectedLookId(look.id);

    // Save to recently used looks in localStorage
    try {
      const updated = [look.id, ...recentLookIds.filter((id) => id !== look.id)].slice(0, 20);
      setRecentLookIds(updated);
      localStorage.setItem("heyzen_recent_looks", JSON.stringify(updated));
    } catch {
      // LocalStorage errors ignored
    }

    // Show temporary feedback toast
    setActionSuccessNotice(`Look "${look.name}" selected! Opening Studio...`);
    setTimeout(() => {
      setActionSuccessNotice(null);
    }, 2500);

    if (onOpenStudio) {
      onOpenStudio();
    }
  };

  const handleImageError = (lookId: string) => {
    setFailedImageIds((prev) => new Set(prev).add(lookId));
  };

  // Filter looks by active sub-tab
  const currentTabLooks = useMemo(() => {
    if (activeSubTab === "recently_used") {
      return looks.filter((item) => recentLookIds.includes(item.id));
    }
    if (activeSubTab === "templates") {
      return looks.filter((item) => item.isTemplate);
    }
    return looks;
  }, [activeSubTab, looks, recentLookIds]);

  // Apply search query across look name, avatar name, prompt, badge, and category
  const filteredLooks = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return currentTabLooks;
    return currentTabLooks.filter(
      (item) =>
        item.name.toLowerCase().includes(q) ||
        item.avatarName.toLowerCase().includes(q) ||
        (item.prompt && item.prompt.toLowerCase().includes(q)) ||
        item.badge.toLowerCase().includes(q) ||
        (item.category && item.category.toLowerCase().includes(q))
    );
  }, [currentTabLooks, searchQuery]);

  return (
    <div
      id="design-look-studio-root"
      data-testid="design-look-studio-root"
      className={`flex-1 h-screen overflow-y-auto flex flex-col font-sans select-none relative transition-colors duration-200 overflow-x-hidden ${
        isLight ? "bg-slate-50 text-slate-900" : "bg-[#07090e] text-slate-100"
      }`}
    >
      {/* 1. TOP BAR WITH TITLE & ACTIONS */}
      <div className="w-full px-6 md:px-10 pt-7 pb-4 flex items-center justify-between z-20">
        <div>
          <h1
            id="design-look-heading"
            data-testid="design-look-heading"
            className={`text-2xl md:text-3xl font-extrabold tracking-tight transition-colors ${
              isLight ? "text-slate-900" : "text-white"
            }`}
          >
            What new look are you imagining?
          </h1>
          <p className={`text-xs mt-1 ${isLight ? "text-slate-500" : "text-slate-400"}`}>
            Browse existing studio looks or create custom styles for your avatars.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            id="generate-look-ai-btn"
            data-testid="generate-look-ai-btn"
            onClick={() => setIsPromptModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-cyan-500 via-blue-600 to-purple-600 hover:from-cyan-400 hover:to-purple-500 text-white text-xs font-bold rounded-full shadow-md shadow-blue-500/20 transition-all cursor-pointer hover:scale-102"
          >
            <Sparkles size={14} />
            <span>Generate with AI</span>
          </button>

          <AskRhysWidget />
        </div>
      </div>

      {/* Action Success Toast Notice */}
      {actionSuccessNotice && (
        <div className="fixed top-6 right-6 z-50 animate-in fade-in slide-in-from-top-3 duration-300">
          <div className="bg-cyan-500 text-slate-950 px-4 py-2 rounded-xl text-xs font-bold shadow-xl flex items-center gap-2">
            <Check size={16} />
            <span>{actionSuccessNotice}</span>
          </div>
        </div>
      )}

      {/* 2. SUB-TABS & SEARCH BAR */}
      <div className="max-w-6xl w-full mx-auto px-6 md:px-10 pt-1 pb-4">
        <div
          className={`flex flex-col sm:flex-row items-stretch sm:items-center justify-between border-b pb-3 gap-3 transition-colors ${
            isLight ? "border-slate-200" : "border-[#141b2c]"
          }`}
        >
          {/* Sub Tabs: Recently used / All looks / Templates */}
          <div className="flex items-center gap-6 text-xs font-bold">
            <button
              id="tab-recently-used"
              data-testid="tab-recently-used"
              onClick={() => setActiveSubTab("recently_used")}
              className={`pb-1.5 transition-colors cursor-pointer relative ${
                activeSubTab === "recently_used"
                  ? isLight
                    ? "text-slate-900 font-extrabold"
                    : "text-white"
                  : isLight
                  ? "text-slate-500 hover:text-slate-800"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Recently used
              {activeSubTab === "recently_used" && (
                <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-cyan-500 rounded-full shadow-xs"></span>
              )}
            </button>

            <button
              id="tab-all-looks"
              data-testid="tab-all-looks"
              onClick={() => setActiveSubTab("all_looks")}
              className={`pb-1.5 transition-colors cursor-pointer relative ${
                activeSubTab === "all_looks"
                  ? isLight
                    ? "text-slate-900 font-extrabold"
                    : "text-white"
                  : isLight
                  ? "text-slate-500 hover:text-slate-800"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              All looks
              {activeSubTab === "all_looks" && (
                <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-cyan-500 rounded-full shadow-xs"></span>
              )}
            </button>

            <button
              id="tab-templates"
              data-testid="tab-templates"
              onClick={() => setActiveSubTab("templates")}
              className={`pb-1.5 transition-colors cursor-pointer relative ${
                activeSubTab === "templates"
                  ? isLight
                    ? "text-slate-900 font-extrabold"
                    : "text-white"
                  : isLight
                  ? "text-slate-500 hover:text-slate-800"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Templates
              {activeSubTab === "templates" && (
                <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-cyan-500 rounded-full shadow-xs"></span>
              )}
            </button>
          </div>

          {/* Search Bar */}
          <div className="relative w-full sm:w-64">
            <Search
              size={13}
              className={`absolute left-3 top-2.5 ${isLight ? "text-slate-400" : "text-slate-400"}`}
            />
            <input
              id="search-looks-input"
              data-testid="search-looks-input"
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search looks..."
              className={`w-full rounded-full pl-8 pr-8 py-1.5 text-xs focus:outline-none transition-colors border ${
                isLight
                  ? "bg-white border-slate-200 text-slate-900 placeholder-slate-400 focus:border-cyan-500 shadow-xs"
                  : "bg-[#111728] border-[#1e2a44] text-white placeholder-slate-400 focus:border-cyan-500"
              }`}
            />
            {searchQuery && (
              <button
                id="search-looks-clear-btn"
                data-testid="search-looks-clear-btn"
                onClick={() => setSearchQuery("")}
                className={`absolute right-2.5 top-2 cursor-pointer ${
                  isLight ? "text-slate-400 hover:text-slate-700" : "text-slate-400 hover:text-white"
                }`}
                title="Clear search"
              >
                <X size={13} />
              </button>
            )}
          </div>
        </div>
      </div>

      {/* 3. MAIN GALLERY VIEW AREA */}
      <div className="max-w-6xl w-full mx-auto px-6 md:px-10 pb-20 flex-1">
        {isLoading ? (
          /* Loading State */
          <div
            id="looks-loading-state"
            data-testid="looks-loading-state"
            className={`p-16 text-center rounded-2xl flex flex-col items-center justify-center border ${
              isLight ? "bg-white border-slate-200" : "bg-[#090d17] border-[#172035]"
            }`}
          >
            <div className="w-8 h-8 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin mb-3"></div>
            <p className={`text-xs ${isLight ? "text-slate-500" : "text-slate-400"}`}>
              Loading looks from workspace...
            </p>
          </div>
        ) : error ? (
          /* API Error State */
          <div
            id="looks-error-state"
            data-testid="looks-error-state"
            className={`p-12 text-center rounded-2xl border ${
              isLight ? "bg-rose-50/50 border-rose-200" : "bg-[#090d17] border-red-500/30"
            }`}
          >
            <AlertCircle size={28} className="text-red-500 mx-auto mb-2" />
            <p className="text-sm text-red-500 font-semibold mb-1">Failed to load looks</p>
            <p className="text-xs text-slate-500 mb-4">{error}</p>
            <button
              onClick={fetchLooks}
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-semibold transition-colors cursor-pointer"
            >
              <RefreshCw size={13} />
              <span>Retry</span>
            </button>
          </div>
        ) : filteredLooks.length === 0 ? (
          /* Empty Results States */
          <div
            id="looks-empty-state"
            data-testid="looks-empty-state"
            className={`p-14 text-center rounded-2xl flex flex-col items-center justify-center border ${
              isLight ? "bg-white border-slate-200" : "bg-[#090d17] border-[#172035]"
            }`}
          >
            {searchQuery.trim() !== "" ? (
              <>
                <Search size={32} className="text-slate-400 mb-3" />
                <p
                  className={`text-sm font-semibold mb-1 ${
                    isLight ? "text-slate-700" : "text-slate-300"
                  }`}
                >
                  No looks match &ldquo;{searchQuery}&rdquo;
                </p>
                <p className="text-xs text-slate-500 mb-4">
                  Check your spelling or try searching for another style or avatar name.
                </p>
                <button
                  onClick={() => setSearchQuery("")}
                  className="px-4 py-1.5 bg-cyan-500 text-slate-950 font-bold rounded-full text-xs hover:bg-cyan-400 transition-colors cursor-pointer"
                >
                  Clear search
                </button>
              </>
            ) : activeSubTab === "recently_used" ? (
              <>
                <Clock size={32} className="text-slate-400 mb-3" />
                <p
                  className={`text-sm font-semibold mb-1 ${
                    isLight ? "text-slate-700" : "text-slate-300"
                  }`}
                >
                  No recently used looks
                </p>
                <p className="text-xs text-slate-500 mb-4">
                  Looks you select or use in Studio will appear here for rapid access.
                </p>
                <button
                  onClick={() => setActiveSubTab("all_looks")}
                  className="px-4 py-1.5 bg-cyan-500 text-slate-950 font-bold rounded-full text-xs hover:bg-cyan-400 transition-colors cursor-pointer"
                >
                  Explore All Looks
                </button>
              </>
            ) : activeSubTab === "templates" ? (
              <>
                <Layers size={32} className="text-slate-400 mb-3" />
                <p
                  className={`text-sm font-semibold mb-1 ${
                    isLight ? "text-slate-700" : "text-slate-300"
                  }`}
                >
                  No template looks found
                </p>
                <p className="text-xs text-slate-500">
                  Preset looks and templates will appear here when configured in workspace presets.
                </p>
              </>
            ) : (
              <>
                <User size={32} className="text-slate-400 mb-3" />
                <p
                  className={`text-sm font-semibold mb-1 ${
                    isLight ? "text-slate-700" : "text-slate-300"
                  }`}
                >
                  No looks available
                </p>
                <p className="text-xs text-slate-500">
                  Create or seed avatars to design and explore looks.
                </p>
              </>
            )}
          </div>
        ) : (
          /* RESPONSIVE LOOKS GRID WITH CONSISTENT 1:1 ASPECT RATIO */
          <div
            id="looks-cards-grid"
            data-testid="looks-cards-grid"
            className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 sm:gap-5"
          >
            {filteredLooks.map((look) => {
              const isSelected = selectedLookId === look.id;
              const isMissingMedia = !look.imageUrl || failedImageIds.has(look.id);

              return (
                <div
                  key={look.id}
                  id={`look-card-${look.id}`}
                  data-testid={`look-card-${look.id}`}
                  onClick={() => handleSelectLook(look)}
                  className={`rounded-2xl overflow-hidden shadow-sm hover:shadow-xl transition-all duration-300 relative group cursor-pointer border flex flex-col ${
                    isSelected
                      ? "ring-2 ring-cyan-500 border-cyan-500"
                      : isLight
                      ? "bg-white border-slate-200 hover:border-cyan-500"
                      : "bg-[#0c111e] border-[#1c2740] hover:border-cyan-500/60"
                  }`}
                >
                  {/* Consistent 1:1 Aspect Ratio Media Container */}
                  <div className="w-full aspect-square relative overflow-hidden bg-slate-900 select-none">
                    {!isMissingMedia ? (
                      <img
                        src={look.imageUrl}
                        alt={`${look.name} - ${look.avatarName}`}
                        className="w-full h-full object-cover object-top group-hover:scale-105 transition-transform duration-500 brightness-95 group-hover:brightness-100"
                        loading="lazy"
                        onError={() => handleImageError(look.id)}
                      />
                    ) : (
                      /* Project Fallback State for Missing Media */
                      <div className="w-full h-full flex flex-col items-center justify-center p-4 bg-slate-800/80 text-slate-400">
                        <div className="w-12 h-12 rounded-full bg-slate-700/80 flex items-center justify-center mb-2">
                          <User size={24} className="text-slate-300" />
                        </div>
                        <span className="text-[11px] font-semibold text-slate-300 text-center truncate max-w-full px-2">
                          {look.name}
                        </span>
                        <span className="text-[9px] text-amber-400/90 font-medium mt-1 uppercase tracking-wider">
                          Media Missing
                        </span>
                      </div>
                    )}

                    {/* Subtle Gradient Scrim at bottom to ensure badge legibility */}
                    <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent pointer-events-none" />

                    {/* Look Name Badge at Bottom Left (Constrained max-w to avoid overlap) */}
                    <div className="absolute bottom-3 left-3 max-w-[calc(100%-5.5rem)] z-10 flex flex-col pointer-events-none">
                      <span
                        className="bg-black/70 backdrop-blur-md px-2.5 py-1 rounded-lg text-white text-[11px] font-semibold border border-white/10 shadow-sm truncate block"
                        title={`${look.name} (${look.avatarName})`}
                      >
                        {look.name}
                      </span>
                    </div>

                    {/* Yellow/Gold Engine Metadata Badge at Bottom Right */}
                    <div
                      title={`Model Engine: ${look.badge}`}
                      className="absolute bottom-3 right-3 bg-amber-400 text-slate-950 font-extrabold text-[9px] px-2.5 py-1 rounded-full shadow-md z-10 pointer-events-none select-none tracking-wide"
                    >
                      {look.badge}
                    </div>

                    {/* On-Hover Action Overlay */}
                    <div className="absolute inset-0 bg-black/45 backdrop-blur-xs opacity-0 group-hover:opacity-100 transition-opacity duration-200 flex items-center justify-center gap-2 z-20">
                      <span className="px-4 py-1.5 bg-cyan-500 hover:bg-cyan-400 text-slate-950 text-xs font-bold rounded-full shadow-lg flex items-center gap-1.5 transition-transform group-hover:scale-105">
                        <Play size={12} className="fill-slate-950" />
                        <span>Use Look</span>
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* AI Generate Look Prompt Modal */}
      {isPromptModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-md p-4 animate-in fade-in duration-200">
          <div
            className={`w-full max-w-lg rounded-3xl p-6 shadow-2xl border transition-colors ${
              isLight ? "bg-white text-slate-900 border-slate-200" : "bg-[#0e1322] text-white border-[#22304f]"
            }`}
          >
            <h3 className="text-lg font-bold mb-1 flex items-center gap-2">
              <Sparkles size={18} className="text-cyan-400" />
              <span>Describe Your New Look</span>
            </h3>
            <p className={`text-xs mb-4 ${isLight ? "text-slate-500" : "text-slate-400"}`}>
              Specify any outfit, styling, scenery, and lighting while keeping your avatar&apos;s face identity locked.
            </p>

            <textarea
              rows={3}
              value={customPrompt}
              onChange={(e) => setCustomPrompt(e.target.value)}
              placeholder="e.g. Wearing a sleek navy blue executive blazer in a modern high-rise glass boardroom at golden hour..."
              className={`w-full rounded-2xl p-3.5 text-xs focus:outline-none focus:border-cyan-500 mb-4 border ${
                isLight
                  ? "bg-slate-50 border-slate-200 text-slate-900 placeholder-slate-400"
                  : "bg-[#121828] border-[#22304d] text-white placeholder-slate-400"
              }`}
            ></textarea>

            <div className="flex justify-end gap-2.5">
              <button
                onClick={() => setIsPromptModalOpen(false)}
                className={`px-4 py-2 rounded-xl text-xs font-semibold cursor-pointer ${
                  isLight ? "text-slate-600 hover:bg-slate-100" : "text-slate-400 hover:bg-[#18233a]"
                }`}
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  setActionSuccessNotice("Styling AI Look... Generating avatar look!");
                  setIsPromptModalOpen(false);
                }}
                className="px-5 py-2 bg-gradient-to-r from-cyan-500 to-blue-600 text-white text-xs font-bold rounded-xl shadow-md cursor-pointer hover:opacity-95"
              >
                Generate Look (20 Credits)
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
