"""Integration tests for Audio Enhancement Celery worker execution (Queue: cpu_media).

Verifies:
1. Celery task queue routing (cpu_media for CPU nodes, gpu_ai for explicit CUDA).
2. Direct audio asset enhancement via worker task.
3. Project timeline speech enhancement via worker task with OCC version bump.
4. Cooperative cancellation handling.
"""

import io
import math
import struct
import uuid
import wave
import pytest
from httpx import AsyncClient

from app.db.session import async_session_factory
from app.models.job import Job
from app.models.project import Project, ProjectVersion
from app.schemas.project_document import ProjectDocumentV1, Scene, SceneSpeech
from app.services.asset_lifecycle import AssetLifecycleManager
from app.services.job_service import JobService, resolve_job_queue
from app.services.project_service import ProjectService
from app.workers.tasks.ai_tasks import _execute_enhance_speech


def _generate_synthetic_wav(duration_seconds: float = 2.0, sample_rate: int = 16000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        total_samples = int(duration_seconds * sample_rate)
        samples = [int(16000 * math.sin(2 * math.pi * 440 * (i / sample_rate))) for i in range(total_samples)]
        wf.writeframes(struct.pack(f"<{len(samples)}h", *samples))
    return buf.getvalue()


async def _setup_user_and_workspace(async_client: AsyncClient) -> tuple[uuid.UUID, uuid.UUID]:
    """Create committed user and workspace via API."""
    email = f"audio_worker_{uuid.uuid4().hex[:8]}@example.com"
    resp = await async_client.post(
        "/api/v1/auth/signup",
        json={"email": email, "display_name": "Audio Worker Tester", "password": "Password123!"},
    )
    assert resp.status_code == 201
    data = resp.json()
    user_id = uuid.UUID(data["user"]["id"])
    token = data["tokens"]["access_token"]

    ws_resp = await async_client.get("/api/v1/workspaces", headers={"Authorization": f"Bearer {token}"})
    assert ws_resp.status_code == 200
    ws_id = uuid.UUID(ws_resp.json()[0]["id"])
    return user_id, ws_id


def test_audio_enhance_queue_routing():
    """Verify enhance_speech and enhance_project_speech route to cpu_media queue by default."""
    queue1 = resolve_job_queue(job_type="enhance_speech", payload={})
    assert queue1 == "cpu_media"

    queue2 = resolve_job_queue(job_type="enhance_project_speech", payload={})
    assert queue2 == "cpu_media"

    cuda_queue = resolve_job_queue(job_type="enhance_speech", payload={"preferred_device": "cuda"})
    assert cuda_queue == "gpu_ai"


@pytest.mark.asyncio
async def test_audio_enhance_worker_direct_audio(async_client: AsyncClient):
    """End-to-end worker test: direct audio asset enhancement."""
    user_id, workspace_id = await _setup_user_and_workspace(async_client)
    raw_wav = _generate_synthetic_wav(duration_seconds=2.0)

    async with async_session_factory() as db:
        asset_mgr = AssetLifecycleManager(db)
        asset = await asset_mgr.ingest_generated_asset(
            workspace_id=workspace_id,
            created_by=user_id,
            content=raw_wav,
            original_filename="test_raw_speech.wav",
            asset_type="audio",
            mime_type="audio/wav",
            metadata={"test": "worker_direct"},
        )
        audio_storage_key = asset.storage_key

        job_service = JobService(db)
        job = Job(
            workspace_id=workspace_id,
            created_by=user_id,
            job_type="enhance_speech",
            status="queued",
            priority=50,
            progress_percent=0,
            stage="queued",
            payload={
                "audio_storage_key": audio_storage_key,
                "denoise": True,
                "remove_silence": False,
                "remove_fillers": False,
                "master_audio": True,
            },
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)
        job_id = job.id

    # Execute worker task
    task_id = str(uuid.uuid4())
    result = await _execute_enhance_speech(job_id, task_id)

    assert result is not None
    assert "output_asset_id" in result
    assert result["noise_reduction_db"] == 18.0
    assert result["sample_rate"] == 48000
    assert result["fillers_status"] == "NOT_IMPLEMENTED"

    # Verify job status in DB
    async with async_session_factory() as db:
        service = JobService(db)
        finished_job = await service.job_repo.get_by_id(job_id)
        assert finished_job is not None
        assert finished_job.status == "succeeded"
        assert finished_job.progress_percent == 100


@pytest.mark.asyncio
async def test_audio_enhance_worker_project_level(async_client: AsyncClient):
    """End-to-end worker test: project-level speech enhancement with OCC."""
    user_id, workspace_id = await _setup_user_and_workspace(async_client)
    raw_wav = _generate_synthetic_wav(duration_seconds=2.0)

    async with async_session_factory() as db:
        asset_mgr = AssetLifecycleManager(db)
        asset = await asset_mgr.ingest_generated_asset(
            workspace_id=workspace_id,
            created_by=user_id,
            content=raw_wav,
            original_filename="scene_raw.wav",
            asset_type="audio",
            mime_type="audio/wav",
            metadata={"test": "worker_project"},
        )

        project_service = ProjectService(db)
        project = Project(
            workspace_id=workspace_id,
            created_by=user_id,
            title="Worker Project Test",
            revision=1,
        )
        scene = Scene(
            id="scene_worker_1",
            sequence=1,
            duration=2.0,
            speech=SceneSpeech(
                voice_id="voice_mock_en_marcus",
                script="Test script for worker",
                audio_asset_id=str(asset.id),
            ),
        )
        doc = ProjectDocumentV1(schema_version=1, scenes=[scene])
        version = ProjectVersion(
            project_id=project.id,
            revision=1,
            document=doc.model_dump(),
            created_by=user_id,
            source="initial",
        )
        await project_service.repo.create_project_with_initial_version(project, version)

        job_service = JobService(db)
        job = Job(
            workspace_id=workspace_id,
            created_by=user_id,
            job_type="enhance_project_speech",
            status="queued",
            priority=50,
            progress_percent=0,
            stage="queued",
            payload={
                "project_id": str(project.id),
                "expected_revision": 1,
                "denoise": True,
                "master_audio": True,
            },
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)
        job_id = job.id

    # Execute worker task
    task_id = str(uuid.uuid4())
    result = await _execute_enhance_speech(job_id, task_id)

    assert result is not None
    assert result["new_revision"] == 2
    assert result["scenes_enhanced"] == 1
    assert result["fillers_status"] == "NOT_IMPLEMENTED"

    async with async_session_factory() as db:
        service = JobService(db)
        finished_job = await service.job_repo.get_by_id(job_id)
        assert finished_job.status == "succeeded"


@pytest.mark.asyncio
async def test_audio_enhance_worker_cooperative_cancellation(async_client: AsyncClient):
    """Verify pre-cancelled or runtime-cancelled jobs exit cooperatively."""
    user_id, workspace_id = await _setup_user_and_workspace(async_client)

    async with async_session_factory() as db:
        job = Job(
            workspace_id=workspace_id,
            created_by=user_id,
            job_type="enhance_speech",
            status="cancelled",
            priority=50,
            progress_percent=0,
            stage="cancelled",
            payload={"test": "cancelled"},
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)
        job_id = job.id

    result = await _execute_enhance_speech(job_id, "task-cancelled")
    assert result == {"status": "cancelled"}
