"""Test suite for Role-Based Access Control (RBAC) across Creative Library resources."""

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


async def _invite_and_join(
    async_client: AsyncClient,
    owner_token: str,
    ws_id: str,
    invitee_token: str,
    invitee_email: str,
    role: str,
) -> None:
    inv_resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/invitations",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"email": invitee_email, "role": role},
    )
    assert inv_resp.status_code == 201
    inv_token = inv_resp.json()["invitation_token"]

    join_resp = await async_client.post(
        f"/api/v1/invitations/{inv_token}/accept",
        headers={"Authorization": f"Bearer {invitee_token}"},
    )
    assert join_resp.status_code == 200


@pytest.mark.asyncio
async def test_rbac_creative_library_roles(async_client: AsyncClient):
    """Verify Owner, Creator, and Viewer permissions on Creative Library resources."""
    # 1. Setup workspace with Owner
    owner_data, owner_token = await _create_user_and_token(async_client, "RBAC Owner")
    ws_id = owner_data["workspace"]["id"]
    owner_headers = {"Authorization": f"Bearer {owner_token}", "X-Workspace-ID": ws_id}

    # 2. Add Creator
    creator_data, creator_token = await _create_user_and_token(async_client, "RBAC Creator")
    await _invite_and_join(
        async_client,
        owner_token,
        ws_id,
        creator_token,
        creator_data["user"]["email"],
        "creator",
    )
    creator_headers = {"Authorization": f"Bearer {creator_token}", "X-Workspace-ID": ws_id}

    # 3. Add Viewer
    viewer_data, viewer_token = await _create_user_and_token(async_client, "RBAC Viewer")
    await _invite_and_join(
        async_client,
        owner_token,
        ws_id,
        viewer_token,
        viewer_data["user"]["email"],
        "viewer",
    )
    viewer_headers = {"Authorization": f"Bearer {viewer_token}", "X-Workspace-ID": ws_id}

    # 4. Creator can create Avatar, Voice, and Template
    av_resp = await async_client.post(
        "/api/v1/avatars",
        headers=creator_headers,
        json={"name": "Creator Avatar"},
    )
    assert av_resp.status_code == 201

    voice_resp = await async_client.post(
        "/api/v1/voices",
        headers=creator_headers,
        json={"name": "Creator Voice"},
    )
    assert voice_resp.status_code == 201

    tpl_resp = await async_client.post(
        "/api/v1/templates",
        headers=creator_headers,
        json={"name": "Creator Template"},
    )
    assert tpl_resp.status_code == 201

    # Creator CANNOT create BrandKit (only Owner/Admin has brand.create)
    brand_fail = await async_client.post(
        "/api/v1/brand-kits",
        headers=creator_headers,
        json={"name": "Forbidden Kit"},
    )
    assert brand_fail.status_code == 403
    assert brand_fail.json()["error"]["code"] == "INSUFFICIENT_PERMISSIONS"

    # 5. Viewer CAN read Avatars, Voices, Templates, BrandKits
    assert (await async_client.get("/api/v1/avatars", headers=viewer_headers)).status_code == 200
    assert (await async_client.get("/api/v1/voices", headers=viewer_headers)).status_code == 200
    assert (await async_client.get("/api/v1/templates", headers=viewer_headers)).status_code == 200
    assert (await async_client.get("/api/v1/brand-kits", headers=viewer_headers)).status_code == 200

    # 6. Viewer CANNOT create Avatars, Voices, or Templates
    assert (await async_client.post(
        "/api/v1/avatars",
        headers=viewer_headers,
        json={"name": "Viewer Avatar"},
    )).status_code == 403

    assert (await async_client.post(
        "/api/v1/voices",
        headers=viewer_headers,
        json={"name": "Viewer Voice"},
    )).status_code == 403

    assert (await async_client.post(
        "/api/v1/templates",
        headers=viewer_headers,
        json={"name": "Viewer Template"},
    )).status_code == 403

    # 7. Unauthenticated request rejected
    assert (await async_client.get("/api/v1/avatars")).status_code == 401
