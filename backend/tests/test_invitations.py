"""Test suite for Workspace Invitations and redemption lifecycles."""

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
async def test_invite_member_and_accept(async_client: AsyncClient):
    """Verify invitation creation and redemption flow."""
    owner, token_owner = await _create_user_and_token(async_client, "Inviting Owner")
    ws_id = owner["workspace"]["id"]
    owner_header = {"Authorization": f"Bearer {token_owner}"}

    invitee, token_invitee = await _create_user_and_token(async_client, "Joining User")
    invitee_email = invitee["user"]["email"]

    # 1. Owner invites invitee as Creator
    inv_resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/invitations",
        headers=owner_header,
        json={"email": invitee_email, "role": "creator"},
    )
    assert inv_resp.status_code == 201
    inv_data = inv_resp.json()
    assert inv_data["email"] == invitee_email
    assert inv_data["role"] == "creator"
    token = inv_data["invitation_token"]

    # 2. Invitee accepts invitation
    accept_resp = await async_client.post(
        f"/api/v1/invitations/{token}/accept",
        headers={"Authorization": f"Bearer {token_invitee}"},
    )
    assert accept_resp.status_code == 200
    assert accept_resp.json()["role"] == "creator"

    # 3. Verify invitee is now a member
    members_resp = await async_client.get(
        f"/api/v1/workspaces/{ws_id}/members",
        headers={"Authorization": f"Bearer {token_invitee}"},
    )
    assert members_resp.status_code == 200
    member_emails = [m["email"] for m in members_resp.json()]
    assert invitee_email in member_emails


@pytest.mark.asyncio
async def test_invite_already_existing_member_rejected(async_client: AsyncClient):
    """Verify inviting an existing member returns 409 MEMBER_ALREADY_EXISTS."""
    owner, token_owner = await _create_user_and_token(async_client, "Owner Existing")
    ws_id = owner["workspace"]["id"]

    # Attempt to invite owner's own email
    dup_inv = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/invitations",
        headers={"Authorization": f"Bearer {token_owner}"},
        json={"email": owner["user"]["email"], "role": "admin"},
    )
    assert dup_inv.status_code == 409
    assert dup_inv.json()["error"]["code"] == "MEMBER_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_redeemed_invitation_cannot_be_reused(async_client: AsyncClient):
    """Verify invitation token cannot be redeemed twice."""
    owner, token_owner = await _create_user_and_token(async_client, "One Time Owner")
    ws_id = owner["workspace"]["id"]

    user_b, token_b = await _create_user_and_token(async_client, "Redeemer")
    inv = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/invitations",
        headers={"Authorization": f"Bearer {token_owner}"},
        json={"email": user_b["user"]["email"], "role": "viewer"},
    )
    token = inv.json()["invitation_token"]

    # First accept
    r1 = await async_client.post(
        f"/api/v1/invitations/{token}/accept",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert r1.status_code == 200

    # Second accept attempt -> Conflict (409)
    r2 = await async_client.post(
        f"/api/v1/invitations/{token}/accept",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert r2.status_code == 409
    assert r2.json()["error"]["code"] == "INVITATION_INVALID"


@pytest.mark.asyncio
async def test_revoke_invitation(async_client: AsyncClient):
    """Verify Admin can revoke an invitation, blocking redemption."""
    owner, token_owner = await _create_user_and_token(async_client, "Revoking Owner")
    ws_id = owner["workspace"]["id"]
    owner_header = {"Authorization": f"Bearer {token_owner}"}

    user_c, token_c = await _create_user_and_token(async_client, "Blocked User")
    inv = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/invitations",
        headers=owner_header,
        json={"email": user_c["user"]["email"], "role": "creator"},
    )
    inv_id = inv.json()["id"]
    token = inv.json()["invitation_token"]

    # Revoke invitation
    rev_resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/invitations/{inv_id}/revoke",
        headers=owner_header,
    )
    assert rev_resp.status_code == 200

    # Attempt to accept revoked invitation
    accept_resp = await async_client.post(
        f"/api/v1/invitations/{token}/accept",
        headers={"Authorization": f"Bearer {token_c}"},
    )
    assert accept_resp.status_code == 409
    assert accept_resp.json()["error"]["code"] == "INVITATION_INVALID"
