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
  SlidersHorizontal,
  Layers,
  FileText,
  Loader2,
  ExternalLink,
} from "lucide-react";
import AskRhysWidget from "../dashboard/AskRhysWidget";
import { BrandKitItem } from "./BrandSystems";
import { PresetBrandItem, presetBrandsList } from "./NewBrandSystem";

interface BrandSystemPreviewProps {
  initialPreset: PresetBrandItem;
  onBack: () => void;
  onCustomize: (preset: PresetBrandItem) => void;
  onUseSystem: (preset: PresetBrandItem) => void;
  onMakeCopy: (preset: PresetBrandItem) => void;
  onSaveBrandSystem: (newKit: BrandKitItem) => void;
  onOpenStudio?: () => void;
}

export default function BrandSystemPreview({
  initialPreset,
  onBack,
  onCustomize,
  onUseSystem,
  onMakeCopy,
  onSaveBrandSystem,
  onOpenStudio,
}: BrandSystemPreviewProps) {
  const [selectedPreset, setSelectedPreset] = useState<PresetBrandItem>(initialPreset);
  const [websiteUrl, setWebsiteUrl] = useState("");
  const [isImporting, setIsImporting] = useState(false);
  const carouselRef = useRef<HTMLDivElement>(null);

  const handleScrollCarousel = (direction: "left" | "right") => {
    if (carouselRef.current) {
      const scrollAmount = 300;
      carouselRef.current.scrollBy({
        left: direction === "right" ? scrollAmount : -scrollAmount,
        behavior: "smooth",
      });
    }
  };

  const handleImportWebsite = (e: React.FormEvent) => {
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
    onSaveBrandSystem(newKit);
  };

  const handleSave = () => {
    const newKit: BrandKitItem = {
      id: "",
      name: selectedPreset.name,
      isFavorite: false,
      logoText: selectedPreset.name.slice(0, 6),
      primaryColor: selectedPreset.primaryColor,
      accentColor: selectedPreset.accentColor,
      secondaryColor: selectedPreset.secondaryColor,
      fontFamily: selectedPreset.fontFamily,
      updatedAt: "Just now",
    };
    onSaveBrandSystem(newKit);
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
            title="Back to New Brand System"
          >
            <ArrowLeft size={16} />
          </button>
          <div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
              {selectedPreset.name}
            </h1>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => onMakeCopy(selectedPreset)}
            className="px-5 py-2.5 bg-[#0f172a] hover:bg-[#172238] text-slate-300 border border-[#1b2940] text-xs sm:text-sm font-semibold rounded-full shadow-xs transition-all cursor-pointer flex items-center gap-1.5"
          >
            <span>Make a copy</span>
          </button>

          <button
            type="button"
            onClick={() => onUseSystem(selectedPreset)}
            className="px-6 py-2.5 bg-white hover:bg-slate-200 text-slate-950 text-xs sm:text-sm font-bold rounded-full shadow-xs transition-all cursor-pointer flex items-center gap-2"
          >
            <Check size={15} />
            <span>Use this System</span>
          </button>

          <AskRhysWidget variant="banner" />
        </div>
      </div>

      {/* 2. MAIN BODY CONTENT */}
      <div className="max-w-6xl w-full mx-auto px-8 sm:px-10 py-8 space-y-10 flex-1">
        {/* SECTION 1: Website URL Extraction */}
        <div className="bg-[#0b111e] border border-[#1b2940] rounded-3xl p-7 sm:p-8 shadow-xl">
          <div className="max-w-2xl">
            <h2 className="text-lg sm:text-xl font-extrabold text-white tracking-tight mb-1.5">
              Instantly create a Brand System from your website
            </h2>
            <p className="text-xs sm:text-sm text-slate-400 leading-relaxed mb-5 font-normal">
              We can detect your brand and build a system with your logos, colors, and fonts.
            </p>

            {/* URL Input */}
            <form onSubmit={handleImportWebsite} className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
              <div className="relative flex-1">
                <Globe size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none" />
                <input
                  type="text"
                  value={websiteUrl}
                  onChange={(e) => setWebsiteUrl(e.target.value)}
                  placeholder="Paste your brand's website URL"
                  className="w-full bg-[#07090e] border border-[#1b2940] rounded-full pl-11 pr-4 py-2.5 text-xs sm:text-sm text-white placeholder:text-slate-500 focus:outline-none focus:border-cyan-500 focus:bg-[#090d16] shadow-xs transition-all"
                />
              </div>

              <button
                type="submit"
                disabled={!websiteUrl.trim() || isImporting}
                className="px-6 py-2.5 bg-white hover:bg-slate-200 disabled:bg-[#151f33] disabled:text-slate-600 disabled:cursor-not-allowed text-slate-950 text-xs sm:text-sm font-bold rounded-full shadow-xs transition-all flex items-center justify-center gap-2 cursor-pointer shrink-0"
              >
                {isImporting ? (
                  <>
                    <Loader2 size={15} className="animate-spin" />
                    <span>Importing...</span>
                  </>
                ) : (
                  <span>Import</span>
                )}
              </button>
            </form>
          </div>
        </div>

        {/* SECTION 2: Preset Horizontal Carousel */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg sm:text-xl font-extrabold text-white tracking-tight">
              Or start manually by choosing a preset
            </h2>

            <div className="flex items-center gap-3">
              {/* Customize Button */}
              <button
                type="button"
                onClick={() => onCustomize(selectedPreset)}
                className="px-4 py-1.5 bg-[#0f172a] hover:bg-[#172238] border border-[#1b2940] hover:border-slate-500 text-slate-200 text-xs font-bold rounded-full shadow-xs flex items-center gap-1.5 transition-all cursor-pointer"
              >
                <SlidersHorizontal size={13} />
                <span>Customize</span>
              </button>

              {/* Carousel Navigation Arrows */}
              <div className="flex items-center gap-1.5">
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
          </div>

          {/* Carousel Cards */}
          <div
            ref={carouselRef}
            className="flex items-stretch gap-4 overflow-x-auto pt-1 pb-4 scrollbar-none no-scrollbar snap-x"
          >
            {presetBrandsList.map((preset) => {
              const isSelected = selectedPreset.id === preset.id;
              return (
                <div
                  key={preset.id}
                  onClick={() => setSelectedPreset(preset)}
                  className={`w-64 sm:w-72 shrink-0 snap-start bg-[#0b111e] rounded-2xl overflow-hidden cursor-pointer border transition-all duration-200 flex flex-col justify-between group ${
                    isSelected
                      ? "border-cyan-500 ring-2 ring-cyan-500/40 shadow-lg"
                      : "border-[#1b2940] hover:border-slate-600 shadow-md hover:shadow-xl"
                  }`}
                >
                  {/* Preset Canvas */}
                  <div
                    className={`h-32 w-full bg-gradient-to-tr ${preset.previewGradient} p-4 flex flex-col justify-between relative overflow-hidden`}
                  >
                    <div className="flex items-center justify-between z-10">
                      {preset.tag ? (
                        <span className="text-[9px] font-mono uppercase tracking-wider bg-black/40 backdrop-blur-sm text-white px-2 py-0.5 rounded font-bold border border-white/10">
                          {preset.tag}
                        </span>
                      ) : (
                        <span className="text-[9px] font-mono uppercase tracking-wider text-white/70">
                          {preset.fontCategory}
                        </span>
                      )}

                      {isSelected && (
                        <div className="w-5 h-5 rounded-full bg-white text-slate-950 flex items-center justify-center font-bold shadow-md animate-in zoom-in-90 duration-150">
                          <Check size={12} strokeWidth={3} />
                        </div>
                      )}
                    </div>

                    <div className="z-10">
                      <div className={`text-xl font-black tracking-tight leading-none ${preset.textColor} drop-shadow-sm`}>
                        {preset.sampleText || preset.name}
                      </div>
                      <div className="text-[9px] text-white/80 font-mono mt-0.5">
                        {preset.fontFamily.split(",")[0]}
                      </div>
                    </div>

                    <div className="flex items-center gap-1 z-10">
                      <div
                        className="w-3.5 h-3.5 rounded border border-white/40 shadow-xs"
                        style={{ backgroundColor: preset.primaryColor }}
                      ></div>
                      <div
                        className="w-3.5 h-3.5 rounded border border-white/40 shadow-xs"
                        style={{ backgroundColor: preset.accentColor }}
                      ></div>
                      <div
                        className="w-3.5 h-3.5 rounded border border-white/40 shadow-xs"
                        style={{ backgroundColor: preset.secondaryColor }}
                      ></div>
                    </div>
                  </div>

                  {/* Card Title */}
                  <div className="p-3 bg-[#0b111e] border-t border-[#1b2940] flex items-center justify-between">
                    <span className="text-xs font-bold text-white truncate">
                      {preset.name}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* SECTION 3: Large Preview Area (Matches Reference Screenshot Layout) */}
        <div className="space-y-3">
          <div className="flex items-center justify-between px-1">
            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">
              {selectedPreset.name} Brand System Spec Sheet & Compositions
            </span>
            <span className="text-[11px] font-mono text-cyan-400 font-semibold flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse"></span>
              Live System Preview
            </span>
          </div>

          <div className="bg-[#090D16] border border-[#18233B] text-slate-100 rounded-3xl p-6 sm:p-8 shadow-2xl relative overflow-hidden">
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
              {/* LEFT COLUMN: Editorial Typography & Design Tokens */}
              <div className="lg:col-span-6 space-y-6">
                {/* 1. Oversized Claim Hero Box */}
                <div
                  className="rounded-2xl p-6 sm:p-8 relative overflow-hidden shadow-lg border border-white/10 flex flex-col justify-between min-h-[220px]"
                  style={{
                    background: `linear-gradient(135deg, ${selectedPreset.primaryColor}ee, ${selectedPreset.secondaryColor}dd)`,
                  }}
                >
                  <div className="flex items-center justify-between mb-4">
                    <span className="text-[9px] font-mono uppercase tracking-widest text-white/80 border border-white/20 px-2 py-0.5 rounded-full backdrop-blur-sm">
                      THE LEAD • 01
                    </span>
                    <span className="text-[10px] font-bold text-white/90">
                      16:9 SEQUENCE
                    </span>
                  </div>

                  <p className="text-2xl sm:text-3xl font-serif italic font-extrabold text-white leading-tight tracking-tight drop-shadow-md">
                    One bold idea, said once, owns the frame.
                  </p>

                  <div className="flex items-center justify-between mt-6 pt-3 border-t border-white/15">
                    <span className="text-[11px] font-mono text-white/80">
                      {selectedPreset.fontFamily.split(",")[0]} 700 Serif
                    </span>
                    <div className="flex items-center gap-1.5">
                      <div
                        className="w-4 h-4 rounded-full border border-white"
                        style={{ backgroundColor: selectedPreset.accentColor }}
                      ></div>
                      <span className="text-[10px] font-bold text-white uppercase tracking-wider">
                        {selectedPreset.name}
                      </span>
                    </div>
                  </div>
                </div>

                {/* 2. Typography Spec Sheet Table */}
                <div className="bg-[#0E1424] border border-[#1C2740] rounded-2xl p-5 shadow-inner space-y-4">
                  <div className="flex items-center justify-between pb-3 border-b border-[#1A253D]">
                    <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                      Typography Tokens
                    </span>
                    <span className="text-[10px] font-mono text-cyan-400">
                      Relative CQW Scale
                    </span>
                  </div>

                  {/* display-hero */}
                  <div className="flex items-center justify-between pb-3 border-b border-[#172238]">
                    <div>
                      <h4 className="text-xs font-bold italic text-white">display-hero</h4>
                      <p className="text-[10px] font-mono text-slate-400">
                        {selectedPreset.fontFamily.split(",")[0]} 600 • 154px • 8cqw
                      </p>
                    </div>
                    <div className="text-3xl font-extrabold tracking-tighter text-white">
                      Aa
                    </div>
                  </div>

                  {/* heading */}
                  <div className="flex items-center justify-between pb-3 border-b border-[#172238]">
                    <div>
                      <h4 className="text-xs font-bold italic text-white">heading</h4>
                      <p className="text-[10px] font-mono text-slate-400">
                        {selectedPreset.fontFamily.split(",")[0]} 700 • 36px • 2.1cqw
                      </p>
                    </div>
                    <div className="text-xl font-bold text-slate-100">
                      Heading Title
                    </div>
                  </div>

                  {/* link spec */}
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="text-xs font-bold italic text-white">link</h4>
                      <p className="text-[10px] font-mono text-slate-400">
                        {selectedPreset.fontFamily.split(",")[0]} 400 • 18px • 0.94cqw
                      </p>
                    </div>
                    <div
                      className="text-xs font-semibold underline underline-offset-4"
                      style={{ color: selectedPreset.accentColor }}
                    >
                      Aa — action link
                    </div>
                  </div>
                </div>

                {/* 3. Color Swatches Strip */}
                <div className="bg-[#0E1424] border border-[#1C2740] rounded-2xl p-4 shadow-inner">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-3">
                    Brand Color Palette
                  </span>

                  <div className="grid grid-cols-3 gap-3">
                    <div className="bg-[#090D18] border border-[#1B2742] rounded-xl p-2.5">
                      <div
                        className="w-full h-8 rounded-lg mb-2 shadow-xs border border-white/10"
                        style={{ backgroundColor: selectedPreset.primaryColor }}
                      ></div>
                      <span className="text-[10px] font-semibold text-slate-400 block">Primary</span>
                      <span className="text-[10px] font-mono text-slate-200">{selectedPreset.primaryColor}</span>
                    </div>

                    <div className="bg-[#090D18] border border-[#1B2742] rounded-xl p-2.5">
                      <div
                        className="w-full h-8 rounded-lg mb-2 shadow-xs border border-white/10"
                        style={{ backgroundColor: selectedPreset.accentColor }}
                      ></div>
                      <span className="text-[10px] font-semibold text-slate-400 block">Accent</span>
                      <span className="text-[10px] font-mono text-slate-200">{selectedPreset.accentColor}</span>
                    </div>

                    <div className="bg-[#090D18] border border-[#1B2742] rounded-xl p-2.5">
                      <div
                        className="w-full h-8 rounded-lg mb-2 shadow-xs border border-white/10"
                        style={{ backgroundColor: selectedPreset.secondaryColor }}
                      ></div>
                      <span className="text-[10px] font-semibold text-slate-400 block">Secondary</span>
                      <span className="text-[10px] font-mono text-slate-200">{selectedPreset.secondaryColor}</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* RIGHT COLUMN: Video Frame Compositions & Avatar Overlays */}
              <div className="lg:col-span-6 space-y-6">
                {/* 1. Identity / Cover Frame (Avatar Overlay + Wordmark) */}
                <div className="bg-[#0E1424] border border-[#1C2740] rounded-2xl p-4 shadow-inner">
                  <div className="flex items-center justify-between pb-2.5 border-b border-[#1A253D] mb-3">
                    <span className="text-xs font-bold text-white flex items-center gap-2">
                      <span
                        className="w-3.5 h-1 rounded-full inline-block"
                        style={{ backgroundColor: selectedPreset.accentColor }}
                      ></span>
                      <span>Identity / Cover Frame</span>
                    </span>
                    <span className="text-[10px] font-mono text-slate-400">avatar overlay + wordmark</span>
                  </div>

                  <div className="aspect-[16/10] bg-slate-900 rounded-xl overflow-hidden relative shadow-md border border-white/10">
                    <img
                      src="https://images.unsplash.com/photo-1534528741775-53994a69daeb?q=80&w=700&auto=format&fit=crop"
                      alt="Avatar Portrait"
                      className="w-full h-full object-cover object-top brightness-90"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-black/85 via-transparent to-black/20"></div>

                    {/* Top Tag */}
                    <span className="absolute top-3 left-3 text-[8px] font-bold bg-black/70 backdrop-blur-sm px-2 py-0.5 rounded text-white tracking-widest border border-white/10">
                      SPECIAL REPORT
                    </span>

                    {/* Lower Third Editorial Statement */}
                    <div className="absolute bottom-3 left-3 right-3 flex items-end justify-between">
                      <div>
                        <h4 className="text-lg sm:text-xl font-serif italic text-white leading-none drop-shadow-md">
                          The brief.
                        </h4>
                        <p className="text-[10px] text-slate-300 font-sans mt-1">
                          Consistent typography across every generated scene.
                        </p>
                      </div>

                      <div
                        className="w-7 h-7 rounded-lg flex items-center justify-center shadow-lg"
                        style={{ backgroundColor: selectedPreset.primaryColor }}
                      >
                        <span className="text-[10px] font-bold text-white">
                          {selectedPreset.name.charAt(0)}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* 2. System Comparison Card */}
                <div className="bg-[#0E1424] border border-[#1C2740] rounded-2xl p-4 shadow-inner">
                  <div className="flex items-center justify-between pb-2.5 border-b border-[#1A253D] mb-3">
                    <span className="text-xs font-bold text-white">
                      Live Output Sequencer Comparison
                    </span>
                    <span className="text-[10px] font-mono text-emerald-400 font-semibold">
                      Auto-Applied
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    {/* Without Brand System */}
                    <div className="bg-[#090D18] border border-[#1B2742] rounded-xl p-3 flex flex-col justify-between min-h-[100px]">
                      <div>
                        <span className="text-[9px] font-bold text-slate-500 uppercase tracking-wider block mb-1">
                          Default Unstyled
                        </span>
                        <p className="text-xs text-slate-400 font-sans leading-tight">
                          Generic video layout without brand guidelines.
                        </p>
                      </div>
                      <span className="text-[9px] text-slate-600">Standard Arial • Gray</span>
                    </div>

                    {/* With Brand System */}
                    <div
                      className="rounded-xl p-3 flex flex-col justify-between min-h-[100px] border"
                      style={{
                        backgroundColor: `${selectedPreset.primaryColor}22`,
                        borderColor: `${selectedPreset.accentColor}66`,
                      }}
                    >
                      <div>
                        <span
                          className="text-[9px] font-bold uppercase tracking-wider block mb-1"
                          style={{ color: selectedPreset.accentColor }}
                        >
                          With {selectedPreset.name}
                        </span>
                        <p className="text-xs font-serif italic text-white leading-tight font-bold">
                          Unified corporate voice and high-impact identity.
                        </p>
                      </div>
                      <span className="text-[9px] font-mono text-cyan-300">
                        {selectedPreset.fontFamily.split(",")[0]} • Applied
                      </span>
                    </div>
                  </div>
                </div>

                {/* 3. Studio Link Callout */}
                <div className="bg-gradient-to-r from-blue-900/30 to-indigo-900/30 border border-blue-500/20 rounded-2xl p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-blue-600/30 border border-blue-500/40 flex items-center justify-center text-cyan-400">
                      <Sparkles size={16} />
                    </div>
                    <div>
                      <h5 className="text-xs font-bold text-white">
                        Ready to use in VidoAI Studio
                      </h5>
                      <p className="text-[10px] text-slate-400">
                        Tokens dynamically linked to Studio Video sequencer.
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2.5 shrink-0">
                    <button
                      type="button"
                      onClick={() => onMakeCopy(selectedPreset)}
                      className="px-4 py-2 bg-white/10 hover:bg-white/20 text-white border border-white/20 text-xs font-semibold rounded-full shadow-xs transition-all cursor-pointer"
                    >
                      <span>Make a copy</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => onUseSystem(selectedPreset)}
                      className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold rounded-full shadow-md transition-all cursor-pointer flex items-center gap-1.5 shrink-0"
                    >
                      <span>Use this System</span>
                      <ArrowRight size={13} />
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
