"""AI Provider Registry and Factory.

Decouples domain services from specific AI vendors and local neural network models.
Enforces interface protocol contracts and resolves providers deterministically.
"""

from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type, Union

from app.ai.capabilities import ProviderDescriptor
from app.ai.adapters.mock import (
    MockASRProvider,
    MockAudioEnhanceProvider,
    MockAvatarProvider,
    MockImageProvider,
    MockLLMProvider,
    MockMattingProvider,
    MockTranslationProvider,
    MockTTSProvider,
    MockVideoProvider,
)
from app.ai.interfaces import (
    ASRProvider,
    AudioEnhanceProvider,
    AvatarProvider,
    ImageProvider,
    LLMProvider,
    MattingProvider,
    TalkingAvatarProvider,
    TranslationProvider,
    TTSProvider,
    VideoProvider,
)
from app.core.config import get_settings
from app.core.exceptions import AIProviderNotFoundException, AIProviderValidationError
from app.core.logging import get_logger

logger = get_logger(__name__)


class AICapability(str, Enum):
    """Core AI processing capabilities supported across HeyZen platform."""
    LLM = "llm"
    TTS = "tts"
    ASR = "asr"
    TRANSLATION = "translation"
    AVATAR = "avatar"
    IMAGE = "image"
    VIDEO = "video"
    MATTING = "matting"
    AUDIO_ENHANCE = "audio_enhance"


CAPABILITY_PROTOCOLS: Dict[AICapability, Type[Any]] = {
    AICapability.LLM: LLMProvider,
    AICapability.TTS: TTSProvider,
    AICapability.ASR: ASRProvider,
    AICapability.TRANSLATION: TranslationProvider,
    AICapability.AVATAR: AvatarProvider,
    AICapability.IMAGE: ImageProvider,
    AICapability.VIDEO: VideoProvider,
    AICapability.MATTING: MattingProvider,
    AICapability.AUDIO_ENHANCE: AudioEnhanceProvider,
}


class AIProviderRegistry:
    """Central registry managing AI provider implementations by capability and name."""

    def __init__(self) -> None:
        self._providers: Dict[AICapability, Dict[str, Any]] = {cap: {} for cap in AICapability}
        self._descriptors: Dict[AICapability, Dict[str, ProviderDescriptor]] = {cap: {} for cap in AICapability}
        self._default_providers: Dict[AICapability, str] = {}

    def _normalize_capability(self, capability: Union[AICapability, str]) -> AICapability:
        """Coerce string or enum into canonical AICapability enum."""
        if isinstance(capability, AICapability):
            return capability
        try:
            return AICapability(str(capability).lower())
        except ValueError:
            valid = [c.value for c in AICapability]
            raise AIProviderNotFoundException(
                message=f"Unknown AI capability '{capability}'. Valid capabilities are: {valid}",
                code="AI_CAPABILITY_UNKNOWN",
            )

    def register(
        self,
        capability: Union[AICapability, str],
        name: str,
        provider: Any,
        is_default: bool = False,
        descriptor: Optional[ProviderDescriptor] = None,
    ) -> None:
        """Register a provider instance or factory for a given capability.

        Validates that the provider satisfies the runtime protocol contract.
        """
        cap = self._normalize_capability(capability)
        protocol = CAPABILITY_PROTOCOLS[cap]

        # Check protocol conformance
        if not isinstance(provider, protocol):
            raise AIProviderValidationError(
                message=(
                    f"Provider '{name}' for capability '{cap.value}' does not satisfy the "
                    f"required protocol contract '{protocol.__name__}'."
                ),
                code="AI_PROVIDER_PROTOCOL_MISMATCH",
            )

        provider_name = name.strip().lower()
        self._providers[cap][provider_name] = provider

        # Resolve descriptor: explicit argument > provider.descriptor attribute > default
        if descriptor is None and hasattr(provider, "descriptor"):
            descriptor = getattr(provider, "descriptor")
        if descriptor is None:
            descriptor = ProviderDescriptor(
                name=provider_name,
                capability=cap.value,
                is_available=True,
            )
        self._descriptors[cap][provider_name] = descriptor

        if is_default or cap not in self._default_providers:
            self._default_providers[cap] = provider_name

        logger.info(
            "Registered AI provider '%s' for capability '%s' (is_default=%s)",
            provider_name,
            cap.value,
            is_default,
        )

    def get_provider(
        self,
        capability: Union[AICapability, str],
        name: Optional[str] = None,
        device: Optional[str] = None,
    ) -> Any:
        """Resolve an active provider for a capability.

        If name is None, resolves the default configured provider.
        """
        cap = self._normalize_capability(capability)
        available = self._providers[cap]

        if device and str(device).strip().lower() == "cuda":
            from app.ai.hardware import detect_hardware
            hw = detect_hardware()
            if not hw.has_cuda:
                from app.core.exceptions import AIRuntimeUnavailableException
                raise AIRuntimeUnavailableException(
                    message="CUDA device execution was requested, but no NVIDIA CUDA GPU accelerator is available on this CPU host.",
                    code="GPU_UNAVAILABLE",
                )

        # Determine target provider name
        target_name = name.strip().lower() if name else None
        if target_name in ("musetalk", "stable_diffusion"):
            from app.ai.hardware import detect_hardware
            hw = detect_hardware()
            if not hw.has_cuda:
                from app.core.exceptions import AIRuntimeUnavailableException
                raise AIRuntimeUnavailableException(
                    message=f"{target_name.capitalize()} provider requires an NVIDIA CUDA GPU accelerator, which is not available on this CPU host.",
                    code="GPU_UNAVAILABLE",
                )

        if not target_name:
            settings = get_settings()
            if settings.AI_PROVIDER_MODE == "real":
                if cap == AICapability.TTS:
                    target_name = "piper"
                elif cap == AICapability.ASR:
                    target_name = "whisper"
                elif cap == AICapability.AVATAR:
                    target_name = "gpu_avatar" if "gpu_avatar" in self._descriptors[cap] else "wav2lip"
                elif cap == AICapability.LLM:
                    target_name = "qwen"
                elif cap == AICapability.TRANSLATION:
                    target_name = "ctranslate2"
                elif cap == AICapability.MATTING:
                    target_name = "mediapipe"
                elif cap == AICapability.AUDIO_ENHANCE:
                    target_name = "deepfilter"
                elif cap == AICapability.IMAGE:
                    target_name = "stable_diffusion"
                else:
                    target_name = self._default_providers.get(cap)
            else:
                target_name = self._default_providers.get(cap)
                if not target_name:
                    setting_key = f"DEFAULT_{cap.value.upper()}_PROVIDER"
                    target_name = getattr(settings, setting_key, "mock").lower()

        if target_name not in available:
            registered_names = list(available.keys())
            raise AIProviderNotFoundException(
                message=(
                    f"No provider registered for capability '{cap.value}' with name '{target_name}'. "
                    f"Available providers: {registered_names}"
                ),
                code="AI_PROVIDER_NOT_CONFIGURED",
            )

        settings = get_settings()
        if settings.AI_PROVIDER_MODE == "real" and target_name == "mock" and name != "mock":
            from app.core.exceptions import AIRuntimeUnavailableException
            raise AIRuntimeUnavailableException(
                message=(
                    f"Real AI mode is active (AI_PROVIDER_MODE='real'); resolving mock provider for '{cap.value}' "
                    "without explicit 'mock' request is strictly forbidden."
                ),
                code="REAL_MODE_MOCK_FALLBACK_FORBIDDEN",
            )


        provider = available[target_name]
        return provider

    def get_llm_provider(self, name: Optional[str] = None):
        return self.get_provider(AICapability.LLM, name)

    def get_tts_provider(self, name: Optional[str] = None):
        return self.get_provider(AICapability.TTS, name)

    def get_asr_provider(self, name: Optional[str] = None):
        return self.get_provider(AICapability.ASR, name)

    def get_translation_provider(self, name: Optional[str] = None):
        return self.get_provider(AICapability.TRANSLATION, name)

    def get_avatar_provider(self, name: Optional[str] = None, device: Optional[str] = None):
        target_name = name or "gpu_avatar"
        if target_name in ("legacy_delaunay", "delaunay", "wav2lip", "mock"):
            target_name = "gpu_avatar"
        return self.get_provider(AICapability.AVATAR, name=target_name, device=device)

    def get_talking_avatar_provider(self, name: Optional[str] = None, device: Optional[str] = None) -> TalkingAvatarProvider:
        target_name = name or "gpu_avatar"
        if target_name in ("legacy_delaunay", "delaunay", "wav2lip", "mock"):
            target_name = "gpu_avatar"
        return self.get_provider(AICapability.AVATAR, name=target_name, device=device)

    def get_image_provider(self, name: Optional[str] = None):
        return self.get_provider(AICapability.IMAGE, name)

    def get_video_provider(self, name: Optional[str] = None):
        return self.get_provider(AICapability.VIDEO, name)

    def get_matting_provider(self, name: Optional[str] = None):
        target_name = name or "mediapipe"
        return self.get_provider(AICapability.MATTING, target_name)

    def get_audio_enhance_provider(self, name: Optional[str] = None) -> AudioEnhanceProvider:
        return self.get_provider(AICapability.AUDIO_ENHANCE, name)

    def get_descriptor(
        self,
        capability: Union[AICapability, str],
        name: Optional[str] = None,
    ) -> Optional[ProviderDescriptor]:
        """Resolve capability descriptor for provider, defaulting to active provider."""
        cap = self._normalize_capability(capability)
        target_name = name.strip().lower() if name else None
        if not target_name:
            settings = get_settings()
            if settings.AI_PROVIDER_MODE == "real":
                if cap == AICapability.TTS and "piper" in self._descriptors[cap]:
                    target_name = "piper"
                elif cap == AICapability.ASR and "whisper" in self._descriptors[cap]:
                    target_name = "whisper"
                elif cap == AICapability.AVATAR:
                    if "gpu_avatar" in self._descriptors[cap]:
                        target_name = "gpu_avatar"
                elif cap == AICapability.LLM and "qwen" in self._descriptors[cap]:
                    target_name = "qwen"
                elif cap == AICapability.TRANSLATION and "ctranslate2" in self._descriptors[cap]:
                    target_name = "ctranslate2"
                elif cap == AICapability.MATTING and "mediapipe" in self._descriptors[cap]:
                    target_name = "mediapipe"
                elif cap == AICapability.AUDIO_ENHANCE and "deepfilter" in self._descriptors[cap]:
                    target_name = "deepfilter"
                elif cap == AICapability.IMAGE and "stable_diffusion" in self._descriptors[cap]:
                    target_name = "stable_diffusion"
                else:
                    target_name = self._default_providers.get(cap)
            else:
                target_name = self._default_providers.get(cap)
                if not target_name:
                    setting_key = f"DEFAULT_{cap.value.upper()}_PROVIDER"
                    target_name = getattr(settings, setting_key, "mock").lower()
        return self._descriptors[cap].get(target_name)

    def list_descriptors(
        self,
        capability: Optional[Union[AICapability, str]] = None,
    ) -> List[ProviderDescriptor]:
        """List provider descriptors, optionally filtered by capability."""
        if capability is not None:
            cap = self._normalize_capability(capability)
            return list(self._descriptors[cap].values())
        result: List[ProviderDescriptor] = []
        for cap in AICapability:
            result.extend(self._descriptors[cap].values())
        return result

    def find_capable_provider(
        self,
        capability: Union[AICapability, str],
        language: Optional[str] = None,
        format_name: Optional[str] = None,
        require_gpu: Optional[bool] = None,
    ) -> Optional[str]:
        """Find the most suitable available provider matching given requirements."""
        cap = self._normalize_capability(capability)
        default_name = self._default_providers.get(cap)

        candidates: List[str] = []
        for name, desc in self._descriptors[cap].items():
            if not desc.is_available:
                continue
            if language and not desc.supports_language(language):
                continue
            if format_name and not (desc.supports_output_format(format_name) or desc.supports_input_format(format_name)):
                continue
            if require_gpu is not None and desc.requires_gpu != require_gpu:
                continue
            candidates.append(name)

        if not candidates:
            return None
        if default_name and default_name in candidates:
            return default_name
        return candidates[0]

    def is_provider_available(
        self,
        capability: Union[AICapability, str],
        name: Optional[str] = None,
    ) -> bool:
        """Check if provider is registered and marked available."""
        desc = self.get_descriptor(capability, name)
        return desc.is_available if desc else False

    def list_providers(
        self,
        capability: Optional[Union[AICapability, str]] = None,
    ) -> Dict[str, List[str]]:
        """List registered provider names, optionally filtered by capability."""
        if capability is not None:
            cap = self._normalize_capability(capability)
            return {cap.value: list(self._providers[cap].keys())}
        return {cap.value: list(self._providers[cap].keys()) for cap in AICapability}

    def unregister(self, capability: Union[AICapability, str], name: str) -> bool:
        """Remove a provider registration."""
        cap = self._normalize_capability(capability)
        provider_name = name.strip().lower()
        if provider_name in self._providers[cap]:
            del self._providers[cap][provider_name]
            if provider_name in self._descriptors[cap]:
                del self._descriptors[cap][provider_name]
            if self._default_providers.get(cap) == provider_name:
                remaining = list(self._providers[cap].keys())
                self._default_providers[cap] = remaining[0] if remaining else None  # type: ignore
            return True
        return False

    def reset(self) -> None:
        """Clear all provider registrations and defaults (primarily for test resets)."""
        self._providers = {cap: {} for cap in AICapability}
        self._descriptors = {cap: {} for cap in AICapability}
        self._default_providers = {}


# Global singleton instance
_registry_instance: Optional[AIProviderRegistry] = None


def get_ai_registry() -> AIProviderRegistry:
    """Retrieve active AIProviderRegistry singleton, auto-registering mock adapters if empty."""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = AIProviderRegistry()
        # Bootstrap default mock implementations for all capabilities
        _bootstrap_default_mock_providers(_registry_instance)
    return _registry_instance


def _bootstrap_default_mock_providers(registry: AIProviderRegistry) -> None:
    """Auto-register deterministic mock adapters as initial platform defaults."""
    registry.register(AICapability.LLM, "mock", MockLLMProvider(), is_default=True)
    registry.register(AICapability.TTS, "mock", MockTTSProvider(), is_default=True)
    registry.register(AICapability.ASR, "mock", MockASRProvider(), is_default=True)
    registry.register(AICapability.TRANSLATION, "mock", MockTranslationProvider(), is_default=True)
    registry.register(AICapability.AVATAR, "mock", MockAvatarProvider(), is_default=True)
    registry.register(AICapability.IMAGE, "mock", MockImageProvider(), is_default=True)
    registry.register(AICapability.VIDEO, "mock", MockVideoProvider(), is_default=True)
    registry.register(AICapability.MATTING, "mock", MockMattingProvider(), is_default=True)
    registry.register(AICapability.AUDIO_ENHANCE, "mock", MockAudioEnhanceProvider(), is_default=True)

    # Register local real Piper TTS provider
    try:
        from app.ai.adapters.piper import PiperTTSProvider
        settings = get_settings()
        piper_default = (getattr(settings, "DEFAULT_TTS_PROVIDER", "mock") == "piper")
        registry.register(AICapability.TTS, "piper", PiperTTSProvider(), is_default=piper_default)
    except Exception as exc:
        logger.warning("Could not auto-register PiperTTSProvider: %s", exc)

    # Register local real Kokoro TTS provider
    try:
        from app.ai.adapters.kokoro import KokoroTTSProvider
        settings = get_settings()
        kokoro_default = (getattr(settings, "DEFAULT_TTS_PROVIDER", "mock") == "kokoro")
        registry.register(AICapability.TTS, "kokoro", KokoroTTSProvider(), is_default=kokoro_default)
    except Exception as exc:
        logger.warning("Could not auto-register KokoroTTSProvider: %s", exc)

    # Register local real Whisper ASR provider
    try:
        from app.ai.adapters.whisper import WhisperASRProvider
        settings = get_settings()
        whisper_default = (getattr(settings, "DEFAULT_ASR_PROVIDER", "mock") == "whisper")
        registry.register(AICapability.ASR, "whisper", WhisperASRProvider(), is_default=whisper_default)
    except Exception as exc:
        logger.warning("Could not auto-register WhisperASRProvider: %s", exc)

    # Register local real Wav2Lip ONNX Avatar provider (strictly development-only lip-sync engine)
    try:
        from app.ai.adapters.wav2lip import Wav2LipONNXAvatarProvider
        registry.register(AICapability.AVATAR, "wav2lip", Wav2LipONNXAvatarProvider(), is_default=False)
    except Exception as exc:
        logger.warning("Could not auto-register Wav2LipONNXAvatarProvider: %s", exc)

    # Register LivePortrait Avatar provider (Official KwaiVGI Architecture)
    try:
        from app.ai.adapters.liveportrait import LivePortraitAdapter
        registry.register(AICapability.AVATAR, "liveportrait", LivePortraitAdapter(), is_default=False)
    except Exception as exc:
        logger.warning("Could not auto-register LivePortraitAdapter: %s", exc)

    # Register MuseTalk Avatar provider (Production-target CUDA architecture / MuseTalk 1.5)
    try:
        from app.ai.adapters.musetalk import MuseTalkAvatarProvider
        registry.register(AICapability.AVATAR, "musetalk", MuseTalkAvatarProvider(), is_default=False)
    except Exception as exc:
        logger.warning("Could not auto-register MuseTalkAvatarProvider: %s", exc)

    # Register Hallo2 Avatar provider (Fudan Hierarchical Diffusion)
    try:
        from app.ai.adapters.hallo2 import Hallo2Adapter
        registry.register(AICapability.AVATAR, "hallo2", Hallo2Adapter(), is_default=False)
    except Exception as exc:
        logger.warning("Could not auto-register Hallo2Adapter: %s", exc)

    # Register Unified GPU Avatar Provider (Canonical production neural avatar provider)
    try:
        from app.ai.providers.gpu_avatar_provider import GPUAvatarProvider
        settings = get_settings()
        gpu_default = (getattr(settings, "DEFAULT_AVATAR_PROVIDER", "gpu_avatar") in ("gpu_avatar", "liveportrait", "mock"))
        registry.register(AICapability.AVATAR, "gpu_avatar", GPUAvatarProvider(), is_default=gpu_default)
    except Exception as exc:
        logger.warning("Could not auto-register GPUAvatarProvider: %s", exc)

    # Register local real Qwen LLM provider
    try:
        from app.ai.adapters.qwen import RealQwenLLMProvider
        settings = get_settings()
        qwen_default = (getattr(settings, "DEFAULT_LLM_PROVIDER", "mock") == "qwen")
        registry.register(AICapability.LLM, "qwen", RealQwenLLMProvider(), is_default=qwen_default)
    except Exception as exc:
        logger.warning("Could not auto-register RealQwenLLMProvider: %s", exc)

    # Register local real CTranslate2 Translation provider
    try:
        from app.ai.adapters.translation import RealCTranslate2TranslationProvider
        settings = get_settings()
        trans_default = (getattr(settings, "DEFAULT_TRANSLATION_PROVIDER", "mock") == "ctranslate2")
        ct2_provider = RealCTranslate2TranslationProvider()
        registry.register(AICapability.TRANSLATION, "ctranslate2", ct2_provider, is_default=trans_default)
        registry.register(AICapability.TRANSLATION, "opus_mt", ct2_provider, is_default=False)
    except Exception as exc:
        logger.warning("Could not auto-register RealCTranslate2TranslationProvider: %s", exc)

    # Register local real MediaPipe Matting provider
    try:
        from app.ai.adapters.matting import RealMediaPipeMattingProvider
        settings = get_settings()
        matting_default = (getattr(settings, "DEFAULT_MATTING_PROVIDER", "mediapipe") == "mediapipe")
        registry.register(AICapability.MATTING, "mediapipe", RealMediaPipeMattingProvider(), is_default=True)
    except Exception as exc:
        logger.warning("Could not auto-register RealMediaPipeMattingProvider: %s", exc)

    # Register local real DeepFilter Audio Enhance provider
    try:
        from app.ai.adapters.audio_enhance import DeepFilterAudioEnhanceProvider
        settings = get_settings()
        audio_enhance_default = (getattr(settings, "DEFAULT_AUDIO_ENHANCE_PROVIDER", "mock") == "deepfilter")
        registry.register(AICapability.AUDIO_ENHANCE, "deepfilter", DeepFilterAudioEnhanceProvider(), is_default=audio_enhance_default)
    except Exception as exc:
        logger.warning("Could not auto-register DeepFilterAudioEnhanceProvider: %s", exc)

    # Register Stable Diffusion Image provider (Production-target CUDA architecture)
    try:
        from app.ai.adapters.stable_diffusion import StableDiffusionImageProvider
        settings = get_settings()
        sd_default = (getattr(settings, "DEFAULT_IMAGE_PROVIDER", "mock") == "stable_diffusion")
        registry.register(AICapability.IMAGE, "stable_diffusion", StableDiffusionImageProvider(), is_default=sd_default)
    except Exception as exc:
        logger.warning("Could not auto-register StableDiffusionImageProvider: %s", exc)

    # Register OpenVoice V2 Voice Cloning provider
    try:
        from app.ai.adapters.openvoice import OpenVoiceCloningProvider
        registry.register(AICapability.TTS, "openvoice", OpenVoiceCloningProvider(), is_default=False)
    except Exception as exc:
        logger.warning("Could not auto-register OpenVoiceCloningProvider: %s", exc)



# Convenience capability accessor functions for business services


def get_llm_provider(name: Optional[str] = None, device: Optional[str] = None) -> LLMProvider:
    """Resolve active LLM provider."""
    return get_ai_registry().get_provider(AICapability.LLM, name=name, device=device)



def get_tts_provider(name: Optional[str] = None) -> TTSProvider:
    """Resolve active TTS provider."""
    return get_ai_registry().get_provider(AICapability.TTS, name)


def get_voice_clone_provider(name: Optional[str] = "openvoice") -> TTSProvider:
    """Resolve active Voice Cloning provider."""
    return get_ai_registry().get_provider(AICapability.TTS, name or "openvoice")


def get_asr_provider(name: Optional[str] = None) -> ASRProvider:
    """Resolve active ASR provider."""
    return get_ai_registry().get_provider(AICapability.ASR, name)


def get_translation_provider(name: Optional[str] = None) -> TranslationProvider:
    """Resolve active Translation provider."""
    return get_ai_registry().get_provider(AICapability.TRANSLATION, name)


def get_avatar_provider(name: Optional[str] = None, device: Optional[str] = None) -> AvatarProvider:
    """Resolve active Avatar provider."""
    return get_ai_registry().get_avatar_provider(name=name, device=device)


def get_talking_avatar_provider(name: Optional[str] = None, device: Optional[str] = None) -> TalkingAvatarProvider:
    """Resolve active TalkingAvatarProvider with strict capability and real-mode enforcement."""
    return get_ai_registry().get_talking_avatar_provider(name=name, device=device)


def get_image_provider(name: Optional[str] = None) -> ImageProvider:
    """Resolve active Image provider."""
    return get_ai_registry().get_provider(AICapability.IMAGE, name)


def get_video_provider(name: Optional[str] = None) -> VideoProvider:
    """Resolve active Video provider."""
    return get_ai_registry().get_provider(AICapability.VIDEO, name)


def get_matting_provider(name: Optional[str] = None) -> MattingProvider:
    """Resolve active Matting provider."""
    return get_ai_registry().get_provider(AICapability.MATTING, name)


def get_audio_enhance_provider(name: Optional[str] = None) -> AudioEnhanceProvider:
    """Resolve active Audio Enhancement provider."""
    return get_ai_registry().get_provider(AICapability.AUDIO_ENHANCE, name)


# Phase 8 Local AI Runtime Foundation Facade Accessors
def get_ai_model_registry():
    """Retrieve global AI ModelRegistry singleton."""
    from app.ai.model_registry import get_model_registry
    return get_model_registry()


def get_ai_runtime_registry():
    """Retrieve global AI RuntimeRegistry singleton."""
    from app.ai.runtimes import get_runtime_registry
    return get_runtime_registry()


def get_ai_hardware_spec(refresh: bool = False):
    """Retrieve host HardwareSpec."""
    from app.ai.hardware import detect_hardware
    return detect_hardware(refresh=refresh)


def resolve_model_and_runtime(
    capability: Union[AICapability, str],
    preferred_device: Optional[str] = None,
    language: Optional[str] = None,
    format_name: Optional[str] = None,
    model_id: Optional[str] = None,
    mode: Optional[str] = None,
):
    """Resolve compatible model and runtime for a capability request."""
    from app.ai.selection import select_model_and_runtime
    cap_str = capability.value if isinstance(capability, AICapability) else str(capability)
    return select_model_and_runtime(
        capability=cap_str,
        preferred_device=preferred_device,
        language=language,
        format_name=format_name,
        model_id=model_id,
        mode=mode,
    )

