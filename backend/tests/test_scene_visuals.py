"""Tests for SceneVisualsOrchestrator domain service."""

import uuid
import pytest

from app.core.exceptions import (
    AIRuntimeUnavailableException,
    ConflictException,
    NotFoundException,
)
from app.models.project import Project, ProjectVersion
from app.schemas.orchestration import GenerateSceneVisualRequest
from app.schemas.project_document import ProjectDocumentV1, Scene
from app.services.project_service import ProjectService
from app.services.scene_visuals_service import SceneVisualsOrchestrator


async def _create_test_project_for_visuals(db_session, user_id, workspace_id):
    project_service = ProjectService(db_session)
    project = Project(
        workspace_id=workspace_id,
        created_by=user_id,
        title="Visuals Test Project",
        revision=1,
    )
    scene_id = str(uuid.uuid4())
    scenes = [
        Scene(
            id=scene_id,
            sequence=1,
            duration=5.0,
            background={"type": "color", "value": "#0F172A"},
        )
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
    saved_project = await project_service.repo.create_project_with_initial_version(project, version)
    return saved_project, scene_id


@pytest.mark.asyncio
async def test_generate_scene_image_success(db_session, test_user, test_workspace):
    """Verify generating background image creates Asset and updates scene in new version."""
    project, scene_id = await _create_test_project_for_visuals(db_session, test_user.id, test_workspace.id)

    orchestrator = SceneVisualsOrchestrator(db_session)
    req = GenerateSceneVisualRequest(
        visual_type="image",
        prompt="Modern minimalist corporate office backdrop",
        aspect_ratio="16:9",
        expected_revision=1,
        run_async=False,
    )

    new_version = await orchestrator.generate_scene_visual(
        project_id=project.id,
        workspace_id=test_workspace.id,
        user_id=test_user.id,
        scene_id=scene_id,
        request=req,
    )

    assert new_version.revision == 2
    doc = ProjectDocumentV1.model_validate(new_version.document)
    scene = doc.scenes[0]
    assert scene.background["type"] == "image"
    assert scene.background["asset_id"] is not None
    assert any(a.asset_id == scene.background["asset_id"] for a in doc.assets)


@pytest.mark.asyncio
async def test_generate_scene_video_success(db_session, test_user, test_workspace):
    """Verify generating b-roll video creates video Asset and updates scene."""
    project, scene_id = await _create_test_project_for_visuals(db_session, test_user.id, test_workspace.id)

    orchestrator = SceneVisualsOrchestrator(db_session)
    req = GenerateSceneVisualRequest(
        visual_type="video",
        prompt="Futuristic digital network abstract particles",
        aspect_ratio="16:9",
        expected_revision=1,
        run_async=False,
    )

    new_version = await orchestrator.generate_scene_visual(
        project_id=project.id,
        workspace_id=test_workspace.id,
        user_id=test_user.id,
        scene_id=scene_id,
        request=req,
    )

    assert new_version.revision == 2
    doc = ProjectDocumentV1.model_validate(new_version.document)
    scene = doc.scenes[0]
    assert scene.background["type"] == "video"
    assert scene.background["asset_id"] is not None


@pytest.mark.asyncio
async def test_generate_scene_visual_nonexistent_scene(db_session, test_user, test_workspace):
    """Verify requesting visual for unknown scene raises SCENE_NOT_FOUND (404)."""
    project, _ = await _create_test_project_for_visuals(db_session, test_user.id, test_workspace.id)

    orchestrator = SceneVisualsOrchestrator(db_session)
    req = GenerateSceneVisualRequest(
        visual_type="image",
        prompt="A sunset",
        expected_revision=1,
        run_async=False,
    )

    with pytest.raises(NotFoundException) as exc_info:
        await orchestrator.generate_scene_visual(
            project_id=project.id,
            workspace_id=test_workspace.id,
            user_id=test_user.id,
            scene_id="nonexistent-scene-999",
            request=req,
        )
    assert exc_info.value.code == "SCENE_NOT_FOUND"


@pytest.mark.asyncio
async def test_generate_scene_image_occ_conflict(db_session, test_user, test_workspace):
    """Verify stale expected_revision triggers OCC ConflictException (409)."""
    project, scene_id = await _create_test_project_for_visuals(db_session, test_user.id, test_workspace.id)

    orchestrator = SceneVisualsOrchestrator(db_session)
    req = GenerateSceneVisualRequest(
        visual_type="image",
        prompt="A sunset",
        expected_revision=99,  # Stale revision
        run_async=False,
        provider="mock",
    )

    with pytest.raises(ConflictException) as exc:
        await orchestrator.generate_scene_visual(
            project_id=project.id,
            workspace_id=test_workspace.id,
            user_id=test_user.id,
            scene_id=scene_id,
            request=req,
        )
    assert exc.value.code == "CONCURRENCY_CONFLICT"


@pytest.mark.asyncio
async def test_generate_scene_image_real_mode_cpu_guard(db_session, test_user, test_workspace):
    """Verify that requesting Stable Diffusion on CPU host raises GPU_UNAVAILABLE and does not mutate project."""
    from app.ai.hardware import detect_hardware
    hw = detect_hardware()

    if not hw.has_cuda:
        project, scene_id = await _create_test_project_for_visuals(db_session, test_user.id, test_workspace.id)

        orchestrator = SceneVisualsOrchestrator(db_session)
        req = GenerateSceneVisualRequest(
            visual_type="image",
            prompt="A futuristic neon skyline",
            aspect_ratio="16:9",
            expected_revision=1,
            run_async=False,
            provider="stable_diffusion",
        )

        with pytest.raises(AIRuntimeUnavailableException) as exc:
            await orchestrator.generate_scene_visual(
                project_id=project.id,
                workspace_id=test_workspace.id,
                user_id=test_user.id,
                scene_id=scene_id,
                request=req,
            )
        assert exc.value.code == "GPU_UNAVAILABLE"

        # Verify project version remains at 1 (zero partial mutation)
        project_service = ProjectService(db_session)
        current = await project_service.get_project(project.id, test_workspace.id)
        assert current.revision == 1

