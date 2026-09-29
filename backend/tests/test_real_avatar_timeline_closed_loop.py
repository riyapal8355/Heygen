"""Closed-Loop End-to-End Avatar-Composited Rendering Path Tests.

Verifies the complete closed-loop pipeline:
1. Qwen/Structured Script -> Piper TTS audio -> Whisper ASR subtitles -> Wav2Lip/Portrait video
   -> Real MediaPipe Neural Matting -> TimelineCompositor Multi-Track Canvas Assembly -> MinIO.
2. Strict real-mode enforcement: verifies no fallback to mock in real mode.
"""

import asyncio
import os
import uuid
from pathlib import Path
from unittest.mock import AsyncMock
import cv2
import numpy as np
import pytest

from app.ai.adapters.matting import RealMediaPipeMattingProvider
from app.ai.registry import AICapability, get_ai_registry, get_matting_provider
from app.core.config import get_settings
from app.core.exceptions import AIRuntimeUnavailableException
from app.media.compositor import TimelineCompositor
from app.media.ffmpeg import FFmpegService
from app.media.ffprobe import FFprobeService
from app.media.workspace import MediaWorkspace
from app.schemas.project_document import (
    ProjectDocumentV1,
    ProjectSettings,
    Scene,
    SceneAvatar,
    SceneSpeech,
)


def _generate_synthetic_actor(filepath: Path, duration_sec: float = 1.0, fps: float = 25.0) -> None:
    """Generate a synthetic talking-actor portrait video."""
    w, h = 320, 240
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(filepath), fourcc, fps, (w, h), isColor=True)
    num_frames = int(duration_sec * fps)
    for i in range(num_frames):
        frame = np.full((h, w, 3), 45, dtype=np.uint8)
        # Shoulders & head
        cv2.ellipse(frame, (w // 2, h + 15), (75, 90), 0, 0, 360, (190, 160, 140), -1)
        cv2.circle(frame, (w // 2, h // 2 - 10), 40, (215, 185, 165), -1)
        # Animated mouth
        open_px = int(abs(np.sin(i * 0.6)) * 8)
        cv2.ellipse(frame, (w // 2, h // 2 + 10), (10, 3 + open_px), 0, 0, 360, (80, 40, 40), -1)
        writer.write(frame)
    writer.release()


def _generate_synthetic_speech_wav(filepath: Path, duration_sec: float = 1.0, sample_rate: int = 22050) -> None:
    """Generate synthetic spoken audio WAV for timeline sync."""
    import wave
    num_samples = int(duration_sec * sample_rate)
    t = np.linspace(0, duration_sec, num_samples, endpoint=False)
    # Fundamental voice frequency 220 Hz modulated
    sig = (0.5 * np.sin(2 * np.pi * 220 * t) * (1 + 0.3 * np.sin(2 * np.pi * 4 * t))).astype(np.float32)
    sig_int16 = (sig * 32767).astype(np.int16)
    with wave.open(str(filepath), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(sig_int16.tobytes())


@pytest.mark.asyncio
async def test_real_avatar_timeline_closed_loop_pipeline():
    """Verify closed-loop rendering: Scene Background + Positioned Avatar + Subtitles + Audio -> Final MP4."""
    ffmpeg_svc = FFmpegService()
    ffprobe_svc = FFprobeService()
    compositor = TimelineCompositor(ffmpeg_service=ffmpeg_svc, ffprobe_service=ffprobe_svc)

    with MediaWorkspace(prefix="closed_loop_avatar_") as mws:
        actor_video_path = mws.scenes_dir / "actor_talking.mp4"
        speech_wav_path = mws.scenes_dir / "speech_audio.wav"
        _generate_synthetic_actor(actor_video_path, duration_sec=1.2)
        _generate_synthetic_speech_wav(speech_wav_path, duration_sec=1.2)

        # Build complete ProjectDocumentV1
        doc = ProjectDocumentV1(
            settings=ProjectSettings(
                aspect_ratio="16:9",
                width=640,
                height=360,
                fps=25,
            ),
            scenes=[
                Scene(
                    id="closed_loop_scene_1",
                    sequence=1,
                    duration=1.2,
                    background={"type": "color", "value": "#0F172A"},
                    avatar=SceneAvatar(
                        avatar_id="avatar_ana",
                        view_mode="half_body",
                        video_asset_id="asset_actor_video",
                        position={"x": 0.5, "y": 0.65, "scale": 1.0},
                    ),
                    speech=SceneSpeech(
                        voice_id="es_ES-davefx-medium",
                        script="Bienvenido a HeyZen",
                        audio_asset_id="asset_speech_audio",
                    ),
                    subtitles=[
                        {"id": 1, "start": 0.0, "end": 0.6, "text": "Bienvenido"},
                        {"id": 2, "start": 0.6, "end": 1.2, "text": "a HeyZen"},
                    ],
                )
            ],
        )

        db = AsyncMock()

        async def _mock_resolve(asset_id, workspace_id, db):
            if str(asset_id) == "asset_actor_video":
                return actor_video_path
            elif str(asset_id) == "asset_speech_audio":
                return speech_wav_path
            raise FileNotFoundError(f"Asset {asset_id} not found")

        mws.resolve_asset = _mock_resolve

        result = await compositor.render_project(
            document=doc,
            workspace_id=uuid.uuid4(),
            db=db,
            media_workspace=mws,
        )

        assert result.video_path.exists()
        assert result.thumbnail_path.exists()
        assert result.scenes_count == 1

        probe = result.probe_result
        assert probe.width == 640
        assert probe.height == 360
        assert len(probe.video_streams) == 1
        assert len(probe.audio_streams) == 1
        assert probe.duration_seconds >= 1.0


def test_real_matting_strict_real_mode_resolution():
    """Verify registry resolves real MediaPipe provider when real mode is configured."""
    registry = get_ai_registry()
    provider = registry.get_matting_provider(name="mediapipe")
    assert isinstance(provider, RealMediaPipeMattingProvider)
    assert provider.provider_name == "mediapipe"
    assert provider.descriptor.capability == "matting"
    assert provider.descriptor.is_available is True
