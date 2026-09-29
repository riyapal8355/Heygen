"""Unit tests for AI Execution Contracts."""

import uuid
import pytest
from pydantic import ValidationError

from app.ai.contracts import (
    AIContractRequest,
    AIContractResult,
    ASRContractRequest,
    ASRContractResult,
    ImageGenContractRequest,
    ImageGenContractResult,
    LipSyncContractRequest,
    LipSyncContractResult,
    MediaAssetRef,
    TranslationContractRequest,
    TranslationContractResult,
    TTSContractRequest,
    TTSContractResult,
    VideoGenContractRequest,
    VideoGenContractResult,
    VideoRenderContractRequest,
    VideoRenderContractResult,
)


def test_media_asset_ref_validation():
    """Verify MediaAssetRef allows asset_id, storage_key, mime_type, but forbids unknown fields."""
    asset_id = uuid.uuid4()
    ref = MediaAssetRef(asset_id=asset_id, storage_key="workspaces/1/assets/a.mp4", mime_type="video/mp4")
    assert ref.asset_id == asset_id
    assert ref.storage_key == "workspaces/1/assets/a.mp4"
    assert ref.mime_type == "video/mp4"

    # Extra fields forbidden
    with pytest.raises(ValidationError):
        MediaAssetRef(asset_id=asset_id, invalid_field="forbidden")


def test_ai_base_contract_request_and_result():
    """Verify AIContractRequest and AIContractResult base fields and serialization."""
    ws_id = uuid.uuid4()
    user_id = uuid.uuid4()
    job_id = uuid.uuid4()

    req = AIContractRequest(
        workspace_id=ws_id,
        user_id=user_id,
        job_id=job_id,
        metadata={"priority": "high"},
    )
    assert req.workspace_id == ws_id
    assert req.user_id == user_id
    assert req.job_id == job_id
    assert req.metadata["priority"] == "high"

    res = AIContractResult(
        status="succeeded",
        duration_seconds=12.5,
        metrics={"compute_time_ms": 450},
    )
    assert res.status == "succeeded"
    assert res.duration_seconds == 12.5
    assert res.metrics["compute_time_ms"] == 450


def test_tts_contract_request_and_validation():
    """Verify TTSContractRequest parameter constraints and validation rules."""
    ws_id = uuid.uuid4()
    user_id = uuid.uuid4()

    # Valid request
    req = TTSContractRequest(
        workspace_id=ws_id,
        user_id=user_id,
        text="Welcome to HeyZen.",
        voice_id="voice-cloned-01",
        speed=1.25,
        pitch=2.0,
        output_format="wav",
        pronunciation_rules=[{"term": "AI", "replacement_phonetic": "A-Eye"}],
    )
    assert req.text == "Welcome to HeyZen."
    assert req.speed == 1.25
    assert req.pitch == 2.0
    assert req.output_format == "wav"

    # Empty text rejected
    with pytest.raises(ValidationError):
        TTSContractRequest(workspace_id=ws_id, user_id=user_id, text="", voice_id="v1")

    # Speed out of bounds (<0.5 or >2.0)
    with pytest.raises(ValidationError):
        TTSContractRequest(workspace_id=ws_id, user_id=user_id, text="Hello", voice_id="v1", speed=0.1)

    with pytest.raises(ValidationError):
        TTSContractRequest(workspace_id=ws_id, user_id=user_id, text="Hello", voice_id="v1", speed=3.5)

    # Pitch out of bounds (<-20 or >20)
    with pytest.raises(ValidationError):
        TTSContractRequest(workspace_id=ws_id, user_id=user_id, text="Hello", voice_id="v1", pitch=-25.0)

    # Valid result model
    res = TTSContractResult(
        status="succeeded",
        sample_rate=24000,
        channels=1,
        word_count=3,
        word_timestamps=[{"word": "Hello", "start": 0.0, "end": 0.5}],
    )
    assert res.sample_rate == 24000
    assert res.word_count == 3


def test_asr_contract_request_and_result():
    """Verify ASRContractRequest and ASRContractResult structure."""
    ws_id = uuid.uuid4()
    user_id = uuid.uuid4()
    asset_id = uuid.uuid4()

    req = ASRContractRequest(
        workspace_id=ws_id,
        user_id=user_id,
        audio_asset=MediaAssetRef(asset_id=asset_id),
        language="en",
        include_word_timestamps=True,
    )
    assert req.audio_asset.asset_id == asset_id
    assert req.include_word_timestamps is True

    res = ASRContractResult(
        status="succeeded",
        detected_language="en",
        full_text="Welcome to the presentation.",
        segments=[{"id": 1, "start": 0.0, "end": 2.0, "text": "Welcome"}],
    )
    assert res.detected_language == "en"
    assert len(res.segments) == 1


def test_translation_contract_request_and_result():
    """Verify TranslationContractRequest with glossary rules."""
    ws_id = uuid.uuid4()
    user_id = uuid.uuid4()

    req = TranslationContractRequest(
        workspace_id=ws_id,
        user_id=user_id,
        text="Hello world",
        source_language="en",
        target_language="es",
        glossary_rules=[{"term": "world", "translated_term": "mundo"}],
    )
    assert req.target_language == "es"
    assert len(req.glossary_rules) == 1

    res = TranslationContractResult(
        status="succeeded",
        source_language="en",
        target_language="es",
        translated_text="Hola mundo",
        segments=[{"source": "Hello world", "target": "Hola mundo"}],
    )
    assert res.translated_text == "Hola mundo"


def test_lipsync_contract_request_and_result():
    """Verify LipSyncContractRequest parameter checking."""
    ws_id = uuid.uuid4()
    user_id = uuid.uuid4()
    look_id = uuid.uuid4()
    audio_id = uuid.uuid4()

    req = LipSyncContractRequest(
        workspace_id=ws_id,
        user_id=user_id,
        avatar_look_asset=MediaAssetRef(asset_id=look_id),
        audio_asset=MediaAssetRef(asset_id=audio_id),
        resolution="1080p",
        fps=30,
        output_format="mp4",
    )
    assert req.fps == 30
    assert req.resolution == "1080p"

    # FPS out of bounds
    with pytest.raises(ValidationError):
        LipSyncContractRequest(
            workspace_id=ws_id,
            user_id=user_id,
            avatar_look_asset=MediaAssetRef(asset_id=look_id),
            audio_asset=MediaAssetRef(asset_id=audio_id),
            fps=120,
        )

    res = LipSyncContractResult(
        status="succeeded",
        resolution="1920x1080",
        fps=30,
        frame_count=150,
    )
    assert res.frame_count == 150


def test_image_and_video_gen_contract_requests():
    """Verify ImageGen, VideoGen, and VideoRender contract models."""
    ws_id = uuid.uuid4()
    user_id = uuid.uuid4()
    proj_id = uuid.uuid4()

    # Image Gen
    img_req = ImageGenContractRequest(
        workspace_id=ws_id,
        user_id=user_id,
        prompt="Studio portrait with rim lighting",
        aspect_ratio="16:9",
        output_format="png",
    )
    assert img_req.aspect_ratio == "16:9"

    with pytest.raises(ValidationError):
        ImageGenContractRequest(
            workspace_id=ws_id,
            user_id=user_id,
            prompt="Test",
            aspect_ratio="100:1",  # Invalid
        )

    # Video Gen
    vid_req = VideoGenContractRequest(
        workspace_id=ws_id,
        user_id=user_id,
        prompt="Aerial view of sunset mountains",
        duration_seconds=5.0,
        aspect_ratio="16:9",
    )
    assert vid_req.duration_seconds == 5.0

    with pytest.raises(ValidationError):
        VideoGenContractRequest(
            workspace_id=ws_id,
            user_id=user_id,
            prompt="Test",
            duration_seconds=60.0,  # Max is 30.0
        )

    # Video Render
    render_req = VideoRenderContractRequest(
        workspace_id=ws_id,
        user_id=user_id,
        project_id=proj_id,
        resolution="1080p",
        fps=30,
        export_format="mp4",
    )
    assert render_req.project_id == proj_id

    render_res = VideoRenderContractResult(
        status="succeeded",
        resolution="1920x1080",
        fps=30,
        size_bytes=1048576,
    )
    assert render_res.size_bytes == 1048576
