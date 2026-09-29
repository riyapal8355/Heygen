"""Test suite for Job state machine, idempotency, event auditing, RBAC, and SSE endpoints."""

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
async def test_submit_job_success(async_client: AsyncClient):
    """Verify job submission returns 201 Created and initializes queued state."""
    token, ws_id = await _setup_user_workspace(async_client, "Job Submitter")
    headers = {"Authorization": f"Bearer {token}", "X-Workspace-ID": ws_id}

    resp = await async_client.post(
        "/api/v1/jobs",
        headers=headers,
        json={
            "job_type": "render_video",
            "priority": 25,
            "payload": {"project_id": str(uuid.uuid4()), "resolution": "1080p"},
        },
    )
    assert resp.status_code == 201
    job = resp.json()
    assert job["job_type"] == "render_video"
    assert job["status"] == "queued"
    assert job["progress_percent"] == 0
    assert job["priority"] == 25
    assert job["stage"] == "queued"
    assert "project_id" in job["payload"]


@pytest.mark.asyncio
async def test_job_idempotency_behavior(async_client: AsyncClient):
    """Verify idempotency key deduplicates within workspace but allows separate workspaces."""
    token_a, ws_a = await _setup_user_workspace(async_client, "User A")
    token_b, ws_b = await _setup_user_workspace(async_client, "User B")
    headers_a = {"Authorization": f"Bearer {token_a}", "X-Workspace-ID": ws_a}
    headers_b = {"Authorization": f"Bearer {token_b}", "X-Workspace-ID": ws_b}

    idempotency_key = f"idem-key-{uuid.uuid4().hex[:8]}"

    # First submission in Workspace A -> 201 Created
    resp1 = await async_client.post(
        "/api/v1/jobs",
        headers=headers_a,
        json={
            "job_type": "tts_synthesis",
            "idempotency_key": idempotency_key,
            "payload": {"text": "Idempotent TTS speech"},
        },
    )
    assert resp1.status_code == 201
    job_a_id = resp1.json()["id"]

    # Duplicate submission in Workspace A with same key -> 200 OK, returns same job
    resp2 = await async_client.post(
        "/api/v1/jobs",
        headers=headers_a,
        json={
            "job_type": "tts_synthesis",
            "idempotency_key": idempotency_key,
            "payload": {"text": "Different payload text ignored"},
        },
    )
    assert resp2.status_code == 200
    assert resp2.json()["id"] == job_a_id

    # Submission in Workspace B with same key -> 201 Created, distinct job
    resp3 = await async_client.post(
        "/api/v1/jobs",
        headers=headers_b,
        json={
            "job_type": "tts_synthesis",
            "idempotency_key": idempotency_key,
            "payload": {"text": "Workspace B text"},
        },
    )
    assert resp3.status_code == 201
    assert resp3.json()["id"] != job_a_id


@pytest.mark.asyncio
async def test_submit_invalid_job_type_rejected(async_client: AsyncClient):
    """Verify unrecognized job types are rejected with 400 Bad Request."""
    token, ws_id = await _setup_user_workspace(async_client, "Invalid Type")
    headers = {"Authorization": f"Bearer {token}", "X-Workspace-ID": ws_id}

    resp = await async_client.post(
        "/api/v1/jobs",
        headers=headers,
        json={"job_type": "quantum_teleportation", "payload": {}},
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "INVALID_JOB_TYPE"


@pytest.mark.asyncio
async def test_list_and_filter_jobs(async_client: AsyncClient):
    """Verify listing jobs with filtering by workload type."""
    token, ws_id = await _setup_user_workspace(async_client, "Job Lister")
    headers = {"Authorization": f"Bearer {token}", "X-Workspace-ID": ws_id}

    # Create one render_video and one lip_sync
    await async_client.post(
        "/api/v1/jobs",
        headers=headers,
        json={"job_type": "render_video", "payload": {}},
    )
    await async_client.post(
        "/api/v1/jobs",
        headers=headers,
        json={"job_type": "lip_sync", "payload": {}},
    )

    # List all
    all_resp = await async_client.get("/api/v1/jobs", headers=headers)
    assert all_resp.status_code == 200
    assert len(all_resp.json()) >= 2

    # Filter by lip_sync
    lip_resp = await async_client.get("/api/v1/jobs?job_type=lip_sync", headers=headers)
    assert lip_resp.status_code == 200
    items = lip_resp.json()
    assert all(j["job_type"] == "lip_sync" for j in items)


@pytest.mark.asyncio
async def test_get_job_and_audit_events(async_client: AsyncClient):
    """Verify fetching single job and its immutable audit event log."""
    token, ws_id = await _setup_user_workspace(async_client, "Event Viewer")
    headers = {"Authorization": f"Bearer {token}", "X-Workspace-ID": ws_id}

    create_resp = await async_client.post(
        "/api/v1/jobs",
        headers=headers,
        json={"job_type": "translate_project", "payload": {"target_lang": "fr"}},
    )
    assert create_resp.status_code == 201
    job_id = create_resp.json()["id"]

    # Get job
    get_resp = await async_client.get(f"/api/v1/jobs/{job_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == job_id

    # Get events
    events_resp = await async_client.get(f"/api/v1/jobs/{job_id}/events", headers=headers)
    assert events_resp.status_code == 200
    events = events_resp.json()
    assert len(events) >= 1
    assert events[0]["to_status"] == "queued"
    assert events[0]["event_type"] == "state_change"


@pytest.mark.asyncio
async def test_cancel_job_lifecycle(async_client: AsyncClient):
    """Verify cancellation transition and prevention of cancelling terminal jobs."""
    token, ws_id = await _setup_user_workspace(async_client, "Canceller")
    headers = {"Authorization": f"Bearer {token}", "X-Workspace-ID": ws_id}

    create_resp = await async_client.post(
        "/api/v1/jobs",
        headers=headers,
        json={"job_type": "render_video", "payload": {}},
    )
    job_id = create_resp.json()["id"]

    # Cancel active job
    cancel_resp = await async_client.post(
        f"/api/v1/jobs/{job_id}/cancel?reason=Testing+Cancellation",
        headers=headers,
    )
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "cancelled"

    # Confirm status is cancelled
    get_resp = await async_client.get(f"/api/v1/jobs/{job_id}", headers=headers)
    assert get_resp.json()["status"] == "cancelled"

    # Cancel again -> 409 Conflict
    conflict_resp = await async_client.post(f"/api/v1/jobs/{job_id}/cancel", headers=headers)
    assert conflict_resp.status_code == 409


@pytest.mark.asyncio
async def test_cross_workspace_job_isolation(async_client: AsyncClient):
    """Verify users from other workspaces cannot read or cancel jobs."""
    token_a, ws_a = await _setup_user_workspace(async_client, "Tenant A")
    token_b, ws_b = await _setup_user_workspace(async_client, "Tenant B")
    headers_a = {"Authorization": f"Bearer {token_a}", "X-Workspace-ID": ws_a}
    headers_b = {"Authorization": f"Bearer {token_b}", "X-Workspace-ID": ws_b}

    create_resp = await async_client.post(
        "/api/v1/jobs",
        headers=headers_a,
        json={"job_type": "voice_clone", "payload": {}},
    )
    job_id = create_resp.json()["id"]

    # Tenant B attempts to read Job A -> 404 Not Found
    get_resp = await async_client.get(f"/api/v1/jobs/{job_id}", headers=headers_b)
    assert get_resp.status_code == 404

    # Tenant B attempts to cancel Job A -> 404 Not Found
    cancel_resp = await async_client.post(f"/api/v1/jobs/{job_id}/cancel", headers=headers_b)
    assert cancel_resp.status_code == 404


@pytest.mark.asyncio
async def test_stream_job_events_sse_initial_chunk(async_client: AsyncClient):
    """Verify Server-Sent Events endpoint yields initial status chunk and proper headers."""
    token, ws_id = await _setup_user_workspace(async_client, "Stream Client")
    headers = {"Authorization": f"Bearer {token}", "X-Workspace-ID": ws_id}

    create_resp = await async_client.post(
        "/api/v1/jobs",
        headers=headers,
        json={"job_type": "avatar_train", "payload": {}},
    )
    job_id = create_resp.json()["id"]

    # Cancel job so stream immediately closes after initial state
    await async_client.post(f"/api/v1/jobs/{job_id}/cancel", headers=headers)

    # Stream
    stream_resp = await async_client.get(f"/api/v1/jobs/{job_id}/stream", headers=headers)
    assert stream_resp.status_code == 200
    assert "text/event-stream" in stream_resp.headers["content-type"]
    body = stream_resp.text
    assert "data:" in body
    assert "cancelled" in body
