"use client";

import React, { useState, useRef, useEffect, useCallback } from "react";
import {
  UserPlus,
  Sparkles,
  ArrowRight,
  Video,
  Image as ImageIcon,
  Play,
  Search,
  Filter,
  Check,
  ChevronRight,
  ExternalLink,
  Crown,
  Upload,
  X,
  Wand2,
} from "lucide-react";
import AskRhysWidget from "../dashboard/AskRhysWidget";
import CreateAvatarWizard from "./CreateAvatarWizard";
import { AvatarOptionData } from "../create/videoAgentData";
import { useAuth } from "@/context/AuthContext";
import { useTheme } from "@/context/ThemeContext";
import { api } from "@/lib/api";

export interface AvatarsManagerProps {
  onOpenStudio?: () => void;
  onSelectAvatar?: (avatar: AvatarOptionData) => void;
  selectedAvatarId?: string;
  defaultTab?: "my_avatars" | "public_avatars";
}

export default function AvatarsManager({
  onOpenStudio,
  onSelectAvatar,
  selectedAvatarId,
  defaultTab = "public_avatars",
}: AvatarsManagerProps) {
  const { theme } = useTheme();
  const isLight = theme === "light";
  const { currentWorkspace } = useAuth();
  const [avatars, setAvatars] = useState<AvatarOptionData[]>([]);
  const [isLoadingAvatars, setIsLoadingAvatars] = useState(true);
  const [avatarError, setAvatarError] = useState<string | null>(null);

  const [activeTab, setActiveTab] = useState<"my_avatars" | "public_avatars">(defaultTab);
  const [isWizardOpen, setIsWizardOpen] = useState(false);
  const [isNewAvatarMode, setIsNewAvatarMode] = useState(false);
  const [isVirtualModalOpen, setIsVirtualModalOpen] = useState(false);
  const [characterPrompt, setCharacterPrompt] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("All");
  const [searchQuery, setSearchQuery] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchAvatars = useCallback(async () => {
    setIsLoadingAvatars(true);
    setAvatarError(null);
    try {
      const resp = await api.creative.listAvatars({}, currentWorkspace?.id);
      const mapped: AvatarOptionData[] = (resp || []).map((a: any) => ({
        id: a.id,
        name: a.name,
        label: a.name || "Avatar",
        tag: a.avatar_type || "Studio",
        type: a.avatar_type === "custom" ? "Custom Avatar" : "Photo Avatar",
        image:
          a.preview_url ||
          a.provider_metadata?.preview_url ||
          a.provider_metadata?.image_url ||
          "https://images.unsplash.com/photo-1534528741775-53994a69daeb?q=80&w=700&auto=format&fit=crop",
        filterCategory: a.provider_metadata?.category || "Professional",
        looks: a.looks?.length || 1,
        lookImages: (a.looks || []).map((l: any) => ({
          id: l.id,
          name: l.name,
          image:
            l.preview_url ||
            l.configuration?.preview_url ||
            "https://images.unsplash.com/photo-1534528741775-53994a69daeb?q=80&w=700&auto=format&fit=crop",
        })),
      }));
      setAvatars(mapped);
    } catch (err: any) {
      setAvatarError(err?.message || "Failed to load avatars from backend.");
    } finally {
      setIsLoadingAvatars(false);
    }
  }, [currentWorkspace?.id]);

  useEffect(() => {
    fetchAvatars();
  }, [fetchAvatars]);

  if (isWizardOpen) {
    return (
      <CreateAvatarWizard
        onBack={() => setIsWizardOpen(false)}
        onSuccess={() => {
          setIsWizardOpen(false);
        }}
      />
    );
  }

  // Filtered public avatars based on real backend data (zero mock fallback)
  const filteredPublicAvatars = avatars.filter((avatar) => {
    const matchesCategory =
      selectedCategory === "All" || avatar.filterCategory === selectedCategory;
    const matchesSearch =
      searchQuery.trim() === "" ||
      avatar.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      avatar.type.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  return (
    <div className={`flex-1 h-screen overflow-y-auto flex flex-col font-sans select-none relative ${isLight ? "bg-slate-50 text-slate-900" : "bg-[#07090e] text-slate-100"}`}>
      <input
        type="file"
        ref={fileInputRef}
        className="hidden"
        accept="image/*"
        onChange={() => {
          alert("GPU_UNAVAILABLE: Digital avatar animation requires NVIDIA CUDA GPU acceleration (CUDA VALIDATION PENDING).");
        }}
      />

      {/* 1. TOP HEADER & TABS BAR */}
      <div className={`w-full px-8 pt-6 pb-4 flex items-center justify-between border-b z-20 ${isLight ? "border-slate-200" : "border-[#141b2c]"}`}>
        {/* Tabs: My Avatars & Public Avatars */}
        {!isNewAvatarMode ? (
          <div className="flex items-center gap-8 text-base font-bold">
            <button
              onClick={() => setActiveTab("my_avatars")}
              className={`transition-colors relative pb-2 cursor-pointer ${
                activeTab === "my_avatars"
                  ? (isLight ? "text-slate-900 font-extrabold" : "text-white")
                  : (isLight ? "text-slate-500 hover:text-slate-800" : "text-slate-400 hover:text-slate-200")
              }`}
            >
              My Avatars
              {activeTab === "my_avatars" && (
                <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-cyan-500 rounded-full shadow-sm shadow-cyan-400"></span>
              )}
            </button>

            <button
              onClick={() => setActiveTab("public_avatars")}
              className={`transition-colors relative pb-2 cursor-pointer ${
                activeTab === "public_avatars"
                  ? (isLight ? "text-slate-900 font-extrabold" : "text-white")
                  : (isLight ? "text-slate-500 hover:text-slate-800" : "text-slate-400 hover:text-slate-200")
              }`}
            >
              Public Avatars
              {activeTab === "public_avatars" && (
                <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-cyan-500 rounded-full shadow-sm shadow-cyan-400"></span>
              )}
            </button>
          </div>
        ) : (
          <div></div>
        )}

        {/* Right Actions: New Avatar & Ask Rhys OR Close Button */}
        <div className="flex items-center gap-3">
          {!isNewAvatarMode ? (
            <>
              <button
                onClick={() => setIsNewAvatarMode(true)}
                className={`flex items-center gap-2 px-4 py-2 rounded-full text-xs font-bold transition-all shadow-sm cursor-pointer ${
                  isLight
                    ? "bg-white hover:bg-slate-50 border border-slate-200 text-slate-800"
                    : "bg-[#121828] hover:bg-[#1a243c] border border-[#243354] text-white"
                }`}
              >
                <UserPlus size={15} />
                <span>New Avatar</span>
              </button>

              <AskRhysWidget />
            </>
          ) : (
            <button
              onClick={() => setIsNewAvatarMode(false)}
              className={`w-9 h-9 rounded-full border flex items-center justify-center transition-colors cursor-pointer ${
                isLight
                  ? "border-slate-200 hover:bg-slate-100 text-slate-500 hover:text-slate-900"
                  : "border-[#22304d] hover:bg-[#18233a] text-slate-400 hover:text-white"
              }`}
              title="Close"
            >
              <X size={18} />
            </button>
          )}
        </div>
      </div>

      {/* 2. MAIN CONTENT VIEW */}
      {activeTab === "my_avatars" || isNewAvatarMode ? (
        <div className="max-w-5xl w-full mx-auto px-6 py-10 flex flex-col items-center justify-center flex-1">
          {/* Main Hero Header */}
          <div className="text-center mb-9">
            <h1 className={`text-3xl md:text-4xl font-extrabold tracking-tight mb-2 ${isLight ? "text-slate-900" : "text-white"}`}>
              {isNewAvatarMode ? "Create a new avatar" : "Create Your First Avatar"}
            </h1>
            <p className={`text-xs md:text-sm max-w-xl mx-auto ${isLight ? "text-slate-600" : "text-slate-400"}`}>
              Create an identity that looks, moves, and sounds consistently in any outfit and setting.{" "}
              <button
                onClick={() => alert("Opening avatar creation guide & best practices...")}
                className={`underline underline-offset-4 hover:text-cyan-500 transition-colors cursor-pointer ${isLight ? "text-slate-700" : "text-slate-300"}`}
              >
                View the guide
              </button>
            </p>
          </div>

          {/* 2 Big Choice Cards Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 w-full max-w-4xl">
            {/* Card 1: Clone a real person */}
            <div
              onClick={() => setIsWizardOpen(true)}
              className={`rounded-3xl overflow-hidden shadow-lg hover:shadow-2xl transition-all duration-300 flex flex-col cursor-pointer group border ${
                isLight
                  ? "bg-white border-slate-200 hover:border-cyan-500 hover:shadow-cyan-500/10"
                  : "bg-[#0c111e] border-[#1d273f] hover:border-cyan-500/70 hover:shadow-cyan-500/10"
              }`}
            >
              {/* Visual Banner Header */}
              <div className={`h-56 relative overflow-hidden flex items-center justify-center ${
                isLight ? "bg-gradient-to-tr from-slate-100 via-sky-50 to-blue-50" : "bg-gradient-to-tr from-[#111728] via-[#162035] to-[#0d1222]"
              }`}>
                <div className="absolute inset-0 flex items-center justify-center gap-2 p-4">
                  <div className="w-28 h-36 rounded-2xl bg-gradient-to-b from-blue-400/20 to-blue-900/40 border border-blue-400/40 flex items-center justify-center text-4xl shadow-lg transform -rotate-6 group-hover:-rotate-8 transition-transform">
                    👨🏼‍💼
                  </div>
                  <div className="w-32 h-44 rounded-2xl bg-gradient-to-b from-purple-400/30 to-purple-900/50 border border-cyan-400/60 flex items-center justify-center text-5xl shadow-2xl z-10 group-hover:scale-105 transition-transform">
                    👩🏼‍💼
                  </div>
                  <div className="w-28 h-36 rounded-2xl bg-gradient-to-b from-emerald-400/20 to-emerald-900/40 border border-emerald-400/40 flex items-center justify-center text-4xl shadow-lg transform rotate-6 group-hover:rotate-8 transition-transform">
                    👩🏽‍💼
                  </div>
                </div>

                <div className="absolute top-2 left-1/4 w-32 h-32 rounded-full border-2 border-cyan-400/30 pointer-events-none"></div>
                <div className="absolute bottom-2 right-1/4 w-32 h-32 rounded-full border-2 border-purple-400/30 pointer-events-none"></div>
              </div>

              {/* Text Body */}
              <div className={`p-6 flex flex-col flex-1 justify-between ${isLight ? "bg-white" : "bg-[#0c111e]"}`}>
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <h3 className={`text-lg font-bold transition-colors ${isLight ? "text-slate-900 group-hover:text-cyan-600" : "text-white group-hover:text-cyan-400"}`}>
                      Clone a real person
                    </h3>
                    <span className="text-[10px] font-bold text-purple-700 dark:text-purple-300 bg-purple-100 dark:bg-purple-900/40 border border-purple-200 dark:border-purple-500/30 px-2 py-0.5 rounded-md">
                      Avatar V
                    </span>
                  </div>
                  <p className={`text-xs leading-relaxed ${isLight ? "text-slate-600" : "text-slate-400"}`}>
                    Use real video footage to create an avatar that looks, moves, and sounds like you.
                  </p>
                </div>

                <div className={`mt-4 pt-3 flex items-center justify-between text-xs font-semibold ${isLight ? "border-t border-slate-100 text-cyan-600" : "border-t border-[#19243d] text-cyan-400"}`}>
                  <span>Start recording or upload video</span>
                  <ChevronRight size={15} className="group-hover:translate-x-1 transition-transform" />
                </div>
              </div>
            </div>

            {/* Card 2: Create a virtual character */}
            <div
              className={`rounded-3xl overflow-hidden shadow-lg transition-all duration-300 flex flex-col relative group ${
                isLight ? "bg-white" : "bg-[#0c111e]"
              } ${
                isNewAvatarMode
                  ? "border-2 border-cyan-400 shadow-2xl shadow-cyan-500/15"
                  : isLight
                  ? "border border-slate-200 hover:border-purple-500/70"
                  : "border border-[#1d273f] hover:border-purple-500/70"
              }`}
            >
              <div className={`h-56 relative overflow-hidden flex items-center justify-center ${
                isLight ? "bg-gradient-to-tr from-purple-50 via-indigo-50 to-slate-100" : "bg-gradient-to-tr from-[#151022] via-[#1e1533] to-[#0d0a17]"
              }`}>
                <div className="absolute inset-0 flex items-center justify-center gap-2 p-4 opacity-75">
                  <div className="w-28 h-36 rounded-2xl bg-gradient-to-b from-amber-400/20 to-amber-900/40 border border-amber-400/40 flex items-center justify-center text-4xl shadow-lg transform -rotate-6">
                    🧝‍♂️
                  </div>
                  <div className="w-32 h-44 rounded-2xl bg-gradient-to-b from-indigo-400/30 to-indigo-900/50 border border-purple-400/60 flex items-center justify-center text-5xl shadow-2xl z-10">
                    🧙‍♂️
                  </div>
                  <div className="w-28 h-36 rounded-2xl bg-gradient-to-b from-cyan-400/20 to-cyan-900/40 border border-cyan-400/40 flex items-center justify-center text-4xl shadow-lg transform rotate-6">
                    🤖
                  </div>
                </div>

                <div className="relative z-20 flex flex-col items-center gap-3 w-full px-8">
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    className="w-full max-w-[210px] py-2.5 px-5 bg-black/85 hover:bg-black text-white border border-white/10 text-xs font-bold rounded-full backdrop-blur-md shadow-xl flex items-center justify-center gap-2 hover:scale-105 transition-all cursor-pointer"
                  >
                    <Upload size={14} />
                    <span>Upload photo</span>
                  </button>

                  <button
                    onClick={() => setIsVirtualModalOpen(true)}
                    className="w-full max-w-[210px] py-2.5 px-5 bg-black/85 hover:bg-black text-white border border-white/10 text-xs font-bold rounded-full backdrop-blur-md shadow-xl flex items-center justify-center gap-2 hover:scale-105 transition-all cursor-pointer"
                  >
                    <Wand2 size={14} />
                    <span>Design with AI</span>
                  </button>
                </div>
              </div>

              <div className={`p-6 flex flex-col flex-1 justify-between ${isLight ? "bg-white" : "bg-[#0c111e]"}`}>
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <h3 className={`text-lg font-bold transition-colors ${isLight ? "text-slate-900 group-hover:text-purple-600" : "text-white group-hover:text-purple-400"}`}>
                      Create a virtual character
                    </h3>
                  </div>
                  <p className={`text-xs leading-relaxed ${isLight ? "text-slate-600" : "text-slate-400"}`}>
                    Start with an image, and bring it to life with unique motion and voice.
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Bottom Switch to Public Avatars Link */}
          {!isNewAvatarMode && (
            <div className="mt-10">
              <button
                onClick={() => setActiveTab("public_avatars")}
                className={`inline-flex items-center gap-2 text-xs font-bold transition-colors cursor-pointer group ${
                  isLight ? "text-slate-600 hover:text-cyan-600" : "text-slate-300 hover:text-cyan-400"
                }`}
              >
                <span>Try a Public Avatar</span>
                <ArrowRight size={14} className="group-hover:translate-x-1 transition-transform" />
              </button>
            </div>
          )}
        </div>
      ) : (
        /* PUBLIC AVATARS GALLERY VIEW */
        <div className="max-w-7xl w-full mx-auto px-8 py-6 flex-1">
          {/* Filter Bar */}
          <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
            <div className="flex flex-wrap items-center gap-2">
              {["All", "Professional", "Lifestyle", "UGC", "Community"].map((cat) => (
                <button
                  key={cat}
                  onClick={() => setSelectedCategory(cat)}
                  className={`px-3.5 py-1.5 rounded-full text-xs font-semibold transition-colors cursor-pointer ${
                    selectedCategory === cat
                      ? "bg-blue-600 text-white shadow-sm font-bold"
                      : isLight
                      ? "bg-white text-slate-600 hover:text-slate-900 border border-slate-200"
                      : "bg-[#121828] text-slate-400 hover:text-white border border-[#1e2a44]"
                  }`}
                >
                  {cat}
                </button>
              ))}
            </div>

            <div className="relative w-64">
              <Search size={14} className="absolute left-3 top-2.5 text-slate-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search avatars..."
                className={`w-full rounded-xl pl-9 pr-8 py-1.5 text-xs focus:outline-none focus:border-blue-500 border ${
                  isLight
                    ? "bg-white border-slate-200 text-slate-900 placeholder-slate-400"
                    : "bg-[#121828] border-[#1e2a44] text-white placeholder-slate-400"
                }`}
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery("")}
                  className={`absolute right-2.5 top-2 cursor-pointer ${isLight ? "text-slate-400 hover:text-slate-700" : "text-slate-400 hover:text-white"}`}
                >
                  <X size={13} />
                </button>
              )}
            </div>
          </div>

          {/* Avatars Grid (High-Res Curated Public Avatars) */}
          {isLoadingAvatars ? (
            <div className={`p-16 text-center rounded-2xl flex flex-col items-center justify-center border ${
              isLight ? "bg-white border-slate-200" : "bg-[#090d17] border-[#172035]"
            }`}>
              <div className="w-8 h-8 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin mb-3"></div>
              <p className={`text-xs ${isLight ? "text-slate-500" : "text-slate-400"}`}>Loading avatars from backend...</p>
            </div>
          ) : avatarError ? (
            <div className={`p-12 text-center rounded-2xl border ${
              isLight ? "bg-rose-50/50 border-rose-200" : "bg-[#090d17] border-red-500/30"
            }`}>
              <p className="text-sm text-red-500 font-semibold mb-1">Failed to load avatars</p>
              <p className="text-xs text-slate-500 mb-4">{avatarError}</p>
              <button
                onClick={fetchAvatars}
                className="px-4 py-2 bg-blue-600 text-white rounded-xl text-xs font-semibold hover:bg-blue-500 transition-colors"
              >
                Retry
              </button>
            </div>
          ) : filteredPublicAvatars.length === 0 ? (
            <div className={`p-12 text-center rounded-2xl border ${
              isLight ? "bg-white border-slate-200" : "bg-[#090d17] border-[#172035]"
            }`}>
              <p className={`text-sm font-semibold mb-1 ${isLight ? "text-slate-700" : "text-slate-300"}`}>No avatars found</p>
              <p className="text-xs text-slate-500">Try adjusting your category filter or search query</p>
            </div>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4 pb-12">
              {filteredPublicAvatars.map((avatar) => {
                const isSelected = selectedAvatarId === avatar.id;

                return (
                  <div
                    key={avatar.id}
                    className={`border rounded-2xl overflow-hidden shadow-sm hover:shadow-xl transition-all flex flex-col group cursor-pointer ${
                      isLight ? "bg-white" : "bg-[#0d1222]"
                    } ${
                      isSelected
                        ? "border-cyan-500 ring-2 ring-cyan-500/20"
                        : isLight
                        ? "border-slate-200 hover:border-cyan-500"
                        : "border-[#1d273f] hover:border-cyan-500/60"
                    }`}
                  >
                    <div className="aspect-[3/4] relative overflow-hidden bg-slate-900">
                      <img
                        src={avatar.image}
                        alt={avatar.name}
                        className="w-full h-full object-cover object-top group-hover:scale-104 transition-transform duration-300"
                      />
                      {avatar.isNew && (
                        <span className="absolute top-2 left-2 text-[9px] font-extrabold bg-cyan-500 text-white px-2 py-0.5 rounded-full shadow-xs">
                          NEW
                        </span>
                      )}
                      {isSelected && (
                        <div className="absolute top-2 right-2 w-5 h-5 rounded-full bg-cyan-500 text-white flex items-center justify-center shadow-xs">
                          <Check size={11} strokeWidth={3} />
                        </div>
                      )}
                    </div>

                    <div className={`p-3 flex flex-col justify-between flex-1 ${isLight ? "bg-white" : "bg-[#0d1222]"}`}>
                      <div>
                        <h4 className={`text-xs font-bold truncate ${isLight ? "text-slate-900" : "text-white"}`}>
                          {avatar.name}
                        </h4>
                        <p className={`text-[10px] truncate mt-0.5 ${isLight ? "text-slate-500" : "text-slate-400"}`}>
                          {avatar.looks} looks • {avatar.filterCategory || avatar.type}
                        </p>
                      </div>

                      <button
                        onClick={() => {
                          if (onSelectAvatar) {
                            onSelectAvatar(avatar);
                          } else if (onOpenStudio) {
                            onOpenStudio();
                          }
                        }}
                        className={`w-full mt-2.5 py-1.5 text-[11px] font-bold rounded-lg transition-colors cursor-pointer ${
                          isSelected
                            ? "bg-cyan-500 text-white"
                            : "bg-blue-600 hover:bg-blue-500 text-white"
                        }`}
                      >
                        {isSelected ? "Selected" : "Use Avatar"}
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Virtual Character Generation Modal */}
      {isVirtualModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-md p-4 animate-in fade-in duration-200">
          <div className={`w-full max-w-lg rounded-3xl p-6 shadow-2xl border ${
            isLight ? "bg-white text-slate-900 border-slate-200" : "bg-[#0e1322] text-white border-[#22304f]"
          }`}>
            <h3 className={`text-lg font-bold mb-1 ${isLight ? "text-slate-900" : "text-white"}`}>Create Virtual AI Character</h3>
            <p className={`text-xs mb-4 ${isLight ? "text-slate-600" : "text-slate-400"}`}>
              Describe the character you want to bring to life with voice and expressive gestures.
            </p>

            <textarea
              rows={3}
              value={characterPrompt}
              onChange={(e) => setCharacterPrompt(e.target.value)}
              placeholder="e.g. A friendly 3D Pixar-style robotic character with expressive glowing blue eyes..."
              className={`w-full rounded-2xl p-3.5 text-xs focus:outline-none focus:border-purple-500 mb-4 border ${
                isLight ? "bg-slate-50 border-slate-200 text-slate-900 placeholder-slate-400" : "bg-[#121828] border-[#22304d] text-white placeholder-slate-400"
              }`}
            ></textarea>

            <div className="flex justify-end gap-2.5">
              <button
                onClick={() => setIsVirtualModalOpen(false)}
                className={`px-4 py-2 rounded-xl text-xs font-semibold cursor-pointer ${
                  isLight ? "text-slate-600 hover:bg-slate-100" : "text-slate-400 hover:bg-[#18233a]"
                }`}
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  alert("GPU_UNAVAILABLE: Virtual 3D character animation requires NVIDIA CUDA GPU acceleration (CUDA VALIDATION PENDING).");
                  setIsVirtualModalOpen(false);
                }}
                className="px-5 py-2 bg-gradient-to-r from-purple-600 to-indigo-600 text-white text-xs font-bold rounded-xl shadow-md cursor-pointer"
              >
                Generate Character
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
