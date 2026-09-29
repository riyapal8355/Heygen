"use client";

import React, { useState } from "react";
import {
  X,
  Sparkles,
  ArrowUp,
  Play,
  Pause,
  Check,
  RotateCcw,
  Volume2,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";

interface DesignVoiceModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: (voiceName: string) => void;
}

const samplePrompts = [
  "An energetic but controlled voice, like a great presenter for a Silicon Valley tech launch.",
  "A soothing, warm female storyteller voice with a soft British cadence for bedtime tales.",
  "A bold, authoritative corporate narrator with clear Hindi and English articulation for business promos.",
  "A friendly, young and vibrant influencer voice for TikTok and Instagram Reels.",
];

export default function DesignVoiceModal({
  isOpen,
  onClose,
  onSuccess,
}: DesignVoiceModalProps) {
  const { currentWorkspace } = useAuth();
  const [prompt, setPrompt] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedVoice, setGeneratedVoice] = useState<{
    name: string;
    description: string;
    isPlaying: boolean;
  } | null>(null);

  if (!isOpen) return null;

  const handleTrySample = () => {
    const random = samplePrompts[Math.floor(Math.random() * samplePrompts.length)];
    setPrompt(random);
  };

  const handleGenerate = () => {
    if (!prompt.trim()) return;
    // Acoustic synthesis from prompt is unsupported in the backend.
    // Register custom voice profile metadata without fake setTimeout per Step 10.
    setGeneratedVoice({
      name: `Custom Voice (${prompt.slice(0, 24)}...)`,
      description: prompt,
      isPlaying: false,
    });
  };

  const togglePlay = () => {
    alert("Audio preview unavailable: Acoustic voice synthesis from prompt is unsupported in the backend.");
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-md p-4 animate-in fade-in duration-200 select-none">
      <div className="w-full max-w-2xl bg-white dark:bg-[#0e1322] text-slate-900 dark:text-white rounded-3xl p-7 shadow-2xl border border-slate-200 dark:border-[#22304f] relative overflow-hidden">
        {/* Header */}
        <div className="flex items-start justify-between mb-2">
          <div>
            <h2 className="text-xl font-bold tracking-tight">Design a voice</h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
              Adjust the prompt and regenerate voices until you find the perfect fit.
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-700 dark:hover:text-white p-1.5 rounded-full hover:bg-slate-100 dark:hover:bg-[#19243d] transition-colors cursor-pointer"
          >
            <X size={20} />
          </button>
        </div>

        {/* Prompt Card Container (Matches Screenshot 2) */}
        <div className="bg-slate-50 dark:bg-[#0a0e19] border border-slate-200 dark:border-[#1e2942] rounded-2xl p-5 mt-5 mb-5">
          <label className="text-xs font-bold text-slate-800 dark:text-slate-200 block mb-2">
            Describe your new voice
          </label>

          <div className="relative bg-white dark:bg-[#111728] border border-slate-200 dark:border-[#22304d] rounded-2xl p-4 focus-within:border-blue-500 transition-colors shadow-inner">
            <textarea
              rows={4}
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="e.g. an energetic but controlled voice, like a great presenter..."
              className="w-full bg-transparent text-xs text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none resize-none leading-relaxed"
            ></textarea>

            {/* Bottom bar inside textarea */}
            <div className="flex items-center justify-between pt-2 mt-1 border-t border-slate-100 dark:border-[#1a253d]">
              <button
                onClick={handleTrySample}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-slate-100 dark:bg-[#18233a] hover:bg-slate-200 dark:hover:bg-[#202e4c] text-[11px] font-semibold text-slate-700 dark:text-slate-300 transition-colors cursor-pointer"
              >
                <Sparkles size={12} className="text-purple-400" />
                <span>Try a sample</span>
              </button>

              <button
                onClick={handleGenerate}
                disabled={!prompt.trim() || isGenerating}
                className={`w-8 h-8 rounded-full flex items-center justify-center text-white transition-all cursor-pointer ${
                  prompt.trim() && !isGenerating
                    ? "bg-slate-900 hover:bg-slate-800 dark:bg-blue-600 dark:hover:bg-blue-500 shadow-md scale-105"
                    : "bg-slate-300 dark:bg-slate-700 text-slate-500 cursor-not-allowed"
                }`}
                title="Generate Voice"
              >
                <ArrowUp size={15} strokeWidth={2.5} />
              </button>
            </div>
          </div>
        </div>

        {/* Results Area */}
        {isGenerating ? (
          <div className="p-8 text-center flex flex-col items-center justify-center">
            <div className="w-10 h-10 rounded-full border-2 border-purple-500 border-t-transparent animate-spin mb-3"></div>
            <p className="text-xs font-semibold text-purple-400 animate-pulse">
              Synthesizing acoustic attributes and tone from prompt...
            </p>
          </div>
        ) : generatedVoice ? (
          <div className="bg-slate-50 dark:bg-[#0a0e1a] border border-blue-500/50 rounded-2xl p-4 flex items-center justify-between animate-in fade-in shadow-lg">
            <div className="flex items-center gap-3">
              <button
                onClick={togglePlay}
                className="w-10 h-10 rounded-full bg-purple-600 text-white flex items-center justify-center shadow-md cursor-pointer hover:bg-purple-500"
              >
                {generatedVoice.isPlaying ? <Pause size={15} /> : <Play size={15} className="ml-0.5 fill-white" />}
              </button>
              <div>
                <h4 className="text-xs font-bold text-slate-900 dark:text-white flex items-center gap-2">
                  {generatedVoice.name}
                  {generatedVoice.isPlaying && (
                    <span className="text-[10px] text-purple-400 flex items-center gap-1 font-mono">
                      <Volume2 size={12} className="animate-bounce" /> Playing...
                    </span>
                  )}
                </h4>
                <p className="text-[11px] text-slate-500 dark:text-slate-400 max-w-md truncate">
                  {generatedVoice.description}
                </p>
                <p className="text-[10px] text-amber-500 dark:text-amber-400 mt-0.5">
                  Acoustic synthesis from prompt is unsupported in backend (registers custom catalog profile).
                </p>
              </div>
            </div>

            <button
              onClick={async () => {
                try {
                  const created = await api.creative.createVoice(
                    {
                      name: generatedVoice.name,
                      description: generatedVoice.description,
                      voice_type: "custom",
                      language: "en",
                      provider: "piper",
                    },
                    currentWorkspace?.id
                  );
                  if (onSuccess) onSuccess(created.name);
                  alert(`Voice "${created.name}" registered to your voices library!`);
                  onClose();
                } catch (err) {
                  alert(err instanceof Error ? err.message : "Failed to register voice in workspace.");
                }
              }}
              className="px-4 py-2 bg-gradient-to-r from-purple-600 to-indigo-600 text-white text-xs font-bold rounded-xl shadow-md cursor-pointer flex items-center gap-1.5"
            >
              <Check size={13} /> Save Voice
            </button>
          </div>
        ) : (
          <div className="text-center py-6 text-xs text-slate-400 dark:text-slate-500">
            Please enter a prompt to design a voice.
          </div>
        )}
      </div>
    </div>
  );
}
