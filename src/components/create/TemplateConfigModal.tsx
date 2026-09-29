"use client";

import React, { useState, useRef, useEffect } from "react";
import {
  X,
  Play,
  Volume2,
  Sparkles,
  ArrowLeft,
  ArrowRight,
  ArrowLeftRight,
  ChevronDown,
  Clock,
  Video as VideoIcon,
  Subtitles,
  Plus,
  Shirt,
  Check,
} from "lucide-react";
import {
  AVATAR_OPTIONS,
  VOICE_OPTIONS,
  BRAND_SYSTEM_OPTIONS,
  VideoAgentTemplate,
} from "./videoAgentData";
import AttachAssetModal from "./AttachAssetModal";
import ChooseBrandSystemModal, { BrandSystemData } from "./ChooseBrandSystemModal";
import ChooseAvatarModal from "./ChooseAvatarModal";
import VoicesLibrary, { VoiceItem } from "../voices/VoicesLibrary";
import { AvatarOptionData, AvatarLook } from "./videoAgentData";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";

function getDefaultScriptForTemplate(template: VideoAgentTemplate): string {
  if (template.defaultScript) return template.defaultScript;
  const titleLower = template.title.toLowerCase();
  if (titleLower.includes("tip") || titleLower.includes("how-to")) {
    return `Share 3 essential tips on how to master ${template.title.toLowerCase()} for your target audience.`;
  }
  if (titleLower.includes("expert") || titleLower.includes("explainer")) {
    return `Explain the core concepts and real-world mechanisms of ${template.title.toLowerCase()} in a clear, authoritative presentation.`;
  }
  if (
    titleLower.includes("education") ||
    titleLower.includes("lesson") ||
    titleLower.includes("course") ||
    titleLower.includes("micro-lesson")
  ) {
    return `Teach a structured lesson covering fundamental principles, practical examples, and actionable takeaways for your learners.`;
  }
  if (
    titleLower.includes("news") ||
    titleLower.includes("brief") ||
    titleLower.includes("update")
  ) {
    return `Deliver a concise, fast-paced news update on the latest trends and headlines in the industry.`;
  }
  if (
    titleLower.includes("sales") ||
    titleLower.includes("outreach") ||
    titleLower.includes("pitch")
  ) {
    return `Deliver a high-converting, personalized 1-to-1 video pitch highlighting key customer pain points and immediate solutions.`;
  }
  if (
    titleLower.includes("tour") ||
    titleLower.includes("real estate") ||
    titleLower.includes("listing") ||
    titleLower.includes("market")
  ) {
    return `Highlight the most appealing property features, neighborhood advantages, and current market insights.`;
  }
  if (
    titleLower.includes("training") ||
    titleLower.includes("onboarding") ||
    titleLower.includes("policy") ||
    titleLower.includes("refresher")
  ) {
    return `Walk team members through key operational guidelines, best practices, and standard operating procedures.`;
  }
  return `Create a high-impact video explaining the key benefits and step-by-step strategy for ${template.title.toLowerCase()}.`;
}

function generateScriptForTemplate(
  template: VideoAgentTemplate,
  promptTopic: string
): string {
  const topic = promptTopic.trim();
  const titleLower = template.title.toLowerCase();

  if (titleLower.includes("tip") || titleLower.includes("how-to")) {
    return `Here are 3 essential steps to master ${topic}:\n\n1. Define your primary outcome clearly from the start.\n2. Execute step-by-step while maintaining consistent visual polish.\n3. Review viewer retention and optimize your closing call-to-action.\n\nTry this in your next project to see immediate engagement!`;
  }
  if (titleLower.includes("expert") || titleLower.includes("explainer")) {
    return `Understanding ${topic}: An Expert Breakdown.\n\n1. Core Concept: Why this fundamental mechanism drives real-world outcomes.\n2. Mechanism: How the underlying framework functions in practice.\n3. Key Takeaway: The single most impactful insight you should implement today.\n\nFollow for more deep dives on this topic!`;
  }
  if (
    titleLower.includes("education") ||
    titleLower.includes("lesson") ||
    titleLower.includes("course") ||
    titleLower.includes("micro-lesson")
  ) {
    return `Welcome to today's module on ${topic}!\n\nLesson Outline:\n• Part 1: Fundamental definitions and prerequisites.\n• Part 2: Step-by-step walkthrough with clear visual examples.\n• Part 3: Knowledge check and interactive summary.\n\nSave this video for your study notes and let's get started!`;
  }
  if (
    titleLower.includes("news") ||
    titleLower.includes("brief") ||
    titleLower.includes("update")
  ) {
    return `Breaking Update: What you need to know about ${topic}.\n\n• Top Headline: Significant new milestone announced today.\n• Industry Impact: How this shift affects creators and business leaders immediately.\n• What's Next: Upcoming regulatory timelines and scheduled rollouts.\n\nStay tuned for continuous coverage on this story!`;
  }
  if (
    titleLower.includes("sales") ||
    titleLower.includes("outreach") ||
    titleLower.includes("pitch")
  ) {
    return `Hi there! I noticed your recent initiatives around ${topic} and wanted to share a quick personalized idea.\n\n1. The Challenge: Common bottlenecks teams experience when scaling.\n2. The Solution: How our tailored framework delivers 3x faster turnaround.\n3. Next Step: Let's connect for 10 minutes this Thursday to review customized benchmarks.\n\nLooking forward to chatting!`;
  }
  if (
    titleLower.includes("tour") ||
    titleLower.includes("real estate") ||
    titleLower.includes("listing") ||
    titleLower.includes("market")
  ) {
    return `Welcome to this exclusive look at ${topic}!\n\nKey Highlights:\n• Location & Curb Appeal: Prime positioning with exceptional accessibility.\n• Interior Features: Modern architectural design with open layout and natural lighting.\n• Market Opportunity: Outstanding valuation and strong long-term appreciation.\n\nContact our team today to schedule a private walkthrough!`;
  }
  if (
    titleLower.includes("training") ||
    titleLower.includes("onboarding") ||
    titleLower.includes("policy") ||
    titleLower.includes("refresher")
  ) {
    return `Internal Training Session: ${topic}.\n\nObjective: Ensure team alignment on core standards and operational workflows.\n\n1. Overview of company standards and key responsibilities.\n2. Standard Operating Procedure breakdown.\n3. Verification checklist and support resources.\n\nPlease confirm module completion with your department lead.`;
  }
  return `Here is a complete breakdown on ${topic}:\n\n1. Overview: The importance and potential impact.\n2. Strategy: Step-by-step execution roadmap.\n3. Next Steps: Action items to get started immediately.\n\nShare this video with your team to put these ideas into practice!`;
}

interface TemplateConfigModalProps {
  isOpen: boolean;
  template: VideoAgentTemplate | null;
  onClose: () => void;
  onContinue: (config: {
    template: VideoAgentTemplate;
    avatar: any;
    voice: any;
    look?: any;
    script: string;
    brand: any;
    speed: string;
    quality: string;
    seedance: boolean;
    captions: boolean;
    attachments: string[];
  }) => void;
}

export default function TemplateConfigModal({
  isOpen,
  template,
  onClose,
  onContinue,
}: TemplateConfigModalProps) {
  const { currentWorkspace } = useAuth();
  const [selectedAvatar, setSelectedAvatar] = useState(AVATAR_OPTIONS[0]);
  const [selectedLook, setSelectedLook] = useState<AvatarLook | undefined>(
    AVATAR_OPTIONS[0].lookImages?.[0]
  );
  const [selectedVoice, setSelectedVoice] = useState(VOICE_OPTIONS[0]);
  const [isPlayingVoice, setIsPlayingVoice] = useState(false);
  const [selectedBrand, setSelectedBrand] = useState<any>(null); // null represents '+ Brand System'
  const [scriptText, setScriptText] = useState("");

  // Preload real workspace/public avatars & voices from backend
  useEffect(() => {
    if (!isOpen) return;
    let active = true;

    async function loadRealOptions() {
      try {
        const [avatarList, voiceList] = await Promise.allSettled([
          api.creative.listAvatars({}, currentWorkspace?.id),
          api.creative.listVoices({}, currentWorkspace?.id),
        ]);

        if (!active) return;

        if (
          avatarList.status === "fulfilled" &&
          Array.isArray(avatarList.value) &&
          avatarList.value.length > 0
        ) {
          const mapped: AvatarOptionData[] = avatarList.value.map((a: any) => ({
            id: a.id,
            name: a.name,
            label: a.name || "Avatar",
            tag: a.avatar_type || "Studio",
            type: a.avatar_type === "custom" ? "Custom Avatar" : "Photo Avatar",
            image:
              a.preview_url ||
              a.provider_metadata?.preview_url ||
              a.provider_metadata?.image_url ||
              "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?q=80&w=600&auto=format&fit=crop",
            filterCategory: a.provider_metadata?.category || "Professional",
            gender: a.provider_metadata?.gender,
            looks: a.looks?.length || 1,
            lookImages: (a.looks || []).map((l: any) => ({
              id: l.id,
              name: l.name,
              image: l.preview_url || l.configuration?.preview_url || a.preview_url,
            })),
          }));

          const defaultAvatar =
            mapped.find((a) => a.name.toLowerCase().includes("annie")) ||
            mapped[0];
          if (defaultAvatar) {
            setSelectedAvatar(defaultAvatar);
            setSelectedLook(defaultAvatar.lookImages?.[0]);
          }
        }

        if (
          voiceList.status === "fulfilled" &&
          Array.isArray(voiceList.value) &&
          voiceList.value.length > 0
        ) {
          const defaultVoice =
            voiceList.value.find(
              (v: any) =>
                v.name?.toLowerCase().includes("annie") ||
                v.id === "en_US-lessac-medium"
            ) || voiceList.value[0];

          if (defaultVoice) {
            setSelectedVoice({
              id: defaultVoice.id,
              name: defaultVoice.name,
              label: "Voice",
              accent: defaultVoice.language || "English (US)",
              style: defaultVoice.description || "Conversational & Warm",
            });
          }
        }
      } catch (err) {
        console.warn("Could not preload real options in TemplateConfigModal:", err);
      }
    }

    loadRealOptions();

    return () => {
      active = false;
    };
  }, [isOpen, currentWorkspace?.id]);

  // Script Writer Popover State
  const [isScriptWriterOpen, setIsScriptWriterOpen] = useState(false);
  const [scriptPrompt, setScriptPrompt] = useState("");

  // Options State
  const [speedOption, setSpeedOption] = useState("Auto");
  const [qualityOption, setQualityOption] = useState("Auto");
  const [seedanceEnabled, setSeedanceEnabled] = useState(false);
  const [captionsEnabled, setCaptionsEnabled] = useState(true);
  const [attachments, setAttachments] = useState<string[]>([]);

  // Popover & Child Modal States
  const [openDropdown, setOpenDropdown] = useState<"speed" | "quality" | null>(null);
  const [isAttachModalOpen, setIsAttachModalOpen] = useState(false);
  const [isBrandModalOpen, setIsBrandModalOpen] = useState(false);
  const [isAvatarModalOpen, setIsAvatarModalOpen] = useState(false);
  const [isChangeLookModalOpen, setIsChangeLookModalOpen] = useState(false);
  const [isVoiceLibraryOpen, setIsVoiceLibraryOpen] = useState(false);

  const modalRef = useRef<HTMLDivElement>(null);
  const changeLookModalRef = useRef<HTMLDivElement>(null);
  const scriptWriterRef = useRef<HTMLDivElement>(null);
  const speedDropdownRef = useRef<HTMLDivElement>(null);
  const qualityDropdownRef = useRef<HTMLDivElement>(null);

  // Sync initial template script & reset fields on open
  useEffect(() => {
    if (isOpen && template) {
      setScriptText(getDefaultScriptForTemplate(template));
      setIsScriptWriterOpen(false);
      setScriptPrompt("");
      setOpenDropdown(null);
    }
  }, [isOpen, template]);

  // Outside click listeners
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (
        scriptWriterRef.current &&
        !scriptWriterRef.current.contains(e.target as Node)
      ) {
        setIsScriptWriterOpen(false);
      }
      if (
        speedDropdownRef.current &&
        !speedDropdownRef.current.contains(e.target as Node)
      ) {
        setOpenDropdown((prev) => (prev === "speed" ? null : prev));
      }
      if (
        qualityDropdownRef.current &&
        !qualityDropdownRef.current.contains(e.target as Node)
      ) {
        setOpenDropdown((prev) => (prev === "quality" ? null : prev));
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Close on Escape key
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        if (isVoiceLibraryOpen) {
          setIsVoiceLibraryOpen(false);
        } else if (isChangeLookModalOpen) {
          setIsChangeLookModalOpen(false);
        } else if (isScriptWriterOpen) {
          setIsScriptWriterOpen(false);
        } else if (openDropdown) {
          setOpenDropdown(null);
        } else if (
          !isBrandModalOpen &&
          !isAttachModalOpen &&
          !isAvatarModalOpen
        ) {
          onClose();
        }
      }
    }
    if (isOpen) {
      window.addEventListener("keydown", handleKeyDown);
    }
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [
    isOpen,
    onClose,
    isVoiceLibraryOpen,
    isChangeLookModalOpen,
    isScriptWriterOpen,
    openDropdown,
    isBrandModalOpen,
    isAttachModalOpen,
    isAvatarModalOpen,
  ]);

  if (!isOpen || !template) return null;

  const handleGenerateScript = () => {
    if (!scriptPrompt.trim()) return;
    const generated = generateScriptForTemplate(template, scriptPrompt);
    setScriptText(generated);
    setScriptPrompt("");
    setIsScriptWriterOpen(false);
  };

  const handleSwapAvatar = () => {
    setIsAvatarModalOpen(true);
  };

  const handleContinue = () => {
    onContinue({
      template,
      avatar: selectedAvatar,
      voice: selectedVoice,
      look: selectedLook,
      script: scriptText,
      brand: selectedBrand || BRAND_SYSTEM_OPTIONS[0],
      speed: speedOption,
      quality: qualityOption,
      seedance: seedanceEnabled,
      captions: captionsEnabled,
      attachments,
    });
    onClose();
  };

  const handleBrandSelected = (brand: BrandSystemData) => {
    setSelectedBrand({
      id: brand.id,
      name: brand.name,
      fullName: brand.fullName || brand.name,
      color: brand.primaryColor,
      label: "Brand System",
    });
    setIsBrandModalOpen(false);
  };

  const handleAvatarSelected = (avatar: AvatarOptionData, look?: AvatarLook) => {
    setSelectedAvatar({
      id: avatar.id,
      name: avatar.name,
      label: avatar.label || "Avatar",
      tag: avatar.tag || "Studio",
      image: look?.image || avatar.image,
      type: avatar.type,
      looks: avatar.looks,
      lookImages: avatar.lookImages,
    });
    setSelectedLook(look || avatar.lookImages?.[0]);
    setIsAvatarModalOpen(false);
  };

  return (
    <div
      onClick={(e) => {
        if (modalRef.current && !modalRef.current.contains(e.target as Node)) {
          onClose();
        }
      }}
      className="fixed inset-0 z-50 bg-black/75 backdrop-blur-md flex items-center justify-center p-4 overflow-y-auto animate-in fade-in duration-200 select-none"
    >
      <div
        ref={modalRef}
        className="w-full max-w-4xl bg-[#0A0F1A] rounded-3xl shadow-2xl border border-[#1B2940] text-slate-100 my-6 max-h-[92vh] flex flex-col relative overflow-hidden animate-in zoom-in-95 duration-150"
      >
        {/* 1. Template Hero Header */}
        <div className="relative w-full h-48 sm:h-56 flex-shrink-0 overflow-hidden bg-slate-950">
          {/* Cover Image */}
          <img
            src={
              template.banner ||
              template.image ||
              "https://images.unsplash.com/photo-1522202176988-66273c2fd55f?q=80&w=1200&auto=format&fit=crop"
            }
            alt={template.title}
            className="w-full h-full object-cover object-center"
          />

          {/* Soft Dark Gradient Overlay for Text Contrast */}
          <div className="absolute inset-0 bg-gradient-to-r from-[#0A0F1A]/95 via-[#0A0F1A]/80 to-transparent sm:w-3/4 pointer-events-none"></div>
          <div className="absolute inset-0 bg-gradient-to-t from-[#0A0F1A]/60 via-transparent to-black/40 pointer-events-none"></div>

          {/* Hero Text (Top Left) */}
          <div className="absolute left-6 sm:left-8 top-6 sm:top-8 max-w-md z-10">
            <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight leading-tight">
              {template.title}
            </h1>
            <p className="text-xs sm:text-sm font-medium text-slate-300 mt-1.5 leading-snug">
              {template.description ||
                "Share a clear, engaging video for your audience."}
            </p>
          </div>

          {/* Close Button (Top Right of Hero: Circular Dark Translucent with White X) */}
          <button
            type="button"
            onClick={onClose}
            className="absolute top-4 right-4 z-20 w-10 h-10 rounded-full bg-black/50 hover:bg-black/80 backdrop-blur-md border border-white/10 flex items-center justify-center text-white transition-colors cursor-pointer shadow-md"
            title="Close"
          >
            <X size={18} />
          </button>
        </div>

        {/* 2. Scrollable Body Content */}
        <div className="flex-1 overflow-y-auto p-6 sm:p-8 space-y-6 scrollbar-thin scrollbar-thumb-slate-800">
          {/* SCRIPT / PROMPT AREA */}
          <div>
            <div className="text-xs font-bold text-slate-300 mb-2 tracking-wide">
              Video Details
            </div>
            <div className="border border-[#1B2940] rounded-2xl bg-[#0B111E] p-4 shadow-sm relative focus-within:border-cyan-500 focus-within:ring-2 focus-within:ring-cyan-500/20 transition-all">
              <textarea
                value={scriptText}
                onChange={(e) => setScriptText(e.target.value)}
                placeholder={
                  template.scriptPlaceholder ||
                  "Type your script or a prompt for me to generate one for you"
                }
                rows={4}
                className="w-full bg-transparent text-xs sm:text-sm text-slate-100 placeholder:text-slate-500 font-normal leading-relaxed outline-none resize-none"
              />

              {/* Bottom Row inside Script Container */}
              <div className="pt-3 flex items-center justify-between border-t border-[#1B2940]/80 mt-1">
                {/* Script Writer Button & Floating Popover */}
                <div className="relative" ref={scriptWriterRef}>
                  <button
                    type="button"
                    onClick={() => setIsScriptWriterOpen(!isScriptWriterOpen)}
                    className={`px-3.5 py-1.5 rounded-full text-xs font-bold flex items-center gap-1.5 transition-all cursor-pointer shadow-sm border ${
                      isScriptWriterOpen
                        ? "bg-[#101827] text-cyan-300 border-cyan-500/60 shadow-xs"
                        : "bg-[#0B1220] hover:bg-[#101827] text-slate-200 border-[#1B2940] hover:border-cyan-500/40"
                    }`}
                  >
                    <Sparkles
                      size={13}
                      className={
                        isScriptWriterOpen ? "text-cyan-400" : "text-cyan-400"
                      }
                    />
                    <span>✨ Script Writer</span>
                  </button>

                  {/* Script Writer Floating Popover (Single Instance, Positioned Directly Below Button) */}
                  {isScriptWriterOpen && (
                    <div className="absolute left-0 top-full mt-2 w-[340px] sm:w-[400px] bg-[#0B111E] border border-[#1B2940] rounded-2xl shadow-2xl p-4 z-40 animate-in fade-in zoom-in-95 duration-150">
                      <div className="text-xs font-bold text-white mb-2 flex items-center gap-1.5">
                        <Sparkles size={13} className="text-cyan-400" />
                        <span>Script Writer</span>
                      </div>
                      <textarea
                        value={scriptPrompt}
                        onChange={(e) => setScriptPrompt(e.target.value)}
                        placeholder="Write a script for..."
                        rows={3}
                        autoFocus
                        onKeyDown={(e) => {
                          if (e.key === "Enter" && !e.shiftKey && scriptPrompt.trim()) {
                            e.preventDefault();
                            handleGenerateScript();
                          }
                        }}
                        className="w-full bg-[#07090e] border border-[#1B2940] rounded-xl p-3 text-xs text-white placeholder:text-slate-500 outline-none focus:border-cyan-500 focus:bg-[#07090e] focus:ring-2 focus:ring-cyan-500/20 transition-all resize-none"
                      />
                      <div className="mt-3 flex items-center justify-end">
                        <button
                          type="button"
                          disabled={!scriptPrompt.trim()}
                          onClick={handleGenerateScript}
                          className={`px-4 py-1.5 rounded-full text-xs font-semibold transition-all duration-150 flex items-center gap-1.5 cursor-pointer ${
                            scriptPrompt.trim()
                              ? "bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-bold shadow-md active:scale-95"
                              : "bg-[#101827] text-slate-500 cursor-not-allowed border border-[#1B2940]"
                          }`}
                        >
                          <span>Generate</span>
                          <Sparkles size={12} />
                        </button>
                      </div>
                    </div>
                  )}
                </div>

                <span className="text-[11px] text-slate-400 font-mono">
                  {scriptText.length} chars
                </span>
              </div>
            </div>
          </div>

          {/* AVATAR SECTION */}
          <div>
            <div className="text-xs font-bold text-slate-300 mb-2 tracking-wide">
              Avatar
            </div>
            <div className="bg-[#0B111E] border border-[#1B2940] rounded-2xl p-3.5 sm:p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-sm">
              {/* Left & Center: Portrait + Name + Voice pill + Change look */}
              <div
                onClick={() => setIsAvatarModalOpen(true)}
                className="flex items-center gap-3.5 cursor-pointer group flex-1"
              >
                <img
                  src={selectedAvatar.image}
                  alt={selectedAvatar.name}
                  className="w-12 h-12 rounded-full object-cover ring-2 ring-cyan-500/40 shadow-sm flex-shrink-0 group-hover:ring-cyan-400 transition-all"
                />
                <div>
                  <div className="text-sm font-bold text-white group-hover:text-cyan-300 transition-colors">
                    {selectedAvatar.name}
                  </div>
                  <div className="flex flex-wrap items-center gap-2 mt-1">
                    {/* Voice Pill (Click text opens Voice Management page; click play toggles preview) */}
                    <div
                      onClick={(e) => {
                        e.stopPropagation();
                        setIsVoiceLibraryOpen(true);
                      }}
                      className="bg-[#101827] hover:bg-[#152033] border border-[#1B2940] hover:border-cyan-500/40 px-2.5 py-1 rounded-full text-[11px] font-semibold text-slate-200 hover:text-white flex items-center gap-1.5 shadow-sm transition-colors cursor-pointer"
                      title="Select Voice from Voices Library"
                    >
                      <Volume2 size={12} className="text-blue-400" />
                      <span>{selectedVoice.name}</span>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          setIsPlayingVoice((prev) => !prev);
                        }}
                        className="p-0.5 hover:bg-slate-800 rounded-full transition-colors cursor-pointer ml-0.5"
                        title={isPlayingVoice ? "Pause Preview" : "Play Voice Preview"}
                      >
                        {isPlayingVoice ? (
                          <span className="w-2 h-2 rounded-xs bg-blue-400 inline-block"></span>
                        ) : (
                          <Play size={9} className="text-slate-400 fill-slate-400" />
                        )}
                      </button>
                    </div>

                    {/* Change Look Pill */}
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        setIsChangeLookModalOpen(true);
                      }}
                      className="bg-[#101827] hover:bg-[#152033] border border-[#1B2940] hover:border-cyan-500/40 px-2.5 py-1 rounded-full text-[11px] font-semibold text-slate-200 hover:text-white flex items-center gap-1.5 shadow-sm transition-colors cursor-pointer"
                    >
                      <Shirt size={12} className="text-slate-400" />
                      <span>Change Look</span>
                    </button>
                  </div>
                </div>
              </div>

              {/* Right: Swap avatar button */}
              <div className="self-end sm:self-center">
                <button
                  type="button"
                  onClick={handleSwapAvatar}
                  className="w-8 h-8 rounded-full bg-[#101827] hover:bg-[#152033] border border-[#1B2940] hover:border-cyan-500/40 text-slate-300 hover:text-white flex items-center justify-center transition-colors cursor-pointer shadow-sm active:scale-95"
                  title="Switch Avatar"
                >
                  <ArrowLeftRight size={14} />
                </button>
              </div>
            </div>
          </div>

          {/* LOWER CONFIGURATION CONTROLS */}
          <div>
            <div className="text-xs font-bold text-slate-300 mb-2 tracking-wide">
              Options
            </div>

            {/* Row 1: Horizontal Option Pills */}
            <div className="flex flex-wrap items-center gap-2 mb-2.5">
              {/* Option 1: Auto (Speed/Duration) */}
              <div className="relative" ref={speedDropdownRef}>
                <button
                  type="button"
                  onClick={() =>
                    setOpenDropdown((prev) => (prev === "speed" ? null : "speed"))
                  }
                  className="bg-[#0B111E] hover:bg-[#101827] border border-[#1B2940] hover:border-cyan-500/40 px-3.5 py-1.5 rounded-full text-xs font-semibold text-slate-200 flex items-center gap-1.5 shadow-sm transition-colors cursor-pointer"
                >
                  <Clock size={13} className="text-slate-400" />
                  <span>{speedOption}</span>
                  <ChevronDown size={12} className="text-slate-400" />
                </button>

                {openDropdown === "speed" && (
                  <div className="absolute left-0 bottom-full mb-2 w-36 bg-[#0B111E] border border-[#1B2940] rounded-xl shadow-2xl p-1.5 z-50 animate-in fade-in duration-150">
                    {["Auto", "Fast Draft", "High Quality"].map((opt) => (
                      <button
                        key={opt}
                        type="button"
                        onClick={() => {
                          setSpeedOption(opt);
                          setOpenDropdown(null);
                        }}
                        className={`w-full text-left px-2.5 py-1.5 rounded-lg text-xs transition-colors ${
                          speedOption === opt
                            ? "bg-cyan-950/60 border border-cyan-500/40 font-bold text-cyan-300"
                            : "text-slate-300 hover:bg-[#101827]"
                        }`}
                      >
                        {opt}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Option 2: Auto (Resolution/Quality) */}
              <div className="relative" ref={qualityDropdownRef}>
                <button
                  type="button"
                  onClick={() =>
                    setOpenDropdown((prev) => (prev === "quality" ? null : "quality"))
                  }
                  className="bg-[#0B111E] hover:bg-[#101827] border border-[#1B2940] hover:border-cyan-500/40 px-3.5 py-1.5 rounded-full text-xs font-semibold text-slate-200 flex items-center gap-1.5 shadow-sm transition-colors cursor-pointer"
                >
                  <VideoIcon size={13} className="text-slate-400" />
                  <span>{qualityOption}</span>
                  <ChevronDown size={12} className="text-slate-400" />
                </button>

                {openDropdown === "quality" && (
                  <div className="absolute left-0 bottom-full mb-2 w-36 bg-[#0B111E] border border-[#1B2940] rounded-xl shadow-2xl p-1.5 z-50 animate-in fade-in duration-150">
                    {["Auto", "1080p HD", "4K Ultra"].map((opt) => (
                      <button
                        key={opt}
                        type="button"
                        onClick={() => {
                          setQualityOption(opt);
                          setOpenDropdown(null);
                        }}
                        className={`w-full text-left px-2.5 py-1.5 rounded-lg text-xs transition-colors ${
                          qualityOption === opt
                            ? "bg-cyan-950/60 border border-cyan-500/40 font-bold text-cyan-300"
                            : "text-slate-300 hover:bg-[#101827]"
                        }`}
                      >
                        {opt}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Option 3: Seedance Toggle */}
              <button
                type="button"
                onClick={() => setSeedanceEnabled(!seedanceEnabled)}
                className={`border px-3.5 py-1.5 rounded-full text-xs font-semibold transition-colors cursor-pointer shadow-sm ${
                  seedanceEnabled
                    ? "bg-cyan-950/60 border-cyan-500/80 text-cyan-300 font-bold shadow-[0_0_10px_rgba(6,182,212,0.2)]"
                    : "bg-[#0B111E] hover:bg-[#101827] border-[#1B2940] text-slate-300"
                }`}
              >
                Seedance {seedanceEnabled ? "ON" : "OFF"}
              </button>

              {/* Option 4: Captions Toggle */}
              <button
                type="button"
                onClick={() => setCaptionsEnabled(!captionsEnabled)}
                className={`border px-3.5 py-1.5 rounded-full text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer shadow-sm ${
                  captionsEnabled
                    ? "bg-cyan-500 border-cyan-500 text-slate-950 font-bold shadow-[0_0_12px_rgba(6,182,212,0.3)]"
                    : "bg-[#0B111E] hover:bg-[#101827] border-[#1B2940] text-slate-300"
                }`}
              >
                <Subtitles size={13} />
                <span>Captions {captionsEnabled ? "ON" : "OFF"}</span>
              </button>

              {/* Option 5: + Brand System (Opens ChooseBrandSystemModal) */}
              <button
                type="button"
                onClick={() => setIsBrandModalOpen(true)}
                className={`border px-3.5 py-1.5 rounded-full text-xs font-semibold flex items-center gap-1.5 shadow-sm transition-colors cursor-pointer ${
                  selectedBrand
                    ? "bg-[#101827] text-white border-cyan-500/40 font-bold"
                    : "bg-[#0B111E] hover:bg-[#101827] border-[#1B2940] text-slate-300"
                }`}
              >
                {selectedBrand ? (
                  <div
                    className="w-2.5 h-2.5 rounded-full border border-white"
                    style={{
                      backgroundColor:
                        selectedBrand.color || selectedBrand.primaryColor,
                    }}
                  ></div>
                ) : (
                  <Plus size={12} />
                )}
                <span>
                  {selectedBrand ? selectedBrand.name : "Brand System"}
                </span>
                <ChevronDown
                  size={11}
                  className={selectedBrand ? "text-slate-300" : "text-slate-400"}
                />
              </button>
            </div>

            {/* Row 2: + Attachments Pill */}
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setIsAttachModalOpen(true)}
                className={`border px-3.5 py-1.5 rounded-full text-xs font-semibold flex items-center gap-1.5 shadow-sm transition-colors cursor-pointer ${
                  attachments.length > 0
                    ? "bg-cyan-950/60 border-cyan-500/80 text-cyan-300 font-bold shadow-[0_0_10px_rgba(6,182,212,0.2)]"
                    : "bg-[#0B111E] hover:bg-[#101827] border-[#1B2940] text-slate-300"
                }`}
              >
                <Plus size={12} />
                <span>
                  {attachments.length > 0
                    ? `${attachments.length} Attachment${
                        attachments.length > 1 ? "s" : ""
                      }`
                    : "Attachments"}
                </span>
              </button>
            </div>
          </div>
        </div>

        {/* 3. Fixed Footer: Left Back & Right Continue */}
        <div className="px-6 sm:px-8 py-4 border-t border-[#1B2940] bg-[#0A0F1A] flex items-center justify-between flex-shrink-0">
          {/* Left: Back */}
          <button
            type="button"
            onClick={onClose}
            className="text-slate-400 hover:text-white font-semibold text-xs flex items-center gap-1.5 px-3 py-2 rounded-xl hover:bg-[#101827] transition-colors cursor-pointer"
          >
            <ArrowLeft size={14} />
            <span>Back</span>
          </button>

          {/* Right: Generate */}
          <button
            type="button"
            onClick={handleContinue}
            className="bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-bold text-xs px-6 py-2.5 rounded-full shadow-lg shadow-cyan-500/25 hover:shadow-cyan-500/40 transition-all duration-150 cursor-pointer flex items-center gap-1.5 active:scale-95"
          >
            <Sparkles size={14} />
            <span>Generate</span>
          </button>
        </div>
      </div>

      {/* ============================================================ */}
      {/* 4. DEDICATED CHANGE LOOK MODAL / GALLERY */}
      {/* ============================================================ */}
      {isChangeLookModalOpen && (
        <div
          onClick={(e) => {
            if (
              changeLookModalRef.current &&
              !changeLookModalRef.current.contains(e.target as Node)
            ) {
              setIsChangeLookModalOpen(false);
            }
          }}
          className="fixed inset-0 z-50 bg-black/75 backdrop-blur-md flex items-center justify-center p-4 overflow-y-auto animate-in fade-in duration-200 select-none"
        >
          <div
            ref={changeLookModalRef}
            className="w-full max-w-4xl bg-[#0A0F1A] rounded-3xl shadow-2xl border border-[#1B2940] text-white my-6 max-h-[90vh] flex flex-col relative overflow-hidden animate-in zoom-in-95 duration-150"
          >
            {/* Header: Back arrow + Breadcrumbs ("Public Avatars > Annie") + Close X */}
            <div className="px-6 py-5 border-b border-[#1B2940] flex items-center justify-between flex-shrink-0 bg-[#0A0F1A]">
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={() => setIsChangeLookModalOpen(false)}
                  className="w-8 h-8 rounded-full bg-[#101827] hover:bg-[#152033] border border-[#1B2940] text-slate-300 hover:text-white flex items-center justify-center transition-colors cursor-pointer"
                  title="Back"
                >
                  <ArrowLeft size={16} />
                </button>
                <div className="flex items-center gap-2 text-sm sm:text-base font-bold text-white">
                  <span className="text-slate-400 font-semibold text-xs sm:text-sm">
                    Public Avatars
                  </span>
                  <span className="text-slate-500 font-normal">&gt;</span>
                  <span>{selectedAvatar.name}</span>
                </div>
              </div>

              <button
                type="button"
                onClick={() => setIsChangeLookModalOpen(false)}
                className="w-8 h-8 rounded-full hover:bg-[#101827] text-slate-400 hover:text-white flex items-center justify-center transition-colors cursor-pointer"
                title="Close"
              >
                <X size={18} />
              </button>
            </div>

            {/* Scrollable 3-Column Looks Grid */}
            <div className="flex-1 overflow-y-auto p-6 sm:p-8 scrollbar-thin scrollbar-thumb-slate-800">
              {(() => {
                const currentLooks =
                  selectedAvatar.lookImages && selectedAvatar.lookImages.length > 0
                    ? selectedAvatar.lookImages
                    : AVATAR_OPTIONS.find((a) => a.id === selectedAvatar.id)?.lookImages || [
                        {
                          id: `${selectedAvatar.id}-default`,
                          name: "Default Look",
                          image: selectedAvatar.image,
                        },
                      ];

                return (
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 sm:gap-5">
                    {currentLooks.map((look) => {
                      const isSelected =
                        selectedLook?.id === look.id ||
                        selectedAvatar.image === look.image;

                      return (
                        <div
                          key={look.id}
                          onClick={() => {
                            setSelectedLook(look);
                            setSelectedAvatar((prev) => ({
                              ...prev,
                              image: look.image,
                            }));
                            setIsChangeLookModalOpen(false);
                          }}
                          className={`group relative h-64 sm:h-72 rounded-2xl overflow-hidden border cursor-pointer transition-all duration-200 flex flex-col justify-end bg-[#0B111E] ${
                            isSelected
                              ? "border-cyan-500 ring-2 ring-cyan-500/40 shadow-lg shadow-cyan-500/20 scale-[1.01]"
                              : "border-[#1B2940] hover:border-cyan-500/50 hover:shadow-md"
                          }`}
                        >
                          {/* Portrait Thumbnail */}
                          <img
                            src={look.image}
                            alt={look.name}
                            className="absolute inset-0 w-full h-full object-cover object-top group-hover:scale-103 transition-transform duration-300"
                          />

                          {/* Selected Checkmark Badge */}
                          {isSelected && (
                            <div className="absolute top-3 right-3 w-6 h-6 rounded-full bg-cyan-500 text-slate-950 font-bold flex items-center justify-center shadow-md z-10">
                              <Check size={13} strokeWidth={3} />
                            </div>
                          )}

                          {/* Bottom Gradient & Look Label */}
                          <div className="relative z-10 p-3 bg-gradient-to-t from-black/90 via-black/50 to-transparent">
                            <div className="text-white text-xs sm:text-sm font-bold truncate">
                              {look.name}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                );
              })()}
            </div>
          </div>
        </div>
      )}

      {/* ============================================================ */}
      {/* 5. VOICE MANAGEMENT LIBRARY MODAL */}
      {/* ============================================================ */}
      {isVoiceLibraryOpen && (
        <div className="fixed inset-0 z-50 bg-[#07090e] flex flex-col animate-in fade-in duration-200">
          <VoicesLibrary
            onBack={() => setIsVoiceLibraryOpen(false)}
            onSelectVoice={(voice: VoiceItem) => {
              setSelectedVoice({
                id: voice.id,
                name: voice.name,
                label: "Voice",
                accent: voice.language,
                style: voice.description,
              });
              setIsVoiceLibraryOpen(false);
            }}
            selectedVoiceId={selectedVoice.id}
            selectedVoiceName={selectedVoice.name}
          />
        </div>
      )}

      {/* Attach Asset Modal */}
      <AttachAssetModal
        isOpen={isAttachModalOpen}
        onClose={() => setIsAttachModalOpen(false)}
        onAttachFile={(fileName) => {
          setAttachments((prev) => [...prev, fileName]);
        }}
      />

      {/* Choose a Brand System Modal */}
      <ChooseBrandSystemModal
        isOpen={isBrandModalOpen}
        onClose={() => setIsBrandModalOpen(false)}
        onSelectBrandSystem={handleBrandSelected}
        selectedBrandId={selectedBrand?.id}
      />

      {/* Choose Avatar Modal */}
      <ChooseAvatarModal
        isOpen={isAvatarModalOpen}
        onClose={() => setIsAvatarModalOpen(false)}
        onSelectAvatar={handleAvatarSelected}
        selectedAvatarId={selectedAvatar.id}
        selectedLookId={selectedLook?.id || selectedAvatar.lookImages?.[0]?.id}
      />
    </div>
  );
}
