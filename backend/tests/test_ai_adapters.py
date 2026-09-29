"""Contract and unit tests for AI Provider Protocols, Registry, and Mock Adapters."""

import pytest

from app.ai.adapters.mock import (
    MockASRProvider,
    MockAvatarProvider,
    MockImageProvider,
    MockLLMProvider,
    MockTranslationProvider,
    MockTTSProvider,
    MockVideoProvider,
)
from app.ai.interfaces import (
    ASRProvider,
    AudioSynthesisResult,
    AvatarProvider,
    ImageProvider,
    LLMProvider,
    ScriptGenerationResult,
    TranscriptionResult,
    TranslationProvider,
    TranslationResult,
    TTSProvider,
    VideoProvider,
)
from app.ai.registry import (
    AICapability,
    AIProviderRegistry,
    get_ai_registry,
    get_asr_provider,
    get_avatar_provider,
    get_image_provider,
    get_llm_provider,
    get_translation_provider,
    get_tts_provider,
    get_video_provider,
)
from app.core.exceptions import AIProviderNotFoundException, AIProviderValidationError


# ---------------------------------------------------------------------------
# Protocol Conformance Tests
# ---------------------------------------------------------------------------

def test_mock_providers_satisfy_protocols():
    """Verify that each mock adapter satisfies its corresponding Protocol runtime check."""
    llm = MockLLMProvider()
    tts = MockTTSProvider()
    asr = MockASRProvider()
    translation = MockTranslationProvider()
    avatar = MockAvatarProvider()
    image = MockImageProvider()
    video = MockVideoProvider()

    assert isinstance(llm, LLMProvider)
    assert isinstance(tts, TTSProvider)
    assert isinstance(asr, ASRProvider)
    assert isinstance(translation, TranslationProvider)
    assert isinstance(avatar, AvatarProvider)
    assert isinstance(image, ImageProvider)
    assert isinstance(video, VideoProvider)


# ---------------------------------------------------------------------------
# Mock Adapter Functional Behavior Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mock_llm_provider_generate_and_stream():
    """Verify MockLLMProvider generates valid structured script and streams tokens."""
    provider = MockLLMProvider()

    # 1. Script Generation
    result = await provider.generate_script(
        prompt="Create an onboarding video for remote software engineers",
        system_prompt="Professional tone",
        context={"company": "HeyZen"},
    )
    assert isinstance(result, ScriptGenerationResult)
    assert "remote software engineers" in result.title.lower() or "script:" in result.title.lower()
    assert len(result.script) > 50
    assert len(result.suggested_scenes) >= 3
    assert result.metadata["mock"] is True
    assert result.metadata["system_prompt"] == "Professional tone"

    # 2. Token Streaming
    tokens = []
    async for token in provider.stream_script("Test prompt"):
        tokens.append(token)
    assert len(tokens) > 0
    full_stream = "".join(tokens)
    assert "[Mock LLM]" in full_stream


@pytest.mark.asyncio
async def test_mock_tts_provider_synthesize_and_clone():
    """Verify MockTTSProvider produces valid WAV audio bytes and respects pronunciation rules."""
    provider = MockTTSProvider()

    # 1. Synthesize Speech with pronunciation override
    pronunciation_rules = [
        {"term": "HeyZen", "replacement_phonetic": "Hay-Zen"}
    ]
    result = await provider.synthesize_speech(
        text="Welcome to HeyZen, the future of video.",
        voice_id="voice-preset-1",
        speed=1.0,
        pitch=0.0,
        pronunciation_rules=pronunciation_rules,
    )
    assert isinstance(result, AudioSynthesisResult)
    assert result.sample_rate == 24000
    assert result.duration_seconds >= 1.0
    assert len(result.word_timestamps) > 0
    # Verify valid WAV RIFF header
    assert result.audio_bytes[:4] == b"RIFF"
    assert result.audio_bytes[8:12] == b"WAVE"

    # 2. Clone Voice
    cloned_id = await provider.clone_voice(
        voice_name="Executive Marcus",
        sample_audio_keys=["workspaces/ws-1/samples/sample1.wav"],
    )
    assert "mock-voice-executive-marcus" in cloned_id


@pytest.mark.asyncio
async def test_mock_asr_provider_transcription():
    """Verify MockASRProvider produces deterministic transcription segments."""
    provider = MockASRProvider()
    result = await provider.transcribe_audio(
        audio_storage_key="workspaces/ws-1/audio/recording.wav",
        language="en",
    )
    assert isinstance(result, TranscriptionResult)
    assert result.detected_language == "en"
    assert "recording.wav" in result.full_text
    assert len(result.segments) >= 1
    assert result.segments[0]["confidence"] > 0.9


@pytest.mark.asyncio
async def test_mock_translation_provider_glossary():
    """Verify MockTranslationProvider applies translation with glossary rule respect."""
    provider = MockTranslationProvider()
    glossary = [
        {"term": "HeyZen", "translated_term": "HeyZen Platform"}
    ]
    result = await provider.translate_text(
        text="Welcome to HeyZen",
        source_lang="en",
        target_lang="es",
        glossary_rules=glossary,
    )
    assert isinstance(result, TranslationResult)
    assert result.source_language == "en"
    assert result.target_language == "es"
    assert "[ES]" in result.translated_text
    assert "HeyZen Platform" in result.translated_text


@pytest.mark.asyncio
async def test_mock_avatar_provider_lip_sync_and_training():
    """Verify MockAvatarProvider returns deterministic storage keys for lip-sync and training."""
    provider = MockAvatarProvider()

    # Lip sync
    video_key = await provider.generate_lip_sync(
        avatar_look_key="workspaces/ws-1/avatars/evelyn/look1.png",
        audio_storage_key="workspaces/ws-1/jobs/audio.wav",
        output_format="mp4",
    )
    assert video_key.startswith("mock/renders/lip_sync_")
    assert video_key.endswith(".mp4")

    # Training
    model_key = await provider.train_digital_twin(
        training_video_keys=["workspaces/ws-1/footage/cam1.mp4"],
        avatar_name="Founder John",
    )
    assert "avatar_founder_john" in model_key
    assert model_key.endswith(".weights")


@pytest.mark.asyncio
async def test_mock_image_and_video_providers():
    """Verify MockImageProvider and MockVideoProvider return deterministic asset keys."""
    img_provider = MockImageProvider()
    vid_provider = MockVideoProvider()

    img_key = await img_provider.generate_image(
        prompt="A modern tech conference stage with neon lighting",
        aspect_ratio="16:9",
    )
    assert img_key.startswith("mock/generated_images/")
    assert img_key.endswith(".png")

    vid_key = await vid_provider.generate_video(
        prompt="Drone aerial shot of futuristic skyscrapers",
        duration_seconds=5.0,
        aspect_ratio="16:9",
    )
    assert vid_key.startswith("mock/generated_videos/")
    assert vid_key.endswith(".mp4")


# ---------------------------------------------------------------------------
# Registry Functionality Tests
# ---------------------------------------------------------------------------

def test_registry_default_bootstrapping():
    """Verify get_ai_registry automatically bootstraps default mock adapters for all capabilities."""
    registry = get_ai_registry()
    for cap in AICapability:
        provider = registry.get_provider(cap)
        assert provider is not None
        assert getattr(provider, "provider_name", "") == "mock"


def test_registry_convenience_helpers():
    """Verify top-level convenience accessors resolve to corresponding mock providers."""
    assert isinstance(get_llm_provider(), LLMProvider)
    assert isinstance(get_tts_provider(), TTSProvider)
    assert isinstance(get_asr_provider(), ASRProvider)
    assert isinstance(get_translation_provider(), TranslationProvider)
    assert isinstance(get_avatar_provider(), AvatarProvider)
    assert isinstance(get_image_provider(), ImageProvider)
    assert isinstance(get_video_provider(), VideoProvider)


def test_registry_multi_provider_coexistence():
    """Verify multiple providers can coexist under the same capability."""
    registry = AIProviderRegistry()
    mock_1 = MockLLMProvider()
    mock_2 = MockLLMProvider()

    registry.register(AICapability.LLM, "default-mock", mock_1, is_default=True)
    registry.register(AICapability.LLM, "secondary-mock", mock_2, is_default=False)

    # Resolution by name
    resolved_1 = registry.get_provider(AICapability.LLM, "default-mock")
    resolved_2 = registry.get_provider(AICapability.LLM, "secondary-mock")
    assert resolved_1 is mock_1
    assert resolved_2 is mock_2

    # Default resolution returns default-mock
    resolved_default = registry.get_provider(AICapability.LLM)
    assert resolved_default is mock_1

    # List providers shows both
    available = registry.list_providers(AICapability.LLM)
    assert "default-mock" in available["llm"]
    assert "secondary-mock" in available["llm"]


def test_registry_unknown_capability_raises():
    """Verify querying an unsupported capability raises AIProviderNotFoundException."""
    registry = AIProviderRegistry()
    with pytest.raises(AIProviderNotFoundException) as exc_info:
        registry.get_provider("quantum_computing")
    assert exc_info.value.code == "AI_CAPABILITY_UNKNOWN"


def test_registry_unconfigured_provider_name_raises():
    """Verify requesting a non-existent provider name raises AIProviderNotFoundException."""
    registry = AIProviderRegistry()
    registry.register(AICapability.LLM, "mock", MockLLMProvider(), is_default=True)

    with pytest.raises(AIProviderNotFoundException) as exc_info:
        registry.get_provider(AICapability.LLM, "nonexistent-model-vendor")
    assert exc_info.value.code == "AI_PROVIDER_NOT_CONFIGURED"


def test_registry_invalid_provider_conformance_rejected():
    """Verify registering an object that fails the protocol raises AIProviderValidationError."""
    registry = AIProviderRegistry()

    class InvalidLLM:
        """Does not implement generate_script or stream_script."""
        def say_hello(self):
            return "hello"

    with pytest.raises(AIProviderValidationError) as exc_info:
        registry.register(AICapability.LLM, "bad-provider", InvalidLLM())  # type: ignore
    assert exc_info.value.code == "AI_PROVIDER_PROTOCOL_MISMATCH"


def test_registry_unregister_provider():
    """Verify unregistering a provider removes it cleanly."""
    registry = AIProviderRegistry()
    mock = MockTTSProvider()
    registry.register(AICapability.TTS, "test-tts", mock)
    assert "test-tts" in registry.list_providers(AICapability.TTS)["tts"]

    removed = registry.unregister(AICapability.TTS, "test-tts")
    assert removed is True
    assert "test-tts" not in registry.list_providers(AICapability.TTS)["tts"]
