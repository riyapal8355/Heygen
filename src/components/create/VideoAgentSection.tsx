"use client";

import React from "react";
import {
  Sparkles,
  GraduationCap,
  Briefcase,
  Video,
  Home,
  LucideIcon,
} from "lucide-react";
import VideoAgentTemplateCard from "./VideoAgentTemplateCard";
import { VideoAgentSectionData, VideoAgentTemplate } from "./videoAgentData";

const iconMap: Record<string, LucideIcon> = {
  "section-personal-brand": Sparkles,
  "section-course-elearning": GraduationCap,
  "section-corporate-training": Briefcase,
  "section-creator-channels": Video,
  "section-real-estate": Home,
};

interface VideoAgentSectionProps {
  section: VideoAgentSectionData;
  onSelectTemplate: (template: VideoAgentTemplate) => void;
}

export default function VideoAgentSection({
  section,
  onSelectTemplate,
}: VideoAgentSectionProps) {
  const IconComponent = iconMap[section.id] || Sparkles;

  return (
    <section id={section.id} className="scroll-mt-32 pt-8 pb-4">
      {/* Section Header */}
      <div className="flex items-center gap-3 mb-5">
        <div className="w-8 h-8 rounded-full bg-cyan-500/15 border border-cyan-500/30 text-cyan-400 flex items-center justify-center flex-shrink-0 shadow-sm">
          <IconComponent size={16} strokeWidth={2.4} />
        </div>
        <h2 className="text-xl md:text-2xl font-black text-white tracking-tight">
          {section.title}
        </h2>
      </div>

      {/* 3-Column Template Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 md:gap-6">
        {section.templates.map((template) => (
          <VideoAgentTemplateCard
            key={template.id}
            template={template}
            onSelect={onSelectTemplate}
          />
        ))}
      </div>
    </section>
  );
}
