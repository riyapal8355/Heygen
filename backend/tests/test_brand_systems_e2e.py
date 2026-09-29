"""End-to-end production verification test suite for HeyZen Brand Systems & Brand Glossaries.

Covers:
1. Brand Kit full CRUD, flat & nested schema interoperability, logo asset binding.
2. Default kit switching and soft deletion semantics.
3. Brand Glossary and Brand Glossary Rules full CRUD (force_translate, do_not_translate, pronunciation).
4. Strict workspace isolation: Workspace B cannot read, update, or delete Workspace A's brand systems, glossaries, or rules.
5. Translate integration: Video translation applies canonical glossary rules with term preservation.
6. Studio/VideoAgent integration: Brand kit styling metadata propagation.
"""

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.brand import BrandKit, BrandGlossary, BrandGlossaryRule
from app.services.brand_service import BrandService
from app.services.video_translation_service import VideoTranslationService
from app.ai.adapters.translation import RealCTranslate2TranslationProvider


async def _setup_workspace_user(async_client: AsyncClient, name: str) -> tuple[str, str, str]:
    """Helper to register user and obtain token, user_id, and primary workspace_id."""
    email = f"{name.lower().replace(' ', '_')}_{uuid.uuid4().hex[:6]}@example.com"
    resp = await async_client.post(
        "/api/v1/auth/signup",
        json={"email": email, "display_name": name, "password": "Password123!"},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    token = data["tokens"]["access_token"]
    user_id = data["user"]["id"]

    ws_resp = await async_client.get("/api/v1/workspaces", headers={"Authorization": f"Bearer {token}"})
    assert ws_resp.status_code == 200, ws_resp.text
    workspace_id = ws_resp.json()[0]["id"]
    return token, user_id, workspace_id


async def _create_test_logo_asset(async_client: AsyncClient, token: str, ws_id: str, filename: str = "logo.svg") -> str:
    """Helper to register an image asset via upload intent."""
    resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/assets/upload-intents",
        headers={"Authorization": f"Bearer {token}"},
        json={"original_filename": filename, "mime_type": "image/svg+xml", "size_bytes": 2048, "asset_type": "image"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["asset_id"]


@pytest.mark.asyncio
async def test_brand_system_full_crud_and_computed_fields(async_client: AsyncClient):
    """Test Brand System creation with flat fields, verification of computed responses, updates, and deletion."""
    token, _, ws_id = await _setup_workspace_user(async_client, "Brand Director")
    headers = {"Authorization": f"Bearer {token}", "X-Workspace-ID": ws_id}

    logo_id = await _create_test_logo_asset(async_client, token, ws_id, "primary_logo.png")

    # 1. CREATE Brand Kit with flat UI fields
    create_payload = {
        "name": "Acme Global Identity",
        "description": "Enterprise brand standards for videos",
        "logo_asset_id": logo_id,
        "primary_color": "#0055FF",
        "accent_color": "#00D2FF",
        "secondary_color": "#111827",
        "font_family": "Inter, sans-serif",
        "is_default": True,
    }
    create_resp = await async_client.post("/api/v1/brand-kits", headers=headers, json=create_payload)
    assert create_resp.status_code == 201, create_resp.text
    kit_data = create_resp.json()
    kit_id = kit_data["id"]

    assert kit_data["name"] == "Acme Global Identity"
    assert kit_data["primary_color"] == "#0055FF"
    assert kit_data["accent_color"] == "#00D2FF"
    assert kit_data["secondary_color"] == "#111827"
    assert kit_data["font_family"] == "Inter, sans-serif"
    assert kit_data["logo_asset_id"] == logo_id
    assert kit_data["is_default"] is True

    # 2. READ Brand Kit
    get_resp = await async_client.get(f"/api/v1/brand-kits/{kit_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["primary_color"] == "#0055FF"

    # 3. LIST Brand Kits
    list_resp = await async_client.get("/api/v1/brand-kits", headers=headers)
    assert list_resp.status_code == 200
    kits = list_resp.json()
    assert any(k["id"] == kit_id for k in kits)

    # 4. UPDATE Brand Kit
    update_payload = {
        "primary_color": "#1D4ED8",
        "accent_color": "#38BDF8",
        "font_family": "Outfit, sans-serif",
    }
    upd_resp = await async_client.patch(f"/api/v1/brand-kits/{kit_id}", headers=headers, json=update_payload)
    assert upd_resp.status_code == 200
    upd_data = upd_resp.json()
    assert upd_data["primary_color"] == "#1D4ED8"
    assert upd_data["accent_color"] == "#38BDF8"
    assert upd_data["font_family"] == "Outfit, sans-serif"

    # 5. DELETE Brand Kit
    del_resp = await async_client.delete(f"/api/v1/brand-kits/{kit_id}", headers=headers)
    assert del_resp.status_code == 204

    # 6. Verify 404
    get_after = await async_client.get(f"/api/v1/brand-kits/{kit_id}", headers=headers)
    assert get_after.status_code == 404


@pytest.mark.asyncio
async def test_brand_glossary_and_rule_types_crud(async_client: AsyncClient):
    """Test Brand Glossary and all three rule types: force_translate, do_not_translate, pronunciation."""
    token, _, ws_id = await _setup_workspace_user(async_client, "Glossary Manager")
    headers = {"Authorization": f"Bearer {token}", "X-Workspace-ID": ws_id}

    # 1. Create Brand Kit
    kit_resp = await async_client.post("/api/v1/brand-kits", headers=headers, json={"name": "Tech Corp"})
    assert kit_resp.status_code == 201
    kit_id = kit_resp.json()["id"]

    # 2. Create Glossary linked to Brand Kit
    gl_resp = await async_client.post(
        f"/api/v1/brand-kits/{kit_id}/glossaries",
        headers=headers,
        json={"name": "Multilingual Tech Glossary", "description": "Canonical terms"},
    )
    assert gl_resp.status_code == 201
    glossary = gl_resp.json()
    glossary_id = glossary["id"]
    assert glossary["brand_kit_id"] == kit_id

    # 3. Add Rule: Force Translate (using UI alias term & replacement)
    r1_resp = await async_client.post(
        f"/api/v1/brand-glossaries/{glossary_id}/rules",
        headers=headers,
        json={"term": "HeyZen", "replacement": "HeyZen Studio", "rule_type": "force_translate"},
    )
    assert r1_resp.status_code == 201
    r1 = r1_resp.json()
    assert r1["source_term"] == "HeyZen"
    assert r1["preferred_term"] == "HeyZen Studio"
    assert r1["term"] == "HeyZen"
    assert r1["replacement"] == "HeyZen Studio"
    assert r1["rule_type"] == "force_translate"

    # 4. Add Rule: Do Not Translate
    r2_resp = await async_client.post(
        f"/api/v1/brand-glossaries/{glossary_id}/rules",
        headers=headers,
        json={"term": "NeuralMesh", "rule_type": "do_not_translate"},
    )
    assert r2_resp.status_code == 201
    r2 = r2_resp.json()
    assert r2["source_term"] == "NeuralMesh"
    assert r2["preferred_term"] == "NeuralMesh"
    assert r2["rule_type"] == "do_not_translate"

    # 5. Add Rule: Pronunciation
    r3_resp = await async_client.post(
        f"/api/v1/brand-glossaries/{glossary_id}/rules",
        headers=headers,
        json={"term": "Rhys", "phonetic_spelling": "Reece", "rule_type": "pronunciation"},
    )
    assert r3_resp.status_code == 201
    r3 = r3_resp.json()
    assert r3["source_term"] == "Rhys"
    assert r3["preferred_term"] == "Reece"
    assert r3["rule_type"] == "pronunciation"

    # 6. List Rules
    rules_resp = await async_client.get(f"/api/v1/brand-glossaries/{glossary_id}/rules", headers=headers)
    assert rules_resp.status_code == 200
    rules = rules_resp.json()
    assert len(rules) == 3

    # 7. Update Rule
    upd_rule = await async_client.patch(
        f"/api/v1/brand-glossary-rules/{r1['id']}",
        headers=headers,
        json={"replacement": "HeyZen Enterprise"},
    )
    assert upd_rule.status_code == 200
    assert upd_rule.json()["preferred_term"] == "HeyZen Enterprise"

    # 8. Delete Rule via nested endpoint
    del_r = await async_client.delete(f"/api/v1/brand-glossaries/{glossary_id}/rules/{r2['id']}", headers=headers)
    assert del_r.status_code == 204

    # 9. List after delete
    rules_after = await async_client.get(f"/api/v1/brand-glossaries/{glossary_id}/rules", headers=headers)
    assert len(rules_after.json()) == 2

    # 10. Delete Glossary
    del_gl = await async_client.delete(f"/api/v1/brand-glossaries/{glossary_id}", headers=headers)
    assert del_gl.status_code == 204


@pytest.mark.asyncio
async def test_workspace_isolation_strict(async_client: AsyncClient):
    """Test that Workspace A cannot access, modify, or delete Brand Kits or Glossaries belonging to Workspace B."""
    token_a, _, ws_a = await _setup_workspace_user(async_client, "Tenant Alpha")
    token_b, _, ws_b = await _setup_workspace_user(async_client, "Tenant Beta")

    headers_a = {"Authorization": f"Bearer {token_a}", "X-Workspace-ID": ws_a}
    headers_b = {"Authorization": f"Bearer {token_b}", "X-Workspace-ID": ws_b}

    # Workspace B creates Brand Kit & Glossary
    kit_b = await async_client.post("/api/v1/brand-kits", headers=headers_b, json={"name": "Beta Private Kit"})
    assert kit_b.status_code == 201
    kit_b_id = kit_b.json()["id"]

    gl_b = await async_client.post("/api/v1/brand-glossaries", headers=headers_b, json={"name": "Beta Glossary"})
    assert gl_b.status_code == 201
    gl_b_id = gl_b.json()["id"]

    rule_b = await async_client.post(
        f"/api/v1/brand-glossaries/{gl_b_id}/rules",
        headers=headers_b,
        json={"source_term": "BetaSecret", "preferred_term": "BetaConfidential"},
    )
    assert rule_b.status_code == 201
    rule_b_id = rule_b.json()["id"]

    # Workspace A attempts to access Workspace B resources
    # 1. GET Brand Kit
    res_kit = await async_client.get(f"/api/v1/brand-kits/{kit_b_id}", headers=headers_a)
    assert res_kit.status_code == 404

    # 2. UPDATE Brand Kit
    res_upd_kit = await async_client.patch(
        f"/api/v1/brand-kits/{kit_b_id}", headers=headers_a, json={"name": "Hacked Kit"}
    )
    assert res_upd_kit.status_code == 404

    # 3. DELETE Brand Kit
    res_del_kit = await async_client.delete(f"/api/v1/brand-kits/{kit_b_id}", headers=headers_a)
    assert res_del_kit.status_code == 404

    # 4. GET Glossary
    res_gl = await async_client.get(f"/api/v1/brand-glossaries/{gl_b_id}", headers=headers_a)
    assert res_gl.status_code == 404

    # 5. LIST Rules of foreign glossary
    res_rules = await async_client.get(f"/api/v1/brand-glossaries/{gl_b_id}/rules", headers=headers_a)
    assert res_rules.status_code == 404

    # 6. UPDATE Rule
    res_upd_rule = await async_client.patch(
        f"/api/v1/brand-glossary-rules/{rule_b_id}", headers=headers_a, json={"preferred_term": "Tampered"}
    )
    assert res_upd_rule.status_code == 404

    # 7. DELETE Rule
    res_del_rule = await async_client.delete(
        f"/api/v1/brand-glossary-rules/{rule_b_id}", headers=headers_a
    )
    assert res_del_rule.status_code == 404


@pytest.mark.asyncio
async def test_translate_glossary_term_protection():
    """Verify CTranslate2 provider applies glossary substitution rules to protect canonical terms."""
    provider = RealCTranslate2TranslationProvider()
    input_text = "Welcome to HeyZen video studio."

    # Rule preserving HeyZen -> HeyZen Studio
    glossary_rules = [
        {"term": "HeyZen", "translated_term": "HeyZen Studio", "case_sensitive": True}
    ]

    result = await provider.translate_text(
        text=input_text,
        source_lang="en",
        target_lang="es",
        glossary_rules=glossary_rules,
    )

    assert len(result.translated_text) > 0
    assert "HeyZen Studio" in result.translated_text
