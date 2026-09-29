"""Real Piper Neural Text-to-Speech (TTS) Provider Adapter.

Executes local neural text-to-speech synthesis using Piper TTS on CPU via ONNX Runtime.
Conforms to the TTSProvider protocol defined in app.ai.interfaces.
"""

import asyncio
import io
import os
import re
import wave
from typing import Any, Dict, List, Optional

from app.ai.capabilities import ProviderDescriptor
from app.ai.contracts import TTSContractRequest, TTSContractResult
from app.ai.interfaces import AudioSynthesisResult, TTSProvider
from app.core.config import get_settings
from app.core.exceptions import (
    AIProviderException,
    NotFoundException,
)
from app.core.logging import get_logger

logger = get_logger(__name__)

# Default model directory relative to AI_MODEL_CACHE_DIR
DEFAULT_PIPER_VOICE_ID = "en_US-lessac-medium"
DEFAULT_SAMPLE_RATE = 22050


class PiperTTSProvider:
    """Production self-hosted CPU neural TTS provider using Piper TTS."""

    provider_name: str = "piper"
    descriptor: ProviderDescriptor = ProviderDescriptor(
        name="piper",
        capability="tts",
        version="1.8.0",
        is_local=True,
        requires_gpu=False,
        supported_languages=[
            "en",
            "en-us",
            "en-gb",
            "es",
            "es-es",
            "es-mx",
            "de",
            "de-de",
            "fr",
            "fr-fr",
            "it",
            "it-it",
            "pt",
            "pt-br",
        ],
        supported_output_formats=["wav"],
        is_available=True,
        metadata={
            "engine": "Piper TTS (ONNX Runtime)",
            "default_voice": DEFAULT_PIPER_VOICE_ID,
            "sample_rate": DEFAULT_SAMPLE_RATE,
            "license": "MIT",
            "voice_license": "Public Domain / CC0 / CC-BY / Apache-2.0",
        },
    )

    def __init__(self, cache_root: Optional[str] = None) -> None:
        settings = get_settings()
        self.cache_root = os.path.abspath(cache_root or settings.AI_MODEL_CACHE_DIR)
        self._voice_cache: Dict[str, Any] = {}
        self._lock = asyncio.Lock()

    def _resolve_model_path(self, voice_id: str) -> str:
        """Resolve on-disk path to Piper ONNX model file."""
        clean_voice = voice_id.strip() if voice_id else DEFAULT_PIPER_VOICE_ID
        if clean_voice in ("tts/piper-es-davefx-cpu", "es_ES-davefx", "es-davefx"):
            clean_voice = "es_ES-davefx-medium"

        is_generic_alias = (
            clean_voice in ("", "default", "mock", "piper", "piper-cpu", "tts/piper-cpu", "lessac")
            or clean_voice.startswith("voice_mock")
            or clean_voice.startswith("mock-")
        )

        backend_cache = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "models_cache")
        roots = [self.cache_root]
        if os.path.abspath(backend_cache) != os.path.abspath(self.cache_root):
            roots.append(backend_cache)

        candidates = []
        voice_key = DEFAULT_PIPER_VOICE_ID if is_generic_alias else clean_voice
        for r in roots:
            candidates.extend([
                os.path.join(r, "tts", "piper", voice_key, f"{voice_key}.onnx"),
                os.path.join(r, voice_key, f"{voice_key}.onnx"),
                os.path.join(r, f"{voice_key}.onnx"),
            ])

        for cand in candidates:
            if os.path.isfile(cand):
                return os.path.abspath(cand)

        raise NotFoundException(
            message=f"Piper voice model '{voice_id}' not found at any expected location: {candidates}",
            code="AI_MODEL_NOT_FOUND",
            details={"voice_id": voice_id, "attempted_paths": candidates},
        )

    def _get_or_load_voice(self, model_path: str) -> Any:
        """Load PiperVoice from on-disk ONNX artifact or retrieve from in-memory cache."""
        if model_path in self._voice_cache:
            return self._voice_cache[model_path]

        try:
            from piper.voice import PiperVoice
            logger.info("Loading Piper voice model from '%s'...", model_path)
            voice = PiperVoice.load(model_path)
            self._voice_cache[model_path] = voice
            return voice
        except Exception as exc:
            logger.error("Failed to load Piper voice from '%s': %s", model_path, exc)
            raise AIProviderException(
                message=f"Failed to load Piper neural voice model: {exc}",
                code="AI_MODEL_LOAD_FAILED",
                details={"model_path": model_path, "error": str(exc)},
            )

    def _synthesize_sync(
        self,
        text: str,
        voice_id: str,
        speed: float = 1.0,
        pitch: float = 0.0,
        pronunciation_rules: Optional[List[Dict[str, str]]] = None,
    ) -> AudioSynthesisResult:
        """Synchronous CPU inference executed in worker thread."""
        from piper.config import SynthesisConfig

        # 1. Apply Brand Glossary / phonetic substitutions
        processed_text = text
        if pronunciation_rules:
            for rule in pronunciation_rules:
                term = rule.get("term", "")
                replacement = rule.get("replacement_phonetic", "")
                if term and replacement:
                    pattern = re.compile(re.escape(term), re.IGNORECASE)
                    processed_text = pattern.sub(replacement, processed_text)

        # 2. Resolve model and load voice
        model_path = self._resolve_model_path(voice_id)
        voice = self._get_or_load_voice(model_path)

        # 3. Configure synthesis parameters
        # In Piper, length_scale is inverse to speech rate (speed=2.0 -> length_scale=0.5)
        safe_speed = max(0.2, min(5.0, speed))
        length_scale = 1.0 / safe_speed
        syn_config = SynthesisConfig(
            length_scale=length_scale,
            volume=1.0,
        )

        # 4. Synthesize WAV audio into in-memory buffer
        buffer = io.BytesIO()
        wf = wave.open(buffer, "wb")
        try:
            voice.synthesize_wav(
                text=processed_text,
                wav_file=wf,
                syn_config=syn_config,
                set_wav_format=True,
            )
        finally:
            wf.close()

        raw_wav_bytes = buffer.getvalue()
        if not raw_wav_bytes or len(raw_wav_bytes) <= 44:
            raise AIProviderException(
                message="Piper TTS synthesized empty audio buffer.",
                code="TTS_SYNTHESIS_EMPTY",
                details={"text": text, "voice_id": voice_id},
            )

        # 5. Measure precise duration & sample rate from WAV header
        try:
            with io.BytesIO(raw_wav_bytes) as read_buf:
                with wave.open(read_buf, "rb") as read_wf:
                    actual_sample_rate = read_wf.getframerate()
                    n_frames = read_wf.getnframes()
                    actual_duration = round(n_frames / float(actual_sample_rate), 3)
        except Exception as parse_err:
            logger.warning("Could not read WAV header: %s; falling back to estimation", parse_err)
            actual_sample_rate = DEFAULT_SAMPLE_RATE
            actual_duration = round(max(0.5, len(text.split()) * 0.4 / safe_speed), 3)

        # 6. Compute word timestamps
        words = processed_text.split()
        word_count = max(1, len(words))
        time_per_word = actual_duration / word_count
        timestamps = [
            {
                "word": word,
                "start": round(i * time_per_word, 3),
                "end": round((i + 1) * time_per_word, 3),
            }
            for i, word in enumerate(words)
        ]

        return AudioSynthesisResult(
            audio_bytes=raw_wav_bytes,
            sample_rate=actual_sample_rate,
            duration_seconds=actual_duration,
            word_timestamps=timestamps,
        )

    def unload_voice(self, voice_id: Optional[str] = None) -> None:
        """Evict cached Piper voice models to reclaim host RAM."""
        if voice_id:
            clean = voice_id.strip()
            keys_to_remove = [k for k in self._voice_cache if clean in k]
            for k in keys_to_remove:
                del self._voice_cache[k]
                logger.info("Evicted voice '%s' from Piper cache", k)
        else:
            self._voice_cache.clear()
            logger.info("Cleared all cached Piper voice models")

    async def synthesize_speech(
        self,
        text: str,
        voice_id: str = DEFAULT_PIPER_VOICE_ID,
        speed: float = 1.0,
        pitch: float = 0.0,
        pronunciation_rules: Optional[List[Dict[str, str]]] = None,
        language: Optional[str] = None,
    ) -> AudioSynthesisResult:
        """Synthesize speech asynchronously offloading CPU work to thread pool with safety bounds."""
        if not text or not text.strip():
            raise AIProviderException(
                message="Synthesis text cannot be empty.",
                code="TTS_EMPTY_TEXT",
            )

        max_len = 10000
        if len(text) > max_len:
            raise AIProviderException(
                message=f"Synthesis text length ({len(text)}) exceeds maximum allowed safety threshold of {max_len} characters.",
                code="TTS_TEXT_TOO_LONG",
                details={"text_length": len(text), "max_length": max_len},
            )

        if language and not self.descriptor.supports_language(language):
            raise AIProviderException(
                message=f"Language '{language}' is not supported by Piper voice '{voice_id}'. Supported languages: {self.descriptor.supported_languages}",
                code="TTS_UNSUPPORTED_LANGUAGE",
                details={"requested_language": language, "supported_languages": self.descriptor.supported_languages},
            )

        settings = get_settings()
        timeout = settings.AI_INFERENCE_TIMEOUT_SECONDS

        try:
            return await asyncio.wait_for(
                asyncio.to_thread(
                    self._synthesize_sync,
                    text=text,
                    voice_id=voice_id,
                    speed=speed,
                    pitch=pitch,
                    pronunciation_rules=pronunciation_rules,
                ),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            logger.error("Piper TTS synthesis timed out after %s seconds", timeout)
            raise AIProviderException(
                message=f"Piper speech synthesis timed out after {timeout} seconds.",
                code="TTS_INFERENCE_TIMEOUT",
                details={"timeout_seconds": timeout, "voice_id": voice_id},
            )

    async def clone_voice(
        self,
        voice_name: str,
        sample_audio_keys: List[str],
        language: str = "en",
    ) -> str:
        """Zero-shot voice cloning boundary.

        Zero-shot voice cloning from audio samples requires a GPU neural model (such as XTTS-v2).
        Piper TTS is a lightweight fixed-neural voice engine and does not support zero-shot voice cloning.
        """
        raise AIProviderException(
            message=(
                "Zero-shot voice cloning requires a CUDA GPU and is not supported by "
                "the lightweight CPU Piper TTS engine. Please run on a GPU-enabled node with XTTS-v2."
            ),
            code="VOICE_CLONING_REQUIRES_GPU",
            details={
                "requested_voice": voice_name,
                "provider": "piper",
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
                "provider": "piper",
                "voice_id": request.voice_id,
                "speed": request.speed,
                "pitch": request.pitch,
                "bytes_generated": len(res.audio_bytes),
                "is_real_ai": True,
            },
        )
