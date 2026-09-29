"""Vendor-independent AI provider protocol definitions.

In accordance with backend-architecture.md Section 10:
All neural network and LLM operations are decoupled from the API server.
These protocols define the abstract contract for future CPU/GPU worker implementations.
"""

from typing import Any, AsyncGenerator, Awaitable, Callable, Dict, List, Optional, Protocol, Tuple, runtime_checkable
from pydantic import BaseModel, Field

from app.ai.contracts import (
    ASRContractRequest,
    ASRContractResult,
    AudioEnhanceContractRequest,
    AudioEnhanceContractResult,
    ImageGenContractRequest,
    ImageGenContractResult,
    LipSyncContractRequest,
    LipSyncContractResult,
    MattingContractRequest,
    MattingContractResult,
    TranslationContractRequest,
    TranslationContractResult,
    TTSContractRequest,
    TTSContractResult,
    VideoGenContractRequest,
    VideoGenContractResult,
)


# --- Data Transfer Objects for AI I/O ---

class ScriptGenerationResult(BaseModel):
    title: str
    script: str
    suggested_scenes: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AudioSynthesisResult(BaseModel):
    audio_bytes: bytes
    sample_rate: int
    duration_seconds: float
    word_timestamps: List[Dict[str, Any]] = Field(default_factory=list)


class TranscriptionResult(BaseModel):
    detected_language: str
    full_text: str
    segments: List[Dict[str, Any]] = Field(default_factory=list)
    duration_seconds: Optional[float] = None
    confidence: Optional[float] = None


class TranslationResult(BaseModel):
    source_language: str
    target_language: str
    translated_text: str
    translated_segments: List[Dict[str, Any]] = Field(default_factory=list)


class MattingResult(BaseModel):
    alpha_storage_key: str
    width: int
    height: int
    frame_count: int
    fps: float = 30.0
    duration_seconds: float = 0.0
    metrics: Dict[str, Any] = Field(default_factory=dict)


class AudioEnhanceResult(BaseModel):
    audio_bytes: bytes
    original_duration_seconds: float
    enhanced_duration_seconds: float
    sample_rate: int = 48000
    channels: int = 2
    pauses_trimmed_count: int = 0
    noise_reduction_db: float = 0.0
    fillers_status: str = "NOT_IMPLEMENTED"
    fillers_removed_count: int = 0
    metrics: Dict[str, Any] = Field(default_factory=dict)

    @property
    def duration_seconds(self) -> float:
        return self.enhanced_duration_seconds

    @property
    def silence_trimmed_seconds(self) -> float:
        return max(0.0, round(self.original_duration_seconds - self.enhanced_duration_seconds, 3))

    @property
    def fillers_removed(self) -> int:
        return self.fillers_removed_count

    @property
    def mastered(self) -> bool:
        return True



# --- Protocols ---

@runtime_checkable
class LLMProvider(Protocol):
    """Abstract interface for large language model generation and video scripting."""

    async def generate_script(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> ScriptGenerationResult:
        """Generate structured video script from user prompt."""
        ...

    async def stream_script(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream script generation tokens asynchronously."""
        ...


@runtime_checkable
class TTSProvider(Protocol):
    """Abstract interface for text-to-speech synthesis and voice cloning."""

    async def synthesize_speech(
        self,
        text: str,
        voice_id: str,
        speed: float = 1.0,
        pitch: float = 0.0,
        pronunciation_rules: Optional[List[Dict[str, str]]] = None,
    ) -> AudioSynthesisResult:
        """Synthesize spoken audio from script text."""
        ...

    async def clone_voice(
        self,
        voice_name: str,
        sample_audio_keys: List[str],
        language: str = "en",
    ) -> str:
        """Create a custom cloned voice model from audio samples."""
        ...

    async def synthesize(
        self,
        request: TTSContractRequest,
    ) -> TTSContractResult:
        """Synthesize speech using strongly typed execution contract."""
        ...


@runtime_checkable
class ASRProvider(Protocol):
    """Abstract interface for automatic speech recognition and timestamped transcription."""

    async def transcribe_audio(
        self,
        audio_storage_key: str,
        language: Optional[str] = None,
    ) -> TranscriptionResult:
        """Transcribe audio into text and timestamped subtitle cues."""
        ...

    async def transcribe(
        self,
        request: ASRContractRequest,
    ) -> ASRContractResult:
        """Transcribe audio using strongly typed execution contract."""
        ...


@runtime_checkable
class TranslationProvider(Protocol):
    """Abstract interface for neural text and script translation with glossary enforcement."""

    async def translate_text(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        glossary_rules: Optional[List[Dict[str, str]]] = None,
    ) -> TranslationResult:
        """Translate text while respecting brand glossary rules."""
        ...

    async def translate(
        self,
        request: TranslationContractRequest,
    ) -> TranslationContractResult:
        """Translate text using strongly typed execution contract."""
        ...


@runtime_checkable
class AvatarProvider(Protocol):
    """Abstract interface for neural avatar rendering, digital twins, and lip-sync."""

    async def generate_lip_sync(
        self,
        avatar_look_key: str,
        audio_storage_key: str,
        output_format: str = "mp4",
    ) -> str:
        """Generate audio-driven lip-synchronized avatar video clip."""
        ...

    async def train_digital_twin(
        self,
        training_video_keys: List[str],
        avatar_name: str,
    ) -> str:
        """Train a personalized digital twin model from uploaded footage."""
        ...

    async def lip_sync(
        self,
        request: LipSyncContractRequest,
    ) -> LipSyncContractResult:
        """Generate lip-sync video using strongly typed execution contract."""
        ...


@runtime_checkable
class TalkingAvatarProvider(Protocol):
    """Abstract interface for talking avatar providers synthesizing speech-driven video."""

    async def generate_talking_video(
        self,
        avatar_image_bytes: bytes,
        audio_bytes: bytes,
        fps: int = 25,
        options: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Callable[[int, str], Awaitable[None]]] = None,
        cancellation_checker: Optional[Callable[[], Awaitable[bool]]] = None,
    ) -> Tuple[bytes, float, int]:
        """Generate talking presenter video with synchronized speech.

        Returns:
            Tuple of (mp4_bytes, duration_seconds, frame_count).
        """
        ...

    def capabilities(self) -> Dict[str, Any]:
        """Return provider capabilities (lip_sync, blinking, head_motion, idle_movement, device, etc.)."""
        ...

    def health_check(self) -> Tuple[bool, str]:
        """Verify model files and inference environment availability."""
        ...


@runtime_checkable
class AvatarMotionProvider(Protocol):
    """Abstract interface for neural avatar motion generation (e.g. LivePortrait).

    Responsible for generating high-fidelity neural portrait animation from a source avatar
    and real driving motion video.
    """

    def health_check(self) -> Tuple[bool, str]:
        """Verify model files and inference environment readiness."""
        ...

    def capabilities(self) -> Dict[str, Any]:
        """Return provider capabilities (head_rotation, eye_gaze, blinking, stitching, etc.)."""
        ...

    async def generate_motion(
        self,
        source_avatar: Any,
        driving_motion: Any,
        output_path: Any,
        options: Optional[Any] = None,
        progress_callback: Optional[Callable[[int, str], Awaitable[None]]] = None,
    ) -> Dict[str, Any]:
        """Generate neural motion video from source avatar and driving motion."""
        ...

    def is_available(self) -> bool:
        """Check whether the provider is currently operational on the host environment."""
        ...


@runtime_checkable
class ImageProvider(Protocol):
    """Abstract interface for generative image creation and background asset generation."""

    async def generate_image(
        self,
        prompt: str,
        aspect_ratio: str = "16:9",
        negative_prompt: Optional[str] = None,
    ) -> str:
        """Generate high-resolution image asset and return S3 storage key."""
        ...

    async def generate(
        self,
        request: ImageGenContractRequest,
    ) -> ImageGenContractResult:
        """Generate image asset using strongly typed execution contract."""
        ...


@runtime_checkable
class VideoProvider(Protocol):
    """Abstract interface for AI video clip generation and generative b-roll."""

    async def generate_video(
        self,
        prompt: str,
        duration_seconds: float = 4.0,
        aspect_ratio: str = "16:9",
    ) -> str:
        """Generate generative b-roll video clip and return S3 storage key."""
        ...

    async def generate(
        self,
        request: VideoGenContractRequest,
    ) -> VideoGenContractResult:
        """Generate video clip using strongly typed execution contract."""
        ...


@runtime_checkable
class MattingProvider(Protocol):
    """Abstract interface for neural human matting and background removal."""

    async def extract_matte(
        self,
        video_storage_key: str,
        output_format: str = "matte_mask",
        threshold: float = 0.5,
    ) -> MattingResult:
        """Extract foreground human alpha matte from video or image."""
        ...

    async def segment(
        self,
        request: MattingContractRequest,
    ) -> MattingContractResult:
        """Execute human matting using strongly typed execution contract."""
        ...


@runtime_checkable
class AudioEnhanceProvider(Protocol):
    """Abstract interface for neural noise suppression, voice EQ, and silence trimming."""

    async def enhance_audio(
        self,
        audio_bytes: bytes,
        remove_noise: bool = True,
        remove_fillers: bool = False,
        trim_silence_pauses: bool = True,
        silence_threshold_seconds: float = 1.2,
        apply_broadcast_eq: bool = True,
    ) -> AudioEnhanceResult:
        """Process raw audio bytes and return cleaned audio bytes with telemetry."""
        ...

    async def enhance(
        self,
        request: AudioEnhanceContractRequest,
    ) -> AudioEnhanceContractResult:
        """Execute audio enhancement using strongly typed execution contract."""
        ...


