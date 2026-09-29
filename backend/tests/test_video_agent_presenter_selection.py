"""Comprehensive verification of Video Agent Presenter Selection and Validation requirements."""

import uuid
import pytest
from sqlalchemy import select

from app.core.exceptions import NotFoundException, ConflictException
from app.db.seeds import AVATAR_ANNIE_ID, AVATAR_DANIEL_ID, AVATAR_RASMUS_ID
from app.models.avatar import Avatar
from app.models.project import Project, ProjectVersion
from app.models.workspace import Workspace
from app.schemas.orchestration import GenerateProjectRequest
from app.schemas.project_document import ProjectDocumentV1
from app.services.video_agent_service import VideoAgentService


@pytest.mark.asyncio
async def test_default_presenter_selection_is_annie(db_session, test_user, test_workspace):
    """Requirement 1: Default presenter remains Annie, and existing Annie behavior does not change."""
    service = VideoAgentService(db_session)
    req = GenerateProjectRequest(
        prompt="Create a professional company overview video",
        target_duration_seconds=20.0,
        aspect_ratio="16:9",
        avatar_id=None,  # No avatar specified -> default must be Annie
    )

    project, initial_version, _ = await service.generate_project(
        workspace_id=test_workspace.id,
        user_id=test_user.id,
        request=req,
    )

    doc = ProjectDocumentV1.model_validate(initial_version.document)
    assert len(doc.scenes) >= 1
    for sc in doc.scenes:
        assert sc.avatar is not None
        assert sc.avatar.avatar_id == str(AVATAR_ANNIE_ID)

    # Verify presenter persisted in project metadata
    assert doc.metadata is not None
    presenter_meta = doc.metadata.get("presenter")
    assert presenter_meta is not None
    assert presenter_meta["avatar_id"] == str(AVATAR_ANNIE_ID)
    assert "Annie" in presenter_meta["name"]
    assert doc.metadata.get("avatar_id") == str(AVATAR_ANNIE_ID)
    assert "Annie" in doc.metadata.get("avatar_name", "")


@pytest.mark.asyncio
async def test_non_annie_presenter_selection_daniel(db_session, test_user, test_workspace):
    """Requirement 3 & 5: Selecting non-Annie presenter (Daniel) resolves real record and persists in ProjectVersion."""
    service = VideoAgentService(db_session)
    req = GenerateProjectRequest(
        prompt="A dynamic product demo for tech creators",
        target_duration_seconds=20.0,
        aspect_ratio="16:9",
        avatar_id=str(AVATAR_DANIEL_ID),  # Daniel selected
    )

    project, initial_version, _ = await service.generate_project(
        workspace_id=test_workspace.id,
        user_id=test_user.id,
        request=req,
    )

    doc = ProjectDocumentV1.model_validate(initial_version.document)
    assert len(doc.scenes) >= 1
    for sc in doc.scenes:
        assert sc.avatar is not None
        assert sc.avatar.avatar_id == str(AVATAR_DANIEL_ID)
        assert sc.avatar.avatar_id != str(AVATAR_ANNIE_ID)

    # Verify presenter metadata in ProjectVersion
    presenter_meta = doc.metadata.get("presenter")
    assert presenter_meta is not None
    assert presenter_meta["avatar_id"] == str(AVATAR_DANIEL_ID)
    assert "Daniel" in presenter_meta["name"]
    assert presenter_meta["provider_reference"] == "daniel"
    assert doc.metadata.get("avatar_id") == str(AVATAR_DANIEL_ID)
    assert "Daniel" in doc.metadata.get("avatar_name", "")


@pytest.mark.asyncio
async def test_non_annie_presenter_selection_rasmus(db_session, test_user, test_workspace):
    """Requirement 3 & 5: Selecting Rasmus resolves real record and does NOT fall back to Annie."""
    service = VideoAgentService(db_session)
    req = GenerateProjectRequest(
        prompt="Executive quarterly report",
        target_duration_seconds=15.0,
        aspect_ratio="16:9",
        avatar_id=str(AVATAR_RASMUS_ID),  # Rasmus selected
    )

    project, initial_version, _ = await service.generate_project(
        workspace_id=test_workspace.id,
        user_id=test_user.id,
        request=req,
    )

    doc = ProjectDocumentV1.model_validate(initial_version.document)
    for sc in doc.scenes:
        assert sc.avatar is not None
        assert sc.avatar.avatar_id == str(AVATAR_RASMUS_ID)
        assert sc.avatar.avatar_id != str(AVATAR_ANNIE_ID)

    assert doc.metadata["presenter"]["avatar_id"] == str(AVATAR_RASMUS_ID)
    assert "Rasmus" in doc.metadata["presenter"]["name"]


@pytest.mark.asyncio
async def test_custom_workspace_presenter_selection(db_session, test_user, test_workspace):
    """Requirement 4: Verify custom avatar created in workspace resolves and is used."""
    # Create custom workspace avatar
    custom_avatar = Avatar(
        workspace_id=test_workspace.id,
        created_by=test_user.id,
        name="Custom CEO Digital Twin",
        avatar_type="custom",
        status="ready",
        visibility="workspace",
        provider="wav2lip",
        provider_reference="custom_ceo",
    )
    db_session.add(custom_avatar)
    await db_session.commit()
    await db_session.refresh(custom_avatar)

    service = VideoAgentService(db_session)
    req = GenerateProjectRequest(
        prompt="Company annual keynote address",
        aspect_ratio="16:9",
        avatar_id=str(custom_avatar.id),
    )

    project, initial_version, _ = await service.generate_project(
        workspace_id=test_workspace.id,
        user_id=test_user.id,
        request=req,
    )

    doc = ProjectDocumentV1.model_validate(initial_version.document)
    for sc in doc.scenes:
        assert sc.avatar is not None
        assert sc.avatar.avatar_id == str(custom_avatar.id)

    assert doc.metadata["presenter"]["avatar_id"] == str(custom_avatar.id)
    assert doc.metadata["presenter"]["name"] == "Custom CEO Digital Twin"


@pytest.mark.asyncio
async def test_unavailable_presenter_returns_truthful_error_no_silent_fallback(db_session, test_user, test_workspace):
    """Requirement 4: Non-existent presenter returns truthful error and does NOT silently fall back to Annie."""
    service = VideoAgentService(db_session)
    fake_avatar_id = str(uuid.uuid4())

    req = GenerateProjectRequest(
        prompt="This request has an unavailable presenter ID",
        aspect_ratio="16:9",
        avatar_id=fake_avatar_id,
    )

    with pytest.raises(NotFoundException) as exc_info:
        await service.generate_project(
            workspace_id=test_workspace.id,
            user_id=test_user.id,
            request=req,
        )

    assert exc_info.value.code == "AVATAR_NOT_FOUND"
    assert fake_avatar_id in exc_info.value.message


@pytest.mark.asyncio
async def test_foreign_workspace_private_presenter_rejected(db_session, test_user, test_workspace):
    """Requirement 4: Private avatar in foreign workspace cannot be accessed by another workspace."""
    foreign_ws = Workspace(
        name="Foreign Workspace",
        slug=f"foreign-ws-{uuid.uuid4().hex[:8]}",
        owner_id=test_user.id,
    )
    db_session.add(foreign_ws)
    await db_session.commit()
    await db_session.refresh(foreign_ws)

    foreign_avatar = Avatar(
        workspace_id=foreign_ws.id,
        created_by=test_user.id,
        name="Private Confidential Avatar",
        avatar_type="custom",
        status="ready",
        visibility="workspace",  # Private to foreign workspace
        provider="wav2lip",
    )
    db_session.add(foreign_avatar)
    await db_session.commit()
    await db_session.refresh(foreign_avatar)

    service = VideoAgentService(db_session)
    req = GenerateProjectRequest(
        prompt="Attempting to access foreign private presenter",
        aspect_ratio="16:9",
        avatar_id=str(foreign_avatar.id),
    )

    with pytest.raises(NotFoundException) as exc_info:
        await service.generate_project(
            workspace_id=test_workspace.id,
            user_id=test_user.id,
            request=req,
        )

    assert exc_info.value.code == "AVATAR_NOT_FOUND"
