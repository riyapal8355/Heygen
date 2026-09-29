"""Tests for Phase 38 Studio Layer Locking & Visibility Unification.

Verifies:
1. Schema & Model:
   - SceneLayer defaults: locked=False, enabled=True
   - Backward compatibility: documents omitting 'locked' deserialize cleanly with locked=False
   - Serialization & round-trip: locked=True, enabled=False, and combinations
2. API Persistence & OCC:
   - Locked and unlocked layers survive ProjectVersion creation (expected_revision)
   - Save & reload: locked and enabled states persist accurately
   - Subsequent OCC save/revision increments retain locked and visibility toggles
3. Compositor Rendering:
   - locked=True + enabled=True renders normally (lock has zero effect on rendering)
   - enabled=False does not render (omitted from output, background remains)
   - locked=True + enabled=False remains hidden
   - Rendering output is identical whether layer is locked or unlocked when enabled=True
"""

import asyncio
import subprocess
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_factory
from app.media.compositor import CanvasProfile, TimelineCompositor
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
    client: AsyncClient, title: str = "Locking & Visibility Studio Project"
) -> Tuple[uuid.UUID, uuid.UUID, uuid.UUID, str]:
    """Helper creating user, workspace, project, and returning auth token."""
    email = f"lockvis_{uuid.uuid4().hex[:8]}@example.com"
    signup = await client.post(
        "/api/v1/auth/signup",
        json={"email": email, "display_name": "LockVis Tester", "password": "Password123!"},
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
            settings=ProjectSettings(aspect_ratio="16:9", width=640, height=360, fps=25, total_duration=3.0),
            scenes=[
                Scene(
                    id="scene_01",
                    sequence=1,
                    duration=3.0,
                    background={"type": "color", "value": "#0000FF"},  # Pure Blue background
                    layers=[
                        SceneLayer(
                            id="layer_rect_red",
                            type="shape",
                            name="Red Box",
                            start_time=0.0,
                            end_time=3.0,
                            enabled=True,
                            locked=False,
                            transform={"x": 0.5, "y": 0.5, "scale": 1.0, "rotation": 0.0},
                            content={
                                "shape_type": "rectangle",
                                "width": 0.5,
                                "height": 0.5,
                                "fill": "#FF0000",
                                "opacity": 1.0,
                            },
                        ),
                        SceneLayer(
                            id="layer_rect_green",
                            type="shape",
                            name="Green Box",
                            start_time=0.0,
                            end_time=3.0,
                            enabled=True,
                            locked=False,
                            transform={"x": 0.5, "y": 0.5, "scale": 0.8, "rotation": 0.0},
                            content={
                                "shape_type": "rectangle",
                                "width": 0.4,
                                "height": 0.4,
                                "fill": "#00FF00",
                                "opacity": 1.0,
                            },
                        ),
                    ],
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
# 1. SCHEMA & BACKWARD COMPATIBILITY
# ==============================================================================

def test_scene_layer_locking_and_visibility_schema():
    """Verify SceneLayer defaults, backward compatibility for missing locked, and roundtrips."""
    # 1. Defaults
    default_layer = SceneLayer(id="def_1", type="text")
    assert default_layer.enabled is True, "Default layer visibility must be True"
    assert default_layer.locked is False, "Default layer lock must be False"

    # 2. Backward compatibility: deserialize legacy document dict without 'locked'
    legacy_data = {
        "id": "legacy_layer",
        "type": "image",
        "name": "Old Document Layer",
        "start_time": 0.0,
        "end_time": 5.0,
        "enabled": True,
        # 'locked' is absent
    }
    deserialized = SceneLayer.model_validate(legacy_data)
    assert deserialized.locked is False, "Missing 'locked' field must deserialize as locked=False"
    assert deserialized.enabled is True

    # 3. Explicit locked=True serialization and round-trip
    locked_layer = SceneLayer(
        id="locked_1",
        type="shape",
        name="Locked Rectangle",
        locked=True,
        enabled=True,
    )
    dumped = locked_layer.model_dump()
    assert dumped["locked"] is True
    assert dumped["enabled"] is True

    roundtrip = SceneLayer.model_validate(dumped)
    assert roundtrip.locked is True
    assert roundtrip.enabled is True

    # 4. Orthogonality: all 4 permutations
    perms = [
        (True, True),
        (True, False),
        (False, True),
        (False, False),
    ]
    for locked_val, enabled_val in perms:
        layer = SceneLayer(id="perm_test", type="text", locked=locked_val, enabled=enabled_val)
        assert layer.locked is locked_val
        assert layer.enabled is enabled_val
        d = layer.model_dump()
        rt = SceneLayer.model_validate(d)
        assert rt.locked is locked_val
        assert rt.enabled is enabled_val


# ==============================================================================
# 2. OCC PERSISTENCE & RELOAD
# ==============================================================================

@pytest.mark.asyncio
async def test_locking_and_visibility_occ_persistence(async_client: AsyncClient):
    """Verify lock and visibility states survive project version creation and reload."""
    user_id, ws_id, proj_id, token = await _setup_workspace_and_project(async_client)
    headers = {"Authorization": f"Bearer {token}"}

    # Fetch initial project (revision 1)
    get_res = await async_client.get(f"/api/v1/workspaces/{ws_id}/projects/{proj_id}", headers=headers)
    assert get_res.status_code == 200
    proj_data = get_res.json()
    assert proj_data["revision"] == 1
    cur_ver_id = proj_data["current_version_id"]

    ver_res = await async_client.get(
        f"/api/v1/workspaces/{ws_id}/projects/{proj_id}/versions/{cur_ver_id}", headers=headers
    )
    assert ver_res.status_code == 200
    doc = ver_res.json()["document"]

    layers = doc["scenes"][0]["layers"]
    assert len(layers) == 2
    assert layers[0]["locked"] is False
    assert layers[0]["enabled"] is True

    # Mutation 1: Lock layer 0, disable layer 1
    layers[0]["locked"] = True
    layers[1]["enabled"] = False

    save_payload = {
        "expected_revision": 1,
        "document": doc,
    }
    ver_create_res = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/projects/{proj_id}/versions",
        json=save_payload,
        headers=headers,
    )
    assert ver_create_res.status_code == 201
    assert ver_create_res.json()["revision"] == 2
    new_ver_id = ver_create_res.json()["id"]

    # Reload project document via version and verify persistence
    reload_ver_res = await async_client.get(
        f"/api/v1/workspaces/{ws_id}/projects/{proj_id}/versions/{new_ver_id}", headers=headers
    )
    assert reload_ver_res.status_code == 200
    reloaded_doc = reload_ver_res.json()["document"]
    reloaded_layers = reloaded_doc["scenes"][0]["layers"]

    assert reloaded_layers[0]["locked"] is True, "Layer 0 locked state must persist as True"
    assert reloaded_layers[0]["enabled"] is True, "Layer 0 visibility must persist as True"
    assert reloaded_layers[1]["locked"] is False, "Layer 1 locked state must persist as False"
    assert reloaded_layers[1]["enabled"] is False, "Layer 1 visibility must persist as False"

    # Mutation 2: Unlock layer 0, re-enable layer 1
    reloaded_layers[0]["locked"] = False
    reloaded_layers[1]["enabled"] = True

    save_payload2 = {
        "expected_revision": 2,
        "document": reloaded_doc,
    }
    ver_create_res2 = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/projects/{proj_id}/versions",
        json=save_payload2,
        headers=headers,
    )
    assert ver_create_res2.status_code == 201
    assert ver_create_res2.json()["revision"] == 3
    final_ver_id = ver_create_res2.json()["id"]

    # Reload again and verify updated states
    reload_ver_res2 = await async_client.get(
        f"/api/v1/workspaces/{ws_id}/projects/{proj_id}/versions/{final_ver_id}", headers=headers
    )
    assert reload_ver_res2.status_code == 200
    final_doc = reload_ver_res2.json()["document"]
    final_layers = final_doc["scenes"][0]["layers"]

    assert final_layers[0]["locked"] is False
    assert final_layers[0]["enabled"] is True
    assert final_layers[1]["locked"] is False
    assert final_layers[1]["enabled"] is True


# ==============================================================================
# 3. COMPOSITOR RENDERING (LOCKED RENDERS NORMALLY, DISABLED OMITTED)
# ==============================================================================

@pytest.mark.asyncio
async def test_rendering_respects_visibility_and_ignores_lock(async_client: AsyncClient):
    """Verify compositor renders locked=True identically to locked=False, and omits enabled=False."""
    user_id, ws_id, proj_id, token = await _setup_workspace_and_project(async_client)
    compositor = TimelineCompositor()
    mws = MediaWorkspace()

    # Document where:
    # - Background: Pure Blue (#0000FF)
    # - Layer 1 (Red rectangle): locked=True, enabled=True -> must render red
    # - Layer 2 (Green rectangle): locked=False, enabled=False -> must NOT render (omitted)
    doc = ProjectDocumentV1(
        schema_version=1,
        settings=ProjectSettings(aspect_ratio="16:9", width=640, height=360, fps=25, total_duration=2.0),
        scenes=[
            Scene(
                id="render_scene_1",
                sequence=1,
                duration=2.0,
                background={"type": "color", "value": "#0000FF"},  # Pure Blue
                layers=[
                    SceneLayer(
                        id="layer_red_locked_visible",
                        type="shape",
                        name="Locked Red Box",
                        start_time=0.0,
                        end_time=2.0,
                        enabled=True,
                        locked=True,  # LOCKED + ENABLED
                        transform={"x": 0.5, "y": 0.5, "scale": 1.0, "rotation": 0.0},
                        content={
                            "shape_type": "rectangle",
                            "width": 0.5,
                            "height": 0.5,
                            "fill": "#FF0000",
                            "opacity": 1.0,
                        },
                    ),
                    SceneLayer(
                        id="layer_green_unlocked_hidden",
                        type="shape",
                        name="Unlocked Hidden Green Box",
                        start_time=0.0,
                        end_time=2.0,
                        enabled=False,  # UNLOCKED + DISABLED
                        locked=False,
                        transform={"x": 0.5, "y": 0.5, "scale": 0.3, "rotation": 0.0},
                        content={
                            "shape_type": "rectangle",
                            "width": 0.3,
                            "height": 0.3,
                            "fill": "#00FF00",
                            "opacity": 1.0,
                        },
                    ),
                ],
            )
        ],
    )

    async with async_session_factory() as db:
        render_res = await compositor.render_project(
            document=doc,
            workspace_id=ws_id,
            db=db,
            media_workspace=mws,
        )
        assert render_res.total_duration <= 2.2

        # Extract frame at t=1.0s
        raw = _extract_frame_rgb(render_res.video_path, timestamp=1.0, width=640, height=360)

        # Center (320, 180) must be RED (Layer 1 rendered despite locked=True, and Layer 2 green was omitted)
        r, g, b = _sample_pixel(raw, x=320, y=180, width=640)
        assert r > 180 and b < 80, f"Locked enabled red layer must render normally, got ({r}, {g}, {b})"
        assert g < 80, f"Disabled green layer must not be present, got ({r}, {g}, {b})"

        # Corner (20, 20) must be BLUE background
        corner_r, corner_g, corner_b = _sample_pixel(raw, x=20, y=20, width=640)
        assert corner_b > 180 and corner_r < 80, f"Background must be blue, got ({corner_r}, {corner_g}, {corner_b})"


@pytest.mark.asyncio
async def test_rendering_locked_disabled_remains_hidden(async_client: AsyncClient):
    """Verify locked=True + enabled=False remains completely hidden in render output."""
    user_id, ws_id, proj_id, token = await _setup_workspace_and_project(async_client)
    compositor = TimelineCompositor()
    mws = MediaWorkspace()

    # Document where red rectangle is locked=True AND enabled=False
    doc = ProjectDocumentV1(
        schema_version=1,
        settings=ProjectSettings(aspect_ratio="16:9", width=640, height=360, fps=25, total_duration=2.0),
        scenes=[
            Scene(
                id="render_scene_2",
                sequence=1,
                duration=2.0,
                background={"type": "color", "value": "#0000FF"},  # Pure Blue
                layers=[
                    SceneLayer(
                        id="layer_red_locked_disabled",
                        type="shape",
                        name="Locked Disabled Red Box",
                        start_time=0.0,
                        end_time=2.0,
                        enabled=False,  # DISABLED
                        locked=True,   # LOCKED
                        transform={"x": 0.5, "y": 0.5, "scale": 1.0, "rotation": 0.0},
                        content={
                            "shape_type": "rectangle",
                            "width": 0.6,
                            "height": 0.6,
                            "fill": "#FF0000",
                            "opacity": 1.0,
                        },
                    ),
                ],
            )
        ],
    )

    async with async_session_factory() as db:
        render_res = await compositor.render_project(
            document=doc,
            workspace_id=ws_id,
            db=db,
            media_workspace=mws,
        )
        assert render_res.total_duration <= 2.2

        # Extract frame at t=1.0s
        raw = _extract_frame_rgb(render_res.video_path, timestamp=1.0, width=640, height=360)

        # Center (320, 180) must remain BLUE background because red is disabled
        r, g, b = _sample_pixel(raw, x=320, y=180, width=640)
        assert b > 180 and r < 80, f"Disabled locked red layer must not render, got ({r}, {g}, {b})"
