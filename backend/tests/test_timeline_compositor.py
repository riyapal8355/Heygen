"""Integration tests for TimelineCompositor real multi-scene rendering."""

import asyncio
import uuid
from pathlib import Path
import pytest
from unittest.mock import AsyncMock

from app.media.compositor import TimelineCompositor
from app.media.ffmpeg import FFmpegService
from app.media.ffprobe import FFprobeService
from app.media.models import CanvasProfile, RenderResult
from app.media.workspace import MediaWorkspace
from app.schemas.project_document import (
    ProjectDocumentV1,
    ProjectSettings,
    Scene,
    SceneSpeech,
)


@pytest.mark.asyncio
async def test_timeline_compositor_multi_scene_render():
    """Verify TimelineCompositor renders multiple scenes into a valid MP4 with real FFmpeg and FFprobe."""
    ffmpeg_svc = FFmpegService()
    ffprobe_svc = FFprobeService()
    assert ffmpeg_svc.is_available(), "FFmpeg must be installed for real media rendering"

    compositor = TimelineCompositor(ffmpeg_service=ffmpeg_svc, ffprobe_service=ffprobe_svc)

    doc = ProjectDocumentV1(
        settings=ProjectSettings(
            aspect_ratio="16:9",
            width=640,
            height=360,
            fps=30,
        ),
        scenes=[
            Scene(
                id="scene_1",
                sequence=1,
                duration=1.5,
                background={"type": "color", "value": "#0F172A"},
                speech=SceneSpeech(voice_id="v1", script="HeyZen Phase 7 Scene 1"),
            ),
            Scene(
                id="scene_2",
                sequence=2,
                duration=1.5,
                background={"type": "color", "value": "#1E293B"},
                speech=SceneSpeech(voice_id="v1", script="Scene 2 Text Overlay"),
            ),
        ],
    )

    db = AsyncMock()
    ws_id = uuid.uuid4()

    progress_records = []

    async def _on_progress(pct: int, stage: str, details=None):
        progress_records.append((pct, stage))

    with MediaWorkspace(prefix="test_comp_") as mws:
        result = await compositor.render_project(
            document=doc,
            workspace_id=ws_id,
            db=db,
            media_workspace=mws,
            progress_callback=_on_progress,
        )

        assert isinstance(result, RenderResult)
        assert result.video_path.exists()
        assert result.thumbnail_path.exists()
        assert result.total_duration >= 2.8
        assert result.scenes_count == 2
        assert result.canvas_profile.width == 640
        assert result.canvas_profile.height == 360

        # Validate with real ffprobe
        probe = result.probe_result
        assert len(probe.video_streams) == 1
        assert len(probe.audio_streams) == 1
        assert probe.width == 640
        assert probe.height == 360
        assert probe.codec_name in ("h264", "aac")

        # Check progress events were captured
        stages = [s for _, s in progress_records]
        assert "preparing_assets" in stages
        assert "rendering_scenes" in stages
        assert "assembling" in stages
        assert "validating_output" in stages


@pytest.mark.asyncio
async def test_timeline_compositor_vertical_shorts_aspect_ratio():
    """Verify rendering with 9:16 vertical shorts aspect ratio."""
    compositor = TimelineCompositor()
    doc = ProjectDocumentV1(
        settings=ProjectSettings(
            aspect_ratio="9:16",
            width=360,
            height=640,
            fps=30,
        ),
        scenes=[
            Scene(
                id="vert_scene",
                sequence=1,
                duration=1.0,
                background={"type": "color", "value": "#312E81"},
            ),
        ],
    )

    db = AsyncMock()
    with MediaWorkspace(prefix="test_vert_") as mws:
        res = await compositor.render_project(
            document=doc,
            workspace_id=uuid.uuid4(),
            db=db,
            media_workspace=mws,
        )
        assert res.canvas_profile.aspect_ratio == "9:16"
        assert res.probe_result.width == 360
        assert res.probe_result.height == 640


@pytest.mark.asyncio
async def test_timeline_compositor_cancellation_aborts_early():
    """Verify cooperative cancellation checker aborts rendering early and cleans up."""
    compositor = TimelineCompositor()
    doc = ProjectDocumentV1(
        settings=ProjectSettings(width=320, height=180, fps=24),
        scenes=[
            Scene(id="s1", sequence=1, duration=1.0),
            Scene(id="s2", sequence=2, duration=1.0),
        ],
    )

    async def _cancel_immediately():
        return True

    db = AsyncMock()
    with pytest.raises(asyncio.CancelledError):
        await compositor.render_project(
            document=doc,
            workspace_id=uuid.uuid4(),
            db=db,
            cancellation_checker=_cancel_immediately,
        )
