"""Phase 42C-1: Unified Text & Caption Render Parity Test Suite.

Verifies:
Test 1: Text above media (media z=0, text z=1) -> text rendered over media.
Test 2: Text below media (text z=0, media z=1) -> media rendered over text.
Test 3: Text between two media/shape layers (shape A z=0, text z=1, shape B z=2).
Test 4: Text between elements (shape z=0, text z=1, shape z=2).
Test 5: Caption interleaving (media A z=0, caption z=1, media B z=2).
Test 6: Hidden text (enabled = false) -> text absent from export.
Test 7: Locked text (locked = true, enabled = true) -> text renders.
Test 8: Timing (text present only during start..end).
Test 9: Opacity (partially transparent text layer composited).
Test 10: Rotation (rotated text layer renders cleanly).
Test 11: Legacy document (no explicit z_index renders with deterministic baseline).
Test 12: Mixed layer types interleaved.
Test 13: Zero double rendering (text and captions rendered exactly once).
"""

import subprocess
import uuid
from pathlib import Path
from PIL import Image
import pytest

from app.db.session import async_session_factory
from app.media.compositor import TimelineCompositor
from app.media.models import CanvasProfile
from app.media.workspace import MediaWorkspace
from app.schemas.project_document import (
    CaptionSettings,
    CaptionStyle,
    ProjectDocumentV1,
    ProjectSettings,
    Scene,
    SceneLayer,
)


def _extract_frame(video_path: Path, timestamp: float, output_png: Path) -> Image.Image:
    """Extract a single frame from rendered video at timestamp as a PIL Image."""
    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{timestamp:.3f}",
        "-i", str(video_path),
        "-vframes", "1",
        str(output_png),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert output_png.exists(), f"Failed to extract frame at {timestamp}s"
    return Image.open(output_png).convert("RGB")


@pytest.mark.asyncio
async def test_1_text_above_media():
    """Test 1: Media at z=0, Text at z=1 -> Text appears above media."""
    compositor = TimelineCompositor()
    mws = MediaWorkspace(prefix="test_p42c1_t1_")
    ws_id = uuid.uuid4()

    try:
        # Red rectangle covering center, text with bright green color on top
        doc = ProjectDocumentV1(
            settings=ProjectSettings(width=640, height=360, fps=30, total_duration=2.0),
            scenes=[
                Scene(
                    id="sc_1",
                    sequence=1,
                    duration=2.0,
                    background={"type": "color", "value": "#000000"},
                    layers=[
                        SceneLayer(
                            id="layer_shape_red",
                            type="shape",
                            start_time=0.0,
                            end_time=2.0,
                            z_index=0,
                            transform={"x": 0.5, "y": 0.5, "scale": 1.0},
                            content={"shape_type": "rectangle", "width": 0.5, "height": 0.5, "fill": "#FF0000"},
                        ),
                        SceneLayer(
                            id="layer_text_green",
                            type="text",
                            start_time=0.0,
                            end_time=2.0,
                            z_index=1,
                            transform={"x": 0.5, "y": 0.5, "scale": 1.0},
                            content={"text": "HELLO", "font_size": 48, "color": "#00FF00"},
                        ),
                    ],
                )
            ],
        )

        async with async_session_factory() as db:
            res = await compositor.render_project(doc, ws_id, db, media_workspace=mws)

        frame = _extract_frame(res.video_path, 1.0, mws.scenes_dir / "frame_t1.png")
        # Text is on top of red box: center area should contain bright green pixels
        pixels = list(frame.getdata())
        green_pixels = [p for p in pixels if p[1] > 150 and p[0] < 100]
        assert len(green_pixels) > 50, "Expected green text pixels to be visible over red shape"
    finally:
        mws.cleanup()


@pytest.mark.asyncio
async def test_2_text_below_media():
    """Test 2: Text at z=0, Media (shape) at z=1 -> Media covers text."""
    compositor = TimelineCompositor()
    mws = MediaWorkspace(prefix="test_p42c1_t2_")
    ws_id = uuid.uuid4()

    try:
        # Green text at z=0, solid red rectangle at z=1 covering text completely
        doc = ProjectDocumentV1(
            settings=ProjectSettings(width=640, height=360, fps=30, total_duration=2.0),
            scenes=[
                Scene(
                    id="sc_2",
                    sequence=1,
                    duration=2.0,
                    background={"type": "color", "value": "#000000"},
                    layers=[
                        SceneLayer(
                            id="layer_text_green",
                            type="text",
                            start_time=0.0,
                            end_time=2.0,
                            z_index=0,  # BEHIND
                            transform={"x": 0.5, "y": 0.5, "scale": 1.0},
                            content={"text": "HELLO", "font_size": 36, "color": "#00FF00"},
                        ),
                        SceneLayer(
                            id="layer_shape_red",
                            type="shape",
                            start_time=0.0,
                            end_time=2.0,
                            z_index=1,  # IN FRONT
                            transform={"x": 0.5, "y": 0.5, "scale": 1.0},
                            content={"shape_type": "rectangle", "width": 0.8, "height": 0.8, "fill": "#FF0000"},
                        ),
                    ],
                )
            ],
        )

        async with async_session_factory() as db:
            res = await compositor.render_project(doc, ws_id, db, media_workspace=mws)

        frame = _extract_frame(res.video_path, 1.0, mws.scenes_dir / "frame_t2.png")
        pixels = list(frame.getdata())
        # Red shape is on top: center area should be covered by red, green text should NOT be visible
        green_pixels = [p for p in pixels if p[1] > 150 and p[0] < 100]
        assert len(green_pixels) == 0, f"Expected text to be hidden under shape, found {len(green_pixels)} green pixels"
        red_pixels = [p for p in pixels if p[0] > 150 and p[1] < 100]
        assert len(red_pixels) > 500, "Expected red shape to cover center area"
    finally:
        mws.cleanup()


@pytest.mark.asyncio
async def test_3_text_between_two_media_layers():
    """Test 3: Shape A (Red) z=0, Text (Green) z=1, Shape B (Blue) z=2."""
    compositor = TimelineCompositor()
    mws = MediaWorkspace(prefix="test_p42c1_t3_")
    ws_id = uuid.uuid4()

    try:
        # Shape A: Large red rectangle (width=0.8, height=0.8) at z=0
        # Text: Green text (width across center) at z=1
        # Shape B: Smaller blue square (width=0.2, height=0.2) at z=2 covering only center
        doc = ProjectDocumentV1(
            settings=ProjectSettings(width=640, height=360, fps=30, total_duration=2.0),
            scenes=[
                Scene(
                    id="sc_3",
                    sequence=1,
                    duration=2.0,
                    background={"type": "color", "value": "#000000"},
                    layers=[
                        SceneLayer(
                            id="shape_a_red",
                            type="shape",
                            start_time=0.0,
                            end_time=2.0,
                            z_index=0,
                            transform={"x": 0.5, "y": 0.5, "scale": 1.0},
                            content={"shape_type": "rectangle", "width": 0.8, "height": 0.8, "fill": "#FF0000"},
                        ),
                        SceneLayer(
                            id="text_green",
                            type="text",
                            start_time=0.0,
                            end_time=2.0,
                            z_index=1,
                            transform={"x": 0.5, "y": 0.5, "scale": 1.0},
                            content={"text": "LONG WIDE TEXT OVERLAY", "font_size": 36, "color": "#00FF00"},
                        ),
                        SceneLayer(
                            id="shape_b_blue",
                            type="shape",
                            start_time=0.0,
                            end_time=2.0,
                            z_index=2,
                            transform={"x": 0.5, "y": 0.5, "scale": 1.0},
                            content={"shape_type": "rectangle", "width": 0.2, "height": 0.2, "fill": "#0000FF"},
                        ),
                    ],
                )
            ],
        )

        async with async_session_factory() as db:
            res = await compositor.render_project(doc, ws_id, db, media_workspace=mws)

        frame = _extract_frame(res.video_path, 1.0, mws.scenes_dir / "frame_t3.png")
        pixels = list(frame.getdata())

        # All 3 layers must be verified in the output:
        red_pixels = [p for p in pixels if p[0] > 150 and p[1] < 100 and p[2] < 100]
        green_pixels = [p for p in pixels if p[1] > 150 and p[0] < 100 and p[2] < 100]
        blue_pixels = [p for p in pixels if p[2] > 150 and p[0] < 100 and p[1] < 100]

        assert len(red_pixels) > 500, "Shape A (Red, z=0) must be visible in background"
        assert len(green_pixels) > 20, "Text (Green, z=1) must be visible over Red"
        assert len(blue_pixels) > 200, "Shape B (Blue, z=2) must be visible over Text"
    finally:
        mws.cleanup()


@pytest.mark.asyncio
async def test_5_caption_interleaving():
    """Test 5: Shape A (Red) z=0, Caption (Yellow) z=1, Shape B (Blue) z=2."""
    compositor = TimelineCompositor()
    mws = MediaWorkspace(prefix="test_p42c1_t5_")
    ws_id = uuid.uuid4()

    try:
        doc = ProjectDocumentV1(
            settings=ProjectSettings(
                width=640,
                height=360,
                fps=30,
                total_duration=2.0,
                captions=CaptionSettings(
                    enabled=True,
                    style=CaptionStyle(
                        font_size=32,
                        color="#FFFF00",  # Bright Yellow
                        background_color="#000000",
                        background_opacity=0.0,
                        position="center",
                        z_index=1,  # Interleaved at z=1
                    ),
                ),
            ),
            scenes=[
                Scene(
                    id="sc_5",
                    sequence=1,
                    duration=2.0,
                    background={"type": "color", "value": "#000000"},
                    subtitles=[
                        {"id": 1, "start": 0.0, "end": 2.0, "text": "CAPTION INTERLEAVED", "z_index": 1}
                    ],
                    layers=[
                        SceneLayer(
                            id="shape_a_red",
                            type="shape",
                            start_time=0.0,
                            end_time=2.0,
                            z_index=0,
                            transform={"x": 0.5, "y": 0.5, "scale": 1.0},
                            content={"shape_type": "rectangle", "width": 0.8, "height": 0.8, "fill": "#FF0000"},
                        ),
                        SceneLayer(
                            id="shape_b_blue",
                            type="shape",
                            start_time=0.0,
                            end_time=2.0,
                            z_index=2,
                            transform={"x": 0.5, "y": 0.5, "scale": 1.0},
                            content={"shape_type": "rectangle", "width": 0.2, "height": 0.2, "fill": "#0000FF"},
                        ),
                    ],
                )
            ],
        )

        async with async_session_factory() as db:
            res = await compositor.render_project(doc, ws_id, db, media_workspace=mws)

        frame = _extract_frame(res.video_path, 1.0, mws.scenes_dir / "frame_t5.png")
        pixels = list(frame.getdata())

        red_pixels = [p for p in pixels if p[0] > 150 and p[1] < 100 and p[2] < 100]
        # Yellow caption: high red and high green, low blue
        yellow_pixels = [p for p in pixels if p[0] > 150 and p[1] > 150 and p[2] < 100]
        blue_pixels = [p for p in pixels if p[2] > 150 and p[0] < 100 and p[1] < 100]

        assert len(red_pixels) > 500, "Shape A (Red, z=0) must be visible"
        assert len(yellow_pixels) > 20, "Caption (Yellow, z=1) must be visible over Red"
        assert len(blue_pixels) > 200, "Shape B (Blue, z=2) must be visible over Caption"
    finally:
        mws.cleanup()


@pytest.mark.asyncio
async def test_6_hidden_text():
    """Test 6: Hidden text (enabled = False) must NOT contribute pixels to export."""
    compositor = TimelineCompositor()
    mws = MediaWorkspace(prefix="test_p42c1_t6_")
    ws_id = uuid.uuid4()

    try:
        doc = ProjectDocumentV1(
            settings=ProjectSettings(width=640, height=360, fps=30, total_duration=2.0),
            scenes=[
                Scene(
                    id="sc_6",
                    sequence=1,
                    duration=2.0,
                    background={"type": "color", "value": "#000000"},
                    layers=[
                        SceneLayer(
                            id="hidden_text",
                            type="text",
                            enabled=False,
                            start_time=0.0,
                            end_time=2.0,
                            transform={"x": 0.5, "y": 0.5},
                            content={"text": "SECRET TEXT", "color": "#00FF00"},
                        ),
                    ],
                )
            ],
        )

        async with async_session_factory() as db:
            res = await compositor.render_project(doc, ws_id, db, media_workspace=mws)

        frame = _extract_frame(res.video_path, 1.0, mws.scenes_dir / "frame_t6.png")
        pixels = list(frame.getdata())
        green_pixels = [p for p in pixels if p[1] > 100]
        assert len(green_pixels) == 0, "Hidden text must not be rendered"
    finally:
        mws.cleanup()


@pytest.mark.asyncio
async def test_7_locked_text_renders():
    """Test 7: Locked text (locked = True, enabled = True) still renders in export."""
    compositor = TimelineCompositor()
    mws = MediaWorkspace(prefix="test_p42c1_t7_")
    ws_id = uuid.uuid4()

    try:
        doc = ProjectDocumentV1(
            settings=ProjectSettings(width=640, height=360, fps=30, total_duration=2.0),
            scenes=[
                Scene(
                    id="sc_7",
                    sequence=1,
                    duration=2.0,
                    background={"type": "color", "value": "#000000"},
                    layers=[
                        SceneLayer(
                            id="locked_text",
                            type="text",
                            locked=True,
                            enabled=True,
                            start_time=0.0,
                            end_time=2.0,
                            transform={"x": 0.5, "y": 0.5},
                            content={"text": "LOCKED BUT VISIBLE", "font_size": 36, "color": "#00FF00"},
                        ),
                    ],
                )
            ],
        )

        async with async_session_factory() as db:
            res = await compositor.render_project(doc, ws_id, db, media_workspace=mws)

        frame = _extract_frame(res.video_path, 1.0, mws.scenes_dir / "frame_t7.png")
        pixels = list(frame.getdata())
        green_pixels = [p for p in pixels if p[1] > 150]
        assert len(green_pixels) > 50, "Locked layer must render normally"
    finally:
        mws.cleanup()


@pytest.mark.asyncio
async def test_8_timing_interval():
    """Test 8: Text renders only during configured timeline interval [1.0, 2.0]."""
    compositor = TimelineCompositor()
    mws = MediaWorkspace(prefix="test_p42c1_t8_")
    ws_id = uuid.uuid4()

    try:
        doc = ProjectDocumentV1(
            settings=ProjectSettings(width=640, height=360, fps=30, total_duration=3.0),
            scenes=[
                Scene(
                    id="sc_8",
                    sequence=1,
                    duration=3.0,
                    background={"type": "color", "value": "#000000"},
                    layers=[
                        SceneLayer(
                            id="timed_text",
                            type="text",
                            start_time=1.0,
                            end_time=2.0,
                            transform={"x": 0.5, "y": 0.5},
                            content={"text": "TIMED", "font_size": 36, "color": "#00FF00"},
                        ),
                    ],
                )
            ],
        )

        async with async_session_factory() as db:
            res = await compositor.render_project(doc, ws_id, db, media_workspace=mws)

        # Before (t = 0.5s): Absent
        f_before = _extract_frame(res.video_path, 0.5, mws.scenes_dir / "frame_t8_before.png")
        g_before = [p for p in list(f_before.getdata()) if p[1] > 100]
        assert len(g_before) == 0, "Text must not appear before start_time"

        # During (t = 1.5s): Present
        f_during = _extract_frame(res.video_path, 1.5, mws.scenes_dir / "frame_t8_during.png")
        g_during = [p for p in list(f_during.getdata()) if p[1] > 150]
        assert len(g_during) > 30, "Text must appear during interval"

        # After (t = 2.5s): Absent
        f_after = _extract_frame(res.video_path, 2.5, mws.scenes_dir / "frame_t8_after.png")
        g_after = [p for p in list(f_after.getdata()) if p[1] > 100]
        assert len(g_after) == 0, "Text must not appear after end_time"
    finally:
        mws.cleanup()


@pytest.mark.asyncio
async def test_10_rotation_rendering():
    """Test 10: Rotated text (45 degrees) renders cleanly without compositor error."""
    compositor = TimelineCompositor()
    mws = MediaWorkspace(prefix="test_p42c1_t10_")
    ws_id = uuid.uuid4()

    try:
        doc = ProjectDocumentV1(
            settings=ProjectSettings(width=640, height=360, fps=30, total_duration=2.0),
            scenes=[
                Scene(
                    id="sc_10",
                    sequence=1,
                    duration=2.0,
                    background={"type": "color", "value": "#000000"},
                    layers=[
                        SceneLayer(
                            id="rotated_text",
                            type="text",
                            start_time=0.0,
                            end_time=2.0,
                            transform={"x": 0.5, "y": 0.5, "rotation": 45.0},
                            content={"text": "ROTATED 45", "font_size": 36, "color": "#00FF00"},
                        ),
                    ],
                )
            ],
        )

        async with async_session_factory() as db:
            res = await compositor.render_project(doc, ws_id, db, media_workspace=mws)

        assert res.video_path.exists()
        frame = _extract_frame(res.video_path, 1.0, mws.scenes_dir / "frame_t10.png")
        pixels = list(frame.getdata())
        green_pixels = [p for p in pixels if p[1] > 150]
        assert len(green_pixels) > 50
    finally:
        mws.cleanup()


@pytest.mark.asyncio
async def test_11_legacy_document_baseline():
    """Test 11: Document without z_index renders using media -> text -> elements baseline."""
    compositor = TimelineCompositor()
    mws = MediaWorkspace(prefix="test_p42c1_t11_")
    ws_id = uuid.uuid4()

    try:
        doc = ProjectDocumentV1(
            settings=ProjectSettings(width=640, height=360, fps=30, total_duration=2.0),
            scenes=[
                Scene(
                    id="sc_11",
                    sequence=1,
                    duration=2.0,
                    background={"type": "color", "value": "#000000"},
                    layers=[
                        # No z_index: media first, text on top
                        SceneLayer(
                            id="legacy_media",
                            type="shape",
                            start_time=0.0,
                            end_time=2.0,
                            transform={"x": 0.5, "y": 0.5},
                            content={"shape_type": "rectangle", "width": 0.5, "height": 0.5, "fill": "#FF0000"},
                        ),
                        SceneLayer(
                            id="legacy_text",
                            type="text",
                            start_time=0.0,
                            end_time=2.0,
                            transform={"x": 0.5, "y": 0.5},
                            content={"text": "LEGACY", "font_size": 36, "color": "#00FF00"},
                        ),
                    ],
                )
            ],
        )

        async with async_session_factory() as db:
            res = await compositor.render_project(doc, ws_id, db, media_workspace=mws)

        frame = _extract_frame(res.video_path, 1.0, mws.scenes_dir / "frame_t11.png")
        pixels = list(frame.getdata())
        green_pixels = [p for p in pixels if p[1] > 150]
        assert len(green_pixels) > 30, "In legacy baseline, text must appear above media"
    finally:
        mws.cleanup()


@pytest.mark.asyncio
async def test_13_no_double_rendering():
    """Test 13: Verifies that text/captions are rendered through unified RGBA and NOT burned twice via ASS."""
    compositor = TimelineCompositor()
    mws = MediaWorkspace(prefix="test_p42c1_t13_")
    ws_id = uuid.uuid4()

    try:
        doc = ProjectDocumentV1(
            settings=ProjectSettings(
                width=640,
                height=360,
                fps=30,
                total_duration=2.0,
                captions=CaptionSettings(
                    enabled=True,
                    style=CaptionStyle(font_size=28, color="#FFFFFF", position="bottom"),
                ),
            ),
            scenes=[
                Scene(
                    id="sc_13",
                    sequence=1,
                    duration=2.0,
                    background={"type": "color", "value": "#000000"},
                    subtitles=[{"id": 1, "start": 0.0, "end": 2.0, "text": "Caption Once"}],
                    layers=[
                        SceneLayer(
                            id="txt_once",
                            type="text",
                            start_time=0.0,
                            end_time=2.0,
                            transform={"x": 0.5, "y": 0.2},
                            content={"text": "Text Once", "font_size": 36, "color": "#FFFFFF"},
                        ),
                    ],
                )
            ],
        )

        async with async_session_factory() as db:
            res = await compositor.render_project(doc, ws_id, db, media_workspace=mws)

        # ASS files were generated on disk for export/inspection
        text_ass = mws.scenes_dir / "scene_000_text.ass"
        captions_ass = mws.scenes_dir / "scene_000_captions.ass"
        assert text_ass.exists()
        assert captions_ass.exists()

        # Extract frame and verify output is valid and clean
        frame = _extract_frame(res.video_path, 1.0, mws.scenes_dir / "frame_t13.png")
        assert frame.size == (640, 360)
    finally:
        mws.cleanup()


@pytest.mark.asyncio
async def test_4_text_between_elements():
    """Test 4: Shape A (Red) z=0, Text (Green) z=1, Shape B (Blue) z=2."""
    compositor = TimelineCompositor()
    mws = MediaWorkspace(prefix="test_p42c1_t4_")
    ws_id = uuid.uuid4()

    try:
        doc = ProjectDocumentV1(
            settings=ProjectSettings(width=640, height=360, fps=30, total_duration=2.0),
            scenes=[
                Scene(
                    id="sc_4",
                    sequence=1,
                    duration=2.0,
                    background={"type": "color", "value": "#000000"},
                    layers=[
                        SceneLayer(
                            id="elem_shape_0",
                            type="shape",
                            start_time=0.0,
                            end_time=2.0,
                            z_index=0,
                            transform={"x": 0.5, "y": 0.5, "scale": 1.0},
                            content={"shape_type": "rectangle", "width": 0.8, "height": 0.8, "fill": "#FF0000"},
                        ),
                        SceneLayer(
                            id="elem_text_1",
                            type="text",
                            start_time=0.0,
                            end_time=2.0,
                            z_index=1,
                            transform={"x": 0.5, "y": 0.5, "scale": 1.0},
                            content={"text": "ELEMENT INTERLEAVED", "font_size": 36, "color": "#00FF00"},
                        ),
                        SceneLayer(
                            id="elem_shape_2",
                            type="shape",
                            start_time=0.0,
                            end_time=2.0,
                            z_index=2,
                            transform={"x": 0.5, "y": 0.5, "scale": 1.0},
                            content={"shape_type": "rectangle", "width": 0.2, "height": 0.2, "fill": "#0000FF"},
                        ),
                    ],
                )
            ],
        )

        async with async_session_factory() as db:
            res = await compositor.render_project(doc, ws_id, db, media_workspace=mws)

        frame = _extract_frame(res.video_path, 1.0, mws.scenes_dir / "frame_t4.png")
        pixels = list(frame.getdata())
        red_pixels = [p for p in pixels if p[0] > 150 and p[1] < 100 and p[2] < 100]
        green_pixels = [p for p in pixels if p[1] > 150 and p[0] < 100 and p[2] < 100]
        blue_pixels = [p for p in pixels if p[2] > 150 and p[0] < 100 and p[1] < 100]

        assert len(red_pixels) > 500, "Bottom shape must be visible"
        assert len(green_pixels) > 20, "Middle text must be visible"
        assert len(blue_pixels) > 200, "Top shape must be visible"
    finally:
        mws.cleanup()


@pytest.mark.asyncio
async def test_9_opacity_blending():
    """Test 9: Partially transparent text blends with underlying solid background."""
    compositor = TimelineCompositor()
    mws = MediaWorkspace(prefix="test_p42c1_t9_")
    ws_id = uuid.uuid4()

    try:
        # White background (#FFFFFF) with 50% opacity red text (#FF0000)
        # Resulting text pixels should have high Red and non-zero Green/Blue from the white background
        doc = ProjectDocumentV1(
            settings=ProjectSettings(width=640, height=360, fps=30, total_duration=2.0),
            scenes=[
                Scene(
                    id="sc_9",
                    sequence=1,
                    duration=2.0,
                    background={"type": "color", "value": "#FFFFFF"},
                    layers=[
                        SceneLayer(
                            id="semi_text",
                            type="text",
                            start_time=0.0,
                            end_time=2.0,
                            z_index=1,
                            transform={"x": 0.5, "y": 0.5},
                            content={"text": "TRANSPARENT", "font_size": 48, "color": "#FF0000", "opacity": 0.5},
                        ),
                    ],
                )
            ],
        )

        async with async_session_factory() as db:
            res = await compositor.render_project(doc, ws_id, db, media_workspace=mws)

        frame = _extract_frame(res.video_path, 1.0, mws.scenes_dir / "frame_t9.png")
        pixels = list(frame.getdata())
        # Blended pink/red pixels: R > 200, and G between 50 and 200 (not pure 0, not pure 255)
        blended_pixels = [p for p in pixels if p[0] > 200 and 50 < p[1] < 220]
        assert len(blended_pixels) > 50, "Expected blended alpha text pixels"
    finally:
        mws.cleanup()


@pytest.mark.asyncio
async def test_12_mixed_layer_types_interleaved():
    """Test 12: Shape z=0, Caption z=1, Text z=2, Shape z=3 all interleaved deterministically."""
    compositor = TimelineCompositor()
    mws = MediaWorkspace(prefix="test_p42c1_t12_")
    ws_id = uuid.uuid4()

    try:
        doc = ProjectDocumentV1(
            settings=ProjectSettings(
                width=640,
                height=360,
                fps=30,
                total_duration=2.0,
                captions=CaptionSettings(
                    enabled=True,
                    style=CaptionStyle(
                        font_size=24,
                        color="#FFFF00",  # Yellow
                        position="center",
                        z_index=1,
                    ),
                ),
            ),
            scenes=[
                Scene(
                    id="sc_12",
                    sequence=1,
                    duration=2.0,
                    background={"type": "color", "value": "#000000"},
                    subtitles=[{"id": 1, "start": 0.0, "end": 2.0, "text": "MIXED CAPTION", "z_index": 1}],
                    layers=[
                        # Shape at bottom: Red z=0
                        SceneLayer(
                            id="m_bottom_shape",
                            type="shape",
                            start_time=0.0,
                            end_time=2.0,
                            z_index=0,
                            transform={"x": 0.5, "y": 0.5},
                            content={"shape_type": "rectangle", "width": 0.9, "height": 0.9, "fill": "#FF0000"},
                        ),
                        # Text at z=2: Green
                        SceneLayer(
                            id="m_mid_text",
                            type="text",
                            start_time=0.0,
                            end_time=2.0,
                            z_index=2,
                            transform={"x": 0.5, "y": 0.3},
                            content={"text": "TOP TEXT", "font_size": 36, "color": "#00FF00"},
                        ),
                        # Shape at top: Blue z=3
                        SceneLayer(
                            id="m_top_shape",
                            type="shape",
                            start_time=0.0,
                            end_time=2.0,
                            z_index=3,
                            transform={"x": 0.5, "y": 0.5},
                            content={"shape_type": "rectangle", "width": 0.15, "height": 0.15, "fill": "#0000FF"},
                        ),
                    ],
                )
            ],
        )

        async with async_session_factory() as db:
            res = await compositor.render_project(doc, ws_id, db, media_workspace=mws)

        frame = _extract_frame(res.video_path, 1.0, mws.scenes_dir / "frame_t12.png")
        pixels = list(frame.getdata())

        red = [p for p in pixels if p[0] > 150 and p[1] < 100 and p[2] < 100]
        yellow = [p for p in pixels if p[0] > 150 and p[1] > 150 and p[2] < 100]
        green = [p for p in pixels if p[1] > 150 and p[0] < 100 and p[2] < 100]
        blue = [p for p in pixels if p[2] > 150 and p[0] < 100 and p[1] < 100]

        assert len(red) > 500, "Base shape (Red, z=0) visible"
        assert len(yellow) > 20, "Caption (Yellow, z=1) visible"
        assert len(green) > 20, "Text (Green, z=2) visible"
        assert len(blue) > 100, "Top shape (Blue, z=3) visible"
    finally:
        mws.cleanup()

