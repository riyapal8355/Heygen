"""Deterministic GPU Model Manifest, Policy and Artifact Integrity Catalog.

Enforces strict commercial safety, byte-size, checksum, and licensing policies
for all GPU worker workloads.
"""

from enum import Enum
import os
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.core.exceptions import AIModelSecurityException


class CommercialStatus(str, Enum):
    APPROVED = "APPROVED"
    CONDITIONAL = "CONDITIONAL"
    BLOCKED = "BLOCKED"
    NON_COMMERCIAL = "NON_COMMERCIAL"
    RESEARCH_ONLY = "RESEARCH_ONLY"
    UNKNOWN = "UNKNOWN"


# Explicit list of banned non-commercial or prohibited component patterns
BANNED_ARTIFACT_PATTERNS = [
    # Non-commercial face parser & detector weights
    "s3fd",
    "79999_iter.pth",
    "face-parse-bisent",
    "celebamask-hq",
    "celebamask",
    "insightface",
    "buffalo_l",
    "1k3d68.onnx",
    "bfm_2009",
    "bfm2009",
    "codeformer",
    # Blocked video & turbo models
    "animatediff",
    "sdxl-turbo",
    "sd-turbo",
    "modelscope",
    "zeroscope",
]


class GPUArtifactManifestEntry(BaseModel):
    """Declarative specification for a GPU model artifact."""
    model_config = ConfigDict(extra="forbid")

    model_id: str
    provider: str
    capability: str
    repository: str
    revision: str
    filename: str
    relative_path: str
    expected_size_bytes: int = Field(..., ge=0)
    expected_sha256: Optional[str] = None
    license: str
    provenance: str
    commercial_status: CommercialStatus
    runtime: str
    supported_devices: List[str] = Field(default_factory=lambda: ["cuda"])
    requires_gpu: bool = True
    minimum_vram_gb: float = Field(8.0, ge=0.0)
    description: str = ""


# Deterministic GPU Catalog Manifest
GPU_MODEL_MANIFEST: Dict[str, GPUArtifactManifestEntry] = {
    # 1. OpenCV YuNet Face Detection (Commercial Safe, MIT/Apache-2.0, verified)
    "avatar/yunet-2023mar": GPUArtifactManifestEntry(
        model_id="avatar/yunet-2023mar",
        provider="musetalk",
        capability="avatar",
        repository="opencv/opencv_zoo",
        revision="2023mar",
        filename="face_detection_yunet_2023mar.onnx",
        relative_path=os.path.join("avatar", "face_detector", "face_detection_yunet_2023mar.onnx"),
        expected_size_bytes=232589,
        expected_sha256="8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4",
        license="Apache-2.0",
        provenance="https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
        commercial_status=CommercialStatus.APPROVED,
        runtime="onnxruntime-cuda",
        supported_devices=["cuda", "cpu"],
        requires_gpu=False,
        minimum_vram_gb=0.5,
        description="YuNet lightweight high-speed neural face detector for avatar lip-sync preprocessing",
    ),

    # 2. MuseTalk Core UNet (Conditional — physical artifact verification required upon download)
    "avatar/musetalk-core": GPUArtifactManifestEntry(
        model_id="avatar/musetalk-core",
        provider="musetalk",
        capability="avatar",
        repository="TMElyralab/MuseTalk",
        revision="main",
        filename="pytorch_model.bin",
        relative_path=os.path.join("avatar", "musetalk", "pytorch_model.bin"),
        expected_size_bytes=3436000000,
        expected_sha256="e031a0ea4c169be865b6a71ec26d03d420b92ea71060937a0914a87adbfb0662",
        license="MIT",
        provenance="https://huggingface.co/TMElyralab/MuseTalk/resolve/main/musetalk/pytorch_model.bin",
        commercial_status=CommercialStatus.CONDITIONAL,
        runtime="pytorch-cuda",
        supported_devices=["cuda"],
        requires_gpu=True,
        minimum_vram_gb=6.0,
        description="MuseTalk real-time neural inpainting lip-sync model",
    ),

    # 3. MuseTalk VAE (sd-vae-ft-mse)
    "avatar/musetalk-vae": GPUArtifactManifestEntry(
        model_id="avatar/musetalk-vae",
        provider="musetalk",
        capability="avatar",
        repository="stabilityai/sd-vae-ft-mse",
        revision="main",
        filename="diffusion_pytorch_model.bin",
        relative_path=os.path.join("avatar", "musetalk", "vae", "diffusion_pytorch_model.bin"),
        expected_size_bytes=334640000,
        expected_sha256="374f073289060b298453cc14b1959b360ea1df7042a5ec2ec9cb4326129994c6",
        license="MIT / CreativeML OpenRAIL-M",
        provenance="https://huggingface.co/stabilityai/sd-vae-ft-mse/resolve/main/diffusion_pytorch_model.bin",
        commercial_status=CommercialStatus.CONDITIONAL,
        runtime="pytorch-cuda",
        supported_devices=["cuda"],
        requires_gpu=True,
        minimum_vram_gb=1.0,
        description="Fine-tuned MSE VAE decoder for image/avatar latent reconstruction",
    ),

    # 4. Stable Diffusion v1.5 (RunwayML / CreativeML OpenRAIL-M, Conditional until physical verification)
    "image/stable-diffusion-v1-5-gpu": GPUArtifactManifestEntry(
        model_id="image/stable-diffusion-v1-5-gpu",
        provider="stable_diffusion",
        capability="image",
        repository="runwayml/stable-diffusion-v1-5",
        revision="1dce59b",
        filename="v1-5-pruned-emaonly.safetensors",
        relative_path=os.path.join("image", "stable_diffusion_v1_5", "v1-5-pruned-emaonly.safetensors"),
        expected_size_bytes=4265380512,
        expected_sha256="6ce016e7d0fe7376494aaeae77f3e3e1c500ec6c76db432e23702d2b57347774",
        license="CreativeML OpenRAIL-M",
        provenance="https://huggingface.co/runwayml/stable-diffusion-v1-5/resolve/1dce59b/v1-5-pruned-emaonly.safetensors",
        commercial_status=CommercialStatus.CONDITIONAL,
        runtime="diffusers-cuda",
        supported_devices=["cuda"],
        requires_gpu=True,
        minimum_vram_gb=6.0,
        description="Stable Diffusion v1.5 text-to-image generator for HeyZen scene visuals",
    ),

    # 5. STRICTLY BLOCKED ENTRIES (Fail-closed enforcement)
    "video/animatediff-v1-5": GPUArtifactManifestEntry(
        model_id="video/animatediff-v1-5",
        provider="animatediff",
        capability="video",
        repository="guoyww/animatediff-motion-adapter-v1-5-2",
        revision="blocked",
        filename="diffusion_pytorch_model.safetensors",
        relative_path="video/animatediff/diffusion_pytorch_model.safetensors",
        expected_size_bytes=0,
        expected_sha256=None,
        license="Unverified / Non-Commercial Ambiguity",
        provenance="BLOCKED",
        commercial_status=CommercialStatus.BLOCKED,
        runtime="diffusers-cuda",
        supported_devices=[],
        requires_gpu=True,
        minimum_vram_gb=12.0,
        description="AnimateDiff motion adapter is STRICTLY BLOCKED from HeyZen production",
    ),
    "image/sdxl-turbo": GPUArtifactManifestEntry(
        model_id="image/sdxl-turbo",
        provider="stability",
        capability="image",
        repository="stabilityai/sdxl-turbo",
        revision="blocked",
        filename="model.safetensors",
        relative_path="image/sdxl_turbo/model.safetensors",
        expected_size_bytes=0,
        expected_sha256=None,
        license="Stability AI Non-Commercial Research Community License",
        provenance="BLOCKED",
        commercial_status=CommercialStatus.BLOCKED,
        runtime="diffusers-cuda",
        supported_devices=[],
        requires_gpu=True,
        minimum_vram_gb=8.0,
        description="SDXL-Turbo is STRICTLY BLOCKED due to non-commercial research license",
    ),
    "image/sd-turbo": GPUArtifactManifestEntry(
        model_id="image/sd-turbo",
        provider="stability",
        capability="image",
        repository="stabilityai/sd-turbo",
        revision="blocked",
        filename="model.safetensors",
        relative_path="image/sd_turbo/model.safetensors",
        expected_size_bytes=0,
        expected_sha256=None,
        license="Stability AI Non-Commercial Research Community License",
        provenance="BLOCKED",
        commercial_status=CommercialStatus.BLOCKED,
        runtime="diffusers-cuda",
        supported_devices=[],
        requires_gpu=True,
        minimum_vram_gb=8.0,
        description="SD-Turbo is STRICTLY BLOCKED due to non-commercial research license",
    ),
    "video/modelscope-t2v": GPUArtifactManifestEntry(
        model_id="video/modelscope-t2v",
        provider="modelscope",
        capability="video",
        repository="damo-vilab/modelscope-damo-text-to-video-synthesis",
        revision="blocked",
        filename="model.bin",
        relative_path="video/modelscope/model.bin",
        expected_size_bytes=0,
        expected_sha256=None,
        license="Research Only",
        provenance="BLOCKED",
        commercial_status=CommercialStatus.BLOCKED,
        runtime="pytorch-cuda",
        supported_devices=[],
        requires_gpu=True,
        minimum_vram_gb=16.0,
        description="ModelScope T2V is STRICTLY BLOCKED from HeyZen production",
    ),
    "video/zeroscope": GPUArtifactManifestEntry(
        model_id="video/zeroscope",
        provider="zeroscope",
        capability="video",
        repository="cerspense/zeroscope_v2_576w",
        revision="blocked",
        filename="model.safetensors",
        relative_path="video/zeroscope/model.safetensors",
        expected_size_bytes=0,
        expected_sha256=None,
        license="CC-BY-NC-4.0",
        provenance="BLOCKED",
        commercial_status=CommercialStatus.BLOCKED,
        runtime="diffusers-cuda",
        supported_devices=[],
        requires_gpu=True,
        minimum_vram_gb=12.0,
        description="Zeroscope is STRICTLY BLOCKED due to CC-BY-NC-4.0 non-commercial restrictions",
    ),
}


def assert_artifact_not_blocked(artifact_name_or_id: str) -> None:
    """Fail-closed assertion ensuring no blocked or non-commercial artifact can be provisioned or loaded.

    Raises:
        AIModelSecurityException: If artifact matches any banned pattern or is marked BLOCKED.
    """
    clean = str(artifact_name_or_id).strip().lower()
    for banned in BANNED_ARTIFACT_PATTERNS:
        if banned in clean:
            raise AIModelSecurityException(
                message=f"Artifact '{artifact_name_or_id}' is strictly BLOCKED from HeyZen production by security policy ({banned}).",
                code="AI_MODEL_SECURITY_BLOCKED",
                details={"artifact": artifact_name_or_id, "banned_rule": banned},
            )

    # Check manifest entry if registered
    entry = GPU_MODEL_MANIFEST.get(clean) or GPU_MODEL_MANIFEST.get(artifact_name_or_id)
    if entry and entry.commercial_status in (
        CommercialStatus.BLOCKED,
        CommercialStatus.NON_COMMERCIAL,
        CommercialStatus.RESEARCH_ONLY,
    ):
        raise AIModelSecurityException(
            message=f"Model '{entry.model_id}' is BLOCKED (license={entry.license}, status={entry.commercial_status.value}).",
            code="AI_MODEL_SECURITY_BLOCKED",
            details={"model_id": entry.model_id, "status": entry.commercial_status.value},
        )


def get_gpu_manifest_entry(model_id: str) -> Optional[GPUArtifactManifestEntry]:
    """Retrieve catalog manifest entry by unique model ID."""
    return GPU_MODEL_MANIFEST.get(model_id.strip())
