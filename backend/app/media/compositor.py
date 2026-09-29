"""Timeline Compositor orchestrating real multi-scene video rendering.

Transforms structured ProjectDocumentV1 timelines into broadcast-quality MP4 videos,
synthesizing visual backgrounds, audio tracks, text overlays, and transitions.
"""

import asyncio
import math
import os
import re
import shutil
import uuid
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional, Union

import cv2
import numpy as np

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.media.errors import (
    FFmpegFailedError,
    MediaProcessingError,
    RenderInputMissingError,
    RenderOutputInvalidError,
)
from app.core.config import get_settings
from app.media.ffmpeg import FFmpegService
from app.media.ffprobe import FFprobeService
from app.media.filters import (
    build_alphamerge_filter,
    build_audio_amix,
    build_audio_volume,
    build_circular_mask_filter,
    build_color_source,
    build_drawtext_filter,
    build_overlay_filter,
    build_scale_and_pad,
    map_transition_to_xfade,
)
from app.media.models import CanvasProfile, MediaProbeResult, RenderResult
from app.media.shapes import render_shape_to_image, render_sticker_to_image
from app.media.text_rasterizer import render_caption_cue_to_image, render_text_layer_to_image
from app.media.workspace import MediaWorkspace
from app.schemas.project_document import CaptionSettings, ProjectDocumentV1, Scene, SceneLayer

logger = get_logger(__name__)


class TimelineCompositor:
    """Orchestrates scene rendering, visual compositing, and audio assembly into MP4."""

    def __init__(
        self,
        ffmpeg_service: Optional[FFmpegService] = None,
        ffprobe_service: Optional[FFprobeService] = None,
    ) -> None:
        self.ffmpeg_service = ffmpeg_service or FFmpegService()
        self.ffprobe_service = ffprobe_service or FFprobeService()

    async def render_project(
        self,
        document: Union[ProjectDocumentV1, Dict[str, Any]],
        workspace_id: Union[str, uuid.UUID],
        db: AsyncSession,
        media_workspace: Optional[MediaWorkspace] = None,
        progress_callback: Optional[Callable[[int, str, Optional[Dict[str, Any]]], Awaitable[None]]] = None,
        cancellation_checker: Optional[Callable[[], Awaitable[bool]]] = None,
    ) -> RenderResult:
        """Render a ProjectDocumentV1 into a fully composited MP4 video and PNG thumbnail.

        Args:
            document: Project document instance or dict payload.
            workspace_id: UUID of the owning workspace (for isolated asset access).
            db: Active async database session.
            media_workspace: Optional existing MediaWorkspace scratch container.
            progress_callback: Async callback reporting (progress_percent, stage, details).
            cancellation_checker: Async callable returning True if the job has been cancelled.

        Returns:
            RenderResult containing output paths and probe metrics.

        Raises:
            asyncio.CancelledError: If cancellation is signaled.
            RenderInputMissingError: If required assets cannot be found or accessed.
            RenderOutputInvalidError: If rendered video fails strict stream/container validation.
            MediaProcessingError: If rendering fails unexpectedly.
        """
        # Parse canonical document
        if isinstance(document, dict):
            doc = ProjectDocumentV1.model_validate(document)
        else:
            doc = document

        # Check cancellation
        if cancellation_checker and await cancellation_checker():
            raise asyncio.CancelledError("Render job was cancelled before execution started.")

        # Determine canvas profile
        settings = doc.settings
        aspect_ratio = settings.aspect_ratio or "16:9"
        canvas = CanvasProfile(
            width=settings.width if settings.width and settings.width >= 128 else 1920,
            height=settings.height if settings.height and settings.height >= 128 else 1080,
            aspect_ratio=aspect_ratio,
            fps=settings.fps if settings.fps and settings.fps >= 15 else 30,
        )

        owns_workspace = False
        mws = media_workspace
        if mws is None:
            mws = MediaWorkspace(prefix="heyzen_composite_")
            owns_workspace = True

        try:
            # 1. Preparing scenes
            scenes = doc.scenes or []
            if not scenes:
                # Default 5s scene if none present
                scenes = [
                    Scene(
                        id="default_scene",
                        sequence=1,
                        duration=5.0,
                        background={"type": "color", "value": "#0F172A"},
                    )
                ]

            total_scenes = len(scenes)
            if progress_callback:
                await progress_callback(
                    15,
                    "preparing_assets",
                    {"total_scenes": total_scenes, "canvas": f"{canvas.width}x{canvas.height}"},
                )

            scene_clips: List[Path] = []

            # 2. Render each scene clip
            for idx, scene in enumerate(scenes):
                if cancellation_checker and await cancellation_checker():
                    raise asyncio.CancelledError(f"Render job cancelled at scene {idx + 1}/{total_scenes}")

                caption_settings = getattr(doc.settings, "captions", None)
                scene_clip = await self._render_scene_clip(
                    scene=scene,
                    scene_index=idx,
                    canvas=canvas,
                    workspace_id=workspace_id,
                    db=db,
                    mws=mws,
                    caption_settings=caption_settings,
                )
                scene_clips.append(scene_clip)

                if progress_callback:
                    pct = 20 + int(((idx + 1) / total_scenes) * 50)
                    await progress_callback(
                        pct,
                        "rendering_scenes",
                        {"completed_scene": idx + 1, "total_scenes": total_scenes},
                    )

            # Check cancellation
            if cancellation_checker and await cancellation_checker():
                raise asyncio.CancelledError("Render job cancelled after scene rendering")

            # 3. Concatenate scene clips
            if progress_callback:
                await progress_callback(75, "assembling", {"total_scenes": total_scenes})

            assembly_path = mws.output_dir / "assembly.mp4"
            if len(scene_clips) == 1:
                shutil.copy2(scene_clips[0], assembly_path)
            else:
                await self._concatenate_scene_clips(
                    scene_clips=scene_clips,
                    scenes=doc.scenes,
                    output_path=assembly_path,
                    mws=mws,
                    fps=canvas.fps,
                )

            # Check cancellation
            if cancellation_checker and await cancellation_checker():
                raise asyncio.CancelledError("Render job cancelled before audio mixing")

            # 4. Mix background audio if configured
            final_video_path = mws.output_dir / "render.mp4"
            await self._mix_background_audio(
                assembly_path=assembly_path,
                audio_tracks=doc.audio_tracks,
                output_path=final_video_path,
                workspace_id=workspace_id,
                db=db,
                mws=mws,
            )

            # 5. Validate final output with FFprobe
            if progress_callback:
                await progress_callback(90, "validating_output", {"output_file": final_video_path.name})

            probe_result = await self.ffprobe_service.validate_render_output(
                final_video_path,
                min_duration=0.1,
                require_video=True,
                require_audio=True,
            )

            # 6. Extract thumbnail image
            thumbnail_path = mws.output_dir / "thumbnail.png"
            thumb_time = min(1.0, max(0.0, probe_result.duration_seconds / 2.0))
            await self.ffmpeg_service.extract_thumbnail(
                video_path=final_video_path,
                output_png=thumbnail_path,
                timestamp=thumb_time,
            )

            if not thumbnail_path.exists() or thumbnail_path.stat().st_size < 100:
                raise RenderOutputInvalidError("Failed to extract valid thumbnail image from rendered video")

            return RenderResult(
                video_path=final_video_path,
                thumbnail_path=thumbnail_path,
                probe_result=probe_result,
                canvas_profile=canvas,
                total_duration=probe_result.duration_seconds,
                scenes_count=total_scenes,
                scene_clips=scene_clips,
            )

        finally:
            if owns_workspace and mws:
                mws.cleanup()

    @staticmethod
    def _hex_to_ass(hex_str: str, alpha: float = 0.0) -> str:
        """Convert hex color (#RRGGBB) and alpha (0.0=opaque, 1.0=transparent) to ASS &HAABBGGRR."""
        clean = (hex_str or "").strip().lstrip("#")
        if len(clean) == 3:
            clean = "".join(c * 2 for c in clean)
        if len(clean) != 6:
            clean = "FFFFFF"
        r, g, b = clean[0:2], clean[2:4], clean[4:6]
        aa = int(max(0.0, min(1.0, alpha)) * 255)
        return f"&H{aa:02X}{b}{g}{r}".upper()

    @staticmethod
    def _format_time(sec: float) -> str:
        """Format seconds into ASS H:MM:SS.cs timestamp string."""
        cs_total = int(round(max(0.0, float(sec)) * 100))
        cs = cs_total % 100
        s_total = cs_total // 100
        s = s_total % 60
        m_total = s_total // 60
        m = m_total % 60
        h = m_total // 60
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

    def _generate_gradient_background(
        self,
        bg: Dict[str, Any],
        canvas: CanvasProfile,
        output_path: Path,
        scene_index: int = 0,
        av_x: float = 0.5,
    ) -> Path:
        """Render a deterministic luxury studio gradient canvas with radial key lighting, vignette, and micro-dither."""
        def hex_to_rgb(h: str) -> np.ndarray:
            clean = str(h or "").strip().lstrip("#")
            if len(clean) == 3:
                clean = "".join(c * 2 for c in clean)
            if len(clean) != 6:
                clean = "0F172A"
            return np.array([int(clean[i : i + 2], 16) for i in (0, 2, 4)], dtype=np.float32)

        start_hex = bg.get("gradient_start") or bg.get("color") or "#0B0F19"
        end_hex = bg.get("gradient_end") or "#1E293B"

        grad_preset = str(bg.get("gradient") or bg.get("value") or "").lower()
        grad_colors = bg.get("gradient_colors") or []
        if len(grad_colors) >= 2:
            start_hex, end_hex = grad_colors[0], grad_colors[1]
        elif bg.get("gradient_start") and bg.get("gradient_end"):
            start_hex, end_hex = bg.get("gradient_start"), bg.get("gradient_end")
        elif "#" in grad_preset:
            hexes = re.findall(r"#[0-9a-fA-F]{6}", grad_preset)
            if len(hexes) >= 2:
                start_hex, end_hex = hexes[0], hexes[1]
            elif len(hexes) == 1:
                start_hex = hexes[0]
        elif "purple" in grad_preset:
            start_hex, end_hex = "#311042", "#6366F1"
        elif "emerald" in grad_preset or "green" in grad_preset:
            start_hex, end_hex = "#064E3B", "#0D9488"
        elif "amber" in grad_preset or "warm" in grad_preset:
            start_hex, end_hex = "#451A03", "#D97706"
        elif "indigo" in grad_preset or "blue" in grad_preset:
            start_hex, end_hex = "#0B192C", "#1E3A8A"

        c_start = hex_to_rgb(start_hex)
        c_end = hex_to_rgb(end_hex)

        w, h = canvas.width, canvas.height
        u = np.linspace(0.0, 1.0, w, dtype=np.float32)
        v = np.linspace(0.0, 1.0, h, dtype=np.float32)
        xx, yy = np.meshgrid(u, v)

        # 1. Base directional background gradient
        weight = (xx * 0.65 + yy * 0.35)
        base_rgb = (1.0 - weight[..., None]) * c_start + weight[..., None] * c_end

        # 2. Studio key light (ambient spotlight centered behind presenter head/chest)
        spot_cx, spot_cy = float(av_x), 0.38
        r = np.sqrt(((xx - spot_cx) * 1.5) ** 2 + ((yy - spot_cy)) ** 2)
        glow = np.exp(-r * 2.8) * 45.0
        glow_tint = np.array([0.75, 0.85, 1.0], dtype=np.float32)
        base_rgb += glow[..., None] * glow_tint

        # 3. Layered studio architectural accents
        if scene_index == 0:
            # Scene 1: Subtle horizontal studio ambient glow strip
            horizon_dist = np.abs(yy - 0.65)
            horizon_glow = np.exp(-horizon_dist * 12.0) * 16.0
            base_rgb += horizon_glow[..., None] * np.array([0.6, 0.8, 1.0], dtype=np.float32)
        elif scene_index == 1:
            # Scene 2: Vertical ambient divider beam separating visual card side from presenter side
            divider_dist = np.abs(xx - 0.50)
            divider_glow = np.exp(-divider_dist * 20.0) * 18.0
            base_rgb += divider_glow[..., None] * np.array([0.5, 0.9, 0.7], dtype=np.float32)
        elif scene_index >= 2:
            # Scene 3: Subtle stage floor gradient wash
            floor_dist = np.clip((yy - 0.72) / 0.28, 0.0, 1.0)
            floor_glow = floor_dist * 22.0
            base_rgb += floor_glow[..., None] * np.array([0.7, 0.6, 1.0], dtype=np.float32)

        # 4. Cinematic vignette (darken corners to focus audience on presenter)
        dist_corner = np.sqrt((xx - 0.5) ** 2 + (yy - 0.5) ** 2) / 0.707
        vignette = 1.0 - 0.30 * np.clip(dist_corner, 0.0, 1.0) ** 1.8
        base_rgb *= vignette[..., None]

        # 5. Subtle fine-grain dither to eliminate 8-bit banding
        np.random.seed(42 + scene_index)
        dither = (np.random.rand(h, w, 1).astype(np.float32) - 0.5) * 1.2
        base_rgb += dither

        grad_bgr = cv2.cvtColor(np.clip(base_rgb, 0, 255).astype(np.uint8), cv2.COLOR_RGB2BGR)
        cv2.imwrite(str(output_path), grad_bgr, [cv2.IMWRITE_PNG_COMPRESSION, 3])
        return output_path

    def _generate_scene_ass_file(
        self,
        subtitles: List[Dict[str, Any]],
        caption_settings: Optional[CaptionSettings],
        canvas: CanvasProfile,
        output_path: Path,
    ) -> Optional[Path]:
        """Generate ASS v4.00+ subtitle file for a scene based on caption settings."""
        if caption_settings and not caption_settings.enabled:
            return None

        enabled_cues = [
            c for c in (subtitles or [])
            if c.get("enabled", True) and str(c.get("text", "")).strip()
        ]
        if not enabled_cues:
            return None

        style = caption_settings.style if caption_settings else None
        font_family = (style.font_family if style and style.font_family else "Arial").strip()
        font_size = int(style.font_size if style and style.font_size else 32)
        is_bold = -1 if (style and (style.font_weight or "").lower() == "bold") else 0

        text_color = self._hex_to_ass(style.color if style else "#FFFFFF", 0.0)

        bg_opacity = float(style.background_opacity) if style and style.background_opacity is not None else 0.6
        bg_color_hex = style.background_color if style and style.background_color else "#000000"
        transparency = max(0.0, min(1.0, 1.0 - bg_opacity))
        back_color = self._hex_to_ass(bg_color_hex, transparency)

        border_style = 3 if bg_opacity > 0.05 else 1
        outline_size = 4 if border_style == 3 else 2

        pos = (style.position if style and style.position else "bottom").lower()
        align = (style.alignment if style and style.alignment else "center").lower()
        if pos == "top":
            ass_align = 7 if align == "left" else (9 if align == "right" else 8)
            margin_v = 30
        elif pos == "center":
            ass_align = 4 if align == "left" else (6 if align == "right" else 5)
            margin_v = 0
        else:
            ass_align = 1 if align == "left" else (3 if align == "right" else 2)
            margin_v = 40

        header = f"""[Script Info]
Title: HeyZen Scene Subtitles
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
PlayResX: {canvas.width}
PlayResY: {canvas.height}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_family},{font_size},{text_color},&H000000FF,&H00000000,{back_color},{is_bold},0,0,0,100,100,0,0,{border_style},{outline_size},0,{ass_align},20,20,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        events = []
        for cue in enabled_cues:
            start_sec = max(0.0, float(cue.get("start", 0.0)))
            end_sec = max(start_sec + 0.1, float(cue.get("end", start_sec + 1.0)))
            cue_text = str(cue.get("text", "")).strip().replace("\n", "\\N")
            start_str = self._format_time(start_sec)
            end_str = self._format_time(end_sec)
            events.append(f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{cue_text}")

        content = header + "\n".join(events) + "\n"
        output_path.write_text(content, encoding="utf-8")
        return output_path

    def _generate_scene_text_ass_file(
        self,
        layers: List[SceneLayer],
        canvas: CanvasProfile,
        output_path: Path,
    ) -> Optional[Path]:
        """Generate ASS v4.00+ script for active visual text overlays in a scene."""
        text_layers = [
            l for l in (layers or [])
            if l.type == "text" and getattr(l, "enabled", True) is not False
        ]
        valid_layers = []
        for l in text_layers:
            content = l.content or {}
            txt = str(content.get("text") or (content.get("title") or l.name or "")).strip()
            if txt:
                valid_layers.append((l, txt))

        if not valid_layers:
            return None

        styles_header = f"""[Script Info]
Title: HeyZen Scene Visual Text Overlays
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
PlayResX: {canvas.width}
PlayResY: {canvas.height}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
"""
        styles_lines = []
        events_lines = []

        for idx, (layer, txt) in enumerate(valid_layers):
            c = layer.content or {}
            style_obj = c.get("style") if isinstance(c.get("style"), dict) else {}

            font_family = str(c.get("font_family") or style_obj.get("fontFamily") or "Arial").strip() or "Arial"
            font_size = int(c.get("font_size") or style_obj.get("fontSize") or 48)
            font_weight = str(c.get("font_weight") or style_obj.get("fontWeight") or "bold").lower()
            is_bold = -1 if font_weight == "bold" else 0

            color_hex = str(c.get("color") or style_obj.get("color") or "#FFFFFF")
            txt_opacity = float(c.get("opacity") if c.get("opacity") is not None else (style_obj.get("opacity") if style_obj.get("opacity") is not None else 1.0))
            text_color = self._hex_to_ass(color_hex, 1.0 - txt_opacity)

            bg_color_hex = str(c.get("background_color") or style_obj.get("backgroundColor") or "#000000")
            bg_opacity = float(c.get("background_opacity") if c.get("background_opacity") is not None else (style_obj.get("backgroundOpacity") if style_obj.get("backgroundOpacity") is not None else 0.0))
            back_color = self._hex_to_ass(bg_color_hex, 1.0 - bg_opacity)

            border_style = 3 if bg_opacity > 0.05 else 1
            outline_size = 4 if border_style == 3 else 1

            t = layer.transform or {}
            pos_x = max(0.0, min(1.0, float(t.get("x", 0.5))))
            pos_y = max(0.0, min(1.0, float(t.get("y", 0.5))))
            scale = max(0.05, min(10.0, float(t.get("scale", 1.0))))
            rotation = float(t.get("rotation", 0.0))

            effective_font_size = max(4, int(round(font_size * scale)))

            px = int(round(canvas.width * pos_x))
            py = int(round(canvas.height * pos_y))

            # Normalize rotation to [-180, 180] degrees
            norm_rot = (rotation + 180.0) % 360.0 - 180.0
            if norm_rot == -180.0 and rotation > 0:
                norm_rot = 180.0
            ass_rot = round(-norm_rot, 2)
            if ass_rot == 0:
                ass_rot_str = "0"
            elif ass_rot == int(ass_rot):
                ass_rot_str = str(int(ass_rot))
            else:
                ass_rot_str = f"{ass_rot:.2f}".rstrip("0").rstrip(".")
            rot_tag = f"\\frz({ass_rot_str})"

            alignment = str(c.get("alignment") or style_obj.get("textAlign") or "center").lower()
            if alignment == "left":
                ass_an = 4
            elif alignment == "right":
                ass_an = 6
            else:
                ass_an = 5

            style_name = f"TextLayer_{idx}"
            styles_lines.append(
                f"Style: {style_name},{font_family},{effective_font_size},{text_color},&H000000FF,&H00000000,{back_color},{is_bold},0,0,0,100,100,0,0,{border_style},{outline_size},0,{ass_an},10,10,10,1"
            )

            start_sec = max(0.0, float(layer.start_time or 0.0))
            end_sec = max(start_sec + 0.1, float(layer.end_time if layer.end_time is not None else 5.0))
            start_str = self._format_time(start_sec)
            end_str = self._format_time(end_sec)
            ass_txt = txt.replace("\n", "\\N")

            events_lines.append(
                f"Dialogue: 0,{start_str},{end_str},{style_name},,0,0,0,,{{\\pos({px},{py})\\an{ass_an}{rot_tag}}}{ass_txt}"
            )

        events_header = "\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        full_content = styles_header + "\n".join(styles_lines) + events_header + "\n".join(events_lines) + "\n"
        output_path.write_text(full_content, encoding="utf-8")
        return output_path

    async def _render_scene_clip(
        self,
        scene: Scene,
        scene_index: int,
        canvas: CanvasProfile,
        workspace_id: Union[str, uuid.UUID],
        db: AsyncSession,
        mws: MediaWorkspace,
        caption_settings: Optional[CaptionSettings] = None,
    ) -> Path:
        """Render an individual scene sequence into an isolated MP4 clip."""
        scene_duration = max(0.5, float(scene.duration or 5.0))
        output_clip_path = mws.scenes_dir / f"scene_{scene_index:03d}.mp4"

        # 1. Resolve speech audio if present
        speech_audio_path: Optional[Path] = None
        if scene.speech and scene.speech.audio_asset_id:
            try:
                speech_audio_path = await mws.resolve_asset(
                    asset_id=scene.speech.audio_asset_id,
                    workspace_id=workspace_id,
                    db=db,
                )
                audio_probe = await self.ffprobe_service.probe(speech_audio_path)
                # Ensure scene duration accommodates full speech audio with 0.1s padding
                if audio_probe.duration_seconds > scene_duration:
                    scene_duration = round(audio_probe.duration_seconds + 0.1, 2)
            except Exception as e:
                logger.warning("Could not resolve scene speech audio %s: %s", scene.speech.audio_asset_id, e)

        # 2. Check for scene avatar video or image
        avatar_path: Optional[Path] = None
        is_avatar_image: bool = False
        if scene.avatar:
            av_ref = scene.avatar.video_asset_id or getattr(scene.avatar, "asset_id", None)
            if not av_ref and scene.avatar.avatar_id:
                from app.models.avatar import Avatar
                from sqlalchemy import select
                try:
                    av_raw = str(scene.avatar.avatar_id).strip()
                    try:
                        av_uuid = uuid.UUID(av_raw)
                        stmt = select(Avatar).where(Avatar.id == av_uuid)
                    except ValueError:
                        from sqlalchemy import func, or_
                        stmt = select(Avatar).where(
                            or_(
                                Avatar.provider_reference == av_raw,
                                func.lower(Avatar.name) == av_raw.lower(),
                                func.replace(func.lower(Avatar.name), " - ", "-") == av_raw.lower(),
                            )
                        )
                    res = await db.execute(stmt)
                    db_av = res.scalars().first()
                    if db_av and db_av.preview_asset_id:
                        av_ref = str(db_av.preview_asset_id)
                except Exception as av_err:
                    logger.warning("Could not lookup avatar %s: %s", scene.avatar.avatar_id, av_err)

            if av_ref:
                try:
                    avatar_path = await mws.resolve_asset(
                        asset_id=av_ref,
                        workspace_id=workspace_id,
                        db=db,
                    )
                    if avatar_path and avatar_path.exists():
                        suffix = avatar_path.suffix.lower()
                        if suffix in (".jpg", ".jpeg", ".png", ".webp"):
                            is_avatar_image = True
                        else:
                            av_probe = await self.ffprobe_service.probe(avatar_path)
                            if av_probe.duration_seconds > scene_duration:
                                scene_duration = round(av_probe.duration_seconds, 2)
                except Exception as e:
                    logger.warning("Could not resolve scene avatar asset %s: %s", av_ref, e)

        # 3. Configure visual inputs and filters
        if hasattr(scene.background, "model_dump"):
            bg = scene.background.model_dump()
        elif isinstance(scene.background, dict):
            bg = scene.background
        else:
            bg = {}
        bg_type = str(bg.get("type", "color")).lower()
        input_args: List[str] = []
        bg_scale_filter = ""

        # Extract camera motion configured for this scene
        camera_motion = str(
            getattr(scene, "camera_motion", None)
            or bg.get("camera_motion")
            or "static"
        ).strip().lower()

        has_avatar = bool(scene.avatar and (scene.avatar.avatar_id or getattr(scene.avatar, "avatar_asset_id", None)))
        av_pos = scene.avatar.position if (scene.avatar and isinstance(scene.avatar.position, dict)) else {}
        av_x = float(av_pos.get("x", 0.68 if scene_index == 1 else 0.5))

        if bg_type in ("gradient", "linear-gradient") or bg.get("gradient"):
            grad_path = mws.scenes_dir / f"scene_{scene_index:03d}_bg_grad.png"
            self._generate_gradient_background(bg, canvas, grad_path, scene_index=scene_index, av_x=av_x)
            input_args.extend(["-loop", "1", "-i", str(grad_path)])
            bg_scale_filter = build_scale_and_pad(canvas.width, canvas.height, fit_mode="cover")

        elif bg_type == "image" and bg.get("asset_id"):
            img_path = await mws.resolve_asset(
                asset_id=bg["asset_id"],
                workspace_id=workspace_id,
                db=db,
            )
            input_args.extend(["-loop", "1", "-i", str(img_path)])
            bg_scale_filter = build_scale_and_pad(canvas.width, canvas.height, fit_mode="contain")

        elif bg_type == "video" and bg.get("asset_id"):
            vid_path = await mws.resolve_asset(
                asset_id=bg["asset_id"],
                workspace_id=workspace_id,
                db=db,
            )
            input_args.extend(["-stream_loop", "-1", "-i", str(vid_path)])
            bg_scale_filter = build_scale_and_pad(canvas.width, canvas.height, fit_mode="cover")

        else:
            # Solid color background canvas
            color_val = bg.get("value") or bg.get("color") or "#0F172A"
            input_args.extend(
                build_color_source(
                    color=color_val,
                    width=canvas.width,
                    height=canvas.height,
                    duration=scene_duration,
                    fps=canvas.fps,
                )
            )

        # 4. Text overlay & Subtitle / Caption processing
        text_ass_path = self._generate_scene_text_ass_file(
            layers=scene.layers,
            canvas=canvas,
            output_path=mws.scenes_dir / f"scene_{scene_index:03d}_text.ass",
        )
        text_filter = ""
        if text_ass_path and text_ass_path.exists():
            escaped_text_ass = str(text_ass_path).replace("\\", "/").replace(":", "\\:")
            text_filter = f"ass='{escaped_text_ass}'"

        ass_path = self._generate_scene_ass_file(
            subtitles=scene.subtitles,
            caption_settings=caption_settings,
            canvas=canvas,
            output_path=mws.scenes_dir / f"scene_{scene_index:03d}_captions.ass",
        )
        ass_filter = ""
        if ass_path and ass_path.exists():
            escaped_ass = str(ass_path).replace("\\", "/").replace(":", "\\:")
            ass_filter = f"ass='{escaped_ass}'"

        # Legacy fallback drawtext ONLY if neither text ASS nor caption ASS is present and scene has script
        drawtext_filter = ""
        if not text_filter and not ass_filter and scene.speech and scene.speech.script:
            script_text = scene.speech.script.strip()
            if script_text:
                text_file = mws.scenes_dir / f"scene_{scene_index:03d}_text.txt"
                text_file.write_text(script_text, encoding="utf-8")
                drawtext_filter = build_drawtext_filter(
                    text_file_path=text_file,
                    font_size=max(24, int(canvas.height * 0.04)),
                    font_color="white",
                    x="(w-text_w)/2",
                    y="h-text_h-80",
                    box=True,
                    box_color="black@0.65",
                    box_borderw=10,
                )

        # 5. Visual Overlay Layers (Images, Videos, Shapes, Stickers, Elements, Text, Captions)
        raw_scene_layers = [
            l for l in (scene.layers or [])
            if l.type in ("image", "video", "media", "shape", "sticker", "element", "text")
            and getattr(l, "enabled", True) is not False
        ]

        active_caption_cues: List[Dict[str, Any]] = []
        is_captions_enabled = bool(caption_settings.enabled) if caption_settings else True
        if is_captions_enabled and scene.subtitles:
            cap_style_z = getattr(caption_settings.style, "z_index", None) if (caption_settings and caption_settings.style) else None
            for cue in scene.subtitles:
                if cue.get("enabled", True) and str(cue.get("text", "")).strip():
                    cue_z = cue.get("z_index") if cue.get("z_index") is not None else cap_style_z
                    active_caption_cues.append({
                        "id": str(cue.get("id", f"cue_{len(active_caption_cues)}")),
                        "type": "caption",
                        "name": "Caption",
                        "start_time": max(0.0, float(cue.get("start", 0.0))),
                        "end_time": max(float(cue.get("start", 0.0)) + 0.1, float(cue.get("end", float(cue.get("start", 0.0)) + 1.0))),
                        "z_index": cue_z,
                        "cue_data": cue,
                    })

        # Wrap into candidates for deterministic Phase 42B sorting
        unified_candidates = []
        for orig_idx, l in enumerate(raw_scene_layers):
            z_val = getattr(l, "z_index", None)
            unified_candidates.append({
                "item": l,
                "kind": "layer",
                "original_idx": orig_idx,
                "current_z": z_val if (isinstance(z_val, (int, float)) and not math.isnan(z_val)) else None,
            })
        base_cue_offset = len(raw_scene_layers)
        for cue_idx, c in enumerate(active_caption_cues):
            c_z = c.get("z_index")
            unified_candidates.append({
                "item": c,
                "kind": "caption",
                "original_idx": base_cue_offset + cue_idx,
                "current_z": c_z if (isinstance(c_z, (int, float)) and not math.isnan(c_z)) else None,
            })

        has_any_z = any(c["current_z"] is not None for c in unified_candidates)
        if has_any_z:
            def _sort_key(entry):
                cz = entry["current_z"]
                if cz is not None:
                    return (0, cz, entry["original_idx"])
                return (1, 0, entry["original_idx"])
            unified_candidates.sort(key=_sort_key)
        else:
            # Deterministic legacy tier normalization: media -> text -> elements -> captions
            def _legacy_tier_key(entry):
                if entry["kind"] == "caption":
                    return (3, entry["original_idx"])
                l = entry["item"]
                if l.type in ("image", "video", "media"):
                    return (0, entry["original_idx"])
                elif l.type == "text":
                    return (1, entry["original_idx"])
                else:
                    return (2, entry["original_idx"])
            unified_candidates.sort(key=_legacy_tier_key)

        has_avatar = bool(avatar_path and avatar_path.exists())
        has_media_layers = bool(unified_candidates)

        if has_avatar or has_media_layers:
            filter_complex_parts: List[str] = []

            # Background stream preparation with optional camera zoom motion
            if camera_motion in ("slow_zoom_in", "zoom_in"):
                bg_pre = f"{bg_scale_filter}," if bg_scale_filter else ""
                filter_complex_parts.append(
                    f"[0:v]{bg_pre}zoompan=z='min(zoom+0.0006,1.06)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={canvas.width}x{canvas.height}:fps={canvas.fps}[bg]"
                )
            elif camera_motion in ("slow_zoom_out", "zoom_out"):
                bg_pre = f"{bg_scale_filter}," if bg_scale_filter else ""
                filter_complex_parts.append(
                    f"[0:v]{bg_pre}zoompan=z='if(lte(zoom,1.0),1.06,max(1.001,zoom-0.0006))':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={canvas.width}x{canvas.height}:fps={canvas.fps}[bg]"
                )
            elif bg_scale_filter:
                filter_complex_parts.append(f"[0:v]{bg_scale_filter}[bg]")
            else:
                filter_complex_parts.append("[0:v]null[bg]")

            current_video_label = "[bg]"

            # Avatar PIP or Matting overlay
            if has_avatar:
                view_mode = (scene.avatar.view_mode or "half_body").lower() if scene.avatar else "half_body"
                pos = scene.avatar.position if (scene.avatar and isinstance(scene.avatar.position, dict)) else {}
                pos_x = float(pos.get("x", 0.5))
                pos_y = float(pos.get("y", 0.65 if view_mode == "half_body" else 0.5))
                scale = float(pos.get("scale", 1.0))

                # Camera motion framing presets (WIDE, MEDIUM, MEDIUM_CLOSE, CLOSE_UP)
                if camera_motion in ("presenter_closeup", "close_up"):
                    view_mode = "close_up"
                    framing_factor = 1.08
                elif camera_motion in ("presenter_medium_close", "medium_close"):
                    view_mode = "medium_close"
                    framing_factor = 0.98
                elif camera_motion in ("presenter_wide", "wide"):
                    view_mode = "wide"
                    framing_factor = 0.78
                else:  # default professional broadcast medium shot
                    view_mode = "medium"
                    framing_factor = 0.88

                if view_mode == "circle":
                    av_in_idx = input_args.count("-i")
                    if is_avatar_image:
                        input_args.extend(["-loop", "1", "-i", str(avatar_path)])
                    else:
                        input_args.extend(["-stream_loop", "-1", "-i", str(avatar_path)])
                    diameter = int(min(canvas.width, canvas.height) * 0.35 * scale)
                    diameter = max(64, min(min(canvas.width, canvas.height), diameter))
                    ox = max(0, min(canvas.width - diameter, int(canvas.width * pos_x - diameter / 2)))
                    oy = max(0, min(canvas.height - diameter, int(canvas.height * pos_y - diameter / 2)))

                    circle_filter = build_circular_mask_filter(diameter)
                    filter_complex_parts.append(f"[{av_in_idx}:v]{circle_filter}[avatar_pip]")
                    filter_complex_parts.append(f"{current_video_label}[avatar_pip]overlay=x={ox}:y={oy}[comp_avatar]")
                    current_video_label = "[comp_avatar]"

                else:
                    target_h = int(canvas.height * framing_factor * scale)
                    target_h = max(64, min(canvas.height * 2, target_h))

                    # Cinematic camera movement expressions anchored to bottom for professional studio framing
                    if camera_motion == "pan_left":
                        ox_expr = f"(main_w*{pos_x:.3f}-overlay_w/2 + (t/{scene_duration:.2f})*35)"
                        oy_expr = "(main_h-overlay_h)"
                    elif camera_motion == "pan_right":
                        ox_expr = f"(main_w*{pos_x:.3f}-overlay_w/2 - (t/{scene_duration:.2f})*35)"
                        oy_expr = "(main_h-overlay_h)"
                    elif camera_motion in ("slow_zoom_in", "zoom_in"):
                        ox_expr = f"(main_w*{pos_x:.3f}-overlay_w/2)"
                        oy_expr = f"(main_h-overlay_h - (t/{scene_duration:.2f})*12)"
                    elif camera_motion in ("slow_zoom_out", "zoom_out"):
                        ox_expr = f"(main_w*{pos_x:.3f}-overlay_w/2)"
                        oy_expr = f"(main_h-overlay_h + (t/{scene_duration:.2f})*12)"
                    else:
                        ox_expr = f"(main_w*{pos_x:.3f}-overlay_w/2)"
                        oy_expr = "(main_h-overlay_h)"

                    if is_avatar_image:
                        matte_img_path = mws.scenes_dir / f"scene_{scene_index:03d}_avatar_matte.png"
                        try:
                            from app.ai.registry import get_matting_provider
                            matting_provider = get_matting_provider()
                            if hasattr(matting_provider, "_get_session"):
                                session = await matting_provider._get_session()
                                import cv2
                                img_bgr = cv2.imread(str(avatar_path))
                                if img_bgr is not None:
                                    alpha = matting_provider.segment_frame_sync(session, img_bgr, threshold=0.5, soft_matte=True)
                                    cv2.imwrite(str(matte_img_path), cv2.cvtColor(alpha, cv2.COLOR_GRAY2BGR))
                                else:
                                    import numpy as np
                                    cv2.imwrite(str(matte_img_path), np.full((768, 768, 3), 255, dtype=np.uint8))
                            else:
                                import cv2
                                import numpy as np
                                cv2.imwrite(str(matte_img_path), np.full((768, 768, 3), 255, dtype=np.uint8))
                        except Exception as matte_err:
                            logger.warning("Could not extract neural matte for avatar image: %s", matte_err)
                            import cv2
                            import numpy as np
                            cv2.imwrite(str(matte_img_path), np.full((768, 768, 3), 255, dtype=np.uint8))

                        av_in_idx = input_args.count("-i")
                        input_args.extend(["-loop", "1", "-i", str(avatar_path)])
                        matte_in_idx = input_args.count("-i")
                        input_args.extend(["-loop", "1", "-i", str(matte_img_path)])

                    else:
                        matte_video_path = mws.scenes_dir / f"scene_{scene_index:03d}_avatar_matte.mp4"
                        from app.ai.registry import get_matting_provider
                        matting_provider = get_matting_provider()

                        if hasattr(matting_provider, "extract_video_matte_sync") and hasattr(matting_provider, "_get_session"):
                            session = await matting_provider._get_session()
                            await asyncio.to_thread(
                                matting_provider.extract_video_matte_sync,
                                session,
                                avatar_path,
                                matte_video_path,
                                0.5,
                                True,
                            )
                        else:
                            av_probe = await self.ffprobe_service.probe(avatar_path)
                            av_w = av_probe.width or canvas.width
                            av_h = av_probe.height or canvas.height
                            av_dur = av_probe.duration_seconds or scene_duration
                            mock_matte_cmd = [
                                "-y", "-f", "lavfi",
                                "-i", f"color=c=white:s={av_w}x{av_h}:r={canvas.fps}:d={av_dur:.3f}",
                                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                                str(matte_video_path),
                            ]
                            await self.ffmpeg_service.execute_ffmpeg(mock_matte_cmd)

                        av_in_idx = input_args.count("-i")
                        input_args.extend(["-stream_loop", "-1", "-i", str(avatar_path)])
                        matte_in_idx = input_args.count("-i")
                        input_args.extend(["-stream_loop", "-1", "-i", str(matte_video_path)])

                    filter_complex_parts.append(f"[{av_in_idx}:v][{matte_in_idx}:v]alphamerge[avatar_rgba]")
                    filter_complex_parts.append(f"[avatar_rgba]scale=-1:{target_h}[scaled_avatar]")
                    filter_complex_parts.append(f"{current_video_label}[scaled_avatar]overlay=x='{ox_expr}':y='{oy_expr}'[comp_avatar]")
                    current_video_label = "[comp_avatar]"

            # Unified Visual Overlay Layers Compositing (Media, Shapes, Stickers, Text, Captions)
            for m_idx, candidate in enumerate(unified_candidates):
                is_video = False
                m_path: Optional[Path] = None

                if candidate["kind"] == "caption":
                    c_data = candidate["item"]["cue_data"]
                    cue_text = str(c_data.get("text", "")).strip()
                    start_t = candidate["item"]["start_time"]
                    end_t = min(scene_duration, candidate["item"]["end_time"])

                    cap_style = caption_settings.style if caption_settings else None
                    font_family = cap_style.font_family if cap_style and cap_style.font_family else "Arial"
                    font_size = cap_style.font_size if (cap_style and cap_style.font_size and cap_style.font_size >= 24) else 36
                    font_weight = cap_style.font_weight if cap_style and cap_style.font_weight else "bold"
                    color = cap_style.color if cap_style and cap_style.color else "#FFFFFF"
                    bg_color = cap_style.background_color if cap_style and cap_style.background_color else "#0A0E1A"
                    bg_opacity = cap_style.background_opacity if cap_style and cap_style.background_opacity is not None else 0.82
                    pos = (cap_style.position or "bottom").lower() if cap_style else "bottom"
                    alignment = (cap_style.alignment or "center").lower() if cap_style else "center"

                    # Context-aware caption placement: prevent covering presenter face, mouth, or chest
                    if has_avatar:
                        if av_x > 0.58:
                            # Presenter on right (split layout): place captions in left visual column
                            pos_x = 0.28
                            pos_y = 0.84
                        elif av_x < 0.42:
                            # Presenter on left: place captions in right visual column
                            pos_x = 0.72
                            pos_y = 0.84
                        else:
                            # Presenter centered: lower-third bottom safe margin
                            pos_x = 0.50
                            pos_y = 0.93
                    else:
                        pos_x = 0.5
                        if alignment == "left":
                            pos_x = 0.2
                        elif alignment == "right":
                            pos_x = 0.8

                        if pos == "top":
                            pos_y = 0.08
                        elif pos == "center":
                            pos_y = 0.50
                        else:
                            pos_y = 0.93

                    cap_img_path = mws.scenes_dir / f"scene_{scene_index:03d}_cap_{m_idx}_{candidate['item']['id']}.png"
                    cap_img = render_caption_cue_to_image(
                        cue_text=cue_text,
                        font_family=font_family,
                        font_size=font_size,
                        font_weight=font_weight,
                        color=color,
                        background_color=bg_color,
                        background_opacity=bg_opacity,
                        alignment=alignment,
                        scale=1.0,
                        canvas_width=canvas.width,
                        canvas_height=canvas.height,
                        output_path=cap_img_path,
                    )
                    m_path = cap_img_path
                    target_w = cap_img.width
                    target_h = cap_img.height
                    m_rotation = 0.0
                    m_opacity = 1.0

                elif candidate["kind"] == "layer" and candidate["item"].type == "text":
                    l = candidate["item"]
                    c_data = l.content if isinstance(l.content, dict) else {}
                    t_data = l.transform if isinstance(l.transform, dict) else {}
                    txt = str(c_data.get("text") or (c_data.get("title") or l.name or "")).strip()

                    start_t = max(0.0, float(l.start_time if l.start_time is not None else 0.0))
                    end_t = min(scene_duration, max(start_t + 0.05, float(l.end_time if l.end_time is not None else scene_duration)))
                    pos_x = max(0.0, min(1.0, float(t_data.get("x", 0.5))))
                    pos_y = max(0.0, min(1.0, float(t_data.get("y", 0.5))))
                    m_scale = max(0.05, min(10.0, float(t_data.get("scale", 1.0))))
                    m_rotation = float(t_data.get("rotation", 0.0))

                    style_obj = c_data.get("style") if isinstance(c_data.get("style"), dict) else {}
                    font_family = str(c_data.get("font_family") or style_obj.get("fontFamily") or "Arial").strip() or "Arial"
                    font_size = int(c_data.get("font_size") or style_obj.get("fontSize") or 48)
                    font_weight = str(c_data.get("font_weight") or style_obj.get("fontWeight") or "bold")
                    font_style = str(c_data.get("font_style") or style_obj.get("fontStyle") or "normal")
                    color = str(c_data.get("color") or style_obj.get("color") or "#FFFFFF")
                    m_opacity = float(c_data.get("opacity") if c_data.get("opacity") is not None else (style_obj.get("opacity") if style_obj.get("opacity") is not None else 1.0))
                    m_opacity = max(0.0, min(1.0, m_opacity))
                    bg_color = str(c_data.get("background_color") or style_obj.get("backgroundColor") or "#000000")
                    bg_opacity = float(c_data.get("background_opacity") if c_data.get("background_opacity") is not None else (style_obj.get("backgroundOpacity") if style_obj.get("backgroundOpacity") is not None else 0.0))
                    alignment = str(c_data.get("alignment") or style_obj.get("textAlign") or "center")

                    txt_img_path = mws.scenes_dir / f"scene_{scene_index:03d}_txt_{m_idx}_{l.id}.png"
                    txt_img = render_text_layer_to_image(
                        text=txt,
                        font_family=font_family,
                        font_size=font_size,
                        font_weight=font_weight,
                        font_style=font_style,
                        color=color,
                        opacity=m_opacity,
                        background_color=bg_color,
                        background_opacity=bg_opacity,
                        alignment=alignment,
                        scale=m_scale,
                        canvas_width=canvas.width,
                        canvas_height=canvas.height,
                        output_path=txt_img_path,
                    )
                    m_path = txt_img_path
                    target_w = txt_img.width
                    target_h = txt_img.height
                    # Opacity is already baked into transparent PNG pixels
                    m_opacity = 1.0

                else:
                    m_layer = candidate["item"]
                    c_data = m_layer.content if isinstance(m_layer.content, dict) else {}
                    t_data = m_layer.transform if isinstance(m_layer.transform, dict) else {}
                    m_scale = max(0.05, min(10.0, float(t_data.get("scale", 1.0))))
                    m_rotation = float(t_data.get("rotation", 0.0))
                    m_opacity = float(c_data.get("opacity") if c_data.get("opacity") is not None else 1.0)
                    m_opacity = max(0.0, min(1.0, m_opacity))

                    pos_x = max(0.0, min(1.0, float(t_data.get("x", 0.5))))
                    pos_y = max(0.0, min(1.0, float(t_data.get("y", 0.5))))

                    start_t = max(0.0, float(m_layer.start_time if m_layer.start_time is not None else 0.0))
                    end_t = min(scene_duration, max(start_t + 0.05, float(m_layer.end_time if m_layer.end_time is not None else scene_duration)))

                    if m_layer.type == "shape":
                        shape_type = c_data.get("shape_type") or "rectangle"
                        w_val = c_data.get("width") if c_data.get("width") is not None else 0.3
                        h_val = c_data.get("height") if c_data.get("height") is not None else 0.2
                        base_w = int(canvas.width * w_val) if float(w_val) <= 1.0 else int(w_val)
                        base_h = int(canvas.height * h_val) if float(h_val) <= 1.0 else int(h_val)
                        target_w = max(4, int(round(base_w * m_scale)))
                        target_h = max(4, int(round(base_h * m_scale)))
                        target_w = (target_w // 2) * 2
                        target_h = (target_h // 2) * 2

                        fill = c_data.get("fill") or "#3B82F6"
                        border_color = c_data.get("border_color") or c_data.get("stroke") or "#FFFFFF"
                        border_width = int(c_data.get("border_width") or c_data.get("stroke_width") or 0)
                        border_radius = int(c_data.get("border_radius") or 0)

                        shape_img_path = mws.scenes_dir / f"scene_{scene_index:03d}_shape_{m_idx}_{m_layer.id}.png"
                        render_shape_to_image(
                            shape_type=shape_type,
                            width=target_w,
                            height=target_h,
                            fill=fill,
                            border_color=border_color,
                            border_width=border_width,
                            border_radius=border_radius,
                            opacity=m_opacity,
                            output_path=shape_img_path,
                        )
                        m_path = shape_img_path

                    elif m_layer.type in ("sticker", "element"):
                        m_asset_id = c_data.get("asset_id") or getattr(m_layer, "asset_id", None) or c_data.get("assetId")
                        if m_asset_id:
                            m_path = await mws.resolve_asset(
                                asset_id=m_asset_id,
                                workspace_id=workspace_id,
                                db=db,
                            )
                            if not m_path or not m_path.exists():
                                raise RenderInputMissingError(f"Failed to resolve sticker layer asset {m_asset_id}")
                            try:
                                m_probe = await self.ffprobe_service.probe(m_path)
                            except Exception as e:
                                raise RenderOutputInvalidError(f"Failed to probe sticker layer asset {m_asset_id}: {e}") from e

                            is_video = (
                                c_data.get("media_type") == "video"
                                or (m_probe.duration_seconds > 0.05 and m_probe.format_name not in ("image2", "png_pipe", "jpeg_pipe", "webp_pipe"))
                            )
                            orig_w = m_probe.width or canvas.width
                            orig_h = m_probe.height or canvas.height
                            target_w = max(4, int(round(canvas.width * 0.25 * m_scale)))
                            target_h = max(4, int(round(target_w * (orig_h / max(1, orig_w)))))
                            target_w = (target_w // 2) * 2
                            target_h = (target_h // 2) * 2
                        else:
                            sticker_id = c_data.get("sticker_id") or c_data.get("id") or m_layer.name or "star"
                            base_dim = int(min(canvas.width, canvas.height) * 0.25)
                            target_w = max(16, int(round(base_dim * m_scale)))
                            target_h = target_w
                            target_w = (target_w // 2) * 2
                            target_h = (target_h // 2) * 2
                            fill_color = c_data.get("fill") or c_data.get("color")
                            sticker_img_path = mws.scenes_dir / f"scene_{scene_index:03d}_sticker_{m_idx}_{m_layer.id}.png"
                            render_sticker_to_image(
                                sticker_id=sticker_id,
                                width=target_w,
                                height=target_h,
                                fill_color=fill_color,
                                opacity=m_opacity,
                                output_path=sticker_img_path,
                            )
                            m_path = sticker_img_path

                    else:
                        m_asset_id = c_data.get("asset_id") or getattr(m_layer, "asset_id", None) or c_data.get("assetId")
                        if not m_asset_id:
                            continue

                        m_path = await mws.resolve_asset(
                            asset_id=m_asset_id,
                            workspace_id=workspace_id,
                            db=db,
                        )
                        if not m_path or not m_path.exists():
                            raise RenderInputMissingError(f"Failed to resolve media layer asset {m_asset_id}")

                        try:
                            m_probe = await self.ffprobe_service.probe(m_path)
                        except Exception as e:
                            raise RenderOutputInvalidError(f"Failed to probe media layer asset {m_asset_id}: {e}") from e

                        is_video = (
                            m_layer.type == "video"
                            or c_data.get("media_type") == "video"
                            or (m_probe.duration_seconds > 0.05 and m_probe.format_name not in ("image2", "png_pipe", "jpeg_pipe", "webp_pipe"))
                        )

                        orig_w = m_probe.width or canvas.width
                        orig_h = m_probe.height or canvas.height
                        target_w = max(4, int(round(canvas.width * 0.4 * m_scale)))
                        target_h = max(4, int(round(target_w * (orig_h / max(1, orig_w)))))
                        target_w = (target_w // 2) * 2
                        target_h = (target_h // 2) * 2

                if not m_path or not m_path.exists():
                    continue

                m_in_idx = input_args.count("-i")
                if is_video:
                    input_args.extend(["-stream_loop", "-1", "-i", str(m_path)])
                else:
                    input_args.extend(["-loop", "1", "-i", str(m_path)])

                layer_filters = []
                if is_video:
                    layer_filters.append(f"setpts=PTS-STARTPTS+{start_t:.3f}/TB")
                layer_filters.append(f"scale={target_w}:{target_h}")
                if m_rotation != 0.0:
                    layer_filters.append(f"rotate={m_rotation:.2f}*PI/180:ow='hypot(iw,ih)':oh=ow:c=none")
                if candidate["kind"] == "layer" and candidate["item"].type in ("image", "video", "media") and m_opacity < 0.99:
                    layer_filters.append(f"format=rgba,colorchannelmixer=aa={m_opacity:.2f}")
                else:
                    layer_filters.append("format=rgba")

                layer_ready_label = f"[m_{m_idx}_ready]"
                filter_complex_parts.append(f"[{m_in_idx}:v]{','.join(layer_filters)}{layer_ready_label}")

                next_video_label = f"[comp_m_{m_idx}]"
                ox_expr = f"(main_w*{pos_x:.3f}-overlay_w/2)"
                oy_expr = f"(main_h*{pos_y:.3f}-overlay_h/2)"
                overlay_opts = f"x='{ox_expr}':y='{oy_expr}':enable='between(t,{start_t:.3f},{end_t:.3f})'"
                if is_video:
                    overlay_opts += ":eof_action=pass"
                filter_complex_parts.append(f"{current_video_label}{layer_ready_label}overlay={overlay_opts}{next_video_label}")
                current_video_label = next_video_label

            # Note: All text layers and caption cues are now rendered as unified RGBA overlays above.
            # We do NOT append text_filter or ass_filter here to strictly prevent double rendering.


            audio_idx = input_args.count("-i")
            audio_args: List[str] = []
            if speech_audio_path and speech_audio_path.exists():
                audio_args.extend(["-i", str(speech_audio_path)])
            else:
                audio_args.extend(["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"])

            cmd_args = ["-y"]
            cmd_args.extend(input_args)
            cmd_args.extend(audio_args)
            cmd_args.extend(["-filter_complex", ";".join(filter_complex_parts)])
            cmd_args.extend(["-map", current_video_label])
            cmd_args.extend(["-map", f"{audio_idx}:a:0"])
            cmd_args.extend([
                "-c:v", "libx264",
                "-preset", "fast",
                "-pix_fmt", "yuv420p",
                "-r", str(canvas.fps),
                "-c:a", "aac",
                "-b:a", "192k",
                "-ar", "48000",
                "-ac", "2",
                "-t", f"{scene_duration:.3f}",
                str(output_clip_path),
            ])

        else:
            # SINGLE-TRACK BACKGROUND ONLY (No Avatar, No Media Layers)
            video_filters: List[str] = []
            if bg_scale_filter:
                video_filters.append(bg_scale_filter)
            if camera_motion == "slow_zoom_in":
                video_filters.append(f"zoompan=z='min(zoom+0.0006,1.06)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={canvas.width}x{canvas.height}:fps={canvas.fps}")
            elif camera_motion == "slow_zoom_out":
                video_filters.append(f"zoompan=z='if(lte(zoom,1.0),1.06,max(1.001,zoom-0.0006))':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={canvas.width}x{canvas.height}:fps={canvas.fps}")
            if text_filter:
                video_filters.append(text_filter)
            if ass_filter:
                video_filters.append(ass_filter)
            if drawtext_filter:
                video_filters.append(drawtext_filter)

            audio_args = []
            if speech_audio_path and speech_audio_path.exists():
                audio_args.extend(["-i", str(speech_audio_path)])
            else:
                audio_args.extend(["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"])

            cmd_args = ["-y"]
            cmd_args.extend(input_args)
            cmd_args.extend(audio_args)
            if video_filters:
                cmd_args.extend(["-vf", ",".join(video_filters)])

            cmd_args.extend([
                "-c:v", "libx264",
                "-preset", "fast",
                "-pix_fmt", "yuv420p",
                "-r", str(canvas.fps),
                "-c:a", "aac",
                "-b:a", "192k",
                "-ar", "48000",
                "-ac", "2",
                "-t", f"{scene_duration:.3f}",
                str(output_clip_path),
            ])

        # Execute scene render
        await self.ffmpeg_service.execute_ffmpeg(cmd_args)

        # Validate clip
        await self.ffprobe_service.validate_render_output(
            output_clip_path,
            min_duration=0.1,
            require_video=True,
            require_audio=True,
        )

        return output_clip_path

    async def _concatenate_scene_clips(
        self,
        scene_clips: List[Path],
        output_path: Path,
        mws: MediaWorkspace,
        scenes: Optional[List[Any]] = None,
        fps: int = 30,
    ) -> None:
        """Concatenate rendered scene clips with transition-aware composition (Phase 42C-2).

        Preserves fast-path concat demuxer/filter if all transitions are hard cuts ('none' or None).
        For projects with configured transitions ('fade', 'wipeleft', 'dissolve', 'slideleft'):
        - Probes actual rendered clip durations.
        - Clamps transition durations safely relative to rendered clip boundaries.
        - Dynamically tracks assembled timeline duration for exact transition offset calculation.
        - Chains xfade video and acrossfade audio for transitions, or concat for hard cuts.
        """
        num_clips = len(scene_clips)
        if num_clips == 0:
            return

        # 1. Probe actual rendered durations of each clip
        clip_durations: List[float] = []
        for clip in scene_clips:
            try:
                probe = await self.ffprobe_service.probe(clip)
                dur = probe.duration_seconds if (probe.duration_seconds and probe.duration_seconds > 0) else 5.0
            except Exception as e:
                logger.warning("Could not probe clip duration for %s: %s; falling back to 5.0s", clip, e)
                dur = 5.0
            clip_durations.append(dur)

        # 2. Inspect transition configurations for boundaries 1..(num_clips-1)
        # scenes[0].transition is ignored (first scene has no incoming transition)
        has_any_transition = False
        transitions_info: List[Dict[str, Any]] = []

        for i in range(1, num_clips):
            sc = scenes[i] if (scenes and i < len(scenes)) else None
            tr = getattr(sc, "transition", None) if sc else None
            tr_type = getattr(tr, "type", None) if tr else (tr.get("type") if isinstance(tr, dict) else None)
            tr_dur = float(getattr(tr, "duration", 0.5) if tr else (tr.get("duration", 0.5) if isinstance(tr, dict) else 0.5))

            xfade_type = map_transition_to_xfade(tr_type)
            if xfade_type is not None and tr_dur > 0.05:
                # Clamp transition duration to available durations
                # Must be strictly less than previous clip duration and incoming clip duration
                prev_dur = clip_durations[i - 1]
                curr_dur = clip_durations[i]
                max_allowed = max(0.0, min(prev_dur - 0.05, curr_dur - 0.05, (prev_dur + curr_dur) / 2.0))
                effective_dur = min(tr_dur, max_allowed)
                if effective_dur >= 0.05:
                    transitions_info.append({
                        "is_transition": True,
                        "xfade_type": xfade_type,
                        "duration": round(effective_dur, 3),
                    })
                    has_any_transition = True
                    continue

            # Hard cut
            transitions_info.append({
                "is_transition": False,
                "xfade_type": None,
                "duration": 0.0,
            })

        # 3. Fast Path: All boundaries are hard cuts
        if not has_any_transition:
            manifest_file = mws.scenes_dir / "concat_manifest.txt"
            manifest_lines = [f"file '{clip.resolve().as_posix()}'" for clip in scene_clips]
            manifest_file.write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")

            # Attempt fast stream copy concat demuxer
            demuxer_args = [
                "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(manifest_file),
                "-c", "copy",
                str(output_path),
            ]
            try:
                await self.ffmpeg_service.execute_ffmpeg(demuxer_args)
                if output_path.exists() and output_path.stat().st_size > 100:
                    return
            except Exception as demuxer_err:
                logger.warning("Concat demuxer failed (%s); falling back to filtergraph concat", demuxer_err)

            # Fallback: re-encode concat filter
            filter_inputs: List[str] = []
            filter_segments: List[str] = []
            for i, clip in enumerate(scene_clips):
                filter_inputs.extend(["-i", str(clip)])
                filter_segments.append(f"[{i}:v:0][{i}:a:0]")

            filtergraph = f"{''.join(filter_segments)}concat=n={num_clips}:v=1:a=1[vcat][acat]"
            fallback_args = [
                "-y",
                *filter_inputs,
                "-filter_complex", filtergraph,
                "-map", "[vcat]",
                "-map", "[acat]",
                "-c:v", "libx264",
                "-preset", "fast",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-b:a", "192k",
                "-ar", "48000",
                "-ac", "2",
                str(output_path),
            ]
            await self.ffmpeg_service.execute_ffmpeg(fallback_args)
            return

        # 4. Transition-aware multi-scene assembly pipeline
        # Build progressive filtergraph with dynamic assembled timeline tracking
        input_args: List[str] = []
        for clip in scene_clips:
            input_args.extend(["-i", str(clip)])

        filter_chains: List[str] = []
        for i in range(num_clips):
            filter_chains.append(f"[{i}:v:0]format=yuv420p,settb=AVTB,fps={fps}[v{i}]")

        current_v = "v0"
        current_a = "0:a:0"
        assembled_dur = clip_durations[0]

        for i in range(1, num_clips):
            tr_info = transitions_info[i - 1]
            next_v = f"v{i}"
            next_a = f"{i}:a:0"
            next_dur = clip_durations[i]

            out_v = f"v_step_{i}"
            out_a = f"a_step_{i}"

            if tr_info["is_transition"]:
                eff_dur = tr_info["duration"]
                offset = max(0.0, assembled_dur - eff_dur)
                xfade_filter = (
                    f"[{current_v}][{next_v}]"
                    f"xfade=transition={tr_info['xfade_type']}:duration={eff_dur:.3f}:offset={offset:.3f},"
                    f"format=yuv420p,settb=AVTB,fps={fps}[{out_v}]"
                )
                acrossfade_filter = (
                    f"[{current_a}][{next_a}]acrossfade=d={eff_dur:.3f}:c1=tri:c2=tri[{out_a}]"
                )
                filter_chains.append(xfade_filter)
                filter_chains.append(acrossfade_filter)
                assembled_dur = assembled_dur + next_dur - eff_dur
            else:
                # True hard cut via concat
                concat_v = f"[{current_v}][{next_v}]concat=n=2:v=1:a=0,settb=AVTB,fps={fps}[{out_v}]"
                concat_a = f"[{current_a}][{next_a}]concat=n=2:v=0:a=1[{out_a}]"
                filter_chains.append(concat_v)
                filter_chains.append(concat_a)
                assembled_dur = assembled_dur + next_dur

            current_v = out_v
            current_a = out_a

        full_filtergraph = ";".join(filter_chains)
        transition_cmd = [
            "-y",
            *input_args,
            "-filter_complex", full_filtergraph,
            "-map", f"[{current_v}]",
            "-map", f"[{current_a}]",
            "-c:v", "libx264",
            "-preset", "fast",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-ar", "48000",
            "-ac", "2",
            str(output_path),
        ]
        await self.ffmpeg_service.execute_ffmpeg(transition_cmd)


    async def _mix_background_audio(
        self,
        assembly_path: Path,
        audio_tracks: List[Any],
        output_path: Path,
        workspace_id: Union[str, uuid.UUID],
        db: AsyncSession,
        mws: MediaWorkspace,
    ) -> None:
        """Mix background music or sound effect tracks into the assembled video."""
        if not audio_tracks:
            shutil.copy2(assembly_path, output_path)
            return

        # 1. Filter tracks that have an asset_id and are not muted
        candidate_tracks = []
        for t in audio_tracks:
            track_asset_id = getattr(t, "asset_id", None) or (t.get("asset_id") if isinstance(t, dict) else None)
            muted = bool(getattr(t, "muted", False) if hasattr(t, "muted") else (t.get("muted", False) if isinstance(t, dict) else False))
            vol = float(getattr(t, "volume", 0.3) if hasattr(t, "volume") else (t.get("volume", 0.3) if isinstance(t, dict) else 0.3))
            if track_asset_id and not muted and vol > 0.0:
                candidate_tracks.append((t, track_asset_id, vol))

        if not candidate_tracks:
            # No audible background music tracks; pass through video assembly directly
            shutil.copy2(assembly_path, output_path)
            return

        # 2. Resolve media files from MinIO
        resolved_tracks = []
        for track_obj, asset_id, vol in candidate_tracks:
            try:
                bg_audio_path = await mws.resolve_asset(
                    asset_id=asset_id,
                    workspace_id=workspace_id,
                    db=db,
                )
                if bg_audio_path and bg_audio_path.exists():
                    st = float(getattr(track_obj, "start_time", 0.0) if hasattr(track_obj, "start_time") else (track_obj.get("start_time", 0.0) if isinstance(track_obj, dict) else 0.0))
                    loop = bool(getattr(track_obj, "loop", True) if hasattr(track_obj, "loop") else (track_obj.get("loop", True) if isinstance(track_obj, dict) else True))
                    resolved_tracks.append((track_obj, bg_audio_path, vol, st, loop))
            except Exception as e:
                logger.warning("Could not resolve background audio asset %s: %s; skipping track", asset_id, e)

        if not resolved_tracks:
            shutil.copy2(assembly_path, output_path)
            return

        # 3. Probe assembly duration to guarantee output is strictly bounded by video
        target_duration: Optional[float] = None
        try:
            probe = await self.ffprobe_service.probe(assembly_path)
            if probe.duration_seconds and probe.duration_seconds > 0.0:
                target_duration = probe.duration_seconds
        except Exception as probe_err:
            logger.warning("Could not probe assembly duration for audio mixing: %s", probe_err)

        # 4. Construct input arguments & filtergraph
        input_args = ["-y", "-i", str(assembly_path)]
        filter_chains = ["[0:a]volume=1.0[v0]"]
        mix_inputs = ["[v0]"]

        for idx, (_, bg_path, vol, st, loop) in enumerate(resolved_tracks, start=1):
            if loop:
                input_args.extend(["-stream_loop", "-1", "-i", str(bg_path)])
            else:
                input_args.extend(["-i", str(bg_path)])

            vol_filter = build_audio_volume(vol)
            if st > 0.0:
                delay_ms = int(st * 1000)
                vol_filter = f"{vol_filter},adelay={delay_ms}|{delay_ms}"

            filter_chains.append(f"[{idx}:a]{vol_filter}[v{idx}]")
            mix_inputs.append(f"[v{idx}]")

        total_audio_inputs = len(mix_inputs)
        filter_chains.append(
            f"{''.join(mix_inputs)}{build_audio_amix(inputs_count=total_audio_inputs, duration_mode='first')}[aout]"
        )
        mix_filter = ";".join(filter_chains)

        mix_args = [
            *input_args,
            "-filter_complex", mix_filter,
            "-map", "0:v",
            "-map", "[aout]",
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-ar", "48000",
            "-ac", "2",
            "-shortest",
        ]
        if target_duration is not None:
            mix_args.extend(["-t", f"{target_duration:.3f}"])
        mix_args.append(str(output_path))

        try:
            await self.ffmpeg_service.execute_ffmpeg(mix_args)
        except Exception as mix_err:
            logger.warning("Background audio mixing failed: %s; falling back to assembly video", mix_err)
            shutil.copy2(assembly_path, output_path)
