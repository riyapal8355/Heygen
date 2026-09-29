"""Studio Text and Caption rasterizer for video composition (Phase 42C-1).

Generates deterministic, high-quality, anti-aliased RGBA PNG overlays for
text layers and subtitle/caption cues using Pillow with 2x supersampling.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from PIL import Image, ImageColor, ImageDraw, ImageFont

from app.media.shapes import parse_color


def resolve_font(
    font_family: str = "Arial",
    font_size: int = 32,
    is_bold: bool = False,
    is_italic: bool = False,
) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Resolve a TrueType/OpenType font with system search and robust fallbacks."""
    fam = (font_family or "Arial").strip().lower()
    
    # Candidate filenames based on font family and style
    candidates: List[str] = []
    if "arial" in fam:
        if is_bold and is_italic:
            candidates.extend(["arialbi.ttf", "Arial-BoldItalic.ttf"])
        elif is_bold:
            candidates.extend(["arialbd.ttf", "Arial-Bold.ttf"])
        elif is_italic:
            candidates.extend(["ariali.ttf", "Arial-Italic.ttf"])
        candidates.extend(["arial.ttf", "Arial.ttf"])
    elif "times" in fam:
        if is_bold:
            candidates.extend(["timesbd.ttf", "Times-Bold.ttf"])
        candidates.extend(["times.ttf", "Times-New-Roman.ttf"])
    elif "courier" in fam:
        if is_bold:
            candidates.extend(["courbd.ttf", "Courier-Bold.ttf"])
        candidates.extend(["cour.ttf", "Courier.ttf"])
    elif "calibri" in fam:
        if is_bold:
            candidates.extend(["calibrib.ttf", "Calibri-Bold.ttf"])
        candidates.extend(["calibri.ttf", "Calibri.ttf"])
    elif "segoe" in fam:
        if is_bold:
            candidates.extend(["segoeuib.ttf", "SegoeUI-Bold.ttf"])
        candidates.extend(["segoeui.ttf", "SegoeUI.ttf"])
    elif "helvetica" in fam:
        if is_bold:
            candidates.extend(["Helvetica-Bold.ttf", "arialbd.ttf"])
        candidates.extend(["Helvetica.ttf", "arial.ttf"])
    else:
        # Generic family name
        base_name = fam.replace(" ", "")
        if is_bold:
            candidates.extend([f"{base_name}bd.ttf", f"{fam}-Bold.ttf", f"{base_name}-Bold.ttf"])
        candidates.extend([f"{base_name}.ttf", f"{fam}.ttf", f"{base_name}.otf"])

    # Fallback candidates
    if is_bold:
        candidates.extend(["arialbd.ttf", "calibrib.ttf", "segoeuib.ttf"])
    candidates.extend(["arial.ttf", "calibri.ttf", "segoeui.ttf", "DejaVuSans.ttf"])

    # Search paths: system fonts
    search_dirs: List[Path] = []
    windir = os.environ.get("WINDIR", "C:\\Windows")
    search_dirs.append(Path(windir) / "Fonts")
    search_dirs.append(Path("/usr/share/fonts"))
    search_dirs.append(Path("/usr/local/share/fonts"))

    for cand in candidates:
        # Try direct resolution first
        try:
            return ImageFont.truetype(cand, font_size)
        except Exception:
            pass
        # Try system font directories
        for sdir in search_dirs:
            p = sdir / cand
            if p.exists():
                try:
                    return ImageFont.truetype(str(p), font_size)
                except Exception:
                    pass

    try:
        return ImageFont.load_default()
    except Exception:
        return ImageFont.load_default()


def render_text_layer_to_image(
    text: str,
    font_family: str = "Arial",
    font_size: int = 48,
    font_weight: str = "bold",
    font_style: str = "normal",
    color: str = "#FFFFFF",
    opacity: float = 1.0,
    background_color: str = "#000000",
    background_opacity: float = 0.0,
    alignment: str = "center",
    scale: float = 1.0,
    canvas_width: int = 1920,
    canvas_height: int = 1080,
    output_path: Optional[Path] = None,
) -> Image.Image:
    """Render a visual text layer to a transparent RGBA image with 2x supersampling.
    
    Matches frontend Studio typography and styling exactly.
    """
    clean_text = str(text or "").strip().replace("\\N", "\n")
    if not clean_text:
        # Return minimal 4x4 transparent image
        img = Image.new("RGBA", (4, 4), (0, 0, 0, 0))
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            img.save(output_path, format="PNG")
        return img

    layer_opacity = max(0.0, min(1.0, float(opacity)))
    is_bold = str(font_weight).lower() in ("bold", "700", "800", "900")
    is_italic = str(font_style).lower() in ("italic", "oblique")

    effective_font_size = max(8, int(round(float(font_size) * max(0.05, float(scale)))))
    supersample = 2
    render_font_size = effective_font_size * supersample

    font = resolve_font(
        font_family=font_family,
        font_size=render_font_size,
        is_bold=is_bold,
        is_italic=is_italic,
    )

    # Split lines and compute layout metrics
    raw_lines = clean_text.splitlines() or [""]
    
    # Calculate line dimensions using textbbox
    dummy_img = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
    dummy_draw = ImageDraw.Draw(dummy_img)

    line_metrics: List[Tuple[str, int, int]] = []
    max_line_w = 0
    total_text_h = 0
    line_spacing = max(4, int(render_font_size * 0.25))

    for line in raw_lines:
        line_str = line if line else " "
        try:
            bbox = dummy_draw.textbbox((0, 0), line_str, font=font)
            lw = max(1, bbox[2] - bbox[0])
            lh = max(1, bbox[3] - bbox[1])
        except Exception:
            lw = int(len(line_str) * render_font_size * 0.6)
            lh = render_font_size
        max_line_w = max(max_line_w, lw)
        line_metrics.append((line, lw, lh))

    for idx, (_, _, lh) in enumerate(line_metrics):
        total_text_h += lh
        if idx < len(line_metrics) - 1:
            total_text_h += line_spacing

    # Background padding (matching canvas px-3.5 py-1.5 scaled)
    has_bg = background_opacity > 0.01
    pad_x = int(round(render_font_size * 0.4)) if has_bg else int(round(render_font_size * 0.1))
    pad_y = int(round(render_font_size * 0.25)) if has_bg else int(round(render_font_size * 0.1))

    box_w = max_line_w + (pad_x * 2)
    box_h = total_text_h + (pad_y * 2)

    # Render image canvas at supersampled resolution
    img = Image.new("RGBA", (box_w, box_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Draw background box if enabled
    if has_bg:
        bg_rgba = parse_color(background_color, opacity=background_opacity * layer_opacity)
        if bg_rgba[3] > 0:
            border_radius = max(2, int(round(render_font_size * 0.25)))
            draw.rounded_rectangle(
                [0, 0, box_w - 1, box_h - 1],
                radius=border_radius,
                fill=bg_rgba,
            )

    # Draw text lines
    text_rgba = parse_color(color, opacity=layer_opacity)
    align_mode = str(alignment).lower().strip()

    cur_y = pad_y
    for line, lw, lh in line_metrics:
        if align_mode == "left":
            cur_x = pad_x
        elif align_mode == "right":
            cur_x = box_w - pad_x - lw
        else:  # center
            cur_x = pad_x + (max_line_w - lw) // 2

        if line.strip():
            draw.text((cur_x, cur_y), line, font=font, fill=text_rgba)
        cur_y += lh + line_spacing

    # Downsample by 2x for smooth anti-aliased output
    target_w = max(4, (box_w // supersample // 2) * 2)
    target_h = max(4, (box_h // supersample // 2) * 2)
    final_img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        final_img.save(output_path, format="PNG")

    return final_img


def render_caption_cue_to_image(
    cue_text: str,
    font_family: str = "Arial",
    font_size: int = 48,
    font_weight: str = "bold",
    color: str = "#FFFFFF",
    background_color: str = "#000000",
    background_opacity: float = 0.6,
    alignment: str = "center",
    scale: float = 1.0,
    canvas_width: int = 1920,
    canvas_height: int = 1080,
    output_path: Optional[Path] = None,
) -> Image.Image:
    """Render a subtitle caption cue to a transparent RGBA image.
    
    Reproduces the exact styling from CaptionStyle and canvas active cue display.
    """
    return render_text_layer_to_image(
        text=cue_text,
        font_family=font_family,
        font_size=font_size,
        font_weight=font_weight,
        color=color,
        opacity=1.0,
        background_color=background_color,
        background_opacity=background_opacity,
        alignment=alignment,
        scale=scale,
        canvas_width=canvas_width,
        canvas_height=canvas_height,
        output_path=output_path,
    )
