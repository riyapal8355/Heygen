"""Unit and functional tests for ModelRegistry and ModelDescriptor."""

import pytest

from app.ai.hardware import detect_hardware
from app.ai.model_registry import (
    ModelDescriptor,
    ModelHealthStatus,
    ModelInstallStatus,
    ModelRegistry,
    get_model_registry,
)


def test_model_registry_baseline_catalog_populated():
    """Verify standard singleton initializes with pre-evaluated models across all 7 capabilities."""
    registry = get_model_registry()
    models = registry.list_models()
    assert len(models) >= 14

    # Capabilities represented
    capabilities = {m.capability for m in models}
    expected = {"tts", "asr", "translation", "avatar", "image", "video", "llm"}
    assert expected.issubset(capabilities)


def test_model_descriptor_query_helpers():
    """Verify ModelDescriptor device, language, and container format filters."""
    desc = ModelDescriptor(
        model_id="tts/test-custom",
        name="Test Custom TTS",
        provider="custom",
        capability="tts",
        supported_devices=["cpu", "cuda"],
        supported_languages=["en", "es", "fr"],
        supported_output_formats=["wav", "mp3"],
        requires_gpu=False,
    )

    assert desc.supports_device("cpu") is True
    assert desc.supports_device("CUDA") is True
    assert desc.supports_device("rocm") is False

    assert desc.supports_language("en") is True
    assert desc.supports_language("FR") is True
    assert desc.supports_language("de") is False

    assert desc.supports_format("wav") is True
    assert desc.supports_format("MP3") is True
    assert desc.supports_format("ogg") is False


def test_register_and_unregister_model():
    """Verify dynamic registration, lookup, and unregistration."""
    registry = ModelRegistry()

    model = ModelDescriptor(
        model_id="tts/dynamic-piper",
        name="Dynamic Piper",
        provider="piper",
        capability="tts",
        supported_devices=["cpu"],
        requires_gpu=False,
    )

    registry.register_model(model, is_default=True)
    assert registry.get_model("tts/dynamic-piper") is not None
    assert registry.get_default_model("tts").model_id == "tts/dynamic-piper"

    # Unregister
    removed = registry.unregister_model("tts/dynamic-piper")
    assert removed is True
    assert registry.get_model("tts/dynamic-piper") is None


def test_list_models_with_filters():
    """Verify filtering models by capability and GPU requirements."""
    registry = get_model_registry()

    tts_models = registry.list_models(capability="tts")
    assert len(tts_models) >= 3
    assert all(m.capability == "tts" for m in tts_models)

    gpu_models = registry.list_models(requires_gpu=True)
    assert len(gpu_models) >= 4
    assert all(m.requires_gpu is True for m in gpu_models)

    cpu_models = registry.list_models(requires_gpu=False)
    assert len(cpu_models) >= 7
    assert all(m.requires_gpu is False for m in cpu_models)


def test_find_compatible_models_on_host():
    """Verify find_compatible_models returns models runnable on host hardware."""
    registry = get_model_registry()
    hw = detect_hardware()

    compat_tts = registry.find_compatible_models("tts", hardware=hw)
    assert len(compat_tts) >= 1

    # In host without CUDA, no compatible model should strictly require GPU
    if not hw.gpu.cuda_available:
        for model in compat_tts:
            assert model.requires_gpu is False
