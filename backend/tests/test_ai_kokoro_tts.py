"""Test suite for Kokoro-82M CPU Neural Text-to-Speech (TTS) Provider.

Validates:
1. Protocol contract adherence (TTSProvider).
2. ProviderDescriptor capability advertising and metadata truthfulness.
3. Auto-registration in AIProviderRegistry and provider isolation.
4. ModelRegistry descriptors and installation verification.
5. Exact artifact SHA256 integrity and voice pack key validation.
6. Real local CPU neural synthesis across all 4 verified Kokoro voices.
7. WAV audio structure (24,000 Hz, mono, 16-bit PCM, non-silent RMS).
8. Session caching and memory reuse.
"""

import hashlib
import io
import os
import time
import wave
import numpy as np
import pytest

from app.ai.adapters.kokoro import DEFAULT_KOKORO_VOICE_ID, KokoroTTSProvider
from app.ai.adapters.piper import PiperTTSProvider
from app.ai.interfaces import AudioSynthesisResult, TTSProvider
from app.ai.model_registry import ModelInstallStatus, get_model_registry
from app.ai.registry import AICapability, get_ai_registry, get_tts_provider
from app.core.exceptions import NotFoundException, ValidationException

EXPECTED_MODEL_SHA256 = "beb0d1848dee9a49da392cc3df26958d46cfa35d321edf434f52949153f0df3a"
EXPECTED_VOICES_SHA256 = "bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d"


@pytest.fixture
def kokoro_provider() -> KokoroTTSProvider:
    return KokoroTTSProvider()


class TestKokoroTTSProvider:
    """Unit and functional validation for KokoroTTSProvider."""

    def test_satisfies_tts_provider_protocol(self, kokoro_provider: KokoroTTSProvider):
        """Verify KokoroTTSProvider satisfies runtime Protocol contract."""
        assert isinstance(kokoro_provider, TTSProvider)
        assert kokoro_provider.provider_name == "kokoro"

    def test_descriptor_metadata(self, kokoro_provider: KokoroTTSProvider):
        """Verify descriptor capabilities and metadata."""
        desc = kokoro_provider.descriptor
        assert desc.name == "kokoro"
        assert desc.capability == "tts"
        assert desc.version == "1.0.0"
        assert desc.is_local is True
        assert desc.requires_gpu is False
        assert desc.supported_output_formats == ["wav"]
        assert "en" in desc.supported_languages
        assert "en-us" in desc.supported_languages
        assert "en-gb" in desc.supported_languages
        assert "es" in desc.supported_languages
        assert "fr" in desc.supported_languages
        assert desc.metadata["model_license"] == "Apache-2.0"
        assert desc.metadata["license_classification"] == "COMMERCIAL_SAFE"
        assert desc.metadata["commercial_use_permitted"] is True

    def test_registry_resolution_and_provider_isolation(self):
        """Verify strict provider isolation between Piper and Kokoro."""
        registry = get_ai_registry()

        kokoro = registry.get_provider(AICapability.TTS, "kokoro")
        piper = registry.get_provider(AICapability.TTS, "piper")

        assert isinstance(kokoro, KokoroTTSProvider)
        assert isinstance(piper, PiperTTSProvider)
        assert kokoro.provider_name == "kokoro"
        assert piper.provider_name == "piper"

        # Direct helper isolation
        assert get_tts_provider("kokoro").provider_name == "kokoro"
        assert get_tts_provider("piper").provider_name == "piper"

    def test_model_registry_descriptors(self):
        """Verify Kokoro descriptors in global ModelRegistry."""
        reg = get_model_registry()

        base_model = reg.get_model("tts/kokoro-cpu")
        assert base_model is not None
        assert base_model.provider == "kokoro"
        assert base_model.capability == "tts"
        assert base_model.requires_gpu is False
        assert base_model.installation_status == ModelInstallStatus.VERIFIED
        assert base_model.checksum_sha256 == EXPECTED_MODEL_SHA256
        assert base_model.license == "Apache-2.0"
        assert base_model.license_commercial_permitted is True

        # Target voices
        heart = reg.get_model("tts/kokoro-en-heart-cpu")
        assert heart is not None
        assert heart.metadata["voice_id"] == "af_heart"
        assert heart.metadata["voice_license"] == "Apache-2.0"

        emma = reg.get_model("tts/kokoro-en-emma-cpu")
        assert emma is not None
        assert emma.metadata["voice_id"] == "bf_emma"
        assert emma.metadata["voice_license"] == "Apache-2.0"

        dora = reg.get_model("tts/kokoro-es-dora-cpu")
        assert dora is not None
        assert dora.metadata["voice_id"] == "ef_dora"
        assert dora.metadata["voice_license"] == "Apache-2.0"

        siwis = reg.get_model("tts/kokoro-fr-siwis-cpu")
        assert siwis is not None
        assert siwis.metadata["voice_id"] == "ff_siwis"
        assert siwis.metadata["voice_license"] == "CC BY 4.0"
        assert siwis.metadata["model_license"] == "Apache-2.0"

    def test_artifact_files_and_checksums(self, kokoro_provider: KokoroTTSProvider):
        """Verify physical ONNX model and voice pack artifacts and SHA256 checksums."""
        model_path, voices_path = kokoro_provider._resolve_paths()

        assert os.path.isfile(model_path), f"Missing model: {model_path}"
        assert os.path.isfile(voices_path), f"Missing voices: {voices_path}"

        # Verify model SHA256
        h_model = hashlib.sha256()
        with open(model_path, "rb") as f:
            while chunk := f.read(1024 * 1024):
                h_model.update(chunk)
        calc_model_sha = h_model.hexdigest()
        assert calc_model_sha == EXPECTED_MODEL_SHA256, f"Model SHA256 mismatch: {calc_model_sha}"

        # Verify voices SHA256
        h_voices = hashlib.sha256()
        with open(voices_path, "rb") as f:
            while chunk := f.read(1024 * 1024):
                h_voices.update(chunk)
        calc_voices_sha = h_voices.hexdigest()
        assert calc_voices_sha == EXPECTED_VOICES_SHA256, f"Voices SHA256 mismatch: {calc_voices_sha}"

        # Verify voice pack contains all 4 target voices
        v_data = np.load(voices_path)
        for target_voice in ["af_heart", "bf_emma", "ef_dora", "ff_siwis"]:
            assert target_voice in v_data, f"Target voice {target_voice} not in voices-v1.0.bin"
            assert v_data[target_voice].shape == (510, 1, 256)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "voice_id,text,expected_lang",
        [
            ("af_heart", "Hello, this is a HeyZen voice preview.", "en-us"),
            ("bf_emma", "Hello, this is a HeyZen voice preview.", "en-gb"),
            ("ef_dora", "Hola, esta es una vista previa de voz de HeyZen.", "es"),
            ("ff_siwis", "Bonjour, ceci est un aperçu vocal de HeyZen.", "fr-fr"),
        ],
    )
    async def test_real_synthesis_all_target_voices(
        self, kokoro_provider: KokoroTTSProvider, voice_id: str, text: str, expected_lang: str
    ):
        """Execute real neural inference for each of the 4 Kokoro voices."""
        detected_lang = kokoro_provider._detect_lang_for_voice(voice_id)
        assert detected_lang == expected_lang

        t0 = time.perf_counter()
        result = await kokoro_provider.synthesize_speech(text=text, voice_id=voice_id)
        latency = time.perf_counter() - t0

        assert isinstance(result, AudioSynthesisResult)
        assert result.sample_rate == 24000
        assert result.duration_seconds > 1.0
        assert len(result.audio_bytes) > 20000

        # Validate WAV structure
        with wave.open(io.BytesIO(result.audio_bytes), "rb") as wf:
            assert wf.getnchannels() == 1
            assert wf.getsampwidth() == 2
            assert wf.getframerate() == 24000
            frames = wf.readframes(wf.getnframes())
            samples = np.frombuffer(frames, dtype=np.int16)
            assert len(samples) > 0

            rms = float(np.sqrt(np.mean(samples.astype(np.float64) ** 2)))
            peak = float(np.max(np.abs(samples)))
            # Non-silent signal check
            assert peak > 1000, f"Peak amplitude too low: {peak}"
            assert rms > 200, f"RMS energy too low: {rms}"

        rtf = latency / result.duration_seconds
        assert rtf < 5.0, f"RTF too high: {rtf}"

    @pytest.mark.asyncio
    async def test_session_caching_and_speed_control(self, kokoro_provider: KokoroTTSProvider):
        """Verify session is cached across calls and speed adjustment works."""
        engine_1 = kokoro_provider._get_or_load_engine()
        engine_2 = kokoro_provider._get_or_load_engine()
        assert engine_1 is engine_2, "Kokoro engine instance should be cached and reused"

        # Speed synthesis
        res_fast = await kokoro_provider.synthesize_speech("Short test.", voice_id="af_heart", speed=1.5)
        res_slow = await kokoro_provider.synthesize_speech("Short test.", voice_id="af_heart", speed=0.8)
        assert res_fast.duration_seconds < res_slow.duration_seconds

    @pytest.mark.asyncio
    async def test_validation_errors(self, kokoro_provider: KokoroTTSProvider):
        """Verify appropriate validation errors on empty text or unknown voices."""
        with pytest.raises(ValidationException):
            await kokoro_provider.synthesize_speech("", voice_id="af_heart")

        with pytest.raises(NotFoundException):
            await kokoro_provider.synthesize_speech("Test text.", voice_id="non_existent_kokoro_voice")
