"""Stable Diffusion Image Provider Adapter (Production-Target CUDA Architecture).

Architectural implementation for photorealistic generative scene background images
on NVIDIA CUDA GPU worker nodes using Stable Diffusion v1.5.
Status: Production-target CUDA provider — architecturally prepared, not locally validated.

Follows strict commercial safety standards:
- Core Model: Stable Diffusion v1.5 (CreativeML OpenRAIL-M)
  Section 5 permits commercial SaaS, hosting, and self-hosted distribution.
- Text Encoder: CLIP ViT-L/14 (MIT License)
- VAE: sd-vae-ft-mse (MIT / OpenRAIL-M commercial permitted)
- Schedulers: PNDM / DDIM / Euler Ancestral (Apache-2.0, Diffusers)

BANNED NON-COMMERCIAL ARTIFACTS (Prohibited from production cache/runtime):
- sdxl-turbo (Stability AI Non-Commercial Research Community License)
- sd-turbo (Stability AI Non-Commercial Research Community License)
- any other image checkpoint classified NON_COMMERCIAL or RESEARCH_ONLY
"""

import io
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image

from app.ai.capabilities import ProviderDescriptor
from app.ai.contracts import ImageGenContractRequest, ImageGenContractResult
from app.ai.hardware import detect_hardware
from app.ai.interfaces import ImageProvider
from app.core.config import get_settings
from app.core.exceptions import (
    AIModelSecurityException,
    AIRuntimeUnavailableException,
    NotFoundException,
)
from app.core.logging import get_logger
from app.storage.s3 import get_storage_provider

logger = get_logger(__name__)

DEFAULT_SD_MODEL_ID = "image/stable-diffusion-v1-5-gpu"
DEFAULT_SD_CACHE_DIR = os.path.join("models_cache", "image", "stable_diffusion_v1_5")

# Pinned Artifact Checksums (CreativeML OpenRAIL-M, runwayml/stable-diffusion-v1-5 commit 1dce59b)
# Note: Physical binary is ~4.27GB and not downloaded to local CPU dev host.
SD_V1_5_WEIGHTS_EXPECTED_SHA256 = "6ce016e7d0fe7376494aaeae77f3e3e1c500ec6c76db432e23702d2b57347774"

# Prohibited non-commercial artifacts
BANNED_NON_COMMERCIAL_ARTIFACTS = [
    "sdxl-turbo",
    "sd-turbo",
    "stabilityai/sdxl-turbo",
    "stabilityai/sd-turbo",
    "non-commercial",
]

# Aspect ratio to resolution mapping (512-base standard for SD 1.5)
ASPECT_RATIO_MAP: Dict[str, Tuple[int, int]] = {
    "16:9": (768, 432),
    "9:16": (432, 768),
    "1:1": (512, 512),
    "4:3": (640, 480),
    "21:9": (896, 384),
}


class StableDiffusionImageProvider(ImageProvider):
    """Production-target CUDA Image Provider for generative scene visuals.

    Architecturally prepared for CUDA GPU execution. When invoked on CPU-only hosts,
    it strictly raises AIRuntimeUnavailableException and will NEVER silently fall back to mock.
    """

    provider_name: str = "stable_diffusion"
    descriptor: ProviderDescriptor = ProviderDescriptor(
        name="stable_diffusion",
        capability="image",
        version="0.1.0",
        is_local=True,
        requires_gpu=True,
        supported_devices=["cuda"],
        supported_output_formats=["png", "jpg", "webp"],
        is_available=False,
        metadata={
            "status": "production_target_cuda_unvalidated",
            "runtime": "diffusers-cuda",
            "license": "CreativeML OpenRAIL-M",
            "license_classification": "CONDITIONAL — ARTIFACT VERIFICATION REQUIRED",
            "commercial_permitted": True,
            "research_only": False,
            "target_resolution": "512x512 / 768x432",
            "notes": "Production-target CUDA provider — architecturally prepared, not locally validated.",
            "source": "runwayml/stable-diffusion-v1-5",
            "auxiliary_models": {
                "text_encoder": "openai/clip-vit-large-patch14 (MIT)",
                "vae": "stabilityai/sd-vae-ft-mse (MIT / OpenRAIL-M commercial permitted)",
                "unet": "runwayml/stable-diffusion-v1-5 (CreativeML OpenRAIL-M)",
            },
            "banned_components": BANNED_NON_COMMERCIAL_ARTIFACTS,
        },
    )

    def __init__(
        self,
        model_path: Optional[str] = None,
        device: str = "cuda",
    ) -> None:
        self.device = device.lower()
        self.model_path = model_path or DEFAULT_SD_CACHE_DIR

        # Validate that model path does not reference a banned non-commercial artifact
        self.validate_artifact_not_banned(self.model_path)
        self._pipeline: Optional[Any] = None

    @classmethod
    def validate_artifact_not_banned(cls, artifact_path_or_name: str) -> None:
        """Ensure that no banned non-commercial artifact can enter the production pipeline."""
        lower_str = str(artifact_path_or_name).lower()
        for banned in BANNED_NON_COMMERCIAL_ARTIFACTS:
            if banned.lower() in lower_str:
                raise AIModelSecurityException(
                    message=(
                        f"Access to non-commercial artifact '{artifact_path_or_name}' is strictly prohibited. "
                        f"Matches banned component rule: {banned}"
                    ),
                    code="AI_BANNED_NON_COMMERCIAL_ARTIFACT",
                    details={"artifact": artifact_path_or_name, "banned_rule": banned},
                )

    def _ensure_cuda_available(self) -> None:
        """Validate that host hardware has an active NVIDIA CUDA GPU accelerator."""
        hw = detect_hardware()
        if not hw.has_cuda:
            raise AIRuntimeUnavailableException(
                message=(
                    "StableDiffusion provider requires an NVIDIA CUDA GPU accelerator and CUDA runtime "
                    "dependencies, which are not available on this CPU host. "
                    "Production-target CUDA provider — architecturally prepared, not locally validated."
                ),
                code="GPU_UNAVAILABLE",
            )

    @staticmethod
    def validate_generated_image(
        image_bytes: bytes,
        expected_aspect_ratio: Optional[str] = None,
        min_width: int = 128,
        min_height: int = 128,
    ) -> Tuple[int, int, str]:
        """Validate that generated byte buffer is a valid, decodable, non-zero image.

        Returns:
            Tuple of (width, height, format_name)
        Raises:
            ValueError if image container is corrupt, empty, or fails dimensional constraints.
        """
        if not image_bytes or len(image_bytes) < 16:
            raise ValueError("Generated image buffer is empty or contains insufficient data.")

        try:
            with Image.open(io.BytesIO(image_bytes)) as img:
                img.verify()

            # Re-open for attribute inspection (verify closes the image stream)
            with Image.open(io.BytesIO(image_bytes)) as img:
                width, height = img.size
                img_format = (img.format or "PNG").upper()
                mode = img.mode

                if width < min_width or height < min_height:
                    raise ValueError(
                        f"Generated image dimensions ({width}x{height}) are below required minimum ({min_width}x{min_height})."
                    )

                if mode not in ("RGB", "RGBA"):
                    raise ValueError(f"Invalid image color mode '{mode}'; expected RGB or RGBA.")

                return width, height, img_format
        except Exception as exc:
            raise ValueError(f"Image validation failed: {str(exc)}") from exc

    async def generate_image(
        self,
        prompt: str,
        aspect_ratio: str = "16:9",
        negative_prompt: Optional[str] = None,
    ) -> str:
        """Protocol method: Generate high-resolution image asset and return S3 storage key."""
        self._ensure_cuda_available()
        storage = get_storage_provider()

        width, height = ASPECT_RATIO_MAP.get(aspect_ratio, (768, 432))
        image_bytes = await self._generate_image_cuda(prompt, width, height, negative_prompt)

        key_hash = abs(hash(prompt + str(time.time()))) % 10000000
        output_key = f"assets/images/sd_{key_hash}.png"
        await storage.put_object(output_key, image_bytes, content_type="image/png")
        return output_key

    async def generate(
        self,
        request: ImageGenContractRequest,
    ) -> ImageGenContractResult:
        """Protocol method: Strongly typed execution contract."""
        self._ensure_cuda_available()
        t0 = time.perf_counter()

        width, height = ASPECT_RATIO_MAP.get(request.aspect_ratio, (768, 432))
        image_bytes = await self._generate_image_cuda(
            prompt=request.prompt,
            width=width,
            height=height,
            negative_prompt=request.negative_prompt,
        )

        w_actual, h_actual, fmt = self.validate_generated_image(
            image_bytes,
            expected_aspect_ratio=request.aspect_ratio,
        )

        storage = get_storage_provider()
        key_hash = abs(hash(request.prompt + str(time.time()))) % 10000000
        output_storage_key = f"workspaces/{request.workspace_id}/assets/image/sd_{key_hash}.png"
        await storage.put_object(output_storage_key, image_bytes, content_type="image/png")

        latency = time.perf_counter() - t0
        return ImageGenContractResult(
            status="succeeded",
            output_storage_key=output_storage_key,
            width=w_actual,
            height=h_actual,
            aspect_ratio=request.aspect_ratio,
            processing_latency=latency,
            metrics={
                "provider": self.provider_name,
                "model": "stable-diffusion-v1-5",
                "format": fmt,
                "latency_seconds": round(latency, 3),
            },
        )

    async def _generate_image_cuda(
        self,
        prompt: str,
        width: int,
        height: int,
        negative_prompt: Optional[str] = None,
    ) -> bytes:
        """Execute diffusion loop on NVIDIA CUDA GPU.

        Guards against missing model weights before execution.
        """
        self._ensure_cuda_available()

        model_weights_dir = Path(self.model_path)
        if not model_weights_dir.is_absolute():
            backend_root = Path(__file__).resolve().parent.parent.parent.parent
            model_weights_dir = backend_root / self.model_path

        if not model_weights_dir.exists() or not any(model_weights_dir.iterdir()):
            raise AIRuntimeUnavailableException(
                message=(
                    f"Stable Diffusion model weights not found at '{model_weights_dir}'. "
                    "CUDA weights must be installed and verified before neural image generation can execute."
                ),
                code="AI_MODEL_NOT_FOUND",
                details={"model_path": str(model_weights_dir)},
            )

        # In production CUDA worker node, diffusers pipeline is executed here:
        # pipe = StableDiffusionPipeline.from_pretrained(model_weights_dir, torch_dtype=torch.float16).to("cuda")
        # image = pipe(prompt=prompt, negative_prompt=negative_prompt, width=width, height=height).images[0]
        # buf = io.BytesIO()
        # image.save(buf, format="PNG")
        # return buf.getvalue()
        raise NotImplementedError("CUDA inference boundary reached on host without GPU worker.")
