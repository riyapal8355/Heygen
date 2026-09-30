export type AppCategory = "create" | "enhance" | "edit" | "interactive";

export type AppActionType =
  | "navigate_video_agent"
  | "navigate_studio"
  | "navigate_single_scene"
  | "navigate_scene_by_scene"
  | "navigate_translate"
  | "navigate_brand"
  | "navigate_design_look"
  | "modal_generator"
  | "modal_podcast"
  | "modal_speech"
  | "modal_pdf"
  | "modal_shots"
  | "modal_upscale"
  | "modal_clipping"
  | "modal_faceswap"
  | "modal_interactive";

export interface AppDefinition {
  id: string;
  name: string;
  description: string;
  category: AppCategory;
  badge?: string;
  keywords: string[];
  gradient: string;
  iconName: string;
  actionType: AppActionType;
  modalTitle: string;
  modalDescription: string;
  modalCta?: string;
  isAvailable?: boolean;
}

export const APP_REGISTRY: AppDefinition[] = [
  // --- CREATE APPS ---
  {
    id: "app_video_agent",
    name: "Video Agent",
    description: "Describe your video and let an AI agent create script, scenes, and avatars",
    category: "create",
    badge: "Featured",
    keywords: ["agent", "prompt", "script", "scenes", "ai", "create", "copilot", "video"],
    gradient: "from-purple-600 via-indigo-600 to-cyan-500",
    iconName: "Sparkles",
    actionType: "navigate_video_agent",
    modalTitle: "AI Video Agent Copilot",
    modalDescription:
      "Give a one-sentence prompt and the AI agent writes the script, selects avatars, generates scenes, and edits the video.",
    modalCta: "Launch Video Agent",
    isAvailable: true,
  },
  {
    id: "app_studio",
    name: "AI Studio",
    description: "Create and produce professional avatar videos on a multi-scene timeline",
    category: "create",
    badge: "Timeline Editor",
    keywords: ["studio", "editor", "timeline", "avatar", "canvas", "scenes", "create"],
    gradient: "from-blue-600 via-indigo-600 to-violet-600",
    iconName: "Video",
    actionType: "navigate_studio",
    modalTitle: "VidoAI Studio Editor",
    modalDescription:
      "Full multi-scene video timeline with custom canvas layouts, script synchronization, and 4K exports.",
    modalCta: "Open in Studio",
    isAvailable: true,
  },
  {
    id: "app_single_scene",
    name: "Single Scene Video",
    description: "Quickly produce single-scene avatar videos from text prompts and templates",
    category: "create",
    keywords: ["single", "scene", "quick", "prompt", "presenter", "create"],
    gradient: "from-sky-500 via-blue-600 to-indigo-700",
    iconName: "Film",
    actionType: "navigate_single_scene",
    modalTitle: "Single Scene Video Creator",
    modalDescription:
      "Rapidly generate focused, single-scene avatar presentations with full audio synthesis and layout controls.",
    modalCta: "Open Single Scene",
    isAvailable: true,
  },
  {
    id: "app_scene_by_scene",
    name: "Scene by Scene",
    description: "Compose multi-scene narrative videos with customizable layout transitions",
    category: "create",
    keywords: ["scene", "multi-scene", "storyboard", "narrative", "script", "create"],
    gradient: "from-teal-500 via-cyan-600 to-blue-600",
    iconName: "Layers",
    actionType: "navigate_scene_by_scene",
    modalTitle: "Scene by Scene Video Builder",
    modalDescription:
      "Build complex storyboarded videos step-by-step with synchronized avatar dialogue and media layers.",
    modalCta: "Open Scene Builder",
    isAvailable: true,
  },
  {
    id: "app_podcast",
    name: "Video Podcast",
    description: "Generate multi-speaker video podcasts with automatic active-speaker cuts",
    category: "create",
    badge: "Multi-Cam",
    keywords: ["podcast", "interview", "speakers", "dialogue", "host", "guest", "create"],
    gradient: "from-cyan-500 via-blue-600 to-indigo-600",
    iconName: "Mic",
    actionType: "modal_podcast",
    modalTitle: "AI Video Podcast Studio",
    modalDescription:
      "Generate multi-speaker video podcasts with automatic speaker switching, camera cuts, and mic waveforms.",
    modalCta: "Build Multi-Cam Podcast",
    isAvailable: true,
  },
  {
    id: "app_design_look",
    name: "Design a Look",
    description: "Generate custom wardrobe, styles, and photo-realistic looks for avatars",
    category: "create",
    badge: "Looks Studio",
    keywords: ["look", "avatar", "wardrobe", "style", "portrait", "design", "create"],
    gradient: "from-fuchsia-600 via-purple-600 to-pink-500",
    iconName: "Palette",
    actionType: "navigate_design_look",
    modalTitle: "Design a Look Studio",
    modalDescription:
      "Synthesize bespoke wardrobe options, styles, and environments for your digital avatars.",
    modalCta: "Design New Look",
    isAvailable: true,
  },
  {
    id: "app_generator",
    name: "AI Video Generator",
    description: "Create AI-generated video clips from text prompts (GPU required)",
    category: "create",
    badge: "Engine",
    keywords: ["generator", "b-roll", "background", "cinematic", "motion", "clip", "create"],
    gradient: "from-amber-500 via-orange-600 to-rose-600",
    iconName: "Sparkles",
    actionType: "modal_generator",
    modalTitle: "Generative Video Engine",
    modalDescription:
      "Turn text prompts into high-motion B-roll backgrounds, dynamic cinematic cuts, and photorealistic environments.",
    modalCta: "Generate Video Clip",
    isAvailable: true,
  },
  {
    id: "app_pdf",
    name: "PPT/PDF to Video",
    description: "Transform slides and documents into engaging avatar presentations",
    category: "create",
    badge: "Presentation",
    keywords: ["ppt", "pdf", "presentation", "slides", "document", "convert", "create"],
    gradient: "from-rose-500 via-pink-600 to-purple-600",
    iconName: "FileText",
    actionType: "modal_pdf",
    modalTitle: "PPT/PDF to Video Converter",
    modalDescription:
      "Upload slide decks or PDF reports to convert each page into structured video scenes with avatar narration.",
    modalCta: "Build Presentation Video",
    isAvailable: true,
  },
  {
    id: "app_shots",
    name: "Cinematic Shots",
    description: "AI-powered cinematic, film-quality camera angles and framing",
    category: "create",
    keywords: ["cinematic", "shots", "camera", "angles", "closeups", "framing", "create"],
    gradient: "from-violet-600 via-purple-600 to-indigo-700",
    iconName: "Camera",
    actionType: "modal_shots",
    modalTitle: "Cinematic Avatar Shots",
    modalDescription:
      "Generate Hollywood-grade closeups, over-the-shoulder angles, and walking shots for high-production commercials inside the studio timeline.",
    modalCta: "Build Cinematic Scene",
    isAvailable: true,
  },

  // --- ENHANCE APPS ---
  {
    id: "app_speech",
    name: "Speech Cleanup",
    description: "Remove room hum, filler words ('ums', 'uhs'), and background noise",
    category: "enhance",
    badge: "Neural Audio",
    keywords: ["speech", "cleanup", "audio", "noise", "filler", "voice", "enhance", "reverb"],
    gradient: "from-amber-400 via-yellow-500 to-emerald-500",
    iconName: "Volume2",
    actionType: "modal_speech",
    modalTitle: "Studio Audio Cleanup Engine",
    modalDescription:
      "One-click noise removal: eliminate room reverberation, breathing noises, 'ums', and 'uhs' to achieve broadcast studio clarity.",
    modalCta: "Apply Cleanup to Project",
    isAvailable: true,
  },
  {
    id: "app_upscale",
    name: "Upscale Video",
    description: "Restore and enhance videos to crystal-clear 4K resolution with neural sharpening",
    category: "enhance",
    badge: "4K Clarity",
    keywords: ["upscale", "4k", "resolution", "restore", "enhance", "quality", "hd"],
    gradient: "from-emerald-500 via-teal-600 to-cyan-600",
    iconName: "Maximize2",
    actionType: "modal_upscale",
    modalTitle: "AI 4K Video Upscaler",
    modalDescription:
      "Restore low-res videos to crystal clear 4K resolution with neural artifact removal, edge sharpening, and facial detail enhancement.",
    modalCta: "Process 4K Upscale",
    isAvailable: true,
  },
  {
    id: "app_brand_kit",
    name: "Brand Systems & Glossaries",
    description: "Manage brand colors, logos, fonts, and pronunciation glossaries",
    category: "enhance",
    badge: "Brand Voice",
    keywords: ["brand", "glossary", "pronunciation", "colors", "fonts", "assets", "enhance"],
    gradient: "from-indigo-500 via-purple-500 to-pink-500",
    iconName: "Palette",
    actionType: "navigate_brand",
    modalTitle: "Brand Systems & Glossaries",
    modalDescription:
      "Maintain consistent brand guidelines, custom fonts, visual palettes, and custom word pronunciation dictionaries across all avatar generations.",
    modalCta: "Manage Brand Systems",
    isAvailable: true,
  },

  // --- EDIT APPS ---
  {
    id: "app_translate",
    name: "Translate Videos",
    description: "Convert any video into 175+ languages with voice preservation and lip-sync",
    category: "edit",
    badge: "175+ Languages",
    keywords: ["translate", "language", "lip-sync", "subtitles", "voice", "dubbing", "edit"],
    gradient: "from-blue-600 via-cyan-600 to-teal-500",
    iconName: "Languages",
    actionType: "navigate_translate",
    modalTitle: "AI Video Translation & Lip-Sync",
    modalDescription:
      "Translate video audio into 175+ languages while preserving the original speaker's authentic voice timbre and adjusting lip movements.",
    modalCta: "Open Translation Studio",
    isAvailable: true,
  },
  {
    id: "app_clipping",
    name: "AI Clipping",
    description: "Upload longer videos and extract viral 9:16 vertical shorts with captions",
    category: "edit",
    keywords: ["clipping", "shorts", "reels", "viral", "vertical", "trim", "edit", "subtitles"],
    gradient: "from-fuchsia-500 via-purple-600 to-indigo-600",
    iconName: "Scissors",
    actionType: "modal_clipping",
    modalTitle: "Viral Shorts & Reels Clipper",
    modalDescription:
      "Upload long webinars, interviews, or videos. AI finds the most viral moments, crops to 9:16 vertical, and adds animated captions.",
    modalCta: "Extract Viral Clips",
    isAvailable: true,
  },
  {
    id: "app_faceswap",
    name: "Face Swap",
    description: "Swap facial features onto video avatars with realistic lighting and angles",
    category: "edit",
    keywords: ["face", "swap", "avatar", "identity", "photo", "edit", "headshot"],
    gradient: "from-pink-500 via-rose-500 to-amber-500",
    iconName: "Sparkles",
    actionType: "modal_faceswap",
    modalTitle: "Avatar Face Swap Studio",
    modalDescription:
      "Upload a single front-facing photo to swap facial features onto any avatar body, wardrobe, or custom scene environment.",
    modalCta: "Apply Face Swap",
    isAvailable: true,
  },

  // --- INTERACTIVE APPS ---
  {
    id: "app_interactive",
    name: "Interactive Video",
    description: "Create branching, clickable video funnels with CTA overlays and quiz buttons",
    category: "interactive",
    badge: "Branching",
    keywords: ["interactive", "branching", "clickable", "button", "funnel", "cta", "quiz", "lead"],
    gradient: "from-cyan-500 via-blue-600 to-purple-600",
    iconName: "MousePointerClick",
    actionType: "modal_interactive",
    modalTitle: "Branching Interactive Funnels",
    modalDescription:
      "Add interactive buttons, clickable cards, quiz questions, and Calendly booking embeds directly onto playing video timelines.",
    modalCta: "Build Interactive Video",
    isAvailable: true,
  },
];

export function filterApps(
  apps: AppDefinition[],
  category: "all" | AppCategory,
  searchQuery: string
): AppDefinition[] {
  let list = apps;

  // 1. Category Filter
  if (category !== "all") {
    list = list.filter((app) => app.category === category);
  }

  // 2. Search Query Filter (name, description, category, keywords)
  const trimmed = searchQuery.trim().toLowerCase();
  if (!trimmed) {
    return list;
  }

  return list.filter((app) => {
    const matchName = app.name.toLowerCase().includes(trimmed);
    const matchDesc = app.description.toLowerCase().includes(trimmed);
    const matchCat = app.category.toLowerCase().includes(trimmed);
    const matchKeyword = app.keywords.some((kw) =>
      kw.toLowerCase().includes(trimmed)
    );
    return matchName || matchDesc || matchCat || matchKeyword;
  });
}
