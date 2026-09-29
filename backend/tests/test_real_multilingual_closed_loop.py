"""Phase 8 Step 6 - Real Multilingual Neural Closed-Loop Pipeline Acceptance Test.

Executes the complete self-hosted, CPU-first multilingual video localization pipeline:
1. Qwen 2.5 0.5B INT4 ONNX CPU generates English ProjectDocumentV1
       ↓
2. Real CTranslate2 INT8 translates script to Spanish with Brand Glossary preservation
       ↓
3. Spanish ProjectDocumentV1 created under sequential OCC
       ↓
4. Real Spanish Piper TTS (es_ES-davefx-medium) synthesizes Spanish speech WAV → MinIO
       ↓
5. Multilingual faster-whisper ASR transcribes Spanish audio → Spanish subtitles/cues
       ↓
6. Real Wav2Lip-ONNX (research-only CPU engine) generates Spanish talking avatar MP4 → MinIO
       ↓
7. Real TimelineCompositor / FFmpeg composites final Spanish MP4
       ↓
8. FFprobe validates video stream, audio stream, dimensions, and duration > 0
       ↓
9. Storage and OCC isolation verified
"""

import copy
import uuid
import cv2
import numpy as np
import pytest
from httpx import AsyncClient

from app.ai.adapters.piper import PiperTTSProvider
from app.ai.adapters.qwen import RealQwenLLMProvider
from app.ai.adapters.translation import RealCTranslate2TranslationProvider
from app.ai.adapters.wav2lip import Wav2LipONNXAvatarProvider
from app.ai.adapters.whisper import WhisperASRProvider
from app.core.config import get_settings
from app.core.exceptions import ConflictException
from app.db.session import async_session_factory
from app.media.compositor import TimelineCompositor
from app.media.ffprobe import FFprobeService
from app.media.workspace import MediaWorkspace
from app.models.avatar import Avatar
from app.models.brand import BrandGlossary, BrandGlossaryRule
from app.models.project import Project, ProjectVersion
from app.schemas.orchestration import GenerateProjectRequest
from app.schemas.project_document import ProjectDocumentV1, SceneAvatar
from app.services.asset_lifecycle import AssetLifecycleManager
from app.services.project_avatar_service import ProjectAvatarOrchestrator
from app.services.project_localization_service import ProjectLocalizationService
from app.services.project_service import ProjectService
from app.services.video_agent_service import VideoAgentService
from app.storage.s3 import get_storage_provider


def _create_synthetic_portrait_image_bytes(width: int = 320, height: int = 320) -> bytes:
    """Generate synthetic portrait image plate for avatar lip-sync."""
    img = np.ones((height, width, 3), dtype=np.uint8) * 230
    cv2.circle(img, (width // 2, height // 2), int(min(width, height) * 0.35), (180, 210, 240), -1)
    cv2.circle(img, (int(width * 0.4), int(height * 0.4)), 8, (50, 50, 50), -1)
    cv2.circle(img, (int(width * 0.6), int(height * 0.4)), 8, (50, 50, 50), -1)
    cv2.ellipse(img, (width // 2, int(height * 0.65)), (25, 12), 0, 0, 180, (50, 50, 180), -1)
    _, buf = cv2.imencode(".png", img)
    return buf.tobytes()


async def _setup_authenticated_env(async_client: AsyncClient) -> tuple[uuid.UUID, uuid.UUID, str]:
    """Create committed user and workspace."""
    email = f"multi_e2e_{uuid.uuid4().hex[:8]}@example.com"
    resp = await async_client.post(
        "/api/v1/auth/signup",
        json={"email": email, "display_name": "Multilingual Tester", "password": "Password123!"},
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
async def test_real_multilingual_closed_loop_pipeline(async_client: AsyncClient, monkeypatch):
    """Execute complete closed-loop multilingual pipeline without mock AI stages."""
    settings = get_settings()
    monkeypatch.setattr(settings, "AI_PROVIDER_MODE", "real")

    user_id, workspace_id, token = await _setup_authenticated_env(async_client)

    # -------------------------------------------------------------------------
    # STAGE 0: Setup Brand Glossary Rules
    # -------------------------------------------------------------------------
    async with async_session_factory() as db:
        glossary = BrandGlossary(
            workspace_id=workspace_id,
            created_by=user_id,
            name="Multilingual Brand Glossary",
            status="active",
        )
        db.add(glossary)
        await db.flush()

        rule1 = BrandGlossaryRule(
            glossary_id=glossary.id,
            source_term="HeyZen",
            preferred_term="HeyZen",
            target_language="es",
            status="active",
        )
        db.add(rule1)
        await db.commit()

    # -------------------------------------------------------------------------
    # STAGE 1: Real Qwen LLM Script & Timeline Generation (English)
    # -------------------------------------------------------------------------
    prompt = "Welcome users to HeyZen in one concise sentence."
    gen_req = GenerateProjectRequest(
        prompt=prompt,
        target_duration_seconds=5.0,
        aspect_ratio="16:9",
        voice_id="en_US-lessac-medium",
        video_tone="Professional",
        provider="qwen",
        device="cpu",
    )

    async with async_session_factory() as db:
        agent_service = VideoAgentService(db)
        en_project, en_version, _ = await agent_service.generate_project(
            workspace_id=workspace_id,
            user_id=user_id,
            request=gen_req,
        )
        await db.commit()
        en_project_id = en_project.id
        en_doc = ProjectDocumentV1.model_validate(en_version.document)

    assert en_project.revision == 1
    assert len(en_doc.scenes) >= 1
    en_scene = en_doc.scenes[0]
    assert en_scene.speech is not None
    assert len(en_scene.speech.script) > 0

    # Ensure concise deterministic script for swift CPU closed-loop execution
    en_script = en_scene.speech.script.split(".")[0].strip() + "."
    if not (10 <= len(en_script) <= 60):
        en_script = "Welcome to HeyZen video platform."

    # -------------------------------------------------------------------------
    # STAGE 2: Real CTranslate2 Translation (English -> Spanish with Glossary)
    # -------------------------------------------------------------------------
    translator = RealCTranslate2TranslationProvider()
    trans_res = await translator.translate_text(
        text=en_script,
        source_lang="en",
        target_lang="es",
        glossary_rules=[{"term": "HeyZen", "translated_term": "HeyZen"}],
    )
    assert len(trans_res.translated_text) > 0
    assert "HeyZen" in trans_res.translated_text
    es_script = trans_res.translated_text

    # Update and commit localized ProjectDocumentV1
    async with async_session_factory() as db:
        proj_service = ProjectService(db)
        es_doc = copy.deepcopy(en_doc)
        es_doc.scenes[0].speech.script = es_script
        es_doc.scenes[0].speech.voice_id = "es_ES-davefx-medium"
        es_doc.scenes[0].speech.audio_asset_id = None
        es_doc.scenes[0].subtitles = []
        es_doc.metadata["language"] = "es"
        es_doc.metadata["localized_from"] = str(en_project_id)

        v2 = await proj_service.create_version(
            project_id=en_project_id,
            workspace_id=workspace_id,
            user_id=user_id,
            document=es_doc,
            expected_revision=1,
            source="neural_translation",
        )
        await db.commit()
        assert v2.revision == 2

    # -------------------------------------------------------------------------
    # STAGE 3: Real Spanish Piper TTS Synthesis (es_ES-davefx-medium)
    # -------------------------------------------------------------------------
    piper = PiperTTSProvider()
    tts_result = await piper.synthesize_speech(
        text=es_script,
        voice_id="es_ES-davefx-medium",
    )
    assert len(tts_result.audio_bytes) > 2000
    assert tts_result.sample_rate == 22050

    async with async_session_factory() as db:
        asset_mgr = AssetLifecycleManager(db)
        audio_asset = await asset_mgr.ingest_generated_asset(
            workspace_id=workspace_id,
            created_by=user_id,
            content=tts_result.audio_bytes,
            original_filename="spanish_speech.wav",
            asset_type="audio",
            mime_type="audio/wav",
            metadata={"voice_id": "es_ES-davefx-medium", "sample_rate": tts_result.sample_rate, "language": "es"},
        )
        audio_asset_id = audio_asset.id

    # -------------------------------------------------------------------------
    # STAGE 4: Multilingual Whisper ASR Transcription (Spanish Audio)
    # -------------------------------------------------------------------------
    whisper = WhisperASRProvider()
    asr_result = await whisper.transcribe_bytes(
        audio_bytes=tts_result.audio_bytes,
        language="es",
        include_word_timestamps=True,
    )
    assert asr_result.detected_language == "es"
    assert len(asr_result.full_text) > 0
    assert len(asr_result.segments) > 0

    # -------------------------------------------------------------------------
    # STAGE 5: Real Wav2Lip-ONNX CPU Avatar Lip-Sync (Research-Only Engine)
    # -------------------------------------------------------------------------
    portrait_bytes = _create_synthetic_portrait_image_bytes(320, 320)
    async with async_session_factory() as db:
        asset_mgr = AssetLifecycleManager(db)
        image_asset = await asset_mgr.ingest_generated_asset(
            workspace_id=workspace_id,
            created_by=user_id,
            content=portrait_bytes,
            original_filename="spanish_presenter.png",
            asset_type="image",
            mime_type="image/png",
        )
        avatar = Avatar(
            workspace_id=workspace_id,
            created_by=user_id,
            name="Spanish Presenter",
            source_asset_id=image_asset.id,
            preview_asset_id=image_asset.id,
            status="ready",
        )
        db.add(avatar)
        await db.commit()
        await db.refresh(avatar)
        avatar_id = avatar.id

    # Prepare v3 document attaching audio and avatar
    async with async_session_factory() as db:
        proj_service = ProjectService(db)
        v2_doc = copy.deepcopy(es_doc)
        if v2_doc.scenes[0].avatar is None:
            v2_doc.scenes[0].avatar = SceneAvatar(avatar_id=str(avatar_id))
        else:
            v2_doc.scenes[0].avatar.avatar_id = str(avatar_id)
        v2_doc.scenes[0].speech.audio_asset_id = str(audio_asset_id)
        v2_doc.scenes[0].subtitles = asr_result.segments

        v3 = await proj_service.create_version(
            project_id=en_project_id,
            workspace_id=workspace_id,
            user_id=user_id,
            document=v2_doc,
            expected_revision=2,
            source="attach_multilingual_media",
        )
        await db.commit()
        assert v3.revision == 3

    # Generate lip-sync video using real Wav2Lip-ONNX
    async with async_session_factory() as db:
        orchestrator = ProjectAvatarOrchestrator(db)
        target_scene_id = v3.document["scenes"][0]["id"]
        v4, avatar_metrics = await orchestrator.generate_project_avatar_video(
            project_id=en_project_id,
            workspace_id=workspace_id,
            user_id=user_id,
            expected_revision=3,
            scene_id=target_scene_id,
            provider_override="wav2lip",
            device_override="cpu",
        )
        await db.commit()
        assert v4.revision == 4

    # -------------------------------------------------------------------------
    # STAGE 6: Real TimelineCompositor / FFmpeg Render
    # -------------------------------------------------------------------------
    storage = get_storage_provider()
    avatar_mp4_bytes = await storage.get_object(avatar_metrics["storage_key"])
    assert len(avatar_mp4_bytes) > 2000

    async with async_session_factory() as db:
        compositor = TimelineCompositor()
        with MediaWorkspace(prefix="multilingual_render_") as media_ws:
            render_result = await compositor.render_project(
                document=v4.document,
                workspace_id=workspace_id,
                db=db,
                media_workspace=media_ws,
            )
            assert render_result.video_path.exists()
            assert render_result.video_path.stat().st_size > 10000

            # -----------------------------------------------------------------
            # STAGE 7: FFprobe Validation
            # -----------------------------------------------------------------
            probe = render_result.probe_result
            assert len(probe.video_streams) >= 1
            assert len(probe.audio_streams) >= 1
            assert probe.width == en_project.width
            assert probe.height == en_project.height
            assert probe.duration_seconds > 0.0

    # -------------------------------------------------------------------------
    # STAGE 8: Storage and OCC Stale Revision Validation
    # -------------------------------------------------------------------------
    async with async_session_factory() as db:
        proj_service = ProjectService(db)
        with pytest.raises(ConflictException):
            await proj_service.create_version(
                project_id=en_project_id,
                workspace_id=workspace_id,
                user_id=user_id,
                document=v4.document,
                expected_revision=1,  # Stale revision (current revision is 4)
                source="stale_revision_test",
            )
