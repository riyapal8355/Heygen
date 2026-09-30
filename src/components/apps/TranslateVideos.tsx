"use client";

import React, { useState, useRef, useEffect } from "react";
import {
  ArrowLeft,
  Upload,
  Link as LinkIcon,
  Sparkles,
  FileVideo,
  Languages,
  Check,
  ChevronDown,
  Plus,
  Trash2,
  FolderClosed,
  CheckCircle2,
  BookOpen,
  Search,
  UploadCloud,
  FileSpreadsheet,
  X,
  Filter,
} from "lucide-react";
import AskRhysWidget from "../dashboard/AskRhysWidget";
import { useAuth } from "@/context/AuthContext";
import { useTheme } from "@/context/ThemeContext";
import { api } from "@/lib/api";

export interface ExistingProjectItem {
  id: string;
  title: string;
  status: "Draft" | "Rendered" | "Ready";
  time: string;
  type: string;
  image: string;
}

export const EXISTING_PROJECTS_DATA: ExistingProjectItem[] = [];

export interface GlossaryOption {
  id: string;
  name: string;
}

interface TranslateVideosProps {
  onBack?: () => void;
  onOpenStudio?: (projectId?: string) => void;
  glossaries?: GlossaryOption[];
  selectedGlossaryId?: string;
  onSelectAndOpenGlossary?: (glossary: GlossaryOption) => void;
  onCreateGlossary?: (name: string) => void;
  onNavigateCreateGlossary?: (glossaryName: string) => void;
  selectedGlossary?: string;
  onSelectGlossary?: (name: string) => void;
}

interface RuleItem {
  id: string;
  originalWord: string;
  behavior: string;
}

interface WordItem {
  id: string;
  word: string;
}

export default function TranslateVideos({
  onBack,
  onOpenStudio,
  glossaries: propGlossaries,
  selectedGlossaryId: propSelectedGlossaryId,
  onSelectAndOpenGlossary,
  onCreateGlossary,
  onNavigateCreateGlossary,
  selectedGlossary: propSelectedGlossary,
  onSelectGlossary,
}: TranslateVideosProps) {
  const { theme } = useTheme();
  const isLight = theme === "light";

  // Top level segmented tabs
  const [activeTab, setActiveTab] = useState<"translate" | "glossary">(
    "translate"
  );

  // Glossary sub-tabs
  const [glossarySubTab, setGlossarySubTab] = useState<
    "pronunciation" | "force_translate"
  >("pronunciation");

  // Translate tab state
  const [videoUrl, setVideoUrl] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedProject, setSelectedProject] = useState<ExistingProjectItem | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [showProjectPicker, setShowProjectPicker] = useState(false);
  const [projectSearchQuery, setProjectSearchQuery] = useState("");
  const [selectedProjectType, setSelectedProjectType] = useState<string>("all");
  const [isProjectFilterOpen, setIsProjectFilterOpen] = useState(false);
  const [targetLanguage, setTargetLanguage] = useState<string>("es");
  const [enableSubtitles, setEnableSubtitles] = useState(true);
  const [enableLipSync, setEnableLipSync] = useState(false);
  const [translationJob, setTranslationJob] = useState<{
    jobId: string | null;
    status: string;
    progress: number;
    stage?: string;
    message?: string;
    result?: any;
    error?: string;
  }>({
    jobId: null,
    status: "idle",
    progress: 0,
  });

  // Durable translation recovery across browser refreshes / component remounts
  useEffect(() => {
    if (typeof window === "undefined") return;
    const savedJobId = window.sessionStorage.getItem("heyzen_active_translation_job_id");
    if (savedJobId) {
      api.jobs
        .get(savedJobId)
        .then((job) => {
          setTranslationJob({
            jobId: job.id,
            status: job.status,
            progress: job.progress_percent ?? 0,
            stage: job.stage || undefined,
            message: job.stage_message || undefined,
            result: job.result,
            error: job.error_details ? JSON.stringify(job.error_details) : job.error_message || undefined,
          });

          if (job.status === "queued" || job.status === "running") {
            const unsub = api.jobs.stream(job.id, (evt) => {
              setTranslationJob((prev) => ({
                ...prev,
                status: evt.status,
                progress: evt.progress_percent ?? prev.progress,
                stage: evt.stage,
                message: evt.message,
                result: evt.result || prev.result,
                error: evt.error_details ? JSON.stringify(evt.error_details) : prev.error,
              }));
            });
            return unsub;
          }
        })
        .catch(() => {});
    }
  }, []);

  const handleStartTranslation = async () => {
    if (!currentWorkspace?.id) {
      alert("No active workspace found. Please select a workspace.");
      return;
    }

    let targetProjectId = selectedProject?.id;
    let targetVideoAssetId: string | undefined = undefined;

    setTranslationJob({
      jobId: null,
      status: "queued",
      progress: 0,
      stage: "queued",
      message: "Preparing translation...",
    });

    try {
      // 1. YouTube / Google Drive URL Ingestion
      if (videoUrl.trim()) {
        setTranslationJob((prev) => ({
          ...prev,
          status: "running",
          progress: 5,
          stage: "ingesting_url",
          message: "Ingesting remote video from URL...",
        }));

        const ingestedAsset = await api.assets.ingestUrl(currentWorkspace.id, videoUrl.trim());
        targetVideoAssetId = ingestedAsset.id;

        const proj = await api.projects.create(currentWorkspace.id, {
          title: ingestedAsset.original_filename || "Ingested Video",
          project_type: "translation",
        });
        targetProjectId = proj.id;
      }
      // 2. Local File Upload
      else if (selectedFile && selectedFile.size > 0 && !selectedProject) {
        setTranslationJob((prev) => ({
          ...prev,
          status: "running",
          progress: 5,
          stage: "uploading",
          message: "Uploading local video to storage...",
        }));

        const uploadedAsset = await api.assets.uploadFile(currentWorkspace.id, selectedFile, "video");
        targetVideoAssetId = uploadedAsset.id;

        const proj = await api.projects.create(currentWorkspace.id, {
          title: selectedFile.name,
          project_type: "translation",
        });
        targetProjectId = proj.id;
      }
      // 3. Existing Project Selection
      else if (selectedProject?.id) {
        targetProjectId = selectedProject.id;
      } else {
        alert("Please browse a local file, enter a video URL, or select an existing project.");
        setTranslationJob({ jobId: null, status: "idle", progress: 0 });
        return;
      }

      setTranslationJob((prev) => ({
        ...prev,
        status: "queued",
        progress: 10,
        stage: "submitting",
        message: "Submitting translation job...",
      }));

      const resp: any = await api.orchestration.translateProject(
        currentWorkspace.id,
        targetProjectId,
        {
          target_language: targetLanguage,
          video_asset_id: targetVideoAssetId,
          enable_subtitles: enableSubtitles,
          enable_lip_sync: enableLipSync,
          glossary_id: activeGlossaryId || undefined,
          expected_revision: 1,
          run_async: true,
          create_fork: true,
        }
      );

      const jobId = resp.id;
      if (typeof window !== "undefined") {
        window.sessionStorage.setItem("heyzen_active_translation_job_id", jobId);
      }

      setTranslationJob({
        jobId,
        status: "queued",
        progress: 15,
        stage: "queued",
        message: "Translation job queued",
      });

      api.jobs.stream(
        jobId,
        (evt) => {
          setTranslationJob((prev) => ({
            ...prev,
            status: evt.status,
            progress: evt.progress_percent ?? prev.progress,
            stage: evt.stage,
            message: evt.message,
            result: evt.result || prev.result,
            error: evt.error_details
              ? typeof evt.error_details === "string"
                ? evt.error_details
                : JSON.stringify(evt.error_details)
              : prev.error,
          }));
        },
        () => {
          // Stream complete/fallback
        }
      );
    } catch (err: any) {
      setTranslationJob({
        jobId: null,
        status: "failed",
        progress: 0,
        error: err?.message || "Failed to start translation",
      });
    }
  };

  // Escape key listener to close Project Picker modal
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setShowProjectPicker(false);
        setIsProjectFilterOpen(false);
      }
    };
    if (showProjectPicker) {
      window.addEventListener("keydown", handleKeyDown);
    }
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [showProjectPicker]);

  const { currentWorkspace } = useAuth();
  const [existingProjects, setExistingProjects] = useState<ExistingProjectItem[]>(EXISTING_PROJECTS_DATA);

  useEffect(() => {
    if (!currentWorkspace?.id) return;
    api.projects
      .list(currentWorkspace.id)
      .then((res) => {
        if (res && res.length > 0) {
          setExistingProjects(
            res.map((p) => ({
              id: p.id,
              title: p.title || "Untitled Video",
              status: p.status === "ready" ? "Ready" : "Draft",
              time: new Date(p.created_at).toLocaleDateString(),
              type:
                p.project_type === "translation"
                  ? "Translations"
                  : "Avatar Video",
              image:
                "https://images.unsplash.com/photo-1534528741775-53994a69daeb?q=80&w=700&auto=format&fit=crop",
            }))
          );
        }
      })
      .catch(() => {});
  }, [currentWorkspace?.id]);

  // Filtered Existing Projects list
  const filteredExistingProjects = existingProjects.filter((p) => {
    const matchesSearch =
      !projectSearchQuery.trim() ||
      p.title.toLowerCase().includes(projectSearchQuery.toLowerCase()) ||
      p.type.toLowerCase().includes(projectSearchQuery.toLowerCase());
    const matchesType =
      selectedProjectType === "all" || p.type === selectedProjectType;
    return matchesSearch && matchesType;
  });

  // Brand Glossary dropdown state (local fallback if not controlled)
  const [localGlossaries, setLocalGlossaries] = useState<GlossaryOption[]>([]);
  const [selectedGlossary, setSelectedGlossary] = useState(
    propSelectedGlossary || "Brand Glossary"
  );
  const [isGlossaryDropdownOpen, setIsGlossaryDropdownOpen] = useState(false);
  const [showCreateGlossaryModal, setShowCreateGlossaryModal] = useState(false);
  const [newGlossaryName, setNewGlossaryName] = useState("");

  const glossaries = propGlossaries && propGlossaries.length > 0 ? propGlossaries : localGlossaries;

  const currentSelectedGlossaryName =
    (propSelectedGlossaryId &&
      glossaries.find((g) => g.id === propSelectedGlossaryId)?.name) ||
    propSelectedGlossary ||
    selectedGlossary ||
    (glossaries.length > 0 ? glossaries[0].name : "Brand Glossary");

  const activeGlossaryId =
    propSelectedGlossaryId ||
    glossaries.find((g) => g.name === currentSelectedGlossaryName)?.id ||
    (glossaries.length > 0 ? glossaries[0].id : null);

  useEffect(() => {
    if (!currentWorkspace?.id) return;
    api.brandGlossaries
      .list(currentWorkspace.id)
      .then((res) => {
        if (Array.isArray(res) && res.length > 0) {
          setLocalGlossaries(res.map((g: any) => ({ id: g.id, name: g.name })));
          if (!propSelectedGlossary && !selectedGlossary) {
            setSelectedGlossary(res[0].name);
          }
        }
      })
      .catch(() => {});
  }, [currentWorkspace?.id, propSelectedGlossary, selectedGlossary]);

  useEffect(() => {
    if (!activeGlossaryId || !currentWorkspace?.id) return;
    api.brandGlossaries
      .listRules(activeGlossaryId, currentWorkspace.id)
      .then((rules) => {
        if (Array.isArray(rules)) {
          const pron: RuleItem[] = [];
          const force: RuleItem[] = [];
          const dont: WordItem[] = [];

          rules.forEach((r: any) => {
            if (r.rule_type === "pronunciation") {
              pron.push({
                id: r.id,
                originalWord: r.term,
                behavior: r.phonetic_spelling || "Phonetic standard",
              });
            } else if (r.rule_type === "force_translate") {
              force.push({
                id: r.id,
                originalWord: r.term,
                behavior: r.replacement || "Force translate rule",
              });
            } else {
              dont.push({
                id: r.id,
                word: r.term,
              });
            }
          });

          setPronunciationRules(pron);
          setForceTranslateRules(force);
          setDontTranslateWords(dont);
        }
      })
      .catch(() => {});
  }, [activeGlossaryId, currentWorkspace?.id]);

  useEffect(() => {
    if (propSelectedGlossary) {
      setSelectedGlossary(propSelectedGlossary);
    }
  }, [propSelectedGlossary]);

  const glossaryDropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        glossaryDropdownRef.current &&
        !glossaryDropdownRef.current.contains(event.target as Node)
      ) {
        setIsGlossaryDropdownOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // 1. Pronunciation State
  const [pronunciationRules, setPronunciationRules] = useState<RuleItem[]>([]);
  const [pronunciationSearch, setPronunciationSearch] = useState("");
  const [isPronunciationSearchOpen, setIsPronunciationSearchOpen] =
    useState(false);
  const [isAddingPronunciation, setIsAddingPronunciation] = useState(false);
  const [draftPronunciationWord, setDraftPronunciationWord] = useState("");
  const [draftPronunciationBehavior, setDraftPronunciationBehavior] =
    useState("");

  // 2. Force Translate State
  const [forceTranslateRules, setForceTranslateRules] = useState<RuleItem[]>(
    []
  );
  const [forceTranslateSearch, setForceTranslateSearch] = useState("");
  const [isForceTranslateSearchOpen, setIsForceTranslateSearchOpen] =
    useState(false);
  const [isAddingForceTranslate, setIsAddingForceTranslate] = useState(false);
  const [draftForceTranslateWord, setDraftForceTranslateWord] = useState("");
  const [draftForceTranslateBehavior, setDraftForceTranslateBehavior] =
    useState("");

  // 3. Don't Translate State
  const [dontTranslateWords, setDontTranslateWords] = useState<WordItem[]>([]);
  const [dontTranslateSearch, setDontTranslateSearch] = useState("");
  const [isDontTranslateSearchOpen, setIsDontTranslateSearchOpen] =
    useState(false);
  const [isAddingDontTranslate, setIsAddingDontTranslate] = useState(false);
  const [draftDontTranslateWord, setDraftDontTranslateWord] = useState("");

  const fileInputRef = useRef<HTMLInputElement>(null);
  const pronunciationCsvRef = useRef<HTMLInputElement>(null);
  const forceTranslateCsvRef = useRef<HTMLInputElement>(null);
  const dontTranslateCsvRef = useRef<HTMLInputElement>(null);

  // File Upload Handlers for Translate Video
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setSelectedFile(e.dataTransfer.files[0]);
    }
  };

  // --- Inline Save Handlers ---
  const handleSavePronunciation = async () => {
    if (!draftPronunciationWord.trim()) return;
    try {
      let ruleId = typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : "pron_rule";
      if (activeGlossaryId && currentWorkspace?.id) {
        const rule = await api.brandGlossaries.createRule(
          activeGlossaryId,
          {
            term: draftPronunciationWord.trim(),
            phonetic_spelling: draftPronunciationBehavior.trim() || "Phonetic standard",
            rule_type: "pronunciation",
          },
          currentWorkspace.id
        );
        ruleId = rule.id;
      }
      const newRule: RuleItem = {
        id: ruleId,
        originalWord: draftPronunciationWord.trim(),
        behavior: draftPronunciationBehavior.trim() || "Phonetic standard",
      };
      setPronunciationRules([newRule, ...pronunciationRules]);
      setDraftPronunciationWord("");
      setDraftPronunciationBehavior("");
      setIsAddingPronunciation(false);
    } catch (err: any) {
      alert(err?.message || "Failed to add pronunciation rule");
    }
  };

  const handleCancelPronunciation = () => {
    setDraftPronunciationWord("");
    setDraftPronunciationBehavior("");
    setIsAddingPronunciation(false);
  };

  const handleSaveForceTranslate = async () => {
    if (!draftForceTranslateWord.trim()) return;
    try {
      let ruleId = typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : "force_rule";
      if (activeGlossaryId && currentWorkspace?.id) {
        const rule = await api.brandGlossaries.createRule(
          activeGlossaryId,
          {
            term: draftForceTranslateWord.trim(),
            replacement: draftForceTranslateBehavior.trim() || "Force translate rule",
            rule_type: "force_translate",
          },
          currentWorkspace.id
        );
        ruleId = rule.id;
      }
      const newRule: RuleItem = {
        id: ruleId,
        originalWord: draftForceTranslateWord.trim(),
        behavior: draftForceTranslateBehavior.trim() || "Force translate rule",
      };
      setForceTranslateRules([newRule, ...forceTranslateRules]);
      setDraftForceTranslateWord("");
      setDraftForceTranslateBehavior("");
      setIsAddingForceTranslate(false);
    } catch (err: any) {
      alert(err?.message || "Failed to add force translate rule");
    }
  };

  const handleCancelForceTranslate = () => {
    setDraftForceTranslateWord("");
    setDraftForceTranslateBehavior("");
    setIsAddingForceTranslate(false);
  };

  const handleSaveDontTranslate = async () => {
    if (!draftDontTranslateWord.trim()) return;
    try {
      let ruleId = typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : "dont_rule";
      if (activeGlossaryId && currentWorkspace?.id) {
        const rule = await api.brandGlossaries.createRule(
          activeGlossaryId,
          {
            term: draftDontTranslateWord.trim(),
            rule_type: "do_not_translate",
          },
          currentWorkspace.id
        );
        ruleId = rule.id;
      }
      const newWord: WordItem = {
        id: ruleId,
        word: draftDontTranslateWord.trim(),
      };
      setDontTranslateWords([newWord, ...dontTranslateWords]);
      setDraftDontTranslateWord("");
      setIsAddingDontTranslate(false);
    } catch (err: any) {
      alert(err?.message || "Failed to add do not translate rule");
    }
  };

  const handleCancelDontTranslate = () => {
    setDraftDontTranslateWord("");
    setIsAddingDontTranslate(false);
  };

  // Create New Glossary Handler
  const handleCreateNewGlossary = async (e: React.FormEvent) => {
    e.preventDefault();
    const name = newGlossaryName.trim() || "Brand Glossary";
    if (currentWorkspace?.id) {
      try {
        const created = await api.brandGlossaries.create(
          { name },
          currentWorkspace.id
        );
        const newGlossary: GlossaryOption = { id: created.id, name: created.name };
        setLocalGlossaries((prev) => [newGlossary, ...prev]);
        setSelectedGlossary(name);

        if (onSelectGlossary) {
          onSelectGlossary(name);
        }

        setNewGlossaryName("");
        setShowCreateGlossaryModal(false);

        if (onCreateGlossary) {
          onCreateGlossary(name);
        } else if (onNavigateCreateGlossary) {
          onNavigateCreateGlossary(name);
        }
        return;
      } catch (err: any) {
        alert(err?.message || "Failed to create glossary");
      }
    }
  };

  // Delete Handlers
  const handleDeletePronunciation = async (id: string) => {
    if (activeGlossaryId && currentWorkspace?.id) {
      try {
        await api.brandGlossaries.deleteRule(activeGlossaryId, id, currentWorkspace.id);
      } catch (err) {
        console.error("Failed to delete rule:", err);
      }
    }
    setPronunciationRules(pronunciationRules.filter((r) => r.id !== id));
  };

  const handleDeleteForceTranslate = async (id: string) => {
    if (activeGlossaryId && currentWorkspace?.id) {
      try {
        await api.brandGlossaries.deleteRule(activeGlossaryId, id, currentWorkspace.id);
      } catch (err) {
        console.error("Failed to delete rule:", err);
      }
    }
    setForceTranslateRules(forceTranslateRules.filter((r) => r.id !== id));
  };

  const handleDeleteDontTranslate = async (id: string) => {
    if (activeGlossaryId && currentWorkspace?.id) {
      try {
        await api.brandGlossaries.deleteRule(activeGlossaryId, id, currentWorkspace.id);
      } catch (err) {
        console.error("Failed to delete rule:", err);
      }
    }
    setDontTranslateWords(dontTranslateWords.filter((w) => w.id !== id));
  };

  // CSV Upload Parsers
  const handlePronunciationCsv = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      const text = event.target?.result as string;
      if (!text) return;
      const lines = text.split(/\r?\n/).filter((l) => l.trim().length > 0);
      const items: RuleItem[] = [];
      lines.forEach((line, idx) => {
        if (
          idx === 0 &&
          (line.toLowerCase().includes("word") ||
            line.toLowerCase().includes("original"))
        )
          return;
        const parts = line.split(",").map((p) => p.trim().replace(/^"|"$/g, ""));
        if (parts[0]) {
          items.push({
            id: typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : `rule_${idx}`,
            originalWord: parts[0],
            behavior: parts[1] || "Uploaded pronunciation",
          });
        }
      });
      if (items.length > 0) {
        setPronunciationRules((prev) => [...items, ...prev]);
      }
    };
    reader.readAsText(file);
    e.target.value = "";
  };

  const handleForceTranslateCsv = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      const text = event.target?.result as string;
      if (!text) return;
      const lines = text.split(/\r?\n/).filter((l) => l.trim().length > 0);
      const items: RuleItem[] = [];
      lines.forEach((line, idx) => {
        if (
          idx === 0 &&
          (line.toLowerCase().includes("word") ||
            line.toLowerCase().includes("original"))
        )
          return;
        const parts = line.split(",").map((p) => p.trim().replace(/^"|"$/g, ""));
        if (parts[0]) {
          items.push({
            id: typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : `rule_${idx}`,
            originalWord: parts[0],
            behavior: parts[1] || "Force translate rule",
          });
        }
      });
      if (items.length > 0) {
        setForceTranslateRules((prev) => [...items, ...prev]);
      }
    };
    reader.readAsText(file);
    e.target.value = "";
  };

  const handleDontTranslateCsv = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      const text = event.target?.result as string;
      if (!text) return;
      const lines = text.split(/\r?\n/).filter((l) => l.trim().length > 0);
      const items: WordItem[] = [];
      lines.forEach((line, idx) => {
        if (idx === 0 && line.toLowerCase().includes("word")) return;
        const parts = line.split(",").map((p) => p.trim().replace(/^"|"$/g, ""));
        if (parts[0]) {
          items.push({
            id: typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : `word_${idx}`,
            word: parts[0],
          });
        }
      });
      if (items.length > 0) {
        setDontTranslateWords((prev) => [...items, ...prev]);
      }
    };
    reader.readAsText(file);
    e.target.value = "";
  };

  // Filtered lists
  const filteredPronunciationRules = pronunciationRules.filter(
    (r) =>
      !pronunciationSearch.trim() ||
      r.originalWord
        .toLowerCase()
        .includes(pronunciationSearch.toLowerCase()) ||
      r.behavior.toLowerCase().includes(pronunciationSearch.toLowerCase())
  );

  const filteredForceTranslateRules = forceTranslateRules.filter(
    (r) =>
      !forceTranslateSearch.trim() ||
      r.originalWord
        .toLowerCase()
        .includes(forceTranslateSearch.toLowerCase()) ||
      r.behavior.toLowerCase().includes(forceTranslateSearch.toLowerCase())
  );

  const filteredDontTranslateWords = dontTranslateWords.filter(
    (w) =>
      !dontTranslateSearch.trim() ||
      w.word.toLowerCase().includes(dontTranslateSearch.toLowerCase())
  );

  return (
    <div
      id="translate-videos-view"
      data-testid="translate-videos-view"
      className={`flex-1 h-screen overflow-y-auto ${isLight ? "bg-slate-50 text-slate-900" : "bg-[#07090e] text-slate-100"} flex flex-col font-sans select-none relative scrollbar-thin`}
    >
      {/* 1. TOP BAR */}
      <header className="w-full px-6 sm:px-10 pt-6 pb-2 flex items-center justify-between z-20">
        <div>
          {onBack && (
            <button
              type="button"
              onClick={onBack}
              title="Back to Apps"
              className={`w-9 h-9 rounded-full border ${isLight ? "border-slate-200 bg-white hover:bg-slate-100 text-slate-700 hover:text-slate-900" : "border-[#1b2940] bg-[#121828] hover:bg-[#18233c] text-slate-300 hover:text-white"} flex items-center justify-center transition-colors shadow-xs cursor-pointer`}
            >
              <ArrowLeft size={16} />
            </button>
          )}
        </div>

        <div>
          <AskRhysWidget variant="banner" />
        </div>
      </header>

      {/* 2. CENTERED HEADER & TOP SEGMENTED TABS */}
      <div className="w-full max-w-4xl mx-auto px-6 text-center pt-2 pb-6">
        <h1 className={`text-2xl sm:text-3xl font-extrabold ${isLight ? "text-slate-900" : "text-white"} tracking-tight leading-tight`}>
          Translate your videos in 175+ languages
        </h1>

        {/* Segmented Control Tabs */}
        <div className="flex justify-center mt-5">
          <div className={`${isLight ? "bg-slate-200/80 border-slate-300/80" : "bg-[#0b111e] border-[#1b2940]"} p-1 rounded-full inline-flex items-center gap-1 border shadow-xs`}>
            <button
              type="button"
              onClick={() => setActiveTab("translate")}
              className={`px-5 py-1.5 rounded-full text-xs font-semibold transition-all cursor-pointer ${
                activeTab === "translate"
                  ? isLight
                    ? "bg-white text-slate-900 shadow-sm border border-slate-200 font-bold"
                    : "bg-[#18233c] text-white shadow-xs border border-[#2b3a5d]/50"
                  : isLight
                  ? "text-slate-600 hover:text-slate-900 hover:bg-white/50"
                  : "text-slate-400 hover:text-white hover:bg-[#101828]"
              }`}
            >
              Translate
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("glossary")}
              className={`px-5 py-1.5 rounded-full text-xs font-semibold transition-all cursor-pointer ${
                activeTab === "glossary"
                  ? isLight
                    ? "bg-white text-slate-900 shadow-sm border border-slate-200 font-bold"
                    : "bg-[#18233c] text-white shadow-xs border border-[#2b3a5d]/50"
                  : isLight
                  ? "text-slate-600 hover:text-slate-900 hover:bg-white/50"
                  : "text-slate-400 hover:text-white hover:bg-[#101828]"
              }`}
            >
              Glossary & Rules
            </button>
          </div>
        </div>
      </div>

      {/* 3. MAIN CONTENT CONTAINER */}
      <main className="max-w-[820px] w-full mx-auto px-6 pb-20 flex-1">
        {activeTab === "translate" ? (
          /* ================= TRANSLATE TAB VIEW ================= */
          <div className={`${isLight ? "bg-white border-slate-200 text-slate-900 shadow-xl" : "bg-[#0b111e] border-[#1b2940] text-slate-100 shadow-xl"} rounded-3xl border p-8 sm:p-10 transition-all`}>
            {/* Hidden File Input */}
            <input
              ref={fileInputRef}
              type="file"
              accept="video/mp4,video/quicktime,video/webm,audio/*"
              onChange={handleFileChange}
              className="hidden"
            />

            {/* Upload / Drop Area */}
            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`relative rounded-2xl border-2 border-dashed ${
                isDragging
                  ? "border-cyan-500 bg-cyan-500/10"
                  : selectedFile
                  ? "border-emerald-500/50 bg-emerald-500/10"
                  : isLight
                  ? "border-slate-300 hover:border-blue-500 bg-slate-50/80"
                  : "border-[#1b2940] hover:border-slate-600 bg-[#07090e]"
              } p-10 sm:p-12 flex flex-col items-center justify-center text-center transition-all duration-200 cursor-pointer group`}
            >
              {selectedFile ? (
                <div className="space-y-3 flex flex-col items-center">
                  <div className={`w-14 h-14 rounded-2xl ${isLight ? "bg-emerald-100 border border-emerald-300 text-emerald-600" : "bg-emerald-950/80 border border-emerald-500/30 text-emerald-400"} flex items-center justify-center shadow-xs`}>
                    <CheckCircle2 size={28} />
                  </div>
                  <div className={`inline-flex items-center gap-2 text-sm font-bold ${isLight ? "text-slate-900 bg-slate-100 border-slate-200" : "text-white bg-[#121828] border-[#1b2940]"} px-4 py-2 rounded-full border shadow-xs`}>
                    <FileVideo size={16} className={isLight ? "text-blue-600" : "text-cyan-400"} />
                    <span>{selectedProject ? `${selectedProject.title}.mp4` : selectedFile.name}</span>
                  </div>
                  <p className={`text-xs ${isLight ? "text-slate-500" : "text-slate-400"}`}>
                    {selectedFile.size > 0
                      ? `${(selectedFile.size / (1024 * 1024)).toFixed(1)} MB`
                      : "14.2 MB"}{" "}
                    • Click to change file
                  </p>
                </div>
              ) : (
                <>
                  {/* Upload Cloud Icon */}
                  <div className={`w-12 h-12 rounded-full ${isLight ? "bg-slate-100 border-slate-300 text-slate-600" : "bg-[#121828] border-[#1b2940] text-slate-400 group-hover:text-cyan-400"} border flex items-center justify-center transition-colors mb-3`}>
                    <Upload size={22} />
                  </div>

                  {/* Text Prompt */}
                  <h3 className={`text-base font-semibold ${isLight ? "text-slate-900" : "text-white"}`}>
                    Drop your videos here to translate
                  </h3>

                  <p className={`text-xs ${isLight ? "text-slate-600" : "text-slate-400"} mt-1 max-w-md leading-relaxed font-normal`}>
                    Your Free plan supports videos up to 1 minutes in length.
                    <br />
                    Videos can be up to 5 GB in MP4, MOV, or WEBM format
                  </p>

                  {/* Buttons */}
                  <div className="flex flex-wrap items-center justify-center gap-3 mt-6">
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        fileInputRef.current?.click();
                      }}
                      className="bg-gradient-to-r from-blue-600 to-cyan-500 hover:from-blue-500 hover:to-cyan-400 text-white text-xs font-semibold px-5 py-2.5 rounded-full shadow-md hover:shadow-cyan-500/20 transition-all cursor-pointer"
                    >
                      Browse local files
                    </button>

                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        setShowProjectPicker(true);
                      }}
                      className={`${isLight ? "bg-slate-100 hover:bg-slate-200 text-slate-800 border-slate-300" : "bg-[#121828] hover:bg-[#18233c] text-slate-200 hover:text-white border-[#1b2940]"} text-xs font-semibold px-5 py-2.5 rounded-full border shadow-xs transition-all cursor-pointer`}
                    >
                      Select an existing project
                    </button>
                  </div>
                </>
              )}
            </div>

            {/* Divider with Centered "OR" */}
            <div className="relative my-7 flex items-center justify-center">
              <div className="absolute inset-0 flex items-center">
                <div className={`w-full border-t ${isLight ? "border-slate-200" : "border-[#1b2940]"}`}></div>
              </div>
              <span className={`relative ${isLight ? "bg-white text-slate-400" : "bg-[#0b111e] text-slate-500"} px-3 text-[11px] font-semibold uppercase tracking-wider`}>
                OR
              </span>
            </div>

            {/* URL Input Section */}
            <div className="relative">
              <LinkIcon
                size={16}
                className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none"
              />
              <input
                type="url"
                value={videoUrl}
                onChange={(e) => setVideoUrl(e.target.value)}
                placeholder="Paste a YouTube or Google Drive URL"
                className={`w-full ${
                  isLight
                    ? "bg-slate-50 border-slate-200 text-slate-900 placeholder:text-slate-400 focus:bg-white focus:border-blue-500"
                    : "bg-[#121828] border-[#1b2940] text-slate-100 placeholder:text-slate-500 focus:bg-[#151f33] focus:border-cyan-500/60"
                } border rounded-full pl-11 pr-4 py-3 text-xs focus:outline-none transition-all shadow-inner`}
              />
            </div>
            {/* Target Language Selection, Subtitles, Lip-Sync & Translation Action */}
            <div className={`mt-8 pt-6 border-t ${isLight ? "border-slate-200" : "border-[#1b2940]"} flex flex-col md:flex-row items-center justify-between gap-4`}>
              <div className="flex flex-wrap items-center gap-4 w-full md:w-auto">
                <div className="flex items-center gap-2">
                  <span className={`text-xs font-semibold ${isLight ? "text-slate-700" : "text-slate-300"}`}>Language:</span>
                  <select
                    value={targetLanguage}
                    onChange={(e) => setTargetLanguage(e.target.value)}
                    className={`${isLight ? "bg-slate-50 border-slate-200 text-slate-900 focus:border-blue-500" : "bg-[#121828] border-[#1b2940] text-white focus:border-cyan-500"} border rounded-xl px-3 py-2 text-xs focus:outline-none cursor-pointer`}
                  >
                    <option value="es">Spanish (es)</option>
                    <option value="fr">French (fr)</option>
                    <option value="de">German (de)</option>
                    <option value="it">Italian (it)</option>
                    <option value="pt">Portuguese (pt)</option>
                    <option value="en">English (en)</option>
                  </select>
                </div>

                <label className={`flex items-center gap-2 text-xs ${isLight ? "text-slate-700" : "text-slate-300"} cursor-pointer select-none`}>
                  <input
                    type="checkbox"
                    checked={enableSubtitles}
                    onChange={(e) => setEnableSubtitles(e.target.checked)}
                    className={`rounded ${isLight ? "bg-white border-slate-300 text-blue-600" : "bg-[#121828] border-[#1b2940] text-cyan-500"} focus:ring-0 cursor-pointer`}
                  />
                  <span>Subtitles</span>
                </label>

                <label className={`flex items-center gap-2 text-xs ${isLight ? "text-slate-700" : "text-slate-300"} cursor-pointer select-none`} title="Uses Wav2Lip CPU development fallback if neural CUDA is unavailable">
                  <input
                    type="checkbox"
                    checked={enableLipSync}
                    onChange={(e) => setEnableLipSync(e.target.checked)}
                    className={`rounded ${isLight ? "bg-white border-slate-300 text-blue-600" : "bg-[#121828] border-[#1b2940] text-cyan-500"} focus:ring-0 cursor-pointer`}
                  />
                  <span>Lip-Sync (CPU)</span>
                </label>
              </div>

              <button
                type="button"
                onClick={handleStartTranslation}
                disabled={translationJob.status === "running" || translationJob.status === "queued"}
                className="w-full md:w-auto bg-gradient-to-r from-blue-600 to-cyan-500 hover:from-blue-500 hover:to-cyan-400 disabled:opacity-50 text-white text-xs font-semibold px-6 py-2.5 rounded-full shadow-md hover:shadow-cyan-500/20 transition-all cursor-pointer flex items-center justify-center gap-2"
              >
                {translationJob.status === "running" || translationJob.status === "queued" ? (
                  <>
                    <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                    <span>Translating...</span>
                  </>
                ) : (
                  <span>Translate Video</span>
                )}
              </button>
            </div>

            {/* Translation Progress & Real Output Card */}
            {translationJob.status !== "idle" && (
              <div className={`mt-6 p-5 rounded-2xl ${isLight ? "bg-slate-50 border-slate-200" : "bg-[#121828] border-[#1b2940]"} border space-y-4`}>
                <div className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <span className={`font-semibold ${isLight ? "text-slate-900" : "text-white"}`}>Status:</span>
                    <span className={`capitalize font-mono ${isLight ? "text-blue-600" : "text-cyan-400"}`}>
                      {translationJob.status}
                    </span>
                    {translationJob.message && (
                      <span className={isLight ? "text-slate-500" : "text-slate-400"}>• {translationJob.message}</span>
                    )}
                  </div>
                  <span className={`font-mono ${isLight ? "text-slate-700" : "text-slate-300"}`}>
                    {translationJob.progress}%
                  </span>
                </div>

                <div className={`w-full h-1.5 ${isLight ? "bg-slate-200" : "bg-[#07090e]"} rounded-full overflow-hidden`}>
                  <div
                    className="h-full bg-gradient-to-r from-blue-500 to-cyan-400 transition-all duration-300"
                    style={{ width: `${Math.min(100, Math.max(0, translationJob.progress))}%` }}
                  ></div>
                </div>

                {/* Succeeded Result Card with Video Player */}
                {(translationJob.status === "succeeded" || translationJob.status === "completed") && (
                  <div className="pt-2 space-y-4">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-emerald-500 font-semibold flex items-center gap-1.5">
                        <CheckCircle2 size={16} />
                        Translation complete!
                        {translationJob.result?.target_language && (
                          <span className={`px-2 py-0.5 rounded-full ${isLight ? "bg-emerald-50 border-emerald-200 text-emerald-700" : "bg-emerald-950 border border-emerald-500/30 text-emerald-300"} uppercase font-mono text-[10px]`}>
                            {translationJob.result.target_language}
                          </span>
                        )}
                        {translationJob.result?.duration && (
                          <span className={isLight ? "text-slate-500" : "text-slate-400"}>
                            ({translationJob.result.duration}s)
                          </span>
                        )}
                      </span>
                    </div>

                    {/* Real Video Player */}
                    {translationJob.result?.video_url && (
                      <div className={`rounded-xl overflow-hidden border ${isLight ? "border-slate-200 bg-black" : "border-[#1b2940] bg-black"} shadow-lg`}>
                        <video
                          controls
                          playsInline
                          src={translationJob.result.video_url}
                          className="w-full max-h-[340px] object-contain mx-auto"
                        />
                      </div>
                    )}

                    {/* Translated Text Preview */}
                    {translationJob.result?.translated_text && (
                      <div className={`p-3 ${isLight ? "bg-slate-100 border-slate-200 text-slate-800" : "bg-[#07090e] border-[#1b2940] text-slate-300"} rounded-xl border text-xs space-y-1`}>
                        <div className={`text-[11px] font-semibold ${isLight ? "text-blue-600" : "text-cyan-400"} uppercase tracking-wider`}>
                          Translated Script ({translationJob.result.target_language || "Target"}):
                        </div>
                        <p className="leading-relaxed">{translationJob.result.translated_text}</p>
                      </div>
                    )}

                    {/* Action Bar: Download MP4, Download Subtitles, Open in Studio */}
                    <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
                      <div className="flex items-center gap-2">
                        {translationJob.result?.video_url && (
                          <a
                            href={translationJob.result.video_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            download={`translated_${translationJob.result.target_language || "video"}.mp4`}
                            className={`px-3.5 py-1.5 ${isLight ? "bg-slate-100 hover:bg-slate-200 text-slate-800 border-slate-200" : "bg-[#18233c] hover:bg-[#202e4f] text-slate-200 hover:text-white border-[#2b3a5d]"} rounded-full text-xs font-semibold border transition-all flex items-center gap-1.5 shadow-xs`}
                          >
                            <span>Download MP4</span>
                          </a>
                        )}

                        {translationJob.result?.subtitle_url && (
                          <a
                            href={translationJob.result.subtitle_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            download={`translated_${translationJob.result.target_language || "video"}.vtt`}
                            className={`px-3.5 py-1.5 ${isLight ? "bg-slate-100 hover:bg-slate-200 text-slate-800 border-slate-200" : "bg-[#18233c] hover:bg-[#202e4f] text-slate-200 hover:text-white border-[#2b3a5d]"} rounded-full text-xs font-semibold border transition-all flex items-center gap-1.5 shadow-xs`}
                          >
                            <span>Download Subtitles (VTT)</span>
                          </a>
                        )}
                      </div>

                      {onOpenStudio && translationJob.result?.project_id && (
                        <button
                          type="button"
                          onClick={() => onOpenStudio(translationJob.result.project_id)}
                          className="px-5 py-2 bg-gradient-to-r from-blue-600 to-cyan-500 hover:from-blue-500 hover:to-cyan-400 text-white font-semibold rounded-full shadow-md transition-all text-xs cursor-pointer"
                        >
                          Open in Studio
                        </button>
                      )}
                    </div>
                  </div>
                )}

                {/* Failed Error State */}
                {translationJob.status === "failed" && (
                  <div className={`pt-2 text-xs ${isLight ? "text-rose-700 bg-rose-50 border-rose-200" : "text-red-400 bg-red-950/30 border-red-900/50"} font-medium border p-3 rounded-xl`}>
                    Translation failed: {translationJob.error || "Unknown error"}
                  </div>
                )}
              </div>
            )}
          </div>
        ) : (
          /* ================= GLOSSARY & RULES TAB VIEW ================= */
          <div className="space-y-6">
            {/* Top Row: Sub-Tabs & Brand Glossary Dropdown */}
            <div className="flex items-center justify-between border-b border-[#1b2940] pb-0">
              {/* Inner Tabs: Pronunciation / Force Translate */}
              <div className="flex items-center gap-6">
                <button
                  type="button"
                  onClick={() => setGlossarySubTab("pronunciation")}
                  className={`pb-3 text-sm font-semibold transition-all relative cursor-pointer ${
                    glossarySubTab === "pronunciation"
                      ? "text-white font-bold"
                      : "text-slate-400 hover:text-slate-200 font-medium"
                  }`}
                >
                  <span>Pronunciation</span>
                  {glossarySubTab === "pronunciation" && (
                    <div className="absolute -bottom-[1px] left-0 right-0 h-[2.5px] bg-cyan-400 rounded-full"></div>
                  )}
                </button>

                <button
                  type="button"
                  onClick={() => setGlossarySubTab("force_translate")}
                  className={`pb-3 text-sm font-semibold transition-all relative cursor-pointer ${
                    glossarySubTab === "force_translate"
                      ? "text-white font-bold"
                      : "text-slate-400 hover:text-slate-200 font-medium"
                  }`}
                >
                  <span>Force Translate</span>
                  {glossarySubTab === "force_translate" && (
                    <div className="absolute -bottom-[1px] left-0 right-0 h-[2.5px] bg-cyan-400 rounded-full"></div>
                  )}
                </button>
              </div>

              {/* Brand Glossary Dropdown (Persistent on right) */}
              <div className="relative pb-2" ref={glossaryDropdownRef}>
                <button
                  type="button"
                  onClick={() =>
                    setIsGlossaryDropdownOpen(!isGlossaryDropdownOpen)
                  }
                  className="bg-[#121828] hover:bg-[#18233c] text-slate-200 border border-[#1b2940] text-xs font-semibold px-4 py-1.5 rounded-full shadow-xs flex items-center gap-2 transition-all cursor-pointer"
                >
                  <span>{currentSelectedGlossaryName}</span>
                  <ChevronDown
                    size={13}
                    className={`text-slate-400 transition-transform duration-200 ${
                      isGlossaryDropdownOpen ? "rotate-180" : ""
                    }`}
                  />
                </button>

                {isGlossaryDropdownOpen && (
                  <div className="absolute right-0 top-full mt-1.5 w-60 bg-[#0b111e] border border-[#1b2940] rounded-2xl shadow-2xl p-1.5 z-40 text-white animate-in fade-in zoom-in-95 duration-100">
                    <div className="space-y-0.5">
                      {glossaries.map((glossary) => {
                        const isSelected =
                          (propSelectedGlossaryId &&
                            glossary.id === propSelectedGlossaryId) ||
                          currentSelectedGlossaryName === glossary.name;
                        return (
                          <button
                            key={glossary.id}
                            type="button"
                            onClick={() => {
                              setSelectedGlossary(glossary.name);
                              if (onSelectGlossary) {
                                onSelectGlossary(glossary.name);
                              }
                              setIsGlossaryDropdownOpen(false);
                              if (onSelectAndOpenGlossary) {
                                onSelectAndOpenGlossary(glossary);
                              } else if (onNavigateCreateGlossary) {
                                onNavigateCreateGlossary(glossary.name);
                              }
                            }}
                            className={`w-full text-left px-3.5 py-2 text-xs font-medium rounded-xl transition-colors flex items-center justify-between cursor-pointer ${
                              isSelected
                                ? "bg-[#18233c] text-cyan-300 font-bold border border-[#2b3a5d]/60"
                                : "text-slate-300 hover:bg-[#121828] hover:text-white"
                            }`}
                          >
                            <span>{glossary.name}</span>
                            {isSelected && (
                              <Check size={14} className="text-cyan-400" />
                            )}
                          </button>
                        );
                      })}
                    </div>

                    {/* Divider */}
                    <div className="border-t border-[#1b2940] my-1"></div>

                    {/* + Create New Brand Glossary */}
                    <button
                      type="button"
                      onClick={() => {
                        setIsGlossaryDropdownOpen(false);
                        setShowCreateGlossaryModal(true);
                      }}
                      className="w-full text-left px-3.5 py-2 text-xs font-semibold text-cyan-400 hover:text-cyan-300 hover:bg-cyan-500/10 rounded-xl transition-colors flex items-center gap-2 cursor-pointer"
                    >
                      <Plus size={14} className="text-cyan-400" />
                      <span>Create New Brand Glossary</span>
                    </button>
                  </div>
                )}
              </div>
            </div>            {/* Sub-Tab 1: PRONUNCIATION */}
            {glossarySubTab === "pronunciation" && (
              <div className="space-y-4 pt-1">
                {/* Hidden CSV Input for Pronunciation */}
                <input
                  ref={pronunciationCsvRef}
                  type="file"
                  accept=".csv"
                  onChange={handlePronunciationCsv}
                  className="hidden"
                />

                {/* Pronunciation Action Row */}
                <div className="flex items-center justify-between gap-3">
                  {/* Left: Search button / input */}
                  <div className="flex items-center gap-2">
                    {isPronunciationSearchOpen ? (
                      <div className="flex items-center bg-[#121828] border border-[#1b2940] rounded-full pl-3 pr-2 py-1.5 shadow-inner">
                        <Search size={14} className="text-slate-400 mr-2" />
                        <input
                          type="text"
                          value={pronunciationSearch}
                          onChange={(e) =>
                            setPronunciationSearch(e.target.value)
                          }
                          placeholder="Search pronunciations..."
                          autoFocus
                          className="bg-transparent border-none text-xs text-slate-100 placeholder:text-slate-500 focus:outline-none w-36 sm:w-48"
                        />
                        <button
                          type="button"
                          onClick={() => {
                            setPronunciationSearch("");
                            setIsPronunciationSearchOpen(false);
                          }}
                          className="text-slate-400 hover:text-slate-200 p-0.5"
                        >
                          <X size={13} />
                        </button>
                      </div>
                    ) : (
                      <button
                        type="button"
                        onClick={() => setIsPronunciationSearchOpen(true)}
                        title="Search pronunciation rules"
                        className="w-9 h-9 rounded-full border border-[#1b2940] bg-[#121828] hover:bg-[#18233c] flex items-center justify-center text-slate-300 hover:text-white transition-colors shadow-xs cursor-pointer"
                      >
                        <Search size={15} />
                      </button>
                    )}
                  </div>

                  {/* Right: + Add new, Upload CSV */}
                  <div className="flex items-center gap-2.5">
                    <button
                      type="button"
                      onClick={() => setIsAddingPronunciation(true)}
                      className="bg-gradient-to-r from-blue-600 to-cyan-500 hover:from-blue-500 hover:to-cyan-400 text-white text-xs font-semibold px-4 py-2 rounded-full shadow-xs flex items-center gap-1.5 transition-all cursor-pointer"
                    >
                      <Plus size={14} />
                      <span>Add new</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => pronunciationCsvRef.current?.click()}
                      className="bg-[#121828] hover:bg-[#18233c] text-slate-300 border border-[#1b2940] text-xs font-semibold px-4 py-2 rounded-full shadow-xs flex items-center gap-1.5 transition-all cursor-pointer"
                    >
                      <UploadCloud size={14} className="text-slate-400" />
                      <span>Upload CSV</span>
                    </button>
                  </div>
                </div>

                {/* Pronunciation Table Card */}
                <div className="bg-[#0b111e] rounded-2xl border border-[#1b2940] overflow-hidden shadow-xs">
                  <div className="grid grid-cols-2 bg-[#07090e] border-b border-[#1b2940] px-6 py-3.5">
                    <span className="text-xs font-semibold text-slate-400">
                      Original Word
                    </span>
                    <span className="text-xs font-semibold text-slate-400">
                      Word Behavior
                    </span>
                  </div>

                  {/* Inline Add New Row */}
                  {isAddingPronunciation && (
                    <div className="grid grid-cols-2 items-center px-6 py-3 bg-[#121828]/50 border-b border-[#1b2940] gap-4">
                      <div>
                        <input
                          type="text"
                          autoFocus
                          value={draftPronunciationWord}
                          onChange={(e) =>
                            setDraftPronunciationWord(e.target.value)
                          }
                          onKeyDown={(e) => {
                            if (e.key === "Enter") handleSavePronunciation();
                            if (e.key === "Escape") handleCancelPronunciation();
                          }}
                          placeholder="Original Word"
                          className="w-full bg-[#07090e] border border-[#1b2940] rounded-xl px-3 py-1.5 text-xs text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-cyan-500"
                        />
                      </div>
                      <div className="flex items-center justify-between gap-3">
                        <input
                          type="text"
                          value={draftPronunciationBehavior}
                          onChange={(e) =>
                            setDraftPronunciationBehavior(e.target.value)
                          }
                          onKeyDown={(e) => {
                            if (e.key === "Enter") handleSavePronunciation();
                            if (e.key === "Escape") handleCancelPronunciation();
                          }}
                          placeholder="Pronounce As"
                          className="w-full bg-[#07090e] border border-[#1b2940] rounded-xl px-3 py-1.5 text-xs text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-cyan-500"
                        />
                        <div className="flex items-center gap-1.5 shrink-0">
                          <button
                            type="button"
                            onClick={handleSavePronunciation}
                            disabled={!draftPronunciationWord.trim()}
                            title="Save"
                            className="w-7 h-7 rounded-full bg-cyan-500 text-slate-950 hover:bg-cyan-400 disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center transition-all cursor-pointer shadow-xs font-bold"
                          >
                            <Check size={13} />
                          </button>
                          <button
                            type="button"
                            onClick={handleCancelPronunciation}
                            title="Cancel"
                            className="w-7 h-7 rounded-full border border-[#1b2940] text-slate-400 hover:text-slate-200 hover:bg-[#18233c] flex items-center justify-center transition-all cursor-pointer"
                          >
                            <X size={13} />
                          </button>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Rules Rows or Empty State */}
                  {filteredPronunciationRules.length > 0 ? (
                    <div className="divide-y divide-[#1b2940]">
                      {filteredPronunciationRules.map((rule) => (
                        <div
                          key={rule.id}
                          className="grid grid-cols-2 items-center px-6 py-4 hover:bg-[#121828]/50 transition-colors group"
                        >
                          <span className="text-xs font-bold text-slate-100">
                            {rule.originalWord}
                          </span>
                          <div className="flex items-center justify-between">
                            <span className="text-xs text-slate-300">
                              {rule.behavior}
                            </span>
                            <button
                              type="button"
                              onClick={() =>
                                handleDeletePronunciation(rule.id)
                              }
                              className="text-slate-500 hover:text-red-400 transition-colors p-1 opacity-0 group-hover:opacity-100"
                            >
                              <Trash2 size={13} />
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    !isAddingPronunciation && (
                      <div className="py-24 px-6 text-center">
                        <p className="text-xs sm:text-sm text-slate-500 font-normal">
                          No pronunciations yet. Click "Add new" to add one.
                        </p>
                      </div>
                    )
                  )}
                </div>
              </div>
            )}

            {/* Sub-Tab 2: FORCE TRANSLATE */}
            {glossarySubTab === "force_translate" && (
              <div className="space-y-10 pt-1">
                {/* ---------------- SECTION 1: FORCE TRANSLATE ---------------- */}
                <div className="space-y-3">
                  {/* Hidden CSV Input for Force Translate */}
                  <input
                    ref={forceTranslateCsvRef}
                    type="file"
                    accept=".csv"
                    onChange={handleForceTranslateCsv}
                    className="hidden"
                  />

                  {/* Description */}
                  <p className="text-xs text-slate-400 font-normal">
                    A list of words you wish to translate into specific words,
                    regardless of language.
                  </p>

                  {/* Action Row */}
                  <div className="flex items-center justify-between gap-3 pt-2">
                    {/* Left: Search button / input */}
                    <div className="flex items-center gap-2">
                      {isForceTranslateSearchOpen ? (
                        <div className="flex items-center bg-[#121828] border border-[#1b2940] rounded-full pl-3 pr-2 py-1.5 shadow-inner">
                          <Search size={14} className="text-slate-400 mr-2" />
                          <input
                            type="text"
                            value={forceTranslateSearch}
                            onChange={(e) =>
                              setForceTranslateSearch(e.target.value)
                            }
                            placeholder="Search force translate..."
                            autoFocus
                            className="bg-transparent border-none text-xs text-slate-100 placeholder:text-slate-500 focus:outline-none w-36 sm:w-48"
                          />
                          <button
                            type="button"
                            onClick={() => {
                              setForceTranslateSearch("");
                              setIsForceTranslateSearchOpen(false);
                            }}
                            className="text-slate-400 hover:text-slate-200 p-0.5"
                          >
                            <X size={13} />
                          </button>
                        </div>
                      ) : (
                        <button
                          type="button"
                          onClick={() => setIsForceTranslateSearchOpen(true)}
                          title="Search force translate rules"
                          className="w-9 h-9 rounded-full border border-[#1b2940] bg-[#121828] hover:bg-[#18233c] flex items-center justify-center text-slate-300 hover:text-white transition-colors shadow-xs cursor-pointer"
                        >
                          <Search size={15} />
                        </button>
                      )}
                    </div>

                    {/* Right: + Add new, Upload CSV */}
                    <div className="flex items-center gap-2.5">
                      <button
                        type="button"
                        onClick={() => setIsAddingForceTranslate(true)}
                        className="bg-gradient-to-r from-blue-600 to-cyan-500 hover:from-blue-500 hover:to-cyan-400 text-white text-xs font-semibold px-4 py-2 rounded-full shadow-xs flex items-center gap-1.5 transition-all cursor-pointer"
                      >
                        <Plus size={14} />
                        <span>Add new</span>
                      </button>

                      <button
                        type="button"
                        onClick={() => forceTranslateCsvRef.current?.click()}
                        className="bg-[#121828] hover:bg-[#18233c] text-slate-300 border border-[#1b2940] text-xs font-semibold px-4 py-2 rounded-full shadow-xs flex items-center gap-1.5 transition-all cursor-pointer"
                      >
                        <UploadCloud size={14} className="text-slate-400" />
                        <span>Upload CSV</span>
                      </button>
                    </div>
                  </div>

                  {/* Force Translate Table Card */}
                  <div className="bg-[#0b111e] rounded-2xl border border-[#1b2940] overflow-hidden shadow-xs">
                    <div className="grid grid-cols-2 bg-[#07090e] border-b border-[#1b2940] px-6 py-3.5">
                      <span className="text-xs font-semibold text-slate-400">
                        Original Word
                      </span>
                      <span className="text-xs font-semibold text-slate-400">
                        Word Behavior
                      </span>
                    </div>

                    {/* Inline Add New Row for Force Translate */}
                    {isAddingForceTranslate && (
                      <div className="grid grid-cols-2 items-center px-6 py-3 bg-[#121828]/50 border-b border-[#1b2940] gap-4">
                        <div>
                          <input
                            type="text"
                            autoFocus
                            value={draftForceTranslateWord}
                            onChange={(e) =>
                              setDraftForceTranslateWord(e.target.value)
                            }
                            onKeyDown={(e) => {
                              if (e.key === "Enter") handleSaveForceTranslate();
                              if (e.key === "Escape") handleCancelForceTranslate();
                            }}
                            placeholder="Original Word"
                            className="w-full bg-[#07090e] border border-[#1b2940] rounded-xl px-3 py-1.5 text-xs text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-cyan-500"
                          />
                        </div>
                        <div className="flex items-center justify-between gap-3">
                          <input
                            type="text"
                            value={draftForceTranslateBehavior}
                            onChange={(e) =>
                              setDraftForceTranslateBehavior(e.target.value)
                            }
                            onKeyDown={(e) => {
                              if (e.key === "Enter") handleSaveForceTranslate();
                              if (e.key === "Escape") handleCancelForceTranslate();
                            }}
                            placeholder="Word Behavior"
                            className="w-full bg-[#07090e] border border-[#1b2940] rounded-xl px-3 py-1.5 text-xs text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-cyan-500"
                          />
                          <div className="flex items-center gap-1.5 shrink-0">
                            <button
                              type="button"
                              onClick={handleSaveForceTranslate}
                              disabled={!draftForceTranslateWord.trim()}
                              title="Save"
                              className="w-7 h-7 rounded-full bg-cyan-500 text-slate-950 hover:bg-cyan-400 disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center transition-all cursor-pointer shadow-xs font-bold"
                            >
                              <Check size={13} />
                            </button>
                            <button
                              type="button"
                              onClick={handleCancelForceTranslate}
                              title="Cancel"
                              className="w-7 h-7 rounded-full border border-[#1b2940] text-slate-400 hover:text-slate-200 hover:bg-[#18233c] flex items-center justify-center transition-all cursor-pointer"
                            >
                              <X size={13} />
                            </button>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Force Translate Rows or Empty State */}
                    {filteredForceTranslateRules.length > 0 ? (
                      <div className="divide-y divide-[#1b2940]">
                        {filteredForceTranslateRules.map((rule) => (
                          <div
                            key={rule.id}
                            className="grid grid-cols-2 items-center px-6 py-4 hover:bg-[#121828]/50 transition-colors group"
                          >
                            <span className="text-xs font-bold text-slate-100">
                              {rule.originalWord}
                            </span>
                            <div className="flex items-center justify-between">
                              <span className="text-xs text-slate-300">
                                {rule.behavior}
                              </span>
                              <button
                                type="button"
                                onClick={() =>
                                  handleDeleteForceTranslate(rule.id)
                                }
                                className="text-slate-500 hover:text-red-400 transition-colors p-1 opacity-0 group-hover:opacity-100"
                              >
                                <Trash2 size={13} />
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      !isAddingForceTranslate && (
                        <div className="py-24 px-6 text-center">
                          <p className="text-xs sm:text-sm text-slate-500 font-normal">
                            No rules yet. Click "Add new" to add one.
                          </p>
                        </div>
                      )
                    )}
                  </div>
                </div>

                {/* ---------------- SECTION 2: DON'T TRANSLATE ---------------- */}
                <div className="space-y-3 pt-4">
                  {/* Hidden CSV Input for Don't Translate */}
                  <input
                    ref={dontTranslateCsvRef}
                    type="file"
                    accept=".csv"
                    onChange={handleDontTranslateCsv}
                    className="hidden"
                  />

                  {/* Heading & Subtitle */}
                  <div>
                    <h3 className="text-base font-bold text-slate-100">
                      Don't Translate
                    </h3>
                    <p className="text-xs text-slate-400 font-normal mt-0.5">
                      Add product names, acronyms, or brand phrases that should
                      always stay as-is.
                    </p>
                  </div>

                  {/* Action Row */}
                  <div className="flex items-center justify-between gap-3 pt-2">
                    {/* Left: Search button / input */}
                    <div className="flex items-center gap-2">
                      {isDontTranslateSearchOpen ? (
                        <div className="flex items-center bg-[#121828] border border-[#1b2940] rounded-full pl-3 pr-2 py-1.5 shadow-inner">
                          <Search size={14} className="text-slate-400 mr-2" />
                          <input
                            type="text"
                            value={dontTranslateSearch}
                            onChange={(e) =>
                              setDontTranslateSearch(e.target.value)
                            }
                            placeholder="Search words..."
                            autoFocus
                            className="bg-transparent border-none text-xs text-slate-100 placeholder:text-slate-500 focus:outline-none w-36 sm:w-48"
                          />
                          <button
                            type="button"
                            onClick={() => {
                              setDontTranslateSearch("");
                              setIsDontTranslateSearchOpen(false);
                            }}
                            className="text-slate-400 hover:text-slate-200 p-0.5"
                          >
                            <X size={13} />
                          </button>
                        </div>
                      ) : (
                        <button
                          type="button"
                          onClick={() => setIsDontTranslateSearchOpen(true)}
                          title="Search don't translate words"
                          className="w-9 h-9 rounded-full border border-[#1b2940] bg-[#121828] hover:bg-[#18233c] flex items-center justify-center text-slate-300 hover:text-white transition-colors shadow-xs cursor-pointer"
                        >
                          <Search size={15} />
                        </button>
                      )}
                    </div>

                    {/* Right: + Add new, Upload CSV */}
                    <div className="flex items-center gap-2.5">
                      <button
                        type="button"
                        onClick={() => setIsAddingDontTranslate(true)}
                        className="bg-gradient-to-r from-blue-600 to-cyan-500 hover:from-blue-500 hover:to-cyan-400 text-white text-xs font-semibold px-4 py-2 rounded-full shadow-xs flex items-center gap-1.5 transition-all cursor-pointer"
                      >
                        <Plus size={14} />
                        <span>Add new</span>
                      </button>

                      <button
                        type="button"
                        onClick={() => dontTranslateCsvRef.current?.click()}
                        className="bg-[#121828] hover:bg-[#18233c] text-slate-300 border border-[#1b2940] text-xs font-semibold px-4 py-2 rounded-full shadow-xs flex items-center gap-1.5 transition-all cursor-pointer"
                      >
                        <UploadCloud size={14} className="text-slate-400" />
                        <span>Upload CSV</span>
                      </button>
                    </div>
                  </div>

                  {/* Don't Translate Table Card */}
                  <div className="bg-[#0b111e] rounded-2xl border border-[#1b2940] overflow-hidden shadow-xs">
                    <div className="bg-[#07090e] border-b border-[#1b2940] px-6 py-3.5">
                      <span className="text-xs font-semibold text-slate-400">
                        Word
                      </span>
                    </div>

                    {/* Inline Add New Row for Don't Translate */}
                    {isAddingDontTranslate && (
                      <div className="flex items-center justify-between px-6 py-3 bg-[#121828]/50 border-b border-[#1b2940] gap-4">
                        <input
                          type="text"
                          autoFocus
                          value={draftDontTranslateWord}
                          onChange={(e) =>
                            setDraftDontTranslateWord(e.target.value)
                          }
                          onKeyDown={(e) => {
                            if (e.key === "Enter") handleSaveDontTranslate();
                            if (e.key === "Escape") handleCancelDontTranslate();
                          }}
                          placeholder="Type a word and press Enter"
                          className="w-full max-w-md bg-[#07090e] border border-[#1b2940] rounded-xl px-3 py-1.5 text-xs text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-cyan-500"
                        />
                        <div className="flex items-center gap-1.5 shrink-0">
                          <button
                            type="button"
                            onClick={handleSaveDontTranslate}
                            disabled={!draftDontTranslateWord.trim()}
                            title="Save"
                            className="w-7 h-7 rounded-full bg-cyan-500 text-slate-950 hover:bg-cyan-400 disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center transition-all cursor-pointer shadow-xs font-bold"
                          >
                            <Check size={13} />
                          </button>
                          <button
                            type="button"
                            onClick={handleCancelDontTranslate}
                            title="Cancel"
                            className="w-7 h-7 rounded-full border border-[#1b2940] text-slate-400 hover:text-slate-200 hover:bg-[#18233c] flex items-center justify-center transition-all cursor-pointer"
                          >
                            <X size={13} />
                          </button>
                        </div>
                      </div>
                    )}

                    {/* Don't Translate Rows or Empty State */}
                    {filteredDontTranslateWords.length > 0 ? (
                      <div className="divide-y divide-[#1b2940]">
                        {filteredDontTranslateWords.map((item) => (
                          <div
                            key={item.id}
                            className="flex items-center justify-between px-6 py-4 hover:bg-[#121828]/50 transition-colors group"
                          >
                            <span className="text-xs font-bold text-slate-100">
                              {item.word}
                            </span>
                            <button
                              type="button"
                              onClick={() =>
                                handleDeleteDontTranslate(item.id)
                              }
                              className="text-slate-500 hover:text-red-400 transition-colors p-1 opacity-0 group-hover:opacity-100"
                            >
                              <Trash2 size={13} />
                            </button>
                          </div>
                        ))}
                      </div>
                    ) : (
                      !isAddingDontTranslate && (
                        <div className="py-24 px-6 text-center">
                          <p className="text-xs sm:text-sm text-slate-500 font-normal">
                            No words yet. Click "Add new" to add one.
                          </p>
                        </div>
                      )
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Project Picker Modal Dialog */}
        {showProjectPicker && (
          <div
            onClick={() => setShowProjectPicker(false)}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-[2px] p-4 sm:p-6 animate-in fade-in duration-200"
          >
            <div
              onClick={(e) => e.stopPropagation()}
              className={`${isLight ? "bg-white border-slate-200 text-slate-900 shadow-2xl" : "bg-[#0b111e] border-[#1b2940] text-slate-100 shadow-2xl"} rounded-[24px] max-w-2xl sm:max-w-3xl w-full border overflow-hidden flex flex-col max-h-[85vh] animate-in fade-in zoom-in-95 duration-150`}
            >
              {/* 1. Header */}
              <div className={`px-6 py-5 flex items-start justify-between border-b ${isLight ? "border-slate-200" : "border-[#1b2940]"}`}>
                <div>
                  <h2 className={`text-lg sm:text-xl font-bold ${isLight ? "text-slate-900" : "text-slate-100"} tracking-tight`}>
                    Select an Existing Project
                  </h2>
                  <p className={`text-xs sm:text-sm ${isLight ? "text-slate-500" : "text-slate-400"} mt-0.5 font-normal`}>
                    Pick an existing asset to dub
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setShowProjectPicker(false)}
                  className={`${isLight ? "text-slate-400 hover:text-slate-700 hover:bg-slate-100" : "text-slate-400 hover:text-white hover:bg-[#18233c]"} p-1.5 rounded-full transition-colors cursor-pointer`}
                  title="Close"
                >
                  <X size={20} />
                </button>
              </div>

              {/* 2. Search & Filters Bar */}
              <div className={`px-6 py-3.5 flex items-center gap-3 border-b ${isLight ? "border-slate-200 bg-slate-50" : "border-[#1b2940] bg-[#07090e]/40"}`}>
                {/* Search Input */}
                <div className="relative flex-1">
                  <Search
                    size={16}
                    className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none"
                  />
                  <input
                    type="text"
                    value={projectSearchQuery}
                    onChange={(e) => setProjectSearchQuery(e.target.value)}
                    placeholder="Search projects..."
                    className={`w-full ${
                      isLight
                        ? "bg-white border-slate-300 text-slate-900 placeholder:text-slate-400 focus:border-blue-500 focus:ring-1 focus:ring-blue-500/30"
                        : "bg-[#121828] border-[#1b2940] text-slate-100 placeholder:text-slate-500 focus:border-cyan-500/60 focus:ring-1 focus:ring-cyan-500/30"
                    } border rounded-xl pl-9 pr-3.5 py-2 text-xs transition-all shadow-2xs`}
                  />
                </div>

                {/* Filters Button */}
                <div className="relative">
                  <button
                    type="button"
                    onClick={() => setIsProjectFilterOpen(!isProjectFilterOpen)}
                    className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold border transition-all cursor-pointer shadow-2xs ${
                      selectedProjectType !== "all" || isProjectFilterOpen
                        ? isLight
                          ? "bg-blue-50 text-blue-600 border-blue-200"
                          : "bg-[#18233c] text-white border-[#2b3a5d]"
                        : isLight
                        ? "bg-white hover:bg-slate-100 text-slate-700 border-slate-200"
                        : "bg-[#121828] hover:bg-[#18233c] text-slate-200 border-[#1b2940]"
                    }`}
                  >
                    <Filter size={14} className={selectedProjectType !== "all" ? (isLight ? "text-blue-600" : "text-cyan-400") : "text-slate-400"} />
                    <span>Filters</span>
                    <span
                      className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full ${
                        selectedProjectType !== "all"
                          ? "bg-blue-600 text-white"
                          : isLight
                          ? "bg-slate-200 text-slate-700"
                          : "bg-[#1b2940] text-slate-300"
                      }`}
                    >
                      {selectedProjectType === "all" ? "0" : "1"}
                    </span>
                  </button>

                  {isProjectFilterOpen && (
                    <div className={`absolute right-0 top-full mt-2 w-48 ${isLight ? "bg-white border-slate-200 shadow-xl" : "bg-[#0b111e] border-[#1b2940] shadow-2xl"} border rounded-2xl p-2 z-20 space-y-1 animate-in fade-in zoom-in-95 duration-100`}>
                      {["all", "Avatar Video", "Translations"].map((filterOpt) => (
                        <button
                          key={filterOpt}
                          type="button"
                          onClick={() => {
                            setSelectedProjectType(filterOpt);
                            setIsProjectFilterOpen(false);
                          }}
                          className={`w-full text-left px-3 py-1.5 rounded-lg text-xs font-medium transition-colors flex items-center justify-between cursor-pointer ${
                            selectedProjectType === filterOpt
                              ? isLight
                                ? "bg-blue-50 text-blue-600 font-semibold"
                                : "bg-[#18233c] text-cyan-400 font-semibold"
                              : isLight
                              ? "text-slate-700 hover:bg-slate-50"
                              : "text-slate-200 hover:bg-[#101828]"
                          }`}
                        >
                          <span>{filterOpt === "all" ? "All Types" : filterOpt}</span>
                          {selectedProjectType === filterOpt && (
                            <Check size={14} className={isLight ? "text-blue-600" : "text-cyan-400"} />
                          )}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* 3. Projects Grid (3 Columns) */}
              <div className={`p-6 overflow-y-auto max-h-[55vh] scrollbar-thin ${isLight ? "scrollbar-track-slate-100 scrollbar-thumb-slate-300 hover:scrollbar-thumb-slate-400" : "scrollbar-track-[#07090e] scrollbar-thumb-[#1b2940] hover:scrollbar-thumb-[#2b3a5d]"}`}>
                {filteredExistingProjects.length === 0 ? (
                  <div className={`text-center py-12 ${isLight ? "text-slate-500" : "text-slate-400"} text-xs font-medium`}>
                    No projects match your search.
                  </div>
                ) : (
                  <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4 sm:gap-5">
                    {filteredExistingProjects.map((project) => {
                      const isSelected = selectedProject?.id === project.id;
                      return (
                        <div
                          key={project.id}
                          onClick={() => {
                            setSelectedProject(project);
                            setSelectedFile(
                              new File([], `${project.title}.mp4`, {
                                type: "video/mp4",
                              })
                            );
                            setShowProjectPicker(false);
                          }}
                          className={`group cursor-pointer rounded-2xl p-2.5 transition-all duration-200 border text-left flex flex-col ${
                            isSelected
                              ? isLight
                                ? "bg-blue-50 border-blue-500 shadow-md ring-2 ring-blue-500/20"
                                : "bg-[#18233c] border-cyan-500 shadow-md ring-2 ring-cyan-500/30"
                              : isLight
                              ? "bg-white hover:bg-slate-50 border-slate-200 hover:border-blue-400 hover:shadow-sm"
                              : "bg-[#0b111e] hover:bg-[#121828]/60 border-[#1b2940] hover:border-[#2b3a5d] hover:shadow-md"
                          }`}
                        >
                          {/* Thumbnail Frame (Approx 4:3) */}
                          <div className="w-full aspect-[4/3] rounded-xl overflow-hidden relative bg-slate-950 mb-2.5 shadow-2xs">
                            <img
                              src={project.image}
                              alt={project.title}
                              className="w-full h-full object-cover object-center group-hover:scale-105 transition-transform duration-300 brightness-95"
                            />
                            <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-black/20"></div>

                            {/* DRAFT Badge */}
                            {project.status === "Draft" && (
                              <span className="absolute top-2 left-2 bg-[#121828]/90 border border-[#1b2940] backdrop-blur-xs text-slate-200 text-[9px] font-bold px-2 py-0.5 rounded shadow-xs tracking-wider">
                                DRAFT
                              </span>
                            )}

                            {/* Selected Checkmark */}
                            {isSelected && (
                              <div className="absolute top-2 right-2 w-6 h-6 rounded-full bg-cyan-500 text-slate-950 flex items-center justify-center shadow-md">
                                <Check size={14} className="stroke-[3]" />
                              </div>
                            )}
                          </div>

                          {/* Title */}
                          <h4 className={`text-xs font-bold ${isLight ? "text-slate-900 group-hover:text-blue-600" : "text-slate-100 group-hover:text-cyan-400"} truncate transition-colors`}>
                            {project.title}
                          </h4>

                          {/* Metadata */}
                          <p className={`text-[11px] ${isLight ? "text-slate-500" : "text-slate-400"} mt-0.5 truncate`}>
                            {project.time} • {project.type}
                          </p>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Create New Brand Glossary Modal Dialog */}
        {showCreateGlossaryModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
            <div className="bg-[#0b111e] rounded-2xl max-w-md w-full p-6 shadow-2xl border border-[#1b2940] animate-in fade-in zoom-in duration-150">
              <div className="flex items-center justify-between pb-3 border-b border-[#1b2940]">
                <h3 className="text-sm font-bold text-slate-100">
                  Create New Brand Glossary
                </h3>
                <button
                  onClick={() => {
                    setNewGlossaryName("");
                    setShowCreateGlossaryModal(false);
                  }}
                  className="text-slate-400 hover:text-slate-200 p-1 rounded-md cursor-pointer"
                >
                  <X size={16} />
                </button>
              </div>

              <form onSubmit={handleCreateNewGlossary} className="py-4 space-y-4">
                <div>
                  <label className="text-xs font-bold text-slate-300 block mb-1.5">
                    Glossary Name
                  </label>
                  <input
                    type="text"
                    required
                    autoFocus
                    value={newGlossaryName}
                    onChange={(e) => setNewGlossaryName(e.target.value)}
                    placeholder="e.g. Brand Glossary 5"
                    className="w-full bg-[#121828] border border-[#1b2940] rounded-xl px-3.5 py-2 text-xs text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-cyan-500"
                  />
                </div>

                <div className="flex items-center justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => {
                      setNewGlossaryName("");
                      setShowCreateGlossaryModal(false);
                    }}
                    className="px-4 py-2 rounded-full text-xs font-semibold text-slate-400 hover:text-slate-200 hover:bg-[#18233c] transition-colors cursor-pointer"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={!newGlossaryName.trim()}
                    className="px-5 py-2 rounded-full text-xs font-semibold bg-gradient-to-r from-blue-600 to-cyan-500 hover:from-blue-500 hover:to-cyan-400 disabled:opacity-40 text-white shadow-sm transition-all cursor-pointer"
                  >
                    Create Glossary
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
