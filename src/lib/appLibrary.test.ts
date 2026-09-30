import { describe, it } from "node:test";
import assert from "node:assert";
import {
  APP_REGISTRY,
  filterApps,
  AppDefinition,
  AppCategory,
} from "./appRegistry";
import { formatTimeAgo } from "../components/dashboard/AppsSidebar";

describe("Apps Home: Canonical App Registry & Filtering Tests", () => {
  it("1. App registry contains valid entries with required fields", () => {
    assert.ok(APP_REGISTRY.length >= 10, "Registry should have at least 10 canonical apps");
    const validCategories: AppCategory[] = ["create", "enhance", "edit", "interactive"];

    const ids = new Set<string>();
    for (const app of APP_REGISTRY) {
      assert.ok(app.id, "App must have an id");
      assert.ok(!ids.has(app.id), `App id ${app.id} must be unique`);
      ids.add(app.id);

      assert.ok(app.name && app.name.trim().length > 0, "App must have a non-empty name");
      assert.ok(app.description && app.description.trim().length > 0, "App must have a description");
      assert.ok(
        validCategories.includes(app.category),
        `App ${app.id} has invalid category ${app.category}`
      );
      assert.ok(Array.isArray(app.keywords) && app.keywords.length > 0, "App must have keywords");
      assert.ok(app.gradient && app.gradient.includes("from-"), "App must have gradient tokens");
      assert.ok(app.actionType, "App must have an actionType");
    }
  });

  it("2. Verifies all 4 categories have representative apps", () => {
    const createApps = APP_REGISTRY.filter((a) => a.category === "create");
    const enhanceApps = APP_REGISTRY.filter((a) => a.category === "enhance");
    const editApps = APP_REGISTRY.filter((a) => a.category === "edit");
    const interactiveApps = APP_REGISTRY.filter((a) => a.category === "interactive");

    assert.ok(createApps.length >= 5, "Create category should have at least 5 apps");
    assert.ok(enhanceApps.length >= 2, "Enhance category should have at least 2 apps");
    assert.ok(editApps.length >= 2, "Edit category should have at least 2 apps");
    assert.ok(interactiveApps.length >= 1, "Interactive category should have at least 1 app");
  });

  it("3. Category filtering isolates apps correctly", () => {
    const all = filterApps(APP_REGISTRY, "all", "");
    assert.strictEqual(all.length, APP_REGISTRY.length, "All apps tab returns full registry");

    const createOnly = filterApps(APP_REGISTRY, "create", "");
    assert.ok(createOnly.length > 0);
    assert.ok(createOnly.every((a) => a.category === "create"));

    const enhanceOnly = filterApps(APP_REGISTRY, "enhance", "");
    assert.ok(enhanceOnly.length > 0);
    assert.ok(enhanceOnly.every((a) => a.category === "enhance"));

    const editOnly = filterApps(APP_REGISTRY, "edit", "");
    assert.ok(editOnly.length > 0);
    assert.ok(editOnly.every((a) => a.category === "edit"));

    const interactiveOnly = filterApps(APP_REGISTRY, "interactive", "");
    assert.ok(interactiveOnly.length > 0);
    assert.ok(interactiveOnly.every((a) => a.category === "interactive"));
  });

  it("4. Search query filters by name, description, category, and keywords (case-insensitive)", () => {
    // Search by name
    const searchPodcast = filterApps(APP_REGISTRY, "all", "podcast");
    assert.ok(searchPodcast.some((a) => a.id === "app_podcast"));

    // Search by keyword
    const searchTranslate = filterApps(APP_REGISTRY, "all", "dubbing");
    assert.ok(searchTranslate.some((a) => a.id === "app_translate"));

    // Case-insensitivity and whitespace trimming
    const searchAgent = filterApps(APP_REGISTRY, "all", "  VIDEO AGENT  ");
    assert.ok(searchAgent.some((a) => a.id === "app_video_agent"));

    // Category search
    const searchInteractive = filterApps(APP_REGISTRY, "all", "interactive");
    assert.ok(searchInteractive.some((a) => a.id === "app_interactive"));
  });

  it("5. Empty search returns no results and clear search restores results", () => {
    const nonexistent = filterApps(APP_REGISTRY, "all", "nonexistent_term_xyz_12345");
    assert.strictEqual(nonexistent.length, 0, "Should return empty array when no matches");

    // Clearing search restores
    const restored = filterApps(APP_REGISTRY, "all", "");
    assert.strictEqual(restored.length, APP_REGISTRY.length);
  });

  it("6. Search respects selected category tab filter", () => {
    // When searching for an edit app while inside 'create' tab, it should not appear
    const searchInCreate = filterApps(APP_REGISTRY, "create", "translate");
    assert.strictEqual(searchInCreate.length, 0, "Translate is an edit app and should not appear in create tab");

    // When searching for the same app inside 'edit' tab, it appears
    const searchInEdit = filterApps(APP_REGISTRY, "edit", "translate");
    assert.ok(searchInEdit.some((a) => a.id === "app_translate"));
  });

  it("7. Relative time formatting handles all cases safely", () => {
    const now = new Date();
    assert.strictEqual(formatTimeAgo(now), "Just now");

    const twoMinutesAgo = new Date(Date.now() - 2 * 60 * 1000);
    assert.strictEqual(formatTimeAgo(twoMinutesAgo), "2m ago");

    const threeHoursAgo = new Date(Date.now() - 3 * 60 * 60 * 1000);
    assert.strictEqual(formatTimeAgo(threeHoursAgo), "3h ago");

    const fourDaysAgo = new Date(Date.now() - 4 * 24 * 60 * 60 * 1000);
    assert.strictEqual(formatTimeAgo(fourDaysAgo), "4d ago");

    // Invalid date safety
    const invalidDate = new Date("invalid date string");
    assert.strictEqual(formatTimeAgo(invalidDate), "Recently");
  });

  it("8. No external stock images or Unsplash URLs in app registry", () => {
    for (const app of APP_REGISTRY) {
      assert.ok(
        !JSON.stringify(app).includes("unsplash.com"),
        `App ${app.id} contains Unsplash URL which violates stock image prohibition`
      );
    }
  });

  it("9. Action types map cleanly to dedicated HeyZen workflows (no generic modal_info)", () => {
    const allowedActions = [
      "navigate_video_agent",
      "navigate_studio",
      "navigate_single_scene",
      "navigate_scene_by_scene",
      "navigate_translate",
      "navigate_brand",
      "navigate_design_look",
      "modal_generator",
      "modal_podcast",
      "modal_speech",
      "modal_pdf",
      "modal_shots",
      "modal_upscale",
      "modal_clipping",
      "modal_faceswap",
      "modal_interactive",
    ];

    for (const app of APP_REGISTRY) {
      assert.ok(
        allowedActions.includes(app.actionType),
        `App ${app.id} actionType ${app.actionType} is not among allowed actions`
      );
      assert.notStrictEqual(
        app.actionType,
        "modal_info",
        `App ${app.id} must NOT use generic modal_info; must have dedicated workflow`
      );
    }
  });

  it("10. Full Routing Matrix: every app has an exact dedicated destination", () => {
    const expectedRouting: Record<string, string> = {
      app_video_agent: "navigate_video_agent",
      app_studio: "navigate_studio",
      app_single_scene: "navigate_single_scene",
      app_scene_by_scene: "navigate_scene_by_scene",
      app_translate: "navigate_translate",
      app_podcast: "modal_podcast",
      app_speech: "modal_speech",
      app_design_look: "navigate_design_look",
      app_brand_kit: "navigate_brand",
      app_generator: "modal_generator",
      app_pdf: "modal_pdf",
      app_shots: "modal_shots",
      app_upscale: "modal_upscale",
      app_clipping: "modal_clipping",
      app_faceswap: "modal_faceswap",
      app_interactive: "modal_interactive",
    };

    assert.strictEqual(
      APP_REGISTRY.length,
      Object.keys(expectedRouting).length,
      "Every registered app must be accounted for in routing matrix"
    );

    for (const app of APP_REGISTRY) {
      assert.strictEqual(
        app.actionType,
        expectedRouting[app.id],
        `App ${app.id} expected ${expectedRouting[app.id]} but got ${app.actionType}`
      );
    }
  });
});
