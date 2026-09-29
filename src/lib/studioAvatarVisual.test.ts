import { describe, it } from "node:test";
import assert from "node:assert/strict";

interface AvatarLook {
  id: string;
  name: string;
  preview_url?: string | null;
  configuration?: {
    pose?: string;
    framing?: string;
    preview_url?: string;
  };
}

interface AvatarItem {
  id: string;
  name: string;
  provider: string;
  provider_reference?: string | null;
  preview_url?: string | null;
  provider_metadata?: {
    preview_url?: string;
    image_url?: string;
    category?: string;
  };
  looks?: AvatarLook[];
}

interface SceneAvatar {
  avatar_id: string;
  view_mode: "half_body" | "close_up" | "circle";
  look_id?: string | null;
  video_asset_id?: string | null;
}

interface StudioScene {
  id: string;
  avatar?: SceneAvatar | null;
}

// Canonical resolution logic mirroring VidoAIStudio.tsx
function resolveActiveAvatar(avatars: AvatarItem[], avatarId?: string | null): AvatarItem | null {
  if (!avatarId) return null;
  return (
    avatars.find(
      (a) =>
        a.id === avatarId ||
        a.name === avatarId ||
        a.provider_reference === avatarId ||
        a.name.toLowerCase().replace(/\s+/g, "-") === avatarId
    ) || null
  );
}

function resolveAvatarVisualUrl(avatar: AvatarItem | null, activeLookId?: string | null): string | null {
  if (!avatar) return null;
  if (activeLookId && Array.isArray(avatar.looks)) {
    const matchedLook = avatar.looks.find(
      (l) => l.id === activeLookId || l.name === activeLookId
    );
    if (matchedLook?.preview_url) return matchedLook.preview_url;
    if (matchedLook?.configuration?.preview_url) return matchedLook.configuration.preview_url;
  }
  return (
    avatar.preview_url ||
    avatar.provider_metadata?.preview_url ||
    avatar.provider_metadata?.image_url ||
    null
  );
}

function isAvatarSelected(av: AvatarItem, sceneAvatarId?: string | null): boolean {
  if (!sceneAvatarId) return false;
  return (
    sceneAvatarId === av.id ||
    sceneAvatarId === av.name ||
    Boolean(av.provider_reference && sceneAvatarId === av.provider_reference) ||
    Boolean(
      sceneAvatarId === "default-presenter" &&
        (av.name.toLowerCase().includes("default") || av.provider_reference === "default-presenter")
    )
  );
}

describe("Studio Avatar Visual Pipeline & Framing Tests", () => {
  const mockCatalog: AvatarItem[] = [
    {
      id: "30000000-0000-0000-0000-000000000001",
      name: "Default Presenter",
      provider: "wav2lip",
      provider_reference: "default-presenter",
      preview_url: "http://127.0.0.1:9000/heyzen-assets/workspaces/0000/assets/2001/default_presenter.jpg?signed=1",
      looks: [
        {
          id: "31000000-0000-0000-0000-000000000001",
          name: "Studio Half Body",
          preview_url: "http://127.0.0.1:9000/heyzen-assets/workspaces/0000/assets/2001/default_presenter.jpg?signed=1",
          configuration: { pose: "half_body" },
        },
        {
          id: "31000000-0000-0000-0000-000000000002",
          name: "Close Up",
          preview_url: "http://127.0.0.1:9000/heyzen-assets/workspaces/0000/assets/2001/default_presenter.jpg?signed=1",
          configuration: { pose: "close_up" },
        },
      ],
    },
    {
      id: "30000000-0000-0000-0000-000000000002",
      name: "Annie - Studio Presenter",
      provider: "wav2lip",
      provider_reference: "annie",
      preview_url: "http://127.0.0.1:9000/heyzen-assets/workspaces/0000/assets/2002/annie_studio_presenter.jpg?signed=1",
    },
    {
      id: "30000000-0000-0000-0000-000000000003",
      name: "Rasmus - Executive",
      provider: "wav2lip",
      provider_reference: "rasmus",
      preview_url: "http://127.0.0.1:9000/heyzen-assets/workspaces/0000/assets/2003/rasmus_executive.jpg?signed=1",
    },
    {
      id: "30000000-0000-0000-0000-000000000004",
      name: "Daniel - Modern Creator",
      provider: "musetalk",
      provider_reference: "daniel",
      preview_url: "http://127.0.0.1:9000/heyzen-assets/workspaces/0000/assets/2004/daniel_modern_creator.jpg?signed=1",
    },
    {
      id: "30000000-0000-0000-0000-000000000005",
      name: "Sophia - Creative Director",
      provider: "wav2lip",
      provider_reference: "sophia",
      preview_url: "http://127.0.0.1:9000/heyzen-assets/workspaces/0000/assets/2005/sophia_creative_director.jpg?signed=1",
    },
  ];

  it("1. resolves default-presenter string to Default Presenter record", () => {
    const resolved = resolveActiveAvatar(mockCatalog, "default-presenter");
    assert.ok(resolved);
    assert.equal(resolved.name, "Default Presenter");
    assert.equal(resolved.provider_reference, "default-presenter");
  });

  it("2. resolves UUID identifier to exact Avatar record for all 5 canonical avatars", () => {
    mockCatalog.forEach((av) => {
      const resolved = resolveActiveAvatar(mockCatalog, av.id);
      assert.ok(resolved);
      assert.equal(resolved.name, av.name);
      assert.equal(resolved.preview_url, av.preview_url);
    });
  });

  it("3. verifies all five canonical avatars have distinct, non-reused visual assets", () => {
    const urls = mockCatalog.map((av) => resolveAvatarVisualUrl(av));
    const uniqueUrls = new Set(urls);
    assert.equal(uniqueUrls.size, 5, "Each avatar must have a unique preview URL");
    urls.forEach((url) => {
      assert.ok(url);
      assert.ok(url.endsWith(".jpg?signed=1"), "Must point to real JPEG asset");
    });
  });

  it("4. selects look-specific preview URL when look is active", () => {
    const defaultAv = mockCatalog[0];
    const visualUrl = resolveAvatarVisualUrl(defaultAv, "31000000-0000-0000-0000-000000000002");
    assert.ok(visualUrl);
    assert.ok(visualUrl.includes("default_presenter.jpg"));
  });

  it("5. correctly highlights selected avatar card for both UUID and provider_reference", () => {
    assert.equal(isAvatarSelected(mockCatalog[0], "default-presenter"), true);
    assert.equal(isAvatarSelected(mockCatalog[0], "30000000-0000-0000-0000-000000000001"), true);
    assert.equal(isAvatarSelected(mockCatalog[1], "default-presenter"), false);
    assert.equal(isAvatarSelected(mockCatalog[1], "30000000-0000-0000-0000-000000000002"), true);
  });

  it("6. preserves scene isolation: Scene 1 avatar does not leak into Scene 2", () => {
    const scene1: StudioScene = {
      id: "scene-1",
      avatar: { avatar_id: "30000000-0000-0000-0000-000000000001", view_mode: "half_body" },
    };
    const scene2: StudioScene = {
      id: "scene-2",
      avatar: { avatar_id: "30000000-0000-0000-0000-000000000003", view_mode: "circle" },
    };

    const av1 = resolveActiveAvatar(mockCatalog, scene1.avatar?.avatar_id);
    const av2 = resolveActiveAvatar(mockCatalog, scene2.avatar?.avatar_id);

    assert.equal(av1?.name, "Default Presenter");
    assert.equal(av2?.name, "Rasmus - Executive");
    assert.notEqual(av1?.id, av2?.id);

    const visual1 = resolveAvatarVisualUrl(av1);
    const visual2 = resolveAvatarVisualUrl(av2);
    assert.notEqual(visual1, visual2);
    assert.ok(visual1?.includes("default_presenter.jpg"));
    assert.ok(visual2?.includes("rasmus_executive.jpg"));
  });

  it("7. maintains avatar selection across framing mode changes (half_body -> close_up -> circle)", () => {
    const scene: StudioScene = {
      id: "scene-dynamic-framing",
      avatar: { avatar_id: "30000000-0000-0000-0000-000000000002", view_mode: "half_body" },
    };

    const initialAv = resolveActiveAvatar(mockCatalog, scene.avatar?.avatar_id);
    const initialVisual = resolveAvatarVisualUrl(initialAv);
    assert.equal(initialAv?.name, "Annie - Studio Presenter");
    assert.ok(initialVisual?.includes("annie_studio_presenter.jpg"));

    // Switch framing to close_up
    scene.avatar!.view_mode = "close_up";
    const closeUpAv = resolveActiveAvatar(mockCatalog, scene.avatar?.avatar_id);
    assert.equal(closeUpAv?.name, "Annie - Studio Presenter");
    assert.equal(resolveAvatarVisualUrl(closeUpAv), initialVisual);

    // Switch framing to circle
    scene.avatar!.view_mode = "circle";
    const circleAv = resolveActiveAvatar(mockCatalog, scene.avatar?.avatar_id);
    assert.equal(circleAv?.name, "Annie - Studio Presenter");
    assert.equal(resolveAvatarVisualUrl(circleAv), initialVisual);
  });

  it("8. handles unknown avatar gracefully with fallback null", () => {
    const resolved = resolveActiveAvatar(mockCatalog, "unknown-avatar-uuid");
    assert.equal(resolved, null);
    const visualUrl = resolveAvatarVisualUrl(resolved);
    assert.equal(visualUrl, null);
  });

  it("9. resolves scene thumbnail avatar visual correctly for all canonical avatars", () => {
    // Daniel
    const danielScene: StudioScene = {
      id: "scene-daniel",
      avatar: { avatar_id: "30000000-0000-0000-0000-000000000004", view_mode: "half_body" },
    };
    const danielAv = resolveActiveAvatar(mockCatalog, danielScene.avatar?.avatar_id);
    const danielVisual = resolveAvatarVisualUrl(danielAv);
    assert.ok(danielVisual?.includes("daniel_modern_creator.jpg"));

    // Annie
    const annieScene: StudioScene = {
      id: "scene-annie",
      avatar: { avatar_id: "30000000-0000-0000-0000-000000000002", view_mode: "half_body" },
    };
    const annieAv = resolveActiveAvatar(mockCatalog, annieScene.avatar?.avatar_id);
    const annieVisual = resolveAvatarVisualUrl(annieAv);
    assert.ok(annieVisual?.includes("annie_studio_presenter.jpg"));

    // Rasmus
    const rasmusScene: StudioScene = {
      id: "scene-rasmus",
      avatar: { avatar_id: "30000000-0000-0000-0000-000000000003", view_mode: "half_body" },
    };
    const rasmusAv = resolveActiveAvatar(mockCatalog, rasmusScene.avatar?.avatar_id);
    const rasmusVisual = resolveAvatarVisualUrl(rasmusAv);
    assert.ok(rasmusVisual?.includes("rasmus_executive.jpg"));

    // Sophia
    const sophiaScene: StudioScene = {
      id: "scene-sophia",
      avatar: { avatar_id: "30000000-0000-0000-0000-000000000005", view_mode: "half_body" },
    };
    const sophiaAv = resolveActiveAvatar(mockCatalog, sophiaScene.avatar?.avatar_id);
    const sophiaVisual = resolveAvatarVisualUrl(sophiaAv);
    assert.ok(sophiaVisual?.includes("sophia_creative_director.jpg"));
  });

  it("10. updates scene thumbnail visual dynamically when avatar changes", () => {
    const mutableScene: StudioScene = {
      id: "scene-01",
      avatar: { avatar_id: "30000000-0000-0000-0000-000000000004", view_mode: "half_body" }, // Daniel
    };
    let av = resolveActiveAvatar(mockCatalog, mutableScene.avatar?.avatar_id);
    let visual = resolveAvatarVisualUrl(av);
    assert.ok(visual?.includes("daniel_modern_creator.jpg"));

    // Switch to Annie
    mutableScene.avatar!.avatar_id = "30000000-0000-0000-0000-000000000002";
    av = resolveActiveAvatar(mockCatalog, mutableScene.avatar?.avatar_id);
    visual = resolveAvatarVisualUrl(av);
    assert.ok(visual?.includes("annie_studio_presenter.jpg"));

    // Switch to Rasmus
    mutableScene.avatar!.avatar_id = "30000000-0000-0000-0000-000000000003";
    av = resolveActiveAvatar(mockCatalog, mutableScene.avatar?.avatar_id);
    visual = resolveAvatarVisualUrl(av);
    assert.ok(visual?.includes("rasmus_executive.jpg"));

    // Switch to Sophia
    mutableScene.avatar!.avatar_id = "30000000-0000-0000-0000-000000000005";
    av = resolveActiveAvatar(mockCatalog, mutableScene.avatar?.avatar_id);
    visual = resolveAvatarVisualUrl(av);
    assert.ok(visual?.includes("sophia_creative_director.jpg"));

    // No avatar -> null visual (triggers fallback)
    mutableScene.avatar = null;
    av = resolveActiveAvatar(mockCatalog, (mutableScene as StudioScene).avatar?.avatar_id);
    visual = resolveAvatarVisualUrl(av);
    assert.equal(visual, null);
  });
});

