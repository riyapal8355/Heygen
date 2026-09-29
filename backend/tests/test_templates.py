"""Test suite for Template and immutable TemplateVersion lifecycles."""

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
async def test_template_and_version_immutability_lifecycle(async_client: AsyncClient):
    """Verify template creation with initial version, adding immutable snapshots, and revision increments."""
    token, ws_id = await _setup_user_workspace(async_client, "Template Architect")
    headers = {"Authorization": f"Bearer {token}", "X-Workspace-ID": ws_id}

    # 1. Create template (initializes revision 1 snapshot)
    create_resp = await async_client.post(
        "/api/v1/templates",
        headers=headers,
        json={
            "name": "Product Teaser 16:9",
            "category": "marketing",
            "description": "High converting product launch video template",
            "configuration": {"placeholders": ["{{product_name}}", "{{tagline}}"]},
        },
    )
    assert create_resp.status_code == 201
    tpl_data = create_resp.json()
    assert tpl_data["name"] == "Product Teaser 16:9"
    assert tpl_data["revision"] == 1
    assert tpl_data["current_version_id"] is not None
    tpl_id = tpl_data["id"]

    # 2. Check initial version in version list
    ver_list_resp = await async_client.get(f"/api/v1/templates/{tpl_id}/versions", headers=headers)
    assert ver_list_resp.status_code == 200
    versions = ver_list_resp.json()
    assert len(versions) == 1
    assert versions[0]["revision"] == 1
    v1_id = versions[0]["id"]

    # 3. Create new immutable version snapshot (revision 2)
    new_doc = {
        "version": 1,
        "scenes": [{"id": "scene_1", "duration": 5.0, "layers": []}],
        "placeholders": [{"token": "{{product_name}}", "default": "My Product"}],
    }
    v2_resp = await async_client.post(
        f"/api/v1/templates/{tpl_id}/versions",
        headers=headers,
        json={"document": new_doc},
    )
    assert v2_resp.status_code == 201
    v2_data = v2_resp.json()
    assert v2_data["revision"] == 2
    assert v2_data["document"]["scenes"][0]["id"] == "scene_1"
    v2_id = v2_data["id"]

    # 4. Check updated template reflects revision 2
    get_tpl = await async_client.get(f"/api/v1/templates/{tpl_id}", headers=headers)
    assert get_tpl.json()["revision"] == 2
    assert get_tpl.json()["current_version_id"] == v2_id

    # 5. Fetch historical revision 1 by ID and verify it remains unchanged
    get_v1 = await async_client.get(f"/api/v1/templates/{tpl_id}/versions/{v1_id}", headers=headers)
    assert get_v1.status_code == 200
    assert get_v1.json()["revision"] == 1

    # 6. List versions shows both (ordered descending)
    all_versions = await async_client.get(f"/api/v1/templates/{tpl_id}/versions", headers=headers)
    assert len(all_versions.json()) == 2
    assert all_versions.json()[0]["revision"] == 2
    assert all_versions.json()[1]["revision"] == 1

    # 7. Soft delete template
    del_resp = await async_client.delete(f"/api/v1/templates/{tpl_id}", headers=headers)
    assert del_resp.status_code == 204

    # 8. Excluded after deletion
    get_after = await async_client.get(f"/api/v1/templates/{tpl_id}", headers=headers)
    assert get_after.status_code == 404


@pytest.mark.asyncio
async def test_duplicate_template_name_rejected(async_client: AsyncClient):
    """Verify duplicate template name in same workspace triggers 409 Conflict."""
    token, ws_id = await _setup_user_workspace(async_client, "Dup Tpl User")
    headers = {"Authorization": f"Bearer {token}", "X-Workspace-ID": ws_id}

    r1 = await async_client.post("/api/v1/templates", headers=headers, json={"name": "Sales Pitch"})
    assert r1.status_code == 201

    r2 = await async_client.post("/api/v1/templates", headers=headers, json={"name": "Sales Pitch"})
    assert r2.status_code == 409
    assert r2.json()["error"]["code"] == "TEMPLATE_NAME_EXISTS"


@pytest.mark.asyncio
async def test_template_workspace_isolation(async_client: AsyncClient):
    """Verify Workspace B cannot read or modify Workspace A's template or version snapshots."""
    token_a, ws_a = await _setup_user_workspace(async_client, "Tpl Tenant A")
    token_b, ws_b = await _setup_user_workspace(async_client, "Tpl Tenant B")

    headers_a = {"Authorization": f"Bearer {token_a}", "X-Workspace-ID": ws_a}
    headers_b = {"Authorization": f"Bearer {token_b}", "X-Workspace-ID": ws_b}

    tpl_a = await async_client.post("/api/v1/templates", headers=headers_a, json={"name": "Confidential Template"})
    assert tpl_a.status_code == 201
    tpl_a_id = tpl_a.json()["id"]

    # User B list should be empty
    list_b = await async_client.get("/api/v1/templates", headers=headers_b)
    assert len(list_b.json()) == 0

    # User B get fails
    get_b = await async_client.get(f"/api/v1/templates/{tpl_a_id}", headers=headers_b)
    assert get_b.status_code == 404

    # User B version creation fails
    ver_b = await async_client.post(
        f"/api/v1/templates/{tpl_a_id}/versions",
        headers=headers_b,
        json={"document": {}},
    )
    assert ver_b.status_code == 404
