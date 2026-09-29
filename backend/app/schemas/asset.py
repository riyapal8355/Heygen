"""Pydantic schemas for Asset management and pre-signed MinIO/S3 flows."""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


class AssetUploadIntentRequest(BaseModel):
    """Client intent declaring an upcoming binary upload."""
    original_filename: str = Field(..., min_length=1, max_length=255)
    mime_type: str = Field(..., min_length=3, max_length=128)
    size_bytes: Optional[int] = Field(default=None, ge=0, description="Expected file size in bytes")
    asset_type: str = Field(
        default="other",
        description="Generic category: image, video, audio, document, font, other",
    )
    checksum_sha256: Optional[str] = Field(
        default=None,
        min_length=64,
        max_length=64,
        description="Claimed SHA-256 digest of binary content",
    )


class AssetIngestUrlRequest(BaseModel):
    """Request to ingest a video from an external URL (YouTube, Google Drive, direct link)."""
    url: str = Field(..., min_length=4, max_length=2048, description="Public video URL")


class AssetUploadIntentResponse(BaseModel):
    """Pre-signed upload coordinates enabling client-to-storage direct PUT."""
    asset_id: uuid.UUID
    storage_bucket: str
    storage_key: str
    signed_upload_url: str
    expires_in_seconds: int
    required_headers: Dict[str, str] = Field(default_factory=dict)


class AssetConfirmResponse(BaseModel):
    """Confirmation status after storage inspection."""
    model_config = ConfigDict(from_attributes=True)

    asset_id: uuid.UUID
    status: str
    size_bytes: Optional[int] = None
    mime_type: str


class AssetDownloadResponse(BaseModel):
    """Pre-signed GET URL for secure direct asset retrieval."""
    asset_id: uuid.UUID
    download_url: str
    expires_in_seconds: int


class AssetResponse(BaseModel):
    """Public asset metadata representation."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    created_by: uuid.UUID
    original_filename: str
    storage_bucket: str
    storage_key: str
    mime_type: str
    size_bytes: Optional[int] = None
    checksum_sha256: Optional[str] = None
    asset_type: str
    status: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="before")
    @classmethod
    def resolve_from_orm(cls, data: Any) -> Any:
        if hasattr(data, "extra_metadata"):
            return {
                "id": data.id,
                "workspace_id": data.workspace_id,
                "created_by": data.created_by,
                "original_filename": data.original_filename,
                "storage_bucket": data.storage_bucket,
                "storage_key": data.storage_key,
                "mime_type": data.mime_type,
                "size_bytes": data.size_bytes,
                "checksum_sha256": data.checksum_sha256,
                "asset_type": data.asset_type,
                "status": data.status,
                "metadata": data.extra_metadata or {},
                "created_at": data.created_at,
                "updated_at": data.updated_at,
            }
        return data
