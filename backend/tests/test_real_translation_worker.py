"""Integration tests for Real Translation Celery worker execution, queue routing, progress, and lifecycle."""

import uuid
import pytest
from httpx import AsyncClient

from app.db.session import async_session_factory
from app.models.job import Job
from app.models.project import Project, ProjectVersion
from app.schemas.job import JobSubmitRequest
from app.schemas.project_document import ProjectDocumentV1, Scene, SceneSpeech
from app.services.job_service import JobService, resolve_job_queue
from app.services.project_service import ProjectService
from app.workers.celery_app import celery_app
from app.workers.tasks.ai_tasks import _execute_translate_project


async def _setup_user_and_workspace(async_client: AsyncClient) -> tuple[uuid.UUID, uuid.UUID]:
    """Create committed user and workspace via API."""
    email = f"trans_worker_{uuid.uuid4().hex[:8]}@example.com"
    resp = await async_client.post(
        "/api/v1/auth/signup",
        json={"email": email, "display_name": "Translation Worker Tester", "password": "Password123!"},
    )
    assert resp.status_code == 201
    data = resp.json()
    user_id = uuid.UUID(data["user"]["id"])
    token = data["tokens"]["access_token"]

    ws_resp = await async_client.get("/api/v1/workspaces", headers={"Authorization": f"Bearer {token}"})
    assert ws_resp.status_code == 200
    ws_id = uuid.UUID(ws_resp.json()[0]["id"])
    return user_id, ws_id


async def _create_test_project(db_session, user_id, workspace_id) -> Project:
    project_service = ProjectService(db_session)
    project = Project(
        workspace_id=workspace_id,
        created_by=user_id,
        title="Worker Translation Test",
        revision=1,
    )
    scene = Scene(
        id=str(uuid.uuid4()),
        sequence=1,
        duration=5.0,
        speech=SceneSpeech(
            voice_id="en_US-lessac-medium",
            script="Good morning and welcome to the team.",
            audio_asset_id=str(uuid.uuid4()),
        ),
    )
    doc = ProjectDocumentV1(
        schema_version=1,
        scenes=[scene],
        metadata={"title": "Worker Translation Test", "language": "en"},
    )
    version = ProjectVersion(
        project_id=project.id,
        revision=1,
        document=doc.model_dump(),
        created_by=user_id,
        source="initial",
    )
    return await project_service.repo.create_project_with_initial_version(project, version)


def test_translation_worker_queue_routing():
    """Verify translate_project workload routes to cpu_media queue for CPU execution."""
    assert resolve_job_queue("translate_project") == "cpu_media"
    assert "heyzen.tasks.ai.translate_project" in celery_app.conf.task_routes
    assert celery_app.conf.task_routes["heyzen.tasks.ai.translate_project"]["queue"] == "cpu_media"


@pytest.mark.asyncio
async def test_real_translation_worker_project_lifecycle(async_client: AsyncClient):
    """End-to-end verification that the Celery task executes real translation and commits localized project."""
    user_id, workspace_id = await _setup_user_and_workspace(async_client)

    async with async_session_factory() as db:
        orig_project = await _create_test_project(db, user_id, workspace_id)
        job_service = JobService(db)

        job = Job(
            workspace_id=workspace_id,
            created_by=user_id,
            job_type="translate_project",
            status="queued",
            priority=50,
            progress_percent=0,
            stage="queued",
            payload={
                "project_id": str(orig_project.id),
                "target_language": "es",
                "source_language": "en",
                "create_fork": True,
                "provider": "ctranslate2",
            },
        )
        job = await job_service.job_repo.create(job)
        await db.commit()
        job_id = job.id

    # Execute worker task
    result = await _execute_translate_project(job_id=job_id, task_id="test-celery-trans-1")

    assert result["source_language"] == "en"
    assert result["target_language"] == "es"
    assert result["scenes_translated"] == 1
    assert result["create_fork"] is True
    assert result["project_id"] != str(orig_project.id)

    # Verify DB job record
    async with async_session_factory() as db:
        job_service = JobService(db)
        updated_job = await job_service.job_repo.get_by_id(job_id)
        assert updated_job is not None
        assert updated_job.status == "succeeded"
        assert updated_job.progress_percent == 100
        assert updated_job.stage == "complete"

        # Verify new localized project
        proj_service = ProjectService(db)
        forked_proj = await proj_service.get_project(uuid.UUID(result["project_id"]), workspace_id)
        assert forked_proj.revision == 1
        forked_ver = await proj_service.get_version(forked_proj.current_version_id, forked_proj.id, workspace_id)
        doc = ProjectDocumentV1.model_validate(forked_ver.document)
        assert doc.metadata["language"] == "es"
        assert doc.scenes[0].speech.audio_asset_id is None
        assert doc.scenes[0].speech.voice_id == "es_ES-davefx-medium"
        assert len(doc.scenes[0].speech.script) > 0


@pytest.mark.asyncio
async def test_real_translation_worker_cancellation(async_client: AsyncClient):
    """Verify cooperative cancellation stops worker execution before translation commit."""
    user_id, workspace_id = await _setup_user_and_workspace(async_client)

    async with async_session_factory() as db:
        orig_project = await _create_test_project(db, user_id, workspace_id)
        job_service = JobService(db)

        job = Job(
            workspace_id=workspace_id,
            created_by=user_id,
            job_type="translate_project",
            status="queued",
            priority=50,
            payload={
                "project_id": str(orig_project.id),
                "target_language": "es",
                "create_fork": True,
            },
        )
        job = await job_service.job_repo.create(job)
        await db.commit()
        job_id = job.id

        # Cancel job prior to execution
        await job_service.cancel_job(job_id, workspace_id)

    result = await _execute_translate_project(job_id=job_id, task_id="test-cancel-trans")
    assert result == {"status": "cancelled"}


@pytest.mark.asyncio
async def test_real_translation_worker_failure_reporting(async_client: AsyncClient):
    """Verify structured error details are persisted when a translation task encounters failure."""
    user_id, workspace_id = await _setup_user_and_workspace(async_client)

    nonexistent_project_id = uuid.uuid4()
    async with async_session_factory() as db:
        job_service = JobService(db)
        job = Job(
            workspace_id=workspace_id,
            created_by=user_id,
            job_type="translate_project",
            status="queued",
            priority=50,
            payload={
                "project_id": str(nonexistent_project_id),
                "target_language": "es",
                "create_fork": True,
            },
        )
        job = await job_service.job_repo.create(job)
        await db.commit()
        job_id = job.id

    with pytest.raises(Exception):
        await _execute_translate_project(job_id=job_id, task_id="test-fail-trans")

    async with async_session_factory() as db:
        job_service = JobService(db)
        failed_job = await job_service.job_repo.get_by_id(job_id)
        assert failed_job.status == "failed"
        assert failed_job.error_details is not None
        assert "error" in failed_job.error_details


@pytest.mark.asyncio
async def test_real_translation_worker_idempotency(async_client: AsyncClient):
    """Verify duplicate submission with the same idempotency key returns the original Job."""
    user_id, workspace_id = await _setup_user_and_workspace(async_client)
    idempotency_key = f"trans-idem-{uuid.uuid4().hex}"

    async with async_session_factory() as db:
        orig_project = await _create_test_project(db, user_id, workspace_id)
        job_service = JobService(db)

        req = JobSubmitRequest(
            job_type="translate_project",
            payload={"project_id": str(orig_project.id), "target_language": "es"},
            idempotency_key=idempotency_key,
        )
        job1, created1 = await job_service.submit_job(workspace_id, user_id, req)
        job2, created2 = await job_service.submit_job(workspace_id, user_id, req)

        assert job1.id == job2.id
        assert created1 is True
        assert created2 is False
