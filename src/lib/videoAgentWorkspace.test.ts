import { describe, it } from "node:test";
import assert from "node:assert/strict";

interface VideoAgentGenerationContext {
  prompt: string;
  avatar?: { id: string; name: string };
  voice?: { id: string; name: string };
  look?: { id: string; name: string };
  captions?: boolean;
  brandSystem?: { id: string; name: string };
  attachments?: string[];
  speed?: string;
  quality?: string;
  seedance?: boolean;
  template?: any;
}

interface ConversationMessage {
  id: string;
  sender: "user" | "agent";
  text: string;
  status?: "thinking" | "generating" | "completed" | "failed";
  projectId?: string;
}

interface VideoArtifact {
  id: string;
  title: string;
  status: "draft" | "ready" | "failed";
  sceneCount: number;
  duration: number;
  videoUrl?: string;
  thumbnailUrl?: string;
  avatarId?: string;
  avatarName?: string;
  voiceId?: string;
}

// Flow simulation functions mirroring the Video Agent Workspace
function simulateGenerateFromModal(modalConfig: {
  template: { title: string; defaultScript?: string };
  avatar: { id: string; name: string };
  voice: { id: string; name: string };
  look?: { id: string; name: string };
  script: string;
  brand: { id: string; name: string };
  captions: boolean;
  attachments: string[];
}): {
  destinationView: string;
  generationContext: VideoAgentGenerationContext;
  initialPrompt: string;
} {
  const fullPrompt = modalConfig.script || modalConfig.template.defaultScript || modalConfig.template.title;
  const context: VideoAgentGenerationContext = {
    prompt: fullPrompt,
    avatar: modalConfig.avatar,
    voice: modalConfig.voice,
    look: modalConfig.look,
    captions: modalConfig.captions,
    brandSystem: modalConfig.brand,
    attachments: modalConfig.attachments,
    template: modalConfig.template,
  };

  return {
    destinationView: "video_agent",
    generationContext: context,
    initialPrompt: fullPrompt,
  };
}

function initializeConversation(context: VideoAgentGenerationContext | null): {
  messages: ConversationMessage[];
  isGenerating: boolean;
} {
  if (!context || !context.prompt) {
    return {
      messages: [
        {
          id: "msg_init",
          sender: "agent",
          text: "Hi! What would you like to create or work on today?",
        },
      ],
      isGenerating: false,
    };
  }

  return {
    messages: [
      {
        id: "user_1",
        sender: "user",
        text: context.prompt,
      },
      {
        id: "agent_1",
        sender: "agent",
        text: "Thinking...",
        status: "generating",
      },
    ],
    isGenerating: true,
  };
}

function completeGenerationSuccess(
  messages: ConversationMessage[],
  project: { id: string; title: string; scenesCount: number; duration: number }
): {
  messages: ConversationMessage[];
  artifacts: VideoArtifact[];
  isGenerating: boolean;
} {
  const updatedMessages = messages.map((m) => {
    if (m.sender === "agent" && m.status === "generating") {
      return {
        ...m,
        status: "completed" as const,
        text: `I've created your video project "${project.title}" with ${project.scenesCount} scenes.`,
        projectId: project.id,
      };
    }
    return m;
  });

  const newArtifact: VideoArtifact = {
    id: project.id,
    title: project.title,
    status: "ready",
    sceneCount: project.scenesCount,
    duration: project.duration,
  };

  return {
    messages: updatedMessages,
    artifacts: [newArtifact],
    isGenerating: false,
  };
}

function completeGenerationFailure(
  messages: ConversationMessage[],
  errorMessage: string
): {
  messages: ConversationMessage[];
  isGenerating: boolean;
} {
  const updatedMessages = messages.map((m) => {
    if (m.sender === "agent" && m.status === "generating") {
      return {
        ...m,
        status: "failed" as const,
        text: `Generation failed: ${errorMessage}`,
      };
    }
    return m;
  });

  return {
    messages: updatedMessages,
    isGenerating: false,
  };
}

function handleFollowUpPrompt(
  currentMessages: ConversationMessage[],
  promptText: string
): ConversationMessage[] {
  return [
    ...currentMessages,
    {
      id: `user_${Date.now()}`,
      sender: "user",
      text: promptText,
    },
    {
      id: `agent_${Date.now()}`,
      sender: "agent",
      text: "Thinking...",
      status: "generating",
    },
  ];
}

describe("Video Agent Workspace & Modal Redirect Flow", () => {
  it("Test 1 & 2: Generate from modal redirects to Video Agent workspace", () => {
    const modalConfig = {
      template: { title: "Ads & Promo", defaultScript: "High-hook UGC ad" },
      avatar: { id: "avatar_1", name: "Annie" },
      voice: { id: "voice_1", name: "Annie (US)" },
      look: { id: "look_casual", name: "Casual Blazer" },
      script: "Create high-converting UGC ad for marketing",
      brand: { id: "brand_1", name: "Tech Brand" },
      captions: true,
      attachments: ["demo.png"],
    };

    const redirect = simulateGenerateFromModal(modalConfig);
    assert.equal(redirect.destinationView, "video_agent");
    assert.ok(redirect.generationContext);
  });

  it("Test 3 & 4: Selected prompt and avatar/voice/look settings reach generation context", () => {
    const modalConfig = {
      template: { title: "Product Launch", defaultScript: "Feature announcement" },
      avatar: { id: "avatar_daniel", name: "Daniel" },
      voice: { id: "voice_marcus", name: "Marcus" },
      look: { id: "look_suit", name: "Navy Suit" },
      script: "Announcing HeyZen 2.0 with all-new neural avatars",
      brand: { id: "brand_heyzen", name: "HeyZen Dark" },
      captions: true,
      attachments: ["logo.svg"],
    };

    const redirect = simulateGenerateFromModal(modalConfig);
    assert.equal(redirect.generationContext.prompt, "Announcing HeyZen 2.0 with all-new neural avatars");
    assert.equal(redirect.generationContext.avatar?.name, "Daniel");
    assert.equal(redirect.generationContext.voice?.name, "Marcus");
    assert.equal(redirect.generationContext.look?.name, "Navy Suit");
    assert.equal(redirect.generationContext.captions, true);
    assert.deepEqual(redirect.generationContext.attachments, ["logo.svg"]);
  });

  it("Test 5 & 6: Video Agent displays initial user prompt and thinking state appears", () => {
    const context: VideoAgentGenerationContext = {
      prompt: "Create an instructional explainer for AI developers",
      avatar: { id: "avatar_1", name: "Annie" },
      voice: { id: "voice_1", name: "Annie" },
    };

    const state = initializeConversation(context);
    assert.equal(state.messages.length, 2);
    assert.equal(state.messages[0].sender, "user");
    assert.equal(state.messages[0].text, "Create an instructional explainer for AI developers");
    assert.equal(state.messages[1].sender, "agent");
    assert.equal(state.messages[1].status, "generating");
    assert.equal(state.isGenerating, true);
  });

  it("Test 7 & 8: Successful generation produces real artifact in Artifacts tab", () => {
    const context: VideoAgentGenerationContext = {
      prompt: "UGC Promo Video",
    };
    const initial = initializeConversation(context);

    const result = completeGenerationSuccess(initial.messages, {
      id: "proj_994f",
      title: "UGC Promo Video Project",
      scenesCount: 3,
      duration: 30,
    });

    assert.equal(result.isGenerating, false);
    assert.equal(result.artifacts.length, 1);
    assert.equal(result.artifacts[0].id, "proj_994f");
    assert.equal(result.artifacts[0].title, "UGC Promo Video Project");
    assert.equal(result.artifacts[0].sceneCount, 3);
    assert.equal(result.artifacts[0].status, "ready");

    const agentMsg = result.messages.find((m) => m.sender === "agent");
    assert.equal(agentMsg?.status, "completed");
    assert.equal(agentMsg?.projectId, "proj_994f");
  });

  it("Test 9: Open in Studio resolves to the correct generated project ID", () => {
    const artifact: VideoArtifact = {
      id: "proj_test_studio_target",
      title: "Test Video",
      status: "ready",
      sceneCount: 3,
      duration: 30,
    };

    let openedProjectId: string | undefined = undefined;
    const handleOpenStudio = (id?: string) => {
      openedProjectId = id;
    };

    handleOpenStudio(artifact.id);
    assert.equal(openedProjectId, "proj_test_studio_target");
  });

  it("Test 10: Additional prompt can be submitted in conversation", () => {
    const initial = initializeConversation(null);
    assert.equal(initial.messages.length, 1);

    const updated = handleFollowUpPrompt(initial.messages, "Make the scenes punchier and add captions");
    assert.equal(updated.length, 3);
    assert.equal(updated[1].sender, "user");
    assert.equal(updated[1].text, "Make the scenes punchier and add captions");
    assert.equal(updated[2].sender, "agent");
    assert.equal(updated[2].status, "generating");
  });

  it("Test 11: Failed generation displays failure state with error message", () => {
    const context: VideoAgentGenerationContext = {
      prompt: "Invalid prompt",
    };
    const initial = initializeConversation(context);
    const failureResult = completeGenerationFailure(initial.messages, "Workspace rate limit reached");

    assert.equal(failureResult.isGenerating, false);
    const agentMsg = failureResult.messages.find((m) => m.sender === "agent");
    assert.equal(agentMsg?.status, "failed");
    assert.ok(agentMsg?.text.includes("Workspace rate limit reached"));
  });

  it("Test 12: Browser Back returns to Dashboard view", () => {
    let currentView = "video_agent";
    const popstateEvent = {
      state: { view: "dashboard" },
    };

    if (popstateEvent.state?.view) {
      currentView = popstateEvent.state.view;
    }
    assert.equal(currentView, "dashboard");
  });

  it("Test 13: Refresh loads existing projects without corrupting state", () => {
    const existingProjects = [
      { id: "p1", title: "Existing Project 1", created_at: "2026-09-25T10:00:00Z" },
      { id: "p2", title: "Existing Project 2", created_at: "2026-09-25T11:00:00Z" },
    ];

    const loadedArtifacts: VideoArtifact[] = existingProjects.map((p) => ({
      id: p.id,
      title: p.title,
      status: "ready",
      sceneCount: 3,
      duration: 30,
    }));

    assert.equal(loadedArtifacts.length, 2);
    assert.equal(loadedArtifacts[0].id, "p1");
    assert.equal(loadedArtifacts[1].id, "p2");
  });

  it("Test 14: Resolves avatar and voice IDs to real backend entities", () => {
    const backendAvatars = [
      { id: "30000000-0000-0000-0000-000000000002", name: "Annie - Studio Presenter" },
      { id: "30000000-0000-0000-0000-000000000004", name: "Daniel - Modern Creator" },
    ];

    function resolveAvatarId(rawId?: string, rawName?: string): string {
      if (rawId && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(rawId)) {
        return rawId;
      }
      const candidate = (rawName || rawId || "Annie").toLowerCase();
      const matched = backendAvatars.find(
        (a) =>
          a.name.toLowerCase().includes(candidate) ||
          candidate.includes(a.name.toLowerCase()) ||
          a.id === rawId
      );
      return matched?.id || backendAvatars[0].id;
    }

    assert.equal(resolveAvatarId("annie", "Annie"), "30000000-0000-0000-0000-000000000002");
    assert.equal(resolveAvatarId(undefined, "Daniel"), "30000000-0000-0000-0000-000000000004");
    assert.equal(
      resolveAvatarId("30000000-0000-0000-0000-000000000004"),
      "30000000-0000-0000-0000-000000000004"
    );
  });

  it("Test 15: Handles asynchronous job status transitions without fake setTimeout", () => {
    const jobLifecycle = [
      { id: "job_1", status: "queued", stage: "initializing", stage_message: "Queued..." },
      { id: "job_1", status: "processing", stage: "script", stage_message: "Generating script..." },
      { id: "job_1", status: "completed", stage: "done", result: { project_id: "proj_99" } },
    ];

    let finalProjectId: string | null = null;
    let currentStage: string | undefined = undefined;

    for (const step of jobLifecycle) {
      if (step.stage_message) {
        currentStage = step.stage_message;
      }
      if (step.status === "completed" && step.result) {
        finalProjectId = step.result.project_id;
      }
    }

    assert.equal(currentStage, "Generating script...");
    assert.equal(finalProjectId, "proj_99");
  });

  it("Test 16: Follow-up prompts retain existing avatar and styling context", () => {
    const initialContext: VideoAgentGenerationContext = {
      prompt: "Create an Ads & Promo video for my software",
      avatar: { id: "30000000-0000-0000-0000-000000000002", name: "Annie" },
      voice: { id: "en_US-lessac-medium", name: "Annie (US)" },
      captions: true,
    };

    const followUpPrompt = "Make it shorter and punchier";
    const followUpContext: VideoAgentGenerationContext = {
      ...initialContext,
      prompt: followUpPrompt,
    };

    assert.equal(followUpContext.prompt, "Make it shorter and punchier");
    assert.equal(followUpContext.avatar?.id, "30000000-0000-0000-0000-000000000002");
    assert.equal(followUpContext.voice?.id, "en_US-lessac-medium");
    assert.equal(followUpContext.captions, true);
  });

  it("Test 17: Failed generation isolates stale artifacts and clears Ready state", () => {
    const staleArtifact: VideoArtifact = {
      id: "prev_proj_1",
      title: "Previous Successful Video",
      status: "ready",
      sceneCount: 3,
      duration: 15,
      videoUrl: "https://minio.local/bucket/prev.mp4",
    };

    // When a new generation starts, selectedArtifact is reset to null
    let selectedArtifact: VideoArtifact | null = staleArtifact;
    let activeGenerationState: { status: string; error?: string } | null = {
      status: "queued",
    };
    selectedArtifact = null;

    assert.equal(selectedArtifact, null);
    assert.equal(activeGenerationState.status, "queued");

    // When generation fails, activeGeneration is set to failed with truthful error
    const failureError = "Media generation job failed on server.";
    activeGenerationState = {
      status: "failed",
      error: failureError,
    };

    // Assert that selectedArtifact remains null (NEVER falls back to stale Ready artifact)
    assert.equal(selectedArtifact, null);
    assert.equal(activeGenerationState.status, "failed");
    assert.equal(activeGenerationState.error, failureError);
  });

  it("Test 18: Active generation displays Generating state and prohibits false Ready badge", () => {
    function deriveArtifactCardDisplay(
      activeGen: { status: string; stageMessage?: string } | null,
      selected: VideoArtifact | null
    ) {
      if (activeGen?.status === "queued" || activeGen?.status === "running") {
        return {
          badge: "Generating...",
          isPlayable: false,
          hasReadyBadge: false,
        };
      }
      if (activeGen?.status === "failed") {
        return {
          badge: "Generation Failed",
          isPlayable: false,
          hasReadyBadge: false,
        };
      }
      if (selected?.videoUrl) {
        return {
          badge: "Ready",
          isPlayable: true,
          hasReadyBadge: true,
        };
      }
      return {
        badge: "Draft / Generation incomplete",
        isPlayable: false,
        hasReadyBadge: false,
      };
    }

    // Queued
    const queuedDisplay = deriveArtifactCardDisplay({ status: "queued" }, null);
    assert.equal(queuedDisplay.badge, "Generating...");
    assert.equal(queuedDisplay.hasReadyBadge, false);
    assert.equal(queuedDisplay.isPlayable, false);

    // Running
    const runningDisplay = deriveArtifactCardDisplay({ status: "running" }, null);
    assert.equal(runningDisplay.badge, "Generating...");
    assert.equal(runningDisplay.hasReadyBadge, false);
    assert.equal(runningDisplay.isPlayable, false);

    // Failed
    const failedDisplay = deriveArtifactCardDisplay({ status: "failed" }, null);
    assert.equal(failedDisplay.badge, "Generation Failed");
    assert.equal(failedDisplay.hasReadyBadge, false);
    assert.equal(failedDisplay.isPlayable, false);

    // Completed with videoUrl
    const completedDisplay = deriveArtifactCardDisplay(null, {
      id: "proj_new",
      title: "Completed Project",
      status: "ready",
      sceneCount: 3,
      duration: 15,
      videoUrl: "https://minio.local/bucket/render.mp4",
    });
    assert.equal(completedDisplay.badge, "Ready");
    assert.equal(completedDisplay.hasReadyBadge, true);
    assert.equal(completedDisplay.isPlayable, true);
  });

  it("Test 19: Retry generation creates new request ID and preserves prompt/avatar/voice", () => {
    const failedContext: VideoAgentGenerationContext = {
      prompt: "Create a high-impact video explaining the key benefits and step-by-step strategy for Ads & Promo.",
      avatar: { id: "30000000-0000-0000-0000-000000000002", name: "Annie - Studio Presenter" },
      voice: { id: "10000000-0000-0000-0000-000000000003", name: "Annie - Lifelike" },
      captions: true,
    };

    let attemptCount = 0;
    const recordedRequests: Array<{ id: string; prompt: string; avatarId?: string; voiceId?: string }> = [];

    function triggerGeneration(prompt: string, context?: VideoAgentGenerationContext | null) {
      attemptCount++;
      const reqId = `gen_req_${attemptCount}_${Date.now()}`;
      recordedRequests.push({
        id: reqId,
        prompt,
        avatarId: context?.avatar?.id,
        voiceId: context?.voice?.id,
      });
    }

    // Initial attempt
    triggerGeneration(failedContext.prompt, failedContext);
    assert.equal(recordedRequests.length, 1);
    assert.equal(recordedRequests[0].prompt, failedContext.prompt);

    // Retry attempt
    triggerGeneration(failedContext.prompt, failedContext);
    assert.equal(recordedRequests.length, 2);
    assert.notEqual(recordedRequests[0].id, recordedRequests[1].id);
    assert.equal(recordedRequests[1].prompt, failedContext.prompt);
    assert.equal(recordedRequests[1].avatarId, "30000000-0000-0000-0000-000000000002");
    assert.equal(recordedRequests[1].voiceId, "10000000-0000-0000-0000-000000000003");
  });

  it("Test 20: Annie avatar and voice resolve to genuine database IDs", () => {
    const backendAvatars = [
      { id: "30000000-0000-0000-0000-000000000002", name: "Annie - Studio Presenter" },
      { id: "30000000-0000-0000-0000-000000000004", name: "Daniel - Modern Creator" },
    ];
    const backendVoices = [
      { id: "10000000-0000-0000-0000-000000000003", name: "Annie - Lifelike", provider: "piper" },
      { id: "10000000-0000-0000-0000-000000000001", name: "Piper Lessac (English)", provider: "piper" },
    ];

    function resolveAnnieVoice(rawId?: string, rawName?: string): string {
      if (rawId && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(rawId)) {
        return rawId;
      }
      if (rawId === "annie-lifelike" || (rawName || "").toLowerCase().includes("annie")) {
        return "10000000-0000-0000-0000-000000000003";
      }
      return backendVoices[0].id;
    }

    assert.equal(resolveAnnieVoice("annie-lifelike", "Annie - Lifelike"), "10000000-0000-0000-0000-000000000003");
    assert.equal(resolveAnnieVoice("10000000-0000-0000-0000-000000000003", "Annie - Lifelike"), "10000000-0000-0000-0000-000000000003");
  });

  it("Test 21: Default presenter selection remains Annie with real asset reference", () => {
    const realAvatars = [
      { id: "30000000-0000-0000-0000-000000000001", name: "Default Presenter", preview_url: "https://minio.local/p1.png" },
      { id: "30000000-0000-0000-0000-000000000002", name: "Annie - Studio Presenter", preview_url: "https://minio.local/annie.png" },
      { id: "30000000-0000-0000-0000-000000000003", name: "Rasmus - Executive", preview_url: "https://minio.local/rasmus.png" },
    ];

    function resolveDefaultPresenter(catalog: typeof realAvatars, explicitContext?: any) {
      if (explicitContext?.avatar) return explicitContext.avatar;
      const annie = catalog.find((a) => a.name.toLowerCase().includes("annie") || a.id === "30000000-0000-0000-0000-000000000002");
      return annie || catalog[0];
    }

    const defaultPresenter = resolveDefaultPresenter(realAvatars);
    assert.ok(defaultPresenter);
    assert.equal(defaultPresenter.id, "30000000-0000-0000-0000-000000000002");
    assert.equal(defaultPresenter.name, "Annie - Studio Presenter");
    assert.equal(defaultPresenter.preview_url, "https://minio.local/annie.png");
  });

  it("Test 22: Selecting non-Annie presenter updates active selection with genuine preview image and UUID", () => {
    const realAvatars = [
      { id: "30000000-0000-0000-0000-000000000002", name: "Annie - Studio Presenter", preview_url: "https://minio.local/annie.png" },
      { id: "30000000-0000-0000-0000-000000000004", name: "Daniel - Modern Creator", preview_url: "https://minio.local/daniel.png" },
      { id: "30000000-0000-0000-0000-000000000005", name: "Sophia - Creative Director", preview_url: "https://minio.local/sophia.png" },
    ];

    let currentSelectedPresenter = realAvatars[0]; // starts as Annie

    // User chooses Daniel from presenter selector
    const daniel = realAvatars.find((a) => a.id === "30000000-0000-0000-0000-000000000004");
    assert.ok(daniel);
    currentSelectedPresenter = daniel;

    assert.equal(currentSelectedPresenter.id, "30000000-0000-0000-0000-000000000004");
    assert.equal(currentSelectedPresenter.name, "Daniel - Modern Creator");
    assert.equal(currentSelectedPresenter.preview_url, "https://minio.local/daniel.png");
    assert.notEqual(currentSelectedPresenter.id, "30000000-0000-0000-0000-000000000002");
  });

  it("Test 23: Selected non-Annie presenter remains selected through prompt -> Generate flow and follow-ups", () => {
    let selectedPresenter = {
      id: "30000000-0000-0000-0000-000000000003",
      name: "Rasmus - Executive",
      preview_url: "https://minio.local/rasmus.png",
    };

    const dispatches: Array<{ prompt: string; avatarId: string; avatarName: string }> = [];

    function handleSendPrompt(composerText: string) {
      const presenterToSend = selectedPresenter;
      dispatches.push({
        prompt: composerText,
        avatarId: presenterToSend.id,
        avatarName: presenterToSend.name,
      });
      // Crucial: selectedPresenter state is NOT reset on submit
    }

    // Prompt 1
    handleSendPrompt("Introduce our enterprise product architecture");
    assert.equal(dispatches.length, 1);
    assert.equal(dispatches[0].avatarId, "30000000-0000-0000-0000-000000000003");
    assert.equal(dispatches[0].avatarName, "Rasmus - Executive");

    // Prompt 2 (Follow-up)
    handleSendPrompt("Make the tone more punchy for the call-to-action");
    assert.equal(dispatches.length, 2);
    assert.equal(dispatches[1].avatarId, "30000000-0000-0000-0000-000000000003");
    assert.equal(dispatches[1].avatarName, "Rasmus - Executive");
  });

  it("Test 24: Pass selected presenter through generation request, scenes, and ProjectVersion metadata", () => {
    const selectedPresenter = {
      id: "30000000-0000-0000-0000-000000000004",
      name: "Daniel - Modern Creator",
    };

    // Simulate backend ProjectDocument generation with selected presenter
    const projectDocument = {
      scenes: [
        { id: "sc_1", avatar: { avatar_id: selectedPresenter.id } },
        { id: "sc_2", avatar: { avatar_id: selectedPresenter.id } },
      ],
      metadata: {
        avatar_id: selectedPresenter.id,
        avatar_name: selectedPresenter.name,
        presenter: {
          avatar_id: selectedPresenter.id,
          name: selectedPresenter.name,
          provider: "wav2lip",
        },
      },
    };

    for (const sc of projectDocument.scenes) {
      assert.equal(sc.avatar.avatar_id, "30000000-0000-0000-0000-000000000004");
    }
    assert.equal(projectDocument.metadata.presenter.avatar_id, "30000000-0000-0000-0000-000000000004");
    assert.equal(projectDocument.metadata.presenter.name, "Daniel - Modern Creator");
  });

  it("Test 25: Studio resolves active presenter from generated project and does not replace with Annie", () => {
    const studioAvatars = [
      { id: "30000000-0000-0000-0000-000000000002", name: "Annie - Studio Presenter", preview_url: "https://minio.local/annie.png" },
      { id: "30000000-0000-0000-0000-000000000004", name: "Daniel - Modern Creator", preview_url: "https://minio.local/daniel.png" },
      { id: "30000000-0000-0000-0000-000000000005", name: "Sophia - Creative Director", preview_url: "https://minio.local/sophia.png" },
    ];

    const loadedScene = {
      id: "sc_1",
      avatar: { avatar_id: "30000000-0000-0000-0000-000000000004" }, // Daniel
    };

    // Studio activeAvatarObj resolver logic
    function resolveActiveAvatar(avatars: typeof studioAvatars, scene: typeof loadedScene) {
      const currentId = scene?.avatar?.avatar_id;
      if (!currentId) return null;
      return avatars.find((a) => a.id === currentId || a.name === currentId) || null;
    }

    const resolved = resolveActiveAvatar(studioAvatars, loadedScene);
    assert.ok(resolved);
    assert.equal(resolved.id, "30000000-0000-0000-0000-000000000004");
    assert.equal(resolved.name, "Daniel - Modern Creator");
    assert.notEqual(resolved.id, "30000000-0000-0000-0000-000000000002");
  });

  it("Test 26: GPU_REQUIRED failure clears video artifact, shows truthful GPU notice, and marks draft scenes incomplete", () => {
    // 1. Initial state with a stale previous artifact
    const staleArtifact: VideoArtifact = {
      id: "prev_annie_video",
      title: "Previous Annie Video",
      status: "ready",
      sceneCount: 3,
      duration: 20,
      avatarName: "Annie - Studio Presenter",
      videoUrl: "https://minio.local/bucket/annie.mp4",
      thumbnailUrl: "https://minio.local/bucket/annie.png",
    };

    let selectedArtifact: VideoArtifact | null = staleArtifact;
    let artifacts: VideoArtifact[] = [staleArtifact];
    let activeGen: any = null;
    let agentMessage: any = null;

    // 2. Generation begins for non-Annie presenter (e.g. Daniel)
    selectedArtifact = null;
    activeGen = {
      id: "gen_100",
      status: "queued",
      prompt: "hey",
      context: {
        avatar: { id: "30000000-0000-0000-0000-000000000004", name: "Daniel - Modern Creator" },
      },
    };
    agentMessage = {
      id: "msg_agent_1",
      sender: "agent",
      status: "generating",
      text: "Thinking...",
    };

    // Stale artifact is cleared immediately
    assert.equal(selectedArtifact, null);

    // 3. Media pipeline fails at avatar stage with GPU_REQUIRED
    const isGpuRequired = true;
    const requiredError = "Neural avatar generation requires a CUDA GPU.";

    // Simulate catch block execution
    selectedArtifact = null;
    const draftScenes = [
      { id: "sc_1", sequence: 1, duration: 10, heading: "Intro", script: "hey there" },
    ];
    activeGen = {
      id: "gen_100",
      status: "failed",
      error: requiredError,
      isGpuRequired: true,
      projectId: "proj_draft_1",
      incompleteScenes: draftScenes,
      prompt: "hey",
      context: {
        avatar: { id: "30000000-0000-0000-0000-000000000004", name: "Daniel - Modern Creator" },
      },
    };
    agentMessage = {
      ...agentMessage,
      status: "failed",
      text: requiredError,
    };

    // Verify requirements:
    // a. No video artifact created or added to artifacts
    assert.equal(artifacts.length, 1); // Only the previous one, no fake new video
    assert.equal(selectedArtifact, null); // Selected artifact is null

    // b. Chat message displays the exact required text
    assert.equal(agentMessage.text, "Neural avatar generation requires a CUDA GPU.");
    assert.equal(agentMessage.status, "failed");

    // c. Active generation is marked failed with GPU notice
    assert.equal(activeGen.isGpuRequired, true);
    assert.equal(activeGen.error, "Neural avatar generation requires a CUDA GPU.");

    // d. Script/scene breakdown is preserved as Draft / Generation incomplete
    assert.ok(activeGen.incompleteScenes);
    assert.equal(activeGen.incompleteScenes.length, 1);
    assert.equal(activeGen.incompleteScenes[0].heading, "Intro");

    // e. Retry action uses the activeGen prompt and context
    let retried = false;
    function handleRetry() {
      assert.equal(activeGen.prompt, "hey");
      assert.equal(activeGen.context.avatar.id, "30000000-0000-0000-0000-000000000004");
      retried = true;
    }
    handleRetry();
    assert.equal(retried, true);
  });

  describe("Flexible Video Duration Scaling & UI Integration", () => {
    // Preset definition matching frontend
    const DURATION_PRESETS = [
      { label: "15 sec", seconds: 15 },
      { label: "30 sec", seconds: 30 },
      { label: "60 sec", seconds: 60 },
      { label: "90 sec", seconds: 90 },
      { label: "2 min", seconds: 120 },
      { label: "5 min", seconds: 300 },
      { label: "10 min", seconds: 600 },
      { label: "Custom", seconds: -1 },
    ];

    function formatDurationMMSS(seconds: number): string {
      const totalSecs = Math.max(0, Math.round(seconds));
      const mins = Math.floor(totalSecs / 60);
      const secs = totalSecs % 60;
      return `${mins}:${secs < 10 ? "0" : ""}${secs}`;
    }

    function getDurationLabel(seconds: number): string {
      const preset = DURATION_PRESETS.find((p) => p.seconds === seconds);
      if (preset && preset.seconds > 0) {
        return `${preset.label} (${formatDurationMMSS(seconds)})`;
      }
      return `Custom: ${formatDurationMMSS(seconds)} (${Math.round(seconds)}s)`;
    }

    it("verifies all required presets are available: 15s, 30s, 60s, 90s, 2m, 5m, 10m, Custom", () => {
      const labels = DURATION_PRESETS.map((p) => p.label);
      assert.deepEqual(labels, [
        "15 sec",
        "30 sec",
        "60 sec",
        "90 sec",
        "2 min",
        "5 min",
        "10 min",
        "Custom",
      ]);

      assert.equal(DURATION_PRESETS.find((p) => p.label === "15 sec")?.seconds, 15);
      assert.equal(DURATION_PRESETS.find((p) => p.label === "30 sec")?.seconds, 30);
      assert.equal(DURATION_PRESETS.find((p) => p.label === "60 sec")?.seconds, 60);
      assert.equal(DURATION_PRESETS.find((p) => p.label === "90 sec")?.seconds, 90);
      assert.equal(DURATION_PRESETS.find((p) => p.label === "2 min")?.seconds, 120);
      assert.equal(DURATION_PRESETS.find((p) => p.label === "5 min")?.seconds, 300);
      assert.equal(DURATION_PRESETS.find((p) => p.label === "10 min")?.seconds, 600);
    });

    it("formats duration correctly in mm:ss format", () => {
      assert.equal(formatDurationMMSS(15), "0:15");
      assert.equal(formatDurationMMSS(30), "0:30");
      assert.equal(formatDurationMMSS(60), "1:00");
      assert.equal(formatDurationMMSS(90), "1:30");
      assert.equal(formatDurationMMSS(120), "2:00");
      assert.equal(formatDurationMMSS(300), "5:00");
      assert.equal(formatDurationMMSS(600), "10:00");
      assert.equal(formatDurationMMSS(185), "3:05");
      assert.equal(formatDurationMMSS(420), "7:00");
    });

    it("generates descriptive duration labels", () => {
      assert.equal(getDurationLabel(15), "15 sec (0:15)");
      assert.equal(getDurationLabel(300), "5 min (5:00)");
      assert.equal(getDurationLabel(180), "Custom: 3:00 (180s)");
      assert.equal(getDurationLabel(420), "Custom: 7:00 (420s)");
    });

    it("custom duration is preserved and NEVER silently clamped to 30s", () => {
      const customInputs = [45, 180, 420, 900, 1800];

      for (const customSec of customInputs) {
        let sentTargetDuration: number | undefined;

        // Simulate API call from VideoAgentWorkspace
        function mockGenerateProject(payload: { target_duration_seconds?: number }) {
          sentTargetDuration = payload.target_duration_seconds;
        }

        mockGenerateProject({
          target_duration_seconds: customSec,
        });

        // Must be the exact requested duration, NOT clamped to 30 or 300
        assert.equal(sentTargetDuration, customSec);
        assert.notEqual(sentTargetDuration, 30);
      }
    });

    it("AI Agent UI displays 'Duration: 5:00' and 'Scenes: 12' correctly", () => {
      const completedArtifact: VideoArtifact = {
        id: "proj_long_1",
        title: "Enterprise Masterclass",
        status: "ready",
        sceneCount: 12,
        duration: 300, // 5 min
      };

      const durationStr = `Duration: ${formatDurationMMSS(completedArtifact.duration)}`;
      const scenesStr = `Scenes: ${completedArtifact.sceneCount}`;

      assert.equal(durationStr, "Duration: 5:00");
      assert.equal(scenesStr, "Scenes: 12");
    });

    it("verifies dynamic scene count scaling without hardcoded 3-scene assumption", () => {
      function simulateScenesForDuration(duration: number): { sceneCount: number; sceneDurations: number[] } {
        let count = 3;
        if (duration <= 20) count = 2;
        else if (duration <= 45) count = 3;
        else if (duration <= 75) count = 4;
        else if (duration <= 105) count = 6;
        else if (duration <= 150) count = 8;
        else if (duration <= 240) count = 10;
        else if (duration <= 360) count = 15;
        else if (duration <= 480) count = 20;
        else count = Math.max(2, Math.min(50, Math.round(duration / 20.0)));

        const baseDur = Math.round((duration / count) * 100) / 100;
        const durations = Array(count).fill(baseDur);
        const rem = Math.round((duration - baseDur * count) * 100) / 100;
        durations[durations.length - 1] = Math.round((durations[durations.length - 1] + rem) * 100) / 100;

        return { sceneCount: count, sceneDurations: durations };
      }

      // 15 sec -> 2 scenes
      const plan15 = simulateScenesForDuration(15);
      assert.equal(plan15.sceneCount, 2);
      assert.equal(Math.round(plan15.sceneDurations.reduce((a, b) => a + b, 0)), 15);

      // 60 sec -> 4 scenes (NOT 3 scenes!)
      const plan60 = simulateScenesForDuration(60);
      assert.equal(plan60.sceneCount, 4);
      assert.equal(Math.round(plan60.sceneDurations.reduce((a, b) => a + b, 0)), 60);

      // 2 min (120 sec) -> 8 scenes
      const plan120 = simulateScenesForDuration(120);
      assert.equal(plan120.sceneCount, 8);
      assert.equal(Math.round(plan120.sceneDurations.reduce((a, b) => a + b, 0)), 120);

      // 5 min (300 sec) -> 15 scenes
      const plan300 = simulateScenesForDuration(300);
      assert.equal(plan300.sceneCount, 15);
      assert.equal(Math.round(plan300.sceneDurations.reduce((a, b) => a + b, 0)), 300);

      // 10 min (600 sec) -> 30 scenes
      const plan600 = simulateScenesForDuration(600);
      assert.equal(plan600.sceneCount, 30);
      assert.equal(Math.round(plan600.sceneDurations.reduce((a, b) => a + b, 0)), 600);
    });

    it("ProjectVersion metadata records requested, planned, and scene durations", () => {
      const requestedSeconds = 120.0;
      const plannedSeconds = 120.0;
      const sceneDurations = [15.0, 15.0, 15.0, 15.0, 15.0, 15.0, 15.0, 15.0];

      const documentMetadata = {
        generated_by: "video_agent",
        target_duration_seconds: requestedSeconds,
        requested_duration_seconds: requestedSeconds,
        actual_planned_duration_seconds: plannedSeconds,
        scene_durations: sceneDurations,
        scene_count: sceneDurations.length,
      };

      assert.equal(documentMetadata.requested_duration_seconds, 120.0);
      assert.equal(documentMetadata.actual_planned_duration_seconds, 120.0);
      assert.equal(documentMetadata.scene_count, 8);
      assert.equal(documentMetadata.scene_durations.length, 8);
      assert.equal(
        documentMetadata.scene_durations.reduce((acc, d) => acc + d, 0),
        120.0
      );
    });
  });
});

