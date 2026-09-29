"""Unit tests for Stable Diffusion Production-Target CUDA Image Provider adapter.

Validates:
1. Provider registration & descriptor metadata (CreativeML OpenRAIL-M).
2. Commercial license metadata & explicit banning of non-commercial components (SDXL-Turbo, SD-Turbo).
3. Active rejection of banned model paths.
4. Refusal to execute on CPU-only host with strict GPU_UNAVAILABLE error.
5. Strict no-fallback to mock behavior in real mode.
6. Model catalog registration & hardware compatibility filtering in ModelRegistry.
7. Pillow image container and dimension validation.
8. Celery gpu_ai vs cpu_media queue routing.
9. Aspect ratio to resolution mapping.
10. Missing weights on CUDA guard.
"""

import io
import uuid
import pytest
from PIL import Image

from app.ai.adapters.stable_diffusion import (
    ASPECT_RATIO_MAP,
    BANNED_NON_COMMERCIAL_ARTIFACTS,
    DEFAULT_SD_MODEL_ID,
    SD_V1_5_WEIGHTS_EXPECTED_SHA256,
    StableDiffusionImageProvider,
)
from app.ai.contracts import ImageGenContractRequest
from app.ai.hardware import detect_hardware
from app.ai.model_registry import get_model_registry
from app.ai.registry import get_ai_registry, get_image_provider
from app.core.exceptions import (
    AIModelSecurityException,
    AIRuntimeUnavailableException,
)
from app.services.job_service import resolve_job_queue


def test_sd_descriptor_and_metadata():
    """Verify Stable Diffusion descriptor records production-target CUDA status and licensing."""
    provider = StableDiffusionImageProvider()
    desc = provider.descriptor

    assert desc.name == "stable_diffusion"
    assert desc.capability == "image"
    assert desc.is_local is True
    assert desc.requires_gpu is True
    assert desc.supported_devices == ["cuda"]
    assert desc.supported_output_formats == ["png", "jpg", "webp"]
    assert desc.is_available is False

    meta = desc.metadata
    assert meta["status"] == "production_target_cuda_unvalidated"
    assert meta["runtime"] == "diffusers-cuda"
    assert meta["commercial_permitted"] is True
    assert meta["research_only"] is False
    assert meta["license"] == "CreativeML OpenRAIL-M"
    assert meta["license_classification"] == "CONDITIONAL — ARTIFACT VERIFICATION REQUIRED"
    assert "text_encoder" in meta["auxiliary_models"]
    assert "runwayml/stable-diffusion-v1-5" in meta["source"]


def test_sd_banned_non_commercial_components():
    """Verify that all non-commercial components are explicitly banned and actively rejected."""
    provider = StableDiffusionImageProvider()
    banned = provider.descriptor.metadata["banned_components"]

    assert "sdxl-turbo" in banned
    assert "sd-turbo" in banned

    # Verify that attempting to load or reference any banned artifact raises AIModelSecurityException
    for item in banned:
        with pytest.raises(AIModelSecurityException) as exc:
            StableDiffusionImageProvider(model_path=f"/path/to/{item}")
        assert exc.value.code == "AI_BANNED_NON_COMMERCIAL_ARTIFACT"


@pytest.mark.asyncio
async def test_sd_cpu_refusal_raises_gpu_unavailable():
    """Verify that calling Stable Diffusion inference methods on CPU-only host raises AIRuntimeUnavailableException."""
    provider = StableDiffusionImageProvider()
    hw = detect_hardware()

    if not hw.has_cuda:
        # 1. Direct generate_image
        with pytest.raises(AIRuntimeUnavailableException) as exc1:
            await provider.generate_image("A futuristic city at sunset", aspect_ratio="16:9")
        assert exc1.value.code == "GPU_UNAVAILABLE"
        assert "Production-target CUDA provider — architecturally prepared, not locally validated" in str(exc1.value)

        # 2. Direct contract generate
        req = ImageGenContractRequest(
            workspace_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            prompt="A cinematic video background",
            aspect_ratio="16:9",
        )
        with pytest.raises(AIRuntimeUnavailableException) as exc2:
            await provider.generate(req)
        assert exc2.value.code == "GPU_UNAVAILABLE"


def test_sd_registry_resolution_on_cpu():
    """Verify registry get_image_provider('stable_diffusion') strictly raises GPU_UNAVAILABLE on CPU host."""
    hw = detect_hardware()
    if not hw.has_cuda:
        registry = get_ai_registry()
        with pytest.raises(AIRuntimeUnavailableException) as exc:
            registry.get_image_provider("stable_diffusion")
        assert exc.value.code == "GPU_UNAVAILABLE"


def test_sd_model_registry_catalog_entry():
    """Verify model catalog entry for image/stable-diffusion-v1-5-gpu has correct metadata and requirements."""
    registry = get_model_registry()
    model = registry.get_model(DEFAULT_SD_MODEL_ID)

    assert model is not None
    assert model.model_id == "image/stable-diffusion-v1-5-gpu"
    assert model.provider == "stable_diffusion"
    assert model.capability == "image"
    assert model.requires_gpu is True
    assert model.supported_devices == ["cuda"]
    assert model.license == "CreativeML OpenRAIL-M"
    assert model.license_commercial_permitted is True
    assert model.metadata["status"] == "production_target_cuda_unvalidated"
    assert model.metadata["license_classification"] == "CONDITIONAL — ARTIFACT VERIFICATION REQUIRED"
    assert model.checksum_sha256 == SD_V1_5_WEIGHTS_EXPECTED_SHA256

    hw = detect_hardware()
    is_compat, state, reason = model.is_compatible_with(hw)
    if not hw.has_cuda:
        assert is_compat is False
        assert "CUDA GPU" in reason or "requires_gpu" in reason or "not operational" in reason


def test_sd_image_validation():
    """Verify image container and dimension validation logic."""
    # 1. Valid PNG
    img = Image.new("RGB", (768, 432), color=(100, 150, 200))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    valid_bytes = buf.getvalue()

    w, h, fmt = StableDiffusionImageProvider.validate_generated_image(valid_bytes)
    assert w == 768
    assert h == 432
    assert fmt == "PNG"

    # 2. Corrupted bytes
    with pytest.raises(ValueError) as exc1:
        StableDiffusionImageProvider.validate_generated_image(b"not_an_image_corrupt_data")
    assert "Image validation failed" in str(exc1.value) or "insufficient data" in str(exc1.value)

    # 3. Empty buffer
    with pytest.raises(ValueError) as exc2:
        StableDiffusionImageProvider.validate_generated_image(b"")
    assert "empty" in str(exc2.value) or "insufficient data" in str(exc2.value)

    # 4. Undersized image
    tiny_img = Image.new("RGB", (64, 64), color=(0, 0, 0))
    tiny_buf = io.BytesIO()
    tiny_img.save(tiny_buf, format="PNG")
    with pytest.raises(ValueError) as exc3:
        StableDiffusionImageProvider.validate_generated_image(tiny_buf.getvalue(), min_width=128, min_height=128)
    assert "below required minimum" in str(exc3.value)


def test_sd_celery_queue_routing():
    """Verify Celery task queue resolution for scene visual jobs."""
    # 1. Stable Diffusion provider routes to gpu_ai
    q1 = resolve_job_queue("generate_scene_visual", {"provider": "stable_diffusion"})
    assert q1 == "gpu_ai"

    # 2. CUDA device routes to gpu_ai
    q2 = resolve_job_queue("generate_scene_visual", {"preferred_device": "cuda"})
    assert q2 == "gpu_ai"

    # 3. Mock provider routes to cpu_media
    q3 = resolve_job_queue("generate_scene_visual", {"provider": "mock"})
    assert q3 == "cpu_media"

    # 4. Explicit CPU device routes to cpu_media
    q4 = resolve_job_queue("generate_scene_visual", {"preferred_device": "cpu"})
    assert q4 == "cpu_media"


def test_sd_aspect_ratio_mapping():
    """Verify aspect ratio to resolution mapping conforms to standard 512-base dimensions."""
    assert ASPECT_RATIO_MAP["16:9"] == (768, 432)
    assert ASPECT_RATIO_MAP["9:16"] == (432, 768)
    assert ASPECT_RATIO_MAP["1:1"] == (512, 512)
    assert ASPECT_RATIO_MAP["4:3"] == (640, 480)
    assert ASPECT_RATIO_MAP["21:9"] == (896, 384)


def test_sd_missing_weights_on_cuda_guard(monkeypatch):
    """Verify that if CUDA were available, missing weights directory raises AI_MODEL_NOT_FOUND."""
    from unittest.mock import MagicMock
    mock_hw = MagicMock()
    mock_hw.has_cuda = True
    monkeypatch.setattr("app.ai.adapters.stable_diffusion.detect_hardware", lambda: mock_hw)

    provider = StableDiffusionImageProvider(model_path="models_cache/nonexistent_sd_weights")
    with pytest.raises(AIRuntimeUnavailableException) as exc:
        provider._ensure_cuda_available()
        import asyncio
        asyncio.run(provider._generate_image_cuda(
            prompt="test prompt",
            width=512,
            height=512,
        ))
    assert exc.value.code == "AI_MODEL_NOT_FOUND"
