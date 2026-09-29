"""Test suite for Celery multi-queue topology, task routing, and worker pipeline executions."""

import uuid
import pytest
from httpx import AsyncClient

from app.db.session import async_session_factory
from app.models.job import Job
from app.repositories.job import JobEventRepository, JobRepository
from app.workers.celery_app import celery_app
from app.workers.tasks.ai_tasks import (
    _execute_avatar_train,
    _execute_lip_sync,
    _execute_translate_project,
    _execute_tts_synthesis,
    _execute_voice_clone,
    tts_synthesis,
)
from app.workers.tasks.maintenance_tasks import reap_stale_jobs
from app.workers.tasks.media_tasks import _execute_render_video, render_video


async def _setup_user_workspace(async_client: AsyncClient, name: str) -> tuple[str, str, str]:
    email = f"{name.lower().replace(' ', '_')}_{uuid.uuid4().hex[:6]}@example.com"
    resp = await async_client.post(
        "/api/v1/auth/signup",
        json={"email": email, "display_name": name, "password": "Password123!"},
    )
    assert resp.status_code == 201
    data = resp.json()
    token = data["tokens"]["access_token"]
    user_id = data["user"]["id"]

    ws_resp = await async_client.get("/api/v1/workspaces", headers={"Authorization": f"Bearer {token}"})
    assert ws_resp.status_code == 200
    workspace_id = ws_resp.json()[0]["id"]
    return token, workspace_id, user_id


def test_celery_multi_queue_topology():
    """Verify Celery application configures cpu_media, gpu_ai, and maintenance queues."""
    queues = {q.name for q in celery_app.conf.task_queues}
    assert "cpu_media" in queues
    assert "gpu_ai" in queues
    assert "maintenance" in queues
    assert celery_app.conf.task_default_queue == "cpu_media"

    routes = celery_app.conf.task_routes
    assert routes["heyzen.tasks.media.*"]["queue"] == "cpu_media"
    assert routes["heyzen.tasks.ai.*"]["queue"] == "gpu_ai"
    assert routes["heyzen.tasks.maintenance.*"]["queue"] == "maintenance"
    assert routes["heyzen.ping"]["queue"] == "cpu_media"


@pytest.mark.asyncio
async def test_render_video_pipeline_execution(async_client: AsyncClient):
    """Verify video rendering pipeline transitions, progress reporting, and output results."""
    token, ws_id, user_id = await _setup_user_workspace(async_client, "Render Worker")

    async with async_session_factory() as db:
        repo = JobRepository(db)
        job = Job(
            workspace_id=uuid.UUID(ws_id),
            created_by=uuid.UUID(user_id),
            job_type="render_video",
            status="queued",
            payload={"timeline": {"fps": 30, "duration": 30}},
        )
        await repo.create(job)
        await db.commit()
        job_id = job.id

    # Execute async pipeline
    result = await _execute_render_video(job_id, "test-render-task")
    assert result["format"] == "mp4"
    assert result["resolution"] == "1920x1080"

    # Verify updated database state
    async with async_session_factory() as db:
        repo = JobRepository(db)
        event_repo = JobEventRepository(db)
        updated_job = await repo.get_by_id(job_id)
        assert updated_job is not None
        assert updated_job.status == "succeeded"
        assert updated_job.progress_percent == 100
        assert updated_job.stage == "complete"
        assert updated_job.result is not None
        assert updated_job.result["format"] == "mp4"

        events = await event_repo.list_by_job(job_id)
        # Should record: starting, progress stages, and succeeded
        assert len(events) >= 4
        stages = [e.stage for e in events]
        assert "analyzing_timeline" in stages
        assert "rendering_audio" in stages
        assert "complete" in stages


@pytest.mark.asyncio
async def test_tts_synthesis_task_execution(async_client: AsyncClient):
    """Verify TTS synthesis worker task runs with mock adapter and updates state."""
    token, ws_id, user_id = await _setup_user_workspace(async_client, "TTS Worker")

    async with async_session_factory() as db:
        repo = JobRepository(db)
        job = Job(
            workspace_id=uuid.UUID(ws_id),
            created_by=uuid.UUID(user_id),
            job_type="tts_synthesis",
            status="queued",
            payload={"text": "Hello HeyZen synthesis test.", "speed": 1.0},
        )
        await repo.create(job)
        await db.commit()
        job_id = job.id

    result = await _execute_tts_synthesis(job_id, "test-tts-task")
    assert result["sample_rate"] == 24000
    assert result["duration_seconds"] > 0

    async with async_session_factory() as db:
        repo = JobRepository(db)
        updated_job = await repo.get_by_id(job_id)
        assert updated_job.status == "succeeded"
        assert updated_job.progress_percent == 100


@pytest.mark.asyncio
async def test_lip_sync_task_execution(async_client: AsyncClient):
    """Verify lip sync worker task generates simulated output."""
    token, ws_id, user_id = await _setup_user_workspace(async_client, "LipSync Worker")

    async with async_session_factory() as db:
        repo = JobRepository(db)
        job = Job(
            workspace_id=uuid.UUID(ws_id),
            created_by=uuid.UUID(user_id),
            job_type="lip_sync",
            status="queued",
            payload={"avatar_look_key": "look-1", "audio_storage_key": "audio-1"},
        )
        await repo.create(job)
        await db.commit()
        job_id = job.id

    result = await _execute_lip_sync(job_id, "test-lipsync-task")
    assert result["format"] == "mp4"

    async with async_session_factory() as db:
        repo = JobRepository(db)
        updated_job = await repo.get_by_id(job_id)
        assert updated_job.status == "succeeded"


@pytest.mark.asyncio
async def test_translate_project_task_execution(async_client: AsyncClient):
    """Verify translation worker task translates text."""
    token, ws_id, user_id = await _setup_user_workspace(async_client, "Translator Worker")

    async with async_session_factory() as db:
        repo = JobRepository(db)
        job = Job(
            workspace_id=uuid.UUID(ws_id),
            created_by=uuid.UUID(user_id),
            job_type="translate_project",
            status="queued",
            payload={"text": "Welcome to video creation.", "source_language": "en", "target_language": "es"},
        )
        await repo.create(job)
        await db.commit()
        job_id = job.id

    result = await _execute_translate_project(job_id, "test-translate-task")
    assert result["target_language"] == "es"
    assert "[ES]" in result["translated_text"]

    async with async_session_factory() as db:
        repo = JobRepository(db)
        updated_job = await repo.get_by_id(job_id)
        assert updated_job.status == "succeeded"


@pytest.mark.asyncio
async def test_voice_clone_and_avatar_train(async_client: AsyncClient):
    """Verify voice cloning and avatar training worker tasks succeed deterministically."""
    token, ws_id, user_id = await _setup_user_workspace(async_client, "Training Worker")

    # Voice clone
    async with async_session_factory() as db:
        repo = JobRepository(db)
        vc_job = Job(
            workspace_id=uuid.UUID(ws_id),
            created_by=uuid.UUID(user_id),
            job_type="voice_clone",
            status="queued",
            payload={"voice_name": "Executive Voice", "sample_audio_keys": ["sample1.wav", "sample2.wav"]},
        )
        await repo.create(vc_job)
        await db.commit()
        vc_job_id = vc_job.id

    vc_result = await _execute_voice_clone(vc_job_id, "test-vc-task")
    assert "mock-voice" in vc_result["voice_id"]

    # Avatar train
    async with async_session_factory() as db:
        repo = JobRepository(db)
        at_job = Job(
            workspace_id=uuid.UUID(ws_id),
            created_by=uuid.UUID(user_id),
            job_type="avatar_train",
            status="queued",
            payload={"avatar_name": "CEO Twin", "training_video_keys": ["vid1.mp4"]},
        )
        await repo.create(at_job)
        await db.commit()
        at_job_id = at_job.id

    at_result = await _execute_avatar_train(at_job_id, "test-avatar-task")
    assert "weights" in at_result["weights_key"]


def test_reap_stale_jobs_maintenance():
    """Verify maintenance task executes without exception."""
    res = reap_stale_jobs(timeout_minutes=60)
    assert "reaped_jobs" in res
    assert "threshold_utc" in res


def test_celery_sync_worker_entrypoint_missing_job():
    """Verify Celery task synchronous entrypoint handles execution when invoked in worker process."""
    res = render_video(str(uuid.uuid4()))
    assert res == {"status": "not_found"}
