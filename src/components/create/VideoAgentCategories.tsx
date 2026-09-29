"use client";

import React, { useRef } from "react";
import { VIDEO_AGENT_CATEGORIES } from "./videoAgentData";

interface VideoAgentCategoriesProps {
  activeCategory: string;
  onSelectCategory: (categoryId: string, sectionId: string) => void;
}

export default function VideoAgentCategories({
  activeCategory,
  onSelectCategory,
}: VideoAgentCategoriesProps) {
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  const handleClick = (categoryId: string, sectionId: string) => {
    onSelectCategory(categoryId, sectionId);
    const element = document.getElementById(sectionId);
    if (element) {
      element.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  };

  return (
    <div className="w-full relative select-none mt-7 mb-2">
      {/* Category Tabs Strip */}
      <div
        ref={scrollContainerRef}
        className="flex items-center gap-2 overflow-x-auto pb-2 scrollbar-thin scrollbar-thumb-slate-800 scrollbar-track-transparent no-scrollbar sm:scrollbar"
        style={{ scrollBehavior: "smooth" }}
      >
        {VIDEO_AGENT_CATEGORIES.map((cat) => {
          const isActive = activeCategory === cat.id;
          return (
            <button
              key={cat.id}
              onClick={() => handleClick(cat.id, cat.sectionId)}
              className={`px-4 py-2 rounded-full text-xs md:text-sm font-semibold whitespace-nowrap transition-all duration-200 cursor-pointer flex-shrink-0 border ${
                isActive
                  ? "bg-[#0B111E] text-white border-cyan-500/80 shadow-[0_0_15px_rgba(6,182,212,0.25)] ring-1 ring-cyan-500/40"
                  : "bg-[#0B1220] text-[#94A3B8] hover:text-white hover:bg-[#101827] border-[#1B2940] hover:border-cyan-500/40 shadow-sm"
              }`}
            >
              {cat.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
