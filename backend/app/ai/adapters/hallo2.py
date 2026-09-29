"""Hallo2 Long-Duration Audio-Driven Portrait Image Animation Adapter.

Architectural implementation for Fudan Generative Vision Hallo2:
- High-fidelity audio-driven portrait diffusion model
- Long-duration audio synchronization with temporal cross-attention
- 512x512 to 1024x1024 spatial resolution support
- Native natural blinks, conversational head gestures, and identity preservation

Repository Reference: https://github.com/fudan-generative-vision/hallo2
License: Apache-2.0
"""

import asyncio
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple, Union

from app.ai.capabilities import ProviderDescriptor
from app.ai.hardware import GPUSpec, detect_hardware
from app.ai.interfaces import AvatarProvider, TalkingAvatarProvider
from app.core.exceptions import (
    AIProviderException,
    AIRuntimeUnavailableException,
)
from app.core.logging import get_logger
from app.media.ffmpeg import FFmpegService
from app.media.ffprobe import FFprobeService

logger = get_logger(__name__)

DEFAULT_HALLO2_CACHE_DIR = os.path.join("models_cache", "avatar", "hallo2")
REQUIRED_HALLO2_VRAM_BYTES = 8 * 1024 * 1024 * 1024  # Minimum 8GB dedicated VRAM for Hallo2


class Hallo2Adapter(AvatarProvider, TalkingAvatarProvider):
    """Hallo2 Neural Portrait Video Generation Provider.

    Hardware Contract:
    Requires an operational NVIDIA GPU with CUDA acceleration and at least 8GB dedicated VRAM.
    On non-CUDA or low-VRAM hosts, it raises AIRuntimeUnavailableException reporting:
    'NEURAL AVATAR QUALITY BLOCKED BY LOCAL HARDWARE'.
    """

    provider_name: str = "hallo2"
    descriptor: ProviderDescriptor = ProviderDescriptor(
        name="hallo2",
        capability="avatar",
        version="2.0.0",
        is_local=True,
        requires_gpu=True,
        supported_devices=["cuda"],
        supported_input_formats=["png", "jpg", "jpeg", "mp4"],
        supported_output_formats=["mp4", "webm"],
        is_available=False,
        metadata={
            "engine": "Hallo2-Fudan",
            "runtime": "PyTorch-CUDA",
            "license": "Apache-2.0",
            "commercial_permitted": True,
            "min_vram_gb": 8.0,
            "architecture": "Hierarchical Audio-Visual Cross-Attention Diffusion",
        },
    )

    def __init__(
        self,
        checkpoint_dir: Optional[str] = None,
        device: str = "cuda",
    ) -> None:
        self.device = device.lower()
        self.checkpoint_dir = checkpoint_dir or DEFAULT_HALLO2_CACHE_DIR
        self.ffmpeg_service = FFmpegService()
        self.ffprobe_service = FFprobeService()

    def capabilities(self) -> Dict[str, Any]:
        """Return provider capabilities metadata."""
        return {
            "provider": self.provider_name,
            "architecture": "Fudan/Hallo2",
            "resolution": [512, 768, 1024],
            "long_duration_capable": True,
            "temporal_attention": True,
            "requires_gpu": True,
            "min_vram_gb": 8.0,
        }

    def _verify_cuda_hardware(self) -> None:
        """Strict hardware verification for Hallo2."""
        spec = detect_hardware()
        gpu: GPUSpec = spec.gpu

        if not gpu.cuda_available:
            raise AIRuntimeUnavailableException(
                message=(
                    "NEURAL AVATAR QUALITY BLOCKED BY LOCAL HARDWARE: "
                    "Hallo2 requires an NVIDIA CUDA GPU with at least 8.0GB VRAM. "
                    f"Detected system GPU: '{gpu.vendor} {gpu.model}' with {gpu.vram_total_gb:.2f}GB VRAM "
                    f"(CUDA available: {gpu.cuda_available}). "
                    "Use REMOTE_GPU provider or execute on a CUDA-enabled GPU worker node."
                ),
                details={
                    "error_code": "NEURAL_AVATAR_QUALITY_BLOCKED_BY_LOCAL_HARDWARE",
                    "gpu_vendor": gpu.vendor,
                    "gpu_model": gpu.model,
                    "cuda_available": gpu.cuda_available,
                    "vram_total_gb": gpu.vram_total_gb,
                    "required_vram_gb": 8.0,
                },
            )

        if gpu.vram_total_bytes < REQUIRED_HALLO2_VRAM_BYTES:
            raise AIRuntimeUnavailableException(
                message=(
                    "NEURAL AVATAR QUALITY BLOCKED BY LOCAL HARDWARE: "
                    f"Insufficient VRAM for Hallo2. Required >= 8.0GB, detected {gpu.vram_total_gb:.2f}GB."
                ),
                details={"vram_total_gb": gpu.vram_total_gb, "required_vram_gb": 8.0},
            )

    def health_check(self) -> Tuple[bool, str]:
        """Check hardware readiness and model checkpoints."""
        try:
            self._verify_cuda_hardware()
        except AIRuntimeUnavailableException as exc:
            return False, str(exc.message)

        ckpt_path = Path(self.checkpoint_dir)
        if not ckpt_path.is_absolute():
            backend_root = Path(__file__).resolve().parent.parent.parent.parent
            ckpt_path = backend_root / self.checkpoint_dir

        if not ckpt_path.exists():
            return False, f"Hallo2 checkpoints missing at {ckpt_path}"

        return True, "Hallo2 CUDA provider ready"

    async def synthesize_portrait(
        self,
        source_avatar: Union[str, Path, bytes],
        audio: Union[str, Path, bytes],
        output_path: Union[str, Path],
        fps: int = 25,
        resolution: int = 512,
        progress_callback: Optional[Callable[[int, str], Awaitable[None]]] = None,
    ) -> Dict[str, Any]:
        """Synthesize long-duration audio-driven portrait via Hallo2."""
        self._verify_cuda_hardware()
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)

        if progress_callback:
            await progress_callback(10, "hallo2_audio_conditioning")

        import torch
        logger.info("Executing Hallo2 portrait diffusion on %s", torch.cuda.get_device_name(0))

        with tempfile.TemporaryDirectory(prefix="hallo2_") as tmpdir:
            tmp_path = Path(tmpdir)
            src_file = tmp_path / "source.png"
            aud_file = tmp_path / "audio.wav"

            if isinstance(source_avatar, bytes):
                src_file.write_bytes(source_avatar)
            else:
                shutil.copy2(str(source_avatar), str(src_file))

            if isinstance(audio, bytes):
                aud_file.write_bytes(audio)
            else:
                shutil.copy2(str(audio), str(aud_file))

            cmd = [
                "python",
                "-m",
                "scripts.inference",
                "-s",
                str(src_file),
                "-a",
                str(aud_file),
                "-o",
                str(tmp_path / "results"),
                "--fps",
                str(fps),
                "--resolution",
                str(resolution),
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                raise AIProviderException(
                    code="HALLO2_INFERENCE_FAILED",
                    message=f"Hallo2 diffusion inference failed: {stderr.decode('utf-8', errors='ignore')}",
                )

            res_files = list((tmp_path / "results").glob("*.mp4"))
            if not res_files:
                raise AIProviderException(
                    code="HALLO2_NO_OUTPUT",
                    message="Hallo2 completed but produced no output MP4.",
                )

            shutil.copy2(str(res_files[0]), str(out_p))
            probe = await self.ffprobe_service.validate_render_output(out_p)

            return {
                "output_path": str(out_p),
                "duration": probe.duration_seconds,
                "fps": probe.fps,
                "provider": "hallo2",
                "model_version": "2.0.0",
                "cuda_device": "cuda:0",
            }

    async def generate_talking_video(
        self,
        avatar_image_bytes: bytes,
        audio_bytes: bytes,
        fps: int = 25,
        options: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Callable[[int, str], Awaitable[None]]] = None,
        cancellation_checker: Optional[Callable[[], Awaitable[bool]]] = None,
    ) -> Tuple[bytes, float, int]:
        self._verify_cuda_hardware()
        raise NotImplementedError("Use GPUAvatarProvider for Hallo2 generation.")

    async def synthesize_avatar_video(
        self,
        avatar_image_bytes: bytes,
        audio_bytes: bytes,
        fps: int = 25,
        options: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Callable[[int, str], Awaitable[None]]] = None,
        cancellation_checker: Optional[Callable[[], Awaitable[bool]]] = None,
    ) -> Tuple[bytes, float, int]:
        return await self.generate_talking_video(
            avatar_image_bytes=avatar_image_bytes,
            audio_bytes=audio_bytes,
            fps=fps,
            options=options,
            progress_callback=progress_callback,
            cancellation_checker=cancellation_checker,
        )

    def is_available(self) -> bool:
        """Check whether Hallo2 is ready for local execution."""
        spec = detect_hardware()
        return spec.gpu.cuda_available and spec.gpu.vram_total_bytes >= REQUIRED_HALLO2_VRAM_BYTES


# Direct alias as required by Section 3 Provider Architecture
Hallo2Provider = Hallo2Adapter
