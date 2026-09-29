"use client";

import React, { useState, useRef, useEffect, useCallback } from "react";
import {
  Mic,
  Sparkles,
  Download,
  Search,
  Globe,
  Filter,
  Play,
  Pause,
  MoreHorizontal,
  ChevronDown,
  Volume2,
  Check,
  X,
  Upload,
  CheckSquare,
  Square,
  RotateCcw,
  ArrowLeft,
} from "lucide-react";
import AskRhysWidget from "../dashboard/AskRhysWidget";
import CreateVoiceCloneModal from "./CreateVoiceCloneModal";
import DesignVoiceModal from "./DesignVoiceModal";
import ImportVoiceModal from "./ImportVoiceModal";
import { useAuth } from "@/context/AuthContext";
import { useTheme } from "@/context/ThemeContext";
import { api } from "@/lib/api";

export interface VoiceItem {
  id: string;
  name: string;
  description: string;
  useCases: string[];
  age: "Young adult" | "Middle-aged" | "Old";
  gender: "Female" | "Male";
  language: string;
  flag: string;
  country: string;
  type: "Public" | "Custom";
  provider?: string;
  previewAssetId?: string | null;
  previewUrl?: string | null;
}

const languagesList = [
  { code: "all", name: "All languages", flag: "🌐" },
  { code: "af", name: "Afrikaans (South Africa)", flag: "🇿🇦" },
  { code: "sq", name: "Albanian", flag: "🇦🇱" },
  { code: "am", name: "Amharic", flag: "🇪🇹" },
  { code: "ar", name: "Arabic", flag: "🇸🇦" },
  { code: "az", name: "Azerbaijani", flag: "🇦🇿" },
  { code: "bn", name: "Bengali (India / Bangladesh)", flag: "🇧🇩" },
  { code: "bg", name: "Bulgarian", flag: "🇧🇬" },
  { code: "ca", name: "Catalan", flag: "🇪🇸" },
  { code: "zh", name: "Chinese (Mandarin)", flag: "🇨🇳" },
  { code: "hr", name: "Croatian", flag: "🇭🇷" },
  { code: "cs", name: "Czech", flag: "🇨🇿" },
  { code: "da", name: "Danish", flag: "🇩🇰" },
  { code: "nl", name: "Dutch", flag: "🇳🇱" },
  { code: "en_us", name: "English (United States)", flag: "🇺🇸" },
  { code: "en_uk", name: "English (United Kingdom)", flag: "🇬🇧" },
  { code: "fil", name: "Filipino", flag: "🇵🇭" },
  { code: "fi", name: "Finnish", flag: "🇫🇮" },
  { code: "fr", name: "French", flag: "🇫🇷" },
  { code: "de", name: "German", flag: "🇩🇪" },
  { code: "el", name: "Greek", flag: "🇬🇷" },
  { code: "gu", name: "Gujarati (India)", flag: "🇮🇳" },
  { code: "he", name: "Hebrew (Israel)", flag: "🇮🇱" },
  { code: "hi", name: "Hindi (India)", flag: "🇮🇳" },
  { code: "hu", name: "Hungarian", flag: "🇭🇺" },
  { code: "id", name: "Indonesian", flag: "🇮🇩" },
  { code: "it", name: "Italian", flag: "🇮🇹" },
  { code: "ja", name: "Japanese", flag: "🇯🇵" },
  { code: "kn", name: "Kannada (India)", flag: "🇮🇳" },
  { code: "ko", name: "Korean", flag: "🇰🇷" },
  { code: "ms", name: "Malay", flag: "🇲🇾" },
  { code: "ml", name: "Malayalam (India)", flag: "🇮🇳" },
  { code: "mr", name: "Marathi (India)", flag: "🇮🇳" },
  { code: "ne", name: "Nepali (Nepal)", flag: "🇳🇵" },
  { code: "no", name: "Norwegian", flag: "🇳🇴" },
  { code: "fa", name: "Persian (Iran)", flag: "🇮🇷" },
  { code: "pl", name: "Polish", flag: "🇵🇱" },
  { code: "pt", name: "Portuguese (Brazil)", flag: "🇧🇷" },
  { code: "pa", name: "Punjabi (India)", flag: "🇮🇳" },
  { code: "ro", name: "Romanian", flag: "🇷🇴" },
  { code: "ru", name: "Russian", flag: "🇷🇺" },
  { code: "es", name: "Spanish (Spain / LatAm)", flag: "🇪🇸" },
  { code: "sv", name: "Swedish", flag: "🇸🇪" },
  { code: "ta", name: "Tamil (India)", flag: "🇮🇳" },
  { code: "te", name: "Telugu (India)", flag: "🇮🇳" },
  { code: "th", name: "Thai (Thailand)", flag: "🇹🇭" },
  { code: "tr", name: "Turkish", flag: "🇹🇷" },
  { code: "uk", name: "Ukrainian", flag: "🇺🇦" },
  { code: "ur", name: "Urdu (Pakistan)", flag: "🇵🇰" },
  { code: "vi", name: "Vietnamese", flag: "🇻🇳" },
];

export interface VoicesLibraryProps {
  onSelectVoice?: (voice: VoiceItem) => void;
  onBack?: () => void;
  selectedVoiceId?: string;
  selectedVoiceName?: string;
}

export default function VoicesLibrary({
  onSelectVoice,
  onBack,
  selectedVoiceId,
  selectedVoiceName,
}: VoicesLibraryProps) {
  const { theme } = useTheme();
  const isLight = theme === "light";
  const { currentWorkspace } = useAuth();
  const [backendVoices, setBackendVoices] = useState<VoiceItem[]>([]);
  const [isLoadingVoices, setIsLoadingVoices] = useState(true);
  const [voiceError, setVoiceError] = useState<string | null>(null);

  const [activeTab, setActiveTab] = useState<"my_voices" | "heygen_library">("heygen_library");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedGender, setSelectedGender] = useState<"All" | "Female" | "Male">("All");
  const [selectedLanguage, setSelectedLanguage] = useState<string>("All languages");
  const [languageSearch, setLanguageSearch] = useState("");
  const [playingVoiceId, setPlayingVoiceId] = useState<string | null>(null);
  const [visibleCount, setVisibleCount] = useState(14);

  // Filters Dropdown State
  const [isFilterDropdownOpen, setIsFilterDropdownOpen] = useState(false);
  const [isLangDropdownOpen, setIsLangDropdownOpen] = useState(false);
  const [isGenderDropdownOpen, setIsGenderDropdownOpen] = useState(false);

  // Selected Filters
  const [selectedUseCases, setSelectedUseCases] = useState<string[]>([]);
  const [selectedAges, setSelectedAges] = useState<string[]>([]);

  // Modals state
  const [isCloneModalOpen, setIsCloneModalOpen] = useState(false);
  const [isDesignModalOpen, setIsDesignModalOpen] = useState(false);
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);

  // Outside click refs
  const filterDropdownRef = useRef<HTMLDivElement>(null);
  const langDropdownRef = useRef<HTMLDivElement>(null);
  const genderDropdownRef = useRef<HTMLDivElement>(null);

  const fetchVoices = useCallback(async () => {
    setIsLoadingVoices(true);
    setVoiceError(null);
    try {
      const resp = await api.creative.listVoices({}, currentWorkspace?.id);
      const mapped: VoiceItem[] = (resp || []).map((v: any) => ({
        id: v.id,
        name: v.name,
        description:
          v.description ||
          `${(v.language || "en").toUpperCase()} • ${v.gender || "neutral"} • ${v.voice_type || "preset"}`,
        useCases: v.provider_metadata?.use_cases || [
          "Informative and educational",
          "Conversational",
        ],
        age: (v.provider_metadata?.age as any) || "Young adult",
        gender: v.gender?.toLowerCase() === "male" ? "Male" : "Female",
        language:
          v.provider_metadata?.language_name ||
          (v.language === "es"
            ? "Spanish (Spain / LatAm)"
            : v.language === "hi"
            ? "Hindi (India)"
            : "English (United States)"),
        flag: v.provider_metadata?.flag || "🌐",
        country: v.provider_metadata?.country || "Global",
        type: v.voice_type === "custom" || v.voice_type === "cloned" ? "Custom" : "Public",
        provider: v.provider,
        previewAssetId: v.preview_asset_id,
        previewUrl: v.preview_url,
      }));
      setBackendVoices(mapped);
    } catch (err: any) {
      setVoiceError(err?.message || "Failed to load voices from backend.");
    } finally {
      setIsLoadingVoices(false);
    }
  }, [currentWorkspace?.id]);

  useEffect(() => {
    fetchVoices();
  }, [fetchVoices]);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (filterDropdownRef.current && !filterDropdownRef.current.contains(event.target as Node)) {
        setIsFilterDropdownOpen(false);
      }
      if (langDropdownRef.current && !langDropdownRef.current.contains(event.target as Node)) {
        setIsLangDropdownOpen(false);
      }
      if (genderDropdownRef.current && !genderDropdownRef.current.contains(event.target as Node)) {
        setIsGenderDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const toggleUseCase = (useCase: string) => {
    setSelectedUseCases((prev) =>
      prev.includes(useCase) ? prev.filter((u) => u !== useCase) : [...prev, useCase]
    );
  };

  const toggleAge = (age: string) => {
    setSelectedAges((prev) =>
      prev.includes(age) ? prev.filter((a) => a !== age) : [...prev, age]
    );
  };

  const clearAllFilters = () => {
    setSelectedUseCases([]);
    setSelectedAges([]);
  };

  const activeFilterCount = selectedUseCases.length + selectedAges.length;

  // Filtered Voices Logic against real backend data (zero mock fallback)
  const filteredVoices = backendVoices.filter((voice) => {
    if (activeTab === "my_voices" && voice.type !== "Custom") {
      return false;
    }
    if (activeTab === "heygen_library" && voice.type !== "Public") {
      return false;
    }

    const matchesSearch =
      voice.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      voice.description.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesGender = selectedGender === "All" || voice.gender === selectedGender;

    const matchesLang =
      selectedLanguage === "All languages" ||
      voice.language.toLowerCase().includes(selectedLanguage.toLowerCase()) ||
      selectedLanguage.toLowerCase().includes(voice.language.toLowerCase()) ||
      voice.language === "All languages";

    const matchesUseCase =
      selectedUseCases.length === 0 ||
      voice.useCases.some((u) => selectedUseCases.includes(u));

    const matchesAge =
      selectedAges.length === 0 || selectedAges.includes(voice.age);

    return matchesSearch && matchesGender && matchesLang && matchesUseCase && matchesAge;
  });

  const filteredLanguages = languagesList.filter((l) =>
    l.name.toLowerCase().includes(languageSearch.toLowerCase())
  );

  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [playbackNotice, setPlaybackNotice] = useState<{ voiceId: string; message: string } | null>(null);

  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current.src = "";
        audioRef.current = null;
      }
    };
  }, []);

  const handlePlayVoice = async (voice: VoiceItem) => {
    setPlaybackNotice(null);

    // 1. If currently playing this voice, stop it
    if (playingVoiceId === voice.id) {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current.currentTime = 0;
      }
      setPlayingVoiceId(null);
      return;
    }

    // 2. If playing another voice, stop that one first
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      setPlayingVoiceId(null);
    }

    // 3. For voices without preview audio (mock providers):
    if (!voice.previewUrl && !voice.previewAssetId) {
      setPlaybackNotice({
        voiceId: voice.id,
        message: "Audio preview is only available for neural voices (Piper Lessac & Davefx).",
      });
      return;
    }

    try {
      let audioUrl = voice.previewUrl;
      if (!audioUrl && voice.id) {
        const previewData = await api.creative.getVoicePreview(voice.id, currentWorkspace?.id);
        audioUrl = previewData.preview_url;
      }

      if (!audioUrl) {
        setPlaybackNotice({
          voiceId: voice.id,
          message: "Preview audio URL could not be resolved.",
        });
        return;
      }

      const audio = new Audio(audioUrl);
      audioRef.current = audio;

      audio.onplay = () => {
        setPlayingVoiceId(voice.id);
      };

      audio.onended = () => {
        setPlayingVoiceId(null);
      };

      audio.onerror = (err) => {
        console.error("Audio playback error:", err);
        setPlayingVoiceId(null);
        setPlaybackNotice({
          voiceId: voice.id,
          message: "Unable to play audio sample from storage.",
        });
      };

      await audio.play();
    } catch (err: any) {
      console.error("Audio play failed:", err);
      setPlayingVoiceId(null);
      setPlaybackNotice({
        voiceId: voice.id,
        message: err?.message || "Audio playback could not be started.",
      });
    }
  };

  return (
    <div className={`flex-1 h-screen overflow-y-auto flex flex-col font-sans select-none ${isLight ? "bg-slate-50 text-slate-900" : "bg-[#07090e] text-slate-100"}`}>
      {/* 1. TOP ACTION BAR */}
      <div className={`w-full px-8 pt-6 pb-4 flex items-center justify-between border-b z-30 ${isLight ? "border-slate-200" : "border-[#141b2c]"}`}>
        <div className="flex items-center gap-3">
          {onBack && (
            <button
              onClick={onBack}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-full text-xs font-semibold transition-all shadow-sm cursor-pointer mr-1 border ${
                isLight
                  ? "bg-white hover:bg-slate-100 border-slate-200 text-slate-700"
                  : "bg-[#121828] hover:bg-[#19233b] border-[#233152] hover:border-blue-500/50 text-slate-200"
              }`}
              title="Back"
            >
              <ArrowLeft size={15} />
              <span>Back</span>
            </button>
          )}

          {/* Clone your voice button */}
          <button
            onClick={() => setIsCloneModalOpen(true)}
            className={`flex items-center gap-2 px-4 py-2 rounded-full text-xs font-semibold transition-all shadow-sm cursor-pointer border ${
              isLight
                ? "bg-white hover:bg-slate-100 border-slate-200 text-slate-800"
                : "bg-[#121828] hover:bg-[#19233b] border-[#233152] hover:border-blue-500/50 text-slate-200"
            }`}
          >
            <Mic size={15} className="text-blue-500" />
            <span>Clone your voice</span>
          </button>

          {/* Design a voice button */}
          <button
            onClick={() => setIsDesignModalOpen(true)}
            className={`flex items-center gap-2 px-4 py-2 rounded-full text-xs font-semibold transition-all shadow-sm cursor-pointer border ${
              isLight
                ? "bg-white hover:bg-slate-100 border-slate-200 text-slate-800"
                : "bg-[#121828] hover:bg-[#19233b] border-[#233152] hover:border-purple-500/50 text-slate-200"
            }`}
          >
            <Sparkles size={15} className="text-purple-500" />
            <span>Design a voice</span>
          </button>

          {/* Import from 3rd party button */}
          <button
            onClick={() => setIsImportModalOpen(true)}
            className={`flex items-center gap-2 px-4 py-2 rounded-full text-xs font-semibold transition-all shadow-sm cursor-pointer border ${
              isLight
                ? "bg-white hover:bg-slate-100 border-slate-200 text-slate-800"
                : "bg-[#121828] hover:bg-[#19233b] border-[#233152] hover:border-emerald-500/50 text-slate-200"
            }`}
          >
            <Download size={15} className="text-emerald-500" />
            <span>Import from 3rd party</span>
          </button>
        </div>

        {/* Ask Rhys Copilot Widget */}
        <AskRhysWidget />
      </div>

      {/* 2. TABS & FILTER TOOLBAR */}
      <div className="px-8 pt-6 max-w-7xl w-full mx-auto">
        {/* Tab Headers */}
        <div className={`flex items-center gap-8 border-b pb-3 text-sm font-semibold ${isLight ? "border-slate-200" : "border-[#172036]"}`}>
          <button
            onClick={() => setActiveTab("my_voices")}
            className={`transition-colors relative pb-3 cursor-pointer ${
              activeTab === "my_voices"
                ? (isLight ? "text-slate-900 font-extrabold" : "text-white")
                : (isLight ? "text-slate-500 hover:text-slate-800" : "text-slate-500 hover:text-slate-300")
            }`}
          >
            My voices
            {activeTab === "my_voices" && (
              <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-500 rounded-full"></span>
            )}
          </button>

          <button
            onClick={() => setActiveTab("heygen_library")}
            className={`transition-colors relative pb-3 cursor-pointer ${
              activeTab === "heygen_library"
                ? (isLight ? "text-slate-900 font-extrabold" : "text-white")
                : (isLight ? "text-slate-500 hover:text-slate-800" : "text-slate-500 hover:text-slate-300")
            }`}
          >
            HeyGen library
            {activeTab === "heygen_library" && (
              <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-500 rounded-full shadow-sm shadow-blue-500"></span>
            )}
          </button>
        </div>

        {/* Filter Controls Row */}
        <div className="flex flex-wrap items-center justify-between gap-3 mt-5 mb-4 relative z-20">
          {/* Search Box */}
          <div className="relative flex-1 min-w-[260px] max-w-md">
            <Search size={15} className="absolute left-3.5 top-3 text-slate-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search voices..."
              className={`w-full border rounded-xl pl-10 pr-4 py-2 text-xs focus:outline-none transition-colors ${
                isLight
                  ? "bg-white border-slate-200 text-slate-900 placeholder-slate-400 focus:border-blue-500"
                  : "bg-[#0d1222] border-[#1e2a44] text-white placeholder-slate-500 focus:border-blue-500"
              }`}
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery("")}
                className={`absolute right-3 top-2.5 ${isLight ? "text-slate-400 hover:text-slate-700" : "text-slate-500 hover:text-white"}`}
              >
                <X size={14} />
              </button>
            )}
          </div>

          {/* Filter Dropdowns */}
          <div className="flex items-center gap-2.5">
            {/* 1. LANGUAGE DROPDOWN (Matches Screenshot 2) */}
            <div className="relative" ref={langDropdownRef}>
              <button
                onClick={() => {
                  setIsLangDropdownOpen(!isLangDropdownOpen);
                  setIsFilterDropdownOpen(false);
                  setIsGenderDropdownOpen(false);
                }}
                className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs transition-colors border cursor-pointer ${
                  selectedLanguage !== "All languages"
                    ? isLight
                      ? "bg-blue-50 text-blue-700 border-blue-200 font-semibold"
                      : "bg-[#18233c] text-blue-300 border-blue-500/60 font-semibold"
                    : isLight
                    ? "bg-white border-slate-200 text-slate-700 hover:text-slate-900 hover:border-slate-300"
                    : "bg-[#0d1222] border-[#1e2a44] text-slate-300 hover:text-white hover:border-[#2e3e63]"
                }`}
              >
                <Globe size={13} className="text-blue-500" />
                <span className="max-w-[130px] truncate">{selectedLanguage}</span>
                <ChevronDown size={13} className="text-slate-400" />
              </button>

              {/* Language Dropdown Menu */}
              {isLangDropdownOpen && (
                <div className={`absolute right-0 mt-2 w-80 max-h-96 border rounded-2xl shadow-2xl p-2 z-50 flex flex-col animate-in fade-in zoom-in-95 duration-150 backdrop-blur-xl ${
                  isLight ? "bg-white/95 border-slate-200 shadow-xl" : "bg-[#0c111e] border-[#222f4d]"
                }`}>
                  {/* Search inside language dropdown */}
                  <div className="relative p-1 mb-1">
                    <Search size={14} className="absolute left-3.5 top-3.5 text-slate-400" />
                    <input
                      type="text"
                      value={languageSearch}
                      onChange={(e) => setLanguageSearch(e.target.value)}
                      placeholder="Search language..."
                      className={`w-full rounded-xl pl-9 pr-3 py-1.5 text-xs focus:outline-none border ${
                        isLight ? "bg-slate-50 border-slate-200 text-slate-900 placeholder-slate-400 focus:border-blue-500" : "bg-[#111728] border-[#1e2a44] text-white placeholder-slate-500 focus:border-blue-500"
                      }`}
                    />
                  </div>

                  {/* Languages list */}
                  <div className="overflow-y-auto max-h-80 space-y-0.5 pr-1">
                    {filteredLanguages.map((lang) => {
                      const isSelected = selectedLanguage === lang.name;
                      return (
                        <button
                          key={lang.code}
                          onClick={() => {
                            setSelectedLanguage(lang.name);
                            setIsLangDropdownOpen(false);
                            setLanguageSearch("");
                          }}
                          className={`w-full flex items-center justify-between px-3 py-2 rounded-xl text-xs transition-colors cursor-pointer ${
                            isSelected
                              ? isLight ? "bg-blue-50 text-blue-600 font-semibold" : "bg-[#18233d] text-blue-400 font-semibold"
                              : isLight ? "text-slate-700 hover:bg-slate-100 hover:text-slate-900" : "text-slate-300 hover:bg-[#131a2c] hover:text-white"
                          }`}
                        >
                          <div className="flex items-center gap-2.5 truncate">
                            <span className="text-base">{lang.flag}</span>
                            <span className="truncate">{lang.name}</span>
                          </div>
                          {isSelected && <Check size={14} className="text-blue-500 flex-shrink-0" />}
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>

            {/* 2. GENDER DROPDOWN */}
            <div className="relative" ref={genderDropdownRef}>
              <button
                onClick={() => {
                  setIsGenderDropdownOpen(!isGenderDropdownOpen);
                  setIsFilterDropdownOpen(false);
                  setIsLangDropdownOpen(false);
                }}
                className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs transition-colors border cursor-pointer ${
                  selectedGender !== "All"
                    ? isLight
                      ? "bg-blue-50 text-blue-700 border-blue-200 font-semibold"
                      : "bg-[#18233c] text-blue-300 border-blue-500/60 font-semibold"
                    : isLight
                    ? "bg-white border-slate-200 text-slate-700 hover:text-slate-900 hover:border-slate-300"
                    : "bg-[#0d1222] border-[#1e2a44] text-slate-300 hover:text-white hover:border-[#2e3e63]"
                }`}
              >
                <span>{selectedGender === "All" ? "All genders" : selectedGender}</span>
                <ChevronDown size={13} className="text-slate-400" />
              </button>

              {isGenderDropdownOpen && (
                <div className={`absolute right-0 mt-2 w-44 border rounded-2xl shadow-2xl p-1.5 z-50 animate-in fade-in duration-150 backdrop-blur-xl ${
                  isLight ? "bg-white/95 border-slate-200 shadow-xl" : "bg-[#0c111e] border-[#222f4d]"
                }`}>
                  {["All", "Female", "Male"].map((g) => (
                    <button
                      key={g}
                      onClick={() => {
                        setSelectedGender(g as any);
                        setIsGenderDropdownOpen(false);
                      }}
                      className={`w-full text-left px-3 py-2 rounded-xl text-xs transition-colors flex items-center justify-between ${
                        selectedGender === g
                          ? isLight ? "bg-blue-50 text-blue-700 font-semibold" : "bg-blue-600/30 text-blue-300 font-semibold"
                          : isLight ? "text-slate-700 hover:bg-slate-100 hover:text-slate-900" : "text-slate-300 hover:bg-[#141b2c] hover:text-white"
                      }`}
                    >
                      <span>{g === "All" ? "All genders" : g}</span>
                      {selectedGender === g && <Check size={13} className="text-blue-500" />}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* 3. FILTERS DROPDOWN (Matches Screenshot 1) */}
            <div className="relative" ref={filterDropdownRef}>
              <button
                onClick={() => {
                  setIsFilterDropdownOpen(!isFilterDropdownOpen);
                  setIsLangDropdownOpen(false);
                  setIsGenderDropdownOpen(false);
                }}
                className={`flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs border transition-colors cursor-pointer ${
                  activeFilterCount > 0
                    ? isLight
                      ? "bg-blue-50 text-blue-700 border-blue-200 font-semibold"
                      : "bg-[#18233c] text-blue-300 border-blue-500/60 font-semibold"
                    : isLight
                    ? "bg-white border-slate-200 text-slate-700 hover:text-slate-900 hover:border-slate-300"
                    : "bg-[#0d1222] border-[#1e2a44] text-slate-300 hover:text-white hover:border-[#2e3e63]"
                }`}
              >
                <Filter size={13} className={activeFilterCount > 0 ? "text-blue-500" : "text-slate-400"} />
                <span>{activeFilterCount} Filters</span>
                <ChevronDown size={13} className="text-slate-400" />
              </button>

              {/* Filters Panel Popover */}
              {isFilterDropdownOpen && (
                <div className={`absolute right-0 mt-2 w-[420px] border rounded-2xl shadow-2xl p-5 z-50 animate-in fade-in zoom-in-95 duration-150 backdrop-blur-xl ${
                  isLight ? "bg-white/95 border-slate-200 shadow-xl" : "bg-[#0c111e] border-[#222f4d]"
                }`}>
                  {/* Header */}
                  <div className={`flex items-center justify-between pb-3 border-b mb-4 ${isLight ? "border-slate-200" : "border-[#1b2742]"}`}>
                    <h3 className={`text-sm font-bold ${isLight ? "text-slate-900" : "text-white"}`}>Filters</h3>
                    {activeFilterCount > 0 && (
                      <button
                        onClick={clearAllFilters}
                        className="text-[11px] text-blue-500 hover:text-blue-600 flex items-center gap-1 font-semibold"
                      >
                        <RotateCcw size={11} /> Reset
                      </button>
                    )}
                  </div>

                  {/* Section 1: Use cases */}
                  <div className="mb-5">
                    <h4 className={`text-xs font-semibold mb-2.5 ${isLight ? "text-slate-700" : "text-slate-300"}`}>Use cases</h4>
                    <div className="grid grid-cols-2 gap-y-2.5 gap-x-4 text-xs">
                      {[
                        "Conversational",
                        "Ads and Social",
                        "Informative and educational",
                        "Narrative & Story",
                      ].map((useCase) => {
                        const isChecked = selectedUseCases.includes(useCase);
                        return (
                          <div
                            key={useCase}
                            onClick={() => toggleUseCase(useCase)}
                            className={`flex items-center gap-2.5 cursor-pointer group ${isLight ? "text-slate-700 hover:text-slate-900" : "text-slate-300 hover:text-white"}`}
                          >
                            <div
                              className={`w-4 h-4 rounded flex items-center justify-center transition-colors border ${
                                isChecked
                                  ? "bg-blue-600 border-blue-500 text-white"
                                  : isLight
                                  ? "bg-white border-slate-300 group-hover:border-blue-400"
                                  : "bg-[#111728] border-[#22304d] group-hover:border-slate-500"
                              }`}
                            >
                              {isChecked && <Check size={11} strokeWidth={3} />}
                            </div>
                            <span className="text-xs">{useCase}</span>
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* Section 2: Voice age */}
                  <div className="mb-3">
                    <h4 className={`text-xs font-semibold mb-2.5 ${isLight ? "text-slate-700" : "text-slate-300"}`}>Voice age</h4>
                    <div className="grid grid-cols-2 gap-y-2.5 gap-x-4 text-xs">
                      {["Young adult", "Middle-aged", "Old"].map((age) => {
                        const isChecked = selectedAges.includes(age);
                        return (
                          <div
                            key={age}
                            onClick={() => toggleAge(age)}
                            className={`flex items-center gap-2.5 cursor-pointer group ${isLight ? "text-slate-700 hover:text-slate-900" : "text-slate-300 hover:text-white"}`}
                          >
                            <div
                              className={`w-4 h-4 rounded flex items-center justify-center transition-colors border ${
                                isChecked
                                  ? "bg-blue-600 border-blue-500 text-white"
                                  : isLight
                                  ? "bg-white border-slate-300 group-hover:border-blue-400"
                                  : "bg-[#111728] border-[#22304d] group-hover:border-slate-500"
                              }`}
                            >
                              {isChecked && <Check size={11} strokeWidth={3} />}
                            </div>
                            <span className="text-xs">{age}</span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* 3. VOICES LIST TABLE */}
        <div className="space-y-1 mt-2 pb-16">
          {isLoadingVoices ? (
            <div className={`p-16 text-center rounded-2xl flex flex-col items-center justify-center border ${
              isLight ? "bg-white border-slate-200" : "bg-[#090d17] border-[#172035]"
            }`}>
              <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mb-3"></div>
              <p className={`text-xs ${isLight ? "text-slate-500" : "text-slate-400"}`}>Loading voices from backend...</p>
            </div>
          ) : voiceError ? (
            <div className={`p-12 text-center rounded-2xl border ${
              isLight ? "bg-rose-50/50 border-rose-200" : "bg-[#090d17] border-red-500/30"
            }`}>
              <p className="text-sm text-red-500 font-semibold mb-1">Failed to load voices</p>
              <p className="text-xs text-slate-500 mb-4">{voiceError}</p>
              <button
                onClick={fetchVoices}
                className="px-4 py-2 bg-blue-600 text-white rounded-xl text-xs font-semibold hover:bg-blue-500 transition-colors"
              >
                Retry
              </button>
            </div>
          ) : filteredVoices.length === 0 ? (
            <div className={`p-12 text-center rounded-2xl border ${
              isLight ? "bg-white border-slate-200" : "bg-[#090d17] border-[#172035]"
            }`}>
              <p className={`text-sm font-semibold mb-1 ${isLight ? "text-slate-700" : "text-slate-300"}`}>No voices found</p>
              <p className="text-xs text-slate-500 mb-3">
                {activeTab === "my_voices"
                  ? "No custom voices cloned yet. Use 'Clone a voice' or 'Design a voice' to create one."
                  : "Try adjusting your filters or search query"}
              </p>
              <button
                onClick={() => {
                  setSearchQuery("");
                  setSelectedGender("All");
                  setSelectedLanguage("All languages");
                  clearAllFilters();
                }}
                className={`px-3.5 py-1.5 border rounded-xl text-xs font-semibold ${
                  isLight ? "bg-blue-50 text-blue-600 border-blue-200 hover:bg-blue-100" : "bg-blue-600/30 text-blue-300 border-blue-500/40"
                }`}
              >
                Clear Filters
              </button>
            </div>
          ) : (
            filteredVoices.slice(0, visibleCount).map((voice) => {
              const isPlaying = playingVoiceId === voice.id;

              return (
                <div
                  key={voice.id}
                  className={`flex items-center justify-between p-3 rounded-xl border transition-all duration-150 group ${
                    isPlaying
                      ? isLight
                        ? "bg-blue-50/80 border-blue-500 shadow-md shadow-blue-500/10"
                        : "bg-[#141c30] border-blue-500/60 shadow-md shadow-blue-500/10"
                      : isLight
                      ? "bg-white border-slate-200/80 hover:bg-slate-50 hover:border-slate-300 shadow-xs"
                      : "bg-[#090d17] border-[#151c2d] hover:bg-[#0f1525] hover:border-[#222f4c]"
                  }`}
                >
                  {/* Left: Play Button & Voice Details */}
                  <div className="flex items-center gap-3.5 min-w-0 flex-1">
                    <button
                      onClick={() => handlePlayVoice(voice)}
                      className={`w-8 h-8 rounded-full flex items-center justify-center transition-all flex-shrink-0 cursor-pointer ${
                        isPlaying
                          ? "bg-blue-600 text-white ring-2 ring-blue-400/50 shadow-md animate-pulse"
                          : isLight
                          ? "bg-slate-100 text-slate-700 hover:bg-blue-600 hover:text-white group-hover:bg-slate-200"
                          : "bg-[#151c2d] text-slate-300 hover:bg-blue-600 hover:text-white group-hover:bg-[#1f2a43]"
                      }`}
                    >
                      {isPlaying ? (
                        <Pause size={13} />
                      ) : (
                        <Play size={13} className="ml-0.5 fill-current" />
                      )}
                    </button>

                    {/* Voice Meta */}
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <h4 className={`text-xs font-semibold truncate transition-colors ${
                          isLight ? "text-slate-900 group-hover:text-blue-600" : "text-white group-hover:text-blue-300"
                        }`}>
                          {voice.name}
                        </h4>
                        {isPlaying && (
                          <span className="flex items-center gap-1 text-[10px] text-blue-500 font-mono">
                            <Volume2 size={12} className="animate-bounce" /> Playing sample...
                          </span>
                        )}
                        {playbackNotice && playbackNotice.voiceId === voice.id && (
                          <span className="text-[10px] text-amber-500 font-sans truncate">
                            ⚠️ {playbackNotice.message}
                          </span>
                        )}
                      </div>
                      <p className={`text-[11px] truncate mt-0.5 ${isLight ? "text-slate-500" : "text-slate-400"}`}>
                        {voice.description}
                      </p>
                    </div>
                  </div>

                  {/* Right: Badges, Flag & Action Menu */}
                  <div className="flex items-center gap-3 ml-4 flex-shrink-0">
                    <span className="text-[10px] font-semibold text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-200 dark:border-emerald-500/20 px-2 py-0.5 rounded-md">
                      {voice.type}
                    </span>

                    <span className="text-base" title={voice.country}>
                      {voice.flag}
                    </span>

                    {onSelectVoice ? (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectVoice(voice);
                        }}
                        className={`text-[11px] font-semibold px-3 py-1 rounded-lg transition-all shadow-sm cursor-pointer ${
                          selectedVoiceId === voice.id || selectedVoiceName === voice.name
                            ? "bg-blue-600 text-white font-bold"
                            : "bg-blue-600/80 hover:bg-blue-600 text-white"
                        }`}
                      >
                        {selectedVoiceId === voice.id || selectedVoiceName === voice.name
                          ? "Selected"
                          : "Use"}
                      </button>
                    ) : (
                      <button
                        onClick={() => {
                          alert(`Voice "${voice.name}" selected for your video project!`);
                        }}
                        className="opacity-0 group-hover:opacity-100 text-[11px] font-semibold bg-blue-600 hover:bg-blue-500 text-white px-2.5 py-1 rounded-lg transition-all shadow-sm cursor-pointer"
                      >
                        Use
                      </button>
                    )}

                    <button className={`p-1.5 rounded-lg transition-colors cursor-pointer ${isLight ? "text-slate-400 hover:text-slate-700 hover:bg-slate-100" : "text-slate-500 hover:text-slate-200 hover:bg-[#18233a]"}`}>
                      <MoreHorizontal size={16} />
                    </button>
                  </div>
                </div>
              );
            })
          )}

          {/* See More Expandable Button */}
          {visibleCount < filteredVoices.length && (
            <div className="text-center pt-5">
              <button
                onClick={() => setVisibleCount((prev) => prev + 10)}
                className={`inline-flex items-center gap-1.5 text-xs font-semibold px-4 py-2 rounded-xl border transition-all cursor-pointer ${
                  isLight
                    ? "text-slate-600 hover:text-slate-900 bg-white border-slate-200 hover:bg-slate-50"
                    : "text-slate-400 hover:text-white bg-[#0e1423] border-[#1b253c] hover:border-[#2a3a5f]"
                }`}
              >
                <span>See More</span>
                <ChevronDown size={14} />
              </button>
            </div>
          )}
        </div>
      </div>

      {/* 4. MODALS (Create Voice Clone, Design Voice, Import) */}
      <CreateVoiceCloneModal
        isOpen={isCloneModalOpen}
        onClose={() => setIsCloneModalOpen(false)}
        onSuccess={(name) => {
          // Add newly created custom voice to state
        }}
      />

      <DesignVoiceModal
        isOpen={isDesignModalOpen}
        onClose={() => setIsDesignModalOpen(false)}
        onSuccess={(name) => {
          // Add newly generated voice
        }}
      />

      <ImportVoiceModal
        isOpen={isImportModalOpen}
        onClose={() => setIsImportModalOpen(false)}
      />
    </div>
  );
}
