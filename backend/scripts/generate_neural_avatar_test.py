"""Standalone Neural Avatar Test Script conforming to Section 15.

Supports:
    --provider liveportrait
    --provider musetalk
    --provider hallo2
    --provider gpu_avatar
    --provider wav2lip

Behavior:
    On CPU machines lacking NVIDIA CUDA GPU:
    - liveportrait -> reports GPU_REQUIRED with detailed error
    - musetalk     -> reports GPU_REQUIRED with detailed error
    - hallo2       -> reports GPU_REQUIRED with detailed error
    - gpu_avatar   -> routes to clean development fallback (or fails fast if allow_fallback=False)
    - wav2lip      -> executes clean development fallback (no Delaunay warping)

    When GPU is later available:
    - Executes actual neural inference seamlessly with no code changes.
"""

import argparse
import asyncio
import os
import sys
import time
from pathlib import Path
from typing import Optional

BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.ai.adapters.hallo2 import Hallo2Adapter
from app.ai.adapters.liveportrait import LivePortraitAdapter, LivePortraitMotionOptions
from app.ai.adapters.musetalk import MuseTalkAvatarProvider
from app.ai.adapters.wav2lip import Wav2LipONNXAvatarProvider
from app.ai.hardware import detect_hardware
from app.ai.model_registry import discover_model_state
from app.ai.providers.gpu_avatar_provider import GPUAvatarProvider, GPUAvatarProviderMode
from app.core.exceptions import AIRuntimeUnavailableException
from app.media.ffprobe import FFprobeService


async def run_test(
    provider_name: str,
    avatar_name: str = "annie",
    output_dir: Optional[Path] = None,
    allow_fallback: bool = True,
) -> None:
    hw = detect_hardware()
    out_dir = output_dir or (BACKEND_ROOT.parent / "test-results" / "avatar_quality")
    out_dir.mkdir(parents=True, exist_ok=True)

    source_path = BACKEND_ROOT / "avatars" / avatar_name / "source.png"
    if not source_path.exists():
        source_path = BACKEND_ROOT.parent / "avatars" / avatar_name / "source.png"

    driving_path = BACKEND_ROOT / "avatars" / avatar_name / "driving" / "talking.mp4"
    if not driving_path.exists():
        driving_path = BACKEND_ROOT.parent / "avatars" / avatar_name / "driving" / "talking.mp4"

    # Reference audio
    audio_path = BACKEND_ROOT / "seed_assets" / "audio" / "intro_speech.wav"
    if not audio_path.exists() or audio_path.stat().st_size == 0:
        scratch_dir = BACKEND_ROOT / "scratch"
        scratch_dir.mkdir(parents=True, exist_ok=True)
        audio_path = scratch_dir / "test_speech.wav"
        if not audio_path.exists() or audio_path.stat().st_size == 0:
            from app.ai.adapters.piper import PiperTTSProvider
            tts = PiperTTSProvider()
            res = await tts.synthesize_speech("Hello, this is a test of the neural avatar development fallback.", "en_US-lessac-medium")
            wav_bytes = res.audio_bytes if hasattr(res, "audio_bytes") else (res[0] if isinstance(res, tuple) else res)
            audio_path.write_bytes(wav_bytes)

    prov = provider_name.strip().lower()

    print(f"\n[NEURAL AVATAR TEST] Provider: '{prov}' | Host CUDA: {hw.gpu.cuda_available}")

    # 1. LIVEPORTRAIT
    if prov == "liveportrait":
        lp = LivePortraitAdapter()
        if not hw.gpu.cuda_available:
            print("STATUS: GPU_REQUIRED")
            print("REASON: KwaiVGI LivePortrait requires an NVIDIA CUDA GPU with >=4.0GB VRAM.")
            print(f"HOST:   {hw.gpu.vendor} {hw.gpu.model} (0 dedicated CUDA VRAM)")
            return
        # GPU Execution
        out_mp4 = out_dir / f"{avatar_name}_liveportrait.mp4"
        res = await lp.generate_motion(
            source_avatar=source_path,
            driving_motion=driving_path,
            output_path=out_mp4,
            options=LivePortraitMotionOptions(fps=25),
        )
        print(f"STATUS: SUCCESS (LivePortrait CUDA)\nOUTPUT: {out_mp4}")

    # 2. MUSETALK
    elif prov == "musetalk":
        mt = MuseTalkAvatarProvider()
        if not hw.gpu.cuda_available:
            print("STATUS: GPU_REQUIRED")
            print("REASON: MuseTalk 1.5 requires an NVIDIA CUDA GPU with >=4.0GB VRAM.")
            print(f"HOST:   {hw.gpu.vendor} {hw.gpu.model} (0 dedicated CUDA VRAM)")
            return
        out_mp4 = out_dir / f"{avatar_name}_musetalk.mp4"
        res = await mt.synthesize_lipsync_from_motion_video(
            motion_video=driving_path,
            audio=audio_path,
            output_path=out_mp4,
            fps=25,
        )
        print(f"STATUS: SUCCESS (MuseTalk 1.5 CUDA)\nOUTPUT: {out_mp4}")

    # 3. HALLO2
    elif prov == "hallo2":
        hallo = Hallo2Adapter()
        if not hw.gpu.cuda_available:
            print("STATUS: GPU_REQUIRED")
            print("REASON: Fudan Hallo2 requires an NVIDIA CUDA GPU with >=8.0GB VRAM.")
            print(f"HOST:   {hw.gpu.vendor} {hw.gpu.model} (0 dedicated CUDA VRAM)")
            return
        out_mp4 = out_dir / f"{avatar_name}_hallo2.mp4"
        res = await hallo.synthesize_portrait(
            source_avatar=source_path,
            audio=audio_path,
            output_path=out_mp4,
            fps=25,
        )
        print(f"STATUS: SUCCESS (Hallo2 CUDA)\nOUTPUT: {out_mp4}")

    # 4. GPU_AVATAR
    elif prov == "gpu_avatar":
        gpu_p = GPUAvatarProvider(allow_fallback=allow_fallback)
        if not hw.gpu.cuda_available and not allow_fallback:
            print("STATUS: GPU_REQUIRED")
            print("REASON: GPUAvatarProvider running with allow_fallback=False on CPU machine.")
            return

        out_mp4 = out_dir / f"{avatar_name}_gpu_avatar.mp4"
        if not hw.gpu.cuda_available:
            print("STATUS: FALLBACK_EXECUTED (CPU Development Fallback — not neural motion)")
        else:
            print("STATUS: SUCCESS (Neural Avatar Pipeline)")

        # Render video
        vid_bytes, dur, frames = await gpu_p.generate_talking_video(
            avatar_image_bytes=source_path.read_bytes(),
            audio_bytes=audio_path.read_bytes() if audio_path.exists() else b"",
            fps=25,
            options={"avatar_name": avatar_name},
        )
        out_mp4.write_bytes(vid_bytes)
        print(f"OUTPUT: {out_mp4} ({dur:.2f}s, {frames} frames)")

    # 5. WAV2LIP
    elif prov in ("wav2lip", "local_wav2lip_fallback"):
        w2l = Wav2LipONNXAvatarProvider()
        out_mp4 = out_dir / f"{avatar_name}_wav2lip_fallback.mp4"
        print("STATUS: EXECUTING_DEVELOPMENT_FALLBACK (Clean Wav2Lip ONNX CPU — no Delaunay)")
        vid_bytes, dur, frames = await w2l.generate_talking_video(
            avatar_image_bytes=source_path.read_bytes(),
            audio_bytes=audio_path.read_bytes() if audio_path.exists() else b"",
            fps=25,
            options={"enable_legacy_delaunay": False},
        )
        out_mp4.write_bytes(vid_bytes)
        print(f"OUTPUT: {out_mp4} ({dur:.2f}s, {frames} frames)")

    else:
        print(f"Unknown provider '{provider_name}'. Choose from: liveportrait, musetalk, hallo2, gpu_avatar, wav2lip")


def main() -> None:
    parser = argparse.ArgumentParser(description="Standalone Neural Avatar Test Tool")
    parser.add_argument(
        "--provider",
        choices=["liveportrait", "musetalk", "hallo2", "gpu_avatar", "wav2lip"],
        default="gpu_avatar",
        help="Provider to execute or test",
    )
    parser.add_argument("--avatar", default="annie", help="Avatar name (annie, daniel)")
    parser.add_argument("--strict-gpu", action="store_true", help="Disallow CPU development fallback")

    args = parser.parse_args()
    asyncio.run(
        run_test(
            provider_name=args.provider,
            avatar_name=args.avatar,
            allow_fallback=not args.strict_gpu,
        )
    )


if __name__ == "__main__":
    main()
