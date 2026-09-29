"""Test suite for AvatarLook sub-resource management, uniqueness, and security."""

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
async def test_avatar_looks_crud_and_uniqueness(async_client: AsyncClient):
    """Verify creating, listing, updating, deleting looks, and duplicate name prevention."""
    token, ws_id = await _setup_user_workspace(async_client, "Look Manager")
    headers = {"Authorization": f"Bearer {token}", "X-Workspace-ID": ws_id}

    # 1. Create parent avatar
    av_resp = await async_client.post(
        "/api/v1/avatars",
        headers=headers,
        json={"name": "David Presenter"},
    )
    assert av_resp.status_code == 201
    avatar_id = av_resp.json()["id"]

    # 2. Add first look
    look1_resp = await async_client.post(
        f"/api/v1/avatars/{avatar_id}/looks",
        headers=headers,
        json={
            "name": "Casual Polo",
            "description": "Short sleeve polo look",
            "configuration": {"pose": "half_body", "background": "studio_blue"},
        },
    )
    assert look1_resp.status_code == 201
    look1 = look1_resp.json()
    assert look1["name"] == "Casual Polo"
    look1_id = look1["id"]

    # 3. Duplicate look name rejected
    dup_resp = await async_client.post(
        f"/api/v1/avatars/{avatar_id}/looks",
        headers=headers,
        json={"name": "Casual Polo"},
    )
    assert dup_resp.status_code == 409
    assert dup_resp.json()["error"]["code"] == "AVATAR_LOOK_NAME_EXISTS"

    # 4. Add second look
    look2_resp = await async_client.post(
        f"/api/v1/avatars/{avatar_id}/looks",
        headers=headers,
        json={"name": "Formal Tuxedo", "configuration": {"pose": "full_body"}},
    )
    assert look2_resp.status_code == 201

    # 5. List looks
    list_resp = await async_client.get(f"/api/v1/avatars/{avatar_id}/looks", headers=headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 2

    # 6. Get look by ID
    get_resp = await async_client.get(f"/api/v1/avatars/{avatar_id}/looks/{look1_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == "Casual Polo"

    # 7. Update look
    upd_resp = await async_client.patch(
        f"/api/v1/avatars/{avatar_id}/looks/{look1_id}",
        headers=headers,
        json={"name": "Smart Casual Polo"},
    )
    assert upd_resp.status_code == 200
    assert upd_resp.json()["name"] == "Smart Casual Polo"

    # 8. Delete look
    del_resp = await async_client.delete(f"/api/v1/avatars/{avatar_id}/looks/{look1_id}", headers=headers)
    assert del_resp.status_code == 204

    # 9. List after delete
    list_after = await async_client.get(f"/api/v1/avatars/{avatar_id}/looks", headers=headers)
    assert len(list_after.json()) == 1


@pytest.mark.asyncio
async def test_avatar_look_wrong_workspace_rejected(async_client: AsyncClient):
    """Verify Workspace B cannot access or modify Workspace A's avatar looks."""
    token_a, ws_a = await _setup_user_workspace(async_client, "Tenant Look A")
    token_b, ws_b = await _setup_user_workspace(async_client, "Tenant Look B")

    headers_a = {"Authorization": f"Bearer {token_a}", "X-Workspace-ID": ws_a}
    headers_b = {"Authorization": f"Bearer {token_b}", "X-Workspace-ID": ws_b}

    av_resp = await async_client.post("/api/v1/avatars", headers=headers_a, json={"name": "Avatar Alpha"})
    avatar_id = av_resp.json()["id"]

    look_resp = await async_client.post(
        f"/api/v1/avatars/{avatar_id}/looks",
        headers=headers_a,
        json={"name": "Alpha Look"},
    )
    look_id = look_resp.json()["id"]

    # User B attempting to list looks fails with 404
    list_b = await async_client.get(f"/api/v1/avatars/{avatar_id}/looks", headers=headers_b)
    assert list_b.status_code == 404

    # User B attempting to delete look fails with 404
    del_b = await async_client.delete(f"/api/v1/avatars/{avatar_id}/looks/{look_id}", headers=headers_b)
    assert del_b.status_code == 404
