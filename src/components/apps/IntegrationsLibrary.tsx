"use client";

import React, { useState } from "react";
import {
  ExternalLink,
  Search,
  Check,
  X,
  Sparkles,
  ArrowRight,
  Plus,
} from "lucide-react";
import AskRhysWidget from "../dashboard/AskRhysWidget";

interface IntegrationItem {
  id: string;
  name: string;
  description: string;
  isNew?: boolean;
  category: string;
  logoBg: string;
  logoLetter?: string;
  logoSvg?: React.ReactNode;
}

const integrationsList: IntegrationItem[] = [
  // Row 1 (NEW)
  {
    id: "chatgpt",
    name: "ChatGPT App",
    description: "Generate video directly in ChatGPT.",
    isNew: true,
    category: "AI & Agents",
    logoBg: "bg-[#10A37F]",
    logoLetter: "GPT",
  },
  {
    id: "n8n",
    name: "n8n",
    description: "Build workflow automations with HeyGen in n8n....",
    isNew: true,
    category: "Automation",
    logoBg: "bg-[#EA4B71]",
    logoLetter: "n8n",
  },
  {
    id: "autohive",
    name: "Autohive",
    description: "Connect HeyGen with Autohive to add personalized ...",
    isNew: true,
    category: "AI & Agents",
    logoBg: "bg-[#FACC15] text-slate-950",
    logoLetter: "AH",
  },
  {
    id: "slack",
    name: "Slack",
    description: "Create videos from Slack conversations without switching...",
    isNew: true,
    category: "Communication",
    logoBg: "bg-[#4A154B]",
    logoLetter: "#",
  },
  // Row 2
  {
    id: "hubspot",
    name: "HubSpot",
    description: "Create and send personalized videos at scale. Sync with...",
    category: "CRM & Sales",
    logoBg: "bg-[#FF7A59]",
    logoLetter: "Hub",
  },
  {
    id: "vimeo",
    name: "Vimeo",
    description: "The Vimeo integration helps you centralize and...",
    category: "Hosting",
    logoBg: "bg-[#1AB7EA]",
    logoLetter: "v",
  },
  {
    id: "adobe_express",
    name: "Adobe Express Plugin",
    description: "Bring HeyGen into Adobe for seamless editing. Create...",
    category: "Design",
    logoBg: "bg-gradient-to-tr from-purple-600 via-pink-600 to-amber-500",
    logoLetter: "A",
  },
  {
    id: "canva",
    name: "Canva App",
    description: "Integrate HeyGen with Canva to power up designs....",
    category: "Design",
    logoBg: "bg-gradient-to-tr from-[#00C4CC] to-[#7D2AE8]",
    logoLetter: "Canva",
  },
  // Row 3
  {
    id: "tolstoy",
    name: "Tolstoy AI Video Player",
    description: "Embed HeyGen videos on sites, emails, or SMS....",
    category: "Video Player",
    logoBg: "bg-black",
    logoLetter: "Tolstoy",
  },
  {
    id: "trupeer",
    name: "Trupeer AI Screen Recorder",
    description: "Upgrade screen recordings with AI voiceovers and...",
    category: "Screen Recording",
    logoBg: "bg-slate-900",
    logoLetter: "[+]",
  },
  {
    id: "flowshare",
    name: "FlowShare",
    description: "Turn tasks into step-by-step guides instantly....",
    category: "Documentation",
    logoBg: "bg-[#002B49]",
    logoLetter: "FS",
  },
  {
    id: "mindstamp",
    name: "Mindstamp",
    description: "Add interactivity to your videos with buttons, quizzes,...",
    category: "Interactive",
    logoBg: "bg-[#4B2E83]",
    logoLetter: "P",
  },
  // Row 4
  {
    id: "repurpose",
    name: "Repurpose.io",
    description: "Turn your HeyGen video into a post and auto-share it...",
    category: "Social Media",
    logoBg: "bg-[#FF5A5F]",
    logoLetter: "R",
  },
  {
    id: "zapier",
    name: "Zapier",
    description: "Connect HeyGen to thousands of apps and automat...",
    category: "Automation",
    logoBg: "bg-[#FF4A00]",
    logoLetter: "*",
  },
  {
    id: "make",
    name: "Make",
    description: "Visually build automations for HeyGen videos....",
    category: "Automation",
    logoBg: "bg-[#6D28D9]",
    logoLetter: "M",
  },
  {
    id: "pabbly",
    name: "Pabbly",
    description: "Connect 2,000+ tools to automate video workflows....",
    category: "Automation",
    logoBg: "bg-[#00A86B]",
    logoLetter: "P",
  },
  // Row 5
  {
    id: "plainly",
    name: "Plainly Videos",
    description: "Auto-insert HeyGen videos into After Effects...",
    category: "Video Effects",
    logoBg: "bg-black",
    logoLetter: "plainly",
  },
  {
    id: "clay",
    name: "Clay",
    description: "Generate HeyGen videos with unique scripts. Pull data...",
    category: "Data Enrichment",
    logoBg: "bg-gradient-to-r from-sky-400 via-amber-400 to-rose-400 text-slate-950",
    logoLetter: "Clay",
  },
  {
    id: "hexus",
    name: "Hexus",
    description: "Add avatars to demos and guides with Hexus AI....",
    category: "Interactive",
    logoBg: "bg-[#1E293B]",
    logoLetter: "X",
  },
  {
    id: "viasocket",
    name: "viaSocket",
    description: "Automate processes across tools with this no-...",
    category: "Automation",
    logoBg: "bg-slate-800",
    logoLetter: ":)",
  },
];

interface IntegrationsLibraryProps {
  onOpenStudio?: () => void;
}

export default function IntegrationsLibrary({ onOpenStudio }: IntegrationsLibraryProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedIntegration, setSelectedIntegration] = useState<IntegrationItem | null>(null);
  const [connectedMap, setConnectedMap] = useState<{ [id: string]: boolean }>({
    chatgpt: true,
    slack: true,
  });

  const filteredIntegrations = integrationsList.filter(
    (item) =>
      item.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.description.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const toggleConnect = (id: string) => {
    setConnectedMap((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  return (
    <div className="flex-1 h-screen overflow-y-auto bg-[#07090e] text-slate-100 flex flex-col font-sans select-none relative">
      {/* 1. TOP HEADER (Exact Screenshot Match) */}
      <div className="w-full px-10 pt-7 pb-4 flex items-center justify-between border-b border-[#141b2c] z-20">
        <div>
          <h1 className="text-2xl md:text-3xl font-black text-white tracking-tight">
            Integrations
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Connect HeyGen with your favorite tools
          </p>
        </div>

        <AskRhysWidget />
      </div>

      {/* 2. MAIN 4-COLUMN INTEGRATIONS GRID (Exact Screenshot Match: 20 Cards) */}
      <div className="max-w-7xl w-full mx-auto px-10 py-6 flex-1 space-y-6 pb-20">
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {filteredIntegrations.map((item) => {
            const isConnected = connectedMap[item.id];
            return (
              <div
                key={item.id}
                onClick={() => setSelectedIntegration(item)}
                className="bg-[#0c111e] hover:bg-[#121828] border border-[#1c2740] hover:border-cyan-500/50 rounded-3xl p-4 flex flex-col justify-between transition-all duration-200 cursor-pointer group shadow-sm hover:shadow-xl hover:shadow-cyan-500/5 min-h-[170px]"
              >
                {/* Top Row: Logo + Badge + Arrow */}
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    {/* Logo Square */}
                    <div
                      className={`w-11 h-11 rounded-2xl ${item.logoBg} flex items-center justify-center font-black text-white text-xs shadow-md shrink-0 group-hover:scale-105 transition-transform`}
                    >
                      {item.logoLetter}
                    </div>

                    {/* Green NEW Badge if applicable */}
                    {item.isNew && (
                      <span className="bg-[#10B981] text-slate-950 font-black text-[9px] px-2 py-0.5 rounded-full uppercase tracking-wider shadow-sm">
                        NEW
                      </span>
                    )}
                  </div>

                  {/* External Arrow */}
                  <div className="w-7 h-7 rounded-full bg-[#151e33] border border-[#223152] flex items-center justify-center text-slate-400 group-hover:text-cyan-400 group-hover:border-cyan-500/40 transition-colors">
                    <ExternalLink size={12} />
                  </div>
                </div>

                {/* Name & Truncated Description */}
                <div>
                  <div className="flex items-center justify-between">
                    <h3 className="text-xs font-bold text-white group-hover:text-cyan-400 transition-colors truncate">
                      {item.name}
                    </h3>
                    {isConnected && (
                      <span className="text-[9px] font-bold text-emerald-400 flex items-center gap-0.5">
                        <Check size={10} /> Active
                      </span>
                    )}
                  </div>
                  <p className="text-[11px] text-slate-400 line-clamp-2 mt-1 leading-snug">
                    {item.description}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* INTEGRATION DETAIL & CONNECT MODAL */}
      {selectedIntegration && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4 animate-in fade-in duration-200">
          <div className="w-full max-w-md bg-[#0e1322] text-white rounded-3xl p-6 shadow-2xl border border-[#22304f]">
            <div className="flex items-center justify-between pb-3 border-b border-[#1c2742] mb-4">
              <div className="flex items-center gap-3">
                <div
                  className={`w-11 h-11 rounded-2xl ${selectedIntegration.logoBg} flex items-center justify-center font-black text-white text-xs shadow-md`}
                >
                  {selectedIntegration.logoLetter}
                </div>
                <div>
                  <h3 className="text-base font-bold text-white">
                    {selectedIntegration.name}
                  </h3>
                  <span className="text-[10px] uppercase font-bold text-cyan-400 tracking-wider">
                    {selectedIntegration.category}
                  </span>
                </div>
              </div>
              <button
                onClick={() => setSelectedIntegration(null)}
                className="text-slate-400 hover:text-white cursor-pointer"
              >
                <X size={18} />
              </button>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed mb-6">
              {selectedIntegration.description} Link your account to automate video generation pipelines, trigger webhook events, and export finished avatar renders directly to {selectedIntegration.name}.
            </p>

            <div className="space-y-3 bg-[#121828] border border-[#202c49] p-3.5 rounded-2xl mb-6">
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-400">Connection Status:</span>
                <span
                  className={`font-bold ${
                    connectedMap[selectedIntegration.id]
                      ? "text-emerald-400"
                      : "text-amber-400"
                  }`}
                >
                  {connectedMap[selectedIntegration.id] ? "Connected & Synchronized" : "Not Connected"}
                </span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-400">Webhook Triggers:</span>
                <span className="font-mono text-[11px] text-white">video.completed, scene.render</span>
              </div>
            </div>

            <div className="flex justify-end gap-2.5 pt-2 border-t border-[#1c2742]">
              <button
                onClick={() => setSelectedIntegration(null)}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:bg-[#18233a]"
              >
                Close
              </button>
              <button
                onClick={() => {
                  toggleConnect(selectedIntegration.id);
                  alert(
                    connectedMap[selectedIntegration.id]
                      ? `Disconnected from ${selectedIntegration.name}`
                      : `Successfully authenticated & linked ${selectedIntegration.name}!`
                  );
                }}
                className={`px-5 py-2 text-xs font-bold rounded-xl shadow-md cursor-pointer transition-all ${
                  connectedMap[selectedIntegration.id]
                    ? "bg-rose-500/20 text-rose-300 border border-rose-500/40 hover:bg-rose-500/30"
                    : "bg-gradient-to-r from-cyan-500 to-blue-600 text-white hover:from-cyan-400 hover:to-blue-500"
                }`}
              >
                {connectedMap[selectedIntegration.id] ? "Disconnect App" : "Connect Integration"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
