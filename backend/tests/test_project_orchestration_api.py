"""Integration and authorization tests for Project Orchestration API endpoints."""

import uuid
import pytest
from httpx import AsyncClient

from app.models.project import Project, ProjectVersion
from app.schemas.project_document import ProjectDocumentV1, Scene, SceneSpeech
from app.services.project_service import ProjectService


async def _signup_and_get_workspace(async_client: AsyncClient, email: str, name: str):
    unique_email = f"{email.split('@')[0]}_{uuid.uuid4().hex[:8]}@example.com"
    res = await async_client.post(
        "/api/v1/auth/signup",
        json={"email": unique_email, "password": "Password123!", "display_name": name},
    )
    assert res.status_code == 201, f"Signup failed: {res.text}"
    data = res.json()
    token = data["tokens"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    ws_id = data["workspace"]["id"]
    return headers, ws_id


async def _create_test_project_via_api(async_client: AsyncClient, headers: dict, ws_id: str):
    res = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/projects/generate",
        headers=headers,
        json={
            "prompt": "API Integration Test Demo Video",
            "target_duration_seconds": 20.0,
            "aspect_ratio": "16:9",
        },
    )
    assert res.status_code == 201
    return res.json()


@pytest.mark.asyncio
async def test_api_generate_project_from_prompt(async_client: AsyncClient):
    """Verify POST /projects/generate creates initialized project with 201 Created."""
    headers, ws_id = await _signup_and_get_workspace(async_client, "agent_api@example.com", "Agent Tester")

    res = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/projects/generate",
        headers=headers,
        json={
            "prompt": "Create an introductory product video for HeyZen",
            "aspect_ratio": "16:9",
            "video_tone": "Professional",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["id"] is not None
    assert data["revision"] == 1
    assert data["status"] == "draft"


@pytest.mark.asyncio
async def test_api_synthesize_speech_async_and_sync(async_client: AsyncClient):
    """Verify POST /projects/{id}/synthesize-speech returns 202 async JobResponse and 200 sync."""
    headers, ws_id = await _signup_and_get_workspace(async_client, "speech_api@example.com", "Speech Tester")
    project = await _create_test_project_via_api(async_client, headers, ws_id)
    proj_id = project["id"]

    # 1. Async mode (canonical API behavior: 202 Accepted)
    async_res = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/projects/{proj_id}/synthesize-speech",
        headers=headers,
        json={
            "expected_revision": 1,
            "run_async": True,
        },
    )
    assert async_res.status_code == 202
    job_data = async_res.json()
    assert job_data["job_type"] == "project_batch_speech"
    assert job_data["status"] == "queued"

    # 2. Sync mode (internal/test behavior: 200 OK)
    sync_res = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/projects/{proj_id}/synthesize-speech",
        headers=headers,
        json={
            "expected_revision": 1,
            "run_async": False,
        },
    )
    assert sync_res.status_code == 200
    ver_data = sync_res.json()
    assert ver_data["revision"] == 2


@pytest.mark.asyncio
async def test_api_validate_timeline(async_client: AsyncClient):
    """Verify POST /projects/{id}/validate returns 200 with diagnostics."""
    headers, ws_id = await _signup_and_get_workspace(async_client, "validate_api@example.com", "Validate Tester")
    project = await _create_test_project_via_api(async_client, headers, ws_id)
    proj_id = project["id"]

    res = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/projects/{proj_id}/validate",
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert "is_valid" in data
    assert data["scene_count"] >= 1
    assert data["total_duration"] > 0


@pytest.mark.asyncio
async def test_api_render_project_requires_expected_revision(async_client: AsyncClient):
    """Verify POST /projects/{id}/render requires expected_revision and returns 202."""
    headers, ws_id = await _signup_and_get_workspace(async_client, "render_api@example.com", "Render Tester")
    project = await _create_test_project_via_api(async_client, headers, ws_id)
    proj_id = project["id"]

    # Missing expected_revision -> 422 Unprocessable Entity
    missing_rev = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/projects/{proj_id}/render",
        headers=headers,
        json={"resolution": "1080p"},
    )
    assert missing_rev.status_code in (422, 400)

    # Stale expected_revision -> 409 Conflict
    stale_rev = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/projects/{proj_id}/render",
        headers=headers,
        json={"expected_revision": 99, "resolution": "1080p"},
    )
    assert stale_rev.status_code == 409

    # Valid matching expected_revision -> 202 Accepted
    res = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/projects/{proj_id}/render",
        headers=headers,
        json={"expected_revision": 1, "resolution": "1080p"},
    )
    assert res.status_code == 202
    data = res.json()
    assert data["job_type"] == "render_video"
    assert data["status"] == "queued"


@pytest.mark.asyncio
async def test_api_translate_project(async_client: AsyncClient):
    """Verify POST /projects/{id}/translate supports forking and async dispatch."""
    headers, ws_id = await _signup_and_get_workspace(async_client, "trans_api@example.com", "Trans Tester")
    project = await _create_test_project_via_api(async_client, headers, ws_id)
    proj_id = project["id"]

    # Async translation dispatch
    res = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/projects/{proj_id}/translate",
        headers=headers,
        json={"target_language": "de", "run_async": True},
    )
    assert res.status_code == 202
    assert res.json()["job_type"] == "translate_project"


@pytest.mark.asyncio
async def test_api_generate_scene_visual(async_client: AsyncClient):
    """Verify POST /projects/{id}/scenes/{scene_id}/generate-visual updates timeline."""
    headers, ws_id = await _signup_and_get_workspace(async_client, "vis_api@example.com", "Visual Tester")
    project = await _create_test_project_via_api(async_client, headers, ws_id)
    proj_id = project["id"]

    # Fetch version to get scene_id
    ver_res = await async_client.get(
        f"/api/v1/workspaces/{ws_id}/projects/{proj_id}/versions/{project['current_version_id']}",
        headers=headers,
    )
    scene_id = ver_res.json()["document"]["scenes"][0]["id"]

    res = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/projects/{proj_id}/scenes/{scene_id}/generate-visual",
        headers=headers,
        json={
            "visual_type": "image",
            "prompt": "Cyberpunk city neon lighting background",
            "expected_revision": 1,
            "run_async": False,
        },
    )
    assert res.status_code == 200
    assert res.json()["revision"] == 2


@pytest.mark.asyncio
async def test_api_cross_workspace_isolation(async_client: AsyncClient):
    """Verify accessing a project from another workspace returns 404."""
    headers_a, ws_a = await _signup_and_get_workspace(async_client, "user_a@example.com", "User A")
    headers_b, ws_b = await _signup_and_get_workspace(async_client, "user_b@example.com", "User B")

    project_a = await _create_test_project_via_api(async_client, headers_a, ws_a)
    proj_a_id = project_a["id"]

    # User B attempts to access User A's project under Workspace B path
    res = await async_client.post(
        f"/api/v1/workspaces/{ws_b}/projects/{proj_a_id}/validate",
        headers=headers_b,
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_api_enhance_speech(async_client: AsyncClient):
    """Verify POST /projects/{id}/enhance-speech supports both async Celery job (202) and sync execution (200)."""
    headers, ws_id = await _signup_and_get_workspace(async_client, "enhance_api@example.com", "Enhance Tester")
    project = await _create_test_project_via_api(async_client, headers, ws_id)
    proj_id = project["id"]

    # 1. Synthesize initial speech synchronously
    synth_res = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/projects/{proj_id}/synthesize-speech",
        headers=headers,
        json={"expected_revision": 1, "run_async": False},
    )
    assert synth_res.status_code == 200
    assert synth_res.json()["revision"] == 2

    # 2. Async dispatch (HTTP 202)
    async_res = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/projects/{proj_id}/enhance-speech",
        headers=headers,
        json={
            "expected_revision": 2,
            "denoise": True,
            "remove_silence": False,
            "master_audio": True,
            "run_async": True,
        },
    )
    assert async_res.status_code == 202
    assert async_res.json()["job_type"] == "enhance_project_speech"

    # 3. Synchronous execution (HTTP 200)
    sync_res = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/projects/{proj_id}/enhance-speech",
        headers=headers,
        json={
            "expected_revision": 2,
            "denoise": True,
            "remove_silence": False,
            "master_audio": True,
            "provider": "mock",
            "run_async": False,
        },
    )
    assert sync_res.status_code == 200
    assert sync_res.json()["revision"] == 3

