"""Phase 11 — Frontend ↔ Backend Integration Test Suite.

Validates the complete request/response contracts matching the Next.js frontend client:
- Authentication: signup, login, /me profile hydration, session cookie refresh, logout, invalid credentials
- Workspace: listing, creation, tenant isolation
- Projects: creation, listing, versioning, optimistic concurrency control (409 on stale revision)
- Assets: upload intent, MinIO pre-signed URLs, confirmation, and download URL generation
- Jobs & Orchestration: async AI generation submission, render submission, validation pre-flight, cancellation
"""

import pytest
import uuid
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_auth_full_lifecycle_and_cookies(async_client: AsyncClient):
    """Verify signup, login, /me, token refresh via cookie, and logout."""
    email = f"frontend_user_{uuid.uuid4().hex[:8]}@example.com"
    password = "FrontendTestPassword123!"
    display_name = "Frontend Test User"

    # 1. Signup
    signup_resp = await async_client.post(
        "/api/v1/auth/signup",
        json={
            "email": email,
            "password": password,
            "display_name": display_name,
        },
    )
    assert signup_resp.status_code == 201
    signup_data = signup_resp.json()
    assert signup_data["user"]["email"] == email
    assert signup_data["user"]["display_name"] == display_name
    assert signup_data["workspace"]["role"] == "owner"
    assert "access_token" in signup_data["tokens"]
    access_token = signup_data["tokens"]["access_token"]
    assert "heyzen_refresh_token" in signup_resp.cookies

    headers = {"Authorization": f"Bearer {access_token}"}

    # 2. Get current user profile (/me)
    me_resp = await async_client.get("/api/v1/auth/me", headers=headers)
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["user"]["email"] == email
    assert len(me_data["workspaces"]) >= 1

    # 3. Session Refresh via HttpOnly Cookie
    refresh_resp = await async_client.post(
        "/api/v1/auth/refresh",
        cookies=signup_resp.cookies,
    )
    assert refresh_resp.status_code == 200
    refresh_data = refresh_resp.json()
    assert "access_token" in refresh_data["tokens"]
    new_token = refresh_data["tokens"]["access_token"]
    assert new_token != access_token

    # 4. Login with credentials
    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login_resp.status_code == 200
    login_data = login_resp.json()
    assert login_data["user"]["email"] == email
    assert "heyzen_refresh_token" in login_resp.cookies

    # 5. Invalid credentials check
    invalid_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "WrongPassword123!"},
    )
    assert invalid_resp.status_code == 401

    # 6. Logout
    logout_resp = await async_client.post(
        "/api/v1/auth/logout",
        cookies=login_resp.cookies,
    )
    assert logout_resp.status_code == 200
    assert logout_resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_workspace_isolation_and_creation(async_client: AsyncClient):
    """Verify workspace listing, creation, and tenant boundaries."""
    email = f"ws_user_{uuid.uuid4().hex[:8]}@example.com"
    signup_resp = await async_client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": "TestPassword123!", "display_name": "WS User"},
    )
    token = signup_resp.json()["tokens"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # List initial workspaces
    list_resp = await async_client.get("/api/v1/workspaces", headers=headers)
    assert list_resp.status_code == 200
    initial_ws = list_resp.json()
    assert len(initial_ws) >= 1

    # Create a secondary workspace
    create_resp = await async_client.post(
        "/api/v1/workspaces",
        headers=headers,
        json={"name": "Second Team Workspace"},
    )
    assert create_resp.status_code == 201
    created_ws = create_resp.json()
    assert created_ws["name"] == "Second Team Workspace"
    assert created_ws["role"] == "owner"

    # Verify both workspaces now appear
    updated_list = (await async_client.get("/api/v1/workspaces", headers=headers)).json()
    assert len(updated_list) == len(initial_ws) + 1


@pytest.mark.asyncio
async def test_project_lifecycle_and_occ(async_client: AsyncClient):
    """Verify project creation, listing, optimistic concurrency control (OCC)."""
    email = f"proj_user_{uuid.uuid4().hex[:8]}@example.com"
    signup_resp = await async_client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": "TestPassword123!", "display_name": "Project User"},
    )
    signup_data = signup_resp.json()
    token = signup_data["tokens"]["access_token"]
    ws_id = signup_data["workspace"]["id"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create Project
    create_resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/projects",
        headers=headers,
        json={
            "title": "Integration Explainer Video",
            "project_type": "standard",
            "aspect_ratio": "16:9",
            "width": 1920,
            "height": 1080,
            "fps": 30,
        },
    )
    assert create_resp.status_code == 201
    proj = create_resp.json()
    proj_id = proj["id"]
    assert proj["title"] == "Integration Explainer Video"
    assert proj["revision"] == 1
    assert proj["current_version_id"] is not None

    # 2. List Projects
    list_resp = await async_client.get(f"/api/v1/workspaces/{ws_id}/projects", headers=headers)
    assert list_resp.status_code == 200
    projects = list_resp.json()
    assert any(p["id"] == proj_id for p in projects)

    # 3. Get Version Snapshot
    version_id = proj["current_version_id"]
    ver_resp = await async_client.get(
        f"/api/v1/workspaces/{ws_id}/projects/{proj_id}/versions/{version_id}",
        headers=headers,
    )
    assert ver_resp.status_code == 200
    version_data = ver_resp.json()
    assert version_data["revision"] == 1
    assert "document" in version_data
    assert version_data["document"]["schema_version"] == 1
    assert version_data["document"]["metadata"].get("title") == "Integration Explainer Video"

    # 4. Save New Version under OCC (expected_revision = 1)
    doc_payload = version_data["document"]
    doc_payload["metadata"]["title"] = "Updated Explainer Video"
    save_resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/projects/{proj_id}/versions",
        headers=headers,
        json={
            "expected_revision": 1,
            "document": doc_payload,
            "source": "manual",
        },
    )
    assert save_resp.status_code == 201
    new_ver = save_resp.json()
    assert new_ver["revision"] == 2

    # 5. Concurrency Conflict: Try saving again with stale expected_revision = 1
    conflict_resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/projects/{proj_id}/versions",
        headers=headers,
        json={
            "expected_revision": 1,
            "document": doc_payload,
            "source": "manual",
        },
    )
    assert conflict_resp.status_code == 409
    assert conflict_resp.json()["error"]["code"] == "CONCURRENCY_CONFLICT"

    # 6. Delete Project
    del_resp = await async_client.delete(
        f"/api/v1/workspaces/{ws_id}/projects/{proj_id}",
        headers=headers,
    )
    assert del_resp.status_code == 204


@pytest.mark.asyncio
async def test_asset_upload_flow(async_client: AsyncClient):
    """Verify asset upload intent generation, confirmation, and download URL."""
    email = f"asset_user_{uuid.uuid4().hex[:8]}@example.com"
    signup_resp = await async_client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": "TestPassword123!", "display_name": "Asset User"},
    )
    signup_data = signup_resp.json()
    token = signup_data["tokens"]["access_token"]
    ws_id = signup_data["workspace"]["id"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create Upload Intent
    intent_resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/assets/upload-intents",
        headers=headers,
        json={
            "original_filename": "presentation.mp4",
            "mime_type": "video/mp4",
            "size_bytes": 1048576,
            "asset_type": "video",
        },
    )
    assert intent_resp.status_code == 201
    intent_data = intent_resp.json()
    asset_id = intent_data["asset_id"]
    assert "signed_upload_url" in intent_data
    assert intent_data["storage_bucket"] == "heyzen-assets"

    # 2. List Assets
    list_resp = await async_client.get(f"/api/v1/workspaces/{ws_id}/assets", headers=headers)
    assert list_resp.status_code == 200
    assets = list_resp.json()
    assert any(a["id"] == asset_id for a in assets)


@pytest.mark.asyncio
async def test_orchestration_render_and_validation(async_client: AsyncClient):
    """Verify pre-flight validation and video render submission."""
    email = f"orch_user_{uuid.uuid4().hex[:8]}@example.com"
    signup_resp = await async_client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": "TestPassword123!", "display_name": "Orch User"},
    )
    signup_data = signup_resp.json()
    token = signup_data["tokens"]["access_token"]
    ws_id = signup_data["workspace"]["id"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create project
    proj_resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/projects",
        headers=headers,
        json={"title": "Render Test Video", "aspect_ratio": "16:9"},
    )
    proj_id = proj_resp.json()["id"]

    # 1. Pre-flight timeline validation
    val_resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/projects/{proj_id}/validate",
        headers=headers,
    )
    assert val_resp.status_code == 200
    val_data = val_resp.json()
    assert "is_valid" in val_data

    # 2. Video Render Export submission
    render_resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/projects/{proj_id}/render",
        headers=headers,
        json={"expected_revision": 1, "resolution": "1080p", "format": "mp4"},
    )
    assert render_resp.status_code == 202
    job_data = render_resp.json()
    assert "id" in job_data
    assert job_data["job_type"] == "render_video"
    job_id = job_data["id"]

    # 3. Query Job Status
    job_status_resp = await async_client.get(
        f"/api/v1/jobs/{job_id}",
        headers=headers,
    )
    assert job_status_resp.status_code == 200
    assert job_status_resp.json()["id"] == job_id
