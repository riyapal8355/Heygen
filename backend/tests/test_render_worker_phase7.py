"""Phase 7 Real Media Rendering Engine Acceptance Test Suite.

Verifies the full authoritative Phase 7 acceptance pipeline:
ProjectDocumentV1
  → real FFmpeg
  → actual scene composition
  → actual MP4
  → real ffprobe validation
  → AssetLifecycleManager
  → MinIO
  → successful render Job
  → Project.status = ready.
"""

import uuid
from pathlib import Path
from unittest.mock import patch
import pytest

from app.db.session import async_session_factory
from app.models.project import Project, ProjectVersion
from app.schemas.orchestration import RenderProjectRequest
from app.schemas.project_document import (
    ProjectDocumentV1,
    ProjectSettings,
    Scene,
    SceneSpeech,
)
from app.services.job_service import JobService
from app.services.project_render_service import ProjectRenderOrchestrator
from app.services.project_service import ProjectService
from app.storage.s3 import get_storage_provider
from app.workers.tasks.media_tasks import _execute_render_video


async def _setup_workspace_and_project(async_client, title="Phase 7 Test Project", width=1280, height=720, aspect_ratio="16:9"):
    """Create test user, workspace, and a multi-scene ProjectDocumentV1."""
    # 1. Register user via /api/v1/auth/signup
    email = f"phase7_{uuid.uuid4().hex[:8]}@example.com"
    pwd = "Password123!"
    reg_resp = await async_client.post(
        "/api/v1/auth/signup",
        json={"email": email, "display_name": "Phase 7 Tester", "password": pwd},
    )
    assert reg_resp.status_code == 201, f"Signup failed: {reg_resp.text}"
    data = reg_resp.json()
    user_id = uuid.UUID(data["user"]["id"])
    token = data["tokens"]["access_token"]
    ws_id = uuid.UUID(data["workspace"]["id"]) if "workspace" in data else None
    if not ws_id:
        ws_resp = await async_client.get("/api/v1/workspaces", headers={"Authorization": f"Bearer {token}"})
        assert ws_resp.status_code == 200
        ws_id = uuid.UUID(ws_resp.json()[0]["id"])

    # 3. Create Project with ProjectDocumentV1 having 2 scenes
    async with async_session_factory() as db:
        project_service = ProjectService(db)
        project = Project(
            workspace_id=ws_id,
            created_by=user_id,
            title=title,
            revision=1,
            status="draft",
        )
        scenes = [
            Scene(
                id=str(uuid.uuid4()),
                sequence=1,
                duration=1.5,
                background={"type": "color", "value": "#0F172A"},
                speech=SceneSpeech(
                    voice_id="mock_voice_1",
                    script="HeyZen Phase 7 Real Media Composition Scene 1",
                ),
            ),
            Scene(
                id=str(uuid.uuid4()),
                sequence=2,
                duration=1.5,
                background={"type": "color", "value": "#1E293B"},
                speech=SceneSpeech(
                    voice_id="mock_voice_2",
                    script="Scene 2 Concat Demuxer Verification",
                ),
            ),
        ]
        doc = ProjectDocumentV1(
            schema_version=1,
            settings=ProjectSettings(
                aspect_ratio=aspect_ratio,
                width=width,
                height=height,
                fps=30,
            ),
            scenes=scenes,
        )
        version = ProjectVersion(
            project_id=project.id,
            revision=1,
            document=doc.model_dump(),
            created_by=user_id,
            source="initial",
        )
        created_project = await project_service.repo.create_project_with_initial_version(project, version)
        await db.commit()

    return user_id, ws_id, created_project.id


@pytest.mark.asyncio
async def test_phase7_real_media_rendering_acceptance_path(async_client):
    """AUTHORITATIVE ACCEPTANCE TEST: Real FFmpeg render pipeline to MinIO with Project.status='ready'."""
    user_id, ws_id, project_id = await _setup_workspace_and_project(
        async_client,
        title="Real Media Acceptance Candidate",
        width=1280,
        height=720,
        aspect_ratio="16:9",
    )

    # 1. Request render via ProjectRenderOrchestrator
    async with async_session_factory() as db:
        orchestrator = ProjectRenderOrchestrator(db)
        req = RenderProjectRequest(
            expected_revision=1,
            resolution="720p",
            fps=30,
            export_format="mp4",
        )
        job, created = await orchestrator.request_render(project_id, ws_id, user_id, req)
        await db.commit()
        assert created is True
        assert job.status == "queued"
        job_id = job.id

    # 2. Execute real render worker with AI_PROVIDER_MODE="real"
    with patch("app.workers.tasks.media_tasks.get_settings") as mock_settings:
        mock_settings.return_value.AI_PROVIDER_MODE = "real"
        mock_settings.return_value.FFMPEG_PATH = "ffmpeg"
        mock_settings.return_value.FFPROBE_PATH = "ffprobe"
        mock_settings.return_value.MEDIA_TIMEOUT_SECONDS = 120

        result = await _execute_render_video(job_id, f"task-{uuid.uuid4().hex[:8]}")

    # 3. Verify render worker result metrics
    assert result["output_asset_id"] is not None
    assert result["output_storage_key"] is not None
    assert result["thumbnail_asset_id"] is not None
    assert result["thumbnail_storage_key"] is not None
    assert result["duration_seconds"] >= 2.8
    assert result["resolution"] == "1280x720"
    assert result["format"] == "mp4"
    assert result["codec"] in ("h264", "aac")
    assert result["size_bytes"] > 1000

    # 4. Verify MinIO object persistence
    storage = get_storage_provider()
    assert storage.object_exists(result["output_storage_key"]), (
        f"Rendered video MP4 not found in MinIO: {result['output_storage_key']}"
    )
    assert storage.object_exists(result["thumbnail_storage_key"]), (
        f"Rendered thumbnail PNG not found in MinIO: {result['thumbnail_storage_key']}"
    )

    # 5. Verify database Job state
    async with async_session_factory() as db:
        job_svc = JobService(db)
        finished_job = await job_svc.job_repo.get_by_id(job_id)
        assert finished_job.status == "succeeded"
        assert finished_job.progress_percent == 100
        assert finished_job.result["output_asset_id"] == result["output_asset_id"]

    # 6. Verify target Project status transition to ready
    async with async_session_factory() as db:
        proj_svc = ProjectService(db)
        fresh_proj = await proj_svc.get_project(project_id, ws_id)
        assert fresh_proj.status == "ready", (
            f"Expected Project.status to be 'ready', got '{fresh_proj.status}'"
        )
        assert fresh_proj.thumbnail_asset_id is not None
        assert str(fresh_proj.thumbnail_asset_id) == result["thumbnail_asset_id"]


@pytest.mark.asyncio
async def test_phase7_real_media_rendering_vertical_shorts(async_client):
    """Verify real rendering of 9:16 vertical video shorts (1080x1920)."""
    user_id, ws_id, project_id = await _setup_workspace_and_project(
        async_client,
        title="Vertical Shorts Candidate",
        width=720,
        height=1280,
        aspect_ratio="9:16",
    )

    async with async_session_factory() as db:
        orchestrator = ProjectRenderOrchestrator(db)
        req = RenderProjectRequest(
            expected_revision=1,
            resolution="720p",
            fps=30,
            export_format="mp4",
        )
        job, _ = await orchestrator.request_render(project_id, ws_id, user_id, req)
        await db.commit()
        job_id = job.id

    with patch("app.workers.tasks.media_tasks.get_settings") as mock_settings:
        mock_settings.return_value.AI_PROVIDER_MODE = "real"
        result = await _execute_render_video(job_id, f"task-{uuid.uuid4().hex[:8]}")

    assert result["resolution"] == "720x1280"
    assert result["duration_seconds"] >= 2.8


@pytest.mark.asyncio
async def test_phase7_render_worker_cancellation_handling(async_client):
    """Verify cancelled render jobs abort cleanly and do not promote Project to ready."""
    user_id, ws_id, project_id = await _setup_workspace_and_project(async_client, title="Cancellation Candidate")

    async with async_session_factory() as db:
        orchestrator = ProjectRenderOrchestrator(db)
        req = RenderProjectRequest(expected_revision=1, resolution="720p", fps=30)
        job, _ = await orchestrator.request_render(project_id, ws_id, user_id, req)
        # Cancel before worker executes
        job_svc = JobService(db)
        await job_svc.cancel_job(job.id, ws_id)
        await db.commit()
        job_id = job.id

    with patch("app.workers.tasks.media_tasks.get_settings") as mock_settings:
        mock_settings.return_value.AI_PROVIDER_MODE = "real"
        result = await _execute_render_video(job_id, "task-cancelled")

    assert result["status"] == "cancelled"

    async with async_session_factory() as db:
        proj_svc = ProjectService(db)
        proj = await proj_svc.get_project(project_id, ws_id)
        assert proj.status != "ready"
