"use client";

import React, { useState } from "react";
import LeftRailNav from "@/components/dashboard/LeftRailNav";
import CreateSidebar from "@/components/dashboard/CreateSidebar";
import ManageAvatarsSidebar from "@/components/dashboard/ManageAvatarsSidebar";
import BrandSidebar from "@/components/dashboard/BrandSidebar";
import AppsSidebar from "@/components/dashboard/AppsSidebar";
import ProjectsSidebar from "@/components/dashboard/ProjectsSidebar";
import TemplatesSidebar from "@/components/dashboard/TemplatesSidebar";
import AskRhysWidget from "@/components/dashboard/AskRhysWidget";
import OnboardingSteps from "@/components/dashboard/OnboardingSteps";
import VideoPrompts from "@/components/dashboard/VideoPrompts";
import VoicesLibrary from "@/components/voices/VoicesLibrary";
import AvatarsManager from "@/components/avatars/AvatarsManager";
import DesignLookStudio from "@/components/avatars/DesignLookStudio";
import BrandSystems from "@/components/brand/BrandSystems";
import AppLibrary from "@/components/apps/AppLibrary";
import IntegrationsLibrary from "@/components/apps/IntegrationsLibrary";
import AllAppOutputs from "@/components/apps/AllAppOutputs";
import TranslateVideos, { GlossaryOption } from "@/components/apps/TranslateVideos";
import BrandGlossaryDetail from "@/components/apps/BrandGlossaryDetail";
import ProjectsManager from "@/components/projects/ProjectsManager";
import TemplatesLibrary from "@/components/templates/TemplatesLibrary";
import VideoAgent, { VideoAgentGenerationContext } from "@/components/create/VideoAgent";
import SceneByScene from "@/components/create/SceneByScene";
import SingleScene from "@/components/create/SingleScene";
import TemplateConfigModal from "@/components/create/TemplateConfigModal";
import { VideoAgentTemplate } from "@/components/create/videoAgentData";
import VidoAIStudio from "@/components/studio/VidoAIStudio";
import AuthPage from "@/components/auth/AuthPage";
import DevelopersManager from "@/components/developers/DevelopersManager";
import { useAuth } from "@/context/AuthContext";
import { useTheme } from "@/context/ThemeContext";
import { api } from "@/lib/api";
import { Video } from "lucide-react";

export function DashboardContent({
  initialView = "dashboard",
  initialActiveRailTab = "home",
  initialAvatarSection = "avatars",
}: {
  initialView?:
    | "dashboard"
    | "avatars"
    | "design_look"
    | "voices"
    | "brand"
    | "apps"
    | "projects"
    | "templates"
    | "studio"
    | "video_agent"
    | "scene_by_scene"
    | "single_scene"
    | "translate"
    | "brand_glossary"
    | "developer";
  initialActiveRailTab?: string;
  initialAvatarSection?: "avatars" | "design_look" | "voices";
}) {
  const { user, isAuthenticated, isLoading, currentWorkspace } = useAuth();
  const { theme } = useTheme();
  const isLight = theme === "light";
  const [activeProjectId, setActiveProjectId] = useState<string | null>(null);
  const [currentView, setCurrentView] = useState<
    | "dashboard"
    | "avatars"
    | "design_look"
    | "voices"
    | "brand"
    | "apps"
    | "projects"
    | "templates"
    | "studio"
    | "video_agent"
    | "scene_by_scene"
    | "single_scene"
    | "translate"
    | "brand_glossary"
    | "developer"
  >(initialView);
  const [activeRailTab, setActiveRailTab] = useState(initialActiveRailTab);
  const [activeSidebarSection, setActiveSidebarSection] = useState("home");
  const [activeAvatarSection, setActiveAvatarSection] =
    useState<"avatars" | "design_look" | "voices">(initialAvatarSection);
  const [activeBrandSection, setActiveBrandSection] = useState<"brand_systems" | "brand_glossary">("brand_systems");
  const [activeAppsSection, setActiveAppsSection] = useState<"home" | "integrations" | "outputs">("home");
  const [activeProjectsSection, setActiveProjectsSection] = useState<"my_projects" | "trash">("my_projects");
  const [activeTemplateCategory, setActiveTemplateCategory] = useState("all");
  const [selectedConfigTemplate, setSelectedConfigTemplate] =
    useState<VideoAgentTemplate | null>(null);

  // Dynamic Glossaries Store with unique IDs
  const [brandGlossaries, setBrandGlossaries] = useState<GlossaryOption[]>([]);
  const [selectedBrandGlossaryId, setSelectedBrandGlossaryId] = useState<string>("");
  const [activeGlossaryName, setActiveGlossaryName] = useState<string>("");
  const [brandKitNames, setBrandKitNames] = useState<string[]>([]);
  const [appliedBrandForVideoAgent, setAppliedBrandForVideoAgent] = useState<{
    id?: string;
    name: string;
    color?: string;
    label?: string;
    fonts?: string;
    fullName?: string;
  } | null>(null);
  const [initialVideoAgentPrompt, setInitialVideoAgentPrompt] = useState<string>("");
  const [videoAgentContext, setVideoAgentContext] = useState<VideoAgentGenerationContext | null>(null);

  React.useEffect(() => {
    if (!currentWorkspace?.id) return;
    let cancelled = false;

    api.brandGlossaries
      .list(currentWorkspace.id)
      .then((glossaries) => {
        if (cancelled) return;
        if (Array.isArray(glossaries)) {
          const mapped: GlossaryOption[] = glossaries.map((g) => ({
            id: g.id,
            name: g.name,
          }));
          setBrandGlossaries(mapped);
          if (mapped.length > 0) {
            setSelectedBrandGlossaryId((prev) => prev || mapped[0].id);
            setActiveGlossaryName((prev) => prev || mapped[0].name);
          }
        }
      })
      .catch((err) => {
        console.error("Failed to load brand glossaries:", err);
      });

    api.brandKits
      .list(currentWorkspace.id)
      .then((kits) => {
        if (cancelled) return;
        if (Array.isArray(kits)) {
          setBrandKitNames(kits.map((k) => k.name));
        }
      })
      .catch((err) => {
        console.error("Failed to load brand kits:", err);
      });

    return () => {
      cancelled = true;
    };
  }, [currentWorkspace?.id]);

  const handleKitsChange = React.useCallback((names: string[]) => {
    setBrandKitNames((prev) => {
      if (prev.length === names.length && prev.every((n, i) => n === names[i])) {
        return prev;
      }
      return names;
    });
  }, []);

  const handleGlossariesChange = React.useCallback(
    (gList: { id: string; name: string }[]) => {
      setBrandGlossaries((prev) => {
        if (
          prev.length === gList.length &&
          prev.every((g, i) => g.id === gList[i]?.id && g.name === gList[i]?.name)
        ) {
          return prev;
        }
        return gList.map((g) => ({ id: g.id, name: g.name }));
      });
    },
    []
  );

  // Browser back / forward navigation support
  React.useEffect(() => {
    const handlePopState = (e: PopStateEvent) => {
      if (e.state) {
        if (e.state.view) setCurrentView(e.state.view);
        if (e.state.railTab) setActiveRailTab(e.state.railTab);
        if (e.state.sidebarSection) setActiveSidebarSection(e.state.sidebarSection);
        if (e.state.avatarSection) setActiveAvatarSection(e.state.avatarSection);
        if (e.state.brandSection) setActiveBrandSection(e.state.brandSection);
        if (e.state.appsSection) setActiveAppsSection(e.state.appsSection);
        if (e.state.projectsSection) setActiveProjectsSection(e.state.projectsSection);
        if (e.state.templateCategory) setActiveTemplateCategory(e.state.templateCategory);
        if (e.state.selectedBrandGlossaryId) setSelectedBrandGlossaryId(e.state.selectedBrandGlossaryId);
        if (e.state.glossaryName) setActiveGlossaryName(e.state.glossaryName);
        if (e.state.appliedBrand) setAppliedBrandForVideoAgent(e.state.appliedBrand);
      } else {
        setCurrentView(initialView);
        setActiveRailTab(initialActiveRailTab);
        setActiveAvatarSection(initialAvatarSection);
        setActiveSidebarSection("home");
      }
    };

    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, [initialView, initialActiveRailTab, initialAvatarSection]);

  const pushNavHistory = (updates: {
    view: typeof currentView;
    railTab?: string;
    sidebarSection?: string;
    avatarSection?: typeof activeAvatarSection;
    brandSection?: typeof activeBrandSection;
    appsSection?: typeof activeAppsSection;
    projectsSection?: typeof activeProjectsSection;
    templateCategory?: string;
    selectedBrandGlossaryId?: string;
    glossaryName?: string;
    appliedBrand?: any;
  }) => {
    if (typeof window !== "undefined") {
      window.history.pushState(
        {
          view: updates.view,
          railTab: updates.railTab ?? activeRailTab,
          sidebarSection: updates.sidebarSection ?? activeSidebarSection,
          avatarSection: updates.avatarSection ?? activeAvatarSection,
          brandSection: updates.brandSection ?? activeBrandSection,
          appsSection: updates.appsSection ?? activeAppsSection,
          projectsSection: updates.projectsSection ?? activeProjectsSection,
          templateCategory: updates.templateCategory ?? activeTemplateCategory,
          selectedBrandGlossaryId: updates.selectedBrandGlossaryId ?? selectedBrandGlossaryId,
          glossaryName: updates.glossaryName ?? activeGlossaryName,
          appliedBrand: updates.appliedBrand ?? appliedBrandForVideoAgent,
        },
        ""
      );
    }
  };

  const handleCreateGlossary = async (name: string) => {
    try {
      const created = await api.brandGlossaries.create({ name }, currentWorkspace?.id);
      const newGlossary: GlossaryOption = { id: created.id, name: created.name };
      setBrandGlossaries((prev) => [newGlossary, ...prev]);
      setSelectedBrandGlossaryId(created.id);
      setActiveGlossaryName(created.name);
      setCurrentView("brand_glossary");
      pushNavHistory({
        view: "brand_glossary",
        railTab: "tools",
        selectedBrandGlossaryId: created.id,
        glossaryName: created.name,
      });
    } catch (err) {
      console.error("Failed to create brand glossary:", err);
    }
  };

  const handleSelectAndOpenGlossary = (glossary: GlossaryOption) => {
    setSelectedBrandGlossaryId(glossary.id);
    setActiveGlossaryName(glossary.name);
    setCurrentView("brand_glossary");
    pushNavHistory({
      view: "brand_glossary",
      railTab: "tools",
      selectedBrandGlossaryId: glossary.id,
      glossaryName: glossary.name,
    });
  };

  if (isLoading) {
    return (
      <div className={`min-h-screen w-full flex items-center justify-center ${isLight ? "bg-slate-50" : "bg-[#07090e]"}`}>
        <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  if (!isAuthenticated || !user) {
    return <AuthPage />;
  }

  const handleRailSelect = (tabId: string) => {
    setActiveRailTab(tabId);
    if (tabId === "avatar") {
      setCurrentView("avatars");
      setActiveAvatarSection("avatars");
      pushNavHistory({ view: "avatars", railTab: "avatar", avatarSection: "avatars" });
    } else if (tabId === "brand") {
      setCurrentView("brand");
      setActiveBrandSection("brand_systems");
      pushNavHistory({ view: "brand", railTab: "brand", brandSection: "brand_systems" });
    } else if (tabId === "tools") {
      setCurrentView("apps");
      setActiveAppsSection("home");
      pushNavHistory({ view: "apps", railTab: "tools", appsSection: "home" });
    } else if (tabId === "projects") {
      setCurrentView("projects");
      setActiveProjectsSection("my_projects");
      pushNavHistory({ view: "projects", railTab: "projects", projectsSection: "my_projects" });
    } else if (tabId === "templates") {
      setCurrentView("templates");
      setActiveTemplateCategory("all");
      pushNavHistory({ view: "templates", railTab: "templates", templateCategory: "all" });
    } else if (tabId === "developer") {
      setCurrentView("developer");
      pushNavHistory({ view: "developer", railTab: "developer" });
    } else if (tabId === "home") {
      setCurrentView("dashboard");
      setActiveSidebarSection("home");
      pushNavHistory({ view: "dashboard", railTab: "home", sidebarSection: "home" });
    }
  };

  const handleAvatarSidebarSelect = (section: "avatars" | "design_look" | "voices") => {
    setActiveAvatarSection(section);
    if (section === "avatars") {
      setCurrentView("avatars");
      pushNavHistory({ view: "avatars", avatarSection: "avatars" });
    } else if (section === "voices") {
      setCurrentView("voices");
      pushNavHistory({ view: "voices", avatarSection: "voices" });
    } else if (section === "design_look") {
      setCurrentView("design_look");
      pushNavHistory({ view: "design_look", avatarSection: "design_look" });
    }
  };

  const handleOpenStudio = async (projectId?: string | React.MouseEvent) => {
    if (typeof projectId === "string") {
      setActiveProjectId(projectId);
      setCurrentView("studio");
      pushNavHistory({ view: "studio" });
      return;
    }
    if (currentWorkspace?.id) {
      try {
        const newProj = await api.projects.create(currentWorkspace.id, {
          title: "Untitled Video Project",
          project_type: "avatar_video",
          aspect_ratio: "16:9",
        });
        setActiveProjectId(newProj.id);
        setCurrentView("studio");
        pushNavHistory({ view: "studio" });
        return;
      } catch (err) {
        console.error("Failed to auto-create studio project:", err);
      }
    }
    setActiveProjectId(null);
    setCurrentView("studio");
    pushNavHistory({ view: "studio" });
  };

  const handleNavigateProjects = () => {
    setCurrentView("projects");
    setActiveRailTab("projects");
    setActiveProjectsSection("my_projects");
    pushNavHistory({
      view: "projects",
      railTab: "projects",
      projectsSection: "my_projects",
    });
  };

  const handleSidebarSelect = (section: string) => {
    setActiveSidebarSection(section);
    if (section === "scene_by_scene") {
      setCurrentView("scene_by_scene");
      setActiveRailTab("home");
      pushNavHistory({
        view: "scene_by_scene",
        railTab: "home",
        sidebarSection: "scene_by_scene",
      });
    } else if (section === "single_scene") {
      setCurrentView("single_scene");
      setActiveRailTab("home");
      pushNavHistory({
        view: "single_scene",
        railTab: "home",
        sidebarSection: "single_scene",
      });
    } else if (section === "video_agent") {
      setVideoAgentContext(null);
      setInitialVideoAgentPrompt("");
      setCurrentView("video_agent");
      setActiveRailTab("home");
      pushNavHistory({
        view: "video_agent",
        railTab: "home",
        sidebarSection: "video_agent",
      });
    } else if (section === "translate") {
      setCurrentView("translate");
      setActiveRailTab("home");
      pushNavHistory({
        view: "translate",
        railTab: "home",
        sidebarSection: "translate",
      });
    } else {
      setCurrentView("dashboard");
      setActiveRailTab("home");
      pushNavHistory({
        view: "dashboard",
        railTab: "home",
        sidebarSection: "home",
      });
    }
  };

  const handleLaunchVideoAgentWithContext = (context: VideoAgentGenerationContext) => {
    setVideoAgentContext(context);
    setInitialVideoAgentPrompt(context.userPrompt || context.prompt || "");
    setCurrentView("video_agent");
    setActiveRailTab("create");
    setActiveSidebarSection("video_agent");
    pushNavHistory({
      view: "video_agent",
      railTab: "create",
      sidebarSection: "video_agent",
    });
  };

  const handleOnboardingNavigate = (view: string) => {
    if (view === "voices") {
      handleAvatarSidebarSelect("voices");
    } else if (view === "design_look") {
      handleAvatarSidebarSelect("design_look");
    } else if (view === "video_agent") {
      handleSidebarSelect("video_agent");
    } else if (view === "avatars") {
      handleAvatarSidebarSelect("avatars");
    } else {
      setCurrentView(view as any);
      pushNavHistory({ view: view as any });
    }
  };

  if (currentView === "studio") {
    return (
      <VidoAIStudio
        projectId={activeProjectId || undefined}
        workspaceId={currentWorkspace?.id}
        onBackToDashboard={() => {
          setCurrentView("dashboard");
          setActiveRailTab("home");
          pushNavHistory({ view: "dashboard", railTab: "home" });
        }}
      />
    );
  }

  if (currentView === "video_agent") {
    return (
      <VideoAgent
        workspaceId={currentWorkspace?.id}
        workspaceName={currentWorkspace?.name || "Personal Workspace"}
        appliedBrandSystem={appliedBrandForVideoAgent}
        initialPrompt={initialVideoAgentPrompt}
        generationContext={videoAgentContext}
        onOpenStudio={(projId) => handleOpenStudio(projId)}
        onBackToDashboard={() => {
          const fromApp =
            videoAgentContext?.sourceApp === "ppt_pdf_to_video" ||
            videoAgentContext?.sourceApp === "cinematic_shots";
          setVideoAgentContext(null);
          setInitialVideoAgentPrompt("");
          if (fromApp) {
            setCurrentView("apps");
            setActiveRailTab("tools");
            setActiveAppsSection("home");
            pushNavHistory({ view: "apps", railTab: "tools", appsSection: "home" });
          } else {
            setCurrentView("dashboard");
            setActiveRailTab("home");
            setActiveSidebarSection("home");
            pushNavHistory({ view: "dashboard", railTab: "home", sidebarSection: "home" });
          }
        }}
      />
    );
  }

  const isAvatarContext =
    currentView === "avatars" || currentView === "design_look" || currentView === "voices";

  return (
    <main
      className={`min-h-screen flex overflow-hidden font-sans transition-colors ${
        isLight ? "bg-slate-50 text-slate-900" : "bg-[#07090e] text-slate-100"
      }`}
    >
      {/* 1. Left Slim Icon Navigation Rail */}
      <LeftRailNav
        activeTab={activeRailTab}
        onSelectTab={handleRailSelect}
        onLogoClick={() => {
          setActiveRailTab("home");
          setCurrentView("dashboard");
        }}
      />

      {/* 2. Secondary Sidebar - Context Aware */}
      {isAvatarContext ? (
        <ManageAvatarsSidebar
          activeSection={activeAvatarSection}
          onSelectSection={handleAvatarSidebarSelect}
        />
      ) : currentView === "brand" ? (
        <BrandSidebar
          activeSection={activeBrandSection}
          brandKits={brandKitNames}
          brandGlossaries={brandGlossaries}
          selectedGlossaryId={selectedBrandGlossaryId}
          onSelectSection={(sec) => {
            setActiveBrandSection(sec);
            pushNavHistory({ view: "brand", railTab: "brand", brandSection: sec });
          }}
          onSelectGlossary={(id, name) => {
            setSelectedBrandGlossaryId(id);
            setActiveGlossaryName(name);
          }}
        />
      ) : activeRailTab === "tools" && (currentView === "apps" || currentView === "brand_glossary") ? (
        <AppsSidebar
          activeSection={currentView === "brand_glossary" ? "translate" : activeAppsSection}
          theme={theme}
          onOpenProject={handleOpenStudio}
          onSeeAllProjects={handleNavigateProjects}
          onSelectSection={(sec) => {
            if (sec === "translate") {
              setCurrentView("translate");
              pushNavHistory({ view: "translate", railTab: "tools" });
            } else {
              setCurrentView("apps");
              setActiveAppsSection(sec as any);
              pushNavHistory({ view: "apps", railTab: "tools", appsSection: sec });
            }
          }}
          onSeeAllOutputs={() => {
            setCurrentView("apps");
            setActiveAppsSection("outputs");
            pushNavHistory({ view: "apps", railTab: "tools", appsSection: "outputs" });
          }}
        />
      ) : currentView === "projects" ? (
        <ProjectsSidebar
          activeSection={activeProjectsSection}
          onSelectSection={(sec) => setActiveProjectsSection(sec as "my_projects" | "trash")}
        />
      ) : currentView === "templates" ? (
        <TemplatesSidebar
          activeCategory={activeTemplateCategory}
          onSelectCategory={(cat) => setActiveTemplateCategory(cat)}
        />
      ) : currentView === "developer" ? null : (
        <CreateSidebar
          activeSection={currentView === "translate" ? "translate" : activeSidebarSection}
          onSelectSection={handleSidebarSelect}
          onOpenProject={handleOpenStudio}
          onSeeAllRecents={handleNavigateProjects}
        />
      )}

      {/* 3. Main Workspace Area */}
      {currentView === "developer" ? (
        <DevelopersManager />
      ) : currentView === "avatars" ? (
        <AvatarsManager onOpenStudio={handleOpenStudio} />
      ) : currentView === "design_look" ? (
        <DesignLookStudio onOpenStudio={handleOpenStudio} />
      ) : currentView === "voices" ? (
        <VoicesLibrary />
      ) : currentView === "brand" ? (
        <BrandSystems
          activeSubSection={activeBrandSection}
          onKitsChange={handleKitsChange}
          onGlossariesChange={handleGlossariesChange}
          onUseSystemInVideoAgent={(brandSystem) => {
            const brandObj = {
              id: brandSystem.id || (typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : "brand_default"),
              name: brandSystem.name,
              fullName: `${brandSystem.name} Brand System`,
              color: brandSystem.primaryColor || "#000000",
              label: "Brand System",
              fonts: brandSystem.fontFamily || "Brand Spec",
            };
            setAppliedBrandForVideoAgent(brandObj);
            setCurrentView("video_agent");
            setActiveRailTab("create");
            setActiveSidebarSection("video_agent");
            pushNavHistory({
              view: "video_agent",
              railTab: "create",
              sidebarSection: "video_agent",
              appliedBrand: brandObj,
            });
          }}
          onOpenStudio={handleOpenStudio}
        />
      ) : currentView === "brand_glossary" ? (
        <BrandGlossaryDetail
          glossaryName={
            brandGlossaries.find((g) => g.id === selectedBrandGlossaryId)?.name ||
            activeGlossaryName ||
            brandGlossaries[0]?.name ||
            "Brand Glossary"
          }
          onBack={() => {
            setCurrentView("translate");
            pushNavHistory({
              view: "translate",
              railTab: "tools",
              selectedBrandGlossaryId: selectedBrandGlossaryId,
              glossaryName: activeGlossaryName,
            });
          }}
          onOpenStudio={handleOpenStudio}
        />
      ) : currentView === "translate" ? (
        <TranslateVideos
          glossaries={brandGlossaries}
          selectedGlossaryId={selectedBrandGlossaryId}
          selectedGlossary={activeGlossaryName}
          onSelectGlossary={(name) => {
            setActiveGlossaryName(name);
            const match = brandGlossaries.find((g) => g.name === name);
            if (match) setSelectedBrandGlossaryId(match.id);
          }}
          onSelectAndOpenGlossary={handleSelectAndOpenGlossary}
          onCreateGlossary={handleCreateGlossary}
          onNavigateCreateGlossary={handleCreateGlossary}
          onBack={() => {
            setCurrentView("apps");
            setActiveAppsSection("home");
            pushNavHistory({ view: "apps", railTab: "tools", appsSection: "home" });
          }}
          onOpenStudio={handleOpenStudio}
        />
      ) : currentView === "apps" ? (
        activeAppsSection === "outputs" ? (
          <AllAppOutputs
            onBack={() => setActiveAppsSection("home")}
            onOpenStudio={handleOpenStudio}
          />
        ) : activeAppsSection === "integrations" ? (
          <IntegrationsLibrary onOpenStudio={handleOpenStudio} />
        ) : (
          <AppLibrary
            onOpenStudio={handleOpenStudio}
            onNavigateVideoAgent={() => {
              setVideoAgentContext(null);
              setInitialVideoAgentPrompt("");
              handleSidebarSelect("video_agent");
            }}
            onLaunchVideoAgentWithContext={handleLaunchVideoAgentWithContext}
            onNavigateTranslate={() => {
              setCurrentView("translate");
              setActiveRailTab("tools");
              pushNavHistory({ view: "translate", railTab: "tools" });
            }}
            onNavigateSingleScene={() => {
              setCurrentView("single_scene");
              setActiveRailTab("home");
              pushNavHistory({ view: "single_scene", railTab: "home" });
            }}
            onNavigateSceneByScene={() => {
              setCurrentView("scene_by_scene");
              setActiveRailTab("home");
              pushNavHistory({ view: "scene_by_scene", railTab: "home" });
            }}
            onNavigateBrand={() => {
              setCurrentView("brand");
              setActiveRailTab("brand");
              pushNavHistory({ view: "brand", railTab: "brand" });
            }}
            onNavigateDesignLook={() => {
              setCurrentView("design_look");
              setActiveRailTab("avatar");
              setActiveAvatarSection("design_look");
              pushNavHistory({ view: "design_look", railTab: "avatar" });
            }}
            onNavigateProjects={handleNavigateProjects}
          />
        )
      ) : currentView === "projects" ? (
        <ProjectsManager
          activeSection={activeProjectsSection}
          onOpenStudio={handleOpenStudio}
        />
      ) : currentView === "templates" ? (
        <TemplatesLibrary
          activeCategory={activeTemplateCategory}
          onOpenStudio={handleOpenStudio}
        />
      ) : currentView === "single_scene" ? (
        <SingleScene
          onOpenStudio={handleOpenStudio}
          onNavigateVoices={() => {
            setCurrentView("voices");
            setActiveRailTab("avatar");
            setActiveAvatarSection("voices");
            pushNavHistory({
              view: "voices",
              railTab: "avatar",
              avatarSection: "voices",
            });
          }}
          onSeeAllProjects={handleNavigateProjects}
        />
      ) : currentView === "scene_by_scene" ? (
        <SceneByScene
          onOpenStudio={handleOpenStudio}
          onSelectTemplate={() => handleOpenStudio()}
          onSeeAllProjects={handleNavigateProjects}
        />
      ) : (
        <div className={`flex-1 h-screen overflow-y-auto flex flex-col ${isLight ? "bg-slate-50 text-slate-900" : "bg-[#07090e] text-slate-100"}`}>
          {/* Top Header with Studio Switcher & Ask Rhys */}
          <header className="w-full px-8 py-4 flex items-center justify-between z-20">
            <div className="flex items-center gap-3">
              <button
                id="open-studio-header-btn"
                data-testid="open-studio-header-btn"
                onClick={() => handleOpenStudio()}
                className={`px-3.5 py-1.5 rounded-full text-xs font-semibold flex items-center gap-1.5 transition-all shadow-sm cursor-pointer ${
                  isLight
                    ? "bg-white hover:bg-slate-100 border border-slate-300 text-blue-600 hover:border-blue-400"
                    : "bg-[#121828] hover:bg-[#1a233a] border border-[#222f4d] hover:border-[#384c7a] text-blue-400"
                }`}
              >
                <Video size={14} /> Open VidoAI Studio Editor
              </button>
            </div>

            <div className="flex items-center gap-3">
              <AskRhysWidget />
            </div>
          </header>

          {/* Hero & Content Container */}
          <div className="max-w-6xl w-full mx-auto px-8 pb-12">
            {/* Welcome Greeting Header (Dynamic) */}
            <div className="text-center mt-2 mb-8">
              <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight">
                <span className={isLight ? "text-slate-900" : "text-white"}>Welcome, </span>
                <span className="bg-gradient-to-r from-cyan-400 via-sky-400 to-blue-500 bg-clip-text text-transparent">
                  {user.name}
                </span>
              </h1>
            </div>

            {/* Account Setup 4-Step Cards */}
            <div className="mb-6">
              <OnboardingSteps
                workspaceId={currentWorkspace?.id}
                onNavigate={handleOnboardingNavigate}
                onOpenStudio={handleOpenStudio}
              />
            </div>

            {/* Video Prompts 2x2 Rich Templates Grid */}
            <div>
              <VideoPrompts
                onSelectPrompt={(tpl, card) => {
                  const promptContext = card?.description
                    ? `${card.title} - ${card.description}`
                    : (tpl?.description || tpl?.defaultScript || tpl?.title || card?.title || "Video Creation");
                  const templateToUse = tpl || {
                    id: card?.id || "prompt_template",
                    title: card?.title || "Video Template",
                    category: card?.category || "General",
                    image: "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?q=80&w=800&auto=format&fit=crop",
                    description: card?.description,
                    defaultScript: promptContext,
                  };
                  setSelectedConfigTemplate(templateToUse);
                }}
              />
            </div>
          </div>

          {/* Template Configuration Modal when opened from Home Page */}
          {selectedConfigTemplate && (
            <TemplateConfigModal
              isOpen={!!selectedConfigTemplate}
              template={selectedConfigTemplate}
              onClose={() => setSelectedConfigTemplate(null)}
              onContinue={(config) => {
                setSelectedConfigTemplate(null);
                const fullPrompt =
                  config.script ||
                  config.template?.defaultScript ||
                  config.template?.title ||
                  "AI Video Project";
                setVideoAgentContext({
                  prompt: fullPrompt,
                  avatar: config.avatar,
                  voice: config.voice,
                  look: config.look,
                  captions: config.captions,
                  brandSystem: config.brand,
                  attachments: config.attachments,
                  speed: config.speed,
                  quality: config.quality,
                  seedance: config.seedance,
                  template: config.template,
                });
                setInitialVideoAgentPrompt(fullPrompt);
                setCurrentView("video_agent");
                pushNavHistory({
                  view: "video_agent",
                  railTab: "home",
                  sidebarSection: "video_agent",
                });
              }}
            />
          )}
        </div>
      )}
    </main>
  );
}

export default function Home() {
  return <DashboardContent />;
}
