"""Tests for ProjectLocalizationService domain service."""

import uuid
import pytest

from app.models.brand import BrandGlossary, BrandGlossaryRule
from app.models.project import Project, ProjectVersion
from app.schemas.project_document import ProjectDocumentV1, Scene, SceneSpeech
from app.services.project_localization_service import ProjectLocalizationService
from app.services.project_service import ProjectService


async def _create_test_project_for_translation(db_session, user_id, workspace_id):
    project_service = ProjectService(db_session)
    project = Project(
        workspace_id=workspace_id,
        created_by=user_id,
        title="Localization Base Project",
        revision=1,
    )
    scenes = [
        Scene(
            id=str(uuid.uuid4()),
            sequence=1,
            duration=5.0,
            speech=SceneSpeech(
                voice_id="voice_mock_en_marcus",
                script="Hello and welcome to our enterprise software.",
                audio_asset_id=str(uuid.uuid4()),
            ),
        ),
        Scene(
            id=str(uuid.uuid4()),
            sequence=2,
            duration=6.0,
            speech=SceneSpeech(
                voice_id="voice_mock_en_marcus",
                script="Discover why companies choose HeyZen worldwide.",
                audio_asset_id=str(uuid.uuid4()),
            ),
        ),
    ]
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
async def test_project_localization_creates_fork(db_session, test_user, test_workspace):
    """Verify translating with create_fork=True creates a distinct Project entity."""
    orig_project = await _create_test_project_for_translation(db_session, test_user.id, test_workspace.id)

    service = ProjectLocalizationService(db_session)
    forked_project, forked_version = await service.translate_project(
        project_id=orig_project.id,
        workspace_id=test_workspace.id,
        user_id=test_user.id,
        target_language="es",
        target_voice_id="voice_mock_es_mateo",
        create_fork=True,
    )

    assert forked_project.id != orig_project.id
    assert "ES" in forked_project.title
    assert forked_project.revision == 1

    doc = ProjectDocumentV1.model_validate(forked_version.document)
    for scene in doc.scenes:
        assert "[ES]" in scene.speech.script
        assert scene.speech.voice_id == "voice_mock_es_mateo"
        assert scene.speech.audio_asset_id is None  # Reset for re-synthesis in target language

    # Original project unaffected
    fresh_orig = await service.project_service.get_project(orig_project.id, test_workspace.id)
    assert fresh_orig.revision == 1


@pytest.mark.asyncio
async def test_project_localization_in_place_version(db_session, test_user, test_workspace):
    """Verify translating with create_fork=False creates a new version on the same project."""
    orig_project = await _create_test_project_for_translation(db_session, test_user.id, test_workspace.id)

    service = ProjectLocalizationService(db_session)
    updated_project, new_version = await service.translate_project(
        project_id=orig_project.id,
        workspace_id=test_workspace.id,
        user_id=test_user.id,
        target_language="fr",
        create_fork=False,
        expected_revision=1,
    )

    assert updated_project.id == orig_project.id
    assert updated_project.revision == 2
    assert new_version.revision == 2

    doc = ProjectDocumentV1.model_validate(new_version.document)
    assert "[FR]" in doc.scenes[0].speech.script


@pytest.mark.asyncio
async def test_project_localization_applies_glossary_rules(db_session, test_user, test_workspace):
    """Verify terminology rules for target language are passed to translation."""
    glossary = BrandGlossary(
        workspace_id=test_workspace.id,
        created_by=test_user.id,
        name="Spanish Terms",
        status="active",
    )
    db_session.add(glossary)
    await db_session.flush()

    rule = BrandGlossaryRule(
        glossary_id=glossary.id,
        source_term="enterprise",
        preferred_term="empresarial",
        target_language="es",
        status="active",
    )
    db_session.add(rule)
    await db_session.commit()

    orig_project = await _create_test_project_for_translation(db_session, test_user.id, test_workspace.id)

    service = ProjectLocalizationService(db_session)
    forked_project, forked_version = await service.translate_project(
        project_id=orig_project.id,
        workspace_id=test_workspace.id,
        user_id=test_user.id,
        target_language="es",
        create_fork=True,
    )

    doc = ProjectDocumentV1.model_validate(forked_version.document)
    assert "empresarial" in doc.scenes[0].speech.script
