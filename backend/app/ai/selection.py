"""Deterministic Model and Runtime Selection Engine.

Implements the execution chain:
    Capability -> Provider -> Model -> Runtime -> Device -> Inference

Ensures:
1. Strict adherence to AI_RUNTIME_MODE (explicit mock vs real).
2. Deterministic candidate ranking based on hardware compatibility and device preferences.
3. No silent fallback: if real execution is configured and no compatible model/runtime
   exists on host, structured domain exceptions are raised.
"""

from typing import Optional, Tuple

from app.ai.hardware import HardwareSpec, detect_hardware
from app.ai.model_registry import ModelDescriptor, get_model_registry
from app.ai.runtimes import AIRuntime, DeviceType, get_runtime_registry
from app.core.config import get_settings
from app.core.exceptions import (
    AIModelIncompatibleException,
    AIRuntimeUnavailableException,
    NotFoundException,
)
from app.core.logging import get_logger

logger = get_logger(__name__)


def select_model_and_runtime(
    capability: str,
    preferred_device: Optional[str] = None,
    language: Optional[str] = None,
    format_name: Optional[str] = None,
    model_id: Optional[str] = None,
    hardware: Optional[HardwareSpec] = None,
    mode: Optional[str] = None,
) -> Tuple[ModelDescriptor, AIRuntime]:
    """Deterministically select the most appropriate ModelDescriptor and AIRuntime.

    Args:
        capability: Required AI capability (e.g. 'tts', 'asr', 'translation', 'avatar', 'image')
        preferred_device: Requested compute target ('auto', 'cpu', 'cuda')
        language: Target ISO language code if applicable
        format_name: Container format if applicable
        model_id: Specific model ID override if explicitly requested
        hardware: Host hardware specification (detected automatically if omitted)
        mode: Execution mode override ('mock' or 'real'); defaults to settings.AI_RUNTIME_MODE

    Returns:
        Tuple of (selected_model_descriptor, selected_ai_runtime)

    Raises:
        AIRuntimeUnavailableException: If requested device (e.g. CUDA GPU) is unavailable.
        AIModelIncompatibleException: If no compatible model exists for host hardware.
        NotFoundException: If explicitly requested model_id does not exist.
    """
    settings = get_settings()
    hw = hardware or detect_hardware()
    model_reg = get_model_registry()
    runtime_reg = get_runtime_registry()

    cap = capability.strip().lower()
    dev_pref = (preferred_device or settings.AI_PREFERRED_DEVICE or "auto").strip().lower()
    active_mode = (mode or settings.AI_RUNTIME_MODE or settings.AI_PROVIDER_MODE or "mock").strip().lower()

    # -------------------------------------------------------------------------
    # 1. Device Preference Pre-check
    # -------------------------------------------------------------------------
    if dev_pref == "cuda" and not hw.gpu.cuda_available:
        raise AIRuntimeUnavailableException(
            message=(
                f"CUDA device execution was explicitly requested for capability '{cap}', "
                f"but host has no operational NVIDIA CUDA GPU (vendor: {hw.gpu.vendor})."
            ),
            code="AI_GPU_UNAVAILABLE",
            details={"capability": cap, "preferred_device": dev_pref, "has_cuda": False},
        )

    # -------------------------------------------------------------------------
    # 2. Specific Model ID Selection (Validated strictly against catalog and host)
    # -------------------------------------------------------------------------
    if model_id:
        target_model = model_reg.get_model(model_id)
        if not target_model:
            raise NotFoundException(
                message=f"Requested model '{model_id}' is not registered in catalog.",
                code="AI_MODEL_NOT_FOUND",
                details={"model_id": model_id, "capability": cap},
            )
        is_compat, state, reason = target_model.is_compatible_with(hw)
        if not is_compat:
            raise AIModelIncompatibleException(
                message=f"Requested model '{model_id}' is incompatible with host hardware: {reason}",
                code="AI_MODEL_INCOMPATIBLE",
                details={"model_id": model_id, "hardware_state": state.value, "reason": reason},
            )
        selected_model = target_model

    # -------------------------------------------------------------------------
    # 3. Explicit Mock Mode (When no specific model_id is requested)
    # -------------------------------------------------------------------------
    elif active_mode == "mock":
        mock_id = f"{cap}/mock-{cap}"
        mock_model = model_reg.get_model(mock_id)
        if not mock_model:
            mock_candidates = [m for m in model_reg.list_models(capability=cap) if m.provider == "mock"]
            mock_model = mock_candidates[0] if mock_candidates else None

        if mock_model:
            cpu_runtime = runtime_reg.get_runtime_for_device(DeviceType.CPU)
            if not cpu_runtime:
                raise AIRuntimeUnavailableException(
                    message="Local CPU runtime is not registered.",
                    code="AI_CPU_UNAVAILABLE",
                )
            return mock_model, cpu_runtime

        selected_model = mock_model
    else:
        # -------------------------------------------------------------------------
        # 4. Deterministic Candidate Query & Compatibility Matching (Real Mode)
        # -------------------------------------------------------------------------
        candidates = model_reg.find_compatible_models(
            capability=cap,
            hardware=hw,
            language=language,
            format_name=format_name,
            device_preference=dev_pref,
        )

        # In real mode, exclude pure mock models from automatic selection if real models exist
        if active_mode == "real":
            real_candidates = [m for m in candidates if m.provider != "mock"]
            if real_candidates:
                candidates = real_candidates

        if not candidates:
            # Diagnose reason for detailed, actionable error payload
            all_for_cap = model_reg.find_models(capability=cap, language=language, format_name=format_name)
            if not all_for_cap:
                raise AIModelIncompatibleException(
                    message=f"No models registered supporting capability '{cap}' with requested constraints (language={language}, format={format_name}).",
                    code="AI_MODEL_NOT_FOUND",
                    details={"capability": cap, "language": language, "format": format_name},
                )

            gpu_required_models = [m for m in all_for_cap if m.requires_gpu]
            if gpu_required_models and not hw.gpu.cuda_available:
                raise AIRuntimeUnavailableException(
                    message=(
                        f"All available real models for capability '{cap}' require NVIDIA CUDA acceleration. "
                        f"Host machine does not possess an operational CUDA GPU (vendor: {hw.gpu.vendor}). "
                        f"This operation must be scheduled on a CUDA-capable worker machine."
                    ),
                    code="AI_GPU_UNAVAILABLE",
                    details={
                        "capability": cap,
                        "required_gpu_models": [m.model_id for m in gpu_required_models],
                        "cuda_available": False,
                    },
                )

            raise AIModelIncompatibleException(
                message=f"No model for capability '{cap}' satisfies host memory or hardware constraints.",
                code="AI_MODEL_INCOMPATIBLE",
                details={"capability": cap, "host_ram_gb": hw.memory.ram_total_gb},
            )

        selected_model = candidates[0]


    # -------------------------------------------------------------------------
    # 5. Resolve Matching Operational Runtime
    # -------------------------------------------------------------------------
    if selected_model.requires_gpu or (dev_pref == "cuda" and selected_model.supports_device("cuda")):
        target_runtime = runtime_reg.get_runtime_for_device(DeviceType.CUDA)
        if not target_runtime or not target_runtime.is_device_available():
            raise AIRuntimeUnavailableException(
                message=f"CUDA runtime is not operational for model '{selected_model.model_id}'.",
                code="AI_GPU_UNAVAILABLE",
                details={"model_id": selected_model.model_id},
            )
    else:
        target_runtime = runtime_reg.get_runtime_for_device(DeviceType.CPU)
        if not target_runtime or not target_runtime.is_device_available():
            raise AIRuntimeUnavailableException(
                message=f"Local CPU runtime is not operational for model '{selected_model.model_id}'.",
                code="AI_CPU_UNAVAILABLE",
                details={"model_id": selected_model.model_id},
            )

    logger.info(
        "Selected model '%s' (provider=%s) on runtime '%s' for capability '%s'",
        selected_model.model_id,
        selected_model.provider,
        target_runtime.runtime_id,
        cap,
    )
    return selected_model, target_runtime
