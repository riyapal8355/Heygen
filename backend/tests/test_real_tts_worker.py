"""Integration tests for real TTS inference inside Celery worker execution."""

import io
import uuid
import wave
import pytest
from httpx import AsyncClient

from app.db.session import async_session_factory
from app.models.job import Job
from app.services.job_service import JobService
from app.storage.s3 import get_storage_provider
from app.workers.tasks.ai_tasks import _execute_tts_synthesis


async def _setup_user_and_workspace(async_client: AsyncClient) -> tuple[uuid.UUID, uuid.UUID]:
    """Create committed user and workspace via API so separate worker sessions can resolve foreign keys."""
    email = f"tts_test_{uuid.uuid4().hex[:8]}@example.com"
    resp = await async_client.post(
        "/api/v1/auth/signup",
        json={"email": email, "display_name": "TTS Worker Tester", "password": "Password123!"},
    )
    assert resp.status_code == 201
    data = resp.json()
    user_id = uuid.UUID(data["user"]["id"])
    token = data["tokens"]["access_token"]

    ws_resp = await async_client.get("/api/v1/workspaces", headers={"Authorization": f"Bearer {token}"})
    assert ws_resp.status_code == 200
    ws_id = uuid.UUID(ws_resp.json()[0]["id"])
    return user_id, ws_id


@pytest.mark.asyncio
async def test_real_tts_worker_execution_and_asset_persistence(async_client: AsyncClient):
    """End-to-end verification that the Celery task executes Piper, creates an asset in MinIO, and updates the Job."""
    user_id, workspace_id = await _setup_user_and_workspace(async_client)

    async with async_session_factory() as db:
        job_service = JobService(db)

        # 1. Create Job with real Piper provider
        job = Job(
            workspace_id=workspace_id,
            created_by=user_id,
            job_type="tts_synthesis",
            status="queued",
            priority=50,
            progress_percent=0,
            stage="queued",
            payload={
                "text": "Hello from HeyZen.",
                "voice_id": "en_US-lessac-medium",
                "provider": "piper",
                "speed": 1.0,
            },
        )
        job = await job_service.job_repo.create(job)
        await db.commit()
        job_id = job.id

    # 2. Execute worker task function
    result = await _execute_tts_synthesis(job_id=job_id, task_id="test-celery-task-piper")

    # 3. Validate returned task dictionary
    assert result["provider"] == "piper"
    assert result["sample_rate"] == 22050
    assert result["duration_seconds"] > 0.5
    assert result["word_count"] == 3
    assert result["format"] == "wav"
    output_asset_id = result["output_asset_id"]
    output_storage_key = result["output_storage_key"]
    assert output_asset_id is not None
    assert output_storage_key is not None

    # 4. Verify database job state
    async with async_session_factory() as db:
        job_service = JobService(db)
        updated_job = await job_service.job_repo.get_by_id(job_id)
        assert updated_job is not None
        assert updated_job.status == "succeeded"
        assert updated_job.stage == "complete"
        assert updated_job.progress_percent == 100
        assert updated_job.result["provider"] == "piper"
        assert updated_job.result["sample_rate"] == 22050

    # 5. Verify asset binary in MinIO
    storage = get_storage_provider()
    audio_bytes = storage.get_object_bytes(output_storage_key)
    assert len(audio_bytes) > 20000
    assert audio_bytes[:4] == b"RIFF"
    assert audio_bytes[8:12] == b"WAVE"

    with io.BytesIO(audio_bytes) as buf:
        with wave.open(buf, "rb") as wf:
            assert wf.getnchannels() == 1
            assert wf.getsampwidth() == 2
            assert wf.getframerate() == 22050
            assert wf.getnframes() > 10000


@pytest.mark.asyncio
async def test_tts_worker_explicit_mock_mode(async_client: AsyncClient):
    """Verify Celery task respects explicit mock provider when requested."""
    user_id, workspace_id = await _setup_user_and_workspace(async_client)

    async with async_session_factory() as db:
        job_service = JobService(db)
        job = Job(
            workspace_id=workspace_id,
            created_by=user_id,
            job_type="tts_synthesis",
            status="queued",
            priority=50,
            progress_percent=0,
            stage="queued",
            payload={
                "text": "Simulated speech synthesis.",
                "provider": "mock",
            },
        )
        job = await job_service.job_repo.create(job)
        await db.commit()
        job_id = job.id

    result = await _execute_tts_synthesis(job_id=job_id, task_id="test-celery-task-mock")
    assert result["provider"] == "mock"
    assert result["sample_rate"] == 24000  # Mock sample rate


@pytest.mark.asyncio
async def test_tts_worker_cooperative_cancellation(async_client: AsyncClient):
    """Verify Celery task detects pre-cancelled job status and exits early."""
    user_id, workspace_id = await _setup_user_and_workspace(async_client)

    async with async_session_factory() as db:
        job_service = JobService(db)
        job = Job(
            workspace_id=workspace_id,
            created_by=user_id,
            job_type="tts_synthesis",
            status="queued",
            priority=50,
            progress_percent=0,
            stage="queued",
            payload={"text": "Should not synthesize."},
        )
        job = await job_service.job_repo.create(job)
        job_id = job.id
        await job_service.cancel_job(job_id=job_id, workspace_id=workspace_id)

    result = await _execute_tts_synthesis(job_id=job_id, task_id="test-celery-task-cancel")
    assert result == {"status": "cancelled"}


def test_tts_worker_job_routing_to_cpu_media():
    """Verify TTS synthesis jobs route deterministically to cpu_media queue for CPU execution."""
    from app.services.job_service import resolve_job_queue
    queue = resolve_job_queue("tts_synthesis")
    assert queue == "cpu_media"

    # Verify explicit CUDA preference routes to gpu_ai
    cuda_queue = resolve_job_queue("tts_synthesis", payload={"preferred_device": "cuda"})
    assert cuda_queue == "gpu_ai"


@pytest.mark.asyncio
async def test_tts_worker_failure_state_and_audit(async_client: AsyncClient):
    """Verify failed inference sets job status=failed and populates error details without silent fallback."""
    user_id, workspace_id = await _setup_user_and_workspace(async_client)

    async with async_session_factory() as db:
        job_service = JobService(db)
        job = Job(
            workspace_id=workspace_id,
            created_by=user_id,
            job_type="tts_synthesis",
            status="queued",
            priority=50,
            progress_percent=0,
            stage="queued",
            payload={
                "text": "Failing test.",
                "voice_id": "nonexistent_voice_fail_404",
                "provider": "piper",
            },
        )
        job = await job_service.job_repo.create(job)
        await db.commit()
        job_id = job.id

    with pytest.raises(Exception):
        await _execute_tts_synthesis(job_id=job_id, task_id="test-celery-fail")

    async with async_session_factory() as db:
        job_service = JobService(db)
        failed_job = await job_service.job_repo.get_by_id(job_id)
        assert failed_job is not None
        assert failed_job.status == "failed"
        assert failed_job.stage == "failed"
        assert "error" in failed_job.error_details


@pytest.mark.asyncio
async def test_tts_worker_workspace_isolation_and_asset_key(async_client: AsyncClient):
    """Verify generated audio asset adheres to strict workspace isolation key naming."""
    user_id, workspace_id = await _setup_user_and_workspace(async_client)

    async with async_session_factory() as db:
        job_service = JobService(db)
        job = Job(
            workspace_id=workspace_id,
            created_by=user_id,
            job_type="tts_synthesis",
            status="queued",
            priority=50,
            progress_percent=0,
            stage="queued",
            payload={
                "text": "Workspace isolation test.",
                "provider": "piper",
            },
        )
        job = await job_service.job_repo.create(job)
        await db.commit()
        job_id = job.id

    result = await _execute_tts_synthesis(job_id=job_id, task_id="test-celery-isolate")
    storage_key = result["output_storage_key"]
    expected_prefix = f"workspaces/{workspace_id}/assets/{result['output_asset_id']}/"
    assert storage_key.startswith(expected_prefix)
    assert not storage_key.startswith("C:") and not storage_key.startswith("/")

