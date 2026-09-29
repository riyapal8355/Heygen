"""Unit and functional tests for AIRuntime layer (CPU and GPU runtimes)."""

import pytest

from app.ai.hardware import detect_hardware
from app.ai.model_registry import ModelDescriptor
from app.ai.runtimes import (
    DeviceType,
    LocalCPURuntime,
    LocalGPURuntime,
    RuntimeHealth,
    RuntimeRegistry,
    RuntimeType,
    get_runtime_registry,
)
from app.core.exceptions import AIRuntimeUnavailableException


@pytest.mark.asyncio
async def test_local_cpu_runtime_initialization_and_health():
    """Verify LocalCPURuntime is operational on this host."""
    runtime = LocalCPURuntime("test-cpu-runtime")
    assert runtime.initialize() is True
    assert runtime.is_device_available() is True
    assert runtime.check_health() in (RuntimeHealth.HEALTHY, RuntimeHealth.DEGRADED)
    assert runtime.device_type == DeviceType.CPU
    assert runtime.runtime_type == RuntimeType.LOCAL_CPU


@pytest.mark.asyncio
async def test_local_gpu_runtime_on_non_cuda_host():
    """Verify LocalGPURuntime reports unavailable on a host lacking CUDA."""
    hw = detect_hardware()
    runtime = LocalGPURuntime("test-gpu-runtime")

    if not hw.gpu.cuda_available:
        assert runtime.initialize() is False
        assert runtime.is_device_available() is False
        assert runtime.check_health() == RuntimeHealth.UNAVAILABLE

        # Compatibility check must return False
        dummy_gpu_model = ModelDescriptor(
            model_id="tts/test-gpu",
            name="Test GPU",
            provider="test",
            capability="tts",
            requires_gpu=True,
            supported_devices=["cuda"],
        )
        is_compat, reason = runtime.check_compatibility(dummy_gpu_model)
        assert is_compat is False
        assert "CUDA" in reason

        # Execution attempt must raise AIRuntimeUnavailableException with code AI_GPU_UNAVAILABLE
        with pytest.raises(AIRuntimeUnavailableException) as exc_info:
            await runtime.execute("tts", dummy_gpu_model, request=None)
        assert exc_info.value.code == "AI_GPU_UNAVAILABLE"


def test_runtime_registry_lookup_and_registration():
    """Verify RuntimeRegistry registers and resolves runtimes by ID and device."""
    registry = RuntimeRegistry()

    cpu_rt = LocalCPURuntime("reg-cpu")
    gpu_rt = LocalGPURuntime("reg-gpu")

    registry.register_runtime(cpu_rt)
    registry.register_runtime(gpu_rt)

    assert registry.get_runtime("reg-cpu") is cpu_rt
    assert registry.get_runtime("reg-gpu") is gpu_rt
    assert registry.get_runtime_for_device(DeviceType.CPU) is cpu_rt
    assert registry.get_runtime_for_device(DeviceType.CUDA) is gpu_rt


@pytest.mark.asyncio
async def test_cpu_runtime_model_execution_mock():
    """Verify LocalCPURuntime executes mock TTS request."""
    runtime = LocalCPURuntime("exec-cpu")
    runtime.initialize()

    mock_model = ModelDescriptor(
        model_id="tts/mock-tts",
        name="Mock TTS",
        provider="mock",
        capability="tts",
        supported_devices=["cpu"],
        requires_gpu=False,
    )

    from app.ai.contracts import TTSContractRequest
    import uuid

    req = TTSContractRequest(
        workspace_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        text="Hello HeyZen AI runtime foundation!",
        voice_id="mock-voice",
    )

    res = await runtime.execute("tts", mock_model, req)
    assert res is not None
    assert res.word_count > 0
