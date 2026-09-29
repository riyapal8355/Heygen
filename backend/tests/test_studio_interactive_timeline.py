"""Tests for Phase 33 Studio Interactive Timeline Manipulation & Clip Trimming.

Verifies:
1. Drag-to-move timing logic (duration preserved, start/end shifted by delta)
2. Negative boundary clamping (start >= 0)
3. Scene end boundary clamping (end <= scene_duration)
4. Left trim behavior (start_time updated, end_time anchored)
5. Right trim behavior (end_time updated, start_time anchored)
6. Minimum duration enforcement (min_duration = 0.2s)
7. Playhead snapping (within 0.1s threshold snaps to playhead)
8. Inspector <-> Timeline synchronization (canonical SceneLayer representation)
9. Inspector -> Timeline update verification
10. Persistence across project reload via OCC create_version
11. Multi-track verification across all 5 tracks:
    - Captions
    - Text
    - Visual Media
    - Elements & Shapes
    - Music
12. Real FFmpeg render parity (visual element active only during trimmed interval)
13. Multi-scene isolation (timing updates isolated to active scene)
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

from app.db.session import async_session_factory
from app.media.compositor import CanvasProfile, TimelineCompositor
from app.media.workspace import MediaWorkspace
from app.models.project import Project, ProjectVersion
from app.schemas.project_document import (
    AudioTrack,
    CaptionSettings,
    ProjectDocumentV1,
    ProjectSettings,
    Scene,
    SceneLayer,
)
from app.services.project_service import ProjectService


MIN_CLIP_DURATION = 0.2
SNAP_THRESHOLD_SECONDS = 0.1


# ---------------------------------------------------------------------------
# Timing math helper functions mirroring src/lib/timelineUtils.ts
# ---------------------------------------------------------------------------

def calculate_move_timing(
    original_start: float,
    original_end: float,
    delta_seconds: float,
    max_duration: float,
    snap_targets: Optional[List[float]] = None,
    snap_threshold: float = SNAP_THRESHOLD_SECONDS,
) -> Tuple[float, float]:
    duration = original_end - original_start
    if duration <= 0:
        duration = MIN_CLIP_DURATION
    
    proposed_start = original_start + delta_seconds
    proposed_end = proposed_start + duration

    # Playhead / Target Snapping
    if snap_targets:
        closest_snap_start = None
        min_start_diff = snap_threshold + 1.0
        for target in snap_targets:
            diff = abs(proposed_start - target)
            if diff <= snap_threshold and diff < min_start_diff:
                min_start_diff = diff
                closest_snap_start = target

        closest_snap_end = None
        min_end_diff = snap_threshold + 1.0
        for target in snap_targets:
            diff = abs(proposed_end - target)
            if diff <= snap_threshold and diff < min_end_diff:
                min_end_diff = diff
                closest_snap_end = target

        if closest_snap_start is not None and closest_snap_end is not None:
            if min_start_diff <= min_end_diff:
                proposed_start = closest_snap_start
                proposed_end = proposed_start + duration
            else:
                proposed_end = closest_snap_end
                proposed_start = proposed_end - duration
        elif closest_snap_start is not None:
            proposed_start = closest_snap_start
            proposed_end = proposed_start + duration
        elif closest_snap_end is not None:
            proposed_end = closest_snap_end
            proposed_start = proposed_end - duration

    # Boundary Clamping
    if proposed_start < 0.0:
        proposed_start = 0.0
        proposed_end = min(max_duration, proposed_start + duration)

    if proposed_end > max_duration:
        proposed_end = max_duration
        proposed_start = max(0.0, proposed_end - duration)

    return round(proposed_start, 4), round(proposed_end, 4)


def calculate_left_trim_timing(
    current_start: float,
    current_end: float,
    delta_seconds: float,
    max_duration: float,
    snap_targets: Optional[List[float]] = None,
    snap_threshold: float = SNAP_THRESHOLD_SECONDS,
) -> Tuple[float, float]:
    proposed_start = current_start + delta_seconds

    if snap_targets:
        closest = None
        min_diff = snap_threshold + 1.0
        for target in snap_targets:
            diff = abs(proposed_start - target)
            if diff <= snap_threshold and diff < min_diff:
                min_diff = diff
                closest = target
        if closest is not None:
            proposed_start = closest

    # Clamping
    clamped_start = max(0.0, min(proposed_start, current_end - MIN_CLIP_DURATION))
    return round(clamped_start, 4), round(current_end, 4)


def calculate_right_trim_timing(
    current_start: float,
    current_end: float,
    delta_seconds: float,
    max_duration: float,
    snap_targets: Optional[List[float]] = None,
    snap_threshold: float = SNAP_THRESHOLD_SECONDS,
) -> Tuple[float, float]:
    proposed_end = current_end + delta_seconds

    if snap_targets:
        closest = None
        min_diff = snap_threshold + 1.0
        for target in snap_targets:
            diff = abs(proposed_end - target)
            if diff <= snap_threshold and diff < min_diff:
                min_diff = diff
                closest = target
        if closest is not None:
            proposed_end = closest

    # Clamping
    clamped_end = min(max_duration, max(proposed_end, current_start + MIN_CLIP_DURATION))
    return round(current_start, 4), round(clamped_end, 4)


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
    client: AsyncClient, title: str = "Interactive Timeline Project"
) -> Tuple[uuid.UUID, uuid.UUID, uuid.UUID, str]:
    email = f"timeline_{uuid.uuid4().hex[:8]}@example.com"
    signup = await client.post(
        "/api/v1/auth/signup",
        json={"email": email, "display_name": "Timeline Tester", "password": "Password123!"},
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
            settings=ProjectSettings(aspect_ratio="16:9", width=640, height=360, fps=25, total_duration=10.0),
            scenes=[
                Scene(
                    id="scene_01",
                    sequence=1,
                    duration=10.0,
                    background={"type": "color", "value": "#000000"},
                    layers=[],
                    subtitles=[],
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
        created_proj = await ps.repo.create_project_with_initial_version(project, version)
        await db.commit()
        return user_id, ws_id, created_proj.id, token


# ---------------------------------------------------------------------------
# Unit Tests for Interaction Timing Math (Tests 1 - 7)
# ---------------------------------------------------------------------------

def test_1_drag_to_move():
    """Test 1: Given start=2, end=5, drag +1.5 => start=3.5, end=6.5, duration=3.0."""
    start, end = calculate_move_timing(
        original_start=2.0,
        original_end=5.0,
        delta_seconds=1.5,
        max_duration=10.0,
    )
    assert start == 3.5
    assert end == 6.5
    assert round(end - start, 4) == 3.0


def test_2_negative_boundary():
    """Test 2: Given start=1, end=4, drag -5 => clamped to start=0, end=3."""
    start, end = calculate_move_timing(
        original_start=1.0,
        original_end=4.0,
        delta_seconds=-5.0,
        max_duration=10.0,
    )
    assert start == 0.0
    assert end == 3.0
    assert round(end - start, 4) == 3.0


def test_3_scene_end_boundary():
    """Test 3: Given scene=10, clip 7->9, drag +5 => clamped to 8->10."""
    start, end = calculate_move_timing(
        original_start=7.0,
        original_end=9.0,
        delta_seconds=5.0,
        max_duration=10.0,
    )
    assert start == 8.0
    assert end == 10.0
    assert round(end - start, 4) == 2.0


def test_4_left_trim():
    """Test 4: Given 2->8, move left edge to 3.5 (delta=+1.5) => 3.5->8.0."""
    start, end = calculate_left_trim_timing(
        current_start=2.0,
        current_end=8.0,
        delta_seconds=1.5,
        max_duration=10.0,
    )
    assert start == 3.5
    assert end == 8.0


def test_5_right_trim():
    """Test 5: Given 2->8, move right edge to 6.5 (delta=-1.5) => 2.0->6.5."""
    start, end = calculate_right_trim_timing(
        current_start=2.0,
        current_end=8.0,
        delta_seconds=-1.5,
        max_duration=10.0,
    )
    assert start == 2.0
    assert end == 6.5


def test_6_minimum_duration():
    """Test 6: Attempt to produce 4->4.1 => clamped to minimum 0.2s duration (4.0->4.2)."""
    # Trimming right edge down to 4.1 from 4.0
    start, end = calculate_right_trim_timing(
        current_start=4.0,
        current_end=6.0,
        delta_seconds=-1.9,  # tries to go to 4.1
        max_duration=10.0,
    )
    assert start == 4.0
    assert end >= 4.2
    assert round(end - start, 2) >= MIN_CLIP_DURATION

    # Trimming left edge up to 4.9 from 5.0 (delta=+0.9 when end is 5.0)
    start_left, end_left = calculate_left_trim_timing(
        current_start=4.0,
        current_end=5.0,
        delta_seconds=0.95,  # tries to go to 4.95 (duration 0.05s)
        max_duration=10.0,
    )
    assert end_left == 5.0
    assert start_left <= 4.8
    assert round(end_left - start_left, 2) >= MIN_CLIP_DURATION


def test_7_playhead_snap():
    """Test 7: playbackTime=5.0, dragged edge=5.08, threshold=0.1 => snaps to 5.0."""
    # Playhead snapping during drag move
    start, end = calculate_move_timing(
        original_start=2.0,
        original_end=5.0,
        delta_seconds=3.08,  # proposed start=5.08, proposed end=8.08
        max_duration=10.0,
        snap_targets=[5.0],
        snap_threshold=SNAP_THRESHOLD_SECONDS,
    )
    # The start edge was at 5.08, within 0.1 of playhead 5.0, so it snapped to 5.0
    assert start == 5.0
    assert end == 8.0

    # Playhead snapping during right trim
    start_r, end_r = calculate_right_trim_timing(
        current_start=2.0,
        current_end=4.0,
        delta_seconds=1.05,  # proposed end=5.05, within 0.1 of 5.0
        max_duration=10.0,
        snap_targets=[5.0],
        snap_threshold=SNAP_THRESHOLD_SECONDS,
    )
    assert start_r == 2.0
    assert end_r == 5.0


# ---------------------------------------------------------------------------
# API & Persistence Integration Tests (Tests 8 - 11)
# ---------------------------------------------------------------------------

async def _get_current_document_and_version(
    client: AsyncClient, ws_id: uuid.UUID, project_id: uuid.UUID, headers: dict
) -> Tuple[dict, int, str]:
    proj_res = await client.get(f"/api/v1/workspaces/{ws_id}/projects/{project_id}", headers=headers)
    assert proj_res.status_code == 200
    cur_ver_id = proj_res.json()["current_version_id"]
    ver_res = await client.get(
        f"/api/v1/workspaces/{ws_id}/projects/{project_id}/versions/{cur_ver_id}", headers=headers
    )
    assert ver_res.status_code == 200
    ver_payload = ver_res.json()
    return ver_payload["document"], ver_payload["revision"], cur_ver_id


@pytest.mark.asyncio
async def test_8_inspector_timeline_sync_and_persistence(async_client: AsyncClient):
    """Test 8 & 10: Verify timeline/inspector timing is persisted and survives reload."""
    client = async_client
    user_id, ws_id, project_id, token = await _setup_workspace_and_project(async_client)
    headers = {"Authorization": f"Bearer {token}"}

    # Initial state: project has scene_01
    doc, rev, _ = await _get_current_document_and_version(client, ws_id, project_id, headers)
    assert len(doc["scenes"]) == 1

    # Add a visual element layer with initial timing 1.0 -> 4.0
    element_layer = {
        "id": "elem_rect_01",
        "type": "shape",
        "name": "Red Box",
        "enabled": True,
        "start_time": 1.0,
        "end_time": 4.0,
        "content": {
            "shape_type": "rectangle",
            "width": 100,
            "height": 100,
            "fill_color": "#FF0000",
            "stroke_color": "#000000",
            "stroke_width": 0,
            "border_radius": 0,
        },
        "transform": {"x": 0.5, "y": 0.5, "scale": 1.0, "rotation": 0.0},
    }
    doc["scenes"][0]["layers"].append(element_layer)

    save_resp = await client.post(
        f"/api/v1/workspaces/{ws_id}/projects/{project_id}/versions",
        headers=headers,
        json={"expected_revision": rev, "document": doc, "source": "studio_manual"},
    )
    assert save_resp.status_code == 201

    # Simulate Drag-to-Move on timeline: shift by +2.0s -> 3.0 -> 6.0
    doc, rev, _ = await _get_current_document_and_version(client, ws_id, project_id, headers)
    moved_start, moved_end = calculate_move_timing(
        original_start=doc["scenes"][0]["layers"][0]["start_time"],
        original_end=doc["scenes"][0]["layers"][0]["end_time"],
        delta_seconds=2.0,
        max_duration=10.0,
    )
    assert moved_start == 3.0
    assert moved_end == 6.0

    doc["scenes"][0]["layers"][0]["start_time"] = moved_start
    doc["scenes"][0]["layers"][0]["end_time"] = moved_end

    save_resp2 = await client.post(
        f"/api/v1/workspaces/{ws_id}/projects/{project_id}/versions",
        headers=headers,
        json={"expected_revision": rev, "document": doc, "source": "studio_manual"},
    )
    assert save_resp2.status_code == 201

    # Reload project and verify exact timing persists (survives reload)
    reloaded_doc, _, _ = await _get_current_document_and_version(client, ws_id, project_id, headers)
    reloaded_layer = reloaded_doc["scenes"][0]["layers"][0]
    assert reloaded_layer["start_time"] == 3.0
    assert reloaded_layer["end_time"] == 6.0


@pytest.mark.asyncio
async def test_9_inspector_to_timeline_sync(async_client: AsyncClient):
    """Test 9: Inspector input update -> persisted scene state -> timeline block update."""
    client = async_client
    user_id, ws_id, project_id, token = await _setup_workspace_and_project(async_client)
    headers = {"Authorization": f"Bearer {token}"}

    doc, rev, _ = await _get_current_document_and_version(client, ws_id, project_id, headers)

    # Add text layer
    text_layer = {
        "id": "text_title_01",
        "type": "text",
        "name": "Title Text",
        "enabled": True,
        "start_time": 0.0,
        "end_time": 5.0,
        "content": {"text": "Hello World", "font_size": 32, "color": "#FFFFFF"},
        "transform": {"x": 0.5, "y": 0.5, "scale": 1.0, "rotation": 0.0},
    }
    doc["scenes"][0]["layers"].append(text_layer)

    # Save via inspector input (user typed 1.5 in Inspector "start_time" field and 4.5 in "end_time")
    doc["scenes"][0]["layers"][0]["start_time"] = 1.5
    doc["scenes"][0]["layers"][0]["end_time"] = 4.5

    save_resp = await client.post(
        f"/api/v1/workspaces/{ws_id}/projects/{project_id}/versions",
        headers=headers,
        json={"expected_revision": rev, "document": doc, "source": "studio_manual"},
    )
    assert save_resp.status_code == 201

    # Verify reload returns updated timing to timeline
    reloaded_doc, _, _ = await _get_current_document_and_version(client, ws_id, project_id, headers)
    assert reloaded_doc["scenes"][0]["layers"][0]["start_time"] == 1.5
    assert reloaded_doc["scenes"][0]["layers"][0]["end_time"] == 4.5


@pytest.mark.asyncio
async def test_11_all_five_tracks(async_client: AsyncClient):
    """Test 11: Timing manipulation across all 5 tracks: Captions, Text, Media, Elements, Music."""
    client = async_client
    user_id, ws_id, project_id, token = await _setup_workspace_and_project(async_client)
    headers = {"Authorization": f"Bearer {token}"}

    doc, rev, _ = await _get_current_document_and_version(client, ws_id, project_id, headers)

    # 1. Caption Cue
    cue = {
        "id": "cue_01",
        "start": 1.0,
        "end": 3.0,
        "text": "Welcome to HeyZen Studio",
        "enabled": True,
    }
    doc["scenes"][0]["subtitles"] = [cue]

    # 2. Text Layer
    text_layer = {
        "id": "text_01",
        "type": "text",
        "name": "Headline",
        "enabled": True,
        "start_time": 0.5,
        "end_time": 4.5,
        "content": {"text": "Headline", "font_size": 28, "color": "#FFFFFF"},
        "transform": {"x": 0.5, "y": 0.2, "scale": 1.0, "rotation": 0.0},
    }

    # 3. Visual Media Layer (Video or Image)
    media_layer = {
        "id": "media_01",
        "type": "image",
        "name": "Hero Image",
        "enabled": True,
        "start_time": 2.0,
        "end_time": 8.0,
        "content": {"asset_id": str(uuid.uuid4()), "url": "https://example.com/hero.jpg"},
        "transform": {"x": 0.5, "y": 0.5, "scale": 1.0, "rotation": 0.0},
    }

    # 4. Elements Layer (Shape/Sticker)
    elem_layer = {
        "id": "elem_01",
        "type": "shape",
        "name": "Badge",
        "enabled": True,
        "start_time": 1.5,
        "end_time": 6.5,
        "content": {"shape_type": "rectangle", "width": 80, "height": 40, "fill_color": "#00FF00"},
        "transform": {"x": 0.8, "y": 0.8, "scale": 1.0, "rotation": 0.0},
    }
    doc["scenes"][0]["layers"] = [text_layer, media_layer, elem_layer]

    # 5. Background Music Track
    music_track = {
        "id": "music_01",
        "asset_id": str(uuid.uuid4()),
        "name": "Upbeat BG Music",
        "volume": 0.4,
        "start_time": 0.0,
        "duration": 9.5,
        "loop": True,
        "muted": False,
    }
    doc["audio_tracks"] = [music_track]

    # Manipulate timings on all 5 tracks using our timing operators:
    # 1. Drag caption cue by +0.5s => 1.5 -> 3.5
    doc["scenes"][0]["subtitles"][0]["start"], doc["scenes"][0]["subtitles"][0]["end"] = calculate_move_timing(
        doc["scenes"][0]["subtitles"][0]["start"], doc["scenes"][0]["subtitles"][0]["end"], 0.5, 10.0
    )

    # 2. Trim left of text layer by +0.5s => 1.0 -> 4.5
    doc["scenes"][0]["layers"][0]["start_time"], doc["scenes"][0]["layers"][0]["end_time"] = calculate_left_trim_timing(
        doc["scenes"][0]["layers"][0]["start_time"], doc["scenes"][0]["layers"][0]["end_time"], 0.5, 10.0
    )

    # 3. Trim right of media layer by -1.5s => 2.0 -> 6.5
    doc["scenes"][0]["layers"][1]["start_time"], doc["scenes"][0]["layers"][1]["end_time"] = calculate_right_trim_timing(
        doc["scenes"][0]["layers"][1]["start_time"], doc["scenes"][0]["layers"][1]["end_time"], -1.5, 10.0
    )

    # 4. Drag element layer by +1.0s => 2.5 -> 7.5
    doc["scenes"][0]["layers"][2]["start_time"], doc["scenes"][0]["layers"][2]["end_time"] = calculate_move_timing(
        doc["scenes"][0]["layers"][2]["start_time"], doc["scenes"][0]["layers"][2]["end_time"], 1.0, 10.0
    )

    # 5. Trim music track right edge (change duration from 9.5 to 7.0)
    doc["audio_tracks"][0]["duration"] = 7.0

    # Save to API
    save_resp = await client.post(
        f"/api/v1/workspaces/{ws_id}/projects/{project_id}/versions",
        headers=headers,
        json={"expected_revision": rev, "document": doc, "source": "studio_manual"},
    )
    assert save_resp.status_code == 201

    # Reload and verify all 5 tracks updated properly
    res_doc, _, _ = await _get_current_document_and_version(client, ws_id, project_id, headers)

    assert res_doc["scenes"][0]["subtitles"][0]["start"] == 1.5
    assert res_doc["scenes"][0]["subtitles"][0]["end"] == 3.5

    assert res_doc["scenes"][0]["layers"][0]["start_time"] == 1.0
    assert res_doc["scenes"][0]["layers"][0]["end_time"] == 4.5

    assert res_doc["scenes"][0]["layers"][1]["start_time"] == 2.0
    assert res_doc["scenes"][0]["layers"][1]["end_time"] == 6.5

    assert res_doc["scenes"][0]["layers"][2]["start_time"] == 2.5
    assert res_doc["scenes"][0]["layers"][2]["end_time"] == 7.5

    assert res_doc["audio_tracks"][0]["start_time"] == 0.0
    assert res_doc["audio_tracks"][0]["duration"] == 7.0


# ---------------------------------------------------------------------------
# FFmpeg Render Parity & Scene Isolation Tests (Tests 12 & 13)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_12_ffmpeg_render_parity(async_client: AsyncClient):
    """Test 12: Real FFmpeg rendering verifying trimmed/moved visual layer interval parity.
    
    A solid green rectangle is placed over a solid black background.
    Layer timing is set to start=1.0s, end=3.0s in a 4.0s scene.
    Frames at t=0.5s: Green rectangle NOT rendered (black pixel)
    Frames at t=2.0s: Green rectangle IS rendered (green pixel)
    Frames at t=3.5s: Green rectangle NOT rendered (black pixel)
    """
    user_id, workspace_id, project_id, token = await _setup_workspace_and_project(async_client)
    mws = MediaWorkspace()
    try:
        canvas = CanvasProfile(width=640, height=360, fps=25)
        scene = Scene(
            id="scene_render_test",
            sequence=1,
            duration=4.0,
            background={"type": "color", "value": "#000000"},
            layers=[
                SceneLayer(
                    id="layer_rect_green",
                    type="shape",
                    name="Green Box",
                    enabled=True,
                    start_time=1.0,
                    end_time=3.0,
                    content={
                        "shape_type": "rectangle",
                        "width": 200,
                        "height": 200,
                        "fill": "#00FF00",
                        "stroke": "#00FF00",
                        "stroke_width": 0,
                        "border_radius": 0,
                    },
                    transform={"x": 0.5, "y": 0.5, "scale": 1.0, "rotation": 0.0},
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

        # Frame 1: at t=0.5s -> Green box should NOT be active
        rgb_0_5 = _extract_frame_rgb(clip_path, 0.5, 640, 360)
        r, g, b = _sample_pixel(rgb_0_5, 320, 180, 640)
        # Background is black (r < 25, g < 25, b < 25)
        assert g < 30, f"Expected black background at t=0.5s, got RGB({r},{g},{b})"

        # Frame 2: at t=2.0s -> Green box SHOULD be active
        rgb_2_0 = _extract_frame_rgb(clip_path, 2.0, 640, 360)
        r, g, b = _sample_pixel(rgb_2_0, 320, 180, 640)
        # Green fill (#00FF00) should be clearly dominant
        assert g > 200 and r < 30 and b < 30, f"Expected green box at t=2.0s, got RGB({r},{g},{b})"

        # Frame 3: at t=3.5s -> Green box should NOT be active
        rgb_3_5 = _extract_frame_rgb(clip_path, 3.5, 640, 360)
        r, g, b = _sample_pixel(rgb_3_5, 320, 180, 640)
        assert g < 30, f"Expected black background at t=3.5s, got RGB({r},{g},{b})"
    finally:
        mws.cleanup()


@pytest.mark.asyncio
async def test_13_scene_isolation(async_client: AsyncClient):
    """Test 13: Multi-scene isolation. Timing changes in Scene 1 do not affect Scene 2."""
    client = async_client
    user_id, ws_id, project_id, token = await _setup_workspace_and_project(async_client)
    headers = {"Authorization": f"Bearer {token}"}

    doc, rev, _ = await _get_current_document_and_version(client, ws_id, project_id, headers)

    # Setup 2 scenes each with a layer
    doc["scenes"] = [
        {
            "id": "scene_A",
            "sequence": 1,
            "duration": 5.0,
            "background": {"type": "color", "value": "#000000"},
            "layers": [
                {
                    "id": "layer_A",
                    "type": "text",
                    "name": "Text A",
                    "enabled": True,
                    "start_time": 0.0,
                    "end_time": 4.0,
                    "content": {"text": "Scene A Text"},
                    "transform": {"x": 0.5, "y": 0.5, "scale": 1.0, "rotation": 0.0},
                }
            ],
            "subtitles": [],
        },
        {
            "id": "scene_B",
            "sequence": 2,
            "duration": 6.0,
            "background": {"type": "color", "value": "#000000"},
            "layers": [
                {
                    "id": "layer_B",
                    "type": "text",
                    "name": "Text B",
                    "enabled": True,
                    "start_time": 1.0,
                    "end_time": 5.0,
                    "content": {"text": "Scene B Text"},
                    "transform": {"x": 0.5, "y": 0.5, "scale": 1.0, "rotation": 0.0},
                }
            ],
            "subtitles": [],
        },
    ]

    # Save base 2-scene document
    save_resp1 = await client.post(
        f"/api/v1/workspaces/{ws_id}/projects/{project_id}/versions",
        headers=headers,
        json={"expected_revision": rev, "document": doc, "source": "studio_manual"},
    )
    assert save_resp1.status_code == 201

    # Now update timing ONLY in Scene A: move layer_A from 0.0->4.0 to 1.0->5.0
    doc, rev, _ = await _get_current_document_and_version(client, ws_id, project_id, headers)
    doc["scenes"][0]["layers"][0]["start_time"] = 1.0
    doc["scenes"][0]["layers"][0]["end_time"] = 5.0

    save_resp = await client.post(
        f"/api/v1/workspaces/{ws_id}/projects/{project_id}/versions",
        headers=headers,
        json={"expected_revision": rev, "document": doc, "source": "studio_manual"},
    )
    assert save_resp.status_code == 201

    # Reload and verify Scene A changed, but Scene B remained untouched
    doc_after, _, _ = await _get_current_document_and_version(client, ws_id, project_id, headers)

    # Scene A updated
    assert doc_after["scenes"][0]["layers"][0]["start_time"] == 1.0
    assert doc_after["scenes"][0]["layers"][0]["end_time"] == 5.0

    # Scene B completely intact
    assert doc_after["scenes"][1]["layers"][0]["start_time"] == 1.0
    assert doc_after["scenes"][1]["layers"][0]["end_time"] == 5.0
    assert doc_after["scenes"][1]["duration"] == 6.0
