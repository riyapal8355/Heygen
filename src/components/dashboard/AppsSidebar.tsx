"use client";

import React, { useState, useEffect } from "react";
import {
  Home,
  PanelLeftClose,
  Link as LinkIcon,
  LayoutGrid,
  RefreshCw,
  Clock,
  Film,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";

interface AppsSidebarProps {
  activeSection: "home" | "integrations" | "outputs" | "translate";
  onSelectSection: (section: "home" | "integrations" | "outputs" | "translate") => void;
  onSeeAllProjects?: () => void;
  onSeeAllOutputs?: () => void;
  onOpenProject?: (projectId: string) => void;
  theme?: "light" | "dark";
}

export function formatTimeAgo(date: Date): string {
  if (isNaN(date.getTime())) return "Recently";
  const diffSec = Math.max(0, Math.floor((Date.now() - date.getTime()) / 1000));
  if (diffSec < 60) return "Just now";
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHours = Math.floor(diffMin / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  if (diffDays < 30) return `${diffDays}d ago`;
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export default function AppsSidebar({
  activeSection,
  onSelectSection,
  onSeeAllProjects,
  onSeeAllOutputs,
  onOpenProject,
  theme = "dark",
}: AppsSidebarProps) {
  const { currentWorkspace } = useAuth();
  const isLight = theme === "light";
  const [recentItems, setRecentItems] = useState<
    Array<{ id: string; title: string; time: string; type: string }>
  >([]);
  const [isLoadingRecents, setIsLoadingRecents] = useState(true);
  const [recentsError, setRecentsError] = useState<string | null>(null);
  const [fetchKey, setFetchKey] = useState(0);

  useEffect(() => {
    if (!currentWorkspace?.id) {
      setIsLoadingRecents(false);
      setRecentItems([]);
      return;
    }
    let cancelled = false;
    setIsLoadingRecents(true);
    setRecentsError(null);

    api.projects
      .list(currentWorkspace.id, { limit: 10 })
      .then((items) => {
        if (cancelled) return;
        const sorted = [...(items || [])].sort((a, b) => {
          const timeA = new Date(a.updated_at || a.created_at || 0).getTime();
          const timeB = new Date(b.updated_at || b.created_at || 0).getTime();
          return timeB - timeA;
        });

        const formatted = sorted.slice(0, 5).map((item) => {
          let typeLabel = "AI Studio";
          if (item.project_type === "agent") typeLabel = "Video Agent";
          else if (item.project_type === "single_scene") typeLabel = "Single Scene";
          else if (item.project_type === "scene_by_scene") typeLabel = "Multi Scene";
          else if (item.project_type === "translate") typeLabel = "Translation";

          const rawDate = new Date(item.updated_at || item.created_at);
          const timeStr = isNaN(rawDate.getTime()) ? "Recently" : formatTimeAgo(rawDate);

          return {
            id: item.id,
            title: item.title?.trim() || "Untitled Video",
            time: timeStr,
            type: typeLabel,
          };
        });

        setRecentItems(formatted);
        setIsLoadingRecents(false);
      })
      .catch(() => {
        if (!cancelled) {
          setRecentsError("Failed to load recents");
          setIsLoadingRecents(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [currentWorkspace?.id, fetchKey]);

  const handleSeeAll = () => {
    if (onSeeAllProjects) {
      onSeeAllProjects();
    } else if (onSeeAllOutputs) {
      onSeeAllOutputs();
    }
  };

  return (
    <aside
      className={`w-56 min-w-56 h-screen flex flex-col justify-between py-5 px-3 select-none transition-colors shrink-0 font-sans ${
        isLight
          ? "bg-white border-r border-slate-200"
          : "bg-[#090d16] border-r border-[#151c2d]"
      }`}
    >
      <div className="flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-2 mb-6">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-lg bg-gradient-to-tr from-purple-500 via-indigo-500 to-cyan-400 flex items-center justify-center shadow-xs">
              <LayoutGrid size={13} className="text-white" />
            </div>
            <span
              className={`text-sm font-bold ${
                isLight ? "text-slate-900" : "text-white"
              }`}
            >
              Apps
            </span>
          </div>
          <button
            type="button"
            title="Collapse sidebar"
            aria-label="Collapse sidebar"
            className={`p-1 rounded-md transition-colors cursor-pointer ${
              isLight
                ? "text-slate-400 hover:text-slate-700 hover:bg-slate-100"
                : "text-slate-400 hover:text-white hover:bg-[#151f33]"
            }`}
          >
            <PanelLeftClose size={17} />
          </button>
        </div>

        {/* Navigation Items */}
        <nav className="flex flex-col gap-1.5" aria-label="Apps Navigation">
          {/* Home Item */}
          <button
            type="button"
            id="apps-sidebar-nav-home"
            data-testid="apps-sidebar-nav-home"
            onClick={() => onSelectSection("home")}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-medium transition-all duration-200 text-left cursor-pointer ${
              isLight
                ? activeSection === "home" || activeSection === "translate"
                  ? "bg-slate-100 text-slate-900 border border-slate-200/80 font-semibold shadow-xs"
                  : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
                : activeSection === "home"
                ? "bg-[#18233c] text-white border border-[#2b3a5d]/50 font-semibold shadow-sm"
                : "text-slate-400 hover:text-slate-200 hover:bg-[#101625]"
            }`}
          >
            <Home
              size={18}
              className={`shrink-0 ${
                isLight
                  ? activeSection === "home" || activeSection === "translate"
                    ? "text-blue-600"
                    : "text-slate-400"
                  : activeSection === "home"
                  ? "text-blue-400"
                  : "text-slate-400"
              }`}
            />
            <span>Home</span>
          </button>

          {/* Integrations Item */}
          <button
            type="button"
            id="apps-sidebar-nav-integrations"
            data-testid="apps-sidebar-nav-integrations"
            onClick={() => onSelectSection("integrations")}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-medium transition-all duration-200 text-left cursor-pointer ${
              isLight
                ? activeSection === "integrations"
                  ? "bg-slate-100 text-slate-900 border border-slate-200/80 font-semibold shadow-xs"
                  : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
                : activeSection === "integrations"
                ? "bg-[#18233c] text-white border border-[#2b3a5d]/50 font-semibold shadow-sm"
                : "text-slate-400 hover:text-slate-200 hover:bg-[#101625]"
            }`}
          >
            <LinkIcon
              size={18}
              className={`shrink-0 ${
                isLight
                  ? activeSection === "integrations"
                    ? "text-blue-600"
                    : "text-slate-400"
                  : activeSection === "integrations"
                  ? "text-blue-400"
                  : "text-slate-400"
              }`}
            />
            <span>Integrations</span>
          </button>
        </nav>

        {/* Divider */}
        <div
          className={`h-[1px] my-5 mx-1 ${
            isLight ? "bg-slate-200" : "bg-[#151c2d]"
          }`}
        />

        {/* RECENTS Section */}
        <div className="px-1" id="apps-sidebar-recents" data-testid="apps-sidebar-recents">
          <div className="flex items-center justify-between mb-2.5">
            <span
              className={`text-[10px] font-bold uppercase tracking-wider flex items-center gap-1 ${
                isLight ? "text-slate-400" : "text-slate-500"
              }`}
            >
              <Clock size={11} />
              <span>Recents</span>
            </span>
            <button
              id="apps-recents-see-all-btn"
              data-testid="apps-recents-see-all-btn"
              type="button"
              onClick={handleSeeAll}
              className={`text-[10px] font-bold cursor-pointer transition-colors ${
                isLight
                  ? "text-slate-500 hover:text-slate-900"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              See all ›
            </button>
          </div>

          <div className="space-y-2">
            {isLoadingRecents ? (
              <div
                data-testid="apps-recents-loading"
                className="space-y-2 animate-pulse py-1"
              >
                <div
                  className={`h-12 rounded-xl ${
                    isLight ? "bg-slate-100" : "bg-[#0e1422]"
                  }`}
                />
                <div
                  className={`h-12 rounded-xl ${
                    isLight ? "bg-slate-100" : "bg-[#0e1422]"
                  }`}
                />
              </div>
            ) : recentsError ? (
              <div
                data-testid="apps-recents-error"
                className={`p-2.5 rounded-xl text-center border ${
                  isLight
                    ? "bg-rose-50 border-rose-200 text-rose-700"
                    : "bg-rose-950/30 border-rose-900/50 text-rose-300"
                }`}
              >
                <p className="text-[10px] font-medium mb-1.5">{recentsError}</p>
                <button
                  type="button"
                  data-testid="apps-recents-retry-btn"
                  onClick={() => setFetchKey((k) => k + 1)}
                  className="inline-flex items-center gap-1 text-[10px] font-bold underline cursor-pointer hover:opacity-80"
                >
                  <RefreshCw size={10} />
                  <span>Retry</span>
                </button>
              </div>
            ) : recentItems.length === 0 ? (
              <p
                data-testid="apps-recents-empty"
                className={`text-[10px] px-1 py-1 italic ${
                  isLight ? "text-slate-400" : "text-slate-500"
                }`}
              >
                No recent projects
              </p>
            ) : (
              recentItems.map((item) => (
                <div
                  key={item.id}
                  id={`apps-recent-project-${item.id}`}
                  data-testid={`recent-project-card-${item.id}`}
                  onClick={() => {
                    if (onOpenProject) {
                      onOpenProject(item.id);
                    } else {
                      handleSeeAll();
                    }
                  }}
                  className={`p-2.5 rounded-xl cursor-pointer transition-all shadow-xs group ${
                    isLight
                      ? "bg-slate-50 hover:bg-slate-100/90 border border-slate-200/70"
                      : "bg-[#0e1422] hover:bg-[#131b2e] border border-[#1a253e] hover:border-cyan-500/40"
                  }`}
                >
                  <h4
                    className={`text-xs font-bold truncate transition-colors ${
                      isLight
                        ? "text-slate-800 group-hover:text-blue-600"
                        : "text-white group-hover:text-cyan-300"
                    }`}
                  >
                    {item.title}
                  </h4>
                  <p
                    className={`text-[10px] mt-0.5 ${
                      isLight ? "text-slate-400" : "text-slate-400"
                    }`}
                  >
                    {item.time} · {item.type}
                  </p>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </aside>
  );
}
