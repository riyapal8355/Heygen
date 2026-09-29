"use client";

import React from "react";
import {
  LayoutGrid,
  BookOpen,
  ShoppingBag,
  Megaphone,
  Share2,
  HelpCircle,
  PanelLeftClose,
  Sparkles,
} from "lucide-react";
import { useTheme } from "@/context/ThemeContext";

interface TemplatesSidebarProps {
  activeCategory: string;
  onSelectCategory: (category: string) => void;
}

const templateCategories = [
  { id: "all", label: "All Templates", icon: LayoutGrid },
  { id: "learning", label: "Learning & Development", icon: BookOpen },
  { id: "sales", label: "Sales & Outreach", icon: ShoppingBag },
  { id: "marketing", label: "Marketing Ads", icon: Megaphone },
  { id: "social", label: "Social Media Shorts", icon: Share2 },
  { id: "explainer", label: "Product Explainers", icon: HelpCircle },
];

export default function TemplatesSidebar({
  activeCategory,
  onSelectCategory,
}: TemplatesSidebarProps) {
  const { theme } = useTheme();
  const isLight = theme === "light";

  return (
    <aside className={`w-64 h-screen flex flex-col justify-between shrink-0 font-sans select-none transition-colors ${
      isLight ? "bg-white border-r border-slate-200" : "bg-[#0a0e17] border-r border-[#141b2c]"
    }`}>
      <div className="p-4 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-2 py-2 mb-2">
          <span className={`text-sm font-bold ${isLight ? "text-slate-900" : "text-white"}`}>Templates</span>
          <button
            title="Collapse sidebar"
            className={`transition-colors p-1 rounded-lg cursor-pointer ${
              isLight ? "text-slate-400 hover:text-slate-900 hover:bg-slate-100" : "text-slate-400 hover:text-slate-200 hover:bg-[#121828]"
            }`}
          >
            <PanelLeftClose size={16} />
          </button>
        </div>

        {/* Categories Navigation */}
        <nav className="space-y-1">
          {templateCategories.map((cat) => {
            const Icon = cat.icon;
            const isActive = activeCategory === cat.id;
            return (
              <button
                key={cat.id}
                onClick={() => onSelectCategory(cat.id)}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-bold transition-all text-left cursor-pointer ${
                  isActive
                    ? isLight
                      ? "bg-[#eef4ff] text-blue-700 shadow-xs border border-blue-200/70"
                      : "bg-[#151f36] text-cyan-400 shadow-sm"
                    : isLight
                    ? "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                    : "text-slate-400 hover:bg-[#111728] hover:text-slate-200"
                }`}
              >
                <Icon size={16} className={`shrink-0 ${isActive && isLight ? "text-blue-600" : ""}`} />
                <span className="truncate">{cat.label}</span>
              </button>
            );
          })}
        </nav>

        {/* Divider */}
        <div className={`h-[1px] my-4 mx-2 ${isLight ? "bg-slate-200" : "bg-[#141b2c]"}`}></div>

        {/* Pro Tip Box */}
        <div className={`rounded-2xl p-3 text-xs border ${
          isLight ? "bg-blue-50/60 border-blue-200/80 text-slate-800" : "bg-[#0e1422] border-[#1a253e] text-white"
        }`}>
          <div className={`flex items-center gap-2 font-bold mb-1 ${isLight ? "text-blue-700" : "text-cyan-400"}`}>
            <Sparkles size={13} />
            <span>AI Auto-Personalize</span>
          </div>
          <p className={`text-[11px] leading-relaxed ${isLight ? "text-slate-600" : "text-slate-400"}`}>
            Click any template to preview its multi-scene sequence, swap avatars, and customize scripts in Studio.
          </p>
        </div>
      </div>
    </aside>
  );
}
