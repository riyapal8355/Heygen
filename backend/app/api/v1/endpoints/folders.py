"""Workspace Folder management API endpoints."""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_permission
from app.db.session import get_db
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.schemas.folder import FolderCreate, FolderResponse, FolderUpdate
from app.services.folder_service import FolderService

router = APIRouter(prefix="/workspaces/{workspace_id}/folders", tags=["Folders"])


@router.post(
    "",
    response_model=FolderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Folder",
    description="Creates a new organizational folder within the active workspace.",
)
async def create_folder(
    payload: FolderCreate,
    workspace_id: uuid.UUID = Path(..., description="Target Workspace UUID", examples=["22222222-2222-2222-2222-222222222222"]),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("folder.create")),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FolderResponse:
    workspace, _ = context
    service = FolderService(db)
    folder = await service.create_folder(
        workspace_id=workspace.id,
        user_id=current_user.id,
        name=payload.name,
        parent_id=payload.parent_id,
    )
    await db.commit()
    await db.refresh(folder)
    return FolderResponse.model_validate(folder)


@router.get(
    "",
    response_model=List[FolderResponse],
    summary="List Folders",
    description="Lists active folders in the workspace, optionally filtering by parent folder.",
)
async def list_folders(
    workspace_id: uuid.UUID = Path(..., description="Target Workspace UUID", examples=["22222222-2222-2222-2222-222222222222"]),
    parent_id: Optional[uuid.UUID] = Query(None, description="Filter by parent folder ID"),
    filter_parent: bool = Query(False, description="Whether to filter explicitly by parent_id"),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("folder.read")),
    db: AsyncSession = Depends(get_db),
) -> List[FolderResponse]:
    workspace, _ = context
    service = FolderService(db)
    folders = await service.list_folders(
        workspace_id=workspace.id,
        parent_id=parent_id,
        filter_parent=filter_parent,
    )
    return [FolderResponse.model_validate(f) for f in folders]


@router.get(
    "/{folder_id}",
    response_model=FolderResponse,
    summary="Get Folder",
    description="Fetches details of a specific workspace folder.",
)
async def get_folder(
    workspace_id: uuid.UUID = Path(..., description="Target Workspace UUID", examples=["22222222-2222-2222-2222-222222222222"]),
    folder_id: uuid.UUID = Path(..., description="Target Folder UUID", examples=["33333333-3333-3333-3333-333333333333"]),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("folder.read")),
    db: AsyncSession = Depends(get_db),
) -> FolderResponse:
    workspace, _ = context
    service = FolderService(db)
    folder = await service.get_folder(folder_id=folder_id, workspace_id=workspace.id)
    return FolderResponse.model_validate(folder)


@router.patch(
    "/{folder_id}",
    response_model=FolderResponse,
    summary="Update Folder",
    description="Renames or moves a folder to a new parent location.",
)
async def update_folder(
    payload: FolderUpdate,
    workspace_id: uuid.UUID = Path(..., description="Target Workspace UUID", examples=["22222222-2222-2222-2222-222222222222"]),
    folder_id: uuid.UUID = Path(..., description="Target Folder UUID", examples=["33333333-3333-3333-3333-333333333333"]),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("folder.update")),
    db: AsyncSession = Depends(get_db),
) -> FolderResponse:
    workspace, _ = context
    service = FolderService(db)
    update_parent = "parent_id" in payload.model_fields_set
    folder = await service.update_folder(
        folder_id=folder_id,
        workspace_id=workspace.id,
        name=payload.name,
        parent_id=payload.parent_id,
        update_parent=update_parent,
    )
    await db.commit()
    await db.refresh(folder)
    return FolderResponse.model_validate(folder)


@router.delete(
    "/{folder_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Folder",
    description="Soft-deletes an empty folder. Fails with 409 if folder contains children or projects.",
)
async def delete_folder(
    workspace_id: uuid.UUID = Path(..., description="Target Workspace UUID", examples=["22222222-2222-2222-2222-222222222222"]),
    folder_id: uuid.UUID = Path(..., description="Target Folder UUID", examples=["33333333-3333-3333-3333-333333333333"]),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("folder.delete")),
    db: AsyncSession = Depends(get_db),
) -> None:
    workspace, _ = context
    service = FolderService(db)
    await service.delete_folder(folder_id=folder_id, workspace_id=workspace.id)
    await db.commit()
