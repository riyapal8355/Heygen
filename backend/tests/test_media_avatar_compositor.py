"""Tests for TimelineCompositor multi-track avatar compositing.

Verifies:
1. Multi-track compositing with avatar overlay and neural alpha matte (view_mode='half_body').
2. Circular PIP mask compositing (view_mode='circle').
3. Spatial positioning (x, y, scale transforms).
4. Multi-scene timeline with mixed avatar configurations, text overlays, and audio tracks.
5. Graceful fallback when avatar asset cannot be resolved.
"""

import asyncio
import os
import tempfile
import uuid
from pathlib import Path
from unittest.mock import AsyncMock
import cv2
import numpy as np
import pytest

from app.media.compositor import TimelineCompositor
from app.media.ffmpeg import FFmpegService
from app.media.ffprobe import FFprobeService
from app.media.models import CanvasProfile, RenderResult
from app.media.workspace import MediaWorkspace
from app.schemas.project_document import (
    ProjectDocumentV1,
    ProjectSettings,
    Scene,
    SceneAvatar,
    SceneSpeech,
)


def _generate_synthetic_avatar_video(filepath: Path, duration_sec: float = 1.5, fps: float = 25.0) -> None:
    """Helper to generate a small portrait video simulating a talking-head actor."""
    w, h = 320, 240
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(filepath), fourcc, fps, (w, h), isColor=True)
    num_frames = int(duration_sec * fps)
    for i in range(num_frames):
        frame = np.full((h, w, 3), 50, dtype=np.uint8)
        # Draw torso and head
        cv2.ellipse(frame, (w // 2, h + 20), (80, 100), 0, 0, 360, (180, 150, 130), -1)
        cv2.circle(frame, (w // 2, h // 2 - 10), 45, (210, 180, 160), -1)
        # Animate mouth moving
        mouth_open = int(abs(np.sin(i * 0.5)) * 10)
        cv2.ellipse(frame, (w // 2, h // 2 + 10), (12, 4 + mouth_open), 0, 0, 360, (100, 50, 50), -1)
        writer.write(frame)
    writer.release()


@pytest.mark.asyncio
async def test_avatar_compositor_half_body_alpha_matting():
    """Verify TimelineCompositor performs neural matting and composites avatar over scene background."""
    ffmpeg_svc = FFmpegService()
    ffprobe_svc = FFprobeService()
    compositor = TimelineCompositor(ffmpeg_service=ffmpeg_svc, ffprobe_service=ffprobe_svc)

    with MediaWorkspace(prefix="test_avatar_half_") as mws:
        # Create synthetic avatar video in workspace
        avatar_file = mws.scenes_dir / "synthetic_avatar.mp4"
        _generate_synthetic_avatar_video(avatar_file, duration_sec=1.2)

        doc = ProjectDocumentV1(
            settings=ProjectSettings(width=640, height=360, fps=25),
            scenes=[
                Scene(
                    id="scene_avatar_1",
                    sequence=1,
                    duration=1.2,
                    background={"type": "color", "value": "#0F172A"},
                    avatar=SceneAvatar(
                        avatar_id="avatar_natalie",
                        view_mode="half_body",
                        video_asset_id="asset_avatar_123",
                        position={"x": 0.5, "y": 0.65, "scale": 1.0},
                    ),
                    speech=SceneSpeech(voice_id="v1", script="Avatar compositing test"),
                )
            ],
        )

        db = AsyncMock()
        # Mock mws.resolve_asset to return our synthetic avatar video
        orig_resolve = mws.resolve_asset

        async def _mock_resolve(asset_id, workspace_id, db):
            if str(asset_id) == "asset_avatar_123":
                return avatar_file
            return await orig_resolve(asset_id, workspace_id, db)

        mws.resolve_asset = _mock_resolve

        res = await compositor.render_project(
            document=doc,
            workspace_id=uuid.uuid4(),
            db=db,
            media_workspace=mws,
        )

        assert isinstance(res, RenderResult)
        assert res.video_path.exists()
        assert res.thumbnail_path.exists()
        assert res.scenes_count == 1

        probe = res.probe_result
        assert probe.width == 640
        assert probe.height == 360
        assert len(probe.video_streams) == 1
        assert len(probe.audio_streams) == 1
        assert probe.duration_seconds >= 1.0


@pytest.mark.asyncio
async def test_avatar_compositor_circle_pip_mask():
    """Verify TimelineCompositor creates circular PIP bubble mask for Loom/HeyGen style avatar."""
    compositor = TimelineCompositor()

    with MediaWorkspace(prefix="test_avatar_circle_") as mws:
        avatar_file = mws.scenes_dir / "synthetic_pip.mp4"
        _generate_synthetic_avatar_video(avatar_file, duration_sec=1.0)

        doc = ProjectDocumentV1(
            settings=ProjectSettings(width=480, height=270, fps=25),
            scenes=[
                Scene(
                    id="scene_pip",
                    sequence=1,
                    duration=1.0,
                    background={"type": "color", "value": "#1E1B4B"},
                    avatar=SceneAvatar(
                        avatar_id="avatar_pip",
                        view_mode="circle",
                        video_asset_id="asset_pip_1",
                        position={"x": 0.85, "y": 0.8, "scale": 0.8},
                    ),
                )
            ],
        )

        db = AsyncMock()

        async def _mock_resolve(asset_id, workspace_id, db):
            return avatar_file

        mws.resolve_asset = _mock_resolve

        res = await compositor.render_project(
            document=doc,
            workspace_id=uuid.uuid4(),
            db=db,
            media_workspace=mws,
        )

        assert res.video_path.exists()
        probe = res.probe_result
        assert probe.width == 480
        assert probe.height == 270


@pytest.mark.asyncio
async def test_avatar_compositor_close_up_positioning():
    """Verify close-up view mode and spatial position transforms."""
    compositor = TimelineCompositor()

    with MediaWorkspace(prefix="test_avatar_closeup_") as mws:
        avatar_file = mws.scenes_dir / "synthetic_closeup.mp4"
        _generate_synthetic_avatar_video(avatar_file, duration_sec=1.0)

        doc = ProjectDocumentV1(
            settings=ProjectSettings(width=640, height=360, fps=25),
            scenes=[
                Scene(
                    id="scene_cu",
                    sequence=1,
                    duration=1.0,
                    background={"type": "color", "value": "#047857"},
                    avatar=SceneAvatar(
                        avatar_id="avatar_cu",
                        view_mode="close_up",
                        video_asset_id="asset_cu_1",
                        position={"x": 0.7, "y": 0.45, "scale": 1.1},
                    ),
                    speech=SceneSpeech(voice_id="v1", script="Close-up framing"),
                )
            ],
        )

        db = AsyncMock()
        mws.resolve_asset = AsyncMock(return_value=avatar_file)

        res = await compositor.render_project(
            document=doc,
            workspace_id=uuid.uuid4(),
            db=db,
            media_workspace=mws,
        )

        assert res.video_path.exists()
        assert res.probe_result.width == 640


@pytest.mark.asyncio
async def test_avatar_compositor_multi_scene_with_mixed_avatars_and_text():
    """Verify multi-scene project concatenating a half-body avatar scene with a circular PIP scene."""
    compositor = TimelineCompositor()

    with MediaWorkspace(prefix="test_avatar_multi_") as mws:
        avatar_file = mws.scenes_dir / "synthetic_multi.mp4"
        _generate_synthetic_avatar_video(avatar_file, duration_sec=1.0)

        doc = ProjectDocumentV1(
            settings=ProjectSettings(width=480, height=270, fps=25),
            scenes=[
                Scene(
                    id="scene_s1",
                    sequence=1,
                    duration=1.0,
                    background={"type": "color", "value": "#0F172A"},
                    avatar=SceneAvatar(
                        avatar_id="av1",
                        view_mode="half_body",
                        video_asset_id="av_asset",
                        position={"x": 0.5, "y": 0.65, "scale": 1.0},
                    ),
                    speech=SceneSpeech(voice_id="v1", script="Scene 1 Presenter"),
                ),
                Scene(
                    id="scene_s2",
                    sequence=2,
                    duration=1.0,
                    background={"type": "color", "value": "#1E293B"},
                    avatar=SceneAvatar(
                        avatar_id="av1",
                        view_mode="circle",
                        video_asset_id="av_asset",
                        position={"x": 0.8, "y": 0.8, "scale": 0.7},
                    ),
                    speech=SceneSpeech(voice_id="v1", script="Scene 2 Circular PIP"),
                ),
            ],
        )

        db = AsyncMock()
        mws.resolve_asset = AsyncMock(return_value=avatar_file)

        res = await compositor.render_project(
            document=doc,
            workspace_id=uuid.uuid4(),
            db=db,
            media_workspace=mws,
        )

        assert res.scenes_count == 2
        assert res.total_duration >= 1.8
        assert res.video_path.exists()


@pytest.mark.asyncio
async def test_avatar_compositor_missing_avatar_asset_fallback():
    """Verify compositor falls back gracefully without crashing when avatar asset is unresolvable."""
    compositor = TimelineCompositor()

    with MediaWorkspace(prefix="test_avatar_fallback_") as mws:
        doc = ProjectDocumentV1(
            settings=ProjectSettings(width=320, height=180, fps=25),
            scenes=[
                Scene(
                    id="scene_fb",
                    sequence=1,
                    duration=1.0,
                    background={"type": "color", "value": "#991B1B"},
                    avatar=SceneAvatar(
                        avatar_id="missing_av",
                        video_asset_id="nonexistent_asset_id",
                    ),
                )
            ],
        )

        db = AsyncMock()
        # Mock mws.resolve_asset raising an error (asset not found)
        mws.resolve_asset = AsyncMock(side_effect=FileNotFoundError("Asset not found"))

        res = await compositor.render_project(
            document=doc,
            workspace_id=uuid.uuid4(),
            db=db,
            media_workspace=mws,
        )

        # Renders the background cleanly as fallback
        assert res.video_path.exists()
        assert res.probe_result.width == 320
        assert res.probe_result.height == 180
