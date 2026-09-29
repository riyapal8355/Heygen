"use client";

import React, { useState, useRef, useEffect } from "react";
import {
  Video,
  ChevronRight,
  ChevronDown,
  Sparkles,
  Rocket,
  Lightbulb,
  GraduationCap,
  Megaphone,
  Check,
} from "lucide-react";
import {
  VideoAgentTemplate,
  getTemplateByIdOrTitle,
} from "../create/videoAgentData";
import { useTheme } from "@/context/ThemeContext";

export interface PromptCardData {
  id: string;
  title: string;
  category: string;
  bgGradient: string;
  accentColor: string;
  visualType: string;
  description?: string;
}

const CATEGORIES = [
  "Real Estate",
  "Healthcare",
  "Fitness & Wellness",
  "Legal",
  "Finance / Insurance",
  "Marketing & Creative",
  "Local Services",
  "Travel, Events & Design",
  "Consulting & Recruiting",
  "Education & Exam Prep",
  "Life & Career Coaching",
  "Faith & Community",
  "Online Courses",
  "Software & Products",
  "Venues & Hospitality",
  "Training / L&D",
  "Personal & School",
  "Something else",
];

const CATEGORY_PROMPT_MAP: Record<string, PromptCardData[]> = {
  "Software & Products": [
    {
      id: "ads_promo",
      title: "Ads & Promo",
      category: "Marketing",
      bgGradient: "from-[#20101b] via-[#171220] to-[#0c0f1c]",
      accentColor: "from-fuchsia-500 to-purple-600",
      visualType: "ad",
      description: "High-converting UGC video ad showcasing your software features",
    },
    {
      id: "product_launch",
      title: "Product Launch",
      category: "Software",
      bgGradient: "from-[#0d1629] via-[#0f1b34] to-[#090e1a]",
      accentColor: "from-blue-500 to-indigo-600",
      visualType: "rocket",
      description: "Exciting feature announcement and release notes video",
    },
    {
      id: "tips_how_to",
      title: "Tips & How-To",
      category: "Tutorial",
      bgGradient: "from-[#111c2e] via-[#10192a] to-[#0b101c]",
      accentColor: "from-cyan-500 to-blue-600",
      visualType: "idea",
      description: "Actionable step-by-step workflow guide and tool walkthrough",
    },
    {
      id: "educational_video",
      title: "Educational Video",
      category: "Learning",
      bgGradient: "from-[#241712] via-[#1a141d] to-[#0d0f17]",
      accentColor: "from-amber-500 to-orange-600",
      visualType: "education",
      description: "In-depth technical breakdown and architecture walkthrough",
    },
    {
      id: "course_lesson_video",
      title: "Course Lesson Video",
      category: "Training",
      bgGradient: "from-[#0c1d1a] via-[#11231f] to-[#0a1210]",
      accentColor: "from-emerald-500 to-teal-600",
      visualType: "course",
      description: "Comprehensive structured module with slides and avatar",
    },
    {
      id: "news_brief_video",
      title: "News Brief Video",
      category: "Updates",
      bgGradient: "from-[#211116] via-[#1a1017] to-[#0f0a12]",
      accentColor: "from-rose-500 to-pink-600",
      visualType: "news",
      description: "Fast-paced developer release notes and ecosystem news",
    },
    {
      id: "sales_outreach",
      title: "Sales Outreach",
      category: "Sales",
      bgGradient: "from-[#1d112b] via-[#161022] to-[#0e0a17]",
      accentColor: "from-purple-500 to-violet-600",
      visualType: "sales",
      description: "Hyper-personalized 1-on-1 demo pitch to convert leads",
    },
  ],
  "Real Estate": [
    {
      id: "re_market_update",
      title: "Market Update",
      category: "Real Estate",
      bgGradient: "from-[#1a150e] via-[#171318] to-[#0c0d14]",
      accentColor: "from-amber-500 to-orange-600",
      visualType: "realestate",
      description: "Monthly local housing stats, median price trends, and inventory",
    },
    {
      id: "re_hosted_tour",
      title: "Hosted Home Tour",
      category: "Real Estate",
      bgGradient: "from-[#0d1c1a] via-[#0f2120] to-[#091014]",
      accentColor: "from-emerald-500 to-teal-600",
      visualType: "realestate",
      description: "Virtual walkthrough guided by a personalized AI agent",
    },
    {
      id: "re_listing_spotlight",
      title: "Listing Spotlight",
      category: "Real Estate",
      bgGradient: "from-[#1d1226] via-[#161020] to-[#0c0d17]",
      accentColor: "from-purple-500 to-indigo-600",
      visualType: "realestate",
      description: "Snappy highlight reel showcasing property photos and open house",
    },
    {
      id: "re_cinematic_tour",
      title: "Cinematic Home Tour",
      category: "Real Estate",
      bgGradient: "from-[#0f172a] via-[#131d33] to-[#090e1a]",
      accentColor: "from-cyan-500 to-blue-600",
      visualType: "realestate",
      description: "Luxury architectural showcase with smooth aerial transitions",
    },
    {
      id: "re_meet_agent",
      title: "Meet the Agent",
      category: "Real Estate",
      bgGradient: "from-[#211219] via-[#19111b] to-[#0c0a14]",
      accentColor: "from-rose-500 to-fuchsia-600",
      visualType: "sales",
      description: "Realtor introduction highlighting local expertise and reviews",
    },
  ],
  "Healthcare": [
    {
      id: "hc_expert_explainer",
      title: "Expert Explainer",
      category: "Healthcare",
      bgGradient: "from-[#0c1d24] via-[#0f2329] to-[#091116]",
      accentColor: "from-teal-500 to-cyan-600",
      visualType: "health",
      description: "Clear, empathetic explanations of clinical care and procedures",
    },
    {
      id: "hc_tips_how_to",
      title: "Tips & How-To",
      category: "Healthcare",
      bgGradient: "from-[#111c2e] via-[#10192a] to-[#0b101c]",
      accentColor: "from-cyan-500 to-blue-600",
      visualType: "idea",
      description: "Daily preventive wellness habits and recovery guidelines",
    },
    {
      id: "hc_educational_video",
      title: "Educational Video",
      category: "Healthcare",
      bgGradient: "from-[#241712] via-[#1a141d] to-[#0d0f17]",
      accentColor: "from-amber-500 to-orange-600",
      visualType: "education",
      description: "Medical science walkthroughs and patient education modules",
    },
    {
      id: "hc_training",
      title: "Corporate Training Video",
      category: "Healthcare",
      bgGradient: "from-[#101827] via-[#131f36] to-[#090d16]",
      accentColor: "from-blue-500 to-indigo-600",
      visualType: "corporate",
      description: "Clinical compliance, hygiene, and hospital protocol training",
    },
  ],
  "Fitness & Wellness": [
    {
      id: "fw_tips_how_to",
      title: "Tips & How-To",
      category: "Fitness",
      bgGradient: "from-[#261310] via-[#1e1218] to-[#0e0a14]",
      accentColor: "from-orange-500 to-red-600",
      visualType: "fitness",
      description: "Daily workout circuits, mobility drills, and nutritional advice",
    },
    {
      id: "fw_ads_promo",
      title: "Ads & Promo",
      category: "Fitness",
      bgGradient: "from-[#20101b] via-[#171220] to-[#0c0f1c]",
      accentColor: "from-fuchsia-500 to-purple-600",
      visualType: "ad",
      description: "Promote your gym membership, challenge, or wellness coaching",
    },
    {
      id: "fw_educational_video",
      title: "Educational Video",
      category: "Wellness",
      bgGradient: "from-[#0e1d16] via-[#12231c] to-[#09120e]",
      accentColor: "from-emerald-500 to-teal-600",
      visualType: "education",
      description: "Science-based muscle hypertrophy and metabolic conditioning",
    },
    {
      id: "fw_expert_explainer",
      title: "Expert Explainer",
      category: "Wellness",
      bgGradient: "from-[#0f172a] via-[#131d33] to-[#090e1a]",
      accentColor: "from-cyan-500 to-blue-600",
      visualType: "explainer",
      description: "Biomechanics masterclass breakdown by elite trainers",
    },
  ],
  "Legal": [
    {
      id: "lg_expert_explainer",
      title: "Expert Explainer",
      category: "Legal",
      bgGradient: "from-[#161726] via-[#121422] to-[#0a0c16]",
      accentColor: "from-indigo-500 to-blue-600",
      visualType: "legal",
      description: "Plain-language breakdown of laws, contracts, and legal rights",
    },
    {
      id: "lg_policy_explainer",
      title: "Policy Explainer",
      category: "Legal",
      bgGradient: "from-[#1c141e] via-[#161220] to-[#0c0b16]",
      accentColor: "from-purple-500 to-violet-600",
      visualType: "corporate",
      description: "Workplace compliance and corporate regulatory guidelines",
    },
    {
      id: "lg_sales_outreach",
      title: "Sales Outreach",
      category: "Legal",
      bgGradient: "from-[#0d1629] via-[#0f1b34] to-[#090e1a]",
      accentColor: "from-blue-500 to-cyan-600",
      visualType: "sales",
      description: "Confidential introduction offering initial case evaluations",
    },
    {
      id: "lg_news_brief",
      title: "News Brief Video",
      category: "Legal",
      bgGradient: "from-[#211116] via-[#1a1017] to-[#0f0a12]",
      accentColor: "from-rose-500 to-pink-600",
      visualType: "news",
      description: "Regulatory updates, precedent rulings, and statutory changes",
    },
  ],
  "Finance / Insurance": [
    {
      id: "fi_market_update",
      title: "Market Update",
      category: "Finance",
      bgGradient: "from-[#0b1c18] via-[#0f2420] to-[#091210]",
      accentColor: "from-emerald-500 to-teal-600",
      visualType: "finance",
      description: "Weekly economic trends, index summaries, and fiscal analysis",
    },
    {
      id: "fi_tips_how_to",
      title: "Tips & How-To",
      category: "Finance",
      bgGradient: "from-[#111c2e] via-[#10192a] to-[#0b101c]",
      accentColor: "from-cyan-500 to-blue-600",
      visualType: "idea",
      description: "Personal wealth building, tax optimization, and investment tips",
    },
    {
      id: "fi_expert_explainer",
      title: "Expert Explainer",
      category: "Insurance",
      bgGradient: "from-[#1d112b] via-[#161022] to-[#0e0a17]",
      accentColor: "from-purple-500 to-indigo-600",
      visualType: "explainer",
      description: "Demystifying policy coverage, life insurance, and annuities",
    },
    {
      id: "fi_educational_video",
      title: "Educational Video",
      category: "Finance",
      bgGradient: "from-[#241712] via-[#1a141d] to-[#0d0f17]",
      accentColor: "from-amber-500 to-orange-600",
      visualType: "education",
      description: "Compound interest dynamics and portfolio diversification",
    },
  ],
  "Marketing & Creative": [
    {
      id: "mc_ads_promo",
      title: "Ads & Promo",
      category: "Marketing",
      bgGradient: "from-[#20101b] via-[#171220] to-[#0c0f1c]",
      accentColor: "from-fuchsia-500 to-purple-600",
      visualType: "ad",
      description: "High-hook UGC and promotional ad format for social platforms",
    },
    {
      id: "mc_product_launch",
      title: "Product Launch",
      category: "Marketing",
      bgGradient: "from-[#0d1629] via-[#0f1b34] to-[#090e1a]",
      accentColor: "from-blue-500 to-indigo-600",
      visualType: "rocket",
      description: "Creative product reveal video with avatar narration",
    },
    {
      id: "mc_educational_video",
      title: "Educational Video",
      category: "Creative",
      bgGradient: "from-[#241712] via-[#1a141d] to-[#0d0f17]",
      accentColor: "from-amber-500 to-orange-600",
      visualType: "education",
      description: "Engaging case study video and marketing strategy breakdown",
    },
    {
      id: "mc_tips_how_to",
      title: "Tips & How-To",
      category: "Creative",
      bgGradient: "from-[#111c2e] via-[#10192a] to-[#0b101c]",
      accentColor: "from-cyan-500 to-blue-600",
      visualType: "idea",
      description: "Creative growth hacks and viral video production tips",
    },
  ],
  "Online Courses": [
    {
      id: "oc_course_lesson",
      title: "Course Lesson Video",
      category: "Online Courses",
      bgGradient: "from-[#0c1d1a] via-[#11231f] to-[#0a1210]",
      accentColor: "from-emerald-500 to-teal-600",
      visualType: "course",
      description: "Comprehensive structured course lecture with side-by-side slides",
    },
    {
      id: "oc_educational_video",
      title: "Educational Video",
      category: "Online Courses",
      bgGradient: "from-[#241712] via-[#1a141d] to-[#0d0f17]",
      accentColor: "from-amber-500 to-orange-600",
      visualType: "education",
      description: "Engaging step-by-step academic tutorial with visual annotations",
    },
    {
      id: "oc_expert_explainer",
      title: "Expert Explainer",
      category: "Online Courses",
      bgGradient: "from-[#111c2e] via-[#10192a] to-[#0b101c]",
      accentColor: "from-cyan-500 to-blue-600",
      visualType: "explainer",
      description: "Subject matter expert masterclass breaking down core principles",
    },
    {
      id: "oc_tips_how_to",
      title: "Tips & How-To",
      category: "Online Courses",
      bgGradient: "from-[#1d112b] via-[#161022] to-[#0e0a17]",
      accentColor: "from-purple-500 to-indigo-600",
      visualType: "idea",
      description: "Quick tactical walkthrough demonstrating formulas or tools",
    },
  ],
  "Training / L&D": [
    {
      id: "ld_corporate_training",
      title: "Corporate Training Video",
      category: "Training",
      bgGradient: "from-[#101827] via-[#131f36] to-[#090d16]",
      accentColor: "from-blue-500 to-indigo-600",
      visualType: "corporate",
      description: "Scalable onboarding and enterprise team upskilling modules",
    },
    {
      id: "ld_team_onboarding",
      title: "Team Onboarding",
      category: "Training",
      bgGradient: "from-[#0c1d1a] via-[#11231f] to-[#0a1210]",
      accentColor: "from-emerald-500 to-teal-600",
      visualType: "corporate",
      description: "Warm welcome and department introduction for new joiners",
    },
    {
      id: "ld_policy_explainer",
      title: "Policy Explainer",
      category: "Training",
      bgGradient: "from-[#1c141e] via-[#161220] to-[#0c0b16]",
      accentColor: "from-purple-500 to-violet-600",
      visualType: "corporate",
      description: "Clear communication of workplace safety and compliance protocols",
    },
    {
      id: "ld_skills_refresher",
      title: "Skills Refresher",
      category: "Training",
      bgGradient: "from-[#111c2e] via-[#10192a] to-[#0b101c]",
      accentColor: "from-cyan-500 to-blue-600",
      visualType: "explainer",
      description: "Annual or quarterly refresher on critical workflows and security",
    },
  ],
};

function getCardsForCategory(category: string): PromptCardData[] {
  if (CATEGORY_PROMPT_MAP[category]) {
    return CATEGORY_PROMPT_MAP[category];
  }

  // Dynamic fallback templates for any other category
  return [
    {
      id: `${category.toLowerCase().replace(/[^a-z0-9]/g, "_")}_tips`,
      title: "Tips & How-To",
      category: category,
      bgGradient: "from-[#111c2e] via-[#10192a] to-[#0b101c]",
      accentColor: "from-cyan-500 to-blue-600",
      visualType: "idea",
      description: `Actionable quick tips and practical insights for ${category}`,
    },
    {
      id: `${category.toLowerCase().replace(/[^a-z0-9]/g, "_")}_explainer`,
      title: "Expert Explainer",
      category: category,
      bgGradient: "from-[#0f172a] via-[#131d33] to-[#090e1a]",
      accentColor: "from-blue-500 to-indigo-600",
      visualType: "explainer",
      description: `Authoritative breakdown and overview tailored for ${category}`,
    },
    {
      id: `${category.toLowerCase().replace(/[^a-z0-9]/g, "_")}_edu`,
      title: "Educational Video",
      category: category,
      bgGradient: "from-[#241712] via-[#1a141d] to-[#0d0f17]",
      accentColor: "from-amber-500 to-orange-600",
      visualType: "education",
      description: `Structured instructional walkthrough designed for ${category}`,
    },
    {
      id: `${category.toLowerCase().replace(/[^a-z0-9]/g, "_")}_promo`,
      title: "Ads & Promo",
      category: category,
      bgGradient: "from-[#20101b] via-[#171220] to-[#0c0f1c]",
      accentColor: "from-fuchsia-500 to-purple-600",
      visualType: "ad",
      description: `High-impact video presentation and outreach for ${category}`,
    },
  ];
}

export default function VideoPrompts({
  onSelectPrompt,
}: {
  onSelectPrompt?: (template?: VideoAgentTemplate, card?: PromptCardData) => void;
}) {
  const { theme } = useTheme();
  const isLight = theme === "light";
  const [activeCategory, setActiveCategory] = useState("Software & Products");
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(e.target as Node)
      ) {
        setIsDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const visibleCards = getCardsForCategory(activeCategory);

  return (
    <div className="w-full mt-7">
      {/* Header Bar */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <div
            className={`w-6 h-6 rounded-lg flex items-center justify-center ${
              isLight
                ? "bg-blue-50 border border-blue-200 text-blue-600"
                : "bg-blue-500/10 border border-blue-500/30 text-blue-400"
            }`}
          >
            <Video size={14} />
          </div>
          <h3
            className={`font-semibold text-sm ${
              isLight ? "text-slate-900" : "text-white"
            }`}
          >
            Video Prompts
          </h3>
        </div>

        {/* Personalization Dropdown / Toggle */}
        <div className="flex items-center gap-1.5 text-xs">
          <span className={isLight ? "text-slate-500" : "text-slate-400"}>Personalization:</span>
          <div className="relative" ref={dropdownRef}>
            <button
              type="button"
              onClick={() => setIsDropdownOpen(!isDropdownOpen)}
              className={`font-semibold underline underline-offset-4 cursor-pointer flex items-center gap-1 transition-colors ${
                isLight ? "text-blue-600 hover:text-blue-700" : "text-blue-400 hover:text-blue-300"
              }`}
            >
              <span>{activeCategory}</span>
              <ChevronDown
                size={13}
                className={`transform transition-transform duration-200 ${
                  isDropdownOpen ? "rotate-180" : ""
                }`}
              />
            </button>

            {isDropdownOpen && (
              <div
                className={`absolute right-0 mt-2 w-64 max-h-72 overflow-y-auto rounded-2xl p-1.5 shadow-2xl z-40 scrollbar-thin animate-in fade-in zoom-in-95 duration-150 ${
                  isLight
                    ? "bg-white border border-slate-200 scrollbar-thumb-slate-300 shadow-slate-200/50"
                    : "bg-[#0B111E] border border-[#1B2940] scrollbar-thumb-slate-800"
                }`}
              >
                {CATEGORIES.map((cat) => {
                  const isSelected = activeCategory === cat;
                  return (
                    <button
                      key={cat}
                      type="button"
                      onClick={() => {
                        setActiveCategory(cat);
                        setIsDropdownOpen(false);
                      }}
                      className={`w-full text-left px-3 py-2 rounded-xl text-xs transition-colors flex items-center justify-between cursor-pointer ${
                        isSelected
                          ? isLight
                            ? "bg-blue-50 text-blue-700 font-semibold border border-blue-200"
                            : "bg-gradient-to-r from-blue-600/30 to-cyan-500/20 text-cyan-300 font-semibold border border-cyan-500/30"
                          : isLight
                          ? "text-slate-700 hover:bg-slate-100 hover:text-slate-900"
                          : "text-slate-300 hover:bg-[#101827] hover:text-white"
                      }`}
                    >
                      <span>{cat}</span>
                      {isSelected && (
                        <Check size={13} className={isLight ? "text-blue-600" : "text-cyan-400"} />
                      )}
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Dynamic Rich Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {visibleCards.map((card) => {
          return (
            <div
              key={card.id}
              onClick={() => {
                const matchedTemplate = getTemplateByIdOrTitle(card.title);
                if (onSelectPrompt) onSelectPrompt(matchedTemplate, card);
              }}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  const matchedTemplate = getTemplateByIdOrTitle(card.title);
                  if (onSelectPrompt) onSelectPrompt(matchedTemplate, card);
                }
              }}
              className={`relative h-48 rounded-2xl p-5 flex flex-col justify-between overflow-hidden group cursor-pointer transition-all duration-300 ${
                isLight
                  ? "bg-white border border-slate-200/80 hover:border-blue-400 shadow-sm hover:shadow-xl"
                  : "bg-[#0d1222] border border-[#1b253e] hover:border-[#32456e] shadow-lg hover:shadow-2xl hover:shadow-blue-500/10"
              }`}
            >
              {/* Card Background Graphics / Visual Elements */}
              <div
                className={`absolute inset-0 transition-transform duration-500 group-hover:scale-105 ${
                  isLight
                    ? "bg-gradient-to-br from-slate-50/90 via-blue-50/40 to-indigo-50/30 opacity-100"
                    : `bg-gradient-to-r ${card.bgGradient} opacity-90`
                }`}
              ></div>

              {/* Dynamic Visual Art Representation for Each Type */}
              {card.visualType === "ad" && (
                <div className="absolute right-0 bottom-0 w-52 h-full flex items-end justify-end pointer-events-none opacity-85 group-hover:opacity-100 transition-opacity">
                  <div className="absolute right-4 bottom-4 w-28 h-28 rounded-full border-4 border-cyan-400/70 shadow-[0_0_35px_rgba(34,211,238,0.5)]"></div>
                  <div className="relative z-10 w-32 h-44 rounded-t-full bg-gradient-to-b from-[#b45309]/80 to-[#78350f]/80 flex items-center justify-center text-5xl shadow-2xl mr-2">
                    <span className="drop-shadow-lg">👩🏾‍💼</span>
                  </div>
                </div>
              )}

              {card.visualType === "rocket" && (
                <div className="absolute right-2 bottom-0 w-48 h-full flex items-end justify-end pointer-events-none opacity-85 group-hover:opacity-100 transition-opacity">
                  <div className="absolute right-2 bottom-2 w-36 h-20 bg-gradient-to-t from-blue-600/30 to-transparent rounded-full blur-lg"></div>
                  <div className="relative z-10 flex flex-col items-center mr-6 mb-2 animate-bounce duration-1000">
                    <span className="text-6xl drop-shadow-[0_0_25px_rgba(96,165,250,0.8)]">
                      🚀
                    </span>
                    <div className="w-10 h-8 bg-gradient-to-b from-orange-400 via-amber-300 to-transparent rounded-full blur-sm opacity-80"></div>
                  </div>
                </div>
              )}

              {card.visualType === "idea" && (
                <div className="absolute right-2 bottom-0 w-52 h-full flex items-end justify-end pointer-events-none opacity-85 group-hover:opacity-100 transition-opacity">
                  <div className="absolute right-24 top-6 w-12 h-12 rounded-full bg-amber-400/20 blur-md"></div>
                  <div className="absolute right-24 top-7 text-2xl animate-pulse">
                    💡
                  </div>
                  <div className="absolute right-14 top-14 w-16 h-10 rounded-lg bg-blue-500/20 border border-cyan-400/40 backdrop-blur-sm shadow-lg"></div>
                  <div className="relative z-10 w-32 h-44 rounded-t-full bg-gradient-to-b from-[#334155]/90 to-[#1e293b]/90 flex items-center justify-center text-5xl mr-2">
                    <span className="drop-shadow-lg">👩🏻‍💼</span>
                  </div>
                </div>
              )}

              {card.visualType === "education" && (
                <div className="absolute right-2 bottom-0 w-48 h-full flex items-end justify-end pointer-events-none opacity-85 group-hover:opacity-100 transition-opacity">
                  <div className="relative z-10 flex items-center gap-2 mr-4 mb-4">
                    <div className="w-24 h-24 rounded-full bg-[#38261e] border-2 border-[#57392b] flex items-center justify-center text-3xl shadow-2xl">
                      🍪
                    </div>
                    <span className="text-4xl transform -rotate-45 drop-shadow-lg">
                      👉
                    </span>
                  </div>
                </div>
              )}

              {card.visualType === "course" && (
                <div className="absolute right-2 bottom-0 w-48 h-full flex items-end justify-end pointer-events-none opacity-85 group-hover:opacity-100 transition-opacity">
                  <div className="relative z-10 flex flex-col items-center mr-6 mb-4">
                    <span className="text-6xl drop-shadow-[0_0_25px_rgba(52,211,153,0.6)]">
                      🎓
                    </span>
                    <div className="text-2xl mt-1">📚</div>
                  </div>
                </div>
              )}

              {card.visualType === "news" && (
                <div className="absolute right-2 bottom-0 w-48 h-full flex items-end justify-end pointer-events-none opacity-85 group-hover:opacity-100 transition-opacity">
                  <div className="relative z-10 flex flex-col items-center mr-6 mb-4">
                    <span className="text-6xl drop-shadow-[0_0_25px_rgba(244,63,94,0.6)]">
                      🎙️
                    </span>
                    <div className="text-2xl mt-1">📰</div>
                  </div>
                </div>
              )}

              {card.visualType === "sales" && (
                <div className="absolute right-2 bottom-0 w-48 h-full flex items-end justify-end pointer-events-none opacity-85 group-hover:opacity-100 transition-opacity">
                  <div className="relative z-10 flex flex-col items-center mr-6 mb-4">
                    <span className="text-6xl drop-shadow-[0_0_25px_rgba(168,85,247,0.6)]">
                      🎯
                    </span>
                    <div className="text-2xl mt-1">📈</div>
                  </div>
                </div>
              )}

              {card.visualType === "explainer" && (
                <div className="absolute right-2 bottom-0 w-48 h-full flex items-end justify-end pointer-events-none opacity-85 group-hover:opacity-100 transition-opacity">
                  <div className="relative z-10 flex flex-col items-center mr-6 mb-4">
                    <span className="text-6xl drop-shadow-[0_0_25px_rgba(56,189,248,0.6)]">
                      ✨
                    </span>
                    <div className="text-2xl mt-1">💡</div>
                  </div>
                </div>
              )}

              {card.visualType === "realestate" && (
                <div className="absolute right-2 bottom-0 w-48 h-full flex items-end justify-end pointer-events-none opacity-85 group-hover:opacity-100 transition-opacity">
                  <div className="relative z-10 flex flex-col items-center mr-6 mb-4">
                    <span className="text-6xl drop-shadow-[0_0_25px_rgba(16,185,129,0.6)]">
                      🏡
                    </span>
                    <div className="text-2xl mt-1">📍</div>
                  </div>
                </div>
              )}

              {card.visualType === "corporate" && (
                <div className="absolute right-2 bottom-0 w-48 h-full flex items-end justify-end pointer-events-none opacity-85 group-hover:opacity-100 transition-opacity">
                  <div className="relative z-10 flex flex-col items-center mr-6 mb-4">
                    <span className="text-6xl drop-shadow-[0_0_25px_rgba(59,130,246,0.6)]">
                      🏢
                    </span>
                    <div className="text-2xl mt-1">👔</div>
                  </div>
                </div>
              )}

              {card.visualType === "health" && (
                <div className="absolute right-2 bottom-0 w-48 h-full flex items-end justify-end pointer-events-none opacity-85 group-hover:opacity-100 transition-opacity">
                  <div className="relative z-10 flex flex-col items-center mr-6 mb-4">
                    <span className="text-6xl drop-shadow-[0_0_25px_rgba(20,184,166,0.6)]">
                      🩺
                    </span>
                    <div className="text-2xl mt-1">🏥</div>
                  </div>
                </div>
              )}

              {card.visualType === "fitness" && (
                <div className="absolute right-2 bottom-0 w-48 h-full flex items-end justify-end pointer-events-none opacity-85 group-hover:opacity-100 transition-opacity">
                  <div className="relative z-10 flex flex-col items-center mr-6 mb-4">
                    <span className="text-6xl drop-shadow-[0_0_25px_rgba(249,115,22,0.6)]">
                      ⚡
                    </span>
                    <div className="text-2xl mt-1">🏋️</div>
                  </div>
                </div>
              )}

              {card.visualType === "legal" && (
                <div className="absolute right-2 bottom-0 w-48 h-full flex items-end justify-end pointer-events-none opacity-85 group-hover:opacity-100 transition-opacity">
                  <div className="relative z-10 flex flex-col items-center mr-6 mb-4">
                    <span className="text-6xl drop-shadow-[0_0_25px_rgba(99,102,241,0.6)]">
                      ⚖️
                    </span>
                    <div className="text-2xl mt-1">📜</div>
                  </div>
                </div>
              )}

              {card.visualType === "finance" && (
                <div className="absolute right-2 bottom-0 w-48 h-full flex items-end justify-end pointer-events-none opacity-85 group-hover:opacity-100 transition-opacity">
                  <div className="relative z-10 flex flex-col items-center mr-6 mb-4">
                    <span className="text-6xl drop-shadow-[0_0_25px_rgba(16,185,129,0.6)]">
                      💎
                    </span>
                    <div className="text-2xl mt-1">📊</div>
                  </div>
                </div>
              )}

              {/* Title Content */}
              <div className="relative z-10 max-w-[65%]">
                <h4
                  className={`text-xl font-bold tracking-tight transition-colors ${
                    isLight
                      ? "text-slate-900 group-hover:text-blue-600"
                      : "text-white drop-shadow-md group-hover:text-cyan-200"
                  }`}
                >
                  {card.title}
                </h4>
                {card.description && (
                  <p
                    className={`text-xs mt-1 line-clamp-2 ${
                      isLight ? "text-slate-600 font-medium" : "text-slate-400"
                    }`}
                  >
                    {card.description}
                  </p>
                )}
              </div>

              {/* Bottom Action Button */}
              <div className="relative z-10">
                <button
                  type="button"
                  aria-label={`Create ${card.title} video now`}
                  onClick={(e) => {
                    e.stopPropagation();
                    const matchedTemplate = getTemplateByIdOrTitle(card.title);
                    if (onSelectPrompt) onSelectPrompt(matchedTemplate, card);
                  }}
                  className={`text-white text-xs font-semibold px-4 py-2 rounded-xl flex items-center gap-1.5 transition-all duration-200 group-hover:scale-105 cursor-pointer ${
                    isLight
                      ? "bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 shadow-md shadow-blue-500/20"
                      : "bg-gradient-to-r from-purple-600 to-indigo-600 group-hover:from-purple-500 group-hover:to-indigo-500 shadow-lg shadow-purple-900/40"
                  }`}
                >
                  <span>Create Now</span>
                  <ChevronRight
                    size={14}
                    className="group-hover:translate-x-0.5 transition-transform"
                  />
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
