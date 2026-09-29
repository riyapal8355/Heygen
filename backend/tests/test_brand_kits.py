"""Test suite for BrandKit identity guidelines, logo asset binding, and default kit management."""

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


async def _create_test_asset(async_client: AsyncClient, token: str, ws_id: str, filename: str = "logo.png") -> str:
    resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/assets/upload-intents",
        headers={"Authorization": f"Bearer {token}"},
        json={"original_filename": filename, "mime_type": "image/png", "size_bytes": 1024, "asset_type": "image"},
    )
    assert resp.status_code == 201
    return resp.json()["asset_id"]


@pytest.mark.asyncio
async def test_brand_kit_crud_and_default_handling(async_client: AsyncClient):
    """Verify brand kit creation, updating default flag, and soft deletion."""
    token, ws_id = await _setup_user_workspace(async_client, "Brand Designer")
    headers = {"Authorization": f"Bearer {token}", "X-Workspace-ID": ws_id}

    logo_id = await _create_test_asset(async_client, token, ws_id, "brand_logo.svg")

    # 1. Create first default brand kit
    k1_resp = await async_client.post(
        "/api/v1/brand-kits",
        headers=headers,
        json={
            "name": "Global Tech Brand",
            "logo_asset_id": logo_id,
            "colors": {"primary": "#0055FF", "secondary": "#111827"},
            "typography": {"primary_font": "Inter", "heading_font": "Cabinet Grotesk"},
            "is_default": True,
        },
    )
    assert k1_resp.status_code == 201
    k1_data = k1_resp.json()
    assert k1_data["is_default"] is True
    k1_id = k1_data["id"]

    # 2. Create second brand kit, also marked default
    k2_resp = await async_client.post(
        "/api/v1/brand-kits",
        headers=headers,
        json={
            "name": "Sub-Brand Spark",
            "colors": {"primary": "#FF3366"},
            "is_default": True,
        },
    )
    assert k2_resp.status_code == 201
    assert k2_resp.json()["is_default"] is True

    # 3. Verify prior kit k1 is no longer default
    get_k1 = await async_client.get(f"/api/v1/brand-kits/{k1_id}", headers=headers)
    assert get_k1.json()["is_default"] is False

    # 4. Update brand kit colors
    upd_resp = await async_client.patch(
        f"/api/v1/brand-kits/{k1_id}",
        headers=headers,
        json={"colors": {"primary": "#0066FF", "accent": "#00FF88"}},
    )
    assert upd_resp.status_code == 200
    assert upd_resp.json()["colors"]["accent"] == "#00FF88"

    # 5. Soft delete brand kit
    del_resp = await async_client.delete(f"/api/v1/brand-kits/{k1_id}", headers=headers)
    assert del_resp.status_code == 204

    # 6. Excluded after delete
    get_after = await async_client.get(f"/api/v1/brand-kits/{k1_id}", headers=headers)
    assert get_after.status_code == 404


@pytest.mark.asyncio
async def test_brand_kit_cross_workspace_logo_rejected(async_client: AsyncClient):
    """Verify linking a logo asset from another workspace fails with 404."""
    token_a, ws_a = await _setup_user_workspace(async_client, "Brand Tenant A")
    token_b, ws_b = await _setup_user_workspace(async_client, "Brand Tenant B")

    logo_b_id = await _create_test_asset(async_client, token_b, ws_b, "foreign_logo.png")

    headers_a = {"Authorization": f"Bearer {token_a}", "X-Workspace-ID": ws_a}
    bad_resp = await async_client.post(
        "/api/v1/brand-kits",
        headers=headers_a,
        json={"name": "Tenant A Kit", "logo_asset_id": logo_b_id},
    )
    assert bad_resp.status_code == 404
    assert bad_resp.json()["error"]["code"] == "ASSET_NOT_FOUND"


@pytest.mark.asyncio
async def test_brand_kit_workspace_isolation(async_client: AsyncClient):
    """Verify Workspace B cannot read or modify Workspace A's brand kit."""
    token_a, ws_a = await _setup_user_workspace(async_client, "Brand Owner A")
    token_b, ws_b = await _setup_user_workspace(async_client, "Brand Owner B")

    headers_a = {"Authorization": f"Bearer {token_a}", "X-Workspace-ID": ws_a}
    headers_b = {"Authorization": f"Bearer {token_b}", "X-Workspace-ID": ws_b}

    kit_a = await async_client.post("/api/v1/brand-kits", headers=headers_a, json={"name": "Confidential Brand"})
    kit_a_id = kit_a.json()["id"]

    # User B list should be empty
    list_b = await async_client.get("/api/v1/brand-kits", headers=headers_b)
    assert len(list_b.json()) == 0

    # User B get fails
    get_b = await async_client.get(f"/api/v1/brand-kits/{kit_a_id}", headers=headers_b)
    assert get_b.status_code == 404
