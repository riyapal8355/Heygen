"use client";

import React from "react";
import {
  ArrowLeft,
  Video,
  Play,
  Clock,
  Sparkles,
  ExternalLink,
} from "lucide-react";
import AskRhysWidget from "../dashboard/AskRhysWidget";

interface AppOutput {
  id: string;
  title: string;
  appName: string;
  createdAt: string;
  duration: string;
  thumbnail: string;
}

interface AllAppOutputsProps {
  onBack: () => void;
  onOpenStudio?: () => void;
}

export default function AllAppOutputs({ onBack, onOpenStudio }: AllAppOutputsProps) {
  // Empty state by default matching screenshot
  const outputs: AppOutput[] = [];

  return (
    <div className="flex-1 h-screen overflow-y-auto bg-[#07090e] text-slate-100 flex flex-col font-sans select-none relative">
      {/* 1. TOP HEADER (Exact Screenshot Match) */}
      <div className="w-full px-10 pt-7 pb-4 flex items-center justify-between border-b border-[#141b2c] z-20">
        <div className="flex items-center gap-3.5">
          {/* Back Button (Circle with Arrow) */}
          <button
            onClick={onBack}
            className="w-9 h-9 rounded-full border border-[#22304d] hover:bg-[#18233a] flex items-center justify-center text-slate-300 hover:text-white transition-colors cursor-pointer"
            title="Back to Apps"
          >
            <ArrowLeft size={16} />
          </button>

          <h1 className="text-2xl font-black text-white tracking-tight">
            All App Outputs
          </h1>
        </div>

        <AskRhysWidget />
      </div>

      {/* 2. MAIN EMPTY STATE AREA (Exact Screenshot Match) */}
      <div className="flex-1 flex flex-col items-center justify-center text-center p-8">
        {outputs.length === 0 ? (
          <div className="flex flex-col items-center max-w-sm">
            {/* Outlined Video Camera Icon (Exact Match) */}
            <div className="w-16 h-14 rounded-2xl border-2 border-slate-600 flex items-center justify-center text-slate-500 mb-4 relative">
              <Video size={28} className="stroke-[1.75]" />
            </div>

            <p className="text-sm font-semibold text-slate-400">
              No outputs yet
            </p>
          </div>
        ) : (
          <div className="max-w-7xl w-full mx-auto px-10 py-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {outputs.map((item) => (
              <div
                key={item.id}
                onClick={() => {
                  if (onOpenStudio) onOpenStudio();
                }}
                className="bg-[#0c111e] hover:bg-[#121828] border border-[#1c2740] rounded-3xl overflow-hidden cursor-pointer group transition-all"
              >
                <div className="aspect-[16/10] relative bg-slate-900 overflow-hidden">
                  <img
                    src={item.thumbnail}
                    alt={item.title}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform"
                  />
                  <span className="absolute bottom-2.5 right-2.5 bg-black/80 text-[10px] font-mono px-2 py-0.5 rounded text-white">
                    {item.duration}
                  </span>
                </div>
                <div className="p-4">
                  <h3 className="text-xs font-bold text-white group-hover:text-cyan-400">
                    {item.title}
                  </h3>
                  <div className="flex items-center justify-between text-[11px] text-slate-400 mt-1">
                    <span>{item.appName}</span>
                    <span>{item.createdAt}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
