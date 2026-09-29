"""Test suite for Project creation, querying, updating, and workspace scoping."""

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
async def test_create_project_initializes_revision_and_document(async_client: AsyncClient):
    """Verify creating a project automatically provisions revision 1 ProjectDocumentV1."""
    token, ws_id = await _setup_user_workspace(async_client, "Project Creator")
    headers = {"Authorization": f"Bearer {token}"}

    create_resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/projects",
        headers=headers,
        json={
            "title": "Summer Campaign",
            "aspect_ratio": "16:9",
            "project_type": "standard",
        },
    )
    assert create_resp.status_code == 201
    project = create_resp.json()
    assert project["title"] == "Summer Campaign"
    assert project["revision"] == 1
    assert project["status"] == "draft"
    assert project["current_version_id"] is not None

    # Verify initial version snapshot
    version_resp = await async_client.get(
        f"/api/v1/workspaces/{ws_id}/projects/{project['id']}/versions/{project['current_version_id']}",
        headers=headers,
    )
    assert version_resp.status_code == 200
    v_data = version_resp.json()
    assert v_data["revision"] == 1
    assert v_data["source"] == "initial"
    assert v_data["document"]["schema_version"] == 1
    assert len(v_data["document"]["scenes"]) == 1


@pytest.mark.asyncio
async def test_list_and_filter_projects(async_client: AsyncClient):
    """Verify listing projects filtered by folder, status, and search."""
    token, ws_id = await _setup_user_workspace(async_client, "Filter Tester")
    headers = {"Authorization": f"Bearer {token}"}

    # Create a folder
    f_resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/folders",
        headers=headers,
        json={"name": "Social Clips"},
    )
    folder_id = f_resp.json()["id"]

    # Create project 1 (in folder)
    await async_client.post(
        f"/api/v1/workspaces/{ws_id}/projects",
        headers=headers,
        json={"title": "Instagram Story 1", "folder_id": folder_id},
    )

    # Create project 2 (at root)
    await async_client.post(
        f"/api/v1/workspaces/{ws_id}/projects",
        headers=headers,
        json={"title": "YouTube Longform 1"},
    )

    # 1. List all projects
    all_resp = await async_client.get(f"/api/v1/workspaces/{ws_id}/projects", headers=headers)
    assert all_resp.status_code == 200
    assert len(all_resp.json()) == 2

    # 2. Filter by folder
    f_filter_resp = await async_client.get(
        f"/api/v1/workspaces/{ws_id}/projects",
        headers=headers,
        params={"folder_id": folder_id, "filter_folder": "true"},
    )
    assert f_filter_resp.status_code == 200
    assert len(f_filter_resp.json()) == 1
    assert f_filter_resp.json()[0]["title"] == "Instagram Story 1"

    # 3. Filter by search keyword
    search_resp = await async_client.get(
        f"/api/v1/workspaces/{ws_id}/projects",
        headers=headers,
        params={"search": "YouTube"},
    )
    assert search_resp.status_code == 200
    assert len(search_resp.json()) == 1
    assert search_resp.json()[0]["title"] == "YouTube Longform 1"


@pytest.mark.asyncio
async def test_cross_workspace_folder_rejected(async_client: AsyncClient):
    """Verify project cannot be assigned to a folder from another workspace."""
    token_a, ws_id_a = await _setup_user_workspace(async_client, "Alice Projects")
    token_b, ws_id_b = await _setup_user_workspace(async_client, "Bob Projects")

    # Alice creates folder
    f_resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id_a}/folders",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"name": "Alice Private Folder"},
    )
    alice_folder_id = f_resp.json()["id"]

    # Bob attempts to create project using Alice's folder
    cross_resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id_b}/projects",
        headers={"Authorization": f"Bearer {token_b}"},
        json={"title": "Bob Infiltrates", "folder_id": alice_folder_id},
    )
    assert cross_resp.status_code == 404
    assert cross_resp.json()["error"]["code"] == "FOLDER_NOT_FOUND"


@pytest.mark.asyncio
async def test_soft_delete_project(async_client: AsyncClient):
    """Verify soft-deleted project is excluded from queries."""
    token, ws_id = await _setup_user_workspace(async_client, "Project Deleter")
    headers = {"Authorization": f"Bearer {token}"}

    create_resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/projects",
        headers=headers,
        json={"title": "Doomed Project"},
    )
    project_id = create_resp.json()["id"]

    del_resp = await async_client.delete(
        f"/api/v1/workspaces/{ws_id}/projects/{project_id}",
        headers=headers,
    )
    assert del_resp.status_code == 204

    # List excludes deleted
    list_resp = await async_client.get(f"/api/v1/workspaces/{ws_id}/projects", headers=headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 0

    # Get returns 404
    get_resp = await async_client.get(f"/api/v1/workspaces/{ws_id}/projects/{project_id}", headers=headers)
    assert get_resp.status_code == 404
