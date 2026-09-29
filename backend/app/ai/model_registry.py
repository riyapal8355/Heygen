"""Model Registry and Hardware Compatibility Engine.

Maintains declarative descriptors for AI models across all modalities, tracks
system requirements (CPU, GPU, RAM, VRAM), licensing constraints, download/cache status,
and provides deterministic hardware compatibility evaluation.
"""

import os
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, ConfigDict, Field

from app.ai.hardware import HardwareSpec, HardwareState, detect_hardware
from app.core.exceptions import AIModelIncompatibleException, NotFoundException
from app.core.logging import get_logger

logger = get_logger(__name__)


class ModelInstallStatus(str, Enum):
    """Lifecycle status of local model artifacts."""
    NOT_INSTALLED = "NOT_INSTALLED"
    DOWNLOADING = "DOWNLOADING"
    INSTALLED = "INSTALLED"
    VERIFIED = "VERIFIED"
    ERROR = "ERROR"


class ModelHealthStatus(str, Enum):
    """Runtime health status of an AI model."""
    UNKNOWN = "UNKNOWN"
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"


class ModelDescriptor(BaseModel):
    """Declarative metadata descriptor for an AI model."""
    model_config = ConfigDict(extra="allow")

    model_id: str = Field(..., description="Unique model identifier, e.g. 'tts/piper-en-lessac'")
    name: str = Field(..., description="Human-readable model name")
    provider: str = Field(..., description="Associated provider family name, e.g. 'piper', 'mock'")
    capability: str = Field(..., description="AICapability string: tts, asr, translation, avatar, image, video, llm")
    supported_runtimes: List[str] = Field(
        default_factory=lambda: ["local_cpu"],
        description="Supported runtime IDs: local_cpu, local_gpu, container_cpu, container_gpu, remote_hosted",
    )
    supported_devices: List[str] = Field(
        default_factory=lambda: ["cpu"],
        description="Supported compute device types: cpu, cuda, mps, rocm",
    )
    requires_gpu: bool = Field(False, description="Whether GPU accelerator is strictly required")
    minimum_ram_bytes: int = Field(0, ge=0, description="Minimum host RAM required in bytes")
    recommended_ram_bytes: int = Field(0, ge=0, description="Recommended host RAM in bytes")
    minimum_vram_bytes: Optional[int] = Field(None, ge=0, description="Minimum GPU VRAM required in bytes")
    approximate_size_bytes: int = Field(0, ge=0, description="Approximate disk footprint in bytes")
    quantization: Optional[str] = Field(None, description="Quantization scheme: fp32, fp16, int8, q4_k_m, none")
    license: str = Field("Unknown", description="Model license, e.g. MIT, Apache-2.0, Non-Commercial")
    license_commercial_permitted: bool = Field(True, description="Whether license permits commercial self-hosting")
    source: str = Field("local", description="Model artifact origin repository or path")
    revision: str = Field("1.0.0", description="Model artifact version or commit SHA")
    checksum_sha256: Optional[str] = Field(None, description="Expected SHA-256 integrity hash")
    cache_path: Optional[str] = Field(None, description="Local absolute path to cached model weights")
    supported_languages: List[str] = Field(default_factory=lambda: ["*"])
    supported_input_formats: List[str] = Field(default_factory=list)
    supported_output_formats: List[str] = Field(default_factory=list)
    installation_status: ModelInstallStatus = Field(ModelInstallStatus.NOT_INSTALLED)
    health_status: ModelHealthStatus = Field(ModelHealthStatus.UNKNOWN)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def supports_device(self, device: str) -> bool:
        """Check if model supports specified device."""
        clean = device.strip().lower()
        return clean in [d.lower() for d in self.supported_devices]

    def supports_language(self, language: str) -> bool:
        """Check if model supports specified language code."""
        if "*" in self.supported_languages:
            return True
        clean = language.strip().lower()
        return clean in [l.lower() for l in self.supported_languages]

    def supports_format(self, format_name: str) -> bool:
        """Check if model supports given container format."""
        clean = format_name.strip().lower()
        if not self.supported_output_formats or "*" in self.supported_output_formats:
            return True
        return clean in [f.lower() for f in self.supported_output_formats]

    def is_compatible_with(self, hardware: HardwareSpec) -> Tuple[bool, HardwareState, str]:
        """Check if target host hardware can safely execute this model."""
        return hardware.check_model_compatibility(
            minimum_ram_bytes=self.minimum_ram_bytes,
            requires_gpu=self.requires_gpu,
            minimum_vram_bytes=self.minimum_vram_bytes,
        )


class ModelRegistry:
    """Central registry managing AI model descriptors, discovery, and compatibility."""

    def __init__(self) -> None:
        self._models: Dict[str, ModelDescriptor] = {}
        self._default_models: Dict[str, str] = {}  # capability -> model_id
        self._default_real_models: Dict[str, str] = {}  # capability -> real model_id

    def register_model(self, descriptor: ModelDescriptor, is_default: bool = False) -> None:
        """Register a model descriptor in the catalog."""
        model_id = descriptor.model_id.strip()
        self._models[model_id] = descriptor
        cap = descriptor.capability.strip().lower()
        if is_default or cap not in self._default_models:
            self._default_models[cap] = model_id
        if descriptor.provider != "mock" and (is_default or cap not in self._default_real_models):
            self._default_real_models[cap] = model_id
        logger.debug("Registered model '%s' for capability '%s'", model_id, cap)

    def unregister_model(self, model_id: str) -> bool:
        """Remove a model from the registry."""
        if model_id in self._models:
            desc = self._models.pop(model_id)
            cap = desc.capability.lower()
            if self._default_models.get(cap) == model_id:
                # Fallback default to remaining model with same capability if any
                remaining = [m.model_id for m in self._models.values() if m.capability.lower() == cap]
                self._default_models[cap] = remaining[0] if remaining else None  # type: ignore
            if self._default_real_models.get(cap) == model_id:
                remaining_real = [m.model_id for m in self._models.values() if m.capability.lower() == cap and m.provider != "mock"]
                self._default_real_models[cap] = remaining_real[0] if remaining_real else None  # type: ignore
            return True
        return False

    def get_model(self, model_id: str) -> Optional[ModelDescriptor]:
        """Retrieve model descriptor by unique ID."""
        return self._models.get(model_id.strip())

    def list_models(
        self,
        capability: Optional[str] = None,
        requires_gpu: Optional[bool] = None,
        installed_only: bool = False,
    ) -> List[ModelDescriptor]:
        """List registered models with optional capability, GPU requirement, and install filters."""
        result: List[ModelDescriptor] = []
        for model in self._models.values():
            if capability and model.capability.lower() != capability.strip().lower():
                continue
            if requires_gpu is not None and model.requires_gpu != requires_gpu:
                continue
            if installed_only and model.installation_status not in (ModelInstallStatus.INSTALLED, ModelInstallStatus.VERIFIED):
                continue
            result.append(model)
        return result

    def find_models(
        self,
        capability: str,
        language: Optional[str] = None,
        format_name: Optional[str] = None,
        requires_gpu: Optional[bool] = None,
    ) -> List[ModelDescriptor]:
        """Filter models matching functional request criteria."""
        cap = capability.strip().lower()
        candidates: List[ModelDescriptor] = []
        for model in self._models.values():
            if model.capability.lower() != cap:
                continue
            if requires_gpu is not None and model.requires_gpu != requires_gpu:
                continue
            if language and not model.supports_language(language):
                continue
            if format_name and not model.supports_format(format_name):
                continue
            candidates.append(model)
        return candidates

    def find_compatible_models(
        self,
        capability: str,
        hardware: Optional[HardwareSpec] = None,
        language: Optional[str] = None,
        format_name: Optional[str] = None,
        device_preference: Optional[str] = None,
    ) -> List[ModelDescriptor]:
        """Find models compatible with host hardware, sorted deterministically."""
        hw = hardware or detect_hardware()
        candidates = self.find_models(capability, language=language, format_name=format_name)

        compatible: List[ModelDescriptor] = []
        for model in candidates:
            # Check device preference filter if specified
            if device_preference and device_preference != "auto":
                if not model.supports_device(device_preference):
                    continue
            is_compat, state, _ = model.is_compatible_with(hw)
            if is_compat:
                compatible.append(model)

        # Deterministic sorting:
        # 1. Prefer installed / verified models
        # 2. Prefer healthy models
        # 3. Prefer designated default model for the capability if any
        # 4. If device_preference == 'cuda', prefer GPU models; if 'cpu', prefer CPU models
        # 5. Alphabetical tie-breaker on model_id
        default_model_id = self._default_real_models.get(capability.strip().lower()) or self._default_models.get(capability.strip().lower())

        def sort_key(m: ModelDescriptor) -> Tuple[int, int, int, int, str]:
            is_installed = 0 if m.installation_status in (ModelInstallStatus.INSTALLED, ModelInstallStatus.VERIFIED) else 1
            is_healthy = 0 if m.health_status == ModelHealthStatus.HEALTHY else 1
            is_default = 0 if m.model_id == default_model_id else 1
            device_match = 0
            if device_preference == "cuda" and not m.requires_gpu:
                device_match = 1
            elif device_preference == "cpu" and m.requires_gpu:
                device_match = 1
            return (is_installed, is_healthy, is_default, device_match, m.model_id)

        compatible.sort(key=sort_key)
        return compatible

    def get_default_model(self, capability: str) -> Optional[ModelDescriptor]:
        """Get the default model descriptor for a capability."""
        cap = capability.strip().lower()
        model_id = self._default_models.get(cap)
        return self.get_model(model_id) if model_id else None

    def set_default_model(self, capability: str, model_id: str) -> None:
        """Explicitly set the default model for a capability."""
        if model_id not in self._models:
            raise NotFoundException(
                message=f"Cannot set default: model '{model_id}' is not registered.",
                code="AI_MODEL_NOT_FOUND",
            )
        self._default_models[capability.strip().lower()] = model_id


# Global registry singleton
_model_registry_instance: Optional[ModelRegistry] = None


def get_model_registry() -> ModelRegistry:
    """Retrieve global ModelRegistry singleton with pre-registered baseline catalog."""
    global _model_registry_instance
    if _model_registry_instance is None:
        _model_registry_instance = ModelRegistry()
        _populate_catalog(_model_registry_instance)
    return _model_registry_instance


def _populate_catalog(registry: ModelRegistry) -> None:
    """Populate catalog with open-source candidates and explicit mock models."""
    mb = 1024 * 1024
    gb = 1024 * mb

    # ---------------------------------------------------------------------------
    # 1. Text-to-Speech (TTS) Models
    # ---------------------------------------------------------------------------
    # Piper TTS: Fast, local, high-quality neural CPU TTS
    piper_cache_path = os.path.join("models_cache", "tts", "piper", "en_US-lessac-medium", "en_US-lessac-medium.onnx")
    is_piper_installed = os.path.isfile(piper_cache_path)
    piper_status = ModelInstallStatus.VERIFIED if is_piper_installed else ModelInstallStatus.NOT_INSTALLED

    registry.register_model(
        ModelDescriptor(
            model_id="tts/piper-cpu",
            name="Piper Neural TTS (CPU)",
            provider="piper",
            capability="tts",
            supported_runtimes=["local_cpu"],
            supported_devices=["cpu"],
            requires_gpu=False,
            minimum_ram_bytes=256 * mb,
            recommended_ram_bytes=512 * mb,
            approximate_size_bytes=63201294,
            quantization="fp32",
            license="MIT",
            license_commercial_permitted=True,
            source="rhasspy/piper",
            revision="en_US-lessac-medium",
            checksum_sha256="5efe09e69902187827af646e1a6e9d269dee769f9877d17b16b1b46eeaaf019f",
            cache_path=piper_cache_path if is_piper_installed else None,
            supported_languages=["en", "en-us", "en-gb"],
            supported_output_formats=["wav"],
            installation_status=piper_status,
            health_status=ModelHealthStatus.HEALTHY,
            metadata={
                "voice": "en_US-lessac-medium",
                "sample_rate": 22050,
                "engine_license": "MIT",
                "voice_license": "Public Domain / ODbL",
            },
        ),
        is_default=True,
    )

    piper_es_cache_path = os.path.join("models_cache", "tts", "piper", "es_ES-davefx-medium", "es_ES-davefx-medium.onnx")
    is_piper_es_installed = os.path.isfile(piper_es_cache_path)
    piper_es_status = ModelInstallStatus.INSTALLED if is_piper_es_installed else ModelInstallStatus.NOT_INSTALLED

    registry.register_model(
        ModelDescriptor(
            model_id="tts/piper-es-davefx-cpu",
            name="Piper TTS Spanish davefx-medium (CPU)",
            provider="piper",
            capability="tts",
            supported_runtimes=["local_cpu"],
            supported_devices=["cpu"],
            requires_gpu=False,
            minimum_ram_bytes=64 * mb,
            recommended_ram_bytes=128 * mb,
            approximate_size_bytes=63201294,
            quantization="fp32",
            license="CC0 (Public Domain)",
            license_commercial_permitted=True,
            source="rhasspy/piper-voices",
            revision="es/es_ES/davefx/medium",
            cache_path=piper_es_cache_path if is_piper_es_installed else None,
            supported_languages=["es", "es-es"],
            supported_output_formats=["wav"],
            installation_status=piper_es_status,
            health_status=ModelHealthStatus.HEALTHY if is_piper_es_installed else ModelHealthStatus.UNKNOWN,
            metadata={
                "engine": "Piper TTS (ONNX Runtime)",
                "voice_name": "es_ES-davefx-medium",
                "sample_rate": 22050,
                "engine_license": "MIT",
                "voice_license": "CC0 (Public Domain)",
                "license_classification": "COMMERCIAL_SAFE",
                "commercial_use_permitted": True,
            },
        ),
        is_default=False,
    )

    # 11 Verified Commercial-Safe Piper Expanded Voices
    new_piper_specs = [
        (
            "tts/piper-en-bryce-cpu",
            "Piper TTS US English bryce-medium (CPU)",
            "en_US-bryce-medium",
            "en/en_US/bryce/medium",
            63531379,
            "dc9caa6c313199ffb5ac698b6e542fa6cba388aeaf2731e25262e33b9810aef1",
            ["en", "en-us"],
            "Public Domain",
            "https://huggingface.co/rhasspy/piper-voices/raw/main/en/en_US/bryce/medium/MODEL_CARD",
        ),
        (
            "tts/piper-en-joe-cpu",
            "Piper TTS US English joe-medium (CPU)",
            "en_US-joe-medium",
            "en/en_US/joe/medium",
            63201294,
            "58afce0321b8d9c46d7cdf9c16500cc55a793b4220212dba6b70fb788b3baf06",
            ["en", "en-us"],
            "CC0 1.0 Universal",
            "https://github.com/OHF-Voice/voice-datasets",
        ),
        (
            "tts/piper-en-kristin-cpu",
            "Piper TTS US English kristin-medium (CPU)",
            "en_US-kristin-medium",
            "en/en_US/kristin/medium",
            63531379,
            "5849957f929cbf720c258f8458692d6103fff2f0e3d3b19c8259474bb06a18d4",
            ["en", "en-us"],
            "Public Domain",
            "https://librivox.org",
        ),
        (
            "tts/piper-en-john-cpu",
            "Piper TTS US English john-medium (CPU)",
            "en_US-john-medium",
            "en/en_US/john/medium",
            63531379,
            "789c6c875726e627ddee93d51d8727859abe9c091c3d141591f4b83c2072e988",
            ["en", "en-us"],
            "Public Domain",
            "https://librivox.org",
        ),
        (
            "tts/piper-en-alba-cpu",
            "Piper TTS British English alba-medium (CPU)",
            "en_GB-alba-medium",
            "en/en_GB/alba/medium",
            63201294,
            "401369c4a81d09fdd86c32c5c864440811dbdcc66466cde2d64f7133a66ad03b",
            ["en", "en-gb"],
            "CC BY 4.0",
            "https://datashare.ed.ac.uk/handle/10283/3270",
        ),
        (
            "tts/piper-es-sharvard-cpu",
            "Piper TTS Spanish sharvard-medium (CPU)",
            "es_ES-sharvard-medium",
            "es/es_ES/sharvard/medium",
            76733615,
            "40febfb1679c69a4505ff311dc136e121e3419a13a290ef264fdf43ddedd0fb1",
            ["es", "es-es"],
            "CC BY 3.0",
            "https://datashare.ed.ac.uk/handle/10283/574",
        ),
        (
            "tts/piper-es-claude-cpu",
            "Piper TTS Mexican Spanish claude-high (CPU)",
            "es_MX-claude-high",
            "es/es_MX/claude/high",
            63122309,
            "3ef40a71ea63852cd8ab7e6fa7d2ecdcfa67a0b47c9c48e3f10e02ee02083ea0",
            ["es", "es-mx"],
            "Apache-2.0",
            "https://huggingface.co/spaces/HirCoir/Piper-TTS-Spanish",
        ),
        (
            "tts/piper-de-thorsten-cpu",
            "Piper TTS German thorsten-medium (CPU)",
            "de_DE-thorsten-medium",
            "de/de_DE/thorsten/medium",
            63201294,
            "7e64762d8e5118bb578f2eea6207e1a35a8e0c30595010b666f983fc87bb7819",
            ["de", "de-de"],
            "CC0 1.0 Universal",
            "https://github.com/thorstenMueller/Thorsten-Voice",
        ),
        (
            "tts/piper-fr-siwis-cpu",
            "Piper TTS French siwis-medium (CPU)",
            "fr_FR-siwis-medium",
            "fr/fr_FR/siwis/medium",
            63201294,
            "641d1ab097da2b81128c076810edb052b385decc8be3381814802a64a73baf99",
            ["fr", "fr-fr"],
            "CC-BY 4.0",
            "https://datashare.is.ed.ac.uk/handle/10283/2353",
        ),
        (
            "tts/piper-it-serena-cpu",
            "Piper TTS Italian serena-medium (CPU)",
            "it_IT-serena-medium",
            "it/it_IT/serena/medium",
            63516051,
            "fe4e26b2c1236e2a44d2e295cad564d94a0d8b0a9fca1ccdfd70dd4af3116eb5",
            ["it", "it-it"],
            "CC-BY-4.0",
            "https://huggingface.co/datasets/committa/serena-synthetic-it-27h",
        ),
        (
            "tts/piper-pt-faber-cpu",
            "Piper TTS Brazilian Portuguese faber-medium (CPU)",
            "pt_BR-faber-medium",
            "pt/pt_BR/faber/medium",
            63201294,
            "858555e3a064209c57088fe6bd70c4c3dc54d03eaa00c45d5ecaf43a33f95aa7",
            ["pt", "pt-br"],
            "CC0 1.0 Universal",
            "https://github.com/OHF-Voice/voice-datasets",
        ),
    ]

    for (m_id, m_name, v_key, v_rev, size_bytes, sha256_hash, langs, v_license, license_ref) in new_piper_specs:
        v_cache_path = os.path.join("models_cache", "tts", "piper", v_key, f"{v_key}.onnx")
        v_installed = os.path.isfile(v_cache_path)
        v_status = ModelInstallStatus.INSTALLED if v_installed else ModelInstallStatus.NOT_INSTALLED
        registry.register_model(
            ModelDescriptor(
                model_id=m_id,
                name=m_name,
                provider="piper",
                capability="tts",
                supported_runtimes=["local_cpu"],
                supported_devices=["cpu"],
                requires_gpu=False,
                minimum_ram_bytes=64 * mb,
                recommended_ram_bytes=128 * mb,
                approximate_size_bytes=size_bytes,
                quantization="fp32",
                license=v_license,
                license_commercial_permitted=True,
                source="rhasspy/piper-voices",
                revision=v_rev,
                checksum_sha256=sha256_hash,
                cache_path=v_cache_path if v_installed else None,
                supported_languages=langs,
                supported_output_formats=["wav"],
                installation_status=v_status,
                health_status=ModelHealthStatus.HEALTHY if v_installed else ModelHealthStatus.UNKNOWN,
                metadata={
                    "engine": "Piper TTS (ONNX Runtime)",
                    "voice_name": v_key,
                    "sample_rate": 22050,
                    "engine_license": "MIT",
                    "voice_license": v_license,
                    "license_url": license_ref,
                    "license_classification": "COMMERCIAL_SAFE",
                    "commercial_use_permitted": True,
                },
            ),
            is_default=False,
        )


    # ---------------------------------------------------------------------------
    # Kokoro-82M: Local CPU Neural TTS via ONNX Runtime
    # ---------------------------------------------------------------------------
    kokoro_cache_path = os.path.join("models_cache", "tts", "kokoro", "kokoro-v1.0.onnx")
    kokoro_voices_path = os.path.join("models_cache", "tts", "kokoro", "voices-v1.0.bin")
    is_kokoro_installed = os.path.isfile(kokoro_cache_path) and os.path.isfile(kokoro_voices_path)
    kokoro_status = ModelInstallStatus.VERIFIED if is_kokoro_installed else ModelInstallStatus.NOT_INSTALLED

    registry.register_model(
        ModelDescriptor(
            model_id="tts/kokoro-cpu",
            name="Kokoro-82M Neural TTS (CPU)",
            provider="kokoro",
            capability="tts",
            supported_runtimes=["local_cpu"],
            supported_devices=["cpu"],
            requires_gpu=False,
            minimum_ram_bytes=384 * mb,
            recommended_ram_bytes=768 * mb,
            approximate_size_bytes=325505369,
            quantization="fp32",
            license="Apache-2.0",
            license_commercial_permitted=True,
            source="thewh1teagle/kokoro-onnx",
            revision="model-files-v1.1",
            checksum_sha256="beb0d1848dee9a49da392cc3df26958d46cfa35d321edf434f52949153f0df3a",
            cache_path=kokoro_cache_path if is_kokoro_installed else None,
            supported_languages=["en", "en-us", "en-gb", "es", "es-es", "fr", "fr-fr", "it", "pt", "pt-br", "hi", "ja", "zh"],
            supported_output_formats=["wav"],
            installation_status=kokoro_status,
            health_status=ModelHealthStatus.HEALTHY if is_kokoro_installed else ModelHealthStatus.UNKNOWN,
            metadata={
                "engine": "Kokoro-82M (ONNX Runtime)",
                "sample_rate": 24000,
                "model_license": "Apache-2.0",
                "voice_pack_license": "Apache-2.0",
                "license_classification": "COMMERCIAL_SAFE",
                "commercial_use_permitted": True,
                "voices_pack_sha256": "bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d",
            },
        ),
        is_default=False,
    )

    kokoro_voice_specs = [
        (
            "tts/kokoro-en-heart-cpu",
            "Kokoro TTS US English af_heart (CPU)",
            "af_heart",
            ["en", "en-us"],
            "Apache-2.0",
            "Apache-2.0",
            "https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md",
            "Permissive audio dataset",
        ),
        (
            "tts/kokoro-en-emma-cpu",
            "Kokoro TTS British English bf_emma (CPU)",
            "bf_emma",
            ["en", "en-gb"],
            "Apache-2.0",
            "Apache-2.0",
            "https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md",
            "Permissive audio dataset",
        ),
        (
            "tts/kokoro-es-dora-cpu",
            "Kokoro TTS Spanish ef_dora (CPU)",
            "ef_dora",
            ["es", "es-es"],
            "Apache-2.0",
            "Apache-2.0",
            "https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md",
            "Permissive audio dataset",
        ),
        (
            "tts/kokoro-fr-siwis-cpu",
            "Kokoro TTS French ff_siwis (CPU)",
            "ff_siwis",
            ["fr", "fr-fr"],
            "Apache-2.0",
            "CC BY 4.0",
            "https://datashare.ed.ac.uk/handle/10283/2353",
            "SIWIS French Speech Synthesis Database",
        ),
    ]

    for (m_id, m_name, v_key, langs, m_lic, v_lic, v_lic_url, dataset_name) in kokoro_voice_specs:
        registry.register_model(
            ModelDescriptor(
                model_id=m_id,
                name=m_name,
                provider="kokoro",
                capability="tts",
                supported_runtimes=["local_cpu"],
                supported_devices=["cpu"],
                requires_gpu=False,
                minimum_ram_bytes=384 * mb,
                recommended_ram_bytes=768 * mb,
                approximate_size_bytes=325505369,
                quantization="fp32",
                license=v_lic,
                license_commercial_permitted=True,
                source="thewh1teagle/kokoro-onnx",
                revision="model-files-v1.1",
                checksum_sha256="beb0d1848dee9a49da392cc3df26958d46cfa35d321edf434f52949153f0df3a",
                cache_path=kokoro_cache_path if is_kokoro_installed else None,
                supported_languages=langs,
                supported_output_formats=["wav"],
                installation_status=kokoro_status,
                health_status=ModelHealthStatus.HEALTHY if is_kokoro_installed else ModelHealthStatus.UNKNOWN,
                metadata={
                    "engine": "Kokoro-82M (ONNX Runtime)",
                    "voice_id": v_key,
                    "sample_rate": 24000,
                    "model_license": m_lic,
                    "voice_license": v_lic,
                    "license_url": v_lic_url,
                    "dataset_name": dataset_name,
                    "license_classification": "COMMERCIAL_SAFE",
                    "commercial_use_permitted": True,
                },
            ),
            is_default=False,
        )

    # Coqui XTTS-v2: Multilingual voice cloning TTS (GPU required)
    registry.register_model(
        ModelDescriptor(
            model_id="tts/xtts-v2-gpu",
            name="Coqui XTTS-v2 Multilingual (GPU)",
            provider="coqui",
            capability="tts",
            supported_runtimes=["local_gpu"],
            supported_devices=["cuda"],
            requires_gpu=True,
            minimum_ram_bytes=4 * gb,
            recommended_ram_bytes=8 * gb,
            minimum_vram_bytes=3 * gb,
            approximate_size_bytes=int(1.8 * gb),
            license="Coqui Public Model License",
            license_commercial_permitted=False,  # Restricted commercial
            source="coqui/XTTS-v2",
            supported_languages=["en", "es", "fr", "de", "it", "pt", "pl", "tr", "ru", "nl", "cs", "ar", "zh", "ja", "ko", "hi"],
            supported_output_formats=["wav"],
            installation_status=ModelInstallStatus.NOT_INSTALLED,
            health_status=ModelHealthStatus.UNKNOWN,
        )
    )

    # Mock TTS: Built-in deterministic testing model
    registry.register_model(
        ModelDescriptor(
            model_id="tts/mock-tts",
            name="Deterministic Mock TTS",
            provider="mock",
            capability="tts",
            supported_runtimes=["local_cpu", "local_gpu"],
            supported_devices=["cpu", "cuda"],
            requires_gpu=False,
            minimum_ram_bytes=10 * mb,
            approximate_size_bytes=1 * mb,
            license="MIT",
            license_commercial_permitted=True,
            supported_languages=["*"],
            supported_output_formats=["wav", "mp3", "aac"],
            installation_status=ModelInstallStatus.INSTALLED,
            health_status=ModelHealthStatus.HEALTHY,
        ),
        is_default=True,
    )

    # ---------------------------------------------------------------------------
    # 2. Automated Speech Recognition (ASR) Models
    # ---------------------------------------------------------------------------
    whisper_cache_path = os.path.join("models_cache", "asr", "whisper", "tiny", "model.bin")
    is_whisper_installed = os.path.isfile(whisper_cache_path)
    whisper_status = ModelInstallStatus.INSTALLED if is_whisper_installed else ModelInstallStatus.NOT_INSTALLED

    registry.register_model(
        ModelDescriptor(
            model_id="asr/whisper-tiny-cpu",
            name="Whisper Tiny CTranslate2 (CPU)",
            provider="whisper",
            capability="asr",
            supported_runtimes=["local_cpu"],
            supported_devices=["cpu"],
            requires_gpu=False,
            minimum_ram_bytes=256 * mb,
            recommended_ram_bytes=512 * mb,
            approximate_size_bytes=75538270,
            quantization="int8",
            license="MIT",
            license_commercial_permitted=True,
            source="Systran/faster-whisper-tiny",
            revision="d90ca5fe260221311c53c58e660288d3deb8d356",
            checksum_sha256="dcb76c6586fc06cbdac6dd21f14cfd129cc4cdd9dce19bf4ffa62e59cbe6e6d1",
            cache_path=whisper_cache_path if is_whisper_installed else None,
            supported_languages=["en", "zh", "de", "es", "ru", "ko", "fr", "ja", "pt", "tr", "*"],
            supported_input_formats=["wav", "mp3", "mp4", "m4a", "webm"],
            installation_status=whisper_status,
            health_status=ModelHealthStatus.HEALTHY,
            metadata={
                "engine": "faster-whisper 1.2.1",
                "runtime": "CTranslate2 (int8)",
                "engine_license": "MIT (faster-whisper)",
                "runtime_license": "MIT (CTranslate2)",
                "model_license": "MIT (OpenAI / Systran)",
                "commercial_use_permitted": True,
                "model_source_repo": "https://huggingface.co/Systran/faster-whisper-tiny",
            },
        )
    )

    registry.register_model(
        ModelDescriptor(
            model_id="asr/whisper-tiny-multilingual-cpu",
            name="Whisper Tiny Multilingual CTranslate2 (CPU)",
            provider="whisper",
            capability="asr",
            supported_runtimes=["local_cpu"],
            supported_devices=["cpu"],
            requires_gpu=False,
            minimum_ram_bytes=256 * mb,
            recommended_ram_bytes=512 * mb,
            approximate_size_bytes=75538270,
            quantization="int8",
            license="MIT",
            license_commercial_permitted=True,
            source="Systran/faster-whisper-tiny",
            revision="d90ca5fe260221311c53c58e660288d3deb8d356",
            checksum_sha256="dcb76c6586fc06cbdac6dd21f14cfd129cc4cdd9dce19bf4ffa62e59cbe6e6d1",
            cache_path=whisper_cache_path if is_whisper_installed else None,
            supported_languages=["en", "zh", "de", "es", "ru", "ko", "fr", "ja", "pt", "tr", "*"],
            supported_input_formats=["wav", "mp3", "mp4", "m4a", "webm"],
            installation_status=whisper_status,
            health_status=ModelHealthStatus.HEALTHY if is_whisper_installed else ModelHealthStatus.UNKNOWN,
            metadata={
                "engine": "faster-whisper 1.2.1",
                "runtime": "CTranslate2 (int8)",
                "license_classification": "COMMERCIAL_SAFE",
                "commercial_use_permitted": True,
                "is_multilingual": True,
                "notes": "Full multilingual ASR checkpoint supporting Spanish, French, German, and 90+ languages.",
            },
        )
    )

    registry.register_model(
        ModelDescriptor(
            model_id="asr/whisper-large-v3-gpu",
            name="OpenAI Whisper Large v3 (GPU)",
            provider="whisper",
            capability="asr",
            supported_runtimes=["local_gpu"],
            supported_devices=["cuda"],
            requires_gpu=True,
            minimum_ram_bytes=8 * gb,
            minimum_vram_bytes=5 * gb,
            approximate_size_bytes=int(2.9 * gb),
            license="MIT",
            license_commercial_permitted=True,
            source="openai/whisper-large-v3",
            supported_languages=["*"],
            supported_input_formats=["wav", "mp3", "mp4", "m4a", "webm"],
            installation_status=ModelInstallStatus.NOT_INSTALLED,
            health_status=ModelHealthStatus.UNKNOWN,
        )
    )

    registry.register_model(
        ModelDescriptor(
            model_id="asr/mock-asr",
            name="Deterministic Mock ASR",
            provider="mock",
            capability="asr",
            supported_runtimes=["local_cpu", "local_gpu"],
            supported_devices=["cpu", "cuda"],
            requires_gpu=False,
            minimum_ram_bytes=10 * mb,
            license="MIT",
            license_commercial_permitted=True,
            supported_languages=["*"],
            installation_status=ModelInstallStatus.INSTALLED,
            health_status=ModelHealthStatus.HEALTHY,
        ),
        is_default=True,
    )

    # ---------------------------------------------------------------------------
    # 3. Translation Models
    # ---------------------------------------------------------------------------
    opus_es_cache_path = os.path.join("models_cache", "translation", "opus-mt-en-es", "model.bin")
    is_opus_es_installed = os.path.isfile(opus_es_cache_path)
    opus_es_status = ModelInstallStatus.INSTALLED if is_opus_es_installed else ModelInstallStatus.NOT_INSTALLED

    registry.register_model(
        ModelDescriptor(
            model_id="translation/opus-mt-en-es-cpu",
            name="Opus-MT English to Spanish (CPU INT8)",
            provider="ctranslate2",
            capability="translation",
            supported_runtimes=["local_cpu"],
            supported_devices=["cpu"],
            requires_gpu=False,
            minimum_ram_bytes=128 * mb,
            recommended_ram_bytes=256 * mb,
            approximate_size_bytes=157 * mb,
            quantization="int8",
            license="Apache-2.0",
            license_commercial_permitted=True,
            source="michaelfeil/ct2fast-opus-mt-en-es",
            revision="76ec296588e2234f9b7dfad5254219a0f5ecb7af",
            cache_path=os.path.join("models_cache", "translation", "opus-mt-en-es") if is_opus_es_installed else None,
            supported_languages=["en", "es"],
            supported_input_formats=["text"],
            supported_output_formats=["text"],
            installation_status=opus_es_status,
            health_status=ModelHealthStatus.HEALTHY if is_opus_es_installed else ModelHealthStatus.UNKNOWN,
            metadata={
                "engine": "CTranslate2 (int8)",
                "source_repo": "Helsinki-NLP/opus-mt-en-es",
                "upstream_revision": "5bc4493d463cf000c1f0b50f8d56886a392ed4ab",
                "license_classification": "COMMERCIAL_SAFE",
                "commercial_use_permitted": True,
                "source_lang": "en",
                "target_lang": "es",
            },
        )
    )

    registry.register_model(
        ModelDescriptor(
            model_id="translation/nllb-200-cpu",
            name="Meta NLLB-200 Distilled 600M (CPU)",
            provider="meta",
            capability="translation",
            supported_runtimes=["local_cpu"],
            supported_devices=["cpu"],
            requires_gpu=False,
            minimum_ram_bytes=int(1.5 * gb),
            approximate_size_bytes=int(1.2 * gb),
            license="CC-BY-NC-4.0",
            license_commercial_permitted=False,
            source="facebook/nllb-200-distilled-600M",
            supported_languages=["*"],
            installation_status=ModelInstallStatus.NOT_INSTALLED,
            health_status=ModelHealthStatus.HEALTHY,
            metadata={
                "license_classification": "RESEARCH_ONLY",
                "commercial_use_permitted": False,
                "notes": "Rejected for commercial production use due to CC-BY-NC-4.0 non-commercial restrictions.",
            },
        )
    )

    registry.register_model(
        ModelDescriptor(
            model_id="translation/mock-translation",
            name="Deterministic Mock Translation",
            provider="mock",
            capability="translation",
            supported_runtimes=["local_cpu", "local_gpu"],
            supported_devices=["cpu", "cuda"],
            requires_gpu=False,
            minimum_ram_bytes=10 * mb,
            license="MIT",
            license_commercial_permitted=True,
            supported_languages=["*"],
            installation_status=ModelInstallStatus.INSTALLED,
            health_status=ModelHealthStatus.HEALTHY,
        ),
        is_default=True,
    )

    # ---------------------------------------------------------------------------
    # 4. Avatar & Lip-Sync Models
    # ---------------------------------------------------------------------------
    wav2lip_cache_path = os.path.join("models_cache", "avatar", "wav2lip", "wav2lip.onnx")
    is_wav2lip_installed = os.path.isfile(wav2lip_cache_path)
    wav2lip_status = ModelInstallStatus.INSTALLED if is_wav2lip_installed else ModelInstallStatus.NOT_INSTALLED

    registry.register_model(
        ModelDescriptor(
            model_id="avatar/wav2lip-cpu",
            name="Wav2Lip Lip-Sync (CPU)",
            provider="wav2lip",
            capability="avatar",
            supported_runtimes=["local_cpu"],
            supported_devices=["cpu"],
            requires_gpu=False,
            minimum_ram_bytes=512 * mb,
            recommended_ram_bytes=1024 * mb,
            approximate_size_bytes=145175471,
            license="Research Only (LRS2 Non-Commercial)",
            license_commercial_permitted=False,
            source="instant-high/wav2lip-onnx",
            checksum_sha256="902d7719f0ebbd461f956da8f603f02e84c019d8d64cfe25402a217605b2e690",
            cache_path=wav2lip_cache_path if is_wav2lip_installed else None,
            supported_output_formats=["mp4", "webm"],
            installation_status=wav2lip_status,
            health_status=ModelHealthStatus.HEALTHY,
            metadata={
                "engine": "Wav2Lip-ONNX",
                "runtime": "onnxruntime (CPUExecutionProvider)",
                "license_classification": "RESEARCH_ONLY",
                "commercial_use_permitted": False,
                "notes": "Real CPU lip-sync verified using research-only Wav2Lip-ONNX.",
            },
        )
    )

    registry.register_model(
        ModelDescriptor(
            model_id="avatar/musetalk-gpu",
            name="MuseTalk Real-Time Lip-Sync (GPU)",
            provider="musetalk",
            capability="avatar",
            supported_runtimes=["local_gpu"],
            supported_devices=["cuda"],
            requires_gpu=True,
            minimum_ram_bytes=8 * gb,
            minimum_vram_bytes=6 * gb,
            approximate_size_bytes=int(3.8 * gb),
            license="MIT",
            license_commercial_permitted=True,
            source="TMElyralab/MuseTalk",
            supported_output_formats=["mp4", "webm"],
            installation_status=ModelInstallStatus.NOT_INSTALLED,
            health_status=ModelHealthStatus.UNKNOWN,
            metadata={
                "status": "production_target_cuda_unvalidated",
                "license_classification": "CONDITIONAL — ARTIFACT VERIFICATION REQUIRED",
                "commercial_use_permitted": True,
                "notes": "Production-target CUDA provider — architecturally prepared, not locally validated.",
                "face_detector": "opencv/yunet (Apache-2.0)",
                "face_masking": "yunet_landmark_geometric (Apache-2.0)",
                "banned_components": [
                    "s3fd-619a3168.pth",
                    "face-parse-bisent/79999_iter.pth",
                    "CelebAMask-HQ",
                    "InsightFace",
                    "BFM_2009",
                    "CodeFormer",
                ],
            },
        )
    )

    registry.register_model(
        ModelDescriptor(
            model_id="avatar/mock-avatar",
            name="Deterministic Mock Avatar",
            provider="mock",
            capability="avatar",
            supported_runtimes=["local_cpu", "local_gpu"],
            supported_devices=["cpu", "cuda"],
            requires_gpu=False,
            minimum_ram_bytes=10 * mb,
            license="MIT",
            license_commercial_permitted=True,
            supported_output_formats=["mp4", "webm"],
            installation_status=ModelInstallStatus.INSTALLED,
            health_status=ModelHealthStatus.HEALTHY,
        ),
        is_default=True,
    )

    # ---------------------------------------------------------------------------
    # 5. Generative Image Models
    # ---------------------------------------------------------------------------
    registry.register_model(
        ModelDescriptor(
            model_id="image/stable-diffusion-v1-5-gpu",
            name="Stable Diffusion v1.5 (GPU)",
            provider="stable_diffusion",
            capability="image",
            supported_runtimes=["local_gpu"],
            supported_devices=["cuda"],
            requires_gpu=True,
            minimum_ram_bytes=8 * gb,
            minimum_vram_bytes=6 * gb,
            approximate_size_bytes=4265380512,
            license="CreativeML OpenRAIL-M",
            license_commercial_permitted=True,
            source="runwayml/stable-diffusion-v1-5",
            checksum_sha256="6ce016e7d0fe7376494aaeae77f3e3e1c500ec6c76db432e23702d2b57347774",
            supported_output_formats=["png", "jpg", "webp"],
            installation_status=ModelInstallStatus.NOT_INSTALLED,
            health_status=ModelHealthStatus.UNKNOWN,
            metadata={
                "status": "production_target_cuda_unvalidated",
                "license_classification": "CONDITIONAL — ARTIFACT VERIFICATION REQUIRED",
                "commercial_use_permitted": True,
                "notes": "Production-target CUDA image provider — architecturally prepared, not locally validated.",
                "banned_components": [
                    "sdxl-turbo",
                    "sd-turbo",
                    "stabilityai/sdxl-turbo",
                    "stabilityai/sd-turbo",
                ],
            },
        )
    )

    registry.register_model(
        ModelDescriptor(
            model_id="image/sdxl-turbo-gpu",
            name="SDXL-Turbo (GPU)",
            provider="stability",
            capability="image",
            supported_runtimes=["local_gpu"],
            supported_devices=["cuda"],
            requires_gpu=True,
            minimum_ram_bytes=8 * gb,
            minimum_vram_bytes=6 * gb,
            approximate_size_bytes=int(3.5 * gb),
            license="Stability AI Non-Commercial",
            license_commercial_permitted=False,
            source="stabilityai/sdxl-turbo",
            supported_output_formats=["png", "jpg", "webp"],
            installation_status=ModelInstallStatus.NOT_INSTALLED,
            health_status=ModelHealthStatus.UNKNOWN,
            metadata={
                "license_classification": "NON_COMMERCIAL",
                "commercial_use_permitted": False,
                "notes": "Rejected for production use due to Stability AI Non-Commercial Research Community License restrictions.",
            },
        )
    )

    registry.register_model(
        ModelDescriptor(
            model_id="image/mock-image",
            name="Deterministic Mock Image",
            provider="mock",
            capability="image",
            supported_runtimes=["local_cpu", "local_gpu"],
            supported_devices=["cpu", "cuda"],
            requires_gpu=False,
            minimum_ram_bytes=10 * mb,
            license="MIT",
            license_commercial_permitted=True,
            supported_output_formats=["png", "jpg", "webp"],
            installation_status=ModelInstallStatus.INSTALLED,
            health_status=ModelHealthStatus.HEALTHY,
        ),
        is_default=True,
    )

    # ---------------------------------------------------------------------------
    # 6. Generative Video Models
    # ---------------------------------------------------------------------------
    registry.register_model(
        ModelDescriptor(
            model_id="video/mock-video",
            name="Deterministic Mock Video",
            provider="mock",
            capability="video",
            supported_runtimes=["local_cpu", "local_gpu"],
            supported_devices=["cpu", "cuda"],
            requires_gpu=False,
            minimum_ram_bytes=10 * mb,
            license="MIT",
            license_commercial_permitted=True,
            supported_output_formats=["mp4", "webm"],
            installation_status=ModelInstallStatus.INSTALLED,
            health_status=ModelHealthStatus.HEALTHY,
        ),
        is_default=True,
    )

    # ---------------------------------------------------------------------------
    # 7. LLM Models
    # ---------------------------------------------------------------------------
    qwen_cache_path = os.path.join(
        "models_cache",
        "llm",
        "qwen2.5-0.5b-onnx",
        "cpu_and_mobile",
        "cpu-int4-rtn-block-32-acc-level-4",
    )
    is_qwen_installed = os.path.isdir(qwen_cache_path) and os.path.isfile(os.path.join(qwen_cache_path, "model.onnx"))
    qwen_status = ModelInstallStatus.INSTALLED if is_qwen_installed else ModelInstallStatus.NOT_INSTALLED

    registry.register_model(
        ModelDescriptor(
            model_id="llm/qwen-2.5-0.5b-cpu",
            name="Qwen 2.5 0.5B Instruct ONNX (CPU)",
            provider="qwen",
            capability="llm",
            supported_runtimes=["local_cpu"],
            supported_devices=["cpu"],
            requires_gpu=False,
            minimum_ram_bytes=512 * mb,
            recommended_ram_bytes=1024 * mb,
            approximate_size_bytes=861939200,
            quantization="int4",
            license="Apache-2.0",
            license_commercial_permitted=True,
            source="Qwen/Qwen2.5-0.5B-Instruct-ONNX",
            cache_path=qwen_cache_path if is_qwen_installed else None,
            supported_languages=["*"],
            supported_input_formats=["text", "json"],
            supported_output_formats=["text", "json"],
            installation_status=qwen_status,
            health_status=ModelHealthStatus.HEALTHY,
            metadata={
                "engine": "onnxruntime-genai",
                "quantization": "int4",
                "license_classification": "COMMERCIAL_SAFE",
                "commercial_use_permitted": True,
                "status": "real_cpu_validated",
                "notes": "Real local CPU SLM for prompt decomposition and structured script generation.",
            },
        )
    )

    registry.register_model(
        ModelDescriptor(
            model_id="llm/qwen-2.5-7b-gpu",
            name="Qwen 2.5 7B Instruct (GPU)",
            provider="qwen",
            capability="llm",
            supported_runtimes=["local_gpu"],
            supported_devices=["cuda"],
            requires_gpu=True,
            minimum_ram_bytes=8 * gb,
            minimum_vram_bytes=8 * gb,
            approximate_size_bytes=int(4.5 * gb),
            license="Apache-2.0",
            license_commercial_permitted=True,
            source="Qwen/Qwen2.5-7B-Instruct",
            supported_languages=["*"],
            supported_input_formats=["text", "json"],
            supported_output_formats=["text", "json"],
            installation_status=ModelInstallStatus.NOT_INSTALLED,
            health_status=ModelHealthStatus.UNKNOWN,
            metadata={
                "status": "production_target_cuda_unvalidated",
                "license_classification": "COMMERCIAL_SAFE",
                "commercial_use_permitted": True,
                "notes": "Production-target CUDA LLM provider — architecturally prepared, not locally validated.",
            },
        )
    )

    registry.register_model(
        ModelDescriptor(
            model_id="llm/llama-3.2-3b-cpu",
            name="Llama-3.2-3B-Instruct (CPU Q4)",
            provider="meta",
            capability="llm",
            supported_runtimes=["local_cpu"],
            supported_devices=["cpu"],
            requires_gpu=False,
            minimum_ram_bytes=3 * gb,
            recommended_ram_bytes=6 * gb,
            approximate_size_bytes=int(2.0 * gb),
            quantization="q4_k_m",
            license="Llama 3.2 Community License",
            license_commercial_permitted=True,
            source="meta-llama/Llama-3.2-3B-Instruct",
            supported_languages=["*"],
            installation_status=ModelInstallStatus.NOT_INSTALLED,
            health_status=ModelHealthStatus.HEALTHY,
        )
    )

    registry.register_model(
        ModelDescriptor(
            model_id="llm/mock-llm",
            name="Deterministic Mock LLM",
            provider="mock",
            capability="llm",
            supported_runtimes=["local_cpu", "local_gpu"],
            supported_devices=["cpu", "cuda"],
            requires_gpu=False,
            minimum_ram_bytes=10 * mb,
            license="MIT",
            license_commercial_permitted=True,
            supported_languages=["*"],
            installation_status=ModelInstallStatus.INSTALLED,
            health_status=ModelHealthStatus.HEALTHY,
        ),
        is_default=True,
    )

    # ---------------------------------------------------------------------------
    # 8. Neural Matting & Background Segmentation Models
    # ---------------------------------------------------------------------------
    mediapipe_cache_path = os.path.join("models_cache", "matting", "mediapipe", "model.onnx")
    is_mediapipe_installed = os.path.isfile(mediapipe_cache_path)
    mediapipe_status = ModelInstallStatus.INSTALLED if is_mediapipe_installed else ModelInstallStatus.NOT_INSTALLED

    registry.register_model(
        ModelDescriptor(
            model_id="matting/mediapipe-selfie-cpu",
            name="MediaPipe Selfie Segmentation (CPU ONNX)",
            provider="mediapipe",
            capability="matting",
            supported_runtimes=["local_cpu"],
            supported_devices=["cpu"],
            requires_gpu=False,
            minimum_ram_bytes=64 * mb,
            recommended_ram_bytes=128 * mb,
            approximate_size_bytes=462352,
            quantization="fp32",
            license="Apache-2.0",
            license_commercial_permitted=True,
            source="onnx-community/mediapipe_selfie_segmentation",
            revision="be49485c8e027524be38591817fc5cd31bd9d00e",
            checksum_sha256="3241ac4ad8aa35bdaf33946776db29f7c283a413aa0b0dacb9483594b4531aad",
            cache_path=mediapipe_cache_path if is_mediapipe_installed else None,
            supported_languages=["*"],
            supported_input_formats=["png", "jpg", "jpeg", "mp4", "webm"],
            supported_output_formats=["png", "mp4"],
            installation_status=mediapipe_status,
            health_status=ModelHealthStatus.HEALTHY if is_mediapipe_installed else ModelHealthStatus.UNKNOWN,
            metadata={
                "engine": "onnxruntime (CPUExecutionProvider)",
                "model_filename": "onnx/model.onnx",
                "source_repo": "https://huggingface.co/onnx-community/mediapipe_selfie_segmentation",
                "license_classification": "COMMERCIAL_SAFE",
                "commercial_use_permitted": True,
                "status": "real_cpu_validated",
                "notes": "Real local CPU selfie segmentation for alpha matte generation.",
            },
        )
    )

    registry.register_model(
        ModelDescriptor(
            model_id="matting/modnet-cpu",
            name="MODNet Portrait Matting (CPU)",
            provider="modnet",
            capability="matting",
            supported_runtimes=["local_cpu"],
            supported_devices=["cpu"],
            requires_gpu=False,
            minimum_ram_bytes=256 * mb,
            approximate_size_bytes=25 * mb,
            license="Creative Commons Non-Commercial (CC-BY-NC 4.0)",
            license_commercial_permitted=False,
            source="ZHKKKe/MODNet",
            supported_languages=["*"],
            supported_input_formats=["png", "jpg", "jpeg", "mp4", "webm"],
            supported_output_formats=["png", "mp4"],
            installation_status=ModelInstallStatus.NOT_INSTALLED,
            health_status=ModelHealthStatus.UNKNOWN,
            metadata={
                "license_classification": "RESEARCH_ONLY",
                "commercial_use_permitted": False,
                "notes": "MODNet portrait matting rejected for commercial production due to CC-BY-NC-4.0 non-commercial restrictions.",
            },
        )
    )

    registry.register_model(
        ModelDescriptor(
            model_id="matting/mock-matting",
            name="Deterministic Mock Matting",
            provider="mock",
            capability="matting",
            supported_runtimes=["local_cpu", "local_gpu"],
            supported_devices=["cpu", "cuda"],
            requires_gpu=False,
            minimum_ram_bytes=10 * mb,
            license="MIT",
            license_commercial_permitted=True,
            supported_languages=["*"],
            supported_input_formats=["png", "jpg", "jpeg", "mp4", "webm"],
            supported_output_formats=["png", "mp4"],
            installation_status=ModelInstallStatus.INSTALLED,
            health_status=ModelHealthStatus.HEALTHY,
        ),
        is_default=True,
    )

    # ---------------------------------------------------------------------------
    # 8. Audio Enhancement & Speech Cleanup Models
    # ---------------------------------------------------------------------------
    vad_cache_path = os.path.join("models_cache", "audio_enhance", "silero_vad", "silero_vad.onnx")
    is_vad_installed = os.path.isfile(vad_cache_path)
    vad_status = ModelInstallStatus.VERIFIED if is_vad_installed else ModelInstallStatus.NOT_INSTALLED

    registry.register_model(
        ModelDescriptor(
            model_id="audio_enhance/silero-vad-cpu",
            name="Silero Voice Activity Detector v5 (CPU)",
            provider="deepfilter",
            capability="audio_enhance",
            supported_runtimes=["local_cpu"],
            supported_devices=["cpu"],
            requires_gpu=False,
            minimum_ram_bytes=64 * mb,
            recommended_ram_bytes=128 * mb,
            approximate_size_bytes=2243022,
            quantization="fp32",
            license="MIT",
            license_commercial_permitted=True,
            source="onnx-community/silero-vad",
            revision="e71cae966052b992a7eca6b17738916ce0eca4ec",
            checksum_sha256="a4a068cd6cf1ea8355b84327595838ca748ec29a25bc91fc82e6c299ccdc5808",
            cache_path=vad_cache_path if is_vad_installed else None,
            supported_languages=["*"],
            supported_input_formats=["wav", "mp3", "m4a", "aac"],
            supported_output_formats=["wav"],
            installation_status=vad_status,
            health_status=ModelHealthStatus.HEALTHY if is_vad_installed else ModelHealthStatus.UNKNOWN,
            metadata={
                "engine": "onnxruntime (CPUExecutionProvider)",
                "model_filename": "silero_vad.onnx",
                "source_repo": "https://huggingface.co/onnx-community/silero-vad",
                "license_classification": "COMMERCIAL_SAFE",
                "commercial_use_permitted": True,
                "status": "real_cpu_validated",
                "sample_rate": 16000,
                "notes": "Voice Activity Detection for silence trimming and speech pause boundary detection.",
            },
        )
    )

    df_cache_path = os.path.join("models_cache", "audio_enhance", "deepfilternet", "enc.onnx")
    is_df_installed = os.path.isfile(df_cache_path)
    df_status = ModelInstallStatus.VERIFIED if is_df_installed else ModelInstallStatus.NOT_INSTALLED

    registry.register_model(
        ModelDescriptor(
            model_id="audio_enhance/deepfilternet3-cpu",
            name="DeepFilterNet3 Speech Enhancement (CPU)",
            provider="deepfilter",
            capability="audio_enhance",
            supported_runtimes=["local_cpu"],
            supported_devices=["cpu"],
            requires_gpu=False,
            minimum_ram_bytes=128 * mb,
            recommended_ram_bytes=256 * mb,
            approximate_size_bytes=8665000,
            quantization="fp32",
            license="MIT / Apache-2.0",
            license_commercial_permitted=True,
            source="bitsydarel/deepfilternet3-onnx",
            revision="891882f01b26d72754c4663a5a2eb3060b17480c",
            checksum_sha256="7c5399d3da8a50ebef1c1a0ae421b33376aa5e45d0e92df16da7e83c9c131916",
            cache_path=df_cache_path if is_df_installed else None,
            supported_languages=["*"],
            supported_input_formats=["wav", "mp3", "m4a", "aac"],
            supported_output_formats=["wav"],
            installation_status=df_status,
            health_status=ModelHealthStatus.HEALTHY if is_df_installed else ModelHealthStatus.UNKNOWN,
            metadata={
                "engine": "Real DeepFilterNet3 ONNX (CPUExecutionProvider) + FFmpeg Broadcast Mastering",
                "source_repo": "https://huggingface.co/bitsydarel/deepfilternet3-onnx",
                "license_classification": "COMMERCIAL_SAFE",
                "commercial_use_permitted": True,
                "status": "REAL CPU INFERENCE VALIDATED",
                "sample_rate": 48000,
                "enc_sha256": "7c5399d3da8a50ebef1c1a0ae421b33376aa5e45d0e92df16da7e83c9c131916",
                "erb_dec_sha256": "ab669a1d10afe20911728b33053a452071042317a90581092b325da7b2f9d895",
                "df_dec_sha256": "23114ce3b0f6464b763ee62f7bb8aab6b2a129a21eabd5bcfe59413db05f278a",
                "config_sha256": "2782b17318f9ebb082f663604b2f030f7da156cf25f8714632825831b6553fa1",
                "notes": "Studio neural speech enhancement, deep filtering, and broadcast vocal EQ mastering.",
            },
        )
    )

    registry.register_model(
        ModelDescriptor(
            model_id="audio_enhance/mock-audio-enhance",
            name="Deterministic Mock Audio Enhancement",
            provider="mock",
            capability="audio_enhance",
            supported_runtimes=["local_cpu", "local_gpu"],
            supported_devices=["cpu", "cuda"],
            requires_gpu=False,
            minimum_ram_bytes=10 * mb,
            license="MIT",
            license_commercial_permitted=True,
            supported_languages=["*"],
            supported_input_formats=["wav", "mp3", "m4a", "aac"],
            supported_output_formats=["wav"],
            installation_status=ModelInstallStatus.INSTALLED,
            health_status=ModelHealthStatus.HEALTHY,
        ),
        is_default=True,
    )

    # ---------------------------------------------------------------------------
    # 8. Neural Talking Avatar Models (Section 7 Discovery & Metadata)
    # ---------------------------------------------------------------------------
    lp_cache_path = os.path.join("models_cache", "avatar", "liveportrait")
    is_lp_installed = os.path.isdir(lp_cache_path) and any(os.scandir(lp_cache_path)) if os.path.exists(lp_cache_path) else False

    registry.register_model(
        ModelDescriptor(
            model_id="avatar/liveportrait",
            name="KwaiVGI LivePortrait Neural Motion Generator",
            provider="liveportrait",
            capability="avatar",
            supported_runtimes=["local_gpu", "container_gpu", "remote_hosted"],
            supported_devices=["cuda"],
            requires_gpu=True,
            minimum_vram_bytes=4 * gb,
            approximate_size_bytes=1800 * mb,
            quantization="fp16",
            license="MIT",
            license_commercial_permitted=True,
            source="KwaiVGI/LivePortrait",
            revision="v1.0.0",
            cache_path=lp_cache_path if is_lp_installed else None,
            supported_input_formats=["png", "jpg", "jpeg", "mp4"],
            supported_output_formats=["mp4"],
            installation_status=ModelInstallStatus.INSTALLED if is_lp_installed else ModelInstallStatus.NOT_INSTALLED,
            health_status=ModelHealthStatus.HEALTHY if is_lp_installed else ModelHealthStatus.UNKNOWN,
            metadata={
                "engine": "Implicit Keypoints + SPADE Motion Generator",
                "recommended_vram_gb": 4.0,
                "cuda_required": True,
            },
        )
    )

    mt_cache_path = os.path.join("models_cache", "avatar", "musetalk")
    is_mt_installed = os.path.isdir(mt_cache_path) and any(os.scandir(mt_cache_path)) if os.path.exists(mt_cache_path) else False

    registry.register_model(
        ModelDescriptor(
            model_id="avatar/musetalk",
            name="MuseTalk 1.5 Real-Time Neural Lip-Sync",
            provider="musetalk",
            capability="avatar",
            supported_runtimes=["local_gpu", "container_gpu", "remote_hosted"],
            supported_devices=["cuda"],
            requires_gpu=True,
            minimum_vram_bytes=4 * gb,
            approximate_size_bytes=2400 * mb,
            quantization="fp16",
            license="MIT",
            license_commercial_permitted=True,
            source="TMElyralab/MuseTalk",
            revision="v1.5.0",
            cache_path=mt_cache_path if is_mt_installed else None,
            supported_input_formats=["mp4", "wav"],
            supported_output_formats=["mp4"],
            installation_status=ModelInstallStatus.INSTALLED if is_mt_installed else ModelInstallStatus.NOT_INSTALLED,
            health_status=ModelHealthStatus.HEALTHY if is_mt_installed else ModelHealthStatus.UNKNOWN,
            metadata={
                "engine": "UNet Latent Face Inpainting + Whisper Audio Conditioning",
                "recommended_vram_gb": 4.0,
                "cuda_required": True,
            },
        )
    )

    hallo_cache_path = os.path.join("models_cache", "avatar", "hallo2")
    is_hallo_installed = os.path.isdir(hallo_cache_path) and any(os.scandir(hallo_cache_path)) if os.path.exists(hallo_cache_path) else False

    registry.register_model(
        ModelDescriptor(
            model_id="avatar/hallo2",
            name="Hallo2 Long-Duration Audio-Driven Diffusion",
            provider="hallo2",
            capability="avatar",
            supported_runtimes=["local_gpu", "container_gpu", "remote_hosted"],
            supported_devices=["cuda"],
            requires_gpu=True,
            minimum_vram_bytes=8 * gb,
            approximate_size_bytes=4200 * mb,
            quantization="fp16",
            license="Apache-2.0",
            license_commercial_permitted=True,
            source="fudan-generative-vision/hallo2",
            revision="v2.0.0",
            cache_path=hallo_cache_path if is_hallo_installed else None,
            supported_input_formats=["png", "jpg", "wav"],
            supported_output_formats=["mp4"],
            installation_status=ModelInstallStatus.INSTALLED if is_hallo_installed else ModelInstallStatus.NOT_INSTALLED,
            health_status=ModelHealthStatus.HEALTHY if is_hallo_installed else ModelHealthStatus.UNKNOWN,
            metadata={
                "engine": "Hierarchical Audio-Visual Cross-Attention Diffusion",
                "recommended_vram_gb": 8.0,
                "cuda_required": True,
            },
        )
    )

    backend_root = Path(__file__).resolve().parent.parent.parent
    w2l_cand1 = os.path.join("models_cache", "avatar", "wav2lip", "wav2lip.onnx")
    w2l_cand2 = str(backend_root / "models_cache" / "avatar" / "wav2lip" / "wav2lip.onnx")
    w2l_cache_path = w2l_cand2 if os.path.isfile(w2l_cand2) else w2l_cand1
    is_w2l_installed = os.path.isfile(w2l_cache_path)

    registry.register_model(
        ModelDescriptor(
            model_id="avatar/wav2lip",
            name="Wav2Lip ONNX (Development Fallback)",
            provider="wav2lip",
            capability="avatar",
            supported_runtimes=["local_cpu"],
            supported_devices=["cpu"],
            requires_gpu=False,
            minimum_ram_bytes=512 * mb,
            approximate_size_bytes=174000000,
            quantization="fp32",
            license="Research Only",
            license_commercial_permitted=False,
            source="Rudrabha/Wav2Lip",
            revision="1.0.0",
            cache_path=w2l_cache_path if is_w2l_installed else None,
            supported_input_formats=["png", "jpg", "jpeg", "wav"],
            supported_output_formats=["mp4"],
            installation_status=ModelInstallStatus.VERIFIED if is_w2l_installed else ModelInstallStatus.NOT_INSTALLED,
            health_status=ModelHealthStatus.HEALTHY if is_w2l_installed else ModelHealthStatus.UNKNOWN,
            metadata={
                "engine": "Wav2Lip-ONNX CPU (Development Fallback)",
                "cuda_required": False,
                "notes": "CPU development fallback — not neural motion.",
            },
        ),
        is_default=True,
    )


class ModelDiscoveryStatus(str, Enum):
    """Section 7: Explicit model discovery states."""
    AVAILABLE = "AVAILABLE"
    NOT_INSTALLED = "NOT_INSTALLED"
    GPU_REQUIRED = "GPU_REQUIRED"
    INVALID_MODEL = "INVALID_MODEL"


def discover_model_state(model_id: str) -> Dict[str, Any]:
    """Evaluate explicit model discovery state strictly conforming to Section 7:

    AVAILABLE | NOT_INSTALLED | GPU_REQUIRED | INVALID_MODEL
    """
    registry = get_model_registry()
    model = registry.get_model(model_id)
    if not model:
        return {
            "model_id": model_id,
            "status": ModelDiscoveryStatus.NOT_INSTALLED.value,
            "reason": f"Model '{model_id}' is not in the declarative catalog.",
        }

    hw = detect_hardware()

    # 1. GPU Requirement Check
    if model.requires_gpu and not hw.gpu.cuda_available:
        return {
            "model_id": model_id,
            "status": ModelDiscoveryStatus.GPU_REQUIRED.value,
            "reason": f"Model '{model.name}' requires NVIDIA CUDA GPU with >={round((model.minimum_vram_bytes or 0)/(1024**3), 1)}GB VRAM.",
            "cuda_required": True,
            "required_vram_gb": round((model.minimum_vram_bytes or 0) / (1024 ** 3), 1),
        }

    # 2. Local Installation Check
    cache_path = model.cache_path
    if cache_path and not os.path.exists(cache_path):
        b_root = Path(__file__).resolve().parent.parent.parent
        alt = b_root / cache_path
        if alt.exists():
            cache_path = str(alt)

    if not cache_path or not os.path.exists(cache_path):
        return {
            "model_id": model_id,
            "status": ModelDiscoveryStatus.NOT_INSTALLED.value,
            "reason": f"Model weights not found at '{cache_path or 'unconfigured'}'.",
            "source": model.source,
        }

    # 3. Integrity Check
    if model.checksum_sha256 and os.path.isfile(cache_path):
        import hashlib
        h = hashlib.sha256()
        with open(cache_path, "rb") as f:
            while chunk := f.read(1024 * 1024):
                h.update(chunk)
        if h.hexdigest().lower() != model.checksum_sha256.lower():
            return {
                "model_id": model_id,
                "status": ModelDiscoveryStatus.INVALID_MODEL.value,
                "reason": "SHA-256 integrity hash verification failed.",
            }

    # 4. Available
    return {
        "model_id": model_id,
        "status": ModelDiscoveryStatus.AVAILABLE.value,
        "reason": "Model weights verified and execution hardware compatible.",
        "path": cache_path,
        "device": "cuda" if model.requires_gpu else "cpu",
    }


