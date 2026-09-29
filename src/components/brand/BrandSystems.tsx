"use client";

import React, { useState } from "react";
import {
  Plus,
  Heart,
  MoreHorizontal,
  Palette,
  X,
  BookOpen,
  Trash2,
  Copy,
  Share2,
  Check,
  Link2,
  Loader2,
  AlertCircle,
} from "lucide-react";
import AskRhysWidget from "../dashboard/AskRhysWidget";
import BrandGlossaryDetail, {
  GlossaryEntry,
  ForceTranslateRule,
  DontTranslateRule,
} from "./BrandGlossaryDetail";
import BrandKitEditor, { getNextCopyName } from "./BrandKitEditor";
import NewBrandSystem, { PresetBrandItem } from "./NewBrandSystem";
import BrandSystemPreview from "./BrandSystemPreview";

import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { useTheme } from "@/context/ThemeContext";

export interface BrandKitItem {
  id: string;
  name: string;
  isFavorite: boolean;
  logoUrl?: string;
  logoText: string;
  primaryColor: string;
  accentColor: string;
  secondaryColor: string;
  fontFamily: string;
  updatedAt: string;
}

export interface BrandGlossaryItem {
  id: string;
  name: string;
  badge?: string;
  creator?: string;
  entriesCount?: number;
  updatedAt?: string;
  pronunciations?: GlossaryEntry[];
  translations?: GlossaryEntry[];
  forceTranslateRules?: ForceTranslateRule[];
  dontTranslateRules?: DontTranslateRule[];
}

export function getNextGlossaryName(existingNames: string[]): string {
  if (!existingNames.includes("Brand Glossary")) {
    return "Brand Glossary";
  }
  let maxNum = 1;
  const regex = /^Brand Glossary(?:\s+(\d+))?$/i;
  for (const name of existingNames) {
    const match = name.match(regex);
    if (match) {
      const num = match[1] ? parseInt(match[1], 10) : 1;
      if (num > maxNum) maxNum = num;
    }
  }
  return `Brand Glossary ${maxNum + 1}`;
}

export interface AppliedBrandSystem {
  id: string;
  name: string;
  primaryColor?: string;
  accentColor?: string;
  secondaryColor?: string;
  fontFamily?: string;
  label?: string;
}

interface BrandSystemsProps {
  activeSubSection?: "brand_systems" | "brand_glossary";
  onOpenStudio?: () => void;
  onKitsChange?: (names: string[]) => void;
  onGlossariesChange?: (glossaries: BrandGlossaryItem[]) => void;
  onUseSystemInVideoAgent?: (brandSystem: AppliedBrandSystem) => void;
}

export default function BrandSystems({
  activeSubSection = "brand_systems",
  onOpenStudio,
  onKitsChange,
  onGlossariesChange,
  onUseSystemInVideoAgent,
}: BrandSystemsProps) {
  const { currentWorkspace } = useAuth();
  const { theme } = useTheme();
  const isLight = theme === "light";
  const [kits, setKits] = useState<BrandKitItem[]>([]);
  const [glossaries, setGlossaries] = useState<BrandGlossaryItem[]>([]);
  const [isLoadingKits, setIsLoadingKits] = useState(true);
  const [isLoadingGlossaries, setIsLoadingGlossaries] = useState(true);
  const [errorKits, setErrorKits] = useState<string | null>(null);
  const [errorGlossaries, setErrorGlossaries] = useState<string | null>(null);

  const [selectedGlossary, setSelectedGlossary] = useState<BrandGlossaryItem | null>(null);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isNewBrandSystemOpen, setIsNewBrandSystemOpen] = useState(false);
  const [previewingPreset, setPreviewingPreset] = useState<PresetBrandItem | null>(null);
  const [customizingPresetData, setCustomizingPresetData] = useState<PresetBrandItem | null>(null);
  const [isGlossaryDetailOpen, setIsGlossaryDetailOpen] = useState(false);
  const [isKitEditorOpen, setIsKitEditorOpen] = useState(false);
  const [selectedKitName, setSelectedKitName] = useState("");

  // Card Three-Dot Menu & Modal States for Brand Systems
  const [activeMenuKitId, setActiveMenuKitId] = useState<string | null>(null);
  const [shareModalKit, setShareModalKit] = useState<BrandKitItem | null>(null);
  const [deleteModalKit, setDeleteModalKit] = useState<BrandKitItem | null>(null);
  const [isCopied, setIsCopied] = useState(false);

  // Card Three-Dot Menu & Modal States for Brand Glossaries
  const [activeGlossaryMenuId, setActiveGlossaryMenuId] = useState<string | null>(null);
  const [deleteGlossaryModal, setDeleteGlossaryModal] = useState<BrandGlossaryItem | null>(null);

  const onKitsChangeRef = React.useRef(onKitsChange);
  React.useEffect(() => {
    onKitsChangeRef.current = onKitsChange;
  }, [onKitsChange]);

  const onGlossariesChangeRef = React.useRef(onGlossariesChange);
  React.useEffect(() => {
    onGlossariesChangeRef.current = onGlossariesChange;
  }, [onGlossariesChange]);

  const prevKitNamesKeyRef = React.useRef<string>("");
  const prevGlossariesKeyRef = React.useRef<string>("");

  const fetchKits = React.useCallback(async () => {
    setIsLoadingKits(true);
    setErrorKits(null);
    try {
      const data = await api.brandKits.list(currentWorkspace?.id);
      const mapped: BrandKitItem[] = data.map((k: any) => ({
        id: k.id,
        name: k.name,
        isFavorite: false,
        logoUrl: k.logo_asset_id,
        logoText: k.name.slice(0, 6),
        primaryColor: k.primary_color || k.colors?.primary || k.colors?.primary_color || "#000000",
        accentColor: k.accent_color || k.colors?.accent || k.colors?.accent_color || "#00d2ff",
        secondaryColor: k.secondary_color || k.colors?.secondary || k.colors?.secondary_color || "#7928ca",
        fontFamily: k.font_family || k.typography?.font_family || k.typography?.primary_font || "Inter, sans-serif",
        updatedAt: k.updated_at ? new Date(k.updated_at).toLocaleDateString() : "Recently",
      }));
      setKits(mapped);
      const names = mapped.map((m) => m.name);
      const namesKey = names.join("::");
      if (prevKitNamesKeyRef.current !== namesKey) {
        prevKitNamesKeyRef.current = namesKey;
        if (onKitsChangeRef.current) {
          onKitsChangeRef.current(names);
        }
      }
    } catch (err: any) {
      setErrorKits(err?.message || "Failed to load brand kits");
      setKits([]);
    } finally {
      setIsLoadingKits(false);
    }
  }, [currentWorkspace?.id]);

  const fetchGlossaries = React.useCallback(async () => {
    setIsLoadingGlossaries(true);
    setErrorGlossaries(null);
    try {
      const data = await api.brandGlossaries.list(currentWorkspace?.id);
      const mapped: BrandGlossaryItem[] = data.map((g: any) => ({
        id: g.id,
        name: g.name,
        badge: "Glossary",
        creator: g.language ? `Lang: ${g.language}` : "Workspace Glossary",
        entriesCount: 0,
        updatedAt: g.updated_at ? new Date(g.updated_at).toLocaleDateString() : "Recently",
        pronunciations: [],
        translations: [],
        forceTranslateRules: [],
        dontTranslateRules: [],
      }));
      setGlossaries(mapped);
      const glossariesKey = mapped.map((g) => `${g.id}:${g.name}`).join("::");
      if (prevGlossariesKeyRef.current !== glossariesKey) {
        prevGlossariesKeyRef.current = glossariesKey;
        if (onGlossariesChangeRef.current) {
          onGlossariesChangeRef.current(mapped);
        }
      }
    } catch (err: any) {
      setErrorGlossaries(err?.message || "Failed to load glossaries");
      setGlossaries([]);
    } finally {
      setIsLoadingGlossaries(false);
    }
  }, [currentWorkspace?.id]);

  React.useEffect(() => {
    fetchKits();
    fetchGlossaries();
  }, [fetchKits, fetchGlossaries]);

  // Global click listener to close card dropdown menus when clicking outside
  React.useEffect(() => {
    const handleDocumentClick = () => {
      setActiveMenuKitId(null);
      setActiveGlossaryMenuId(null);
    };
    window.addEventListener("click", handleDocumentClick);
    return () => window.removeEventListener("click", handleDocumentClick);
  }, []);

  const handleDuplicateKit = async (kitToDuplicate: BrandKitItem) => {
    try {
      const newName = getNextCopyName(kitToDuplicate.name, kits.map((k) => k.name));
      await api.brandKits.create(
        {
          name: newName,
          primary_color: kitToDuplicate.primaryColor,
          accent_color: kitToDuplicate.accentColor,
          secondary_color: kitToDuplicate.secondaryColor,
          font_family: kitToDuplicate.fontFamily,
        },
        currentWorkspace?.id
      );
      await fetchKits();
      setActiveMenuKitId(null);
    } catch (err: any) {
      alert(err?.message || "Failed to duplicate brand kit");
    }
  };

  const handleCreateNewBrandGlossary = async () => {
    try {
      const nextName = getNextGlossaryName(glossaries.map((g) => g.name));
      const created = await api.brandGlossaries.create(
        { name: nextName, description: "Workspace Glossary" },
        currentWorkspace?.id
      );
      await fetchGlossaries();
      const newGlossaryItem: BrandGlossaryItem = {
        id: created.id,
        name: created.name,
        badge: "New",
        creator: "Workspace Glossary",
        entriesCount: 0,
        updatedAt: "Just now",
        pronunciations: [],
        translations: [],
        forceTranslateRules: [],
        dontTranslateRules: [],
      };
      setSelectedGlossary(newGlossaryItem);
      setIsGlossaryDetailOpen(true);
      if (typeof window !== "undefined") {
        window.history.pushState(
          { glossaryDetail: true, glossaryId: created.id, glossaryName: created.name, view: "brand" },
          ""
        );
      }
    } catch (err: any) {
      alert(err?.message || "Failed to create brand glossary");
    }
  };

  const handleDuplicateGlossary = async (glossaryToDuplicate: BrandGlossaryItem) => {
    try {
      const newName = getNextCopyName(glossaryToDuplicate.name, glossaries.map((g) => g.name));
      await api.brandGlossaries.create(
        { name: newName, description: "Workspace Glossary" },
        currentWorkspace?.id
      );
      await fetchGlossaries();
      setActiveGlossaryMenuId(null);
    } catch (err: any) {
      alert(err?.message || "Failed to duplicate brand glossary");
    }
  };

  // New Brand Kit Form State
  const [newKitName, setNewKitName] = useState("");
  const [newPrimaryColor, setNewPrimaryColor] = useState("#000000");
  const [newAccentColor, setNewAccentColor] = useState("#00d2ff");
  const [newSecondaryColor, setNewSecondaryColor] = useState("#7928ca");
  const [newFont, setNewFont] = useState("Inter");

  // Browser back/forward navigation support for Brand System pages
  React.useEffect(() => {
    const handlePopState = (e: PopStateEvent) => {
      if (e.state?.manualPronunciation) {
        return;
      }
      if (e.state?.glossaryDetail) {
        setIsGlossaryDetailOpen(true);
        return;
      }
      if (isGlossaryDetailOpen) {
        setIsGlossaryDetailOpen(false);
      } else if (isKitEditorOpen) {
        setIsKitEditorOpen(false);
      } else if (previewingPreset) {
        setPreviewingPreset(null);
      } else if (isNewBrandSystemOpen) {
        setIsNewBrandSystemOpen(false);
      }
    };
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, [isGlossaryDetailOpen, isKitEditorOpen, previewingPreset, isNewBrandSystemOpen]);

  const handleOpenNewBrandSystem = () => {
    setIsNewBrandSystemOpen(true);
    if (typeof window !== "undefined") {
      window.history.pushState({ newBrandSystem: true, view: "brand" }, "");
    }
  };

  const handleCloseNewBrandSystem = () => {
    setIsNewBrandSystemOpen(false);
  };

  if (isGlossaryDetailOpen && activeSubSection === "brand_glossary") {
    return (
      <BrandGlossaryDetail
        glossaryId={selectedGlossary?.id}
        glossaryName={selectedGlossary?.name || "Brand Glossary"}
        initialPronunciations={selectedGlossary?.pronunciations || []}
        initialForceRules={selectedGlossary?.forceTranslateRules || []}
        initialDontTranslateRules={selectedGlossary?.dontTranslateRules || []}
        onUpdatePronunciations={(newPron) => {
          if (!selectedGlossary) return;
          const updatedGlossary: BrandGlossaryItem = {
            ...selectedGlossary,
            pronunciations: newPron,
            entriesCount:
              newPron.length +
              (selectedGlossary.forceTranslateRules?.length || 0) +
              (selectedGlossary.dontTranslateRules?.length || 0),
            updatedAt: "Just now",
          };
          setSelectedGlossary(updatedGlossary);
          const updatedList = glossaries.map((g) =>
            g.id === updatedGlossary.id ? updatedGlossary : g
          );
          setGlossaries(updatedList);
        }}
        onUpdateForceRules={(newForce) => {
          if (!selectedGlossary) return;
          const updatedGlossary: BrandGlossaryItem = {
            ...selectedGlossary,
            forceTranslateRules: newForce,
            entriesCount:
              (selectedGlossary.pronunciations?.length || 0) +
              newForce.length +
              (selectedGlossary.dontTranslateRules?.length || 0),
            updatedAt: "Just now",
          };
          setSelectedGlossary(updatedGlossary);
          const updatedList = glossaries.map((g) =>
            g.id === updatedGlossary.id ? updatedGlossary : g
          );
          setGlossaries(updatedList);
        }}
        onUpdateDontTranslateRules={(newDont) => {
          if (!selectedGlossary) return;
          const updatedGlossary: BrandGlossaryItem = {
            ...selectedGlossary,
            dontTranslateRules: newDont,
            entriesCount:
              (selectedGlossary.pronunciations?.length || 0) +
              (selectedGlossary.forceTranslateRules?.length || 0) +
              newDont.length,
            updatedAt: "Just now",
          };
          setSelectedGlossary(updatedGlossary);
          const updatedList = glossaries.map((g) =>
            g.id === updatedGlossary.id ? updatedGlossary : g
          );
          setGlossaries(updatedList);
        }}
        onBack={() => setIsGlossaryDetailOpen(false)}
        onOpenStudio={onOpenStudio}
      />
    );
  }

  if (isKitEditorOpen && activeSubSection === "brand_systems") {
    const currentEditingKit = kits.find((k) => k.name === selectedKitName);
    return (
      <BrandKitEditor
        initialTitle={selectedKitName}
        initialPrimaryColor={currentEditingKit?.primaryColor || customizingPresetData?.primaryColor}
        initialAccentColor={currentEditingKit?.accentColor || customizingPresetData?.accentColor}
        initialSecondaryColor={currentEditingKit?.secondaryColor || customizingPresetData?.secondaryColor}
        initialFontFamily={currentEditingKit?.fontFamily || customizingPresetData?.fontFamily}
        initialLogoAssetId={currentEditingKit?.logoUrl}
        existingKitNames={kits.map((k) => k.name)}
        onBack={() => {
          setIsKitEditorOpen(false);
        }}
        onUseSystem={(system) => {
          if (onUseSystemInVideoAgent) {
            onUseSystemInVideoAgent({
              id: kits.find((k) => k.name === system.name)?.id || "brand_kit_preset",
              name: system.name,
              primaryColor: system.primaryColor,
              accentColor: system.accentColor,
              secondaryColor: system.secondaryColor,
              fontFamily: system.fontFamily,
            });
          } else if (onOpenStudio) {
            onOpenStudio();
          }
        }}
        onSave={async (savedKit) => {
          try {
            const existingKit = kits.find((k) => k.name === savedKit.name);
            if (existingKit) {
              await api.brandKits.update(
                existingKit.id,
                {
                  name: savedKit.name,
                  primary_color: savedKit.primaryColor,
                  accent_color: savedKit.accentColor,
                  secondary_color: savedKit.secondaryColor,
                  font_family: savedKit.fontFamily,
                  logo_asset_id: savedKit.logoAssetId || undefined,
                },
                currentWorkspace?.id
              );
            } else {
              await api.brandKits.create(
                {
                  name: savedKit.name,
                  primary_color: savedKit.primaryColor,
                  accent_color: savedKit.accentColor,
                  secondary_color: savedKit.secondaryColor,
                  font_family: savedKit.fontFamily,
                  logo_asset_id: savedKit.logoAssetId || undefined,
                },
                currentWorkspace?.id
              );
            }
            await fetchKits();
            setIsKitEditorOpen(false);
            setCustomizingPresetData(null);
            setPreviewingPreset(null);
            setIsNewBrandSystemOpen(false);
          } catch (err: any) {
            alert(err?.message || "Failed to save brand kit");
          }
        }}
        onOpenStudio={onOpenStudio}
      />
    );
  }

  if (previewingPreset && activeSubSection === "brand_systems") {
    return (
      <BrandSystemPreview
        initialPreset={previewingPreset}
        onBack={() => {
          setPreviewingPreset(null);
        }}
        onCustomize={(preset) => {
          setCustomizingPresetData(preset);
          setSelectedKitName(preset.name);
          setIsKitEditorOpen(true);
          if (typeof window !== "undefined") {
            window.history.pushState({ kitEditor: true, presetId: preset.id }, "");
          }
        }}
        onUseSystem={(preset) => {
          setCustomizingPresetData(preset);
          setSelectedKitName(preset.name);
          setIsKitEditorOpen(true);
          if (typeof window !== "undefined") {
            window.history.pushState({ kitEditor: true, presetId: preset.id }, "");
          }
        }}
        onMakeCopy={(preset) => {
          const nextCopyTitle = getNextCopyName(preset.name, kits.map((k) => k.name));
          setCustomizingPresetData(preset);
          setSelectedKitName(nextCopyTitle);
          setIsKitEditorOpen(true);
          if (typeof window !== "undefined") {
            window.history.pushState({ kitEditor: true, presetId: preset.id, copyTitle: nextCopyTitle }, "");
          }
        }}
        onSaveBrandSystem={async (newKit) => {
          try {
            await api.brandKits.create(
              {
                name: newKit.name,
                primary_color: newKit.primaryColor,
                accent_color: newKit.accentColor,
                secondary_color: newKit.secondaryColor,
                font_family: newKit.fontFamily,
              },
              currentWorkspace?.id
            );
            await fetchKits();
            setPreviewingPreset(null);
            setIsNewBrandSystemOpen(false);
          } catch (err: any) {
            alert(err?.message || "Failed to save brand system");
          }
        }}
        onOpenStudio={onOpenStudio}
      />
    );
  }

  if (isNewBrandSystemOpen && activeSubSection === "brand_systems") {
    return (
      <NewBrandSystem
        onBack={handleCloseNewBrandSystem}
        onSelectPreset={(preset) => {
          setPreviewingPreset(preset);
          if (typeof window !== "undefined") {
            window.history.pushState({ previewPreset: preset.id }, "");
          }
        }}
        onCreateBrand={async (newKit) => {
          try {
            await api.brandKits.create(
              {
                name: newKit.name,
                primary_color: newKit.primaryColor,
                accent_color: newKit.accentColor,
                secondary_color: newKit.secondaryColor,
                font_family: newKit.fontFamily,
              },
              currentWorkspace?.id
            );
            await fetchKits();
            setIsNewBrandSystemOpen(false);
          } catch (err: any) {
            alert(err?.message || "Failed to create brand system");
          }
        }}
        onOpenStudio={onOpenStudio}
      />
    );
  }

  const handleToggleFavorite = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setKits((prev) =>
      prev.map((k) => (k.id === id ? { ...k, isFavorite: !k.isFavorite } : k))
    );
  };

  const handleCreateKit = async () => {
    if (!newKitName.trim()) return;
    try {
      await api.brandKits.create(
        {
          name: newKitName.trim(),
          primary_color: newPrimaryColor,
          accent_color: newAccentColor,
          secondary_color: newSecondaryColor,
          font_family: newFont,
        },
        currentWorkspace?.id
      );
      await fetchKits();
      setNewKitName("");
      setIsCreateModalOpen(false);
    } catch (err: any) {
      alert(err?.message || "Failed to create brand kit");
    }
  };

  return (
    <div className={`flex-1 h-screen overflow-y-auto ${isLight ? "bg-slate-50 text-slate-900" : "bg-[#07090e] text-slate-100"} flex flex-col font-sans select-none`}>
      {/* Top Header Section (Matches Reference Screenshot) */}
      <div className={`w-full px-8 sm:px-10 pt-8 pb-5 flex items-center justify-between border-b ${isLight ? "border-slate-200 bg-white" : "border-[#1b2940] bg-[#07090e]"} z-20`}>
        <div>
          <h1 className={`text-2xl sm:text-3xl font-extrabold ${isLight ? "text-slate-900" : "text-white"} tracking-tight`}>
            {activeSubSection === "brand_systems" ? "Brand Systems" : "Brand Glossary"}
          </h1>
          {activeSubSection === "brand_systems" && (
            <p className={`text-xs ${isLight ? "text-slate-600" : "text-slate-400"} mt-1 leading-relaxed`}>
              Brand systems keep every video consistent without restyling elements one by one.
            </p>
          )}
        </div>

        <div className="flex items-center gap-3">
          {activeSubSection === "brand_glossary" && (
            <button
              type="button"
              onClick={handleCreateNewBrandGlossary}
              className={`flex items-center gap-2 px-4 py-2 ${isLight ? "bg-slate-900 hover:bg-slate-800 text-white" : "bg-white hover:bg-slate-200 text-slate-950"} text-xs font-semibold rounded-full shadow-xs transition-all cursor-pointer hover:scale-[1.02]`}
            >
              <Plus size={14} className="stroke-[2.5]" />
              <span>New Brand Glossary</span>
            </button>
          )}

          <AskRhysWidget variant="banner" />
        </div>
      </div>

      {/* Main Workspace Area */}
      {activeSubSection === "brand_systems" ? (
        <div className="max-w-6xl w-full mx-auto px-8 sm:px-10 py-8 flex-1">
          {/* Brand Kits Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {/* Card 1: + Add new */}
            <div
              onClick={handleOpenNewBrandSystem}
              className={`aspect-[16/11] ${
                isLight
                  ? "bg-white/90 border-2 border-dashed border-slate-300 hover:border-blue-500 hover:bg-white shadow-xs"
                  : "bg-[#0b111e]/60 border-2 border-dashed border-[#1b2940] hover:border-cyan-500/60 hover:bg-[#0f172a]/80"
              } rounded-3xl flex items-center justify-center cursor-pointer group transition-all duration-300 hover:shadow-lg`}
            >
              <button
                type="button"
                className={`flex items-center gap-2 px-5 py-2.5 ${
                  isLight
                    ? "bg-slate-100 border border-slate-300 text-slate-700 group-hover:border-blue-500 group-hover:text-blue-600"
                    : "bg-[#0f172a] border border-[#1b2940] text-slate-200 group-hover:border-cyan-500 group-hover:text-cyan-400"
                } rounded-full text-xs font-semibold shadow-xs group-hover:scale-105 transition-all pointer-events-none`}
              >
                <Plus size={15} className={isLight ? "text-slate-500 group-hover:text-blue-600" : "text-slate-400 group-hover:text-cyan-400"} />
                <span>Add new</span>
              </button>
            </div>

            {isLoadingKits && (
              <div className="flex items-center justify-center py-20 col-span-full">
                <Loader2 className="w-8 h-8 text-cyan-400 animate-spin" />
              </div>
            )}

            {errorKits && (
              <div className="flex flex-col items-center justify-center py-12 text-center col-span-full">
                <AlertCircle className="w-8 h-8 text-rose-400 mb-2" />
                <p className="text-xs text-rose-400">{errorKits}</p>
                <button onClick={fetchKits} className="mt-2 text-xs text-cyan-400 underline cursor-pointer">Retry</button>
              </div>
            )}

            {!isLoadingKits && !errorKits && kits.length === 0 && (
              <div className={`col-span-full md:col-span-1 lg:col-span-2 flex flex-col justify-center p-6 border border-dashed ${isLight ? "border-slate-300 bg-white" : "border-[#1b2940] bg-[#0b111e]/40"} rounded-3xl`}>
                <div className="flex items-center gap-3 mb-2">
                  <div className="w-8 h-8 rounded-full bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
                    <Palette size={16} />
                  </div>
                  <h3 className={`text-sm font-bold ${isLight ? "text-slate-900" : "text-slate-200"}`}>No brand systems yet.</h3>
                </div>
                <p className={`text-xs ${isLight ? "text-slate-600" : "text-slate-400"} leading-relaxed`}>
                  Click <strong className={isLight ? "text-blue-600 font-semibold" : "text-cyan-400 font-semibold"}>&quot;Add new&quot;</strong> to configure your logo, custom color palettes, and fonts for all generated and translated videos.
                </p>
              </div>
            )}

            {/* Brand Kit Cards (Card 2: Demo HeyGen Brand Kit Copy, Card 3: Demo HeyGen Brand Kit, plus dynamically created) */}
            {kits.map((kit) => (
              <div key={kit.id} className="flex flex-col group">
                {/* Visual Card Frame */}
                <div
                  onClick={() => {
                    setSelectedKitName(kit.name);
                    setCustomizingPresetData(null);
                    setIsKitEditorOpen(true);
                  }}
                  className={`aspect-[16/11] ${
                    isLight
                      ? "bg-white border border-slate-200 hover:border-blue-500/60 shadow-md hover:shadow-xl"
                      : "bg-[#0b111e] border border-[#1b2940] hover:border-cyan-500/40 shadow-xl hover:shadow-2xl"
                  } rounded-3xl overflow-hidden transition-all duration-300 relative flex flex-col justify-between cursor-pointer p-6`}
                >
                  {/* Top Right Action Icons: Heart & More */}
                  <div className="flex items-center justify-end gap-2 z-10 relative">
                    <button
                      type="button"
                      onClick={(e) => handleToggleFavorite(kit.id, e)}
                      className={`w-8 h-8 rounded-full flex items-center justify-center transition-all shadow-xs cursor-pointer ${
                        kit.isFavorite
                          ? "bg-rose-500/20 border border-rose-500/40 text-rose-500 hover:bg-rose-500/30"
                          : isLight
                          ? "bg-slate-100 border border-slate-200 hover:border-slate-300 text-slate-600 hover:text-slate-900"
                          : "bg-[#0f172a] border border-[#1b2940] hover:border-slate-500 text-slate-400 hover:text-slate-200"
                      }`}
                      title={kit.isFavorite ? "Remove favorite" : "Favorite"}
                    >
                      <Heart
                        size={14}
                        className={kit.isFavorite ? "fill-rose-500 text-rose-500" : (isLight ? "text-slate-500" : "text-slate-400")}
                      />
                    </button>

                    <div className="relative">
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          setActiveMenuKitId(activeMenuKitId === kit.id ? null : kit.id);
                        }}
                        className={`w-8 h-8 rounded-full ${
                          isLight
                            ? "bg-slate-100 border border-slate-200 hover:border-slate-300 text-slate-600 hover:text-slate-900"
                            : "bg-[#0f172a] border border-[#1b2940] hover:border-slate-500 text-slate-400 hover:text-slate-200"
                        } flex items-center justify-center shadow-xs transition-colors cursor-pointer ${
                          activeMenuKitId === kit.id
                            ? isLight
                              ? "border-blue-500 bg-blue-50 text-blue-600 ring-2 ring-blue-500/20"
                              : "border-cyan-500/60 bg-[#162035] text-white ring-2 ring-cyan-500/20"
                            : ""
                        }`}
                        title="More options"
                      >
                        <MoreHorizontal size={15} />
                      </button>

                      {/* Three-Dot Dropdown Menu (Matches Reference Screenshot) */}
                      {activeMenuKitId === kit.id && (
                        <div
                          onClick={(e) => e.stopPropagation()}
                          className={`absolute right-0 top-10 w-44 ${
                            isLight
                              ? "bg-white border-slate-200 text-slate-800 shadow-2xl"
                              : "bg-[#0b111e] border-[#1b2940] text-slate-300 shadow-2xl"
                          } rounded-2xl border py-1.5 z-40 animate-in fade-in zoom-in-95 duration-100 font-sans`}
                        >
                          {/* Header: Created by Riya */}
                          <div className={`px-3.5 py-1.5 border-b ${isLight ? "border-slate-100 text-slate-600" : "border-[#1b2940] text-slate-400"} flex items-center gap-2`}>
                            <div className="w-5 h-5 rounded-full bg-gradient-to-tr from-purple-500 to-indigo-500 text-[10px] font-bold text-white flex items-center justify-center shrink-0">
                              R
                            </div>
                            <span className="text-[11px] font-semibold truncate">
                              Created by Riya
                            </span>
                          </div>

                          {/* Menu Actions */}
                          <div className="py-1">
                            {/* Duplicate */}
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleDuplicateKit(kit);
                              }}
                              className={`w-full flex items-center gap-2.5 px-3.5 py-2 text-xs font-medium ${isLight ? "text-slate-700 hover:bg-slate-100 hover:text-slate-900" : "text-slate-300 hover:bg-[#162035] hover:text-white"} transition-colors text-left cursor-pointer`}
                            >
                              <Copy size={13} className={isLight ? "text-slate-500" : "text-slate-400"} />
                              <span>Duplicate</span>
                            </button>

                            {/* Share 💎 */}
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                setActiveMenuKitId(null);
                                setShareModalKit(kit);
                              }}
                              className={`w-full flex items-center justify-between px-3.5 py-2 text-xs font-medium ${isLight ? "text-slate-700 hover:bg-slate-100 hover:text-slate-900" : "text-slate-300 hover:bg-[#162035] hover:text-white"} transition-colors text-left cursor-pointer`}
                            >
                              <div className="flex items-center gap-2.5">
                                <Share2 size={13} className={isLight ? "text-slate-500" : "text-slate-400"} />
                                <span>Share</span>
                              </div>
                              <span className="text-xs">💎</span>
                            </button>

                            <div className={`h-px ${isLight ? "bg-slate-200" : "bg-[#1b2940]"} my-1`}></div>

                            {/* Delete */}
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                setActiveMenuKitId(null);
                                setDeleteModalKit(kit);
                              }}
                              className="w-full flex items-center gap-2.5 px-3.5 py-2 text-xs font-medium text-rose-500 hover:bg-rose-500/10 hover:text-rose-600 transition-colors text-left cursor-pointer"
                            >
                              <Trash2 size={13} className="text-rose-500" />
                              <span>Delete</span>
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Centered Brand Logo & Visual Emblem */}
                  <div className="flex items-center justify-center gap-3 my-auto">
                    <div className={`text-left font-black tracking-tighter text-3xl md:text-4xl ${isLight ? "text-slate-900" : "text-white"} leading-none`}>
                      <div>Hey</div>
                      <div>Gen</div>
                    </div>

                    {/* Prism Logo Symbol */}
                    <div className="w-14 h-14 relative flex items-center justify-center">
                      <div className="w-12 h-12 bg-gradient-to-tr from-cyan-400 via-fuchsia-400 to-emerald-400 rounded-2xl shadow-md transform rotate-12 group-hover:rotate-45 transition-transform duration-500"></div>
                    </div>
                  </div>

                  {/* Bottom Color Swatches Bar (Three-color bar matching reference) */}
                  <div className={`w-full h-4 rounded-full overflow-hidden flex shadow-inner border ${isLight ? "border-slate-300" : "border-white/10"}`}>
                    <div className="flex-1" style={{ backgroundColor: kit.primaryColor || "#000000" }}></div>
                    <div className="flex-1" style={{ backgroundColor: kit.accentColor || "#00d2ff" }}></div>
                    <div className="w-12" style={{ backgroundColor: kit.secondaryColor || "#7928ca" }}></div>
                  </div>
                </div>

                {/* Kit Name Below Card */}
                <span className={`text-xs sm:text-sm font-semibold ${isLight ? "text-slate-800" : "text-slate-200"} mt-2.5 px-1`}>
                  {kit.name}
                </span>
              </div>
            ))}
          </div>
        </div>
      ) : (
        /* BRAND GLOSSARY OVERVIEW WORKSPACE (Matches Reference Screenshot) */
        <div className="max-w-2xl w-full px-8 sm:px-10 py-8 flex-1">
          <div className="flex flex-col gap-3.5">
            {isLoadingGlossaries && (
              <div className="flex items-center justify-center py-20">
                <Loader2 className="w-8 h-8 text-cyan-400 animate-spin" />
              </div>
            )}
            {errorGlossaries && (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <AlertCircle className="w-8 h-8 text-rose-400 mb-2" />
                <p className="text-xs text-rose-400">{errorGlossaries}</p>
                <button onClick={fetchGlossaries} className="mt-2 text-xs text-cyan-400 underline cursor-pointer">Retry</button>
              </div>
            )}
            {!isLoadingGlossaries && !errorGlossaries && glossaries.length === 0 && (
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <div className={`w-14 h-14 rounded-2xl ${isLight ? "bg-slate-100 border-slate-200 text-slate-500" : "bg-slate-900 border-slate-800 text-slate-500"} border flex items-center justify-center mb-3`}>
                  <BookOpen size={28} />
                </div>
                <h3 className={`text-sm font-bold ${isLight ? "text-slate-900" : "text-slate-300"}`}>No Brand Glossaries</h3>
                <p className={`text-xs ${isLight ? "text-slate-500" : "text-slate-500"} mt-1 max-w-sm`}>Create a glossary to customize pronunciation and translation rules.</p>
              </div>
            )}
            {glossaries.map((glossary) => (
              <div
                key={glossary.id}
                onClick={() => {
                  setSelectedGlossary(glossary);
                  setIsGlossaryDetailOpen(true);
                  if (typeof window !== "undefined") {
                    window.history.pushState(
                      { glossaryDetail: true, glossaryId: glossary.id, glossaryName: glossary.name, view: "brand" },
                      ""
                    );
                  }
                }}
                className={`w-full ${
                  isLight
                    ? "bg-white hover:bg-slate-50 border-slate-200 hover:border-blue-400 shadow-sm hover:shadow-md"
                    : "bg-[#0b111e] hover:bg-[#101726] border-[#1b2940] hover:border-cyan-500/40 shadow-lg hover:shadow-2xl"
                } border rounded-3xl p-5 sm:p-6 transition-all duration-200 cursor-pointer group relative`}
              >
                <div className="flex flex-col gap-3">
                  {/* Top Row: Badge on Left, Three-dot Action on Right */}
                  <div className="flex items-center justify-between">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-bold ${
                      isLight
                        ? "bg-blue-50 text-blue-600 border border-blue-200"
                        : "bg-cyan-500/15 text-cyan-400 border border-cyan-500/30"
                    } tracking-wide`}>
                      {glossary.badge || "New"}
                    </span>

                    <div className="relative">
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          setActiveGlossaryMenuId(
                            activeGlossaryMenuId === glossary.id ? null : glossary.id
                          );
                        }}
                        className={`w-7 h-7 rounded-full ${
                          isLight
                            ? "bg-slate-100 border border-slate-200 hover:border-slate-300 text-slate-600 hover:text-slate-900"
                            : "bg-[#0f172a] border border-[#1b2940] hover:border-slate-500 text-slate-400 hover:text-slate-200"
                        } flex items-center justify-center shadow-2xs transition-colors cursor-pointer ${
                          activeGlossaryMenuId === glossary.id
                            ? isLight
                              ? "border-blue-500 bg-blue-50 text-blue-600 ring-2 ring-blue-500/20"
                              : "border-cyan-500/60 bg-[#162035] text-white ring-2 ring-cyan-500/20"
                            : ""
                        }`}
                        title="More options"
                      >
                        <MoreHorizontal size={14} />
                      </button>

                      {/* Three-Dot Dropdown Menu (Contains EXACTLY Duplicate and Delete) */}
                      {activeGlossaryMenuId === glossary.id && (
                        <div
                          onClick={(e) => e.stopPropagation()}
                          className={`absolute right-0 top-9 w-36 ${
                            isLight
                              ? "bg-white border-slate-200 text-slate-800 shadow-2xl"
                              : "bg-[#0b111e] border-[#1b2940] text-slate-300 shadow-2xl"
                          } rounded-2xl border py-1.5 z-30 animate-in fade-in zoom-in-95 duration-100 font-sans`}
                        >
                          {/* Duplicate */}
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDuplicateGlossary(glossary);
                            }}
                            className={`w-full flex items-center gap-2.5 px-3.5 py-2 text-xs font-medium ${isLight ? "text-slate-700 hover:bg-slate-100 hover:text-slate-900" : "text-slate-300 hover:bg-[#162035] hover:text-white"} transition-colors text-left cursor-pointer`}
                          >
                            <Copy size={13} className={isLight ? "text-slate-500" : "text-slate-400"} />
                            <span>Duplicate</span>
                          </button>

                          <div className={`h-px ${isLight ? "bg-slate-200" : "bg-[#1b2940]"} my-1`}></div>

                          {/* Delete */}
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              setActiveGlossaryMenuId(null);
                              setDeleteGlossaryModal(glossary);
                            }}
                            className="w-full flex items-center gap-2.5 px-3.5 py-2 text-xs font-medium text-rose-500 hover:bg-rose-500/10 hover:text-rose-600 transition-colors text-left cursor-pointer"
                          >
                            <Trash2 size={13} className="text-rose-500" />
                            <span>Delete</span>
                          </button>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Row: Name + Creator on Left, Entries Count Badge on Right */}
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className={`text-base font-bold ${isLight ? "text-slate-900 group-hover:text-blue-600" : "text-white group-hover:text-cyan-400"} transition-colors`}>
                        {glossary.name}
                      </h3>
                      <p className={`text-xs ${isLight ? "text-slate-500" : "text-slate-400"} font-normal mt-0.5`}>
                        {glossary.creator || "By ritap6778@gmail.com"}
                      </p>
                    </div>

                    <div className={`px-3.5 py-1 ${isLight ? "bg-slate-100 border-slate-200 text-slate-700" : "bg-[#07090e] border-[#1b2940] text-slate-300"} border rounded-full text-xs font-semibold shadow-2xs`}>
                      {glossary.entriesCount ?? 0} Entries
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* CREATE BRAND SYSTEM MODAL */}
      {isCreateModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-200">
          <div className={`w-full max-w-lg ${isLight ? "bg-white text-slate-900 border-slate-200" : "bg-[#0b111e] text-slate-100 border-[#1b2940]"} rounded-3xl p-6 shadow-2xl border`}>
            <div className={`flex items-center justify-between pb-3 border-b ${isLight ? "border-slate-200" : "border-[#1b2940]"} mb-4`}>
              <h3 className={`text-base font-bold flex items-center gap-2 ${isLight ? "text-slate-900" : "text-white"}`}>
                <Palette size={16} className={isLight ? "text-blue-600" : "text-cyan-400"} />
                <span>Create New Brand System</span>
              </h3>
              <button
                type="button"
                onClick={() => setIsCreateModalOpen(false)}
                className={`p-1 rounded-lg ${isLight ? "text-slate-400 hover:text-slate-700 hover:bg-slate-100" : "text-slate-400 hover:text-white hover:bg-[#152033]"} cursor-pointer`}
              >
                <X size={18} />
              </button>
            </div>

            {/* Form Fields */}
            <div className="space-y-4">
              <div>
                <label className={`text-xs font-semibold ${isLight ? "text-slate-700" : "text-slate-300"} block mb-1`}>
                  Brand Name
                </label>
                <input
                  type="text"
                  value={newKitName}
                  onChange={(e) => setNewKitName(e.target.value)}
                  placeholder="e.g. Acme Studio Media"
                  autoFocus
                  className={`w-full ${
                    isLight
                      ? "bg-slate-50 border-slate-200 text-slate-900 placeholder:text-slate-400 focus:bg-white focus:border-blue-500"
                      : "bg-[#07090e] border-[#1b2940] text-white placeholder:text-slate-500 focus:bg-[#090d16] focus:border-cyan-500"
                  } border rounded-xl px-3.5 py-2 text-xs focus:outline-none`}
                />
              </div>

              {/* Color Palette Selectors */}
              <div>
                <label className={`text-xs font-semibold ${isLight ? "text-slate-700" : "text-slate-300"} block mb-1.5`}>
                  Brand Color Palette
                </label>
                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <span className={`text-[10px] ${isLight ? "text-slate-500" : "text-slate-400"} block mb-1`}>Primary</span>
                    <div className={`flex items-center gap-2 ${isLight ? "bg-slate-50 border-slate-200 text-slate-800" : "bg-[#07090e] border-[#1b2940] text-slate-300"} border p-1.5 rounded-xl`}>
                      <input
                        type="color"
                        value={newPrimaryColor}
                        onChange={(e) => setNewPrimaryColor(e.target.value)}
                        className="w-6 h-6 rounded cursor-pointer border-0 bg-transparent"
                      />
                      <span className="text-[11px] font-mono truncate">
                        {newPrimaryColor}
                      </span>
                    </div>
                  </div>

                  <div>
                    <span className={`text-[10px] ${isLight ? "text-slate-500" : "text-slate-400"} block mb-1`}>Accent</span>
                    <div className={`flex items-center gap-2 ${isLight ? "bg-slate-50 border-slate-200 text-slate-800" : "bg-[#07090e] border-[#1b2940] text-slate-300"} border p-1.5 rounded-xl`}>
                      <input
                        type="color"
                        value={newAccentColor}
                        onChange={(e) => setNewAccentColor(e.target.value)}
                        className="w-6 h-6 rounded cursor-pointer border-0 bg-transparent"
                      />
                      <span className="text-[11px] font-mono truncate">
                        {newAccentColor}
                      </span>
                    </div>
                  </div>

                  <div>
                    <span className={`text-[10px] ${isLight ? "text-slate-500" : "text-slate-400"} block mb-1`}>Secondary</span>
                    <div className={`flex items-center gap-2 ${isLight ? "bg-slate-50 border-slate-200 text-slate-800" : "bg-[#07090e] border-[#1b2940] text-slate-300"} border p-1.5 rounded-xl`}>
                      <input
                        type="color"
                        value={newSecondaryColor}
                        onChange={(e) => setNewSecondaryColor(e.target.value)}
                        className="w-6 h-6 rounded cursor-pointer border-0 bg-transparent"
                      />
                      <span className="text-[11px] font-mono truncate">
                        {newSecondaryColor}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Font Family */}
              <div>
                <label className={`text-xs font-semibold ${isLight ? "text-slate-700" : "text-slate-300"} block mb-1`}>
                  Brand Typography
                </label>
                <select
                  value={newFont}
                  onChange={(e) => setNewFont(e.target.value)}
                  className={`w-full ${
                    isLight
                      ? "bg-slate-50 border-slate-200 text-slate-900 focus:bg-white focus:border-blue-500"
                      : "bg-[#07090e] border-[#1b2940] text-white focus:bg-[#090d16] focus:border-cyan-500"
                  } border rounded-xl px-3 py-2 text-xs focus:outline-none cursor-pointer`}
                >
                  <option className={isLight ? "bg-white text-slate-900" : "bg-[#0b111e] text-white"}>Inter (Modern Sans)</option>
                  <option className={isLight ? "bg-white text-slate-900" : "bg-[#0b111e] text-white"}>Outfit (Tech Geometric)</option>
                  <option className={isLight ? "bg-white text-slate-900" : "bg-[#0b111e] text-white"}>Playfair Display (Luxury Serif)</option>
                  <option className={isLight ? "bg-white text-slate-900" : "bg-[#0b111e] text-white"}>Montserrat (Bold Grotesque)</option>
                  <option className={isLight ? "bg-white text-slate-900" : "bg-[#0b111e] text-white"}>Roboto (Clean Corporate)</option>
                </select>
              </div>
            </div>

            {/* Actions */}
            <div className={`flex justify-end gap-2.5 mt-6 pt-3 border-t ${isLight ? "border-slate-200" : "border-[#1b2940]"}`}>
              <button
                type="button"
                onClick={() => setIsCreateModalOpen(false)}
                className={`px-4 py-2 rounded-xl text-xs font-semibold ${isLight ? "text-slate-600 hover:text-slate-900 hover:bg-slate-100" : "text-slate-400 hover:text-white hover:bg-[#152033]"} cursor-pointer`}
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleCreateKit}
                disabled={!newKitName.trim()}
                className={`px-5 py-2 ${isLight ? "bg-blue-600 hover:bg-blue-700 text-white" : "bg-white hover:bg-slate-200 text-slate-950"} text-xs font-bold rounded-xl shadow-xs disabled:opacity-50 cursor-pointer`}
              >
                Save Brand System
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Share Brand System Modal */}
      {shareModalKit && (
        <div
          className="fixed inset-0 bg-black/60 backdrop-blur-xs flex items-center justify-center z-50 p-4"
          onClick={() => {
            setShareModalKit(null);
            setIsCopied(false);
          }}
        >
          <div
            className={`${isLight ? "bg-white text-slate-900 border-slate-200" : "bg-[#0b111e] text-slate-100 border-[#1b2940]"} rounded-3xl p-6 sm:p-7 max-w-md w-full shadow-2xl border animate-in fade-in zoom-in-95 duration-150`}
            onClick={(e) => e.stopPropagation()}
          >
            <div className={`flex items-center justify-between pb-4 border-b ${isLight ? "border-slate-200" : "border-[#1b2940]"}`}>
              <div className="flex items-center gap-2.5">
                <div className={`w-8 h-8 rounded-xl ${isLight ? "bg-blue-50 border-blue-200 text-blue-600" : "bg-cyan-500/15 border-cyan-500/30 text-cyan-400"} border flex items-center justify-center font-bold`}>
                  <Share2 size={16} />
                </div>
                <div>
                  <h3 className={`text-sm font-bold ${isLight ? "text-slate-900" : "text-white"}`}>Share Brand System</h3>
                  <p className={`text-[11px] ${isLight ? "text-slate-500" : "text-slate-400"} truncate max-w-[240px]`}>{shareModalKit.name}</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => {
                  setShareModalKit(null);
                  setIsCopied(false);
                }}
                className={`w-8 h-8 rounded-full ${isLight ? "hover:bg-slate-100 text-slate-400 hover:text-slate-700" : "hover:bg-[#152033] text-slate-400 hover:text-white"} flex items-center justify-center transition-colors cursor-pointer`}
              >
                <X size={16} />
              </button>
            </div>

            <div className="mt-5 space-y-4">
              <div>
                <label className={`text-xs font-semibold ${isLight ? "text-slate-700" : "text-slate-300"} block mb-1.5`}>
                  Share link
                </label>
                <div className={`flex items-center gap-2 p-1.5 ${isLight ? "bg-slate-50 border-slate-200" : "bg-[#07090e] border-[#1b2940]"} border rounded-xl`}>
                  <input
                    type="text"
                    readOnly
                    value={
                      typeof window !== "undefined"
                        ? `${window.location.origin}/brand-systems/${shareModalKit.id}`
                        : `https://app.heygen.com/brand-systems/${shareModalKit.id}`
                    }
                    className={`bg-transparent text-xs ${isLight ? "text-slate-700" : "text-slate-300"} px-2 py-1 flex-1 outline-hidden select-all`}
                  />
                  <button
                    type="button"
                    onClick={() => {
                      const url =
                        typeof window !== "undefined"
                          ? `${window.location.origin}/brand-systems/${shareModalKit.id}`
                          : `https://app.heygen.com/brand-systems/${shareModalKit.id}`;
                      if (navigator.clipboard) {
                        navigator.clipboard.writeText(url);
                      }
                      setIsCopied(true);
                      setTimeout(() => setIsCopied(false), 2000);
                    }}
                    className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer flex items-center gap-1.5 ${
                      isCopied
                        ? "bg-emerald-500 text-white shadow-xs"
                        : isLight
                        ? "bg-blue-600 hover:bg-blue-700 text-white shadow-xs"
                        : "bg-white hover:bg-slate-200 text-slate-950 shadow-xs"
                    }`}
                  >
                    {isCopied ? (
                      <>
                        <Check size={13} />
                        <span>Copied</span>
                      </>
                    ) : (
                      <>
                        <Link2 size={13} />
                        <span>Copy link</span>
                      </>
                    )}
                  </button>
                </div>
              </div>

              <div className={`p-3 ${isLight ? "bg-amber-50 border-amber-200 text-amber-900" : "bg-amber-500/10 border-amber-500/20 text-amber-300"} border rounded-xl flex items-start gap-2.5`}>
                <span className="text-sm">💎</span>
                <p className="text-[11px] leading-relaxed">
                  Anyone with this link will be able to view and duplicate the <strong>{shareModalKit.name}</strong> Brand System into their workspace.
                </p>
              </div>
            </div>

            <div className="mt-6 flex justify-end">
              <button
                type="button"
                onClick={() => {
                  setShareModalKit(null);
                  setIsCopied(false);
                }}
                className={`px-5 py-2 ${isLight ? "bg-slate-100 hover:bg-slate-200 text-slate-800 border-slate-300" : "bg-[#0f172a] hover:bg-[#172238] text-slate-300 border-[#1b2940]"} border text-xs font-semibold rounded-full transition-colors cursor-pointer`}
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Brand System Confirmation Modal */}
      {deleteModalKit && (
        <div
          className="fixed inset-0 bg-black/60 backdrop-blur-xs flex items-center justify-center z-50 p-4"
          onClick={() => setDeleteModalKit(null)}
        >
          <div
            className={`${isLight ? "bg-white text-slate-900 border-slate-200" : "bg-[#0b111e] text-slate-100 border-[#1b2940]"} rounded-3xl p-6 sm:p-7 max-w-sm w-full shadow-2xl border animate-in fade-in zoom-in-95 duration-150`}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="w-11 h-11 rounded-2xl bg-rose-500/20 border border-rose-500/30 text-rose-500 flex items-center justify-center mb-4 mx-auto">
              <Trash2 size={20} />
            </div>

            <h3 className={`text-base font-bold ${isLight ? "text-slate-900" : "text-white"} text-center`}>
              Delete Brand System?
            </h3>
            <p className={`text-xs ${isLight ? "text-slate-600" : "text-slate-400"} text-center mt-2 leading-relaxed`}>
              Are you sure you want to delete <strong className={`${isLight ? "text-slate-900" : "text-white"} font-semibold`}>{deleteModalKit.name}</strong>? This action cannot be undone.
            </p>

            <div className="mt-6 flex items-center justify-center gap-3">
              <button
                type="button"
                onClick={() => setDeleteModalKit(null)}
                className={`flex-1 px-4 py-2.5 ${isLight ? "bg-slate-100 hover:bg-slate-200 text-slate-700 border-slate-300" : "bg-[#0f172a] hover:bg-[#172238] text-slate-300 border-[#1b2940]"} border text-xs font-semibold rounded-full transition-colors cursor-pointer`}
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={async () => {
                  try {
                    await api.brandKits.delete(deleteModalKit.id, currentWorkspace?.id);
                    await fetchKits();
                    setDeleteModalKit(null);
                  } catch (err: any) {
                    alert(err?.message || "Failed to delete brand kit");
                  }
                }}
                className="flex-1 px-4 py-2.5 bg-rose-600 hover:bg-rose-700 text-white text-xs font-semibold rounded-full shadow-xs transition-colors cursor-pointer"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Brand Glossary Confirmation Modal */}
      {deleteGlossaryModal && (
        <div
          className="fixed inset-0 bg-black/60 backdrop-blur-xs flex items-center justify-center z-50 p-4"
          onClick={() => setDeleteGlossaryModal(null)}
        >
          <div
            className={`${isLight ? "bg-white text-slate-900 border-slate-200" : "bg-[#0b111e] text-slate-100 border-[#1b2940]"} rounded-3xl p-6 sm:p-7 max-w-sm w-full shadow-2xl border animate-in fade-in zoom-in-95 duration-150`}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="w-11 h-11 rounded-2xl bg-rose-500/20 border border-rose-500/30 text-rose-500 flex items-center justify-center mb-4 mx-auto">
              <Trash2 size={20} />
            </div>

            <h3 className={`text-base font-bold ${isLight ? "text-slate-900" : "text-white"} text-center`}>
              Delete Brand Glossary?
            </h3>
            <p className={`text-xs ${isLight ? "text-slate-600" : "text-slate-400"} text-center mt-2 leading-relaxed`}>
              Are you sure you want to delete <strong className={`${isLight ? "text-slate-900" : "text-white"} font-semibold`}>{deleteGlossaryModal.name}</strong>? This action cannot be undone.
            </p>

            <div className="mt-6 flex items-center justify-center gap-3">
              <button
                type="button"
                onClick={() => setDeleteGlossaryModal(null)}
                className={`flex-1 px-4 py-2.5 ${isLight ? "bg-slate-100 hover:bg-slate-200 text-slate-700 border-slate-300" : "bg-[#0f172a] hover:bg-[#172238] text-slate-300 border-[#1b2940]"} border text-xs font-semibold rounded-full transition-colors cursor-pointer`}
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={async () => {
                  try {
                    await api.brandGlossaries.delete(deleteGlossaryModal.id, currentWorkspace?.id);
                    await fetchGlossaries();
                    setDeleteGlossaryModal(null);
                  } catch (err: any) {
                    alert(err?.message || "Failed to delete brand glossary");
                  }
                }}
                className="flex-1 px-4 py-2.5 bg-rose-600 hover:bg-rose-700 text-white text-xs font-semibold rounded-full shadow-xs transition-colors cursor-pointer"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

