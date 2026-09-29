"use client";

import React, { useState, useRef, useEffect } from "react";
import {
  X,
  ArrowLeft,
  ArrowRight,
  LayoutGrid,
  List as ListIcon,
  ChevronDown,
  UserPlus,
  Check,
  Camera,
  Upload as UploadIcon,
  Image as ImageIcon,
  Wand2,
  BookOpen,
  Search,
  SlidersHorizontal,
  Heart,
  Shirt,
} from "lucide-react";
import { AvatarOptionData, AvatarLook } from "./videoAgentData";
import CreateAvatarModal from "./CreateAvatarModal";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";

interface ChooseAvatarModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectAvatar: (avatar: AvatarOptionData, selectedLook?: AvatarLook) => void;
  selectedAvatarId?: string;
  selectedLookId?: string;
}

export default function ChooseAvatarModal({
  isOpen,
  onClose,
  onSelectAvatar,
  selectedAvatarId = "annie",
  selectedLookId,
}: ChooseAvatarModalProps) {
  const { currentWorkspace } = useAuth();
  const [backendAvatars, setBackendAvatars] = useState<AvatarOptionData[]>([]);
  const [isLoadingAvatars, setIsLoadingAvatars] = useState(true);

  const [activeTab, setActiveTab] = useState<"recent" | "my" | "public">("recent");
  const [viewMode, setViewMode] = useState<"list" | "grid">("list");
  const [selectedId, setSelectedId] = useState(selectedAvatarId);
  const [currentSelectedLook, setCurrentSelectedLook] = useState<AvatarLook | null>(null);
  const [expandedAvatarId, setExpandedAvatarId] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    async function loadAvatars() {
      setIsLoadingAvatars(true);
      try {
        const resp = await api.creative.listAvatars({}, currentWorkspace?.id);
        if (active) {
          const mapped: AvatarOptionData[] = (resp || []).map((a: any) => ({
            id: a.id,
            name: a.name,
            label: a.name || "Avatar",
            tag: a.avatar_type || "Studio",
            type: a.avatar_type === "custom" ? "Custom Avatar" : "Photo Avatar",
            image:
              a.preview_url ||
              a.provider_metadata?.preview_url ||
              a.provider_metadata?.image_url ||
              "https://images.unsplash.com/photo-1534528741775-53994a69daeb?q=80&w=700&auto=format&fit=crop",
            filterCategory: a.provider_metadata?.category || "Professional",
            gender: a.provider_metadata?.gender,
            ageGroup: a.provider_metadata?.age_group,
            ethnicity: a.provider_metadata?.ethnicity,
            looks: a.looks?.length || 1,
            lookImages: (a.looks || []).map((l: any) => ({
              id: l.id,
              name: l.name,
              image:
                l.preview_url ||
                l.configuration?.preview_url ||
                "https://images.unsplash.com/photo-1534528741775-53994a69daeb?q=80&w=700&auto=format&fit=crop",
            })),
          }));
          setBackendAvatars(mapped);
          if (mapped.length > 0 && (!selectedId || selectedId === "annie" || selectedId === "30000000-0000-0000-0000-000000000002")) {
            const annie = mapped.find(
              (a) =>
                a.id === "30000000-0000-0000-0000-000000000002" ||
                a.name.toLowerCase().includes("annie")
            );
            setSelectedId(annie ? annie.id : mapped[0].id);
          }
        }
      } catch {
        // Fallback handled gracefully
      } finally {
        if (active) setIsLoadingAvatars(false);
      }
    }
    loadAvatars();
    return () => {
      active = false;
    };
  }, [currentWorkspace?.id]);

  // Search & Filter state for Public Avatars
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedFilter, setSelectedFilter] = useState<
    "All" | "Professional" | "Lifestyle" | "UGC" | "Community" | "Favorites"
  >("All");
  const [favoritesList, setFavoritesList] = useState<string[]>(["cora", "annie"]);
  const [isFilterPopoverOpen, setIsFilterPopoverOpen] = useState(false);

  // Demographic filter state (Gender, Age, Ethnicity)
  const [selectedGenders, setSelectedGenders] = useState<string[]>([]);
  const [selectedAges, setSelectedAges] = useState<string[]>([]);
  const [selectedEthnicities, setSelectedEthnicities] = useState<string[]>([]);

  // Draft state while popover is open
  const [draftGenders, setDraftGenders] = useState<string[]>([]);
  const [draftAges, setDraftAges] = useState<string[]>([]);
  const [draftEthnicities, setDraftEthnicities] = useState<string[]>([]);

  // Dropdown & Modal state for Create Avatar flows
  const [isCreateMenuOpen, setIsCreateMenuOpen] = useState(false);
  const [isCloneModalOpen, setIsCloneModalOpen] = useState(false);
  const [isVirtualModalOpen, setIsVirtualModalOpen] = useState(false);
  const [isGuideOpen, setIsGuideOpen] = useState(false);
  const [isUploadPhotoModalOpen, setIsUploadPhotoModalOpen] = useState(false);
  const [photoPreview, setPhotoPreview] = useState<string | null>(null);
  const [photoName, setPhotoName] = useState<string>("");

  // Virtual Character modal state
  const [virtualName, setVirtualName] = useState("");
  const [virtualImagePreview, setVirtualImagePreview] = useState<string | null>(null);

  const createMenuRef = useRef<HTMLDivElement>(null);
  const filterMenuRef = useRef<HTMLDivElement>(null);
  const photoInputRef = useRef<HTMLInputElement>(null);
  const virtualInputRef = useRef<HTMLInputElement>(null);

  // Sync selectedId and selectedLook on open
  useEffect(() => {
    if (isOpen && selectedAvatarId) {
      setSelectedId(selectedAvatarId);
      const found = backendAvatars.find((a) => a.id === selectedAvatarId);
      if (found) {
        if (selectedLookId && found.lookImages) {
          const look = found.lookImages.find((l) => l.id === selectedLookId);
          if (look) setCurrentSelectedLook(look);
          else setCurrentSelectedLook(found.lookImages[0] || null);
        } else if (found.lookImages && found.lookImages.length > 0) {
          setCurrentSelectedLook(found.lookImages[0]);
        }
      }
    }
  }, [isOpen, selectedAvatarId, selectedLookId, backendAvatars]);

  // Close on Escape key
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        if (isCloneModalOpen) {
          setIsCloneModalOpen(false);
        } else if (isVirtualModalOpen) {
          setIsVirtualModalOpen(false);
        } else if (isGuideOpen) {
          setIsGuideOpen(false);
        } else if (isUploadPhotoModalOpen) {
          setIsUploadPhotoModalOpen(false);
        } else if (isCreateMenuOpen) {
          setIsCreateMenuOpen(false);
        } else if (isFilterPopoverOpen) {
          setIsFilterPopoverOpen(false);
        } else {
          onClose();
        }
      }
    }
    if (isOpen) {
      window.addEventListener("keydown", handleKeyDown);
    }
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [
    isOpen,
    onClose,
    isCloneModalOpen,
    isVirtualModalOpen,
    isGuideOpen,
    isUploadPhotoModalOpen,
    isCreateMenuOpen,
    isFilterPopoverOpen,
  ]);

  // Outside click listeners
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (
        createMenuRef.current &&
        !createMenuRef.current.contains(e.target as Node)
      ) {
        setIsCreateMenuOpen(false);
      }
      if (
        filterMenuRef.current &&
        !filterMenuRef.current.contains(e.target as Node)
      ) {
        setIsFilterPopoverOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  if (!isOpen) return null;

  // Dynamic recent avatars from real backend list
  const recentAvatars = backendAvatars.slice(0, 2);

  // Ordered public avatars: Annie, Cora (NEW), Marieke (NEW), followed by others
  const publicAvatarsOrder = [
    "annie",
    "cora",
    "marieke",
    "rasmus",
    "daniel",
    "sophia",
    "marcus",
    "emma",
    "james",
    "ava",
    "lucas",
    "elena",
  ];

  const publicAvatarsList = backendAvatars;

  // Filtered public avatars based on search, category, and demographic filters
  const filteredPublicAvatars = publicAvatarsList.filter((avatar) => {
    const matchesSearch =
      searchQuery.trim() === "" ||
      avatar.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      avatar.type.toLowerCase().includes(searchQuery.toLowerCase());

    let matchesCategory = true;
    if (selectedFilter === "Favorites") {
      matchesCategory = favoritesList.includes(avatar.id);
    } else if (selectedFilter !== "All") {
      matchesCategory = avatar.filterCategory === selectedFilter;
    }

    let matchesGender = true;
    if (selectedGenders.length > 0) {
      matchesGender = !!avatar.gender && selectedGenders.includes(avatar.gender);
    }

    let matchesAge = true;
    if (selectedAges.length > 0) {
      matchesAge = !!avatar.ageGroup && selectedAges.includes(avatar.ageGroup);
    }

    let matchesEthnicity = true;
    if (selectedEthnicities.length > 0) {
      matchesEthnicity = !!avatar.ethnicity && selectedEthnicities.includes(avatar.ethnicity);
    }

    return (
      matchesSearch &&
      matchesCategory &&
      matchesGender &&
      matchesAge &&
      matchesEthnicity
    );
  });

  const toggleFavorite = (avatarId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setFavoritesList((prev) =>
      prev.includes(avatarId)
        ? prev.filter((id) => id !== avatarId)
        : [...prev, avatarId]
    );
  };

  const handleSelectAvatar = (avatar: AvatarOptionData, look?: AvatarLook) => {
    setSelectedId(avatar.id);
    if (look) {
      setCurrentSelectedLook(look);
    } else if (avatar.lookImages && avatar.lookImages.length > 0) {
      const belongs = avatar.lookImages.some((l) => l.id === currentSelectedLook?.id);
      if (!belongs) {
        setCurrentSelectedLook(avatar.lookImages[0]);
      }
    }
  };

  const handleContinue = () => {
    const chosen =
      backendAvatars.find((a) => a.id === selectedId) ||
      backendAvatars[0];
    if (chosen) {
      onSelectAvatar(chosen, currentSelectedLook || chosen.lookImages?.[0]);
    }
    onClose();
  };

  const handlePhotoSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setPhotoName(file.name);
      const url = URL.createObjectURL(file);
      setPhotoPreview(url);
      setIsUploadPhotoModalOpen(true);
      setIsCreateMenuOpen(false);
    }
  };

  const handleConfirmPhotoAvatar = () => {
    if (photoPreview) {
      const avatarId = typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : "photo-avatar";
      const lookId = typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : "photo-look";
      const customAvatar: AvatarOptionData = {
        id: avatarId,
        name: photoName.replace(/\.[^/.]+$/, "") || "Custom Avatar",
        label: "Avatar",
        tag: "Photo Avatar",
        image: photoPreview,
        type: "Photo Avatar",
        looks: 1,
        lookImages: [
          {
            id: lookId,
            name: "Default Look",
            image: photoPreview,
          },
        ],
      };
      onSelectAvatar(customAvatar, customAvatar.lookImages[0]);
      setIsUploadPhotoModalOpen(false);
      onClose();
    }
  };

  const handleVirtualPhotoSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const url = URL.createObjectURL(file);
      setVirtualImagePreview(url);
      if (!virtualName) {
        setVirtualName(file.name.replace(/\.[^/.]+$/, ""));
      }
    }
  };

  const handleConfirmVirtualAvatar = () => {
    const imgUrl =
      virtualImagePreview ||
      "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?q=80&w=800&auto=format&fit=crop";
    const avatarId = typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : "virtual-avatar";
    const lookId = typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : "virtual-look";
    const customAvatar: AvatarOptionData = {
      id: avatarId,
      name: virtualName.trim() || "Virtual Twin",
      label: "Avatar",
      tag: "Virtual Twin",
      image: imgUrl,
      type: "Digital 3D Character",
      looks: 1,
      lookImages: [
        {
          id: lookId,
          name: "Default Look",
          image: imgUrl,
        },
      ],
    };
    onSelectAvatar(customAvatar, customAvatar.lookImages[0]);
    setIsVirtualModalOpen(false);
    onClose();
  };

  // Toggle filter popover & sync drafts
  const handleToggleFilterPopover = () => {
    if (!isFilterPopoverOpen) {
      setDraftGenders(selectedGenders);
      setDraftAges(selectedAges);
      setDraftEthnicities(selectedEthnicities);
    }
    setIsFilterPopoverOpen(!isFilterPopoverOpen);
  };

  // Reset all demographic filters
  const handleResetFilters = () => {
    setDraftGenders([]);
    setDraftAges([]);
    setDraftEthnicities([]);
    setSelectedGenders([]);
    setSelectedAges([]);
    setSelectedEthnicities([]);
  };

  // Apply demographic filters & close popover
  const handleApplyFilters = () => {
    setSelectedGenders(draftGenders);
    setSelectedAges(draftAges);
    setSelectedEthnicities(draftEthnicities);
    setIsFilterPopoverOpen(false);
  };

  const hasActiveDemographicFilters =
    selectedGenders.length > 0 ||
    selectedAges.length > 0 ||
    selectedEthnicities.length > 0;

  return (
    <>
      {/* Hidden File Input for Upload Photo */}
      <input
        type="file"
        ref={photoInputRef}
        onChange={handlePhotoSelect}
        accept="image/*"
        className="hidden"
      />

      {/* Hidden File Input for Virtual Character */}
      <input
        type="file"
        ref={virtualInputRef}
        onChange={handleVirtualPhotoSelect}
        accept="image/*"
        className="hidden"
      />

      <div
        onClick={onClose}
        className="fixed inset-0 z-50 bg-black/75 backdrop-blur-md flex items-center justify-center p-3 sm:p-4 select-none animate-in fade-in duration-150"
      >
        <div
          onClick={(e) => e.stopPropagation()}
          className="w-full max-w-[1060px] h-[765px] max-h-[92vh] bg-[#0A0F1A] rounded-3xl shadow-2xl border border-[#1B2940] text-slate-100 flex flex-col relative overflow-hidden"
        >
          {/* ============================================================ */}
          {/* 1. HEADER & TOP NAVIGATION ROW */}
          {/* ============================================================ */}
          <div className="px-8 pt-7 pb-0 flex-shrink-0 bg-[#0A0F1A]">
            {/* Title + Simple X Close Icon */}
            <div className="flex items-center justify-between pb-4">
              <h2 className="text-2xl font-bold text-white tracking-tight">
                Choose Avatar
              </h2>
              <button
                type="button"
                onClick={onClose}
                className="text-slate-400 hover:text-white transition-colors p-1 cursor-pointer"
                title="Close"
              >
                <X size={20} />
              </button>
            </div>

            {/* Navigation Row: Tabs on Left, Grid/List + Create Avatar on Right */}
            <div className="flex items-center justify-between border-b border-[#1B2940]">
              {/* Tabs */}
              <div className="flex items-center gap-8">
                <button
                  type="button"
                  onClick={() => setActiveTab("recent")}
                  className={`pb-3.5 text-sm font-semibold transition-all relative cursor-pointer ${
                    activeTab === "recent"
                      ? "text-white font-bold"
                      : "text-slate-400 hover:text-slate-200 font-medium"
                  }`}
                >
                  Recently Used
                  {activeTab === "recent" && (
                    <div className="absolute left-0 bottom-0 w-full h-[3px] bg-cyan-500 rounded-full"></div>
                  )}
                </button>

                <button
                  type="button"
                  onClick={() => setActiveTab("my")}
                  className={`pb-3.5 text-sm font-semibold transition-all relative cursor-pointer ${
                    activeTab === "my"
                      ? "text-white font-bold"
                      : "text-slate-400 hover:text-slate-200 font-medium"
                  }`}
                >
                  My Avatars
                  {activeTab === "my" && (
                    <div className="absolute left-0 bottom-0 w-full h-[3px] bg-cyan-500 rounded-full"></div>
                  )}
                </button>

                <button
                  type="button"
                  onClick={() => setActiveTab("public")}
                  className={`pb-3.5 text-sm font-semibold transition-all relative cursor-pointer ${
                    activeTab === "public"
                      ? "text-white font-bold"
                      : "text-slate-400 hover:text-slate-200 font-medium"
                  }`}
                >
                  Public Avatars
                  {activeTab === "public" && (
                    <div className="absolute left-0 bottom-0 w-full h-[3px] bg-cyan-500 rounded-full"></div>
                  )}
                </button>
              </div>

              {/* Right Controls: Grid/List Segmented Toggle + Create Avatar Button */}
              <div className="flex items-center gap-3 pb-3">
                {/* Grid / List Toggle */}
                <div className="bg-[#0B1220] p-0.5 rounded-xl flex items-center gap-0.5 border border-[#1B2940]">
                  <button
                    type="button"
                    onClick={() => setViewMode("grid")}
                    className={`px-3 py-1 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all cursor-pointer ${
                      viewMode === "grid"
                        ? "bg-[#101827] text-white shadow-xs font-bold ring-1 ring-cyan-500/30"
                        : "text-slate-400 hover:text-white"
                    }`}
                  >
                    <LayoutGrid size={13} />
                    <span>Grid</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setViewMode("list")}
                    className={`px-3 py-1 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all cursor-pointer ${
                      viewMode === "list"
                        ? "bg-[#101827] text-white shadow-xs font-bold ring-1 ring-cyan-500/30"
                        : "text-slate-400 hover:text-white"
                    }`}
                  >
                    <ListIcon size={13} />
                    <span>List</span>
                  </button>
                </div>

                {/* Create Avatar Button + Dropdown Menu */}
                <div ref={createMenuRef} className="relative">
                  <button
                    type="button"
                    onClick={() => setIsCreateMenuOpen(!isCreateMenuOpen)}
                    className="bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-bold text-xs px-4 py-2 rounded-full shadow-md hover:shadow-cyan-500/20 flex items-center gap-1.5 transition-all cursor-pointer active:scale-95"
                  >
                    <UserPlus size={13} />
                    <span>Create Avatar</span>
                    <ChevronDown size={11} className="text-slate-950/70 ml-0.5" />
                  </button>

                  {/* Create Avatar Dropdown */}
                  {isCreateMenuOpen && (
                    <div className="absolute right-0 top-full mt-2 w-52 bg-[#0B111E] border border-[#1B2940] rounded-2xl shadow-xl p-1.5 z-50 animate-in fade-in zoom-in-95 duration-100">
                      <button
                        type="button"
                        onClick={() => {
                          setIsCloneModalOpen(true);
                          setIsCreateMenuOpen(false);
                        }}
                        className="w-full text-left px-3 py-2.5 rounded-xl text-xs font-semibold text-slate-200 hover:bg-[#101827] hover:text-white flex items-center gap-2.5 transition-colors cursor-pointer"
                      >
                        <Camera size={14} className="text-cyan-400" />
                        <span>Clone a real person</span>
                      </button>

                      <button
                        type="button"
                        onClick={() => {
                          photoInputRef.current?.click();
                          setIsCreateMenuOpen(false);
                        }}
                        className="w-full text-left px-3 py-2.5 rounded-xl text-xs font-semibold text-slate-200 hover:bg-[#101827] hover:text-white flex items-center gap-2.5 transition-colors cursor-pointer"
                      >
                        <UploadIcon size={14} className="text-purple-400" />
                        <span>Upload photo</span>
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* ============================================================ */}
          {/* 2. MAIN CONTENT AREA */}
          {/* ============================================================ */}
          <div className="flex-1 overflow-y-auto px-8 py-6 scrollbar-thin">
            {/* ============================================================ */}
            {/* TAB 1: RECENTLY USED */}
            {/* ============================================================ */}
            {activeTab === "recent" && (
              <>
                {/* REFERENCE 2: LIST VIEW */}
                {viewMode === "list" ? (
                  <div className="space-y-4">
                    {/* Row 1: Annie */}
                    {(() => {
                      const annie =
                        recentAvatars.find((a) => a.id === "annie") || recentAvatars[0];
                      const isSelected = selectedId === annie.id;
                      const look1 = annie.lookImages?.[0];
                      const look2 = annie.lookImages?.[1];
                      const look3 = annie.lookImages?.[2];

                      return (
                        <div
                          key={annie.id}
                          onClick={() => handleSelectAvatar(annie)}
                          className={`rounded-2xl border p-5 transition-all duration-150 bg-[#0B111E] flex items-center justify-between gap-6 cursor-pointer ${
                            isSelected
                              ? "border-cyan-500 ring-2 ring-cyan-500/30 bg-cyan-500/10"
                              : "border-[#1B2940] hover:border-slate-600 hover:bg-[#101827]"
                          }`}
                        >
                          {/* Left: Avatar Portrait (~120px) + Name & Looks Count */}
                          <div className="flex items-center gap-6 min-w-0">
                            <div className="relative flex-shrink-0">
                              <img
                                src={annie.image}
                                alt={annie.name}
                                className="w-28 h-28 sm:w-30 sm:h-30 rounded-full object-cover object-top ring-2 ring-[#1B2940]"
                              />
                              {isSelected && (
                                <div className="absolute -top-1 -right-1 w-6 h-6 rounded-full bg-cyan-500 text-slate-950 flex items-center justify-center shadow-xs">
                                  <Check size={13} strokeWidth={3} />
                                </div>
                              )}
                            </div>

                            <div className="min-w-0">
                              <h3 className="text-xl font-bold text-white">
                                {annie.name}
                              </h3>
                              <p className="text-sm font-medium text-slate-400 mt-1">
                                57 looks
                              </p>
                            </div>
                          </div>

                          {/* Right: Three Look Thumbnails */}
                          <div className="flex items-center gap-3 flex-shrink-0">
                            {/* Look 1: Beige Blazer */}
                            {look1 && (
                              <div
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleSelectAvatar(annie, look1);
                                }}
                                className={`relative w-20 h-26 sm:w-22 sm:h-28 rounded-2xl overflow-hidden border cursor-pointer transition-all ${
                                  isSelected && currentSelectedLook?.id === look1.id
                                    ? "border-cyan-500 ring-2 ring-cyan-500/30 shadow-xs"
                                    : "border-[#1B2940] hover:border-slate-500"
                                }`}
                              >
                                <img
                                  src={look1.image}
                                  alt={look1.name}
                                  className="w-full h-full object-cover object-center"
                                />
                              </div>
                            )}

                            {/* Look 2: Navy Blazer */}
                            {look2 && (
                              <div
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleSelectAvatar(annie, look2);
                                }}
                                className={`relative w-20 h-26 sm:w-22 sm:h-28 rounded-2xl overflow-hidden border cursor-pointer transition-all ${
                                  isSelected && currentSelectedLook?.id === look2.id
                                    ? "border-cyan-500 ring-2 ring-cyan-500/30 shadow-xs"
                                    : "border-[#1B2940] hover:border-slate-500"
                                }`}
                              >
                                <img
                                  src={look2.image}
                                  alt={look2.name}
                                  className="w-full h-full object-cover object-center"
                                />
                              </div>
                            )}

                            {/* Look 3: Dark Overlay (+55) */}
                            <div
                              onClick={(e) => {
                                e.stopPropagation();
                                handleSelectAvatar(annie);
                              }}
                              className="relative w-20 h-26 sm:w-22 sm:h-28 rounded-2xl overflow-hidden border border-[#1B2940] cursor-pointer shadow-2xs hover:border-slate-500 transition-colors"
                            >
                              <img
                                src={look3?.image || annie.image}
                                alt="More looks"
                                className="w-full h-full object-cover object-center filter brightness-50"
                              />
                              <div className="absolute inset-0 flex items-center justify-center text-white font-bold text-base sm:text-lg tracking-wide bg-black/50">
                                +55
                              </div>
                            </div>
                          </div>
                        </div>
                      );
                    })()}

                    {/* Row 2: Rasmus */}
                    {(() => {
                      const rasmus =
                        recentAvatars.find((a) => a.id === "rasmus") || recentAvatars[1];
                      const isSelected = selectedId === rasmus.id;
                      const look1 = rasmus.lookImages?.[0];
                      const look2 = rasmus.lookImages?.[1];
                      const look3 = rasmus.lookImages?.[2];

                      return (
                        <div
                          key={rasmus.id}
                          onClick={() => handleSelectAvatar(rasmus)}
                          className={`rounded-2xl border p-5 transition-all duration-150 bg-[#0B111E] flex items-center justify-between gap-6 cursor-pointer ${
                            isSelected
                              ? "border-cyan-500 ring-2 ring-cyan-500/30 bg-cyan-500/10"
                              : "border-[#1B2940] hover:border-slate-600 hover:bg-[#101827]"
                          }`}
                        >
                          {/* Left: Avatar Portrait (~120px) + Name & Looks Count */}
                          <div className="flex items-center gap-6 min-w-0">
                            <div className="relative flex-shrink-0">
                              <img
                                src={rasmus.image}
                                alt={rasmus.name}
                                className="w-28 h-28 sm:w-30 sm:h-30 rounded-full object-cover object-top ring-2 ring-[#1B2940]"
                              />
                              {isSelected && (
                                <div className="absolute -top-1 -right-1 w-6 h-6 rounded-full bg-cyan-500 text-slate-950 flex items-center justify-center shadow-xs">
                                  <Check size={13} strokeWidth={3} />
                                </div>
                              )}
                            </div>

                            <div className="min-w-0">
                              <h3 className="text-xl font-bold text-white">
                                {rasmus.name}
                              </h3>
                              <p className="text-sm font-medium text-slate-400 mt-1">
                                8 looks
                              </p>
                            </div>
                          </div>

                          {/* Right: Three Look Thumbnails */}
                          <div className="flex items-center gap-3 flex-shrink-0">
                            {/* Look 1: Navy Jacket */}
                            {look1 && (
                              <div
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleSelectAvatar(rasmus, look1);
                                }}
                                className={`relative w-20 h-26 sm:w-22 sm:h-28 rounded-2xl overflow-hidden border cursor-pointer transition-all ${
                                  isSelected && currentSelectedLook?.id === look1.id
                                    ? "border-cyan-500 ring-2 ring-cyan-500/30 shadow-xs"
                                    : "border-[#1B2940] hover:border-slate-500"
                                }`}
                              >
                                <img
                                  src={look1.image}
                                  alt={look1.name}
                                  className="w-full h-full object-cover object-center"
                                />
                              </div>
                            )}

                            {/* Look 2: Grey Oxford */}
                            {look2 && (
                              <div
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleSelectAvatar(rasmus, look2);
                                }}
                                className={`relative w-20 h-26 sm:w-22 sm:h-28 rounded-2xl overflow-hidden border cursor-pointer transition-all ${
                                  isSelected && currentSelectedLook?.id === look2.id
                                    ? "border-cyan-500 ring-2 ring-cyan-500/30 shadow-xs"
                                    : "border-[#1B2940] hover:border-slate-500"
                                }`}
                              >
                                <img
                                  src={look2.image}
                                  alt={look2.name}
                                  className="w-full h-full object-cover object-center"
                                />
                              </div>
                            )}

                            {/* Look 3: Dark Overlay (+6) */}
                            <div
                              onClick={(e) => {
                                e.stopPropagation();
                                handleSelectAvatar(rasmus);
                              }}
                              className="relative w-20 h-26 sm:w-22 sm:h-28 rounded-2xl overflow-hidden border border-[#1B2940] cursor-pointer shadow-2xs hover:border-slate-500 transition-colors"
                            >
                              <img
                                src={look3?.image || rasmus.image}
                                alt="More looks"
                                className="w-full h-full object-cover object-center filter brightness-50"
                              />
                              <div className="absolute inset-0 flex items-center justify-center text-white font-bold text-base sm:text-lg tracking-wide bg-black/50">
                                +6
                              </div>
                            </div>
                          </div>
                        </div>
                      );
                    })()}
                  </div>
                ) : (
                  /* REFERENCE 1: GRID VIEW (Collage Layout) */
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                    {recentAvatars.map((avatar) => {
                      const isSelected = selectedId === avatar.id;
                      const look1 = avatar.lookImages?.[0];
                      const look2 = avatar.lookImages?.[1];
                      const look3 = avatar.lookImages?.[2];

                      return (
                        <div
                          key={avatar.id}
                          onClick={() => handleSelectAvatar(avatar)}
                          className={`group rounded-3xl border p-3 transition-all duration-150 cursor-pointer bg-[#0B111E] flex flex-col justify-between ${
                            isSelected
                              ? "border-cyan-500 ring-2 ring-cyan-500/30 bg-cyan-500/10 shadow-xs"
                              : "border-[#1B2940] hover:border-cyan-500/40 hover:bg-[#101827]"
                          }`}
                        >
                          {/* Collage Image Layout: Left 60% Large Image + Right 40% 2 Vertical Looks */}
                          <div className="h-64 sm:h-72 w-full rounded-2xl overflow-hidden grid grid-cols-5 gap-2 bg-[#07090e] p-1 border border-[#1B2940]/50">
                            {/* Left: Large Main Portrait */}
                            <div className="col-span-3 h-full rounded-xl overflow-hidden relative bg-[#0A0F1A]">
                              <img
                                src={look1?.image || avatar.image}
                                alt={avatar.name}
                                className="w-full h-full object-cover object-top group-hover:scale-101 transition-transform duration-200"
                              />
                            </div>

                            {/* Right: 2 Vertically Stacked Looks */}
                            <div className="col-span-2 h-full flex flex-col gap-2">
                              <div className="flex-1 rounded-xl overflow-hidden relative bg-[#0A0F1A]">
                                <img
                                  src={look2?.image || avatar.image}
                                  alt={`${avatar.name} look 2`}
                                  className="w-full h-full object-cover object-top"
                                />
                              </div>
                              <div className="flex-1 rounded-xl overflow-hidden relative bg-[#0A0F1A]">
                                <img
                                  src={look3?.image || avatar.image}
                                  alt={`${avatar.name} look 3`}
                                  className="w-full h-full object-cover object-top"
                                />
                              </div>
                            </div>
                          </div>

                          {/* Name Label */}
                          <div className="pt-3 pb-1 px-2 flex items-center justify-between">
                            <h4 className="text-lg font-bold text-white">
                              {avatar.name}
                            </h4>
                            {isSelected && (
                              <div className="w-5 h-5 rounded-full bg-cyan-500 text-slate-950 flex items-center justify-center shadow-xs">
                                <Check size={12} strokeWidth={3} />
                              </div>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </>
            )}

            {/* ============================================================ */}
            {/* TAB 2: MY AVATARS */}
            {/* ============================================================ */}
            {activeTab === "my" && (
              <div className="py-2 flex flex-col items-center">
                {/* Main Heading & Subtitle */}
                <div className="text-center max-w-2xl mb-8">
                  <h2 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
                    Create Your First Avatar
                  </h2>
                  <p className="text-xs sm:text-sm text-slate-400 mt-2.5 leading-relaxed">
                    Create an identity that looks, moves, and sounds consistently in any outfit and setting.{" "}
                    <button
                      type="button"
                      onClick={() => setIsGuideOpen(true)}
                      className="text-cyan-400 font-semibold underline underline-offset-2 hover:text-cyan-300 transition-colors cursor-pointer inline"
                    >
                      View the guide
                    </button>
                  </p>
                </div>

                {/* 2 Creation Cards */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 w-full max-w-4xl">
                  {/* Card 1: Clone a real person */}
                  <div
                    onClick={() => setIsCloneModalOpen(true)}
                    className="group bg-[#0B111E] rounded-3xl border border-[#1B2940] hover:border-cyan-500/50 overflow-hidden shadow-lg hover:shadow-cyan-500/10 transition-all duration-200 cursor-pointer flex flex-col justify-between"
                  >
                    {/* Banner Image */}
                    <div className="h-48 sm:h-52 w-full relative overflow-hidden bg-[#07090e]">
                      <img
                        src="https://images.unsplash.com/photo-1576267423445-b2e0074d68a4?q=80&w=800&auto=format&fit=crop"
                        alt="Clone a real person"
                        className="w-full h-full object-cover object-center group-hover:scale-102 transition-transform duration-300"
                      />
                    </div>

                    {/* Content */}
                    <div className="p-6 flex-1 flex flex-col justify-between">
                      <div>
                        <div className="flex items-center justify-between gap-2 mb-2">
                          <h3 className="text-base sm:text-lg font-bold text-white tracking-tight">
                            Clone a real person
                          </h3>
                          <span className="bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 text-[10px] font-extrabold px-2.5 py-0.5 rounded-full uppercase tracking-wider">
                            Avatar V
                          </span>
                        </div>
                        <p className="text-xs sm:text-sm text-slate-400 leading-relaxed font-normal">
                          Use real video footage to create an avatar that looks, moves, and sounds like you.
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Card 2: Create a virtual character */}
                  <div
                    onClick={() => setIsVirtualModalOpen(true)}
                    className="group bg-[#0B111E] rounded-3xl border border-[#1B2940] hover:border-cyan-500/50 overflow-hidden shadow-lg hover:shadow-cyan-500/10 transition-all duration-200 cursor-pointer flex flex-col justify-between"
                  >
                    {/* Banner Image */}
                    <div className="h-48 sm:h-52 w-full relative overflow-hidden bg-[#07090e]">
                      <img
                        src="https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?q=80&w=800&auto=format&fit=crop"
                        alt="Create a virtual character"
                        className="w-full h-full object-cover object-center group-hover:scale-102 transition-transform duration-300"
                      />
                    </div>

                    {/* Content */}
                    <div className="p-6 flex-1 flex flex-col justify-between">
                      <div>
                        <div className="flex items-center justify-between gap-2 mb-2">
                          <h3 className="text-base sm:text-lg font-bold text-white tracking-tight">
                            Create a virtual character
                          </h3>
                        </div>
                        <p className="text-xs sm:text-sm text-slate-400 leading-relaxed font-normal">
                          Start with an image, and bring it to life with unique motion and voice.
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* ============================================================ */}
            {/* TAB 3: PUBLIC AVATARS */}
            {/* ============================================================ */}
            {activeTab === "public" && (
              <div className="space-y-4">
                {/* 1. Search Row & Filter Popover */}
                <div className="flex items-center gap-3">
                  <div className="relative flex-1">
                    <Search
                      size={15}
                      className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none"
                    />
                    <input
                      type="text"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      placeholder="Search"
                      className="w-full bg-[#07090e] border border-[#1B2940] rounded-2xl pl-10 pr-9 py-2.5 text-xs text-white placeholder:text-slate-500 outline-none focus:border-cyan-500 focus:bg-[#0B111E] transition-all shadow-2xs"
                    />
                    {searchQuery && (
                      <button
                        type="button"
                        onClick={() => setSearchQuery("")}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white cursor-pointer"
                      >
                        <X size={14} />
                      </button>
                    )}
                  </div>

                  {/* Filter Button & Demographic Filter Popover */}
                  <div ref={filterMenuRef} className="relative">
                    <button
                      type="button"
                      onClick={handleToggleFilterPopover}
                      className={`w-10 h-10 rounded-2xl border flex items-center justify-center transition-colors cursor-pointer ${
                        isFilterPopoverOpen || hasActiveDemographicFilters
                          ? "bg-cyan-500/20 text-cyan-300 border-cyan-500 shadow-xs"
                          : "bg-[#0B1220] hover:bg-[#101827] text-slate-300 border-[#1B2940] shadow-2xs"
                      }`}
                      title="Filter Avatars"
                    >
                      <SlidersHorizontal size={15} />
                    </button>

                    {/* Filter Popover Dialog (495px width, rounded-20px, Single Action Row) */}
                    {isFilterPopoverOpen && (
                      <div className="absolute right-0 top-full mt-2 w-[495px] max-w-[calc(100vw-3rem)] bg-[#0B111E] border border-[#1B2940] rounded-[20px] shadow-2xl p-5 z-50 flex flex-col max-h-[440px] animate-in fade-in zoom-in-95 duration-100">
                        {/* Scrollable Filter Options Area */}
                        <div className="overflow-y-auto flex-1 space-y-4 pr-1 pb-1 scrollbar-thin">
                          {/* 1. Gender */}
                          <div>
                            <div className="text-xs font-bold text-white mb-2">
                              Gender
                            </div>
                            <div className="flex flex-wrap items-center gap-2">
                              {(["Woman", "Man"] as const).map((gender) => {
                                const isSelected = draftGenders.includes(gender);
                                return (
                                  <button
                                    key={gender}
                                    type="button"
                                    onClick={() =>
                                      setDraftGenders((prev) =>
                                        prev.includes(gender)
                                          ? prev.filter((g) => g !== gender)
                                          : [...prev, gender]
                                      )
                                    }
                                    className={`px-4 py-1.5 rounded-full text-xs font-medium border transition-all cursor-pointer ${
                                      isSelected
                                        ? "bg-cyan-500/20 border-cyan-500 text-cyan-300 font-bold shadow-2xs"
                                        : "bg-[#07090e] hover:bg-[#101827] border-[#1B2940] text-slate-300"
                                    }`}
                                  >
                                    {gender}
                                  </button>
                                );
                              })}
                            </div>
                          </div>

                          {/* 2. Age */}
                          <div>
                            <div className="text-xs font-bold text-white mb-2">
                              Age
                            </div>
                            <div className="flex flex-wrap items-center gap-2">
                              {(
                                ["Young Adult", "Middle Aged", "Elderly"] as const
                              ).map((age) => {
                                const isSelected = draftAges.includes(age);
                                return (
                                  <button
                                    key={age}
                                    type="button"
                                    onClick={() =>
                                      setDraftAges((prev) =>
                                        prev.includes(age)
                                          ? prev.filter((a) => a !== age)
                                          : [...prev, age]
                                      )
                                    }
                                    className={`px-4 py-1.5 rounded-full text-xs font-medium border transition-all cursor-pointer ${
                                      isSelected
                                        ? "bg-cyan-500/20 border-cyan-500 text-cyan-300 font-bold shadow-2xs"
                                        : "bg-[#07090e] hover:bg-[#101827] border-[#1B2940] text-slate-300"
                                    }`}
                                  >
                                    {age}
                                  </button>
                                );
                              })}
                            </div>
                          </div>

                          {/* 3. Ethnicity */}
                          <div>
                            <div className="text-xs font-bold text-white mb-2">
                              Ethnicity
                            </div>
                            <div className="flex flex-wrap items-center gap-2">
                              {(
                                [
                                  "White",
                                  "Asian",
                                  "South Asian",
                                  "Latino",
                                  "Middle Eastern",
                                  "Black",
                                ] as const
                              ).map((ethnicity) => {
                                const isSelected =
                                  draftEthnicities.includes(ethnicity);
                                return (
                                  <button
                                    key={ethnicity}
                                    type="button"
                                    onClick={() =>
                                      setDraftEthnicities((prev) =>
                                        prev.includes(ethnicity)
                                          ? prev.filter((e) => e !== ethnicity)
                                          : [...prev, ethnicity]
                                      )
                                    }
                                    className={`px-4 py-1.5 rounded-full text-xs font-medium border transition-all cursor-pointer ${
                                      isSelected
                                        ? "bg-cyan-500/20 border-cyan-500 text-cyan-300 font-bold shadow-2xs"
                                        : "bg-[#07090e] hover:bg-[#101827] border-[#1B2940] text-slate-300"
                                    }`}
                                  >
                                    {ethnicity}
                                  </button>
                                );
                              })}
                            </div>
                          </div>
                        </div>

                        {/* Fixed Bottom Action Row: Single Reset and Single Done button */}
                        <div className="pt-3.5 mt-2 border-t border-[#1B2940] flex items-center justify-between flex-shrink-0">
                          <button
                            type="button"
                            onClick={handleResetFilters}
                            className="px-5 py-1.5 bg-[#0B1220] hover:bg-[#101827] border border-[#1B2940] text-slate-300 font-semibold text-xs rounded-full cursor-pointer transition-colors"
                          >
                            Reset
                          </button>
                          <button
                            type="button"
                            onClick={handleApplyFilters}
                            className="px-6 py-1.5 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-bold text-xs rounded-full shadow-xs cursor-pointer transition-colors active:scale-95"
                          >
                            Done
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* 2. Category Filter Pills */}
                <div className="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-none">
                  {(
                    [
                      "All",
                      "Professional",
                      "Lifestyle",
                      "UGC",
                      "Community",
                      "Favorites",
                    ] as const
                  ).map((cat) => {
                    const isActive = selectedFilter === cat;
                    return (
                      <button
                        key={cat}
                        type="button"
                        onClick={() => setSelectedFilter(cat)}
                        className={`px-3.5 py-1.5 rounded-full text-xs font-semibold whitespace-nowrap transition-all cursor-pointer border ${
                          isActive
                            ? "bg-cyan-500/20 border-cyan-500 text-cyan-300 font-bold shadow-2xs"
                            : "bg-[#0B1220] hover:bg-[#101827] border-[#1B2940] text-slate-400 hover:text-white"
                        }`}
                      >
                        {cat === "Favorites" ? `Favorites (${favoritesList.length})` : cat}
                      </button>
                    );
                  })}
                </div>

                {/* 3. Public Avatars Content (List View or Grid View) */}
                {viewMode === "list" ? (
                  <div className="divide-y divide-[#1B2940]/60">
                    {filteredPublicAvatars.length === 0 ? (
                      <div className="py-16 text-center text-slate-500 text-xs">
                        No public avatars found matching your criteria.
                      </div>
                    ) : (
                      filteredPublicAvatars.map((avatar) => {
                        const isSelected = selectedId === avatar.id;
                        const isExpanded = expandedAvatarId === avatar.id;
                        const isFav = favoritesList.includes(avatar.id);
                        const look1 = avatar.lookImages?.[0];
                        const look2 = avatar.lookImages?.[1];
                        const look3 = avatar.lookImages?.[2];

                        // Remaining looks count calculation
                        let remainingCount = Math.max(0, avatar.looks - 2);
                        if (avatar.id === "annie") remainingCount = 55;
                        if (avatar.id === "cora") remainingCount = 35;
                        if (avatar.id === "marieke") remainingCount = 27;

                        return (
                          <div
                            key={avatar.id}
                            onClick={() => handleSelectAvatar(avatar)}
                            className={`py-4 transition-all duration-150 rounded-2xl px-3 my-1 cursor-pointer ${
                              isSelected ? "bg-cyan-500/10 border border-cyan-500/40" : "hover:bg-[#101827]/60"
                            }`}
                          >
                            <div className="flex items-center justify-between gap-6 px-1">
                              {/* Left: Circular Avatar Portrait (~100-110px) + Name & Looks Count */}
                              <div className="flex items-center gap-5 min-w-0">
                                <div className="relative flex-shrink-0">
                                  <img
                                    src={avatar.image}
                                    alt={avatar.name}
                                    className="w-24 h-24 sm:w-26 sm:h-26 rounded-full object-cover object-top ring-2 ring-[#1B2940]"
                                  />
                                  {isSelected && (
                                    <div className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-cyan-500 text-slate-950 flex items-center justify-center shadow-xs">
                                      <Check size={12} strokeWidth={3} />
                                    </div>
                                  )}
                                </div>

                                <div className="min-w-0">
                                  <div className="flex items-center gap-2">
                                    <h3 className="text-lg sm:text-xl font-bold text-white">
                                      {avatar.name}
                                    </h3>
                                    {avatar.isNew && (
                                      <span className="text-[10px] font-extrabold px-2 py-0.5 rounded-full bg-cyan-500/20 border border-cyan-500/30 text-cyan-300 tracking-wider">
                                        NEW
                                      </span>
                                    )}
                                  </div>
                                  <p className="text-xs sm:text-sm font-medium text-slate-400 mt-1">
                                    {avatar.looks} looks
                                  </p>
                                </div>
                              </div>

                              {/* Right: Favorite Heart + 3 Look Thumbnails */}
                              <div className="flex items-center gap-3 flex-shrink-0">
                                {/* Favorite Heart Button */}
                                <button
                                  type="button"
                                  onClick={(e) => toggleFavorite(avatar.id, e)}
                                  className={`w-8 h-8 rounded-full flex items-center justify-center transition-colors cursor-pointer ${
                                    isFav
                                      ? "text-rose-400 bg-rose-500/20 hover:bg-rose-500/30"
                                      : "text-slate-500 hover:text-slate-300 hover:bg-[#101827]"
                                  }`}
                                  title={isFav ? "Remove from Favorites" : "Add to Favorites"}
                                >
                                  <Heart
                                    size={15}
                                    className={isFav ? "fill-rose-400" : ""}
                                  />
                                </button>

                                {/* Look 1 */}
                                {look1 && (
                                  <div
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      handleSelectAvatar(avatar, look1);
                                    }}
                                    className={`relative w-16 h-22 sm:w-18 sm:h-24 rounded-2xl overflow-hidden border cursor-pointer transition-all ${
                                      isSelected && currentSelectedLook?.id === look1.id
                                        ? "border-cyan-500 ring-2 ring-cyan-500/30 shadow-xs"
                                        : "border-[#1B2940] hover:border-slate-500"
                                    }`}
                                  >
                                    <img
                                      src={look1.image}
                                      alt={look1.name}
                                      className="w-full h-full object-cover object-center"
                                    />
                                  </div>
                                )}

                                {/* Look 2 */}
                                {look2 && (
                                  <div
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      handleSelectAvatar(avatar, look2);
                                    }}
                                    className={`relative w-16 h-22 sm:w-18 sm:h-24 rounded-2xl overflow-hidden border cursor-pointer transition-all ${
                                      isSelected && currentSelectedLook?.id === look2.id
                                        ? "border-cyan-500 ring-2 ring-cyan-500/30 shadow-xs"
                                        : "border-[#1B2940] hover:border-slate-500"
                                    }`}
                                  >
                                    <img
                                      src={look2.image}
                                      alt={look2.name}
                                      className="w-full h-full object-cover object-center"
                                    />
                                  </div>
                                )}

                                {/* Look 3: Dark Overlay (+55, +35, +27) */}
                                <div
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleSelectAvatar(avatar);
                                    setExpandedAvatarId(isExpanded ? null : avatar.id);
                                  }}
                                  className="relative w-16 h-22 sm:w-18 sm:h-24 rounded-2xl overflow-hidden border border-[#1B2940] cursor-pointer shadow-2xs group hover:border-slate-500"
                                  title="View all looks"
                                >
                                  <img
                                    src={look3?.image || avatar.image}
                                    alt="More looks"
                                    className="w-full h-full object-cover object-center filter brightness-50 group-hover:scale-105 transition-transform duration-200"
                                  />
                                  <div className="absolute inset-0 flex items-center justify-center text-white font-bold text-sm sm:text-base tracking-wide bg-black/50 group-hover:bg-black/60 transition-colors">
                                    +{remainingCount}
                                  </div>
                                </div>
                              </div>
                            </div>

                            {/* Inline Expandable Look Picker */}
                            {isExpanded && avatar.lookImages && avatar.lookImages.length > 0 && (
                              <div className="mt-2 pt-3 border-t border-[#1B2940] animate-in fade-in slide-in-from-top-2 duration-150 px-2">
                                <div className="text-xs font-semibold text-slate-300 mb-2 flex items-center justify-between">
                                  <div className="flex items-center gap-1.5">
                                    <Shirt size={13} className="text-cyan-400" />
                                    <span>Available Outfits & Looks for {avatar.name}</span>
                                  </div>
                                  <span className="text-[11px] text-slate-400 font-normal">
                                    Click to select outfit
                                  </span>
                                </div>
                                <div className="flex flex-wrap items-center gap-2">
                                  {avatar.lookImages.map((look) => {
                                    const isLookActive =
                                      isSelected && currentSelectedLook?.id === look.id;

                                    return (
                                      <div
                                        key={look.id}
                                        onClick={(e) => {
                                          e.stopPropagation();
                                          handleSelectAvatar(avatar, look);
                                        }}
                                        className={`flex items-center gap-2 p-1.5 pr-3 rounded-xl border cursor-pointer transition-all ${
                                          isLookActive
                                            ? "bg-cyan-500/20 border-cyan-500 text-cyan-300 font-bold ring-2 ring-cyan-500/30"
                                            : "bg-[#07090e] hover:bg-[#101827] border-[#1B2940] text-slate-300 font-medium"
                                        }`}
                                      >
                                        <img
                                          src={look.image}
                                          alt={look.name}
                                          className="w-7 h-9 rounded-lg object-cover"
                                        />
                                        <span className="text-xs">{look.name}</span>
                                        {isLookActive && (
                                          <Check size={12} className="text-cyan-400 ml-1" />
                                        )}
                                      </div>
                                    );
                                  })}
                                </div>
                              </div>
                            )}
                          </div>
                        );
                      })
                    )}
                  </div>
                ) : (
                  /* Public Avatars: Grid View */
                  <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
                    {filteredPublicAvatars.length === 0 ? (
                      <div className="col-span-full py-16 text-center text-slate-500 text-xs">
                        No public avatars found matching your criteria.
                      </div>
                    ) : (
                      filteredPublicAvatars.map((avatar) => {
                        const isSelected = selectedId === avatar.id;
                        const isFav = favoritesList.includes(avatar.id);

                        return (
                          <div
                            key={avatar.id}
                            onClick={() => handleSelectAvatar(avatar)}
                            className={`rounded-2xl border overflow-hidden transition-all duration-150 bg-[#0B111E] cursor-pointer flex flex-col justify-between group ${
                              isSelected
                                ? "border-cyan-500 ring-2 ring-cyan-500/30 bg-cyan-500/10 shadow-sm"
                                : "border-[#1B2940] hover:border-cyan-500/40 hover:bg-[#101827] hover:shadow-xs"
                            }`}
                          >
                            {/* Portrait Studio Image */}
                            <div className="h-48 sm:h-52 w-full relative bg-[#07090e] overflow-hidden">
                              <img
                                src={avatar.image}
                                alt={avatar.name}
                                className="w-full h-full object-cover object-top group-hover:scale-102 transition-transform duration-300"
                              />

                              {/* NEW Badge */}
                              {avatar.isNew && (
                                <div className="absolute top-2.5 left-2.5">
                                  <span className="text-[10px] font-extrabold px-2 py-0.5 rounded-full bg-cyan-500 text-slate-950 shadow-xs">
                                    NEW
                                  </span>
                                </div>
                              )}

                              {/* Favorite Heart Button */}
                              <button
                                type="button"
                                onClick={(e) => toggleFavorite(avatar.id, e)}
                                className={`absolute top-2.5 right-2.5 w-7 h-7 rounded-full backdrop-blur-md flex items-center justify-center transition-colors cursor-pointer ${
                                  isFav
                                    ? "bg-rose-500 text-white shadow-xs"
                                    : "bg-black/60 text-white/80 hover:bg-black/80 hover:text-white"
                                }`}
                              >
                                <Heart size={13} className={isFav ? "fill-white" : ""} />
                              </button>

                              {/* Selected Checkmark Badge */}
                              {isSelected && (
                                <div className="absolute bottom-2.5 right-2.5 w-6 h-6 rounded-full bg-cyan-500 text-slate-950 flex items-center justify-center shadow-xs">
                                  <Check size={12} strokeWidth={3} />
                                </div>
                              )}
                            </div>

                            {/* Details */}
                            <div className="p-3 bg-[#0B111E] border-t border-[#1B2940] flex items-center justify-between">
                              <div>
                                <div className="text-sm font-bold text-white">
                                  {avatar.name}
                                </div>
                                <div className="text-xs text-slate-400 font-medium mt-0.5">
                                  {avatar.looks} looks
                                </div>
                              </div>

                              <span
                                className={`text-[11px] font-bold px-2.5 py-1 rounded-full transition-colors ${
                                  isSelected
                                    ? "bg-cyan-500 text-slate-950"
                                    : "bg-[#101827] text-slate-300 group-hover:bg-[#1B2940] group-hover:text-white"
                                }`}
                              >
                                {isSelected ? "Selected" : "Select"}
                              </span>
                            </div>
                          </div>
                        );
                      })
                    )}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* ============================================================ */}
          {/* 3. FIXED FOOTER */}
          {/* ============================================================ */}
          <div className="px-8 py-4 border-t border-[#1B2940] flex items-center justify-between flex-shrink-0 bg-[#0A0F1A]">
            {/* Left: Back */}
            <button
              type="button"
              onClick={onClose}
              className="text-slate-400 hover:text-white font-semibold text-xs flex items-center gap-1.5 px-3 py-2 rounded-xl hover:bg-[#101827] transition-colors cursor-pointer"
            >
              <ArrowLeft size={14} />
              <span>Back</span>
            </button>

            {/* Right: Continue */}
            <button
              type="button"
              onClick={handleContinue}
              className="bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-bold text-xs px-6 py-2.5 rounded-full shadow-lg hover:shadow-cyan-500/25 transition-all duration-150 cursor-pointer flex items-center gap-1.5 active:scale-95"
            >
              <span>Continue</span>
              <ArrowRight size={14} />
            </button>
          </div>
        </div>
      </div>

      {/* ============================================================ */}
      {/* 4. CLONE A REAL PERSON MODAL SCREEN */}
      {/* ============================================================ */}
      {isCloneModalOpen && (
        <CreateAvatarModal
          isOpen={isCloneModalOpen}
          onClose={() => setIsCloneModalOpen(false)}
        />
      )}

      {/* ============================================================ */}
      {/* 5. VIRTUAL CHARACTER CREATION MODAL */}
      {/* ============================================================ */}
      {isVirtualModalOpen && (
        <div
          onClick={() => setIsVirtualModalOpen(false)}
          className="fixed inset-0 z-70 bg-black/75 backdrop-blur-md flex items-center justify-center p-4 animate-in fade-in duration-150"
        >
          <div
            onClick={(e) => e.stopPropagation()}
            className="w-full max-w-md bg-[#0A0F1A] rounded-3xl p-6 sm:p-7 shadow-2xl border border-[#1B2940] text-slate-100 animate-in zoom-in-95 duration-150"
          >
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Wand2 size={18} className="text-purple-400" />
                <h4 className="text-base sm:text-lg font-bold text-white">
                  Create a virtual character
                </h4>
              </div>
              <button
                type="button"
                onClick={() => setIsVirtualModalOpen(false)}
                className="text-slate-400 hover:text-white p-1 cursor-pointer"
              >
                <X size={16} />
              </button>
            </div>

            {/* Upload image area */}
            <div
              onClick={() => virtualInputRef.current?.click()}
              className="w-full h-44 rounded-2xl border-2 border-dashed border-[#1B2940] hover:border-purple-400 bg-[#0B111E] hover:bg-[#101827] flex flex-col items-center justify-center p-4 cursor-pointer transition-colors mb-4 overflow-hidden relative"
            >
              {virtualImagePreview ? (
                <img
                  src={virtualImagePreview}
                  alt="Virtual character preview"
                  className="w-full h-full object-cover rounded-xl"
                />
              ) : (
                <div className="flex flex-col items-center text-center">
                  <div className="w-10 h-10 rounded-full bg-purple-500/20 text-purple-400 flex items-center justify-center mb-2">
                    <ImageIcon size={18} />
                  </div>
                  <span className="text-xs font-semibold text-slate-200">
                    Upload Character Image
                  </span>
                  <span className="text-[11px] text-slate-400 mt-0.5">
                    PNG, JPG, or WEBP up to 20MB
                  </span>
                </div>
              )}
            </div>

            {/* Character Name Input */}
            <div className="mb-5">
              <label className="text-xs font-semibold text-slate-300 block mb-1.5">
                Character Name
              </label>
              <input
                type="text"
                value={virtualName}
                onChange={(e) => setVirtualName(e.target.value)}
                placeholder="e.g. AI Virtual Twin"
                className="w-full bg-[#07090e] border border-[#1B2940] rounded-xl px-3.5 py-2 text-xs text-white outline-none focus:border-purple-500 focus:bg-[#0B111E] placeholder:text-slate-600 transition-all"
              />
            </div>

            {/* Buttons */}
            <div className="flex items-center justify-end gap-2">
              <button
                type="button"
                onClick={() => setIsVirtualModalOpen(false)}
                className="px-3.5 py-2 text-xs text-slate-400 hover:text-white font-medium cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirmVirtualAvatar}
                className="bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-xs font-bold px-5 py-2 rounded-xl transition-colors cursor-pointer shadow-md"
              >
                Create Character
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ============================================================ */}
      {/* 6. VIEW THE GUIDE POPUP */}
      {/* ============================================================ */}
      {isGuideOpen && (
        <div
          onClick={() => setIsGuideOpen(false)}
          className="fixed inset-0 z-70 bg-black/75 backdrop-blur-md flex items-center justify-center p-4 animate-in fade-in duration-150"
        >
          <div
            onClick={(e) => e.stopPropagation()}
            className="w-full max-w-md bg-[#0A0F1A] rounded-3xl p-6 sm:p-7 shadow-2xl border border-[#1B2940] text-slate-100 animate-in zoom-in-95 duration-150"
          >
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <BookOpen size={18} className="text-cyan-400" />
                <h4 className="text-base sm:text-lg font-bold text-white">
                  Avatar Creation Guide
                </h4>
              </div>
              <button
                type="button"
                onClick={() => setIsGuideOpen(false)}
                className="text-slate-400 hover:text-white p-1 cursor-pointer"
              >
                <X size={16} />
              </button>
            </div>

            <div className="space-y-3.5 text-xs text-slate-300 leading-relaxed mb-6">
              <div className="bg-[#0B111E] border border-[#1B2940] p-3 rounded-2xl">
                <div className="font-bold text-white mb-1">1. Lighting & Background</div>
                <p className="text-slate-400">Ensure your face is evenly lit with soft natural light and a clean, uncluttered background.</p>
              </div>

              <div className="bg-[#0B111E] border border-[#1B2940] p-3 rounded-2xl">
                <div className="font-bold text-white mb-1">2. Camera & Eye Contact</div>
                <p className="text-slate-400">Keep the camera at eye level and look directly into the lens while speaking naturally.</p>
              </div>

              <div className="bg-[#0B111E] border border-[#1B2940] p-3 rounded-2xl">
                <div className="font-bold text-white mb-1">3. Clear Audio Quality</div>
                <p className="text-slate-400">Record in a quiet room with minimal echo using a quality microphone.</p>
              </div>
            </div>

            <div className="flex items-center justify-end">
              <button
                type="button"
                onClick={() => setIsGuideOpen(false)}
                className="bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-bold text-xs px-5 py-2 rounded-xl transition-colors cursor-pointer shadow-xs"
              >
                Got it
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ============================================================ */}
      {/* 7. UPLOAD PHOTO PREVIEW MODAL */}
      {/* ============================================================ */}
      {isUploadPhotoModalOpen && photoPreview && (
        <div
          onClick={() => setIsUploadPhotoModalOpen(false)}
          className="fixed inset-0 z-70 bg-black/75 backdrop-blur-md flex items-center justify-center p-4 animate-in fade-in duration-150"
        >
          <div
            onClick={(e) => e.stopPropagation()}
            className="w-full max-w-sm bg-[#0A0F1A] rounded-3xl p-6 shadow-2xl border border-[#1B2940] text-slate-100 animate-in zoom-in-95 duration-150"
          >
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <ImageIcon size={18} className="text-cyan-400" />
                <h4 className="text-base font-bold text-white">
                  Photo Avatar Preview
                </h4>
              </div>
              <button
                type="button"
                onClick={() => setIsUploadPhotoModalOpen(false)}
                className="text-slate-400 hover:text-white p-1 cursor-pointer"
              >
                <X size={16} />
              </button>
            </div>

            <div className="w-full h-56 rounded-2xl overflow-hidden bg-[#07090e] border border-[#1B2940] mb-4 relative">
              <img
                src={photoPreview}
                alt={photoName}
                className="w-full h-full object-cover object-center"
              />
            </div>

            <p className="text-xs text-slate-400 mb-5 truncate font-medium">
              {photoName}
            </p>

            <div className="flex items-center justify-end gap-2">
              <button
                type="button"
                onClick={() => {
                  photoInputRef.current?.click();
                }}
                className="px-3 py-1.5 text-xs text-slate-400 hover:text-white font-medium cursor-pointer"
              >
                Change Photo
              </button>
              <button
                type="button"
                onClick={handleConfirmPhotoAvatar}
                className="bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-bold text-xs px-5 py-2 rounded-xl transition-colors cursor-pointer shadow-md"
              >
                Use Photo Avatar
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
