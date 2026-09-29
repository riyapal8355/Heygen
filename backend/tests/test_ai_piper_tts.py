"""Comprehensive unit and contract tests for Real Piper TTS Provider Adapter.

Validates:
- Protocol conformance (TTSProvider)
- Real speech synthesis producing valid 16-bit mono 22,050 Hz PCM WAV audio
- Audio waveform verification (non-empty, non-silent, valid RIFF/WAVE header)
- Speed scaling (faster speeds generate proportionally shorter durations)
- Brand Glossary / pronunciation rule substitutions
- Strongly typed TTS contract execution (TTSContractRequest -> TTSContractResult)
- Voice cloning hardware boundary (raises VOICE_CLONING_REQUIRES_GPU)
- Error handling on invalid/empty text
- AI provider and model registry discovery and resolution
"""

import io
import wave
import pytest

from app.ai.adapters.mock import MockTTSProvider
from app.ai.adapters.piper import DEFAULT_PIPER_VOICE_ID, PiperTTSProvider
from app.ai.contracts import TTSContractRequest, TTSContractResult
from app.ai.interfaces import AudioSynthesisResult, TTSProvider
from app.ai.lifecycle import get_lifecycle_manager
from app.ai.model_registry import ModelInstallStatus, get_model_registry
from app.ai.registry import AICapability, get_ai_registry, get_tts_provider
from app.core.exceptions import AIProviderException


@pytest.mark.asyncio
async def test_piper_provider_satisfies_protocol():
    """Verify PiperTTSProvider satisfies runtime Protocol contract and descriptor metadata."""
    provider = PiperTTSProvider()
    assert isinstance(provider, TTSProvider)
    assert provider.provider_name == "piper"
    assert provider.descriptor.capability == "tts"
    assert provider.descriptor.is_local is True
    assert provider.descriptor.requires_gpu is False
    assert provider.descriptor.is_available is True
    assert "wav" in provider.descriptor.supported_output_formats
    assert "en" in provider.descriptor.supported_languages


@pytest.mark.asyncio
async def test_piper_synthesizes_real_speech_audio():
    """Primary Acceptance Test: Take text and generate a REAL non-silent speech audio asset."""
    provider = PiperTTSProvider()
    input_text = "Hello from HeyZen."

    result = await provider.synthesize_speech(text=input_text, voice_id=DEFAULT_PIPER_VOICE_ID)

    assert isinstance(result, AudioSynthesisResult)
    assert result.sample_rate == 22050
    assert result.duration_seconds > 0.5
    assert len(result.audio_bytes) > 20000

    # Verify RIFF/WAVE standard header
    assert result.audio_bytes[:4] == b"RIFF"
    assert result.audio_bytes[8:12] == b"WAVE"

    # Deep inspection of parsed WAV structure
    with io.BytesIO(result.audio_bytes) as buf:
        with wave.open(buf, "rb") as wf:
            assert wf.getnchannels() == 1  # Mono
            assert wf.getsampwidth() == 2  # 16-bit PCM
            assert wf.getframerate() == 22050
            n_frames = wf.getnframes()
            assert n_frames > 10000
            # Confirm audio waveform is not purely silent zeros
            raw_frames = wf.readframes(n_frames)
            assert raw_frames != b"\x00" * len(raw_frames)
            # Verify calculated duration matches frames / framerate
            calculated_duration = round(n_frames / float(wf.getframerate()), 3)
            assert abs(result.duration_seconds - calculated_duration) < 0.05

    # Check word timestamps
    assert len(result.word_timestamps) == 3
    words = [t["word"] for t in result.word_timestamps]
    assert words == ["Hello", "from", "HeyZen."]
    for ts in result.word_timestamps:
        assert ts["start"] >= 0.0
        assert ts["end"] > ts["start"]


@pytest.mark.asyncio
async def test_piper_speed_multiplier_effects():
    """Verify speech rate scaling: speed=2.0 generates shorter audio than speed=1.0."""
    provider = PiperTTSProvider()
    text = "Autonomous AI video generation studio powered by lightweight neural text to speech."

    res_normal = await provider.synthesize_speech(text=text, speed=1.0)
    res_fast = await provider.synthesize_speech(text=text, speed=2.0)

    assert res_fast.duration_seconds < res_normal.duration_seconds
    assert len(res_fast.audio_bytes) < len(res_normal.audio_bytes)


@pytest.mark.asyncio
async def test_piper_pronunciation_rules_substitution():
    """Verify Brand Glossary phonetic substitution rules are applied before speech synthesis."""
    provider = PiperTTSProvider()
    rules = [
        {"term": "AI", "replacement_phonetic": "Artificial Intelligence"}
    ]

    result = await provider.synthesize_speech(
        text="Experience AI today.",
        pronunciation_rules=rules,
    )

    words = [t["word"] for t in result.word_timestamps]
    assert "Artificial" in words
    assert "Intelligence" in words
    assert "AI" not in words


@pytest.mark.asyncio
async def test_piper_typed_contract_execution():
    """Verify strongly typed TTSContractRequest and TTSContractResult execution."""
    import uuid
    provider = PiperTTSProvider()
    request = TTSContractRequest(
        workspace_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        text="Next generation synthetic media platform.",
        voice_id="en_US-lessac-medium",
        speed=1.0,
        pitch=0.0,
        output_format="wav",
    )

    result = await provider.synthesize(request)

    assert isinstance(result, TTSContractResult)
    assert result.status == "succeeded"
    assert result.sample_rate == 22050
    assert result.channels == 1
    assert result.word_count == 5
    assert len(result.word_timestamps) == 5
    assert result.duration_seconds > 0.5
    assert result.metrics["provider"] == "piper"
    assert result.metrics["is_real_ai"] is True


@pytest.mark.asyncio
async def test_piper_voice_cloning_requires_gpu():
    """Verify zero-shot voice cloning strictly raises VOICE_CLONING_REQUIRES_GPU on CPU Piper."""
    provider = PiperTTSProvider()

    with pytest.raises(AIProviderException) as exc_info:
        await provider.clone_voice(
            voice_name="Executive Avatar",
            sample_audio_keys=["workspaces/sample.wav"],
        )

    assert exc_info.value.code == "VOICE_CLONING_REQUIRES_GPU"
    assert "CUDA GPU" in exc_info.value.message


@pytest.mark.asyncio
async def test_piper_empty_text_error():
    """Verify empty or whitespace-only text raises TTS_EMPTY_TEXT."""
    provider = PiperTTSProvider()

    with pytest.raises(AIProviderException) as exc_info:
        await provider.synthesize_speech("   ")

    assert exc_info.value.code == "TTS_EMPTY_TEXT"


def test_piper_registry_and_model_catalog_integration():
    """Verify Piper is registered in AIProviderRegistry and ModelRegistry."""
    # 1. AIProviderRegistry
    registry = get_ai_registry()
    piper = registry.get_tts_provider("piper")
    assert isinstance(piper, PiperTTSProvider)

    mock = registry.get_tts_provider("mock")
    assert isinstance(mock, MockTTSProvider)

    # 2. ModelRegistry
    model_reg = get_model_registry()
    piper_desc = model_reg.get_model("tts/piper-cpu")
    assert piper_desc is not None
    assert piper_desc.provider == "piper"
    assert piper_desc.requires_gpu is False
    assert piper_desc.checksum_sha256 == "5efe09e69902187827af646e1a6e9d269dee769f9877d17b16b1b46eeaaf019f"
    assert piper_desc.installation_status in (ModelInstallStatus.INSTALLED, ModelInstallStatus.VERIFIED)

    # 3. ModelLifecycleManager
    lifecycle = get_lifecycle_manager()
    is_valid = lifecycle.verify_artifact(piper_desc)
    assert is_valid is True


@pytest.mark.asyncio
async def test_piper_missing_model_raises_not_found():
    """Verify requesting an uninstalled voice model raises NotFoundException."""
    from app.core.exceptions import NotFoundException
    provider = PiperTTSProvider()
    with pytest.raises(NotFoundException) as exc_info:
        await provider.synthesize_speech("Hello.", voice_id="nonexistent_voice_model_404")
    assert exc_info.value.code == "AI_MODEL_NOT_FOUND"


@pytest.mark.asyncio
async def test_piper_unsupported_language_raises():
    """Verify requesting an unsupported language raises TTS_UNSUPPORTED_LANGUAGE."""
    provider = PiperTTSProvider()
    with pytest.raises(AIProviderException) as exc_info:
        await provider.synthesize_speech("Ni hao.", language="zh")
    assert exc_info.value.code == "TTS_UNSUPPORTED_LANGUAGE"


@pytest.mark.asyncio
async def test_piper_text_too_long_raises():
    """Verify text exceeding max safety threshold raises TTS_TEXT_TOO_LONG."""
    provider = PiperTTSProvider()
    long_text = "word " * 3000  # 15000 chars > 10000 limit
    with pytest.raises(AIProviderException) as exc_info:
        await provider.synthesize_speech(long_text)
    assert exc_info.value.code == "TTS_TEXT_TOO_LONG"


@pytest.mark.asyncio
async def test_piper_unload_voice():
    """Verify unload_voice reclaims cached model instances from memory."""
    provider = PiperTTSProvider()
    # Synthesize to ensure voice is loaded in memory
    await provider.synthesize_speech("Cache priming.")
    assert len(provider._voice_cache) > 0

    # Unload specific voice
    provider.unload_voice("en_US-lessac-medium")
    assert len(provider._voice_cache) == 0


def test_piper_lifecycle_checksum_mismatch(tmp_path):
    """Verify verify_model_checksum catches corrupted or tampered model artifacts."""
    from app.ai.lifecycle import verify_model_checksum
    from app.core.exceptions import AIModelSecurityException

    corrupted_file = tmp_path / "corrupted_model.onnx"
    corrupted_file.write_bytes(b"corrupted_binary_data")

    with pytest.raises(AIModelSecurityException) as exc_info:
        verify_model_checksum(str(corrupted_file), "5efe09e69902187827af646e1a6e9d269dee769f9877d17b16b1b46eeaaf019f")
    assert exc_info.value.code == "AI_CHECKSUM_MISMATCH"


def test_piper_lifecycle_path_traversal_blocked():
    """Verify resolve_safe_cache_path strictly prevents directory traversal attacks."""
    from app.ai.lifecycle import resolve_safe_cache_path
    from app.core.exceptions import AIModelSecurityException

    with pytest.raises(AIModelSecurityException) as exc_info:
        resolve_safe_cache_path("models_cache", "../../etc/passwd")
    assert exc_info.value.code == "AI_PATH_TRAVERSAL_DETECTED"

