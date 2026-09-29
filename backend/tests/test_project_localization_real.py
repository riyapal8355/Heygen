"""Integration tests for Real Project Localization with CTranslate2 and Brand Glossary.

Validates multi-scene neural translation, strict immutability of source projects,
fork vs in-place OCC versioning, SceneSpeech audio reset, SceneAvatar reset,
subtitle clearing, text layer translation, and glossary term preservation.
"""

import copy
import uuid
import pytest
from unittest.mock import patch

from app.ai.adapters.translation import RealCTranslate2TranslationProvider
from app.ai.registry import AIProviderRegistry
from app.core.exceptions import ConflictException
from app.models.brand import BrandGlossary, BrandGlossaryRule
from app.models.project import Project, ProjectVersion
from app.schemas.project_document import (
    ProjectDocumentV1,
    Scene,
    SceneAvatar,
    SceneLayer,
    SceneSpeech,
)
from app.services.project_localization_service import ProjectLocalizationService
from app.services.project_service import ProjectService


async def _create_real_multiscene_project(db_session, user_id, workspace_id) -> Project:
    project_service = ProjectService(db_session)
    project = Project(
        workspace_id=workspace_id,
        created_by=user_id,
        title="Annual Company Announcement",
        revision=1,
    )
    scenes = [
        Scene(
            id=str(uuid.uuid4()),
            sequence=1,
            duration=5.0,
            avatar=SceneAvatar(
                avatar_id="avatar-default-actor",
                look_id="suit-navy",
                video_asset_id=str(uuid.uuid4()),
            ),
            speech=SceneSpeech(
                voice_id="en_US-lessac-medium",
                script="Welcome everyone to our global conference.",
                audio_asset_id=str(uuid.uuid4()),
            ),
            subtitles=[{"id": 1, "start": 0.0, "end": 2.5, "text": "Welcome everyone"}],
            layers=[
                SceneLayer(
                    id="layer-title-1",
                    type="text",
                    name="Headline",
                    content={"text": "Global Conference 2026"},
                )
            ],
        ),
        Scene(
            id=str(uuid.uuid4()),
            sequence=2,
            duration=6.0,
            avatar=SceneAvatar(
                avatar_id="avatar-default-actor",
                look_id="suit-navy",
                video_asset_id=str(uuid.uuid4()),
            ),
            speech=SceneSpeech(
                voice_id="en_US-lessac-medium",
                script="HeyZen uses WorkComposer for seamless video production.",
                audio_asset_id=str(uuid.uuid4()),
            ),
            subtitles=[{"id": 1, "start": 0.0, "end": 3.0, "text": "HeyZen uses WorkComposer"}],
        ),
    ]
    doc = ProjectDocumentV1(
        schema_version=1,
        scenes=scenes,
        metadata={"title": "Annual Company Announcement", "language": "en"},
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
async def test_real_project_localization_creates_fork(db_session, test_user, test_workspace):
    """Verify translating with real CTranslate2 provider forks a new project preserving source."""
    orig_project = await _create_real_multiscene_project(db_session, test_user.id, test_workspace.id)

    # Set up custom AI registry with RealCTranslate2TranslationProvider
    registry = AIProviderRegistry()
    registry.register("translation", "ctranslate2", RealCTranslate2TranslationProvider(), is_default=True)
    service = ProjectLocalizationService(db_session, ai_registry=registry)

    forked_project, forked_version = await service.translate_project(
        project_id=orig_project.id,
        workspace_id=test_workspace.id,
        user_id=test_user.id,
        target_language="es",
        target_voice_id="es_ES-davefx-medium",
        create_fork=True,
    )

    # 1. Project identity separation
    assert forked_project.id != orig_project.id
    assert "ES" in forked_project.title
    assert forked_project.revision == 1

    # 2. Document inspection
    doc = ProjectDocumentV1.model_validate(forked_version.document)
    assert doc.metadata["language"] == "es"
    assert doc.metadata["localized_from"] == str(orig_project.id)
    assert len(doc.scenes) == 2

    for scene in doc.scenes:
        # Neural Spanish translation produced
        assert len(scene.speech.script) > 0
        assert not scene.speech.script.startswith("[ES]")  # Not mock!
        # Audio asset reset for target TTS re-synthesis
        assert scene.speech.audio_asset_id is None
        assert scene.speech.voice_id == "es_ES-davefx-medium"
        # Old original-language subtitles cleared
        assert scene.subtitles == []
        # Avatar video reset for target lip-sync re-generation
        if scene.avatar:
            assert scene.avatar.video_asset_id is None
            assert scene.avatar.avatar_id == "avatar-default-actor"

    # Text layer translated
    layer = doc.scenes[0].layers[0]
    assert "text" in layer.content
    assert len(layer.content["text"]) > 0

    # 3. Strict immutability of source project
    fresh_orig = await service.project_service.get_project(orig_project.id, test_workspace.id)
    assert fresh_orig.revision == 1
    orig_version = await service.project_service.get_version(
        fresh_orig.current_version_id, orig_project.id, test_workspace.id
    )
    orig_doc = ProjectDocumentV1.model_validate(orig_version.document)
    assert orig_doc.metadata["language"] == "en"
    assert orig_doc.scenes[0].speech.audio_asset_id is not None
    assert orig_doc.scenes[0].speech.script == "Welcome everyone to our global conference."


@pytest.mark.asyncio
async def test_real_project_localization_in_place_occ(db_session, test_user, test_workspace):
    """Verify translating with create_fork=False creates a new version under OCC revision control."""
    orig_project = await _create_real_multiscene_project(db_session, test_user.id, test_workspace.id)

    registry = AIProviderRegistry()
    registry.register("translation", "ctranslate2", RealCTranslate2TranslationProvider(), is_default=True)
    service = ProjectLocalizationService(db_session, ai_registry=registry)

    updated_project, new_version = await service.translate_project(
        project_id=orig_project.id,
        workspace_id=test_workspace.id,
        user_id=test_user.id,
        target_language="es",
        create_fork=False,
        expected_revision=1,
    )

    assert updated_project.id == orig_project.id
    assert updated_project.revision == 2
    assert new_version.revision == 2

    doc = ProjectDocumentV1.model_validate(new_version.document)
    assert doc.metadata["language"] == "es"
    assert doc.metadata["source_revision"] == 1


@pytest.mark.asyncio
async def test_real_project_localization_stale_revision_conflict(db_session, test_user, test_workspace):
    """Verify OCC conflict is raised if expected_revision does not match current project revision."""
    orig_project = await _create_real_multiscene_project(db_session, test_user.id, test_workspace.id)

    registry = AIProviderRegistry()
    registry.register("translation", "ctranslate2", RealCTranslate2TranslationProvider(), is_default=True)
    service = ProjectLocalizationService(db_session, ai_registry=registry)

    with pytest.raises(ConflictException) as exc_info:
        await service.translate_project(
            project_id=orig_project.id,
            workspace_id=test_workspace.id,
            user_id=test_user.id,
            target_language="es",
            create_fork=False,
            expected_revision=999,  # Stale revision
        )
    assert exc_info.value.code == "CONCURRENCY_CONFLICT"

    # Verify project revision remained unchanged
    fresh_orig = await service.project_service.get_project(orig_project.id, test_workspace.id)
    assert fresh_orig.revision == 1


@pytest.mark.asyncio
async def test_real_project_localization_brand_glossary_enforcement(db_session, test_user, test_workspace):
    """Verify Brand Glossary rules protect brand terms in multi-scene project localization."""
    # Create glossary with rules
    glossary = BrandGlossary(
        workspace_id=test_workspace.id,
        created_by=test_user.id,
        name="Spanish Enterprise Glossary",
        status="active",
    )
    db_session.add(glossary)
    await db_session.flush()

    rule1 = BrandGlossaryRule(
        glossary_id=glossary.id,
        source_term="HeyZen",
        preferred_term="HeyZen",
        target_language="es",
        status="active",
    )
    rule2 = BrandGlossaryRule(
        glossary_id=glossary.id,
        source_term="WorkComposer",
        preferred_term="WorkComposer",
        target_language="es",
        status="active",
    )
    db_session.add_all([rule1, rule2])
    await db_session.commit()

    orig_project = await _create_real_multiscene_project(db_session, test_user.id, test_workspace.id)

    registry = AIProviderRegistry()
    registry.register("translation", "ctranslate2", RealCTranslate2TranslationProvider(), is_default=True)
    service = ProjectLocalizationService(db_session, ai_registry=registry)

    forked_project, forked_version = await service.translate_project(
        project_id=orig_project.id,
        workspace_id=test_workspace.id,
        user_id=test_user.id,
        target_language="es",
        create_fork=True,
    )

    doc = ProjectDocumentV1.model_validate(forked_version.document)
    scene2_script = doc.scenes[1].speech.script
    assert "HeyZen" in scene2_script
    assert "WorkComposer" in scene2_script
