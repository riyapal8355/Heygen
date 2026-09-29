"""Test suite for Avatar domain lifecycle, asset validation, uniqueness, and workspace isolation."""

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


async def _create_test_asset(async_client: AsyncClient, token: str, ws_id: str, filename: str = "portrait.png") -> str:
    resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/assets/upload-intents",
        headers={"Authorization": f"Bearer {token}"},
        json={"original_filename": filename, "mime_type": "image/png", "size_bytes": 2048, "asset_type": "image"},
    )
    assert resp.status_code == 201
    return resp.json()["asset_id"]


@pytest.mark.asyncio
async def test_avatar_crud_flow(async_client: AsyncClient):
    """Verify avatar creation with initial look, retrieval, update, and soft-deletion."""
    token, ws_id = await _setup_user_workspace(async_client, "Avatar Creator")
    headers = {"Authorization": f"Bearer {token}", "X-Workspace-ID": ws_id}

    preview_asset_id = await _create_test_asset(async_client, token, ws_id, "avatar_preview.png")

    # 1. Create avatar with initial look
    create_resp = await async_client.post(
        "/api/v1/avatars",
        headers=headers,
        json={
            "name": "Sarah Executive",
            "description": "Corporate spokesperson avatar",
            "avatar_type": "digital_twin",
            "preview_asset_id": preview_asset_id,
            "initial_look": {
                "name": "Navy Blazer",
                "description": "Standard business presentation attire",
                "configuration": {"pose": "half_body"},
            },
        },
    )
    assert create_resp.status_code == 201
    avatar_data = create_resp.json()
    assert avatar_data["name"] == "Sarah Executive"
    assert avatar_data["avatar_type"] == "digital_twin"
    avatar_id = avatar_data["id"]

    # Verify initial look created via looks sub-resource
    looks_resp = await async_client.get(f"/api/v1/avatars/{avatar_id}/looks", headers=headers)
    assert looks_resp.status_code == 200
    looks = looks_resp.json()
    assert len(looks) == 1
    assert looks[0]["name"] == "Navy Blazer"

    # 2. Get avatar by ID
    get_resp = await async_client.get(f"/api/v1/avatars/{avatar_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == avatar_id

    # 3. List avatars (verify workspace avatar exists alongside public catalog)
    list_resp = await async_client.get("/api/v1/avatars", headers=headers)
    assert list_resp.status_code == 200
    items = list_resp.json()
    ws_items = [a for a in items if a["workspace_id"] == ws_id]
    assert len(ws_items) == 1
    assert ws_items[0]["id"] == avatar_id
    pub_items = [a for a in items if a["visibility"] == "public"]
    assert len(pub_items) >= 5

    # 4. Update avatar
    update_resp = await async_client.patch(
        f"/api/v1/avatars/{avatar_id}",
        headers=headers,
        json={"name": "Sarah Senior Executive", "description": "Updated description"},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["name"] == "Sarah Senior Executive"

    # 5. Delete avatar (soft-delete)
    del_resp = await async_client.delete(f"/api/v1/avatars/{avatar_id}", headers=headers)
    assert del_resp.status_code == 204

    # 6. Deleted avatar excluded from listing and get returns 404
    list_after = await async_client.get("/api/v1/avatars", headers=headers)
    assert list_after.status_code == 200
    ws_after = [a for a in list_after.json() if a["workspace_id"] == ws_id]
    assert len(ws_after) == 0

    get_after = await async_client.get(f"/api/v1/avatars/{avatar_id}", headers=headers)
    assert get_after.status_code == 404


@pytest.mark.asyncio
async def test_duplicate_avatar_name_rejected(async_client: AsyncClient):
    """Verify duplicate avatar names within the same workspace trigger 409 Conflict."""
    token, ws_id = await _setup_user_workspace(async_client, "Dup Avatar User")
    headers = {"Authorization": f"Bearer {token}", "X-Workspace-ID": ws_id}

    r1 = await async_client.post("/api/v1/avatars", headers=headers, json={"name": "Marcus Studio"})
    assert r1.status_code == 201

    r2 = await async_client.post("/api/v1/avatars", headers=headers, json={"name": "Marcus Studio"})
    assert r2.status_code == 409
    error = r2.json()
    assert error["error"]["code"] == "AVATAR_NAME_EXISTS"


@pytest.mark.asyncio
async def test_cross_workspace_asset_reference_rejected(async_client: AsyncClient):
    """Verify linking an asset owned by Workspace B to an avatar in Workspace A fails with 404."""
    token_a, ws_a = await _setup_user_workspace(async_client, "Tenant A")
    token_b, ws_b = await _setup_user_workspace(async_client, "Tenant B")

    # Create asset in Workspace B
    asset_b_id = await _create_test_asset(async_client, token_b, ws_b, "asset_b.png")

    # Attempt to create avatar in Workspace A referencing Workspace B asset
    headers_a = {"Authorization": f"Bearer {token_a}", "X-Workspace-ID": ws_a}
    bad_resp = await async_client.post(
        "/api/v1/avatars",
        headers=headers_a,
        json={"name": "Cross Tenant Avatar", "preview_asset_id": asset_b_id},
    )
    assert bad_resp.status_code == 404
    assert bad_resp.json()["error"]["code"] == "ASSET_NOT_FOUND"


@pytest.mark.asyncio
async def test_workspace_isolation_avatars(async_client: AsyncClient):
    """Verify Workspace B cannot read or modify Workspace A's avatar."""
    token_a, ws_a = await _setup_user_workspace(async_client, "Owner A")
    token_b, ws_b = await _setup_user_workspace(async_client, "Owner B")

    headers_a = {"Authorization": f"Bearer {token_a}", "X-Workspace-ID": ws_a}
    headers_b = {"Authorization": f"Bearer {token_b}", "X-Workspace-ID": ws_b}

    resp = await async_client.post("/api/v1/avatars", headers=headers_a, json={"name": "Secret Avatar A"})
    assert resp.status_code == 201
    avatar_id = resp.json()["id"]

    # User B listing should not contain User A's private avatar
    list_b = await async_client.get("/api/v1/avatars", headers=headers_b)
    assert list_b.status_code == 200
    assert not any(a["id"] == avatar_id for a in list_b.json())

    # User B get by ID fails with 404
    get_b = await async_client.get(f"/api/v1/avatars/{avatar_id}", headers=headers_b)
    assert get_b.status_code == 404

    # User B delete fails with 404
    del_b = await async_client.delete(f"/api/v1/avatars/{avatar_id}", headers=headers_b)
    assert del_b.status_code == 404
