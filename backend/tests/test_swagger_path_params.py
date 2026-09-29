"""Regression tests for Swagger path parameters, UUID validation, and workspace header context (Phase 45.7)."""

import uuid
import pytest
from httpx import AsyncClient
from app.db.seeds import (
    DEV_USER_EMAIL,
    DEV_USER_PASSWORD,
    DEV_WORKSPACE_ID,
    DEV_FOLDER_ID,
    DEV_PROJECT_ID,
)


async def _setup_authenticated_user(async_client: AsyncClient, name: str) -> tuple[str, str]:
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
async def test_literal_placeholder_path_parameter_rejected(async_client: AsyncClient):
    """Verify that unpopulated Swagger path parameters like {workspace_id} are safely rejected with WORKSPACE_INVALID_ID."""
    token, _ = await _setup_authenticated_user(async_client, "Placeholder Tester")
    headers = {"Authorization": f"Bearer {token}"}
    fake_folder_id = str(uuid.uuid4())

    # Literal {workspace_id} in path
    resp = await async_client.get(
        f"/api/v1/workspaces/{{workspace_id}}/folders/{fake_folder_id}",
        headers=headers,
    )
    assert resp.status_code == 404
    data = resp.json()
    assert data["error"]["code"] == "WORKSPACE_INVALID_ID"
    assert "Invalid workspace ID in URL path" in data["error"]["message"]


@pytest.mark.asyncio
async def test_malformed_uuid_path_parameter_rejected(async_client: AsyncClient):
    """Verify that non-UUID strings in path parameters are safely rejected without database query errors."""
    token, _ = await _setup_authenticated_user(async_client, "Malformed Tester")
    headers = {"Authorization": f"Bearer {token}"}
    fake_folder_id = str(uuid.uuid4())

    resp = await async_client.get(
        f"/api/v1/workspaces/not-a-valid-uuid/folders/{fake_folder_id}",
        headers=headers,
    )
    assert resp.status_code == 404
    data = resp.json()
    assert data["error"]["code"] == "WORKSPACE_INVALID_ID"


@pytest.mark.asyncio
async def test_matching_workspace_header_and_path_accepted(async_client: AsyncClient):
    """Verify that when both path parameter and X-Workspace-ID header match, the request succeeds."""
    token, ws_id = await _setup_authenticated_user(async_client, "Matching Context")
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Workspace-ID": ws_id,
    }

    # Create folder
    create_resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/folders",
        headers=headers,
        json={"name": "Test Swagger Folder"},
    )
    assert create_resp.status_code == 201
    folder_id = create_resp.json()["id"]

    # Fetch folder with matching header
    get_resp = await async_client.get(
        f"/api/v1/workspaces/{ws_id}/folders/{folder_id}",
        headers=headers,
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == folder_id
    assert get_resp.json()["name"] == "Test Swagger Folder"


@pytest.mark.asyncio
async def test_mismatched_workspace_header_rejected(async_client: AsyncClient):
    """Verify that providing an X-Workspace-ID that conflicts with the URL path raises 403 WORKSPACE_MISMATCH."""
    token, ws_id = await _setup_authenticated_user(async_client, "Mismatch Tester")
    headers = {"Authorization": f"Bearer {token}"}

    create_resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/folders",
        headers=headers,
        json={"name": "Mismatch Target Folder"},
    )
    assert create_resp.status_code == 201
    folder_id = create_resp.json()["id"]

    # Now attempt access with a conflicting X-Workspace-ID header
    conflicting_ws_id = str(uuid.uuid4())
    mismatched_headers = {
        "Authorization": f"Bearer {token}",
        "X-Workspace-ID": conflicting_ws_id,
    }
    resp = await async_client.get(
        f"/api/v1/workspaces/{ws_id}/folders/{folder_id}",
        headers=mismatched_headers,
    )
    assert resp.status_code == 403
    data = resp.json()
    assert data["error"]["code"] == "WORKSPACE_MISMATCH"
    assert "X-Workspace-ID header does not match workspace ID in URL path" in data["error"]["message"]


@pytest.mark.asyncio
async def test_development_fixtures_accessible(async_client: AsyncClient):
    """Verify that development seed fixtures (DEV_WORKSPACE_ID, DEV_FOLDER_ID, DEV_PROJECT_ID) are properly accessible."""
    # Authenticate as the seeded dev user
    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"email": DEV_USER_EMAIL, "password": DEV_USER_PASSWORD},
    )
    assert login_resp.status_code == 200
    dev_token = login_resp.json()["tokens"]["access_token"]
    headers = {"Authorization": f"Bearer {dev_token}"}

    # Verify seeded workspace access
    ws_resp = await async_client.get(f"/api/v1/workspaces/{DEV_WORKSPACE_ID}", headers=headers)
    assert ws_resp.status_code == 200
    assert ws_resp.json()["id"] == str(DEV_WORKSPACE_ID)

    # Verify seeded folder access
    folder_resp = await async_client.get(f"/api/v1/workspaces/{DEV_WORKSPACE_ID}/folders/{DEV_FOLDER_ID}", headers=headers)
    assert folder_resp.status_code == 200
    assert folder_resp.json()["id"] == str(DEV_FOLDER_ID)
    assert folder_resp.json()["name"] == "Demo Projects"

    # Verify seeded project access
    proj_resp = await async_client.get(f"/api/v1/workspaces/{DEV_WORKSPACE_ID}/projects/{DEV_PROJECT_ID}", headers=headers)
    assert proj_resp.status_code == 200
    assert proj_resp.json()["id"] == str(DEV_PROJECT_ID)
