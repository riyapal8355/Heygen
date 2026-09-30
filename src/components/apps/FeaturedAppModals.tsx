"use client";

import React, { useState } from "react";
import {
  X,
  Sparkles,
  Play,
  Film,
  Mic,
  Volume2,
  Scissors,
  Layers,
  ArrowRight,
  Upload,
  Check,
  Video,
  FileText,
  Camera,
  Maximize2,
  MousePointerClick,
  Sliders,
  User,
  Image as ImageIcon,
  Calendar,
} from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { VideoAgentGenerationContext } from "../create/VideoAgentWorkspace";

export type FeaturedModalType =
  | "generator"
  | "podcast"
  | "speech"
  | "pdf"
  | "shots"
  | "upscale"
  | "clipping"
  | "faceswap"
  | "interactive";

interface FeaturedAppModalsProps {
  activeModal: FeaturedModalType | null;
  onClose: () => void;
  onOpenStudio?: (projectId?: string) => void;
  onLaunchVideoAgentWithContext?: (context: VideoAgentGenerationContext) => void;
}

export default function FeaturedAppModals({
  activeModal,
  onClose,
  onOpenStudio,
  onLaunchVideoAgentWithContext,
}: FeaturedAppModalsProps) {
  const { currentWorkspace } = useAuth();

  // 1. AI Video Generator State
  const [prompt, setPrompt] = useState(
    "A majestic Japanese Torii gate floating in tranquil ocean waters at golden hour sunset with gentle waves and cinematic lens flare, 4K resolution"
  );
  const [selectedStyle, setSelectedStyle] = useState("Cinematic Film");
  const [aspectRatio, setAspectRatio] = useState<"16:9" | "9:16" | "1:1">("16:9");
  const [cameraMotion, setCameraMotion] = useState("Drone Zoom Out");
  const [generatorGpuNotice, setGeneratorGpuNotice] = useState<string | null>(null);

  // 2. Video Podcast State
  const [podcastLayout, setPodcastLayout] = useState<"split" | "active_speaker" | "pip">("split");
  const [hostName, setHostName] = useState("Riya (Tech Host)");
  const [guestName, setGuestName] = useState("Alex (AI Researcher)");
  const [studioBackdrop, setStudioBackdrop] = useState("Neon Loft Staircase");
  const [dialogue, setDialogue] = useState(
    "Host: Welcome back to the Future of AI. Today we are diving into video synthesis models.\nGuest: Thanks for having me Riya! The evolution over the past 12 months has been staggering."
  );

  // 3. Speech Cleanup State
  const [removeHum, setRemoveHum] = useState(true);
  const [removeFillers, setRemoveFillers] = useState(true);
  const [broadcastWarmth, setBroadcastWarmth] = useState(true);
  const [removePauses, setRemovePauses] = useState(true);
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);
  const [audioMode, setAudioMode] = useState<"before" | "after">("after");

  // 4. PPT/PDF to Video State
  const [selectedDocName, setSelectedDocName] = useState("Q3_Product_Roadmap.pdf");
  const [docSlideCount, setDocSlideCount] = useState(8);
  const [docLayoutPreset, setDocLayoutPreset] = useState("Side-by-Side Presentation");
  const [docPresenter, setDocPresenter] = useState("Annie (Studio Presenter)");
  const [docPrompt, setDocPrompt] = useState(
    "Create an executive product presentation highlighting our quarterly milestones, roadmap architecture, and strategic growth drivers."
  );

  // 5. Cinematic Shots State
  const [cinematicShotType, setCinematicShotType] = useState("Over-the-Shoulder Dialogue Cut");
  const [cinematicCameraMotion, setCinematicCameraMotion] = useState("Slow Push-In Dolly");
  const [cinematicLighting, setCinematicLighting] = useState("Golden Hour Cinematic 35mm");
  const [cinematicLens, setCinematicLens] = useState("50mm Prime F/1.4");
  const [cinematicPrompt, setCinematicPrompt] = useState(
    "Dramatic cinematic scene with high production value, shallow depth of field, and expressive camera movement."
  );

  // 6. Upscale Video State
  const [upscaleModel, setUpscaleModel] = useState("Neural Face Detail Restore");
  const [upscaleTargetRes, setUpscaleTargetRes] = useState("4K UHD (3840x2160)");
  const [temporalSmoothing, setTemporalSmoothing] = useState(true);

  // 7. AI Clipping State
  const [clipViralityFocus, setClipViralityFocus] = useState("Key Insights & Takeaways");
  const [clipAspectRatio, setClipAspectRatio] = useState<"9:16" | "1:1">("9:16");
  const [clipCaptionStyle, setClipCaptionStyle] = useState("Animated Dynamic Word-by-Word");

  // 8. Face Swap State
  const [faceSwapTargetAvatar, setFaceSwapTargetAvatar] = useState("Daniel (Executive)");
  const [faceMatchTolerance, setFaceMatchTolerance] = useState(85);
  const [preserveOriginalLighting, setPreserveOriginalLighting] = useState(true);

  // 9. Interactive Video State
  const [interactionType, setInteractionType] = useState("Branching Choice (Two Pathways)");
  const [ctaButtonLabel, setCtaButtonLabel] = useState("Explore Enterprise Demo");
  const [interactionTimestamp, setInteractionTimestamp] = useState("00:15");

  if (!activeModal) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 backdrop-blur-md p-4 animate-in fade-in duration-200 select-none"
    >
      {/* 1. AI VIDEO GENERATOR MODAL */}
      {activeModal === "generator" && (
        <div
          id="modal-generator"
          data-testid="modal-generator"
          className="w-full max-w-2xl bg-[#0e1322] text-white rounded-3xl p-6 shadow-2xl border border-[#22304f] max-h-[90vh] overflow-y-auto"
        >
          <div className="flex items-center justify-between pb-4 border-b border-[#1c2742] mb-5">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-amber-500 to-orange-500 flex items-center justify-center text-white shadow-md">
                <Sparkles size={20} />
              </div>
              <div>
                <h3 className="text-lg font-black text-white">AI Video Generator</h3>
                <p className="text-xs text-slate-400">
                  Transform prompts into cinematic B-roll scenes and dynamic backgrounds
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              aria-label="Close modal"
              className="text-slate-400 hover:text-white cursor-pointer"
            >
              <X size={18} />
            </button>
          </div>

          <div className="space-y-4">
            <div>
              <label className="text-xs font-bold text-slate-300 block mb-1.5">
                Video Prompt Description
              </label>
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                rows={3}
                className="w-full bg-[#121828] border border-[#202c49] rounded-2xl p-3.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-amber-400 resize-none leading-relaxed"
                placeholder="Describe your scene in detail..."
              />
            </div>

            <div>
              <label className="text-xs font-bold text-slate-300 block mb-1.5">
                Visual Aesthetic & Style
              </label>
              <div className="grid grid-cols-3 gap-2">
                {[
                  "Cinematic Film",
                  "Anime / Studio Ghibli",
                  "Hyperrealistic 3D",
                  "Cyberpunk Neon",
                  "Documentary Nature",
                  "Vintage 35mm",
                ].map((style) => (
                  <button
                    key={style}
                    onClick={() => setSelectedStyle(style)}
                    className={`py-2 px-3 rounded-xl text-xs font-semibold border transition-all text-center cursor-pointer ${
                      selectedStyle === style
                        ? "bg-amber-500/20 text-amber-300 border-amber-500 shadow-sm"
                        : "bg-[#121828] text-slate-400 border-[#202c49] hover:text-white"
                    }`}
                  >
                    {style}
                  </button>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-bold text-slate-300 block mb-1.5">
                  Aspect Ratio
                </label>
                <div className="flex gap-2">
                  {(["16:9", "9:16", "1:1"] as const).map((ratio) => (
                    <button
                      key={ratio}
                      onClick={() => setAspectRatio(ratio)}
                      className={`flex-1 py-1.5 rounded-xl text-xs font-bold border transition-colors cursor-pointer ${
                        aspectRatio === ratio
                          ? "bg-amber-500/20 text-amber-300 border-amber-500"
                          : "bg-[#121828] text-slate-400 border-[#202c49]"
                      }`}
                    >
                      {ratio}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="text-xs font-bold text-slate-300 block mb-1.5">
                  Camera Motion
                </label>
                <select
                  value={cameraMotion}
                  onChange={(e) => setCameraMotion(e.target.value)}
                  className="w-full bg-[#121828] border border-[#202c49] rounded-xl px-3 py-1.5 text-xs text-white focus:outline-none cursor-pointer"
                >
                  <option>Drone Zoom Out</option>
                  <option>Slow Pan Right</option>
                  <option>Orbit 360 Dynamic</option>
                  <option>Static Tripod Crisp</option>
                  <option>FPV Fast Flythrough</option>
                </select>
              </div>
            </div>
          </div>

          {generatorGpuNotice && (
            <div
              id="generator-gpu-required-notice"
              data-testid="generator-gpu-required-notice"
              className="mt-4 p-3 rounded-2xl bg-amber-500/15 border border-amber-500/40 text-amber-300 text-xs flex items-center gap-2 animate-in fade-in"
            >
              <span className="font-bold shrink-0">⚠️ GPU_REQUIRED:</span>
              <span>{generatorGpuNotice}</span>
            </div>
          )}

          <div className="flex justify-between items-center mt-6 pt-4 border-t border-[#1c2742]">
            <span className="text-[11px] text-slate-400">
              Generates 10s 4K video • 25 credits
            </span>
            <div className="flex items-center gap-2.5">
              <button
                onClick={() => {
                  setGeneratorGpuNotice(null);
                  onClose();
                }}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:bg-[#18233a] cursor-pointer"
              >
                Cancel
              </button>
              <button
                id="modal-generator-submit-btn"
                data-testid="modal-generator-submit-btn"
                onClick={() => {
                  setGeneratorGpuNotice(
                    "Local CUDA GPU unavailable. Text-to-Video generation requires NVIDIA CUDA hardware. Current host is AMD Ryzen CPU-only. Mock generation is disabled."
                  );
                }}
                className="px-5 py-2 bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-400 hover:to-orange-400 text-slate-950 text-xs font-extrabold rounded-xl shadow-md cursor-pointer flex items-center gap-1.5"
              >
                <Sparkles size={13} />
                <span>Generate Video Clip</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 2. VIDEO PODCAST STUDIO MODAL */}
      {activeModal === "podcast" && (
        <div
          id="modal-podcast"
          data-testid="modal-podcast"
          className="w-full max-w-2xl bg-[#0e1322] text-white rounded-3xl p-6 shadow-2xl border border-[#22304f] max-h-[90vh] overflow-y-auto"
        >
          <div className="flex items-center justify-between pb-4 border-b border-[#1c2742] mb-5">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center text-white shadow-md">
                <Mic size={20} />
              </div>
              <div>
                <h3 className="text-lg font-black text-white">Video Podcast Studio</h3>
                <p className="text-xs text-slate-400">
                  Generate multi-speaker video podcasts with automatic active-speaker cuts
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              aria-label="Close modal"
              className="text-slate-400 hover:text-white cursor-pointer"
            >
              <X size={18} />
            </button>
          </div>

          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-[#121828] border border-[#202c49] p-3 rounded-2xl">
                <span className="text-[10px] font-bold text-cyan-400 uppercase block mb-1">
                  Host 1 (Primary)
                </span>
                <input
                  type="text"
                  value={hostName}
                  onChange={(e) => setHostName(e.target.value)}
                  className="w-full bg-transparent text-xs font-bold text-white focus:outline-none border-b border-white/10 pb-1"
                />
              </div>

              <div className="bg-[#121828] border border-[#202c49] p-3 rounded-2xl">
                <span className="text-[10px] font-bold text-purple-400 uppercase block mb-1">
                  Guest 2 (Interviewee)
                </span>
                <input
                  type="text"
                  value={guestName}
                  onChange={(e) => setGuestName(e.target.value)}
                  className="w-full bg-transparent text-xs font-bold text-white focus:outline-none border-b border-white/10 pb-1"
                />
              </div>
            </div>

            <div>
              <label className="text-xs font-bold text-slate-300 block mb-1.5">
                Camera Layout Switching Mode
              </label>
              <div className="grid grid-cols-3 gap-2">
                {[
                  { id: "split", label: "Side-by-Side Split" },
                  { id: "active_speaker", label: "Active Speaker Focus" },
                  { id: "pip", label: "Picture-in-Picture" },
                ].map((mode) => (
                  <button
                    key={mode.id}
                    onClick={() => setPodcastLayout(mode.id as any)}
                    className={`py-2 px-3 rounded-xl text-xs font-semibold border transition-all text-center cursor-pointer ${
                      podcastLayout === mode.id
                        ? "bg-cyan-500/20 text-cyan-300 border-cyan-500"
                        : "bg-[#121828] text-slate-400 border-[#202c49] hover:text-white"
                    }`}
                  >
                    {mode.label}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="text-xs font-bold text-slate-300 block mb-1.5">
                Studio Set / Environment
              </label>
              <select
                value={studioBackdrop}
                onChange={(e) => setStudioBackdrop(e.target.value)}
                className="w-full bg-[#121828] border border-[#202c49] rounded-xl px-3 py-2 text-xs text-white focus:outline-none cursor-pointer"
              >
                <option>Neon Loft Staircase with Boom Mics</option>
                <option>Late Night High-End Talk Show</option>
                <option>Cozy Warm Bookshelf Lounge</option>
                <option>Silicon Valley Minimal Tech Studio</option>
              </select>
            </div>

            <div>
              <label className="text-xs font-bold text-slate-300 block mb-1.5">
                Podcast Script (Turns)
              </label>
              <textarea
                value={dialogue}
                onChange={(e) => setDialogue(e.target.value)}
                rows={4}
                className="w-full bg-[#121828] border border-[#202c49] rounded-2xl p-3 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-400 resize-none font-mono"
              />
            </div>
          </div>

          <div className="flex justify-between items-center mt-6 pt-4 border-t border-[#1c2742]">
            <span className="text-[11px] text-slate-400">
              Generates multi-cam video podcast • 30 credits
            </span>
            <div className="flex items-center gap-2.5">
              <button
                onClick={onClose}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:bg-[#18233a] cursor-pointer"
              >
                Cancel
              </button>
              <button
                id="modal-podcast-submit-btn"
                data-testid="modal-podcast-submit-btn"
                onClick={async () => {
                  if (!currentWorkspace?.id) {
                    alert("No active workspace found.");
                    return;
                  }
                  try {
                    const proj = await api.projects.create(currentWorkspace.id, {
                      title: `Podcast: ${hostName.slice(0, 24)}`,
                      aspect_ratio: "16:9",
                    });
                    onClose();
                    if (onOpenStudio) {
                      onOpenStudio(proj.id);
                    }
                  } catch (err: any) {
                    alert(err?.message || "Failed to create podcast project");
                  }
                }}
                className="px-5 py-2 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white text-xs font-bold rounded-xl shadow-md cursor-pointer flex items-center gap-1.5"
              >
                <Video size={13} />
                <span>Build Multi-Cam Podcast</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 3. SPEECH CLEANUP MODAL */}
      {activeModal === "speech" && (
        <div
          id="modal-speech"
          data-testid="modal-speech"
          className="w-full max-w-xl bg-[#0e1322] text-white rounded-3xl p-6 shadow-2xl border border-[#22304f] max-h-[90vh] overflow-y-auto"
        >
          <div className="flex items-center justify-between pb-4 border-b border-[#1c2742] mb-5">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-yellow-400 to-amber-500 flex items-center justify-center text-slate-950 shadow-md">
                <Volume2 size={20} />
              </div>
              <div>
                <h3 className="text-lg font-black text-white">Studio Speech Cleanup</h3>
                <p className="text-xs text-slate-400">
                  One-click neural audio enhancement: remove background noise & filler words
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              aria-label="Close modal"
              className="text-slate-400 hover:text-white cursor-pointer"
            >
              <X size={18} />
            </button>
          </div>

          <div className="bg-[#121828] border border-[#202c49] rounded-2xl p-4 mb-5">
            <div className="flex items-center justify-between mb-3 text-xs">
              <span className="font-bold text-white">Audio Preview</span>
              <div className="flex bg-[#0c111e] rounded-lg p-0.5 border border-[#1e2a44]">
                <button
                  onClick={() => setAudioMode("before")}
                  className={`px-2.5 py-1 rounded text-[11px] font-bold transition-all cursor-pointer ${
                    audioMode === "before"
                      ? "bg-slate-700 text-white"
                      : "text-slate-400 hover:text-white"
                  }`}
                >
                  Raw (Before)
                </button>
                <button
                  onClick={() => setAudioMode("after")}
                  className={`px-2.5 py-1 rounded text-[11px] font-bold transition-all cursor-pointer ${
                    audioMode === "after"
                      ? "bg-yellow-500 text-slate-950"
                      : "text-slate-400 hover:text-white"
                  }`}
                >
                  Cleaned (After)
                </button>
              </div>
            </div>

            <div className="h-16 flex items-center justify-between gap-1 px-2">
              {Array.from({ length: 36 }).map((_, i) => {
                const height =
                  audioMode === "after"
                    ? Math.sin(i * 0.4) * 30 + 35
                    : Math.sin(i * 0.4) * 20 + 25 + (i % 2 === 0 ? 15 : 5);
                return (
                  <div
                    key={i}
                    style={{ height: `${height}%` }}
                    className={`w-1 rounded-full transition-all duration-300 ${
                      audioMode === "after"
                        ? "bg-gradient-to-t from-yellow-500 to-amber-300 shadow-sm shadow-yellow-500/30"
                        : "bg-slate-600"
                    }`}
                  />
                );
              })}
            </div>

            <div className="flex items-center justify-between mt-3 pt-2 border-t border-[#1c2742] text-[11px] text-slate-400">
              <span>Duration: 00:45</span>
              <button
                onClick={() => setIsPlayingAudio(!isPlayingAudio)}
                className="font-bold text-yellow-400 hover:underline flex items-center gap-1 cursor-pointer"
              >
                <Play size={12} className={isPlayingAudio ? "fill-yellow-400" : ""} />
                <span>{isPlayingAudio ? "Pause Preview" : "Play Sample"}</span>
              </button>
            </div>
          </div>

          <div className="space-y-2.5">
            {[
              {
                title: "Remove Background Hum & Room Reverb",
                desc: "Eliminates fan noise, traffic rumble, and metallic echo",
                state: removeHum,
                toggle: () => setRemoveHum(!removeHum),
              },
              {
                title: "Auto-Cut Filler Words ('ums', 'uhs', 'likes')",
                desc: "Trims hesitation gaps while preserving natural conversational flow",
                state: removeFillers,
                toggle: () => setRemoveFillers(!removeFillers),
              },
              {
                title: "Broadcast Warmth & Voice EQ Mastering",
                desc: "Applies studio microphone proximity effect and compressor",
                state: broadcastWarmth,
                toggle: () => setBroadcastWarmth(!broadcastWarmth),
              },
              {
                title: "Trim Long Dead Pauses (>1.2s)",
                desc: "Shortens dead air for fast-paced, high-retention video pacing",
                state: removePauses,
                toggle: () => setRemovePauses(!removePauses),
              },
            ].map((feature) => (
              <div
                key={feature.title}
                onClick={feature.toggle}
                className="p-3 bg-[#121828] border border-[#202c49] hover:border-[#2f4066] rounded-2xl flex items-center justify-between cursor-pointer transition-colors"
              >
                <div>
                  <h4 className="text-xs font-bold text-white">{feature.title}</h4>
                  <p className="text-[10px] text-slate-400">{feature.desc}</p>
                </div>
                <div
                  className={`w-9 h-5 rounded-full transition-colors flex items-center p-0.5 ${
                    feature.state ? "bg-yellow-500 justify-end" : "bg-slate-700 justify-start"
                  }`}
                >
                  <div className="w-4 h-4 rounded-full bg-slate-950 shadow-sm" />
                </div>
              </div>
            ))}
          </div>

          <div className="flex justify-between items-center mt-6 pt-4 border-t border-[#1c2742]">
            <span className="text-[11px] text-slate-400">
              Lossless 48kHz WAV Export
            </span>
            <div className="flex items-center gap-2.5">
              <button
                onClick={onClose}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:bg-[#18233a] cursor-pointer"
              >
                Cancel
              </button>
              <button
                id="modal-speech-submit-btn"
                data-testid="modal-speech-submit-btn"
                onClick={async () => {
                  if (!currentWorkspace?.id) {
                    if (onOpenStudio) onOpenStudio();
                    onClose();
                    return;
                  }
                  try {
                    const proj = await api.projects.create(currentWorkspace.id, {
                      title: "Audio Cleanup Project",
                      aspect_ratio: "16:9",
                    });
                    onClose();
                    if (onOpenStudio) onOpenStudio(proj.id);
                  } catch (err: any) {
                    alert(err?.message || "Failed to create project");
                  }
                }}
                className="px-5 py-2 bg-gradient-to-r from-yellow-400 to-amber-500 hover:from-yellow-300 hover:to-amber-400 text-slate-950 text-xs font-extrabold rounded-xl shadow-md cursor-pointer flex items-center gap-1.5"
              >
                <Check size={13} className="stroke-[3]" />
                <span>Apply Cleanup to Project</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 4. PPT/PDF TO VIDEO WORKFLOW MODAL */}
      {activeModal === "pdf" && (
        <div
          id="modal-pdf"
          data-testid="modal-pdf"
          className="w-full max-w-2xl bg-[#0e1322] text-white rounded-3xl p-6 shadow-2xl border border-[#22304f] max-h-[90vh] overflow-y-auto"
        >
          <div className="flex items-center justify-between pb-4 border-b border-[#1c2742] mb-5">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-rose-500 to-pink-600 flex items-center justify-center text-white shadow-md">
                <FileText size={20} />
              </div>
              <div>
                <h3 className="text-lg font-black text-white">PPT/PDF to Video Converter</h3>
                <p className="text-xs text-slate-400">
                  Turn slide decks and documents into structured video scenes with avatar narration
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              aria-label="Close modal"
              className="text-slate-400 hover:text-white cursor-pointer"
            >
              <X size={18} />
            </button>
          </div>

          <div className="space-y-4">
            {/* Document Ingestion Card */}
            <div className="p-4 bg-[#121828] border border-[#202c49] rounded-2xl">
              <label className="text-xs font-bold text-slate-300 block mb-2">
                Active Slide Deck / Document
              </label>
              <div className="flex items-center justify-between p-3 bg-[#0a0f1d] border border-[#1b2640] rounded-xl">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-lg bg-rose-500/20 text-rose-400 flex items-center justify-center">
                    <FileText size={18} />
                  </div>
                  <div>
                    <h4 className="text-xs font-bold text-white">{selectedDocName}</h4>
                    <p className="text-[10px] text-slate-400">
                      {docSlideCount} slides parsed • Text and visual assets extracted
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => alert("Upload dialog: select PDF or PPTX deck.")}
                  className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs text-slate-200 cursor-pointer"
                >
                  Change Deck
                </button>
              </div>
            </div>

            {/* Slide-to-Video Layout Mode */}
            <div>
              <label className="text-xs font-bold text-slate-300 block mb-1.5">
                Presentation Layout Style
              </label>
              <div className="grid grid-cols-3 gap-2">
                {[
                  "Side-by-Side Presentation",
                  "Presenter Bubble in Corner",
                  "Full Slide Narration",
                ].map((preset) => (
                  <button
                    key={preset}
                    onClick={() => setDocLayoutPreset(preset)}
                    className={`py-2 px-3 rounded-xl text-xs font-semibold border transition-all text-center cursor-pointer ${
                      docLayoutPreset === preset
                        ? "bg-rose-500/20 text-rose-300 border-rose-500"
                        : "bg-[#121828] text-slate-400 border-[#202c49] hover:text-white"
                    }`}
                  >
                    {preset}
                  </button>
                ))}
              </div>
            </div>

            {/* Presenter Selection */}
            <div>
              <label className="text-xs font-bold text-slate-300 block mb-1.5">
                Avatar Presenter
              </label>
              <select
                value={docPresenter}
                onChange={(e) => setDocPresenter(e.target.value)}
                className="w-full bg-[#121828] border border-[#202c49] rounded-xl px-3 py-2 text-xs text-white focus:outline-none cursor-pointer"
              >
                <option>Annie (Studio Presenter)</option>
                <option>Daniel (Executive)</option>
                <option>Riya (Product Lead)</option>
                <option>Rasmus (Global Keynote)</option>
              </select>
            </div>

            {/* Presentation Prompt / Narrative Instructions */}
            <div>
              <label className="text-xs font-bold text-slate-300 block mb-1.5">
                Presentation Instructions & Creative Direction
              </label>
              <textarea
                id="modal-pdf-prompt-input"
                data-testid="modal-pdf-prompt-input"
                value={docPrompt}
                onChange={(e) => setDocPrompt(e.target.value)}
                rows={2}
                className="w-full bg-[#121828] border border-[#202c49] rounded-xl p-3 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-rose-400 resize-none leading-relaxed"
                placeholder="Describe key emphasis points, audience tone, or narrative focus..."
              />
            </div>
          </div>

          <div className="flex justify-between items-center mt-6 pt-4 border-t border-[#1c2742]">
            <span className="text-[11px] text-slate-400">
              Passes {docSlideCount} slides & configuration to Video Agent for timeline orchestration
            </span>
            <div className="flex items-center gap-2.5">
              <button
                onClick={onClose}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:bg-[#18233a] cursor-pointer"
              >
                Cancel
              </button>
              <button
                id="modal-pdf-submit-btn"
                data-testid="modal-pdf-submit-btn"
                onClick={() => {
                  const modalConfiguration = {
                    documentName: selectedDocName,
                    slideCount: docSlideCount,
                    layoutPreset: docLayoutPreset,
                    presenter: docPresenter,
                    aspectRatio: "16:9",
                  };
                  const attachment = {
                    name: selectedDocName,
                    type: selectedDocName.toLowerCase().endsWith(".pdf") ? "pdf" : "pptx",
                    slideCount: docSlideCount,
                    status: "attached",
                  };
                  const launchContext: VideoAgentGenerationContext = {
                    sourceApp: "ppt_pdf_to_video",
                    workflowIntent: "ppt_pdf_to_video",
                    workflowLabel: "PPT/PDF to Video",
                    modalConfiguration,
                    attachment,
                    userPrompt: docPrompt,
                    prompt: docPrompt,
                    target_duration_seconds: Math.max(15, docSlideCount * 5),
                  };
                  onClose();
                  if (onLaunchVideoAgentWithContext) {
                    onLaunchVideoAgentWithContext(launchContext);
                  }
                }}
                className="px-5 py-2 bg-gradient-to-r from-rose-500 to-pink-600 hover:from-rose-400 hover:to-pink-500 text-white text-xs font-bold rounded-xl shadow-md cursor-pointer flex items-center gap-1.5"
              >
                <FileText size={13} />
                <span>Build Presentation Video</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 5. CINEMATIC SHOTS WORKFLOW MODAL */}
      {activeModal === "shots" && (
        <div
          id="modal-shots"
          data-testid="modal-shots"
          className="w-full max-w-2xl bg-[#0e1322] text-white rounded-3xl p-6 shadow-2xl border border-[#22304f] max-h-[90vh] overflow-y-auto"
        >
          <div className="flex items-center justify-between pb-4 border-b border-[#1c2742] mb-5">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-violet-600 to-indigo-700 flex items-center justify-center text-white shadow-md">
                <Camera size={20} />
              </div>
              <div>
                <h3 className="text-lg font-black text-white">Cinematic Avatar Shots</h3>
                <p className="text-xs text-slate-400">
                  Configure Hollywood-grade camera angles, lenses, and lighting for high-production scenes
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              aria-label="Close modal"
              className="text-slate-400 hover:text-white cursor-pointer"
            >
              <X size={18} />
            </button>
          </div>

          <div className="space-y-4">
            <div>
              <label className="text-xs font-bold text-slate-300 block mb-1.5">
                Cinematic Framing & Shot Composition
              </label>
              <div className="grid grid-cols-2 gap-2">
                {[
                  "Over-the-Shoulder Dialogue Cut",
                  "Cinematic Medium Tracking",
                  "Dramatic Low-Angle Hero",
                  "Wide Establishing Dolly",
                ].map((shot) => (
                  <button
                    key={shot}
                    onClick={() => setCinematicShotType(shot)}
                    className={`py-2 px-3 rounded-xl text-xs font-semibold border transition-all text-left cursor-pointer ${
                      cinematicShotType === shot
                        ? "bg-violet-500/20 text-violet-300 border-violet-500"
                        : "bg-[#121828] text-slate-400 border-[#202c49] hover:text-white"
                    }`}
                  >
                    {shot}
                  </button>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-bold text-slate-300 block mb-1.5">
                  Camera Motion
                </label>
                <select
                  value={cinematicCameraMotion}
                  onChange={(e) => setCinematicCameraMotion(e.target.value)}
                  className="w-full bg-[#121828] border border-[#202c49] rounded-xl px-3 py-2 text-xs text-white focus:outline-none cursor-pointer"
                >
                  <option>Slow Push-In Dolly</option>
                  <option>Steadicam Follow</option>
                  <option>360 Orbital Tracking</option>
                  <option>Rack Focus 35mm</option>
                </select>
              </div>

              <div>
                <label className="text-xs font-bold text-slate-300 block mb-1.5">
                  Lens & Depth of Field
                </label>
                <select
                  value={cinematicLens}
                  onChange={(e) => setCinematicLens(e.target.value)}
                  className="w-full bg-[#121828] border border-[#202c49] rounded-xl px-3 py-2 text-xs text-white focus:outline-none cursor-pointer"
                >
                  <option>35mm Wide F/1.8 (Environmental)</option>
                  <option>50mm Prime F/1.4 (Standard Natural)</option>
                  <option>85mm Portrait F/1.2 (Bokeh Shallow)</option>
                </select>
              </div>
            </div>

            <div>
              <label className="text-xs font-bold text-slate-300 block mb-1.5">
                Lighting & Color Grade
              </label>
              <select
                value={cinematicLighting}
                onChange={(e) => setCinematicLighting(e.target.value)}
                className="w-full bg-[#121828] border border-[#202c49] rounded-xl px-3 py-2 text-xs text-white focus:outline-none cursor-pointer"
              >
                <option>Golden Hour Cinematic 35mm</option>
                <option>Cyberpunk Blue & Magenta</option>
                <option>Studio Softbox Commercial</option>
                <option>Moody Film Noir High-Contrast</option>
              </select>
            </div>

            {/* Cinematic Creative Prompt / Direction */}
            <div>
              <label className="text-xs font-bold text-slate-300 block mb-1.5">
                Cinematic Scene Prompt & Creative Direction
              </label>
              <textarea
                id="modal-shots-prompt-input"
                data-testid="modal-shots-prompt-input"
                value={cinematicPrompt}
                onChange={(e) => setCinematicPrompt(e.target.value)}
                rows={2}
                className="w-full bg-[#121828] border border-[#202c49] rounded-xl p-3 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-violet-400 resize-none leading-relaxed"
                placeholder="Describe camera framing, motion pacing, and dramatic atmosphere..."
              />
            </div>
          </div>

          <div className="flex justify-between items-center mt-6 pt-4 border-t border-[#1c2742]">
            <span className="text-[11px] text-slate-400">
              Passes cinematic configuration & prompt to Video Agent for scene orchestration
            </span>
            <div className="flex items-center gap-2.5">
              <button
                onClick={onClose}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:bg-[#18233a] cursor-pointer"
              >
                Cancel
              </button>
              <button
                id="modal-shots-submit-btn"
                data-testid="modal-shots-submit-btn"
                onClick={() => {
                  const modalConfiguration = {
                    shotType: cinematicShotType,
                    cameraMotion: cinematicCameraMotion,
                    lens: cinematicLens,
                    lighting: cinematicLighting,
                    aspectRatio: "16:9",
                  };
                  const launchContext: VideoAgentGenerationContext = {
                    sourceApp: "cinematic_shots",
                    workflowIntent: "cinematic_shots",
                    workflowLabel: "Cinematic Shots",
                    modalConfiguration,
                    userPrompt: cinematicPrompt,
                    prompt: cinematicPrompt,
                    target_duration_seconds: 30,
                  };
                  onClose();
                  if (onLaunchVideoAgentWithContext) {
                    onLaunchVideoAgentWithContext(launchContext);
                  }
                }}
                className="px-5 py-2 bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white text-xs font-bold rounded-xl shadow-md cursor-pointer flex items-center gap-1.5"
              >
                <Camera size={13} />
                <span>Build Cinematic Scene</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 6. UPSCALE VIDEO WORKFLOW MODAL */}
      {activeModal === "upscale" && (
        <div
          id="modal-upscale"
          data-testid="modal-upscale"
          className="w-full max-w-xl bg-[#0e1322] text-white rounded-3xl p-6 shadow-2xl border border-[#22304f] max-h-[90vh] overflow-y-auto"
        >
          <div className="flex items-center justify-between pb-4 border-b border-[#1c2742] mb-5">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-emerald-500 to-teal-600 flex items-center justify-center text-white shadow-md">
                <Maximize2 size={20} />
              </div>
              <div>
                <h3 className="text-lg font-black text-white">AI 4K Video Upscaler</h3>
                <p className="text-xs text-slate-400">
                  Restore and enhance videos to crystal-clear 4K resolution with neural sharpening
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              aria-label="Close modal"
              className="text-slate-400 hover:text-white cursor-pointer"
            >
              <X size={18} />
            </button>
          </div>

          <div className="space-y-4">
            <div>
              <label className="text-xs font-bold text-slate-300 block mb-1.5">
                Enhancement Engine
              </label>
              <div className="space-y-2">
                {[
                  {
                    name: "Neural Face Detail Restore",
                    desc: "Reconstructs lifelike eye, lip, and skin micro-textures on avatar closeups",
                  },
                  {
                    name: "ESRGAN 4K Super-Resolution",
                    desc: "Quadruples pixel density with neural edge preservation and anti-aliasing",
                  },
                  {
                    name: "Temporal 60fps Motion Interpolation",
                    desc: "Eliminates stutter by generating fluid in-between movement frames",
                  },
                ].map((engine) => (
                  <div
                    key={engine.name}
                    onClick={() => setUpscaleModel(engine.name)}
                    className={`p-3 rounded-xl border cursor-pointer transition-all ${
                      upscaleModel === engine.name
                        ? "bg-emerald-500/20 text-emerald-300 border-emerald-500"
                        : "bg-[#121828] text-slate-400 border-[#202c49] hover:text-white"
                    }`}
                  >
                    <h4 className="text-xs font-bold text-white">{engine.name}</h4>
                    <p className="text-[10px] text-slate-400 mt-0.5">{engine.desc}</p>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <label className="text-xs font-bold text-slate-300 block mb-1.5">
                Output Target Resolution
              </label>
              <select
                value={upscaleTargetRes}
                onChange={(e) => setUpscaleTargetRes(e.target.value)}
                className="w-full bg-[#121828] border border-[#202c49] rounded-xl px-3 py-2 text-xs text-white focus:outline-none cursor-pointer"
              >
                <option>4K UHD (3840x2160) - Broadcast Standard</option>
                <option>1440p QHD (2560x1440) - Web Optimized</option>
              </select>
            </div>
          </div>

          <div className="flex justify-between items-center mt-6 pt-4 border-t border-[#1c2742]">
            <span className="text-[11px] text-slate-400">
              Lossless ProRes / H.265 Export Available
            </span>
            <div className="flex items-center gap-2.5">
              <button
                onClick={onClose}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:bg-[#18233a] cursor-pointer"
              >
                Cancel
              </button>
              <button
                id="modal-upscale-submit-btn"
                data-testid="modal-upscale-submit-btn"
                onClick={async () => {
                  if (!currentWorkspace?.id) {
                    if (onOpenStudio) onOpenStudio();
                    onClose();
                    return;
                  }
                  try {
                    const proj = await api.projects.create(currentWorkspace.id, {
                      title: "4K Upscaled Project",
                      aspect_ratio: "16:9",
                      width: 3840,
                      height: 2160,
                    });
                    onClose();
                    if (onOpenStudio) onOpenStudio(proj.id);
                  } catch (err: any) {
                    alert(err?.message || "Failed to create upscaled project");
                  }
                }}
                className="px-5 py-2 bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 text-white text-xs font-bold rounded-xl shadow-md cursor-pointer flex items-center gap-1.5"
              >
                <Maximize2 size={13} />
                <span>Process 4K Upscale</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 7. AI CLIPPING WORKFLOW MODAL */}
      {activeModal === "clipping" && (
        <div
          id="modal-clipping"
          data-testid="modal-clipping"
          className="w-full max-w-xl bg-[#0e1322] text-white rounded-3xl p-6 shadow-2xl border border-[#22304f] max-h-[90vh] overflow-y-auto"
        >
          <div className="flex items-center justify-between pb-4 border-b border-[#1c2742] mb-5">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-fuchsia-500 to-purple-600 flex items-center justify-center text-white shadow-md">
                <Scissors size={20} />
              </div>
              <div>
                <h3 className="text-lg font-black text-white">Viral Shorts & Reels Clipper</h3>
                <p className="text-xs text-slate-400">
                  Upload webinars, podcasts, or recordings to extract high-performing 9:16 vertical clips
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              aria-label="Close modal"
              className="text-slate-400 hover:text-white cursor-pointer"
            >
              <X size={18} />
            </button>
          </div>

          <div className="space-y-4">
            <div>
              <label className="text-xs font-bold text-slate-300 block mb-1.5">
                Highlight Detection Strategy
              </label>
              <select
                value={clipViralityFocus}
                onChange={(e) => setClipViralityFocus(e.target.value)}
                className="w-full bg-[#121828] border border-[#202c49] rounded-xl px-3 py-2 text-xs text-white focus:outline-none cursor-pointer"
              >
                <option>Key Insights & Takeaways (Educational)</option>
                <option>Highest Emotional Intensity (Viral Hooks)</option>
                <option>Q&A Discussion Highlights (Interviews)</option>
                <option>Punchlines & Humorous Moments</option>
              </select>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-bold text-slate-300 block mb-1.5">
                  Output Format
                </label>
                <div className="flex gap-2">
                  <button
                    onClick={() => setClipAspectRatio("9:16")}
                    className={`flex-1 py-2 rounded-xl text-xs font-bold border transition-colors cursor-pointer ${
                      clipAspectRatio === "9:16"
                        ? "bg-fuchsia-500/20 text-fuchsia-300 border-fuchsia-500"
                        : "bg-[#121828] text-slate-400 border-[#202c49]"
                    }`}
                  >
                    9:16 Vertical
                  </button>
                  <button
                    onClick={() => setClipAspectRatio("1:1")}
                    className={`flex-1 py-2 rounded-xl text-xs font-bold border transition-colors cursor-pointer ${
                      clipAspectRatio === "1:1"
                        ? "bg-fuchsia-500/20 text-fuchsia-300 border-fuchsia-500"
                        : "bg-[#121828] text-slate-400 border-[#202c49]"
                    }`}
                  >
                    1:1 Square
                  </button>
                </div>
              </div>

              <div>
                <label className="text-xs font-bold text-slate-300 block mb-1.5">
                  Animated Caption Preset
                </label>
                <select
                  value={clipCaptionStyle}
                  onChange={(e) => setClipCaptionStyle(e.target.value)}
                  className="w-full bg-[#121828] border border-[#202c49] rounded-xl px-3 py-2 text-xs text-white focus:outline-none cursor-pointer"
                >
                  <option>Animated Dynamic Word-by-Word</option>
                  <option>Clean Yellow Subtitle Bar</option>
                  <option>Karaoke Neon Glow</option>
                </select>
              </div>
            </div>
          </div>

          <div className="flex justify-between items-center mt-6 pt-4 border-t border-[#1c2742]">
            <span className="text-[11px] text-slate-400">
              Generates 3-5 vertical short clips with captions
            </span>
            <div className="flex items-center gap-2.5">
              <button
                onClick={onClose}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:bg-[#18233a] cursor-pointer"
              >
                Cancel
              </button>
              <button
                id="modal-clipping-submit-btn"
                data-testid="modal-clipping-submit-btn"
                onClick={async () => {
                  if (!currentWorkspace?.id) {
                    if (onOpenStudio) onOpenStudio();
                    onClose();
                    return;
                  }
                  try {
                    const proj = await api.projects.create(currentWorkspace.id, {
                      title: "Viral Short Clip (9:16)",
                      aspect_ratio: clipAspectRatio,
                      width: clipAspectRatio === "9:16" ? 1080 : 1080,
                      height: clipAspectRatio === "9:16" ? 1920 : 1080,
                    });
                    onClose();
                    if (onOpenStudio) onOpenStudio(proj.id);
                  } catch (err: any) {
                    alert(err?.message || "Failed to create clip project");
                  }
                }}
                className="px-5 py-2 bg-gradient-to-r from-fuchsia-500 to-purple-600 hover:from-fuchsia-400 hover:to-purple-500 text-white text-xs font-bold rounded-xl shadow-md cursor-pointer flex items-center gap-1.5"
              >
                <Scissors size={13} />
                <span>Extract Viral Clips</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 8. AVATAR FACE SWAP WORKFLOW MODAL */}
      {activeModal === "faceswap" && (
        <div
          id="modal-faceswap"
          data-testid="modal-faceswap"
          className="w-full max-w-xl bg-[#0e1322] text-white rounded-3xl p-6 shadow-2xl border border-[#22304f] max-h-[90vh] overflow-y-auto"
        >
          <div className="flex items-center justify-between pb-4 border-b border-[#1c2742] mb-5">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-pink-500 to-rose-500 flex items-center justify-center text-white shadow-md">
                <Sparkles size={20} />
              </div>
              <div>
                <h3 className="text-lg font-black text-white">Avatar Face Swap Studio</h3>
                <p className="text-xs text-slate-400">
                  Swap your facial features onto video avatars with realistic lighting and angles
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              aria-label="Close modal"
              className="text-slate-400 hover:text-white cursor-pointer"
            >
              <X size={18} />
            </button>
          </div>

          <div className="space-y-4">
            <div className="p-3 bg-[#121828] border border-[#202c49] rounded-2xl flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-pink-500/20 text-pink-400 flex items-center justify-center font-bold">
                  IMG
                </div>
                <div>
                  <h4 className="text-xs font-bold text-white">Source Face Photo</h4>
                  <p className="text-[10px] text-slate-400">Front-facing portrait detected • 1024x1024</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => alert("Upload dialog: upload front-facing portrait photo.")}
                className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs text-slate-200 cursor-pointer"
              >
                Change Photo
              </button>
            </div>

            <div>
              <label className="text-xs font-bold text-slate-300 block mb-1.5">
                Target Avatar Body & Wardrobe
              </label>
              <select
                value={faceSwapTargetAvatar}
                onChange={(e) => setFaceSwapTargetAvatar(e.target.value)}
                className="w-full bg-[#121828] border border-[#202c49] rounded-xl px-3 py-2 text-xs text-white focus:outline-none cursor-pointer"
              >
                <option>Daniel (Executive Business Suit)</option>
                <option>Annie (Studio Blazer)</option>
                <option>Riya (Casual Tech)</option>
                <option>Rasmus (Keynote Speaker)</option>
              </select>
            </div>

            <div className="p-3 bg-[#121828] border border-[#202c49] rounded-2xl">
              <div className="flex justify-between items-center text-xs mb-1">
                <span className="font-bold text-white">Skin Tone & Lighting Blend</span>
                <span className="text-pink-400 font-bold">{faceMatchTolerance}%</span>
              </div>
              <input
                type="range"
                min={50}
                max={100}
                value={faceMatchTolerance}
                onChange={(e) => setFaceMatchTolerance(Number(e.target.value))}
                className="w-full cursor-pointer accent-pink-500"
              />
            </div>
          </div>

          <div className="flex justify-between items-center mt-6 pt-4 border-t border-[#1c2742]">
            <span className="text-[11px] text-slate-400">
              Seamless edge blending with photorealistic lighting
            </span>
            <div className="flex items-center gap-2.5">
              <button
                onClick={onClose}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:bg-[#18233a] cursor-pointer"
              >
                Cancel
              </button>
              <button
                id="modal-faceswap-submit-btn"
                data-testid="modal-faceswap-submit-btn"
                onClick={async () => {
                  if (!currentWorkspace?.id) {
                    if (onOpenStudio) onOpenStudio();
                    onClose();
                    return;
                  }
                  try {
                    const proj = await api.projects.create(currentWorkspace.id, {
                      title: "Face Swap Project",
                      aspect_ratio: "16:9",
                    });
                    onClose();
                    if (onOpenStudio) onOpenStudio(proj.id);
                  } catch (err: any) {
                    alert(err?.message || "Failed to create face swap project");
                  }
                }}
                className="px-5 py-2 bg-gradient-to-r from-pink-500 to-rose-500 hover:from-pink-400 hover:to-rose-400 text-white text-xs font-bold rounded-xl shadow-md cursor-pointer flex items-center gap-1.5"
              >
                <Sparkles size={13} />
                <span>Apply Face Swap</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 9. INTERACTIVE VIDEO FUNNEL WORKFLOW MODAL */}
      {activeModal === "interactive" && (
        <div
          id="modal-interactive"
          data-testid="modal-interactive"
          className="w-full max-w-xl bg-[#0e1322] text-white rounded-3xl p-6 shadow-2xl border border-[#22304f] max-h-[90vh] overflow-y-auto"
        >
          <div className="flex items-center justify-between pb-4 border-b border-[#1c2742] mb-5">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-cyan-500 to-purple-600 flex items-center justify-center text-white shadow-md">
                <MousePointerClick size={20} />
              </div>
              <div>
                <h3 className="text-lg font-black text-white">Branching Interactive Funnels</h3>
                <p className="text-xs text-slate-400">
                  Add interactive buttons, clickable cards, quiz questions, and booking embeds
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              aria-label="Close modal"
              className="text-slate-400 hover:text-white cursor-pointer"
            >
              <X size={18} />
            </button>
          </div>

          <div className="space-y-4">
            <div>
              <label className="text-xs font-bold text-slate-300 block mb-1.5">
                Interaction Overlay Format
              </label>
              <select
                value={interactionType}
                onChange={(e) => setInteractionType(e.target.value)}
                className="w-full bg-[#121828] border border-[#202c49] rounded-xl px-3 py-2 text-xs text-white focus:outline-none cursor-pointer"
              >
                <option>Branching Choice (Two Pathways)</option>
                <option>Clickable Product CTA Overlay</option>
                <option>Book Demo (Calendly / Form Embed)</option>
                <option>Quiz / Knowledge Check Interstitial</option>
              </select>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-bold text-slate-300 block mb-1.5">
                  CTA Button Label
                </label>
                <input
                  type="text"
                  value={ctaButtonLabel}
                  onChange={(e) => setCtaButtonLabel(e.target.value)}
                  className="w-full bg-[#121828] border border-[#202c49] rounded-xl px-3 py-2 text-xs text-white focus:outline-none"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-slate-300 block mb-1.5">
                  Overlay Trigger Time
                </label>
                <input
                  type="text"
                  value={interactionTimestamp}
                  onChange={(e) => setInteractionTimestamp(e.target.value)}
                  className="w-full bg-[#121828] border border-[#202c49] rounded-xl px-3 py-2 text-xs text-white focus:outline-none"
                />
              </div>
            </div>
          </div>

          <div className="flex justify-between items-center mt-6 pt-4 border-t border-[#1c2742]">
            <span className="text-[11px] text-slate-400">
              Interactive timeline layers render on playback
            </span>
            <div className="flex items-center gap-2.5">
              <button
                onClick={onClose}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:bg-[#18233a] cursor-pointer"
              >
                Cancel
              </button>
              <button
                id="modal-interactive-submit-btn"
                data-testid="modal-interactive-submit-btn"
                onClick={async () => {
                  if (!currentWorkspace?.id) {
                    if (onOpenStudio) onOpenStudio();
                    onClose();
                    return;
                  }
                  try {
                    const proj = await api.projects.create(currentWorkspace.id, {
                      title: "Interactive Video Funnel",
                      aspect_ratio: "16:9",
                    });
                    onClose();
                    if (onOpenStudio) onOpenStudio(proj.id);
                  } catch (err: any) {
                    alert(err?.message || "Failed to create interactive project");
                  }
                }}
                className="px-5 py-2 bg-gradient-to-r from-cyan-500 to-purple-600 hover:from-cyan-400 hover:to-purple-500 text-white text-xs font-bold rounded-xl shadow-md cursor-pointer flex items-center gap-1.5"
              >
                <MousePointerClick size={13} />
                <span>Build Interactive Video</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
