"""Integration tests for real ASR inference inside Celery worker execution (Queue: cpu_media)."""

import uuid
import pytest
from httpx import AsyncClient

from app.ai.adapters.piper import DEFAULT_PIPER_VOICE_ID, PiperTTSProvider
from app.db.session import async_session_factory
from app.models.job import Job
from app.schemas.project_document import create_default_project_document
from app.services.asset_lifecycle import AssetLifecycleManager
from app.services.job_service import JobService, resolve_job_queue
from app.services.project_service import ProjectService
from app.workers.tasks.ai_tasks import _execute_asr_transcription


async def _setup_user_and_workspace(async_client: AsyncClient) -> tuple[uuid.UUID, uuid.UUID]:
    """Create committed user and workspace via API so separate worker sessions can resolve foreign keys."""
    email = f"asr_worker_{uuid.uuid4().hex[:8]}@example.com"
    resp = await async_client.post(
        "/api/v1/auth/signup",
        json={"email": email, "display_name": "ASR Worker Tester", "password": "Password123!"},
    )
    assert resp.status_code == 201
    data = resp.json()
    user_id = uuid.UUID(data["user"]["id"])
    token = data["tokens"]["access_token"]

    ws_resp = await async_client.get("/api/v1/workspaces", headers={"Authorization": f"Bearer {token}"})
    assert ws_resp.status_code == 200
    ws_id = uuid.UUID(ws_resp.json()[0]["id"])
    return user_id, ws_id


def test_asr_queue_routing():
    """Verify asr_transcription jobs are routed to cpu_media queue on CPU nodes."""
    queue = resolve_job_queue(job_type="asr_transcription", payload={})
    assert queue == "cpu_media"

    # Explicit CUDA requests route to gpu_ai
    cuda_queue = resolve_job_queue(job_type="asr_transcription", payload={"preferred_device": "cuda"})
    assert cuda_queue == "gpu_ai"


@pytest.mark.asyncio
async def test_real_asr_worker_execution_direct_audio(async_client: AsyncClient):
    """End-to-end worker test: Ingest Piper WAV to MinIO, execute ASR worker, update Job status and telemetry."""
    user_id, workspace_id = await _setup_user_and_workspace(async_client)

    # 1. Synthesize real audio via Piper TTS and store in MinIO
    piper = PiperTTSProvider()
    spoken_text = "Welcome to HeyZen video studio."
    synth = await piper.synthesize_speech(text=spoken_text, voice_id=DEFAULT_PIPER_VOICE_ID)

    async with async_session_factory() as db:
        asset_mgr = AssetLifecycleManager(db)
        asset = await asset_mgr.ingest_generated_asset(
            workspace_id=workspace_id,
            created_by=user_id,
            content=synth.audio_bytes,
            original_filename="sample_for_transcription.wav",
            asset_type="audio",
            mime_type="audio/wav",
            metadata={"source": "piper_test"},
        )
        audio_storage_key = asset.storage_key

        # 2. Create Job in queued state
        job_service = JobService(db)
        job = Job(
            workspace_id=workspace_id,
            created_by=user_id,
            job_type="asr_transcription",
            status="queued",
            priority=50,
            progress_percent=0,
            stage="queued",
            payload={
                "audio_storage_key": audio_storage_key,
                "provider": "whisper",
                "language": "en",
            },
        )
        job = await job_service.job_repo.create(job)
        await db.commit()
        job_id = job.id

    # 3. Execute Celery worker task function
    result = await _execute_asr_transcription(job_id=job_id, task_id="test-celery-task-asr")

    # 4. Validate returned result
    assert result["provider"] == "whisper"
    assert result["model"] == "asr/whisper-tiny-cpu"
    assert result["language"] == "en"
    assert result["duration_seconds"] > 0.5
    assert result["segment_count"] >= 1
    assert result["word_count"] >= 3
    assert len(result["transcription_text"]) > 0
    assert result["processing_latency"] > 0.0

    # 5. Verify database job state
    async with async_session_factory() as db:
        job_service = JobService(db)
        updated_job = await job_service.job_repo.get_by_id(job_id)
        assert updated_job is not None
        assert updated_job.status == "succeeded"
        assert updated_job.stage == "complete"
        assert updated_job.progress_percent == 100
        assert updated_job.result["provider"] == "whisper"
        assert updated_job.result["language"] == "en"


@pytest.mark.asyncio
async def test_real_asr_worker_project_transcription_occ(async_client: AsyncClient):
    """Verify worker transcribes project scene audio and commits new version under OCC."""
    user_id, workspace_id = await _setup_user_and_workspace(async_client)

    # 1. Synthesize audio via Piper TTS and upload to MinIO
    piper = PiperTTSProvider()
    synth = await piper.synthesize_speech(text="Hello from HeyZen.", voice_id=DEFAULT_PIPER_VOICE_ID)

    async with async_session_factory() as db:
        asset_mgr = AssetLifecycleManager(db)
        asset = await asset_mgr.ingest_generated_asset(
            workspace_id=workspace_id,
            created_by=user_id,
            content=synth.audio_bytes,
            original_filename="scene_speech.wav",
            asset_type="audio",
            mime_type="audio/wav",
            metadata={"voice": "piper"},
        )

        # 2. Create Project and initial ProjectVersion
        proj_service = ProjectService(db)
        project = await proj_service.create_project(
            workspace_id=workspace_id,
            user_id=user_id,
            title="ASR Project Worker Test",
        )
        doc = create_default_project_document()
        scene = doc.scenes[0]
        # Attach speech with audio_asset_id
        from app.schemas.project_document import SceneSpeech
        scene.speech = SceneSpeech(
            voice_id="en_US-lessac-medium",
            script="Hello from HeyZen.",
            audio_asset_id=str(asset.id),
        )
        initial_version = await proj_service.create_version(
            project_id=project.id,
            workspace_id=workspace_id,
            user_id=user_id,
            expected_revision=1,
            document=doc,
            source="initial_test",
        )
        await db.commit()
        project_id = project.id
        scene_id = scene.id
        expected_rev = initial_version.revision

        # 3. Create ASR Job for project
        job_service = JobService(db)
        job = Job(
            workspace_id=workspace_id,
            created_by=user_id,
            job_type="asr_transcription",
            status="queued",
            priority=50,
            progress_percent=0,
            stage="queued",
            payload={
                "project_id": str(project_id),
                "expected_revision": expected_rev,
                "scene_id": scene_id,
                "provider": "whisper",
                "language": "en",
            },
        )
        job = await job_service.job_repo.create(job)
        await db.commit()
        job_id = job.id

    # 4. Execute worker task
    result = await _execute_asr_transcription(job_id=job_id, task_id="test-proj-asr-task")

    # 5. Verify OCC version advance
    assert result["project_id"] == str(project_id)
    assert result["new_revision"] == expected_rev + 1
    assert result["segment_count"] >= 1

    # Verify updated ProjectVersion in DB
    async with async_session_factory() as db:
        proj_service = ProjectService(db)
        new_version_id = uuid.UUID(result["new_version_id"])
        new_ver = await proj_service.get_version(new_version_id, project_id, workspace_id)
        assert new_ver is not None
        assert new_ver.revision == expected_rev + 1
        scene_data = new_ver.document["scenes"][0]
        assert "subtitles" in scene_data
        assert len(scene_data["subtitles"]) >= 1
        assert new_ver.document["metadata"]["transcription"]["detected_language"] == "en"


@pytest.mark.asyncio
async def test_real_asr_worker_cancellation(async_client: AsyncClient):
    """Verify cooperative cancellation prevents unnecessary neural processing."""
    user_id, workspace_id = await _setup_user_and_workspace(async_client)

    async with async_session_factory() as db:
        job_service = JobService(db)
        job = Job(
            workspace_id=workspace_id,
            created_by=user_id,
            job_type="asr_transcription",
            status="cancelled",
            priority=50,
            progress_percent=0,
            stage="cancelled",
            payload={"audio_storage_key": "any-key"},
        )
        job = await job_service.job_repo.create(job)
        await db.commit()
        job_id = job.id

    result = await _execute_asr_transcription(job_id=job_id, task_id="test-cancelled-asr")
    assert result == {"status": "cancelled"}


@pytest.mark.asyncio
async def test_real_asr_worker_failure_on_missing_audio(async_client: AsyncClient):
    """Verify that worker marks Job as failed when audio asset cannot be found."""
    user_id, workspace_id = await _setup_user_and_workspace(async_client)

    async with async_session_factory() as db:
        job_service = JobService(db)
        job = Job(
            workspace_id=workspace_id,
            created_by=user_id,
            job_type="asr_transcription",
            status="queued",
            priority=50,
            progress_percent=0,
            stage="queued",
            payload={
                "audio_storage_key": "non_existent_audio_key_12345.wav",
                "expected_revision": 1,
                "provider": "whisper",
            },
        )
        job = await job_service.job_repo.create(job)
        await db.commit()
        job_id = job.id

    with pytest.raises(Exception):
        await _execute_asr_transcription(job_id=job_id, task_id="test-failing-asr")

    async with async_session_factory() as db:
        job_service = JobService(db)
        failed_job = await job_service.job_repo.get_by_id(job_id)
        assert failed_job is not None
        assert failed_job.status == "failed"
        assert "error" in failed_job.error_details
