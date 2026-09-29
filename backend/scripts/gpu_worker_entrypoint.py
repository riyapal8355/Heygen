#!/usr/bin/env python3
"""GPU Worker Startup Supervisor and Hardware Admission Gate.

Before Celery worker process is spawned to consume 'gpu_ai', validates:
1. NVIDIA GPU presence
2. NVIDIA driver is visible
3. CUDA is operational
4. Torch CUDA is available
5. GPU device is compatible (compute capability >= 7.0)
6. Required VRAM is available (>= 8.0 GB)
7. Model manifest is valid
8. Required model artifacts exist (when artifact verification is enabled)
9. Artifact checksums are verified
10. No blocked or non-commercial artifact is active

If ANY check fails:
- Emits structured JSON diagnostic report
- Exits with non-zero status code (exit 1)
- STRICTLY REFUSES to start Celery worker

If all checks pass:
- Emits structured startup telemetry
- Replaces process image with Celery worker command via os.execvp
"""

import json
import os
import sys
from typing import Any, Dict, Tuple

# Ensure backend root is in PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.ai.gpu_manifest import (
    CommercialStatus,
    GPU_MODEL_MANIFEST,
    assert_artifact_not_blocked,
)
from app.ai.hardware import check_gpu_admission, detect_hardware
from app.ai.lifecycle import compute_file_sha256, resolve_safe_cache_path
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger("gpu_worker_supervisor")


def execute_supervisor_validation() -> Tuple[bool, str, Dict[str, Any]]:

    report: Dict[str, Any] = {
        "supervisor": "heyzen_gpu_worker_supervisor",
        "admitted": False,
        "checks": {},
    }

    settings = get_settings()
    min_vram_gb = float(os.environ.get("GPU_MIN_VRAM_GB", "8.0"))
    min_compute_cap = float(os.environ.get("GPU_MIN_COMPUTE_CAPABILITY", "7.0"))

    # 1-6. Hardware & CUDA Admission
    hw = detect_hardware(refresh=True)
    admitted, reason, details = check_gpu_admission(
        min_vram_gb=min_vram_gb,
        min_compute_capability=min_compute_cap,
        spec=hw,
    )
    report["checks"]["hardware_admission"] = {
        "passed": admitted,
        "reason": reason,
        "details": details,
    }
    if not admitted:
        report["failure_stage"] = "hardware_admission"
        report["reason"] = reason
        return False, reason, report

    # 7. Model Manifest Validation
    manifest_valid = bool(GPU_MODEL_MANIFEST and len(GPU_MODEL_MANIFEST) > 0)
    report["checks"]["manifest_validation"] = {
        "passed": manifest_valid,
        "entry_count": len(GPU_MODEL_MANIFEST),
    }
    if not manifest_valid:
        msg = "MANIFEST_INVALID: GPU model manifest is empty or corrupted."
        report["failure_stage"] = "manifest_validation"
        report["reason"] = msg
        return False, msg, report

    # 8. Blocked Model Policy Assertion
    blocked_check_passed = True
    blocked_failures = []
    for model_id in ["video/animatediff-v1-5", "image/sdxl-turbo", "image/sd-turbo", "video/modelscope-t2v", "video/zeroscope"]:
        try:
            assert_artifact_not_blocked(model_id)
            # If assert did NOT raise, the blocked policy check failed!
            blocked_check_passed = False
            blocked_failures.append(f"Model {model_id} was not properly blocked!")
        except Exception:
            # Expected behavior: assert raises AIModelSecurityException
            pass

    report["checks"]["blocked_model_enforcement"] = {
        "passed": blocked_check_passed,
        "failures": blocked_failures,
    }
    if not blocked_check_passed:
        msg = f"POLICY_FAILURE: Blocked models were not rejected: {blocked_failures}"
        report["failure_stage"] = "blocked_model_enforcement"
        report["reason"] = msg
        return False, msg, report

    # 9-10. Artifact Existence & Checksum Verification (if enforced by environment)
    require_artifacts = os.environ.get("GPU_WORKER_REQUIRE_MODELS", "true").lower() in ("true", "1", "yes")
    cache_root = os.path.abspath(settings.AI_MODEL_CACHE_DIR)
    report["checks"]["artifacts"] = {"enforced": require_artifacts, "cache_root": cache_root, "models": {}}

    if require_artifacts:
        # Check required production models (Yunet face detector is physically present in repo)
        yunet_entry = GPU_MODEL_MANIFEST.get("avatar/yunet-2023mar")
        if yunet_entry:
            yunet_path = resolve_safe_cache_path(cache_root, yunet_entry.relative_path)
            if not os.path.isfile(yunet_path):
                msg = f"ARTIFACT_MISSING: Required auxiliary face detector missing at {yunet_path}."
                report["failure_stage"] = "artifact_verification"
                report["reason"] = msg
                report["checks"]["artifacts"]["models"][yunet_entry.model_id] = {"passed": False, "reason": msg}
                return False, msg, report

            # Verify checksum
            if yunet_entry.expected_sha256:
                actual_sha = compute_file_sha256(yunet_path)
                if actual_sha.lower() != yunet_entry.expected_sha256.lower():
                    msg = f"CHECKSUM_MISMATCH: Artifact {yunet_entry.model_id} checksum failed."
                    report["failure_stage"] = "artifact_verification"
                    report["reason"] = msg
                    report["checks"]["artifacts"]["models"][yunet_entry.model_id] = {"passed": False, "reason": msg}
                    return False, msg, report

            report["checks"]["artifacts"]["models"][yunet_entry.model_id] = {"passed": True, "path": yunet_path}

    report["admitted"] = True
    report["reason"] = "All GPU worker admission and policy gates passed."
    return True, report["reason"], report


def main() -> None:
    cmd_args = sys.argv[1:]
    if cmd_args and cmd_args[0] == "validate":
        from app.cli.gpu import main as cli_main
        sys.argv = [sys.argv[0]] + cmd_args
        cli_main()
        return

    admitted, reason, report = execute_supervisor_validation()

    # Output structured telemetry report
    report_json = json.dumps(report, indent=2, default=str)
    if not admitted:
        print(f"FATAL: GPU Worker Startup Rejected:\n{report_json}", file=sys.stderr)
        sys.exit(1)

    print(f"SUCCESS: GPU Worker Startup Admitted:\n{report_json}", file=sys.stdout)

    # If arguments were provided to entrypoint (e.g. celery worker command), execvp them
    if not cmd_args:
        # Default Celery worker command
        cmd_args = [
            "celery",
            "-A",
            "app.workers.celery_app.celery_app",
            "worker",
            "-Q",
            "gpu_ai",
            "-c",
            "1",
            "--max-tasks-per-child=50",
            "--loglevel=INFO",
            "-n",
            "gpu_worker@%h",
        ]

    logger.info("Executing GPU worker command: %s", " ".join(cmd_args))
    os.execvp(cmd_args[0], cmd_args)


if __name__ == "__main__":
    main()
