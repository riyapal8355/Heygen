"""Asset management endpoints for pre-signed MinIO direct uploads and secure downloads."""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_permission
from app.db.session import get_db
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.schemas.asset import (
    AssetConfirmResponse,
    AssetDownloadResponse,
    AssetIngestUrlRequest,
    AssetResponse,
    AssetUploadIntentRequest,
    AssetUploadIntentResponse,
)
from app.services.asset_service import AssetService
from app.services.url_ingestion_service import UrlIngestionService

router = APIRouter(prefix="/workspaces/{workspace_id}/assets", tags=["Assets", "Media"])


@router.post(
    "/ingest-url",
    response_model=AssetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest Video from URL",
    description="Ingests a video from a remote URL (YouTube, Google Drive, direct MP4) into MinIO object storage.",
)
async def ingest_video_url(
    payload: AssetIngestUrlRequest,
    workspace_id: uuid.UUID = Path(..., description="Target Workspace UUID", examples=["22222222-2222-2222-2222-222222222222"]),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("asset.create")),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AssetResponse:
    workspace, _ = context
    service = UrlIngestionService(db)
    asset = await service.ingest_video_url(
        url=payload.url,
        workspace_id=workspace.id,
        user_id=current_user.id,
    )
    return AssetResponse.model_validate(asset)


@router.post(
    "/upload-intents",
    response_model=AssetUploadIntentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Upload Intent",
    description="Registers upload intent and generates a pre-signed PUT URL for direct MinIO/S3 upload.",
)
async def create_upload_intent(
    payload: AssetUploadIntentRequest,
    workspace_id: uuid.UUID = Path(..., description="Target Workspace UUID", examples=["22222222-2222-2222-2222-222222222222"]),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("asset.create")),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AssetUploadIntentResponse:
    workspace, _ = context
    service = AssetService(db)
    asset, signed_upload_url = await service.create_upload_intent(
        workspace_id=workspace.id,
        user_id=current_user.id,
        original_filename=payload.original_filename,
        mime_type=payload.mime_type,
        size_bytes=payload.size_bytes,
        asset_type=payload.asset_type,
        checksum_sha256=payload.checksum_sha256,
    )
    await db.commit()

    return AssetUploadIntentResponse(
        asset_id=asset.id,
        storage_bucket=asset.storage_bucket,
        storage_key=asset.storage_key,
        signed_upload_url=signed_upload_url,
        expires_in_seconds=900,
        required_headers={"Content-Type": asset.mime_type},
    )


@router.post(
    "/{asset_id}/confirm",
    response_model=AssetConfirmResponse,
    summary="Confirm Asset Upload",
    description="Verifies the uploaded binary object in storage and transitions status to 'ready'.",
)
async def confirm_asset_upload(
    workspace_id: uuid.UUID = Path(..., description="Target Workspace UUID", examples=["22222222-2222-2222-2222-222222222222"]),
    asset_id: uuid.UUID = Path(..., description="Target Asset UUID", examples=["66666666-6666-6666-6666-666666666666"]),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("asset.create")),
    db: AsyncSession = Depends(get_db),
) -> AssetConfirmResponse:
    workspace, _ = context
    service = AssetService(db)
    asset = await service.confirm_upload(asset_id=asset_id, workspace_id=workspace.id)
    await db.commit()
    await db.refresh(asset)

    return AssetConfirmResponse(
        asset_id=asset.id,
        status=asset.status,
        size_bytes=asset.size_bytes,
        mime_type=asset.mime_type,
    )


@router.get(
    "/{asset_id}/download",
    response_model=AssetDownloadResponse,
    summary="Get Signed Download URL",
    description="Generates a secure pre-signed GET URL for direct asset consumption from storage.",
)
async def get_asset_download_url(
    workspace_id: uuid.UUID = Path(..., description="Target Workspace UUID", examples=["22222222-2222-2222-2222-222222222222"]),
    asset_id: uuid.UUID = Path(..., description="Target Asset UUID", examples=["66666666-6666-6666-6666-666666666666"]),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("asset.read")),
    db: AsyncSession = Depends(get_db),
) -> AssetDownloadResponse:
    workspace, _ = context
    service = AssetService(db)
    asset, download_url = await service.generate_download_url(
        asset_id=asset_id,
        workspace_id=workspace.id,
        expires_in_seconds=3600,
    )
    return AssetDownloadResponse(
        asset_id=asset.id,
        download_url=download_url,
        expires_in_seconds=3600,
    )


@router.get(
    "",
    response_model=List[AssetResponse],
    summary="List Workspace Assets",
    description="Lists active assets with optional filtering by asset type, status, or filename.",
)
async def list_assets(
    workspace_id: uuid.UUID = Path(..., description="Target Workspace UUID", examples=["22222222-2222-2222-2222-222222222222"]),
    asset_type: Optional[str] = Query(None, description="Filter by category: image, video, audio, etc."),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by lifecycle state"),
    search: Optional[str] = Query(None, description="Keyword search in original filename"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("asset.read")),
    db: AsyncSession = Depends(get_db),
) -> List[AssetResponse]:
    workspace, _ = context
    service = AssetService(db)
    assets = await service.list_assets(
        workspace_id=workspace.id,
        asset_type=asset_type,
        status=status_filter,
        search=search,
        limit=limit,
        offset=offset,
    )
    return [AssetResponse.model_validate(a) for a in assets]


@router.get(
    "/{asset_id}",
    response_model=AssetResponse,
    summary="Get Asset Metadata",
    description="Fetches metadata record for an individual asset.",
)
async def get_asset(
    workspace_id: uuid.UUID = Path(..., description="Target Workspace UUID", examples=["22222222-2222-2222-2222-222222222222"]),
    asset_id: uuid.UUID = Path(..., description="Target Asset UUID", examples=["66666666-6666-6666-6666-666666666666"]),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("asset.read")),
    db: AsyncSession = Depends(get_db),
) -> AssetResponse:
    workspace, _ = context
    service = AssetService(db)
    asset = await service.get_asset(asset_id=asset_id, workspace_id=workspace.id)
    return AssetResponse.model_validate(asset)


@router.delete(
    "/{asset_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Asset",
    description="Soft-deletes asset record from database. Physical object cleanup is scheduled asynchronously.",
)
async def delete_asset(
    workspace_id: uuid.UUID = Path(..., description="Target Workspace UUID", examples=["22222222-2222-2222-2222-222222222222"]),
    asset_id: uuid.UUID = Path(..., description="Target Asset UUID", examples=["66666666-6666-6666-6666-666666666666"]),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("asset.delete")),
    db: AsyncSession = Depends(get_db),
) -> None:
    workspace, _ = context
    service = AssetService(db)
    await service.delete_asset(asset_id=asset_id, workspace_id=workspace.id)
    await db.commit()
