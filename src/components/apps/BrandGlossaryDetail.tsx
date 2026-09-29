"use client";

import React, { useState, useRef, useEffect } from "react";
import {
  ArrowLeft,
  ArrowRight,
  Search,
  UploadCloud,
  Plus,
  Trash2,
  Check,
  X,
  Play,
  FileText,
} from "lucide-react";
import AskRhysWidget from "../dashboard/AskRhysWidget";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { useTheme } from "@/context/ThemeContext";

export interface GlossaryEntry {
  id: string;
  originalWord: string;
  targetOrPronunciation: string;
}

export interface ForceTranslateRule {
  id: string;
  sourceWord: string;
  targetWord: string;
}

export interface DontTranslateRule {
  id: string;
  term: string;
}

interface BrandGlossaryDetailProps {
  glossaryId?: string;
  glossaryName?: string;
  initialPronunciations?: GlossaryEntry[];
  initialForceRules?: ForceTranslateRule[];
  initialDontTranslateRules?: DontTranslateRule[];
  onUpdatePronunciations?: (pronunciations: GlossaryEntry[]) => void;
  onUpdateForceRules?: (rules: ForceTranslateRule[]) => void;
  onUpdateDontTranslateRules?: (rules: DontTranslateRule[]) => void;
  onBack?: () => void;
  onOpenStudio?: () => void;
}

export default function BrandGlossaryDetail({
  glossaryId = "glossary_default",
  glossaryName = "Brand Glossary",
  initialPronunciations = [],
  initialForceRules = [],
  initialDontTranslateRules = [],
  onUpdatePronunciations,
  onUpdateForceRules,
  onUpdateDontTranslateRules,
  onBack,
  onOpenStudio,
}: BrandGlossaryDetailProps) {
  const { currentWorkspace } = useAuth();
  const { theme } = useTheme();
  const isLight = theme === "light";
  const [activeTab, setActiveTab] = useState<"pronunciations" | "translations">(
    "pronunciations"
  );
  const [searchQuery, setSearchQuery] = useState("");

  // Pronunciations state
  const [pronunciations, setPronunciations] = useState<GlossaryEntry[]>(
    () => initialPronunciations
  );
  const [isAddingPronunciation, setIsAddingPronunciation] = useState(false);
  const [newOriginalWord, setNewOriginalWord] = useState("");
  const [newPronunciation, setNewPronunciation] = useState("");

  // Translations: Section 1 (Force Translate)
  const [forceRules, setForceRules] = useState<ForceTranslateRule[]>(
    () => initialForceRules
  );
  const [isAddingForceRule, setIsAddingForceRule] = useState(false);
  const [newForceSource, setNewForceSource] = useState("");
  const [newForceTarget, setNewForceTarget] = useState("");

  // Translations: Section 2 (Don't Translate)
  const [dontRules, setDontRules] = useState<DontTranslateRule[]>(
    () => initialDontTranslateRules
  );
  const [isAddingDontRule, setIsAddingDontRule] = useState(false);
  const [newDontTerm, setNewDontTerm] = useState("");

  // Refs for CSV and Auto-focus
  const pronCsvRef = useRef<HTMLInputElement>(null);
  const forceCsvRef = useRef<HTMLInputElement>(null);
  const dontCsvRef = useRef<HTMLInputElement>(null);
  const originalWordInputRef = useRef<HTMLInputElement>(null);
  const forceSourceInputRef = useRef<HTMLInputElement>(null);
  const dontTermInputRef = useRef<HTMLInputElement>(null);

  // Sync state if initial props change, or fetch from backend if glossaryId is a UUID
  useEffect(() => {
    if (!glossaryId || !/^[0-9a-fA-F-]{36}$/.test(glossaryId)) {
      setPronunciations(initialPronunciations);
      setForceRules(initialForceRules);
      setDontRules(initialDontTranslateRules);
      return;
    }

    api.brandGlossaries.listRules(glossaryId, currentWorkspace?.id)
      .then((rules) => {
        const prons: GlossaryEntry[] = [];
        const forces: ForceTranslateRule[] = [];
        const donts: DontTranslateRule[] = [];
        for (const r of rules) {
          const term = r.term || r.source_term || "";
          if (r.rule_type === "pronunciation") {
            prons.push({
              id: r.id,
              originalWord: term,
              targetOrPronunciation: r.phonetic_spelling || r.replacement || "",
            });
          } else if (r.rule_type === "do_not_translate") {
            donts.push({
              id: r.id,
              term: term,
            });
          } else {
            forces.push({
              id: r.id,
              sourceWord: term,
              targetWord: r.replacement || "",
            });
          }
        }
        setPronunciations(prons);
        setForceRules(forces);
        setDontRules(donts);
      })
      .catch((err) => {
        console.error("Failed to load glossary rules:", err);
      });
  }, [glossaryId, currentWorkspace?.id, initialPronunciations, initialForceRules, initialDontTranslateRules]);

  useEffect(() => {
    setForceRules(initialForceRules);
  }, [initialForceRules]);

  useEffect(() => {
    setDontRules(initialDontTranslateRules);
  }, [initialDontTranslateRules]);

  // Focus inputs automatically
  useEffect(() => {
    if (isAddingPronunciation) {
      const timer = setTimeout(() => {
        originalWordInputRef.current?.focus();
      }, 50);
      return () => clearTimeout(timer);
    }
  }, [isAddingPronunciation]);

  useEffect(() => {
    if (isAddingForceRule) {
      const timer = setTimeout(() => {
        forceSourceInputRef.current?.focus();
      }, 50);
      return () => clearTimeout(timer);
    }
  }, [isAddingForceRule]);

  useEffect(() => {
    if (isAddingDontRule) {
      const timer = setTimeout(() => {
        dontTermInputRef.current?.focus();
      }, 50);
      return () => clearTimeout(timer);
    }
  }, [isAddingDontRule]);

  // Validations
  const isPronValid =
    newOriginalWord.trim().length > 0 && newPronunciation.trim().length > 0;
  const isForceValid =
    newForceSource.trim().length > 0 && newForceTarget.trim().length > 0;
  const isDontValid = newDontTerm.trim().length > 0;

  // SpeechSynthesis audio playback
  const handlePlayAudio = (text: string) => {
    const cleanText = text.trim();
    if (!cleanText) return;
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(cleanText);
      window.speechSynthesis.speak(utterance);
    }
  };

  // Pronunciation Add / Cancel / Delete Handlers
  const handleSavePronunciation = async () => {
    const word = newOriginalWord.trim();
    const phonetic = newPronunciation.trim();
    if (!word || !phonetic) return;

    try {
      let ruleId = typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : "pron_rule";
      if (glossaryId && /^[0-9a-fA-F-]{36}$/.test(glossaryId)) {
        const created = await api.brandGlossaries.createRule(
          glossaryId,
          {
            term: word,
            phonetic_spelling: phonetic,
            rule_type: "pronunciation",
          },
          currentWorkspace?.id
        );
        ruleId = created.id;
      }

      const newEntry: GlossaryEntry = {
        id: ruleId,
        originalWord: word,
        targetOrPronunciation: phonetic,
      };
      const updated = [newEntry, ...pronunciations];
      setPronunciations(updated);
      if (onUpdatePronunciations) {
        onUpdatePronunciations(updated);
      }
      setNewOriginalWord("");
      setNewPronunciation("");
      setIsAddingPronunciation(false);
    } catch (err: any) {
      alert(err?.message || "Failed to save pronunciation rule");
    }
  };

  const handleCancelPronunciation = () => {
    setNewOriginalWord("");
    setNewPronunciation("");
    setIsAddingPronunciation(false);
  };

  const handleDeletePronunciation = async (id: string) => {
    try {
      if (glossaryId && /^[0-9a-fA-F-]{36}$/.test(glossaryId) && /^[0-9a-fA-F-]{36}$/.test(id)) {
        await api.brandGlossaries.deleteRule(glossaryId, id, currentWorkspace?.id);
      }
      const updated = pronunciations.filter((p) => p.id !== id);
      setPronunciations(updated);
      if (onUpdatePronunciations) {
        onUpdatePronunciations(updated);
      }
    } catch (err: any) {
      alert(err?.message || "Failed to delete pronunciation rule");
    }
  };

  // Force Translate Handlers
  const handleSaveForceRule = async () => {
    const source = newForceSource.trim();
    const target = newForceTarget.trim();
    if (!source || !target) return;

    try {
      let ruleId = typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : "force_rule";
      if (glossaryId && /^[0-9a-fA-F-]{36}$/.test(glossaryId)) {
        const created = await api.brandGlossaries.createRule(
          glossaryId,
          {
            term: source,
            replacement: target,
            rule_type: "force_translate",
          },
          currentWorkspace?.id
        );
        ruleId = created.id;
      }

      const newRule: ForceTranslateRule = {
        id: ruleId,
        sourceWord: source,
        targetWord: target,
      };
      const updated = [newRule, ...forceRules];
      setForceRules(updated);
      if (onUpdateForceRules) {
        onUpdateForceRules(updated);
      }
      setNewForceSource("");
      setNewForceTarget("");
      setIsAddingForceRule(false);
    } catch (err: any) {
      alert(err?.message || "Failed to save translation rule");
    }
  };

  const handleCancelForceRule = () => {
    setNewForceSource("");
    setNewForceTarget("");
    setIsAddingForceRule(false);
  };

  const handleDeleteForceRule = async (id: string) => {
    try {
      if (glossaryId && /^[0-9a-fA-F-]{36}$/.test(glossaryId) && /^[0-9a-fA-F-]{36}$/.test(id)) {
        await api.brandGlossaries.deleteRule(glossaryId, id, currentWorkspace?.id);
      }
      const updated = forceRules.filter((r) => r.id !== id);
      setForceRules(updated);
      if (onUpdateForceRules) {
        onUpdateForceRules(updated);
      }
    } catch (err: any) {
      alert(err?.message || "Failed to delete translation rule");
    }
  };

  // Don't Translate Handlers
  const handleSaveDontRule = async () => {
    const term = newDontTerm.trim();
    if (!term) return;

    try {
      let ruleId = typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : "dont_rule";
      if (glossaryId && /^[0-9a-fA-F-]{36}$/.test(glossaryId)) {
        const created = await api.brandGlossaries.createRule(
          glossaryId,
          {
            term: term,
            rule_type: "do_not_translate",
          },
          currentWorkspace?.id
        );
        ruleId = created.id;
      }

      const newRule: DontTranslateRule = {
        id: ruleId,
        term: term,
      };
      const updated = [newRule, ...dontRules];
      setDontRules(updated);
      if (onUpdateDontTranslateRules) {
        onUpdateDontTranslateRules(updated);
      }
      setNewDontTerm("");
      setIsAddingDontRule(false);
    } catch (err: any) {
      alert(err?.message || "Failed to save rule");
    }
  };

  const handleCancelDontRule = () => {
    setNewDontTerm("");
    setIsAddingDontRule(false);
  };

  const handleDeleteDontRule = async (id: string) => {
    try {
      if (glossaryId && /^[0-9a-fA-F-]{36}$/.test(glossaryId) && /^[0-9a-fA-F-]{36}$/.test(id)) {
        await api.brandGlossaries.deleteRule(glossaryId, id, currentWorkspace?.id);
      }
      const updated = dontRules.filter((r) => r.id !== id);
      setDontRules(updated);
      if (onUpdateDontTranslateRules) {
        onUpdateDontTranslateRules(updated);
      }
    } catch (err: any) {
      alert(err?.message || "Failed to delete rule");
    }
  };

  // CSV Parsers
  const handlePronCsv = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = async (event) => {
      const text = event.target?.result as string;
      if (!text) return;
      const lines = text.split(/\r?\n/).filter((l) => l.trim().length > 0);
      const items: GlossaryEntry[] = [];
      for (let idx = 0; idx < lines.length; idx++) {
        const line = lines[idx];
        if (
          idx === 0 &&
          (line.toLowerCase().includes("word") ||
            line.toLowerCase().includes("original"))
        )
          continue;
        const parts = line.split(",").map((p) => p.trim().replace(/^"|"$/g, ""));
        if (parts[0]) {
          let ruleId = typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : `pron_${idx}`;
          const word = parts[0];
          const phonetic = parts[1] || "Uploaded pronunciation";
          if (glossaryId && /^[0-9a-fA-F-]{36}$/.test(glossaryId)) {
            try {
              const created = await api.brandGlossaries.createRule(
                glossaryId,
                {
                  term: word,
                  phonetic_spelling: phonetic,
                  rule_type: "pronunciation",
                },
                currentWorkspace?.id
              );
              ruleId = created.id;
            } catch (err) {
              console.error("Failed to persist CSV pronunciation rule", err);
            }
          }
          items.push({
            id: ruleId,
            originalWord: word,
            targetOrPronunciation: phonetic,
          });
        }
      }
      if (items.length > 0) {
        const updated = [...items, ...pronunciations];
        setPronunciations(updated);
        if (onUpdatePronunciations) {
          onUpdatePronunciations(updated);
        }
      }
    };
    reader.readAsText(file);
    e.target.value = "";
  };

  const handleForceCsv = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = async (event) => {
      const text = event.target?.result as string;
      if (!text) return;
      const lines = text.split(/\r?\n/).filter((l) => l.trim().length > 0);
      const items: ForceTranslateRule[] = [];
      for (let idx = 0; idx < lines.length; idx++) {
        const line = lines[idx];
        if (
          idx === 0 &&
          (line.toLowerCase().includes("source") ||
            line.toLowerCase().includes("original"))
        )
          continue;
        const parts = line.split(",").map((p) => p.trim().replace(/^"|"$/g, ""));
        if (parts[0]) {
          let ruleId = typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : `force_${idx}`;
          const source = parts[0];
          const target = parts[1] || parts[0];
          if (glossaryId && /^[0-9a-fA-F-]{36}$/.test(glossaryId)) {
            try {
              const created = await api.brandGlossaries.createRule(
                glossaryId,
                {
                  term: source,
                  replacement: target,
                  rule_type: "force_translate",
                },
                currentWorkspace?.id
              );
              ruleId = created.id;
            } catch (err) {
              console.error("Failed to persist CSV translation rule", err);
            }
          }
          items.push({
            id: ruleId,
            sourceWord: source,
            targetWord: target,
          });
        }
      }
      if (items.length > 0) {
        const updated = [...items, ...forceRules];
        setForceRules(updated);
        if (onUpdateForceRules) {
          onUpdateForceRules(updated);
        }
      }
    };
    reader.readAsText(file);
    e.target.value = "";
  };

  const handleDontCsv = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = async (event) => {
      const text = event.target?.result as string;
      if (!text) return;
      const lines = text.split(/\r?\n/).filter((l) => l.trim().length > 0);
      const items: DontTranslateRule[] = [];
      for (let idx = 0; idx < lines.length; idx++) {
        const line = lines[idx];
        if (
          idx === 0 &&
          (line.toLowerCase().includes("term") ||
            line.toLowerCase().includes("word"))
        )
          continue;
        const parts = line.split(",").map((p) => p.trim().replace(/^"|"$/g, ""));
        if (parts[0]) {
          let ruleId = typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : `dont_${idx}`;
          const term = parts[0];
          if (glossaryId && /^[0-9a-fA-F-]{36}$/.test(glossaryId)) {
            try {
              const created = await api.brandGlossaries.createRule(
                glossaryId,
                {
                  term: term,
                  rule_type: "do_not_translate",
                },
                currentWorkspace?.id
              );
              ruleId = created.id;
            } catch (err) {
              console.error("Failed to persist CSV dont-translate rule", err);
            }
          }
          items.push({
            id: ruleId,
            term: term,
          });
        }
      }
      if (items.length > 0) {
        const updated = [...items, ...dontRules];
        setDontRules(updated);
        if (onUpdateDontTranslateRules) {
          onUpdateDontTranslateRules(updated);
        }
      }
    };
    reader.readAsText(file);
    e.target.value = "";
  };

  // Search Filters
  const filteredPronunciations = pronunciations.filter(
    (item) =>
      !searchQuery.trim() ||
      item.originalWord.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.targetOrPronunciation
        .toLowerCase()
        .includes(searchQuery.toLowerCase())
  );

  const filteredForceRules = forceRules.filter(
    (rule) =>
      !searchQuery.trim() ||
      rule.sourceWord.toLowerCase().includes(searchQuery.toLowerCase()) ||
      rule.targetWord.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const filteredDontRules = dontRules.filter(
    (rule) =>
      !searchQuery.trim() ||
      rule.term.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className={`flex-1 h-screen overflow-y-auto ${isLight ? "bg-slate-50 text-slate-900" : "bg-[#07090e] text-slate-100"} flex flex-col font-sans select-none relative scrollbar-thin`}>
      {/* 1. TOP HEADER */}
      <header className={`w-full px-6 sm:px-10 pt-6 pb-4 flex items-center justify-between z-20 border-b ${isLight ? "border-slate-200 bg-white" : "border-[#1b2940] bg-[#07090e]"}`}>
        <div className="flex items-center gap-3">
          {onBack && (
            <button
              type="button"
              onClick={onBack}
              title="Back"
              className={`w-9 h-9 rounded-full border ${isLight ? "border-slate-200 bg-slate-100 hover:bg-slate-200 text-slate-700 hover:text-slate-900" : "border-[#1b2940] bg-[#0b111e] hover:bg-[#162035] text-slate-300 hover:text-white"} flex items-center justify-center transition-colors shadow-xs cursor-pointer`}
            >
              <ArrowLeft size={16} />
            </button>
          )}
          <h1 className={`text-xl sm:text-2xl font-black ${isLight ? "text-slate-900" : "text-white"} tracking-tight`}>
            {glossaryName}
          </h1>
        </div>

        <div className="flex items-center gap-4">
          {/* Search Input on Top Right */}
          <div className="relative w-48 sm:w-64">
            <Search
              size={14}
              className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none"
            />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search Glossary"
              className={`w-full ${isLight ? "bg-slate-100 border-slate-200 text-slate-900 placeholder:text-slate-400 focus:bg-white focus:border-blue-500" : "bg-[#0b111e] border-[#1b2940] text-white placeholder:text-slate-500 focus:bg-[#07090e] focus:border-cyan-500"} border rounded-full pl-9 pr-3.5 py-1.5 text-xs focus:outline-none shadow-xs transition-all`}
            />
          </div>

          <AskRhysWidget />
        </div>
      </header>

      {/* 2. TOP SEGMENTED TABS */}
      <div className="w-full max-w-4xl mx-auto px-6 text-center pt-6 pb-4">
        <div className={`${isLight ? "bg-slate-200/80 border-slate-300/80" : "bg-[#0b111e] border-[#1b2940]"} border p-1 rounded-full inline-flex items-center gap-1 shadow-inner`}>
          <button
            type="button"
            onClick={() => setActiveTab("pronunciations")}
            className={`px-6 py-1.5 rounded-full text-xs font-semibold transition-all cursor-pointer ${
              activeTab === "pronunciations"
                ? isLight
                  ? "bg-white text-slate-900 border-slate-200 shadow-sm font-bold"
                  : "bg-[#18233c] text-white border border-[#2b3a5d]/50 shadow-xs font-bold"
                : isLight
                ? "text-slate-600 hover:text-slate-900 hover:bg-white/50 font-medium"
                : "text-slate-400 hover:text-slate-200 hover:bg-[#152033] font-medium"
            }`}
          >
            Pronunciations
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("translations")}
            className={`px-6 py-1.5 rounded-full text-xs font-semibold transition-all cursor-pointer ${
              activeTab === "translations"
                ? isLight
                  ? "bg-white text-slate-900 border-slate-200 shadow-sm font-bold"
                  : "bg-[#18233c] text-white border border-[#2b3a5d]/50 shadow-xs font-bold"
                : isLight
                ? "text-slate-600 hover:text-slate-900 hover:bg-white/50 font-medium"
                : "text-slate-400 hover:text-slate-200 hover:bg-[#152033] font-medium"
            }`}
          >
            Translations
          </button>
        </div>
      </div>

      {/* 3. MAIN TAB CONTENT */}
      <main className="max-w-[820px] w-full mx-auto px-6 pb-20 flex-1">
        {activeTab === "pronunciations" ? (
          /* ================= PRONUNCIATIONS SECTION ================= */
          <div className="space-y-4">
            {/* Hidden CSV Input */}
            <input
              ref={pronCsvRef}
              type="file"
              accept=".csv"
              onChange={handlePronCsv}
              className="hidden"
            />

            {/* Section Header with Heading on Left and Action Buttons on Right */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-2">
              <div>
                <h2 className="text-xl font-extrabold text-white tracking-tight">
                  Pronunciations
                </h2>
                <p className="text-xs text-slate-400 mt-1 font-normal">
                  Ensure correct pronunciation of brand terms by entering
                  phonetic spellings.
                </p>
              </div>

              <div className="flex items-center gap-2.5 shrink-0">
                <button
                  type="button"
                  onClick={() => setIsAddingPronunciation(true)}
                  className="flex items-center gap-1.5 px-3.5 py-1.5 bg-white hover:bg-slate-200 text-slate-950 text-xs font-semibold rounded-full shadow-xs transition-all cursor-pointer active:scale-95 select-none"
                >
                  <Plus size={13} className="stroke-[2.5]" />
                  <span>Add new</span>
                </button>

                <button
                  type="button"
                  onClick={() => pronCsvRef.current?.click()}
                  className="flex items-center gap-1.5 px-3.5 py-1.5 bg-[#0f172a] hover:bg-[#172238] text-slate-200 border border-[#1b2940] text-xs font-semibold rounded-full shadow-xs transition-all cursor-pointer select-none"
                >
                  <UploadCloud size={13} className="text-slate-400" />
                  <span>Upload CSV</span>
                </button>
              </div>
            </div>

            {/* Table Container */}
            <div className={`${isLight ? "bg-white border-slate-200 shadow-sm" : "bg-[#0b111e] border-[#1b2940] shadow-xl"} rounded-3xl border overflow-hidden mt-3`}>
              {/* Table Header */}
              <div className={`grid grid-cols-2 ${isLight ? "bg-slate-50 border-slate-200 text-slate-700" : "bg-[#0e1626] border-[#1b2940] text-slate-400"} border-b px-6 py-3.5`}>
                <span className="text-xs font-semibold">
                  Original Word
                </span>
                <span className="text-xs font-semibold">
                  Word Behavior
                </span>
              </div>

              {/* Inline Edit Row (Matches Reference Screenshot) */}
              {isAddingPronunciation && (
                <div className={`grid grid-cols-2 items-center px-6 py-3.5 ${isLight ? "bg-slate-50 border-slate-200" : "bg-[#0e1626]/80 border-[#1b2940]"} border-b gap-4`}>
                  {/* Left Column: Original Word Input + Right Arrow */}
                  <div className="flex items-center gap-3">
                    <input
                      ref={originalWordInputRef}
                      type="text"
                      value={newOriginalWord}
                      onChange={(e) => setNewOriginalWord(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" && isPronValid) {
                          e.preventDefault();
                          handleSavePronunciation();
                        }
                        if (e.key === "Escape") {
                          e.preventDefault();
                          handleCancelPronunciation();
                        }
                      }}
                      placeholder="Enter original word"
                      className={`w-full ${isLight ? "bg-white border-slate-300 text-slate-900 placeholder:text-slate-400 focus:border-blue-500" : "bg-[#07090e] border-[#1b2940] text-white placeholder:text-slate-500 focus:border-cyan-500"} border rounded-2xl px-3.5 py-2 text-xs focus:outline-none shadow-2xs transition-all`}
                    />
                    <ArrowRight size={15} className={isLight ? "text-slate-400" : "text-slate-500"} />
                  </div>

                  {/* Right Column: Pronunciation Input + Play Button + Save Check + Cancel X */}
                  <div className="flex items-center justify-between gap-2.5">
                    <div className="relative flex-1 flex items-center">
                      <input
                        type="text"
                        value={newPronunciation}
                        onChange={(e) => setNewPronunciation(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter" && isPronValid) {
                            e.preventDefault();
                            handleSavePronunciation();
                          }
                          if (e.key === "Escape") {
                            e.preventDefault();
                            handleCancelPronunciation();
                          }
                        }}
                        placeholder="Enter pronunciation"
                        className={`w-full ${isLight ? "bg-white border-slate-300 text-slate-900 placeholder:text-slate-400 focus:border-blue-500" : "bg-[#07090e] border-[#1b2940] text-white placeholder:text-slate-500 focus:border-cyan-500"} border rounded-2xl pl-3.5 pr-9 py-2 text-xs focus:outline-none shadow-2xs transition-all`}
                      />
                      {/* Play button */}
                      <button
                        type="button"
                        onClick={() =>
                          handlePlayAudio(newPronunciation || newOriginalWord)
                        }
                        title="Play pronunciation"
                        className={`absolute right-2 top-1/2 -translate-y-1/2 w-6 h-6 rounded-full ${isLight ? "bg-blue-50 hover:bg-blue-100 text-blue-600" : "bg-[#162035] hover:bg-[#1f2d4a] text-cyan-400"} flex items-center justify-center transition-colors cursor-pointer`}
                      >
                        <Play size={11} className="fill-current ml-0.5" />
                      </button>
                    </div>

                    {/* Save Check Button */}
                    <button
                      type="button"
                      onClick={handleSavePronunciation}
                      disabled={!isPronValid}
                      title="Save pronunciation"
                      className={`w-7 h-7 rounded-full flex items-center justify-center transition-all shadow-xs shrink-0 ${
                        isPronValid
                          ? isLight
                            ? "bg-blue-600 text-white hover:bg-blue-700 cursor-pointer font-bold"
                            : "bg-white text-slate-950 hover:bg-slate-200 cursor-pointer font-bold"
                          : "bg-slate-200 text-slate-400 dark:bg-[#151f33] dark:text-slate-600 cursor-not-allowed border dark:border-[#1b2940]"
                      }`}
                    >
                      <Check
                        size={13}
                        className={isPronValid ? "stroke-[2.5]" : "stroke-2"}
                      />
                    </button>

                    {/* Cancel X Button */}
                    <button
                      type="button"
                      onClick={handleCancelPronunciation}
                      title="Cancel"
                      className={`w-7 h-7 rounded-full border ${isLight ? "border-slate-200 bg-slate-100 text-slate-600 hover:text-slate-900 hover:bg-slate-200" : "border-[#1b2940] bg-[#0f172a] text-slate-400 hover:text-slate-200 hover:bg-[#162035]"} flex items-center justify-center transition-all cursor-pointer shrink-0`}
                    >
                      <X size={13} />
                    </button>
                  </div>
                </div>
              )}

              {/* Items List */}
              {filteredPronunciations.length > 0 ? (
                <div className={`divide-y ${isLight ? "divide-slate-100" : "divide-[#151f33]"}`}>
                  {filteredPronunciations.map((item) => (
                    <div
                      key={item.id}
                      className={`grid grid-cols-2 items-center px-6 py-4 ${isLight ? "hover:bg-slate-50" : "hover:bg-[#101828]/70"} transition-colors group`}
                    >
                      <span className={`text-xs font-bold ${isLight ? "text-slate-900" : "text-white"}`}>
                        {item.originalWord}
                      </span>
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className={`text-xs ${isLight ? "text-slate-600" : "text-slate-300"}`}>
                            {item.targetOrPronunciation}
                          </span>
                          <button
                            type="button"
                            onClick={() =>
                              handlePlayAudio(item.targetOrPronunciation)
                            }
                            title="Play pronunciation"
                            className={`w-5 h-5 rounded-full ${isLight ? "bg-blue-50 text-blue-600 hover:bg-blue-100" : "bg-[#162035] text-cyan-400 hover:bg-[#1f2d4a]"} flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer`}
                          >
                            <Play size={9} className="fill-current ml-0.5" />
                          </button>
                        </div>
                        <button
                          type="button"
                          onClick={() => handleDeletePronunciation(item.id)}
                          title="Delete"
                          className="text-slate-400 hover:text-rose-500 transition-colors p-1 opacity-0 group-hover:opacity-100 cursor-pointer"
                        >
                          <Trash2 size={13} />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                !isAddingPronunciation && (
                  <div className={`py-14 text-center text-xs ${isLight ? "text-slate-500" : "text-slate-500"} font-medium`}>
                    {searchQuery
                      ? "No matching pronunciations found"
                      : "No pronunciations added yet"}
                  </div>
                )
              )}
            </div>
          </div>
        ) : (
          /* ================= TRANSLATIONS SECTION (Matches Reference Screenshot) ================= */
          <div className="space-y-10 pb-16">
            {/* SECTION 1: Force Translate */}
            <div>
              {/* Hidden CSV Input */}
              <input
                ref={forceCsvRef}
                type="file"
                accept=".csv"
                onChange={handleForceCsv}
                className="hidden"
              />

              {/* Header */}
              <div>
                <h2 className={`text-xl font-extrabold ${isLight ? "text-slate-900" : "text-white"} tracking-tight`}>
                  Force Translate
                </h2>
                <p className={`text-xs ${isLight ? "text-slate-600" : "text-slate-400"} mt-1 font-normal`}>
                  A list of words you wish to translate into specific words.
                </p>
              </div>

              {/* If has items or inline adding */}
              {isAddingForceRule || filteredForceRules.length > 0 ? (
                <div className={`${isLight ? "bg-white border-slate-200 shadow-sm" : "bg-[#0b111e] border-[#1b2940] shadow-xl"} rounded-3xl border overflow-hidden mt-3`}>
                  {/* Table Header */}
                  <div className={`grid grid-cols-2 ${isLight ? "bg-slate-50 border-slate-200 text-slate-700" : "bg-[#0e1626] border-[#1b2940] text-slate-400"} border-b px-6 py-3.5`}>
                    <span className="text-xs font-semibold">
                      Original Word
                    </span>
                    <span className="text-xs font-semibold">
                      Translate To
                    </span>
                  </div>

                  {/* Inline Add Row */}
                  {isAddingForceRule && (
                    <div className={`grid grid-cols-2 items-center px-6 py-3.5 ${isLight ? "bg-slate-50 border-slate-200" : "bg-[#0e1626]/80 border-[#1b2940]"} border-b gap-4`}>
                      <div className="flex items-center gap-3">
                        <input
                          ref={forceSourceInputRef}
                          type="text"
                          value={newForceSource}
                          onChange={(e) => setNewForceSource(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter" && isForceValid)
                              handleSaveForceRule();
                            if (e.key === "Escape") handleCancelForceRule();
                          }}
                          placeholder="Enter original word"
                          className={`w-full ${isLight ? "bg-white border-slate-300 text-slate-900 placeholder:text-slate-400 focus:border-blue-500" : "bg-[#07090e] border-[#1b2940] text-white placeholder:text-slate-500 focus:border-cyan-500"} border rounded-2xl px-3.5 py-2 text-xs focus:outline-none shadow-2xs transition-all`}
                        />
                        <ArrowRight size={15} className={isLight ? "text-slate-400" : "text-slate-500"} />
                      </div>

                      <div className="flex items-center justify-between gap-2.5">
                        <input
                          type="text"
                          value={newForceTarget}
                          onChange={(e) => setNewForceTarget(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter" && isForceValid)
                              handleSaveForceRule();
                            if (e.key === "Escape") handleCancelForceRule();
                          }}
                          placeholder="Enter translation"
                          className={`w-full ${isLight ? "bg-white border-slate-300 text-slate-900 placeholder:text-slate-400 focus:border-blue-500" : "bg-[#07090e] border-[#1b2940] text-white placeholder:text-slate-500 focus:border-cyan-500"} border rounded-2xl px-3.5 py-2 text-xs focus:outline-none shadow-2xs transition-all`}
                        />

                        {/* Save Check */}
                        <button
                          type="button"
                          onClick={handleSaveForceRule}
                          disabled={!isForceValid}
                          title="Save rule"
                          className={`w-7 h-7 rounded-full flex items-center justify-center transition-all shadow-xs shrink-0 ${
                            isForceValid
                              ? isLight
                                ? "bg-blue-600 text-white hover:bg-blue-700 cursor-pointer font-bold"
                                : "bg-white text-slate-950 hover:bg-slate-200 cursor-pointer font-bold"
                              : "bg-slate-200 text-slate-400 dark:bg-[#151f33] dark:text-slate-600 cursor-not-allowed border dark:border-[#1b2940]"
                          }`}
                        >
                          <Check
                            size={13}
                            className={isForceValid ? "stroke-[2.5]" : "stroke-2"}
                          />
                        </button>

                        {/* Cancel X */}
                        <button
                          type="button"
                          onClick={handleCancelForceRule}
                          title="Cancel"
                          className={`w-7 h-7 rounded-full border ${isLight ? "border-slate-200 bg-slate-100 text-slate-600 hover:text-slate-900 hover:bg-slate-200" : "border-[#1b2940] bg-[#0f172a] text-slate-400 hover:text-slate-200 hover:bg-[#162035]"} flex items-center justify-center transition-all cursor-pointer shrink-0`}
                        >
                          <X size={13} />
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Rows */}
                  <div className={`divide-y ${isLight ? "divide-slate-100" : "divide-[#151f33]"}`}>
                    {filteredForceRules.map((rule) => (
                      <div
                        key={rule.id}
                        className={`grid grid-cols-2 items-center px-6 py-4 ${isLight ? "hover:bg-slate-50" : "hover:bg-[#101828]/70"} transition-colors group`}
                      >
                        <span className={`text-xs font-bold ${isLight ? "text-slate-900" : "text-white"}`}>
                          {rule.sourceWord}
                        </span>
                        <div className="flex items-center justify-between">
                          <span className={`text-xs ${isLight ? "text-slate-600" : "text-slate-300"}`}>
                            {rule.targetWord}
                          </span>
                          <button
                            type="button"
                            onClick={() => handleDeleteForceRule(rule.id)}
                            title="Delete"
                            className="text-slate-400 hover:text-rose-500 transition-colors p-1 opacity-0 group-hover:opacity-100 cursor-pointer"
                          >
                            <Trash2 size={13} />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                /* Empty-State Card (Matches Reference Screenshot) */
                <div className={`${isLight ? "bg-white border-slate-200 shadow-sm" : "bg-[#0b111e] border-[#1b2940] shadow-xl"} rounded-3xl border p-10 sm:p-12 text-center max-w-[820px] mx-auto mt-3`}>
                  <div className={`w-12 h-12 rounded-2xl ${isLight ? "bg-blue-50 border border-blue-200 text-blue-600" : "bg-[#162035] border border-[#2b3a5d]/40 text-cyan-400"} mx-auto flex items-center justify-center mb-3`}>
                    <FileText size={24} />
                  </div>
                  <h3 className={`text-sm font-bold ${isLight ? "text-slate-900" : "text-white"}`}>
                    No &apos;Force Translate&apos; rules added yet
                  </h3>

                  <div className="flex items-center justify-center gap-3 mt-5">
                    <button
                      type="button"
                      onClick={() => forceCsvRef.current?.click()}
                      className={`${isLight ? "bg-slate-100 hover:bg-slate-200 text-slate-800 border-slate-300" : "bg-[#0f172a] hover:bg-[#172238] text-slate-200 border-[#1b2940]"} border text-xs font-semibold px-5 py-2.5 rounded-full shadow-xs flex items-center gap-1.5 transition-all cursor-pointer`}
                    >
                      <UploadCloud size={14} className={isLight ? "text-slate-600" : "text-slate-400"} />
                      <span>Upload CSV</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => setIsAddingForceRule(true)}
                      className={`${isLight ? "bg-blue-600 hover:bg-blue-700 text-white" : "bg-white hover:bg-slate-200 text-slate-950"} text-xs font-semibold px-5 py-2.5 rounded-full shadow-xs flex items-center gap-1.5 transition-all cursor-pointer`}
                    >
                      <Plus size={14} />
                      <span>Add manually</span>
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* SECTION 2: Don't Translate */}
            <div>
              {/* Hidden CSV Input */}
              <input
                ref={dontCsvRef}
                type="file"
                accept=".csv"
                onChange={handleDontCsv}
                className="hidden"
              />

              {/* Header */}
              <div>
                <h2 className={`text-xl font-extrabold ${isLight ? "text-slate-900" : "text-white"} tracking-tight`}>
                  Don&apos;t Translate
                </h2>
                <p className={`text-xs ${isLight ? "text-slate-600" : "text-slate-400"} mt-1 font-normal`}>
                  Add product names, acronyms, or brand phrases that should always
                  stay as-is.
                </p>
              </div>

              {/* If has items or inline adding */}
              {isAddingDontRule || filteredDontRules.length > 0 ? (
                <div className={`${isLight ? "bg-white border-slate-200 shadow-sm" : "bg-[#0b111e] border-[#1b2940] shadow-xl"} rounded-3xl border overflow-hidden mt-3`}>
                  {/* Table Header */}
                  <div className={`${isLight ? "bg-slate-50 border-slate-200 text-slate-700" : "bg-[#0e1626] border-[#1b2940] text-slate-400"} border-b px-6 py-3.5`}>
                    <span className="text-xs font-semibold">
                      Term / Phrase
                    </span>
                  </div>

                  {/* Inline Add Row */}
                  {isAddingDontRule && (
                    <div className={`flex items-center px-6 py-3.5 ${isLight ? "bg-slate-50 border-slate-200" : "bg-[#0e1626]/80 border-[#1b2940]"} border-b gap-3`}>
                      <input
                        ref={dontTermInputRef}
                        type="text"
                        value={newDontTerm}
                        onChange={(e) => setNewDontTerm(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter" && isDontValid)
                            handleSaveDontRule();
                          if (e.key === "Escape") handleCancelDontRule();
                        }}
                        placeholder="Enter term or phrase"
                        className={`flex-1 ${isLight ? "bg-white border-slate-300 text-slate-900 placeholder:text-slate-400 focus:border-blue-500" : "bg-[#07090e] border-[#1b2940] text-white placeholder:text-slate-500 focus:border-cyan-500"} border rounded-2xl px-3.5 py-2 text-xs focus:outline-none shadow-2xs transition-all`}
                      />

                      {/* Save Check */}
                      <button
                        type="button"
                        onClick={handleSaveDontRule}
                        disabled={!isDontValid}
                        title="Save rule"
                        className={`w-7 h-7 rounded-full flex items-center justify-center transition-all shadow-xs shrink-0 ${
                          isDontValid
                            ? isLight
                              ? "bg-blue-600 text-white hover:bg-blue-700 cursor-pointer font-bold"
                              : "bg-white text-slate-950 hover:bg-slate-200 cursor-pointer font-bold"
                            : "bg-slate-200 text-slate-400 dark:bg-[#151f33] dark:text-slate-600 cursor-not-allowed border dark:border-[#1b2940]"
                        }`}
                      >
                        <Check
                          size={13}
                          className={isDontValid ? "stroke-[2.5]" : "stroke-2"}
                        />
                      </button>

                      {/* Cancel X */}
                      <button
                        type="button"
                        onClick={handleCancelDontRule}
                        title="Cancel"
                        className={`w-7 h-7 rounded-full border ${isLight ? "border-slate-200 bg-slate-100 text-slate-600 hover:text-slate-900 hover:bg-slate-200" : "border-[#1b2940] bg-[#0f172a] text-slate-400 hover:text-slate-200 hover:bg-[#162035]"} flex items-center justify-center transition-all cursor-pointer shrink-0`}
                      >
                        <X size={13} />
                      </button>
                    </div>
                  )}

                  {/* Rows */}
                  <div className={`divide-y ${isLight ? "divide-slate-100" : "divide-[#151f33]"}`}>
                    {filteredDontRules.map((rule) => (
                      <div
                        key={rule.id}
                        className={`flex items-center justify-between px-6 py-4 ${isLight ? "hover:bg-slate-50" : "hover:bg-[#101828]/70"} transition-colors group`}
                      >
                        <span className={`text-xs font-bold ${isLight ? "text-slate-900" : "text-white"}`}>
                          {rule.term}
                        </span>
                        <button
                          type="button"
                          onClick={() => handleDeleteDontRule(rule.id)}
                          title="Delete"
                          className="text-slate-400 hover:text-rose-500 transition-colors p-1 opacity-0 group-hover:opacity-100 cursor-pointer"
                        >
                          <Trash2 size={13} />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                /* Empty-State Card (Matches Reference Screenshot) */
                <div className={`${isLight ? "bg-white border-slate-200 shadow-sm" : "bg-[#0b111e] border-[#1b2940] shadow-xl"} rounded-3xl border p-10 sm:p-12 text-center max-w-[820px] mx-auto mt-3`}>
                  <div className={`w-12 h-12 rounded-2xl ${isLight ? "bg-blue-50 border border-blue-200 text-blue-600" : "bg-[#162035] border border-[#2b3a5d]/40 text-cyan-400"} mx-auto flex items-center justify-center mb-3`}>
                    <FileText size={24} />
                  </div>
                  <h3 className={`text-sm font-bold ${isLight ? "text-slate-900" : "text-white"}`}>
                    No &apos;Don&apos;t Translate&apos; rules added yet
                  </h3>

                  <div className="flex items-center justify-center gap-3 mt-5">
                    <button
                      type="button"
                      onClick={() => dontCsvRef.current?.click()}
                      className={`${isLight ? "bg-slate-100 hover:bg-slate-200 text-slate-800 border-slate-300" : "bg-[#0f172a] hover:bg-[#172238] text-slate-200 border-[#1b2940]"} border text-xs font-semibold px-5 py-2.5 rounded-full shadow-xs flex items-center gap-1.5 transition-all cursor-pointer`}
                    >
                      <UploadCloud size={14} className={isLight ? "text-slate-600" : "text-slate-400"} />
                      <span>Upload CSV</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => setIsAddingDontRule(true)}
                      className={`${isLight ? "bg-blue-600 hover:bg-blue-700 text-white" : "bg-white hover:bg-slate-200 text-slate-950"} text-xs font-semibold px-5 py-2.5 rounded-full shadow-xs flex items-center gap-1.5 transition-all cursor-pointer`}
                    >
                      <Plus size={14} />
                      <span>Add manually</span>
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
