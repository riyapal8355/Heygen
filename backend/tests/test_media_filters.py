"""Unit tests for FFmpeg filtergraph builders in app.media.filters."""

from pathlib import Path
import pytest

from app.media.filters import (
    build_audio_amix,
    build_audio_volume,
    build_color_source,
    build_drawtext_filter,
    build_scale_and_pad,
    escape_filter_path,
    normalize_color_spec,
)


def test_escape_filter_path_windows_and_posix():
    """Verify colon escaping for FFmpeg filter options on Windows and POSIX paths."""
    win_path = Path("C:/Users/test/Documents/text.txt")
    escaped = escape_filter_path(win_path)
    assert r"C\:" in escaped
    assert "\\" not in escaped or r"\:" in escaped


def test_normalize_color_spec():
    """Verify hex normalization to FFmpeg 0x format and named colors preservation."""
    assert normalize_color_spec("#1e1e2e") == "0x1e1e2e"
    assert normalize_color_spec("#fff") == "0xffffff"
    assert normalize_color_spec("black") == "black"
    assert normalize_color_spec("BLUE") == "blue"


def test_build_color_source():
    """Verify color source arguments for synthetic background generation."""
    args = build_color_source("#0f172a", width=1920, height=1080, duration=5.0, fps=30)
    assert "-f" in args
    assert "lavfi" in args
    assert "-i" in args
    filter_arg = args[args.index("-i") + 1]
    assert "color=c=0x0f172a" in filter_arg
    assert "s=1920x1080" in filter_arg
    assert "r=30" in filter_arg
    assert "d=5.000" in filter_arg


def test_build_scale_and_pad_contain():
    """Verify contain mode letterboxing/pillarboxing filter syntax."""
    f = build_scale_and_pad(1920, 1080, fit_mode="contain", bg_color="black")
    assert "scale=1920:1080:force_original_aspect_ratio=decrease" in f
    assert "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=black" in f
    assert "setsar=1" in f


def test_build_scale_and_pad_cover():
    """Verify cover mode crop filter syntax."""
    f = build_scale_and_pad(1080, 1920, fit_mode="cover")
    assert "scale=1080:1920:force_original_aspect_ratio=increase" in f
    assert "crop=1080:1920" in f
    assert "setsar=1" in f


def test_build_scale_and_pad_stretch():
    """Verify stretch mode filter syntax."""
    f = build_scale_and_pad(1280, 720, fit_mode="stretch")
    assert f == "scale=1280:720,setsar=1"


def test_build_drawtext_filter():
    """Verify safe drawtext referencing external textfile."""
    text_path = Path("C:/scratch/scene_001_text.txt")
    dt = build_drawtext_filter(
        text_file_path=text_path,
        font_size=48,
        font_color="white",
        box=True,
    )
    assert "drawtext=" in dt
    assert "textfile=" in dt
    assert "fontsize=48" in dt
    assert "fontcolor=white" in dt
    assert "box=1" in dt


def test_build_audio_volume_and_amix():
    """Verify audio gain and mixing filters."""
    vol = build_audio_volume(0.35)
    assert vol == "volume=0.35"

    # Clamping
    vol_clamped = build_audio_volume(10.0)
    assert vol_clamped == "volume=5.00"

    amix = build_audio_amix(inputs_count=2, duration_mode="first")
    assert amix == "amix=inputs=2:duration=first:dropout_transition=2.0"
