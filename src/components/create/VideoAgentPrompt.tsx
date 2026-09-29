"use client";

import React, { useState, useRef, useEffect } from "react";
import {
  Plus,
  SlidersHorizontal,
  ChevronDown,
  Sparkles,
  Play,
  Volume2,
  Paperclip,
  Globe,
  FileText,
  Wand2,
  Check,
  Send,
  CalendarCheck,
  FolderClosed,
  BookOpen,
} from "lucide-react";
import {
  AVATAR_OPTIONS,
  VOICE_OPTIONS,
  BRAND_SYSTEM_OPTIONS,
} from "./videoAgentData";
import AttachAssetModal from "./AttachAssetModal";
import KnowledgeHubModal from "./KnowledgeHubModal";
import ChooseBrandSystemModal, { BrandSystemData } from "./ChooseBrandSystemModal";
import ChooseAvatarModal from "./ChooseAvatarModal";
import { AvatarOptionData, AvatarLook } from "./videoAgentData";

interface VideoAgentPromptProps {
  promptValue: string;
  onChangePrompt: (value: string) => void;
  onSubmit: (prompt: string, config: { avatar: any; voice: any; brand: any; plan: string }) => void;
  initialBrand?: { id?: string; name: string; color?: string; label?: string; fonts?: string; fullName?: string };
}

export default function VideoAgentPrompt({
  promptValue,
  onChangePrompt,
  onSubmit,
  initialBrand,
}: VideoAgentPromptProps) {
  const [selectedAvatar, setSelectedAvatar] = useState(AVATAR_OPTIONS[0]);
  const [selectedVoice, setSelectedVoice] = useState(VOICE_OPTIONS[0]);
  const [selectedBrand, setSelectedBrand] = useState(() => {
    if (initialBrand) {
      return {
        id: initialBrand.id || "applied-brand",
        name: initialBrand.name,
        fullName: initialBrand.fullName || initialBrand.name,
        label: initialBrand.label || "Brand System",
        color: initialBrand.color || "#000000",
        fonts: initialBrand.fonts || "Custom Brand Spec",
      };
    }
    return BRAND_SYSTEM_OPTIONS[0];
  });
  const [selectedPlan, setSelectedPlan] = useState("Plan");
  const [activeModal, setActiveModal] = useState<"asset" | "knowledge" | "brand" | "avatar" | null>(null);

  useEffect(() => {
    if (initialBrand) {
      setSelectedBrand({
        id: initialBrand.id || "applied-brand",
        name: initialBrand.name,
        fullName: initialBrand.fullName || initialBrand.name,
        label: initialBrand.label || "Brand System",
        color: initialBrand.color || "#000000",
        fonts: initialBrand.fonts || "Custom Brand Spec",
      });
    }
  }, [initialBrand]);

  // Dropdown open states
  const [openDropdown, setOpenDropdown] = useState<
    "avatar" | "voice" | "brand" | "plus" | "settings" | "plan" | null
  >(null);

  // Settings state
  const [aspectRatio, setAspectRatio] = useState<"16:9" | "9:16" | "1:1">("16:9");
  const [targetDuration, setTargetDuration] = useState("1-2 mins");
  const [videoTone, setVideoTone] = useState("Professional");

  const composerRef = useRef<HTMLDivElement>(null);

  // Close dropdowns on outside click
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (composerRef.current && !composerRef.current.contains(event.target as Node)) {
        setOpenDropdown(null);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const toggleDropdown = (name: typeof openDropdown) => {
    setOpenDropdown((prev) => (prev === name ? null : name));
  };

  const handleSubmit = () => {
    onSubmit(promptValue, {
      avatar: selectedAvatar,
      voice: selectedVoice,
      brand: selectedBrand,
      plan: selectedPlan,
    });
  };

  const handleBrandSelected = (brand: BrandSystemData) => {
    setSelectedBrand({
      id: brand.id,
      name: brand.name,
      fullName: brand.fullName || brand.name,
      color: brand.primaryColor,
      label: "Brand System",
      fonts: brand.fontFamily,
    });
    setActiveModal(null);
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
    setActiveModal(null);
  };

  return (
    <div
      ref={composerRef}
      className="w-full bg-[#0A0F1A] border border-[#1B2940] rounded-3xl p-5 md:p-6 shadow-2xl shadow-black/60 transition-all relative"
    >
      {/* 1. Context Chips Top Row */}
      <div className="flex flex-wrap items-center gap-2.5 pb-4 border-b border-[#1B2940]/70">
        {/* CHIP 1: Avatar */}
        <div className="relative">
          <button
            type="button"
            onClick={() => toggleDropdown("avatar")}
            className="flex items-center gap-2 bg-[#0B1220] hover:bg-[#101827] border border-[#1B2940] hover:border-cyan-500/40 px-3 py-1.5 rounded-full text-xs transition-colors cursor-pointer text-slate-200 shadow-sm"
          >
            <img
              src={selectedAvatar.image}
              alt={selectedAvatar.name}
              className="w-5 h-5 rounded-full object-cover ring-1 ring-cyan-500/40"
            />
            <span className="font-bold text-white">{selectedAvatar.name}</span>
            <span className="text-slate-400 font-medium">{selectedAvatar.label}</span>
            <ChevronDown size={13} className="text-slate-400" />
          </button>

          {/* Avatar Dropdown */}
          {openDropdown === "avatar" && (
            <div className="absolute left-0 top-full mt-2 w-64 bg-[#0B111E] border border-[#1B2940] rounded-2xl shadow-2xl p-2 z-40 animate-in fade-in slide-in-from-top-2 duration-150">
              <div className="px-3 py-1.5 text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                Select Avatar
              </div>
              <div className="space-y-1">
                {AVATAR_OPTIONS.map((av) => (
                  <button
                    key={av.id}
                    onClick={() => {
                      setSelectedAvatar(av);
                      setOpenDropdown(null);
                    }}
                    className={`w-full flex items-center justify-between p-2 rounded-xl text-xs transition-colors text-left cursor-pointer ${
                      selectedAvatar.id === av.id
                        ? "bg-cyan-950/60 border border-cyan-500/40 text-cyan-300 font-semibold"
                        : "text-slate-300 hover:bg-[#101827]"
                    }`}
                  >
                    <div className="flex items-center gap-2.5">
                      <img
                        src={av.image}
                        alt={av.name}
                        className="w-7 h-7 rounded-full object-cover ring-1 ring-slate-700"
                      />
                      <div>
                        <div className="font-semibold text-white">{av.name}</div>
                        <div className="text-[10px] text-slate-400">{av.type}</div>
                      </div>
                    </div>
                    {selectedAvatar.id === av.id && <Check size={14} className="text-cyan-400" />}
                  </button>
                ))}
              </div>
              <div className="pt-1.5 mt-1.5 border-t border-[#1B2940]">
                <button
                  type="button"
                  onClick={() => {
                    setOpenDropdown(null);
                    setActiveModal("avatar");
                  }}
                  className="w-full text-center py-1.5 rounded-xl text-xs font-bold text-cyan-400 hover:text-cyan-300 hover:bg-cyan-500/10 transition-colors cursor-pointer"
                >
                  Choose Avatar...
                </button>
              </div>
            </div>
          )}
        </div>

        {/* CHIP 2: Voice */}
        <div className="relative">
          <button
            type="button"
            onClick={() => toggleDropdown("voice")}
            className="flex items-center gap-2 bg-[#0B1220] hover:bg-[#101827] border border-[#1B2940] hover:border-cyan-500/40 px-3 py-1.5 rounded-full text-xs transition-colors cursor-pointer text-slate-200 shadow-sm"
          >
            <div className="w-5 h-5 rounded-full bg-blue-500/20 text-blue-400 flex items-center justify-center">
              <Play size={10} className="fill-blue-400 ml-0.5" />
            </div>
            <span className="font-bold text-white">{selectedVoice.name}</span>
            <span className="text-slate-400 font-medium">{selectedVoice.label}</span>
            <ChevronDown size={13} className="text-slate-400" />
          </button>

          {/* Voice Dropdown */}
          {openDropdown === "voice" && (
            <div className="absolute left-0 top-full mt-2 w-64 bg-[#0B111E] border border-[#1B2940] rounded-2xl shadow-2xl p-2 z-40 animate-in fade-in slide-in-from-top-2 duration-150">
              <div className="px-3 py-1.5 text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                Select Voice
              </div>
              <div className="space-y-1">
                {VOICE_OPTIONS.map((vc) => (
                  <button
                    key={vc.id}
                    onClick={() => {
                      setSelectedVoice(vc);
                      setOpenDropdown(null);
                    }}
                    className={`w-full flex items-center justify-between p-2 rounded-xl text-xs transition-colors text-left cursor-pointer ${
                      selectedVoice.id === vc.id
                        ? "bg-blue-950/60 border border-blue-500/40 text-blue-300 font-semibold"
                        : "text-slate-300 hover:bg-[#101827]"
                    }`}
                  >
                    <div className="flex items-center gap-2.5">
                      <div className="w-7 h-7 rounded-full bg-blue-500/20 text-blue-400 flex items-center justify-center flex-shrink-0">
                        <Volume2 size={14} />
                      </div>
                      <div>
                        <div className="font-semibold text-white">{vc.name}</div>
                        <div className="text-[10px] text-slate-400">{vc.style}</div>
                      </div>
                    </div>
                    {selectedVoice.id === vc.id && <Check size={14} className="text-blue-400" />}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* CHIP 3: Brand System */}
        <div className="relative">
          <button
            type="button"
            onClick={() => toggleDropdown("brand")}
            className="flex items-center gap-2 bg-[#0B1220] hover:bg-[#101827] border border-[#1B2940] hover:border-cyan-500/40 px-3 py-1.5 rounded-full text-xs transition-colors cursor-pointer text-slate-200 shadow-sm"
          >
            <div
              className="w-4 h-4 rounded-full border border-slate-500"
              style={{ backgroundColor: selectedBrand.color }}
            ></div>
            <span className="font-bold text-white">{selectedBrand.name}</span>
            <span className="text-slate-400 font-medium">{selectedBrand.label}</span>
            <ChevronDown size={13} className="text-slate-400" />
          </button>

          {/* Brand System Dropdown */}
          {openDropdown === "brand" && (
            <div className="absolute left-0 top-full mt-2 w-64 bg-[#0B111E] border border-[#1B2940] rounded-2xl shadow-2xl p-2 z-40 animate-in fade-in slide-in-from-top-2 duration-150">
              <div className="px-3 py-1.5 text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                Select Brand System
              </div>
              <div className="space-y-1">
                {(BRAND_SYSTEM_OPTIONS.some((b) => b.name === selectedBrand.name || b.id === selectedBrand.id)
                  ? BRAND_SYSTEM_OPTIONS
                  : [selectedBrand, ...BRAND_SYSTEM_OPTIONS]
                ).map((bd) => (
                  <button
                    key={bd.id}
                    onClick={() => {
                      setSelectedBrand(bd);
                      setOpenDropdown(null);
                    }}
                    className={`w-full flex items-center justify-between p-2 rounded-xl text-xs transition-colors text-left cursor-pointer ${
                      selectedBrand.name === bd.name || selectedBrand.id === bd.id
                        ? "bg-[#152033] border border-cyan-500/40 text-cyan-300 font-semibold"
                        : "text-slate-300 hover:bg-[#101827]"
                    }`}
                  >
                    <div className="flex items-center gap-2.5">
                      <div
                        className="w-5 h-5 rounded-full border border-slate-600 flex-shrink-0"
                        style={{ backgroundColor: bd.color }}
                      ></div>
                      <div>
                        <div className="font-semibold text-white">{bd.fullName || bd.name}</div>
                        <div className="text-[10px] text-slate-400">{bd.fonts || "Brand System"}</div>
                      </div>
                    </div>
                    {(selectedBrand.name === bd.name || selectedBrand.id === bd.id) && <Check size={14} className="text-cyan-400" />}
                  </button>
                ))}
              </div>
              <div className="pt-1.5 mt-1.5 border-t border-[#1B2940]">
                <button
                  type="button"
                  onClick={() => {
                    setOpenDropdown(null);
                    setActiveModal("brand");
                  }}
                  className="w-full text-center py-1.5 rounded-xl text-xs font-bold text-cyan-400 hover:text-cyan-300 hover:bg-cyan-500/10 transition-colors cursor-pointer"
                >
                  Choose a Brand System...
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 2. Prompt Textarea */}
      <div className="py-4">
        <textarea
          value={promptValue}
          onChange={(e) => onChangePrompt(e.target.value)}
          placeholder="Ask for a video, an avatar, or anything in between—I can get you started."
          rows={3}
          className="w-full bg-transparent text-white placeholder:text-slate-500 text-sm md:text-base font-normal leading-relaxed outline-none resize-none"
        />
      </div>

      {/* 3. Bottom Controls Row */}
      <div className="flex items-center justify-between pt-2">
        {/* Bottom Left Controls: Plus & Settings */}
        <div className="flex items-center gap-2">
          {/* Plus (+) Button & Menu */}
          <div className="relative">
            <button
              type="button"
              onClick={() => toggleDropdown("plus")}
              className="w-8 h-8 rounded-full bg-[#0B1220] hover:bg-[#101827] border border-[#1B2940] hover:border-cyan-500/40 text-slate-300 hover:text-white flex items-center justify-center transition-colors cursor-pointer shadow-sm"
              title="Add attachment or resource"
            >
              <Plus size={16} />
            </button>

            {/* Plus Menu Popup */}
            {openDropdown === "plus" && (
              <div className="absolute left-0 bottom-full mb-3 w-44 bg-[#0B111E] border border-[#1B2940] rounded-2xl shadow-2xl p-1.5 z-50 animate-in fade-in slide-in-from-bottom-2 duration-150">
                <div className="flex flex-col gap-0.5">
                  <button
                    type="button"
                    onClick={() => {
                      setOpenDropdown(null);
                      setActiveModal("asset");
                    }}
                    className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-bold text-slate-300 hover:text-white hover:bg-[#101827] transition-colors text-left cursor-pointer group"
                  >
                    <FolderClosed
                      size={15}
                      className="text-slate-400 group-hover:text-cyan-400 transition-colors"
                    />
                    <span>Assets</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setOpenDropdown(null);
                      setActiveModal("knowledge");
                    }}
                    className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-bold text-slate-300 hover:text-white hover:bg-[#101827] transition-colors text-left cursor-pointer group"
                  >
                    <BookOpen
                      size={15}
                      className="text-slate-400 group-hover:text-cyan-400 transition-colors"
                    />
                    <span>Knowledge</span>
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Sliders / Settings Button & Menu */}
          <div className="relative">
            <button
              type="button"
              onClick={() => toggleDropdown("settings")}
              className="w-8 h-8 rounded-full bg-[#0B1220] hover:bg-[#101827] border border-[#1B2940] hover:border-cyan-500/40 text-slate-300 hover:text-white flex items-center justify-center transition-colors cursor-pointer shadow-sm"
              title="Video Generation Settings"
            >
              <SlidersHorizontal size={15} />
            </button>

            {/* Settings Popup */}
            {openDropdown === "settings" && (
              <div className="absolute left-0 bottom-full mb-2 w-64 bg-[#0B111E] border border-[#1B2940] rounded-2xl shadow-2xl p-4 z-40 animate-in fade-in slide-in-from-bottom-2 duration-150">
                <div className="text-xs font-bold text-white mb-3 flex items-center gap-1.5">
                  <SlidersHorizontal size={13} className="text-cyan-400" />
                  <span>Video Agent Parameters</span>
                </div>

                {/* Aspect Ratio Selection */}
                <div className="mb-3">
                  <label className="text-[11px] font-semibold text-slate-400 block mb-1.5">
                    Aspect Ratio
                  </label>
                  <div className="grid grid-cols-3 gap-1.5">
                    {(["16:9", "9:16", "1:1"] as const).map((ratio) => (
                      <button
                        key={ratio}
                        type="button"
                        onClick={() => setAspectRatio(ratio)}
                        className={`py-1 text-xs rounded-lg font-medium border text-center transition-colors cursor-pointer ${
                          aspectRatio === ratio
                            ? "bg-cyan-500/20 text-cyan-300 border-cyan-500/50 font-bold"
                            : "bg-[#07090e] text-slate-300 border-[#1B2940] hover:bg-[#101827]"
                        }`}
                      >
                        {ratio}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Duration Selection */}
                <div className="mb-3">
                  <label className="text-[11px] font-semibold text-slate-400 block mb-1.5">
                    Target Duration
                  </label>
                  <select
                    value={targetDuration}
                    onChange={(e) => setTargetDuration(e.target.value)}
                    className="w-full bg-[#07090e] border border-[#1B2940] rounded-lg px-2.5 py-1.5 text-xs text-slate-200 outline-none focus:border-cyan-500"
                  >
                    <option value="30 seconds">30 seconds (Shorts/TikTok)</option>
                    <option value="1-2 mins">1-2 mins (Explainer)</option>
                    <option value="3-5 mins">3-5 mins (Course Lesson)</option>
                  </select>
                </div>

                {/* Video Tone */}
                <div>
                  <label className="text-[11px] font-semibold text-slate-400 block mb-1.5">
                    Tone & Style
                  </label>
                  <select
                    value={videoTone}
                    onChange={(e) => setVideoTone(e.target.value)}
                    className="w-full bg-[#07090e] border border-[#1B2940] rounded-lg px-2.5 py-1.5 text-xs text-slate-200 outline-none focus:border-cyan-500"
                  >
                    <option value="Professional">Professional & Polished</option>
                    <option value="Casual">Casual & Conversational</option>
                    <option value="Energetic">High Energy & Viral</option>
                  </select>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Bottom Right Controls: Plan & Submit */}
        <div className="flex items-center gap-2.5">
          {/* Plan Button & Dropdown */}
          <div className="relative">
            <button
              type="button"
              onClick={() => toggleDropdown("plan")}
              className="flex items-center gap-1.5 px-3.5 py-2 rounded-full text-xs font-semibold text-slate-200 hover:text-white bg-[#0B1220] hover:bg-[#101827] border border-[#1B2940] hover:border-cyan-500/40 transition-colors cursor-pointer shadow-sm"
            >
              {selectedPlan === "Auto-pilot" ? (
                <Sparkles size={13} className="text-cyan-400" />
              ) : (
                <CalendarCheck size={13} className="text-cyan-400" />
              )}
              <span>{selectedPlan}</span>
              <ChevronDown size={13} className="text-slate-400" />
            </button>

            {/* Plan Dropdown */}
            {openDropdown === "plan" && (
              <div className="absolute right-0 bottom-full mb-3 w-[315px] max-w-[calc(100vw-3rem)] bg-[#0B111E] border border-[#1B2940] rounded-[20px] shadow-2xl p-2.5 z-50 animate-in fade-in slide-in-from-bottom-2 duration-150">
                <div className="flex flex-col gap-1">
                  {/* Option 1: Plan */}
                  <button
                    type="button"
                    onClick={() => {
                      setSelectedPlan("Plan");
                      setOpenDropdown(null);
                    }}
                    className={`w-full flex items-start gap-3 p-3 rounded-2xl text-left transition-colors cursor-pointer group ${
                      selectedPlan === "Plan"
                        ? "bg-[#101827] border border-cyan-500/30 text-white"
                        : "text-slate-300 hover:bg-[#101827]"
                    }`}
                  >
                    <div className="w-8 h-8 rounded-xl bg-cyan-500/15 border border-cyan-500/30 flex items-center justify-center text-cyan-400 flex-shrink-0 mt-0.5">
                      <CalendarCheck size={16} strokeWidth={2} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-bold text-white leading-tight">
                          Plan
                        </span>
                        {selectedPlan === "Plan" && (
                          <Check size={14} className="text-cyan-400 flex-shrink-0" />
                        )}
                      </div>
                      <p className="text-xs text-slate-400 leading-relaxed mt-0.5 whitespace-pre-line">
                        I&apos;ll ask a few quick questions,
                        {"\n"}then build your video.
                      </p>
                    </div>
                  </button>

                  {/* Option 2: Auto-pilot */}
                  <button
                    type="button"
                    onClick={() => {
                      setSelectedPlan("Auto-pilot");
                      setOpenDropdown(null);
                    }}
                    className={`w-full flex items-start gap-3 p-3 rounded-2xl text-left transition-colors cursor-pointer group ${
                      selectedPlan === "Auto-pilot"
                        ? "bg-[#101827] border border-cyan-500/30 text-white"
                        : "text-slate-300 hover:bg-[#101827]"
                    }`}
                  >
                    <div className="w-8 h-8 rounded-xl bg-purple-500/15 border border-purple-500/30 flex items-center justify-center text-purple-400 flex-shrink-0 mt-0.5">
                      <Sparkles size={16} strokeWidth={2} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-bold text-white leading-tight">
                          Auto-pilot
                        </span>
                        {selectedPlan === "Auto-pilot" && (
                          <Check size={14} className="text-purple-400 flex-shrink-0" />
                        )}
                      </div>
                      <p className="text-xs text-slate-400 leading-relaxed mt-0.5">
                        Auto-generate your video.
                      </p>
                    </div>
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Submit Button */}
          <button
            type="button"
            onClick={handleSubmit}
            className="bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 text-xs font-bold px-6 py-2.5 rounded-full shadow-lg shadow-cyan-500/25 transition-all duration-200 cursor-pointer flex items-center gap-1.5 active:scale-95"
          >
            <span>Submit</span>
          </button>
        </div>
      </div>

      {/* Attach Asset Modal */}
      <AttachAssetModal
        isOpen={activeModal === "asset"}
        onClose={() => setActiveModal(null)}
        onAttachFile={(fileName) => {
          onChangePrompt(
            (promptValue ? promptValue + "\n" : "") + `[Attached Asset: ${fileName}]`
          );
        }}
      />

      {/* Knowledge Hub Modal */}
      <KnowledgeHubModal
        isOpen={activeModal === "knowledge"}
        onClose={() => setActiveModal(null)}
      />

      {/* Choose a Brand System Modal */}
      <ChooseBrandSystemModal
        isOpen={activeModal === "brand"}
        onClose={() => setActiveModal(null)}
        onSelectBrandSystem={handleBrandSelected}
        selectedBrandId={selectedBrand?.id}
      />

      {/* Choose Avatar Modal */}
      <ChooseAvatarModal
        isOpen={activeModal === "avatar"}
        onClose={() => setActiveModal(null)}
        onSelectAvatar={handleAvatarSelected}
        selectedAvatarId={selectedAvatar.id}
      />
    </div>
  );
}
