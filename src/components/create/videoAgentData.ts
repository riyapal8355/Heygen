export interface VideoAgentTemplate {
  id: string;
  title: string;
  category: string;
  image: string;
  banner?: string;
  aspectRatio?: "16:9" | "9:16";
  duration?: string;
  scenesCount?: number;
  description?: string;
  scriptPlaceholder?: string;
  defaultScript?: string;
}

export interface VideoAgentSectionData {
  id: string;
  title: string;
  categoryTabId: string;
  templates: VideoAgentTemplate[];
}

export const VIDEO_AGENT_CATEGORIES = [
  { id: "personal-brand", label: "Personal Brand", sectionId: "section-personal-brand" },
  { id: "course-elearning", label: "Course & E-learning", sectionId: "section-course-elearning" },
  { id: "corporate-training", label: "Corporate Training", sectionId: "section-corporate-training" },
  { id: "creator-channels", label: "Creator Channels", sectionId: "section-creator-channels" },
  { id: "real-estate", label: "Real Estate", sectionId: "section-real-estate" },
];

export interface AvatarLook {
  id: string;
  name: string;
  image: string;
}

export interface AvatarOptionData {
  id: string;
  name: string;
  label: string;
  tag: string;
  image: string;
  type: string;
  looks: number;
  lookImages: AvatarLook[];
  category?: "recent" | "my" | "public";
  filterCategory?: "Professional" | "Lifestyle" | "UGC" | "Community";
  gender?: "Woman" | "Man";
  ageGroup?: "Young Adult" | "Middle Aged" | "Elderly";
  ethnicity?: "White" | "Asian" | "South Asian" | "Latino" | "Middle Eastern" | "Black";
  isNew?: boolean;
  isFavorite?: boolean;
}

export const AVATAR_OPTIONS: AvatarOptionData[] = [
  {
    id: "annie",
    name: "Annie",
    label: "Avatar",
    tag: "Studio",
    image: "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?q=80&w=600&auto=format&fit=crop",
    type: "Lifelike Portrait",
    looks: 57,
    category: "recent",
    filterCategory: "Professional",
    gender: "Woman",
    ageGroup: "Young Adult",
    ethnicity: "White",
    lookImages: [
      {
        id: "annie-look-1",
        name: "Beige Blazer",
        image: "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?q=80&w=400&auto=format&fit=crop",
      },
      {
        id: "annie-look-2",
        name: "Navy Blazer",
        image: "https://images.unsplash.com/photo-1580894732444-8ecded7900cd?q=80&w=400&auto=format&fit=crop",
      },
      {
        id: "annie-look-3",
        name: "White Studio Top",
        image: "https://images.unsplash.com/photo-1573497019940-1c28c88b4f3e?q=80&w=400&auto=format&fit=crop",
      },
      {
        id: "annie-look-4",
        name: "Casual Denim",
        image: "https://images.unsplash.com/photo-1567532939604-b6b5b0db2604?q=80&w=400&auto=format&fit=crop",
      },
      {
        id: "annie-look-5",
        name: "Formal Black Suit",
        image: "https://images.unsplash.com/photo-1580489944761-15a19d654956?q=80&w=400&auto=format&fit=crop",
      },
      {
        id: "annie-look-6",
        name: "Terracotta Knit",
        image: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?q=80&w=400&auto=format&fit=crop",
      },
      {
        id: "annie-look-7",
        name: "Silk Blouse",
        image: "https://images.unsplash.com/photo-1544005313-94ddf0286df2?q=80&w=400&auto=format&fit=crop",
      },
      {
        id: "annie-look-8",
        name: "Charcoal Blazer",
        image: "https://images.unsplash.com/photo-1573496799652-408c2ac9fe98?q=80&w=400&auto=format&fit=crop",
      },
      {
        id: "annie-look-9",
        name: "Smart Casual",
        image: "https://images.unsplash.com/photo-1573497019236-17f8177b81e8?q=80&w=400&auto=format&fit=crop",
      },
    ],
  },
  {
    id: "rasmus",
    name: "Rasmus",
    label: "Avatar",
    tag: "Studio",
    image: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?q=80&w=600&auto=format&fit=crop",
    type: "Executive Presenter",
    looks: 8,
    category: "recent",
    filterCategory: "Professional",
    gender: "Man",
    ageGroup: "Middle Aged",
    ethnicity: "White",
    lookImages: [
      {
        id: "rasmus-look-1",
        name: "Navy Jacket",
        image: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?q=80&w=400&auto=format&fit=crop",
      },
      {
        id: "rasmus-look-2",
        name: "Grey Oxford Shirt",
        image: "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?q=80&w=400&auto=format&fit=crop",
      },
      {
        id: "rasmus-look-3",
        name: "Green Knit Shirt",
        image: "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?q=80&w=400&auto=format&fit=crop",
      },
      {
        id: "rasmus-look-4",
        name: "Winter Wool Coat",
        image: "https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?q=80&w=400&auto=format&fit=crop",
      },
    ],
  },
  {
    id: "daniel",
    name: "Daniel",
    label: "Avatar",
    tag: "Studio",
    image: "https://images.unsplash.com/photo-1539571696357-5a69c17a67c6?q=80&w=600&auto=format&fit=crop",
    type: "Modern Creator",
    looks: 12,
    category: "recent",
    filterCategory: "Lifestyle",
    gender: "Man",
    ageGroup: "Young Adult",
    ethnicity: "White",
    lookImages: [
      {
        id: "daniel-look-1",
        name: "Black Shirt",
        image: "https://images.unsplash.com/photo-1539571696357-5a69c17a67c6?q=80&w=400&auto=format&fit=crop",
      },
      {
        id: "daniel-look-2",
        name: "White Shirt",
        image: "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?q=80&w=400&auto=format&fit=crop",
      },
      {
        id: "daniel-look-3",
        name: "Blue Shirt",
        image: "https://images.unsplash.com/photo-1522075469751-3a6694fb2f61?q=80&w=400&auto=format&fit=crop",
      },
      {
        id: "daniel-look-4",
        name: "Tailored Blazer",
        image: "https://images.unsplash.com/photo-1492562080023-ab3db95bfbce?q=80&w=400&auto=format&fit=crop",
      },
    ],
  },
  {
    id: "sophia",
    name: "Sophia",
    label: "Avatar",
    tag: "Studio",
    image: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?q=80&w=600&auto=format&fit=crop",
    type: "Creative Director",
    looks: 24,
    category: "recent",
    filterCategory: "UGC",
    gender: "Woman",
    ageGroup: "Young Adult",
    ethnicity: "White",
    lookImages: [
      {
        id: "sophia-look-1",
        name: "White Top",
        image: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?q=80&w=400&auto=format&fit=crop",
      },
      {
        id: "sophia-look-2",
        name: "Black Outfit",
        image: "https://images.unsplash.com/photo-1517841905240-472988babdf9?q=80&w=400&auto=format&fit=crop",
      },
      {
        id: "sophia-look-3",
        name: "Beige Outfit",
        image: "https://images.unsplash.com/photo-1544005313-94ddf0286df2?q=80&w=400&auto=format&fit=crop",
      },
      {
        id: "sophia-look-4",
        name: "Professional Blazer",
        image: "https://images.unsplash.com/photo-1524504388940-b1c1722653e1?q=80&w=400&auto=format&fit=crop",
      },
    ],
  },
  {
    id: "cora",
    name: "Cora",
    label: "Avatar",
    tag: "Studio",
    image: "https://images.unsplash.com/photo-1573497019236-17f8177b81e8?q=80&w=600&auto=format&fit=crop",
    type: "Studio Presenter",
    looks: 37,
    category: "public",
    filterCategory: "UGC",
    gender: "Woman",
    ageGroup: "Young Adult",
    ethnicity: "White",
    isNew: true,
    lookImages: [
      {
        id: "cora-look-1",
        name: "Terracotta Blazer",
        image: "https://images.unsplash.com/photo-1573497019236-17f8177b81e8?q=80&w=400&auto=format&fit=crop",
      },
      {
        id: "cora-look-2",
        name: "Charcoal Top",
        image: "https://images.unsplash.com/photo-1544005313-94ddf0286df2?q=80&w=400&auto=format&fit=crop",
      },
      {
        id: "cora-look-3",
        name: "White Blouse",
        image: "https://images.unsplash.com/photo-1531746020798-e6953c6e8e04?q=80&w=400&auto=format&fit=crop",
      },
      {
        id: "cora-look-4",
        name: "Navy Blazer",
        image: "https://images.unsplash.com/photo-1581092918056-0c4c3acd3789?q=80&w=400&auto=format&fit=crop",
      },
    ],
  },
  {
    id: "marieke",
    name: "Marieke",
    label: "Avatar",
    tag: "Corporate",
    image: "https://images.unsplash.com/photo-1598550874175-4d0ef436c909?q=80&w=600&auto=format&fit=crop",
    type: "Executive Presenter",
    looks: 28,
    category: "public",
    filterCategory: "Lifestyle",
    gender: "Woman",
    ageGroup: "Middle Aged",
    ethnicity: "White",
    isNew: true,
    lookImages: [
      {
        id: "marieke-look-1",
        name: "Executive Blazer",
        image: "https://images.unsplash.com/photo-1598550874175-4d0ef436c909?q=80&w=400&auto=format&fit=crop",
      },
      {
        id: "marieke-look-2",
        name: "White Oxford Shirt",
        image: "https://images.unsplash.com/photo-1580489944761-15a19d654956?q=80&w=400&auto=format&fit=crop",
      },
      {
        id: "marieke-look-3",
        name: "Grey Knitwear",
        image: "https://images.unsplash.com/photo-1567532939604-b6b5b0db2604?q=80&w=400&auto=format&fit=crop",
      },
    ],
  },
  {
    id: "marcus",
    name: "Marcus",
    label: "Avatar",
    tag: "Corporate",
    image: "https://images.unsplash.com/photo-1560250097-0b93528c311a?q=80&w=600&auto=format&fit=crop",
    type: "Executive Presenter",
    looks: 18,
    category: "public",
    filterCategory: "Professional",
    gender: "Man",
    ageGroup: "Middle Aged",
    ethnicity: "Black",
    lookImages: [
      {
        id: "marcus-look-1",
        name: "Executive Charcoal Suit",
        image: "https://images.unsplash.com/photo-1560250097-0b93528c311a?q=80&w=400&auto=format&fit=crop",
      },
      {
        id: "marcus-look-2",
        name: "Classic Black Polo",
        image: "https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?q=80&w=400&auto=format&fit=crop",
      },
      {
        id: "marcus-look-3",
        name: "Deep Navy Blazer",
        image: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?q=80&w=400&auto=format&fit=crop",
      },
    ],
  },
  {
    id: "emma",
    name: "Emma",
    label: "Avatar",
    tag: "Corporate",
    image: "https://images.unsplash.com/photo-1580489944761-15a19d654956?q=80&w=600&auto=format&fit=crop",
    type: "Business Executive",
    looks: 16,
    category: "public",
    filterCategory: "Professional",
    gender: "Woman",
    ageGroup: "Young Adult",
    ethnicity: "White",
    lookImages: [
      {
        id: "emma-look-1",
        name: "Executive Blue Suit",
        image: "https://images.unsplash.com/photo-1580489944761-15a19d654956?q=80&w=400&auto=format&fit=crop",
      },
      {
        id: "emma-look-2",
        name: "Conference Gray Blazer",
        image: "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?q=80&w=400&auto=format&fit=crop",
      },
      {
        id: "emma-look-3",
        name: "Casual Smart Knit",
        image: "https://images.unsplash.com/photo-1567532939604-b6b5b0db2604?q=80&w=400&auto=format&fit=crop",
      },
    ],
  },
  {
    id: "james",
    name: "James",
    label: "Avatar",
    tag: "Instant",
    image: "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?q=80&w=600&auto=format&fit=crop",
    type: "Tech Presenter",
    looks: 14,
    category: "public",
    filterCategory: "Community",
    gender: "Man",
    ageGroup: "Young Adult",
    ethnicity: "Asian",
    lookImages: [
      {
        id: "james-look-1",
        name: "Slate Gray Blazer",
        image: "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?q=80&w=400&auto=format&fit=crop",
      },
      {
        id: "james-look-2",
        name: "Casual Tech Tee",
        image: "https://images.unsplash.com/photo-1522075469751-3a6694fb2f61?q=80&w=400&auto=format&fit=crop",
      },
      {
        id: "james-look-3",
        name: "Minimalist Oxford",
        image: "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?q=80&w=400&auto=format&fit=crop",
      },
    ],
  },
  {
    id: "ava",
    name: "Ava",
    label: "Avatar",
    tag: "Studio",
    image: "https://images.unsplash.com/photo-1524504388940-b1c1722653e1?q=80&w=600&auto=format&fit=crop",
    type: "Media Host",
    looks: 20,
    category: "public",
    filterCategory: "Lifestyle",
    gender: "Woman",
    ageGroup: "Young Adult",
    ethnicity: "Latino",
    lookImages: [
      {
        id: "ava-look-1",
        name: "Terracotta Blazer",
        image: "https://images.unsplash.com/photo-1524504388940-b1c1722653e1?q=80&w=400&auto=format&fit=crop",
      },
      {
        id: "ava-look-2",
        name: "Clean White Blouse",
        image: "https://images.unsplash.com/photo-1544005313-94ddf0286df2?q=80&w=400&auto=format&fit=crop",
      },
      {
        id: "ava-look-3",
        name: "Urban Chic Jacket",
        image: "https://images.unsplash.com/photo-1517841905240-472988babdf9?q=80&w=400&auto=format&fit=crop",
      },
    ],
  },
  {
    id: "lucas",
    name: "Lucas",
    label: "Avatar",
    tag: "Instant",
    image: "https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?q=80&w=600&auto=format&fit=crop",
    type: "Creative Creator",
    looks: 15,
    category: "public",
    filterCategory: "UGC",
    gender: "Man",
    ageGroup: "Young Adult",
    ethnicity: "Latino",
    lookImages: [
      {
        id: "lucas-look-1",
        name: "Urban Denim",
        image: "https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?q=80&w=400&auto=format&fit=crop",
      },
      {
        id: "lucas-look-2",
        name: "Studio Tee",
        image: "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?q=80&w=400&auto=format&fit=crop",
      },
    ],
  },
  {
    id: "elena",
    name: "Elena",
    label: "Avatar",
    tag: "Studio",
    image: "https://images.unsplash.com/photo-1567532939604-b6b5b0db2604?q=80&w=600&auto=format&fit=crop",
    type: "Corporate Presenter",
    looks: 22,
    category: "public",
    filterCategory: "Community",
    gender: "Woman",
    ageGroup: "Young Adult",
    ethnicity: "South Asian",
    lookImages: [
      {
        id: "elena-look-1",
        name: "Emerald Blouse",
        image: "https://images.unsplash.com/photo-1567532939604-b6b5b0db2604?q=80&w=400&auto=format&fit=crop",
      },
      {
        id: "elena-look-2",
        name: "Warm Studio Knit",
        image: "https://images.unsplash.com/photo-1524504388940-b1c1722653e1?q=80&w=400&auto=format&fit=crop",
      },
    ],
  },
];

export const VOICE_OPTIONS = [
  {
    id: "annie-lifelike",
    name: "Annie - Lifelike",
    label: "Voice",
    accent: "American (Neutral)",
    style: "Conversational & Warm",
  },
  {
    id: "marcus-confident",
    name: "Marcus - Confident",
    label: "Voice",
    accent: "British (RP)",
    style: "Deep & Authoritative",
  },
  {
    id: "sarah-calm",
    name: "Sarah - Calm",
    label: "Voice",
    accent: "American (West Coast)",
    style: "Educational & Clear",
  },
  {
    id: "alex-energetic",
    name: "Alex - Energetic",
    label: "Voice",
    accent: "Canadian",
    style: "Fast-Paced & Engaging",
  },
];

export const BRAND_SYSTEM_OPTIONS = [
  {
    id: "demo-heygen-brand",
    name: "Demo HeyGen Bran...",
    fullName: "Demo HeyGen Brand System",
    label: "Brand System",
    color: "#000000",
    fonts: "Geist Sans • 4 Styles",
  },
  {
    id: "tech-corp-dark",
    name: "TechCorp Global",
    fullName: "TechCorp Global Brand System",
    label: "Brand System",
    color: "#0ea5e9",
    fonts: "Inter • Modern Tech",
  },
  {
    id: "creator-studio",
    name: "Creator Neon Kit",
    fullName: "Creator Neon Brand Kit",
    label: "Brand System",
    color: "#ec4899",
    fonts: "Outfit • Bold & Vibrant",
  },
];

export const VIDEO_AGENT_SECTIONS: VideoAgentSectionData[] = [
  {
    id: "section-personal-brand",
    categoryTabId: "personal-brand",
    title: "Build your personal brand",
    templates: [
      {
        id: "pb-1",
        title: "Tips & How-To",
        category: "Personal Brand",
        image: "https://images.unsplash.com/photo-1522202176988-66273c2fd55f?q=80&w=800&auto=format&fit=crop",
        duration: "1:15",
        scenesCount: 5,
        description: "Actionable quick tips with bulleted steps and dynamic avatar callouts",
      },
      {
        id: "pb-2",
        title: "Expert Explainer",
        category: "Personal Brand",
        image: "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?q=80&w=800&auto=format&fit=crop",
        duration: "2:00",
        scenesCount: 6,
        description: "Break down complex insights with clear slides and authoritative presentation",
      },
      {
        id: "pb-3",
        title: "Educational Video",
        category: "Personal Brand",
        image: "https://images.unsplash.com/photo-1531482615713-2afd69097998?q=80&w=800&auto=format&fit=crop",
        duration: "2:30",
        scenesCount: 7,
        description: "Structured educational walkthroughs for teaching your audience high-value skills",
      },
      {
        id: "pb-4",
        title: "Course Lesson Video",
        category: "Personal Brand",
        image: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?q=80&w=800&auto=format&fit=crop",
        duration: "3:10",
        scenesCount: 9,
        description: "Deep dive module lesson with chapter headings, code snippets, and takeaways",
      },
      {
        id: "pb-5",
        title: "News Brief Video",
        category: "Personal Brand",
        image: "https://images.unsplash.com/photo-1495020689067-958852a7765e?q=80&w=800&auto=format&fit=crop",
        duration: "0:55",
        scenesCount: 4,
        description: "Fast-paced industry news summary with headline banners and lower thirds",
      },
      {
        id: "pb-6",
        title: "Sales Outreach",
        category: "Personal Brand",
        image: "https://images.unsplash.com/photo-1560250097-0b93528c311a?q=80&w=800&auto=format&fit=crop",
        duration: "1:05",
        scenesCount: 4,
        description: "Hyper-personalized 1-to-1 video pitch that books meetings and builds trust",
      },
    ],
  },
  {
    id: "section-course-elearning",
    categoryTabId: "course-elearning",
    title: "Build learning videos that stick",
    templates: [
      {
        id: "cl-1",
        title: "Course Lesson Video",
        category: "Course & E-learning",
        image: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?q=80&w=800&auto=format&fit=crop",
        duration: "2:45",
        scenesCount: 8,
        description: "Comprehensive structured course lecture with side-by-side slides and avatar",
      },
      {
        id: "cl-2",
        title: "Micro-lesson",
        category: "Course & E-learning",
        image: "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?q=80&w=800&auto=format&fit=crop",
        duration: "0:45",
        scenesCount: 3,
        description: "Bite-sized concept explainer designed for quick retention and mobile viewing",
      },
      {
        id: "cl-3",
        title: "Corporate Training Video",
        category: "Course & E-learning",
        image: "https://images.unsplash.com/photo-1551836022-d5d88e9218df?q=80&w=800&auto=format&fit=crop",
        duration: "3:30",
        scenesCount: 10,
        description: "Formal enterprise compliance and staff development video with quizzes",
      },
      {
        id: "cl-4",
        title: "Educational Video",
        category: "Course & E-learning",
        image: "https://images.unsplash.com/photo-1524178232363-1fb2b075b655?q=80&w=800&auto=format&fit=crop",
        duration: "2:15",
        scenesCount: 6,
        description: "Engaging step-by-step academic or technical tutorial with visual annotations",
      },
      {
        id: "cl-5",
        title: "Expert Explainer",
        category: "Course & E-learning",
        image: "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?q=80&w=800&auto=format&fit=crop",
        duration: "1:50",
        scenesCount: 5,
        description: "Subject matter expert masterclass breaking down core principles",
      },
      {
        id: "cl-6",
        title: "Tips & How-To",
        category: "Course & E-learning",
        image: "https://images.unsplash.com/photo-1434030216411-0b793f4b4173?q=80&w=800&auto=format&fit=crop",
        duration: "1:20",
        scenesCount: 4,
        description: "Quick tactical walk-through demonstrating tools, workflows, or formulas",
      },
    ],
  },
  {
    id: "section-corporate-training",
    categoryTabId: "corporate-training",
    title: "Turn knowledge into training",
    templates: [
      {
        id: "ct-1",
        title: "Corporate Training Video",
        category: "Corporate Training",
        image: "https://images.unsplash.com/photo-1551836022-d5d88e9218df?q=80&w=800&auto=format&fit=crop",
        duration: "3:15",
        scenesCount: 9,
        description: "Scalable onboarding and enterprise team upskilling modules",
      },
      {
        id: "ct-2",
        title: "Course Lesson Video",
        category: "Corporate Training",
        image: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?q=80&w=800&auto=format&fit=crop",
        duration: "2:50",
        scenesCount: 7,
        description: "Internal company academy lesson with downloadable resources",
      },
      {
        id: "ct-3",
        title: "Team Onboarding",
        category: "Corporate Training",
        image: "https://images.unsplash.com/photo-1522071820081-009f0129c71c?q=80&w=800&auto=format&fit=crop",
        duration: "2:00",
        scenesCount: 6,
        description: "Warm welcome and department introduction for new joiners",
      },
      {
        id: "ct-4",
        title: "Policy Explainer",
        category: "Corporate Training",
        image: "https://images.unsplash.com/photo-1450133064473-71024230f91b?q=80&w=800&auto=format&fit=crop",
        duration: "1:40",
        scenesCount: 5,
        description: "Clear communication of workplace guidelines, safety, and compliance protocols",
      },
      {
        id: "ct-5",
        title: "Skills Refresher",
        category: "Corporate Training",
        image: "https://images.unsplash.com/photo-1517245386807-bb43f82c33c4?q=80&w=800&auto=format&fit=crop",
        duration: "1:30",
        scenesCount: 4,
        description: "Annual or quarterly refresher on critical workflows and security standards",
      },
      {
        id: "ct-6",
        title: "Internal Update",
        category: "Corporate Training",
        image: "https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?q=80&w=800&auto=format&fit=crop",
        duration: "1:10",
        scenesCount: 3,
        description: "Executive town hall or department update video delivered with AI avatars",
      },
    ],
  },
  {
    id: "section-creator-channels",
    categoryTabId: "creator-channels",
    title: "Build creator channel videos",
    templates: [
      {
        id: "cc-1",
        title: "Ads & Promo",
        category: "Creator Channels",
        image: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?q=80&w=800&auto=format&fit=crop",
        duration: "0:30",
        scenesCount: 3,
        description: "High-hook UGC and promotional ad format optimized for TikTok, Reels, and Shorts",
      },
      {
        id: "cc-2",
        title: "Educational Video",
        category: "Creator Channels",
        image: "https://images.unsplash.com/photo-1531482615713-2afd69097998?q=80&w=800&auto=format&fit=crop",
        duration: "2:00",
        scenesCount: 6,
        description: "Engaging YouTube and social explainer video with animated graphics",
      },
      {
        id: "cc-3",
        title: "Expert Explainer",
        category: "Creator Channels",
        image: "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?q=80&w=800&auto=format&fit=crop",
        duration: "1:45",
        scenesCount: 5,
        description: "Authority-building breakdown on trending tech, finance, or lifestyle topics",
      },
      {
        id: "cc-4",
        title: "Tips & How-To",
        category: "Creator Channels",
        image: "https://images.unsplash.com/photo-1522202176988-66273c2fd55f?q=80&w=800&auto=format&fit=crop",
        duration: "1:00",
        scenesCount: 4,
        description: "Viral tip listicle with high-energy pacing and engaging caption overlays",
      },
      {
        id: "cc-5",
        title: "News Brief Video",
        category: "Creator Channels",
        image: "https://images.unsplash.com/photo-1495020689067-958852a7765e?q=80&w=800&auto=format&fit=crop",
        duration: "0:45",
        scenesCount: 3,
        description: "Daily summary of top news stories ready to schedule across channels",
      },
      {
        id: "cc-6",
        title: "Video Podcast",
        category: "Creator Channels",
        image: "https://images.unsplash.com/photo-1590602847861-f357a9332bbc?q=80&w=800&auto=format&fit=crop",
        duration: "3:00",
        scenesCount: 8,
        description: "Multi-camera podcast style interview format with dual avatar speakers",
      },
    ],
  },
  {
    id: "section-real-estate",
    categoryTabId: "real-estate",
    title: "Sell homes with better video",
    templates: [
      {
        id: "re-1",
        title: "Market Update",
        category: "Real Estate",
        image: "https://images.unsplash.com/photo-1560518883-ce09059eeffa?q=80&w=800&auto=format&fit=crop",
        duration: "1:15",
        scenesCount: 4,
        description: "Monthly local housing market statistics, price trends, and inventory stats",
      },
      {
        id: "re-2",
        title: "Hosted Home Tour",
        category: "Real Estate",
        image: "https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?q=80&w=800&auto=format&fit=crop",
        duration: "2:10",
        scenesCount: 7,
        description: "Virtual walkthrough guided by a personalized AI agent highlighting key features",
      },
      {
        id: "re-3",
        title: "Listing Spotlight",
        category: "Real Estate",
        image: "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?q=80&w=800&auto=format&fit=crop",
        duration: "0:50",
        scenesCount: 4,
        description: "Snappy highlight reel showcasing property photos, price, and open house date",
      },
      {
        id: "re-4",
        title: "Cinematic Home Tour",
        category: "Real Estate",
        image: "https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?q=80&w=800&auto=format&fit=crop",
        duration: "2:30",
        scenesCount: 8,
        description: "Luxury architectural showcase with smooth aerial transitions and ambient music",
      },
      {
        id: "re-5",
        title: "Meet the Agent",
        category: "Real Estate",
        image: "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?q=80&w=800&auto=format&fit=crop",
        duration: "1:00",
        scenesCount: 3,
        description: "Realtor introduction highlighting local expertise, client reviews, and contact info",
      },
    ],
  },
];

export const ALL_VIDEO_AGENT_TEMPLATES: VideoAgentTemplate[] = VIDEO_AGENT_SECTIONS.flatMap(
  (sec) => sec.templates
);

export function getTemplateByIdOrTitle(idOrTitle: string): VideoAgentTemplate {
  const normalized = idOrTitle.trim().toLowerCase();
  const match = ALL_VIDEO_AGENT_TEMPLATES.find(
    (t) =>
      t.id.toLowerCase() === normalized ||
      t.title.toLowerCase() === normalized ||
      t.id.toLowerCase().replace(/[-_]/g, "") === normalized.replace(/[-_]/g, "")
  );

  if (match) return match;

  return {
    id: normalized.replace(/\s+/g, "-"),
    title: idOrTitle,
    category: "General",
    image: "https://images.unsplash.com/photo-1522202176988-66273c2fd55f?q=80&w=800&auto=format&fit=crop",
    banner: "https://images.unsplash.com/photo-1522202176988-66273c2fd55f?q=80&w=1200&auto=format&fit=crop",
    description: `Create an engaging ${idOrTitle} video for your audience with AI avatars.`,
  };
}

