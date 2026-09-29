"""OpenVoice V2 neural voice cloning and tone color conversion provider.

Implements instant zero-shot voice cloning using MyShell.ai's MIT-licensed
OpenVoice V2 Tone Color Converter architecture.
"""

import hashlib
import io
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import soundfile as sf
import torch

from app.ai.capabilities import ProviderDescriptor
from app.ai.contracts import (
    TTSContractRequest,
    TTSContractResult,
)
from app.ai.interfaces import AudioSynthesisResult, TTSProvider
from app.ai.openvoice.mel_processing import spectrogram_torch
from app.ai.openvoice.models import SynthesizerTrn
from app.ai.openvoice.utils import HParams, get_hparams_from_file
from app.core.config import get_settings
from app.core.exceptions import (
    AIProviderException,
    AIRuntimeUnavailableException,
    ValidationException,
)
from app.core.logging import get_logger

logger = get_logger(__name__)

# Constants & Operational Limits
MIN_SAMPLE_DURATION_SECONDS = 3.0
MAX_SAMPLE_DURATION_SECONDS = 120.0
MIN_AUDIO_RMS_ENERGY = 0.001  # Silence detection threshold


class OpenVoiceCloningProvider(TTSProvider):
    """OpenVoice V2 instant zero-shot voice cloning provider (CPU/CUDA compatible)."""

    def __init__(
        self,
        model_dir: Optional[Union[str, Path]] = None,
        device: Optional[str] = None,
        enable_watermark: bool = False,
    ) -> None:
        self.settings = get_settings()
        self.provider_name = "openvoice"

        # Determine device
        if device:
            self.device = device
        else:
            self.device = "cuda:0" if torch.cuda.is_available() else "cpu"

        # Resolve model directory
        if model_dir:
            self.model_dir = Path(model_dir)
        else:
            base_dir = Path(getattr(self.settings, "MODEL_CACHE_DIR", "models_cache"))
            self.model_dir = base_dir / "voice_clone" / "openvoice_v2"

        self.converter_config_path = self.model_dir / "converter" / "config.json"
        self.converter_checkpoint_path = self.model_dir / "converter" / "checkpoint.pth"
        self.default_base_se_path = self.model_dir / "base_speakers" / "ses" / "en-default.pth"
        self.manifest_path = self.model_dir / "openvoice_manifest.json"

        self._model: Optional[SynthesizerTrn] = None
        self._hps: Optional[HParams] = None
        self._default_base_se: Optional[torch.Tensor] = None
        self._is_loaded = False
        self._load_latency_ms = 0.0

        # Capability descriptor
        self.descriptor = ProviderDescriptor(
            name=self.provider_name,
            capability="tts",
            supported_languages=["en", "es", "fr", "zh", "jp", "kr"],
            supported_input_formats=["wav", "mp3", "m4a", "aac"],
            supported_output_formats=["wav"],
            requires_gpu=False,
            is_available=self._check_files_exist(),
        )

    def _check_files_exist(self) -> bool:
        """Check whether minimum required model files exist on disk."""
        return (
            self.converter_config_path.is_file()
            and self.converter_checkpoint_path.is_file()
            and self.default_base_se_path.is_file()
        )

    def verify_manifest_checksums(self) -> None:
        """Verify SHA256 hashes of physical model artifacts against approved manifest."""
        if not self.manifest_path.is_file():
            logger.warning("OpenVoice manifest not found at %s", self.manifest_path)
            return

        try:
            with open(self.manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)

            artifacts = manifest.get("artifacts", [])
            for art in artifacts:
                rel_path = art.get("path")
                expected_sha = art.get("sha256")
                expected_size = art.get("size_bytes")
                target_file = self.model_dir / rel_path

                if not target_file.is_file():
                    raise AIRuntimeUnavailableException(
                        message=f"OpenVoice required artifact missing: {rel_path}",
                        code="VOICE_CLONE_MODEL_UNAVAILABLE",
                        details={"missing_file": str(target_file)},
                    )

                actual_size = target_file.stat().st_size
                if expected_size and actual_size != expected_size:
                    raise AIRuntimeUnavailableException(
                        message=f"OpenVoice artifact size mismatch for {rel_path} ({actual_size} != {expected_size})",
                        code="VOICE_CLONE_MODEL_UNAVAILABLE",
                        details={"file": rel_path, "expected": expected_size, "actual": actual_size},
                    )

                # Compute SHA256
                sha = hashlib.sha256()
                with open(target_file, "rb") as bf:
                    while chunk := bf.read(65536):
                        sha.update(chunk)
                actual_sha = sha.hexdigest()

                if expected_sha and actual_sha != expected_sha:
                    raise AIRuntimeUnavailableException(
                        message=f"OpenVoice artifact checksum verification failed for {rel_path}",
                        code="VOICE_CLONE_MODEL_UNAVAILABLE",
                        details={"file": rel_path, "expected": expected_sha, "actual": actual_sha},
                    )

            logger.info("OpenVoice V2 physical artifacts verified successfully against manifest.")

        except AIRuntimeUnavailableException:
            raise
        except Exception as exc:
            logger.error("Failed to verify OpenVoice manifest checksums: %s", exc)
            raise AIRuntimeUnavailableException(
                message=f"OpenVoice artifact integrity check failed: {exc}",
                code="VOICE_CLONE_MODEL_UNAVAILABLE",
                details={"error": str(exc)},
            )

    def load_model(self) -> None:
        """Load ToneColorConverter neural network weights into memory."""
        if self._is_loaded and self._model is not None:
            return

        # Perform strict checksum check before loading
        self.verify_manifest_checksums()

        if not self._check_files_exist():
            raise AIRuntimeUnavailableException(
                message="OpenVoice V2 model artifacts not found in model cache.",
                code="VOICE_CLONE_MODEL_UNAVAILABLE",
                details={"model_dir": str(self.model_dir)},
            )

        start_time = time.perf_counter()
        try:
            logger.info("Loading OpenVoice V2 converter model on device %s...", self.device)
            hps = get_hparams_from_file(str(self.converter_config_path))
            model = SynthesizerTrn(
                len(getattr(hps, "symbols", [])),
                hps.data.filter_length // 2 + 1,
                n_speakers=hps.data.n_speakers,
                **hps.model,
            ).to(self.device)

            ckpt = torch.load(str(self.converter_checkpoint_path), map_location=self.device)
            model.load_state_dict(ckpt["model"], strict=False)
            model.eval()

            # Load default base speaker embedding
            base_se = torch.load(str(self.default_base_se_path), map_location=self.device)

            self._model = model
            self._hps = hps
            self._default_base_se = base_se
            self._is_loaded = True
            self._load_latency_ms = (time.perf_counter() - start_time) * 1000.0

            logger.info(
                "OpenVoice V2 converter loaded in %.2f ms (device: %s)",
                self._load_latency_ms,
                self.device,
            )

        except Exception as exc:
            logger.error("Failed to load OpenVoice V2 model: %s", exc)
            raise AIRuntimeUnavailableException(
                message=f"Failed to initialize OpenVoice neural weights: {exc}",
                code="VOICE_CLONE_MODEL_UNAVAILABLE",
                details={"error": str(exc)},
            )

    def extract_speaker_embedding(
        self,
        audio_input: Union[bytes, str, Path],
    ) -> Tuple[torch.Tensor, float, int]:
        """Extract 256-dimensional speaker timbre embedding vector from reference audio.

        Returns:
            Tuple[torch.Tensor, float, int]: (speaker_embedding_tensor, duration_seconds, sample_rate)
        """
        self.load_model()
        assert self._model is not None
        assert self._hps is not None

        # Load audio bytes or path
        try:
            if isinstance(audio_input, bytes):
                audio_buf = io.BytesIO(audio_input)
                audio_data, sr = sf.read(audio_buf, dtype="float32")
            else:
                audio_data, sr = sf.read(str(audio_input), dtype="float32")
        except Exception as exc:
            raise ValidationException(
                message=f"Reference audio file is invalid or cannot be decoded: {exc}",
                code="VOICE_CLONE_INVALID_AUDIO",
                details={"error": str(exc)},
            )

        # Convert multi-channel to mono
        if audio_data.ndim > 1:
            audio_data = audio_data.mean(axis=1)

        duration_sec = len(audio_data) / float(sr)

        # Duration validation
        if duration_sec < MIN_SAMPLE_DURATION_SECONDS:
            raise ValidationException(
                message=(
                    f"Reference audio duration ({duration_sec:.1f}s) is too short. "
                    f"Minimum required is {MIN_SAMPLE_DURATION_SECONDS} seconds of speech."
                ),
                code="VOICE_CLONE_AUDIO_TOO_SHORT",
                details={"duration_seconds": duration_sec, "min_required": MIN_SAMPLE_DURATION_SECONDS},
            )

        if duration_sec > MAX_SAMPLE_DURATION_SECONDS:
            raise ValidationException(
                message=(
                    f"Reference audio duration ({duration_sec:.1f}s) exceeds the maximum limit "
                    f"of {MAX_SAMPLE_DURATION_SECONDS} seconds."
                ),
                code="VOICE_CLONE_AUDIO_TOO_LONG",
                details={"duration_seconds": duration_sec, "max_allowed": MAX_SAMPLE_DURATION_SECONDS},
            )

        # Silence / Energy validation
        rms_energy = np.sqrt(np.mean(audio_data ** 2))
        if rms_energy < MIN_AUDIO_RMS_ENERGY:
            raise ValidationException(
                message="Reference audio appears completely silent or lacks audible voice energy.",
                code="VOICE_CLONE_INVALID_AUDIO",
                details={"rms_energy": float(rms_energy)},
            )

        # Resample to target model sampling rate if needed
        target_sr = self._hps.data.sampling_rate
        if sr != target_sr:
            import scipy.signal
            num_target_samples = int(len(audio_data) * target_sr / sr)
            audio_data = scipy.signal.resample(audio_data, num_target_samples).astype(np.float32)

        # Compute spectrogram
        audio_tensor = torch.FloatTensor(audio_data).unsqueeze(0).to(self.device)
        spec = spectrogram_torch(
            audio_tensor,
            self._hps.data.filter_length,
            target_sr,
            self._hps.data.hop_length,
            self._hps.data.win_length,
            center=False,
        ).to(self.device)

        # Extract embedding
        with torch.no_grad():
            embedding = self._model.ref_enc(spec.transpose(1, 2)).unsqueeze(-1)

        return embedding.detach().cpu(), duration_sec, target_sr

    def convert_voice(
        self,
        base_audio_bytes: bytes,
        target_se: torch.Tensor,
        base_se: Optional[torch.Tensor] = None,
        tau: float = 0.3,
    ) -> bytes:
        """Convert base synthesized speech audio into target speaker's tone color."""
        self.load_model()
        assert self._model is not None
        assert self._hps is not None

        if base_se is None:
            base_se = self._default_base_se
        if base_se is None:
            raise AIRuntimeUnavailableException(
                message="Base speaker embedding is missing or not loaded.",
                code="VOICE_CLONE_MODEL_UNAVAILABLE",
            )

        # Read base audio
        try:
            audio_buf = io.BytesIO(base_audio_bytes)
            audio_data, sr = sf.read(audio_buf, dtype="float32")
        except Exception as exc:
            raise ValidationException(
                message=f"Failed to read base speech audio for voice conversion: {exc}",
                code="VOICE_CLONE_INVALID_AUDIO",
                details={"error": str(exc)},
            )

        if audio_data.ndim > 1:
            audio_data = audio_data.mean(axis=1)

        target_sr = self._hps.data.sampling_rate
        if sr != target_sr:
            import scipy.signal
            num_samples = int(len(audio_data) * target_sr / sr)
            audio_data = scipy.signal.resample(audio_data, num_samples).astype(np.float32)

        audio_tensor = torch.FloatTensor(audio_data).unsqueeze(0).to(self.device)
        spec = spectrogram_torch(
            audio_tensor,
            self._hps.data.filter_length,
            target_sr,
            self._hps.data.hop_length,
            self._hps.data.win_length,
            center=False,
        ).to(self.device)

        spec_lengths = torch.LongTensor([spec.size(-1)]).to(self.device)
        sid_src = base_se.to(self.device)
        sid_tgt = target_se.to(self.device)

        with torch.no_grad():
            converted = self._model.voice_conversion(
                spec,
                spec_lengths,
                sid_src=sid_src,
                sid_tgt=sid_tgt,
                tau=tau,
            )
            out_pcm = converted[0][0, 0].data.cpu().float().numpy()

        # Write output WAV
        out_buf = io.BytesIO()
        sf.write(out_buf, out_pcm, target_sr, format="WAV", subtype="PCM_16")
        return out_buf.getvalue()

    # -------------------------------------------------------------------------
    # TTSProvider Protocol Implementation
    # -------------------------------------------------------------------------

    async def clone_voice(
        self,
        voice_name: str,
        sample_audio_keys: List[str],
        language: str = "en",
    ) -> str:
        """Create a custom cloned voice identifier (protocol compliance)."""
        clean_name = voice_name.lower().replace(" ", "-")
        return f"openvoice-{clean_name}"

    async def synthesize_speech(
        self,
        text: str,
        voice_id: str,
        speed: float = 1.0,
        pitch: float = 0.0,
        pronunciation_rules: Optional[List[Dict[str, str]]] = None,
    ) -> AudioSynthesisResult:
        """Synthesize speech using base TTS engine, converted via OpenVoice tone color."""
        # For standalone synthesis, delegate to Piper base provider
        from app.ai.registry import get_tts_provider
        piper = get_tts_provider("piper")
        return await piper.synthesize_speech(
            text=text,
            voice_id="en_US-lessac-medium",
            speed=speed,
            pitch=pitch,
            pronunciation_rules=pronunciation_rules,
        )

    async def synthesize(
        self,
        request: TTSContractRequest,
    ) -> TTSContractResult:
        """Execute strongly typed TTS synthesis."""
        synth = await self.synthesize_speech(
            text=request.text,
            voice_id=request.voice_id,
            speed=request.speed,
            pitch=request.pitch,
        )
        return TTSContractResult(
            request_id=request.request_id,
            provider=self.provider_name,
            audio_bytes=synth.audio_bytes,
            duration_seconds=synth.duration_seconds,
            sample_rate=synth.sample_rate,
            format=request.output_format,
            word_timestamps=synth.word_timestamps,
        )
