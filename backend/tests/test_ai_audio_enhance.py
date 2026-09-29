"""Comprehensive tests for Real Audio Enhancement & Studio Speech Cleanup Provider.

Verifies:
1. Protocol conformance (AudioEnhanceProvider).
2. Model catalog registration (audio_enhance/silero-vad-cpu, audio_enhance/deepfilternet3-cpu).
3. Exact model provenance and MIT / Apache-2.0 COMMERCIAL_SAFE licensing.
4. Provider registry resolution (AICapability.AUDIO_ENHANCE).
5. Real Silero VAD pause trimming on speech audio.
6. Real de-noising (FFmpeg afftdn) and studio broadcast mastering (loudnorm, EQ).
7. Explicit refusal/non-faking of semantic filler removal (fillers_status="NOT_IMPLEMENTED", fillers_removed=0).
8. Strict real-mode failure on missing/corrupt model artifact.
9. Mock provider contract execution.
10. Performance and RTF telemetry.
"""

import io
import math
import os
from pathlib import Path
import struct
import tempfile
import time
import wave
import numpy as np
import pytest

from app.ai.adapters.audio_enhance import (
    DEFAULT_SILERO_VAD_PATH,
    SILERO_VAD_SHA256,
    DEEPFILTERNET3_CONFIG_SHA256,
    DEEPFILTERNET3_DF_DEC_SHA256,
    DEEPFILTERNET3_ENC_SHA256,
    DEEPFILTERNET3_ERB_DEC_SHA256,
    DEEPFILTERNET3_REVISION,
    DeepFilterAudioEnhanceProvider,
    DeepFilterNet3AudioEnhanceProvider,
    DeepFilterNet3Engine,
)
from app.ai.adapters.mock import MockAudioEnhanceProvider
from app.ai.contracts import AudioEnhanceContractRequest, AudioEnhanceContractResult
from app.ai.interfaces import AudioEnhanceProvider, AudioEnhanceResult
from app.ai.model_registry import ModelInstallStatus, get_model_registry
from app.ai.registry import AICapability, get_ai_registry, get_audio_enhance_provider
from app.core.exceptions import AIModelSecurityException, AIRuntimeUnavailableException, NotFoundException


def generate_synthetic_audio(
    duration_seconds: float = 3.0,
    sample_rate: int = 16000,
    with_silence_gap: bool = True,
) -> bytes:
    """Generate a clean synthetic sine-wave speech simulation audio WAV with an optional 1-second silence gap."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)

        total_samples = int(duration_seconds * sample_rate)
        # First 1.0s tone, 2.0s silence, remaining tone
        silence_start = int(1.0 * sample_rate)
        silence_end = int(3.0 * sample_rate) if with_silence_gap else silence_start

        samples = []
        for i in range(total_samples):
            if silence_start <= i < silence_end:
                samples.append(0)
            else:
                # 440 Hz sine wave
                val = int(16000 * math.sin(2 * math.pi * 440 * (i / sample_rate)))
                samples.append(val)

        raw_bytes = struct.pack(f"<{len(samples)}h", *samples)
        wf.writeframes(raw_bytes)

    return buf.getvalue()


def test_audio_enhance_protocol_conformance():
    """Verify that both DeepFilterAudioEnhanceProvider and MockAudioEnhanceProvider implement AudioEnhanceProvider."""
    real_provider = DeepFilterAudioEnhanceProvider()
    mock_provider = MockAudioEnhanceProvider()

    assert isinstance(real_provider, AudioEnhanceProvider)
    assert isinstance(mock_provider, AudioEnhanceProvider)
    assert real_provider.provider_name == "deepfilter"
    assert mock_provider.provider_name == "mock"


def test_audio_enhance_model_catalog_registration():
    """Verify audio enhance models are registered in ModelRegistry with verified metadata."""
    model_reg = get_model_registry()

    # Silero VAD
    vad_model = model_reg.get_model("audio_enhance/silero-vad-cpu")
    assert vad_model is not None
    assert vad_model.capability == "audio_enhance"
    assert vad_model.requires_gpu is False
    assert "cpu" in vad_model.supported_devices
    assert vad_model.license == "MIT"
    assert vad_model.license_commercial_permitted is True
    assert vad_model.metadata.get("license_classification") == "COMMERCIAL_SAFE"
    assert vad_model.checksum_sha256 == "a4a068cd6cf1ea8355b84327595838ca748ec29a25bc91fc82e6c299ccdc5808"
    assert vad_model.revision == "e71cae966052b992a7eca6b17738916ce0eca4ec"

    # DeepFilterNet3
    df_model = model_reg.get_model("audio_enhance/deepfilternet3-cpu")
    assert df_model is not None
    assert df_model.capability == "audio_enhance"
    assert df_model.requires_gpu is False
    assert "cpu" in df_model.supported_devices
    assert "MIT" in df_model.license
    assert df_model.license_commercial_permitted is True
    assert df_model.metadata.get("license_classification") == "COMMERCIAL_SAFE"
    assert df_model.checksum_sha256 == "7c5399d3da8a50ebef1c1a0ae421b33376aa5e45d0e92df16da7e83c9c131916"
    assert df_model.revision == "891882f01b26d72754c4663a5a2eb3060b17480c"


def test_audio_enhance_provider_registry_resolution():
    """Verify AICapability.AUDIO_ENHANCE resolves properly in AIProviderRegistry."""
    registry = get_ai_registry()
    provider = registry.get_audio_enhance_provider()
    assert provider is not None
    assert isinstance(provider, AudioEnhanceProvider)


@pytest.mark.asyncio
async def test_mock_audio_enhance_provider():
    """Verify deterministic behavior of MockAudioEnhanceProvider."""
    provider = MockAudioEnhanceProvider()
    input_wav = generate_synthetic_audio(duration_seconds=3.0)

    res = await provider.enhance_audio(
        audio_bytes=input_wav,
        denoise=True,
        remove_silence=True,
        remove_fillers=True,
        master_audio=True,
    )

    assert isinstance(res, AudioEnhanceResult)
    assert len(res.audio_bytes) > 0
    assert res.noise_reduction_db == 18.0
    assert res.silence_trimmed_seconds > 0.0
    assert res.fillers_removed == 0
    assert res.fillers_status == "NOT_IMPLEMENTED"
    assert res.mastered is True
    assert res.sample_rate == 48000


@pytest.mark.asyncio
async def test_real_audio_enhance_provider_denoise_and_master():
    """Verify real DeepFilter / FFmpeg de-noising and broadcast mastering pipeline."""
    provider = DeepFilterAudioEnhanceProvider()
    input_wav = generate_synthetic_audio(duration_seconds=2.0)

    t0 = time.perf_counter()
    res = await provider.enhance_audio(
        audio_bytes=input_wav,
        denoise=True,
        remove_silence=False,
        remove_fillers=False,
        master_audio=True,
    )
    latency_ms = (time.perf_counter() - t0) * 1000

    assert isinstance(res, AudioEnhanceResult)
    assert len(res.audio_bytes) > 0
    assert res.sample_rate == 48000
    assert res.mastered is True
    assert res.noise_reduction_db == 18.0
    assert res.silence_trimmed_seconds == 0.0
    assert res.fillers_removed == 0
    assert "real_time_factor" in res.metrics
    # Real-time factor on CPU should be comfortably fast (< 1.0 RTF)
    assert res.metrics["real_time_factor"] < 1.0


@pytest.mark.asyncio
async def test_real_audio_enhance_silero_vad_silence_trimming():
    """Verify Silero VAD accurately detects and trims dead pause segments on speech audio."""
    from app.ai.adapters.piper import PiperTTSProvider
    piper = PiperTTSProvider()
    speech = await piper.synthesize_speech("HeyZen audio enhancement test with a pause.")

    # Read speech WAV and insert a 2-second silence in the middle
    with wave.open(io.BytesIO(speech.audio_bytes), "rb") as wf:
        sr = wf.getframerate()
        raw = wf.readframes(wf.getnframes())

    silence_raw = b"\x00" * (sr * 2 * 2)  # 2 seconds of 16-bit mono silence
    half_idx = len(raw) // 4 * 2
    padded_raw = raw[:half_idx] + silence_raw + raw[half_idx:]

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(padded_raw)
    input_wav = buf.getvalue()

    provider = DeepFilterAudioEnhanceProvider()
    res = await provider.enhance_audio(
        audio_bytes=input_wav,
        denoise=False,
        remove_silence=True,
        remove_fillers=False,
        master_audio=False,
    )

    assert isinstance(res, AudioEnhanceResult)
    assert res.silence_trimmed_seconds > 0.5
    assert res.duration_seconds < (len(padded_raw) / (sr * 2))
    assert res.fillers_removed == 0
    assert res.fillers_status == "NOT_IMPLEMENTED"


@pytest.mark.asyncio
async def test_filler_removal_not_implemented_guard():
    """Verify semantic filler removal is explicitly guarded as NOT_IMPLEMENTED rather than faked."""
    provider = DeepFilterAudioEnhanceProvider()
    input_wav = generate_synthetic_audio(duration_seconds=2.0)

    res = await provider.enhance_audio(
        audio_bytes=input_wav,
        remove_fillers=True,
    )

    # Per strict user instructions: VAD must NOT fake lexical filler-word removal
    assert res.fillers_removed == 0
    assert res.fillers_status == "NOT_IMPLEMENTED"


@pytest.mark.asyncio
async def test_strict_real_mode_corrupt_artifact_guard():
    """Verify security check throws AIModelSecurityException on checksum mismatch."""
    provider = DeepFilterAudioEnhanceProvider()

    with tempfile.NamedTemporaryFile(suffix=".onnx", delete=False) as f:
        f.write(b"CORRUPT_NOT_REAL_ONNX_BYTES")
        corrupt_path = f.name

    try:
        with pytest.raises(AIModelSecurityException):
            provider._verify_file_hash(corrupt_path, "expected_sha256_hash_that_does_not_match")
    finally:
        if os.path.exists(corrupt_path):
            os.remove(corrupt_path)


@pytest.mark.asyncio
async def test_deepfilternet3_real_onnx_telemetry_proof():
    """Verify actual DeepFilterNet3 ONNX models executed and returned rich execution telemetry."""
    provider = DeepFilterAudioEnhanceProvider()
    input_wav = generate_synthetic_audio(duration_seconds=2.0)

    res = await provider.enhance_audio(
        audio_bytes=input_wav,
        denoise=True,
        remove_silence=False,
        remove_fillers=False,
        master_audio=True,
    )

    metrics = res.metrics
    assert metrics.get("provider") == "deepfilter"
    assert metrics.get("runtime") == "onnxruntime"
    assert metrics.get("execution_provider") == "CPUExecutionProvider"
    assert metrics.get("neural_enhancement_active") is True
    assert metrics.get("neural_engine") == "DeepFilterNet3 ONNX"
    assert metrics.get("model_revision") == "891882f01b26d72754c4663a5a2eb3060b17480c"
    assert metrics.get("enc_sha256") == "7c5399d3da8a50ebef1c1a0ae421b33376aa5e45d0e92df16da7e83c9c131916"
    assert metrics.get("erb_dec_sha256") == "ab669a1d10afe20911728b33053a452071042317a90581092b325da7b2f9d895"
    assert metrics.get("df_dec_sha256") == "23114ce3b0f6464b763ee62f7bb8aab6b2a129a21eabd5bcfe59413db05f278a"
    assert metrics.get("config_sha256") == "2782b17318f9ebb082f663604b2f030f7da156cf25f8714632825831b6553fa1"
    assert metrics.get("neural_inference_frames", 0) > 0
    assert metrics.get("neural_latency_seconds", 0.0) > 0.0
    assert metrics.get("neural_real_time_factor", 1.0) < 1.0
    assert metrics.get("mastering_active") is True


@pytest.mark.asyncio
async def test_deepfilternet3_noise_suppression_comparison():
    """Compare baseline noisy audio vs DeepFilterNet3 neural-only vs DeepFilterNet3 + Mastering."""
    sr = 48000
    duration = 3.0
    t = np.linspace(0, duration, int(sr * duration), endpoint=False, dtype=np.float32)

    # 1.0s speech tone + noise, 1.0s noise-only, 1.0s silence
    speech_tone = 0.3 * np.sin(2 * np.pi * 440 * t[: sr * 1])
    noise_part = 0.05 * np.random.randn(sr * 1).astype(np.float32)
    silence_part = np.zeros(sr * 1, dtype=np.float32)

    composite = np.concatenate([speech_tone + noise_part[: len(speech_tone)], noise_part, silence_part])
    comp_int16 = (np.clip(composite, -1.0, 1.0) * 32767.0).astype(np.int16)

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(comp_int16.tobytes())
    raw_wav = buf.getvalue()

    provider = DeepFilterAudioEnhanceProvider()

    # B: DeepFilterNet3 neural-only
    res_neural = await provider.enhance_audio(
        audio_bytes=raw_wav,
        denoise=True,
        trim_silence_pauses=False,
        apply_broadcast_eq=False,
    )
    assert res_neural.metrics["neural_enhancement_active"] is True
    assert res_neural.metrics["mastering_active"] is False

    # C: DeepFilterNet3 + Mastering
    res_full = await provider.enhance_audio(
        audio_bytes=raw_wav,
        denoise=True,
        trim_silence_pauses=False,
        apply_broadcast_eq=True,
    )
    assert res_full.metrics["neural_enhancement_active"] is True
    assert res_full.metrics["mastering_active"] is True

    # Parse audio and check noise attenuation in the middle 1.0s noise segment
    with wave.open(io.BytesIO(res_neural.audio_bytes), "rb") as wf:
        out_raw = wf.readframes(wf.getnframes())
        out_int16 = np.frombuffer(out_raw, dtype=np.int16)
        out_float = out_int16.astype(np.float32) / 32768.0

    # Middle 1.0s noise section (samples sr to 2*sr)
    # in stereo output from provider, step by channels
    channels = res_neural.channels
    noise_section = out_float[sr * channels : 2 * sr * channels : channels]
    noise_rms = np.sqrt(np.mean(noise_section**2))
    input_noise_rms = np.sqrt(np.mean(noise_part**2))

    # Neural model must attenuate noise significantly
    assert noise_rms < input_noise_rms * 0.5


def test_deepfilternet3_failure_missing_artifact():
    """Verify DeepFilterNet3Engine raises NotFoundException when an ONNX artifact is missing."""
    with tempfile.TemporaryDirectory() as empty_dir:
        engine = DeepFilterNet3Engine(cache_dir=empty_dir)
        dummy_audio = np.ones(48000, dtype=np.float32) * 0.1
        with pytest.raises(NotFoundException) as exc_info:
            engine.enhance(dummy_audio, sr=48000)
        assert exc_info.value.code == "AI_MODEL_NOT_FOUND"


def test_deepfilternet3_failure_corrupt_checksum():
    """Verify DeepFilterNet3Engine raises AIModelSecurityException on corrupted artifact checksum."""
    with tempfile.TemporaryDirectory() as corrupt_dir:
        model_dir = Path(corrupt_dir) / "audio_enhance" / "deepfilternet"
        model_dir.mkdir(parents=True)
        (model_dir / "enc.onnx").write_bytes(b"CORRUPTED_ONNX_MODEL_FILE")
        (model_dir / "erb_dec.onnx").write_bytes(b"CORRUPTED_ONNX_MODEL_FILE")
        (model_dir / "df_dec.onnx").write_bytes(b"CORRUPTED_ONNX_MODEL_FILE")
        (model_dir / "config.ini").write_bytes(b"CORRUPTED_CONFIG_FILE")

        engine = DeepFilterNet3Engine(cache_dir=corrupt_dir)
        dummy_audio = np.ones(48000, dtype=np.float32) * 0.1
        with pytest.raises(AIModelSecurityException) as exc_info:
            engine.enhance(dummy_audio, sr=48000)
        assert exc_info.value.code == "AI_MODEL_INTEGRITY_MISMATCH"


def test_deepfilternet3_failure_invalid_input():
    """Verify DeepFilterNet3Engine rejects empty, NaN, and wrong sample rate inputs."""
    from app.ai.adapters.audio_enhance import DeepFilterNet3Engine
    from app.core.config import get_settings
    cache_dir = getattr(get_settings(), "AI_MODEL_CACHE_DIR", "models_cache")
    engine = DeepFilterNet3Engine(cache_dir=cache_dir)

    # Empty audio
    with pytest.raises(ValueError, match="empty"):
        engine.enhance(np.array([], dtype=np.float32), sr=48000)

    # NaN audio
    nan_audio = np.array([0.1, np.nan, 0.2], dtype=np.float32)
    with pytest.raises(ValueError, match="NaN or Inf"):
        engine.enhance(nan_audio, sr=48000)

    # Wrong sample rate
    with pytest.raises(ValueError, match="sample rate"):
        engine.enhance(np.ones(1000, dtype=np.float32), sr=16000)

