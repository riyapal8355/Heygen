"""Integration tests for real avatar lip-sync inference inside Celery worker execution."""

import uuid
import cv2
import numpy as np
import pytest
from httpx import AsyncClient

from app.db.session import async_session_factory
from app.models.avatar import Avatar
from app.models.job import Job
from app.models.project import Project, ProjectVersion
from app.schemas.project_document import (
    CanvasSettings,
    DocumentAssetRef,
    ProjectDocumentV1,
    ProjectSettings,
    Scene,
    SceneAvatar,
    SceneSpeech,
)
from app.services.asset_lifecycle import AssetLifecycleManager
from app.services.job_service import JobService, resolve_job_queue
from app.services.project_service import ProjectService
from app.storage.s3 import get_storage_provider
from app.workers.tasks.ai_tasks import _execute_lip_sync


def _create_synthetic_wav_bytes(duration_seconds: float = 1.0, sample_rate: int = 16000) -> bytes:
    """Generate minimal valid PCM WAV bytes with a sine wave tone."""
    import io
    import wave

    t = np.linspace(0, duration_seconds, int(sample_rate * duration_seconds), endpoint=False)
    waveform = (np.sin(2 * np.pi * 440.0 * t) * 16000).astype(np.int16)

    bio = io.BytesIO()
    with wave.open(bio, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(waveform.tobytes())
    return bio.getvalue()


def _create_synthetic_portrait_image_bytes(width: int = 320, height: int = 320) -> bytes:
    """Generate synthetic portrait image bytes."""
    img = np.ones((height, width, 3), dtype=np.uint8) * 230
    cv2.circle(img, (width // 2, height // 2), int(min(width, height) * 0.35), (180, 210, 240), -1)
    cv2.circle(img, (int(width * 0.4), int(height * 0.4)), 8, (50, 50, 50), -1)
    cv2.circle(img, (int(width * 0.6), int(height * 0.4)), 8, (50, 50, 50), -1)
    cv2.ellipse(img, (width // 2, int(height * 0.65)), (25, 12), 0, 0, 180, (50, 50, 180), -1)
    _, buf = cv2.imencode(".png", img)
    return buf.tobytes()


async def _setup_user_and_workspace(async_client: AsyncClient) -> tuple[uuid.UUID, uuid.UUID]:
    """Create committed user and workspace via API."""
    email = f"avatar_worker_{uuid.uuid4().hex[:8]}@example.com"
    resp = await async_client.post(
        "/api/v1/auth/signup",
        json={"email": email, "display_name": "Avatar Worker Tester", "password": "Password123!"},
    )
    assert resp.status_code == 201
    data = resp.json()
    user_id = uuid.UUID(data["user"]["id"])
    token = data["tokens"]["access_token"]

    ws_resp = await async_client.get("/api/v1/workspaces", headers={"Authorization": f"Bearer {token}"})
    assert ws_resp.status_code == 200
    ws_id = uuid.UUID(ws_resp.json()[0]["id"])
    return user_id, ws_id


def test_avatar_task_queue_routing():
    """Verify Celery queue resolution for CPU Wav2Lip vs CUDA MuseTalk."""
    # CPU Wav2Lip routes to cpu_media
    assert resolve_job_queue("lip_sync", {"provider": "wav2lip"}) == "cpu_media"
    assert resolve_job_queue("generate_avatar_video", {"provider": "wav2lip"}) == "cpu_media"
    assert resolve_job_queue("generate_avatar_video", {"device": "cpu"}) == "cpu_media"


    # GPU / CUDA requests route to gpu_ai
    assert resolve_job_queue("lip_sync", {"provider": "musetalk", "device": "cuda"}) == "gpu_ai"
    assert resolve_job_queue("generate_avatar_video", {"device": "cuda"}) == "gpu_ai"
    assert resolve_job_queue("generate_avatar_video", {"requires_gpu": True}) == "gpu_ai"


@pytest.mark.asyncio
async def test_real_wav2lip_worker_execution(async_client: AsyncClient):
    """Verify _execute_lip_sync executes Wav2Lip on CPU, saves video asset, and updates project revision."""
    user_id, workspace_id = await _setup_user_and_workspace(async_client)

    async with async_session_factory() as db:
        asset_mgr = AssetLifecycleManager(db)

        # 1. Store portrait image asset
        portrait_bytes = _create_synthetic_portrait_image_bytes()
        image_asset = await asset_mgr.ingest_generated_asset(
            workspace_id=workspace_id,
            created_by=user_id,
            content=portrait_bytes,
            original_filename="portrait.png",
            asset_type="image",
            mime_type="image/png",
        )

        # 2. Store audio asset
        wav_bytes = _create_synthetic_wav_bytes(duration_seconds=1.0)
        audio_asset = await asset_mgr.ingest_generated_asset(
            workspace_id=workspace_id,
            created_by=user_id,
            content=wav_bytes,
            original_filename="speech.wav",
            asset_type="audio",
            mime_type="audio/wav",
        )

        # 3. Create Avatar entity referencing image
        avatar = Avatar(
            workspace_id=workspace_id,
            created_by=user_id,
            name="Test Avatar Actor",
            source_asset_id=image_asset.id,
            preview_asset_id=image_asset.id,
            status="ready",
        )
        db.add(avatar)
        await db.flush()
        avatar_id = avatar.id

        # 4. Create Project with initial revision
        scene = Scene(
            id=str(uuid.uuid4()),
            sequence=1,
            duration=2.0,
            avatar=SceneAvatar(avatar_id=str(avatar_id)),
            speech=SceneSpeech(voice_id="en_US-lessac-medium", script="Hello world", audio_asset_id=str(audio_asset.id)),
        )

        doc = ProjectDocumentV1(
            schema_version=1,
            settings=ProjectSettings(width=1280, height=720, aspect_ratio="16:9", total_duration=2.0),
            scenes=[scene],
            assets=[
                DocumentAssetRef(asset_id=str(image_asset.id), asset_type="image", storage_key=image_asset.storage_key),
                DocumentAssetRef(asset_id=str(audio_asset.id), asset_type="audio", storage_key=audio_asset.storage_key),
            ],
        )

        project_service = ProjectService(db)
        project = Project(
            workspace_id=workspace_id,
            created_by=user_id,
            title="Real Wav2Lip Worker Test Project",
            status="draft",
            revision=1,
        )
        version = ProjectVersion(
            project_id=project.id,
            revision=1,
            document=doc.model_dump(),
            created_by=user_id,
            source="initial",
        )
        created_proj = await project_service.repo.create_project_with_initial_version(project, version)
        await db.commit()
        project_id = created_proj.id

        # 5. Create Job for lip-sync execution
        job_service = JobService(db)
        job = Job(
            workspace_id=workspace_id,
            created_by=user_id,
            job_type="generate_avatar_video",
            status="queued",
            priority=50,
            progress_percent=0,
            stage="queued",
            payload={
                "project_id": str(project_id),
                "expected_revision": 1,
                "scene_id": scene.id,
                "provider": "wav2lip",
                "device": "cpu",
            },
        )
        job = await job_service.job_repo.create(job)
        await db.commit()
        job_id = job.id

    # 6. Execute worker task function
    result = await _execute_lip_sync(job_id=job_id, task_id="test-celery-avatar-task")

    # 7. Validate results
    assert result["status"] == "succeeded"
    assert result["provider"] == "wav2lip"
    assert result["new_revision"] == 2
    assert "video_asset_id" in result
    assert result["duration_seconds"] >= 0.9

    # 8. Verify Job and ProjectVersion in DB
    async with async_session_factory() as db:
        job_service = JobService(db)
        updated_job = await job_service.job_repo.get_by_id(job_id)
        assert updated_job is not None
        assert updated_job.status == "succeeded"
        assert updated_job.progress_percent == 100

        project_service = ProjectService(db)
        proj = await project_service.get_project(project_id, workspace_id)
        assert proj.revision == 2

        v2 = await project_service.get_version(proj.current_version_id, project_id, workspace_id)
        doc_v2 = v2.document
        target_avatar = doc_v2["scenes"][0]["avatar"]
        assert target_avatar["video_asset_id"] == result["video_asset_id"]

    # 9. Verify generated video in storage
    storage = get_storage_provider()
    mp4_bytes = await storage.get_object(result["storage_key"])
    assert len(mp4_bytes) > 2000
    assert mp4_bytes[:8].endswith(b"ftyp") or b"moov" in mp4_bytes[:2048]


@pytest.mark.asyncio
async def test_avatar_worker_cooperative_cancellation(async_client: AsyncClient):
    """Verify worker task detects cancelled state and exits without running inference."""
    user_id, workspace_id = await _setup_user_and_workspace(async_client)

    async with async_session_factory() as db:
        job_service = JobService(db)
        job = Job(
            workspace_id=workspace_id,
            created_by=user_id,
            job_type="generate_avatar_video",
            status="cancelled",
            priority=50,
            progress_percent=0,
            stage="cancelled",
            payload={"project_id": str(uuid.uuid4()), "expected_revision": 1},
        )
        job = await job_service.job_repo.create(job)
        await db.commit()
        job_id = job.id

    result = await _execute_lip_sync(job_id=job_id, task_id="test-celery-cancel")
    assert result["status"] == "cancelled"


@pytest.mark.asyncio
async def test_avatar_worker_failure_recording(async_client: AsyncClient):
    """Verify worker marks job as failed and records error details when project not found."""
    user_id, workspace_id = await _setup_user_and_workspace(async_client)

    async with async_session_factory() as db:
        job_service = JobService(db)
        job = Job(
            workspace_id=workspace_id,
            created_by=user_id,
            job_type="generate_avatar_video",
            status="queued",
            priority=50,
            progress_percent=0,
            stage="queued",
            payload={"project_id": str(uuid.uuid4()), "expected_revision": 1},
        )
        job = await job_service.job_repo.create(job)
        await db.commit()
        job_id = job.id

    with pytest.raises(Exception):
        await _execute_lip_sync(job_id=job_id, task_id="test-celery-fail")

    async with async_session_factory() as db:
        job_service = JobService(db)
        failed_job = await job_service.job_repo.get_by_id(job_id)
        assert failed_job.status == "failed"
        assert failed_job.error_details is not None
