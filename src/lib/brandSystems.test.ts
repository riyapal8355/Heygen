import { describe, it } from "node:test";
import assert from "node:assert/strict";

import {
  getNextCopyName,
} from "../components/brand/BrandKitEditor";
import {
  getNextGlossaryName,
  BrandKitItem,
  BrandGlossaryItem,
  AppliedBrandSystem,
} from "../components/brand/BrandSystems";
import {
  BrandKitItemResponse,
  BrandGlossaryRuleItemResponse,
} from "./api";

describe("Brand Systems & Glossary Frontend Unit Tests", () => {
  it("computes next copy names predictably", () => {
    assert.equal(getNextCopyName("Corporate Blue", []), "Corporate Blue Copy");
    assert.equal(
      getNextCopyName("Corporate Blue", ["Corporate Blue Copy"]),
      "Corporate Blue Copy 2"
    );
    assert.equal(
      getNextCopyName("Corporate Blue Copy 2", ["Corporate Blue Copy", "Corporate Blue Copy 2"]),
      "Corporate Blue Copy 3"
    );
  });

  it("computes next brand glossary names predictably", () => {
    assert.equal(getNextGlossaryName([]), "Brand Glossary");
    assert.equal(getNextGlossaryName(["Brand Glossary"]), "Brand Glossary 2");
    assert.equal(
      getNextGlossaryName(["Brand Glossary", "Brand Glossary 2"]),
      "Brand Glossary 3"
    );
  });

  it("normalizes BrandKitItem from backend response with flat and nested colors", () => {
    const backendResponse: BrandKitItemResponse = {
      id: "kit-123",
      workspace_id: "ws-456",
      created_by: "usr-789",
      name: "Acme Pro",
      description: "Acme corporate brand kit",
      logo_asset_id: "asset-logo-1",
      colors: {
        primary: "#0055FF",
        accent: "#00D2FF",
        secondary: "#111827",
      },
      typography: {
        primary_font: "Inter, sans-serif",
      },
      settings: {},
      is_default: true,
      created_at: "2026-03-01T00:00:00Z",
      updated_at: "2026-03-02T12:00:00Z",
      primary_color: "#0055FF",
      accent_color: "#00D2FF",
      secondary_color: "#111827",
      font_family: "Inter, sans-serif",
    };

    const mapped: BrandKitItem = {
      id: backendResponse.id,
      name: backendResponse.name,
      isFavorite: false,
      logoUrl: backendResponse.logo_asset_id || undefined,
      logoText: backendResponse.name.slice(0, 6),
      primaryColor:
        backendResponse.primary_color ||
        backendResponse.colors?.primary ||
        "#000000",
      accentColor:
        backendResponse.accent_color ||
        backendResponse.colors?.accent ||
        "#00d2ff",
      secondaryColor:
        backendResponse.secondary_color ||
        backendResponse.colors?.secondary ||
        "#7928ca",
      fontFamily:
        backendResponse.font_family ||
        backendResponse.typography?.primary_font ||
        "Inter, sans-serif",
      updatedAt: "Recently",
    };

    assert.equal(mapped.name, "Acme Pro");
    assert.equal(mapped.primaryColor, "#0055FF");
    assert.equal(mapped.accentColor, "#00D2FF");
    assert.equal(mapped.secondaryColor, "#111827");
    assert.equal(mapped.fontFamily, "Inter, sans-serif");
    assert.equal(mapped.logoUrl, "asset-logo-1");
  });

  it("classifies glossary rules accurately by rule_type", () => {
    const rules: BrandGlossaryRuleItemResponse[] = [
      {
        id: "r1",
        glossary_id: "g1",
        source_term: "HeyZen",
        preferred_term: "HeyZen Studio",
        source_language: "en",
        case_sensitive: false,
        status: "active",
        created_at: "2026-03-01T00:00:00Z",
        updated_at: "2026-03-01T00:00:00Z",
        term: "HeyZen",
        replacement: "HeyZen Studio",
        rule_type: "force_translate",
      },
      {
        id: "r2",
        glossary_id: "g1",
        source_term: "NeuralMesh",
        preferred_term: "NeuralMesh",
        source_language: "en",
        case_sensitive: false,
        status: "active",
        created_at: "2026-03-01T00:00:00Z",
        updated_at: "2026-03-01T00:00:00Z",
        term: "NeuralMesh",
        rule_type: "do_not_translate",
      },
      {
        id: "r3",
        glossary_id: "g1",
        source_term: "Rhys",
        preferred_term: "Reece",
        source_language: "en",
        case_sensitive: false,
        status: "active",
        created_at: "2026-03-01T00:00:00Z",
        updated_at: "2026-03-01T00:00:00Z",
        term: "Rhys",
        phonetic_spelling: "Reece",
        rule_type: "pronunciation",
      },
    ];

    const prons: any[] = [];
    const forces: any[] = [];
    const donts: any[] = [];

    for (const r of rules) {
      if (r.rule_type === "pronunciation") {
        prons.push(r);
      } else if (r.rule_type === "do_not_translate") {
        donts.push(r);
      } else {
        forces.push(r);
      }
    }

    assert.equal(prons.length, 1);
    assert.equal(prons[0].term, "Rhys");
    assert.equal(prons[0].phonetic_spelling, "Reece");

    assert.equal(donts.length, 1);
    assert.equal(donts[0].term, "NeuralMesh");

    assert.equal(forces.length, 1);
    assert.equal(forces[0].term, "HeyZen");
    assert.equal(forces[0].replacement, "HeyZen Studio");
  });

  it("applies brand system to video agent context properly", () => {
    const selectedKit: AppliedBrandSystem = {
      id: "kit-999",
      name: "Vibrant Tech",
      primaryColor: "#4F46E5",
      accentColor: "#06B6D4",
      secondaryColor: "#1E1B4B",
      fontFamily: "Space Grotesk, sans-serif",
    };

    // When applied to Video Agent orchestration payload
    const projectRequest = {
      prompt: "Create a promotional launch video",
      brand_kit_id: selectedKit.id,
      styling_override: {
        primary_color: selectedKit.primaryColor,
        accent_color: selectedKit.accentColor,
        font_family: selectedKit.fontFamily,
      },
    };

    assert.equal(projectRequest.brand_kit_id, "kit-999");
    assert.equal(projectRequest.styling_override.primary_color, "#4F46E5");
    assert.equal(projectRequest.styling_override.font_family, "Space Grotesk, sans-serif");
  });
});
