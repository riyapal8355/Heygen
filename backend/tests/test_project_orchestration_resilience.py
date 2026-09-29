"""Resilience, concurrency, idempotency, cancellation, and rollback tests."""

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.exceptions import ConflictException
from app.models.job import Job
from app.models.project import Project, ProjectVersion
from app.schemas.orchestration import RenderProjectRequest, SynthesizeProjectSpeechRequest
from app.schemas.project_document import ProjectDocumentV1, Scene, SceneSpeech
from app.services.asset_lifecycle import AssetLifecycleManager
from app.services.job_service import JobService
from app.services.project_render_service import ProjectRenderOrchestrator
from app.services.project_service import ProjectService
from app.services.project_speech_service import ProjectSpeechOrchestrator


async def _create_test_project_for_resilience(db_session, user_id, workspace_id):
    project_service = ProjectService(db_session)
    project = Project(
        workspace_id=workspace_id,
        created_by=user_id,
        title="Resilience Test Project",
        revision=1,
    )
    scenes = [
        Scene(
            id=str(uuid.uuid4()),
            sequence=1,
            duration=5.0,
            speech=SceneSpeech(
                voice_id="voice_mock_en_marcus",
                script="Testing resilience and failure domains.",
            ),
        )
    ]
    doc = ProjectDocumentV1(
        schema_version=1,
        scenes=scenes,
    )
    version = ProjectVersion(
        project_id=project.id,
        revision=1,
        document=doc.model_dump(),
        created_by=user_id,
        source="initial",
    )
    return await project_service.repo.create_project_with_initial_version(project, version)


@pytest.mark.asyncio
async def test_idempotent_repeated_orchestration_requests(db_session, test_user, test_workspace):
    """Verify repeated requests with same idempotency key return existing job without duplication."""
    project = await _create_test_project_for_resilience(db_session, test_user.id, test_workspace.id)

    orchestrator = ProjectRenderOrchestrator(db_session)
    idempotency_key = f"render-key-{uuid.uuid4()}"
    req = RenderProjectRequest(expected_revision=1, resolution="1080p", idempotency_key=idempotency_key)

    job_1, created_1 = await orchestrator.request_render(project.id, test_workspace.id, test_user.id, req)
    assert created_1 is True

    # Repeated request with same idempotency key
    job_2, created_2 = await orchestrator.request_render(project.id, test_workspace.id, test_user.id, req)
    assert created_2 is False
    assert job_2.id == job_1.id


@pytest.mark.asyncio
async def test_optimistic_concurrency_conflict_rejection(db_session, test_user, test_workspace):
    """Verify stale expected_revision raises ConcurrencyConflictError (HTTP 409)."""
    project = await _create_test_project_for_resilience(db_session, test_user.id, test_workspace.id)

    orchestrator = ProjectSpeechOrchestrator(db_session)

    # First update advances revision to 2
    v2 = await orchestrator.synthesize_project_speech(
        project_id=project.id,
        workspace_id=test_workspace.id,
        user_id=test_user.id,
        expected_revision=1,
    )
    assert v2.revision == 2

    # Second update attempting against stale expected_revision=1 must fail with 409
    with pytest.raises(ConflictException) as exc_info:
        await orchestrator.synthesize_project_speech(
            project_id=project.id,
            workspace_id=test_workspace.id,
            user_id=test_user.id,
            expected_revision=1,
        )
    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "CONCURRENCY_CONFLICT"


@pytest.mark.asyncio
async def test_cooperative_cancellation_halts_task(async_client):
    """Verify cancelling a job transitions it to CANCELLED and halts execution."""
    from app.db.session import async_session_factory
    from app.workers.tasks.media_tasks import _execute_render_video

    email = f"cancel_test_{uuid.uuid4().hex[:6]}@example.com"
    resp = await async_client.post(
        "/api/v1/auth/signup",
        json={"email": email, "display_name": "Cancel Test", "password": "Password123!"},
    )
    assert resp.status_code == 201
    data = resp.json()
    token = data["tokens"]["access_token"]
    user_id = uuid.UUID(data["user"]["id"])
    ws_resp = await async_client.get("/api/v1/workspaces", headers={"Authorization": f"Bearer {token}"})
    assert ws_resp.status_code == 200
    ws_id = uuid.UUID(ws_resp.json()[0]["id"])

    async with async_session_factory() as db:
        job_service = JobService(db)
        job = Job(
            workspace_id=ws_id,
            created_by=user_id,
            job_type="render_video",
            status="queued",
            payload={"total_duration": 5.0},
        )
        await job_service.job_repo.create(job)
        await db.commit()
        job_id = job.id

        # Cancel the job before or during execution
        await job_service.cancel_job(job_id, ws_id)
        await db.commit()

        # Re-fetch and check
        fresh_job = await job_service.job_repo.get_by_id(job_id)
        assert fresh_job.status == "cancelled"

    # Worker execution stops early
    res = await _execute_render_video(job_id, "cancelled-task")
    assert res["status"] == "cancelled"


@pytest.mark.asyncio
async def test_partial_storage_db_rollback(db_session, test_user, test_workspace):
    """Verify orphaned MinIO object is deleted if DB commit fails after upload."""
    mock_storage = MagicMock()
    mock_storage.bucket_name = "heyzen-media"
    mock_storage.upload_bytes = AsyncMock()
    mock_storage.delete_object = MagicMock()

    asset_mgr = AssetLifecycleManager(db_session, storage=mock_storage)

    # Force database failure during asset creation by patching asset_repo.create
    with patch.object(asset_mgr.asset_repo, "create", side_effect=RuntimeError("DB disk full error")):
        with pytest.raises(RuntimeError):
            await asset_mgr.ingest_generated_asset(
                workspace_id=test_workspace.id,
                created_by=test_user.id,
                content=b"simulated audio bytes",
                original_filename="fail_test.wav",
                asset_type="audio",
                mime_type="audio/wav",
            )

    # Verify upload was attempted and cleanup delete was triggered
    mock_storage.upload_bytes.assert_called_once()
    mock_storage.delete_object.assert_called_once()
