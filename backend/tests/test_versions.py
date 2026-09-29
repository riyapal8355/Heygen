"""Test suite for Project Versions, immutable history, and optimistic concurrency."""

import uuid
import pytest
from httpx import AsyncClient

from app.schemas.project_document import create_default_project_document


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
async def test_optimistic_concurrency_workflow(async_client: AsyncClient):
    """Verify version advance with expected_revision and 409 on stale revision."""
    token, ws_id = await _setup_user_workspace(async_client, "Concurrency User")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create project (starts at revision 1)
    p_resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/projects",
        headers=headers,
        json={"title": "Interactive Storyboard"},
    )
    project_id = p_resp.json()["id"]
    assert p_resp.json()["revision"] == 1

    # 2. User A prepares updated document based on revision 1
    doc_v2 = create_default_project_document(initial_title="Updated Storyboard V2")
    doc_v2.settings.total_duration = 15.0

    save_v2_resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/projects/{project_id}/versions",
        headers=headers,
        json={
            "expected_revision": 1,
            "document": doc_v2.model_dump(),
            "source": "manual",
        },
    )
    assert save_v2_resp.status_code == 201
    v2_data = save_v2_resp.json()
    assert v2_data["revision"] == 2
    assert v2_data["document"]["settings"]["total_duration"] == 15.0

    # Project revision is now 2
    proj_check = await async_client.get(
        f"/api/v1/workspaces/{ws_id}/projects/{project_id}",
        headers=headers,
    )
    assert proj_check.json()["revision"] == 2
    assert proj_check.json()["duration_ms"] == 15000

    # 3. User B attempts save with stale expected_revision=1
    stale_doc = create_default_project_document(initial_title="Stale Overwrite Attempt")
    stale_resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/projects/{project_id}/versions",
        headers=headers,
        json={
            "expected_revision": 1,
            "document": stale_doc.model_dump(),
            "source": "autosave",
        },
    )
    assert stale_resp.status_code == 409
    assert stale_resp.json()["error"]["code"] == "CONCURRENCY_CONFLICT"

    # 4. User B syncs and saves with expected_revision=2 -> succeeds at revision 3
    save_v3_resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/projects/{project_id}/versions",
        headers=headers,
        json={
            "expected_revision": 2,
            "document": stale_doc.model_dump(),
            "source": "manual",
        },
    )
    assert save_v3_resp.status_code == 201
    assert save_v3_resp.json()["revision"] == 3


@pytest.mark.asyncio
async def test_version_history_listing_and_immutability(async_client: AsyncClient):
    """Verify multiple versions are recorded immutably and returned in descending order."""
    token, ws_id = await _setup_user_workspace(async_client, "History User")
    headers = {"Authorization": f"Bearer {token}"}

    # Create project
    p_resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/projects",
        headers=headers,
        json={"title": "History Project"},
    )
    project_id = p_resp.json()["id"]

    # Save revision 2
    doc2 = create_default_project_document(initial_title="Rev 2 Title")
    await async_client.post(
        f"/api/v1/workspaces/{ws_id}/projects/{project_id}/versions",
        headers=headers,
        json={"expected_revision": 1, "document": doc2.model_dump()},
    )

    # Save revision 3
    doc3 = create_default_project_document(initial_title="Rev 3 Title")
    await async_client.post(
        f"/api/v1/workspaces/{ws_id}/projects/{project_id}/versions",
        headers=headers,
        json={"expected_revision": 2, "document": doc3.model_dump()},
    )

    # List versions
    list_resp = await async_client.get(
        f"/api/v1/workspaces/{ws_id}/projects/{project_id}/versions",
        headers=headers,
    )
    assert list_resp.status_code == 200
    versions = list_resp.json()
    assert len(versions) == 3
    assert [v["revision"] for v in versions] == [3, 2, 1]
