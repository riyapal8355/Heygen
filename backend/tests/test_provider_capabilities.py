"""Unit and functional tests for ProviderDescriptor and AI capability discovery."""

import pytest

from app.ai.capabilities import ProviderDescriptor
from app.ai.registry import (
    AICapability,
    AIProviderRegistry,
    get_ai_registry,
)
from app.ai.adapters.mock import MockTTSProvider, MockLLMProvider


def test_provider_descriptor_attributes_and_helpers():
    """Verify ProviderDescriptor attribute defaults and helper query methods."""
    desc = ProviderDescriptor(
        name="custom-tts",
        capability="tts",
        supported_languages=["en", "es"],
        supported_input_formats=["txt"],
        supported_output_formats=["wav", "mp3"],
        requires_gpu=True,
        is_available=True,
    )
    assert desc.name == "custom-tts"
    assert desc.capability == "tts"
    assert desc.requires_gpu is True
    assert desc.is_available is True

    # Language support
    assert desc.supports_language("en") is True
    assert desc.supports_language("ES") is True
    assert desc.supports_language("fr") is False

    # Format support
    assert desc.supports_output_format("wav") is True
    assert desc.supports_output_format("MP3") is True
    assert desc.supports_output_format("aac") is False

    # Wildcard support
    wildcard_desc = ProviderDescriptor(
        name="wildcard-llm",
        capability="llm",
        supported_languages=["*"],
    )
    assert wildcard_desc.supports_language("ja") is True
    assert wildcard_desc.supports_language("de") is True


def test_registry_descriptor_association_and_query():
    """Verify registering a provider preserves and exposes its ProviderDescriptor."""
    registry = AIProviderRegistry()
    mock_tts = MockTTSProvider()

    # Register with auto-discovered descriptor from mock adapter
    registry.register(AICapability.TTS, "mock", mock_tts, is_default=True)

    desc = registry.get_descriptor(AICapability.TTS, "mock")
    assert desc is not None
    assert desc.name == "mock"
    assert desc.capability == "tts"
    assert desc.supports_language("en") is True

    # Register custom provider with explicit descriptor
    custom_desc = ProviderDescriptor(
        name="xtts-v2",
        capability="tts",
        requires_gpu=True,
        supported_languages=["en", "de", "fr"],
        supported_output_formats=["wav"],
        is_available=True,
    )
    registry.register(AICapability.TTS, "xtts-v2", mock_tts, descriptor=custom_desc)

    resolved_desc = registry.get_descriptor(AICapability.TTS, "xtts-v2")
    assert resolved_desc is not None
    assert resolved_desc.requires_gpu is True
    assert resolved_desc.supports_language("de") is True


def test_registry_list_descriptors():
    """Verify list_descriptors retrieves descriptors across all or specific capabilities."""
    registry = AIProviderRegistry()
    mock_tts = MockTTSProvider()
    mock_llm = MockLLMProvider()

    registry.register(AICapability.TTS, "mock-tts", mock_tts)
    registry.register(AICapability.LLM, "mock-llm", mock_llm)

    # Filtered
    tts_descs = registry.list_descriptors(AICapability.TTS)
    assert len(tts_descs) == 1
    assert tts_descs[0].capability == "tts"

    # All
    all_descs = registry.list_descriptors()
    assert len(all_descs) == 2


def test_registry_find_capable_provider():
    """Verify find_capable_provider selects the appropriate provider based on criteria."""
    registry = AIProviderRegistry()
    mock_tts = MockTTSProvider()

    # Provider 1: CPU English only
    cpu_desc = ProviderDescriptor(
        name="cpu-tts",
        capability="tts",
        requires_gpu=False,
        supported_languages=["en"],
        supported_output_formats=["wav"],
        is_available=True,
    )
    registry.register(AICapability.TTS, "cpu-tts", mock_tts, descriptor=cpu_desc, is_default=True)

    # Provider 2: GPU Multilingual
    gpu_desc = ProviderDescriptor(
        name="gpu-tts",
        capability="tts",
        requires_gpu=True,
        supported_languages=["en", "es", "fr", "de", "ja"],
        supported_output_formats=["wav", "mp3"],
        is_available=True,
    )
    registry.register(AICapability.TTS, "gpu-tts", mock_tts, descriptor=gpu_desc)

    # Provider 3: Unavailable provider
    offline_desc = ProviderDescriptor(
        name="offline-tts",
        capability="tts",
        requires_gpu=False,
        supported_languages=["zh"],
        is_available=False,
    )
    registry.register(AICapability.TTS, "offline-tts", mock_tts, descriptor=offline_desc)

    # Find CPU English
    match_1 = registry.find_capable_provider(AICapability.TTS, language="en", require_gpu=False)
    assert match_1 == "cpu-tts"

    # Find Japanese (only GPU provider supports it)
    match_2 = registry.find_capable_provider(AICapability.TTS, language="ja")
    assert match_2 == "gpu-tts"

    # Find GPU provider with mp3 output
    match_3 = registry.find_capable_provider(AICapability.TTS, format_name="mp3", require_gpu=True)
    assert match_3 == "gpu-tts"

    # Find Chinese (offline provider should be excluded)
    match_4 = registry.find_capable_provider(AICapability.TTS, language="zh")
    assert match_4 is None


def test_registry_availability_check():
    """Verify is_provider_available accurately reflects descriptor availability."""
    registry = AIProviderRegistry()
    mock_llm = MockLLMProvider()

    desc = ProviderDescriptor(name="test-llm", capability="llm", is_available=True)
    registry.register(AICapability.LLM, "test-llm", mock_llm, descriptor=desc)
    assert registry.is_provider_available(AICapability.LLM, "test-llm") is True

    # Mark offline
    desc.is_available = False
    assert registry.is_provider_available(AICapability.LLM, "test-llm") is False


def test_default_bootstrapped_descriptors():
    """Verify singleton get_ai_registry registers descriptors for all 7 mock adapters."""
    registry = get_ai_registry()
    for cap in AICapability:
        desc = registry.get_descriptor(cap)
        assert desc is not None
        assert desc.name == "mock"
        assert desc.capability == cap.value
        assert desc.is_available is True
