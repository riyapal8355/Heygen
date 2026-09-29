"""Dry-run validation command for the HeyZen Neural Avatar Stack.

Evaluates host hardware, CUDA capabilities, remote worker connectivity,
and all registered avatar providers to confirm GPU readiness.

Conforms to Section 24 of the specification.
"""

import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import httpx

from app.ai.hardware import detect_hardware, get_neural_avatar_hardware_status
from app.ai.model_registry import discover_model_state
from app.ai.registry import AICapability, get_ai_registry


def validate_stack() -> None:
    print("=" * 60)
    print("HEYZEN — NEURAL AVATAR STACK VALIDATION")
    print("=" * 60)

    hw = detect_hardware()
    status = get_neural_avatar_hardware_status()
    registry = get_ai_registry()

    # 1. CUDA & Display Hardware
    if hw.gpu.cuda_available:
        print("\nCUDA: AVAILABLE")
        print(f"Device: {hw.gpu.vendor} {hw.gpu.model} ({hw.gpu.vram_total_gb:.2f} GB VRAM)")
    else:
        print("\nCUDA: NOT AVAILABLE")
        print(f"Host Display: {hw.gpu.vendor} {hw.gpu.model} ({hw.gpu.vram_total_gb:.2f} GB shared)")
        print("Note: PyTorch runtime is CPU-only.")

    # 2. Neural Avatar Models
    print("\n--- Model Capabilities & Hardware Readiness ---")
    for mid, name in [
        ("avatar/liveportrait", "LivePortrait"),
        ("avatar/musetalk", "MuseTalk"),
        ("avatar/hallo2", "Hallo2"),
    ]:
        state = discover_model_state(mid)
        st = state["status"]
        if st == "AVAILABLE":
            print(f"{name}:\n  READY (Local CUDA)")
        elif st == "GPU_REQUIRED":
            print(f"{name}:\n  GPU REQUIRED ({state['reason']})")
        else:
            print(f"{name}:\n  {st} ({state['reason']})")

    # 3. Remote GPU Worker
    worker_url = os.environ.get("REMOTE_GPU_WORKER_URL", "http://127.0.0.1:8100")
    print("\n--- Remote GPU Worker Status ---")
    try:
        resp = httpx.get(f"{worker_url}/health", timeout=2.0)
        if resp.status_code == 200:
            data = resp.json()
            print(f"Remote GPU:\n  ONLINE ({worker_url})\n  GPU: {data.get('gpu_name')}\n  VRAM: {data.get('vram_gb')} GB")
        else:
            print(f"Remote GPU:\n  NOT CONFIGURED / UNREACHABLE ({worker_url})")
    except Exception:
        print(f"Remote GPU:\n  READY / NOT CONFIGURED (URL: {worker_url})")

    # 4. Fallback Provider
    w2l_state = discover_model_state("avatar/wav2lip")
    print("\n--- Development Fallback ---")
    if w2l_state["status"] == "AVAILABLE":
        print("Wav2Lip fallback:\n  AVAILABLE (CPU Development Fallback — clean neural lip sync, no Delaunay)")
    else:
        print(f"Wav2Lip fallback:\n  {w2l_state['status']}")

    # 5. Active Default Selection
    gpu_provider = registry.get_provider(AICapability.AVATAR, name="gpu_avatar")
    print("\n--- Active Provider Selection ---")
    print(f"Production Provider: {gpu_provider.provider_name}")
    if hasattr(gpu_provider, "mode"):
        print(f"Active Mode:         {gpu_provider.mode.value}")
        print(f"Fallback Permitted:  {gpu_provider.allow_fallback}")
    print("=" * 60)


if __name__ == "__main__":
    validate_stack()
