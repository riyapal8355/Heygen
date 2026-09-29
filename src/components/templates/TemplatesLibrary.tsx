"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  Search,
  Sparkles,
  Clapperboard,
  Play,
  Clock,
  Layers,
  Check,
  Loader2,
  AlertCircle,
} from "lucide-react";
import AskRhysWidget from "../dashboard/AskRhysWidget";
import TemplatePreviewModal, {
  VideoTemplate,
} from "./TemplatePreviewModal";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";

interface TemplatesLibraryProps {
  activeCategory?: string;
  onOpenStudio?: (projectId?: string) => void;
}

export default function TemplatesLibrary({
  activeCategory = "all",
  onOpenStudio,
}: TemplatesLibraryProps) {
  const { currentWorkspace } = useAuth();
  const [templates, setTemplates] = useState<VideoTemplate[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedTemplate, setSelectedTemplate] = useState<VideoTemplate | null>(null);
  const [aspectFilter, setAspectFilter] = useState<"all" | "16:9" | "9:16">("all");
  const [isInstantiating, setIsInstantiating] = useState(false);

  const fetchTemplates = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.creative.listTemplates(
        {
          category: activeCategory !== "all" ? activeCategory : undefined,
          search: searchQuery.trim() || undefined,
        },
        currentWorkspace?.id
      );

      const mapped: VideoTemplate[] = data.map((t: any) => ({
        id: t.id,
        title: t.name,
        category: t.category || "marketing",
        aspectRatio: (t.configuration?.aspect_ratio as "16:9" | "9:16") || "16:9",
        totalDuration: t.configuration?.total_duration || "1:00",
        scenesCount: t.configuration?.scenes_count || 1,
        thumbnail:
          t.configuration?.thumbnail_url ||
          "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?q=80&w=800&auto=format&fit=crop",
        scenes: t.configuration?.scenes || [],
      }));

      setTemplates(mapped);
    } catch (err: any) {
      setError(err?.message || "Failed to load templates.");
      setTemplates([]);
    } finally {
      setIsLoading(false);
    }
  }, [activeCategory, searchQuery, currentWorkspace?.id]);

  useEffect(() => {
    fetchTemplates();
  }, [fetchTemplates]);

  const filteredTemplates = templates.filter((tpl) => {
    const matchesCategory =
      activeCategory === "all" ||
      tpl.category.toLowerCase() === activeCategory.toLowerCase();

    const matchesAspect = aspectFilter === "all" || tpl.aspectRatio === aspectFilter;
    const matchesSearch = tpl.title.toLowerCase().includes(searchQuery.toLowerCase());

    return matchesCategory && matchesAspect && matchesSearch;
  });

  const handleCreateFromTemplate = async (tpl: VideoTemplate) => {
    try {
      setIsInstantiating(true);
      const project = await api.creative.instantiateTemplate(
        tpl.id,
        tpl.title,
        currentWorkspace?.id
      );
      setSelectedTemplate(null);
      if (onOpenStudio) {
        onOpenStudio(project.id);
      }
    } catch (err: any) {
      alert(err?.message || "Failed to instantiate template");
    } finally {
      setIsInstantiating(false);
    }
  };

  return (
    <div className="flex-1 h-screen overflow-y-auto bg-[#07090e] text-slate-100 flex flex-col font-sans select-none relative">
      {/* 1. TOP HEADER */}
      <div className="w-full px-10 pt-7 pb-4 flex items-center justify-between border-b border-[#141b2c] z-20">
        <div>
          <h1 className="text-2xl md:text-3xl font-black text-white tracking-tight">
            Video Templates
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Professionally designed multi-scene templates for learning, marketing, and sales
          </p>
        </div>

        <AskRhysWidget />
      </div>

      {/* 2. FILTER & SEARCH BAR */}
      <div className="max-w-7xl w-full mx-auto px-10 pt-6 pb-2 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        {/* Aspect Ratio Filters */}
        <div className="flex items-center gap-2 bg-[#0c111e] border border-[#1e2a44] p-1 rounded-2xl w-fit">
          <button
            onClick={() => setAspectFilter("all")}
            className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer ${
              aspectFilter === "all"
                ? "bg-[#1f2b48] text-cyan-400 shadow-sm"
                : "text-slate-400 hover:text-white"
            }`}
          >
            All Ratios
          </button>
          <button
            onClick={() => setAspectFilter("16:9")}
            className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer ${
              aspectFilter === "16:9"
                ? "bg-[#1f2b48] text-cyan-400 shadow-sm"
                : "text-slate-400 hover:text-white"
            }`}
          >
            Landscape 16:9
          </button>
          <button
            onClick={() => setAspectFilter("9:16")}
            className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer ${
              aspectFilter === "9:16"
                ? "bg-[#1f2b48] text-cyan-400 shadow-sm"
                : "text-slate-400 hover:text-white"
            }`}
          >
            Portrait 9:16
          </button>
        </div>

        {/* Search Bar */}
        <div className="relative w-64">
          <Search size={14} className="absolute left-3.5 top-2.5 text-slate-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search Templates"
            className="w-full bg-[#111728] border border-[#1e2a44] rounded-full pl-9 pr-3.5 py-1.5 text-xs text-white placeholder-slate-400 focus:outline-none focus:border-cyan-500 shadow-inner"
          />
        </div>
      </div>

      {/* 3. TEMPLATES GRID */}
      <div className="max-w-7xl w-full mx-auto px-10 py-6 flex-1 pb-16">
        {isLoading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="w-8 h-8 text-cyan-400 animate-spin" />
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <AlertCircle className="w-10 h-10 text-rose-400 mb-3" />
            <h3 className="text-sm font-bold text-slate-200">Failed to load templates</h3>
            <p className="text-xs text-slate-400 mt-1 max-w-sm">{error}</p>
            <button
              onClick={fetchTemplates}
              className="mt-4 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-xs font-bold text-white rounded-xl transition-colors cursor-pointer"
            >
              Retry
            </button>
          </div>
        ) : filteredTemplates.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <div className="w-16 h-16 rounded-2xl bg-slate-900 border border-slate-800 flex items-center justify-center mb-4 text-slate-500">
              <Clapperboard size={32} />
            </div>
            <h3 className="text-base font-bold text-slate-300">No Templates Found</h3>
            <p className="text-xs text-slate-500 mt-1 max-w-sm">
              {searchQuery
                ? "No templates match your search criteria."
                : "No templates are available in this workspace category."}
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredTemplates.map((tpl) => (
              <div
                key={tpl.id}
                onClick={() => setSelectedTemplate(tpl)}
                className="bg-[#0c111e] hover:bg-[#121828] border border-[#1c2740] hover:border-cyan-500/60 rounded-3xl overflow-hidden shadow-sm hover:shadow-xl hover:shadow-cyan-500/10 transition-all duration-300 cursor-pointer group flex flex-col justify-between"
              >
                {/* Thumbnail Container */}
                <div className="aspect-[16/10] w-full relative overflow-hidden bg-slate-900">
                  <img
                    src={tpl.thumbnail}
                    alt={tpl.title}
                    className="w-full h-full object-cover object-top group-hover:scale-105 transition-transform duration-500 brightness-90"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-black/20"></div>

                  {/* Top Badges */}
                  <div className="absolute top-3 left-3 flex items-center gap-2">
                    <span className="bg-black/70 backdrop-blur-sm text-[10px] font-bold text-cyan-400 border border-cyan-500/30 px-2 py-0.5 rounded-md">
                      {tpl.aspectRatio}
                    </span>
                    <span className="bg-black/70 backdrop-blur-sm text-[10px] font-bold text-white px-2 py-0.5 rounded-md flex items-center gap-1">
                      <Layers size={10} /> {tpl.scenesCount} Scenes
                    </span>
                  </div>

                  {/* Bottom Duration Badge */}
                  <span className="absolute bottom-3 right-3 bg-black/80 text-[10px] font-mono font-bold text-slate-300 px-2 py-0.5 rounded flex items-center gap-1">
                    <Clock size={10} /> {tpl.totalDuration}
                  </span>

                  {/* Center Hover Play Icon */}
                  <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                    <div className="w-12 h-12 rounded-full bg-cyan-500 text-slate-950 flex items-center justify-center shadow-lg shadow-cyan-500/40">
                      <Play size={20} className="ml-1 fill-slate-950" />
                    </div>
                  </div>
                </div>

                {/* Text Info */}
                <div className="p-4">
                  <h3 className="text-xs font-bold text-white group-hover:text-cyan-400 transition-colors line-clamp-1">
                    {tpl.title}
                  </h3>
                  <div className="flex items-center justify-between text-[11px] text-slate-400 mt-2 pt-2 border-t border-[#17223b]">
                    <span className="capitalize">{tpl.category}</span>
                    <span className="font-semibold text-cyan-400 flex items-center gap-1">
                      <span>Preview & Edit</span>
                      <Clapperboard size={11} />
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* TEMPLATE PREVIEW MODAL */}
      {selectedTemplate && (
        <TemplatePreviewModal
          template={selectedTemplate}
          onClose={() => setSelectedTemplate(null)}
          onCreateFromTemplate={handleCreateFromTemplate}
        />
      )}
    </div>
  );
}
