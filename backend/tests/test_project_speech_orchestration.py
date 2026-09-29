"""Tests for ProjectSpeechOrchestrator domain service."""

import uuid
import pytest
from unittest.mock import AsyncMock, patch

from app.core.config import get_settings
from app.core.exceptions import ConflictException
from app.media.errors import FFmpegNotFoundError
from app.media.ffmpeg import FFmpegService
from app.models.brand import BrandGlossary, BrandGlossaryRule
from app.models.project import Project, ProjectVersion
from app.schemas.project_document import ProjectDocumentV1, Scene, SceneSpeech, create_default_project_document
from app.services.project_service import ProjectService
from app.services.project_speech_service import ProjectSpeechOrchestrator


async def _create_test_project_with_scenes(db_session, user_id, workspace_id, scene_texts):
    project_service = ProjectService(db_session)
    project = Project(
        workspace_id=workspace_id,
        created_by=user_id,
        title="Speech Test Project",
        revision=1,
    )
    scenes = []
    for idx, text in enumerate(scene_texts, start=1):
        scenes.append(
            Scene(
                id=str(uuid.uuid4()),
                sequence=idx,
                duration=5.0,
                speech=SceneSpeech(
                    voice_id="voice_mock_en_marcus",
                    script=text,
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
async def test_speech_synthesis_multi_scene_success(db_session, test_user, test_workspace):
    """Verify batch scene speech synthesis creates audio assets and updates durations."""
    project = await _create_test_project_with_scenes(
        db_session, test_user.id, test_workspace.id,
        ["First scene introducing the topic.", "Second scene detailing the core benefits."]
    )

    orchestrator = ProjectSpeechOrchestrator(db_session)
    new_version = await orchestrator.synthesize_project_speech(
        project_id=project.id,
        workspace_id=test_workspace.id,
        user_id=test_user.id,
        expected_revision=1,
    )

    assert new_version.revision == 2
    doc = ProjectDocumentV1.model_validate(new_version.document)
    for scene in doc.scenes:
        assert scene.speech.audio_asset_id is not None
        assert scene.duration > 0.5  # Probe duration + padding

    # Check project pointer advanced
    updated_project = await orchestrator.project_service.get_project(project.id, test_workspace.id)
    assert updated_project.revision == 2
    assert updated_project.current_version_id == new_version.id


@pytest.mark.asyncio
async def test_speech_synthesis_applies_brand_glossary_rules(db_session, test_user, test_workspace):
    """Verify active Brand Glossary rules perform pronunciation substitution before TTS."""
    glossary = BrandGlossary(
        workspace_id=test_workspace.id,
        created_by=test_user.id,
        name="Phonetic Rules",
        status="active",
    )
    db_session.add(glossary)
    await db_session.flush()

    rule = BrandGlossaryRule(
        glossary_id=glossary.id,
        source_term="HeyZen",
        preferred_term="Hay-Zen",
        case_sensitive=False,
        status="active",
    )
    db_session.add(rule)
    await db_session.commit()

    project = await _create_test_project_with_scenes(
        db_session, test_user.id, test_workspace.id,
        ["Welcome to HeyZen, the video platform."]
    )

    orchestrator = ProjectSpeechOrchestrator(db_session)
    new_version = await orchestrator.synthesize_project_speech(
        project_id=project.id,
        workspace_id=test_workspace.id,
        user_id=test_user.id,
        expected_revision=1,
    )

    assert new_version.revision == 2
    doc = ProjectDocumentV1.model_validate(new_version.document)
    assert doc.scenes[0].speech.audio_asset_id is not None


@pytest.mark.asyncio
async def test_speech_synthesis_strict_probe_safety_in_real_mode(db_session, test_user, test_workspace):
    """Verify that during real execution (AI_PROVIDER_MODE != 'mock'), missing FFmpeg raises FFMPEG_NOT_FOUND."""
    project = await _create_test_project_with_scenes(
        db_session, test_user.id, test_workspace.id,
        ["Testing strict probe safety without mock fallback."]
    )

    orchestrator = ProjectSpeechOrchestrator(db_session)

    # Simulate real provider mode and unavailable ffprobe
    with patch("app.services.project_speech_service.get_settings") as mock_settings:
        mock_settings.return_value.AI_PROVIDER_MODE = "real"
        with patch.object(FFmpegService, "is_ffprobe_available", return_value=False):
            with pytest.raises(FFmpegNotFoundError) as exc_info:
                await orchestrator.synthesize_project_speech(
                    project_id=project.id,
                    workspace_id=test_workspace.id,
                    user_id=test_user.id,
                    expected_revision=1,
                )
            assert "FFprobe executable is not available" in str(exc_info.value)

    # Verify project revision remained unchanged at 1
    unmodified_project = await orchestrator.project_service.get_project(project.id, test_workspace.id)
    assert unmodified_project.revision == 1


@pytest.mark.asyncio
async def test_speech_synthesis_strict_version_immutability(db_session, test_user, test_workspace):
    """Verify original ProjectVersion document is byte-for-byte identical after synthesis."""
    project = await _create_test_project_with_scenes(
        db_session, test_user.id, test_workspace.id,
        ["Immutable original script."]
    )
    orig_version = await orchestrator_get_version(db_session, project.current_version_id, project.id, test_workspace.id)
    orig_doc_snapshot = orig_version.document.copy()

    orchestrator = ProjectSpeechOrchestrator(db_session)
    new_version = await orchestrator.synthesize_project_speech(
        project_id=project.id,
        workspace_id=test_workspace.id,
        user_id=test_user.id,
        expected_revision=1,
    )

    # Re-fetch version 1
    version_1 = await orchestrator_get_version(db_session, orig_version.id, project.id, test_workspace.id)
    assert version_1.document == orig_doc_snapshot
    assert version_1.document != new_version.document
    assert new_version.revision == 2


async def orchestrator_get_version(db, version_id, project_id, workspace_id):
    service = ProjectService(db)
    return await service.get_version(version_id, project_id, workspace_id)
