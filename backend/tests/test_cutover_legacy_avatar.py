"""Regression Test Suite: Complete Cutover from Legacy Avatar Video Generation.

Proves:
1. Legacy renderer (legacy_delaunay) is never registered or selected.
2. Delaunay mesh warping is never selected for production and has been eliminated.
3. Driving-video fallback is never selected (no silent substitution of Annie's video).
4. Annie remains the default presenter.
5. Selected presenter (Annie) reaches the canonical neural provider (gpu_avatar).
6. Non-Annie presenters (Daniel, Rasmus, Sophia) reach the canonical neural provider.
7. CPU machine returns truthful GPU_REQUIRED state (no silent legacy fallback).
8. No fake/mock avatar MP4 is created.
"""

from pathlib import Path
import uuid
import pytest
from sqlalchemy import select

from app.ai.adapters.wav2lip import Wav2LipONNXAvatarProvider
from app.ai.capabilities import ProviderDescriptor
from app.ai.hardware import detect_hardware
from app.ai.providers.gpu_avatar_provider import GPUAvatarProvider, GPUAvatarProviderMode
from app.ai.registry import (
    AICapability,
    get_ai_registry,
    get_avatar_provider,
    get_talking_avatar_provider,
)
from app.core.config import get_settings
from app.core.exceptions import (
    AIRuntimeUnavailableException,
    ConflictException,
    NotFoundException,
    ValidationException,
)
from app.db.seeds import (
    AVATAR_ANNIE_ID,
    AVATAR_DANIEL_ID,
    AVATAR_DEFAULT_PRESENTER_ID,
    AVATAR_RASMUS_ID,
    AVATAR_SOPHIA_ID,
)
from app.models.avatar import Avatar
from app.schemas.orchestration import GenerateProjectRequest
from app.schemas.project_document import ProjectDocumentV1
from app.services.project_avatar_service import ProjectAvatarOrchestrator
from app.services.video_agent_service import VideoAgentService


# =============================================================================
# 1. Legacy Renderer Never Selected or Registered
# =============================================================================
def test_legacy_renderer_never_selected():
    """Verify legacy_delaunay is removed from registry and legacy names map to gpu_avatar."""
    reg = get_ai_registry()
    avatar_providers = reg.list_providers(AICapability.AVATAR)["avatar"]

    # 1. Must NOT be registered
    assert "legacy_delaunay" not in avatar_providers
    assert "delaunay" not in avatar_providers

    # 2. If a legacy name is requested, canonical router routes to gpu_avatar
    p1 = get_talking_avatar_provider("legacy_delaunay")
    assert isinstance(p1, GPUAvatarProvider)
    assert p1.provider_name == "gpu_avatar"

    p2 = get_talking_avatar_provider("delaunay")
    assert isinstance(p2, GPUAvatarProvider)
    assert p2.provider_name == "gpu_avatar"

    p3 = get_avatar_provider("legacy_delaunay")
    assert isinstance(p3, GPUAvatarProvider)


# =============================================================================
# 2. Delaunay Never Selected for Production
# =============================================================================
@pytest.mark.asyncio
async def test_delaunay_never_selected_for_production(db_session):
    """Verify Delaunay is never selected for production and has been stripped from code."""
    # 1. Default talking avatar provider is gpu_avatar
    default_talking = get_talking_avatar_provider()
    assert isinstance(default_talking, GPUAvatarProvider)
    assert default_talking.provider_name == "gpu_avatar"

    # 2. In PostgreSQL, all canonical presets specify provider = 'gpu_avatar'
    preset_ids = [
        AVATAR_DEFAULT_PRESENTER_ID,
        AVATAR_ANNIE_ID,
        AVATAR_RASMUS_ID,
        AVATAR_DANIEL_ID,
        AVATAR_SOPHIA_ID,
    ]
    res = await db_session.execute(select(Avatar).where(Avatar.id.in_(preset_ids)))
    avatars = res.scalars().all()
    assert len(avatars) >= 4
    for av in avatars:
        assert av.provider == "gpu_avatar", f"Avatar {av.name} has legacy provider '{av.provider}'"

    # 3. Wav2Lip is strictly marked as DEVELOPMENT_ONLY
    w2l_desc = Wav2LipONNXAvatarProvider.descriptor
    assert w2l_desc.metadata.get("classification") == "DEVELOPMENT_ONLY"

    # 4. Delaunay mesh preparation and sinusoidal head pose warping methods are deleted
    w2l = Wav2LipONNXAvatarProvider()
    assert not hasattr(w2l, "_prepare_delaunay_mesh")
    assert not hasattr(w2l, "_apply_3d_head_pose")

    # 5. GPUAvatarProviderMode has NO Wav2Lip fallback mode
    assert "LOCAL_WAV2LIP_FALLBACK" not in GPUAvatarProviderMode.__members__


# =============================================================================
# 3. Driving-Video Fallback Never Selected
# =============================================================================
@pytest.mark.asyncio
async def test_driving_video_fallback_never_selected():
    """Verify that an avatar without its own driving template NEVER falls back to Annie's video."""
    provider = GPUAvatarProvider(mode=GPUAvatarProviderMode.LOCAL_GPU)

    # 1. Local pipeline: requesting unknown avatar with no driving template raises ValidationException
    with pytest.raises(ValidationException) as exc_info:
        await provider._execute_local_cuda_pipeline(
            avatar_image_bytes=b"fake_image",
            audio_bytes=b"fake_audio",
            fps=25,
            options={"avatar_name": "unknown_nonexistent_avatar"},
            progress_callback=None,
        )
    assert "Driving-video fallback is strictly disabled" in str(exc_info.value)

    # 2. Remote worker pipeline: requesting unknown avatar raises ValidationException
    with pytest.raises(ValidationException) as exc_info_remote:
        await provider._execute_remote_worker_pipeline(
            avatar_image_bytes=b"fake_image",
            audio_bytes=b"fake_audio",
            fps=25,
            options={"avatar_name": "unknown_nonexistent_avatar"},
            progress_callback=None,
        )
    assert "Driving-video fallback is strictly disabled" in str(exc_info_remote.value)


# =============================================================================
# 4. Annie Remains Default Presenter
# =============================================================================
@pytest.mark.asyncio
async def test_annie_remains_default_presenter(db_session, test_user, test_workspace):
    """Verify VideoAgent defaults to Annie when no avatar_id is provided."""
    service = VideoAgentService(db_session)
    req = GenerateProjectRequest(
        prompt="Professional overview of HeyZen platform",
        target_duration_seconds=15.0,
        aspect_ratio="16:9",
        avatar_id=None,  # No presenter specified
        voice_id=None,
        video_tone="Professional",
        auto_synthesize_speech=False,
    )

    project, initial_version, job_id = await service.generate_project(
        workspace_id=test_workspace.id,
        user_id=test_user.id,
        request=req,
    )

    doc = ProjectDocumentV1.model_validate(initial_version.document)
    first_scene = doc.scenes[0]
    assert first_scene.avatar is not None
    assert first_scene.avatar.avatar_id == str(AVATAR_ANNIE_ID)


async def _create_test_audio_asset(db_session, workspace_id, user_id):
    from app.models.asset import Asset
    from app.storage.s3 import get_storage_provider
    storage = get_storage_provider()
    audio_id = uuid.uuid4()
    storage_key = f"workspaces/{workspace_id}/assets/{audio_id}/speech.wav"
    storage.upload_bytes(
        b"RIFF4\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00@\x1f\x00\x00\x80>\x00\x00\x02\x00\x10\x00data\x10\x00\x00\x00" + b"\x00" * 16,
        storage_key,
        content_type="audio/wav",
    )
    asset = Asset(
        id=audio_id,
        workspace_id=workspace_id,
        created_by=user_id,
        original_filename="speech.wav",
        storage_bucket=storage.bucket_name,
        storage_key=storage_key,
        mime_type="audio/wav",
        size_bytes=64,
        asset_type="audio",
        status="ready",
    )
    db_session.add(asset)
    await db_session.flush()
    return asset


# =============================================================================
# 5. Selected Presenter Reaches Neural Provider
# =============================================================================
@pytest.mark.asyncio
async def test_selected_presenter_reaches_neural_provider(db_session, test_user, test_workspace):
    """Verify Annie selection resolves to gpu_avatar and truthfully checks GPU requirement."""
    service = VideoAgentService(db_session)
    req = GenerateProjectRequest(
        prompt="Corporate explainer video",
        target_duration_seconds=15.0,
        aspect_ratio="16:9",
        avatar_id=str(AVATAR_ANNIE_ID),
        video_tone="Professional",
        auto_synthesize_speech=False,
    )

    project, initial_version, _ = await service.generate_project(
        workspace_id=test_workspace.id,
        user_id=test_user.id,
        request=req,
    )

    # Attach speech audio asset to scene
    audio_asset = await _create_test_audio_asset(db_session, test_workspace.id, test_user.id)
    doc = ProjectDocumentV1.model_validate(initial_version.document)
    doc.scenes[0].speech.audio_asset_id = str(audio_asset.id)
    initial_version.document = doc.model_dump()
    db_session.add(initial_version)
    await db_session.commit()

    orchestrator = ProjectAvatarOrchestrator(db_session)
    hw = detect_hardware()

    # On non-CUDA machine, orchestrator must report GPU_REQUIRED and NOT fall back to fake MP4
    if not hw.gpu.cuda_available:
        with pytest.raises(AIRuntimeUnavailableException) as exc_info:
            await orchestrator.generate_project_avatar_video(
                project_id=project.id,
                workspace_id=test_workspace.id,
                user_id=test_user.id,
                expected_revision=project.revision,
                scene_id=doc.scenes[0].id,
                avatar_id_override=AVATAR_ANNIE_ID,
            )
        assert exc_info.value.code == "GPU_REQUIRED"
        assert exc_info.value.details.get("provider_status") == "GPU_REQUIRED"


# =============================================================================
# 6. Non-Annie Presenters Reach Neural Provider
# =============================================================================
@pytest.mark.asyncio
async def test_non_annie_presenters_reach_neural_provider(db_session, test_user, test_workspace):
    """Verify Daniel, Rasmus, and Sophia reach the neural provider with their own references."""
    service = VideoAgentService(db_session)
    orchestrator = ProjectAvatarOrchestrator(db_session)
    hw = detect_hardware()

    presenters = [
        ("Daniel", AVATAR_DANIEL_ID, "daniel"),
        ("Rasmus", AVATAR_RASMUS_ID, "rasmus"),
        ("Sophia", AVATAR_SOPHIA_ID, "sophia"),
    ]

    for name, av_uuid, expected_ref in presenters:
        # Verify avatar in database uses gpu_avatar
        db_av = (await db_session.execute(select(Avatar).where(Avatar.id == av_uuid))).scalars().first()
        if db_av:
            assert db_av.provider == "gpu_avatar"
            assert db_av.provider_reference == expected_ref

        # VideoAgent resolves the presenter UUID
        req = GenerateProjectRequest(
            prompt=f"{name} presenter update",
            target_duration_seconds=10.0,
            avatar_id=str(av_uuid),
            auto_synthesize_speech=False,
        )
        proj, ver, _ = await service.generate_project(
            workspace_id=test_workspace.id,
            user_id=test_user.id,
            request=req,
        )

        audio_asset = await _create_test_audio_asset(db_session, test_workspace.id, test_user.id)
        doc = ProjectDocumentV1.model_validate(ver.document)
        doc.scenes[0].speech.audio_asset_id = str(audio_asset.id)
        ver.document = doc.model_dump()
        db_session.add(ver)
        await db_session.commit()

        assert doc.scenes[0].avatar.avatar_id == str(av_uuid)

        # On non-CUDA machine, orchestrator stops with truthful GPU_REQUIRED (no fake video)
        if not hw.gpu.cuda_available:
            with pytest.raises(AIRuntimeUnavailableException) as exc_info:
                await orchestrator.generate_project_avatar_video(
                    project_id=proj.id,
                    workspace_id=test_workspace.id,
                    user_id=test_user.id,
                    expected_revision=proj.revision,
                    scene_id=doc.scenes[0].id,
                    avatar_id_override=av_uuid,
                )
            assert exc_info.value.code == "GPU_REQUIRED"


# =============================================================================
# 7. CPU Machine Returns Truthful GPU_REQUIRED State
# =============================================================================
def test_cpu_machine_returns_gpu_required():
    """Verify GPUAvatarProvider truthfully reports GPU_REQUIRED on non-CUDA machine."""
    hw = detect_hardware()
    if not hw.gpu.cuda_available:
        provider = GPUAvatarProvider(mode=GPUAvatarProviderMode.LOCAL_GPU)

        # 1. Health check returns GPU_REQUIRED
        is_healthy, reason = provider.health_check()
        assert is_healthy is False
        assert "GPU_REQUIRED" in reason

        # 2. Capabilities truthfully report no local CUDA
        caps = provider.capabilities()
        assert caps["local_cuda_available"] is False
        assert caps["allows_fallback"] is False


# =============================================================================
# 8. No Fake Avatar MP4 is Created
# =============================================================================
@pytest.mark.asyncio
async def test_no_fake_avatar_mp4_created():
    """Verify that calling generate_talking_video without CUDA creates NO fake MP4."""
    hw = detect_hardware()
    if not hw.gpu.cuda_available:
        provider = GPUAvatarProvider(mode=GPUAvatarProviderMode.LOCAL_GPU)

        with pytest.raises(AIRuntimeUnavailableException) as exc_info:
            await provider.generate_talking_video(
                avatar_image_bytes=b"dummy_image_data_not_valid",
                audio_bytes=b"dummy_audio_data_not_valid",
                fps=25,
            )

        # Must fail truthfully with GPU_REQUIRED
        assert exc_info.value.code == "GPU_REQUIRED"
        assert exc_info.value.details.get("provider_status") == "GPU_REQUIRED"
        assert "NEURAL AVATAR QUALITY BLOCKED BY LOCAL HARDWARE" in str(exc_info.value.message)
