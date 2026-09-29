"""Test suite for Workspace Folders, hierarchy invariants, cycle prevention, and safe deletion."""

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
async def test_create_root_and_nested_folders(async_client: AsyncClient):
    """Verify creating root folders, nested subfolders, and hierarchy listing."""
    token, ws_id = await _setup_user_workspace(async_client, "Folder Creator")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create root folder
    root_resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/folders",
        headers=headers,
        json={"name": "Marketing Videos"},
    )
    assert root_resp.status_code == 201
    root_data = root_resp.json()
    assert root_data["name"] == "Marketing Videos"
    assert root_data["parent_id"] is None
    root_id = root_data["id"]

    # 2. Create nested subfolder
    sub_resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/folders",
        headers=headers,
        json={"name": "Q3 Campaigns", "parent_id": root_id},
    )
    assert sub_resp.status_code == 201
    sub_data = sub_resp.json()
    assert sub_data["name"] == "Q3 Campaigns"
    assert sub_data["parent_id"] == root_id

    # 3. List all folders
    list_resp = await async_client.get(f"/api/v1/workspaces/{ws_id}/folders", headers=headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 2

    # 4. Filter by parent_id
    filtered_resp = await async_client.get(
        f"/api/v1/workspaces/{ws_id}/folders",
        headers=headers,
        params={"parent_id": root_id, "filter_parent": "true"},
    )
    assert filtered_resp.status_code == 200
    items = filtered_resp.json()
    assert len(items) == 1
    assert items[0]["name"] == "Q3 Campaigns"


@pytest.mark.asyncio
async def test_duplicate_sibling_folder_names_rejected(async_client: AsyncClient):
    """Verify duplicate sibling names within same parent return 409 Conflict."""
    token, ws_id = await _setup_user_workspace(async_client, "Unique Sibling")
    headers = {"Authorization": f"Bearer {token}"}

    # Create first folder
    resp1 = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/folders",
        headers=headers,
        json={"name": "Product Demos"},
    )
    assert resp1.status_code == 201

    # Attempt second folder with same name at root
    resp2 = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/folders",
        headers=headers,
        json={"name": "product demos"},  # case-insensitive match
    )
    assert resp2.status_code == 409
    assert resp2.json()["error"]["code"] == "FOLDER_NAME_EXISTS"


@pytest.mark.asyncio
async def test_cross_workspace_parent_rejected(async_client: AsyncClient):
    """Verify cannot set parent_id to a folder belonging to another workspace."""
    token_a, ws_id_a = await _setup_user_workspace(async_client, "User A")
    token_b, ws_id_b = await _setup_user_workspace(async_client, "User B")

    # User A creates folder
    folder_a = await async_client.post(
        f"/api/v1/workspaces/{ws_id_a}/folders",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"name": "User A Folder"},
    )
    assert folder_a.status_code == 201
    folder_a_id = folder_a.json()["id"]

    # User B attempts to create folder inside User A's folder
    cross_resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id_b}/folders",
        headers={"Authorization": f"Bearer {token_b}"},
        json={"name": "User B Folder", "parent_id": folder_a_id},
    )
    assert cross_resp.status_code == 404
    assert cross_resp.json()["error"]["code"] == "FOLDER_NOT_FOUND"


@pytest.mark.asyncio
async def test_update_folder_rename_and_cycle_prevention(async_client: AsyncClient):
    """Verify folder renaming and hierarchy cycle rejection."""
    token, ws_id = await _setup_user_workspace(async_client, "Cycle Tester")
    headers = {"Authorization": f"Bearer {token}"}

    # Create folder A and folder B under A
    res_a = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/folders",
        headers=headers,
        json={"name": "Folder Alpha"},
    )
    folder_a_id = res_a.json()["id"]

    res_b = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/folders",
        headers=headers,
        json={"name": "Folder Beta", "parent_id": folder_a_id},
    )
    folder_b_id = res_b.json()["id"]

    # 1. Rename folder A
    rename_resp = await async_client.patch(
        f"/api/v1/workspaces/{ws_id}/folders/{folder_a_id}",
        headers=headers,
        json={"name": "Folder Alpha Renamed"},
    )
    assert rename_resp.status_code == 200
    assert rename_resp.json()["name"] == "Folder Alpha Renamed"

    # 2. Attempt self-parent cycle
    self_cycle = await async_client.patch(
        f"/api/v1/workspaces/{ws_id}/folders/{folder_a_id}",
        headers=headers,
        json={"parent_id": folder_a_id},
    )
    assert self_cycle.status_code == 409
    assert self_cycle.json()["error"]["code"] == "FOLDER_CYCLE_DETECTED"

    # 3. Attempt descendant-parent cycle (move A under B when B is already under A)
    desc_cycle = await async_client.patch(
        f"/api/v1/workspaces/{ws_id}/folders/{folder_a_id}",
        headers=headers,
        json={"parent_id": folder_b_id},
    )
    assert desc_cycle.status_code == 409
    assert desc_cycle.json()["error"]["code"] == "FOLDER_CYCLE_DETECTED"


@pytest.mark.asyncio
async def test_non_empty_folder_deletion_rejected(async_client: AsyncClient):
    """Verify non-empty folders cannot be deleted until emptied."""
    token, ws_id = await _setup_user_workspace(async_client, "Delete Tester")
    headers = {"Authorization": f"Bearer {token}"}

    # Create Parent and Child folders
    res_p = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/folders",
        headers=headers,
        json={"name": "Parent Folder"},
    )
    parent_id = res_p.json()["id"]

    res_c = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/folders",
        headers=headers,
        json={"name": "Child Folder", "parent_id": parent_id},
    )
    child_id = res_c.json()["id"]

    # Deleting parent fails with 409
    del_parent_fail = await async_client.delete(
        f"/api/v1/workspaces/{ws_id}/folders/{parent_id}",
        headers=headers,
    )
    assert del_parent_fail.status_code == 409
    assert del_parent_fail.json()["error"]["code"] == "FOLDER_NOT_EMPTY"

    # Delete child succeeds
    del_child = await async_client.delete(
        f"/api/v1/workspaces/{ws_id}/folders/{child_id}",
        headers=headers,
    )
    assert del_child.status_code == 204

    # Now deleting parent succeeds
    del_parent_ok = await async_client.delete(
        f"/api/v1/workspaces/{ws_id}/folders/{parent_id}",
        headers=headers,
    )
    assert del_parent_ok.status_code == 204

    # Deleted parent excluded from list
    list_resp = await async_client.get(f"/api/v1/workspaces/{ws_id}/folders", headers=headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 0
