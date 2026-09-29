"use client";

import React, { useState, useRef } from "react";
import {
  ArrowLeft,
  Globe,
  Sparkles,
  ChevronLeft,
  ChevronRight,
  Check,
  ArrowRight,
  Palette,
  Loader2,
} from "lucide-react";
import AskRhysWidget from "../dashboard/AskRhysWidget";
import { BrandKitItem } from "./BrandSystems";

export interface PresetBrandItem {
  id: string;
  name: string;
  description: string;
  primaryColor: string;
  accentColor: string;
  secondaryColor: string;
  fontFamily: string;
  fontCategory: string;
  previewGradient: string;
  textColor: string;
  sampleText?: string;
  tag?: string;
}

export const presetBrandsList: PresetBrandItem[] = [
  {
    id: "preset-signal",
    name: "Signal",
    description: "High-energy tech & broadcast",
    primaryColor: "#F97316",
    accentColor: "#FBBF24",
    secondaryColor: "#1E293B",
    fontFamily: "Outfit, sans-serif",
    fontCategory: "Bold Geometric",
    previewGradient: "from-orange-500 via-amber-500 to-slate-900",
    textColor: "text-white",
    sampleText: "Signal",
    tag: "Trending",
  },
  {
    id: "preset-block-frame",
    name: "BLOCK FRAME",
    description: "Geometric structural blocks",
    primaryColor: "#6366F1",
    accentColor: "#A855F7",
    secondaryColor: "#0F172A",
    fontFamily: "Space Grotesk, sans-serif",
    fontCategory: "Display Sans",
    previewGradient: "from-indigo-600 via-purple-600 to-slate-950",
    textColor: "text-white",
    sampleText: "BLOCK",
    tag: "Popular",
  },
  {
    id: "preset-blue-prof",
    name: "Blue Professional",
    description: "Enterprise SaaS & corporate trust",
    primaryColor: "#0284C7",
    accentColor: "#38BDF8",
    secondaryColor: "#0F172A",
    fontFamily: "Inter, sans-serif",
    fontCategory: "Clean Sans",
    previewGradient: "from-sky-600 via-blue-700 to-slate-950",
    textColor: "text-white",
    sampleText: "Pro Blue",
  },
  {
    id: "preset-mat",
    name: "Mat",
    description: "Warm matte editorial & modern architecture",
    primaryColor: "#292524",
    accentColor: "#D6D3D1",
    secondaryColor: "#E7E5E4",
    fontFamily: "Plus Jakarta Sans, sans-serif",
    fontCategory: "Modern Neutral",
    previewGradient: "from-stone-800 via-stone-700 to-stone-900",
    textColor: "text-white",
    sampleText: "Matte",
  },
  {
    id: "preset-vellum",
    name: "Vellum",
    description: "Editorial luxury & literary serif",
    primaryColor: "#78350F",
    accentColor: "#FDE68A",
    secondaryColor: "#451A03",
    fontFamily: "Playfair Display, serif",
    fontCategory: "Luxury Serif",
    previewGradient: "from-amber-800 via-yellow-900 to-stone-950",
    textColor: "text-amber-100",
    sampleText: "Vellum",
  },
  {
    id: "preset-sage-lime",
    name: "Sage Lime Fintech",
    description: "Electric growth & modern wealth",
    primaryColor: "#064E3B",
    accentColor: "#84CC16",
    secondaryColor: "#022C22",
    fontFamily: "Geist, sans-serif",
    fontCategory: "Fintech Modern",
    previewGradient: "from-emerald-800 via-teal-900 to-slate-950",
    textColor: "text-lime-300",
    sampleText: "Fintech",
    tag: "New",
  },
  {
    id: "preset-pink-black",
    name: "Creator Neon",
    description: "Vibrant high-contrast social creator",
    primaryColor: "#DB2777",
    accentColor: "#F43F5E",
    secondaryColor: "#18181B",
    fontFamily: "Outfit, sans-serif",
    fontCategory: "Vibrant Display",
    previewGradient: "from-pink-600 via-rose-700 to-zinc-950",
    textColor: "text-white",
    sampleText: "Neon",
  },
  {
    id: "preset-stencil-tablet",
    name: "Stencil Tablet",
    description: "Industrial blueprint & developer tech",
    primaryColor: "#334155",
    accentColor: "#EA580C",
    secondaryColor: "#0F172A",
    fontFamily: "Space Mono, monospace",
    fontCategory: "Tech Mono",
    previewGradient: "from-slate-700 via-slate-800 to-zinc-950",
    textColor: "text-orange-400",
    sampleText: "STENCIL",
  },
  {
    id: "preset-playful",
    name: "Playful",
    description: "Bright consumer & energetic storytelling",
    primaryColor: "#F59E0B",
    accentColor: "#EC4899",
    secondaryColor: "#3B82F6",
    fontFamily: "Outfit, sans-serif",
    fontCategory: "Playful Rounded",
    previewGradient: "from-amber-500 via-rose-500 to-blue-600",
    textColor: "text-white",
    sampleText: "Playful",
  },
  {
    id: "preset-cartesian",
    name: "Cartesian",
    description: "Precise coordinates & structured cobalt grid",
    primaryColor: "#1D4ED8",
    accentColor: "#60A5FA",
    secondaryColor: "#1E3A8A",
    fontFamily: "Space Mono, monospace",
    fontCategory: "Structured Mono",
    previewGradient: "from-blue-700 via-indigo-800 to-slate-950",
    textColor: "text-sky-200",
    sampleText: "(x, y)",
  },
  {
    id: "preset-mono-minimal",
    name: "Mono Minimal",
    description: "High-fashion monochrome minimalism",
    primaryColor: "#000000",
    accentColor: "#71717A",
    secondaryColor: "#27272A",
    fontFamily: "Inter, sans-serif",
    fontCategory: "Swiss Minimal",
    previewGradient: "from-zinc-900 via-neutral-900 to-black",
    textColor: "text-white",
    sampleText: "Minimal",
  },
  {
    id: "preset-sunset-aura",
    name: "Sunset Aura",
    description: "Radiant violet & dusk amber warmth",
    primaryColor: "#9333EA",
    accentColor: "#F97316",
    secondaryColor: "#4C1D95",
    fontFamily: "Outfit, sans-serif",
    fontCategory: "Soft Aura",
    previewGradient: "from-purple-600 via-fuchsia-600 to-amber-600",
    textColor: "text-white",
    sampleText: "Aura",
  },
];

interface NewBrandSystemProps {
  onBack: () => void;
  onSelectPreset: (preset: PresetBrandItem) => void;
  onCreateBrand: (newKit: BrandKitItem) => void;
  onOpenStudio?: () => void;
}

export default function NewBrandSystem({
  onBack,
  onSelectPreset,
  onCreateBrand,
  onOpenStudio,
}: NewBrandSystemProps) {
  const [websiteUrl, setWebsiteUrl] = useState("");
  const [isExtracting, setIsExtracting] = useState(false);
  const [selectedPresetId, setSelectedPresetId] = useState<string>("preset-signal");
  const carouselRef = useRef<HTMLDivElement>(null);

  const selectedPreset =
    presetBrandsList.find((p) => p.id === selectedPresetId) || presetBrandsList[0];

  const handleScrollCarousel = (direction: "left" | "right") => {
    if (carouselRef.current) {
      const scrollAmount = 300;
      carouselRef.current.scrollBy({
        left: direction === "right" ? scrollAmount : -scrollAmount,
        behavior: "smooth",
      });
    }
  };

  const handleExtractWebsite = (e: React.FormEvent) => {
    e.preventDefault();
    if (!websiteUrl.trim()) return;

    let domain = websiteUrl.replace(/^https?:\/\//i, "").replace(/\/.*$/, "").trim();
    if (!domain) domain = "Custom Studio";

    const capitalizedName =
      domain.charAt(0).toUpperCase() + domain.slice(1).split(".")[0] + " Brand Kit";

    const newKit: BrandKitItem = {
      id: "",
      name: capitalizedName,
      isFavorite: false,
      logoText: capitalizedName.slice(0, 6),
      primaryColor: "#0f172a",
      accentColor: "#0284c7",
      secondaryColor: "#64748b",
      fontFamily: "Inter, sans-serif",
      updatedAt: "Just now",
    };
    onCreateBrand(newKit);
  };

  const handleCreateFromPreset = () => {
    const newKit: BrandKitItem = {
      id: "",
      name: `${selectedPreset.name} Brand Kit`,
      isFavorite: false,
      logoText: selectedPreset.name.slice(0, 6),
      primaryColor: selectedPreset.primaryColor,
      accentColor: selectedPreset.accentColor,
      secondaryColor: selectedPreset.secondaryColor,
      fontFamily: selectedPreset.fontFamily,
      updatedAt: "Just now",
    };
    onCreateBrand(newKit);
  };

  return (
    <div className="flex-1 h-screen overflow-y-auto bg-[#07090e] text-slate-100 flex flex-col font-sans select-none">
      {/* 1. TOP HEADER */}
      <div className="w-full px-8 sm:px-10 pt-8 pb-5 flex items-center justify-between border-b border-[#1b2940] bg-[#07090e] z-20 sticky top-0">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={onBack}
            className="w-9 h-9 rounded-full border border-[#1b2940] bg-[#0b111e] hover:bg-[#162035] flex items-center justify-center text-slate-300 hover:text-white transition-colors cursor-pointer shadow-xs"
            title="Back to Brand Systems"
          >
            <ArrowLeft size={16} />
          </button>
          <div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
              New Brand System
            </h1>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <AskRhysWidget variant="banner" />
        </div>
      </div>

      {/* 2. MAIN BODY */}
      <div className="max-w-6xl w-full mx-auto px-8 sm:px-10 py-8 space-y-12 flex-1">
        {/* SECTION 1: Website URL Extraction */}
        <div className="bg-[#0b111e] border border-[#1b2940] rounded-3xl p-7 sm:p-9 shadow-xl">
          <div className="max-w-2xl">
            <h2 className="text-xl sm:text-2xl font-extrabold text-white tracking-tight mb-2">
              Instantly create a Brand System from your website
            </h2>
            <p className="text-xs sm:text-sm text-slate-400 leading-relaxed mb-6 font-normal">
              Enter your website URL to automatically extract your brand colors, fonts, logo, and visual style without manual setup.
            </p>

            {/* URL Input Form */}
            <form onSubmit={handleExtractWebsite} className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
              <div className="relative flex-1">
                <Globe size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none" />
                <input
                  type="text"
                  value={websiteUrl}
                  onChange={(e) => setWebsiteUrl(e.target.value)}
                  placeholder="https://yourcompany.com"
                  className="w-full bg-[#07090e] border border-[#1b2940] rounded-full pl-11 pr-4 py-3 text-xs sm:text-sm text-white placeholder:text-slate-500 focus:outline-none focus:border-cyan-500 focus:bg-[#090d16] shadow-xs transition-all"
                />
              </div>

              <button
                type="submit"
                disabled={!websiteUrl.trim() || isExtracting}
                className="px-7 py-3 bg-white hover:bg-slate-200 disabled:bg-[#151f33] disabled:text-slate-600 disabled:cursor-not-allowed text-slate-950 text-xs sm:text-sm font-bold rounded-full shadow-xs transition-all flex items-center justify-center gap-2 cursor-pointer shrink-0"
              >
                {isExtracting ? (
                  <>
                    <Loader2 size={16} className="animate-spin" />
                    <span>Extracting...</span>
                  </>
                ) : (
                  <>
                    <Sparkles size={15} />
                    <span>Create Brand System</span>
                  </>
                )}
              </button>
            </form>
          </div>
        </div>

        {/* SECTION 2: Manual Preset Gallery */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl sm:text-2xl font-extrabold text-white tracking-tight">
                Or start manually by choosing a preset
              </h2>
              <p className="text-xs sm:text-sm text-slate-400 mt-1 font-normal">
                Select one of our curated design systems as a starting point. You can customize colors, fonts, and assets anytime.
              </p>
            </div>

            {/* Carousel Arrow Controls */}
            <div className="flex items-center gap-2 shrink-0">
              <button
                type="button"
                onClick={() => handleScrollCarousel("left")}
                className="w-8 h-8 rounded-full bg-[#0b111e] border border-[#1b2940] hover:bg-[#162035] text-slate-300 hover:text-white flex items-center justify-center transition-colors shadow-xs cursor-pointer"
                title="Scroll Left"
              >
                <ChevronLeft size={16} />
              </button>
              <button
                type="button"
                onClick={() => handleScrollCarousel("right")}
                className="w-8 h-8 rounded-full bg-[#0b111e] border border-[#1b2940] hover:bg-[#162035] text-slate-300 hover:text-white flex items-center justify-center transition-colors shadow-xs cursor-pointer"
                title="Scroll Right"
              >
                <ChevronRight size={16} />
              </button>
            </div>
          </div>

          {/* Horizontally Scrollable Preset Gallery Carousel */}
          <div
            ref={carouselRef}
            className="flex items-stretch gap-5 overflow-x-auto pt-2 pb-5 scrollbar-none no-scrollbar snap-x"
          >
            {presetBrandsList.map((preset) => {
              const isSelected = selectedPresetId === preset.id;
              return (
                <div
                  key={preset.id}
                  onClick={() => onSelectPreset(preset)}
                  className={`w-72 sm:w-80 shrink-0 snap-start bg-[#0b111e] rounded-3xl overflow-hidden cursor-pointer border transition-all duration-200 flex flex-col justify-between group ${
                    isSelected
                      ? "border-cyan-500 ring-2 ring-cyan-500/40 shadow-lg"
                      : "border-[#1b2940] hover:border-slate-600 shadow-md hover:shadow-xl"
                  }`}
                >
                  {/* Preset Visual Banner Canvas */}
                  <div
                    className={`h-40 w-full bg-gradient-to-tr ${preset.previewGradient} p-5 flex flex-col justify-between relative overflow-hidden`}
                  >
                    {/* Top Row: Tag / Indicator & Selection Badge */}
                    <div className="flex items-center justify-between z-10">
                      {preset.tag ? (
                        <span className="text-[9px] font-mono uppercase tracking-wider bg-black/40 backdrop-blur-sm text-white px-2 py-0.5 rounded-md font-bold border border-white/10">
                          {preset.tag}
                        </span>
                      ) : (
                        <span className="text-[9px] font-mono uppercase tracking-wider text-white/70">
                          {preset.fontCategory}
                        </span>
                      )}

                      {isSelected ? (
                        <div className="w-6 h-6 rounded-full bg-white text-slate-950 flex items-center justify-center font-bold shadow-md animate-in zoom-in-90 duration-150">
                          <Check size={13} strokeWidth={3} />
                        </div>
                      ) : (
                        <div className="w-6 h-6 rounded-full border border-white/40 group-hover:border-white/80 transition-colors"></div>
                      )}
                    </div>

                    {/* Center Brand Typography Sample */}
                    <div className="z-10 my-auto">
                      <div
                        className={`text-2xl font-black tracking-tight leading-none ${preset.textColor} drop-shadow-sm`}
                      >
                        {preset.sampleText || preset.name}
                      </div>
                      <div className="text-[10px] text-white/80 font-mono mt-1">
                        {preset.fontFamily.split(",")[0]}
                      </div>
                    </div>

                    {/* Bottom Color Palette Dots / Swatches */}
                    <div className="flex items-center gap-1.5 z-10">
                      <div
                        className="w-4 h-4 rounded-md border border-white/40 shadow-xs"
                        style={{ backgroundColor: preset.primaryColor }}
                      ></div>
                      <div
                        className="w-4 h-4 rounded-md border border-white/40 shadow-xs"
                        style={{ backgroundColor: preset.accentColor }}
                      ></div>
                      <div
                        className="w-4 h-4 rounded-md border border-white/40 shadow-xs"
                        style={{ backgroundColor: preset.secondaryColor }}
                      ></div>
                    </div>
                  </div>

                  {/* Preset Footer Info */}
                  <div className="p-4 bg-[#0b111e] flex items-center justify-between border-t border-[#1b2940]">
                    <div>
                      <h3 className="text-sm font-bold text-white truncate">
                        {preset.name}
                      </h3>
                      <p className="text-[11px] text-slate-400 truncate mt-0.5">
                        {preset.description}
                      </p>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Bottom Actions Bar for Preset Selection */}
          <div className="bg-[#0b111e] border border-[#1b2940] rounded-2xl p-4 px-6 flex flex-col sm:flex-row items-center justify-between gap-4 shadow-xl">
            <div className="flex items-center gap-3">
              <div
                className="w-8 h-8 rounded-xl flex items-center justify-center shadow-xs"
                style={{ backgroundColor: selectedPreset.primaryColor }}
              >
                <Palette size={16} className="text-white" />
              </div>
              <div>
                <span className="text-xs font-semibold text-slate-400 block">
                  Selected Preset
                </span>
                <span className="text-sm font-bold text-white">
                  {selectedPreset.name} • {selectedPreset.fontFamily.split(",")[0]}
                </span>
              </div>
            </div>

            <div className="flex items-center gap-3 w-full sm:w-auto">
              <button
                type="button"
                onClick={onBack}
                className="flex-1 sm:flex-none px-5 py-2.5 bg-[#0f172a] hover:bg-[#172238] text-slate-300 border border-[#1b2940] text-xs font-bold rounded-full transition-all cursor-pointer shadow-xs"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => onSelectPreset(selectedPreset)}
                className="flex-1 sm:flex-none px-7 py-2.5 bg-white hover:bg-slate-200 text-slate-950 text-xs font-bold rounded-full shadow-xs transition-all flex items-center justify-center gap-2 cursor-pointer"
              >
                <span>Continue with {selectedPreset.name}</span>
                <ArrowRight size={14} />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
