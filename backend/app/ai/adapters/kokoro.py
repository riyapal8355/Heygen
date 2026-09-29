"""Real Kokoro-82M Neural Text-to-Speech (TTS) Provider Adapter.

Executes local neural text-to-speech synthesis using Kokoro-82M on CPU via ONNX Runtime.
Conforms to the TTSProvider protocol defined in app.ai.interfaces.
"""

import asyncio
import io
import os
import wave
from typing import Any, Dict, List, Optional

import numpy as np
import soundfile as sf

from app.ai.capabilities import ProviderDescriptor
from app.ai.contracts import TTSContractRequest, TTSContractResult
from app.ai.interfaces import AudioSynthesisResult, TTSProvider
from app.core.config import get_settings
from app.core.exceptions import (
    AIProviderException,
    NotFoundException,
    ValidationException,
)
from app.core.logging import get_logger

logger = get_logger(__name__)

DEFAULT_KOKORO_VOICE_ID = "af_heart"
DEFAULT_SAMPLE_RATE = 24000


class KokoroTTSProvider:
    """Production self-hosted CPU neural TTS provider using Kokoro-82M ONNX."""

    provider_name: str = "kokoro"
    descriptor: ProviderDescriptor = ProviderDescriptor(
        name="kokoro",
        capability="tts",
        version="1.0.0",
        is_local=True,
        requires_gpu=False,
        supported_languages=[
            "en",
            "en-us",
            "en-gb",
            "es",
            "es-es",
            "fr",
            "fr-fr",
            "it",
            "pt",
            "pt-br",
            "hi",
            "ja",
            "zh",
        ],
        supported_output_formats=["wav"],
        is_available=True,
        metadata={
            "engine": "Kokoro-82M (ONNX Runtime)",
            "default_voice": DEFAULT_KOKORO_VOICE_ID,
            "sample_rate": DEFAULT_SAMPLE_RATE,
            "model_license": "Apache-2.0",
            "voice_license": "Apache-2.0 / CC BY 4.0",
            "license_classification": "COMMERCIAL_SAFE",
            "commercial_use_permitted": True,
        },
    )

    def __init__(self, cache_root: Optional[str] = None) -> None:
        settings = get_settings()
        self.cache_root = os.path.abspath(cache_root or settings.AI_MODEL_CACHE_DIR)
        self._engine: Optional[Any] = None
        self._voices_data: Optional[Dict[str, Any]] = None
        self._lock = asyncio.Lock()

    def _resolve_paths(self) -> tuple[str, str]:
        """Resolve paths to kokoro-v1.0.onnx model and voices-v1.0.bin."""
        model_candidates = [
            os.path.join(self.cache_root, "tts", "kokoro", "kokoro-v1.0.onnx"),
            os.path.join(self.cache_root, "kokoro", "kokoro-v1.0.onnx"),
            os.path.join(self.cache_root, "kokoro-v1.0.onnx"),
        ]
        voices_candidates = [
            os.path.join(self.cache_root, "tts", "kokoro", "voices-v1.0.bin"),
            os.path.join(self.cache_root, "kokoro", "voices-v1.0.bin"),
            os.path.join(self.cache_root, "voices-v1.0.bin"),
        ]

        model_path = next((os.path.abspath(c) for c in model_candidates if os.path.isfile(c)), None)
        voices_path = next((os.path.abspath(c) for c in voices_candidates if os.path.isfile(c)), None)

        if not model_path:
            raise NotFoundException(
                message=f"Kokoro model file 'kokoro-v1.0.onnx' not found at candidate locations: {model_candidates}",
                code="AI_MODEL_NOT_FOUND",
                details={"candidates": model_candidates},
            )
        if not voices_path:
            raise NotFoundException(
                message=f"Kokoro voice pack 'voices-v1.0.bin' not found at candidate locations: {voices_candidates}",
                code="AI_MODEL_NOT_FOUND",
                details={"candidates": voices_candidates},
            )

        return model_path, voices_path

    def _get_or_load_engine(self) -> Any:
        """Lazy thread-safe loader for Kokoro ONNX inference engine."""
        if self._engine is not None:
            return self._engine

        model_path, voices_path = self._resolve_paths()
        try:
            from kokoro_onnx import Kokoro

            logger.info("Initializing Kokoro ONNX engine from '%s' and '%s'...", model_path, voices_path)
            self._engine = Kokoro(model_path, voices_path)
            # Cache voice names list
            data = np.load(voices_path)
            self._voices_data = {k: True for k in data.files}
            logger.info("Loaded Kokoro engine with %d voices in cache.", len(self._voices_data))
            return self._engine
        except Exception as exc:
            logger.error("Failed to load Kokoro ONNX model: %s", exc, exc_info=True)
            raise AIProviderException(
                message=f"Failed to initialize Kokoro ONNX engine: {exc}",
                code="AI_MODEL_LOAD_FAILED",
                provider="kokoro",
            ) from exc

    def _detect_lang_for_voice(self, voice_id: str) -> str:
        """Derive dialect/language code from Kokoro voice identifier prefix."""
        v = voice_id.lower().strip()
        if v.startswith("af_") or v.startswith("am_"):
            return "en-us"
        elif v.startswith("bf_") or v.startswith("bm_"):
            return "en-gb"
        elif v.startswith("ef_") or v.startswith("em_"):
            return "es"
        elif v.startswith("ff_"):
            return "fr-fr"
        elif v.startswith("if_") or v.startswith("im_"):
            return "it"
        elif v.startswith("pf_") or v.startswith("pm_"):
            return "pt-br"
        elif v.startswith("hf_") or v.startswith("hm_"):
            return "hi"
        elif v.startswith("jf_") or v.startswith("jm_"):
            return "ja"
        elif v.startswith("zf_") or v.startswith("zm_"):
            return "zh"
        return "en-us"

    def _resolve_voice_id(self, voice_id: Optional[str]) -> str:
        """Resolve clean Kokoro voice identifier or fallback to default."""
        clean = (voice_id or "").strip()
        if not clean or clean in ("default", "mock", "kokoro", "kokoro-cpu"):
            return DEFAULT_KOKORO_VOICE_ID

        # Map friendly names if passed
        friendly_map = {
            "heart": "af_heart",
            "kokoro heart": "af_heart",
            "emma": "bf_emma",
            "kokoro emma": "bf_emma",
            "dora": "ef_dora",
            "kokoro dora": "ef_dora",
            "siwis": "ff_siwis",
            "kokoro siwis": "ff_siwis",
        }
        clean_lower = clean.lower()
        if clean_lower in friendly_map:
            return friendly_map[clean_lower]

        return clean

    def _synthesize_sync(self, text: str, voice: str, speed: float, lang: str) -> AudioSynthesisResult:
        """Execute synchronous Kokoro ONNX inference and format as PCM WAV."""
        engine = self._get_or_load_engine()

        if self._voices_data is not None and voice not in self._voices_data:
            raise NotFoundException(
                message=f"Voice '{voice}' is not present in the Kokoro voice pack.",
                code="VOICE_NOT_FOUND",
                details={"voice": voice, "available_sample": list(self._voices_data.keys())[:10]},
            )

        try:
            samples, sample_rate = engine.create(
                text=text,
                voice=voice,
                speed=float(speed),
                lang=lang,
            )
        except Exception as exc:
            logger.error("Kokoro synthesis error for voice '%s': %s", voice, exc, exc_info=True)
            raise AIProviderException(
                message=f"Kokoro synthesis failed for voice '{voice}': {exc}",
                code="AI_SYNTHESIS_FAILED",
                provider="kokoro",
            ) from exc

        if samples is None or len(samples) == 0:
            raise AIProviderException(
                message="Kokoro produced empty audio waveform.",
                code="AI_SYNTHESIS_EMPTY",
                provider="kokoro",
            )

        # Ensure float32 range [-1.0, 1.0] and verify non-zero signal
        samples = np.asarray(samples, dtype=np.float32)
        rms = float(np.sqrt(np.mean(samples**2)))
        peak = float(np.max(np.abs(samples)))

        if peak == 0.0 or rms < 0.0001:
            raise AIProviderException(
                message="Kokoro produced completely silent audio (zero RMS / peak).",
                code="AI_SYNTHESIS_SILENT",
                provider="kokoro",
            )

        duration_seconds = len(samples) / float(sample_rate)

        # Encode float32 numpy array to 16-bit PCM WAV container
        wav_buffer = io.BytesIO()
        sf.write(wav_buffer, samples, sample_rate, format="WAV", subtype="PCM_16")
        audio_bytes = wav_buffer.getvalue()

        # Validate WAV structure
        try:
            with wave.open(io.BytesIO(audio_bytes), "rb") as wf:
                assert wf.getnchannels() == 1, "Expected mono output"
                assert wf.getsampwidth() == 2, "Expected 16-bit samples"
                assert wf.getframerate() == sample_rate, "Sample rate mismatch"
        except Exception as exc:
            raise AIProviderException(
                message=f"Kokoro generated invalid WAV header: {exc}",
                code="AI_INVALID_AUDIO_FORMAT",
                provider="kokoro",
            ) from exc

        return AudioSynthesisResult(
            audio_bytes=audio_bytes,
            sample_rate=sample_rate,
            duration_seconds=round(duration_seconds, 3),
            word_timestamps=[],
        )

    async def synthesize_speech(
        self,
        text: str,
        voice_id: str,
        speed: float = 1.0,
        pitch: float = 0.0,
        pronunciation_rules: Optional[List[Dict[str, str]]] = None,
    ) -> AudioSynthesisResult:
        """Synthesize speech using Kokoro-82M neural model on CPU."""
        if not text or not text.strip():
            raise ValidationException(
                message="Text payload for speech synthesis cannot be empty.",
                code="EMPTY_TEXT",
            )

        clean_text = text.strip()
        resolved_voice = self._resolve_voice_id(voice_id)
        lang = self._detect_lang_for_voice(resolved_voice)

        clamped_speed = max(0.5, min(2.0, float(speed)))

        async with self._lock:
            return await asyncio.to_thread(
                self._synthesize_sync,
                text=clean_text,
                voice=resolved_voice,
                speed=clamped_speed,
                lang=lang,
            )

    async def clone_voice(
        self,
        voice_name: str,
        sample_audio_keys: List[str],
        language: str = "en",
    ) -> str:
        """Zero-shot voice cloning boundary.

        Zero-shot voice cloning from audio samples requires a GPU neural model (such as XTTS-v2).
        Kokoro-82M is a fixed-preset neural voice engine and does not support zero-shot voice cloning.
        """
        raise AIProviderException(
            message=(
                "Zero-shot voice cloning requires a CUDA GPU and is not supported by "
                "the lightweight CPU Kokoro TTS engine. Please run on a GPU-enabled node with XTTS-v2."
            ),
            code="VOICE_CLONING_REQUIRES_GPU",
            details={
                "requested_voice": voice_name,
                "provider": "kokoro",
                "required_capability": "gpu_voice_cloning",
            },
        )

    async def synthesize(
        self,
        request: TTSContractRequest,
    ) -> TTSContractResult:
        """Synthesize speech using strongly typed execution contract."""
        res = await self.synthesize_speech(
            text=request.text,
            voice_id=request.voice_id,
            speed=request.speed,
            pitch=request.pitch,
            pronunciation_rules=request.pronunciation_rules,
        )
        words = request.text.split()
        return TTSContractResult(
            status="succeeded",
            duration_seconds=res.duration_seconds,
            sample_rate=res.sample_rate,
            channels=1,
            word_count=len(words),
            word_timestamps=res.word_timestamps,
            metrics={
                "provider": "kokoro",
                "voice_id": request.voice_id,
                "speed": request.speed,
                "pitch": request.pitch,
                "bytes_generated": len(res.audio_bytes),
                "is_real_ai": True,
            },
        )

    async def execute(self, request: TTSContractRequest) -> TTSContractResult:
        """Alias for synthesize executing TTSContractRequest."""
        return await self.synthesize(request)
