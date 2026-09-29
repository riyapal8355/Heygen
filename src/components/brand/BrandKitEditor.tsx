"use client";

import React, { useState, useRef } from "react";
import {
  Plus,
  ChevronDown,
  ArrowRight,
  ArrowLeft,
  Upload,
  Image as ImageIcon,
  Check,
  Loader2,
  Trash2,
  Palette,
  FileText,
} from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";

interface ColorToken {
  id: string;
  name: string;
  hex: string;
}

interface FontToken {
  id: string;
  role: string;
  family: string;
  weight: string;
  size: string;
  cqw: string;
}

export function getNextCopyName(baseName: string, existingNames: string[]): string {
  let cleanBase = baseName.replace(/(\s+Copy(\s+\d+)?)+$/i, "").trim();
  if (!cleanBase) cleanBase = baseName;
  const firstCopy = `${cleanBase} Copy`;
  if (!existingNames.includes(firstCopy)) {
    return firstCopy;
  }
  let index = 2;
  while (existingNames.includes(`${cleanBase} Copy ${index}`)) {
    index++;
  }
  return `${cleanBase} Copy ${index}`;
}

interface BrandKitEditorProps {
  onBack?: () => void;
  onOpenStudio?: () => void;
  onUseSystem?: (system: {
    id?: string;
    name: string;
    primaryColor: string;
    accentColor: string;
    secondaryColor: string;
    fontFamily: string;
  }) => void;
  initialTitle?: string;
  initialPrimaryColor?: string;
  initialAccentColor?: string;
  initialSecondaryColor?: string;
  initialFontFamily?: string;
  initialLogoAssetId?: string;
  existingKitNames?: string[];
  onSave?: (savedKit: {
    name: string;
    primaryColor: string;
    accentColor: string;
    secondaryColor: string;
    fontFamily: string;
    logoAssetId?: string;
    isCopy?: boolean;
  }) => void;
}

export default function BrandKitEditor({
  onBack,
  onOpenStudio,
  onUseSystem,
  initialTitle = "Demo HeyGen Brand Kit Copy",
  initialPrimaryColor,
  initialAccentColor,
  initialSecondaryColor,
  initialFontFamily,
  initialLogoAssetId,
  existingKitNames = [],
  onSave,
}: BrandKitEditorProps) {
  const { currentWorkspace } = useAuth();
  const [activeTab, setActiveTab] = useState<"brand_spec" | "assets" | "logos">("brand_spec");
  const [brandTitle, setBrandTitle] = useState(initialTitle);
  const [logoAssetId, setLogoAssetId] = useState<string | undefined>(initialLogoAssetId);
  const [logoPreviewUrl, setLogoPreviewUrl] = useState<string | null>(null);
  const [isUploadingLogo, setIsUploadingLogo] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Exact Colors matching reference
  const [colors, setColors] = useState<ColorToken[]>([
    { id: "c1", name: "Background", hex: "#F7F8FA" },
    { id: "c2", name: "Main Text", hex: initialPrimaryColor || "#000000" },
    { id: "c3", name: "Accent 1", hex: initialAccentColor || "#00C4FF" },
    { id: "c4", name: "Panel Background", hex: "#FFFFFF" },
    { id: "c5", name: "Secondary Text", hex: initialSecondaryColor || "#818999" },
    { id: "c6", name: "Border", hex: "#E2E3E6" },
    { id: "c7", name: "Ink On Light", hex: "#111827" },
    { id: "c8", name: "Hairline Light", hex: "#F3F4F6" },
  ]);

  // Exact Fonts matching reference
  const [fonts, setFonts] = useState<FontToken[]>([
    { id: "f1", role: "Body", family: initialFontFamily || "TT Norms Pro", weight: "400", size: "16px", cqw: "0.85cqw" },
    { id: "f2", role: "Label", family: initialFontFamily || "TT Norms Pro", weight: "500", size: "14px", cqw: "0.75cqw" },
    { id: "f3", role: "Caption", family: initialFontFamily || "TT Norms Pro", weight: "400", size: "12px", cqw: "0.65cqw" },
    { id: "f4", role: "Display", family: initialFontFamily || "TT Norms Pro", weight: "600", size: "154px", cqw: "8cqw" },
    { id: "f5", role: "Heading", family: initialFontFamily || "Albert Sans", weight: "700", size: "36px", cqw: "2.1cqw" },
    { id: "f6", role: "Heading 2", family: initialFontFamily || "Albert Sans", weight: "600", size: "28px", cqw: "1.6cqw" },
  ]);

  React.useEffect(() => {
    setBrandTitle(initialTitle);
  }, [initialTitle]);

  React.useEffect(() => {
    setLogoAssetId(initialLogoAssetId);
  }, [initialLogoAssetId]);

  React.useEffect(() => {
    if (initialPrimaryColor || initialAccentColor || initialSecondaryColor) {
      setColors([
        { id: "c1", name: "Background", hex: "#F7F8FA" },
        { id: "c2", name: "Main Text", hex: initialPrimaryColor || "#000000" },
        { id: "c3", name: "Accent 1", hex: initialAccentColor || "#00C4FF" },
        { id: "c4", name: "Panel Background", hex: "#FFFFFF" },
        { id: "c5", name: "Secondary Text", hex: initialSecondaryColor || "#818999" },
        { id: "c6", name: "Border", hex: "#E2E3E6" },
        { id: "c7", name: "Ink On Light", hex: "#111827" },
        { id: "c8", name: "Hairline Light", hex: "#F3F4F6" },
      ]);
    }
  }, [initialPrimaryColor, initialAccentColor, initialSecondaryColor]);

  React.useEffect(() => {
    if (initialFontFamily) {
      setFonts([
        { id: "f1", role: "Body", family: initialFontFamily, weight: "400", size: "16px", cqw: "0.85cqw" },
        { id: "f2", role: "Label", family: initialFontFamily, weight: "500", size: "14px", cqw: "0.75cqw" },
        { id: "f3", role: "Caption", family: initialFontFamily, weight: "400", size: "12px", cqw: "0.65cqw" },
        { id: "f4", role: "Display", family: initialFontFamily, weight: "600", size: "154px", cqw: "8cqw" },
        { id: "f5", role: "Heading", family: initialFontFamily, weight: "700", size: "36px", cqw: "2.1cqw" },
        { id: "f6", role: "Heading 2", family: initialFontFamily, weight: "600", size: "28px", cqw: "1.6cqw" },
      ]);
    }
  }, [initialFontFamily]);

  const fontOptions = [
    "TT Norms Pro",
    "Albert Sans",
    "Inter",
    "Outfit",
    "Playfair Display",
    "Space Grotesk",
    "Montserrat",
    "Roboto",
  ];

  const handleAddColor = () => {
    const newColor: ColorToken = {
      id: typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : "color_token",
      name: `Color ${colors.length + 1}`,
      hex: "#3B82F6",
    };
    setColors([...colors, newColor]);
  };

  const handleAddFont = () => {
    const newFont: FontToken = {
      id: typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : "font_token",
      role: `Custom Role ${fonts.length + 1}`,
      family: "TT Norms Pro",
      weight: "500",
      size: "24px",
      cqw: "1.2cqw",
    };
    setFonts([...fonts, newFont]);
  };

  const handleColorChange = (id: string, newHex: string) => {
    setColors(colors.map((c) => (c.id === id ? { ...c, hex: newHex } : c)));
  };

  const handleFontChange = (id: string, newFamily: string) => {
    setFonts(fonts.map((f) => (f.id === id ? { ...f, family: newFamily } : f)));
  };

  const handleLogoFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith("image/")) {
      setUploadError("Please upload a valid image file (PNG, SVG, JPG, WebP).");
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      setUploadError("Logo file must be under 10MB.");
      return;
    }

    setIsUploadingLogo(true);
    setUploadError(null);
    try {
      if (!currentWorkspace?.id) {
        throw new Error("No active workspace found for upload.");
      }
      const asset = await api.assets.uploadFile(currentWorkspace.id, file, "image");
      setLogoAssetId(asset.id);
      const objectUrl = URL.createObjectURL(file);
      setLogoPreviewUrl(objectUrl);
    } catch (err: any) {
      setUploadError(err?.message || "Failed to upload logo asset.");
    } finally {
      setIsUploadingLogo(false);
    }
  };

  const handleSave = () => {
    if (onSave) {
      onSave({
        name: brandTitle,
        primaryColor: colors[1]?.hex || "#000000",
        accentColor: colors[2]?.hex || "#00C4FF",
        secondaryColor: colors[4]?.hex || "#818999",
        fontFamily: fonts[0]?.family || "Inter, sans-serif",
        logoAssetId: logoAssetId,
      });
    } else {
      alert(`Brand System "${brandTitle}" saved successfully!`);
      if (onBack) onBack();
    }
  };

  const handleMakeCopy = () => {
    const nextName = getNextCopyName(brandTitle, [brandTitle, ...existingKitNames]);
    setBrandTitle(nextName);
  };

  const handleUseSystem = () => {
    const systemData = {
      name: brandTitle,
      primaryColor: colors[1]?.hex || "#000000",
      accentColor: colors[2]?.hex || "#00C4FF",
      secondaryColor: colors[4]?.hex || "#818999",
      fontFamily: fonts[0]?.family || "Inter, sans-serif",
    };
    if (onUseSystem) {
      onUseSystem(systemData);
    } else if (onOpenStudio) {
      onOpenStudio();
    }
  };

  return (
    <div className="flex-1 h-screen overflow-y-auto bg-[#07090e] text-slate-100 flex flex-col font-sans select-none">
      {/* 1. TOP HEADER */}
      <div className="w-full px-8 sm:px-10 pt-6 pb-4 flex items-center justify-between border-b border-[#1b2940] bg-[#07090e] z-20">
        <div>
          {/* Logo & Title */}
          <div className="flex items-center gap-3 mb-1">
            {onBack && (
              <button
                type="button"
                onClick={onBack}
                className="w-8 h-8 rounded-full border border-[#1b2940] bg-[#0b111e] hover:bg-[#162035] flex items-center justify-center text-slate-300 hover:text-white transition-colors cursor-pointer mr-1"
                title="Back"
              >
                <ArrowLeft size={16} />
              </button>
            )}

            <div className="w-8 h-8 flex flex-col justify-center font-black text-xs leading-none tracking-tighter text-white">
              <div>Hey</div>
              <div>Gen</div>
            </div>

            <input
              type="text"
              value={brandTitle}
              onChange={(e) => setBrandTitle(e.target.value)}
              className="text-2xl font-extrabold text-white tracking-tight bg-transparent focus:outline-none focus:border-b border-cyan-500"
            />
          </div>

          <p className="text-xs text-slate-400">
            Define your brand here. Edit brand colors, upload logos, fonts, assets, and more.
          </p>
        </div>

        {/* Top Right Action Buttons */}
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={handleMakeCopy}
            className="px-5 py-2 bg-[#0f172a] hover:bg-[#172238] text-slate-300 border border-[#1b2940] text-xs font-semibold rounded-full shadow-xs transition-all cursor-pointer"
          >
            Make a copy
          </button>

          <button
            type="button"
            onClick={handleUseSystem}
            className="px-5 py-2 bg-white hover:bg-slate-200 text-slate-950 text-xs font-bold rounded-full shadow-sm transition-all cursor-pointer"
          >
            Use this System
          </button>
        </div>
      </div>

      {/* 2. TABS ROW */}
      <div className="w-full px-8 sm:px-10 pt-3 border-b border-[#1b2940] bg-[#07090e]">
        <div className="flex items-center gap-8 text-xs font-bold">
          <button
            type="button"
            onClick={() => setActiveTab("brand_spec")}
            className={`pb-2.5 transition-colors cursor-pointer relative ${
              activeTab === "brand_spec"
                ? "text-white font-extrabold"
                : "text-slate-400 hover:text-white"
            }`}
          >
            Brand Spec
            {activeTab === "brand_spec" && (
              <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-cyan-400 rounded-full shadow-xs"></span>
            )}
          </button>

          <button
            type="button"
            onClick={() => setActiveTab("logos")}
            className={`pb-2.5 transition-colors cursor-pointer relative ${
              activeTab === "logos"
                ? "text-white font-extrabold"
                : "text-slate-400 hover:text-white"
            }`}
          >
            Logos
            {activeTab === "logos" && (
              <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-cyan-400 rounded-full shadow-xs"></span>
            )}
          </button>

          <button
            type="button"
            onClick={() => setActiveTab("assets")}
            className={`pb-2.5 transition-colors cursor-pointer relative ${
              activeTab === "assets"
                ? "text-white font-extrabold"
                : "text-slate-400 hover:text-white"
            }`}
          >
            Assets
            {activeTab === "assets" && (
              <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-cyan-400 rounded-full shadow-xs"></span>
            )}
          </button>
        </div>
      </div>

      {/* 3. MAIN CONTENT */}
      <div className="max-w-[1440px] w-full mx-auto px-8 sm:px-10 py-6 flex-1 grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* LEFT COLUMN: Tokens + Bottom Cancel/Save Bar */}
        <div className="lg:col-span-5 flex flex-col justify-between max-h-[calc(100vh-170px)]">
          <div className="space-y-6 overflow-y-auto pr-2 flex-1 no-scrollbar">
            {activeTab === "brand_spec" && (
              <>
                {/* COLORS SECTION */}
                <div>
                  <span className="text-[10px] font-bold text-slate-400 tracking-wider uppercase block mb-3">
                    Colors
                  </span>

                  <div className="space-y-2">
                    {colors.map((color) => (
                      <div
                        key={color.id}
                        className="bg-[#0b111e] border border-[#1b2940] hover:border-slate-600 rounded-2xl p-2.5 px-3.5 flex items-center justify-between shadow-xs transition-colors"
                      >
                        <div className="flex items-center gap-3">
                          <div className="relative flex items-center justify-center">
                            <input
                              type="color"
                              value={color.hex}
                              onChange={(e) => handleColorChange(color.id, e.target.value)}
                              className="w-6 h-6 rounded-full cursor-pointer border border-white/20 bg-transparent"
                            />
                          </div>

                          <div>
                            <span className="text-xs font-bold text-white block">
                              {color.name}
                            </span>
                            <span className="text-[10px] font-mono text-slate-400">
                              {color.hex.toUpperCase()}
                            </span>
                          </div>
                        </div>
                      </div>
                    ))}

                    {/* Add a new color button */}
                    <button
                      type="button"
                      onClick={handleAddColor}
                      className="w-full py-2.5 bg-[#0b111e] hover:bg-[#162035] border border-dashed border-[#1b2940] hover:border-cyan-500/60 rounded-2xl text-xs font-semibold text-slate-300 flex items-center justify-center gap-2 transition-all cursor-pointer shadow-xs"
                    >
                      <Plus size={14} />
                      <span>Add a new color</span>
                    </button>
                  </div>
                </div>

                {/* FONTS SECTION */}
                <div>
                  <span className="text-[10px] font-bold text-slate-400 tracking-wider uppercase block mb-3">
                    Fonts
                  </span>

                  <div className="space-y-2.5">
                    {fonts.map((font) => (
                      <div
                        key={font.id}
                        className="bg-[#0b111e] border border-[#1b2940] rounded-2xl p-3 px-3.5 shadow-xs"
                      >
                        <label className="text-[10px] font-semibold text-slate-400 block mb-1">
                          {font.role}
                        </label>

                        <div className="relative">
                          <select
                            value={font.family}
                            onChange={(e) => handleFontChange(font.id, e.target.value)}
                            className="w-full appearance-none bg-[#07090e] border border-[#1b2940] rounded-xl px-3 py-1.5 text-xs font-semibold text-white focus:outline-none focus:border-cyan-500 focus:bg-[#090d16] cursor-pointer pr-8"
                          >
                            {fontOptions.map((opt) => (
                              <option key={opt} value={opt} className="bg-[#0b111e] text-white">
                                {opt}
                              </option>
                            ))}
                          </select>
                          <ChevronDown size={14} className="absolute right-3 top-2.5 text-slate-400 pointer-events-none" />
                        </div>
                      </div>
                    ))}

                    {/* Add a new font button */}
                    <button
                      type="button"
                      onClick={handleAddFont}
                      className="w-full py-2.5 bg-[#0b111e] hover:bg-[#162035] border border-dashed border-[#1b2940] hover:border-cyan-500/60 rounded-2xl text-xs font-semibold text-slate-300 flex items-center justify-center gap-2 transition-all cursor-pointer shadow-xs"
                    >
                      <Plus size={14} />
                      <span>Add a new font</span>
                    </button>
                  </div>
                </div>
              </>
            )}

            {activeTab === "logos" && (
              <div className="space-y-5">
                <span className="text-[10px] font-bold text-slate-400 tracking-wider uppercase block mb-1">
                  Brand Logo Identity
                </span>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Upload your vector or high-resolution PNG logo stored securely in MinIO storage.
                </p>

                {/* Uploaded Logo Box */}
                {logoAssetId ? (
                  <div className="bg-[#0b111e] border border-cyan-500/40 rounded-2xl p-4 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-12 h-12 rounded-xl bg-slate-900 border border-slate-700 flex items-center justify-center overflow-hidden p-1">
                        {logoPreviewUrl ? (
                          <img src={logoPreviewUrl} alt="Logo" className="w-full h-full object-contain" />
                        ) : (
                          <ImageIcon className="text-cyan-400" size={24} />
                        )}
                      </div>
                      <div>
                        <span className="text-xs font-bold text-white block">Active Brand Logo</span>
                        <span className="text-[10px] font-mono text-cyan-400">Asset: {logoAssetId.slice(0, 12)}...</span>
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => {
                        setLogoAssetId(undefined);
                        setLogoPreviewUrl(null);
                      }}
                      className="p-2 rounded-xl bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 hover:text-rose-300 transition-colors cursor-pointer"
                      title="Remove logo"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                ) : (
                  <div
                    onClick={() => fileInputRef.current?.click()}
                    className="border-2 border-dashed border-[#1b2940] hover:border-cyan-500/60 rounded-3xl p-8 flex flex-col items-center justify-center text-center cursor-pointer bg-[#0b111e]/40 hover:bg-[#0b111e] transition-all group"
                  >
                    <input
                      type="file"
                      ref={fileInputRef}
                      onChange={handleLogoFileSelect}
                      accept="image/*"
                      className="hidden"
                    />
                    <div className="w-12 h-12 rounded-2xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400 mb-3 group-hover:scale-110 transition-transform">
                      {isUploadingLogo ? <Loader2 className="animate-spin" size={20} /> : <Upload size={20} />}
                    </div>
                    <span className="text-xs font-bold text-slate-200">
                      {isUploadingLogo ? "Uploading logo to MinIO..." : "Upload Logo Asset"}
                    </span>
                    <span className="text-[10px] text-slate-500 mt-1">SVG, PNG, JPG, or WebP up to 10MB</span>
                  </div>
                )}

                {uploadError && (
                  <p className="text-xs text-rose-400 mt-2">{uploadError}</p>
                )}
              </div>
            )}

            {activeTab === "assets" && (
              <div className="space-y-4">
                <span className="text-[10px] font-bold text-slate-400 tracking-wider uppercase block mb-1">
                  Brand Graphic Assets
                </span>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Attach workspace graphics, watermarks, or banners to this brand system.
                </p>
                <div
                  onClick={() => fileInputRef.current?.click()}
                  className="border-2 border-dashed border-[#1b2940] hover:border-cyan-500/60 rounded-3xl p-8 flex flex-col items-center justify-center text-center cursor-pointer bg-[#0b111e]/40 hover:bg-[#0b111e] transition-all group"
                >
                  <div className="w-12 h-12 rounded-2xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400 mb-3 group-hover:scale-110 transition-transform">
                    <Upload size={20} />
                  </div>
                  <span className="text-xs font-bold text-slate-200">Upload Media Asset</span>
                  <span className="text-[10px] text-slate-500 mt-1">PNG, JPG, SVG, MP4</span>
                </div>
              </div>
            )}
          </div>

          {/* BOTTOM CANCEL & SAVE BAR */}
          <div className="pt-4 mt-3 border-t border-[#1b2940] flex items-center gap-3">
            <button
              type="button"
              onClick={onBack}
              className="flex-1 py-2.5 bg-[#0f172a] hover:bg-[#172238] text-slate-300 border border-[#1b2940] text-xs font-bold rounded-2xl transition-all cursor-pointer shadow-xs"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSave}
              className="flex-1 py-2.5 bg-white hover:bg-slate-200 text-slate-950 text-xs font-bold rounded-2xl shadow-sm transition-all cursor-pointer"
            >
              Save
            </button>
          </div>
        </div>

        {/* RIGHT COLUMN: Spec Sheet & Frame Compositions */}
        <div className="lg:col-span-7 bg-[#0b111e] border border-[#1b2940] rounded-3xl p-6 shadow-xl flex flex-col justify-between overflow-y-auto max-h-[calc(100vh-170px)]">
          <div className="space-y-8">
            {/* 1. TYPOGRAPHY SPEC SHEET SECTION */}
            <div className="bg-[#07090e] border border-[#1b2940] rounded-2xl p-6 shadow-inner space-y-6">
              <div className="flex items-center justify-between pb-3 border-b border-[#1b2940]">
                <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                  Typography Spec Sheet
                </span>
                <span className="text-[10px] font-mono text-cyan-400 font-semibold">
                  Live Token Render
                </span>
              </div>

              {/* link Spec Row */}
              <div className="flex items-center justify-between pb-5 border-b border-[#1b2940]">
                <div>
                  <h4 className="text-xs font-bold italic text-white mb-0.5">
                    link
                  </h4>
                  <p className="text-[10px] font-mono text-slate-400">
                    {fonts[1]?.family || fonts[0]?.family || "TT Norms Pro"} {fonts[1]?.weight || "400"} • {fonts[1]?.size || "18px"} • {fonts[1]?.cqw || "0.94cqw"}
                  </p>
                </div>

                <div
                  className="text-sm font-semibold underline underline-offset-4"
                  style={{ color: colors[2]?.hex || "#00C4FF" }}
                >
                  Aa — link
                </div>
              </div>

              {/* display-hero Spec Row */}
              <div className="flex items-center justify-between pb-5 border-b border-[#1b2940]">
                <div>
                  <h4 className="text-xs font-bold italic text-white mb-0.5">
                    display-hero
                  </h4>
                  <p className="text-[10px] font-mono text-slate-400">
                    {fonts[3]?.family || fonts[0]?.family || "TT Norms Pro"} {fonts[3]?.weight || "600"} • {fonts[3]?.size || "154px"} • {fonts[3]?.cqw || "8cqw"}
                  </p>
                </div>

                <div
                  className="text-4xl font-extrabold tracking-tighter text-white truncate max-w-[140px]"
                  style={{ fontFamily: fonts[3]?.family || fonts[0]?.family }}
                >
                  {brandTitle.slice(0, 3)}...
                </div>
              </div>

              {/* wordmark-mega Spec Row */}
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="text-xs font-bold italic text-white mb-0.5">
                    wordmark-mega
                  </h4>
                  <p className="text-[10px] font-mono text-slate-400">
                    {fonts[4]?.family || fonts[0]?.family || "TT Norms Pro"} {fonts[4]?.weight || "600"} • {fonts[4]?.size || "154px"} • {fonts[4]?.cqw || "8.02cqw"}
                  </p>
                </div>

                <div
                  className="text-4xl font-black text-white"
                  style={{ fontFamily: fonts[4]?.family || fonts[0]?.family }}
                >
                  Aa
                </div>
              </div>
            </div>

            {/* 2. FRAME COMPOSITIONS SECTION */}
            <div>
              <div className="flex items-center justify-between pb-3 border-b border-[#1b2940] mb-4">
                <h3 className="text-sm font-bold italic tracking-tight text-white flex items-center gap-2">
                  <span className="w-4 h-0.5 bg-cyan-400 inline-block"></span>
                  <span>Frame Compositions</span>
                </h3>
                <span className="text-[11px] font-mono text-slate-400">
                  01 • 16:9
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Frame 1: Identity / Cover */}
                <div className="flex flex-col">
                  <div className="aspect-[16/10] bg-slate-900 rounded-2xl overflow-hidden relative shadow-md border border-[#1b2940]">
                    <img
                      src="https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?q=80&w=700&auto=format&fit=crop"
                      alt="Identity Cover"
                      className="w-full h-full object-cover object-top brightness-90"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-black/20"></div>

                    <span className="absolute top-2.5 left-2.5 text-[8px] font-bold bg-black/60 backdrop-blur-sm px-2 py-0.5 rounded text-white tracking-widest border border-white/10">
                      SPECIAL REPORT
                    </span>

                    <div className="absolute bottom-2.5 left-2.5">
                      <h4
                        className="text-base font-serif italic text-white leading-none"
                        style={{ fontFamily: fonts[0]?.family }}
                      >
                        The brief.
                      </h4>
                    </div>
                  </div>

                  <div className="flex items-center justify-between mt-2 px-1 text-[10px]">
                    <span className="font-bold text-slate-200">Identity / Cover</span>
                    <span className="text-slate-400 italic">avatar overlay + wordmark</span>
                  </div>
                </div>

                {/* Frame 2: Oversized Claim */}
                <div className="flex flex-col">
                  <div
                    className="aspect-[16/10] rounded-2xl overflow-hidden relative shadow-md p-4 flex flex-col justify-between border"
                    style={{
                      background: `linear-gradient(135deg, ${colors[1]?.hex || "#0f172a"}, ${colors[4]?.hex || "#232B33"})`,
                      borderColor: `${colors[2]?.hex || "#00C4FF"}44`,
                    }}
                  >
                    <span className="text-[8px] font-bold uppercase tracking-widest text-white/80">
                      THE LEAD
                    </span>

                    <p
                      className="text-sm font-serif italic font-bold text-white leading-snug"
                      style={{ fontFamily: fonts[0]?.family }}
                    >
                      One bold idea, said once, owns the frame.
                    </p>

                    <div className="flex justify-end">
                      <span
                        className="text-[7px] font-bold text-white px-2 py-0.5 rounded-full"
                        style={{ backgroundColor: colors[2]?.hex || "#00C4FF" }}
                      >
                        {brandTitle.toUpperCase()}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center justify-between mt-2 px-1 text-[10px]">
                    <span className="font-bold text-slate-200">Oversized Claim</span>
                    <span className="text-slate-400 italic">serif-italic statement</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Bottom Info Bar */}
          <div className="mt-6 pt-4 border-t border-[#1b2940] flex items-center justify-between text-xs text-slate-400">
            <span>Tokens dynamically linked to Studio Video sequencer</span>
            <button
              type="button"
              onClick={() => {
                if (onOpenStudio) onOpenStudio();
              }}
              className="font-bold text-cyan-400 hover:text-cyan-300 hover:underline flex items-center gap-1 cursor-pointer"
            >
              <span>Test in Studio</span>
              <ArrowRight size={13} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

