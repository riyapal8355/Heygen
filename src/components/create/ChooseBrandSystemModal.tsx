"use client";

import React, { useState, useRef, useEffect } from "react";
import {
  X,
  ArrowLeft,
  ArrowRight,
  Plus,
  Check,
  ChevronRight,
  Eye,
  Sparkles,
  Palette,
  Layers,
  ChevronLeft,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";

export interface BrandSystemData {
  id: string;
  name: string;
  fullName?: string;
  category: "custom" | "preset";
  primaryColor: string;
  accentColor: string;
  secondaryColor: string;
  fontFamily: string;
  previewGradient: string;
  badge?: string;
  hasPreviewPill?: boolean;
}

const initialCustomBrands: BrandSystemData[] = [];

const initialPresetBrands: BrandSystemData[] = [
  {
    id: "preset-signal",
    name: "Signal",
    category: "preset",
    primaryColor: "#f97316",
    accentColor: "#fbbf24",
    secondaryColor: "#1e293b",
    fontFamily: "Outfit, sans-serif",
    previewGradient: "from-orange-500/90 via-amber-600/80 to-slate-900",
  },
  {
    id: "preset-block-frame",
    name: "Block Frame",
    category: "preset",
    primaryColor: "#6366f1",
    accentColor: "#a855f7",
    secondaryColor: "#0f172a",
    fontFamily: "Space Grotesk, sans-serif",
    previewGradient: "from-indigo-600/90 via-purple-700/80 to-slate-950",
    hasPreviewPill: true,
  },
  {
    id: "preset-blue-prof",
    name: "Blue Professional",
    category: "preset",
    primaryColor: "#0284c7",
    accentColor: "#38bdf8",
    secondaryColor: "#0f172a",
    fontFamily: "Inter, sans-serif",
    previewGradient: "from-sky-600/90 via-blue-700/80 to-slate-950",
  },
  {
    id: "preset-studio-dark",
    name: "Studio Minimal",
    category: "preset",
    primaryColor: "#10b981",
    accentColor: "#34d399",
    secondaryColor: "#064e3b",
    fontFamily: "Geist, sans-serif",
    previewGradient: "from-emerald-600/90 via-teal-800/80 to-slate-950",
  },
  {
    id: "preset-vibrant-neon",
    name: "Creator Neon",
    category: "preset",
    primaryColor: "#ec4899",
    accentColor: "#f43f5e",
    secondaryColor: "#581c87",
    fontFamily: "Outfit, sans-serif",
    previewGradient: "from-pink-600/90 via-rose-700/80 to-purple-950",
  },
];

interface ChooseBrandSystemModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectBrandSystem: (brand: BrandSystemData) => void;
  selectedBrandId?: string;
}

export default function ChooseBrandSystemModal({
  isOpen,
  onClose,
  onSelectBrandSystem,
  selectedBrandId = "",
}: ChooseBrandSystemModalProps) {
  const { currentWorkspace } = useAuth();
  const [customBrands, setCustomBrands] = useState<BrandSystemData[]>(initialCustomBrands);
  const [selectedId, setSelectedId] = useState(selectedBrandId);
  const [isViewAllExpanded, setIsViewAllExpanded] = useState(false);
  const [isNewBrandModalOpen, setIsNewBrandModalOpen] = useState(false);
  const [newBrandName, setNewBrandName] = useState("");
  const [previewModalBrand, setPreviewModalBrand] = useState<BrandSystemData | null>(null);

  const carouselRef = useRef<HTMLDivElement>(null);
  const modalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!currentWorkspace?.id || !isOpen) return;
    api.brandKits
      .list(currentWorkspace.id)
      .then((kits) => {
        if (Array.isArray(kits) && kits.length > 0) {
          const dynamicKits: BrandSystemData[] = kits.map((k) => ({
            id: k.id,
            name: k.name,
            fullName: k.name,
            category: "custom",
            primaryColor: k.primary_color || "#0f172a",
            accentColor: k.accent_color || "#06b6d4",
            secondaryColor: k.secondary_color || "#8b5cf6",
            fontFamily: k.font_family || "Inter, sans-serif",
            previewGradient: "from-slate-900 via-[#131b2e] to-[#0f172a]",
          }));
          setCustomBrands(dynamicKits);
        }
      })
      .catch((err) => {
        console.error("Failed to fetch brand kits:", err);
      });
  }, [currentWorkspace?.id, isOpen]);

  // Sync selectedId when modal opens
  useEffect(() => {
    if (isOpen && selectedBrandId) {
      setSelectedId(selectedBrandId);
    }
  }, [isOpen, selectedBrandId]);

  // Close on Escape key
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        if (previewModalBrand) {
          setPreviewModalBrand(null);
        } else if (isNewBrandModalOpen) {
          setIsNewBrandModalOpen(false);
        } else {
          onClose();
        }
      }
    }
    if (isOpen) {
      window.addEventListener("keydown", handleKeyDown);
    }
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose, previewModalBrand, isNewBrandModalOpen]);

  if (!isOpen) return null;

  const handleScrollCarousel = (direction: "left" | "right") => {
    if (carouselRef.current) {
      const scrollAmount = 260;
      carouselRef.current.scrollBy({
        left: direction === "right" ? scrollAmount : -scrollAmount,
        behavior: "smooth",
      });
    }
  };

  const handleCreateNewBrand = async () => {
    if (!newBrandName.trim()) return;
    if (currentWorkspace?.id) {
      try {
        const kit = await api.brandKits.create(
          {
            name: newBrandName.trim(),
            primary_color: "#0f172a",
            accent_color: "#0284c7",
            secondary_color: "#64748b",
            font_family: "Inter, sans-serif",
          },
          currentWorkspace.id
        );
        const created: BrandSystemData = {
          id: kit.id,
          name: kit.name,
          fullName: kit.name,
          category: "custom",
          primaryColor: kit.primary_color || "#0f172a",
          accentColor: kit.accent_color || "#0284c7",
          secondaryColor: kit.secondary_color || "#64748b",
          fontFamily: kit.font_family || "Inter, sans-serif",
          previewGradient: "from-slate-900 via-[#1a233b] to-[#0d1424]",
        };
        setCustomBrands((prev) => [created, ...prev]);
        setSelectedId(created.id);
        setNewBrandName("");
        setIsNewBrandModalOpen(false);
        return;
      } catch (err: any) {
        alert(err?.message || "Failed to create brand kit");
      }
    }
  };

  const handleContinue = () => {
    const all = [...customBrands, ...initialPresetBrands];
    const chosen = all.find((b) => b.id === selectedId) || customBrands[0];
    onSelectBrandSystem(chosen);
    onClose();
  };

  return (
    <div
      onClick={(e) => {
        if (modalRef.current && !modalRef.current.contains(e.target as Node)) {
          onClose();
        }
      }}
      className="fixed inset-0 z-50 bg-black/75 backdrop-blur-md flex items-center justify-center p-4 overflow-y-auto animate-in fade-in duration-200 select-none"
    >
      <div
        ref={modalRef}
        className="w-full max-w-4xl lg:max-w-5xl bg-[#0A0F1A] rounded-3xl p-6 sm:p-8 shadow-2xl border border-[#1B2940] text-slate-100 my-6 max-h-[94vh] flex flex-col relative animate-in zoom-in-95 duration-150"
      >
        {/* 1. Modal Header */}
        <div className="flex items-center justify-between pb-4 border-b border-[#1B2940] flex-shrink-0">
          <h2 className="text-xl sm:text-2xl font-black text-white tracking-tight">
            Choose a Brand System
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="w-8 h-8 rounded-full hover:bg-[#101827] flex items-center justify-center text-slate-400 hover:text-white transition-colors cursor-pointer"
            title="Close"
          >
            <X size={18} />
          </button>
        </div>

        {/* 2. Scrollable Body */}
        <div className="flex-1 overflow-y-auto py-5 pr-1 space-y-7 scrollbar-thin scrollbar-thumb-slate-800">
          {/* SECTION A: Your Brand Systems */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm sm:text-base font-extrabold text-white">
                Your Brand Systems
              </h3>
              <button
                type="button"
                onClick={() => setIsViewAllExpanded(!isViewAllExpanded)}
                className="text-xs font-bold text-slate-400 hover:text-cyan-400 flex items-center gap-1 transition-colors cursor-pointer"
              >
                <span>{isViewAllExpanded ? "Show Less <" : "View All >"}</span>
              </button>
            </div>

            {/* Two Large Custom Brand Cards Side-by-Side */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {customBrands.map((brand) => {
                const isSelected = selectedId === brand.id;
                return (
                  <div
                    key={brand.id}
                    onClick={() => setSelectedId(brand.id)}
                    className={`group relative rounded-2xl overflow-hidden cursor-pointer border transition-all duration-200 flex flex-col justify-between ${
                      isSelected
                        ? "border-cyan-500 ring-2 ring-cyan-500/40 shadow-lg shadow-cyan-500/10"
                        : "border-[#1B2940] hover:border-cyan-500/40 bg-[#0B111E]"
                    }`}
                  >
                    {/* Visual Brand Kit Preview Canvas */}
                    <div
                      className={`h-40 sm:h-44 w-full bg-gradient-to-tr ${brand.previewGradient} p-5 flex flex-col justify-between text-white relative overflow-hidden`}
                    >
                      {/* Ambient Brand Logo / Text */}
                      <div className="flex items-center justify-between z-10">
                        <div className="flex items-center gap-2">
                          <div
                            className="w-4 h-4 rounded-full border border-white/40"
                            style={{ backgroundColor: brand.accentColor }}
                          ></div>
                          <span className="text-xs font-mono uppercase tracking-widest text-slate-300">
                            Brand Kit
                          </span>
                        </div>
                        {isSelected && (
                          <div className="w-6 h-6 rounded-full bg-cyan-400 text-slate-950 flex items-center justify-center font-bold shadow-md animate-in zoom-in-90 duration-150">
                            <Check size={14} strokeWidth={3} />
                          </div>
                        )}
                      </div>

                      {/* Center Brand typography showcase */}
                      <div className="z-10">
                        <div className="text-xl sm:text-2xl font-black tracking-tight leading-none text-white drop-shadow-sm">
                          HeyGen
                        </div>
                        <div className="text-[11px] text-slate-300 font-mono mt-1">
                          Aa Bb Gg 123 • {brand.fontFamily.split(",")[0]}
                        </div>
                      </div>

                      {/* Color Palette Swatches at Bottom */}
                      <div className="flex items-center gap-2 z-10">
                        <div
                          className="w-5 h-5 rounded-md border border-white/30 shadow-xs"
                          style={{ backgroundColor: brand.primaryColor }}
                        ></div>
                        <div
                          className="w-5 h-5 rounded-md border border-white/30 shadow-xs"
                          style={{ backgroundColor: brand.accentColor }}
                        ></div>
                        <div
                          className="w-5 h-5 rounded-md border border-white/30 shadow-xs"
                          style={{ backgroundColor: brand.secondaryColor }}
                        ></div>
                      </div>

                      {/* Background Ambient Glow */}
                      <div
                        className="absolute -right-10 -bottom-10 w-36 h-36 rounded-full blur-2xl opacity-40 pointer-events-none"
                        style={{ backgroundColor: brand.accentColor }}
                      ></div>
                    </div>

                    {/* Brand Name Footer */}
                    <div className="p-3.5 bg-[#0B111E] border-t border-[#1B2940] flex items-center justify-between">
                      <span className="text-xs sm:text-sm font-bold text-white truncate">
                        {brand.name}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* SECTION B: Preset Brand Systems Carousel */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm sm:text-base font-extrabold text-white">
                Or select a Brand System preset
              </h3>

              {/* Scroll controls */}
              <div className="flex items-center gap-1.5">
                <button
                  type="button"
                  onClick={() => handleScrollCarousel("left")}
                  className="w-7 h-7 rounded-full bg-[#101827] hover:bg-[#152033] border border-[#1B2940] text-slate-300 hover:text-white flex items-center justify-center transition-colors cursor-pointer"
                  title="Previous"
                >
                  <ChevronLeft size={15} />
                </button>
                <button
                  type="button"
                  onClick={() => handleScrollCarousel("right")}
                  className="w-7 h-7 rounded-full bg-[#101827] hover:bg-[#152033] border border-[#1B2940] text-slate-300 hover:text-white flex items-center justify-center transition-colors cursor-pointer"
                  title="Next"
                >
                  <ChevronRight size={15} />
                </button>
              </div>
            </div>

            {/* Horizontal Presets Carousel */}
            <div
              ref={carouselRef}
              className="flex items-center gap-4 overflow-x-auto pb-2 scrollbar-none no-scrollbar snap-x"
            >
              {initialPresetBrands.map((preset) => {
                const isSelected = selectedId === preset.id;
                return (
                  <div
                    key={preset.id}
                    onClick={() => setSelectedId(preset.id)}
                    className={`w-64 sm:w-72 flex-shrink-0 snap-start rounded-2xl overflow-hidden cursor-pointer border transition-all duration-200 bg-[#0B111E] flex flex-col justify-between ${
                      isSelected
                        ? "border-cyan-500 ring-2 ring-cyan-500/40 shadow-lg shadow-cyan-500/10"
                        : "border-[#1B2940] hover:border-cyan-500/40"
                    }`}
                  >
                    {/* Visual Card Canvas */}
                    <div
                      className={`h-36 w-full bg-gradient-to-tr ${preset.previewGradient} p-4 flex flex-col justify-between text-white relative overflow-hidden`}
                    >
                      {/* Top Header: Tag & Optional Preview Pill */}
                      <div className="flex items-center justify-between z-10">
                        <span className="text-[10px] font-mono uppercase tracking-widest text-white/80">
                          Preset
                        </span>

                        {preset.hasPreviewPill ? (
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              setPreviewModalBrand(preset);
                            }}
                            className="bg-black/60 hover:bg-black/80 backdrop-blur-md border border-white/10 text-white text-[10px] font-bold px-2.5 py-1 rounded-full flex items-center gap-1 shadow-sm transition-colors cursor-pointer"
                          >
                            <Eye size={10} />
                            <span>Preview</span>
                          </button>
                        ) : isSelected ? (
                          <div className="w-5 h-5 rounded-full bg-cyan-400 text-slate-950 flex items-center justify-center font-bold shadow-md">
                            <Check size={12} strokeWidth={3} />
                          </div>
                        ) : null}
                      </div>

                      {/* Center Graphic */}
                      <div className="z-10">
                        <div className="text-lg font-black tracking-tight text-white drop-shadow-sm">
                          {preset.name}
                        </div>
                        <div className="text-[10px] text-white/80 font-mono">
                          {preset.fontFamily.split(",")[0]}
                        </div>
                      </div>

                      {/* Palette Bar */}
                      <div className="flex items-center gap-1.5 z-10">
                        <div
                          className="w-4 h-4 rounded-md border border-white/40"
                          style={{ backgroundColor: preset.primaryColor }}
                        ></div>
                        <div
                          className="w-4 h-4 rounded-md border border-white/40"
                          style={{ backgroundColor: preset.accentColor }}
                        ></div>
                        <div
                          className="w-4 h-4 rounded-md border border-white/40"
                          style={{ backgroundColor: preset.secondaryColor }}
                        ></div>
                      </div>
                    </div>

                    {/* Footer Title */}
                    <div className="p-3 bg-[#0B111E] border-t border-[#1B2940] flex items-center justify-between">
                      <span className="text-xs font-bold text-white">
                        {preset.name}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* 3. Stable Modal Footer */}
        <div className="pt-4 border-t border-[#1B2940] flex items-center justify-between flex-shrink-0">
          {/* Left: Back */}
          <button
            type="button"
            onClick={onClose}
            className="text-slate-400 hover:text-white font-bold text-xs flex items-center gap-1.5 px-3 py-2 rounded-xl hover:bg-[#101827] transition-colors cursor-pointer"
          >
            <ArrowLeft size={14} />
            <span>Back</span>
          </button>

          {/* Right Group: + New Brand System and Continue */}
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setIsNewBrandModalOpen(true)}
              className="border border-[#1B2940] hover:border-cyan-500/40 bg-[#0B1220] hover:bg-[#101827] font-bold text-xs px-4 py-2.5 rounded-full shadow-sm flex items-center gap-1.5 text-slate-200 hover:text-white transition-all cursor-pointer"
            >
              <Plus size={13} />
              <span>New Brand System</span>
            </button>

            <button
              type="button"
              onClick={handleContinue}
              className="bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-bold text-xs px-7 py-2.5 rounded-full shadow-lg shadow-cyan-500/25 transition-all duration-200 cursor-pointer flex items-center gap-1.5 active:scale-95"
            >
              <span>Continue</span>
              <ArrowRight size={14} />
            </button>
          </div>
        </div>
      </div>

      {/* Popover/Modal: Create New Brand System */}
      {isNewBrandModalOpen && (
        <div
          onClick={(e) => e.stopPropagation()}
          className="fixed inset-0 z-60 bg-black/75 backdrop-blur-md flex items-center justify-center p-4 animate-in fade-in duration-150"
        >
          <div className="w-full max-w-sm bg-[#0A0F1A] rounded-3xl p-6 shadow-2xl border border-[#1B2940] text-slate-100 animate-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between mb-4">
              <h4 className="text-base font-bold text-white">
                Create New Brand System
              </h4>
              <button
                type="button"
                onClick={() => setIsNewBrandModalOpen(false)}
                className="text-slate-400 hover:text-white p-1 cursor-pointer"
              >
                <X size={16} />
              </button>
            </div>

            <div className="mb-5">
              <label className="text-xs font-semibold text-slate-400 block mb-1.5">
                Brand System Name
              </label>
              <input
                type="text"
                value={newBrandName}
                onChange={(e) => setNewBrandName(e.target.value)}
                placeholder="e.g. Acme Studio"
                autoFocus
                className="w-full bg-[#07090e] border border-[#1B2940] rounded-xl px-3 py-2 text-xs text-white placeholder:text-slate-500 outline-none focus:border-cyan-500 focus:ring-2 focus:ring-cyan-500/20"
              />
            </div>

            <div className="flex items-center justify-end gap-2">
              <button
                type="button"
                onClick={() => setIsNewBrandModalOpen(false)}
                className="px-3 py-1.5 rounded-xl text-xs font-semibold text-slate-400 hover:text-white hover:bg-[#101827] cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleCreateNewBrand}
                disabled={!newBrandName.trim()}
                className={`px-4 py-1.5 rounded-full text-xs font-bold transition-all ${
                  newBrandName.trim()
                    ? "bg-gradient-to-r from-cyan-500 to-blue-600 text-slate-950 cursor-pointer shadow-md"
                    : "bg-[#101827] text-slate-500 cursor-not-allowed border border-[#1B2940]"
                }`}
              >
                Create
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Popover/Modal: Preset Brand Preview */}
      {previewModalBrand && (
        <div
          onClick={(e) => {
            e.stopPropagation();
            setPreviewModalBrand(null);
          }}
          className="fixed inset-0 z-60 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in duration-150"
        >
          <div
            onClick={(e) => e.stopPropagation()}
            className="w-full max-w-md bg-[#0A0F1A] rounded-3xl p-6 shadow-2xl border border-[#1B2940] text-slate-100 animate-in zoom-in-95 duration-150"
          >
            <div className="flex items-center justify-between mb-4">
              <div>
                <h4 className="text-lg font-bold text-white">
                  {previewModalBrand.name}
                </h4>
                <p className="text-xs text-slate-400">Brand System Preview</p>
              </div>
              <button
                type="button"
                onClick={() => setPreviewModalBrand(null)}
                className="w-7 h-7 rounded-full hover:bg-[#101827] flex items-center justify-center text-slate-400 hover:text-white cursor-pointer"
              >
                <X size={16} />
              </button>
            </div>

            {/* Canvas Preview */}
            <div
              className={`h-48 w-full rounded-2xl bg-gradient-to-tr ${previewModalBrand.previewGradient} p-6 flex flex-col justify-between text-white shadow-inner mb-5 border border-white/10`}
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono uppercase tracking-wider text-white/80">
                  Typography & Tone
                </span>
                <div
                  className="w-4 h-4 rounded-full border border-white"
                  style={{ backgroundColor: previewModalBrand.accentColor }}
                ></div>
              </div>

              <div>
                <div className="text-2xl font-black">{previewModalBrand.name}</div>
                <div className="text-xs text-white/80 font-mono mt-1">
                  Primary: {previewModalBrand.fontFamily}
                </div>
              </div>

              <div className="flex items-center gap-2">
                <div
                  className="px-2.5 py-0.5 rounded text-[10px] font-bold bg-white/20 backdrop-blur-sm"
                >
                  Primary
                </div>
                <div
                  className="px-2.5 py-0.5 rounded text-[10px] font-bold bg-white/20 backdrop-blur-sm"
                >
                  Secondary
                </div>
                <div
                  className="px-2.5 py-0.5 rounded text-[10px] font-bold bg-white/20 backdrop-blur-sm"
                >
                  Accent
                </div>
              </div>
            </div>

            <div className="flex items-center justify-between">
              <button
                type="button"
                onClick={() => setPreviewModalBrand(null)}
                className="px-4 py-2 text-xs font-semibold text-slate-400 hover:text-white cursor-pointer"
              >
                Close
              </button>
              <button
                type="button"
                onClick={() => {
                  setSelectedId(previewModalBrand.id);
                  setPreviewModalBrand(null);
                }}
                className="bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 text-xs font-bold px-5 py-2 rounded-full cursor-pointer shadow-md transition-all"
              >
                Select this Preset
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
