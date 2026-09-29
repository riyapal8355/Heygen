"use client";

import React, { useState, useEffect, useCallback, useRef, useMemo } from "react";
import {
  Play,
  Pause,
  RotateCcw,
  RotateCw,
  CheckCircle2,
  Plus,
  Clapperboard,
  User,
  Mic,
  FileText,
  Image as ImageIcon,
  Type,
  Component,
  Music,
  Shuffle,
  Subtitles,
  Palette,
  Crown,
  Volume2,
  Maximize2,
  Minimize2,
  Lock,
  Eye,
  Scissors,
  ZoomIn,
  ZoomOut,
  Trash2,
  Pencil,
  Copy,
  Sliders,
  Sparkles,
  ArrowLeft,
  ChevronDown,
  ChevronUp,
  Layers,
  AlertTriangle,
  Download,
  Loader2,
  Search,
  Check,
  X,
  RefreshCw,
  Repeat,
  Star,
  Heart,
  Flame,
  ThumbsUp,
  Tag,
  Rocket,
  Trophy,
} from "lucide-react";
import UserMenuDropdown from "../dashboard/UserMenuDropdown";
import { useTheme } from "@/context/ThemeContext";
import { api, ApiError } from "@/lib/api";
import MusicPanel, { AudioTrackItem } from "./MusicPanel";
import MusicTimelineTrack from "./MusicTimelineTrack";
import MediaPanel from "./MediaPanel";
import CaptionsPanel, { CaptionSettingsState, SubtitleCue } from "./CaptionsPanel";
import CaptionTimelineTrack from "./CaptionTimelineTrack";
import TextPanel from "./TextPanel";
import TextTimelineTrack from "./TextTimelineTrack";
import MediaTimelineTrack from "./MediaTimelineTrack";
import ElementsPanel from "./ElementsPanel";
import ElementsTimelineTrack from "./ElementsTimelineTrack";
import AttachAssetModal from "../create/AttachAssetModal";
import CanvasTransformGizmo from "./CanvasTransformGizmo";
import {
  canSplitClip,
  splitClip,
  MIN_CLIP_DURATION,
  MIN_TIMELINE_ZOOM,
  MAX_TIMELINE_ZOOM,
  DEFAULT_TIMELINE_ZOOM,
  calculateSceneResizeTiming,
  clampLayersToSceneDuration,
} from "@/lib/timelineUtils";
import {
  SnapTargetLayer,
  AlignmentGuide,
  getLayerEffectiveBounds,
} from "@/lib/studioCanvasSnapping";
import {
  isInputOrEditableTarget,
  getSelectedVisualLayer,
  calculateKeyboardNudge,
  canDeleteLayerViaKeyboard,
  createLayerDuplicatePayload,
  SerializedStudioLayer,
} from "@/lib/studioKeyboardUtils";
import {
  createHistory,
  pushHistory,
  undo,
  redo,
  canUndo,
  canRedo,
  HistoryState,
  HistorySelectionState,
} from "@/lib/studioHistory";
import {
  bringLayerForward,
  sendLayerBackward,
  bringLayerToFront,
  sendLayerToBack,
  moveLayerToIndex,
  normalizeLayerZIndices,
  getOrderedVisualLayers,
  duplicateLayerWithZIndex,
  deleteLayerWithZIndex,
  VisualLayer,
} from "@/lib/studioLayerOrdering";
import {
  SelectedLayerIdentity,
  selectSingleLayer,
  toggleLayerSelection,
  addLayersToSelection,
  removeLayersFromSelection,
  isLayerSelected,
  calculateGroupBounds,
  getLayersIntersectingMarquee,
  calculateGroupMove,
  calculateGroupAlignment,
  calculateGroupDistribution,
  groupDuplicateLayers,
  groupDeleteLayers,
  groupSetLock,
  groupSetVisibility,
  groupMoveZOrder,
  calculateGroupTimelineMove,
  batchSetOpacity,
  batchSetVisibility,
  batchSetLock,
  batchApplyTransformDelta,
  TransformBatchDelta,
} from "@/lib/studioMultiSelection";
import UnifiedLayersPanel from "./UnifiedLayersPanel";
import MultiSelectionInspector from "./MultiSelectionInspector";

export interface StudioScene {
  id: string;
  sequence: number;
  duration: number;
  title?: string;
  background?: { type: string; value?: string; asset_id?: string | null };
  transition?: { type: string; duration: number } | null;
  avatar?: {
    avatar_id: string;
    look_id?: string | null;
    view_mode?: string;
    video_asset_id?: string | null;
    position?: { x: number; y: number; scale: number; rotation: number };
    start_time?: number;
    end_time?: number;
  } | null;
  speech?: {
    voice_id: string;
    script: string;
    audio_asset_id?: string | null;
    speed?: number;
    pitch?: number;
    start_time?: number;
    end_time?: number;
  } | null;
  layers?: any[];
  subtitles?: any[];
}

export default function VidoAIStudio({
  projectId,
  workspaceId,
  onBackToDashboard,
}: {
  projectId?: string;
  workspaceId?: string;
  onBackToDashboard?: () => void;
}) {
  // Navigation & Tool State
  const [activeTab, setActiveTab] = useState<"scene" | "avatar" | "voice" | "music" | "media" | "captions" | "text" | "elements" | "layers">("scene");
  const [activeLeftTool, setActiveLeftTool] = useState("scenes");
  const [selectedTextLayerId, setSelectedTextLayerId] = useState<string | null>(null);
  const [selectedMediaLayerId, setSelectedMediaLayerId] = useState<string | null>(null);
  const [selectedElementLayerId, setSelectedElementLayerId] = useState<string | null>(null);
  // Canonical Multi-Layer Selection State (Phase 44)
  const [selectedLayerIds, setSelectedLayerIds] = useState<string[]>([]);
  // Marquee rectangular drag selection state
  const [marqueeState, setMarqueeState] = useState<{
    active: boolean;
    startX: number;
    startY: number;
    currentX: number;
    currentY: number;
    isAdditive: boolean;
  } | null>(null);
  // Group canvas drag session reference
  const groupDragRef = useRef<{
    active: boolean;
    startX: number;
    startY: number;
    initialLayers: VisualLayer[];
  } | null>(null);
  const [assetUrls, setAssetUrls] = useState<Record<string, string>>({});
  const mediaVideoRefs = useRef<Record<string, HTMLVideoElement | null>>({});
  const canvasViewportRef = useRef<HTMLDivElement | null>(null);
  const [aspectRatio, setAspectRatio] = useState("16:9");
  const [activeSceneIndex, setActiveSceneIndex] = useState(0);
  const [canvasDimensions, setCanvasDimensions] = useState({ width: 768, height: 432 });

  // Resizable Studio Sections State
  const [leftSidebarWidth, setLeftSidebarWidth] = useState<number>(() => {
    if (typeof window !== "undefined") {
      try {
        const saved = sessionStorage.getItem("studio_left_sidebar_width");
        if (saved) {
          const val = parseInt(saved, 10);
          if (!isNaN(val) && val >= 140 && val <= 420) return val;
        }
      } catch {}
    }
    return 176; // Default w-44 (176px)
  });

  const [rightInspectorWidth, setRightInspectorWidth] = useState<number>(() => {
    if (typeof window !== "undefined") {
      try {
        const saved = sessionStorage.getItem("studio_right_inspector_width");
        if (saved) {
          const val = parseInt(saved, 10);
          if (!isNaN(val) && val >= 240 && val <= 500) return val;
        }
      } catch {}
    }
    return 320; // Default w-80 (320px)
  });

  const [timelineHeight, setTimelineHeight] = useState<number>(() => {
    if (typeof window !== "undefined") {
      try {
        const saved = sessionStorage.getItem("studio_timeline_height");
        if (saved) {
          const val = parseInt(saved, 10);
          if (!isNaN(val) && val >= 160 && val <= 550) return val;
        }
      } catch {}
    }
    return 256; // Default h-64 (256px)
  });

  // Resize handler for Left Sidebar (horizontal)
  const handleLeftResizeStart = useCallback((e: React.PointerEvent) => {
    e.preventDefault();
    const startX = e.clientX;
    const startWidth = leftSidebarWidth;

    const onPointerMove = (moveEvent: PointerEvent) => {
      const delta = moveEvent.clientX - startX;
      const newWidth = Math.min(420, Math.max(140, startWidth + delta));
      setLeftSidebarWidth(newWidth);
      if (typeof window !== "undefined") {
        try {
          sessionStorage.setItem("studio_left_sidebar_width", String(newWidth));
        } catch {}
      }
    };

    const onPointerUp = () => {
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerup", onPointerUp);
      document.body.style.userSelect = "";
      document.body.style.cursor = "";
    };

    document.body.style.userSelect = "none";
    document.body.style.cursor = "col-resize";
    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", onPointerUp);
  }, [leftSidebarWidth]);

  // Resize handler for Right Inspector (horizontal)
  const handleRightResizeStart = useCallback((e: React.PointerEvent) => {
    e.preventDefault();
    const startX = e.clientX;
    const startWidth = rightInspectorWidth;

    const onPointerMove = (moveEvent: PointerEvent) => {
      const delta = startX - moveEvent.clientX;
      const newWidth = Math.min(500, Math.max(240, startWidth + delta));
      setRightInspectorWidth(newWidth);
      if (typeof window !== "undefined") {
        try {
          sessionStorage.setItem("studio_right_inspector_width", String(newWidth));
        } catch {}
      }
    };

    const onPointerUp = () => {
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerup", onPointerUp);
      document.body.style.userSelect = "";
      document.body.style.cursor = "";
    };

    document.body.style.userSelect = "none";
    document.body.style.cursor = "col-resize";
    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", onPointerUp);
  }, [rightInspectorWidth]);

  // Resize handler for Timeline (vertical)
  const handleTimelineResizeStart = useCallback((e: React.PointerEvent) => {
    e.preventDefault();
    const startY = e.clientY;
    const startHeight = timelineHeight;

    const onPointerMove = (moveEvent: PointerEvent) => {
      const delta = startY - moveEvent.clientY;
      const newHeight = Math.min(550, Math.max(160, startHeight + delta));
      setTimelineHeight(newHeight);
      if (typeof window !== "undefined") {
        try {
          sessionStorage.setItem("studio_timeline_height", String(newHeight));
        } catch {}
      }
    };

    const onPointerUp = () => {
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerup", onPointerUp);
      document.body.style.userSelect = "";
      document.body.style.cursor = "";
    };

    document.body.style.userSelect = "none";
    document.body.style.cursor = "row-resize";
    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", onPointerUp);
  }, [timelineHeight]);

  useEffect(() => {
    if (!canvasViewportRef.current) return;
    const updateSize = () => {
      if (canvasViewportRef.current) {
        const rect = canvasViewportRef.current.getBoundingClientRect();
        if (rect.width > 0 && rect.height > 0) {
          setCanvasDimensions({ width: rect.width, height: rect.height });
        }
      }
    };
    updateSize();
    const ro = new ResizeObserver(updateSize);
    ro.observe(canvasViewportRef.current);
    return () => ro.disconnect();
  }, []);

  const studioRootRef = useRef<HTMLDivElement | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const { theme } = useTheme();
  const isLight = theme === "light";

  useEffect(() => {
    const handleFullscreenChange = () => {
      const currentFs = document.fullscreenElement || (document as any).webkitFullscreenElement;
      const isCurrent = Boolean(
        currentFs &&
        (currentFs === studioRootRef.current ||
         studioRootRef.current?.contains(currentFs))
      );
      setIsFullscreen(isCurrent);
      setTimeout(() => {
        if (canvasViewportRef.current) {
          const rect = canvasViewportRef.current.getBoundingClientRect();
          if (rect.width > 0 && rect.height > 0) {
            setCanvasDimensions({ width: rect.width, height: rect.height });
          }
        }
      }, 50);
    };

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && (document.fullscreenElement || (document as any).webkitFullscreenElement)) {
        if (document.exitFullscreen) {
          document.exitFullscreen().catch(() => {});
        } else if ((document as any).webkitExitFullscreen) {
          (document as any).webkitExitFullscreen();
        }
      }
    };

    document.addEventListener("fullscreenchange", handleFullscreenChange);
    document.addEventListener("webkitfullscreenchange", handleFullscreenChange);
    window.addEventListener("keydown", handleKeyDown);

    return () => {
      document.removeEventListener("fullscreenchange", handleFullscreenChange);
      document.removeEventListener("webkitfullscreenchange", handleFullscreenChange);
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, []);

  const toggleStudioFullscreen = async () => {
    try {
      if (!document.fullscreenElement) {
        if (studioRootRef.current?.requestFullscreen) {
          await studioRootRef.current.requestFullscreen();
        } else if ((studioRootRef.current as any)?.webkitRequestFullscreen) {
          await (studioRootRef.current as any).webkitRequestFullscreen();
        }
      } else {
        if (document.exitFullscreen) {
          await document.exitFullscreen();
        } else if ((document as any).webkitExitFullscreen) {
          await (document as any).webkitExitFullscreen();
        }
      }
    } catch (err) {
      console.error("Fullscreen toggle failed:", err);
    }
  };

  // Captions & Subtitles State
  const [captionSettings, setCaptionSettings] = useState<CaptionSettingsState>({
    enabled: true,
    style: {
      font_family: "Arial",
      font_size: 32,
      font_weight: "bold",
      color: "#FFFFFF",
      background_color: "#000000",
      background_opacity: 0.6,
      position: "bottom",
      alignment: "center",
    },
  });
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [selectedCueId, setSelectedCueId] = useState<string | number | null>(null);

  // Audio Tracks (Multi-track array architecture)
  const [audioTracks, setAudioTracks] = useState<AudioTrackItem[]>([]);
  const [activeAudioTrackId, setActiveAudioTrackId] = useState<string | null>(null);

  // Modal State for AttachAssetModal
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [uploadModalTarget, setUploadModalTarget] = useState<"music" | "media">("media");

  // Document & Concurrency State
  const [projectTitle, setProjectTitle] = useState("Untitled Project");
  const [revision, setRevision] = useState(1);
  const revisionRef = useRef<number>(1);
  const updateRevision = useCallback((newRev: number) => {
    revisionRef.current = newRev;
    setRevision(newRev);
  }, []);
  const saveQueueRef = useRef<Promise<any>>(Promise.resolve());
  const [saveStatus, setSaveStatus] = useState<"saved" | "saving" | "unsaved" | "conflict">("saved");
  const [conflictMessage, setConflictMessage] = useState<string | null>(null);
  const [currentDocument, setCurrentDocument] = useState<any>(null);
  const [isLoadingProject, setIsLoadingProject] = useState(false);

  // Real Scenes State
  const [scenes, setScenes] = useState<StudioScene[]>([]);
  const scenesRef = useRef<StudioScene[]>([]);
  useEffect(() => {
    scenesRef.current = scenes;
  }, [scenes]);

  // Helper to sync single selection states with selectedLayerIds
  const syncSingleSelectionFromIds = useCallback((ids: string[], currentScenes?: StudioScene[]) => {
    if (ids.length === 1) {
      const activeSc = (currentScenes || scenesRef.current || scenes)[activeSceneIndex];
      const target = (activeSc?.layers || []).find((l: any) => l.id === ids[0]);
      if (target) {
        if (target.type === "image" || target.type === "video" || target.type === "media") {
          setSelectedMediaLayerId(ids[0]);
          setSelectedTextLayerId(null);
          setSelectedElementLayerId(null);
        } else if (target.type === "text") {
          setSelectedTextLayerId(ids[0]);
          setSelectedMediaLayerId(null);
          setSelectedElementLayerId(null);
        } else {
          setSelectedElementLayerId(ids[0]);
          setSelectedMediaLayerId(null);
          setSelectedTextLayerId(null);
        }
        return;
      }
    }
    // If 0 or >1 layers are selected, clear single-type selections
    setSelectedMediaLayerId(null);
    setSelectedTextLayerId(null);
    setSelectedElementLayerId(null);
  }, [activeSceneIndex, scenes]);

  // Single & additive selection helpers across all visual layers
  const selectMediaLayer = useCallback((id: string | null, isAdditive?: boolean) => {
    if (!id) {
      if (!isAdditive) {
        setSelectedLayerIds([]);
        setSelectedMediaLayerId(null);
      }
      return;
    }
    if (isAdditive) {
      setSelectedLayerIds((prev) => {
        const next = prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id];
        syncSingleSelectionFromIds(next);
        return next;
      });
    } else {
      setSelectedLayerIds([id]);
      setSelectedMediaLayerId(id);
      setSelectedTextLayerId(null);
      setSelectedElementLayerId(null);
    }
  }, [syncSingleSelectionFromIds]);

  const selectTextLayer = useCallback((id: string | null, isAdditive?: boolean) => {
    if (!id) {
      if (!isAdditive) {
        setSelectedLayerIds([]);
        setSelectedTextLayerId(null);
      }
      return;
    }
    if (isAdditive) {
      setSelectedLayerIds((prev) => {
        const next = prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id];
        syncSingleSelectionFromIds(next);
        return next;
      });
    } else {
      setSelectedLayerIds([id]);
      setSelectedTextLayerId(id);
      setSelectedMediaLayerId(null);
      setSelectedElementLayerId(null);
    }
  }, [syncSingleSelectionFromIds]);

  const selectElementLayer = useCallback((id: string | null, isAdditive?: boolean) => {
    if (!id) {
      if (!isAdditive) {
        setSelectedLayerIds([]);
        setSelectedElementLayerId(null);
      }
      return;
    }
    if (isAdditive) {
      setSelectedLayerIds((prev) => {
        const next = prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id];
        syncSingleSelectionFromIds(next);
        return next;
      });
    } else {
      setSelectedLayerIds([id]);
      setSelectedElementLayerId(id);
      setSelectedMediaLayerId(null);
      setSelectedTextLayerId(null);
    }
  }, [syncSingleSelectionFromIds]);

  const clearVisualSelection = useCallback(() => {
    setSelectedLayerIds([]);
    setSelectedMediaLayerId(null);
    setSelectedTextLayerId(null);
    setSelectedElementLayerId(null);
  }, []);

  const selectAllLayers = useCallback(() => {
    const currentSc = scenes[activeSceneIndex];
    if (!currentSc?.layers) return;
    const allIds = currentSc.layers
      .filter((l: any) =>
        ["image", "video", "media", "text", "shape", "sticker", "element"].includes(l.type)
      )
      .map((l: any) => l.id);
    setSelectedLayerIds(allIds);
    syncSingleSelectionFromIds(allIds);
  }, [scenes, activeSceneIndex, syncSingleSelectionFromIds]);

  // --------------------------------------------------------------------------
  // CLIENT-SIDE UNDO/REDO HISTORY (PHASE 40)
  // --------------------------------------------------------------------------
  const historyRef = useRef<HistoryState | null>(null);
  const [canUndoState, setCanUndoState] = useState(false);
  const [canRedoState, setCanRedoState] = useState(false);
  const isRestoringHistoryRef = useRef(false);

  const audioTracksRef = useRef<AudioTrackItem[]>([]);
  useEffect(() => {
    audioTracksRef.current = audioTracks;
  }, [audioTracks]);

  // Transient Magnetic Alignment Guides (Phase 42A)
  const [activeSnapGuides, setActiveSnapGuides] = useState<AlignmentGuide[]>([]);

  // Catalogs
  const [voices, setVoices] = useState<any[]>([]);
  const [avatars, setAvatars] = useState<any[]>([]);
  const [voiceSearch, setVoiceSearch] = useState("");
  const [voiceLangFilter, setVoiceLangFilter] = useState("all");
  const [avatarSearch, setAvatarSearch] = useState("");

  // Media Playback State
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackTime, setPlaybackTime] = useState(0.0);
  const [mediaUrls, setMediaUrls] = useState<Record<string, string>>({});
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const previewAudioRef = useRef<HTMLAudioElement | null>(null);
  const [previewingVoiceId, setPreviewingVoiceId] = useState<string | null>(null);

  // Timeline Zoom & Pan (Phase 43)
  const [timelineZoom, setTimelineZoom] = useState<number>(DEFAULT_TIMELINE_ZOOM);
  const timelineScrollContainerRef = useRef<HTMLDivElement | null>(null);

  // Notifications & User Feedback
  const [notification, setNotification] = useState<{
    type: "success" | "error" | "info";
    message: string;
  } | null>(null);

  // Async Jobs State
  const [speechJobState, setSpeechJobState] = useState<{
    isSynthesizing: boolean;
    progressPct: number;
    stage?: string;
    jobId?: string;
  }>({ isSynthesizing: false, progressPct: 0 });

  const [avatarJobState, setAvatarJobState] = useState<{
    isGenerating: boolean;
    progressPct: number;
    stage?: string;
    jobId?: string;
  }>({ isGenerating: false, progressPct: 0 });

  const [renderState, setRenderState] = useState<{
    isRendering: boolean;
    progressPct: number;
    stage?: string;
    downloadUrl?: string;
    jobId?: string;
    error?: string;
  }>({ isRendering: false, progressPct: 0 });

  // Compute Active Scene Safely
  const activeScene = useMemo(() => {
    if (scenes.length === 0) return null;
    return scenes[Math.min(activeSceneIndex, scenes.length - 1)] || scenes[0];
  }, [scenes, activeSceneIndex]);

  // Compute Total Duration
  const totalDuration = useMemo(() => {
    if (scenes.length === 0) return 5.0;
    return scenes.reduce((acc, s) => acc + (typeof s.duration === "number" ? s.duration : 5.0), 0.0);
  }, [scenes]);

  // Compute Active Scene Start Offset in Total Timeline
  const activeSceneOffset = useMemo(() => {
    return scenes.slice(0, activeSceneIndex).reduce((acc, s) => acc + (typeof s.duration === "number" ? s.duration : 5.0), 0.0);
  }, [scenes, activeSceneIndex]);

  // Compute Active Caption Cue at current playback time
  const activeCaptionCue = useMemo(() => {
    if (!captionSettings.enabled || !activeScene?.subtitles) return null;
    return activeScene.subtitles.find(
      (cue: any) =>
        cue.enabled !== false &&
        cue.text?.trim() &&
        playbackTime >= (cue.start ?? 0) &&
        playbackTime <= (cue.end ?? 0)
    );
  }, [captionSettings.enabled, activeScene?.subtitles, playbackTime]);

  // Compute Active Text Layers at current playback time
  const activeTextLayers = useMemo(() => {
    if (!activeScene?.layers) return [];
    return activeScene.layers.filter(
      (l: any) =>
        l.type === "text" &&
        l.enabled !== false &&
        (l.content?.text || l.name) &&
        playbackTime >= (l.start_time ?? 0) &&
        playbackTime < (l.end_time ?? (activeScene.duration || 5.0))
    );
  }, [activeScene?.layers, activeScene?.duration, playbackTime]);

  // Compute Active Visual Media Layers (Images & Videos) at current playback time
  const activeMediaLayers = useMemo(() => {
    if (!activeScene?.layers) return [];
    return activeScene.layers.filter(
      (l: any) =>
        (l.type === "image" || l.type === "video" || l.type === "media") &&
        l.enabled !== false &&
        playbackTime >= (l.start_time ?? 0) &&
        playbackTime < (l.end_time ?? (activeScene.duration || 5.0))
    );
  }, [activeScene?.layers, activeScene?.duration, playbackTime]);

  // Compute Active Elements, Shapes, and Stickers Layers at current playback time
  const activeElementLayers = useMemo(() => {
    if (!activeScene?.layers) return [];
    return activeScene.layers.filter(
      (l: any) =>
        (l.type === "shape" || l.type === "sticker" || l.type === "element") &&
        l.enabled !== false &&
        playbackTime >= (l.start_time ?? 0) &&
        playbackTime < (l.end_time ?? (activeScene.duration || 5.0))
    );
  }, [activeScene?.layers, activeScene?.duration, playbackTime]);

  // Compute Active Visual Layers at current playback time in canonical stacking order (Phase 42B)
  const activeVisualLayers = useMemo(() => {
    if (!activeScene?.layers) return [];
    const active = activeScene.layers.filter(
      (l: any) =>
        ["image", "video", "media", "text", "shape", "sticker", "element"].includes(l.type) &&
        l.enabled !== false &&
        playbackTime >= (l.start_time ?? 0) &&
        playbackTime < (l.end_time ?? (activeScene.duration || 5.0))
    );
    return getOrderedVisualLayers(active);
  }, [activeScene?.layers, activeScene?.duration, playbackTime]);

  // Synchronize layer video elements with studio playback
  useEffect(() => {
    activeMediaLayers.forEach((layer: any) => {
      const isVideo = layer.type === "video" || layer.content?.media_type === "video";
      if (!isVideo) return;
      const el = mediaVideoRefs.current[layer.id];
      if (!el) return;
      const targetTime = Math.max(0, playbackTime - (layer.start_time || 0));
      if (Math.abs(el.currentTime - targetTime) > 0.15) {
        el.currentTime = targetTime;
      }
      if (isPlaying && el.paused) {
        el.play().catch(() => {});
      } else if (!isPlaying && !el.paused) {
        el.pause();
      }
    });
  }, [activeMediaLayers, playbackTime, isPlaying]);

  // Pre-load download URLs for media layers
  useEffect(() => {
    if (!workspaceId || !activeScene?.layers) return;
    const mediaLayers = activeScene.layers.filter(
      (l: any) => l.type === "image" || l.type === "video" || l.type === "media"
    );
    mediaLayers.forEach((l: any) => {
      const assetId = l.content?.asset_id || l.asset_id;
      if (assetId && !assetUrls[assetId]) {
        api.assets
          .getDownloadUrl(workspaceId, assetId)
          .then((res) => {
            if (res?.download_url) {
              setAssetUrls((prev) => ({ ...prev, [assetId]: res.download_url }));
            }
          })
          .catch(() => {});
      }
    });
  }, [workspaceId, activeScene?.layers, assetUrls]);

  // Dismiss notification helper
  const showNotification = (type: "success" | "error" | "info", message: string) => {
    setNotification({ type, message });
    setTimeout(() => {
      setNotification((curr) => (curr?.message === message ? null : curr));
    }, 6000);
  };

  // --------------------------------------------------------------------------
  // 1. LOAD PROJECT, VOICES & AVATARS
  // --------------------------------------------------------------------------
  const loadCatalogs = useCallback(async () => {
    if (!workspaceId) return;
    try {
      const [vList, aList] = await Promise.all([
        api.creative.listVoices({}, workspaceId).catch(() => []),
        api.creative.listAvatars({}, workspaceId).catch(() => []),
      ]);
      if (Array.isArray(vList)) setVoices(vList);
      if (Array.isArray(aList)) setAvatars(aList);
    } catch {
      // Non-fatal catalog loading
    }
  }, [workspaceId]);

  const loadProject = useCallback(async () => {
    if (!workspaceId || !projectId) return;
    setIsLoadingProject(true);
    try {
      const proj = await api.projects.get(workspaceId, projectId);
      setProjectTitle(proj.title || "Untitled Video");
      setAspectRatio(proj.aspect_ratio || "16:9");
      updateRevision(proj.revision || 1);

      let docScenes: StudioScene[] = [];
      let docAudioTracks: AudioTrackItem[] = [];

      if (proj.current_version_id) {
        const ver = await api.projects.getVersion(workspaceId, projectId, proj.current_version_id);
        if (ver?.document) {
          setCurrentDocument(ver.document);
          if (ver.document.settings) {
            if (ver.document.settings.title) setProjectTitle(ver.document.settings.title);
            if (ver.document.settings.aspect_ratio) setAspectRatio(ver.document.settings.aspect_ratio);
          }
          if (ver.document.metadata?.title) {
            setProjectTitle(ver.document.metadata.title);
          }
          if (Array.isArray(ver.document.scenes) && ver.document.scenes.length > 0) {
            docScenes = ver.document.scenes.map((s: any, idx: number) => ({
              id: String(s.id || `scene_${idx + 1}`),
              sequence: s.sequence || idx + 1,
              duration: typeof s.duration === "number" ? s.duration : 5.0,
              title: s.title || `Scene ${String(idx + 1).padStart(2, "0")}`,
              background: s.background || { type: "color", value: "#0F172A" },
              transition: s.transition !== undefined ? s.transition : { type: "fade", duration: 0.5 },
              avatar: s.avatar || null,
              speech: s.speech || null,
              layers: Array.isArray(s.layers) ? normalizeLayerZIndices(s.layers) : [],
              subtitles: Array.isArray(s.subtitles) ? s.subtitles : [],
            }));
          }

          if (Array.isArray(ver.document.audio_tracks)) {
            docAudioTracks = ver.document.audio_tracks.map((t: any, idx: number) => ({
              id: String(t.id || `track_${idx + 1}`),
              asset_id: t.asset_id || null,
              name: t.name || `Audio Track ${idx + 1}`,
              volume: typeof t.volume === "number" ? t.volume : 0.3,
              start_time: typeof t.start_time === "number" ? t.start_time : 0.0,
              duration: typeof t.duration === "number" ? t.duration : null,
              loop: Boolean(t.loop),
              muted: Boolean(t.muted),
            }));
            setAudioTracks(docAudioTracks);
            if (docAudioTracks.length > 0) {
              setActiveAudioTrackId((prev) => prev || docAudioTracks[0].id);
            }

            // Load caption settings
            if (ver.document?.settings?.captions) {
              setCaptionSettings({
                enabled: ver.document.settings.captions.enabled !== false,
                style: {
                  font_family: ver.document.settings.captions.style?.font_family || "Arial",
                  font_size: ver.document.settings.captions.style?.font_size || 32,
                  font_weight: ver.document.settings.captions.style?.font_weight || "bold",
                  color: ver.document.settings.captions.style?.color || "#FFFFFF",
                  background_color: ver.document.settings.captions.style?.background_color || "#000000",
                  background_opacity: ver.document.settings.captions.style?.background_opacity ?? 0.6,
                  position: ver.document.settings.captions.style?.position || "bottom",
                  alignment: ver.document.settings.captions.style?.alignment || "center",
                },
              });
            }
          } else {
            setAudioTracks([]);
          }
        }
        if (ver.revision) updateRevision(ver.revision);
      }

      // Default fallback scene if project has zero scenes
      if (docScenes.length === 0) {
        docScenes = [
          {
            id: "scene-1",
            sequence: 1,
            duration: 5.0,
            title: "Scene 01",
            background: { type: "color", value: "#0F172A" },
            transition: { type: "fade", duration: 0.5 },
            avatar: {
              avatar_id: "default-presenter",
              view_mode: "half_body",
              position: { x: 0.5, y: 0.65, scale: 1.0, rotation: 0.0 },
              video_asset_id: null,
            },
            speech: {
              voice_id: "10000000-0000-0000-0000-000000000004", // Bryce (Piper)
              script: "Welcome to HeyZen. Enter your script here.",
              speed: 1.0,
              pitch: 0.0,
              audio_asset_id: null,
            },
            layers: [],
            subtitles: [],
          },
        ];
      }

      setScenes(docScenes);
      historyRef.current = createHistory(docScenes, docAudioTracks, {
        activeSceneIndex: 0,
        selectedMediaLayerId: null,
        selectedTextLayerId: null,
        selectedElementLayerId: null,
      });
      setCanUndoState(false);
      setCanRedoState(false);
      setSaveStatus("saved");
      setConflictMessage(null);
    } catch (err: any) {
      showNotification("error", err?.message || "Failed to load project.");
    } finally {
      setIsLoadingProject(false);
    }
  }, [workspaceId, projectId]);

  useEffect(() => {
    loadProject();
    loadCatalogs();
  }, [loadProject, loadCatalogs]);

  // Resolve pre-signed MinIO download URLs for active scene media
  useEffect(() => {
    if (!workspaceId || !activeScene) return;

    // 1. Avatar Video Asset URL
    const videoAssetId = activeScene.avatar?.video_asset_id;
    if (videoAssetId && !mediaUrls[videoAssetId]) {
      api.assets
        .getDownloadUrl(workspaceId, videoAssetId)
        .then((res) => {
          if (res?.download_url) {
            setMediaUrls((prev) => ({ ...prev, [videoAssetId]: res.download_url }));
          }
        })
        .catch(() => {});
    }

    // 2. Speech Audio Asset URL
    const audioAssetId = activeScene.speech?.audio_asset_id;
    if (audioAssetId && !mediaUrls[audioAssetId]) {
      api.assets
        .getDownloadUrl(workspaceId, audioAssetId)
        .then((res) => {
          if (res?.download_url) {
            setMediaUrls((prev) => ({ ...prev, [audioAssetId]: res.download_url }));
          }
        })
        .catch(() => {});
    }

    // 3. Scene Background Asset URL (Image or Video)
    const bgAssetId = activeScene.background?.asset_id;
    if (bgAssetId && !mediaUrls[bgAssetId]) {
      api.assets
        .getDownloadUrl(workspaceId, bgAssetId)
        .then((res) => {
          if (res?.download_url) {
            setMediaUrls((prev) => ({ ...prev, [bgAssetId]: res.download_url }));
          }
        })
        .catch(() => {});
    }
  }, [activeScene, workspaceId, mediaUrls]);

  // --------------------------------------------------------------------------
  // 2. PROJECT PERSISTENCE (OCC & VERSIONING)
  // --------------------------------------------------------------------------
  const handleSave = useCallback(
    async (
      updatedScenesList?: StudioScene[],
      updatedAudioTracksList?: AudioTrackItem[]
    ): Promise<number | undefined> => {
      if (!workspaceId || !projectId) {
        setSaveStatus("saved");
        return revisionRef.current;
      }

      const saveOperation = async (): Promise<number | undefined> => {
        setSaveStatus("saving");
        setConflictMessage(null);
        try {
          const baseDoc = currentDocument || {};
          const width = aspectRatio === "9:16" ? 1080 : 1920;
          const height = aspectRatio === "9:16" ? 1920 : 1080;
          const activeScenes = updatedScenesList || scenesRef.current || scenes;
          const activeTracks = updatedAudioTracksList || audioTracksRef.current || audioTracks;

          const updatedSettings = {
            ...(baseDoc.settings || {}),
            aspect_ratio: aspectRatio,
            width,
            height,
            fps: baseDoc.settings?.fps || 30,
            total_duration: activeScenes.reduce((sum, s) => sum + (s.duration || 5.0), 0.0),
            captions: captionSettings,
          };

          const updatedMetadata = {
            ...(baseDoc.metadata || {}),
            title: projectTitle,
          };

          const doc = {
            ...baseDoc,
            schema_version: 1, // Authoritative integer 1 contract
            settings: updatedSettings,
            scenes: activeScenes.map((s, idx) => ({
              ...s,
              sequence: idx + 1,
              duration: typeof s.duration === "number" ? s.duration : 5.0,
            })),
            audio_tracks: activeTracks.map((t) => ({
              id: t.id,
              asset_id: t.asset_id || null,
              name: t.name || "Audio Track",
              volume: typeof t.volume === "number" ? t.volume : 0.3,
              start_time: typeof t.start_time === "number" ? t.start_time : 0.0,
              duration: typeof t.duration === "number" ? t.duration : null,
              loop: Boolean(t.loop),
              muted: Boolean(t.muted),
            })),
            assets: Array.isArray(baseDoc.assets) ? baseDoc.assets : [],
            metadata: updatedMetadata,
          };

          let attempt = 0;
          while (attempt < 2) {
            try {
              const expectedRev = revisionRef.current;
              const updatedVer = await api.projects.createVersion(workspaceId, projectId, {
                expected_revision: expectedRev,
                document: doc,
                source: "studio_manual",
              });

              setCurrentDocument(doc);
              updateRevision(updatedVer.revision);
              setSaveStatus("saved");
              setConflictMessage(null);
              return updatedVer.revision;
            } catch (err: any) {
              const isConflict =
                (err instanceof ApiError && err.code === "CONCURRENCY_CONFLICT") ||
                err?.message?.includes("Revision conflict") ||
                err?.status === 409;

              if (isConflict && attempt === 0) {
                attempt++;
                try {
                  // Refetch latest project & version revision
                  const freshProj = await api.projects.get(workspaceId, projectId);
                  if (freshProj?.revision) {
                    updateRevision(freshProj.revision);
                  }
                  if (freshProj?.current_version_id) {
                    const freshVer = await api.projects.getVersion(workspaceId, projectId, freshProj.current_version_id);
                    if (freshVer?.revision) {
                      updateRevision(Math.max(revisionRef.current, freshVer.revision));
                    }
                    if (Array.isArray(freshVer?.document?.assets)) {
                      doc.assets = freshVer.document.assets;
                    }
                  }
                  // Safely retry once with fresh revision while preserving user's studio state
                  continue;
                } catch {
                  // If refetch failed, proceed to conflict error reporting
                }
              }

              if (isConflict) {
                setSaveStatus("conflict");
                setConflictMessage("Conflict: Project was modified in another session. Click to reload.");
                showNotification("error", "Version conflict detected. Click to reload latest project.");
              } else {
                setSaveStatus("unsaved");
                showNotification("error", err?.message || "Failed to save project.");
              }
              throw err;
            }
          }
        } catch (queueErr) {
          throw queueErr;
        }
      };

      // Serialize save mutations so concurrent calls cannot race
      const queuedPromise = saveQueueRef.current.then(saveOperation, saveOperation);
      saveQueueRef.current = queuedPromise.catch(() => {});
      return queuedPromise;
    },
    [
      workspaceId,
      projectId,
      aspectRatio,
      captionSettings,
      projectTitle,
      currentDocument,
      scenes,
      audioTracks,
      updateRevision,
      showNotification,
    ]
  );

  // --------------------------------------------------------------------------
  // 2b. CLIENT-SIDE UNDO/REDO CONTROLLER (PHASE 40 & PHASE 44)
  // --------------------------------------------------------------------------
  const getCurrentSelection = useCallback((): HistorySelectionState => ({
    activeSceneIndex,
    selectedMediaLayerId,
    selectedTextLayerId,
    selectedElementLayerId,
    selectedLayerIds,
  }), [activeSceneIndex, selectedMediaLayerId, selectedTextLayerId, selectedElementLayerId, selectedLayerIds]);

  const commitStudioHistory = useCallback(
    (
      actionName: string,
      newScenes?: StudioScene[],
      newAudioOrSelection?: AudioTrackItem[] | Partial<HistorySelectionState>,
      newSelection?: Partial<HistorySelectionState>
    ) => {
      if (isRestoringHistoryRef.current) return;
      const targetScenes = newScenes || scenesRef.current || scenes;
      let targetAudioTracks = audioTracksRef.current || audioTracks;
      let partialSelection: Partial<HistorySelectionState> | undefined = newSelection;

      if (Array.isArray(newAudioOrSelection)) {
        targetAudioTracks = newAudioOrSelection;
      } else if (newAudioOrSelection && typeof newAudioOrSelection === "object") {
        partialSelection = newAudioOrSelection;
      }

      const targetSelection: HistorySelectionState = {
        ...getCurrentSelection(),
        ...(partialSelection || {}),
      };

      if (!historyRef.current) {
        historyRef.current = createHistory(targetScenes, targetAudioTracks, targetSelection);
        setCanUndoState(false);
        setCanRedoState(false);
        return;
      }

      const nextHistory = pushHistory(
        historyRef.current,
        targetScenes,
        targetAudioTracks,
        targetSelection,
        actionName
      );
      historyRef.current = nextHistory;
      setCanUndoState(canUndo(nextHistory));
      setCanRedoState(canRedo(nextHistory));
    },
    [getCurrentSelection, scenes, audioTracks]
  );

  const handleUndo = useCallback(async () => {
    if (!historyRef.current || !canUndo(historyRef.current)) return;
    const result = undo(historyRef.current);
    if (!result) return;

    historyRef.current = result.nextState;
    setCanUndoState(canUndo(result.nextState));
    setCanRedoState(canRedo(result.nextState));

    isRestoringHistoryRef.current = true;
    try {
      const { scenes: restoredScenes, audio_tracks: restoredAudioTracks, selection: restoredSelection } = result.snapshot;
      setScenes(restoredScenes);
      if (Array.isArray(restoredAudioTracks)) {
        setAudioTracks(restoredAudioTracks);
      }
      setActiveSceneIndex(restoredSelection.activeSceneIndex);
      setSelectedMediaLayerId(restoredSelection.selectedMediaLayerId);
      setSelectedTextLayerId(restoredSelection.selectedTextLayerId);
      setSelectedElementLayerId(restoredSelection.selectedElementLayerId);
      setSelectedLayerIds(restoredSelection.selectedLayerIds || []);

      await handleSave(restoredScenes, restoredAudioTracks);
      showNotification("info", `Undo: ${result.snapshot.actionName || "action"}`);
    } finally {
      isRestoringHistoryRef.current = false;
    }
  }, [handleSave, showNotification]);

  const handleRedo = useCallback(async () => {
    if (!historyRef.current || !canRedo(historyRef.current)) return;
    const result = redo(historyRef.current);
    if (!result) return;

    historyRef.current = result.nextState;
    setCanUndoState(canUndo(result.nextState));
    setCanRedoState(canRedo(result.nextState));

    isRestoringHistoryRef.current = true;
    try {
      const { scenes: restoredScenes, audio_tracks: restoredAudioTracks, selection: restoredSelection } = result.snapshot;
      setScenes(restoredScenes);
      if (Array.isArray(restoredAudioTracks)) {
        setAudioTracks(restoredAudioTracks);
      }
      setActiveSceneIndex(restoredSelection.activeSceneIndex);
      setSelectedMediaLayerId(restoredSelection.selectedMediaLayerId);
      setSelectedTextLayerId(restoredSelection.selectedTextLayerId);
      setSelectedElementLayerId(restoredSelection.selectedElementLayerId);
      setSelectedLayerIds(restoredSelection.selectedLayerIds || []);

      await handleSave(restoredScenes, restoredAudioTracks);
      showNotification("info", `Redo: ${result.snapshot.actionName || "action"}`);
    } finally {
      isRestoringHistoryRef.current = false;
    }
  }, [handleSave, showNotification]);

  // --------------------------------------------------------------------------
  // 3. SCENE CRUD MANAGEMENT
  // --------------------------------------------------------------------------
  const handleAddScene = async () => {
    const newSceneId = `scene_${Date.now()}`;
    const defaultVoiceId = voices[0]?.id ? String(voices[0].id) : "10000000-0000-0000-0000-000000000004";
    const defaultAvatarId = avatars[0]?.id ? String(avatars[0].id) : "default-presenter";

    const newScene: StudioScene = {
      id: newSceneId,
      sequence: scenes.length + 1,
      duration: 5.0,
      title: `Scene ${String(scenes.length + 1).padStart(2, "0")}`,
      background: { type: "color", value: "#0F172A" },
      transition: { type: "fade", duration: 0.5 },
      avatar: {
        avatar_id: defaultAvatarId,
        view_mode: "half_body",
        position: { x: 0.5, y: 0.65, scale: 1.0, rotation: 0.0 },
        video_asset_id: null,
      },
      speech: {
        voice_id: defaultVoiceId,
        script: "Enter your script for this scene.",
        speed: 1.0,
        pitch: 0.0,
        audio_asset_id: null,
      },
      layers: [],
      subtitles: [],
    };

    const nextScenes = [...scenes, newScene];
    setScenes(nextScenes);
    setActiveSceneIndex(nextScenes.length - 1);
    commitStudioHistory("Add Scene", nextScenes, { activeSceneIndex: nextScenes.length - 1 });
    await handleSave(nextScenes);
    showNotification("success", "New scene added.");
  };

  const handleDuplicateScene = async (index: number) => {
    if (index < 0 || index >= scenes.length) return;
    const target = scenes[index];
    const duplicatedScene: StudioScene = {
      ...target,
      id: `scene_${Date.now()}`,
      sequence: index + 2,
      title: `${target.title || "Scene"} (Copy)`,
      avatar: target.avatar ? { ...target.avatar, video_asset_id: null } : null,
      speech: target.speech ? { ...target.speech, audio_asset_id: null } : null,
    };

    const nextScenes = [
      ...scenes.slice(0, index + 1),
      duplicatedScene,
      ...scenes.slice(index + 1),
    ].map((s, i) => ({ ...s, sequence: i + 1 }));

    setScenes(nextScenes);
    setActiveSceneIndex(index + 1);
    commitStudioHistory("Duplicate Scene", nextScenes, { activeSceneIndex: index + 1 });
    await handleSave(nextScenes);
    showNotification("success", "Scene duplicated.");
  };

  const handleDeleteScene = async (index: number) => {
    if (scenes.length <= 1) {
      showNotification("info", "A project must have at least one scene.");
      return;
    }
    const nextScenes = scenes.filter((_, i) => i !== index).map((s, i) => ({ ...s, sequence: i + 1 }));
    const nextIdx = Math.max(0, Math.min(activeSceneIndex, nextScenes.length - 1));
    setScenes(nextScenes);
    setActiveSceneIndex(nextIdx);
    commitStudioHistory("Delete Scene", nextScenes, { activeSceneIndex: nextIdx });
    await handleSave(nextScenes);
    showNotification("info", "Scene removed.");
  };

  const handleMoveScene = async (fromIndex: number, toIndex: number) => {
    if (toIndex < 0 || toIndex >= scenes.length || fromIndex === toIndex) return;
    const copy = [...scenes];
    const [moved] = copy.splice(fromIndex, 1);
    copy.splice(toIndex, 0, moved);
    const nextScenes = copy.map((s, i) => ({ ...s, sequence: i + 1 }));
    setScenes(nextScenes);
    setActiveSceneIndex(toIndex);
    commitStudioHistory("Reorder Scene", nextScenes, { activeSceneIndex: toIndex });
    await handleSave(nextScenes);
  };

  // --------------------------------------------------------------------------
  // 4. SCENE PROPERTIES & SCRIPT EDITING
  // --------------------------------------------------------------------------
  const updateActiveScene = (updater: (prev: StudioScene) => StudioScene) => {
    setScenes((prev) => {
      const idx = Math.min(activeSceneIndex, prev.length - 1);
      if (idx < 0) return prev;
      const copy = [...prev];
      copy[idx] = updater(copy[idx]);
      return copy;
    });
    setSaveStatus("unsaved");
  };

  const handleScriptChange = (text: string) => {
    updateActiveScene((s) => ({
      ...s,
      speech: {
        voice_id: s.speech?.voice_id || voices[0]?.id || "10000000-0000-0000-0000-000000000004",
        script: text,
        speed: s.speech?.speed ?? 1.0,
        pitch: s.speech?.pitch ?? 0.0,
        audio_asset_id: null, // Audio invalidated on text change
      },
      avatar: s.avatar
        ? {
            ...s.avatar,
            video_asset_id: null, // Avatar video invalidated when script/speech changes
          }
        : null,
    }));
  };

  const handleSelectVoice = async (voiceId: string) => {
    const updated = scenes.map((s, i) => {
      if (i !== activeSceneIndex) return s;
      return {
        ...s,
        speech: {
          ...(s.speech || { script: "", speed: 1.0, pitch: 0.0 }),
          voice_id: voiceId,
          audio_asset_id: null, // Audio invalidated on voice change
        },
        avatar: s.avatar ? { ...s.avatar, video_asset_id: null } : null,
      };
    });
    setScenes(updated);
    commitStudioHistory("Change Voice", updated);
    await handleSave(updated);
    showNotification("success", "Voice updated for scene.");
  };

  const handleSelectAvatar = async (avatarId: string) => {
    const updated = scenes.map((s, i) => {
      if (i !== activeSceneIndex) return s;
      return {
        ...s,
        avatar: {
          ...(s.avatar || {
            view_mode: "half_body",
            position: { x: 0.5, y: 0.65, scale: 1.0, rotation: 0.0 },
          }),
          avatar_id: avatarId,
          video_asset_id: null, // Video invalidated on actor change
        },
      };
    });
    setScenes(updated);
    commitStudioHistory("Change Avatar", updated);
    await handleSave(updated);
    showNotification("success", "Avatar actor updated for scene.");
  };

  const handlePreviewVoice = async (voiceId: string) => {
    if (previewingVoiceId === voiceId) {
      if (previewAudioRef.current) {
        previewAudioRef.current.pause();
        previewAudioRef.current.currentTime = 0;
      }
      setPreviewingVoiceId(null);
      return;
    }

    try {
      setPreviewingVoiceId(voiceId);
      const prevData = await api.creative.getVoicePreview(voiceId, workspaceId);
      if (prevData?.preview_url) {
        if (!previewAudioRef.current) {
          previewAudioRef.current = new Audio();
        }
        previewAudioRef.current.src = prevData.preview_url;
        previewAudioRef.current.onended = () => setPreviewingVoiceId(null);
        previewAudioRef.current.onerror = () => setPreviewingVoiceId(null);
        await previewAudioRef.current.play();
      } else {
        setPreviewingVoiceId(null);
        showNotification("info", "Preview audio currently unavailable for this voice.");
      }
    } catch {
      setPreviewingVoiceId(null);
      showNotification("error", "Failed to play voice preview.");
    }
  };

  // --------------------------------------------------------------------------
  // 4B. MUSIC & MEDIA HANDLERS
  // --------------------------------------------------------------------------
  const handleAddMusicTrack = async (asset: { id: string; name: string }) => {
    const newTrack: AudioTrackItem = {
      id: `track_${Date.now()}`,
      asset_id: asset.id,
      name: asset.name,
      volume: 0.3,
      start_time: 0.0,
      duration: null,
      loop: true,
      muted: false,
    };
    const nextTracks = [...audioTracks, newTrack];
    setAudioTracks(nextTracks);
    setActiveAudioTrackId(newTrack.id);
    commitStudioHistory("Add Audio Track", undefined, nextTracks);
    await handleSave(undefined, nextTracks);
    showNotification("success", `Added background audio track: ${asset.name}`);
  };

  const handleUpdateMusicTrack = (
    trackId: string,
    updates: Partial<AudioTrackItem>
  ) => {
    const nextTracks = audioTracks.map((t) =>
      t.id === trackId ? { ...t, ...updates } : t
    );
    setAudioTracks(nextTracks);
    setSaveStatus("unsaved");
  };

  const handleCommitAudioTrack = async (actionName = "Update Audio Track") => {
    commitStudioHistory(actionName, undefined, audioTracksRef.current);
    await handleSave(undefined, audioTracksRef.current);
  };

  const handleRemoveMusicTrack = async (trackId: string) => {
    const nextTracks = audioTracks.filter((t) => t.id !== trackId);
    setAudioTracks(nextTracks);
    setActiveAudioTrackId(nextTracks[0]?.id || null);
    commitStudioHistory("Remove Audio Track", undefined, nextTracks);
    await handleSave(undefined, nextTracks);
    showNotification("info", "Background audio track removed.");
  };

  const getNeighborLayers = useCallback((currentLayerId: string): SnapTargetLayer[] => {
    if (!activeScene?.layers) return [];
    return activeScene.layers
      .filter((l: any) => l.id !== currentLayerId && l.enabled !== false)
      .map((l: any) => {
        const bounds = getLayerEffectiveBounds(l);
        return {
          id: l.id,
          name: l.name,
          enabled: l.enabled !== false,
          locked: l.locked === true,
          bounds: {
            x: l.transform?.x ?? 0.5,
            y: l.transform?.y ?? 0.5,
            width: bounds.width,
            height: bounds.height,
          },
        };
      });
  }, [activeScene?.layers]);

  const handleSetSceneBackground = async (asset: { id: string; type: string; name: string }) => {
    updateActiveScene((s) => ({
      ...s,
      background: {
        type: asset.type,
        asset_id: asset.id,
        value: asset.name,
      },
    }));
    await handleSave();
    showNotification("success", `Set ${asset.type} as scene background.`);
  };

  const handleAddMediaLayer = async (asset: { id: string; type: string; name: string }) => {
    const newId = `layer_${Date.now()}`;
    const newLayer = {
      id: newId,
      type: asset.type === "video" ? "video" : "image",
      name: asset.name,
      start_time: 0.0,
      end_time: activeScene?.duration || 5.0,
      enabled: true,
      content: {
        asset_id: asset.id,
        name: asset.name,
        media_type: asset.type,
        opacity: 1.0,
      },
      transform: {
        x: 0.5,
        y: 0.5,
        scale: 1.0,
        rotation: 0.0,
      },
    };
    const currentLayers = activeScene?.layers || [];
    const nextLayers = [...currentLayers, newLayer];
    const nextScenes = scenes.map((s, idx) =>
      idx === activeSceneIndex ? { ...s, layers: nextLayers } : s
    );
    setScenes(nextScenes);
    selectMediaLayer(newId);
    setActiveLeftTool("media");
    setActiveTab("media");
    commitStudioHistory("Add Media Layer", nextScenes, { selectedMediaLayerId: newId });
    await handleSave(nextScenes);
    showNotification("success", `Added ${asset.name} as visual scene layer.`);
  };

  // --------------------------------------------------------------------------
  // 4b. UNIFIED TIMING UPDATE HANDLERS (PHASE 33)
  // --------------------------------------------------------------------------
  const handleUpdateLayerTiming = (
    sceneIdx: number,
    layerId: string,
    startTime: number,
    endTime: number
  ) => {
    setScenes((prev) => {
      if (sceneIdx < 0 || sceneIdx >= prev.length) return prev;
      const next = [...prev];
      const targetScene = next[sceneIdx];
      if (!targetScene || !targetScene.layers) return prev;
      const updatedLayers = targetScene.layers.map((l) => {
        if (l.id !== layerId) return l;
        if (l.locked === true) return l;
        return {
          ...l,
          start_time: startTime,
          end_time: endTime,
        };
      });
      next[sceneIdx] = {
        ...targetScene,
        layers: updatedLayers,
      };
      return next;
    });
    setSaveStatus("unsaved");
  };

  const handleUpdateCueTiming = (
    sceneIdx: number,
    cueId: string | number,
    startTime: number,
    endTime: number
  ) => {
    setScenes((prev) => {
      if (sceneIdx < 0 || sceneIdx >= prev.length) return prev;
      const next = [...prev];
      const targetScene = next[sceneIdx];
      if (!targetScene || !targetScene.subtitles) return prev;
      const updatedSubtitles = (targetScene.subtitles as any[]).map((cue) => {
        if (String(cue.id) !== String(cueId)) return cue;
        return {
          ...cue,
          start: startTime,
          end: endTime,
          start_time: startTime,
          end_time: endTime,
        };
      });
      next[sceneIdx] = {
        ...targetScene,
        subtitles: updatedSubtitles,
      };
      return next;
    });
    setSaveStatus("unsaved");
  };

  const handleUpdateMusicTiming = (
    trackId: string,
    startTime: number,
    duration: number
  ) => {
    setAudioTracks((prev) =>
      prev.map((t) =>
        t.id === trackId
          ? {
              ...t,
              start_time: startTime,
              duration: duration,
            }
          : t
      )
    );
    setSaveStatus("unsaved");
  };

  const handleCommitTiming = async () => {
    commitStudioHistory("Timeline Timing", scenesRef.current, audioTracksRef.current);
    await handleSave(scenesRef.current, audioTracksRef.current);
  };

  const timelineTracksContainerRef = useRef<HTMLDivElement>(null);

  const handleDeleteAvatar = (index: number) => {
    const nextScenes = scenes.map((s, i) =>
      i === index ? { ...s, avatar: null } : s
    );
    setScenes(nextScenes);
    commitStudioHistory("Delete Avatar", nextScenes);
    handleSave(nextScenes);
    showNotification("info", "Avatar removed from scene.");
  };

  const handleDeleteScript = (index: number) => {
    const nextScenes = scenes.map((s, i) =>
      i === index
        ? {
            ...s,
            speech: s.speech
              ? { ...s.speech, script: "", audio_asset_id: null }
              : null,
          }
        : s
    );
    setScenes(nextScenes);
    commitStudioHistory("Delete Script", nextScenes);
    handleSave(nextScenes);
    showNotification("info", "Script cleared from scene.");
  };

  const handleDeleteSpeechAudio = (index: number) => {
    const nextScenes = scenes.map((s, i) =>
      i === index
        ? {
            ...s,
            speech: s.speech ? { ...s.speech, audio_asset_id: null } : null,
          }
        : s
    );
    setScenes(nextScenes);
    commitStudioHistory("Delete Speech Audio", nextScenes);
    handleSave(nextScenes);
    showNotification("info", "Speech audio cleared from scene.");
  };

  const handleDeleteLayer = (layerId: string) => {
    if (selectedLayerIds.length > 1 && selectedLayerIds.includes(layerId)) {
      const currentLayers = (activeScene?.layers || []) as VisualLayer[];
      const nextLayers = groupDeleteLayers(currentLayers, selectedLayerIds);
      const nextScenes = scenes.map((s, idx) =>
        idx === activeSceneIndex ? { ...s, layers: nextLayers } : s
      );
      setScenes(nextScenes);
      clearVisualSelection();
      commitStudioHistory("Delete Group", nextScenes, { selectedLayerIds: [] });
      handleSave(nextScenes);
      showNotification("info", `Deleted ${selectedLayerIds.length} layers.`);
      return;
    }
    const current = activeScene?.layers || [];
    const updated = deleteLayerWithZIndex(current, layerId);
    const nextScenes = scenes.map((s, idx) =>
      idx === activeSceneIndex ? { ...s, layers: updated } : s
    );
    setScenes(nextScenes);
    commitStudioHistory("Delete Layer", nextScenes);
    handleSave(nextScenes);
    showNotification("info", "Layer deleted.");
  };

  const handleDeleteCue = (sceneIdx: number, cueId: string | number) => {
    const target = scenes[sceneIdx];
    if (!target || !target.subtitles) return;
    const updatedSubtitles = (target.subtitles as any[]).filter(
      (c) => String(c.id) !== String(cueId)
    );
    const nextScenes = scenes.map((s, idx) =>
      idx === sceneIdx ? { ...s, subtitles: updatedSubtitles } : s
    );
    setScenes(nextScenes);
    commitStudioHistory("Delete Caption Cue", nextScenes);
    handleSave(nextScenes);
    showNotification("info", "Caption cue deleted.");
  };

  const startResizeScene = (
    e: React.PointerEvent,
    sceneIdx: number,
    edge: "left" | "right"
  ) => {
    e.stopPropagation();
    if (e.button !== 0) return;

    const startX = e.clientX;
    const initialScenes = [...scenesRef.current];
    const targetScene = initialScenes[sceneIdx];
    if (!targetScene) return;

    const initDuration = Number(targetScene.duration || 5.0);
    const initPrevDuration = sceneIdx > 0 ? Number(initialScenes[sceneIdx - 1]?.duration || 5.0) : 0;
    const container = timelineTracksContainerRef.current;
    const containerWidth = container ? container.getBoundingClientRect().width : 1000;
    const secondsPerPixel = totalDuration / Math.max(1, containerWidth);

    const onPointerMove = (ev: PointerEvent) => {
      const dx = ev.clientX - startX;
      const deltaSeconds = dx * secondsPerPixel;

      setScenes((prev) => {
        const next = [...prev];
        if (edge === "right") {
          const newDur = calculateSceneResizeTiming(
            initDuration,
            deltaSeconds,
            1.0,
            60.0
          );
          const sc = next[sceneIdx];
          if (!sc) return prev;
          const updatedLayers = clampLayersToSceneDuration(sc.layers || [], newDur);
          const updatedSubtitles = (sc.subtitles || []).map((cue: any) => ({
            ...cue,
            end: Math.min(newDur, cue.end || newDur),
            end_time: Math.min(newDur, cue.end_time || newDur),
          }));
          next[sceneIdx] = {
            ...sc,
            duration: newDur,
            layers: updatedLayers,
            subtitles: updatedSubtitles,
          };
        } else {
          if (sceneIdx > 0) {
            const maxDelta = initPrevDuration - 1.0;
            const minDelta = -(initDuration - 1.0);
            const clampedDelta = Math.max(minDelta, Math.min(maxDelta, deltaSeconds));
            const newPrevDur = Math.round((initPrevDuration + clampedDelta) * 10) / 10;
            const newCurDur = Math.round((initDuration - clampedDelta) * 10) / 10;

            const prevSc = next[sceneIdx - 1];
            const curSc = next[sceneIdx];
            if (prevSc && curSc) {
              next[sceneIdx - 1] = {
                ...prevSc,
                duration: newPrevDur,
                layers: clampLayersToSceneDuration(prevSc.layers || [], newPrevDur),
              };
              next[sceneIdx] = {
                ...curSc,
                duration: newCurDur,
                layers: clampLayersToSceneDuration(curSc.layers || [], newCurDur),
              };
            }
          } else {
            const newDur = calculateSceneResizeTiming(
              initDuration,
              -deltaSeconds,
              1.0,
              60.0
            );
            const sc = next[0];
            if (sc) {
              next[0] = {
                ...sc,
                duration: newDur,
                layers: clampLayersToSceneDuration(sc.layers || [], newDur),
              };
            }
          }
        }
        return next;
      });
      setSaveStatus("unsaved");
    };

    const onPointerUp = () => {
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerup", onPointerUp);
      window.removeEventListener("pointercancel", onPointerUp);
      commitStudioHistory("Resize Scene Duration", scenesRef.current);
      handleSave(scenesRef.current);
    };

    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", onPointerUp);
    window.addEventListener("pointercancel", onPointerUp);
  };

  const startResizeAvatar = (
    e: React.PointerEvent,
    sceneIdx: number,
    edge: "left" | "right"
  ) => {
    e.stopPropagation();
    if (e.button !== 0) return;

    const startX = e.clientX;
    const initialScenes = [...scenesRef.current];
    const targetScene = initialScenes[sceneIdx];
    if (!targetScene || !targetScene.avatar) return;

    const sceneDuration = Number(targetScene.duration || 5.0);
    const initStart = Number(targetScene.avatar.start_time ?? 0);
    const initEnd = Number(targetScene.avatar.end_time ?? sceneDuration);
    const container = timelineTracksContainerRef.current;
    const containerWidth = container ? container.getBoundingClientRect().width : 1000;
    const secondsPerPixel = totalDuration / Math.max(1, containerWidth);

    const onPointerMove = (ev: PointerEvent) => {
      const dx = ev.clientX - startX;
      const deltaSeconds = dx * secondsPerPixel;

      setScenes((prev) => {
        const next = [...prev];
        const sc = next[sceneIdx];
        if (!sc || !sc.avatar) return prev;

        let newStart = initStart;
        let newEnd = initEnd;

        if (edge === "left") {
          newStart = Math.max(0, Math.min(initEnd - MIN_CLIP_DURATION, initStart + deltaSeconds));
        } else {
          newEnd = Math.min(sceneDuration, Math.max(initStart + MIN_CLIP_DURATION, initEnd + deltaSeconds));
        }

        next[sceneIdx] = {
          ...sc,
          avatar: {
            ...sc.avatar,
            start_time: Math.round(newStart * 10) / 10,
            end_time: Math.round(newEnd * 10) / 10,
          },
        };
        return next;
      });
      setSaveStatus("unsaved");
    };

    const onPointerUp = () => {
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerup", onPointerUp);
      window.removeEventListener("pointercancel", onPointerUp);
      commitStudioHistory("Resize Avatar Timing", scenesRef.current);
      handleSave(scenesRef.current);
    };

    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", onPointerUp);
    window.addEventListener("pointercancel", onPointerUp);
  };

  const startResizeSpeech = (
    e: React.PointerEvent,
    sceneIdx: number,
    edge: "left" | "right",
    kind: "script" | "audio"
  ) => {
    e.stopPropagation();
    if (e.button !== 0) return;

    const startX = e.clientX;
    const initialScenes = [...scenesRef.current];
    const targetScene = initialScenes[sceneIdx];
    if (!targetScene || !targetScene.speech) return;

    const sceneDuration = Number(targetScene.duration || 5.0);
    const initStart = Number(targetScene.speech.start_time ?? 0);
    const initEnd = Number(targetScene.speech.end_time ?? sceneDuration);
    const container = timelineTracksContainerRef.current;
    const containerWidth = container ? container.getBoundingClientRect().width : 1000;
    const secondsPerPixel = totalDuration / Math.max(1, containerWidth);

    const onPointerMove = (ev: PointerEvent) => {
      const dx = ev.clientX - startX;
      const deltaSeconds = dx * secondsPerPixel;

      setScenes((prev) => {
        const next = [...prev];
        const sc = next[sceneIdx];
        if (!sc || !sc.speech) return prev;

        let newStart = initStart;
        let newEnd = initEnd;

        if (edge === "left") {
          newStart = Math.max(0, Math.min(initEnd - MIN_CLIP_DURATION, initStart + deltaSeconds));
        } else {
          newEnd = Math.min(sceneDuration, Math.max(initStart + MIN_CLIP_DURATION, initEnd + deltaSeconds));
        }

        next[sceneIdx] = {
          ...sc,
          speech: {
            ...sc.speech,
            start_time: Math.round(newStart * 10) / 10,
            end_time: Math.round(newEnd * 10) / 10,
          },
        };
        return next;
      });
      setSaveStatus("unsaved");
    };

    const onPointerUp = () => {
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerup", onPointerUp);
      window.removeEventListener("pointercancel", onPointerUp);
      commitStudioHistory(`Resize ${kind === "script" ? "Script" : "Speech"} Timing`, scenesRef.current);
      handleSave(scenesRef.current);
    };

    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", onPointerUp);
    window.addEventListener("pointercancel", onPointerUp);
  };

  // --------------------------------------------------------------------------
  // 4c. UNIFIED CANVAS TRANSFORM HANDLERS (PHASE 34)
  // --------------------------------------------------------------------------
  const handleUpdateLayerTransform = (
    layerId: string,
    changes: Partial<{ x: number; y: number; scale: number; rotation: number }>
  ) => {
    setScenes((prev) => {
      if (activeSceneIndex < 0 || activeSceneIndex >= prev.length) return prev;
      const next = [...prev];
      const targetScene = next[activeSceneIndex];
      if (!targetScene || !targetScene.layers) return prev;
      const updatedLayers = targetScene.layers.map((l: any) => {
        if (l.id !== layerId) return l;
        if (l.locked === true) return l;
        return {
          ...l,
          transform: {
            ...(l.transform || { x: 0.5, y: 0.5, scale: 1.0, rotation: 0.0 }),
            ...changes,
          },
        };
      });
      next[activeSceneIndex] = {
        ...targetScene,
        layers: updatedLayers,
      };
      return next;
    });
    setSaveStatus("unsaved");
  };

  const handleCommitLayerTransform = async () => {
    commitStudioHistory("Transform Layer");
    await handleSave();
  };

  // --------------------------------------------------------------------------
  // 4c. CANONICAL CROSS-TYPE LAYER ORDERING HANDLERS (PHASE 42B)
  // --------------------------------------------------------------------------
  const handleBringLayerForward = useCallback(
    async (layerId: string) => {
      if (!activeScene || !activeScene.layers) return;
      const target = activeScene.layers.find((l: any) => l.id === layerId);
      if (!target || target.locked === true) return;

      const updatedLayers = bringLayerForward(activeScene.layers, layerId);
      const nextScenes = scenes.map((s, idx) =>
        idx === activeSceneIndex ? { ...s, layers: updatedLayers } : s
      );
      setScenes(nextScenes);
      commitStudioHistory("Bring Layer Forward", nextScenes);
      await handleSave(nextScenes);
    },
    [activeScene, activeSceneIndex, scenes, commitStudioHistory, handleSave]
  );

  const handleSendLayerBackward = useCallback(
    async (layerId: string) => {
      if (!activeScene || !activeScene.layers) return;
      const target = activeScene.layers.find((l: any) => l.id === layerId);
      if (!target || target.locked === true) return;

      const updatedLayers = sendLayerBackward(activeScene.layers, layerId);
      const nextScenes = scenes.map((s, idx) =>
        idx === activeSceneIndex ? { ...s, layers: updatedLayers } : s
      );
      setScenes(nextScenes);
      commitStudioHistory("Send Layer Backward", nextScenes);
      await handleSave(nextScenes);
    },
    [activeScene, activeSceneIndex, scenes, commitStudioHistory, handleSave]
  );

  const handleBringLayerToFront = useCallback(
    async (layerId: string) => {
      if (!activeScene || !activeScene.layers) return;
      const target = activeScene.layers.find((l: any) => l.id === layerId);
      if (!target || target.locked === true) return;

      const updatedLayers = bringLayerToFront(activeScene.layers, layerId);
      const nextScenes = scenes.map((s, idx) =>
        idx === activeSceneIndex ? { ...s, layers: updatedLayers } : s
      );
      setScenes(nextScenes);
      commitStudioHistory("Bring Layer To Front", nextScenes);
      await handleSave(nextScenes);
    },
    [activeScene, activeSceneIndex, scenes, commitStudioHistory, handleSave]
  );

  const handleSendLayerToBack = useCallback(
    async (layerId: string) => {
      if (!activeScene || !activeScene.layers) return;
      const target = activeScene.layers.find((l: any) => l.id === layerId);
      if (!target || target.locked === true) return;

      const updatedLayers = sendLayerToBack(activeScene.layers, layerId);
      const nextScenes = scenes.map((s, idx) =>
        idx === activeSceneIndex ? { ...s, layers: updatedLayers } : s
      );
      setScenes(nextScenes);
      commitStudioHistory("Send Layer To Back", nextScenes);
      await handleSave(nextScenes);
    },
    [activeScene, activeSceneIndex, scenes, commitStudioHistory, handleSave]
  );

  const handleMoveLayerToIndex = useCallback(
    async (layerId: string, toIndex: number) => {
      if (!activeScene || !activeScene.layers) return;
      const target = activeScene.layers.find((l: any) => l.id === layerId);
      if (!target || target.locked === true) return;

      const updatedLayers = moveLayerToIndex(activeScene.layers, layerId, toIndex);
      const nextScenes = scenes.map((s, idx) =>
        idx === activeSceneIndex ? { ...s, layers: updatedLayers } : s
      );
      setScenes(nextScenes);
      commitStudioHistory("Reorder Layers", nextScenes);
      await handleSave(nextScenes);
    },
    [activeScene, activeSceneIndex, scenes, commitStudioHistory, handleSave]
  );

  // --------------------------------------------------------------------------
  // 5. ASYNC AI GENERATION: SPEECH & TALKING AVATAR
  // --------------------------------------------------------------------------
  const handleGenerateSpeech = async () => {
    if (!workspaceId || !projectId || !activeScene) return;
    const scriptText = activeScene.speech?.script?.trim();
    if (!scriptText) {
      showNotification("error", "Please enter a script before generating speech audio.");
      return;
    }

    setSpeechJobState({ isSynthesizing: true, progressPct: 0, stage: "Submitting..." });
    try {
      let effectiveRev = revisionRef.current;
      try {
        const savedRev = await handleSave();
        if (typeof savedRev === "number") {
          effectiveRev = savedRev;
        } else {
          effectiveRev = revisionRef.current;
        }
      } catch {
        setSpeechJobState({ isSynthesizing: false, progressPct: 0 });
        return;
      }

      let res: any;
      try {
        res = await api.orchestration.synthesizeSpeech(workspaceId, projectId, {
          expected_revision: effectiveRev,
          scene_ids: [activeScene.id],
          run_async: true,
        });
      } catch (speechErr: any) {
        const isConflict =
          (speechErr instanceof ApiError && speechErr.code === "CONCURRENCY_CONFLICT") ||
          speechErr?.message?.includes("Revision conflict") ||
          speechErr?.status === 409;
        if (isConflict) {
          const freshProj = await api.projects.get(workspaceId, projectId);
          if (freshProj?.revision) {
            updateRevision(freshProj.revision);
            effectiveRev = freshProj.revision;
            res = await api.orchestration.synthesizeSpeech(workspaceId, projectId, {
              expected_revision: effectiveRev,
              scene_ids: [activeScene.id],
              run_async: true,
            });
          } else {
            throw speechErr;
          }
        } else {
          throw speechErr;
        }
      }

      const jobId = res?.id;
      if (!jobId) {
        if (res?.revision) updateRevision(res.revision);
        await loadProject();
        setSpeechJobState({ isSynthesizing: false, progressPct: 100, stage: "Done" });
        showNotification("success", "Speech synthesis complete.");
        return;
      }

      setSpeechJobState((p) => ({ ...p, jobId }));

      // SSE Job Streaming with Durable Fallback
      api.jobs.stream(
        jobId,
        (event) => {
          setSpeechJobState((prev) => ({
            ...prev,
            progressPct: event.progress_pct ?? prev.progressPct,
            stage: event.stage || event.status,
          }));

          if (event.status === "succeeded" || event.status === "completed") {
            setSpeechJobState({ isSynthesizing: false, progressPct: 100, stage: "Completed" });
            loadProject();
            showNotification("success", "Speech audio synthesized successfully!");
          } else if (event.status === "failed") {
            setSpeechJobState({ isSynthesizing: false, progressPct: 0, stage: "Failed" });
            showNotification("error", event.message || "Speech synthesis failed.");
          }
        },
        () => {
          // Durable check on drop
          api.jobs.get(jobId).then((j) => {
            if (j.status === "succeeded") {
              setSpeechJobState({ isSynthesizing: false, progressPct: 100, stage: "Completed" });
              loadProject();
            }
          }).catch(() => {});
        }
      );
    } catch (err: any) {
      setSpeechJobState({ isSynthesizing: false, progressPct: 0 });
      showNotification("error", err?.message || "Failed to initiate speech synthesis.");
    }
  };

  const handleGenerateAvatarVideo = async () => {
    if (!workspaceId || !projectId || !activeScene) return;
    if (!activeScene.speech?.audio_asset_id) {
      showNotification("error", "Speech audio is required. Click 'Generate Speech' first.");
      return;
    }

    setAvatarJobState({ isGenerating: true, progressPct: 0, stage: "Submitting..." });
    try {
      let effectiveRev = revisionRef.current;
      try {
        const savedRev = await handleSave();
        if (typeof savedRev === "number") {
          effectiveRev = savedRev;
        } else {
          effectiveRev = revisionRef.current;
        }
      } catch {
        setAvatarJobState({ isGenerating: false, progressPct: 0 });
        return;
      }

      let res: any;
      try {
        res = await api.orchestration.generateAvatarVideo(workspaceId, projectId, {
          expected_revision: effectiveRev,
          scene_id: activeScene.id,
          run_async: true,
        });
      } catch (avatarErr: any) {
        const isConflict =
          (avatarErr instanceof ApiError && avatarErr.code === "CONCURRENCY_CONFLICT") ||
          avatarErr?.message?.includes("Revision conflict") ||
          avatarErr?.status === 409;
        if (isConflict) {
          const freshProj = await api.projects.get(workspaceId, projectId);
          if (freshProj?.revision) {
            updateRevision(freshProj.revision);
            effectiveRev = freshProj.revision;
            res = await api.orchestration.generateAvatarVideo(workspaceId, projectId, {
              expected_revision: effectiveRev,
              scene_id: activeScene.id,
              run_async: true,
            });
          } else {
            throw avatarErr;
          }
        } else {
          throw avatarErr;
        }
      }

      const jobId = res?.id;
      if (!jobId) {
        if (res?.revision) updateRevision(res.revision);
        await loadProject();
        setAvatarJobState({ isGenerating: false, progressPct: 100, stage: "Done" });
        showNotification("success", "Avatar lip-sync video complete.");
        return;
      }

      setAvatarJobState((p) => ({ ...p, jobId }));

      api.jobs.stream(
        jobId,
        (event) => {
          setAvatarJobState((prev) => ({
            ...prev,
            progressPct: event.progress_pct ?? prev.progressPct,
            stage: event.stage || event.status,
          }));

          if (event.status === "succeeded" || event.status === "completed") {
            setAvatarJobState({ isGenerating: false, progressPct: 100, stage: "Completed" });
            loadProject();
            showNotification("success", "Talking avatar video generated successfully!");
          } else if (event.status === "failed") {
            const isGpu =
              event.message?.includes("GPU_UNAVAILABLE") ||
              (event.error_details && JSON.stringify(event.error_details).includes("GPU_UNAVAILABLE"));
            const msg = isGpu
              ? "GPU_UNAVAILABLE: No NVIDIA CUDA GPU detected on host. MuseTalk requires a dedicated CUDA GPU. Please select Wav2Lip (CPU Prototype)."
              : event.message || "Avatar video generation failed.";
            setAvatarJobState({ isGenerating: false, progressPct: 0, stage: "Failed" });
            showNotification("error", msg);
          }
        },
        () => {
          api.jobs.get(jobId).then((j) => {
            if (j.status === "succeeded") {
              setAvatarJobState({ isGenerating: false, progressPct: 100, stage: "Completed" });
              loadProject();
            }
          }).catch(() => {});
        }
      );
    } catch (err: any) {
      const isGpu = err?.code === "GPU_UNAVAILABLE" || err?.message?.includes("GPU_UNAVAILABLE");
      const msg = isGpu
        ? "GPU_UNAVAILABLE: No NVIDIA CUDA GPU detected on host. MuseTalk requires a dedicated CUDA GPU. Please select Wav2Lip (CPU Prototype)."
        : err?.message || "Failed to initiate avatar generation.";
      setAvatarJobState({ isGenerating: false, progressPct: 0 });
      showNotification("error", msg);
    }
  };

  const handleGenerateCaptions = async (sceneIndex: number) => {
    if (!workspaceId || !projectId) return;
    const targetScene = scenes[sceneIndex];
    if (!targetScene) return;

    if (!targetScene.speech?.audio_asset_id) {
      showNotification("error", "Scene has no generated speech audio. Generate speech first before transcribing.");
      return;
    }

    setIsTranscribing(true);
    try {
      let effectiveRev = revisionRef.current;
      try {
        const savedRev = await handleSave();
        if (typeof savedRev === "number") {
          effectiveRev = savedRev;
        } else {
          effectiveRev = revisionRef.current;
        }
      } catch {
        setIsTranscribing(false);
        return;
      }

      let resp: any;
      try {
        resp = await api.orchestration.transcribeAudio(workspaceId, projectId, {
          expected_revision: effectiveRev,
          scene_id: targetScene.id,
          run_async: true,
        });
      } catch (transErr: any) {
        const isConflict =
          (transErr instanceof ApiError && transErr.code === "CONCURRENCY_CONFLICT") ||
          transErr?.message?.includes("Revision conflict") ||
          transErr?.status === 409;
        if (isConflict) {
          const freshProj = await api.projects.get(workspaceId, projectId);
          if (freshProj?.revision) {
            updateRevision(freshProj.revision);
            effectiveRev = freshProj.revision;
            resp = await api.orchestration.transcribeAudio(workspaceId, projectId, {
              expected_revision: effectiveRev,
              scene_id: targetScene.id,
              run_async: true,
            });
          } else {
            throw transErr;
          }
        } else {
          throw transErr;
        }
      }

      const jobId = resp?.id;
      if (!jobId) {
        // Synchronous completion fallback
        if (resp?.revision) updateRevision(resp.revision);
        if (resp?.document) {
          setCurrentDocument(resp.document);
          if (resp.document.scenes) {
            setScenes(resp.document.scenes);
          }
        } else {
          await loadProject();
        }
        showNotification("success", "Captions generated successfully with Faster-Whisper!");
        return;
      }

      // Stream / Poll transcription job
      api.jobs.stream(
        jobId,
        (event) => {
          if (event.status === "succeeded" || event.status === "completed") {
            setIsTranscribing(false);
            loadProject();
            showNotification("success", "Captions generated successfully with Faster-Whisper!");
          } else if (event.status === "failed") {
            setIsTranscribing(false);
            showNotification("error", event.message || "Caption transcription failed.");
          }
        },
        () => {
          api.jobs.get(jobId).then((j) => {
            if (j.status === "succeeded") {
              setIsTranscribing(false);
              loadProject();
              showNotification("success", "Captions generated successfully!");
            }
          }).catch(() => {});
        }
      );
    } catch (err: any) {
      setIsTranscribing(false);
      showNotification("error", err?.message || "Failed to transcribe audio.");
    }
  };

  // --------------------------------------------------------------------------
  // 6. TIMELINE COMPOSITOR EXPORT / RENDER
  // --------------------------------------------------------------------------
  const handleExport = async () => {
    if (!workspaceId || !projectId) {
      showNotification("error", "No active project to render.");
      return;
    }
    if (renderState.isRendering) return;

    setRenderState({ isRendering: true, progressPct: 0, stage: "Saving timeline state..." });
    let effectiveRevision = revisionRef.current;
    try {
      // Save document state first to guarantee persisted OCC revision and latest timeline state
      const savedRev = await handleSave();
      if (typeof savedRev === "number") {
        effectiveRevision = savedRev;
      } else {
        effectiveRevision = revisionRef.current;
      }
    } catch (saveErr: any) {
      setRenderState({
        isRendering: false,
        progressPct: 0,
        error: saveErr?.message || "Failed to save timeline state before rendering.",
      });
      return;
    }

    setRenderState({ isRendering: true, progressPct: 0, stage: "Queued" });
    try {
      let job: any;
      try {
        job = await api.orchestration.renderProject(workspaceId, projectId, {
          expected_revision: effectiveRevision,
          resolution: "1080p",
          format: "mp4",
          export_format: "mp4",
        });
      } catch (renderErr: any) {
        const isConflict =
          (renderErr instanceof ApiError && renderErr.code === "CONCURRENCY_CONFLICT") ||
          renderErr?.message?.includes("Revision conflict") ||
          renderErr?.status === 409;
        if (isConflict) {
          const freshProj = await api.projects.get(workspaceId, projectId);
          if (freshProj?.revision) {
            updateRevision(freshProj.revision);
            effectiveRevision = freshProj.revision;
            job = await api.orchestration.renderProject(workspaceId, projectId, {
              expected_revision: effectiveRevision,
              resolution: "1080p",
              format: "mp4",
              export_format: "mp4",
            });
          } else {
            throw renderErr;
          }
        } else {
          throw renderErr;
        }
      }

      setRenderState((p) => ({ ...p, jobId: job.id, stage: "Processing" }));

      api.jobs.stream(
        job.id,
        async (event) => {
          let downloadUrl =
            event.result?.video_download_url ||
            event.result_payload?.video_download_url;

          const outputAssetId =
            event.result?.output_asset_id ||
            event.result_payload?.output_asset_id;

          if (!downloadUrl && outputAssetId && workspaceId) {
            try {
              const dlResp = await api.assets.getDownloadUrl(workspaceId, outputAssetId);
              if (dlResp?.download_url) {
                downloadUrl = dlResp.download_url;
              }
            } catch {
              // fallback
            }
          }

          setRenderState((prev) => ({
            ...prev,
            progressPct: event.progress_pct ?? prev.progressPct,
            stage: event.stage || event.status,
            downloadUrl: downloadUrl || prev.downloadUrl,
          }));

          if (event.status === "succeeded" || event.status === "completed") {
            setRenderState((prev) => ({
              ...prev,
              isRendering: false,
              progressPct: 100,
              stage: "Completed",
              downloadUrl: downloadUrl || prev.downloadUrl,
            }));
            showNotification("success", "Video rendering completed!");
          } else if (event.status === "failed") {
            const isGpu =
              event.message?.includes("GPU_REQUIRED") ||
              event.message?.includes("GPU_UNAVAILABLE") ||
              JSON.stringify(event).includes("GPU_REQUIRED") ||
              JSON.stringify(event).includes("GPU_UNAVAILABLE");
            const errorMsg = isGpu
              ? "GPU_REQUIRED: Neural avatar generation requires a CUDA GPU or configured remote GPU worker."
              : event.message || "Video rendering failed.";

            setRenderState((prev) => ({
              ...prev,
              isRendering: false,
              stage: "Failed",
              error: errorMsg,
            }));
            showNotification("error", errorMsg);
          } else if (event.status === "cancelled") {
            setRenderState((prev) => ({
              ...prev,
              isRendering: false,
              stage: "Cancelled",
              error: "Render job was cancelled",
            }));
          }
        },
        async () => {
          try {
            const j = await api.jobs.get(job.id);
            if (j.status === "succeeded") {
              let dUrl = (j.result as any)?.video_download_url;
              const outId = (j.result as any)?.output_asset_id;
              if (!dUrl && outId && workspaceId) {
                const dlResp = await api.assets.getDownloadUrl(workspaceId, outId);
                dUrl = dlResp?.download_url;
              }
              setRenderState((prev) => ({
                ...prev,
                isRendering: false,
                progressPct: 100,
                stage: "Completed",
                downloadUrl: dUrl || prev.downloadUrl,
              }));
            } else if (j.status === "failed") {
              const isGpu =
                j.error_message?.includes("GPU_REQUIRED") ||
                j.error_message?.includes("GPU_UNAVAILABLE");
              const err = isGpu
                ? "GPU_REQUIRED: Neural avatar generation requires a CUDA GPU or configured remote GPU worker."
                : j.error_message || "Video rendering failed.";
              setRenderState((prev) => ({
                ...prev,
                isRendering: false,
                stage: "Failed",
                error: err,
              }));
              showNotification("error", err);
            }
          } catch {}
        }
      );
    } catch (err: any) {
      const isGpu =
        err?.code === "GPU_REQUIRED" ||
        err?.code === "GPU_UNAVAILABLE" ||
        err?.message?.includes("GPU_REQUIRED") ||
        err?.message?.includes("GPU_UNAVAILABLE");
      const errDetail = isGpu
        ? "GPU_REQUIRED: Neural avatar generation requires a CUDA GPU or configured remote GPU worker."
        : err?.message || "Failed to submit video render job.";

      setRenderState({
        isRendering: false,
        progressPct: 0,
        error: errDetail,
      });
      showNotification("error", errDetail);
    }
  };

  const handleCancelRender = async () => {
    if (!renderState.jobId) return;
    try {
      await api.jobs.cancel(renderState.jobId, "Cancelled by user");
      setRenderState((prev) => ({ ...prev, isRendering: false, stage: "Cancelled" }));
      showNotification("info", "Render job cancelled.");
    } catch {
      // ignore
    }
  };

  // --------------------------------------------------------------------------
  // 7. CANVAS PLAYER CONTROLS
  // --------------------------------------------------------------------------
  const activeVideoUrl =
    renderState.downloadUrl ||
    (activeScene?.avatar?.video_asset_id
      ? mediaUrls[activeScene.avatar.video_asset_id]
      : null);

  const activeAudioUrl = activeScene?.speech?.audio_asset_id
    ? mediaUrls[activeScene.speech.audio_asset_id]
    : null;

  const togglePlayback = () => {
    if (activeVideoUrl && videoRef.current) {
      if (videoRef.current.paused) {
        videoRef.current.play().then(() => setIsPlaying(true)).catch(() => {});
      } else {
        videoRef.current.pause();
        setIsPlaying(false);
      }
    } else if (activeAudioUrl && audioRef.current) {
      if (audioRef.current.paused) {
        audioRef.current.play().then(() => setIsPlaying(true)).catch(() => {});
      } else {
        audioRef.current.pause();
        setIsPlaying(false);
      }
    } else {
      setIsPlaying(!isPlaying);
    }
  };

  // --------------------------------------------------------------------------
  // 7A. ADVANCED TIMELINE EDITING & SNAPPING (PHASE 43)
  // --------------------------------------------------------------------------
  const handleZoomChange = useCallback((newZoom: number) => {
    const clamped = Math.max(MIN_TIMELINE_ZOOM, Math.min(MAX_TIMELINE_ZOOM, Math.round(newZoom * 10) / 10));
    const container = timelineScrollContainerRef.current;
    if (container && container.clientWidth > 0) {
      const oldZoom = timelineZoom;
      const centerPx = container.scrollLeft + container.clientWidth / 2;
      const ratio = clamped / oldZoom;
      const newScrollLeft = centerPx * ratio - container.clientWidth / 2;
      setTimelineZoom(clamped);
      requestAnimationFrame(() => {
        if (container) {
          container.scrollLeft = Math.max(0, newScrollLeft);
        }
      });
    } else {
      setTimelineZoom(clamped);
    }
  }, [timelineZoom]);

  const handleSplitSelectedClip = useCallback(async () => {
    if (!activeScene) return;

    // 1. Check if a visual layer is selected in activeScene
    const activeRes = getSelectedVisualLayer(
      scenes,
      activeSceneIndex,
      selectedMediaLayerId,
      selectedTextLayerId,
      selectedElementLayerId
    );

    if (activeRes && activeRes.layer) {
      const layer = activeRes.layer;
      if (layer.locked === true) {
        showNotification("info", "Cannot split a locked layer.");
        return;
      }

      const sceneDuration = activeScene.duration || 5.0;
      const startTime = Math.max(0, Number(layer.start_time ?? 0));
      const endTime = Math.max(startTime + MIN_CLIP_DURATION, Number(layer.end_time ?? sceneDuration));
      const splitTime = playbackTime;

      if (!canSplitClip(startTime, endTime, splitTime, MIN_CLIP_DURATION, layer.locked)) {
        showNotification("info", `Cannot split "${layer.name || "layer"}" at ${splitTime.toFixed(1)}s (must be between ${startTime.toFixed(1)}s and ${endTime.toFixed(1)}s with min ${MIN_CLIP_DURATION}s duration).`);
        return;
      }

      const newId = `${activeRes.kind}_${Date.now()}`;
      const splitResult = splitClip(layer, splitTime, newId, MIN_CLIP_DURATION);
      if (!splitResult) return;

      const currentLayers = activeScene.layers || [];
      const nextLayers: any[] = [];
      for (const l of currentLayers) {
        if (l.id === layer.id) {
          nextLayers.push(splitResult.firstClip);
          nextLayers.push(splitResult.secondClip);
        } else {
          nextLayers.push(l);
        }
      }

      const nextScenes = scenes.map((s, idx) =>
        idx === activeSceneIndex ? { ...s, layers: nextLayers } : s
      );

      setScenes(nextScenes);
      if (activeRes.kind === "media") selectMediaLayer(newId);
      else if (activeRes.kind === "text") selectTextLayer(newId);
      else selectElementLayer(newId);

      commitStudioHistory("Split Clip", nextScenes, {
        selectedMediaLayerId: activeRes.kind === "media" ? newId : null,
        selectedTextLayerId: activeRes.kind === "text" ? newId : null,
        selectedElementLayerId: activeRes.kind === "element" ? newId : null,
      });

      await handleSave(nextScenes);
      showNotification("success", `Split "${layer.name || "layer"}" at ${splitTime.toFixed(1)}s.`);
      return;
    }

    // 2. Check if an audio track is selected
    if (activeAudioTrackId) {
      const track = audioTracks.find((t) => t.id === activeAudioTrackId);
      if (track) {
        const globalPlayhead = activeSceneOffset + playbackTime;
        const startTime = Math.max(0, Number(track.start_time ?? 0));
        const rawDuration = typeof track.duration === "number" && track.duration > 0
          ? track.duration
          : Math.max(MIN_CLIP_DURATION, totalDuration - startTime);
        const endTime = Math.max(startTime + MIN_CLIP_DURATION, startTime + rawDuration);

        if (!canSplitClip(startTime, endTime, globalPlayhead, MIN_CLIP_DURATION, false)) {
          showNotification("info", `Cannot split audio track "${track.name}" at ${globalPlayhead.toFixed(1)}s.`);
          return;
        }

        const newTrackId = `audio_${Date.now()}`;
        const splitResult = splitClip(track, globalPlayhead, newTrackId, MIN_CLIP_DURATION);
        if (!splitResult) return;

        const nextTracks: AudioTrackItem[] = [];
        for (const t of audioTracks) {
          if (t.id === track.id) {
            nextTracks.push(splitResult.firstClip as AudioTrackItem);
            nextTracks.push(splitResult.secondClip as AudioTrackItem);
          } else {
            nextTracks.push(t);
          }
        }

        setAudioTracks(nextTracks);
        setActiveAudioTrackId(newTrackId);

        commitStudioHistory("Split Audio Track", scenes, nextTracks);
        await handleSave(scenes, nextTracks);
        showNotification("success", `Split audio track "${track.name}" at ${globalPlayhead.toFixed(1)}s.`);
        return;
      }
    }

    showNotification("info", "Select a clip to split at the current playhead.");
  }, [
    activeScene,
    scenes,
    activeSceneIndex,
    selectedMediaLayerId,
    selectedTextLayerId,
    selectedElementLayerId,
    playbackTime,
    activeAudioTrackId,
    audioTracks,
    activeSceneOffset,
    totalDuration,
    selectMediaLayer,
    selectTextLayer,
    selectElementLayer,
    commitStudioHistory,
    handleSave,
    showNotification,
  ]);

  // --------------------------------------------------------------------------
  // 7A-2. PHASE 44: MULTI-LAYER GROUP OPERATIONS & ACTIONS
  // --------------------------------------------------------------------------
  const handleGroupAlign = useCallback(
    async (alignment: "left" | "center" | "right" | "top" | "middle" | "bottom") => {
      if (selectedLayerIds.length < 2 || !activeScene?.layers) return;
      const selectedLayers = (activeScene.layers as VisualLayer[]).filter((l) =>
        selectedLayerIds.includes(l.id)
      );
      const alignMap = calculateGroupAlignment(selectedLayers, alignment);
      if (alignMap.size === 0) return;

      const nextLayers = activeScene.layers.map((l: any) => {
        const update = alignMap.get(l.id);
        return update ? { ...l, transform: { ...(l.transform || {}), ...update } } : l;
      });
      const nextScenes = scenes.map((s, idx) =>
        idx === activeSceneIndex ? { ...s, layers: nextLayers } : s
      );
      setScenes(nextScenes);
      commitStudioHistory(`Align Group ${alignment}`, nextScenes, { selectedLayerIds });
      await handleSave(nextScenes);
      showNotification("info", `Aligned ${selectedLayerIds.length} layers to ${alignment}.`);
    },
    [selectedLayerIds, activeScene, scenes, activeSceneIndex, commitStudioHistory, handleSave, showNotification]
  );

  const handleGroupDistribute = useCallback(
    async (axis: "horizontal" | "vertical") => {
      if (selectedLayerIds.length < 3 || !activeScene?.layers) return;
      const selectedLayers = (activeScene.layers as VisualLayer[]).filter((l) =>
        selectedLayerIds.includes(l.id)
      );
      const distMap = calculateGroupDistribution(selectedLayers, axis);
      if (distMap.size === 0) return;

      const nextLayers = activeScene.layers.map((l: any) => {
        const update = distMap.get(l.id);
        return update ? { ...l, transform: { ...(l.transform || {}), ...update } } : l;
      });
      const nextScenes = scenes.map((s, idx) =>
        idx === activeSceneIndex ? { ...s, layers: nextLayers } : s
      );
      setScenes(nextScenes);
      commitStudioHistory(`Distribute Group ${axis}`, nextScenes, { selectedLayerIds });
      await handleSave(nextScenes);
      showNotification("info", `Distributed ${selectedLayerIds.length} layers evenly.`);
    },
    [selectedLayerIds, activeScene, scenes, activeSceneIndex, commitStudioHistory, handleSave, showNotification]
  );

  const handleGroupDuplicate = useCallback(async () => {
    if (selectedLayerIds.length === 0 || !activeScene?.layers) return;
    const currentLayers = activeScene.layers as VisualLayer[];
    const { nextLayers, newIds } = groupDuplicateLayers(currentLayers, selectedLayerIds);
    if (newIds.length === 0) return;

    const nextScenes = scenes.map((s, idx) =>
      idx === activeSceneIndex ? { ...s, layers: nextLayers } : s
    );
    setScenes(nextScenes);
    setSelectedLayerIds(newIds);
    syncSingleSelectionFromIds(newIds, nextScenes);
    commitStudioHistory("Duplicate Group", nextScenes, { selectedLayerIds: newIds });
    await handleSave(nextScenes);
    showNotification("success", `Duplicated ${newIds.length} layers.`);
  }, [selectedLayerIds, activeScene, scenes, activeSceneIndex, syncSingleSelectionFromIds, commitStudioHistory, handleSave, showNotification]);

  const handleGroupDelete = useCallback(async () => {
    if (selectedLayerIds.length === 0 || !activeScene?.layers) return;
    const currentLayers = activeScene.layers as VisualLayer[];
    const nextLayers = groupDeleteLayers(currentLayers, selectedLayerIds);

    const nextScenes = scenes.map((s, idx) =>
      idx === activeSceneIndex ? { ...s, layers: nextLayers } : s
    );
    setScenes(nextScenes);
    clearVisualSelection();
    commitStudioHistory("Delete Group", nextScenes, { selectedLayerIds: [] });
    await handleSave(nextScenes);
    showNotification("info", `Deleted ${selectedLayerIds.length} layers.`);
  }, [selectedLayerIds, activeScene, scenes, activeSceneIndex, clearVisualSelection, commitStudioHistory, handleSave, showNotification]);

  const handleGroupLock = useCallback(async () => {
    if (selectedLayerIds.length === 0 || !activeScene?.layers) return;
    const currentLayers = activeScene.layers as VisualLayer[];
    const allLocked = currentLayers
      .filter((l) => selectedLayerIds.includes(l.id))
      .every((l) => l.locked === true);
    const nextLayers = groupSetLock(currentLayers, selectedLayerIds, !allLocked);

    const nextScenes = scenes.map((s, idx) =>
      idx === activeSceneIndex ? { ...s, layers: nextLayers } : s
    );
    setScenes(nextScenes);
    commitStudioHistory(allLocked ? "Unlock Group" : "Lock Group", nextScenes, { selectedLayerIds });
    await handleSave(nextScenes);
    showNotification("info", `${allLocked ? "Unlocked" : "Locked"} ${selectedLayerIds.length} layers.`);
  }, [selectedLayerIds, activeScene, scenes, activeSceneIndex, commitStudioHistory, handleSave, showNotification]);

  const handleGroupVisibility = useCallback(async () => {
    if (selectedLayerIds.length === 0 || !activeScene?.layers) return;
    const currentLayers = activeScene.layers as VisualLayer[];
    const allVisible = currentLayers
      .filter((l) => selectedLayerIds.includes(l.id))
      .every((l) => l.enabled !== false);
    const nextLayers = groupSetVisibility(currentLayers, selectedLayerIds, !allVisible);

    const nextScenes = scenes.map((s, idx) =>
      idx === activeSceneIndex ? { ...s, layers: nextLayers } : s
    );
    setScenes(nextScenes);
    commitStudioHistory(allVisible ? "Hide Group" : "Show Group", nextScenes, { selectedLayerIds });
    await handleSave(nextScenes);
    showNotification("info", `${allVisible ? "Hidden" : "Shown"} ${selectedLayerIds.length} layers.`);
  }, [selectedLayerIds, activeScene, scenes, activeSceneIndex, commitStudioHistory, handleSave, showNotification]);

  const handleGroupZOrder = useCallback(
    async (direction: "forward" | "backward" | "front" | "back") => {
      if (selectedLayerIds.length === 0 || !activeScene?.layers) return;
      const currentLayers = activeScene.layers as VisualLayer[];
      const nextLayers = groupMoveZOrder(currentLayers, selectedLayerIds, direction);

      const nextScenes = scenes.map((s, idx) =>
        idx === activeSceneIndex ? { ...s, layers: nextLayers } : s
      );
      setScenes(nextScenes);
      commitStudioHistory(`Group Z-Order ${direction}`, nextScenes, { selectedLayerIds });
      await handleSave(nextScenes);
      showNotification("info", `Moved selected layers ${direction}.`);
    },
    [selectedLayerIds, activeScene, scenes, activeSceneIndex, commitStudioHistory, handleSave, showNotification]
  );

  const handleBatchUpdateOpacity = useCallback(
    async (opacity: number) => {
      if (selectedLayerIds.length === 0 || !activeScene?.layers) return;
      const currentLayers = activeScene.layers as VisualLayer[];
      const nextLayers = batchSetOpacity(currentLayers, selectedLayerIds, opacity);
      const nextScenes = scenes.map((s, idx) =>
        idx === activeSceneIndex ? { ...s, layers: nextLayers } : s
      );
      setScenes(nextScenes);
      commitStudioHistory(`Batch Opacity ${Math.round(opacity * 100)}%`, nextScenes, { selectedLayerIds });
      await handleSave(nextScenes);
      showNotification("info", `Updated opacity for ${selectedLayerIds.length} layers.`);
    },
    [selectedLayerIds, activeScene, scenes, activeSceneIndex, commitStudioHistory, handleSave, showNotification]
  );

  const handleBatchUpdateVisibility = useCallback(
    async (enabled: boolean) => {
      if (selectedLayerIds.length === 0 || !activeScene?.layers) return;
      const currentLayers = activeScene.layers as VisualLayer[];
      const nextLayers = batchSetVisibility(currentLayers, selectedLayerIds, enabled);
      const nextScenes = scenes.map((s, idx) =>
        idx === activeSceneIndex ? { ...s, layers: nextLayers } : s
      );
      setScenes(nextScenes);
      commitStudioHistory(enabled ? "Show Group" : "Hide Group", nextScenes, { selectedLayerIds });
      await handleSave(nextScenes);
      showNotification("info", `${enabled ? "Shown" : "Hidden"} ${selectedLayerIds.length} layers.`);
    },
    [selectedLayerIds, activeScene, scenes, activeSceneIndex, commitStudioHistory, handleSave, showNotification]
  );

  const handleBatchUpdateLock = useCallback(
    async (locked: boolean) => {
      if (selectedLayerIds.length === 0 || !activeScene?.layers) return;
      const currentLayers = activeScene.layers as VisualLayer[];
      const nextLayers = batchSetLock(currentLayers, selectedLayerIds, locked);
      const nextScenes = scenes.map((s, idx) =>
        idx === activeSceneIndex ? { ...s, layers: nextLayers } : s
      );
      setScenes(nextScenes);
      commitStudioHistory(locked ? "Lock Group" : "Unlock Group", nextScenes, { selectedLayerIds });
      await handleSave(nextScenes);
      showNotification("info", `${locked ? "Locked" : "Unlocked"} ${selectedLayerIds.length} layers.`);
    },
    [selectedLayerIds, activeScene, scenes, activeSceneIndex, commitStudioHistory, handleSave, showNotification]
  );

  const handleBatchApplyTransformDelta = useCallback(
    async (delta: TransformBatchDelta) => {
      if (selectedLayerIds.length === 0 || !activeScene?.layers) return;
      const currentLayers = activeScene.layers as VisualLayer[];
      const nextLayers = batchApplyTransformDelta(currentLayers, selectedLayerIds, delta);
      const nextScenes = scenes.map((s, idx) =>
        idx === activeSceneIndex ? { ...s, layers: nextLayers } : s
      );
      setScenes(nextScenes);
      const label =
        delta.dx !== undefined || delta.dy !== undefined
          ? "Batch Nudge Position"
          : delta.scaleMult !== undefined
          ? "Batch Scale"
          : "Batch Rotate";
      commitStudioHistory(label, nextScenes, { selectedLayerIds });
      await handleSave(nextScenes);
    },
    [selectedLayerIds, activeScene, scenes, activeSceneIndex, commitStudioHistory, handleSave]
  );

  // Computed multi-selection bounds for canvas
  const selectedVisualLayersForBounds = useMemo(() => {
    if (selectedLayerIds.length <= 1 || !activeVisualLayers) return [];
    return activeVisualLayers.filter((l: any) => selectedLayerIds.includes(l.id));
  }, [selectedLayerIds, activeVisualLayers]);

  const groupBounds = useMemo(() => {
    if (selectedVisualLayersForBounds.length <= 1) return null;
    return calculateGroupBounds(selectedVisualLayersForBounds);
  }, [selectedVisualLayersForBounds]);

  // Group drag on canvas
  const handleGroupPointerDown = useCallback((e: React.PointerEvent) => {
    if (selectedLayerIds.length <= 1) return;
    e.stopPropagation();
    e.preventDefault();
    try {
      (e.target as HTMLElement).setPointerCapture(e.pointerId);
    } catch {}

    const currentLayers = (activeScene?.layers || []) as VisualLayer[];
    groupDragRef.current = {
      active: true,
      startX: e.clientX,
      startY: e.clientY,
      initialLayers: JSON.parse(JSON.stringify(currentLayers)),
    };
  }, [selectedLayerIds, activeScene]);

  const handleGroupPointerMove = useCallback((e: React.PointerEvent) => {
    const session = groupDragRef.current;
    if (!session || !session.active || !canvasViewportRef.current) return;

    const rect = canvasViewportRef.current.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) return;

    const deltaX = (e.clientX - session.startX) / rect.width;
    const deltaY = (e.clientY - session.startY) / rect.height;

    const initialSelectedLayers = session.initialLayers.filter((l) => selectedLayerIds.includes(l.id));
    const allCurrentLayers = (activeScene?.layers || []) as VisualLayer[];

    const res = calculateGroupMove(
      initialSelectedLayers,
      deltaX,
      deltaY,
      allCurrentLayers,
      true
    );

    const nextLayers = session.initialLayers.map((l) => {
      const moved = res.transformMap.get(l.id);
      return moved ? { ...l, transform: { ...(l.transform || {}), ...moved } } : l;
    });

    setScenes((prev) =>
      prev.map((s, idx) => (idx === activeSceneIndex ? { ...s, layers: nextLayers } : s))
    );
    setActiveSnapGuides(res.activeGuides);
  }, [selectedLayerIds, activeScene, activeSceneIndex]);

  const handleGroupPointerUp = useCallback(async (e: React.PointerEvent) => {
    const session = groupDragRef.current;
    if (!session || !session.active) return;
    groupDragRef.current = null;
    setActiveSnapGuides([]);

    try {
      (e.target as HTMLElement).releasePointerCapture(e.pointerId);
    } catch {}

    const nextScenes = scenesRef.current || scenes;
    commitStudioHistory("Move Group", nextScenes, { selectedLayerIds });
    await handleSave(nextScenes);
  }, [scenes, selectedLayerIds, commitStudioHistory, handleSave]);

  // Canvas marquee rectangular selection
  const handleCanvasPointerDown = useCallback((e: React.PointerEvent) => {
    if (e.target !== canvasViewportRef.current && !(e.target as HTMLElement).classList.contains("canvas-background-layer")) {
      return;
    }
    if (!canvasViewportRef.current) return;
    const rect = canvasViewportRef.current.getBoundingClientRect();
    const normX = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    const normY = Math.max(0, Math.min(1, (e.clientY - rect.top) / rect.height));
    const isAdditive = e.ctrlKey || e.metaKey || e.shiftKey;

    setMarqueeState({
      active: true,
      startX: normX,
      startY: normY,
      currentX: normX,
      currentY: normY,
      isAdditive,
    });
  }, []);

  const handleCanvasPointerMove = useCallback((e: React.PointerEvent) => {
    if (!marqueeState || !marqueeState.active || !canvasViewportRef.current) return;
    const rect = canvasViewportRef.current.getBoundingClientRect();
    const normX = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    const normY = Math.max(0, Math.min(1, (e.clientY - rect.top) / rect.height));

    setMarqueeState((prev) => (prev ? { ...prev, currentX: normX, currentY: normY } : null));

    const minX = Math.min(marqueeState.startX, normX);
    const maxX = Math.max(marqueeState.startX, normX);
    const minY = Math.min(marqueeState.startY, normY);
    const maxY = Math.max(marqueeState.startY, normY);

    if (maxX - minX > 0.01 || maxY - minY > 0.01) {
      const intersecting = getLayersIntersectingMarquee(activeVisualLayers, { minX, maxX, minY, maxY });
      if (marqueeState.isAdditive) {
        setSelectedLayerIds((prev) => Array.from(new Set([...prev, ...intersecting])));
      } else {
        setSelectedLayerIds(intersecting);
      }
    }
  }, [marqueeState, activeVisualLayers]);

  const handleCanvasPointerUp = useCallback(() => {
    if (marqueeState && marqueeState.active) {
      setMarqueeState(null);
      syncSingleSelectionFromIds(selectedLayerIds);
    }
  }, [marqueeState, selectedLayerIds, syncSingleSelectionFromIds]);

  // --------------------------------------------------------------------------
  // 7B. CENTRAL STUDIO KEYBOARD NAVIGATION & SHORTCUTS (PHASE 39 & PHASE 44)
  // --------------------------------------------------------------------------
  const studioClipboardRef = useRef<SerializedStudioLayer | null>(null);
  const nudgeDebounceTimerRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    const handleKeyDown = async (e: KeyboardEvent) => {
      // 1. Focus guard: If target is input/textarea/select/contenteditable, allow native typing
      if (isInputOrEditableTarget(e.target)) {
        // Exception: Escape inside an input blurs it without deselecting layer
        if (e.key === "Escape") {
          if (e.target && typeof (e.target as HTMLElement).blur === "function") {
            (e.target as HTMLElement).blur();
          }
        }
        return;
      }

      // If modal or dialog is open, do not intercept
      if (isUploadModalOpen) return;

      const isModifier = e.ctrlKey || e.metaKey;

      // Undo: Ctrl/Cmd + Z (without Shift)
      if (isModifier && !e.shiftKey && (e.key === "z" || e.key === "Z")) {
        e.preventDefault();
        await handleUndo();
        return;
      }

      // Redo: Ctrl/Cmd + Shift + Z OR Ctrl/Cmd + Y
      if (
        (isModifier && e.shiftKey && (e.key === "z" || e.key === "Z")) ||
        (isModifier && !e.shiftKey && (e.key === "y" || e.key === "Y"))
      ) {
        e.preventDefault();
        await handleRedo();
        return;
      }

      // Select All visual layers: Ctrl/Cmd + A (Phase 44)
      if (isModifier && (e.key === "a" || e.key === "A")) {
        e.preventDefault();
        selectAllLayers();
        showNotification("info", "Selected all visual layers in scene.");
        return;
      }

      // 2. Escape: Deselect active layer
      if (e.key === "Escape") {
        clearVisualSelection();
        return;
      }

      // 3. Space: Playback toggle
      if (e.key === " " || e.code === "Space") {
        e.preventDefault();
        togglePlayback();
        return;
      }

      // Split clip at playhead: S (no modifiers)
      if (!isModifier && !e.altKey && !e.shiftKey && (e.key === "s" || e.key === "S")) {
        e.preventDefault();
        await handleSplitSelectedClip();
        return;
      }

      // Multi-layer group duplicate: Ctrl/Cmd + D (Phase 44)
      if (isModifier && (e.key === "d" || e.key === "D") && selectedLayerIds.length > 1) {
        e.preventDefault();
        await handleGroupDuplicate();
        return;
      }

      // Multi-layer group delete: Delete / Backspace (Phase 44)
      if ((e.key === "Delete" || e.key === "Backspace") && selectedLayerIds.length > 1) {
        e.preventDefault();
        await handleGroupDelete();
        return;
      }

      // Multi-layer group z-order: Ctrl/Cmd + [ or ] (Phase 44)
      if (isModifier && (e.key === "]" || e.key === "[") && selectedLayerIds.length > 1) {
        e.preventDefault();
        if (e.key === "]") {
          await handleGroupZOrder(e.shiftKey ? "front" : "forward");
        } else {
          await handleGroupZOrder(e.shiftKey ? "back" : "backward");
        }
        return;
      }

      // Resolve active visual layer
      const activeRes = getSelectedVisualLayer(
        scenes,
        activeSceneIndex,
        selectedMediaLayerId,
        selectedTextLayerId,
        selectedElementLayerId
      );

      // 4. Copy: Ctrl/Cmd + C
      if (isModifier && (e.key === "c" || e.key === "C")) {
        if (!activeRes) return;
        studioClipboardRef.current = {
          layer: activeRes.layer,
          kind: activeRes.kind,
          timestamp: Date.now(),
        };
        e.preventDefault();
        showNotification("info", `Copied "${activeRes.layer.name || "layer"}" to clipboard.`);
        return;
      }

      // 5. Paste: Ctrl/Cmd + V
      if (isModifier && (e.key === "v" || e.key === "V")) {
        if (!studioClipboardRef.current || !activeScene) return;
        e.preventDefault();
        const { clonedLayer, newId } = createLayerDuplicatePayload(
          studioClipboardRef.current.layer,
          studioClipboardRef.current.kind
        );

        const currentLayers = activeScene.layers || [];
        const nextLayers = [...currentLayers, clonedLayer];
        const nextScenes = scenes.map((s, idx) =>
          idx === activeSceneIndex ? { ...s, layers: nextLayers } : s
        );

        setScenes(nextScenes);
        if (studioClipboardRef.current.kind === "media") selectMediaLayer(newId);
        else if (studioClipboardRef.current.kind === "text") selectTextLayer(newId);
        else selectElementLayer(newId);

        commitStudioHistory("Paste Layer", nextScenes, {
          selectedMediaLayerId: studioClipboardRef.current.kind === "media" ? newId : null,
          selectedTextLayerId: studioClipboardRef.current.kind === "text" ? newId : null,
          selectedElementLayerId: studioClipboardRef.current.kind === "element" ? newId : null,
        });

        await handleSave(nextScenes);
        showNotification("success", `Pasted "${clonedLayer.name}".`);
        return;
      }

      // 6. Duplicate: Ctrl/Cmd + D
      if (isModifier && (e.key === "d" || e.key === "D")) {
        if (!activeRes || !activeRes.layer.id || !activeScene) return;
        e.preventDefault();
        const { clonedLayer, newId } = createLayerDuplicatePayload(activeRes.layer, activeRes.kind);

        const currentLayers = activeScene.layers || [];
        const nextLayers = duplicateLayerWithZIndex(currentLayers, activeRes.layer.id, clonedLayer);
        const nextScenes = scenes.map((s, idx) =>
          idx === activeSceneIndex ? { ...s, layers: nextLayers } : s
        );

        setScenes(nextScenes);
        if (activeRes.kind === "media") selectMediaLayer(newId);
        else if (activeRes.kind === "text") selectTextLayer(newId);
        else selectElementLayer(newId);

        commitStudioHistory("Duplicate Layer", nextScenes, {
          selectedMediaLayerId: activeRes.kind === "media" ? newId : null,
          selectedTextLayerId: activeRes.kind === "text" ? newId : null,
          selectedElementLayerId: activeRes.kind === "element" ? newId : null,
        });

        await handleSave(nextScenes);
        showNotification("success", `Duplicated "${activeRes.layer.name || "layer"}".`);
        return;
      }

      // 7. Arrow-Key Nudging (ArrowLeft, ArrowRight, ArrowUp, ArrowDown)
      if (
        e.key === "ArrowLeft" ||
        e.key === "ArrowRight" ||
        e.key === "ArrowUp" ||
        e.key === "ArrowDown"
      ) {
        if (!activeRes || !activeRes.layer.id) return;
        // Phase 38 protection: locked layer MUST NOT be nudged
        if (activeRes.layer.locked === true) return;

        e.preventDefault();
        const newPos = calculateKeyboardNudge(activeRes.layer.transform, e.key, e.shiftKey);
        handleUpdateLayerTransform(activeRes.layer.id, newPos);

        // Debounce OCC commit to avoid flooding backend during key repeats
        if (nudgeDebounceTimerRef.current) {
          clearTimeout(nudgeDebounceTimerRef.current);
        }
        nudgeDebounceTimerRef.current = setTimeout(async () => {
          try {
            await handleCommitLayerTransform();
          } catch {
            // Error notification already handled in handleSave
          }
        }, 500);
        return;
      }

      // 8. Delete / Backspace
      if (e.key === "Delete" || e.key === "Backspace") {
        if (!activeRes || !activeRes.layer.id || !activeScene) return;
        // Phase 38 protection: locked layer MUST NOT be deleted via keyboard
        if (!canDeleteLayerViaKeyboard(activeRes.layer)) return;

        e.preventDefault();
        const layerId = activeRes.layer.id;
        const currentLayers = activeScene.layers || [];
        const updatedLayers = deleteLayerWithZIndex(currentLayers, layerId);

        // Select another remaining layer of the same kind if available
        const remainingOfSameKind = updatedLayers.filter((l: any) => {
          if (activeRes.kind === "media") return l.type === "image" || l.type === "video" || l.type === "media";
          if (activeRes.kind === "text") return l.type === "text";
          return l.type === "shape" || l.type === "sticker" || l.type === "element";
        });
        const nextSelectedId = remainingOfSameKind[0]?.id || null;

        if (activeRes.kind === "media") selectMediaLayer(nextSelectedId);
        else if (activeRes.kind === "text") selectTextLayer(nextSelectedId);
        else selectElementLayer(nextSelectedId);

        const nextScenes = scenes.map((s, idx) =>
          idx === activeSceneIndex ? { ...s, layers: updatedLayers } : s
        );
        setScenes(nextScenes);
        commitStudioHistory("Delete Layer", nextScenes, {
          selectedMediaLayerId: activeRes.kind === "media" ? nextSelectedId : null,
          selectedTextLayerId: activeRes.kind === "text" ? nextSelectedId : null,
          selectedElementLayerId: activeRes.kind === "element" ? nextSelectedId : null,
        });
        await handleSave(nextScenes);
        showNotification("info", `Deleted ${activeRes.layer.name || "layer"}.`);
        return;
      }

      // 9. Layer Stacking Shortcuts (Phase 42B)
      // Ctrl/Cmd + ] : Bring Forward
      // Ctrl/Cmd + [ : Send Backward
      // Ctrl/Cmd + Shift + ] : Bring To Front
      // Ctrl/Cmd + Shift + [ : Send To Back
      if (isModifier && (e.key === "]" || e.key === "[")) {
        if (!activeRes || !activeRes.layer.id || !activeScene) return;
        if (activeRes.layer.locked === true) return;
        e.preventDefault();

        const currentLayers = activeScene.layers || [];
        let updatedLayers: any[];
        let actionName: string;

        if (e.key === "]") {
          if (e.shiftKey) {
            actionName = "Bring Layer To Front";
            updatedLayers = bringLayerToFront(currentLayers, activeRes.layer.id);
          } else {
            actionName = "Bring Layer Forward";
            updatedLayers = bringLayerForward(currentLayers, activeRes.layer.id);
          }
        } else {
          if (e.shiftKey) {
            actionName = "Send Layer To Back";
            updatedLayers = sendLayerToBack(currentLayers, activeRes.layer.id);
          } else {
            actionName = "Send Layer Backward";
            updatedLayers = sendLayerBackward(currentLayers, activeRes.layer.id);
          }
        }

        const nextScenes = scenes.map((s, idx) =>
          idx === activeSceneIndex ? { ...s, layers: updatedLayers } : s
        );
        setScenes(nextScenes);
        commitStudioHistory(actionName, nextScenes, {
          selectedMediaLayerId: activeRes.kind === "media" ? activeRes.layer.id : null,
          selectedTextLayerId: activeRes.kind === "text" ? activeRes.layer.id : null,
          selectedElementLayerId: activeRes.kind === "element" ? activeRes.layer.id : null,
        });
        await handleSave(nextScenes);
        showNotification("info", `${actionName}: "${activeRes.layer.name || "layer"}".`);
        return;
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      if (nudgeDebounceTimerRef.current) {
        clearTimeout(nudgeDebounceTimerRef.current);
      }
    };
  }, [
    scenes,
    activeSceneIndex,
    activeScene,
    selectedMediaLayerId,
    selectedTextLayerId,
    selectedElementLayerId,
    selectedLayerIds,
    selectAllLayers,
    handleGroupDelete,
    handleGroupDuplicate,
    handleGroupZOrder,
    isUploadModalOpen,
    selectMediaLayer,
    selectTextLayer,
    selectElementLayer,
    clearVisualSelection,
    handleUpdateLayerTransform,
    handleCommitLayerTransform,
    handleSave,
    handleUndo,
    handleRedo,
    togglePlayback,
    showNotification,
  ]);

  const formatSeconds = (sec: number) => {
    const s = Math.max(0, Math.floor(sec));
    const m = Math.floor(s / 60);
    const rem = s % 60;
    return `${String(m).padStart(2, "0")}:${String(rem).padStart(2, "0")}`;
  };

  // Selected avatar & voice info
  const activeAvatarObj = useMemo(() => {
    const currentId = activeScene?.avatar?.avatar_id;
    if (!currentId) return null;
    return (
      avatars.find(
        (a) =>
          a.id === currentId ||
          a.name === currentId ||
          a.provider_reference === currentId ||
          a.name?.toLowerCase().replace(/\s+/g, "-") === currentId
      ) || null
    );
  }, [avatars, activeScene?.avatar?.avatar_id]);

  const avatarVisualUrl = useMemo(() => {
    if (!activeAvatarObj) return null;
    const activeLookId = (activeScene?.avatar as any)?.look_id;
    if (activeLookId && Array.isArray(activeAvatarObj.looks)) {
      const matchedLook = activeAvatarObj.looks.find(
        (l: any) => l.id === activeLookId || l.name === activeLookId
      );
      if (matchedLook?.preview_url) return matchedLook.preview_url;
    }
    return (
      activeAvatarObj.preview_url ||
      (activeAvatarObj as any)?.provider_metadata?.preview_url ||
      (activeAvatarObj as any)?.provider_metadata?.image_url ||
      null
    );
  }, [activeAvatarObj, (activeScene?.avatar as any)?.look_id]);

  const activeVoiceObj = voices.find((v) => v.id === activeScene?.speech?.voice_id);

  // Filtered voice catalog
  const filteredVoices = useMemo(() => {
    return voices.filter((v) => {
      const matchSearch =
        !voiceSearch ||
        v.name?.toLowerCase().includes(voiceSearch.toLowerCase()) ||
        v.language?.toLowerCase().includes(voiceSearch.toLowerCase());
      const matchLang =
        voiceLangFilter === "all" ||
        v.language?.toLowerCase().startsWith(voiceLangFilter.toLowerCase());
      return matchSearch && matchLang;
    });
  }, [voices, voiceSearch, voiceLangFilter]);

  // Filtered avatar catalog
  const filteredAvatars = useMemo(() => {
    return avatars.filter((a) => {
      return (
        !avatarSearch ||
        a.name?.toLowerCase().includes(avatarSearch.toLowerCase()) ||
        a.provider?.toLowerCase().includes(avatarSearch.toLowerCase()) ||
        a.provider_reference?.toLowerCase().includes(avatarSearch.toLowerCase())
      );
    });
  }, [avatars, avatarSearch]);

  return (
    <div
      ref={studioRootRef}
      id="vido-studio-container"
      data-testid="vido-studio-container"
      className={`w-full h-screen flex flex-col overflow-hidden select-none ${
        isLight ? "bg-slate-50 text-slate-800" : "bg-[#07090e] text-slate-200"
      }`}
    >
      {/* 1. TOP NAVIGATION BAR */}
      <header
        className={`h-14 min-h-14 px-4 flex items-center justify-between z-30 border-b ${
          isLight ? "bg-white border-slate-200 text-slate-900" : "bg-[#0a0d16] border-[#171f33] text-white"
        }`}
      >
        {/* Left: Brand Logo & Navigation */}
        <div className="flex items-center gap-4">
          {onBackToDashboard && (
            <button
              id="back-to-dashboard-btn"
              data-testid="back-to-dashboard-btn"
              onClick={onBackToDashboard}
              className="p-1.5 rounded-lg bg-[#141b2c] hover:bg-[#1c263e] text-slate-300 hover:text-white transition-colors flex items-center gap-1 text-xs cursor-pointer"
              title="Return to Home"
            >
              <ArrowLeft size={15} /> Dashboard
            </button>
          )}

          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-tr from-cyan-400 via-blue-600 to-purple-600 flex items-center justify-center text-white text-xs font-bold shadow-md">
              ▶
            </div>
            <div>
              <span className="font-extrabold text-white text-base tracking-tight">HeyZen Studio</span>
              <span className="text-[10px] text-slate-400 ml-2 hidden sm:inline">AI Scene Editor</span>
            </div>
          </div>

          <div className="h-5 w-[1px] bg-[#1a243a]"></div>

          {/* Undo / Redo / Auto-Save */}
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <button
              type="button"
              onClick={handleUndo}
              disabled={!canUndoState || saveStatus === "saving"}
              className="p-1 hover:text-white hover:bg-[#141b2c] rounded disabled:opacity-30 disabled:hover:text-slate-400 disabled:hover:bg-transparent cursor-pointer disabled:cursor-not-allowed transition-colors"
              title="Undo (Ctrl/Cmd+Z)"
              aria-label="Undo"
            >
              <RotateCcw size={14} />
            </button>
            <button
              type="button"
              onClick={handleRedo}
              disabled={!canRedoState || saveStatus === "saving"}
              className="p-1 hover:text-white hover:bg-[#141b2c] rounded disabled:opacity-30 disabled:hover:text-slate-400 disabled:hover:bg-transparent cursor-pointer disabled:cursor-not-allowed transition-colors"
              title="Redo (Ctrl/Cmd+Shift+Z, Ctrl/Cmd+Y)"
              aria-label="Redo"
            >
              <RotateCw size={14} />
            </button>
            <button
              onClick={saveStatus === "conflict" ? loadProject : () => handleSave()}
              disabled={saveStatus === "saving"}
              className={`flex items-center gap-1 text-[11px] ml-1 px-2.5 py-0.5 rounded-full border transition-all cursor-pointer ${
                saveStatus === "saving"
                  ? "text-blue-400 bg-blue-500/10 border-blue-500/30"
                  : saveStatus === "conflict"
                  ? "text-amber-400 bg-amber-500/10 border-amber-500/30 animate-pulse"
                  : saveStatus === "unsaved"
                  ? "text-slate-300 bg-slate-500/10 border-slate-500/30 hover:border-blue-400"
                  : "text-emerald-400 bg-emerald-500/10 border-emerald-500/20"
              }`}
              title={
                conflictMessage ||
                (saveStatus === "conflict"
                  ? "Click to reload latest version"
                  : `Click to save (Revision ${revision})`)
              }
            >
              {saveStatus === "saving" ? (
                <Loader2 size={11} className="animate-spin" />
              ) : saveStatus === "conflict" ? (
                <AlertTriangle size={11} />
              ) : (
                <CheckCircle2 size={11} />
              )}
              <span>
                {saveStatus === "saving"
                  ? "Saving..."
                  : saveStatus === "conflict"
                  ? "Conflict (Reload)"
                  : saveStatus === "unsaved"
                  ? "Save Changes"
                  : `Saved (r${revision})`}
              </span>
            </button>
          </div>
        </div>

        {/* Center: Project Title */}
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={projectTitle}
            onChange={(e) => {
              setProjectTitle(e.target.value);
              setSaveStatus("unsaved");
            }}
            onBlur={() => handleSave()}
            placeholder="Project Title"
            className="bg-transparent hover:bg-[#121827] focus:bg-[#121827] border border-transparent hover:border-[#1e2a44] focus:border-blue-500 rounded-lg px-2.5 py-1 text-sm font-semibold text-white focus:outline-none text-center"
          />
        </div>

        {/* Right: Aspect Ratio, Preview & Export */}
        <div className="flex items-center gap-3">
          {/* Aspect Ratio Switcher */}
          <div
            onClick={() => {
              const next = aspectRatio === "16:9" ? "9:16" : "16:9";
              setAspectRatio(next);
              setSaveStatus("unsaved");
            }}
            className="flex items-center gap-1.5 bg-[#101625] border border-[#1e2940] rounded-lg px-2.5 py-1 text-xs text-slate-300 cursor-pointer hover:border-slate-500 transition-colors"
            title="Toggle Canvas Ratio (16:9 / 9:16)"
          >
            <span className="font-medium">{aspectRatio}</span>
            <ChevronDown size={13} />
          </div>

          {/* Canvas Preview Button */}
          <button
            onClick={togglePlayback}
            className="flex items-center gap-1.5 bg-[#121828] hover:bg-[#1a233a] border border-[#212e48] px-3 py-1.5 rounded-xl text-xs font-semibold text-white transition-colors cursor-pointer"
          >
            {isPlaying ? (
              <Pause size={13} className="text-blue-400" />
            ) : (
              <Play size={13} className="text-blue-400 fill-blue-400" />
            )}
            <span>{isPlaying ? "Pause" : "Preview"}</span>
          </button>

          {/* Export / Generate Button & Render Status */}
          {renderState.downloadUrl ? (
            <div className="flex items-center gap-2">
              <button
                id="studio-generate-btn"
                data-testid="studio-generate-btn"
                onClick={handleExport}
                disabled={renderState.isRendering}
                className="bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white font-bold text-xs px-3.5 py-1.5 rounded-xl shadow-lg shadow-blue-500/25 transition-all cursor-pointer flex items-center gap-1.5 disabled:opacity-50"
                title="Generate Video (Re-render)"
              >
                <Clapperboard size={13} /> Generate Video
              </button>
              <a
                href={renderState.downloadUrl}
                download="rendered_video.mp4"
                target="_blank"
                rel="noopener noreferrer"
                className="bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs px-3.5 py-1.5 rounded-xl shadow-lg shadow-emerald-500/25 transition-all flex items-center gap-1.5 cursor-pointer"
                title="Download Rendered MP4"
              >
                <Download size={13} /> Download MP4
              </a>
            </div>
          ) : renderState.isRendering ? (
            <div className="flex items-center gap-2">
              <button
                id="studio-generate-btn"
                data-testid="studio-generate-btn"
                disabled
                className="bg-blue-600/80 text-white font-bold text-xs px-3.5 py-1.5 rounded-xl flex items-center gap-1.5 cursor-not-allowed opacity-80 shadow-md"
              >
                <Loader2 size={12} className="animate-spin" />
                <span>{renderState.stage || "Generating"} ({renderState.progressPct}%)</span>
              </button>
              <button
                onClick={handleCancelRender}
                className="text-xs text-slate-400 hover:text-red-400 p-1 rounded hover:bg-[#141b2c] cursor-pointer"
                title="Cancel Generation"
              >
                <X size={14} />
              </button>
            </div>
          ) : (
            <button
              id="studio-generate-btn"
              data-testid="studio-generate-btn"
              onClick={handleExport}
              disabled={renderState.isRendering}
              className="bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white font-bold text-xs px-4 py-1.5 rounded-xl shadow-lg shadow-blue-500/25 transition-all cursor-pointer flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed"
              title="Generate Video"
            >
              <Clapperboard size={13} /> Generate Video
            </button>
          )}

          <div className="h-5 w-[1px] bg-[#1a243a]"></div>

          <UserMenuDropdown placement="top-bar" />
        </div>
      </header>

      {/* Notification Toast Banner */}
      {notification && (
        <div
          className={`px-4 py-2 text-xs flex items-center justify-between border-b z-40 transition-all ${
            notification.type === "error"
              ? "bg-red-950/90 border-red-500/40 text-red-200"
              : notification.type === "success"
              ? "bg-emerald-950/90 border-emerald-500/40 text-emerald-200"
              : "bg-blue-950/90 border-blue-500/40 text-blue-200"
          }`}
        >
          <div className="flex items-center gap-2">
            {notification.type === "error" ? (
              <AlertTriangle size={14} className="text-red-400" />
            ) : (
              <CheckCircle2 size={14} className="text-emerald-400" />
            )}
            <span>{notification.message}</span>
          </div>
          <button
            onClick={() => setNotification(null)}
            className="p-1 text-slate-400 hover:text-white cursor-pointer"
          >
            <X size={13} />
          </button>
        </div>
      )}

      {/* 2. MAIN WORKSPACE (Left Rail + Scenes Strip + Canvas Viewport + Right Inspector) */}
      <div className="flex-1 flex overflow-hidden">
        {/* LEFT TOOL ICON RAIL */}
        <aside
          className={`w-16 min-w-16 border-r flex flex-col justify-between py-3 select-none z-20 ${
            isLight ? "bg-white border-slate-200 text-slate-700" : "bg-[#090c15] border-[#151c2d] text-white"
          }`}
        >
          <div className="flex flex-col items-center gap-1">
            {/* Quick Add Scene */}
            <button
              onClick={handleAddScene}
              className="w-11 h-11 mb-2 rounded-xl bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white flex items-center justify-center shadow-lg shadow-blue-600/30 cursor-pointer"
              title="Add New Scene"
            >
              <Plus size={18} />
            </button>

            {[
              { id: "scenes", label: "Scenes", icon: Clapperboard, tab: "scene" },
              { id: "layers", label: "Layers", icon: Layers, tab: "layers" },
              { id: "script", label: "Script", icon: FileText, tab: "scene" },
              { id: "avatar", label: "Avatar", icon: User, tab: "avatar" },
              { id: "voice", label: "Voice", icon: Mic, tab: "voice" },
              { id: "media", label: "Media", icon: ImageIcon, tab: "media" },
              { id: "text", label: "Text", icon: Type, tab: "text" },
              { id: "elements", label: "Elements", icon: Component, tab: "elements" },
              { id: "music", label: "Music", icon: Music, tab: "music" },
              { id: "transitions", label: "Transitions", icon: Shuffle, tab: "scene" },
              { id: "captions", label: "Captions", icon: Subtitles, tab: "captions" },
              { id: "brand_kit", label: "Brand Kit", icon: Palette, tab: "scene" },
            ].map((tool) => {
              const Icon = tool.icon;
              const isActive = activeLeftTool === tool.id;
              return (
                <button
                  key={tool.id}
                  onClick={() => {
                    setActiveLeftTool(tool.id);
                    setActiveTab(tool.tab as any);
                  }}
                  className={`w-11 h-10 rounded-xl flex flex-col items-center justify-center gap-0.5 text-[9px] transition-colors cursor-pointer ${
                    isActive
                      ? isLight
                        ? "bg-blue-50 text-blue-600 font-semibold"
                        : "bg-[#18233a] text-blue-400 font-semibold"
                      : isLight
                      ? "text-slate-500 hover:text-slate-900 hover:bg-slate-100"
                      : "text-slate-400 hover:text-slate-200 hover:bg-[#101625]"
                  }`}
                >
                  <Icon size={16} />
                  <span>{tool.label}</span>
                </button>
              );
            })}
          </div>

          {/* AI Credits Box */}
          <div className="p-1.5 flex flex-col items-center text-center">
            <div className={`w-full border rounded-xl p-2 mb-1 ${isLight ? "bg-slate-50 border-slate-200 text-slate-900" : "bg-[#101626] border-[#1a2640] text-white"}`}>
              <span className="text-[9px] text-slate-400 block">AI Credits</span>
              <span className={`text-[11px] font-bold ${isLight ? "text-slate-900" : "text-white"}`}>Active</span>
              <div className="w-full h-1 bg-slate-200 dark:bg-[#1c2742] rounded-full mt-1 overflow-hidden">
                <div className="w-[100%] h-full bg-gradient-to-r from-blue-500 to-emerald-500"></div>
              </div>
            </div>
            <div className="text-[9px] text-slate-400 flex items-center justify-center gap-1">
              <span>Rev {revision}</span>
            </div>
          </div>
        </aside>

        {/* SCENES THUMBNAILS STRIP */}
        <div
          id="studio-left-sidebar"
          data-testid="studio-left-sidebar"
          style={{ width: `${leftSidebarWidth}px`, minWidth: `${leftSidebarWidth}px` }}
          className={`border-r flex flex-col p-3 overflow-y-auto shrink-0 select-none ${
            isLight ? "bg-slate-50 border-slate-200" : "bg-[#0a0d16] border-[#151c2d]"
          }`}
        >
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-bold text-white uppercase tracking-wider">
              Scenes ({scenes.length})
            </span>
            <button
              onClick={handleAddScene}
              className="p-1 text-slate-400 hover:text-white hover:bg-[#151d30] rounded cursor-pointer"
              title="Add Scene"
            >
              <Plus size={14} />
            </button>
          </div>

          {isLoadingProject ? (
            <div className="flex flex-col items-center justify-center py-8 text-slate-500 gap-2">
              <Loader2 size={18} className="animate-spin" />
              <span className="text-xs">Loading scenes...</span>
            </div>
          ) : (
            <div className="space-y-2.5">
              {scenes.map((sc, idx) => {
                const isSelected = activeSceneIndex === idx;
                const hasVideo = Boolean(sc.avatar?.video_asset_id);
                const hasAudio = Boolean(sc.speech?.audio_asset_id);
                const currentAvatarId = sc.avatar?.avatar_id;
                const scAvatar = currentAvatarId
                  ? avatars.find(
                      (a) =>
                        a.id === currentAvatarId ||
                        a.name === currentAvatarId ||
                        a.provider_reference === currentAvatarId ||
                        a.name?.toLowerCase().replace(/\s+/g, "-") === currentAvatarId ||
                        (currentAvatarId === "default-presenter" &&
                          (a.name?.toLowerCase().includes("default") || a.provider_reference === "default-presenter"))
                    ) || null
                  : null;

                const scLookId = (sc.avatar as any)?.look_id;
                let scAvatarVisualUrl: string | null = null;
                if (scAvatar && currentAvatarId) {
                  if (scLookId && Array.isArray(scAvatar.looks)) {
                    const matchedLook = scAvatar.looks.find(
                      (l: any) => l.id === scLookId || l.name === scLookId
                    );
                    if (matchedLook?.preview_url) {
                      scAvatarVisualUrl = matchedLook.preview_url;
                    } else if (matchedLook?.configuration?.preview_url) {
                      scAvatarVisualUrl = matchedLook.configuration.preview_url;
                    }
                  }
                  if (!scAvatarVisualUrl) {
                    scAvatarVisualUrl =
                      scAvatar.preview_url ||
                      (scAvatar as any)?.provider_metadata?.preview_url ||
                      (scAvatar as any)?.provider_metadata?.image_url ||
                      null;
                  }
                }

                return (
                  <div
                    key={sc.id}
                    onClick={() => setActiveSceneIndex(idx)}
                    className={`group relative rounded-xl p-2 cursor-pointer transition-all border ${
                      isSelected
                        ? "bg-[#162035] border-blue-500 shadow-md shadow-blue-500/15"
                        : "bg-[#0e1322] border-[#1a233a] hover:border-[#283758]"
                    }`}
                  >
                    <div className="flex items-center justify-between text-[10px] text-slate-400 mb-1">
                      <span className="font-semibold text-slate-300">
                        {sc.title || `Scene ${String(idx + 1).padStart(2, "0")}`}
                      </span>
                      <span>{Math.round(sc.duration || 5)}s</span>
                    </div>

                    {/* Thumbnail Box */}
                    <div className="aspect-video bg-[#1a2236] rounded-lg overflow-hidden relative flex items-center justify-center border border-white/5">
                      {scAvatarVisualUrl ? (
                        <img
                          src={scAvatarVisualUrl}
                          alt={scAvatar?.name || "Avatar thumbnail"}
                          className="w-full h-full object-cover object-top"
                          onError={(e) => {
                            (e.currentTarget as HTMLElement).style.display = "none";
                            const fallback = e.currentTarget.nextElementSibling as HTMLElement;
                            if (fallback) fallback.classList.remove("hidden");
                          }}
                        />
                      ) : null}

                      <div className={`text-xl ${scAvatarVisualUrl ? "hidden" : "flex items-center justify-center"}`}>
                        {hasVideo ? "🎬" : hasAudio ? "🎙️" : "👤"}
                      </div>

                      {/* Status Badges */}
                      <div className="absolute top-1 left-1 flex gap-0.5 flex-wrap max-w-[85%]">
                        {hasVideo && (
                          <span className="text-[7px] bg-emerald-600/90 text-white px-1 py-0.2 rounded font-bold">
                            VID
                          </span>
                        )}
                        {hasAudio && (
                          <span className="text-[7px] bg-blue-600/90 text-white px-1 py-0.2 rounded font-bold">
                            TTS
                          </span>
                        )}
                        {sc.background?.type === "image" && sc.background?.asset_id && (
                          <span className="text-[7px] bg-cyan-600/90 text-white px-1 py-0.2 rounded font-bold">
                            BG:IMG
                          </span>
                        )}
                        {sc.background?.type === "video" && sc.background?.asset_id && (
                          <span className="text-[7px] bg-purple-600/90 text-white px-1 py-0.2 rounded font-bold">
                            BG:VID
                          </span>
                        )}
                      </div>

                      <span className="absolute bottom-1 right-1 text-[8px] bg-black/70 px-1 rounded text-white">
                        {formatSeconds(sc.duration || 5)}
                      </span>
                    </div>

                    {/* Scene Quick Actions (Reorder / Duplicate / Delete) */}
                    <div className="mt-1.5 flex items-center justify-between opacity-0 group-hover:opacity-100 transition-opacity">
                      <div className="flex items-center gap-1 text-slate-400">
                        {idx > 0 && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleMoveScene(idx, idx - 1);
                            }}
                            className="hover:text-white p-0.5"
                            title="Move Up"
                          >
                            <ChevronUp size={12} />
                          </button>
                        )}
                        {idx < scenes.length - 1 && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleMoveScene(idx, idx + 1);
                            }}
                            className="hover:text-white p-0.5"
                            title="Move Down"
                          >
                            <ChevronDown size={12} />
                          </button>
                        )}
                      </div>

                      <div className="flex items-center gap-1 text-slate-400">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDuplicateScene(idx);
                          }}
                          className="hover:text-white p-0.5"
                          title="Duplicate Scene"
                        >
                          <Copy size={11} />
                        </button>
                        {scenes.length > 1 && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDeleteScene(idx);
                            }}
                            className="hover:text-red-400 p-0.5"
                            title="Delete Scene"
                          >
                            <Trash2 size={11} />
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* DRAGGABLE RESIZE HANDLE: LEFT SIDEBAR <-> CANVAS */}
        <div
          id="resize-handle-left-sidebar"
          data-testid="resize-handle-left-sidebar"
          onPointerDown={handleLeftResizeStart}
          className="w-2.5 -ml-1 -mr-1 z-30 cursor-col-resize flex items-center justify-center group bg-[#090d18] border-l border-r border-[#1a233a] hover:bg-blue-600/30 active:bg-blue-500/50 transition-colors select-none shrink-0"
          title="Drag to resize sidebar"
        >
          <div className="w-[2px] h-10 bg-[#25324e] group-hover:bg-blue-400 group-active:bg-white rounded-full transition-colors" />
        </div>

        {/* CENTER VIDEO CANVAS VIEWPORT & PLAYER */}
        <div className="flex-1 bg-[#06080d] flex flex-col items-center justify-center p-6 relative overflow-hidden">
          {/* Main Video Viewport Canvas */}
          <div
            ref={canvasViewportRef}
            onClick={() => {
              if (!marqueeState?.active) {
                clearVisualSelection();
              }
            }}
            onPointerDown={handleCanvasPointerDown}
            onPointerMove={handleCanvasPointerMove}
            onPointerUp={handleCanvasPointerUp}
            className={`relative w-full ${
              aspectRatio === "9:16"
                ? "max-w-xs aspect-[9/16]"
                : aspectRatio === "1:1"
                ? "max-w-md aspect-square"
                : "max-w-3xl aspect-video"
            } bg-[#0b0e18] rounded-2xl border border-[#1f2a44] shadow-2xl overflow-hidden flex flex-col items-center justify-center transition-all`}
          >
            {/* Background Studio Color / Style / Image / Video */}
            {activeScene?.background?.type === "image" &&
            activeScene.background.asset_id &&
            mediaUrls[activeScene.background.asset_id] ? (
              <img
                src={mediaUrls[activeScene.background.asset_id]}
                alt="Scene Background"
                className="canvas-background-layer absolute inset-0 w-full h-full object-contain pointer-events-auto"
              />
            ) : activeScene?.background?.type === "video" &&
              activeScene.background.asset_id &&
              mediaUrls[activeScene.background.asset_id] ? (
              <video
                src={mediaUrls[activeScene.background.asset_id]}
                className="canvas-background-layer absolute inset-0 w-full h-full object-cover pointer-events-auto"
                autoPlay
                loop
                muted
                playsInline
              />
            ) : (
              <div
                className="canvas-background-layer absolute inset-0 pointer-events-auto"
                style={{
                  backgroundColor: activeScene?.background?.value || "#0F172A",
                }}
              ></div>
            )}

            {/* Transient Magnetic Alignment Guides (Phase 42A) */}
            {activeSnapGuides.map((guide, idx) => (
              <div
                key={`snap-guide-${guide.type}-${idx}`}
                className={`absolute pointer-events-none z-50 transition-opacity duration-75 ${
                  guide.type === "vertical"
                    ? "top-0 bottom-0 w-[1.5px] bg-cyan-400 shadow-[0_0_8px_rgba(34,211,238,0.9)]"
                    : "left-0 right-0 h-[1.5px] bg-cyan-400 shadow-[0_0_8px_rgba(34,211,238,0.9)]"
                }`}
                style={
                  guide.type === "vertical"
                    ? { left: `${Math.max(0, Math.min(100, guide.position * 100))}%` }
                    : { top: `${Math.max(0, Math.min(100, guide.position * 100))}%` }
                }
              >
                {guide.label && (
                  <span
                    className={`absolute text-[9px] font-mono px-1 py-0.5 rounded bg-cyan-950/90 text-cyan-300 border border-cyan-500/50 shadow whitespace-nowrap ${
                      guide.type === "vertical"
                        ? "top-2 left-1.5"
                        : "left-2 -top-4"
                    }`}
                  >
                    {guide.label}
                  </span>
                )}
              </div>
            ))}

            {/* REAL MEDIA / AVATAR RENDERER */}
            {activeVideoUrl ? (
              <video
                ref={videoRef}
                src={activeVideoUrl}
                className="relative z-10 w-full h-full object-contain"
                playsInline
                onTimeUpdate={(e) => setPlaybackTime(e.currentTarget.currentTime)}
                onEnded={() => setIsPlaying(false)}
              />
            ) : (
              <div className="relative z-10 w-full h-full flex flex-col items-center justify-end overflow-hidden pointer-events-none select-none">
                {/* Audio element if audio exists */}
                {activeAudioUrl && (
                  <audio
                    ref={audioRef}
                    src={activeAudioUrl}
                    onTimeUpdate={(e) => setPlaybackTime(e.currentTarget.currentTime)}
                    onEnded={() => setIsPlaying(false)}
                  />
                )}

                {/* Avatar Visual Presenter (Framing Mode: Circle PIP, Close-Up, or Half-Body) */}
                {activeScene?.avatar?.view_mode === "circle" ? (
                  <div className="absolute bottom-14 right-10 w-44 h-44 md:w-52 md:h-52 rounded-full overflow-hidden border-4 border-blue-500/60 shadow-2xl shadow-blue-500/25 bg-[#0d1322] flex items-center justify-center pointer-events-auto transition-all">
                    {avatarVisualUrl ? (
                      <img
                        src={avatarVisualUrl}
                        alt={activeAvatarObj?.name || "Avatar"}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="w-full h-full bg-gradient-to-t from-blue-900/40 to-purple-900/40 flex flex-col items-center justify-center">
                        <span className="text-6xl drop-shadow-md">
                          {activeScene?.speech?.audio_asset_id ? "🎙️" : "👤"}
                        </span>
                      </div>
                    )}
                  </div>
                ) : activeScene?.avatar?.view_mode === "close_up" ? (
                  <div className="h-[88%] aspect-[3/4] max-h-[92%] rounded-2xl overflow-hidden shadow-2xl border border-white/10 bg-[#0d1322]/80 flex items-center justify-center relative pointer-events-auto transition-all mb-4">
                    {avatarVisualUrl ? (
                      <img
                        src={avatarVisualUrl}
                        alt={activeAvatarObj?.name || "Avatar"}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="w-full h-full bg-gradient-to-t from-blue-900/40 to-purple-900/40 flex flex-col items-center justify-center">
                        <span className="text-6xl drop-shadow-md">
                          {activeScene?.speech?.audio_asset_id ? "🎙️" : "👤"}
                        </span>
                      </div>
                    )}
                  </div>
                ) : (
                  /* Standard Half-Body Framing (Default) */
                  <div className="h-[92%] aspect-[3/4] max-h-[95%] rounded-t-2xl overflow-hidden shadow-2xl border-t border-x border-white/10 bg-[#0d1322]/80 flex items-center justify-center relative pointer-events-auto transition-all">
                    {avatarVisualUrl ? (
                      <img
                        src={avatarVisualUrl}
                        alt={activeAvatarObj?.name || "Avatar"}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="w-full h-full bg-gradient-to-t from-blue-900/40 to-purple-900/40 flex flex-col items-center justify-center">
                        <span className="text-6xl drop-shadow-md">
                          {activeScene?.speech?.audio_asset_id ? "🎙️" : "👤"}
                        </span>
                      </div>
                    )}
                  </div>
                )}

                {/* Presenter Name Badge Overlay */}
                {activeAvatarObj && (
                  <div className="absolute top-4 left-4 z-20 flex items-center gap-1.5 bg-black/75 backdrop-blur-md px-3 py-1 rounded-full border border-white/15 shadow-md">
                    <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
                    <span className="text-[11px] font-semibold text-slate-200">
                      {activeAvatarObj.name}
                    </span>
                    <span className="text-[8px] uppercase px-1.5 py-0.2 rounded bg-blue-600/70 text-blue-100 font-bold">
                      {activeAvatarObj.provider || "wav2lip"}
                    </span>
                  </div>
                )}

                {/* Subtitle / Script Text Preview */}
                {activeScene?.speech?.script && (
                  <div className="absolute bottom-4 z-20 max-w-lg mx-auto bg-black/75 backdrop-blur-md border border-white/15 px-4 py-2 rounded-xl text-center shadow-xl">
                    <p className="text-xs text-slate-200 line-clamp-2 italic">
                      "{activeScene.speech.script}"
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* Active Visual Layers on Canvas Viewport (Phase 42B Unified Cross-Type Stacking) */}
            {activeVisualLayers.map((layer: any) => {
              const zIndex = 20 + (typeof layer.z_index === "number" ? layer.z_index : 0);
              const c = layer.content || {};
              const t = layer.transform || {};
              const posX = t.x ?? 0.5;
              const posY = t.y ?? 0.5;
              const scale = t.scale ?? 1.0;
              const rotation = t.rotation ?? 0.0;
              const opacity = c.opacity ?? 1.0;

              // MEDIA LAYER (Image or Video)
              if (layer.type === "image" || layer.type === "video" || layer.type === "media") {
                const isSelected =
                  selectedLayerIds.length > 0
                    ? selectedLayerIds.includes(layer.id)
                    : selectedMediaLayerId === layer.id;
                const isSingleSelectedOnly = selectedLayerIds.length <= 1 && isSelected;
                const isVideo = layer.type === "video" || c.media_type === "video";
                const assetId = c.asset_id || layer.asset_id;
                const mediaSrc = assetId ? assetUrls[assetId] : null;

                return (
                  <div
                    key={layer.id}
                    onClick={(e) => {
                      e.stopPropagation();
                      const isAdditive = e.ctrlKey || e.metaKey || e.shiftKey;
                      selectMediaLayer(layer.id, isAdditive);
                      setActiveLeftTool("media");
                      setActiveTab("media");
                    }}
                    style={{
                      left: `${posX * 100}%`,
                      top: `${posY * 100}%`,
                      transform: `translate(-50%, -50%) rotate(${rotation}deg)`,
                      opacity: opacity,
                      width: `${Math.max(4, 40 * scale)}%`,
                      zIndex: zIndex,
                    }}
                    className={`absolute cursor-pointer select-none transition-shadow rounded-lg ${
                      isSelected
                        ? "shadow-2xl ring-2 ring-blue-500/80"
                        : "hover:ring-1 hover:ring-white/40 shadow-md"
                    }`}
                    title={`Click to edit ${isVideo ? "video" : "image"} layer (z-index: ${layer.z_index ?? 0})`}
                  >
                    {isVideo ? (
                      <video
                        ref={(el) => {
                          mediaVideoRefs.current[layer.id] = el;
                        }}
                        src={mediaSrc || undefined}
                        muted
                        playsInline
                        className="w-full h-auto object-contain pointer-events-none rounded-lg"
                      />
                    ) : mediaSrc ? (
                      <img
                        src={mediaSrc}
                        alt={layer.name || "Media Layer"}
                        className="w-full h-auto object-contain pointer-events-none rounded-lg"
                      />
                    ) : (
                      <div className="w-full aspect-video bg-blue-950/60 border border-blue-500/30 flex items-center justify-center text-slate-300 text-xs rounded-lg p-3">
                        <ImageIcon size={18} className="mr-1.5 text-blue-400" />
                        <span>{layer.name || "Image Layer"}</span>
                      </div>
                    )}

                    {/* DIRECT MANIPULATION GIZMO (Single selection only) */}
                    {isSingleSelectedOnly && (
                      <CanvasTransformGizmo
                        layerId={layer.id}
                        transform={{ x: posX, y: posY, scale, rotation }}
                        canvasRef={canvasViewportRef}
                        onTransformChange={(changes) => handleUpdateLayerTransform(layer.id, changes)}
                        onTransformCommit={handleCommitLayerTransform}
                        locked={layer.locked === true}
                        layerBounds={getLayerEffectiveBounds(layer)}
                        neighborLayers={getNeighborLayers(layer.id)}
                        onSnapGuidesChange={setActiveSnapGuides}
                      />
                    )}
                  </div>
                );
              }

              // TEXT LAYER
              if (layer.type === "text") {
                const styleObj = c.style || {};
                const fontSize = c.font_size || styleObj.fontSize || 48;
                const fontWeight = (c.font_weight || styleObj.fontWeight || "bold") === "bold" ? "bold" : "normal";
                const color = c.color || styleObj.color || "#FFFFFF";
                const bgColor = c.background_color || styleObj.backgroundColor || "#000000";
                const bgOpacity = c.background_opacity ?? styleObj.backgroundOpacity ?? 0.0;
                const alignment = c.alignment || styleObj.textAlign || "center";
                const isSelected =
                  selectedLayerIds.length > 0
                    ? selectedLayerIds.includes(layer.id)
                    : selectedTextLayerId === layer.id;
                const isSingleSelectedOnly = selectedLayerIds.length <= 1 && isSelected;

                return (
                  <div
                    key={layer.id}
                    onClick={(e) => {
                      e.stopPropagation();
                      const isAdditive = e.ctrlKey || e.metaKey || e.shiftKey;
                      selectTextLayer(layer.id, isAdditive);
                      setActiveLeftTool("text");
                      setActiveTab("text");
                    }}
                    style={{
                      left: `${posX * 100}%`,
                      top: `${posY * 100}%`,
                      transform: `translate(-50%, -50%) rotate(${rotation}deg)`,
                      fontFamily: c.font_family || styleObj.fontFamily || "Arial",
                      fontSize: `${Math.max(14, Math.round(fontSize * 0.75 * scale))}px`,
                      fontWeight: fontWeight,
                      color: color,
                      backgroundColor:
                        bgOpacity > 0
                          ? `${bgColor}${Math.round(bgOpacity * 255).toString(16).padStart(2, "0")}`
                          : "transparent",
                      opacity: opacity,
                      textAlign: alignment as any,
                      zIndex: zIndex,
                    }}
                    className={`absolute px-3.5 py-1.5 rounded-lg max-w-[85%] transition-all duration-75 cursor-pointer select-none ${
                      isSelected
                        ? "shadow-lg ring-2 ring-blue-500/80"
                        : "hover:ring-1 hover:ring-white/40"
                    }`}
                    title={`Click to edit text overlay (z-index: ${layer.z_index ?? 0})`}
                  >
                    {c.text || layer.name || "Text"}

                    {/* DIRECT MANIPULATION GIZMO (Single selection only) */}
                    {isSingleSelectedOnly && (
                      <CanvasTransformGizmo
                        layerId={layer.id}
                        transform={{ x: posX, y: posY, scale, rotation }}
                        canvasRef={canvasViewportRef}
                        onTransformChange={(changes) => handleUpdateLayerTransform(layer.id, changes)}
                        onTransformCommit={handleCommitLayerTransform}
                        locked={layer.locked === true}
                        layerBounds={getLayerEffectiveBounds(layer)}
                        neighborLayers={getNeighborLayers(layer.id)}
                        onSnapGuidesChange={setActiveSnapGuides}
                      />
                    )}
                  </div>
                );
              }

              // ELEMENT LAYER (Shape, Sticker, Element)
              const isSelected =
                selectedLayerIds.length > 0
                  ? selectedLayerIds.includes(layer.id)
                  : selectedElementLayerId === layer.id;
              const isSingleSelectedOnly = selectedLayerIds.length <= 1 && isSelected;
              const isShape = layer.type === "shape";

              if (isShape) {
                const shapeType = c.shape_type || "rectangle";
                const fill = c.fill || "#3B82F6";
                const borderColor = c.border_color || "#FFFFFF";
                const borderWidth = c.border_width ?? 0;
                const borderRadius = c.border_radius ?? (shapeType === "rounded_rectangle" ? 16 : 0);
                const widthPct = Math.max(2, (c.width ?? 0.35) * 100 * scale);
                const heightPct = Math.max(2, (c.height ?? 0.2) * 100 * scale);

                return (
                  <div
                    key={layer.id}
                    onClick={(e) => {
                      e.stopPropagation();
                      const isAdditive = e.ctrlKey || e.metaKey || e.shiftKey;
                      selectElementLayer(layer.id, isAdditive);
                      setActiveLeftTool("elements");
                      setActiveTab("elements");
                    }}
                    style={{
                      left: `${posX * 100}%`,
                      top: `${posY * 100}%`,
                      transform: `translate(-50%, -50%) rotate(${rotation}deg)`,
                      width: `${widthPct}%`,
                      height: `${heightPct}%`,
                      opacity: opacity,
                      zIndex: zIndex,
                    }}
                    className={`absolute cursor-pointer select-none transition-shadow ${
                      isSelected
                        ? "shadow-2xl ring-2 ring-blue-500/80"
                        : "hover:ring-1 hover:ring-white/40 shadow-sm"
                    }`}
                    title={`Click to edit shape: ${layer.name || shapeType} (z-index: ${layer.z_index ?? 0})`}
                  >
                    {shapeType === "circle" ? (
                      <div className="w-full h-full flex items-center justify-center pointer-events-none">
                        <div
                          className="aspect-square h-full max-w-full rounded-full pointer-events-none"
                          style={{
                            backgroundColor: fill,
                            border: borderWidth > 0 ? `${borderWidth}px solid ${borderColor}` : "none",
                          }}
                        />
                      </div>
                    ) : shapeType === "ellipse" ? (
                      <div
                        className="w-full h-full pointer-events-none"
                        style={{
                          borderRadius: "50%",
                          backgroundColor: fill,
                          border: borderWidth > 0 ? `${borderWidth}px solid ${borderColor}` : "none",
                        }}
                      />
                    ) : shapeType === "line" ? (
                      <div className="w-full h-full flex items-center pointer-events-none">
                        <div
                          className="w-full rounded-full pointer-events-none"
                          style={{
                            height: `${Math.max(2, borderWidth || 4)}px`,
                            backgroundColor: fill || borderColor,
                          }}
                        />
                      </div>
                    ) : shapeType === "arrow" ? (
                      <div className="w-full h-full flex items-center justify-center pointer-events-none">
                        <svg
                          viewBox="0 0 100 100"
                          preserveAspectRatio="none"
                          className="w-full h-full pointer-events-none"
                        >
                          <polygon
                            points="0,36 65,36 65,0 100,50 65,100 65,64 0,64"
                            fill={fill}
                            stroke={borderWidth > 0 ? borderColor : undefined}
                            strokeWidth={borderWidth > 0 ? borderWidth : undefined}
                          />
                        </svg>
                      </div>
                    ) : (
                      <div
                        className="w-full h-full pointer-events-none"
                        style={{
                          borderRadius: `${borderRadius}px`,
                          backgroundColor: fill,
                          border: borderWidth > 0 ? `${borderWidth}px solid ${borderColor}` : "none",
                        }}
                      />
                    )}

                    {/* DIRECT MANIPULATION GIZMO (Single selection only) */}
                    {isSingleSelectedOnly && (
                      <CanvasTransformGizmo
                        layerId={layer.id}
                        transform={{ x: posX, y: posY, scale, rotation }}
                        canvasRef={canvasViewportRef}
                        onTransformChange={(changes) => handleUpdateLayerTransform(layer.id, changes)}
                        onTransformCommit={handleCommitLayerTransform}
                        locked={layer.locked === true}
                        layerBounds={getLayerEffectiveBounds(layer)}
                        neighborLayers={getNeighborLayers(layer.id)}
                        onSnapGuidesChange={setActiveSnapGuides}
                      />
                    )}
                  </div>
                );
              }

              // Sticker
              const stickerId = c.sticker_id || "star";
              const stickerAssetId = c.asset_id || layer.asset_id;
              const stickerImgSrc = stickerAssetId ? assetUrls[stickerAssetId] : null;
              const minCanvasDim = Math.min(canvasDimensions.width, canvasDimensions.height);
              const stickerSizePx = Math.max(16, Math.round(minCanvasDim * 0.25 * scale));
              const iconSizePx = Math.max(12, Math.round(stickerSizePx * 0.75));

              return (
                <div
                  key={layer.id}
                  onClick={(e) => {
                    e.stopPropagation();
                    const isAdditive = e.ctrlKey || e.metaKey || e.shiftKey;
                    selectElementLayer(layer.id, isAdditive);
                    setActiveLeftTool("elements");
                    setActiveTab("elements");
                  }}
                  style={{
                    left: `${posX * 100}%`,
                    top: `${posY * 100}%`,
                    transform: `translate(-50%, -50%) rotate(${rotation}deg)`,
                    opacity: opacity,
                    zIndex: zIndex,
                    width: `${stickerSizePx}px`,
                    height: `${stickerSizePx}px`,
                  }}
                  className={`absolute cursor-pointer select-none transition-shadow flex items-center justify-center rounded-xl ${
                    isSelected
                      ? "shadow-2xl ring-2 ring-blue-500/80"
                      : "hover:ring-1 hover:ring-white/40 shadow-sm"
                  }`}
                  title={`Click to edit sticker: ${layer.name || stickerId} (z-index: ${layer.z_index ?? 0})`}
                >
                  {stickerImgSrc ? (
                    <img
                      src={stickerImgSrc}
                      alt={layer.name || "Sticker"}
                      className="w-full h-full object-contain pointer-events-none"
                    />
                  ) : stickerId === "heart" ? (
                    <Heart size={iconSizePx} className="fill-red-500 text-red-600 drop-shadow-md" />
                  ) : stickerId === "fire" ? (
                    <Flame size={iconSizePx} className="fill-orange-500 text-amber-400 drop-shadow-md" />
                  ) : stickerId === "sparkles" ? (
                    <Sparkles size={iconSizePx} className="fill-purple-500 text-pink-400 drop-shadow-md" />
                  ) : stickerId === "rocket" ? (
                    <Rocket size={iconSizePx} className="fill-pink-500 text-blue-400 drop-shadow-md" />
                  ) : stickerId === "thumbs_up" ? (
                    <ThumbsUp size={iconSizePx} className="fill-blue-500 text-blue-300 drop-shadow-md" />
                  ) : stickerId === "checkmark" ? (
                    <CheckCircle2 size={iconSizePx} className="fill-emerald-500 text-white drop-shadow-md" />
                  ) : stickerId === "warning" ? (
                    <AlertTriangle size={iconSizePx} className="fill-amber-400 text-black drop-shadow-md" />
                  ) : stickerId === "trophy" ? (
                    <Trophy size={iconSizePx} className="fill-amber-400 text-amber-600 drop-shadow-md" />
                  ) : stickerId === "discount" ? (
                    <Tag size={iconSizePx} className="fill-red-500 text-white drop-shadow-md" />
                  ) : (
                    <Star size={iconSizePx} className="fill-amber-400 text-amber-500 drop-shadow-md" />
                  )}

                  {/* DIRECT MANIPULATION GIZMO (Single selection only) */}
                  {isSingleSelectedOnly && (
                    <CanvasTransformGizmo
                      layerId={layer.id}
                      transform={{ x: posX, y: posY, scale, rotation }}
                      canvasRef={canvasViewportRef}
                      onTransformChange={(changes) => handleUpdateLayerTransform(layer.id, changes)}
                      onTransformCommit={handleCommitLayerTransform}
                      locked={layer.locked === true}
                      layerBounds={getLayerEffectiveBounds(layer)}
                      neighborLayers={getNeighborLayers(layer.id)}
                      onSnapGuidesChange={setActiveSnapGuides}
                    />
                  )}
                </div>
              );
            })}

            {/* MULTI-SELECTION GROUP BOUNDING BOX OVERLAY (Phase 44) */}
            {selectedLayerIds.length > 1 && groupBounds && (
              <div
                style={{
                  left: `${groupBounds.minX * 100}%`,
                  top: `${groupBounds.minY * 100}%`,
                  width: `${groupBounds.width * 100}%`,
                  height: `${groupBounds.height * 100}%`,
                  zIndex: 60,
                }}
                onPointerDown={handleGroupPointerDown}
                onPointerMove={handleGroupPointerMove}
                onPointerUp={handleGroupPointerUp}
                className="absolute border-2 border-dashed border-blue-500 bg-blue-500/10 cursor-move rounded select-none shadow-[0_0_15px_rgba(59,130,246,0.35)]"
              >
                {/* Floating Action Bar */}
                <div
                  onClick={(e) => e.stopPropagation()}
                  className="absolute -top-10 left-1/2 -translate-x-1/2 flex items-center gap-1.5 bg-[#0b101d]/95 border border-blue-500/40 rounded-xl px-2 py-1 shadow-2xl text-[10px] text-white whitespace-nowrap z-50 backdrop-blur-md"
                >
                  <span className="font-semibold text-blue-300 flex items-center gap-1 pr-1 border-r border-white/10">
                    <Layers size={11} /> {selectedVisualLayersForBounds.length}
                  </span>
                  <div className="flex items-center gap-0.5 pr-1 border-r border-white/10">
                    <button onClick={() => handleGroupAlign("left")} className="p-1 hover:bg-white/10 rounded" title="Align Left">Left</button>
                    <button onClick={() => handleGroupAlign("center")} className="p-1 hover:bg-white/10 rounded" title="Align Center">Center</button>
                    <button onClick={() => handleGroupAlign("right")} className="p-1 hover:bg-white/10 rounded" title="Align Right">Right</button>
                    <button onClick={() => handleGroupAlign("top")} className="p-1 hover:bg-white/10 rounded" title="Align Top">Top</button>
                    <button onClick={() => handleGroupAlign("middle")} className="p-1 hover:bg-white/10 rounded" title="Align Middle">Mid</button>
                    <button onClick={() => handleGroupAlign("bottom")} className="p-1 hover:bg-white/10 rounded" title="Align Bottom">Bottom</button>
                  </div>
                  <div className="flex items-center gap-0.5 pr-1 border-r border-white/10">
                    <button
                      onClick={() => handleGroupDistribute("horizontal")}
                      disabled={selectedVisualLayersForBounds.filter((l) => l.locked !== true).length < 3}
                      className="p-1 hover:bg-white/10 disabled:opacity-30 disabled:hover:bg-transparent rounded font-medium"
                      title="Distribute Horizontally (requires 3+ unlocked layers)"
                    >
                      Dist H
                    </button>
                    <button
                      onClick={() => handleGroupDistribute("vertical")}
                      disabled={selectedVisualLayersForBounds.filter((l) => l.locked !== true).length < 3}
                      className="p-1 hover:bg-white/10 disabled:opacity-30 disabled:hover:bg-transparent rounded font-medium"
                      title="Distribute Vertically (requires 3+ unlocked layers)"
                    >
                      Dist V
                    </button>
                  </div>
                  <button onClick={handleGroupDuplicate} className="p-1 hover:bg-white/10 rounded" title="Duplicate Group (Ctrl+D)">
                    <Copy size={11} />
                  </button>
                  <button onClick={handleGroupLock} className="p-1 hover:bg-white/10 rounded" title="Toggle Lock">
                    <Lock size={11} />
                  </button>
                  <button onClick={handleGroupVisibility} className="p-1 hover:bg-white/10 rounded" title="Toggle Visibility">
                    <Eye size={11} />
                  </button>
                  <button onClick={handleGroupDelete} className="p-1 hover:bg-rose-900/60 text-rose-300 rounded" title="Delete Group (Delete)">
                    <Trash2 size={11} />
                  </button>
                </div>
              </div>
            )}

            {/* MARQUEE SELECTION RECTANGLE (Phase 44) */}
            {marqueeState && marqueeState.active && (
              <div
                style={{
                  left: `${Math.min(marqueeState.startX, marqueeState.currentX) * 100}%`,
                  top: `${Math.min(marqueeState.startY, marqueeState.currentY) * 100}%`,
                  width: `${Math.abs(marqueeState.currentX - marqueeState.startX) * 100}%`,
                  height: `${Math.abs(marqueeState.currentY - marqueeState.startY) * 100}%`,
                  zIndex: 70,
                }}
                className="absolute border border-dashed border-blue-400 bg-blue-500/15 pointer-events-none rounded shadow-[0_0_8px_rgba(59,130,246,0.3)]"
              />
            )}

            {/* Dynamic Active Caption Cue Overlay on Canvas Viewport */}
            {activeCaptionCue && (
              <div
                className={`absolute inset-x-0 z-25 px-6 pointer-events-none flex ${
                  captionSettings.style.position === "top"
                    ? "top-14 justify-center"
                    : captionSettings.style.position === "center"
                    ? "top-1/2 -translate-y-1/2 justify-center"
                    : "bottom-16 justify-center"
                } ${
                  captionSettings.style.alignment === "left"
                    ? "!justify-start pl-8"
                    : captionSettings.style.alignment === "right"
                    ? "!justify-end pr-8"
                    : "!justify-center"
                }`}
              >
                <div
                  style={{
                    fontFamily: captionSettings.style.font_family || "Arial",
                    fontSize: `${Math.max(14, Math.round((captionSettings.style.font_size || 32) * 0.75))}px`,
                    fontWeight: captionSettings.style.font_weight === "bold" ? "bold" : "normal",
                    color: captionSettings.style.color || "#FFFFFF",
                    backgroundColor:
                      captionSettings.style.background_opacity > 0
                        ? `${captionSettings.style.background_color || "#000000"}${Math.round(
                            (captionSettings.style.background_opacity ?? 0.6) * 255
                          )
                            .toString(16)
                            .padStart(2, "0")}`
                        : "transparent",
                  }}
                  className="max-w-[85%] px-3.5 py-1.5 rounded-lg shadow-lg text-center backdrop-blur-xs transition-all duration-75"
                >
                  {activeCaptionCue.text}
                </div>
              </div>
            )}

            {/* Overlay Status Badge */}
            <div className="absolute top-4 left-4 z-20">
              <div className="bg-black/70 backdrop-blur-sm text-[10px] px-2.5 py-1 rounded-md border border-white/10 text-slate-300 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse"></span>
                <span>
                  {activeScene?.title || `Scene ${activeSceneIndex + 1}`} ({activeScene?.duration || 5}s)
                </span>
                {activeScene?.avatar?.video_asset_id && (
                  <span className="bg-emerald-600/80 text-white text-[9px] px-1.5 py-0.2 rounded font-semibold ml-1">
                    Rendered MP4
                  </span>
                )}
              </div>
            </div>

            {/* Video Player Floating Bottom Control Bar */}
            <div className="absolute bottom-0 inset-x-0 bg-gradient-to-t from-black/95 via-black/60 to-transparent p-4 flex items-center justify-between z-30">
              <div className="flex items-center gap-3">
                <button
                  onClick={togglePlayback}
                  className="w-8 h-8 rounded-full bg-blue-600 hover:bg-blue-500 flex items-center justify-center text-white transition-all shadow-md cursor-pointer"
                  title={isPlaying ? "Pause" : "Play"}
                >
                  {isPlaying ? <Pause size={14} /> : <Play size={14} className="fill-white" />}
                </button>
                <span className="text-xs font-medium text-slate-300 font-mono">
                  {formatSeconds(playbackTime)} / {formatSeconds(activeScene?.duration || 5)}
                </span>
              </div>

              {/* Scrubber slider */}
              <div className="flex-1 mx-6">
                <div
                  onClick={(e) => {
                    const rect = e.currentTarget.getBoundingClientRect();
                    const clickPos = (e.clientX - rect.left) / rect.width;
                    const targetTime = clickPos * (activeScene?.duration || 5);
                    setPlaybackTime(targetTime);
                    if (videoRef.current) videoRef.current.currentTime = targetTime;
                    if (audioRef.current) audioRef.current.currentTime = targetTime;
                  }}
                  className="w-full h-1.5 bg-slate-700/80 rounded-full overflow-hidden cursor-pointer relative"
                >
                  <div
                    className="h-full bg-blue-500 rounded-full"
                    style={{
                      width: `${Math.min(
                        100,
                        (playbackTime / Math.max(0.1, activeScene?.duration || 5)) * 100
                      )}%`,
                    }}
                  ></div>
                </div>
              </div>

              <div className="flex items-center gap-3 text-slate-300">
                <Volume2 size={16} className="hover:text-white cursor-pointer" />
                <button
                  type="button"
                  id="studio-fullscreen-btn"
                  data-testid="studio-fullscreen-btn"
                  onClick={toggleStudioFullscreen}
                  className="hover:text-white cursor-pointer transition-colors p-0.5 rounded flex items-center justify-center text-slate-300 hover:text-white"
                  title={isFullscreen ? "Exit Fullscreen" : "Enter Fullscreen"}
                  aria-label={isFullscreen ? "Exit Fullscreen" : "Enter Fullscreen"}
                >
                  {isFullscreen ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* DRAGGABLE RESIZE HANDLE: CANVAS <-> RIGHT INSPECTOR */}
        <div
          id="resize-handle-right-inspector"
          data-testid="resize-handle-right-inspector"
          onPointerDown={handleRightResizeStart}
          className="w-2.5 -ml-1 -mr-1 z-30 cursor-col-resize flex items-center justify-center group bg-[#090d18] border-l border-r border-[#1a233a] hover:bg-blue-600/30 active:bg-blue-500/50 transition-colors select-none shrink-0"
          title="Drag to resize inspector"
        >
          <div className="w-[2px] h-10 bg-[#25324e] group-hover:bg-blue-400 group-active:bg-white rounded-full transition-colors" />
        </div>

        {/* RIGHT INSPECTOR PANEL (Scene / Script / Avatar / Voice) */}
        <aside
          id="studio-right-inspector"
          data-testid="studio-right-inspector"
          style={{ width: `${rightInspectorWidth}px`, minWidth: `${rightInspectorWidth}px` }}
          className={`border-l flex flex-col select-none shrink-0 ${
            isLight ? "bg-white border-slate-200 text-slate-900" : "bg-[#090d16] border-[#151c2d] text-white"
          }`}
        >
          {/* Tab Switcher / Multi-Selection Header */}
          {selectedLayerIds.length > 1 ? (
            <div className="flex items-center justify-between px-3.5 py-2.5 bg-blue-950/60 border-b border-blue-500/30 text-xs">
              <span className="font-bold text-blue-300 flex items-center gap-1.5">
                <Layers size={13} className="text-blue-400" />
                Multi-Selection Inspector ({selectedLayerIds.length})
              </span>
              <button
                onClick={clearVisualSelection}
                className="text-[10px] text-slate-400 hover:text-white px-2 py-0.5 rounded bg-slate-800/80 hover:bg-slate-700 transition-colors cursor-pointer"
                title="Deselect all (Esc)"
              >
                Exit
              </button>
            </div>
          ) : (
            <div className="flex border-b border-[#171f33] overflow-x-auto text-[11px]">
              {(["scene", "layers", "avatar", "voice", "music", "media", "captions", "text", "elements"] as const).map((tab) => (
                <button
                  key={tab}
                  onClick={() => {
                    setActiveTab(tab);
                    if (tab === "music") setActiveLeftTool("music");
                    else if (tab === "layers") setActiveLeftTool("layers");
                    else if (tab === "media") setActiveLeftTool("media");
                    else if (tab === "captions") setActiveLeftTool("captions");
                    else if (tab === "text") setActiveLeftTool("text");
                    else if (tab === "elements") setActiveLeftTool("elements");
                    else if (tab === "avatar") setActiveLeftTool("avatar");
                    else if (tab === "voice") setActiveLeftTool("voice");
                    else setActiveLeftTool("scenes");
                  }}
                  className={`flex-1 py-3 px-1 text-center font-semibold capitalize transition-all border-b-2 cursor-pointer whitespace-nowrap ${
                    activeTab === tab
                      ? "border-blue-500 text-white bg-[#111728]"
                      : "border-transparent text-slate-400 hover:text-slate-200"
                  }`}
                >
                  {tab === "scene" ? "Scene" : tab === "layers" ? "Layers" : tab === "music" ? "Music" : tab === "media" ? "Media" : tab === "captions" ? "Captions" : tab === "text" ? "Text" : tab === "elements" ? "Elements" : tab}
                </button>
              ))}
            </div>
          )}

          {/* Inspector Content */}
          <div className="p-4 flex-1 overflow-y-auto space-y-4">
            {selectedLayerIds.length > 1 ? (
              <MultiSelectionInspector
                layers={(activeScene?.layers || []) as VisualLayer[]}
                selectedLayerIds={selectedLayerIds}
                onBatchUpdateOpacity={handleBatchUpdateOpacity}
                onBatchUpdateVisibility={handleBatchUpdateVisibility}
                onBatchUpdateLock={handleBatchUpdateLock}
                onBatchApplyTransformDelta={handleBatchApplyTransformDelta}
                onGroupAlign={handleGroupAlign}
                onGroupDistribute={handleGroupDistribute}
                onGroupDuplicate={handleGroupDuplicate}
                onGroupDelete={handleGroupDelete}
                onGroupZOrder={handleGroupZOrder}
                onClearSelection={clearVisualSelection}
              />
            ) : (
              <>
            {/* -------------------------------------------------------- */}
            {/* TAB 1: SCRIPT & SCENE SETTINGS                           */}
            {/* -------------------------------------------------------- */}
            {activeTab === "scene" && activeScene && (
              <div className="space-y-4">
                {/* Script Editor Box */}
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <label className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1">
                      <FileText size={13} className="text-blue-400" /> Scene Script
                    </label>
                    <span className="text-[10px] text-slate-400">
                      {activeScene.speech?.script?.length || 0} chars
                    </span>
                  </div>
                  <textarea
                    rows={4}
                    value={activeScene.speech?.script || ""}
                    onChange={(e) => handleScriptChange(e.target.value)}
                    onBlur={() => handleSave()}
                    placeholder="Enter speech script for this scene..."
                    className="w-full bg-[#121828] border border-[#1e2a44] rounded-xl p-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 transition-colors resize-none"
                  />
                </div>

                {/* AI Speech & Avatar Actions */}
                <div className="p-3 bg-[#101626] border border-[#1a2640] rounded-xl space-y-2.5">
                  <span className="text-[11px] font-bold text-slate-300 block uppercase tracking-wider">
                    Scene AI Generation
                  </span>

                  {/* 1. Generate Speech Audio */}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-1.5 text-xs text-slate-300">
                      <Mic size={14} className={activeScene.speech?.audio_asset_id ? "text-emerald-400" : "text-slate-500"} />
                      <span>Speech Audio:</span>
                      <span className={`text-[10px] font-semibold ${activeScene.speech?.audio_asset_id ? "text-emerald-400" : "text-amber-400"}`}>
                        {activeScene.speech?.audio_asset_id ? "Generated" : "Needed"}
                      </span>
                    </div>

                    <button
                      onClick={handleGenerateSpeech}
                      disabled={speechJobState.isSynthesizing}
                      className="px-2.5 py-1 bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold rounded-lg shadow disabled:opacity-50 cursor-pointer flex items-center gap-1"
                    >
                      {speechJobState.isSynthesizing ? (
                        <>
                          <Loader2 size={12} className="animate-spin" />
                          <span>{speechJobState.progressPct}%</span>
                        </>
                      ) : (
                        <>
                          <Sparkles size={12} />
                          <span>Generate Audio</span>
                        </>
                      )}
                    </button>
                  </div>

                  {/* 2. Generate Talking Avatar Video */}
                  <div className="flex items-center justify-between pt-2 border-t border-white/5">
                    <div className="flex items-center gap-1.5 text-xs text-slate-300">
                      <Clapperboard size={14} className={activeScene.avatar?.video_asset_id ? "text-emerald-400" : "text-slate-500"} />
                      <span>Avatar Video:</span>
                      <span className={`text-[10px] font-semibold ${activeScene.avatar?.video_asset_id ? "text-emerald-400" : "text-slate-400"}`}>
                        {activeScene.avatar?.video_asset_id ? "Rendered" : "Pending"}
                      </span>
                    </div>

                    <button
                      onClick={handleGenerateAvatarVideo}
                      disabled={avatarJobState.isGenerating || !activeScene.speech?.audio_asset_id}
                      className="px-2.5 py-1 bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold rounded-lg shadow disabled:opacity-40 cursor-pointer flex items-center gap-1"
                      title={!activeScene.speech?.audio_asset_id ? "Synthesize speech first" : "Generate lip-sync video"}
                    >
                      {avatarJobState.isGenerating ? (
                        <>
                          <Loader2 size={12} className="animate-spin" />
                          <span>{avatarJobState.progressPct}%</span>
                        </>
                      ) : (
                        <>
                          <Clapperboard size={12} />
                          <span>Generate Video</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>

                {/* Duration Stepper */}
                <div>
                  <div className="flex items-center justify-between text-[11px] text-slate-400 mb-1.5">
                    <span>Scene Duration</span>
                    <span className="text-white font-bold">{Math.round(activeScene.duration || 5)}s</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => {
                        const cur = activeScene.duration || 5;
                        if (cur > 1) {
                          updateActiveScene((s) => ({ ...s, duration: cur - 1 }));
                          handleSave();
                        }
                      }}
                      className="w-8 h-8 rounded-lg bg-[#121828] border border-[#1e2a44] text-white flex items-center justify-center font-bold hover:bg-[#1c263e] cursor-pointer"
                    >
                      -
                    </button>
                    <input
                      type="range"
                      min={1}
                      max={60}
                      value={activeScene.duration || 5}
                      onChange={(e) => {
                        const val = Number(e.target.value);
                        updateActiveScene((s) => ({ ...s, duration: val }));
                      }}
                      onMouseUp={() => handleSave()}
                      className="flex-1 accent-blue-500"
                    />
                    <button
                      onClick={() => {
                        const cur = activeScene.duration || 5;
                        updateActiveScene((s) => ({ ...s, duration: cur + 1 }));
                        handleSave();
                      }}
                      className="w-8 h-8 rounded-lg bg-[#121828] border border-[#1e2a44] text-white flex items-center justify-center font-bold hover:bg-[#1c263e] cursor-pointer"
                    >
                      +
                    </button>
                  </div>
                </div>

                {/* Transition Selector */}
                <div>
                  <label className="text-[11px] text-slate-400 block mb-1.5">Transition</label>
                  <select
                    value={activeScene.transition?.type || "fade"}
                    onChange={(e) => {
                      const t = e.target.value;
                      updateActiveScene((s) => ({
                        ...s,
                        transition: t === "none" ? null : { type: t, duration: 0.5 },
                      }));
                      handleSave();
                    }}
                    className="w-full bg-[#121828] border border-[#1e2a44] rounded-xl p-2 text-xs text-white focus:outline-none cursor-pointer"
                  >
                    <option value="none">None (Cut)</option>
                    <option value="fade">Fade</option>
                    <option value="wipe_left">Wipe Left</option>
                    <option value="dissolve">Dissolve</option>
                  </select>
                </div>

                {/* Background Color */}
                <div>
                  <label className="text-[11px] text-slate-400 block mb-1.5">Background Color</label>
                  <div className="flex items-center gap-2">
                    {["#0F172A", "#1E1B4B", "#064E3B", "#831843", "#000000"].map((color) => (
                      <button
                        key={color}
                        onClick={() => {
                          updateActiveScene((s) => ({
                            ...s,
                            background: { type: "color", value: color },
                          }));
                          handleSave();
                        }}
                        style={{ backgroundColor: color }}
                        className={`w-7 h-7 rounded-lg border-2 transition-all cursor-pointer ${
                          activeScene.background?.value === color
                            ? "border-blue-400 scale-110 shadow-md"
                            : "border-transparent hover:scale-105"
                        }`}
                      />
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* -------------------------------------------------------- */}
            {/* TAB 2: AVATAR SELECTION                                  */}
            {/* -------------------------------------------------------- */}
            {activeTab === "avatar" && activeScene && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
                    <User size={14} className="text-blue-400" /> Select Avatar
                  </h4>
                  <span className="text-[10px] text-slate-400">
                    {avatarSearch ? `${filteredAvatars.length} of ${avatars.length}` : avatars.length} available
                  </span>
                </div>

                {/* Search */}
                <div className="relative">
                  <Search size={13} className="absolute left-2.5 top-2.5 text-slate-500" />
                  <input
                    type="text"
                    value={avatarSearch}
                    onChange={(e) => setAvatarSearch(e.target.value)}
                    placeholder="Search avatars..."
                    className="w-full bg-[#121828] border border-[#1e2a44] rounded-xl pl-8 pr-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none"
                  />
                </div>

                {/* View Mode Toggle */}
                <div>
                  <label className="text-[11px] text-slate-400 block mb-1.5">Framing Mode</label>
                  <div className="grid grid-cols-3 gap-1.5 bg-[#101625] p-1 rounded-xl border border-[#1e2940]">
                    {(["half_body", "close_up", "circle"] as const).map((mode) => (
                      <button
                        key={mode}
                        onClick={() => {
                          updateActiveScene((s) => ({
                            ...s,
                            avatar: {
                              ...(s.avatar || { avatar_id: "default-presenter" }),
                              view_mode: mode,
                            },
                          }));
                          handleSave();
                        }}
                        className={`py-1 text-[10px] font-semibold rounded-lg capitalize transition-colors cursor-pointer ${
                          activeScene.avatar?.view_mode === mode
                            ? "bg-blue-600 text-white shadow"
                            : "text-slate-400 hover:text-white"
                        }`}
                      >
                        {mode.replace("_", " ")}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Avatars Grid List */}
                <div className="space-y-2 max-h-[380px] overflow-y-auto pr-1">
                  {filteredAvatars.map((av) => {
                    const isSelected =
                      activeScene.avatar?.avatar_id === av.id ||
                      activeScene.avatar?.avatar_id === av.name ||
                      (av.provider_reference && activeScene.avatar?.avatar_id === av.provider_reference) ||
                      (activeScene.avatar?.avatar_id === "default-presenter" && (av.name.toLowerCase().includes("default") || av.provider_reference === "default-presenter"));
                    const isGpu = av.provider === "musetalk";
                    const avatarImg = av.preview_url || av.provider_metadata?.preview_url || av.provider_metadata?.image_url;

                    return (
                      <div
                        key={av.id}
                        onClick={() => handleSelectAvatar(String(av.id))}
                        className={`p-2.5 rounded-xl border transition-all cursor-pointer ${
                          isSelected
                            ? "bg-[#162035] border-blue-500 shadow-md shadow-blue-500/15"
                            : "bg-[#0e1322] border-[#1a233a] hover:border-[#283758]"
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2.5">
                            <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-blue-900 to-purple-900 border border-blue-500/30 flex items-center justify-center text-lg shadow overflow-hidden flex-shrink-0">
                              {avatarImg ? (
                                <img
                                  src={avatarImg}
                                  alt={av.name}
                                  className="w-full h-full object-cover"
                                />
                              ) : (
                                "👤"
                              )}
                            </div>
                            <div>
                              <span className="text-xs font-bold text-white block">{av.name}</span>
                              <div className="flex items-center gap-1 mt-0.5">
                                <span className={`text-[9px] px-1.5 py-0.2 rounded font-semibold uppercase ${
                                  isGpu ? "bg-amber-900/60 text-amber-300" : "bg-blue-900/60 text-blue-300"
                                }`}>
                                  {av.provider || "wav2lip"}
                                </span>
                                {isGpu && (
                                  <span className="text-[8px] text-slate-400">(GPU)</span>
                                )}
                              </div>
                            </div>
                          </div>

                          {isSelected && (
                            <div className="w-5 h-5 rounded-full bg-blue-600 text-white flex items-center justify-center flex-shrink-0">
                              <Check size={12} />
                            </div>
                          )}
                        </div>

                        {/* Optional Look / Style Switcher for Selected Avatar */}
                        {isSelected && Array.isArray(av.looks) && av.looks.length > 1 && (
                          <div className="mt-2 pt-2 border-t border-[#1e2a44] flex items-center gap-1.5 flex-wrap">
                            <span className="text-[9px] text-slate-400 block w-full">Looks / Styling:</span>
                            {av.looks.map((look: any) => {
                              const isLookActive =
                                (activeScene.avatar as any)?.look_id === look.id ||
                                (!((activeScene.avatar as any)?.look_id) && look.name.toLowerCase().includes("half"));
                              return (
                                <button
                                  key={look.id}
                                  type="button"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    updateActiveScene((s) => ({
                                      ...s,
                                      avatar: {
                                        ...(s.avatar || { avatar_id: av.id }),
                                        look_id: look.id,
                                        ...(look.configuration?.pose ? { view_mode: look.configuration.pose } : {}),
                                      },
                                    }));
                                    handleSave();
                                  }}
                                  className={`text-[9px] px-2 py-0.5 rounded-md border font-medium transition-all ${
                                    isLookActive
                                      ? "bg-blue-600 border-blue-400 text-white shadow-sm"
                                      : "bg-[#111726] border-[#1e2940] text-slate-300 hover:text-white"
                                  }`}
                                >
                                  {look.name}
                                </button>
                              );
                            })}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* -------------------------------------------------------- */}
            {/* TAB 3: VOICE SELECTION                                   */}
            {/* -------------------------------------------------------- */}
            {activeTab === "voice" && activeScene && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
                    <Mic size={14} className="text-blue-400" /> Voice Library
                  </h4>
                  <span className="text-[10px] text-slate-400">
                    {voices.length} voices
                  </span>
                </div>

                {/* Language Filter Chips */}
                <div className="flex gap-1 overflow-x-auto pb-1 text-[10px]">
                  {[
                    { id: "all", label: "All" },
                    { id: "en", label: "EN" },
                    { id: "es", label: "ES" },
                    { id: "de", label: "DE" },
                    { id: "fr", label: "FR" },
                    { id: "it", label: "IT" },
                    { id: "pt", label: "PT" },
                  ].map((chip) => (
                    <button
                      key={chip.id}
                      onClick={() => setVoiceLangFilter(chip.id)}
                      className={`px-2 py-0.5 rounded-full border transition-colors cursor-pointer whitespace-nowrap ${
                        voiceLangFilter === chip.id
                          ? "bg-blue-600 border-blue-500 text-white font-bold"
                          : "bg-[#101625] border-[#1e2940] text-slate-400 hover:text-white"
                      }`}
                    >
                      {chip.label}
                    </button>
                  ))}
                </div>

                {/* Voice Search */}
                <div className="relative">
                  <Search size={13} className="absolute left-2.5 top-2.5 text-slate-500" />
                  <input
                    type="text"
                    value={voiceSearch}
                    onChange={(e) => setVoiceSearch(e.target.value)}
                    placeholder="Search voices..."
                    className="w-full bg-[#121828] border border-[#1e2a44] rounded-xl pl-8 pr-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none"
                  />
                </div>

                {/* Voice Cards List */}
                <div className="space-y-2 max-h-[380px] overflow-y-auto pr-1">
                  {filteredVoices.map((v) => {
                    const isSelected =
                      activeScene.speech?.voice_id === v.id ||
                      activeScene.speech?.voice_id === v.name;
                    const isPreviewing = previewingVoiceId === v.id;

                    return (
                      <div
                        key={v.id}
                        className={`p-2.5 rounded-xl border transition-all flex items-center justify-between ${
                          isSelected
                            ? "bg-[#162035] border-blue-500 shadow-md shadow-blue-500/15"
                            : "bg-[#0e1322] border-[#1a233a] hover:border-[#283758]"
                        }`}
                      >
                        <div
                          onClick={() => handleSelectVoice(String(v.id))}
                          className="flex-1 cursor-pointer"
                        >
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-bold text-white">{v.name}</span>
                            <span className="text-[9px] bg-blue-900/50 text-blue-300 px-1.5 py-0.2 rounded font-semibold uppercase">
                              {v.language || "en"}
                            </span>
                            <span className="text-[9px] bg-purple-900/50 text-purple-300 px-1.5 py-0.2 rounded font-semibold">
                              {v.provider || "piper"}
                            </span>
                          </div>
                          <span className="text-[10px] text-slate-400 capitalize block mt-0.5">
                            {v.gender || "neutral"} • {v.voice_type || "synthetic"}
                          </span>
                        </div>

                        <div className="flex items-center gap-1.5">
                          {/* Play Preview Audio */}
                          <button
                            onClick={() => handlePreviewVoice(v.id)}
                            className="p-1.5 rounded-lg bg-[#141c2e] hover:bg-[#1f2c4a] text-slate-300 hover:text-white cursor-pointer transition-colors"
                            title="Play Voice Sample"
                          >
                            {isPreviewing ? (
                              <Loader2 size={13} className="animate-spin text-blue-400" />
                            ) : (
                              <Play size={13} />
                            )}
                          </button>

                          {/* Selected Mark */}
                          {isSelected && (
                            <div className="w-5 h-5 rounded-full bg-blue-600 text-white flex items-center justify-center">
                              <Check size={12} />
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* -------------------------------------------------------- */}
            {/* TAB 4: MUSIC & BACKGROUND AUDIO                          */}
            {/* -------------------------------------------------------- */}
            {activeTab === "music" && (
              <MusicPanel
                workspaceId={workspaceId}
                audioTracks={audioTracks}
                activeTrackId={activeAudioTrackId}
                onSelectTrack={(trackId) => setActiveAudioTrackId(trackId)}
                onAddTrack={handleAddMusicTrack}
                onUpdateTrack={handleUpdateMusicTrack}
                onRemoveTrack={handleRemoveMusicTrack}
                onCommitTrack={handleCommitAudioTrack}
                onOpenUploadModal={() => {
                  setUploadModalTarget("music");
                  setIsUploadModalOpen(true);
                }}
              />
            )}

            {/* -------------------------------------------------------- */}
            {/* TAB 5: MEDIA LIBRARY & SCENE ASSETS                      */}
            {/* -------------------------------------------------------- */}
            {activeTab === "media" && (
              <MediaPanel
                workspaceId={workspaceId}
                onSetSceneBackground={handleSetSceneBackground}
                onAddMediaLayer={handleAddMediaLayer}
                onAddMusicTrack={handleAddMusicTrack}
                onOpenUploadModal={() => {
                  setUploadModalTarget("media");
                  setIsUploadModalOpen(true);
                }}
                currentBackgroundAssetId={activeScene?.background?.asset_id}
                scenes={scenes}
                activeSceneIndex={activeSceneIndex}
                onSelectScene={(idx) => setActiveSceneIndex(idx)}
                selectedMediaLayerId={selectedMediaLayerId}
                onSelectMediaLayer={selectMediaLayer}
                onUpdateMediaLayers={async (sceneIdx, layers) => {
                  const updated = scenes.map((s, idx) => (idx === sceneIdx ? { ...s, layers } : s));
                  setScenes(updated);
                  commitStudioHistory("Update Media Layer", updated);
                  await handleSave(updated);
                }}
                assetUrls={assetUrls}
              />
            )}

            {/* -------------------------------------------------------- */}
            {/* TAB 6: CAPTIONS & SUBTITLES                              */}
            {/* -------------------------------------------------------- */}
            {activeTab === "captions" && (
              <CaptionsPanel
                scenes={scenes}
                activeSceneIndex={activeSceneIndex}
                onSelectScene={(idx) => setActiveSceneIndex(idx)}
                captionSettings={captionSettings}
                onUpdateCaptionSettings={(settings) => {
                  setCaptionSettings(settings);
                  commitStudioHistory("Update Caption Settings");
                  handleSave();
                }}
                onUpdateSubtitles={(sceneIndex, newSubtitles) => {
                  const next = [...scenes];
                  if (next[sceneIndex]) {
                    next[sceneIndex] = {
                      ...next[sceneIndex],
                      subtitles: newSubtitles,
                    };
                  }
                  setScenes(next);
                  commitStudioHistory("Update Subtitles", next);
                  handleSave(next);
                }}
                onGenerateCaptions={handleGenerateCaptions}
                isGenerating={isTranscribing}
                selectedCueId={selectedCueId}
                onSelectCue={(id) => setSelectedCueId(id)}
              />
            )}

            {/* -------------------------------------------------------- */}
            {/* TAB 7: TEXT OVERLAYS                                     */}
            {/* -------------------------------------------------------- */}
            {activeTab === "text" && (
              <TextPanel
                scenes={scenes}
                activeSceneIndex={activeSceneIndex}
                onSelectScene={(idx) => setActiveSceneIndex(idx)}
                selectedTextLayerId={selectedTextLayerId}
                onSelectTextLayer={selectTextLayer}
                onUpdateTextLayers={async (sceneIdx, layers) => {
                  const updated = scenes.map((s, idx) => (idx === sceneIdx ? { ...s, layers } : s));
                  setScenes(updated);
                  commitStudioHistory("Update Text Layer", updated);
                  await handleSave(updated);
                }}
              />
            )}

            {/* -------------------------------------------------------- */}
            {/* TAB 8: ELEMENTS & SHAPES                                 */}
            {/* -------------------------------------------------------- */}
            {activeTab === "elements" && (
              <ElementsPanel
                scenes={scenes}
                activeSceneIndex={activeSceneIndex}
                onSelectScene={(idx) => setActiveSceneIndex(idx)}
                selectedElementLayerId={selectedElementLayerId}
                onSelectElementLayer={selectElementLayer}
                onUpdateElementLayers={async (sceneIdx, layers) => {
                  const updated = scenes.map((s, idx) => (idx === sceneIdx ? { ...s, layers } : s));
                  setScenes(updated);
                  commitStudioHistory("Update Element Layer", updated);
                  await handleSave(updated);
                }}
              />
            )}

            {/* -------------------------------------------------------- */}
            {/* TAB 9: UNIFIED SCENE LAYERS (PHASE 42B / PHASE 44)       */}
            {/* -------------------------------------------------------- */}
            {activeTab === "layers" && activeScene && (
              <UnifiedLayersPanel
                layers={activeScene.layers || []}
                activeSceneIndex={activeSceneIndex}
                selectedMediaLayerId={selectedMediaLayerId}
                selectedTextLayerId={selectedTextLayerId}
                selectedElementLayerId={selectedElementLayerId}
                selectedLayerIds={selectedLayerIds}
                onSelectLayer={(layerId, type, isAdditive) => {
                  if (type === "image" || type === "video" || type === "media") {
                    selectMediaLayer(layerId, isAdditive);
                  } else if (type === "text") {
                    selectTextLayer(layerId, isAdditive);
                  } else {
                    selectElementLayer(layerId, isAdditive);
                  }
                }}
                onSelectAll={selectAllLayers}
                onClearSelection={clearVisualSelection}
                onGroupAlign={handleGroupAlign}
                onGroupDistribute={handleGroupDistribute}
                onGroupDuplicate={handleGroupDuplicate}
                onGroupDelete={handleGroupDelete}
                onGroupToggleLock={handleGroupLock}
                onGroupToggleVisibility={handleGroupVisibility}
                onGroupZOrder={handleGroupZOrder}
                onBringForward={handleBringLayerForward}
                onSendBackward={handleSendLayerBackward}
                onBringToFront={handleBringLayerToFront}
                onSendToBack={handleSendLayerToBack}
                onMoveLayerToIndex={handleMoveLayerToIndex}
                onToggleEnable={(layerId) => {
                  const current = activeScene.layers || [];
                  const updated = current.map((l: any) =>
                    l.id === layerId ? { ...l, enabled: l.enabled === false ? true : false } : l
                  );
                  const nextScenes = scenes.map((s, idx) =>
                    idx === activeSceneIndex ? { ...s, layers: updated } : s
                  );
                  setScenes(nextScenes);
                  commitStudioHistory("Toggle Layer Visibility", nextScenes);
                  handleSave(nextScenes);
                }}
                onToggleLock={(layerId) => {
                  const current = activeScene.layers || [];
                  const updated = current.map((l: any) =>
                    l.id === layerId ? { ...l, locked: l.locked === true ? false : true } : l
                  );
                  const nextScenes = scenes.map((s, idx) =>
                    idx === activeSceneIndex ? { ...s, layers: updated } : s
                  );
                  setScenes(nextScenes);
                  commitStudioHistory("Toggle Layer Lock", nextScenes);
                  handleSave(nextScenes);
                }}
                onDeleteLayer={(layerId) => {
                  const current = activeScene.layers || [];
                  const updated = deleteLayerWithZIndex(current, layerId);
                  const nextScenes = scenes.map((s, idx) =>
                    idx === activeSceneIndex ? { ...s, layers: updated } : s
                  );
                  setScenes(nextScenes);
                  commitStudioHistory("Delete Layer", nextScenes);
                  handleSave(nextScenes);
                }}
                onDuplicateLayer={(layerId) => {
                  const current = activeScene.layers || [];
                  const target = current.find((l: any) => l.id === layerId);
                  if (!target) return;
                  const kind =
                    target.type === "image" || target.type === "video" || target.type === "media"
                      ? "media"
                      : target.type === "text"
                      ? "text"
                      : "element";
                  const { clonedLayer, newId } = createLayerDuplicatePayload(target, kind as any);
                  const updated = duplicateLayerWithZIndex(current, layerId, clonedLayer);
                  const nextScenes = scenes.map((s, idx) =>
                    idx === activeSceneIndex ? { ...s, layers: updated } : s
                  );
                  setScenes(nextScenes);
                  if (kind === "media") selectMediaLayer(newId);
                  else if (kind === "text") selectTextLayer(newId);
                  else selectElementLayer(newId);
                  commitStudioHistory("Duplicate Layer", nextScenes);
                  handleSave(nextScenes);
                }}
                assetUrls={assetUrls}
              />
            )}
          </>
        )}
      </div>
        </aside>
      </div>

      {/* DRAGGABLE RESIZE HANDLE: WORKSPACE <-> TIMELINE */}
      <div
        id="resize-handle-timeline"
        data-testid="resize-handle-timeline"
        onPointerDown={handleTimelineResizeStart}
        className="w-full h-2.5 -mt-1 -mb-1 z-30 cursor-row-resize flex items-center justify-center group bg-[#090d18] border-t border-b border-[#1a233a] hover:bg-blue-600/30 active:bg-blue-500/50 transition-colors select-none shrink-0"
        title="Drag to resize timeline"
      >
        <div className="h-[2px] w-14 bg-[#25324e] group-hover:bg-blue-400 group-active:bg-white rounded-full transition-colors" />
      </div>

      {/* 3. MULTI-TRACK BOTTOM TIMELINE */}
      <div
        id="studio-bottom-timeline"
        data-testid="studio-bottom-timeline"
        style={{ height: `${timelineHeight}px`, minHeight: `${timelineHeight}px` }}
        className={`border-t flex flex-col select-none shrink-0 overflow-hidden ${
          isLight ? "bg-white border-slate-200 text-slate-900" : "bg-[#080b12] border-[#151c2d] text-white"
        }`}
      >
        {/* Timeline Action Bar */}
        <div className="h-9 bg-[#0b0e18] border-b border-[#151c2d] px-4 flex items-center justify-between text-slate-400 text-xs">
          <div className="flex items-center gap-3">
            <button
              onClick={handleUndo}
              disabled={!canUndoState}
              className="hover:text-white p-1 cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed"
              title="Undo (Ctrl+Z)"
            >
              <RotateCcw size={13} />
            </button>
            <button
              onClick={handleRedo}
              disabled={!canRedoState}
              className="hover:text-white p-1 cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed"
              title="Redo (Ctrl+Y / Ctrl+Shift+Z)"
            >
              <RotateCw size={13} />
            </button>
            <div className="h-4 w-[1px] bg-[#1a243a]"></div>
            <button
              onClick={() => handleDuplicateScene(activeSceneIndex)}
              className="hover:text-white p-1 cursor-pointer flex items-center gap-1"
              title="Duplicate Selected Scene"
            >
              <Copy size={13} /> <span className="text-[11px] hidden sm:inline">Duplicate</span>
            </button>
            <button
              onClick={() => handleDeleteScene(activeSceneIndex)}
              className="hover:text-red-400 p-1 cursor-pointer flex items-center gap-1"
              title="Delete Selected Scene"
            >
              <Trash2 size={13} /> <span className="text-[11px] hidden sm:inline">Delete</span>
            </button>
            <div className="h-4 w-[1px] bg-[#1a243a]"></div>
            <button
              onClick={handleSplitSelectedClip}
              className="hover:text-white p-1 cursor-pointer flex items-center gap-1 text-slate-300 hover:text-cyan-400 transition-colors"
              title="Split selected clip at playhead (S)"
            >
              <Scissors size={13} /> <span className="text-[11px] hidden sm:inline">Split (S)</span>
            </button>
          </div>

          <div className="flex items-center gap-3">
            {/* Timeline Zoom Controls (Phase 43) */}
            <div className="flex items-center gap-1.5 bg-[#090d16] border border-[#1a243a] px-2 py-0.5 rounded-lg">
              <button
                onClick={() => handleZoomChange(timelineZoom - 0.2)}
                disabled={timelineZoom <= MIN_TIMELINE_ZOOM}
                className="p-1 hover:text-white disabled:opacity-30 cursor-pointer disabled:cursor-not-allowed transition-colors"
                title="Zoom Out"
              >
                <ZoomOut size={12} />
              </button>
              <input
                type="range"
                min={MIN_TIMELINE_ZOOM}
                max={MAX_TIMELINE_ZOOM}
                step={0.1}
                value={timelineZoom}
                onChange={(e) => handleZoomChange(parseFloat(e.target.value))}
                className="w-16 h-1 bg-[#151d2f] rounded-lg appearance-none cursor-pointer accent-blue-500"
                title={`Timeline Zoom: ${Math.round(timelineZoom * 100)}%`}
              />
              <button
                onClick={() => handleZoomChange(timelineZoom + 0.2)}
                disabled={timelineZoom >= MAX_TIMELINE_ZOOM}
                className="p-1 hover:text-white disabled:opacity-30 cursor-pointer disabled:cursor-not-allowed transition-colors"
                title="Zoom In"
              >
                <ZoomIn size={12} />
              </button>
              <button
                onClick={() => handleZoomChange(DEFAULT_TIMELINE_ZOOM)}
                className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#131929] hover:bg-[#1c2842] text-slate-300 hover:text-white cursor-pointer ml-0.5"
                title="Reset Zoom to 100%"
              >
                {Math.round(timelineZoom * 100)}%
              </button>
            </div>

            <span className="text-[11px] font-mono text-slate-300">
              Total: {formatSeconds(totalDuration)} ({scenes.length} scenes)
            </span>
          </div>
        </div>

        {/* Tracks Container */}
        <div
          ref={timelineScrollContainerRef}
          className="flex-1 flex overflow-x-auto overflow-y-hidden"
        >
          {/* Left Track Labels */}
          <div className="w-32 min-w-32 sticky left-0 z-20 bg-[#090d16] border-r border-[#151c2d] flex flex-col py-1 text-[11px] text-slate-400">
            <div
              onClick={() => {
                setActiveLeftTool("scenes");
                setActiveTab("scene");
              }}
              className="h-7 px-3 flex items-center justify-between border-b border-[#131929] cursor-pointer hover:text-white transition-colors"
              title="Configure Scenes"
            >
              <span>🎬 Scene</span>
              <Eye size={11} />
            </div>
            <div
              onClick={() => {
                setActiveLeftTool("avatar");
                setActiveTab("avatar");
              }}
              className="h-7 px-3 flex items-center justify-between border-b border-[#131929] cursor-pointer hover:text-white transition-colors"
              title="Configure Avatar"
            >
              <span>👤 Avatar</span>
              <Eye size={11} />
            </div>
            <div
              onClick={() => {
                setActiveLeftTool("scenes");
                setActiveTab("scene");
              }}
              className="h-7 px-3 flex items-center justify-between border-b border-[#131929] cursor-pointer hover:text-white transition-colors"
              title="Configure Script"
            >
              <span>🔤 Script</span>
              <Eye size={11} />
            </div>
            <div
              onClick={() => {
                setActiveLeftTool("voice");
                setActiveTab("voice");
              }}
              className="h-7 px-3 flex items-center justify-between border-b border-[#131929] cursor-pointer hover:text-white transition-colors"
              title="Configure Speech & Voice"
            >
              <span>🎵 Speech</span>
              <Eye size={11} />
            </div>
            <div
              onClick={() => {
                setActiveLeftTool("music");
                setActiveTab("music");
              }}
              className="h-7 px-3 flex items-center justify-between cursor-pointer hover:text-white transition-colors"
              title="Configure Background Music"
            >
              <span>🎶 Music</span>
              <Eye size={11} />
            </div>
            <div
              onClick={() => {
                setActiveLeftTool("captions");
                setActiveTab("captions");
              }}
              className="h-7 px-3 flex items-center justify-between border-t border-[#131929] cursor-pointer hover:text-white transition-colors"
              title="Configure Captions"
            >
              <span>💬 Captions</span>
              <Eye size={11} />
            </div>
            <div
              onClick={() => {
                setActiveLeftTool("text");
                setActiveTab("text");
              }}
              className="h-7 px-3 flex items-center justify-between border-t border-[#131929] cursor-pointer hover:text-white transition-colors"
              title="Configure Text Overlays"
            >
              <span>✍️ Text</span>
              <Eye size={11} />
            </div>
            <div
              onClick={() => {
                setActiveLeftTool("media");
                setActiveTab("media");
              }}
              className="h-7 px-3 flex items-center justify-between border-t border-[#131929] cursor-pointer hover:text-white transition-colors"
              title="Configure Media Layers"
            >
              <span>🎬 Media</span>
              <Eye size={11} />
            </div>
            <div
              onClick={() => {
                setActiveLeftTool("elements");
                setActiveTab("elements");
              }}
              className="h-7 px-3 flex items-center justify-between border-t border-[#131929] cursor-pointer hover:text-white transition-colors"
              title="Configure Elements & Shapes"
            >
              <span>🎨 Elements</span>
              <Eye size={11} />
            </div>
          </div>

          {/* Right Track Timeline Lanes */}
          <div
            ref={timelineTracksContainerRef}
            onClick={(e) => {
              const rect = e.currentTarget.getBoundingClientRect();
              const clickPos = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
              const clickGlobalTime = clickPos * totalDuration;
              let accumulated = 0;
              let foundSceneIdx = 0;
              let sceneRelativeTime = 0;
              for (let i = 0; i < scenes.length; i++) {
                const d = typeof scenes[i].duration === "number" ? scenes[i].duration : 5.0;
                if (clickGlobalTime <= accumulated + d || i === scenes.length - 1) {
                  foundSceneIdx = i;
                  sceneRelativeTime = Math.max(0, Math.min(d, clickGlobalTime - accumulated));
                  break;
                }
                accumulated += d;
              }
              if (foundSceneIdx !== activeSceneIndex) {
                setActiveSceneIndex(foundSceneIdx);
              }
              setPlaybackTime(sceneRelativeTime);
              if (videoRef.current) videoRef.current.currentTime = sceneRelativeTime;
              if (audioRef.current) audioRef.current.currentTime = sceneRelativeTime;
            }}
            style={{
              minWidth: `${Math.round(Math.max(1, timelineZoom) * 100)}%`,
              width: `${Math.round(Math.max(1, timelineZoom) * 100)}%`,
            }}
            className="flex-1 flex flex-col py-1 relative min-w-[700px] bg-[#07090f] cursor-pointer"
          >
            {/* Dynamic Playhead Needle */}
            <div
              className="absolute top-0 bottom-0 w-[2px] bg-blue-500 z-30 pointer-events-none shadow-[0_0_8px_rgba(59,130,246,0.8)] transition-all"
              style={{
                left: `${Math.min(100, ((activeSceneOffset + playbackTime) / Math.max(0.1, totalDuration)) * 100)}%`,
              }}
            >
              <div className="w-3 h-3 bg-blue-500 transform -translate-x-[5px] rotate-45 rounded-xs"></div>
            </div>

            {/* 1. Scene Video Track */}
            <div className="h-7 px-2 flex items-center gap-1.5 border-b border-[#131929]">
              {scenes.map((sc, idx) => {
                const isSelected = activeSceneIndex === idx;
                const widthPct = ((sc.duration || 5) / totalDuration) * 100;
                return (
                  <div
                    key={sc.id}
                    onClick={() => setActiveSceneIndex(idx)}
                    style={{ width: `${Math.max(12, widthPct)}%` }}
                    className={`group relative h-5.5 rounded text-[10px] px-2 flex items-center justify-between truncate cursor-pointer transition-all border ${
                      isSelected
                        ? "bg-blue-600/40 border-blue-400 text-blue-100 font-semibold"
                        : "bg-blue-950/40 border-blue-900/60 text-blue-300 hover:border-blue-700"
                    }`}
                  >
                    {/* Left Edge Resize Handle */}
                    <div
                      className="absolute left-0 top-0 bottom-0 w-2.5 cursor-ew-resize opacity-0 group-hover:opacity-100 flex items-center justify-center hover:bg-blue-400/40 rounded-l transition-opacity z-10"
                      onPointerDown={(e) => startResizeScene(e, idx, "left")}
                      title="Drag left edge to resize scene"
                    >
                      <div className="w-[2px] h-3 bg-blue-300 rounded-full pointer-events-none" />
                    </div>

                    <span className="truncate mr-1">{sc.title || `Scene ${idx + 1}`}</span>

                    <div className="flex items-center gap-1 shrink-0">
                      <span className="text-[9px] opacity-70">{Math.round((sc.duration || 5) * 10) / 10}s</span>

                      {/* Hover / Selection Controls */}
                      <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity ml-1 z-20">
                        <button
                          type="button"
                          className="p-0.5 rounded hover:bg-white/20 text-blue-200 hover:text-white"
                          title="Edit Scene"
                          onClick={(e) => {
                            e.stopPropagation();
                            setActiveSceneIndex(idx);
                            setActiveLeftTool("scenes");
                            setActiveTab("scene");
                          }}
                        >
                          <Pencil size={10} />
                        </button>
                        {scenes.length > 1 && (
                          <button
                            type="button"
                            className="p-0.5 rounded hover:bg-red-500/40 text-blue-200 hover:text-red-200"
                            title="Delete Scene"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDeleteScene(idx);
                            }}
                          >
                            <Trash2 size={10} />
                          </button>
                        )}
                      </div>
                    </div>

                    {/* Right Edge Resize Handle */}
                    <div
                      className="absolute right-0 top-0 bottom-0 w-2.5 cursor-ew-resize opacity-0 group-hover:opacity-100 flex items-center justify-center hover:bg-blue-400/40 rounded-r transition-opacity z-10"
                      onPointerDown={(e) => startResizeScene(e, idx, "right")}
                      title="Drag right edge to resize scene"
                    >
                      <div className="w-[2px] h-3 bg-blue-300 rounded-full pointer-events-none" />
                    </div>
                  </div>
                );
              })}
            </div>

            {/* 2. Avatar Track */}
            <div className="h-7 px-2 flex items-center gap-1.5 border-b border-[#131929]">
              {scenes.map((sc, idx) => {
                const isSelected = activeSceneIndex === idx;
                const widthPct = ((sc.duration || 5) / totalDuration) * 100;
                const avObj = avatars.find((a) =>
                  a.id === sc.avatar?.avatar_id ||
                  a.provider_reference === sc.avatar?.avatar_id ||
                  a.name === sc.avatar?.avatar_id ||
                  a.name?.toLowerCase().replace(/\s+/g, "-") === sc.avatar?.avatar_id
                );
                const hasAvatar = Boolean(sc.avatar);
                const aStart = Math.max(0, sc.avatar?.start_time ?? 0);
                const aEnd = Math.min(sc.duration || 5, sc.avatar?.end_time ?? (sc.duration || 5));
                const clipDur = Math.max(0.5, aEnd - aStart);
                const leftPct = ((aStart) / (sc.duration || 5)) * 100;
                const clipWidthPct = Math.max(10, ((clipDur) / (sc.duration || 5)) * 100);

                return (
                  <div
                    key={sc.id}
                    style={{ width: `${Math.max(12, widthPct)}%` }}
                    className="h-7 relative flex items-center"
                  >
                    {hasAvatar ? (
                      <div
                        onClick={() => setActiveSceneIndex(idx)}
                        style={{
                          left: `${leftPct}%`,
                          width: `${clipWidthPct}%`,
                        }}
                        className={`group absolute h-5.5 rounded text-[10px] px-2 flex items-center justify-between truncate cursor-pointer transition-all border ${
                          isSelected
                            ? "bg-purple-600/40 border-purple-400 text-purple-100 font-semibold"
                            : "bg-purple-950/40 border-purple-900/60 text-purple-300 hover:border-purple-700"
                        }`}
                      >
                        {/* Left Edge Resize Handle */}
                        <div
                          className="absolute left-0 top-0 bottom-0 w-2.5 cursor-ew-resize opacity-0 group-hover:opacity-100 flex items-center justify-center hover:bg-purple-400/40 rounded-l transition-opacity z-10"
                          onPointerDown={(e) => startResizeAvatar(e, idx, "left")}
                          title="Drag left edge to resize avatar start time"
                        >
                          <div className="w-[2px] h-3 bg-purple-300 rounded-full pointer-events-none" />
                        </div>

                        <span className="truncate mr-1">👤 {avObj?.name || sc.avatar?.avatar_id || "Avatar"}</span>

                        <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity ml-1 shrink-0 z-20">
                          <button
                            type="button"
                            className="p-0.5 rounded hover:bg-white/20 text-purple-200 hover:text-white"
                            title="Edit Avatar"
                            onClick={(e) => {
                              e.stopPropagation();
                              setActiveSceneIndex(idx);
                              setActiveLeftTool("avatar");
                              setActiveTab("avatar");
                            }}
                          >
                            <Pencil size={10} />
                          </button>
                          <button
                            type="button"
                            className="p-0.5 rounded hover:bg-red-500/40 text-purple-200 hover:text-red-200"
                            title="Remove Avatar"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDeleteAvatar(idx);
                            }}
                          >
                            <Trash2 size={10} />
                          </button>
                        </div>

                        {/* Right Edge Resize Handle */}
                        <div
                          className="absolute right-0 top-0 bottom-0 w-2.5 cursor-ew-resize opacity-0 group-hover:opacity-100 flex items-center justify-center hover:bg-purple-400/40 rounded-r transition-opacity z-10"
                          onPointerDown={(e) => startResizeAvatar(e, idx, "right")}
                          title="Drag right edge to resize avatar end time"
                        >
                          <div className="w-[2px] h-3 bg-purple-300 rounded-full pointer-events-none" />
                        </div>
                      </div>
                    ) : (
                      <div
                        onClick={() => {
                          setActiveSceneIndex(idx);
                          setActiveLeftTool("avatar");
                          setActiveTab("avatar");
                        }}
                        className="w-full h-5.5 rounded text-[10px] px-2 flex items-center justify-center border border-dashed border-purple-900/40 text-purple-400/60 hover:border-purple-600/60 hover:text-purple-300 cursor-pointer"
                        title="Add Avatar to Scene"
                      >
                        <span>+ Avatar</span>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            {/* 3. Script / Text Track */}
            <div className="h-7 px-2 flex items-center gap-1.5 border-b border-[#131929]">
              {scenes.map((sc, idx) => {
                const isSelected = activeSceneIndex === idx;
                const widthPct = ((sc.duration || 5) / totalDuration) * 100;
                const hasScript = Boolean(sc.speech?.script);
                const sStart = Math.max(0, sc.speech?.start_time ?? 0);
                const sEnd = Math.min(sc.duration || 5, sc.speech?.end_time ?? (sc.duration || 5));
                const clipDur = Math.max(0.5, sEnd - sStart);
                const leftPct = (sStart / (sc.duration || 5)) * 100;
                const clipWidthPct = Math.max(10, (clipDur / (sc.duration || 5)) * 100);

                return (
                  <div
                    key={sc.id}
                    style={{ width: `${Math.max(12, widthPct)}%` }}
                    className="h-7 relative flex items-center"
                  >
                    {hasScript ? (
                      <div
                        onClick={() => setActiveSceneIndex(idx)}
                        style={{
                          left: `${leftPct}%`,
                          width: `${clipWidthPct}%`,
                        }}
                        className={`group absolute h-5.5 rounded text-[10px] px-2 flex items-center justify-between truncate cursor-pointer transition-all border ${
                          isSelected
                            ? "bg-emerald-600/40 border-emerald-400 text-emerald-100 font-semibold"
                            : "bg-emerald-950/40 border-emerald-900/60 text-emerald-300 hover:border-emerald-700"
                        }`}
                      >
                        {/* Left Edge Resize Handle */}
                        <div
                          className="absolute left-0 top-0 bottom-0 w-2.5 cursor-ew-resize opacity-0 group-hover:opacity-100 flex items-center justify-center hover:bg-emerald-400/40 rounded-l transition-opacity z-10"
                          onPointerDown={(e) => startResizeSpeech(e, idx, "left", "script")}
                          title="Drag left edge to resize script start time"
                        >
                          <div className="w-[2px] h-3 bg-emerald-300 rounded-full pointer-events-none" />
                        </div>

                        <span className="truncate mr-1">🔤 {sc.speech?.script || "No script"}</span>

                        <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity ml-1 shrink-0 z-20">
                          <button
                            type="button"
                            className="p-0.5 rounded hover:bg-white/20 text-emerald-200 hover:text-white"
                            title="Edit Script"
                            onClick={(e) => {
                              e.stopPropagation();
                              setActiveSceneIndex(idx);
                              setActiveLeftTool("scenes");
                              setActiveTab("scene");
                            }}
                          >
                            <Pencil size={10} />
                          </button>
                          <button
                            type="button"
                            className="p-0.5 rounded hover:bg-red-500/40 text-emerald-200 hover:text-red-200"
                            title="Clear Script"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDeleteScript(idx);
                            }}
                          >
                            <Trash2 size={10} />
                          </button>
                        </div>

                        {/* Right Edge Resize Handle */}
                        <div
                          className="absolute right-0 top-0 bottom-0 w-2.5 cursor-ew-resize opacity-0 group-hover:opacity-100 flex items-center justify-center hover:bg-emerald-400/40 rounded-r transition-opacity z-10"
                          onPointerDown={(e) => startResizeSpeech(e, idx, "right", "script")}
                          title="Drag right edge to resize script end time"
                        >
                          <div className="w-[2px] h-3 bg-emerald-300 rounded-full pointer-events-none" />
                        </div>
                      </div>
                    ) : (
                      <div
                        onClick={() => {
                          setActiveSceneIndex(idx);
                          setActiveLeftTool("scenes");
                          setActiveTab("scene");
                        }}
                        className="w-full h-5.5 rounded text-[10px] px-2 flex items-center justify-center border border-dashed border-emerald-900/40 text-emerald-400/60 hover:border-emerald-600/60 hover:text-emerald-300 cursor-pointer"
                        title="Add Script to Scene"
                      >
                        <span>+ Script</span>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            {/* 4. Speech Audio Track */}
            <div className="h-7 px-2 flex items-center gap-1.5">
              {scenes.map((sc, idx) => {
                const isSelected = activeSceneIndex === idx;
                const widthPct = ((sc.duration || 5) / totalDuration) * 100;
                const vObj = voices.find((v) => v.id === sc.speech?.voice_id);
                const hasVoiceOrAudio = Boolean(sc.speech?.voice_id || sc.speech?.audio_asset_id);
                const sStart = Math.max(0, sc.speech?.start_time ?? 0);
                const sEnd = Math.min(sc.duration || 5, sc.speech?.end_time ?? (sc.duration || 5));
                const clipDur = Math.max(0.5, sEnd - sStart);
                const leftPct = (sStart / (sc.duration || 5)) * 100;
                const clipWidthPct = Math.max(10, (clipDur / (sc.duration || 5)) * 100);

                return (
                  <div
                    key={sc.id}
                    style={{ width: `${Math.max(12, widthPct)}%` }}
                    className="h-7 relative flex items-center"
                  >
                    <div
                      onClick={() => setActiveSceneIndex(idx)}
                      style={{
                        left: `${leftPct}%`,
                        width: `${clipWidthPct}%`,
                      }}
                      className={`group absolute h-5.5 rounded text-[10px] px-2 flex items-center justify-between truncate cursor-pointer transition-all border ${
                        isSelected
                          ? "bg-indigo-600/40 border-indigo-400 text-indigo-100 font-semibold"
                          : "bg-indigo-950/40 border-indigo-900/60 text-indigo-300 hover:border-indigo-700"
                      }`}
                    >
                      {/* Left Edge Resize Handle */}
                      <div
                        className="absolute left-0 top-0 bottom-0 w-2.5 cursor-ew-resize opacity-0 group-hover:opacity-100 flex items-center justify-center hover:bg-indigo-400/40 rounded-l transition-opacity z-10"
                        onPointerDown={(e) => startResizeSpeech(e, idx, "left", "audio")}
                        title="Drag left edge to resize speech start time"
                      >
                        <div className="w-[2px] h-3 bg-indigo-300 rounded-full pointer-events-none" />
                      </div>

                      <div className="flex items-center gap-1 truncate mr-1">
                        <span className="truncate">🎙️ {vObj?.name || (hasVoiceOrAudio ? "Voice" : "No voice")}</span>
                        {sc.speech?.audio_asset_id && (
                          <span className="text-[8px] bg-indigo-500/30 text-indigo-200 px-1 rounded font-mono">
                            WAV
                          </span>
                        )}
                      </div>

                      <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity ml-1 shrink-0 z-20">
                        <button
                          type="button"
                          className="p-0.5 rounded hover:bg-white/20 text-indigo-200 hover:text-white"
                          title="Edit Voice & Speech"
                          onClick={(e) => {
                            e.stopPropagation();
                            setActiveSceneIndex(idx);
                            setActiveLeftTool("voice");
                            setActiveTab("voice");
                          }}
                        >
                          <Pencil size={10} />
                        </button>
                        {sc.speech?.audio_asset_id && (
                          <button
                            type="button"
                            className="p-0.5 rounded hover:bg-red-500/40 text-indigo-200 hover:text-red-200"
                            title="Clear Speech Audio"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDeleteSpeechAudio(idx);
                            }}
                          >
                            <Trash2 size={10} />
                          </button>
                        )}
                      </div>

                      {/* Right Edge Resize Handle */}
                      <div
                        className="absolute right-0 top-0 bottom-0 w-2.5 cursor-ew-resize opacity-0 group-hover:opacity-100 flex items-center justify-center hover:bg-indigo-400/40 rounded-r transition-opacity z-10"
                        onPointerDown={(e) => startResizeSpeech(e, idx, "right", "audio")}
                        title="Drag right edge to resize speech end time"
                      >
                        <div className="w-[2px] h-3 bg-indigo-300 rounded-full pointer-events-none" />
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* 5. Background Music Track */}
            <MusicTimelineTrack
              audioTracks={audioTracks}
              totalDuration={totalDuration}
              activeTrackId={activeAudioTrackId}
              playbackTime={activeSceneOffset + playbackTime}
              onSelectTrack={(id) => {
                setActiveAudioTrackId(id);
                setActiveLeftTool("music");
                setActiveTab("music");
              }}
              onOpenMusicPanel={() => {
                setActiveLeftTool("music");
                setActiveTab("music");
              }}
              onDeleteTrack={handleRemoveMusicTrack}
              onUpdateTiming={handleUpdateMusicTiming}
              onCommitTiming={handleCommitTiming}
            />

            {/* 6. Subtitles / Captions Track */}
            <CaptionTimelineTrack
              scenes={scenes}
              totalDuration={totalDuration}
              activeSceneIndex={activeSceneIndex}
              playbackTime={playbackTime}
              selectedCueId={selectedCueId}
              onSelectScene={(idx) => setActiveSceneIndex(idx)}
              onSelectCue={(cueId) => setSelectedCueId(cueId)}
              onOpenCaptionsPanel={() => {
                setActiveLeftTool("captions");
                setActiveTab("captions");
              }}
              onDeleteCue={handleDeleteCue}
              onUpdateCueTiming={handleUpdateCueTiming}
              onCommitCueTiming={handleCommitTiming}
            />

            {/* 7. Text Overlays Track */}
            <TextTimelineTrack
              scenes={scenes}
              totalDuration={totalDuration}
              activeSceneIndex={activeSceneIndex}
              playbackTime={playbackTime}
              selectedTextLayerId={selectedTextLayerId}
              selectedLayerIds={selectedLayerIds}
              onSelectScene={(idx) => setActiveSceneIndex(idx)}
              onSelectTextLayer={(id, isAdditive) => selectTextLayer(id, isAdditive)}
              onOpenTextPanel={() => {
                setActiveLeftTool("text");
                setActiveTab("text");
              }}
              onDeleteLayer={handleDeleteLayer}
              onUpdateTiming={handleUpdateLayerTiming}
              onCommitTiming={handleCommitTiming}
            />

            {/* 8. Visual Media Layers Track */}
            <MediaTimelineTrack
              scenes={scenes}
              totalDuration={totalDuration}
              activeSceneIndex={activeSceneIndex}
              playbackTime={playbackTime}
              selectedMediaLayerId={selectedMediaLayerId}
              selectedLayerIds={selectedLayerIds}
              onSelectScene={(idx) => setActiveSceneIndex(idx)}
              onSelectMediaLayer={(id, isAdditive) => {
                selectMediaLayer(id, isAdditive);
                setActiveLeftTool("media");
                setActiveTab("media");
              }}
              onOpenMediaPanel={() => {
                setActiveLeftTool("media");
                setActiveTab("media");
              }}
              onDeleteLayer={handleDeleteLayer}
              onUpdateTiming={handleUpdateLayerTiming}
              onCommitTiming={handleCommitTiming}
            />

            {/* 9. Elements & Shapes Track */}
            <ElementsTimelineTrack
              scenes={scenes}
              totalDuration={totalDuration}
              activeSceneIndex={activeSceneIndex}
              playbackTime={playbackTime}
              selectedElementLayerId={selectedElementLayerId}
              selectedLayerIds={selectedLayerIds}
              onSelectScene={(idx) => setActiveSceneIndex(idx)}
              onSelectElementLayer={(id, isAdditive) => {
                selectElementLayer(id, isAdditive);
                setActiveLeftTool("elements");
                setActiveTab("elements");
              }}
              onOpenElementsPanel={() => {
                setActiveLeftTool("elements");
                setActiveTab("elements");
              }}
              onDeleteLayer={handleDeleteLayer}
              onUpdateTiming={handleUpdateLayerTiming}
              onCommitTiming={handleCommitTiming}
            />
          </div>
        </div>
      </div>

      {/* Attach Asset / Upload Modal */}
      {isUploadModalOpen && (
        <AttachAssetModal
          isOpen={isUploadModalOpen}
          onClose={() => setIsUploadModalOpen(false)}
          onAttachAsset={(asset) => {
            if (uploadModalTarget === "music" || asset.type === "audio") {
              handleAddMusicTrack({ id: asset.id, name: asset.name });
            } else {
              showNotification("success", `Uploaded ${asset.name} to workspace media library.`);
            }
          }}
        />
      )}
    </div>
  );
}
