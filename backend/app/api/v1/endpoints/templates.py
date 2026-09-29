"""Template and immutable TemplateVersion management API endpoints."""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Path, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_permission
from app.db.session import get_db
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.schemas.project import ProjectResponse
from app.schemas.template import (
    CreateTemplateRequest,
    CreateTemplateVersionRequest,
    TemplateResponse,
    TemplateVersionResponse,
    UpdateTemplateRequest,
)
from app.services.template_service import TemplateService

router = APIRouter(tags=["Templates"])


@router.post(
    "/templates",
    response_model=TemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Template",
    description="Initializes a new template with revision 1 immutable TemplateVersion.",
)
async def create_template(
    payload: CreateTemplateRequest,
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("template.create")),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TemplateResponse:
    workspace, _ = context
    service = TemplateService(db)
    template = await service.create_template(
        workspace_id=workspace.id,
        user_id=current_user.id,
        payload=payload,
    )
    await db.commit()
    return TemplateResponse.model_validate(template)


@router.get(
    "/templates",
    response_model=List[TemplateResponse],
    summary="List Templates",
    description="Lists active templates in the workspace.",
)
async def list_templates(
    category: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("template.read")),
    db: AsyncSession = Depends(get_db),
) -> List[TemplateResponse]:
    workspace, _ = context
    service = TemplateService(db)
    templates = await service.list_templates(
        workspace_id=workspace.id,
        category=category,
        status=status_filter,
        search=search,
        limit=limit,
        offset=offset,
    )
    return [TemplateResponse.model_validate(t) for t in templates]


@router.get(
    "/templates/{template_id}",
    response_model=TemplateResponse,
    summary="Get Template",
    description="Fetches a specific template and its active version snapshot.",
)
async def get_template(
    template_id: uuid.UUID = Path(..., description="Target Video Template UUID"),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("template.read")),
    db: AsyncSession = Depends(get_db),
) -> TemplateResponse:
    workspace, _ = context
    service = TemplateService(db)
    template = await service.get_template(template_id, workspace.id)
    return TemplateResponse.model_validate(template)


@router.patch(
    "/templates/{template_id}",
    response_model=TemplateResponse,
    summary="Update Template",
    description="Updates template metadata and settings without modifying historical version snapshots.",
)
async def update_template(
    payload: UpdateTemplateRequest,
    template_id: uuid.UUID = Path(..., description="Target Video Template UUID"),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("template.update")),
    db: AsyncSession = Depends(get_db),
) -> TemplateResponse:
    workspace, _ = context
    service = TemplateService(db)
    template = await service.update_template(template_id, workspace.id, payload)
    await db.commit()
    await db.refresh(template)
    return TemplateResponse.model_validate(template)


@router.delete(
    "/templates/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Template",
    description="Soft-deletes a template.",
)
async def delete_template(
    template_id: uuid.UUID = Path(..., description="Target Video Template UUID"),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("template.delete")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    workspace, _ = context
    service = TemplateService(db)
    await service.soft_delete_template(template_id, workspace.id)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# Immutable Template Version endpoints
@router.get(
    "/templates/{template_id}/versions",
    response_model=List[TemplateVersionResponse],
    summary="List Template Versions",
    description="Lists all immutable historical version snapshots of a template.",
)
async def list_template_versions(
    template_id: uuid.UUID = Path(..., description="Target Video Template UUID"),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("template.read")),
    db: AsyncSession = Depends(get_db),
) -> List[TemplateVersionResponse]:
    workspace, _ = context
    service = TemplateService(db)
    versions = await service.list_versions(template_id, workspace.id)
    return [TemplateVersionResponse.model_validate(v) for v in versions]


@router.post(
    "/templates/{template_id}/versions",
    response_model=TemplateVersionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Template Version",
    description="Creates a new immutable snapshot of the template document and bumps revision.",
)
async def create_template_version(
    payload: CreateTemplateVersionRequest,
    template_id: uuid.UUID = Path(..., description="Target Video Template UUID"),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("template.create")),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TemplateVersionResponse:
    workspace, _ = context
    service = TemplateService(db)
    version = await service.create_version(
        template_id=template_id,
        workspace_id=workspace.id,
        user_id=current_user.id,
        payload=payload,
    )
    await db.commit()
    return TemplateVersionResponse.model_validate(version)


@router.get(
    "/templates/{template_id}/versions/{version_id}",
    response_model=TemplateVersionResponse,
    summary="Get Template Version",
    description="Fetches a specific immutable version snapshot by ID.",
)
async def get_template_version(
    template_id: uuid.UUID = Path(..., description="Target Video Template UUID"),
    version_id: uuid.UUID = Path(..., description="Target Template Version UUID"),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("template.read")),
    db: AsyncSession = Depends(get_db),
) -> TemplateVersionResponse:
    workspace, _ = context
    service = TemplateService(db)
    version = await service.get_version(template_id, version_id, workspace.id)
    return TemplateVersionResponse.model_validate(version)


@router.post(
    "/templates/{template_id}/instantiate",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Instantiate Template",
    description="Instantiates a template into an active video project pre-populated with its document.",
)
async def instantiate_template(
    template_id: uuid.UUID = Path(..., description="Target Video Template UUID"),
    title: Optional[str] = Query(None, description="Optional custom title for the new project"),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("project.create")),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    workspace, _ = context
    service = TemplateService(db)
    project = await service.instantiate_template(
        template_id=template_id,
        workspace_id=workspace.id,
        user_id=current_user.id,
        title=title,
    )
    await db.commit()
    await db.refresh(project)
    return ProjectResponse.model_validate(project)

