"use client";

import React, { useState, useMemo } from "react";
import {
  Mic,
  Video,
  Sparkles,
  Languages,
  Film,
  FileText,
  Layers,
  Scissors,
  Camera,
  Maximize2,
  MousePointerClick,
  Palette,
  Volume2,
  Search,
  ArrowRight,
  X,
  Play,
  Check,
  Info,
} from "lucide-react";
import AskRhysWidget from "../dashboard/AskRhysWidget";
import FeaturedAppModals, { FeaturedModalType } from "./FeaturedAppModals";
import { useTheme } from "@/context/ThemeContext";
import {
  APP_REGISTRY,
  AppDefinition,
  AppCategory,
  filterApps,
} from "@/lib/appRegistry";
import { VideoAgentGenerationContext } from "../create/VideoAgentWorkspace";

interface AppLibraryProps {
  onOpenStudio?: (projectId?: string) => void;
  onNavigateVideoAgent?: () => void;
  onLaunchVideoAgentWithContext?: (context: VideoAgentGenerationContext) => void;
  onNavigateTranslate?: () => void;
  onNavigateSingleScene?: () => void;
  onNavigateSceneByScene?: () => void;
  onNavigateBrand?: () => void;
  onNavigateDesignLook?: () => void;
  onNavigateProjects?: () => void;
}

// Icon mapper for canonical app registry
function renderAppIcon(iconName: string, className = "w-6 h-6 text-white") {
  switch (iconName) {
    case "Sparkles":
      return <Sparkles className={className} />;
    case "Video":
      return <Video className={className} />;
    case "Film":
      return <Film className={className} />;
    case "Layers":
      return <Layers className={className} />;
    case "Mic":
      return <Mic className={className} />;
    case "Palette":
      return <Palette className={className} />;
    case "FileText":
      return <FileText className={className} />;
    case "Camera":
      return <Camera className={className} />;
    case "Volume2":
      return <Volume2 className={className} />;
    case "Maximize2":
      return <Maximize2 className={className} />;
    case "Languages":
      return <Languages className={className} />;
    case "Scissors":
      return <Scissors className={className} />;
    case "MousePointerClick":
      return <MousePointerClick className={className} />;
    default:
      return <Sparkles className={className} />;
  }
}

export default function AppLibrary({
  onOpenStudio,
  onNavigateVideoAgent,
  onLaunchVideoAgentWithContext,
  onNavigateTranslate,
  onNavigateSingleScene,
  onNavigateSceneByScene,
  onNavigateBrand,
  onNavigateDesignLook,
  onNavigateProjects,
}: AppLibraryProps) {
  const { theme } = useTheme();
  const isLight = theme === "light";

  const [activeTab, setActiveTab] = useState<"all" | AppCategory>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedApp, setSelectedApp] = useState<AppDefinition | null>(null);
  const [activeFeaturedModal, setActiveFeaturedModal] = useState<FeaturedModalType | null>(null);

  // Filter apps based on active category tab and search query
  const filteredApps = useMemo(() => {
    return filterApps(APP_REGISTRY, activeTab, searchQuery);
  }, [activeTab, searchQuery]);

  // Grouped for "all" tab display
  const createApps = useMemo(
    () => filteredApps.filter((a) => a.category === "create"),
    [filteredApps]
  );
  const enhanceApps = useMemo(
    () => filteredApps.filter((a) => a.category === "enhance"),
    [filteredApps]
  );
  const editApps = useMemo(
    () => filteredApps.filter((a) => a.category === "edit"),
    [filteredApps]
  );
  const interactiveApps = useMemo(
    () => filteredApps.filter((a) => a.category === "interactive"),
    [filteredApps]
  );

  const handleLaunchApp = (app: AppDefinition) => {
    switch (app.actionType) {
      case "navigate_video_agent":
        if (onNavigateVideoAgent) onNavigateVideoAgent();
        else if (onOpenStudio) onOpenStudio();
        break;
      case "navigate_studio":
        if (onOpenStudio) onOpenStudio();
        break;
      case "navigate_single_scene":
        if (onNavigateSingleScene) onNavigateSingleScene();
        else if (onOpenStudio) onOpenStudio();
        break;
      case "navigate_scene_by_scene":
        if (onNavigateSceneByScene) onNavigateSceneByScene();
        else if (onOpenStudio) onOpenStudio();
        break;
      case "navigate_translate":
        if (onNavigateTranslate) onNavigateTranslate();
        break;
      case "navigate_brand":
        if (onNavigateBrand) onNavigateBrand();
        else if (onOpenStudio) onOpenStudio();
        break;
      case "navigate_design_look":
        if (onNavigateDesignLook) onNavigateDesignLook();
        else if (onOpenStudio) onOpenStudio();
        break;
      case "modal_generator":
        setActiveFeaturedModal("generator");
        break;
      case "modal_podcast":
        setActiveFeaturedModal("podcast");
        break;
      case "modal_speech":
        setActiveFeaturedModal("speech");
        break;
      case "modal_pdf":
        setActiveFeaturedModal("pdf");
        break;
      case "modal_shots":
        setActiveFeaturedModal("shots");
        break;
      case "modal_upscale":
        setActiveFeaturedModal("upscale");
        break;
      case "modal_clipping":
        setActiveFeaturedModal("clipping");
        break;
      case "modal_faceswap":
        setActiveFeaturedModal("faceswap");
        break;
      case "modal_interactive":
        setActiveFeaturedModal("interactive");
        break;
      default:
        setSelectedApp(app);
        break;
    }
  };

  const handleClearSearch = () => {
    setSearchQuery("");
  };

  return (
    <div
      className={`flex-1 h-screen overflow-y-auto overflow-x-hidden flex flex-col font-sans select-none relative scrollbar-thin ${
        isLight
          ? "bg-slate-50 text-slate-800 scrollbar-thumb-slate-300"
          : "bg-[#07090e] text-slate-100 scrollbar-thumb-slate-800"
      }`}
    >
      {/* 1. TOP HEADER */}
      <header
        className={`w-full max-w-7xl mx-auto px-6 sm:px-10 pt-8 pb-5 flex items-center justify-between border-b z-20 shrink-0 ${
          isLight ? "border-slate-200" : "border-[#1B2940]/40"
        }`}
      >
        <div>
          <h1
            id="apps-page-title"
            data-testid="apps-page-title"
            className={`text-3xl sm:text-4xl font-black tracking-tight ${
              isLight ? "text-slate-900" : "text-white"
            }`}
          >
            App Library
          </h1>
          <p
            className={`text-xs sm:text-sm mt-1 font-medium ${
              isLight ? "text-slate-500" : "text-slate-400"
            }`}
          >
            Use HeyGen Apps to up-level your creative process
          </p>
        </div>

        <div>
          <AskRhysWidget />
        </div>
      </header>

      {/* 2. MAIN SCROLLABLE CONTAINER */}
      <main className="max-w-7xl w-full mx-auto px-6 sm:px-10 pb-20 space-y-10 flex-1">
        {/* HERO CARD: "Prompt to Video" */}
        <section
          id="apps-hero-card"
          data-testid="apps-hero-card"
          aria-label="Featured Creation Engine: Prompt to Video"
          className={`relative rounded-3xl p-8 sm:p-10 overflow-hidden border transition-all ${
            isLight
              ? "bg-gradient-to-r from-blue-50 via-indigo-50/80 to-purple-50 text-slate-900 border-indigo-100 shadow-md"
              : "bg-gradient-to-r from-[#0B111E] via-[#101827] to-[#0B111E] text-white border-[#1B2940] shadow-xl"
          }`}
        >
          <div className="relative z-10 max-w-xl flex flex-col justify-between">
            <div>
              <div
                className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-bold mb-4 ${
                  isLight
                    ? "bg-blue-100 border border-blue-200 text-blue-700"
                    : "bg-cyan-500/15 border border-cyan-500/30 text-cyan-400"
                }`}
              >
                <Sparkles size={13} />
                <span>Featured Creation Engine</span>
              </div>

              <h2
                className={`text-3xl sm:text-4xl font-black tracking-tight leading-tight ${
                  isLight ? "text-slate-900" : "text-white"
                }`}
              >
                Prompt to Video
              </h2>

              <p
                className={`text-xs sm:text-sm mt-3 leading-relaxed font-normal ${
                  isLight ? "text-slate-600" : "text-slate-300"
                }`}
              >
                From idea to finished video with just a prompt. Type your idea.
                Click generate. Get a share-ready video faster than you can
                think.
              </p>
            </div>

            <div className="mt-8">
              <button
                type="button"
                id="try-video-agent-hero-btn"
                data-testid="try-video-agent-hero-btn"
                onClick={() => {
                  if (onNavigateVideoAgent) onNavigateVideoAgent();
                  else if (onOpenStudio) onOpenStudio();
                }}
                className="bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-cyan-500 hover:to-blue-600 text-white font-bold px-6 py-2.5 rounded-full text-xs shadow-lg shadow-purple-900/30 hover:shadow-cyan-500/25 transition-all duration-200 flex items-center gap-2 group cursor-pointer hover:scale-105 active:scale-95"
              >
                <span>Try Video Agent</span>
                <ArrowRight
                  size={14}
                  className="group-hover:translate-x-0.5 transition-transform duration-200"
                />
              </button>
            </div>
          </div>

          {/* Right Visual Composition (Pure CSS & SVG, No Stock Images) */}
          <div className="absolute right-0 top-0 bottom-0 w-1/2 hidden md:flex items-center justify-end pr-8 pointer-events-none select-none">
            <div className="relative w-84 h-56">
              {/* Back Card */}
              <div
                className={`absolute right-12 top-2 w-52 h-36 rounded-2xl p-4 shadow-2xl border transform rotate-6 opacity-60 flex flex-col justify-between ${
                  isLight
                    ? "border-slate-200 bg-gradient-to-br from-indigo-100 to-blue-50"
                    : "border-[#1B2940] bg-gradient-to-br from-[#0e172a] to-[#121d33]"
                }`}
              >
                <div className="flex items-center gap-2">
                  <div className="w-6 h-6 rounded-lg bg-indigo-500/20 flex items-center justify-center text-indigo-400">
                    <Sparkles size={13} />
                  </div>
                  <span className="text-[11px] font-bold">Script Generation</span>
                </div>
                <div className="space-y-1.5 opacity-50">
                  <div className="h-2 w-3/4 rounded bg-indigo-300 dark:bg-indigo-700/50" />
                  <div className="h-2 w-1/2 rounded bg-indigo-300 dark:bg-indigo-700/50" />
                </div>
              </div>

              {/* Middle Card */}
              <div
                className={`absolute right-6 top-8 w-56 h-40 rounded-2xl p-4 shadow-2xl border transform -rotate-3 opacity-85 flex flex-col justify-between ${
                  isLight
                    ? "border-slate-200 bg-gradient-to-br from-purple-100 to-indigo-50"
                    : "border-[#1B2940] bg-gradient-to-br from-[#131b2e] to-[#0c1322]"
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-6 h-6 rounded-lg bg-purple-500/20 flex items-center justify-center text-purple-400">
                      <Layers size={13} />
                    </div>
                    <span className="text-[11px] font-bold">Multi-Scene Timeline</span>
                  </div>
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-300 font-bold">
                    3 Scenes
                  </span>
                </div>
                <div className="flex gap-2 items-center">
                  <div className="w-10 h-10 rounded-xl bg-purple-500/20 flex items-center justify-center text-purple-400 text-xs font-bold">
                    01
                  </div>
                  <div className="w-10 h-10 rounded-xl bg-indigo-500/20 flex items-center justify-center text-indigo-400 text-xs font-bold">
                    02
                  </div>
                  <div className="w-10 h-10 rounded-xl bg-cyan-500/20 flex items-center justify-center text-cyan-400 text-xs font-bold">
                    03
                  </div>
                </div>
              </div>

              {/* Front Card */}
              <div
                className={`absolute right-0 top-14 w-60 h-44 rounded-2xl p-4 shadow-2xl border-2 transform rotate-2 flex flex-col justify-between ${
                  isLight
                    ? "border-blue-500 bg-white"
                    : "border-cyan-500/80 bg-[#0B111E]"
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-7 h-7 rounded-xl bg-gradient-to-tr from-cyan-400 to-blue-600 flex items-center justify-center text-white shadow-xs">
                      <Sparkles size={14} />
                    </div>
                    <div>
                      <span className="text-xs font-black block">AI Video Agent</span>
                      <span className="text-[10px] text-cyan-400 font-bold">Ready to Export</span>
                    </div>
                  </div>
                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
                </div>

                <div
                  className={`rounded-xl p-2.5 flex items-center justify-between border ${
                    isLight
                      ? "bg-slate-100 border-slate-200 text-slate-800"
                      : "bg-[#07090e]/80 border-white/10 text-white"
                  }`}
                >
                  <span className="text-[11px] font-bold">✨ 4K Script Synced</span>
                  <div className="w-5 h-5 rounded-full bg-cyan-400 text-slate-950 flex items-center justify-center shadow-xs">
                    <Play size={10} className="fill-current ml-0.5" />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* 3. CATEGORY SELECTOR PILLS & SEARCH */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pt-1">
          {/* Category Tabs */}
          <div
            id="apps-category-tabs"
            data-testid="apps-category-tabs"
            role="tablist"
            aria-label="Filter apps by category"
            className={`p-1 rounded-full inline-flex items-center gap-1 border shadow-xs ${
              isLight ? "bg-slate-100 border-slate-200" : "bg-[#0B1220] border-[#1B2940]"
            }`}
          >
            {[
              { id: "all", label: "All Apps" },
              { id: "create", label: "Create" },
              { id: "enhance", label: "Enhance" },
              { id: "edit", label: "Edit" },
              { id: "interactive", label: "Interactive" },
            ].map((tab) => {
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  type="button"
                  id={`apps-tab-${tab.id}`}
                  data-testid={`apps-tab-${tab.id}`}
                  role="tab"
                  aria-selected={isActive}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`px-4 py-1.5 rounded-full text-xs transition-all cursor-pointer ${
                    isActive
                      ? isLight
                        ? "bg-white text-blue-600 font-bold shadow-xs border border-blue-200"
                        : "bg-[#101827] text-white font-bold shadow-xs border border-cyan-500/40"
                      : isLight
                      ? "text-slate-600 hover:text-slate-900 hover:bg-white/60 font-medium"
                      : "text-slate-400 hover:text-white font-medium hover:bg-[#101827]/50"
                  }`}
                >
                  {tab.label}
                </button>
              );
            })}
          </div>

          {/* Search Apps Input with Clear Button */}
          <div className="relative w-full sm:w-72">
            <Search
              size={14}
              className="absolute left-3.5 top-2.5 text-slate-500 pointer-events-none"
            />
            <input
              type="text"
              id="apps-search-input"
              data-testid="apps-search-input"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search Apps (name, category, keywords)..."
              className={`w-full rounded-full pl-9 pr-8 py-1.5 text-xs shadow-xs focus:outline-none transition-all ${
                isLight
                  ? "bg-white border border-slate-200 text-slate-900 placeholder:text-slate-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
                  : "bg-[#0A0F1A] border border-[#1B2940] text-white placeholder:text-slate-500 focus:border-cyan-500 focus:ring-2 focus:ring-cyan-500/20"
              }`}
            />
            {searchQuery && (
              <button
                type="button"
                id="apps-clear-search-btn"
                data-testid="apps-clear-search-btn"
                onClick={handleClearSearch}
                aria-label="Clear search"
                className="absolute right-2.5 top-2 text-slate-400 hover:text-slate-200 cursor-pointer p-0.5 rounded-full"
              >
                <X size={14} />
              </button>
            )}
          </div>
        </div>

        {/* 4. FEATURED 3-APP HORIZONTAL CARDS (Visible when not actively searching) */}
        {!searchQuery.trim() &&
          (activeTab === "all" || activeTab === "create" || activeTab === "edit") && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
              {/* Card 1: Translate Videos */}
              <div
                id="featured-app-translate"
                data-testid="featured-app-translate"
                tabIndex={0}
                role="button"
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    if (onNavigateTranslate) onNavigateTranslate();
                  }
                }}
                onClick={() => {
                  if (onNavigateTranslate) onNavigateTranslate();
                }}
                className={`group relative h-48 rounded-3xl overflow-hidden transition-all duration-300 cursor-pointer border ${
                  isLight
                    ? "border-slate-200 bg-gradient-to-br from-blue-600 via-cyan-600 to-teal-500 shadow-sm hover:shadow-xl hover:border-blue-400"
                    : "border-[#1B2940] hover:border-cyan-500/50 bg-gradient-to-br from-blue-900/80 via-cyan-950 to-[#0B111E] shadow-lg hover:shadow-2xl hover:shadow-cyan-500/10"
                }`}
              >
                {/* Background Artwork */}
                <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/40 to-transparent p-6 flex flex-col justify-between">
                  <div className="flex items-center justify-between">
                    <div className="w-10 h-10 rounded-2xl bg-white/10 backdrop-blur-md border border-white/20 flex items-center justify-center text-white shadow-sm">
                      <Languages size={20} />
                    </div>
                    <span className="text-[10px] uppercase font-bold tracking-wider px-2.5 py-0.5 rounded-full bg-cyan-400/20 text-cyan-300 border border-cyan-400/30">
                      175+ Languages
                    </span>
                  </div>

                  <div>
                    <h3 className="text-xl font-black tracking-tight text-white group-hover:text-cyan-200 transition-colors drop-shadow-sm">
                      Translate Videos
                    </h3>
                    <p className="text-xs text-slate-200/90 line-clamp-1 mt-0.5">
                      Convert any video into 175+ languages with lip-sync
                    </p>
                    <div className="mt-3">
                      <span className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-xs font-bold border backdrop-blur-md bg-white/15 hover:bg-cyan-500 hover:text-slate-950 text-white border-white/20 transition-all">
                        <span>Try Translate Videos</span>
                        <ArrowRight size={13} />
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Card 2: PPT/PDF to Video */}
              <div
                id="featured-app-pdf"
                data-testid="featured-app-pdf"
                tabIndex={0}
                role="button"
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    setActiveFeaturedModal("pdf");
                  }
                }}
                onClick={() => {
                  setActiveFeaturedModal("pdf");
                }}
                className={`group relative h-48 rounded-3xl overflow-hidden transition-all duration-300 cursor-pointer border ${
                  isLight
                    ? "border-slate-200 bg-gradient-to-br from-rose-500 via-pink-600 to-purple-600 shadow-sm hover:shadow-xl hover:border-pink-400"
                    : "border-[#1B2940] hover:border-pink-500/50 bg-gradient-to-br from-rose-950 via-purple-950 to-[#0B111E] shadow-lg hover:shadow-2xl hover:shadow-pink-500/10"
                }`}
              >
                <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/40 to-transparent p-6 flex flex-col justify-between">
                  <div className="flex items-center justify-between">
                    <div className="w-10 h-10 rounded-2xl bg-white/10 backdrop-blur-md border border-white/20 flex items-center justify-center text-white shadow-sm">
                      <FileText size={20} />
                    </div>
                    <span className="text-[10px] uppercase font-bold tracking-wider px-2.5 py-0.5 rounded-full bg-rose-400/20 text-rose-300 border border-rose-400/30">
                      Slides to Video
                    </span>
                  </div>

                  <div>
                    <h3 className="text-xl font-black tracking-tight text-white group-hover:text-rose-200 transition-colors drop-shadow-sm">
                      PPT/PDF to Video
                    </h3>
                    <p className="text-xs text-slate-200/90 line-clamp-1 mt-0.5">
                      Transform documents into engaging avatar videos
                    </p>
                    <div className="mt-3">
                      <span className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-xs font-bold border backdrop-blur-md bg-white/15 hover:bg-rose-500 hover:text-slate-950 text-white border-white/20 transition-all">
                        <span>Try PPT/PDF to Video</span>
                        <ArrowRight size={13} />
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Card 3: Cinematic Shots */}
              <div
                id="featured-app-shots"
                data-testid="featured-app-shots"
                tabIndex={0}
                role="button"
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    setActiveFeaturedModal("shots");
                  }
                }}
                onClick={() => {
                  setActiveFeaturedModal("shots");
                }}
                className={`group relative h-48 rounded-3xl overflow-hidden transition-all duration-300 cursor-pointer border ${
                  isLight
                    ? "border-slate-200 bg-gradient-to-br from-violet-600 via-purple-600 to-indigo-700 shadow-sm hover:shadow-xl hover:border-purple-400"
                    : "border-[#1B2940] hover:border-purple-500/50 bg-gradient-to-br from-purple-950 via-indigo-950 to-[#0B111E] shadow-lg hover:shadow-2xl hover:shadow-purple-500/10"
                }`}
              >
                <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/40 to-transparent p-6 flex flex-col justify-between">
                  <div className="flex items-center justify-between">
                    <div className="w-10 h-10 rounded-2xl bg-white/10 backdrop-blur-md border border-white/20 flex items-center justify-center text-white shadow-sm">
                      <Camera size={20} />
                    </div>
                    <span className="text-[10px] uppercase font-bold tracking-wider px-2.5 py-0.5 rounded-full bg-violet-400/20 text-violet-300 border border-violet-400/30">
                      Cinematic
                    </span>
                  </div>

                  <div>
                    <h3 className="text-xl font-black tracking-tight text-white group-hover:text-purple-200 transition-colors drop-shadow-sm">
                      Cinematic Shots
                    </h3>
                    <p className="text-xs text-slate-200/90 line-clamp-1 mt-0.5">
                      AI-powered cinematic, film-quality camera angles
                    </p>
                    <div className="mt-3">
                      <span className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-xs font-bold border backdrop-blur-md bg-white/15 hover:bg-violet-500 hover:text-slate-950 text-white border-white/20 transition-all">
                        <span>Try Cinematic Shots</span>
                        <ArrowRight size={13} />
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

        {/* 5. SEARCH EMPTY STATE */}
        {filteredApps.length === 0 ? (
          <div
            id="apps-search-empty-state"
            data-testid="apps-search-empty-state"
            className="text-center py-20 px-4 flex flex-col items-center justify-center animate-in fade-in duration-200"
          >
            <div
              className={`w-14 h-14 rounded-2xl flex items-center justify-center mb-4 ${
                isLight ? "bg-slate-100 text-slate-400" : "bg-[#101827] text-slate-500"
              }`}
            >
              <Search size={26} />
            </div>
            <h3
              className={`text-base font-bold mb-1 ${
                isLight ? "text-slate-800" : "text-white"
              }`}
            >
              No apps found
            </h3>
            <p
              className={`text-xs max-w-sm mb-5 ${
                isLight ? "text-slate-500" : "text-slate-400"
              }`}
            >
              No apps matched &ldquo;{searchQuery}&rdquo;. Try another search term or
              select a different category.
            </p>
            <button
              type="button"
              id="apps-empty-clear-btn"
              data-testid="apps-empty-clear-btn"
              onClick={handleClearSearch}
              className="px-4 py-2 rounded-xl text-xs font-bold bg-blue-600 hover:bg-blue-500 text-white shadow-sm cursor-pointer transition-all"
            >
              Clear search
            </button>
          </div>
        ) : (
          /* 6. APPS GRID (Categorized sections or direct search results) */
          <div className="space-y-12" id="apps-grid" data-testid="apps-grid">
            {/* When searching or on a single category, show unified grid */}
            {searchQuery.trim() || activeTab !== "all" ? (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h2
                    className={`text-lg font-bold ${
                      isLight ? "text-slate-900" : "text-white"
                    }`}
                  >
                    {searchQuery.trim()
                      ? `Search Results (${filteredApps.length})`
                      : activeTab === "create"
                      ? "Create Apps"
                      : activeTab === "enhance"
                      ? "Enhance Apps"
                      : activeTab === "edit"
                      ? "Edit Apps"
                      : "Interactive Apps"}
                  </h2>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-5">
                  {filteredApps.map((app) => (
                    <AppCard
                      key={app.id}
                      app={app}
                      isLight={isLight}
                      onClick={() => handleLaunchApp(app)}
                    />
                  ))}
                </div>
              </div>
            ) : (
              /* When on "All Apps" without search, show curated sections */
              <>
                {/* SECTION 1: CREATE */}
                {createApps.length > 0 && (
                  <div className="space-y-5">
                    <div className="text-center pt-2">
                      <h2
                        className={`text-2xl sm:text-3xl font-black tracking-tight ${
                          isLight ? "text-slate-900" : "text-white"
                        }`}
                      >
                        Apps to{" "}
                        <span className={isLight ? "text-blue-600" : "text-cyan-400"}>
                          create
                        </span>{" "}
                        avatars,
                        <br />
                        videos, images and more.
                      </h2>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-5">
                      {createApps.map((app) => (
                        <AppCard
                          key={app.id}
                          app={app}
                          isLight={isLight}
                          onClick={() => handleLaunchApp(app)}
                        />
                      ))}
                    </div>
                  </div>
                )}

                {/* SECTION 2: ENHANCE */}
                {enhanceApps.length > 0 && (
                  <div className="space-y-5 pt-4">
                    <div className="text-center">
                      <h2
                        className={`text-2xl sm:text-3xl font-black tracking-tight ${
                          isLight ? "text-slate-900" : "text-white"
                        }`}
                      >
                        Apps to{" "}
                        <span className={isLight ? "text-emerald-600" : "text-emerald-400"}>
                          enhance
                        </span>
                        <br />
                        all that you create.
                      </h2>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-5">
                      {enhanceApps.map((app) => (
                        <AppCard
                          key={app.id}
                          app={app}
                          isLight={isLight}
                          onClick={() => handleLaunchApp(app)}
                        />
                      ))}
                    </div>
                  </div>
                )}

                {/* SECTION 3: EDIT */}
                {editApps.length > 0 && (
                  <div className="space-y-5 pt-4">
                    <div className="text-center">
                      <h2
                        className={`text-2xl sm:text-3xl font-black tracking-tight ${
                          isLight ? "text-slate-900" : "text-white"
                        }`}
                      >
                        Apps to{" "}
                        <span className={isLight ? "text-purple-600" : "text-purple-400"}>
                          edit
                        </span>
                        , change,
                        <br />
                        and remix your content
                      </h2>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-5">
                      {editApps.map((app) => (
                        <AppCard
                          key={app.id}
                          app={app}
                          isLight={isLight}
                          onClick={() => handleLaunchApp(app)}
                        />
                      ))}
                    </div>
                  </div>
                )}

                {/* SECTION 4: INTERACTIVE */}
                {interactiveApps.length > 0 && (
                  <div className="space-y-5 pt-4">
                    <div className="text-center">
                      <h2
                        className={`text-2xl sm:text-3xl font-black tracking-tight ${
                          isLight ? "text-slate-900" : "text-white"
                        }`}
                      >
                        Apps for{" "}
                        <span className={isLight ? "text-cyan-600" : "text-cyan-400"}>
                          interactive
                        </span>
                        <br />
                        and branching experiences
                      </h2>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-5">
                      {interactiveApps.map((app) => (
                        <AppCard
                          key={app.id}
                          app={app}
                          isLight={isLight}
                          onClick={() => handleLaunchApp(app)}
                        />
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </main>

      {/* FEATURED APPS DEDICATED STUDIOS & MODALS */}
      <FeaturedAppModals
        activeModal={activeFeaturedModal}
        onClose={() => setActiveFeaturedModal(null)}
        onOpenStudio={onOpenStudio}
        onLaunchVideoAgentWithContext={onLaunchVideoAgentWithContext}
      />

      {/* APP DETAIL / LAUNCH INSPECTOR MODAL */}
      {selectedApp && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="app-modal-title"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4 animate-in fade-in duration-200 select-none"
        >
          <div
            className={`w-full max-w-lg rounded-3xl p-6 shadow-2xl border ${
              isLight
                ? "bg-white text-slate-800 border-slate-200"
                : "bg-[#0A0F1A] text-slate-100 border-[#1B2940]"
            }`}
          >
            <div
              className={`flex items-center justify-between pb-3 border-b mb-4 ${
                isLight ? "border-slate-100" : "border-[#1B2940]"
              }`}
            >
              <div className="flex items-center gap-3">
                <div
                  className={`w-12 h-12 rounded-2xl flex items-center justify-center shadow-md bg-gradient-to-tr ${selectedApp.gradient}`}
                >
                  {renderAppIcon(selectedApp.iconName, "w-6 h-6 text-white")}
                </div>
                <div>
                  <h3
                    id="app-modal-title"
                    className={`text-base font-bold ${
                      isLight ? "text-slate-900" : "text-white"
                    }`}
                  >
                    {selectedApp.modalTitle}
                  </h3>
                  <span
                    className={`text-[10px] uppercase font-bold tracking-wider ${
                      isLight ? "text-blue-600" : "text-cyan-400"
                    }`}
                  >
                    {selectedApp.category} Engine
                  </span>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setSelectedApp(null)}
                aria-label="Close modal"
                className={`w-8 h-8 rounded-full flex items-center justify-center cursor-pointer ${
                  isLight
                    ? "text-slate-400 hover:text-slate-700 hover:bg-slate-100"
                    : "text-slate-400 hover:text-white hover:bg-[#101827]"
                }`}
              >
                <X size={18} />
              </button>
            </div>

            <p
              className={`text-xs leading-relaxed mb-6 ${
                isLight ? "text-slate-600" : "text-slate-300"
              }`}
            >
              {selectedApp.modalDescription}
            </p>

            <div
              className={`flex justify-end gap-2.5 pt-3 border-t ${
                isLight ? "border-slate-100" : "border-[#1B2940]"
              }`}
            >
              <button
                type="button"
                onClick={() => setSelectedApp(null)}
                className={`px-4 py-2 rounded-xl text-xs font-semibold cursor-pointer ${
                  isLight
                    ? "text-slate-500 hover:text-slate-800 hover:bg-slate-100"
                    : "text-slate-400 hover:text-white hover:bg-[#101827]"
                }`}
              >
                Close
              </button>
              <button
                type="button"
                onClick={() => {
                  setSelectedApp(null);
                  if (onOpenStudio) onOpenStudio();
                }}
                className="px-5 py-2 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-cyan-500 hover:to-blue-600 text-white text-xs font-bold rounded-full shadow-md cursor-pointer flex items-center gap-1.5 transition-all"
              >
                <span>{selectedApp.modalCta || "Launch in Studio"}</span>
                <ArrowRight size={14} />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Sub-component for individual App Card
function AppCard({
  app,
  isLight,
  onClick,
}: {
  app: AppDefinition;
  isLight: boolean;
  onClick: () => void;
}) {
  return (
    <div
      id={`app-card-${app.id}`}
      data-testid={`app-card-${app.id}`}
      tabIndex={0}
      role="button"
      aria-label={`${app.name}: ${app.description}`}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onClick();
        }
      }}
      onClick={onClick}
      className={`group rounded-2xl border overflow-hidden transition-all duration-300 cursor-pointer flex flex-col justify-between select-none focus:outline-none focus:ring-2 focus:ring-cyan-500/50 ${
        isLight
          ? "bg-white hover:bg-slate-50/90 border-slate-200 hover:border-blue-400 shadow-xs hover:shadow-xl"
          : "bg-[#0B111E] hover:bg-[#101827] border-[#1B2940] hover:border-cyan-500/50 shadow-md hover:shadow-2xl hover:shadow-cyan-500/10"
      }`}
    >
      {/* Top Visual Area (Curated Gradient Art, No Stock Images) */}
      <div className={`h-36 w-full relative overflow-hidden bg-gradient-to-tr ${app.gradient} flex items-center justify-center p-4`}>
        {/* Subtle geometric pattern overlay */}
        <div className="absolute inset-0 bg-black/15 backdrop-blur-[1px]" />

        {/* Decorative central emblem */}
        <div className="relative z-10 w-14 h-14 rounded-2xl bg-white/15 backdrop-blur-md border border-white/25 flex items-center justify-center shadow-lg group-hover:scale-110 transition-transform duration-300">
          {renderAppIcon(app.iconName, "w-7 h-7 text-white")}
        </div>

        {/* Badge */}
        {app.badge && (
          <div className="absolute top-2.5 right-2.5 z-10">
            <span className="text-[10px] font-extrabold uppercase px-2 py-0.5 rounded-full bg-black/40 backdrop-blur-md text-white border border-white/20">
              {app.badge}
            </span>
          </div>
        )}

        {/* Gradient fade into card body */}
        <div
          className={`absolute inset-x-0 bottom-0 h-6 ${
            isLight
              ? "bg-gradient-to-t from-white to-transparent"
              : "bg-gradient-to-t from-[#0B111E] to-transparent"
          }`}
        />
      </div>

      {/* Bottom Content Area */}
      <div
        className={`p-4 flex items-center justify-between gap-3 transition-colors ${
          isLight
            ? "bg-white group-hover:bg-slate-50/90"
            : "bg-[#0B111E] group-hover:bg-[#101827]"
        }`}
      >
        <div className="min-w-0 flex-1">
          <h3
            className={`text-sm font-bold truncate transition-colors ${
              isLight
                ? "text-slate-900 group-hover:text-blue-600"
                : "text-white group-hover:text-cyan-200"
            }`}
          >
            {app.name}
          </h3>
          <p
            className={`text-[11px] line-clamp-1 mt-0.5 font-normal ${
              isLight ? "text-slate-500" : "text-slate-400"
            }`}
          >
            {app.description}
          </p>
        </div>
        <div
          className={`w-8 h-8 rounded-full border flex items-center justify-center shrink-0 transition-all ${
            isLight
              ? "bg-slate-100 border-slate-200 group-hover:bg-blue-600 group-hover:text-white text-slate-700 shadow-xs"
              : "bg-[#101827] border-[#1B2940] group-hover:border-cyan-500/50 group-hover:bg-cyan-500 text-slate-300 group-hover:text-slate-950 shadow-md"
          }`}
        >
          <ArrowRight
            size={14}
            className="transform group-hover:translate-x-0.5 transition-transform"
          />
        </div>
      </div>
    </div>
  );
}
