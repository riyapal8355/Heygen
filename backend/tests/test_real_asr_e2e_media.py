"""Primary Acceptance and End-to-End Media Integration Tests for Real ASR.

Validates:
- Primary Closed-Loop Pipeline:
    Piper REAL TTS ("Hello from HeyZen.")
      ↓
    Real WAV waveform in MinIO
      ↓
    Real Whisper ASR
      ↓
    Real transcript & segment timestamps
      ↓
    ProjectDocumentV1 safe subtitles
      ↓
    Immutable ProjectVersion (OCC)
- Requirement #2 Verification:
    SceneLayer(type="text") safety check: existing visual text overlays remain intact,
    and subtitle cues are safely isolated on scene.subtitles without clashing with compositor.
- Optimistic Concurrency Control: stale revision rejection raises CONCURRENCY_CONFLICT.
- API Endpoint: POST /api/v1/workspaces/{workspace_id}/projects/{project_id}/transcribe
"""

import uuid
import pytest
from httpx import AsyncClient

from app.ai.adapters.piper import DEFAULT_PIPER_VOICE_ID, PiperTTSProvider
from app.db.session import async_session_factory
from app.media.compositor import TimelineCompositor
from app.media.workspace import MediaWorkspace
from app.models.project import ProjectVersion
from app.schemas.orchestration import TranscribeProjectAudioRequest
from app.schemas.project_document import (
    CanvasSettings,
    SceneLayer,
    SceneSpeech,
    create_default_project_document,
)
from app.services.asset_lifecycle import AssetLifecycleManager
from app.services.project_service import ProjectService
from app.services.project_transcription_service import ProjectTranscriptionOrchestrator
from app.core.exceptions import ConflictException


async def _setup_authenticated_env(async_client: AsyncClient) -> tuple[uuid.UUID, uuid.UUID, str]:
    """Create committed user and workspace, returning user_id, workspace_id, access_token."""
    email = f"e2e_asr_{uuid.uuid4().hex[:8]}@example.com"
    resp = await async_client.post(
        "/api/v1/auth/signup",
        json={"email": email, "display_name": "ASR E2E Tester", "password": "Password123!"},
    )
    assert resp.status_code == 201
    data = resp.json()
    user_id = uuid.UUID(data["user"]["id"])
    token = data["tokens"]["access_token"]

    ws_resp = await async_client.get("/api/v1/workspaces", headers={"Authorization": f"Bearer {token}"})
    assert ws_resp.status_code == 200
    ws_id = uuid.UUID(ws_resp.json()[0]["id"])
    return user_id, ws_id, token


@pytest.mark.asyncio
async def test_primary_closed_loop_piper_to_whisper_e2e(async_client: AsyncClient):
    """Primary Acceptance Test: Piper Real TTS -> MinIO WAV -> Real Whisper ASR -> ProjectDocumentV1 OCC."""
    user_id, workspace_id, _ = await _setup_authenticated_env(async_client)

    # 1. Synthesize real audio using Piper TTS
    spoken_text = "Hello from HeyZen."
    piper = PiperTTSProvider()
    synth_res = await piper.synthesize_speech(text=spoken_text, voice_id=DEFAULT_PIPER_VOICE_ID)
    assert len(synth_res.audio_bytes) > 20000

    async with async_session_factory() as db:
        # 2. Store audio asset in MinIO
        asset_mgr = AssetLifecycleManager(db)
        asset = await asset_mgr.ingest_generated_asset(
            workspace_id=workspace_id,
            created_by=user_id,
            content=synth_res.audio_bytes,
            original_filename="piper_speech.wav",
            asset_type="audio",
            mime_type="audio/wav",
            metadata={"voice_id": DEFAULT_PIPER_VOICE_ID},
        )

        # 3. Create Project with initial revision
        proj_service = ProjectService(db)
        project = await proj_service.create_project(
            workspace_id=workspace_id,
            user_id=user_id,
            title="Primary ASR Acceptance Project",
        )
        doc = create_default_project_document()
        scene = doc.scenes[0]
        scene.speech = SceneSpeech(
            voice_id="en_US-lessac-medium",
            script="Hello from HeyZen.",
            audio_asset_id=str(asset.id),
        )
        v1 = await proj_service.create_version(
            project_id=project.id,
            workspace_id=workspace_id,
            user_id=user_id,
            expected_revision=1,
            document=doc,
            source="initial",
        )
        await db.commit()
        project_id = project.id
        scene_id = scene.id
        rev1 = v1.revision

    # 4. Transcribe project audio via ProjectTranscriptionOrchestrator
    async with async_session_factory() as db:
        orchestrator = ProjectTranscriptionOrchestrator(db)
        new_version, transcription = await orchestrator.transcribe_project_audio(
            project_id=project_id,
            workspace_id=workspace_id,
            user_id=user_id,
            expected_revision=rev1,
            scene_id=scene_id,
            provider_override="whisper",
            language="en",
        )
        await db.commit()

    # 5. Validate acceptance criteria
    assert new_version.revision == rev1 + 1
    assert transcription.detected_language == "en"
    assert transcription.duration_seconds > 0.5
    assert len(transcription.segments) >= 1
    # Check similarity (not hardcoded)
    lower_text = transcription.full_text.lower()
    assert "hello" in lower_text
    assert "from" in lower_text

    # Validate timing on new version document
    doc_scene = new_version.document["scenes"][0]
    assert "subtitles" in doc_scene
    subtitles = doc_scene["subtitles"]
    assert len(subtitles) >= 1
    for sub in subtitles:
        assert sub["start"] >= 0.0
        assert sub["end"] > sub["start"]
        assert len(sub["text"]) > 0


@pytest.mark.asyncio
async def test_scenelayer_safety_and_compositor_compatibility(async_client: AsyncClient):
    """Requirement #2 Test: Verify that existing SceneLayer(type="text") is preserved and unaffected by subtitles."""
    user_id, workspace_id, _ = await _setup_authenticated_env(async_client)

    piper = PiperTTSProvider()
    synth = await piper.synthesize_speech(text="Autonomous AI Video.", voice_id=DEFAULT_PIPER_VOICE_ID)

    async with async_session_factory() as db:
        asset_mgr = AssetLifecycleManager(db)
        asset = await asset_mgr.ingest_generated_asset(
            workspace_id=workspace_id,
            created_by=user_id,
            content=synth.audio_bytes,
            original_filename="audio_layer_test.wav",
            asset_type="audio",
            mime_type="audio/wav",
        )

        proj_service = ProjectService(db)
        project = await proj_service.create_project(workspace_id=workspace_id, user_id=user_id, title="SceneLayer Safety Test")
        doc = create_default_project_document()
        scene = doc.scenes[0]
        scene.speech = SceneSpeech(
            voice_id="en_US-lessac-medium",
            script="Autonomous AI Video.",
            audio_asset_id=str(asset.id),
        )

        # Add explicit visual editor text layer (e.g. Title banner)
        visual_layer = SceneLayer(
            id="title-banner-1",
            type="text",
            name="Title Layer",
            start_time=0.0,
            end_time=5.0,
            transform={"x": 0.5, "y": 0.2, "scale": 1.0},
            content={"title": "Exclusive Presentation Title", "text": "Exclusive Presentation Title"},
        )
        scene.layers.append(visual_layer)

        v1 = await proj_service.create_version(
            project_id=project.id,
            workspace_id=workspace_id,
            user_id=user_id,
            expected_revision=1,
            document=doc,
            source="initial",
        )
        await db.commit()
        project_id = project.id
        scene_id = scene.id
        rev1 = v1.revision

    # Transcribe scene audio
    async with async_session_factory() as db:
        orchestrator = ProjectTranscriptionOrchestrator(db)
        new_version, _ = await orchestrator.transcribe_project_audio(
            project_id=project_id,
            workspace_id=workspace_id,
            user_id=user_id,
            expected_revision=rev1,
            scene_id=scene_id,
            provider_override="whisper",
        )
        await db.commit()

    # Verify visual text layer is 100% UNTOUCHED
    updated_scene = new_version.document["scenes"][0]
    assert len(updated_scene["layers"]) == 1
    assert updated_scene["layers"][0]["id"] == "title-banner-1"
    assert updated_scene["layers"][0]["content"]["text"] == "Exclusive Presentation Title"

    # Verify subtitles are stored safely in scene.subtitles
    assert len(updated_scene["subtitles"]) >= 1

    # Verify compositor parses document without conflict and renders MP4 cleanly
    compositor = TimelineCompositor()
    async with async_session_factory() as db:
        with MediaWorkspace() as mws:
            render_res = await compositor.render_project(
                document=new_version.document,
                workspace_id=workspace_id,
                db=db,
                media_workspace=mws,
            )
            assert render_res.video_path.exists()
            assert render_res.video_path.stat().st_size > 0
            assert render_res.total_duration > 0


@pytest.mark.asyncio
async def test_transcribe_occ_stale_revision_conflict(async_client: AsyncClient):
    """Verify that attempting to transcribe with a stale revision raises CONCURRENCY_CONFLICT."""
    user_id, workspace_id, _ = await _setup_authenticated_env(async_client)

    async with async_session_factory() as db:
        proj_service = ProjectService(db)
        project = await proj_service.create_project(workspace_id=workspace_id, user_id=user_id, title="OCC Conflict Test")
        doc = create_default_project_document()
        v1 = await proj_service.create_version(
            project_id=project.id,
            workspace_id=workspace_id,
            user_id=user_id,
            expected_revision=1,
            document=doc,
            source="initial",
        )
        await db.commit()
        project_id = project.id

    # Call with stale expected_revision=99
    async with async_session_factory() as db:
        orchestrator = ProjectTranscriptionOrchestrator(db)
        with pytest.raises(ConflictException) as exc_info:
            await orchestrator.transcribe_project_audio(
                project_id=project_id,
                workspace_id=workspace_id,
                user_id=user_id,
                expected_revision=99,  # Stale! Current is 1
            )
        assert exc_info.value.code == "CONCURRENCY_CONFLICT"


@pytest.mark.asyncio
async def test_transcribe_project_api_endpoint(async_client: AsyncClient):
    """Verify API endpoint POST /workspaces/{ws_id}/projects/{proj_id}/transcribe (both sync and async)."""
    user_id, workspace_id, token = await _setup_authenticated_env(async_client)
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Synthesize audio via Piper TTS and upload to MinIO
    piper = PiperTTSProvider()
    synth = await piper.synthesize_speech(text="API endpoint transcription test.", voice_id=DEFAULT_PIPER_VOICE_ID)

    async with async_session_factory() as db:
        asset_mgr = AssetLifecycleManager(db)
        asset = await asset_mgr.ingest_generated_asset(
            workspace_id=workspace_id,
            created_by=user_id,
            content=synth.audio_bytes,
            original_filename="api_speech.wav",
            asset_type="audio",
            mime_type="audio/wav",
        )

        proj_service = ProjectService(db)
        project = await proj_service.create_project(workspace_id=workspace_id, user_id=user_id, title="API Transcribe Project")
        doc = create_default_project_document()
        scene = doc.scenes[0]
        scene.speech = SceneSpeech(
            voice_id="en_US-lessac-medium",
            script="API endpoint transcription test.",
            audio_asset_id=str(asset.id),
        )
        v1 = await proj_service.create_version(
            project_id=project.id,
            workspace_id=workspace_id,
            user_id=user_id,
            expected_revision=1,
            document=doc,
            source="initial",
        )
        await db.commit()
        project_id = project.id
        scene_id = scene.id
        rev1 = v1.revision

    # Test Synchronous API execution (run_async=False) -> HTTP 200 ProjectVersionResponse
    sync_resp = await async_client.post(
        f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/transcribe",
        headers=headers,
        json={
            "expected_revision": rev1,
            "scene_id": scene_id,
            "provider": "whisper",
            "language": "en",
            "run_async": False,
        },
    )
    assert sync_resp.status_code == 200
    v2_data = sync_resp.json()
    assert v2_data["revision"] == rev1 + 1

    # Test Asynchronous API execution (run_async=True) -> HTTP 202 JobResponse
    async_resp = await async_client.post(
        f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/transcribe",
        headers=headers,
        json={
            "expected_revision": rev1 + 1,
            "scene_id": scene_id,
            "provider": "whisper",
            "language": "en",
            "run_async": True,
        },
    )
    assert async_resp.status_code == 202
    job_data = async_resp.json()
    assert job_data["job_type"] == "asr_transcription"
    assert job_data["status"] == "queued"
