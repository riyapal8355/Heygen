"""FFmpeg filtergraph builders for video scaling, overlays, color backgrounds, and audio mixing."""

import re
from pathlib import Path
from typing import List, Optional, Union


def escape_filter_path(path: Union[str, Path]) -> str:
    """Escape a filesystem path for inclusion in an FFmpeg filter argument string.

    Handles Windows drive letters ('C:' -> 'C\\:') and backslashes ('/' conversion).
    """
    posix_path = Path(path).as_posix()
    # FFmpeg interprets colons as filter option separators, so escape drive colons
    escaped = posix_path.replace(":", r"\:")
    return escaped


def normalize_color_spec(color: str) -> str:
    """Normalize hex colors (#RRGGBB or #RGB) into FFmpeg 0xRRGGBB format or keep color name."""
    clean = color.strip()
    if clean.startswith("#"):
        hex_val = clean.lstrip("#")
        if len(hex_val) == 3:
            hex_val = "".join(c * 2 for c in hex_val)
        return f"0x{hex_val}"
    return clean.lower()


def build_color_source(
    color: str,
    width: int,
    height: int,
    duration: float,
    fps: int = 30,
) -> List[str]:
    """Build FFmpeg input arguments generating a synthetic solid color canvas.

    Args:
        color: Hex string (e.g. '#1e1e2e') or named color ('black', 'white').
        width: Canvas width in pixels.
        height: Canvas height in pixels.
        duration: Duration in seconds.
        fps: Frames per second.

    Returns:
        List of command-line arguments for FFmpeg input.
    """
    color_spec = normalize_color_spec(color)
    dur = max(0.1, duration)
    return [
        "-f", "lavfi",
        "-i", f"color=c={color_spec}:s={width}x{height}:r={fps}:d={dur:.3f}",
    ]


def build_scale_and_pad(
    target_width: int,
    target_height: int,
    fit_mode: str = "contain",
    bg_color: str = "black",
) -> str:
    """Build video filter chain scaling and positioning visual media onto target canvas.

    Args:
        target_width: Desired canvas width.
        target_height: Desired canvas height.
        fit_mode: 'contain' (letterbox/pillarbox), 'cover' (crop to fill), or 'stretch'.
        bg_color: Background padding color.

    Returns:
        FFmpeg filter string.
    """
    clean_mode = fit_mode.strip().lower()
    color_spec = normalize_color_spec(bg_color)

    if clean_mode == "cover":
        return (
            f"scale={target_width}:{target_height}:force_original_aspect_ratio=increase,"
            f"crop={target_width}:{target_height},"
            f"setsar=1"
        )
    elif clean_mode == "stretch":
        return f"scale={target_width}:{target_height},setsar=1"
    else:
        # Default: contain
        return (
            f"scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,"
            f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2:color={color_spec},"
            f"setsar=1"
        )


def build_drawtext_filter(
    text_file_path: Union[str, Path],
    font_size: int = 42,
    font_color: str = "white",
    x: str = "(w-text_w)/2",
    y: str = "h-text_h-60",
    box: bool = True,
    box_color: str = "black@0.6",
    box_borderw: int = 8,
) -> str:
    """Build safe drawtext filter referencing text from an external file to prevent injection.

    Args:
        text_file_path: Path to local utf-8 text file containing the text to render.
        font_size: Font size in pixels.
        font_color: Text color name or hex.
        x: Horizontal position expression.
        y: Vertical position expression.
        box: Whether to draw a background box for legibility.
        box_color: Box color with alpha (e.g. 'black@0.6').
        box_borderw: Box padding border width.

    Returns:
        FFmpeg drawtext filter string.
    """
    escaped_path = escape_filter_path(text_file_path)
    color_spec = normalize_color_spec(font_color)
    box_flag = "1" if box else "0"

    return (
        f"drawtext=textfile='{escaped_path}':"
        f"fontsize={font_size}:"
        f"fontcolor={color_spec}:"
        f"x={x}:y={y}:"
        f"box={box_flag}:boxcolor={box_color}:boxborderw={box_borderw}"
    )


def build_audio_volume(volume_factor: float) -> str:
    """Build FFmpeg audio volume adjustment filter.

    Args:
        volume_factor: Multiplier (1.0 = 100%, 0.5 = 50%, 0.0 = mute).
    """
    clamped = max(0.0, min(float(volume_factor), 5.0))
    return f"volume={clamped:.2f}"


def build_audio_amix(
    inputs_count: int,
    duration_mode: str = "first",
    dropout_transition: float = 2.0,
) -> str:
    """Build FFmpeg audio amix filter for blending voiceover and background music tracks.

    Args:
        inputs_count: Number of input audio streams.
        duration_mode: 'first' (match first input duration), 'longest', or 'shortest'.
        dropout_transition: Transition time in seconds.
    """
    return f"amix=inputs={inputs_count}:duration={duration_mode}:dropout_transition={dropout_transition:.1f}"


def build_circular_mask_filter(diameter: int) -> str:
    """Build filter string transforming an input video stream into a circular PIP bubble with alpha."""
    dim = max(64, int(diameter))
    return (
        f"scale={dim}:{dim}:force_original_aspect_ratio=increase,"
        f"crop={dim}:{dim},"
        f"format=yuva420p,"
        f"geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':"
        f"a='if(lte(pow(X-W/2,2)+pow(Y-H/2,2),pow(min(W,H)/2,2)),255,0)'"
    )


def build_alphamerge_filter(
    video_label: str,
    matte_label: str,
    out_label: str = "avatar_rgba",
) -> str:
    """Build FFmpeg filter merging a color video stream and greyscale alpha matte video stream into an RGBA stream."""
    v = video_label.strip("[]")
    m = matte_label.strip("[]")
    o = out_label.strip("[]")
    return f"[{v}][{m}]alphamerge[{o}]"


def build_overlay_filter(
    base_label: str,
    overlay_label: str,
    x: Union[int, str] = 0,
    y: Union[int, str] = 0,
    out_label: str = "comp",
) -> str:
    """Build FFmpeg overlay filter positioning an RGBA overlay stream onto a base video stream."""
    b = base_label.strip("[]")
    ov = overlay_label.strip("[]")
    o = out_label.strip("[]")
    return f"[{b}][{ov}]overlay=x={x}:y={y}[{o}]"


def map_transition_to_xfade(transition_type: Optional[str]) -> Optional[str]:
    """Map canonical repository transition type to FFmpeg xfade transition name.

    Only maps repository-supported types:
    - 'fade' -> 'fade'
    - 'dissolve' -> 'dissolve'
    - 'wipe' / 'wipe_left' -> 'wipeleft'
    - 'slide' / 'slide_left' -> 'slideleft'

    Returns None for hard cuts ('none', None, or unrecognized).
    """
    if not transition_type:
        return None
    t = transition_type.strip().lower()
    if t in ("fade", "fadeblack", "fadewhite"):
        return "fade"
    if t in ("dissolve", "crossfade"):
        return "dissolve"
    if t in ("wipe", "wipe_left", "wipeleft"):
        return "wipeleft"
    if t in ("slide", "slide_left", "slideleft"):
        return "slideleft"
    return None

