"use client";

import React, { useState } from "react";
import {
  Search,
  Sparkles,
  Play,
  ArrowRight,
  Filter,
  Check,
  ChevronDown,
} from "lucide-react";
import AskRhysWidget from "../dashboard/AskRhysWidget";

interface LookCardItem {
  id: string;
  name: string;
  badge: string;
  imageUrl: string;
  prompt: string;
}

const screenshotLooks: LookCardItem[] = [
  {
    id: "look_1",
    name: "Redhead Studio Anchor",
    badge: "Avatar V",
    imageUrl: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?q=80&w=800&auto=format&fit=crop",
    prompt: "Female presenter with red hair wearing camel blazer in a modern broadcast studio with blue accent light.",
  },
  {
    id: "look_2",
    name: "Alex - Podcast Streamer",
    badge: "Avatar IV",
    imageUrl: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?q=80&w=800&auto=format&fit=crop",
    prompt: "Man with beard in white hoodie seated at dynamic studio microphone in modern acoustic studio.",
  },
  {
    id: "look_3",
    name: "Riya - Creator Podcast",
    badge: "Avatar V",
    imageUrl: "https://images.unsplash.com/photo-1580489944761-15a19d654956?q=80&w=800&auto=format&fit=crop",
    prompt: "Woman in white denim top in warm studio with studio microphone and warm shelves.",
  },
  {
    id: "look_4",
    name: "Marcus - Skyline Executive",
    badge: "Avatar IV",
    imageUrl: "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?q=80&w=800&auto=format&fit=crop",
    prompt: "Man in navy blazer and open shirt in modern glass boardroom overlooking high-rise city skyline.",
  },
  {
    id: "look_5",
    name: "Sophia - Studio Presenter",
    badge: "Avatar IV",
    imageUrl: "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?q=80&w=800&auto=format&fit=crop",
    prompt: "Presenter in taupe blazer in newsroom studio with blurred screen.",
  },
  {
    id: "look_6",
    name: "Lucas - Blue Studio",
    badge: "Avatar IV",
    imageUrl: "https://images.unsplash.com/photo-1492562080023-ab3db95bfbce?q=80&w=800&auto=format&fit=crop",
    prompt: "Man in charcoal zip cardigan against sleek deep blue studio background.",
  },
  {
    id: "look_7",
    name: "Rachel - Boardroom Partner",
    badge: "Avatar IV",
    imageUrl: "https://images.unsplash.com/photo-1573497019940-1c28c88b4f3e?q=80&w=800&auto=format&fit=crop",
    prompt: "Woman with wavy red hair in dark suit in bright conference room.",
  },
  {
    id: "look_8",
    name: "Daniel - Studio Desk",
    badge: "Avatar IV",
    imageUrl: "https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?q=80&w=800&auto=format&fit=crop",
    prompt: "Man in dark shirt seated at light wood desk in natural warm light.",
  },
  {
    id: "look_9",
    name: "Elena - Financial District",
    badge: "Avatar IV",
    imageUrl: "https://images.unsplash.com/photo-1567532939604-b6b5b0db2604?q=80&w=800&auto=format&fit=crop",
    prompt: "Woman in grey blazer in modern high-rise skyscraper with natural light.",
  },
  {
    id: "look_10",
    name: "Arthur - Classic Library",
    badge: "Avatar IV",
    imageUrl: "https://images.unsplash.com/photo-1560250097-0b93528c311a?q=80&w=800&auto=format&fit=crop",
    prompt: "Man in classic navy suit and pocket square in warm wood library with classic desk lamp.",
  },
  {
    id: "look_11",
    name: "Night Skyline City",
    badge: "Avatar IV",
    imageUrl: "https://images.unsplash.com/photo-1544005313-94ddf0286df2?q=80&w=800&auto=format&fit=crop",
    prompt: "Woman in light grey suit in front of city skyline with night bokeh lights.",
  },
  {
    id: "look_12",
    name: "Victor - Skyline Architect",
    badge: "Avatar IV",
    imageUrl: "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?q=80&w=800&auto=format&fit=crop",
    prompt: "Man with glasses in charcoal suit with city skyline daylight backdrop.",
  },
  {
    id: "look_13",
    name: "Blonde Studio Casual",
    badge: "Avatar IV",
    imageUrl: "https://images.unsplash.com/photo-1531746020798-e6953c6e8e04?q=80&w=800&auto=format&fit=crop",
    prompt: "Woman in white shirt in warm bright loft studio with brick and timber accents.",
  },
  {
    id: "look_14",
    name: "Conference Stage Keynote",
    badge: "Avatar IV",
    imageUrl: "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?q=80&w=800&auto=format&fit=crop",
    prompt: "Man in tan blazer on conference stage with subtle stage lighting.",
  },
  {
    id: "look_15",
    name: "Clean White Shirt",
    badge: "Avatar IV",
    imageUrl: "https://images.unsplash.com/photo-1501196354995-cbb51c65aaea?q=80&w=800&auto=format&fit=crop",
    prompt: "Man in crisp white linen shirt in bright daylight setting.",
  },
  {
    id: "look_16",
    name: "Formal Executive Tie",
    badge: "Avatar IV",
    imageUrl: "https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?q=80&w=800&auto=format&fit=crop",
    prompt: "Man in dark suit and necktie in modern boardroom.",
  },
  {
    id: "look_17",
    name: "Nutrition & Kitchen Chef",
    badge: "Avatar IV",
    imageUrl: "https://images.unsplash.com/photo-1583394838336-acd977736f90?q=80&w=800&auto=format&fit=crop",
    prompt: "Woman at modern kitchen counter with fresh vegetables and fruits.",
  },
  {
    id: "look_18",
    name: "Industrial Turbine Plant",
    badge: "Avatar IV",
    imageUrl: "https://images.unsplash.com/photo-1504384308090-c894fdcc538d?q=80&w=800&auto=format&fit=crop",
    prompt: "Engineer in boiler suit, safety glasses, and white helmet in electrical plant.",
  },
  {
    id: "look_19",
    name: "Automotive Showroom Lead",
    badge: "Avatar IV",
    imageUrl: "https://images.unsplash.com/photo-1573496799652-408c2ac9fe98?q=80&w=800&auto=format&fit=crop",
    prompt: "Woman with glasses in front of luxury electric car showroom.",
  },
  {
    id: "look_20",
    name: "EV Presentation Screen",
    badge: "Avatar IV",
    imageUrl: "https://images.unsplash.com/photo-1580489944761-15a19d654956?q=80&w=800&auto=format&fit=crop",
    prompt: "Woman in navy suit in front of car presentation monitor.",
  },
  {
    id: "look_21",
    name: "Mechanic Garage Workshop",
    badge: "Avatar IV",
    imageUrl: "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?q=80&w=800&auto=format&fit=crop",
    prompt: "Technician in blue mechanics uniform in vehicle service garage with hydraulic lifts.",
  },
  {
    id: "look_22",
    name: "Dealership Executive",
    badge: "Avatar IV",
    imageUrl: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?q=80&w=800&auto=format&fit=crop",
    prompt: "Man in blue suit in front of modern showroom vehicle.",
  },
  {
    id: "look_23",
    name: "Auto Service Specialist",
    badge: "Avatar IV",
    imageUrl: "https://images.unsplash.com/photo-1573497019940-1c28c88b4f3e?q=80&w=800&auto=format&fit=crop",
    prompt: "Woman in blue mechanic overalls in service garage.",
  },
  {
    id: "look_24",
    name: "EV Mobility Manager",
    badge: "Avatar IV",
    imageUrl: "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?q=80&w=800&auto=format&fit=crop",
    prompt: "Man in light blue business shirt in modern automotive event.",
  },
  {
    id: "look_25",
    name: "Construction Site Supervisor",
    badge: "Avatar IV",
    imageUrl: "https://images.unsplash.com/photo-1504384308090-c894fdcc538d?q=80&w=800&auto=format&fit=crop",
    prompt: "Civil engineer in yellow hi-vis safety vest and white hard hat on construction site.",
  },
  {
    id: "look_26",
    name: "Warehouse Logistics Engineer",
    badge: "Avatar IV",
    imageUrl: "https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?q=80&w=800&auto=format&fit=crop",
    prompt: "Engineer in safety vest and hard hat in industrial logistics warehouse.",
  },
  {
    id: "look_27",
    name: "Residential Real Estate",
    badge: "Avatar IV",
    imageUrl: "https://images.unsplash.com/photo-1560250097-0b93528c311a?q=80&w=800&auto=format&fit=crop",
    prompt: "Real estate agent in green suit in front of suburban house with lawn.",
  },
  {
    id: "look_28",
    name: "Suburban Luxury Realtor",
    badge: "Avatar IV",
    imageUrl: "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?q=80&w=800&auto=format&fit=crop",
    prompt: "Realtor in navy blazer standing in front of two-story family home.",
  },
];

export default function DesignLookStudio({
  onOpenStudio,
}: {
  onOpenStudio?: () => void;
}) {
  const [activeSubTab, setActiveSubTab] = useState<"recently_used" | "all_looks" | "templates">("all_looks");
  const [searchQuery, setSearchQuery] = useState("");
  const [isPromptModalOpen, setIsPromptModalOpen] = useState(false);
  const [customPrompt, setCustomPrompt] = useState("");

  const filteredLooks = screenshotLooks.filter((item) =>
    item.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    item.prompt.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="flex-1 h-screen overflow-y-auto bg-[#07090e] text-slate-100 flex flex-col font-sans select-none">
      {/* 1. TOP BAR WITH TITLE & ASK RHYS */}
      <div className="w-full px-10 pt-7 pb-4 flex items-center justify-between z-20">
        <div>
          <h1 className="text-2xl md:text-3xl font-extrabold text-white tracking-tight">
            What new look are you imagining?
          </h1>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setIsPromptModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-cyan-500 via-blue-600 to-purple-600 hover:from-cyan-400 hover:to-purple-500 text-white text-xs font-bold rounded-full shadow-md shadow-blue-500/20 transition-all cursor-pointer"
          >
            <Sparkles size={14} />
            <span>Generate with AI</span>
          </button>

          <AskRhysWidget />
        </div>
      </div>

      {/* 2. SUB-TABS & SEARCH (Exact Match to Screenshot) */}
      <div className="max-w-6xl w-full mx-auto px-10 pt-1 pb-4">
        <div className="flex items-center justify-between border-b border-[#141b2c] pb-3">
          {/* Sub Tabs: Recently used / All looks */}
          <div className="flex items-center gap-6 text-xs font-bold">
            <button
              onClick={() => setActiveSubTab("recently_used")}
              className={`pb-1.5 transition-colors cursor-pointer relative ${
                activeSubTab === "recently_used"
                  ? "text-white"
                  : "text-slate-500 hover:text-slate-300"
              }`}
            >
              Recently used
              {activeSubTab === "recently_used" && (
                <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-cyan-400 rounded-full"></span>
              )}
            </button>

            <button
              onClick={() => setActiveSubTab("all_looks")}
              className={`pb-1.5 transition-colors cursor-pointer relative ${
                activeSubTab === "all_looks"
                  ? "text-white"
                  : "text-slate-500 hover:text-slate-300"
              }`}
            >
              All looks
              {activeSubTab === "all_looks" && (
                <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-cyan-400 rounded-full"></span>
              )}
            </button>

            <button
              onClick={() => setActiveSubTab("templates")}
              className={`pb-1.5 transition-colors cursor-pointer relative ${
                activeSubTab === "templates"
                  ? "text-white"
                  : "text-slate-500 hover:text-slate-300"
              }`}
            >
              Templates
              {activeSubTab === "templates" && (
                <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-cyan-400 rounded-full"></span>
              )}
            </button>
          </div>

          {/* Search Bar */}
          <div className="relative w-64">
            <Search size={13} className="absolute left-3 top-2.5 text-slate-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search looks..."
              className="w-full bg-[#111728] border border-[#1e2a44] rounded-full pl-8 pr-3 py-1.5 text-xs text-white placeholder-slate-400 focus:outline-none focus:border-cyan-500"
            />
          </div>
        </div>
      </div>

      {/* 3. STRICT 2-COLUMN PHOTOREALISTIC LOOKS GRID (Exact Match to Screenshot) */}
      <div className="max-w-6xl w-full mx-auto px-10 pb-20 flex-1">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filteredLooks.map((look) => (
            <div
              key={look.id}
              onClick={() => {
                if (onOpenStudio) onOpenStudio();
                alert(`Look "${look.name}" selected! Opening Studio.`);
              }}
              className="rounded-2xl overflow-hidden shadow-sm hover:shadow-xl transition-all duration-300 relative group cursor-pointer border border-[#1c2740] bg-[#0c111e]"
            >
              {/* High-Resolution Photorealistic Card Aspect */}
              <div className="aspect-[16/10] relative overflow-hidden bg-slate-900">
                <img
                  src={look.imageUrl}
                  alt={look.name}
                  className="w-full h-full object-cover object-top group-hover:scale-105 transition-transform duration-500 brightness-95 group-hover:brightness-100"
                  loading="lazy"
                />

                {/* Subtle Gradient Shadow on bottom */}
                <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/10 to-transparent pointer-events-none"></div>

                {/* Yellow/Gold Pill Badge at Bottom Right (Exact Match) */}
                <div className="absolute bottom-2.5 right-2.5 bg-amber-400 text-slate-950 font-extrabold text-[9px] px-2.5 py-0.5 rounded-full shadow-md z-10">
                  {look.badge}
                </div>

                {/* Look Name Badge at Bottom Left (Exact Match) */}
                <div className="absolute bottom-2.5 left-2.5 bg-black/65 backdrop-blur-md px-2.5 py-0.5 rounded-lg text-white text-[11px] font-semibold border border-white/10 shadow-sm max-w-[200px] truncate z-10">
                  {look.name}
                </div>

                {/* On-Hover Action Overlay */}
                <div className="absolute inset-0 bg-black/50 backdrop-blur-sm opacity-0 group-hover:opacity-100 transition-opacity duration-200 flex items-center justify-center gap-2 z-20">
                  <span className="px-4 py-1.5 bg-cyan-500 text-slate-950 text-xs font-bold rounded-full shadow-lg flex items-center gap-1.5">
                    <Play size={12} className="fill-slate-950" />
                    <span>Use Look</span>
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* AI Generate Look Prompt Modal */}
      {isPromptModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-md p-4 animate-in fade-in duration-200">
          <div className="w-full max-w-lg bg-[#0e1322] text-white rounded-3xl p-6 shadow-2xl border border-[#22304f]">
            <h3 className="text-lg font-bold mb-1 flex items-center gap-2">
              <Sparkles size={18} className="text-cyan-400" />
              <span>Describe Your New Look</span>
            </h3>
            <p className="text-xs text-slate-400 mb-4">
              Specify any outfit, styling, scenery, and lighting while keeping your avatar's face identity 100% locked.
            </p>

            <textarea
              rows={3}
              value={customPrompt}
              onChange={(e) => setCustomPrompt(e.target.value)}
              placeholder="e.g. Wearing a sleek navy blue executive blazer in a modern high-rise glass boardroom at golden hour..."
              className="w-full bg-[#121828] border border-[#22304d] rounded-2xl p-3.5 text-xs text-white placeholder-slate-400 focus:outline-none focus:border-cyan-500 mb-4"
            ></textarea>

            <div className="flex justify-end gap-2.5">
              <button
                onClick={() => setIsPromptModalOpen(false)}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:bg-[#18233a] cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  alert("Styling AI Look... Generating high-resolution avatar look!");
                  setIsPromptModalOpen(false);
                }}
                className="px-5 py-2 bg-gradient-to-r from-cyan-500 to-blue-600 text-white text-xs font-bold rounded-xl shadow-md cursor-pointer"
              >
                Generate Look (20 Credits)
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
