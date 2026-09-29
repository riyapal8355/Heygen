"""Test suite for Workspace creation, listing, updating, soft deletion, and ownership transfer."""

import uuid
import pytest
from httpx import AsyncClient


async def _create_user_and_token(async_client: AsyncClient, name: str) -> tuple[dict, str]:
    email = f"{name.lower().replace(' ', '_')}_{uuid.uuid4().hex[:6]}@example.com"
    resp = await async_client.post(
        "/api/v1/auth/signup",
        json={"email": email, "display_name": name, "password": "Password123!"},
    )
    assert resp.status_code == 201
    data = resp.json()
    return data, data["tokens"]["access_token"]


@pytest.mark.asyncio
async def test_create_workspace(async_client: AsyncClient):
    """Verify user can create an additional workspace and becomes its Owner."""
    _, token = await _create_user_and_token(async_client, "Org Founder")
    auth_header = {"Authorization": f"Bearer {token}"}

    create_resp = await async_client.post(
        "/api/v1/workspaces",
        headers=auth_header,
        json={"name": "Acme Media Studio"},
    )
    assert create_resp.status_code == 201
    data = create_resp.json()
    assert data["name"] == "Acme Media Studio"
    assert "acme-media-studio" in data["slug"]
    assert data["role"] == "owner"
    assert data["status"] == "active"


@pytest.mark.asyncio
async def test_list_user_workspaces(async_client: AsyncClient):
    """Verify user sees only the workspaces they belong to."""
    user_data, token = await _create_user_and_token(async_client, "Multi Org")
    auth_header = {"Authorization": f"Bearer {token}"}

    # Initial personal workspace created at signup
    list_1 = await async_client.get("/api/v1/workspaces", headers=auth_header)
    assert list_1.status_code == 200
    assert len(list_1.json()) == 1

    # Create second workspace
    await async_client.post(
        "/api/v1/workspaces",
        headers=auth_header,
        json={"name": "Second Workspace"},
    )

    list_2 = await async_client.get("/api/v1/workspaces", headers=auth_header)
    assert list_2.status_code == 200
    assert len(list_2.json()) == 2


@pytest.mark.asyncio
async def test_workspace_isolation_non_member_forbidden(async_client: AsyncClient):
    """Verify User B cannot access User A's workspace."""
    _, token_a = await _create_user_and_token(async_client, "User A")
    ws_a_resp = await async_client.post(
        "/api/v1/workspaces",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"name": "Secret A Workspace"},
    )
    ws_a_id = ws_a_resp.json()["id"]

    _, token_b = await _create_user_and_token(async_client, "User B")

    # User B attempts to fetch User A's workspace
    forbidden_resp = await async_client.get(
        f"/api/v1/workspaces/{ws_a_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert forbidden_resp.status_code in (403, 404)


@pytest.mark.asyncio
async def test_update_workspace(async_client: AsyncClient):
    """Verify Owner can update workspace name."""
    _, token = await _create_user_and_token(async_client, "Updater")
    auth_header = {"Authorization": f"Bearer {token}"}

    ws_resp = await async_client.post(
        "/api/v1/workspaces",
        headers=auth_header,
        json={"name": "Initial Name"},
    )
    ws_id = ws_resp.json()["id"]

    patch_resp = await async_client.patch(
        f"/api/v1/workspaces/{ws_id}",
        headers=auth_header,
        json={"name": "Updated Name Studio"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["name"] == "Updated Name Studio"


@pytest.mark.asyncio
async def test_delete_workspace_owner_only(async_client: AsyncClient):
    """Verify Owner can soft-delete workspace, hiding it from listings."""
    _, token = await _create_user_and_token(async_client, "Deleter")
    auth_header = {"Authorization": f"Bearer {token}"}

    ws_resp = await async_client.post(
        "/api/v1/workspaces",
        headers=auth_header,
        json={"name": "Doomed Workspace"},
    )
    ws_id = ws_resp.json()["id"]

    del_resp = await async_client.delete(
        f"/api/v1/workspaces/{ws_id}",
        headers=auth_header,
    )
    assert del_resp.status_code == 204

    # Workspace should no longer appear in active listings
    list_resp = await async_client.get("/api/v1/workspaces", headers=auth_header)
    ids = [w["id"] for w in list_resp.json()]
    assert ws_id not in ids


@pytest.mark.asyncio
async def test_transfer_ownership_success(async_client: AsyncClient):
    """Verify Owner transfers workspace ownership to another member atomically."""
    # 1. Create Owner and Workspace
    user_a, token_a = await _create_user_and_token(async_client, "Owner A")
    ws_resp = await async_client.post(
        "/api/v1/workspaces",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"name": "Transferable Media"},
    )
    ws_id = ws_resp.json()["id"]

    # 2. Create User B and invite/add them to workspace
    user_b, token_b = await _create_user_and_token(async_client, "Member B")
    user_b_id = user_b["user"]["id"]

    # Owner A invites Member B
    inv_resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/invitations",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"email": user_b["user"]["email"], "role": "admin"},
    )
    assert inv_resp.status_code == 201
    token_str = inv_resp.json()["invitation_token"]

    # Member B accepts invitation
    accept_resp = await async_client.post(
        f"/api/v1/invitations/{token_str}/accept",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert accept_resp.status_code == 200

    # 3. Owner A transfers ownership to Member B
    transfer_resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/transfer-ownership",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"target_user_id": user_b_id},
    )
    assert transfer_resp.status_code == 200
    updated_ws = transfer_resp.json()
    assert updated_ws["owner_id"] == user_b_id

    # 4. Verify Member B now sees role == 'owner'
    ws_b_get = await async_client.get(
        f"/api/v1/workspaces/{ws_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert ws_b_get.status_code == 200
    assert ws_b_get.json()["role"] == "owner"
