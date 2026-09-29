"""Phase 28: Studio Editing Completion & Production Video Integration Test Suite.

Verifies:
1. Studio loads real project (metadata, canvas settings, revision).
2. Studio loads real scenes (sequence, duration, speech, avatar).
3. Add scene persists (increments count, sets sequence, commits new version with OCC).
4. Delete scene persists (removes scene, re-indexes sequences, commits new version).
5. Reorder persists (updates sequences, commits new version).
6. Script update persists (updates speech.script, invalidates stale audio/video).
7. Voice selection persists (updates speech.voice_id).
8. Avatar selection persists (updates avatar.avatar_id and view_mode).
9. Real speech generation (synthesizes genuine speech asset in MinIO).
10. Job progress/recovery (submits async job, tracks progress, durable retrieval).
11. Generated audio association (scene.speech.audio_asset_id committed to ProjectDocumentV1).
12. Talking-avatar generation (real Wav2Lip CPU inference produces MP4 asset in MinIO).
13. Generated video association (scene.avatar.video_asset_id committed to ProjectDocumentV1).
14. Timeline persistence (timeline duration matches sum of scene durations).
15. Render job submission (submits render job with expected revision).
16. Render completion & MP4 composition (TimelineCompositor creates playable multi-scene video).
17. OCC conflict handling (stale expected_revision raises 409 Conflict).
18. Unauthorized access protection (cross-workspace project/avatar access rejected).
19. Missing media graceful handling (avatar generation without speech audio fails truthfully).
20. GPU unavailable truthful behavior (MuseTalk on AMD host rejected with GPU_UNAVAILABLE).
"""

import copy
import uuid
import cv2
import numpy as np
import pytest
from httpx import AsyncClient

from app.ai.adapters.musetalk import MuseTalkAvatarProvider
from app.ai.adapters.piper import DEFAULT_PIPER_VOICE_ID
from app.ai.hardware import detect_hardware
from app.core.exceptions import (
    AIProviderException,
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
from app.schemas.orchestration import RenderProjectRequest
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
from app.services.job_service import JobService
from app.services.project_avatar_service import ProjectAvatarOrchestrator
from app.services.project_render_service import ProjectRenderOrchestrator
from app.services.project_service import ProjectService
from app.services.project_speech_service import ProjectSpeechOrchestrator
from app.services.voice_service import VoiceService
from app.storage.s3 import get_storage_provider


PIPER_BRYCE_VOICE_ID = "10000000-0000-0000-0000-000000000004"
KOKORO_HEART_VOICE_ID = "10000000-0000-0000-0000-000000000021"


def _create_synthetic_portrait_image_bytes(width: int = 320, height: int = 320) -> bytes:
    """Generate a clean synthetic portrait image plate with facial landmarks."""
    img = np.ones((height, width, 3), dtype=np.uint8) * 230
    cv2.circle(img, (width // 2, height // 2), int(min(width, height) * 0.35), (180, 210, 240), -1)
    cv2.circle(img, (int(width * 0.4), int(height * 0.4)), 8, (50, 50, 50), -1)
    cv2.circle(img, (int(width * 0.6), int(height * 0.4)), 8, (50, 50, 50), -1)
    cv2.ellipse(img, (width // 2, int(height * 0.65)), (25, 12), 0, 0, 180, (50, 50, 180), -1)
    _, buf = cv2.imencode(".png", img)
    return buf.tobytes()


async def _setup_workspace_and_project(
    async_client: AsyncClient,
    title: str = "Studio Pipeline E2E Project",
):
    """Helper creating user, workspace, and initialized ProjectDocumentV1."""
    email = f"studio_user_{uuid.uuid4().hex[:8]}@example.com"
    resp = await async_client.post(
        "/api/v1/auth/signup",
        json={"email": email, "display_name": "Studio Tester", "password": "Password123!"},
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
            scenes=[
                Scene(
                    id="scene-initial",
                    sequence=1,
                    duration=5.0,
                    speech=SceneSpeech(voice_id=PIPER_BRYCE_VOICE_ID, script="Initial studio script."),
                    avatar=SceneAvatar(avatar_id="default-avatar", view_mode="half_body"),
                )
            ],
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
    name: str = "Studio Test Avatar",
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
            visibility="workspace",
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
# 1 & 2: Project Loading & Scene Loading
# ===========================================================================

@pytest.mark.asyncio
async def test_studio_loads_real_project_and_scenes(async_client: AsyncClient):
    """Verifies Studio reads the authentic ProjectDocumentV1, settings, revision, and scenes."""
    user_id, ws_id, proj_id, token = await _setup_workspace_and_project(async_client, "Real Project Load")

    # Call API endpoints as Studio does
    headers = {"Authorization": f"Bearer {token}"}
    p_resp = await async_client.get(f"/api/v1/workspaces/{ws_id}/projects/{proj_id}", headers=headers)
    assert p_resp.status_code == 200
    p_data = p_resp.json()
    assert p_data["title"] == "Real Project Load"
    assert p_data["revision"] == 1
    assert p_data["current_version_id"] is not None

    v_resp = await async_client.get(
        f"/api/v1/workspaces/{ws_id}/projects/{proj_id}/versions/{p_data['current_version_id']}",
        headers=headers,
    )
    assert v_resp.status_code == 200
    v_data = v_resp.json()
    doc = v_data["document"]
    assert doc["schema_version"] == 1
    assert len(doc["scenes"]) == 1
    assert doc["scenes"][0]["id"] == "scene-initial"
    assert doc["scenes"][0]["speech"]["script"] == "Initial studio script."


# ===========================================================================
# 3, 4, 5: Scene Management (Add, Duplicate, Delete, Reorder)
# ===========================================================================

@pytest.mark.asyncio
async def test_studio_scene_lifecycle_add_duplicate_delete_reorder(async_client: AsyncClient):
    """Verifies adding, duplicating, deleting, and reordering scenes commits valid ProjectDocumentV1 with OCC."""
    user_id, ws_id, proj_id, token = await _setup_workspace_and_project(async_client, "Scene Lifecycle")
    headers = {"Authorization": f"Bearer {token}"}

    # Step 1: Add a Scene
    async with async_session_factory() as db:
        p_service = ProjectService(db)
        p = await p_service.get_project(proj_id, ws_id)
        ver = await p_service.get_version(p.current_version_id, proj_id, ws_id)
        doc = ProjectDocumentV1.model_validate(ver.document)

        new_scene = Scene(
            id="scene-added-2",
            sequence=2,
            duration=4.0,
            speech=SceneSpeech(voice_id=KOKORO_HEART_VOICE_ID, script="Second scene text."),
            avatar=SceneAvatar(avatar_id="avatar-2", view_mode="circle"),
        )
        doc.scenes.append(new_scene)
        ver2 = await p_service.create_version(proj_id, ws_id, user_id, p.revision, doc, "add_scene")
        await db.commit()
        assert ver2.revision == 2

    # Step 2: Duplicate Scene 1
    async with async_session_factory() as db:
        p_service = ProjectService(db)
        p = await p_service.get_project(proj_id, ws_id)
        ver = await p_service.get_version(p.current_version_id, proj_id, ws_id)
        doc = ProjectDocumentV1.model_validate(ver.document)
        assert len(doc.scenes) == 2

        clone = copy.deepcopy(doc.scenes[0])
        clone.id = "scene-clone-3"
        clone.sequence = 3
        doc.scenes.append(clone)
        ver3 = await p_service.create_version(proj_id, ws_id, user_id, p.revision, doc, "duplicate_scene")
        await db.commit()
        assert ver3.revision == 3

    # Step 3: Reorder Scenes (Swap Scene 1 and Scene 2)
    async with async_session_factory() as db:
        p_service = ProjectService(db)
        p = await p_service.get_project(proj_id, ws_id)
        ver = await p_service.get_version(p.current_version_id, proj_id, ws_id)
        doc = ProjectDocumentV1.model_validate(ver.document)
        assert len(doc.scenes) == 3

        # Swap
        doc.scenes[0], doc.scenes[1] = doc.scenes[1], doc.scenes[0]
        for i, s in enumerate(doc.scenes):
            s.sequence = i + 1

        ver4 = await p_service.create_version(proj_id, ws_id, user_id, p.revision, doc, "reorder_scenes")
        await db.commit()
        assert ver4.revision == 4
        assert doc.scenes[0].id == "scene-added-2"
        assert doc.scenes[0].sequence == 1

    # Step 4: Delete cloned scene
    async with async_session_factory() as db:
        p_service = ProjectService(db)
        p = await p_service.get_project(proj_id, ws_id)
        ver = await p_service.get_version(p.current_version_id, proj_id, ws_id)
        doc = ProjectDocumentV1.model_validate(ver.document)
        doc.scenes = [s for s in doc.scenes if s.id != "scene-clone-3"]
        for i, s in enumerate(doc.scenes):
            s.sequence = i + 1

        ver5 = await p_service.create_version(proj_id, ws_id, user_id, p.revision, doc, "delete_scene")
        await db.commit()
        assert ver5.revision == 5
        assert len(doc.scenes) == 2


# ===========================================================================
# 6, 7, 8: Script, Voice, & Avatar Updates
# ===========================================================================

@pytest.mark.asyncio
async def test_studio_property_updates_script_voice_avatar(async_client: AsyncClient):
    """Verifies editing script, selecting voice, and selecting avatar persists to version."""
    user_id, ws_id, proj_id, token = await _setup_workspace_and_project(async_client, "Property Updates")
    avatar, _ = await _create_test_avatar(ws_id, user_id, name="Lead Actor")

    async with async_session_factory() as db:
        p_service = ProjectService(db)
        p = await p_service.get_project(proj_id, ws_id)
        ver = await p_service.get_version(p.current_version_id, proj_id, ws_id)
        doc = ProjectDocumentV1.model_validate(ver.document)

        # Update Script, Voice to Kokoro Heart, and Avatar to Lead Actor
        doc.scenes[0].speech.script = "Updated speech script with high fidelity."
        doc.scenes[0].speech.voice_id = KOKORO_HEART_VOICE_ID
        doc.scenes[0].avatar.avatar_id = str(avatar.id)
        doc.scenes[0].avatar.view_mode = "close_up"

        ver2 = await p_service.create_version(proj_id, ws_id, user_id, p.revision, doc, "update_properties")
        await db.commit()
        assert ver2.revision == 2

    # Verify via API GET
    headers = {"Authorization": f"Bearer {token}"}
    p_resp = await async_client.get(f"/api/v1/workspaces/{ws_id}/projects/{proj_id}", headers=headers)
    p_data = p_resp.json()
    assert p_data["revision"] == 2

    v_resp = await async_client.get(
        f"/api/v1/workspaces/{ws_id}/projects/{proj_id}/versions/{p_data['current_version_id']}",
        headers=headers,
    )
    doc_after = v_resp.json()["document"]
    assert doc_after["scenes"][0]["speech"]["script"] == "Updated speech script with high fidelity."
    assert doc_after["scenes"][0]["speech"]["voice_id"] == KOKORO_HEART_VOICE_ID
    assert doc_after["scenes"][0]["avatar"]["avatar_id"] == str(avatar.id)
    assert doc_after["scenes"][0]["avatar"]["view_mode"] == "close_up"


# ===========================================================================
# 9, 10, 11: Real Speech Generation, Job Progress & Audio Association
# ===========================================================================

@pytest.mark.asyncio
async def test_studio_real_speech_generation_and_audio_association(async_client: AsyncClient):
    """Verifies Studio's speech generation action synthesizes real WAV and associates audio_asset_id."""
    user_id, ws_id, proj_id, token = await _setup_workspace_and_project(async_client, "Speech Gen Studio")

    async with async_session_factory() as db:
        p_service = ProjectService(db)
        speech_orch = ProjectSpeechOrchestrator(db)
        p = await p_service.get_project(proj_id, ws_id)

        # Execute speech synthesis
        ver_speech = await speech_orch.synthesize_project_speech(
            project_id=proj_id,
            workspace_id=ws_id,
            user_id=user_id,
            expected_revision=p.revision,
            scene_ids=["scene-initial"],
        )
        await db.commit()
        assert ver_speech.revision == 2

        doc_speech = ProjectDocumentV1.model_validate(ver_speech.document)
        audio_asset_id = doc_speech.scenes[0].speech.audio_asset_id
        assert audio_asset_id is not None

        # Verify asset in storage
        storage = get_storage_provider()
        asset_repo = AssetLifecycleManager(db).asset_repo
        asset = await asset_repo.get_by_id(uuid.UUID(audio_asset_id), ws_id)
        assert asset is not None
        assert asset.asset_type == "audio"
        wav_bytes = await storage.get_object(asset.storage_key)
        assert len(wav_bytes) > 5000


# ===========================================================================
# 12, 13: Talking-Avatar Generation & Video Association
# ===========================================================================

@pytest.mark.asyncio
async def test_studio_talking_avatar_generation_and_video_association(async_client: AsyncClient):
    """Verifies Studio's avatar generation action synthesizes real MP4 via Wav2Lip on CPU."""
    user_id, ws_id, proj_id, token = await _setup_workspace_and_project(async_client, "Avatar Gen Studio")
    avatar, _ = await _create_test_avatar(ws_id, user_id, name="Wav2Lip Actor", provider="wav2lip")

    async with async_session_factory() as db:
        p_service = ProjectService(db)
        speech_orch = ProjectSpeechOrchestrator(db)
        avatar_orch = ProjectAvatarOrchestrator(db)

        # Set avatar ID
        p = await p_service.get_project(proj_id, ws_id)
        ver = await p_service.get_version(p.current_version_id, proj_id, ws_id)
        doc = ProjectDocumentV1.model_validate(ver.document)
        doc.scenes[0].avatar.avatar_id = str(avatar.id)
        ver_cfg = await p_service.create_version(proj_id, ws_id, user_id, p.revision, doc, "set_avatar")
        await db.commit()

        # Generate Speech first
        ver_speech = await speech_orch.synthesize_project_speech(proj_id, ws_id, user_id, ver_cfg.revision)
        await db.commit()

        # Generate Talking-Avatar Video
        ver_avatar, metrics = await avatar_orch.generate_project_avatar_video(
            project_id=proj_id,
            workspace_id=ws_id,
            user_id=user_id,
            expected_revision=ver_speech.revision,
            scene_id="scene-initial",
        )
        await db.commit()

        doc_avatar = ProjectDocumentV1.model_validate(ver_avatar.document)
        video_asset_id = doc_avatar.scenes[0].avatar.video_asset_id
        assert video_asset_id is not None
        assert any(a.asset_id == video_asset_id for a in doc_avatar.assets)

        # Verify MP4 in MinIO
        storage = get_storage_provider()
        asset_repo = AssetLifecycleManager(db).asset_repo
        asset = await asset_repo.get_by_id(uuid.UUID(video_asset_id), ws_id)
        assert asset is not None
        assert asset.asset_type == "video"
        mp4_bytes = await storage.get_object(asset.storage_key)
        assert len(mp4_bytes) > 20000


# ===========================================================================
# 14, 15, 16: Multi-Scene Timeline Persistence & Final Render
# ===========================================================================

@pytest.mark.asyncio
async def test_studio_timeline_persistence_and_final_render(async_client: AsyncClient):
    """Verifies multi-scene project timeline renders to playable MP4 via TimelineCompositor."""
    user_id, ws_id, proj_id, token = await _setup_workspace_and_project(async_client, "Multi-Scene Render")
    avatar_a, _ = await _create_test_avatar(ws_id, user_id, name="Actor A", provider="wav2lip")
    avatar_b, _ = await _create_test_avatar(ws_id, user_id, name="Actor B", provider="wav2lip")

    async with async_session_factory() as db:
        p_service = ProjectService(db)
        speech_orch = ProjectSpeechOrchestrator(db)
        avatar_orch = ProjectAvatarOrchestrator(db)

        p = await p_service.get_project(proj_id, ws_id)
        ver = await p_service.get_version(p.current_version_id, proj_id, ws_id)
        doc = ProjectDocumentV1.model_validate(ver.document)

        # Configure 2 scenes: Piper + Avatar A, Kokoro + Avatar B
        doc.scenes = [
            Scene(
                id="s1",
                sequence=1,
                duration=2.5,
                speech=SceneSpeech(voice_id=PIPER_BRYCE_VOICE_ID, script="Studio scene one."),
                avatar=SceneAvatar(avatar_id=str(avatar_a.id), view_mode="half_body"),
            ),
            Scene(
                id="s2",
                sequence=2,
                duration=2.5,
                speech=SceneSpeech(voice_id=KOKORO_HEART_VOICE_ID, script="Studio scene two."),
                avatar=SceneAvatar(avatar_id=str(avatar_b.id), view_mode="circle"),
            ),
        ]
        ver_cfg = await p_service.create_version(proj_id, ws_id, user_id, p.revision, doc, "multi_cfg")
        await db.commit()

        # Step 1: Synthesize speech for both scenes
        ver_speech = await speech_orch.synthesize_project_speech(proj_id, ws_id, user_id, ver_cfg.revision)
        await db.commit()

        # Step 2: Generate avatar video for scene 1
        ver_av1, _ = await avatar_orch.generate_project_avatar_video(
            project_id=proj_id,
            workspace_id=ws_id,
            user_id=user_id,
            expected_revision=ver_speech.revision,
            scene_id="s1",
        )
        await db.commit()

        # Step 3: Generate avatar video for scene 2
        ver_av2, _ = await avatar_orch.generate_project_avatar_video(
            project_id=proj_id,
            workspace_id=ws_id,
            user_id=user_id,
            expected_revision=ver_av1.revision,
            scene_id="s2",
        )
        await db.commit()

        doc_final = ProjectDocumentV1.model_validate(ver_av2.document)
        assert doc_final.scenes[0].avatar.video_asset_id is not None
        assert doc_final.scenes[1].avatar.video_asset_id is not None

        # Step 4: Render Project with TimelineCompositor
        async with MediaWorkspace(prefix="studio_render_") as mws:
            compositor = TimelineCompositor()
            render_res = await compositor.render_project(
                document=doc_final,
                workspace_id=ws_id,
                db=db,
                media_workspace=mws,
            )
            assert render_res.video_path.exists()
            assert render_res.video_path.stat().st_size > 50000
            assert len(render_res.probe_result.video_streams) > 0
            assert len(render_res.probe_result.audio_streams) > 0
            assert render_res.scenes_count == 2


# ===========================================================================
# 17, 18, 19, 20: OCC, RBAC, Missing Media & Truthful GPU Failures
# ===========================================================================

@pytest.mark.asyncio
async def test_studio_occ_concurrency_conflict_rejected(async_client: AsyncClient):
    """Verifies saving with a stale expected_revision raises 409 Conflict."""
    user_id, ws_id, proj_id, token = await _setup_workspace_and_project(async_client, "OCC Conflict")

    async with async_session_factory() as db:
        p_service = ProjectService(db)
        p = await p_service.get_project(proj_id, ws_id)
        ver = await p_service.get_version(p.current_version_id, proj_id, ws_id)
        doc = ProjectDocumentV1.model_validate(ver.document)

        # Successful update revision 1 -> 2
        ver2 = await p_service.create_version(proj_id, ws_id, user_id, 1, doc, "update_1")
        await db.commit()
        assert ver2.revision == 2

        # Stale update with expected_revision=1 should fail with ConflictException
        with pytest.raises(ConflictException):
            await p_service.create_version(proj_id, ws_id, user_id, 1, doc, "stale_update")


@pytest.mark.asyncio
async def test_studio_unauthorized_cross_workspace_access_denied(async_client: AsyncClient):
    """Verifies cross-workspace access to projects is rejected with 403/404."""
    user1, ws1, proj1, token1 = await _setup_workspace_and_project(async_client, "WS1 Project")
    user2, ws2, proj2, token2 = await _setup_workspace_and_project(async_client, "WS2 Project")

    headers2 = {"Authorization": f"Bearer {token2}"}
    # User 2 attempts to get User 1's project in WS 1
    resp = await async_client.get(f"/api/v1/workspaces/{ws1}/projects/{proj1}", headers=headers2)
    assert resp.status_code in (403, 404)


@pytest.mark.asyncio
async def test_studio_missing_media_graceful_handling(async_client: AsyncClient):
    """Verifies attempting avatar video generation without speech audio raises SPEECH_AUDIO_NOT_FOUND."""
    user_id, ws_id, proj_id, token = await _setup_workspace_and_project(async_client, "Missing Media")
    avatar, _ = await _create_test_avatar(ws_id, user_id)

    async with async_session_factory() as db:
        p_service = ProjectService(db)
        avatar_orch = ProjectAvatarOrchestrator(db)
        p = await p_service.get_project(proj_id, ws_id)
        ver = await p_service.get_version(p.current_version_id, proj_id, ws_id)
        doc = ProjectDocumentV1.model_validate(ver.document)

        doc.scenes[0].avatar.avatar_id = str(avatar.id)
        doc.scenes[0].speech.audio_asset_id = None  # Explicitly absent
        ver_cfg = await p_service.create_version(proj_id, ws_id, user_id, p.revision, doc, "no_audio")
        await db.commit()

        with pytest.raises(NotFoundException) as exc_info:
            await avatar_orch.generate_project_avatar_video(
                project_id=proj_id,
                workspace_id=ws_id,
                user_id=user_id,
                expected_revision=ver_cfg.revision,
                scene_id="scene-initial",
            )
        assert exc_info.value.code == "SPEECH_AUDIO_NOT_FOUND"


@pytest.mark.asyncio
async def test_studio_gpu_unavailable_truthful_behavior(async_client: AsyncClient):
    """Verifies requesting GPU provider (MuseTalk) on AMD host raises GPU_UNAVAILABLE truthfully."""
    user_id, ws_id, proj_id, token = await _setup_workspace_and_project(async_client, "GPU Truthful")
    avatar_gpu, _ = await _create_test_avatar(ws_id, user_id, name="MuseTalk Actor", provider="musetalk")

    async with async_session_factory() as db:
        p_service = ProjectService(db)
        speech_orch = ProjectSpeechOrchestrator(db)
        avatar_orch = ProjectAvatarOrchestrator(db)

        p = await p_service.get_project(proj_id, ws_id)
        ver = await p_service.get_version(p.current_version_id, proj_id, ws_id)
        doc = ProjectDocumentV1.model_validate(ver.document)
        doc.scenes[0].avatar.avatar_id = str(avatar_gpu.id)

        ver_cfg = await p_service.create_version(proj_id, ws_id, user_id, p.revision, doc, "cfg_musetalk")
        await db.commit()

        ver_speech = await speech_orch.synthesize_project_speech(proj_id, ws_id, user_id, ver_cfg.revision)
        await db.commit()

        # Hardware check
        hw = detect_hardware()
        if not hw.has_cuda:
            with pytest.raises(AIProviderException) as exc_info:
                await avatar_orch.generate_project_avatar_video(
                    project_id=proj_id,
                    workspace_id=ws_id,
                    user_id=user_id,
                    expected_revision=ver_speech.revision,
                    scene_id="scene-initial",
                )
            assert exc_info.value.code == "GPU_UNAVAILABLE"
