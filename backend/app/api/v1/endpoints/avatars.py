"""Avatar and AvatarLook management API endpoints."""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Path, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_permission
from app.db.session import get_db
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.schemas.avatar import (
    AvatarLookResponse,
    AvatarResponse,
    CreateAvatarLookRequest,
    CreateAvatarRequest,
    UpdateAvatarLookRequest,
    UpdateAvatarRequest,
)
from app.models.avatar import Avatar, AvatarLook
from app.services.avatar_service import AvatarService
from app.storage.s3 import get_storage_provider

router = APIRouter(tags=["Avatars"])


async def _attach_avatar_urls(service: AvatarService, avatar: Avatar, resp: AvatarResponse, workspace_id: uuid.UUID) -> None:
    storage = get_storage_provider()
    target_asset_id = avatar.preview_asset_id or avatar.source_asset_id
    if target_asset_id:
        asset = await service.asset_repo.get_by_id(target_asset_id, workspace_id)
        if asset and asset.storage_key:
            resp.preview_url = storage.generate_download_url(asset.storage_key, expires_in_seconds=3600)
    if not resp.preview_url and avatar.provider_metadata:
        resp.preview_url = avatar.provider_metadata.get("preview_url") or avatar.provider_metadata.get("image_url")

    looks_list: List[AvatarLookResponse] = []
    for l in (avatar.looks or []):
        look_resp = AvatarLookResponse.model_validate(l)
        if l.preview_asset_id:
            look_asset = await service.asset_repo.get_by_id(l.preview_asset_id, workspace_id)
            if look_asset and look_asset.storage_key:
                look_resp.preview_url = storage.generate_download_url(look_asset.storage_key, expires_in_seconds=3600)
        if not look_resp.preview_url and isinstance(l.configuration, dict):
            look_resp.preview_url = l.configuration.get("preview_url") or l.configuration.get("image_url")
        looks_list.append(look_resp)
    resp.looks = looks_list


@router.post(
    "/avatars",
    response_model=AvatarResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Avatar",
    description="Initializes a new avatar in the active workspace.",
)
async def create_avatar(
    payload: CreateAvatarRequest,
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("avatar.create")),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AvatarResponse:
    workspace, _ = context
    service = AvatarService(db)
    avatar = await service.create_avatar(
        workspace_id=workspace.id,
        user_id=current_user.id,
        payload=payload,
    )
    await db.commit()
    return AvatarResponse.model_validate(avatar)


@router.get(
    "/avatars",
    response_model=List[AvatarResponse],
    summary="List Avatars",
    description="Lists active avatars in the active workspace.",
)
async def list_avatars(
    avatar_type: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("avatar.read")),
    db: AsyncSession = Depends(get_db),
) -> List[AvatarResponse]:
    workspace, _ = context
    service = AvatarService(db)
    avatars = await service.list_avatars(
        workspace_id=workspace.id,
        avatar_type=avatar_type,
        status=status_filter,
        search=search,
        limit=limit,
        offset=offset,
    )
    results = []
    for a in avatars:
        resp = AvatarResponse.model_validate(a)
        await _attach_avatar_urls(service, a, resp, workspace.id)
        results.append(resp)
    return results


@router.get(
    "/avatars/{avatar_id}",
    response_model=AvatarResponse,
    summary="Get Avatar",
    description="Fetches an avatar and its looks by ID.",
)
async def get_avatar(
    avatar_id: uuid.UUID = Path(..., description="Target Avatar UUID"),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("avatar.read")),
    db: AsyncSession = Depends(get_db),
) -> AvatarResponse:
    workspace, _ = context
    service = AvatarService(db)
    avatar = await service.get_avatar(avatar_id, workspace.id)
    resp = AvatarResponse.model_validate(avatar)
    await _attach_avatar_urls(service, avatar, resp, workspace.id)
    return resp


@router.patch(
    "/avatars/{avatar_id}",
    response_model=AvatarResponse,
    summary="Update Avatar",
    description="Updates avatar metadata, status, or asset references.",
)
async def update_avatar(
    payload: UpdateAvatarRequest,
    avatar_id: uuid.UUID = Path(..., description="Target Avatar UUID"),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("avatar.update")),
    db: AsyncSession = Depends(get_db),
) -> AvatarResponse:
    workspace, _ = context
    service = AvatarService(db)
    avatar = await service.update_avatar(avatar_id, workspace.id, payload)
    await db.commit()
    await db.refresh(avatar)
    return AvatarResponse.model_validate(avatar)


@router.delete(
    "/avatars/{avatar_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Avatar",
    description="Soft-deletes an avatar record.",
)
async def delete_avatar(
    avatar_id: uuid.UUID = Path(..., description="Target Avatar UUID"),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("avatar.delete")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    workspace, _ = context
    service = AvatarService(db)
    await service.soft_delete_avatar(avatar_id, workspace.id)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# Avatar Look sub-resource endpoints
@router.get(
    "/avatars/{avatar_id}/looks",
    response_model=List[AvatarLookResponse],
    summary="List Avatar Looks",
    description="Lists all visual presentation looks for an avatar.",
)
async def list_avatar_looks(
    avatar_id: uuid.UUID = Path(..., description="Target Avatar UUID"),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("avatar.read")),
    db: AsyncSession = Depends(get_db),
) -> List[AvatarLookResponse]:
    workspace, _ = context
    service = AvatarService(db)
    looks = await service.list_looks(avatar_id, workspace.id)
    storage = get_storage_provider()
    results = []
    for l in looks:
        look_resp = AvatarLookResponse.model_validate(l)
        if l.preview_asset_id:
            look_asset = await service.asset_repo.get_by_id(l.preview_asset_id, workspace.id)
            if look_asset and look_asset.storage_key:
                look_resp.preview_url = storage.generate_download_url(look_asset.storage_key, expires_in_seconds=3600)
        if not look_resp.preview_url and isinstance(l.configuration, dict):
            look_resp.preview_url = l.configuration.get("preview_url") or l.configuration.get("image_url")
        results.append(look_resp)
    return results


@router.post(
    "/avatars/{avatar_id}/looks",
    response_model=AvatarLookResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Avatar Look",
    description="Adds a new visual look/pose to an avatar.",
)
async def create_avatar_look(
    payload: CreateAvatarLookRequest,
    avatar_id: uuid.UUID = Path(..., description="Target Avatar UUID"),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("avatar.create")),
    db: AsyncSession = Depends(get_db),
) -> AvatarLookResponse:
    workspace, _ = context
    service = AvatarService(db)
    look = await service.create_look(avatar_id, workspace.id, payload)
    await db.commit()
    await db.refresh(look)
    return AvatarLookResponse.model_validate(look)


@router.get(
    "/avatars/{avatar_id}/looks/{look_id}",
    response_model=AvatarLookResponse,
    summary="Get Avatar Look",
    description="Fetches a specific avatar look by ID.",
)
async def get_avatar_look(
    avatar_id: uuid.UUID = Path(..., description="Target Avatar UUID"),
    look_id: uuid.UUID = Path(..., description="Target Avatar Look UUID"),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("avatar.read")),
    db: AsyncSession = Depends(get_db),
) -> AvatarLookResponse:
    workspace, _ = context
    service = AvatarService(db)
    look = await service.get_look(avatar_id, look_id, workspace.id)
    look_resp = AvatarLookResponse.model_validate(look)
    if look.preview_asset_id:
        storage = get_storage_provider()
        look_asset = await service.asset_repo.get_by_id(look.preview_asset_id, workspace.id)
        if look_asset and look_asset.storage_key:
            look_resp.preview_url = storage.generate_download_url(look_asset.storage_key, expires_in_seconds=3600)
    if not look_resp.preview_url and isinstance(look.configuration, dict):
        look_resp.preview_url = look.configuration.get("preview_url") or look.configuration.get("image_url")
    return look_resp


@router.patch(
    "/avatars/{avatar_id}/looks/{look_id}",
    response_model=AvatarLookResponse,
    summary="Update Avatar Look",
    description="Updates look configuration, styling, or preview asset.",
)
async def update_avatar_look(
    payload: UpdateAvatarLookRequest,
    avatar_id: uuid.UUID = Path(..., description="Target Avatar UUID"),
    look_id: uuid.UUID = Path(..., description="Target Avatar Look UUID"),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("avatar.update")),
    db: AsyncSession = Depends(get_db),
) -> AvatarLookResponse:
    workspace, _ = context
    service = AvatarService(db)
    look = await service.update_look(avatar_id, look_id, workspace.id, payload)
    await db.commit()
    await db.refresh(look)
    return AvatarLookResponse.model_validate(look)


@router.delete(
    "/avatars/{avatar_id}/looks/{look_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Avatar Look",
    description="Deletes a visual look from an avatar.",
)
async def delete_avatar_look(
    avatar_id: uuid.UUID = Path(..., description="Target Avatar UUID"),
    look_id: uuid.UUID = Path(..., description="Target Avatar Look UUID"),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("avatar.delete")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    workspace, _ = context
    service = AvatarService(db)
    await service.delete_look(avatar_id, look_id, workspace.id)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
