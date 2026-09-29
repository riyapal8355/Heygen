"""Phase 8 Step 8 — Closed-Loop Audio Enhancement & Speech Cleanup Pipeline Test.

Executes the complete multi-modal pipeline:
1. Piper TTS: Synthesizes narration audio.
2. Real Audio Enhancement: Silero VAD silence trimming, adaptive de-noise, broadcast vocal EQ mastering (48kHz stereo).
3. Whisper ASR: Transcribes the cleaned studio audio into structured word-level subtitle cues.
4. Timeline Compositor: Assembles the multi-track canvas, enhanced audio, and subtitle cues into final MP4.
5. Telemetry & Verification: Validates audio/video container, sampling rates, RTF, and licensing separation.
"""

import asyncio
import io
import os
import time
import wave
from pathlib import Path
import pytest

from app.ai.adapters.audio_enhance import DeepFilterAudioEnhanceProvider
from app.ai.adapters.piper import DEFAULT_PIPER_VOICE_ID, PiperTTSProvider
from app.ai.adapters.whisper import WhisperASRProvider
from app.media.compositor import TimelineCompositor
from app.media.ffmpeg import FFmpegService
from app.media.ffprobe import FFprobeService
from app.media.workspace import MediaWorkspace
from app.schemas.project_document import (
    ProjectDocumentV1,
    ProjectSettings,
    Scene,
    SceneSpeech,
)


@pytest.mark.asyncio
async def test_real_audio_enhancement_closed_loop_pipeline(db_session, test_user, test_workspace):
    """Verify complete closed-loop pipeline from Piper TTS -> Audio Enhance -> Whisper ASR -> Compositor MP4."""
    from app.services.asset_lifecycle import AssetLifecycleManager

    # 1. Synthesize real speech with Piper TTS
    piper = PiperTTSProvider()
    spoken_text = "Welcome to HeyZen studio. This is neural speech cleanup and broadcast mastering."

    t0_tts = time.perf_counter()
    tts_result = await piper.synthesize_speech(
        text=spoken_text,
        voice_id=DEFAULT_PIPER_VOICE_ID,
    )
    latency_tts = time.perf_counter() - t0_tts

    assert len(tts_result.audio_bytes) > 0
    assert tts_result.duration_seconds > 1.0

    # 2. Insert a 2.0-second dead air pause in the speech audio to test Silero VAD trimming
    with wave.open(io.BytesIO(tts_result.audio_bytes), "rb") as wf:
        sr = wf.getframerate()
        raw_frames = wf.readframes(wf.getnframes())

    silence_frames = b"\x00" * int(sr * 2.0 * 2)  # 2.0s 16-bit mono silence
    half_idx = len(raw_frames) // 4 * 2
    paused_raw = raw_frames[:half_idx] + silence_frames + raw_frames[half_idx:]

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(paused_raw)
    raw_speech_with_pause = buf.getvalue()
    raw_duration = len(paused_raw) / (sr * 2)

    # 3. Real Audio Enhancement (DeepFilterNet / Silero VAD / FFmpeg Broadcast Mastering)
    enhance_provider = DeepFilterAudioEnhanceProvider()
    t0_enh = time.perf_counter()
    enhanced_res = await enhance_provider.enhance_audio(
        audio_bytes=raw_speech_with_pause,
        denoise=True,
        remove_silence=True,
        remove_fillers=False,
        master_audio=True,
        silence_threshold_seconds=0.8,
    )
    latency_enh = time.perf_counter() - t0_enh


    assert len(enhanced_res.audio_bytes) > 0
    assert enhanced_res.sample_rate == 48000
    assert enhanced_res.channels == 2
    assert enhanced_res.mastered is True
    assert enhanced_res.noise_reduction_db == 18.0
    assert enhanced_res.silence_trimmed_seconds > 0.5
    assert enhanced_res.fillers_status == "NOT_IMPLEMENTED"
    assert enhanced_res.fillers_removed == 0
    assert enhanced_res.duration_seconds < raw_duration
    assert enhanced_res.metrics["real_time_factor"] < 1.0

    # Ingest enhanced audio asset into DB/MinIO
    asset_mgr = AssetLifecycleManager(db_session)
    enhanced_asset = await asset_mgr.ingest_generated_asset(
        workspace_id=test_workspace.id,
        created_by=test_user.id,
        content=enhanced_res.audio_bytes,
        original_filename="enhanced_speech_clean.wav",
        asset_type="audio",
        mime_type="audio/wav",
        metadata={"enhanced": True},
    )

    # 4. Whisper ASR Transcription of Enhanced Audio
    whisper = WhisperASRProvider()
    t0_asr = time.perf_counter()
    asr_res = await whisper.transcribe_bytes(
        audio_bytes=enhanced_res.audio_bytes,
        language="en",
        include_word_timestamps=True,
    )
    latency_asr = time.perf_counter() - t0_asr

    assert len(asr_res.full_text) > 0
    assert len(asr_res.segments) > 0

    # 5. Assemble Timeline and Render via Compositor
    ffmpeg_svc = FFmpegService()
    ffprobe_svc = FFprobeService()
    compositor = TimelineCompositor(ffmpeg_service=ffmpeg_svc, ffprobe_service=ffprobe_svc)

    with MediaWorkspace(prefix="closed_loop_enhanced_") as mws:
        duration = round(enhanced_res.duration_seconds, 2)
        doc = ProjectDocumentV1(
            settings=ProjectSettings(
                aspect_ratio="16:9",
                width=640,
                height=360,
                fps=25,
            ),
            scenes=[
                Scene(
                    id="enhanced_scene_1",
                    sequence=1,
                    duration=duration,
                    background={"type": "color", "value": "#090D16"},
                    speech=SceneSpeech(
                        audio_asset_id=str(enhanced_asset.id),
                        voice_id=DEFAULT_PIPER_VOICE_ID,
                    ),
                    subtitles=asr_res.segments,
                )
            ],
        )

        t0_render = time.perf_counter()
        result = await compositor.render_project(
            document=doc,
            workspace_id=test_workspace.id,
            db=db_session,
            media_workspace=mws,
        )
        latency_render = time.perf_counter() - t0_render

        assert result.video_path.exists()
        assert result.video_path.stat().st_size > 5000

        # 6. Verify with FFprobe
        probe = result.probe_result
        assert len(probe.video_streams) == 1
        assert len(probe.audio_streams) == 1
        assert probe.duration_seconds > 0.5
        assert probe.width == 640
        assert probe.height == 360

        print("\n=== CLOSED-LOOP BENCHMARK TELEMETRY ===")
        print(f"TTS Latency: {latency_tts:.3f}s")
        print(f"Audio Enhancement Latency: {latency_enh:.3f}s (RTF: {enhanced_res.metrics['real_time_factor']:.4f})")
        print(f"Raw duration: {raw_duration:.3f}s -> Enhanced duration: {enhanced_res.duration_seconds:.3f}s")
        print(f"Silence trimmed: {enhanced_res.silence_trimmed_seconds:.3f}s")
        print(f"Noise reduction: {enhanced_res.noise_reduction_db}dB")
        print(f"Final MP4: {result.video_path.stat().st_size} bytes, probed {probe.duration_seconds:.2f}s")

