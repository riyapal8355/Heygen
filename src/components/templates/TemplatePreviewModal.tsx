"use client";

import React, { useState } from "react";
import {
  X,
  Play,
  Pause,
  ChevronLeft,
  ChevronRight,
  Clapperboard,
  Video,
} from "lucide-react";

export interface TemplateScene {
  id: string;
  sceneNumber: number;
  title: string;
  chapterBadge?: string;
  avatarImg: string;
  headline: string;
  subtitle: string;
  duration: string;
  type: "intro" | "kitchen" | "presentation" | "bullets" | "code" | "comparison" | "outro";
}

export interface VideoTemplate {
  id: string;
  title: string;
  category: string;
  aspectRatio: "16:9" | "9:16";
  totalDuration: string;
  scenesCount: number;
  thumbnail: string;
  scenes: TemplateScene[];
}

export const samplePromptCourseTemplate: VideoTemplate = {
  id: "template_prompt_course",
  title: "Prompt Engineering Course",
  category: "Learning & Development",
  aspectRatio: "16:9",
  totalDuration: "2:41",
  scenesCount: 9,
  thumbnail: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?q=80&w=700&auto=format&fit=crop",
  scenes: [
    {
      id: "s1",
      sceneNumber: 1,
      title: "Chapter 4: Role-Playing Technique",
      chapterBadge: "Chapter 4",
      avatarImg: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?q=80&w=700&auto=format&fit=crop",
      headline: "Getting Better Results with the Role-Playing Technique",
      subtitle: "The 4-stage system for domain-specific agent reasoning",
      duration: "0:24",
      type: "intro",
    },
    {
      id: "s2",
      sceneNumber: 2,
      title: "Kitchen Casual Discussion",
      chapterBadge: "Context",
      avatarImg: "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?q=80&w=700&auto=format&fit=crop",
      headline: "Establish Clear Roles & Constraints",
      subtitle: "Setting persona identity, knowledge domain, and style boundaries",
      duration: "0:18",
      type: "kitchen",
    },
    {
      id: "s3",
      sceneNumber: 3,
      title: "System Blueprint Slide",
      chapterBadge: "Blueprint",
      avatarImg: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?q=80&w=700&auto=format&fit=crop",
      headline: "The System Prompt Blueprint",
      subtitle: "Structuring role directives vs user task inputs",
      duration: "0:22",
      type: "presentation",
    },
    {
      id: "s4",
      sceneNumber: 4,
      title: "Four Crucial Directives",
      chapterBadge: "Pillars",
      avatarImg: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?q=80&w=700&auto=format&fit=crop",
      headline: "Four Crucial Directives",
      subtitle: "1. Persona  2. Context  3. Guardrails  4. Format",
      duration: "0:28",
      type: "bullets",
    },
    {
      id: "s5",
      sceneNumber: 5,
      title: "Zero-Shot Playground Demo",
      chapterBadge: "Demo",
      avatarImg: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?q=80&w=700&auto=format&fit=crop",
      headline: "Live Prompt Syntax Demo",
      subtitle: "Step-by-step token crafting in the interactive playground",
      duration: "0:30",
      type: "code",
    },
    {
      id: "s6",
      sceneNumber: 6,
      title: "Output Benchmark Comparison",
      chapterBadge: "Results",
      avatarImg: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?q=80&w=700&auto=format&fit=crop",
      headline: "Evaluating Model Output Quality",
      subtitle: "92% higher precision with role-context calibration",
      duration: "0:15",
      type: "comparison",
    },
    {
      id: "s7",
      sceneNumber: 7,
      title: "Chapter Takeaways",
      chapterBadge: "Summary",
      avatarImg: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?q=80&w=700&auto=format&fit=crop",
      headline: "Key Takeaways Checklist",
      subtitle: "Actionable summary to apply to production apps",
      duration: "0:14",
      type: "bullets",
    },
    {
      id: "s8",
      sceneNumber: 8,
      title: "Desk Hands-On Exercise",
      chapterBadge: "Exercise",
      avatarImg: "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?q=80&w=700&auto=format&fit=crop",
      headline: "Your Turn to Prompt",
      subtitle: "Interactive challenge for prompt optimization",
      duration: "0:20",
      type: "kitchen",
    },
    {
      id: "s9",
      sceneNumber: 9,
      title: "Next Lesson Preview",
      chapterBadge: "Outro",
      avatarImg: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?q=80&w=700&auto=format&fit=crop",
      headline: "Up Next: Few-Shot Prompting",
      subtitle: "See you in Chapter 5!",
      duration: "0:10",
      type: "outro",
    },
  ],
};

interface TemplatePreviewModalProps {
  template: VideoTemplate;
  onClose: () => void;
  onCreateFromTemplate: (template: VideoTemplate) => void;
}

export default function TemplatePreviewModal({
  template,
  onClose,
  onCreateFromTemplate,
}: TemplatePreviewModalProps) {
  const scenes = template?.scenes && template.scenes.length > 0 ? template.scenes : [
    {
      id: "s1",
      sceneNumber: 1,
      title: template?.title || "Scene 1",
      headline: template?.title || "Overview",
      subtitle: "Template Preview",
      duration: "0:10",
      avatarImg: template?.thumbnail || "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?q=80&w=700&auto=format&fit=crop",
      type: "intro" as const,
    }
  ];

  const [selectedSceneIndex, setSelectedSceneIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);

  const currentScene = scenes[selectedSceneIndex] || scenes[0];

  const handleNextScene = () => {
    if (selectedSceneIndex < scenes.length - 1) {
      setSelectedSceneIndex(selectedSceneIndex + 1);
    }
  };

  const handlePrevScene = () => {
    if (selectedSceneIndex > 0) {
      setSelectedSceneIndex(selectedSceneIndex - 1);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 backdrop-blur-md p-4 animate-in fade-in duration-200 select-none">
      <div className="w-full max-w-5xl bg-white text-slate-900 rounded-3xl p-6 shadow-2xl border border-slate-200 max-h-[95vh] overflow-y-auto flex flex-col justify-between">
        {/* 1. TOP TITLE & CLOSE (Exact Screenshot Match: Light modal with bold title) */}
        <div className="flex items-center justify-between pb-3 border-b border-slate-100 mb-4">
          <h2 className="text-lg font-extrabold text-slate-950 tracking-tight">
            {template.title}
          </h2>

          <button
            onClick={onClose}
            className="w-8 h-8 rounded-full hover:bg-slate-100 flex items-center justify-center text-slate-400 hover:text-slate-800 transition-colors cursor-pointer"
          >
            <X size={18} />
          </button>
        </div>

        {/* 2. MAIN VIDEO PLAYER CANVAS (Exact Screenshot Match) */}
        <div className="relative w-full aspect-[16/9] max-h-[390px] bg-[#12161f] rounded-2xl overflow-hidden shadow-xl flex items-center justify-center mx-auto mb-5 border border-slate-200">
          {/* Background Office Wood Wall */}
          <div className="absolute inset-0 bg-gradient-to-r from-slate-950 via-[#1b2234] to-[#121828] opacity-95"></div>

          {/* Left Text Overlay (Exact Screenshot Match) */}
          <div className="absolute left-8 top-10 bottom-16 max-w-md z-10 flex flex-col justify-center text-left">
            {currentScene.chapterBadge && (
              <span className="inline-block bg-[#FFD1DC] text-[#C2185B] text-[10px] font-bold px-2.5 py-0.5 rounded-full w-fit mb-3 shadow-xs">
                {currentScene.chapterBadge}
              </span>
            )}

            <h3 className="text-xl md:text-2xl font-black text-white tracking-tight leading-snug mb-2 drop-shadow-sm">
              {currentScene.headline}
            </h3>

            <p className="text-xs text-slate-300 leading-relaxed drop-shadow-sm">
              {currentScene.subtitle}
            </p>
          </div>

          {/* Right Avatar Portrait in Set (Exact Screenshot Match: Man in grey button shirt) */}
          <div className="absolute right-10 bottom-0 top-4 w-72 flex items-end justify-center z-10">
            <img
              src={currentScene.avatarImg}
              alt="Avatar Speaker"
              className="h-full object-cover object-top drop-shadow-2xl brightness-95"
            />
          </div>

          {/* Bottom Player Controls (Exact Screenshot Match: Play icon & 0:00 / 2:41) */}
          <div className="absolute bottom-0 left-0 right-0 p-4 bg-gradient-to-t from-black/90 via-black/40 to-transparent z-20 flex flex-col gap-1.5">
            {/* Scrubber Progress Bar */}
            <div className="w-full h-1 bg-white/20 rounded-full overflow-hidden relative cursor-pointer">
              <div
                style={{ width: `${((selectedSceneIndex + 1) / template.scenes.length) * 100}%` }}
                className="h-full bg-cyan-400 rounded-full transition-all duration-300"
              ></div>
            </div>

            <div className="flex items-center justify-between text-xs text-white pt-1">
              <div className="flex items-center gap-2.5">
                <button
                  onClick={() => setIsPlaying(!isPlaying)}
                  className="w-6 h-6 rounded-full bg-white/20 hover:bg-white/30 flex items-center justify-center cursor-pointer transition-colors"
                >
                  {isPlaying ? <Pause size={12} /> : <Play size={12} className="ml-0.5 fill-white" />}
                </button>
                <span className="text-[11px] font-mono text-slate-200">
                  0:00 / {template.totalDuration}
                </span>
              </div>

              <div className="text-[11px] text-slate-300">
                Scene {selectedSceneIndex + 1} of {template.scenes.length}
              </div>
            </div>
          </div>
        </div>

        {/* 3. MULTI-SCENE HORIZONTAL TIMELINE STRIP (Exact Screenshot Match) */}
        <div className="w-full relative mb-5">
          <div className="flex items-center gap-2.5 overflow-x-auto pb-2 pt-1 px-1 no-scrollbar">
            {template.scenes.map((scene, idx) => {
              const isSelected = selectedSceneIndex === idx;
              return (
                <div
                  key={scene.id}
                  onClick={() => setSelectedSceneIndex(idx)}
                  className={`shrink-0 w-28 aspect-[16/10] rounded-xl overflow-hidden relative border-2 cursor-pointer transition-all duration-200 group ${
                    isSelected
                      ? "border-cyan-500 shadow-md scale-105"
                      : "border-slate-200 hover:border-slate-400 opacity-80 hover:opacity-100"
                  }`}
                >
                  <img
                    src={scene.avatarImg}
                    alt={scene.title}
                    className="w-full h-full object-cover object-top"
                  />
                  <div className="absolute inset-0 bg-black/20 group-hover:bg-transparent transition-colors"></div>
                  <span className="absolute top-1 left-1 bg-black/70 text-[9px] font-mono px-1 rounded text-white font-bold">
                    {idx + 1}
                  </span>
                </div>
              );
            })}

            {/* Next / Prev Navigation Buttons */}
            <div className="flex items-center gap-1.5 pl-2">
              <button
                onClick={handlePrevScene}
                disabled={selectedSceneIndex === 0}
                className="w-8 h-8 rounded-full bg-slate-100 hover:bg-slate-200 flex items-center justify-center text-slate-700 disabled:opacity-40 cursor-pointer shadow-xs"
              >
                <ChevronLeft size={16} />
              </button>
              <button
                onClick={handleNextScene}
                disabled={selectedSceneIndex === template.scenes.length - 1}
                className="w-8 h-8 rounded-full bg-slate-100 hover:bg-slate-200 flex items-center justify-center text-slate-700 disabled:opacity-40 cursor-pointer shadow-xs"
              >
                <ChevronRight size={16} />
              </button>
            </div>
          </div>
        </div>

        {/* 4. PRIMARY CTA: CREATE FROM TEMPLATE (Exact Screenshot Match: Black pill button) */}
        <div className="flex justify-center pt-1">
          <button
            onClick={() => {
              onClose();
              onCreateFromTemplate(template);
            }}
            className="px-8 py-3 bg-slate-950 hover:bg-slate-800 text-white text-xs font-bold rounded-full shadow-lg hover:shadow-xl transition-all duration-300 cursor-pointer flex items-center gap-2 hover:scale-105"
          >
            <Clapperboard size={15} />
            <span>Create from Template</span>
          </button>
        </div>
      </div>
    </div>
  );
}
