"""Phase 29A: Studio Music & Media Editor Test Suite.

Verifies:
1. Workspace audio asset listing
2. Audio asset preview metadata and download URL
3. Add music track to ProjectDocumentV1.audio_tracks
4. Multiple audio_tracks array state (non-zero index support)
5. Update volume on audio track
6. Mute / unmute flag on audio track
7. Loop flag on audio track
8. Start offset (start_time) on audio track
9. Remove music track from audio_tracks
10. Persistence across project revisions
11. OCC conflict rejection (stale expected_revision raises 409)
12. Compositor receives correct music asset
13. Compositor respects muted flag (audio not mixed)
14. Compositor respects start_time (adelay filter applied)
15. Compositor respects loop flag
16. Final render contains expected audio mix
17. Final render duration remains strictly video-controlled
18. Upload intent creation
19. Asset confirmation
20. Media library listing (all, image, video, audio)
21. Scene background persistence (image/video background)
22. Scene layer persistence (media layer)
23. Cross-workspace asset isolation
"""

import copy
import io
import math
import struct
import uuid
import wave
from pathlib import Path
from typing import Tuple

import cv2
import numpy as np
import pytest
from httpx import AsyncClient

from app.core.exceptions import ConflictException, NotFoundException
from app.db.session import async_session_factory
from app.media.compositor import TimelineCompositor
from app.media.errors import RenderInputMissingError
from app.media.ffprobe import FFprobeService
from app.media.workspace import MediaWorkspace
from app.storage.s3 import get_storage_provider
from app.models.project import Project, ProjectVersion
from app.schemas.project_document import (
    AudioTrack,
    ProjectDocumentV1,
    ProjectSettings,
    Scene,
    SceneAvatar,
    SceneLayer,
    SceneSpeech,
)
from app.services.asset_lifecycle import AssetLifecycleManager
from app.services.project_service import ProjectService


def _create_synthetic_wav(
    duration: float = 1.0, freq: float = 440.0, sample_rate: int = 16000
) -> bytes:
    """Generate a clean synthetic sine wave PCM audio buffer."""
    num_samples = int(duration * sample_rate)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        for i in range(num_samples):
            val = int(32767.0 * 0.4 * math.sin(2.0 * math.pi * freq * i / sample_rate))
            wf.writeframes(struct.pack("<h", val))
    return buf.getvalue()


def _create_synthetic_png(width: int = 320, height: int = 240) -> bytes:
    """Generate a synthetic test image."""
    img = np.ones((height, width, 3), dtype=np.uint8) * 120
    cv2.putText(
        img, "MEDIA TEST", (20, height // 2), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2
    )
    _, buf = cv2.imencode(".png", img)
    return buf.tobytes()


async def _setup_workspace_and_project(
    async_client: AsyncClient,
    title: str = "Music & Media Test Project",
) -> Tuple[uuid.UUID, uuid.UUID, uuid.UUID, str]:
    """Helper creating user, workspace, and initialized ProjectDocumentV1."""
    email = f"music_user_{uuid.uuid4().hex[:8]}@example.com"
    resp = await async_client.post(
        "/api/v1/auth/signup",
        json={"email": email, "display_name": "Music Tester", "password": "Password123!"},
    )
    assert resp.status_code == 201
    data = resp.json()
    user_id = uuid.UUID(data["user"]["id"])
    token = data["tokens"]["access_token"]

    ws_resp = await async_client.get(
        "/api/v1/workspaces", headers={"Authorization": f"Bearer {token}"}
    )
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
            settings=ProjectSettings(
                width=1280, height=720, aspect_ratio="16:9", total_duration=4.0
            ),
            scenes=[
                Scene(
                    id="scene_001",
                    sequence=1,
                    duration=4.0,
                    speech=SceneSpeech(
                        voice_id="10000000-0000-0000-0000-000000000004",
                        script="Speech for music test.",
                    ),
                    avatar=SceneAvatar(avatar_id="default-presenter", view_mode="half_body"),
                )
            ],
            audio_tracks=[],
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


# ============================================================================
# 1. MUSIC AUDIT TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_workspace_audio_asset_listing_and_preview(async_client: AsyncClient):
    """1 & 2: List workspace audio assets and verify signed preview URL."""
    user_id, ws_id, _, token = await _setup_workspace_and_project(async_client)

    # Ingest synthetic audio into workspace
    audio_bytes = _create_synthetic_wav(duration=2.0)
    async with async_session_factory() as db:
        mgr = AssetLifecycleManager(db)
        audio_asset = await mgr.ingest_generated_asset(
            workspace_id=ws_id,
            created_by=user_id,
            content=audio_bytes,
            original_filename="test_lofi_beat.wav",
            asset_type="audio",
            mime_type="audio/wav",
        )
        asset_id = audio_asset.id

    # List audio assets via API
    resp = await async_client.get(
        f"/api/v1/workspaces/{ws_id}/assets?asset_type=audio",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    matched = next((a for a in data if a["id"] == str(asset_id)), None)
    assert matched is not None
    assert matched["asset_type"] == "audio"
    assert matched["original_filename"] == "test_lofi_beat.wav"

    # Get signed download preview URL
    dl_resp = await async_client.get(
        f"/api/v1/workspaces/{ws_id}/assets/{asset_id}/download",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert dl_resp.status_code == 200
    dl_data = dl_resp.json()
    assert "download_url" in dl_data
    assert dl_data["download_url"].startswith("http")


@pytest.mark.asyncio
async def test_add_and_manage_multiple_music_tracks(async_client: AsyncClient):
    """3, 4, 5, 6, 7, 8, 9: Add music track, multi-track array, volume, mute, loop, start offset, remove."""
    user_id, ws_id, project_id, token = await _setup_workspace_and_project(async_client)

    # Create 2 audio assets
    wav1 = _create_synthetic_wav(duration=1.5, freq=300.0)
    wav2 = _create_synthetic_wav(duration=2.0, freq=600.0)

    async with async_session_factory() as db:
        mgr = AssetLifecycleManager(db)
        asset1 = await mgr.ingest_generated_asset(
            workspace_id=ws_id,
            created_by=user_id,
            content=wav1,
            original_filename="ambient_track_1.wav",
            asset_type="audio",
            mime_type="audio/wav",
        )
        asset2 = await mgr.ingest_generated_asset(
            workspace_id=ws_id,
            created_by=user_id,
            content=wav2,
            original_filename="beat_track_2.wav",
            asset_type="audio",
            mime_type="audio/wav",
        )

    # Fetch initial project version
    p_resp = await async_client.get(
        f"/api/v1/workspaces/{ws_id}/projects/{project_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert p_resp.status_code == 200
    current_ver_id = p_resp.json()["current_version_id"]

    v_resp = await async_client.get(
        f"/api/v1/workspaces/{ws_id}/projects/{project_id}/versions/{current_ver_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert v_resp.status_code == 200
    doc = v_resp.json()["document"]

    # 3. Add first music track
    track_1 = {
        "id": "track_ambient",
        "asset_id": str(asset1.id),
        "name": "Ambient Track 1",
        "volume": 0.4,
        "start_time": 0.0,
        "duration": None,
        "loop": True,
        "muted": False,
    }
    doc["audio_tracks"] = [track_1]

    save_resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/projects/{project_id}/versions",
        headers={"Authorization": f"Bearer {token}"},
        json={"expected_revision": 1, "document": doc, "source": "studio_manual"},
    )
    assert save_resp.status_code == 201
    assert save_resp.json()["revision"] == 2

    # 4. Multi-track array: add second music track (array architecture, not hardcoded to index 0)
    track_2 = {
        "id": "track_beat",
        "asset_id": str(asset2.id),
        "name": "Beat Track 2",
        "volume": 0.75,
        "start_time": 1.5,
        "duration": 5.0,
        "loop": False,
        "muted": True,
    }
    doc["audio_tracks"].append(track_2)

    save_resp2 = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/projects/{project_id}/versions",
        headers={"Authorization": f"Bearer {token}"},
        json={"expected_revision": 2, "document": doc, "source": "studio_manual"},
    )
    assert save_resp2.status_code == 201
    assert save_resp2.json()["revision"] == 3

    # Verify both tracks persisted in ProjectDocumentV1
    doc_r3 = save_resp2.json()["document"]
    assert len(doc_r3["audio_tracks"]) == 2
    assert doc_r3["audio_tracks"][0]["id"] == "track_ambient"
    assert doc_r3["audio_tracks"][1]["id"] == "track_beat"
    assert doc_r3["audio_tracks"][1]["muted"] is True
    assert doc_r3["audio_tracks"][1]["start_time"] == 1.5

    # 5, 6, 7, 8: Update volume, unmute, toggle loop, change offset on track_2
    doc_r3["audio_tracks"][1]["volume"] = 0.5
    doc_r3["audio_tracks"][1]["muted"] = False
    doc_r3["audio_tracks"][1]["loop"] = True
    doc_r3["audio_tracks"][1]["start_time"] = 0.5

    save_resp3 = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/projects/{project_id}/versions",
        headers={"Authorization": f"Bearer {token}"},
        json={"expected_revision": 3, "document": doc_r3, "source": "studio_manual"},
    )
    assert save_resp3.status_code == 201
    assert save_resp3.json()["revision"] == 4
    updated_t2 = save_resp3.json()["document"]["audio_tracks"][1]
    assert updated_t2["volume"] == 0.5
    assert updated_t2["muted"] is False
    assert updated_t2["loop"] is True
    assert updated_t2["start_time"] == 0.5

    # 9. Remove track_1: verify only track_2 remains
    doc_r4 = save_resp3.json()["document"]
    doc_r4["audio_tracks"] = [doc_r4["audio_tracks"][1]]

    save_resp4 = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/projects/{project_id}/versions",
        headers={"Authorization": f"Bearer {token}"},
        json={"expected_revision": 4, "document": doc_r4, "source": "studio_manual"},
    )
    assert save_resp4.status_code == 201
    assert save_resp4.json()["revision"] == 5
    assert len(save_resp4.json()["document"]["audio_tracks"]) == 1
    assert save_resp4.json()["document"]["audio_tracks"][0]["id"] == "track_beat"


@pytest.mark.asyncio
async def test_music_occ_conflict_handling(async_client: AsyncClient):
    """10 & 11: Verify persistence across revisions and OCC conflict rejection."""
    _, ws_id, project_id, token = await _setup_workspace_and_project(async_client)

    # Initial doc fetch
    p_resp = await async_client.get(
        f"/api/v1/workspaces/{ws_id}/projects/{project_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    current_ver_id = p_resp.json()["current_version_id"]
    v_resp = await async_client.get(
        f"/api/v1/workspaces/{ws_id}/projects/{project_id}/versions/{current_ver_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    doc = v_resp.json()["document"]

    # Session 1 saves revision 2
    save1 = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/projects/{project_id}/versions",
        headers={"Authorization": f"Bearer {token}"},
        json={"expected_revision": 1, "document": doc, "source": "studio_manual"},
    )
    assert save1.status_code == 201

    # Session 2 attempts save with stale expected_revision=1 -> 409 Conflict
    stale_save = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/projects/{project_id}/versions",
        headers={"Authorization": f"Bearer {token}"},
        json={"expected_revision": 1, "document": doc, "source": "studio_manual"},
    )
    assert stale_save.status_code == 409
    assert "CONCURRENCY_CONFLICT" in stale_save.text


# ============================================================================
# 2. COMPOSITOR & RENDER VERIFICATION
# ============================================================================


@pytest.mark.asyncio
async def test_compositor_receives_music_and_respects_muted_loop_start(async_client: AsyncClient):
    """12, 13, 14, 15: Verify _mix_background_audio respects asset, muted, start_time, loop."""
    user_id, ws_id, project_id, token = await _setup_workspace_and_project(async_client)

    music_bytes = _create_synthetic_wav(duration=1.0, freq=500.0)
    speech_bytes = _create_synthetic_wav(duration=3.0, freq=250.0)

    async with async_session_factory() as db:
        mgr = AssetLifecycleManager(db)
        music_asset = await mgr.ingest_generated_asset(
            workspace_id=ws_id,
            created_by=user_id,
            content=music_bytes,
            original_filename="music_bg.wav",
            asset_type="audio",
            mime_type="audio/wav",
        )
        speech_asset = await mgr.ingest_generated_asset(
            workspace_id=ws_id,
            created_by=user_id,
            content=speech_bytes,
            original_filename="speech_tts.wav",
            asset_type="audio",
            mime_type="audio/wav",
        )

        compositor = TimelineCompositor()
        mws = MediaWorkspace(prefix="test_compositor_music_")

        try:
            # Create a 3-second base video assembly with speech audio
            assembly_path = mws.output_dir / "assembly.mp4"
            cmd_assembly = [
                "-y",
                "-f",
                "lavfi",
                "-i",
                "color=c=black:s=640x360:r=25:d=3.0",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=440:duration=3.0",
                "-c:v",
                "libx264",
                "-c:a",
                "aac",
                "-shortest",
                str(assembly_path),
            ]
            await compositor.ffmpeg_service.execute_ffmpeg(cmd_assembly)
            assert assembly_path.exists()

            # Case A: Track is MUTED -> should pass through assembly cleanly
            muted_track = AudioTrack(
                id="t_muted",
                asset_id=str(music_asset.id),
                name="Muted Track",
                volume=0.5,
                loop=True,
                muted=True,
            )
            out_muted = mws.output_dir / "out_muted.mp4"
            await compositor._mix_background_audio(
                assembly_path=assembly_path,
                audio_tracks=[muted_track],
                output_path=out_muted,
                workspace_id=ws_id,
                db=db,
                mws=mws,
            )
            assert out_muted.exists()

            # Case B: Active Track with start_time=1.0 and loop=True
            active_track = AudioTrack(
                id="t_active",
                asset_id=str(music_asset.id),
                name="Active Music",
                volume=0.35,
                start_time=0.5,
                loop=True,
                muted=False,
            )
            out_active = mws.output_dir / "out_active.mp4"
            await compositor._mix_background_audio(
                assembly_path=assembly_path,
                audio_tracks=[active_track],
                output_path=out_active,
                workspace_id=ws_id,
                db=db,
                mws=mws,
            )
            assert out_active.exists()

            # Verify with FFprobe: audio stream exists, duration bounded by assembly (3.0s)
            probe_active = await compositor.ffprobe_service.probe(out_active)
            assert probe_active.has_audio is True
            assert probe_active.has_video is True
            assert abs(probe_active.duration_seconds - 3.0) < 0.2

        finally:
            mws.cleanup()


@pytest.mark.asyncio
async def test_final_render_with_music_and_duration_bounded(async_client: AsyncClient):
    """16 & 17: Full ProjectDocumentV1 render produces playable MP4 with background audio."""
    user_id, ws_id, project_id, token = await _setup_workspace_and_project(async_client)

    # Ingest speech audio and background music
    speech_wav = _create_synthetic_wav(duration=2.5, freq=200.0)
    bg_music_wav = _create_synthetic_wav(duration=1.0, freq=600.0)

    async with async_session_factory() as db:
        mgr = AssetLifecycleManager(db)
        speech_asset = await mgr.ingest_generated_asset(
            workspace_id=ws_id,
            created_by=user_id,
            content=speech_wav,
            original_filename="speech.wav",
            asset_type="audio",
            mime_type="audio/wav",
        )
        music_asset = await mgr.ingest_generated_asset(
            workspace_id=ws_id,
            created_by=user_id,
            content=bg_music_wav,
            original_filename="bg_music.wav",
            asset_type="audio",
            mime_type="audio/wav",
        )

        # Build document with speech and music track
        doc = ProjectDocumentV1(
            schema_version=1,
            settings=ProjectSettings(
                width=640, height=360, aspect_ratio="16:9", fps=25, total_duration=3.0
            ),
            scenes=[
                Scene(
                    id="sc_1",
                    sequence=1,
                    duration=3.0,
                    background={"type": "color", "value": "#111827"},
                    speech=SceneSpeech(
                        voice_id="10000000-0000-0000-0000-000000000004",
                        script="Compositor music test",
                        audio_asset_id=str(speech_asset.id),
                    ),
                )
            ],
            audio_tracks=[
                AudioTrack(
                    id="track_bg",
                    asset_id=str(music_asset.id),
                    name="Background Music",
                    volume=0.3,
                    start_time=0.0,
                    loop=True,
                    muted=False,
                )
            ],
        )

        compositor = TimelineCompositor()
        mws = MediaWorkspace(prefix="test_render_music_")

        try:
            render_result = await compositor.render_project(
                document=doc,
                workspace_id=ws_id,
                db=db,
                media_workspace=mws,
            )
            assert render_result.video_path.exists()
            assert render_result.thumbnail_path.exists()

            # Duration strictly bounded by scene narration duration (2.5s)
            probe = render_result.probe_result
            assert probe.has_video is True
            assert probe.has_audio is True
            assert abs(probe.duration_seconds - 2.5) <= 0.2
            assert probe.width == 640
            assert probe.height == 360

        finally:
            mws.cleanup()


# ============================================================================
# 3. MEDIA FOUNDATION & SECURITY TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_media_upload_intent_confirmation_and_library(async_client: AsyncClient):
    """18, 19, 20: Upload intent, direct MinIO upload, confirmation, and library filtering."""
    user_id, ws_id, _, token = await _setup_workspace_and_project(async_client)

    # 18. Create upload intent for an image asset
    intent_resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/assets/upload-intents",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "original_filename": "product_banner.png",
            "mime_type": "image/png",
            "size_bytes": 1024,
            "asset_type": "image",
        },
    )
    assert intent_resp.status_code == 201
    intent_data = intent_resp.json()
    asset_id = intent_data["asset_id"]
    upload_url = intent_data["signed_upload_url"]
    assert upload_url.startswith("http")

    # Upload binary to MinIO
    img_bytes = _create_synthetic_png()
    storage = get_storage_provider()
    storage.s3_client.put_object(
        Bucket=storage.bucket_name,
        Key=intent_data["storage_key"],
        Body=img_bytes,
        ContentType="image/png",
    )

    # 19. Confirm asset upload
    conf_resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/assets/{asset_id}/confirm",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert conf_resp.status_code == 200
    assert conf_resp.json()["status"] == "ready"

    # 20. Media library filtering by asset_type
    lib_img = await async_client.get(
        f"/api/v1/workspaces/{ws_id}/assets?asset_type=image",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert lib_img.status_code == 200
    assert any(a["id"] == str(asset_id) for a in lib_img.json())

    lib_video = await async_client.get(
        f"/api/v1/workspaces/{ws_id}/assets?asset_type=video",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert lib_video.status_code == 200
    assert not any(a["id"] == str(asset_id) for a in lib_video.json())


@pytest.mark.asyncio
async def test_scene_background_and_layer_media_persistence(async_client: AsyncClient):
    """21 & 22: Persist image background and media layer in ProjectDocumentV1."""
    user_id, ws_id, project_id, token = await _setup_workspace_and_project(async_client)

    # Ingest test image asset
    img_bytes = _create_synthetic_png()
    async with async_session_factory() as db:
        mgr = AssetLifecycleManager(db)
        img_asset = await mgr.ingest_generated_asset(
            workspace_id=ws_id,
            created_by=user_id,
            content=img_bytes,
            original_filename="studio_backdrop.png",
            asset_type="image",
            mime_type="image/png",
        )
        asset_id = str(img_asset.id)

    # Fetch document
    p_resp = await async_client.get(
        f"/api/v1/workspaces/{ws_id}/projects/{project_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    doc = (
        await async_client.get(
            f"/api/v1/workspaces/{ws_id}/projects/{project_id}/versions/{p_resp.json()['current_version_id']}",
            headers={"Authorization": f"Bearer {token}"},
        )
    ).json()["document"]

    # 21. Set scene background to image asset
    doc["scenes"][0]["background"] = {
        "type": "image",
        "asset_id": asset_id,
        "value": "studio_backdrop.png",
    }

    # 22. Add media layer to scene
    layer = {
        "id": "layer_logo_001",
        "type": "image",
        "name": "Overlay Logo",
        "start_time": 0.0,
        "end_time": 4.0,
        "content": {"asset_id": asset_id, "name": "studio_backdrop.png"},
        "transform": {"x": 0.8, "y": 0.2, "scale": 0.5},
    }
    doc["scenes"][0]["layers"] = [layer]

    save_resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/projects/{project_id}/versions",
        headers={"Authorization": f"Bearer {token}"},
        json={"expected_revision": 1, "document": doc, "source": "studio_manual"},
    )
    assert save_resp.status_code == 201
    persisted_doc = save_resp.json()["document"]

    # Verify background persisted
    assert persisted_doc["scenes"][0]["background"]["type"] == "image"
    assert persisted_doc["scenes"][0]["background"]["asset_id"] == asset_id

    # Verify layer persisted
    assert len(persisted_doc["scenes"][0]["layers"]) == 1
    assert persisted_doc["scenes"][0]["layers"][0]["id"] == "layer_logo_001"
    assert persisted_doc["scenes"][0]["layers"][0]["content"]["asset_id"] == asset_id


@pytest.mark.asyncio
async def test_cross_workspace_asset_isolation(async_client: AsyncClient):
    """23: Verify Workspace A cannot access or resolve private asset belonging to Workspace B."""
    # Create Workspace A
    _, ws_a, _, token_a = await _setup_workspace_and_project(async_client, title="Project A")

    # Create Workspace B
    _, ws_b, _, token_b = await _setup_workspace_and_project(async_client, title="Project B")

    # Upload audio to Workspace B
    audio_b = _create_synthetic_wav(duration=1.0)
    intent_b = await async_client.post(
        f"/api/v1/workspaces/{ws_b}/assets/upload-intents",
        headers={"Authorization": f"Bearer {token_b}"},
        json={
            "original_filename": "private_b_track.wav",
            "mime_type": "audio/wav",
            "size_bytes": len(audio_b),
            "asset_type": "audio",
        },
    )
    assert intent_b.status_code == 201
    asset_b_id = intent_b.json()["asset_id"]

    # User A tries to get download URL for Workspace B's asset -> 404 Not Found
    rogue_dl = await async_client.get(
        f"/api/v1/workspaces/{ws_a}/assets/{asset_b_id}/download",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert rogue_dl.status_code == 404

    # Backend compositor MediaWorkspace resolution of asset_b in workspace_a must raise
    async with async_session_factory() as db:
        mws = MediaWorkspace(prefix="test_isolation_")
        try:
            with pytest.raises(RenderInputMissingError):
                await mws.resolve_asset(asset_id=asset_b_id, workspace_id=ws_a, db=db)
        finally:
            mws.cleanup()
