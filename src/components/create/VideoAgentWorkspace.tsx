"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  Home,
  Share2,
  Lock,
  Building2,
  Sparkles,
  Clapperboard,
  Play,
  ArrowUp,
  Plus,
  Bot,
  User as UserIcon,
  Video as VideoIcon,
  CheckCircle2,
  AlertCircle,
  AlertTriangle,
  RefreshCw,
  FolderOpen,
  Film,
  FileText,
  Volume2,
  Layers,
  Clock,
  ChevronRight,
  ExternalLink,
  Trash2,
  X,
  Download,
  ChevronDown,
  Check,
  Camera,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { useTheme } from "@/context/ThemeContext";
import { api, ProjectResponse, JobResponse } from "@/lib/api";
import AttachAssetModal from "./AttachAssetModal";
import ChooseAvatarModal from "./ChooseAvatarModal";
import { AVATAR_OPTIONS, VOICE_OPTIONS, BRAND_SYSTEM_OPTIONS } from "./videoAgentData";

export interface VideoAgentGenerationContext {
  prompt?: string;
  avatar?: any;
  voice?: any;
  look?: any;
  captions?: boolean;
  brandSystem?: any;
  attachments?: string[];
  speed?: string;
  quality?: string;
  seedance?: boolean;
  template?: any;
  target_duration_seconds?: number;
  sourceApp?: string;
  workflowIntent?: string;
  workflowLabel?: string;
  modalConfiguration?: Record<string, any>;
  attachment?: Record<string, any>;
  userPrompt?: string;
}

export const DURATION_PRESETS = [
  { label: "15 sec", seconds: 15 },
  { label: "30 sec", seconds: 30 },
  { label: "60 sec", seconds: 60 },
  { label: "90 sec", seconds: 90 },
  { label: "2 min", seconds: 120 },
  { label: "5 min", seconds: 300 },
  { label: "10 min", seconds: 600 },
  { label: "Custom", seconds: -1 },
] as const;

export function formatDurationMMSS(seconds: number): string {
  const totalSecs = Math.max(0, Math.round(seconds));
  const mins = Math.floor(totalSecs / 60);
  const secs = totalSecs % 60;
  return `${mins}:${secs < 10 ? "0" : ""}${secs}`;
}

export function getDurationLabel(seconds: number): string {
  const preset = DURATION_PRESETS.find((p) => p.seconds === seconds);
  if (preset && preset.seconds > 0) {
    return `${preset.label} (${formatDurationMMSS(seconds)})`;
  }
  return `Custom: ${formatDurationMMSS(seconds)} (${Math.round(seconds)}s)`;
}

export interface VideoAgentWorkspaceProps {
  workspaceId?: string;
  workspaceName?: string;
  initialPrompt?: string;
  generationContext?: VideoAgentGenerationContext | null;
  appliedBrandSystem?: any;
  onOpenStudio?: (projectId?: string) => void;
  onBackToDashboard?: () => void;
}

interface ConversationMessage {
  id: string;
  sender: "user" | "agent";
  text: string;
  timestamp: Date;
  status?: "thinking" | "generating" | "completed" | "failed";
  stageMessage?: string;
  projectId?: string;
  config?: {
    avatarName?: string;
    voiceName?: string;
    lookName?: string;
    captions?: boolean;
    brandName?: string;
    aspectRatio?: string;
  };
}

interface VideoArtifact {
  id: string;
  title: string;
  status: "draft" | "ready" | "processing" | "failed";
  aspectRatio: string;
  duration: number;
  sceneCount: number;
  scenes: Array<{
    id: string;
    sequence: number;
    duration: number;
    heading?: string;
    script?: string;
    avatarId?: string;
    avatarVideoAssetId?: string;
    cameraMotion?: string;
    transition?: any;
    background?: any;
  }>;
  avatarId?: string;
  voiceId?: string;
  avatarName: string;
  voiceName: string;
  createdAt: string;
  thumbnailUrl?: string;
  videoUrl?: string;
  generationType?: string;
  outputAssetId?: string;
  error?: string;
}

interface ActiveGenerationState {
  id: string;
  status: "queued" | "running" | "completed" | "failed";
  stage?: string;
  stageMessage?: string;
  progress?: number;
  jobId?: string;
  projectId?: string;
  error?: string;
  isGpuRequired?: boolean;
  incompleteScenes?: Array<{
    id: string;
    sequence: number;
    duration: number;
    heading?: string;
    script?: string;
  }>;
  plannedDuration?: number;
  targetDurationSeconds?: number;
  prompt: string;
  context?: VideoAgentGenerationContext | null;
  startedAt: number;
}

export default function VideoAgentWorkspace({
  workspaceId: propWorkspaceId,
  workspaceName: propWorkspaceName,
  initialPrompt,
  generationContext,
  appliedBrandSystem,
  onOpenStudio,
  onBackToDashboard,
}: VideoAgentWorkspaceProps) {
  const { currentWorkspace, user } = useAuth();
  const { theme } = useTheme();
  const isLight = theme === "light";
  const effectiveWorkspaceId = propWorkspaceId || currentWorkspace?.id;
  const effectiveWorkspaceName =
    propWorkspaceName || currentWorkspace?.name || "Personal Workspace";

  // Navigation & Tabs
  const [activeTab, setActiveTab] = useState<"artifacts" | "resources">("artifacts");
  const [videoTitle, setVideoTitle] = useState("New video");

  // Conversation state
  const [messages, setMessages] = useState<ConversationMessage[]>([
    {
      id: "msg_init",
      sender: "agent",
      text: "Hi! What would you like to create or work on today?",
      timestamp: new Date(),
    },
  ]);

  // Composer state
  const [composerText, setComposerText] = useState(() => {
    return generationContext?.userPrompt || generationContext?.prompt || initialPrompt || "";
  });
  const [isGenerating, setIsGenerating] = useState(false);
  const [isAttachModalOpen, setIsAttachModalOpen] = useState(false);
  const [attachedFiles, setAttachedFiles] = useState<string[]>(() => {
    if (generationContext?.attachment?.name) {
      return [generationContext.attachment.name];
    }
    return generationContext?.attachments || [];
  });

  // Artifacts state
  const [artifacts, setArtifacts] = useState<VideoArtifact[]>([]);
  const [selectedArtifact, setSelectedArtifact] = useState<VideoArtifact | null>(null);
  const [activeGeneration, setActiveGeneration] = useState<ActiveGenerationState | null>(null);

  // Backend available avatars & voices for genuine ID resolution
  const [backendAvatars, setBackendAvatars] = useState<any[]>([]);
  const [backendVoices, setBackendVoices] = useState<any[]>([]);

  // Presenter selector state
  const [selectedPresenter, setSelectedPresenter] = useState<any | null>(() => {
    if (generationContext?.avatar) return generationContext.avatar;
    return null;
  });
  const [isPresenterPickerOpen, setIsPresenterPickerOpen] = useState(false);
  const [isChooseAvatarModalOpen, setIsChooseAvatarModalOpen] = useState(false);
  const presenterPickerRef = useRef<HTMLDivElement>(null);

  // Duration selector state (15s, 30s, 60s, 90s, 2m, 5m, 10m, custom)
  const [selectedDurationSeconds, setSelectedDurationSeconds] = useState<number>(() => {
    if (generationContext?.target_duration_seconds && generationContext.target_duration_seconds > 0) {
      return generationContext.target_duration_seconds;
    }
    return 30;
  });
  const [isDurationPickerOpen, setIsDurationPickerOpen] = useState(false);
  const [customDurationInput, setCustomDurationInput] = useState<string>("");
  const [isCustomMode, setIsCustomMode] = useState<boolean>(false);
  const durationPickerRef = useRef<HTMLDivElement>(null);

  // Close presenter & duration popovers on outside click
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (
        presenterPickerRef.current &&
        !presenterPickerRef.current.contains(e.target as Node)
      ) {
        setIsPresenterPickerOpen(false);
      }
      if (
        durationPickerRef.current &&
        !durationPickerRef.current.contains(e.target as Node)
      ) {
        setIsDurationPickerOpen(false);
      }
    }
    if (isPresenterPickerOpen || isDurationPickerOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isPresenterPickerOpen, isDurationPickerOpen]);

  // Modals & previews
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);
  const [activePreviewSceneIdx, setActivePreviewSceneIdx] = useState(0);
  const [isShareModalOpen, setIsShareModalOpen] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const composerInputRef = useRef<HTMLTextAreaElement>(null);
  const hasTriggeredInitialRef = useRef(false);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Load backend avatars and voices for real ID resolution
  useEffect(() => {
    if (!effectiveWorkspaceId) return;
    let active = true;

    api.creative
      .listAvatars({}, effectiveWorkspaceId)
      .then((avs) => {
        if (active && Array.isArray(avs)) {
          setBackendAvatars(avs);
          setSelectedPresenter((prev: any) => {
            if (prev) {
              const matchedPrev = avs.find(
                (a: any) =>
                  a.id === prev.id ||
                  a.name?.toLowerCase() === prev.name?.toLowerCase()
              );
              return matchedPrev ? { ...matchedPrev, ...prev } : prev;
            }
            if (generationContext?.avatar) {
              const matchedFromContext = avs.find(
                (a: any) =>
                  a.id === generationContext.avatar.id ||
                  a.name?.toLowerCase() ===
                    generationContext.avatar.name?.toLowerCase()
              );
              if (matchedFromContext) return matchedFromContext;
              return generationContext.avatar;
            }
            // Default to Annie as the canonical preset presenter
            const annie = avs.find(
              (a: any) =>
                a.name?.toLowerCase().includes("annie") ||
                a.id === "30000000-0000-0000-0000-000000000002"
            );
            return annie || avs[0] || null;
          });
        }
      })
      .catch(() => {});

    api.creative
      .listVoices({}, effectiveWorkspaceId)
      .then((vcs) => {
        if (active && Array.isArray(vcs)) {
          setBackendVoices(vcs);
        }
      })
      .catch(() => {});

    return () => {
      active = false;
    };
  }, [effectiveWorkspaceId, generationContext?.avatar]);

  // Load existing projects from workspace as initial artifacts if available
  useEffect(() => {
    if (!effectiveWorkspaceId) return;
    api.projects
      .list(effectiveWorkspaceId, { limit: 10 })
      .then((projs) => {
        if (Array.isArray(projs) && projs.length > 0) {
          const loaded: VideoArtifact[] = projs.map((p) => {
            const isDraft = p.status === "draft" || !p.thumbnail_asset_id;
            return {
              id: p.id,
              title: p.title || "Video Project",
              status: (p.status as any) || (isDraft ? "draft" : "ready"),
              aspectRatio: p.aspect_ratio || "16:9",
              duration: p.duration_ms ? Math.round(p.duration_ms / 1000) : 30,
              sceneCount: (p as any).scenes_count || 3,
              scenes: [
                {
                  id: "sc_1",
                  sequence: 1,
                  duration: 10,
                  heading: "Introduction",
                  script: "Welcome to this presentation.",
                },
              ],
              avatarName: (p as any).avatar_name || "Presenter",
              voiceName: "Voice",
              createdAt: p.created_at,
            };
          });
          setArtifacts((prev) => {
            const existingIds = new Set(prev.map((a) => a.id));
            const fresh = loaded.filter((l) => !existingIds.has(l.id));
            return [...prev, ...fresh];
          });
          const hasPendingInitialGen = Boolean(
            (generationContext?.prompt || initialPrompt)?.trim()
          );
          // Never auto-select an unrendered draft project without a videoUrl
          const readyWithVideo = loaded.find((l) => Boolean(l.videoUrl));
          if (
            !selectedArtifact &&
            readyWithVideo &&
            !hasPendingInitialGen &&
            !isGenerating &&
            !activeGeneration
          ) {
            setSelectedArtifact(readyWithVideo);
          }
        }
      })
      .catch((err) => {
        console.error("Failed to load existing workspace projects:", err);
      });
  }, [effectiveWorkspaceId]);

  // Sync composer text and attached files whenever generationContext changes
  useEffect(() => {
    if (generationContext?.workflowIntent) {
      const p = generationContext.userPrompt || generationContext.prompt || initialPrompt || "";
      if (p) setComposerText(p);
      if (generationContext.attachment?.name) {
        setAttachedFiles([generationContext.attachment.name]);
      }
    }
  }, [generationContext, initialPrompt]);

  // Trigger initial generation if context or prompt is provided AND workspace is ready
  useEffect(() => {
    if (hasTriggeredInitialRef.current) return;
    if (!effectiveWorkspaceId) return; // Wait until workspace is ready

    // When launched from a modal workflow (PPT/PDF or Cinematic Shots), do NOT auto-execute.
    // The user must review, optionally edit their prompt, and click Generate.
    if (generationContext?.workflowIntent) {
      hasTriggeredInitialRef.current = true;
      return;
    }

    const promptToRun = generationContext?.prompt || initialPrompt;
    if (promptToRun && promptToRun.trim().length > 0) {
      hasTriggeredInitialRef.current = true;
      executeGeneration(promptToRun, generationContext);
    }
  }, [generationContext, initialPrompt, effectiveWorkspaceId]);

  const handleRetry = () => {
    const promptToRetry =
      activeGeneration?.prompt ||
      [...messages].reverse().find((m) => m.sender === "user")?.text ||
      initialPrompt ||
      "";
    const contextToRetry: VideoAgentGenerationContext =
      activeGeneration?.context || {
        ...generationContext,
        prompt: promptToRetry,
        avatar: selectedPresenter || generationContext?.avatar,
        target_duration_seconds: activeGeneration?.targetDurationSeconds || selectedDurationSeconds,
      };
    if (!promptToRetry.trim() || isGenerating) return;
    executeGeneration(promptToRetry, contextToRetry);
  };

  const executeGeneration = async (
    prompt: string,
    context?: VideoAgentGenerationContext | null
  ) => {
    if (!effectiveWorkspaceId) {
      console.warn("No active workspace to execute generation");
      return;
    }

    const durationToUse =
      (context?.target_duration_seconds && context.target_duration_seconds > 0)
        ? context.target_duration_seconds
        : selectedDurationSeconds;
    if (context?.target_duration_seconds && context.target_duration_seconds > 0) {
      setSelectedDurationSeconds(context.target_duration_seconds);
    }

    const genReqId = `gen_${Date.now()}`;
    const userMsgId = `user_${Date.now()}`;
    const agentMsgId = `agent_${Date.now()}`;

    // Clear any previous/stale artifact so failure never coexists with Ready
    setSelectedArtifact(null);

    // Track active generation job state
    setActiveGeneration({
      id: genReqId,
      status: "queued",
      stage: "preparing",
      stageMessage: "Decomposing prompt into multi-scene timeline & speech scripts...",
      plannedDuration: durationToUse,
      targetDurationSeconds: durationToUse,
      prompt,
      context,
      startedAt: Date.now(),
    });

    // 1. Post user message
    const userMsg: ConversationMessage = {
      id: userMsgId,
      sender: "user",
      text: prompt,
      timestamp: new Date(),
      config: {
        avatarName:
          context?.avatar?.name ||
          selectedPresenter?.name ||
          "Annie - Studio Presenter",
        voiceName: context?.voice?.name || "Annie - Lifelike",
        lookName: context?.look?.name || "Default Look",
        captions: context?.captions ?? true,
        brandName: context?.brandSystem?.name || appliedBrandSystem?.name,
        aspectRatio: "16:9",
      },
    };

    // 2. Post thinking agent message
    const agentMsg: ConversationMessage = {
      id: agentMsgId,
      sender: "agent",
      text: "Thinking...",
      status: "generating",
      stageMessage: "Decomposing prompt into multi-scene timeline & speech scripts...",
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMsg, agentMsg]);
    setIsGenerating(true);
    setVideoTitle(context?.template?.title || prompt.slice(0, 32) || "New video");

    let currentGenProjId: string | undefined = undefined;

    try {
      // Resolve avatar ID to a genuine backend UUID
      let resolvedAvatarId: string | undefined = undefined;
      const rawAvatarId =
        context?.avatar?.id ||
        (context as any)?.avatarId ||
        selectedPresenter?.id;
      const rawAvatarName = (
        context?.avatar?.name ||
        selectedPresenter?.name ||
        ""
      ).toLowerCase();

      if (
        rawAvatarId &&
        /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(
          rawAvatarId
        )
      ) {
        resolvedAvatarId = rawAvatarId;
      } else if (rawAvatarName) {
        const matchedByName = backendAvatars.find(
          (a: any) =>
            a.name?.toLowerCase().includes(rawAvatarName) ||
            a.provider_reference?.toLowerCase() === rawAvatarName
        );
        if (matchedByName) resolvedAvatarId = matchedByName.id;
      }

      // Default to Annie if no avatar is requested or found
      if (!resolvedAvatarId && !rawAvatarId && !rawAvatarName) {
        const annieAv = backendAvatars.find(
          (a: any) =>
            a.name?.toLowerCase().includes("annie") ||
            a.id === "30000000-0000-0000-0000-000000000002"
        );
        resolvedAvatarId = annieAv?.id || "30000000-0000-0000-0000-000000000002";
      } else if (!resolvedAvatarId && rawAvatarId) {
        // Truthful forwarding to backend if requested ID cannot be resolved locally
        resolvedAvatarId = rawAvatarId;
      }

      // Resolve voice ID to a genuine backend voice model
      let resolvedVoiceId = "10000000-0000-0000-0000-000000000003"; // Annie - Lifelike UUID
      const rawVoiceId = context?.voice?.id || (context as any)?.voiceId;
      const rawVoiceName = (context?.voice?.name || "").toLowerCase();

      if (
        rawVoiceId &&
        /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(
          rawVoiceId
        )
      ) {
        resolvedVoiceId = rawVoiceId;
      } else if (
        rawVoiceId === "annie-lifelike" ||
        rawVoiceName.includes("annie")
      ) {
        resolvedVoiceId = "10000000-0000-0000-0000-000000000003";
      } else if (rawVoiceName.includes("marcus")) {
        resolvedVoiceId = "en_US-lessac-medium";
      } else if (backendVoices.length > 0) {
        const matchedVoice =
          backendVoices.find(
            (v: any) =>
              v.id === rawVoiceId ||
              v.name?.toLowerCase().includes(rawVoiceName) ||
              v.provider_reference === rawVoiceId
          ) || backendVoices[0];
        if (matchedVoice) resolvedVoiceId = matchedVoice.id;
      }

      // 3. Call real backend project orchestration generator
      const genResult = await api.orchestration.generateProject(
        effectiveWorkspaceId,
        {
          prompt: prompt.trim(),
          target_duration_seconds: durationToUse,
          aspect_ratio: (context?.modalConfiguration as any)?.aspectRatio || "16:9",
          avatar_id: resolvedAvatarId || undefined,
          voice_id: resolvedVoiceId || undefined,
          video_tone: context?.speed || "Professional",
          auto_synthesize_speech: false,
          run_async: true,
          workflow_intent: context?.workflowIntent,
          workflow_label: context?.workflowLabel,
          workflow_metadata: context?.modalConfiguration,
          attachment: context?.attachment,
        }
      );

      // 4. Extract generated project (supports both async JobResponse and sync ProjectResponse)
      let createdProject: ProjectResponse | null = null;
      let outputAssetId: string | undefined = undefined;
      let thumbnailAssetId: string | undefined = undefined;
      let videoUrl: string | undefined = undefined;
      let thumbnailUrl: string | undefined = undefined;
      let pipelineMode: string | undefined = undefined;

      if ("job_type" in genResult) {
        const jobId = (genResult as JobResponse).id;
        currentGenProjId =
          (genResult as any).payload?.project_id ||
          (genResult as any).result?.project_id;
        setActiveGeneration((prev) =>
          prev
            ? {
                ...prev,
                status: "running",
                jobId,
                projectId: currentGenProjId,
                stage: "submitting",
                stageMessage: "Submitting generation job to media pipeline...",
              }
            : null
        );

        setMessages((prev) =>
          prev.map((m) =>
            m.id === agentMsgId
              ? {
                  ...m,
                  stageMessage: "Submitting generation job to media pipeline...",
                }
              : m
          )
        );

        let attempts = 0;
        const maxAttempts = 90;
        let completedJob = genResult as JobResponse;

        while (attempts < maxAttempts) {
          await new Promise((r) => setTimeout(r, 1000));
          attempts++;
          const polled = await api.jobs.get(jobId);
          if (polled.status === "succeeded" || polled.status === "completed") {
            completedJob = polled;
            break;
          }
          if (polled.status === "failed") {
            const isGpuRequired =
              polled.error_details?.code === "GPU_REQUIRED" ||
              polled.error_details?.provider_status === "GPU_REQUIRED" ||
              (typeof polled.error_details?.error === "string" && polled.error_details.error.includes("GPU_REQUIRED")) ||
              (typeof polled.stage_message === "string" && polled.stage_message.includes("GPU_REQUIRED"));

            const errorText = isGpuRequired
              ? "Neural avatar generation requires a CUDA GPU."
              : (polled.error_details?.message ||
                 polled.error_details?.error ||
                 polled.stage_message ||
                 "Media generation job failed on server.");

            const err = new Error(errorText);
            (err as any).isGpuRequired = isGpuRequired;
            (err as any).projectId =
              currentGenProjId ||
              polled.result?.project_id ||
              (polled as any).payload?.project_id;
            throw err;
          }
          if (polled.stage_message || polled.stage) {
            let userFriendlyStage = polled.stage_message || polled.stage;
            if (polled.stage === "preparing") {
              userFriendlyStage = "Preparing workspace and presenter assets...";
            } else if (polled.stage === "generating_audio") {
              userFriendlyStage = "Generating speech audio via Piper TTS...";
            } else if (polled.stage === "preparing_avatar") {
              userFriendlyStage = "Composing avatar visuals and framing...";
            } else if (polled.stage === "rendering") {
              userFriendlyStage = "Rendering multi-scene video timeline with FFmpeg...";
            } else if (polled.stage === "uploading") {
              userFriendlyStage = "Uploading rendered MP4 to asset storage...";
            }
            setActiveGeneration((prev) =>
              prev
                ? {
                    ...prev,
                    status: "running",
                    stage: polled.stage,
                    stageMessage: userFriendlyStage,
                    progress: polled.progress_percent,
                    jobId,
                  }
                : null
            );
            setMessages((prev) =>
              prev.map((m) =>
                m.id === agentMsgId
                  ? {
                      ...m,
                      stageMessage: userFriendlyStage,
                    }
                  : m
              )
            );
          }
        }

        const projId = completedJob.result?.project_id || (completedJob as any)?.payload?.project_id;
        if (!projId) {
          throw new Error("Generation job finished but returned no project_id");
        }
        createdProject = await api.projects.get(effectiveWorkspaceId, projId);
        outputAssetId = completedJob.result?.output_asset_id;
        thumbnailAssetId = completedJob.result?.thumbnail_asset_id;
        pipelineMode = completedJob.result?.pipeline_mode;

        // Fetch real MinIO download URLs for rendered video & thumbnail assets
        if (outputAssetId) {
          try {
            const down = await api.assets.getDownloadUrl(effectiveWorkspaceId, outputAssetId);
            if (down?.download_url) {
              videoUrl = down.download_url;
            }
          } catch (assetErr) {
            console.warn("Could not fetch download URL for output video asset:", assetErr);
          }
        }

        if (thumbnailAssetId) {
          try {
            const thumbDown = await api.assets.getDownloadUrl(effectiveWorkspaceId, thumbnailAssetId);
            if (thumbDown?.download_url) {
              thumbnailUrl = thumbDown.download_url;
            }
          } catch (thumbErr) {
            console.warn("Could not fetch download URL for thumbnail asset:", thumbErr);
          }
        }
      } else {
        createdProject = genResult as ProjectResponse;
      }

      if (!createdProject?.id) {
        throw new Error("Backend did not return a valid generated project ID");
      }

      // 5. Query latest project version for scene details
      let scenesList: Array<{
        id: string;
        sequence: number;
        duration: number;
        heading?: string;
        script?: string;
        avatarId?: string;
        avatarVideoAssetId?: string;
        cameraMotion?: string;
        transition?: any;
        background?: any;
      }> = [];
      let totalDuration = durationToUse;

      try {
        const latestVersion = await api.projects.getLatestVersion(
          effectiveWorkspaceId,
          createdProject.id
        );
        if (latestVersion?.document?.scenes) {
          scenesList = latestVersion.document.scenes.map((sc: any, idx: number) => ({
            id: sc.id || `scene_${idx + 1}`,
            sequence: sc.sequence || idx + 1,
            duration: sc.duration || 10,
            heading: sc.layers?.find((l: any) => l.name === "Scene Heading")?.content?.text,
            script: sc.speech?.script || "Synthesized presentation scene.",
            avatarId: sc.avatar?.avatar_id,
            avatarVideoAssetId: sc.avatar?.video_asset_id,
            cameraMotion: sc.camera_motion || "static",
            transition: sc.transition,
            background: sc.background,
          }));
          totalDuration =
            latestVersion.document.settings?.total_duration ||
            ((latestVersion.document as any)?.metadata?.actual_planned_duration_seconds as number) ||
            ((latestVersion.document as any)?.metadata?.target_duration_seconds as number) ||
            scenesList.reduce((acc, s) => acc + (s.duration || 0), 0) ||
            durationToUse;
        }
      } catch (docErr) {
        console.warn("Could not load scene details from project version:", docErr);
        const fallbackCount = Math.max(1, Math.min(30, Math.round(durationToUse / 15)));
        const fallbackDur = Math.round((durationToUse / fallbackCount) * 10) / 10;
        scenesList = Array.from({ length: fallbackCount }, (_, idx) => ({
          id: `sc_${idx + 1}`,
          sequence: idx + 1,
          duration: fallbackDur,
          heading: idx === 0 ? "Hook & Overview" : idx === fallbackCount - 1 ? "Call to Action" : `Key Topic ${idx + 1}`,
          script: idx === 0 ? prompt.slice(0, 100) : "Synthesized presentation scene.",
        }));
      }

      const isNeuralLipSync = pipelineMode === "wav2lip_lip_sync";
      const generationType = isNeuralLipSync ? "AI Neural Lip-Synced Video" : "Rendered Avatar Video";

      // 6. Build new artifact card with real video URL
      const newArtifact: VideoArtifact = {
        id: createdProject.id,
        title: createdProject.title || prompt.slice(0, 40),
        status: "ready",
        aspectRatio: createdProject.aspect_ratio || "16:9",
        duration: totalDuration,
        sceneCount: scenesList.length || 1,
        scenes: scenesList,
        avatarId: resolvedAvatarId,
        voiceId: resolvedVoiceId,
        avatarName:
          context?.avatar?.name ||
          selectedPresenter?.name ||
          "Annie - Studio Presenter",
        voiceName: context?.voice?.name || "Annie - Lifelike",
        createdAt: createdProject.created_at || new Date().toISOString(),
        videoUrl: videoUrl,
        thumbnailUrl: thumbnailUrl,
        generationType: generationType,
        outputAssetId: outputAssetId,
      };

      setArtifacts((prev) => [newArtifact, ...prev]);
      setSelectedArtifact(newArtifact);
      setVideoTitle(newArtifact.title);
      setActiveGeneration((prev) =>
        prev
          ? {
              ...prev,
              status: "completed",
              projectId: createdProject.id,
              plannedDuration: totalDuration,
              targetDurationSeconds: durationToUse,
            }
          : null
      );

      // 7. Update agent message to completed state with honest rendering status & duration info
      const completionText = videoUrl
        ? `I've successfully generated and rendered your video project "${newArtifact.title}".\n\n• Duration: ${formatDurationMMSS(newArtifact.duration)}\n• Scenes: ${newArtifact.sceneCount}\n\nReal speech was synthesized via Piper TTS, scenes were composed with your presenter visual, and a full MP4 was rendered and uploaded to your asset storage (${generationType}). You can play the video right here or open in Studio to fine-tune.`
        : `I've created your video project "${newArtifact.title}".\n\n• Duration: ${formatDurationMMSS(newArtifact.duration)}\n• Scenes: ${newArtifact.sceneCount}\n\nTimeline and speech scripts are saved to your workspace. You can review the scenes below or open in Studio to edit and preview.`;

      setMessages((prev) =>
        prev.map((m) =>
          m.id === agentMsgId
            ? {
                ...m,
                status: "completed",
                text: completionText,
                stageMessage: undefined,
                projectId: newArtifact.id,
              }
            : m
        )
      );
    } catch (err: any) {
      console.error("Video Agent generation failed:", err);
      const isGpu =
        err.isGpuRequired ||
        (typeof err.message === "string" && err.message.includes("CUDA GPU")) ||
        (typeof err.message === "string" && err.message.includes("GPU_REQUIRED"));
      const errMsg = isGpu
        ? "Neural avatar generation requires a CUDA GPU."
        : (err.message || "Media generation job failed on server.");

      // Ensure failed generation clears any selected artifact so old presenter never displays
      setSelectedArtifact(null);

      // Load draft script / decomposed scenes if available from the project version
      let incompleteScenes: any[] = [];
      let plannedDuration = durationToUse;
      const failProjId = err.projectId || currentGenProjId;
      if (failProjId && effectiveWorkspaceId) {
        try {
          const latestVersion = await api.projects.getLatestVersion(
            effectiveWorkspaceId,
            failProjId
          );
          if (latestVersion?.document?.scenes) {
            incompleteScenes = latestVersion.document.scenes.map((sc: any, idx: number) => ({
              id: sc.id || `scene_${idx + 1}`,
              sequence: sc.sequence || idx + 1,
              duration: sc.duration || 10,
              heading: sc.layers?.find((l: any) => l.name === "Scene Heading")?.content?.text || `Scene ${idx + 1}`,
              script: sc.speech?.script || "Synthesized presentation scene.",
            }));
            plannedDuration =
              latestVersion.document.settings?.total_duration ||
              ((latestVersion.document as any)?.metadata?.actual_planned_duration_seconds as number) ||
              ((latestVersion.document as any)?.metadata?.target_duration_seconds as number) ||
              incompleteScenes.reduce((acc, s) => acc + (s.duration || 0), 0) ||
              durationToUse;
          }
        } catch (fetchErr) {
          console.warn("Could not fetch draft project version on failure:", fetchErr);
        }
      }

      setActiveGeneration((prev) => ({
        id: genReqId,
        status: "failed",
        error: errMsg,
        isGpuRequired: Boolean(isGpu),
        projectId: failProjId,
        incompleteScenes: incompleteScenes.length > 0 ? incompleteScenes : prev?.incompleteScenes,
        plannedDuration: plannedDuration || prev?.plannedDuration || durationToUse,
        targetDurationSeconds: durationToUse,
        prompt,
        context,
        startedAt: prev?.startedAt || Date.now(),
      }));

      setMessages((prev) =>
        prev.map((m) =>
          m.id === agentMsgId
            ? {
                ...m,
                status: "failed",
                text: errMsg,
                stageMessage: undefined,
              }
            : m
        )
      );
    } finally {
      setIsGenerating(false);
    }
  };

  const handleSendPrompt = () => {
    if (!composerText.trim() || isGenerating) return;
    const promptToSend = composerText.trim();
    setComposerText("");

    const presenterToSend = selectedPresenter
      ? {
          id: selectedPresenter.id,
          name: selectedPresenter.name,
          image: selectedPresenter.preview_url || selectedPresenter.image,
          preview_url: selectedPresenter.preview_url || selectedPresenter.image,
        }
      : generationContext?.avatar || {
          id:
            selectedArtifact?.avatarId ||
            selectedArtifact?.scenes[0]?.avatarId ||
            "30000000-0000-0000-0000-000000000002",
          name: selectedArtifact?.avatarName || "Annie - Studio Presenter",
        };

    executeGeneration(promptToSend, {
      ...generationContext,
      prompt: promptToSend,
      avatar: presenterToSend,
      voice: generationContext?.voice || {
        id: selectedArtifact?.voiceId || "10000000-0000-0000-0000-000000000003",
        name: selectedArtifact?.voiceName || "Annie - Lifelike",
      },
      target_duration_seconds: selectedDurationSeconds,
      attachments: attachedFiles,
    });
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendPrompt();
    }
  };

  return (
    <div
      id="video-agent-workspace"
      data-testid="video-agent-workspace"
      className={`h-screen w-screen flex flex-col overflow-hidden font-sans select-none transition-colors ${
        isLight ? "bg-slate-50 text-slate-900" : "bg-[#07090e] text-slate-100"
      }`}
    >
      {/* ============================================================ */}
      {/* 1. TOP HEADER */}
      {/* ============================================================ */}
      <header
        className={`h-13 border-b px-4 flex items-center justify-between flex-shrink-0 z-30 transition-colors ${
          isLight
            ? "border-slate-200 bg-white shadow-xs"
            : "border-[#1b253e] bg-[#0a0e19]"
        }`}
      >
        {/* Left: Home Navigation & Project Breadcrumb */}
        <div className="flex items-center gap-3">
          <button
            type="button"
            id="video-agent-home-btn"
            data-testid="video-agent-home-btn"
            onClick={onBackToDashboard}
            className={`flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-xl transition-all cursor-pointer shadow-sm active:scale-95 ${
              isLight
                ? "text-slate-700 hover:text-slate-900 bg-slate-100 hover:bg-slate-200 border border-slate-300"
                : "text-slate-300 hover:text-white bg-[#121828] hover:bg-[#1a233a] border border-[#222f4d] hover:border-cyan-500/40"
            }`}
            title="Return to Dashboard"
          >
            <Home size={14} className={isLight ? "text-blue-600" : "text-cyan-400"} />
            <span>Home</span>
          </button>

          <span className={isLight ? "text-slate-400 text-sm" : "text-slate-600 text-sm"}>/</span>

          <div className="flex items-center gap-2">
            <span
              className={`text-xs font-bold tracking-tight max-w-[220px] md:max-w-xs truncate ${
                isLight ? "text-slate-900" : "text-slate-200"
              }`}
            >
              {videoTitle}
            </span>
            <span
              className={`text-[10px] px-2 py-0.5 rounded-full font-semibold flex items-center gap-1 border ${
                isLight
                  ? "bg-blue-50 text-blue-700 border-blue-200"
                  : "bg-cyan-500/10 text-cyan-400 border-cyan-500/30"
              }`}
            >
              <Sparkles size={10} /> Video Agent
            </span>
          </div>
        </div>

        {/* Right: Share, Private & Workspace Badges */}
        <div className="flex items-center gap-2.5">
          <button
            type="button"
            onClick={() => setIsShareModalOpen(true)}
            className={`text-xs font-semibold px-3 py-1.5 rounded-xl flex items-center gap-1.5 transition-all cursor-pointer ${
              isLight
                ? "text-slate-700 hover:text-slate-900 bg-slate-100 hover:bg-slate-200 border border-slate-300"
                : "text-slate-300 hover:text-white bg-[#121828] hover:bg-[#192238] border border-[#222f4d]"
            }`}
          >
            <Share2 size={13} className={isLight ? "text-blue-600" : "text-blue-400"} />
            <span>Share</span>
          </button>

          <div
            className={`hidden sm:flex items-center gap-1 text-[11px] px-2.5 py-1 rounded-xl border ${
              isLight
                ? "text-slate-700 bg-slate-100 border-slate-300"
                : "text-slate-400 bg-[#0d1222] border-[#1b253e]"
            }`}
          >
            <Lock size={11} className={isLight ? "text-amber-600" : "text-amber-400"} />
            <span>Private</span>
          </div>

          <div
            className={`flex items-center gap-1.5 text-xs px-3 py-1 rounded-xl border ${
              isLight
                ? "text-slate-800 bg-slate-100 border-slate-300"
                : "text-slate-300 bg-[#0d1222] border-[#1b253e]"
            }`}
          >
            <Building2 size={13} className={isLight ? "text-blue-600" : "text-cyan-400"} />
            <span className="max-w-[130px] truncate">{effectiveWorkspaceName}</span>
          </div>
        </div>
      </header>

      {/* ============================================================ */}
      {/* 2. MAIN 2-COLUMN WORKSPACE LAYOUT */}
      {/* ============================================================ */}
      <div className="flex-1 flex overflow-hidden">
        {/* ============================================================ */}
        {/* LEFT COLUMN: CONVERSATION / AGENT PANEL */}
        {/* ============================================================ */}
        <div
          className={`w-80 md:w-96 border-r flex flex-col h-full flex-shrink-0 transition-colors ${
            isLight
              ? "border-slate-200 bg-white"
              : "border-[#18233a] bg-[#090d17]"
          }`}
        >
          {/* Conversation Header */}
          <div
            className={`p-3.5 border-b flex items-center gap-2.5 ${
              isLight
                ? "border-slate-200 bg-slate-50"
                : "border-[#18233a] bg-[#0b101c]"
            }`}
          >
            <div
              className={`w-8 h-8 rounded-xl flex items-center justify-center shadow-sm ${
                isLight
                  ? "bg-blue-50 border border-blue-200 text-blue-600"
                  : "bg-gradient-to-tr from-cyan-500/20 via-blue-500/20 to-purple-500/20 border border-cyan-500/30 text-cyan-400"
              }`}
            >
              <Bot size={16} />
            </div>
            <div>
              <h3
                className={`text-xs font-bold flex items-center gap-1.5 ${
                  isLight ? "text-slate-900" : "text-white"
                }`}
              >
                HeyZen Agent <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
              </h3>
              <p className={isLight ? "text-[10px] text-slate-500" : "text-[10px] text-slate-400"}>
                Conversational Video Co-pilot
              </p>
            </div>
          </div>

          {/* Messages Scroll Area */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-thin scrollbar-thumb-slate-800">
            {/* WORKFLOW CONTEXT BANNER (when launched from PPT/PDF or Cinematic Shots) */}
            {generationContext?.workflowIntent && (
              <div
                id="video-agent-workflow-context"
                data-testid="video-agent-workflow-context"
                className={`p-4 rounded-2xl border shadow-lg transition-all mb-4 ${
                  generationContext.workflowIntent === "ppt_pdf_to_video"
                    ? isLight
                      ? "bg-rose-50/90 border-rose-200 text-rose-950"
                      : "bg-[#180f1d] border-rose-500/40 text-rose-100"
                    : isLight
                    ? "bg-violet-50/90 border-violet-200 text-violet-950"
                    : "bg-[#141028] border-violet-500/40 text-violet-100"
                }`}
              >
                <div className="flex items-center justify-between gap-3 mb-2.5">
                  <div className="flex items-center gap-2.5">
                    <span className="p-2 rounded-xl bg-white/10 text-white flex items-center justify-center">
                      {generationContext.workflowIntent === "ppt_pdf_to_video" ? (
                        <FileText size={18} className="text-rose-400" />
                      ) : (
                        <Camera size={18} className="text-violet-400" />
                      )}
                    </span>
                    <div>
                      <h4 className="text-xs font-black uppercase tracking-wider flex items-center gap-1.5">
                        <span id="workflow-context-label">
                          {generationContext.workflowLabel ||
                            (generationContext.workflowIntent === "ppt_pdf_to_video"
                              ? "PPT/PDF to Video"
                              : "Cinematic Shots")}
                        </span>
                        <span className="text-[10px] px-2 py-0.5 rounded-full font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                          Active Workflow Context
                        </span>
                      </h4>
                      <p className="text-[11px] opacity-80 mt-0.5">
                        {generationContext.workflowIntent === "ppt_pdf_to_video"
                          ? "Turn presentation decks into structured timeline scenes with presenter narration"
                          : "Hollywood-grade framing, camera motion, lighting, and visual depth"}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Configuration parameters chips */}
                {generationContext.modalConfiguration && (
                  <div
                    id="workflow-context-config"
                    data-testid="workflow-context-config"
                    className="flex flex-wrap gap-1.5 text-[10px] pt-1"
                  >
                    {Object.entries(generationContext.modalConfiguration).map(([key, val]) => {
                      if (!val || typeof val === "object") return null;
                      return (
                        <span
                          key={key}
                          className="px-2 py-1 rounded-lg font-medium border bg-black/25 border-white/10"
                        >
                          <strong className="opacity-70 capitalize">
                            {key.replace(/([A-Z])/g, " $1")}:
                          </strong>{" "}
                          <span>{String(val)}</span>
                        </span>
                      );
                    })}
                  </div>
                )}

                {/* Attachment chip if present */}
                {generationContext.attachment && (
                  <div
                    id="workflow-context-attachment"
                    data-testid="workflow-context-attachment"
                    className="mt-2.5 flex items-center gap-2 p-2 rounded-xl bg-black/30 border border-white/10 text-[11px]"
                  >
                    <FileText size={14} className="text-rose-400 shrink-0" />
                    <span className="font-semibold truncate">
                      {generationContext.attachment.name || "Attachment"}
                    </span>
                    {generationContext.attachment.slideCount && (
                      <span className="text-[10px] opacity-75">
                        ({generationContext.attachment.slideCount} slides)
                      </span>
                    )}
                  </div>
                )}

                {/* Honest backend parsing notice for PPT/PDF */}
                {generationContext.workflowIntent === "ppt_pdf_to_video" && (
                  <p className="mt-2 text-[10px] opacity-75 italic leading-tight">
                    ℹ️ Direct binary PPT/PDF document slide extraction is currently unavailable on the backend. Scene plan, slide sequence, and presenter narration will be structured from your deck configuration and prompt instructions.
                  </p>
                )}
              </div>
            )}

            {messages.map((msg) => {
              const isUser = msg.sender === "user";

              if (isUser) {
                return (
                  <div key={msg.id} className="flex flex-col items-end gap-1.5">
                    <div className="max-w-[90%] bg-blue-600 text-white p-3 rounded-2xl rounded-tr-sm text-xs shadow-md border border-blue-500">
                      <p className="leading-relaxed whitespace-pre-wrap">{msg.text}</p>
                    </div>

                    {/* Metadata tags */}
                    {msg.config && (
                      <div className="flex flex-wrap items-center justify-end gap-1 text-[10px] text-slate-400">
                        {msg.config.avatarName && (
                          <span
                            className={`px-1.5 py-0.5 rounded-md border ${
                              isLight
                                ? "bg-slate-100 border-slate-200 text-slate-700"
                                : "bg-[#101828] border-[#1d2944] text-slate-300"
                            }`}
                          >
                            👤 {msg.config.avatarName}
                          </span>
                        )}
                        {msg.config.voiceName && (
                          <span
                            className={`px-1.5 py-0.5 rounded-md border ${
                              isLight
                                ? "bg-slate-100 border-slate-200 text-slate-700"
                                : "bg-[#101828] border-[#1d2944] text-slate-300"
                            }`}
                          >
                            🎙️ {msg.config.voiceName}
                          </span>
                        )}
                        {msg.config.captions && (
                          <span
                            className={`px-1.5 py-0.5 rounded-md border ${
                              isLight
                                ? "bg-blue-50 border-blue-200 text-blue-700 font-semibold"
                                : "bg-[#101828] border-[#1d2944] text-cyan-400"
                            }`}
                          >
                            CC ON
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                );
              }

              // Agent message
              return (
                <div key={msg.id} className="flex items-start gap-2.5">
                  <div
                    className={`w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5 border ${
                      isLight
                        ? "bg-blue-50 border-blue-200 text-blue-600"
                        : "bg-cyan-500/15 border-cyan-500/30 text-cyan-400"
                    }`}
                  >
                    <Sparkles size={13} />
                  </div>

                  <div className="flex-1 space-y-2">
                    <div
                      className={`p-3.5 rounded-2xl rounded-tl-sm text-xs leading-relaxed border shadow-xs ${
                        msg.status === "generating"
                          ? isLight
                            ? "bg-blue-50 border-blue-200 text-blue-900"
                            : "bg-gradient-to-r from-[#0d1629] to-[#0a1122] border-cyan-500/40 text-cyan-200"
                          : msg.status === "failed"
                          ? isLight
                            ? "bg-rose-50 border-rose-200 text-rose-800"
                            : "bg-rose-950/20 border-rose-500/30 text-rose-300"
                          : isLight
                          ? "bg-slate-100 border-slate-200 text-slate-800"
                          : "bg-[#101828] border-[#1d2944] text-slate-200"
                      }`}
                    >
                      {msg.status === "generating" ? (
                        <div className="space-y-2">
                          <div
                            className={`flex items-center gap-2 font-bold text-xs ${
                              isLight ? "text-blue-700" : "text-cyan-300"
                            }`}
                          >
                            <RefreshCw size={13} className={`animate-spin ${isLight ? "text-blue-600" : "text-cyan-400"}`} />
                            <span>Generating Video Project...</span>
                          </div>
                          <p className={isLight ? "text-[11px] text-slate-600" : "text-[11px] text-slate-400"}>
                            {msg.stageMessage}
                          </p>
                          <div className={`w-full h-1.5 rounded-full overflow-hidden ${isLight ? "bg-slate-200" : "bg-[#080c16]"}`}>
                            <div className="h-full bg-gradient-to-r from-blue-600 to-indigo-600 animate-pulse w-3/4 rounded-full"></div>
                          </div>
                        </div>
                      ) : (
                        <p className="whitespace-pre-wrap">{msg.text}</p>
                      )}
                    </div>

                    {/* Agent Action Buttons if Completed */}
                    {msg.status === "completed" && msg.projectId && (
                      <div className="flex flex-wrap items-center gap-2 pt-1">
                        <button
                          type="button"
                          onClick={() => onOpenStudio?.(msg.projectId)}
                          className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-bold text-[11px] px-3.5 py-1.5 rounded-xl flex items-center gap-1.5 shadow-md shadow-blue-500/20 transition-all cursor-pointer"
                        >
                          <Clapperboard size={12} />
                          <span>Open in Studio</span>
                        </button>
                        <button
                          type="button"
                          onClick={() => setActiveTab("artifacts")}
                          className={`font-medium text-[11px] px-3 py-1.5 rounded-xl flex items-center gap-1 transition-all cursor-pointer border ${
                            isLight
                              ? "bg-slate-100 hover:bg-slate-200 border-slate-300 text-slate-700"
                              : "bg-[#12192c] hover:bg-[#1a253f] border-[#223354] text-slate-300 hover:text-white"
                          }`}
                        >
                          <span>View Artifacts →</span>
                        </button>
                      </div>
                    )}

                    {/* Retry button if failed */}
                    {msg.status === "failed" && (
                      <button
                        type="button"
                        onClick={handleRetry}
                        className="text-xs text-rose-500 hover:text-rose-600 font-semibold underline underline-offset-2 flex items-center gap-1 pt-1 cursor-pointer transition-all active:scale-95"
                      >
                        <RefreshCw size={12} /> Retry Generation
                      </button>
                    )}

                    {/* Suggested Initial Actions (if on initial message) */}
                    {msg.id === "msg_init" && messages.length === 1 && (
                      <div className="flex flex-col gap-1.5 pt-2">
                        <button
                          type="button"
                          onClick={() => {
                            setComposerText("Create a high-converting UGC video ad showcasing your software features");
                            composerInputRef.current?.focus();
                          }}
                          className={`text-left text-xs p-2.5 rounded-xl transition-all flex items-center justify-between cursor-pointer group border ${
                            isLight
                              ? "bg-slate-50 hover:bg-slate-100 border-slate-200 hover:border-blue-400 text-slate-700 hover:text-slate-900"
                              : "bg-[#101828] hover:bg-[#162238] border-[#1e2c49] hover:border-cyan-500/40 text-slate-300 hover:text-white"
                          }`}
                        >
                          <span className="flex items-center gap-2">
                            <span>🎬</span> Create a video
                          </span>
                          <ChevronRight
                            size={13}
                            className={`transition-colors ${
                              isLight ? "text-slate-400 group-hover:text-blue-600" : "text-slate-500 group-hover:text-cyan-400"
                            }`}
                          />
                        </button>

                        <button
                          type="button"
                          onClick={() => {
                            if (artifacts.length > 0) {
                              setActiveTab("artifacts");
                            } else {
                              onOpenStudio?.();
                            }
                          }}
                          className={`text-left text-xs p-2.5 rounded-xl transition-all flex items-center justify-between cursor-pointer group border ${
                            isLight
                              ? "bg-slate-50 hover:bg-slate-100 border-slate-200 hover:border-blue-400 text-slate-700 hover:text-slate-900"
                              : "bg-[#101828] hover:bg-[#162238] border-[#1e2c49] hover:border-blue-500/40 text-slate-300 hover:text-white"
                          }`}
                        >
                          <span className="flex items-center gap-2">
                            <span>✂️</span> Edit a video
                          </span>
                          <ChevronRight
                            size={13}
                            className={`transition-colors ${
                              isLight ? "text-slate-400 group-hover:text-blue-600" : "text-slate-500 group-hover:text-blue-400"
                            }`}
                          />
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* ============================================================ */}
        {/* CENTER / RIGHT COLUMN: ARTIFACTS / RESOURCES WORKSPACE */}
        {/* ============================================================ */}
        <div
          className={`flex-1 flex flex-col h-full overflow-hidden transition-colors ${
            isLight ? "bg-slate-50" : "bg-[#07090e]"
          }`}
        >
          {/* Tabs Strip */}
          <div
            className={`px-6 pt-3 pb-2 border-b flex items-center gap-3 transition-colors ${
              isLight
                ? "border-slate-200 bg-white"
                : "border-[#18233a] bg-[#0a0e19]"
            }`}
          >
            <button
              type="button"
              onClick={() => setActiveTab("artifacts")}
              className={`text-xs font-bold px-4 py-1.5 rounded-full transition-all flex items-center gap-1.5 cursor-pointer ${
                activeTab === "artifacts"
                  ? isLight
                    ? "bg-blue-50 text-blue-700 border border-blue-200 shadow-xs"
                    : "bg-cyan-500/15 text-cyan-300 border border-cyan-500/40 shadow-sm"
                  : isLight
                  ? "text-slate-600 hover:text-slate-900"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              <Film size={13} />
              <span>Artifacts</span>
              {artifacts.length > 0 && (
                <span
                  className={`w-4 h-4 rounded-full font-extrabold text-[10px] flex items-center justify-center ml-0.5 ${
                    isLight ? "bg-blue-600 text-white" : "bg-cyan-500 text-slate-950"
                  }`}
                >
                  {artifacts.length}
                </span>
              )}
            </button>

            <button
              type="button"
              onClick={() => setActiveTab("resources")}
              className={`text-xs font-bold px-4 py-1.5 rounded-full transition-all flex items-center gap-1.5 cursor-pointer ${
                activeTab === "resources"
                  ? isLight
                    ? "bg-blue-50 text-blue-700 border border-blue-200 shadow-xs"
                    : "bg-cyan-500/15 text-cyan-300 border border-cyan-500/40 shadow-sm"
                  : isLight
                  ? "text-slate-600 hover:text-slate-900"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              <Layers size={13} />
              <span>Resources</span>
            </button>
          </div>

          {/* Main Content Workspace Body */}
          <div className="flex-1 overflow-y-auto p-6 scrollbar-thin scrollbar-thumb-slate-800 flex flex-col">
            {activeTab === "artifacts" ? (
              (activeGeneration?.status === "queued" || activeGeneration?.status === "running") ? (
                /* State 1: Active Generation (Queued / Running) */
                <div className="max-w-4xl w-full mx-auto space-y-6">
                  <div className="bg-[#0b101d] border border-cyan-500/40 rounded-3xl overflow-hidden shadow-2xl p-5">
                    <div className="relative aspect-video w-full rounded-2xl bg-[#080c16] border border-cyan-500/30 overflow-hidden flex flex-col items-center justify-center p-6 text-center group shadow-inner">
                      {/* Avatar Portrait Presenter Backdrop with Darkened Overlay */}
                      <img
                        src={
                          selectedPresenter?.preview_url ||
                          selectedPresenter?.image ||
                          backendAvatars.find(
                            (a) =>
                              a.id === activeGeneration?.context?.avatar?.id
                          )?.preview_url ||
                          AVATAR_OPTIONS.find((a) =>
                            a.name.toLowerCase().includes("annie")
                          )?.image ||
                          AVATAR_OPTIONS[0].image
                        }
                        alt={selectedPresenter?.name || "Presenter Avatar"}
                        className="absolute inset-0 w-full h-full object-cover object-top opacity-30 blur-xs"
                      />
                      <div className="absolute inset-0 bg-gradient-to-t from-[#07090e] via-[#07090e]/75 to-[#07090e]/50"></div>

                      {/* Top Badges */}
                      <div className="absolute top-4 left-4 right-4 flex items-center justify-between z-10">
                        <span className="bg-[#0b101d]/90 border border-[#233355] text-white text-xs font-bold px-3 py-1 rounded-full shadow-md backdrop-blur-md">
                          {videoTitle}
                        </span>
                        <span className="bg-cyan-500/20 border border-cyan-500/40 text-cyan-300 text-[11px] font-bold px-2.5 py-1 rounded-full flex items-center gap-1.5 backdrop-blur-md animate-pulse">
                          <RefreshCw size={12} className="animate-spin text-cyan-400" /> Generating...
                        </span>
                      </div>

                      {/* Center Spinner and Stage Message */}
                      <div className="relative z-10 flex flex-col items-center gap-3 max-w-md">
                        <div className="w-14 h-14 rounded-2xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400 shadow-lg shadow-cyan-500/20 animate-pulse">
                          <Sparkles size={28} />
                        </div>
                        <h4 className="text-white font-bold text-sm tracking-wide">
                          Synthesizing & Rendering Video
                        </h4>
                        <p className="text-slate-300 text-xs leading-relaxed">
                          {activeGeneration?.stageMessage || "Decomposing prompt into multi-scene timeline & speech scripts..."}
                        </p>
                        <div className="w-48 bg-[#0b101d] h-1.5 rounded-full overflow-hidden border border-cyan-500/30 mt-1">
                          <div className="h-full bg-gradient-to-r from-cyan-500 via-blue-500 to-indigo-500 animate-pulse w-3/4 rounded-full"></div>
                        </div>
                      </div>

                      {/* Bottom Info Bar */}
                      <div className="absolute bottom-4 left-4 right-4 flex items-center justify-between z-10 text-xs text-slate-400">
                        <div className="flex items-center gap-2">
                          <span className="bg-black/80 px-2.5 py-1 rounded-md text-[11px] font-medium text-slate-300">
                            3 Scenes (estimated)
                          </span>
                          <span className="bg-black/80 px-2.5 py-1 rounded-md text-[11px] font-medium text-slate-300">
                            ~15s - 30s
                          </span>
                        </div>
                        <span className="bg-black/80 px-2.5 py-1 rounded-md text-[11px] font-medium text-cyan-400">
                          16:9 1080p
                        </span>
                      </div>
                    </div>

                    {/* Action Status Bar */}
                    <div className="mt-4 flex items-center justify-between pt-2">
                      <span className="text-xs text-slate-400 flex items-center gap-2">
                        <RefreshCw size={12} className="animate-spin text-cyan-400" />
                        <span>Generating media pipeline assets...</span>
                      </span>
                    </div>
                  </div>
                </div>
              ) : activeGeneration?.status === "failed" ? (
                /* State 2: Generation Failed View */
                <div className="max-w-4xl w-full mx-auto space-y-6">
                  <div className="bg-[#0b101d] border border-rose-500/40 rounded-3xl overflow-hidden shadow-2xl p-5 space-y-5">
                    <div className="relative aspect-video w-full rounded-2xl bg-[#080c16] border border-rose-500/30 overflow-hidden flex flex-col items-center justify-center p-6 text-center shadow-inner">
                      <div className="absolute inset-0 bg-gradient-to-b from-rose-950/20 via-[#07090e]/80 to-[#07090e]"></div>

                      {/* Top Badges */}
                      <div className="absolute top-4 left-4 right-4 flex items-center justify-between z-10">
                        <span className="bg-[#0b101d]/90 border border-[#233355] text-white text-xs font-bold px-3 py-1 rounded-full shadow-md backdrop-blur-md">
                          {videoTitle}
                        </span>
                        <span className="bg-rose-500/20 border border-rose-500/40 text-rose-400 text-[11px] font-bold px-2.5 py-1 rounded-full flex items-center gap-1 backdrop-blur-md">
                          <AlertCircle size={12} /> {activeGeneration?.isGpuRequired ? "GPU Required" : "Generation Failed"}
                        </span>
                      </div>

                      {/* Center Error Content */}
                      <div className="relative z-10 flex flex-col items-center gap-3 max-w-md">
                        <div className="w-12 h-12 rounded-2xl bg-rose-500/10 border border-rose-500/30 flex items-center justify-center text-rose-400 shadow-lg shadow-rose-500/20">
                          <AlertTriangle size={24} />
                        </div>
                        <h4 className="text-white font-bold text-sm">
                          {activeGeneration?.isGpuRequired
                            ? "Neural avatar generation requires a CUDA GPU."
                            : "Media Generation Failed"}
                        </h4>
                        <p className="text-rose-300/90 text-xs leading-relaxed max-w-sm">
                          {activeGeneration?.isGpuRequired
                            ? "This machine is running on CPU. Real neural avatar rendering requires an active CUDA GPU or remote GPU worker. No fake or placeholder video was generated."
                            : activeGeneration?.error || "Media generation job failed on server."}
                        </p>
                        <div className="flex items-center gap-2 mt-2">
                          <button
                            type="button"
                            onClick={handleRetry}
                            className="bg-gradient-to-r from-rose-600 to-rose-700 hover:from-rose-500 hover:to-rose-600 text-white font-bold text-xs px-5 py-2.5 rounded-xl shadow-lg shadow-rose-600/30 flex items-center gap-2 cursor-pointer transition-all active:scale-95"
                          >
                            <RefreshCw size={13} />
                            <span>Retry Generation</span>
                          </button>
                          {activeGeneration?.projectId && (
                            <button
                              type="button"
                              onClick={() => onOpenStudio?.(activeGeneration.projectId)}
                              className="bg-[#12192c] hover:bg-[#1a253f] border border-[#233355] text-slate-200 hover:text-white font-semibold text-xs px-4 py-2.5 rounded-xl flex items-center gap-1.5 transition-all cursor-pointer"
                            >
                              <Clapperboard size={13} />
                              <span>Open Draft in Studio</span>
                            </button>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Requirement 3: Keep successfully generated project/script information, clearly marked as Draft / Generation incomplete */}
                    {activeGeneration?.incompleteScenes && activeGeneration.incompleteScenes.length > 0 && (
                      <div className="border border-amber-500/30 bg-[#0d1322] rounded-2xl p-4">
                        <div className="flex flex-wrap items-center justify-between gap-2 mb-3 border-b border-[#1b2844] pb-2">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="bg-amber-500/20 border border-amber-500/40 text-amber-300 text-[11px] font-bold px-2 py-0.5 rounded-md">
                              Draft / Generation incomplete
                            </span>
                            <span className="text-xs text-slate-300 font-semibold bg-[#121a2d] px-2.5 py-0.5 rounded-md border border-[#1e2d4a]">
                              Duration: <span className="text-white font-bold">{formatDurationMMSS(activeGeneration.plannedDuration || activeGeneration.incompleteScenes.reduce((acc, s) => acc + (s.duration || 0), 0))}</span>
                            </span>
                            <span className="text-xs text-slate-300 font-semibold bg-[#121a2d] px-2.5 py-0.5 rounded-md border border-[#1e2d4a]">
                              Scenes: <span className="text-white font-bold">{activeGeneration.incompleteScenes.length}</span>
                            </span>
                            <span className="text-xs text-slate-400">
                              (neural avatar rendering requires CUDA GPU)
                            </span>
                          </div>
                          {activeGeneration.projectId && (
                            <button
                              type="button"
                              onClick={() => onOpenStudio?.(activeGeneration.projectId)}
                              className="text-xs text-cyan-400 hover:text-cyan-300 font-medium flex items-center gap-1 cursor-pointer"
                            >
                              <span>Open in Studio →</span>
                            </button>
                          )}
                        </div>

                        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 max-h-[460px] overflow-y-auto pr-1">
                          {activeGeneration.incompleteScenes.map((sc, idx) => (
                            <div
                              key={sc.id || idx}
                              className="bg-[#080c16] border border-[#1b2742] rounded-xl p-3 flex flex-col justify-between"
                            >
                              <div>
                                <div className="flex items-center justify-between mb-1.5">
                                  <span className="text-[10px] font-bold text-amber-400 bg-amber-500/10 px-1.5 py-0.5 rounded">
                                    Scene {idx + 1 < 10 ? `0${idx + 1}` : idx + 1}
                                  </span>
                                  <span className="text-[10px] text-slate-400 flex items-center gap-1">
                                    <Clock size={10} /> {sc.duration}s
                                  </span>
                                </div>
                                <h5 className="text-xs font-bold text-white mb-1 truncate">
                                  {sc.heading || `Scene ${idx + 1}`}
                                </h5>
                                <p className="text-[11px] text-slate-300 italic line-clamp-3 leading-relaxed">
                                  &ldquo;{sc.script}&rdquo;
                                </p>
                              </div>
                              <div className="mt-2 pt-1.5 border-t border-[#141d30] text-[10px] text-slate-400">
                                <span>Draft Script — No Video Asset</span>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ) : selectedArtifact ? (
                /* State 3: Selected Artifact (Completed Video or Draft Project) */
                <div className="max-w-4xl w-full mx-auto space-y-6">
                  <div
                    className={`rounded-3xl overflow-hidden p-5 transition-colors border ${
                      isLight
                        ? "bg-white border-slate-200 shadow-md"
                        : "bg-[#0b101d] border-[#1e2c48] shadow-2xl"
                    }`}
                  >
                    {/* Video Player Canvas Card or Draft Notice */}
                    {selectedArtifact.videoUrl ? (
                      <div className="relative aspect-video w-full rounded-2xl bg-black border border-slate-700/40 overflow-hidden flex items-center justify-center group shadow-inner">
                        <video
                          key={selectedArtifact.videoUrl}
                          src={selectedArtifact.videoUrl}
                          controls
                          playsInline
                          poster={selectedArtifact.thumbnailUrl || AVATAR_OPTIONS[0].image}
                          className="w-full h-full object-contain bg-black"
                        />
                      </div>
                    ) : (
                      /* Draft project view - clearly marked as Draft / Generation incomplete */
                      <div className="relative aspect-video w-full rounded-2xl bg-[#080c16] border border-amber-500/30 overflow-hidden flex flex-col items-center justify-center p-6 text-center group shadow-inner">
                        <div className="absolute inset-0 bg-gradient-to-t from-[#07090e] via-[#07090e]/80 to-[#07090e]/50"></div>

                        {/* Top Badges */}
                        <div className="absolute top-4 left-4 right-4 flex items-center justify-between z-10">
                          <span className="bg-[#0b101d]/90 border border-[#233355] text-white text-xs font-bold px-3 py-1 rounded-full shadow-md backdrop-blur-md">
                            {selectedArtifact.title}
                          </span>
                          <span className="bg-amber-500/20 border border-amber-500/40 text-amber-300 text-[11px] font-bold px-2.5 py-1 rounded-full flex items-center gap-1 backdrop-blur-md">
                            Draft / Generation incomplete
                          </span>
                        </div>

                        {/* Center Incomplete Notice */}
                        <div className="relative z-10 flex flex-col items-center gap-2.5 max-w-md">
                          <div className="w-12 h-12 rounded-2xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400 shadow-lg shadow-amber-500/20">
                            <Clapperboard size={24} />
                          </div>
                          <h4 className="text-white font-bold text-sm">
                            Draft Project
                          </h4>
                          <p className="text-slate-400 text-xs leading-relaxed max-w-sm">
                            This project contains timeline scenes and speech scripts, but no rendered video asset exists.
                          </p>
                          <button
                            type="button"
                            onClick={() => onOpenStudio?.(selectedArtifact.id)}
                            className="mt-2 bg-gradient-to-r from-blue-600 via-indigo-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white font-bold text-xs px-5 py-2.5 rounded-xl shadow-lg shadow-blue-500/25 transition-all flex items-center gap-2 cursor-pointer active:scale-95"
                          >
                            <Clapperboard size={15} />
                            <span>Open in Studio</span>
                          </button>
                        </div>

                        {/* Bottom Info Bar inside card */}
                        <div className="absolute bottom-4 left-4 right-4 flex items-center justify-between z-10 text-xs text-slate-400">
                          <div className="flex items-center gap-2">
                            <span className="bg-black/70 px-2.5 py-1 rounded-md text-[11px] font-medium text-slate-300">
                              Duration: <b className="text-white">{formatDurationMMSS(selectedArtifact.duration)}</b>
                            </span>
                            <span className="bg-black/70 px-2.5 py-1 rounded-md text-[11px] font-medium text-slate-300">
                              Scenes: <b className="text-white">{selectedArtifact.sceneCount}</b>
                            </span>
                          </div>
                          <span className="bg-black/70 px-2.5 py-1 rounded-md text-[11px] font-medium text-amber-400">
                            Draft
                          </span>
                        </div>
                      </div>
                    )}

                    {/* Primary Actions Strip */}
                    <div className="mt-4 flex flex-wrap items-center justify-between gap-3 pt-2">
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => onOpenStudio?.(selectedArtifact.id)}
                          className="bg-gradient-to-r from-blue-600 via-indigo-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white font-bold text-xs px-5 py-2.5 rounded-xl shadow-lg shadow-blue-500/25 transition-all flex items-center gap-2 cursor-pointer active:scale-95"
                        >
                          <Clapperboard size={15} />
                          <span>Open in Studio</span>
                        </button>

                        {selectedArtifact.videoUrl && (
                          <>
                            <button
                              type="button"
                              onClick={() => setIsPreviewOpen(true)}
                              className={`font-semibold text-xs px-4 py-2.5 rounded-xl flex items-center gap-1.5 transition-all cursor-pointer border ${
                                isLight
                                  ? "bg-slate-100 hover:bg-slate-200 border-slate-300 text-slate-700 hover:text-slate-900"
                                  : "bg-[#12192c] hover:bg-[#1a253f] border-[#233355] text-slate-200 hover:text-white"
                              }`}
                            >
                              <Play size={13} />
                              <span>Preview</span>
                            </button>

                            <a
                              href={selectedArtifact.videoUrl}
                              download={`${selectedArtifact.title.replace(/\s+/g, "_") || "video"}.mp4`}
                              className={`font-semibold text-xs px-4 py-2.5 rounded-xl flex items-center gap-1.5 transition-all cursor-pointer shadow-xs border ${
                                isLight
                                  ? "bg-blue-50 hover:bg-blue-100 border-blue-200 text-blue-700"
                                  : "bg-[#12192c] hover:bg-[#1a253f] border-cyan-500/40 text-cyan-300 hover:text-white"
                              }`}
                              title="Download Rendered MP4"
                            >
                              <Download size={13} />
                              <span>Download MP4</span>
                            </a>
                          </>
                        )}
                      </div>

                      <div
                        className={`flex items-center gap-2 text-xs ${
                          isLight ? "text-slate-600" : "text-slate-400"
                        }`}
                      >
                        {selectedArtifact.generationType && (
                          <span
                            className={`font-semibold px-2 py-0.5 rounded-md text-[11px] border ${
                              isLight
                                ? "bg-blue-50 border-blue-200 text-blue-700"
                                : "bg-cyan-950/70 border-cyan-500/30 text-cyan-400"
                            }`}
                          >
                            {selectedArtifact.generationType}
                          </span>
                        )}
                        <span>
                          Presenter:{" "}
                          <b className={isLight ? "text-slate-900" : "text-slate-200"}>
                            {selectedArtifact.avatarName}
                          </b>
                        </span>
                        <span>•</span>
                        <span>
                          Voice:{" "}
                          <b className={isLight ? "text-slate-900" : "text-slate-200"}>
                            {selectedArtifact.voiceName}
                          </b>
                        </span>
                      </div>
                    </div>

                    {/* Timeline Scenes Sequence Breakdown */}
                    <div
                      className={`mt-6 border-t pt-4 ${
                        isLight ? "border-slate-200" : "border-[#18233a]"
                      }`}
                    >
                      <div className="flex items-center justify-between mb-3">
                        <h4
                          className={`text-xs font-bold flex items-center gap-1.5 ${
                            isLight ? "text-slate-900" : "text-slate-300"
                          }`}
                        >
                          <Layers size={13} className={isLight ? "text-blue-600" : "text-cyan-400"} />
                          <span>Scene Breakdown</span>
                        </h4>
                        <div className="flex items-center gap-2">
                          <span
                            className={`px-2.5 py-0.5 rounded-md text-[11px] font-medium border ${
                              isLight
                                ? "bg-slate-100 border-slate-300 text-slate-700"
                                : "bg-[#12192c] border-[#233355] text-slate-300"
                            }`}
                          >
                            Duration:{" "}
                            <b className={isLight ? "text-slate-900" : "text-white"}>
                              {formatDurationMMSS(selectedArtifact.duration)}
                            </b>
                          </span>
                          <span
                            className={`px-2.5 py-0.5 rounded-md text-[11px] font-medium border ${
                              isLight
                                ? "bg-slate-100 border-slate-300 text-slate-700"
                                : "bg-[#12192c] border-[#233355] text-slate-300"
                            }`}
                          >
                            Scenes:{" "}
                            <b className={isLight ? "text-slate-900" : "text-white"}>
                              {selectedArtifact.sceneCount}
                            </b>
                          </span>
                        </div>
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 max-h-[460px] overflow-y-auto pr-1">
                        {selectedArtifact.scenes.map((sc, idx) => (
                          <div
                            key={sc.id}
                            className={`rounded-xl p-3.5 flex flex-col justify-between transition-all group border ${
                              isLight
                                ? "bg-white border-slate-200 hover:border-blue-400 shadow-xs"
                                : "bg-[#090d18] border-[#1b2742] hover:border-cyan-500/40"
                            }`}
                          >
                            <div>
                              <div className="flex items-center justify-between mb-2">
                                <span
                                  className={`text-[10px] font-bold px-2 py-0.5 rounded-md border ${
                                    isLight
                                      ? "text-blue-700 bg-blue-50 border-blue-200"
                                      : "text-cyan-400 bg-cyan-500/10 border-transparent"
                                  }`}
                                >
                                  Scene {idx + 1 < 10 ? `0${idx + 1}` : idx + 1}
                                </span>
                                <span
                                  className={`text-[10px] flex items-center gap-1 ${
                                    isLight ? "text-slate-500" : "text-slate-400"
                                  }`}
                                >
                                  <Clock size={10} /> {sc.duration}s
                                </span>
                              </div>
                              <h5
                                className={`text-xs font-bold mb-1.5 truncate ${
                                  isLight ? "text-slate-900" : "text-white"
                                }`}
                              >
                                {sc.heading || `Scene ${idx + 1}`}
                              </h5>
                              <p
                                className={`text-[11px] italic line-clamp-3 leading-relaxed ${
                                  isLight ? "text-slate-600" : "text-slate-300"
                                }`}
                              >
                                &ldquo;{sc.script}&rdquo;
                              </p>
                            </div>

                            <div
                              className={`mt-3 pt-2 border-t flex flex-wrap items-center justify-between gap-1.5 text-[10px] ${
                                isLight ? "border-slate-100 text-slate-500" : "border-[#141d30] text-slate-400"
                              }`}
                            >
                              <div className="flex items-center gap-1.5">
                                <span className={isLight ? "text-blue-700 font-medium" : "text-cyan-300 font-medium"}>
                                  {sc.avatarVideoAssetId || selectedArtifact.generationType?.includes("Neural")
                                    ? "🎬 Lip-Sync Presenter"
                                    : "👤 Presenter"}
                                </span>
                                {sc.cameraMotion && sc.cameraMotion !== "static" && (
                                  <span
                                    className={`px-1.5 py-0.5 rounded text-[9px] font-mono border ${
                                      isLight
                                        ? "bg-slate-100 border-slate-300 text-slate-700"
                                        : "bg-blue-950/80 border-blue-500/30 text-blue-300"
                                    }`}
                                  >
                                    🎥 {sc.cameraMotion.replace(/_/g, " ")}
                                  </span>
                                )}
                              </div>
                              <div className="flex items-center gap-1">
                                {sc.transition?.type && sc.transition.type !== "none" && (
                                  <span className={isLight ? "text-slate-500 text-[9px]" : "text-slate-400 text-[9px]"}>
                                    ⇋ {sc.transition.type}
                                  </span>
                                )}
                                <span className={isLight ? "text-blue-600 font-medium" : "text-cyan-400 font-medium"}>
                                  Captions
                                </span>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              ) : artifacts.length === 0 ? (
                /* State 4: Empty Artifacts State */
                <div className="flex-1 flex flex-col items-center justify-center text-center max-w-md mx-auto my-auto p-6 animate-in fade-in">
                  <div
                    className={`w-20 h-20 rounded-3xl flex items-center justify-center mb-4 shadow-xl relative border ${
                      isLight
                        ? "bg-blue-50 border-blue-200 text-blue-600"
                        : "bg-[#0f1628] border-[#233355] text-cyan-400 shadow-cyan-500/5"
                    }`}
                  >
                    <div
                      className={`absolute inset-0 rounded-3xl blur-xl ${
                        isLight ? "bg-blue-200/40" : "bg-cyan-500/10"
                      }`}
                    ></div>
                    <Clapperboard size={36} className="relative z-10" />
                  </div>
                  <h3
                    className={`text-base font-bold mb-2 ${
                      isLight ? "text-slate-900" : "text-white"
                    }`}
                  >
                    Your videos and assets will appear here
                  </h3>
                  <p
                    className={`text-xs leading-relaxed mb-6 font-normal ${
                      isLight ? "text-slate-600" : "text-slate-400"
                    }`}
                  >
                    Enter a prompt in the conversation on the left or use the composer below to begin generating scenes, avatar presenters, and video timelines.
                  </p>
                  <div className="flex flex-wrap justify-center gap-2">
                    {[
                      "Ads & Promo UGC video",
                      "Product Launch announcement",
                      "Step-by-step How-To guide",
                      "Company All-Hands brief",
                    ].map((sug) => (
                      <button
                        key={sug}
                        type="button"
                        onClick={() => {
                          setComposerText(sug);
                          composerInputRef.current?.focus();
                        }}
                        className={`text-[11px] px-3 py-1.5 rounded-full transition-all cursor-pointer border ${
                          isLight
                            ? "bg-white hover:bg-slate-100 border-slate-200 text-slate-700 hover:text-slate-900 shadow-xs"
                            : "bg-[#0e1424] hover:bg-[#152038] border-[#1f2c4a] text-slate-300 hover:text-white"
                        }`}
                      >
                        {sug}
                      </button>
                    ))}
                  </div>
                </div>
              ) : null
            ) : (
              /* Resources Tab */
              <div className="max-w-4xl w-full mx-auto space-y-6">
                {/* 1. Avatars in Workspace */}
                <div
                  className={`rounded-2xl p-4 transition-colors border ${
                    isLight
                      ? "bg-white border-slate-200 shadow-sm"
                      : "bg-[#0b101d] border-[#1e2c48]"
                  }`}
                >
                  <h4
                    className={`text-xs font-bold mb-3 flex items-center gap-2 ${
                      isLight ? "text-slate-900" : "text-white"
                    }`}
                  >
                    <UserIcon size={14} className={isLight ? "text-blue-600" : "text-cyan-400"} />
                    <span>Workspace Presenter Avatars</span>
                  </h4>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    {AVATAR_OPTIONS.slice(0, 4).map((av) => (
                      <div
                        key={av.id}
                        className={`rounded-xl p-2.5 flex items-center gap-2.5 border ${
                          isLight
                            ? "bg-slate-50 border-slate-200"
                            : "bg-[#090d18] border-[#1b2742]"
                        }`}
                      >
                        <img
                          src={av.image}
                          alt={av.name}
                          className="w-10 h-10 rounded-lg object-cover"
                        />
                        <div className="truncate">
                          <p
                            className={`text-xs font-bold truncate ${
                              isLight ? "text-slate-900" : "text-white"
                            }`}
                          >
                            {av.name}
                          </p>
                          <p className={isLight ? "text-[10px] text-slate-500" : "text-[10px] text-slate-400"}>
                            {av.label}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* 2. Voices in Workspace */}
                <div
                  className={`rounded-2xl p-4 transition-colors border ${
                    isLight
                      ? "bg-white border-slate-200 shadow-sm"
                      : "bg-[#0b101d] border-[#1e2c48]"
                  }`}
                >
                  <h4
                    className={`text-xs font-bold mb-3 flex items-center gap-2 ${
                      isLight ? "text-slate-900" : "text-white"
                    }`}
                  >
                    <Volume2 size={14} className={isLight ? "text-blue-600" : "text-blue-400"} />
                    <span>AI Voice Models</span>
                  </h4>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
                    {VOICE_OPTIONS.slice(0, 3).map((vc) => (
                      <div
                        key={vc.id}
                        className={`rounded-xl p-2.5 flex items-center justify-between border ${
                          isLight
                            ? "bg-slate-50 border-slate-200"
                            : "bg-[#090d18] border-[#1b2742]"
                        }`}
                      >
                        <div>
                          <p
                            className={`text-xs font-bold ${
                              isLight ? "text-slate-900" : "text-white"
                            }`}
                          >
                            {vc.name}
                          </p>
                          <p className={isLight ? "text-[10px] text-slate-500" : "text-[10px] text-slate-400"}>
                            {vc.style}
                          </p>
                        </div>
                        <span
                          className={`text-[10px] px-2 py-0.5 rounded-md font-semibold ${
                            isLight
                              ? "bg-blue-50 text-blue-700 border border-blue-200"
                              : "bg-blue-500/10 text-blue-400"
                          }`}
                        >
                          {vc.accent}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* 3. Attachments */}
                <div
                  className={`rounded-2xl p-4 flex items-center justify-between transition-colors border ${
                    isLight
                      ? "bg-white border-slate-200 shadow-sm"
                      : "bg-[#0b101d] border-[#1e2c48]"
                  }`}
                >
                  <div>
                    <h4
                      className={`text-xs font-bold flex items-center gap-2 ${
                        isLight ? "text-slate-900" : "text-white"
                      }`}
                    >
                      <FolderOpen size={14} className={isLight ? "text-amber-600" : "text-amber-400"} />
                      <span>Attached Assets & Media</span>
                    </h4>
                    <p className={isLight ? "text-[11px] text-slate-500 mt-1" : "text-[11px] text-slate-400 mt-1"}>
                      {attachedFiles.length > 0
                        ? `${attachedFiles.length} file(s) attached`
                        : "No extra files attached to this session."}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => setIsAttachModalOpen(true)}
                    className={`text-xs font-semibold px-3 py-1.5 rounded-xl transition-all cursor-pointer flex items-center gap-1.5 border ${
                      isLight
                        ? "bg-slate-100 hover:bg-slate-200 border-slate-300 text-slate-800"
                        : "bg-[#12192c] hover:bg-[#1a253f] border-[#233355] text-slate-200 hover:text-white"
                    }`}
                  >
                    <Plus size={13} /> Add Attachment
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* ============================================================ */}
          {/* 3. PERSISTENT BOTTOM PROMPT COMPOSER */}
          {/* ============================================================ */}
          <div
            className={`p-4 border-t transition-colors ${
              isLight ? "border-slate-200 bg-white" : "border-[#18233a] bg-[#0a0e19]"
            }`}
          >
            <div className="max-w-4xl mx-auto sm:pr-14">
              {/* Presenter & Duration Selector Strip */}
              <div className="flex flex-wrap items-center justify-between gap-2 mb-2 px-1">
                <div className="flex flex-wrap items-center gap-2">
                  <div className="relative">
                    <button
                      type="button"
                      id="presenter-selector-btn"
                      data-testid="presenter-selector-btn"
                      onClick={() => setIsPresenterPickerOpen((prev) => !prev)}
                      className={`flex items-center gap-2 px-2.5 py-1.5 rounded-xl border text-xs transition-all cursor-pointer shadow-sm group ${
                        isLight
                          ? "bg-slate-100 hover:bg-slate-200 border-slate-300 hover:border-blue-400 text-slate-800"
                          : "bg-[#0F172A] hover:bg-[#16233B] border-[#233554] hover:border-cyan-500/50 text-slate-200"
                      }`}
                      title="Choose Presenter"
                    >
                      <div className="relative w-6 h-6 rounded-full overflow-hidden border border-cyan-500/40 bg-slate-800 flex-shrink-0">
                        {selectedPresenter?.preview_url || selectedPresenter?.image ? (
                          <img
                            src={selectedPresenter.preview_url || selectedPresenter.image}
                            alt={selectedPresenter.name || "Presenter"}
                            className="w-full h-full object-cover object-top"
                          />
                        ) : (
                          <UserIcon size={14} className="text-slate-400 m-auto mt-1" />
                        )}
                      </div>
                      <div className="flex flex-col text-left">
                        <span className="text-[9px] text-slate-400 font-semibold tracking-wider uppercase leading-none">Presenter</span>
                        <span
                          className={`text-xs font-semibold truncate max-w-[140px] sm:max-w-[200px] transition-colors ${
                            isLight
                              ? "text-slate-900 group-hover:text-blue-600"
                              : "text-white group-hover:text-cyan-300"
                          }`}
                        >
                          {selectedPresenter?.name || "Annie - Studio Presenter"}
                        </span>
                      </div>
                      <ChevronDown
                        size={14}
                        className={`transition-colors ml-0.5 ${
                          isLight
                            ? "text-slate-500 group-hover:text-blue-600"
                            : "text-slate-400 group-hover:text-cyan-400"
                        }`}
                      />
                    </button>

                    {/* Presenter Dropdown Popover */}
                    {isPresenterPickerOpen && (
                      <div
                        ref={presenterPickerRef}
                        id="presenter-dropdown-menu"
                        data-testid="presenter-dropdown-menu"
                        className={`absolute bottom-full left-0 mb-2 w-80 rounded-2xl p-2 shadow-2xl z-50 animate-in fade-in zoom-in-95 duration-100 border ${
                          isLight
                            ? "bg-white border-slate-200 shadow-slate-200/50"
                            : "bg-[#0B111E] border-[#1E2D4A]"
                        }`}
                      >
                        <div
                          className={`px-2.5 py-1.5 border-b flex items-center justify-between mb-1 ${
                            isLight ? "border-slate-200 text-slate-900" : "border-[#18233a] text-slate-200"
                          }`}
                        >
                          <span className="text-xs font-bold">Select Presenter</span>
                          <button
                            type="button"
                            onClick={() => {
                              setIsPresenterPickerOpen(false);
                              setIsChooseAvatarModalOpen(true);
                            }}
                            className={`text-[11px] font-medium cursor-pointer ${
                              isLight ? "text-blue-600 hover:text-blue-700" : "text-cyan-400 hover:text-cyan-300"
                            }`}
                          >
                            Browse All
                          </button>
                        </div>

                        <div className="max-h-64 overflow-y-auto space-y-1 p-1 scrollbar-thin">
                          {backendAvatars.map((av) => {
                            const isSelected = selectedPresenter?.id === av.id;
                            const imgUrl =
                              av.preview_url ||
                              av.provider_metadata?.preview_url ||
                              av.provider_metadata?.image_url;
                            return (
                              <button
                                key={av.id}
                                type="button"
                                data-testid={`presenter-option-${av.id}`}
                                onClick={() => {
                                  setSelectedPresenter(av);
                                  setIsPresenterPickerOpen(false);
                                }}
                                className={`w-full flex items-center gap-2.5 p-2 rounded-xl text-left transition-all cursor-pointer border ${
                                  isSelected
                                    ? isLight
                                      ? "bg-blue-50 border-blue-200 text-blue-900 font-semibold"
                                      : "bg-cyan-500/15 border-cyan-500/40 text-white"
                                    : isLight
                                    ? "hover:bg-slate-100 text-slate-700 hover:text-slate-900 border-transparent"
                                    : "hover:bg-[#12192c] text-slate-300 hover:text-white border-transparent"
                                }`}
                              >
                                <div className="w-8 h-8 rounded-full overflow-hidden border border-slate-300 bg-slate-100 flex-shrink-0">
                                  {imgUrl ? (
                                    <img
                                      src={imgUrl}
                                      alt={av.name}
                                      className="w-full h-full object-cover object-top"
                                    />
                                  ) : (
                                    <UserIcon size={16} className="text-slate-400 m-auto mt-1.5" />
                                  )}
                                </div>
                                <div className="flex-1 min-w-0">
                                  <p
                                    className={`text-xs font-bold truncate ${
                                      isLight ? "text-slate-900" : "text-slate-100"
                                    }`}
                                  >
                                    {av.name}
                                  </p>
                                  <span className="text-[10px] text-slate-400 capitalize">
                                    {av.avatar_type || "Studio"}
                                  </span>
                                </div>
                                {isSelected && (
                                  <Check
                                    size={14}
                                    className={`flex-shrink-0 ${isLight ? "text-blue-600" : "text-cyan-400"}`}
                                  />
                                )}
                              </button>
                            );
                          })}
                        </div>

                        <div
                          className={`pt-2 border-t mt-1 ${
                            isLight ? "border-slate-200" : "border-[#18233a]"
                          }`}
                        >
                          <button
                            type="button"
                            onClick={() => {
                              setIsPresenterPickerOpen(false);
                              setIsChooseAvatarModalOpen(true);
                            }}
                            className={`w-full py-1.5 text-center text-xs font-semibold rounded-xl transition-all cursor-pointer border ${
                              isLight
                                ? "text-blue-700 bg-blue-50 hover:bg-blue-100 border-blue-200"
                                : "text-cyan-400 hover:text-cyan-300 bg-cyan-950/40 hover:bg-cyan-900/40 border-cyan-500/30"
                            }`}
                          >
                            Open Avatar Catalog...
                          </button>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Duration Selector */}
                  <div className="relative">
                    <button
                      type="button"
                      id="duration-selector-btn"
                      data-testid="duration-selector-btn"
                      onClick={() => setIsDurationPickerOpen((prev) => !prev)}
                      className={`flex items-center gap-2 px-2.5 py-1.5 rounded-xl border text-xs transition-all cursor-pointer shadow-sm group ${
                        isLight
                          ? "bg-slate-100 hover:bg-slate-200 border-slate-300 hover:border-blue-400 text-slate-800"
                          : "bg-[#0F172A] hover:bg-[#16233B] border-[#233554] hover:border-cyan-500/50 text-slate-200"
                      }`}
                      title="Choose Video Duration"
                    >
                      <Clock size={15} className={`flex-shrink-0 ${isLight ? "text-blue-600" : "text-cyan-400"}`} />
                      <div className="flex flex-col text-left">
                        <span className="text-[9px] text-slate-400 font-semibold tracking-wider uppercase leading-none">Duration</span>
                        <span
                          className={`text-xs font-semibold truncate max-w-[130px] sm:max-w-[180px] transition-colors ${
                            isLight
                              ? "text-slate-900 group-hover:text-blue-600"
                              : "text-white group-hover:text-cyan-300"
                          }`}
                          id="selected-duration-label"
                        >
                          {getDurationLabel(selectedDurationSeconds)}
                        </span>
                      </div>
                      <ChevronDown
                        size={14}
                        className={`transition-colors ml-0.5 ${
                          isLight
                            ? "text-slate-500 group-hover:text-blue-600"
                            : "text-slate-400 group-hover:text-cyan-400"
                        }`}
                      />
                    </button>

                    {/* Duration Dropdown Popover */}
                    {isDurationPickerOpen && (
                      <div
                        ref={durationPickerRef}
                        id="duration-dropdown-menu"
                        data-testid="duration-dropdown-menu"
                        className={`absolute bottom-full left-0 mb-2 w-64 rounded-2xl p-2.5 shadow-2xl z-50 animate-in fade-in zoom-in-95 duration-100 border ${
                          isLight
                            ? "bg-white border-slate-200 shadow-slate-200/50"
                            : "bg-[#0B111E] border-[#1E2D4A]"
                        }`}
                      >
                        <div
                          className={`px-2 py-1 border-b flex items-center justify-between mb-1.5 ${
                            isLight ? "border-slate-200 text-slate-900" : "border-[#18233a] text-slate-200"
                          }`}
                        >
                          <span className="text-xs font-bold">Video Duration</span>
                          <span
                            className={`text-[10px] font-mono ${
                              isLight ? "text-blue-600" : "text-cyan-400"
                            }`}
                          >
                            {formatDurationMMSS(selectedDurationSeconds)}
                          </span>
                        </div>

                        <div className="space-y-1">
                          {DURATION_PRESETS.map((preset) => {
                            if (preset.seconds === -1) {
                              const isCustomActive = isCustomMode || !DURATION_PRESETS.some((p) => p.seconds === selectedDurationSeconds && p.seconds > 0);
                              return (
                                <button
                                  key="custom"
                                  type="button"
                                  id="duration-preset-custom"
                                  data-testid="duration-preset-custom"
                                  onClick={() => {
                                    setIsCustomMode(true);
                                    if (!customDurationInput) {
                                      setCustomDurationInput(String(selectedDurationSeconds));
                                    }
                                  }}
                                  className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-xl text-left text-xs transition-all cursor-pointer border ${
                                    isCustomActive
                                      ? isLight
                                        ? "bg-blue-50 border-blue-200 text-blue-900 font-semibold"
                                        : "bg-cyan-500/15 border-cyan-500/40 text-white font-semibold"
                                      : isLight
                                      ? "hover:bg-slate-100 text-slate-700 hover:text-slate-900 border-transparent"
                                      : "hover:bg-[#12192c] text-slate-300 hover:text-white border-transparent"
                                  }`}
                                >
                                  <span>Custom Duration...</span>
                                  {isCustomActive && (
                                    <Check
                                      size={13}
                                      className={isLight ? "text-blue-600" : "text-cyan-400"}
                                    />
                                  )}
                                </button>
                              );
                            }

                            const isSelected = !isCustomMode && selectedDurationSeconds === preset.seconds;
                            return (
                              <button
                                key={preset.seconds}
                                type="button"
                                id={`duration-preset-${preset.seconds}`}
                                data-testid={`duration-preset-${preset.seconds}`}
                                onClick={() => {
                                  setIsCustomMode(false);
                                  setSelectedDurationSeconds(preset.seconds);
                                  setIsDurationPickerOpen(false);
                                }}
                                className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-xl text-left text-xs transition-all cursor-pointer border ${
                                  isSelected
                                    ? isLight
                                      ? "bg-blue-50 border-blue-200 text-blue-900 font-semibold"
                                      : "bg-cyan-500/15 border-cyan-500/40 text-white font-semibold"
                                    : isLight
                                    ? "hover:bg-slate-100 text-slate-700 hover:text-slate-900 border-transparent"
                                    : "hover:bg-[#12192c] text-slate-300 hover:text-white border-transparent"
                                }`}
                              >
                                <span>{preset.label}</span>
                                <div className="flex items-center gap-1.5">
                                  <span className="text-[10px] text-slate-400 font-mono">
                                    {formatDurationMMSS(preset.seconds)}
                                  </span>
                                  {isSelected && (
                                    <Check
                                      size={13}
                                      className={isLight ? "text-blue-600" : "text-cyan-400"}
                                    />
                                  )}
                                </div>
                              </button>
                            );
                          })}
                        </div>

                        {/* Custom Duration Input Field */}
                        {(isCustomMode || !DURATION_PRESETS.some((p) => p.seconds === selectedDurationSeconds && p.seconds > 0)) && (
                          <div
                            className={`pt-2 mt-1.5 border-t space-y-1.5 ${
                              isLight ? "border-slate-200" : "border-[#18233a]"
                            }`}
                          >
                            <label
                              className={`text-[10px] font-semibold block ${
                                isLight ? "text-slate-700" : "text-slate-300"
                              }`}
                            >
                              Enter Duration (seconds, up to 3600s):
                            </label>
                            <div className="flex items-center gap-1.5">
                              <input
                                type="number"
                                id="custom-duration-input"
                                data-testid="custom-duration-input"
                                min={5}
                                max={3600}
                                placeholder="e.g. 180"
                                value={customDurationInput}
                                onChange={(e) => {
                                  setCustomDurationInput(e.target.value);
                                  const val = parseInt(e.target.value, 10);
                                  if (!isNaN(val) && val >= 5) {
                                    setSelectedDurationSeconds(val);
                                  }
                                }}
                                className={`flex-1 rounded-lg px-2 py-1 text-xs focus:outline-none border ${
                                  isLight
                                    ? "bg-slate-50 border-slate-300 text-slate-900 placeholder-slate-400 focus:border-blue-500"
                                    : "bg-[#090d18] border-[#233554] text-white placeholder-slate-500 focus:border-cyan-500"
                                }`}
                              />
                              <button
                                type="button"
                                id="apply-custom-duration-btn"
                                data-testid="apply-custom-duration-btn"
                                onClick={() => {
                                  const val = parseInt(customDurationInput, 10);
                                  if (!isNaN(val) && val >= 5) {
                                    setSelectedDurationSeconds(val);
                                    setIsDurationPickerOpen(false);
                                  }
                                }}
                                className="bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs px-2.5 py-1 rounded-lg transition-all cursor-pointer"
                              >
                                Set
                              </button>
                            </div>
                            <p className="text-[9px] text-slate-400 leading-tight">
                              Natural AI pacing generates scripts & scenes proportional to length.
                            </p>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>

                {/* Presenter Real AI Status Badge */}
                <div
                  className={`hidden sm:flex items-center gap-1.5 text-[11px] px-2.5 py-1 rounded-xl border ${
                    isLight
                      ? "text-slate-700 bg-slate-100 border-slate-300"
                      : "text-slate-400 bg-[#0c1220] border-[#1b253e]"
                  }`}
                >
                  <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                  <span>Interactive Presenter</span>
                </div>
              </div>

              <div
                id="video-agent-prompt-composer"
                data-testid="video-agent-prompt-composer"
                className={`rounded-2xl p-2 flex items-center gap-2.5 transition-all border ${
                  isLight
                    ? "bg-white border-slate-300 focus-within:border-blue-500 shadow-sm"
                    : "bg-[#0B111E] border-[#1E2D4A] focus-within:border-cyan-500/60 shadow-xl"
                }`}
              >
                {/* + Attachment Button */}
                <button
                  type="button"
                  onClick={() => setIsAttachModalOpen(true)}
                  className={`p-2 rounded-xl transition-colors cursor-pointer flex-shrink-0 ${
                    isLight
                      ? "text-slate-500 hover:text-slate-900 hover:bg-slate-100"
                      : "text-slate-400 hover:text-white hover:bg-[#162238]"
                  }`}
                  title="Attach Media or File"
                >
                  <Plus size={16} />
                </button>

                {/* Prompt Textarea */}
                <textarea
                  id="video-agent-composer-input"
                  data-testid="video-agent-composer-input"
                  ref={composerInputRef}
                  value={composerText}
                  onChange={(e) => setComposerText(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Enter your prompt instructions..."
                  rows={1}
                  disabled={isGenerating}
                  className={`flex-1 bg-transparent text-xs sm:text-sm focus:outline-none resize-none py-1.5 max-h-24 scrollbar-none ${
                    isLight
                      ? "text-slate-900 placeholder-slate-400"
                      : "text-slate-100 placeholder-slate-500"
                  }`}
                />

                {/* Send / Generate Button */}
                <button
                  type="button"
                  id="video-agent-generate-btn"
                  data-testid="video-agent-generate-btn"
                  onClick={handleSendPrompt}
                  disabled={!composerText.trim() || isGenerating}
                  className="w-9 h-9 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white flex items-center justify-center shadow-md shadow-blue-500/25 active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed transition-all flex-shrink-0 cursor-pointer"
                  title="Generate / Send Prompt"
                >
                  {isGenerating ? (
                    <RefreshCw size={15} className="animate-spin" />
                  ) : (
                    <ArrowUp size={16} strokeWidth={2.5} />
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ============================================================ */}
      {/* 4. MODALS: ATTACH ASSET & PREVIEW & SHARE */}
      {/* ============================================================ */}
      <AttachAssetModal
        isOpen={isAttachModalOpen}
        onClose={() => setIsAttachModalOpen(false)}
        onAttachFile={(fileName) => {
          setAttachedFiles((prev) => [...prev, fileName]);
        }}
      />

      {/* Timeline Scene Preview Modal */}
      {isPreviewOpen && selectedArtifact && selectedArtifact.videoUrl && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4 animate-in fade-in">
          <div className="w-full max-w-2xl bg-[#0c1220] border border-[#233152] rounded-3xl p-6 shadow-2xl relative">
            <div className="flex items-center justify-between pb-3 border-b border-[#1c2742]">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <Film size={16} className="text-cyan-400" />
                <span>Timeline Preview — {selectedArtifact.title}</span>
              </h3>
              <button
                type="button"
                onClick={() => setIsPreviewOpen(false)}
                className="text-slate-400 hover:text-white p-1 rounded-lg"
              >
                <X size={16} />
              </button>
            </div>

            <div className="mt-4 space-y-4">
              <div className="relative aspect-video rounded-xl bg-[#080c16] border border-[#1f2b45] overflow-hidden flex items-center justify-center">
                {selectedArtifact.videoUrl ? (
                  <video
                    src={selectedArtifact.videoUrl}
                    controls
                    autoPlay
                    playsInline
                    poster={selectedArtifact.thumbnailUrl || AVATAR_OPTIONS[0].image}
                    className="w-full h-full object-contain bg-black"
                  />
                ) : (
                  <>
                    <img
                      src={selectedArtifact.thumbnailUrl || AVATAR_OPTIONS[0].image}
                      alt="Avatar"
                      className="absolute inset-0 w-full h-full object-cover object-top opacity-50"
                    />
                    <div className="relative z-10 text-center px-6">
                      <span className="text-[11px] text-cyan-400 font-bold bg-cyan-950/80 px-2.5 py-1 rounded-md border border-cyan-500/30">
                        Scene 0{activePreviewSceneIdx + 1} of {selectedArtifact.scenes.length}
                      </span>
                      <p className="text-sm text-white font-medium mt-3 italic">
                        &ldquo;{selectedArtifact.scenes[activePreviewSceneIdx]?.script}&rdquo;
                      </p>
                    </div>
                  </>
                )}
              </div>

              {/* Scene Navigation Carousel */}
              <div className="flex items-center justify-between">
                <button
                  type="button"
                  disabled={activePreviewSceneIdx === 0}
                  onClick={() => setActivePreviewSceneIdx((p) => Math.max(0, p - 1))}
                  className="px-3 py-1.5 rounded-xl bg-[#12192c] text-xs font-semibold text-slate-300 disabled:opacity-40"
                >
                  ← Previous Scene
                </button>
                <span className="text-xs text-slate-400 font-medium">
                  {selectedArtifact.scenes[activePreviewSceneIdx]?.duration}s
                </span>
                <button
                  type="button"
                  disabled={activePreviewSceneIdx === selectedArtifact.scenes.length - 1}
                  onClick={() =>
                    setActivePreviewSceneIdx((p) =>
                      Math.min(selectedArtifact.scenes.length - 1, p + 1)
                    )
                  }
                  className="px-3 py-1.5 rounded-xl bg-[#12192c] text-xs font-semibold text-slate-300 disabled:opacity-40"
                >
                  Next Scene →
                </button>
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-[#1c2742]">
                <button
                  type="button"
                  onClick={() => {
                    setIsPreviewOpen(false);
                    onOpenStudio?.(selectedArtifact.id);
                  }}
                  className="bg-gradient-to-r from-blue-600 to-cyan-600 text-white font-bold text-xs px-4 py-2 rounded-xl flex items-center gap-1.5 cursor-pointer"
                >
                  <Clapperboard size={13} /> Edit in Studio
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Share Modal */}
      {isShareModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4 animate-in fade-in">
          <div className="w-full max-w-md bg-[#0c1220] border border-[#233152] rounded-3xl p-6 shadow-2xl relative">
            <div className="flex items-center justify-between pb-3 border-b border-[#1c2742]">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <Share2 size={16} className="text-blue-400" />
                <span>Share Video Agent Project</span>
              </h3>
              <button
                type="button"
                onClick={() => setIsShareModalOpen(false)}
                className="text-slate-400 hover:text-white p-1 rounded-lg"
              >
                <X size={16} />
              </button>
            </div>
            <p className="text-xs text-slate-300 mt-4">
              Collaborate with workspace team members on this video project.
            </p>
            <div className="mt-4 flex items-center gap-2">
              <input
                readOnly
                value={typeof window !== "undefined" ? window.location.href : ""}
                className="flex-1 bg-[#070a12] border border-[#1b253e] rounded-xl px-3 py-2 text-xs text-slate-300 select-all"
              />
              <button
                type="button"
                onClick={() => {
                  if (typeof navigator !== "undefined") {
                    navigator.clipboard.writeText(window.location.href);
                    alert("Project link copied to clipboard!");
                  }
                  setIsShareModalOpen(false);
                }}
                className="bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold px-3 py-2 rounded-xl"
              >
                Copy
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Choose Avatar Modal */}
      <ChooseAvatarModal
        isOpen={isChooseAvatarModalOpen}
        onClose={() => setIsChooseAvatarModalOpen(false)}
        selectedAvatarId={selectedPresenter?.id}
        onSelectAvatar={(avatar, look) => {
          const matched =
            backendAvatars.find((a) => a.id === avatar.id) || avatar;
          setSelectedPresenter({
            ...matched,
            id: avatar.id,
            name: avatar.name || matched.name,
            preview_url: avatar.image || matched.preview_url,
            image: avatar.image || matched.preview_url,
            selectedLook: look,
          });
          setIsChooseAvatarModalOpen(false);
        }}
      />
    </div>
  );
}
