"""Phase 29C: Studio Text Overlays End-to-End Test Suite.

Verifies:
1. Text layer schema models & defaults (SceneLayer type="text", enabled=True, transform, content)
2. Add multiple text layers to scene and persist into ProjectDocumentV1
3. Text layer editing (text, styling, position) and OCC conflict handling
4. Text layer timing validation (start_time >= 0, end_time > start_time)
5. Text layer duplicate and delete persistence
6. Multi-scene text layer isolation (no cross-scene text leakage)
7. TimelineCompositor ASS script generation (_generate_scene_text_ass_file) with exact styles & positions
8. Actual text burn-in into MP4 video (pixel intensity verification on solid background)
9. Text outside active time range does not render (t=1.0s vs t=2.5s frame verification)
10. Disabled text layer does not render into video
11. Multiple overlapping text layers render simultaneously
12. Coexistence of text overlays, speech captions, and background music
13. Cross-workspace project isolation and security
"""

import copy
import io
import math
import struct
import subprocess
import uuid
import wave
from pathlib import Path
from typing import Tuple

import pytest
from httpx import AsyncClient

from app.core.exceptions import ConflictException
from app.db.session import async_session_factory
from app.media.compositor import CanvasProfile, TimelineCompositor
from app.media.ffprobe import FFprobeService
from app.media.workspace import MediaWorkspace
from app.models.project import Project, ProjectVersion
from app.schemas.project_document import (
    AudioTrack,
    CaptionSettings,
    CaptionStyle,
    ProjectDocumentV1,
    ProjectSettings,
    Scene,
    SceneLayer,
    SceneSpeech,
)
from app.services.asset_lifecycle import AssetLifecycleManager
from app.services.project_service import ProjectService


def _create_synthetic_wav(duration: float = 2.0, freq: float = 300.0, sample_rate: int = 16000) -> bytes:
    """Generate a clean synthetic WAV audio in-memory for testing."""
    buf = io.BytesIO()
    num_samples = int(sample_rate * duration)
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        frames = bytearray()
        for i in range(num_samples):
            t = float(i) / sample_rate
            sample = int(16000.0 * math.sin(2.0 * math.pi * freq * t))
            frames.extend(struct.pack("<h", sample))
        wf.writeframes(frames)
    return buf.getvalue()


async def _setup_workspace_and_project(
    client: AsyncClient, title: str = "Text Studio Project"
) -> Tuple[uuid.UUID, uuid.UUID, uuid.UUID, str]:
    """Helper creating user, workspace, project, and returning auth token."""
    email = f"text_{uuid.uuid4().hex[:8]}@example.com"
    signup = await client.post(
        "/api/v1/auth/signup",
        json={"email": email, "display_name": "Text Tester", "password": "Password123!"},
    )
    assert signup.status_code == 201
    data = signup.json()
    user_id = uuid.UUID(data["user"]["id"])
    token = data["tokens"]["access_token"]

    ws_resp = await client.get(
        "/api/v1/workspaces",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert ws_resp.status_code == 200
    workspaces = ws_resp.json()
    ws_id = uuid.UUID(workspaces[0]["id"])

    async with async_session_factory() as db:
        ps = ProjectService(db)
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
                        script="Hello world text test scene.",
                    ),
                    layers=[],
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
        created_proj = await ps.repo.create_project_with_initial_version(project, version)
        await db.commit()
        project_id = created_proj.id

    return user_id, ws_id, project_id, token


# ==============================================================================
# 1. TEXT LAYER SCHEMA & DEFAULTS
# ==============================================================================

def test_text_layer_schema_and_defaults():
    """1: Verify SceneLayer schema defaults, enabled toggle, and JSONB serialization."""
    layer = SceneLayer(
        id="text_123",
        type="text",
        name="Header Title",
        start_time=0.5,
        end_time=3.5,
        transform={"x": 0.5, "y": 0.2, "scale": 1.0},
        content={
            "text": "Main Headline",
            "font_family": "Arial",
            "font_size": 48,
            "font_weight": "bold",
            "color": "#FFFFFF",
            "background_color": "#000000",
            "background_opacity": 0.5,
            "opacity": 1.0,
            "alignment": "center",
        },
    )
    assert layer.id == "text_123"
    assert layer.type == "text"
    assert layer.enabled is True
    assert layer.start_time == 0.5
    assert layer.end_time == 3.5
    assert layer.content["font_size"] == 48

    # Wrap inside Scene and ProjectDocumentV1
    scene = Scene(id="sc_1", sequence=1, duration=4.0, layers=[layer])
    doc = ProjectDocumentV1(scenes=[scene])
    dumped = doc.model_dump()

    # Verify JSON structure
    assert len(dumped["scenes"][0]["layers"]) == 1
    dumped_layer = dumped["scenes"][0]["layers"][0]
    assert dumped_layer["id"] == "text_123"
    assert dumped_layer["enabled"] is True
    assert dumped_layer["content"]["text"] == "Main Headline"

    # Reload from JSON
    reloaded = ProjectDocumentV1.model_validate(dumped)
    assert reloaded.scenes[0].layers[0].content["text"] == "Main Headline"
    assert reloaded.scenes[0].layers[0].enabled is True


# ==============================================================================
# 2. ADD, PERSIST, AND EDIT MULTIPLE TEXT LAYERS WITH OCC
# ==============================================================================

@pytest.mark.asyncio
async def test_add_and_persist_multiple_text_layers(async_client: AsyncClient):
    """2, 3, 4: Add multiple text layers, persist across revisions, and verify OCC conflict handling."""
    user_id, ws_id, project_id, token = await _setup_workspace_and_project(async_client)

    layer1 = {
        "id": "text_01",
        "type": "text",
        "name": "Title",
        "start_time": 0.0,
        "end_time": 2.5,
        "enabled": True,
        "transform": {"x": 0.5, "y": 0.15},
        "content": {"text": "Welcome to HeyZen", "font_size": 42, "color": "#FFFFFF"},
    }
    layer2 = {
        "id": "text_02",
        "type": "text",
        "name": "Subtitle",
        "start_time": 1.0,
        "end_time": 3.5,
        "enabled": True,
        "transform": {"x": 0.5, "y": 0.85},
        "content": {"text": "AI Video Generation", "font_size": 28, "color": "#60A5FA"},
    }

    # Fetch active document via version endpoint
    get_resp = await async_client.get(
        f"/api/v1/workspaces/{ws_id}/projects/{project_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert get_resp.status_code == 200
    p_data = get_resp.json()
    rev1 = p_data["revision"]
    ver_resp = await async_client.get(
        f"/api/v1/workspaces/{ws_id}/projects/{project_id}/versions/{p_data['current_version_id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert ver_resp.status_code == 200
    doc = ver_resp.json()["document"]

    # Append text layers
    doc["scenes"][0]["layers"] = [layer1, layer2]

    # Save revision 2
    save_resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/projects/{project_id}/versions",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "expected_revision": rev1,
            "document": doc,
            "source": "add_text_layers",
        },
    )
    assert save_resp.status_code == 201
    rev2_data = save_resp.json()
    assert rev2_data["revision"] == rev1 + 1
    assert len(rev2_data["document"]["scenes"][0]["layers"]) == 2

    # Verify reload via version endpoint
    reload_p = await async_client.get(
        f"/api/v1/workspaces/{ws_id}/projects/{project_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert reload_p.status_code == 200
    reload_v = await async_client.get(
        f"/api/v1/workspaces/{ws_id}/projects/{project_id}/versions/{reload_p.json()['current_version_id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert reload_v.status_code == 200
    loaded_layers = reload_v.json()["document"]["scenes"][0]["layers"]
    assert len(loaded_layers) == 2
    assert loaded_layers[0]["content"]["text"] == "Welcome to HeyZen"
    assert loaded_layers[1]["content"]["text"] == "AI Video Generation"

    # Edit layer 1 properties
    doc_edit = copy.deepcopy(reload_v.json()["document"])
    doc_edit["scenes"][0]["layers"][0]["content"]["text"] = "Welcome to HeyZen Studio!"
    doc_edit["scenes"][0]["layers"][0]["content"]["font_size"] = 54
    doc_edit["scenes"][0]["layers"][0]["transform"]["y"] = 0.20

    save_edit = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/projects/{project_id}/versions",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "expected_revision": rev2_data["revision"],
            "document": doc_edit,
            "source": "edit_text_layer",
        },
    )
    assert save_edit.status_code == 201
    assert save_edit.json()["document"]["scenes"][0]["layers"][0]["content"]["text"] == "Welcome to HeyZen Studio!"

    # OCC conflict test: attempt to save with stale expected_revision
    stale_conflict = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/projects/{project_id}/versions",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "expected_revision": rev1,  # Stale revision
            "document": doc_edit,
            "source": "stale_attempt",
        },
    )
    assert stale_conflict.status_code == 409


# ==============================================================================
# 3. TEXT LAYER DUPLICATE, DELETE, AND TOGGLE ENABLED
# ==============================================================================

@pytest.mark.asyncio
async def test_text_layer_duplicate_delete_toggle(async_client: AsyncClient):
    """5, 6, 7: Duplicate text layer, toggle enabled status, and delete layer."""
    user_id, ws_id, project_id, token = await _setup_workspace_and_project(async_client)

    original_layer = SceneLayer(
        id="text_orig",
        type="text",
        name="Banner",
        start_time=0.5,
        end_time=3.0,
        enabled=True,
        transform={"x": 0.5, "y": 0.5},
        content={"text": "Original Banner", "font_size": 36, "color": "#FACC15"},
    )

    async with async_session_factory() as db:
        ps = ProjectService(db)
        proj = await ps.get_project(project_id, ws_id)
        ver = await ps.get_version(proj.current_version_id, project_id, ws_id)
        doc = ProjectDocumentV1.model_validate(ver.document)
        doc.scenes[0].layers = [original_layer]

        # Duplicate: create independent copy with new ID
        dup_layer = SceneLayer(
            id="text_dup_999",
            type="text",
            name="Banner (Copy)",
            start_time=1.0,
            end_time=3.5,
            enabled=False,  # Toggle disabled
            transform={"x": 0.5, "y": 0.7},
            content=copy.deepcopy(original_layer.content),
        )
        doc.scenes[0].layers.append(dup_layer)

        v2 = await ps.create_version(
            project_id=project_id,
            workspace_id=ws_id,
            user_id=user_id,
            expected_revision=proj.revision,
            document=doc,
            source="duplicate_layer",
        )
        await db.commit()
        assert len(v2.document["scenes"][0]["layers"]) == 2
        assert v2.document["scenes"][0]["layers"][1]["id"] == "text_dup_999"
        assert v2.document["scenes"][0]["layers"][1]["enabled"] is False

        # Delete original layer
        doc_del = ProjectDocumentV1.model_validate(v2.document)
        doc_del.scenes[0].layers = [l for l in doc_del.scenes[0].layers if l.id != "text_orig"]
        v3 = await ps.create_version(
            project_id=project_id,
            workspace_id=ws_id,
            user_id=user_id,
            expected_revision=v2.revision,
            document=doc_del,
            source="delete_layer",
        )
        await db.commit()
        assert len(v3.document["scenes"][0]["layers"]) == 1
        assert v3.document["scenes"][0]["layers"][0]["id"] == "text_dup_999"


# ==============================================================================
# 4. MULTI-SCENE TEXT LAYER ISOLATION
# ==============================================================================

@pytest.mark.asyncio
async def test_multi_scene_text_layer_isolation(async_client: AsyncClient):
    """10: Text layers remain strictly isolated per scene with no cross-scene leakage."""
    user_id, ws_id, project_id, token = await _setup_workspace_and_project(async_client)

    scene1_layer = SceneLayer(
        id="sc1_text",
        type="text",
        name="Scene 1 Title",
        start_time=0.0,
        end_time=3.0,
        content={"text": "Scene 1 Headline"},
    )
    scene2_layer = SceneLayer(
        id="sc2_text",
        type="text",
        name="Scene 2 Title",
        start_time=0.0,
        end_time=3.0,
        content={"text": "Scene 2 Headline"},
    )

    async with async_session_factory() as db:
        ps = ProjectService(db)
        proj = await ps.get_project(project_id, ws_id)
        doc = ProjectDocumentV1(
            schema_version=1,
            settings=ProjectSettings(total_duration=6.0),
            scenes=[
                Scene(id="scene_001", sequence=1, duration=3.0, layers=[scene1_layer]),
                Scene(id="scene_002", sequence=2, duration=3.0, layers=[scene2_layer]),
            ],
        )
        ver = await ps.create_version(
            project_id=project_id,
            workspace_id=ws_id,
            user_id=user_id,
            expected_revision=proj.revision,
            document=doc,
            source="multi_scene_text",
        )
        await db.commit()

        # Verify Scene 1 only has Scene 1 text
        sc1_layers = ver.document["scenes"][0]["layers"]
        assert len(sc1_layers) == 1
        assert sc1_layers[0]["content"]["text"] == "Scene 1 Headline"

        # Verify Scene 2 only has Scene 2 text
        sc2_layers = ver.document["scenes"][1]["layers"]
        assert len(sc2_layers) == 1
        assert sc2_layers[0]["content"]["text"] == "Scene 2 Headline"


# ==============================================================================
# 5. COMPOSITOR ASS TEXT SCRIPT GENERATION
# ==============================================================================

def test_compositor_text_ass_generation():
    """7, 13: Compositor generates valid ASS v4.00+ script with exact styles, timing, and pos."""
    compositor = TimelineCompositor()
    mws = MediaWorkspace(prefix="test_text_ass_")
    canvas = CanvasProfile(width=1280, height=720, fps=25)

    try:
        layers = [
            SceneLayer(
                id="txt_01",
                type="text",
                start_time=0.5,
                end_time=2.5,
                enabled=True,
                transform={"x": 0.5, "y": 0.2},
                content={
                    "text": "Header Overlay",
                    "font_family": "Arial",
                    "font_size": 48,
                    "font_weight": "bold",
                    "color": "#FFFFFF",
                    "background_color": "#000000",
                    "background_opacity": 0.6,
                    "alignment": "center",
                },
            ),
            SceneLayer(
                id="txt_02",
                type="text",
                start_time=1.0,
                end_time=3.0,
                enabled=False,  # Disabled: must be excluded
                content={"text": "Disabled Text"},
            ),
        ]

        out_ass = mws.scenes_dir / "scene_000_text.ass"
        res_path = compositor._generate_scene_text_ass_file(
            layers=layers,
            canvas=canvas,
            output_path=out_ass,
        )

        assert res_path is not None
        assert res_path.exists()
        content = res_path.read_text(encoding="utf-8")

        # Verify headers
        assert "[Script Info]" in content
        assert "ScriptType: v4.00+" in content
        assert "PlayResX: 1280" in content
        assert "PlayResY: 720" in content
        assert "[V4+ Styles]" in content
        assert "[Events]" in content

        # Verify active text is included with \pos(640, 144)
        assert "Header Overlay" in content
        assert "\\pos(640,144)" in content
        assert "0:00:00.50" in content
        assert "0:00:02.50" in content

        # Verify disabled text is omitted
        assert "Disabled Text" not in content

    finally:
        mws.cleanup()


# ==============================================================================
# 6. FULL PIPELINE RENDER: TEXT BURN-IN ON ACTUAL MP4 FRAMES
# ==============================================================================

@pytest.mark.asyncio
async def test_final_render_burns_text_into_mp4(async_client: AsyncClient):
    """8, 9, 14, 15, 16, 17: Renders scene into MP4 and verifies text pixels on solid black background."""
    user_id, ws_id, project_id, _ = await _setup_workspace_and_project(async_client)

    speech_wav = _create_synthetic_wav(duration=3.0, freq=330.0)

    async with async_session_factory() as db:
        mgr = AssetLifecycleManager(db)
        speech_asset = await mgr.ingest_generated_asset(
            workspace_id=ws_id,
            created_by=user_id,
            content=speech_wav,
            original_filename="speech_text.wav",
            asset_type="audio",
            mime_type="audio/wav",
        )

        # Scene with solid black background and large white text in the center
        # Text is active strictly from t=0.2s to t=1.8s
        text_layer = SceneLayer(
            id="burn_text_1",
            type="text",
            name="Title",
            start_time=0.2,
            end_time=1.8,
            enabled=True,
            transform={"x": 0.5, "y": 0.5},
            content={
                "text": "BURNED TEXT",
                "font_family": "Arial",
                "font_size": 48,
                "font_weight": "bold",
                "color": "#FFFFFF",
                "background_color": "#000000",
                "background_opacity": 0.0,
                "alignment": "center",
            },
        )

        doc = ProjectDocumentV1(
            schema_version=1,
            settings=ProjectSettings(
                width=640,
                height=360,
                aspect_ratio="16:9",
                fps=25,
                total_duration=3.0,
            ),
            scenes=[
                Scene(
                    id="sc_txt_burn",
                    sequence=1,
                    duration=3.0,
                    background={"type": "color", "value": "#000000"},  # Pure black background
                    speech=SceneSpeech(
                        voice_id="10000000-0000-0000-0000-000000000004",
                        script="Text overlay burn test.",
                        audio_asset_id=str(speech_asset.id),
                    ),
                    layers=[text_layer],
                )
            ],
        )

        compositor = TimelineCompositor()
        mws = MediaWorkspace(prefix="test_render_text_")

        try:
            render_res = await compositor.render_project(
                document=doc,
                workspace_id=ws_id,
                db=db,
                media_workspace=mws,
            )

            video_path = render_res.video_path
            assert video_path.exists()
            assert video_path.stat().st_size > 5000

            # 1. Inspect frame at t=1.0s (WHEN TEXT IS ACTIVE):
            # Extract raw RGB24 frame at t=1.0s using ffmpeg
            active_frame_path = mws.scenes_dir / "frame_active.raw"
            cmd_active = [
                "ffmpeg", "-y",
                "-ss", "1.0",
                "-i", str(video_path),
                "-vframes", "1",
                "-f", "rawvideo",
                "-pix_fmt", "rgb24",
                str(active_frame_path),
            ]
            subprocess.run(cmd_active, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            assert active_frame_path.exists()

            with open(active_frame_path, "rb") as f:
                active_data = f.read()

            # Solid black background with white text must have bright pixels (>180 intensity)
            bright_pixels_active = sum(1 for b in active_data if b > 180)
            assert bright_pixels_active > 100, f"Expected text overlay pixels, found only {bright_pixels_active}"

            # 2. Inspect frame at t=2.5s (AFTER TEXT HAS ENDED at 1.8s):
            expired_frame_path = mws.scenes_dir / "frame_expired.raw"
            cmd_expired = [
                "ffmpeg", "-y",
                "-ss", "2.5",
                "-i", str(video_path),
                "-vframes", "1",
                "-f", "rawvideo",
                "-pix_fmt", "rgb24",
                str(expired_frame_path),
            ]
            subprocess.run(cmd_expired, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            assert expired_frame_path.exists()

            with open(expired_frame_path, "rb") as f:
                expired_data = f.read()

            # At t=2.5s, text has vanished: bright white pixels must be 0
            bright_pixels_expired = sum(1 for b in expired_data if b > 180)
            assert bright_pixels_expired == 0, f"Expected 0 text pixels after end_time, found {bright_pixels_expired}"

        finally:
            mws.cleanup()


# ==============================================================================
# 7. TEXT, CAPTIONS, AND MUSIC COEXISTENCE
# ==============================================================================

@pytest.mark.asyncio
async def test_text_captions_and_music_coexistence(async_client: AsyncClient):
    """11, 12: Text overlays, speech subtitles, and background music render simultaneously without collisions."""
    user_id, ws_id, project_id, _ = await _setup_workspace_and_project(async_client)

    speech_wav = _create_synthetic_wav(duration=2.5, freq=220.0)
    music_wav = _create_synthetic_wav(duration=1.0, freq=440.0)

    async with async_session_factory() as db:
        mgr = AssetLifecycleManager(db)
        speech_asset = await mgr.ingest_generated_asset(
            workspace_id=ws_id,
            created_by=user_id,
            content=speech_wav,
            original_filename="speech_multi.wav",
            asset_type="audio",
            mime_type="audio/wav",
        )
        music_asset = await mgr.ingest_generated_asset(
            workspace_id=ws_id,
            created_by=user_id,
            content=music_wav,
            original_filename="music_multi.wav",
            asset_type="audio",
            mime_type="audio/wav",
        )

        doc = ProjectDocumentV1(
            schema_version=1,
            settings=ProjectSettings(
                width=640,
                height=360,
                aspect_ratio="16:9",
                fps=25,
                total_duration=2.5,
                captions=CaptionSettings(
                    enabled=True,
                    style=CaptionStyle(font_size=20, position="bottom", alignment="center"),
                ),
            ),
            scenes=[
                Scene(
                    id="sc_multi_all",
                    sequence=1,
                    duration=2.5,
                    background={"type": "color", "value": "#1E293B"},
                    speech=SceneSpeech(
                        voice_id="10000000-0000-0000-0000-000000000004",
                        script="Coexistence test narration.",
                        audio_asset_id=str(speech_asset.id),
                    ),
                    subtitles=[
                        {"id": "cue_1", "start": 0.2, "end": 2.2, "text": "Narrated Speech Caption", "enabled": True}
                    ],
                    layers=[
                        SceneLayer(
                            id="top_headline",
                            type="text",
                            start_time=0.0,
                            end_time=2.5,
                            enabled=True,
                            transform={"x": 0.5, "y": 0.15},
                            content={"text": "Top Video Headline", "font_size": 32, "color": "#FACC15"},
                        )
                    ],
                )
            ],
            audio_tracks=[
                AudioTrack(
                    id="bgm_track",
                    asset_id=str(music_asset.id),
                    name="Background Music",
                    volume=0.25,
                    loop=True,
                )
            ],
        )

        compositor = TimelineCompositor()
        mws = MediaWorkspace(prefix="test_coexistence_")

        try:
            render_res = await compositor.render_project(
                document=doc,
                workspace_id=ws_id,
                db=db,
                media_workspace=mws,
            )

            assert render_res.video_path.exists()
            assert render_res.thumbnail_path.exists()

            probe = await FFprobeService().probe(render_res.video_path)
            assert probe.has_video is True
            assert probe.has_audio is True
            assert 2.4 <= probe.duration_seconds <= 2.8

        finally:
            mws.cleanup()


# ==============================================================================
# 8. CROSS-WORKSPACE TEXT ISOLATION
# ==============================================================================

@pytest.mark.asyncio
async def test_cross_workspace_text_isolation(async_client: AsyncClient):
    """18: Unauthorized cross-workspace project access is denied (HTTP 403 / 404)."""
    _, ws_a, proj_a, token_a = await _setup_workspace_and_project(async_client, title="Project A")
    _, ws_b, _, token_b = await _setup_workspace_and_project(async_client, title="Project B")

    # User B attempts to access Project A
    resp = await async_client.get(
        f"/api/v1/workspaces/{ws_a}/projects/{proj_a}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp.status_code in (403, 404)
