"""Test suite for BrandGlossary and BrandGlossaryRule terminology workflows."""

import uuid
import pytest
from httpx import AsyncClient


async def _setup_user_workspace(async_client: AsyncClient, name: str) -> tuple[str, str]:
    email = f"{name.lower().replace(' ', '_')}_{uuid.uuid4().hex[:6]}@example.com"
    resp = await async_client.post(
        "/api/v1/auth/signup",
        json={"email": email, "display_name": name, "password": "Password123!"},
    )
    assert resp.status_code == 201
    data = resp.json()
    token = data["tokens"]["access_token"]

    ws_resp = await async_client.get("/api/v1/workspaces", headers={"Authorization": f"Bearer {token}"})
    assert ws_resp.status_code == 200
    workspace_id = ws_resp.json()[0]["id"]
    return token, workspace_id


@pytest.mark.asyncio
async def test_glossary_and_rule_lifecycle(async_client: AsyncClient):
    """Verify glossary creation under brand kit, terminology rules management, and cascading isolation."""
    token, ws_id = await _setup_user_workspace(async_client, "Glossary Specialist")
    headers = {"Authorization": f"Bearer {token}", "X-Workspace-ID": ws_id}

    # 1. Create brand kit
    kit_resp = await async_client.post("/api/v1/brand-kits", headers=headers, json={"name": "Medical AI"})
    assert kit_resp.status_code == 201
    kit_id = kit_resp.json()["id"]

    # 2. Create glossary bound to brand kit
    gl_resp = await async_client.post(
        f"/api/v1/brand-kits/{kit_id}/glossaries",
        headers=headers,
        json={"name": "Pharma Terminology Rules"},
    )
    assert gl_resp.status_code == 201
    gl_data = gl_resp.json()
    assert gl_data["name"] == "Pharma Terminology Rules"
    assert gl_data["brand_kit_id"] == kit_id
    gl_id = gl_data["id"]

    # 3. Add rules to glossary
    r1_resp = await async_client.post(
        f"/api/v1/brand-glossaries/{gl_id}/rules",
        headers=headers,
        json={
            "source_term": "HeyZen",
            "preferred_term": "Hay-Zen",
            "source_language": "en",
            "case_sensitive": True,
        },
    )
    assert r1_resp.status_code == 201
    r1_id = r1_resp.json()["id"]

    r2_resp = await async_client.post(
        f"/api/v1/brand-glossaries/{gl_id}/rules",
        headers=headers,
        json={
            "source_term": "cheap",
            "preferred_term": "cost-effective",
            "forbidden_term": "cheap",
        },
    )
    assert r2_resp.status_code == 201

    # 4. List rules
    rules_resp = await async_client.get(f"/api/v1/brand-glossaries/{gl_id}/rules", headers=headers)
    assert rules_resp.status_code == 200
    assert len(rules_resp.json()) == 2

    # 5. Update rule
    upd_rule = await async_client.patch(
        f"/api/v1/brand-glossary-rules/{r1_id}",
        headers=headers,
        json={"preferred_term": "HAY-zen"},
    )
    assert upd_rule.status_code == 200
    assert upd_rule.json()["preferred_term"] == "HAY-zen"

    # 6. Delete rule
    del_rule = await async_client.delete(f"/api/v1/brand-glossary-rules/{r1_id}", headers=headers)
    assert del_rule.status_code == 204

    # 7. List rules after deletion
    rules_after = await async_client.get(f"/api/v1/brand-glossaries/{gl_id}/rules", headers=headers)
    assert len(rules_after.json()) == 1


@pytest.mark.asyncio
async def test_glossary_workspace_isolation(async_client: AsyncClient):
    """Verify Workspace B cannot access or modify Workspace A's glossaries and rules."""
    token_a, ws_a = await _setup_user_workspace(async_client, "Glossary Tenant A")
    token_b, ws_b = await _setup_user_workspace(async_client, "Glossary Tenant B")

    headers_a = {"Authorization": f"Bearer {token_a}", "X-Workspace-ID": ws_a}
    headers_b = {"Authorization": f"Bearer {token_b}", "X-Workspace-ID": ws_b}

    gl_a = await async_client.post("/api/v1/brand-glossaries", headers=headers_a, json={"name": "Internal Terms A"})
    assert gl_a.status_code == 201
    gl_a_id = gl_a.json()["id"]

    rule_a = await async_client.post(
        f"/api/v1/brand-glossaries/{gl_a_id}/rules",
        headers=headers_a,
        json={"source_term": "AI", "preferred_term": "Artificial Intelligence"},
    )
    rule_a_id = rule_a.json()["id"]

    # User B list glossaries should be empty
    list_b = await async_client.get("/api/v1/brand-glossaries", headers=headers_b)
    assert len(list_b.json()) == 0

    # User B get glossary fails
    get_b = await async_client.get(f"/api/v1/brand-glossaries/{gl_a_id}", headers=headers_b)
    assert get_b.status_code == 404

    # User B delete rule fails
    del_b = await async_client.delete(f"/api/v1/brand-glossary-rules/{rule_a_id}", headers=headers_b)
    assert del_b.status_code == 404
