"""Canonical Structured Project JSON Schema Definition.

Authoritative contract for ProjectDocumentV1 (PostgreSQL JSONB storage).
"""

from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, ConfigDict, Field, field_validator


class CaptionStyle(BaseModel):
    """Visual typography and placement styling for burned/displayed subtitles."""
    font_family: str = Field(default="Arial", description="Font family name")
    font_size: int = Field(default=48, ge=12, le=120, description="Font size in px")
    font_weight: str = Field(default="bold", description="normal or bold")
    color: str = Field(default="#FFFFFF", description="Text color hex")
    background_color: str = Field(default="#000000", description="Background box color hex")
    background_opacity: float = Field(default=0.6, ge=0.0, le=1.0, description="Background box opacity")
    position: str = Field(default="bottom", description="top, center, or bottom")
    alignment: str = Field(default="center", description="left, center, or right")
    z_index: Optional[int] = Field(default=None, description="Visual stacking order for captions (None defaults to frontmost)")


class CaptionSettings(BaseModel):
    """Project-level caption toggle and styling configuration."""
    enabled: bool = Field(default=True, description="Whether subtitles/captions are displayed and burned")
    style: CaptionStyle = Field(default_factory=CaptionStyle)


class ProjectSettings(BaseModel):
    """Core timeline and render canvas configuration."""
    aspect_ratio: str = Field(default="16:9", description="Canvas ratio: 16:9, 9:16, 1:1, etc.")
    width: int = Field(default=1920, ge=128, le=7680, description="Pixel width")
    height: int = Field(default=1080, ge=128, le=4320, description="Pixel height")
    fps: int = Field(default=30, ge=1, le=120, description="Render framerate")
    total_duration: float = Field(default=0.0, ge=0.0, description="Computed runtime in seconds")
    captions: CaptionSettings = Field(default_factory=CaptionSettings)


CanvasSettings = ProjectSettings


class AudioTrack(BaseModel):
    """Audio timeline track reference."""
    id: str = Field(..., description="Unique track ID")
    asset_id: Optional[str] = Field(default=None, description="Reference to assets.id in object storage")
    name: str = Field(default="Audio Track")
    volume: float = Field(default=1.0, ge=0.0, le=2.0)
    start_time: float = Field(default=0.0, ge=0.0)
    duration: Optional[float] = Field(default=None, ge=0.0)
    fade_in_duration: float = Field(default=0.0, ge=0.0)
    fade_out_duration: float = Field(default=0.0, ge=0.0)
    loop: bool = Field(default=False)
    muted: bool = Field(default=False, description="Whether audio track is muted")


class SceneTransition(BaseModel):
    """Transition visual effect into this scene."""
    type: str = Field(default="fade", description="Transition style: fade, wipe, dissolve, slide")
    duration: float = Field(default=0.5, ge=0.0, le=5.0)


class SceneAvatar(BaseModel):
    """Avatar actor configuration for talking video scenes."""
    avatar_id: str = Field(..., description="Reference to avatar model or identifier")
    look_id: Optional[str] = Field(default=None, description="Look/outfit identifier")
    position: Dict[str, float] = Field(
        default_factory=lambda: {"x": 0.5, "y": 0.65, "scale": 1.0, "rotation": 0.0}
    )
    view_mode: str = Field(default="half_body", description="half_body, close_up, circle")
    video_asset_id: Optional[str] = Field(
        default=None,
        description="Synthesized talking-avatar video asset reference in MinIO",
    )


class SceneSpeech(BaseModel):
    """Script and voice speech synthesis parameters."""
    voice_id: str = Field(..., description="Voice identifier")
    script: str = Field(default="", description="Text speech content")
    audio_asset_id: Optional[str] = Field(default=None, description="Pre-synthesized audio asset reference")
    speed: float = Field(default=1.0, ge=0.5, le=2.0)
    pitch: float = Field(default=0.0, ge=-20.0, le=20.0)


class SceneLayer(BaseModel):
    """Visual canvas layer (text, media, shape, sticker)."""
    id: str = Field(..., description="Unique layer ID")
    type: str = Field(..., description="Layer type: text, image, video, shape, sticker")
    name: str = Field(default="Layer")
    start_time: float = Field(default=0.0, ge=0.0)
    end_time: float = Field(default=5.0, ge=0.0)
    enabled: bool = Field(default=True, description="Layer visibility toggle")
    locked: bool = Field(default=False, description="Layer manipulation lock toggle")
    z_index: int = Field(default=0, description="Visual stacking order (lower is behind, higher is in front)")
    transform: Dict[str, Any] = Field(default_factory=dict)
    content: Dict[str, Any] = Field(default_factory=dict)


class SceneBackground(BaseModel):
    """Background visual configuration for a scene."""
    model_config = ConfigDict(extra="allow")

    type: str = Field(default="color", description="color, gradient, image, video")
    value: Optional[str] = Field(default="#0F172A", description="Color hex or asset reference")
    color: Optional[str] = Field(default=None, description="Primary color hex")
    gradient: Optional[str] = Field(default=None, description="CSS gradient expression")
    gradient_start: Optional[str] = Field(default=None, description="Start hex color")
    gradient_end: Optional[str] = Field(default=None, description="End hex color")
    gradient_colors: Optional[List[str]] = Field(default=None, description="Top and bottom gradient hex colors")
    asset_id: Optional[str] = Field(default=None, description="Media asset UUID")
    position: Optional[Dict[str, float]] = None
    scale: Optional[float] = 1.0
    effect: Optional[str] = None


class Scene(BaseModel):
    """Individual sequence cut in the video project."""
    id: str = Field(..., description="Unique scene UUID/string")
    sequence: int = Field(..., ge=1, description="1-indexed sequence order")
    duration: float = Field(default=5.0, ge=0.1, description="Scene length in seconds")
    transition: Optional[SceneTransition] = None
    camera_motion: Optional[str] = Field(
        default="static",
        description="Camera movement: static, slow_zoom_in, slow_zoom_out, pan_left, pan_right, presenter_closeup, presenter_medium, presenter_wide",
    )
    background: Union[SceneBackground, Dict[str, Any]] = Field(
        default_factory=lambda: {"type": "color", "value": "#0F172A"}
    )
    avatar: Optional[SceneAvatar] = None
    speech: Optional[SceneSpeech] = None
    layers: List[SceneLayer] = Field(default_factory=list)
    subtitles: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Timestamped speech transcription cues: [{'id': int, 'start': float, 'end': float, 'text': str, 'words': [...]}]",
    )


class DocumentAssetRef(BaseModel):
    """Manifest of media assets referenced in this project document."""
    asset_id: str = Field(..., description="UUID string of the asset")
    asset_type: str = Field(..., description="image, video, audio, font, other")
    storage_key: Optional[str] = None


class ProjectDocumentV1(BaseModel):
    """Canonical HeyZen Project Document specification (Version 1)."""
    schema_version: Literal[1] = Field(default=1, description="Schema version tag (must be 1 for V1)")
    settings: ProjectSettings = Field(default_factory=ProjectSettings)
    scenes: List[Scene] = Field(default_factory=list)
    audio_tracks: List[AudioTrack] = Field(default_factory=list)
    assets: List[DocumentAssetRef] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("schema_version")
    @classmethod
    def validate_schema_version(cls, v: int) -> int:
        if v != 1:
            raise ValueError(f"Unsupported schema_version: {v}. Expected 1.")
        return v


def create_default_project_document(
    aspect_ratio: str = "16:9",
    width: int = 1920,
    height: int = 1080,
    fps: int = 30,
    initial_title: Optional[str] = None,
) -> ProjectDocumentV1:
    """Factory creating an initialized, valid ProjectDocumentV1 with one default scene."""
    import uuid
    default_scene = Scene(
        id=str(uuid.uuid4()),
        sequence=1,
        duration=5.0,
        background={"type": "color", "value": "#0F172A"},
    )
    settings = ProjectSettings(
        aspect_ratio=aspect_ratio,
        width=width,
        height=height,
        fps=fps,
        total_duration=5.0,
    )
    metadata = {}
    if initial_title:
        metadata["title"] = initial_title

    return ProjectDocumentV1(
        schema_version=1,
        settings=settings,
        scenes=[default_scene],
        audio_tracks=[],
        assets=[],
        metadata=metadata,
    )
