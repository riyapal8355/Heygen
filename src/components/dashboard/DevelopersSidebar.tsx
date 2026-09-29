"use client";

import React from "react";
import { useTheme } from "@/context/ThemeContext";
import {
  Home,
  DollarSign,
  TrendingUp,
  Layers,
  Send,
  Link2,
  FileText,
  GitBranch,
  Terminal,
  Wand2,
  Clock,
  ExternalLink,
  PanelLeftClose,
  Sun,
  Moon,
} from "lucide-react";

interface DevelopersSidebarProps {
  activeSection: string;
  onSelectSection: (section: string) => void;
}

export default function DevelopersSidebar({
  activeSection,
  onSelectSection,
}: DevelopersSidebarProps) {
  const { theme, toggleTheme } = useTheme();
  const mainNav = [
    { id: "overview", label: "Overview", icon: Home },
    { id: "billing", label: "Billing", icon: DollarSign },
    { id: "usage", label: "Usage", icon: TrendingUp },
    { id: "models", label: "Models", icon: Layers },
    { id: "webhook", label: "Webhook", icon: Send },
    { id: "connections", label: "Connections", icon: Link2 },
  ];

  const externalLinks = [
    { label: "API Doc", icon: FileText, url: "https://docs.vidoai.com/api" },
    { label: "MCP", icon: GitBranch, url: "https://docs.vidoai.com/mcp" },
    { label: "CLI", icon: Terminal, url: "https://docs.vidoai.com/cli" },
    { label: "Skills", icon: Wand2, url: "https://docs.vidoai.com/skills" },
    { label: "Changelog", icon: Clock, url: "https://docs.vidoai.com/changelog" },
  ];

  const isLight = theme === "light";

  return (
    <aside className={`w-60 h-screen flex flex-col justify-between shrink-0 font-sans select-none z-20 overflow-y-auto transition-colors ${
      isLight ? "bg-white border-r border-slate-200" : "bg-[#0a0e17] border-r border-[#141b2c]"
    }`}>
      <div className="p-4 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-2 py-1 mb-4">
          <span className={`text-sm font-bold tracking-tight ${isLight ? "text-slate-900" : "text-white"}`}>Developers</span>
          <div className="flex items-center gap-1">
            <button
              onClick={toggleTheme}
              title={theme === "dark" ? "Switch to Light Mode" : "Switch to Dark Mode"}
              className={`transition-colors p-1.5 rounded-lg cursor-pointer ${
                isLight ? "text-slate-500 hover:text-amber-500 hover:bg-slate-100" : "text-slate-400 hover:text-amber-400 hover:bg-[#121828]"
              }`}
            >
              {theme === "dark" ? <Sun size={15} /> : <Moon size={15} className="text-indigo-600" />}
            </button>
            <button
              title="Collapse sidebar"
              className={`transition-colors p-1 rounded-lg cursor-pointer ${
                isLight ? "text-slate-400 hover:text-slate-900 hover:bg-slate-100" : "text-slate-400 hover:text-slate-200 hover:bg-[#121828]"
              }`}
            >
              <PanelLeftClose size={16} />
            </button>
          </div>
        </div>

        {/* Primary Navigation Items */}
        <nav className="space-y-1">
          {mainNav.map((item) => {
            const Icon = item.icon;
            const isActive = activeSection === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onSelectSection(item.id)}
                className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-semibold transition-all text-left cursor-pointer ${
                  isActive
                    ? isLight
                      ? "bg-[#eef4ff] text-blue-700 shadow-xs border border-blue-200/70"
                      : "bg-[#151f36] text-cyan-400 shadow-sm"
                    : isLight
                    ? "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                    : "text-slate-400 hover:bg-[#111728] hover:text-slate-200"
                }`}
              >
                <Icon size={16} className={`shrink-0 ${isActive && isLight ? "text-blue-600" : ""}`} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        {/* Divider Line */}
        <div className={`h-[1px] my-4 mx-2 ${isLight ? "bg-slate-200" : "bg-[#141b2c]"}`} />

        {/* External Developer Resources Links */}
        <div className="space-y-1">
          {externalLinks.map((link) => {
            const Icon = link.icon;
            const isApiDoc = link.label === "API Doc";
            const isMcp = link.label === "MCP";
            const isCli = link.label === "CLI";
            const isSkills = link.label === "Skills";
            const isChangelog = link.label === "Changelog";
            const isInternal = isApiDoc || isMcp || isCli || isSkills || isChangelog;
            const targetId = isApiDoc ? "api-doc" : isMcp ? "mcp" : isCli ? "cli" : isSkills ? "skills" : isChangelog ? "changelog" : "";
            const isActive = activeSection === targetId;

            return isInternal ? (
              <button
                key={link.label}
                onClick={() => onSelectSection(targetId)}
                className={`w-full flex items-center justify-between px-3.5 py-2 rounded-xl text-xs font-medium transition-colors group cursor-pointer ${
                  isActive
                    ? isLight
                      ? "bg-[#eef4ff] text-blue-700 font-semibold shadow-xs border border-blue-200/70"
                      : "bg-[#151f36] text-cyan-400 font-semibold shadow-sm"
                    : isLight
                    ? "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
                    : "text-slate-400 hover:text-white hover:bg-[#111728]"
                }`}
              >
                <div className="flex items-center gap-3 truncate">
                  <Icon size={15} className={`${isActive ? (isLight ? "text-blue-600" : "text-cyan-400") : isLight ? "text-slate-400 group-hover:text-blue-600" : "text-slate-500 group-hover:text-cyan-400"} shrink-0`} />
                  <span className="truncate">{link.label}</span>
                </div>
                <span className={`text-[10px] px-1.5 py-0.5 rounded border font-mono font-bold ${
                  isChangelog 
                    ? "bg-purple-500/10 text-purple-600 dark:text-purple-300 border-purple-500/30" 
                    : isLight
                    ? "bg-blue-50 text-blue-700 border-blue-200"
                    : "bg-cyan-500/10 text-cyan-400 border-cyan-500/20"
                }`}>
                  {isApiDoc ? "Quick Start" : isMcp ? "Protocol" : isCli ? "Terminal" : isSkills ? "AI Agent" : "v3.8 Live"}
                </span>
              </button>
            ) : (
              <a
                key={link.label}
                href={link.url}
                target="_blank"
                rel="noreferrer"
                className={`w-full flex items-center justify-between px-3.5 py-2 rounded-xl text-xs font-medium transition-colors group cursor-pointer ${
                  isLight
                    ? "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
                    : "text-slate-400 hover:text-white hover:bg-[#111728]"
                }`}
              >
                <div className="flex items-center gap-3 truncate">
                  <Icon size={15} className="text-slate-500 group-hover:text-cyan-400 shrink-0" />
                  <span className="truncate">{link.label}</span>
                </div>
                <ExternalLink size={13} className="text-slate-500 group-hover:text-cyan-400 shrink-0" />
              </a>
            );
          })}
        </div>
      </div>
    </aside>
  );
}
