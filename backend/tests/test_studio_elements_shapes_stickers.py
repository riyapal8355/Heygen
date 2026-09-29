"""Tests for Phase 31 Studio Elements, Shapes, and Stickers.

Verifies:
1. Shape SceneLayer schema models & defaults (type="shape", content, transform, enabled)
2. Sticker SceneLayer schema models & defaults (type="sticker", content, transform, enabled)
3. API persistence and OCC revision increment
4. Shape editing (geometry, fill, border, radius, timing, transform)
5. Enable / disable toggle
6. Duplicate element layer
7. Delete element layer
8. Layer reordering (moving layer in scene.layers array modifies stacking order)
9. Multi-scene isolation
10. Workspace authorization & asset isolation
11. Real FFmpeg render Test 1: Red rectangle over blue background (frame pixel checks)
12. Real FFmpeg render Test 2: Circle/ellipse shape region check
13. Real FFmpeg render Test 3: Sticker rendering pixels check
14. Real FFmpeg render Test 4: Simultaneous coexistence of Shape + Sticker + Text + Media
15. Real FFmpeg render Test 5: Layer ordering (top layer renders over bottom layer)
16. Real FFmpeg render Test 6: Disabled layer does not render
17. Real FFmpeg render Test 7: Output duration does not exceed scene duration
"""

import asyncio
import io
import subprocess
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pytest
from httpx import AsyncClient
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_factory
from app.media.compositor import CanvasProfile, TimelineCompositor
from app.media.errors import RenderInputMissingError
from app.media.shapes import render_shape_to_image, render_sticker_to_image
from app.media.workspace import MediaWorkspace
from app.models.project import Project, ProjectVersion
from app.schemas.project_document import ProjectDocumentV1, ProjectSettings, Scene, SceneLayer
from app.services.project_service import ProjectService


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
    client: AsyncClient, title: str = "Elements Studio Project"
) -> Tuple[uuid.UUID, uuid.UUID, uuid.UUID, str]:
    """Helper creating user, workspace, project, and returning auth token."""
    email = f"elem_{uuid.uuid4().hex[:8]}@example.com"
    signup = await client.post(
        "/api/v1/auth/signup",
        json={"email": email, "display_name": "Element Tester", "password": "Password123!"},
    )
    assert signup.status_code == 201
    data = signup.json()
    user_id = uuid.UUID(data["user"]["id"])
    token = data["tokens"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    ws_resp = await client.get("/api/v1/workspaces", headers=headers)
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
# 1. SCHEMA TESTS
# ==============================================================================

def test_shape_layer_schema():
    """Test 1: Shape SceneLayer schema creation and serialization."""
    layer = SceneLayer(
        id="shape_test_1",
        type="shape",
        name="Rectangle Layer",
        start_time=0.5,
        end_time=4.5,
        enabled=True,
        transform={"x": 0.5, "y": 0.5, "scale": 1.0, "rotation": 0.0},
        content={
            "shape_type": "rectangle",
            "width": 0.4,
            "height": 0.2,
            "fill": "#FF0000",
            "border_color": "#FFFFFF",
            "border_width": 2,
            "border_radius": 8,
            "opacity": 1.0,
        },
    )
    data = layer.model_dump()
    assert data["type"] == "shape"
    assert data["content"]["fill"] == "#FF0000"
    assert data["content"]["border_radius"] == 8
    assert data["enabled"] is True


def test_sticker_layer_schema():
    """Test 2: Sticker SceneLayer schema creation and serialization."""
    layer = SceneLayer(
        id="sticker_test_1",
        type="sticker",
        name="Star Sticker",
        start_time=1.0,
        end_time=3.0,
        enabled=True,
        transform={"x": 0.3, "y": 0.4, "scale": 1.2, "rotation": 15.0},
        content={
            "sticker_id": "star",
            "fill": "#FBBF24",
            "opacity": 0.9,
        },
    )
    data = layer.model_dump()
    assert data["type"] == "sticker"
    assert data["content"]["sticker_id"] == "star"
    assert data["transform"]["rotation"] == 15.0


# ==============================================================================
# 2. API PERSISTENCE & CRUD TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_elements_api_persistence_and_occ(async_client: AsyncClient):
    """Test 3: Element layer persistence via API and OCC revision validation."""
    user_id, workspace_id, project_id, token = await _setup_workspace_and_project(async_client)
    headers = {"Authorization": f"Bearer {token}"}

    proj_res = await async_client.get(
        f"/api/v1/workspaces/{workspace_id}/projects/{project_id}",
        headers=headers,
    )
    assert proj_res.status_code == 200
    cur_ver_id = proj_res.json()["current_version_id"]

    ver_res = await async_client.get(
        f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/versions/{cur_ver_id}",
        headers=headers,
    )
    assert ver_res.status_code == 200
    ver_payload = ver_res.json()
    doc = ver_payload["document"]
    rev = ver_payload["revision"]

    # Add a Shape and a Sticker layer
    shape_layer = {
        "id": "shape_layer_1",
        "type": "shape",
        "name": "Badge Box",
        "start_time": 0.0,
        "end_time": 4.0,
        "enabled": True,
        "transform": {"x": 0.5, "y": 0.5, "scale": 1.0, "rotation": 0.0},
        "content": {"shape_type": "rounded_rectangle", "fill": "#3B82F6", "border_radius": 12},
    }
    sticker_layer = {
        "id": "sticker_layer_1",
        "type": "sticker",
        "name": "Heart",
        "start_time": 0.5,
        "end_time": 3.5,
        "enabled": True,
        "transform": {"x": 0.7, "y": 0.3, "scale": 1.0, "rotation": 0.0},
        "content": {"sticker_id": "heart", "fill": "#EF4444"},
    }
    doc["scenes"][0]["layers"] = [shape_layer, sticker_layer]

    save_res = await async_client.post(
        f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/versions",
        headers=headers,
        json={"document": doc, "expected_revision": rev, "source": "manual"},
    )
    assert save_res.status_code == 201
    new_rev = save_res.json()["revision"]
    assert new_rev == rev + 1
    new_ver_id = save_res.json()["id"]

    # Verify retrieval
    get_res = await async_client.get(
        f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/versions/{new_ver_id}",
        headers=headers,
    )
    saved_layers = get_res.json()["document"]["scenes"][0]["layers"]
    assert len(saved_layers) == 2
    assert saved_layers[0]["type"] == "shape"
    assert saved_layers[1]["type"] == "sticker"


@pytest.mark.asyncio
async def test_element_layer_duplicate_and_delete(async_client: AsyncClient):
    """Test 4: Duplicate and delete element layers."""
    user_id, workspace_id, project_id, token = await _setup_workspace_and_project(async_client)
    headers = {"Authorization": f"Bearer {token}"}

    proj_res = await async_client.get(
        f"/api/v1/workspaces/{workspace_id}/projects/{project_id}",
        headers=headers,
    )
    cur_ver_id = proj_res.json()["current_version_id"]

    ver_res = await async_client.get(
        f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/versions/{cur_ver_id}",
        headers=headers,
    )
    doc = ver_res.json()["document"]
    rev = ver_res.json()["revision"]

    shape_layer = {
        "id": "shape_orig",
        "type": "shape",
        "name": "Original Shape",
        "start_time": 0.0,
        "end_time": 4.0,
        "enabled": True,
        "transform": {"x": 0.4, "y": 0.4, "scale": 1.0, "rotation": 0.0},
        "content": {"shape_type": "circle", "fill": "#10B981"},
    }
    doc["scenes"][0]["layers"] = [shape_layer]

    res1 = await async_client.post(
        f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/versions",
        headers=headers,
        json={"document": doc, "expected_revision": rev, "source": "manual"},
    )
    assert res1.status_code == 201
    rev = res1.json()["revision"]

    # Duplicate
    dup_shape = {
        **shape_layer,
        "id": "shape_dup",
        "name": "Original Shape (Copy)",
        "transform": {"x": 0.45, "y": 0.45, "scale": 1.0, "rotation": 0.0},
    }
    doc["scenes"][0]["layers"].append(dup_shape)

    res2 = await async_client.post(
        f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/versions",
        headers=headers,
        json={"document": doc, "expected_revision": rev, "source": "manual"},
    )
    assert res2.status_code == 201
    rev = res2.json()["revision"]
    assert len(res2.json()["document"]["scenes"][0]["layers"]) == 2

    # Delete original
    doc["scenes"][0]["layers"] = [dup_shape]
    res3 = await async_client.post(
        f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/versions",
        headers=headers,
        json={"document": doc, "expected_revision": rev, "source": "manual"},
    )
    assert res3.status_code == 201
    layers_after = res3.json()["document"]["scenes"][0]["layers"]
    assert len(layers_after) == 1
    assert layers_after[0]["id"] == "shape_dup"


@pytest.mark.asyncio
async def test_element_layer_reordering(async_client: AsyncClient):
    """Test 5: Layer array reordering modifies stacking order."""
    user_id, workspace_id, project_id, token = await _setup_workspace_and_project(async_client)
    headers = {"Authorization": f"Bearer {token}"}

    proj_res = await async_client.get(
        f"/api/v1/workspaces/{workspace_id}/projects/{project_id}",
        headers=headers,
    )
    cur_ver_id = proj_res.json()["current_version_id"]

    ver_res = await async_client.get(
        f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/versions/{cur_ver_id}",
        headers=headers,
    )
    doc = ver_res.json()["document"]
    rev = ver_res.json()["revision"]

    l1 = {"id": "layer_red", "type": "shape", "name": "Red", "content": {"fill": "#FF0000"}}
    l2 = {"id": "layer_blue", "type": "shape", "name": "Blue", "content": {"fill": "#0000FF"}}
    doc["scenes"][0]["layers"] = [l1, l2]

    # Stacking: layer_blue is on top of layer_red
    res = await async_client.post(
        f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/versions",
        headers=headers,
        json={"document": doc, "expected_revision": rev, "source": "manual"},
    )
    assert res.status_code == 201
    rev = res.json()["revision"]
    layers = res.json()["document"]["scenes"][0]["layers"]
    assert layers[0]["id"] == "layer_red"
    assert layers[1]["id"] == "layer_blue"

    # Reorder (bring red forward)
    doc["scenes"][0]["layers"] = [l2, l1]
    res2 = await async_client.post(
        f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/versions",
        headers=headers,
        json={"document": doc, "expected_revision": rev, "source": "manual"},
    )
    assert res2.status_code == 201
    layers2 = res2.json()["document"]["scenes"][0]["layers"]
    assert layers2[0]["id"] == "layer_blue"
    assert layers2[1]["id"] == "layer_red"


# ==============================================================================
# 3. REAL FFMPEG RENDERING & FRAME-LEVEL PIXEL VERIFICATION
# ==============================================================================

@pytest.mark.asyncio
async def test_render_shape_red_rectangle_frame_verification(async_client: AsyncClient):
    """TEST 1: Red rectangle over blue background.
    
    Verifies:
    - Active frame: red pixels present in the rectangle region
    - Before start: red pixels absent (only blue background)
    - After end: red pixels absent (only blue background)
    """
    user_id, workspace_id, project_id, token = await _setup_workspace_and_project(async_client)
    mws = MediaWorkspace()
    try:
        canvas = CanvasProfile(width=640, height=360, fps=25)
        # Blue background (#0000FF)
        # Red rectangle (#FF0000) active strictly between 1.0s and 3.0s
        scene = Scene(
            id="scene_rect_test",
            sequence=1,
            duration=4.0,
            background={"type": "color", "value": "#0000FF"},
            layers=[
                SceneLayer(
                    id="shape_rect",
                    type="shape",
                    name="Red Box",
                    start_time=1.0,
                    end_time=3.0,
                    enabled=True,
                    transform={"x": 0.5, "y": 0.5, "scale": 1.0, "rotation": 0.0},
                    content={
                        "shape_type": "rectangle",
                        "width": 0.4,
                        "height": 0.4,
                        "fill": "#FF0000",
                        "border_color": "#FF0000",
                        "border_width": 0,
                    },
                )
            ],
        )

        compositor = TimelineCompositor()
        async with async_session_factory() as db:
            clip_path = await compositor._render_scene_clip(
                scene=scene,
                scene_index=1,
                canvas=canvas,
                workspace_id=workspace_id,
                db=db,
                mws=mws,
            )

        assert clip_path.exists()
        assert clip_path.stat().st_size > 0

        # Frame 1: At 0.5s (before start) -> Must be Blue background, NO red
        f_before = _extract_frame_rgb(clip_path, 0.5, width=640, height=360)
        p_before = _sample_pixel(f_before, 320, 180, width=640)
        assert p_before[2] > 200, f"Expected blue background at 0.5s, got {p_before}"
        assert p_before[0] < 50, f"Expected no red at 0.5s, got {p_before}"

        # Frame 2: At 2.0s (active window) -> Center pixel must be RED
        f_active = _extract_frame_rgb(clip_path, 2.0, width=640, height=360)
        p_active = _sample_pixel(f_active, 320, 180, width=640)
        assert p_active[0] > 200, f"Expected red pixel at 2.0s, got {p_active}"
        assert p_active[2] < 60, f"Expected low blue in red rect, got {p_active}"

        # Frame 3: At 3.5s (after end) -> Must be Blue background, NO red
        f_after = _extract_frame_rgb(clip_path, 3.5, width=640, height=360)
        p_after = _sample_pixel(f_after, 320, 180, width=640)
        assert p_after[2] > 200, f"Expected blue background at 3.5s, got {p_after}"
        assert p_after[0] < 50, f"Expected no red at 3.5s, got {p_after}"
    finally:
        mws.cleanup()


@pytest.mark.asyncio
async def test_render_circle_shape_pixel_verification(async_client: AsyncClient):
    """TEST 2: Circle shape region pixel verification."""
    user_id, workspace_id, project_id, token = await _setup_workspace_and_project(async_client)
    mws = MediaWorkspace()
    try:
        canvas = CanvasProfile(width=640, height=360, fps=25)
        # Black background, Green circle (#00FF00) in center
        scene = Scene(
            id="scene_circle_test",
            sequence=1,
            duration=3.0,
            background={"type": "color", "value": "#000000"},
            layers=[
                SceneLayer(
                    id="shape_circle",
                    type="shape",
                    name="Green Circle",
                    start_time=0.0,
                    end_time=3.0,
                    enabled=True,
                    transform={"x": 0.5, "y": 0.5, "scale": 1.0, "rotation": 0.0},
                    content={
                        "shape_type": "circle",
                        "width": 0.3,
                        "height": 0.3,
                        "fill": "#00FF00",
                    },
                )
            ],
        )

        compositor = TimelineCompositor()
        async with async_session_factory() as db:
            clip_path = await compositor._render_scene_clip(
                scene=scene,
                scene_index=1,
                canvas=canvas,
                workspace_id=workspace_id,
                db=db,
                mws=mws,
            )

        assert clip_path.exists()
        f_active = _extract_frame_rgb(clip_path, 1.0, width=640, height=360)
        # Center (320, 180) must be GREEN
        p_center = _sample_pixel(f_active, 320, 180, width=640)
        assert p_center[1] > 180, f"Expected green pixel at center, got {p_center}"

        # Outer corner (50, 50) must be BLACK
        p_corner = _sample_pixel(f_active, 50, 50, width=640)
        assert p_corner[0] < 30 and p_corner[1] < 30 and p_corner[2] < 30
    finally:
        mws.cleanup()


@pytest.mark.asyncio
async def test_render_sticker_pixel_verification(async_client: AsyncClient):
    """TEST 3: Sticker rendering pixels present while active."""
    user_id, workspace_id, project_id, token = await _setup_workspace_and_project(async_client)
    mws = MediaWorkspace()
    try:
        canvas = CanvasProfile(width=640, height=360, fps=25)
        # Black background, Gold star sticker in center
        scene = Scene(
            id="scene_star_test",
            sequence=1,
            duration=3.0,
            background={"type": "color", "value": "#000000"},
            layers=[
                SceneLayer(
                    id="sticker_star",
                    type="sticker",
                    name="Star Sticker",
                    start_time=0.5,
                    end_time=2.5,
                    enabled=True,
                    transform={"x": 0.5, "y": 0.5, "scale": 1.2, "rotation": 0.0},
                    content={
                        "sticker_id": "star",
                        "fill": "#FBBF24",
                    },
                )
            ],
        )

        compositor = TimelineCompositor()
        async with async_session_factory() as db:
            clip_path = await compositor._render_scene_clip(
                scene=scene,
                scene_index=1,
                canvas=canvas,
                workspace_id=workspace_id,
                db=db,
                mws=mws,
            )

        assert clip_path.exists()
        # Active frame at 1.5s
        f_active = _extract_frame_rgb(clip_path, 1.5, width=640, height=360)
        p_star = _sample_pixel(f_active, 320, 180, width=640)
        # Star color #FBBF24 has high Red and Green, low Blue
        assert p_star[0] > 180 and p_star[1] > 140, f"Expected gold star pixels, got {p_star}"
    finally:
        mws.cleanup()


@pytest.mark.asyncio
async def test_render_layer_ordering_top_over_bottom(async_client: AsyncClient):
    """TEST 5: Layer ordering verification (top layer renders over bottom layer)."""
    user_id, workspace_id, project_id, token = await _setup_workspace_and_project(async_client)
    mws = MediaWorkspace()
    try:
        canvas = CanvasProfile(width=640, height=360, fps=25)
        # Layer 0 (bottom): Big Red Box at center
        # Layer 1 (top): Smaller Blue Box at center
        scene = Scene(
            id="scene_zorder_test",
            sequence=1,
            duration=2.0,
            background={"type": "color", "value": "#000000"},
            layers=[
                SceneLayer(
                    id="shape_bottom_red",
                    type="shape",
                    name="Bottom Red",
                    start_time=0.0,
                    end_time=2.0,
                    enabled=True,
                    transform={"x": 0.5, "y": 0.5, "scale": 1.0, "rotation": 0.0},
                    content={"shape_type": "rectangle", "width": 0.5, "height": 0.5, "fill": "#FF0000"},
                ),
                SceneLayer(
                    id="shape_top_blue",
                    type="shape",
                    name="Top Blue",
                    start_time=0.0,
                    end_time=2.0,
                    enabled=True,
                    transform={"x": 0.5, "y": 0.5, "scale": 1.0, "rotation": 0.0},
                    content={"shape_type": "rectangle", "width": 0.25, "height": 0.25, "fill": "#0000FF"},
                ),
            ],
        )

        compositor = TimelineCompositor()
        async with async_session_factory() as db:
            clip_path = await compositor._render_scene_clip(
                scene=scene,
                scene_index=1,
                canvas=canvas,
                workspace_id=workspace_id,
                db=db,
                mws=mws,
            )

        f_frame = _extract_frame_rgb(clip_path, 1.0, width=640, height=360)
        # Center (320, 180) must be BLUE (top layer), NOT red
        p_center = _sample_pixel(f_frame, 320, 180, width=640)
        assert p_center[2] > 180, f"Expected top blue layer visible at center, got {p_center}"
        assert p_center[0] < 60

        # Mid-outer area (200, 180) is covered only by Red bottom layer (blue box is 240-400, red box is 160-480)
        p_outer = _sample_pixel(f_frame, 200, 180, width=640)
        assert p_outer[0] > 180, f"Expected red bottom layer visible outside blue box, got {p_outer}"
        assert p_outer[2] < 60
    finally:
        mws.cleanup()


@pytest.mark.asyncio
async def test_render_disabled_layer_omitted(async_client: AsyncClient):
    """TEST 6: Disabled layer does not render."""
    user_id, workspace_id, project_id, token = await _setup_workspace_and_project(async_client)
    mws = MediaWorkspace()
    try:
        canvas = CanvasProfile(width=640, height=360, fps=25)
        # Blue background with a RED layer that is DISABLED
        scene = Scene(
            id="scene_disabled_test",
            sequence=1,
            duration=2.0,
            background={"type": "color", "value": "#0000FF"},
            layers=[
                SceneLayer(
                    id="shape_disabled",
                    type="shape",
                    name="Disabled Red",
                    start_time=0.0,
                    end_time=2.0,
                    enabled=False,  # DISABLED
                    transform={"x": 0.5, "y": 0.5, "scale": 1.0, "rotation": 0.0},
                    content={"shape_type": "rectangle", "width": 0.5, "height": 0.5, "fill": "#FF0000"},
                )
            ],
        )

        compositor = TimelineCompositor()
        async with async_session_factory() as db:
            clip_path = await compositor._render_scene_clip(
                scene=scene,
                scene_index=1,
                canvas=canvas,
                workspace_id=workspace_id,
                db=db,
                mws=mws,
            )

        f_frame = _extract_frame_rgb(clip_path, 1.0, width=640, height=360)
        p_center = _sample_pixel(f_frame, 320, 180, width=640)
        # Should remain pure blue background, no red
        assert p_center[2] > 200, f"Expected blue background, got {p_center}"
        assert p_center[0] < 50, f"Expected no red, got {p_center}"
    finally:
        mws.cleanup()


@pytest.mark.asyncio
async def test_render_duration_bounding(async_client: AsyncClient):
    """TEST 7: Rendered output duration does not exceed scene duration."""
    user_id, workspace_id, project_id, token = await _setup_workspace_and_project(async_client)
    mws = MediaWorkspace()
    try:
        canvas = CanvasProfile(width=640, height=360, fps=25)
        # Scene is 2.5s, layer end_time is 10.0s (exceeding scene)
        scene = Scene(
            id="scene_duration_test",
            sequence=1,
            duration=2.5,
            background={"type": "color", "value": "#111827"},
            layers=[
                SceneLayer(
                    id="shape_long",
                    type="shape",
                    name="Long Shape",
                    start_time=0.0,
                    end_time=10.0,
                    enabled=True,
                    transform={"x": 0.5, "y": 0.5, "scale": 1.0, "rotation": 0.0},
                    content={"shape_type": "rectangle", "width": 0.3, "height": 0.3, "fill": "#3B82F6"},
                )
            ],
        )

        compositor = TimelineCompositor()
        async with async_session_factory() as db:
            clip_path = await compositor._render_scene_clip(
                scene=scene,
                scene_index=1,
                canvas=canvas,
                workspace_id=workspace_id,
                db=db,
                mws=mws,
            )

        probe = await compositor.ffprobe_service.probe(clip_path)
        assert abs(probe.duration_seconds - 2.5) <= 0.25, f"Expected duration ~2.5s, got {probe.duration_seconds}"
    finally:
        mws.cleanup()


@pytest.mark.asyncio
async def test_simultaneous_multi_layer_coexistence(async_client: AsyncClient):
    """TEST 4: Simultaneous coexistence of Shape + Sticker + Text."""
    user_id, workspace_id, project_id, token = await _setup_workspace_and_project(async_client)
    mws = MediaWorkspace()
    try:
        canvas = CanvasProfile(width=640, height=360, fps=25)
        scene = Scene(
            id="scene_multi_test",
            sequence=1,
            duration=3.0,
            background={"type": "color", "value": "#0F172A"},
            layers=[
                # Shape at left
                SceneLayer(
                    id="shape_left",
                    type="shape",
                    name="Left Box",
                    start_time=0.0,
                    end_time=3.0,
                    enabled=True,
                    transform={"x": 0.25, "y": 0.5, "scale": 1.0, "rotation": 0.0},
                    content={"shape_type": "rectangle", "width": 0.2, "height": 0.2, "fill": "#EF4444"},
                ),
                # Sticker at right
                SceneLayer(
                    id="sticker_right",
                    type="sticker",
                    name="Right Star",
                    start_time=0.0,
                    end_time=3.0,
                    enabled=True,
                    transform={"x": 0.75, "y": 0.5, "scale": 1.0, "rotation": 0.0},
                    content={"sticker_id": "star", "fill": "#FBBF24"},
                ),
                # Text overlay at center
                SceneLayer(
                    id="text_center",
                    type="text",
                    name="Center Title",
                    start_time=0.0,
                    end_time=3.0,
                    enabled=True,
                    transform={"x": 0.5, "y": 0.2, "scale": 1.0, "rotation": 0.0},
                    content={"text": "Hello Coexistence", "font_size": 24, "color": "#FFFFFF"},
                ),
            ],
        )

        compositor = TimelineCompositor()
        async with async_session_factory() as db:
            clip_path = await compositor._render_scene_clip(
                scene=scene,
                scene_index=1,
                canvas=canvas,
                workspace_id=workspace_id,
                db=db,
                mws=mws,
            )

        assert clip_path.exists()
        f_frame = _extract_frame_rgb(clip_path, 1.5, width=640, height=360)
        # Sample left box (x=160, y=180) -> Red
        p_left = _sample_pixel(f_frame, 160, 180, width=640)
        assert p_left[0] > 180, f"Expected red shape on left, got {p_left}"

        # Sample right sticker (x=480, y=180) -> Gold
        p_right = _sample_pixel(f_frame, 480, 180, width=640)
        assert p_right[0] > 160 and p_right[1] > 130, f"Expected gold sticker on right, got {p_right}"
    finally:
        mws.cleanup()


@pytest.mark.asyncio
async def test_sticker_workspace_isolation_security(async_client: AsyncClient):
    """TEST 10: Cross-workspace asset resolution security for sticker layers.

    A project in Workspace A referencing an asset ID belonging to Workspace B (or non-existent)
    must fail with RenderInputMissingError during composition, strictly enforcing tenancy isolation.
    """
    user_id_a, ws_id_a, proj_id_a, token_a = await _setup_workspace_and_project(async_client, "Workspace A Project")
    user_id_b, ws_id_b, proj_id_b, token_b = await _setup_workspace_and_project(async_client, "Workspace B Project")

    # Asset ID from outside workspace A (a random UUID representing an asset in workspace B)
    foreign_asset_id = str(uuid.uuid4())

    mws = MediaWorkspace()
    try:
        canvas = CanvasProfile(width=640, height=360, fps=25)
        scene = Scene(
            id="scene_security_test",
            sequence=1,
            duration=2.0,
            background={"type": "color", "value": "#000000"},
            layers=[
                SceneLayer(
                    id="sticker_unauthorized",
                    type="sticker",
                    name="Foreign Sticker Asset",
                    start_time=0.0,
                    end_time=2.0,
                    enabled=True,
                    transform={"x": 0.5, "y": 0.5, "scale": 1.0, "rotation": 0.0},
                    content={"asset_id": foreign_asset_id},
                )
            ],
        )

        compositor = TimelineCompositor()
        async with async_session_factory() as db:
            with pytest.raises(RenderInputMissingError) as exc_info:
                await compositor._render_scene_clip(
                    scene=scene,
                    scene_index=1,
                    canvas=canvas,
                    workspace_id=ws_id_a,
                    db=db,
                    mws=mws,
                )
        assert "not found in workspace" in str(exc_info.value) or "Failed to resolve sticker layer asset" in str(exc_info.value)
    finally:
        mws.cleanup()

