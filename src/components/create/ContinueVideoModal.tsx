"use client";

import React, { useState, useRef, useEffect } from "react";
import {
  X,
  Play,
  Volume2,
  Sparkles,
  RefreshCw,
  ArrowLeftRight,
  ChevronDown,
  Clock,
  Video as VideoIcon,
  Subtitles,
  Plus,
  ArrowRight,
  Check,
  Paperclip,
  CheckCircle2,
  Shirt,
  MessageSquare,
} from "lucide-react";
import {
  AVATAR_OPTIONS,
  VOICE_OPTIONS,
  BRAND_SYSTEM_OPTIONS,
} from "./videoAgentData";
import AttachAssetModal from "./AttachAssetModal";
import ChooseBrandSystemModal, { BrandSystemData } from "./ChooseBrandSystemModal";
import ChooseAvatarModal from "./ChooseAvatarModal";
import { AvatarOptionData, AvatarLook } from "./videoAgentData";

interface ContinueVideoModalProps {
  isOpen: boolean;
  onClose: () => void;
  onContinue: (config: {
    avatar: any;
    voice: any;
    script: string;
    brand: any;
    speed: string;
    quality: string;
    seedance: boolean;
    captions: boolean;
    instructions: string;
    attachments: string[];
  }) => void;
  initialPrompt?: string;
  initialAvatar?: any;
  initialVoice?: any;
  initialBrand?: any;
}

export default function ContinueVideoModal({
  isOpen,
  onClose,
  onContinue,
  initialPrompt = "",
  initialAvatar = AVATAR_OPTIONS[0],
  initialVoice = VOICE_OPTIONS[0],
  initialBrand = BRAND_SYSTEM_OPTIONS[0],
}: ContinueVideoModalProps) {
  const [selectedAvatar, setSelectedAvatar] = useState(initialAvatar);
  const [selectedVoice, setSelectedVoice] = useState(initialVoice);
  const [selectedBrand, setSelectedBrand] = useState(initialBrand);
  const [scriptText, setScriptText] = useState(initialPrompt);

  // Options State
  const [speedOption, setSpeedOption] = useState("Auto");
  const [qualityOption, setQualityOption] = useState("Auto");
  const [seedanceEnabled, setSeedanceEnabled] = useState(false);
  const [captionsEnabled, setCaptionsEnabled] = useState(true);
  const [instructions, setInstructions] = useState("");
  const [attachments, setAttachments] = useState<string[]>([]);

  // Popover States
  const [openDropdown, setOpenDropdown] = useState<
    "avatar" | "voice" | "brand" | "speed" | "quality" | "instructions" | null
  >(null);
  const [isAttachModalOpen, setIsAttachModalOpen] = useState(false);
  const [isBrandModalOpen, setIsBrandModalOpen] = useState(false);
  const [isAvatarModalOpen, setIsAvatarModalOpen] = useState(false);
  const [instructionsInput, setInstructionsInput] = useState("");

  const modalRef = useRef<HTMLDivElement>(null);

  // Sync initial props when opened
  useEffect(() => {
    if (isOpen) {
      if (initialPrompt && !scriptText) {
        setScriptText(initialPrompt);
      }
      if (initialAvatar) setSelectedAvatar(initialAvatar);
      if (initialVoice) setSelectedVoice(initialVoice);
      if (initialBrand) setSelectedBrand(initialBrand);
    }
  }, [isOpen, initialPrompt, initialAvatar, initialVoice, initialBrand]);

  // Close on Escape key
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (
        e.key === "Escape" &&
        !isBrandModalOpen &&
        !isAttachModalOpen &&
        !isAvatarModalOpen
      ) {
        onClose();
      }
    }
    if (isOpen) {
      window.addEventListener("keydown", handleKeyDown);
    }
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose, isBrandModalOpen, isAttachModalOpen, isAvatarModalOpen]);

  if (!isOpen) return null;

  const handleScriptWriter = () => {
    const topic = scriptText.trim() || "modern video production";
    const sampleScript = `Hook: Stop scrolling if you want to scale your video engagement in 2026.\n\nHere are 3 essential steps:\n1. Hook your viewers in the first 3 seconds with a bold problem statement.\n2. Deliver high-density actionable value with clear visual slides.\n3. End with a singular, frictionless call to action.\n\nReady to transform your content? Let's get started today!`;
    setScriptText(sampleScript);
  };

  const handleSwapAvatar = () => {
    setIsAvatarModalOpen(true);
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
    setIsAvatarModalOpen(false);
  };

  const handleContinue = () => {
    onContinue({
      avatar: selectedAvatar,
      voice: selectedVoice,
      script: scriptText,
      brand: selectedBrand,
      speed: speedOption,
      quality: qualityOption,
      seedance: seedanceEnabled,
      captions: captionsEnabled,
      instructions,
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
        className="w-full max-w-2xl bg-[#0A0F1A] rounded-3xl p-6 sm:p-8 shadow-2xl border border-[#1B2940] text-slate-100 my-8 max-h-[92vh] overflow-y-auto animate-in zoom-in-95 duration-150 relative scrollbar-thin"
      >
        {/* 1. Modal Header */}
        <div className="flex items-center justify-between pb-5 border-b border-[#1B2940]">
          <h2 className="text-xl sm:text-2xl font-black text-white tracking-tight">
            Continue creating your video
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="w-8 h-8 rounded-full hover:bg-[#101827] flex items-center justify-center text-slate-400 hover:text-white transition-colors cursor-pointer"
            title="Close"
          >
            <X size={18} />
          </button>
        </div>

        <div className="space-y-6 pt-5">
          {/* 2. AVATAR SECTION */}
          <div>
            <div className="text-xs font-bold text-white mb-2 tracking-wide">
              Avatar
            </div>
            <div className="bg-[#0B111E] border border-[#1B2940] rounded-2xl p-3.5 sm:p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-2xs">
              {/* Left Side: Avatar thumbnail & name & voice pill */}
              <div
                onClick={() => setIsAvatarModalOpen(true)}
                className="flex items-center gap-3.5 cursor-pointer group flex-1"
              >
                <img
                  src={selectedAvatar.image}
                  alt={selectedAvatar.name}
                  className="w-12 h-12 rounded-full object-cover ring-2 ring-[#1B2940] shadow-sm flex-shrink-0 group-hover:ring-cyan-500 transition-all"
                />
                <div>
                  <div className="text-sm font-bold text-white group-hover:text-cyan-400 transition-colors">
                    {selectedAvatar.name}
                  </div>
                  <div className="flex flex-wrap items-center gap-2 mt-1">
                    {/* Voice Pill */}
                    <div
                      onClick={(e) => e.stopPropagation()}
                      className="bg-[#101827] border border-[#1B2940] px-2.5 py-1 rounded-full text-[11px] font-semibold text-slate-300 flex items-center gap-1.5 shadow-2xs"
                    >
                      <Volume2 size={12} className="text-cyan-400" />
                      <span>{selectedVoice.name}</span>
                      <Play size={9} className="text-slate-400 fill-slate-400 ml-0.5" />
                    </div>

                    {/* Change Look Pill */}
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        setIsAvatarModalOpen(true);
                      }}
                      className="bg-[#101827] hover:bg-[#1B2940] border border-[#1B2940] px-2.5 py-1 rounded-full text-[11px] font-semibold text-slate-300 hover:text-white flex items-center gap-1.5 shadow-2xs transition-colors cursor-pointer"
                    >
                      <Shirt size={12} className="text-slate-400" />
                      <span>Change Look</span>
                    </button>
                  </div>
                </div>
              </div>

              {/* Right Side: Swap & Remove Buttons */}
              <div className="flex items-center gap-1.5 self-end sm:self-center">
                <button
                  type="button"
                  onClick={() => setIsAvatarModalOpen(true)}
                  className="w-8 h-8 rounded-full bg-[#101827] hover:bg-[#1B2940] border border-[#1B2940] text-slate-300 flex items-center justify-center transition-colors cursor-pointer shadow-2xs"
                  title="Switch Avatar"
                >
                  <ArrowLeftRight size={14} />
                </button>
                <button
                  type="button"
                  onClick={() => setSelectedAvatar(AVATAR_OPTIONS[0])}
                  className="w-8 h-8 rounded-full hover:bg-[#101827] text-slate-400 hover:text-white flex items-center justify-center transition-colors cursor-pointer"
                  title="Reset Avatar"
                >
                  <X size={15} />
                </button>
              </div>
            </div>
          </div>

          {/* 3. SCRIPT SECTION */}
          <div>
            <div className="text-xs font-bold text-white mb-2 tracking-wide">
              Script
            </div>
            <div className="border border-[#1B2940] rounded-2xl bg-[#0B111E] p-3.5 shadow-2xs relative focus-within:border-cyan-500 focus-within:ring-1 focus-within:ring-cyan-500/30 transition-all">
              <textarea
                value={scriptText}
                onChange={(e) => setScriptText(e.target.value)}
                placeholder="Type your script or a prompt for me to generate one for you"
                rows={4}
                className="w-full bg-transparent text-xs sm:text-sm text-white placeholder:text-slate-500 font-normal leading-relaxed outline-none resize-none"
              />

              {/* Bottom Inside: Script Writer Button */}
              <div className="pt-2 flex items-center justify-between border-t border-[#1B2940]/60">
                <button
                  type="button"
                  onClick={handleScriptWriter}
                  className="bg-[#101827] hover:bg-[#1B2940] border border-[#1B2940] text-slate-200 font-bold text-xs px-3.5 py-1.5 rounded-full flex items-center gap-1.5 transition-colors cursor-pointer shadow-2xs"
                >
                  <Sparkles size={13} className="text-cyan-400" />
                  <span>Script Writer</span>
                </button>

                <span className="text-[11px] text-slate-500 font-mono">
                  {scriptText.length} chars
                </span>
              </div>
            </div>
          </div>

          {/* 4. BRAND SYSTEM SECTION */}
          <div>
            <div className="text-xs font-bold text-white mb-2 tracking-wide">
              Brand System
            </div>
            <div
              onClick={() => setIsBrandModalOpen(true)}
              className="bg-[#0B111E] hover:bg-[#101827] border border-[#1B2940] rounded-2xl p-3.5 flex items-center justify-between cursor-pointer transition-colors shadow-2xs"
            >
              <div className="flex items-center gap-3">
                <div
                  className="w-5 h-5 rounded-full border border-slate-600 shadow-2xs"
                  style={{ backgroundColor: selectedBrand.color || selectedBrand.primaryColor }}
                ></div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-white">
                    {selectedBrand.name}
                  </span>
                  <span className="text-[11px] text-slate-400 font-medium">
                    Brand System
                  </span>
                </div>
              </div>

              <ChevronDown size={14} className="text-slate-500" />
            </div>
          </div>

          {/* 5. OPTIONS SECTION */}
          <div>
            <div className="text-xs font-bold text-white mb-2 tracking-wide">
              Options
            </div>

            {/* Row 1: Horizontal Option Pills */}
            <div className="flex flex-wrap items-center gap-2 mb-2.5">
              {/* Option 1: Auto (Speed/Duration) */}
              <div className="relative">
                <button
                  type="button"
                  onClick={() =>
                    setOpenDropdown((prev) => (prev === "speed" ? null : "speed"))
                  }
                  className="bg-[#0B1220] hover:bg-[#101827] border border-[#1B2940] px-3.5 py-1.5 rounded-full text-xs font-semibold text-slate-300 flex items-center gap-1.5 shadow-2xs transition-colors cursor-pointer"
                >
                  <Clock size={13} className="text-slate-400" />
                  <span>{speedOption}</span>
                  <ChevronDown size={12} className="text-slate-500" />
                </button>

                {openDropdown === "speed" && (
                  <div className="absolute left-0 bottom-full mb-2 w-36 bg-[#0B111E] border border-[#1B2940] rounded-xl shadow-xl p-1.5 z-50 animate-in fade-in duration-150">
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
                            ? "bg-cyan-500/20 text-cyan-300 font-bold"
                            : "text-slate-300 hover:bg-[#101827]"
                        }`}
                      >
                        {opt}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Option 2: Auto (Resolution/Framerate) */}
              <div className="relative">
                <button
                  type="button"
                  onClick={() =>
                    setOpenDropdown((prev) => (prev === "quality" ? null : "quality"))
                  }
                  className="bg-[#0B1220] hover:bg-[#101827] border border-[#1B2940] px-3.5 py-1.5 rounded-full text-xs font-semibold text-slate-300 flex items-center gap-1.5 shadow-2xs transition-colors cursor-pointer"
                >
                  <VideoIcon size={13} className="text-slate-400" />
                  <span>{qualityOption}</span>
                  <ChevronDown size={12} className="text-slate-500" />
                </button>

                {openDropdown === "quality" && (
                  <div className="absolute left-0 bottom-full mb-2 w-36 bg-[#0B111E] border border-[#1B2940] rounded-xl shadow-xl p-1.5 z-50 animate-in fade-in duration-150">
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
                            ? "bg-cyan-500/20 text-cyan-300 font-bold"
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
                className={`border px-3.5 py-1.5 rounded-full text-xs font-semibold transition-colors cursor-pointer shadow-2xs ${
                  seedanceEnabled
                    ? "bg-cyan-500/20 border-cyan-500 text-cyan-300 font-bold"
                    : "bg-[#0B1220] hover:bg-[#101827] border-[#1B2940] text-slate-300"
                }`}
              >
                Seedance {seedanceEnabled ? "ON" : "OFF"}
              </button>

              {/* Option 4: Captions Toggle */}
              <button
                type="button"
                onClick={() => setCaptionsEnabled(!captionsEnabled)}
                className={`border px-3.5 py-1.5 rounded-full text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer shadow-2xs ${
                  captionsEnabled
                    ? "bg-cyan-500/20 border-cyan-500 text-cyan-300 font-bold"
                    : "bg-[#0B1220] hover:bg-[#101827] border-[#1B2940] text-slate-300"
                }`}
              >
                <Subtitles size={13} />
                <span>Captions {captionsEnabled ? "ON" : "OFF"}</span>
              </button>

              {/* Option 5: Instructions */}
              <div className="relative">
                <button
                  type="button"
                  onClick={() =>
                    setOpenDropdown((prev) =>
                      prev === "instructions" ? null : "instructions"
                    )
                  }
                  className={`border px-3.5 py-1.5 rounded-full text-xs font-semibold flex items-center gap-1 shadow-2xs transition-colors cursor-pointer ${
                    instructions
                      ? "bg-cyan-500/20 border-cyan-500 text-cyan-300 font-bold"
                      : "bg-[#0B1220] hover:bg-[#101827] border-[#1B2940] text-slate-300"
                  }`}
                >
                  <Plus size={12} />
                  <span>{instructions ? "Instructions Added" : "Instructions"}</span>
                </button>

                {openDropdown === "instructions" && (
                  <div className="absolute left-0 bottom-full mb-2 w-64 bg-[#0B111E] border border-[#1B2940] rounded-2xl shadow-xl p-3 z-50 animate-in fade-in duration-150">
                    <div className="text-[11px] font-bold text-slate-400 mb-1.5">
                      Custom Directives
                    </div>
                    <input
                      type="text"
                      value={instructionsInput}
                      onChange={(e) => setInstructionsInput(e.target.value)}
                      placeholder="e.g. Keep tone energetic and concise"
                      className="w-full bg-[#07090e] border border-[#1B2940] rounded-xl px-2.5 py-1.5 text-xs text-white outline-none focus:border-cyan-500 placeholder:text-slate-600 mb-2"
                    />
                    <div className="flex justify-end gap-1.5">
                      <button
                        type="button"
                        onClick={() => {
                          setInstructions(instructionsInput);
                          setOpenDropdown(null);
                        }}
                        className="bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 text-[11px] font-bold px-3 py-1 rounded-lg"
                      >
                        Save
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Row 2: Attachments Pill */}
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setIsAttachModalOpen(true)}
                className={`border px-3.5 py-1.5 rounded-full text-xs font-semibold flex items-center gap-1.5 shadow-2xs transition-colors cursor-pointer ${
                  attachments.length > 0
                    ? "bg-cyan-500/20 border-cyan-500 text-cyan-300 font-bold"
                    : "bg-[#0B1220] hover:bg-[#101827] border-[#1B2940] text-slate-300"
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

        {/* 6. Modal Bottom Footer: Continue Button */}
        <div className="mt-8 pt-4 border-t border-[#1B2940] flex items-center justify-end">
          <button
            type="button"
            onClick={handleContinue}
            className="bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-bold text-xs px-7 py-3 rounded-full shadow-lg hover:shadow-cyan-500/25 transition-all duration-200 cursor-pointer flex items-center gap-2 active:scale-95"
          >
            <span>Continue</span>
            <ArrowRight size={14} />
          </button>
        </div>
      </div>

      {/* Attach Asset Modal (Reusing existing attachment workflow) */}
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
      />
    </div>
  );
}
