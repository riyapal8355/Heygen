"""Test suite for Workspace Onboarding Status, Locking Rules, and Completion API."""

import uuid
import pytest
from httpx import AsyncClient


async def _create_user_and_workspace(async_client: AsyncClient, name: str) -> tuple[dict, str, str]:
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
    workspaces = ws_resp.json()
    assert len(workspaces) >= 1
    workspace_id = workspaces[0]["id"]
    return data, token, workspace_id


@pytest.mark.asyncio
async def test_initial_onboarding_status(async_client: AsyncClient):
    """Verify freshly created workspace starts at 0/4 with only Step 1 unlocked."""
    _, token, workspace_id = await _create_user_and_workspace(async_client, "Fresh User")
    headers = {"Authorization": f"Bearer {token}"}

    resp = await async_client.get(f"/api/v1/workspaces/{workspace_id}/onboarding", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["step_1_digital_twin"] is False
    assert data["step_2_voice"] is False
    assert data["step_3_look"] is False
    assert data["step_4_video"] is False
    assert data["completed_count"] == 0
    assert data["total_steps"] == 4
    assert data["is_step_2_unlocked"] is False
    assert data["is_step_3_unlocked"] is False
    assert data["is_step_4_unlocked"] is False


@pytest.mark.asyncio
async def test_complete_step_1_unlocks_steps_2_and_3(async_client: AsyncClient):
    """Completing step 1 marks digital twin done, yields 1/4, and unlocks steps 2 & 3."""
    _, token, workspace_id = await _create_user_and_workspace(async_client, "Twin Creator")
    headers = {"Authorization": f"Bearer {token}"}

    step1_resp = await async_client.post(
        f"/api/v1/workspaces/{workspace_id}/onboarding/complete-step",
        headers=headers,
        json={"step": 1},
    )
    assert step1_resp.status_code == 200
    data = step1_resp.json()

    assert data["step_1_digital_twin"] is True
    assert data["completed_count"] == 1
    assert data["is_step_2_unlocked"] is True
    assert data["is_step_3_unlocked"] is True
    assert data["is_step_4_unlocked"] is False
    assert 1 in data["completed_steps"]

    # Verify persistent state via GET
    get_resp = await async_client.get(f"/api/v1/workspaces/{workspace_id}/onboarding", headers=headers)
    assert get_resp.status_code == 200
    get_data = get_resp.json()
    assert get_data["step_1_digital_twin"] is True
    assert get_data["completed_count"] == 1


@pytest.mark.asyncio
async def test_step_4_unlocked_after_step_2(async_client: AsyncClient):
    """Step 4 unlocks when Step 2 is completed even if Step 3 is incomplete."""
    _, token, workspace_id = await _create_user_and_workspace(async_client, "Voice Polisher")
    headers = {"Authorization": f"Bearer {token}"}

    # Complete Step 1
    await async_client.post(
        f"/api/v1/workspaces/{workspace_id}/onboarding/complete-step",
        headers=headers,
        json={"step": 1},
    )
    # Complete Step 2
    step2_resp = await async_client.post(
        f"/api/v1/workspaces/{workspace_id}/onboarding/complete-step",
        headers=headers,
        json={"step": 2},
    )
    assert step2_resp.status_code == 200
    data = step2_resp.json()

    assert data["step_2_voice"] is True
    assert data["completed_count"] == 2
    assert data["is_step_4_unlocked"] is True


@pytest.mark.asyncio
async def test_step_4_unlocked_after_step_3(async_client: AsyncClient):
    """Step 4 unlocks when Step 3 is completed even if Step 2 is incomplete."""
    _, token, workspace_id = await _create_user_and_workspace(async_client, "Look Designer")
    headers = {"Authorization": f"Bearer {token}"}

    # Complete Step 1
    await async_client.post(
        f"/api/v1/workspaces/{workspace_id}/onboarding/complete-step",
        headers=headers,
        json={"step": 1},
    )
    # Complete Step 3
    step3_resp = await async_client.post(
        f"/api/v1/workspaces/{workspace_id}/onboarding/complete-step",
        headers=headers,
        json={"step": 3},
    )
    assert step3_resp.status_code == 200
    data = step3_resp.json()

    assert data["step_3_look"] is True
    assert data["completed_count"] == 2
    assert data["is_step_4_unlocked"] is True


@pytest.mark.asyncio
async def test_full_onboarding_completion(async_client: AsyncClient):
    """Completing all 4 steps yields 4/4 and persistent completed state."""
    _, token, workspace_id = await _create_user_and_workspace(async_client, "Master Producer")
    headers = {"Authorization": f"Bearer {token}"}

    for step in [1, 2, 3, 4]:
        resp = await async_client.post(
            f"/api/v1/workspaces/{workspace_id}/onboarding/complete-step",
            headers=headers,
            json={"step": step},
        )
        assert resp.status_code == 200

    final_resp = await async_client.get(f"/api/v1/workspaces/{workspace_id}/onboarding", headers=headers)
    assert final_resp.status_code == 200
    data = final_resp.json()

    assert data["step_1_digital_twin"] is True
    assert data["step_2_voice"] is True
    assert data["step_3_look"] is True
    assert data["step_4_video"] is True
    assert data["completed_count"] == 4
    assert set(data["completed_steps"]) == {1, 2, 3, 4}
