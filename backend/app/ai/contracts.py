"""Vendor-independent AI and media execution contracts.

Provides strongly-typed Pydantic V2 models for input requests and output results across
all generative, audio, visual, and timeline rendering workloads.
Shields the HeyZen domain and job pipeline from provider-specific APIs.
"""

import uuid
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class MediaAssetRef(BaseModel):
    """Reference to an existing storage object or database asset."""

    model_config = ConfigDict(extra="forbid")

    asset_id: Optional[uuid.UUID] = Field(None, description="Database asset identifier")
    storage_key: Optional[str] = Field(None, description="Object storage key in MinIO/S3")
    mime_type: Optional[str] = Field(None, description="MIME content type")


class AIContractRequest(BaseModel):
    """Base request contract carrying multi-tenant boundary and execution context."""

    model_config = ConfigDict(extra="allow")

    job_id: Optional[uuid.UUID] = Field(None, description="Durable job tracking identifier")
    workspace_id: uuid.UUID = Field(..., description="Owning workspace boundary")
    user_id: uuid.UUID = Field(..., description="Initiating user identifier")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary execution metadata")


class AIContractResult(BaseModel):
    """Base result contract carrying output asset references and execution telemetry."""

    model_config = ConfigDict(extra="allow")

    status: Literal["succeeded", "failed"] = Field("succeeded", description="Terminal execution outcome")
    output_asset_id: Optional[uuid.UUID] = Field(None, description="Database Asset record identifier")
    output_storage_key: Optional[str] = Field(None, description="S3/MinIO key of generated binary")
    duration_seconds: Optional[float] = Field(None, ge=0.0, description="Runtime duration in seconds if media")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Performance and compute metrics")


# =============================================================================
# 1. Text-to-Speech (TTS) Contracts
# =============================================================================

class TTSContractRequest(AIContractRequest):
    """Execution contract for synthesizing spoken audio from text."""

    text: str = Field(..., min_length=1, max_length=20000, description="Spoken script text")
    voice_id: str = Field(..., min_length=1, description="Target voice identifier or cloned model ID")
    speed: float = Field(1.0, ge=0.5, le=2.0, description="Speech playback speed multiplier")
    pitch: float = Field(0.0, ge=-20.0, le=20.0, description="Semitone pitch shift")
    output_format: Literal["wav", "mp3", "aac"] = Field("wav", description="Audio container format")
    pronunciation_rules: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Brand kit phonetic substitution rules: [{'term': 'X', 'replacement_phonetic': 'Y'}]",
    )


class TTSContractResult(AIContractResult):
    """Execution result for synthesized speech audio."""

    sample_rate: int = Field(24000, description="Audio sampling rate in Hz")
    channels: int = Field(1, description="Audio channel count (1=mono, 2=stereo)")
    word_count: int = Field(..., ge=0, description="Total spoken word count")
    word_timestamps: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Timestamped word alignment: [{'word': str, 'start': float, 'end': float}]",
    )


# =============================================================================
# 2. Automated Speech Recognition (ASR) Contracts
# =============================================================================

class ASRContractRequest(AIContractRequest):
    """Execution contract for transcribing audio to text."""

    audio_asset: MediaAssetRef = Field(..., description="Source audio asset to transcribe")
    language: Optional[str] = Field(None, max_length=16, description="Expected ISO language code (e.g. 'en', 'es')")
    include_word_timestamps: bool = Field(True, description="Whether to compute granular per-word timings")


class ASRContractResult(AIContractResult):
    """Execution result for speech transcription."""

    detected_language: str = Field("en", description="Identified language code")
    full_text: str = Field(..., description="Full transcribed text corpus")
    segments: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Timestamped sentence/phrase segments: [{'id': int, 'start': float, 'end': float, 'text': str}]",
    )


# =============================================================================
# 3. Translation Contracts
# =============================================================================

class TranslationContractRequest(AIContractRequest):
    """Execution contract for text and script translation with glossary enforcement."""

    text: str = Field(..., min_length=1, description="Source script text to translate")
    source_language: str = Field("en", max_length=16, description="Source ISO language code")
    target_language: str = Field(..., max_length=16, description="Target ISO language code")
    glossary_rules: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Brand terminology override rules: [{'term': 'X', 'translated_term': 'Y'}]",
    )


class TranslationContractResult(AIContractResult):
    """Execution result for translated text and aligned segments."""

    source_language: str = Field(..., description="Confirmed source language code")
    target_language: str = Field(..., description="Confirmed target language code")
    translated_text: str = Field(..., description="Fully translated text content")
    segments: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Aligned translation segments",
    )


# =============================================================================
# 4. Neural Lip-Sync Contracts
# =============================================================================

class LipSyncContractRequest(AIContractRequest):
    """Execution contract for audio-driven neural avatar facial animation."""

    avatar_look_asset: MediaAssetRef = Field(..., description="Base avatar look plate (image or video asset)")
    audio_asset: MediaAssetRef = Field(..., description="Driving speech audio asset")
    output_format: Literal["mp4", "webm"] = Field("mp4", description="Output video format")
    resolution: str = Field("1080p", description="Output target resolution: 720p, 1080p, 4k")
    fps: int = Field(30, ge=15, le=60, description="Target frame rate")


class LipSyncContractResult(AIContractResult):
    """Execution result for generated lip-sync video."""

    resolution: str = Field("1920x1080", description="Rendered pixel dimensions")
    fps: int = Field(30, description="Output frame rate")
    frame_count: int = Field(..., ge=0, description="Total rendered video frames")


# =============================================================================
# 5. Generative Image Contracts
# =============================================================================

class ImageGenContractRequest(AIContractRequest):
    """Execution contract for generative background and still visual creation."""

    prompt: str = Field(..., min_length=1, max_length=2000, description="Visual description prompt")
    aspect_ratio: Literal["16:9", "9:16", "1:1", "4:3", "21:9"] = Field("16:9", description="Target aspect ratio")
    negative_prompt: Optional[str] = Field(None, max_length=1000, description="Excluded visual concepts")
    output_format: Literal["png", "jpg", "webp"] = Field("png", description="Image container format")


class ImageGenContractResult(AIContractResult):
    """Execution result for generated image asset."""

    width: int = Field(..., ge=128, description="Image pixel width")
    height: int = Field(..., ge=128, description="Image pixel height")
    aspect_ratio: str = Field(..., description="Actual aspect ratio")


# =============================================================================
# 6. Generative Video & Timeline Rendering Contracts
# =============================================================================

class VideoGenContractRequest(AIContractRequest):
    """Execution contract for generative AI video b-roll and motion clips."""

    prompt: str = Field(..., min_length=1, max_length=2000, description="Video motion prompt")
    duration_seconds: float = Field(4.0, ge=1.0, le=30.0, description="Target clip duration")
    aspect_ratio: Literal["16:9", "9:16", "1:1"] = Field("16:9", description="Video canvas ratio")
    output_format: Literal["mp4", "webm"] = Field("mp4", description="Video container format")


class VideoGenContractResult(AIContractResult):
    """Execution result for generative video clip."""

    resolution: str = Field("1920x1080", description="Video resolution")
    fps: int = Field(30, description="Frame rate")


class VideoRenderContractRequest(AIContractRequest):
    """Execution contract for rendering full composite project timeline."""

    project_id: uuid.UUID = Field(..., description="Target project to render")
    project_version_id: Optional[uuid.UUID] = Field(None, description="Specific revision snapshot to render")
    resolution: Literal["720p", "1080p", "4k"] = Field("1080p", description="Output export resolution")
    fps: int = Field(30, ge=15, le=60, description="Export frame rate")
    export_format: Literal["mp4", "webm"] = Field("mp4", description="Output container format")


class VideoRenderContractResult(AIContractResult):
    """Execution result for completed video composition export."""

    resolution: str = Field("1920x1080", description="Rendered video resolution")
    fps: int = Field(30, description="Frame rate")
    size_bytes: int = Field(..., ge=0, description="Rendered file byte size")
    thumbnail_asset_id: Optional[uuid.UUID] = Field(None, description="Generated poster frame asset")


# =============================================================================
# 7. Large Language Model (LLM) Video Agent Contracts
# =============================================================================

class LLMContractRequest(AIContractRequest):
    """Execution contract for video agent prompt decomposition and script generation."""

    prompt: str = Field(..., min_length=1, max_length=5000, description="User video concept or prompt")
    system_prompt: Optional[str] = Field(None, max_length=2000, description="Optional system-level instructions")
    target_scenes: int = Field(3, ge=1, le=100, description="Target number of scenes to generate")
    target_duration_seconds: float = Field(30.0, ge=1.0, le=14400.0, description="Target total video duration")
    video_tone: str = Field("professional", description="Desired tone: professional, casual, dramatic, energetic")
    aspect_ratio: str = Field("16:9", description="Target aspect ratio: 16:9, 9:16, 1:1")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="Sampling randomness temperature")
    max_new_tokens: int = Field(1024, ge=64, le=8192, description="Maximum completion tokens to generate")


class LLMContractResult(AIContractResult):
    """Execution result for generated video project structure and script."""

    title: str = Field(..., description="Generated video project title")
    script: str = Field(..., description="Complete aggregated spoken script")
    suggested_scenes: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Structured scene breakdowns: [{'sequence': int, 'duration': float, 'heading': str, 'text': str, 'visual_description': str}]",
    )
    prompt_tokens: int = Field(0, ge=0, description="Number of tokens in input prompt")
    completion_tokens: int = Field(0, ge=0, description="Number of generated completion tokens")
    generation_latency: float = Field(0.0, ge=0.0, description="Inference latency in seconds")
    tokens_per_second: float = Field(0.0, ge=0.0, description="Generation throughput in tokens per second")


# =============================================================================
# 8. Neural Human Matting & Background Removal Contracts
# =============================================================================

class MattingContractRequest(AIContractRequest):
    """Execution contract for extracting foreground alpha matte from video or portrait image."""

    media_asset: MediaAssetRef = Field(..., description="Source video or image asset to segment")
    output_format: Literal["matte_mask", "rgba_video", "png_mask"] = Field(
        "matte_mask",
        description="Desired alpha output container format",
    )
    threshold: float = Field(0.5, ge=0.0, le=1.0, description="Foreground segmentation confidence threshold")


class MattingContractResult(AIContractResult):
    """Execution result for neural human matting."""

    frame_count: int = Field(..., ge=0, description="Total processed video/image frames")
    width: int = Field(..., ge=1, description="Matte output width in pixels")
    height: int = Field(..., ge=1, description="Matte output height in pixels")
    fps: float = Field(30.0, description="Video frame rate if temporal sequence")
    processing_latency: float = Field(0.0, ge=0.0, description="Total matting latency in seconds")
    fps_throughput: float = Field(0.0, ge=0.0, description="Frame processing throughput (fps)")


# =============================================================================
# 9. Neural Audio Enhancement & Studio Speech Cleanup Contracts
# =============================================================================

class AudioEnhanceContractRequest(AIContractRequest):
    """Execution contract for neural speech cleanup and audio enhancement."""

    audio_asset: MediaAssetRef = Field(..., description="Source audio asset to enhance")
    remove_noise: bool = Field(True, description="Remove background hum, room reverb, fan noise")
    remove_fillers: bool = Field(False, description="Semantic filler removal (disabled/not implemented without lexical alignment)")
    trim_silence_pauses: bool = Field(True, description="Trim dead pauses longer than silence_threshold_seconds using VAD")
    silence_threshold_seconds: float = Field(1.2, ge=0.2, le=10.0, description="Pause duration threshold in seconds")
    apply_broadcast_eq: bool = Field(True, description="Apply studio warmth, vocal presence EQ, and limiter")
    output_format: Literal["wav", "mp3"] = Field("wav", description="Output container format")


class AudioEnhanceContractResult(AIContractResult):
    """Execution result for enhanced speech audio."""

    original_duration_seconds: float = Field(..., ge=0.0, description="Input audio duration in seconds")
    enhanced_duration_seconds: float = Field(..., ge=0.0, description="Cleaned audio duration in seconds")
    duration_reduction_seconds: float = Field(0.0, ge=0.0, description="Total dead air trimmed in seconds")
    pauses_trimmed_count: int = Field(0, ge=0, description="Count of silent pauses trimmed")
    noise_reduction_db: float = Field(0.0, description="Estimated SNR noise reduction in dB")
    sample_rate: int = Field(48000, description="Master audio sample rate in Hz")
    channels: int = Field(2, description="Output audio channels (1=mono, 2=stereo)")
    fillers_status: str = Field("NOT_IMPLEMENTED", description="Status of semantic filler word removal")
    fillers_removed_count: int = Field(0, ge=0, description="Count of filler words removed")
    processing_latency: float = Field(0.0, ge=0.0, description="Total enhancement latency in seconds")
    real_time_factor: float = Field(0.0, ge=0.0, description="Processing Real-Time Factor (RTF)")



