"""Unit and integration tests for Real CTranslate2 Neural Translation Provider.

Validates protocol conformance, model descriptor, strict real-mode error semantics,
brand glossary terminology masking/unmasking collision safety, telemetry, and CPU inference.
"""

import os
import pytest
from unittest.mock import patch

from app.ai.contracts import TranslationContractRequest, TranslationContractResult
from app.ai.interfaces import TranslationProvider, TranslationResult
from app.ai.adapters.translation import RealCTranslate2TranslationProvider
from app.ai.adapters.mock import MockTranslationProvider
from app.ai.registry import AICapability, AIProviderRegistry, get_ai_registry
from app.ai.model_registry import get_model_registry, ModelInstallStatus
from app.core.exceptions import (
    AIModelIncompatibleException,
    AIProviderException,
    AIRuntimeUnavailableException,
    NotFoundException,
    ValidationException,
)


def test_real_translation_provider_satisfies_protocol():
    """Verify RealCTranslate2TranslationProvider satisfies the TranslationProvider protocol."""
    provider = RealCTranslate2TranslationProvider()
    assert isinstance(provider, TranslationProvider)
    assert provider.provider_name == "ctranslate2"
    assert provider.descriptor.capability == "translation"
    assert "es" in provider.descriptor.supported_languages
    assert "en" in provider.descriptor.supported_languages
    assert provider.descriptor.metadata["commercial_use_permitted"] is True


def test_translation_model_registry_entries():
    """Verify translation model descriptors in the centralized ModelRegistry."""
    registry = get_model_registry()
    model = registry.get_model("translation/opus-mt-en-es-cpu")
    assert model is not None
    assert model.capability == "translation"
    assert model.provider == "ctranslate2"
    assert model.license == "Apache-2.0"
    assert model.license_commercial_permitted is True
    assert model.installation_status == ModelInstallStatus.INSTALLED
    assert "local_cpu" in model.supported_runtimes
    assert model.quantization == "int8"
    assert "76ec296588e2234f9b7dfad5254219a0f5ecb7af" in model.revision

    # Verify research-only model separation (NLLB-200)
    nllb = registry.get_model("translation/nllb-200-cpu")
    assert nllb is not None
    assert nllb.license_commercial_permitted is False


def test_ai_provider_registry_resolution():
    """Verify that the AIProviderRegistry resolves ctranslate2 in real mode and preserves mock in mock mode."""
    reg = get_ai_registry()
    
    # In mock mode, defaults to mock
    with patch("app.ai.registry.get_settings") as mock_settings:
        mock_settings.return_value.AI_PROVIDER_MODE = "mock"
        mock_settings.return_value.DEFAULT_TRANSLATION_PROVIDER = "mock"
        provider = reg.get_translation_provider()
        assert isinstance(provider, MockTranslationProvider)

    # In real mode, resolves ctranslate2
    with patch("app.ai.registry.get_settings") as mock_settings:
        mock_settings.return_value.AI_PROVIDER_MODE = "real"
        mock_settings.return_value.DEFAULT_TRANSLATION_PROVIDER = "ctranslate2"
        provider = reg.get_translation_provider()
        assert isinstance(provider, RealCTranslate2TranslationProvider)

    # Explicit override resolves ctranslate2 or mock
    assert isinstance(reg.get_translation_provider("ctranslate2"), RealCTranslate2TranslationProvider)
    assert isinstance(reg.get_translation_provider("mock"), MockTranslationProvider)


@pytest.mark.asyncio
async def test_real_translation_cpu_inference():
    """Validate real CPU neural translation with MarianMT CTranslate2 INT8."""
    provider = RealCTranslate2TranslationProvider()
    
    text = "Hello and welcome to the presentation."
    result = await provider.translate_text(
        text=text,
        source_lang="en",
        target_lang="es",
    )

    assert isinstance(result, TranslationResult)
    assert result.source_language == "en"
    assert result.target_language == "es"
    assert len(result.translated_text) > 0
    # Spanish translation of "Hello and welcome to the presentation" contains "Hola" or "bienvenido" or "presentación"
    lowered = result.translated_text.lower()
    assert any(w in lowered for w in ["hola", "bienvenid", "presentaci", "presentación"])
    assert len(result.translated_segments) == 1
    assert result.translated_segments[0]["rules_applied"] == 0

    # Also test strongly-typed contract execution
    import uuid
    req = TranslationContractRequest(
        workspace_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        text=text,
        source_language="en",
        target_language="es",
    )
    contract_res = await provider.translate(req)
    assert isinstance(contract_res, TranslationContractResult)
    assert contract_res.status == "succeeded"
    assert contract_res.metrics["provider"] == "ctranslate2"
    assert contract_res.metrics["word_count"] == len(text.split())
    assert contract_res.metrics["char_count"] == len(text)
    assert contract_res.metrics["latency_seconds"] > 0


@pytest.mark.asyncio
async def test_brand_glossary_term_protection():
    """Verify that Brand Glossary rules deterministically preserve brand terms without translation."""
    provider = RealCTranslate2TranslationProvider()
    
    text = "HeyZen uses WorkComposer to create amazing videos."
    rules = [
        {"term": "HeyZen", "translated_term": "HeyZen"},
        {"term": "WorkComposer", "translated_term": "WorkComposer"},
    ]

    result = await provider.translate_text(
        text=text,
        source_lang="en",
        target_lang="es",
        glossary_rules=rules,
    )

    assert "HeyZen" in result.translated_text
    assert "WorkComposer" in result.translated_text
    assert result.translated_segments[0]["rules_applied"] == 2


@pytest.mark.asyncio
async def test_placeholder_collision_safety():
    """Verify that text already containing placeholder-like tokens is handled safely without corruption."""
    provider = RealCTranslate2TranslationProvider()
    
    # Text deliberately contains tokens resembling placeholder formatting: TERM_0000, __GLOSSARY__
    text = "The file is named TERM_0000 and HeyZen processes it."
    rules = [
        {"term": "HeyZen", "translated_term": "HeyZen"},
    ]

    result = await provider.translate_text(
        text=text,
        source_lang="en",
        target_lang="es",
        glossary_rules=rules,
    )

    assert "HeyZen" in result.translated_text
    assert "TERM_0000" in result.translated_text


@pytest.mark.asyncio
async def test_unsupported_language_pair_raises_structured_error():
    """Verify that requesting an unsupported target language raises AIModelIncompatibleException."""
    provider = RealCTranslate2TranslationProvider()
    
    with pytest.raises(AIModelIncompatibleException) as exc_info:
        await provider.translate_text(
            text="Hello world",
            source_lang="en",
            target_lang="ja",  # Japanese not supported by en-es Opus-MT
        )
    assert exc_info.value.code == "LANGUAGE_PAIR_UNSUPPORTED"


@pytest.mark.asyncio
async def test_missing_model_directory_raises_not_found():
    """Verify that pointing to a nonexistent cache dir raises AIRuntimeUnavailableException in real mode."""
    provider = RealCTranslate2TranslationProvider(cache_root="/nonexistent/model/cache")
    
    with pytest.raises(AIRuntimeUnavailableException) as exc_info:
        await provider.translate_text(
            text="Hello world",
            source_lang="en",
            target_lang="es",
        )
    assert exc_info.value.code == "TRANSLATION_MODEL_NOT_FOUND"


@pytest.mark.asyncio
async def test_empty_or_whitespace_text_handled():
    """Verify that empty or whitespace-only text raises ValidationException in real mode."""
    provider = RealCTranslate2TranslationProvider()
    
    with pytest.raises(ValidationException) as exc_info:
        await provider.translate_text(text="   ", source_lang="en", target_lang="es")
    assert exc_info.value.code == "TEXT_EMPTY"


@pytest.mark.asyncio
async def test_unicode_special_characters():
    """Verify that input with punctuation, quotes, and symbols translates cleanly without crashing."""
    provider = RealCTranslate2TranslationProvider()
    
    text = "¿How does 'HeyZen' work with 100% efficiency & 24/7 support?"
    rules = [{"term": "HeyZen", "translated_term": "HeyZen"}]
    
    result = await provider.translate_text(
        text=text,
        source_lang="en",
        target_lang="es",
        glossary_rules=rules,
    )
    assert len(result.translated_text) > 0
    assert "HeyZen" in result.translated_text


def test_strict_real_mode_no_mock_fallback():
    """Verify that in real mode, resolving an unavailable provider fails strictly without falling back to mock."""
    reg = AIProviderRegistry()
    with patch("app.ai.registry.get_settings") as mock_settings:
        mock_settings.return_value.AI_PROVIDER_MODE = "real"
        # Attempting to resolve a non-registered provider must raise AIProviderNotFoundException
        from app.core.exceptions import AIProviderNotFoundException
        with pytest.raises(AIProviderNotFoundException):
            reg.get_translation_provider("nonexistent_provider")
