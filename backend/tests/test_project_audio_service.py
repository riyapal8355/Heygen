"""Tests for ProjectAudioOrchestrator domain service and OCC integration."""

import uuid
import pytest

from app.core.exceptions import ConflictException, NotFoundException
from app.models.project import Project, ProjectVersion
from app.schemas.project_document import ProjectDocumentV1, Scene, SceneSpeech
from app.services.asset_lifecycle import AssetLifecycleManager
from app.services.project_audio_service import ProjectAudioOrchestrator
from app.services.project_service import ProjectService


def _generate_synthetic_wav(duration_seconds: float = 2.0, sample_rate: int = 48000) -> bytes:
    import io
    import math
    import struct
    import wave
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        total_samples = int(duration_seconds * sample_rate)
        samples = [int(16000 * math.sin(2 * math.pi * 440 * (i / sample_rate))) for i in range(total_samples)]
        wf.writeframes(struct.pack(f"<{len(samples)}h", *samples))
    return buf.getvalue()


async def _create_test_project_with_audio(db_session, user_id, workspace_id, scene_count=2):
    project_service = ProjectService(db_session)
    asset_mgr = AssetLifecycleManager(db_session)

    project = Project(
        workspace_id=workspace_id,
        created_by=user_id,
        title="Audio Enhance Test Project",
        revision=1,
    )

    scenes = []
    for idx in range(1, scene_count + 1):
        raw_wav = _generate_synthetic_wav(duration_seconds=3.0)
        asset = await asset_mgr.ingest_generated_asset(
            workspace_id=workspace_id,
            created_by=user_id,
            content=raw_wav,
            original_filename=f"scene_{idx}_audio.wav",
            asset_type="audio",
            mime_type="audio/wav",
            metadata={"test": True},
        )
        scenes.append(
            Scene(
                id=f"scene_{idx}",
                sequence=idx,
                duration=3.0,
                speech=SceneSpeech(
                    voice_id="voice_mock_en_marcus",
                    script=f"Scene text {idx}",
                    audio_asset_id=str(asset.id),
                ),
            )
        )

    doc = ProjectDocumentV1(
        schema_version=1,
        scenes=scenes,
    )
    version = ProjectVersion(
        project_id=project.id,
        revision=1,
        document=doc.model_dump(),
        created_by=user_id,
        source="initial",
    )
    return await project_service.repo.create_project_with_initial_version(project, version)


@pytest.mark.asyncio
async def test_enhance_project_speech_multi_scene_success(db_session, test_user, test_workspace):
    """Verify batch speech enhancement creates enhanced assets, updates scenes, and commits new version."""
    project = await _create_test_project_with_audio(db_session, test_user.id, test_workspace.id, scene_count=2)

    orchestrator = ProjectAudioOrchestrator(db_session)
    new_version, meta = await orchestrator.enhance_project_speech(
        project_id=project.id,
        workspace_id=test_workspace.id,
        user_id=test_user.id,
        expected_revision=1,
        denoise=True,
        remove_silence=False,
        remove_fillers=False,
        master_audio=True,
        provider_override="mock",
    )

    assert new_version.revision == 2
    assert meta["scenes_enhanced"] == 2
    assert meta["revision"] == 2

    doc = ProjectDocumentV1.model_validate(new_version.document)
    for scene in doc.scenes:
        assert scene.speech.audio_asset_id is not None
        assert scene.duration > 0.0

    # Verify project pointer in DB
    updated_project = await orchestrator.project_service.get_project(project.id, test_workspace.id)
    assert updated_project.revision == 2
    assert updated_project.current_version_id == new_version.id


@pytest.mark.asyncio
async def test_enhance_project_speech_occ_conflict(db_session, test_user, test_workspace):
    """Verify optimistic concurrency conflict raises ConflictException."""
    project = await _create_test_project_with_audio(db_session, test_user.id, test_workspace.id, scene_count=1)

    orchestrator = ProjectAudioOrchestrator(db_session)
    with pytest.raises(ConflictException) as exc_info:
        await orchestrator.enhance_project_speech(
            project_id=project.id,
            workspace_id=test_workspace.id,
            user_id=test_user.id,
            expected_revision=999,  # Stale revision
            provider_override="mock",
        )
    assert "Revision conflict" in str(exc_info.value)


@pytest.mark.asyncio
async def test_enhance_project_speech_workspace_isolation(db_session, test_user, test_workspace):
    """Verify cross-workspace access is rejected with NotFoundException."""
    project = await _create_test_project_with_audio(db_session, test_user.id, test_workspace.id, scene_count=1)
    other_workspace_id = uuid.uuid4()

    orchestrator = ProjectAudioOrchestrator(db_session)
    with pytest.raises(NotFoundException):
        await orchestrator.enhance_project_speech(
            project_id=project.id,
            workspace_id=other_workspace_id,
            user_id=test_user.id,
            expected_revision=1,
            provider_override="mock",
        )


@pytest.mark.asyncio
async def test_enhance_project_speech_selective_scene(db_session, test_user, test_workspace):
    """Verify selective scene enhancement updates only the targeted scene."""
    project = await _create_test_project_with_audio(db_session, test_user.id, test_workspace.id, scene_count=2)

    orchestrator = ProjectAudioOrchestrator(db_session)
    new_version, meta = await orchestrator.enhance_project_speech(
        project_id=project.id,
        workspace_id=test_workspace.id,
        user_id=test_user.id,
        expected_revision=1,
        scene_id="scene_1",
        provider_override="mock",
    )

    assert new_version.revision == 2
    assert meta["scenes_enhanced"] == 1
    assert meta["details"][0]["scene_id"] == "scene_1"
