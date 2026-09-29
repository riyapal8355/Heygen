"""Test suite for Workspace Memberships, Role Management, and Constraints."""

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workspace import WorkspaceMember
from app.repositories.workspace import WorkspaceRepository


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
async def test_list_members(async_client: AsyncClient):
    """Verify listing members of a workspace."""
    user_a, token_a = await _create_user_and_token(async_client, "Team Owner")
    ws_id = user_a["workspace"]["id"]
    auth_header = {"Authorization": f"Bearer {token_a}"}

    resp = await async_client.get(f"/api/v1/workspaces/{ws_id}/members", headers=auth_header)
    assert resp.status_code == 200
    members = resp.json()
    assert len(members) == 1
    assert members[0]["email"] == user_a["user"]["email"]
    assert members[0]["role"] == "owner"


@pytest.mark.asyncio
async def test_admin_can_manage_members_and_creator_cannot(async_client: AsyncClient):
    """Verify Admin can update roles, but Creator cannot."""
    # 1. Create Owner & Workspace
    user_owner, token_owner = await _create_user_and_token(async_client, "WS Owner")
    ws_id = user_owner["workspace"]["id"]
    owner_header = {"Authorization": f"Bearer {token_owner}"}

    # 2. Add Member B as Admin
    user_admin, token_admin = await _create_user_and_token(async_client, "WS Admin")
    inv_admin = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/invitations",
        headers=owner_header,
        json={"email": user_admin["user"]["email"], "role": "admin"},
    )
    await async_client.post(
        f"/api/v1/invitations/{inv_admin.json()['invitation_token']}/accept",
        headers={"Authorization": f"Bearer {token_admin}"},
    )

    # 3. Add Member C as Viewer
    user_c, token_c = await _create_user_and_token(async_client, "WS Viewer")
    inv_c = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/invitations",
        headers=owner_header,
        json={"email": user_c["user"]["email"], "role": "viewer"},
    )
    await async_client.post(
        f"/api/v1/invitations/{inv_c.json()['invitation_token']}/accept",
        headers={"Authorization": f"Bearer {token_c}"},
    )

    # 4. Admin promotes Viewer to Creator -> Allowed
    admin_header = {"Authorization": f"Bearer {token_admin}"}
    patch_resp = await async_client.patch(
        f"/api/v1/workspaces/{ws_id}/members/{user_c['user']['id']}",
        headers=admin_header,
        json={"role": "creator"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["role"] == "creator"

    # 5. User C (now Creator) attempts to manage members -> Forbidden (403)
    creator_header = {"Authorization": f"Bearer {token_c}"}
    fail_patch = await async_client.patch(
        f"/api/v1/workspaces/{ws_id}/members/{user_admin['user']['id']}",
        headers=creator_header,
        json={"role": "viewer"},
    )
    assert fail_patch.status_code == 403


@pytest.mark.asyncio
async def test_owner_cannot_be_removed_or_demoted(async_client: AsyncClient):
    """Verify Workspace Owner account cannot be removed or demoted directly."""
    user_owner, token_owner = await _create_user_and_token(async_client, "Immutable Owner")
    ws_id = user_owner["workspace"]["id"]
    owner_id = user_owner["user"]["id"]
    owner_header = {"Authorization": f"Bearer {token_owner}"}

    # 1. Attempt to remove Owner
    del_resp = await async_client.delete(
        f"/api/v1/workspaces/{ws_id}/members/{owner_id}",
        headers=owner_header,
    )
    assert del_resp.status_code == 409
    assert del_resp.json()["error"]["code"] == "OWNER_CANNOT_LEAVE"

    # 2. Attempt to demote Owner to Creator
    patch_resp = await async_client.patch(
        f"/api/v1/workspaces/{ws_id}/members/{owner_id}",
        headers=owner_header,
        json={"role": "creator"},
    )
    assert patch_resp.status_code == 409
    assert patch_resp.json()["error"]["code"] == "OWNER_ROLE_LOCKED"


@pytest.mark.asyncio
async def test_member_self_removal(async_client: AsyncClient):
    """Verify regular member can remove themselves (leave workspace)."""
    user_owner, token_owner = await _create_user_and_token(async_client, "Org Boss")
    ws_id = user_owner["workspace"]["id"]

    user_leaver, token_leaver = await _create_user_and_token(async_client, "Leaving User")
    inv = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/invitations",
        headers={"Authorization": f"Bearer {token_owner}"},
        json={"email": user_leaver["user"]["email"], "role": "creator"},
    )
    await async_client.post(
        f"/api/v1/invitations/{inv.json()['invitation_token']}/accept",
        headers={"Authorization": f"Bearer {token_leaver}"},
    )

    # Member removes themselves
    del_resp = await async_client.delete(
        f"/api/v1/workspaces/{ws_id}/members/{user_leaver['user']['id']}",
        headers={"Authorization": f"Bearer {token_leaver}"},
    )
    assert del_resp.status_code == 204


@pytest.mark.asyncio
async def test_duplicate_membership_constraint_enforced(db_session: AsyncSession):
    """Verify PostgreSQL UNIQUE(workspace_id, user_id) constraint prevents duplicate membership."""
    from app.models.user import User
    from app.models.workspace import Workspace

    user = User(email=f"unique_member_{uuid.uuid4().hex[:6]}@example.com", display_name="Member Test")
    db_session.add(user)
    await db_session.flush()

    ws = Workspace(name="Unique WS", slug=f"unique-ws-{uuid.uuid4().hex[:6]}", owner_id=user.id)
    db_session.add(ws)
    await db_session.flush()

    m1 = WorkspaceMember(
        workspace_id=ws.id,
        user_id=user.id,
        role="creator",
        status="active",
    )
    db_session.add(m1)
    await db_session.flush()

    # Attempt second membership for same workspace and user
    m2 = WorkspaceMember(
        workspace_id=ws.id,
        user_id=user.id,
        role="admin",
        status="active",
    )
    db_session.add(m2)

    with pytest.raises(IntegrityError):
        await db_session.flush()
