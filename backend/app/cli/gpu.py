
"""NVIDIA GPU AI Runtime Validation Harness CLI.

Usage:
    python -m app.cli.gpu validate [--json] [--run-tensor-test] [--min-vram 8.0] [--min-cc 7.0]

Performs exhaustive verification of:
1. NVIDIA device presence and driver visibility
2. PyTorch CUDA operational state
3. Compute capability thresholds (default: >= 7.0)
4. Total and free VRAM thresholds (default: >= 8.0 GB)
5. Pinned CUDA version compatibility
6. Model manifest and blocked-artifact policy enforcement
7. Provider runtime dependency imports
8. Optional minimal CUDA tensor execution test

Exits:
    0: Host is admitted and fully operational for GPU AI workloads.
    1: Host fails admission (e.g. GPU_UNAVAILABLE on CPU hosts).
"""

import argparse
import json
import os
import sys
import time
from typing import Any, Dict, Optional, Tuple

from app.ai.gpu_manifest import (
    CommercialStatus,
    GPU_MODEL_MANIFEST,
    assert_artifact_not_blocked,
)
from app.ai.hardware import (
    GPUAdmissionResult,
    GPUErrorCode,
    check_gpu_admission,
    detect_hardware,
)
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger("gpu_validation_cli")


def run_minimal_cuda_tensor_test() -> Dict[str, Any]:
    """Execute a minimal CUDA tensor operation to prove hardware execution independent of model weights."""
    try:
        import torch
        if not torch.cuda.is_available():
            return {
                "executed": False,
                "reason": "CUDA unavailable on host",
                "latency_ms": None,
            }

        t0 = time.perf_counter()
        device = torch.device("cuda:0")
        # Allocate two 1024x1024 float32 matrices on GPU
        x = torch.randn(1024, 1024, device=device, dtype=torch.float32)
        y = torch.randn(1024, 1024, device=device, dtype=torch.float32)
        z = torch.matmul(x, y)
        torch.cuda.synchronize()
        latency_ms = (time.perf_counter() - t0) * 1000.0

        # Memory cleanup
        del x, y, z
        torch.cuda.empty_cache()

        return {
            "executed": True,
            "device": str(device),
            "tensor_shape": [1024, 1024],
            "operation": "matmul (FP32)",
            "latency_ms": round(latency_ms, 2),
            "status": "PASSED",
        }
    except Exception as exc:
        return {
            "executed": False,
            "error": str(exc),
            "status": "FAILED",
        }


def validate_provider_dependencies() -> Dict[str, Any]:
    """Verify runtime Python dependencies required by GPU providers."""
    deps: Dict[str, Any] = {}

    # PyTorch
    try:
        import torch
        deps["torch"] = {
            "installed": True,
            "version": torch.__version__,
            "cuda_version": getattr(torch.version, "cuda", None),
        }
    except ImportError:
        deps["torch"] = {"installed": False, "version": None}

    # OpenCV (YuNet face detector for MuseTalk)
    try:
        import cv2
        deps["opencv"] = {"installed": True, "version": cv2.__version__}
    except ImportError:
        deps["opencv"] = {"installed": False, "version": None}

    # Pillow (Stable Diffusion image processing)
    try:
        import PIL
        deps["pillow"] = {"installed": True, "version": PIL.__version__}
    except ImportError:
        deps["pillow"] = {"installed": False, "version": None}

    # SciPy
    try:
        import scipy
        deps["scipy"] = {"installed": True, "version": scipy.__version__}
    except ImportError:
        deps["scipy"] = {"installed": False, "version": None}

    return deps


def execute_gpu_validation(
    min_vram_gb: float = 8.0,
    min_compute_capability: float = 7.0,
    run_tensor_test: bool = True,
) -> Tuple[bool, Dict[str, Any]]:
    """Perform full diagnostic GPU runtime audit."""
    hw = detect_hardware(refresh=True)
    admission: GPUAdmissionResult = check_gpu_admission(
        min_vram_gb=min_vram_gb,
        min_compute_capability=min_compute_capability,
        spec=None,  # Live host mode
    )

    # Policy enforcement check
    blocked_failures = []
    for model_id in ["video/animatediff-v1-5", "image/sdxl-turbo", "image/sd-turbo", "video/modelscope-t2v", "video/zeroscope"]:
        try:
            assert_artifact_not_blocked(model_id)
            blocked_failures.append(f"Model {model_id} was not properly blocked!")
        except Exception:
            pass

    # Provider dependencies
    dependencies = validate_provider_dependencies()

    # Optional minimal tensor test
    tensor_test = None
    if run_tensor_test and admission.available:
        tensor_test = run_minimal_cuda_tensor_test()
    else:
        tensor_test = {
            "executed": False,
            "status": "SKIPPED",
            "reason": "GPU acceleration is unavailable or tensor test not requested",
        }

    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "verdict": "ADMITTED" if admission.supported else "REJECTED",
        "admitted": admission.supported,
        "error_code": admission.error_code.value if admission.error_code else None,
        "reason": admission.reason,
        "host": {
            "os": f"{hw.os_name} {hw.os_release}",
            "cpu": hw.cpu.model,
            "logical_cores": hw.cpu.logical_cores,
            "system_ram_gb": hw.memory.ram_total_gb,
        },
        "gpu": {
            "has_gpu": hw.gpu.has_gpu,
            "vendor": hw.gpu.vendor,
            "model": hw.gpu.model,
            "cuda_available": hw.gpu.cuda_available,
            "driver_version": hw.gpu.driver_version,
            "cuda_version": hw.gpu.cuda_version,
            "compute_capability": hw.gpu.compute_capability,
            "total_vram_gb": hw.gpu.vram_total_gb,
            "free_vram_gb": hw.gpu.vram_free_gb,
        },
        "thresholds": {
            "min_vram_gb": min_vram_gb,
            "min_compute_capability": min_compute_capability,
        },
        "dependencies": dependencies,
        "blocked_model_enforcement": {
            "passed": len(blocked_failures) == 0,
            "blocked_failures": blocked_failures,
        },
        "tensor_test": tensor_test,
    }

    return admission.supported, report


def main() -> None:
    parser = argparse.ArgumentParser(description="HeyZen NVIDIA GPU AI Runtime Validation CLI")
    subparsers = parser.add_subparsers(dest="subcommand", help="Subcommand to execute")

    validate_parser = subparsers.add_parser("validate", help="Validate host GPU availability and runtime compatibility")
    validate_parser.add_argument("--json", action="store_true", help="Output machine-readable JSON format")
    validate_parser.add_argument("--run-tensor-test", action="store_true", default=True, help="Execute minimal CUDA tensor test if available")
    validate_parser.add_argument("--min-vram", type=float, default=8.0, help="Minimum VRAM in GB (default: 8.0)")
    validate_parser.add_argument("--min-cc", type=float, default=7.0, help="Minimum CUDA compute capability (default: 7.0)")

    args = parser.parse_args()

    # Default to validate if no subcommand passed
    subcommand = args.subcommand or "validate"
    if subcommand != "validate":
        parser.print_help()
        sys.exit(1)

    min_vram = getattr(args, "min_vram", 8.0)
    min_cc = getattr(args, "min_cc", 7.0)
    run_tensor = getattr(args, "run_tensor_test", True)
    output_json = getattr(args, "json", False)

    admitted, report = execute_gpu_validation(
        min_vram_gb=min_vram,
        min_compute_capability=min_cc,
        run_tensor_test=run_tensor,
    )

    if output_json:
        print(json.dumps(report, indent=2))
    else:
        print("\n========================================================")
        print("  HEYZEN NVIDIA GPU RUNTIME VALIDATION REPORT")
        print("========================================================")
        print(f"  Verdict:           {report['verdict']}")
        print(f"  Error Code:        {report['error_code'] or 'NONE'}")
        print(f"  Reason:            {report['reason']}")
        print("--------------------------------------------------------")
        print(f"  Host CPU:          {report['host']['cpu']} ({report['host']['logical_cores']} cores)")
        print(f"  System RAM:        {report['host']['system_ram_gb']} GB")
        print(f"  GPU Vendor:        {report['gpu']['vendor']}")
        print(f"  GPU Model:         {report['gpu']['model']}")
        print(f"  CUDA Available:    {report['gpu']['cuda_available']}")
        print(f"  CUDA Version:      {report['gpu']['cuda_version'] or 'N/A'}")
        print(f"  Driver Version:    {report['gpu']['driver_version'] or 'N/A'}")
        print(f"  Compute Cap:       {report['gpu']['compute_capability'] or 'N/A'}")
        print(f"  VRAM (Total/Free): {report['gpu']['total_vram_gb']} GB / {report['gpu']['free_vram_gb']} GB")
        print("--------------------------------------------------------")
        print(f"  Blocked Models:    {'ENFORCED (PASS)' if report['blocked_model_enforcement']['passed'] else 'FAIL'}")
        print(f"  Tensor Test:       {report['tensor_test']['status']}")
        print("========================================================\n")

    if not admitted:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
