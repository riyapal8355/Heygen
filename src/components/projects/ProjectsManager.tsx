"use client";

import React, { useState, useMemo, useEffect, useCallback } from "react";
import {
  Video,
  Search,
  Filter,
  Calendar,
  ArrowUpDown,
  MoreHorizontal,
  Trash2,
  Edit2,
  Copy,
  PlusSquare,
  Users,
  FolderInput,
  CheckSquare,
  Square,
  X,
  Sparkles,
  Gem,
  Check,
  ArrowDown,
  ArrowUp,
  Grid,
  List,
  Clock,
  Plus,
} from "lucide-react";
import AskRhysWidget from "../dashboard/AskRhysWidget";
import { useAuth } from "@/context/AuthContext";
import { useTheme } from "@/context/ThemeContext";
import { api } from "@/lib/api";

interface ProjectItem {
  id: string;
  title: string;
  type: "avatar_video" | "agent" | "translations" | "apps" | "assets";
  badgeLabel: string;
  status: "Draft" | "Rendered" | "Processing";
  createdAt: string;
  createdTimestamp: number;
  lastModifiedTimestamp: number;
  source: string;
  creator: string;
  category?: "Batch Translations" | "Proofread" | "Translations" | "Standard";
}

interface ProjectsManagerProps {
  activeSection?: "my_projects" | "trash" | string;
  onOpenStudio?: (projectId?: string) => void;
}

export default function ProjectsManager({
  activeSection = "my_projects",
  onOpenStudio,
}: ProjectsManagerProps) {
  const { theme } = useTheme();
  const isLight = theme === "light";

  // Navigation tabs
  const [activeTab, setActiveTab] = useState<
    "my_projects" | "avatar_video" | "agent" | "translations" | "apps" | "assets"
  >("my_projects");

  // Search
  const [searchQuery, setSearchQuery] = useState("");

  // Dropdown states: "filter" | "view" | "sort" | null
  const [activeDropdown, setActiveDropdown] = useState<"filter" | "view" | "sort" | null>(null);

  // Close active dropdown when clicking outside or pressing Escape
  useEffect(() => {
    if (!activeDropdown) return;
    const handleDocumentClick = () => {
      setActiveDropdown(null);
    };
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setActiveDropdown(null);
      }
    };
    window.addEventListener("click", handleDocumentClick);
    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("click", handleDocumentClick);
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [activeDropdown]);

  // View state: "date" | "grid" | "list"
  const [viewMode, setViewMode] = useState<"date" | "grid" | "list">("date");

  // Sort state
  const [sortBy, setSortBy] = useState<"last_modified" | "creation_date">("last_modified");
  const [sortDirection, setSortDirection] = useState<"desc" | "asc">("desc");

  // Filters state
  const [selectedFilters, setSelectedFilters] = useState<string[]>([]);

  // Selection & context menu
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [openMenuId, setOpenMenuId] = useState<string | null>(null);

  // Inline rename
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [newTitle, setNewTitle] = useState("");

  // Backend workspace & data
  const { currentWorkspace, user } = useAuth();
  const [projects, setProjects] = useState<ProjectItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  const loadProjects = useCallback(async () => {
    if (!currentWorkspace?.id) return;
    setIsLoading(true);
    setLoadError(null);
    try {
      const resp = await api.projects.list(currentWorkspace.id);
      const mapped: ProjectItem[] = resp.map((p) => {
        let mappedType: ProjectItem["type"] = "avatar_video";
        if (p.project_type === "agent") mappedType = "agent";
        else if (p.project_type === "translation") mappedType = "translations";
        else if (p.project_type === "apps") mappedType = "apps";
        else if (p.project_type === "assets") mappedType = "assets";

        let badgeLabel = "Avatar Video";
        if (mappedType === "translations") badgeLabel = "Translations";
        else if (mappedType === "agent") badgeLabel = "Agent";
        else if (mappedType === "apps") badgeLabel = "Apps";

        const cTime = new Date(p.created_at).getTime() || Date.now();
        const uTime = new Date(p.updated_at).getTime() || cTime;

        return {
          id: p.id,
          title: p.title || "Untitled Video",
          type: mappedType,
          badgeLabel,
          status: p.status === "ready" ? "Rendered" : p.status === "processing" ? "Processing" : "Draft",
          createdAt: new Date(p.created_at).toLocaleDateString(),
          createdTimestamp: cTime,
          lastModifiedTimestamp: uTime,
          source: "HeyZen Studio",
          creator: user?.name || "Creator",
          category: mappedType === "translations" ? "Translations" : "Standard",
        };
      });
      setProjects(mapped);
    } catch (err: any) {
      setLoadError(err?.message || "Failed to load projects");
    } finally {
      setIsLoading(false);
    }
  }, [currentWorkspace?.id, user?.name]);

  useEffect(() => {
    loadProjects();
  }, [loadProjects]);

  const [trashProjects, setTrashProjects] = useState<ProjectItem[]>([]);

  // Tab definitions
  const tabs = [
    { id: "my_projects", label: "My Projects", placeholder: "Search Projects" },
    { id: "avatar_video", label: "Avatar Video", placeholder: "Search Avatar Video" },
    { id: "agent", label: "Agent", placeholder: "Search Agent" },
    { id: "translations", label: "Translations", placeholder: "Search Translations" },
    { id: "apps", label: "Apps", placeholder: "Search Apps" },
    { id: "assets", label: "Assets", placeholder: "Search Assets" },
  ];

  const currentTabObj = tabs.find((t) => t.id === activeTab) || tabs[0];

  // Filter and sort items
  const filteredAndSortedProjects = useMemo(() => {
    let result = projects.filter((p) => {
      // Tab matching
      const matchesTab =
        activeTab === "my_projects"
          ? true
          : p.type === activeTab;

      // Search matching
      const matchesSearch =
        !searchQuery.trim() ||
        p.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        p.source.toLowerCase().includes(searchQuery.toLowerCase());

      // Filter checkbox matching
      const matchesFilters =
        selectedFilters.length === 0 ||
        (p.category && selectedFilters.includes(p.category));

      return matchesTab && matchesSearch && matchesFilters;
    });

    // Sorting
    result.sort((a, b) => {
      const timeA = sortBy === "last_modified" ? a.lastModifiedTimestamp : a.createdTimestamp;
      const timeB = sortBy === "last_modified" ? b.lastModifiedTimestamp : b.createdTimestamp;
      return sortDirection === "desc" ? timeB - timeA : timeA - timeB;
    });

    return result;
  }, [projects, activeTab, searchQuery, selectedFilters, sortBy, sortDirection]);

  const toggleFilter = (filterName: string) => {
    setSelectedFilters((prev) =>
      prev.includes(filterName)
        ? prev.filter((f) => f !== filterName)
        : [...prev, filterName]
    );
  };

  const toggleSelect = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]
    );
  };

  const handleCopyId = (id: string) => {
    navigator.clipboard?.writeText(id);
    alert(`Project ID "${id}" copied to clipboard!`);
    setOpenMenuId(null);
  };

  const handleEditAsNew = async (p: ProjectItem) => {
    setOpenMenuId(null);
    if (!currentWorkspace?.id) {
      if (onOpenStudio) onOpenStudio();
      return;
    }
    try {
      const newProj = await api.projects.create(currentWorkspace.id, {
        title: `${p.title} (Copy)`,
      });
      try {
        const origVer = await api.projects.getLatestVersion(currentWorkspace.id, p.id);
        if (origVer?.document) {
          await api.projects.createVersion(currentWorkspace.id, newProj.id, {
            expected_revision: 1,
            document: origVer.document,
            source: "duplicate",
          });
        }
      } catch {
        // initial version revision 1 already created
      }
      if (onOpenStudio) onOpenStudio(newProj.id);
    } catch (err) {
      console.error("Failed to duplicate project", err);
    }
  };

  const handleStartRename = (p: ProjectItem) => {
    setRenamingId(p.id);
    setNewTitle(p.title);
    setOpenMenuId(null);
  };

  const handleSaveRename = async (id: string) => {
    if (newTitle.trim()) {
      if (currentWorkspace?.id) {
        try {
          await api.projects.update(currentWorkspace.id, id, { title: newTitle.trim() });
        } catch {
          // ignore
        }
      }
      setProjects(
        projects.map((p) =>
          p.id === id
            ? { ...p, title: newTitle.trim(), lastModifiedTimestamp: Date.now() }
            : p
        )
      );
    }
    setRenamingId(null);
  };

  const handleDeleteProject = async (id: string, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    if (currentWorkspace?.id) {
      try {
        await api.projects.delete(currentWorkspace.id, id);
      } catch {
        // ignore
      }
    }
    const item = projects.find((p) => p.id === id);
    if (item) {
      setProjects(projects.filter((p) => p.id !== id));
      setTrashProjects([...trashProjects, item]);
    }
    setOpenMenuId(null);
  };

  const handleRestoreProject = (id: string) => {
    const item = trashProjects.find((p) => p.id === id);
    if (item) {
      setTrashProjects(trashProjects.filter((p) => p.id !== id));
      setProjects([...projects, item]);
    }
  };

  const handleCreateProject = async () => {
    if (!currentWorkspace?.id) return;
    try {
      const newProj = await api.projects.create(currentWorkspace.id, {
        title: "Untitled Video Project",
        project_type: "avatar_video",
        aspect_ratio: "16:9",
      });
      await loadProjects();
      if (onOpenStudio) onOpenStudio(newProj.id);
    } catch (err: any) {
      alert(err?.message || "Failed to create project");
    }
  };

  const handleCreateSampleTranslation = async () => {
    if (!currentWorkspace?.id) return;
    try {
      const newProj = await api.projects.create(currentWorkspace.id, {
        title: "French & Spanish Localized Video",
        project_type: "translation",
        aspect_ratio: "16:9",
      });
      await loadProjects();
      if (onOpenStudio) onOpenStudio(newProj.id);
    } catch (err: any) {
      alert(err?.message || "Failed to create sample video");
    }
  };

  return (
    <div
      onClick={() => {
        setOpenMenuId(null);
        setActiveDropdown(null);
      }}
      className={`flex-1 h-screen overflow-y-auto ${isLight ? "bg-slate-50 text-slate-900" : "bg-[#07090e] text-slate-100"} flex flex-col font-sans select-none relative`}
    >
      {/* 1. TOP HEADER & TABS BAR */}
      <div className={`w-full px-10 pt-7 pb-2 border-b ${isLight ? "border-slate-200 bg-white" : "border-[#141b2c]"} z-20`}>
        <div className="flex items-center justify-between mb-4">
          <h1 className={`text-2xl md:text-3xl font-extrabold ${isLight ? "text-slate-900" : "text-white"} tracking-tight`}>
            {activeSection === "trash" ? "Trash" : "Projects"}
          </h1>

          {/* Right Action Bar (Search, Filter, Date/View, Sort + Ask Rhys) */}
          <div className="flex items-center gap-2.5 relative">
            {activeSection !== "trash" && (
              <button
                onClick={handleCreateProject}
                className="bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-bold text-xs px-3.5 py-1.5 rounded-full shadow-md shadow-cyan-500/20 hover:shadow-cyan-500/30 transition-all flex items-center gap-1.5 cursor-pointer shrink-0"
              >
                <Plus size={13} strokeWidth={3} />
                <span>Create Video</span>
              </button>
            )}
            {/* Search Input Box */}
            <div className="relative flex items-center">
              <Search
                size={14}
                className="absolute left-3.5 text-slate-400 pointer-events-none"
              />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder={currentTabObj.placeholder}
                className={`w-52 md:w-60 ${
                  isLight
                    ? "bg-slate-100 hover:bg-slate-200/70 focus:bg-white border-slate-300 text-slate-900 placeholder:text-slate-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
                    : "bg-[#111728] hover:bg-[#151f36] focus:bg-[#151f36] border-[#1e2a44] text-white placeholder-slate-400 focus:border-cyan-500 focus:ring-2 focus:ring-cyan-500/20"
                } border rounded-full pl-9 pr-8 py-1.5 text-xs transition-all outline-none`}
              />
              {searchQuery ? (
                <button
                  onClick={() => setSearchQuery("")}
                  className={`absolute right-2.5 ${isLight ? "text-slate-400 hover:text-slate-700" : "text-slate-400 hover:text-white"} p-0.5 rounded-full transition-colors`}
                >
                  <X size={12} />
                </button>
              ) : (
                <div className={`absolute right-2.5 w-4 h-4 rounded-full ${isLight ? "bg-slate-200 text-slate-500" : "bg-slate-700/50 text-slate-400"} flex items-center justify-center`}>
                  <X size={10} />
                </div>
              )}
            </div>

            {/* 1st Action Icon: Filter Button */}
            <div className="relative">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setActiveDropdown(activeDropdown === "filter" ? null : "filter");
                }}
                className={`w-9 h-9 rounded-full border flex items-center justify-center transition-colors cursor-pointer ${
                  activeDropdown === "filter" || selectedFilters.length > 0
                    ? isLight
                      ? "bg-blue-50 border-blue-500 text-blue-600 shadow-sm"
                      : "bg-[#162035] border-cyan-500 text-cyan-400 shadow-md shadow-cyan-950"
                    : isLight
                    ? "bg-white hover:bg-slate-100 border-slate-200 text-slate-600 hover:text-slate-900"
                    : "bg-[#0c111e] hover:bg-[#151f36] border-[#1c2740] text-slate-400 hover:text-white"
                }`}
                title="Filters"
              >
                <Filter size={15} />
              </button>

              {/* Filter Popover */}
              {activeDropdown === "filter" && (
                <div
                  onClick={(e) => e.stopPropagation()}
                  className={`absolute top-11 right-0 w-48 ${isLight ? "bg-white border-slate-200 text-slate-800 shadow-2xl" : "bg-[#0d1222] border-[#22304f] text-slate-300 shadow-2xl"} border rounded-2xl p-3 z-50 animate-in fade-in zoom-in-95 duration-150 backdrop-blur-xl`}
                >
                  <div className={`text-[11px] font-semibold ${isLight ? "text-slate-500" : "text-slate-400"} mb-2 px-1`}>
                    Filters
                  </div>

                  <div className="space-y-2">
                    {[
                      { id: "Batch Translations", label: "Batch Translations" },
                      { id: "Proofread", label: "Proofread" },
                      { id: "Translations", label: "Translations" },
                    ].map((item) => {
                      const isChecked = selectedFilters.includes(item.id);
                      return (
                        <label
                          key={item.id}
                          onClick={() => toggleFilter(item.id)}
                          className={`flex items-center gap-2.5 px-1 py-1 text-xs ${isLight ? "text-slate-700 hover:text-slate-900 hover:bg-slate-100" : "text-slate-300 hover:text-white hover:bg-[#162035]"} rounded-lg cursor-pointer transition-colors`}
                        >
                          <div
                            className={`w-4 h-4 rounded border flex items-center justify-center transition-all ${
                              isChecked
                                ? "bg-cyan-500 border-cyan-500 text-slate-950 font-bold"
                                : isLight
                                ? "border-slate-300 bg-white"
                                : "border-slate-600 bg-[#121828]"
                            }`}
                          >
                            {isChecked && <Check size={12} strokeWidth={3} />}
                          </div>
                          <span className="text-xs font-medium">{item.label}</span>
                        </label>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>

            {/* 2nd Action Icon: View Button (Date / Grid / List) */}
            <div className="relative">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setActiveDropdown(activeDropdown === "view" ? null : "view");
                }}
                className={`w-9 h-9 rounded-full border flex items-center justify-center transition-colors cursor-pointer ${
                  activeDropdown === "view"
                    ? "bg-[#162035] border-cyan-500 text-cyan-400 shadow-md shadow-cyan-950"
                    : "bg-[#0c111e] hover:bg-[#151f36] border-[#1c2740] text-slate-400 hover:text-white"
                }`}
                title="View Format"
              >
                <Calendar size={15} />
              </button>

              {/* View Popover */}
              {activeDropdown === "view" && (
                <div
                  onClick={(e) => e.stopPropagation()}
                  className="absolute top-11 right-0 w-44 bg-[#0d1222] border border-[#22304f] rounded-2xl shadow-2xl p-2.5 z-50 animate-in fade-in zoom-in-95 duration-150 backdrop-blur-xl"
                >
                  <div className="space-y-1">
                    {[
                      { id: "date", label: "Date View" },
                      { id: "grid", label: "Grid View" },
                      { id: "list", label: "List View" },
                    ].map((item) => {
                      const isSelected = viewMode === item.id;
                      return (
                        <button
                          key={item.id}
                          onClick={() => {
                            setViewMode(item.id as any);
                            setActiveDropdown(null);
                          }}
                          className={`w-full flex items-center gap-2.5 px-2.5 py-2 rounded-xl text-xs font-medium transition-colors text-left cursor-pointer ${
                            isSelected
                              ? "bg-[#162035] text-white font-semibold"
                              : "text-slate-400 hover:bg-[#141b2c] hover:text-slate-200"
                          }`}
                        >
                          <div
                            className={`w-4 h-4 rounded-full flex items-center justify-center transition-all ${
                              isSelected
                                ? "bg-cyan-500 text-slate-950"
                                : "border border-slate-600 bg-[#121828]"
                            }`}
                          >
                            {isSelected && <Check size={11} strokeWidth={3} />}
                          </div>
                          <span>{item.label}</span>
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>

            {/* 3rd Action Icon: Sort Button */}
            <div className="relative">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setActiveDropdown(activeDropdown === "sort" ? null : "sort");
                }}
                className={`w-9 h-9 rounded-full border flex items-center justify-center transition-colors cursor-pointer ${
                  activeDropdown === "sort"
                    ? "bg-[#162035] border-cyan-500 text-cyan-400 shadow-md shadow-cyan-950"
                    : "bg-[#0c111e] hover:bg-[#151f36] border-[#1c2740] text-slate-400 hover:text-white"
                }`}
                title="Sort Options"
              >
                <ArrowUpDown size={15} />
              </button>

              {/* Sort Popover */}
              {activeDropdown === "sort" && (
                <div
                  onClick={(e) => e.stopPropagation()}
                  className="absolute top-11 right-0 w-52 bg-[#0d1222] border border-[#22304f] rounded-2xl shadow-2xl p-2.5 z-50 animate-in fade-in zoom-in-95 duration-150 backdrop-blur-xl"
                >
                  <div className="space-y-1">
                    {/* Sort By Field */}
                    {[
                      { id: "last_modified", label: "By Last Modified" },
                      { id: "creation_date", label: "By Creation Date" },
                    ].map((item) => {
                      const isSelected = sortBy === item.id;
                      return (
                        <button
                          key={item.id}
                          onClick={() => {
                            setSortBy(item.id as any);
                            setActiveDropdown(null);
                          }}
                          className={`w-full flex items-center gap-2.5 px-2.5 py-2 rounded-xl text-xs font-medium transition-colors text-left cursor-pointer ${
                            isSelected
                              ? "bg-[#162035] text-white font-semibold"
                              : "text-slate-400 hover:bg-[#141b2c] hover:text-slate-200"
                          }`}
                        >
                          <div
                            className={`w-4 h-4 rounded-full flex items-center justify-center transition-all ${
                              isSelected
                                ? "bg-cyan-500 text-slate-950"
                                : "border border-slate-600 bg-[#121828]"
                            }`}
                          >
                            {isSelected && <Check size={11} strokeWidth={3} />}
                          </div>
                          <span>{item.label}</span>
                        </button>
                      );
                    })}

                    {/* Divider Line */}
                    <div className="h-[1px] bg-[#1a253c] my-1.5" />

                    {/* Direction */}
                    {[
                      { id: "desc", label: "Descending", icon: ArrowDown },
                      { id: "asc", label: "Ascending", icon: ArrowUp },
                    ].map((item) => {
                      const isSelected = sortDirection === item.id;
                      const Icon = item.icon;
                      return (
                        <button
                          key={item.id}
                          onClick={() => {
                            setSortDirection(item.id as any);
                            setActiveDropdown(null);
                          }}
                          className={`w-full flex items-center justify-between px-2.5 py-2 rounded-xl text-xs font-medium transition-colors text-left cursor-pointer ${
                            isSelected
                              ? "bg-[#162035] text-white font-semibold"
                              : "text-slate-400 hover:bg-[#141b2c] hover:text-slate-200"
                          }`}
                        >
                          <div className="flex items-center gap-2.5">
                            <div
                              className={`w-4 h-4 rounded-full flex items-center justify-center transition-all ${
                                isSelected
                                  ? "bg-cyan-500 text-slate-950"
                                  : "border border-slate-600 bg-[#121828]"
                              }`}
                            >
                              {isSelected && <Check size={11} strokeWidth={3} />}
                            </div>
                            <span>{item.label}</span>
                          </div>
                          <Icon size={14} className="text-slate-400" />
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>

            {/* Ask Rhys Widget */}
            <div className="ml-2">
              <AskRhysWidget initialBanner={true} />
            </div>
          </div>
        </div>

        {/* Sub-Tabs Row (Exact Match: My Projects, Avatar Video, Agent, Translations, Apps, Assets) */}
        {activeSection === "my_projects" && (
          <div className="flex items-center gap-7 text-xs font-bold pt-1">
            {tabs.map((tab) => {
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => {
                    setActiveTab(tab.id as any);
                    setActiveDropdown(null);
                  }}
                  className={`pb-2.5 transition-colors cursor-pointer relative ${
                    isActive
                      ? (isLight ? "text-slate-900 font-extrabold" : "text-white font-extrabold")
                      : (isLight ? "text-slate-600 hover:text-slate-900" : "text-slate-400 hover:text-slate-200")
                  }`}
                >
                  {tab.label}
                  {isActive && (
                    <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-cyan-500 rounded-full shadow-sm shadow-cyan-400" />
                  )}
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* 2. MAIN WORKSPACE */}
      <div className="max-w-7xl w-full mx-auto px-10 py-6 flex-1 flex flex-col justify-between pb-16">
        {activeSection === "trash" ? (
          /* TRASH VIEW */
          <div>
            <h2 className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-4">
              Deleted Items ({trashProjects.length})
            </h2>

            {trashProjects.length === 0 ? (
              <div className="text-center py-24 text-slate-500 text-xs font-semibold">
                Trash is empty
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {trashProjects.map((p) => (
                  <div
                    key={p.id}
                    className={`rounded-3xl p-4 flex items-center justify-between border ${
                      isLight ? "bg-white border-slate-200 shadow-sm" : "bg-[#0c111e] border-[#1c2740]"
                    }`}
                  >
                    <div>
                      <h4 className={`text-xs font-bold ${isLight ? "text-slate-900" : "text-white"}`}>{p.title}</h4>
                      <p className={`text-[10px] ${isLight ? "text-slate-500" : "text-slate-400"}`}>{p.source}</p>
                    </div>
                    <button
                      onClick={() => handleRestoreProject(p.id)}
                      className={`px-3 py-1 rounded-xl text-xs font-semibold cursor-pointer ${
                        isLight
                          ? "bg-cyan-50 hover:bg-cyan-100 border border-cyan-200 text-cyan-700"
                          : "bg-[#151f36] hover:bg-[#1d2b4a] border border-[#243354] text-cyan-400"
                      }`}
                    >
                      Restore
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        ) : filteredAndSortedProjects.length === 0 ? (
          /* EMPTY STATE (Dual Glowing Cyan Folders 3D Illustration) */
          <div className="flex-1 flex flex-col items-center justify-center py-20 text-center animate-in fade-in duration-300">
            {/* Dual Glowing Cyan Folders */}
            <div className="relative w-48 h-32 flex items-center justify-center mb-6">
              {/* Left Main Folder */}
              <div className="relative transform -rotate-6 hover:rotate-0 transition-transform duration-300 cursor-pointer">
                <svg width="90" height="75" viewBox="0 0 100 85" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <defs>
                    <linearGradient id="darkFolderGrad1" x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" stopColor="#00c8ff" />
                      <stop offset="100%" stopColor="#0284c7" />
                    </linearGradient>
                    <linearGradient id="darkFolderBack1" x1="0%" y1="0%" x2="0%" y2="100%">
                      <stop offset="0%" stopColor="#00b4d8" />
                      <stop offset="100%" stopColor="#0369a1" />
                    </linearGradient>
                  </defs>
                  {/* Folder Back Tab */}
                  <path d="M10 20C10 14.4772 14.4772 10 20 10H42L52 22H90C95.5228 22 100 26.4772 100 32V75C100 80.5228 95.5228 85 90 85H20C14.4772 85 10 80.5228 10 75V20Z" fill="url(#darkFolderBack1)" opacity="0.4" />
                  {/* Folder Front Face */}
                  <rect x="0" y="24" width="92" height="60" rx="10" fill="url(#darkFolderGrad1)" opacity="0.95" />
                  {/* Glowing Top Lip */}
                  <path d="M0 32C0 27.5817 3.58172 24 8 24H84C88.4183 24 92 27.5817 92 32V38H0V32Z" fill="#38bdf8" />
                  {/* Shiny subtle line */}
                  <line x1="12" y1="48" x2="45" y2="48" stroke="#ffffff" strokeWidth="2.5" strokeLinecap="round" opacity="0.8" />
                </svg>
                {/* Floating small blue star */}
                <div className="absolute -top-2 -left-2 w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
              </div>

              {/* Right Secondary Folder */}
              <div className="relative -ml-4 transform rotate-12 hover:rotate-6 transition-transform duration-300 cursor-pointer">
                <svg width="75" height="65" viewBox="0 0 100 85" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <defs>
                    <linearGradient id="darkFolderGrad2" x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" stopColor="#38bdf8" />
                      <stop offset="100%" stopColor="#0ea5e9" />
                    </linearGradient>
                  </defs>
                  {/* Folder Back */}
                  <path d="M12 18C12 13.5817 15.5817 10 20 10H40L48 20H88C92.4183 20 96 23.5817 96 28V75C96 79.4183 92.4183 83 88 83H20C15.5817 83 12 79.4183 12 75V18Z" fill="#0284c7" opacity="0.5" />
                  {/* Folder Front */}
                  <rect x="5" y="22" width="88" height="58" rx="8" fill="url(#darkFolderGrad2)" opacity="0.9" />
                  {/* Top line */}
                  <line x1="18" y1="36" x2="50" y2="36" stroke="#ffffff" strokeWidth="2.5" strokeLinecap="round" opacity="0.7" />
                </svg>
                <div className="absolute -top-1 -right-1 w-2 h-2 rounded-full bg-sky-400" />
              </div>
            </div>

            {/* Empty text */}
            <p className="text-xs font-medium text-slate-400 max-w-sm mb-4">
              You have not created any {activeTab === "translations" ? "videos" : activeTab.replace("_", " ")} yet
            </p>

            {/* Quick action button for testing / creating */}
            {activeSection !== "trash" && (
              <button
                onClick={activeTab === "translations" ? handleCreateSampleTranslation : handleCreateProject}
                className="mt-2 text-xs font-semibold text-sky-700 dark:text-cyan-400 bg-sky-50 hover:bg-sky-100 dark:bg-[#121b2d] dark:hover:bg-[#18243c] border border-sky-200 dark:border-[#223354] px-4 py-2 rounded-full transition-colors flex items-center gap-1.5 cursor-pointer shadow-md"
              >
                <Plus size={13} /> {activeTab === "translations" ? "Create Sample Translation Video" : "Create Video"}
              </button>
            )}
          </div>
        ) : viewMode === "list" ? (
          /* LIST VIEW */
          <div className={`border rounded-2xl overflow-hidden shadow-lg ${isLight ? "bg-white border-slate-200" : "bg-[#0c111e] border-[#1c2740]"}`}>
            <table className={`w-full text-left text-xs ${isLight ? "text-slate-700" : "text-slate-300"}`}>
              <thead className={`font-semibold border-b ${isLight ? "bg-slate-50 text-slate-700 border-slate-200" : "bg-[#111728] text-slate-400 border-[#1c2740]"}`}>
                <tr>
                  <th className="p-3.5 pl-5">Project</th>
                  <th className="p-3.5">Type</th>
                  <th className="p-3.5">Status</th>
                  <th className="p-3.5">Created</th>
                  <th className="p-3.5 text-right pr-5">Actions</th>
                </tr>
              </thead>
              <tbody className={`divide-y ${isLight ? "divide-slate-100" : "divide-[#182236]"}`}>
                {filteredAndSortedProjects.map((project) => (
                  <tr
                    key={project.id}
                    className={`transition-colors group cursor-pointer ${isLight ? "hover:bg-slate-50/80" : "hover:bg-[#151f36]"}`}
                    onClick={() => {
                      if (onOpenStudio) onOpenStudio(project.id);
                    }}
                  >
                    <td className={`p-3.5 pl-5 font-semibold flex items-center gap-3 ${isLight ? "text-slate-900" : "text-white"}`}>
                      <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${isLight ? "bg-cyan-50 border border-cyan-200 text-cyan-600" : "bg-[#1a233a] border border-[#263554] text-cyan-400"}`}>
                        <Video size={14} />
                      </div>
                      <span>{project.title}</span>
                    </td>
                    <td className="p-3.5">
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${isLight ? "bg-cyan-50 text-cyan-700 border border-cyan-200" : "bg-[#162035] text-cyan-300 border border-cyan-800/40"}`}>
                        {project.badgeLabel}
                      </span>
                    </td>
                    <td className={`p-3.5 ${isLight ? "text-slate-600" : "text-slate-400"}`}>{project.status}</td>
                    <td className={`p-3.5 ${isLight ? "text-slate-600" : "text-slate-400"}`}>{project.createdAt}</td>
                    <td className="p-3.5 text-right pr-5" onClick={(e) => e.stopPropagation()}>
                      <button
                        onClick={() => handleDeleteProject(project.id)}
                        className={`p-1 rounded transition-colors ${isLight ? "text-slate-400 hover:text-rose-500 hover:bg-rose-50" : "text-slate-400 hover:text-rose-400 hover:bg-[#1a253c]"}`}
                        title="Delete"
                      >
                        <Trash2 size={14} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          /* GRID & DATE VIEW */
          <div>
            {/* Group Label: TODAY if Date View */}
            {viewMode === "date" && (
              <h2 className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-4">
                TODAY
              </h2>
            )}

            {/* Projects Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              {filteredAndSortedProjects.map((project) => {
                const isSelected = selectedIds.includes(project.id);
                const isMenuOpen = openMenuId === project.id;

                return (
                  <div key={project.id} className="flex flex-col relative group">
                    {/* Aspect 16:10 Thumbnail Card Frame */}
                    <div
                      onClick={() => {
                        if (onOpenStudio) onOpenStudio(project.id);
                      }}
                      className={`aspect-[16/10] rounded-3xl overflow-hidden relative shadow-sm hover:shadow-xl transition-all duration-300 cursor-pointer flex items-center justify-center p-4 border ${
                        isLight
                          ? "bg-slate-100 hover:bg-slate-200/80 border-slate-200/80 hover:border-cyan-500 hover:shadow-cyan-500/10"
                          : "bg-[#1a2130] hover:bg-[#20293d] border-[#222d42] hover:border-cyan-500/60 hover:shadow-cyan-500/10"
                      }`}
                    >
                      {/* Top-Left: Rounded Checkbox Icon */}
                      <button
                        onClick={(e) => toggleSelect(project.id, e)}
                        className={`absolute top-3 left-3 w-5 h-5 rounded-md border flex items-center justify-center transition-colors cursor-pointer z-10 ${
                          isSelected
                            ? "bg-cyan-500 border-cyan-500 text-slate-950"
                            : "bg-white/90 hover:bg-white border-white/60 text-slate-900 shadow-sm"
                        }`}
                        title="Select project"
                      >
                        {isSelected && <CheckSquare size={14} className="fill-slate-950 text-cyan-500" />}
                      </button>

                      {/* Top-Right: Three Dots Menu Button */}
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setOpenMenuId(isMenuOpen ? null : project.id);
                        }}
                        className="absolute top-3 right-3 w-7 h-7 rounded-full bg-white/90 hover:bg-white flex items-center justify-center text-slate-800 shadow-md transition-colors cursor-pointer z-20"
                        title="More options"
                      >
                        <MoreHorizontal size={16} />
                      </button>

                      {/* Center: Circular Edit Button with Pencil */}
                      <div
                        onClick={(e) => {
                          e.stopPropagation();
                          if (onOpenStudio) onOpenStudio(project.id);
                        }}
                        className={`w-12 h-12 rounded-full border flex items-center justify-center shadow-lg transition-transform duration-200 hover:scale-110 cursor-pointer ${
                          isLight
                            ? "bg-white/90 hover:bg-white text-slate-800 border-slate-200/60"
                            : "bg-black/60 hover:bg-black/80 text-white border-white/20"
                        }`}
                        title="Edit project in Studio"
                      >
                        <Edit2 size={18} />
                      </div>

                      {/* Bottom-Left Badge */}
                      <span className={`absolute bottom-3 left-3 text-[10px] font-bold px-2.5 py-0.5 rounded-full shadow-md ${
                        isLight ? "bg-slate-900/80 text-white" : "bg-black/80 text-white"
                      }`}>
                        {project.badgeLabel}
                      </span>
                    </div>

                    {/* Title & Subtitle Below Card */}
                    <div className="mt-2.5 px-1">
                      {renamingId === project.id ? (
                        <div className="flex items-center gap-1.5" onClick={(e) => e.stopPropagation()}>
                          <input
                            type="text"
                            value={newTitle}
                            onChange={(e) => setNewTitle(e.target.value)}
                            onKeyDown={(e) => e.key === "Enter" && handleSaveRename(project.id)}
                            autoFocus
                            className={`border border-cyan-500 rounded px-2 py-0.5 text-xs outline-none w-full ${isLight ? "bg-white text-slate-900" : "bg-[#121828] text-white"}`}
                          />
                          <button
                            onClick={() => handleSaveRename(project.id)}
                            className="text-cyan-500 text-xs font-bold hover:underline"
                          >
                            Save
                          </button>
                        </div>
                      ) : (
                        <h3 className={`text-xs font-bold transition-colors ${
                          isLight ? "text-slate-900 group-hover:text-cyan-600" : "text-white group-hover:text-cyan-400"
                        }`}>
                          {project.title}
                        </h3>
                      )}
                      <p className={`text-[11px] mt-0.5 ${isLight ? "text-slate-500" : "text-slate-400"}`}>
                        {project.createdAt} • {project.source}
                      </p>
                    </div>

                    {/* CONTEXT MENU DROPDOWN */}
                    {isMenuOpen && (
                      <div
                        onClick={(e) => e.stopPropagation()}
                        className="absolute top-12 right-0 w-48 bg-white text-slate-900 rounded-2xl shadow-2xl border border-slate-100 p-2 z-40 animate-in fade-in zoom-in-95 duration-150 font-sans"
                      >
                        <div className="px-3 py-1.5 text-[11px] font-semibold text-slate-500">
                          Created by {project.creator}
                        </div>

                        {/* Copy ID */}
                        <button
                          onClick={() => handleCopyId(project.id)}
                          className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-medium hover:bg-slate-100 text-slate-800 text-left transition-colors cursor-pointer"
                        >
                          <Copy size={14} className="text-slate-600" />
                          <span>Copy ID</span>
                        </button>

                        {/* Edit as New */}
                        <button
                          onClick={() => handleEditAsNew(project)}
                          className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-medium hover:bg-slate-100 text-slate-800 text-left transition-colors cursor-pointer"
                        >
                          <PlusSquare size={14} className="text-slate-600" />
                          <span>Edit as New</span>
                        </button>

                        {/* Collaborate */}
                        <button
                          onClick={() => {
                            alert("Collaborate: Invite team members to edit this project.");
                            setOpenMenuId(null);
                          }}
                          className="w-full flex items-center justify-between px-3 py-2 rounded-xl text-xs font-medium hover:bg-slate-100 text-slate-800 text-left transition-colors cursor-pointer"
                        >
                          <div className="flex items-center gap-2.5">
                            <Users size={14} className="text-slate-600" />
                            <span>Collaborate</span>
                          </div>
                          <Gem size={13} className="text-amber-500 fill-amber-500" />
                        </button>

                        {/* Rename */}
                        <button
                          onClick={() => handleStartRename(project)}
                          className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-medium hover:bg-slate-100 text-slate-800 text-left transition-colors cursor-pointer"
                        >
                          <Edit2 size={14} className="text-slate-600" />
                          <span>Rename</span>
                        </button>

                        {/* Move */}
                        <button
                          onClick={() => {
                            alert("Move project to another folder");
                            setOpenMenuId(null);
                          }}
                          className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-medium hover:bg-slate-100 text-slate-800 text-left transition-colors cursor-pointer"
                        >
                          <FolderInput size={14} className="text-slate-600" />
                          <span>Move</span>
                        </button>

                        {/* Divider */}
                        <div className="h-[1px] bg-slate-100 my-1"></div>

                        {/* Trash */}
                        <button
                          onClick={(e) => handleDeleteProject(project.id, e)}
                          className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-medium hover:bg-rose-50 text-rose-600 text-left transition-colors cursor-pointer"
                        >
                          <Trash2 size={14} className="text-rose-600" />
                          <span>Trash</span>
                        </button>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Bottom Center Text */}
        <div className="pt-16 pb-4 text-center">
          <p className="text-xs font-medium text-slate-500">
            You've reached the end
          </p>
        </div>
      </div>
    </div>
  );
}
