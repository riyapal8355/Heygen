"use client";

import React, { useState, useRef } from "react";
import {
  Play,
  Pause,
  Sparkles,
  ChevronDown,
  RefreshCw,
  Mic,
  Upload,
  Volume2,
  Film,
  RectangleHorizontal,
  Square,
  Layers,
  User,
  Bot,
  Video,
  Check,
  X,
} from "lucide-react";
import AskRhysWidget from "../dashboard/AskRhysWidget";
import { api, ProjectDocumentV1 } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";

interface SingleSceneProps {
  onOpenStudio?: (projectId?: string) => void;
  onNavigateVoices?: () => void;
  onSeeAllProjects?: () => void;
}

export default function SingleScene({
  onOpenStudio,
  onNavigateVoices,
  onSeeAllProjects,
}: SingleSceneProps) {
  const { currentWorkspace } = useAuth();

  // Mode selection: Presenter | Avatar IV | Cinematic
  const [selectedMode, setSelectedMode] = useState<"presenter" | "avatar_iv" | "cinematic">("avatar_iv");

  // Script text
  const [scriptText, setScriptText] = useState("");

  // Voice selection
  const [selectedVoice, setSelectedVoice] = useState("Matteo");
  const [isVoiceDropdownOpen, setIsVoiceDropdownOpen] = useState(false);

  // Mode Info Popover state ("avatar_iv" | "cinematic" | null)
  const [activeInfoPopover, setActiveInfoPopover] = useState<"avatar_iv" | "cinematic" | null>(null);

  // Selected Model in bottom bar
  const [selectedModel, setSelectedModel] = useState("Avatar IV");
  const [isModelDropdownOpen, setIsModelDropdownOpen] = useState(false);

  // Avatar IV selection
  const [selectedAvatar, setSelectedAvatar] = useState({
    id: "matteo-avatar",
    name: "Matteo",
    role: "Professional Presenter",
    image: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?q=80&w=700&auto=format&fit=crop",
  });
  const [isAvatarDropdownOpen, setIsAvatarDropdownOpen] = useState(false);

  // Aspect ratio: 16:9 | 9:16
  const [aspectRatio, setAspectRatio] = useState<"16:9" | "9:16">("16:9");
  const [isRatioDropdownOpen, setIsRatioDropdownOpen] = useState(false);

  // Resolution: 720p | 1080p | 4K
  const [resolution, setResolution] = useState("720p");
  const [isResDropdownOpen, setIsResDropdownOpen] = useState(false);

  // Audio Playback state
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);

  // Toast feedback
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // Generating state
  const [isGenerating, setIsGenerating] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Outside click listener for popovers
  React.useEffect(() => {
    const handleOutsideClick = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      if (!target.closest(".mode-info-popover-container")) {
        setActiveInfoPopover(null);
      }
      if (!target.closest(".model-dropdown-container")) {
        setIsModelDropdownOpen(false);
      }
      if (!target.closest(".voice-dropdown-container")) {
        setIsVoiceDropdownOpen(false);
      }
      if (!target.closest(".ratio-dropdown-container")) {
        setIsRatioDropdownOpen(false);
      }
      if (!target.closest(".res-dropdown-container")) {
        setIsResDropdownOpen(false);
      }
    };
    document.addEventListener("click", handleOutsideClick);
    return () => document.removeEventListener("click", handleOutsideClick);
  }, []);

  const modelsList = [
    {
      id: "Avatar V",
      name: "Avatar V",
      description: "Character consistent motion style that adapts to script.",
      iconBg: "bg-purple-600 text-white shadow-sm shadow-purple-500/20",
      iconText: "V",
      isPremium: true,
    },
    {
      id: "Avatar IV",
      name: "Avatar IV",
      description: "Generic motion that adapts to script.",
      iconBg: "bg-slate-800 text-cyan-400 border border-slate-700 shadow-sm",
      iconText: "IV",
      isPremium: false,
    },
    {
      id: "Avatar III",
      name: "Avatar III",
      description: "Applies lip sync.",
      iconBg: "bg-amber-500/20 text-amber-400 border border-amber-500/40",
      iconText: "III",
      isPremium: false,
    },
  ];

  const availableVoices = [
    { name: "Matteo", lang: "English (US)", accent: "Natural & Expressive" },
    { name: "Sarah", lang: "English (US)", accent: "Warm & Friendly" },
    { name: "Oliver", lang: "English (UK)", accent: "Professional" },
    { name: "Elena", lang: "Spanish (ES)", accent: "Clear & Crisp" },
  ];

  const availableAvatars = [
    {
      id: "matteo-avatar",
      name: "Matteo",
      role: "Professional Presenter",
      image: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?q=80&w=700&auto=format&fit=crop",
    },
    {
      id: "sarah-avatar",
      name: "Sarah",
      role: "Corporate Lead",
      image: "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?q=80&w=700&auto=format&fit=crop",
    },
    {
      id: "marcus-avatar",
      name: "Marcus",
      role: "Tech Host",
      image: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?q=80&w=700&auto=format&fit=crop",
    },
  ];

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => {
      setToastMessage((prev) => (prev === msg ? null : prev));
    }, 3000);
  };

  const handlePlayPreview = () => {
    if (isPlayingAudio) {
      if (typeof window !== "undefined" && window.speechSynthesis) {
        window.speechSynthesis.cancel();
      }
      setIsPlayingAudio(false);
      return;
    }

    const textToSpeak = scriptText.trim() || "Hello! This is a preview of your avatar's speech in AI Studio.";
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(textToSpeak);
      utterance.rate = 1.0;
      utterance.onend = () => setIsPlayingAudio(false);
      utterance.onerror = () => setIsPlayingAudio(false);
      setIsPlayingAudio(true);
      window.speechSynthesis.speak(utterance);
    } else {
      showToast("Speech synthesis preview started");
      setIsPlayingAudio(true);
      setTimeout(() => setIsPlayingAudio(false), 2500);
    }
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      showToast(`Uploaded ${file.name}`);
      const reader = new FileReader();
      reader.onload = (event) => {
        if (typeof event.target?.result === "string") {
          setScriptText(event.target.result.slice(0, 1000));
        }
      };
      reader.readAsText(file);
    }
  };

  const handleGenerate = async () => {
    if (isGenerating) return;
    if (!currentWorkspace?.id) {
      showToast("No active workspace found");
      return;
    }
    try {
      setIsGenerating(true);
      showToast("Creating project in workspace...");

      // 1. Create a real Project in PostgreSQL
      const project = await api.projects.create(currentWorkspace.id, {
        title: scriptText.slice(0, 30).trim() || "Single Scene Video",
        aspect_ratio: aspectRatio,
      });

      // 2. If user entered script text, update project document with the scene script
      if (scriptText.trim()) {
        const doc = {
          schema_version: 1,
          settings: {
            aspect_ratio: aspectRatio,
            width: aspectRatio === "9:16" ? 1080 : 1920,
            height: aspectRatio === "9:16" ? 1920 : 1080,
            fps: 30,
            total_duration: 5.0,
          },
          scenes: [
            {
              id: "scene-1",
              sequence: 1,
              duration: 5.0,
              background: { type: "color", value: "#0F172A" },
              avatar: selectedAvatar?.id
                ? {
                    avatar_id: selectedAvatar.id,
                    position: { x: 0.5, y: 0.65, scale: 1.0, rotation: 0.0 },
                    view_mode: "half_body",
                  }
                : null,
              speech: {
                voice_id: selectedVoice || "default-voice",
                script: scriptText.trim(),
                speed: 1.0,
                pitch: 0.0,
              },
              layers: [],
              subtitles: [],
            },
          ],
          audio_tracks: [],
          assets: [],
          metadata: {
            title: scriptText.slice(0, 30).trim() || "Single Scene Video",
          },
        };
        await api.projects.createVersion(currentWorkspace.id, project.id, {
          expected_revision: 1,
          document: doc,
          source: "single_scene",
        });
      }

      showToast("Project created successfully!");
      if (onOpenStudio) {
        onOpenStudio(project.id);
      }
    } catch (err: any) {
      showToast(err?.message || "Failed to create project");
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="flex-1 h-screen overflow-y-auto bg-[#07090e] text-slate-100 flex flex-col font-sans select-none relative scrollbar-thin scrollbar-thumb-[#151c2d]">
      {/* Toast Feedback */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 bg-[#18233c] text-white border border-[#2b3a5d]/50 text-xs font-semibold px-4 py-2.5 rounded-xl shadow-2xl flex items-center gap-2 animate-in fade-in slide-in-from-bottom-3 duration-200">
          <Sparkles size={14} className="text-cyan-400" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Hidden File Input for Upload */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileUpload}
        accept=".txt,.doc,.docx,.pdf,.srt"
        className="hidden"
      />

      {/* 1. TOP HEADER (Centered Greeting & Ask Rhys on Right) */}
      <header className="w-full px-8 sm:px-12 pt-8 pb-4 flex items-center justify-between bg-[#07090e] z-20">
        <div className="w-24 hidden sm:block"></div>

        <div className="text-center flex-1">
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            What should your avatar say?
          </h1>
        </div>

        <div className="flex items-center gap-3">
          <AskRhysWidget variant="banner" />
        </div>
      </header>

      {/* 2. MODE SWITCHER (Segmented Control) */}
      <div className="flex justify-center mt-2 mb-8 px-4 relative z-40">
        <div className="bg-[#0b111e] p-1 rounded-full inline-flex items-center gap-1 border border-[#1b2940] shadow-sm relative mode-info-popover-container">
          <button
            type="button"
            onClick={() => {
              setSelectedMode("presenter");
              setActiveInfoPopover(null);
            }}
            className={`px-4 sm:px-6 py-2 rounded-full text-xs sm:text-sm font-bold transition-all cursor-pointer flex items-center gap-1.5 ${
              selectedMode === "presenter"
                ? "bg-[#18233c] text-white shadow-xs border border-[#2b3a5d]/50"
                : "text-slate-400 hover:text-white hover:bg-[#101828]"
            }`}
          >
            <User size={14} />
            <span>Presenter</span>
          </button>

          <button
            type="button"
            onClick={() => {
              setSelectedMode("avatar_iv");
              setActiveInfoPopover(activeInfoPopover === "avatar_iv" ? null : "avatar_iv");
            }}
            className={`px-4 sm:px-6 py-2 rounded-full text-xs sm:text-sm font-bold transition-all cursor-pointer flex items-center gap-1.5 ${
              selectedMode === "avatar_iv"
                ? "bg-[#18233c] text-white shadow-xs border border-[#2b3a5d]/50"
                : "text-slate-400 hover:text-white hover:bg-[#101828]"
            }`}
          >
            <Bot size={14} />
            <span>Avatar IV</span>
          </button>

          <button
            type="button"
            onClick={() => {
              setSelectedMode("cinematic");
              setActiveInfoPopover(activeInfoPopover === "cinematic" ? null : "cinematic");
            }}
            className={`px-4 sm:px-6 py-2 rounded-full text-xs sm:text-sm font-bold transition-all cursor-pointer flex items-center gap-1.5 ${
              selectedMode === "cinematic"
                ? "bg-[#18233c] text-white shadow-xs border border-[#2b3a5d]/50"
                : "text-slate-400 hover:text-white hover:bg-[#101828]"
            }`}
          >
            <Film size={14} />
            <span>Cinematic</span>
          </button>

          {/* Floating Information Popover for Avatar IV / Cinematic */}
          {activeInfoPopover && (
            <div
              onClick={(e) => e.stopPropagation()}
              className="absolute top-full mt-3 left-1/2 -translate-x-1/2 w-[360px] xs:w-[420px] sm:w-[500px] max-w-[92vw] bg-[#17181c] border border-white/10 rounded-[28px] sm:rounded-[32px] p-5 shadow-[0_25px_60px_rgba(0,0,0,0.55)] z-50 text-white animate-in fade-in zoom-in-95 duration-150"
            >
              {/* Pointer Triangle pointing toward the active tab */}
              <div
                className={`absolute -top-2 w-4 h-4 bg-[#17181c] rotate-45 border-l border-t border-white/10 z-10 transition-all duration-200 ${
                  activeInfoPopover === "avatar_iv"
                    ? "left-1/2 -translate-x-1/2"
                    : "left-[82%] sm:left-[84%] -translate-x-1/2"
                }`}
              ></div>

              {/* 1. Top Preview Image / Video Area */}
              <div className="w-full aspect-[16/9] rounded-2xl overflow-hidden relative shadow-md bg-black border border-white/10">
                <img
                  src={
                    activeInfoPopover === "avatar_iv"
                      ? "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?q=80&w=900&auto=format&fit=crop"
                      : "https://images.unsplash.com/photo-1534430480872-3498386e7856?q=80&w=900&auto=format&fit=crop"
                  }
                  alt={activeInfoPopover === "avatar_iv" ? "Avatar IV Presenter" : "Cinematic Scene in City"}
                  className="w-full h-full object-cover object-center brightness-95"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-black/20"></div>

                {/* Top Left Badge */}
                <div className="absolute top-3 left-3">
                  <span className="bg-black/60 backdrop-blur-sm text-white text-[10px] font-bold px-2.5 py-0.5 rounded-full border border-white/10 flex items-center gap-1 shadow-sm">
                    {activeInfoPopover === "avatar_iv" ? (
                      <>
                        <Sparkles size={11} className="text-cyan-400" />
                        <span className="text-cyan-300">Avatar IV</span>
                      </>
                    ) : (
                      <>
                        <Film size={11} className="text-amber-400" />
                        <span className="text-amber-300">Cinematic</span>
                      </>
                    )}
                  </span>
                </div>
              </div>

              {/* 2. Heading: "If you want to..." */}
              <div className="mt-4 px-1">
                <h4 className="text-sm sm:text-base font-bold text-white tracking-tight">
                  If you want to...
                </h4>

                {/* 3. Bullet Points */}
                <ul className="mt-2.5 space-y-2 text-xs sm:text-[13px] text-slate-300 leading-relaxed">
                  {activeInfoPopover === "avatar_iv" ? (
                    <>
                      <li className="flex items-start gap-2.5">
                        <span className="text-cyan-400 font-bold select-none">•</span>
                        <span>Turn a script or idea into a clear talking video.</span>
                      </li>
                      <li className="flex items-start gap-2.5">
                        <span className="text-cyan-400 font-bold select-none">•</span>
                        <span>Create longer videos (training, explainers, updates).</span>
                      </li>
                      <li className="flex items-start gap-2.5">
                        <span className="text-cyan-400 font-bold select-none">•</span>
                        <span>Generate consistent, high-quality videos at scale.</span>
                      </li>
                    </>
                  ) : (
                    <>
                      <li className="flex items-start gap-2.5">
                        <span className="text-amber-400 font-bold select-none">•</span>
                        <span>Create short, cinematic clips (ads, hooks, social).</span>
                      </li>
                      <li className="flex items-start gap-2.5">
                        <span className="text-amber-400 font-bold select-none">•</span>
                        <span>Direct camera, lighting, and full-body performance.</span>
                      </li>
                      <li className="flex items-start gap-2.5">
                        <span className="text-amber-400 font-bold select-none">•</span>
                        <span>Stage interactions across people, products, and places.</span>
                      </li>
                    </>
                  )}
                </ul>
              </div>

              {/* 4. Divider Line */}
              <div className="h-px bg-white/10 my-4 mx-1"></div>

              {/* 5. Bottom Stats Row (4 Equal Columns with Vertical Separators) */}
              <div className="grid grid-cols-4 divide-x divide-white/10 text-center py-1">
                {activeInfoPopover === "avatar_iv" ? (
                  <>
                    <div className="px-1 sm:px-2">
                      <div className="text-sm sm:text-base font-extrabold text-white tracking-tight">30 min</div>
                      <div className="text-[10px] sm:text-[11px] text-slate-400 mt-0.5 font-medium">Max length</div>
                    </div>
                    <div className="px-1 sm:px-2">
                      <div className="text-sm sm:text-base font-extrabold text-white tracking-tight">175+</div>
                      <div className="text-[10px] sm:text-[11px] text-slate-400 mt-0.5 font-medium">Languages</div>
                    </div>
                    <div className="px-1 sm:px-2">
                      <div className="text-sm sm:text-base font-extrabold text-white tracking-tight">#1</div>
                      <div className="text-[10px] sm:text-[11px] text-slate-400 mt-0.5 font-medium">For lip sync</div>
                    </div>
                    <div className="px-1 sm:px-2">
                      <div className="text-sm sm:text-base font-extrabold text-white tracking-tight">0.3</div>
                      <div className="text-[10px] sm:text-[11px] text-slate-400 mt-0.5 font-medium">Credits/sec</div>
                    </div>
                  </>
                ) : (
                  <>
                    <div className="px-1 sm:px-2">
                      <div className="text-sm sm:text-base font-extrabold text-white tracking-tight">15 sec</div>
                      <div className="text-[10px] sm:text-[11px] text-slate-400 mt-0.5 font-medium">Max length</div>
                    </div>
                    <div className="px-1 sm:px-2">
                      <div className="text-sm sm:text-base font-extrabold text-white tracking-tight">360°</div>
                      <div className="text-[10px] sm:text-[11px] text-slate-400 mt-0.5 font-medium">Camera control</div>
                    </div>
                    <div className="px-1 sm:px-2">
                      <div className="text-sm sm:text-base font-extrabold text-white tracking-tight">3+</div>
                      <div className="text-[10px] sm:text-[11px] text-slate-400 mt-0.5 font-medium">References</div>
                    </div>
                    <div className="px-1 sm:px-2">
                      <div className="text-sm sm:text-base font-extrabold text-white tracking-tight">60</div>
                      <div className="text-[10px] sm:text-[11px] text-slate-400 mt-0.5 font-medium">Credits</div>
                    </div>
                  </>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 3. MAIN WORKSPACE CONTAINER */}
      <main className="max-w-4xl w-full mx-auto px-6 sm:px-8 pb-16 space-y-12 flex-1">
        {/* ================= SECTION 1: VIDEO SCRIPT CARD ================= */}
        <div className="bg-[#0b111e] border border-[#1b2940] rounded-3xl p-6 sm:p-7 shadow-xl space-y-5">
          {/* Card Body: Left Avatar Preview + Right Script Area */}
          <div className="flex flex-col md:flex-row gap-6 items-stretch">
            {/* Left: Vertical Avatar Preview */}
            <div
              onClick={() => setIsAvatarDropdownOpen(!isAvatarDropdownOpen)}
              className="w-full md:w-56 aspect-[3/4] md:aspect-auto rounded-2xl bg-slate-950 overflow-hidden relative shadow-md border border-[#1b2940] group cursor-pointer shrink-0 flex flex-col justify-end"
            >
              <img
                src={selectedAvatar.image}
                alt={selectedAvatar.name}
                className="absolute inset-0 w-full h-full object-cover object-top group-hover:scale-105 transition-transform duration-500 brightness-95"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-black/20"></div>

              {/* Hover Switch Indicator */}
              <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-200 bg-black/30 backdrop-blur-[2px]">
                <div className="px-3 py-1.5 rounded-full bg-white text-slate-900 text-xs font-bold flex items-center gap-1.5 shadow-md">
                  <RefreshCw size={13} className="text-slate-700 animate-spin-reverse" />
                  <span>Change</span>
                </div>
              </div>

              {/* Avatar Name Tag */}
              <div className="p-3.5 z-10 relative">
                <span className="bg-black/60 backdrop-blur-sm text-white text-[10px] font-semibold px-2.5 py-0.5 rounded-full border border-white/10">
                  {selectedAvatar.name}
                </span>
              </div>
            </div>

            {/* Right: Main Video Script Input */}
            <div className="flex-1 flex flex-col justify-between">
              <div>
                <label className="text-[10px] sm:text-[11px] font-extrabold uppercase tracking-wider text-slate-300 block mb-2">
                  Video Script
                </label>
                <textarea
                  value={scriptText}
                  onChange={(e) => setScriptText(e.target.value)}
                  placeholder="Type your script, or upload/record"
                  className="w-full h-36 sm:h-44 resize-none bg-transparent text-slate-100 placeholder:text-slate-500 text-sm sm:text-base leading-relaxed focus:outline-none focus:ring-0 border-none p-0"
                />
              </div>

              {/* Upload or Record Clickable Prompt */}
              <div className="flex items-center gap-3 pt-2 text-xs text-slate-400 border-t border-[#1b2940]">
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="text-cyan-400 hover:text-cyan-300 font-semibold hover:underline cursor-pointer flex items-center gap-1"
                >
                  <Upload size={13} />
                  <span>Upload script file</span>
                </button>
                <span className="text-slate-600">•</span>
                <button
                  type="button"
                  onClick={() => showToast("Microphone audio recorder ready")}
                  className="text-cyan-400 hover:text-cyan-300 font-semibold hover:underline cursor-pointer flex items-center gap-1"
                >
                  <Mic size={13} />
                  <span>Record speech</span>
                </button>
                <span className="ml-auto text-[11px] text-slate-500">
                  {scriptText.length} chars
                </span>
              </div>
            </div>
          </div>

          {/* Bottom Controls Bar */}
          <div className="border-t border-[#1b2940] pt-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            {/* Left Control Pills */}
            <div className="flex flex-wrap items-center gap-2 relative">
              {/* 1. Model Selector Pill */}
              <div className="relative model-dropdown-container">
                <button
                  type="button"
                  onClick={() => {
                    setIsModelDropdownOpen(!isModelDropdownOpen);
                    setIsVoiceDropdownOpen(false);
                    setIsRatioDropdownOpen(false);
                    setIsResDropdownOpen(false);
                  }}
                  className={`px-3.5 py-1.5 border rounded-full text-xs font-semibold transition-all cursor-pointer flex items-center gap-1.5 shadow-2xs ${
                    isModelDropdownOpen
                      ? "bg-[#18233c] border-[#2b3a5d] text-white"
                      : "bg-[#121828] hover:bg-[#18233c] border-[#1b2940] text-slate-200 hover:text-white"
                  }`}
                >
                  {selectedModel === "Avatar V" ? (
                    <div className="w-3.5 h-3.5 rounded-full bg-purple-600 text-[8px] font-black text-white flex items-center justify-center shrink-0">
                      V
                    </div>
                  ) : selectedModel === "Avatar III" ? (
                    <div className="w-3.5 h-3.5 rounded-full bg-amber-500/20 text-[7px] font-black text-amber-400 border border-amber-500/40 flex items-center justify-center shrink-0">
                      III
                    </div>
                  ) : (
                    <div className="w-3.5 h-3.5 rounded-full bg-slate-800 text-[7px] font-black text-cyan-400 border border-slate-700 flex items-center justify-center shrink-0">
                      IV
                    </div>
                  )}
                  <span>{selectedModel}</span>
                  {selectedModel === "Avatar V" && (
                    <Sparkles size={11} className="text-cyan-400 fill-cyan-400 -ml-0.5 shrink-0" />
                  )}
                  <ChevronDown size={13} className="text-slate-400" />
                </button>

                {isModelDropdownOpen && (
                  <div className="absolute left-0 top-full mt-2 w-[340px] xs:w-[420px] sm:w-[500px] max-w-[92vw] bg-[#0b111e] rounded-2xl shadow-2xl border border-[#1b2940] p-2 sm:p-2.5 z-50 animate-in fade-in zoom-in-95 duration-150 space-y-1">
                    {modelsList.map((model) => {
                      const isSelected = selectedModel === model.id;
                      return (
                        <button
                          key={model.id}
                          type="button"
                          onClick={() => {
                            setSelectedModel(model.id);
                            setIsModelDropdownOpen(false);
                          }}
                          className={`w-full text-left p-3 rounded-xl transition-all flex items-center justify-between gap-3 cursor-pointer ${
                            isSelected
                              ? "bg-[#18233c] border border-[#2b3a5d]/70 text-white"
                              : "hover:bg-[#121828] border border-transparent text-slate-200"
                          }`}
                        >
                          <div className="flex items-center gap-3 min-w-0">
                            {/* Circular Icon */}
                            <div
                              className={`w-9 h-9 rounded-full flex items-center justify-center text-xs font-bold shrink-0 ${model.iconBg}`}
                            >
                              {model.iconText}
                            </div>

                            {/* Name & Description */}
                            <div className="min-w-0">
                              <div className="flex items-center gap-1.5">
                                <span className="font-bold text-white text-sm">
                                  {model.name}
                                </span>
                                {model.isPremium && (
                                  <Sparkles size={13} className="text-cyan-400 fill-cyan-400 shrink-0" />
                                )}
                              </div>
                              <p className="text-xs text-slate-400 truncate mt-0.5">
                                {model.description}
                              </p>
                            </div>
                          </div>

                          {/* Selection Checkmark */}
                          {isSelected && (
                            <Check size={18} className="text-cyan-400 stroke-[2.5] shrink-0 ml-2" />
                          )}
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* 2. Voice Selector Pill ("Matteo") */}
              <div className="relative voice-dropdown-container">
                <button
                  type="button"
                  onClick={() => {
                    if (onNavigateVoices) {
                      onNavigateVoices();
                    } else {
                      setIsVoiceDropdownOpen(!isVoiceDropdownOpen);
                    }
                    setActiveInfoPopover(null);
                    setIsModelDropdownOpen(false);
                    setIsRatioDropdownOpen(false);
                    setIsResDropdownOpen(false);
                  }}
                  className="px-3.5 py-1.5 bg-[#121828] hover:bg-[#18233c] border border-[#1b2940] rounded-full text-xs font-semibold text-slate-200 hover:text-white transition-colors cursor-pointer flex items-center gap-1.5 shadow-2xs"
                >
                  <Volume2 size={14} className="text-slate-400" />
                  <span>{selectedVoice}</span>
                  <ChevronDown size={13} className="text-slate-400" />
                </button>
              </div>

              {/* 3. Play Preview Button */}
              <button
                type="button"
                onClick={handlePlayPreview}
                className={`w-8 h-8 rounded-full border flex items-center justify-center transition-all cursor-pointer shadow-2xs ${
                  isPlayingAudio
                    ? "bg-cyan-500 text-slate-950 border-cyan-400 animate-pulse"
                    : "bg-[#121828] hover:bg-[#18233c] border-[#1b2940] text-slate-200 hover:text-white"
                }`}
                title="Preview voice speech"
              >
                {isPlayingAudio ? (
                  <Pause size={13} className="fill-current" />
                ) : (
                  <Play size={13} className="fill-current ml-0.5" />
                )}
              </button>

              {/* 4. Aspect Ratio Selector (16:9 / 9:16) */}
              <div className="relative ratio-dropdown-container">
                <button
                  type="button"
                  onClick={() => {
                    setIsRatioDropdownOpen(!isRatioDropdownOpen);
                    setActiveInfoPopover(null);
                    setIsModelDropdownOpen(false);
                    setIsVoiceDropdownOpen(false);
                    setIsResDropdownOpen(false);
                  }}
                  className="px-3.5 py-1.5 bg-[#121828] hover:bg-[#18233c] border border-[#1b2940] rounded-full text-xs font-semibold text-slate-200 hover:text-white transition-colors cursor-pointer flex items-center gap-1.5 shadow-2xs"
                >
                  <RectangleHorizontal size={14} className="text-slate-400" />
                  <span>{aspectRatio}</span>
                  <ChevronDown size={13} className="text-slate-400" />
                </button>

                {isRatioDropdownOpen && (
                  <div className="absolute left-0 bottom-full mb-2 w-40 bg-[#0b111e] rounded-2xl shadow-2xl border border-[#1b2940] py-1.5 z-40 animate-in fade-in zoom-in-95 duration-150">
                    <button
                      type="button"
                      onClick={() => {
                        setAspectRatio("16:9");
                        setIsRatioDropdownOpen(false);
                      }}
                      className="w-full px-3 py-2 text-left text-xs font-medium text-slate-300 hover:text-white hover:bg-[#121828] flex items-center justify-between cursor-pointer"
                    >
                      <div className="flex items-center gap-1.5">
                        <RectangleHorizontal size={13} />
                        <span>Landscape 16:9</span>
                      </div>
                      {aspectRatio === "16:9" && <Check size={14} className="text-cyan-400" />}
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setAspectRatio("9:16");
                        setIsRatioDropdownOpen(false);
                      }}
                      className="w-full px-3 py-2 text-left text-xs font-medium text-slate-300 hover:text-white hover:bg-[#121828] flex items-center justify-between cursor-pointer"
                    >
                      <div className="flex items-center gap-1.5">
                        <Square size={13} />
                        <span>Portrait 9:16</span>
                      </div>
                      {aspectRatio === "9:16" && <Check size={14} className="text-cyan-400" />}
                    </button>
                  </div>
                )}
              </div>

              {/* 5. Resolution Selector ("720p") */}
              <div className="relative res-dropdown-container">
                <button
                  type="button"
                  onClick={() => {
                    setIsResDropdownOpen(!isResDropdownOpen);
                    setActiveInfoPopover(null);
                    setIsModelDropdownOpen(false);
                    setIsVoiceDropdownOpen(false);
                    setIsRatioDropdownOpen(false);
                  }}
                  className="px-3.5 py-1.5 bg-[#121828] hover:bg-[#18233c] border border-[#1b2940] rounded-full text-xs font-semibold text-slate-200 hover:text-white transition-colors cursor-pointer flex items-center gap-1.5 shadow-2xs"
                >
                  <span>{resolution}</span>
                  <ChevronDown size={13} className="text-slate-400" />
                </button>

                {isResDropdownOpen && (
                  <div className="absolute left-0 bottom-full mb-2 w-32 bg-[#0b111e] rounded-2xl shadow-2xl border border-[#1b2940] py-1.5 z-40 animate-in fade-in zoom-in-95 duration-150">
                    {["720p", "1080p", "4K"].map((res) => (
                      <button
                        key={res}
                        type="button"
                        onClick={() => {
                          setResolution(res);
                          setIsResDropdownOpen(false);
                        }}
                        className="w-full px-3 py-2 text-left text-xs font-medium text-slate-300 hover:text-white hover:bg-[#121828] flex items-center justify-between cursor-pointer"
                      >
                        <span>{res}</span>
                        {resolution === res && <Check size={14} className="text-cyan-400" />}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Right: Generate Button */}
            <button
              type="button"
              onClick={handleGenerate}
              disabled={isGenerating}
              className="px-7 py-2.5 bg-gradient-to-r from-blue-600 to-cyan-500 hover:from-blue-500 hover:to-cyan-400 disabled:opacity-50 text-white font-bold text-xs sm:text-sm rounded-full shadow-md hover:shadow-cyan-500/20 transition-all cursor-pointer flex items-center justify-center gap-2"
            >
              <Sparkles size={15} />
              <span>{isGenerating ? "Generating..." : "Generate"}</span>
            </button>
          </div>
        </div>

        {/* ================= SECTION 2: RECENT CREATIONS ================= */}
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base sm:text-lg font-extrabold text-white tracking-tight">
              Recent Creations
            </h2>
            <button
              type="button"
              onClick={() => {
                if (onSeeAllProjects) {
                  onSeeAllProjects();
                } else if (onOpenStudio) {
                  onOpenStudio();
                }
              }}
              className="text-xs font-semibold text-slate-400 hover:text-cyan-400 transition-colors cursor-pointer flex items-center gap-1"
            >
              <span>All Projects</span>
              <span>&gt;</span>
            </button>
          </div>

          {/* Large Empty-State Container */}
          <div className="bg-[#0b111e] border-2 border-dashed border-[#1b2940] rounded-3xl p-12 sm:p-16 flex flex-col items-center justify-center text-center">
            {/* Center Illustration / Icon */}
            <div className="w-16 h-16 rounded-2xl bg-[#121828] border border-[#1b2940] shadow-sm flex items-center justify-center text-slate-400 mb-4">
              <Film size={28} className="stroke-[1.5]" />
            </div>

            {/* Main Text */}
            <h3 className="text-sm sm:text-base font-bold text-white">
              No projects here yet
            </h3>

            {/* Subtext */}
            <p className="text-xs text-slate-400 max-w-sm mt-1.5 leading-relaxed">
              Videos you create with Presenter and Cinematic mode will appear here
            </p>
          </div>
        </section>
      </main>
    </div>
  );
}
