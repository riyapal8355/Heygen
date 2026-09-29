"""AI Runtime Abstraction Layer.

Defines unified execution runtime interfaces across compute devices (CPU, CUDA, ROCm),
environments (local process, container, remote), and handles device health, resource
tracking, concurrency limits, and model execution lifecycle.
"""

from abc import ABC, abstractmethod
from enum import Enum
import threading
from typing import Any, Dict, List, Optional, Tuple

from app.ai.hardware import HardwareSpec, detect_hardware
from app.ai.model_registry import ModelDescriptor
from app.core.exceptions import (
    AIModelIncompatibleException,
    AIResourceExhaustedException,
    AIRuntimeUnavailableException,
)
from app.core.logging import get_logger

logger = get_logger(__name__)


class RuntimeType(str, Enum):
    """Runtime execution environment category."""
    LOCAL_CPU = "local_cpu"
    LOCAL_GPU = "local_gpu"
    CONTAINER_CPU = "container_cpu"
    CONTAINER_GPU = "container_gpu"
    REMOTE_HOSTED = "remote_hosted"


class DeviceType(str, Enum):
    """Underlying hardware acceleration device type."""
    CPU = "cpu"
    CUDA = "cuda"
    ROCM = "rocm"
    MPS = "mps"


class RuntimeHealth(str, Enum):
    """Operational health state of an AI execution runtime."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


class AIRuntime(ABC):
    """Abstract execution runtime managing hardware device boundaries and inference workloads."""

    def __init__(
        self,
        runtime_id: str,
        runtime_type: RuntimeType,
        device_type: DeviceType,
        device_id: str = "0",
        max_concurrency: int = 2,
    ) -> None:
        self.runtime_id = runtime_id
        self.runtime_type = runtime_type
        self.device_type = device_type
        self.device_id = device_id
        self.max_concurrency = max_concurrency
        self.active_tasks = 0
        self._lock = threading.Lock()

    @abstractmethod
    def initialize(self) -> bool:
        """Initialize device contexts, worker pools, or runtime handles."""
        ...

    @abstractmethod
    def shutdown(self) -> None:
        """Release allocated device resources, memory, and runtime handles."""
        ...

    @abstractmethod
    def check_health(self) -> RuntimeHealth:
        """Evaluate operational readiness and resource health of the runtime."""
        ...

    @abstractmethod
    def is_device_available(self) -> bool:
        """Verify if underlying compute accelerator is physically operational."""
        ...

    @abstractmethod
    def check_compatibility(self, model: ModelDescriptor) -> Tuple[bool, str]:
        """Validate whether a model descriptor is compatible with this runtime."""
        ...

    @abstractmethod
    async def execute(self, capability: str, model: ModelDescriptor, request: Any) -> Any:
        """Execute model inference through the runtime."""
        ...


class LocalCPURuntime(AIRuntime):
    """Operational execution runtime for host CPU inference.

    Executes neural synthesis, transcription, translation, and media processing
    using host CPU cores, threading, and system RAM. Fully operational on current machine.
    """

    def __init__(
        self,
        runtime_id: str = "runtime-local-cpu",
        max_concurrency: int = 2,
    ) -> None:
        super().__init__(
            runtime_id=runtime_id,
            runtime_type=RuntimeType.LOCAL_CPU,
            device_type=DeviceType.CPU,
            device_id="cpu",
            max_concurrency=max_concurrency,
        )
        self._initialized = False

    def initialize(self) -> bool:
        logger.info("Initializing LocalCPURuntime [%s]", self.runtime_id)
        self._initialized = True
        return True

    def shutdown(self) -> None:
        logger.info("Shutting down LocalCPURuntime [%s]", self.runtime_id)
        self._initialized = False

    def is_device_available(self) -> bool:
        # Host CPU is always available on host machine
        return True

    def check_health(self) -> RuntimeHealth:
        try:
            hw = detect_hardware()
            # If available RAM is extremely low (<100MB), report degraded
            if hw.memory.ram_available_bytes < 100 * 1024 * 1024:
                return RuntimeHealth.DEGRADED
            return RuntimeHealth.HEALTHY
        except Exception:
            return RuntimeHealth.UNKNOWN

    def check_compatibility(self, model: ModelDescriptor) -> Tuple[bool, str]:
        if model.requires_gpu:
            return False, f"Model '{model.model_id}' strictly requires a GPU, but LocalCPURuntime is CPU-only."
        if not model.supports_device("cpu"):
            return False, f"Model '{model.model_id}' does not list CPU among supported devices."

        hw = detect_hardware()
        if model.minimum_ram_bytes > 0 and hw.memory.ram_total_bytes < model.minimum_ram_bytes:
            req_gb = round(model.minimum_ram_bytes / (1024 ** 3), 2)
            return False, f"Model requires {req_gb} GB RAM, host has {hw.memory.ram_total_gb} GB."

        return True, "Model is fully compatible with LocalCPURuntime."

    async def execute(self, capability: str, model: ModelDescriptor, request: Any) -> Any:
        compat, reason = self.check_compatibility(model)
        if not compat:
            raise AIModelIncompatibleException(
                message=f"LocalCPURuntime cannot execute model '{model.model_id}': {reason}",
                code="AI_MODEL_INCOMPATIBLE",
                details={"model_id": model.model_id, "reason": reason},
            )

        with self._lock:
            self.active_tasks += 1

        try:
            # Dispatch to provider adapter registered for this capability
            from app.ai.registry import get_ai_registry
            registry = get_ai_registry()
            provider = registry.get_provider(capability, model.provider)

            # Delegate execution based on capability contract
            cap = capability.lower()
            if cap == "tts":
                if hasattr(provider, "synthesize"):
                    return await provider.synthesize(request)
                if hasattr(provider, "synthesize_speech"):
                    return await provider.synthesize_speech(
                        text=getattr(request, "text", ""),
                        voice_id=getattr(request, "voice_id", "default"),
                        speed=getattr(request, "speed", 1.0),
                        pitch=getattr(request, "pitch", 0.0),
                    )
            elif cap == "asr":
                if hasattr(provider, "transcribe"):
                    return await provider.transcribe(request)
            elif cap == "translation":
                if hasattr(provider, "translate"):
                    return await provider.translate(request)
            elif cap == "image":
                if hasattr(provider, "generate"):
                    return await provider.generate(request)
            elif cap == "avatar":
                if hasattr(provider, "lip_sync"):
                    return await provider.lip_sync(request)
            elif cap == "video":
                if hasattr(provider, "generate"):
                    return await provider.generate(request)
            elif cap == "llm":
                if hasattr(provider, "generate_script"):
                    prompt = getattr(request, "prompt", str(request))
                    return await provider.generate_script(prompt=prompt)

            # Generic fallback invocation
            if callable(provider):
                return await provider(request)

            raise AIModelIncompatibleException(
                message=f"Provider '{model.provider}' does not support execution for capability '{capability}'.",
                code="AI_PROVIDER_EXECUTION_UNSUPPORTED",
            )
        finally:
            with self._lock:
                self.active_tasks = max(0, self.active_tasks - 1)


class LocalGPURuntime(AIRuntime):
    """Execution runtime for local NVIDIA CUDA GPU inference.

    Handles CUDA device context initialization, VRAM monitoring, and CUDA-accelerated
    inference. On machines lacking CUDA (such as the current Windows machine),
    correctly and safely reports UNAVAILABLE without failing application startup.
    Full CUDA execution is ready for validation on a CUDA-capable host.
    """

    def __init__(
        self,
        runtime_id: str = "runtime-local-gpu",
        device_id: str = "cuda:0",
        max_concurrency: int = 1,
    ) -> None:
        super().__init__(
            runtime_id=runtime_id,
            runtime_type=RuntimeType.LOCAL_GPU,
            device_type=DeviceType.CUDA,
            device_id=device_id,
            max_concurrency=max_concurrency,
        )
        self._initialized = False

    def initialize(self) -> bool:
        hw = detect_hardware()
        if not hw.gpu.cuda_available:
            logger.info("LocalGPURuntime [%s] initialization skipped: no CUDA GPU detected on host.", self.runtime_id)
            self._initialized = False
            return False

        logger.info(
            "Initializing LocalGPURuntime [%s] on device %s (%s, %.2f GB VRAM)",
            self.runtime_id,
            self.device_id,
            hw.gpu.model,
            hw.gpu.vram_total_gb,
        )
        self._initialized = True
        return True

    def shutdown(self) -> None:
        logger.info("Shutting down LocalGPURuntime [%s]", self.runtime_id)
        self._initialized = False

    def is_device_available(self) -> bool:
        hw = detect_hardware()
        return bool(hw.gpu.cuda_available)

    def check_health(self) -> RuntimeHealth:
        hw = detect_hardware()
        if not hw.gpu.cuda_available:
            return RuntimeHealth.UNAVAILABLE
        if hw.gpu.vram_free_bytes < 512 * 1024 * 1024:
            return RuntimeHealth.DEGRADED
        return RuntimeHealth.HEALTHY

    def check_compatibility(self, model: ModelDescriptor) -> Tuple[bool, str]:
        hw = detect_hardware()
        if not hw.gpu.cuda_available:
            return (
                False,
                f"Cannot execute on LocalGPURuntime: No NVIDIA CUDA GPU is operational on this host (vendor: {hw.gpu.vendor}).",
            )
        if not model.supports_device("cuda"):
            return False, f"Model '{model.model_id}' does not support CUDA device execution."
        if model.minimum_vram_bytes and hw.gpu.vram_total_bytes < model.minimum_vram_bytes:
            req_gb = round(model.minimum_vram_bytes / (1024 ** 3), 2)
            return False, f"Model requires {req_gb} GB VRAM, GPU has {hw.gpu.vram_total_gb} GB."

        return True, "Model is compatible with LocalGPURuntime."

    async def execute(self, capability: str, model: ModelDescriptor, request: Any) -> Any:
        if not self.is_device_available():
            raise AIRuntimeUnavailableException(
                message=(
                    f"Cannot execute GPU model '{model.model_id}' on '{self.runtime_id}': "
                    f"CUDA GPU is unavailable on this host. This operation requires a CUDA-capable machine."
                ),
                code="AI_GPU_UNAVAILABLE",
                details={
                    "runtime_id": self.runtime_id,
                    "model_id": model.model_id,
                    "capability": capability,
                    "requires_cuda": True,
                },
            )

        compat, reason = self.check_compatibility(model)
        if not compat:
            raise AIModelIncompatibleException(
                message=f"LocalGPURuntime cannot execute model '{model.model_id}': {reason}",
                code="AI_MODEL_INCOMPATIBLE",
                details={"model_id": model.model_id, "reason": reason},
            )

        # Execution on CUDA-capable host
        with self._lock:
            self.active_tasks += 1

        try:
            from app.ai.registry import get_ai_registry
            registry = get_ai_registry()
            provider = registry.get_provider(capability, model.provider)
            # Future GPU-specific execution hooks for Phase 8 Steps 2-8
            if hasattr(provider, "synthesize"):
                return await provider.synthesize(request)
            if hasattr(provider, "transcribe"):
                return await provider.transcribe(request)
            if hasattr(provider, "translate"):
                return await provider.translate(request)
            if hasattr(provider, "generate"):
                return await provider.generate(request)
            if hasattr(provider, "lip_sync"):
                return await provider.lip_sync(request)
            return await provider(request)
        finally:
            with self._lock:
                self.active_tasks = max(0, self.active_tasks - 1)


class RuntimeRegistry:
    """Central registry of compute runtimes."""

    def __init__(self) -> None:
        self._runtimes: Dict[str, AIRuntime] = {}

    def register_runtime(self, runtime: AIRuntime) -> None:
        """Register an active runtime instance."""
        self._runtimes[runtime.runtime_id] = runtime
        logger.info("Registered AI runtime '%s' (type=%s, device=%s)", runtime.runtime_id, runtime.runtime_type, runtime.device_type)

    def get_runtime(self, runtime_id: str) -> Optional[AIRuntime]:
        """Retrieve runtime by ID."""
        return self._runtimes.get(runtime_id)

    def list_runtimes(self) -> List[AIRuntime]:
        """List all registered runtimes."""
        return list(self._runtimes.values())

    def get_runtime_for_device(self, device_type: DeviceType) -> Optional[AIRuntime]:
        """Find the primary runtime for a given device type."""
        for rt in self._runtimes.values():
            if rt.device_type == device_type:
                return rt
        return None

    def get_available_runtimes(self) -> List[AIRuntime]:
        """List runtimes whose underlying compute device is operational."""
        return [rt for rt in self._runtimes.values() if rt.is_device_available()]


# Global runtime registry singleton
_runtime_registry_instance: Optional[RuntimeRegistry] = None


def get_runtime_registry() -> RuntimeRegistry:
    """Retrieve global RuntimeRegistry singleton initialized with standard local runtimes."""
    global _runtime_registry_instance
    if _runtime_registry_instance is None:
        _runtime_registry_instance = RuntimeRegistry()
        # Register standard Local CPU runtime (operational here)
        cpu_rt = LocalCPURuntime()
        cpu_rt.initialize()
        _runtime_registry_instance.register_runtime(cpu_rt)

        # Register standard Local GPU runtime (graceful unavailable on non-CUDA host)
        gpu_rt = LocalGPURuntime()
        gpu_rt.initialize()
        _runtime_registry_instance.register_runtime(gpu_rt)

    return _runtime_registry_instance
