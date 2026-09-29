"""AI provider adapters package."""

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

from app.ai.adapters.piper import PiperTTSProvider
from app.ai.adapters.kokoro import KokoroTTSProvider
from app.ai.adapters.wav2lip import Wav2LipONNXAvatarProvider
from app.ai.adapters.musetalk import MuseTalkAvatarProvider
from app.ai.adapters.liveportrait import LivePortraitAdapter
from app.ai.adapters.hallo2 import Hallo2Adapter
from app.ai.adapters.qwen import RealQwenLLMProvider
from app.ai.adapters.translation import RealCTranslate2TranslationProvider
from app.ai.adapters.matting import RealMediaPipeMattingProvider
from app.ai.adapters.audio_enhance import DeepFilterAudioEnhanceProvider
from app.ai.adapters.stable_diffusion import StableDiffusionImageProvider
from app.ai.adapters.openvoice import OpenVoiceCloningProvider

__all__ = [
    "MockLLMProvider",
    "RealQwenLLMProvider",
    "MockTTSProvider",
    "PiperTTSProvider",
    "KokoroTTSProvider",
    "MockASRProvider",
    "MockTranslationProvider",
    "RealCTranslate2TranslationProvider",
    "MockAvatarProvider",
    "Wav2LipONNXAvatarProvider",
    "LivePortraitAdapter",
    "MuseTalkAvatarProvider",
    "Hallo2Adapter",
    "MockImageProvider",
    "StableDiffusionImageProvider",
    "MockVideoProvider",
    "MockMattingProvider",
    "RealMediaPipeMattingProvider",
    "MockAudioEnhanceProvider",
    "DeepFilterAudioEnhanceProvider",
    "OpenVoiceCloningProvider",
]


