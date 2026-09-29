"""Unit tests for Phase 42C-1 text and caption rasterizer."""

import tempfile
from pathlib import Path
from PIL import Image

from app.media.text_rasterizer import (
    render_caption_cue_to_image,
    render_text_layer_to_image,
    resolve_font,
)


def test_resolve_font_default_and_bold():
    font_reg = resolve_font("Arial", 32, is_bold=False)
    assert font_reg is not None

    font_bold = resolve_font("Arial", 32, is_bold=True)
    assert font_bold is not None


def test_render_text_layer_to_image_basic():
    with tempfile.TemporaryDirectory() as tmp_dir:
        out_png = Path(tmp_dir) / "test_text.png"
        img = render_text_layer_to_image(
            text="Hello World",
            font_size=40,
            color="#FFFFFF",
            opacity=1.0,
            output_path=out_png,
        )
        assert out_png.exists()
        assert img.mode == "RGBA"
        assert img.width > 20
        assert img.height > 10

        # Check that there are non-transparent white pixels
        pixels = list(img.getdata())
        white_pixels = [p for p in pixels if p[0] > 200 and p[1] > 200 and p[2] > 200 and p[3] > 200]
        assert len(white_pixels) > 50


def test_render_text_layer_with_background_box():
    with tempfile.TemporaryDirectory() as tmp_dir:
        out_png = Path(tmp_dir) / "test_text_bg.png"
        img = render_text_layer_to_image(
            text="Header Banner",
            font_size=36,
            color="#FFFFFF",
            background_color="#3B82F6",
            background_opacity=0.8,
            output_path=out_png,
        )
        assert out_png.exists()
        pixels = list(img.getdata())
        # Blue background pixels: R<100, G>100, B>200, Alpha > 150
        blue_pixels = [p for p in pixels if p[0] < 100 and p[1] > 100 and p[2] > 200 and p[3] > 150]
        assert len(blue_pixels) > 100


def test_render_text_layer_opacity():
    with tempfile.TemporaryDirectory() as tmp_dir:
        out_png = Path(tmp_dir) / "test_text_opacity.png"
        img = render_text_layer_to_image(
            text="Transparent Text",
            font_size=32,
            color="#FF0000",
            opacity=0.5,
            output_path=out_png,
        )
        pixels = list(img.getdata())
        # Maximum alpha around 128 (0.5 * 255 = 127.5), allowing for Lanczos resampling ringing
        max_alpha = max(p[3] for p in pixels)
        assert max_alpha <= 160
        assert max_alpha >= 100


def test_render_caption_cue_to_image():
    with tempfile.TemporaryDirectory() as tmp_dir:
        out_png = Path(tmp_dir) / "test_caption.png"
        img = render_caption_cue_to_image(
            cue_text="Transcribed speech cue",
            font_size=28,
            color="#FFFF00",
            background_color="#000000",
            background_opacity=0.6,
            output_path=out_png,
        )
        assert out_png.exists()
        assert img.width > 20
        assert img.height > 10
