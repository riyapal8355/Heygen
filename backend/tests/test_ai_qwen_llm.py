"""Comprehensive unit and runtime tests for RealQwenLLMProvider and LLM registry."""

import os
import pytest
from unittest.mock import patch

from app.ai.adapters.mock import MockLLMProvider
from app.ai.adapters.qwen import RealQwenLLMProvider
from app.ai.capabilities import ProviderDescriptor
from app.ai.contracts import LLMContractRequest, LLMContractResult
from app.ai.interfaces import LLMProvider, ScriptGenerationResult
from app.ai.model_registry import ModelInstallStatus, get_model_registry
from app.ai.registry import AICapability, get_ai_registry, get_llm_provider
from app.core.config import get_settings
from app.core.exceptions import (
    AIRuntimeUnavailableException,
    ValidationException,
)


def test_qwen_provider_conforms_to_protocol():
    """Verify RealQwenLLMProvider satisfies runtime-checkable LLMProvider protocol."""
    provider = RealQwenLLMProvider()
    assert isinstance(provider, LLMProvider)
    assert provider.provider_name == "qwen"
    assert hasattr(provider, "generate_script")
    assert hasattr(provider, "stream_script")
    assert hasattr(provider, "generate")


def test_qwen_provider_descriptor_metadata():
    """Verify declarative ProviderDescriptor metadata for Qwen provider."""
    provider = RealQwenLLMProvider()
    desc = provider.descriptor
    assert isinstance(desc, ProviderDescriptor)
    assert desc.name == "qwen"
    assert desc.capability == "llm"
    assert desc.is_local is True
    assert desc.requires_gpu is False
    assert desc.is_available is True
    assert desc.metadata.get("license") == "Apache-2.0"
    assert desc.metadata.get("license_classification") == "COMMERCIAL_SAFE"
    assert desc.metadata.get("commercial_use_permitted") is True


def test_qwen_model_catalog_metadata():
    """Verify Qwen 2.5 0.5B CPU model descriptor in central ModelRegistry."""
    model_reg = get_model_registry()
    model = model_reg.get_model("llm/qwen-2.5-0.5b-cpu")
    assert model is not None
    assert model.name == "Qwen 2.5 0.5B Instruct ONNX (CPU)"
    assert model.provider == "qwen"
    assert model.capability == "llm"
    assert model.requires_gpu is False
    assert "cpu" in model.supported_devices
    assert model.license == "Apache-2.0"
    assert model.license_commercial_permitted is True
    assert model.metadata.get("license_classification") == "COMMERCIAL_SAFE"


def test_qwen_cuda_target_model_metadata():
    """Verify Qwen 2.5 7B GPU model descriptor is registered as unvalidated production target."""
    model_reg = get_model_registry()
    model = model_reg.get_model("llm/qwen-2.5-7b-gpu")
    assert model is not None
    assert model.provider == "qwen"
    assert model.requires_gpu is True
    assert "cuda" in model.supported_devices
    assert model.metadata.get("status") == "production_target_cuda_unvalidated"


def test_real_mode_resolves_qwen_default():
    """Under AI_PROVIDER_MODE='real', get_llm_provider() must resolve Qwen by default."""
    settings = get_settings()
    with patch.object(settings, "AI_PROVIDER_MODE", "real"):
        registry = get_ai_registry()
        provider = registry.get_provider(AICapability.LLM)
        assert isinstance(provider, RealQwenLLMProvider)
        assert provider.provider_name == "qwen"


def test_real_mode_forbids_silent_mock_fallback():
    """Under AI_PROVIDER_MODE='real', attempting to get mock without explicit name fails."""
    settings = get_settings()
    with patch.object(settings, "AI_PROVIDER_MODE", "real"):
        registry = get_ai_registry()
        # Explicit mock request works for test isolation
        mock_p = registry.get_provider(AICapability.LLM, name="mock")
        assert isinstance(mock_p, MockLLMProvider)

        # When real provider is unavailable, it must NEVER silently fall back to mock
        registry.unregister(AICapability.LLM, "qwen")
        try:
            from app.core.exceptions import AIProviderNotFoundException
            with pytest.raises(AIProviderNotFoundException) as exc_info:
                registry.get_provider(AICapability.LLM)
            assert exc_info.value.code == "AI_PROVIDER_NOT_CONFIGURED"
        finally:
            # Re-register qwen for subsequent tests
            registry.register(AICapability.LLM, "qwen", RealQwenLLMProvider(), is_default=False)


def test_mock_mode_resolves_mock_default():
    """Under AI_PROVIDER_MODE='mock', get_llm_provider() resolves MockLLMProvider."""
    settings = get_settings()
    with patch.object(settings, "AI_PROVIDER_MODE", "mock"):
        registry = get_ai_registry()
        provider = registry.get_provider(AICapability.LLM, name="mock")
        assert isinstance(provider, MockLLMProvider)


def test_cuda_device_request_on_cpu_raises_error():
    """Requesting CUDA device on CPU host must raise structured GPU_UNAVAILABLE error."""
    registry = get_ai_registry()
    with pytest.raises(AIRuntimeUnavailableException) as exc_info:
        registry.get_provider(AICapability.LLM, device="cuda")
    assert exc_info.value.code == "GPU_UNAVAILABLE"


def test_missing_model_directory_raises_structured_error():
    """In real mode, if model directory does not exist, an explicit structured error is raised."""
    settings = get_settings()
    with patch.object(settings, "AI_PROVIDER_MODE", "real"):
        provider = RealQwenLLMProvider(model_dir="non_existent_model_directory_xyz")
        with pytest.raises(AIRuntimeUnavailableException) as exc_info:
            provider._ensure_model_loaded()
        assert exc_info.value.code == "REAL_LLM_MODEL_NOT_FOUND"


def test_prompt_empty_validation_error():
    """Empty prompts must be rejected with ValidationException."""
    provider = RealQwenLLMProvider()
    with pytest.raises(ValidationException) as exc_info:
        import asyncio
        asyncio.run(provider.generate_script(""))
    assert exc_info.value.code == "PROMPT_EMPTY"


def test_json_extraction_from_markdown_code_blocks():
    """Verify JSON extractor correctly parses ```json ... ``` blocks."""
    provider = RealQwenLLMProvider()
    raw = """
Here is the video plan:
```json
{
  "title": "Quantum Computing 101",
  "scenes": [
    {
      "sequence": 1,
      "heading": "Intro to Qubits",
      "text": "Welcome to quantum computing.",
      "duration": 5.0,
      "visual_description": "Spinning sphere"
    }
  ]
}
```
Hope you like it!
"""
    parsed = provider._extract_and_parse_json(raw, "Quantum Computing", 1, 5.0)
    assert parsed["title"] == "Quantum Computing 101"
    assert len(parsed["scenes"]) == 1
    assert parsed["scenes"][0]["heading"] == "Intro to Qubits"
    assert parsed["scenes"][0]["duration"] == 5.0


def test_json_extraction_from_raw_braces():
    """Verify JSON extractor parses raw JSON without markdown blocks."""
    provider = RealQwenLLMProvider()
    raw = '{"title": "Eco Friendly Homes", "scenes": [{"sequence": 1, "text": "Build green.", "duration": 6.0}]}'
    parsed = provider._extract_and_parse_json(raw, "Eco Friendly Homes", 1, 6.0)
    assert parsed["title"] == "Eco Friendly Homes"
    assert len(parsed["scenes"]) == 1
    assert parsed["scenes"][0]["text"] == "Build green."


def test_json_heuristic_recovery_on_malformed_output():
    """Verify heuristic extractor cleanly structures unparseable prose into valid scenes."""
    provider = RealQwenLLMProvider()
    raw = "The Future of Medicine. We are entering a new era of genomics. Nanobots will repair cells in minutes."
    parsed = provider._extract_and_parse_json(raw, "Medicine", target_scenes=2, target_duration=10.0)
    assert len(parsed["scenes"]) >= 1
    assert "scenes" in parsed
    assert parsed.get("heuristic_recovery") is True
    for s in parsed["scenes"]:
        assert s["duration"] > 0
        assert len(s["text"]) > 0


@pytest.mark.asyncio
async def test_qwen_generate_contract():
    """Verify strongly typed LLMContractRequest execution returns LLMContractResult."""
    provider = RealQwenLLMProvider()
    req = LLMContractRequest(
        workspace_id="00000000-0000-0000-0000-000000000001",
        user_id="00000000-0000-0000-0000-000000000002",
        prompt="Create a 2-scene video introducing cloud storage.",
        target_scenes=2,
        target_duration_seconds=12.0,
        video_tone="professional",
        max_new_tokens=120,
    )
    res = await provider.generate(req)
    assert isinstance(res, LLMContractResult)
    assert res.status == "succeeded"
    assert len(res.title) > 0
    assert len(res.suggested_scenes) >= 1
    assert res.prompt_tokens > 0
    assert res.completion_tokens > 0
    assert res.tokens_per_second > 0
    assert res.generation_latency > 0
