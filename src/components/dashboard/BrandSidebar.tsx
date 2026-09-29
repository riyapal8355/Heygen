"use client";

import React from "react";
import { Palette, BookOpen, PanelLeftClose } from "lucide-react";
import { useTheme } from "@/context/ThemeContext";

interface BrandSidebarProps {
  activeSection: "brand_systems" | "brand_glossary";
  onSelectSection: (section: "brand_systems" | "brand_glossary") => void;
  brandKits?: string[];
  brandGlossaries?: { id: string; name: string }[];
  selectedKit?: string;
  selectedGlossaryId?: string;
  onSelectKit?: (kitName: string) => void;
  onSelectGlossary?: (glossaryId: string, glossaryName: string) => void;
  onAddNewKit?: () => void;
}

export default function BrandSidebar({
  activeSection,
  onSelectSection,
  brandKits = [],
  brandGlossaries,
  selectedKit = "",
  selectedGlossaryId,
  onSelectKit,
  onSelectGlossary,
}: BrandSidebarProps) {
  const { theme } = useTheme();
  const isLight = theme === "light";

  return (
    <aside className={`w-64 min-w-64 h-screen flex flex-col justify-between shrink-0 font-sans select-none transition-colors ${
      isLight ? "bg-white border-r border-slate-200" : "bg-[#090d16] border-r border-[#151c2d]"
    }`}>
      <div className="p-4 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-2 py-2 mb-2">
          <span className={`text-sm font-bold ${isLight ? "text-slate-900" : "text-white"}`}>Brand</span>
          <button
            type="button"
            title="Collapse sidebar"
            className={`transition-colors p-1 rounded-lg cursor-pointer ${
              isLight ? "text-slate-400 hover:text-slate-900 hover:bg-slate-100" : "text-slate-400 hover:text-white hover:bg-[#152033]"
            }`}
          >
            <PanelLeftClose size={16} />
          </button>
        </div>

        {/* Navigation Items */}
        <nav className="space-y-1">
          {/* Brand Systems Item */}
          <button
            type="button"
            onClick={() => onSelectSection("brand_systems")}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-semibold transition-all text-left cursor-pointer ${
              activeSection === "brand_systems"
                ? isLight
                  ? "bg-[#eef4ff] text-slate-900 border border-blue-200/70 font-semibold shadow-xs"
                  : "bg-[#18233c] text-white border border-[#2b3a5d]/50 shadow-sm"
                : isLight
                ? "text-slate-600 hover:bg-slate-50 hover:text-slate-900 font-medium"
                : "text-slate-400 hover:bg-[#101625] hover:text-slate-200 font-medium"
            }`}
          >
            <Palette
              size={16}
              className={`shrink-0 ${
                activeSection === "brand_systems"
                  ? isLight ? "text-blue-600" : "text-cyan-400"
                  : "text-slate-400"
              }`}
            />
            <span>Brand Systems</span>
          </button>

          {/* Brand Glossary Item */}
          <button
            type="button"
            onClick={() => onSelectSection("brand_glossary")}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-semibold transition-all text-left cursor-pointer ${
              activeSection === "brand_glossary"
                ? isLight
                  ? "bg-[#eef4ff] text-slate-900 border border-blue-200/70 font-semibold shadow-xs"
                  : "bg-[#18233c] text-white border border-[#2b3a5d]/50 shadow-sm"
                : isLight
                ? "text-slate-600 hover:bg-slate-50 hover:text-slate-900 font-medium"
                : "text-slate-400 hover:bg-[#101625] hover:text-slate-200 font-medium"
            }`}
          >
            <BookOpen
              size={16}
              className={`shrink-0 ${
                activeSection === "brand_glossary"
                  ? isLight ? "text-blue-600" : "text-cyan-400"
                  : "text-slate-400"
              }`}
            />
            <span>Brand Glossary</span>
          </button>
        </nav>

        {/* Divider */}
        <div className={`h-[1px] my-4 mx-2 ${isLight ? "bg-slate-200" : "bg-[#1b2940]"}`}></div>

        {/* Brand Items Sub-List */}
        <div className="space-y-1">
          {activeSection === "brand_glossary" && brandGlossaries && brandGlossaries.length > 0 ? (
            brandGlossaries.map((glossary) => (
              <button
                key={glossary.id}
                type="button"
                onClick={() => {
                  onSelectSection("brand_glossary");
                  if (onSelectGlossary) onSelectGlossary(glossary.id, glossary.name);
                }}
                className={`w-full flex items-center justify-between px-3 py-2 rounded-xl text-xs transition-colors text-left cursor-pointer ${
                  selectedGlossaryId === glossary.id
                    ? isLight
                      ? "text-slate-900 font-semibold bg-slate-100 border border-slate-300"
                      : "text-white font-medium bg-[#18233c] border border-[#2b3a5d]/40"
                    : isLight
                    ? "text-slate-600 font-normal hover:text-slate-900 hover:bg-slate-50"
                    : "text-slate-400 font-normal hover:text-slate-200 hover:bg-[#101625]"
                }`}
              >
                <span className="truncate">{glossary.name}</span>
              </button>
            ))
          ) : (
            brandKits.map((kit, index) => (
              <button
                key={`${kit}-${index}`}
                type="button"
                onClick={() => {
                  onSelectSection("brand_systems");
                  if (onSelectKit) onSelectKit(kit);
                }}
                className={`w-full flex items-center justify-between px-3 py-2 rounded-xl text-xs transition-colors text-left cursor-pointer ${
                  selectedKit === kit && activeSection === "brand_systems"
                    ? isLight
                      ? "text-slate-900 font-semibold bg-slate-100 border border-slate-300"
                      : "text-white font-medium bg-[#18233c] border border-[#2b3a5d]/40"
                    : isLight
                    ? "text-slate-600 font-normal hover:text-slate-900 hover:bg-slate-50"
                    : "text-slate-400 font-normal hover:text-slate-200 hover:bg-[#101625]"
                }`}
              >
                <span className="truncate">{kit}</span>
              </button>
            ))
          )}
        </div>
      </div>
    </aside>
  );
}
