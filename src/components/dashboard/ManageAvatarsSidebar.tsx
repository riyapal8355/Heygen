"use client";

import React, { useState, useEffect } from "react";
import {
  User,
  Sparkles,
  Volume2,
  PanelLeftClose,
  PanelLeftOpen,
} from "lucide-react";
import { useTheme } from "@/context/ThemeContext";

interface ManageAvatarsSidebarProps {
  activeSection?: "avatars" | "design_look" | "voices";
  onSelectSection?: (section: "avatars" | "design_look" | "voices") => void;
}

export default function ManageAvatarsSidebar({
  activeSection = "voices",
  onSelectSection,
}: ManageAvatarsSidebarProps) {
  const { theme } = useTheme();
  const isLight = theme === "light";
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [currentActive, setCurrentActive] = useState(activeSection);

  useEffect(() => {
    setCurrentActive(activeSection);
  }, [activeSection]);

  const menuItems = [
    { id: "avatars" as const, label: "Avatars", icon: User },
    { id: "design_look" as const, label: "Design a look", icon: Sparkles },
    { id: "voices" as const, label: "Voices", icon: Volume2 },
  ];

  const handleSelect = (id: "avatars" | "design_look" | "voices") => {
    setCurrentActive(id);
    if (onSelectSection) onSelectSection(id);
  };

  if (isCollapsed) {
    return (
      <div className={`h-screen py-4 px-2 flex flex-col items-center select-none transition-colors ${
        isLight ? "bg-white border-r border-slate-200" : "bg-[#090d16] border-r border-[#151c2d]"
      }`}>
        <button
          onClick={() => setIsCollapsed(false)}
          className={`p-2 rounded-lg transition-colors cursor-pointer ${
            isLight ? "text-slate-400 hover:text-slate-900 hover:bg-slate-100" : "text-slate-400 hover:text-white hover:bg-[#151f33]"
          }`}
          title="Expand sidebar"
        >
          <PanelLeftOpen size={18} />
        </button>
      </div>
    );
  }

  return (
    <div className={`w-56 min-w-56 h-screen flex flex-col py-5 px-3 select-none transition-colors ${
      isLight ? "bg-white border-r border-slate-200" : "bg-[#090d16] border-r border-[#151c2d]"
    }`}>
      {/* Sidebar Header */}
      <div className="flex items-center justify-between px-2 mb-6">
        <span className={`font-semibold text-sm tracking-wide ${
          isLight ? "text-slate-900" : "text-white"
        }`}>
          Manage Avatars
        </span>
        <button
          onClick={() => setIsCollapsed(true)}
          className={`p-1 rounded-md transition-colors cursor-pointer ${
            isLight ? "text-slate-400 hover:text-slate-900 hover:bg-slate-100" : "text-slate-400 hover:text-white hover:bg-[#151f33]"
          }`}
          title="Collapse sidebar"
        >
          <PanelLeftClose size={17} />
        </button>
      </div>

      {/* Navigation Links */}
      <div className="flex flex-col gap-1.5">
        {menuItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentActive === item.id;
          return (
            <button
              key={item.id}
              id={`manage-avatars-nav-${item.id}`}
              data-testid={`manage-avatars-nav-${item.id}`}
              onClick={() => handleSelect(item.id)}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-medium transition-all duration-200 cursor-pointer ${
                isActive
                  ? isLight
                    ? "bg-[#eef4ff] text-slate-900 border border-blue-200/70 font-semibold shadow-xs"
                    : "bg-[#18233c] text-white border border-[#2b3a5d]/50 font-semibold shadow-sm"
                  : isLight
                  ? "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
                  : "text-slate-400 hover:text-slate-200 hover:bg-[#101625]"
              }`}
            >
              <Icon
                size={18}
                className={isActive ? (isLight ? "text-blue-600" : "text-blue-400") : (isLight ? "text-slate-400" : "text-slate-400")}
              />
              <span>{item.label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
