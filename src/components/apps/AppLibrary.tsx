"use client";

import React, { useState } from "react";
import {
  Mic,
  Video,
  Sparkles,
  Languages,
  Film,
  FileText,
  PlaySquare,
  Scissors,
  TrendingUp,
  ShoppingBag,
  UserCheck,
  RefreshCw,
  Image as ImageIcon,
  Volume2,
  MousePointerClick,
  MessageSquare,
  Search,
  ArrowRight,
  X,
  Play,
} from "lucide-react";
import AskRhysWidget from "../dashboard/AskRhysWidget";
import FeaturedAppModals from "./FeaturedAppModals";
import { useTheme } from "@/context/ThemeContext";

export interface AppCardData {
  id: string;
  name: string;
  description: string;
  category: "create" | "enhance" | "edit" | "interactive";
  image: string;
  modalTitle: string;
  modalDescription: string;
  featuredAction?: "generator" | "podcast" | "speech" | "studio" | "video_agent" | "translate";
}

const CREATE_APPS: AppCardData[] = [
  {
    id: "app_generator",
    name: "AI Video Generator",
    description: "Create AI-generated video clips from text prompts",
    category: "create",
    image: "https://images.unsplash.com/photo-1503899036084-c55cdd92da26?q=80&w=600&auto=format&fit=crop",
    modalTitle: "Generative Video Engine",
    modalDescription: "Turn text prompts into high-motion B-roll backgrounds, dynamic cinematic cuts, and photorealistic environments.",
    featuredAction: "generator",
  },
  {
    id: "app_agent",
    name: "Video Agent",
    description: "Describe your video and let an AI agent create it",
    category: "create",
    image: "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?q=80&w=600&auto=format&fit=crop",
    modalTitle: "AI Video Agent Copilot",
    modalDescription: "Give a one-sentence prompt and the AI agent writes the script, selects avatars, generates scenes, and edits the video.",
    featuredAction: "video_agent",
  },
  {
    id: "app_podcast",
    name: "Video Podcast",
    description: "Generate a podcast video with multiple speakers",
    category: "create",
    image: "https://images.unsplash.com/photo-1590602847861-f357a9332bbc?q=80&w=600&auto=format&fit=crop",
    modalTitle: "AI Video Podcast Studio",
    modalDescription: "Generate multi-speaker video podcasts with automatic speaker switching, camera cuts, and mic waveforms.",
    featuredAction: "podcast",
  },
  {
    id: "app_product",
    name: "Product Placement",
    description: "Create a video ad showcasing your products",
    category: "create",
    image: "https://images.unsplash.com/photo-1523275335684-37898b6baf30?q=80&w=600&auto=format&fit=crop",
    modalTitle: "E-Commerce Product Placement",
    modalDescription: "Place your physical 3D product or software mockup directly into the avatar's hands with realistic physics and lighting.",
  },
  {
    id: "app_pdf",
    name: "PPT/PDF to Video",
    description: "Transform documents into engaging avatar videos",
    category: "create",
    image: "https://images.unsplash.com/photo-1551836022-d5d88e9218df?q=80&w=600&auto=format&fit=crop",
    modalTitle: "Document to Video Converter",
    modalDescription: "Upload any PowerPoint slide deck or PDF report. AI turns each page into an interactive video scene presented by your chosen avatar.",
  },
  {
    id: "app_shots",
    name: "Avatar Shots",
    description: "AI-powered cinematic, film-quality camera angles",
    category: "create",
    image: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?q=80&w=600&auto=format&fit=crop",
    modalTitle: "Cinematic Avatar Shots",
    modalDescription: "Generate Hollywood-grade closeups, over-the-shoulder angles, and walking shots for high-production value commercials.",
  },
  {
    id: "app_studio",
    name: "AI Studio",
    description: "Create and produce professional avatar videos",
    category: "create",
    image: "https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?q=80&w=600&auto=format&fit=crop",
    modalTitle: "VidoAI Studio Editor",
    modalDescription: "Full multi-scene video timeline with custom canvas layouts, script synchronization, and 4K exports.",
    featuredAction: "studio",
  },
  {
    id: "app_images",
    name: "Generate Images",
    description: "Create AI-generated images for your videos",
    category: "create",
    image: "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?q=80&w=600&auto=format&fit=crop",
    modalTitle: "AI Media Generator",
    modalDescription: "Synthesize bespoke photographic backgrounds, illustration graphics, and brand assets directly inside the video studio.",
  },
];

const ENHANCE_APPS: AppCardData[] = [
  {
    id: "app_upscale",
    name: "Upscale Video",
    description: "Create high resolution 4K outputs from existing video",
    category: "enhance",
    image: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?q=80&w=600&auto=format&fit=crop",
    modalTitle: "AI 4K Video Upscaler",
    modalDescription: "Restore low-res videos to crystal clear 4K resolution with neural artifact removal and facial detail enhancement.",
  },
  {
    id: "app_speech",
    name: "Speech Cleanup",
    description: "Remove unwanted pauses, filler words, and background noise",
    category: "enhance",
    image: "https://images.unsplash.com/photo-1598488035139-bdbb2231ce04?q=80&w=600&auto=format&fit=crop",
    modalTitle: "Studio Audio Cleanup Engine",
    modalDescription: "One-click noise removal: eliminate room reverberation, breathing noises, 'ums', and 'uhs' to achieve broadcast studio clarity.",
    featuredAction: "speech",
  },
  {
    id: "app_interactive",
    name: "Interactive Video",
    description: "Create branching, clickable interactive video funnels",
    category: "interactive",
    image: "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?q=80&w=600&auto=format&fit=crop",
    modalTitle: "Branching Interactive Funnels",
    modalDescription: "Add interactive buttons, clickable cards, quiz questions, and Calendly embeds directly onto playing video timelines.",
  },
  {
    id: "app_agent_enhance",
    name: "Video Agent",
    description: "Automate script enhancements and scene timing",
    category: "enhance",
    image: "https://images.unsplash.com/photo-1573497019940-1c28c88b4f3e?q=80&w=600&auto=format&fit=crop",
    modalTitle: "AI Video Agent Copilot",
    modalDescription: "AI agent automatically refines pacing, enhances avatar body gestures, and syncs caption animations.",
    featuredAction: "video_agent",
  },
];

const EDIT_APPS: AppCardData[] = [
  {
    id: "app_clipping",
    name: "AI Clipping",
    description: "Upload a longer video and AI will create viral short clips",
    category: "edit",
    image: "https://images.unsplash.com/photo-1531482615713-2afd69097998?q=80&w=600&auto=format&fit=crop",
    modalTitle: "Viral Shorts & Reels Clipper",
    modalDescription: "Upload long webinars, interviews, or YouTube videos. AI finds the most viral moments, crops to 9:16 vertical, and adds animated captions.",
  },
  {
    id: "app_faceswap",
    name: "Face Swap",
    description: "Make any avatar your own by swapping your face onto video",
    category: "edit",
    image: "https://images.unsplash.com/photo-1580489944761-15a19d654956?q=80&w=600&auto=format&fit=crop",
    modalTitle: "Avatar Face Swap Studio",
    modalDescription: "Upload a single front-facing photo to swap facial features onto any body, wardrobe, or custom environment.",
  },
  {
    id: "app_translate",
    name: "Translate Videos",
    description: "Convert any video into 175+ languages with lip-sync",
    category: "edit",
    image: "https://images.unsplash.com/photo-1522202176988-66273c2fd55f?q=80&w=600&auto=format&fit=crop",
    modalTitle: "AI Video Translation & Lip-Sync",
    modalDescription: "Translate video audio into 175+ languages while preserving the original speaker's authentic voice timbre and adjusting lip movements.",
    featuredAction: "translate",
  },
  {
    id: "app_batch",
    name: "Batch Mode",
    description: "Create multiple avatar videos at once from spreadsheet data",
    category: "edit",
    image: "https://images.unsplash.com/photo-1522202176988-66273c2fd55f?q=80&w=600&auto=format&fit=crop",
    modalTitle: "Personalized Batch Generator",
    modalDescription: "Connect CSV spreadsheet variables (Customer Name, Company, City) to generate 1,000s of personalized outreach videos in minutes.",
  },
];

interface AppLibraryProps {
  onOpenStudio?: () => void;
  onNavigateVideoAgent?: () => void;
  onNavigateTranslate?: () => void;
}

export default function AppLibrary({
  onOpenStudio,
  onNavigateVideoAgent,
  onNavigateTranslate,
}: AppLibraryProps) {
  const { theme } = useTheme();
  const isLight = theme === "light";
  const [activeTab, setActiveTab] = useState<
    "all" | "create" | "enhance" | "edit" | "interactive"
  >("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedApp, setSelectedApp] = useState<AppCardData | null>(null);
  const [activeFeaturedModal, setActiveFeaturedModal] = useState<
    "generator" | "podcast" | "speech" | null
  >(null);

  const handleAppClick = (app: AppCardData) => {
    if (app.featuredAction === "generator") {
      setActiveFeaturedModal("generator");
    } else if (app.featuredAction === "podcast") {
      setActiveFeaturedModal("podcast");
    } else if (app.featuredAction === "speech") {
      setActiveFeaturedModal("speech");
    } else if (app.featuredAction === "studio" && onOpenStudio) {
      onOpenStudio();
    } else if (app.featuredAction === "video_agent" && onNavigateVideoAgent) {
      onNavigateVideoAgent();
    } else if (app.featuredAction === "translate" && onNavigateTranslate) {
      onNavigateTranslate();
    } else {
      setSelectedApp(app);
    }
  };

  const filterBySearch = (list: AppCardData[]) => {
    if (!searchQuery.trim()) return list;
    const q = searchQuery.toLowerCase();
    return list.filter(
      (app) =>
        app.name.toLowerCase().includes(q) ||
        app.description.toLowerCase().includes(q)
    );
  };

  const filteredCreate = filterBySearch(CREATE_APPS);
  const filteredEnhance = filterBySearch(ENHANCE_APPS);
  const filteredEdit = filterBySearch(EDIT_APPS);

  return (
    <div
      className={`flex-1 h-screen overflow-y-auto flex flex-col font-sans select-none relative scrollbar-thin ${
        isLight
          ? "bg-slate-50 text-slate-800 scrollbar-thumb-slate-300"
          : "bg-[#07090e] text-slate-100 scrollbar-thumb-slate-800"
      }`}
    >
      {/* 1. TOP HEADER */}
      <header
        className={`w-full max-w-7xl mx-auto px-6 sm:px-10 pt-8 pb-5 flex items-center justify-between border-b z-20 ${
          isLight ? "border-slate-200" : "border-[#1B2940]/40"
        }`}
      >
        <div>
          <h1
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
      <main className="max-w-7xl w-full mx-auto px-6 sm:px-10 pb-20 space-y-12 flex-1">
        {/* HERO CARD: "Prompt to Video" */}
        <div
          className={`relative rounded-3xl p-8 sm:p-10 overflow-hidden border transition-all ${
            isLight
              ? "bg-gradient-to-r from-blue-50 via-indigo-50/70 to-purple-50 text-slate-900 border-indigo-100 shadow-md"
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
                onClick={() => {
                  if (onNavigateVideoAgent) onNavigateVideoAgent();
                  else if (onOpenStudio) onOpenStudio();
                }}
                className="bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-cyan-500 hover:to-blue-600 text-white hover:text-slate-950 font-bold px-6 py-2.5 rounded-full text-xs shadow-lg shadow-purple-900/40 hover:shadow-cyan-500/25 transition-all duration-200 flex items-center gap-2 group cursor-pointer hover:scale-105 active:scale-95"
              >
                <span>Try Video Agent</span>
                <ArrowRight
                  size={14}
                  className="group-hover:translate-x-0.5 transition-transform duration-200"
                />
              </button>
            </div>
          </div>

          {/* Right Visual Collage */}
          <div className="absolute right-0 top-0 bottom-0 w-1/2 hidden md:flex items-center justify-end pr-8 pointer-events-none">
            <div className="relative w-80 h-52">
              {/* Back Card */}
              <div
                className={`absolute right-12 top-2 w-48 h-32 rounded-2xl overflow-hidden shadow-2xl border transform rotate-6 opacity-60 ${
                  isLight ? "border-slate-200 bg-white" : "border-[#1B2940] bg-[#0B111E]"
                }`}
              >
                <img
                  src="https://images.unsplash.com/photo-1534528741775-53994a69daeb?q=80&w=400&auto=format&fit=crop"
                  alt="Avatar Collage 1"
                  className="w-full h-full object-cover brightness-90"
                />
              </div>
              {/* Middle Card */}
              <div
                className={`absolute right-6 top-8 w-52 h-36 rounded-2xl overflow-hidden shadow-2xl border transform -rotate-3 opacity-80 ${
                  isLight ? "border-slate-200 bg-white" : "border-[#1B2940] bg-[#0B111E]"
                }`}
              >
                <img
                  src="https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?q=80&w=400&auto=format&fit=crop"
                  alt="Avatar Collage 2"
                  className="w-full h-full object-cover brightness-90"
                />
              </div>
              {/* Front Card */}
              <div
                className={`absolute right-0 top-14 w-56 h-40 rounded-2xl overflow-hidden shadow-2xl border-2 transform rotate-2 ${
                  isLight
                    ? "border-blue-500 bg-white"
                    : "border-cyan-500/80 bg-[#0B111E]"
                }`}
              >
                <img
                  src="https://images.unsplash.com/photo-1522202176988-66273c2fd55f?q=80&w=500&auto=format&fit=crop"
                  alt="Avatar Collage 3"
                  className="w-full h-full object-cover"
                />
                <div className="absolute bottom-2 left-2 right-2 bg-black/70 backdrop-blur-md rounded-xl p-2 flex items-center justify-between text-white text-[11px] font-bold border border-white/10">
                  <span>✨ 4K Script Synced</span>
                  <div className="w-5 h-5 rounded-full bg-cyan-400 text-slate-950 flex items-center justify-center">
                    <Play size={10} className="fill-current ml-0.5" />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* 3. CATEGORY SELECTOR PILLS & SEARCH */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pt-2">
          {/* Centered Pill Category Tabs */}
          <div
            className={`p-1 rounded-full inline-flex items-center gap-1 border shadow-xs ${
              isLight ? "bg-slate-100 border-slate-200" : "bg-[#0B1220] border-[#1B2940]"
            }`}
          >
            <button
              type="button"
              onClick={() => setActiveTab("all")}
              className={`px-4 py-1.5 rounded-full text-xs transition-all cursor-pointer ${
                activeTab === "all"
                  ? isLight
                    ? "bg-white text-blue-600 font-bold shadow-xs border border-blue-200"
                    : "bg-[#101827] text-white font-bold shadow-xs border border-cyan-500/40"
                  : isLight
                  ? "text-slate-600 hover:text-slate-900 hover:bg-white/60 font-medium"
                  : "text-slate-400 hover:text-white font-medium hover:bg-[#101827]/50"
              }`}
            >
              All Apps
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("create")}
              className={`px-4 py-1.5 rounded-full text-xs transition-all cursor-pointer ${
                activeTab === "create"
                  ? isLight
                    ? "bg-white text-blue-600 font-bold shadow-xs border border-blue-200"
                    : "bg-[#101827] text-white font-bold shadow-xs border border-cyan-500/40"
                  : isLight
                  ? "text-slate-600 hover:text-slate-900 hover:bg-white/60 font-medium"
                  : "text-slate-400 hover:text-white font-medium hover:bg-[#101827]/50"
              }`}
            >
              Create
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("enhance")}
              className={`px-4 py-1.5 rounded-full text-xs transition-all cursor-pointer ${
                activeTab === "enhance"
                  ? isLight
                    ? "bg-white text-blue-600 font-bold shadow-xs border border-blue-200"
                    : "bg-[#101827] text-white font-bold shadow-xs border border-cyan-500/40"
                  : isLight
                  ? "text-slate-600 hover:text-slate-900 hover:bg-white/60 font-medium"
                  : "text-slate-400 hover:text-white font-medium hover:bg-[#101827]/50"
              }`}
            >
              Enhance
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("edit")}
              className={`px-4 py-1.5 rounded-full text-xs transition-all cursor-pointer ${
                activeTab === "edit"
                  ? isLight
                    ? "bg-white text-blue-600 font-bold shadow-xs border border-blue-200"
                    : "bg-[#101827] text-white font-bold shadow-xs border border-cyan-500/40"
                  : isLight
                  ? "text-slate-600 hover:text-slate-900 hover:bg-white/60 font-medium"
                  : "text-slate-400 hover:text-white font-medium hover:bg-[#101827]/50"
              }`}
            >
              Edit
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("interactive")}
              className={`px-4 py-1.5 rounded-full text-xs transition-all cursor-pointer ${
                activeTab === "interactive"
                  ? isLight
                    ? "bg-white text-blue-600 font-bold shadow-xs border border-blue-200"
                    : "bg-[#101827] text-white font-bold shadow-xs border border-cyan-500/40"
                  : isLight
                  ? "text-slate-600 hover:text-slate-900 hover:bg-white/60 font-medium"
                  : "text-slate-400 hover:text-white font-medium hover:bg-[#101827]/50"
              }`}
            >
              Interactive
            </button>
          </div>

          {/* Search Apps Input */}
          <div className="relative w-full sm:w-64">
            <Search
              size={14}
              className="absolute left-3.5 top-2.5 text-slate-500"
            />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search Apps"
              className={`w-full rounded-full pl-9 pr-3.5 py-1.5 text-xs shadow-xs focus:outline-none transition-all ${
                isLight
                  ? "bg-white border border-slate-200 text-slate-900 placeholder:text-slate-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
                  : "bg-[#0A0F1A] border border-[#1B2940] text-white placeholder:text-slate-500 focus:border-cyan-500 focus:ring-2 focus:ring-cyan-500/20"
              }`}
            />
          </div>
        </div>

        {/* 4. FEATURED 3-APP HORIZONTAL CARDS (Directly under category tabs) */}
        {(activeTab === "all" || activeTab === "create" || activeTab === "edit") &&
          !searchQuery.trim() && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
              {/* Card 1: Translate Videos */}
              <div
                onClick={() => {
                  if (onNavigateTranslate) {
                    onNavigateTranslate();
                  } else {
                    setSelectedApp({
                      id: "feat_translate",
                      name: "Translate Videos",
                      description: "Convert any video into 175+ languages with lip-sync",
                      category: "edit",
                      image:
                        "https://images.unsplash.com/photo-1522202176988-66273c2fd55f?q=80&w=800&auto=format&fit=crop",
                      modalTitle: "AI Video Translation & Lip-Sync",
                      modalDescription:
                        "Translate video audio into 175+ languages while preserving the original speaker's authentic voice timbre and adjusting lip movements.",
                    });
                  }
                }}
                className={`group relative h-48 rounded-3xl overflow-hidden transition-all duration-300 cursor-pointer border ${
                  isLight
                    ? "border-slate-200 bg-white shadow-sm hover:shadow-xl hover:border-blue-400"
                    : "border-[#1B2940] hover:border-cyan-500/50 bg-[#0B111E] shadow-lg hover:shadow-2xl hover:shadow-cyan-500/10"
                }`}
              >
                <img
                  src="https://images.unsplash.com/photo-1522202176988-66273c2fd55f?q=80&w=800&auto=format&fit=crop"
                  alt="Translate Videos"
                  className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500 brightness-90"
                />
                <div
                  className={`absolute inset-0 p-6 flex flex-col justify-between ${
                    isLight
                      ? "bg-gradient-to-t from-white/95 via-white/80 to-transparent"
                      : "bg-gradient-to-t from-[#0B111E] via-[#0B111E]/50 to-black/30"
                  }`}
                >
                  <h3
                    className={`text-xl font-black tracking-tight drop-shadow-xs transition-colors ${
                      isLight ? "text-slate-900 group-hover:text-blue-600" : "text-white group-hover:text-cyan-200"
                    }`}
                  >
                    Translate Videos
                  </h3>
                  <div>
                    <span
                      className={`inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-xs font-bold border backdrop-blur-md transition-all ${
                        isLight
                          ? "bg-slate-900 text-white border-slate-800 group-hover:bg-blue-600 group-hover:border-blue-600"
                          : "bg-[#07090e]/80 group-hover:bg-cyan-500 group-hover:text-slate-950 text-white border-[#1B2940] group-hover:border-cyan-500"
                      }`}
                    >
                      <span>Try Translate Videos</span>
                      <ArrowRight size={13} />
                    </span>
                  </div>
                </div>
              </div>

              {/* Card 2: PPT/PDF to Video */}
              <div
                onClick={() =>
                  setSelectedApp({
                    id: "feat_pdf",
                    name: "PPT/PDF to Video",
                    description: "Transform documents into engaging avatar videos",
                    category: "create",
                    image:
                      "https://images.unsplash.com/photo-1551836022-d5d88e9218df?q=80&w=800&auto=format&fit=crop",
                    modalTitle: "Document to Video Converter",
                    modalDescription:
                      "Upload any PowerPoint slide deck or PDF report. AI turns each page into an interactive video scene presented by your chosen avatar.",
                  })
                }
                className={`group relative h-48 rounded-3xl overflow-hidden transition-all duration-300 cursor-pointer border ${
                  isLight
                    ? "border-slate-200 bg-white shadow-sm hover:shadow-xl hover:border-blue-400"
                    : "border-[#1B2940] hover:border-cyan-500/50 bg-[#0B111E] shadow-lg hover:shadow-2xl hover:shadow-cyan-500/10"
                }`}
              >
                <img
                  src="https://images.unsplash.com/photo-1551836022-d5d88e9218df?q=80&w=800&auto=format&fit=crop"
                  alt="PPT/PDF to Video"
                  className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500 brightness-90"
                />
                <div
                  className={`absolute inset-0 p-6 flex flex-col justify-between ${
                    isLight
                      ? "bg-gradient-to-t from-white/95 via-white/80 to-transparent"
                      : "bg-gradient-to-t from-[#0B111E] via-[#0B111E]/50 to-black/30"
                  }`}
                >
                  <h3
                    className={`text-xl font-black tracking-tight drop-shadow-xs transition-colors ${
                      isLight ? "text-slate-900 group-hover:text-blue-600" : "text-white group-hover:text-cyan-200"
                    }`}
                  >
                    PPT/PDF to Video
                  </h3>
                  <div>
                    <span
                      className={`inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-xs font-bold border backdrop-blur-md transition-all ${
                        isLight
                          ? "bg-slate-900 text-white border-slate-800 group-hover:bg-blue-600 group-hover:border-blue-600"
                          : "bg-[#07090e]/80 group-hover:bg-cyan-500 group-hover:text-slate-950 text-white border-[#1B2940] group-hover:border-cyan-500"
                      }`}
                    >
                      <span>Try PPT/PDF to Video</span>
                      <ArrowRight size={13} />
                    </span>
                  </div>
                </div>
              </div>

              {/* Card 3: Cinematic Shots */}
              <div
                onClick={() =>
                  setSelectedApp({
                    id: "feat_shots",
                    name: "Avatar Shots",
                    description: "AI-powered cinematic, film-quality camera angles",
                    category: "create",
                    image:
                      "https://images.unsplash.com/photo-1534528741775-53994a69daeb?q=80&w=800&auto=format&fit=crop",
                    modalTitle: "Cinematic Avatar Shots",
                    modalDescription:
                      "Generate Hollywood-grade closeups, over-the-shoulder angles, and walking shots for high-production value commercials.",
                  })
                }
                className={`group relative h-48 rounded-3xl overflow-hidden transition-all duration-300 cursor-pointer border ${
                  isLight
                    ? "border-slate-200 bg-white shadow-sm hover:shadow-xl hover:border-blue-400"
                    : "border-[#1B2940] hover:border-cyan-500/50 bg-[#0B111E] shadow-lg hover:shadow-2xl hover:shadow-cyan-500/10"
                }`}
              >
                <img
                  src="https://images.unsplash.com/photo-1534528741775-53994a69daeb?q=80&w=800&auto=format&fit=crop"
                  alt="Cinematic Shots"
                  className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500 brightness-90"
                />
                <div
                  className={`absolute inset-0 p-6 flex flex-col justify-between ${
                    isLight
                      ? "bg-gradient-to-t from-white/95 via-white/80 to-transparent"
                      : "bg-gradient-to-t from-[#0B111E] via-[#0B111E]/50 to-black/30"
                  }`}
                >
                  <h3
                    className={`text-xl font-black tracking-tight drop-shadow-xs transition-colors ${
                      isLight ? "text-slate-900 group-hover:text-blue-600" : "text-white group-hover:text-cyan-200"
                    }`}
                  >
                    Cinematic Shots
                  </h3>
                  <div>
                    <span
                      className={`inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-xs font-bold border backdrop-blur-md transition-all ${
                        isLight
                          ? "bg-slate-900 text-white border-slate-800 group-hover:bg-blue-600 group-hover:border-blue-600"
                          : "bg-[#07090e]/80 group-hover:bg-cyan-500 group-hover:text-slate-950 text-white border-[#1B2940] group-hover:border-cyan-500"
                      }`}
                    >
                      <span>Try Cinematic Shots</span>
                      <ArrowRight size={13} />
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}

        {/* 5. SECTION 1: APPS TO CREATE... */}
        {(activeTab === "all" || activeTab === "create") &&
          filteredCreate.length > 0 && (
            <div className="space-y-6 pt-6">
              <div className="text-center">
                <h2
                  className={`text-2xl sm:text-3xl font-black tracking-tight ${
                    isLight ? "text-slate-900" : "text-white"
                  }`}
                >
                  Apps to <span className={isLight ? "text-blue-600" : "text-cyan-400"}>create</span> avatars,
                  <br />
                  videos, images and more.
                </h2>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-5">
                {filteredCreate.map((app) => (
                  <div
                    key={app.id}
                    onClick={() => handleAppClick(app)}
                    className={`group rounded-2xl border overflow-hidden transition-all duration-300 cursor-pointer flex flex-col justify-between select-none ${
                      isLight
                        ? "bg-white hover:bg-slate-50/90 border-slate-200 hover:border-blue-400 shadow-sm hover:shadow-xl"
                        : "bg-[#0B111E] hover:bg-[#101827] border-[#1B2940] hover:border-cyan-500/50 shadow-lg hover:shadow-2xl hover:shadow-cyan-500/10"
                    }`}
                  >
                    <div className="h-36 w-full overflow-hidden relative bg-slate-950">
                      <img
                        src={app.image}
                        alt={app.name}
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500 brightness-90 group-hover:brightness-95"
                      />
                      <div
                        className={`absolute inset-0 ${
                          isLight
                            ? "bg-gradient-to-t from-white via-transparent to-transparent"
                            : "bg-gradient-to-t from-[#0B111E] via-transparent to-transparent"
                        }`}
                      ></div>
                    </div>

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
                ))}
              </div>
            </div>
          )}

        {/* 6. SECTION 2: APPS TO ENHANCE... */}
        {(activeTab === "all" ||
          activeTab === "enhance" ||
          activeTab === "interactive") &&
          filteredEnhance.length > 0 && (
            <div className="space-y-6 pt-6">
              <div className="text-center">
                <h2
                  className={`text-2xl sm:text-3xl font-black tracking-tight ${
                    isLight ? "text-slate-900" : "text-white"
                  }`}
                >
                  Apps to <span className={isLight ? "text-emerald-600" : "text-emerald-400"}>enhance</span>
                  <br />
                  all that you create.
                </h2>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-5">
                {filteredEnhance.map((app) => (
                  <div
                    key={app.id}
                    onClick={() => handleAppClick(app)}
                    className={`group rounded-2xl border overflow-hidden transition-all duration-300 cursor-pointer flex flex-col justify-between select-none ${
                      isLight
                        ? "bg-white hover:bg-slate-50/90 border-slate-200 hover:border-emerald-500/70 shadow-sm hover:shadow-xl"
                        : "bg-[#0B111E] hover:bg-[#101827] border-[#1B2940] hover:border-emerald-500/50 shadow-lg hover:shadow-2xl hover:shadow-emerald-500/10"
                    }`}
                  >
                    <div className="h-36 w-full overflow-hidden relative bg-slate-950">
                      <img
                        src={app.image}
                        alt={app.name}
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500 brightness-90 group-hover:brightness-95"
                      />
                      <div
                        className={`absolute inset-0 ${
                          isLight
                            ? "bg-gradient-to-t from-white via-transparent to-transparent"
                            : "bg-gradient-to-t from-[#0B111E] via-transparent to-transparent"
                        }`}
                      ></div>
                    </div>

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
                              ? "text-slate-900 group-hover:text-emerald-600"
                              : "text-white group-hover:text-emerald-200"
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
                            ? "bg-slate-100 border-slate-200 group-hover:bg-emerald-600 group-hover:text-white text-slate-700 shadow-xs"
                            : "bg-[#101827] border-[#1B2940] group-hover:border-emerald-500/50 group-hover:bg-emerald-500 text-slate-300 group-hover:text-slate-950 shadow-md"
                        }`}
                      >
                        <ArrowRight
                          size={14}
                          className="transform group-hover:translate-x-0.5 transition-transform"
                        />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

        {/* 7. SECTION 3: APPS TO EDIT... */}
        {(activeTab === "all" || activeTab === "edit") &&
          filteredEdit.length > 0 && (
            <div className="space-y-6 pt-6">
              <div className="text-center">
                <h2
                  className={`text-2xl sm:text-3xl font-black tracking-tight ${
                    isLight ? "text-slate-900" : "text-white"
                  }`}
                >
                  Apps to <span className={isLight ? "text-purple-600" : "text-purple-400"}>edit</span>, change,
                  <br />
                  and remix your content
                </h2>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-5">
                {filteredEdit.map((app) => (
                  <div
                    key={app.id}
                    onClick={() => handleAppClick(app)}
                    className={`group rounded-2xl border overflow-hidden transition-all duration-300 cursor-pointer flex flex-col justify-between select-none ${
                      isLight
                        ? "bg-white hover:bg-slate-50/90 border-slate-200 hover:border-purple-500/70 shadow-sm hover:shadow-xl"
                        : "bg-[#0B111E] hover:bg-[#101827] border-[#1B2940] hover:border-purple-500/50 shadow-lg hover:shadow-2xl hover:shadow-purple-500/10"
                    }`}
                  >
                    <div className="h-36 w-full overflow-hidden relative bg-slate-950">
                      <img
                        src={app.image}
                        alt={app.name}
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500 brightness-90 group-hover:brightness-95"
                      />
                      <div
                        className={`absolute inset-0 ${
                          isLight
                            ? "bg-gradient-to-t from-white via-transparent to-transparent"
                            : "bg-gradient-to-t from-[#0B111E] via-transparent to-transparent"
                        }`}
                      ></div>
                    </div>

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
                              ? "text-slate-900 group-hover:text-purple-600"
                              : "text-white group-hover:text-purple-200"
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
                            ? "bg-slate-100 border-slate-200 group-hover:bg-purple-600 group-hover:text-white text-slate-700 shadow-xs"
                            : "bg-[#101827] border-[#1B2940] group-hover:border-purple-500/50 group-hover:bg-purple-500 text-slate-300 group-hover:text-slate-950 shadow-md"
                        }`}
                      >
                        <ArrowRight
                          size={14}
                          className="transform group-hover:translate-x-0.5 transition-transform"
                        />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
      </main>

      {/* FEATURED APPS DEDICATED STUDIOS & MODALS */}
      <FeaturedAppModals
        activeModal={activeFeaturedModal}
        onClose={() => setActiveFeaturedModal(null)}
        onOpenStudio={onOpenStudio}
      />

      {/* APP LAUNCH / INSPECTOR MODAL */}
      {selectedApp && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4 animate-in fade-in duration-200 select-none">
          <div className="w-full max-w-lg bg-[#0A0F1A] text-slate-100 rounded-3xl p-6 shadow-2xl border border-[#1B2940]">
            <div className="flex items-center justify-between pb-3 border-b border-[#1B2940] mb-4">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-2xl overflow-hidden bg-[#101827] border border-[#1B2940] shrink-0">
                  <img
                    src={selectedApp.image}
                    alt={selectedApp.name}
                    className="w-full h-full object-cover"
                  />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white">
                    {selectedApp.modalTitle}
                  </h3>
                  <span className="text-[10px] uppercase font-bold text-cyan-400 tracking-wider">
                    {selectedApp.category} Engine
                  </span>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setSelectedApp(null)}
                className="w-8 h-8 rounded-full hover:bg-[#101827] flex items-center justify-center text-slate-400 hover:text-white cursor-pointer"
              >
                <X size={18} />
              </button>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed mb-6">
              {selectedApp.modalDescription}
            </p>

            <div className="flex justify-end gap-2.5 pt-3 border-t border-[#1B2940]">
              <button
                type="button"
                onClick={() => setSelectedApp(null)}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-white hover:bg-[#101827] cursor-pointer"
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
                <span>Launch in Studio</span>
                <ArrowRight size={14} />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
