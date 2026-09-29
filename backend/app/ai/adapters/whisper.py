"""Real Whisper Neural Automated Speech Recognition (ASR) Provider Adapter.

Executes local neural speech-to-text inference using faster-whisper (CTranslate2) on CPU.
Conforms to the ASRProvider protocol defined in app.ai.interfaces.
"""

import asyncio
import gc
import io
import os
import time
from typing import Any, Dict, List, Optional, Union

from app.ai.capabilities import ProviderDescriptor
from app.ai.contracts import ASRContractRequest, ASRContractResult
from app.ai.interfaces import ASRProvider, TranscriptionResult
from app.ai.lifecycle import resolve_safe_cache_path
from app.core.config import get_settings
from app.core.exceptions import (
    AIProviderException,
    NotFoundException,
)
from app.core.logging import get_logger

logger = get_logger(__name__)

DEFAULT_WHISPER_MODEL_ID = "tiny"
MAX_AUDIO_DURATION_SECONDS = 600.0  # 10 minutes max for CPU safety


class WhisperASRProvider:
    """Production self-hosted CPU neural ASR provider using faster-whisper (CTranslate2)."""

    provider_name: str = "whisper"
    descriptor: ProviderDescriptor = ProviderDescriptor(
        name="whisper",
        capability="asr",
        version="1.2.1",
        is_local=True,
        requires_gpu=False,
        supported_languages=[
            "en", "zh", "de", "es", "ru", "ko", "fr", "ja", "pt", "tr",
            "pl", "ca", "nl", "ar", "sv", "it", "id", "hi", "fi", "vi",
            "he", "uk", "el", "ms", "cs", "ro", "da", "hu", "ta", "no",
            "th", "ur", "hr", "bg", "lt", "la", "mi", "ml", "cy", "sk",
            "te", "fa", "lv", "bn", "sr", "az", "sl", "kn", "et", "mk",
            "br", "eu", "is", "hy", "ne", "mn", "bs", "kk", "sq", "sw",
            "gl", "mr", "pa", "si", "km", "sn", "yo", "so", "af", "oc",
            "ka", "be", "tg", "sd", "gu", "am", "yi", "lo", "uz", "fo",
            "ht", "ps", "tk", "nn", "mt", "sa", "lb", "my", "bo", "tl",
            "mg", "as", "tt", "haw", "ln", "ha", "ba", "jw", "su",
        ],
        supported_input_formats=["wav", "mp3", "mp4", "m4a", "webm", "ogg", "flac"],
        is_available=True,
        metadata={
            "engine": "faster-whisper (CTranslate2)",
            "default_model": DEFAULT_WHISPER_MODEL_ID,
            "quantization": "int8",
            "engine_license": "MIT",
            "runtime_license": "MIT (CTranslate2)",
            "model_license": "MIT (OpenAI / Systran)",
            "commercial_use_permitted": True,
            "supports_word_timestamps": True,
        },
    )

    def __init__(self, cache_root: Optional[str] = None) -> None:
        settings = get_settings()
        self.cache_root = os.path.abspath(cache_root or settings.AI_MODEL_CACHE_DIR)
        self._model_cache: Dict[str, Any] = {}
        self._lock = asyncio.Lock()

    def _resolve_model_dir(self, model_id: Optional[str] = None) -> str:
        """Resolve safe local directory path for Whisper CTranslate2 model weights."""
        clean = (model_id or DEFAULT_WHISPER_MODEL_ID).strip()
        # Normalize aliases
        if clean in ("", "default", "tiny", "whisper-tiny", "asr/whisper-tiny-cpu", "asr/whisper-tiny-multilingual-cpu", "whisper-tiny-multilingual-cpu", "tiny-multilingual"):
            target_subpath = os.path.join("asr", "whisper", "tiny")
        else:
            # Strip any prefix like asr/whisper/
            sub = clean.replace("asr/whisper/", "").replace("asr/", "")
            target_subpath = os.path.join("asr", "whisper", sub)

        resolved = resolve_safe_cache_path(self.cache_root, target_subpath)

        # Also check fallback locations within cache root
        candidates = [
            resolved,
            os.path.join(self.cache_root, "asr", "whisper", "tiny"),
            os.path.join(self.cache_root, "whisper-tiny"),
            os.path.join(self.cache_root, "tiny"),
        ]

        for cand in candidates:
            if os.path.isdir(cand) and os.path.isfile(os.path.join(cand, "model.bin")):
                return os.path.abspath(cand)

        raise NotFoundException(
            message=f"Whisper ASR model '{clean}' not found in cache. Attempted paths: {candidates}",
            code="AI_MODEL_NOT_FOUND",
            details={"model_id": clean, "attempted_paths": candidates},
        )

    def _get_or_load_model(self, model_dir: str) -> Any:
        """Load WhisperModel from on-disk CTranslate2 weights or retrieve from cache."""
        if model_dir in self._model_cache:
            return self._model_cache[model_dir]

        try:
            from faster_whisper import WhisperModel
            logger.info("Loading Whisper ASR model from '%s' on CPU (compute_type=int8)...", model_dir)
            model = WhisperModel(
                model_dir,
                device="cpu",
                compute_type="int8",
                local_files_only=True,
            )
            self._model_cache[model_dir] = model
            return model
        except Exception as exc:
            logger.error("Failed to load Whisper ASR model from '%s': %s", model_dir, exc)
            raise AIProviderException(
                message=f"Failed to load Whisper neural ASR model: {exc}",
                code="AI_MODEL_LOAD_FAILED",
                details={"model_dir": model_dir, "error": str(exc)},
            )

    def _transcribe_sync(
        self,
        audio_input: Union[str, bytes, io.BytesIO],
        language: Optional[str] = None,
        model_id: Optional[str] = None,
        include_word_timestamps: bool = True,
        beam_size: int = 5,
    ) -> TranscriptionResult:
        """Synchronous CPU inference executed in worker thread pool."""
        # 1. Validate audio input
        audio_to_process: Any = audio_input

        if isinstance(audio_input, bytes):
            if len(audio_input) == 0:
                raise AIProviderException(
                    message="Transcription failed: input audio buffer is completely empty (0 bytes).",
                    code="ASR_EMPTY_AUDIO",
                )
            if len(audio_input) <= 44:
                # 44 bytes is the size of a standard RIFF/WAV header with 0 data frames
                raise AIProviderException(
                    message="Transcription failed: audio buffer contains only header bytes without audio data.",
                    code="ASR_EMPTY_AUDIO",
                )
            audio_to_process = io.BytesIO(audio_input)

        elif isinstance(audio_input, io.BytesIO):
            val = audio_input.getvalue()
            if len(val) == 0 or len(val) <= 44:
                raise AIProviderException(
                    message="Transcription failed: input audio stream is empty.",
                    code="ASR_EMPTY_AUDIO",
                )
            audio_input.seek(0)
            audio_to_process = audio_input

        elif isinstance(audio_input, str):
            # Could be a file path or an S3 key
            if os.path.isfile(audio_input):
                if os.path.getsize(audio_input) <= 44:
                    raise AIProviderException(
                        message=f"Transcription failed: audio file '{audio_input}' is empty or header-only.",
                        code="ASR_EMPTY_AUDIO",
                    )
                audio_to_process = audio_input
            else:
                # Try fetching from object storage if it looks like an S3 key
                try:
                    from app.storage.s3 import get_storage_provider
                    storage = get_storage_provider()
                    audio_bytes = storage.get_object_bytes(audio_input)
                    if len(audio_bytes) <= 44:
                        raise AIProviderException(
                            message=f"Storage object '{audio_input}' contains empty audio buffer.",
                            code="ASR_EMPTY_AUDIO",
                        )
                    audio_to_process = io.BytesIO(audio_bytes)
                except AIProviderException:
                    raise
                except Exception as s3_err:
                    raise NotFoundException(
                        message=f"Audio file or storage object not found: '{audio_input}': {s3_err}",
                        code="ASR_AUDIO_NOT_FOUND",
                        details={"audio_key": audio_input, "error": str(s3_err)},
                    )

        # 2. Language validation
        clean_lang = language.strip().lower() if language else None
        if clean_lang and clean_lang != "auto" and clean_lang != "*":
            if not self.descriptor.supports_language(clean_lang):
                raise AIProviderException(
                    message=f"Requested language '{clean_lang}' is not supported by Whisper ASR.",
                    code="ASR_UNSUPPORTED_LANGUAGE",
                    details={"requested_language": clean_lang},
                )

        # 3. Load model
        model_dir = self._resolve_model_dir(model_id)
        model = self._get_or_load_model(model_dir)

        # 4. Transcribe with PyAV / faster-whisper
        t0 = time.time()
        try:
            segments_iter, info = model.transcribe(
                audio_to_process,
                language=clean_lang if clean_lang != "auto" else None,
                beam_size=beam_size,
                word_timestamps=include_word_timestamps,
                vad_filter=False,
            )

            # Check safety duration threshold
            if info.duration > MAX_AUDIO_DURATION_SECONDS:
                raise AIProviderException(
                    message=(
                        f"Audio duration ({info.duration:.1f}s) exceeds maximum allowed CPU "
                        f"safety limit of {MAX_AUDIO_DURATION_SECONDS}s."
                    ),
                    code="ASR_AUDIO_TOO_LONG",
                    details={"duration": info.duration, "max_duration": MAX_AUDIO_DURATION_SECONDS},
                )

            # Collect segments and timestamps
            parsed_segments: List[Dict[str, Any]] = []
            segment_id = 1
            prev_end = 0.0

            for s in segments_iter:
                seg_start = round(max(0.0, float(s.start)), 3)
                seg_end = round(max(seg_start, float(s.end)), 3)

                words_list: List[Dict[str, Any]] = []
                if include_word_timestamps and getattr(s, "words", None):
                    for w in s.words:
                        w_start = round(max(0.0, float(w.start)), 3)
                        w_end = round(max(w_start, float(w.end)), 3)
                        w_prob = round(float(w.probability), 3) if hasattr(w, "probability") else 1.0
                        words_list.append({
                            "word": w.word,
                            "start": w_start,
                            "end": w_end,
                            "probability": w_prob,
                        })

                parsed_segments.append({
                    "id": segment_id,
                    "start": seg_start,
                    "end": seg_end,
                    "text": s.text.strip(),
                    "words": words_list,
                })
                segment_id += 1
                prev_end = seg_end

        except AIProviderException:
            raise
        except ValueError as val_err:
            if "not a valid language code" in str(val_err).lower():
                raise AIProviderException(
                    message=f"Unsupported language code: {val_err}",
                    code="ASR_UNSUPPORTED_LANGUAGE",
                    details={"error": str(val_err)},
                )
            raise AIProviderException(
                message=f"Whisper speech recognition failed: {val_err}",
                code="ASR_INVALID_AUDIO",
                details={"error": str(val_err)},
            )
        except Exception as trans_err:
            logger.error("Whisper transcription inference failed: %s", trans_err)
            raise AIProviderException(
                message=f"Whisper speech recognition failed: {trans_err}",
                code="ASR_INVALID_AUDIO",
                details={"error": str(trans_err)},
            )

        latency = round(time.time() - t0, 3)
        full_text = " ".join(seg["text"] for seg in parsed_segments if seg["text"])
        duration = round(float(info.duration) if info.duration > 0 else prev_end, 3)
        confidence = round(float(info.language_probability), 3) if hasattr(info, "language_probability") else 0.95

        logger.info(
            "Whisper ASR completed in %.2fs: %d segments, duration=%.2fs, lang='%s' (p=%.2f)",
            latency,
            len(parsed_segments),
            duration,
            info.language,
            confidence,
        )

        return TranscriptionResult(
            detected_language=info.language,
            full_text=full_text,
            duration_seconds=duration,
            segments=parsed_segments,
            confidence=confidence,
        )

    def unload_model(self, model_id: Optional[str] = None) -> None:
        """Evict cached Whisper model from host RAM and trigger garbage collection."""
        if model_id:
            try:
                resolved = self._resolve_model_dir(model_id)
                if resolved in self._model_cache:
                    del self._model_cache[resolved]
                    logger.info("Evicted Whisper model '%s' from memory", resolved)
            except Exception:
                self._model_cache.clear()
        else:
            self._model_cache.clear()
            logger.info("Cleared all cached Whisper ASR models")
        gc.collect()

    async def transcribe_audio(
        self,
        audio_storage_key: str,
        language: Optional[str] = None,
    ) -> TranscriptionResult:
        """Transcribe audio into text and timestamped cues with timeout bounds."""
        settings = get_settings()
        timeout = settings.AI_INFERENCE_TIMEOUT_SECONDS

        try:
            return await asyncio.wait_for(
                asyncio.to_thread(
                    self._transcribe_sync,
                    audio_input=audio_storage_key,
                    language=language,
                    include_word_timestamps=True,
                ),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            logger.error("Whisper ASR inference timed out after %s seconds", timeout)
            raise AIProviderException(
                message=f"Whisper speech recognition timed out after {timeout} seconds.",
                code="ASR_INFERENCE_TIMEOUT",
                details={"timeout_seconds": timeout},
            )

    async def transcribe_bytes(
        self,
        audio_bytes: bytes,
        language: Optional[str] = None,
        include_word_timestamps: bool = True,
    ) -> TranscriptionResult:
        """Transcribe raw audio bytes asynchronously."""
        settings = get_settings()
        timeout = settings.AI_INFERENCE_TIMEOUT_SECONDS

        try:
            return await asyncio.wait_for(
                asyncio.to_thread(
                    self._transcribe_sync,
                    audio_input=audio_bytes,
                    language=language,
                    include_word_timestamps=include_word_timestamps,
                ),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            raise AIProviderException(
                message=f"Whisper speech recognition timed out after {timeout} seconds.",
                code="ASR_INFERENCE_TIMEOUT",
                details={"timeout_seconds": timeout},
            )

    async def transcribe(
        self,
        request: ASRContractRequest,
    ) -> ASRContractResult:
        """Transcribe audio using strongly typed execution contract."""
        audio_key = request.audio_asset.storage_key or str(request.audio_asset.asset_id or "")
        res = await self.transcribe_audio(
            audio_storage_key=audio_key,
            language=request.language,
        )
        return ASRContractResult(
            status="succeeded",
            detected_language=res.detected_language,
            full_text=res.full_text,
            segments=res.segments,
            metrics={
                "provider": "whisper",
                "model": DEFAULT_WHISPER_MODEL_ID,
                "duration_seconds": res.duration_seconds,
                "segment_count": len(res.segments),
                "confidence": res.confidence,
                "is_real_ai": True,
            },
        )
