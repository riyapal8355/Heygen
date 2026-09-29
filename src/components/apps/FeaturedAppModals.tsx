

"use client";

import React, { useState } from "react";
import {
  X,
  Sparkles,
  Play,
  Film,
  Mic,
  Volume2,
  Sliders,
  Scissors,
  Layers,
  ArrowRight,
  Upload,
  Check,
  RefreshCw,
  Video,
} from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";

interface FeaturedAppModalsProps {
  activeModal: "generator" | "podcast" | "speech" | null;
  onClose: () => void;
  onOpenStudio?: (projectId?: string) => void;
}

export default function FeaturedAppModals({
  activeModal,
  onClose,
  onOpenStudio,
}: FeaturedAppModalsProps) {
  const { currentWorkspace } = useAuth();
  // 1. AI Video Generator State
  const [prompt, setPrompt] = useState(
    "A majestic Japanese Torii gate floating in tranquil ocean waters at golden hour sunset with gentle waves and cinematic lens flare, 4K resolution"
  );
  const [selectedStyle, setSelectedStyle] = useState("Cinematic Film");
  const [aspectRatio, setAspectRatio] = useState<"16:9" | "9:16" | "1:1">("16:9");
  const [cameraMotion, setCameraMotion] = useState("Drone Zoom Out");
  const [duration, setDuration] = useState("10s");
  const [isGenerating, setIsGenerating] = useState(false);

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

  if (!activeModal) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 backdrop-blur-md p-4 animate-in fade-in duration-200 select-none">
      {/* 1. AI VIDEO GENERATOR MODAL */}
      {activeModal === "generator" && (
        <div className="w-full max-w-2xl bg-[#0e1322] text-white rounded-3xl p-6 shadow-2xl border border-[#22304f] max-h-[90vh] overflow-y-auto">
          {/* Header */}
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
              className="text-slate-400 hover:text-white cursor-pointer"
            >
              <X size={18} />
            </button>
          </div>

          {/* Prompt Input */}
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

            {/* Visual Style Selection */}
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

            {/* Aspect Ratio & Camera Motion */}
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

          {/* Action Footer */}
          <div className="flex justify-between items-center mt-6 pt-4 border-t border-[#1c2742]">
            <span className="text-[11px] text-slate-400">
              Generates 10s 4K video • 25 credits
            </span>
            <div className="flex items-center gap-2.5">
              <button
                onClick={onClose}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:bg-[#18233a] cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  alert(
                    "GPU_UNAVAILABLE: Text-to-Video generation requires NVIDIA CUDA hardware (CUDA VALIDATION PENDING). Current host is AMD Ryzen CPU-only. Mock generation is disabled."
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
        <div className="w-full max-w-2xl bg-[#0e1322] text-white rounded-3xl p-6 shadow-2xl border border-[#22304f] max-h-[90vh] overflow-y-auto">
          {/* Header */}
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
              className="text-slate-400 hover:text-white cursor-pointer"
            >
              <X size={18} />
            </button>
          </div>

          <div className="space-y-4">
            {/* Multi-Speaker Selection */}
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

            {/* Layout Mode */}
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

            {/* Podcast Backdrop */}
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

            {/* Script Dialogue */}
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

          {/* Action Footer */}
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
        <div className="w-full max-w-xl bg-[#0e1322] text-white rounded-3xl p-6 shadow-2xl border border-[#22304f] max-h-[90vh] overflow-y-auto">
          {/* Header */}
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
              className="text-slate-400 hover:text-white cursor-pointer"
            >
              <X size={18} />
            </button>
          </div>

          {/* Interactive Waveform Audio Visualizer */}
          <div className="bg-[#121828] border border-[#202c49] rounded-2xl p-4 mb-5">
            <div className="flex items-center justify-between mb-3 text-xs">
              <span className="font-bold text-white">Audio Preview</span>
              {/* Before / After Switcher */}
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

            {/* Fake Sound Waveform Bars */}
            <div className="h-16 flex items-center justify-between gap-1 px-2">
              {Array.from({ length: 36 }).map((_, i) => {
                const height = audioMode === "after"
                  ? Math.sin(i * 0.4) * 30 + 35
                  : (Math.sin(i * 0.4) * 20 + 25) + (i % 2 === 0 ? 15 : 5);
                return (
                  <div
                    key={i}
                    style={{ height: `${height}%` }}
                    className={`w-1 rounded-full transition-all duration-300 ${
                      audioMode === "after"
                        ? "bg-gradient-to-t from-yellow-500 to-amber-300 shadow-sm shadow-yellow-500/30"
                        : "bg-slate-600"
                    }`}
                  ></div>
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

          {/* 4 Enhancement Toggles */}
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
                  <div className="w-4 h-4 rounded-full bg-slate-950 shadow-sm"></div>
                </div>
              </div>
            ))}
          </div>

          {/* Action Footer */}
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
    </div>
  );
}
