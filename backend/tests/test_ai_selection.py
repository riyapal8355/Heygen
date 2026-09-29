"""Unit and functional tests for deterministic model and runtime selection."""

import pytest

from app.ai.hardware import detect_hardware
from app.ai.selection import select_model_and_runtime
from app.core.exceptions import (
    AIModelIncompatibleException,
    AIRuntimeUnavailableException,
    NotFoundException,
)


def test_selection_default_mock_mode():
    """Verify mock mode returns deterministic mock model and CPU runtime."""
    model, runtime = select_model_and_runtime("tts", mode="mock")
    assert model.provider == "mock"
    assert model.capability == "tts"
    assert runtime.runtime_id == "runtime-local-cpu"


def test_selection_real_mode_cpu_model():
    """Verify real mode selects CPU model on non-CUDA host."""
    hw = detect_hardware()
    model, runtime = select_model_and_runtime("tts", mode="real", hardware=hw)

    if not hw.gpu.cuda_available:
        # Must select CPU model (e.g. Piper) and CPU runtime
        assert model.requires_gpu is False
        assert runtime.device_type.value == "cpu"
        assert model.model_id == "tts/piper-cpu"


def test_selection_preferred_device_cuda_on_non_cuda_host():
    """Verify explicitly requesting CUDA device on non-CUDA host raises AI_GPU_UNAVAILABLE."""
    hw = detect_hardware()
    if not hw.gpu.cuda_available:
        with pytest.raises(AIRuntimeUnavailableException) as exc_info:
            select_model_and_runtime("tts", preferred_device="cuda", hardware=hw)
        assert exc_info.value.code == "AI_GPU_UNAVAILABLE"


def test_selection_explicit_model_id_not_found():
    """Verify requesting non-existent model ID raises NotFoundException."""
    with pytest.raises(NotFoundException) as exc_info:
        select_model_and_runtime("tts", model_id="tts/nonexistent-model")
    assert exc_info.value.code == "AI_MODEL_NOT_FOUND"


def test_selection_explicit_gpu_model_on_non_cuda_host():
    """Verify explicitly requesting a GPU-only model on non-CUDA host raises AIModelIncompatibleException."""
    hw = detect_hardware()
    if not hw.gpu.cuda_available:
        with pytest.raises(AIModelIncompatibleException) as exc_info:
            select_model_and_runtime("tts", model_id="tts/xtts-v2-gpu", hardware=hw)
        assert exc_info.value.code == "AI_MODEL_INCOMPATIBLE"
