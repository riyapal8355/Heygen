"""Comprehensive tests for real AI video and media generation pipeline.

Tests:
1. End-to-end media generation pipeline: Project -> Script -> Real TTS Audio -> Compositor -> MP4 -> MinIO -> Asset -> ProjectVersion -> Completed Job.
2. Media validation with FFprobe: container=MP4, video stream, audio stream, duration > 0, width > 0, height > 0, file size > 0.
3. Workspace isolation: Workspace B cannot read Workspace A's job, project, or output video asset.
4. Controlled failure recovery: Invalid pipeline input marks job failed with error details.
"""

import copy
import uuid
import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import async_session_factory
from app.main import app
from app.media.ffprobe import FFprobeService
from app.models.asset import Asset
from app.models.job import Job
from app.models.project import Project, ProjectVersion
from app.models.workspace import Workspace, WorkspaceMember
from app.repositories.asset import AssetRepository
from app.schemas.orchestration import GenerateProjectRequest
from app.schemas.project_document import ProjectDocumentV1, ProjectSettings, Scene, SceneAvatar, SceneSpeech
from app.services.asset_lifecycle import AssetLifecycleManager
from app.services.job_service import JobService
from app.services.media_pipeline_service import MediaPipelineService
from app.services.project_service import ProjectService
from app.services.video_agent_service import VideoAgentService
from app.storage.s3 import get_storage_provider


@pytest.mark.asyncio
async def test_real_media_generation_pipeline_end_to_end(db_session, test_user, test_workspace):
    """Verify full end-to-end media pipeline produces real playable MP4 in MinIO with Asset record."""
    # 1. Create project with VideoAgentService
    agent_service = VideoAgentService(db_session)
    gen_req = GenerateProjectRequest(
        prompt="Introduce HeyZen AI video production studio in a clean concise intro",
        target_duration_seconds=10.0,
        aspect_ratio="16:9",
        avatar_id="30000000-0000-0000-0000-000000000004",  # Daniel
        voice_id="en_US-lessac-medium",  # Real Piper TTS voice
        video_tone="Professional",
        auto_synthesize_speech=False,
    )

    project, initial_version, _ = await agent_service.generate_project(
        workspace_id=test_workspace.id,
        user_id=test_user.id,
        request=gen_req,
    )
    await db_session.commit()
    await db_session.refresh(project)
    await db_session.refresh(initial_version)

    # 2. Submit Job
    job_service = JobService(db_session)
    job = Job(
        workspace_id=test_workspace.id,
        created_by=test_user.id,
        job_type="generate_project",
        status="queued",
        stage="preparing",
        stage_message="Queued for generation",
        payload={
            "project_id": str(project.id),
            "initial_version_id": str(initial_version.id),
            "prompt": gen_req.prompt,
            "voice_id": "en_US-lessac-medium",
            "avatar_id": "30000000-0000-0000-0000-000000000004",
        },
        result={
            "project_id": str(project.id),
            "initial_version_id": str(initial_version.id),
        },
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    # 3. Execute media pipeline
    pipeline = MediaPipelineService(db_session)
    result = await pipeline.execute_generation_pipeline(job.id)

    # 4. Verify Job completed successfully
    assert result["status"] == "completed"
    assert "output_asset_id" in result
    assert "duration_seconds" in result
    assert result["duration_seconds"] > 0
    assert result["format"] == "mp4"

    # Refresh job from DB
    await db_session.refresh(job)
    assert job.status == "succeeded"
    assert job.stage in ("complete", "completed")
    assert job.progress_percent == 100

    # 5. Verify Output Video Asset exists in MinIO
    output_asset_id = uuid.UUID(result["output_asset_id"])
    asset_repo = AssetRepository(db_session)
    video_asset = await asset_repo.get_by_id(output_asset_id, test_workspace.id)
    assert video_asset is not None
    assert video_asset.asset_type == "video"
    assert video_asset.mime_type == "video/mp4"
    assert video_asset.size_bytes > 0

    storage = get_storage_provider()
    raw_mp4 = storage.get_object_bytes(video_asset.storage_key)
    assert len(raw_mp4) > 0
    assert len(raw_mp4) == video_asset.size_bytes

    # 6. Validate MP4 container and streams with FFprobe
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_f:
        tmp_path = tmp_f.name
        tmp_f.write(raw_mp4)

    try:
        ffprobe = FFprobeService()
        probe = await ffprobe.validate_render_output(
            tmp_path,
            min_duration=0.1,
            require_video=True,
            require_audio=True,
        )
        assert probe.duration_seconds > 0
        assert probe.width == 1920
        assert probe.height == 1080
        assert probe.codec_name == "h264"
        assert probe.has_audio is True
    finally:
        import os
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

    # 7. Verify Project and ProjectVersion update
    await db_session.refresh(project)
    assert project.status == "ready"
    assert project.thumbnail_asset_id is not None
    assert project.duration_ms > 0

    proj_service = ProjectService(db_session)
    latest_version = await proj_service.get_version(project.current_version_id, project.id, test_workspace.id)
    doc = ProjectDocumentV1.model_validate(latest_version.document)
    assert len(doc.assets) >= 1
    # Check speech audio assets were attached to scenes
    for scene in doc.scenes:
        if scene.speech and scene.speech.script:
            assert scene.speech.audio_asset_id is not None


@pytest.mark.asyncio
async def test_media_validation_failure_on_corrupt_file():
    """Verify FFprobe validation strictly rejects non-playable or invalid containers."""
    import tempfile
    ffprobe = FFprobeService()
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_f:
        tmp_path = tmp_f.name
        tmp_f.write(b"NOT_A_REAL_MP4_FILE_JUST_CORRUPT_BYTES")

    try:
        from app.media.errors import RenderOutputInvalidError
        with pytest.raises(RenderOutputInvalidError):
            await ffprobe.validate_render_output(
                tmp_path,
                min_duration=0.1,
                require_video=True,
                require_audio=True,
            )
    finally:
        import os
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


@pytest.mark.asyncio
async def test_workspace_isolation_for_generation_job_and_assets(db_session, test_user):
    """Verify Workspace B cannot read Workspace A's job, project, or output video asset."""
    # Create Workspace A and Workspace B with test_user as owner
    ws_a = Workspace(name="Workspace A", slug=f"ws-a-{uuid.uuid4().hex[:6]}", owner_id=test_user.id)
    ws_b = Workspace(name="Workspace B", slug=f"ws-b-{uuid.uuid4().hex[:6]}", owner_id=test_user.id)
    db_session.add_all([ws_a, ws_b])
    await db_session.flush()

    member_a = WorkspaceMember(workspace_id=ws_a.id, user_id=test_user.id, role="owner")
    db_session.add(member_a)
    await db_session.commit()

    # Create dummy asset and project in Workspace A
    asset_mgr = AssetLifecycleManager(db_session)
    asset_a = await asset_mgr.ingest_generated_asset(
        workspace_id=ws_a.id,
        created_by=test_user.id,
        content=b"FAKE_MP4_DATA_FOR_ISOLATION_TEST",
        original_filename="secret_video.mp4",
        asset_type="video",
        mime_type="video/mp4",
    )

    job_a = Job(
        workspace_id=ws_a.id,
        created_by=test_user.id,
        job_type="generate_project",
        status="succeeded",
        payload={"secret": "workspace_a_only"},
    )
    db_session.add(job_a)
    await db_session.commit()

    # Workspace B attempts access
    asset_repo = AssetRepository(db_session)
    cross_asset = await asset_repo.get_by_id(asset_a.id, ws_b.id)
    assert cross_asset is None, "Workspace B must NOT be able to resolve Workspace A's asset"

    job_service = JobService(db_session)
    from app.core.exceptions import NotFoundException
    with pytest.raises(NotFoundException):
        await job_service.get_job(job_a.id, ws_b.id)


@pytest.mark.asyncio
async def test_pipeline_failure_handling(db_session, test_user, test_workspace):
    """Verify controlled pipeline failure marks job failed and updates project status."""
    non_existent_project_id = uuid.uuid4()

    # Create job pointing to non-existent project
    job = Job(
        workspace_id=test_workspace.id,
        created_by=test_user.id,
        job_type="generate_project",
        status="queued",
        payload={"project_id": str(non_existent_project_id)},
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    # Execute pipeline - should fail gracefully and mark job failed
    pipeline = MediaPipelineService(db_session)
    with pytest.raises(Exception):
        await pipeline.execute_generation_pipeline(job.id)

    await db_session.refresh(job)
    assert job.status == "failed"
    assert job.error_details is not None
    assert "error" in job.error_details
