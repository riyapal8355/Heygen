"""Tests for ProjectRenderOrchestrator and render safety."""

import uuid
import pytest
from unittest.mock import patch

from app.core.exceptions import ConflictException
from app.models.project import Project, ProjectVersion
from app.schemas.orchestration import RenderProjectRequest
from app.schemas.project_document import ProjectDocumentV1, Scene, SceneSpeech
from app.services.project_render_service import ProjectRenderOrchestrator
from app.services.project_service import ProjectService
from app.workers.tasks.media_tasks import _execute_render_video


async def _create_valid_render_test_project(db_session, user_id, workspace_id, scene_duration=5.0):
    project_service = ProjectService(db_session)
    project = Project(
        workspace_id=workspace_id,
        created_by=user_id,
        title="Render Candidate Project",
        revision=1,
    )
    scenes = [
        Scene(
            id=str(uuid.uuid4()),
            sequence=1,
            duration=scene_duration,
            speech=SceneSpeech(
                voice_id="voice_mock_en_marcus",
                script="Narration script for export",
                audio_asset_id=str(uuid.uuid4()),
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
async def test_timeline_validation_flags_empty_and_zero_duration_scenes(db_session, test_user, test_workspace):
    """Verify pre-flight diagnostics detect invalid timeline states."""
    project_service = ProjectService(db_session)

    # Empty scenes
    proj_empty = Project(workspace_id=test_workspace.id, created_by=test_user.id, title="Empty", revision=1)
    ver_empty = ProjectVersion(project_id=proj_empty.id, revision=1, document=ProjectDocumentV1(schema_version=1, scenes=[]).model_dump(), created_by=test_user.id, source="initial")
    p_empty = await project_service.repo.create_project_with_initial_version(proj_empty, ver_empty)

    orchestrator = ProjectRenderOrchestrator(db_session)
    val_empty = await orchestrator.validate_timeline(p_empty.id, test_workspace.id)
    assert val_empty.is_valid is False
    assert any("at least one scene" in err for err in val_empty.errors)

    # Invalid document (raw dict with duration < 0.1)
    proj_invalid = Project(workspace_id=test_workspace.id, created_by=test_user.id, title="Invalid", revision=1)
    ver_invalid = ProjectVersion(
        project_id=proj_invalid.id,
        revision=1,
        document={"schema_version": 1, "scenes": [{"id": "s1", "sequence": 1, "duration": 0.0}]},
        created_by=test_user.id,
        source="initial",
    )
    p_invalid = await project_service.repo.create_project_with_initial_version(proj_invalid, ver_invalid)
    val_invalid = await orchestrator.validate_timeline(p_invalid.id, test_workspace.id)
    assert val_invalid.is_valid is False
    assert any("invalid" in err.lower() for err in val_invalid.errors)

    # Missing audio asset produces warning
    p_warn = await _create_valid_render_test_project(db_session, test_user.id, test_workspace.id, scene_duration=5.0)
    ver_warn = await project_service.get_version(p_warn.current_version_id, p_warn.id, test_workspace.id)
    doc_warn = dict(ver_warn.document)
    doc_warn["scenes"] = [dict(s) for s in doc_warn["scenes"]]
    doc_warn["scenes"][0]["speech"] = dict(doc_warn["scenes"][0]["speech"])
    doc_warn["scenes"][0]["speech"]["audio_asset_id"] = None
    ver_warn.document = doc_warn
    await db_session.commit()

    val_warn = await orchestrator.validate_timeline(p_warn.id, test_workspace.id)
    assert any("no pre-synthesized audio asset" in w for w in val_warn.warnings)


@pytest.mark.asyncio
async def test_render_request_requires_matching_expected_revision(db_session, test_user, test_workspace):
    """Verify render dispatch rejects stale or mismatched expected_revision with 409."""
    project = await _create_valid_render_test_project(db_session, test_user.id, test_workspace.id)

    orchestrator = ProjectRenderOrchestrator(db_session)

    # Mismatched revision (expected=2, actual=1)
    stale_req = RenderProjectRequest(expected_revision=2, resolution="1080p", fps=30)
    with pytest.raises(ConflictException) as exc_info:
        await orchestrator.request_render(project.id, test_workspace.id, test_user.id, stale_req)
    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "CONCURRENCY_CONFLICT"

    # Matching revision succeeds
    valid_req = RenderProjectRequest(expected_revision=1, resolution="1080p", fps=30)
    job, created = await orchestrator.request_render(project.id, test_workspace.id, test_user.id, valid_req)
    assert job is not None
    assert created is True
    assert job.job_type == "render_video"


async def _setup_user_workspace(async_client, name: str) -> tuple[str, uuid.UUID, uuid.UUID]:
    email = f"{name.lower().replace(' ', '_')}_{uuid.uuid4().hex[:6]}@example.com"
    resp = await async_client.post(
        "/api/v1/auth/signup",
        json={"email": email, "display_name": name, "password": "Password123!"},
    )
    assert resp.status_code == 201
    data = resp.json()
    token = data["tokens"]["access_token"]
    user_id = uuid.UUID(data["user"]["id"])
    ws_id = uuid.UUID(data["workspace"]["id"]) if "workspace" in data else None
    if not ws_id:
        ws_resp = await async_client.get("/api/v1/workspaces", headers={"Authorization": f"Bearer {token}"})
        assert ws_resp.status_code == 200
        ws_id = uuid.UUID(ws_resp.json()[0]["id"])
    return token, ws_id, user_id


@pytest.mark.asyncio
async def test_mock_render_worker_produces_valid_media_and_sets_ready(async_client):
    """Verify worker in mock mode generates structurally valid fixtures and sets Project.status='ready'."""
    from app.db.session import async_session_factory

    _, ws_id, user_id = await _setup_user_workspace(async_client, "Render Worker Mock")

    async with async_session_factory() as db:
        project = await _create_valid_render_test_project(db, user_id, ws_id)
        orchestrator = ProjectRenderOrchestrator(db)
        valid_req = RenderProjectRequest(expected_revision=1, resolution="1080p", fps=30)
        job, _ = await orchestrator.request_render(project.id, ws_id, user_id, valid_req)
        await db.commit()
        job_id = job.id
        proj_id = project.id

    # Execute worker logic
    with patch("app.workers.tasks.media_tasks.get_settings") as mock_settings:
        mock_settings.return_value.AI_PROVIDER_MODE = "mock"
        mock_settings.return_value.S3_BUCKET = "heyzen-media"
        result = await _execute_render_video(job_id, "test-task-123")

    assert result["output_asset_id"] is not None
    assert result["thumbnail_asset_id"] is not None
    assert result["duration_seconds"] > 0

    # Project promoted to ready
    async with async_session_factory() as db:
        p_svc = ProjectService(db)
        fresh_proj = await p_svc.get_project(proj_id, ws_id)
        assert fresh_proj.status == "ready"
        assert fresh_proj.thumbnail_asset_id is not None


@pytest.mark.asyncio
async def test_real_render_worker_fails_cleanly_without_fake_ready(async_client):
    """Verify render safety: when real render fails (e.g. missing ffmpeg), fails cleanly and does NOT set ready."""
    from app.db.session import async_session_factory

    _, ws_id, user_id = await _setup_user_workspace(async_client, "Render Worker Real")

    async with async_session_factory() as db:
        project = await _create_valid_render_test_project(db, user_id, ws_id)
        orchestrator = ProjectRenderOrchestrator(db)
        valid_req = RenderProjectRequest(expected_revision=1, resolution="1080p", fps=30)
        job, _ = await orchestrator.request_render(project.id, ws_id, user_id, valid_req)
        await db.commit()
        job_id = job.id
        proj_id = project.id

    # Execute worker with AI_PROVIDER_MODE="real" and uninstalled ffmpeg mock
    with patch("app.workers.tasks.media_tasks.get_settings") as mock_settings, \
         patch("app.media.ffmpeg.FFmpegService.is_available", return_value=False):
        mock_settings.return_value.AI_PROVIDER_MODE = "real"
        with pytest.raises(Exception) as exc_info:
            await _execute_render_video(job_id, "test-task-456")
        assert "FFmpeg" in str(exc_info.value) or "FFprobe" in str(exc_info.value)

    # Verify project status was NOT changed to ready
    async with async_session_factory() as db:
        p_svc = ProjectService(db)
        fresh_proj = await p_svc.get_project(proj_id, ws_id)
        assert fresh_proj.status != "ready"

