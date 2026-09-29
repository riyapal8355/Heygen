"""Project lifecycle, canvas state, and versioning API endpoints."""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_permission
from app.db.session import get_db
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.schemas.project import (
    CreateProjectVersionRequest,
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
    ProjectVersionResponse,
)
from app.services.project_service import ProjectService

router = APIRouter(prefix="/workspaces/{workspace_id}/projects", tags=["Projects"])


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Project",
    description="Initializes a new video project with default ProjectDocumentV1 at revision 1.",
)
async def create_project(
    payload: ProjectCreate,
    workspace_id: uuid.UUID = Path(..., description="Target Workspace UUID", examples=["22222222-2222-2222-2222-222222222222"]),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("project.create")),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    workspace, _ = context
    service = ProjectService(db)
    project = await service.create_project(
        workspace_id=workspace.id,
        user_id=current_user.id,
        title=payload.title,
        folder_id=payload.folder_id,
        project_type=payload.project_type,
        aspect_ratio=payload.aspect_ratio,
        width=payload.width,
        height=payload.height,
        fps=payload.fps,
    )
    await db.commit()
    await db.refresh(project)
    return ProjectResponse.model_validate(project)


@router.get(
    "",
    response_model=List[ProjectResponse],
    summary="List Projects",
    description="Lists active projects in the workspace with optional folder, status, and title filtering.",
)
async def list_projects(
    workspace_id: uuid.UUID = Path(..., description="Target Workspace UUID", examples=["22222222-2222-2222-2222-222222222222"]),
    folder_id: Optional[uuid.UUID] = Query(None, description="Filter by folder ID"),
    filter_folder: bool = Query(False, description="Whether to filter explicitly by folder_id"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status: draft, processing, ready, archived"),
    search: Optional[str] = Query(None, description="Search by title keyword"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("project.read")),
    db: AsyncSession = Depends(get_db),
) -> List[ProjectResponse]:
    workspace, _ = context
    service = ProjectService(db)
    projects = await service.list_projects(
        workspace_id=workspace.id,
        folder_id=folder_id,
        filter_folder=filter_folder,
        status=status_filter,
        search=search,
        limit=limit,
        offset=offset,
    )
    return [ProjectResponse.model_validate(p) for p in projects]


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Get Project",
    description="Fetches metadata summary for a single project.",
)
async def get_project(
    workspace_id: uuid.UUID = Path(..., description="Target Workspace UUID", examples=["22222222-2222-2222-2222-222222222222"]),
    project_id: uuid.UUID = Path(..., description="Target Project UUID", examples=["44444444-4444-4444-4444-444444444444"]),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("project.read")),
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    workspace, _ = context
    service = ProjectService(db)
    project = await service.get_project(project_id=project_id, workspace_id=workspace.id)
    return ProjectResponse.model_validate(project)


@router.patch(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Update Project Metadata",
    description="Updates project title, folder assignment, status, or thumbnail poster.",
)
async def update_project(
    payload: ProjectUpdate,
    workspace_id: uuid.UUID = Path(..., description="Target Workspace UUID", examples=["22222222-2222-2222-2222-222222222222"]),
    project_id: uuid.UUID = Path(..., description="Target Project UUID", examples=["44444444-4444-4444-4444-444444444444"]),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("project.update")),
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    workspace, _ = context
    service = ProjectService(db)
    update_folder = "folder_id" in payload.model_fields_set
    update_thumb = "thumbnail_asset_id" in payload.model_fields_set
    project = await service.update_project(
        project_id=project_id,
        workspace_id=workspace.id,
        title=payload.title,
        folder_id=payload.folder_id,
        update_folder=update_folder,
        status=payload.status,
        aspect_ratio=payload.aspect_ratio,
        thumbnail_asset_id=payload.thumbnail_asset_id,
        update_thumbnail=update_thumb,
    )
    await db.commit()
    await db.refresh(project)
    return ProjectResponse.model_validate(project)


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Project",
    description="Soft-deletes a project and removes it from normal query results.",
)
async def delete_project(
    workspace_id: uuid.UUID = Path(..., description="Target Workspace UUID", examples=["22222222-2222-2222-2222-222222222222"]),
    project_id: uuid.UUID = Path(..., description="Target Project UUID", examples=["44444444-4444-4444-4444-444444444444"]),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("project.delete")),
    db: AsyncSession = Depends(get_db),
) -> None:
    workspace, _ = context
    service = ProjectService(db)
    await service.delete_project(project_id=project_id, workspace_id=workspace.id)
    await db.commit()


# Versioning Sub-Endpoints


@router.get(
    "/{project_id}/versions",
    response_model=List[ProjectVersionResponse],
    tags=["Projects", "Studio"],
    summary="List Project Versions",
    description="Lists chronological version history snapshots for a project.",
)
async def list_project_versions(
    workspace_id: uuid.UUID = Path(..., description="Target Workspace UUID", examples=["22222222-2222-2222-2222-222222222222"]),
    project_id: uuid.UUID = Path(..., description="Target Project UUID", examples=["44444444-4444-4444-4444-444444444444"]),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("project.read")),
    db: AsyncSession = Depends(get_db),
) -> List[ProjectVersionResponse]:
    workspace, _ = context
    service = ProjectService(db)
    versions = await service.list_versions(
        project_id=project_id,
        workspace_id=workspace.id,
        limit=limit,
        offset=offset,
    )
    return [ProjectVersionResponse.model_validate(v) for v in versions]


@router.get(
    "/{project_id}/versions/latest",
    response_model=ProjectVersionResponse,
    tags=["Projects", "Studio"],
    summary="Get Latest Project Version Snapshot",
    description="Fetches full ProjectDocument JSON for the latest project version snapshot.",
)
async def get_latest_project_version(
    workspace_id: uuid.UUID = Path(..., description="Target Workspace UUID", examples=["22222222-2222-2222-2222-222222222222"]),
    project_id: uuid.UUID = Path(..., description="Target Project UUID", examples=["44444444-4444-4444-4444-444444444444"]),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("project.read")),
    db: AsyncSession = Depends(get_db),
) -> ProjectVersionResponse:
    workspace, _ = context
    service = ProjectService(db)
    project = await service.get_project(project_id=project_id, workspace_id=workspace.id)
    if not project or not project.current_version_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Project or version not found")
    version = await service.get_version(
        version_id=project.current_version_id,
        project_id=project_id,
        workspace_id=workspace.id,
    )
    return ProjectVersionResponse.model_validate(version)


@router.get(
    "/{project_id}/versions/{version_id}",
    response_model=ProjectVersionResponse,
    tags=["Projects", "Studio"],
    summary="Get Project Version Snapshot",
    description="Fetches full ProjectDocument JSON for an immutable version snapshot.",
)
async def get_project_version(
    workspace_id: uuid.UUID = Path(..., description="Target Workspace UUID", examples=["22222222-2222-2222-2222-222222222222"]),
    project_id: uuid.UUID = Path(..., description="Target Project UUID", examples=["44444444-4444-4444-4444-444444444444"]),
    version_id: uuid.UUID = Path(..., description="Target Project Version UUID", examples=["55555555-5555-5555-5555-555555555555"]),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("project.read")),
    db: AsyncSession = Depends(get_db),
) -> ProjectVersionResponse:
    workspace, _ = context
    service = ProjectService(db)
    version = await service.get_version(
        version_id=version_id,
        project_id=project_id,
        workspace_id=workspace.id,
    )
    return ProjectVersionResponse.model_validate(version)


@router.post(
    "/{project_id}/versions",
    response_model=ProjectVersionResponse,
    tags=["Projects", "Studio"],
    status_code=status.HTTP_201_CREATED,
    summary="Save New Project Version (Optimistic Concurrency)",
    description="Saves a new immutable project version. Fails with 409 Conflict if expected_revision does not match.",
)
async def create_project_version(
    payload: CreateProjectVersionRequest,
    workspace_id: uuid.UUID = Path(..., description="Target Workspace UUID", examples=["22222222-2222-2222-2222-222222222222"]),
    project_id: uuid.UUID = Path(..., description="Target Project UUID", examples=["44444444-4444-4444-4444-444444444444"]),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("project.update")),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectVersionResponse:
    workspace, _ = context
    service = ProjectService(db)
    version = await service.create_version(
        project_id=project_id,
        workspace_id=workspace.id,
        user_id=current_user.id,
        expected_revision=payload.expected_revision,
        document=payload.document,
        source=payload.source or "manual",
    )
    await db.commit()
    await db.refresh(version)
    return ProjectVersionResponse.model_validate(version)
