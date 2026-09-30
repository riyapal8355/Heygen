"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  Plus,
  Search,
  MoreHorizontal,
  Play,
  Pencil,
  Video,
  Layers,
  Sparkles,
  LayoutGrid,
  Square,
  RectangleHorizontal,
  Copy,
  Users,
  FolderInput,
  Trash2,
  Check,
  X,
  FileEdit,
} from "lucide-react";
import AskRhysWidget from "../dashboard/AskRhysWidget";

export interface SceneBySceneTemplate {
  id: string;
  title: string;
  category: string;
  image: string;
  aspectRatio?: "16:9" | "9:16";
  duration?: string;
  scenesCount?: number;
  tabCategory?: string;
}

export interface GetStartedVideoItem {
  id: string;
  title: string;
  time: string;
  source: string;
  type: "avatar" | "placeholder";
  image?: string;
  isDraft: boolean;
}

export const SCENE_BY_SCENE_TEMPLATES: SceneBySceneTemplate[] = [
  {
    id: "sbs-1",
    title: "Focus Framework Intro",
    category: "Corporate • Learning & Development • Training",
    tabCategory: "training",
    image: "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?q=80&w=800&auto=format&fit=crop",
    aspectRatio: "16:9",
    duration: "1:45",
    scenesCount: 5,
  },
  {
    id: "sbs-2",
    title: "Minimalist Sales Report",
    category: "Sales • Corporate",
    tabCategory: "sales",
    image: "https://images.unsplash.com/photo-1551836022-d5d88e9218df?q=80&w=800&auto=format&fit=crop",
    aspectRatio: "16:9",
    duration: "1:15",
    scenesCount: 4,
  },
  {
    id: "sbs-3",
    title: "Stress-Free Moving Quote",
    category: "Marketing • Explainer",
    tabCategory: "marketing",
    image: "https://images.unsplash.com/photo-1560518883-ce09059eeffa?q=80&w=800&auto=format&fit=crop",
    aspectRatio: "16:9",
    duration: "0:50",
    scenesCount: 3,
  },
  {
    id: "sbs-4",
    title: "Wealth Management",
    category: "Marketing • Sales",
    tabCategory: "sales",
    image: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?q=80&w=800&auto=format&fit=crop",
    aspectRatio: "16:9",
    duration: "2:10",
    scenesCount: 6,
  },
  {
    id: "sbs-5",
    title: "Product Roadmap",
    category: "Tutorials & Explainers • Sales • Corporate",
    tabCategory: "tutorials",
    image: "https://images.unsplash.com/photo-1531482615713-2afd69097998?q=80&w=800&auto=format&fit=crop",
    aspectRatio: "16:9",
    duration: "2:30",
    scenesCount: 7,
  },
  {
    id: "sbs-6",
    title: "Financial Services Marketing",
    category: "Marketing • Corporate",
    tabCategory: "marketing",
    image: "https://images.unsplash.com/photo-1450133064473-71024230f91b?q=80&w=800&auto=format&fit=crop",
    aspectRatio: "16:9",
    duration: "1:20",
    scenesCount: 4,
  },
  {
    id: "sbs-7",
    title: "Property Listing",
    category: "Real Estate",
    tabCategory: "real_estate",
    image: "https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?q=80&w=800&auto=format&fit=crop",
    aspectRatio: "16:9",
    duration: "1:55",
    scenesCount: 6,
  },
  {
    id: "sbs-8",
    title: "Business Strategy",
    category: "Corporate",
    tabCategory: "corporate",
    image: "https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?q=80&w=800&auto=format&fit=crop",
    aspectRatio: "16:9",
    duration: "2:05",
    scenesCount: 6,
  },
  {
    id: "sbs-9",
    title: "Tech News Report",
    category: "Explainer Video",
    tabCategory: "tutorials",
    image: "https://images.unsplash.com/photo-1495020689067-958852a7765e?q=80&w=800&auto=format&fit=crop",
    aspectRatio: "16:9",
    duration: "1:00",
    scenesCount: 4,
  },
];

import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";

interface SceneBySceneProps {
  onOpenStudio?: (projectId?: string) => void;
  onSelectTemplate?: (template: SceneBySceneTemplate) => void;
  onSeeAllProjects?: () => void;
}

export default function SceneByScene({
  onOpenStudio,
  onSelectTemplate,
  onSeeAllProjects,
}: SceneBySceneProps) {
  const { currentWorkspace } = useAuth();
  const [activeCategoryTab, setActiveCategoryTab] = useState("recommended");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedRatio, setSelectedRatio] = useState<"16:9" | "9:16">("16:9");

  // Get started videos state (loaded from real backend projects)
  const [videos, setVideos] = useState<GetStartedVideoItem[]>([]);
  const [isLoadingVideos, setIsLoadingVideos] = useState(false);

  // Three-dot dropdown state
  const [openMenuVideoId, setOpenMenuVideoId] = useState<string | null>(null);

  // Rename modal state
  const [renameVideo, setRenameVideo] = useState<GetStartedVideoItem | null>(null);
  const [renameTitleInput, setRenameTitleInput] = useState("");

  // Delete modal state
  const [deleteVideo, setDeleteVideo] = useState<GetStartedVideoItem | null>(null);

  // Toast feedback state
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const loadVideos = React.useCallback(async () => {
    if (!currentWorkspace?.id) return;
    setIsLoadingVideos(true);
    try {
      const resp = await api.projects.list(currentWorkspace.id);
      const mapped: GetStartedVideoItem[] = resp.slice(0, 10).map((p) => ({
        id: p.id,
        title: p.title,
        time: new Date(p.updated_at).toLocaleDateString(),
        source: "AI Studio",
        type: "avatar",
        image: "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?q=80&w=700&auto=format&fit=crop",
        isDraft: p.status === "draft",
      }));
      setVideos(mapped);
    } catch (err: any) {
      console.error("Failed to load projects:", err);
    } finally {
      setIsLoadingVideos(false);
    }
  }, [currentWorkspace?.id]);

  useEffect(() => {
    loadVideos();
  }, [loadVideos]);

  // Close dropdown on click outside
  useEffect(() => {
    const handleOutsideClick = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      if (!target.closest(".video-menu-container")) {
        setOpenMenuVideoId(null);
      }
    };
    if (openMenuVideoId) {
      document.addEventListener("click", handleOutsideClick);
    }
    return () => {
      document.removeEventListener("click", handleOutsideClick);
    };
  }, [openMenuVideoId]);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => {
      setToastMessage((prev) => (prev === msg ? null : prev));
    }, 3000);
  };

  const handleCopyId = (video: GetStartedVideoItem) => {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(video.id);
    }
    showToast(`Video ID copied: ${video.id}`);
    setOpenMenuVideoId(null);
  };

  const handleEditAsNew = async (video: GetStartedVideoItem) => {
    setOpenMenuVideoId(null);
    if (!currentWorkspace?.id) return;
    try {
      const newProj = await api.projects.create(currentWorkspace.id, {
        title: `${video.title} (Copy)`,
        aspect_ratio: selectedRatio,
      });
      await loadVideos();
      if (onOpenStudio) {
        onOpenStudio(newProj.id);
      }
    } catch (err: any) {
      showToast(err?.message || "Failed to create project copy");
    }
  };

  const handleCollaborate = (video: GetStartedVideoItem) => {
    showToast(`Collaborate link generated for ${video.title}`);
    setOpenMenuVideoId(null);
  };

  const handleOpenRename = (video: GetStartedVideoItem) => {
    setRenameVideo(video);
    setRenameTitleInput(video.title);
    setOpenMenuVideoId(null);
  };

  const handleCreateNewVideo = async () => {
    if (!currentWorkspace?.id) {
      if (onOpenStudio) onOpenStudio();
      return;
    }
    try {
      const newProj = await api.projects.create(currentWorkspace.id, {
        title: "Untitled Video",
        aspect_ratio: selectedRatio,
      });
      await loadVideos();
      if (onOpenStudio) {
        onOpenStudio(newProj.id);
      }
    } catch (err: any) {
      showToast(err?.message || "Failed to create new video");
    }
  };

  const handleSaveRename = async () => {
    if (!renameVideo || !renameTitleInput.trim() || !currentWorkspace?.id) return;
    try {
      await api.projects.update(currentWorkspace.id, renameVideo.id, { title: renameTitleInput.trim() });
      await loadVideos();
      showToast("Video renamed successfully");
      setRenameVideo(null);
    } catch (err: any) {
      showToast(err?.message || "Failed to rename video");
    }
  };

  const handleMove = (video: GetStartedVideoItem) => {
    showToast(`Moved ${video.title} to folder`);
    setOpenMenuVideoId(null);
  };

  const handleOpenDelete = (video: GetStartedVideoItem) => {
    setDeleteVideo(video);
    setOpenMenuVideoId(null);
  };

  const handleConfirmDelete = async () => {
    if (!deleteVideo || !currentWorkspace?.id) return;
    try {
      await api.projects.delete(currentWorkspace.id, deleteVideo.id);
      await loadVideos();
      showToast(`Deleted ${deleteVideo.title}`);
      setDeleteVideo(null);
    } catch (err: any) {
      showToast(err?.message || "Failed to delete video");
    }
  };

  const categoryTabs = [
    { id: "all", label: "All" },
    { id: "my_templates", label: "My Templates" },
    { id: "recommended", label: "Recommended" },
    { id: "training", label: "Training" },
    { id: "corporate", label: "Corporate" },
    { id: "marketing", label: "Marketing" },
    { id: "sales", label: "Sales" },
    { id: "tutorials", label: "Tutorials & Explainers" },
    { id: "real_estate", label: "Real Estate" },
    { id: "healthcare", label: "Healthcare" },
    { id: "ecommerce", label: "E-Commerce" },
  ];

  const filteredTemplates = SCENE_BY_SCENE_TEMPLATES.filter((tpl) => {
    const matchesSearch =
      !searchQuery.trim() ||
      tpl.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      tpl.category.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesCategory =
      activeCategoryTab === "all" ||
      activeCategoryTab === "recommended" ||
      activeCategoryTab === "my_templates" ||
      tpl.tabCategory === activeCategoryTab ||
      tpl.category.toLowerCase().includes(activeCategoryTab.replace("_", " "));

    return matchesSearch && matchesCategory;
  });

  const handleCardClick = async (template: SceneBySceneTemplate) => {
    if (onSelectTemplate) {
      onSelectTemplate(template);
      return;
    }
    if (!currentWorkspace?.id) return;
    try {
      const proj = await api.projects.create(currentWorkspace.id, {
        title: template.title,
        aspect_ratio: template.aspectRatio || selectedRatio,
      });
      if (onOpenStudio) {
        onOpenStudio(proj.id);
      }
    } catch (err: any) {
      showToast(err?.message || "Failed to create project from template");
    }
  };

  return (
    <div
      id="scene-by-scene-view"
      data-testid="scene-by-scene-view"
      className="flex-1 h-screen overflow-y-auto bg-[#07090e] text-slate-100 flex flex-col font-sans select-none relative scrollbar-thin scrollbar-thumb-[#151c2d]"
    >
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 bg-[#18233c] text-white border border-[#2b3a5d]/50 text-xs font-semibold px-4 py-2.5 rounded-xl shadow-2xl flex items-center gap-2 animate-in fade-in slide-in-from-bottom-3 duration-200">
          <Sparkles size={14} className="text-cyan-400" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* 1. TOP HEADER (Center Title & Ask Rhys on Right) */}
      <header className="w-full px-8 sm:px-12 pt-8 pb-5 flex items-center justify-between border-b border-[#151c2d] bg-[#07090e] sticky top-0 z-20">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            Welcome to AI Studio
          </h1>
        </div>

        <div className="flex items-center gap-3">
          <AskRhysWidget variant="banner" />
        </div>
      </header>

      {/* 2. MAIN WORKSPACE CONTAINER */}
      <main className="max-w-7xl w-full mx-auto px-8 sm:px-12 py-8 space-y-10 flex-1">
        {/* ================= SECTION 1: GET STARTED ================= */}
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base sm:text-lg font-extrabold text-white tracking-tight">
              Get started
            </h2>
            <button
              type="button"
              onClick={() => {
                if (onSeeAllProjects) onSeeAllProjects();
                else if (onOpenStudio) onOpenStudio();
              }}
              className="text-xs font-semibold text-slate-400 hover:text-white transition-colors cursor-pointer flex items-center gap-1"
            >
              <span>See All</span>
              <span>&gt;</span>
            </button>
          </div>

          {/* 3 Cards Row */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-start">
            {/* CARD 1 — NEW VIDEO (Large Dashed Card) */}
            <div
              onClick={handleCreateNewVideo}
              className="w-full aspect-[16/10] bg-[#0b111e] border-2 border-dashed border-[#1b2940] hover:border-cyan-500/50 hover:bg-[#0f172a]/50 rounded-3xl flex flex-col items-center justify-center p-6 cursor-pointer group transition-all duration-300 hover:shadow-lg shrink-0"
            >
              <div className="w-12 h-12 rounded-full bg-[#151f33] group-hover:bg-[#18233c] text-slate-300 group-hover:text-cyan-400 flex items-center justify-center shadow-xs group-hover:scale-110 transition-all duration-300">
                <Plus size={22} className="stroke-[2.5]" />
              </div>

              <span className="text-sm font-bold text-white group-hover:text-cyan-400 mt-3 transition-colors">
                New video
              </span>
              <span className="text-xs text-slate-400 mt-0.5">
                Start in landscape
              </span>
            </div>

            {/* UNTITLED VIDEO CARDS (Rendered dynamically from state) */}
            {videos.map((video) => (
              <div
                key={video.id}
                onClick={() => onOpenStudio && onOpenStudio(video.id)}
                className="flex flex-col cursor-pointer group relative w-full"
              >
                <div className={`w-full aspect-[16/10] ${video.type === "placeholder" ? "bg-[#0f172a] flex items-center justify-center" : "bg-[#0b111e]"} rounded-3xl overflow-visible relative shadow-xs hover:shadow-lg transition-all duration-300 border border-[#1b2940] hover:border-cyan-500/40 shrink-0`}>
                  {/* Thumbnail Image or Placeholder */}
                  {video.type === "avatar" && video.image ? (
                    <div className="w-full h-full aspect-[16/10] rounded-3xl overflow-hidden relative">
                      <img
                        src={video.image}
                        alt={video.title}
                        className="w-full h-full object-cover object-top group-hover:scale-105 transition-transform duration-500 brightness-95 block"
                      />
                      <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-black/40"></div>
                    </div>
                  ) : (
                    <div className="w-12 h-12 rounded-2xl bg-[#151f33] text-slate-300 group-hover:text-cyan-400 shadow-sm flex items-center justify-center transition-colors">
                      <Video size={24} />
                    </div>
                  )}

                  {/* Top Badges */}
                  <div className="absolute top-3 left-3 flex items-center gap-2 z-10">
                    <span className="bg-black/70 backdrop-blur-sm text-white text-[10px] font-semibold px-2.5 py-0.5 rounded-full border border-white/10">
                      Avatar Video
                    </span>
                    {video.isDraft && (
                      <span className="bg-black/70 backdrop-blur-sm text-amber-300 text-[10px] font-bold px-2.5 py-0.5 rounded-full border border-white/10">
                        Draft
                      </span>
                    )}
                  </div>

                  {/* Top Right Three-dot Menu Container */}
                  <div className="absolute top-3 right-3 z-30 video-menu-container">
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        setOpenMenuVideoId(openMenuVideoId === video.id ? null : video.id);
                      }}
                      className={`w-7 h-7 rounded-full flex items-center justify-center transition-all shadow-xs cursor-pointer border border-white/10 ${
                        openMenuVideoId === video.id
                          ? "bg-[#18233c] text-cyan-400 ring-2 ring-cyan-500 shadow-md"
                          : "bg-black/60 hover:bg-[#18233c] text-slate-200"
                      }`}
                      title="More options"
                    >
                      <MoreHorizontal size={14} />
                    </button>

                    {/* Dropdown Menu */}
                    {openMenuVideoId === video.id && (
                      <div
                        onClick={(e) => e.stopPropagation()}
                        className="absolute right-0 top-full mt-2 w-52 bg-[#0b111e] rounded-2xl shadow-2xl border border-[#1b2940] py-2 z-50 text-slate-200 font-sans animate-in fade-in zoom-in-95 duration-150"
                      >
                        {/* Header: Created by Riya */}
                        <div className="px-3.5 py-2 flex items-center gap-2 border-b border-[#151c2d] mb-1">
                          <div className="w-5 h-5 rounded-full bg-gradient-to-tr from-cyan-500 to-blue-600 text-white flex items-center justify-center text-[10px] font-bold shadow-xs">
                            R
                          </div>
                          <span className="text-xs font-semibold text-slate-300 truncate">
                            Created by Riya
                          </span>
                        </div>

                        {/* Menu Item 1: Copy ID */}
                        <button
                          type="button"
                          onClick={() => handleCopyId(video)}
                          className="w-full px-3.5 py-2 text-left text-xs font-medium text-slate-300 hover:bg-[#18233c] hover:text-white flex items-center gap-2.5 transition-colors cursor-pointer"
                        >
                          <Copy size={14} className="text-slate-400" />
                          <span>Copy ID</span>
                        </button>

                        {/* Menu Item 2: Edit as New */}
                        <button
                          type="button"
                          onClick={() => handleEditAsNew(video)}
                          className="w-full px-3.5 py-2 text-left text-xs font-medium text-slate-300 hover:bg-[#18233c] hover:text-white flex items-center gap-2.5 transition-colors cursor-pointer"
                        >
                          <FileEdit size={14} className="text-slate-400" />
                          <span>Edit as New</span>
                        </button>

                        {/* Menu Item 3: Collaborate 💎 */}
                        <button
                          type="button"
                          onClick={() => handleCollaborate(video)}
                          className="w-full px-3.5 py-2 text-left text-xs font-medium text-slate-300 hover:bg-[#18233c] hover:text-white flex items-center justify-between transition-colors cursor-pointer"
                        >
                          <div className="flex items-center gap-2.5">
                            <Users size={14} className="text-slate-400" />
                            <span>Collaborate</span>
                          </div>
                          <span className="text-xs">💎</span>
                        </button>

                        {/* Menu Item 4: Rename */}
                        <button
                          type="button"
                          onClick={() => handleOpenRename(video)}
                          className="w-full px-3.5 py-2 text-left text-xs font-medium text-slate-300 hover:bg-[#18233c] hover:text-white flex items-center gap-2.5 transition-colors cursor-pointer"
                        >
                          <Pencil size={14} className="text-slate-400" />
                          <span>Rename</span>
                        </button>

                        {/* Menu Item 5: Move */}
                        <button
                          type="button"
                          onClick={() => handleMove(video)}
                          className="w-full px-3.5 py-2 text-left text-xs font-medium text-slate-300 hover:bg-[#18233c] hover:text-white flex items-center gap-2.5 transition-colors cursor-pointer"
                        >
                          <FolderInput size={14} className="text-slate-400" />
                          <span>Move</span>
                        </button>

                        {/* Divider */}
                        <div className="h-px bg-[#151c2d] my-1 mx-2"></div>

                        {/* Menu Item 7: Trash */}
                        <button
                          type="button"
                          onClick={() => handleOpenDelete(video)}
                          className="w-full px-3.5 py-2 text-left text-xs font-medium text-rose-400 hover:bg-rose-950/40 hover:text-rose-300 flex items-center gap-2.5 transition-colors cursor-pointer"
                        >
                          <Trash2 size={14} className="text-rose-400" />
                          <span>Trash</span>
                        </button>
                      </div>
                    )}
                  </div>

                  {/* Center Hover Edit Icon */}
                  {video.type === "avatar" && (
                    <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-200 bg-black/40 backdrop-blur-[2px] rounded-3xl pointer-events-none">
                      <div className="w-11 h-11 rounded-full bg-white text-slate-900 flex items-center justify-center shadow-lg transform scale-90 group-hover:scale-100 transition-transform">
                        <Pencil size={18} className="ml-0.5" />
                      </div>
                    </div>
                  )}
                </div>

                {/* Title & Metadata */}
                <div className="mt-2.5 px-1">
                  <h3 className="text-sm font-bold text-white group-hover:text-cyan-400 transition-colors">
                    {video.title}
                  </h3>
                  <p className="text-xs text-slate-400 mt-0.5">
                    {video.time} • {video.source}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Rename Dialog Modal */}
        {renameVideo && (
          <div
            onClick={() => setRenameVideo(null)}
            className="fixed inset-0 bg-black/70 backdrop-blur-xs flex items-center justify-center z-50 p-4"
          >
            <div
              onClick={(e) => e.stopPropagation()}
              className="bg-[#0b111e] rounded-3xl p-6 max-w-sm w-full shadow-2xl border border-[#1b2940] animate-in fade-in zoom-in-95 duration-150"
            >
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-base font-bold text-white">Rename video</h3>
                <button
                  onClick={() => setRenameVideo(null)}
                  className="p-1 text-slate-400 hover:text-white rounded-lg"
                >
                  <X size={16} />
                </button>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="text-xs font-semibold text-slate-300 block mb-1.5">
                    Video Title
                  </label>
                  <input
                    type="text"
                    autoFocus
                    value={renameTitleInput}
                    onChange={(e) => setRenameTitleInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") handleSaveRename();
                      if (e.key === "Escape") setRenameVideo(null);
                    }}
                    placeholder="Enter video name"
                    className="w-full bg-[#07090e] border border-[#1b2940] rounded-xl px-3.5 py-2.5 text-xs text-white placeholder:text-slate-500 focus:outline-none focus:border-cyan-500 focus:ring-2 focus:ring-cyan-500/20"
                  />
                </div>

                <div className="flex items-center justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setRenameVideo(null)}
                    className="px-4 py-2 text-xs font-bold text-slate-300 hover:text-white bg-[#0f172a] hover:bg-[#172238] border border-[#1b2940] rounded-xl transition-colors cursor-pointer"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={handleSaveRename}
                    disabled={!renameTitleInput.trim()}
                    className="px-4 py-2 text-xs font-bold text-white bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 rounded-xl transition-colors cursor-pointer shadow-xs"
                  >
                    Save
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Delete Confirmation Dialog Modal */}
        {deleteVideo && (
          <div
            onClick={() => setDeleteVideo(null)}
            className="fixed inset-0 bg-black/70 backdrop-blur-xs flex items-center justify-center z-50 p-4"
          >
            <div
              onClick={(e) => e.stopPropagation()}
              className="bg-[#0b111e] rounded-3xl p-6 max-w-sm w-full shadow-2xl border border-[#1b2940] animate-in fade-in zoom-in-95 duration-150"
            >
              <h3 className="text-lg font-bold text-white">Delete video?</h3>
              <p className="text-xs text-slate-400 mt-2 leading-relaxed">
                Are you sure you want to delete <span className="font-bold text-slate-200">"{deleteVideo.title}"</span>? This action cannot be undone.
              </p>

              <div className="flex items-center justify-end gap-2.5 mt-6">
                <button
                  type="button"
                  onClick={() => setDeleteVideo(null)}
                  className="px-4 py-2 text-xs font-bold text-slate-300 hover:text-white bg-[#0f172a] hover:bg-[#172238] border border-[#1b2940] rounded-xl transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleConfirmDelete}
                  className="px-4 py-2 text-xs font-bold text-white bg-red-600 hover:bg-red-700 rounded-xl transition-colors cursor-pointer shadow-xs"
                >
                  Delete
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ================= SECTION 2: USE A TEMPLATE ================= */}
        <section className="bg-[#0b111e] border border-[#1b2940] rounded-3xl p-6 sm:p-8 shadow-sm space-y-6">
          {/* Header Row: Title on Left, Search & Aspect Ratio Controls on Right */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h2 className="text-xl sm:text-2xl font-extrabold text-white tracking-tight">
                Use a template
              </h2>
            </div>

            <div className="flex items-center gap-3">
              {/* Search templates input */}
              <div className="relative w-56 sm:w-64">
                <Search
                  size={14}
                  className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none"
                />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search templates"
                  className="w-full bg-[#07090e] border border-[#1b2940] rounded-full pl-9 pr-4 py-2 text-xs text-white placeholder:text-slate-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500/30 shadow-2xs transition-all"
                />
              </div>

              {/* Aspect Ratio / Layout Toggle */}
              <div className="flex items-center bg-[#07090e] border border-[#1b2940] p-1 rounded-full shadow-2xs">
                <button
                  type="button"
                  onClick={() => setSelectedRatio("16:9")}
                  className={`px-3 py-1 rounded-full text-xs font-semibold transition-all cursor-pointer flex items-center gap-1.5 ${
                    selectedRatio === "16:9"
                      ? "bg-[#18233c] text-cyan-400 font-bold border border-[#2b3a5d]/50 shadow-2xs"
                      : "text-slate-400 hover:text-white"
                  }`}
                  title="Landscape 16:9"
                >
                  <RectangleHorizontal size={13} />
                  <span className="hidden sm:inline">16:9</span>
                </button>
                <button
                  type="button"
                  onClick={() => setSelectedRatio("9:16")}
                  className={`px-3 py-1 rounded-full text-xs font-semibold transition-all cursor-pointer flex items-center gap-1.5 ${
                    selectedRatio === "9:16"
                      ? "bg-[#18233c] text-cyan-400 font-bold border border-[#2b3a5d]/50 shadow-2xs"
                      : "text-slate-400 hover:text-white"
                  }`}
                  title="Portrait 9:16"
                >
                  <Square size={13} />
                  <span className="hidden sm:inline">9:16</span>
                </button>
              </div>
            </div>
          </div>

          {/* Category Tabs (Horizontally scrollable with active cyan underline) */}
          <div className="border-b border-[#1b2940] flex items-center gap-6 overflow-x-auto no-scrollbar scrollbar-none text-xs font-medium text-slate-400 pt-1">
            {categoryTabs.map((tab) => {
              const isActive = activeCategoryTab === tab.id;
              return (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setActiveCategoryTab(tab.id)}
                  className={`pb-3 transition-colors shrink-0 cursor-pointer relative ${
                    isActive
                      ? "text-white font-bold"
                      : "hover:text-white font-medium"
                  }`}
                >
                  <span>{tab.label}</span>
                  {isActive && (
                    <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-cyan-400 rounded-full"></span>
                  )}
                </button>
              );
            })}
          </div>

          {/* 3-Column Template Grid with Fixed Min-Height Container */}
          <div className="min-h-[480px]">
            {filteredTemplates.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 pt-2">
                {filteredTemplates.map((template) => (
                  <div
                    key={template.id}
                    onClick={() => handleCardClick(template)}
                    className="bg-[#0b111e] border border-[#1b2940] hover:border-cyan-500/40 rounded-2xl overflow-hidden shadow-xs hover:shadow-lg transition-all duration-300 cursor-pointer group flex flex-col justify-between"
                  >
                    {/* Visual Thumbnail */}
                    <div className="aspect-[16/10] w-full bg-[#07090e] relative overflow-hidden">
                      <img
                        src={template.image}
                        alt={template.title}
                        className="w-full h-full object-cover object-top group-hover:scale-105 transition-transform duration-500 brightness-95"
                      />
                      <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-black/30"></div>

                      {/* Top Scene Count Badge */}
                      <div className="absolute top-2.5 left-2.5">
                        <span className="bg-black/70 backdrop-blur-sm text-white text-[10px] font-semibold px-2 py-0.5 rounded-md flex items-center gap-1 border border-white/10">
                          <Layers size={10} />
                          <span>{template.scenesCount || 5} Scenes</span>
                        </span>
                      </div>

                      {/* Center Play Overlay */}
                      <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity bg-black/40 backdrop-blur-[2px]">
                        <div className="w-11 h-11 rounded-full bg-white text-slate-900 flex items-center justify-center shadow-lg transform scale-90 group-hover:scale-100 transition-transform">
                          <Play size={18} className="ml-0.5 fill-slate-900" />
                        </div>
                      </div>
                    </div>

                    {/* Card Info */}
                    <div className="p-4 bg-[#0b111e] flex flex-col justify-between flex-1">
                      <div>
                        <h3 className="text-sm font-bold text-white group-hover:text-cyan-400 transition-colors line-clamp-1">
                          {template.title}
                        </h3>
                        <p className="text-xs text-slate-400 mt-1 line-clamp-1">
                          {template.category}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="h-[480px] flex flex-col items-center justify-center text-center p-8">
                <Search size={32} className="text-slate-600 mb-3" />
                <p className="text-sm font-semibold text-slate-300">No templates found</p>
                <p className="text-xs text-slate-500 mt-1">Try searching for a different keyword or category.</p>
              </div>
            )}
          </div>

          {/* Bottom Center: See More Button */}
          <div className="pt-4 flex justify-center">
            <button
              type="button"
              onClick={() => onOpenStudio?.()}
              className="px-7 py-2.5 bg-[#0f172a] hover:bg-[#172238] text-slate-200 border border-[#1b2940] hover:border-cyan-500/40 text-xs sm:text-sm font-bold rounded-full shadow-xs transition-all cursor-pointer hover:shadow-sm hover:text-white"
            >
              See More
            </button>
          </div>
        </section>
      </main>
    </div>
  );
}
