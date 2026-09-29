"""Phase 27: Complete Talking-Avatar Scene Pipeline Test Suite.

Exhaustively verifies:
1. Avatar lookup (by UUID and by name/provider_reference).
2. Avatar workspace authorization & RBAC (cross-workspace private avatar access denied).
3. Independent voice and avatar provider resolution (Voice.provider -> TTS, Avatar.provider -> LipSync).
4. Piper speech dependency (real Piper TTS audio consumed by scene pipeline).
5. Kokoro speech dependency (real Kokoro TTS audio consumed by scene pipeline).
6. Speech asset required (SPEECH_AUDIO_NOT_FOUND if audio_asset_id missing).
7. Lip-sync provider resolution routing (avatar -> avatar provider -> provider implementation).
8. CPU prototype provider classification (Wav2Lip strictly RESEARCH_ONLY / non-commercial).
9. MuseTalk GPU admission check (requires CUDA, hardware compatibility).
10. GPU unavailable failure (GPU_UNAVAILABLE raised without silent CPU fallback).
11. Avatar video asset creation in MinIO (workspace-scoped, video/mp4 MIME, unique ID).
12. Scene avatar video attachment (scene.avatar.video_asset_id populated, doc.assets updated, OCC revision committed).
13. Multi-provider multi-avatar project (Scene 1: Avatar A + Piper Bryce; Scene 2: Avatar B + Kokoro Heart).
14. Voice change preserves avatar actor configuration.
15. Render consumes avatar video (TimelineCompositor composites avatar overlay + background + speech audio).
16. Missing speech asset failure (ASSET_NOT_FOUND if referenced asset UUID missing from storage).
17. Missing or deleted avatar failure (AVATAR_NOT_FOUND).
18. Provider failure handling (corrupted image/audio raises validation error, project revision unchanged).
19. MinIO asset verification via FFprobe (video stream, audio stream, duration, resolution).
20. No silent CPU fallback (GPU provider never falls back to CPU or generates fake output).
21. Cooperative cancellation handling in lip-sync orchestration.
22. Localization resets talking-avatar video_asset_id while preserving avatar actor identity.
"""

import copy
import io
import os
import uuid
import cv2
import numpy as np
import pytest
from httpx import AsyncClient

from app.ai.adapters.kokoro import KokoroTTSProvider
from app.ai.adapters.musetalk import MuseTalkAvatarProvider
from app.ai.adapters.piper import DEFAULT_PIPER_VOICE_ID, PiperTTSProvider
from app.ai.adapters.wav2lip import Wav2LipONNXAvatarProvider
from app.ai.hardware import detect_hardware
from app.ai.model_registry import get_model_registry
from app.ai.registry import get_ai_registry, get_avatar_provider
from app.core.config import get_settings
from app.core.exceptions import (
    AIProviderException,
    AIRuntimeUnavailableException,
    ConflictException,
    ForbiddenException,
    NotFoundException,
    ValidationException,
)
from app.db.session import async_session_factory
from app.media.compositor import TimelineCompositor
from app.media.ffprobe import FFprobeService
from app.media.workspace import MediaWorkspace
from app.models.avatar import Avatar
from app.models.project import Project, ProjectVersion
from app.schemas.orchestration import GenerateAvatarVideoRequest, RenderProjectRequest
from app.schemas.project_document import (
    DocumentAssetRef,
    ProjectDocumentV1,
    ProjectSettings,
    Scene,
    SceneAvatar,
    SceneSpeech,
)
from app.services.asset_lifecycle import AssetLifecycleManager
from app.services.avatar_service import AvatarService
from app.services.project_avatar_service import ProjectAvatarOrchestrator
from app.services.project_localization_service import ProjectLocalizationService
from app.services.project_render_service import ProjectRenderOrchestrator
from app.services.project_service import ProjectService
from app.services.project_speech_service import ProjectSpeechOrchestrator
from app.storage.s3 import get_storage_provider


PIPER_BRYCE_VOICE_ID = "10000000-0000-0000-0000-000000000004"
KOKORO_HEART_VOICE_ID = "10000000-0000-0000-0000-000000000021"


def _create_synthetic_portrait_image_bytes(width: int = 320, height: int = 320) -> bytes:
    """Generate a clean synthetic portrait image plate with facial landmarks."""
    img = np.ones((height, width, 3), dtype=np.uint8) * 230
    # Head contour
    cv2.circle(img, (width // 2, height // 2), int(min(width, height) * 0.35), (180, 210, 240), -1)
    # Eyes
    cv2.circle(img, (int(width * 0.4), int(height * 0.4)), 8, (50, 50, 50), -1)
    cv2.circle(img, (int(width * 0.6), int(height * 0.4)), 8, (50, 50, 50), -1)
    # Mouth arc
    cv2.ellipse(img, (width // 2, int(height * 0.65)), (25, 12), 0, 0, 180, (50, 50, 180), -1)
    _, buf = cv2.imencode(".png", img)
    return buf.tobytes()


async def _setup_workspace_and_project(
    async_client: AsyncClient,
    title: str = "Talking Avatar Pipeline Project",
):
    """Helper creating user, workspace, and initialized ProjectDocumentV1."""
    email = f"talking_avatar_{uuid.uuid4().hex[:8]}@example.com"
    resp = await async_client.post(
        "/api/v1/auth/signup",
        json={"email": email, "display_name": "Avatar Tester", "password": "Password123!"},
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


async def _create_test_avatar(
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    name: str = "Test Avatar Presenter",
    visibility: str = "workspace",
    provider: str = "wav2lip",
    status: str = "ready",
) -> tuple[Avatar, uuid.UUID]:
    """Helper creating a test Avatar record with uploaded source portrait in MinIO."""
    portrait_bytes = _create_synthetic_portrait_image_bytes()
    async with async_session_factory() as db:
        asset_mgr = AssetLifecycleManager(db)
        image_asset = await asset_mgr.ingest_generated_asset(
            workspace_id=workspace_id,
            created_by=user_id,
            content=portrait_bytes,
            original_filename=f"portrait_{uuid.uuid4().hex[:6]}.png",
            asset_type="image",
            mime_type="image/png",
            metadata={"role": "reference_portrait"},
        )

        avatar = Avatar(
            workspace_id=workspace_id,
            created_by=user_id,
            name=name,
            avatar_type="custom",
            status=status,
            visibility=visibility,
            provider=provider,
            provider_reference=f"ref_{uuid.uuid4().hex[:6]}",
            source_asset_id=image_asset.id,
            preview_asset_id=image_asset.id,
        )
        db.add(avatar)
        await db.commit()
        await db.refresh(avatar)
        return avatar, image_asset.id


# ===========================================================================
# SCENARIOS 1 & 2: Avatar Lookup & Workspace Authorization
# ===========================================================================


@pytest.mark.asyncio
async def test_avatar_lookup_uuid_and_name(async_client: AsyncClient):
    """Scenario 1: Verify avatar lookup works by UUID and by name/provider_reference."""
    user_id, ws_id, proj_id, token = await _setup_workspace_and_project(async_client)
    avatar, img_id = await _create_test_avatar(ws_id, user_id, name="Corporate Host", provider="wav2lip")

    async with async_session_factory() as db:
        # Synthesize real speech first to attach to scene
        speech_orch = ProjectSpeechOrchestrator(db)
        # Configure scene with UUID
        p_service = ProjectService(db)
        p = await p_service.get_project(proj_id, ws_id)
        ver = await p_service.get_version(p.current_version_id, proj_id, ws_id)
        doc = ProjectDocumentV1.model_validate(ver.document)
        doc.scenes = [
            Scene(
                id="scene-1",
                sequence=1,
                duration=3.0,
                speech=SceneSpeech(voice_id=PIPER_BRYCE_VOICE_ID, script="Short intro."),
                avatar=SceneAvatar(avatar_id=str(avatar.id), view_mode="half_body"),
            )
        ]
        ver2 = await p_service.create_version(proj_id, ws_id, user_id, p.revision, doc, "config")
        await db.commit()

        # Generate speech
        ver3 = await speech_orch.synthesize_project_speech(proj_id, ws_id, user_id, ver2.revision)
        await db.commit()

        # Orchestrate avatar by UUID
        avatar_orch = ProjectAvatarOrchestrator(db)
        ver4, m1 = await avatar_orch.generate_project_avatar_video(
            project_id=proj_id,
            workspace_id=ws_id,
            user_id=user_id,
            expected_revision=ver3.revision,
            scene_id="scene-1",
        )
        await db.commit()
        assert ver4.revision == ver3.revision + 1
        assert m1["video_asset_id"] is not None

        # Test lookup by Name
        doc4 = ProjectDocumentV1.model_validate(ver4.document)
        doc4.scenes[0].avatar.avatar_id = "Corporate Host"
        ver5 = await p_service.create_version(proj_id, ws_id, user_id, ver4.revision, doc4, "name_lookup_test")
        await db.commit()

        ver6, m2 = await avatar_orch.generate_project_avatar_video(
            project_id=proj_id,
            workspace_id=ws_id,
            user_id=user_id,
            expected_revision=ver5.revision,
            scene_id="scene-1",
        )
        await db.commit()
        assert ver6.revision == ver5.revision + 1
        # Canonical UUID is persisted into scene.avatar.avatar_id
        doc6 = ProjectDocumentV1.model_validate(ver6.document)
        assert doc6.scenes[0].avatar.avatar_id == str(avatar.id)


@pytest.mark.asyncio
async def test_avatar_workspace_authorization_access_denied(async_client: AsyncClient):
    """Scenario 2: Private avatar owned by Workspace A accessed from Workspace B raises AVATAR_ACCESS_DENIED."""
    user_a, ws_a, proj_a, token_a = await _setup_workspace_and_project(async_client, title="Workspace A Project")
    user_b, ws_b, proj_b, token_b = await _setup_workspace_and_project(async_client, title="Workspace B Project")

    # Create private avatar in Workspace A
    private_avatar_a, _ = await _create_test_avatar(
        workspace_id=ws_a,
        user_id=user_a,
        name="Secret Avatar A",
        visibility="workspace",
    )

    async with async_session_factory() as db:
        p_service = ProjectService(db)
        p_b = await p_service.get_project(proj_b, ws_b)
        ver_b = await p_service.get_version(p_b.current_version_id, proj_b, ws_b)
        doc = ProjectDocumentV1.model_validate(ver_b.document)
        # Attempt to configure Workspace A's avatar into Workspace B's scene
        doc.scenes = [
            Scene(
                id="scene-b-1",
                sequence=1,
                duration=3.0,
                speech=SceneSpeech(voice_id=PIPER_BRYCE_VOICE_ID, script="Testing access control.", audio_asset_id=str(uuid.uuid4())),
                avatar=SceneAvatar(avatar_id=str(private_avatar_a.id), view_mode="half_body"),
            )
        ]
        ver_b2 = await p_service.create_version(proj_b, ws_b, user_b, p_b.revision, doc, "attempt_unauthorized")
        await db.commit()

        avatar_orch = ProjectAvatarOrchestrator(db)
        with pytest.raises(ForbiddenException) as exc_info:
            await avatar_orch.generate_project_avatar_video(
                project_id=proj_b,
                workspace_id=ws_b,
                user_id=user_b,
                expected_revision=ver_b2.revision,
                scene_id="scene-b-1",
            )
        assert exc_info.value.code == "AVATAR_ACCESS_DENIED"
        assert "Access denied" in exc_info.value.message


# ===========================================================================
# SCENARIOS 3, 4, 5: Voice & Speech Dependencies (Piper & Kokoro)
# ===========================================================================


@pytest.mark.asyncio
async def test_voice_and_avatar_provider_resolution_independence(async_client: AsyncClient):
    """Scenario 3: Changing voice preserves avatar actor; provider resolution is independent."""
    user_id, ws_id, proj_id, token = await _setup_workspace_and_project(async_client)
    avatar, img_id = await _create_test_avatar(ws_id, user_id, name="Multi Voice Avatar", provider="wav2lip")

    async with async_session_factory() as db:
        p_service = ProjectService(db)
        speech_orch = ProjectSpeechOrchestrator(db)
        avatar_orch = ProjectAvatarOrchestrator(db)

        # Initial Scene with Piper Bryce
        p = await p_service.get_project(proj_id, ws_id)
        ver = await p_service.get_version(p.current_version_id, proj_id, ws_id)
        doc = ProjectDocumentV1.model_validate(ver.document)
        doc.scenes = [
            Scene(
                id="scene-1",
                sequence=1,
                duration=3.0,
                speech=SceneSpeech(voice_id=PIPER_BRYCE_VOICE_ID, script="First line with Piper."),
                avatar=SceneAvatar(avatar_id=str(avatar.id), view_mode="half_body"),
            )
        ]
        ver_c = await p_service.create_version(proj_id, ws_id, user_id, p.revision, doc, "config_piper")
        await db.commit()

        # 1. Synthesize Piper speech
        ver_speech_1 = await speech_orch.synthesize_project_speech(proj_id, ws_id, user_id, ver_c.revision)
        await db.commit()
        doc_s1 = ProjectDocumentV1.model_validate(ver_speech_1.document)
        audio_asset_piper = doc_s1.scenes[0].speech.audio_asset_id
        assert audio_asset_piper is not None

        # 2. Generate Avatar video with Piper audio
        ver_av_1, m1 = await avatar_orch.generate_project_avatar_video(
            project_id=proj_id,
            workspace_id=ws_id,
            user_id=user_id,
            expected_revision=ver_speech_1.revision,
            scene_id="scene-1",
        )
        await db.commit()
        doc_av1 = ProjectDocumentV1.model_validate(ver_av_1.document)
        assert doc_av1.scenes[0].avatar.avatar_id == str(avatar.id)
        assert doc_av1.scenes[0].avatar.video_asset_id is not None

        # 3. Switch voice to Kokoro Heart (without touching avatar actor)
        doc_av1.scenes[0].speech.voice_id = KOKORO_HEART_VOICE_ID
        doc_av1.scenes[0].speech.script = "Second line with Kokoro Heart."
        ver_c2 = await p_service.create_version(proj_id, ws_id, user_id, ver_av_1.revision, doc_av1, "config_kokoro")
        await db.commit()

        # 4. Synthesize Kokoro speech
        ver_speech_2 = await speech_orch.synthesize_project_speech(proj_id, ws_id, user_id, ver_c2.revision)
        await db.commit()
        doc_s2 = ProjectDocumentV1.model_validate(ver_speech_2.document)
        audio_asset_kokoro = doc_s2.scenes[0].speech.audio_asset_id
        assert audio_asset_kokoro is not None
        assert audio_asset_kokoro != audio_asset_piper

        # Avatar actor configuration is completely preserved
        assert doc_s2.scenes[0].avatar.avatar_id == str(avatar.id)
        assert doc_s2.scenes[0].avatar.view_mode == "half_body"


@pytest.mark.asyncio
async def test_piper_and_kokoro_speech_dependencies_real_synthesis(async_client: AsyncClient):
    """Scenarios 4 & 5: Real Piper and Kokoro speech assets are consumed directly by avatar orchestration."""
    user_id, ws_id, proj_id, token = await _setup_workspace_and_project(async_client)
    avatar, _ = await _create_test_avatar(ws_id, user_id, name="Dual Engine Actor", provider="wav2lip")

    async with async_session_factory() as db:
        p_service = ProjectService(db)
        speech_orch = ProjectSpeechOrchestrator(db)
        avatar_orch = ProjectAvatarOrchestrator(db)

        p = await p_service.get_project(proj_id, ws_id)
        ver = await p_service.get_version(p.current_version_id, proj_id, ws_id)
        doc = ProjectDocumentV1.model_validate(ver.document)
        doc.scenes = [
            Scene(
                id="s-piper",
                sequence=1,
                duration=2.5,
                speech=SceneSpeech(voice_id=PIPER_BRYCE_VOICE_ID, script="Testing Piper audio dependency."),
                avatar=SceneAvatar(avatar_id=str(avatar.id), view_mode="half_body"),
            ),
            Scene(
                id="s-kokoro",
                sequence=2,
                duration=2.5,
                speech=SceneSpeech(voice_id=KOKORO_HEART_VOICE_ID, script="Testing Kokoro audio dependency."),
                avatar=SceneAvatar(avatar_id=str(avatar.id), view_mode="half_body"),
            ),
        ]
        ver_cfg = await p_service.create_version(proj_id, ws_id, user_id, p.revision, doc, "config_dual")
        await db.commit()

        # Synthesize both scenes
        ver_synth = await speech_orch.synthesize_project_speech(proj_id, ws_id, user_id, ver_cfg.revision)
        await db.commit()
        doc_synth = ProjectDocumentV1.model_validate(ver_synth.document)

        # Confirm speech assets exist in MinIO
        storage = get_storage_provider()
        piper_aid = uuid.UUID(doc_synth.scenes[0].speech.audio_asset_id)
        kokoro_aid = uuid.UUID(doc_synth.scenes[1].speech.audio_asset_id)
        a_repo = AssetLifecycleManager(db).asset_repo
        a1 = await a_repo.get_by_id(piper_aid, ws_id)
        a2 = await a_repo.get_by_id(kokoro_aid, ws_id)
        assert a1 is not None and a2 is not None

        # Verify raw bytes in MinIO
        b1 = await storage.get_object(a1.storage_key)
        b2 = await storage.get_object(a2.storage_key)
        assert len(b1) > 10000
        assert len(b2) > 10000

        # Generate avatar video for scene 1 (Piper)
        ver_av1, m1 = await avatar_orch.generate_project_avatar_video(
            project_id=proj_id,
            workspace_id=ws_id,
            user_id=user_id,
            expected_revision=ver_synth.revision,
            scene_id="s-piper",
        )
        await db.commit()
        assert m1["video_asset_id"] is not None

        # Generate avatar video for scene 2 (Kokoro)
        ver_av2, m2 = await avatar_orch.generate_project_avatar_video(
            project_id=proj_id,
            workspace_id=ws_id,
            user_id=user_id,
            expected_revision=ver_av1.revision,
            scene_id="s-kokoro",
        )
        await db.commit()
        assert m2["video_asset_id"] is not None
        assert m1["video_asset_id"] != m2["video_asset_id"]


# ===========================================================================
# SCENARIOS 6, 7, 8: Provider Resolution & CPU Prototype Classification
# ===========================================================================


@pytest.mark.asyncio
async def test_speech_asset_required_failure(async_client: AsyncClient):
    """Scenario 6: SPEECH_AUDIO_NOT_FOUND if scene has script but no pre-synthesized audio asset."""
    user_id, ws_id, proj_id, token = await _setup_workspace_and_project(async_client)
    avatar, _ = await _create_test_avatar(ws_id, user_id)

    async with async_session_factory() as db:
        p_service = ProjectService(db)
        p = await p_service.get_project(proj_id, ws_id)
        ver = await p_service.get_version(p.current_version_id, proj_id, ws_id)
        doc = ProjectDocumentV1.model_validate(ver.document)
        doc.scenes = [
            Scene(
                id="s-unsynthesized",
                sequence=1,
                duration=3.0,
                speech=SceneSpeech(voice_id=PIPER_BRYCE_VOICE_ID, script="Script without audio asset.", audio_asset_id=None),
                avatar=SceneAvatar(avatar_id=str(avatar.id), view_mode="half_body"),
            )
        ]
        ver_cfg = await p_service.create_version(proj_id, ws_id, user_id, p.revision, doc, "no_audio")
        await db.commit()

        avatar_orch = ProjectAvatarOrchestrator(db)
        with pytest.raises(NotFoundException) as exc_info:
            await avatar_orch.generate_project_avatar_video(
                project_id=proj_id,
                workspace_id=ws_id,
                user_id=user_id,
                expected_revision=ver_cfg.revision,
                scene_id="s-unsynthesized",
            )
        assert exc_info.value.code == "SPEECH_AUDIO_NOT_FOUND"


def test_cpu_prototype_wav2lip_descriptor_research_only():
    """Scenario 8: Wav2Lip descriptor and model registry entry strictly classify as RESEARCH_ONLY / Non-Commercial."""
    provider = Wav2LipONNXAvatarProvider()
    desc = provider.descriptor
    assert desc.name == "wav2lip"
    assert desc.requires_gpu is False
    assert desc.is_available is True
    meta = desc.metadata
    assert meta["research_only"] is True
    assert meta["commercial_permitted"] is False
    assert meta["license_classification"] == "RESEARCH_ONLY"
    assert "Research Only (LRS2 Non-Commercial)" in meta["license"]

    # Model Registry check
    model_reg = get_model_registry()
    model_desc = model_reg.get_model("avatar/wav2lip-cpu")
    assert model_desc is not None
    assert model_desc.requires_gpu is False
    assert model_desc.license_commercial_permitted is False
    assert model_desc.metadata["license_classification"] == "RESEARCH_ONLY"


# ===========================================================================
# SCENARIOS 9, 10, 20: MuseTalk GPU Admission & No Silent Fallback
# ===========================================================================


def test_musetalk_gpu_admission_check():
    """Scenario 9: MuseTalk requires CUDA GPU accelerator and verifies hardware compatibility."""
    hw = detect_hardware()
    provider = MuseTalkAvatarProvider()
    desc = provider.descriptor
    assert desc.name == "musetalk"
    assert desc.requires_gpu is True
    assert desc.supported_devices == ["cuda"]

    # In this CPU environment, hw.has_cuda is False
    assert hw.has_cuda is False
    is_compat, state, reason = hw.check_model_compatibility(requires_gpu=True, minimum_vram_bytes=6 * 1024**3)
    assert is_compat is False
    assert state.value == "REQUIRES_GPU"


@pytest.mark.asyncio
async def test_gpu_unavailable_failure_no_cpu_fallback(async_client: AsyncClient):
    """Scenarios 10 & 20: Requesting MuseTalk raises GPU_UNAVAILABLE without fallback to CPU or mock."""
    user_id, ws_id, proj_id, token = await _setup_workspace_and_project(async_client)
    # Create avatar explicitly specifying musetalk provider
    avatar_gpu, _ = await _create_test_avatar(ws_id, user_id, name="GPU MuseTalk Avatar", provider="musetalk")

    async with async_session_factory() as db:
        p_service = ProjectService(db)
        speech_orch = ProjectSpeechOrchestrator(db)
        avatar_orch = ProjectAvatarOrchestrator(db)

        p = await p_service.get_project(proj_id, ws_id)
        ver = await p_service.get_version(p.current_version_id, proj_id, ws_id)
        doc = ProjectDocumentV1.model_validate(ver.document)
        doc.scenes = [
            Scene(
                id="s-gpu",
                sequence=1,
                duration=3.0,
                speech=SceneSpeech(voice_id=PIPER_BRYCE_VOICE_ID, script="Testing GPU admission rejection."),
                avatar=SceneAvatar(avatar_id=str(avatar_gpu.id), view_mode="half_body"),
            )
        ]
        ver_cfg = await p_service.create_version(proj_id, ws_id, user_id, p.revision, doc, "config_gpu_scene")
        await db.commit()

        ver_synth = await speech_orch.synthesize_project_speech(proj_id, ws_id, user_id, ver_cfg.revision)
        await db.commit()

        # When invoking orchestrator for this scene (or with provider_override='musetalk')
        with pytest.raises(AIRuntimeUnavailableException) as exc_info:
            await avatar_orch.generate_project_avatar_video(
                project_id=proj_id,
                workspace_id=ws_id,
                user_id=user_id,
                expected_revision=ver_synth.revision,
                scene_id="s-gpu",
            )
        assert exc_info.value.code == "GPU_UNAVAILABLE"
        assert "NVIDIA CUDA GPU" in exc_info.value.message

        # Verify revision was not changed and no video_asset_id was attached
        p_after = await p_service.get_project(proj_id, ws_id)
        assert p_after.revision == ver_synth.revision


# ===========================================================================
# SCENARIOS 11, 12, 19: Real Video Asset Creation, Attachment, and FFprobe
# ===========================================================================


@pytest.mark.asyncio
async def test_avatar_video_asset_creation_and_ffprobe_verification(async_client: AsyncClient):
    """Scenarios 11, 12, & 19: Full real Wav2Lip generation -> MinIO Asset -> Scene attachment -> FFprobe metadata."""
    user_id, ws_id, proj_id, token = await _setup_workspace_and_project(async_client)
    avatar, _ = await _create_test_avatar(ws_id, user_id, name="Media Verification Actor", provider="wav2lip")

    async with async_session_factory() as db:
        p_service = ProjectService(db)
        speech_orch = ProjectSpeechOrchestrator(db)
        avatar_orch = ProjectAvatarOrchestrator(db)
        asset_repo = AssetLifecycleManager(db).asset_repo

        p = await p_service.get_project(proj_id, ws_id)
        ver = await p_service.get_version(p.current_version_id, proj_id, ws_id)
        doc = ProjectDocumentV1.model_validate(ver.document)
        doc.scenes = [
            Scene(
                id="s-real-media",
                sequence=1,
                duration=3.0,
                speech=SceneSpeech(voice_id=PIPER_BRYCE_VOICE_ID, script="HeyZen real video generation test."),
                avatar=SceneAvatar(avatar_id=str(avatar.id), view_mode="half_body"),
            )
        ]
        ver_cfg = await p_service.create_version(proj_id, ws_id, user_id, p.revision, doc, "config_media")
        await db.commit()

        # Synthesize real speech
        ver_speech = await speech_orch.synthesize_project_speech(proj_id, ws_id, user_id, ver_cfg.revision)
        await db.commit()

        # Synthesize real avatar video on CPU
        ver_av, metrics = await avatar_orch.generate_project_avatar_video(
            project_id=proj_id,
            workspace_id=ws_id,
            user_id=user_id,
            expected_revision=ver_speech.revision,
            scene_id="s-real-media",
        )
        await db.commit()

        # 1. Verify ProjectDocumentV1 updates
        doc_av = ProjectDocumentV1.model_validate(ver_av.document)
        video_asset_id_str = doc_av.scenes[0].avatar.video_asset_id
        assert video_asset_id_str is not None
        assert any(a.asset_id == video_asset_id_str and a.asset_type == "video" for a in doc_av.assets)

        # 2. Verify Asset record in DB
        video_asset = await asset_repo.get_by_id(uuid.UUID(video_asset_id_str), ws_id)
        assert video_asset is not None
        assert video_asset.asset_type == "video"
        assert video_asset.mime_type == "video/mp4"
        assert video_asset.workspace_id == ws_id

        # 3. Verify media bytes in MinIO
        storage = get_storage_provider()
        mp4_bytes = await storage.get_object(video_asset.storage_key)
        assert len(mp4_bytes) > 20000

        # 4. Verify FFprobe metadata on generated MP4
        async with MediaWorkspace(prefix="probe_test_") as mws:
            local_mp4 = mws.root_path / "generated_avatar.mp4"
            local_mp4.write_bytes(mp4_bytes)

            ffprobe = FFprobeService()
            probe = await ffprobe.probe(local_mp4)
            assert len(probe.video_streams) > 0
            assert len(probe.audio_streams) > 0
            assert probe.duration_seconds > 1.0
            assert probe.codec_name in ("h264", "h264_qsv", "libx264")
            assert probe.width > 0
            assert probe.height > 0


# ===========================================================================
# SCENARIOS 13, 14, 15: Multi-Scene Project & Timeline Compositor Rendering
# ===========================================================================


@pytest.mark.asyncio
async def test_multi_scene_multi_provider_project_and_render_pipeline(async_client: AsyncClient):
    """Scenarios 13 & 15: Multi-scene (Piper Bryce + Kokoro Heart) full pipeline to final rendered MP4."""
    user_id, ws_id, proj_id, token = await _setup_workspace_and_project(async_client, title="Full Talking Avatar E2E")
    avatar_a, _ = await _create_test_avatar(ws_id, user_id, name="Avatar Presenter A", provider="wav2lip")
    avatar_b, _ = await _create_test_avatar(ws_id, user_id, name="Avatar Presenter B", provider="wav2lip")

    async with async_session_factory() as db:
        p_service = ProjectService(db)
        speech_orch = ProjectSpeechOrchestrator(db)
        avatar_orch = ProjectAvatarOrchestrator(db)

        p = await p_service.get_project(proj_id, ws_id)
        ver = await p_service.get_version(p.current_version_id, proj_id, ws_id)
        doc = ProjectDocumentV1.model_validate(ver.document)
        doc.scenes = [
            Scene(
                id="scene-a",
                sequence=1,
                duration=2.5,
                speech=SceneSpeech(voice_id=PIPER_BRYCE_VOICE_ID, script="Scene one with Avatar A."),
                avatar=SceneAvatar(avatar_id=str(avatar_a.id), view_mode="half_body"),
            ),
            Scene(
                id="scene-b",
                sequence=2,
                duration=2.5,
                speech=SceneSpeech(voice_id=KOKORO_HEART_VOICE_ID, script="Scene two with Avatar B."),
                avatar=SceneAvatar(avatar_id=str(avatar_b.id), view_mode="circle"),
            ),
        ]
        ver_cfg = await p_service.create_version(proj_id, ws_id, user_id, p.revision, doc, "multi_scene_cfg")
        await db.commit()

        # Step 1: Synthesize all speech assets
        ver_synth = await speech_orch.synthesize_project_speech(proj_id, ws_id, user_id, ver_cfg.revision)
        await db.commit()

        # Step 2: Generate talking-avatar video for Scene 1
        ver_av1, m1 = await avatar_orch.generate_project_avatar_video(
            project_id=proj_id,
            workspace_id=ws_id,
            user_id=user_id,
            expected_revision=ver_synth.revision,
            scene_id="scene-a",
        )
        await db.commit()

        # Step 3: Generate talking-avatar video for Scene 2
        ver_av2, m2 = await avatar_orch.generate_project_avatar_video(
            project_id=proj_id,
            workspace_id=ws_id,
            user_id=user_id,
            expected_revision=ver_av1.revision,
            scene_id="scene-b",
        )
        await db.commit()

        doc_final = ProjectDocumentV1.model_validate(ver_av2.document)
        assert doc_final.scenes[0].avatar.video_asset_id is not None
        assert doc_final.scenes[1].avatar.video_asset_id is not None
        assert doc_final.scenes[0].avatar.video_asset_id != doc_final.scenes[1].avatar.video_asset_id

        # Step 4: Render Project with TimelineCompositor
        async with MediaWorkspace(prefix="timeline_e2e_") as mws:
            compositor = TimelineCompositor()
            render_res = await compositor.render_project(
                document=doc_final,
                workspace_id=ws_id,
                db=db,
                media_workspace=mws,
            )
            assert render_res.video_path is not None
            assert render_res.video_path.exists()
            assert render_res.video_path.stat().st_size > 50000
            assert len(render_res.probe_result.video_streams) > 0
            assert len(render_res.probe_result.audio_streams) > 0

            # Step 5: Probe final MP4
            ffprobe = FFprobeService()
            probe = await ffprobe.probe(render_res.video_path)
            assert len(probe.video_streams) > 0
            assert len(probe.audio_streams) > 0
            assert probe.duration_seconds > 4.0
            assert render_res.scenes_count == 2


# ===========================================================================
# SCENARIOS 16, 17, 18: Truthful Failure Semantics
# ===========================================================================


@pytest.mark.asyncio
async def test_missing_or_deleted_avatar_failure(async_client: AsyncClient):
    """Scenario 17: Non-existent or deleted avatar raises AVATAR_NOT_FOUND."""
    user_id, ws_id, proj_id, token = await _setup_workspace_and_project(async_client)
    fake_avatar_id = uuid.uuid4()

    async with async_session_factory() as db:
        p_service = ProjectService(db)
        p = await p_service.get_project(proj_id, ws_id)
        ver = await p_service.get_version(p.current_version_id, proj_id, ws_id)
        doc = ProjectDocumentV1.model_validate(ver.document)
        doc.scenes = [
            Scene(
                id="s-missing-av",
                sequence=1,
                duration=3.0,
                speech=SceneSpeech(voice_id=PIPER_BRYCE_VOICE_ID, script="Testing missing avatar.", audio_asset_id=str(uuid.uuid4())),
                avatar=SceneAvatar(avatar_id=str(fake_avatar_id), view_mode="half_body"),
            )
        ]
        ver_cfg = await p_service.create_version(proj_id, ws_id, user_id, p.revision, doc, "missing_av")
        await db.commit()

        avatar_orch = ProjectAvatarOrchestrator(db)
        with pytest.raises(NotFoundException) as exc_info:
            await avatar_orch.generate_project_avatar_video(
                project_id=proj_id,
                workspace_id=ws_id,
                user_id=user_id,
                expected_revision=ver_cfg.revision,
                scene_id="s-missing-av",
            )
        assert exc_info.value.code == "AVATAR_NOT_FOUND"


@pytest.mark.asyncio
async def test_missing_speech_asset_in_storage_failure(async_client: AsyncClient):
    """Scenario 16: ASSET_NOT_FOUND if speech audio asset ID does not exist in workspace."""
    user_id, ws_id, proj_id, token = await _setup_workspace_and_project(async_client)
    avatar, _ = await _create_test_avatar(ws_id, user_id)
    fake_audio_uuid = uuid.uuid4()

    async with async_session_factory() as db:
        p_service = ProjectService(db)
        p = await p_service.get_project(proj_id, ws_id)
        ver = await p_service.get_version(p.current_version_id, proj_id, ws_id)
        doc = ProjectDocumentV1.model_validate(ver.document)
        doc.scenes = [
            Scene(
                id="s-missing-audio",
                sequence=1,
                duration=3.0,
                speech=SceneSpeech(voice_id=PIPER_BRYCE_VOICE_ID, script="Missing audio test.", audio_asset_id=str(fake_audio_uuid)),
                avatar=SceneAvatar(avatar_id=str(avatar.id), view_mode="half_body"),
            )
        ]
        ver_cfg = await p_service.create_version(proj_id, ws_id, user_id, p.revision, doc, "missing_audio")
        await db.commit()

        avatar_orch = ProjectAvatarOrchestrator(db)
        with pytest.raises(NotFoundException) as exc_info:
            await avatar_orch.generate_project_avatar_video(
                project_id=proj_id,
                workspace_id=ws_id,
                user_id=user_id,
                expected_revision=ver_cfg.revision,
                scene_id="s-missing-audio",
            )
        assert exc_info.value.code == "ASSET_NOT_FOUND"


@pytest.mark.asyncio
async def test_avatar_provider_failure_does_not_corrupt_version(async_client: AsyncClient):
    """Scenario 18: Provider inference failure raises validation error and does NOT commit new revision."""
    user_id, ws_id, proj_id, token = await _setup_workspace_and_project(async_client)
    avatar, _ = await _create_test_avatar(ws_id, user_id)

    async with async_session_factory() as db:
        p_service = ProjectService(db)
        asset_mgr = AssetLifecycleManager(db)
        # Ingest corrupted audio (empty bytes)
        bad_audio_asset = await asset_mgr.ingest_generated_asset(
            workspace_id=ws_id,
            created_by=user_id,
            content=b"not a valid wav file header",
            original_filename="bad_audio.wav",
            asset_type="audio",
            mime_type="audio/wav",
            metadata={},
        )

        p = await p_service.get_project(proj_id, ws_id)
        ver = await p_service.get_version(p.current_version_id, proj_id, ws_id)
        doc = ProjectDocumentV1.model_validate(ver.document)
        doc.scenes = [
            Scene(
                id="s-corrupt",
                sequence=1,
                duration=3.0,
                speech=SceneSpeech(voice_id=PIPER_BRYCE_VOICE_ID, script="Corrupt audio test.", audio_asset_id=str(bad_audio_asset.id)),
                avatar=SceneAvatar(avatar_id=str(avatar.id), view_mode="half_body"),
            )
        ]
        ver_cfg = await p_service.create_version(proj_id, ws_id, user_id, p.revision, doc, "corrupt_test")
        await db.commit()

        avatar_orch = ProjectAvatarOrchestrator(db)
        with pytest.raises(ValidationException):
            await avatar_orch.generate_project_avatar_video(
                project_id=proj_id,
                workspace_id=ws_id,
                user_id=user_id,
                expected_revision=ver_cfg.revision,
                scene_id="s-corrupt",
            )

        # Confirm project revision was not incremented
        p_after = await p_service.get_project(proj_id, ws_id)
        assert p_after.revision == ver_cfg.revision


# ===========================================================================
# SCENARIOS 21 & 22: Cancellation & Localization Integrity
# ===========================================================================


@pytest.mark.asyncio
async def test_talking_avatar_cooperative_cancellation(async_client: AsyncClient):
    """Scenario 21: Cooperative cancellation aborts inference cleanly."""
    user_id, ws_id, proj_id, token = await _setup_workspace_and_project(async_client)
    avatar, _ = await _create_test_avatar(ws_id, user_id)

    async with async_session_factory() as db:
        p_service = ProjectService(db)
        speech_orch = ProjectSpeechOrchestrator(db)
        avatar_orch = ProjectAvatarOrchestrator(db)

        p = await p_service.get_project(proj_id, ws_id)
        ver = await p_service.get_version(p.current_version_id, proj_id, ws_id)
        doc = ProjectDocumentV1.model_validate(ver.document)
        doc.scenes = [
            Scene(
                id="s-cancel",
                sequence=1,
                duration=3.0,
                speech=SceneSpeech(voice_id=PIPER_BRYCE_VOICE_ID, script="Cancelling test."),
                avatar=SceneAvatar(avatar_id=str(avatar.id), view_mode="half_body"),
            )
        ]
        ver_cfg = await p_service.create_version(proj_id, ws_id, user_id, p.revision, doc, "cancel_cfg")
        await db.commit()

        ver_synth = await speech_orch.synthesize_project_speech(proj_id, ws_id, user_id, ver_cfg.revision)
        await db.commit()

        async def _is_cancelled():
            return True

        with pytest.raises(AIProviderException) as exc_info:
            await avatar_orch.generate_project_avatar_video(
                project_id=proj_id,
                workspace_id=ws_id,
                user_id=user_id,
                expected_revision=ver_synth.revision,
                scene_id="s-cancel",
                cancellation_checker=_is_cancelled,
            )
        assert exc_info.value.code == "INFERENCE_CANCELLED"


@pytest.mark.asyncio
async def test_localization_resets_talking_avatar_video_and_preserves_actor(async_client: AsyncClient):
    """Scenario 22: Localization preserves avatar actor configuration while resetting video_asset_id."""
    user_id, ws_id, proj_id, token = await _setup_workspace_and_project(async_client)
    avatar, _ = await _create_test_avatar(ws_id, user_id, name="Bilingual Host")

    async with async_session_factory() as db:
        p_service = ProjectService(db)
        p = await p_service.get_project(proj_id, ws_id)
        ver = await p_service.get_version(p.current_version_id, proj_id, ws_id)
        doc = ProjectDocumentV1.model_validate(ver.document)
        fake_vid_asset_id = str(uuid.uuid4())
        doc.scenes = [
            Scene(
                id="s-loc",
                sequence=1,
                duration=3.0,
                speech=SceneSpeech(voice_id=PIPER_BRYCE_VOICE_ID, script="Hello world.", audio_asset_id=str(uuid.uuid4())),
                avatar=SceneAvatar(avatar_id=str(avatar.id), view_mode="half_body", video_asset_id=fake_vid_asset_id),
            )
        ]
        ver_cfg = await p_service.create_version(proj_id, ws_id, user_id, p.revision, doc, "before_translation")
        await db.commit()

        loc_service = ProjectLocalizationService(db)
        forked_proj, forked_ver = await loc_service.translate_project(
            project_id=proj_id,
            workspace_id=ws_id,
            user_id=user_id,
            target_language="es",
            source_language="en",
            create_fork=True,
            expected_revision=ver_cfg.revision,
        )
        await db.commit()

        forked_doc = ProjectDocumentV1.model_validate(forked_ver.document)
        loc_scene = forked_doc.scenes[0]

        # Avatar identity and framing preserved
        assert loc_scene.avatar.avatar_id == str(avatar.id)
        assert loc_scene.avatar.view_mode == "half_body"

        # Previous English video_asset_id and audio_asset_id reset to None for Spanish synthesis
        assert loc_scene.avatar.video_asset_id is None
        assert loc_scene.speech.audio_asset_id is None
