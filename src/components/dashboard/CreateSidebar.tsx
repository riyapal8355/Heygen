"use client";

import React, { useState, useEffect } from "react";
import {
  Home,
  Bot,
  Clapperboard,
  Image as ImageIcon,
  Languages,
  PanelLeftClose,
  PanelLeftOpen,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { useTheme } from "@/context/ThemeContext";
import { api } from "@/lib/api";

interface CreateSidebarProps {
  activeSection?: string;
  onSelectSection?: (section: string) => void;
  onSeeAllRecents?: () => void;
  onOpenProject?: (projectId: string) => void;
  theme?: "light" | "dark";
}

function formatTimeAgo(date: Date): string {
  const diffSec = Math.max(0, Math.floor((Date.now() - date.getTime()) / 1000));
  if (diffSec < 60) return "Just now";
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHours = Math.floor(diffMin / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  return `${diffDays}d ago`;
}

export default function CreateSidebar({
  activeSection = "home",
  onSelectSection,
  onSeeAllRecents,
  onOpenProject,
  theme: propTheme,
}: CreateSidebarProps) {
  const { currentWorkspace } = useAuth();
  const { theme: contextTheme } = useTheme();
  const theme = propTheme || contextTheme;
  const [isCollapsed, setIsCollapsed] = useState(false);
  const currentActive = activeSection;
  const isLight = theme === "light";

  const menuItems = [
    { id: "home", label: "Home", icon: Home },
    { id: "video_agent", label: "Video agent", icon: Bot },
    { id: "scene_by_scene", label: "Scene by scene", icon: Clapperboard },
    { id: "single_scene", label: "Single scene", icon: ImageIcon },
    { id: "translate", label: "Translate", icon: Languages },
  ];

  const [recentItems, setRecentItems] = useState<
    Array<{
      id: string;
      title: string;
      isDraft: boolean;
      time: string;
      source: string;
    }>
  >([]);

  useEffect(() => {
    if (!currentWorkspace?.id) return;
    let cancelled = false;

    api.projects
      .list(currentWorkspace.id, { limit: 5 })
      .then((items) => {
        if (cancelled) return;
        if (Array.isArray(items)) {
          const mapped = items.slice(0, 5).map((p: any) => {
            const date = new Date(p.updated_at || p.created_at || Date.now());
            return {
              id: p.id,
              title: p.title || "Untitled Video",
              isDraft: p.status === "draft",
              time: formatTimeAgo(date),
              source: p.project_type === "translation" ? "Translation" : "AI Studio",
            };
          });
          setRecentItems(mapped);
        }
      })
      .catch(() => {
        // preserve empty state
      });

    return () => {
      cancelled = true;
    };
  }, [currentWorkspace?.id]);

  const handleSelect = (id: string) => {
    if (onSelectSection) onSelectSection(id);
  };

  if (isCollapsed) {
    return (
      <div
        className={`h-screen py-4 px-2 flex flex-col items-center transition-colors shrink-0 ${
          isLight ? "bg-white border-r border-slate-200" : "bg-[#090d16] border-r border-[#1b2940]"
        }`}
      >
        <button
          onClick={() => setIsCollapsed(false)}
          className={`p-2 rounded-lg transition-colors cursor-pointer ${
            isLight
              ? "text-slate-400 hover:text-slate-700 hover:bg-slate-100"
              : "text-slate-400 hover:text-white hover:bg-[#151f33]"
          }`}
          title="Expand sidebar"
        >
          <PanelLeftOpen size={18} />
        </button>
      </div>
    );
  }

  return (
    <aside
      className={`w-56 min-w-56 h-screen flex flex-col justify-between py-5 px-3 select-none transition-colors shrink-0 font-sans ${
        isLight ? "bg-white border-r border-slate-200" : "bg-[#090d16] border-r border-[#1b2940]"
      }`}
    >
      <div className="flex flex-col">
        {/* Sidebar Header */}
        <div className="flex items-center justify-between px-2 mb-6">
          <span
            className={`font-bold text-sm tracking-wide ${
              isLight ? "text-slate-900" : "text-white"
            }`}
          >
            Create
          </span>
          <button
            onClick={() => setIsCollapsed(true)}
            className={`p-1 rounded-md transition-colors cursor-pointer ${
              isLight
                ? "text-slate-400 hover:text-slate-700 hover:bg-slate-100"
                : "text-slate-400 hover:text-white hover:bg-[#151f33]"
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
                onClick={() => handleSelect(item.id)}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-medium transition-all duration-200 cursor-pointer text-left ${
                  isLight
                    ? isActive
                      ? "bg-[#eef4ff] text-slate-900 border border-blue-200/70 font-semibold shadow-xs"
                      : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
                    : isActive
                    ? "bg-[#18233c] text-white border border-[#2b3a5d]/50 font-semibold shadow-sm"
                    : "text-slate-300 hover:text-white hover:bg-[#101828]"
                }`}
              >
                <Icon
                  size={18}
                  className={`shrink-0 ${
                    isLight
                      ? isActive
                        ? "text-[#2563eb]"
                        : "text-slate-500"
                      : isActive
                      ? "text-cyan-400"
                      : "text-slate-400"
                  }`}
                />
                <span>{item.label}</span>
              </button>
            );
          })}
        </div>

        {/* Divider */}
        <div
          className={`h-[1px] my-5 mx-1 ${
            isLight ? "bg-slate-200" : "bg-[#1b2940]"
          }`}
        ></div>

        {/* RECENTS Section */}
        <div className="px-1">
          <div className="flex items-center justify-between mb-2.5">
            <span
              className={`text-[10px] font-bold uppercase tracking-wider ${
                isLight ? "text-slate-400" : "text-slate-500"
              }`}
            >
              Recents
            </span>
            <button
              type="button"
              onClick={onSeeAllRecents}
              className={`text-[10px] font-bold cursor-pointer transition-colors ${
                isLight
                  ? "text-slate-400 hover:text-slate-700"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              See all &gt;
            </button>
          </div>

          <div className="space-y-2">
            {recentItems.length === 0 ? (
              <p
                className={`text-[10px] py-2 px-1 ${
                  isLight ? "text-slate-400" : "text-slate-500"
                }`}
              >
                No recent projects
              </p>
            ) : (
              recentItems.map((item) => (
                <div
                  key={item.id}
                  onClick={() => {
                    if (onOpenProject) onOpenProject(item.id);
                    else if (onSeeAllRecents) onSeeAllRecents();
                  }}
                  className={`p-2.5 rounded-xl cursor-pointer transition-all shadow-xs group ${
                    isLight
                      ? "bg-slate-50 hover:bg-slate-100/90 border border-slate-200/70"
                      : "bg-[#0e1422] hover:bg-[#131b2e] border border-[#1b2940] hover:border-cyan-500/40"
                  }`}
                >
                <div className="flex items-center gap-1.5">
                  <h4
                    className={`text-xs font-bold truncate transition-colors ${
                      isLight
                        ? "text-slate-800 group-hover:text-blue-600"
                        : "text-white group-hover:text-cyan-300"
                    }`}
                  >
                    {item.title}
                  </h4>
                  {item.isDraft && (
                    <span
                      className={`text-[9px] font-bold uppercase px-1 rounded ${
                        isLight
                          ? "bg-slate-200 text-slate-600"
                          : "bg-slate-800 text-slate-300"
                      }`}
                    >
                      DRAFT
                    </span>
                  )}
                </div>
                <p
                  className={`text-[10px] mt-0.5 ${
                    isLight ? "text-slate-400" : "text-slate-400"
                  }`}
                >
                  {item.time} • {item.source}
                </p>
              </div>
            )))}
          </div>
        </div>
      </div>
    </aside>
  );
}
