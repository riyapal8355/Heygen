"""Phase 26: Complete Voice-to-Project Speech Pipeline Integration Tests.

Validates:
1. Voice lookup by ID and provider resolution (Piper Bryce and Kokoro Heart).
2. Workspace authorization & rejection of cross-workspace private voices.
3. Provider resolution isolation (Piper -> PiperTTSProvider, Kokoro -> KokoroTTSProvider).
4. Real Piper Bryce speech generation -> MinIO asset -> Scene attachment.
5. Real Kokoro Heart speech generation -> MinIO asset -> Scene attachment.
6. Multi-provider project containing Scene 1 (Piper) and Scene 2 (Kokoro).
7. Non-contamination: Piper produces 22,050 Hz WAV; Kokoro produces 24,000 Hz WAV.
8. Rejection of mock/unavailable catalog voices in real mode.
9. Rejection of soft-deleted voices.
10. Rejection of non-existent voice IDs.
11. Async job execution lifecycle (queued -> running -> completed).
12. Localization resetting generated audio asset and remapping target voice.
13. Timeline rendering: FFmpeg compositor consumes speech audio assets into final MP4.
"""

import io
import uuid
import wave
import numpy as np
import pytest
from httpx import AsyncClient
from unittest.mock import patch

from app.core.exceptions import ConflictException, ForbiddenException, NotFoundException
from app.db.session import async_session_factory
from app.models.project import Project, ProjectVersion
from app.models.voice import Voice
from app.repositories.asset import AssetRepository
from app.repositories.voice import VoiceRepository
from app.schemas.job import JobSubmitRequest
from app.schemas.orchestration import RenderProjectRequest, SynthesizeProjectSpeechRequest
from app.schemas.project_document import (
    DocumentAssetRef,
    ProjectDocumentV1,
    ProjectSettings,
    Scene,
    SceneSpeech,
)
from app.services.job_service import JobService
from app.services.project_localization_service import ProjectLocalizationService
from app.services.project_render_service import ProjectRenderOrchestrator
from app.services.project_service import ProjectService
from app.services.project_speech_service import ProjectSpeechOrchestrator
from app.storage.s3 import get_storage_provider
from app.workers.tasks.ai_tasks import _execute_project_batch_speech
from app.workers.tasks.media_tasks import _execute_render_video

PIPER_BRYCE_ID = "10000000-0000-0000-0000-000000000004"
KOKORO_HEART_ID = "10000000-0000-0000-0000-000000000021"
MOCK_ANNIE_ID = "10000000-0000-0000-0000-000000000003"


async def _setup_workspace_and_project(async_client: AsyncClient, title: str = "Pipeline Test Project"):
    """Helper creating user, workspace, and initialized project."""
    email = f"speech_pipe_{uuid.uuid4().hex[:8]}@example.com"
    resp = await async_client.post(
        "/api/v1/auth/signup",
        json={"email": email, "display_name": "Pipeline Tester", "password": "Password123!"},
    )
    assert resp.status_code == 201
    data = resp.json()
    user_id = uuid.UUID(data["user"]["id"])
    token = data["tokens"]["access_token"]

    ws_resp = await async_client.get("/api/v1/workspaces", headers={"Authorization": f"Bearer {token}"})
    assert ws_resp.status_code == 200
    ws_id = uuid.UUID(ws_resp.json()[0]["id"])

    async with async_session_factory() as db:
        proj_service = ProjectService(db)
        project = Project(
            workspace_id=ws_id,
            created_by=user_id,
            title=title,
            status="draft",
            revision=1,
        )
        doc = ProjectDocumentV1(
            schema_version=1,
            settings=ProjectSettings(width=1280, height=720, aspect_ratio="16:9", total_duration=5.0),
            scenes=[],
        )
        version = ProjectVersion(
            project_id=project.id,
            revision=1,
            document=doc.model_dump(),
            created_by=user_id,
            source="initial",
        )
        created_proj = await proj_service.repo.create_project_with_initial_version(project, version)
        await db.commit()
        project_id = created_proj.id

    return user_id, ws_id, project_id, token


@pytest.mark.asyncio
async def test_voice_lookup_and_provider_resolution(async_client: AsyncClient):
    """Verify voice resolution returns correct providers for Piper Bryce and Kokoro Heart."""
    user_id, ws_id, project_id, _ = await _setup_workspace_and_project(async_client)

    async with async_session_factory() as db:
        orchestrator = ProjectSpeechOrchestrator(db)

        # 1. Piper Bryce
        v_piper, prov_piper, ref_piper = await orchestrator._resolve_voice(
            voice_id=PIPER_BRYCE_ID,
            workspace_id=ws_id,
            is_mock_mode=False,
        )
        assert v_piper is not None
        assert prov_piper == "piper"
        assert ref_piper == "en_US-bryce-medium"

        # 2. Kokoro Heart
        v_kokoro, prov_kokoro, ref_kokoro = await orchestrator._resolve_voice(
            voice_id=KOKORO_HEART_ID,
            workspace_id=ws_id,
            is_mock_mode=False,
        )
        assert v_kokoro is not None
        assert prov_kokoro == "kokoro"
        assert ref_kokoro == "af_heart"


@pytest.mark.asyncio
async def test_workspace_authorization_cross_workspace_rejected(async_client: AsyncClient):
    """Verify private voice belonging to another workspace is strictly rejected with VOICE_ACCESS_DENIED."""
    user_id_a, ws_id_a, _, _ = await _setup_workspace_and_project(async_client)
    user_id_b, ws_id_b, _, _ = await _setup_workspace_and_project(async_client)

    # Create a private custom voice in Workspace A
    private_voice_id = uuid.uuid4()
    async with async_session_factory() as db:
        voice_repo = VoiceRepository(db)
        private_voice = Voice(
            id=private_voice_id,
            workspace_id=ws_id_a,
            created_by=user_id_a,
            name="Workspace A Secret Voice",
            language="en",
            gender="neutral",
            voice_type="custom",
            provider="piper",
            provider_reference="en_US-lessac-medium",
            visibility="workspace",  # Private to workspace A
            status="ready",
        )
        await voice_repo.create(private_voice)
        await db.commit()

    # Attempt to resolve from Workspace B
    async with async_session_factory() as db:
        orchestrator = ProjectSpeechOrchestrator(db)
        with pytest.raises(ForbiddenException) as exc_info:
            await orchestrator._resolve_voice(
                voice_id=str(private_voice_id),
                workspace_id=ws_id_b,
                is_mock_mode=False,
            )
        assert exc_info.value.code == "VOICE_ACCESS_DENIED"


@pytest.mark.asyncio
async def test_mock_voice_rejected_in_real_mode(async_client: AsyncClient):
    """Verify attempting to synthesize speech with an unavailable mock catalog voice raises VOICE_UNAVAILABLE."""
    user_id, ws_id, _, _ = await _setup_workspace_and_project(async_client)

    async with async_session_factory() as db:
        orchestrator = ProjectSpeechOrchestrator(db)
        with pytest.raises(ConflictException) as exc_info:
            await orchestrator._resolve_voice(
                voice_id=MOCK_ANNIE_ID,
                workspace_id=ws_id,
                is_mock_mode=False,
            )
        assert exc_info.value.code == "VOICE_UNAVAILABLE"


@pytest.mark.asyncio
async def test_deleted_and_nonexistent_voices_rejected(async_client: AsyncClient):
    """Verify deleted voices raise VOICE_DELETED and non-existent IDs raise VOICE_NOT_FOUND."""
    user_id, ws_id, _, _ = await _setup_workspace_and_project(async_client)

    # 1. Non-existent UUID
    fake_id = str(uuid.uuid4())
    async with async_session_factory() as db:
        orchestrator = ProjectSpeechOrchestrator(db)
        with pytest.raises(NotFoundException) as exc_info:
            await orchestrator._resolve_voice(
                voice_id=fake_id,
                workspace_id=ws_id,
                is_mock_mode=False,
            )
        assert exc_info.value.code == "VOICE_NOT_FOUND"

    # 2. Soft-deleted voice
    del_voice_id = uuid.uuid4()
    async with async_session_factory() as db:
        voice_repo = VoiceRepository(db)
        del_voice = Voice(
            id=del_voice_id,
            workspace_id=ws_id,
            created_by=user_id,
            name="Deleted Voice",
            language="en",
            gender="neutral",
            voice_type="custom",
            provider="piper",
            provider_reference="en_US-lessac-medium",
            visibility="workspace",
            status="ready",
        )
        created = await voice_repo.create(del_voice)
        await voice_repo.soft_delete(created)
        await db.commit()

    async with async_session_factory() as db:
        orchestrator = ProjectSpeechOrchestrator(db)
        with pytest.raises(NotFoundException) as exc_info:
            await orchestrator._resolve_voice(
                voice_id=str(del_voice_id),
                workspace_id=ws_id,
                is_mock_mode=False,
            )
        assert exc_info.value.code == "VOICE_DELETED"


@pytest.mark.asyncio
async def test_piper_bryce_real_speech_generation(async_client: AsyncClient):
    """Verify Piper Bryce synthesis creates a valid 22.05 kHz WAV asset in MinIO and attaches it to scene."""
    user_id, ws_id, project_id, _ = await _setup_workspace_and_project(async_client)

    # Set up project with Piper Bryce scene
    async with async_session_factory() as db:
        proj_service = ProjectService(db)
        version = await proj_service.get_version(
            (await proj_service.get_project(project_id, ws_id)).current_version_id,
            project_id,
            ws_id,
        )
        doc = ProjectDocumentV1.model_validate(version.document)
        doc.scenes = [
            Scene(
                id="scene-piper-bryce",
                sequence=1,
                duration=3.0,
                speech=SceneSpeech(
                    voice_id=PIPER_BRYCE_ID,
                    script="HeyZen presents neural speech synthesis using Piper Bryce.",
                ),
            )
        ]
        await proj_service.create_version(
            project_id=project_id,
            workspace_id=ws_id,
            user_id=user_id,
            expected_revision=1,
            document=doc,
        )
        await db.commit()

    # Synthesize speech
    async with async_session_factory() as db:
        orchestrator = ProjectSpeechOrchestrator(db)
        new_version = await orchestrator.synthesize_project_speech(
            project_id=project_id,
            workspace_id=ws_id,
            user_id=user_id,
            expected_revision=2,
        )
        await db.commit()

    assert new_version.revision == 3
    new_doc = ProjectDocumentV1.model_validate(new_version.document)
    scene = new_doc.scenes[0]
    asset_id_str = scene.speech.audio_asset_id
    assert asset_id_str is not None
    assert scene.duration > 1.0

    # Verify Asset in database
    async with async_session_factory() as db:
        asset_repo = AssetRepository(db)
        asset = await asset_repo.get_by_id(uuid.UUID(asset_id_str), ws_id)
        assert asset is not None
        assert asset.mime_type == "audio/wav"
        assert asset.extra_metadata.get("provider") == "piper"
        assert asset.extra_metadata.get("sample_rate") == 22050
        storage_key = asset.storage_key

    # Verify WAV in MinIO
    storage = get_storage_provider()
    assert storage.object_exists(storage_key) is True
    wav_bytes = storage.get_object_bytes(storage_key)
    assert len(wav_bytes) > 1000

    # Verify audio properties
    with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
        assert wf.getframerate() == 22050
        assert wf.getnchannels() == 1
        samples = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)
        assert np.max(np.abs(samples)) > 500  # Non-silent waveform


@pytest.mark.asyncio
async def test_kokoro_heart_real_speech_generation(async_client: AsyncClient):
    """Verify Kokoro Heart synthesis creates a valid 24 kHz WAV asset in MinIO and attaches it to scene."""
    user_id, ws_id, project_id, _ = await _setup_workspace_and_project(async_client)

    # Set up project with Kokoro Heart scene
    async with async_session_factory() as db:
        proj_service = ProjectService(db)
        version = await proj_service.get_version(
            (await proj_service.get_project(project_id, ws_id)).current_version_id,
            project_id,
            ws_id,
        )
        doc = ProjectDocumentV1.model_validate(version.document)
        doc.scenes = [
            Scene(
                id="scene-kokoro-heart",
                sequence=1,
                duration=3.0,
                speech=SceneSpeech(
                    voice_id=KOKORO_HEART_ID,
                    script="HeyZen presents high fidelity speech synthesis using Kokoro Heart.",
                ),
            )
        ]
        await proj_service.create_version(
            project_id=project_id,
            workspace_id=ws_id,
            user_id=user_id,
            expected_revision=1,
            document=doc,
        )
        await db.commit()

    # Synthesize speech
    async with async_session_factory() as db:
        orchestrator = ProjectSpeechOrchestrator(db)
        new_version = await orchestrator.synthesize_project_speech(
            project_id=project_id,
            workspace_id=ws_id,
            user_id=user_id,
            expected_revision=2,
        )
        await db.commit()

    assert new_version.revision == 3
    new_doc = ProjectDocumentV1.model_validate(new_version.document)
    scene = new_doc.scenes[0]
    asset_id_str = scene.speech.audio_asset_id
    assert asset_id_str is not None
    assert scene.duration > 1.0

    # Verify Asset in database
    async with async_session_factory() as db:
        asset_repo = AssetRepository(db)
        asset = await asset_repo.get_by_id(uuid.UUID(asset_id_str), ws_id)
        assert asset is not None
        assert asset.mime_type == "audio/wav"
        assert asset.extra_metadata.get("provider") == "kokoro"
        assert asset.extra_metadata.get("sample_rate") == 24000
        storage_key = asset.storage_key

    # Verify WAV in MinIO
    storage = get_storage_provider()
    assert storage.object_exists(storage_key) is True
    wav_bytes = storage.get_object_bytes(storage_key)
    assert len(wav_bytes) > 1000

    # Verify audio properties
    with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
        assert wf.getframerate() == 24000
        assert wf.getnchannels() == 1
        samples = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)
        assert np.max(np.abs(samples)) > 500  # Non-silent waveform


@pytest.mark.asyncio
async def test_multi_provider_project_and_render_pipeline(async_client: AsyncClient):
    """MANDATORY ACCEPTANCE TEST:
    Create a project with Scene 1 (Piper Bryce) and Scene 2 (Kokoro Heart).
    Verify both synthesize accurately with no cross-contamination, and render into final MP4 video.
    """
    user_id, ws_id, project_id, token = await _setup_workspace_and_project(
        async_client, title="Multi-Provider Acceptance Project"
    )

    # 1. Configure Project with Scene 1 (Piper) and Scene 2 (Kokoro)
    async with async_session_factory() as db:
        proj_service = ProjectService(db)
        version = await proj_service.get_version(
            (await proj_service.get_project(project_id, ws_id)).current_version_id,
            project_id,
            ws_id,
        )
        doc = ProjectDocumentV1.model_validate(version.document)
        doc.scenes = [
            Scene(
                id="scene-1-piper",
                sequence=1,
                duration=3.0,
                background={"type": "color", "value": "#1E293B"},
                speech=SceneSpeech(
                    voice_id=PIPER_BRYCE_ID,
                    script="Scene one is narrated with Piper Bryce.",
                ),
            ),
            Scene(
                id="scene-2-kokoro",
                sequence=2,
                duration=3.0,
                background={"type": "color", "value": "#0F172A"},
                speech=SceneSpeech(
                    voice_id=KOKORO_HEART_ID,
                    script="Scene two is narrated with Kokoro Heart.",
                ),
            ),
        ]
        await proj_service.create_version(
            project_id=project_id,
            workspace_id=ws_id,
            user_id=user_id,
            expected_revision=1,
            document=doc,
        )
        await db.commit()

    # 2. Synthesize Project Speech in one batch operation
    async with async_session_factory() as db:
        orchestrator = ProjectSpeechOrchestrator(db)
        new_version = await orchestrator.synthesize_project_speech(
            project_id=project_id,
            workspace_id=ws_id,
            user_id=user_id,
            expected_revision=2,
        )
        await db.commit()

    assert new_version.revision == 3
    synth_doc = ProjectDocumentV1.model_validate(new_version.document)
    s1 = synth_doc.scenes[0]
    s2 = synth_doc.scenes[1]

    # Verify both scenes received distinct audio assets
    assert s1.speech.audio_asset_id is not None
    assert s2.speech.audio_asset_id is not None
    assert s1.speech.audio_asset_id != s2.speech.audio_asset_id

    # 3. Verify Provider Isolation & Distinct Characteristics
    storage = get_storage_provider()
    async with async_session_factory() as db:
        asset_repo = AssetRepository(db)
        asset_1 = await asset_repo.get_by_id(uuid.UUID(s1.speech.audio_asset_id), ws_id)
        asset_2 = await asset_repo.get_by_id(uuid.UUID(s2.speech.audio_asset_id), ws_id)

        assert asset_1.extra_metadata.get("provider") == "piper"
        assert asset_1.extra_metadata.get("sample_rate") == 22050

        assert asset_2.extra_metadata.get("provider") == "kokoro"
        assert asset_2.extra_metadata.get("sample_rate") == 24000

    # Verify MinIO files
    wav_1 = storage.get_object_bytes(asset_1.storage_key)
    wav_2 = storage.get_object_bytes(asset_2.storage_key)

    with wave.open(io.BytesIO(wav_1), "rb") as wf1:
        assert wf1.getframerate() == 22050
    with wave.open(io.BytesIO(wav_2), "rb") as wf2:
        assert wf2.getframerate() == 24000

    # 4. Render Project into Final MP4 Video via TimelineCompositor
    async with async_session_factory() as db:
        render_orchestrator = ProjectRenderOrchestrator(db)
        req = RenderProjectRequest(
            resolution="720p",
            format="mp4",
            expected_revision=3,
            priority=50,
        )
        job, created = await render_orchestrator.request_render(project_id, ws_id, user_id, req)
        await db.commit()
        assert created is True
        job_id = job.id

    with patch("app.workers.tasks.media_tasks.get_settings") as mock_settings:
        mock_settings.return_value.AI_PROVIDER_MODE = "real"
        mock_settings.return_value.FFMPEG_PATH = "ffmpeg"
        mock_settings.return_value.FFPROBE_PATH = "ffprobe"
        mock_settings.return_value.MEDIA_TIMEOUT_SECONDS = 180

        render_result = await _execute_render_video(job_id, f"task-multi-e2e-{uuid.uuid4().hex[:6]}")

    # 5. Verify Final Render Video Result
    assert render_result["format"] == "mp4"
    assert render_result["duration_seconds"] > 2.0
    video_key = render_result["output_storage_key"]
    assert storage.object_exists(video_key) is True
    video_bytes = storage.get_object_bytes(video_key)
    assert len(video_bytes) > 10000
    assert b"ftyp" in video_bytes[:32]


@pytest.mark.asyncio
async def test_async_job_lifecycle_speech_generation(async_client: AsyncClient):
    """Verify submitting speech synthesis through the API queues a job and processes successfully."""
    user_id, ws_id, project_id, token = await _setup_workspace_and_project(async_client)

    # 1. Setup scene
    async with async_session_factory() as db:
        proj_service = ProjectService(db)
        version = await proj_service.get_version(
            (await proj_service.get_project(project_id, ws_id)).current_version_id,
            project_id,
            ws_id,
        )
        doc = ProjectDocumentV1.model_validate(version.document)
        doc.scenes = [
            Scene(
                id="async-job-scene",
                sequence=1,
                duration=3.0,
                speech=SceneSpeech(
                    voice_id=PIPER_BRYCE_ID,
                    script="Async background job speech processing test.",
                ),
            )
        ]
        await proj_service.create_version(
            project_id=project_id,
            workspace_id=ws_id,
            user_id=user_id,
            expected_revision=1,
            document=doc,
        )
        await db.commit()

    # 2. Submit async speech job via API
    resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/projects/{project_id}/synthesize-speech",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "expected_revision": 2,
            "run_async": True,
        },
    )
    assert resp.status_code == 202
    job_data = resp.json()
    job_id = uuid.UUID(job_data["id"])
    assert job_data["status"] == "queued"

    # 3. Execute job task via worker handler
    worker_res = await _execute_project_batch_speech(job_id, f"task-{uuid.uuid4().hex[:6]}")
    assert worker_res["project_id"] == str(project_id)
    assert worker_res["new_revision"] == 3

    # 4. Verify completed state in DB
    async with async_session_factory() as db:
        job_service = JobService(db)
        completed_job = await job_service.job_repo.get_by_id(job_id)
        assert completed_job.status == "succeeded"
        assert completed_job.progress_percent == 100


@pytest.mark.asyncio
async def test_localization_resets_audio_and_remaps_voice(async_client: AsyncClient):
    """Verify localization invalidates audio_asset_id and updates voice_id to target language voice."""
    user_id, ws_id, project_id, token = await _setup_workspace_and_project(async_client)

    # 1. Project with existing audio asset ID
    existing_asset_id = str(uuid.uuid4())
    async with async_session_factory() as db:
        proj_service = ProjectService(db)
        version = await proj_service.get_version(
            (await proj_service.get_project(project_id, ws_id)).current_version_id,
            project_id,
            ws_id,
        )
        doc = ProjectDocumentV1.model_validate(version.document)
        doc.scenes = [
            Scene(
                id="scene-trans",
                sequence=1,
                duration=4.0,
                speech=SceneSpeech(
                    voice_id=PIPER_BRYCE_ID,
                    script="Welcome to HeyZen.",
                    audio_asset_id=existing_asset_id,
                ),
            )
        ]
        await proj_service.create_version(
            project_id=project_id,
            workspace_id=ws_id,
            user_id=user_id,
            expected_revision=1,
            document=doc,
        )
        await db.commit()

    # 2. Localize to Spanish with Spanish Kokoro Dora voice
    KOKORO_DORA_ID = "10000000-0000-0000-0000-000000000023"
    async with async_session_factory() as db:
        loc_service = ProjectLocalizationService(db)
        forked_proj, forked_ver = await loc_service.translate_project(
            project_id=project_id,
            workspace_id=ws_id,
            user_id=user_id,
            target_language="es",
            target_voice_id=KOKORO_DORA_ID,
            create_fork=True,
            expected_revision=2,
        )
        await db.commit()

    # Verify translated document has audio_asset_id reset and target voice mapped
    trans_doc = ProjectDocumentV1.model_validate(forked_ver.document)
    trans_scene = trans_doc.scenes[0]
    assert trans_scene.speech.audio_asset_id is None  # Must NOT reuse English audio
    assert trans_scene.speech.voice_id == KOKORO_DORA_ID
