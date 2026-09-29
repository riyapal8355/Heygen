"""Data models for media probe inspection, canvas dimensions, and rendering options."""

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class MediaStreamInfo(BaseModel):
    """Detailed stream metrics from ffprobe or synthetic container probe."""

    model_config = ConfigDict(extra="allow")

    index: int = Field(0, description="Stream index in container")
    codec_type: str = Field("video", description="video, audio, subtitle, attachment")
    codec_name: Optional[str] = Field(None, description="Codec identifier (e.g. h264, aac, png)")
    width: Optional[int] = Field(None, description="Visual width in pixels")
    height: Optional[int] = Field(None, description="Visual height in pixels")
    fps: Optional[float] = Field(None, description="Stream frame rate")
    sample_rate: Optional[int] = Field(None, description="Audio sample rate in Hz")
    channels: Optional[int] = Field(None, description="Audio channel count")
    bit_rate: Optional[int] = Field(None, description="Stream bit rate in bps")
    duration: Optional[float] = Field(None, description="Stream duration in seconds")


class MediaProbeResult(BaseModel):
    """Unified media container and stream inspection result."""

    model_config = ConfigDict(extra="allow")

    duration_seconds: float = Field(0.0, ge=0.0, description="Container media duration")
    format_name: str = Field("unknown", description="Container format name (e.g. 'mp4', 'wav', 'png')")
    size_bytes: int = Field(0, ge=0, description="Total file size in bytes")
    bit_rate: Optional[int] = Field(None, description="Average container bit rate")
    video_streams: List[Dict[str, Any]] = Field(default_factory=list, description="Visual stream descriptions")
    audio_streams: List[Dict[str, Any]] = Field(default_factory=list, description="Audio stream descriptions")
    width: Optional[int] = Field(None, description="Primary visual width in pixels")
    height: Optional[int] = Field(None, description="Primary visual height in pixels")
    fps: Optional[float] = Field(None, description="Primary visual frame rate")
    sample_rate: Optional[int] = Field(None, description="Primary audio sampling rate")
    channels: Optional[int] = Field(None, description="Primary audio channels")
    codec_name: Optional[str] = Field(None, description="Primary audio/video codec identifier")

    @property
    def has_audio(self) -> bool:
        """Return True if media contains at least one audio stream."""
        return len(self.audio_streams) > 0

    @property
    def has_video(self) -> bool:
        """Return True if media contains at least one visual/video stream."""
        return len(self.video_streams) > 0


class CanvasProfile(BaseModel):
    """Pixel dimension and aspect ratio mapping for timeline compositing."""

    width: int = Field(1920, ge=128, le=7680)
    height: int = Field(1080, ge=128, le=4320)
    aspect_ratio: str = Field("16:9")
    fps: int = Field(30, ge=15, le=60)

    @classmethod
    def from_aspect_ratio(cls, aspect_ratio: str, resolution: str = "1080p", fps: int = 30) -> "CanvasProfile":
        """Resolve deterministic canvas dimensions from standard aspect ratios and target resolutions."""
        ar = aspect_ratio.strip().lower()
        res = resolution.strip().lower()

        if ar == "9:16":
            # Vertical / Shorts / TikTok
            if res == "720p":
                return cls(width=720, height=1280, aspect_ratio="9:16", fps=fps)
            elif res == "4k":
                return cls(width=2160, height=3840, aspect_ratio="9:16", fps=fps)
            else:
                return cls(width=1080, height=1920, aspect_ratio="9:16", fps=fps)

        elif ar == "1:1":
            # Square / Instagram Feed
            if res == "720p":
                return cls(width=720, height=720, aspect_ratio="1:1", fps=fps)
            elif res == "4k":
                return cls(width=2160, height=2160, aspect_ratio="1:1", fps=fps)
            else:
                return cls(width=1080, height=1080, aspect_ratio="1:1", fps=fps)

        else:
            # Default 16:9 Landscape / YouTube
            if res == "720p":
                return cls(width=1280, height=720, aspect_ratio="16:9", fps=fps)
            elif res == "4k":
                return cls(width=3840, height=2160, aspect_ratio="16:9", fps=fps)
            else:
                return cls(width=1920, height=1080, aspect_ratio="16:9", fps=fps)


class RenderResult(BaseModel):
    """Encapsulates rendered output paths, verification metrics, and canvas dimensions."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    video_path: Any
    thumbnail_path: Any
    probe_result: MediaProbeResult
    canvas_profile: CanvasProfile
    total_duration: float = Field(0.0, ge=0.0)
    scenes_count: int = Field(1, ge=1)
    scene_clips: List[Any] = Field(default_factory=list)

