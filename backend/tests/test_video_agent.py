"""Tests for VideoAgentService prompt-to-project timeline generation."""

import uuid
import pytest
from app.db.seeds import AVATAR_ANNIE_ID
from app.models.brand import BrandKit
from app.models.user import User
from app.models.workspace import Workspace
from app.schemas.orchestration import GenerateProjectRequest
from app.schemas.project_document import ProjectDocumentV1
from app.services.video_agent_service import VideoAgentService


@pytest.mark.asyncio
async def test_video_agent_generates_valid_multi_scene_project(db_session, test_user, test_workspace):
    """Verify VideoAgent parses prompt into structured Project and baseline version."""
    service = VideoAgentService(db_session)
    req = GenerateProjectRequest(
        prompt="Create a high-energy product teaser for HeyZen video creation platform",
        target_duration_seconds=30.0,
        aspect_ratio="16:9",
        avatar_id=str(AVATAR_ANNIE_ID),
        voice_id="voice_mock_en_marcus",
        video_tone="Energetic",
        auto_synthesize_speech=False,
    )

    project, initial_version, job_id = await service.generate_project(
        workspace_id=test_workspace.id,
        user_id=test_user.id,
        request=req,
    )

    assert project.id is not None
    assert project.workspace_id == test_workspace.id
    assert project.created_by == test_user.id
    assert project.revision == 1
    assert project.status == "draft"
    assert project.width == 1920
    assert project.height == 1080
    assert project.aspect_ratio == "16:9"
    assert job_id is None

    # Validate document schema
    doc = ProjectDocumentV1.model_validate(initial_version.document)
    assert doc.schema_version == 1
    assert len(doc.scenes) >= 1
    assert doc.settings.aspect_ratio == "16:9"
    assert doc.settings.total_duration > 0

    first_scene = doc.scenes[0]
    assert first_scene.avatar is not None
    assert first_scene.avatar.avatar_id == str(AVATAR_ANNIE_ID)
    assert first_scene.speech is not None
    assert first_scene.speech.voice_id == "voice_mock_en_marcus"
    assert len(first_scene.speech.script) > 0


@pytest.mark.asyncio
async def test_video_agent_applies_brand_kit_colors(db_session, test_user, test_workspace):
    """Verify VideoAgent applies BrandKit background colors to scenes."""
    brand_kit = BrandKit(
        workspace_id=test_workspace.id,
        created_by=test_user.id,
        name="Tech Brand",
        colors={"primary": "#3B82F6", "background": "#1E293B"},
    )
    db_session.add(brand_kit)
    await db_session.commit()
    await db_session.refresh(brand_kit)

    service = VideoAgentService(db_session)
    req = GenerateProjectRequest(
        prompt="A branded corporate overview",
        aspect_ratio="9:16",
        brand_kit_id=brand_kit.id,
    )

    project, initial_version, _ = await service.generate_project(
        workspace_id=test_workspace.id,
        user_id=test_user.id,
        request=req,
    )

    assert project.width == 1080
    assert project.height == 1920
    doc = ProjectDocumentV1.model_validate(initial_version.document)
    for scene in doc.scenes:
        assert scene.background.value == "#1E293B"
