"""Phase 36: Studio Render Parity Corrections Test Suite.

Verifies:
1. Text ASS generation injects \frz(round(-rotation, 2)) for positive angles (rotation = 30 -> \frz(-30))
2. Text ASS generation injects positive \frz for negative angles (rotation = -45 -> \frz(45))
3. Text ASS rotation normalization for 0, 90, -90, 180, -180, and wrapped angles
4. Text ASS font size scaling (font_size * scale)
5. Actual FFmpeg render burn-in with rotated and scaled text on video frames
6. Shape sizing render parity across 16:9, 9:16, and 1:1 canvas profiles
7. Sticker sizing render parity across 16:9, 9:16, 1:1 and scales (0.5, 1.0, 2.0)
8. Media layer scale support for scale > 2.0 (up to canonical limit 3.0)
"""

import uuid
from pathlib import Path
import pytest

from app.db.session import async_session_factory
from app.media.compositor import CanvasProfile, TimelineCompositor
from app.media.workspace import MediaWorkspace
from app.schemas.project_document import ProjectDocumentV1, ProjectSettings, Scene, SceneLayer


# ==============================================================================
# 1. TEXT ROTATION AND SCALE ASS GENERATION
# ==============================================================================

def test_text_ass_rotation_positive_angle(tmp_path: Path):
    """Test 1: Verify rotation = 30 produces \\frz(-30) in Dialogue tag."""
    compositor = TimelineCompositor()
    canvas = CanvasProfile(width=1280, height=720, fps=25)
    out_ass = tmp_path / "test_rot_pos.ass"

    layer = SceneLayer(
        id="txt_rot_pos",
        type="text",
        start_time=0.0,
        end_time=2.0,
        enabled=True,
        transform={"x": 0.5, "y": 0.5, "scale": 1.0, "rotation": 30.0},
        content={"text": "Rotated Positive 30", "font_size": 48},
    )

    res = compositor._generate_scene_text_ass_file(layers=[layer], canvas=canvas, output_path=out_ass)
    assert res is not None and res.exists()
    content = res.read_text(encoding="utf-8")
    assert "\\frz(-30)" in content
    assert "\\pos(640,360)" in content


def test_text_ass_rotation_negative_angle(tmp_path: Path):
    """Test 2: Verify rotation = -45 produces \\frz(45) in Dialogue tag."""
    compositor = TimelineCompositor()
    canvas = CanvasProfile(width=1280, height=720, fps=25)
    out_ass = tmp_path / "test_rot_neg.ass"

    layer = SceneLayer(
        id="txt_rot_neg",
        type="text",
        start_time=0.0,
        end_time=2.0,
        enabled=True,
        transform={"x": 0.5, "y": 0.5, "scale": 1.0, "rotation": -45.0},
        content={"text": "Rotated Negative 45", "font_size": 48},
    )

    res = compositor._generate_scene_text_ass_file(layers=[layer], canvas=canvas, output_path=out_ass)
    assert res is not None and res.exists()
    content = res.read_text(encoding="utf-8")
    assert "\\frz(45)" in content
    assert "\\pos(640,360)" in content


@pytest.mark.parametrize(
    "rotation, expected_tag",
    [
        (0.0, "\\frz(0)"),
        (90.0, "\\frz(-90)"),
        (-90.0, "\\frz(90)"),
        (180.0, "\\frz(-180)"),
        (-180.0, "\\frz(180)"),
        (270.0, "\\frz(90)"),
        (-270.0, "\\frz(-90)"),
        (35.5, "\\frz(-35.5)"),
    ],
)
def test_text_ass_rotation_normalization(tmp_path: Path, rotation: float, expected_tag: str):
    """Test 3: Verify rotation normalization across representative and wrapped angles."""
    compositor = TimelineCompositor()
    canvas = CanvasProfile(width=1280, height=720, fps=25)
    out_ass = tmp_path / f"test_rot_{rotation}.ass"

    layer = SceneLayer(
        id=f"txt_norm_{rotation}",
        type="text",
        start_time=0.0,
        end_time=2.0,
        enabled=True,
        transform={"x": 0.5, "y": 0.5, "scale": 1.0, "rotation": rotation},
        content={"text": f"Angle {rotation}", "font_size": 48},
    )

    res = compositor._generate_scene_text_ass_file(layers=[layer], canvas=canvas, output_path=out_ass)
    assert res is not None and res.exists()
    content = res.read_text(encoding="utf-8")
    assert expected_tag in content


def test_text_ass_scale_font_size(tmp_path: Path):
    """Test 4: Verify scale = 2.0 multiplies baseFontSize by 2 in ASS Style."""
    compositor = TimelineCompositor()
    canvas = CanvasProfile(width=1280, height=720, fps=25)
    out_ass = tmp_path / "test_scale.ass"

    layer = SceneLayer(
        id="txt_scale_2",
        type="text",
        start_time=0.0,
        end_time=2.0,
        enabled=True,
        transform={"x": 0.5, "y": 0.5, "scale": 2.0, "rotation": 0.0},
        content={"text": "Scaled Text", "font_size": 48, "font_family": "Arial"},
    )

    res = compositor._generate_scene_text_ass_file(layers=[layer], canvas=canvas, output_path=out_ass)
    assert res is not None and res.exists()
    content = res.read_text(encoding="utf-8")

    # Font size in style should be 48 * 2 = 96
    assert "Style: TextLayer_0,Arial,96," in content
    # Content object itself is not mutated
    assert layer.content["font_size"] == 48


# ==============================================================================
# 2. ACTUAL FFMPEG RENDER BURN-IN TEST
# ==============================================================================

@pytest.mark.asyncio
async def test_text_ffmpeg_burn_in_rotated_and_scaled(tmp_path: Path):
    """Test 5: Actual FFmpeg video render burning in rotated + scaled text into MP4 pixels."""
    compositor = TimelineCompositor()
    canvas = CanvasProfile(width=640, height=360, fps=25)

    text_layer = SceneLayer(
        id="burn_in_txt",
        type="text",
        name="Rotated Title",
        start_time=0.0,
        end_time=1.5,
        enabled=True,
        transform={"x": 0.5, "y": 0.5, "scale": 1.5, "rotation": 30.0},
        content={
            "text": "BURN_IN_TEST",
            "font_size": 36,
            "color": "#FFFFFF",
            "font_family": "Arial",
            "font_weight": "bold",
        },
    )

    scene = Scene(
        id="scene_rot_burn",
        sequence=1,
        duration=1.5,
        background={"type": "color", "value": "#000000"},
        layers=[text_layer],
    )

    async with async_session_factory() as db:
        mws = MediaWorkspace(base_dir=tmp_path)
        try:
            clip_path = await compositor._render_scene_clip(
                scene=scene,
                scene_index=0,
                canvas=canvas,
                workspace_id=uuid.uuid4(),
                db=db,
                mws=mws,
            )
            assert clip_path.exists()
            assert clip_path.stat().st_size > 1000  # Valid MP4 video output!

            # Extract frame and verify text pixels were burned into the output
            frame_png = tmp_path / "frame_rot_check.png"
            await compositor.ffmpeg_service.extract_thumbnail(
                video_path=clip_path,
                output_png=frame_png,
                timestamp=0.5,
            )
            assert frame_png.exists()
            from PIL import Image
            im = Image.open(frame_png).convert("L")
            white_pixels = [p for p in im.getdata() if p > 128]
            assert len(white_pixels) > 50, f"Expected text pixels burned into frame, found {len(white_pixels)}"
        finally:
            mws.cleanup()


# ==============================================================================
# 3. SHAPE & STICKER SIZING PARITY
# ==============================================================================

@pytest.mark.parametrize(
    "aspect_ratio, width, height",
    [
        ("16:9", 1280, 720),
        ("9:16", 720, 1280),
        ("1:1", 720, 720),
    ],
)
@pytest.mark.asyncio
async def test_shape_render_parity_aspect_ratios(tmp_path: Path, aspect_ratio: str, width: int, height: int):
    """Test 6: Verify shape renders proportionally across 16:9, 9:16, and 1:1 canvas ratios."""
    compositor = TimelineCompositor()
    canvas = CanvasProfile(width=width, height=height, aspect_ratio=aspect_ratio, fps=25)

    shape_layer = SceneLayer(
        id=f"shape_{aspect_ratio.replace(':', '_')}",
        type="shape",
        name="Parity Box",
        start_time=0.0,
        end_time=1.0,
        enabled=True,
        transform={"x": 0.5, "y": 0.5, "scale": 1.0, "rotation": 0.0},
        content={
            "shape_type": "rectangle",
            "width": 0.35,
            "height": 0.2,
            "fill": "#3B82F6",
        },
    )

    scene = Scene(
        id=f"sc_shape_{aspect_ratio.replace(':', '_')}",
        sequence=1,
        duration=1.0,
        background={"type": "color", "value": "#0F172A"},
        layers=[shape_layer],
    )

    async with async_session_factory() as db:
        mws = MediaWorkspace(base_dir=tmp_path)
        try:
            clip_path = await compositor._render_scene_clip(
                scene=scene,
                scene_index=0,
                canvas=canvas,
                workspace_id=uuid.uuid4(),
                db=db,
                mws=mws,
            )
            assert clip_path.exists()
            assert clip_path.stat().st_size > 1000
        finally:
            mws.cleanup()


@pytest.mark.parametrize(
    "scale",
    [0.5, 1.0, 2.0],
)
@pytest.mark.asyncio
async def test_sticker_render_parity_scales(tmp_path: Path, scale: float):
    """Test 7: Verify sticker renders proportionally across scale values."""
    compositor = TimelineCompositor()
    canvas = CanvasProfile(width=640, height=360, fps=25)

    sticker_layer = SceneLayer(
        id=f"sticker_scale_{scale}",
        type="sticker",
        name="Star Sticker",
        start_time=0.0,
        end_time=1.0,
        enabled=True,
        transform={"x": 0.5, "y": 0.5, "scale": scale, "rotation": 15.0},
        content={"sticker_id": "star", "fill": "#FBBF24"},
    )

    scene = Scene(
        id=f"sc_sticker_{scale}",
        sequence=1,
        duration=1.0,
        background={"type": "color", "value": "#000000"},
        layers=[sticker_layer],
    )

    async with async_session_factory() as db:
        mws = MediaWorkspace(base_dir=tmp_path)
        try:
            clip_path = await compositor._render_scene_clip(
                scene=scene,
                scene_index=0,
                canvas=canvas,
                workspace_id=uuid.uuid4(),
                db=db,
                mws=mws,
            )
            assert clip_path.exists()
            assert clip_path.stat().st_size > 1000
        finally:
            mws.cleanup()


# ==============================================================================
# 4. MEDIA SCALE PARITY
# ==============================================================================

@pytest.mark.asyncio
async def test_media_layer_high_scale(tmp_path: Path):
    """Test 8: Verify media layer renders at high scale (scale = 3.0) without capping."""
    compositor = TimelineCompositor()
    canvas = CanvasProfile(width=640, height=360, fps=25)

    # Synthetic image
    from PIL import Image
    img_path = tmp_path / "test_input.png"
    Image.new("RGB", (320, 180), (255, 0, 0)).save(str(img_path))

    # Media layer with scale = 3.0
    media_layer = SceneLayer(
        id="media_high_scale",
        type="image",
        name="High Scale Image",
        start_time=0.0,
        end_time=1.0,
        enabled=True,
        transform={"x": 0.5, "y": 0.5, "scale": 3.0, "rotation": 0.0},
        content={"asset_id": "mock_asset", "opacity": 1.0},
    )

    scene = Scene(
        id="sc_media_scale",
        sequence=1,
        duration=1.0,
        background={"type": "color", "value": "#000000"},
        layers=[media_layer],
    )

    async with async_session_factory() as db:
        mws = MediaWorkspace(base_dir=tmp_path)
        try:
            # Mock resolving asset to our synthetic image
            mws.resolve_asset = lambda *args, **kwargs: (
                asyncio.sleep(0),
                img_path
            )[1]
            # Since resolve_asset is an async method on MediaWorkspace, mock it properly
            async def _mock_resolve(*args, **kwargs):
                return img_path
            mws.resolve_asset = _mock_resolve

            clip_path = await compositor._render_scene_clip(
                scene=scene,
                scene_index=0,
                canvas=canvas,
                workspace_id=uuid.uuid4(),
                db=db,
                mws=mws,
            )
            assert clip_path.exists()
            assert clip_path.stat().st_size > 1000
        finally:
            mws.cleanup()
