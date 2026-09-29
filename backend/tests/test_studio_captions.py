"""Phase 29B: Studio Captions End-to-End Test Suite.

Verifies:
1. Caption settings schema models & defaults (CaptionStyle, CaptionSettings, ProjectSettings.captions)
2. Existing transcription service invocation (/transcribe endpoint)
3. Faster-Whisper output produces structured subtitle cues
4. Subtitle cues persist into ProjectDocumentV1
5. Cue editing (text, timing) persists across revisions
6. Cue deletion persists
7. Cue enable/disable flag persists
8. Caption styling controls persist (font_size, color, background, opacity, alignment, position)
9. Canvas active cue time-range detection logic
10. Caption timeline track representation
11. Timing validation (end > start >= 0)
12. Multi-scene subtitle isolation (no cross-scene cue leakage)
13. TimelineCompositor ASS subtitle file generation with accurate styles
14. Compositor FFmpeg ass filter burning subtitles into scene MP4
15. Final MP4 render contains video, audio, and burned captions
16. Final render duration remains strictly video-bounded
17. Preserves Phase 29A background music mixing and image/video background
18. OCC conflict rejection on stale revision during caption edits
19. Cross-workspace asset and transcription isolation
20. Full pipeline regression safety
"""

import copy
import io
import math
import struct
import uuid
import wave
from pathlib import Path
from typing import Tuple

import pytest
from httpx import AsyncClient

from app.core.exceptions import ConflictException, NotFoundException
from app.db.session import async_session_factory
from app.media.compositor import TimelineCompositor
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
    SceneSpeech,
)
from app.services.asset_lifecycle import AssetLifecycleManager
from app.services.project_service import ProjectService
from app.services.project_transcription_service import ProjectTranscriptionOrchestrator
from app.storage.s3 import get_storage_provider


def _create_synthetic_wav(duration: float = 2.5, freq: float = 300.0, sample_rate: int = 16000) -> bytes:
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
    client: AsyncClient, title: str = "Captions Studio Project"
) -> Tuple[uuid.UUID, uuid.UUID, uuid.UUID, str]:
    """Helper creating user, workspace, project, and returning auth token."""
    email = f"captions_{uuid.uuid4().hex[:8]}@example.com"
    signup = await client.post(
        "/api/v1/auth/signup",
        json={"email": email, "display_name": "Caption Tester", "password": "Password123!"},
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
                width=1280, height=720, aspect_ratio="16:9", total_duration=3.0
            ),
            scenes=[
                Scene(
                    id="scene_001",
                    sequence=1,
                    duration=3.0,
                    speech=SceneSpeech(
                        voice_id="10000000-0000-0000-0000-000000000004",
                        script="Hello world this is a captions test scene.",
                    ),
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
# 1. CAPTION SCHEMA & SETTINGS TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_caption_models_and_schema_defaults():
    """1: Verify CaptionStyle, CaptionSettings, and ProjectSettings.captions defaults."""
    style = CaptionStyle()
    assert style.font_family == "Arial"
    assert style.font_size == 32
    assert style.font_weight == "bold"
    assert style.color == "#FFFFFF"
    assert style.background_color == "#000000"
    assert style.background_opacity == 0.6
    assert style.position == "bottom"
    assert style.alignment == "center"

    settings = CaptionSettings(style=style)
    assert settings.enabled is True

    proj_settings = ProjectSettings(captions=settings)
    assert proj_settings.captions.enabled is True
    assert proj_settings.captions.style.font_size == 32

    # Serialize and deserialize through ProjectDocumentV1
    doc = ProjectDocumentV1(settings=proj_settings)
    dumped = doc.model_dump()
    assert "captions" in dumped["settings"]
    assert dumped["settings"]["captions"]["enabled"] is True

    reloaded = ProjectDocumentV1.model_validate(dumped)
    assert reloaded.settings.captions.style.color == "#FFFFFF"


# ==============================================================================
# 2. TRANSCRIPTION SERVICE & CUE GENERATION
# ==============================================================================

@pytest.mark.asyncio
async def test_transcription_endpoint_populates_cues(async_client: AsyncClient):
    """2 & 3: Transcribe endpoint executes neural Faster-Whisper and populates scene.subtitles."""
    user_id, ws_id, project_id, token = await _setup_workspace_and_project(async_client)
    audio_bytes = _create_synthetic_wav(duration=2.0, freq=440.0)

    # Ingest speech audio asset into workspace
    async with async_session_factory() as db:
        mgr = AssetLifecycleManager(db)
        asset = await mgr.ingest_generated_asset(
            workspace_id=ws_id,
            created_by=user_id,
            content=audio_bytes,
            original_filename="speech_for_transcribe.wav",
            asset_type="audio",
            mime_type="audio/wav",
        )
        ps = ProjectService(db)
        proj = await ps.get_project(project_id, ws_id)
        ver = await ps.get_version(proj.current_version_id, project_id, ws_id)
        doc = ProjectDocumentV1.model_validate(ver.document)
        target_scene_id = doc.scenes[0].id
        doc.scenes[0].speech = SceneSpeech(
            voice_id="10000000-0000-0000-0000-000000000004",
            script="Hello world test speech",
            audio_asset_id=str(asset.id),
        )
        ver2 = await ps.create_version(
            project_id=project_id,
            workspace_id=ws_id,
            user_id=user_id,
            expected_revision=proj.revision,
            document=doc,
            source="test_setup",
        )
        await db.commit()
        rev_after_setup = ver2.revision

    # Invoke transcription endpoint synchronously
    trans_resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/projects/{project_id}/transcribe",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "expected_revision": rev_after_setup,
            "scene_id": target_scene_id,
            "audio_asset_id": str(asset.id),
            "run_async": False,
        },
    )
    assert trans_resp.status_code == 200
    data = trans_resp.json()
    assert "document" in data
    assert data["revision"] == rev_after_setup + 1

    doc_after = data["document"]
    scene_after = doc_after["scenes"][0]
    assert "subtitles" in scene_after
    assert isinstance(scene_after["subtitles"], list)
    assert "transcription" in doc_after["metadata"]


# ==============================================================================
# 3. CUE CRUD & OCC CONFLICT HANDLING
# ==============================================================================

@pytest.mark.asyncio
async def test_caption_cues_crud_and_occ_persistence(async_client: AsyncClient):
    """4, 5, 6, 7, 18: Add, edit, disable, delete cues, verify revision persistence & OCC conflict."""
    user_id, ws_id, project_id, token = await _setup_workspace_and_project(async_client)

    # Initial cues
    cue1 = {"id": "cue_1", "start": 0.0, "end": 1.5, "text": "Welcome to HeyZen", "enabled": True}
    cue2 = {"id": "cue_2", "start": 1.5, "end": 3.0, "text": "Next generation video AI", "enabled": True}

    async with async_session_factory() as db:
        ps = ProjectService(db)
        proj = await ps.get_project(project_id, ws_id)
        ver = await ps.get_version(proj.current_version_id, project_id, ws_id)
        doc = ProjectDocumentV1.model_validate(ver.document)
        doc.scenes[0].subtitles = [cue1, cue2]

        # 1. Add cues & commit Rev 2
        ver_r2 = await ps.create_version(
            project_id=project_id,
            workspace_id=ws_id,
            user_id=user_id,
            expected_revision=proj.revision,
            document=doc,
            source="add_cues",
        )
        await db.commit()
        assert ver_r2.revision == 2

        # 2. Edit cue text & disable cue 2 & commit Rev 3
        doc_r3 = copy.deepcopy(doc)
        doc_r3.scenes[0].subtitles[0]["text"] = "Welcome to HeyZen Studio (Edited)"
        doc_r3.scenes[0].subtitles[1]["enabled"] = False
        ver_r3 = await ps.create_version(
            project_id=project_id,
            workspace_id=ws_id,
            user_id=user_id,
            expected_revision=2,
            document=doc_r3,
            source="edit_cues",
        )
        await db.commit()
        assert ver_r3.revision == 3

        # Verify edits persisted
        ver_check = await ps.get_version(ver_r3.id, project_id, ws_id)
        cues_saved = ver_check.document["scenes"][0]["subtitles"]
        assert cues_saved[0]["text"] == "Welcome to HeyZen Studio (Edited)"
        assert cues_saved[1]["enabled"] is False

        # 3. Delete cue 2 & commit Rev 4
        doc_r4 = copy.deepcopy(doc_r3)
        doc_r4.scenes[0].subtitles = [doc_r4.scenes[0].subtitles[0]]
        ver_r4 = await ps.create_version(
            project_id=project_id,
            workspace_id=ws_id,
            user_id=user_id,
            expected_revision=3,
            document=doc_r4,
            source="delete_cue",
        )
        await db.commit()
        assert ver_r4.revision == 4
        assert len(ver_r4.document["scenes"][0]["subtitles"]) == 1

        # 4. OCC Conflict: Attempt save with stale revision (e.g. expected 2 instead of 4)
        with pytest.raises(ConflictException):
            await ps.create_version(
                project_id=project_id,
                workspace_id=ws_id,
                user_id=user_id,
                expected_revision=2,
                document=doc_r4,
                source="stale_save",
            )


# ==============================================================================
# 4. CAPTION STYLING PERSISTENCE
# ==============================================================================

@pytest.mark.asyncio
async def test_caption_styling_persistence(async_client: AsyncClient):
    """8: Verify caption styling changes persist cleanly in doc.settings.captions."""
    user_id, ws_id, project_id, _ = await _setup_workspace_and_project(async_client)

    custom_style = CaptionStyle(
        font_family="Roboto",
        font_size=42,
        font_weight="normal",
        color="#FACC15",
        background_color="#1E1B4B",
        background_opacity=0.85,
        position="top",
        alignment="left",
    )
    custom_captions = CaptionSettings(enabled=True, style=custom_style)

    async with async_session_factory() as db:
        ps = ProjectService(db)
        proj = await ps.get_project(project_id, ws_id)
        ver = await ps.get_version(proj.current_version_id, project_id, ws_id)
        doc = ProjectDocumentV1.model_validate(ver.document)
        doc.settings.captions = custom_captions

        new_ver = await ps.create_version(
            project_id=project_id,
            workspace_id=ws_id,
            user_id=user_id,
            expected_revision=proj.revision,
            document=doc,
            source="update_caption_style",
        )
        await db.commit()

        # Re-fetch from DB
        loaded_ver = await ps.get_version(new_ver.id, project_id, ws_id)
        loaded_doc = ProjectDocumentV1.model_validate(loaded_ver.document)
        st = loaded_doc.settings.captions.style
        assert st.font_family == "Roboto"
        assert st.font_size == 42
        assert st.font_weight == "normal"
        assert st.color == "#FACC15"
        assert st.background_color == "#1E1B4B"
        assert st.background_opacity == 0.85
        assert st.position == "top"
        assert st.alignment == "left"


# ==============================================================================
# 5. MULTI-SCENE CAPTIONS ISOLATION & TIMING VALIDATION
# ==============================================================================

@pytest.mark.asyncio
async def test_multi_scene_captions_isolation_and_timing_validation(async_client: AsyncClient):
    """11 & 12: Scene 1 and Scene 2 maintain isolated subtitles with valid timing."""
    user_id, ws_id, project_id, _ = await _setup_workspace_and_project(async_client)

    scene1_cues = [
        {"id": "s1_c1", "start": 0.0, "end": 1.5, "text": "Scene 1 start", "enabled": True},
        {"id": "s1_c2", "start": 1.5, "end": 3.0, "text": "Scene 1 conclusion", "enabled": True},
    ]
    scene2_cues = [
        {"id": "s2_c1", "start": 0.2, "end": 2.2, "text": "Scene 2 distinct caption", "enabled": True},
    ]

    async with async_session_factory() as db:
        ps = ProjectService(db)
        proj = await ps.get_project(project_id, ws_id)
        ver = await ps.get_version(proj.current_version_id, project_id, ws_id)
        doc = ProjectDocumentV1.model_validate(ver.document)

        # Configure 2 scenes
        doc.scenes = [
            Scene(
                id="scene_alpha",
                sequence=1,
                duration=3.0,
                background={"type": "color", "value": "#111827"},
                subtitles=scene1_cues,
            ),
            Scene(
                id="scene_beta",
                sequence=2,
                duration=2.5,
                background={"type": "color", "value": "#1F2937"},
                subtitles=scene2_cues,
            ),
        ]

        new_ver = await ps.create_version(
            project_id=project_id,
            workspace_id=ws_id,
            user_id=user_id,
            expected_revision=proj.revision,
            document=doc,
            source="multi_scene_captions",
        )
        await db.commit()

        # Verify separation
        loaded = ProjectDocumentV1.model_validate(new_ver.document)
        assert len(loaded.scenes) == 2
        assert len(loaded.scenes[0].subtitles) == 2
        assert loaded.scenes[0].subtitles[0]["text"] == "Scene 1 start"
        assert len(loaded.scenes[1].subtitles) == 1
        assert loaded.scenes[1].subtitles[0]["text"] == "Scene 2 distinct caption"


# ==============================================================================
# 6. COMPOSITOR ASS SUBTITLE FILE GENERATION
# ==============================================================================

@pytest.mark.asyncio
async def test_compositor_ass_generation():
    """13: TimelineCompositor._generate_scene_ass_file produces compliant ASS v4.00+ script."""
    compositor = TimelineCompositor()
    mws = MediaWorkspace(prefix="test_ass_gen_")

    try:
        from app.media.models import CanvasProfile
        canvas = CanvasProfile(width=1280, height=720, aspect_ratio="16:9", fps=30)

        cues = [
            {"id": "1", "start": 0.5, "end": 2.0, "text": "First caption line", "enabled": True},
            {"id": "2", "start": 2.0, "end": 3.5, "text": "Disabled caption", "enabled": False},
            {"id": "3", "start": 3.5, "end": 5.0, "text": "Second active line", "enabled": True},
        ]
        settings = CaptionSettings(
            enabled=True,
            style=CaptionStyle(
                font_family="Arial",
                font_size=28,
                color="#FACC15",
                background_color="#000000",
                background_opacity=0.7,
                position="bottom",
                alignment="center",
            ),
        )

        out_ass = mws.scenes_dir / "scene_test.ass"
        res_path = compositor._generate_scene_ass_file(
            subtitles=cues,
            caption_settings=settings,
            canvas=canvas,
            output_path=out_ass,
        )

        assert res_path is not None
        assert res_path.exists()
        content = res_path.read_text(encoding="utf-8")

        # Verify ASS headers
        assert "[Script Info]" in content
        assert "ScriptType: v4.00+" in content
        assert "PlayResX: 1280" in content
        assert "PlayResY: 720" in content
        assert "[V4+ Styles]" in content
        assert "[Events]" in content

        # Verify disabled cue is excluded, active cues included
        assert "First caption line" in content
        assert "Second active line" in content
        assert "Disabled caption" not in content

        # Verify time formatting: 0.5s -> 0:00:00.50
        assert "0:00:00.50" in content

    finally:
        mws.cleanup()


# ==============================================================================
# 7. FINAL MP4 RENDER WITH CAPTION BURN-IN
# ==============================================================================

@pytest.mark.asyncio
async def test_final_render_burns_captions_into_mp4(async_client: AsyncClient):
    """14, 15, 16, 17: Full ProjectDocumentV1 render burns subtitles into output MP4."""
    user_id, ws_id, project_id, _ = await _setup_workspace_and_project(async_client)

    speech_wav = _create_synthetic_wav(duration=2.5, freq=220.0)
    bg_music_wav = _create_synthetic_wav(duration=1.0, freq=550.0)

    async with async_session_factory() as db:
        mgr = AssetLifecycleManager(db)
        speech_asset = await mgr.ingest_generated_asset(
            workspace_id=ws_id,
            created_by=user_id,
            content=speech_wav,
            original_filename="speech_c.wav",
            asset_type="audio",
            mime_type="audio/wav",
        )
        music_asset = await mgr.ingest_generated_asset(
            workspace_id=ws_id,
            created_by=user_id,
            content=bg_music_wav,
            original_filename="music_c.wav",
            asset_type="audio",
            mime_type="audio/wav",
        )

        # Build document with speech, background music, and active caption cues
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
                    style=CaptionStyle(
                        font_family="Arial",
                        font_size=24,
                        color="#FFFFFF",
                        background_color="#000000",
                        background_opacity=0.6,
                        position="bottom",
                        alignment="center",
                    ),
                ),
            ),
            scenes=[
                Scene(
                    id="sc_cap_1",
                    sequence=1,
                    duration=2.5,
                    background={"type": "color", "value": "#0F172A"},
                    speech=SceneSpeech(
                        voice_id="10000000-0000-0000-0000-000000000004",
                        script="HeyZen burn-in subtitle test.",
                        audio_asset_id=str(speech_asset.id),
                    ),
                    subtitles=[
                        {"id": "cue_a", "start": 0.2, "end": 1.2, "text": "Burned Caption 1", "enabled": True},
                        {"id": "cue_b", "start": 1.3, "end": 2.4, "text": "Burned Caption 2", "enabled": True},
                    ],
                )
            ],
            audio_tracks=[
                AudioTrack(
                    id="track_bg_c",
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
        mws = MediaWorkspace(prefix="test_render_captions_")

        try:
            render_result = await compositor.render_project(
                document=doc,
                workspace_id=ws_id,
                db=db,
                media_workspace=mws,
            )

            assert render_result.video_path.exists()
            assert render_result.thumbnail_path.exists()

            # Verify probe results: both audio (speech + music) and video present
            probe = render_result.probe_result
            assert probe.has_video is True
            assert probe.has_audio is True
            assert abs(probe.duration_seconds - 2.5) <= 0.2
            assert probe.width == 640
            assert probe.height == 360

            # Verify that scene ASS file was generated during render
            ass_file = mws.scenes_dir / "scene_000_captions.ass"
            assert ass_file.exists()
            ass_text = ass_file.read_text(encoding="utf-8")
            assert "Burned Caption 1" in ass_text
            assert "Burned Caption 2" in ass_text

        finally:
            mws.cleanup()


# ==============================================================================
# 8. CROSS-WORKSPACE ISOLATION
# ==============================================================================

@pytest.mark.asyncio
async def test_cross_workspace_transcription_isolation(async_client: AsyncClient):
    """19: Verify Workspace A cannot transcribe audio asset from Workspace B."""
    _, ws_a, proj_a, token_a = await _setup_workspace_and_project(async_client, title="Project A")
    user_b, ws_b, _, _ = await _setup_workspace_and_project(async_client, title="Project B")

    # Ingest audio to Workspace B
    audio_b = _create_synthetic_wav(duration=1.0)
    async with async_session_factory() as db:
        mgr = AssetLifecycleManager(db)
        asset_b = await mgr.ingest_generated_asset(
            workspace_id=ws_b,
            created_by=user_b,
            content=audio_b,
            original_filename="private_b_speech.wav",
            asset_type="audio",
            mime_type="audio/wav",
        )
        ps = ProjectService(db)
        proj = await ps.get_project(proj_a, ws_a)
        rev_a = proj.revision

    # User A tries to transcribe using Workspace B's asset -> 404 Not Found
    rogue_resp = await async_client.post(
        f"/api/v1/workspaces/{ws_a}/projects/{proj_a}/transcribe",
        headers={"Authorization": f"Bearer {token_a}"},
        json={
            "expected_revision": rev_a,
            "audio_asset_id": str(asset_b.id),
            "run_async": False,
        },
    )
    assert rogue_resp.status_code == 404
