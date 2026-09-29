"""Studio Elements, Shapes, and Stickers rasterizer for video composition.

Generates deterministic, high-quality, anti-aliased RGBA PNG overlays for
primitives (Rectangle, Rounded Rectangle, Circle, Ellipse, Line, Arrow)
and built-in stickers (Star, Heart, Fire, Sparkles, Rocket, Thumbs Up, Checkmark, Warning, Trophy, Discount)
using Pillow supersampling.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from PIL import Image, ImageColor, ImageDraw


def parse_color(color_val: Any, opacity: float = 1.0) -> Tuple[int, int, int, int]:
    """Parse color string or tuple into RGBA tuple with opacity factored in."""
    if not color_val:
        return (0, 0, 0, 0)
    
    if isinstance(color_val, (tuple, list)):
        r = int(color_val[0])
        g = int(color_val[1])
        b = int(color_val[2])
        a = int(color_val[3]) if len(color_val) > 3 else 255
    else:
        color_str = str(color_val).strip()
        if color_str.lower() in ("transparent", "none", ""):
            return (0, 0, 0, 0)
        try:
            rgba = ImageColor.getcolor(color_str, "RGBA")
            r, g, b, a = rgba
        except Exception:
            # Fallback default
            r, g, b, a = 255, 255, 255, 255
            
    final_alpha = max(0, min(255, int(round(a * max(0.0, min(1.0, opacity))))))
    return (r, g, b, final_alpha)


def render_shape_to_image(
    shape_type: str,
    width: int,
    height: int,
    fill: Any = "#3B82F6",
    border_color: Any = "#FFFFFF",
    border_width: int = 0,
    border_radius: int = 0,
    opacity: float = 1.0,
    output_path: Optional[Path] = None,
) -> Image.Image:
    """Render a vector shape to an anti-aliased RGBA Pillow Image.
    
    Uses 2x supersampling to ensure crisp anti-aliased edges and curves.
    """
    w = max(4, int(width))
    h = max(4, int(height))
    scale = 2
    sw = w * scale
    sh = h * scale
    
    img = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    fill_rgba = parse_color(fill, opacity=opacity)
    border_rgba = parse_color(border_color, opacity=opacity) if border_width > 0 else (0, 0, 0, 0)
    bw = int(round(border_width * scale))
    
    # Inset drawing coordinates so borders don't clip at outer boundaries
    pad = bw // 2 if bw > 0 else 0
    x0, y0 = pad, pad
    x1, y1 = sw - 1 - pad, sh - 1 - pad
    
    st = str(shape_type).lower().replace("-", "_").strip()
    
    if st in ("rounded_rectangle", "rounded_rect", "rounded_box") or (st == "rectangle" and border_radius > 0):
        radius = int(round((border_radius if border_radius > 0 else min(w, h) * 0.15) * scale))
        draw.rounded_rectangle(
            [x0, y0, x1, y1],
            radius=radius,
            fill=fill_rgba if fill_rgba[3] > 0 else None,
            outline=border_rgba if bw > 0 and border_rgba[3] > 0 else None,
            width=bw if bw > 0 else 1,
        )
        
    elif st in ("circle", "ellipse"):
        if st == "circle":
            dim = min(x1 - x0, y1 - y0)
            cx = (x0 + x1) / 2
            cy = (y0 + y1) / 2
            x0, y0 = cx - dim / 2, cy - dim / 2
            x1, y1 = cx + dim / 2, cy + dim / 2
        draw.ellipse(
            [x0, y0, x1, y1],
            fill=fill_rgba if fill_rgba[3] > 0 else None,
            outline=border_rgba if bw > 0 and border_rgba[3] > 0 else None,
            width=bw if bw > 0 else 1,
        )
        
    elif st in ("line", "horizontal_line"):
        line_color = fill_rgba if fill_rgba[3] > 0 else border_rgba
        if line_color[3] == 0:
            line_color = (255, 255, 255, int(255 * opacity))
        lw = max(2, bw if bw > 0 else int(round(4 * scale)))
        cy = sh / 2
        draw.line([(0, cy), (sw, cy)], fill=line_color, width=lw)
        
    elif st in ("arrow", "right_arrow"):
        arrow_color = fill_rgba if fill_rgba[3] > 0 else border_rgba
        if arrow_color[3] == 0:
            arrow_color = (255, 255, 255, int(255 * opacity))
        # Draw a horizontal arrow pointing right: shaft + head
        head_w = int(sw * 0.35)
        shaft_h = max(2, int(sh * 0.28))
        shaft_y0 = (sh - shaft_h) // 2
        shaft_y1 = shaft_y0 + shaft_h
        shaft_x1 = sw - head_w
        
        # Shaft
        draw.rectangle([x0, shaft_y0, shaft_x1, shaft_y1], fill=arrow_color)
        # Arrowhead triangle
        head_poly = [
            (shaft_x1, 0),
            (sw - 1, sh / 2),
            (shaft_x1, sh - 1),
        ]
        draw.polygon(head_poly, fill=arrow_color)
        if bw > 0 and border_rgba[3] > 0:
            draw.polygon(head_poly, outline=border_rgba)
            
    else:
        # Default: Rectangle
        draw.rectangle(
            [x0, y0, x1, y1],
            fill=fill_rgba if fill_rgba[3] > 0 else None,
            outline=border_rgba if bw > 0 and border_rgba[3] > 0 else None,
            width=bw if bw > 0 else 1,
        )
        
    # Lanczos downsampling from 2x supersampling for anti-aliasing
    final_img = img.resize((w, h), resample=Image.Resampling.LANCZOS)
    
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        final_img.save(str(output_path), "PNG")
        
    return final_img


def render_sticker_to_image(
    sticker_id: str,
    width: int,
    height: int,
    fill_color: Any = None,
    opacity: float = 1.0,
    output_path: Optional[Path] = None,
) -> Image.Image:
    """Render a built-in vector sticker graphic to an anti-aliased RGBA Pillow Image."""
    w = max(16, int(width))
    h = max(16, int(height))
    scale = 2
    sw = w * scale
    sh = h * scale
    
    img = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    sid = str(sticker_id).lower().replace("-", "_").strip()
    
    # Coordinates helper
    cx, cy = sw / 2, sh / 2
    r = min(sw, sh) * 0.44
    
    if sid in ("star", "gold_star"):
        color = parse_color(fill_color or "#FBBF24", opacity)
        outline = parse_color("#F59E0B", opacity)
        # 5-pointed star
        points = []
        for i in range(10):
            ang = math.pi / 2 + i * (2 * math.pi / 10)
            curr_r = r if i % 2 == 0 else r * 0.45
            px = cx + curr_r * math.cos(ang)
            py = cy - curr_r * math.sin(ang)
            points.append((px, py))
        draw.polygon(points, fill=color, outline=outline)
        
    elif sid in ("heart", "love"):
        color = parse_color(fill_color or "#EF4444", opacity)
        outline = parse_color("#DC2626", opacity)
        # Symmetrical heart polygon
        heart_pts = []
        steps = 40
        for i in range(steps):
            t = (i / steps) * 2 * math.pi
            # parametric heart equation
            x = 16 * (math.sin(t) ** 3)
            y = -(13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
            px = cx + (x / 18.0) * r
            py = cy + (y / 18.0) * r
            heart_pts.append((px, py))
        draw.polygon(heart_pts, fill=color, outline=outline)
        
    elif sid in ("fire", "flame"):
        color = parse_color(fill_color or "#F97316", opacity)
        # Stylized flame polygon
        flame_outer = [
            (cx, cy - r),
            (cx + r * 0.6, cy - r * 0.3),
            (cx + r * 0.7, cy + r * 0.4),
            (cx + r * 0.4, cy + r * 0.9),
            (cx, cy + r),
            (cx - r * 0.4, cy + r * 0.9),
            (cx - r * 0.7, cy + r * 0.4),
            (cx - r * 0.6, cy - r * 0.3),
        ]
        draw.polygon(flame_outer, fill=color)
        # Inner yellow core
        inner_color = parse_color("#FDE047", opacity)
        flame_inner = [
            (cx, cy - r * 0.2),
            (cx + r * 0.35, cy + r * 0.3),
            (cx + r * 0.2, cy + r * 0.75),
            (cx, cy + r * 0.85),
            (cx - r * 0.2, cy + r * 0.75),
            (cx - r * 0.35, cy + r * 0.3),
        ]
        draw.polygon(flame_inner, fill=inner_color)
        
    elif sid in ("sparkles", "sparkle"):
        color = parse_color(fill_color or "#A855F7", opacity)
        # Main center 4-point sparkle
        pts = []
        for i in range(8):
            ang = i * (2 * math.pi / 8)
            curr_r = r * 0.85 if i % 2 == 0 else r * 0.22
            points_x = cx + curr_r * math.cos(ang)
            points_y = cy - curr_r * math.sin(ang)
            pts.append((points_x, points_y))
        draw.polygon(pts, fill=color)
        
        # Secondary small sparkle top right
        sub_cx, sub_cy = cx + r * 0.55, cy - r * 0.55
        sub_r = r * 0.35
        sub_pts = []
        for i in range(8):
            ang = i * (2 * math.pi / 8)
            curr_r = sub_r if i % 2 == 0 else sub_r * 0.25
            points_x = sub_cx + curr_r * math.cos(ang)
            points_y = sub_cy - curr_r * math.sin(ang)
            sub_pts.append((points_x, points_y))
        draw.polygon(sub_pts, fill=parse_color("#EC4899", opacity))
        
    elif sid in ("checkmark", "check"):
        # Circle badge
        bg_col = parse_color(fill_color or "#10B981", opacity)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=bg_col)
        # White checkmark lines
        chk_col = parse_color("#FFFFFF", opacity)
        lw = max(4, int(r * 0.22))
        p1 = (cx - r * 0.45, cy + r * 0.05)
        p2 = (cx - r * 0.1, cy + r * 0.45)
        p3 = (cx + r * 0.5, cy - r * 0.35)
        draw.line([p1, p2, p3], fill=chk_col, width=lw, joint="curve")
        
    elif sid in ("warning", "alert"):
        # Yellow caution triangle
        bg_col = parse_color(fill_color or "#EAB308", opacity)
        pts = [
            (cx, cy - r),
            (cx + r * 1.1, cy + r * 0.9),
            (cx - r * 1.1, cy + r * 0.9),
        ]
        draw.polygon(pts, fill=bg_col, outline=parse_color("#CA8A04", opacity))
        # Exclamation mark
        ex_col = parse_color("#000000", opacity)
        lw = max(4, int(r * 0.18))
        draw.line([(cx, cy - r * 0.35), (cx, cy + r * 0.25)], fill=ex_col, width=lw)
        draw.ellipse([cx - lw // 2, cy + r * 0.5, cx + lw // 2, cy + r * 0.5 + lw], fill=ex_col)
        
    elif sid in ("trophy", "cup"):
        gold = parse_color(fill_color or "#F59E0B", opacity)
        dark_gold = parse_color("#D97706", opacity)
        # Cup body
        draw.polygon([
            (cx - r * 0.6, cy - r * 0.6),
            (cx + r * 0.6, cy - r * 0.6),
            (cx + r * 0.45, cy + r * 0.1),
            (cx - r * 0.45, cy + r * 0.1),
        ], fill=gold, outline=dark_gold)
        # Stem and base
        draw.rectangle([cx - r * 0.15, cy + r * 0.1, cx + r * 0.15, cy + r * 0.55], fill=gold)
        draw.rectangle([cx - r * 0.5, cy + r * 0.55, cx + r * 0.5, cy + r * 0.85], fill=dark_gold)
        
    elif sid in ("discount", "sale", "badge"):
        badge_col = parse_color(fill_color or "#EF4444", opacity)
        # 12-pointed starburst badge
        points = []
        for i in range(24):
            ang = i * (2 * math.pi / 24)
            curr_r = r if i % 2 == 0 else r * 0.82
            px = cx + curr_r * math.cos(ang)
            py = cy - curr_r * math.sin(ang)
            points.append((px, py))
        draw.polygon(points, fill=badge_col, outline=parse_color("#B91C1C", opacity))
        # Center white text or star
        draw.ellipse([cx - r * 0.35, cy - r * 0.35, cx + r * 0.35, cy + r * 0.35], fill=parse_color("#FFFFFF", opacity))
        
    elif sid in ("thumbs_up", "like"):
        thumb_col = parse_color(fill_color or "#3B82F6", opacity)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=thumb_col)
        # Simple like icon outline in white
        white = parse_color("#FFFFFF", opacity)
        lw = max(3, int(r * 0.16))
        draw.line([(cx - r * 0.2, cy - r * 0.4), (cx - r * 0.2, cy + r * 0.3)], fill=white, width=lw)
        draw.line([(cx - r * 0.2, cy + r * 0.3), (cx + r * 0.4, cy + r * 0.3)], fill=white, width=lw)
        draw.line([(cx + r * 0.4, cy + r * 0.3), (cx + r * 0.35, cy - r * 0.1)], fill=white, width=lw)
        draw.line([(cx + r * 0.35, cy - r * 0.1), (cx - r * 0.2, cy - r * 0.1)], fill=white, width=lw)
        
    elif sid in ("rocket", "launch"):
        rocket_col = parse_color(fill_color or "#EC4899", opacity)
        # Rocket body pointing up-right
        body = [
            (cx + r * 0.6, cy - r * 0.6),
            (cx + r * 0.4, cy + r * 0.1),
            (cx - r * 0.1, cy + r * 0.4),
            (cx - r * 0.5, cy + r * 0.5),
            (cx - r * 0.4, cy + r * 0.1),
            (cx - r * 0.1, cy - r * 0.4),
        ]
        draw.polygon(body, fill=rocket_col, outline=parse_color("#BE185D", opacity))
        # Window
        draw.ellipse([cx, cy - r * 0.2, cx + r * 0.3, cy + r * 0.1], fill=parse_color("#60A5FA", opacity))
        
    else:
        # Default: colorful star
        color = parse_color(fill_color or "#3B82F6", opacity)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)
        
    final_img = img.resize((w, h), resample=Image.Resampling.LANCZOS)
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        final_img.save(str(output_path), "PNG")
        
    return final_img
