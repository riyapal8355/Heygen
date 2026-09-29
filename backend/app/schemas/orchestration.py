"""Pydantic schemas for Video Project AI Orchestration & Timeline Synthesis Engine."""

import uuid
from typing import Any, List, Literal, Optional
from pydantic import BaseModel, Field, field_validator


class GenerateProjectRequest(BaseModel):
    """Payload for natural language prompt-to-project generation via Video Agent."""
    prompt: str = Field(..., min_length=1, max_length=5000, description="Natural language project prompt")
    target_duration_seconds: Optional[float] = Field(30.0, ge=1.0, le=14400.0, description="Desired total video duration")
    aspect_ratio: Literal["16:9", "9:16", "1:1"] = Field("16:9", description="Aspect ratio canvas format")
    avatar_id: Optional[str] = Field(None, description="Optional default catalog avatar ID")
    voice_id: Optional[str] = Field(None, description="Optional default catalog voice ID")
    brand_kit_id: Optional[uuid.UUID] = Field(None, description="Optional brand kit for color scheme and styling")
    video_tone: str = Field("Professional", description="Video tone (Professional, Energetic, Casual, Educational)")
    auto_synthesize_speech: bool = Field(False, description="Whether to kick off async speech synthesis immediately")
    run_async: bool = Field(False, description="Whether to run generation asynchronously via Celery job")
    provider: Optional[str] = Field(None, description="Optional LLM provider override ('qwen', 'mock')")
    device: Optional[str] = Field(None, description="Optional compute device override ('cpu', 'cuda')")
    idempotency_key: Optional[str] = Field(None, description="Optional idempotency key for async task deduplication")

    @field_validator("prompt", mode="before")
    @classmethod
    def normalize_prompt(cls, v: Any) -> str:
        if not isinstance(v, str) or not v.strip():
            raise ValueError("Prompt must not be empty.")
        return v.strip()

    @field_validator("target_duration_seconds", mode="before")
    @classmethod
    def normalize_duration(cls, v: Any) -> float:
        from app.core.config import get_settings
        cfg = get_settings()
        min_dur = getattr(cfg, "MIN_VIDEO_DURATION_SECONDS", 5.0)
        max_dur = getattr(cfg, "MAX_VIDEO_DURATION_SECONDS", 3600.0)

        if v is None or v == "":
            return 30.0
        try:
            val = float(v)
            if val <= 0:
                return 30.0
            if val < min_dur:
                return min_dur
            if val > max_dur:
                return max_dur
            return round(val, 2)
        except (ValueError, TypeError):
            return 30.0

    @field_validator("aspect_ratio", mode="before")
    @classmethod
    def normalize_aspect_ratio(cls, v: Any) -> str:
        if not v:
            return "16:9"
        v_str = str(v).strip().lower()
        if v_str in ("16:9", "16/9", "horizontal", "landscape", "wide"):
            return "16:9"
        if v_str in ("9:16", "9/16", "vertical", "portrait", "story"):
            return "9:16"
        if v_str in ("1:1", "1/1", "square"):
            return "1:1"
        return "16:9"

    @field_validator("brand_kit_id", mode="before")
    @classmethod
    def normalize_brand_kit_id(cls, v: Any) -> Optional[uuid.UUID]:
        if v is None or (isinstance(v, str) and not v.strip()):
            return None
        if isinstance(v, str):
            try:
                return uuid.UUID(v.strip())
            except (ValueError, TypeError):
                return None
        return v

    @field_validator("avatar_id", "voice_id", "provider", "device", "idempotency_key", mode="before")
    @classmethod
    def empty_string_to_none(cls, v: Any) -> Optional[str]:
        if v is None or (isinstance(v, str) and not v.strip()):
            return None
        return str(v).strip()


class SynthesizeProjectSpeechRequest(BaseModel):
    """Payload for batch or selective scene speech synthesis."""
    scene_ids: Optional[List[str]] = Field(None, description="Target scene IDs; None means all scenes with speech text")
    expected_revision: int = Field(..., ge=1, description="Required current revision for optimistic concurrency check")
    voice_id_override: Optional[str] = Field(None, description="Optional voice ID override for target scenes")
    run_async: bool = Field(True, description="Canonical execution mode: async via Celery job")
    idempotency_key: Optional[str] = Field(None, description="Optional idempotency key for async task deduplication")

    @field_validator("voice_id_override", "idempotency_key", mode="before")
    @classmethod
    def empty_string_to_none(cls, v: Any) -> Optional[str]:
        if v is None or (isinstance(v, str) and not v.strip()):
            return None
        return str(v).strip()


class TranslateProjectRequest(BaseModel):
    """Payload for multi-scene project localization and video translation."""
    target_language: str = Field("es", min_length=2, max_length=16, description="Target language code (e.g. 'es', 'fr', 'de')")
    target_languages: Optional[List[str]] = Field(None, description="Optional multi-language targets for multi-output translation")
    source_language: str = Field("en", min_length=2, max_length=16, description="Source language code")
    target_voice_id: Optional[str] = Field(None, description="Optional voice ID matching target language")
    video_asset_id: Optional[str] = Field(None, description="Optional source video asset UUID for direct video dubbing")
    enable_subtitles: bool = Field(True, description="Generate and embed translated subtitles")
    enable_lip_sync: bool = Field(False, description="Apply lip-sync synchronization")
    enable_voice_clone: bool = Field(False, description="Apply voice cloning to target audio")
    glossary_id: Optional[str] = Field(None, description="Brand Glossary UUID to enforce")
    create_fork: bool = Field(True, description="Create new project fork vs new version on same project")
    expected_revision: Optional[int] = Field(None, ge=1, description="Required when create_fork=False")
    run_async: bool = Field(True, description="Canonical execution mode: async via Celery job")
    idempotency_key: Optional[str] = Field(None, description="Optional idempotency key")

    @field_validator("target_voice_id", "video_asset_id", "glossary_id", "idempotency_key", mode="before")
    @classmethod
    def empty_string_to_none(cls, v: Any) -> Optional[str]:
        if v is None or (isinstance(v, str) and not v.strip()):
            return None
        return str(v).strip()


class RenderProjectRequest(BaseModel):
    """Payload for composite video rendering export."""
    resolution: Literal["720p", "1080p", "4k"] = Field("1080p", description="Output render resolution")
    fps: int = Field(30, ge=15, le=60, description="Video framerate")
    export_format: Literal["mp4", "webm"] = Field("mp4", description="Output video format")
    expected_revision: int = Field(..., ge=1, description="Required exact project revision to freeze and render")
    idempotency_key: Optional[str] = Field(None, description="Optional idempotency key")


class TimelineValidationResponse(BaseModel):
    """Diagnostic response evaluating project timeline readiness for rendering."""
    is_valid: bool = Field(..., description="Whether project passes all pre-flight checks")
    scene_count: int = Field(..., description="Number of scenes in the project timeline")
    total_duration: float = Field(..., description="Calculated total duration in seconds")
    errors: List[str] = Field(default_factory=list, description="Fatal blocking issues that prevent rendering")
    warnings: List[str] = Field(default_factory=list, description="Non-blocking recommendations")


class GenerateSceneVisualRequest(BaseModel):
    """Payload for generating background or b-roll visuals for a specific scene."""
    visual_type: Literal["image", "video"] = Field("image", description="Visual media type to generate")
    prompt: str = Field(..., min_length=3, max_length=1000, description="Visual description prompt")
    aspect_ratio: Literal["16:9", "9:16", "1:1"] = Field("16:9", description="Asset aspect ratio")
    expected_revision: int = Field(..., ge=1, description="Required current revision for optimistic concurrency check")
    provider: Optional[str] = Field(None, description="Optional provider override ('stable_diffusion' or 'mock')")
    negative_prompt: Optional[str] = Field(None, max_length=1000, description="Excluded visual concepts")
    seed: Optional[int] = Field(None, description="Deterministic generation seed")
    run_async: bool = Field(True, description="Canonical execution mode: async via Celery job")
    idempotency_key: Optional[str] = Field(None, description="Optional idempotency key")


class TranscribeProjectAudioRequest(BaseModel):
    """Payload for transcribing scene speech audio into subtitles and text."""
    expected_revision: int = Field(..., ge=1, description="Required current project revision for optimistic concurrency check")
    scene_id: Optional[str] = Field(None, description="Optional target scene ID; if None, targets first scene with audio")
    audio_asset_id: Optional[uuid.UUID] = Field(None, description="Optional direct audio asset ID override")
    language: Optional[str] = Field(None, max_length=16, description="Optional language hint (e.g. 'en')")
    provider: Optional[str] = Field(None, description="Optional provider override ('whisper' or 'mock')")
    run_async: bool = Field(True, description="Canonical execution mode: async via Celery job")
    idempotency_key: Optional[str] = Field(None, description="Optional idempotency key for deduplication")


class GenerateAvatarVideoRequest(BaseModel):
    """Payload for generating neural lip-synced avatar video for a scene."""
    expected_revision: int = Field(..., ge=1, description="Required current project revision for optimistic concurrency check")
    scene_id: Optional[str] = Field(None, description="Optional target scene ID; if None, targets first scene with avatar")
    avatar_id_override: Optional[str] = Field(None, description="Optional avatar ID or asset ID override")
    provider: Optional[str] = Field(None, description="Optional provider override ('wav2lip', 'musetalk', 'mock')")
    device: Optional[str] = Field(None, description="Optional device target ('cpu', 'cuda')")
    run_async: bool = Field(True, description="Canonical execution mode: async via Celery job (HTTP 202)")
    idempotency_key: Optional[str] = Field(None, description="Optional idempotency key for deduplication")

    @field_validator("scene_id", "avatar_id_override", "provider", "device", "idempotency_key", mode="before")
    @classmethod
    def empty_string_to_none(cls, v: Any) -> Optional[str]:
        if v is None or (isinstance(v, str) and not v.strip()):
            return None
        return str(v).strip()


class EnhanceProjectSpeechRequest(BaseModel):
    """Payload for neural audio enhancement and studio speech cleanup."""
    expected_revision: int = Field(..., ge=1, description="Required current project revision for optimistic concurrency check")
    scene_id: Optional[str] = Field(None, description="Optional target scene ID; if None, targets all scenes with speech")
    denoise: bool = Field(True, description="Enable neural noise suppression")
    remove_silence: bool = Field(False, description="Enable Silero VAD dead-pause trimming")
    remove_fillers: bool = Field(False, description="Filler removal toggle (disabled/NOT_IMPLEMENTED)")
    master_audio: bool = Field(True, description="Apply broadcast EQ, compression, and loudness mastering")
    provider: Optional[str] = Field(None, description="Optional provider override ('deepfilter' or 'mock')")
    run_async: bool = Field(True, description="Canonical execution mode: async via Celery job (HTTP 202)")
    idempotency_key: Optional[str] = Field(None, description="Optional idempotency key for deduplication")

    @field_validator("scene_id", "provider", "idempotency_key", mode="before")
    @classmethod
    def empty_string_to_none(cls, v: Any) -> Optional[str]:
        if v is None or (isinstance(v, str) and not v.strip()):
            return None
        return str(v).strip()



