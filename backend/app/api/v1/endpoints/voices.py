"""Voice catalog management API endpoints."""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Path, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_permission
from app.core.exceptions import NotFoundException
from app.db.session import get_db
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.schemas.voice import CreateVoiceRequest, UpdateVoiceRequest, VoicePreviewResponse, VoiceResponse
from app.schemas.voice_clone import VoiceCloneJobResponse, VoiceCloneRequest
from app.services.voice_service import VoiceService
from app.storage.s3 import get_storage_provider

router = APIRouter(tags=["Voices", "Audio"])


@router.post(
    "/workspaces/{workspace_id}/voices/clone",
    response_model=VoiceCloneJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Clone Voice (Workspace-scoped)",
    description="Initiates asynchronous zero-shot voice cloning from a reference audio asset in the workspace.",
)
async def clone_voice_workspace(
    payload: VoiceCloneRequest,
    workspace_id: uuid.UUID = Path(..., description="Target Workspace UUID", examples=["22222222-2222-2222-2222-222222222222"]),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("voice.create")),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> VoiceCloneJobResponse:
    workspace, _ = context
    service = VoiceService(db)
    return await service.clone_voice_intent(
        workspace_id=workspace.id,
        user_id=current_user.id,
        payload=payload,
    )


@router.post(
    "/voices/clone",
    response_model=VoiceCloneJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Clone Voice (Header-scoped)",
    description="Initiates asynchronous zero-shot voice cloning from a reference audio asset.",
)
async def clone_voice_header(
    payload: VoiceCloneRequest,
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("voice.create")),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> VoiceCloneJobResponse:
    workspace, _ = context
    service = VoiceService(db)
    return await service.clone_voice_intent(
        workspace_id=workspace.id,
        user_id=current_user.id,
        payload=payload,
    )


@router.post(
    "/voices",
    response_model=VoiceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Voice",
    description="Registers a new speech synthesis voice in the workspace.",
)
async def create_voice(
    payload: CreateVoiceRequest,
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("voice.create")),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> VoiceResponse:
    workspace, _ = context
    service = VoiceService(db)
    voice = await service.create_voice(
        workspace_id=workspace.id,
        user_id=current_user.id,
        payload=payload,
    )
    await db.commit()
    return VoiceResponse.model_validate(voice)


@router.get(
    "/voices",
    response_model=List[VoiceResponse],
    summary="List Voices",
    description="Lists active voices in the workspace with filtering.",
)
async def list_voices(
    language: Optional[str] = Query(None),
    gender: Optional[str] = Query(None),
    voice_type: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("voice.read")),
    db: AsyncSession = Depends(get_db),
) -> List[VoiceResponse]:
    workspace, _ = context
    service = VoiceService(db)
    voices = await service.list_voices(
        workspace_id=workspace.id,
        language=language,
        gender=gender,
        voice_type=voice_type,
        status=status_filter,
        search=search,
        limit=limit,
        offset=offset,
    )
    storage = get_storage_provider()
    results = []
    for v in voices:
        resp = VoiceResponse.model_validate(v)
        if v.preview_asset_id:
            asset = await service.asset_repo.get_by_id(v.preview_asset_id, workspace.id)
            if asset and asset.storage_key:
                resp.preview_url = storage.generate_download_url(asset.storage_key, expires_in_seconds=3600)
        results.append(resp)
    return results


@router.get(
    "/voices/{voice_id}",
    response_model=VoiceResponse,
    summary="Get Voice",
    description="Fetches a specific voice by ID.",
)
async def get_voice(
    voice_id: uuid.UUID = Path(..., description="Target Voice Catalog UUID", examples=["10000000-0000-0000-0000-000000000001"]),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("voice.read")),
    db: AsyncSession = Depends(get_db),
) -> VoiceResponse:
    workspace, _ = context
    service = VoiceService(db)
    voice = await service.get_voice(voice_id, workspace.id)
    resp = VoiceResponse.model_validate(voice)
    if voice.preview_asset_id:
        asset = await service.asset_repo.get_by_id(voice.preview_asset_id, workspace.id)
        if asset and asset.storage_key:
            storage = get_storage_provider()
            resp.preview_url = storage.generate_download_url(asset.storage_key, expires_in_seconds=3600)
    return resp


@router.get(
    "/voices/{voice_id}/preview",
    response_model=VoicePreviewResponse,
    summary="Get Voice Preview Audio",
    description="Generates a signed URL for direct audio playback of the voice preview sample.",
)
async def get_voice_preview(
    voice_id: uuid.UUID = Path(..., description="Target Voice Catalog UUID", examples=["10000000-0000-0000-0000-000000000001"]),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("voice.read")),
    db: AsyncSession = Depends(get_db),
) -> VoicePreviewResponse:
    workspace, _ = context
    service = VoiceService(db)
    voice = await service.get_voice(voice_id, workspace.id)
    if not voice.preview_asset_id:
        if voice.provider == "mock":
            raise NotFoundException(
                code="VOICE_PREVIEW_UNAVAILABLE",
                message=f"Voice '{voice.name}' is a catalog mock preset and does not have an audio preview.",
            )
        raise NotFoundException(
            code="VOICE_PREVIEW_NOT_FOUND",
            message=f"No preview audio asset found for voice '{voice.name}'.",
        )

    asset = await service.asset_repo.get_by_id(voice.preview_asset_id, workspace.id)
    if not asset:
        raise NotFoundException(
            code="ASSET_NOT_FOUND",
            message="Preview audio asset record not found.",
        )

    storage = get_storage_provider()
    preview_url = storage.generate_download_url(asset.storage_key, expires_in_seconds=3600)
    return VoicePreviewResponse(
        voice_id=voice.id,
        preview_asset_id=voice.preview_asset_id,
        preview_url=preview_url,
        provider=voice.provider,
        status=voice.status,
        expires_in_seconds=3600,
    )


@router.patch(
    "/voices/{voice_id}",
    response_model=VoiceResponse,
    summary="Update Voice",
    description="Updates voice metadata, language, or preview sample asset.",
)
async def update_voice(
    payload: UpdateVoiceRequest,
    voice_id: uuid.UUID = Path(..., description="Target Voice Catalog UUID", examples=["10000000-0000-0000-0000-000000000001"]),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("voice.update")),
    db: AsyncSession = Depends(get_db),
) -> VoiceResponse:
    workspace, _ = context
    service = VoiceService(db)
    voice = await service.update_voice(voice_id, workspace.id, payload)
    await db.commit()
    await db.refresh(voice)
    return VoiceResponse.model_validate(voice)


@router.delete(
    "/voices/{voice_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Voice",
    description="Soft-deletes a voice.",
)
async def delete_voice(
    voice_id: uuid.UUID = Path(..., description="Target Voice Catalog UUID", examples=["10000000-0000-0000-0000-000000000001"]),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("voice.delete")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    workspace, _ = context
    service = VoiceService(db)
    await service.soft_delete_voice(voice_id, workspace.id)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
