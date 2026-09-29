"use client";

import React, { useState, useRef, useEffect } from "react";
import {
  X,
  ArrowLeft,
  Camera,
  Mic,
  Sparkles,
  Smartphone,
  Video,
  Upload,
  AlertCircle,
  HelpCircle,
  ChevronDown,
  FileVideo,
  QrCode,
  Check,
  User,
  Film,
} from "lucide-react";

interface CreateAvatarModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAvatarCreated?: (avatarName: string) => void;
}

export default function CreateAvatarModal({
  isOpen,
  onClose,
  onAvatarCreated,
}: CreateAvatarModalProps) {
  const [recordMethod, setRecordMethod] = useState<"webcam" | "phone">("webcam");
  const [selectedLanguage, setSelectedLanguage] = useState("English");
  const [isLanguageOpen, setIsLanguageOpen] = useState(false);
  const [isHelpOpen, setIsHelpOpen] = useState(false);
  const [uploadedVideo, setUploadedVideo] = useState<{
    name: string;
    size: string;
  } | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const languageMenuRef = useRef<HTMLDivElement>(null);

  const languages = [
    "English",
    "Spanish",
    "French",
    "German",
    "Japanese",
    "Portuguese",
    "Hindi",
    "Chinese",
  ];

  // Escape key listener
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        if (isHelpOpen) {
          setIsHelpOpen(false);
        } else {
          onClose();
        }
      }
    }
    if (isOpen) {
      window.addEventListener("keydown", handleKeyDown);
    }
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose, isHelpOpen]);

  // Outside click for language dropdown
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (
        languageMenuRef.current &&
        !languageMenuRef.current.contains(e.target as Node)
      ) {
        setIsLanguageOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  if (!isOpen) return null;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const sizeMB = (file.size / (1024 * 1024)).toFixed(1);
      setUploadedVideo({
        name: file.name,
        size: `${sizeMB} MB`,
      });
    }
  };

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleRemoveVideo = () => {
    setUploadedVideo(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  return (
    <div
      onClick={onClose}
      className="fixed inset-0 z-60 bg-black/75 backdrop-blur-md flex items-center justify-center p-3 sm:p-4 select-none animate-in fade-in duration-150"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-[1140px] h-[820px] max-h-[94vh] bg-[#0A0F1A] rounded-3xl shadow-2xl border border-[#1B2940] text-slate-100 flex overflow-hidden relative"
      >
        {/* Hidden File Picker for Footage */}
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileChange}
          accept="video/*"
          className="hidden"
        />

        {/* Top-Right Simple X Close Button */}
        <button
          type="button"
          onClick={onClose}
          className="absolute top-5 right-6 z-20 text-slate-400 hover:text-white transition-colors p-1.5 rounded-full hover:bg-[#101827] cursor-pointer"
          title="Close and return to Choose Avatar"
        >
          <X size={20} />
        </button>

        {/* ============================================================ */}
        {/* 1. LEFT SIDEBAR */}
        {/* ============================================================ */}
        <div className="w-56 sm:w-60 border-r border-[#1B2940] p-5 flex flex-col justify-between bg-[#07090e] flex-shrink-0">
          <div>
            {/* Logo / Brand Header */}
            <div className="flex items-center gap-2.5 pb-6">
              <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-indigo-500 via-purple-500 to-cyan-400 flex items-center justify-center shadow-xs">
                <Sparkles size={15} className="text-white" />
              </div>
              <span className="font-bold text-base tracking-tight text-white">
                HeyGen
              </span>
            </div>

            {/* Navigation Menu */}
            <div className="space-y-1">
              <div className="px-3 py-2 rounded-xl text-xs font-medium text-slate-400 hover:bg-[#101827] hover:text-white flex items-center gap-2.5 cursor-pointer transition-colors">
                <Film size={15} className="text-slate-500" />
                <span>Avatar Shots</span>
              </div>

              {/* Active Item: Avatars */}
              <div className="px-3 py-2 rounded-xl text-xs font-bold text-cyan-300 bg-cyan-500/20 border border-cyan-500/30 flex items-center gap-2.5 cursor-pointer transition-colors shadow-2xs">
                <User size={15} className="text-cyan-400" />
                <span>Avatars</span>
              </div>

              <div className="px-3 py-2 rounded-xl text-xs font-medium text-slate-400 hover:bg-[#101827] hover:text-white flex items-center gap-2.5 cursor-pointer transition-colors">
                <Mic size={15} className="text-slate-500" />
                <span>Voices</span>
              </div>
            </div>

            {/* Section: CREATE VIDEO */}
            <div className="mt-8">
              <div className="px-3 pb-2 text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                Create Video
              </div>
              <div className="px-3 py-2 rounded-xl text-xs font-medium text-slate-400 hover:bg-[#101827] hover:text-white flex items-center gap-2.5 cursor-pointer transition-colors">
                <Sparkles size={15} className="text-slate-500" />
                <span>AI Studio</span>
              </div>
            </div>
          </div>

          {/* Bottom User Avatar Chip */}
          <div className="pt-4 border-t border-[#1B2940] flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-full bg-[#101827] border border-[#1B2940] text-cyan-400 flex items-center justify-center text-xs font-bold shadow-xs">
              U
            </div>
            <div className="min-w-0 flex-1">
              <div className="text-xs font-bold text-white truncate">
                User Workspace
              </div>
              <div className="text-[10px] text-slate-500 truncate">Free Plan</div>
            </div>
          </div>
        </div>

        {/* ============================================================ */}
        {/* 2. MAIN CONTENT AREA */}
        {/* ============================================================ */}
        <div className="flex-1 overflow-y-auto p-6 sm:p-10 flex flex-col items-center justify-between scrollbar-thin bg-[#0A0F1A]">
          <div className="w-full max-w-2xl flex flex-col items-center text-center">
            {/* Top Heading */}
            <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight mb-2">
              Create your Avatar in 15 seconds
            </h1>

            {/* Subtitle with clickable upload footage */}
            <p className="text-xs sm:text-sm text-slate-400 leading-relaxed max-w-lg mb-6">
              Record your motion once, then reuse it across any look for this avatar. Or{" "}
              <button
                type="button"
                onClick={handleUploadClick}
                className="text-cyan-400 font-semibold underline underline-offset-2 hover:text-cyan-300 cursor-pointer transition-colors inline"
              >
                upload footage
              </button>
            </p>

            {/* Segmented Recording Method Tabs */}
            <div className="bg-[#0B1220] p-1 rounded-2xl flex items-center gap-1 border border-[#1B2940] mb-6 w-full max-w-md">
              <button
                type="button"
                onClick={() => setRecordMethod("webcam")}
                className={`flex-1 py-2 rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 transition-all cursor-pointer ${
                  recordMethod === "webcam"
                    ? "bg-[#101827] text-white shadow-xs font-bold ring-1 ring-cyan-500/30"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                <Video size={14} />
                <span>Record via webcam</span>
              </button>

              <button
                type="button"
                onClick={() => setRecordMethod("phone")}
                className={`flex-1 py-2 rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 transition-all cursor-pointer ${
                  recordMethod === "phone"
                    ? "bg-[#101827] text-white shadow-xs font-bold ring-1 ring-cyan-500/30"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                <Smartphone size={14} />
                <span>Record via phone</span>
              </button>
            </div>

            {/* ============================================================ */}
            {/* RECORDING / CAMERA PREVIEW CONTAINER */}
            {/* ============================================================ */}
            {uploadedVideo ? (
              /* State: Video Footage Selected */
              <div className="w-full h-80 bg-[#0B111E] rounded-2xl border border-cyan-500/50 ring-4 ring-cyan-500/10 flex flex-col items-center justify-center p-6 text-center animate-in zoom-in-95 duration-150">
                <div className="w-14 h-14 rounded-2xl bg-cyan-500/20 border border-cyan-500/30 text-cyan-400 flex items-center justify-center mb-3 shadow-xs">
                  <FileVideo size={28} />
                </div>
                <h3 className="text-base font-bold text-white mb-1">
                  {uploadedVideo.name}
                </h3>
                <p className="text-xs text-slate-400 mb-4">
                  Video file ready • {uploadedVideo.size}
                </p>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={handleUploadClick}
                    className="px-3.5 py-1.5 bg-[#101827] hover:bg-[#1B2940] border border-[#1B2940] text-slate-200 rounded-xl text-xs font-semibold transition-colors cursor-pointer"
                  >
                    Change video
                  </button>
                  <button
                    type="button"
                    onClick={handleRemoveVideo}
                    className="px-3.5 py-1.5 bg-rose-500/20 hover:bg-rose-500/30 text-rose-400 border border-rose-500/30 rounded-xl text-xs font-semibold transition-colors cursor-pointer"
                  >
                    Remove
                  </button>
                </div>
              </div>
            ) : recordMethod === "webcam" ? (
              /* State: Camera & Mic Blocked (Exact Reference Match) */
              <div className="w-full h-80 bg-[#0B111E] rounded-2xl border border-[#1B2940] flex flex-col items-center justify-center p-6 text-center relative overflow-hidden">
                {/* Warning Icon */}
                <div className="w-12 h-12 rounded-full bg-rose-500/20 text-rose-400 flex items-center justify-center mb-3 shadow-xs">
                  <AlertCircle size={24} />
                </div>

                {/* Blocked Header */}
                <h3 className="text-base font-bold text-white mb-1.5">
                  Camera & microphone are blocked
                </h3>

                {/* Warning Subtitle */}
                <p className="text-xs text-rose-400/90 font-medium max-w-sm mb-4 leading-relaxed">
                  Please enable camera & microphone access in your browser settings
                </p>

                {/* Get Help Button */}
                <button
                  type="button"
                  onClick={() => setIsHelpOpen(true)}
                  className="bg-[#101827] hover:bg-[#1B2940] border border-[#1B2940] hover:border-cyan-500/50 text-white font-semibold text-xs px-5 py-2 rounded-full shadow-xs transition-colors cursor-pointer mb-3"
                >
                  Get help
                </button>

                {/* Link to Record via phone */}
                <button
                  type="button"
                  onClick={() => setRecordMethod("phone")}
                  className="text-xs text-slate-400 hover:text-white font-medium transition-colors cursor-pointer"
                >
                  Or record via phone →
                </button>
              </div>
            ) : (
              /* State: Record via Phone */
              <div className="w-full h-80 bg-[#0B111E] rounded-2xl border border-[#1B2940] flex flex-col items-center justify-center p-6 text-center">
                <div className="w-16 h-16 bg-[#07090e] rounded-2xl shadow-xs border border-[#1B2940] flex items-center justify-center mb-3 text-cyan-400">
                  <QrCode size={34} />
                </div>
                <h3 className="text-base font-bold text-white mb-1">
                  Scan QR code with your phone
                </h3>
                <p className="text-xs text-slate-400 max-w-xs mb-3">
                  Open your mobile camera to record video footage directly from your device.
                </p>
                <div className="inline-flex items-center gap-1.5 text-xs text-cyan-400 font-semibold bg-cyan-500/20 border border-cyan-500/30 px-3 py-1.5 rounded-xl">
                  <span>Pairing link active</span>
                </div>
              </div>
            )}

            {/* Language Selector */}
            <div className="mt-5 flex items-center justify-center gap-2 text-xs text-slate-400">
              <span>We&apos;ll provide a script on screen in</span>
              <div ref={languageMenuRef} className="relative">
                <button
                  type="button"
                  onClick={() => setIsLanguageOpen(!isLanguageOpen)}
                  className="bg-[#0B1220] border border-[#1B2940] hover:border-slate-600 px-3 py-1 rounded-xl text-xs font-semibold text-slate-200 flex items-center gap-1.5 shadow-2xs transition-colors cursor-pointer"
                >
                  <span>{selectedLanguage}</span>
                  <ChevronDown size={12} className="text-slate-500" />
                </button>

                {/* Language Dropdown */}
                {isLanguageOpen && (
                  <div className="absolute left-0 bottom-full mb-1.5 w-36 bg-[#0B111E] border border-[#1B2940] rounded-2xl shadow-xl p-1 z-30 animate-in fade-in zoom-in-95 duration-100 max-h-48 overflow-y-auto">
                    {languages.map((lang) => (
                      <button
                        key={lang}
                        type="button"
                        onClick={() => {
                          setSelectedLanguage(lang);
                          setIsLanguageOpen(false);
                        }}
                        className={`w-full text-left px-2.5 py-1.5 rounded-xl text-xs flex items-center justify-between cursor-pointer ${
                          selectedLanguage === lang
                            ? "bg-cyan-500/20 text-cyan-300 font-bold"
                            : "text-slate-300 hover:bg-[#101827] hover:text-white"
                        }`}
                      >
                        <span>{lang}</span>
                        {selectedLanguage === lang && (
                          <Check size={12} className="text-cyan-400" />
                        )}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* ============================================================ */}
          {/* 3. FOOTER */}
          {/* ============================================================ */}
          <div className="w-full pt-4 border-t border-[#1B2940] flex items-center justify-between">
            {/* Left: Back */}
            <button
              type="button"
              onClick={onClose}
              className="text-slate-400 hover:text-white font-semibold text-xs flex items-center gap-1.5 px-3 py-2 rounded-xl hover:bg-[#101827] transition-colors cursor-pointer"
            >
              <ArrowLeft size={14} />
              <span>Back</span>
            </button>

            {/* Right: I'm ready (Disabled unless footage uploaded, matches reference) */}
            {uploadedVideo ? (
              <button
                type="button"
                onClick={() => {
                  if (onAvatarCreated) onAvatarCreated(uploadedVideo.name);
                  onClose();
                }}
                className="bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-bold text-xs px-6 py-2.5 rounded-full shadow-md transition-all cursor-pointer active:scale-95"
              >
                I&apos;m ready
              </button>
            ) : (
              <button
                type="button"
                disabled
                className="bg-[#101827] border border-[#1B2940] text-slate-600 font-semibold text-xs px-6 py-2.5 rounded-full cursor-not-allowed shadow-2xs"
                title="Please allow camera/mic access or upload footage to continue"
              >
                I&apos;m ready
              </button>
            )}
          </div>
        </div>

        {/* ============================================================ */}
        {/* GET HELP POPUP DIALOG */}
        {/* ============================================================ */}
        {isHelpOpen && (
          <div
            onClick={(e) => e.stopPropagation()}
            className="fixed inset-0 z-70 bg-black/75 backdrop-blur-md flex items-center justify-center p-4 animate-in fade-in duration-150"
          >
            <div className="w-full max-w-sm bg-[#0A0F1A] rounded-3xl p-6 shadow-2xl border border-[#1B2940] text-slate-100 animate-in zoom-in-95 duration-150">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <HelpCircle size={18} className="text-cyan-400" />
                  <h4 className="text-base font-bold text-white">
                    Enable Camera & Microphone
                  </h4>
                </div>
                <button
                  type="button"
                  onClick={() => setIsHelpOpen(false)}
                  className="text-slate-400 hover:text-white p-1 cursor-pointer"
                >
                  <X size={16} />
                </button>
              </div>

              <div className="space-y-3 text-xs text-slate-300 mb-6 leading-relaxed">
                <div className="flex items-start gap-2.5 bg-[#0B111E] border border-[#1B2940] p-2.5 rounded-xl">
                  <span className="w-5 h-5 rounded-full bg-[#101827] text-cyan-400 font-bold flex items-center justify-center text-[11px] flex-shrink-0">
                    1
                  </span>
                  <span>Click the tune/lock icon in your browser address bar.</span>
                </div>

                <div className="flex items-start gap-2.5 bg-[#0B111E] border border-[#1B2940] p-2.5 rounded-xl">
                  <span className="w-5 h-5 rounded-full bg-[#101827] text-cyan-400 font-bold flex items-center justify-center text-[11px] flex-shrink-0">
                    2
                  </span>
                  <span>Set <strong>Camera</strong> and <strong>Microphone</strong> to <strong>Allow</strong>.</span>
                </div>

                <div className="flex items-start gap-2.5 bg-[#0B111E] border border-[#1B2940] p-2.5 rounded-xl">
                  <span className="w-5 h-5 rounded-full bg-[#101827] text-cyan-400 font-bold flex items-center justify-center text-[11px] flex-shrink-0">
                    3
                  </span>
                  <span>Refresh the page and re-open the Create Avatar flow.</span>
                </div>
              </div>

              <div className="flex items-center justify-end">
                <button
                  type="button"
                  onClick={() => setIsHelpOpen(false)}
                  className="bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-bold text-xs px-5 py-2 rounded-xl transition-colors cursor-pointer shadow-xs"
                >
                  Got it
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
