"""Integration and end-to-end tests for Real Qwen LLM VideoAgentService and async task execution."""

import os
import uuid
import pytest
from httpx import AsyncClient

from app.core.config import get_settings
from app.core.exceptions import AIProviderException, AIRuntimeUnavailableException, ConflictException
from app.db.seeds import AVATAR_ANNIE_ID
from app.models.job import Job
from app.models.project import Project, ProjectVersion
from app.schemas.orchestration import GenerateProjectRequest
from app.schemas.project_document import ProjectDocumentV1
from app.services.video_agent_service import VideoAgentService
from app.workers.tasks.ai_tasks import _execute_generate_project


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
    user_id = data["user"]["id"]
    return headers, ws_id, user_id


@pytest.mark.asyncio
async def test_video_agent_real_qwen_generation(db_session, test_user, test_workspace):
    """Test that VideoAgentService invokes RealQwenLLMProvider and creates a valid ProjectDocumentV1."""
    service = VideoAgentService(db_session)
    req = GenerateProjectRequest(
        prompt="Explain cloud storage security in two concise scenes with a professional presenter",
        target_duration_seconds=20.0,
        aspect_ratio="16:9",
        avatar_id=str(AVATAR_ANNIE_ID),
        voice_id="en_US-lessac-medium",
        video_tone="Professional",
        provider="qwen",
        device="cpu",
    )

    project, initial_version, job_id = await service.generate_project(
        workspace_id=test_workspace.id,
        user_id=test_user.id,
        request=req,
    )

    assert project.id is not None
    assert project.workspace_id == test_workspace.id
    assert project.created_by == test_user.id
    assert project.revision == 1
    assert project.status == "draft"
    assert project.width == 1920
    assert project.height == 1080
    assert project.aspect_ratio == "16:9"
    assert job_id is None

    # Validate ProjectDocumentV1
    doc = ProjectDocumentV1.model_validate(initial_version.document)
    assert doc.schema_version == 1
    assert len(doc.scenes) >= 1
    assert doc.settings.aspect_ratio == "16:9"
    assert doc.settings.total_duration > 0

    first_scene = doc.scenes[0]
    assert first_scene.avatar is not None
    assert first_scene.avatar.avatar_id == str(AVATAR_ANNIE_ID)
    assert first_scene.speech is not None
    assert first_scene.speech.voice_id == "en_US-lessac-medium"
    assert len(first_scene.speech.script) > 0

    # Verify LLM metrics attached in document metadata
    assert doc.metadata is not None
    llm_metrics = doc.metadata.get("llm_metrics", {})
    assert llm_metrics.get("provider") == "qwen"
    assert llm_metrics.get("device") == "cpu"
    assert llm_metrics.get("output_tokens", 0) > 0


@pytest.mark.asyncio
async def test_video_agent_real_mode_no_silent_fallback(db_session, test_user, test_workspace, monkeypatch):
    """Verify that in real mode, an unavailable or invalid LLM provider raises an exception and never falls back to mock."""
    monkeypatch.setattr(get_settings(), "AI_PROVIDER_MODE", "real")

    service = VideoAgentService(db_session)
    # Requesting a non-existent or invalid model/device must raise an explicit exception
    req = GenerateProjectRequest(
        prompt="This should fail immediately without falling back to mock",
        provider="nonexistent_llm",
        device="cpu",
    )

    with pytest.raises((AIProviderException, AIRuntimeUnavailableException)):
        await service.generate_project(
            workspace_id=test_workspace.id,
            user_id=test_user.id,
            request=req,
        )


@pytest.mark.asyncio
async def test_video_agent_async_job_creation_and_task_execution(async_client: AsyncClient):
    """Verify async generation flow: creates a queued Job and executes via Celery task."""
    from app.db.session import async_session_factory
    from app.schemas.job import JobSubmitRequest
    from app.services.job_service import JobService

    headers, ws_id_str, user_id_str = await _signup_and_get_workspace(async_client, "qwen_worker@example.com", "Worker Tester")
    workspace_id = uuid.UUID(ws_id_str)
    user_id = uuid.UUID(user_id_str)

    idempotency_key = f"gen-key-{uuid.uuid4()}"
    req = GenerateProjectRequest(
        prompt="A quick product announcement for a modern AI video studio",
        target_duration_seconds=15.0,
        aspect_ratio="16:9",
        run_async=True,
        idempotency_key=idempotency_key,
        provider="qwen",
        device="cpu",
    )

    async with async_session_factory() as db:
        job_service = JobService(db)
        job_req = JobSubmitRequest(
            job_type="generate_project",
            payload=req.model_dump(),
            idempotency_key=idempotency_key,
            priority=5,
        )
        job, created = await job_service.submit_job(workspace_id, user_id, job_req)
        await db.commit()
        assert created is True
        assert job is not None
        assert job.job_type == "generate_project"
        assert job.status == "queued"
        assert job.idempotency_key == idempotency_key
        job_id = job.id

        # Idempotent repeated request should return the exact same job
        job2, created2 = await job_service.submit_job(workspace_id, user_id, job_req)
        assert created2 is False
        assert job2.id == job_id

    # Execute the Celery task runner synchronously
    result = await _execute_generate_project(job_id, "celery-test-task-1")
    assert result["status"] == "succeeded"
    assert "project_id" in result
    assert result["revision"] == 1

    # Verify updated Job and Project in DB
    async with async_session_factory() as db:
        job_service = JobService(db)
        updated_job = await job_service.job_repo.get_by_id(job_id)
        assert updated_job.status == "succeeded"
        assert updated_job.progress_percent == 100

        created_project = await db.get(Project, uuid.UUID(result["project_id"]))
        assert created_project is not None
        assert created_project.revision == 1


@pytest.mark.asyncio
async def test_api_generate_project_async_and_sync(async_client: AsyncClient):
    """Test API endpoint POST /workspaces/{id}/projects/generate for both sync (201) and async (202)."""
    headers, ws_id, _ = await _signup_and_get_workspace(async_client, "qwen_api@example.com", "Qwen Tester")

    # 1. Sync generation (HTTP 201 Created with ProjectResponse)
    sync_res = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/projects/generate",
        headers=headers,
        json={
            "prompt": "Sync project generation test with Qwen ONNX",
            "aspect_ratio": "16:9",
            "run_async": False,
            "provider": "mock",  # use mock for fast API route response check
        },
    )
    assert sync_res.status_code == 201
    proj_data = sync_res.json()
    assert proj_data["id"] is not None
    assert proj_data["revision"] == 1

    # 2. Async generation (HTTP 202 Accepted with JobResponse)
    async_res = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/projects/generate",
        headers=headers,
        json={
            "prompt": "Async project generation test with Qwen ONNX",
            "aspect_ratio": "16:9",
            "run_async": True,
            "provider": "mock",
        },
    )
    assert async_res.status_code == 202
    job_data = async_res.json()
    assert job_data["id"] is not None
    assert job_data["job_type"] == "generate_project"
    assert job_data["status"] == "queued"


@pytest.mark.asyncio
async def test_video_agent_worker_cooperative_cancellation(async_client: AsyncClient):
    """Verify that a cancelled job is halted cooperatively by _execute_generate_project."""
    from app.db.session import async_session_factory
    from app.schemas.job import JobSubmitRequest
    from app.services.job_service import JobService

    headers, ws_id_str, user_id_str = await _signup_and_get_workspace(async_client, "cancel_worker@example.com", "Cancel Tester")
    workspace_id = uuid.UUID(ws_id_str)
    user_id = uuid.UUID(user_id_str)

    async with async_session_factory() as db:
        job_service = JobService(db)
        job_req = JobSubmitRequest(
            job_type="generate_project",
            payload={"prompt": "This will be cancelled", "aspect_ratio": "16:9"},
            priority=5,
        )
        job, _ = await job_service.submit_job(workspace_id, user_id, job_req)
        await job_service.cancel_job(job.id, workspace_id, "User requested stop")
        await db.commit()
        job_id = job.id

    result = await _execute_generate_project(job_id, "test-cancel-task")
    assert result["status"] == "cancelled"


@pytest.mark.asyncio
async def test_video_agent_worker_failure_handling(async_client: AsyncClient):
    """Verify that execution failure marks the Job as failed in the database."""
    from app.db.session import async_session_factory
    from app.schemas.job import JobSubmitRequest
    from app.services.job_service import JobService

    headers, ws_id_str, user_id_str = await _signup_and_get_workspace(async_client, "fail_worker@example.com", "Fail Tester")
    workspace_id = uuid.UUID(ws_id_str)
    user_id = uuid.UUID(user_id_str)

    async with async_session_factory() as db:
        job_service = JobService(db)
        job_req = JobSubmitRequest(
            job_type="generate_project",
            payload={"prompt": "Will fail", "provider": "invalid_provider_name"},
            priority=5,
        )
        job, _ = await job_service.submit_job(workspace_id, user_id, job_req)
        await db.commit()
        job_id = job.id

    with pytest.raises(Exception):
        await _execute_generate_project(job_id, "test-fail-task")

    async with async_session_factory() as db:
        job_service = JobService(db)
        failed_job = await job_service.job_repo.get_by_id(job_id)
        assert failed_job.status == "failed"
        assert failed_job.error_details is not None

