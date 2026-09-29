"use client";

import React from "react";
import { ArrowRight, Play, Sparkles } from "lucide-react";
import { VideoAgentTemplate } from "./videoAgentData";

interface VideoAgentTemplateCardProps {
  template: VideoAgentTemplate;
  onSelect: (template: VideoAgentTemplate) => void;
}

export default function VideoAgentTemplateCard({
  template,
  onSelect,
}: VideoAgentTemplateCardProps) {
  return (
    <div
      onClick={() => onSelect(template)}
      className="group relative aspect-[16/10] w-full rounded-2xl md:rounded-3xl overflow-hidden cursor-pointer shadow-lg hover:shadow-2xl hover:shadow-cyan-500/10 transition-all duration-300 border border-[#1B2940] hover:border-cyan-500/50 bg-[#0B111E] select-none"
    >
      {/* Background Image */}
      <img
        src={template.image}
        alt={template.title}
        className="w-full h-full object-cover object-center transform group-hover:scale-105 transition-transform duration-500 brightness-90 group-hover:brightness-95"
      />

      {/* Dark/Gradient Overlays to ensure strong text contrast and dark theme consistency */}
      <div className="absolute inset-0 bg-gradient-to-t from-[#0B111E] via-[#0B111E]/50 to-black/30 transition-opacity duration-300 group-hover:via-[#0B111E]/40"></div>
      
      {/* Top subtle duration badge */}
      {template.duration && (
        <div className="absolute top-3 right-3 opacity-80 group-hover:opacity-100 transition-opacity duration-200">
          <span className="bg-[#07090e]/80 backdrop-blur-md text-[11px] text-slate-300 px-2.5 py-0.5 rounded-full font-medium border border-[#1B2940]">
            {template.duration}
          </span>
        </div>
      )}

      {/* Content Overlay */}
      <div className="absolute inset-0 p-5 md:p-6 flex flex-col justify-between z-10">
        {/* Top: Large Bold Title */}
        <div>
          <h3 className="text-xl md:text-2xl font-black text-white tracking-tight leading-tight drop-shadow-md group-hover:text-cyan-200 transition-colors">
            {template.title}
          </h3>
          {template.description && (
            <p className="text-xs text-slate-400 mt-1 line-clamp-2 max-w-sm font-normal">
              {template.description}
            </p>
          )}
        </div>

        {/* Bottom CTA: "Create yours →" matching Home Primary CTA */}
        <div className="flex items-center justify-between pt-2">
          <button
            type="button"
            className="bg-gradient-to-r from-purple-600 to-indigo-600 group-hover:from-cyan-500 group-hover:to-blue-600 text-white group-hover:text-slate-950 text-xs font-bold px-3.5 py-1.5 rounded-full shadow-lg shadow-purple-900/40 group-hover:shadow-cyan-500/25 flex items-center gap-1.5 transition-all duration-200 group-hover:scale-105 cursor-pointer"
          >
            <span>Create yours</span>
            <ArrowRight
              size={13}
              className="transform group-hover:translate-x-0.5 transition-transform duration-200"
            />
          </button>

          {/* Floating subtle play icon on hover */}
          <div className="w-8 h-8 rounded-full bg-[#101827]/80 backdrop-blur-sm border border-[#1B2940] group-hover:border-cyan-500/50 text-cyan-400 flex items-center justify-center transition-all duration-300 shadow-md transform group-hover:scale-105 opacity-0 group-hover:opacity-100">
            <Play size={13} className="ml-0.5 fill-current" />
          </div>
        </div>
      </div>
    </div>
  );
}
