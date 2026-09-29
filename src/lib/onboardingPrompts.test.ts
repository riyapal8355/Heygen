import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { getTemplateByIdOrTitle, VideoAgentTemplate } from "../components/create/videoAgentData";

// Core onboarding dependency & progress functions
export function computeOnboardingState(steps: {
  step_1_digital_twin: boolean;
  step_2_voice: boolean;
  step_3_look: boolean;
  step_4_video: boolean;
}) {
  const isStep1Done = Boolean(steps.step_1_digital_twin);
  const isStep2Done = Boolean(steps.step_2_voice);
  const isStep3Done = Boolean(steps.step_3_look);
  const isStep4Done = Boolean(steps.step_4_video);

  const isStep1Unlocked = true; // Always available
  const isStep2Unlocked = isStep1Done; // Requires Step 1
  const isStep3Unlocked = isStep1Done; // Requires Step 1
  const isStep4Unlocked = isStep2Done || isStep3Done; // Requires Step 2 OR Step 3

  const completedCount = [isStep1Done, isStep2Done, isStep3Done, isStep4Done].filter(Boolean).length;
  const progressText = `Finish your account setup - ${completedCount}/4`;

  return {
    isStep1Done,
    isStep2Done,
    isStep3Done,
    isStep4Done,
    isStep1Unlocked,
    isStep2Unlocked,
    isStep3Unlocked,
    isStep4Unlocked,
    completedCount,
    progressText,
  };
}

// Navigation resolution mapping
export function resolveOnboardingNavigation(stepNumber: number, state: ReturnType<typeof computeOnboardingState>): {
  allowed: boolean;
  targetView?: string;
  reason?: string;
} {
  if (stepNumber === 1) {
    return { allowed: true, targetView: "recording_modal" };
  }
  if (stepNumber === 2) {
    if (!state.isStep2Unlocked) {
      return { allowed: false, reason: "Unlocks after step 1" };
    }
    return { allowed: true, targetView: "voices" };
  }
  if (stepNumber === 3) {
    if (!state.isStep3Unlocked) {
      return { allowed: false, reason: "Unlocks after step 1" };
    }
    return { allowed: true, targetView: "design_look" };
  }
  if (stepNumber === 4) {
    if (!state.isStep4Unlocked) {
      return { allowed: false, reason: "Unlocks after step 2 or 3" };
    }
    return { allowed: true, targetView: "video_agent" };
  }
  return { allowed: false, reason: "Invalid step" };
}

// Prompt context resolution function mirroring dashboard page.tsx
export function formatPromptContext(card: { title: string; description?: string }, template?: VideoAgentTemplate | null): string {
  if (card.description && card.description.trim().length > 0) {
    return `${card.title} - ${card.description}`;
  }
  if (template?.description && template.description.trim().length > 0) {
    return template.description;
  }
  if (template?.defaultScript && template.defaultScript.trim().length > 0) {
    return template.defaultScript;
  }
  if (template?.title && template.title.trim().length > 0) {
    return template.title;
  }
  return card.title || "Video Creation";
}

describe("HeyZen Onboarding Steps Logic", () => {
  it("Step 1 is available initially and 0/4 progress is shown", () => {
    const state = computeOnboardingState({
      step_1_digital_twin: false,
      step_2_voice: false,
      step_3_look: false,
      step_4_video: false,
    });

    assert.equal(state.isStep1Unlocked, true);
    assert.equal(state.isStep2Unlocked, false);
    assert.equal(state.isStep3Unlocked, false);
    assert.equal(state.isStep4Unlocked, false);
    assert.equal(state.completedCount, 0);
    assert.equal(state.progressText, "Finish your account setup - 0/4");

    const nav = resolveOnboardingNavigation(1, state);
    assert.equal(nav.allowed, true);
    assert.equal(nav.targetView, "recording_modal");
  });

  it("Step 1 completion unlocks Step 2 and Step 3, yielding 1/4 progress", () => {
    const state = computeOnboardingState({
      step_1_digital_twin: true,
      step_2_voice: false,
      step_3_look: false,
      step_4_video: false,
    });

    assert.equal(state.isStep1Done, true);
    assert.equal(state.isStep2Unlocked, true);
    assert.equal(state.isStep3Unlocked, true);
    assert.equal(state.isStep4Unlocked, false);
    assert.equal(state.completedCount, 1);
    assert.equal(state.progressText, "Finish your account setup - 1/4");

    // Step 2 can now navigate to voices
    const nav2 = resolveOnboardingNavigation(2, state);
    assert.equal(nav2.allowed, true);
    assert.equal(nav2.targetView, "voices");

    // Step 3 can now navigate to design_look
    const nav3 = resolveOnboardingNavigation(3, state);
    assert.equal(nav3.allowed, true);
    assert.equal(nav3.targetView, "design_look");

    // Step 4 remains locked
    const nav4 = resolveOnboardingNavigation(4, state);
    assert.equal(nav4.allowed, false);
    assert.equal(nav4.reason, "Unlocks after step 2 or 3");
  });

  it("Step 4 unlocks when Step 2 is completed (even if Step 3 is incomplete)", () => {
    const state = computeOnboardingState({
      step_1_digital_twin: true,
      step_2_voice: true,
      step_3_look: false,
      step_4_video: false,
    });

    assert.equal(state.isStep2Done, true);
    assert.equal(state.isStep4Unlocked, true);
    assert.equal(state.completedCount, 2);
    assert.equal(state.progressText, "Finish your account setup - 2/4");

    const nav4 = resolveOnboardingNavigation(4, state);
    assert.equal(nav4.allowed, true);
    assert.equal(nav4.targetView, "video_agent");
  });

  it("Step 4 unlocks when Step 3 is completed (even if Step 2 is incomplete)", () => {
    const state = computeOnboardingState({
      step_1_digital_twin: true,
      step_2_voice: false,
      step_3_look: true,
      step_4_video: false,
    });

    assert.equal(state.isStep3Done, true);
    assert.equal(state.isStep4Unlocked, true);
    assert.equal(state.completedCount, 2);
    assert.equal(state.progressText, "Finish your account setup - 2/4");

    const nav4 = resolveOnboardingNavigation(4, state);
    assert.equal(nav4.allowed, true);
    assert.equal(nav4.targetView, "video_agent");
  });

  it("Full completion yields 4/4 progress", () => {
    const state = computeOnboardingState({
      step_1_digital_twin: true,
      step_2_voice: true,
      step_3_look: true,
      step_4_video: true,
    });

    assert.equal(state.completedCount, 4);
    assert.equal(state.progressText, "Finish your account setup - 4/4");
    assert.equal(state.isStep1Done, true);
    assert.equal(state.isStep2Done, true);
    assert.equal(state.isStep3Done, true);
    assert.equal(state.isStep4Done, true);
  });
});

describe("HeyZen Video Prompts to Video Agent Flow", () => {
  const samplePrompts = [
    {
      id: "ads_promo",
      title: "Ads & Promo",
      category: "Marketing",
      description: "High-converting UGC video ad showcasing your software features",
    },
    {
      id: "product_launch",
      title: "Product Launch",
      category: "Software",
      description: "Exciting feature announcement and release notes video",
    },
    {
      id: "tips_how_to",
      title: "Tips & How-To",
      category: "Tutorial",
      description: "Actionable step-by-step workflow guide and tool walkthrough",
    },
    {
      id: "educational_video",
      title: "Educational Video",
      category: "Learning",
      description: "In-depth technical breakdown and architecture walkthrough",
    },
  ];

  it("Every sample prompt generates a non-empty, rich prompt context for Video Agent", () => {
    for (const card of samplePrompts) {
      const template = getTemplateByIdOrTitle(card.title);
      const prompt = formatPromptContext(card, template);

      assert.ok(prompt.length > 10, `Prompt for ${card.title} should be substantial`);
      assert.ok(prompt.includes(card.title), `Prompt should include card title ${card.title}`);
      assert.ok(prompt.includes(card.description), `Prompt should include card description`);
    }
  });

  it("Ads & Promo specifically passes the required UGC ad prompt context", () => {
    const card = samplePrompts[0];
    const template = getTemplateByIdOrTitle(card.title);
    const prompt = formatPromptContext(card, template);

    assert.equal(
      prompt,
      "Ads & Promo - High-converting UGC video ad showcasing your software features"
    );
  });

  it("Product Launch specifically passes the required feature announcement prompt context", () => {
    const card = samplePrompts[1];
    const template = getTemplateByIdOrTitle(card.title);
    const prompt = formatPromptContext(card, template);

    assert.equal(
      prompt,
      "Product Launch - Exciting feature announcement and release notes video"
    );
  });

  it("Fallback works smoothly if card has title only", () => {
    const card = { title: "Custom Video Prompt" };
    const prompt = formatPromptContext(card, null);
    assert.equal(prompt, "Custom Video Prompt");
  });
});
