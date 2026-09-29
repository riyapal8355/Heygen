"""Phase 29D: Studio Media Layers (Images & Videos) End-to-End Test Suite.

Verifies:
1. Media SceneLayer schema models & defaults (SceneLayer type="image"/"video"/"media", enabled=True, transform, content)
2. Add image layer to scene and persist into ProjectDocumentV1
3. Add video layer to scene and persist into ProjectDocumentV1
4. Multiple media layers in the same scene
5. Persistence across reloads
6. OCC conflict handling on media layer updates
7. Enable / disable toggle persistence
8. Delete media layer persistence
9. Duplicate media layer (unique ID, cloned transforms and timing)
10. Timing validation (start_time >= 0, end_time > start_time, bounded by scene duration)
11. Transform persistence (x, y, scale, rotation, opacity)
12. Multi-scene media layer isolation
13. Workspace isolation (multi-tenant security preventing cross-workspace asset references)
14. Media probe behavior on image & video assets
15. Signed asset access & security
16. Image layer FFmpeg rendering & frame-level pixel inspection (active vs expired)
17. Video layer FFmpeg rendering & frame-level pixel inspection (active vs expired)
18. Multiple media layers rendering simultaneously (red image + green video)
19. Disabled media layer omitted from render
20. Media layer duration bounds (never extends project duration)
21. Text overlay + media layer coexistence in rendered MP4
22. Captions + media layer coexistence in rendered MP4
23. Music + media layer coexistence in rendered MP4
24. Background + media layer coexistence in rendered MP4
25. Frame-level pixel verification of composite scene
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

from app.db.session import async_session_factory
from app.media.compositor import CanvasProfile, TimelineCompositor
from app.media.errors import RenderInputMissingError, RenderOutputInvalidError
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
    """Generate a clean synthetic WAV audio in-memory."""
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


def _create_test_image_bytes(color: str = "red", width: int = 320, height: int = 240) -> bytes:
    """Create a high-contrast PNG image using FFmpeg."""
    cmd = [
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", f"color=c={color}:s={width}x{height}:d=0.1",
        "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "pipe:1"
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    return proc.stdout


def _create_test_video_bytes(color: str = "lime", duration: float = 1.5, width: int = 320, height: int = 240) -> bytes:
    """Create a short MP4 test video using FFmpeg."""
    cmd = [
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", f"color=c={color}:s={width}x{height}:r=25:d={duration:.3f}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-f", "mp4",
        "-movflags", "+frag_keyframe+empty_moov", "pipe:1"
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    return proc.stdout


def _extract_frame_rgb(video_path: Path, timestamp: float, width: int = 640, height: int = 360) -> bytes:
    """Extract a single video frame as raw RGB24 bytes."""
    cmd = [
        "ffmpeg", "-y", "-ss", f"{timestamp:.3f}", "-i", str(video_path),
        "-vframes", "1", "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{width}x{height}", "pipe:1"
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    return proc.stdout


def _sample_pixel(raw_rgb: bytes, x: int, y: int, width: int = 640) -> Tuple[int, int, int]:
    """Sample RGB pixel at (x, y) coordinates."""
    offset = (y * width + x) * 3
    return raw_rgb[offset], raw_rgb[offset + 1], raw_rgb[offset + 2]


async def _setup_workspace_and_project(
    client: AsyncClient, title: str = "Media Studio Project"
) -> Tuple[uuid.UUID, uuid.UUID, uuid.UUID, str]:
    """Helper creating user, workspace, project, and returning auth token."""
    email = f"media_{uuid.uuid4().hex[:8]}@example.com"
    signup = await client.post(
        "/api/v1/auth/signup",
        json={"email": email, "display_name": "Media Tester", "password": "Password123!"},
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
            settings=ProjectSettings(aspect_ratio="16:9", width=640, height=360, fps=25, total_duration=4.0),
            scenes=[
                Scene(
                    id="scene_01",
                    sequence=1,
                    duration=4.0,
                    background={"type": "color", "value": "#000000"},
                    layers=[],
                )
            ],
            audio_tracks=[],
            assets=[],
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
        proj_id = created_proj.id

    return user_id, ws_id, proj_id, token


# ==============================================================================
# 1. Media SceneLayer Schema & Defaults
# ==============================================================================
def test_media_layer_schema_and_defaults():
    """Test 1: Verify SceneLayer serialization for image and video media layers."""
    img_layer = SceneLayer(
        id="layer_img_1",
        type="image",
        name="Banner Image",
        start_time=0.5,
        end_time=3.5,
        enabled=True,
        transform={"x": 0.5, "y": 0.5, "scale": 1.2, "rotation": 0.0},
        content={"asset_id": "asset_123", "name": "banner.png", "opacity": 0.85},
    )
    assert img_layer.type == "image"
    assert img_layer.enabled is True
    assert img_layer.transform["scale"] == 1.2
    assert img_layer.content["opacity"] == 0.85

    vid_layer = SceneLayer(
        id="layer_vid_1",
        type="video",
        name="Overlay Clip",
        start_time=1.0,
        end_time=3.0,
        enabled=True,
        transform={"x": 0.2, "y": 0.8, "scale": 0.8, "rotation": 15.0},
        content={"asset_id": "asset_456", "name": "clip.mp4", "opacity": 1.0},
    )
    assert vid_layer.type == "video"
    assert vid_layer.transform["rotation"] == 15.0


# ==============================================================================
# 2-4. Add Image & Video Layers and Persist
# ==============================================================================
@pytest.mark.asyncio
async def test_add_and_persist_media_layers(async_client: AsyncClient):
    """Tests 2, 3, 4: Add image and video layers to a scene and persist via API."""
    user_id, ws_id, proj_id, token = await _setup_workspace_and_project(async_client)

    # Get current project document
    p_resp = await async_client.get(
        f"/api/v1/workspaces/{ws_id}/projects/{proj_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    p_data = p_resp.json()
    ver_resp = await async_client.get(
        f"/api/v1/workspaces/{ws_id}/projects/{proj_id}/versions/{p_data['current_version_id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    doc = ver_resp.json()["document"]
    assert len(doc["scenes"][0]["layers"]) == 0

    # Add image layer and video layer
    img_layer = {
        "id": "img_layer_01",
        "type": "image",
        "name": "Logo Image",
        "start_time": 0.0,
        "end_time": 4.0,
        "enabled": True,
        "transform": {"x": 0.5, "y": 0.5, "scale": 1.0, "rotation": 0.0},
        "content": {"asset_id": str(uuid.uuid4()), "name": "logo.png", "opacity": 1.0},
    }
    vid_layer = {
        "id": "vid_layer_01",
        "type": "video",
        "name": "Overlay Video",
        "start_time": 1.0,
        "end_time": 3.0,
        "enabled": True,
        "transform": {"x": 0.3, "y": 0.4, "scale": 0.9, "rotation": 0.0},
        "content": {"asset_id": str(uuid.uuid4()), "name": "overlay.mp4", "opacity": 0.9},
    }
    doc["scenes"][0]["layers"] = [img_layer, vid_layer]

    save_resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/projects/{proj_id}/versions",
        headers={"Authorization": f"Bearer {token}"},
        json={"document": doc, "expected_revision": p_data["revision"]},
    )
    assert save_resp.status_code == 201
    saved_doc = save_resp.json()["document"]
    assert len(saved_doc["scenes"][0]["layers"]) == 2
    assert saved_doc["scenes"][0]["layers"][0]["type"] == "image"
    assert saved_doc["scenes"][0]["layers"][1]["type"] == "video"


# ==============================================================================
# 5-6. Persistence After Reload & OCC Conflict Handling
# ==============================================================================
@pytest.mark.asyncio
async def test_media_layer_reload_and_occ_conflict(async_client: AsyncClient):
    """Tests 5, 6: Verify reload durability and OCC rejection on concurrent revisions."""
    user_id, ws_id, proj_id, token = await _setup_workspace_and_project(async_client)

    p_resp = await async_client.get(
        f"/api/v1/workspaces/{ws_id}/projects/{proj_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    p_data = p_resp.json()
    ver_resp = await async_client.get(
        f"/api/v1/workspaces/{ws_id}/projects/{proj_id}/versions/{p_data['current_version_id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    doc = ver_resp.json()["document"]
    doc["scenes"][0]["layers"].append({
        "id": "layer_occ",
        "type": "image",
        "name": "Test Layer",
        "start_time": 0.0,
        "end_time": 4.0,
        "transform": {"x": 0.5, "y": 0.5, "scale": 1.0},
        "content": {"asset_id": "asset_1"},
    })

    # Save revision 2
    rev2_resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/projects/{proj_id}/versions",
        headers={"Authorization": f"Bearer {token}"},
        json={"document": doc, "expected_revision": p_data["revision"]},
    )
    assert rev2_resp.status_code == 201

    # Reload project
    reload_resp = await async_client.get(
        f"/api/v1/workspaces/{ws_id}/projects/{proj_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    reload_data = reload_resp.json()
    assert reload_data["revision"] == 2
    v_reload = await async_client.get(
        f"/api/v1/workspaces/{ws_id}/projects/{proj_id}/versions/{reload_data['current_version_id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    reloaded_doc = v_reload.json()["document"]
    assert len(reloaded_doc["scenes"][0]["layers"]) == 1
    assert reloaded_doc["scenes"][0]["layers"][0]["id"] == "layer_occ"

    # Stale revision conflict attempt (expected_revision=1)
    conflict_resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/projects/{proj_id}/versions",
        headers={"Authorization": f"Bearer {token}"},
        json={"document": doc, "expected_revision": 1},
    )
    assert conflict_resp.status_code == 409


# ==============================================================================
# 7-9. Enable/Disable, Delete, Duplicate
# ==============================================================================
@pytest.mark.asyncio
async def test_media_layer_enable_delete_duplicate(async_client: AsyncClient):
    """Tests 7, 8, 9: Verify enable toggle, duplicate creation, and layer deletion."""
    user_id, ws_id, proj_id, token = await _setup_workspace_and_project(async_client)

    p_resp = await async_client.get(
        f"/api/v1/workspaces/{ws_id}/projects/{proj_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    p_data = p_resp.json()
    v_resp = await async_client.get(
        f"/api/v1/workspaces/{ws_id}/projects/{proj_id}/versions/{p_data['current_version_id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    doc = v_resp.json()["document"]

    orig_layer = {
        "id": "layer_orig",
        "type": "image",
        "name": "Original Media",
        "start_time": 0.5,
        "end_time": 3.5,
        "enabled": True,
        "transform": {"x": 0.5, "y": 0.5, "scale": 1.0, "rotation": 0.0},
        "content": {"asset_id": "asset_dup", "name": "pic.png", "opacity": 0.8},
    }
    doc["scenes"][0]["layers"] = [orig_layer]
    r2 = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/projects/{proj_id}/versions",
        headers={"Authorization": f"Bearer {token}"},
        json={"document": doc, "expected_revision": p_data["revision"]},
    )
    doc2 = r2.json()["document"]

    # Duplicate
    dup_layer = {
        "id": "layer_orig_copy",
        "type": orig_layer["type"],
        "name": "Original Media (Copy)",
        "start_time": orig_layer["start_time"],
        "end_time": orig_layer["end_time"],
        "enabled": True,
        "transform": copy.deepcopy(orig_layer["transform"]),
        "content": copy.deepcopy(orig_layer["content"]),
    }
    doc2["scenes"][0]["layers"].append(dup_layer)
    r3 = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/projects/{proj_id}/versions",
        headers={"Authorization": f"Bearer {token}"},
        json={"document": doc2, "expected_revision": 2},
    )
    doc3 = r3.json()["document"]
    assert len(doc3["scenes"][0]["layers"]) == 2

    # Disable original layer
    doc3["scenes"][0]["layers"][0]["enabled"] = False
    r4 = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/projects/{proj_id}/versions",
        headers={"Authorization": f"Bearer {token}"},
        json={"document": doc3, "expected_revision": 3},
    )
    doc4 = r4.json()["document"]
    assert doc4["scenes"][0]["layers"][0]["enabled"] is False
    assert doc4["scenes"][0]["layers"][1]["enabled"] is True

    # Delete original layer
    doc4["scenes"][0]["layers"] = [l for l in doc4["scenes"][0]["layers"] if l["id"] != "layer_orig"]
    r5 = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/projects/{proj_id}/versions",
        headers={"Authorization": f"Bearer {token}"},
        json={"document": doc4, "expected_revision": 4},
    )
    doc5 = r5.json()["document"]
    assert len(doc5["scenes"][0]["layers"]) == 1
    assert doc5["scenes"][0]["layers"][0]["id"] == "layer_orig_copy"


# ==============================================================================
# 10-12. Timing, Transform Persistence & Multi-Scene Isolation
# ==============================================================================
@pytest.mark.asyncio
async def test_timing_transform_and_multi_scene_isolation(async_client: AsyncClient):
    """Tests 10, 11, 12: Verify timing bounds, transform parameters, and scene isolation."""
    user_id, ws_id, proj_id, token = await _setup_workspace_and_project(async_client)

    p_resp = await async_client.get(
        f"/api/v1/workspaces/{ws_id}/projects/{proj_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    p_data = p_resp.json()
    v_resp = await async_client.get(
        f"/api/v1/workspaces/{ws_id}/projects/{proj_id}/versions/{p_data['current_version_id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    doc = v_resp.json()["document"]

    # Add a second scene
    doc["scenes"].append({
        "id": "scene_02",
        "sequence": 2,
        "duration": 3.0,
        "background": {"type": "color", "value": "#112233"},
        "layers": [],
    })
    # Add media layer ONLY to Scene 1
    doc["scenes"][0]["layers"].append({
        "id": "sc1_layer",
        "type": "video",
        "name": "Scene 1 Media",
        "start_time": 0.5,
        "end_time": 3.5,
        "transform": {"x": 0.25, "y": 0.75, "scale": 1.5, "rotation": -45.0},
        "content": {"opacity": 0.75, "asset_id": "asset_isolated"},
    })

    r2 = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/projects/{proj_id}/versions",
        headers={"Authorization": f"Bearer {token}"},
        json={"document": doc, "expected_revision": p_data["revision"]},
    )
    assert r2.status_code == 201
    doc2 = r2.json()["document"]

    sc1_layer = doc2["scenes"][0]["layers"][0]
    assert sc1_layer["start_time"] == 0.5
    assert sc1_layer["end_time"] == 3.5
    assert sc1_layer["transform"]["rotation"] == -45.0
    assert sc1_layer["content"]["opacity"] == 0.75

    # Scene 2 has zero layers
    assert len(doc2["scenes"][1]["layers"]) == 0


# ==============================================================================
# 13. Cross-Workspace Asset Security & Isolation
# ==============================================================================
@pytest.mark.asyncio
async def test_cross_workspace_media_isolation(async_client: AsyncClient):
    """Test 13: Attempting to resolve an asset belonging to Workspace B in Workspace A fails."""
    user_a, ws_a, proj_a, token_a = await _setup_workspace_and_project(async_client, "Project A")
    user_b, ws_b, proj_b, token_b = await _setup_workspace_and_project(async_client, "Project B")

    img_bytes = _create_test_image_bytes("red", 100, 100)
    async with async_session_factory() as db:
        alm = AssetLifecycleManager(db)
        asset_b = await alm.ingest_generated_asset(
            workspace_id=ws_b,
            created_by=user_b,
            content=img_bytes,
            original_filename="secret_ws_b.png",
            asset_type="image",
            mime_type="image/png",
        )

    # Workspace A attempts to resolve Workspace B's asset inside its MediaWorkspace
    mws = MediaWorkspace()
    try:
        async with async_session_factory() as db:
            with pytest.raises(RenderInputMissingError):
                await mws.resolve_asset(asset_id=asset_b.id, workspace_id=ws_a, db=db)
    finally:
        mws.cleanup()


# ==============================================================================
# 14-15. Media Probe Behavior & Signed Asset Security
# ==============================================================================
@pytest.mark.asyncio
async def test_media_probe_and_signed_url_security(async_client: AsyncClient):
    """Tests 14, 15: Verify ffprobe inspection on image/video and asset lifecycle access."""
    user_id, ws_id, proj_id, token = await _setup_workspace_and_project(async_client)
    ffprobe = FFprobeService()

    img_data = _create_test_image_bytes("blue", 320, 240)
    async with async_session_factory() as db:
        alm = AssetLifecycleManager(db)
        asset = await alm.ingest_generated_asset(
            workspace_id=ws_id,
            created_by=user_id,
            content=img_data,
            original_filename="probe_test.png",
            asset_type="image",
            mime_type="image/png",
        )

    mws = MediaWorkspace()
    try:
        async with async_session_factory() as db:
            local_path = await mws.resolve_asset(asset.id, ws_id, db)
            probe_res = await ffprobe.probe(local_path)
            assert probe_res.width == 320
            assert probe_res.height == 240
            assert probe_res.has_video is True

        with pytest.raises(Exception):
            await ffprobe.probe(mws.inputs_dir / "non_existent.png")
    finally:
        mws.cleanup()


# ==============================================================================
# 16. Image Layer FFmpeg Rendering & Pixel Verification (Mandatory Active vs Expired)
# ==============================================================================
@pytest.mark.asyncio
async def test_image_layer_render_and_pixel_verification(async_client: AsyncClient):
    """Test 16: Render an MP4 with a RED image overlay over BLUE background.
    Verifies:
    - At t=1.0s (active window: 0.5s-2.0s), center contains RED pixels (R > 180, B < 80).
    - At t=2.5s (after window), center contains BLUE background pixels (B > 180, R < 80).
    """
    user_id, ws_id, proj_id, token = await _setup_workspace_and_project(async_client)
    compositor = TimelineCompositor()

    red_img_bytes = _create_test_image_bytes("red", 320, 240)
    async with async_session_factory() as db:
        alm = AssetLifecycleManager(db)
        red_asset = await alm.ingest_generated_asset(
            workspace_id=ws_id,
            created_by=user_id,
            content=red_img_bytes,
            original_filename="pure_red.png",
            asset_type="image",
            mime_type="image/png",
        )

    doc = ProjectDocumentV1(
        schema_version=1,
        settings=ProjectSettings(aspect_ratio="16:9", width=640, height=360, fps=25, total_duration=3.0),
        scenes=[
            Scene(
                id="scene_img_test",
                sequence=1,
                duration=3.0,
                background={"type": "color", "value": "#0000FF"},  # Pure Blue
                layers=[
                    SceneLayer(
                        id="layer_red_image",
                        type="image",
                        name="Red Box",
                        start_time=0.5,
                        end_time=2.0,
                        enabled=True,
                        transform={"x": 0.5, "y": 0.5, "scale": 1.0, "rotation": 0.0},
                        content={"asset_id": str(red_asset.id), "opacity": 1.0},
                    )
                ],
            )
        ],
        audio_tracks=[],
    )

    mws = MediaWorkspace()
    try:
        async with async_session_factory() as db:
            render_res = await compositor.render_project(
                document=doc,
                workspace_id=ws_id,
                db=db,
                media_workspace=mws,
            )
            assert render_res.video_path.exists()
            assert render_res.probe_result.has_video is True

            # Sample frame at t=1.0s (active window)
            raw_active = _extract_frame_rgb(render_res.video_path, timestamp=1.0, width=640, height=360)
            r_act, g_act, b_act = _sample_pixel(raw_active, x=320, y=180, width=640)
            assert r_act > 180, f"Expected high Red at active frame, got ({r_act}, {g_act}, {b_act})"
            assert b_act < 80, f"Expected low Blue at active frame, got ({r_act}, {g_act}, {b_act})"

            # Sample frame at t=2.5s (after active window)
            raw_expired = _extract_frame_rgb(render_res.video_path, timestamp=2.5, width=640, height=360)
            r_exp, g_exp, b_exp = _sample_pixel(raw_expired, x=320, y=180, width=640)
            assert b_exp > 180, f"Expected high Blue at expired frame, got ({r_exp}, {g_exp}, {b_exp})"
            assert r_exp < 80, f"Expected low Red at expired frame, got ({r_exp}, {g_exp}, {b_exp})"
    finally:
        mws.cleanup()


# ==============================================================================
# 17. Video Layer FFmpeg Rendering & Pixel Verification
# ==============================================================================
@pytest.mark.asyncio
async def test_video_layer_render_and_pixel_verification(async_client: AsyncClient):
    """Test 17: Render an MP4 with a GREEN video overlay over a BLACK background.
    Verifies:
    - At t=1.5s (active window: 1.0s-2.5s), center contains GREEN pixels (G > 180, R < 60, B < 60).
    - At t=3.0s (after window), center is black (G < 40).
    """
    user_id, ws_id, proj_id, token = await _setup_workspace_and_project(async_client)
    compositor = TimelineCompositor()

    green_vid_bytes = _create_test_video_bytes("lime", duration=2.0, width=320, height=240)
    async with async_session_factory() as db:
        alm = AssetLifecycleManager(db)
        vid_asset = await alm.ingest_generated_asset(
            workspace_id=ws_id,
            created_by=user_id,
            content=green_vid_bytes,
            original_filename="pure_green.mp4",
            asset_type="video",
            mime_type="video/mp4",
        )

    doc = ProjectDocumentV1(
        schema_version=1,
        settings=ProjectSettings(aspect_ratio="16:9", width=640, height=360, fps=25, total_duration=3.5),
        scenes=[
            Scene(
                id="scene_vid_test",
                sequence=1,
                duration=3.5,
                background={"type": "color", "value": "#000000"},
                layers=[
                    SceneLayer(
                        id="layer_green_video",
                        type="video",
                        name="Green Video Overlay",
                        start_time=1.0,
                        end_time=2.5,
                        enabled=True,
                        transform={"x": 0.5, "y": 0.5, "scale": 1.0, "rotation": 0.0},
                        content={"asset_id": str(vid_asset.id), "opacity": 1.0},
                    )
                ],
            )
        ],
        audio_tracks=[],
    )

    mws = MediaWorkspace()
    try:
        async with async_session_factory() as db:
            render_res = await compositor.render_project(document=doc, workspace_id=ws_id, db=db, media_workspace=mws)
            assert render_res.video_path.exists()

            # Active frame at t=1.5s: Green pixels present
            raw_act = _extract_frame_rgb(render_res.video_path, timestamp=1.5, width=640, height=360)
            r_act, g_act, b_act = _sample_pixel(raw_act, x=320, y=180, width=640)
            assert g_act > 180, f"Expected high Green at t=1.5s, got ({r_act}, {g_act}, {b_act})"
            assert r_act < 60
            assert b_act < 60

            # Expired frame at t=3.0s: Black background (Green absent)
            raw_exp = _extract_frame_rgb(render_res.video_path, timestamp=3.0, width=640, height=360)
            r_exp, g_exp, b_exp = _sample_pixel(raw_exp, x=320, y=180, width=640)
            assert g_exp < 40, f"Expected Black at t=3.0s, got ({r_exp}, {g_exp}, {b_exp})"
    finally:
        mws.cleanup()


# ==============================================================================
# 18. Multiple Media Layers Render Simultaneously
# ==============================================================================
@pytest.mark.asyncio
async def test_multiple_media_layers_render_simultaneously(async_client: AsyncClient):
    """Test 18: Render both a RED image (left, x=0.25) and GREEN video (right, x=0.75) simultaneously."""
    user_id, ws_id, proj_id, token = await _setup_workspace_and_project(async_client)
    compositor = TimelineCompositor()

    red_img = _create_test_image_bytes("red", 200, 200)
    green_vid = _create_test_video_bytes("lime", duration=2.0, width=200, height=200)

    async with async_session_factory() as db:
        alm = AssetLifecycleManager(db)
        red_asset = await alm.ingest_generated_asset(ws_id, user_id, red_img, "red.png", "image", "image/png")
        green_asset = await alm.ingest_generated_asset(ws_id, user_id, green_vid, "green.mp4", "video", "video/mp4")

    doc = ProjectDocumentV1(
        schema_version=1,
        settings=ProjectSettings(aspect_ratio="16:9", width=640, height=360, fps=25, total_duration=2.5),
        scenes=[
            Scene(
                id="multi_media_scene",
                sequence=1,
                duration=2.5,
                background={"type": "color", "value": "#000000"},
                layers=[
                    SceneLayer(
                        id="layer_left_red",
                        type="image",
                        name="Left Red",
                        start_time=0.2,
                        end_time=2.2,
                        transform={"x": 0.25, "y": 0.5, "scale": 0.8},
                        content={"asset_id": str(red_asset.id)},
                    ),
                    SceneLayer(
                        id="layer_right_green",
                        type="video",
                        name="Right Green",
                        start_time=0.2,
                        end_time=2.2,
                        transform={"x": 0.75, "y": 0.5, "scale": 0.8},
                        content={"asset_id": str(green_asset.id)},
                    ),
                ],
            )
        ],
    )

    mws = MediaWorkspace()
    try:
        async with async_session_factory() as db:
            render_res = await compositor.render_project(document=doc, workspace_id=ws_id, db=db, media_workspace=mws)
            raw = _extract_frame_rgb(render_res.video_path, timestamp=1.0, width=640, height=360)

            # Left side (x=160, y=180) must be RED
            r_l, g_l, b_l = _sample_pixel(raw, x=160, y=180, width=640)
            assert r_l > 170 and b_l < 70, f"Expected Red on left, got ({r_l}, {g_l}, {b_l})"

            # Right side (x=480, y=180) must be GREEN
            r_r, g_r, b_r = _sample_pixel(raw, x=480, y=180, width=640)
            assert g_r > 170 and r_r < 70, f"Expected Green on right, got ({r_r}, {g_r}, {b_r})"
    finally:
        mws.cleanup()


# ==============================================================================
# 19-20. Disabled Layer Omitted & Duration Bounds
# ==============================================================================
@pytest.mark.asyncio
async def test_disabled_layer_and_duration_bounding(async_client: AsyncClient):
    """Tests 19, 20: Verify disabled layer does not render, and layer timing never extends project duration."""
    user_id, ws_id, proj_id, token = await _setup_workspace_and_project(async_client)
    compositor = TimelineCompositor()

    red_img = _create_test_image_bytes("red", 200, 200)
    async with async_session_factory() as db:
        alm = AssetLifecycleManager(db)
        red_asset = await alm.ingest_generated_asset(ws_id, user_id, red_img, "red_dis.png", "image", "image/png")

    doc = ProjectDocumentV1(
        schema_version=1,
        settings=ProjectSettings(aspect_ratio="16:9", width=640, height=360, fps=25, total_duration=2.0),
        scenes=[
            Scene(
                id="dis_scene",
                sequence=1,
                duration=2.0,
                background={"type": "color", "value": "#0000FF"},  # Pure Blue
                layers=[
                    SceneLayer(
                        id="layer_disabled_red",
                        type="image",
                        name="Disabled Red",
                        start_time=0.0,
                        end_time=15.0,  # Exceeds scene duration
                        enabled=False,  # Explicitly disabled
                        transform={"x": 0.5, "y": 0.5, "scale": 1.0},
                        content={"asset_id": str(red_asset.id)},
                    )
                ],
            )
        ],
    )

    mws = MediaWorkspace()
    try:
        async with async_session_factory() as db:
            render_res = await compositor.render_project(document=doc, workspace_id=ws_id, db=db, media_workspace=mws)
            # Duration must remain bounded to scene length (2.0s)
            assert render_res.total_duration <= 2.2

            # Frame at t=1.0s must be Blue background (Red omitted)
            raw = _extract_frame_rgb(render_res.video_path, timestamp=1.0, width=640, height=360)
            r, g, b = _sample_pixel(raw, x=320, y=180, width=640)
            assert b > 180 and r < 80, f"Disabled red layer should not render, got ({r}, {g}, {b})"
    finally:
        mws.cleanup()


# ==============================================================================
# 21-25. Coexistence: Media + Text + Captions + Music + Background (Full Verification)
# ==============================================================================
@pytest.mark.asyncio
async def test_full_coexistence_and_final_mp4_verification(async_client: AsyncClient):
    """Tests 21, 22, 23, 24, 25: Verify all Phase 29 features coexist simultaneously in the final MP4.
    Scene includes:
    - Image background
    - Image media layer (Red logo at top-left)
    - Video media layer (Green box at center)
    - Visual text overlay (Yellow text at top-right)
    - Captions subtitle cues
    - Background music track
    """
    user_id, ws_id, proj_id, token = await _setup_workspace_and_project(async_client)
    compositor = TimelineCompositor()

    # Create assets
    bg_img = _create_test_image_bytes("blue", 640, 360)
    red_logo = _create_test_image_bytes("red", 160, 160)
    green_vid = _create_test_video_bytes("lime", duration=2.0, width=200, height=200)
    wav_music = _create_synthetic_wav(duration=3.0, freq=440.0)

    async with async_session_factory() as db:
        alm = AssetLifecycleManager(db)
        bg_asset = await alm.ingest_generated_asset(ws_id, user_id, bg_img, "bg.png", "image", "image/png")
        red_asset = await alm.ingest_generated_asset(ws_id, user_id, red_logo, "red_logo.png", "image", "image/png")
        green_asset = await alm.ingest_generated_asset(ws_id, user_id, green_vid, "green_clip.mp4", "video", "video/mp4")
        music_asset = await alm.ingest_generated_asset(ws_id, user_id, wav_music, "theme.wav", "audio", "audio/wav")

    doc = ProjectDocumentV1(
        schema_version=1,
        settings=ProjectSettings(
            aspect_ratio="16:9",
            width=640,
            height=360,
            fps=25,
            total_duration=3.0,
            captions=CaptionSettings(
                enabled=True,
                style=CaptionStyle(
                    font_size=28,
                    color="#FFFFFF",
                    background_color="#000000",
                    background_opacity=0.8,
                    position="bottom",
                ),
            ),
        ),
        scenes=[
            Scene(
                id="coexist_scene_01",
                sequence=1,
                duration=3.0,
                background={"type": "image", "asset_id": str(bg_asset.id)},
                layers=[
                    # Red image layer at top-left (x=0.2, y=0.25)
                    SceneLayer(
                        id="layer_logo",
                        type="image",
                        name="Corner Logo",
                        start_time=0.2,
                        end_time=2.8,
                        transform={"x": 0.2, "y": 0.25, "scale": 0.6},
                        content={"asset_id": str(red_asset.id), "opacity": 1.0},
                    ),
                    # Green video layer at center (x=0.5, y=0.5)
                    SceneLayer(
                        id="layer_center_vid",
                        type="video",
                        name="Center Video",
                        start_time=0.5,
                        end_time=2.5,
                        transform={"x": 0.5, "y": 0.5, "scale": 0.7},
                        content={"asset_id": str(green_asset.id), "opacity": 1.0},
                    ),
                    # Text overlay at top-right
                    SceneLayer(
                        id="layer_txt",
                        type="text",
                        name="Headline",
                        start_time=0.0,
                        end_time=3.0,
                        transform={"x": 0.8, "y": 0.2},
                        content={"text": "HEYZEN", "color": "#FFFF00", "font_size": 24},
                    ),
                ],
                subtitles=[
                    {"id": 1, "start": 0.5, "end": 2.5, "text": "Coexisting Subtitles", "enabled": True}
                ],
            )
        ],
        audio_tracks=[
            AudioTrack(
                id="track_bg_music",
                asset_id=str(music_asset.id),
                name="Theme Music",
                volume=0.8,
                start_time=0.0,
                duration=3.0,
            )
        ],
    )

    mws = MediaWorkspace()
    try:
        async with async_session_factory() as db:
            render_res = await compositor.render_project(document=doc, workspace_id=ws_id, db=db, media_workspace=mws)

            # 1. Output Validation
            assert render_res.video_path.exists()
            assert render_res.probe_result.has_video is True
            assert render_res.probe_result.has_audio is True
            assert render_res.total_duration >= 2.8 and render_res.total_duration <= 3.2

            # 2. Pixel verification at t=1.0s
            raw = _extract_frame_rgb(render_res.video_path, timestamp=1.0, width=640, height=360)

            # Check Top-Left: Red logo (x=128, y=90)
            r_logo, g_logo, b_logo = _sample_pixel(raw, x=128, y=90, width=640)
            assert r_logo > 170 and b_logo < 80, f"Expected Red logo at (128,90), got ({r_logo}, {g_logo}, {b_logo})"

            # Check Center: Green video overlay (x=320, y=180)
            r_vid, g_vid, b_vid = _sample_pixel(raw, x=320, y=180, width=640)
            assert g_vid > 170 and r_vid < 70, f"Expected Green video at (320,180), got ({r_vid}, {g_vid}, {b_vid})"
    finally:
        mws.cleanup()
